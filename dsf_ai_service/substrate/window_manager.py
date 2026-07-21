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
import collections.abc
import contextvars
import copy
import hashlib
import json
import math
import os
import threading
import time
import weakref
from collections import OrderedDict, namedtuple
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Mapping, Optional


SCHEMA_NAME = "dsf.binding_windows"
SCHEMA_VERSION = 2

# ── Disk-resident closed-window store (GL-SPC-SUBSTRATE-TRUE §memory) ───────
# RAM holds only the chi index + a window LOCATOR (window_id -> exact byte
# range in a WAL segment) + small per-window METADATA + a byte-budgeted LRU
# content cache.  Window CONTENT lives on disk and is fetched on demand; it
# never materializes wholesale at boot (P1: RAM never scales with lifetime
# experience).  The WAL format and its write-once discipline are UNCHANGED —
# this is a read-side re-architecture only.
WINDOW_CACHE_MB_ENV = "GUALA_WINDOW_CACHE_MB"
WINDOW_CACHE_DEFAULT_MB = 256
# GUALA_WINDOW_CACHE_MB is a budget on ESTIMATED RESIDENT bytes, not
# serialized bytes.  A parsed window record costs measurably more RAM than
# its canonical JSON line (dict/str object overhead; measured ~4.9x on
# production-shaped records, review 2026-07-16), so each cached record is
# accounted at serialized_length x CACHE_RESIDENT_MULTIPLIER.  The default
# 256MB budget therefore admits ~51MB of serialized content (~256MB
# resident), keeping the cache honest against the <2GB process target.
CACHE_RESIDENT_MULTIPLIER = 5

# Appended to every named integrity-halt message so the 03:00 operator knows
# the sanctioned recovery path without reading the spec.
RESTORE_HINT = (
    "Recovery: STOP the service, then restore a named S3 backup with "
    "'python -m tools.restore_from_s3 --list' / '--backup <name>'.")

# Record kinds inside a WAL line's "record" object.  A record with no
# "record_kind" key is a full closed window (every record written today).
# "window_gist" is RESERVED for the Change-3 distill-then-fade lane: a window
# whose verbatim content has been released and replaced by metadata + a
# distilled gist.  Change 1 does not WRITE gist records, but the read side
# must tolerate them from day one (typed record on fetch, never a
# hash-verification crash) so forgetting is one more compaction policy, not
# a format fork.
RECORD_KIND_KEY = "record_kind"
RECORD_KIND_GIST = "window_gist"

# Locator entry: exactly where one closed record's canonical line lives.
# ``kind`` is "window" (full content) or "gist" (content released; fetch
# returns the typed gist record).
WindowLocation = namedtuple(
    "WindowLocation", ("path", "offset", "length", "kind"))


def _window_cache_budget_bytes() -> int:
    raw = os.environ.get(WINDOW_CACHE_MB_ENV, "")
    try:
        mb = float(raw) if raw else float(WINDOW_CACHE_DEFAULT_MB)
    except ValueError:
        mb = float(WINDOW_CACHE_DEFAULT_MB)
    return max(0, int(mb * 1024 * 1024))

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

# ── Boot-time checkpoint (GL-FIX-WAL-BOOT-CHECKPOINT-20260720) ─────────────
# Compaction already streams and re-verifies every closed record once, to
# rewrite them into one fresh base segment (see _compact_locked). Nothing
# used to consume that work at boot: restore_from_wal re-parsed and
# re-verified the base's records from scratch too, every single time, so
# boot cost grew with her ENTIRE lifetime forever regardless of how often
# compaction ran. A checkpoint written alongside each compaction's base
# lets restore trust that base (one cheap whole-file digest check, no
# per-record re-parse) and fully re-verify only what was appended SINCE
# that compaction. Any checkpoint miss, corruption, or digest mismatch
# falls back to the original full replay unchanged -- this can only make
# boot faster, never less safe (see restore_from_wal's fast-path comment).
# Scope, stated plainly: this removes per-record JSON-parse/schema-
# validation/re-hash cost for the base (measured a real, constant-factor
# speedup) -- it does NOT make boot cost independent of her total
# lifetime. Loading the checkpoint is still one JSON parse sized by total
# historical window count, because locator/window_meta/chi_index are
# inherently per-window data the runtime needs fully resident for recall
# regardless of how it was loaded. A complexity-class change would mean
# keeping fewer old windows resident at all -- a bigger, separate decision
# this fix deliberately does not make.
WAL_CHECKPOINT_PREFIX = "ckpt-"
WAL_CHECKPOINT_SUFFIX = ".json"
CHECKPOINT_FORMAT = "wal_index_checkpoint"


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


class WindowStoreIntegrityHalt(WindowIntegrityError):
    """NAMED loud-halt error (P4): durable window memory failed verification.

    Raised when a WAL record's hash does not verify, the manifest's durable
    prefix digest mismatches, committed records are missing, or a located
    record cannot be read back from its segment.  Boot must HALT on this —
    it must never be swallowed into recover-and-continue paths."""


class _WindowsContentView(collections.abc.Mapping):
    """Read-only mapping surface over the disk-resident closed-window store.

    Preserves the legacy ``manager.windows`` direct-read contract
    (``[window_id]``, ``in``, ``len``, iteration, ``.values()``) while content
    is fetched on demand and returned as a detached copy.  Never a write
    surface: closed windows are write-once."""

    def __init__(self, manager: "WindowManager"):
        self._manager = manager

    def __getitem__(self, window_id: str) -> dict:
        record = self._manager._fetch_window_detached(str(window_id))
        if record is None:
            raise KeyError(window_id)
        return record

    def __iter__(self):
        return iter(self._manager.window_ids())

    def __len__(self) -> int:
        return self._manager.closed_window_count()

    def __contains__(self, window_id) -> bool:
        return self._manager.has_closed_window(str(window_id))


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
    _settlement_in_progress: bool = field(default=False, repr=False)
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
        if self.closed_tick is not None or self.closed_wall_clock is not None:
            raise WindowIntegrityError("cannot mutate a closed binding window")
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
        retain_closed_windows: bool = True,
        settle_window_fn: Optional[Callable[[Mapping[str, Any]], Any]] = None,
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
        self._retain_closed_windows = bool(retain_closed_windows)
        self._settle_window = settle_window_fn
        self._lock = threading.RLock()
        self._bound_context = contextvars.ContextVar(
            f"binding_window_context_{id(self)}", default=None)
        self._contexts: dict[str, BindingWindow] = {}
        # ── Disk-resident closed-window store ──
        # _window_locator: window_id -> WindowLocation (segment byte range).
        # _window_meta:    window_id -> small metadata dict (close reason,
        #                  origin, modality summary, word list, affect at
        #                  close, reinforcement count, last-fetched tick —
        #                  the fade policy's future inputs live here too).
        # _pending:        full records not yet durable in the current WAL
        #                  generation (closes before configure_wal, or a
        #                  restored legacy snapshot awaiting its base fold).
        #                  Bounded by construction: boot->first-save only.
        # Content itself stays on disk; reads go through the LRU cache.
        self._window_locator: dict[str, WindowLocation] = {}
        self._window_meta: dict[str, dict] = {}
        self._pending: dict[str, dict] = {}
        self.windows = _WindowsContentView(self)  # legacy direct-read surface
        self._cache_lock = threading.Lock()
        self._content_cache: OrderedDict[str, tuple[dict, int]] = OrderedDict()
        self._content_cache_bytes = 0
        self._content_cache_budget = _window_cache_budget_bytes()
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

    # ── Disk-resident store: metadata, cache, fetch-on-demand ─────────────

    @staticmethod
    def _window_metadata_from_record(record: Mapping[str, Any]) -> dict:
        """Small resident metadata for one closed record.

        Includes the boot-scan fields the language-fact rebuild needs
        (close reason, origin, modality summary, word list) plus the fields
        the Change-3 distill-then-fade policy will need (affect summary at
        close, reinforcement count, last-fetched tick)."""
        if record.get(RECORD_KIND_KEY) == RECORD_KIND_GIST:
            meta = {
                "close_reason": record.get("close_reason"),
                "context_origin": record.get("context_origin"),
                "experience_origin": record.get("experience_origin"),
                "modalities": tuple(record.get("modalities") or ()),
                "word_count": int(record.get("word_count") or 0),
                "entry_count": 0,
                "opened_tick": record.get("opened_tick"),
                "closed_tick": record.get("closed_tick"),
                "affect_snapshot": dict(record.get("affect_snapshot") or {}),
                "reinforcement_count": int(
                    record.get("reinforcement_count") or 1),
                "content_released": True,
                "gist": copy.deepcopy(record.get("gist") or {}),
                "last_fetched_tick": None,
            }
            return meta
        entries = record.get("entries") or []
        modalities: list[str] = []
        seen_modalities: set[str] = set()
        # P1 review 2026-07-16: metadata keeps a word COUNT, never the word
        # list — a resident per-window word list scales RAM with lifetime
        # language experience, and qualification only needs the word-modality
        # flag (in ``modalities``); qualifying windows are fetched anyway.
        word_count = 0
        for entry in entries:
            modality = str(entry.get("modality") or "")
            if modality not in seen_modalities:
                seen_modalities.add(modality)
                modalities.append(modality)
            if modality == "word":
                word_count += 1
        return {
            "close_reason": record.get("close_reason"),
            "context_origin": record.get("context_origin"),
            "experience_origin": (
                (record.get("context_detail") or {}).get("experience_origin")),
            "modalities": tuple(modalities),
            "word_count": word_count,
            "entry_count": len(entries),
            "opened_tick": record.get("opened_tick"),
            "closed_tick": record.get("closed_tick"),
            "affect_snapshot": dict(record.get("affect_snapshot") or {}),
            "reinforcement_count": int(record.get("reinforcement_count") or 1),
            "content_released": False,
            "last_fetched_tick": None,
        }

    def window_ids(self) -> tuple[str, ...]:
        """Every closed window id, in durable append order (point in time)."""
        with self._lock:
            ids = list(self._window_locator)
            ids.extend(wid for wid in self._pending
                       if wid not in self._window_locator)
            return tuple(ids)

    def closed_window_count(self) -> int:
        with self._lock:
            extra = sum(1 for wid in self._pending
                        if wid not in self._window_locator)
            return len(self._window_locator) + extra

    def has_closed_window(self, window_id: str) -> bool:
        with self._lock:
            return (window_id in self._window_locator
                    or window_id in self._pending)

    def window_metadata(self, window_id: str) -> Optional[dict]:
        """Detached copy of one window's small resident metadata."""
        with self._lock:
            meta = self._window_meta.get(str(window_id))
            return None if meta is None else copy.deepcopy(meta)

    def _cache_get(self, window_id: str) -> Optional[dict]:
        with self._cache_lock:
            hit = self._content_cache.get(window_id)
            if hit is None:
                return None
            self._content_cache.move_to_end(window_id)
            record = hit[0]
        # Deepcopy OUTSIDE the cache lock: cached records are private
        # immutable copies (installed detached, only ever read), so copying
        # after release is safe and keeps a big record's copy cost from
        # serialising every other cache access.
        return copy.deepcopy(record)

    def _cache_put(self, window_id: str, record: dict, nbytes: int) -> None:
        # Account ESTIMATED RESIDENT cost, not serialized bytes — a parsed
        # record occupies ~CACHE_RESIDENT_MULTIPLIER x its canonical line
        # (see the constant's note).  The budget is honest RAM, per P1.
        cost = nbytes * CACHE_RESIDENT_MULTIPLIER
        if cost > self._content_cache_budget:
            return  # larger than the whole budget: serve straight from disk
        detached = copy.deepcopy(record)
        with self._cache_lock:
            previous = self._content_cache.pop(window_id, None)
            if previous is not None:
                self._content_cache_bytes -= previous[1]
            self._content_cache[window_id] = (detached, cost)
            self._content_cache_bytes += cost
            while (self._content_cache_bytes > self._content_cache_budget
                   and self._content_cache):
                _, (_, evicted_cost) = self._content_cache.popitem(last=False)
                self._content_cache_bytes -= evicted_cost

    def _cache_clear(self) -> None:
        with self._cache_lock:
            self._content_cache.clear()
            self._content_cache_bytes = 0

    def cache_stats(self) -> dict:
        with self._cache_lock:
            return {
                "entries": len(self._content_cache),
                "bytes": self._content_cache_bytes,
                "budget_bytes": self._content_cache_budget,
            }

    def _read_located_record(self, location: WindowLocation) -> dict:
        """Read + hash-verify one located record line from its segment."""
        with open(location.path, "rb") as handle:
            handle.seek(location.offset)
            raw = handle.read(location.length)
        if len(raw) != location.length:
            raise WindowStoreIntegrityHalt(
                f"short read at {os.path.basename(location.path)}"
                f"+{location.offset}: got {len(raw)} of {location.length} bytes")
        record, _record_hash = self._verify_wal_line(raw.rstrip(b"\n"))
        return record

    def _fetch_window_detached(self, window_id: str) -> Optional[dict]:
        """Fetch one closed record on demand: pending -> LRU cache -> disk.

        Always returns a detached copy (or None for an unknown id).  Retries
        across a concurrent compaction (the locator is rebuilt when segment
        files are rewritten); an unreadable located record is a NAMED loud
        halt (P4), never a silent miss."""
        window_id = str(window_id)
        last_error: Optional[Exception] = None
        for _attempt in range(4):
            with self._lock:
                pending = self._pending.get(window_id)
                if pending is not None:
                    self._note_window_fetch(window_id)
                    return copy.deepcopy(pending)
                location = self._window_locator.get(window_id)
            if location is None:
                return None
            cached = self._cache_get(window_id)
            if cached is not None:
                with self._lock:
                    self._note_window_fetch(window_id)
                return cached
            try:
                record = self._read_located_record(location)
                if record.get("window_id") != window_id:
                    raise WindowStoreIntegrityHalt(
                        f"located record at {os.path.basename(location.path)}"
                        f"+{location.offset} holds "
                        f"{record.get('window_id')!r}, not {window_id!r}")
            except (OSError, ValueError, KeyError, TypeError,
                    WindowIntegrityError) as error:
                last_error = error
                with self._lock:
                    current = self._window_locator.get(window_id)
                if current is not None and current != location:
                    continue  # locator moved (compaction) — retry fresh
                raise WindowStoreIntegrityHalt(
                    f"closed window {window_id!r} could not be read from its "
                    f"durable location {location}: {error}") from error
            self._cache_put(window_id, record, location.length)
            with self._lock:
                self._note_window_fetch(window_id)
            return record
        raise WindowStoreIntegrityHalt(
            f"closed window {window_id!r} unreadable after locator retries: "
            f"{last_error}")

    def _note_window_fetch(self, window_id: str) -> None:
        """Record fetch recency (fade-policy input).  Caller holds _lock."""
        meta = self._window_meta.get(window_id)
        if meta is not None:
            try:
                meta["last_fetched_tick"] = int(self._get_tick())
            except Exception:
                pass

    def _fetch_many_detached(self, window_ids) -> dict[str, Optional[dict]]:
        """Fetch a batch of closed records, reading cache misses through ONE
        file handle per segment in (path, offset) order.

        A per-window open()+seek() made a cold 200-window chi bucket cost
        0.7-6s on EFS (review measurement 2026-07-16); grouped sequential
        reads amortise the round trips.  Any per-record read/verify failure
        falls back to the retrying single fetch (which absorbs compaction
        races and raises the NAMED halt when truly unreadable)."""
        results: dict[str, Optional[dict]] = {}
        misses: list[tuple[str, WindowLocation]] = []
        for window_id in window_ids:
            window_id = str(window_id)
            if window_id in results:
                continue
            with self._lock:
                pending = self._pending.get(window_id)
                if pending is not None:
                    self._note_window_fetch(window_id)
                    results[window_id] = copy.deepcopy(pending)
                    continue
                location = self._window_locator.get(window_id)
            if location is None:
                results[window_id] = None
                continue
            cached = self._cache_get(window_id)
            if cached is not None:
                with self._lock:
                    self._note_window_fetch(window_id)
                results[window_id] = cached
                continue
            misses.append((window_id, location))

        misses.sort(key=lambda item: (item[1].path, item[1].offset))
        handle = None
        handle_path = None
        try:
            for window_id, location in misses:
                try:
                    if handle is None or handle_path != location.path:
                        if handle is not None:
                            handle.close()
                            handle = None
                        handle = open(location.path, "rb")
                        handle_path = location.path
                    handle.seek(location.offset)
                    raw = handle.read(location.length)
                    if len(raw) != location.length:
                        raise WindowStoreIntegrityHalt(
                            f"short read at "
                            f"{os.path.basename(location.path)}"
                            f"+{location.offset}")
                    record, _record_hash = self._verify_wal_line(
                        raw.rstrip(b"\n"))
                    if record.get("window_id") != window_id:
                        raise WindowStoreIntegrityHalt(
                            f"located record holds "
                            f"{record.get('window_id')!r}, "
                            f"not {window_id!r}")
                except (OSError, ValueError, KeyError, TypeError,
                        WindowIntegrityError):
                    # Segment may have been rewritten (compaction) or this
                    # handle is stale — the single-fetch path re-resolves the
                    # locator, retries, and halts loudly if truly corrupt.
                    if handle is not None:
                        handle.close()
                        handle = None
                        handle_path = None
                    results[window_id] = self._fetch_window_detached(window_id)
                    continue
                self._cache_put(window_id, record, location.length)
                with self._lock:
                    self._note_window_fetch(window_id)
                results[window_id] = copy.deepcopy(record)
        finally:
            if handle is not None:
                handle.close()
        return results

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
            # An explicit context_id on an ENTRY is routing, not a binding
            # claim.  begin_context() rebinds this caller's contextvar as a
            # side effect; when the caller already held a DIFFERENT open
            # binding, restore it so a targeted write (e.g. the per-frame
            # sense contexts of process_sight_frame/process_sound_frame,
            # GL-RPT-WAL-BLOAT F2) can never steal the thread's experience
            # context.  Root cause of the observed-conversation empty-window
            # bug (2026-07-16): a send-time camera frame rebound the turn's
            # live-conversation binding to its frame context, whose close
            # then reset the binding to None — every following word entry
            # routed to fresh implicit contexts and the observed window
            # closed with zero entries, so its BindingWindowCitation had no
            # modalities to cite.
            previous = self._bound_context.get()
            self.begin_context(explicit_context_id, trigger_reason)
            explicit_context_id = explicit_context_id.strip()
            if previous is not None and previous != explicit_context_id:
                with self._lock:
                    if previous in self._contexts:
                        self._bound_context.set(previous)
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

        ``mirror_atlas=False`` is valid only when another structural store
        already receives the same event (for example the persisted visual
        motif system). The production engine does not retain closed windows,
        so a canonical fact with no other structural destination must mirror
        into LivingAtlas, which preserves its explicit ``structural_fact`` at
        the exact chi cell rather than flattening it into a score.
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
            if self._retain_closed_windows:
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
                    reason: str = "context_complete",
                    *,
                    return_settlement: bool = False):
        """Close and settle one immutable context without holding the global lock."""
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                return None
            if window._settlement_in_progress:
                raise WindowIntegrityError(
                    "binding context settlement is already in progress")
            if window.closed_tick is None:
                window.closed_tick = int(self._get_tick())
                window.closed_wall_clock = time.time()
                window.close_reason = str(reason)
            record = window.to_record()
            self._validate_window_record(record, closed=True)
            window_id = window.window_id
            window._settlement_in_progress = True

        settlement_result = None
        if self._settle_window is not None:
            try:
                settlement_result = self._settle_window(record)
            except Exception as exc:
                with self._lock:
                    current = self._contexts.get(context_id)
                    if current is window:
                        window._settlement_in_progress = False
                self._log_event(
                    "window_settlement_failed",
                    window_id=window_id,
                    context_id=context_id,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise

        with self._lock:
            current = self._contexts.get(context_id)
            if current is not window or not window._settlement_in_progress:
                raise WindowIntegrityError(
                    "binding context changed during atomic settlement")
            if window.to_record() != record:
                window._settlement_in_progress = False
                raise WindowIntegrityError(
                    "closed binding context mutated during settlement")
            removed = self._contexts.pop(context_id, None)
            if removed is not window:
                raise WindowIntegrityError(
                    "binding context changed during atomic settlement")
            if self._retain_closed_windows:
                # Disk-resident store: the record parks in _pending (readable
                # immediately) and moves to the durable locator once its WAL
                # append lands (_wal_on_close below, outside this lock).  RAM
                # keeps only locator + metadata + chi index afterwards.
                self._pending[window.window_id] = record
                self._window_meta[window.window_id] = (
                    self._window_metadata_from_record(record))
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
        if self._retain_closed_windows:
            # Durably append the just-closed record to the WAL outside
            # ``self._lock`` so its small fsync never blocks concurrent
            # open-context work. The production engine deliberately disables
            # this closed-window retention: atlas/section physics is durable;
            # the binding context exists only while the experience is forming.
            self._wal_on_close(record)
        self._log_event("window_closed", **event)
        if return_settlement:
            return window_id, settlement_result
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
        """Return full closed windows referenced by one canonical chi bucket.

        Fetch-on-demand: ids resolve atomically under the lock; content comes
        from the LRU cache or its exact WAL byte range.  Detached copies."""
        with self._lock:
            locations = self._chi_index.get(int(chi), ())
            seen = set()
            window_ids = []
            for location in locations:
                window_id = location["window_id"]
                if window_id in seen:
                    continue
                seen.add(window_id)
                window_ids.append(window_id)
        fetched = self._fetch_many_detached(window_ids)
        windows = []
        for window_id in window_ids:
            record = fetched.get(window_id)
            if record is None:
                raise WindowStoreIntegrityHalt(
                    f"chi index references closed window {window_id!r} but "
                    f"no durable content exists for it. {RESTORE_HINT}")
            windows.append(record)
        return tuple(windows)

    def recall_snapshot(self, chis: list[int]) -> tuple[dict, ...]:
        """Return every full closed window matching any chi, once.

        The id set resolves atomically under the lock; closed records are
        immutable, so fetching content afterwards is equivalent to the old
        in-lock deepcopy.  Detached copies."""
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
        fetched = self._fetch_many_detached(window_ids)
        results = []
        for window_id in window_ids:
            record = fetched.get(window_id)
            if record is None:
                raise WindowStoreIntegrityHalt(
                    f"chi index references closed window {window_id!r} but "
                    f"no durable content exists for it. {RESTORE_HINT}")
            results.append(record)
        return tuple(results)

    def closed_window(self, window_id: str) -> Optional[dict]:
        """Return one detached closed window by its exact durable identity."""
        return self._fetch_window_detached(str(window_id))

    def snapshot(self) -> dict:
        """Return the complete closed/open memory and its independently checked index.

        Legacy/test surface: it MATERIALIZES every closed record (fetched on
        demand from the disk-resident store), so its cost and footprint are
        O(store).  The live save path uses snapshot_incremental() instead."""
        with self._lock:
            windows = {}
            for window_id in self.window_ids():
                record = self._fetch_window_detached(window_id)
                if record is None:
                    raise WindowIntegrityError(
                        f"closed window {window_id!r} vanished during snapshot")
                windows[window_id] = record
            snapshot = {
                "schema": SCHEMA_NAME,
                "version": SCHEMA_VERSION,
                "windows": windows,
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
            # Legacy full-snapshot restore: the supplied records become the
            # PENDING set (readable immediately, resident until the next save
            # folds them into a WAL base segment — the same divergence-driven
            # compaction that always followed a legacy migration).
            self._window_locator.clear()
            self._pending = dict(closed)
            self._window_meta = {
                window_id: self._window_metadata_from_record(record)
                for window_id, record in closed.items()
            }
            self._cache_clear()
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

    def _wal_checkpoint_path(self, generation: int) -> str:
        return os.path.join(
            self._wal_dir,
            f"{WAL_CHECKPOINT_PREFIX}{generation:08d}{WAL_CHECKPOINT_SUFFIX}")

    @staticmethod
    def _parse_checkpoint_name(name: str) -> Optional[int]:
        """Return the generation for a checkpoint filename, else None."""
        if (not name.startswith(WAL_CHECKPOINT_PREFIX)
                or not name.endswith(WAL_CHECKPOINT_SUFFIX)):
            return None
        core = name[len(WAL_CHECKPOINT_PREFIX):-len(WAL_CHECKPOINT_SUFFIX)]
        try:
            return int(core)
        except ValueError:
            return None

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
        """Remove stale segment AND checkpoint files (keep exactly one
        generation, or all strictly below a bound).  Never removes the live
        generation's data."""
        if self._wal_dir is None:
            return
        for name in os.listdir(self._wal_dir):
            parsed = self._parse_segment_name(name)
            gen = parsed[0] if parsed is not None else (
                self._parse_checkpoint_name(name))
            if gen is None:
                continue
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

    def _wal_append_line(self, line: bytes, record_hash: str) -> WindowLocation:
        """Append one durable, fsync'd record line to the active segment.

        Caller must hold ``self._wal_lock``.  Counters/digest advance only
        after the bytes are fsync'd, so the manifest never claims a record
        durable before it truly is.  Returns the record's exact durable
        location for the window locator.
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
            handle.seek(0, os.SEEK_END)
            offset = handle.tell()
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
        return WindowLocation(path, offset, len(line), "window")

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
        compaction -- the record stays in ``_pending`` (readable, resident)
        and the WAL is marked for a fold-into-base by the next save rather
        than silently losing the record.
        """
        with self._wal_lock:
            if not (self._wal_enabled and self._wal_base_written):
                self._wal_base_written = False
                return
            record_hash = _sha256_hex(_canonical_wal_bytes(record))
            line = _canonical_wal_bytes(
                {"record": record, "sha256": record_hash}) + b"\n"
            location = self._wal_append_line(line, record_hash)
            append_generation = self._wal_generation
        # Publish the durable location and release the resident copy.  Lock
        # order stays self._lock -> self._wal_lock everywhere else, so the
        # wal lock is fully released before self._lock is taken here.
        window_id = record["window_id"]
        with self._lock:
            with self._wal_lock:
                current_generation = self._wal_generation
            if current_generation != append_generation:
                # A compaction ran between our append and this publish: it
                # folded the pending copy into the NEW base and rebuilt the
                # locator.  Our old-generation line is a superseded
                # duplicate — publishing its location would point the
                # locator at a file scheduled for deletion.  Discard.
                self._pending.pop(window_id, None)
                return
            self._pending.pop(window_id, None)
            self._window_locator[window_id] = location
        self._cache_put(window_id, record, location.length)

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
                "closed_window_count": self.closed_window_count(),
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

    def _iter_record_lines_locked(self):
        """Yield (window_id, canonical_line_bytes, record_hash, kind, record)
        for every current closed record, one at a time, in durable append
        order.

        Streams disk-resident records straight from their located byte
        ranges (re-verified) and serialises pending records; content never
        materializes wholesale (one record at a time).  Caller holds
        ``self._lock``."""
        for window_id, location in list(self._window_locator.items()):
            with open(location.path, "rb") as handle:
                handle.seek(location.offset)
                raw = handle.read(location.length)
            if len(raw) != location.length:
                raise WindowStoreIntegrityHalt(
                    f"short read compacting {window_id!r} at "
                    f"{os.path.basename(location.path)}+{location.offset}")
            line = raw if raw.endswith(b"\n") else raw + b"\n"
            try:
                record, record_hash = self._verify_wal_line(line.rstrip(b"\n"))
            except (ValueError, KeyError, TypeError,
                    WindowIntegrityError) as exc:
                raise WindowStoreIntegrityHalt(
                    f"record for {window_id!r} failed verification during "
                    f"compaction: {exc}") from exc
            if record.get("window_id") != window_id:
                raise WindowStoreIntegrityHalt(
                    f"located record identity mismatch during compaction: "
                    f"expected {window_id!r}, found {record.get('window_id')!r}")
            kind = ("gist" if record.get(RECORD_KIND_KEY) == RECORD_KIND_GIST
                    else "window")
            yield window_id, line, record_hash, kind, record
        for window_id, record in list(self._pending.items()):
            if window_id in self._window_locator:
                continue
            record_hash = _sha256_hex(_canonical_wal_bytes(record))
            line = _canonical_wal_bytes(
                {"record": record, "sha256": record_hash}) + b"\n"
            yield window_id, line, record_hash, "window", record

    def _compact_locked(self, rewrite_policy: Optional[Callable] = None) -> dict:
        """Write a new base segment holding every current closed window, make
        it durable, then switch the live WAL AND the window locator onto it.
        Caller holds ``_lock``.

        Compaction rewrites segment files, so the locator is rebuilt here
        with each record's new byte range — an in-flight fetch that resolved
        the old locator still succeeds (the previous generation's files are
        kept until the next compaction) and retries against the new locator
        if not.

        ``rewrite_policy`` is the Change-3 seam: a future distill-then-fade
        lane passes a policy mapping ``(window_id, line, record_hash) ->
        (line, record_hash)`` (e.g. replacing a full record with its typed
        gist record).  Default is identity — Change 1 never rewrites content.
        Whatever the policy emits stays one canonical hash-verified line, so
        forgetting is a logged compaction rewrite, never an in-place
        mutation and never a format fork."""
        new_generation = self._wal_generation + 1
        tmp_path = self._wal_segment_path(new_generation, 0) + ".tmp"
        final_path = self._wal_segment_path(new_generation, 0)
        digest = hashlib.sha256()
        raw_digest = hashlib.sha256()  # whole-file bytes -- checkpoint seal,
                                        # completely separate from `digest`
        total_bytes = 0
        record_count = 0
        record_hashes: list[str] = []
        new_locator: dict[str, WindowLocation] = {}
        new_meta: dict[str, dict] = {}
        with open(tmp_path, "wb") as handle:
            for window_id, line, record_hash, kind, record in (
                    self._iter_record_lines_locked()):
                if rewrite_policy is not None:
                    line, record_hash = rewrite_policy(
                        window_id, line, record_hash)
                    # A policy may have rewritten a full record to a typed
                    # gist record (Change 3); re-derive the locator kind AND
                    # the metadata from what was actually written, so the
                    # resident view can never go stale against the rewrite.
                    record, _ = self._verify_wal_line(line.rstrip(b"\n"))
                    kind = ("gist"
                            if record.get(RECORD_KIND_KEY) == RECORD_KIND_GIST
                            else "window")
                offset = total_bytes
                handle.write(line)
                raw_digest.update(line)
                total_bytes += len(line)
                record_count += 1
                new_locator[window_id] = WindowLocation(
                    final_path, offset, len(line), kind)
                meta = self._window_metadata_from_record(record)
                previous_meta = self._window_meta.get(window_id)
                if previous_meta is not None:
                    # Fetch recency is runtime state, not record content —
                    # carry it across the rewrite (fade-policy input).
                    meta["last_fetched_tick"] = previous_meta.get(
                        "last_fetched_tick")
                new_meta[window_id] = meta
                record_hashes.append(record_hash)
                digest.update(record_hash.encode("ascii"))
                digest.update(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_dir(self._wal_dir)
        _atomic_rename_with_retry(tmp_path, final_path)
        _fsync_dir(self._wal_dir)
        # Checkpoint the state this base now represents -- the fast-boot seam
        # (restore_from_wal). Best-effort: a failure here loses only the fast
        # path for THIS generation, never the compaction itself, so it must
        # never raise past this point, and it changes nothing about how
        # ``digest``/``self._wal_digest_hasher`` are computed -- that chain
        # stays the exact, unmodified algorithm it always was (plain,
        # zero-started, one record hash at a time). The checkpoint carries
        # its own copy of those same per-record hashes (``record_hashes``)
        # so a later fast-boot can feed them into a hasher itself and
        # reproduce the IDENTICAL chain without re-parsing/re-validating
        # each full record -- cheap because sha256("64 hex chars") costs
        # nothing like re-verifying a whole JSON record does.
        try:
            self._write_wal_checkpoint_locked(
                generation=new_generation, base_digest=raw_digest.hexdigest(),
                base_bytes=total_bytes, record_count=record_count,
                record_hashes=record_hashes,
                locator=new_locator, window_meta=new_meta)
        except Exception as checkpoint_error:
            self._log_event(
                "window_wal_checkpoint_write_failed",
                generation=new_generation, error=str(checkpoint_error))
        with self._wal_lock:
            prev_generation = self._wal_generation
            self._wal_generation = new_generation
            # Force the NEXT append onto a fresh segment (index 1), never
            # back into segment 0 (the base). Before this, a small compact
            # left segment 0 under WAL_SEGMENT_MAX_RECORDS/BYTES, so new
            # closes kept appending INTO the base file itself -- its bytes
            # on disk no longer matched what was just checkpointed, so the
            # fast-boot digest check (restore_from_wal) would mismatch and
            # silently fall back on literally every boot after any activity,
            # making the checkpoint dead weight. Sealing the base the moment
            # it's written (same "start fresh, treat as empty" pattern
            # restore_from_wal already uses for its own post-restore
            # segment) is what makes segment 0 a true, stable base.
            self._wal_segment_index = 1
            self._wal_segment_records = 0
            self._wal_segment_bytes = 0
            self._wal_record_count = record_count
            self._wal_digest_hasher = digest
            self._wal_base_written = True
        # Install the rebuilt locator AND metadata; pending records are now
        # durable.  The content cache is cleared: under a rewrite_policy the
        # cached full records may no longer match what the store holds, and
        # a stale cache would silently serve pre-rewrite content forever.
        self._window_locator = new_locator
        self._window_meta = new_meta
        self._pending.clear()
        self._cache_clear()
        # Older generations are now fully superseded by this base and safe to
        # drop.  The PREVIOUS generation is kept until the caller's manifest
        # (pointing here) is durable; the next compaction / a boot restore
        # removes it -- so a crash mid-compaction can always fall back to the
        # last committed generation.
        self._delete_wal_generations(below=prev_generation)
        self._log_event(
            "window_wal_compacted", generation=new_generation,
            records=record_count, bytes=total_bytes)
        return {"generation": new_generation, "records": record_count,
                "path": final_path, "bytes": total_bytes}

    def _write_wal_checkpoint_locked(
            self, *, generation: int, base_digest: str, base_bytes: int,
            record_count: int, record_hashes: list[str],
            locator: dict[str, WindowLocation],
            window_meta: dict[str, dict]) -> None:
        """Durably write the fast-boot checkpoint for a just-written base
        segment.  Caller holds ``_lock`` (and is mid-``_compact_locked``,
        so ``self._chi_index``/``self._chi_index_seen`` are read directly
        here -- both are kept in lockstep with every closed window AT
        CLOSE TIME, pending or durable (see ``_index_closed_window``), so
        they already reflect exactly what ``locator``/``window_meta`` just
        folded in.

        Raises on any failure; the caller treats that as "no fast path
        for this generation" and continues -- never as a compaction
        failure.

        Two deliberate space/parse-cost cuts (profiled 2026-07-20: JSON
        parsing this file was the single biggest cost in the fast path,
        bigger than the whole-file digest hash): ``chi_index_seen`` is NOT
        stored -- it is a pure dedup helper, fully re-derivable from
        ``chi_index`` alone in one cheap pass at load time, so storing it
        separately only doubled that structure's bytes for free. Per-entry
        chi_index dicts (``{"window_id":..,"entry_index":..}``) are stored
        as plain ``[window_id, entry_index]`` pairs -- same information,
        without repeating both key names on every single entry. And
        ``record_hashes`` is one concatenated 64-char-per-hash string, not
        a JSON array of N separate string objects -- parsing one long
        string is far cheaper than constructing N of them."""
        locator_payload = {
            window_id: [loc.offset, loc.length, loc.kind]
            for window_id, loc in locator.items()
        }
        chi_index_payload = {
            str(chi): [[e["window_id"], e["entry_index"]] for e in entries]
            for chi, entries in self._chi_index.items()
        }
        checkpoint = {
            "format": CHECKPOINT_FORMAT,
            "schema": SCHEMA_NAME,
            "version": SCHEMA_VERSION,
            "generation": generation,
            "base_digest": base_digest,
            "base_bytes": base_bytes,
            "record_count": record_count,
            "record_hashes_blob": "".join(record_hashes),
            "window_meta": window_meta,
            "locator": locator_payload,
            "chi_index": chi_index_payload,
            "window_sequence": self._window_sequence,
            "context_sequence": self._context_sequence,
        }
        payload = json.dumps(
            checkpoint, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False).encode("ascii")
        final_path = self._wal_checkpoint_path(generation)
        tmp_path = final_path + ".tmp"
        with open(tmp_path, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_dir(self._wal_dir)
        _atomic_rename_with_retry(tmp_path, final_path)
        _fsync_dir(self._wal_dir)

    def _read_wal_checkpoint(self, generation: int) -> Optional[dict]:
        """Load and structurally validate the checkpoint for ``generation``.

        Returns None for anything short of a well-formed checkpoint --
        missing file, bad JSON, wrong format/schema/generation, or a
        malformed field.  Never raises: every caller treats "no usable
        checkpoint" as "fall back to full replay", so a checkpoint-reader
        bug can only cost speed, never correctness."""
        path = self._wal_checkpoint_path(generation)
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
            data = json.loads(raw)
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        if (data.get("format") != CHECKPOINT_FORMAT
                or data.get("schema") != SCHEMA_NAME
                or data.get("version") != SCHEMA_VERSION
                or data.get("generation") != generation):
            return None
        required = ("base_digest", "base_bytes", "record_count",
                    "record_hashes_blob", "window_meta", "locator",
                    "chi_index", "window_sequence", "context_sequence")
        if not all(key in data for key in required):
            return None
        record_count = data["record_count"]
        blob = data["record_hashes_blob"]
        if (not isinstance(data["base_digest"], str)
                or not isinstance(data["locator"], dict)
                or not isinstance(data["window_meta"], dict)
                or not isinstance(data["chi_index"], dict)
                or not isinstance(record_count, int)
                or not isinstance(blob, str)
                or len(blob) != 64 * record_count):
            return None
        return data

    def _verified_checkpoint_for_generation(
            self, generation: int, segments: list[tuple[int, str]]
    ) -> tuple[Optional[dict], Optional[str]]:
        """Shared by restore_from_wal's fast path and bootstrap_minimal_
        from_checkpoint: find generation's checkpoint, confirm segment 0
        is really its base (index 0, present), and confirm a fresh
        whole-file hash of that base's ACTUAL bytes on disk right now
        matches what the checkpoint sealed at compaction time.

        Returns (checkpoint, base_path) only when every check passes;
        (None, None) otherwise -- callers treat that uniformly as "no
        fast path available for this generation", never an error."""
        if not segments or segments[0][0] != 0:
            return None, None
        checkpoint = self._read_wal_checkpoint(generation)
        if checkpoint is None:
            return None, None
        base_path = segments[0][1]
        try:
            if os.path.getsize(base_path) != checkpoint["base_bytes"]:
                return None, None
            base_hasher = hashlib.sha256()
            with open(base_path, "rb") as handle:
                for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                    base_hasher.update(chunk)
            if base_hasher.hexdigest() != checkpoint["base_digest"]:
                return None, None
        except OSError:
            return None, None
        return checkpoint, base_path

    @classmethod
    def _verify_wal_line(cls, raw: bytes) -> tuple[dict, str]:
        """Parse+verify one WAL line, returning (record, record_hash).

        Hash verification is LINE-level, so it holds for every record kind
        the WAL will ever carry; structural validation then dispatches on
        the record kind (full window today; typed gist records — Change-3
        distill-then-fade — are tolerated, never a verification crash).
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
        if record.get(RECORD_KIND_KEY) == RECORD_KIND_GIST:
            cls._validate_gist_record(record)
        else:
            cls._validate_window_record(record, closed=True)
        return record, stored_hash

    @staticmethod
    def _validate_gist_record(record: Mapping[str, Any]) -> None:
        """Minimal structural validation for a distilled (content-released)
        window record.  The full gist semantics ship with Change 3; the read
        side accepts the typed shape from day one."""
        if not record.get("window_id"):
            raise WindowIntegrityError("gist record lacks a window_id")
        if record.get("content_released") is not True:
            raise WindowIntegrityError(
                f"gist record {record.get('window_id')!r} must declare "
                f"content_released=true")
        if not isinstance(record.get("gist"), Mapping):
            raise WindowIntegrityError(
                f"gist record {record.get('window_id')!r} lacks a gist object")

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

    def restore_from_wal(self, manifest: Mapping[str, Any], wal_dir: str,
                          *, populate_chi_index: bool = True) -> None:
        """Boot index scan: ONE streaming pass over the WAL segments of the
        manifest's generation, verifying every record hash, and atomically
        install the reconstructed indexes.

        What the pass builds (all small, all resident): the chi index + its
        O(1) dedup sets, the window LOCATOR (window_id -> exact segment byte
        range), and per-window METADATA (close reason, origin, modality
        summary, word list, affect at close).  Window CONTENT never
        materializes here — each record is parsed, verified, indexed, and
        discarded, so boot RSS does not scale with lifetime experience (P1).

        Records the manifest counted as durable are digest-verified as a
        matched prefix; any records appended after the last manifest but before
        a crash are individually hash-verified and recovered (less loss than
        the old full-save-only model).  A torn/incomplete trailing record (only
        ever possible as the very last line) is discarded, never accepted.
        Any other verification failure is a NAMED loud halt
        (WindowStoreIntegrityHalt) — never recover-and-continue (P4).

        ``populate_chi_index=False`` (GL-FIX-BOOT-READY-DECOUPLE-20260720):
        skip building chi_index/chi_index_seen (installed empty instead).
        Confirmed by tracing every real caller in the codebase: chi_index's
        ONLY consumer is give_experience's occasional cross-modal bundle
        recall (recall_snapshot/lookup_chi) — real conversation composes
        entirely from the organism/atlas and never reads it (a standing
        "one mind, one mouth" architectural ruling already in place). Real
        cognition needs locator+meta (feeds language-fact-memory) but never
        chi_index, so it is the one piece of "materialize her whole history"
        boot cost with zero benefit to anything on the critical path. This
        does NOT skip verification of the records themselves (every hash
        still checked, exactly as always) — only the chi-bucket bookkeeping
        those already-verified records would otherwise also feed. Caller
        (bootstrap_minimal_then_background) is responsible for later
        running a full restore_from_wal to backfill the real index.
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
        locator: dict[str, WindowLocation] = {}
        window_meta: dict[str, dict] = {}
        chi_index: dict[int, list[dict]] = {}
        chi_seen: dict[int, set] = {}
        record_count = 0
        torn_discarded = 0
        torn_truncation: Optional[tuple[str, int]] = None
        max_window_seq = -1
        max_context_seq = -1
        checkpoint_window_sequence = 0
        checkpoint_context_sequence = 0
        verify_prefix = hashlib.sha256()   # first durable_count record hashes
        rolling = hashlib.sha256()         # every valid record hash
        replay_start = 0

        # ── Fast path: trust a compaction checkpoint, replay only the delta
        # appended since (GL-FIX-WAL-BOOT-CHECKPOINT-20260720). Engaged only
        # when a checkpoint for THIS generation exists, is well-formed, and
        # its base_digest matches a fresh whole-file hash of segment 0's
        # actual bytes on disk right now -- proof the base has not changed
        # since compaction verified every record in it. The digest CHAIN
        # algorithm itself never changes: the checkpoint carries the base's
        # own per-record hashes (in original order), and the fast path
        # feeds those into verify_prefix/rolling exactly as the real loop
        # below would -- cheap (no JSON parse, no record validation, just
        # hashing short hex strings) but bit-for-bit the same chain a full
        # replay produces. ANY miss below falls through to the untouched
        # full replay, starting at segment 0 exactly as before this change
        # existed -- this can only make boot faster, never less safe.
        checkpoint, base_path = self._verified_checkpoint_for_generation(
            generation, segments)
        if checkpoint is not None:
            try:
                fast_locator = {
                    window_id: WindowLocation(
                        base_path, loc[0], loc[1], loc[2])
                    for window_id, loc in checkpoint["locator"].items()
                }
                # JSON has no tuple type -- _window_metadata_from_
                # record's "modalities" is a tuple in every OTHER
                # code path (fresh compute, legacy snapshot()), so
                # restore it here too rather than silently handing
                # back a list where every other caller expects a
                # tuple.
                fast_meta = {
                    window_id: {
                        **meta,
                        "modalities": tuple(meta.get("modalities") or ()),
                    }
                    for window_id, meta in
                    checkpoint["window_meta"].items()
                }
                # chi_index pairs -> the {"window_id":..,
                # "entry_index":..} dict shape every OTHER writer
                # of this structure uses; chi_index_seen is not
                # stored at all (redundant with chi_index) so it is
                # rebuilt here in the same pass, at no extra cost.
                # Skipped entirely when populate_chi_index=False (the
                # confirmed-unused-by-real-cognition boot-ready-decouple
                # path) -- installed empty, no reason to even parse it.
                fast_chi_index: dict[int, list[dict]] = {}
                fast_chi_seen: dict[int, set] = {}
                if populate_chi_index:
                    for chi, pairs in checkpoint["chi_index"].items():
                        chi_int = int(chi)
                        entries = [
                            {"window_id": wid, "entry_index": idx}
                            for wid, idx in pairs
                        ]
                        fast_chi_index[chi_int] = entries
                        fast_chi_seen[chi_int] = {
                            (wid, idx) for wid, idx in pairs}
                blob = checkpoint["record_hashes_blob"]
                fast_record_hashes = [
                    blob[i:i + 64] for i in range(0, len(blob), 64)]
                fast_window_sequence = int(checkpoint["window_sequence"])
                fast_context_sequence = int(checkpoint["context_sequence"])
            except Exception:
                # Any malformed checkpoint field, however unlikely
                # (disk corruption, a future writer bug): this whole
                # block is a pure optimization, so anything going
                # wrong here must degrade to the full replay below,
                # never propagate past this point.
                pass
            else:
                locator = fast_locator
                window_meta = fast_meta
                chi_index = fast_chi_index
                chi_seen = fast_chi_seen
                checkpoint_window_sequence = fast_window_sequence
                checkpoint_context_sequence = fast_context_sequence
                # Replay the base's own per-record hashes through
                # the SAME accounting the real loop below uses --
                # identical verify_prefix/rolling/record_count
                # bookkeeping, just skipping the expensive parse.
                for record_hash in fast_record_hashes:
                    if record_count < durable_count:
                        verify_prefix.update(record_hash.encode("ascii"))
                        verify_prefix.update(b"\n")
                    rolling.update(record_hash.encode("ascii"))
                    rolling.update(b"\n")
                    record_count += 1
                replay_start = 1
        self._log_event(
            "window_wal_restore_fast_path",
            generation=generation, engaged=(replay_start == 1),
            segments_total=len(segments),
            segments_replayed=max(0, len(segments) - replay_start))

        for seg_pos in range(replay_start, len(segments)):
            _, path = segments[seg_pos]
            is_last_segment = seg_pos == len(segments) - 1
            segment_size = os.path.getsize(path)
            with open(path, "rb") as handle:
                offset = 0
                line_pos = 0
                while True:
                    raw = handle.readline()
                    if not raw:
                        break
                    line_length = len(raw)
                    has_newline = raw.endswith(b"\n")
                    line = raw[:-1] if has_newline else raw
                    is_trailing_partial = (
                        is_last_segment
                        and not has_newline
                        and offset + line_length >= segment_size)
                    if line == b"":
                        # Blank line: only tolerable as a torn trailing artifact.
                        if is_trailing_partial:
                            torn_discarded += 1
                            torn_truncation = (path, offset)
                            offset += line_length
                            line_pos += 1
                            continue
                        raise WindowStoreIntegrityHalt(
                            f"WAL segment {os.path.basename(path)} has an empty "
                            f"interior record at line {line_pos}. {RESTORE_HINT}")
                    try:
                        record, record_hash = self._verify_wal_line(line)
                    except (ValueError, KeyError, TypeError,
                            json.JSONDecodeError, WindowIntegrityError) as exc:
                        if is_trailing_partial:
                            torn_discarded += 1
                            torn_truncation = (path, offset)
                            offset += line_length
                            line_pos += 1
                            continue
                        raise WindowStoreIntegrityHalt(
                            f"WAL segment {os.path.basename(path)} line {line_pos} "
                            f"is corrupt and is not the trailing record: {exc}. "
                            f"{RESTORE_HINT}")
                    # ── Index this record, then DISCARD its content ──
                    window_id = record["window_id"]
                    kind = ("gist"
                            if record.get(RECORD_KIND_KEY) == RECORD_KIND_GIST
                            else "window")
                    locator[window_id] = WindowLocation(
                        path, offset, line_length, kind)
                    window_meta[window_id] = (
                        self._window_metadata_from_record(record))
                    max_window_seq = max(
                        max_window_seq, self._parse_window_sequence(window_id))
                    max_context_seq = max(
                        max_context_seq,
                        self._parse_context_sequence(record.get("context_id")))
                    if populate_chi_index:
                        for entry in record.get("entries") or []:
                            chi = int(entry["chi"])
                            entry_index = int(entry["entry_index"])
                            seen = chi_seen.setdefault(chi, set())
                            key = (window_id, entry_index)
                            if key in seen:
                                continue
                            seen.add(key)
                            chi_index.setdefault(chi, []).append(
                                {"window_id": window_id,
                                 "entry_index": entry_index})
                    if record_count < durable_count:
                        verify_prefix.update(record_hash.encode("ascii"))
                        verify_prefix.update(b"\n")
                    rolling.update(record_hash.encode("ascii"))
                    rolling.update(b"\n")
                    record_count += 1
                    offset += line_length
                    line_pos += 1

        if record_count < durable_count:
            raise WindowStoreIntegrityHalt(
                f"WAL generation {generation} holds {record_count} valid "
                f"records, fewer than the {durable_count} the manifest marks "
                f"durable -- committed data is missing. {RESTORE_HINT}")
        if verify_prefix.hexdigest() != expected_digest:
            raise WindowStoreIntegrityHalt(
                f"WAL durable prefix digest does not match the manifest. "
                f"{RESTORE_HINT}")

        # ── Torn-tail SELF-HEAL (review blocker 1, 2026-07-16) ──
        # Discarding a torn trailing record is not enough: the torn bytes
        # stay on disk, new closes open a FRESH segment, and the NEXT boot
        # then finds the torn line in an INTERIOR segment — a permanent
        # named halt for what was one crash mid-append.  The torn record was
        # never counted durable (counters/digest advance only after fsync),
        # so truncating it back off changes nothing the manifest attests to.
        # Loud by design: window_wal_torn_truncated names segment and bytes.
        if torn_truncation is not None:
            torn_path, torn_offset = torn_truncation
            torn_size = os.path.getsize(torn_path)
            fd = os.open(torn_path, os.O_RDWR)
            try:
                os.ftruncate(fd, torn_offset)
                os.fsync(fd)
            finally:
                os.close(fd)
            self._log_event(
                "window_wal_torn_truncated",
                segment=os.path.basename(torn_path),
                truncated_at=torn_offset,
                bytes_removed=torn_size - torn_offset)

        # Open contexts from the manifest; a context whose window already
        # appears closed in the WAL (a close that raced the manifest read) is
        # superseded by the closed record and dropped from the open set.
        open_contexts: dict[str, BindingWindow] = {}
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
            if window.window_id in locator:
                continue
            open_contexts[context_id] = window

        next_window_sequence = max(
            int(manifest["next_window_sequence"]),
            len(locator),
            max_window_seq + 1,
            checkpoint_window_sequence)
        next_context_sequence = max(
            int(manifest["next_context_sequence"]),
            max_context_seq + 1,
            checkpoint_context_sequence)

        last_index = segments[-1][0] if segments else -1

        with self._lock:
            self._window_locator = locator
            self._window_meta = window_meta
            self._pending = {}
            self._cache_clear()
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
                self._wal_record_count = record_count
                self._wal_digest_hasher = rolling
                self._wal_base_written = True
        # Drop any non-current generation (older superseded, or an orphan base
        # from a compaction that crashed before its manifest committed).
        self._delete_wal_generations(keep=generation)
        self._log_event(
            "window_state_restored_wal",
            windows=len(locator), open_contexts=len(open_contexts),
            chi_buckets=len(chi_index), durable_count=durable_count,
            recovered=record_count - durable_count,
            torn_discarded=torn_discarded, generation=generation)

    def restore_persisted(self, data: Mapping[str, Any], state_dir: str,
                           *, populate_chi_index: bool = True) -> None:
        """Restore window state from either a WAL manifest (new format) or a
        legacy full snapshot, configuring the WAL either way.

        ``populate_chi_index=False`` forwards to restore_from_wal (see its
        own docstring, GL-FIX-CHI-INDEX-ELIMINATION-20260720) -- the real
        boot path passes this, since chi routing now lives on the atlas,
        not a second copy here."""
        wal_dir = os.path.join(state_dir, WAL_DIRNAME)
        self.configure_wal(wal_dir)
        if isinstance(data, Mapping) and data.get("format") == MANIFEST_FORMAT:
            self.restore_from_wal(
                data, wal_dir, populate_chi_index=populate_chi_index)
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
