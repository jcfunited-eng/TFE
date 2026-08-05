"""Passive multisensory learning beside an already-custodied causal THING.

This owner admits one authenticated passive settled occurrence without
inventing an action execution.  The existing THING owner remains the only
identity authority.  A passive occurrence can attach only when the current
physical-contact continuity resolves to exactly one retained THING mosaic.

Every canonical sensory lane remains explicit and every observed lane retains
its complete L0--L4 root.  At least two observed senses are required, but no
named lane is mandatory.  No sensory value, label, hash, score, similarity,
Chi, Atlas identity, raw-media payload, or ML operation can select a THING.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    FullFieldSensoryRoot,
    ThingEncounterPartition,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    PhysicalSurfaceContinuityWitness,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)
from dsf_ai_service.substrate.native_evidence_custody import (
    NativeEvidenceTransitionIndex,
)
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    NeuronMosaicAssembly,
    WholeOrganismNeuronPopulationOwner,
)


PROFILE_SCHEMA = "guala.passive_thing_learning.profile.v1"
SENSE_SCHEMA = "guala.passive_thing_learning.sense.v1"
STORY_SCHEMA = "guala.passive_thing_learning.story.v1"
RECORD_SCHEMA = "guala.passive_thing_learning.record.v2"
STATE_SCHEMA = "guala.passive_thing_learning.state.v2"
ENVELOPE_SCHEMA = "guala.passive_thing_learning.state_hmac.v1"
_LEGACY_STATE_SCHEMA = "guala.passive_thing_learning.state.v1"
PASSIVE_THING_LEARNING_CONSUMER_ID = "passive-thing-learning"
PASSIVE_RELATION_GAP_CAPABILITY_SCHEMA = (
    "guala.passive_thing_learning.relation_gap_capability.v1"
)

_RECORD_DOMAIN = b"guala-passive-thing-learning-record-v2\0"
_RELATION_GAP_DOMAIN = b"guala-passive-relation-gap-capability-v1\0"
_STATE_DOMAIN = b"guala-passive-thing-learning-state-v2\0"
_LEGACY_STATE_DOMAIN = b"guala-passive-thing-learning-state-v1\0"
_HEX = frozenset("0123456789abcdef")
_SENSES = tuple(value.value for value in SENSE_ORDER)
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
_RELATION_GAP_AUTHORITY = object()


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


def _key(value: bytes | str, label: str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(f"{label} authority key changed")
    return hashlib.sha256(label.encode("utf-8") + b"\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("passive story time must be an exact Fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class PassiveThingLearningProfile:
    profile_id: str
    max_records: int
    max_roots_per_record: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_records: int,
        max_roots_per_record: int,
        max_state_bytes: int,
    ) -> "PassiveThingLearningProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "passive profile id"),
            max_records=_positive(max_records, "passive record capacity"),
            max_roots_per_record=_positive(
                max_roots_per_record,
                "passive root capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "passive state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_records=provisional.max_records,
            max_roots_per_record=provisional.max_roots_per_record,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_records": self.max_records,
            "max_roots_per_record": self.max_roots_per_record,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "passive profile id")
        _positive(self.max_records, "passive record capacity")
        _positive(self.max_roots_per_record, "passive root capacity")
        _positive(self.max_state_bytes, "passive state capacity")
        _sha(self.authority_receipt_sha256, "passive profile authority")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("passive profile authority changed")


@dataclass(frozen=True, slots=True)
class PassiveThingSenseState:
    sense: str
    state: str
    relation: str
    structural_fingerprint: str
    topology_receipt_sha256: str | None
    boundary_receipt_sha256: str
    root_route_keys: tuple[tuple[str, str], ...]

    def payload(self) -> dict[str, object]:
        return {
            "boundary_receipt_sha256": self.boundary_receipt_sha256,
            "relation": self.relation,
            "root_route_keys": [
                list(value) for value in self.root_route_keys
            ],
            "schema": SENSE_SCHEMA,
            "sense": self.sense,
            "state": self.state,
            "structural_fingerprint": self.structural_fingerprint,
            "topology_receipt_sha256": self.topology_receipt_sha256,
        }

    def verify(self) -> None:
        if self.sense not in _SENSES:
            raise ValueError("passive sensory lane changed")
        if self.state not in {"observed", "quiescent", "sensor_unavailable"}:
            raise ValueError("passive sensory lane remains unresolved")
        _identifier(self.relation, "passive sensory relation")
        _sha(
            self.structural_fingerprint,
            "passive sensory structural fingerprint",
        )
        if self.topology_receipt_sha256 is not None:
            _sha(self.topology_receipt_sha256, "passive sensory topology")
        _sha(self.boundary_receipt_sha256, "passive sensory boundary")
        if (
            self.root_route_keys
            != tuple(sorted(set(self.root_route_keys)))
            or any(
                not isinstance(value, tuple)
                or len(value) != 2
                or value[0] != self.sense
                or _sha(value[1], "passive sensory root") != value[1]
                for value in self.root_route_keys
            )
        ):
            raise ValueError("passive sensory root membership changed")
        if self.state == "observed" and not self.root_route_keys:
            raise ValueError("observed passive sense lacks full roots")
        if (
            self.state in {"quiescent", "sensor_unavailable"}
            and (
                self.root_route_keys
                or self.topology_receipt_sha256 is not None
            )
        ):
            raise ValueError("unavailable passive sense changed evidence")


@dataclass(frozen=True, slots=True)
class PassiveThingCausalStory:
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    custody_capability_receipt_sha256: str
    source_kind: str
    settlement_event_id: str
    settlement_authority_receipt_sha256: str
    settlement_structural_fingerprint: str
    source_time_start: Fraction
    source_time_end: Fraction
    world_observation_receipt_sha256: str
    world_revision: int
    entity_continuity_hmac_sha256: str
    target_partition_authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "custody_capability_receipt_sha256": (
                self.custody_capability_receipt_sha256
            ),
            "entity_continuity_hmac_sha256": (
                self.entity_continuity_hmac_sha256
            ),
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "schema": STORY_SCHEMA,
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "settlement_event_id": self.settlement_event_id,
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_kind": self.source_kind,
            "source_occurrence_id": self.source_occurrence_id,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "target_partition_authority_receipt_sha256": (
                self.target_partition_authority_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }

    def verify(self) -> None:
        for value, label in (
            (self.source_occurrence_id, "passive source occurrence"),
            (self.parent_custody_receipt_sha256, "passive parent custody"),
            (
                self.custody_capability_receipt_sha256,
                "passive custody capability",
            ),
            (self.settlement_event_id, "passive settlement event"),
            (
                self.settlement_authority_receipt_sha256,
                "passive settlement authority",
            ),
            (
                self.settlement_structural_fingerprint,
                "passive settlement structure",
            ),
            (
                self.world_observation_receipt_sha256,
                "passive world observation",
            ),
            (
                self.entity_continuity_hmac_sha256,
                "passive entity continuity",
            ),
            (
                self.target_partition_authority_receipt_sha256,
                "passive target partition",
            ),
        ):
            _sha(value, label)
        _identifier(self.source_kind, "passive source kind")
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or isinstance(self.world_revision, bool)
            or not isinstance(self.world_revision, int)
            or self.world_revision < 0
        ):
            raise ValueError("passive causal story extent changed")


@dataclass(frozen=True, slots=True)
class _VerifiedPassiveThingLearningRecordIntegrity:
    owner_authority: object
    thing_id: str
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    six_lane_states: tuple[PassiveThingSenseState, ...]
    native_evidence_transition: NativeEvidenceTransitionIndex
    neuron_mosaic_assembly: NeuronMosaicAssembly
    story: PassiveThingCausalStory
    physical_surface_continuity: PhysicalSurfaceContinuityWitness | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def matches(
        self,
        record: "PassiveThingLearningRecord",
        owner_authority: object,
    ) -> bool:
        return (
            self.owner_authority is owner_authority
            and self.thing_id == record.thing_id
            and self.full_field_roots is record.full_field_roots
            and self.six_lane_states is record.six_lane_states
            and self.native_evidence_transition
            is record.native_evidence_transition
            and self.neuron_mosaic_assembly
            is record.neuron_mosaic_assembly
            and self.physical_surface_continuity
            is record.physical_surface_continuity
            and self.story is record.story
            and self.authority_hmac_sha256
            == record.authority_hmac_sha256
            and self.authority_receipt_sha256
            == record.authority_receipt_sha256
        )


@dataclass(frozen=True, slots=True)
class PassiveThingLearningRecord:
    thing_id: str
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    six_lane_states: tuple[PassiveThingSenseState, ...]
    native_evidence_transition: NativeEvidenceTransitionIndex
    neuron_mosaic_assembly: NeuronMosaicAssembly
    story: PassiveThingCausalStory
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    physical_surface_continuity: PhysicalSurfaceContinuityWitness | None = None
    _verified_integrity: (
        _VerifiedPassiveThingLearningRecordIntegrity | None
    ) = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    @property
    def observed_senses(self) -> tuple[str, ...]:
        return tuple(
            value.sense
            for value in self.six_lane_states
            if value.state == "observed"
        )

    def payload(self) -> dict[str, object]:
        payload = {
            "full_field_roots": [
                value.record() for value in self.full_field_roots
            ],
            "native_evidence_transition": (
                self.native_evidence_transition.record()
            ),
            "neuron_mosaic_assembly": (
                self.neuron_mosaic_assembly.record()
            ),
            "schema": RECORD_SCHEMA,
            "six_lane_states": [
                value.payload() for value in self.six_lane_states
            ],
            "story": self.story.payload(),
            "thing_id": self.thing_id,
        }

        if self.physical_surface_continuity is not None:
            payload["physical_surface_continuity"] = (
                self.physical_surface_continuity.record()
            )
        return payload
    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,

            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _PreparedState:
    phase: str


@dataclass(frozen=True, slots=True)
class PreparedPassiveThingLearning:
    record: PassiveThingLearningRecord
    _prior_records: tuple[
        tuple[str, PassiveThingLearningRecord],
        ...,
    ] = field(repr=False)
    _staged_records: tuple[
        tuple[str, PassiveThingLearningRecord],
        ...,
    ] = field(repr=False)
    _state: _PreparedState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PassiveThingLearningUndo:
    _prepared: PreparedPassiveThingLearning = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class PassiveThingLearningResolution:
    state: str
    reasons: tuple[str, ...]
    record: PassiveThingLearningRecord | None
    prepared: PreparedPassiveThingLearning | None


@dataclass(frozen=True, slots=True)
class PassiveRelationGapCapability:
    passive_record_receipt_sha256: str
    settlement_receipt_sha256: str
    thing_id: str
    whole_organism_episode_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _record: PassiveThingLearningRecord = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "passive_record_receipt_sha256": (
                self.passive_record_receipt_sha256
            ),
            "schema": PASSIVE_RELATION_GAP_CAPABILITY_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "thing_id": self.thing_id,
            "whole_organism_episode_receipt_sha256": (
                self.whole_organism_episode_receipt_sha256
            ),
        }


class PassiveWholeOrganismThingLearningOwner:
    """Own bounded passive multisensory additions to existing THINGs."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: PassiveThingLearningProfile,
        partition_authority: CustodiedW1ContactThingEncounterAuthority,
        thing_owner: CausalThingMosaicOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
    ) -> None:
        if not isinstance(profile, PassiveThingLearningProfile):
            raise TypeError("passive learning profile is not typed")
        profile.verify()
        if not isinstance(
            partition_authority,
            CustodiedW1ContactThingEncounterAuthority,
        ):
            raise TypeError("passive learning requires target authority")
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError("passive learning requires exact THING owner")
        if not isinstance(
            neuron_owner,
            WholeOrganismNeuronPopulationOwner,
        ):
            raise TypeError(
                "passive learning requires exact neuron owner"
            )
        if (
            getattr(thing_owner, "_partition_authority", None)
            is not partition_authority
        ):
            raise ValueError(
                "passive learning crossed THING partition authority"
            )
        root = _key(authority_key, "passive whole-organism THING learning")
        self._record_key = hashlib.sha256(
            _RECORD_DOMAIN + root
        ).digest()
        self._relation_gap_key = hashlib.sha256(
            _RELATION_GAP_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._legacy_state_key = hashlib.sha256(
            _LEGACY_STATE_DOMAIN + root
        ).digest()
        self._profile = profile
        self._partitions = partition_authority
        self._things = thing_owner
        self._neurons = neuron_owner
        self._records: dict[str, PassiveThingLearningRecord] = {}
        self._record_owner_authority = object()
        self._prepared_authority = object()
        self._relation_gap_owner_authority = object()
        self._lock = threading.RLock()

    @property
    def records(self) -> tuple[PassiveThingLearningRecord, ...]:
        with self._lock:
            return tuple(
                sorted(
                    self._records.values(),
                    key=lambda value: (
                        value.story.source_time_start,
                        value.story.source_time_end,
                        value.thing_id,
                        value.authority_receipt_sha256,
                    ),
                )
            )

    def rebind_neuron_owner(
        self,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
    ) -> None:
        """Rebind an equivalent cold-restored neuron authority atomically."""

        if not isinstance(
            neuron_owner,
            WholeOrganismNeuronPopulationOwner,
        ):
            raise TypeError("passive learning requires exact neuron owner")
        with self._lock:
            for record in self._records.values():
                neuron_owner.verify_mosaic_assembly(
                    record.neuron_mosaic_assembly,
                    expected_roots=record.full_field_roots,
                    expected_settlement_receipt_sha256=(
                        record.story.settlement_authority_receipt_sha256
                    ),
                )
            self._neurons = neuron_owner

    def issue_relation_gap_capability(
        self,
        *,
        record: PassiveThingLearningRecord,
        whole_organism_episode_receipt_sha256: str,
    ) -> PassiveRelationGapCapability:
        """Bind one unresolved relation to one retained whole episode."""

        self._verify_record(record)
        if self._records.get(
            record.authority_receipt_sha256
        ) != record:
            raise ValueError(
                "relation-gap capability requires retained passive record"
            )
        _sha(
            whole_organism_episode_receipt_sha256,
            "whole-organism episode",
        )
        provisional = PassiveRelationGapCapability(
            passive_record_receipt_sha256=(
                record.authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                record.story.settlement_authority_receipt_sha256
            ),
            thing_id=record.thing_id,
            whole_organism_episode_receipt_sha256=(
                whole_organism_episode_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _record=record,
            _owner_authority=self._relation_gap_owner_authority,
            _construction_authority=_RELATION_GAP_AUTHORITY,
        )
        signature = hmac.new(
            self._relation_gap_key,
            _RELATION_GAP_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = PassiveRelationGapCapability(
            passive_record_receipt_sha256=(
                provisional.passive_record_receipt_sha256
            ),
            settlement_receipt_sha256=(
                provisional.settlement_receipt_sha256
            ),
            thing_id=provisional.thing_id,
            whole_organism_episode_receipt_sha256=(
                provisional.whole_organism_episode_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            _record=record,
            _owner_authority=self._relation_gap_owner_authority,
            _construction_authority=_RELATION_GAP_AUTHORITY,
        )
        self.verify_relation_gap_capability(result)
        return result

    def verify_relation_gap_capability(
        self,
        capability: PassiveRelationGapCapability,
    ) -> None:
        if (
            not isinstance(capability, PassiveRelationGapCapability)
            or capability._construction_authority
            is not _RELATION_GAP_AUTHORITY
            or capability._owner_authority
            is not self._relation_gap_owner_authority
        ):
            raise ValueError(
                "passive relation-gap capability changed ownership"
            )
        self._verify_record(capability._record)
        if (
            self._records.get(
                capability.passive_record_receipt_sha256
            )
            != capability._record
            or capability.settlement_receipt_sha256
            != capability._record.story
            .settlement_authority_receipt_sha256
            or capability.thing_id != capability._record.thing_id
        ):
            raise ValueError(
                "passive relation-gap capability changed episode"
            )
        expected = hmac.new(
            self._relation_gap_key,
            _RELATION_GAP_DOMAIN + _canonical(capability.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                capability.authority_hmac_sha256,
            )
            or capability.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": capability.payload(),
            })
        ):
            raise ValueError(
                "passive relation-gap capability authority changed"
            )

    def owns_thing_owner(self, thing_owner: CausalThingMosaicOwner) -> bool:
        return thing_owner is self._things

    @staticmethod
    def _items(
        records: Mapping[str, PassiveThingLearningRecord],
    ) -> tuple[tuple[str, PassiveThingLearningRecord], ...]:
        return tuple((key, records[key]) for key in sorted(records))

    @staticmethod
    def _sense_states(
        settlement,
        roots: tuple[FullFieldSensoryRoot, ...],
    ) -> tuple[PassiveThingSenseState, ...]:
        interpretations = {
            value.sense: value for value in settlement.interpretations
        }
        if tuple(
            sense for sense in _SENSES if sense in interpretations
        ) != _SENSES:
            raise ValueError(
                "passive occurrence lacks six sensory boundaries"
            )
        values = []
        for sense in _SENSES:
            interpretation = interpretations[sense]
            value = PassiveThingSenseState(
                sense=sense,
                state=interpretation.state,
                relation=interpretation.relation,
                structural_fingerprint=(
                    interpretation.structural_fingerprint
                ),
                topology_receipt_sha256=(
                    interpretation.topology_receipt_sha256
                ),
                boundary_receipt_sha256=(
                    interpretation.boundary_receipt_sha256
                ),
                root_route_keys=tuple(sorted(
                    root.route_key
                    for root in roots
                    if root.sense == sense
                )),
            )
            value.verify()
            values.append(value)
        return tuple(values)

    def _target(self, continuity: str):
        matches = tuple(
            mosaic
            for mosaic in self._things.mosaics
            if any(
                partition.entity_continuity_hmac_sha256 == continuity
                for partition in mosaic.partitions
            )
        )
        if len(matches) != 1:
            raise ValueError(
                "passive custody does not resolve one retained THING"
            )
        mosaic = matches[0]
        target_partition = next(
            partition
            for partition in reversed(mosaic.partitions)
            if partition.entity_continuity_hmac_sha256 == continuity
        )
        return mosaic, target_partition

    def _seal(
        self,
        *,
        thing_id: str,
        roots: tuple[FullFieldSensoryRoot, ...],
        states: tuple[PassiveThingSenseState, ...],
        native_evidence_transition: NativeEvidenceTransitionIndex,
        neuron_mosaic_assembly: NeuronMosaicAssembly,
        story: PassiveThingCausalStory,
        physical_surface_continuity: PhysicalSurfaceContinuityWitness | None,
    ) -> PassiveThingLearningRecord:
        provisional = PassiveThingLearningRecord(
            thing_id=thing_id,
            full_field_roots=roots,
            six_lane_states=states,
            native_evidence_transition=native_evidence_transition,
            neuron_mosaic_assembly=neuron_mosaic_assembly,
            story=story,
            authority_hmac_sha256="0" * 64,
            physical_surface_continuity=physical_surface_continuity,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._record_key,
            _RECORD_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return PassiveThingLearningRecord(
            thing_id=provisional.thing_id,
            full_field_roots=provisional.full_field_roots,
            six_lane_states=provisional.six_lane_states,
            native_evidence_transition=(
                provisional.native_evidence_transition
            ),
            neuron_mosaic_assembly=(
                provisional.neuron_mosaic_assembly
            ),
            story=provisional.story,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            physical_surface_continuity=(
                provisional.physical_surface_continuity
            ),
        )

    def _verify_record(self, record: PassiveThingLearningRecord) -> None:
        if not isinstance(record, PassiveThingLearningRecord):
            raise TypeError("passive learning record is not typed")
        verified = record._verified_integrity
        if verified is not None and verified.matches(
            record,
            self._record_owner_authority,
        ):
            return
        _sha(record.thing_id, "passive learned THING")
        if (
            not record.full_field_roots
            or len(record.full_field_roots)
            > self._profile.max_roots_per_record
            or tuple(value.sense for value in record.six_lane_states)
            != _SENSES
        ):
            raise ValueError("passive learning record extent changed")
        for root in record.full_field_roots:
            root.verify()
        for value in record.six_lane_states:
            value.verify()
        if not isinstance(
            record.native_evidence_transition,
            NativeEvidenceTransitionIndex,
        ):
            raise TypeError(
                "passive learning native witness is not typed"
            )
        record.native_evidence_transition.verify()
        self._neurons.verify_mosaic_assembly(
            record.neuron_mosaic_assembly,
            expected_roots=record.full_field_roots,
            expected_settlement_receipt_sha256=(
                record.story.settlement_authority_receipt_sha256
            ),
        )
        expected_routes = tuple(sorted(
            root.route_key for root in record.full_field_roots
        ))
        retained_routes = tuple(sorted(
            route
            for state in record.six_lane_states
            for route in state.root_route_keys
        ))
        if (
            expected_routes != retained_routes
            or len(record.observed_senses) < 2
        ):
            raise ValueError(
                "passive learning lost symmetric sensory participation"
            )
        record.story.verify()
        if record.physical_surface_continuity is not None:
            witness = record.physical_surface_continuity
            self._partitions.verify_physical_surface_continuity_witness(
                witness
            )
            if (
                witness.settlement_receipt_sha256
                != record.story.settlement_authority_receipt_sha256
                or witness.settlement_structural_fingerprint
                != record.story.settlement_structural_fingerprint
                or witness.world_observation_receipt_sha256
                != record.story.world_observation_receipt_sha256
                or witness.world_revision != record.story.world_revision
                or witness.entity_continuity_hmac_sha256
                != record.story.entity_continuity_hmac_sha256
            ):
                raise ValueError(
                    "physical surface continuity left passive story"
                )
        _sha(record.authority_hmac_sha256, "passive record HMAC")
        _sha(record.authority_receipt_sha256, "passive record authority")
        expected_hmac = hmac.new(
            self._record_key,
            _RECORD_DOMAIN + _canonical(record.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                record.authority_hmac_sha256,
            )
            or record.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": record.payload(),
            })
        ):
            raise ValueError("passive learning record authority changed")
        object.__setattr__(
            record,
            "_verified_integrity",
            _VerifiedPassiveThingLearningRecordIntegrity(
                owner_authority=self._record_owner_authority,
                thing_id=record.thing_id,
                full_field_roots=record.full_field_roots,
                six_lane_states=record.six_lane_states,
                native_evidence_transition=(
                    record.native_evidence_transition
                ),
                neuron_mosaic_assembly=record.neuron_mosaic_assembly,
                story=record.story,
                authority_hmac_sha256=record.authority_hmac_sha256,
                physical_surface_continuity=record.physical_surface_continuity,
                authority_receipt_sha256=(
                    record.authority_receipt_sha256
                ),
            ),
        )

    def _verify_target(self, record: PassiveThingLearningRecord) -> None:
        mosaic, target = self._target(
            record.story.entity_continuity_hmac_sha256
        )
        if (
            mosaic.thing_id != record.thing_id
            or not any(
                partition.authority_receipt_sha256
                == record.story.target_partition_authority_receipt_sha256
                for partition in mosaic.partitions
            )
            or target.entity_continuity_hmac_sha256
            != record.story.entity_continuity_hmac_sha256
        ):
            raise ValueError("passive record left its exact THING owner")

    def prepare_admission(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
        physical_surface_continuity: PhysicalSurfaceContinuityWitness | None = None,
    ) -> PassiveThingLearningResolution:
        """Preflight one passive occurrence without mutation."""

        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ) or not isinstance(
            custody_capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "passive learning requires typed settled custody"
            )
        if (
            custody_capability.consumer_id
            != PASSIVE_THING_LEARNING_CONSUMER_ID
        ):
            raise ValueError(
                "passive learning requires its own custody capability"
            )
        with self._lock:
            try:
                view = custody_authority.open_child(custody_capability)
                if view.world_execution is not None:
                    raise ValueError(
                        "passive learning refuses represented execution"
                    )
                counter = view.occurrence_counter
                if (
                    counter.source_occurrence_id
                    != view.source_occurrence_id
                    or counter.custody_count != 1
                    or counter.source_transduction_lineage_count != 1
                    or counter.full_field_build_lineage_count != 1
                    or counter.causal_settlement_lineage_count != 1
                ):
                    raise ValueError(
                        "passive learning requires one settled occurrence"
                    )
                settlement = view.causal_settlement
                settlement.verify()
                roots = full_field_sensory_roots(settlement)
                if len(roots) > self._profile.max_roots_per_record:
                    raise RuntimeError(
                        "passive full-field root capacity exhausted"
                    )
                states = self._sense_states(settlement, roots)
                if sum(
                    value.state == "observed" for value in states
                ) < 2:
                    return PassiveThingLearningResolution(
                        state="unresolved",
                        reasons=("fewer_than_two_observed_senses",),
                        record=None,
                        prepared=None,
                    )
                if physical_surface_continuity is None:
                    continuity = (
                        self._partitions.entity_continuity_from_custody(
                            custody_authority=custody_authority,
                            capability=custody_capability,
                        )
                    )
                else:
                    self._partitions.verify_physical_surface_continuity_witness(
                        physical_surface_continuity
                    )
                    if (
                        physical_surface_continuity.settlement_receipt_sha256
                        != settlement.authority_receipt_sha256
                        or physical_surface_continuity.settlement_structural_fingerprint
                        != settlement.structural_fingerprint
                        or physical_surface_continuity.world_observation_receipt_sha256
                        != view.world_observation.authority_receipt_sha256
                        or physical_surface_continuity.world_revision
                        != view.world_observation.revision
                    ):
                        raise ValueError(
                            "physical surface continuity crossed passive occurrence"
                        )
                    continuity = (
                        physical_surface_continuity.entity_continuity_hmac_sha256
                    )
                mosaic, target_partition = self._target(continuity)
                if any(
                    value.story.source_occurrence_id
                    == view.source_occurrence_id
                    or value.story.parent_custody_receipt_sha256
                    == view.parent_custody_receipt_sha256
                    or value.story.custody_capability_receipt_sha256
                    == custody_capability.authority_receipt_sha256
                    for value in self._records.values()
                ):
                    return PassiveThingLearningResolution(
                        state="unresolved",
                        reasons=("passive_experience_already_learned",),
                        record=None,
                        prepared=None,
                    )
                story = PassiveThingCausalStory(
                    source_occurrence_id=view.source_occurrence_id,
                    parent_custody_receipt_sha256=(
                        view.parent_custody_receipt_sha256
                    ),
                    custody_capability_receipt_sha256=(
                        custody_capability.authority_receipt_sha256
                    ),
                    source_kind=view.source_kind.value,
                    settlement_event_id=settlement.event_id,
                    settlement_authority_receipt_sha256=(
                        settlement.authority_receipt_sha256
                    ),
                    settlement_structural_fingerprint=(
                        settlement.structural_fingerprint
                    ),
                    source_time_start=settlement.source_time_start,
                    source_time_end=settlement.source_time_end,
                    world_observation_receipt_sha256=(
                        view.world_observation.authority_receipt_sha256
                    ),
                    world_revision=view.world_observation.revision,
                    entity_continuity_hmac_sha256=continuity,
                    target_partition_authority_receipt_sha256=(
                        target_partition.authority_receipt_sha256
                    ),
                )
                story.verify()
                neuron_mosaic_assembly = (
                    self._neurons.issue_mosaic_assembly(settlement)
                )
                record = self._seal(
                    thing_id=mosaic.thing_id,
                    roots=roots,
                    states=states,
                    native_evidence_transition=(
                        settlement.native_evidence_witness
                        .transition_index()
                    ),
                    neuron_mosaic_assembly=neuron_mosaic_assembly,
                    story=story,
                    physical_surface_continuity=physical_surface_continuity,
                )
                self._verify_record(record)
                self._verify_target(record)
                if len(self._records) >= self._profile.max_records:
                    raise RuntimeError(
                        "passive learning record capacity exhausted"
                    )
                staged = dict(self._records)
                staged[record.authority_receipt_sha256] = record
                self._encoded(staged)
                prepared = PreparedPassiveThingLearning(
                    record=record,
                    _prior_records=self._items(self._records),
                    _staged_records=self._items(staged),
                    _state=_PreparedState("prepared"),
                    _owner_authority=self._prepared_authority,
                    _construction_authority=_PREPARED_AUTHORITY,
                )
                return PassiveThingLearningResolution(
                    state="prepared",
                    reasons=(),
                    record=record,
                    prepared=prepared,
                )
            except (PermissionError, ValueError, RuntimeError) as error:
                return PassiveThingLearningResolution(
                    state="unresolved",
                    reasons=(str(error),),
                    record=None,
                    prepared=None,
                )

    def _verify_prepared(
        self,
        prepared: PreparedPassiveThingLearning,
        *,
        require_current: bool,
    ) -> None:
        if (
            not isinstance(prepared, PreparedPassiveThingLearning)
            or prepared._construction_authority is not _PREPARED_AUTHORITY
            or prepared._owner_authority is not self._prepared_authority
            or prepared._state.phase != "prepared"
        ):
            raise ValueError("prepared passive learning changed custody")
        prior = dict(prepared._prior_records)
        staged = dict(prepared._staged_records)
        if (
            len(prior) != len(prepared._prior_records)
            or len(staged) != len(prepared._staged_records)
            or len(staged) != len(prior) + 1
            or staged.get(prepared.record.authority_receipt_sha256)
            != prepared.record
        ):
            raise ValueError("prepared passive learning changed state")
        self._verify_record(prepared.record)
        self._verify_target(prepared.record)
        self._encoded(prior)
        self._encoded(staged)
        if require_current and self._records != prior:
            raise RuntimeError("prepared passive learning is stale")

    def commit_prepared(
        self,
        prepared: PreparedPassiveThingLearning,
    ) -> PassiveThingLearningUndo:
        """Publish one preflighted passive occurrence exactly once."""

        with self._lock:
            self._verify_prepared(prepared, require_current=True)
            self._records = dict(prepared._staged_records)
            prepared._state.phase = "committed"
            return PassiveThingLearningUndo(
                _prepared=prepared,
                _owner_authority=self._prepared_authority,
                _construction_authority=_UNDO_AUTHORITY,
            )

    def discard_prepared(
        self,
        prepared: PreparedPassiveThingLearning,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared, require_current=False)
            prepared._state.phase = "discarded"

    def rollback_committed(
        self,
        undo: PassiveThingLearningUndo,
    ) -> None:
        """Restore exact prior bytes while the committed state is current."""

        if (
            not isinstance(undo, PassiveThingLearningUndo)
            or undo._construction_authority is not _UNDO_AUTHORITY
            or undo._owner_authority is not self._prepared_authority
        ):
            raise ValueError("passive learning undo changed custody")
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._owner_authority is not self._prepared_authority
                or prepared._state.phase != "committed"
            ):
                raise ValueError("passive learning undo changed custody")
            prior = dict(prepared._prior_records)
            staged = dict(prepared._staged_records)
            self._encoded(prior)
            self._encoded(staged)
            if self._records != staged:
                raise RuntimeError("passive learning undo is stale")
            self._records = prior
            prepared._state.phase = "rolled_back"

    def admit(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> PassiveThingLearningResolution:
        prepared = self.prepare_admission(
            custody_authority=custody_authority,
            custody_capability=custody_capability,
        )
        if prepared.state != "prepared":
            return prepared
        self.commit_prepared(prepared.prepared)
        return PassiveThingLearningResolution(
            state="learned",
            reasons=(),
            record=prepared.record,
            prepared=None,
        )

    def roots_for_thing(
        self,
        thing_id: str,
    ) -> tuple[FullFieldSensoryRoot, ...]:
        _sha(thing_id, "passive learned THING")
        with self._lock:
            roots: dict[
                tuple[str, str, int, str],
                FullFieldSensoryRoot,
            ] = {}
            for record in self._records.values():
                if record.thing_id != thing_id:
                    continue
                for root in record.full_field_roots:
                    roots[(
                        root.sense,
                        root.physical_value_sha256,
                        root.topology_index,
                        root.full_evidence_json,
                    )] = root
            return tuple(roots[key] for key in sorted(roots))

    def receipts_for_thing(self, thing_id: str) -> tuple[str, ...]:
        _sha(thing_id, "passive learned THING")
        with self._lock:
            return tuple(
                value.authority_receipt_sha256
                for value in sorted(
                    (
                        record for record in self._records.values()
                        if record.thing_id == thing_id
                    ),
                    key=lambda value: (
                        value.story.source_time_start,
                        value.story.source_time_end,
                        value.authority_receipt_sha256,
                    ),
                )
            )

    def _body(
        self,
        records: Mapping[str, PassiveThingLearningRecord],
    ) -> dict[str, object]:
        ordered = sorted(
            records.values(),
            key=lambda value: (
                value.story.source_time_start,
                value.story.source_time_end,
                value.thing_id,
                value.authority_receipt_sha256,
            ),
        )
        return {
            "profile": self._profile.record(),
            "records": [value.record() for value in ordered],
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        records: Mapping[str, PassiveThingLearningRecord],
    ) -> bytes:
        body = self._body(records)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("passive learning state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._records)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "full_field": True,
                "master_sense": None,
                "records": len(self._records),
                "reduced_approximation": False,
                "retained_roots": sum(
                    len(value.full_field_roots)
                    for value in self._records.values()
                ),
                "schema": "guala.passive_thing_learning.status.v1",
                "state_bytes": len(self._encoded(self._records)),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: PassiveThingLearningProfile,
        partition_authority: CustodiedW1ContactThingEncounterAuthority,
        thing_owner: CausalThingMosaicOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
        encoded: bytes,
    ) -> "PassiveWholeOrganismThingLearningOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("passive learning cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "passive learning cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {
                "body",
                "schema",
                "state_hmac_sha256",
            }
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("passive learning cold envelope changed")
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body) != {"profile", "records", "schema"}
            or body.get("schema")
            not in {STATE_SCHEMA, _LEGACY_STATE_SCHEMA}
            or body.get("profile") != profile.record()
            or not isinstance(body.get("records"), list)
        ):
            raise ValueError("passive learning cold payload changed")
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            partition_authority=partition_authority,
            thing_owner=thing_owner,
            neuron_owner=neuron_owner,
        )
        legacy_state = body["schema"] == _LEGACY_STATE_SCHEMA
        expected_hmac = hmac.new(
            (
                owner._legacy_state_key
                if legacy_state
                else owner._state_key
            ),
            (
                _LEGACY_STATE_DOMAIN
                if legacy_state
                else _STATE_DOMAIN
            )
            + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError("passive learning cold authority changed")
        if legacy_state:
            if body["records"]:
                raise ValueError(
                    "populated passive learning v1 state lacks exact "
                    "neuron mosaic custody and cannot be restored"
                )
            raise ValueError(
                "empty passive learning v1 state requires explicit "
                "schema migration"
            )
        for raw in body["records"]:
            record = owner._record_from_raw(raw)
            if record.authority_receipt_sha256 in owner._records:
                raise ValueError("passive learning cold record repeats")
            owner._verify_record(record)
            owner._verify_target(record)
            owner._records[record.authority_receipt_sha256] = record
        if owner.snapshot_encoded() != encoded:
            raise ValueError("passive learning cold round-trip changed")
        return owner

    @classmethod
    def migrate_authenticated_empty_v1_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: PassiveThingLearningProfile,
        partition_authority: CustodiedW1ContactThingEncounterAuthority,
        thing_owner: CausalThingMosaicOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
        encoded: bytes,
    ) -> bytes:
        """Translate only authenticated empty v1 custody into empty v2.

        No populated record is translated because v1 retained no neuron
        mosaic assembly from which a truthful v2 record could be restored.
        """

        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("passive learning v1 migration state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "passive learning v1 migration state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "passive learning v1 migration envelope changed"
            )
        body = envelope.get("body")
        if (
            not isinstance(body, dict)
            or set(body) != {"profile", "records", "schema"}
            or body.get("schema") != _LEGACY_STATE_SCHEMA
            or body.get("profile") != profile.record()
            or body.get("records") != []
        ):
            raise ValueError(
                "passive learning v1 migration is not empty exact custody"
            )
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            partition_authority=partition_authority,
            thing_owner=thing_owner,
            neuron_owner=neuron_owner,
        )
        expected_hmac = hmac.new(
            owner._legacy_state_key,
            _LEGACY_STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError(
                "passive learning v1 migration authority changed"
            )
        return owner.snapshot_encoded()

    def _record_from_raw(self, raw: object) -> PassiveThingLearningRecord:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "full_field_roots",
            "native_evidence_transition",
            "neuron_mosaic_assembly",
            "schema",
            "six_lane_states",
            "story",
            "thing_id",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) not in (
                expected,
                expected | {"physical_surface_continuity"},
            )
            or raw.get("schema") != RECORD_SCHEMA
            or not isinstance(raw.get("full_field_roots"), list)
            or not isinstance(raw.get("six_lane_states"), list)
        ):
            raise ValueError("passive learning cold record changed")
        physical_surface_continuity = None
        if "physical_surface_continuity" in raw:
            physical_surface_continuity = (
                PhysicalSurfaceContinuityWitness.from_record(
                    raw["physical_surface_continuity"]
                )
            )
            self._partitions.verify_physical_surface_continuity_witness(
                physical_surface_continuity
            )
        return PassiveThingLearningRecord(
            thing_id=raw["thing_id"],
            full_field_roots=tuple(
                self._root_from_raw(value)
                for value in raw["full_field_roots"]
            ),
            six_lane_states=tuple(
                self._sense_from_raw(value)
                for value in raw["six_lane_states"]
            ),
            native_evidence_transition=(
                NativeEvidenceTransitionIndex.from_record(
                    raw["native_evidence_transition"]
                )
            ),
            neuron_mosaic_assembly=(
                self._neurons.mosaic_assembly_from_record(
                    raw["neuron_mosaic_assembly"]
                )
            ),
            story=self._story_from_raw(raw["story"]),
            physical_surface_continuity=physical_surface_continuity,
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    @staticmethod
    def _root_from_raw(raw: object) -> FullFieldSensoryRoot:
        expected = {
            "full_evidence_json",
            "physical_value_sha256",
            "schema",
            "sense",
            "topology_index",
        }
        if not isinstance(raw, dict) or set(raw) != expected:
            raise ValueError("passive learning cold root changed")
        root = FullFieldSensoryRoot(
            sense=raw["sense"],
            topology_index=raw["topology_index"],
            physical_value_sha256=raw["physical_value_sha256"],
            full_evidence_json=raw["full_evidence_json"],
        )
        root.verify()
        return root

    @staticmethod
    def _sense_from_raw(raw: object) -> PassiveThingSenseState:
        expected = {
            "boundary_receipt_sha256",
            "relation",
            "root_route_keys",
            "schema",
            "sense",
            "state",
            "structural_fingerprint",
            "topology_receipt_sha256",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != SENSE_SCHEMA
            or not isinstance(raw.get("root_route_keys"), list)
            or any(
                not isinstance(value, list) or len(value) != 2
                for value in raw["root_route_keys"]
            )
        ):
            raise ValueError("passive learning cold sense changed")
        return PassiveThingSenseState(
            sense=raw["sense"],
            state=raw["state"],
            relation=raw["relation"],
            structural_fingerprint=raw["structural_fingerprint"],
            topology_receipt_sha256=raw["topology_receipt_sha256"],
            boundary_receipt_sha256=raw["boundary_receipt_sha256"],
            root_route_keys=tuple(
                (value[0], value[1])
                for value in raw["root_route_keys"]
            ),
        )

    @staticmethod
    def _story_from_raw(raw: object) -> PassiveThingCausalStory:
        expected = {
            "custody_capability_receipt_sha256",
            "entity_continuity_hmac_sha256",
            "parent_custody_receipt_sha256",
            "schema",
            "settlement_authority_receipt_sha256",
            "settlement_event_id",
            "settlement_structural_fingerprint",
            "source_kind",
            "source_occurrence_id",
            "source_time_end",
            "source_time_start",
            "target_partition_authority_receipt_sha256",
            "world_observation_receipt_sha256",
            "world_revision",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != STORY_SCHEMA
        ):
            raise ValueError("passive learning cold story changed")
        return PassiveThingCausalStory(
            source_occurrence_id=raw["source_occurrence_id"],
            parent_custody_receipt_sha256=(
                raw["parent_custody_receipt_sha256"]
            ),
            custody_capability_receipt_sha256=(
                raw["custody_capability_receipt_sha256"]
            ),
            source_kind=raw["source_kind"],
            settlement_event_id=raw["settlement_event_id"],
            settlement_authority_receipt_sha256=(
                raw["settlement_authority_receipt_sha256"]
            ),
            settlement_structural_fingerprint=(
                raw["settlement_structural_fingerprint"]
            ),
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold passive story start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold passive story end",
            ),
            world_observation_receipt_sha256=(
                raw["world_observation_receipt_sha256"]
            ),
            world_revision=raw["world_revision"],
            entity_continuity_hmac_sha256=(
                raw["entity_continuity_hmac_sha256"]
            ),
            target_partition_authority_receipt_sha256=(
                raw["target_partition_authority_receipt_sha256"]
            ),
        )


__all__ = (
    "PASSIVE_RELATION_GAP_CAPABILITY_SCHEMA",
    "PASSIVE_THING_LEARNING_CONSUMER_ID",
    "PassiveThingCausalStory",
    "PassiveThingLearningProfile",
    "PassiveRelationGapCapability",
    "PassiveThingLearningRecord",
    "PassiveThingLearningResolution",
    "PassiveThingLearningUndo",
    "PassiveThingSenseState",
    "PassiveWholeOrganismThingLearningOwner",
    "PreparedPassiveThingLearning",
)
