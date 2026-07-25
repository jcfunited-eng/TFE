import contextlib
import io
import threading
import wave
from types import SimpleNamespace

import pytest

from dsf_ai_service.v4.gualaloom_v5_engine import (
    Guala,
    REPLAY_SOUND_MAX_COUNT,
    REPLAY_SOUND_SCHEMA,
)


def _pcm_wav(*, sample_rate=16_000, frame_count=320, sample=700):
    raw = int(sample).to_bytes(2, "little", signed=True) * frame_count
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(raw)
    return output.getvalue()


def _minimal_engine():
    engine = object.__new__(Guala)
    engine.lock = threading.RLock()
    engine._sound_replay_lock = threading.RLock()
    engine._sounds = {}
    engine.tick = 41
    engine._events_for_test = []
    engine._log_substrate_event = lambda kind, **detail: (
        engine._events_for_test.append((kind, detail)))
    engine._engine_mutation_scope = lambda _name: contextlib.nullcontext()
    engine._sound_frames_for_test = []

    def process_sound_frame(wav_bytes, source="mic:live", **_kwargs):
        engine._sound_frames_for_test.append((wav_bytes, source))
        return {
            "accepted": True,
            "entries_bound": 16,
            "context_id": "test-context",
            "closed_window_id": 1,
            "settlement": {"settled": True},
        }

    engine.process_sound_frame = process_sound_frame
    return engine


def test_registration_and_replay_use_the_same_full_field_boundary():
    engine = _minimal_engine()
    wav_bytes = _pcm_wav()

    registered = engine.register_replayable_sound(
        "bell", "bell", wav_bytes, source="sound_upload:bell")

    assert registered["accepted"] is True
    assert engine._sound_frames_for_test == [(wav_bytes, "sound_upload:bell")]
    record = engine._sounds["bell"]
    assert record["replay_schema"] == REPLAY_SOUND_SCHEMA
    assert "cochlear" not in record
    assert "raw_signal" not in record
    Guala._validate_sounds_payload(engine._sounds, engine.tick)

    replayed = engine.replay_sound_asset(
        "bell", source="autonomous_sound_replay:bell")

    assert replayed["accepted"] is True
    assert engine._sound_frames_for_test[-1] == (
        wav_bytes, "autonomous_sound_replay:bell")
    assert record["times_attended"] == 2


def test_legacy_sound_is_preserved_but_never_fabricated_as_replay_audio():
    engine = _minimal_engine()
    engine._sounds["legacy"] = {
        "item_id": "legacy",
        "title": "legacy",
        "cochlear": {"old": {"winding": 7, "n_events": 2}},
        "raw_signal": [0.25, -0.25],
        "times_attended": 3,
        "last_attended_tick": 12,
    }

    Guala._validate_sounds_payload(engine._sounds, engine.tick)
    replayed = engine.replay_sound_asset("legacy")

    assert replayed == {
        "accepted": False,
        "replay_available": False,
        "reason": "legacy_sound_has_no_retained_16khz_pcm",
    }
    assert engine._sound_frames_for_test == []


def test_autonomy_selects_only_replayable_audio_and_replays_once_per_activity():
    engine = _minimal_engine()
    engine.register_replayable_sound("new", "new", _pcm_wav())
    engine._sounds["legacy"] = {
        "item_id": "legacy",
        "title": "legacy",
        "cochlear": {},
        "times_attended": 0,
        "last_attended_tick": 0,
    }
    engine._corpora = {}
    engine._sensory_items = {}
    engine._pictures = {}
    engine._videos = {}
    engine.coordinator = SimpleNamespace(_presence={}, _pair_bond={})
    engine._last_emission_tick = engine.tick
    engine.needs = SimpleNamespace(novelty=0.5)

    candidates = engine._candidate_activities()
    assert ("ATTENDING_AUDIO", "new") in candidates
    assert ("ATTENDING_AUDIO", "legacy") not in candidates

    activity = SimpleNamespace(target="new", metadata={}, started_tick=engine.tick)
    frames_before = len(engine._sound_frames_for_test)
    engine._atick_attending_audio(activity)
    engine._atick_attending_audio(activity)

    assert len(engine._sound_frames_for_test) == frames_before + 1
    assert activity.metadata["_replayed"] is True
    assert activity.metadata["causal_entries"] == 16


def test_replay_storage_count_and_integrity_are_hard_boundaries():
    engine = _minimal_engine()
    wav_bytes = _pcm_wav()
    for index in range(REPLAY_SOUND_MAX_COUNT):
        engine.register_replayable_sound(
            f"sound-{index}", f"sound {index}", wav_bytes)

    with pytest.raises(ValueError, match="count boundary reached"):
        engine.register_replayable_sound("overflow", "overflow", wav_bytes)

    tampered = dict(engine._sounds["sound-0"])
    tampered["replay_wav_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="sha256 mismatch"):
        Guala._validate_sounds_payload({"sound-0": tampered}, engine.tick)


def test_replay_capture_rejects_non_16khz_audio():
    with pytest.raises(ValueError, match="16 kHz mono PCM16"):
        Guala._canonical_replay_wav(_pcm_wav(sample_rate=8_000))
