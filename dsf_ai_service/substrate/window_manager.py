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

# ── Incremental (write-ahead log) persistence ──────────────────────────────
# Closed windows are strictly immutable/append-only (a window record is
# written exactly once, at end_context, and never mutated again).  Rather than
# re-serialising the entire closed-window store every save cycle (the full
# snapshot() path deepcopies + re-validates + re-serialises every window on
# every 60s save -- ~44s over ~220MB in production), each just-closed window is
# appended once, as one canonical hash-verified JSON line, to a rolling segment
# file under WAL_DIRNAME.  The periodic save then writes only a tiny manifest
# (open contexts + counters + a durable WAL marker), never the closed records.
WAL_DIRNAME = "guala_windows_wal"
WAL_SEGMENT_PREFIX = "seg-"
WAL_SEGMENT_SUFFIX = ".jsonl"
# Roll to a fresh segment file at whichever of these limits is hit first, so no
# single segment grows unbounded even between compactions.
WAL_SEGMENT_MAX_RECORDS = 10_000
WAL_SEGMENT_MAX_BYTES = 64 * 1024 * 1024
# Value of the "format" key that marks guala_windows.json as a WAL manifest
# rather than a legacy full-snapshot payload.
MANIFEST_FORMAT = "wal_manifest"


def _canonical_wal_bytes(value: Any) -> bytes:
    """Deterministic canonical JSON bytes for one persisted record/line.

    Mirrors the project's established hash-verified-record convention
    (glew_runtime/*._canonical_bytes): sorted keys, tight separators,
    ASCII-escaped, non-finite floats rejected.  A record hashes and
    re-serialises identically across a json round-trip, so the stored digest
    verifies the exact bytes on restore.
    """
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fsync_dir(path: str) -> None:
    """Commit a directory entry to disk (required on EFS/NFS after create/rename)."""
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_rename_with_retry(tmp: str, final: str) -> None:
    """Rename tmp->final, retrying transient EFS/NFS ENOENT (matches the
    engine's _atomic_write discipline: the data is already fsync'd, only the
    directory-entry lookup can lag on the NFS client)."""
    for attempt in range(4):
        try:
            os.rename(tmp, final)
            return
        except FileNotFoundError:
            if attempt == 3:
                raise
            time.sleep(0.05 * (attempt + 1))


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
        # Persistent O(1) dedup companion to _chi_index: chi -> set of
        # (window_id, entry_index).  Kept in lockstep at every _chi_index
        # mutation site (init / _index_closed_window / restore /
        # restore_from_wal).  The prior ``location not in bucket`` list scan
        # made one giant-window close O(entries x bucket) inside self._lock —
        # measured live 2026-07-15 as a 5+ minute whole-substrate stall
        # (engine loop, saves, autonomy all queued behind one audio-episode
        # close on the post-restore state).
        self._chi_index_seen: dict[int, set] = {}
        self._window_sequence = 0
        self._context_sequence = 0

        # ── Write-ahead-log (incremental persistence) state ──
        # Guarded by its own lock so appending a closed record never blocks
        # concurrent open-context work on ``self._lock``.  Lock order is
        # always self._lock -> self._wal_lock (never the reverse) so the two
        # can be held together (compact/snapshot) without deadlock.
        self._wal_lock = threading.Lock()
        self._wal_dir: Optional[str] = None
        self._wal_enabled = False
        self._wal_generation = 0            # bumped once per compaction
        self._wal_segment_index = 0         # rolls within a generation
        self._wal_segment_records = 0       # records in the active segment file
        self._wal_segment_bytes = 0         # bytes in the active segment file
        self._wal_record_count = 0          # durable records in this generation
        self._wal_digest_hasher = hashlib.sha256()  # rolling digest of record hashes
        # False means the closed-window store is NOT yet reflected in the WAL
        # (fresh-with-windows or a just-migrated legacy snapshot); the next
        # save folds it into a base segment.  Fresh-empty starts True.
        self._wal_base_written = True

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

        if (current is not None
                and current.context_origin in ("inferred", "implicit")
                and inferred is not None and inferred != current.context_id):
            # The caller supplied a new structural episode/bundle boundary.
            # Close only this caller's previously-bound manager-created
            # context.  GL-RPT-WAL-BLOAT F2 (2026-07-15): "implicit" joins
            # "inferred" here -- an implicit context is a manager-generated
            # container for entries that declared no structure, so an entry
            # that DOES declare structure is exactly its real boundary.
            # Before this, an implicit-bound caller absorbed episode/bundle
            # entries forever (origin was "legacy", which this check
            # deliberately skips).  Explicit and legacy (caller-owned
            # ``open()``) contexts still absorb structured entries
            # unchanged -- that behavior is what binds a bundle's lanes and
            # a sentence's words into one window.
            self.end_context(current.context_id, "context_boundary")
            current = None

        if current is not None:
            return current
        if inferred is not None:
            self.begin_context(
                inferred, trigger_reason, _origin="inferred")
            return self._contexts[inferred]

        implicit_id = self._next_context_id("implicit")
        self.begin_context(implicit_id, trigger_reason, _origin="implicit")
        return self._contexts[implicit_id]

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

    @staticmethod
    def _seen_from_chi_index(chi_index: Mapping[int, list]) -> dict[int, set]:
        """Rebuild the O(1) dedup companion from a chi index (restore paths)."""
        return {
            chi: {(location["window_id"], int(location["entry_index"]))
                  for location in locations}
            for chi, locations in chi_index.items()
        }

    def _index_closed_window(self, record: Mapping[str, Any]) -> None:
        window_id = record["window_id"]
        for entry in record.get("entries") or []:
            chi = int(entry["chi"])
            entry_index = int(entry["entry_index"])
            seen = self._chi_index_seen.setdefault(chi, set())
            key = (window_id, entry_index)
            if key in seen:
                continue
            seen.add(key)
            self._chi_index.setdefault(chi, []).append({
                "window_id": window_id,
                "entry_index": entry_index,
            })

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
            # GL-AUDIT-RAM-6GB / GL-RPT-WAL-BLOAT F1 (2026-07-15): the Atlas
            # compatibility mirror is no longer populated.  Its content was a
            # full deepcopy of every closed record (~1.7 GB at production
            # scale) that nothing reads: its only consumer compares mapping
            # identity (manager_for_compatibility_mirror), recall resolves the
            # owning manager and reads canonical memory, and the Atlas never
            # persists it.  Keeping it EMPTY -- rather than sharing record
            # references -- also preserves the original detachment guarantee:
            # no writer can ever corrupt canonical memory through the mirror.
            # The dict OBJECT itself must survive untouched; its identity is
            # the registry key that lets RecallEngine find this manager, and
            # pre-existing content remains honored as a one-time migration
            # input at construction.
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
        # Durably append the just-closed record to the WAL outside ``self._lock``
        # so its small fsync never blocks concurrent open-context work.  The
        # record was fully built and validated (closed=True) inside the lock and
        # closed windows are immutable, so serialising it here is race-free.
        self._wal_on_close(record)
        self._log_event("window_closed", **event)
        return window_id

    def close(self, reason: str, context_id: Optional[str] = None) -> Optional[str]:
        """Backward-compatible close of only the caller's bound context.

        GL-RPT-WAL-BLOAT F2 (2026-07-15): a close that cannot resolve a
        target is now LOUD (``window_close_unbound`` event + ``None``)
        instead of an invisible no-op.  The bound contextvar is caller
        local by design, so a close issued from a different thread -- or
        from a different copied ``contextvars.Context`` (app.py runs every
        executor job in a fresh copy) -- than the opener can never resolve
        the window here.  Real boundary closes must pass ``context_id``
        explicitly (or call ``end_context`` directly), which succeeds
        regardless of thread.
        """
        context_id = context_id or self._bound_context.get()
        if context_id is None:
            self._log_event("window_close_unbound", close_reason=str(reason))
            return None
        return self.end_context(context_id, reason)

    def open_context_ids(self, prefix: str = "") -> tuple[str, ...]:
        """Point-in-time ids of currently-open contexts, optionally filtered
        by id prefix.

        Thread-independent read: unlike ``active_context_id`` (deliberately
        caller-bound), this exposes every open context so a REAL experience
        boundary (e.g. the engine's activity end) can close stragglers by
        EXPLICIT id via ``end_context`` no matter which thread -- or long
        discarded contextvar context -- opened them.  Read-only; the caller
        decides what a real boundary is.  GL-RPT-WAL-BLOAT F2.
        """
        with self._lock:
            return tuple(context_id for context_id in self._contexts
                         if context_id.startswith(prefix))

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
            self._chi_index_seen = self._seen_from_chi_index(chi_index)
            self._window_sequence = next_window_sequence
            self._context_sequence = next_context_sequence
            # Mirror content retired (GL-RPT-WAL-BLOAT F1); mapping identity
            # preserved for the registry.
            self._compatibility_windows.clear()
            self._bound_context.set(None)
            # This full-snapshot restore replaced the closed-window store; the
            # WAL (if any) does not reflect it.  A non-empty store must be
            # folded into a fresh base segment by the next save (see
            # snapshot_incremental); an empty store needs no base.
            with self._wal_lock:
                self._wal_base_written = (len(closed) == 0)
        self._log_event(
            "window_state_restored",
            windows=len(closed), open_contexts=len(contexts),
            chi_buckets=len(chi_index))

    # ── Incremental / write-ahead-log persistence ─────────────────────────
    #
    # Design: a closed window is written exactly once.  Instead of the O(store)
    # full snapshot() every save, each just-closed record is appended as one
    # canonical hash-verified JSON line to a rolling segment file, and the
    # periodic save writes only a tiny manifest (open contexts + counters + a
    # durable WAL marker: generation, record count, rolling digest).  restore
    # replays the segments, re-validating every record and rebuilding the chi
    # index from scratch (with O(1) dedup -- never the O(n) ``_index_closed_
    # window`` list scan, which would reintroduce the boot-time O(n^2) hang
    # fixed in _validate_snapshot).  Compaction folds the store into a fresh
    # base segment on the (rarer) cold-save path.

    @staticmethod
    def _parse_segment_name(name: str) -> Optional[tuple[int, int]]:
        """Return (generation, index) for a WAL segment filename, else None."""
        if (not name.startswith(WAL_SEGMENT_PREFIX)
                or not name.endswith(WAL_SEGMENT_SUFFIX)):
            return None
        core = name[len(WAL_SEGMENT_PREFIX):-len(WAL_SEGMENT_SUFFIX)]
        parts = core.split("-")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    def _wal_segment_path(self, generation: int, index: int) -> str:
        return os.path.join(
            self._wal_dir,
            f"{WAL_SEGMENT_PREFIX}{generation:08d}-{index:08d}{WAL_SEGMENT_SUFFIX}")

    def _scan_wal_max_generation(self, wal_dir: str) -> int:
        max_gen = -1
        for name in os.listdir(wal_dir):
            parsed = self._parse_segment_name(name)
            if parsed is not None:
                max_gen = max(max_gen, parsed[0])
        return max_gen

    def _list_wal_segments(self, generation: int) -> list[tuple[int, str]]:
        """Ordered (index, path) for every segment of one generation on disk."""
        found: list[tuple[int, str]] = []
        for name in os.listdir(self._wal_dir):
            parsed = self._parse_segment_name(name)
            if parsed is not None and parsed[0] == generation:
                found.append((parsed[1], os.path.join(self._wal_dir, name)))
        found.sort(key=lambda item: item[0])
        return found

    def _delete_wal_generations(self, *, keep: Optional[int] = None,
                                below: Optional[int] = None) -> None:
        """Remove stale segment files (keep exactly one generation, or all
        strictly below a bound).  Never removes the live generation's data."""
        if self._wal_dir is None:
            return
        for name in os.listdir(self._wal_dir):
            parsed = self._parse_segment_name(name)
            if parsed is None:
                continue
            gen = parsed[0]
            drop = False
            if keep is not None and gen != keep:
                drop = True
            if below is not None and gen < below:
                drop = True
            if drop:
                try:
                    os.remove(os.path.join(self._wal_dir, name))
                except OSError:
                    pass

    def configure_wal(self, wal_dir: str) -> str:
        """Point the WAL at ``wal_dir`` (idempotent).  Safe before any append.

        Starts a generation strictly above any leftover segments so a fresh or
        legacy-migrated store can never mix with stale data; restore_from_wal
        overrides the generation to the manifest's own.
        """
        if self._wal_enabled and self._wal_dir == wal_dir:
            return self._wal_dir
        os.makedirs(wal_dir, exist_ok=True)
        max_gen = self._scan_wal_max_generation(wal_dir)
        with self._wal_lock:
            self._wal_dir = wal_dir
            self._wal_enabled = True
            self._wal_generation = max_gen + 1 if max_gen >= 0 else 0
            self._wal_segment_index = 0
            self._wal_segment_records = 0
            self._wal_segment_bytes = 0
            self._wal_record_count = 0
            self._wal_digest_hasher = hashlib.sha256()
        return wal_dir

    def configure_wal_under(self, state_dir: str) -> str:
        """Configure the WAL directory as ``state_dir/WAL_DIRNAME``."""
        return self.configure_wal(os.path.join(state_dir, WAL_DIRNAME))

    def _wal_append_line(self, line: bytes, record_hash: str) -> None:
        """Append one durable, fsync'd record line to the active segment.

        Caller must hold ``self._wal_lock``.  Counters/digest advance only
        after the bytes are fsync'd, so the manifest never claims a record
        durable before it truly is.
        """
        if (self._wal_segment_records > 0
                and (self._wal_segment_records >= WAL_SEGMENT_MAX_RECORDS
                     or self._wal_segment_bytes + len(line) > WAL_SEGMENT_MAX_BYTES)):
            self._wal_segment_index += 1
            self._wal_segment_records = 0
            self._wal_segment_bytes = 0
        path = self._wal_segment_path(self._wal_generation, self._wal_segment_index)
        new_file = self._wal_segment_records == 0
        with open(path, "ab") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        if new_file:
            _fsync_dir(self._wal_dir)
        self._wal_segment_records += 1
        self._wal_segment_bytes += len(line)
        self._wal_record_count += 1
        self._wal_digest_hasher.update(record_hash.encode("ascii"))
        self._wal_digest_hasher.update(b"\n")

    def append_closed_record(self, record: Mapping[str, Any]) -> bytes:
        """Validate a closed-window record and append it to the WAL.

        Returns the exact canonical line bytes that were (or would be) written.
        When the WAL is not configured the bytes are still produced but not
        persisted (so callers can serialise without a directory).
        """
        if not isinstance(record, Mapping):
            raise TypeError("append_closed_record requires a window record mapping")
        self._validate_window_record(record, closed=True)
        record_hash = _sha256_hex(_canonical_wal_bytes(record))
        line = _canonical_wal_bytes(
            {"record": record, "sha256": record_hash}) + b"\n"
        with self._wal_lock:
            if self._wal_enabled:
                self._wal_append_line(line, record_hash)
        return line

    def _wal_on_close(self, record: Mapping[str, Any]) -> None:
        """Durably append a just-closed record when the WAL already reflects
        the store.  If the record cannot be appended durably right now -- the
        WAL is not configured yet (e.g. a close before the first save on a
        fresh boot), or the store is a legacy migration awaiting its first base
        compaction -- the WAL no longer reflects the store, so mark it for a
        fold-into-base by the next save rather than silently losing the record.
        """
        with self._wal_lock:
            if not (self._wal_enabled and self._wal_base_written):
                self._wal_base_written = False
                return
            record_hash = _sha256_hex(_canonical_wal_bytes(record))
            line = _canonical_wal_bytes(
                {"record": record, "sha256": record_hash}) + b"\n"
            self._wal_append_line(line, record_hash)

    def snapshot_incremental(self, since_seq: Optional[int] = None) -> dict:
        """Return the small save-cycle manifest (open contexts + counters + a
        durable WAL marker).  Closed records are NOT included here: each was
        already appended durably at close time, so the periodic save cost is
        proportional to the number of OPEN contexts, never the whole store.

        ``since_seq`` is accepted for API compatibility; it is unnecessary in
        the append-at-close design because closed records are already durable.
        """
        with self._lock:
            if not self._wal_enabled:
                raise WindowIntegrityError(
                    "WAL directory is not configured; call configure_wal first")
            if not self._wal_base_written:
                # First save after a legacy migration or a fresh-with-windows
                # start: fold the current closed store into a base segment so
                # the manifest faithfully represents it.
                self._compact_locked()
            with self._wal_lock:
                generation = self._wal_generation
                durable_count = self._wal_record_count
                digest = self._wal_digest_hasher.copy().hexdigest()
            open_contexts = {
                context_id: window.to_record()
                for context_id, window in self._contexts.items()
            }
            for context_id, record in open_contexts.items():
                if record.get("context_id") != context_id:
                    raise WindowIntegrityError(
                        f"open context key/id mismatch for {context_id!r}")
                self._validate_window_record(record, closed=False)
            manifest = {
                "schema": SCHEMA_NAME,
                "version": SCHEMA_VERSION,
                "format": MANIFEST_FORMAT,
                "wal_generation": generation,
                "wal_durable_count": durable_count,
                "wal_digest": digest,
                "closed_window_count": len(self._windows),
                "open_contexts": open_contexts,
                "next_window_sequence": self._window_sequence,
                "next_context_sequence": self._context_sequence,
            }
            # Final strict-JSON guarantee, including NaN rejection (mirrors
            # snapshot()'s last line of defence).
            json.dumps(manifest, allow_nan=False, sort_keys=True)
            return manifest

    def compact(self, wal_dir: Optional[str] = None) -> dict:
        """Fold the entire closed-window store into a single fresh base
        segment and reset the WAL to it.  Cold-save (rare) path."""
        with self._lock:
            if wal_dir is not None:
                self.configure_wal(wal_dir)
            if not self._wal_enabled:
                raise WindowIntegrityError(
                    "WAL directory is not configured; call configure_wal first")
            return self._compact_locked()

    def _compact_locked(self) -> dict:
        """Write a new base segment holding every current closed window, make
        it durable, then switch the live WAL onto it.  Caller holds ``_lock``.
        """
        records = list(self._windows.values())
        new_generation = self._wal_generation + 1
        tmp_path = self._wal_segment_path(new_generation, 0) + ".tmp"
        final_path = self._wal_segment_path(new_generation, 0)
        digest = hashlib.sha256()
        total_bytes = 0
        with open(tmp_path, "wb") as handle:
            for record in records:
                record_hash = _sha256_hex(_canonical_wal_bytes(record))
                line = _canonical_wal_bytes(
                    {"record": record, "sha256": record_hash}) + b"\n"
                handle.write(line)
                total_bytes += len(line)
                digest.update(record_hash.encode("ascii"))
                digest.update(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_dir(self._wal_dir)
        _atomic_rename_with_retry(tmp_path, final_path)
        _fsync_dir(self._wal_dir)
        with self._wal_lock:
            prev_generation = self._wal_generation
            self._wal_generation = new_generation
            self._wal_segment_index = 0
            self._wal_segment_records = len(records)
            self._wal_segment_bytes = total_bytes
            self._wal_record_count = len(records)
            self._wal_digest_hasher = digest
            self._wal_base_written = True
        # Older generations are now fully superseded by this base and safe to
        # drop.  The PREVIOUS generation is kept until the caller's manifest
        # (pointing here) is durable; the next compaction / a boot restore
        # removes it -- so a crash mid-compaction can always fall back to the
        # last committed generation.
        self._delete_wal_generations(below=prev_generation)
        self._log_event(
            "window_wal_compacted", generation=new_generation,
            records=len(records), bytes=total_bytes)
        return {"generation": new_generation, "records": len(records),
                "path": final_path, "bytes": total_bytes}

    @classmethod
    def _verify_wal_line(cls, raw: bytes) -> tuple[dict, str]:
        """Parse+verify one WAL line, returning (record, record_hash).

        Raises on any malformation, hash mismatch, or record-integrity fault.
        """
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError("WAL line is not a JSON object")
        record = obj.get("record")
        stored_hash = obj.get("sha256")
        if not isinstance(record, dict) or not isinstance(stored_hash, str):
            raise ValueError("WAL line missing record/sha256")
        actual_hash = _sha256_hex(_canonical_wal_bytes(record))
        if actual_hash != stored_hash:
            raise ValueError("WAL record hash mismatch")
        cls._validate_window_record(record, closed=True)
        return record, stored_hash

    @staticmethod
    def _parse_window_sequence(window_id: Any) -> int:
        """Best-effort sequence embedded in ``win_<seq:016x>_<id>``; -1 if not."""
        if not isinstance(window_id, str) or not window_id.startswith("win_"):
            return -1
        try:
            return int(window_id.split("_")[1], 16)
        except (IndexError, ValueError):
            return -1

    @staticmethod
    def _parse_context_sequence(context_id: Any) -> int:
        """Sequence embedded in a manager-generated ``legacy:<16hex>`` /
        ``implicit:<16hex>`` context id -- the only forms ``_next_context_id``
        emits, and thus the only ones whose sequence could collide with a
        future generated id.  Returns -1 for any caller-supplied context id
        (``episode:...``, ``bundle:...``, or an arbitrary explicit string), so
        next_context_sequence is bumped only by real generated sequences."""
        if not isinstance(context_id, str):
            return -1
        for prefix in ("legacy:", "implicit:"):
            if context_id.startswith(prefix):
                try:
                    return int(context_id[len(prefix):], 16)
                except ValueError:
                    return -1
        return -1

    def restore_from_wal(self, manifest: Mapping[str, Any], wal_dir: str) -> None:
        """Replay the WAL segments for the manifest's generation, verifying
        every record, and atomically install the reconstructed state.

        Records the manifest counted as durable are digest-verified as a
        matched prefix; any records appended after the last manifest but before
        a crash are individually hash-verified and recovered (less loss than
        the old full-save-only model).  A torn/incomplete trailing record (only
        ever possible as the very last line) is discarded, never accepted.
        """
        if not isinstance(manifest, Mapping):
            raise WindowIntegrityError("WAL manifest must be a mapping")
        if manifest.get("format") != MANIFEST_FORMAT:
            raise WindowIntegrityError("payload is not a WAL manifest")
        if manifest.get("schema") != SCHEMA_NAME:
            raise WindowIntegrityError("WAL manifest schema mismatch")
        if manifest.get("version") != SCHEMA_VERSION:
            raise WindowIntegrityError("WAL manifest version mismatch")
        os.makedirs(wal_dir, exist_ok=True)
        self._wal_dir = wal_dir

        generation = int(manifest["wal_generation"])
        durable_count = int(manifest["wal_durable_count"])
        expected_digest = str(manifest["wal_digest"])
        if durable_count < 0:
            raise WindowIntegrityError("WAL durable_count must be non-negative")

        segments = self._list_wal_segments(generation)
        records: list[dict] = []
        record_hashes: list[str] = []
        torn_discarded = 0
        for seg_pos, (_, path) in enumerate(segments):
            is_last_segment = seg_pos == len(segments) - 1
            with open(path, "rb") as handle:
                content = handle.read()
            if not content:
                continue
            ends_with_newline = content.endswith(b"\n")
            lines = content.split(b"\n")
            if ends_with_newline:
                lines = lines[:-1]
            for line_pos, raw in enumerate(lines):
                is_trailing_partial = (
                    is_last_segment
                    and line_pos == len(lines) - 1
                    and not ends_with_newline)
                if raw == b"":
                    # Blank line: only tolerable as a torn trailing artifact.
                    if is_trailing_partial:
                        torn_discarded += 1
                        continue
                    raise WindowIntegrityError(
                        f"WAL segment {os.path.basename(path)} has an empty "
                        f"interior record at line {line_pos}")
                try:
                    record, record_hash = self._verify_wal_line(raw)
                except (ValueError, KeyError, TypeError,
                        json.JSONDecodeError, WindowIntegrityError) as exc:
                    if is_trailing_partial:
                        torn_discarded += 1
                        continue
                    raise WindowIntegrityError(
                        f"WAL segment {os.path.basename(path)} line {line_pos} "
                        f"is corrupt and is not the trailing record: {exc}")
                records.append(record)
                record_hashes.append(record_hash)

        if len(records) < durable_count:
            raise WindowIntegrityError(
                f"WAL generation {generation} holds {len(records)} valid "
                f"records, fewer than the {durable_count} the manifest marks "
                f"durable -- committed data is missing")
        verify = hashlib.sha256()
        for record_hash in record_hashes[:durable_count]:
            verify.update(record_hash.encode("ascii"))
            verify.update(b"\n")
        if verify.hexdigest() != expected_digest:
            raise WindowIntegrityError(
                "WAL durable prefix digest does not match the manifest")

        # Rebuild windows + chi index with O(1) dedup (never _index_closed_
        # window's O(n) list scan) so a large single-chi bucket cannot make
        # boot O(n^2).  Every (window_id, entry_index) is unique by
        # construction, so the dedup is defensive only.
        windows: dict[str, dict] = {}
        chi_index: dict[int, list[dict]] = {}
        chi_seen: dict[int, set] = {}
        max_window_seq = -1
        for record in records:
            window_id = record["window_id"]
            windows[window_id] = record
            max_window_seq = max(
                max_window_seq, self._parse_window_sequence(window_id))
            for entry in record.get("entries") or []:
                chi = int(entry["chi"])
                entry_index = int(entry["entry_index"])
                seen = chi_seen.setdefault(chi, set())
                key = (window_id, entry_index)
                if key in seen:
                    continue
                seen.add(key)
                chi_index.setdefault(chi, []).append(
                    {"window_id": window_id, "entry_index": entry_index})

        # Open contexts from the manifest; a context whose window already
        # appears closed in the WAL (a close that raced the manifest read) is
        # superseded by the closed record and dropped from the open set.
        open_contexts: dict[str, BindingWindow] = {}
        max_context_seq = -1
        for context_id, raw_record in (manifest.get("open_contexts") or {}).items():
            record = _json_safe(raw_record, f"manifest.open_contexts.{context_id}")
            if record.get("context_id") != context_id:
                raise WindowIntegrityError(
                    f"open context key/id mismatch for {context_id!r}")
            self._validate_window_record(record, closed=False)
            window = BindingWindow.from_record(record)
            max_window_seq = max(
                max_window_seq, self._parse_window_sequence(window.window_id))
            max_context_seq = max(
                max_context_seq, self._parse_context_sequence(context_id))
            if window.window_id in windows:
                continue
            open_contexts[context_id] = window
        for window_id_key in windows:
            record = windows[window_id_key]
            max_context_seq = max(
                max_context_seq,
                self._parse_context_sequence(record.get("context_id")))

        next_window_sequence = max(
            int(manifest["next_window_sequence"]),
            len(windows),
            max_window_seq + 1)
        next_context_sequence = max(
            int(manifest["next_context_sequence"]),
            max_context_seq + 1)

        last_index = segments[-1][0] if segments else -1
        rolling = hashlib.sha256()
        for record_hash in record_hashes:
            rolling.update(record_hash.encode("ascii"))
            rolling.update(b"\n")

        with self._lock:
            self._windows.clear()
            self._windows.update(windows)
            self.windows = self._windows  # legacy direct-read surface
            self._contexts = open_contexts
            self._chi_index = chi_index
            # The replay's own dedup sets become the live O(1) companion —
            # same (window_id, entry_index) keys _index_closed_window uses.
            self._chi_index_seen = chi_seen
            self._window_sequence = next_window_sequence
            self._context_sequence = next_context_sequence
            # Mirror content retired (GL-RPT-WAL-BLOAT F1); mapping identity
            # preserved for the registry.
            self._compatibility_windows.clear()
            self._bound_context.set(None)
            with self._wal_lock:
                self._wal_dir = wal_dir
                self._wal_enabled = True
                self._wal_generation = generation
                # New closes append to a FRESH segment after the last existing
                # one, so they can never merge with a discarded torn tail.
                self._wal_segment_index = last_index + 1
                self._wal_segment_records = 0
                self._wal_segment_bytes = 0
                self._wal_record_count = len(records)
                self._wal_digest_hasher = rolling
                self._wal_base_written = True
        # Drop any non-current generation (older superseded, or an orphan base
        # from a compaction that crashed before its manifest committed).
        self._delete_wal_generations(keep=generation)
        self._log_event(
            "window_state_restored_wal",
            windows=len(windows), open_contexts=len(open_contexts),
            chi_buckets=len(chi_index), durable_count=durable_count,
            recovered=len(records) - durable_count,
            torn_discarded=torn_discarded, generation=generation)

    def restore_persisted(self, data: Mapping[str, Any], state_dir: str) -> None:
        """Restore window state from either a WAL manifest (new format) or a
        legacy full snapshot, configuring the WAL either way."""
        wal_dir = os.path.join(state_dir, WAL_DIRNAME)
        self.configure_wal(wal_dir)
        if isinstance(data, Mapping) and data.get("format") == MANIFEST_FORMAT:
            self.restore_from_wal(data, wal_dir)
        else:
            # Legacy full snapshot; the next save folds it into a WAL base.
            self.restore(data)

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
        derived_seen: dict[str, set[tuple[str, int]]] = {}
        for window_id, record in windows.items():
            if record.get("window_id") != window_id:
                raise WindowIntegrityError(
                    f"window key/id mismatch for {window_id!r}")
            cls._validate_window_record(record, closed=True)
            for entry in record.get("entries") or []:
                chi_key = str(entry["chi"])
                dedupe_key = (window_id, entry["entry_index"])
                seen = derived_seen.setdefault(chi_key, set())
                if dedupe_key not in seen:
                    seen.add(dedupe_key)
                    derived_index.setdefault(chi_key, []).append(
                        {"window_id": window_id,
                         "entry_index": entry["entry_index"]})

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
