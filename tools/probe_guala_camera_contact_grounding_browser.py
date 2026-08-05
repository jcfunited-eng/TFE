#!/usr/bin/env python3
"""Real-Chromium proof of custody-native live-camera contact grounding.

The reviewed Guala page owns both capture paths.  Its microphone and camera
remain independent physical clocks.  This probe supplies Chromium's fake
microphone WAV and native fake camera, but it never injects a sensory request,
transcript, label, object identity, or meaning claim.

One W1 object is already held through authenticated physical custody before
capture.  The first camera occurrence must remain unresolved.  The probe then
POSTs an authenticated, exactly empty grounding operation.  A later camera
occurrence must resolve the same THING, and the same result must survive a
cold engine restoration.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_RING_BYTES,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    THING_SENSORY_EXPANSION_CONSUMER_ID,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    PickCommand,
    encode_command,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_guala_candidate_browser import (
    MINIMUM_SETTLED_CHUNKS,
    PAGE,
    _browser_instrumentation,
    _configure_candidate_environment,
    _free_port,
    _install_candidate_globals,
    _resident_groups,
    _start_candidate,
    _status_snapshot,
    _stop_admission_and_drain,
    _tree_rss_breakdown,
    _validate_records,
    _validate_visual_intervals,
    _wait_for_candidate,
    build_cognitive_proof_wav,
)


GROUNDING_PATH = "/api/v1/embodiment/ground-latest-sight-contact"
GROUNDING_SCHEMA = (
    "guala.live_sight.lived_contact_grounding.observation.v1"
)
PROOF_SCHEMA = "guala.live_camera.contact_grounding.browser_proof.v1"
API_KEY = "camera-contact-browser-proof-control-key-v1"
ENGINE_KEY = "camera-contact-browser-proof-engine-key-v1"
MINIMUM_LIVE_SIGHT_OCCURRENCES = 2
MAXIMUM_PROOF_SECONDS = 180
SHA256_HEX = frozenset("0123456789abcdef")
CAMERA_WIDTH = 128
CAMERA_HEIGHT = 128


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in SHA256_HEX for character in value)
    ):
        raise RuntimeError(f"{label} is not a SHA-256 receipt")
    return value


def _directory_bytes(root: str) -> int:
    return sum(
        entry.stat().st_size
        for entry in Path(root).rglob("*")
        if entry.is_file()
    )


def build_authenticated_camera_source(path: Path) -> dict[str, object]:
    """Write one nonuniform physical light field as a looping Y4M source."""

    if not isinstance(path, Path):
        raise TypeError("camera source path must be typed")
    header = (
        f"YUV4MPEG2 W{CAMERA_WIDTH} H{CAMERA_HEIGHT} "
        "F30:1 Ip A1:1 C420jpeg\n"
    ).encode("ascii")
    luminance = bytes(
        (
            row * 17
            + column * 29
            + ((row // 8) ^ (column // 8)) * 11
        ) % 220 + 16
        for row in range(CAMERA_HEIGHT)
        for column in range(CAMERA_WIDTH)
    )
    chroma_width = CAMERA_WIDTH // 2
    chroma_height = CAMERA_HEIGHT // 2
    chroma_u = bytes(
        (row * 7 + column * 13) % 224 + 16
        for row in range(chroma_height)
        for column in range(chroma_width)
    )
    chroma_v = bytes(
        (row * 19 + column * 5) % 224 + 16
        for row in range(chroma_height)
        for column in range(chroma_width)
    )
    frame = b"FRAME\n" + luminance + chroma_u + chroma_v
    encoded = header + frame * 30
    path.write_bytes(encoded)
    return {
        "byte_count": len(encoded),
        "height": CAMERA_HEIGHT,
        "path": path,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "width": CAMERA_WIDTH,
    }


def _activate_local_hot_files(state_dir: str):
    """Publish every verified staged file into one disposable state root."""

    def activate(**values) -> None:
        replacements: list[tuple[str, str]] = []
        for relative_path, source_path in sorted(values["files"].items()):
            destination = os.path.join(state_dir, relative_path)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            replacement = destination + ".verified-camera-grounding"
            shutil.copy2(source_path, replacement)
            replacements.append((replacement, destination))
        for replacement, destination in sorted(
            replacements,
            key=lambda value: (
                os.path.basename(value[1]) == "guala_core.json"
            ),
        ):
            os.replace(replacement, destination)

    return activate


def _establish_contact_grounded_thing(engine: Guala):
    before = engine._embodiment_world.observation_snapshot()
    execution = engine._embodiment_world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(PickCommand("W1-object-1")),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )
    if execution.disposition != "applied":
        raise RuntimeError("W1 did not apply the physical Pick occurrence")
    mount = engine._w1_physical_evidence.mount_action_outcome(execution)
    engine._w1_physical_evidence.verify_mount(mount)
    custody = engine._settled_prediction_custody(
        mount,
        world_execution=execution,
    )
    thing = engine._admit_thing_genesis_from_custody(custody)
    after = engine._embodiment_world.observation_snapshot()
    held_object_ids = tuple(
        value.object_id
        for value in after.objects
        if value.held_by_body_id == after.self_body_id
    )
    if held_object_ids != ("W1-object-1",):
        raise RuntimeError("physical W1 contact did not remain held")
    return thing, mount


def _assert_complete_sight_custody(engine: Guala):
    latest = engine._latest_live_sight_custody
    if not isinstance(latest, tuple) or len(latest) != 2:
        raise RuntimeError("camera occurrence has no live sight custody")
    custody, capability = latest
    engine._retained_audiovisual_custody.verify_custody(custody)
    if custody.canonical_audio_sha256 is not None:
        raise RuntimeError("standalone camera custody gained audio")
    if capability.consumer_id != THING_SENSORY_EXPANSION_CONSUMER_ID:
        raise RuntimeError("camera grounding capability changed consumer")
    if (
        engine._retained_audiovisual_custody.open_child(capability)
        is not custody
    ):
        raise RuntimeError("camera grounding capability crossed custody")
    observed = tuple(
        interpretation
        for interpretation in custody.settlement.interpretations
        if interpretation.state == "observed"
    )
    if tuple(value.sense for value in observed) != ("sight",):
        raise RuntimeError("standalone camera settlement changed senses")
    if not all(
        tuple(name for name, _field in field_tuple.fields)
        == DSF_FIELD_ORDER
        for interpretation in observed
        for substream in interpretation.substreams
        for field_tuple in substream.field_tuples
    ):
        raise RuntimeError("camera settlement flattened the DSF field")
    roots = full_field_sensory_roots(custody.settlement)
    if not roots or {root.sense for root in roots} != {"sight"}:
        raise RuntimeError("camera settlement lost its full-field roots")
    return custody, capability, roots


def _settled_sight_records(page) -> list[dict[str, object]]:
    records = page.evaluate("() => window.__candidateSightFrames")
    return [
        value
        for value in records
        if isinstance(value, dict)
        and isinstance(value.get("response"), dict)
    ]


def _wait_for_settled_sights(page, count: int, timeout_ms: int) -> None:
    page.wait_for_function(
        """required => (
          Array.isArray(window.__candidateSightFrames)&&
          window.__candidateSightFrames.filter(
            value=>value&&value.response!==null
          ).length>=required
        )""",
        arg=count,
        timeout=timeout_ms,
    )


def _validate_camera_record(
    record: dict[str, object],
    *,
    expected_state: str,
    expected_thing_ids: list[str],
) -> dict[str, str]:
    request = record["request"]
    response = record["response"]
    if set(request) != {
        "capture_ended_ms",
        "capture_started_ms",
        "command",
        "sight_frames",
        "text",
    }:
        raise RuntimeError("page camera request shape changed")
    if request["text"] != "" or request["command"] != "":
        raise RuntimeError("page camera request gained semantic input")
    frames = request.get("sight_frames")
    capture_started_ms = request.get("capture_started_ms")
    capture_ended_ms = request.get("capture_ended_ms")
    if (
        not isinstance(frames, list)
        or len(frames) < 4
        or isinstance(capture_started_ms, bool)
        or not isinstance(capture_started_ms, int)
        or isinstance(capture_ended_ms, bool)
        or not isinstance(capture_ended_ms, int)
        or capture_ended_ms <= capture_started_ms
    ):
        raise RuntimeError("page camera interval changed")
    captured = [frame.get("captured_ms") for frame in frames]
    if (
        any(
            isinstance(value, bool) or not isinstance(value, int)
            for value in captured
        )
        or captured != sorted(captured)
        or len(set(captured)) != len(captured)
        or not all(
            capture_started_ms < value < capture_ended_ms
            for value in captured
        )
    ):
        raise RuntimeError("page camera frame timing changed")
    if (
        record.get("responseStatus") != 200
        or response.get("ok") is not True
    ):
        raise RuntimeError(f"camera settlement failed: {response}")
    observation = response.get("articulatory_response")
    if (
        not isinstance(observation, dict)
        or observation.get("state") != expected_state
        or observation.get("thing_ids") != expected_thing_ids
    ):
        raise RuntimeError(
            "camera THING resolution changed: "
            f"expected={expected_state}/{expected_thing_ids}; "
            f"actual={observation}"
        )
    receipt = _sha256(
        observation.get("response_authority_receipt_sha256"),
        "camera resolution",
    )
    request_receipt = hashlib.sha256(json.dumps(
        request,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()
    return {
        "request_sha256": request_receipt,
        "response_authority_receipt_sha256": receipt,
    }


def _post_exact_empty_grounding(
    *,
    port: int,
) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        port,
        timeout=120,
    )
    try:
        connection.request(
            "POST",
            GROUNDING_PATH,
            body=b"",
            headers={
                "Content-Length": "0",
                "X-API-Key": API_KEY,
            },
        )
        response = connection.getresponse()
        body = response.read()
        return response.status, json.loads(body)
    finally:
        connection.close()


def _validate_grounding(
    value: dict[str, object],
    *,
    thing_id: str,
    custody,
) -> None:
    if set(value) != {
        "admission_basis",
        "expansion_authority_receipt_sha256",
        "full_field_root_count",
        "grounding_contact_custody_receipt_sha256",
        "grounding_contact_settlement_receipt_sha256",
        "meaning_authority",
        "reduced_approximation",
        "schema",
        "senses",
        "source_occurrence_id",
        "state",
        "thing_id",
    }:
        raise RuntimeError("grounding receipt shape changed")
    if (
        value.get("schema") != GROUNDING_SCHEMA
        or value.get("state") != "grounded"
        or value.get("admission_basis") != "lived_contact_tutor"
        or value.get("thing_id") != thing_id
        or value.get("source_occurrence_id")
        != custody.source_occurrence_id
        or value.get("senses") != ["sight"]
        or value.get("meaning_authority") is not False
        or value.get("reduced_approximation") is not False
    ):
        raise RuntimeError(f"grounding authority changed: {value}")
    for field in (
        "expansion_authority_receipt_sha256",
        "grounding_contact_custody_receipt_sha256",
        "grounding_contact_settlement_receipt_sha256",
    ):
        _sha256(value.get(field), field)


def _assert_expected_page_errors(
    *,
    console_errors: list[str],
    http_errors: list[dict[str, object]],
) -> int:
    expected = [
        value
        for value in http_errors
        if (
            value.get("status") == 404
            and "/v7/state?session_id=" in str(value.get("url"))
        )
    ]
    unexpected = [value for value in http_errors if value not in expected]
    if unexpected or len(console_errors) != len(expected):
        raise RuntimeError(
            "browser emitted unexpected errors: "
            f"console={console_errors}; http={unexpected}"
        )
    return len(expected)


def _run_camera_page(
    *,
    browser,
    candidate_origin: str,
    page_url: str,
    microphone: bool,
    required_sights: int,
    timeout_ms: int,
):
    context = browser.new_context()
    context.grant_permissions(
        ["camera", "microphone"],
        origin=candidate_origin,
    )
    page = context.new_page()
    console_errors: list[str] = []
    http_errors: list[dict[str, object]] = []
    page.add_init_script(_browser_instrumentation(candidate_origin))
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
    if microphone:
        page.locator("#mic-perm").click()
        page.wait_for_function(
            "() => Boolean(micPCMActive&&micEpoch&&micEpoch.active)",
            timeout=30_000,
        )
    page.locator("#cam-perm").click()
    page.wait_for_function(
        "() => Boolean(camStream)",
        timeout=30_000,
    )
    _wait_for_settled_sights(page, required_sights, timeout_ms)
    return context, page, console_errors, http_errors


def run_probe(*, timeout_seconds: int) -> dict[str, object]:
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or timeout_seconds <= 0
        or timeout_seconds > MAXIMUM_PROOF_SECONDS
    ):
        raise ValueError(
            "camera grounding proof timeout must be within 1–180 seconds"
        )
    _configure_candidate_environment()
    os.environ["GUALA_CAUSAL_ACTION_KEY"] = ENGINE_KEY
    schedule = build_cognitive_proof_wav()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "camera grounding proof requires Python Playwright"
        ) from error

    import dsf_ai_service.app as app_module

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    writer = None
    reader = None
    server = None
    initial_resources = _resident_groups(_tree_rss_breakdown())
    try:
        with tempfile.TemporaryDirectory(
            prefix="guala-camera-contact-browser-"
        ) as scratch_dir:
            state_dir = os.path.join(scratch_dir, "state")
            camera_source = build_authenticated_camera_source(
                Path(scratch_dir) / "camera.y4m"
            )
            writer = Guala()
            _install_candidate_globals(writer)
            app_module._GUALALOOM_API_KEY = API_KEY
            app_module.STATE_DIR = state_dir
            writer._generate_genesis_identity(state_dir)
            thing, contact_mount = _establish_contact_grounded_thing(
                writer
            )
            writer.save_full_state(state_dir)
            writer._authoritative_hot_generation_publisher = (
                _activate_local_hot_files(state_dir)
            )

            port = _free_port()
            candidate_origin = f"http://127.0.0.1:{port}"
            page_url = f"{candidate_origin}/gualaloom"
            server = _start_candidate(port)
            fetched_html = _wait_for_candidate(page_url, server)
            reviewed_html_sha256 = hashlib.sha256(
                PAGE.read_bytes()
            ).hexdigest()
            if (
                hashlib.sha256(fetched_html).hexdigest()
                != reviewed_html_sha256
            ):
                raise RuntimeError(
                    "candidate did not serve the reviewed Guala page"
                )

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--autoplay-policy=no-user-gesture-required",
                        "--use-fake-device-for-media-stream",
                        "--use-fake-ui-for-media-stream",
                        (
                            "--use-file-for-fake-audio-capture="
                            f"{schedule['wav_path']}"
                        ),
                        (
                            "--use-file-for-fake-video-capture="
                            f"{camera_source['path']}"
                        ),
                    ],
                )
                (
                    live_context,
                    live_page,
                    live_console_errors,
                    live_http_errors,
                ) = _run_camera_page(
                    browser=browser,
                    candidate_origin=candidate_origin,
                    page_url=page_url,
                    microphone=True,
                    required_sights=1,
                    timeout_ms=timeout_seconds * 1_000,
                )
                first_records = _settled_sight_records(live_page)
                first = first_records[0]
                first_receipts = _validate_camera_record(
                    first,
                    expected_state="unresolved",
                    expected_thing_ids=[],
                )
                custody, _capability, first_roots = (
                    _assert_complete_sight_custody(writer)
                )
                first_response = (
                    writer._latest_sight_evoked_articulatory_occurrence
                )
                if (
                    first_response is None
                    or first_response.authority_receipt_sha256
                    != first_receipts[
                        "response_authority_receipt_sha256"
                    ]
                    or first_response.cue_settlement_receipt_sha256
                    != custody.settlement.authority_receipt_sha256
                ):
                    raise RuntimeError(
                        "browser first sight crossed engine custody"
                    )

                active_status = _status_snapshot(live_page)
                if (
                    active_status["microphoneTracks"] != ["live"]
                    or active_status["cameraTracks"] != ["live"]
                ):
                    raise RuntimeError(
                        "real browser sensory tracks did not remain live"
                    )
                active_resources = _resident_groups(
                    _tree_rss_breakdown()
                )

                live_page.locator("#cam-perm").click()
                live_page.wait_for_function(
                    "() => !camStream",
                    timeout=30_000,
                )
                live_page.wait_for_function(
                    """required => (
                      window.__candidateSoundFrames.filter(
                        value=>value&&value.response!==null
                      ).length>=required
                    )""",
                    arg=MINIMUM_SETTLED_CHUNKS,
                    timeout=timeout_seconds * 1_000,
                )
                drain = _stop_admission_and_drain(
                    live_page,
                    timeout_ms=120_000,
                )
                sound_records = drain.pop("soundRecords")
                drain.pop("binauralRecords")
                settled_sound = _validate_records(sound_records)

                registry_after_drain = (
                    app_module._auditory_pcm_streams.status()
                )
                pair_registry_after_drain = (
                    app_module._browser_binaural_pcm_streams.status()
                )
                if (
                    registry_after_drain["active_streams"] != 0
                    or registry_after_drain["retained_pcm_bytes"] != 0
                    or pair_registry_after_drain["active_streams"] != 0
                    or pair_registry_after_drain[
                        "retained_pcm_bytes"
                    ] != 0
                ):
                    raise RuntimeError(
                        "browser sensory transport did not drain"
                    )

                status_code, grounded = _post_exact_empty_grounding(
                    port=port
                )
                if status_code != 200:
                    raise RuntimeError(
                        "empty authenticated grounding failed: "
                        f"{status_code} {grounded}"
                    )
                _validate_grounding(
                    grounded,
                    thing_id=thing.thing_id,
                    custody=custody,
                )

                live_page.locator("#cam-perm").click()
                live_page.wait_for_function(
                    "() => Boolean(camStream)",
                    timeout=30_000,
                )
                _wait_for_settled_sights(
                    live_page,
                    MINIMUM_LIVE_SIGHT_OCCURRENCES,
                    timeout_seconds * 1_000,
                )
                live_records = _settled_sight_records(live_page)
                _validate_visual_intervals(live_records[:2])
                second_receipts = _validate_camera_record(
                    live_records[1],
                    expected_state="unbound",
                    expected_thing_ids=[thing.thing_id],
                )
                live_page.locator("#cam-perm").click()
                live_page.wait_for_function(
                    "() => !camStream",
                    timeout=30_000,
                )
                if live_page.evaluate(
                    "() => window.__candidateFetchErrors"
                ):
                    raise RuntimeError(
                        "browser capture instrumentation failed"
                    )
                expected_live_404s = _assert_expected_page_errors(
                    console_errors=live_console_errors,
                    http_errors=live_http_errors,
                )
                live_context.close()

                writer.save_hot_state(state_dir)
                expansion_snapshot = (
                    writer._causal_thing_sensory_expansion
                    .snapshot_encoded()
                )
                writer.strict_shutdown(timeout=30.0)
                writer = None

                reader = Guala()
                reader.load_full_state(
                    state_dir,
                    require_exact_binary=True,
                )
                if not reader._load_successful:
                    raise RuntimeError(
                        f"cold restore failed: {reader._load_errors}"
                    )
                if (
                    reader._causal_thing_sensory_expansion
                    .snapshot_encoded()
                    != expansion_snapshot
                ):
                    raise RuntimeError(
                        "cold restore changed grounded sight expansion"
                    )
                _install_candidate_globals(reader)
                app_module._GUALALOOM_API_KEY = API_KEY
                app_module.STATE_DIR = state_dir

                (
                    cold_context,
                    cold_page,
                    cold_console_errors,
                    cold_http_errors,
                ) = _run_camera_page(
                    browser=browser,
                    candidate_origin=candidate_origin,
                    page_url=page_url,
                    microphone=False,
                    required_sights=1,
                    timeout_ms=timeout_seconds * 1_000,
                )
                cold_records = _settled_sight_records(cold_page)
                cold_receipts = _validate_camera_record(
                    cold_records[0],
                    expected_state="unbound",
                    expected_thing_ids=[thing.thing_id],
                )
                cold_page.locator("#cam-perm").click()
                cold_page.wait_for_function(
                    "() => !camStream",
                    timeout=30_000,
                )
                expected_cold_404s = _assert_expected_page_errors(
                    console_errors=cold_console_errors,
                    http_errors=cold_http_errors,
                )
                cold_context.close()
                browser.close()

            expansion_status = (
                reader._causal_thing_sensory_expansion.status()
            )
            if (
                expansion_status["reduced_approximation"] is not False
                or expansion_status["state_bytes"]
                > expansion_status["state_capacity_bytes"]
            ):
                raise RuntimeError(
                    "grounded expansion exceeded its exact allocation"
                )
            state_bytes = _directory_bytes(state_dir)
            final_resources = _resident_groups(_tree_rss_breakdown())
            return {
                "authority_boundary": {
                    "meaning_authority": False,
                    "object_name_authority": False,
                    "source_identity_authority": False,
                    "transcript_authority": False,
                    "word_learning_seeded": False,
                },
                "browser": {
                    "authenticated_camera_source": {
                        "byte_count": camera_source["byte_count"],
                        "height": camera_source["height"],
                        "sha256": camera_source["sha256"],
                        "width": camera_source["width"],
                    },
                    "active_camera_tracks": (
                        active_status["cameraTracks"]
                    ),
                    "active_microphone_tracks": (
                        active_status["microphoneTracks"]
                    ),
                    "capture_drain": drain,
                    "cold_page_expected_unstarted_poll_count": (
                        expected_cold_404s
                    ),
                    "live_page_expected_unstarted_poll_count": (
                        expected_live_404s
                    ),
                    "settled_live_sight_occurrences": (
                        len(live_records)
                    ),
                    "settled_sound_occurrences": len(settled_sound),
                },
                "cold_restored_sight": cold_receipts,
                "contact": {
                    "physical_mount_receipt_sha256": (
                        contact_mount.evidence_receipt
                        .authority_receipt_sha256
                    ),
                    "thing_id": thing.thing_id,
                },
                "first_unresolved_sight": {
                    **first_receipts,
                    "full_field_root_count": len(first_roots),
                    "source_occurrence_id": (
                        custody.source_occurrence_id
                    ),
                },
                "grounding": grounded,
                "limits": {
                    "persistent_state_bytes": state_bytes,
                    "pcm_ring_capacity_bytes": PCM_RING_BYTES,
                    "sensory_expansion": expansion_status,
                    "timeout_seconds": timeout_seconds,
                },
                "resources": {
                    "active_browser_capture": active_resources,
                    "final": final_resources,
                    "initial": initial_resources,
                    "tree_growth_bytes": (
                        final_resources["tree_bytes"]
                        - initial_resources["tree_bytes"]
                    ),
                },
                "reviewed_html_sha256": reviewed_html_sha256,
                "schema": PROOF_SCHEMA,
                "second_resolved_sight": second_receipts,
                "state": "passed",
            }
    finally:
        if server is not None:
            server.should_exit = True
            thread = getattr(server, "_candidate_thread", None)
            if thread is not None:
                thread.join(timeout=30)
        if writer is not None:
            writer.strict_shutdown(timeout=30.0)
        if reader is not None:
            reader.strict_shutdown(timeout=30.0)
        stop_exact_field_executor()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=MAXIMUM_PROOF_SECONDS,
    )
    args = parser.parse_args()
    result = run_probe(timeout_seconds=args.timeout_seconds)
    print(json.dumps(
        result,
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
