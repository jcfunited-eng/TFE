"""Prove bounded continuous audiovisual cognition in a real Chromium page.

This probe serves the reviewed local Guala page and its real FastAPI routes
from one candidate process. Chromium receives the known physical WAV through
its fake microphone device and its native fake camera device. The page is not
reimplemented: only the hard-coded production API origin is redirected to the
candidate origin before page JavaScript starts.

One actually captured runtime channel must remain active through the exact
presemantic recurrent-motif owner.
When Chromium exposes two runtime channels, their distinct bytes and shared
clock must also reach the candidate binaural endpoint.  That optional pair
must remain hardware-unproven and excluded from room-hearing cognition.

The fake-microphone WAV must carry two independent Hello occurrences followed
by an equal-gain Hello-plus-Daddy overlap.  The proof requires exact motif
growth from the independent occurrences and later firing of at least one of
those learned motif neuron identities inside the overlap.  A transcript is
never interpreted as Guala's recognition.
"""

from __future__ import annotations

import argparse
import base64
import cProfile
import hashlib
import itertools
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_CHUNK_SAMPLES,
    PCM_CONTINUITY_SCHEMA,
    PCM_RING_BYTES,
    PCM_SAMPLE_RATE_HZ,
    PCM_TRANSPORT_UNITS,
    AuditoryPCMStreamRegistry,
)
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    BINAURAL_RING_BYTES_PER_STREAM,
    BrowserBinauralPCMStreamRegistry,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


PRODUCTION_API_ORIGIN = "https://3d6toi0gw0.execute-api.us-east-1.amazonaws.com"
PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
MINIMUM_SETTLED_CHUNKS = 5
PROOF_SECONDS = 35
HELLO_LEARNING_SETTLEMENT_SEQUENCE = 9
OVERLAP_FIRING_SETTLEMENT_SEQUENCE = 15
COGNITIVE_PROOF_WAV = Path(
    "/tmp/guala-live-motif-cognitive-proof.wav"
)
COGNITIVE_SOURCE_RECORDINGS = (
    (
        Path("harness/hello guala 1.mp3"),
        "a34617fa9d0fd84dfdbbc211486c0c5ea7aef791505de006af092340d98411bf",
    ),
    (
        Path("harness/hello guala 2.mp3"),
        "cb57e13b88d06712fda555889ba351ce50f7abb027e7d64e6c03c6bec0bdab98",
    ),
    (
        Path("docs/Daddy says Hello.mp3"),
        "11e76f8358448f348cc531e0f1493868d91da6bc8d80ef1101a364fdba4361de",
    ),
)


def _configure_candidate_environment() -> None:
    os.environ.setdefault("DECAY_PAUSED", "1")
    os.environ.setdefault("EVENT_DRIVEN_SUBSTRATE", "0")
    os.environ.setdefault(
        "GUALA_CAUSAL_ACTION_KEY",
        "candidate-browser-proof-authority-key-v1",
    )
    os.environ.setdefault("NATIVE_CORE_ENABLED", "1")
    os.environ.setdefault("SELF_HEARING_ENABLED", "0")
    os.environ.setdefault("SUBSTRATE_MODE", "embedded")
    os.environ.setdefault("WAVE_ATLAS_ENABLED", "0")
    os.environ.setdefault("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")


def _checked_cognitive_source(
    relative_path: Path,
    expected_pcm_sha256: str,
) -> bytes:
    from tools.probe_auditory_full_field_discrimination import (
        _decode_pcm,
    )

    source = ROOT / relative_path
    if not source.is_file():
        raise FileNotFoundError(
            "authoritative candidate cognitive proof source recording is "
            f"absent: {relative_path}"
        )
    pcm = _decode_pcm(source)
    actual = hashlib.sha256(pcm).hexdigest()
    if actual != expected_pcm_sha256:
        raise RuntimeError(
            f"cognitive proof source PCM changed: {relative_path}; "
            f"expected={expected_pcm_sha256}; actual={actual}"
        )
    return pcm


def build_cognitive_proof_wav(
    output_path: Path = COGNITIVE_PROOF_WAV,
) -> dict[str, object]:
    """Build and receipt the exact 48-second fake-microphone schedule."""

    hello_one_pcm, hello_two_pcm, daddy_pcm = (
        _checked_cognitive_source(path, digest)
        for path, digest in COGNITIVE_SOURCE_RECORDINGS
    )
    hello_one = np.frombuffer(
        hello_one_pcm, dtype="<i2"
    ).astype(np.int32)
    hello_two = np.frombuffer(
        hello_two_pcm, dtype="<i2"
    ).astype(np.int32)
    daddy = np.frombuffer(daddy_pcm, dtype="<i2").astype(np.int32)
    scheduled = np.zeros(48 * PCM_SAMPLE_RATE_HZ, dtype=np.int32)

    def admit(
        first_sample_index: int,
        values: np.ndarray,
        *,
        half_gain: bool = False,
    ) -> None:
        admitted = values
        if half_gain:
            admitted = np.where(
                values >= 0,
                values // 2,
                -((-values) // 2),
            )
        scheduled[
            first_sample_index:first_sample_index + len(admitted)
        ] += admitted

    admit(12_800, hello_one)
    admit(230_400, hello_two)
    admit(422_400, hello_two, half_gain=True)
    admit(422_400, daddy, half_gain=True)
    pcm = np.clip(
        scheduled, -32_768, 32_767
    ).astype("<i2").tobytes()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(PCM_SAMPLE_RATE_HZ)
        target.writeframes(pcm)
    chunk_bytes = PCM_CHUNK_SAMPLES * 2
    chunk_sha256s = tuple(
        hashlib.sha256(pcm[offset:offset + chunk_bytes]).hexdigest()
        for offset in range(0, len(pcm), chunk_bytes)
    )
    return {
        "chunk_sha256s": chunk_sha256s,
        "hello_learning_sequence": (
            HELLO_LEARNING_SETTLEMENT_SEQUENCE
        ),
        "overlap_firing_sequence": (
            OVERLAP_FIRING_SETTLEMENT_SEQUENCE
        ),
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "sample_count": len(pcm) // 2,
        "source_pcm_sha256s": tuple(
            digest for _path, digest in COGNITIVE_SOURCE_RECORDINGS
        ),
        "wav_path": output_path,
    }


def _validate_cognitive_schedule_transport(
    settled: list[dict],
    schedule: dict[str, object],
) -> dict[str, object]:
    """Reconcile the authenticated source with its captured PCM exactly.

    Chromium's microphone device resamples the WAV before the 16 kHz
    AudioWorklet.  Post-resampler magnitudes therefore cannot truthfully equal
    pre-resampler WAV magnitudes.  The unique first physical-pressure edge
    supplies the exact causal sample offset.  Every captured magnitude is then
    hashed into the server's own continuity receipt and that complete receipt
    chain is reconstructed here.  No correlation, tolerance, interpolation,
    or approximate waveform match participates.
    """

    wav_path = schedule.get("wav_path")
    source_sha256 = schedule.get("pcm_sha256")
    source_sample_count = schedule.get("sample_count")
    if (
        not isinstance(wav_path, Path)
        or not wav_path.is_file()
        or not isinstance(source_sha256, str)
        or not isinstance(source_sample_count, int)
    ):
        raise RuntimeError("cognitive proof source authority changed")
    with wave.open(str(wav_path), "rb") as source:
        source_shape = (
            source.getnchannels(),
            source.getsampwidth(),
            source.getframerate(),
            source.getnframes(),
        )
        source_pcm = source.readframes(source.getnframes())
    if (
        source_shape
        != (1, 2, PCM_SAMPLE_RATE_HZ, source_sample_count)
        or hashlib.sha256(source_pcm).hexdigest() != source_sha256
    ):
        raise RuntimeError("authenticated cognitive source WAV changed")

    captured_chunks: list[bytes] = []
    captured_pcm_sha256s: list[str] = []
    continuity_receipt_sha256s: list[str] = []
    prior_receipt_sha256 = None
    source_epoch_start_ns = None
    for expected_sequence, record in enumerate(settled):
        request = record["request"]
        response = record["response"]
        continuity = response["pcm_continuity"]
        try:
            pcm = base64.b64decode(request["text"], validate=True)
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(
                "candidate browser request lost scheduled PCM"
            ) from error
        if (
            request.get("audio_sequence") != expected_sequence
            or request.get("audio_sample_count") * 2 != len(pcm)
        ):
            raise RuntimeError(
                "candidate captured PCM lost its declared sample interval"
            )
        pcm_sha256 = hashlib.sha256(pcm).hexdigest()
        epoch_ms = request.get("audio_source_epoch_ms")
        if (
            isinstance(epoch_ms, bool)
            or not isinstance(epoch_ms, int)
        ):
            raise RuntimeError(
                "candidate captured PCM lost its physical source epoch"
            )
        current_epoch_start_ns = epoch_ms * 1_000_000
        if source_epoch_start_ns is None:
            source_epoch_start_ns = current_epoch_start_ns
        elif current_epoch_start_ns != source_epoch_start_ns:
            raise RuntimeError(
                "candidate captured PCM changed physical source epoch"
            )
        payload = {
            "first_sample_index": request[
                "audio_first_sample_index"
            ],
            "pcm_sha256": pcm_sha256,
            "prior_receipt_sha256": prior_receipt_sha256,
            "sample_count": request["audio_sample_count"],
            "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
            "schema": PCM_CONTINUITY_SCHEMA,
            "sequence": expected_sequence,
            "stream_id": request["audio_stream_id"],
            "source_epoch_start_ns": source_epoch_start_ns,
        }
        expected_receipt_sha256 = hashlib.sha256(json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()
        if (
            continuity.get("receipt_sha256")
            != expected_receipt_sha256
        ):
            raise RuntimeError(
                "candidate captured PCM hash did not enter the server "
                f"continuity receipt at sequence {expected_sequence}"
            )
        captured_chunks.append(pcm)
        captured_pcm_sha256s.append(pcm_sha256)
        continuity_receipt_sha256s.append(
            expected_receipt_sha256
        )
        prior_receipt_sha256 = expected_receipt_sha256

    captured_pcm = b"".join(captured_chunks)
    source_values = np.frombuffer(source_pcm, dtype="<i2")
    captured_values = np.frombuffer(captured_pcm, dtype="<i2")
    source_pressure_indices = np.flatnonzero(source_values)
    captured_pressure_indices = np.flatnonzero(captured_values)
    if (
        not len(source_pressure_indices)
        or not len(captured_pressure_indices)
    ):
        raise RuntimeError(
            "cognitive schedule has no physical pressure edge"
        )
    source_first_pressure_sample = int(
        source_pressure_indices[0]
    )
    captured_first_pressure_sample = int(
        captured_pressure_indices[0]
    )
    source_start_offset_samples = (
        source_first_pressure_sample
        - captured_first_pressure_sample
    )
    if (
        source_start_offset_samples < 0
        or source_start_offset_samples + len(captured_values)
        > len(source_values)
    ):
        raise RuntimeError(
            "candidate physical pressure has no bounded causal source "
            "offset inside the authenticated WAV"
        )
    return {
        "captured_first_pressure_sample": (
            captured_first_pressure_sample
        ),
        "captured_pcm_sha256": hashlib.sha256(
            captured_pcm
        ).hexdigest(),
        "captured_pcm_sha256s": captured_pcm_sha256s,
        "continuity_receipt_sha256s": (
            continuity_receipt_sha256s
        ),
        "source_first_pressure_sample": (
            source_first_pressure_sample
        ),
        "source_pcm_sha256": source_sha256,
        "source_start_offset_samples": (
            source_start_offset_samples
        ),
        "source_transduction": (
            "chromium_microphone_to_16khz_audioworklet"
        ),
    }



def _process_rss_bytes(process_id: int) -> int:
    with open(f"/proc/{process_id}/status", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError(
        f"candidate process {process_id} resident memory is unavailable"
    )


def _process_tree_ids(process_id: int) -> tuple[int, ...]:
    pending = [process_id]
    observed = []
    while pending:
        current = pending.pop()
        if current in observed:
            continue
        observed.append(current)
        children_path = (
            f"/proc/{current}/task/{current}/children"
        )
        try:
            children = Path(children_path).read_text().split()
        except FileNotFoundError:
            continue
        pending.extend(int(value) for value in children)
    return tuple(observed)


def _tree_rss_bytes() -> int:
    total = 0
    for process_id in _process_tree_ids(os.getpid()):
        try:
            total += _process_rss_bytes(process_id)
        except FileNotFoundError:
            continue
    return total


def _tree_rss_breakdown() -> list[dict[str, object]]:
    result = []
    for process_id in _process_tree_ids(os.getpid()):
        try:
            resident_bytes = _process_rss_bytes(process_id)
            command = Path(
                f"/proc/{process_id}/comm"
            ).read_text().strip()
        except FileNotFoundError:
            continue
        result.append({
            "command": command,
            "process_id": process_id,
            "resident_bytes": resident_bytes,
        })
    return sorted(
        result,
        key=lambda value: value["resident_bytes"],
        reverse=True,
    )


def _resident_groups(
    breakdown: list[dict[str, object]],
) -> dict[str, int]:
    candidate_process_id = os.getpid()
    candidate = sum(
        value["resident_bytes"]
        for value in breakdown
        if value["process_id"] == candidate_process_id
    )
    chromium = sum(
        value["resident_bytes"]
        for value in breakdown
        if str(value["command"]).startswith("chrome")
    )
    exact_workers = sum(
        value["resident_bytes"]
        for value in breakdown
        if (
            value["process_id"] != candidate_process_id
            and not str(value["command"]).startswith("chrome")
        )
    )
    return {
        "candidate_engine_bytes": candidate,
        "chromium_bytes": chromium,
        "exact_worker_bytes": exact_workers,
        "tree_bytes": candidate + chromium + exact_workers,
    }


def _retained_owner_status(engine: Guala) -> dict[str, object]:
    hearing = engine.auditory_l5_status()
    terminal_lengths = tuple(
        len(value)
        for value in (
            engine._auditory_receptor_terminal_by_stream.values()
        )
        if not isinstance(value, str)
    )
    recurrent_motif = {
        **hearing["recurrent_motif"],
        "maximum_pending_transport_units_in_one_stream": (
            max(terminal_lengths, default=0)
        ),
    }
    return {
        "auditory_full_field_streams": (
            engine._auditory_full_field_streams.status()
        ),
        "auditory_l5": engine._auditory_l5_owner.status(),
        "auditory_recurrent_motif": recurrent_motif,
        "auditory_hearing_authority": hearing[
            "active_hearing_authority"
        ],
        "auditory_legacy_quarantine": {
            "krimelack_live": hearing["krimelack_live"],
            "krimelack_cognition": hearing["krimelack_cognition"],
            "incremental_terminal": hearing[
                "legacy_incremental_terminal"
            ],
        },
        "causal_action": engine._causal_action_owner.status(),
        "causal_action_cycle": (
            engine._causal_action_cycle.status()
            if engine._causal_action_cycle is not None
            else None
        ),
        "exact_causal_experience": (
            engine._causal_experience_owner.status()
        ),
        "full_field_prediction": (
            engine._full_field_prediction.status()
            if engine._full_field_prediction is not None
            else None
        ),
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_candidate(url: str, server: uvicorn.Server) -> bytes:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if not server_thread_alive(server):
            raise RuntimeError("candidate service stopped before readiness")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return response.read()
        except Exception as error:
            last_error = error
        time.sleep(0.1)
    raise RuntimeError(
        f"candidate service did not become ready: {last_error}"
    )


def server_thread_alive(server: uvicorn.Server) -> bool:
    thread = getattr(server, "_candidate_thread", None)
    return isinstance(thread, threading.Thread) and thread.is_alive()


def _install_candidate_globals(engine: Guala) -> None:
    import dsf_ai_service.app as app_module

    app_module._guala = engine
    app_module._init_complete = True
    app_module._init_error = None
    app_module._LIFESPAN_STARTED = True
    app_module._auditory_pcm_streams = AuditoryPCMStreamRegistry()
    app_module._browser_binaural_pcm_streams = (
        BrowserBinauralPCMStreamRegistry()
    )
    app_module._converse_inflight = 0
    app_module._converse_window_started_at = 0.0
    app_module._is_remote = lambda: False
    profile_prefix = os.environ.get(
        "GUALA_CANDIDATE_MUTATION_PROFILE_PREFIX"
    )
    if profile_prefix:
        original_executor = app_module._run_lifecycle_executor
        sequence = itertools.count()
        profile_start = int(os.environ.get(
            "GUALA_CANDIDATE_MUTATION_PROFILE_START",
            "0",
        ))
        profile_count = int(os.environ.get(
            "GUALA_CANDIDATE_MUTATION_PROFILE_COUNT",
            "0",
        ))

        async def profiled_executor(function, *args):
            if getattr(function, "__name__", "") != "_decode_serialized":
                return await original_executor(function, *args)
            current_sequence = next(sequence)
            if (
                current_sequence < profile_start
                or (
                    profile_count > 0
                    and current_sequence >= profile_start + profile_count
                )
            ):
                return await original_executor(function, *args)
            profile_path = (
                f"{profile_prefix}-{current_sequence:03d}.prof"
            )

            def run_profiled():
                profiler = cProfile.Profile()
                try:
                    return profiler.runcall(function, *args)
                finally:
                    profiler.dump_stats(profile_path)

            return await original_executor(run_profiled)

        app_module._run_lifecycle_executor = profiled_executor


def _start_candidate(port: int) -> uvicorn.Server:
    import dsf_ai_service.app as app_module

    config = uvicorn.Config(
        app_module.app,
        host="127.0.0.1",
        port=port,
        lifespan="off",
        log_level="warning",
    )
    server = uvicorn.Server(config)
    profile_path = os.environ.get("GUALA_CANDIDATE_PROFILE_PATH")

    def run_server() -> None:
        if profile_path:
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                server.run()
            finally:
                profiler.disable()
                profiler.dump_stats(profile_path)
        else:
            server.run()

    thread = threading.Thread(
        target=run_server,
        name="guala-candidate-browser-service",
        daemon=True,
    )
    server._candidate_thread = thread
    thread.start()
    return server


def _browser_instrumentation(candidate_origin: str) -> str:
    return f"""
      (() => {{
        const production={json.dumps(PRODUCTION_API_ORIGIN)};
        const candidate={json.dumps(candidate_origin)};
        const nativeFetch=window.fetch.bind(window);
        window.__candidateSoundFrames=[];
        window.__candidateBinauralFrames=[];
        window.__candidateBinauralLineages=[];
        window.__candidateSightFrames=[];
        window.__candidateFetchErrors=[];
        window.fetch=(input,init={{}})=>{{
          const supplied=typeof input==='string'?input:input.url;
          const rewritten=supplied.startsWith(production)
            ? candidate+supplied.slice(production.length)
            : supplied;
          let requestRecord=null;
          if(rewritten.endsWith('/sound_frame')){{
            try{{
              const body=JSON.parse(init.body);
              requestRecord={{
                request:body,
                response:null,
                responseStatus:null,
                fetchError:null,
                requestedAtMs:performance.now(),
                responseAtMs:null
              }};
              window.__candidateSoundFrames.push(requestRecord);
            }}catch(error){{
              window.__candidateFetchErrors.push(
                'sound request capture failed: '+error.message
              );
            }}
          }}else if(rewritten.endsWith(
            '/api/v1/auditory/binaural-pcm/chunk'
          )){{
            try{{
              const body=JSON.parse(init.body);
              requestRecord={{
                request:body,
                response:null,
                responseStatus:null,
                fetchError:null,
                requestedAtMs:performance.now(),
                responseAtMs:null
              }};
              window.__candidateBinauralFrames.push(requestRecord);
            }}catch(error){{
              window.__candidateFetchErrors.push(
                'binaural request capture failed: '+error.message
              );
            }}
          }}else if(rewritten.endsWith(
            '/api/v1/auditory/binaural-pcm/lineage'
          )){{
            try{{
              const body=JSON.parse(init.body);
              requestRecord={{
                request:body,
                response:null,
                responseStatus:null,
                fetchError:null,
                requestedAtMs:performance.now(),
                responseAtMs:null
              }};
              window.__candidateBinauralLineages.push(requestRecord);
            }}catch(error){{
              window.__candidateFetchErrors.push(
                'binaural lineage capture failed: '+error.message
              );
            }}
          }}else if(rewritten.endsWith('/sight_frame')){{
            try{{
              const body=JSON.parse(init.body);
              requestRecord={{
                request:body,
                response:null,
                responseStatus:null,
                fetchError:null,
                requestedAtMs:performance.now(),
                responseAtMs:null
              }};
              window.__candidateSightFrames.push(requestRecord);
            }}catch(error){{
              window.__candidateFetchErrors.push(
                'sight request capture failed: '+error.message
              );
            }}
          }}
          return nativeFetch(rewritten,init).then(response=>{{
            if(requestRecord){{
              requestRecord.responseStatus=response.status;
              requestRecord.responseAtMs=performance.now();
              response.clone().json().then(value=>{{
                requestRecord.response=value;
              }}).catch(error=>{{
                requestRecord.fetchError=error.message;
              }});
            }}
            return response;
          }}).catch(error=>{{
            if(requestRecord)requestRecord.fetchError=error.message;
            throw error;
          }});
        }};
      }})();
    """


def _status_snapshot(page) -> dict:
    return page.evaluate(
        """() => ({
          microphoneStatus:document.getElementById('mic-status').textContent,
          cameraStatus:document.getElementById('cam-status').textContent,
          microphoneActive:Boolean(
            micPCMActive&&micEpoch&&micEpoch.active&&micEpoch.accepting
          ),
          cameraActive:Boolean(camStream),
          pendingChunks:micEpoch?micEpoch.pendingChunks:null,
          admittedSequence:micEpoch?micEpoch.sequence:null,
          monoStreamId:micEpoch?micEpoch.monoStreamId:null,
          binauralStreamId:micEpoch?micEpoch.streamId:null,
          inputChannelCount:micEpoch?micEpoch.inputChannelCount:null,
          binauralActive:Boolean(
            micEpoch&&micEpoch.active&&micEpoch.accepting&&
            micEpoch.binauralActive
          ),
          microphoneTracks:micStream
            ? micStream.getTracks().map(track=>track.readyState):[],
          cameraTracks:camStream
            ? camStream.getTracks().map(track=>track.readyState):[],
          proofElapsedMs:Number.isFinite(
            window.__candidateProofStartedAtMs
          )?performance.now()-window.__candidateProofStartedAtMs:null,
          capturedSoundRequests:Array.isArray(
            window.__candidateSoundFrames
          )?window.__candidateSoundFrames.length:0,
          settledSoundResponses:Array.isArray(
            window.__candidateSoundFrames
          )?window.__candidateSoundFrames.filter(
            value=>value&&value.response!==null
          ).length:0
        })"""
    )


def _stop_admission_and_drain(page, timeout_ms: int = 70_000) -> dict:
    return page.evaluate(
        """async timeoutMs => {
          const epoch=micEpoch;
          if(!epoch||!epoch.active||!epoch.accepting){
            throw new Error('microphone epoch was not accepting at proof stop');
          }
          const acceptedBeforeStop=epoch.sequence;
          const pendingBeforeStop=epoch.pendingChunks;
          const soundRequestsAtStop=window.__candidateSoundFrames.length;
          const binauralRequestsAtStop=
            window.__candidateBinauralFrames.length;
          const terminal=value=>value&&(
            value.response!==null||value.fetchError!==null
          );
          const soundResponsesAtStop=
            window.__candidateSoundFrames.filter(terminal).length;
          const binauralResponsesAtStop=
            window.__candidateBinauralFrames.filter(terminal).length;
          const binauralWasActive=epoch.binauralActive;
          const closePromise=_closePCMEpoch(epoch,true,true);
          if(epoch.accepting){
            throw new Error('microphone admission remained open at stop');
          }
          const deadline=performance.now()+timeoutMs;
          while(true){
            const sound=window.__candidateSoundFrames;
            const binaural=window.__candidateBinauralFrames;
            const countsComplete=
              sound.length===acceptedBeforeStop&&
              (!binauralWasActive||
                binaural.length===acceptedBeforeStop);
            const responsesTerminal=
              sound.every(terminal)&&binaural.every(terminal);
            if(epoch.pendingChunks===0&&countsComplete&&
               responsesTerminal)break;
            if(sound.length>acceptedBeforeStop||
               binaural.length>acceptedBeforeStop){
              throw new Error(
                'capture admitted a new interval after proof stop'
              );
            }
            if(performance.now()>=deadline){
              throw new Error(
                'accepted microphone intervals did not drain before '+timeoutMs+
                'ms; accepted='+acceptedBeforeStop+
                '; pending='+epoch.pendingChunks+
                '; sound='+sound.length+
                '; binaural='+binaural.length
              );
            }
            await new Promise(resolve=>setTimeout(resolve,25));
          }
          await closePromise;
          const sound=window.__candidateSoundFrames;
          const binaural=window.__candidateBinauralFrames;
          if(sound.length!==acceptedBeforeStop||
             (binauralWasActive&&
              binaural.length!==acceptedBeforeStop)){
            throw new Error(
              'drained request counts diverged from pre-stop admission'
            );
          }
          return {
            acceptedBeforeStop,
            pendingBeforeStop,
            soundRequestsAtStop,
            binauralRequestsAtStop,
            soundResponsesAtStop,
            binauralResponsesAtStop,
            soundRequestsAfterDrain:sound.length,
            binauralRequestsAfterDrain:binaural.length,
            acceptedSoundRequestsIssuedAfterStop:
              sound.length-soundRequestsAtStop,
            acceptedBinauralRequestsIssuedAfterStop:
              binaural.length-binauralRequestsAtStop,
            acceptedSoundResponsesAfterStop:
              sound.filter(terminal).length-soundResponsesAtStop,
            acceptedBinauralResponsesAfterStop:
              binaural.filter(terminal).length-binauralResponsesAtStop,
            newAdmissionsAfterStop:
              Math.max(0,sound.length-acceptedBeforeStop,
                binaural.length-acceptedBeforeStop),
            binauralWasActive,
            soundRecords:sound,
            binauralRecords:binaural
          };
        }""",
        timeout_ms,
    )


def _validate_visual_intervals(records: list[dict]) -> list[dict]:
    settled = [
        record
        for record in records
        if isinstance(record.get("response"), dict)
    ]
    if len(settled) < 2:
        raise RuntimeError(
            "candidate browser settled fewer than two independent sight fields"
        )
    prior_interval_end_ms = None
    for record in settled:
        request = record["request"]
        frames = request.get("sight_frames")
        if not isinstance(frames, list) or len(frames) < 4:
            raise RuntimeError(
                "candidate browser did not pair four physical sight frames"
            )
        interval_start_ms = request.get("capture_started_ms")
        interval_end_ms = request.get("capture_ended_ms")
        response = record.get("response")
        if (
            record.get("responseStatus") != 200
            or not isinstance(response, dict)
            or response.get("ok") is not True
        ):
            raise RuntimeError(
                f"candidate independent sight settlement failed: {response}"
            )
        captured = [frame["captured_ms"] for frame in frames]
        if captured != sorted(captured) or len(set(captured)) != len(captured):
            raise RuntimeError("candidate sight frames reordered or overlapped")
        if not all(
            interval_start_ms < value < interval_end_ms
            for value in captured
        ):
            raise RuntimeError(
                "candidate sight frame left its physical PCM interval"
            )
        if (
            prior_interval_end_ms is not None
            and interval_start_ms < prior_interval_end_ms
        ):
            raise RuntimeError(
                "successive candidate sight intervals overlapped or reordered"
            )
        prior_interval_end_ms = interval_end_ms
    return settled


def _validate_records(records: list[dict]) -> list[dict]:
    settled = [
        record
        for record in records
        if isinstance(record.get("response"), dict)
    ]
    if len(settled) < MINIMUM_SETTLED_CHUNKS:
        raise RuntimeError(
            "candidate browser settled only "
            f"{len(settled)} chunks; {MINIMUM_SETTLED_CHUNKS} required"
        )
    for expected_sequence, record in enumerate(settled):
        request = record["request"]
        response = record["response"]
        continuity = response.get("pcm_continuity")
        recognition = response.get("spoken_word_recognition")
        if record["responseStatus"] != 200 or response.get("ok") is not True:
            raise RuntimeError(
                f"candidate settlement {expected_sequence} failed: {response}"
            )
        if (
            request.get("audio_sequence") != expected_sequence
            or request.get("audio_first_sample_index")
            != expected_sequence * PCM_CHUNK_SAMPLES
            or request.get("audio_sample_count") != PCM_CHUNK_SAMPLES
        ):
            raise RuntimeError(
                "candidate browser emitted a discontinuous sample interval"
            )
        if (
            not isinstance(continuity, dict)
            or continuity.get("status") != "contiguous"
            or continuity.get("sequence") != expected_sequence
            or continuity.get("first_sample_index")
            != expected_sequence * PCM_CHUNK_SAMPLES
            or continuity.get("sample_count") != PCM_CHUNK_SAMPLES
        ):
            raise RuntimeError(
                "candidate server did not receipt the exact sample interval"
            )
        channel_mode = request.get("audio_channel_mode")
        if (
            channel_mode not in (
                "single_runtime_channel",
                "discrete_left_projection",
            )
            or continuity.get("channel_mode") != channel_mode
            or continuity.get(
                "binaural_hardware_authority_proven"
            ) is not False
            or continuity.get("room_hearing_authority") is not False
        ):
            raise RuntimeError(
                "candidate active channel crossed its hearing authority"
            )
        if channel_mode == "discrete_left_projection":
            projection = request.get("audio_channel_projection")
            if (
                not isinstance(projection, dict)
                or projection.get("channel") != "left"
                or projection.get("target_mono_stream_id")
                != request.get("audio_stream_id")
                or projection.get(
                    "binaural_hardware_authority_proven"
                ) is not False
                or projection.get("room_hearing_authority") is not False
                or continuity.get(
                    "channel_projection_receipt_sha256"
                ) != projection.get("authority_receipt_sha256")
            ):
                raise RuntimeError(
                    "candidate left-channel provenance was not preserved"
                )
        elif (
            request.get("audio_channel_projection") is not None
            or continuity.get(
                "channel_projection_receipt_sha256"
            ) is not None
        ):
            raise RuntimeError(
                "candidate single channel carried false pair provenance"
            )
        motif = response.get("auditory_motif")
        if (
            not isinstance(recognition, dict)
            or recognition.get("source")
            != "exact_presemantic_recurrent_motif"
            or recognition.get("recognized_form") is not None
            or recognition.get("kind_id") is not None
            or recognition.get("meaning_authority") is not False
            or recognition.get("transcript_authority") is not False
            or not isinstance(motif, dict)
            or motif.get("authority_receipt_sha256")
            != continuity.get(
                "auditory_motif_result_receipt_sha256"
            )
            or continuity.get("meaning_authority") is not False
            or continuity.get("transcript_authority") is not False
        ):
            raise RuntimeError(
                "candidate captured channel did not enter the exact "
                "presemantic recurrent-motif owner"
            )
        if "sound" not in response.get("observed_senses", []):
            raise RuntimeError(
                "candidate full sensory settlement omitted physical sound"
            )
        if "sight_frames" in request:
            raise RuntimeError(
                "candidate continuous sound transport remained coupled to sight"
            )
        if record.get("fetchError"):
            raise RuntimeError(
                f"candidate browser response capture failed: "
                f"{record['fetchError']}"
            )
    return settled


def _validate_recurrent_motif_cognitive_proof(
    settled: list[dict],
) -> dict[str, object]:
    by_sequence = {
        record["request"]["audio_sequence"]: record
        for record in settled
    }
    learning = by_sequence.get(HELLO_LEARNING_SETTLEMENT_SEQUENCE)
    overlap = by_sequence.get(OVERLAP_FIRING_SETTLEMENT_SEQUENCE)
    if learning is None or overlap is None:
        raise RuntimeError(
            "candidate browser did not settle the scheduled independent "
            "Hello learning and Hello-plus-Daddy overlap windows"
        )
    learning_motif = learning["response"].get("auditory_motif")
    overlap_motif = overlap["response"].get("auditory_motif")
    if not isinstance(learning_motif, dict) or not isinstance(
        overlap_motif, dict
    ):
        raise RuntimeError(
            "candidate browser cognitive windows lost typed motif results"
        )
    grown = frozenset(
        learning_motif.get("newly_grown_motif_neuron_ids", ())
    )
    overlap_firing = frozenset(
        overlap_motif.get("firing_motif_neuron_ids", ())
    )
    co_firing = tuple(sorted(grown.intersection(overlap_firing)))
    if not grown:
        raise RuntimeError(
            "two independent live Hello experiences grew no exact motif"
        )
    if not co_firing:
        raise RuntimeError(
            "the learned live Hello motif did not fire inside the equal-gain "
            "Hello-plus-Daddy overlap"
        )
    overlap_event_activation_ids = {
        span.get("motif_neuron_id")
        for span in overlap_motif.get("activation_spans", ())
        if isinstance(span, dict)
        and isinstance(span.get("source_index_start"), int)
        and isinstance(span.get("source_index_end"), int)
        and span["source_index_start"] < 600
        and span["source_index_end"] >= 200
    }
    evidenced_co_firing = tuple(sorted(
        set(co_firing).intersection(overlap_event_activation_ids)
    ))
    if not evidenced_co_firing:
        raise RuntimeError(
            "overlap co-firing lost its exact full-field activation span "
            "inside the scheduled mixed event"
        )
    return {
        "hello_growth_sequence": HELLO_LEARNING_SETTLEMENT_SEQUENCE,
        "hello_grown_motif_neuron_ids": sorted(grown),
        "overlap_sequence": OVERLAP_FIRING_SETTLEMENT_SEQUENCE,
        "overlap_firing_motif_neuron_ids": sorted(overlap_firing),
        "hello_overlap_co_firing_motif_neuron_ids": list(
            evidenced_co_firing
        ),
        "meaning_authority": False,
        "transcript_authority": False,
    }


def _validate_binaural_records(
    records: list[dict],
    lineages: list[dict],
    sound_records: list[dict],
    *,
    binaural_active: bool,
    require_distinct_pair: bool = False,
    inflight_pair_limit: int = 0,
) -> list[dict]:
    settled = [
        record
        for record in records
        if isinstance(record.get("response"), dict)
    ]
    settled_lineages = [
        record
        for record in lineages
        if isinstance(record.get("response"), dict)
    ]
    if not binaural_active:
        if settled:
            raise RuntimeError(
                "inactive candidate pair emitted binaural PCM"
            )
        if any(
            record["request"].get("audio_channel_mode")
            != "single_runtime_channel"
            for record in sound_records
        ):
            raise RuntimeError(
                "single-channel candidate claimed pair provenance"
            )
        return []
    if len(settled_lineages) != 1:
        raise RuntimeError(
            "candidate pair has no unique runtime channel lineage"
        )
    lineage_request = settled_lineages[0]["request"]
    lineage_response = settled_lineages[0]["response"]
    if (
        settled_lineages[0].get("responseStatus") != 200
        or lineage_response.get("ok") is not True
        or lineage_request.get("media_track_channel_count") != 2
        or lineage_request.get("worklet_input_channel_count") != 2
        or lineage_request.get("channel_order") != ["left", "right"]
        or lineage_response.get(
            "binaural_hardware_authority_proven"
        ) is not False
        or lineage_response.get("cognition_authority") is not False
    ):
        raise RuntimeError(
            "candidate pair lineage crossed its unproven boundary"
        )
    trailing_pairs = len(settled) - len(sound_records)
    if (
        trailing_pairs < 0
        or trailing_pairs > inflight_pair_limit
    ):
        raise RuntimeError(
            "candidate pair and active hearing lost interval correlation: "
            f"pair={len(settled)}, hearing={len(sound_records)}, "
            f"inflight_limit={inflight_pair_limit}"
        )
    for expected_sequence, (pair, sound) in enumerate(
        zip(
            settled[:len(sound_records)],
            sound_records,
            strict=True,
        )
    ):
        request = pair["request"]
        response = pair["response"]
        continuity = response.get("continuity")
        room = response.get("room_hearing")
        projection = response.get("left_channel_projection")
        sound_request = sound["request"]
        if (
            pair.get("responseStatus") != 200
            or response.get("ok") is not True
            or request.get("sequence") != expected_sequence
            or request.get("first_sample_index")
            != expected_sequence * PCM_CHUNK_SAMPLES
            or (
                require_distinct_pair
                and request.get("left_pcm_b64")
                == request.get("right_pcm_b64")
            )
            or not isinstance(continuity, dict)
            or continuity.get("status") != "contiguous"
            or continuity.get("sequence") != expected_sequence
        ):
            raise RuntimeError(
                "candidate discrete pair was averaged, duplicated, "
                "or discontinuous"
            )
        if (
            response.get(
                "binaural_hardware_authority_proven"
            ) is not False
            or not isinstance(room, dict)
            or room.get("state")
            != "refused_unproven_browser_hardware"
            or room.get("authority") is not False
            or room.get(
                "full_field_occurrence_receipt_sha256s"
            ) != []
            or response.get(
                "production_exact_room_hearing_wired"
            ) is not False
            or response.get("cognition_authority") is not False
            or response.get("meaning_authority") is not False
        ):
            raise RuntimeError(
                "candidate pair gained false room-hearing authority"
            )
        if (
            not isinstance(projection, dict)
            or projection
            != sound_request.get("audio_channel_projection")
            or sound_request.get("audio_channel_mode")
            != "discrete_left_projection"
            or request.get("target_mono_stream_id")
            != sound_request.get("audio_stream_id")
        ):
            raise RuntimeError(
                "candidate pair did not feed its signed left channel "
                "into active hearing"
            )
        if pair.get("fetchError"):
            raise RuntimeError(
                "candidate pair response capture failed: "
                f"{pair['fetchError']}"
            )
    return settled[:len(sound_records)]


def _acceptance_half_diagnostics(
    *,
    records: list[dict],
    status_samples: list[dict],
    proof_seconds: int,
) -> list[dict[str, object]]:
    """Summarize each exact half even when final acceptance fails."""

    half_seconds = proof_seconds / 2
    diagnostics = []
    for half_index in range(2):
        start_ms = half_index * half_seconds * 1000
        end_ms = (half_index + 1) * half_seconds * 1000
        samples = [
            value
            for value in status_samples
            if isinstance(value.get("proofElapsedMs"), (int, float))
            and start_ms <= value["proofElapsedMs"] < end_ms
        ]
        requested = [
            value
            for value in records
            if isinstance(value.get("requestedAtMs"), (int, float))
            and isinstance(value.get("proofStartedAtMs"), (int, float))
            and start_ms
            <= value["requestedAtMs"] - value["proofStartedAtMs"]
            < end_ms
        ]
        settled = [
            value
            for value in records
            if isinstance(value.get("responseAtMs"), (int, float))
            and isinstance(value.get("proofStartedAtMs"), (int, float))
            and start_ms
            <= value["responseAtMs"] - value["proofStartedAtMs"]
            < end_ms
        ]
        response_seconds = [
            (value["responseAtMs"] - value["requestedAtMs"]) / 1000
            for value in settled
            if isinstance(value.get("requestedAtMs"), (int, float))
        ]
        groups = [
            value["residentGroups"]
            for value in samples
            if isinstance(value.get("residentGroups"), dict)
        ]
        prediction = [
            value["predictionStatus"]
            for value in samples
            if isinstance(value.get("predictionStatus"), dict)
        ]
        pending_chunks = [
            value["pendingChunks"]
            for value in samples
            if isinstance(value.get("pendingChunks"), int)
        ]
        sequences = [
            value.get("request", {}).get("audio_sequence")
            for value in settled
        ]
        discontinuities = sum(
            not isinstance(value, int)
            for value in sequences
        ) + sum(
            right != left + 1
            for left, right in zip(sequences, sequences[1:])
            if isinstance(left, int) and isinstance(right, int)
        )
        diagnostics.append({
            "half": half_index + 1,
            "interval_seconds": [half_index * half_seconds, (half_index + 1) * half_seconds],
            "requested_chunks": len(requested),
            "settled_chunks": len(settled),
            "settled_chunks_per_second": (
                len(settled) / half_seconds
            ),
            "response_seconds": {
                "minimum": min(response_seconds) if response_seconds else None,
                "mean": (
                    sum(response_seconds) / len(response_seconds)
                    if response_seconds else None
                ),
                "maximum": max(response_seconds) if response_seconds else None,
            },
            "maximum_pending_chunks": (
                max(pending_chunks) if pending_chunks else None
            ),
            "discontinuities": discontinuities,
            "microphone_stopped_samples": sum(
                value.get("microphoneActive") is not True
                for value in samples
            ),
            "candidate_engine_rss": {
                "first": groups[0]["candidate_engine_bytes"] if groups else None,
                "last": groups[-1]["candidate_engine_bytes"] if groups else None,
                "maximum": (
                    max(value["candidate_engine_bytes"] for value in groups)
                    if groups else None
                ),
            },
            "exact_worker_rss": {
                "first": groups[0]["exact_worker_bytes"] if groups else None,
                "last": groups[-1]["exact_worker_bytes"] if groups else None,
                "maximum": (
                    max(value["exact_worker_bytes"] for value in groups)
                    if groups else None
                ),
            },
            "prediction_first": prediction[0] if prediction else None,
            "prediction_last": prediction[-1] if prediction else None,
        })
    return diagnostics


def run_probe(*, wav_path: Path | None, proof_seconds: int) -> dict:
    _configure_candidate_environment()
    import dsf_ai_service.app as app_module

    schedule = build_cognitive_proof_wav()
    if wav_path is None:
        wav_path = schedule["wav_path"]
    if not isinstance(wav_path, Path) or not wav_path.is_file():
        raise FileNotFoundError(f"known microphone WAV is absent: {wav_path}")
    with wave.open(str(wav_path), "rb") as supplied:
        if (
            supplied.getnchannels() != 1
            or supplied.getsampwidth() != 2
            or supplied.getframerate() != PCM_SAMPLE_RATE_HZ
            or supplied.getnframes() != schedule["sample_count"]
        ):
            raise RuntimeError(
                "fake-microphone WAV differs from the authenticated "
                "cognitive schedule"
            )
        supplied_pcm = supplied.readframes(supplied.getnframes())
    if hashlib.sha256(supplied_pcm).hexdigest() != schedule["pcm_sha256"]:
        raise RuntimeError(
            "fake-microphone PCM differs from the authenticated cognitive "
            "schedule"
        )
    if proof_seconds < PROOF_SECONDS:
        raise ValueError(
            f"candidate browser proof must run for at least {PROOF_SECONDS}s"
        )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "candidate browser proof requires the Python Playwright package"
        ) from error
    reviewed_html = PAGE.read_bytes()
    reviewed_sha256 = hashlib.sha256(reviewed_html).hexdigest()
    reviewed_source = reviewed_html.decode("utf-8")
    if (
        "sample/=channels.length;" in reviewed_source
        or "GualaDiscreteBinauralPCMTransport" not in reviewed_source
        or "audio_channel_mode:channelProjection?" not in reviewed_source
        or (
            "presemantic auditory motifs were flattened into a word or kind"
            not in reviewed_source
        )
        or "/api/v1/auditory/reply/" in reviewed_source
    ):
        raise RuntimeError(
            "reviewed browser artifact violates the hearing contract"
        )
    exact_field_owner = start_exact_field_executor()
    exact_field_owner.assert_healthy()
    engine = Guala()
    _install_candidate_globals(engine)
    port = _free_port()
    candidate_origin = f"http://127.0.0.1:{port}"
    page_url = f"{candidate_origin}/gualaloom"
    server = _start_candidate(port)
    initial_breakdown = _tree_rss_breakdown()
    initial_groups = _resident_groups(initial_breakdown)
    initial_rss = initial_groups["tree_bytes"]
    status_samples = []
    console_errors = []
    http_errors = []
    try:
        fetched_html = _wait_for_candidate(page_url, server)
        fetched_sha256 = hashlib.sha256(fetched_html).hexdigest()
        if fetched_sha256 != reviewed_sha256:
            raise RuntimeError(
                "candidate browser did not fetch the reviewed HTML artifact"
            )
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                    f"--use-file-for-fake-audio-capture={wav_path}",
                ],
            )
            context = browser.new_context()
            context.grant_permissions(
                ["camera", "microphone"],
                origin=candidate_origin,
            )
            page = context.new_page()
            page.add_init_script(
                _browser_instrumentation(candidate_origin)
            )
            page.on(
                "console",
                lambda message: console_errors.append(message.text)
                if message.type == "error"
                else None,
            )
            page.on(
                "response",
                lambda response: http_errors.append({
                    "status": response.status,
                    "url": response.url,
                })
                if response.status >= 400
                else None,
            )
            page.goto(page_url, wait_until="domcontentloaded")
            page.locator("#mic-perm").click()
            try:
                page.wait_for_function(
                    "() => Boolean(micPCMActive&&micEpoch&&micEpoch.active)",
                    timeout=30_000,
                )
            except Exception as error:
                raise RuntimeError(
                    "candidate microphone did not start; "
                    f"status={_status_snapshot(page)}; "
                    f"console_errors={console_errors}; "
                    f"http_errors={http_errors}"
                ) from error
            page.evaluate(
                "() => { window.__candidateProofStartedAtMs=performance.now(); }"
            )
            deadline = time.monotonic() + proof_seconds
            while time.monotonic() < deadline:
                page.wait_for_timeout(500)
                snapshot = _status_snapshot(page)
                snapshot["predictionStatus"] = (
                    engine._full_field_prediction.status()
                    if engine._full_field_prediction is not None
                    else None
                )
                snapshot["retainedOwners"] = _retained_owner_status(
                    engine
                )
                breakdown = _tree_rss_breakdown()
                snapshot["residentGroups"] = _resident_groups(
                    breakdown
                )
                snapshot["treeResidentBytes"] = snapshot[
                    "residentGroups"
                ]["tree_bytes"]
                status_samples.append(snapshot)
            final_status = _status_snapshot(page)
            registry_status = app_module._auditory_pcm_streams.status()
            binaural_registry_status = (
                app_module._browser_binaural_pcm_streams.status()
            )
            drain_summary = _stop_admission_and_drain(page)
            records = drain_summary.pop("soundRecords")
            binaural_records = drain_summary.pop("binauralRecords")
            drained_registry_status = (
                app_module._auditory_pcm_streams.status()
            )
            drained_binaural_registry_status = (
                app_module._browser_binaural_pcm_streams.status()
            )
            proof_started_at_ms = page.evaluate(
                "() => window.__candidateProofStartedAtMs"
            )
            for record in records:
                record["proofStartedAtMs"] = proof_started_at_ms
            binaural_lineages = page.evaluate(
                "() => window.__candidateBinauralLineages"
            )
            sight_records = page.evaluate("() => window.__candidateSightFrames")
            fetch_errors = page.evaluate("() => window.__candidateFetchErrors")
            designation_messages = page.evaluate(
                """() => Array.from(
                  document.querySelectorAll('.msg.system')
                ).map(value=>value.textContent).filter(
                  value=>value.startsWith(
                    'recognized learned sound form:'
                  )
                )"""
            )
            forbidden_hearing_messages = page.evaluate(
                """() => Array.from(
                  document.querySelectorAll('.msg.user,.msg.system')
                ).map(value=>value.textContent).filter(value=>
                  value.startsWith('heard:')||
                  value.startsWith('replying to:')||
                  value.includes('no learned causal action for:')
                )"""
            )
            half_diagnostics = _acceptance_half_diagnostics(
                records=records,
                status_samples=status_samples,
                proof_seconds=proof_seconds,
            )
            print(
                "[candidate-acceptance-diagnostics] "
                + json.dumps(
                    half_diagnostics,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                flush=True,
            )
            try:
                settled = _validate_records(records)
            except RuntimeError as error:
                sound_diagnostics = [
                    {
                        "audio_channel_mode": record.get(
                            "request", {}
                        ).get("audio_channel_mode"),
                        "observed_senses": record.get(
                            "response"
                        ).get("observed_senses")
                        if isinstance(record.get("response"), dict)
                        else None,
                        "pcm_continuity": (
                            record["response"].get("pcm_continuity")
                            if isinstance(
                                record.get("response"), dict
                            )
                            else None
                        ),
                        "recognition_source": (
                            record["response"].get(
                            "spoken_word_recognition", {}
                            ).get("source")
                            if isinstance(
                                record.get("response"), dict
                            )
                            else None
                        )
                    }
                    for record in records[:3]
                ]
                binaural_diagnostics = [
                    {
                        "channels_distinct": record.get(
                            "request", {}
                        ).get("left_pcm_b64")
                        != record.get("request", {}).get(
                            "right_pcm_b64"
                        ),
                        "binaural_hardware_authority_proven": (
                            record.get("response", {}).get(
                                "binaural_hardware_authority_proven"
                            )
                        ),
                        "room_hearing": record.get(
                            "response", {}
                        ).get("room_hearing"),
                        "cognition_authority": record.get(
                            "response", {}
                        ).get("cognition_authority"),
                        "meaning_authority": record.get(
                            "response", {}
                        ).get("meaning_authority"),
                    }
                    for record in binaural_records[:3]
                ]
                raise RuntimeError(
                    f"{error}; final_status={final_status}; "
                    f"captured_sound_requests={len(records)}; "
                    f"captured_binaural_requests="
                    f"{len(binaural_records)}; "
                    f"sound_diagnostics={sound_diagnostics}; "
                    f"binaural_diagnostics={binaural_diagnostics}"
                ) from error
            schedule_transport = (
                _validate_cognitive_schedule_transport(
                    settled,
                    schedule,
                )
            )
            cognitive_proof = _validate_recurrent_motif_cognitive_proof(
                settled
            )
            settled_binaural = _validate_binaural_records(
                binaural_records,
                binaural_lineages,
                settled,
                binaural_active=final_status["binauralActive"],
            )
            if sight_records:
                raise RuntimeError(
                    "auditory cognitive proof unexpectedly admitted sight"
                )
            settled_sight = []
            if forbidden_hearing_messages:
                raise RuntimeError(
                    "candidate browser rendered a legacy hearing/reply "
                    f"surface: {forbidden_hearing_messages}"
                )
            if designation_messages:
                raise RuntimeError(
                    "candidate browser displayed a presemantic motif as a "
                    "learned word"
                )
            if fetch_errors:
                raise RuntimeError(
                    f"candidate browser instrumentation failed: {fetch_errors}"
                )
            unstarted_v7_polls = [
                value
                for value in http_errors
                if (
                    value["status"] == 404
                    and "/v7/state?session_id=" in value["url"]
                )
            ]
            unexpected_http_errors = [
                value
                for value in http_errors
                if value not in unstarted_v7_polls
            ]
            if (
                unexpected_http_errors
                or len(console_errors) != len(unstarted_v7_polls)
            ):
                raise RuntimeError(
                    "candidate browser console errors: "
                    f"{console_errors}; unexpected HTTP errors: "
                    f"{unexpected_http_errors}; explicitly observed "
                    f"unstarted v7 polls: {unstarted_v7_polls}"
                )
            if not final_status["microphoneActive"]:
                raise RuntimeError("candidate microphone did not remain active")
            if final_status["microphoneTracks"] != ["live"]:
                raise RuntimeError("candidate microphone track did not remain live")
            if final_status["cameraTracks"]:
                raise RuntimeError(
                    "candidate auditory proof unexpectedly opened camera"
                )
            maximum_pending = max(
                value["pendingChunks"]
                for value in status_samples
                if isinstance(value["pendingChunks"], int)
            )
            if maximum_pending >= PCM_TRANSPORT_UNITS:
                raise RuntimeError(
                    "candidate browser reached its pending-window failure wall"
                )
            if final_status["pendingChunks"] > 2:
                raise RuntimeError(
                    "candidate browser accumulated more than one active and "
                    "one newly admitted physical sound interval"
                )
            motif_resource_samples = [
                value["retainedOwners"]["auditory_recurrent_motif"]
                for value in status_samples
            ]
            motif_resource_violations = [
                sample
                for sample in motif_resource_samples
                if (
                    sample[
                        "maximum_pending_transport_units_in_one_stream"
                    ]
                    > sample[
                        "max_pending_transport_units_per_stream"
                    ]
                    or sample[
                        "pending_independent_experience_count"
                    ]
                    > sample[
                        "pending_independent_experience_capacity"
                    ]
                )
            ]
            if motif_resource_violations:
                raise RuntimeError(
                    "candidate recurrent-motif owner exceeded its exact "
                    "per-stream transport or experience allocation: "
                    f"{motif_resource_violations[-1]}"
                )
            failure_statuses = [
                value
                for value in status_samples
                if any(
                    marker in (
                        value["microphoneStatus"]
                        + " "
                        + value["cameraStatus"]
                    ).lower()
                    for marker in (
                        "fell behind",
                        "raw sound stopped",
                        "raw sight failed",
                        "raw sight rejected",
                    )
                )
            ]
            if failure_statuses:
                raise RuntimeError(
                    f"candidate browser reported sensory failure: "
                    f"{failure_statuses[-1]}"
                )
            if (
                registry_status["active_streams"] != 1
                or registry_status["retained_pcm_bytes"] > PCM_RING_BYTES
            ):
                raise RuntimeError(
                    "candidate server exceeded its bounded PCM ring"
                )
            expected_binaural_streams = (
                1 if final_status["binauralActive"] else 0
            )
            if (
                binaural_registry_status["active_streams"]
                != expected_binaural_streams
                or binaural_registry_status["retained_pcm_bytes"]
                > BINAURAL_RING_BYTES_PER_STREAM
                * expected_binaural_streams
            ):
                raise RuntimeError(
                    "candidate server exceeded its bounded pair ring"
                )
            if (
                drained_registry_status["active_streams"] != 0
                or drained_binaural_registry_status[
                    "active_streams"
                ] != 0
            ):
                raise RuntimeError(
                    "candidate server retained a capture owner after "
                    "bounded microphone drain"
                )
            final_breakdown = _tree_rss_breakdown()
            final_groups = _resident_groups(final_breakdown)
            final_rss = final_groups["tree_bytes"]
            resident_samples = [
                value["treeResidentBytes"]
                for value in status_samples
            ]
            resident_quartiles = [
                resident_samples[
                    min(
                        len(resident_samples) - 1,
                        len(resident_samples) * numerator // 4,
                    )
                ]
                for numerator in (1, 2, 3)
            ]
            result = {
                "reviewed_html_sha256": reviewed_sha256,
                "fetched_html_sha256": fetched_sha256,
                "proof_seconds": proof_seconds,
                "settled_chunks": len(settled),
                "recurrent_motif_cognitive_proof": cognitive_proof,
                "authenticated_cognitive_schedule": {
                    "pcm_sha256": schedule["pcm_sha256"],
                    "sample_count": schedule["sample_count"],
                    "source_pcm_sha256s": list(
                        schedule["source_pcm_sha256s"]
                    ),
                    "transport": schedule_transport,
                },
                "settled_binaural_chunks": len(settled_binaural),
                "binaural_channel_bytes_distinct": (
                    bool(settled_binaural)
                    and all(
                        record["request"]["left_pcm_b64"]
                        != record["request"]["right_pcm_b64"]
                        for record in settled_binaural
                    )
                ),
                "settled_sight_fields": len(settled_sight),
                "settled_samples": (
                    len(settled) * PCM_CHUNK_SAMPLES
                ),
                "first_sample_index": settled[0]["request"][
                    "audio_first_sample_index"
                ],
                "last_sample_index_exclusive": (
                    settled[-1]["request"]["audio_first_sample_index"]
                    + settled[-1]["request"]["audio_sample_count"]
                ),
                "maximum_pending_chunks": maximum_pending,
                "maximum_pending_motif_transport_units": max(
                    sample["pending_transport_units"]
                    for sample in motif_resource_samples
                ),
                "maximum_pending_motif_experiences": max(
                    sample["pending_independent_experience_count"]
                    for sample in motif_resource_samples
                ),
                "microphone_status": final_status["microphoneStatus"],
                "input_channel_count": final_status[
                    "inputChannelCount"
                ],
                "binaural_transport_active": final_status[
                    "binauralActive"
                ],
                "capture_drain": drain_summary,
                "active_channel_modes": sorted({
                    record["request"]["audio_channel_mode"]
                    for record in settled
                }),
                "camera_status": final_status["cameraStatus"],
                "microphone_tracks": final_status["microphoneTracks"],
                "camera_tracks": final_status["cameraTracks"],
                "krimelack_designation_messages": (
                    designation_messages
                ),
                "unstarted_v7_poll_count": len(unstarted_v7_polls),
                "registry": registry_status,
                "binaural_registry": binaural_registry_status,
                "drained_registry": drained_registry_status,
                "drained_binaural_registry": (
                    drained_binaural_registry_status
                ),
                "authority_boundary": {
                    "binaural_hardware_authority_proven": False,
                    "room_hearing_authority": False,
                    "separation_authority": False,
                    "meaning_authority": False,
                    "transcript_authority": False,
                },
                "initial_resident_bytes": initial_rss,
                "initial_resident_groups": initial_groups,
                "initial_tree_resident_breakdown": initial_breakdown,
                "final_resident_bytes": final_rss,
                "final_resident_groups": final_groups,
                "resident_growth_bytes": final_rss - initial_rss,
                "maximum_tree_resident_bytes": max(
                    value["treeResidentBytes"]
                    for value in status_samples
                ),
                "tree_resident_quartiles": resident_quartiles,
                "resident_group_samples": [
                    value["residentGroups"]
                    for value in status_samples
                ],
                "retained_owner_samples": [
                    value["retainedOwners"]
                    for value in status_samples
                ],
                "acceptance_halves": half_diagnostics,
                "final_tree_resident_breakdown": final_breakdown,
                "full_field_prediction_status": (
                    engine._full_field_prediction.status()
                    if engine._full_field_prediction is not None
                    else None
                ),
                "causal_action_cycle_status": (
                    engine._causal_action_cycle.status()
                    if engine._causal_action_cycle is not None
                    else None
                ),
            }
            page.locator("#mic-perm").click()
            context.close()
            browser.close()
            return result
    finally:
        server.should_exit = True
        thread = getattr(server, "_candidate_thread", None)
        if isinstance(thread, threading.Thread):
            thread.join(timeout=30)
        engine.shutdown()
        stop_exact_field_executor()


def run_live_probe(*, wav_path: Path | None, proof_seconds: int) -> dict:
    """Run the same authenticated cognitive proof against dsf-ai.com."""

    if proof_seconds < PROOF_SECONDS:
        raise ValueError(
            f"live browser proof must run for at least {PROOF_SECONDS}s"
        )
    schedule = build_cognitive_proof_wav()
    if wav_path is None:
        wav_path = schedule["wav_path"]
    if not isinstance(wav_path, Path) or not wav_path.is_file():
        raise FileNotFoundError(f"known microphone WAV is absent: {wav_path}")
    with wave.open(str(wav_path), "rb") as supplied:
        supplied_pcm = supplied.readframes(supplied.getnframes())
        supplied_shape = (
            supplied.getnchannels(),
            supplied.getsampwidth(),
            supplied.getframerate(),
            supplied.getnframes(),
        )
    if (
        supplied_shape
        != (1, 2, PCM_SAMPLE_RATE_HZ, schedule["sample_count"])
        or hashlib.sha256(supplied_pcm).hexdigest()
        != schedule["pcm_sha256"]
    ):
        raise RuntimeError(
            "live fake-microphone WAV differs from the authenticated "
            "cognitive schedule"
        )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "live browser proof requires the Python Playwright package"
        ) from error
    live_origin = "https://dsf-ai.com"
    page_url = f"{live_origin}/gualaloom.html"
    reviewed_sha256 = hashlib.sha256(PAGE.read_bytes()).hexdigest()
    with urllib.request.urlopen(page_url, timeout=30) as response:
        deployed_sha256 = hashlib.sha256(response.read()).hexdigest()
    if deployed_sha256 != reviewed_sha256:
        raise RuntimeError(
            "deployed Guala page differs from the reviewed local artifact"
        )
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                f"--use-file-for-fake-audio-capture={wav_path}",
            ],
        )
        context = browser.new_context()
        context.grant_permissions(["microphone"], origin=live_origin)
        page = context.new_page()
        page.add_init_script(
            _browser_instrumentation(PRODUCTION_API_ORIGIN)
        )
        page.goto(page_url, wait_until="domcontentloaded")
        page.locator("#mic-perm").click()
        page.wait_for_function(
            "() => Boolean(micPCMActive&&micEpoch&&micEpoch.active)",
            timeout=30_000,
        )
        deadline = time.monotonic() + proof_seconds
        maximum_pending = 0
        while time.monotonic() < deadline:
            page.wait_for_timeout(500)
            status = _status_snapshot(page)
            if isinstance(status["pendingChunks"], int):
                maximum_pending = max(
                    maximum_pending, status["pendingChunks"]
                )
        drain = _stop_admission_and_drain(page)
        records = drain.pop("soundRecords")
        settled = _validate_records(records)
        schedule_transport = (
            _validate_cognitive_schedule_transport(
                settled,
                schedule,
            )
        )
        cognition = _validate_recurrent_motif_cognitive_proof(settled)
        motif_statuses = [
            record["response"]["auditory_l5"]["recurrent_motif"]
            for record in settled
        ]
        if any(
            status["pending_transport_units"]
            > (
                status["max_pending_transport_units_per_stream"]
                * status["active_terminal_streams"]
            )
            or status["pending_independent_experience_count"]
            > status["pending_independent_experience_capacity"]
            for status in motif_statuses
        ):
            raise RuntimeError(
                "deployed recurrent-motif owner exceeded bounded state"
            )
        result = {
            "deployed_html_sha256": deployed_sha256,
            "authenticated_cognitive_schedule_pcm_sha256": (
                schedule["pcm_sha256"]
            ),
            "authenticated_cognitive_schedule_transport": (
                schedule_transport
            ),
            "recurrent_motif_cognitive_proof": cognition,
            "settled_chunks": len(settled),
            "maximum_browser_pending_chunks": maximum_pending,
            "maximum_pending_motif_transport_units": max(
                status["pending_transport_units"]
                for status in motif_statuses
            ),
            "maximum_pending_motif_experiences": max(
                status["pending_independent_experience_count"]
                for status in motif_statuses
            ),
            "capture_drain": drain,
        }
        context.close()
        browser.close()
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wav",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=PROOF_SECONDS,
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="prove the deployed https://dsf-ai.com/gualaloom.html artifact",
    )
    args = parser.parse_args()
    runner = run_live_probe if args.live else run_probe
    result = runner(wav_path=args.wav, proof_seconds=args.seconds)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
