"""Bounded process-local custody for asynchronous learned physical-act trials.

The registry is deliberately content-neutral.  It knows only an opaque
operation identifier, the digest of the exact physical request, execution
state, and a bounded JSON transport result.  It writes nothing to disk and
never interprets an act as a word, imitation, or intelligible emission.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable

from dsf_ai_service.substrate.embodiment_world import MAX_VOCAL_SAMPLE_COUNT


LEARNED_BODY_ACT_TRIAL_ACCEPTED_SCHEMA = (
    "guala.embodiment.learned_body_act_trial.accepted.v1"
)
LEARNED_BODY_ACT_TRIAL_STATUS_SCHEMA = (
    "guala.embodiment.learned_body_act_trial.status.v1"
)
LEARNED_BODY_ACT_TRIAL_REQUEST_SCHEMA = (
    "guala.embodiment.learned_body_act_trial.request.v1"
)

MAX_LEARNED_BODY_ACT_TRIAL_OPERATIONS = 16
MAX_LEARNED_BODY_ACT_TRIAL_TOMBSTONES = 16
LEARNED_BODY_ACT_TRIAL_TTL_SECONDS = 300

# The physical pressure contribution is bounded by MAX_VOCAL_SAMPLE_COUNT
# signed 16-bit samples and canonical base64 expansion.  The remaining
# 256 KiB is an explicit ceiling for typed structural receipts and the world
# transition envelope.  It is a transport custody limit, never a decision
# threshold.
MAX_LEARNED_BODY_ACT_STRUCTURAL_ENVELOPE_BYTES = 256 * 1024
MAX_LEARNED_BODY_ACT_PCM_BASE64_BYTES = (
    4 * (((MAX_VOCAL_SAMPLE_COUNT * 2) + 2) // 3)
)
MAX_LEARNED_BODY_ACT_TRIAL_RESULT_BYTES = (
    MAX_LEARNED_BODY_ACT_PCM_BASE64_BYTES
    + MAX_LEARNED_BODY_ACT_STRUCTURAL_ENVELOPE_BYTES
)

_FAILURE_CODES = frozenset({
    "execution_failed",
    "execution_rejected",
    "result_not_json",
    "response_bound_exceeded",
})


class LearnedBodyActTrialCapacityError(RuntimeError):
    """Raised when every bounded operation slot is occupied."""


class LearnedBodyActTrialUnknownError(KeyError):
    """Raised when this process has never held the opaque operation ID."""


class LearnedBodyActTrialUnavailableError(RuntimeError):
    """Raised after expiry or terminal one-use consumption."""


@dataclass
class _Operation:
    request_sha256: str
    created_monotonic: float
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


def canonical_trial_request_sha256(payload: dict[str, object]) -> str:
    """Digest the exact normalized physical request with no semantic label."""

    if not isinstance(payload, dict):
        raise TypeError("trial request digest payload must be a mapping")
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


class LearnedBodyActTrialRegistry:
    """A bounded, expiring, one-use, process-local operation registry."""

    def __init__(
        self,
        *,
        max_operations: int = MAX_LEARNED_BODY_ACT_TRIAL_OPERATIONS,
        max_tombstones: int = MAX_LEARNED_BODY_ACT_TRIAL_TOMBSTONES,
        ttl_seconds: int = LEARNED_BODY_ACT_TRIAL_TTL_SECONDS,
        max_result_bytes: int = MAX_LEARNED_BODY_ACT_TRIAL_RESULT_BYTES,
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
                not isinstance(value, int)
                or isinstance(value, bool)
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
    def _validate_sha256(value: str, label: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise ValueError(f"{label} must be a lowercase SHA-256")
        return value

    @staticmethod
    def _validate_operation_id(value: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            raise RuntimeError(
                "operation token factory did not return 256 opaque bits"
            )
        return value

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
        request_sha256 = self._validate_sha256(
            request_sha256,
            "request_sha256",
        )
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            if len(self._operations) >= self._max_operations:
                raise LearnedBodyActTrialCapacityError(
                    "learned body-act trial capacity is occupied"
                )
            operation_id = self._validate_operation_id(
                self._token_factory()
            )
            if (
                operation_id in self._operations
                or operation_id in self._tombstones
            ):
                raise RuntimeError("opaque operation ID collision")
            self._operations[operation_id] = _Operation(
                request_sha256=request_sha256,
                created_monotonic=now,
                expires_monotonic=now + self._ttl_seconds,
            )
            return operation_id

    def discard_unstarted(self, operation_id: str) -> None:
        now = float(self._monotonic_now())
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None or operation.state != "accepted":
                raise RuntimeError(
                    "only an unstarted trial may be discarded"
                )
            del self._operations[operation_id]
            self._remember_tombstone_locked(operation_id, now=now)

    def mark_running(self, operation_id: str) -> bool:
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            operation = self._operations.get(operation_id)
            if operation is None:
                return False
            if operation.state != "accepted":
                raise RuntimeError("learned body-act trial started twice")
            operation.state = "running"
            return True

    def complete(
        self,
        operation_id: str,
        result: dict[str, object],
    ) -> bool:
        failure_code = None
        try:
            if not isinstance(result, dict):
                raise TypeError("trial result must be a mapping")
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
                    "only a running learned body-act trial may complete"
                )
            if failure_code is not None:
                operation.state = "failed"
                operation.failure_code = failure_code
                operation.expires_monotonic = now + self._ttl_seconds
                return True
            operation.state = "completed"
            operation.result_json = result_json
            operation.expires_monotonic = now + self._ttl_seconds
            return True

    def fail(self, operation_id: str, failure_code: str) -> bool:
        if failure_code not in _FAILURE_CODES:
            raise ValueError("unknown learned body-act trial failure code")
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            operation = self._operations.get(operation_id)
            if operation is None:
                return False
            if operation.state != "running":
                raise RuntimeError(
                    "only a running learned body-act trial may fail"
                )
            operation.state = "failed"
            operation.failure_code = failure_code
            operation.expires_monotonic = now + self._ttl_seconds
            return True

    def poll(self, operation_id: str) -> tuple[int, dict[str, object]]:
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            if operation_id in self._tombstones:
                raise LearnedBodyActTrialUnavailableError(
                    "operation expired or its terminal result was consumed"
                )
            operation = self._operations.get(operation_id)
            if operation is None:
                raise LearnedBodyActTrialUnknownError(operation_id)
            response: dict[str, object] = {
                "schema": LEARNED_BODY_ACT_TRIAL_STATUS_SCHEMA,
                "operation_id": operation_id,
                "request_sha256": operation.request_sha256,
                "state": operation.state,
            }
            if operation.state in {"accepted", "running"}:
                return 202, response
            del self._operations[operation_id]
            self._remember_tombstone_locked(operation_id, now=now)
            if operation.state == "failed":
                response["failure_code"] = operation.failure_code
                return 409, response
            if operation.state != "completed" or operation.result_json is None:
                raise RuntimeError("terminal trial record is incomplete")
            response["result"] = json.loads(
                operation.result_json.decode("ascii")
            )
            return 200, response

    def snapshot(self) -> dict[str, int]:
        now = float(self._monotonic_now())
        with self._lock:
            self._expire_locked(now)
            return {
                "operation_count": len(self._operations),
                "tombstone_count": len(self._tombstones),
                "max_operations": self._max_operations,
                "max_tombstones": self._max_tombstones,
                "ttl_seconds": self._ttl_seconds,
                "max_result_bytes": self._max_result_bytes,
            }
