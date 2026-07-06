"""Memory collector.

Samples memory via /proc/self/status (harness process itself as a
baseline) and /proc/meminfo (host memory). For the substrate under test,
memory metrics come from CloudWatch (ECS task-level) or docker stats —
those are wrapped in aws_signals.py.

This collector's job is to observe the harness's own memory usage while
running plus host memory pressure — the runtime environment the harness
depends on staying healthy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..types import TraceId
from .collector import Collector, Sample


class MemoryCollector(Collector):
    """Harness-process RSS + host memory pressure indicators.

    Substrate-side memory (the container the substrate runs in) requires
    CloudWatch or docker stats — separate collector.
    """

    name = "memory"
    sample_interval_ms = 1000

    def __init__(self, trace_id: TraceId):
        super().__init__(trace_id)
        self._status_path = Path("/proc/self/status")
        self._meminfo_path = Path("/proc/meminfo")
        self._initial_rss_kb: int | None = None

    async def _sample_once(self) -> Sample | None:
        if not self._status_path.exists() or not self._meminfo_path.exists():
            self._mark_degraded("/proc memory sources unavailable")
            return None

        rss_kb = self._read_rss_kb()
        meminfo = self._read_meminfo()

        if self._initial_rss_kb is None:
            self._initial_rss_kb = rss_kb

        rss_delta_mb = (rss_kb - self._initial_rss_kb) / 1024.0

        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={
                "harness_rss_mb": round(rss_kb / 1024.0, 2),
                "harness_rss_delta_mb": round(rss_delta_mb, 2),
                "host_mem_available_mb": round(
                    meminfo.get("MemAvailable", 0) / 1024.0, 2
                ),
                "host_mem_pressure_pct": round(
                    100.0 * (
                        1.0 - meminfo.get("MemAvailable", 0)
                        / max(meminfo.get("MemTotal", 1), 1)
                    ),
                    2,
                ),
            },
        )

    def _read_rss_kb(self) -> int:
        for line in self._status_path.read_text().splitlines():
            if line.startswith("VmRSS:"):
                # "VmRSS:\t   12345 kB"
                parts = line.split()
                return int(parts[1])
        return 0

    def _read_meminfo(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for line in self._meminfo_path.read_text().splitlines():
            # "MemTotal:       16384000 kB"
            if ":" in line:
                key, rest = line.split(":", 1)
                parts = rest.strip().split()
                if parts and parts[0].isdigit():
                    result[key.strip()] = int(parts[0])
        return result

    def _summarize(self) -> dict[str, Any]:
        if not self._samples:
            return {"sample_count": 0}
        rss_deltas = [
            s.values.get("harness_rss_delta_mb", 0) for s in self._samples
        ]
        pressures = [
            s.values.get("host_mem_pressure_pct", 0) for s in self._samples
        ]
        return {
            "sample_count": len(self._samples),
            "peak_rss_delta_mb": round(max(rss_deltas), 2) if rss_deltas else 0,
            "final_rss_delta_mb": round(rss_deltas[-1], 2) if rss_deltas else 0,
            "peak_host_pressure_pct": round(max(pressures), 2) if pressures else 0,
            "mean_host_pressure_pct": (
                round(sum(pressures) / len(pressures), 2) if pressures else 0
            ),
        }
