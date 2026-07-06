"""CPU collector.

Samples per-container CPU utilization via /proc/stat. Real code, not
stub — works on Linux dev machines and inside containers.

For AWS ECS metrics (task-level CPU utilization), a separate collector
would wrap CloudWatch — that's marked as a stub in aws_signals.py because
it requires boto3 + credentials that this skeleton doesn't wire.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..types import TraceId
from .collector import Collector, Sample


class CPUCollector(Collector):
    """Per-container CPU utilization from /proc/stat.

    Computes deltas between samples: (busy_delta / total_delta) as a
    percentage. First sample returns 0 (no prior baseline).
    """

    name = "cpu"
    sample_interval_ms = 1000

    def __init__(self, trace_id: TraceId):
        super().__init__(trace_id)
        self._prev_total: int | None = None
        self._prev_busy: int | None = None
        self._proc_stat = Path("/proc/stat")

    async def _sample_once(self) -> Sample | None:
        if not self._proc_stat.exists():
            self._mark_degraded("/proc/stat not present (non-Linux host?)")
            return None

        # /proc/stat first line: "cpu  user nice system idle iowait irq softirq steal guest guest_nice"
        line = self._proc_stat.read_text().splitlines()[0]
        parts = line.split()
        if parts[0] != "cpu" or len(parts) < 8:
            self._mark_degraded(f"unexpected /proc/stat format: {line[:60]!r}")
            return None

        values = [int(v) for v in parts[1:8]]
        user, nice, system, idle, iowait, irq, softirq = values
        total = sum(values)
        busy = total - idle - iowait

        if self._prev_total is None:
            # First sample: no delta yet
            self._prev_total = total
            self._prev_busy = busy
            return Sample(
                t_offset_ms=self.trace_id.t_offset_ms(),
                values={
                    "cpu_pct": 0.0,
                    "user_pct": 0.0,
                    "system_pct": 0.0,
                    "iowait_pct": 0.0,
                    "baseline_established": True,
                },
            )

        total_delta = total - self._prev_total
        busy_delta = busy - self._prev_busy  # type: ignore[operator]
        self._prev_total = total
        self._prev_busy = busy

        if total_delta <= 0:
            return None  # no time passed, skip

        cpu_pct = (busy_delta / total_delta) * 100.0

        return Sample(
            t_offset_ms=self.trace_id.t_offset_ms(),
            values={
                "cpu_pct": round(cpu_pct, 2),
                "user_raw": user,
                "system_raw": system,
                "iowait_raw": iowait,
            },
        )

    def _summarize(self) -> dict[str, Any]:
        if not self._samples:
            return {"sample_count": 0}
        cpu_values = [
            s.values["cpu_pct"] for s in self._samples
            if "cpu_pct" in s.values and not s.values.get(
                "baseline_established", False
            )
        ]
        if not cpu_values:
            return {"sample_count": len(self._samples), "no_useful_samples": True}
        return {
            "sample_count": len(self._samples),
            "peak_cpu_pct": round(max(cpu_values), 2),
            "mean_cpu_pct": round(sum(cpu_values) / len(cpu_values), 2),
            "time_over_80_pct_samples": sum(1 for v in cpu_values if v > 80.0),
            "time_over_90_pct_samples": sum(1 for v in cpu_values if v > 90.0),
        }
