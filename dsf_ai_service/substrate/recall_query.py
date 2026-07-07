"""Recall query: chi values in, ranked binding windows out.

Per GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1 and
GL-CMD-CROSS-SENSE-RECALL-BUILD-EVE-20260706-v1. Turns "the sound cue
came in" into "here are the windows that had this sound, one of which
also has the picture and the word." Reads GL-CMD-BINDING-WINDOWS-BUILD-
EVE-20260706-v1's atlas.windows (closed binding windows, plain dicts)
-- never writes to it, never touches how windows are formed.

Scope of this build (GL-CMD-CROSS-SENSE-RECALL-BUILD-EVE-20260706-v1):
walk atlas.windows, rank by exactly three factors (recency, affect
strength at window formation, section match), return top-N. No
caching -- runs live every call. No new ranking factors. Recall
results are NOT wired into the live conversational emission/
composition path in this build -- see the module docstring note below
and the build report for why.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RecallQuery:
    """Query parameters for a recall lookup."""

    chis: list          # list[int] -- the chi values to search for
    section_hint: Optional[str] = None   # e.g. "sound" -- boosts matching windows
    source_context: dict = field(default_factory=dict)
    max_results: int = 5


@dataclass
class RecallResult:
    """Ranked list of windows matching a query."""

    query_id: str
    windows: list = field(default_factory=list)   # list[dict] -- ranked, highest first
    duration_ms: float = 0.0

    def window_ids(self) -> list:
        return [w.get("window_id") for w in self.windows]

    def top_affect_strength(self) -> float:
        if not self.windows:
            return 0.0
        return _affect_strength(self.windows[0])


def _affect_strength(window: dict) -> float:
    """Affect strength at window formation: arousal (magnitude of
    activation) plus |valence| (magnitude of pleasant/unpleasant pull) --
    both already captured in the window's own affect_snapshot at close()
    time, no new signal invented."""
    snap = window.get("affect_snapshot") or {}
    return abs(snap.get("arousal", 0.0)) + abs(snap.get("valence", 0.0))


class RecallEngine:
    """Reads atlas.windows (never writes it). One method: query()."""

    def __init__(self, atlas_windows_fn, get_tick_fn, log_event_fn):
        """
        atlas_windows_fn: callable() -> dict, returns the atlas's own
            `windows` dict (same object each call, read live -- no
            caching, no copy taken at construction time).
        get_tick_fn: callable() -> int, current engine tick (for recency
            scoring relative to "now").
        log_event_fn: Guala._log_substrate_event.
        """
        self._get_windows = atlas_windows_fn
        self._get_tick = get_tick_fn
        self._log_event = log_event_fn

    def query(self, request: RecallQuery) -> RecallResult:
        t0 = time.monotonic()
        query_id = f"rq_{uuid.uuid4().hex[:12]}"
        query_chis = set(request.chis or [])
        windows = self._get_windows()
        now_tick = self._get_tick()

        matches = []
        for window in windows.values():
            entries = window.get("entries") or []
            hit_entries = [e for e in entries if e.get("chi") in query_chis]
            if not hit_entries:
                continue

            # Factor 1: recency -- higher (more recent) closed_tick wins.
            # Scored as closeness to "now" so it combines cleanly with the
            # other two [0, ~few] factors instead of dwarfing them with a
            # raw tick number.
            closed_tick = window.get("closed_tick") or window.get("opened_tick", 0)
            age = max(0, now_tick - closed_tick)
            recency_score = 1.0 / (1.0 + age / 1000.0)

            # Factor 2: affect strength at window formation.
            affect_score = _affect_strength(window)

            # Factor 3: section match -- query's section hint matches any
            # hit entry's section/modality.
            section_score = 0.0
            if request.section_hint:
                for e in hit_entries:
                    if (e.get("section") == request.section_hint
                            or e.get("modality") == request.section_hint):
                        section_score = 1.0
                        break

            rank_score = recency_score + affect_score + section_score
            matches.append((rank_score, window))

        matches.sort(key=lambda m: -m[0])
        top_windows = [w for _score, w in matches[:max(1, request.max_results)]]

        duration_ms = (time.monotonic() - t0) * 1000
        result = RecallResult(query_id=query_id, windows=top_windows,
                              duration_ms=duration_ms)

        self._log_event(
            "recall_query_executed",
            query_id=query_id,
            input_chis=list(query_chis)[:20],
            windows_returned_count=len(top_windows),
            windows_returned_ids=result.window_ids(),
            top_result_affect_strength=round(result.top_affect_strength(), 4),
            wall_clock=time.time(),
            duration_ms=round(duration_ms, 3),
        )
        return result
