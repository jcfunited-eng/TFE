"""Bounded transient physical causal-experience transactions.

One context owns physical full-field entries until its caller closes it.
Closing invokes exactly one atomic settlement callback.  A successful
settlement releases the complete context immediately; a failed settlement
leaves the sealed context available only for an explicit retry or discard.

There is deliberately no Atlas mirror, semantic section/motif/chi identity,
closed-window store, lookup/recall index, cache, WAL, snapshot, restore, or
persistence surface in this owner.
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
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Mapping, Optional


WINDOW_TOTAL_OPEN_MB_ENV = "GUALA_WINDOW_STORE_MB"
WINDOW_TOTAL_OPEN_DEFAULT_MB = 128
WINDOW_CONTEXT_MB_ENV = "GUALA_WINDOW_MAX_RECORD_MB"
WINDOW_CONTEXT_DEFAULT_MB = 64

_TOPOLOGY_FIELDS = (
    "sense",
    "sensor_id",
    "substream_id",
    "topology_index",
    "coordinates",
    "physical_quantity",
    "physical_unit",
)


class _OwnedJsonDict(dict):
    """Deeply owned JSON object; mutation is never a lawful transition."""

    def _immutable(self, *_args, **_kwargs):
        raise TypeError("owned physical evidence is immutable")

    __delitem__ = _immutable
    __setitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable

    def __deepcopy__(self, _memo):
        return self


class _OwnedJsonList(list):
    """Deeply owned JSON array; mutation is never a lawful transition."""

    def _immutable(self, *_args, **_kwargs):
        raise TypeError("owned physical evidence is immutable")

    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    __setitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable

    def __deepcopy__(self, _memo):
        return self


def _positive_mebibyte_budget(env_name: str, default_mb: int) -> int:
    raw = os.environ.get(env_name)
    if raw is None:
        return default_mb * 1024 * 1024
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(
            f"{env_name} must be an integer MiB value"
        ) from error
    if value <= 0:
        raise ValueError(f"{env_name} must be greater than zero")
    return value * 1024 * 1024


def _json_safe(value: Any, path: str = "value") -> Any:
    """Return deeply immutable deterministic JSON physical evidence."""
    if isinstance(value, (_OwnedJsonDict, _OwnedJsonList)):
        return value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, complex):
        return _OwnedJsonDict({
            "real": _json_safe(value.real, f"{path}.real"),
            "imag": _json_safe(value.imag, f"{path}.imag"),
        })
    if isinstance(value, bytes):
        return _OwnedJsonDict({
            "encoding": "base64",
            "data": base64.b64encode(value).decode("ascii"),
        })
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if is_dataclass(value):
        return _json_safe(asdict(value), path)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            safe_key = key if isinstance(key, str) else str(key)
            if safe_key in result:
                raise ValueError(
                    f"{path} has colliding JSON object key {safe_key!r}"
                )
            result[safe_key] = _json_safe(
                item,
                f"{path}.{safe_key}",
            )
        return _OwnedJsonDict(result)
    if isinstance(value, (list, tuple)):
        return _OwnedJsonList([
            _json_safe(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ])
    if isinstance(value, (set, frozenset)):
        converted = [
            _json_safe(item, f"{path}[]")
            for item in value
        ]
        return _OwnedJsonList(sorted(
            converted,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ))
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
    raise TypeError(
        f"{path} contains unsupported non-JSON value "
        f"{type(value).__name__}"
    )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _physical_topology_fact_from_safe(safe: Any) -> Any:
    """Project topology from an already-owned JSON-safe field."""
    if isinstance(safe, dict):
        records = [safe]
        batch = False
    elif isinstance(safe, list) and safe:
        records = safe
        batch = True
    else:
        raise TypeError(
            "physical full_field must be one record or a non-empty record list"
        )
    topology = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"physical full_field[{index}] is not a record"
            )
        missing = [
            name for name in _TOPOLOGY_FIELDS
            if name not in record
        ]
        if missing:
            raise ValueError(
                "physical full-field record lacks topology facts: "
                f"{missing}"
            )
        topology.append(_OwnedJsonDict({
            name: record[name] for name in _TOPOLOGY_FIELDS
        }))
    owned = _OwnedJsonList(topology)
    return owned if batch else owned[0]


def physical_topology_fact(full_field: Any) -> Any:
    """Project only explicit sensor topology from native full-field records."""
    return _physical_topology_fact_from_safe(
        _json_safe(full_field, "entry.full_field")
    )


class WindowIntegrityError(ValueError):
    """The transient physical transaction changed shape or authority."""


class WindowCapacityRefusal(WindowIntegrityError):
    """A per-context or aggregate hard byte boundary refused mutation."""

    def __init__(
        self,
        *,
        scope: str,
        current_bytes: int,
        attempted_bytes: int,
        budget_bytes: int,
    ):
        self.scope = str(scope)
        self.current_bytes = int(current_bytes)
        self.attempted_bytes = int(attempted_bytes)
        self.budget_bytes = int(budget_bytes)
        super().__init__(
            f"{self.scope} capacity refused: attempted "
            f"{self.attempted_bytes} canonical bytes with "
            f"{self.current_bytes} already owned; budget is "
            f"{self.budget_bytes} bytes"
        )


@dataclass(slots=True)
class WindowEntry:
    """One admitted physical full-field fact."""

    modality: str
    tick: int
    source_tag: str
    topology: Any
    full_field: Any
    detail: dict = field(default_factory=dict)

    def record(self, entry_index: int) -> dict:
        return {
            "entry_index": int(entry_index),
            "modality": self.modality,
            "tick": self.tick,
            "source_tag": self.source_tag,
            "topology": self.topology,
            "full_field": self.full_field,
            "detail": self.detail,
        }


@dataclass(slots=True)
class BindingWindow:
    """One caller-owned physical transaction."""

    window_id: str
    context_id: str
    context_origin: str
    opened_tick: int
    trigger_reason: str
    context_detail: dict
    entries: list[WindowEntry] = field(default_factory=list)
    closed_tick: Optional[int] = None
    close_reason: Optional[str] = None
    _settlement_in_progress: bool = False
    _mutation_revision: int = 0
    _settlement_custodies: list[object] = field(default_factory=list)

    def record(self) -> dict:
        return {
            "window_id": self.window_id,
            "context_id": self.context_id,
            "context_origin": self.context_origin,
            "opened_tick": self.opened_tick,
            "closed_tick": self.closed_tick,
            "trigger_reason": self.trigger_reason,
            "close_reason": self.close_reason,
            "context_detail": self.context_detail,
            "entries": [
                entry.record(index)
                for index, entry in enumerate(self.entries)
            ],
        }

    def add_entry(self, entry: WindowEntry) -> int:
        if (
            self.closed_tick is not None
            or self._settlement_in_progress
        ):
            raise WindowIntegrityError(
                "cannot mutate a closing or closed physical window"
            )
        self.entries.append(entry)
        self._mutation_revision += 1
        return len(self.entries) - 1


@dataclass(frozen=True, slots=True)
class EmptyWindowTransactionSnapshot:
    """Exact scalar state at a boundary with no open physical context."""

    window_sequence: int
    context_sequence: int
    capacity_refusal_count: int
    last_capacity_refusal: Optional[dict[str, Any]]


class WindowManager:
    """Fail-closed owner of bounded transient physical transactions."""

    def __init__(
        self,
        *,
        log_event_fn: Callable[..., Any],
        get_tick_fn: Callable[[], int],
        settle_window_fn: Optional[
            Callable[[Mapping[str, Any]], Any]
        ] = None,
        max_total_open_bytes: Optional[int] = None,
        max_context_bytes: Optional[int] = None,
    ):
        self._log_event = log_event_fn
        self._get_tick = get_tick_fn
        self._settle_window = settle_window_fn
        self._max_total_open_bytes = (
            _positive_mebibyte_budget(
                WINDOW_TOTAL_OPEN_MB_ENV,
                WINDOW_TOTAL_OPEN_DEFAULT_MB,
            )
            if max_total_open_bytes is None
            else int(max_total_open_bytes)
        )
        self._max_context_bytes = (
            _positive_mebibyte_budget(
                WINDOW_CONTEXT_MB_ENV,
                WINDOW_CONTEXT_DEFAULT_MB,
            )
            if max_context_bytes is None
            else int(max_context_bytes)
        )
        if (
            self._max_total_open_bytes <= 0
            or self._max_context_bytes <= 0
        ):
            raise ValueError(
                "physical window byte budgets must be greater than zero"
            )
        self._lock = threading.RLock()
        self._bound_context = contextvars.ContextVar(
            f"physical_window_context_{id(self)}",
            default=None,
        )
        self._contexts: dict[str, BindingWindow] = {}
        self._open_context_bytes: dict[str, int] = {}
        self._open_context_total_bytes = 0
        self._window_sequence = 0
        self._context_sequence = 0
        self._capacity_refusal_count = 0
        self._last_capacity_refusal = None

    @property
    def current(self) -> Optional[BindingWindow]:
        context_id = self._bound_context.get()
        with self._lock:
            return (
                self._contexts.get(context_id)
                if context_id is not None
                else None
            )

    @property
    def active_context_id(self) -> Optional[str]:
        context_id = self._bound_context.get()
        with self._lock:
            return (
                context_id
                if context_id in self._contexts
                else None
            )

    def _refuse_capacity(
        self,
        *,
        scope: str,
        current_bytes: int,
        attempted_bytes: int,
        budget_bytes: int,
    ) -> None:
        refusal = WindowCapacityRefusal(
            scope=scope,
            current_bytes=current_bytes,
            attempted_bytes=attempted_bytes,
            budget_bytes=budget_bytes,
        )
        self._capacity_refusal_count += 1
        self._last_capacity_refusal = {
            "scope": refusal.scope,
            "current_bytes": refusal.current_bytes,
            "attempted_bytes": refusal.attempted_bytes,
            "budget_bytes": refusal.budget_bytes,
        }
        self._log_event(
            "window_capacity_refused",
            **self._last_capacity_refusal,
        )
        raise refusal

    def _new_window(
        self,
        context_id: str,
        trigger_reason: str,
        context_origin: str,
        context_detail: Optional[Mapping[str, Any]],
    ) -> BindingWindow:
        tick = int(self._get_tick())
        sequence = self._window_sequence
        self._window_sequence += 1
        identity = hashlib.sha256(
            (
                f"{sequence}|{context_id}|{tick}|"
                f"{trigger_reason}"
            ).encode("utf-8")
        ).hexdigest()[:16]
        return BindingWindow(
            window_id=f"win_{sequence:016x}_{identity}",
            context_id=context_id,
            context_origin=context_origin,
            opened_tick=tick,
            trigger_reason=str(trigger_reason),
            context_detail=_json_safe(
                context_detail or {},
                "window.context_detail",
            ),
        )

    def begin_context(
        self,
        context_id: str,
        trigger_reason: str = "input",
        *,
        context_detail: Optional[Mapping[str, Any]] = None,
        _origin: str = "explicit",
    ) -> str:
        """Begin or reactivate exactly one caller-owned context."""
        if not isinstance(context_id, str) or not context_id.strip():
            raise ValueError("context_id must be a non-empty string")
        context_id = context_id.strip()
        opened = False
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                window = self._new_window(
                    context_id,
                    trigger_reason,
                    _origin,
                    context_detail,
                )
                initial_bytes = len(_canonical_bytes(window.record()))
                if initial_bytes > self._max_context_bytes:
                    self._refuse_capacity(
                        scope="new_open_context",
                        current_bytes=0,
                        attempted_bytes=initial_bytes,
                        budget_bytes=self._max_context_bytes,
                    )
                attempted_total = (
                    self._open_context_total_bytes + initial_bytes
                )
                if attempted_total > self._max_total_open_bytes:
                    self._refuse_capacity(
                        scope="aggregate_open_contexts",
                        current_bytes=self._open_context_total_bytes,
                        attempted_bytes=attempted_total,
                        budget_bytes=self._max_total_open_bytes,
                    )
                self._contexts[context_id] = window
                self._open_context_bytes[context_id] = initial_bytes
                self._open_context_total_bytes = attempted_total
                opened = True
            self._bound_context.set(context_id)
            window_id = window.window_id
            event = {
                "window_id": window.window_id,
                "context_id": context_id,
                "tick": window.opened_tick,
                "operational_wall_clock": time.time(),
                "trigger_reason": window.trigger_reason,
            }
        if opened:
            self._log_event("window_opened", **event)
        return window_id

    def activate_context(self, context_id: str) -> str:
        """Bind an already-open context to this caller."""
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                raise KeyError(
                    f"unknown open physical context {context_id!r}"
                )
            self._bound_context.set(context_id)
            return window.window_id

    def _next_context_id(self) -> str:
        with self._lock:
            sequence = self._context_sequence
            self._context_sequence += 1
        return f"physical:{sequence:016x}"

    def open(
        self,
        trigger_reason: str,
        context_id: Optional[str] = None,
        **context_detail: Any,
    ) -> str:
        """Open a physical context, preserving an existing caller binding."""
        bound = self._bound_context.get()
        with self._lock:
            if context_id is None and bound in self._contexts:
                return self._contexts[bound].window_id
        return self.begin_context(
            context_id or self._next_context_id(),
            trigger_reason,
            context_detail=context_detail,
            _origin="open",
        )

    @contextmanager
    def binding_context(
        self,
        context_id: str,
        trigger_reason: str = "input",
        *,
        close_reason: str = "context_complete",
        failure_reason: str = "context_failed",
        context_detail: Optional[Mapping[str, Any]] = None,
    ):
        token = self._bound_context.set(context_id)
        completed = False
        try:
            window_id = self.begin_context(
                context_id,
                trigger_reason,
                context_detail=context_detail,
            )
            yield window_id
            completed = True
        finally:
            self.end_context(
                context_id,
                close_reason if completed else failure_reason,
            )
            self._bound_context.reset(token)

    def add_entry(
        self,
        *,
        modality: str,
        topology: Any,
        full_field: Any,
        tick: Optional[int] = None,
        source_tag: str = "",
        context_id: Optional[str] = None,
        detail: Optional[Mapping[str, Any]] = None,
    ) -> int:
        """Admit one explicit topology plus its complete physical field."""
        modality = str(modality).strip()
        if not modality:
            raise ValueError("physical entry modality must be non-empty")
        safe_full_field = _json_safe(
            full_field,
            "entry.full_field",
        )
        expected_topology = _physical_topology_fact_from_safe(
            safe_full_field
        )
        safe_topology = _json_safe(
            topology,
            "entry.topology",
        )
        if safe_topology != expected_topology:
            raise WindowIntegrityError(
                "physical entry topology differs from its full field"
            )
        records = (
            [safe_full_field]
            if isinstance(safe_full_field, dict)
            else safe_full_field
        )
        if any(record.get("sense") != modality for record in records):
            raise WindowIntegrityError(
                "physical entry modality differs from its full field"
            )
        safe_detail = _json_safe(
            detail or {},
            "entry.detail",
        )
        actual_tick = int(
            self._get_tick() if tick is None else tick
        )
        target_context = (
            context_id
            if context_id is not None
            else self._bound_context.get()
        )
        if not isinstance(target_context, str) or not target_context:
            raise WindowIntegrityError(
                "physical entry has no caller-owned open context"
            )

        with self._lock:
            window = self._contexts.get(target_context)
            if window is None:
                raise KeyError(
                    f"unknown open physical context {target_context!r}"
                )
            entry = WindowEntry(
                modality=modality,
                tick=actual_tick,
                source_tag=str(source_tag or ""),
                topology=safe_topology,
                full_field=safe_full_field,
                detail=safe_detail,
            )
            entry_index = len(window.entries)
            entry_bytes = len(_canonical_bytes(
                entry.record(entry_index)
            ))
            current_bytes = self._open_context_bytes[target_context]
            proposed_bytes = (
                current_bytes
                + entry_bytes
                + int(bool(window.entries))
            )
            attempted_total = (
                self._open_context_total_bytes
                - current_bytes
                + proposed_bytes
            )
            if proposed_bytes > self._max_context_bytes:
                self._refuse_capacity(
                    scope="open_context",
                    current_bytes=current_bytes,
                    attempted_bytes=proposed_bytes,
                    budget_bytes=self._max_context_bytes,
                )
            if attempted_total > self._max_total_open_bytes:
                self._refuse_capacity(
                    scope="aggregate_open_contexts",
                    current_bytes=self._open_context_total_bytes,
                    attempted_bytes=attempted_total,
                    budget_bytes=self._max_total_open_bytes,
                )
            index = window.add_entry(entry)
            self._open_context_bytes[target_context] = proposed_bytes
            self._open_context_total_bytes = attempted_total
            event = {
                "window_id": window.window_id,
                "context_id": target_context,
                "modality": modality,
                "entry_index": index,
                "topology": copy.deepcopy(safe_topology),
            }
        self._log_event("window_entry_added", **event)
        return index

    def bind_settlement_custody(
        self,
        context_id: str,
        entry_indices,
        custody: object,
    ) -> None:
        """Bind private typed state to already-admitted public fields."""
        if not isinstance(context_id, str) or not context_id.strip():
            raise ValueError(
                "settlement custody context_id must be non-empty"
            )
        indices = tuple(entry_indices)
        if (
            not indices
            or any(
                isinstance(index, bool) or not isinstance(index, int)
                for index in indices
            )
            or len(set(indices)) != len(indices)
        ):
            raise ValueError(
                "settlement custody entry indices are invalid"
            )
        binder = getattr(custody, "_bind_to_window_entries", None)
        if not callable(binder):
            raise TypeError(
                "settlement custody has no exact window binder"
            )
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                raise KeyError(
                    f"unknown open physical context {context_id!r}"
                )
            if (
                window.closed_tick is not None
                or window._settlement_in_progress
            ):
                raise WindowIntegrityError(
                    "cannot bind custody to a closing physical window"
                )
            if any(
                index < 0 or index >= len(window.entries)
                for index in indices
            ):
                raise WindowIntegrityError(
                    "settlement custody references an absent entry"
                )
            already_bound = {
                index
                for bound in window._settlement_custodies
                for index in getattr(bound, "entry_indices", ())
            }
            if already_bound.intersection(indices):
                raise WindowIntegrityError(
                    "settlement custody repeated an entry authority"
                )
            entry_records = tuple(
                window.entries[index].record(index)
                for index in indices
            )
            bound = binder(
                window_id=window.window_id,
                context_id=window.context_id,
                entry_indices=indices,
                entry_records=entry_records,
            )
            if tuple(getattr(bound, "entry_indices", ())) != indices:
                raise WindowIntegrityError(
                    "settlement custody changed admitted entry indices"
                )
            window._settlement_custodies.append(bound)

    def _settlement_custodies_for_record(
        self,
        record: Mapping[str, Any],
    ) -> tuple[object, ...]:
        """Return private capabilities only during their active settlement."""
        window_id = str(record.get("window_id") or "")
        context_id = str(record.get("context_id") or "")
        with self._lock:
            window = self._contexts.get(context_id)
            if (
                window is None
                or window.window_id != window_id
                or not window._settlement_in_progress
            ):
                raise WindowIntegrityError(
                    "settlement custody requested outside its transaction"
                )
            return tuple(window._settlement_custodies)

    def end_context(
        self,
        context_id: str,
        reason: str = "context_complete",
        *,
        return_settlement: bool = False,
    ):
        """Seal, settle, and release one context atomically."""
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                return None
            if window._settlement_in_progress:
                raise WindowIntegrityError(
                    "physical context settlement is already in progress"
                )
            if window.closed_tick is None:
                proposed_tick = int(self._get_tick())
                proposed_reason = str(reason)
                record = window.record()
                record["closed_tick"] = proposed_tick
                record["close_reason"] = proposed_reason
            else:
                proposed_tick = window.closed_tick
                proposed_reason = window.close_reason
                record = window.record()
            record_bytes = len(_canonical_bytes(record))
            current_bytes = self._open_context_bytes[context_id]
            attempted_total = (
                self._open_context_total_bytes
                - current_bytes
                + record_bytes
            )
            if record_bytes > self._max_context_bytes:
                self._refuse_capacity(
                    scope="closed_context",
                    current_bytes=current_bytes,
                    attempted_bytes=record_bytes,
                    budget_bytes=self._max_context_bytes,
                )
            if attempted_total > self._max_total_open_bytes:
                self._refuse_capacity(
                    scope="aggregate_open_contexts",
                    current_bytes=self._open_context_total_bytes,
                    attempted_bytes=attempted_total,
                    budget_bytes=self._max_total_open_bytes,
                )
            if window.closed_tick is None:
                window.closed_tick = proposed_tick
                window.close_reason = proposed_reason
                window._mutation_revision += 1
            self._open_context_bytes[context_id] = record_bytes
            self._open_context_total_bytes = attempted_total
            mutation_seal = (
                window._mutation_revision,
                window.closed_tick,
                window.close_reason,
                len(window.entries),
                len(window._settlement_custodies),
            )
            window._settlement_in_progress = True
            settlement_record = copy.deepcopy(record)
            window_id = window.window_id

        settlement_result = None
        try:
            if self._settle_window is not None:
                settlement_result = self._settle_window(
                    settlement_record
                )
        except Exception as error:
            with self._lock:
                current = self._contexts.get(context_id)
                if current is window:
                    window._settlement_in_progress = False
            self._log_event(
                "window_settlement_failed",
                window_id=window_id,
                context_id=context_id,
                error_type=type(error).__name__,
                error=str(error),
            )
            raise

        with self._lock:
            current = self._contexts.get(context_id)
            if current is not window or not window._settlement_in_progress:
                raise WindowIntegrityError(
                    "physical context changed during atomic settlement"
                )
            if (
                window._mutation_revision,
                window.closed_tick,
                window.close_reason,
                len(window.entries),
                len(window._settlement_custodies),
            ) != mutation_seal:
                window._settlement_in_progress = False
                raise WindowIntegrityError(
                    "physical context mutated during atomic settlement"
                )
            removed = self._contexts.pop(context_id, None)
            if removed is not window:
                window._settlement_in_progress = False
                raise WindowIntegrityError(
                    "physical context changed during atomic settlement"
                )
            owned_bytes = self._open_context_bytes.pop(context_id)
            self._open_context_total_bytes -= owned_bytes
            if self._bound_context.get() == context_id:
                self._bound_context.set(None)
            event = {
                "window_id": window_id,
                "context_id": context_id,
                "close_reason": str(window.close_reason),
                "entry_count": len(window.entries),
                "tick_span": window.closed_tick - window.opened_tick,
            }
        self._log_event("window_closed", **event)
        if return_settlement:
            return window_id, settlement_result
        return window_id

    def discard_unsettled_context(
        self,
        context_id: str,
        reason: str = "context_failed",
    ) -> Optional[str]:
        """Release one failed transient context without publishing it."""
        with self._lock:
            window = self._contexts.get(context_id)
            if window is None:
                return None
            if window._settlement_in_progress:
                raise WindowIntegrityError(
                    "cannot discard a context during settlement"
                )
            removed = self._contexts.pop(context_id, None)
            if removed is not window:
                raise WindowIntegrityError(
                    "physical context changed during discard"
                )
            owned_bytes = self._open_context_bytes.pop(context_id)
            self._open_context_total_bytes -= owned_bytes
            if self._bound_context.get() == context_id:
                self._bound_context.set(None)
            event = {
                "window_id": window.window_id,
                "context_id": context_id,
                "close_reason": str(reason),
                "entry_count": len(window.entries),
            }
        self._log_event("window_discarded_unsettled", **event)
        return window.window_id

    def close(
        self,
        reason: str,
        context_id: Optional[str] = None,
    ) -> Optional[str]:
        """Close only an explicit or caller-bound context."""
        target = context_id or self._bound_context.get()
        if target is None:
            self._log_event(
                "window_close_unbound",
                close_reason=str(reason),
            )
            return None
        return self.end_context(target, reason)

    def open_context_ids(self, prefix: str = "") -> tuple[str, ...]:
        """Return a thread-independent point-in-time context census."""
        with self._lock:
            return tuple(
                context_id
                for context_id in self._contexts
                if context_id.startswith(prefix)
            )

    def snapshot_empty_transaction_boundary(
        self,
    ) -> EmptyWindowTransactionSnapshot:
        """Freeze exact transient counters only when no context is owned."""

        with self._lock:
            if (
                self._contexts
                or self._open_context_bytes
                or self._open_context_total_bytes
                or self._bound_context.get() is not None
            ):
                raise RuntimeError(
                    "physical window transaction boundary is not empty"
                )
            return EmptyWindowTransactionSnapshot(
                window_sequence=self._window_sequence,
                context_sequence=self._context_sequence,
                capacity_refusal_count=self._capacity_refusal_count,
                last_capacity_refusal=copy.deepcopy(
                    self._last_capacity_refusal
                ),
            )

    def restore_empty_transaction_boundary(
        self,
        snapshot: EmptyWindowTransactionSnapshot,
    ) -> None:
        """Restore an exact failed transaction without retaining its window."""

        if not isinstance(snapshot, EmptyWindowTransactionSnapshot):
            raise TypeError(
                "physical window transaction snapshot is not typed"
            )
        with self._lock:
            if (
                self._contexts
                or self._open_context_bytes
                or self._open_context_total_bytes
                or self._bound_context.get() is not None
            ):
                raise RuntimeError(
                    "physical window rollback found a live context"
                )
            self._window_sequence = snapshot.window_sequence
            self._context_sequence = snapshot.context_sequence
            self._capacity_refusal_count = (
                snapshot.capacity_refusal_count
            )
            self._last_capacity_refusal = copy.deepcopy(
                snapshot.last_capacity_refusal
            )
            if self.snapshot_empty_transaction_boundary() != snapshot:
                raise RuntimeError(
                    "physical window rollback changed prior state"
                )

    def resource_stats(self) -> dict:
        """Expose only bounded transient ownership."""
        with self._lock:
            return {
                "open_contexts": len(self._contexts),
                "open_context_bytes": self._open_context_total_bytes,
                "total_owned_bytes": self._open_context_total_bytes,
                "aggregate_budget_bytes": self._max_total_open_bytes,
                "per_context_budget_bytes": self._max_context_bytes,
                "capacity_refusal_count": self._capacity_refusal_count,
                "last_capacity_refusal": copy.deepcopy(
                    self._last_capacity_refusal
                ),
            }
