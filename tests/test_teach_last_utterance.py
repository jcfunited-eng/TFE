"""GL-FEAT-TEACH-LAST-C1-20260722: the speaker's live voice becomes the
recognizer's vocabulary — a closed-but-unrecognized utterance's bounded
PCM tail is retained (one slot) and teachable through the existing
tutor-authority path."""

import asyncio
import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.app as appmod  # noqa: E402
from dsf_ai_service.substrate.auditory_pcm_stream import (  # noqa: E402
    AuditoryPCMStreamRegistry,
)


PCM_HALF_SECOND = b"\x01\x00" * 8000  # 0.5s @ 16k s16le — above the blip floor


class _FakeEngine:
    def __init__(self):
        self.taught = []
        self.closed = []

    def close_auditory_pcm_stream(self, stream_id, release_terminal=True):
        self.closed.append((stream_id, release_terminal))
        return {"closed": True, "terminal": None}

    def durably_teach_isolated_auditory_asset(self, wav_bytes, label,
                                              state_dir=None):
        self.taught.append((wav_bytes, label))
        return {"recognition_state": "unique", "tutor_label": label}


def _stream_with_pcm(registry, pcm):
    opened = registry.open()
    registry.accept(
        stream_id=opened["stream_id"], sequence=0, first_sample_index=0,
        sample_rate_hz=16000, source_epoch_start_ns=1_000_000,
        pcm_s16le=pcm)
    return opened["stream_id"]


@pytest.fixture
def wired(monkeypatch):
    registry = AuditoryPCMStreamRegistry()
    engine = _FakeEngine()
    monkeypatch.setattr(appmod, "_auditory_pcm_streams", registry)
    monkeypatch.setattr(appmod, "_guala", engine)
    monkeypatch.setattr(appmod, "_is_remote", lambda: False)

    async def _direct(fn):
        return fn()

    monkeypatch.setattr(appmod, "_run_lifecycle_executor", _direct)
    with appmod._last_unrecognized_lock:
        appmod._last_unrecognized_utterance = None
    yield registry, engine
    with appmod._last_unrecognized_lock:
        appmod._last_unrecognized_utterance = None


def test_unrecognized_close_retains_the_utterance(wired):
    registry, engine = wired
    sid = _stream_with_pcm(registry, PCM_HALF_SECOND)
    result = appmod._close_auditory_pcm_epoch(sid)
    assert result["teachable"] is True
    with appmod._last_unrecognized_lock:
        slot = appmod._last_unrecognized_utterance
    assert slot is not None and slot["pcm"] == PCM_HALF_SECOND


def test_blip_below_floor_is_not_retained(wired):
    registry, engine = wired
    sid = _stream_with_pcm(registry, b"\x01\x00" * 100)
    result = appmod._close_auditory_pcm_epoch(sid)
    assert result["teachable"] is False
    with appmod._last_unrecognized_lock:
        assert appmod._last_unrecognized_utterance is None


def test_teach_last_teaches_retained_pcm_and_clears_slot(wired):
    registry, engine = wired
    sid = _stream_with_pcm(registry, PCM_HALF_SECOND)
    appmod._close_auditory_pcm_epoch(sid)
    result = asyncio.run(appmod.auditory_teach_last(
        appmod.AuditoryTeachLastRequest(
            tutor_label="Good Morning Guala", source="joe")))
    assert result["ok"] is True
    assert result["taught_label"] == "good morning guala"
    assert len(engine.taught) == 1
    wav, label = engine.taught[0]
    assert label == "good morning guala"
    assert wav[:4] == b"RIFF" and PCM_HALF_SECOND in wav
    with appmod._last_unrecognized_lock:
        assert appmod._last_unrecognized_utterance is None


def test_teach_last_empty_slot_is_409(wired):
    with pytest.raises(HTTPException) as e:
        asyncio.run(appmod.auditory_teach_last(
            appmod.AuditoryTeachLastRequest(tutor_label="hi", source="joe")))
    assert e.value.status_code == 409


def test_teach_last_rejects_bad_source_and_label(wired):
    registry, engine = wired
    sid = _stream_with_pcm(registry, PCM_HALF_SECOND)
    appmod._close_auditory_pcm_epoch(sid)
    with pytest.raises(HTTPException) as e:
        asyncio.run(appmod.auditory_teach_last(
            appmod.AuditoryTeachLastRequest(tutor_label="hi",
                                            source="stranger")))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        asyncio.run(appmod.auditory_teach_last(
            appmod.AuditoryTeachLastRequest(tutor_label="   ",
                                            source="joe")))
    assert e.value.status_code == 400
    # slot must survive rejected attempts
    with appmod._last_unrecognized_lock:
        assert appmod._last_unrecognized_utterance is not None
