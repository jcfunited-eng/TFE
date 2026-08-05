"""Measure exact auditory settlement across native-derived capture cadences.

This is an architecture gate, not a synthetic recognition test.  Every case
uses the public ``/sound_frame`` function, continuous PCM continuity owner,
incremental cochlear state, all 32 auditory native ports, unchanged L0--L4,
auditory L5, causal settlement, and terminal advancement.  Only the physical
duration varies.  The result identifies which lower-level integration cadence
can remain ahead of its own source clock before any browser transport design
is selected.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import statistics
import struct
import time

import dsf_ai_service.app as app_module
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


RAW_SAMPLE_COUNTS = (
    5 * OBSERVATION_HOP_SAMPLES,
    10 * OBSERVATION_HOP_SAMPLES,
    20 * OBSERVATION_HOP_SAMPLES,
    50 * OBSERVATION_HOP_SAMPLES,
    100 * OBSERVATION_HOP_SAMPLES,
    200 * OBSERVATION_HOP_SAMPLES,
    500 * OBSERVATION_HOP_SAMPLES,
)
WARM_SETTLEMENTS = 1
MEASURED_SETTLEMENTS = 3


def _pcm(sample_count: int) -> bytes:
    values = tuple(
        int(
            8_000
            * math.sin(
                2 * math.pi * 440 * index / PCM_SAMPLE_RATE_HZ
            )
        )
        for index in range(sample_count)
    )
    return struct.pack(f"<{sample_count}h", *values)


def _post(
    *,
    stream_id: str,
    sequence: int,
    sample_count: int,
    pcm: bytes,
) -> dict:
    response = asyncio.run(app_module.sound_frame(app_module.GLMessage(
        text=base64.b64encode(pcm).decode("ascii"),
        source="browser_microphone",
        audio_encoding="pcm_s16le",
        audio_stream_id=stream_id,
        audio_sequence=sequence,
        audio_first_sample_index=sequence * sample_count,
        audio_sample_count=sample_count,
        audio_sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        audio_source_epoch_ms=1_000,
        capture_purpose="ambient",
        sight_frames=[],
    )))
    if not isinstance(response, dict) or response.get("ok") is not True:
        raise RuntimeError(
            f"exact auditory cadence probe was rejected: {response}"
        )
    continuity = response.get("pcm_continuity")
    if (
        not isinstance(continuity, dict)
        or continuity.get("status") != "contiguous"
        or continuity.get("sequence") != sequence
    ):
        raise RuntimeError(
            "exact auditory cadence probe lost PCM continuity"
        )
    if response.get("causal_boundary") != "sound":
        raise RuntimeError(
            "exact auditory cadence probe did not settle sound"
        )
    return response


def main() -> None:
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    os.environ["WAVE_ATLAS_ENABLED"] = "0"
    os.environ["WAVE_SUMMARY_ENQUEUE_ENABLED"] = "0"
    os.environ["SELF_HEARING_ENABLED"] = "0"
    os.environ["GUALA_EXACT_FIELD_EXECUTOR_REQUIRED"] = "1"
    os.environ["GUALA_CAUSAL_ACTION_KEY"] = (
        "pcm-cadence-probe-authority"
    )

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    engine = Guala()
    app_module._guala = engine
    app_module._is_remote = lambda: False
    app_module._converse_inflight = 0
    app_module._converse_window_started_at = 0.0
    app_module._auditory_pcm_streams = AuditoryPCMStreamRegistry()
    results = []
    try:
        for sample_count in RAW_SAMPLE_COUNTS:
            pcm = _pcm(sample_count)
            opened = asyncio.run(
                app_module.auditory_pcm_stream_open()
            )
            stream_id = opened["stream_id"]
            durations = []
            try:
                for sequence in range(
                    WARM_SETTLEMENTS + MEASURED_SETTLEMENTS
                ):
                    started = time.perf_counter()
                    _post(
                        stream_id=stream_id,
                        sequence=sequence,
                        sample_count=sample_count,
                        pcm=pcm,
                    )
                    elapsed = time.perf_counter() - started
                    if sequence >= WARM_SETTLEMENTS:
                        durations.append(elapsed)
            finally:
                engine.close_auditory_pcm_stream(
                    stream_id,
                    release_terminal=False,
                )
                app_module._auditory_pcm_streams.close(stream_id)
            source_seconds = (
                sample_count / PCM_SAMPLE_RATE_HZ
            )
            result = {
                "raw_samples": sample_count,
                "observation_hops": (
                    sample_count // OBSERVATION_HOP_SAMPLES
                ),
                "source_seconds": source_seconds,
                "minimum_seconds": min(durations),
                "median_seconds": statistics.median(durations),
                "maximum_seconds": max(durations),
                "headroom_ratio": (
                    source_seconds / max(durations)
                ),
                "kept_pace": max(durations) < source_seconds,
            }
            results.append(result)
            print(json.dumps(result, sort_keys=True), flush=True)
    finally:
        engine.shutdown()
        stop_exact_field_executor()

    print(json.dumps(
        {"cadences": results},
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
