"""Chi routing over canonical binding-window memory.

Recall returns every complete window containing any requested Chi.  It never
reduces a window to a weighted score and never uses a top-k truncation as a
decision authority.  Chi coverage is explicitly a reduced routing projection,
not structural recognition.  Language Fact-Strand reciprocity remains the
only language-recognition authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from dsf_ai_service.substrate.window_manager import (
    WindowManager,
    WindowStoreIntegrityHalt,
    _json_safe,
    manager_for_compatibility_mirror,
)


@dataclass
class RecallQuery:
    """Exact structural query.

    ``max_results`` remains accepted for transport compatibility but is not
    applied.  Truncating structurally matching memory would manufacture a
    winner from storage order.
    """

    chis: list
    section_hint: Optional[str] = None
    source_context: dict = field(default_factory=dict)
    max_results: Optional[int] = 5


@dataclass
class RecallResult:
    """Full structural candidates and their honest resolution state."""

    query_id: str
    windows: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    resolution: str = "unknown"
    selected_window_id: Optional[str] = None
    unknown_reason: Optional[str] = None
    routing_projection: str = "chi_index"
    decision_authority: bool = False
    source_context: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    truncated: bool = False

    def window_ids(self) -> list:
        return [window.get("window_id") for window in self.windows]

    def selected_window(self) -> Optional[dict]:
        if self.selected_window_id is None:
            return None
        return next(
            (window for window in self.windows
             if window.get("window_id") == self.selected_window_id),
            None)

    def top_affect_strength(self) -> float:
        """Compatibility helper: affect of the uniquely resolved window only.

        There is deliberately no "top" affect value when recall is ambiguous;
        returning zero preserves the old numeric response field without using
        affect magnitude to break a structural tie.
        """
        selected = self.selected_window()
        return _affect_strength(selected) if selected is not None else 0.0


def _affect_strength(window: Optional[dict]) -> float:
    if not window:
        return 0.0
    snapshot = window.get("affect_snapshot") or {}
    arousal = snapshot.get("arousal", 0.0)
    valence = snapshot.get("valence", 0.0)
    if not isinstance(arousal, (int, float)) or not isinstance(
            valence, (int, float)):
        return 0.0
    return abs(float(arousal)) + abs(float(valence))


def _candidate_for(window: dict, query_chis: tuple[int, ...],
                   section_hint: Optional[str]) -> dict:
    query_set = set(query_chis)
    hit_entries = [
        entry for entry in window.get("entries") or []
        if entry.get("chi") in query_set
    ]
    matched_set = {int(entry["chi"]) for entry in hit_entries}
    matched_chis = [chi for chi in query_chis if chi in matched_set]
    hint_match = None
    if section_hint is not None:
        hint_match = any(
            entry.get("section") == section_hint
            or entry.get("modality") == section_hint
            for entry in hit_entries)
    facts = []
    for entry in hit_entries:
        fact = (entry.get("provenance") or {}).get("structural_fact")
        if fact is not None:
            facts.append(copy.deepcopy(fact))
    return {
        "window_id": window["window_id"],
        "matched_chis": matched_chis,
        "unmatched_chis": [chi for chi in query_chis if chi not in matched_set],
        "matched_entry_indices": [entry["entry_index"] for entry in hit_entries],
        "matched_modalities": list(dict.fromkeys(
            entry.get("modality") for entry in hit_entries)),
        "matched_sections": list(dict.fromkeys(
            entry.get("section") for entry in hit_entries)),
        "section_hint": section_hint,
        "section_hint_match": hint_match,
        "structural_facts": facts,
    }


def _resolve(candidates: list[dict]) -> tuple[str, Optional[str], Optional[str]]:
    if not candidates:
        return "unknown", None, "no_chi_route"
    return "routing_candidates", None, "requires_fact_strand_reciprocity"


class RecallEngine:
    """Routes chi -> window_id through the atlas's own cross-reference
    (GL-FIX-CHI-INDEX-ELIMINATION-20260720); fetches full window content
    from WindowManager, which stays the sole content authority."""

    def __init__(self, atlas_windows_fn=None, get_tick_fn=None,
                 log_event_fn=None, *, window_manager: Optional[WindowManager] = None,
                 atlas=None):
        # Current engine wiring passes only lambda: atlas.windows.  Resolve that
        # compatibility mirror to its owner once; query() never scans the mirror.
        if window_manager is None and atlas_windows_fn is not None:
            mirror = atlas_windows_fn()
            window_manager = manager_for_compatibility_mirror(mirror)
        if window_manager is None:
            raise ValueError(
                "RecallEngine requires canonical WindowManager memory; an "
                "unregistered Atlas windows mapping cannot be recall authority")
        if atlas is None or not hasattr(atlas, "window_ids_for_chis"):
            raise ValueError(
                "RecallEngine requires the living atlas (window_ids_for_chis) "
                "as its chi routing authority -- the window store no longer "
                "maintains its own separate chi index")
        self._window_manager = window_manager
        self._atlas = atlas
        self._get_tick = get_tick_fn or (lambda: 0)
        self._log_event = log_event_fn or (lambda *_args, **_kwargs: None)
        self._query_lock = threading.Lock()
        self._query_sequence = 0

    def _next_query_id(self, query_chis: tuple[int, ...],
                       source_context: dict) -> str:
        with self._query_lock:
            sequence = self._query_sequence
            self._query_sequence += 1
        identity = hashlib.sha256(json.dumps(
            {"chis": query_chis, "source_context": source_context},
            allow_nan=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()[:16]
        return f"rq_{sequence:016x}_{identity}"

    def query(self, request: RecallQuery) -> RecallResult:
        if not isinstance(request, RecallQuery):
            raise TypeError("request must be RecallQuery")
        started = time.monotonic()
        query_chis = tuple(dict.fromkeys(int(chi) for chi in (request.chis or [])))
        source_context = _json_safe(
            request.source_context or {}, "recall.source_context")
        query_id = self._next_query_id(query_chis, source_context)

        # GL-FIX-CHI-INDEX-ELIMINATION-20260720: chi -> window_id routes
        # through the atlas's own cross-reference (record()'s window_id
        # field), not a second, separate index the window store used to
        # maintain purely for this one caller. Content fetch stays with
        # WindowManager, already fetch-on-demand (never a boot cost).
        window_ids = self._atlas.window_ids_for_chis(query_chis)
        windows = []
        for window_id in window_ids:
            window = self._window_manager.closed_window(window_id)
            if window is None:
                raise WindowStoreIntegrityHalt(
                    f"atlas references closed window {window_id!r} but no "
                    f"durable content exists for it.")
            windows.append(window)
        windows.sort(key=lambda window: window["window_id"])
        candidates = [
            _candidate_for(window, query_chis, request.section_hint)
            for window in windows
        ]
        resolution, selected_window_id, unknown_reason = _resolve(candidates)
        duration_ms = (time.monotonic() - started) * 1000.0
        result = RecallResult(
            query_id=query_id,
            windows=windows,
            candidates=candidates,
            resolution=resolution,
            selected_window_id=selected_window_id,
            unknown_reason=unknown_reason,
            routing_projection="chi_index",
            decision_authority=False,
            source_context=source_context,
            duration_ms=duration_ms,
            truncated=False,
        )

        self._log_event(
            "recall_query_executed",
            query_id=query_id,
            input_chis=list(query_chis),
            source_context=source_context,
            windows_returned_count=len(windows),
            windows_returned_ids=result.window_ids(),
            resolution=resolution,
            selected_window_id=selected_window_id,
            unknown_reason=unknown_reason,
            chi_routing_candidates=copy.deepcopy(candidates),
            routing_projection="chi_index",
            decision_authority=False,
            max_results_ignored=request.max_results,
            top_result_affect_strength=round(
                result.top_affect_strength(), 4),
            query_tick=int(self._get_tick()),
            wall_clock=time.time(),
            duration_ms=round(duration_ms, 3),
        )
        return result
