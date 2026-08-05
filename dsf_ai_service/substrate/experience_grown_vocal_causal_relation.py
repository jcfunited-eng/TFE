"""Bounded physical recall relations for experience-grown vocal programs.

One finalized body-owned motor fragment may close only the exact unresolved
inquiry that caused it.  The resulting relation is anchored to the retained
causal THING encounter partition and its complete D/M/R/U/C/P/B evidence.
Later recall begins from authenticated settled-experience custody and requires
one unique reciprocal THING plus one live relation.

The owner retains no waveform, label, text, meaning, similarity, score, Chi,
or legacy inquiry-action binding.  THING identifiers are indexes backed by
the retained encounter partition and never identity authorities by themselves.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_inquiry import (
    BodyOwnedFragmentInquiryClosure,
    CausalInquiryOwner,
    CausalInquiryUndo,
    InquiryNeed,
    InquiryWitness,
    PreparedCausalInquiryMutation,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    FullFieldSensoryRoot,
    ThingEncounterPartition,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_thing_reciprocal_mosaic import (
    CausalThingReciprocalEvocation,
    CausalThingReciprocalMosaicOwner,
)
from dsf_ai_service.substrate.experience_grown_vocal_motor_fragment import (
    ExperienceGrownVocalMotorFragment,
    ExperienceGrownVocalMotorFragmentOwner,
)
from dsf_ai_service.substrate.pending_body_owned_vocal_consequence import (
    PendingBodyOwnedVocalClientCapability,
    PendingBodyOwnedVocalConsequenceConsumeUndo,
    PendingBodyOwnedVocalConsequenceOwner,
    PreparedPendingBodyOwnedVocalConsequenceConsume,
    RestoredPendingBodyOwnedVocalCustody,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceConsumerView,
    SettledExperienceCustodyAuthority,
)


RELATION_SCHEMA = "guala.experience_grown_vocal_causal_relation.v1"
ROOT_COMMITMENT_SCHEMA = (
    "guala.experience_grown_vocal_causal_relation.root_commitment.v1"
)
SELECTION_SCHEMA = (
    "guala.experience_grown_vocal_causal_relation.selection.v1"
)
PROGRAM_CUSTODY_SCHEMA = (
    "guala.experience_grown_vocal_causal_relation.program_custody.v1"
)
EVOKED_PROGRAM_CUSTODY_SCHEMA = (
    "guala.experience_grown_vocal_causal_relation."
    "evoked_program_custody.v1"
)
STATE_SCHEMA = (
    "guala.experience_grown_vocal_causal_relation.state.v1"
)
ENVELOPE_SCHEMA = (
    "guala.experience_grown_vocal_causal_relation.state_hmac.v1"
)
VOCAL_CAUSAL_RELATION_SELECTION_CONSUMER_ID = (
    "experience-grown-vocal-causal-relation-selection"
)

_RELATION_DOMAIN = b"guala-experience-grown-vocal-causal-relation-v1\0"
_SELECTION_DOMAIN = (
    b"guala-experience-grown-vocal-causal-relation-selection-v1\0"
)
_PROGRAM_CUSTODY_DOMAIN = (
    b"guala-experience-grown-vocal-causal-relation-program-custody-v1\0"
)
_EVOKED_PROGRAM_DOMAIN = (
    b"guala-experience-grown-vocal-evoked-program-custody-v1\0"
)
_STATE_DOMAIN = (
    b"guala-experience-grown-vocal-causal-relation-state-v1\0"
)
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
_PROGRAM_CUSTODY_AUTHORITY = object()
_EVOKED_PROGRAM_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")
_MAX_CONFIGURED_RELATIONS = 1_000_000
_MAX_CONFIGURED_STATE_BYTES = 256 * 1024 * 1024


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
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("vocal causal relation key changed")
    return raw


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


def _bounded(value: object, label: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > maximum
    ):
        raise ValueError(f"{label} is outside its exact capacity")
    return value


@dataclass(frozen=True, slots=True)
class VocalCausalRootCommitment:
    sense: str
    topology_index: int
    physical_value_sha256: str
    full_evidence_sha256: str

    @classmethod
    def from_root(
        cls,
        root: FullFieldSensoryRoot,
    ) -> "VocalCausalRootCommitment":
        root.verify()
        _verify_root_full_field(root)
        return cls(
            sense=root.sense,
            topology_index=root.topology_index,
            physical_value_sha256=root.physical_value_sha256,
            full_evidence_sha256=hashlib.sha256(
                root.full_evidence_json.encode("utf-8")
            ).hexdigest(),
        )

    def record(self) -> dict[str, object]:
        return {
            "full_evidence_sha256": self.full_evidence_sha256,
            "physical_value_sha256": self.physical_value_sha256,
            "schema": ROOT_COMMITMENT_SCHEMA,
            "sense": self.sense,
            "topology_index": self.topology_index,
        }


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalCausalRelation:
    relation_id: str
    fragment_receipt_sha256: str
    need_receipt_sha256: str
    witness_receipt_sha256: str
    pending_custody_receipt_sha256: str
    inquiry_closure: BodyOwnedFragmentInquiryClosure
    consequence_settlement_receipt_sha256: str
    consequence_partition_receipt_sha256: str
    consequence_boundary_receipts: tuple[tuple[str, str], ...]
    thing_anchor_root_commitments: tuple[
        VocalCausalRootCommitment, ...
    ]
    thing_id: str
    program_id: str
    program_authority_receipt_sha256: str
    command_graph_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "command_graph_sha256": self.command_graph_sha256,
            "consequence_boundary_receipts": [
                [sense, receipt]
                for sense, receipt in self.consequence_boundary_receipts
            ],
            "consequence_partition_receipt_sha256": (
                self.consequence_partition_receipt_sha256
            ),
            "thing_anchor_root_commitments": [
                value.record()
                for value in self.thing_anchor_root_commitments
            ],
            "consequence_settlement_receipt_sha256": (
                self.consequence_settlement_receipt_sha256
            ),
            "fragment_receipt_sha256": self.fragment_receipt_sha256,
            "inquiry_closure": self.inquiry_closure.record(),
            "need_receipt_sha256": self.need_receipt_sha256,
            "pending_custody_receipt_sha256": (
                self.pending_custody_receipt_sha256
            ),
            "program_authority_receipt_sha256": (
                self.program_authority_receipt_sha256
            ),
            "program_id": self.program_id,
            "relation_id": self.relation_id,
            "schema": RELATION_SCHEMA,
            "thing_id": self.thing_id,
            "witness_receipt_sha256": self.witness_receipt_sha256,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalProgramCustody:
    relation_receipt_sha256: str
    current_custody_receipt_sha256: str
    current_capability_receipt_sha256: str
    current_settlement_receipt_sha256: str
    evocation_receipt_sha256: str
    thing_class_receipt_sha256: str
    consequence_partition_receipt_sha256: str
    program: ArticulatoryProgram
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _current_custody_authority: SettledExperienceCustodyAuthority = field(
        repr=False,
        compare=False,
    )
    _current_custody_capability: SettledExperienceConsumerCapability = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "consequence_partition_receipt_sha256": (
                self.consequence_partition_receipt_sha256
            ),
            "current_capability_receipt_sha256": (
                self.current_capability_receipt_sha256
            ),
            "current_custody_receipt_sha256": (
                self.current_custody_receipt_sha256
            ),
            "current_settlement_receipt_sha256": (
                self.current_settlement_receipt_sha256
            ),
            "evocation_receipt_sha256": self.evocation_receipt_sha256,
            "program": self.program.as_record(),
            "relation_receipt_sha256": self.relation_receipt_sha256,
            "schema": PROGRAM_CUSTODY_SCHEMA,
            "thing_class_receipt_sha256": (
                self.thing_class_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalEvokedProgramCustody:
    relation_receipt_sha256: str
    evocation_receipt_sha256: str
    thing_class_receipt_sha256: str
    program: ArticulatoryProgram
    fragment_pressure_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _evocation: CausalThingReciprocalEvocation = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "evocation_receipt_sha256": (
                self.evocation_receipt_sha256
            ),
            "fragment_pressure_sha256": (
                self.fragment_pressure_sha256
            ),
            "program": self.program.as_record(),
            "relation_receipt_sha256": (
                self.relation_receipt_sha256
            ),
            "schema": EVOKED_PROGRAM_CUSTODY_SCHEMA,
            "thing_class_receipt_sha256": (
                self.thing_class_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalCausalSelection:
    state: str
    reason: str
    current_settlement_receipt_sha256: str
    current_partition_receipt_sha256s: tuple[str, ...]
    current_thing_ids: tuple[str, ...]
    cue_senses: tuple[str, ...]
    evocation: CausalThingReciprocalEvocation | None
    candidate_relation_receipt_sha256s: tuple[str, ...]
    program_custody: ExperienceGrownVocalProgramCustody | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "candidate_relation_receipt_sha256s": list(
                self.candidate_relation_receipt_sha256s
            ),
            "current_settlement_receipt_sha256": (
                self.current_settlement_receipt_sha256
            ),
            "current_partition_receipt_sha256s": list(
                self.current_partition_receipt_sha256s
            ),
            "current_thing_ids": list(self.current_thing_ids),
            "cue_senses": list(self.cue_senses),
            "evocation_receipt_sha256": (
                None
                if self.evocation is None
                else self.evocation.authority_receipt_sha256
            ),
            "program_custody_receipt_sha256": (
                None
                if self.program_custody is None
                else self.program_custody.authority_receipt_sha256
            ),
            "reason": self.reason,
            "schema": SELECTION_SCHEMA,
            "state": self.state,
        }


@dataclass(slots=True)
class _TransactionState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class PreparedExperienceGrownVocalCausalRelation:
    relation: ExperienceGrownVocalCausalRelation
    _prior_relations: tuple[
        ExperienceGrownVocalCausalRelation, ...
    ] = field(repr=False, compare=False)
    _staged_relations: tuple[
        ExperienceGrownVocalCausalRelation, ...
    ] = field(repr=False, compare=False)
    _inquiry_prepared: PreparedCausalInquiryMutation = field(
        repr=False,
        compare=False,
    )
    _pending_prepared: (
        PreparedPendingBodyOwnedVocalConsequenceConsume
    ) = field(repr=False, compare=False)
    _state: _TransactionState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ExperienceGrownVocalCausalRelationUndo:
    _prepared: PreparedExperienceGrownVocalCausalRelation = field(
        repr=False,
        compare=False,
    )
    _inquiry_undo: CausalInquiryUndo = field(
        repr=False,
        compare=False,
    )
    _pending_undo: PendingBodyOwnedVocalConsequenceConsumeUndo = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


class ExperienceGrownVocalCausalRelationCapacityError(RuntimeError):
    pass


def _verify_root_full_field(root: FullFieldSensoryRoot) -> None:
    root.verify()
    evidence = json.loads(root.full_evidence_json)
    tuples = evidence.get("field_tuples")
    if not isinstance(tuples, list) or not tuples:
        raise ValueError("vocal causal root has no full field tuples")
    for field_tuple in tuples:
        fields = field_tuple.get("fields")
        if (
            not isinstance(fields, list)
            or tuple(item[0] for item in fields) != DSF_FIELD_ORDER
        ):
            raise ValueError(
                "vocal causal root lost D/M/R/U/C/P/B field authority"
            )


def _root_commitments(
    roots: tuple[FullFieldSensoryRoot, ...],
) -> tuple[VocalCausalRootCommitment, ...]:
    return tuple(
        VocalCausalRootCommitment.from_root(root)
        for root in roots
    )


def _boundaries_from_roots(
    roots: tuple[FullFieldSensoryRoot, ...],
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for root in roots:
        evidence = json.loads(root.full_evidence_json)
        pair = (
            root.sense,
            _sha(
                evidence.get("boundary_receipt_sha256"),
                "vocal causal sensory boundary",
            ),
        )
        if pair not in result:
            result.append(pair)
    return tuple(result)


class ExperienceGrownVocalCausalRelationOwner:
    """Own atomic inquiry closure and later physical vocal recall."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_relations: int,
        max_state_bytes: int,
        fragment_owner: ExperienceGrownVocalMotorFragmentOwner,
        inquiry_owner: CausalInquiryOwner,
        pending_owner: PendingBodyOwnedVocalConsequenceOwner,
        thing_owner: CausalThingMosaicOwner,
        reciprocal_owner: CausalThingReciprocalMosaicOwner,
        motor_owner: ArticulatorySelfVocalMotorOwner,
    ) -> None:
        if not isinstance(
            fragment_owner,
            ExperienceGrownVocalMotorFragmentOwner,
        ):
            raise TypeError("vocal causal relation requires fragment custody")
        if not isinstance(inquiry_owner, CausalInquiryOwner):
            raise TypeError("vocal causal relation requires inquiry custody")
        if not isinstance(
            pending_owner,
            PendingBodyOwnedVocalConsequenceOwner,
        ):
            raise TypeError("vocal causal relation requires pending custody")
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError("vocal causal relation requires THING custody")
        if not isinstance(
            reciprocal_owner,
            CausalThingReciprocalMosaicOwner,
        ):
            raise TypeError(
                "vocal causal relation requires reciprocal THING custody"
            )
        if not isinstance(motor_owner, ArticulatorySelfVocalMotorOwner):
            raise TypeError("vocal causal relation requires motor custody")
        if (
            fragment_owner._inquiry is not inquiry_owner
            or fragment_owner._things is not thing_owner
            or fragment_owner._motor is not motor_owner
            or pending_owner._inquiry is not inquiry_owner
            or reciprocal_owner._things is not thing_owner
        ):
            raise ValueError(
                "vocal causal relation crossed substrate ownership"
            )
        root_key = _key(authority_key)
        self._relation_key = hashlib.sha256(
            _RELATION_DOMAIN + root_key
        ).digest()
        self._selection_key = hashlib.sha256(
            _SELECTION_DOMAIN + root_key
        ).digest()
        self._program_custody_key = hashlib.sha256(
            _PROGRAM_CUSTODY_DOMAIN + root_key
        ).digest()
        self._evoked_program_key = hashlib.sha256(
            _EVOKED_PROGRAM_DOMAIN + root_key
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + root_key
        ).digest()
        self._max_relations = _bounded(
            max_relations,
            "vocal causal relation count",
            _MAX_CONFIGURED_RELATIONS,
        )
        self._max_state_bytes = _bounded(
            max_state_bytes,
            "vocal causal relation state bytes",
            _MAX_CONFIGURED_STATE_BYTES,
        )
        self._fragments = fragment_owner
        self._inquiry = inquiry_owner
        self._pending = pending_owner
        self._things = thing_owner
        self._reciprocal = reciprocal_owner
        self._motor = motor_owner
        self._relations: tuple[
            ExperienceGrownVocalCausalRelation, ...
        ] = ()
        self._prepared: (
            PreparedExperienceGrownVocalCausalRelation | None
        ) = None
        self._latest_undo: (
            ExperienceGrownVocalCausalRelationUndo | None
        ) = None
        self._owner_authority = object()
        self._evoked_program_owner_authority = object()
        self._lock = threading.RLock()
        self._encoded(self._relations)

    @property
    def relations(
        self,
    ) -> tuple[ExperienceGrownVocalCausalRelation, ...]:
        with self._lock:
            return self._relations

    def _program(
        self,
        relation: ExperienceGrownVocalCausalRelation,
    ) -> ArticulatoryProgram:
        self._motor.snapshot_encoded()
        matches = tuple(
            program
            for program in self._motor.programs
            if (
                program.program_id == relation.program_id
                and program.authority_receipt_sha256
                == relation.program_authority_receipt_sha256
            )
        )
        if len(matches) != 1:
            raise ValueError(
                "vocal causal relation lost exact motor program custody"
            )
        return matches[0]

    def _fragment(
        self,
        receipt: str,
    ) -> ExperienceGrownVocalMotorFragment:
        self._fragments.snapshot_encoded()
        matches = tuple(
            fragment
            for fragment in self._fragments.fragments
            if fragment.authority_receipt_sha256 == receipt
        )
        if len(matches) != 1:
            raise ValueError(
                "vocal causal relation lacks one finalized fragment"
            )
        return matches[0]

    def _partition(
        self,
        *,
        thing_id: str,
        partition_receipt: str,
    ) -> ThingEncounterPartition:
        matches = tuple(
            partition
            for mosaic in self._things.mosaics
            if mosaic.thing_id == thing_id
            for partition in mosaic.partitions
            if (
                partition.authority_receipt_sha256
                == partition_receipt
            )
        )
        if len(matches) != 1:
            raise ValueError(
                "vocal causal relation lacks one retained THING partition"
            )
        self._things._partition_authority.verify(matches[0])
        for root in matches[0].full_field_roots:
            _verify_root_full_field(root)
        return matches[0]

    def _unique_anchor_partition(
        self,
        *,
        thing_id: str,
        matching_route_keys: tuple[tuple[str, str], ...],
    ) -> ThingEncounterPartition:
        route_keys = frozenset(matching_route_keys)
        matches = tuple(
            partition
            for mosaic in self._things.mosaics
            if mosaic.thing_id == thing_id
            for partition in mosaic.partitions
            if route_keys.issubset(
                root.route_key for root in partition.full_field_roots
            )
        )
        if len(matches) != 1:
            raise ValueError(
                "vocal causal relation lacks one exact route-bearing "
                "THING partition"
            )
        self._things._partition_authority.verify(matches[0])
        return matches[0]

    def _verify_relation(
        self,
        relation: ExperienceGrownVocalCausalRelation,
    ) -> None:
        if not isinstance(
            relation,
            ExperienceGrownVocalCausalRelation,
        ):
            raise TypeError("vocal causal relation is not typed")
        for digest, label in (
            (relation.relation_id, "vocal causal relation identity"),
            (
                relation.fragment_receipt_sha256,
                "vocal causal relation fragment",
            ),
            (relation.need_receipt_sha256, "vocal causal relation need"),
            (
                relation.witness_receipt_sha256,
                "vocal causal relation witness",
            ),
            (
                relation.pending_custody_receipt_sha256,
                "vocal causal relation pending custody",
            ),
            (
                relation.consequence_settlement_receipt_sha256,
                "vocal causal relation consequence",
            ),
            (
                relation.consequence_partition_receipt_sha256,
                "vocal causal relation partition",
            ),
            (relation.thing_id, "vocal causal relation THING"),
            (relation.program_id, "vocal causal relation program"),
            (
                relation.program_authority_receipt_sha256,
                "vocal causal relation program authority",
            ),
            (
                relation.command_graph_sha256,
                "vocal causal relation command graph",
            ),
            (relation.authority_hmac_sha256, "vocal causal relation HMAC"),
            (
                relation.authority_receipt_sha256,
                "vocal causal relation authority",
            ),
        ):
            _sha(digest, label)
        self._inquiry.verify_body_owned_fragment_closure(
            relation.inquiry_closure
        )
        if (
            relation.inquiry_closure.need_receipt_sha256
            != relation.need_receipt_sha256
            or relation.inquiry_closure.witness_receipt_sha256
            != relation.witness_receipt_sha256
            or relation.inquiry_closure.fragment_receipt_sha256
            != relation.fragment_receipt_sha256
            or relation.inquiry_closure.pending_custody_receipt_sha256
            != relation.pending_custody_receipt_sha256
            or relation.inquiry_closure
            .consequence_settlement_receipt_sha256
            != relation.consequence_settlement_receipt_sha256
            or relation.inquiry_closure
            .program_authority_receipt_sha256
            != relation.program_authority_receipt_sha256
        ):
            raise ValueError(
                "vocal causal relation changed inquiry closure"
            )
        fragment = self._fragment(
            relation.fragment_receipt_sha256
        )
        if (
            fragment.need_receipt_sha256
            != relation.need_receipt_sha256
            or fragment.witness_receipt_sha256
            != relation.witness_receipt_sha256
            or fragment.consequence_settlement_receipt_sha256
            != relation.consequence_settlement_receipt_sha256
            or fragment.unique_thing_id != relation.thing_id
            or fragment.program_id != relation.program_id
            or fragment.program_authority_receipt_sha256
            != relation.program_authority_receipt_sha256
            or fragment.command_graph_sha256
            != relation.command_graph_sha256
            or fragment.consequence_boundary_receipts
            != relation.consequence_boundary_receipts
        ):
            raise ValueError("vocal causal relation changed its fragment")
        self._program(relation)
        partition = self._partition(
            thing_id=relation.thing_id,
            partition_receipt=(
                relation.consequence_partition_receipt_sha256
            ),
        )
        if (
            _root_commitments(partition.full_field_roots)
            != relation.thing_anchor_root_commitments
        ):
            raise ValueError(
                "vocal causal relation changed full-field partition evidence"
            )
        identity_payload = {
            "consequence_partition_receipt_sha256": (
                relation.consequence_partition_receipt_sha256
            ),
            "fragment_receipt_sha256": (
                relation.fragment_receipt_sha256
            ),
            "program_authority_receipt_sha256": (
                relation.program_authority_receipt_sha256
            ),
            "schema": RELATION_SCHEMA,
        }
        if relation.relation_id != _digest(identity_payload):
            raise ValueError("vocal causal relation identity changed")
        expected = hmac.new(
            self._relation_key,
            _RELATION_DOMAIN + _canonical(relation.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                relation.authority_hmac_sha256,
            )
            or relation.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": relation.payload(),
            })
        ):
            raise ValueError("vocal causal relation authority changed")

    def _body(
        self,
        relations: tuple[
            ExperienceGrownVocalCausalRelation, ...
        ],
    ) -> dict[str, object]:
        return {
            "max_relations": self._max_relations,
            "relations": [value.record() for value in relations],
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        relations: tuple[
            ExperienceGrownVocalCausalRelation, ...
        ],
    ) -> bytes:
        if (
            len(relations) > self._max_relations
            or tuple(value.relation_id for value in relations)
            != tuple(sorted({
                value.relation_id for value in relations
            }))
        ):
            raise ValueError("vocal causal relation extent changed")
        for relation in relations:
            self._verify_relation(relation)
        body = self._body(relations)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._max_state_bytes:
            raise ExperienceGrownVocalCausalRelationCapacityError(
                "vocal causal relation state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None or self._latest_undo is not None:
                raise RuntimeError(
                    "vocal causal relation cannot snapshot a transaction"
                )
            return self._encoded(self._relations)

    def _seal_relation(
        self,
        *,
        fragment: ExperienceGrownVocalMotorFragment,
        pending_custody: RestoredPendingBodyOwnedVocalCustody,
        closure: BodyOwnedFragmentInquiryClosure,
        partition: ThingEncounterPartition,
    ) -> ExperienceGrownVocalCausalRelation:
        identity_payload = {
            "consequence_partition_receipt_sha256": (
                partition.authority_receipt_sha256
            ),
            "fragment_receipt_sha256": (
                fragment.authority_receipt_sha256
            ),
            "program_authority_receipt_sha256": (
                fragment.program_authority_receipt_sha256
            ),
            "schema": RELATION_SCHEMA,
        }
        provisional = ExperienceGrownVocalCausalRelation(
            relation_id=_digest(identity_payload),
            fragment_receipt_sha256=(
                fragment.authority_receipt_sha256
            ),
            need_receipt_sha256=fragment.need_receipt_sha256,
            witness_receipt_sha256=fragment.witness_receipt_sha256,
            pending_custody_receipt_sha256=(
                pending_custody.pending_authority_receipt_sha256
            ),
            inquiry_closure=closure,
            consequence_settlement_receipt_sha256=(
                fragment.consequence_settlement_receipt_sha256
            ),
            consequence_partition_receipt_sha256=(
                partition.authority_receipt_sha256
            ),
            consequence_boundary_receipts=(
                fragment.consequence_boundary_receipts
            ),
            thing_anchor_root_commitments=_root_commitments(
                partition.full_field_roots
            ),
            thing_id=fragment.unique_thing_id,
            program_id=fragment.program_id,
            program_authority_receipt_sha256=(
                fragment.program_authority_receipt_sha256
            ),
            command_graph_sha256=fragment.command_graph_sha256,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._relation_key,
            _RELATION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return ExperienceGrownVocalCausalRelation(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def prepare(
        self,
        *,
        fragment: ExperienceGrownVocalMotorFragment,
        need: InquiryNeed,
        witness: InquiryWitness,
        pending_capability: PendingBodyOwnedVocalClientCapability,
        pending_custody: RestoredPendingBodyOwnedVocalCustody,
        later_custody_authority: SettledExperienceCustodyAuthority,
        later_custody_capability: SettledExperienceConsumerCapability,
    ) -> PreparedExperienceGrownVocalCausalRelation:
        with self._lock:
            if self._prepared is not None or self._latest_undo is not None:
                raise RuntimeError(
                    "vocal causal relation already has a transaction"
                )
            if len(self._relations) >= self._max_relations:
                raise ExperienceGrownVocalCausalRelationCapacityError(
                    "vocal causal relation capacity exhausted"
                )
            retained_fragment = self._fragment(
                fragment.authority_receipt_sha256
            )
            if retained_fragment != fragment:
                raise ValueError(
                    "vocal causal relation changed finalized fragment"
                )
            if (
                self._inquiry.active_need != need
                or need.witness_receipt_sha256
                != witness.authority_receipt_sha256
                or fragment.need_receipt_sha256
                != need.authority_receipt_sha256
                or fragment.witness_receipt_sha256
                != witness.authority_receipt_sha256
            ):
                raise ValueError(
                    "vocal causal relation changed exact active inquiry"
                )
            self._pending.verify_restored_custody(pending_custody)
            if (
                pending_custody.need_authority_receipt_sha256
                != need.authority_receipt_sha256
                or pending_custody.witness_authority_receipt_sha256
                != witness.authority_receipt_sha256
                or pending_custody.candidate_authority_receipt_sha256
                != fragment.candidate_receipt_sha256
                or pending_custody.program.program_id
                != fragment.program_id
                or pending_custody.program.authority_receipt_sha256
                != fragment.program_authority_receipt_sha256
                or pending_custody.command_graph_sha256
                != fragment.command_graph_sha256
            ):
                raise ValueError(
                    "vocal causal relation changed restored pending custody"
                )
            view = later_custody_authority.open_child(
                later_custody_capability
            )
            if (
                view.parent_custody_receipt_sha256
                != fragment.consequence_custody_receipt_sha256
                or later_custody_capability.authority_receipt_sha256
                != fragment.consequence_capability_receipt_sha256
                or view.source_occurrence_id
                != fragment.consequence_source_occurrence_id
                or view.causal_settlement.authority_receipt_sha256
                != fragment.consequence_settlement_receipt_sha256
            ):
                raise ValueError(
                    "vocal causal relation changed consequence custody"
                )
            roots = full_field_sensory_roots(
                view.causal_settlement
            )
            for root in roots:
                _verify_root_full_field(root)
            if (
                len({root.sense for root in roots}) < 2
                or _boundaries_from_roots(roots)
                != fragment.consequence_boundary_receipts
            ):
                raise ValueError(
                    "vocal causal relation consequence is not complete "
                    "multisensory full-field evidence"
                )
            route = self._things.route(view.causal_settlement)
            if (
                route.state != "unique"
                or route.thing_ids != (fragment.unique_thing_id,)
            ):
                raise ValueError(
                    "vocal causal relation consequence lost unique THING"
                )
            partition = self._unique_anchor_partition(
                thing_id=fragment.unique_thing_id,
                matching_route_keys=route.matching_route_keys,
            )
            if (
                any(
                    relation.fragment_receipt_sha256
                    == fragment.authority_receipt_sha256
                    for relation in self._relations
                )
            ):
                raise ValueError(
                    "vocal causal relation changed or replayed partition"
                )
            inquiry_prepared = (
                self._inquiry.prepare_body_owned_fragment_closure(
                    need=need,
                    witness=witness,
                    fragment_receipt_sha256=(
                        fragment.authority_receipt_sha256
                    ),
                    pending_custody_receipt_sha256=(
                        pending_custody.pending_authority_receipt_sha256
                    ),
                    consequence_settlement_receipt_sha256=(
                        fragment.consequence_settlement_receipt_sha256
                    ),
                    program_authority_receipt_sha256=(
                        fragment.program_authority_receipt_sha256
                    ),
                )
            )
            pending_prepared = None
            try:
                pending_prepared = self._pending.prepare_consume(
                    pending_capability
                )
                closure = inquiry_prepared.result
                if not isinstance(
                    closure,
                    BodyOwnedFragmentInquiryClosure,
                ):
                    raise TypeError(
                        "vocal causal relation inquiry closure is not typed"
                    )
                relation = self._seal_relation(
                    fragment=fragment,
                    pending_custody=pending_custody,
                    closure=closure,
                    partition=partition,
                )
                staged = tuple(sorted(
                    (*self._relations, relation),
                    key=lambda value: value.relation_id,
                ))
                self._encoded(staged)
                prepared = PreparedExperienceGrownVocalCausalRelation(
                    relation=relation,
                    _prior_relations=self._relations,
                    _staged_relations=staged,
                    _inquiry_prepared=inquiry_prepared,
                    _pending_prepared=pending_prepared,
                    _state=_TransactionState(),
                    _owner_authority=self._owner_authority,
                    _construction_authority=_PREPARED_AUTHORITY,
                )
                self._prepared = prepared
                return prepared
            except BaseException:
                if pending_prepared is not None:
                    self._pending.discard_consume(pending_prepared)
                self._inquiry.discard_prepared(inquiry_prepared)
                raise

    def _verify_prepared(
        self,
        prepared: PreparedExperienceGrownVocalCausalRelation,
    ) -> None:
        if (
            not isinstance(
                prepared,
                PreparedExperienceGrownVocalCausalRelation,
            )
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or self._prepared is not prepared
            or prepared._state.phase != "prepared"
            or self._relations != prepared._prior_relations
        ):
            raise ValueError(
                "vocal causal relation preparation changed custody"
            )
        self._encoded(prepared._prior_relations)
        self._encoded(prepared._staged_relations)

    def discard(
        self,
        prepared: PreparedExperienceGrownVocalCausalRelation,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            self._pending.discard_consume(
                prepared._pending_prepared
            )
            self._inquiry.discard_prepared(
                prepared._inquiry_prepared
            )
            self._prepared = None
            prepared._state.phase = "discarded"

    def commit(
        self,
        prepared: PreparedExperienceGrownVocalCausalRelation,
    ) -> ExperienceGrownVocalCausalRelationUndo:
        with self._lock:
            self._verify_prepared(prepared)
            inquiry_undo = self._inquiry.commit_prepared(
                prepared._inquiry_prepared
            )
            pending_undo = None
            try:
                pending_undo = self._pending.commit_consume(
                    prepared._pending_prepared
                )
                self._relations = prepared._staged_relations
                prepared._state.phase = "committed"
                self._prepared = None
                undo = ExperienceGrownVocalCausalRelationUndo(
                    _prepared=prepared,
                    _inquiry_undo=inquiry_undo,
                    _pending_undo=pending_undo,
                    _owner_authority=self._owner_authority,
                    _construction_authority=_UNDO_AUTHORITY,
                )
                self._latest_undo = undo
                return undo
            except BaseException:
                if pending_undo is not None:
                    self._pending.rollback_consume(pending_undo)
                else:
                    self._pending.discard_consume(
                        prepared._pending_prepared
                    )
                self._inquiry.rollback_committed(inquiry_undo)
                self._prepared = None
                prepared._state.phase = "failed"
                raise

    def _verify_undo(
        self,
        undo: ExperienceGrownVocalCausalRelationUndo,
    ) -> None:
        if (
            not isinstance(
                undo,
                ExperienceGrownVocalCausalRelationUndo,
            )
            or undo._construction_authority is not _UNDO_AUTHORITY
            or undo._owner_authority is not self._owner_authority
            or self._latest_undo is not undo
            or undo._prepared._state.phase != "committed"
            or self._prepared is not None
            or self._relations != undo._prepared._staged_relations
        ):
            raise ValueError("vocal causal relation undo changed custody")
        self._encoded(self._relations)
        self._inquiry.verify_committed(undo._inquiry_undo)
        self._pending.verify_consume_undo(undo._pending_undo)

    def rollback(
        self,
        undo: ExperienceGrownVocalCausalRelationUndo,
    ) -> None:
        with self._lock:
            self._verify_undo(undo)
            self._relations = undo._prepared._prior_relations
            self._pending.rollback_consume(undo._pending_undo)
            self._inquiry.rollback_committed(undo._inquiry_undo)
            undo._prepared._state.phase = "rolled_back"
            self._latest_undo = None

    def finalize(
        self,
        undo: ExperienceGrownVocalCausalRelationUndo,
    ) -> ExperienceGrownVocalCausalRelation:
        with self._lock:
            self._verify_undo(undo)
            self._inquiry.finalize_committed(undo._inquiry_undo)
            self._pending.finalize_consume(undo._pending_undo)
            undo._prepared._state.phase = "finalized"
            self._latest_undo = None
            return undo._prepared.relation

    def _program_custody(
        self,
        *,
        relation: ExperienceGrownVocalCausalRelation,
        program: ArticulatoryProgram,
        custody_receipt: str,
        capability_receipt: str,
        settlement_receipt: str,
        evocation: CausalThingReciprocalEvocation,
        current_custody_authority: SettledExperienceCustodyAuthority,
        current_custody_capability: SettledExperienceConsumerCapability,
    ) -> ExperienceGrownVocalProgramCustody:
        candidate = evocation.candidate
        if candidate is None:
            raise ValueError(
                "vocal causal program custody lacks unique THING"
            )
        provisional = ExperienceGrownVocalProgramCustody(
            relation_receipt_sha256=(
                relation.authority_receipt_sha256
            ),
            current_custody_receipt_sha256=custody_receipt,
            current_capability_receipt_sha256=capability_receipt,
            current_settlement_receipt_sha256=settlement_receipt,
            evocation_receipt_sha256=(
                evocation.authority_receipt_sha256
            ),
            thing_class_receipt_sha256=(
                candidate.authority_receipt_sha256
            ),
            consequence_partition_receipt_sha256=(
                relation.consequence_partition_receipt_sha256
            ),
            program=program,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _current_custody_authority=current_custody_authority,
            _current_custody_capability=current_custody_capability,
            _owner_authority=self._owner_authority,
            _construction_authority=_PROGRAM_CUSTODY_AUTHORITY,
        )
        signature = hmac.new(
            self._program_custody_key,
            _PROGRAM_CUSTODY_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return ExperienceGrownVocalProgramCustody(
            relation_receipt_sha256=(
                provisional.relation_receipt_sha256
            ),
            current_custody_receipt_sha256=(
                provisional.current_custody_receipt_sha256
            ),
            current_capability_receipt_sha256=(
                provisional.current_capability_receipt_sha256
            ),
            current_settlement_receipt_sha256=(
                provisional.current_settlement_receipt_sha256
            ),
            evocation_receipt_sha256=(
                provisional.evocation_receipt_sha256
            ),
            thing_class_receipt_sha256=(
                provisional.thing_class_receipt_sha256
            ),
            consequence_partition_receipt_sha256=(
                provisional.consequence_partition_receipt_sha256
            ),
            program=program,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            _current_custody_authority=current_custody_authority,
            _current_custody_capability=current_custody_capability,
            _owner_authority=self._owner_authority,
            _construction_authority=_PROGRAM_CUSTODY_AUTHORITY,
        )

    def verify_program_custody(
        self,
        custody: ExperienceGrownVocalProgramCustody,
    ) -> None:
        if (
            not isinstance(custody, ExperienceGrownVocalProgramCustody)
            or custody._construction_authority
            is not _PROGRAM_CUSTODY_AUTHORITY
            or custody._owner_authority is not self._owner_authority
            or not isinstance(
                custody._current_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                custody._current_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody._current_custody_capability.consumer_id
            != VOCAL_CAUSAL_RELATION_SELECTION_CONSUMER_ID
        ):
            raise ValueError(
                "experience-grown vocal program custody changed"
            )
        for digest, label in (
            (
                custody.relation_receipt_sha256,
                "vocal program custody relation",
            ),
            (
                custody.current_custody_receipt_sha256,
                "vocal program current custody",
            ),
            (
                custody.current_capability_receipt_sha256,
                "vocal program current capability",
            ),
            (
                custody.current_settlement_receipt_sha256,
                "vocal program current settlement",
            ),
            (
                custody.evocation_receipt_sha256,
                "vocal program evocation",
            ),
            (
                custody.thing_class_receipt_sha256,
                "vocal program THING class",
            ),
            (
                custody.consequence_partition_receipt_sha256,
                "vocal program partition",
            ),
            (custody.authority_hmac_sha256, "vocal program custody HMAC"),
            (
                custody.authority_receipt_sha256,
                "vocal program custody authority",
            ),
        ):
            _sha(digest, label)
        matches = tuple(
            relation
            for relation in self._relations
            if relation.authority_receipt_sha256
            == custody.relation_receipt_sha256
        )
        if (
            len(matches) != 1
            or self._program(matches[0]) != custody.program
            or matches[0].consequence_partition_receipt_sha256
            != custody.consequence_partition_receipt_sha256
        ):
            raise ValueError(
                "vocal program custody lost retained relation"
            )
        view = custody._current_custody_authority.open_child(
            custody._current_custody_capability
        )
        if (
            view.parent_custody_receipt_sha256
            != custody.current_custody_receipt_sha256
            or custody._current_custody_capability
            .authority_receipt_sha256
            != custody.current_capability_receipt_sha256
            or view.causal_settlement.authority_receipt_sha256
            != custody.current_settlement_receipt_sha256
        ):
            raise ValueError(
                "vocal program custody lost current settled experience"
            )
        expected = hmac.new(
            self._program_custody_key,
            _PROGRAM_CUSTODY_DOMAIN + _canonical(custody.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                custody.authority_hmac_sha256,
            )
            or custody.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": custody.payload(),
            })
        ):
            raise ValueError("vocal program custody authority changed")

    def open_program_custody(
        self,
        custody: ExperienceGrownVocalProgramCustody,
    ) -> SettledExperienceConsumerView:
        """Reopen the request-live settled view behind typed program custody."""

        self.verify_program_custody(custody)
        return custody._current_custody_authority.open_child(
            custody._current_custody_capability
        )

    def verified_program_fragment(
        self,
        custody: ExperienceGrownVocalProgramCustody,
    ) -> ExperienceGrownVocalMotorFragment:
        """Return the finalized physical origin of one live program custody."""

        self.verify_program_custody(custody)
        matches = tuple(
            relation
            for relation in self._relations
            if relation.authority_receipt_sha256
            == custody.relation_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "vocal program custody lost one retained relation"
            )
        fragment = self._fragment(matches[0].fragment_receipt_sha256)
        if (
            fragment.program_id != custody.program.program_id
            or fragment.program_authority_receipt_sha256
            != custody.program.authority_receipt_sha256
        ):
            raise ValueError(
                "vocal program custody changed finalized fragment"
            )
        return fragment

    def _selection(
        self,
        *,
        state: str,
        reason: str,
        settlement_receipt: str,
        current_partition_receipts: tuple[str, ...],
        current_thing_ids: tuple[str, ...],
        cue_senses: tuple[str, ...],
        evocation: CausalThingReciprocalEvocation | None,
        candidates: tuple[ExperienceGrownVocalCausalRelation, ...],
        program_custody: ExperienceGrownVocalProgramCustody | None,
    ) -> ExperienceGrownVocalCausalSelection:
        provisional = ExperienceGrownVocalCausalSelection(
            state=state,
            reason=reason,
            current_settlement_receipt_sha256=settlement_receipt,
            current_partition_receipt_sha256s=tuple(sorted(
                current_partition_receipts
            )),
            current_thing_ids=tuple(sorted(current_thing_ids)),
            cue_senses=cue_senses,
            evocation=evocation,
            candidate_relation_receipt_sha256s=tuple(sorted(
                value.authority_receipt_sha256
                for value in candidates
            )),
            program_custody=program_custody,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._selection_key,
            _SELECTION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = ExperienceGrownVocalCausalSelection(
            state=provisional.state,
            reason=provisional.reason,
            current_settlement_receipt_sha256=(
                provisional.current_settlement_receipt_sha256
            ),
            current_partition_receipt_sha256s=(
                provisional.current_partition_receipt_sha256s
            ),
            current_thing_ids=provisional.current_thing_ids,
            cue_senses=provisional.cue_senses,
            evocation=evocation,
            candidate_relation_receipt_sha256s=(
                provisional.candidate_relation_receipt_sha256s
            ),
            program_custody=program_custody,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify_selection(result)
        return result

    def verify_selection(
        self,
        value: ExperienceGrownVocalCausalSelection,
    ) -> None:
        if not isinstance(
            value,
            ExperienceGrownVocalCausalSelection,
        ):
            raise TypeError("vocal causal selection is not typed")
        if (
            value.state not in {"ready", "silent"}
            or value.current_partition_receipt_sha256s
            != tuple(sorted(value.current_partition_receipt_sha256s))
            or value.current_thing_ids
            != tuple(sorted(value.current_thing_ids))
            or value.candidate_relation_receipt_sha256s
            != tuple(sorted(
                value.candidate_relation_receipt_sha256s
            ))
        ):
            raise ValueError("vocal causal selection extent changed")
        if value.evocation is None:
            if (
                value.state != "silent"
                or value.cue_senses
                or value.program_custody is not None
                or value.candidate_relation_receipt_sha256s
            ):
                raise ValueError(
                    "unowned vocal causal selection selected authority"
                )
        else:
            self._reciprocal.verify_evocation(value.evocation)
            if (
                not value.cue_senses
                or value.cue_senses != value.evocation.cue_senses
            ):
                raise ValueError(
                    "vocal causal selection changed derived cue senses"
                )
        for digest, label in (
            (
                value.current_settlement_receipt_sha256,
                "vocal causal selection settlement",
            ),
            (
                value.authority_hmac_sha256,
                "vocal causal selection HMAC",
            ),
            (
                value.authority_receipt_sha256,
                "vocal causal selection authority",
            ),
        ):
            _sha(digest, label)
        retained_receipts = {
            relation.authority_receipt_sha256
            for relation in self._relations
        }
        if any(
            receipt not in retained_receipts
            for receipt in value.candidate_relation_receipt_sha256s
        ):
            raise ValueError(
                "vocal causal selection lost retained relation"
            )
        if value.state == "ready":
            if (
                len(value.candidate_relation_receipt_sha256s) != 1
                or not value.current_partition_receipt_sha256s
                or len(value.current_thing_ids) != 1
                or value.evocation is None
                or value.program_custody is None
            ):
                raise ValueError(
                    "ready vocal causal selection lost program custody"
                )
            self.verify_program_custody(value.program_custody)
        elif value.program_custody is not None:
            raise ValueError(
                "silent vocal causal selection selected a program"
            )
        expected = hmac.new(
            self._selection_key,
            _SELECTION_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("vocal causal selection authority changed")

    def select(
        self,
        *,
        current_custody_authority: SettledExperienceCustodyAuthority,
        current_custody_capability: SettledExperienceConsumerCapability,
    ) -> ExperienceGrownVocalCausalSelection:
        if (
            not isinstance(
                current_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                current_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or current_custody_capability.consumer_id
            != VOCAL_CAUSAL_RELATION_SELECTION_CONSUMER_ID
        ):
            raise ValueError(
                "vocal causal selection lacks exact settled custody"
            )
        with self._lock:
            self._encoded(self._relations)
            view = current_custody_authority.open_child(
                current_custody_capability
            )
            roots = full_field_sensory_roots(
                view.causal_settlement
            )
            for root in roots:
                _verify_root_full_field(root)
            exact_partitions = tuple(
                (mosaic, partition)
                for mosaic in self._things.mosaics
                for partition in mosaic.partitions
                if partition.settlement_receipt_sha256
                == view.causal_settlement.authority_receipt_sha256
            )
            continuity = (
                self._things._partition_authority
                .held_entity_continuity(view.world_observation)
            )
            current_partitions = (
                ()
                if continuity is None
                else tuple(
                    (mosaic, partition)
                    for mosaic in self._things.mosaics
                    for partition in mosaic.partitions
                    if partition.entity_continuity_hmac_sha256
                    == continuity
                )
            )
            current_partition_receipts = tuple(
                partition.authority_receipt_sha256
                for _mosaic, partition in current_partitions
            )
            current_thing_ids = tuple(sorted({
                mosaic.thing_id
                for mosaic, _partition in current_partitions
            }))
            if len(current_thing_ids) != 1:
                return self._selection(
                    state="silent",
                    reason=(
                        "current_thing_ambiguous"
                        if current_thing_ids
                        else "current_thing_unresolved"
                    ),
                    settlement_receipt=(
                        view.causal_settlement.authority_receipt_sha256
                    ),
                    current_partition_receipts=(
                        current_partition_receipts
                    ),
                    current_thing_ids=current_thing_ids,
                    cue_senses=(),
                    evocation=None,
                    candidates=(),
                    program_custody=None,
                )
            for _mosaic, partition in current_partitions:
                self._things._partition_authority.verify(partition)
            for _mosaic, partition in exact_partitions:
                self._things._partition_authority.verify(partition)
                if partition.full_field_roots != roots:
                    raise ValueError(
                        "current vocal cue partition changed full field"
                    )
            current_thing_id = current_thing_ids[0]
            entity_senses = {
                sense
                for _mosaic, partition in current_partitions
                for sense, _physical_root in partition.entity_root_keys
            }
            material_senses = {
                root.sense
                for root in roots
                if root.sense in entity_senses
            }
            available_cue_senses = tuple(
                sense.value
                for sense in SENSE_ORDER
                if sense.value in material_senses
            )
            if not available_cue_senses:
                return self._selection(
                    state="silent",
                    reason="current_thing_has_no_material_cue",
                    settlement_receipt=(
                        view.causal_settlement.authority_receipt_sha256
                    ),
                    current_partition_receipts=(
                        current_partition_receipts
                    ),
                    current_thing_ids=current_thing_ids,
                    cue_senses=(),
                    evocation=None,
                    candidates=(),
                    program_custody=None,
                )
            sensory_evocations = tuple(
                (
                    sense,
                    self._reciprocal.evoke(
                        view.causal_settlement,
                        cue_senses=(sense,),
                    ),
                )
                for sense in available_cue_senses
            )
            for _sense, sensory_evocation in sensory_evocations:
                self._reciprocal.verify_evocation(
                    sensory_evocation
                )
            exact_evocations = tuple(
                (sense, sensory_evocation)
                for sense, sensory_evocation in sensory_evocations
                if (
                    sensory_evocation.state == "unique"
                    and sensory_evocation.candidate is not None
                )
            )
            resolved_thing_ids = tuple(sorted({
                sensory_evocation.candidate.thing_id
                for _sense, sensory_evocation in exact_evocations
                if sensory_evocation.candidate is not None
            }))
            ambiguous = any(
                sensory_evocation.state == "ambiguous"
                for _sense, sensory_evocation in sensory_evocations
            )
            if (
                ambiguous
                or resolved_thing_ids != (current_thing_id,)
            ):
                representative = (
                    exact_evocations[0][1]
                    if exact_evocations
                    else sensory_evocations[0][1]
                )
                return self._selection(
                    state="silent",
                    reason=(
                        "cue_ambiguous"
                        if ambiguous or len(resolved_thing_ids) > 1
                        else "cue_unresolved"
                    ),
                    settlement_receipt=(
                        view.causal_settlement.authority_receipt_sha256
                    ),
                    current_partition_receipts=(
                        current_partition_receipts
                    ),
                    current_thing_ids=current_thing_ids,
                    cue_senses=representative.cue_senses,
                    evocation=representative,
                    candidates=(),
                    program_custody=None,
                )
            cue_senses, evocation = exact_evocations[0]
            cue_senses = (cue_senses,)
            candidate_class = evocation.candidate
            relations = tuple(
                relation
                for relation in self._relations
                if (
                    relation.thing_id == candidate_class.thing_id
                    and relation.consequence_partition_receipt_sha256
                    in candidate_class.partition_receipt_sha256s
                )
            )
            if len(relations) != 1:
                return self._selection(
                    state="silent",
                    reason=(
                        "no_live_vocal_relation"
                        if not relations
                        else "multiple_live_vocal_relations"
                    ),
                    settlement_receipt=(
                        view.causal_settlement.authority_receipt_sha256
                    ),
                    current_partition_receipts=(
                        current_partition_receipts
                    ),
                    current_thing_ids=current_thing_ids,
                    cue_senses=cue_senses,
                    evocation=evocation,
                    candidates=relations,
                    program_custody=None,
                )
            relation = relations[0]
            custody = self._program_custody(
                relation=relation,
                program=self._program(relation),
                custody_receipt=(
                    view.parent_custody_receipt_sha256
                ),
                capability_receipt=(
                    current_custody_capability
                    .authority_receipt_sha256
                ),
                settlement_receipt=(
                    view.causal_settlement.authority_receipt_sha256
                ),
                evocation=evocation,
                current_custody_authority=current_custody_authority,
                current_custody_capability=current_custody_capability,
            )
            self.verify_program_custody(custody)
            return self._selection(
                state="ready",
                reason="one_physical_vocal_relation",
                settlement_receipt=(
                    view.causal_settlement.authority_receipt_sha256
                ),
                current_partition_receipts=(
                    current_partition_receipts
                ),
                current_thing_ids=current_thing_ids,
                cue_senses=cue_senses,
                evocation=evocation,
                candidates=relations,
                program_custody=custody,
            )

    @staticmethod
    def _closure_from_record(
        raw: object,
    ) -> BodyOwnedFragmentInquiryClosure:
        if not isinstance(raw, Mapping):
            raise ValueError("vocal causal inquiry closure changed")
        fields = set(BodyOwnedFragmentInquiryClosure.__dataclass_fields__)
        if set(raw) != fields | {"schema"}:
            raise ValueError("vocal causal inquiry closure fields changed")
        return BodyOwnedFragmentInquiryClosure(
            need_receipt_sha256=raw["need_receipt_sha256"],
            witness_receipt_sha256=raw["witness_receipt_sha256"],
            fragment_receipt_sha256=raw["fragment_receipt_sha256"],
            pending_custody_receipt_sha256=(
                raw["pending_custody_receipt_sha256"]
            ),
            consequence_settlement_receipt_sha256=(
                raw["consequence_settlement_receipt_sha256"]
            ),
            program_authority_receipt_sha256=(
                raw["program_authority_receipt_sha256"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw[
                "authority_receipt_sha256"
            ],
        )

    @staticmethod
    def _root_from_record(raw: object) -> VocalCausalRootCommitment:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "full_evidence_sha256",
                "physical_value_sha256",
                "schema",
                "sense",
                "topology_index",
            }
            or raw.get("schema") != ROOT_COMMITMENT_SCHEMA
        ):
            raise ValueError("vocal causal root commitment changed")
        return VocalCausalRootCommitment(
            sense=raw["sense"],
            topology_index=raw["topology_index"],
            physical_value_sha256=raw["physical_value_sha256"],
            full_evidence_sha256=raw["full_evidence_sha256"],
        )

    def _relation_from_record(
        self,
        raw: object,
    ) -> ExperienceGrownVocalCausalRelation:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != set(ExperienceGrownVocalCausalRelation.__dataclass_fields__)
            | {"schema"}
            or raw.get("schema") != RELATION_SCHEMA
        ):
            raise ValueError("vocal causal relation record changed")
        boundaries = raw["consequence_boundary_receipts"]
        anchor_roots = raw["thing_anchor_root_commitments"]
        if (
            not isinstance(boundaries, list)
            or not isinstance(anchor_roots, list)
        ):
            raise ValueError("vocal causal relation evidence changed")
        relation = ExperienceGrownVocalCausalRelation(
            relation_id=raw["relation_id"],
            fragment_receipt_sha256=raw[
                "fragment_receipt_sha256"
            ],
            need_receipt_sha256=raw["need_receipt_sha256"],
            witness_receipt_sha256=raw["witness_receipt_sha256"],
            pending_custody_receipt_sha256=raw[
                "pending_custody_receipt_sha256"
            ],
            inquiry_closure=self._closure_from_record(
                raw["inquiry_closure"]
            ),
            consequence_settlement_receipt_sha256=raw[
                "consequence_settlement_receipt_sha256"
            ],
            consequence_partition_receipt_sha256=raw[
                "consequence_partition_receipt_sha256"
            ],
            consequence_boundary_receipts=tuple(
                (item[0], item[1]) for item in boundaries
            ),
            thing_anchor_root_commitments=tuple(
                self._root_from_record(item) for item in anchor_roots
            ),
            thing_id=raw["thing_id"],
            program_id=raw["program_id"],
            program_authority_receipt_sha256=raw[
                "program_authority_receipt_sha256"
            ],
            command_graph_sha256=raw["command_graph_sha256"],
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw[
                "authority_receipt_sha256"
            ],
        )
        self._verify_relation(relation)
        return relation

    def restore_encoded(self, encoded: bytes) -> None:
        if not isinstance(encoded, bytes):
            raise TypeError("vocal causal relation state is not bytes")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "vocal causal relation state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {
                "body",
                "schema",
                "state_hmac_sha256",
            }
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError("vocal causal relation envelope changed")
        body = envelope["body"]
        if (
            set(body) != {"max_relations", "relations", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("max_relations") != self._max_relations
            or not isinstance(body.get("relations"), list)
        ):
            raise ValueError("vocal causal relation state changed")
        expected = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected,
            envelope.get("state_hmac_sha256", ""),
        ):
            raise ValueError("vocal causal relation state HMAC changed")
        relations = tuple(
            self._relation_from_record(raw)
            for raw in body["relations"]
        )
        if self._encoded(relations) != encoded:
            raise ValueError(
                "vocal causal relation state is not canonical"
            )
        with self._lock:
            if self._prepared is not None or self._latest_undo is not None:
                raise RuntimeError(
                    "vocal causal relation cannot restore a transaction"
                )
            self._relations = relations

    def select_evoked_program(
        self,
        evocation: CausalThingReciprocalEvocation,
    ) -> ExperienceGrownVocalEvokedProgramCustody | None:
        """Select one retained relation from this owner's verified THING cue."""

        self._reciprocal.verify_evocation(evocation)
        if evocation.state != "unique" or evocation.candidate is None:
            return None
        with self._lock:
            self._encoded(self._relations)
            candidate = evocation.candidate
            relations = tuple(
                relation
                for relation in self._relations
                if (
                    relation.thing_id == candidate.thing_id
                    and relation.consequence_partition_receipt_sha256
                    in candidate.partition_receipt_sha256s
                )
            )
            if len(relations) != 1:
                return None
            relation = relations[0]
            self._verify_relation(relation)
            program = self._program(relation)
            fragment = self._fragment(
                relation.fragment_receipt_sha256
            )
            provisional = ExperienceGrownVocalEvokedProgramCustody(
                relation_receipt_sha256=(
                    relation.authority_receipt_sha256
                ),
                evocation_receipt_sha256=(
                    evocation.authority_receipt_sha256
                ),
                thing_class_receipt_sha256=(
                    candidate.authority_receipt_sha256
                ),
                program=program,
                fragment_pressure_sha256=fragment.pressure_sha256,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
                _evocation=evocation,
                _owner_authority=(
                    self._evoked_program_owner_authority
                ),
                _construction_authority=_EVOKED_PROGRAM_AUTHORITY,
            )
            signature = hmac.new(
                self._evoked_program_key,
                _EVOKED_PROGRAM_DOMAIN
                + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            custody = ExperienceGrownVocalEvokedProgramCustody(
                relation_receipt_sha256=(
                    provisional.relation_receipt_sha256
                ),
                evocation_receipt_sha256=(
                    provisional.evocation_receipt_sha256
                ),
                thing_class_receipt_sha256=(
                    provisional.thing_class_receipt_sha256
                ),
                program=program,
                fragment_pressure_sha256=(
                    provisional.fragment_pressure_sha256
                ),
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
                _evocation=evocation,
                _owner_authority=(
                    self._evoked_program_owner_authority
                ),
                _construction_authority=_EVOKED_PROGRAM_AUTHORITY,
            )
            self.verify_evoked_program_custody(custody)
            return custody

    def verify_evoked_program_custody(
        self,
        custody: ExperienceGrownVocalEvokedProgramCustody,
    ) -> None:
        """Verify cue custody against current reciprocal, relation, and motor."""

        if (
            not isinstance(
                custody,
                ExperienceGrownVocalEvokedProgramCustody,
            )
            or custody._construction_authority
            is not _EVOKED_PROGRAM_AUTHORITY
            or custody._owner_authority
            is not self._evoked_program_owner_authority
        ):
            raise ValueError(
                "evoked vocal program custody changed ownership"
            )
        self._reciprocal.verify_evocation(custody._evocation)
        candidate = custody._evocation.candidate
        if (
            custody._evocation.state != "unique"
            or candidate is None
            or custody.evocation_receipt_sha256
            != custody._evocation.authority_receipt_sha256
            or custody.thing_class_receipt_sha256
            != candidate.authority_receipt_sha256
        ):
            raise ValueError(
                "evoked vocal program custody changed its THING cue"
            )
        with self._lock:
            self._encoded(self._relations)
            relations = tuple(
                relation
                for relation in self._relations
                if relation.authority_receipt_sha256
                == custody.relation_receipt_sha256
            )
            if len(relations) != 1:
                raise ValueError(
                    "evoked vocal program lost retained relation"
                )
            relation = relations[0]
            self._verify_relation(relation)
            program = self._program(relation)
            fragment = self._fragment(
                relation.fragment_receipt_sha256
            )
            if (
                relation.thing_id != candidate.thing_id
                or relation.consequence_partition_receipt_sha256
                not in candidate.partition_receipt_sha256s
                or program != custody.program
                or fragment.pressure_sha256
                != custody.fragment_pressure_sha256
            ):
                raise ValueError(
                    "evoked vocal program custody changed its relation"
                )
        expected = hmac.new(
            self._evoked_program_key,
            _EVOKED_PROGRAM_DOMAIN + _canonical(custody.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                custody.authority_hmac_sha256,
            )
            or custody.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": custody.payload(),
            })
        ):
            raise ValueError(
                "evoked vocal program custody authority changed"
            )

    def verified_evoked_program(
        self,
        custody: ExperienceGrownVocalEvokedProgramCustody,
    ) -> tuple[ArticulatoryProgram, ExperienceGrownVocalMotorFragment]:
        """Open one verified program and its retained pressure witness."""

        self.verify_evoked_program_custody(custody)
        relation = next(
            relation
            for relation in self._relations
            if relation.authority_receipt_sha256
            == custody.relation_receipt_sha256
        )
        return (
            self._program(relation),
            self._fragment(relation.fragment_receipt_sha256),
        )

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = (
                self._encoded(self._relations)
                if self._prepared is None
                else self._encoded(self._prepared._prior_relations)
            )
            return {
                "label_authority": False,
                "meaning_authority": False,
                "max_relations": self._max_relations,
                "motor_derived_from_witness_field": True,
                "relation_count": len(self._relations),
                "retained_pcm_bytes": 0,
                "root_commitments_are_decision_authority": False,
                "schema": (
                    "guala.experience_grown_vocal_causal_relation."
                    "status.v1"
                ),
                "signal_matching": False,
                "state_bytes": len(encoded),
                "witness_full_dsf_field_preserved_upstream": True,
                "authoritative_full_field_owner": (
                    "causal_thing_mosaic"
                ),
                "word_authority": False,
            }


__all__ = (
    "ENVELOPE_SCHEMA",
    "EVOKED_PROGRAM_CUSTODY_SCHEMA",
    "ExperienceGrownVocalCausalRelation",
    "ExperienceGrownVocalCausalRelationCapacityError",
    "ExperienceGrownVocalCausalRelationOwner",
    "ExperienceGrownVocalCausalRelationUndo",
    "ExperienceGrownVocalCausalSelection",
    "ExperienceGrownVocalEvokedProgramCustody",
    "ExperienceGrownVocalProgramCustody",
    "PreparedExperienceGrownVocalCausalRelation",
    "PROGRAM_CUSTODY_SCHEMA",
    "RELATION_SCHEMA",
    "ROOT_COMMITMENT_SCHEMA",
    "SELECTION_SCHEMA",
    "STATE_SCHEMA",
    "VOCAL_CAUSAL_RELATION_SELECTION_CONSUMER_ID",
    "VocalCausalRootCommitment",
)
