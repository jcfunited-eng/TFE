from __future__ import annotations

import io
import math
import struct
import time
import wave
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _tone_wav(frequency_hz: float = 440.0, amplitude: int = 12_000) -> bytes:
    sample_rate = 16_000
    samples = [
        int(amplitude * math.sin(2 * math.pi * frequency_hz * index / sample_rate))
        for index in range(sample_rate)
    ]
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return payload.getvalue()


def _sight_grid() -> np.ndarray:
    rows, columns = np.indices((64, 64))
    return (((rows * 17 + columns * 31) % 256) / 255.0).astype(np.float64)


def _configure_embedded_engine(monkeypatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    return Guala()


def test_real_audiovisual_capture_produces_one_queue_free_settlement(
        monkeypatch) -> None:
    engine = _configure_embedded_engine(monkeypatch)
    context_id = "test:av:one"
    try:
        source_start_ns = time.time_ns()
        engine.window_manager.begin_context(
            context_id,
            "audiovisual_capture",
            context_detail={
                "source_time_start_ns": source_start_ns,
                "source_time_end_ns": source_start_ns + 5_000_000_000,
                "sensor_unavailable": ["touch", "smell", "taste", "body"],
            },
        )
        engine.process_sight_frame(_sight_grid())
        engine.process_sound_frame(_tone_wav(), source="joe_voice")
        engine.window_manager.end_context(
            context_id, "audiovisual_capture_complete")

        assert engine._causal_settlement_accepted == 1
        assert engine._causal_settlement_failed == 0
        assert engine._latest_causal_settlement is not None
        settlement = engine._latest_causal_settlement
        settlement.verify()
        assert settlement.source_time_start == Fraction(
            source_start_ns, 1_000_000_000
        )
        assert settlement.source_time_end == Fraction(
            source_start_ns + 5_000_000_000, 1_000_000_000
        )
        by_sense = {item.sense: item for item in settlement.interpretations}
        assert tuple(by_sense) == (
            "sight", "sound", "touch", "smell", "taste", "body"
        )
        assert len(by_sense["sight"].substreams) == 3
        assert len(by_sense["sound"].substreams) == len(AUDITORY_CHANNELS)
        assert tuple(
            item.substream_id for item in by_sense["sound"].substreams
        ) == tuple(item.name for item in AUDITORY_CHANNELS)
        assert all(
            tuple(name for name, _value in field_tuple.fields)
            == DSF_FIELD_ORDER
            for sense in ("sight", "sound")
            for substream in by_sense[sense].substreams
            for field_tuple in substream.field_tuples
        )
        assert all(
            substream.field_tuples
            for sense in ("sight", "sound")
            for substream in by_sense[sense].substreams
        )
        assert settlement.routing_chis
        assert settlement.source_tags == ("cam:live", "joe_voice")
        assert engine._latest_auditory_l5_experience is not None
        assert len(engine._latest_auditory_l5_experience.ports) == len(
            AUDITORY_CHANNELS
        )
        assert engine._organism_queue is None
        assert engine._organism_sensory_queue.qsize() == 0
        assert engine._organism_sensory_dropped_count == 0
        assert engine.window_manager.open_context_ids() == ()
        assert engine._causal_experience_owner.status()["tracked_senses"] == [
            "sight", "sound"
        ]
    finally:
        engine.shutdown()


def test_live_sound_full_field_distinguishes_frequency_and_amplitude(
        monkeypatch) -> None:
    engine = _configure_embedded_engine(monkeypatch)
    anchor_ns = 1_000_000_000_000
    try:
        first = engine.process_sound_frame(
            _tone_wav(440.0, 8_000),
            source="untrusted-client-label",
            source_anchor_ns=anchor_ns,
            source_time_end_ns=anchor_ns + 1_000_000_000,
        )["settlement"]
        first_l5 = engine._latest_auditory_l5_experience
        repeated = engine.process_sound_frame(
            _tone_wav(440.0, 8_000),
            source="a-different-untrusted-label",
            source_anchor_ns=anchor_ns,
            source_time_end_ns=anchor_ns + 1_000_000_000,
        )["settlement"]
        repeated_l5 = engine._latest_auditory_l5_experience
        changed_frequency = engine.process_sound_frame(
            _tone_wav(640.0, 8_000),
            source="untrusted-client-label",
            source_anchor_ns=anchor_ns,
            source_time_end_ns=anchor_ns + 1_000_000_000,
        )["settlement"]
        changed_frequency_l5 = engine._latest_auditory_l5_experience
        changed_amplitude = engine.process_sound_frame(
            _tone_wav(640.0, 16_000),
            source="untrusted-client-label",
            source_anchor_ns=anchor_ns,
            source_time_end_ns=anchor_ns + 1_000_000_000,
        )["settlement"]
        changed_amplitude_l5 = engine._latest_auditory_l5_experience

        for settlement in (
            first, repeated, changed_frequency, changed_amplitude
        ):
            settlement.verify()
        sound = lambda settlement: next(
            item for item in settlement.interpretations if item.sense == "sound"
        )
        assert sound(first).relation == "first_observation"
        assert sound(repeated).relation == "recurrence"
        assert sound(changed_frequency).relation == "recurrence"
        assert sound(changed_amplitude).relation == "recurrence"
        assert sound(first).structural_fingerprint == (
            sound(repeated).structural_fingerprint
        )
        assert sound(first).structural_fingerprint == (
            sound(changed_frequency).structural_fingerprint
        )
        assert sound(changed_frequency).structural_fingerprint == (
            sound(changed_amplitude).structural_fingerprint
        )
        assert first_l5.relation == "first_observation"
        assert repeated_l5.relation == "recurrence"
        assert changed_frequency_l5.relation == "structural_change"
        assert changed_amplitude_l5.relation == "structural_change"
        assert first_l5.structural_fingerprint == (
            repeated_l5.structural_fingerprint
        )
        assert first_l5.structural_fingerprint != (
            changed_frequency_l5.structural_fingerprint
        )
        assert changed_frequency_l5.structural_fingerprint != (
            changed_amplitude_l5.structural_fingerprint
        )
        assert first.source_tags != repeated.source_tags
        assert first.structural_fingerprint == repeated.structural_fingerprint
        assert engine._causal_experience_owner.status()[
            "transition_relations"
        ] <= 1_024
        assert engine._auditory_l5_owner.status()[
            "transition_relations"
        ] <= 1_024
    finally:
        engine.shutdown()
