"""Canonical binding-window memory.

A binding window is one caller-delimited experience.  The manager owns the
durable window records and the chi index used by recall.  LivingAtlas may hold
a compatibility copy, but it is not the authority for either storage or
lookup.

Legacy ``open``/``add_entry``/``close`` callers remain supported.  New callers
should use ``begin_context``/``end_context`` (or ``binding_context``) with a
stable caller context id.  Contexts are independent: ending one can never
close another, including when different threads are active concurrently.
"""
from __future__ import annotations

import base64
import contextvars
import copy
import hashlib
import json
import math
import os
import threading
import time
import weakref
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Mapping, Optional


SCHEMA_NAME = "dsf.binding_windows"
SCHEMA_VERSION = 2


class WindowIntegrityError(ValueError):
    """Raised when a window snapshot or internal index is inconsistent."""


def _json_safe(value: Any, path: str = "value") -> Any:
    """Return a deterministic JSON-safe copy without hiding unsupported data."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, complex):
        return {"real": _json_safe(value.real, f"{path}.real"),
                "imag": _json_safe(value.imag, f"{path}.imag")}
    if isinstance(value, bytes):
        return {"encoding": "base64",
                "data": base64.b64encode(value).decode("ascii")}
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if is_dataclass(value):
        return _json_safe(asdict(value), path)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            safe_key = key if isinstance(key, str) else str(key)
            if safe_key in result:
                raise ValueError(f"{path} has colliding JSON object key {safe_key!r}")
            result[safe_key] = _json_safe(item, f"{path}.{safe_key}")
        return result
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, f"{path}[{index}]")
                for index, item in enumerate(value)]
    if isinstance(value, (set, frozenset)):
        converted = [_json_safe(item, f"{path}[]") for item in value]
        return sorted(converted, key=lambda item: json.dumps(
            item, sort_keys=True, separators=(",", ":")))

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            item = item_method()
        except (TypeError, ValueError):
            item = value
        if item is not value:
            return _json_safe(item, path)

    list_method = getattr(value, "tolist", None)
    if callable(list_method):
        return _json_safe(list_method(), path)

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return _json_safe(isoformat(), path)

    raise TypeError(f"{path} contains unsupported non-JSON value "
                    f"{type(value).__name__}")


def _tuple_refs(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return _json_safe(value, "provenance reference list")
    return [_json_safe(value, "provenance reference")]


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


@dataclass
class WindowEntry:
    """One complete, JSON-safe fact of an experience window."""

    modality: str
    section: str
    motif_id: int
    chi: int
    tick: int
    source_tag: str = ""
    provenance: dict = field(default_factory=dict)
    language_position: Optional[int] = None

    def to_record(self, entry_index: int) -> dict:
        return {
            "entry_index": entry_index,
            "modality": self.modality,
            "section": self.section,
            "motif_id": self.motif_id,
            "chi": self.chi,
            "tick": self.tick,
            "source_tag": self.source_tag,
            "language_position": self.language_position,
            "provenance": _json_safe(self.provenance, "entry.provenance"),
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "WindowEntry":
        return cls(
            modality=str(record["modality"]),
            section=str(record["section"]),
            motif_id=int(record["motif_id"]),
            chi=int(record["chi"]),
            tick=int(record["tick"]),
            source_tag=str(record.get("source_tag") or ""),
            provenance=_json_safe(record.get("provenance") or {},
                                  "entry.provenance"),
            language_position=(
                None if record.get("language_position") is None
                else int(record["language_position"])),
        )


@dataclass
class BindingWindow:
    """One atomic caller context and every entry experienced inside it."""

    window_id: str
    context_id: str
    context_origin: str
    opened_tick: int
    opened_wall_clock: float
    trigger_reason: str
    presence_state: dict = field(default_factory=dict)
    affect_snapshot: dict = field(default_factory=dict)
    needs_snapshot: dict = field(default_factory=dict)
    context_detail: dict = field(default_factory=dict)
    entries: list[WindowEntry] = field(default_factory=list)
    closed_tick: Optional[int] = None
    closed_wall_clock: Optional[float] = None
    close_reason: Optional[str] = None
    _language_positions: dict = field(default_factory=dict, repr=False)
    _next_language_position: int = field(default=0, repr=False)

    def language_position_for(self, tick: int, source_tag: str,
                              explicit: Optional[int]) -> Optional[int]:
        if explicit is not None:
            if explicit < 0:
                raise ValueError("language_position must be non-negative")
            self._next_language_position = max(
                self._next_language_position, explicit + 1)
            return explicit
        identity = (int(tick), str(source_tag))
        position = self._language_positions.get(identity)
        if position is None:
            position = self._next_language_position
            self._language_positions[identity] = position
            self._next_language_position += 1
        return position

    def add_entry(self, entry: WindowEntry) -> int:
        self.entries.append(entry)
        return len(self.entries) - 1

    def to_record(self) -> dict:
        return {
            "window_id": self.window_id,
            "context_id": self.context_id,
            "context_origin": self.context_origin,
            "opened_tick": self.opened_tick,
            "opened_wall_clock": self.opened_wall_clock,
            "closed_tick": self.closed_tick,
            "closed_wall_clock": self.closed_wall_clock,
            "trigger_reason": self.trigger_reason,
            "close_reason": self.close_reason,
            "presence_state": _json_safe(self.presence_state,
                                         "window.presence_state"),
            "affect_snapshot": _json_safe(self.affect_snapshot,
                                          "window.affect_snapshot"),
            "needs_snapshot": _json_safe(self.needs_snapshot,
                                         "window.needs_snapshot"),
            "context_detail": _json_safe(self.context_detail,
                                         "window.context_detail"),
            "entries": [entry.to_record(index)
                        for index, entry in enumerate(self.entries)],
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "BindingWindow":
        window = cls(
            window_id=str(record["window_id"]),
            context_id=str(record["context_id"]),
            context_origin=str(record.get("context_origin") or "restored"),
            opened_tick=int(record["opened_tick"]),
            opened_wall_clock=float(record["opened_wall_clock"]),
            trigger_reason=str(record.get("trigger_reason") or "restored"),
            presence_state=_json_safe(record.get("presence_state") or {},
                                      "window.presence_state"),
            affect_snapshot=_json_safe(record.get("affect_snapshot") or {},
                                       "window.affect_snapshot"),
            needs_snapshot=_json_safe(record.get("needs_snapshot") or {},
                                      "window.needs_snapshot"),
            context_detail=_json_safe(record.get("context_detail") or {},
                                      "window.context_detail"),
            entries=[WindowEntry.from_record(item)
                     for item in record.get("entries") or []],
            closed_tick=(None if record.get("closed_tick") is None
                         else int(record["closed_tick"])),
            closed_wall_clock=(
                None if record.get("closed_wall_clock") is None
                else float(record["closed_wall_clock"])),
            close_reason=record.get("close_reason"),
        )
        for entry in window.entries:
            if entry.modality == "word" and entry.language_position is not None:
                window._language_positions[(entry.tick, entry.source_tag)] = (
                    entry.language_position)
                window._next_language_position = max(
                    window._next_language_position,
                    entry.language_position + 1)
        return window


# A legacy engine supplies only ``lambda: atlas.windows`` to RecallEngine.
# Resolve that compatibility object back to its authoritative manager without
# making the Atlas copy the recall authority.  Weak references prevent manager
# lifetimes from being extended by the registry.
_MIRROR_REGISTRY_LOCK = threading.Lock()
_MIRROR_REGISTRY: dict[int, weakref.ReferenceType] = {}


def manager_for_compatibility_mirror(mirror: dict) -> Optional["WindowManager"]:
    with _MIRROR_REGISTRY_LOCK:
        registered = _MIRROR_REGISTRY.get(id(mirror))
        if registered is None:
            return None
        manager = registered()
        if manager is None or manager._compatibility_windows is not mirror:
            _MIRROR_REGISTRY.pop(id(mirror), None)
            return None
        return manager


class WindowManager:
    """Thread-safe owner of binding contexts, windows, and the chi index."""

    def __init__(
        self,
        atlas_record_fn: Callable[..., Any],
        log_event_fn: Callable[..., Any],
        get_tick_fn: Callable[[], int],
        get_presence_fn: Optional[Callable[[], dict]] = None,
        get_affect_fn: Optional[Callable[[], dict]] = None,
        quiet_timeout_sec: Optional[float] = None,
        atlas_windows: Optional[dict] = None,
        get_needs_fn: Optional[Callable[[], dict]] = None,
    ):
        # ``quiet_timeout_sec`` is accepted for constructor compatibility only.
        # It has no authority over an experience boundary.
        self.quiet_timeout_sec = quiet_timeout_sec
        self._atlas_record = atlas_record_fn
        self._log_event = log_event_fn
        self._get_tick = get_tick_fn
        self._get_presence = get_presence_fn or (lambda: {})
        self._get_affect = get_affect_fn or (lambda: {})
        self._get_needs = get_needs_fn or (lambda: {})
        self._lock = threading.RLock()
        self._bound_context = contextvars.ContextVar(
            f"binding_window_context_{id(self)}", default=None)
        self._contexts: dict[str, BindingWindow] = {}
        self._windows: dict[str, dict] = {}
        self.windows = self._windows  # legacy direct-read surface
        self._chi_index: dict[int, list[dict]] = {}
        self._window_sequence = 0
        self._context_sequence = 0
        self._compatibility_windows = (
            atlas_windows if atlas_windows is not None else {})

        # Existing mirror content is a one-time migration input.  Runtime recall
        # never reads it again.
        if self._compatibility_windows:
            migrated = self._snapshot_from_legacy_windows(
                self._compatibility_windows)
            self.restore(migrated)

        with _MIRROR_REGISTRY_LOCK:
            _MIRROR_REGISTRY[id(self._compatibility_windows)] = weakref.ref(self)

    @property
    def current(self) -> Optional[BindingWindow]:
        context_id = self._bound_context.get()
        with self._lock:
            if context_id is not None:
                return self._contexts.get(context_id)
            # Compatibility for inspection-only callers when exactly one
            # context exists.  Never choose arbitrarily among concurrent ones.
            if len(self._contexts) == 1:
                return next(iter(self._contexts.values()))
            return None

    @property
    def active_context_id(self) -> Optional[str]:
        """Return only this caller's bound context, never another caller's."""
        context_id = self._bound_context.get()
        with self._lock:
            return context_id if context_id in self._contexts else None

    @property
    def chi_index(self) -> dict:
        with self._lock:
            return {chi: copy.deepcopy(locations)
                    for chi, locations in self._chi_index.items()}

    def _new_window(self, context_id: str, trigger_reason: str,
                    context_origin: str, context_detail: Optional[Mapping]) -> BindingWindow:
        tick = int(self._get_tick())
        sequence = self._window_sequence
        self._window_sequence += 1
        identity = hashlib.sha256(
            f"{sequence}|{context_id}|{tick}|{trigger_reason}".encode("utf-8")
        ).hexdigest()[:16]
        return BindingWindow(
            window_id=f"win_{sequence:016x}_{identity}",
            context_id=context_id,
            context_origin=context_origin,
            opened_tick=tick,
            opened_wall_clock=time.time(),
            trigger_reason=str(trigger_reason),
            presence_state=_json_safe(self._get_presence() or {},
                                      "window.presence_state"),
            affect_snapshot=_json_safe(self._get_affect() or {},
                                       "window.affect_snapshot"),
            needs_snapshot=_json_safe(self._get_needs() or {},
                                      "window.needs_snapshot"),
            context_detail=_json_safe(context_detail or {},
                                      "window.context_detail"),
        )

    def _next_context_id(self, prefix: str) -> str:
        with self._lock:
            sequence = self._context_sequence
            self._context_sequence += 1
        return f"{prefix}:{sequence:016x}"

    def begin_context(self, context_id: str, trigger_reason: str = "input",
                      *, context_detail: Optional[Mapping] = None,
                      _origin: str = "explicit") -> str:
        """Begin or reactivate exactly one caller-owned experience context."""
        if not isinstance(context_id, str) or not context_id.strip():
            raise ValueError("context_id must be a non-empty string")
        context_id = context_id.strip()
        opened = False
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                window = self._new_window(
                    context_id, trigger_reason, _origin, context_detail)
                self._contexts[context_id] = window
                opened = True
            self._bound_context.set(context_id)
            window_id = window.window_id
            event = {
                "window_id": window_id,
                "context_id": context_id,
                "tick": window.opened_tick,
                "wall_clock": window.opened_wall_clock,
                "trigger_reason": window.trigger_reason,
                "presence_state": copy.deepcopy(window.presence_state),
            }
        if opened:
            self._log_event("window_opened", **event)
        return window_id

    def activate_context(self, context_id: str) -> str:
        """Bind an already-open restored/cross-thread context to this caller."""
        with self._lock:
            if context_id not in self._contexts:
                raise KeyError(f"unknown open binding context {context_id!r}")
            self._bound_context.set(context_id)
            return self._contexts[context_id].window_id

    @contextmanager
    def binding_context(self, context_id: str, trigger_reason: str = "input",
                        *, close_reason: str = "context_complete",
                        failure_reason: str = "context_failed",
                        context_detail: Optional[Mapping] = None):
        token = self._bound_context.set(context_id)
        completed = False
        try:
            window_id = self.begin_context(
                context_id, trigger_reason,
                context_detail=context_detail)
            yield window_id
            completed = True
        finally:
            self.end_context(
                context_id, close_reason if completed else failure_reason)
            self._bound_context.reset(token)

    def open(self, trigger_reason: str, context_id: Optional[str] = None,
             **context_detail: Any) -> str:
        """Backward-compatible open; existing bound context remains open."""
        bound = self._bound_context.get()
        with self._lock:
            if context_id is None and bound in self._contexts:
                return self._contexts[bound].window_id
        context_id = context_id or self._next_context_id("legacy")
        return self.begin_context(
            context_id, trigger_reason,
            context_detail=context_detail, _origin="legacy")

    @staticmethod
    def _inferred_context_id(atlas_kwargs: Mapping[str, Any]) -> Optional[str]:
        episode = _first_present(
            atlas_kwargs.get("episode_ref"),
            (atlas_kwargs.get("episode_refs") or [None])[0]
            if isinstance(atlas_kwargs.get("episode_refs"), (list, tuple))
            else None)
        if episode not in (None, ""):
            return f"episode:{episode}"
        bundle = _first_present(
            atlas_kwargs.get("bundle_id"),
            (atlas_kwargs.get("bundle_ids") or [None])[0]
            if isinstance(atlas_kwargs.get("bundle_ids"), (list, tuple))
            else None)
        if bundle not in (None, ""):
            return f"bundle:{bundle}"
        return None

    def _context_for_entry(self, explicit_context_id: Optional[str],
                           trigger_reason: str,
        atlas_kwargs: Mapping[str, Any]) -> BindingWindow:
        if explicit_context_id is not None:
            self.begin_context(explicit_context_id, trigger_reason)
            explicit_context_id = explicit_context_id.strip()
            return self._contexts[explicit_context_id]

        inferred = self._inferred_context_id(atlas_kwargs)
        bound = self._bound_context.get()
        with self._lock:
            current = self._contexts.get(bound) if bound is not None else None

        if (current is not None and current.context_origin == "inferred"
                and inferred is not None and inferred != current.context_id):
            # The caller supplied a new structural episode/bundle boundary.
            # Close only this caller's previously-bound inferred context.
            self.end_context(current.context_id, "context_boundary")
            current = None

        if current is not None:
            return current
        if inferred is not None:
            self.begin_context(
                inferred, trigger_reason, _origin="inferred")
            return self._contexts[inferred]

        legacy_id = self._next_context_id("implicit")
        self.begin_context(legacy_id, trigger_reason, _origin="legacy")
        return self._contexts[legacy_id]

    def _entry_provenance(
        self,
        *,
        source_tag: str,
        provenance: Optional[Mapping[str, Any]],
        atlas_kwargs: Mapping[str, Any],
        salience: Optional[float],
        dwell_ticks: Optional[float],
        detail: Optional[Mapping[str, Any]],
        structural_fact: Optional[Mapping[str, Any]],
        needs_snapshot: Optional[Mapping[str, Any]],
    ) -> dict:
        base = _json_safe(provenance or {}, "entry.provenance")
        if not isinstance(base, dict):
            raise TypeError("provenance must be a mapping")

        source = _first_present(
            atlas_kwargs.get("source"), base.get("source"), source_tag or None)
        episode_ref = _first_present(
            atlas_kwargs.get("episode_ref"), base.get("episode_ref"))
        episode_refs = _tuple_refs(
            atlas_kwargs.get("episode_refs")
            or base.get("episode_refs")
            or episode_ref)
        bundle_id = _first_present(
            atlas_kwargs.get("bundle_id"), base.get("bundle_id"))
        bundle_ids = _tuple_refs(
            atlas_kwargs.get("bundle_ids")
            or base.get("bundle_ids")
            or bundle_id)
        sensory_refs = _tuple_refs(
            atlas_kwargs.get("sensory_refs") or base.get("sensory_refs"))

        scene_keys = ("presence", "location", "sky_state", "place", "ambient")
        scene = dict(base.get("scene") or {})
        for key in scene_keys:
            if key in atlas_kwargs:
                scene[key] = atlas_kwargs[key]

        affect_keys = ("arousal", "valence", "surprise", "polarity",
                       "need_pressure")
        affect = _json_safe(self._get_affect() or {}, "entry.affect")
        affect.update(base.get("affect") or {})
        for key in affect_keys:
            if key in atlas_kwargs:
                affect[key] = atlas_kwargs[key]

        needs = _json_safe(self._get_needs() or {}, "entry.needs")
        needs.update(base.get("needs") or {})
        if needs_snapshot is not None:
            needs.update(_json_safe(needs_snapshot, "entry.needs"))

        fact = _first_present(
            structural_fact, atlas_kwargs.get("structural_fact"),
            base.get("structural_fact"))
        if fact is not None and not isinstance(fact, Mapping):
            raise TypeError("structural_fact must be a mapping when supplied")

        reserved = {
            "source", "episode_ref", "episode_refs", "bundle_id", "bundle_ids",
            "sensory_refs", "presence", "location", "sky_state", "place",
            "ambient", *affect_keys, "structural_fact", "window_id",
            "window_entry_index", "salience", "dwell_ticks",
        }
        complete_detail = dict(base.get("detail") or {})
        if detail is not None:
            complete_detail.update(_json_safe(detail, "entry.detail"))
        for key, value in atlas_kwargs.items():
            if key not in reserved:
                complete_detail[key] = value

        base.update({
            "source": _json_safe(source, "entry.source"),
            "source_tag": _json_safe(source_tag, "entry.source_tag"),
            "episode_ref": _json_safe(episode_ref, "entry.episode_ref"),
            "episode_refs": _json_safe(episode_refs, "entry.episode_refs"),
            "bundle_id": _json_safe(bundle_id, "entry.bundle_id"),
            "bundle_ids": _json_safe(bundle_ids, "entry.bundle_ids"),
            "sensory_refs": _json_safe(sensory_refs, "entry.sensory_refs"),
            "scene": _json_safe(scene, "entry.scene"),
            "affect": _json_safe(affect, "entry.affect"),
            "needs": _json_safe(needs, "entry.needs"),
            "salience": _json_safe(salience, "entry.salience"),
            "dwell_ticks": _json_safe(dwell_ticks, "entry.dwell_ticks"),
            "detail": _json_safe(complete_detail, "entry.detail"),
            "structural_fact": (
                None if fact is None
                else _json_safe(fact, "entry.structural_fact")),
        })
        return base

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
        context_id: Optional[str] = None,
        language_position: Optional[int] = None,
        structural_fact: Optional[Mapping[str, Any]] = None,
        needs_snapshot: Optional[Mapping[str, Any]] = None,
        detail: Optional[Mapping[str, Any]] = None,
        salience: Optional[float] = None,
        dwell_ticks: Optional[float] = None,
        mirror_atlas: bool = True,
        **atlas_kwargs: Any,
    ) -> int:
        """Append one complete window fact and optionally mirror legacy Atlas.

        ``mirror_atlas=False`` is the canonical-memory path.  It prevents a
        first-class BindingWindow fact from being flattened into a legacy
        section/motif Atlas record merely for compatibility.  The window and
        its Chi index remain complete and authoritative either way.
        """
        actual_tick = int(tick if tick is not None else self._get_tick())
        motif_id = int(motif_id)
        chi = int(chi)
        source_tag = str(source_tag or "")
        if salience is None and "salience" in atlas_kwargs:
            salience = atlas_kwargs["salience"]
        if dwell_ticks is None and "dwell_ticks" in atlas_kwargs:
            dwell_ticks = atlas_kwargs["dwell_ticks"]

        with self._lock:
            window = self._context_for_entry(
                context_id, trigger_reason, atlas_kwargs)
            entry_index = len(window.entries)
            position = None
            if modality == "word":
                position = window.language_position_for(
                    actual_tick, source_tag, language_position)
            full_provenance = self._entry_provenance(
                source_tag=source_tag,
                provenance=provenance,
                atlas_kwargs=atlas_kwargs,
                salience=salience,
                dwell_ticks=dwell_ticks,
                detail=detail,
                structural_fact=structural_fact,
                needs_snapshot=needs_snapshot,
            )
            entry = WindowEntry(
                modality=str(modality), section=str(section),
                motif_id=motif_id, chi=chi, tick=actual_tick,
                source_tag=source_tag, provenance=full_provenance,
                language_position=position)
            # Build/validate the record before the compatibility write so a
            # non-JSON fact cannot leave a mirrored binding without memory.
            entry.to_record(entry_index)

            mirror_kwargs = dict(atlas_kwargs)
            if salience is not None:
                mirror_kwargs["salience"] = salience
            if dwell_ticks is not None:
                mirror_kwargs["dwell_ticks"] = dwell_ticks
            if structural_fact is not None:
                mirror_kwargs["structural_fact"] = structural_fact
            mirror_kwargs["window_id"] = window.window_id
            mirror_kwargs["window_entry_index"] = entry_index
            if mirror_atlas:
                self._atlas_record(
                    str(section), motif_id, chi, actual_tick, **mirror_kwargs)
            index = window.add_entry(entry)
            event = {
                "window_id": window.window_id,
                "context_id": window.context_id,
                "modality": str(modality),
                "chi": chi,
                "entry_index": index,
                "language_position": position,
            }
        self._log_event("window_entry_added", **event)
        return index

    def _index_closed_window(self, record: Mapping[str, Any]) -> None:
        window_id = record["window_id"]
        for entry in record.get("entries") or []:
            chi = int(entry["chi"])
            location = {
                "window_id": window_id,
                "entry_index": int(entry["entry_index"]),
            }
            bucket = self._chi_index.setdefault(chi, [])
            if location not in bucket:
                bucket.append(location)

    def end_context(self, context_id: str,
                    reason: str = "context_complete") -> Optional[str]:
        """Close exactly ``context_id``; all other contexts remain untouched."""
        with self._lock:
            window = self._contexts.pop(context_id, None)
            if window is None:
                return None
            window.closed_tick = int(self._get_tick())
            window.closed_wall_clock = time.time()
            window.close_reason = str(reason)
            record = window.to_record()
            self._validate_window_record(record, closed=True)
            self._windows[window.window_id] = record
            self._index_closed_window(record)
            # Atlas receives a detached compatibility copy.  Recall never reads it.
            self._compatibility_windows[window.window_id] = copy.deepcopy(record)
            if self._bound_context.get() == context_id:
                self._bound_context.set(None)
            event = {
                "window_id": window.window_id,
                "context_id": context_id,
                "close_reason": str(reason),
                "entry_count": len(window.entries),
                "tick_span": window.closed_tick - window.opened_tick,
                "affect_snapshot": copy.deepcopy(window.affect_snapshot),
            }
            window_id = window.window_id
        self._log_event("window_closed", **event)
        return window_id

    def close(self, reason: str, context_id: Optional[str] = None) -> Optional[str]:
        """Backward-compatible close of only the caller's bound context."""
        context_id = context_id or self._bound_context.get()
        if context_id is None:
            return None
        return self.end_context(context_id, reason)

    def lookup_chi(self, chi: int) -> tuple[dict, ...]:
        """Return full closed windows referenced by one canonical chi bucket."""
        with self._lock:
            locations = self._chi_index.get(int(chi), ())
            seen = set()
            windows = []
            for location in locations:
                window_id = location["window_id"]
                if window_id in seen:
                    continue
                seen.add(window_id)
                windows.append(copy.deepcopy(self._windows[window_id]))
            return tuple(windows)

    def recall_snapshot(self, chis: list[int]) -> tuple[dict, ...]:
        """Return every full closed window matching any chi, once, atomically."""
        ordered_chis = list(dict.fromkeys(int(chi) for chi in chis))
        with self._lock:
            window_ids = []
            seen = set()
            for chi in ordered_chis:
                for location in self._chi_index.get(chi, ()):
                    window_id = location["window_id"]
                    if window_id not in seen:
                        seen.add(window_id)
                        window_ids.append(window_id)
            return tuple(copy.deepcopy(self._windows[window_id])
                         for window_id in window_ids)

    def closed_window(self, window_id: str) -> Optional[dict]:
        """Return one detached closed window by its exact durable identity."""
        with self._lock:
            record = self._windows.get(str(window_id))
            return None if record is None else copy.deepcopy(record)

    def snapshot(self) -> dict:
        """Return the complete closed/open memory and its independently checked index."""
        with self._lock:
            snapshot = {
                "schema": SCHEMA_NAME,
                "version": SCHEMA_VERSION,
                "windows": copy.deepcopy(self._windows),
                "open_contexts": {
                    context_id: window.to_record()
                    for context_id, window in self._contexts.items()
                },
                "chi_index": {
                    str(chi): copy.deepcopy(locations)
                    for chi, locations in self._chi_index.items()
                },
                "next_window_sequence": self._window_sequence,
                "next_context_sequence": self._context_sequence,
            }
            self._validate_snapshot(snapshot)
            # Strict JSON encoding is the final guarantee, including NaN rejection.
            json.dumps(snapshot, allow_nan=False, sort_keys=True)
            return snapshot

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        """Validate completely, then atomically replace canonical memory."""
        safe_snapshot = _json_safe(snapshot, "snapshot")
        self._validate_snapshot(safe_snapshot)
        closed = copy.deepcopy(safe_snapshot["windows"])
        contexts = {
            context_id: BindingWindow.from_record(record)
            for context_id, record in safe_snapshot["open_contexts"].items()
        }
        chi_index = {
            int(chi): copy.deepcopy(locations)
            for chi, locations in safe_snapshot["chi_index"].items()
        }
        next_window_sequence = int(safe_snapshot["next_window_sequence"])
        next_context_sequence = int(safe_snapshot["next_context_sequence"])
        with self._lock:
            self._windows.clear()
            self._windows.update(closed)
            self._contexts = contexts
            self._chi_index = chi_index
            self._window_sequence = next_window_sequence
            self._context_sequence = next_context_sequence
            self._compatibility_windows.clear()
            self._compatibility_windows.update(copy.deepcopy(closed))
            self._bound_context.set(None)
        self._log_event(
            "window_state_restored",
            windows=len(closed), open_contexts=len(contexts),
            chi_buckets=len(chi_index))

    def validate_integrity(self) -> tuple[str, ...]:
        """Return all integrity errors without modifying state."""
        try:
            self.snapshot()
        except (WindowIntegrityError, TypeError, ValueError) as error:
            return (str(error),)
        return ()

    @staticmethod
    def _validate_window_record(record: Mapping[str, Any], *, closed: bool) -> None:
        required = ("window_id", "context_id", "opened_tick",
                    "opened_wall_clock", "entries")
        missing = [key for key in required if key not in record]
        if missing:
            raise WindowIntegrityError(f"window missing fields {missing}")
        if not record["window_id"] or not record["context_id"]:
            raise WindowIntegrityError("window and context ids must be non-empty")
        if closed:
            if record.get("closed_tick") is None or record.get("closed_wall_clock") is None:
                raise WindowIntegrityError(
                    f"closed window {record['window_id']} lacks close coordinates")
        elif record.get("closed_tick") is not None:
            raise WindowIntegrityError(
                f"open context {record['context_id']} is already closed")

        previous_language_position = -1
        for expected_index, entry in enumerate(record.get("entries") or []):
            if int(entry.get("entry_index", -1)) != expected_index:
                raise WindowIntegrityError(
                    f"window {record['window_id']} entry index discontinuity")
            for key in ("modality", "section", "motif_id", "chi", "tick",
                        "provenance"):
                if key not in entry:
                    raise WindowIntegrityError(
                        f"window {record['window_id']} entry {expected_index} "
                        f"missing {key}")
            if not isinstance(entry["chi"], int):
                raise WindowIntegrityError(
                    f"window {record['window_id']} entry {expected_index} chi is not int")
            if not isinstance(entry.get("provenance"), dict):
                raise WindowIntegrityError(
                    f"window {record['window_id']} entry {expected_index} provenance is not object")
            if entry.get("modality") == "word":
                position = entry.get("language_position")
                if position is None or not isinstance(position, int) or position < 0:
                    raise WindowIntegrityError(
                        f"window {record['window_id']} word entry lacks ordered position")
                if position < previous_language_position:
                    raise WindowIntegrityError(
                        f"window {record['window_id']} word positions are not ordered")
                previous_language_position = position
            fact = entry["provenance"].get("structural_fact")
            if fact is not None and not isinstance(fact, dict):
                raise WindowIntegrityError(
                    f"window {record['window_id']} structural fact is not object")

    @classmethod
    def _validate_snapshot(cls, snapshot: Mapping[str, Any]) -> None:
        if snapshot.get("schema") != SCHEMA_NAME:
            raise WindowIntegrityError("binding-window snapshot schema mismatch")
        if snapshot.get("version") != SCHEMA_VERSION:
            raise WindowIntegrityError("binding-window snapshot version mismatch")
        windows = snapshot.get("windows")
        open_contexts = snapshot.get("open_contexts")
        chi_index = snapshot.get("chi_index")
        if not isinstance(windows, dict) or not isinstance(open_contexts, dict):
            raise WindowIntegrityError("windows/open_contexts must be objects")
        if not isinstance(chi_index, dict):
            raise WindowIntegrityError("chi_index must be an object")
        for counter_name in ("next_window_sequence", "next_context_sequence"):
            counter = snapshot.get(counter_name)
            if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
                raise WindowIntegrityError(
                    f"{counter_name} must be a non-negative integer")
        if snapshot["next_window_sequence"] < len(windows):
            raise WindowIntegrityError(
                "next_window_sequence cannot precede retained windows")

        derived_index: dict[str, list[dict]] = {}
        for window_id, record in windows.items():
            if record.get("window_id") != window_id:
                raise WindowIntegrityError(
                    f"window key/id mismatch for {window_id!r}")
            cls._validate_window_record(record, closed=True)
            for entry in record.get("entries") or []:
                location = {"window_id": window_id,
                            "entry_index": entry["entry_index"]}
                bucket = derived_index.setdefault(str(entry["chi"]), [])
                if location not in bucket:
                    bucket.append(location)

        for context_id, record in open_contexts.items():
            if record.get("context_id") != context_id:
                raise WindowIntegrityError(
                    f"open context key/id mismatch for {context_id!r}")
            cls._validate_window_record(record, closed=False)

        normalized_index = {
            str(int(chi)): locations for chi, locations in chi_index.items()}
        if normalized_index != derived_index:
            raise WindowIntegrityError(
                "chi_index does not exactly match closed window entries")

    @classmethod
    def _snapshot_from_legacy_windows(cls, legacy: Mapping[str, Any]) -> dict:
        windows = {}
        for window_id, source_record in legacy.items():
            record = _json_safe(source_record, f"legacy.{window_id}")
            record["window_id"] = str(record.get("window_id") or window_id)
            record["context_id"] = str(
                record.get("context_id") or f"legacy:{record['window_id']}")
            record["context_origin"] = str(
                record.get("context_origin") or "legacy_migration")
            record.setdefault("opened_tick", 0)
            record.setdefault("opened_wall_clock", 0.0)
            record.setdefault("closed_tick", record["opened_tick"])
            record.setdefault("closed_wall_clock", record["opened_wall_clock"])
            record.setdefault("trigger_reason", "legacy_migration")
            record.setdefault("close_reason", "legacy_migration")
            record.setdefault("presence_state", {})
            record.setdefault("affect_snapshot", {})
            record.setdefault("needs_snapshot", {})
            record.setdefault("context_detail", {})
            entries = []
            for index, legacy_entry in enumerate(record.get("entries") or []):
                entry = dict(legacy_entry)
                entry["entry_index"] = index
                entry.setdefault("source_tag", "")
                entry.setdefault("language_position", (
                    index if entry.get("modality") == "word" else None))
                provenance = dict(entry.get("provenance") or {})
                provenance.setdefault("source", entry.get("source_tag") or None)
                provenance.setdefault("source_tag", entry.get("source_tag") or "")
                provenance.setdefault("episode_ref", None)
                provenance.setdefault("episode_refs", [])
                provenance.setdefault("bundle_id", None)
                provenance.setdefault("bundle_ids", [])
                provenance.setdefault("sensory_refs", [])
                provenance.setdefault("scene", {})
                provenance.setdefault("affect", {})
                provenance.setdefault("needs", {})
                provenance.setdefault("salience", None)
                provenance.setdefault("dwell_ticks", None)
                provenance.setdefault("detail", {})
                provenance.setdefault("structural_fact", None)
                entry["provenance"] = provenance
                entries.append(entry)
            record["entries"] = entries
            windows[record["window_id"]] = record

        chi_index: dict[str, list[dict]] = {}
        for window_id, record in windows.items():
            for entry in record["entries"]:
                location = {"window_id": window_id,
                            "entry_index": entry["entry_index"]}
                bucket = chi_index.setdefault(str(entry["chi"]), [])
                if location not in bucket:
                    bucket.append(location)
        return {
            "schema": SCHEMA_NAME,
            "version": SCHEMA_VERSION,
            "windows": windows,
            "open_contexts": {},
            "chi_index": chi_index,
            "next_window_sequence": len(windows),
            "next_context_sequence": 0,
        }
