"""Durable custody for one self-heard body-owned vocal consequence.

The body owns an articulation only while its transient candidate and W1 undo
are live.  This owner seals the exact compact motor command and authenticated
causal receipts before that transient custody is finalized.  It retains no
waveform, transcript, label, semantic assertion, or Chi authority.

The store has capacity one.  Both publication and consumption are explicit
prepare/commit/finalize transactions with exact rollback.  Its HMAC state can
be cold-restored without reconstructing the old transient candidate or undo.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ARTICULATORY_PROGRAM_SCHEMA,
    ArticulatoryBodyTrajectoryInterval,
    ArticulatoryProgram,
    LaryngealExcitationConfiguration,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.causal_inquiry import (
    CausalInquiryOwner,
    InquiryNeed,
    InquiryWitness,
)
from dsf_ai_service.substrate.embodied_vocal_body import (
    BodyOwnedMotorFragmentCustody,
    EmbodiedVocalBodyAuthority,
    TransientVocalCandidate,
)
from dsf_ai_service.substrate.embodiment_world import VOCAL_SAMPLE_RATE_HZ


RECORD_SCHEMA = "guala.pending_body_owned_vocal_consequence.record.v2"
CAPABILITY_SCHEMA = (
    "guala.pending_body_owned_vocal_consequence.client_capability.v1"
)
STATE_SCHEMA = "guala.pending_body_owned_vocal_consequence.state.v2"
ENVELOPE_SCHEMA = (
    "guala.pending_body_owned_vocal_consequence.state_hmac.v2"
)
STATUS_SCHEMA = "guala.pending_body_owned_vocal_consequence.status.v1"

_RECORD_DOMAIN = b"guala-pending-body-owned-vocal-record-v2\0"
_CAPABILITY_DOMAIN = b"guala-pending-body-owned-vocal-capability-v1\0"
_STATE_DOMAIN = b"guala-pending-body-owned-vocal-state-v2\0"
_IDENTITY_SCHEMA = (
    "guala.pending_body_owned_vocal_consequence.identity.v1"
)
_HEX = frozenset("0123456789abcdef")
_MAX_PROFILE_ID_BYTES = 256
_MAX_STATE_BYTES = 1024 * 1024
_MIN_STATE_BYTES = 4 * 1024
_PREPARED_AUTHORITY = object()
_COMMIT_UNDO_AUTHORITY = object()
_CONSUME_PREPARED_AUTHORITY = object()
_CONSUME_UNDO_AUTHORITY = object()
_RESTORED_CUSTODY_AUTHORITY = object()


class PendingBodyOwnedVocalConsequenceCapacityError(RuntimeError):
    """The single durable pending-custody slot is occupied."""


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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError(
            "pending vocal consequence authority key must be bytes or text"
        )
    if not 32 <= len(result) <= 4_096:
        raise ValueError(
            "pending vocal consequence authority key boundary changed"
        )
    return result


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > _MAX_PROFILE_ID_BYTES
    ):
        raise ValueError(f"{name} changed")
    return value


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive_int(value: object, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(f"{name} changed")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("pending vocal source time is not exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object) -> Fraction:
    if not isinstance(value, str):
        raise ValueError("pending vocal source time is not canonical")
    parts = value.split("/")
    if len(parts) != 2:
        raise ValueError("pending vocal source time is not canonical")
    try:
        numerator = int(parts[0])
        denominator = int(parts[1])
    except ValueError as exc:
        raise ValueError(
            "pending vocal source time is not canonical"
        ) from exc
    if denominator <= 0:
        raise ValueError("pending vocal source time is not canonical")
    result = Fraction(numerator, denominator)
    if value != _fraction_text(result):
        raise ValueError("pending vocal source time is not canonical")
    return result


def _sign(
    key: bytes,
    domain: bytes,
    payload: Mapping[str, object],
) -> str:
    return hmac.new(
        key,
        domain + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class PendingBodyOwnedVocalClientCapability:
    """Opaque client-held authority for exactly one pending record."""

    opaque_token: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "opaque_token": self.opaque_token,
            "schema": CAPABILITY_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PendingBodyOwnedVocalConsequenceRecord:
    """Exact durable receipts and compact motor geometry for one consequence."""

    pending_id: str
    need_id: str
    need_authority_hmac_sha256: str
    need_authority_receipt_sha256: str
    witness_authority_hmac_sha256: str
    witness_authority_receipt_sha256: str
    witness_parent_custody_receipt_sha256: str
    witness_custody_capability_receipt_sha256: str
    witness_settlement_receipt_sha256: str
    witness_source_occurrence_id: str
    witness_source_time_start: Fraction
    witness_source_time_end: Fraction
    witness_world_observation_receipt_sha256: str
    witness_world_execution_receipt_sha256: str | None
    witness_world_before_receipt_sha256: str | None
    witness_world_after_receipt_sha256: str | None
    candidate_authority_hmac_sha256: str
    candidate_authority_receipt_sha256: str
    transient_act_id: str
    candidate_custody_receipt_sha256: str
    candidate_actuator_graph_receipt_sha256: str
    candidate_pressure_sha256: str
    candidate_source_sample_count: int
    candidate_program_sample_count: int
    candidate_sample_count: int
    candidate_exact_quiescent: bool
    candidate_world_execution_receipt_sha256: str
    candidate_w1_mount_receipt_sha256: str
    candidate_causal_settlement_receipt_sha256: str
    candidate_binaural_l5_receipt_sha256: str
    candidate_receptor_settlement_receipt_sha256: str
    candidate_recurrent_q_receipt_sha256: str
    motor_custody_authority_hmac_sha256: str
    motor_custody_authority_receipt_sha256: str
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    command_graph_sha256: str
    program: ArticulatoryProgram
    client_capability_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_actuator_graph_receipt_sha256": (
                self.candidate_actuator_graph_receipt_sha256
            ),
            "candidate_authority_hmac_sha256": (
                self.candidate_authority_hmac_sha256
            ),
            "candidate_authority_receipt_sha256": (
                self.candidate_authority_receipt_sha256
            ),
            "candidate_binaural_l5_receipt_sha256": (
                self.candidate_binaural_l5_receipt_sha256
            ),
            "candidate_causal_settlement_receipt_sha256": (
                self.candidate_causal_settlement_receipt_sha256
            ),
            "candidate_custody_receipt_sha256": (
                self.candidate_custody_receipt_sha256
            ),
            "candidate_exact_quiescent": self.candidate_exact_quiescent,
            "candidate_pressure_sha256": self.candidate_pressure_sha256,
            "candidate_program_sample_count": (
                self.candidate_program_sample_count
            ),
            "candidate_receptor_settlement_receipt_sha256": (
                self.candidate_receptor_settlement_receipt_sha256
            ),
            "candidate_recurrent_q_receipt_sha256": (
                self.candidate_recurrent_q_receipt_sha256
            ),
            "candidate_sample_count": self.candidate_sample_count,
            "candidate_source_sample_count": (
                self.candidate_source_sample_count
            ),
            "candidate_w1_mount_receipt_sha256": (
                self.candidate_w1_mount_receipt_sha256
            ),
            "candidate_world_execution_receipt_sha256": (
                self.candidate_world_execution_receipt_sha256
            ),
            "client_capability_receipt_sha256": (
                self.client_capability_receipt_sha256
            ),
            "command_graph_sha256": self.command_graph_sha256,
            "motor_custody_authority_hmac_sha256": (
                self.motor_custody_authority_hmac_sha256
            ),
            "motor_custody_authority_receipt_sha256": (
                self.motor_custody_authority_receipt_sha256
            ),
            "need_authority_hmac_sha256": (
                self.need_authority_hmac_sha256
            ),
            "need_authority_receipt_sha256": (
                self.need_authority_receipt_sha256
            ),
            "need_id": self.need_id,
            "pending_id": self.pending_id,
            "program": self.program.as_record(),
            "schema": RECORD_SCHEMA,
            "transient_act_id": self.transient_act_id,
            "witness_authority_hmac_sha256": (
                self.witness_authority_hmac_sha256
            ),
            "witness_authority_receipt_sha256": (
                self.witness_authority_receipt_sha256
            ),
            "witness_custody_capability_receipt_sha256": (
                self.witness_custody_capability_receipt_sha256
            ),
            "witness_parent_custody_receipt_sha256": (
                self.witness_parent_custody_receipt_sha256
            ),
            "witness_settlement_receipt_sha256": (
                self.witness_settlement_receipt_sha256
            ),
            "witness_source_occurrence_id": (
                self.witness_source_occurrence_id
            ),
            "witness_source_time_end": _fraction_text(
                self.witness_source_time_end
            ),
            "witness_source_time_start": _fraction_text(
                self.witness_source_time_start
            ),
            "witness_world_after_receipt_sha256": (
                self.witness_world_after_receipt_sha256
            ),
            "witness_world_before_receipt_sha256": (
                self.witness_world_before_receipt_sha256
            ),
            "witness_world_execution_receipt_sha256": (
                self.witness_world_execution_receipt_sha256
            ),
            "witness_world_observation_receipt_sha256": (
                self.witness_world_observation_receipt_sha256
            ),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _MutationState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class PreparedPendingBodyOwnedVocalConsequence:
    record: PendingBodyOwnedVocalConsequenceRecord
    client_capability: PendingBodyOwnedVocalClientCapability
    _state: _MutationState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PendingBodyOwnedVocalConsequenceCommitUndo:
    record: PendingBodyOwnedVocalConsequenceRecord
    client_capability: PendingBodyOwnedVocalClientCapability
    _state: _MutationState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PreparedPendingBodyOwnedVocalConsequenceConsume:
    record: PendingBodyOwnedVocalConsequenceRecord
    _state: _MutationState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PendingBodyOwnedVocalConsequenceConsumeUndo:
    record: PendingBodyOwnedVocalConsequenceRecord
    _state: _MutationState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class RestoredPendingBodyOwnedVocalCustody:
    """Typed custody independent of the expired live candidate and W1 undo."""

    pending_id: str
    candidate_authority_receipt_sha256: str
    motor_custody_authority_receipt_sha256: str
    need_authority_receipt_sha256: str
    witness_authority_receipt_sha256: str
    witness_settlement_receipt_sha256: str
    witness_source_time_start: Fraction
    witness_source_time_end: Fraction
    world_before_receipt_sha256: str
    world_after_receipt_sha256: str
    world_execution_receipt_sha256: str
    command_graph_sha256: str
    program: ArticulatoryProgram
    pending_authority_receipt_sha256: str
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class PendingBodyOwnedVocalConsequenceOwner:
    """Own exactly one durable, capability-gated pending consequence."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile_id: str,
        max_state_bytes: int,
        inquiry_owner: CausalInquiryOwner,
        vocal_body_owner: EmbodiedVocalBodyAuthority,
    ) -> None:
        self._key = _key(authority_key)
        self._profile_id = _identifier(
            profile_id,
            "pending vocal consequence profile",
        )
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not _MIN_STATE_BYTES
            <= max_state_bytes
            <= _MAX_STATE_BYTES
        ):
            raise ValueError(
                "pending vocal consequence state capacity changed"
            )
        if not isinstance(inquiry_owner, CausalInquiryOwner):
            raise TypeError(
                "pending vocal consequence requires its inquiry owner"
            )
        if not isinstance(vocal_body_owner, EmbodiedVocalBodyAuthority):
            raise TypeError(
                "pending vocal consequence requires its vocal body owner"
            )
        self._max_state_bytes = max_state_bytes
        self._inquiry = inquiry_owner
        self._body = vocal_body_owner
        self._record_key = hashlib.sha256(
            _RECORD_DOMAIN + self._key
        ).digest()
        self._capability_key = hashlib.sha256(
            _CAPABILITY_DOMAIN + self._key
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + self._key
        ).digest()
        self._pending: PendingBodyOwnedVocalConsequenceRecord | None = None
        self._prepared: (
            PreparedPendingBodyOwnedVocalConsequence | None
        ) = None
        self._latest_commit_undo: (
            PendingBodyOwnedVocalConsequenceCommitUndo | None
        ) = None
        self._prepared_consume: (
            PreparedPendingBodyOwnedVocalConsequenceConsume | None
        ) = None
        self._latest_consume_undo: (
            PendingBodyOwnedVocalConsequenceConsumeUndo | None
        ) = None
        self._owner_authority = object()
        self._lock = threading.RLock()

    @property
    def pending(
        self,
    ) -> PendingBodyOwnedVocalConsequenceRecord | None:
        with self._lock:
            return self._pending

    def _verify_client_capability(
        self,
        capability: PendingBodyOwnedVocalClientCapability,
        *,
        expected_receipt: str,
    ) -> None:
        if not isinstance(
            capability,
            PendingBodyOwnedVocalClientCapability,
        ):
            raise TypeError(
                "pending vocal consequence client capability is not typed"
            )
        _sha(capability.opaque_token, "pending vocal opaque token")
        signature = _sign(
            self._capability_key,
            _CAPABILITY_DOMAIN,
            capability.payload(),
        )
        if (
            not hmac.compare_digest(
                signature,
                capability.authority_hmac_sha256,
            )
            or capability.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": capability.payload(),
            })
            or not hmac.compare_digest(
                capability.authority_receipt_sha256,
                expected_receipt,
            )
        ):
            raise ValueError(
                "pending vocal consequence client capability changed"
            )

    def _issue_client_capability(
        self,
        pending_id: str,
    ) -> PendingBodyOwnedVocalClientCapability:
        _sha(pending_id, "pending vocal consequence identity")
        provisional = PendingBodyOwnedVocalClientCapability(
            opaque_token=hmac.new(
                self._capability_key,
                b"opaque-client-token-v1\0"
                + pending_id.encode("ascii"),
                hashlib.sha256,
            ).hexdigest(),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._capability_key,
            _CAPABILITY_DOMAIN,
            provisional.payload(),
        )
        return replace(
            provisional,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _active_witness(
        self,
        need: InquiryNeed,
        witness: InquiryWitness,
    ) -> None:
        # The inquiry snapshot verifies the retained witness and need HMACs
        # before their exact receipts and Fraction interval cross custody.
        self._inquiry.snapshot_encoded()
        if (
            not isinstance(need, InquiryNeed)
            or self._inquiry.active_need != need
            or not isinstance(witness, InquiryWitness)
            or need.witness_receipt_sha256
            != witness.authority_receipt_sha256
        ):
            raise ValueError(
                "pending vocal consequence lost active inquiry custody"
            )
        matches = tuple(
            value
            for value in self._inquiry.witnesses
            if value.authority_receipt_sha256
            == witness.authority_receipt_sha256
        )
        if len(matches) != 1 or matches[0] != witness:
            raise ValueError(
                "pending vocal consequence witness is not retained"
            )
        if (
            witness.source_time_end <= witness.source_time_start
            or need.origin != witness.origin
            or need.route_state != witness.route_state
        ):
            raise ValueError(
                "pending vocal consequence inquiry relation changed"
            )

    def _verify_record(
        self,
        value: PendingBodyOwnedVocalConsequenceRecord,
    ) -> None:
        if not isinstance(
            value,
            PendingBodyOwnedVocalConsequenceRecord,
        ):
            raise TypeError(
                "pending vocal consequence record is not typed"
            )
        value.program.verify()
        source_count = _positive_int(
            value.candidate_source_sample_count,
            "pending vocal consequence source sample count",
        )
        program_count = _positive_int(
            value.candidate_program_sample_count,
            "pending vocal consequence program sample count",
        )
        sample_count = _positive_int(
            value.candidate_sample_count,
            "pending vocal consequence sample count",
        )
        if (
            value.witness_source_time_end
            <= value.witness_source_time_start
            or not source_count <= program_count <= sample_count
            or value.program.sample_count
            != value.candidate_program_sample_count
            or value.candidate_exact_quiescent is not True
            or _digest(value.program.as_record())
            != value.command_graph_sha256
            or value.candidate_pressure_sha256
            == "0" * 64
        ):
            raise ValueError(
                "pending vocal consequence physical structure changed"
            )
        for digest, name in (
            (value.pending_id, "pending identity"),
            (value.need_id, "need identity"),
            (value.need_authority_hmac_sha256, "need HMAC"),
            (value.need_authority_receipt_sha256, "need authority"),
            (value.witness_authority_hmac_sha256, "witness HMAC"),
            (value.witness_authority_receipt_sha256, "witness authority"),
            (
                value.witness_parent_custody_receipt_sha256,
                "witness parent custody",
            ),
            (
                value.witness_custody_capability_receipt_sha256,
                "witness custody capability",
            ),
            (
                value.witness_settlement_receipt_sha256,
                "witness settlement",
            ),
            (
                value.witness_source_occurrence_id,
                "witness source occurrence",
            ),
            (
                value.witness_world_observation_receipt_sha256,
                "witness world observation",
            ),
            (
                value.candidate_authority_hmac_sha256,
                "candidate HMAC",
            ),
            (
                value.candidate_authority_receipt_sha256,
                "candidate authority",
            ),
            (value.transient_act_id, "transient act identity"),
            (
                value.candidate_custody_receipt_sha256,
                "candidate custody",
            ),
            (
                value.candidate_actuator_graph_receipt_sha256,
                "candidate actuator graph",
            ),
            (
                value.candidate_pressure_sha256,
                "candidate pressure",
            ),
            (
                value.candidate_world_execution_receipt_sha256,
                "candidate world execution",
            ),
            (
                value.candidate_w1_mount_receipt_sha256,
                "candidate W1 mount",
            ),
            (
                value.candidate_causal_settlement_receipt_sha256,
                "candidate causal settlement",
            ),
            (
                value.candidate_binaural_l5_receipt_sha256,
                "candidate binaural L5",
            ),
            (
                value.candidate_receptor_settlement_receipt_sha256,
                "candidate receptor settlement",
            ),
            (
                value.candidate_recurrent_q_receipt_sha256,
                "candidate recurrent Q",
            ),
            (
                value.motor_custody_authority_hmac_sha256,
                "motor custody HMAC",
            ),
            (
                value.motor_custody_authority_receipt_sha256,
                "motor custody authority",
            ),
            (value.world_before_receipt_sha256, "world before"),
            (value.world_after_receipt_sha256, "world after"),
            (value.world_execution_receipt_sha256, "world execution"),
            (value.command_graph_sha256, "command graph"),
            (
                value.client_capability_receipt_sha256,
                "client capability",
            ),
            (value.authority_hmac_sha256, "record HMAC"),
            (value.authority_receipt_sha256, "record authority"),
        ):
            _sha(digest, f"pending vocal consequence {name}")
        for optional, name in (
            (
                value.witness_world_execution_receipt_sha256,
                "witness world execution",
            ),
            (
                value.witness_world_before_receipt_sha256,
                "witness world before",
            ),
            (
                value.witness_world_after_receipt_sha256,
                "witness world after",
            ),
        ):
            if optional is not None:
                _sha(optional, f"pending vocal consequence {name}")
        identity = _digest({
            "candidate_authority_receipt_sha256": (
                value.candidate_authority_receipt_sha256
            ),
            "motor_custody_authority_receipt_sha256": (
                value.motor_custody_authority_receipt_sha256
            ),
            "need_authority_receipt_sha256": (
                value.need_authority_receipt_sha256
            ),
            "schema": _IDENTITY_SCHEMA,
            "witness_authority_receipt_sha256": (
                value.witness_authority_receipt_sha256
            ),
        })
        signature = _sign(
            self._record_key,
            _RECORD_DOMAIN,
            value.payload(),
        )
        if (
            value.pending_id != identity
            or not hmac.compare_digest(
                signature,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError(
                "pending vocal consequence record authority changed"
            )

    def prepare(
        self,
        *,
        need: InquiryNeed,
        witness: InquiryWitness,
        candidate: TransientVocalCandidate,
        motor_custody: BodyOwnedMotorFragmentCustody,
    ) -> PreparedPendingBodyOwnedVocalConsequence:
        with self._lock:
            if (
                self._pending is not None
                or self._prepared is not None
                or self._latest_commit_undo is not None
                or self._prepared_consume is not None
                or self._latest_consume_undo is not None
            ):
                raise PendingBodyOwnedVocalConsequenceCapacityError(
                    "pending vocal consequence capacity one is occupied"
                )
            self._active_witness(need, witness)
            self._body.verify_candidate(candidate)
            self._body.verify_motor_fragment_custody(
                motor_custody,
                candidate,
            )
            if (
                motor_custody.candidate_receipt_sha256
                != candidate.authority_receipt_sha256
                or motor_custody.transient_act_id
                != candidate.transient_act_id
                or motor_custody.pressure_sha256
                != candidate.pressure_sha256
                or motor_custody.world_execution_receipt_sha256
                != candidate.world_execution_receipt_sha256
                or motor_custody.program.sample_count
                != candidate.program_sample_count
            ):
                raise ValueError(
                    "pending vocal consequence crossed physical custody"
                )
            identity = _digest({
                "candidate_authority_receipt_sha256": (
                    candidate.authority_receipt_sha256
                ),
                "motor_custody_authority_receipt_sha256": (
                    motor_custody.authority_receipt_sha256
                ),
                "need_authority_receipt_sha256": (
                    need.authority_receipt_sha256
                ),
                "schema": _IDENTITY_SCHEMA,
                "witness_authority_receipt_sha256": (
                    witness.authority_receipt_sha256
                ),
            })
            capability = self._issue_client_capability(identity)
            provisional = PendingBodyOwnedVocalConsequenceRecord(
                pending_id=identity,
                need_id=need.need_id,
                need_authority_hmac_sha256=need.authority_hmac_sha256,
                need_authority_receipt_sha256=(
                    need.authority_receipt_sha256
                ),
                witness_authority_hmac_sha256=(
                    witness.authority_hmac_sha256
                ),
                witness_authority_receipt_sha256=(
                    witness.authority_receipt_sha256
                ),
                witness_parent_custody_receipt_sha256=(
                    witness.parent_custody_receipt_sha256
                ),
                witness_custody_capability_receipt_sha256=(
                    witness.custody_capability_receipt_sha256
                ),
                witness_settlement_receipt_sha256=(
                    witness.settlement_receipt_sha256
                ),
                witness_source_occurrence_id=(
                    witness.source_occurrence_id
                ),
                witness_source_time_start=witness.source_time_start,
                witness_source_time_end=witness.source_time_end,
                witness_world_observation_receipt_sha256=(
                    witness.world_observation_receipt_sha256
                ),
                witness_world_execution_receipt_sha256=(
                    witness.world_execution_receipt_sha256
                ),
                witness_world_before_receipt_sha256=(
                    witness.world_before_receipt_sha256
                ),
                witness_world_after_receipt_sha256=(
                    witness.world_after_receipt_sha256
                ),
                candidate_authority_hmac_sha256=(
                    candidate.authority_hmac_sha256
                ),
                candidate_authority_receipt_sha256=(
                    candidate.authority_receipt_sha256
                ),
                transient_act_id=candidate.transient_act_id,
                candidate_custody_receipt_sha256=(
                    candidate.custody_receipt_sha256
                ),
                candidate_actuator_graph_receipt_sha256=(
                    candidate.actuator_graph_receipt_sha256
                ),
                candidate_pressure_sha256=candidate.pressure_sha256,
                candidate_source_sample_count=(
                    candidate.source_sample_count
                ),
                candidate_program_sample_count=(
                    candidate.program_sample_count
                ),
                candidate_sample_count=candidate.sample_count,
                candidate_exact_quiescent=candidate.exact_quiescent,
                candidate_world_execution_receipt_sha256=(
                    candidate.world_execution_receipt_sha256
                ),
                candidate_w1_mount_receipt_sha256=(
                    candidate.w1_mount_receipt_sha256
                ),
                candidate_causal_settlement_receipt_sha256=(
                    candidate.causal_settlement_receipt_sha256
                ),
                candidate_binaural_l5_receipt_sha256=(
                    candidate.binaural_l5_receipt_sha256
                ),
                candidate_receptor_settlement_receipt_sha256=(
                    candidate.receptor_settlement_receipt_sha256
                ),
                candidate_recurrent_q_receipt_sha256=(
                    candidate.recurrent_q_receipt_sha256
                ),
                motor_custody_authority_hmac_sha256=(
                    motor_custody.authority_hmac_sha256
                ),
                motor_custody_authority_receipt_sha256=(
                    motor_custody.authority_receipt_sha256
                ),
                world_before_receipt_sha256=(
                    motor_custody.world_before_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    motor_custody.world_after_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    motor_custody.world_execution_receipt_sha256
                ),
                command_graph_sha256=(
                    motor_custody.command_graph_sha256
                ),
                program=motor_custody.program,
                client_capability_receipt_sha256=(
                    capability.authority_receipt_sha256
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = _sign(
                self._record_key,
                _RECORD_DOMAIN,
                provisional.payload(),
            )
            record = replace(
                provisional,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._verify_record(record)
            self._encoded_state(record)
            prepared = PreparedPendingBodyOwnedVocalConsequence(
                record=record,
                client_capability=capability,
                _state=_MutationState(),
                _owner_authority=self._owner_authority,
                _construction_authority=_PREPARED_AUTHORITY,
            )
            self._prepared = prepared
            return prepared

    def _verify_prepared(
        self,
        prepared: PreparedPendingBodyOwnedVocalConsequence,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedPendingBodyOwnedVocalConsequence,
            )
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or self._prepared is not prepared
            or prepared._state.phase != "prepared"
        ):
            raise ValueError(
                "pending vocal consequence prepared custody changed"
            )
        self._verify_record(prepared.record)
        self._verify_client_capability(
            prepared.client_capability,
            expected_receipt=(
                prepared.record.client_capability_receipt_sha256
            ),
        )

    def discard(
        self,
        prepared: PreparedPendingBodyOwnedVocalConsequence,
    ) -> None:
        """Discard request-1 preparation before any durable publication."""

        with self._lock:
            self._verify_prepared(prepared)
            prepared._state.phase = "discarded"
            self._prepared = None

    def commit(
        self,
        prepared: PreparedPendingBodyOwnedVocalConsequence,
    ) -> PendingBodyOwnedVocalConsequenceCommitUndo:
        with self._lock:
            self._verify_prepared(prepared)
            self._pending = prepared.record
            prepared._state.phase = "committed"
            self._prepared = None
            undo = PendingBodyOwnedVocalConsequenceCommitUndo(
                record=prepared.record,
                client_capability=prepared.client_capability,
                _state=_MutationState(phase="committed"),
                _owner_authority=self._owner_authority,
                _construction_authority=_COMMIT_UNDO_AUTHORITY,
            )
            self._latest_commit_undo = undo
            return undo

    def _verify_commit_undo(
        self,
        undo: PendingBodyOwnedVocalConsequenceCommitUndo,
    ) -> None:
        if (
            not isinstance(
                undo,
                PendingBodyOwnedVocalConsequenceCommitUndo,
            )
            or undo._construction_authority
            is not _COMMIT_UNDO_AUTHORITY
            or undo._owner_authority is not self._owner_authority
            or self._latest_commit_undo is not undo
            or undo._state.phase != "committed"
            or self._pending != undo.record
        ):
            raise ValueError(
                "pending vocal consequence commit undo changed"
            )
        self._verify_record(undo.record)
        self._verify_client_capability(
            undo.client_capability,
            expected_receipt=(
                undo.record.client_capability_receipt_sha256
            ),
        )

    def rollback_commit(
        self,
        undo: PendingBodyOwnedVocalConsequenceCommitUndo,
    ) -> None:
        with self._lock:
            self._verify_commit_undo(undo)
            self._pending = None
            undo._state.phase = "rolled_back"
            self._latest_commit_undo = None

    def finalize_commit(
        self,
        undo: PendingBodyOwnedVocalConsequenceCommitUndo,
    ) -> None:
        with self._lock:
            self._verify_commit_undo(undo)
            undo._state.phase = "finalized"
            self._latest_commit_undo = None

    def open_pending_custody(
        self,
        capability: PendingBodyOwnedVocalClientCapability,
    ) -> RestoredPendingBodyOwnedVocalCustody:
        with self._lock:
            if (
                self._pending is None
                or self._prepared_consume is not None
                or self._latest_consume_undo is not None
            ):
                raise ValueError(
                    "pending vocal consequence is not available"
                )
            record = self._pending
            self._verify_record(record)
            self._verify_client_capability(
                capability,
                expected_receipt=(
                    record.client_capability_receipt_sha256
                ),
            )
            return RestoredPendingBodyOwnedVocalCustody(
                pending_id=record.pending_id,
                candidate_authority_receipt_sha256=(
                    record.candidate_authority_receipt_sha256
                ),
                motor_custody_authority_receipt_sha256=(
                    record.motor_custody_authority_receipt_sha256
                ),
                need_authority_receipt_sha256=(
                    record.need_authority_receipt_sha256
                ),
                witness_authority_receipt_sha256=(
                    record.witness_authority_receipt_sha256
                ),
                witness_settlement_receipt_sha256=(
                    record.witness_settlement_receipt_sha256
                ),
                witness_source_time_start=(
                    record.witness_source_time_start
                ),
                witness_source_time_end=record.witness_source_time_end,
                world_before_receipt_sha256=(
                    record.world_before_receipt_sha256
                ),
                world_after_receipt_sha256=(
                    record.world_after_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    record.world_execution_receipt_sha256
                ),
                command_graph_sha256=record.command_graph_sha256,
                program=record.program,
                pending_authority_receipt_sha256=(
                    record.authority_receipt_sha256
                ),
                _owner_authority=self._owner_authority,
                _construction_authority=_RESTORED_CUSTODY_AUTHORITY,
            )

    def verify_restored_custody(
        self,
        custody: RestoredPendingBodyOwnedVocalCustody,
    ) -> None:
        with self._lock:
            if (
                not isinstance(
                    custody,
                    RestoredPendingBodyOwnedVocalCustody,
                )
                or custody._construction_authority
                is not _RESTORED_CUSTODY_AUTHORITY
                or custody._owner_authority is not self._owner_authority
                or self._pending is None
                or custody.pending_id != self._pending.pending_id
                or custody.pending_authority_receipt_sha256
                != self._pending.authority_receipt_sha256
                or custody.program != self._pending.program
            ):
                raise ValueError(
                    "restored pending vocal custody changed"
                )
            self._verify_record(self._pending)

    def prepare_consume(
        self,
        capability: PendingBodyOwnedVocalClientCapability,
    ) -> PreparedPendingBodyOwnedVocalConsequenceConsume:
        with self._lock:
            if (
                self._pending is None
                or self._prepared is not None
                or self._latest_commit_undo is not None
                or self._prepared_consume is not None
                or self._latest_consume_undo is not None
            ):
                raise ValueError(
                    "pending vocal consequence cannot be consumed"
                )
            self._verify_record(self._pending)
            self._verify_client_capability(
                capability,
                expected_receipt=(
                    self._pending.client_capability_receipt_sha256
                ),
            )
            prepared = (
                PreparedPendingBodyOwnedVocalConsequenceConsume(
                    record=self._pending,
                    _state=_MutationState(),
                    _owner_authority=self._owner_authority,
                    _construction_authority=(
                        _CONSUME_PREPARED_AUTHORITY
                    ),
                )
            )
            self._prepared_consume = prepared
            return prepared

    def _verify_prepared_consume(
        self,
        prepared: PreparedPendingBodyOwnedVocalConsequenceConsume,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedPendingBodyOwnedVocalConsequenceConsume,
            )
            or prepared._construction_authority
            is not _CONSUME_PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or self._prepared_consume is not prepared
            or prepared._state.phase != "prepared"
            or self._pending != prepared.record
        ):
            raise ValueError(
                "pending vocal consequence consume preparation changed"
            )
        self._verify_record(prepared.record)

    def discard_consume(
        self,
        prepared: PreparedPendingBodyOwnedVocalConsequenceConsume,
    ) -> None:
        with self._lock:
            self._verify_prepared_consume(prepared)
            prepared._state.phase = "discarded"
            self._prepared_consume = None

    def commit_consume(
        self,
        prepared: PreparedPendingBodyOwnedVocalConsequenceConsume,
    ) -> PendingBodyOwnedVocalConsequenceConsumeUndo:
        with self._lock:
            self._verify_prepared_consume(prepared)
            self._pending = None
            prepared._state.phase = "committed"
            self._prepared_consume = None
            undo = PendingBodyOwnedVocalConsequenceConsumeUndo(
                record=prepared.record,
                _state=_MutationState(phase="committed"),
                _owner_authority=self._owner_authority,
                _construction_authority=_CONSUME_UNDO_AUTHORITY,
            )
            self._latest_consume_undo = undo
            return undo

    def _verify_consume_undo(
        self,
        undo: PendingBodyOwnedVocalConsequenceConsumeUndo,
    ) -> None:
        if (
            not isinstance(
                undo,
                PendingBodyOwnedVocalConsequenceConsumeUndo,
            )
            or undo._construction_authority
            is not _CONSUME_UNDO_AUTHORITY
            or undo._owner_authority is not self._owner_authority
            or self._latest_consume_undo is not undo
            or undo._state.phase != "committed"
            or self._pending is not None
        ):
            raise ValueError(
                "pending vocal consequence consume undo changed"
            )
        self._verify_record(undo.record)

    def rollback_consume(
        self,
        undo: PendingBodyOwnedVocalConsequenceConsumeUndo,
    ) -> None:
        with self._lock:
            self._verify_consume_undo(undo)
            self._pending = undo.record
            undo._state.phase = "rolled_back"
            self._latest_consume_undo = None

    def verify_consume_undo(
        self,
        undo: PendingBodyOwnedVocalConsequenceConsumeUndo,
    ) -> None:
        with self._lock:
            self._verify_consume_undo(undo)

    def finalize_consume(
        self,
        undo: PendingBodyOwnedVocalConsequenceConsumeUndo,
    ) -> None:
        with self._lock:
            self._verify_consume_undo(undo)
            undo._state.phase = "finalized"
            self._latest_consume_undo = None

    @staticmethod
    def _program_from_record(raw: object) -> ArticulatoryProgram:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "authority_receipt_sha256",
                "body_trajectory",
                "larynx",
                "program_id",
                "sample_count",
                "sample_rate_hz",
                "schema",
                "tract",
            }
            or raw.get("schema") != ARTICULATORY_PROGRAM_SCHEMA
            or raw.get("sample_rate_hz") != VOCAL_SAMPLE_RATE_HZ
            or not isinstance(raw.get("larynx"), Mapping)
            or not isinstance(raw.get("tract"), Mapping)
            or not isinstance(raw.get("body_trajectory"), list)
        ):
            raise ValueError("pending vocal articulatory program changed")
        larynx = raw["larynx"]
        tract = raw["tract"]
        if set(larynx) != {
            "cycle_samples",
            "open_samples",
            "peak_volume_velocity_pcm",
        } or set(tract) != {
            "apex_section_area_mm2",
            "final_section_area_mm2",
            "initial_section_area_mm2",
            "radiation_load_area_mm2",
            "wall_retention_ppm",
        }:
            raise ValueError(
                "pending vocal physical configuration changed"
            )
        try:
            body_trajectory = tuple(
                ArticulatoryBodyTrajectoryInterval(
                    sample_start=item["sample_start"],
                    sample_end=item["sample_end"],
                    glottal_open_samples=item[
                        "glottal_open_samples"
                    ],
                    section_area_mm2=tuple(
                        item["section_area_mm2"]
                    ),
                )
                for item in raw["body_trajectory"]
                if (
                    isinstance(item, Mapping)
                    and set(item)
                    == {
                        "glottal_open_samples",
                        "sample_end",
                        "sample_start",
                        "section_area_mm2",
                    }
                )
            )
            if len(body_trajectory) != len(raw["body_trajectory"]):
                raise ValueError(
                    "pending vocal body trajectory is malformed"
                )
            program = ArticulatoryProgram(
                sample_count=raw["sample_count"],
                larynx=LaryngealExcitationConfiguration(
                    cycle_samples=larynx["cycle_samples"],
                    open_samples=larynx["open_samples"],
                    peak_volume_velocity_pcm=(
                        larynx["peak_volume_velocity_pcm"]
                    ),
                ),
                tract=VocalTractConfiguration(
                    initial_section_area_mm2=tuple(
                        tract["initial_section_area_mm2"]
                    ),
                    apex_section_area_mm2=tuple(
                        tract["apex_section_area_mm2"]
                    ),
                    final_section_area_mm2=tuple(
                        tract["final_section_area_mm2"]
                    ),
                    radiation_load_area_mm2=(
                        tract["radiation_load_area_mm2"]
                    ),
                    wall_retention_ppm=tract["wall_retention_ppm"],
                ),
                body_trajectory=body_trajectory,
                program_id=raw["program_id"],
                authority_receipt_sha256=(
                    raw["authority_receipt_sha256"]
                ),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "pending vocal physical configuration changed"
            ) from exc
        program.verify()
        return program

    def _record_from_mapping(
        self,
        raw: object,
    ) -> PendingBodyOwnedVocalConsequenceRecord:
        if not isinstance(raw, Mapping):
            raise ValueError("pending vocal consequence record changed")
        expected = set(
            PendingBodyOwnedVocalConsequenceRecord.__dataclass_fields__
        ) | {"schema"}
        if set(raw) != expected or raw.get("schema") != RECORD_SCHEMA:
            raise ValueError("pending vocal consequence record changed")
        values = dict(raw)
        values.pop("schema")
        values["program"] = self._program_from_record(values["program"])
        try:
            values["witness_source_time_start"] = _fraction_from_text(
                values["witness_source_time_start"]
            )
            values["witness_source_time_end"] = _fraction_from_text(
                values["witness_source_time_end"]
            )
            record = PendingBodyOwnedVocalConsequenceRecord(**values)
        except TypeError as exc:
            raise ValueError(
                "pending vocal consequence record changed"
            ) from exc
        self._verify_record(record)
        return record

    def _state_body(
        self,
        pending: PendingBodyOwnedVocalConsequenceRecord | None,
    ) -> dict[str, object]:
        return {
            "capacity": 1,
            "max_state_bytes": self._max_state_bytes,
            "pending": None if pending is None else pending.record(),
            "profile_id": self._profile_id,
            "schema": STATE_SCHEMA,
        }

    def _encoded_state(
        self,
        pending: PendingBodyOwnedVocalConsequenceRecord | None,
    ) -> bytes:
        body = self._state_body(pending)
        signature = _sign(
            self._state_key,
            _STATE_DOMAIN,
            body,
        )
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": signature,
        })
        if len(encoded) > self._max_state_bytes:
            raise PendingBodyOwnedVocalConsequenceCapacityError(
                "pending vocal consequence state byte capacity exceeded"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if (
                self._prepared is not None
                or self._latest_commit_undo is not None
                or self._prepared_consume is not None
                or self._latest_consume_undo is not None
            ):
                raise RuntimeError(
                    "cannot snapshot pending vocal consequence transaction"
                )
            return self._encoded_state(self._pending)

    def restore_encoded(self, encoded: bytes) -> None:
        if not isinstance(encoded, bytes):
            raise TypeError(
                "pending vocal consequence state must be bytes"
            )
        if len(encoded) > self._max_state_bytes:
            raise PendingBodyOwnedVocalConsequenceCapacityError(
                "pending vocal consequence state byte capacity exceeded"
            )
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                "pending vocal consequence state is not canonical JSON"
            ) from exc
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError(
                "pending vocal consequence state envelope changed"
            )
        body = envelope["body"]
        if (
            set(body)
            != {
                "capacity",
                "max_state_bytes",
                "pending",
                "profile_id",
                "schema",
            }
            or body.get("schema") != STATE_SCHEMA
            or body.get("capacity") != 1
            or body.get("max_state_bytes") != self._max_state_bytes
            or body.get("profile_id") != self._profile_id
        ):
            raise ValueError(
                "pending vocal consequence state profile changed"
            )
        signature = _sign(
            self._state_key,
            _STATE_DOMAIN,
            body,
        )
        if not hmac.compare_digest(
            signature,
            envelope.get("state_hmac_sha256", ""),
        ):
            raise ValueError(
                "pending vocal consequence state HMAC changed"
            )
        pending = (
            None
            if body["pending"] is None
            else self._record_from_mapping(body["pending"])
        )
        with self._lock:
            if (
                self._prepared is not None
                or self._latest_commit_undo is not None
                or self._prepared_consume is not None
                or self._latest_consume_undo is not None
            ):
                raise RuntimeError(
                    "cannot restore pending vocal consequence transaction"
                )
            prior = self._pending
            self._pending = pending
            try:
                if self._encoded_state(self._pending) != encoded:
                    raise ValueError(
                        "pending vocal consequence state is not canonical"
                    )
            except BaseException:
                self._pending = prior
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded_state(self._pending)
            return {
                "capacity": 1,
                "motor_derived_from_witness_field": True,
                "pending_count": int(self._pending is not None),
                "prepared_count": int(self._prepared is not None),
                "retained_raw_media_bytes": 0,
                "schema": STATUS_SCHEMA,
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._max_state_bytes,
                "wall_time_expiry": False,
                "witness_full_dsf_field_receipts_preserved": True,
            }


__all__ = (
    "CAPABILITY_SCHEMA",
    "ENVELOPE_SCHEMA",
    "PendingBodyOwnedVocalClientCapability",
    "PendingBodyOwnedVocalConsequenceCapacityError",
    "PendingBodyOwnedVocalConsequenceCommitUndo",
    "PendingBodyOwnedVocalConsequenceConsumeUndo",
    "PendingBodyOwnedVocalConsequenceOwner",
    "PendingBodyOwnedVocalConsequenceRecord",
    "PreparedPendingBodyOwnedVocalConsequence",
    "PreparedPendingBodyOwnedVocalConsequenceConsume",
    "RECORD_SCHEMA",
    "RestoredPendingBodyOwnedVocalCustody",
    "STATE_SCHEMA",
    "STATUS_SCHEMA",
)
