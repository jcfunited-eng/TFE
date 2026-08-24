"""The general tutor voice coexists with the real world without semantic input."""

from __future__ import annotations

import base64
import json
import struct
from dsf_ai_service import native_production_app as production


def _payload() -> dict[str, object]:
    return {
        "schema": production.GUIDED_WORLD_VOICE_SCHEMA,
        "pcm_s16le_base64": base64.b64encode(struct.pack("<hh", 2, -2)).decode(),
        "sample_rate_hz": production.COCHLEAR_SAMPLE_RATE_HZ,
    }


def _mount_transport(monkeypatch) -> list[tuple[object, str]]:
    monkeypatch.setattr(production, "_spoken_voice_refusal", lambda: None)
    monkeypatch.setattr(
        production,
        "_refresh_public_observation_cache",
        lambda: (_ for _ in ()).throw(
            AssertionError("observer must not run after the committed lesson")
        ),
    )
    monkeypatch.setattr(
        production,
        "_guided_world_voice_episodes",
        lambda samples, sample_rate: (
            [("physical-world-episode", [(1, 1)])],
            {
                "audio_sample_count": len(samples),
                "retinal_luminance_present": True,
                "smell_present": True,
                "taste_present": False,
                "world_revision": 9,
                "world_state_sha256": "2" * 64,
            },
        ),
    )
    calls: list[tuple[object, str]] = []

    def perform(episodes, intake):
        calls.append((episodes, intake))
        return {
            "accepted": True,
            "generation": 4,
            "hop_count": 1,
            "observation": {},
            "persisted": {"state_sha256": "3" * 64},
            "receptor_ingress": {},
            "totals": {},
        }

    monkeypatch.setattr(production, "_perform_admitted_intake_locked", perform)
    return calls


def test_grounded_world_voice_refuses_semantic_or_object_fields(monkeypatch) -> None:
    _mount_transport(monkeypatch)
    payload = _payload()
    payload["object_id"] = "apple"

    response = production.guided_world_voice(payload)

    assert response.status_code == 422
    assert json.loads(response.body)["accepted"] is False


def test_grounded_world_voice_refuses_a_caller_predecessor_gate(monkeypatch) -> None:
    calls = _mount_transport(monkeypatch)
    payload = _payload()
    payload["expected_predecessor_state_sha256"] = "4" * 64

    response = production.guided_world_voice(payload)

    assert response.status_code == 422
    assert calls == []


def test_grounded_world_voice_commits_one_physical_world_trajectory(monkeypatch) -> None:
    calls = _mount_transport(monkeypatch)

    response = production.guided_world_voice(_payload())

    body = json.loads(response.body)
    assert response.status_code == 200
    assert body["accepted"] is True
    assert body["schema"] == production.GUIDED_WORLD_VOICE_SCHEMA
    assert body["transport_metadata_only"] is True
    assert body["world_sensorium"]["world_revision"] == 9
    assert calls[0][0] == [("physical-world-episode", [(1, 1)])]
    assert calls[0][1].startswith("guided-world-voice:")
