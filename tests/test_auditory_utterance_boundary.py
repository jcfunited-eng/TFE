from __future__ import annotations

import asyncio
import base64
import io
import math
import struct
import wave
from pathlib import Path

import pytest

import dsf_ai_service.app as app_module
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _tone_wav() -> bytes:
    rate = 16_000
    values = [
        int(8_000 * math.sin(2.0 * math.pi * 440.0 * index / rate))
        for index in range(rate)
    ]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
    return payload.getvalue()


@pytest.fixture
def engine(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    value = Guala()
    try:
        yield value
    finally:
        value.shutdown()


def _hear(engine: Guala, boundary: str):
    receipt = engine.process_sound_frame(
        _tone_wav(),
        source="browser_microphone",
        source_anchor_ns=1_000_000_000,
        source_time_end_ns=2_000_000_000,
        auditory_event_boundary=boundary,
    )
    assert receipt["accepted"] is True
    return engine._latest_auditory_l5_experience


def test_ambient_hearing_settles_experience_without_recognition_or_tutor_slot(
    engine: Guala,
) -> None:
    experience = _hear(engine, "ambient")

    assert experience is not None
    experience.verify()
    assert engine._latest_auditory_recognitions == ()
    status = engine.auditory_l5_status()
    assert status["recognition_boundary"] == "ambient"
    assert status["recognition_attempted"] is False
    assert status["l5_owner"]["pending_tutor_experiences"] == 0
    with pytest.raises(RuntimeError, match="tutor window"):
        engine.teach_latest_auditory_experience(
            experience_id=experience.experience_id,
            kind="spoken_form",
            tutor_label="hello",
        )


def test_only_explicit_utterance_can_learn_recognize_and_open_reply_evidence(
    engine: Guala,
) -> None:
    witness = _hear(engine, "utterance")
    engine.teach_latest_auditory_experience(
        experience_id=witness.experience_id,
        kind="spoken_form",
        tutor_label="hello guala",
    )

    _hear(engine, "ambient")
    assert engine._latest_auditory_recognitions == ()
    assert engine.auditory_l5_status()["recognition_attempted"] is False

    _hear(engine, "utterance")
    spoken = next(
        item for item in engine._latest_auditory_recognitions
        if item.kind is AuditoryReciprocityKind.SPOKEN_FORM
    )
    assert spoken.state is AuditoryRecognitionState.UNIQUE
    assert spoken.tutor_label == "hello guala"
    assert engine.auditory_l5_status()["recognition_attempted"] is True


def test_invalid_boundary_fails_before_sensory_mutation(engine: Guala) -> None:
    before = engine.auditory_l5_status()["l5_owner"]["settled"]
    with pytest.raises(ValueError, match="auditory event boundary"):
        engine.process_sound_frame(
            _tone_wav(), auditory_event_boundary="guessed-speech"
        )
    assert engine.auditory_l5_status()["l5_owner"]["settled"] == before


def test_failed_valid_capture_clears_prior_recognition_status(engine: Guala) -> None:
    witness = _hear(engine, "utterance")
    engine.teach_latest_auditory_experience(
        experience_id=witness.experience_id,
        kind="spoken_form",
        tutor_label="hello",
    )
    _hear(engine, "utterance")
    assert engine.auditory_l5_status()["recognitions"]

    with pytest.raises(wave.Error):
        engine.process_sound_frame(
            b"not-a-wave", auditory_event_boundary="ambient"
        )

    status = engine.auditory_l5_status()
    assert status["latest_experience_id"] is None
    assert status["recognitions"] == []
    assert status["recognition_boundary"] == "ambient"
    assert status["recognition_attempted"] is False


def test_tutor_window_expires_by_all_later_experiences(engine: Guala) -> None:
    utterance = _hear(engine, "utterance")
    for index in range(4):
        anchor = 10_000_000_000 + index * 2_000_000_000
        engine.process_sound_frame(
            _tone_wav(),
            source="browser_microphone",
            source_anchor_ns=anchor,
            source_time_end_ns=anchor + 1_000_000_000,
            auditory_event_boundary="ambient",
        )

    with pytest.raises(RuntimeError, match="tutor window"):
        engine.teach_latest_auditory_experience(
            experience_id=utterance.experience_id,
            kind="spoken_form",
            tutor_label="stale label",
        )


def test_remote_transport_preserves_explicit_boundary(monkeypatch) -> None:
    calls = []

    class Client:
        async def call(self, operation, **kwargs):
            calls.append((operation, kwargs))
            return {"ok": True, "seq": 9}

    monkeypatch.setattr(app_module, "_is_remote", lambda: True)
    monkeypatch.setattr(app_module, "_get_substrate_client", lambda: Client())
    response = asyncio.run(app_module.sound_frame(app_module.GLMessage(
        text=base64.b64encode(b"webm").decode("ascii"),
        source="browser_microphone",
        capture_purpose="utterance",
        capture_started_ms=1_000,
        capture_ended_ms=2_000,
    )))

    assert response["ok"] is True
    assert calls[0][1]["data"]["auditory_event_boundary"] == "utterance"


def test_http_reply_door_is_closed_for_ambient_and_open_for_utterance(
    engine: Guala,
    monkeypatch,
) -> None:
    import dsf_ai_service.substrate_runner as substrate_runner

    witness = _hear(engine, "utterance")
    engine.teach_latest_auditory_experience(
        experience_id=witness.experience_id,
        kind="spoken_form",
        tutor_label="hello guala",
    )
    reply_calls = []
    monkeypatch.setattr(app_module, "_guala", engine)
    monkeypatch.setattr(app_module, "_is_remote", lambda: False)
    monkeypatch.setattr(app_module, "_converse_inflight", 0)
    monkeypatch.setattr(app_module, "_converse_window_started_at", 0.0)
    monkeypatch.setattr(
        substrate_runner, "_webm_to_wav_bytes", lambda _encoded: _tone_wav()
    )
    monkeypatch.setattr(
        app_module,
        "_maybe_trigger_voice_reply",
        lambda spoken, tick: reply_calls.append((spoken, tick)),
    )
    monkeypatch.setenv("VOICE_WHISPER", "0")

    def post(purpose: str):
        return asyncio.run(app_module.sound_frame(app_module.GLMessage(
            text=base64.b64encode(b"webm").decode("ascii"),
            source="browser_microphone",
            capture_purpose=purpose,
            capture_started_ms=1_000,
            capture_ended_ms=2_000,
        )))

    ambient = post("ambient")
    assert ambient["spoken_word_recognition"]["status"] == "not_attempted"
    assert reply_calls == []

    utterance = post("utterance")
    assert utterance["spoken_word_recognition"]["status"] == "unique"
    assert utterance["transcript"] == "hello guala"
    assert [value[0] for value in reply_calls] == ["hello guala"]


def test_browser_has_no_manual_utterance_control_or_labeling_path() -> None:
    html = Path("dsf_ai_service/static/gualaloom.html").read_text()
    assert 'id="speak-utterance"' not in html
    assert "toggleUtterance" not in html
    assert "utteranceRecorder" not in html
    assert "capture_purpose:'ambient'" in html
    assert "source:'browser_microphone'" in html
