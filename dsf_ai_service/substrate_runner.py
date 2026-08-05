"""Embedded transport helpers for Guala's current physical boundaries.

This module is not a second cognition service.  The application owns the one
engine instance and mounts it here solely so the in-process substrate client
can reach bounded physical transport and observation handlers.
"""

import base64
import binascii
import hashlib
import os
import subprocess
import threading
import time


STATE_DIR = os.environ.get("STATE_DIR", "/mnt/efs/guala")

_guala = None
_shutdown = False
_shutdown_event = threading.Event()
_background_threads = []
_background_threads_lock = threading.Lock()

# These lifecycle facts are read by app.py's embedded save owner.  No runner
# operation mutates cognition, status, or persistence through them.
_autonomy_pause_refcount = 0
_backup_in_flight = False
_last_successful_backup_wall = 0.0
_backup_lock = threading.Lock()

# The application mounts both bounded rings after it has acquired the sole
# authenticated engine owner.
_substrate_ring = None
_input_ring = None
_input_ring_consumer_started = False

_AUDITORY_PCM_SAMPLE_RATE_HZ = 16_000
_AUDITORY_PCM_SAMPLE_WIDTH_BYTES = 2
_AUDITORY_PCM_MAX_SECONDS = 8
_AUDITORY_PCM_MAX_BYTES = (
    _AUDITORY_PCM_SAMPLE_RATE_HZ
    * _AUDITORY_PCM_SAMPLE_WIDTH_BYTES
    * _AUDITORY_PCM_MAX_SECONDS
)
_AUDITORY_ENCODED_MAX_BYTES = 4 * 1024 * 1024
_AUDITORY_MEDIA_CONTAINER_MAX_BYTES = 30 * 1024 * 1024
_AUDITORY_PCM_DECODE_SENTINEL_BYTES = _AUDITORY_PCM_SAMPLE_WIDTH_BYTES


def _start_background_thread(target, name, *, daemon=True):
    """Start and retain one joinable runner-owned helper."""

    def run_and_release():
        try:
            target()
        finally:
            current = threading.current_thread()
            with _background_threads_lock:
                if current in _background_threads:
                    _background_threads.remove(current)

    with _background_threads_lock:
        if _shutdown_event.is_set():
            raise RuntimeError(
                f"runner background admission is quiesced; rejected {name}"
            )
        thread = threading.Thread(
            target=run_and_release,
            daemon=daemon,
            name=name,
        )
        _background_threads.append(thread)
        try:
            thread.start()
        except BaseException:
            _background_threads.remove(thread)
            raise
    return thread


def quiesce_background_loops(timeout=120.0):
    """Stop and join every runner-owned helper or report exact owners."""
    global _shutdown

    _shutdown = True
    _shutdown_event.set()
    deadline = time.monotonic() + float(timeout)
    while _backup_in_flight:
        if time.monotonic() >= deadline:
            raise RuntimeError(
                "runner quiescence timed out waiting for the app save owner"
            )
        _shutdown_event.wait(0.05)

    with _background_threads_lock:
        threads = tuple(_background_threads)
    alive = []
    for thread in threads:
        if thread is threading.current_thread():
            continue
        thread.join(timeout=max(0.0, deadline - time.monotonic()))
        if thread.is_alive():
            alive.append(thread.name)
    if alive:
        raise RuntimeError(
            "runner quiescence timed out joining: "
            + ", ".join(sorted(alive))
        )
    return {
        "runner_threads_joined": len(threads),
        "alive": [],
    }


def resume_background_loops():
    """A quiesced embedded owner requires process replacement."""
    raise RuntimeError(
        "runner quiescence is irreversible; process replacement is required"
    )


def boot_substrate():
    """Reject the retired standalone mutable-state bootstrap."""
    raise RuntimeError(
        "standalone substrate boot is retired; production must acquire "
        "the sole owner and materialize an authenticated immutable "
        "generation through dsf_ai_service.app"
    )


def _webm_to_wav_bytes(
    audio_bytes,
    *,
    encoded_max_bytes=_AUDITORY_ENCODED_MAX_BYTES,
):
    """Decode bounded encoded audio into canonical mono 16 kHz PCM WAV."""
    import io
    import selectors
    import tempfile
    import wave

    if not isinstance(audio_bytes, bytes):
        raise TypeError("auditory encoded input must be bytes")
    if (
        isinstance(encoded_max_bytes, bool)
        or not isinstance(encoded_max_bytes, int)
        or encoded_max_bytes <= 0
        or encoded_max_bytes > _AUDITORY_MEDIA_CONTAINER_MAX_BYTES
    ):
        raise ValueError("auditory encoded input boundary is invalid")
    if len(audio_bytes) > encoded_max_bytes:
        return None

    command = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-map",
        "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(_AUDITORY_PCM_SAMPLE_RATE_HZ),
        "-t",
        str(
            _AUDITORY_PCM_MAX_SECONDS
            + 1 / _AUDITORY_PCM_SAMPLE_RATE_HZ
        ),
        "-fs",
        str(
            _AUDITORY_PCM_MAX_BYTES
            + _AUDITORY_PCM_DECODE_SENTINEL_BYTES
        ),
        "pipe:1",
    ]
    decoded = bytearray()
    with tempfile.TemporaryFile() as encoded_input:
        encoded_input.write(audio_bytes)
        encoded_input.seek(0)
        process = subprocess.Popen(
            command,
            stdin=encoded_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if process.stdout is None:
            process.kill()
            process.wait()
            raise RuntimeError("ffmpeg stdout pipe was not created")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 8.0
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise subprocess.TimeoutExpired(command, 8.0)
                chunk = os.read(
                    process.stdout.fileno(),
                    min(
                        64 * 1024,
                        _AUDITORY_PCM_MAX_BYTES + 1 - len(decoded),
                    ),
                )
                if not chunk:
                    break
                decoded.extend(chunk)
                if len(decoded) > _AUDITORY_PCM_MAX_BYTES:
                    process.kill()
                    process.wait()
                    return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, 8.0)
            returncode = process.wait(timeout=remaining)
        finally:
            selector.close()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()

    if returncode != 0 or len(decoded) < 400:
        return None
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(_AUDITORY_PCM_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(_AUDITORY_PCM_SAMPLE_RATE_HZ)
        wav_file.writeframes(decoded)
    return wav_buffer.getvalue()


def _report_visual_rejection(error, *, source):
    """Record bounded physical rejection facts without semantic labeling."""
    error_type = type(error).__name__
    reason = str(error)
    if len(error_type.encode("utf-8")) > 128:
        error_type = "VisualRejection"
    if len(reason.encode("utf-8")) > 1024:
        reason = "visual rejection description exceeded telemetry boundary"
    try:
        _guala.record_live_visual_rejection(
            error_type=error_type,
            reason=reason,
        )
    except Exception as telemetry_error:
        try:
            _guala._log_substrate_event(
                "visual_rejection_telemetry_failed",
                source=source,
                error_type=type(telemetry_error).__name__,
            )
        except Exception as log_error:
            print(
                "[runner-visual-rejection] telemetry and event log failed: "
                f"{type(telemetry_error).__name__}/"
                f"{type(log_error).__name__}",
                flush=True,
            )
    return error_type, reason


def _process_sight_sequence(data, *, source):
    from dsf_ai_service.substrate.visual_region_continuity import (
        canonical_visual_frames_from_claims,
    )

    source_start_ns = data.get("source_time_start_ns")
    source_end_ns = data.get("source_time_end_ns")
    frames = canonical_visual_frames_from_claims(
        data.get("frames") or (),
        source_time_start_ns=source_start_ns,
        source_time_end_ns=source_end_ns,
    )
    return _guala.process_live_visual_region_sequence(
        frames,
        source_time_start_ns=source_start_ns,
        source_time_end_ns=source_end_ns,
    )


def _decode_sound_window(data):
    encoded = data.get("audio_b64", "")
    if (
        not isinstance(encoded, str)
        or len(encoded)
        > 4 * ((_AUDITORY_ENCODED_MAX_BYTES + 2) // 3)
    ):
        raise ValueError("encoded audio exceeds its byte boundary")
    audio_bytes = base64.b64decode(encoded, validate=True)
    if not audio_bytes:
        raise ValueError("encoded audio is empty")
    wav_bytes = _webm_to_wav_bytes(audio_bytes)
    if wav_bytes is None:
        raise ValueError("encoded audio did not produce bounded PCM")
    return wav_bytes


def _process_sound_window(event, data):
    source = event.get("source", "ambient")
    boundary = data.get("auditory_event_boundary", "ambient")
    if boundary not in {"ambient", "utterance"}:
        raise ValueError("auditory event boundary is invalid")

    source_start_ns = data.get("source_time_start_ns")
    source_end_ns = data.get("source_time_end_ns")
    wav_bytes = _decode_sound_window(data)
    paired_sight = data.get("sight_frames") or ()
    visual_claimed = (
        bool(data.get("visual_claimed"))
        or bool(paired_sight)
        or bool(data.get("legacy_sight_claimed"))
    )
    visual_source = data.get("visual_source", "camera_stream")
    if visual_source not in {
        "camera_stream",
        "simulated_material_display",
    }:
        raise ValueError("visual source provenance is invalid")
    if not visual_claimed:
        return _guala.process_sound_frame(
            wav_bytes,
            source=source,
            source_anchor_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
            auditory_event_boundary=boundary,
        )

    context_id = f"sense:av:{source}:ring:{event.get('seq', 0)}"
    _guala.window_manager.begin_context(
        context_id,
        "audiovisual_capture",
        context_detail={
            "experience_origin": "remote_live_audiovisual",
            "auditory_event_boundary": boundary,
            "source": source,
            "visual_source": visual_source,
            "source_time_start_ns": source_start_ns,
            "source_time_end_ns": source_end_ns,
            "sensor_unavailable": [
                "touch",
                "smell",
                "taste",
                "body",
            ],
        },
    )
    try:
        try:
            transport_error = data.get("visual_transport_error")
            if transport_error is not None:
                if (
                    not isinstance(transport_error, str)
                    or not transport_error
                    or len(transport_error.encode("utf-8")) > 1024
                ):
                    raise ValueError(
                        "visual transport rejection changed shape"
                    )
                raise ValueError(transport_error)
            if data.get("legacy_sight_claimed"):
                raise ValueError(
                    "legacy singleton sight cannot establish a temporal field"
                )
            _process_sight_sequence(
                {
                    "frames": paired_sight,
                    "source_time_start_ns": source_start_ns,
                    "source_time_end_ns": source_end_ns,
                },
                source=source,
            )
        except Exception as sight_error:
            error_type, reason = _report_visual_rejection(
                sight_error,
                source=source,
            )
            try:
                _guala._log_substrate_event(
                    "sight_frame_failed_in_causal_window",
                    source=source,
                    error_type=error_type,
                    error=reason,
                )
            except Exception as log_error:
                print(
                    "[runner-visual-rejection] causal-window event log "
                    f"failed: {type(log_error).__name__}",
                    flush=True,
                )
        return _guala.process_sound_frame(
            wav_bytes,
            source=source,
            source_anchor_ns=source_start_ns,
            source_time_end_ns=source_end_ns,
            auditory_event_boundary=boundary,
        )
    finally:
        try:
            _guala.window_manager.end_context(
                context_id,
                "audiovisual_capture_complete",
            )
        except Exception:
            _guala.window_manager.discard_unsettled_context(
                context_id,
                "remote_live_audiovisual_settlement_failed",
            )
            raise


def _start_input_ring_consumer():
    """Start the sole bounded physical input-ring consumer."""
    global _input_ring_consumer_started

    if _input_ring_consumer_started:
        return
    _input_ring_consumer_started = True

    def drain_loop():
        while not _shutdown:
            if _input_ring is None or _guala is None:
                if _shutdown_event.wait(1.0):
                    break
                continue
            try:
                events = _input_ring.drain(max_n=10)
                for event in events:
                    kind = event.get("kind")
                    data = event.get("data", {})
                    source = event.get("source", "bridge")
                    if kind == "sight_sequence":
                        try:
                            _process_sight_sequence(data, source=source)
                        except Exception as error:
                            _report_visual_rejection(error, source=source)
                    elif kind == "sound_window":
                        _guala._enter_live_interaction()
                        try:
                            _process_sound_window(event, data)
                        except Exception as error:
                            try:
                                _guala._log_substrate_event(
                                    "sound_frame_transport_rejected",
                                    source=source,
                                    error_type=type(error).__name__,
                                    reason=str(error)[:1024],
                                )
                            except Exception as log_error:
                                print(
                                    "[runner-sound-rejection] event log "
                                    f"failed: {type(log_error).__name__}",
                                    flush=True,
                                )
                        finally:
                            _guala._exit_live_interaction()
            except Exception as drain_error:
                print(
                    "[runner-input-ring] drain failed: "
                    f"{type(drain_error).__name__}: {drain_error}",
                    flush=True,
                )
            if _shutdown_event.wait(0.5):
                break

    _start_background_thread(
        drain_loop,
        "input-ring-consumer",
    )


def handle_ring_write(args):
    """Admit only current physical sight or sound transport."""
    if _input_ring is None:
        return {
            "ok": False,
            "error": "input ring not initialized",
        }
    kind = args.get("kind")
    if kind not in {"sight_sequence", "sound_window"}:
        return {
            "ok": False,
            "error": "unsupported physical input event",
            "status_code": 422,
        }
    data = args.get("data")
    if not isinstance(data, dict):
        return {
            "ok": False,
            "error": "physical input data must be an object",
            "status_code": 422,
        }

    from dsf_ai_service.substrate.ring_buffer import (
        InputRingCapacityError,
    )

    try:
        sequence = _input_ring.publish(
            kind,
            args.get("source", "bridge"),
            **{
                key: value
                for key, value in data.items()
                if key != "source"
            },
        )
    except InputRingCapacityError as error:
        return {
            "ok": False,
            "error": str(error),
            "input_pending": _input_ring.pending,
            "input_pending_transport_bytes": (
                _input_ring.pending_transport_bytes
            ),
            "input_max_pending_transport_bytes": (
                _input_ring.max_pending_transport_bytes
            ),
            "input_rejected_events": _input_ring.rejected_events,
        }
    return {
        "ok": True,
        "transport_receipt": {
            "kind": kind,
            "sequence": sequence,
        },
    }


def handle_observation_snapshot(_args):
    """Return the engine's authoritative read-only physical observation."""
    return _guala.observation_snapshot()


LEARNED_BODY_ACT_TRANSPORT_SCHEMA = (
    "guala.embodied_action_experience.learned_body_act_transport.v1"
)
_RAW_VOCAL_CAUSAL_ACT_SCHEMA = (
    "guala.embodied_action_experience.vocal_causal_act.v1"
)
_RAW_VOCAL_CAUSAL_ACT_FIELDS = frozenset({
    "act_receipt",
    "additional_world_mutation",
    "pcm_s16le",
    "pcm_sha256",
    "program_custody_receipt_sha256",
    "reason",
    "retained_pcm_bytes",
    "sample_count",
    "sample_rate_hz",
    "schema",
    "selection_authority_hmac_sha256",
    "selection_authority_receipt_sha256",
    "state",
})
_LEARNED_BODY_ACT_COMMON_FIELDS = frozenset({
    "additional_world_mutation",
    "reason",
    "schema",
    "selection_authority_hmac_sha256",
    "selection_authority_receipt_sha256",
    "state",
})
_LEARNED_BODY_ACT_EMITTED_FIELDS = frozenset({
    *_LEARNED_BODY_ACT_COMMON_FIELDS,
    "act_receipt",
    "pcm_s16le_base64",
    "pcm_sha256",
    "program_custody_receipt_sha256",
    "retained_pcm_bytes",
    "sample_count",
    "sample_rate_hz",
})


def _canonical_lower_sha256(value, label):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(f"{label} changed")
    return value


def _typed_full_vocal_act_receipt(value):
    del value
    raise RuntimeError(
        "legacy Python learned vocal act is permanently retired"
    )


def _verify_learned_body_act_transport(value):
    del value
    raise RuntimeError(
        "legacy Python learned vocal act is permanently retired"
    )


def _embodied_action_transport(result):
    """Expose physical action evidence without retired vocal cognition."""

    if not isinstance(result, dict):
        raise ValueError("embodied action result is not a mapping")
    has_raw = "vocal_causal_act" in result
    has_transport = "learned_body_act" in result
    if has_raw or has_transport:
        raise RuntimeError(
            "legacy Python learned vocal act is permanently retired"
        )
    return dict(result)


def handle_embodied_action_experience(args):
    """Durably experience one canonical W1 command."""
    try:
        encoded = args.get("command_payload_base64")
        if not isinstance(encoded, str) or len(encoded) > 8192:
            raise ValueError("embodied command transport exceeds boundary")
        command_payload = base64.b64decode(encoded, validate=True)
        if base64.b64encode(command_payload).decode("ascii") != encoded:
            raise ValueError("embodied command transport is not canonical")
        result = _guala.durably_experience_embodied_action(
            tutor_id=args.get("tutor_id"),
            nonce=args.get("nonce"),
            port_id=args.get("port_id"),
            command_payload=command_payload,
            state_dir=STATE_DIR,
        )
        return _embodied_action_transport(result)
    except (PermissionError, RuntimeError, ValueError) as error:
        return {
            "ok": False,
            "error": str(error),
        }


def handle_ground_latest_sight_contact(_args):
    """Ground retained sight through current W1 contact custody."""
    try:
        return _guala.durably_ground_latest_retained_sight_to_contact(
            state_dir=STATE_DIR,
        )
    except (RuntimeError, ValueError) as error:
        return {
            "ok": False,
            "error": str(error),
        }


OP_HANDLERS = {
    "ring_write": handle_ring_write,
    "observation_snapshot": handle_observation_snapshot,
    "embodied_action_experience": handle_embodied_action_experience,
    "ground_latest_sight_contact": handle_ground_latest_sight_contact,
}
HANDLERS = OP_HANDLERS


def dispatch(op, args):
    """Dispatch one allowed embedded operation and fail closed otherwise."""
    if _guala is None:
        raise RuntimeError("substrate not ready")
    handler = OP_HANDLERS.get(op)
    if handler is None:
        raise ValueError(f"unknown op: {op}")
    return handler(args)


def heartbeat_loop():
    """Compatibility callable retained for app startup; no heartbeat exists."""
    return None
