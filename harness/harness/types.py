"""Shared types for the harness.

Kept minimal: verdict enum, trace ID with wall-clock anchor, and a small
timing helper. Everything downstream depends on these being stable.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """Harness run outcome. Exit codes match spec §4.2."""

    PASS = "PASS"                        # exit 0
    FAIL = "FAIL"                        # exit 1
    TIMEOUT = "TIMEOUT"                  # exit 2
    RESOURCE_CAP = "RESOURCE_CAP"        # exit 3
    PRECONDITION_NOT_MET = "PRECONDITION_NOT_MET"  # exit 4
    RESTORE_FAILED = "RESTORE_FAILED"    # exit 5

    def exit_code(self) -> int:
        return {
            Verdict.PASS: 0,
            Verdict.FAIL: 1,
            Verdict.TIMEOUT: 2,
            Verdict.RESOURCE_CAP: 3,
            Verdict.PRECONDITION_NOT_MET: 4,
            Verdict.RESTORE_FAILED: 5,
        }[self]


@dataclass(frozen=True)
class TraceId:
    """Uniquely identifies a run, anchors wall-clock and monotonic clocks
    so every observability stream and every substrate event can be
    correlated to a single run."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    wall_clock_start: float = field(default_factory=time.time)
    monotonic_start: float = field(default_factory=time.monotonic)

    def t_offset_ms(self, monotonic_now: float | None = None) -> int:
        """Milliseconds since run start. Used to timestamp every observation
        against the run's own zero rather than wall-clock."""
        if monotonic_now is None:
            monotonic_now = time.monotonic()
        return int((monotonic_now - self.monotonic_start) * 1000)


@dataclass
class Finding:
    """Structured finding surfaced during a run. See spec §6.9."""

    severity: str          # INFO | WATCH | WARN | CRITICAL
    source: str            # which collector or checker produced this
    message: str
    detail: dict = field(default_factory=dict)
    t_offset_ms: int = 0
