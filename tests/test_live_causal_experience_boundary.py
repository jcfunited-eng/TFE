from __future__ import annotations

import io
import math
import struct
import time
import wave
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _tone_wav() -> bytes:
    sample_rate = 16_000
    samples = [
        int(12_000 * math.sin(2 * math.pi * 440 * index / sample_rate))
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


def test_real_audiovisual_capture_produces_one_queue_free_settlement(
        monkeypatch) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("WAVE_SUMMARY_ENQUEUE_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
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
        assert settlement.source_time_start == Fraction(source_start_ns, 1_000_000_000)
        assert settlement.source_time_end == Fraction(source_start_ns + 5_000_000_000, 1_000_000_000)
        by_sense = {item.sense: item for item in settlement.interpretations}
        assert tuple(by_sense) == (
            "sight", "sound", "touch", "smell", "taste", "body")
        assert len(by_sense["sight"].substreams) == 3
        assert len(by_sense["sound"].substreams) == 6
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
        assert engine._organism_queue is None
        assert engine._organism_sensory_queue.qsize() == 0
        assert engine._organism_sensory_dropped_count == 0
        assert engine.window_manager.open_context_ids() == ()
        assert engine._causal_experience_owner.status()["tracked_senses"] == [
            "sight", "sound"]
    finally:
        engine.shutdown()
