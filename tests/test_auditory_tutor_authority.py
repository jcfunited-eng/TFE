from __future__ import annotations

import io
import math
import struct
import wave
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from dsf_ai_service import app as app_module
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _tone_wav(duration_seconds: int = 1) -> bytes:
    rate = 16_000
    values = [
        int(8_000 * math.sin(2.0 * math.pi * 440.0 * index / rate))
        for index in range(rate * duration_seconds)
    ]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
    return payload.getvalue()


def test_auditory_tutoring_requires_server_credential(monkeypatch) -> None:
    calls = []
    fake = SimpleNamespace(
        teach_latest_auditory_experience=lambda **values: (
            calls.append(values),
            {
                "accepted": True,
                "experience_id": values["experience_id"],
                "kind": values["kind"],
                "tutor_label": values["tutor_label"],
                "reinforcement_count": 1,
            },
        )[1]
    )
    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setattr(app_module, "_guala", fake)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    client = TestClient(app_module.app)
    request = {
        "experience_id": "1" * 64,
        "kind": "spoken_form",
        "tutor_label": "hello",
    }

    assert client.post("/api/v1/auditory/teach", json=request).status_code == 401
    assert client.post(
        "/api/v1/auditory/teach",
        json={**request, "source": "joe"},
        headers={"X-API-Key": "wrong"},
    ).status_code == 401
    accepted = client.post(
        "/api/v1/auditory/teach",
        json=request,
        headers={"X-API-Key": "auditory-secret"},
    )

    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True
    assert len(calls) == 1
    assert calls[0]["experience_id"] == "1" * 64
    assert calls[0]["kind"] == "spoken_form"
    assert calls[0]["tutor_label"] == "hello"
    receipt = calls[0]["authority_receipt"]
    assert receipt["experience_id"] == "1" * 64
    assert receipt["kind"] == "spoken_form"
    assert receipt["tutor_label"] == "hello"
    assert len(receipt["authority_hmac_sha256"]) == 64


def test_authenticated_malformed_experience_id_returns_bounded_4xx(
    monkeypatch,
) -> None:
    calls = []
    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setattr(
        app_module,
        "_guala",
        SimpleNamespace(
            teach_latest_auditory_experience=lambda **values: calls.append(values)
        ),
    )
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)

    response = TestClient(app_module.app).post(
        "/api/v1/auditory/teach",
        json={
            "experience_id": "not-a-sha256-experience-id",
            "kind": "spoken_form",
            "tutor_label": "hello",
        },
        headers={"X-API-Key": "auditory-secret"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "auditory tutor experience id must be a SHA-256 hex digest"
    )
    assert calls == []


def test_monaural_source_label_is_not_a_tutoring_option(monkeypatch) -> None:
    def reject_source(**_values):
        raise ValueError(
            "monaural audio has no uninterrupted receipted source-continuity authority"
        )

    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setattr(
        app_module,
        "_guala",
        SimpleNamespace(teach_latest_auditory_experience=reject_source),
    )
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    client = TestClient(app_module.app)
    response = client.post(
        "/api/v1/auditory/teach",
        json={
            "experience_id": "2" * 64,
            "kind": "source_continuity",
            "tutor_label": "Joe",
        },
        headers={"X-API-Key": "auditory-secret"},
    )
    assert response.status_code == 409
    assert "monaural audio" in response.json()["detail"]


def test_authenticated_http_tutoring_reaches_required_engine_owner(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        engine.process_sound_frame(
            _tone_wav(),
            source="browser_microphone",
            source_anchor_ns=1_000_000_000,
            source_time_end_ns=2_000_000_000,
            auditory_event_boundary="utterance",
        )
        experience = engine._latest_auditory_l5_experience
        monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "auditory-secret")
        monkeypatch.setattr(app_module, "_guala", engine)
        monkeypatch.setattr(app_module, "_is_remote", lambda: False)
        response = TestClient(app_module.app).post(
            "/api/v1/auditory/teach",
            json={
                "experience_id": experience.experience_id,
                "kind": "spoken_form",
                "tutor_label": "hello guala",
            },
            headers={"X-API-Key": "auditory-secret"},
        )

        assert response.status_code == 200
        assert response.json()["recognized_label"] == "hello guala"
        reciprocity = engine.auditory_l5_status()["reciprocity"]
        assert reciprocity["tutor_authority_required"] is True
        assert reciprocity["tutor_authority_nonce_count"] == 1
    finally:
        engine.shutdown()


def test_isolated_asset_tutoring_is_authenticated(monkeypatch) -> None:
    calls = []
    fake = SimpleNamespace(
        teach_isolated_auditory_asset=lambda wav, label: (
            calls.append((wav, label)),
            {"accepted": True, "tutor_label": label},
        )[1]
    )
    monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setattr(app_module, "_guala", fake)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    import dsf_ai_service.substrate_runner as substrate_runner
    monkeypatch.setattr(
        substrate_runner, "_webm_to_wav_bytes", lambda _encoded: _tone_wav()
    )
    client = TestClient(app_module.app)
    files = {"file": ("spoken.webm", b"bounded-audio", "audio/webm")}
    form = {"tutor_label": "hello guala"}

    assert client.post(
        "/api/v1/auditory/teach-asset", files=files, data=form
    ).status_code == 401
    accepted = client.post(
        "/api/v1/auditory/teach-asset",
        files=files,
        data=form,
        headers={"X-API-Key": "auditory-secret"},
    )
    assert accepted.status_code == 200
    assert calls == [(_tone_wav(), "hello guala")]


def test_isolated_asset_transaction_teaches_full_l5_without_retention(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    before_sounds = dict(engine._sounds)
    try:
        result = engine.teach_isolated_auditory_asset(
            _tone_wav(), "hello guala"
        )
        assert result["accepted"] is True
        assert result["recognized_label"] == "hello guala"
        assert result["event_boundary"] == "utterance"
        assert result["port_count"] == 16
        assert result["sample_count"] == 16_000
        assert engine._sounds == before_sounds
        status = engine.auditory_l5_status()["reciprocity"]
        assert status["class_counts"]["spoken_form"] == 1
        assert status["tutor_authority_nonce_count"] == 1
    finally:
        engine.shutdown()


def test_oversized_tutor_asset_fails_before_class_mutation(monkeypatch) -> None:
    monkeypatch.setenv("GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        before = engine.auditory_l5_status()["reciprocity"]
        with pytest.raises(ValueError, match="eight-second"):
            engine.teach_isolated_auditory_asset(
                _tone_wav(9), "too long"
            )
        after = engine.auditory_l5_status()["reciprocity"]
        assert after["class_counts"] == before["class_counts"]
        assert after["reinforcements"] == before["reinforcements"]
    finally:
        engine.shutdown()
