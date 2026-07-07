"""Binding window: the unit of cross-modal experience.

Per GL-SPEC-SUBSTRATE-FOUNDATION-EVE-20260706-v1 §2 and
GL-DES-BINDING-WINDOWS-EVE-20260706-v1. A binding window is one atomic
experience: senses + words recorded as "these were together" -- every
entry inside a window can retrieve every other entry in the same window,
recorded when the window forms, not inferred from timestamps later.

Scope of this build (GL-CMD-BINDING-WINDOWS-BUILD-EVE-20260706-v1):
real windows, real lifecycle, real events -- wired additively. The
design doc's "atlas holds windows as first-class objects, chi lookup
returns windows" is the eventual shape; this build gets there without a
destructive rewrite of the atlas's existing per-chi entry storage (which
dozens of existing methods -- match_score, recall_scene, decay, prune,
total_strength, and more -- depend on today, unchanged, correctness-
critical, live). Instead: WindowManager.add_entry() calls the EXISTING
atlas-write function with EXACTLY the arguments it already receives
(same call, same side effects, same timing -- transduction and write
behavior do not change), then ALSO tags the resulting atlas entry with
window_id/entry_index (additive fields every existing reader already
ignores unknown keys on, same as presence/location/sky_state/bundle_id
today) and records the entry into the currently-open window's own list.
No recall/consumption of window_id is built here -- that's explicitly
out of scope (a later dispatch); this build's job is real windows with
real linkage data, ready for that later mechanism to read.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class WindowEntry:
    """One sensory/word binding recorded inside a window."""

    modality: str            # sight | sound | word | touch | smell | taste
    section: str              # atlas section actually written (e.g. "sight", "audio_low", "listen")
    motif_id: int
    chi: int
    tick: int
    source_tag: str = ""
    provenance: dict = field(default_factory=dict)


@dataclass
class BindingWindow:
    """One atomic experience. See module docstring."""

    window_id: str
    opened_tick: int
    opened_wall_clock: float
    trigger_reason: str
    presence_state: dict = field(default_factory=dict)
    affect_snapshot: dict = field(default_factory=dict)
    entries: list = field(default_factory=list)   # list[WindowEntry]
    closed_tick: Optional[int] = None
    closed_wall_clock: Optional[float] = None
    close_reason: Optional[str] = None

    def add_entry(self, entry: WindowEntry) -> int:
        self.entries.append(entry)
        return len(self.entries) - 1


class WindowManager:
    """Owns the currently-open binding window. One window open at a time
    per GL-DES-BINDING-WINDOWS-EVE-20260706-v1's explicit v1 ruling (whole-
    window discipline preserves cross-modal linkage; splitting into per-
    modality windows loses it on the spot).

    Opens on the first entry after a quiet period, or via explicit open()
    (give_experience's own flow). Closes on explicit close() (sentence end,
    activity change -- callers name the reason), or lazily on quiet timeout
    (checked at the start of the next open()/add_entry() call -- see
    _maybe_close_for_quiet_timeout's docstring for why this is a lazy
    check, not a background timer).
    """

    QUIET_TIMEOUT_SEC_DEFAULT = 0.5

    def __init__(
        self,
        atlas_record_fn: Callable[..., Any],
        log_event_fn: Callable[..., Any],
        get_tick_fn: Callable[[], int],
        get_presence_fn: Optional[Callable[[], dict]] = None,
        get_affect_fn: Optional[Callable[[], dict]] = None,
        quiet_timeout_sec: Optional[float] = None,
        atlas_windows: Optional[dict] = None,
    ):
        """
        atlas_record_fn: the EXISTING record path (Guala._atlas_record, or
            self.atlas.record directly for Section.receive's call site).
            Called with EXACTLY the arguments the caller already passes --
            WindowManager adds bookkeeping on top, it does not change what
            gets written to the atlas or when.
        log_event_fn: Guala._log_substrate_event.
        get_tick_fn: callable() -> int, current engine tick.
        get_presence_fn / get_affect_fn: optional callables for the
            window's provenance snapshot; default to {} if not supplied
            (some callers, e.g. Section.receive, have no direct engine
            reference -- honest empty, not a placeholder).
        atlas_windows: the real atlas's own `windows` dict (passed by
            reference -- writes here are writes there), so closed windows
            land where a future recall mechanism and existing persistence
            sweep will actually find them. Defaults to a private dict when
            not supplied (standalone/test use).
        """
        self._atlas_record = atlas_record_fn
        self._log_event = log_event_fn
        self._get_tick = get_tick_fn
        self._get_presence = get_presence_fn or (lambda: {})
        self._get_affect = get_affect_fn or (lambda: {})
        self.quiet_timeout_sec = (
            quiet_timeout_sec if quiet_timeout_sec is not None
            else self.QUIET_TIMEOUT_SEC_DEFAULT
        )

        self.current: Optional[BindingWindow] = None
        self._last_entry_wall_time: Optional[float] = None
        # closed windows land here as plain dicts (JSON-friendly), keyed by
        # window_id -- this dict IS atlas.windows when wired to the real
        # engine (same object, not a copy), or a private dict in isolation.
        self.windows: dict = atlas_windows if atlas_windows is not None else {}

    def _maybe_close_for_quiet_timeout(self) -> None:
        """Lazy quiet-timeout check: evaluated at the start of the next
        open()/add_entry() call, not by a background timer. A window that
        opens and is never touched again stays open until an explicit
        close() -- sentence-end and activity-change triggers cover the
        common case in real operation; this is a backstop for the
        abnormal one, and its imprecision (not exactly quiet_timeout_sec,
        possibly much longer if nothing else ever happens) is an accepted
        tradeoff against adding a background timer thread to a substrate
        that already has real GIL-contention history tonight."""
        if (self.current is not None and self._last_entry_wall_time is not None
                and time.time() - self._last_entry_wall_time > self.quiet_timeout_sec):
            self.close(reason="quiet_timeout")

    def open(self, trigger_reason: str) -> str:
        """Open a new window. If one is already open, returns its ID
        unchanged (one window open at a time -- do not silently orphan
        an existing window's entries by opening a second one)."""
        self._maybe_close_for_quiet_timeout()
        if self.current is not None:
            return self.current.window_id

        window_id = f"win_{uuid.uuid4().hex[:12]}"
        tick = self._get_tick()
        window = BindingWindow(
            window_id=window_id,
            opened_tick=tick,
            opened_wall_clock=time.time(),
            trigger_reason=trigger_reason,
            presence_state=dict(self._get_presence()),
            affect_snapshot=dict(self._get_affect()),
        )
        self.current = window
        # NOTE: not added to self.windows here -- self.windows (== atlas.
        # windows when wired to the real engine) only receives the plain-
        # dict snapshot at close() time. A still-open window lives only in
        # self.current until it closes; recall/persistence never see a
        # half-formed window.
        self._last_entry_wall_time = time.time()
        self._log_event(
            "window_opened",
            window_id=window_id, tick=tick,
            wall_clock=window.opened_wall_clock,
            trigger_reason=trigger_reason,
            presence_state=window.presence_state,
        )
        return window_id

    def add_entry(
        self,
        modality: str,
        section: str,
        motif_id: int,
        chi: int,
        tick: Optional[int] = None,
        source_tag: str = "",
        provenance: Optional[dict] = None,
        trigger_reason: str = "input",
        **atlas_kwargs: Any,
    ) -> int:
        """Record one binding: writes the atlas via the EXACT same call
        the caller already made (same args, same side effects, same
        timing as before this dispatch), then records the entry into the
        currently-open window (opening one first if none is open), tags
        the atlas entry with window_id/entry_index, and emits
        window_entry_added. Returns the entry's index within the window.
        """
        self._maybe_close_for_quiet_timeout()
        if self.current is None:
            self.open(trigger_reason=trigger_reason)

        window = self.current
        entry_index = len(window.entries)
        atlas_kwargs = dict(atlas_kwargs)
        atlas_kwargs["window_id"] = window.window_id
        atlas_kwargs["window_entry_index"] = entry_index

        actual_tick = tick if tick is not None else self._get_tick()
        self._atlas_record(section, motif_id, chi, actual_tick, **atlas_kwargs)

        entry = WindowEntry(
            modality=modality, section=section, motif_id=motif_id, chi=chi,
            tick=actual_tick, source_tag=source_tag, provenance=provenance or {},
        )
        idx = window.add_entry(entry)
        self._last_entry_wall_time = time.time()
        self._log_event(
            "window_entry_added",
            window_id=window.window_id, modality=modality, chi=chi,
            entry_index=idx,
        )
        return idx

    def close(self, reason: str) -> Optional[str]:
        """Close the currently-open window, if any. No-op if none is
        open (callers name a reason unconditionally -- e.g. sentence-end
        firing with no window open is normal, not an error)."""
        if self.current is None:
            return None
        window = self.current
        window.closed_tick = self._get_tick()
        window.closed_wall_clock = time.time()
        window.close_reason = reason
        window_id = window.window_id

        self.windows[window_id] = {
            "window_id": window_id,
            "opened_tick": window.opened_tick,
            "opened_wall_clock": window.opened_wall_clock,
            "closed_tick": window.closed_tick,
            "closed_wall_clock": window.closed_wall_clock,
            "trigger_reason": window.trigger_reason,
            "close_reason": window.close_reason,
            "presence_state": window.presence_state,
            "affect_snapshot": window.affect_snapshot,
            "entries": [
                {
                    "modality": e.modality, "section": e.section,
                    "motif_id": e.motif_id, "chi": e.chi, "tick": e.tick,
                    "source_tag": e.source_tag, "provenance": e.provenance,
                }
                for e in window.entries
            ],
        }

        self._log_event(
            "window_closed",
            window_id=window_id, close_reason=reason,
            entry_count=len(window.entries),
            tick_span=window.closed_tick - window.opened_tick,
            affect_snapshot=window.affect_snapshot,
        )
        self.current = None
        self._last_entry_wall_time = None
        return window_id
