from __future__ import annotations

import inspect
import subprocess

import pytest

from tools import probe_guala_live_multisensory_browser as probe


def _sound_record(
    *,
    sight: bool,
) -> dict[str, object]:
    observed = ("sight", "sound") if sight else ("sound",)
    request = {
        "audio_encoding": "pcm_s16le",
        "audio_stream_id": "stream",
        "command": "",
        "source": "browser_microphone",
        "text": "cGNt",
    }
    if sight:
        request["visual_source"] = "camera_stream"
        request["sight_frames"] = [
            {
                "captured_ms": 1_000 + index * 250,
                "frame_b64": f"frame-{index}",
            }
            for index in range(4)
        ]
    response = {
        "causal_boundary": "audiovisual" if sight else "sound",
        "ok": True,
        "pcm_continuity": {
            "causal_settlement_receipt_sha256": "a" * 64,
            "cochlear_state_receipt_sha256": "b" * 64,
            "meaning_authority": False,
            "status": "contiguous",
            "transcript_authority": False,
        },
        "sensory_boundary": {
            sense: (
                "observed"
                if sense in observed
                else "sensor_unavailable"
            )
            for sense in probe.SENSE_ORDER
        },
        "spoken_word_recognition": {
            "candidate_labels": [],
            "meaning_authority": False,
            "recognized_form": None,
            "transcript_authority": False,
        },
        "visual_source": "camera_stream" if sight else None,
    }
    if sight:
        response["visual_region"] = {
            "authority_receipt_sha256": "e" * 64,
            "full_field_receipt_sha256": "f" * 64,
        }
    return {
        "request": request,
        "response_status": 200,
        "response": response,
    }


def _camera_record() -> dict[str, object]:
    return {
        "request": {
            "capture_ended_ms": 3_000,
            "capture_started_ms": 1_000,
            "sight_frames": [
                {
                    "captured_ms": 1_000 + index * 250,
                    "frame_b64": f"frame-{index}",
                }
                for index in range(4)
            ],
            "source": "browser_visual",
            "text": "",
            "visual_source": "camera_stream",
        },
        "response_status": 200,
        "response": {
            "object_name_recognition": {"status": "unavailable"},
            "ok": True,
            "raw_sight": "accepted",
            "visual_region": {
                "authority_receipt_sha256": "c" * 64,
                "full_field_receipt_sha256": "d" * 64,
            },
        },
    }


def test_fake_devices_are_bounded_deterministic_physical_sources(
    tmp_path,
) -> None:
    first_wav = probe.build_fake_microphone_wav(tmp_path / "first.wav")
    second_wav = probe.build_fake_microphone_wav(tmp_path / "second.wav")
    first_camera = probe.build_fake_camera_y4m(tmp_path / "first.y4m")
    second_camera = probe.build_fake_camera_y4m(tmp_path / "second.y4m")

    assert first_wav["pcm_sha256"] == second_wav["pcm_sha256"]
    assert first_wav["sample_count"] == 480_000
    assert first_wav["pcm_bytes"] == 960_000
    assert first_camera["sha256"] == second_camera["sha256"]
    assert first_camera["width"] == 128
    assert first_camera["height"] == 128
    assert first_camera["byte_count"] < 1024 * 1024


def test_sound_only_and_joined_windows_keep_all_six_states() -> None:
    sound = probe._sound_only_validator(_sound_record(sight=False))
    joined = probe._joined_validator(_sound_record(sight=True))

    assert sound["sensory_boundary"] == {
        "sight": "sensor_unavailable",
        "sound": "observed",
        "touch": "sensor_unavailable",
        "smell": "sensor_unavailable",
        "taste": "sensor_unavailable",
        "body": "sensor_unavailable",
    }
    assert joined["sensory_boundary"] == {
        "sight": "observed",
        "sound": "observed",
        "touch": "sensor_unavailable",
        "smell": "sensor_unavailable",
        "taste": "sensor_unavailable",
        "body": "sensor_unavailable",
    }
    assert len(joined["causal_settlement_receipt_sha256"]) == 64
    assert joined["visual_full_field_receipt_sha256"] == "f" * 64


def test_camera_only_requires_visual_receipts_and_no_audio() -> None:
    result = probe._validate_camera_only(_camera_record())

    assert result == {
        "visual_full_field_receipt_sha256": "d" * 64,
        "visual_settlement_receipt_sha256": "c" * 64,
    }
    changed = _camera_record()
    changed["request"]["audio_encoding"] = "pcm_s16le"
    with pytest.raises(RuntimeError, match="gained sound"):
        probe._validate_camera_only(changed)


def test_probe_rejects_semantic_authority_in_page_request() -> None:
    changed = _sound_record(sight=True)
    changed["request"]["label"] = "A"

    with pytest.raises(RuntimeError, match="semantic authority"):
        probe._joined_validator(changed)


def test_live_probe_uses_only_deployed_page_controls_for_ingress() -> None:
    source = inspect.getsource(probe.run_live_probe)

    assert 'page.locator("#mic-perm").click()' in source
    assert 'page.locator("#camera-perm").click()' in source
    assert 'path="/sound_frame"' in source
    assert 'path="/sight_frame"' in source
    assert "urllib.request.urlopen(page_url" in source
    assert "urllib.request.Request" not in source
    assert "http.client" not in inspect.getsource(probe)
    assert "speechSynthesis" in source
    assert "SpeechSynthesisUtterance" in source


def test_live_probe_cli_is_importable_without_retired_runtime() -> None:
    completed = subprocess.run(
        [
            "python",
            "tools/probe_guala_live_multisensory_browser.py",
            "--help",
        ],
        cwd=probe.ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--url" in completed.stdout
    assert "--timeout-seconds" in completed.stdout
    assert "gualaloom_v5_engine" not in inspect.getsource(probe)
