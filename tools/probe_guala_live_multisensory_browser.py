#!/usr/bin/env python3
"""Prove deployed browser-owned sight and sound transport.

Chromium opens the reviewed production Guala page and supplies deterministic
fake camera and microphone devices.  The probe uses only the page controls;
it never constructs or sends a sensory request itself.

The proof requires three distinct physical boundaries:

* microphone alone settles sound while sight is sensor-unavailable;
* camera alone settles sight through the standalone visual route;
* camera and microphone together settle sight and sound in one receipt-linked
  six-sense causal window.

No transcript, symbol, label, pronunciation, meaning, or synthesized speech
is supplied by this probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import tempfile
import time
import urllib.parse
import urllib.request
import wave
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
REVIEWED_PAGE = ROOT / "dsf_ai_service" / "static" / "gualaloom.html"
DEFAULT_PAGE_URL = "https://dsf-ai.com/gualaloom.html"
PROOF_SCHEMA = "guala.live_multisensory.browser_transport_proof.v1"
PCM_SAMPLE_RATE_HZ = 16_000
PCM_PROOF_SECONDS = 30
CAMERA_WIDTH = 128
CAMERA_HEIGHT = 128
SHA256_HEX = frozenset("0123456789abcdef")
SENSE_ORDER = ("sight", "sound", "touch", "smell", "taste", "body")
UNOBSERVED_SENSES = ("touch", "smell", "taste", "body")


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in SHA256_HEX for character in value)
    ):
        raise RuntimeError(f"{label} is not a SHA-256 receipt")
    return value


def build_fake_microphone_wav(path: Path) -> dict[str, object]:
    """Create bounded deterministic physical pressure samples."""

    sample_count = PCM_SAMPLE_RATE_HZ * PCM_PROOF_SECONDS
    samples = bytearray()
    for index in range(sample_count):
        first = math.sin(2 * math.pi * 337 * index / PCM_SAMPLE_RATE_HZ)
        second = math.sin(2 * math.pi * 613 * index / PCM_SAMPLE_RATE_HZ)
        envelope = 0.35 + 0.15 * (
            (index // (PCM_SAMPLE_RATE_HZ // 4)) % 4
        )
        value = round(4_000 * envelope * (first + 0.5 * second))
        samples.extend(struct.pack("<h", max(-32_768, min(32_767, value))))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(PCM_SAMPLE_RATE_HZ)
        target.writeframes(samples)
    return {
        "path": path,
        "pcm_bytes": len(samples),
        "pcm_sha256": hashlib.sha256(samples).hexdigest(),
        "sample_count": sample_count,
        "sample_rate_hz": PCM_SAMPLE_RATE_HZ,
    }


def build_fake_camera_y4m(path: Path) -> dict[str, object]:
    """Create one bounded nonuniform light field for Chromium."""

    header = (
        f"YUV4MPEG2 W{CAMERA_WIDTH} H{CAMERA_HEIGHT} "
        "F30:1 Ip A1:1 C420jpeg\n"
    ).encode("ascii")
    frames = []
    for frame_index in range(30):
        luminance = bytes(
            (
                row * 17
                + column * 29
                + frame_index * 7
                + ((row // 8) ^ (column // 8)) * 11
            ) % 220 + 16
            for row in range(CAMERA_HEIGHT)
            for column in range(CAMERA_WIDTH)
        )
        chroma_width = CAMERA_WIDTH // 2
        chroma_height = CAMERA_HEIGHT // 2
        chroma_u = bytes(
            (row * 7 + column * 13 + frame_index * 3) % 224 + 16
            for row in range(chroma_height)
            for column in range(chroma_width)
        )
        chroma_v = bytes(
            (row * 19 + column * 5 + frame_index * 5) % 224 + 16
            for row in range(chroma_height)
            for column in range(chroma_width)
        )
        frames.append(b"FRAME\n" + luminance + chroma_u + chroma_v)
    encoded = header + b"".join(frames)
    path.write_bytes(encoded)
    return {
        "byte_count": len(encoded),
        "height": CAMERA_HEIGHT,
        "path": path,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "width": CAMERA_WIDTH,
    }


def _browser_instrumentation() -> str:
    """Observe fetch without changing the page-owned request."""

    return """
      (() => {
        const originalFetch = window.fetch.bind(window);
        window.__gualaLiveMultisensoryRecords = [];
        window.fetch = async (input, init = {}) => {
          const url = typeof input === "string" ? input : input.url;
          let request = null;
          if (typeof init.body === "string") {
            try { request = JSON.parse(init.body); } catch (_error) {}
          }
          const record = {
            requested_at_ms: Date.now(),
            url,
            request,
            response: null,
            response_status: null,
            response_error: null
          };
          window.__gualaLiveMultisensoryRecords.push(record);
          try {
            const response = await originalFetch(input, init);
            record.response_status = response.status;
            try { record.response = await response.clone().json(); }
            catch (error) { record.response_error = String(error); }
            return response;
          } catch (error) {
            record.response_error = String(error);
            throw error;
          }
        };
      })();
    """


def _record_path(record: dict[str, object]) -> str:
    url = record.get("url")
    if not isinstance(url, str):
        return ""
    return urllib.parse.urlparse(url).path


def _records(page, path: str) -> list[dict[str, object]]:
    values = page.evaluate(
        "() => window.__gualaLiveMultisensoryRecords || []"
    )
    return [
        value
        for value in values
        if isinstance(value, dict)
        and _record_path(value) == path
        and isinstance(value.get("response"), dict)
    ]


def _wait_for_valid_record(
    page,
    *,
    path: str,
    validator: Callable[[dict[str, object]], dict[str, object]],
    timeout_seconds: int,
) -> tuple[dict[str, object], dict[str, object]]:
    deadline = time.monotonic() + timeout_seconds
    errors: list[str] = []
    while time.monotonic() < deadline:
        for record in _records(page, path):
            try:
                return record, validator(record)
            except RuntimeError as error:
                errors.append(str(error))
        page.wait_for_timeout(250)
    raise RuntimeError(
        f"deployed {path} produced no valid boundary; "
        f"latest_validation_errors={errors[-4:]}"
    )


def _assert_no_semantic_request_authority(
    request: dict[str, object],
) -> None:
    forbidden = {
        "label",
        "meaning",
        "pronunciation",
        "recognized_form",
        "symbol",
        "transcript",
        "tutor_designation",
        "word",
    }
    if any(key in request for key in forbidden):
        raise RuntimeError("browser sensory request gained semantic authority")
    if request.get("command") not in (None, ""):
        raise RuntimeError("browser sensory request gained a command")


def _assert_no_language_response_authority(value: object) -> None:
    authority_names = {
        "label_authority",
        "meaning_authority",
        "pronunciation_authority",
        "reading_authority",
        "recognition_authority",
        "transcript_authority",
        "tts_authority",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            if key in authority_names and item not in (False, None):
                raise RuntimeError(
                    "browser sensory response gained language authority"
                )
            if key == "candidate_labels" and item not in ([], None):
                raise RuntimeError(
                    "browser sensory response gained a candidate label"
                )
            if key == "recognized_form" and item is not None:
                raise RuntimeError(
                    "browser sensory response gained a recognized form"
                )
            _assert_no_language_response_authority(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_language_response_authority(item)


def _validate_six_sense_sound(
    record: dict[str, object],
    *,
    expected_observed: tuple[str, ...],
    expected_boundary: str,
    expected_visual_source: str | None,
) -> dict[str, object]:
    request = record.get("request")
    response = record.get("response")
    if (
        record.get("response_status") != 200
        or not isinstance(request, dict)
        or not isinstance(response, dict)
        or response.get("ok") is not True
    ):
        raise RuntimeError("sound request did not settle")
    _assert_no_semantic_request_authority(request)
    _assert_no_language_response_authority(response)
    has_sight = "sight_frames" in request
    if has_sight != ("sight" in expected_observed):
        raise RuntimeError("sound request changed its sight participation")
    if (
        request.get("visual_source") if has_sight else None
    ) != expected_visual_source:
        raise RuntimeError("sound request changed visual provenance")
    boundary = response.get("sensory_boundary")
    if not isinstance(boundary, dict) or tuple(boundary) != SENSE_ORDER:
        raise RuntimeError("sound response lost exact six-sense order")
    expected = {
        sense: (
            "observed"
            if sense in expected_observed
            else "sensor_unavailable"
        )
        for sense in SENSE_ORDER
    }
    if boundary != expected:
        raise RuntimeError(
            f"sound response changed six-sense truth: {boundary}"
        )
    if (
        response.get("causal_boundary") != expected_boundary
        or response.get("visual_source") != expected_visual_source
    ):
        raise RuntimeError("sound response changed causal boundary")
    continuity = response.get("pcm_continuity")
    recognition = response.get("spoken_word_recognition")
    if (
        not isinstance(continuity, dict)
        or continuity.get("status") != "contiguous"
        or continuity.get("meaning_authority") is not False
        or continuity.get("transcript_authority") is not False
        or not isinstance(recognition, dict)
        or recognition.get("recognized_form") is not None
        or recognition.get("candidate_labels") != []
        or recognition.get("meaning_authority") is not False
        or recognition.get("transcript_authority") is not False
    ):
        raise RuntimeError("sound response gained language authority")
    result = {
        "causal_settlement_receipt_sha256": _sha256(
            continuity.get("causal_settlement_receipt_sha256"),
            "causal settlement",
        ),
        "cochlear_state_receipt_sha256": _sha256(
            continuity.get("cochlear_state_receipt_sha256"),
            "cochlear state",
        ),
        "sensory_boundary": boundary,
    }
    if "sight" in expected_observed:
        visual = response.get("visual_region")
        if not isinstance(visual, dict):
            raise RuntimeError("joined response lost visual settlement")
        result["visual_full_field_receipt_sha256"] = _sha256(
            visual.get("full_field_receipt_sha256"),
            "joined visual full-field",
        )
        result["visual_settlement_receipt_sha256"] = _sha256(
            visual.get("authority_receipt_sha256"),
            "joined visual settlement",
        )
    return result


def _validate_camera_only(
    record: dict[str, object],
) -> dict[str, object]:
    request = record.get("request")
    response = record.get("response")
    if (
        record.get("response_status") != 200
        or not isinstance(request, dict)
        or not isinstance(response, dict)
        or response.get("ok") is not True
        or response.get("raw_sight") != "accepted"
    ):
        raise RuntimeError("camera-only request did not settle")
    _assert_no_semantic_request_authority(request)
    _assert_no_language_response_authority(response)
    if (
        request.get("text") != ""
        or request.get("visual_source") != "camera_stream"
        or "audio_encoding" in request
        or "audio_stream_id" in request
    ):
        raise RuntimeError("camera-only request gained sound or semantics")
    frames = request.get("sight_frames")
    if not isinstance(frames, list) or not 4 <= len(frames) <= 8:
        raise RuntimeError("camera-only request changed bounded frame extent")
    visual = response.get("visual_region")
    recognition = response.get("object_name_recognition")
    if (
        not isinstance(visual, dict)
        or not isinstance(recognition, dict)
        or recognition.get("status") != "unavailable"
    ):
        raise RuntimeError("camera-only response changed visual truth")
    return {
        "visual_full_field_receipt_sha256": _sha256(
            visual.get("full_field_receipt_sha256"),
            "camera full-field",
        ),
        "visual_settlement_receipt_sha256": _sha256(
            visual.get("authority_receipt_sha256"),
            "camera settlement",
        ),
    }


def _sound_only_validator(record: dict[str, object]) -> dict[str, object]:
    return _validate_six_sense_sound(
        record,
        expected_observed=("sound",),
        expected_boundary="sound",
        expected_visual_source=None,
    )


def _joined_validator(record: dict[str, object]) -> dict[str, object]:
    return _validate_six_sense_sound(
        record,
        expected_observed=("sight", "sound"),
        expected_boundary="audiovisual",
        expected_visual_source="camera_stream",
    )


def run_live_probe(
    *,
    page_url: str,
    timeout_seconds: int,
) -> dict[str, object]:
    if (
        not isinstance(timeout_seconds, int)
        or isinstance(timeout_seconds, bool)
        or not 10 <= timeout_seconds <= 180
    ):
        raise ValueError("live probe timeout must be within 10–180 seconds")
    parsed = urllib.parse.urlparse(page_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("live probe requires an HTTPS page URL")
    reviewed = REVIEWED_PAGE.read_bytes()
    reviewed_sha256 = hashlib.sha256(reviewed).hexdigest()
    with urllib.request.urlopen(page_url, timeout=30) as response:
        deployed = response.read()
    deployed_sha256 = hashlib.sha256(deployed).hexdigest()
    if deployed_sha256 != reviewed_sha256:
        raise RuntimeError(
            "deployed Guala page differs from the reviewed local artifact"
        )
    deployed_text = deployed.decode("utf-8")
    if (
        "speechSynthesis" in deployed_text
        or "SpeechSynthesisUtterance" in deployed_text
    ):
        raise RuntimeError("deployed page gained synthesized speech")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "live multisensory proof requires Python Playwright"
        ) from error

    with tempfile.TemporaryDirectory(
        prefix="guala-live-multisensory-browser-"
    ) as scratch:
        scratch_path = Path(scratch)
        microphone = build_fake_microphone_wav(
            scratch_path / "microphone.wav"
        )
        camera = build_fake_camera_y4m(scratch_path / "camera.y4m")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=[
                    "--autoplay-policy=no-user-gesture-required",
                    "--use-fake-device-for-media-stream",
                    "--use-fake-ui-for-media-stream",
                    (
                        "--use-file-for-fake-audio-capture="
                        f"{microphone['path']}"
                    ),
                    (
                        "--use-file-for-fake-video-capture="
                        f"{camera['path']}"
                    ),
                ],
            )
            origin = f"{parsed.scheme}://{parsed.netloc}"
            context = browser.new_context()
            context.grant_permissions(
                ["camera", "microphone"],
                origin=origin,
            )
            page = context.new_page()
            page.add_init_script(_browser_instrumentation())
            page.goto(page_url, wait_until="domcontentloaded")

            page.locator("#mic-perm").click()
            page.wait_for_function(
                "() => Boolean(micPCMActive&&micEpoch&&micEpoch.active)",
                timeout=30_000,
            )
            _sound_record, sound_only = _wait_for_valid_record(
                page,
                path="/sound_frame",
                validator=_sound_only_validator,
                timeout_seconds=timeout_seconds,
            )
            page.locator("#mic-stop").click()
            page.wait_for_function(
                "() => !micPCMActive&&!micEpoch",
                timeout=30_000,
            )

            page.locator("#camera-perm").click()
            page.wait_for_function(
                "() => Boolean(cameraStream)",
                timeout=30_000,
            )
            _camera_record, camera_only = _wait_for_valid_record(
                page,
                path="/sight_frame",
                validator=_validate_camera_only,
                timeout_seconds=timeout_seconds,
            )

            page.locator("#mic-perm").click()
            page.wait_for_function(
                "() => Boolean(micPCMActive&&micEpoch&&micEpoch.active)",
                timeout=30_000,
            )
            _joined_record, joined = _wait_for_valid_record(
                page,
                path="/sound_frame",
                validator=_joined_validator,
                timeout_seconds=timeout_seconds,
            )

            page.locator("#mic-stop").click()
            page.wait_for_function(
                "() => !micPCMActive&&!micEpoch",
                timeout=30_000,
            )
            page.locator("#camera-stop").click()
            page.wait_for_function(
                "() => !cameraStream",
                timeout=30_000,
            )
            context.close()
            browser.close()

    return {
        "authority_boundary": {
            "label_authority": False,
            "meaning_authority": False,
            "pronunciation_authority": False,
            "transcript_authority": False,
            "tts_authority": False,
        },
        "camera_only": camera_only,
        "deployed_html_sha256": deployed_sha256,
        "fake_camera_sha256": camera["sha256"],
        "fake_microphone_pcm_sha256": microphone["pcm_sha256"],
        "joined_sight_sound": joined,
        "reviewed_html_sha256": reviewed_sha256,
        "schema": PROOF_SCHEMA,
        "sound_only": sound_only,
        "state": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_PAGE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    print(json.dumps(
        run_live_probe(
            page_url=args.url,
            timeout_seconds=args.timeout_seconds,
        ),
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
