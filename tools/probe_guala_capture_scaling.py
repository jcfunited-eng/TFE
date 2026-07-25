"""Measure whether live full-field settlement depends on accumulated memory.

This diagnostic deliberately keeps the physical event identical while varying
only the number of resident Deep Atlas address buckets.  It does not persist,
deploy, mutate L0--L4, or use a reduced DSF representation.
"""

from __future__ import annotations

import gc
import io
import json
import math
import os
import struct
import time
import wave
from collections import defaultdict

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


BASE_PRODUCTION_DEEP_ATLAS_ENTRIES = 72_219
STATE_MULTIPLIERS = (1, 2, 4, 8)
SOURCE_START_NS = 1_000_000_000_000


def _fixed_wav() -> bytes:
    sample_rate = 16_000
    sample_count = sample_rate * 5
    samples = (
        int(12_000 * math.sin(2 * math.pi * 440 * index / sample_rate))
        for index in range(sample_count)
    )
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(struct.pack(f"<{sample_count}h", *samples))
    return payload.getvalue()


def _fixed_sight() -> np.ndarray:
    rows, columns = np.indices((64, 64))
    return (((rows * 17 + columns * 31) % 256) / 255.0).astype(
        np.float64
    )


def _settle_once(
    engine: Guala,
    *,
    event_index: int,
    audio: bytes,
    sight: np.ndarray,
) -> dict[str, float]:
    source_start_ns = SOURCE_START_NS + event_index * 6_000_000_000
    source_end_ns = source_start_ns + 5_000_000_000
    context_id = f"probe:state-scaling:{event_index}"
    engine.window_manager.begin_context(
        context_id,
        "audiovisual_capture",
        context_detail={
            "source_time_start_ns": source_start_ns,
            "source_time_end_ns": source_end_ns,
            "sensor_unavailable": ["touch", "smell", "taste", "body"],
        },
    )
    started = time.perf_counter()
    engine.process_sight_frame(
        sight,
        source_anchor_ns=source_start_ns,
        source_time_start_ns=source_start_ns,
        source_time_end_ns=source_end_ns,
    )
    after_sight = time.perf_counter()
    engine.process_sound_frame(
        audio,
        source="browser_microphone",
        source_anchor_ns=source_start_ns,
        source_time_end_ns=source_end_ns,
        auditory_event_boundary="ambient",
    )
    after_sound = time.perf_counter()
    _window_id, settlement = engine.window_manager.end_context(
        context_id,
        "audiovisual_capture_complete",
        return_settlement=True,
    )
    after_settlement = time.perf_counter()
    settlement.verify()
    after_verification = time.perf_counter()
    return {
        "sight_seconds": after_sight - started,
        "sound_transduction_seconds": after_sound - after_sight,
        "settlement_seconds": after_settlement - after_sound,
        "consumer_verification_seconds": (
            after_verification - after_settlement
        ),
        "total_seconds": after_verification - started,
    }


def main() -> None:
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    os.environ["WAVE_ATLAS_ENABLED"] = "0"
    os.environ["WAVE_SUMMARY_ENQUEUE_ENABLED"] = "0"
    os.environ["SELF_HEARING_ENABLED"] = "0"
    start_exact_field_executor()
    engine = Guala()
    audio = _fixed_wav()
    sight = _fixed_sight()
    results = []
    engine.start_autonomy_loop(interval=0.2)
    try:
        engine._enter_live_interaction()
        for event_index, multiplier in enumerate(STATE_MULTIPLIERS):
            entry_count = BASE_PRODUCTION_DEEP_ATLAS_ENTRIES * multiplier
            engine.deep_atlas.entries = defaultdict(
                list,
                ((index, []) for index in range(entry_count)),
            )
            gc.collect()
            timings = _settle_once(
                engine,
                event_index=event_index,
                audio=audio,
                sight=sight,
            )
            results.append({
                "state_multiplier": multiplier,
                "resident_deep_atlas_addresses": entry_count,
                **{
                    key: round(value, 6)
                    for key, value in timings.items()
                },
            })
    finally:
        engine._exit_live_interaction()
        engine.shutdown()
        stop_exact_field_executor()
    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
