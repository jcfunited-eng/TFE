"""Bounded whole-organism admission into causal THING mosaics.

Learning occurs only from one provider-authenticated, L6-settled consequence
that is also held through one typed settled-experience custody.  All six
canonical sensory lanes must be explicit.  Any two or more independently
mounted observed senses may participate; no named sense is mandatory and no
sense supplies THING identity.  The causal target partition authority alone
supplies physical continuity.

The complete explicit L0--L4 roots, every sensory boundary state, and the
causal episode receipts are retained.  Hashes authenticate custody and state;
they are never treated as meaning.  There are no labels, similarities,
scores, thresholds, ML paths, Chi identities, Atlas identities, or sensory
priority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaic,
    CausalThingMosaicOwner,
    FullFieldSensoryRoot,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.native_evidence_custody import (
    NativeEvidenceTransitionIndex,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    ContributionState,
    DownstreamAuthority,
    L6Disposition,
    MechanismKind,
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodeCapability,
    WholeOrganismEpisodePhase,
    WholeOrganismEpisodeRecord,
)
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    NeuronMosaicAssembly,
    WholeOrganismNeuronPopulationOwner,
)


PROFILE_SCHEMA = "guala.whole_organism_thing_mosaic_learning.profile.v1"
SENSE_STATE_SCHEMA = (
    "guala.whole_organism_thing_mosaic_learning.sense_state.v1"
)
STORY_SCHEMA = "guala.whole_organism_thing_mosaic_learning.story.v1"
RECORD_SCHEMA = "guala.whole_organism_thing_mosaic_learning.record.v3"
STATE_SCHEMA = "guala.whole_organism_thing_mosaic_learning.state.v2"
ENVELOPE_SCHEMA = (
    "guala.whole_organism_thing_mosaic_learning.state_hmac.v2"
)
LEGACY_STATE_SCHEMA = "guala.whole_organism_thing_mosaic_learning.state.v1"
LEGACY_ENVELOPE_SCHEMA = (
    "guala.whole_organism_thing_mosaic_learning.state_hmac.v1"
)

_RECORD_DOMAIN = b"guala-whole-organism-thing-mosaic-learning-record-v2\0"
_STATE_DOMAIN = b"guala-whole-organism-thing-mosaic-learning-state-v2\0"
_LEGACY_STATE_DOMAIN = (
    b"guala-whole-organism-thing-mosaic-learning-state-v1\0"
)
_HEX = frozenset("0123456789abcdef")
_SENSES = tuple(value.value for value in SENSE_ORDER)


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
        raise TypeError("causal story time must be an exact Fraction")
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
class WholeOrganismThingMosaicLearningProfile:
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
    ) -> "WholeOrganismThingMosaicLearningProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "learning profile id"),
            max_records=_positive(max_records, "learning record capacity"),
            max_roots_per_record=_positive(
                max_roots_per_record,
                "learning root capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "learning state capacity",
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
        _identifier(self.profile_id, "learning profile id")
        _positive(self.max_records, "learning record capacity")
        _positive(self.max_roots_per_record, "learning root capacity")
        _positive(self.max_state_bytes, "learning state capacity")
        _sha(self.authority_receipt_sha256, "learning profile authority")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("learning profile authority changed")


@dataclass(frozen=True, slots=True)
class WholeOrganismSenseSettlement:
    sense: str
    boundary_state: str
    relation: str
    structural_fingerprint: str
    topology_receipt_sha256: str | None
    boundary_receipt_sha256: str
    mechanism_id: str
    contribution_state: ContributionState
    contribution_authority_receipt_sha256: str
    root_route_keys: tuple[tuple[str, str], ...]

    def payload(self) -> dict[str, object]:
        return {
            "boundary_receipt_sha256": self.boundary_receipt_sha256,
            "boundary_state": self.boundary_state,
            "contribution_authority_receipt_sha256": (
                self.contribution_authority_receipt_sha256
            ),
            "contribution_state": self.contribution_state.value,
            "mechanism_id": self.mechanism_id,
            "relation": self.relation,
            "root_route_keys": [
                list(value) for value in self.root_route_keys
            ],
            "schema": SENSE_STATE_SCHEMA,
            "sense": self.sense,
            "structural_fingerprint": self.structural_fingerprint,
            "topology_receipt_sha256": self.topology_receipt_sha256,
        }

    def verify(self) -> None:
        if self.sense not in _SENSES:
            raise ValueError("learning sense changed")
        if self.boundary_state not in {
            "observed",
            "sensor_unavailable",
        }:
            raise ValueError("learning retained an unresolved sensory lane")
        _identifier(self.relation, "learning sensory relation")
        _identifier(self.mechanism_id, "learning sensory mechanism")
        _sha(
            self.structural_fingerprint,
            "learning sensory structural fingerprint",
        )
        if self.topology_receipt_sha256 is not None:
            _sha(
                self.topology_receipt_sha256,
                "learning sensory topology",
            )
        _sha(self.boundary_receipt_sha256, "learning sensory boundary")
        _sha(
            self.contribution_authority_receipt_sha256,
            "learning sensory contribution",
        )
        if not isinstance(self.contribution_state, ContributionState):
            raise TypeError("learning sensory contribution state is not typed")
        if (
            self.root_route_keys
            != tuple(sorted(set(self.root_route_keys)))
            or any(
                not isinstance(value, tuple)
                or len(value) != 2
                or value[0] != self.sense
                or _sha(value[1], "learning sensory root") != value[1]
                for value in self.root_route_keys
            )
        ):
            raise ValueError("learning sensory root membership changed")
        if (
            self.boundary_state == "observed"
            and (
                self.contribution_state is not ContributionState.PERTURBED
                or not self.root_route_keys
            )
        ):
            raise ValueError("observed learning sense lacks full roots")
        if (
            self.boundary_state == "sensor_unavailable"
            and (
                self.contribution_state is not ContributionState.UNAVAILABLE
                or self.root_route_keys
                or self.topology_receipt_sha256 is not None
            )
        ):
            raise ValueError("unavailable learning sense changed evidence")


@dataclass(frozen=True, slots=True)
class WholeOrganismCausalStory:
    episode_id: str
    chain_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    manifest_receipt_sha256: str
    episode_authority_receipt_sha256: str
    settlement_event_id: str
    settlement_authority_receipt_sha256: str
    settlement_structural_fingerprint: str
    action_authority_receipt_sha256: str
    prior_episode_receipt_sha256: str
    action_execution_receipt_sha256: str
    l6_authority_receipt_sha256: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    thing_custody_capability_receipt_sha256: str
    world_observation_receipt_sha256: str
    entity_continuity_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_authority_receipt_sha256": (
                self.action_authority_receipt_sha256
            ),
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256
            ),
            "chain_id": self.chain_id,
            "entity_continuity_hmac_sha256": (
                self.entity_continuity_hmac_sha256
            ),
            "episode_authority_receipt_sha256": (
                self.episode_authority_receipt_sha256
            ),
            "episode_id": self.episode_id,
            "l6_authority_receipt_sha256": (
                self.l6_authority_receipt_sha256
            ),
            "manifest_receipt_sha256": self.manifest_receipt_sha256,
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "prior_episode_receipt_sha256": (
                self.prior_episode_receipt_sha256
            ),
            "schema": STORY_SCHEMA,
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "settlement_event_id": self.settlement_event_id,
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "thing_custody_capability_receipt_sha256": (
                self.thing_custody_capability_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def verify(self) -> None:
        _sha(self.episode_id, "learning story episode")
        _identifier(self.chain_id, "learning story chain")
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
        ):
            raise ValueError("learning story interval changed")
        for value, label in (
            (self.manifest_receipt_sha256, "story manifest"),
            (self.episode_authority_receipt_sha256, "story episode"),
            (self.settlement_event_id, "story settlement event"),
            (
                self.settlement_authority_receipt_sha256,
                "story settlement authority",
            ),
            (
                self.settlement_structural_fingerprint,
                "story settlement structure",
            ),
            (self.action_authority_receipt_sha256, "story action"),
            (self.prior_episode_receipt_sha256, "story prior episode"),
            (self.action_execution_receipt_sha256, "story execution"),
            (self.l6_authority_receipt_sha256, "story L6"),
            (self.source_occurrence_id, "story source occurrence"),
            (self.parent_custody_receipt_sha256, "story parent custody"),
            (
                self.thing_custody_capability_receipt_sha256,
                "story THING custody capability",
            ),
            (
                self.world_observation_receipt_sha256,
                "story world observation",
            ),
            (
                self.entity_continuity_hmac_sha256,
                "story entity continuity",
            ),
        ):
            _sha(value, label)


@dataclass(frozen=True, slots=True)
class WholeOrganismThingMosaicLearningRecord:
    thing_id: str
    thing_version: int
    prior_learning_receipt_sha256: str | None
    partition: ThingEncounterPartition
    six_lane_settlement: tuple[WholeOrganismSenseSettlement, ...]
    native_evidence_transition: NativeEvidenceTransitionIndex
    neuron_mosaic_assembly: NeuronMosaicAssembly
    story: WholeOrganismCausalStory
    thing_mosaic_authority_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def full_field_roots(self) -> tuple[FullFieldSensoryRoot, ...]:
        return self.partition.full_field_roots

    @property
    def observed_senses(self) -> tuple[str, ...]:
        return tuple(
            value.sense
            for value in self.six_lane_settlement
            if value.boundary_state == "observed"
        )

    def payload(self) -> dict[str, object]:
        return {
            "partition": self.partition.record(),
            "prior_learning_receipt_sha256": (
                self.prior_learning_receipt_sha256
            ),
            "native_evidence_transition": (
                self.native_evidence_transition.record()
            ),
            "neuron_mosaic_assembly": (
                self.neuron_mosaic_assembly.record()
            ),
            "schema": RECORD_SCHEMA,
            "six_lane_settlement": [
                value.payload() for value in self.six_lane_settlement
            ],
            "story": self.story.payload(),
            "thing_id": self.thing_id,
            "thing_mosaic_authority_receipt_sha256": (
                self.thing_mosaic_authority_receipt_sha256
            ),
            "thing_version": self.thing_version,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismThingMosaicLearningResolution:
    state: str
    reasons: tuple[str, ...]
    record: WholeOrganismThingMosaicLearningRecord | None
    mosaic: CausalThingMosaic | None


class WholeOrganismThingMosaicLearningOwner:
    """Atomically joins settled whole-organism experience to one THING."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: WholeOrganismThingMosaicLearningProfile,
        episode_authority: WholeOrganismEpisodeAuthority,
        partition_authority: CustodiedW1ContactThingEncounterAuthority,
        thing_owner: CausalThingMosaicOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
    ) -> None:
        if not isinstance(
            profile,
            WholeOrganismThingMosaicLearningProfile,
        ):
            raise TypeError("whole-organism learning profile is not typed")
        profile.verify()
        if not isinstance(episode_authority, WholeOrganismEpisodeAuthority):
            raise TypeError("whole-organism learning requires episode authority")
        if not isinstance(
            partition_authority,
            CustodiedW1ContactThingEncounterAuthority,
        ):
            raise TypeError("whole-organism learning requires target authority")
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError("whole-organism learning requires THING owner")
        if not isinstance(
            neuron_owner,
            WholeOrganismNeuronPopulationOwner,
        ):
            raise TypeError(
                "whole-organism learning requires neuron-population owner"
            )
        if (
            getattr(thing_owner, "_partition_authority", None)
            is not partition_authority
        ):
            raise ValueError(
                "whole-organism learning crossed THING partition authority"
            )
        root = _key(authority_key, "whole-organism THING learning")
        self._record_key = hashlib.sha256(
            _RECORD_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._episodes = episode_authority
        self._partitions = partition_authority
        self._things = thing_owner
        self._neurons = neuron_owner
        self._records: dict[
            str,
            WholeOrganismThingMosaicLearningRecord,
        ] = {}
        self._lock = threading.RLock()

    @property
    def records(
        self,
    ) -> tuple[WholeOrganismThingMosaicLearningRecord, ...]:
        with self._lock:
            return tuple(
                sorted(
                    self._records.values(),
                    key=lambda value: (
                        value.story.source_time_start,
                        value.story.source_time_end,
                        value.thing_id,
                        value.thing_version,
                        value.authority_receipt_sha256,
                    ),
                )
            )

    def _six_lane_settlement(
        self,
        record: WholeOrganismEpisodeRecord,
        settlement: CausalExperienceSettlement,
    ) -> tuple[WholeOrganismSenseSettlement, ...]:
        manifest = self._episodes.manifest
        sensory_specs = tuple(
            value
            for value in manifest.mechanisms
            if value.kind is MechanismKind.RECEPTOR_FAMILY
        )
        by_sense: dict[str, tuple[object, object]] = {}
        contributions = {
            value.mechanism_id: value for value in record.contributions
        }
        for spec in sensory_specs:
            if spec.sense in by_sense:
                raise ValueError(
                    "whole-organism manifest repeats a sensory lane"
                )
            contribution = contributions.get(spec.mechanism_id)
            if contribution is None:
                raise ValueError(
                    "whole-organism sensory contribution is absent"
                )
            by_sense[spec.sense] = (spec, contribution)
        if tuple(sense for sense in _SENSES if sense in by_sense) != _SENSES:
            raise ValueError(
                "whole-organism consequence lacks six mounted sensory lanes"
            )

        interpretations = {
            value.sense: value
            for value in settlement.interpretations
        }
        roots_by_sense: dict[str, tuple[FullFieldSensoryRoot, ...]] = {
            sense: tuple(
                root for root in record.full_field_roots
                if root.sense == sense
            )
            for sense in _SENSES
        }
        values = []
        for sense in _SENSES:
            interpretation = interpretations.get(sense)
            if interpretation is None:
                raise ValueError(
                    "whole-organism consequence lost a sensory boundary"
                )
            spec, contribution = by_sense[sense]
            roots = roots_by_sense[sense]
            value = WholeOrganismSenseSettlement(
                sense=sense,
                boundary_state=interpretation.state,
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
                mechanism_id=spec.mechanism_id,
                contribution_state=contribution.state,
                contribution_authority_receipt_sha256=(
                    contribution.authority_receipt_sha256
                ),
                root_route_keys=tuple(
                    sorted(root.route_key for root in roots)
                ),
            )
            value.verify()
            values.append(value)
        return tuple(values)

    def _seal(
        self,
        *,
        thing_id: str,
        thing_version: int,
        prior_learning_receipt_sha256: str | None,
        partition: ThingEncounterPartition,
        six_lane_settlement: tuple[
            WholeOrganismSenseSettlement,
            ...,
        ],
        native_evidence_transition: NativeEvidenceTransitionIndex,
        neuron_mosaic_assembly: NeuronMosaicAssembly,
        story: WholeOrganismCausalStory,
        thing_mosaic_authority_receipt_sha256: str,
    ) -> WholeOrganismThingMosaicLearningRecord:
        provisional = WholeOrganismThingMosaicLearningRecord(
            thing_id=thing_id,
            thing_version=thing_version,
            prior_learning_receipt_sha256=(
                prior_learning_receipt_sha256
            ),
            partition=partition,
            six_lane_settlement=six_lane_settlement,
            native_evidence_transition=native_evidence_transition,
            neuron_mosaic_assembly=neuron_mosaic_assembly,
            story=story,
            thing_mosaic_authority_receipt_sha256=(
                thing_mosaic_authority_receipt_sha256
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._record_key,
            _RECORD_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismThingMosaicLearningRecord(
            thing_id=provisional.thing_id,
            thing_version=provisional.thing_version,
            prior_learning_receipt_sha256=(
                provisional.prior_learning_receipt_sha256
            ),
            partition=provisional.partition,
            six_lane_settlement=provisional.six_lane_settlement,
            native_evidence_transition=(
                provisional.native_evidence_transition
            ),
            neuron_mosaic_assembly=(
                provisional.neuron_mosaic_assembly
            ),
            story=provisional.story,
            thing_mosaic_authority_receipt_sha256=(
                provisional.thing_mosaic_authority_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _story(
        self,
        *,
        episode: WholeOrganismEpisodeRecord,
        partition: ThingEncounterPartition,
    ) -> WholeOrganismCausalStory:
        values = (
            episode.action_authority_receipt_sha256,
            episode.prior_episode_receipt_sha256,
            episode.action_execution_receipt_sha256,
            episode.l6_authority_receipt_sha256,
            partition.source_occurrence_id,
            partition.parent_custody_receipt_sha256,
            partition.thing_custody_capability_receipt_sha256,
        )
        if any(value is None for value in values):
            raise ValueError(
                "learning consequence lacks complete causal story custody"
            )
        story = WholeOrganismCausalStory(
            episode_id=episode.episode_id,
            chain_id=episode.chain_id,
            source_time_start=episode.source_time_start,
            source_time_end=episode.source_time_end,
            manifest_receipt_sha256=episode.manifest_receipt_sha256,
            episode_authority_receipt_sha256=(
                episode.authority_receipt_sha256
            ),
            settlement_event_id=episode.settlement_event_id,
            settlement_authority_receipt_sha256=(
                episode.settlement_authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                episode.settlement_structural_fingerprint
            ),
            action_authority_receipt_sha256=values[0],
            prior_episode_receipt_sha256=values[1],
            action_execution_receipt_sha256=values[2],
            l6_authority_receipt_sha256=values[3],
            source_occurrence_id=values[4],
            parent_custody_receipt_sha256=values[5],
            thing_custody_capability_receipt_sha256=values[6],
            world_observation_receipt_sha256=(
                partition.world_observation_receipt_sha256
            ),
            entity_continuity_hmac_sha256=(
                partition.entity_continuity_hmac_sha256
            ),
        )
        story.verify()
        return story

    def _verify_record(
        self,
        record: WholeOrganismThingMosaicLearningRecord,
    ) -> None:
        if not isinstance(
            record,
            WholeOrganismThingMosaicLearningRecord,
        ):
            raise TypeError("whole-organism learning record is not typed")
        _sha(record.thing_id, "learned THING identity")
        if (
            isinstance(record.thing_version, bool)
            or not isinstance(record.thing_version, int)
            or record.thing_version < 0
        ):
            raise ValueError("learned THING version changed")
        if record.prior_learning_receipt_sha256 is not None:
            _sha(
                record.prior_learning_receipt_sha256,
                "prior learning authority",
            )
        self._partitions.verify(record.partition)
        if (
            len(record.partition.full_field_roots)
            > self._profile.max_roots_per_record
            or tuple(value.sense for value in record.six_lane_settlement)
            != _SENSES
        ):
            raise ValueError("whole-organism learning extent changed")
        for value in record.six_lane_settlement:
            value.verify()
        if not isinstance(
            record.native_evidence_transition,
            NativeEvidenceTransitionIndex,
        ):
            raise TypeError(
                "whole-organism learning native witness is not typed"
            )
        record.native_evidence_transition.verify()
        self._neurons.verify_mosaic_assembly(
            record.neuron_mosaic_assembly,
            expected_roots=record.partition.full_field_roots,
            expected_settlement_receipt_sha256=(
                record.partition.settlement_receipt_sha256
            ),
        )
        if len(record.observed_senses) < 2:
            raise ValueError(
                "whole-organism learning lost multisensory participation"
            )
        record.story.verify()
        if (
            record.story.settlement_authority_receipt_sha256
            != record.partition.settlement_receipt_sha256
            or record.story.settlement_structural_fingerprint
            != record.partition.settlement_structural_fingerprint
            or record.story.action_execution_receipt_sha256
            != record.partition.execution_receipt_sha256
            or record.story.world_observation_receipt_sha256
            != record.partition.world_observation_receipt_sha256
            or record.story.entity_continuity_hmac_sha256
            != record.partition.entity_continuity_hmac_sha256
        ):
            raise ValueError("whole-organism learning crossed causal story")
        _sha(
            record.thing_mosaic_authority_receipt_sha256,
            "learned THING mosaic authority",
        )
        _sha(record.authority_hmac_sha256, "learning record HMAC")
        _sha(record.authority_receipt_sha256, "learning record authority")
        expected_hmac = hmac.new(
            self._record_key,
            _RECORD_DOMAIN + _canonical(record.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                record.authority_hmac_sha256,
                expected_hmac,
            )
            or record.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": record.payload(),
            })
        ):
            raise ValueError("whole-organism learning authority changed")

    def _verify_external_authorities(
        self,
        record: WholeOrganismThingMosaicLearningRecord,
    ) -> None:
        capability = self._episodes.capability_for(
            record.story.episode_authority_receipt_sha256
        )
        episode = self._episodes.require(
            capability,
            DownstreamAuthority.LEARNING,
        )
        if (
            episode.phase
            is not WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED
            or episode.l6_disposition is not L6Disposition.SETTLED
            or episode.authority_receipt_sha256
            != record.story.episode_authority_receipt_sha256
            or episode.settlement_authority_receipt_sha256
            != record.partition.settlement_receipt_sha256
            or episode.full_field_roots
            != record.partition.full_field_roots
            or episode.native_evidence_transition.authority_receipt_sha256
            != record.native_evidence_transition.authority_receipt_sha256
        ):
            raise ValueError(
                "learning record left its whole-organism consequence"
            )
        mosaics = {
            value.thing_id: value for value in self._things.mosaics
        }
        mosaic = mosaics.get(record.thing_id)
        if (
            mosaic is None
            or record.thing_version >= len(mosaic.partitions)
            or mosaic.partitions[record.thing_version] != record.partition
        ):
            raise ValueError("learning record left its exact THING owner")

    def admit(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
        whole_organism_capability: WholeOrganismEpisodeCapability,
        neuron_mosaic_assembly: NeuronMosaicAssembly,
        prior_learning_receipt_sha256: str | None = None,
    ) -> WholeOrganismThingMosaicLearningResolution:
        """Admit one complete multisensory consequence or leave no mutation."""

        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ) or not isinstance(
            custody_capability,
            SettledExperienceConsumerCapability,
        ):
            raise TypeError(
                "learning requires typed settled-experience custody"
            )
        if custody_capability.consumer_id != THING_MOSAIC_CONSUMER_ID:
            raise ValueError(
                "learning requires the THING custody capability"
            )
        if not isinstance(
            whole_organism_capability,
            WholeOrganismEpisodeCapability,
        ):
            raise TypeError(
                "learning requires a typed whole-organism capability"
            )
        if not isinstance(neuron_mosaic_assembly, NeuronMosaicAssembly):
            raise TypeError(
                "learning requires a typed neuron mosaic assembly"
            )

        with self._lock:
            try:
                episode = self._episodes.require(
                    whole_organism_capability,
                    DownstreamAuthority.LEARNING,
                )
                if (
                    episode.phase
                    is not WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED
                    or episode.l6_disposition is not L6Disposition.SETTLED
                ):
                    raise ValueError(
                        "learning requires one settled consequence"
                    )
                self._neurons.verify_mosaic_assembly(
                    neuron_mosaic_assembly,
                    expected_roots=episode.full_field_roots,
                    expected_settlement_receipt_sha256=(
                        episode.settlement_authority_receipt_sha256
                    ),
                )
                view = custody_authority.open_child(custody_capability)
                execution = view.world_execution
                if execution is None:
                    raise ValueError(
                        "learning requires applied-execution custody"
                    )
                if (
                    view.causal_settlement.authority_receipt_sha256
                    != episode.settlement_authority_receipt_sha256
                    or view.causal_settlement.structural_fingerprint
                    != episode.settlement_structural_fingerprint
                    or execution.authority_receipt_sha256
                    != episode.action_execution_receipt_sha256
                ):
                    raise ValueError(
                        "learning consequence crossed settled custody"
                    )
                six_lanes = self._six_lane_settlement(
                    episode,
                    view.causal_settlement,
                )
                observed = tuple(
                    value.sense
                    for value in six_lanes
                    if value.boundary_state == "observed"
                )
                if len(observed) < 2:
                    return WholeOrganismThingMosaicLearningResolution(
                        state="unresolved",
                        reasons=("fewer_than_two_observed_senses",),
                        record=None,
                        mosaic=None,
                    )
                if (
                    len(episode.full_field_roots)
                    > self._profile.max_roots_per_record
                ):
                    raise RuntimeError(
                        "learning full-field root capacity exhausted"
                    )
                if any(
                    value.story.episode_authority_receipt_sha256
                    == episode.authority_receipt_sha256
                    or value.story.source_occurrence_id
                    == view.source_occurrence_id
                    for value in self._records.values()
                ):
                    return WholeOrganismThingMosaicLearningResolution(
                        state="unresolved",
                        reasons=("experience_already_learned",),
                        record=None,
                        mosaic=None,
                    )
                if prior_learning_receipt_sha256 is None:
                    prior_record = None
                    prior_partition = None
                else:
                    _sha(
                        prior_learning_receipt_sha256,
                        "prior learning authority",
                    )
                    prior_record = self._records.get(
                        prior_learning_receipt_sha256
                    )
                    if prior_record is None:
                        raise ValueError(
                            "learning continuation names no retained prior"
                        )
                    prior_partition = prior_record.partition
                    current = next(
                        (
                            value for value in self._things.mosaics
                            if value.thing_id == prior_record.thing_id
                        ),
                        None,
                    )
                    if (
                        current is None
                        or current.version != prior_record.thing_version
                        or current.partitions[-1] != prior_partition
                    ):
                        raise ValueError(
                            "learning continuation prior is not current"
                        )
                partition = self._partitions.partition_from_custody(
                    custody_authority=custody_authority,
                    capability=custody_capability,
                    prior=prior_partition,
                )
                if (
                    partition.full_field_roots != episode.full_field_roots
                    or partition.entity_root_keys
                    != tuple(
                        sorted(
                            root.route_key
                            for root in episode.full_field_roots
                        )
                    )
                ):
                    raise ValueError(
                        "learning partition lost symmetric full-field roots"
                    )
                if prior_record is None:
                    prepared = (
                        self._things.prepare_custody_genesis_admission(
                            partition
                        )
                    )
                else:
                    prepared = (
                        self._things.prepare_ordered_custody_continuation(
                            (partition,)
                        )
                    )
                staged_mosaic = prepared.staged_mosaic
                story = self._story(
                    episode=episode,
                    partition=partition,
                )
                learning_record = self._seal(
                    thing_id=staged_mosaic.thing_id,
                    thing_version=staged_mosaic.version,
                    prior_learning_receipt_sha256=(
                        prior_learning_receipt_sha256
                    ),
                    partition=partition,
                    six_lane_settlement=six_lanes,
                    native_evidence_transition=(
                        episode.native_evidence_transition
                    ),
                    neuron_mosaic_assembly=neuron_mosaic_assembly,
                    story=story,
                    thing_mosaic_authority_receipt_sha256=(
                        staged_mosaic.authority_receipt_sha256
                    ),
                )
                self._verify_record(learning_record)
                if len(self._records) >= self._profile.max_records:
                    raise RuntimeError(
                        "whole-organism learning record capacity exhausted"
                    )
                staged_records = dict(self._records)
                staged_records[
                    learning_record.authority_receipt_sha256
                ] = learning_record
                self._encoded(staged_records)
            except (PermissionError, ValueError, RuntimeError) as error:
                return WholeOrganismThingMosaicLearningResolution(
                    state="unresolved",
                    reasons=(str(error),),
                    record=None,
                    mosaic=None,
                )

            prior_records = self._records
            undo = None
            try:
                if prior_record is None:
                    undo = (
                        self._things
                        .commit_prepared_custody_genesis_admission(
                            prepared
                        )
                    )
                else:
                    undo = (
                        self._things
                        .commit_prepared_ordered_custody_continuation(
                            prepared
                        )
                    )
                self._records = staged_records
                self._verify_external_authorities(learning_record)
            except BaseException:
                self._records = prior_records
                if undo is not None:
                    if prior_record is None:
                        self._things.rollback_committed_custody_genesis_admission(
                            undo
                        )
                    else:
                        self._things.rollback_committed_ordered_custody_continuation(
                            undo
                        )
                raise
            return WholeOrganismThingMosaicLearningResolution(
                state="learned",
                reasons=(),
                record=learning_record,
                mosaic=staged_mosaic,
            )

    def _body(
        self,
        records: Mapping[
            str,
            WholeOrganismThingMosaicLearningRecord,
        ],
    ) -> dict[str, object]:
        ordered = sorted(
            records.values(),
            key=lambda value: (
                value.story.source_time_start,
                value.story.source_time_end,
                value.thing_id,
                value.thing_version,
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
        records: Mapping[
            str,
            WholeOrganismThingMosaicLearningRecord,
        ],
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
            raise RuntimeError(
                "whole-organism learning state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._records)

    def rebind_neuron_owner(
        self,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
    ) -> None:
        """Rebind an equivalent cold-restored neuron authority atomically."""

        if not isinstance(
            neuron_owner,
            WholeOrganismNeuronPopulationOwner,
        ):
            raise TypeError(
                "whole-organism learning requires neuron-population owner"
            )
        with self._lock:
            for record in self._records.values():
                neuron_owner.verify_mosaic_assembly(
                    record.neuron_mosaic_assembly,
                    expected_roots=record.partition.full_field_roots,
                    expected_settlement_receipt_sha256=(
                        record.partition.settlement_receipt_sha256
                    ),
                )
            self._neurons = neuron_owner

    def rebind_episode_authority(
        self,
        episode_authority: WholeOrganismEpisodeAuthority,
    ) -> None:
        """Rebind equivalent cold-restored whole episodes atomically."""

        if not isinstance(
            episode_authority,
            WholeOrganismEpisodeAuthority,
        ):
            raise TypeError(
                "whole-organism learning requires episode authority"
            )
        with self._lock:
            prior = self._episodes
            self._episodes = episode_authority
            try:
                for record in self._records.values():
                    self._verify_external_authorities(record)
            except BaseException:
                self._episodes = prior
                raise

    def status(self) -> dict[str, object]:
        with self._lock:
            roots = sum(
                len(value.full_field_roots)
                for value in self._records.values()
            )
            return {
                "full_field": True,
                "master_sense": None,
                "records": len(self._records),
                "reduced_approximation": False,
                "retained_roots": roots,
                "schema": (
                    "guala.whole_organism_thing_mosaic_learning.status.v1"
                ),
                "state_bytes": len(self._encoded(self._records)),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: WholeOrganismThingMosaicLearningProfile,
        episode_authority: WholeOrganismEpisodeAuthority,
        partition_authority: CustodiedW1ContactThingEncounterAuthority,
        thing_owner: CausalThingMosaicOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
        encoded: bytes,
    ) -> "WholeOrganismThingMosaicLearningOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("whole-organism learning cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "whole-organism learning cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {
                "body",
                "schema",
                "state_hmac_sha256",
            }
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "whole-organism learning cold envelope changed"
            )
        body = envelope.get("body")
        if envelope.get("schema") == LEGACY_ENVELOPE_SCHEMA:
            if (
                not isinstance(body, dict)
                or set(body) != {"profile", "records", "schema"}
                or body.get("schema") != LEGACY_STATE_SCHEMA
                or body.get("profile") != profile.record()
                or body.get("records") != []
            ):
                raise ValueError(
                    "only empty legacy learning state can migrate"
                )
            root = _key(
                authority_key,
                "whole-organism THING learning",
            )
            legacy_state_key = hashlib.sha256(
                _LEGACY_STATE_DOMAIN + root
            ).digest()
            expected_legacy_hmac = hmac.new(
                legacy_state_key,
                _LEGACY_STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(
                envelope.get("state_hmac_sha256", ""),
                expected_legacy_hmac,
            ):
                raise ValueError(
                    "legacy whole-organism learning authority changed"
                )
            return cls(
                authority_key=authority_key,
                profile=profile,
                episode_authority=episode_authority,
                partition_authority=partition_authority,
                thing_owner=thing_owner,
                neuron_owner=neuron_owner,
            )
        if envelope.get("schema") != ENVELOPE_SCHEMA:
            raise ValueError(
                "whole-organism learning cold envelope changed"
            )
        if (
            not isinstance(body, dict)
            or set(body) != {"profile", "records", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
            or not isinstance(body.get("records"), list)
        ):
            raise ValueError(
                "whole-organism learning cold payload changed"
            )
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            episode_authority=episode_authority,
            partition_authority=partition_authority,
            thing_owner=thing_owner,
            neuron_owner=neuron_owner,
        )
        expected_hmac = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            envelope.get("state_hmac_sha256", ""),
            expected_hmac,
        ):
            raise ValueError(
                "whole-organism learning cold state authority changed"
            )
        for raw in body["records"]:
            record = owner._record_from_raw(raw)
            if record.authority_receipt_sha256 in owner._records:
                raise ValueError(
                    "whole-organism learning cold state repeats a record"
                )
            owner._verify_record(record)
            owner._verify_external_authorities(record)
            owner._records[record.authority_receipt_sha256] = record
        owner._verify_retained_chains()
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "whole-organism learning cold round-trip changed state"
            )
        return owner

    def _verify_retained_chains(self) -> None:
        by_receipt = self._records
        by_thing: dict[
            str,
            list[WholeOrganismThingMosaicLearningRecord],
        ] = {}
        for record in by_receipt.values():
            by_thing.setdefault(record.thing_id, []).append(record)
        mosaics = {
            value.thing_id: value for value in self._things.mosaics
        }
        for thing_id, values in by_thing.items():
            ordered = sorted(values, key=lambda value: value.thing_version)
            mosaic = mosaics.get(thing_id)
            if (
                mosaic is None
                or tuple(value.thing_version for value in ordered)
                != tuple(range(len(ordered)))
                or mosaic.version != ordered[-1].thing_version
                or tuple(value.partition for value in ordered)
                != mosaic.partitions
            ):
                raise ValueError(
                    "whole-organism learning cold THING chain changed"
                )
            for index, value in enumerate(ordered):
                expected_prior = (
                    None
                    if index == 0
                    else ordered[index - 1].authority_receipt_sha256
                )
                if value.prior_learning_receipt_sha256 != expected_prior:
                    raise ValueError(
                        "whole-organism learning cold story chain changed"
                    )

    def _record_from_raw(
        self,
        raw: object,
    ) -> WholeOrganismThingMosaicLearningRecord:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "partition",
            "prior_learning_receipt_sha256",
            "native_evidence_transition",
            "neuron_mosaic_assembly",
            "schema",
            "six_lane_settlement",
            "story",
            "thing_id",
            "thing_mosaic_authority_receipt_sha256",
            "thing_version",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != RECORD_SCHEMA
            or not isinstance(raw.get("six_lane_settlement"), list)
        ):
            raise ValueError(
                "whole-organism learning cold record changed"
            )
        return WholeOrganismThingMosaicLearningRecord(
            thing_id=raw["thing_id"],
            thing_version=raw["thing_version"],
            prior_learning_receipt_sha256=(
                raw["prior_learning_receipt_sha256"]
            ),
            partition=self._partition_from_raw(raw["partition"]),
            six_lane_settlement=tuple(
                self._sense_state_from_raw(value)
                for value in raw["six_lane_settlement"]
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
            thing_mosaic_authority_receipt_sha256=(
                raw["thing_mosaic_authority_receipt_sha256"]
            ),
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )

    @staticmethod
    def _sense_state_from_raw(
        raw: object,
    ) -> WholeOrganismSenseSettlement:
        expected = {
            "boundary_receipt_sha256",
            "boundary_state",
            "contribution_authority_receipt_sha256",
            "contribution_state",
            "mechanism_id",
            "relation",
            "root_route_keys",
            "schema",
            "sense",
            "structural_fingerprint",
            "topology_receipt_sha256",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != SENSE_STATE_SCHEMA
            or not isinstance(raw.get("root_route_keys"), list)
            or any(
                not isinstance(value, list) or len(value) != 2
                for value in raw["root_route_keys"]
            )
        ):
            raise ValueError(
                "whole-organism learning cold sense state changed"
            )
        return WholeOrganismSenseSettlement(
            sense=raw["sense"],
            boundary_state=raw["boundary_state"],
            relation=raw["relation"],
            structural_fingerprint=raw["structural_fingerprint"],
            topology_receipt_sha256=raw["topology_receipt_sha256"],
            boundary_receipt_sha256=raw["boundary_receipt_sha256"],
            mechanism_id=raw["mechanism_id"],
            contribution_state=ContributionState(
                raw["contribution_state"]
            ),
            contribution_authority_receipt_sha256=(
                raw["contribution_authority_receipt_sha256"]
            ),
            root_route_keys=tuple(
                (value[0], value[1])
                for value in raw["root_route_keys"]
            ),
        )

    @staticmethod
    def _story_from_raw(raw: object) -> WholeOrganismCausalStory:
        expected = {
            "action_authority_receipt_sha256",
            "action_execution_receipt_sha256",
            "chain_id",
            "entity_continuity_hmac_sha256",
            "episode_authority_receipt_sha256",
            "episode_id",
            "l6_authority_receipt_sha256",
            "manifest_receipt_sha256",
            "parent_custody_receipt_sha256",
            "prior_episode_receipt_sha256",
            "schema",
            "settlement_authority_receipt_sha256",
            "settlement_event_id",
            "settlement_structural_fingerprint",
            "source_occurrence_id",
            "source_time_end",
            "source_time_start",
            "thing_custody_capability_receipt_sha256",
            "world_observation_receipt_sha256",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != STORY_SCHEMA
        ):
            raise ValueError(
                "whole-organism learning cold story changed"
            )
        return WholeOrganismCausalStory(
            episode_id=raw["episode_id"],
            chain_id=raw["chain_id"],
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold learning story start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold learning story end",
            ),
            manifest_receipt_sha256=raw["manifest_receipt_sha256"],
            episode_authority_receipt_sha256=(
                raw["episode_authority_receipt_sha256"]
            ),
            settlement_event_id=raw["settlement_event_id"],
            settlement_authority_receipt_sha256=(
                raw["settlement_authority_receipt_sha256"]
            ),
            settlement_structural_fingerprint=(
                raw["settlement_structural_fingerprint"]
            ),
            action_authority_receipt_sha256=(
                raw["action_authority_receipt_sha256"]
            ),
            prior_episode_receipt_sha256=(
                raw["prior_episode_receipt_sha256"]
            ),
            action_execution_receipt_sha256=(
                raw["action_execution_receipt_sha256"]
            ),
            l6_authority_receipt_sha256=(
                raw["l6_authority_receipt_sha256"]
            ),
            source_occurrence_id=raw["source_occurrence_id"],
            parent_custody_receipt_sha256=(
                raw["parent_custody_receipt_sha256"]
            ),
            thing_custody_capability_receipt_sha256=(
                raw["thing_custody_capability_receipt_sha256"]
            ),
            world_observation_receipt_sha256=(
                raw["world_observation_receipt_sha256"]
            ),
            entity_continuity_hmac_sha256=(
                raw["entity_continuity_hmac_sha256"]
            ),
        )

    @staticmethod
    def _partition_from_raw(raw: object) -> ThingEncounterPartition:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "entity_continuity_hmac_sha256",
            "entity_root_keys",
            "execution_receipt_sha256",
            "full_field_roots",
            "parent_custody_receipt_sha256",
            "prior_partition_receipt_sha256",
            "schema",
            "settlement_receipt_sha256",
            "settlement_structural_fingerprint",
            "source_occurrence_id",
            "thing_custody_capability_receipt_sha256",
            "world_observation_receipt_sha256",
            "world_revision",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or not isinstance(raw.get("full_field_roots"), list)
            or not isinstance(raw.get("entity_root_keys"), list)
            or any(
                not isinstance(value, list) or len(value) != 2
                for value in raw["entity_root_keys"]
            )
        ):
            raise ValueError(
                "whole-organism learning cold partition changed"
            )
        return ThingEncounterPartition(
            source_occurrence_id=raw["source_occurrence_id"],
            parent_custody_receipt_sha256=(
                raw["parent_custody_receipt_sha256"]
            ),
            thing_custody_capability_receipt_sha256=(
                raw["thing_custody_capability_receipt_sha256"]
            ),
            settlement_receipt_sha256=raw["settlement_receipt_sha256"],
            settlement_structural_fingerprint=(
                raw["settlement_structural_fingerprint"]
            ),
            world_observation_receipt_sha256=(
                raw["world_observation_receipt_sha256"]
            ),
            execution_receipt_sha256=raw["execution_receipt_sha256"],
            world_revision=raw["world_revision"],
            entity_continuity_hmac_sha256=(
                raw["entity_continuity_hmac_sha256"]
            ),
            prior_partition_receipt_sha256=(
                raw["prior_partition_receipt_sha256"]
            ),
            entity_root_keys=tuple(
                (value[0], value[1])
                for value in raw["entity_root_keys"]
            ),
            full_field_roots=tuple(
                WholeOrganismThingMosaicLearningOwner._root_from_raw(value)
                for value in raw["full_field_roots"]
            ),
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
            raise ValueError(
                "whole-organism learning cold full-field root changed"
            )
        root = FullFieldSensoryRoot(
            sense=raw["sense"],
            topology_index=raw["topology_index"],
            physical_value_sha256=raw["physical_value_sha256"],
            full_evidence_json=raw["full_evidence_json"],
        )
        root.verify()
        return root


__all__ = (
    "WholeOrganismCausalStory",
    "WholeOrganismSenseSettlement",
    "WholeOrganismThingMosaicLearningOwner",
    "WholeOrganismThingMosaicLearningProfile",
    "WholeOrganismThingMosaicLearningRecord",
    "WholeOrganismThingMosaicLearningResolution",
)
