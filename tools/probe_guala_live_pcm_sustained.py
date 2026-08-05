"""Sustain the exact browser PCM plus camera route without persistence.

This invokes the same ``/sound_frame`` route function, continuous PCM
registry, visual sequence decoder, engine mutation executor, L5 settlement,
and causal close used by the public page.  It differs only in supplying fixed
physical bytes instead of waiting for a laptop microphone and camera.
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
from collections import defaultdict
from io import BytesIO

from PIL import Image

import dsf_ai_service.app as app_module
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMStreamRegistry,
    PCM_SAMPLE_RATE_HZ,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from tools.probe_guala_capture_scaling import (
    BASE_PRODUCTION_DEEP_ATLAS_ENTRIES,
)


SETTLEMENT_COUNT = 120
WARM_SETTLEMENT_COUNT = 10
PCM_SAMPLES_PER_SETTLEMENT = 80_000
SOURCE_INTERVAL_MILLISECONDS = 5_000
MAX_RESIDENT_GROWTH_BYTES = 128 * 1024 * 1024


def _pcm() -> bytes:
    values = tuple(
        int(8_000 * math.sin(2 * math.pi * 440 * index / 16_000))
        for index in range(PCM_SAMPLES_PER_SETTLEMENT)
    )
    return struct.pack(f"<{len(values)}h", *values)


def _jpeg_b64() -> str:
    payload = BytesIO()
    Image.new("RGB", (128, 128), color=(30, 90, 170)).save(
        payload,
        format="JPEG",
    )
    return base64.b64encode(payload.getvalue()).decode("ascii")


def _sight_frames(
    *,
    sequence: int,
    encoded_frame: str,
) -> list[app_module.GLVisualFrameClaim]:
    source_start_ms = (
        1_000 + sequence * SOURCE_INTERVAL_MILLISECONDS
    )
    return [
        app_module.GLVisualFrameClaim(
            captured_ms=source_start_ms + offset,
            frame_b64=encoded_frame,
        )
        for offset in (800, 1_600, 2_400, 3_200)
    ]


def _post(
    *,
    stream_id: str,
    sequence: int,
    pcm: bytes,
    encoded_frame: str,
) -> dict:
    response = asyncio.run(app_module.sound_frame(app_module.GLMessage(
        text=base64.b64encode(pcm).decode("ascii"),
        source="browser_microphone",
        audio_encoding="pcm_s16le",
        audio_stream_id=stream_id,
        audio_sequence=sequence,
        audio_first_sample_index=(
            sequence * PCM_SAMPLES_PER_SETTLEMENT
        ),
        audio_sample_count=PCM_SAMPLES_PER_SETTLEMENT,
        audio_sample_rate_hz=PCM_SAMPLE_RATE_HZ,
        audio_source_epoch_ms=1_000,
        sight_frames=_sight_frames(
            sequence=sequence,
            encoded_frame=encoded_frame,
        ),
    )))
    if not isinstance(response, dict):
        raise RuntimeError("live PCM route returned a non-object response")
    if response.get("ok") is not True:
        raise RuntimeError(
            f"live PCM route rejected settlement: {response}"
        )
    continuity = response.get("pcm_continuity")
    if (
        not isinstance(continuity, dict)
        or continuity.get("sequence") != sequence
        or continuity.get("status") != "contiguous"
    ):
        raise RuntimeError(
            "live PCM route did not publish exact continuity"
        )
    if response.get("causal_boundary") != "audiovisual":
        raise RuntimeError(
            "live PCM route did not settle one audiovisual boundary: "
            f"{response}"
        )
    return response


def _rss_bytes(process_id: int) -> int:
    with open(f"/proc/{process_id}/status", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError(f"resident memory unavailable for process {process_id}")


def _total_rss(process_ids: tuple[int, ...]) -> int:
    return sum(_rss_bytes(process_id) for process_id in process_ids)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(fraction * len(ordered)))
    return ordered[index]


def main() -> None:
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    os.environ["WAVE_ATLAS_ENABLED"] = "0"
    os.environ["WAVE_SUMMARY_ENQUEUE_ENABLED"] = "0"
    os.environ["SELF_HEARING_ENABLED"] = "0"
    os.environ["GUALA_CAUSAL_ACTION_KEY"] = (
        "live-pcm-sustained-probe-authority"
    )
    owner = start_exact_field_executor()
    process_ids = (os.getpid(), *owner.worker_pids)
    engine = Guala()
    engine.deep_atlas.entries = defaultdict(
        list,
        (
            (index, [])
            for index in range(BASE_PRODUCTION_DEEP_ATLAS_ENTRIES)
        ),
    )
    app_module._guala = engine
    app_module._is_remote = lambda: False
    app_module._converse_inflight = 0
    app_module._converse_window_started_at = 0.0
    app_module._auditory_pcm_streams = AuditoryPCMStreamRegistry()
    pcm = _pcm()
    encoded_frame = _jpeg_b64()
    durations: list[float] = []
    resident_samples: list[int] = []
    stream_id = asyncio.run(
        app_module.auditory_pcm_stream_open()
    )["stream_id"]
    engine.start_autonomy_loop(interval=0.2)
    try:
        for sequence in range(WARM_SETTLEMENT_COUNT):
            _post(
                stream_id=stream_id,
                sequence=sequence,
                pcm=pcm,
                encoded_frame=encoded_frame,
            )
        resident_samples.append(_total_rss(process_ids))
        for measured_index, sequence in enumerate(
            range(
                WARM_SETTLEMENT_COUNT,
                WARM_SETTLEMENT_COUNT + SETTLEMENT_COUNT,
            ),
            start=1,
        ):
            started = time.perf_counter()
            _post(
                stream_id=stream_id,
                sequence=sequence,
                pcm=pcm,
                encoded_frame=encoded_frame,
            )
            durations.append(time.perf_counter() - started)
            if measured_index % 10 == 0:
                resident_samples.append(_total_rss(process_ids))
                print(json.dumps({
                    "completed": measured_index,
                    "last_seconds": round(durations[-1], 6),
                    "maximum_seconds": round(max(durations), 6),
                    "resident_bytes": resident_samples[-1],
                }), flush=True)
    finally:
        engine.close_auditory_pcm_stream(stream_id)
        engine.shutdown()
        stop_exact_field_executor()
    resident_growth = resident_samples[-1] - resident_samples[0]
    result = {
        "settlements": len(durations),
        "raw_pcm_samples_per_settlement": (
            PCM_SAMPLES_PER_SETTLEMENT
        ),
        "source_interval_seconds": (
            SOURCE_INTERVAL_MILLISECONDS / 1_000
        ),
        "minimum_seconds": round(min(durations), 6),
        "median_seconds": round(statistics.median(durations), 6),
        "p95_seconds": round(_percentile(durations, 0.95), 6),
        "p99_seconds": round(_percentile(durations, 0.99), 6),
        "maximum_seconds": round(max(durations), 6),
        "deadline_failures": sum(
            duration
            >= SOURCE_INTERVAL_MILLISECONDS / 1_000
            for duration in durations
        ),
        "initial_resident_bytes": resident_samples[0],
        "final_resident_bytes": resident_samples[-1],
        "peak_observed_resident_bytes": max(resident_samples),
        "resident_growth_bytes": resident_growth,
        "resident_growth_limit_bytes": MAX_RESIDENT_GROWTH_BYTES,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["deadline_failures"]:
        raise RuntimeError(
            "live PCM route exceeded its physical source interval"
        )
    if resident_growth > MAX_RESIDENT_GROWTH_BYTES:
        raise RuntimeError(
            "live PCM route exceeded its resident growth boundary"
        )


if __name__ == "__main__":
    main()
