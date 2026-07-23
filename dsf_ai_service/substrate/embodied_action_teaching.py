"""Authenticated guided W1 action demonstrations.

One demonstration joins an authorized tutor, canonical W1 command bytes, an
exact full-field pre-state, the applied W1 execution, and its exact full-field
post-state.  Only that complete causal proof may create an embodied action
binding.  This authority does not parse language, choose actions, assign chi
meaning, reduce DSF fields, or alter L0--L4.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Mapping, Sequence

from dsf_ai_service.substrate.causal_action_cycle import (
    ActionBinding,
    ActionCommand,
    CausalActionCycle,
)
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    EmbodiedSensoryOutcome,
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
    decode_command,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


DEMONSTRATION_SCHEMA = "guala.embodied_action_teaching.demonstration.v1"
STATE_SCHEMA = "guala.embodied_action_teaching.state.v1"
ENVELOPE_SCHEMA = "guala.embodied_action_teaching.state.hmac.v1"

DEMONSTRATION_DOMAIN = b"guala-embodied-action-demonstration-v1\0"
STATE_DOMAIN = b"guala-embodied-action-teaching-state-v1\0"

DEFAULT_DEMONSTRATION_CAPACITY = 64
DEFAULT_MAX_COMMAND_BYTES = 4096
DEFAULT_MAX_ENCODED_STATE_BYTES = 8 * 1024 * 1024
MAX_AUTHORITY_KEY_BYTES = 4096
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


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _nonce(value: object) -> str:
    result = _identifier(value, "demonstration nonce")
    if len(result) < 16:
        raise ValueError("demonstration nonce must carry at least 16 characters")
    return result


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, bytes):
        result = value
    else:
        raise ValueError("embodied teaching key must be bytes or text")
    if not result or len(result) > MAX_AUTHORITY_KEY_BYTES:
        raise ValueError("embodied teaching key must be bounded and nonempty")
    return result


def _positive_capacity(value: object, name: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise ValueError(f"{name} is outside its exact capacity boundary")
    return value


@dataclass(frozen=True, slots=True)
class EmbodiedActionDemonstrationReceipt:
    tutor_id: str
    nonce: str
    port_id: str
    command_payload_base64: str
    command_sha256: str
    action_receipt_sha256: str
    pre_settlement_receipt_sha256: str
    pre_structural_fingerprint: str
    pre_observation_receipt_sha256: str
    execution_receipt_sha256: str
    post_settlement_receipt_sha256: str
    post_structural_fingerprint: str
    post_observation_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "action_receipt_sha256": self.action_receipt_sha256,
            "command_payload_base64": self.command_payload_base64,
            "command_sha256": self.command_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "nonce": self.nonce,
            "port_id": self.port_id,
            "post_observation_receipt_sha256": (
                self.post_observation_receipt_sha256
            ),
            "post_settlement_receipt_sha256": (
                self.post_settlement_receipt_sha256
            ),
            "post_structural_fingerprint": self.post_structural_fingerprint,
            "pre_observation_receipt_sha256": (
                self.pre_observation_receipt_sha256
            ),
            "pre_settlement_receipt_sha256": (
                self.pre_settlement_receipt_sha256
            ),
            "pre_structural_fingerprint": self.pre_structural_fingerprint,
            "schema": DEMONSTRATION_SCHEMA,
            "tutor_id": self.tutor_id,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.unsigned_record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class GuidedActionBinding:
    demonstration: EmbodiedActionDemonstrationReceipt
    binding_id: str

    def as_record(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "demonstration": self.demonstration.as_record(),
        }


class EmbodiedActionTeachingAuthority:
    """Bounded owner of exact tutor-guided body demonstrations."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        authorized_tutors: Sequence[str],
        world_authority: EmbodimentWorldAuthority,
        sensory_authority: EmbodimentSensoryOutcomeAuthority,
        action_cycle: CausalActionCycle,
        demonstration_capacity: int = DEFAULT_DEMONSTRATION_CAPACITY,
        max_command_bytes: int = DEFAULT_MAX_COMMAND_BYTES,
        max_encoded_state_bytes: int = DEFAULT_MAX_ENCODED_STATE_BYTES,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise ValueError("embodied teaching requires the W1 world authority")
        if not isinstance(sensory_authority, EmbodimentSensoryOutcomeAuthority):
            raise ValueError("embodied teaching requires the sensory authority")
        if not isinstance(action_cycle, CausalActionCycle):
            raise ValueError("embodied teaching requires the causal action cycle")
        if (
            not isinstance(authorized_tutors, Sequence)
            or isinstance(authorized_tutors, (str, bytes, bytearray))
            or not authorized_tutors
        ):
            raise ValueError("embodied teaching requires authorized tutors")
        tutors = tuple(
            sorted(_identifier(item, "tutor id") for item in authorized_tutors)
        )
        if len(tutors) != len(set(tutors)):
            raise ValueError("authorized tutor identities repeat")
        self._key = _key(authority_key)
        self._authorized_tutors = tutors
        self._world = world_authority
        self._sensory = sensory_authority
        self._cycle = action_cycle
        self._capacity = _positive_capacity(
            demonstration_capacity, "demonstration capacity", 4096
        )
        self._max_command_bytes = _positive_capacity(
            max_command_bytes, "command byte capacity", 1024 * 1024
        )
        self._max_encoded_state_bytes = _positive_capacity(
            max_encoded_state_bytes,
            "encoded state byte capacity",
            256 * 1024 * 1024,
        )
        self._records: OrderedDict[str, GuidedActionBinding] = OrderedDict()
        self._lock = threading.RLock()
        self._encoded_state_for(self._records)

    def _sign(self, domain: bytes, payload: Mapping[str, object]) -> str:
        return hmac.new(
            self._key, domain + _canonical(payload), hashlib.sha256
        ).hexdigest()

    def _verify_outcome(
        self,
        outcome: EmbodiedSensoryOutcome,
        *,
        observation: ObservationSnapshot,
        execution_receipt: ActionExecutionReceipt | None,
        observation_receipt_sha256: str,
        execution_receipt_sha256: str | None,
        revision: int,
    ) -> None:
        if not isinstance(outcome, EmbodiedSensoryOutcome):
            raise ValueError("demonstration requires a typed embodied full field")
        self._sensory.verify_outcome_observation_receipt(
            outcome.observation_receipt
        )
        receipt = outcome.observation_receipt
        if (
            receipt.world_observation_receipt_sha256
            != observation_receipt_sha256
            or receipt.execution_receipt_sha256 != execution_receipt_sha256
            or receipt.world_revision != revision
        ):
            raise ValueError("embodied full field names different world evidence")
        outcome.built_full_field.boundary.verify(
            outcome.built_full_field.receipt_registry
        )
        settlement = outcome.causal_settlement
        settlement.verify()
        expected_assembly = (
            f"embodied-outcome-{receipt.authority_receipt_sha256}"
        )
        if (
            outcome.built_full_field.boundary.assembly_id != expected_assembly
            or settlement.assembly_id != expected_assembly
            or settlement.assembly_receipt_sha256
            != outcome.built_full_field.boundary.authority_receipt_sha256
            or settlement.source_tags
            != (f"embodiment-outcome:{receipt.authority_receipt_sha256}",)
            or settlement.routing_chis != ()
        ):
            raise ValueError("embodied settlement lost its exact causal authority")
        expected = self._sensory.transduce(
            observation,
            causal_owner=ExactCausalExperienceOwner(
                on_settlement=lambda _settlement: None,
                log_event=lambda *_args, **_kwargs: None,
            ),
            execution_receipt=execution_receipt,
            commit=False,
        )
        if (
            expected.built_full_field.boundary.authority_receipt_sha256
            != outcome.built_full_field.boundary.authority_receipt_sha256
            or expected.causal_settlement.structural_fingerprint
            != settlement.structural_fingerprint
        ):
            raise ValueError("embodied full field differs from exact W1 geometry")

    def _receipt_for(
        self,
        *,
        tutor_id: str,
        nonce: str,
        action: ActionCommand,
        execution: ActionExecutionReceipt,
        pre_outcome: EmbodiedSensoryOutcome,
        post_outcome: EmbodiedSensoryOutcome,
    ) -> EmbodiedActionDemonstrationReceipt:
        unsigned = {
            "action_receipt_sha256": action.authority_receipt_sha256,
            "command_payload_base64": base64.b64encode(
                action.command_payload
            ).decode("ascii"),
            "command_sha256": execution.command_sha256,
            "execution_receipt_sha256": execution.authority_receipt_sha256,
            "nonce": nonce,
            "port_id": action.port_id,
            "post_observation_receipt_sha256": (
                execution.after.authority_receipt_sha256
            ),
            "post_settlement_receipt_sha256": (
                post_outcome.causal_settlement.authority_receipt_sha256
            ),
            "post_structural_fingerprint": (
                post_outcome.causal_settlement.structural_fingerprint
            ),
            "pre_observation_receipt_sha256": (
                execution.before.authority_receipt_sha256
            ),
            "pre_settlement_receipt_sha256": (
                pre_outcome.causal_settlement.authority_receipt_sha256
            ),
            "pre_structural_fingerprint": (
                pre_outcome.causal_settlement.structural_fingerprint
            ),
            "schema": DEMONSTRATION_SCHEMA,
            "tutor_id": tutor_id,
        }
        signature = self._sign(DEMONSTRATION_DOMAIN, unsigned)
        authority_receipt = _digest(
            {"authority_hmac_sha256": signature, "payload": unsigned}
        )
        return EmbodiedActionDemonstrationReceipt(
            tutor_id=tutor_id,
            nonce=nonce,
            port_id=action.port_id,
            command_payload_base64=unsigned["command_payload_base64"],
            command_sha256=execution.command_sha256,
            action_receipt_sha256=action.authority_receipt_sha256,
            pre_settlement_receipt_sha256=unsigned[
                "pre_settlement_receipt_sha256"
            ],
            pre_structural_fingerprint=unsigned[
                "pre_structural_fingerprint"
            ],
            pre_observation_receipt_sha256=unsigned[
                "pre_observation_receipt_sha256"
            ],
            execution_receipt_sha256=execution.authority_receipt_sha256,
            post_settlement_receipt_sha256=unsigned[
                "post_settlement_receipt_sha256"
            ],
            post_structural_fingerprint=unsigned[
                "post_structural_fingerprint"
            ],
            post_observation_receipt_sha256=unsigned[
                "post_observation_receipt_sha256"
            ],
            authority_hmac_sha256=signature,
            authority_receipt_sha256=authority_receipt,
        )

    def verify_demonstration_receipt(
        self, receipt: EmbodiedActionDemonstrationReceipt
    ) -> None:
        if not isinstance(receipt, EmbodiedActionDemonstrationReceipt):
            raise ValueError("demonstration receipt is not typed")
        _identifier(receipt.tutor_id, "tutor id")
        if receipt.tutor_id not in self._authorized_tutors:
            raise ValueError("demonstration tutor is not authorized")
        _nonce(receipt.nonce)
        if receipt.port_id != PORT_ID:
            raise ValueError("demonstration belongs to another embodiment port")
        try:
            command_payload = base64.b64decode(
                receipt.command_payload_base64, validate=True
            )
        except Exception as error:
            raise ValueError("demonstration command is not canonical base64") from error
        if (
            not command_payload
            or len(command_payload) > self._max_command_bytes
            or base64.b64encode(command_payload).decode("ascii")
            != receipt.command_payload_base64
        ):
            raise ValueError("demonstration command bytes changed")
        command = decode_command(
            command_payload, max_command_bytes=self._max_command_bytes
        )
        if encode_command(command) != command_payload:
            raise ValueError("demonstration command is not canonical W1 bytes")
        action = ActionCommand.embodiment(receipt.port_id, command_payload)
        if (
            hashlib.sha256(command_payload).hexdigest() != receipt.command_sha256
            or action.authority_receipt_sha256 != receipt.action_receipt_sha256
        ):
            raise ValueError("demonstration command identity changed")
        for value, name in (
            (receipt.pre_settlement_receipt_sha256, "pre settlement"),
            (receipt.pre_structural_fingerprint, "pre structure"),
            (receipt.pre_observation_receipt_sha256, "pre observation"),
            (receipt.execution_receipt_sha256, "execution"),
            (receipt.post_settlement_receipt_sha256, "post settlement"),
            (receipt.post_structural_fingerprint, "post structure"),
            (receipt.post_observation_receipt_sha256, "post observation"),
        ):
            _sha256(value, name)
        unsigned = receipt.unsigned_record()
        expected_hmac = self._sign(DEMONSTRATION_DOMAIN, unsigned)
        if not hmac.compare_digest(
            expected_hmac, receipt.authority_hmac_sha256
        ):
            raise ValueError("demonstration HMAC changed")
        expected_receipt = _digest(
            {"authority_hmac_sha256": expected_hmac, "payload": unsigned}
        )
        if expected_receipt != receipt.authority_receipt_sha256:
            raise ValueError("demonstration receipt identity changed")

    def demonstrate(
        self,
        *,
        tutor_id: str,
        nonce: str,
        command_payload: bytes,
        pre_outcome: EmbodiedSensoryOutcome,
        execution_receipt: ActionExecutionReceipt,
        post_outcome: EmbodiedSensoryOutcome,
    ) -> GuidedActionBinding:
        """Learn only from one complete authenticated physical transition."""

        tutor = _identifier(tutor_id, "tutor id")
        if tutor not in self._authorized_tutors:
            raise ValueError("demonstration tutor is not authorized")
        demonstration_nonce = _nonce(nonce)
        if (
            not isinstance(command_payload, bytes)
            or not command_payload
            or len(command_payload) > self._max_command_bytes
        ):
            raise ValueError("demonstration command exceeds its byte boundary")
        decoded_command = decode_command(
            command_payload, max_command_bytes=self._max_command_bytes
        )
        if encode_command(decoded_command) != command_payload:
            raise ValueError("demonstration command is not canonical W1 bytes")
        self._world.verify_execution_receipt(execution_receipt)
        if (
            execution_receipt.port_id != self._world.port_id
            or execution_receipt.actor_body_id
            != execution_receipt.before.self_body_id
            or execution_receipt.actor_body_id
            != execution_receipt.after.self_body_id
            or execution_receipt.command_sha256
            != hashlib.sha256(command_payload).hexdigest()
        ):
            raise ValueError(
                "demonstration command differs from an exact self-body W1 execution"
            )
        self._verify_outcome(
            pre_outcome,
            observation=execution_receipt.before,
            execution_receipt=None,
            observation_receipt_sha256=(
                execution_receipt.before.authority_receipt_sha256
            ),
            execution_receipt_sha256=None,
            revision=execution_receipt.before.revision,
        )
        self._verify_outcome(
            post_outcome,
            observation=execution_receipt.after,
            execution_receipt=execution_receipt,
            observation_receipt_sha256=(
                execution_receipt.after.authority_receipt_sha256
            ),
            execution_receipt_sha256=(
                execution_receipt.authority_receipt_sha256
            ),
            revision=execution_receipt.after.revision,
        )
        action = ActionCommand.embodiment(self._world.port_id, command_payload)
        receipt = self._receipt_for(
            tutor_id=tutor,
            nonce=demonstration_nonce,
            action=action,
            execution=execution_receipt,
            pre_outcome=pre_outcome,
            post_outcome=post_outcome,
        )
        self.verify_demonstration_receipt(receipt)
        expected_binding_id = _digest(
            {
                "action_receipt_sha256": action.authority_receipt_sha256,
                "schema": "guala.causal_action_cycle.semantic_relation.v1",
                "trigger_structural_fingerprint": (
                    pre_outcome.causal_settlement.structural_fingerprint
                ),
            }
        )
        guided = GuidedActionBinding(
            demonstration=receipt,
            binding_id=expected_binding_id,
        )
        with self._lock:
            prior = self._records.get(demonstration_nonce)
            if prior is not None:
                if prior == guided:
                    return prior
                raise ValueError("demonstration nonce was already used")
            if len(self._records) >= self._capacity:
                raise RuntimeError("embodied demonstration capacity is full")
            candidate = OrderedDict(self._records)
            candidate[demonstration_nonce] = guided
            self._encoded_state_for(candidate)

            trigger = pre_outcome.causal_settlement
            self._cycle.accept(trigger)
            binding = self._cycle.teach(
                trigger_reference=trigger.event_id,
                action=action,
                source=tutor,
                nonce=demonstration_nonce,
                teaching_evidence_receipt_sha256=(
                    receipt.authority_receipt_sha256
                ),
            )
            if (
                not isinstance(binding, ActionBinding)
                or binding.binding_id != expected_binding_id
                or binding.teacher_relation.teaching_evidence_receipt_sha256
                != receipt.authority_receipt_sha256
                or not self._cycle.verify_teaching_evidence_binding(
                    binding_id=binding.binding_id,
                    teaching_evidence_receipt_sha256=(
                        receipt.authority_receipt_sha256
                    ),
                    source=tutor,
                    nonce=demonstration_nonce,
                )
            ):
                raise RuntimeError("causal cycle did not retain demonstration authority")
            self._records = candidate
            return guided

    def _state_payload(
        self, records: Mapping[str, GuidedActionBinding]
    ) -> dict[str, object]:
        return {
            "authorized_tutors": list(self._authorized_tutors),
            "limits": {
                "demonstration_capacity": self._capacity,
                "max_command_bytes": self._max_command_bytes,
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
            },
            "records": [records[key].as_record() for key in sorted(records)],
            "schema": STATE_SCHEMA,
        }

    def _encoded_state_for(
        self, records: Mapping[str, GuidedActionBinding]
    ) -> bytes:
        payload = _canonical(self._state_payload(records))
        if len(payload) > self._max_encoded_state_bytes:
            raise RuntimeError("embodied teaching state capacity is full")
        envelope = {
            "authority_hmac_sha256": hmac.new(
                self._key, STATE_DOMAIN + payload, hashlib.sha256
            ).hexdigest(),
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._max_encoded_state_bytes:
            raise RuntimeError("embodied teaching envelope capacity is full")
        return encoded

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded_state_for(self._records)

    def _receipt_from_record(
        self, value: object
    ) -> EmbodiedActionDemonstrationReceipt:
        expected = {
            "action_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "command_payload_base64",
            "command_sha256",
            "execution_receipt_sha256",
            "nonce",
            "port_id",
            "post_observation_receipt_sha256",
            "post_settlement_receipt_sha256",
            "post_structural_fingerprint",
            "pre_observation_receipt_sha256",
            "pre_settlement_receipt_sha256",
            "pre_structural_fingerprint",
            "schema",
            "tutor_id",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != DEMONSTRATION_SCHEMA
        ):
            raise ValueError("demonstration receipt fields changed")
        receipt = EmbodiedActionDemonstrationReceipt(
            tutor_id=value.get("tutor_id"),
            nonce=value.get("nonce"),
            port_id=value.get("port_id"),
            command_payload_base64=value.get("command_payload_base64"),
            command_sha256=value.get("command_sha256"),
            action_receipt_sha256=value.get("action_receipt_sha256"),
            pre_settlement_receipt_sha256=value.get(
                "pre_settlement_receipt_sha256"
            ),
            pre_structural_fingerprint=value.get(
                "pre_structural_fingerprint"
            ),
            pre_observation_receipt_sha256=value.get(
                "pre_observation_receipt_sha256"
            ),
            execution_receipt_sha256=value.get("execution_receipt_sha256"),
            post_settlement_receipt_sha256=value.get(
                "post_settlement_receipt_sha256"
            ),
            post_structural_fingerprint=value.get(
                "post_structural_fingerprint"
            ),
            post_observation_receipt_sha256=value.get(
                "post_observation_receipt_sha256"
            ),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
            authority_receipt_sha256=value.get("authority_receipt_sha256"),
        )
        self.verify_demonstration_receipt(receipt)
        if receipt.as_record() != dict(value):
            raise ValueError("demonstration receipt is not canonical")
        return receipt

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._max_encoded_state_bytes
        ):
            raise ValueError("embodied teaching snapshot exceeds byte capacity")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodied teaching snapshot is invalid") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"authority_hmac_sha256", "payload_base64", "schema"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("embodied teaching envelope fields changed")
        try:
            payload = base64.b64decode(
                envelope.get("payload_base64"), validate=True
            )
        except Exception as error:
            raise ValueError("embodied teaching state is not canonical base64") from error
        expected_hmac = hmac.new(
            self._key, STATE_DOMAIN + payload, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac, envelope.get("authority_hmac_sha256", "")
        ):
            raise ValueError("embodied teaching state HMAC changed")
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("embodied teaching state payload is invalid") from error
        if (
            not isinstance(decoded, Mapping)
            or _canonical(decoded) != payload
            or set(decoded) != {
                "authorized_tutors",
                "limits",
                "records",
                "schema",
            }
            or decoded.get("schema") != STATE_SCHEMA
            or decoded.get("authorized_tutors") != list(self._authorized_tutors)
            or decoded.get("limits")
            != {
                "demonstration_capacity": self._capacity,
                "max_command_bytes": self._max_command_bytes,
                "max_encoded_state_bytes": self._max_encoded_state_bytes,
            }
            or not isinstance(decoded.get("records"), list)
            or len(decoded["records"]) > self._capacity
        ):
            raise ValueError("embodied teaching state fields changed")
        records: OrderedDict[str, GuidedActionBinding] = OrderedDict()
        for value in decoded["records"]:
            if (
                not isinstance(value, Mapping)
                or set(value) != {"binding_id", "demonstration"}
            ):
                raise ValueError("guided action binding fields changed")
            receipt = self._receipt_from_record(value.get("demonstration"))
            binding_id = _sha256(value.get("binding_id"), "causal binding")
            expected_binding = _digest(
                {
                    "action_receipt_sha256": receipt.action_receipt_sha256,
                    "schema": "guala.causal_action_cycle.semantic_relation.v1",
                    "trigger_structural_fingerprint": (
                        receipt.pre_structural_fingerprint
                    ),
                }
            )
            if binding_id != expected_binding or receipt.nonce in records:
                raise ValueError("guided action binding authority changed")
            if not self._cycle.verify_teaching_evidence_binding(
                binding_id=binding_id,
                teaching_evidence_receipt_sha256=(
                    receipt.authority_receipt_sha256
                ),
                source=receipt.tutor_id,
                nonce=receipt.nonce,
            ):
                raise ValueError(
                    "guided action binding is absent from the causal cycle"
                )
            records[receipt.nonce] = GuidedActionBinding(
                demonstration=receipt,
                binding_id=binding_id,
            )
        with self._lock:
            if self._encoded_state_for(records) != encoded:
                raise ValueError("embodied teaching state is not canonical")
            self._records = records

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "authorized_tutors": len(self._authorized_tutors),
                "demonstration_capacity": self._capacity,
                "demonstrations": len(self._records),
                "encoded_state_bytes": len(self._encoded_state_for(self._records)),
            }


__all__ = (
    "EmbodiedActionDemonstrationReceipt",
    "EmbodiedActionTeachingAuthority",
    "GuidedActionBinding",
)
