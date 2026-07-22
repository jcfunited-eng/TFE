"""Capacity-one authority for causal settlement-to-action dispatch.

The dispatcher coordinates, but does not reinterpret, the full-field identity
owned by :class:`CausalActionCycle`.  It admits one verified causal settlement,
selects at most one learned action, sends one authenticated request to the
matching injected executor, and waits for an explicitly authenticated outcome
observation binding.  A later sensory settlement is never inferred to be an
outcome merely because it arrived later.

Chi values and source tags are deliberately absent from every identity and
decision in this module.  There is no score, timeout, retry guess, probabilistic
choice, or lifetime dispatch ledger.  The only retained transaction is the one
live transaction plus the latest terminal result used for idempotence.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
    PerceptionWitness,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


REQUEST_SCHEMA = "guala.causal_settlement_dispatcher.request.v1"
ACKNOWLEDGEMENT_SCHEMA = "guala.causal_settlement_dispatcher.executor_ack.v1"
OBSERVATION_ATTESTATION_SCHEMA = (
    "guala.causal_settlement_dispatcher.outcome_attestation.v1"
)
OUTCOME_BINDING_SCHEMA = "guala.causal_settlement_dispatcher.outcome_binding.v1"
RESULT_SCHEMA = "guala.causal_settlement_dispatcher.result.v1"
ACTIVE_SCHEMA = "guala.causal_settlement_dispatcher.active.v1"
STATE_SCHEMA = "guala.causal_settlement_dispatcher.state.v1"
ENVELOPE_SCHEMA = "guala.causal_settlement_dispatcher.state.hmac.v1"

REQUEST_DOMAIN = b"guala-causal-settlement-dispatcher-request-v1\0"
ACKNOWLEDGEMENT_DOMAIN = b"guala-causal-settlement-dispatcher-ack-v1\0"
OBSERVATION_ATTESTATION_DOMAIN = (
    b"guala-causal-settlement-dispatcher-observation-v1\0"
)
OUTCOME_BINDING_DOMAIN = b"guala-causal-settlement-dispatcher-binding-v1\0"
STATE_DOMAIN = b"guala-causal-settlement-dispatcher-state-v1\0"

DEFAULT_MAX_WITNESS_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_ENCODED_STATE_BYTES = 1024 * 1024
MIN_ENCODED_STATE_BYTES = 64 * 1024
MAX_IDENTIFIER_BYTES = 256
MAX_AUTHORITY_KEY_BYTES = 4096
MAX_ACTION_PAYLOAD_BYTES = 4096
MAX_SPEECH_SCALARS = 512


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: object, name: str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(f"{name} must be bytes or text")
    if not result or len(result) > MAX_AUTHORITY_KEY_BYTES:
        raise ValueError(f"{name} must be bounded and nonempty")
    return result


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _sha256(value: object, name: str) -> str:
    return sha256_digest(value, name)


def _sign(key: bytes, domain: bytes, payload: Mapping[str, object]) -> str:
    return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()


def _authority_receipt(payload: Mapping[str, object], signature: str) -> str:
    _sha256(signature, "authority HMAC")
    return _digest({"authority_hmac_sha256": signature, "payload": dict(payload)})


def _verify_hmac(
    *, key: bytes, domain: bytes, payload: Mapping[str, object], signature: object
) -> None:
    supplied = _sha256(signature, "authority HMAC")
    expected = _sign(key, domain, payload)
    if not hmac.compare_digest(expected, supplied):
        raise ValueError("authority HMAC changed")


def _action_from_record(value: object) -> ActionCommand:
    expected = {
        "command_payload_base64",
        "kind",
        "port_id",
        "schema",
        "unicode_scalars",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("dispatcher action record fields changed")
    try:
        command_payload = base64.b64decode(
            value.get("command_payload_base64"), validate=True
        )
    except Exception as error:
        raise ValueError("dispatcher action payload is not canonical base64") from error
    scalars = value.get("unicode_scalars")
    if not isinstance(scalars, list):
        raise ValueError("dispatcher action Unicode sequence changed")
    action = ActionCommand(
        kind=value.get("kind"),
        unicode_scalars=tuple(scalars),
        port_id=value.get("port_id"),
        command_payload=command_payload,
    )
    action.verify(
        max_scalars=MAX_SPEECH_SCALARS,
        max_command_bytes=MAX_ACTION_PAYLOAD_BYTES,
    )
    if action.as_record() != dict(value):
        raise ValueError("dispatcher action record is not canonical")
    return action


@dataclass(frozen=True, slots=True)
class ExecutorRequest:
    intent_receipt_sha256: str
    trigger_settlement_receipt_sha256: str
    action: ActionCommand
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action": self.action.as_record(),
            "intent_receipt_sha256": self.intent_receipt_sha256,
            "schema": REQUEST_SCHEMA,
            "trigger_settlement_receipt_sha256": (
                self.trigger_settlement_receipt_sha256
            ),
        }

    @property
    def authority_receipt_sha256(self) -> str:
        return _authority_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key, "dispatcher authority key")
        _sha256(self.intent_receipt_sha256, "request intent")
        _sha256(self.trigger_settlement_receipt_sha256, "request trigger")
        self.action.verify(
            max_scalars=MAX_SPEECH_SCALARS,
            max_command_bytes=MAX_ACTION_PAYLOAD_BYTES,
        )
        _verify_hmac(
            key=key,
            domain=REQUEST_DOMAIN,
            payload=self.payload(),
            signature=self.authority_hmac_sha256,
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _request_from(value: object, *, key: bytes) -> ExecutorRequest:
    expected = {
        "action",
        "authority_hmac_sha256",
        "intent_receipt_sha256",
        "schema",
        "trigger_settlement_receipt_sha256",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != REQUEST_SCHEMA
    ):
        raise ValueError("executor request fields changed")
    request = ExecutorRequest(
        intent_receipt_sha256=value.get("intent_receipt_sha256"),
        trigger_settlement_receipt_sha256=value.get(
            "trigger_settlement_receipt_sha256"
        ),
        action=_action_from_record(value.get("action")),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    request.verify(key)
    return request


@dataclass(frozen=True, slots=True)
class ExecutorAcknowledgement:
    executor_id: str
    request_receipt_sha256: str
    executor_action_receipt_sha256: str
    disposition: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "executor_action_receipt_sha256": self.executor_action_receipt_sha256,
            "executor_id": self.executor_id,
            "request_receipt_sha256": self.request_receipt_sha256,
            "schema": ACKNOWLEDGEMENT_SCHEMA,
        }

    @property
    def authority_receipt_sha256(self) -> str:
        return _authority_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key, "executor authority key")
        _identifier(self.executor_id, "executor id")
        _sha256(self.request_receipt_sha256, "acknowledged request")
        _sha256(self.executor_action_receipt_sha256, "executor action receipt")
        if self.disposition not in {"executed", "rejected"}:
            raise ValueError("executor disposition must be executed or rejected")
        _verify_hmac(
            key=key,
            domain=ACKNOWLEDGEMENT_DOMAIN,
            payload=self.payload(),
            signature=self.authority_hmac_sha256,
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def authenticate_executor_acknowledgement(
    *,
    request: ExecutorRequest,
    executor_id: str,
    authority_key: object,
    executor_action_receipt_sha256: str,
    disposition: str,
) -> ExecutorAcknowledgement:
    """Create the acknowledgement at an injected executor boundary."""
    key = _key(authority_key, "executor authority key")
    unsigned = {
        "disposition": disposition,
        "executor_action_receipt_sha256": _sha256(
            executor_action_receipt_sha256, "executor action receipt"
        ),
        "executor_id": _identifier(executor_id, "executor id"),
        "request_receipt_sha256": request.authority_receipt_sha256,
        "schema": ACKNOWLEDGEMENT_SCHEMA,
    }
    acknowledgement = ExecutorAcknowledgement(
        executor_id=unsigned["executor_id"],
        request_receipt_sha256=unsigned["request_receipt_sha256"],
        executor_action_receipt_sha256=unsigned[
            "executor_action_receipt_sha256"
        ],
        disposition=disposition,
        authority_hmac_sha256=_sign(key, ACKNOWLEDGEMENT_DOMAIN, unsigned),
    )
    acknowledgement.verify(key)
    return acknowledgement


def _acknowledgement_from(
    value: object, *, key: bytes
) -> ExecutorAcknowledgement:
    expected = {
        "authority_hmac_sha256",
        "disposition",
        "executor_action_receipt_sha256",
        "executor_id",
        "request_receipt_sha256",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != ACKNOWLEDGEMENT_SCHEMA
    ):
        raise ValueError("executor acknowledgement fields changed")
    acknowledgement = ExecutorAcknowledgement(
        executor_id=value.get("executor_id"),
        request_receipt_sha256=value.get("request_receipt_sha256"),
        executor_action_receipt_sha256=value.get(
            "executor_action_receipt_sha256"
        ),
        disposition=value.get("disposition"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    acknowledgement.verify(key)
    return acknowledgement


@dataclass(frozen=True, slots=True)
class OutcomeObservationAttestation:
    observer_id: str
    execution_receipt_sha256: str
    outcome_settlement_receipt_sha256: str
    observation_nonce: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "observation_nonce": self.observation_nonce,
            "observer_id": self.observer_id,
            "outcome_settlement_receipt_sha256": (
                self.outcome_settlement_receipt_sha256
            ),
            "schema": OBSERVATION_ATTESTATION_SCHEMA,
        }

    @property
    def authority_receipt_sha256(self) -> str:
        return _authority_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key, "outcome observer authority key")
        _identifier(self.observer_id, "outcome observer id")
        _sha256(self.execution_receipt_sha256, "observed execution")
        _sha256(self.outcome_settlement_receipt_sha256, "observed settlement")
        _identifier(self.observation_nonce, "observation nonce")
        if len(self.observation_nonce) < 16:
            raise ValueError("observation nonce must carry at least 16 characters")
        _verify_hmac(
            key=key,
            domain=OBSERVATION_ATTESTATION_DOMAIN,
            payload=self.payload(),
            signature=self.authority_hmac_sha256,
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def authenticate_outcome_observation(
    *,
    observer_id: str,
    authority_key: object,
    execution_receipt_sha256: str,
    outcome_settlement_receipt_sha256: str,
    observation_nonce: str,
) -> OutcomeObservationAttestation:
    """Create the independent sensory observer's causal attestation."""
    key = _key(authority_key, "outcome observer authority key")
    unsigned = {
        "execution_receipt_sha256": _sha256(
            execution_receipt_sha256, "observed execution"
        ),
        "observation_nonce": _identifier(observation_nonce, "observation nonce"),
        "observer_id": _identifier(observer_id, "outcome observer id"),
        "outcome_settlement_receipt_sha256": _sha256(
            outcome_settlement_receipt_sha256, "observed settlement"
        ),
        "schema": OBSERVATION_ATTESTATION_SCHEMA,
    }
    if len(observation_nonce) < 16:
        raise ValueError("observation nonce must carry at least 16 characters")
    attestation = OutcomeObservationAttestation(
        observer_id=unsigned["observer_id"],
        execution_receipt_sha256=unsigned["execution_receipt_sha256"],
        outcome_settlement_receipt_sha256=unsigned[
            "outcome_settlement_receipt_sha256"
        ],
        observation_nonce=unsigned["observation_nonce"],
        authority_hmac_sha256=_sign(
            key, OBSERVATION_ATTESTATION_DOMAIN, unsigned
        ),
    )
    attestation.verify(key)
    return attestation


def _attestation_from(
    value: object, *, key: bytes
) -> OutcomeObservationAttestation:
    expected = {
        "authority_hmac_sha256",
        "execution_receipt_sha256",
        "observation_nonce",
        "observer_id",
        "outcome_settlement_receipt_sha256",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != OBSERVATION_ATTESTATION_SCHEMA
    ):
        raise ValueError("outcome observation attestation fields changed")
    attestation = OutcomeObservationAttestation(
        observer_id=value.get("observer_id"),
        execution_receipt_sha256=value.get("execution_receipt_sha256"),
        outcome_settlement_receipt_sha256=value.get(
            "outcome_settlement_receipt_sha256"
        ),
        observation_nonce=value.get("observation_nonce"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    attestation.verify(key)
    return attestation


@dataclass(frozen=True, slots=True)
class OutcomeObservationBinding:
    execution_receipt_sha256: str
    outcome_settlement_receipt_sha256: str
    outcome_structural_fingerprint: str
    observer_attestation_receipt_sha256: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "observer_attestation_receipt_sha256": (
                self.observer_attestation_receipt_sha256
            ),
            "outcome_settlement_receipt_sha256": (
                self.outcome_settlement_receipt_sha256
            ),
            "outcome_structural_fingerprint": self.outcome_structural_fingerprint,
            "schema": OUTCOME_BINDING_SCHEMA,
        }

    @property
    def authority_receipt_sha256(self) -> str:
        return _authority_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key, "dispatcher authority key")
        _sha256(self.execution_receipt_sha256, "bound execution")
        _sha256(self.outcome_settlement_receipt_sha256, "bound outcome")
        _sha256(self.outcome_structural_fingerprint, "bound outcome structure")
        _sha256(
            self.observer_attestation_receipt_sha256,
            "bound observer attestation",
        )
        _verify_hmac(
            key=key,
            domain=OUTCOME_BINDING_DOMAIN,
            payload=self.payload(),
            signature=self.authority_hmac_sha256,
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _binding_from(
    value: object, *, dispatcher_key: bytes
) -> OutcomeObservationBinding:
    expected = {
        "authority_hmac_sha256",
        "execution_receipt_sha256",
        "observer_attestation_receipt_sha256",
        "outcome_settlement_receipt_sha256",
        "outcome_structural_fingerprint",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != OUTCOME_BINDING_SCHEMA
    ):
        raise ValueError("outcome observation binding fields changed")
    binding = OutcomeObservationBinding(
        execution_receipt_sha256=value.get("execution_receipt_sha256"),
        outcome_settlement_receipt_sha256=value.get(
            "outcome_settlement_receipt_sha256"
        ),
        outcome_structural_fingerprint=value.get(
            "outcome_structural_fingerprint"
        ),
        observer_attestation_receipt_sha256=value.get(
            "observer_attestation_receipt_sha256"
        ),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    binding.verify(dispatcher_key)
    return binding


@dataclass(frozen=True, slots=True)
class DispatchResult:
    status: str
    phase: str
    trigger_settlement_receipt_sha256: str
    reason: str
    request_receipt_sha256: str | None = None
    execution_receipt_sha256: str | None = None
    executor_acknowledgement_receipt_sha256: str | None = None
    closure_feedback_receipt_sha256: str | None = None

    def verify(self) -> None:
        if self.status not in {
            "unknown",
            "ambiguous",
            "pending",
            "rejected",
            "completed",
        }:
            raise ValueError("dispatch result status changed")
        allowed_phases = {
            "selection",
            "executor_acknowledgement",
            "outcome_observation",
            "closed",
        }
        if self.phase not in allowed_phases:
            raise ValueError("dispatch result phase changed")
        _sha256(self.trigger_settlement_receipt_sha256, "dispatch trigger")
        _identifier(self.reason, "dispatch reason")
        for value, name in (
            (self.request_receipt_sha256, "dispatch request"),
            (self.execution_receipt_sha256, "dispatch execution"),
            (
                self.executor_acknowledgement_receipt_sha256,
                "dispatch acknowledgement",
            ),
            (self.closure_feedback_receipt_sha256, "dispatch closure"),
        ):
            if value is not None:
                _sha256(value, name)
        if self.status in {"unknown", "ambiguous"}:
            if self.phase != "selection" or any(
                value is not None
                for value in (
                    self.request_receipt_sha256,
                    self.execution_receipt_sha256,
                    self.executor_acknowledgement_receipt_sha256,
                    self.closure_feedback_receipt_sha256,
                )
            ):
                raise ValueError("silent dispatch result exposed action authority")
        elif self.status == "pending":
            if self.request_receipt_sha256 is None or self.phase == "closed":
                raise ValueError("pending dispatch lost its request")
        elif self.status == "rejected":
            if (
                self.phase != "closed"
                or self.request_receipt_sha256 is None
                or self.executor_acknowledgement_receipt_sha256 is None
                or self.execution_receipt_sha256 is not None
            ):
                raise ValueError("rejected dispatch lost executor authority")
        elif (
            self.phase != "closed"
            or self.request_receipt_sha256 is None
            or self.execution_receipt_sha256 is None
            or self.executor_acknowledgement_receipt_sha256 is None
            or self.closure_feedback_receipt_sha256 is None
        ):
            raise ValueError("completed dispatch lost its closure chain")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            "closure_feedback_receipt_sha256": self.closure_feedback_receipt_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "executor_acknowledgement_receipt_sha256": (
                self.executor_acknowledgement_receipt_sha256
            ),
            "phase": self.phase,
            "reason": self.reason,
            "request_receipt_sha256": self.request_receipt_sha256,
            "schema": RESULT_SCHEMA,
            "status": self.status,
            "trigger_settlement_receipt_sha256": (
                self.trigger_settlement_receipt_sha256
            ),
        }


def _result_from(value: object) -> DispatchResult:
    expected = {
        "closure_feedback_receipt_sha256",
        "execution_receipt_sha256",
        "executor_acknowledgement_receipt_sha256",
        "phase",
        "reason",
        "request_receipt_sha256",
        "schema",
        "status",
        "trigger_settlement_receipt_sha256",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != RESULT_SCHEMA
    ):
        raise ValueError("dispatch result fields changed")
    result = DispatchResult(
        status=value.get("status"),
        phase=value.get("phase"),
        trigger_settlement_receipt_sha256=value.get(
            "trigger_settlement_receipt_sha256"
        ),
        reason=value.get("reason"),
        request_receipt_sha256=value.get("request_receipt_sha256"),
        execution_receipt_sha256=value.get("execution_receipt_sha256"),
        executor_acknowledgement_receipt_sha256=value.get(
            "executor_acknowledgement_receipt_sha256"
        ),
        closure_feedback_receipt_sha256=value.get(
            "closure_feedback_receipt_sha256"
        ),
    )
    result.verify()
    return result


@dataclass(frozen=True, slots=True)
class _ActiveDispatch:
    phase: str
    trigger_settlement_receipt_sha256: str
    request: ExecutorRequest
    acknowledgement: ExecutorAcknowledgement | None = None
    execution_receipt_sha256: str | None = None
    outcome_binding: OutcomeObservationBinding | None = None
    cycle_outcome_receipt_sha256: str | None = None

    def as_record(self) -> dict[str, object]:
        return {
            "acknowledgement": (
                self.acknowledgement.as_record()
                if self.acknowledgement is not None
                else None
            ),
            "cycle_outcome_receipt_sha256": self.cycle_outcome_receipt_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "outcome_binding": (
                self.outcome_binding.as_record()
                if self.outcome_binding is not None
                else None
            ),
            "phase": self.phase,
            "request": self.request.as_record(),
            "schema": ACTIVE_SCHEMA,
            "trigger_settlement_receipt_sha256": (
                self.trigger_settlement_receipt_sha256
            ),
        }


class CausalSettlementDispatcher:
    """Serial capacity-one dispatch owner with explicit outcome causality."""

    def __init__(
        self,
        *,
        cycle: CausalActionCycle,
        authority_key: object,
        speech_executor: Callable[[ExecutorRequest], ExecutorAcknowledgement],
        speech_executor_id: str,
        speech_executor_authority_key: object,
        embodiment_executor: Callable[[ExecutorRequest], ExecutorAcknowledgement],
        embodiment_executor_id: str,
        embodiment_executor_authority_key: object,
        outcome_observer_id: str,
        outcome_observer_authority_key: object,
        max_witness_bytes: int = DEFAULT_MAX_WITNESS_BYTES,
        max_encoded_state_bytes: int = DEFAULT_MAX_ENCODED_STATE_BYTES,
    ) -> None:
        if not isinstance(cycle, CausalActionCycle):
            raise TypeError("dispatcher requires a causal action cycle")
        if not callable(speech_executor) or not callable(embodiment_executor):
            raise TypeError("dispatcher executors must be callable")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in (max_witness_bytes, max_encoded_state_bytes)
        ):
            raise ValueError("dispatcher capacities must be positive integers")
        if max_encoded_state_bytes < MIN_ENCODED_STATE_BYTES:
            raise ValueError("dispatcher state capacity is below its exact live bound")
        self._cycle = cycle
        self._key = _key(authority_key, "dispatcher authority key")
        self._speech_executor = speech_executor
        self._speech_executor_id = _identifier(
            speech_executor_id, "speech executor id"
        )
        self._speech_executor_key = _key(
            speech_executor_authority_key, "speech executor authority key"
        )
        self._embodiment_executor = embodiment_executor
        self._embodiment_executor_id = _identifier(
            embodiment_executor_id, "embodiment executor id"
        )
        self._embodiment_executor_key = _key(
            embodiment_executor_authority_key,
            "embodiment executor authority key",
        )
        self._outcome_observer_id = _identifier(
            outcome_observer_id, "outcome observer id"
        )
        self._outcome_observer_key = _key(
            outcome_observer_authority_key,
            "outcome observer authority key",
        )
        self._max_witness_bytes = max_witness_bytes
        self._max_encoded_state_bytes = max_encoded_state_bytes
        self._lock = threading.RLock()
        self._active: _ActiveDispatch | None = None
        self._latest_terminal: DispatchResult | None = None

    def _request(self, intent: object) -> ExecutorRequest:
        unsigned = {
            "action": intent.action.as_record(),
            "intent_receipt_sha256": intent.authority_receipt_sha256,
            "schema": REQUEST_SCHEMA,
            "trigger_settlement_receipt_sha256": (
                intent.trigger_settlement_receipt_sha256
            ),
        }
        request = ExecutorRequest(
            intent_receipt_sha256=unsigned["intent_receipt_sha256"],
            trigger_settlement_receipt_sha256=unsigned[
                "trigger_settlement_receipt_sha256"
            ],
            action=intent.action,
            authority_hmac_sha256=_sign(self._key, REQUEST_DOMAIN, unsigned),
        )
        request.verify(self._key)
        return request

    def _pending_result(self, active: _ActiveDispatch, reason: str) -> DispatchResult:
        result = DispatchResult(
            status="pending",
            phase=(
                "executor_acknowledgement"
                if active.phase == "executor_acknowledgement"
                else "outcome_observation"
            ),
            trigger_settlement_receipt_sha256=(
                active.trigger_settlement_receipt_sha256
            ),
            reason=reason,
            request_receipt_sha256=active.request.authority_receipt_sha256,
            execution_receipt_sha256=active.execution_receipt_sha256,
            executor_acknowledgement_receipt_sha256=(
                active.acknowledgement.authority_receipt_sha256
                if active.acknowledgement is not None
                else None
            ),
        )
        result.verify()
        return result

    def dispatch(self, settlement: CausalExperienceSettlement) -> DispatchResult:
        witness = PerceptionWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        with self._lock:
            if (
                self._latest_terminal is not None
                and self._latest_terminal.trigger_settlement_receipt_sha256
                == witness.settlement_receipt_sha256
            ):
                return self._latest_terminal
            if self._active is not None:
                if (
                    self._active.trigger_settlement_receipt_sha256
                    == witness.settlement_receipt_sha256
                ):
                    same_request_reason = (
                        "executor_acknowledgement_pending"
                        if self._active.phase == "executor_acknowledgement"
                        else "outcome_observation_binding_pending"
                    )
                    return self._pending_result(
                        self._active, same_request_reason
                    )
                return self._pending_result(
                    self._active, "causal_action_capacity_one_busy"
                )
            selection = self._cycle.select(settlement)
            if selection.status in {"unknown", "ambiguous"}:
                result = DispatchResult(
                    status=selection.status,
                    phase="selection",
                    trigger_settlement_receipt_sha256=(
                        witness.settlement_receipt_sha256
                    ),
                    reason=selection.stop_reason,
                )
                result.verify()
                return result
            request = self._request(selection.intent)
            self._active = _ActiveDispatch(
                phase="executor_acknowledgement",
                trigger_settlement_receipt_sha256=witness.settlement_receipt_sha256,
                request=request,
            )
            self._encoded_locked()
            executor = (
                self._speech_executor
                if request.action.kind == "speech"
                else self._embodiment_executor
            )
        try:
            acknowledgement = executor(request)
        except Exception:
            with self._lock:
                return self._pending_result(
                    self._active, "executor_acknowledgement_pending"
                )
        return self.accept_executor_acknowledgement(acknowledgement)

    def accept_executor_acknowledgement(
        self, acknowledgement: ExecutorAcknowledgement
    ) -> DispatchResult:
        if not isinstance(acknowledgement, ExecutorAcknowledgement):
            raise TypeError("executor acknowledgement must be typed")
        with self._lock:
            active = self._active
            if active is None:
                if (
                    self._latest_terminal is not None
                    and self._latest_terminal.executor_acknowledgement_receipt_sha256
                    == acknowledgement.authority_receipt_sha256
                ):
                    return self._latest_terminal
                raise ValueError("executor acknowledgement has no live request")
            expected_id, key = (
                (self._speech_executor_id, self._speech_executor_key)
                if active.request.action.kind == "speech"
                else (self._embodiment_executor_id, self._embodiment_executor_key)
            )
            acknowledgement.verify(key)
            if (
                acknowledgement.executor_id != expected_id
                or acknowledgement.request_receipt_sha256
                != active.request.authority_receipt_sha256
            ):
                raise ValueError("executor acknowledgement names another request")
            if active.acknowledgement is not None:
                if active.acknowledgement != acknowledgement:
                    raise ValueError("live request received two acknowledgements")
                return self._pending_result(
                    active, "outcome_observation_binding_pending"
                )
            execution = self._cycle.record_execution(
                intent_receipt_sha256=active.request.intent_receipt_sha256,
                executor_receipt_sha256=(
                    acknowledgement.executor_action_receipt_sha256
                ),
                disposition=acknowledgement.disposition,
            )
            if acknowledgement.disposition == "rejected":
                result = DispatchResult(
                    status="rejected",
                    phase="closed",
                    trigger_settlement_receipt_sha256=(
                        active.trigger_settlement_receipt_sha256
                    ),
                    reason="authenticated_executor_rejected",
                    request_receipt_sha256=(
                        active.request.authority_receipt_sha256
                    ),
                    executor_acknowledgement_receipt_sha256=(
                        acknowledgement.authority_receipt_sha256
                    ),
                )
                result.verify()
                self._active = None
                self._latest_terminal = result
                self._encoded_locked()
                return result
            self._active = _ActiveDispatch(
                phase="outcome_observation",
                trigger_settlement_receipt_sha256=(
                    active.trigger_settlement_receipt_sha256
                ),
                request=active.request,
                acknowledgement=acknowledgement,
                execution_receipt_sha256=execution.authority_receipt_sha256,
            )
            self._encoded_locked()
            return self._pending_result(
                self._active, "outcome_observation_binding_pending"
            )

    def bind_outcome_observation(
        self,
        *,
        settlement: CausalExperienceSettlement,
        attestation: OutcomeObservationAttestation,
    ) -> OutcomeObservationBinding:
        witness = PerceptionWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        if not isinstance(attestation, OutcomeObservationAttestation):
            raise TypeError("outcome observation attestation must be typed")
        attestation.verify(self._outcome_observer_key)
        with self._lock:
            active = self._active
            if (
                active is None
                or active.execution_receipt_sha256 is None
                or active.acknowledgement is None
                or active.phase == "executor_acknowledgement"
            ):
                raise ValueError("outcome observation has no live execution")
            if (
                attestation.observer_id != self._outcome_observer_id
                or attestation.execution_receipt_sha256
                != active.execution_receipt_sha256
                or attestation.outcome_settlement_receipt_sha256
                != witness.settlement_receipt_sha256
            ):
                raise ValueError("outcome observation names another causal chain")
            if (
                witness.settlement_receipt_sha256
                == active.trigger_settlement_receipt_sha256
            ):
                raise ValueError("pre-action trigger cannot be its own outcome")
            unsigned = {
                "execution_receipt_sha256": active.execution_receipt_sha256,
                "observer_attestation_receipt_sha256": (
                    attestation.authority_receipt_sha256
                ),
                "outcome_settlement_receipt_sha256": (
                    witness.settlement_receipt_sha256
                ),
                "outcome_structural_fingerprint": witness.structural_fingerprint,
                "schema": OUTCOME_BINDING_SCHEMA,
            }
            binding = OutcomeObservationBinding(
                execution_receipt_sha256=unsigned[
                    "execution_receipt_sha256"
                ],
                outcome_settlement_receipt_sha256=unsigned[
                    "outcome_settlement_receipt_sha256"
                ],
                outcome_structural_fingerprint=unsigned[
                    "outcome_structural_fingerprint"
                ],
                observer_attestation_receipt_sha256=unsigned[
                    "observer_attestation_receipt_sha256"
                ],
                authority_hmac_sha256=_sign(
                    self._key, OUTCOME_BINDING_DOMAIN, unsigned
                ),
            )
            binding.verify(self._key)
            if active.outcome_binding is not None:
                if active.outcome_binding != binding:
                    raise ValueError("live execution received two outcome bindings")
                return active.outcome_binding
            self._active = _ActiveDispatch(
                phase="outcome_bound",
                trigger_settlement_receipt_sha256=(
                    active.trigger_settlement_receipt_sha256
                ),
                request=active.request,
                acknowledgement=active.acknowledgement,
                execution_receipt_sha256=active.execution_receipt_sha256,
                outcome_binding=binding,
            )
            self._encoded_locked()
            return binding

    def close_bound_outcome(
        self,
        *,
        binding: OutcomeObservationBinding,
        settlement: CausalExperienceSettlement,
    ) -> DispatchResult:
        witness = PerceptionWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        if not isinstance(binding, OutcomeObservationBinding):
            raise TypeError("outcome observation binding must be typed")
        binding.verify(self._key)
        with self._lock:
            active = self._active
            if (
                active is None
                or active.outcome_binding != binding
                or active.execution_receipt_sha256
                != binding.execution_receipt_sha256
                or witness.settlement_receipt_sha256
                != binding.outcome_settlement_receipt_sha256
                or witness.structural_fingerprint
                != binding.outcome_structural_fingerprint
            ):
                raise ValueError("only the live exact outcome binding may close")
            if active.cycle_outcome_receipt_sha256 is None:
                outcome = self._cycle.observe_outcome(
                    execution_receipt_sha256=active.execution_receipt_sha256,
                    settlement=settlement,
                )
                active = _ActiveDispatch(
                    phase="cycle_outcome_recorded",
                    trigger_settlement_receipt_sha256=(
                        active.trigger_settlement_receipt_sha256
                    ),
                    request=active.request,
                    acknowledgement=active.acknowledgement,
                    execution_receipt_sha256=active.execution_receipt_sha256,
                    outcome_binding=active.outcome_binding,
                    cycle_outcome_receipt_sha256=(
                        outcome.authority_receipt_sha256
                    ),
                )
                self._active = active
                self._encoded_locked()
            feedback = self._cycle.close_observed(
                outcome_receipt_sha256=active.cycle_outcome_receipt_sha256
            )
            result = DispatchResult(
                status="completed",
                phase="closed",
                trigger_settlement_receipt_sha256=(
                    active.trigger_settlement_receipt_sha256
                ),
                reason="causal_action_cycle_closed",
                request_receipt_sha256=active.request.authority_receipt_sha256,
                execution_receipt_sha256=active.execution_receipt_sha256,
                executor_acknowledgement_receipt_sha256=(
                    active.acknowledgement.authority_receipt_sha256
                ),
                closure_feedback_receipt_sha256=(
                    feedback.authority_receipt_sha256
                ),
            )
            result.verify()
            self._active = None
            self._latest_terminal = result
            self._encoded_locked()
            return result

    def _state_record(self) -> dict[str, object]:
        return {
            "active": self._active.as_record() if self._active is not None else None,
            "latest_terminal": (
                self._latest_terminal.as_record()
                if self._latest_terminal is not None
                else None
            ),
            "limits": {
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
                "max_witness_bytes": self._max_witness_bytes,
            },
            "schema": STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        payload = _canonical(self._state_record())
        if len(payload) > self._max_encoded_state_bytes:
            raise RuntimeError("dispatcher encoded state capacity is full")
        return payload

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded_locked()
        return {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._key, STATE_DOMAIN + payload, hashlib.sha256
            ).hexdigest(),
        }

    def restore_encoded(self, value: object) -> None:
        if (
            not isinstance(value, Mapping)
            or set(value) != {"payload_base64", "schema", "state_hmac_sha256"}
            or value.get("schema") != ENVELOPE_SCHEMA
        ):
            raise ValueError("dispatcher state envelope is malformed")
        try:
            payload = base64.b64decode(value.get("payload_base64"), validate=True)
        except Exception as error:
            raise ValueError("dispatcher state is not canonical base64") from error
        if (
            not payload
            or len(payload) > self._max_encoded_state_bytes
            or base64.b64encode(payload).decode("ascii")
            != value.get("payload_base64")
        ):
            raise ValueError("dispatcher state byte boundary changed")
        expected_hmac = hmac.new(
            self._key, STATE_DOMAIN + payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac, value.get("state_hmac_sha256", "")
        ):
            raise ValueError("dispatcher state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("dispatcher state is invalid") from error
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or set(decoded) != {"active", "latest_terminal", "limits", "schema"}
            or decoded.get("schema") != STATE_SCHEMA
            or decoded.get("limits")
            != {
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
                "max_witness_bytes": self._max_witness_bytes,
            }
        ):
            raise ValueError("dispatcher state fields changed")
        latest = (
            _result_from(decoded["latest_terminal"])
            if decoded["latest_terminal"] is not None
            else None
        )
        active_value = decoded["active"]
        active = None
        if active_value is not None:
            expected = {
                "acknowledgement",
                "cycle_outcome_receipt_sha256",
                "execution_receipt_sha256",
                "outcome_binding",
                "phase",
                "request",
                "schema",
                "trigger_settlement_receipt_sha256",
            }
            if (
                not isinstance(active_value, Mapping)
                or set(active_value) != expected
                or active_value.get("schema") != ACTIVE_SCHEMA
            ):
                raise ValueError("active dispatcher state fields changed")
            request = _request_from(active_value.get("request"), key=self._key)
            acknowledgement_value = active_value.get("acknowledgement")
            executor_key = (
                self._speech_executor_key
                if request.action.kind == "speech"
                else self._embodiment_executor_key
            )
            acknowledgement = (
                _acknowledgement_from(acknowledgement_value, key=executor_key)
                if acknowledgement_value is not None
                else None
            )
            binding_value = active_value.get("outcome_binding")
            binding = (
                _binding_from(binding_value, dispatcher_key=self._key)
                if binding_value is not None
                else None
            )
            active = _ActiveDispatch(
                phase=active_value.get("phase"),
                trigger_settlement_receipt_sha256=active_value.get(
                    "trigger_settlement_receipt_sha256"
                ),
                request=request,
                acknowledgement=acknowledgement,
                execution_receipt_sha256=active_value.get(
                    "execution_receipt_sha256"
                ),
                outcome_binding=binding,
                cycle_outcome_receipt_sha256=active_value.get(
                    "cycle_outcome_receipt_sha256"
                ),
            )
            self._verify_active(active)
        if latest is not None and active is not None:
            if (
                latest.trigger_settlement_receipt_sha256
                == active.trigger_settlement_receipt_sha256
            ):
                raise ValueError("dispatcher terminal and live identities collide")
        with self._lock:
            prior = (self._active, self._latest_terminal)
            self._active, self._latest_terminal = active, latest
            try:
                if self._encoded_locked() != payload:
                    raise ValueError("dispatcher state is not canonical")
            except BaseException:
                self._active, self._latest_terminal = prior
                raise

    def _verify_active(self, active: _ActiveDispatch) -> None:
        if active.phase not in {
            "executor_acknowledgement",
            "outcome_observation",
            "outcome_bound",
            "cycle_outcome_recorded",
        }:
            raise ValueError("active dispatcher phase changed")
        _sha256(active.trigger_settlement_receipt_sha256, "active trigger")
        active.request.verify(self._key)
        if (
            active.request.trigger_settlement_receipt_sha256
            != active.trigger_settlement_receipt_sha256
        ):
            raise ValueError("active request trigger changed")
        if active.phase == "executor_acknowledgement":
            if any(
                value is not None
                for value in (
                    active.acknowledgement,
                    active.execution_receipt_sha256,
                    active.outcome_binding,
                    active.cycle_outcome_receipt_sha256,
                )
            ):
                raise ValueError("pending executor state contains future authority")
            return
        if active.acknowledgement is None or active.execution_receipt_sha256 is None:
            raise ValueError("active execution authority is incomplete")
        expected_id, executor_key = (
            (self._speech_executor_id, self._speech_executor_key)
            if active.request.action.kind == "speech"
            else (self._embodiment_executor_id, self._embodiment_executor_key)
        )
        active.acknowledgement.verify(executor_key)
        if (
            active.acknowledgement.executor_id != expected_id
            or active.acknowledgement.request_receipt_sha256
            != active.request.authority_receipt_sha256
            or active.acknowledgement.disposition != "executed"
            or not self._cycle.verify_live_execution_receipt(
                active.execution_receipt_sha256
            )
        ):
            raise ValueError("active execution lost its authority chain")
        if active.phase == "outcome_observation":
            if (
                active.outcome_binding is not None
                or active.cycle_outcome_receipt_sha256 is not None
            ):
                raise ValueError("unbound outcome state contains future authority")
            return
        if active.outcome_binding is None:
            raise ValueError("active outcome binding is missing")
        active.outcome_binding.verify(self._key)
        if (
            active.outcome_binding.execution_receipt_sha256
            != active.execution_receipt_sha256
        ):
            raise ValueError("active outcome binding names another execution")
        if active.phase == "outcome_bound":
            if active.cycle_outcome_receipt_sha256 is not None:
                raise ValueError("bound outcome contains premature cycle outcome")
        elif active.cycle_outcome_receipt_sha256 is None:
            raise ValueError("recorded cycle outcome receipt is missing")
        else:
            _sha256(active.cycle_outcome_receipt_sha256, "cycle outcome")

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "active": self._active is not None,
                "capacity": 1,
                "encoded_state_bytes": len(self._encoded_locked()),
                "latest_terminal_status": (
                    self._latest_terminal.status
                    if self._latest_terminal is not None
                    else None
                ),
                "phase": self._active.phase if self._active is not None else "idle",
            }


__all__ = (
    "CausalSettlementDispatcher",
    "DispatchResult",
    "ExecutorAcknowledgement",
    "ExecutorRequest",
    "OutcomeObservationAttestation",
    "OutcomeObservationBinding",
    "authenticate_executor_acknowledgement",
    "authenticate_outcome_observation",
)
