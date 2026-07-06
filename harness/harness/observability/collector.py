"""Base Collector class.

Every observability stream in spec §5 implements this interface. The
runner starts all collectors before probe injection, snapshots them
periodically during the run, stops them after cleanup, and merges their
outputs into the report.

Design constraints:
- Async throughout: collectors run concurrently with the probe.
- Each collector owns its own state. No shared mutable state between
  collectors. This mirrors the substrate spec's message-passing shape.
- Collectors do not raise into the runner: any exception is captured as
  a Finding and the collector marks itself degraded. A degraded collector
  still returns a snapshot with whatever it managed to gather.
- Collectors are cheap when idle: minimal sampling until start() is
  called.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..types import Finding, TraceId


@dataclass
class Sample:
    """One observation from a collector."""

    t_offset_ms: int
    values: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectorSnapshot:
    """Final output of a collector at run end."""

    name: str
    samples: list[Sample] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    degraded: bool = False
    degraded_reason: str | None = None


class Collector(ABC):
    """Base for every observability stream.

    Subclasses implement _sample_once() and _summarize(). The base class
    handles the sampling loop, exception isolation, and snapshot assembly.
    """

    name: str
    sample_interval_ms: int = 1000

    def __init__(self, trace_id: TraceId):
        self.trace_id = trace_id
        self._samples: list[Sample] = []
        self._findings: list[Finding] = []
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._degraded = False
        self._degraded_reason: str | None = None

    async def start(self) -> None:
        """Start the sampling loop. Non-blocking — returns immediately after
        scheduling the loop task."""
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name=f"collector:{self.name}")

    async def stop(self) -> None:
        """Signal stop and await the sampling task."""
        self._stop_event.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                self._add_finding(
                    "WARN",
                    f"collector {self.name} did not stop within 5s; cancelled",
                )
            self._task = None

    def snapshot(self) -> CollectorSnapshot:
        """Assemble the final snapshot. Called after stop() by the runner."""
        try:
            summary = self._summarize()
        except Exception as e:  # collectors do not raise into runner
            summary = {}
            self._add_finding(
                "WARN",
                f"summarize failed for {self.name}: {type(e).__name__}: {e}",
            )
        return CollectorSnapshot(
            name=self.name,
            samples=list(self._samples),
            summary=summary,
            findings=list(self._findings),
            degraded=self._degraded,
            degraded_reason=self._degraded_reason,
        )

    async def _run(self) -> None:
        """The sampling loop. Runs until stop_event is set."""
        interval = self.sample_interval_ms / 1000.0
        while not self._stop_event.is_set():
            try:
                sample = await self._sample_once()
                if sample is not None:
                    self._samples.append(sample)
            except Exception as e:
                self._mark_degraded(
                    f"{type(e).__name__} in sample: {e}"
                )
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=interval
                )
            except asyncio.TimeoutError:
                pass  # normal: means we hit the sample interval

    def _mark_degraded(self, reason: str) -> None:
        """Mark this collector as degraded — still returns partial data."""
        if not self._degraded:
            self._degraded = True
            self._degraded_reason = reason
            self._add_finding("WATCH", f"collector {self.name} degraded: {reason}")

    def _add_finding(self, severity: str, message: str, **detail) -> None:
        self._findings.append(
            Finding(
                severity=severity,
                source=f"collector:{self.name}",
                message=message,
                detail=detail,
                t_offset_ms=self.trace_id.t_offset_ms(),
            )
        )

    @abstractmethod
    async def _sample_once(self) -> Sample | None:
        """Take one sample. Called at sample_interval_ms cadence.

        Returns None if no observation is available at this moment (not
        an error). Raises for real errors — the base class catches and
        marks degraded.
        """

    def _summarize(self) -> dict[str, Any]:
        """Aggregate samples into a summary dict for the report.

        Default: max, mean, count of numeric values across samples.
        Override for collector-specific summaries.
        """
        if not self._samples:
            return {"sample_count": 0}
        numeric_keys: dict[str, list[float]] = {}
        for sample in self._samples:
            for key, val in sample.values.items():
                if isinstance(val, (int, float)):
                    numeric_keys.setdefault(key, []).append(val)
        summary: dict[str, Any] = {"sample_count": len(self._samples)}
        for key, vals in numeric_keys.items():
            summary[f"{key}_max"] = max(vals)
            summary[f"{key}_mean"] = sum(vals) / len(vals)
        return summary
