"""Bounded process-local custody for asynchronous embodied reading lessons.

The operation registry is a transport boundary, not a cognitive authority.
It retains no lesson geometry, WAV, designation, inferred identity, or
meaning.  It knows only an opaque operation identifier, the digest of the
strict physical request, execution state, and one bounded receipt-only JSON
result.  Terminal results are consumed by the first successful poll.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable


EMBODIED_READING_OPERATION_ACCEPTED_SCHEMA = (
    "guala.embodied_reading.operation.accepted.v1"
)
EMBODIED_READING_OPERATION_STATUS_SCHEMA = (
    "guala.embodied_reading.operation.status.v1"
)

MAX_EMBODIED_READING_OPERATIONS = 4
MAX_EMBODIED_READING_OPERATION_TOMBSTONES = 8
EMBODIED_READING_OPERATION_TTL_SECONDS = 900
MAX_EMBODIED_READING_OPERATION_RESULT_BYTES = 64 * 1024

_FAILURE_CODES = frozenset({
    "lesson_failed",
    "lesson_rejected",
    "response_bound_exceeded",
    "result_not_json",
})
_HEX = frozenset("0123456789abcdef")


class EmbodiedReadingOperationCapacityError(RuntimeError):
    """Raised when every bounded reading-operation slot is occupied."""


class EmbodiedReadingOperationUnknownError(KeyError):
    """Raised when this process has never held the opaque operation ID."""


class EmbodiedReadingOperationUnavailableError(RuntimeError):
    """Raised after expiry or terminal one-use consumption."""


@dataclass
class _Operation:
    request_sha256: str
    expires_monotonic: float
    state: str = "accepted"
    result_json: bytes | None = None
    failure_code: str | None = None


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


class EmbodiedReadingOperationRegistry:
    """Bounded, expiring, one-use custody for lesson operation receipts."""

    def __init__(
        self,
        *,
        max_operations: int = MAX_EMBODIED_READING_OPERATIONS,
        max_tombstones: int = (
            MAX_EMBODIED_READING_OPERATION_TOMBSTONES
        ),
        ttl_seconds: int = EMBODIED_READING_OPERATION_TTL_SECONDS,
        max_result_bytes: int = (
            MAX_EMBODIED_READING_OPERATION_RESULT_BYTES
        ),
        monotonic_now: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] = lambda: secrets.token_hex(32),
    ):
        for name, value in (
            ("max_operations", max_operations),
            ("max_tombstones", max_tombstones),
            ("ttl_seconds", ttl_seconds),
            ("max_result_bytes", max_result_bytes),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(f"{name} must be a positive integer")
        self._max_operations = max_operations
        self._max_tombstones = max_tombstones
        self._ttl_seconds = ttl_seconds
        self._max_result_bytes = max_result_bytes
        self._monotonic_now = monotonic_now
        self._token_factory = token_factory
        self._lock = threading.Lock()
        self._operations: dict[str, _Operation] = {}
        self._tombstones: dict[str, float] = {}

    @staticmethod
    def _factory_operation_id(value: object) -> str:
        try:
            return _sha256(value, "opaque operation ID")
        except ValueError as error:
            raise RuntimeError(
                "operation token factory did not return 256 opaque bits"
            ) from error

    @staticmethod
    def _external_operation_id(value: object) -> str:
        try:
            return _sha256(value, "opaque operation ID")
        except ValueError as error:
            raise EmbodiedReadingOperationUnknownError(value) from error

    def _remember_tombstone_locked(
        self,
        operation_id: str,
        *,
        now: float,
    ) -> None:
        while len(self._tombstones) >= self._max_tombstones:
            oldest = min(
                self._tombstones,
                key=self._tombstones.__getitem__,
            )
            del self._tombstones[oldest]
        self._tombstones[operation_id] = now + self._ttl_seconds

    def _expire_locked(self, now: float) -> None:
        for operation_id, expiry in tuple(self._tombstones.items()):
            if expiry <= now:
                del self._tombstones[operation_id]
        for operation_id, operation in tuple(self._operations.items()):
            # Running work owns a bounded slot until it reaches a terminal
            # state.  Expiring its record would orphan an active mutation and
            # permit capacity to exceed the declared physical boundary.
            if (
                operation.state != "running"
                and operation.expires_monotonic <= now
            ):
                del self._operations[operation_id]
                self._remember_tombstone_locked(
                    operation_id,
                    now=now,
                )

    def create(self, request_sha256: str) -> str:
        request_sha256 = _sha256(
            request_sha256,
            "embodied reading request",
        )
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            if len(self._operations) >= self._max_operations:
                raise EmbodiedReadingOperationCapacityError(
                    "embodied reading operation capacity is occupied"
                )
            operation_id = self._factory_operation_id(
                self._token_factory()
            )
            if (
                operation_id in self._operations
                or operation_id in self._tombstones
            ):
                raise RuntimeError("opaque operation ID collision")
            self._operations[operation_id] = _Operation(
                request_sha256=request_sha256,
                expires_monotonic=now + self._ttl_seconds,
            )
            return operation_id

    def discard_unstarted(self, operation_id: str) -> None:
        operation_id = self._external_operation_id(operation_id)
        now = float(self._monotonic_now())
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None or operation.state != "accepted":
                raise RuntimeError(
                    "only an unstarted reading operation may be discarded"
                )
            del self._operations[operation_id]
            self._remember_tombstone_locked(operation_id, now=now)

    def mark_running(self, operation_id: str) -> bool:
        operation_id = self._external_operation_id(operation_id)
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            operation = self._operations.get(operation_id)
            if operation is None:
                return False
            if operation.state != "accepted":
                raise RuntimeError(
                    "embodied reading operation started twice"
                )
            operation.state = "running"
            return True

    def complete(
        self,
        operation_id: str,
        result: dict[str, object],
    ) -> bool:
        operation_id = self._external_operation_id(operation_id)
        failure_code = None
        try:
            if not isinstance(result, dict):
                raise TypeError("reading operation result must be a mapping")
            result_json = _canonical_json_bytes(result)
        except (TypeError, ValueError):
            result_json = None
            failure_code = "result_not_json"
        if (
            result_json is not None
            and len(result_json) > self._max_result_bytes
        ):
            result_json = None
            failure_code = "response_bound_exceeded"

        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            operation = self._operations.get(operation_id)
            if operation is None:
                return False
            if operation.state != "running":
                raise RuntimeError(
                    "only a running reading operation may complete"
                )
            operation.expires_monotonic = now + self._ttl_seconds
            if failure_code is not None:
                operation.state = "failed"
                operation.failure_code = failure_code
                return True
            operation.state = "completed"
            operation.result_json = result_json
            return True

    def fail(self, operation_id: str, failure_code: str) -> bool:
        operation_id = self._external_operation_id(operation_id)
        if failure_code not in _FAILURE_CODES:
            raise ValueError(
                "unknown embodied reading operation failure code"
            )
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            operation = self._operations.get(operation_id)
            if operation is None:
                return False
            if operation.state != "running":
                raise RuntimeError(
                    "only a running reading operation may fail"
                )
            operation.state = "failed"
            operation.failure_code = failure_code
            operation.expires_monotonic = now + self._ttl_seconds
            return True

    def poll(self, operation_id: str) -> tuple[int, dict[str, object]]:
        operation_id = self._external_operation_id(operation_id)
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            if operation_id in self._tombstones:
                raise EmbodiedReadingOperationUnavailableError(
                    "operation expired or its terminal result was consumed"
                )
            operation = self._operations.get(operation_id)
            if operation is None:
                raise EmbodiedReadingOperationUnknownError(operation_id)
            response: dict[str, object] = {
                "operation_id": operation_id,
                "request_sha256": operation.request_sha256,
                "schema": EMBODIED_READING_OPERATION_STATUS_SCHEMA,
                "state": operation.state,
            }
            if operation.state in {"accepted", "running"}:
                return 202, response
            del self._operations[operation_id]
            self._remember_tombstone_locked(operation_id, now=now)
            if operation.state == "failed":
                response["failure_code"] = operation.failure_code
                return 409, response
            if (
                operation.state != "completed"
                or operation.result_json is None
            ):
                raise RuntimeError(
                    "terminal reading operation record is incomplete"
                )
            response["result"] = json.loads(
                operation.result_json.decode("ascii")
            )
            return 200, response

    def snapshot(self) -> dict[str, int]:
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            return {
                "max_operations": self._max_operations,
                "max_result_bytes": self._max_result_bytes,
                "max_tombstones": self._max_tombstones,
                "operation_count": len(self._operations),
                "tombstone_count": len(self._tombstones),
                "ttl_seconds": self._ttl_seconds,
            }


__all__ = (
    "EMBODIED_READING_OPERATION_ACCEPTED_SCHEMA",
    "EMBODIED_READING_OPERATION_STATUS_SCHEMA",
    "EMBODIED_READING_OPERATION_TTL_SECONDS",
    "EmbodiedReadingOperationCapacityError",
    "EmbodiedReadingOperationRegistry",
    "EmbodiedReadingOperationUnavailableError",
    "EmbodiedReadingOperationUnknownError",
    "MAX_EMBODIED_READING_OPERATIONS",
    "MAX_EMBODIED_READING_OPERATION_RESULT_BYTES",
    "MAX_EMBODIED_READING_OPERATION_TOMBSTONES",
)
