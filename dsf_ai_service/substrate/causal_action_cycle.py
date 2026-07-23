"""Bounded modality-neutral causal perception-to-action ownership.

The cycle accepts verified six-sense settlements without flattening their DSF
field.  Exact structural fingerprints are action identity; routing chi values
and source bookkeeping are never identity or meaning.  An action is either
Unicode speech or opaque bytes addressed to an embodiment port.  Embodiment
interpretation and execution remain outside this module and must return an
independent executor receipt.

Teacher relations, intents, executions, outcomes, feedback, and closures are
authenticated.  Completed transactions compact into one latest closure per
binding, so this is not a lifetime action ledger.  An observed outcome can
close neutrally without teacher feedback; explicit confirmation and revocation
remain available.  Rejected executions remove their intent immediately.  The
executor-recording API is trusted-internal and must never be exposed as a
remote request surface.  Every retained collection and byte surface is bounded
and authenticated on persistence.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import receipt_sha256, sha256_digest
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


STATE_SCHEMA = "guala.causal_action_cycle.state.v2"
ENVELOPE_SCHEMA = "guala.causal_action_cycle.hmac.v2"
ACTION_SCHEMA = "guala.causal_action_cycle.action.v1"
TEACHER_SCHEMA = "guala.causal_action_cycle.teacher.v1"
TEACHER_EVIDENCE_SCHEMA = "guala.causal_action_cycle.teacher.v2"
INTENT_SCHEMA = "guala.causal_action_cycle.intent.v1"
EXECUTION_SCHEMA = "guala.causal_action_cycle.execution.v1"
OUTCOME_SCHEMA = "guala.causal_action_cycle.outcome.v1"
FEEDBACK_SCHEMA = "guala.causal_action_cycle.feedback.v1"
CLOSURE_SCHEMA = "guala.causal_action_cycle.closure.v1"
BINDING_SCHEMA = "guala.causal_action_cycle.binding.v2"

STATE_DOMAIN = b"guala-causal-action-cycle-state-v2\0"
TEACHER_DOMAIN = b"guala-causal-action-cycle-teacher-v1\0"
INTENT_DOMAIN = b"guala-causal-action-cycle-intent-v1\0"
EXECUTION_DOMAIN = b"guala-causal-action-cycle-execution-v1\0"
OUTCOME_DOMAIN = b"guala-causal-action-cycle-outcome-v1\0"
FEEDBACK_DOMAIN = b"guala-causal-action-cycle-feedback-v1\0"
CLOSURE_DOMAIN = b"guala-causal-action-cycle-closure-v1\0"

DEFAULT_WORKING_CAPACITY = 8
DEFAULT_EVIDENCE_CAPACITY = 128
DEFAULT_BINDING_CAPACITY = 64
DEFAULT_TRANSACTION_CAPACITY = 128
DEFAULT_MAX_WITNESS_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_COMMAND_BYTES = 4096
DEFAULT_MAX_SPEECH_SCALARS = 512
DEFAULT_ENCODED_STATE_BYTES = 32 * 1024 * 1024
MAX_IDENTIFIER_BYTES = 256


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


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("causal action cycle key must be bytes or text")
    if not result:
        raise ValueError("causal action cycle key is required")
    return result


def _sign(key: bytes, domain: bytes, payload: bytes) -> str:
    return hmac.new(key, domain + payload, hashlib.sha256).hexdigest()


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _nonce(value: object, name: str) -> str:
    result = _identifier(value, name)
    if len(result) < 16:
        raise ValueError(f"{name} must carry at least 16 characters")
    return result


def _signed_receipt(payload: Mapping[str, object], signature: str) -> str:
    sha256_digest(signature, "authority HMAC")
    return _digest({"authority_hmac_sha256": signature, "payload": dict(payload)})


def _verify_signed(
    *,
    key: bytes,
    domain: bytes,
    payload: Mapping[str, object],
    identity: str,
    signature: str,
    name: str,
) -> None:
    encoded = _canonical(payload)
    if receipt_sha256(encoded) != sha256_digest(identity, f"{name} identity"):
        raise ValueError(f"{name} identity changed")
    expected = _sign(key, domain, encoded)
    if not hmac.compare_digest(expected, signature):
        raise ValueError(f"{name} HMAC changed")


@dataclass(frozen=True, slots=True)
class ActionCommand:
    kind: str
    unicode_scalars: tuple[int, ...] = ()
    port_id: str | None = None
    command_payload: bytes = b""

    @classmethod
    def speech(cls, text: str) -> "ActionCommand":
        if not isinstance(text, str) or not text:
            raise ValueError("speech action requires nonempty text")
        return cls(kind="speech", unicode_scalars=tuple(ord(item) for item in text))

    @classmethod
    def embodiment(cls, port_id: str, payload: bytes) -> "ActionCommand":
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("embodiment action requires exact command bytes")
        return cls(
            kind="embodiment_port",
            port_id=_identifier(port_id, "embodiment port"),
            command_payload=payload,
        )

    def verify(self, *, max_scalars: int, max_command_bytes: int) -> None:
        if self.kind == "speech":
            if (
                not self.unicode_scalars
                or len(self.unicode_scalars) > max_scalars
                or self.port_id is not None
                or self.command_payload
                or any(
                    isinstance(item, bool)
                    or not isinstance(item, int)
                    or item < 0
                    or item > 0x10FFFF
                    or 0xD800 <= item <= 0xDFFF
                    for item in self.unicode_scalars
                )
            ):
                raise ValueError("speech action is outside its exact boundary")
            return
        if self.kind == "embodiment_port":
            _identifier(self.port_id, "embodiment port")
            if (
                self.unicode_scalars
                or not isinstance(self.command_payload, bytes)
                or not self.command_payload
                or len(self.command_payload) > max_command_bytes
            ):
                raise ValueError("embodiment command exceeds its exact byte boundary")
            return
        raise ValueError("action must be speech or embodiment_port")

    def as_record(self) -> dict[str, object]:
        return {
            "command_payload_base64": base64.b64encode(
                self.command_payload
            ).decode("ascii"),
            "kind": self.kind,
            "port_id": self.port_id,
            "schema": ACTION_SCHEMA,
            "unicode_scalars": list(self.unicode_scalars),
        }

    @property
    def authority_receipt_sha256(self) -> str:
        return _digest(self.as_record())


def _action_from(
    value: object, *, max_scalars: int, max_command_bytes: int
) -> ActionCommand:
    expected = {
        "command_payload_base64",
        "kind",
        "port_id",
        "schema",
        "unicode_scalars",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != ACTION_SCHEMA
    ):
        raise ValueError("action record fields changed")
    try:
        payload = base64.b64decode(value.get("command_payload_base64"), validate=True)
    except Exception as error:
        raise ValueError("action payload is not canonical base64") from error
    action = ActionCommand(
        kind=value.get("kind"),
        unicode_scalars=tuple(value.get("unicode_scalars") or ()),
        port_id=value.get("port_id"),
        command_payload=payload,
    )
    action.verify(max_scalars=max_scalars, max_command_bytes=max_command_bytes)
    if action.as_record() != dict(value):
        raise ValueError("action record is not canonical")
    return action


def _payload_structure(decoded: Mapping[str, object]) -> str:
    interpretations = decoded.get("interpretations")
    language_events = decoded.get("language_events")
    expected_senses = tuple(item.value for item in SENSE_ORDER)
    if (
        not isinstance(interpretations, list)
        or len(interpretations) != len(expected_senses)
        or any(not isinstance(item, Mapping) for item in interpretations)
        or tuple(item.get("sense") for item in interpretations) != expected_senses
        or not isinstance(language_events, list)
    ):
        raise ValueError("perception witness lost canonical six-sense structure")
    language_identity = []
    for item in language_events:
        if not isinstance(item, Mapping):
            raise ValueError("perception witness language event changed")
        occurrence = item.get("recognition_occurrence")
        selected = (
            occurrence.get("selected_class_authority_receipt_sha256")
            if isinstance(occurrence, Mapping)
            else None
        )
        language_identity.append({
            "form": item.get("form"),
            "recognition_class_authority_receipt_sha256": selected,
            "unicode_scalars": item.get("unicode_scalars"),
        })
    return _digest({
        "interpretations": {
            item["sense"]: {
                "state": item.get("state"),
                "structural_fingerprint": item.get("structural_fingerprint"),
            }
            for item in interpretations
        },
        "language_events": language_identity,
    })


@dataclass(frozen=True, slots=True)
class PerceptionWitness:
    event_id: str
    settlement_receipt_sha256: str
    structural_fingerprint: str
    settlement_payload_base64: str

    @classmethod
    def from_settlement(
        cls, settlement: CausalExperienceSettlement, *, max_bytes: int
    ) -> "PerceptionWitness":
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("causal action cycle requires an exact causal settlement")
        settlement.verify()
        payload = settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "causal action cycle settlement",
        )
        if len(payload) > max_bytes:
            raise RuntimeError("causal action perception exceeds its byte boundary")
        witness = cls(
            event_id=settlement.event_id,
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            structural_fingerprint=settlement.structural_fingerprint,
            settlement_payload_base64=base64.b64encode(payload).decode("ascii"),
        )
        witness.verify(max_bytes=max_bytes)
        return witness

    def verify(self, *, max_bytes: int) -> None:
        sha256_digest(self.event_id, "perception event")
        sha256_digest(self.settlement_receipt_sha256, "perception settlement")
        sha256_digest(self.structural_fingerprint, "perception structure")
        try:
            payload = base64.b64decode(self.settlement_payload_base64, validate=True)
        except Exception as error:
            raise ValueError("perception witness is not canonical base64") from error
        if (
            not payload
            or len(payload) > max_bytes
            or receipt_sha256(payload) != self.settlement_receipt_sha256
            or base64.b64encode(payload).decode("ascii")
            != self.settlement_payload_base64
        ):
            raise ValueError("perception witness receipt changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("perception witness payload is invalid") from error
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or decoded.get("event_id") != self.event_id
            or decoded.get("structural_fingerprint") != self.structural_fingerprint
            or _payload_structure(decoded) != self.structural_fingerprint
        ):
            raise ValueError("perception witness structural identity changed")

    def as_record(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "settlement_payload_base64": self.settlement_payload_base64,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "structural_fingerprint": self.structural_fingerprint,
        }


def _witness_from(value: object, *, max_bytes: int) -> PerceptionWitness:
    expected = {
        "event_id",
        "settlement_payload_base64",
        "settlement_receipt_sha256",
        "structural_fingerprint",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("perception witness fields changed")
    witness = PerceptionWitness(**dict(value))
    witness.verify(max_bytes=max_bytes)
    return witness


def _witness_language_source_event(witness: PerceptionWitness) -> str | None:
    payload = base64.b64decode(
        witness.settlement_payload_base64, validate=True
    )
    decoded = json.loads(payload.decode("utf-8"))
    language_events = decoded.get("language_events")
    if not language_events:
        return None
    if not isinstance(language_events, list) or len(language_events) != 1:
        raise ValueError("perception witness language source changed")
    source_event_id = language_events[0].get("source_event_id")
    return sha256_digest(source_event_id, "language source event")


@dataclass(frozen=True, slots=True)
class TeacherRelation:
    trigger_settlement_receipt_sha256: str
    trigger_structural_fingerprint: str
    action_receipt_sha256: str
    source: str
    nonce: str
    authority_hmac_sha256: str
    teaching_evidence_receipt_sha256: str | None = None

    def payload(self) -> dict[str, object]:
        payload = {
            "action_receipt_sha256": self.action_receipt_sha256,
            "nonce": self.nonce,
            "schema": (
                TEACHER_EVIDENCE_SCHEMA
                if self.teaching_evidence_receipt_sha256 is not None
                else TEACHER_SCHEMA
            ),
            "source": self.source,
            "trigger_settlement_receipt_sha256": (
                self.trigger_settlement_receipt_sha256
            ),
            "trigger_structural_fingerprint": self.trigger_structural_fingerprint,
        }
        if self.teaching_evidence_receipt_sha256 is not None:
            payload["teaching_evidence_receipt_sha256"] = (
                self.teaching_evidence_receipt_sha256
            )
        return payload

    @property
    def relation_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    def verify(self, key: bytes) -> None:
        sha256_digest(self.trigger_settlement_receipt_sha256, "teacher trigger")
        sha256_digest(self.trigger_structural_fingerprint, "teacher structure")
        sha256_digest(self.action_receipt_sha256, "teacher action")
        _identifier(self.source, "teacher source")
        _nonce(self.nonce, "teacher nonce")
        if self.teaching_evidence_receipt_sha256 is not None:
            sha256_digest(
                self.teaching_evidence_receipt_sha256,
                "teacher evidence receipt",
            )
        _verify_signed(
            key=key,
            domain=TEACHER_DOMAIN,
            payload=self.payload(),
            identity=self.relation_id,
            signature=self.authority_hmac_sha256,
            name="teacher relation",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _teacher_from(value: object, *, key: bytes) -> TeacherRelation:
    v1_fields = {
        "action_receipt_sha256",
        "authority_hmac_sha256",
        "nonce",
        "schema",
        "source",
        "trigger_settlement_receipt_sha256",
        "trigger_structural_fingerprint",
    }
    v2_fields = v1_fields | {"teaching_evidence_receipt_sha256"}
    if (
        not isinstance(value, Mapping)
        or (
            value.get("schema") == TEACHER_SCHEMA
            and set(value) != v1_fields
        )
        or (
            value.get("schema") == TEACHER_EVIDENCE_SCHEMA
            and set(value) != v2_fields
        )
        or value.get("schema") not in {
            TEACHER_SCHEMA,
            TEACHER_EVIDENCE_SCHEMA,
        }
    ):
        raise ValueError("teacher relation fields changed")
    relation = TeacherRelation(
        trigger_settlement_receipt_sha256=value.get(
            "trigger_settlement_receipt_sha256"
        ),
        trigger_structural_fingerprint=value.get("trigger_structural_fingerprint"),
        action_receipt_sha256=value.get("action_receipt_sha256"),
        source=value.get("source"),
        nonce=value.get("nonce"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
        teaching_evidence_receipt_sha256=value.get(
            "teaching_evidence_receipt_sha256"
        ),
    )
    relation.verify(key)
    return relation


@dataclass(frozen=True, slots=True)
class ActionIntent:
    binding_id: str
    trigger_settlement_receipt_sha256: str
    trigger_structural_fingerprint: str
    action: ActionCommand
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action": self.action.as_record(),
            "binding_id": self.binding_id,
            "schema": INTENT_SCHEMA,
            "trigger_settlement_receipt_sha256": (
                self.trigger_settlement_receipt_sha256
            ),
            "trigger_structural_fingerprint": self.trigger_structural_fingerprint,
        }

    @property
    def intent_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes, *, max_scalars: int, max_command_bytes: int) -> None:
        self.action.verify(
            max_scalars=max_scalars, max_command_bytes=max_command_bytes
        )
        sha256_digest(self.binding_id, "intent binding")
        sha256_digest(self.trigger_settlement_receipt_sha256, "intent trigger")
        sha256_digest(self.trigger_structural_fingerprint, "intent structure")
        _verify_signed(
            key=key,
            domain=INTENT_DOMAIN,
            payload=self.payload(),
            identity=self.intent_id,
            signature=self.authority_hmac_sha256,
            name="action intent",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


@dataclass(frozen=True, slots=True)
class ActionExecution:
    intent_receipt_sha256: str
    executor_receipt_sha256: str
    disposition: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "executor_receipt_sha256": self.executor_receipt_sha256,
            "intent_receipt_sha256": self.intent_receipt_sha256,
            "schema": EXECUTION_SCHEMA,
        }

    @property
    def execution_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        if self.disposition not in {"executed", "rejected"}:
            raise ValueError("execution disposition changed")
        sha256_digest(self.intent_receipt_sha256, "execution intent")
        sha256_digest(self.executor_receipt_sha256, "external executor")
        _verify_signed(
            key=key,
            domain=EXECUTION_DOMAIN,
            payload=self.payload(),
            identity=self.execution_id,
            signature=self.authority_hmac_sha256,
            name="action execution",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


@dataclass(frozen=True, slots=True)
class ActionOutcome:
    execution_receipt_sha256: str
    outcome_settlement_receipt_sha256: str
    outcome_structural_fingerprint: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "outcome_settlement_receipt_sha256": (
                self.outcome_settlement_receipt_sha256
            ),
            "outcome_structural_fingerprint": self.outcome_structural_fingerprint,
            "schema": OUTCOME_SCHEMA,
        }

    @property
    def outcome_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        sha256_digest(self.execution_receipt_sha256, "outcome execution")
        sha256_digest(self.outcome_settlement_receipt_sha256, "outcome settlement")
        sha256_digest(self.outcome_structural_fingerprint, "outcome structure")
        _verify_signed(
            key=key,
            domain=OUTCOME_DOMAIN,
            payload=self.payload(),
            identity=self.outcome_id,
            signature=self.authority_hmac_sha256,
            name="action outcome",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


@dataclass(frozen=True, slots=True)
class ActionFeedback:
    outcome_receipt_sha256: str
    binding_id: str
    decision: str
    resulting_binding_status: str
    source: str
    nonce: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "decision": self.decision,
            "nonce": self.nonce,
            "outcome_receipt_sha256": self.outcome_receipt_sha256,
            "resulting_binding_status": self.resulting_binding_status,
            "schema": FEEDBACK_SCHEMA,
            "source": self.source,
        }

    @property
    def feedback_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(self, key: bytes) -> None:
        if self.decision not in {"observe", "confirm", "revoke"}:
            raise ValueError("feedback decision changed")
        if (
            self.resulting_binding_status
            not in {"provisional", "confirmed", "revoked"}
            or (
                self.decision == "confirm"
                and self.resulting_binding_status != "confirmed"
            )
            or (
                self.decision == "revoke"
                and self.resulting_binding_status != "revoked"
            )
            or (
                self.decision == "observe"
                and self.resulting_binding_status == "revoked"
            )
        ):
            raise ValueError("feedback resulting binding status changed")
        sha256_digest(self.outcome_receipt_sha256, "feedback outcome")
        sha256_digest(self.binding_id, "feedback binding")
        _identifier(self.source, "feedback source")
        _nonce(self.nonce, "feedback nonce")
        _verify_signed(
            key=key,
            domain=FEEDBACK_DOMAIN,
            payload=self.payload(),
            identity=self.feedback_id,
            signature=self.authority_hmac_sha256,
            name="action feedback",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _intent_from(
    value: object, *, key: bytes, max_scalars: int, max_command_bytes: int
) -> ActionIntent:
    expected = {
        "action",
        "authority_hmac_sha256",
        "binding_id",
        "schema",
        "trigger_settlement_receipt_sha256",
        "trigger_structural_fingerprint",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("intent fields changed")
    item = ActionIntent(
        binding_id=value.get("binding_id"),
        trigger_settlement_receipt_sha256=value.get(
            "trigger_settlement_receipt_sha256"
        ),
        trigger_structural_fingerprint=value.get("trigger_structural_fingerprint"),
        action=_action_from(
            value.get("action"),
            max_scalars=max_scalars,
            max_command_bytes=max_command_bytes,
        ),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    item.verify(key, max_scalars=max_scalars, max_command_bytes=max_command_bytes)
    return item


def _execution_from(value: object, *, key: bytes) -> ActionExecution:
    expected = {
        "authority_hmac_sha256",
        "disposition",
        "executor_receipt_sha256",
        "intent_receipt_sha256",
        "schema",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("execution fields changed")
    item = ActionExecution(
        intent_receipt_sha256=value.get("intent_receipt_sha256"),
        executor_receipt_sha256=value.get("executor_receipt_sha256"),
        disposition=value.get("disposition"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    item.verify(key)
    return item


def _outcome_from(value: object, *, key: bytes) -> ActionOutcome:
    expected = {
        "authority_hmac_sha256",
        "execution_receipt_sha256",
        "outcome_settlement_receipt_sha256",
        "outcome_structural_fingerprint",
        "schema",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("outcome fields changed")
    item = ActionOutcome(
        execution_receipt_sha256=value.get("execution_receipt_sha256"),
        outcome_settlement_receipt_sha256=value.get(
            "outcome_settlement_receipt_sha256"
        ),
        outcome_structural_fingerprint=value.get("outcome_structural_fingerprint"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    item.verify(key)
    return item


def _feedback_from(value: object, *, key: bytes) -> ActionFeedback:
    expected = {
        "authority_hmac_sha256",
        "binding_id",
        "decision",
        "nonce",
        "outcome_receipt_sha256",
        "resulting_binding_status",
        "schema",
        "source",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("feedback fields changed")
    item = ActionFeedback(
        outcome_receipt_sha256=value.get("outcome_receipt_sha256"),
        binding_id=value.get("binding_id"),
        decision=value.get("decision"),
        resulting_binding_status=value.get("resulting_binding_status"),
        source=value.get("source"),
        nonce=value.get("nonce"),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    item.verify(key)
    return item


@dataclass(frozen=True, slots=True)
class ActionClosure:
    intent: ActionIntent
    execution: ActionExecution
    outcome: ActionOutcome
    feedback: ActionFeedback
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "execution": self.execution.as_record(),
            "feedback": self.feedback.as_record(),
            "intent": self.intent.as_record(),
            "outcome": self.outcome.as_record(),
            "schema": CLOSURE_SCHEMA,
        }

    @property
    def closure_id(self) -> str:
        return receipt_sha256(_canonical(self.payload()))

    @property
    def authority_receipt_sha256(self) -> str:
        return _signed_receipt(self.payload(), self.authority_hmac_sha256)

    def verify(
        self, key: bytes, *, max_scalars: int, max_command_bytes: int
    ) -> None:
        self.intent.verify(
            key, max_scalars=max_scalars, max_command_bytes=max_command_bytes
        )
        self.execution.verify(key)
        self.outcome.verify(key)
        self.feedback.verify(key)
        if (
            self.execution.disposition != "executed"
            or self.execution.intent_receipt_sha256
            != self.intent.authority_receipt_sha256
            or self.outcome.execution_receipt_sha256
            != self.execution.authority_receipt_sha256
            or self.feedback.outcome_receipt_sha256
            != self.outcome.authority_receipt_sha256
            or self.feedback.binding_id != self.intent.binding_id
        ):
            raise ValueError("action closure authority chain changed")
        _verify_signed(
            key=key,
            domain=CLOSURE_DOMAIN,
            payload=self.payload(),
            identity=self.closure_id,
            signature=self.authority_hmac_sha256,
            name="action closure",
        )

    def as_record(self) -> dict[str, object]:
        return {**self.payload(), "authority_hmac_sha256": self.authority_hmac_sha256}


def _closure_from(
    value: object, *, key: bytes, max_scalars: int, max_command_bytes: int
) -> ActionClosure:
    expected = {
        "authority_hmac_sha256",
        "execution",
        "feedback",
        "intent",
        "outcome",
        "schema",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("closure fields changed")
    closure = ActionClosure(
        intent=_intent_from(
            value.get("intent"),
            key=key,
            max_scalars=max_scalars,
            max_command_bytes=max_command_bytes,
        ),
        execution=_execution_from(value.get("execution"), key=key),
        outcome=_outcome_from(value.get("outcome"), key=key),
        feedback=_feedback_from(value.get("feedback"), key=key),
        authority_hmac_sha256=value.get("authority_hmac_sha256"),
    )
    closure.verify(
        key, max_scalars=max_scalars, max_command_bytes=max_command_bytes
    )
    return closure


@dataclass(frozen=True, slots=True)
class ActionBinding:
    binding_id: str
    trigger_witness_receipt_sha256: str
    trigger_structural_fingerprint: str
    action: ActionCommand
    teacher_relation: TeacherRelation
    status: str = "provisional"
    latest_closure: ActionClosure | None = None

    def verify(
        self, key: bytes, *, max_scalars: int, max_command_bytes: int
    ) -> None:
        self.action.verify(
            max_scalars=max_scalars, max_command_bytes=max_command_bytes
        )
        self.teacher_relation.verify(key)
        expected_id = _digest({
            "action_receipt_sha256": self.action.authority_receipt_sha256,
            "schema": "guala.causal_action_cycle.semantic_relation.v1",
            "trigger_structural_fingerprint": self.trigger_structural_fingerprint,
        })
        if (
            self.binding_id != expected_id
            or self.teacher_relation.trigger_settlement_receipt_sha256
            != self.trigger_witness_receipt_sha256
            or self.teacher_relation.trigger_structural_fingerprint
            != self.trigger_structural_fingerprint
            or self.teacher_relation.action_receipt_sha256
            != self.action.authority_receipt_sha256
            or self.status not in {"provisional", "confirmed", "revoked"}
        ):
            raise ValueError("action binding evidence changed")
        if self.latest_closure is None:
            if self.status != "provisional":
                raise ValueError("action binding status lacks closure authority")
            return
        self.latest_closure.verify(
            key, max_scalars=max_scalars, max_command_bytes=max_command_bytes
        )
        expected_status = self.latest_closure.feedback.resulting_binding_status
        if (
            self.status != expected_status
            or self.latest_closure.intent.binding_id != self.binding_id
            or self.latest_closure.intent.action != self.action
            or self.latest_closure.intent.trigger_structural_fingerprint
            != self.trigger_structural_fingerprint
        ):
            raise ValueError("action binding closure changed")

    def as_record(self) -> dict[str, object]:
        return {
            "action": self.action.as_record(),
            "binding_id": self.binding_id,
            "latest_closure": (
                self.latest_closure.as_record()
                if self.latest_closure is not None
                else None
            ),
            "schema": BINDING_SCHEMA,
            "status": self.status,
            "teacher_relation": self.teacher_relation.as_record(),
            "trigger_structural_fingerprint": self.trigger_structural_fingerprint,
            "trigger_witness_receipt_sha256": self.trigger_witness_receipt_sha256,
        }


def _binding_from(
    value: object, *, key: bytes, max_scalars: int, max_command_bytes: int
) -> ActionBinding:
    expected = {
        "action",
        "binding_id",
        "latest_closure",
        "schema",
        "status",
        "teacher_relation",
        "trigger_structural_fingerprint",
        "trigger_witness_receipt_sha256",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != BINDING_SCHEMA
    ):
        raise ValueError("binding fields changed")
    raw_closure = value.get("latest_closure")
    binding = ActionBinding(
        binding_id=value.get("binding_id"),
        trigger_witness_receipt_sha256=value.get(
            "trigger_witness_receipt_sha256"
        ),
        trigger_structural_fingerprint=value.get("trigger_structural_fingerprint"),
        action=_action_from(
            value.get("action"),
            max_scalars=max_scalars,
            max_command_bytes=max_command_bytes,
        ),
        teacher_relation=_teacher_from(value.get("teacher_relation"), key=key),
        status=value.get("status"),
        latest_closure=(
            _closure_from(
                raw_closure,
                key=key,
                max_scalars=max_scalars,
                max_command_bytes=max_command_bytes,
            )
            if raw_closure is not None
            else None
        ),
    )
    binding.verify(
        key, max_scalars=max_scalars, max_command_bytes=max_command_bytes
    )
    return binding


@dataclass(frozen=True, slots=True)
class ActionSelection:
    status: str
    intent: ActionIntent | None = None
    stop_reason: str | None = None

    def __post_init__(self) -> None:
        if self.status == "committed":
            if self.intent is None or self.stop_reason is not None:
                raise ValueError("committed selection lost its intent")
        elif self.status in {"unknown", "ambiguous"}:
            if self.intent is not None or self.stop_reason != f"causal_action_{self.status}":
                raise ValueError("silent selection exposed an intent")
        else:
            raise ValueError("selection status changed")


@dataclass(frozen=True, slots=True)
class VerifiedActionRelationEvidence:
    """Read-only, reverified evidence for one learned action relation."""

    binding_id: str
    status: str
    trigger_witness: PerceptionWitness
    action: ActionCommand
    latest_closure_receipt_sha256: str | None
    outcome_witness: PerceptionWitness | None


class CausalActionCycle:
    """One serial, bounded owner for perception-to-action transactions."""

    def __init__(
        self,
        *,
        authority_key: object,
        log_event: Callable[..., None] | None = None,
        working_capacity: int = DEFAULT_WORKING_CAPACITY,
        evidence_capacity: int = DEFAULT_EVIDENCE_CAPACITY,
        binding_capacity: int = DEFAULT_BINDING_CAPACITY,
        transaction_capacity: int = DEFAULT_TRANSACTION_CAPACITY,
        max_witness_bytes: int = DEFAULT_MAX_WITNESS_BYTES,
        max_command_bytes: int = DEFAULT_MAX_COMMAND_BYTES,
        max_speech_scalars: int = DEFAULT_MAX_SPEECH_SCALARS,
        encoded_state_capacity: int = DEFAULT_ENCODED_STATE_BYTES,
    ) -> None:
        values = (
            working_capacity,
            evidence_capacity,
            binding_capacity,
            transaction_capacity,
            max_witness_bytes,
            max_command_bytes,
            max_speech_scalars,
            encoded_state_capacity,
        )
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item <= 0
            for item in values
        ):
            raise ValueError("causal action cycle capacities must be positive")
        self._key = _key(authority_key)
        self._log = log_event or (lambda *_args, **_kwargs: None)
        self._working_capacity = working_capacity
        self._evidence_capacity = evidence_capacity
        self._binding_capacity = binding_capacity
        self._transaction_capacity = transaction_capacity
        self._max_witness_bytes = max_witness_bytes
        self._max_command_bytes = max_command_bytes
        self._max_speech_scalars = max_speech_scalars
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._working: OrderedDict[str, PerceptionWitness] = OrderedDict()
        self._working_by_receipt: dict[str, str] = {}
        self._working_by_source_event: dict[str, str] = {}
        self._evidence: dict[str, PerceptionWitness] = {}
        self._bindings: dict[str, ActionBinding] = {}
        self._by_structure: dict[str, set[str]] = {}
        self._intents: OrderedDict[str, ActionIntent] = OrderedDict()
        self._executions: OrderedDict[str, ActionExecution] = OrderedDict()
        self._outcomes: OrderedDict[str, ActionOutcome] = OrderedDict()

    def _emit(self, name: str, **fields: object) -> None:
        try:
            self._log(name, **fields)
        except Exception:
            pass

    def _capacities(self) -> dict[str, int]:
        return {
            "binding_capacity": self._binding_capacity,
            "encoded_state_capacity": self._encoded_state_capacity,
            "evidence_capacity": self._evidence_capacity,
            "max_command_bytes": self._max_command_bytes,
            "max_speech_scalars": self._max_speech_scalars,
            "max_witness_bytes": self._max_witness_bytes,
            "transaction_capacity": self._transaction_capacity,
            "working_capacity": self._working_capacity,
        }

    def _state(self) -> dict[str, object]:
        return {
            "bindings": [
                self._bindings[key].as_record() for key in sorted(self._bindings)
            ],
            "capacities": self._capacities(),
            "evidence": [
                self._evidence[key].as_record() for key in sorted(self._evidence)
            ],
            "executions": [
                self._executions[key].as_record() for key in sorted(self._executions)
            ],
            "intents": [
                self._intents[key].as_record() for key in sorted(self._intents)
            ],
            "outcomes": [
                self._outcomes[key].as_record() for key in sorted(self._outcomes)
            ],
            "schema": STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        payload = _canonical(self._state())
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError("causal action encoded state capacity is full")
        return payload

    @contextmanager
    def _atomic(self):
        prior = (
            dict(self._evidence),
            dict(self._bindings),
            {key: set(value) for key, value in self._by_structure.items()},
            OrderedDict(self._intents),
            OrderedDict(self._executions),
            OrderedDict(self._outcomes),
        )
        try:
            yield
            self._encoded_locked()
        except BaseException:
            (
                self._evidence,
                self._bindings,
                self._by_structure,
                self._intents,
                self._executions,
                self._outcomes,
            ) = prior
            raise

    def _gc_evidence_locked(self) -> None:
        required = set()
        for binding in self._bindings.values():
            required.add(binding.trigger_witness_receipt_sha256)
            if binding.latest_closure is not None:
                required.add(
                    binding.latest_closure.intent.trigger_settlement_receipt_sha256
                )
                required.add(
                    binding.latest_closure.outcome.outcome_settlement_receipt_sha256
                )
        for intent in self._intents.values():
            required.add(intent.trigger_settlement_receipt_sha256)
        for outcome in self._outcomes.values():
            required.add(outcome.outcome_settlement_receipt_sha256)
        self._evidence = {
            receipt: witness
            for receipt, witness in self._evidence.items()
            if receipt in required
        }

    def _retain_evidence_locked(self, witness: PerceptionWitness) -> None:
        receipt = witness.settlement_receipt_sha256
        existing = self._evidence.get(receipt)
        if existing is not None and existing != witness:
            raise ValueError("perception evidence receipt changed")
        self._evidence[receipt] = witness
        if len(self._evidence) > self._evidence_capacity:
            raise RuntimeError("causal action evidence capacity is full")

    def accept(self, settlement: CausalExperienceSettlement) -> PerceptionWitness:
        witness = PerceptionWitness.from_settlement(
            settlement, max_bytes=self._max_witness_bytes
        )
        expired = None
        with self._lock:
            known_event = self._working_by_receipt.get(
                witness.settlement_receipt_sha256
            )
            if known_event is not None:
                known = self._working[known_event]
                if known != witness:
                    raise ValueError("perception receipt was offered differently")
                self._working.move_to_end(known_event)
                return known
            if witness.event_id in self._working:
                raise ValueError("perception event was offered differently")
            source_event_id = _witness_language_source_event(witness)
            if (
                source_event_id is not None
                and source_event_id in self._working_by_source_event
            ):
                raise ValueError(
                    "language source event was offered as two perceptions"
                )
            if len(self._working) >= self._working_capacity:
                expired, old = self._working.popitem(last=False)
                del self._working_by_receipt[old.settlement_receipt_sha256]
                old_source_event = _witness_language_source_event(old)
                if old_source_event is not None:
                    del self._working_by_source_event[old_source_event]
            self._working[witness.event_id] = witness
            self._working_by_receipt[witness.settlement_receipt_sha256] = witness.event_id
            if source_event_id is not None:
                self._working_by_source_event[source_event_id] = witness.event_id
        self._emit(
            "causal_action_cycle_perception_accepted",
            event_id=witness.event_id,
            structural_fingerprint=witness.structural_fingerprint,
            expired_event_id=expired,
        )
        return witness

    def _working_witness(self, reference: str) -> PerceptionWitness:
        with self._lock:
            witness = self._working.get(reference)
            if witness is None:
                event = self._working_by_receipt.get(reference)
                witness = self._working.get(event) if event else None
            if witness is None:
                event = self._working_by_source_event.get(reference)
                witness = self._working.get(event) if event else None
            if witness is None:
                raise ValueError("causal perception is no longer in working memory")
            return witness

    def perception_record(self, reference: str) -> dict[str, object]:
        """Return a verified decoded copy of one bounded working perception."""
        witness = self._working_witness(reference)
        witness.verify(max_bytes=self._max_witness_bytes)
        payload = base64.b64decode(
            witness.settlement_payload_base64, validate=True
        )
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, dict) or _canonical(decoded) != payload:
            raise ValueError("working perception record is not canonical")
        return decoded

    def issue_teacher_relation(
        self,
        *,
        trigger_reference: str,
        action: ActionCommand,
        source: str,
        nonce: str,
        teaching_evidence_receipt_sha256: str | None = None,
    ) -> TeacherRelation:
        witness = self._working_witness(trigger_reference)
        action.verify(
            max_scalars=self._max_speech_scalars,
            max_command_bytes=self._max_command_bytes,
        )
        _identifier(source, "teacher source")
        _nonce(nonce, "teacher nonce")
        if teaching_evidence_receipt_sha256 is not None:
            sha256_digest(
                teaching_evidence_receipt_sha256,
                "teacher evidence receipt",
            )
        with self._lock:
            if any(
                item.teacher_relation.nonce == nonce
                for item in self._bindings.values()
            ):
                raise ValueError("teacher nonce was already used")
        schema = (
            TEACHER_EVIDENCE_SCHEMA
            if teaching_evidence_receipt_sha256 is not None
            else TEACHER_SCHEMA
        )
        unsigned = {
            "action_receipt_sha256": action.authority_receipt_sha256,
            "nonce": nonce,
            "schema": schema,
            "source": source,
            "trigger_settlement_receipt_sha256": witness.settlement_receipt_sha256,
            "trigger_structural_fingerprint": witness.structural_fingerprint,
        }
        if teaching_evidence_receipt_sha256 is not None:
            unsigned["teaching_evidence_receipt_sha256"] = (
                teaching_evidence_receipt_sha256
            )
        relation = TeacherRelation(
            trigger_settlement_receipt_sha256=witness.settlement_receipt_sha256,
            trigger_structural_fingerprint=witness.structural_fingerprint,
            action_receipt_sha256=action.authority_receipt_sha256,
            source=source,
            nonce=nonce,
            authority_hmac_sha256=_sign(
                self._key, TEACHER_DOMAIN, _canonical(unsigned)
            ),
            teaching_evidence_receipt_sha256=(
                teaching_evidence_receipt_sha256
            ),
        )
        relation.verify(self._key)
        return relation

    def learn(
        self,
        *,
        trigger_reference: str,
        action: ActionCommand,
        teacher_relation: TeacherRelation,
    ) -> ActionBinding:
        witness = self._working_witness(trigger_reference)
        action.verify(
            max_scalars=self._max_speech_scalars,
            max_command_bytes=self._max_command_bytes,
        )
        teacher_relation.verify(self._key)
        if (
            teacher_relation.trigger_settlement_receipt_sha256
            != witness.settlement_receipt_sha256
            or teacher_relation.trigger_structural_fingerprint
            != witness.structural_fingerprint
            or teacher_relation.action_receipt_sha256
            != action.authority_receipt_sha256
        ):
            raise ValueError("teacher relation names different causal evidence")
        binding_id = _digest({
            "action_receipt_sha256": action.authority_receipt_sha256,
            "schema": "guala.causal_action_cycle.semantic_relation.v1",
            "trigger_structural_fingerprint": witness.structural_fingerprint,
        })
        with self._lock:
            for prior in self._bindings.values():
                if prior.teacher_relation.nonce == teacher_relation.nonce:
                    if (
                        prior.binding_id == binding_id
                        and prior.teacher_relation == teacher_relation
                    ):
                        return prior
                    raise ValueError("teacher nonce was already used")
            if len(self._bindings) >= self._binding_capacity:
                raise RuntimeError("causal action binding capacity is full")
            binding = ActionBinding(
                binding_id=binding_id,
                trigger_witness_receipt_sha256=witness.settlement_receipt_sha256,
                trigger_structural_fingerprint=witness.structural_fingerprint,
                action=action,
                teacher_relation=teacher_relation,
            )
            binding.verify(
                self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            with self._atomic():
                self._retain_evidence_locked(witness)
                self._bindings[binding_id] = binding
                self._by_structure.setdefault(
                    witness.structural_fingerprint, set()
                ).add(binding_id)
        self._emit("causal_action_cycle_learned", binding_id=binding_id)
        return binding

    def teach(
        self,
        *,
        trigger_reference: str,
        action: ActionCommand,
        source: str,
        nonce: str,
        teaching_evidence_receipt_sha256: str | None = None,
    ) -> ActionBinding:
        relation = self.issue_teacher_relation(
            trigger_reference=trigger_reference,
            action=action,
            source=source,
            nonce=nonce,
            teaching_evidence_receipt_sha256=(
                teaching_evidence_receipt_sha256
            ),
        )
        return self.learn(
            trigger_reference=trigger_reference,
            action=action,
            teacher_relation=relation,
        )

    def verify_teaching_evidence_binding(
        self,
        *,
        binding_id: str,
        teaching_evidence_receipt_sha256: str,
        source: str,
        nonce: str,
    ) -> bool:
        """Verify that one learned relation retains its exact evidence link."""

        try:
            binding_identity = sha256_digest(binding_id, "teaching binding")
            evidence_identity = sha256_digest(
                teaching_evidence_receipt_sha256,
                "teaching evidence receipt",
            )
            teacher_source = _identifier(source, "teacher source")
            teacher_nonce = _nonce(nonce, "teacher nonce")
        except (TypeError, ValueError):
            return False
        with self._lock:
            binding = self._bindings.get(binding_identity)
            if binding is None:
                return False
            try:
                binding.verify(
                    self._key,
                    max_scalars=self._max_speech_scalars,
                    max_command_bytes=self._max_command_bytes,
                )
            except (TypeError, ValueError):
                return False
            relation = binding.teacher_relation
            return (
                relation.teaching_evidence_receipt_sha256
                == evidence_identity
                and relation.source == teacher_source
                and relation.nonce == teacher_nonce
            )

    def verified_relation_evidence(
        self,
    ) -> tuple[VerifiedActionRelationEvidence, ...]:
        """Return immutable, fully reverified learned relation evidence.

        This is a read-only internal boundary for deterministic deliberation.
        It exposes complete perception witnesses rather than fingerprints
        alone; consumers must recompute every witness before using the
        fingerprints as indexes.
        """

        verified = []
        with self._lock:
            for binding_id in sorted(self._bindings):
                binding = self._bindings[binding_id]
                binding.verify(
                    self._key,
                    max_scalars=self._max_speech_scalars,
                    max_command_bytes=self._max_command_bytes,
                )
                trigger = self._evidence.get(
                    binding.trigger_witness_receipt_sha256
                )
                if trigger is None:
                    raise ValueError("action relation lost trigger evidence")
                trigger.verify(max_bytes=self._max_witness_bytes)
                if (
                    trigger.structural_fingerprint
                    != binding.trigger_structural_fingerprint
                ):
                    raise ValueError("action trigger field evidence changed")
                closure = binding.latest_closure
                closure_receipt = None
                outcome = None
                if closure is not None:
                    closure.verify(
                        self._key,
                        max_scalars=self._max_speech_scalars,
                        max_command_bytes=self._max_command_bytes,
                    )
                    closure_receipt = closure.authority_receipt_sha256
                    outcome = self._evidence.get(
                        closure.outcome.outcome_settlement_receipt_sha256
                    )
                    if outcome is None:
                        raise ValueError("action relation lost outcome evidence")
                    outcome.verify(max_bytes=self._max_witness_bytes)
                    if (
                        outcome.structural_fingerprint
                        != closure.outcome.outcome_structural_fingerprint
                    ):
                        raise ValueError("action outcome field evidence changed")
                verified.append(
                    VerifiedActionRelationEvidence(
                        binding_id=binding.binding_id,
                        status=binding.status,
                        trigger_witness=trigger,
                        action=binding.action,
                        latest_closure_receipt_sha256=closure_receipt,
                        outcome_witness=outcome,
                    )
                )
        return tuple(verified)

    def select(self, settlement: CausalExperienceSettlement) -> ActionSelection:
        witness = self.accept(settlement)
        with self._lock:
            candidates = tuple(sorted(
                item
                for item in self._by_structure.get(
                    witness.structural_fingerprint, ()
                )
                if self._bindings[item].status != "revoked"
            ))
            if not candidates:
                return ActionSelection(
                    status="unknown", stop_reason="causal_action_unknown"
                )
            if len(candidates) != 1:
                return ActionSelection(
                    status="ambiguous", stop_reason="causal_action_ambiguous"
                )
            binding = self._bindings[candidates[0]]
            unsigned = {
                "action": binding.action.as_record(),
                "binding_id": binding.binding_id,
                "schema": INTENT_SCHEMA,
                "trigger_settlement_receipt_sha256": witness.settlement_receipt_sha256,
                "trigger_structural_fingerprint": witness.structural_fingerprint,
            }
            intent = ActionIntent(
                binding_id=binding.binding_id,
                trigger_settlement_receipt_sha256=witness.settlement_receipt_sha256,
                trigger_structural_fingerprint=witness.structural_fingerprint,
                action=binding.action,
                authority_hmac_sha256=_sign(
                    self._key, INTENT_DOMAIN, _canonical(unsigned)
                ),
            )
            intent.verify(
                self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            receipt = intent.authority_receipt_sha256
            existing = self._intents.get(receipt)
            if existing is not None:
                return ActionSelection(status="committed", intent=existing)
            if len(self._intents) >= self._transaction_capacity:
                raise RuntimeError("causal action intent capacity is full")
            with self._atomic():
                self._retain_evidence_locked(witness)
                self._intents[receipt] = intent
        self._emit(
            "causal_action_cycle_intent_issued",
            intent_receipt_sha256=receipt,
            action_kind=binding.action.kind,
        )
        return ActionSelection(status="committed", intent=intent)

    def verify_live_intent(self, intent: object) -> bool:
        """Verify intent authority and current issued-intent membership."""
        if not isinstance(intent, ActionIntent):
            return False
        try:
            intent.verify(
                self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            receipt = intent.authority_receipt_sha256
        except (TypeError, ValueError):
            return False
        with self._lock:
            return self._intents.get(receipt) == intent

    def verify_live_execution_receipt(self, receipt: object) -> bool:
        """Return whether an authenticated execution is awaiting outcome."""
        try:
            canonical = sha256_digest(receipt, "execution receipt")
        except (TypeError, ValueError):
            return False
        with self._lock:
            execution = self._executions.get(canonical)
            if execution is None:
                return False
            try:
                execution.verify(self._key)
            except (TypeError, ValueError):
                return False
            return execution.authority_receipt_sha256 == canonical

    def live_execution_trigger_receipt(self, receipt: object) -> str | None:
        """Resolve a live execution to its authenticated trigger receipt."""
        if not self.verify_live_execution_receipt(receipt):
            return None
        canonical = str(receipt)
        with self._lock:
            execution = self._executions[canonical]
            intent = self._intents.get(execution.intent_receipt_sha256)
            if intent is None:
                return None
            intent.verify(
                self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            return intent.trigger_settlement_receipt_sha256

    def live_execution_binding_id(self, receipt: object) -> str | None:
        """Resolve a live execution to its authenticated learned relation."""
        if not self.verify_live_execution_receipt(receipt):
            return None
        canonical = str(receipt)
        with self._lock:
            execution = self._executions[canonical]
            intent = self._intents.get(execution.intent_receipt_sha256)
            if intent is None:
                return None
            intent.verify(
                self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            return intent.binding_id

    def record_execution(
        self,
        *,
        intent_receipt_sha256: str,
        executor_receipt_sha256: str,
        disposition: str,
    ) -> ActionExecution:
        """TRUSTED-INTERNAL executor acknowledgement; never expose remotely.

        Only an in-process executor adapter that actually received the exact
        action command may call this method.  A rejected disposition is the
        abort path and atomically releases the live intent.
        """
        sha256_digest(intent_receipt_sha256, "intent receipt")
        sha256_digest(executor_receipt_sha256, "executor receipt")
        if disposition not in {"executed", "rejected"}:
            raise ValueError("execution disposition must be executed or rejected")
        with self._lock:
            intent = self._intents.get(intent_receipt_sha256)
            if intent is None:
                raise ValueError("execution names an unknown intent")
            unsigned = {
                "disposition": disposition,
                "executor_receipt_sha256": executor_receipt_sha256,
                "intent_receipt_sha256": intent_receipt_sha256,
                "schema": EXECUTION_SCHEMA,
            }
            execution = ActionExecution(
                intent_receipt_sha256=intent_receipt_sha256,
                executor_receipt_sha256=executor_receipt_sha256,
                disposition=disposition,
                authority_hmac_sha256=_sign(
                    self._key, EXECUTION_DOMAIN, _canonical(unsigned)
                ),
            )
            execution.verify(self._key)
            if disposition == "rejected":
                with self._atomic():
                    del self._intents[intent_receipt_sha256]
                    self._gc_evidence_locked()
                self._emit(
                    "causal_action_cycle_execution_rejected",
                    execution_receipt_sha256=execution.authority_receipt_sha256,
                )
                return execution
            receipt = execution.authority_receipt_sha256
            if any(
                item.intent_receipt_sha256 == intent_receipt_sha256
                for item in self._executions.values()
            ):
                raise ValueError("intent already has an execution receipt")
            if len(self._executions) >= self._transaction_capacity:
                raise RuntimeError("causal action execution capacity is full")
            with self._atomic():
                self._executions[receipt] = execution
        self._emit(
            "causal_action_cycle_execution_recorded",
            execution_receipt_sha256=receipt,
        )
        return execution

    def observe_outcome(
        self,
        *,
        execution_receipt_sha256: str,
        settlement: CausalExperienceSettlement,
    ) -> ActionOutcome:
        witness = self.accept(settlement)
        with self._lock:
            execution = self._executions.get(execution_receipt_sha256)
            if execution is None or execution.disposition != "executed":
                raise ValueError("outcome lacks an executed action receipt")
            unsigned = {
                "execution_receipt_sha256": execution_receipt_sha256,
                "outcome_settlement_receipt_sha256": witness.settlement_receipt_sha256,
                "outcome_structural_fingerprint": witness.structural_fingerprint,
                "schema": OUTCOME_SCHEMA,
            }
            outcome = ActionOutcome(
                execution_receipt_sha256=execution_receipt_sha256,
                outcome_settlement_receipt_sha256=witness.settlement_receipt_sha256,
                outcome_structural_fingerprint=witness.structural_fingerprint,
                authority_hmac_sha256=_sign(
                    self._key, OUTCOME_DOMAIN, _canonical(unsigned)
                ),
            )
            outcome.verify(self._key)
            receipt = outcome.authority_receipt_sha256
            if any(
                item.execution_receipt_sha256 == execution_receipt_sha256
                for item in self._outcomes.values()
            ):
                raise ValueError("execution already has an outcome")
            if len(self._outcomes) >= self._transaction_capacity:
                raise RuntimeError("causal action outcome capacity is full")
            with self._atomic():
                self._retain_evidence_locked(witness)
                self._outcomes[receipt] = outcome
        self._emit(
            "causal_action_cycle_outcome_observed",
            outcome_receipt_sha256=receipt,
        )
        return outcome

    def _close_outcome_locked(
        self,
        *,
        outcome_receipt_sha256: str,
        decision: str,
        resulting_status: str,
        source: str,
        nonce: str,
    ) -> tuple[ActionFeedback, ActionClosure]:
        if any(
            binding.latest_closure is not None
            and binding.latest_closure.feedback.nonce == nonce
            for binding in self._bindings.values()
        ):
            raise ValueError("feedback nonce was already used")
        outcome = self._outcomes.get(outcome_receipt_sha256)
        if outcome is None:
            raise ValueError("closure names an unknown outcome")
        execution = self._executions[outcome.execution_receipt_sha256]
        intent = self._intents[execution.intent_receipt_sha256]
        binding = self._bindings[intent.binding_id]
        if decision == "observe" and resulting_status != binding.status:
            raise ValueError("neutral observation cannot change binding status")
        unsigned = {
            "binding_id": binding.binding_id,
            "decision": decision,
            "nonce": nonce,
            "outcome_receipt_sha256": outcome_receipt_sha256,
            "resulting_binding_status": resulting_status,
            "schema": FEEDBACK_SCHEMA,
            "source": source,
        }
        feedback = ActionFeedback(
            outcome_receipt_sha256=outcome_receipt_sha256,
            binding_id=binding.binding_id,
            decision=decision,
            resulting_binding_status=resulting_status,
            source=source,
            nonce=nonce,
            authority_hmac_sha256=_sign(
                self._key, FEEDBACK_DOMAIN, _canonical(unsigned)
            ),
        )
        feedback.verify(self._key)
        closure_unsigned = {
            "execution": execution.as_record(),
            "feedback": feedback.as_record(),
            "intent": intent.as_record(),
            "outcome": outcome.as_record(),
            "schema": CLOSURE_SCHEMA,
        }
        closure = ActionClosure(
            intent=intent,
            execution=execution,
            outcome=outcome,
            feedback=feedback,
            authority_hmac_sha256=_sign(
                self._key, CLOSURE_DOMAIN, _canonical(closure_unsigned)
            ),
        )
        closure.verify(
            self._key,
            max_scalars=self._max_speech_scalars,
            max_command_bytes=self._max_command_bytes,
        )
        with self._atomic():
            self._bindings[binding.binding_id] = replace(
                binding,
                status=resulting_status,
                latest_closure=closure,
            )
            del self._outcomes[outcome_receipt_sha256]
            del self._executions[outcome.execution_receipt_sha256]
            del self._intents[execution.intent_receipt_sha256]
            self._gc_evidence_locked()
        return feedback, closure

    def close_observed(
        self, *, outcome_receipt_sha256: str
    ) -> ActionFeedback:
        """Neutrally close one observed outcome without teacher judgment.

        This is an internal settlement operation.  It authenticates and
        compacts the completed chain but preserves the binding's current
        status, so a provisional learned relation remains selectable.
        """
        sha256_digest(outcome_receipt_sha256, "observed outcome receipt")
        with self._lock:
            outcome = self._outcomes.get(outcome_receipt_sha256)
            if outcome is None:
                raise ValueError("closure names an unknown outcome")
            execution = self._executions[outcome.execution_receipt_sha256]
            intent = self._intents[execution.intent_receipt_sha256]
            binding = self._bindings[intent.binding_id]
            feedback, closure = self._close_outcome_locked(
                outcome_receipt_sha256=outcome_receipt_sha256,
                decision="observe",
                resulting_status=binding.status,
                source="causal_action_cycle:trusted_internal",
                nonce=f"observe:{outcome_receipt_sha256}",
            )
        self._emit(
            "causal_action_cycle_closed",
            closure_receipt_sha256=closure.authority_receipt_sha256,
            decision="observe",
        )
        return feedback

    def apply_feedback(
        self,
        *,
        outcome_receipt_sha256: str,
        decision: str,
        source: str,
        nonce: str,
    ) -> ActionFeedback:
        """Close an observed outcome with explicit teacher judgment."""
        if decision not in {"confirm", "revoke"}:
            raise ValueError("feedback decision must be confirm or revoke")
        _identifier(source, "feedback source")
        _nonce(nonce, "feedback nonce")
        resulting_status = "confirmed" if decision == "confirm" else "revoked"
        with self._lock:
            feedback, closure = self._close_outcome_locked(
                outcome_receipt_sha256=outcome_receipt_sha256,
                decision=decision,
                resulting_status=resulting_status,
                source=source,
                nonce=nonce,
            )
        self._emit(
            "causal_action_cycle_closed",
            closure_receipt_sha256=closure.authority_receipt_sha256,
            decision=decision,
        )
        return feedback

    def review_latest_closure(
        self,
        *,
        binding_id: str,
        decision: str,
        source: str,
        nonce: str,
    ) -> ActionFeedback:
        """Apply explicit teacher judgment to the latest observed closure."""
        sha256_digest(binding_id, "reviewed binding")
        if decision not in {"confirm", "revoke"}:
            raise ValueError("review decision must be confirm or revoke")
        _identifier(source, "feedback source")
        _nonce(nonce, "feedback nonce")
        resulting_status = "confirmed" if decision == "confirm" else "revoked"
        with self._lock:
            if any(
                item.latest_closure is not None
                and item.latest_closure.feedback.nonce == nonce
                for item in self._bindings.values()
            ):
                raise ValueError("feedback nonce was already used")
            binding = self._bindings.get(binding_id)
            if binding is None or binding.latest_closure is None:
                raise ValueError("binding has no observed closure to review")
            prior = binding.latest_closure
            outcome_receipt = prior.outcome.authority_receipt_sha256
            unsigned = {
                "binding_id": binding.binding_id,
                "decision": decision,
                "nonce": nonce,
                "outcome_receipt_sha256": outcome_receipt,
                "resulting_binding_status": resulting_status,
                "schema": FEEDBACK_SCHEMA,
                "source": source,
            }
            feedback = ActionFeedback(
                outcome_receipt_sha256=outcome_receipt,
                binding_id=binding.binding_id,
                decision=decision,
                resulting_binding_status=resulting_status,
                source=source,
                nonce=nonce,
                authority_hmac_sha256=_sign(
                    self._key, FEEDBACK_DOMAIN, _canonical(unsigned)
                ),
            )
            feedback.verify(self._key)
            closure_unsigned = {
                "execution": prior.execution.as_record(),
                "feedback": feedback.as_record(),
                "intent": prior.intent.as_record(),
                "outcome": prior.outcome.as_record(),
                "schema": CLOSURE_SCHEMA,
            }
            reviewed = ActionClosure(
                intent=prior.intent,
                execution=prior.execution,
                outcome=prior.outcome,
                feedback=feedback,
                authority_hmac_sha256=_sign(
                    self._key, CLOSURE_DOMAIN, _canonical(closure_unsigned)
                ),
            )
            reviewed.verify(
                self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            with self._atomic():
                self._bindings[binding_id] = replace(
                    binding,
                    status=resulting_status,
                    latest_closure=reviewed,
                )
        self._emit(
            "causal_action_cycle_closure_reviewed",
            binding_id=binding_id,
            decision=decision,
            closure_receipt_sha256=reviewed.authority_receipt_sha256,
        )
        return feedback

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded_locked()
        return {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(self._key, STATE_DOMAIN, payload),
        }

    def restore_encoded(self, value: object) -> None:
        if (
            not isinstance(value, Mapping)
            or set(value)
            != {"payload_base64", "schema", "state_hmac_sha256"}
            or value.get("schema") != ENVELOPE_SCHEMA
        ):
            raise ValueError("causal action cycle envelope is malformed")
        try:
            payload = base64.b64decode(value.get("payload_base64"), validate=True)
        except Exception as error:
            raise ValueError("causal action state is not canonical base64") from error
        if (
            not payload
            or len(payload) > self._encoded_state_capacity
            or base64.b64encode(payload).decode("ascii")
            != value.get("payload_base64")
        ):
            raise ValueError("causal action state byte boundary changed")
        expected_hmac = _sign(self._key, STATE_DOMAIN, payload)
        if not hmac.compare_digest(
            expected_hmac, value.get("state_hmac_sha256", "")
        ):
            raise ValueError("causal action cycle state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("causal action state is invalid") from error
        expected_fields = {
            "bindings",
            "capacities",
            "evidence",
            "executions",
            "intents",
            "outcomes",
            "schema",
        }
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or set(decoded) != expected_fields
            or decoded.get("schema") != STATE_SCHEMA
            or decoded.get("capacities") != self._capacities()
            or any(
                not isinstance(decoded.get(name), list)
                for name in (
                    "bindings",
                    "evidence",
                    "executions",
                    "intents",
                    "outcomes",
                )
            )
        ):
            raise ValueError("causal action state fields changed")
        if (
            len(decoded["bindings"]) > self._binding_capacity
            or len(decoded["evidence"]) > self._evidence_capacity
            or any(
                len(decoded[name]) > self._transaction_capacity
                for name in ("executions", "intents", "outcomes")
            )
        ):
            raise ValueError("causal action restored capacity changed")

        evidence = {}
        for record in decoded["evidence"]:
            witness = _witness_from(record, max_bytes=self._max_witness_bytes)
            if witness.settlement_receipt_sha256 in evidence:
                raise ValueError("causal action repeats evidence")
            evidence[witness.settlement_receipt_sha256] = witness
        bindings = {}
        index: dict[str, set[str]] = {}
        teacher_nonces = set()
        feedback_nonces = set()
        for record in decoded["bindings"]:
            binding = _binding_from(
                record,
                key=self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            trigger = evidence.get(binding.trigger_witness_receipt_sha256)
            if (
                binding.binding_id in bindings
                or trigger is None
                or trigger.structural_fingerprint
                != binding.trigger_structural_fingerprint
                or binding.teacher_relation.nonce in teacher_nonces
            ):
                raise ValueError("binding lost unique full-field authority")
            teacher_nonces.add(binding.teacher_relation.nonce)
            closure = binding.latest_closure
            if closure is not None:
                current = evidence.get(
                    closure.intent.trigger_settlement_receipt_sha256
                )
                outcome = evidence.get(
                    closure.outcome.outcome_settlement_receipt_sha256
                )
                if (
                    current is None
                    or outcome is None
                    or current.structural_fingerprint
                    != closure.intent.trigger_structural_fingerprint
                    or outcome.structural_fingerprint
                    != closure.outcome.outcome_structural_fingerprint
                    or closure.feedback.nonce in feedback_nonces
                ):
                    raise ValueError("binding closure lost full-field evidence")
                feedback_nonces.add(closure.feedback.nonce)
            bindings[binding.binding_id] = binding
            index.setdefault(binding.trigger_structural_fingerprint, set()).add(
                binding.binding_id
            )
        intents: OrderedDict[str, ActionIntent] = OrderedDict()
        for record in decoded["intents"]:
            intent = _intent_from(
                record,
                key=self._key,
                max_scalars=self._max_speech_scalars,
                max_command_bytes=self._max_command_bytes,
            )
            receipt = intent.authority_receipt_sha256
            binding = bindings.get(intent.binding_id)
            witness = evidence.get(intent.trigger_settlement_receipt_sha256)
            if (
                receipt in intents
                or binding is None
                or witness is None
                or binding.action != intent.action
                or witness.structural_fingerprint
                != intent.trigger_structural_fingerprint
            ):
                raise ValueError("intent lost its authority chain")
            intents[receipt] = intent
        executions: OrderedDict[str, ActionExecution] = OrderedDict()
        execution_intents = set()
        for record in decoded["executions"]:
            execution = _execution_from(record, key=self._key)
            receipt = execution.authority_receipt_sha256
            if (
                execution.disposition != "executed"
                or execution.intent_receipt_sha256 not in intents
                or execution.intent_receipt_sha256 in execution_intents
            ):
                raise ValueError("execution lost its live intent")
            executions[receipt] = execution
            execution_intents.add(execution.intent_receipt_sha256)
        outcomes: OrderedDict[str, ActionOutcome] = OrderedDict()
        outcome_executions = set()
        for record in decoded["outcomes"]:
            outcome = _outcome_from(record, key=self._key)
            receipt = outcome.authority_receipt_sha256
            witness = evidence.get(outcome.outcome_settlement_receipt_sha256)
            if (
                outcome.execution_receipt_sha256 not in executions
                or outcome.execution_receipt_sha256 in outcome_executions
                or witness is None
                or witness.structural_fingerprint
                != outcome.outcome_structural_fingerprint
            ):
                raise ValueError("outcome lost its execution authority")
            outcomes[receipt] = outcome
            outcome_executions.add(outcome.execution_receipt_sha256)
        with self._lock:
            prior = (
                self._evidence,
                self._bindings,
                self._by_structure,
                self._intents,
                self._executions,
                self._outcomes,
            )
            self._evidence = evidence
            self._bindings = bindings
            self._by_structure = index
            self._intents = intents
            self._executions = executions
            self._outcomes = outcomes
            try:
                if self._encoded_locked() != payload:
                    raise ValueError("causal action state is not canonical")
            except BaseException:
                (
                    self._evidence,
                    self._bindings,
                    self._by_structure,
                    self._intents,
                    self._executions,
                    self._outcomes,
                ) = prior
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            states = {"provisional": 0, "confirmed": 0, "revoked": 0}
            for binding in self._bindings.values():
                states[binding.status] += 1
            return {
                "bindings": len(self._bindings),
                "binding_statuses": states,
                "closures": sum(
                    item.latest_closure is not None
                    for item in self._bindings.values()
                ),
                "encoded_state_bytes": len(self._encoded_locked()),
                "evidence": len(self._evidence),
                "executions": len(self._executions),
                "intents": len(self._intents),
                "outcomes": len(self._outcomes),
                "working_perceptions": len(self._working),
            }


__all__ = (
    "ActionBinding",
    "ActionClosure",
    "ActionCommand",
    "ActionExecution",
    "ActionFeedback",
    "ActionIntent",
    "ActionOutcome",
    "ActionSelection",
    "CausalActionCycle",
    "PerceptionWitness",
    "TeacherRelation",
    "TEACHER_EVIDENCE_SCHEMA",
    "VerifiedActionRelationEvidence",
)
