from __future__ import annotations

import io
import math
import shutil
import struct
import wave
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from dsf_ai_service import app as app_module
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _tone_wav(
    duration_seconds: int = 1,
    frequency_hz: int = 440,
    leading_absent_hops: int = 20,
) -> bytes:
    rate = 16_000
    values = [0] * (leading_absent_hops * 160) + [
        int(8_000 * math.sin(
            2.0 * math.pi * frequency_hz * index / rate
        ))
        for index in range(rate * duration_seconds)
    ] + [0] * (30 * 160)
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
        durably_teach_latest_auditory_experience=lambda **values: (
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
            durably_teach_latest_auditory_experience=lambda **values: calls.append(values)
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
        SimpleNamespace(durably_teach_latest_auditory_experience=reject_source),
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
    monkeypatch, tmp_path,
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
            source_time_end_ns=2_500_000_000,
            auditory_event_boundary="utterance",
        )
        experience = engine._latest_auditory_l5_experience
        monkeypatch.setattr(app_module, "_GUALALOOM_API_KEY", "auditory-secret")
        monkeypatch.setattr(app_module, "_guala", engine)
        monkeypatch.setattr(app_module, "_is_remote", lambda: False)
        monkeypatch.setattr(app_module, "STATE_DIR", str(tmp_path / "state"))
        monkeypatch.setattr(
            engine,
            "_authoritative_hot_generation_publisher",
            lambda **_values: None,
            raising=False,
        )
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
        durably_teach_isolated_auditory_asset=lambda wav, label, **values: (
            calls.append((wav, label, values["state_dir"])),
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
    assert calls == [(_tone_wav(), "hello guala", app_module.STATE_DIR)]


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
        assert result["channel_count"] == 16
        assert result["kernel_component_count"] == 32
        assert result["sample_count"] == 16_320
        assert engine._sounds == before_sounds
        status = engine.auditory_l5_status()["reciprocity"]
        assert status["class_counts"]["spoken_form"] == 1
        assert status["tutor_authority_nonce_count"] == 1
    finally:
        engine.shutdown()


def test_tutor_event_settles_the_surrounded_physical_event(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        result = engine.teach_isolated_auditory_asset(
            _tone_wav(leading_absent_hops=23),
            "hello guala",
        )
        assert result["accepted"] is True
        assert result["sample_count"] == 16_320
        assert engine.auditory_l5_status()["reciprocity"][
            "class_counts"
        ]["spoken_form"] == 1
    finally:
        engine.shutdown()


def test_durable_teaching_failure_rolls_back_auditory_class(
    monkeypatch, tmp_path,
) -> None:
    monkeypatch.setenv("GUALALOOM_API_KEY", "auditory-secret")
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    monkeypatch.setattr(
        engine,
        "_authoritative_hot_generation_publisher",
        lambda **_values: None,
        raising=False,
    )
    monkeypatch.setattr(
        engine,
        "save_hot_state",
        lambda _state_dir: (_ for _ in ()).throw(
            RuntimeError("injected authoritative commit failure")),
    )
    try:
        with pytest.raises(RuntimeError, match="authoritative commit failure"):
            engine.durably_teach_isolated_auditory_asset(
                _tone_wav(),
                "hello guala",
                state_dir=str(tmp_path / "state"),
            )
        reciprocity = engine.auditory_l5_status()["reciprocity"]
        assert reciprocity["class_counts"]["spoken_form"] == 0
        assert reciprocity["tutor_authority_nonce_count"] == 0
    finally:
        engine.shutdown()


def test_durable_teaching_refuses_absent_recovery_authority(
    monkeypatch, tmp_path,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        with pytest.raises(RuntimeError, match="durability is unavailable"):
            engine.durably_teach_isolated_auditory_asset(
                _tone_wav(),
                "hello guala",
                state_dir=str(tmp_path / "state"),
            )
        reciprocity = engine.auditory_l5_status()["reciprocity"]
        assert reciprocity["class_counts"]["spoken_form"] == 0
        assert reciprocity["tutor_authority_nonce_count"] == 0
    finally:
        engine.shutdown()


def test_three_durable_classes_restore_exactly_after_process_replacement(
    monkeypatch, tmp_path,
) -> None:
    from dsf_ai_service.substrate.live_recovery_generation import (
        LiveRecoveryGenerationStore,
    )

    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    active = tmp_path / "active"
    baseline_tree = tmp_path / "baseline-tree"
    engine = Guala()
    try:
        engine.save_full_state(str(active))
        shutil.copytree(active, baseline_tree)
        baseline = SimpleNamespace(
            generation_uuid="584b0681-b386-4762-92af-54fd671d4f53",
            identity=engine._guala_identity,
            tick=engine.tick,
            manifest_sha256="7" * 64,
        )
        recovery = LiveRecoveryGenerationStore(
            tmp_path / "live-recovery",
            baseline=baseline,
            hot_files=Guala.HOT_SAVE_MANIFEST_FILES,
            hmac_key=b"auditory-restart-test-key-material-32-bytes",
        )

        def publish(**values):
            assert values["identity"] == baseline.identity
            assert tuple(sorted(values["manifest_files"])) == recovery.hot_files
            recovery.commit_hot_state(
                tick=values["save_tick"],
                files={
                    name: active / name
                    for name in recovery.hot_files
                },
            )

        engine._authoritative_hot_generation_publisher = publish
        for label, frequency in (
            ("hello", 330),
            ("hello guala", 440),
            ("your name is guala", 550),
        ):
            result = engine.durably_teach_isolated_auditory_asset(
                _tone_wav(frequency_hz=frequency),
                label,
                state_dir=str(active),
            )
            assert result["accepted"] is True
        expected = engine._auditory_reciprocity_owner.encoded_snapshot()
        assert engine.auditory_l5_status()["reciprocity"][
            "class_counts"
        ]["spoken_form"] == 3
    finally:
        engine.shutdown()

    boot_active = tmp_path / "boot-active"
    shutil.copytree(baseline_tree, boot_active)
    restored_generation = recovery.apply_current(boot_active)
    assert restored_generation is not None

    restored = Guala()
    try:
        restored.load_full_state(str(boot_active))
        assert restored._load_successful is True
        assert restored._auditory_reciprocity_owner.encoded_snapshot() == expected
        assert restored.auditory_l5_status()["reciprocity"][
            "class_counts"
        ]["spoken_form"] == 3
    finally:
        restored.shutdown()


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
