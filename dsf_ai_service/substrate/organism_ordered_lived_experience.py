"""Bounded organism-owned order over authenticated lived experiences.

This module retains observed causal adjacency between complete settled
whole-organism occurrences.  An occurrence must first be admitted from an
existing passive or action-consequence learning record, its matching settled
whole-organism episode, and the exact retained historical THING mosaic.

Relations may cross THING identity.  They preserve the complete explicit
D/M/R/U/C/P/B evidence of both occurrences and exact causal time.  The owner
derives one HMAC-authenticated organism-life chronology; callers cannot supply
or select a context.  Every later relation must continue from the prior
relation's exact target.  There are no labels, scores, thresholds, text,
grammar, meaning assertions, ML operations, or changes to L0-L4.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaic,
    CausalThingMosaicOwner,
    FullFieldSensoryRoot,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveThingLearningRecord,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    DownstreamAuthority,
    L6Disposition,
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodePhase,
    WholeOrganismEpisodeRecord,
)
from dsf_ai_service.substrate.whole_organism_thing_mosaic_learning import (
    WholeOrganismThingMosaicLearningOwner,
    WholeOrganismThingMosaicLearningRecord,
)


PROFILE_SCHEMA = "guala.organism_ordered_lived_experience.profile.v1"
OCCURRENCE_SCHEMA = "guala.organism_ordered_lived_experience.occurrence.v1"
RELATION_SCHEMA = "guala.organism_ordered_lived_experience.relation.v1"
PREPARED_SCHEMA = "guala.organism_ordered_lived_experience.prepared.v1"
STATE_SCHEMA = "guala.organism_ordered_lived_experience.state.v1"
ENVELOPE_SCHEMA = "guala.organism_ordered_lived_experience.state_hmac.v1"
STATUS_SCHEMA = "guala.organism_ordered_lived_experience.status.v1"

_OCCURRENCE_DOMAIN = b"guala-organism-ordered-lived-occurrence-v1\0"
_RELATION_DOMAIN = b"guala-organism-ordered-lived-relation-v1\0"
_PREPARED_DOMAIN = b"guala-organism-ordered-lived-prepared-v1\0"
_STATE_DOMAIN = b"guala-organism-ordered-lived-state-v1\0"
_HEX = frozenset("0123456789abcdef")
_LEARNING_KINDS = frozenset({"passive", "consequence"})
_PHASES = frozenset({
    WholeOrganismEpisodePhase.OBSERVATION_COMPLETED.value,
    WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED.value,
})


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


def _key(value: bytes | str, domain: bytes) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("ordered lived-experience authority key changed")
    return hashlib.sha256(domain + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} changed")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("ordered lived-experience time must be exact")
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


def _verify_full_root(root: FullFieldSensoryRoot) -> None:
    if not isinstance(root, FullFieldSensoryRoot):
        raise TypeError("ordered lived-experience root is not typed")
    root.verify()


def _roots_receipt(
    roots: tuple[FullFieldSensoryRoot, ...],
) -> str:
    if not roots:
        raise ValueError("ordered lived-experience roots are absent")
    for root in roots:
        _verify_full_root(root)
    return _digest([root.record() for root in roots])


@dataclass(frozen=True, slots=True)
class OrderedLivedExperienceProfile:
    profile_id: str
    max_occurrences: int
    max_relations: int
    max_roots_per_occurrence: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_occurrences: int,
        max_relations: int,
        max_roots_per_occurrence: int,
        max_state_bytes: int,
    ) -> "OrderedLivedExperienceProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id,
                "ordered lived-experience profile",
            ),
            max_occurrences=_positive(
                max_occurrences,
                "ordered lived-experience occurrence capacity",
            ),
            max_relations=_positive(
                max_relations,
                "ordered lived-experience relation capacity",
            ),
            max_roots_per_occurrence=_positive(
                max_roots_per_occurrence,
                "ordered lived-experience root capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "ordered lived-experience state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_occurrences=provisional.max_occurrences,
            max_relations=provisional.max_relations,
            max_roots_per_occurrence=(
                provisional.max_roots_per_occurrence
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_occurrences": self.max_occurrences,
            "max_relations": self.max_relations,
            "max_roots_per_occurrence": self.max_roots_per_occurrence,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            max_occurrences=self.max_occurrences,
            max_relations=self.max_relations,
            max_roots_per_occurrence=self.max_roots_per_occurrence,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError(
                "ordered lived-experience profile authority changed"
            )


@dataclass(frozen=True, slots=True)
class SettledLivedExperienceOccurrence:
    learning_kind: str
    thing_id: str
    mosaic_receipt_sha256: str
    terminal_partition_receipt_sha256: str
    learning_receipt_sha256: str
    episode_receipt_sha256: str
    episode_phase: str
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    source_occurrence_id: str
    causal_story_receipt_sha256: str
    story_chain_receipt_sha256: str
    entity_continuity_hmac_sha256: str
    source_time_start: Fraction
    source_time_end: Fraction
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "causal_story_receipt_sha256": (
                self.causal_story_receipt_sha256
            ),
            "entity_continuity_hmac_sha256": (
                self.entity_continuity_hmac_sha256
            ),
            "episode_phase": self.episode_phase,
            "episode_receipt_sha256": self.episode_receipt_sha256,
            "full_field_roots": [
                value.record() for value in self.full_field_roots
            ],
            "learning_kind": self.learning_kind,
            "learning_receipt_sha256": self.learning_receipt_sha256,
            "mosaic_receipt_sha256": self.mosaic_receipt_sha256,
            "schema": OCCURRENCE_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "story_chain_receipt_sha256": (
                self.story_chain_receipt_sha256
            ),
            "terminal_partition_receipt_sha256": (
                self.terminal_partition_receipt_sha256
            ),
            "thing_id": self.thing_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def custody_record(self) -> dict[str, object]:
        """Persist source custody without duplicating retained field bytes."""

        payload = self.payload()
        payload.pop("full_field_roots")
        return payload | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "full_field_root_count": len(self.full_field_roots),
            "full_field_roots_receipt_sha256": _roots_receipt(
                self.full_field_roots
            ),
        }


@dataclass(frozen=True, slots=True)
class OrderedLivedExperienceSourceCustody:
    """Existing owners that retain the one authoritative learned evidence."""

    episode_authority: WholeOrganismEpisodeAuthority
    passive_learning_owner: PassiveWholeOrganismThingLearningOwner
    consequence_learning_owner: WholeOrganismThingMosaicLearningOwner
    thing_owner: CausalThingMosaicOwner

    def verify(self) -> None:
        if (
            not isinstance(
                self.episode_authority,
                WholeOrganismEpisodeAuthority,
            )
            or not isinstance(
                self.passive_learning_owner,
                PassiveWholeOrganismThingLearningOwner,
            )
            or not isinstance(
                self.consequence_learning_owner,
                WholeOrganismThingMosaicLearningOwner,
            )
            or not isinstance(self.thing_owner, CausalThingMosaicOwner)
        ):
            raise TypeError(
                "ordered lived-experience source custody is not typed"
            )

    def episode(
        self,
        episode_receipt_sha256: str,
    ) -> WholeOrganismEpisodeRecord:
        matches = tuple(
            value
            for value in self.episode_authority.episodes
            if value.authority_receipt_sha256
            == episode_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "ordered lived-experience episode custody is absent"
            )
        capability = self.episode_authority.capability_for(
            episode_receipt_sha256
        )
        return self.episode_authority.require(
            capability,
            DownstreamAuthority.LEARNING,
        )


class SettledLivedExperienceAuthority:
    """Admit only source-owned settled episodes and learned THING custody."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        self._key = _key(authority_key, _OCCURRENCE_DOMAIN)

    def _seal(
        self,
        *,
        learning_kind: str,
        thing_id: str,
        mosaic_receipt_sha256: str,
        terminal_partition_receipt_sha256: str,
        learning_receipt_sha256: str,
        episode_receipt_sha256: str,
        episode_phase: str,
        settlement_receipt_sha256: str,
        settlement_structural_fingerprint: str,
        source_occurrence_id: str,
        causal_story_receipt_sha256: str,
        story_chain_receipt_sha256: str,
        entity_continuity_hmac_sha256: str,
        source_time_start: Fraction,
        source_time_end: Fraction,
        full_field_roots: tuple[FullFieldSensoryRoot, ...],
    ) -> SettledLivedExperienceOccurrence:
        provisional = SettledLivedExperienceOccurrence(
            learning_kind=learning_kind,
            thing_id=thing_id,
            mosaic_receipt_sha256=mosaic_receipt_sha256,
            terminal_partition_receipt_sha256=(
                terminal_partition_receipt_sha256
            ),
            learning_receipt_sha256=learning_receipt_sha256,
            episode_receipt_sha256=episode_receipt_sha256,
            episode_phase=episode_phase,
            settlement_receipt_sha256=settlement_receipt_sha256,
            settlement_structural_fingerprint=(
                settlement_structural_fingerprint
            ),
            source_occurrence_id=source_occurrence_id,
            causal_story_receipt_sha256=causal_story_receipt_sha256,
            story_chain_receipt_sha256=story_chain_receipt_sha256,
            entity_continuity_hmac_sha256=(
                entity_continuity_hmac_sha256
            ),
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            full_field_roots=full_field_roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        self._verify_payload(provisional)
        signature = hmac.new(
            self._key,
            _OCCURRENCE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = SettledLivedExperienceOccurrence(
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
        self.verify(result)
        return result

    @staticmethod
    def _verify_payload(
        value: SettledLivedExperienceOccurrence,
    ) -> None:
        if not isinstance(value, SettledLivedExperienceOccurrence):
            raise TypeError("settled lived occurrence is not typed")
        if value.learning_kind not in _LEARNING_KINDS:
            raise ValueError("settled lived occurrence kind changed")
        if value.episode_phase not in _PHASES:
            raise ValueError("settled lived occurrence phase changed")
        for digest, label in (
            (value.thing_id, "settled lived THING"),
            (value.mosaic_receipt_sha256, "settled lived mosaic"),
            (
                value.terminal_partition_receipt_sha256,
                "settled lived terminal partition",
            ),
            (value.learning_receipt_sha256, "settled lived learning"),
            (value.episode_receipt_sha256, "settled lived episode"),
            (value.settlement_receipt_sha256, "settled lived settlement"),
            (
                value.settlement_structural_fingerprint,
                "settled lived structure",
            ),
            (
                value.source_occurrence_id,
                "settled lived source occurrence",
            ),
            (
                value.causal_story_receipt_sha256,
                "settled lived causal story",
            ),
            (
                value.story_chain_receipt_sha256,
                "settled lived story chain",
            ),
            (
                value.entity_continuity_hmac_sha256,
                "settled lived entity continuity",
            ),
        ):
            _sha(digest, label)
        if (
            not isinstance(value.source_time_start, Fraction)
            or not isinstance(value.source_time_end, Fraction)
            or value.source_time_end <= value.source_time_start
            or not value.full_field_roots
        ):
            raise ValueError("settled lived occurrence extent changed")
        for root in value.full_field_roots:
            _verify_full_root(root)

    def verify(self, value: SettledLivedExperienceOccurrence) -> None:
        self._verify_payload(value)
        _sha(value.authority_hmac_sha256, "settled lived HMAC")
        _sha(value.authority_receipt_sha256, "settled lived authority")
        expected = hmac.new(
            self._key,
            _OCCURRENCE_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError("settled lived occurrence authority changed")

    @staticmethod
    def _episode(
        *,
        episode_authority: WholeOrganismEpisodeAuthority,
        episode: WholeOrganismEpisodeRecord,
    ) -> WholeOrganismEpisodeRecord:
        if not isinstance(
            episode_authority,
            WholeOrganismEpisodeAuthority,
        ) or not isinstance(episode, WholeOrganismEpisodeRecord):
            raise TypeError(
                "settled lived occurrence requires typed episode custody"
            )
        capability = episode_authority.capability_for(
            episode.authority_receipt_sha256
        )
        retained = episode_authority.require(
            capability,
            DownstreamAuthority.LEARNING,
        )
        if (
            retained != episode
            or episode.l6_disposition is not L6Disposition.SETTLED
            or episode.phase
            not in {
                WholeOrganismEpisodePhase.OBSERVATION_COMPLETED,
                WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED,
            }
        ):
            raise ValueError(
                "settled lived occurrence lacks one settled learned episode"
            )
        return retained

    @staticmethod
    def _mosaic(
        *,
        thing_owner: CausalThingMosaicOwner,
        mosaic: CausalThingMosaic,
        thing_id: str,
        terminal_partition_receipt_sha256: str,
    ) -> CausalThingMosaic:
        if not isinstance(
            thing_owner,
            CausalThingMosaicOwner,
        ) or not isinstance(mosaic, CausalThingMosaic):
            raise TypeError(
                "settled lived occurrence requires typed THING custody"
            )
        retained = thing_owner.materialize_retained_prefix(
            thing_id=thing_id,
            terminal_partition_receipt_sha256=(
                terminal_partition_receipt_sha256
            ),
        )
        if retained != mosaic:
            raise ValueError(
                "settled lived occurrence changed historical mosaic custody"
            )
        return retained

    def admit_passive(
        self,
        *,
        episode_authority: WholeOrganismEpisodeAuthority,
        episode: WholeOrganismEpisodeRecord,
        learning_owner: PassiveWholeOrganismThingLearningOwner,
        learning_record: PassiveThingLearningRecord,
        thing_owner: CausalThingMosaicOwner,
        mosaic: CausalThingMosaic,
    ) -> SettledLivedExperienceOccurrence:
        episode = self._episode(
            episode_authority=episode_authority,
            episode=episode,
        )
        if not isinstance(
            learning_owner,
            PassiveWholeOrganismThingLearningOwner,
        ) or not isinstance(learning_record, PassiveThingLearningRecord):
            raise TypeError(
                "passive lived occurrence requires typed learning custody"
            )
        learning_owner._verify_record(learning_record)
        learning_owner._verify_target(learning_record)
        if learning_record not in learning_owner.records:
            raise ValueError("passive lived learning is not retained")
        story = learning_record.story
        if (
            episode.phase
            is not WholeOrganismEpisodePhase.OBSERVATION_COMPLETED
            or episode.settlement_authority_receipt_sha256
            != story.settlement_authority_receipt_sha256
            or episode.settlement_structural_fingerprint
            != story.settlement_structural_fingerprint
            or episode.source_time_start != story.source_time_start
            or episode.source_time_end != story.source_time_end
            or episode.full_field_roots != learning_record.full_field_roots
        ):
            raise ValueError(
                "passive lived occurrence crossed episode custody"
            )
        retained = self._mosaic(
            thing_owner=thing_owner,
            mosaic=mosaic,
            thing_id=learning_record.thing_id,
            terminal_partition_receipt_sha256=(
                story.target_partition_authority_receipt_sha256
            ),
        )
        return self._seal(
            learning_kind="passive",
            thing_id=learning_record.thing_id,
            mosaic_receipt_sha256=retained.authority_receipt_sha256,
            terminal_partition_receipt_sha256=(
                story.target_partition_authority_receipt_sha256
            ),
            learning_receipt_sha256=(
                learning_record.authority_receipt_sha256
            ),
            episode_receipt_sha256=episode.authority_receipt_sha256,
            episode_phase=episode.phase.value,
            settlement_receipt_sha256=(
                episode.settlement_authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                episode.settlement_structural_fingerprint
            ),
            source_occurrence_id=story.source_occurrence_id,
            causal_story_receipt_sha256=_digest(story.payload()),
            story_chain_receipt_sha256=_digest({
                "parent_custody_receipt_sha256": (
                    story.parent_custody_receipt_sha256
                ),
                "source_kind": story.source_kind,
            }),
            entity_continuity_hmac_sha256=(
                story.entity_continuity_hmac_sha256
            ),
            source_time_start=episode.source_time_start,
            source_time_end=episode.source_time_end,
            full_field_roots=episode.full_field_roots,
        )

    def admit_consequence(
        self,
        *,
        episode_authority: WholeOrganismEpisodeAuthority,
        episode: WholeOrganismEpisodeRecord,
        learning_owner: WholeOrganismThingMosaicLearningOwner,
        learning_record: WholeOrganismThingMosaicLearningRecord,
        thing_owner: CausalThingMosaicOwner,
        mosaic: CausalThingMosaic,
    ) -> SettledLivedExperienceOccurrence:
        episode = self._episode(
            episode_authority=episode_authority,
            episode=episode,
        )
        if not isinstance(
            learning_owner,
            WholeOrganismThingMosaicLearningOwner,
        ) or not isinstance(
            learning_record,
            WholeOrganismThingMosaicLearningRecord,
        ):
            raise TypeError(
                "consequence lived occurrence requires typed learning custody"
            )
        learning_owner._verify_record(learning_record)
        learning_owner._verify_external_authorities(learning_record)
        if learning_record not in learning_owner.records:
            raise ValueError("consequence lived learning is not retained")
        story = learning_record.story
        if (
            episode.phase
            is not WholeOrganismEpisodePhase.CONSEQUENCE_COMPLETED
            or episode.authority_receipt_sha256
            != story.episode_authority_receipt_sha256
            or episode.settlement_authority_receipt_sha256
            != story.settlement_authority_receipt_sha256
            or episode.settlement_structural_fingerprint
            != story.settlement_structural_fingerprint
            or episode.source_time_start != story.source_time_start
            or episode.source_time_end != story.source_time_end
            or episode.full_field_roots != learning_record.full_field_roots
        ):
            raise ValueError(
                "consequence lived occurrence crossed episode custody"
            )
        retained = self._mosaic(
            thing_owner=thing_owner,
            mosaic=mosaic,
            thing_id=learning_record.thing_id,
            terminal_partition_receipt_sha256=(
                learning_record.partition.authority_receipt_sha256
            ),
        )
        if (
            retained.authority_receipt_sha256
            != learning_record.thing_mosaic_authority_receipt_sha256
        ):
            raise ValueError(
                "consequence lived occurrence changed learned mosaic"
            )
        return self._seal(
            learning_kind="consequence",
            thing_id=learning_record.thing_id,
            mosaic_receipt_sha256=retained.authority_receipt_sha256,
            terminal_partition_receipt_sha256=(
                learning_record.partition.authority_receipt_sha256
            ),
            learning_receipt_sha256=(
                learning_record.authority_receipt_sha256
            ),
            episode_receipt_sha256=episode.authority_receipt_sha256,
            episode_phase=episode.phase.value,
            settlement_receipt_sha256=(
                episode.settlement_authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                episode.settlement_structural_fingerprint
            ),
            source_occurrence_id=story.source_occurrence_id,
            causal_story_receipt_sha256=_digest(story.payload()),
            story_chain_receipt_sha256=_digest({
                "chain_id": story.chain_id,
                "prior_episode_receipt_sha256": (
                    story.prior_episode_receipt_sha256
                ),
            }),
            entity_continuity_hmac_sha256=(
                story.entity_continuity_hmac_sha256
            ),
            source_time_start=episode.source_time_start,
            source_time_end=episode.source_time_end,
            full_field_roots=episode.full_field_roots,
        )


@dataclass(frozen=True, slots=True)
class OrderedLivedExperienceRelation:
    chronology_authority_receipt_sha256: str
    chronology_sequence: int
    predecessor_relation_receipt_sha256: str | None
    source_occurrence_receipt_sha256: str
    target_occurrence_receipt_sha256: str
    source_thing_id: str
    target_thing_id: str
    same_thing: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "chronology_authority_receipt_sha256": (
                self.chronology_authority_receipt_sha256
            ),
            "chronology_sequence": self.chronology_sequence,
            "predecessor_relation_receipt_sha256": (
                self.predecessor_relation_receipt_sha256
            ),
            "same_thing": self.same_thing,
            "schema": RELATION_SCHEMA,
            "source_occurrence_receipt_sha256": (
                self.source_occurrence_receipt_sha256
            ),
            "source_thing_id": self.source_thing_id,
            "target_occurrence_receipt_sha256": (
                self.target_occurrence_receipt_sha256
            ),
            "target_thing_id": self.target_thing_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _PreparedState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class PreparedOrderedLivedExperience:
    state: str
    relation: OrderedLivedExperienceRelation | None
    prior_occurrences: tuple[SettledLivedExperienceOccurrence, ...]
    prior_relations: tuple[OrderedLivedExperienceRelation, ...]
    staged_occurrences: tuple[SettledLivedExperienceOccurrence, ...]
    staged_relations: tuple[OrderedLivedExperienceRelation, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    _state: _PreparedState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "prior_occurrence_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_occurrences
            ],
            "prior_relation_receipts": [
                value.authority_receipt_sha256
                for value in self.prior_relations
            ],
            "relation_receipt_sha256": (
                None
                if self.relation is None
                else self.relation.authority_receipt_sha256
            ),
            "schema": PREPARED_SCHEMA,
            "staged_occurrence_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_occurrences
            ],
            "staged_relation_receipts": [
                value.authority_receipt_sha256
                for value in self.staged_relations
            ],
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class OrderedLivedExperienceUndo:
    prepared: PreparedOrderedLivedExperience
    _owner_authority: object = field(repr=False, compare=False)


class OrganismOrderedLivedExperienceOwner:
    """Own exact causal paths across complete learned occurrences."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: OrderedLivedExperienceProfile,
        evidence_authority: SettledLivedExperienceAuthority,
        source_custody: OrderedLivedExperienceSourceCustody | None = None,
    ) -> None:
        if not isinstance(profile, OrderedLivedExperienceProfile):
            raise TypeError(
                "ordered lived-experience profile is not typed"
            )
        profile.verify()
        if not isinstance(
            evidence_authority,
            SettledLivedExperienceAuthority,
        ):
            raise TypeError(
                "ordered lived-experience evidence authority is not typed"
            )
        if source_custody is not None:
            if not isinstance(
                source_custody,
                OrderedLivedExperienceSourceCustody,
            ):
                raise TypeError(
                    "ordered lived-experience source custody is not typed"
                )
            source_custody.verify()
        root = _key(authority_key, _RELATION_DOMAIN)
        self._relation_key = hashlib.sha256(
            _RELATION_DOMAIN + root
        ).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._evidence = evidence_authority
        self._source_custody = source_custody
        chronology_payload = {
            "profile_authority_receipt_sha256": (
                profile.authority_receipt_sha256
            ),
            "schema": (
                "guala.organism_ordered_lived_experience."
                "chronology_identity.v1"
            ),
        }
        chronology_hmac = hmac.new(
            self._relation_key,
            b"guala-organism-lived-chronology-identity-v1\0"
            + _canonical(chronology_payload),
            hashlib.sha256,
        ).hexdigest()
        self._chronology_authority_receipt_sha256 = _digest({
            "authority_hmac_sha256": chronology_hmac,
            "payload": chronology_payload,
        })
        self._occurrences: tuple[SettledLivedExperienceOccurrence, ...] = ()
        self._relations: tuple[OrderedLivedExperienceRelation, ...] = ()
        self._prepared: PreparedOrderedLivedExperience | None = None
        self._owner_authority = object()
        self._lock = threading.RLock()
        initial_body = self._state_body(
            self._occurrences,
            self._relations,
        )
        self._committed_state_receipt_sha256 = _digest(initial_body)
        self._committed_encoded = self._encoded(
            self._occurrences,
            self._relations,
        )

    def rebind_source_custody(
        self,
        source_custody: OrderedLivedExperienceSourceCustody,
    ) -> None:
        """Rebind equivalent restored source authorities atomically."""

        if not isinstance(
            source_custody,
            OrderedLivedExperienceSourceCustody,
        ):
            raise TypeError(
                "ordered lived-experience source custody is not typed"
            )
        source_custody.verify()
        with self._lock:
            prior = self._source_custody
            self._source_custody = source_custody
            try:
                self._verify_graph(self._occurrences, self._relations)
            except BaseException:
                self._source_custody = prior
                raise

    def _require_source_custody(
        self,
        occurrence: SettledLivedExperienceOccurrence,
    ) -> None:
        custody = self._source_custody
        if custody is None:
            return
        episode = custody.episode(
            occurrence.episode_receipt_sha256
        )
        if occurrence.learning_kind == "passive":
            records = tuple(
                value
                for value in custody.passive_learning_owner.records
                if value.authority_receipt_sha256
                == occurrence.learning_receipt_sha256
            )
            if len(records) != 1:
                raise ValueError(
                    "ordered lived-experience passive custody is absent"
                )
            record = records[0]
            mosaic = custody.thing_owner.materialize_retained_prefix(
                thing_id=record.thing_id,
                terminal_partition_receipt_sha256=(
                    record.story
                    .target_partition_authority_receipt_sha256
                ),
            )
            expected = self._evidence.admit_passive(
                episode_authority=custody.episode_authority,
                episode=episode,
                learning_owner=custody.passive_learning_owner,
                learning_record=record,
                thing_owner=custody.thing_owner,
                mosaic=mosaic,
            )
        else:
            records = tuple(
                value
                for value in custody.consequence_learning_owner.records
                if value.authority_receipt_sha256
                == occurrence.learning_receipt_sha256
            )
            if len(records) != 1:
                raise ValueError(
                    "ordered lived-experience consequence custody is absent"
                )
            record = records[0]
            mosaic = custody.thing_owner.materialize_retained_prefix(
                thing_id=record.thing_id,
                terminal_partition_receipt_sha256=(
                    record.partition.authority_receipt_sha256
                ),
            )
            expected = self._evidence.admit_consequence(
                episode_authority=custody.episode_authority,
                episode=episode,
                learning_owner=custody.consequence_learning_owner,
                learning_record=record,
                thing_owner=custody.thing_owner,
                mosaic=mosaic,
            )
        if expected != occurrence:
            raise ValueError(
                "ordered lived-experience crossed source custody"
            )

    @property
    def occurrences(self) -> tuple[SettledLivedExperienceOccurrence, ...]:
        with self._lock:
            return self._occurrences

    @property
    def relations(self) -> tuple[OrderedLivedExperienceRelation, ...]:
        with self._lock:
            return self._relations

    @property
    def chronology_authority_receipt_sha256(self) -> str:
        return self._chronology_authority_receipt_sha256

    def _seal_relation(
        self,
        *,
        chronology_sequence: int,
        predecessor_relation_receipt_sha256: str | None,
        source: SettledLivedExperienceOccurrence,
        target: SettledLivedExperienceOccurrence,
    ) -> OrderedLivedExperienceRelation:
        provisional = OrderedLivedExperienceRelation(
            chronology_authority_receipt_sha256=(
                self._chronology_authority_receipt_sha256
            ),
            chronology_sequence=chronology_sequence,
            predecessor_relation_receipt_sha256=(
                predecessor_relation_receipt_sha256
            ),
            source_occurrence_receipt_sha256=(
                source.authority_receipt_sha256
            ),
            target_occurrence_receipt_sha256=(
                target.authority_receipt_sha256
            ),
            source_thing_id=source.thing_id,
            target_thing_id=target.thing_id,
            same_thing=source.thing_id == target.thing_id,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._relation_key,
            _RELATION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = OrderedLivedExperienceRelation(
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
        self._verify_relation(result)
        return result

    def _verify_relation(
        self,
        value: OrderedLivedExperienceRelation,
        occurrences: tuple[
            SettledLivedExperienceOccurrence, ...
        ] | None = None,
    ) -> None:
        if not isinstance(value, OrderedLivedExperienceRelation):
            raise TypeError("ordered lived-experience relation is not typed")
        for digest, label in (
            (
                value.chronology_authority_receipt_sha256,
                "ordered lived chronology",
            ),
            (
                value.source_occurrence_receipt_sha256,
                "ordered lived source occurrence",
            ),
            (
                value.target_occurrence_receipt_sha256,
                "ordered lived target occurrence",
            ),
            (value.source_thing_id, "ordered lived source THING"),
            (value.target_thing_id, "ordered lived target THING"),
            (value.authority_hmac_sha256, "ordered lived relation HMAC"),
            (
                value.authority_receipt_sha256,
                "ordered lived relation authority",
            ),
        ):
            _sha(digest, label)
        if value.predecessor_relation_receipt_sha256 is not None:
            _sha(
                value.predecessor_relation_receipt_sha256,
                "ordered lived predecessor relation",
            )
        if (
            value.chronology_authority_receipt_sha256
            != self._chronology_authority_receipt_sha256
            or isinstance(value.chronology_sequence, bool)
            or not isinstance(value.chronology_sequence, int)
            or value.chronology_sequence <= 0
            or value.source_occurrence_receipt_sha256
            == value.target_occurrence_receipt_sha256
            or value.same_thing
            != (value.source_thing_id == value.target_thing_id)
        ):
            raise ValueError(
                "ordered lived-experience relation shape changed"
            )
        expected = hmac.new(
            self._relation_key,
            _RELATION_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, value.authority_hmac_sha256)
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError(
                "ordered lived-experience relation authority changed"
            )
        if occurrences is not None:
            by_receipt = {
                item.authority_receipt_sha256: item
                for item in occurrences
            }
            source = by_receipt.get(
                value.source_occurrence_receipt_sha256
            )
            target = by_receipt.get(
                value.target_occurrence_receipt_sha256
            )
            if (
                source is None
                or target is None
                or source.thing_id != value.source_thing_id
                or target.thing_id != value.target_thing_id
                or target.source_time_start < source.source_time_end
            ):
                raise ValueError(
                    "ordered lived relation left occurrence custody"
                )

    def _verify_graph(
        self,
        occurrences: tuple[SettledLivedExperienceOccurrence, ...],
        relations: tuple[OrderedLivedExperienceRelation, ...],
    ) -> None:
        if (
            len(occurrences) > self._profile.max_occurrences
            or len(relations) > self._profile.max_relations
            or len({
                value.authority_receipt_sha256 for value in occurrences
            }) != len(occurrences)
            or len({
                value.authority_receipt_sha256 for value in relations
            }) != len(relations)
        ):
            raise RuntimeError(
                "ordered lived-experience capacity exhausted"
            )
        for occurrence in occurrences:
            self._evidence.verify(occurrence)
            self._require_source_custody(occurrence)
            if (
                len(occurrence.full_field_roots)
                > self._profile.max_roots_per_occurrence
            ):
                raise RuntimeError(
                    "ordered lived-experience root capacity exhausted"
                )
        for relation in relations:
            self._verify_relation(relation, occurrences)
        if tuple(
            value.chronology_sequence for value in relations
        ) != tuple(range(1, len(relations) + 1)):
            raise ValueError(
                "ordered lived chronology sequence changed"
            )
        if (
            (not relations and len(occurrences) > 1)
            or (
                relations
                and len(occurrences) != len(relations) + 1
            )
        ):
            raise ValueError(
                "ordered lived chronology occurrence extent changed"
            )
        for index, relation in enumerate(relations):
            prior = None if index == 0 else relations[index - 1]
            if (
                relation.predecessor_relation_receipt_sha256
                != (
                    None
                    if prior is None
                    else prior.authority_receipt_sha256
                )
                or (
                    prior is not None
                    and relation.source_occurrence_receipt_sha256
                    != prior.target_occurrence_receipt_sha256
                )
                or relation.source_occurrence_receipt_sha256
                != occurrences[index].authority_receipt_sha256
                or relation.target_occurrence_receipt_sha256
                != occurrences[index + 1].authority_receipt_sha256
            ):
                raise ValueError(
                    "ordered lived chronology continuity changed"
                )

    def _seal_prepared(
        self,
        *,
        state: str,
        relation: OrderedLivedExperienceRelation | None,
        prior_occurrences: tuple[
            SettledLivedExperienceOccurrence, ...
        ],
        prior_relations: tuple[OrderedLivedExperienceRelation, ...],
        staged_occurrences: tuple[
            SettledLivedExperienceOccurrence, ...
        ],
        staged_relations: tuple[OrderedLivedExperienceRelation, ...],
    ) -> PreparedOrderedLivedExperience:
        provisional = PreparedOrderedLivedExperience(
            state=state,
            relation=relation,
            prior_occurrences=prior_occurrences,
            prior_relations=prior_relations,
            staged_occurrences=staged_occurrences,
            staged_relations=staged_relations,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            _state=_PreparedState(),
            _owner_authority=self._owner_authority,
        )
        signature = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return PreparedOrderedLivedExperience(
            state=provisional.state,
            relation=provisional.relation,
            prior_occurrences=provisional.prior_occurrences,
            prior_relations=provisional.prior_relations,
            staged_occurrences=provisional.staged_occurrences,
            staged_relations=provisional.staged_relations,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            _state=provisional._state,
            _owner_authority=self._owner_authority,
        )

    def prepare(
        self,
        *,
        occurrence: SettledLivedExperienceOccurrence,
    ) -> PreparedOrderedLivedExperience:
        """Stage one occurrence and derive adjacency from the owned head."""

        self._evidence.verify(occurrence)
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "ordered lived-experience mutation is already prepared"
                )
            retained = tuple(
                value
                for value in self._occurrences
                if value.authority_receipt_sha256
                == occurrence.authority_receipt_sha256
            )
            if retained:
                if len(retained) != 1 or retained[0] != occurrence:
                    raise ValueError(
                        "ordered lived occurrence conflicts with retained "
                        "custody"
                    )
                prepared = self._seal_prepared(
                    state="quiescent",
                    relation=None,
                    prior_occurrences=self._occurrences,
                    prior_relations=self._relations,
                    staged_occurrences=self._occurrences,
                    staged_relations=self._relations,
                )
                self._prepared = prepared
                return prepared
            source = (
                None if not self._occurrences else self._occurrences[-1]
            )
            if (
                source is not None
                and occurrence.source_time_start < source.source_time_end
            ):
                raise ValueError(
                    "ordered lived target begins before its source closes"
                )
            relation = (
                None
                if source is None
                else self._seal_relation(
                    chronology_sequence=len(self._relations) + 1,
                    predecessor_relation_receipt_sha256=(
                        None
                        if not self._relations
                        else self._relations[-1].authority_receipt_sha256
                    ),
                    source=source,
                    target=occurrence,
                )
            )
            staged_occurrences = self._occurrences + (occurrence,)
            staged_relations = (
                self._relations
                if relation is None
                else self._relations + (relation,)
            )
            self._verify_graph(staged_occurrences, staged_relations)
            self._encoded(staged_occurrences, staged_relations)
            prepared = self._seal_prepared(
                state="perturbed",
                relation=relation,
                prior_occurrences=self._occurrences,
                prior_relations=self._relations,
                staged_occurrences=staged_occurrences,
                staged_relations=staged_relations,
            )
            self._prepared = prepared
            return prepared

    def _require_prepared(
        self,
        prepared: PreparedOrderedLivedExperience,
    ) -> PreparedOrderedLivedExperience:
        if (
            not isinstance(prepared, PreparedOrderedLivedExperience)
            or prepared is not self._prepared
            or prepared._owner_authority is not self._owner_authority
            or prepared._state.phase != "prepared"
            or prepared.state not in {"perturbed", "quiescent"}
            or prepared.prior_occurrences != self._occurrences
            or prepared.prior_relations != self._relations
        ):
            raise ValueError(
                "prepared ordered lived-experience mutation changed"
            )
        expected = hmac.new(
            self._prepared_key,
            _PREPARED_DOMAIN + _canonical(prepared.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                prepared.authority_hmac_sha256,
            )
            or prepared.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": prepared.payload(),
            })
        ):
            raise ValueError(
                "prepared ordered lived-experience authority changed"
            )
        if prepared.state == "quiescent":
            if (
                prepared.relation is not None
                or prepared.staged_occurrences
                != prepared.prior_occurrences
                or prepared.staged_relations != prepared.prior_relations
            ):
                raise ValueError(
                    "quiescent ordered lived preparation changed state"
                )
        elif (
            len(prepared.staged_occurrences)
            != len(prepared.prior_occurrences) + 1
            or prepared.staged_occurrences[:-1]
            != prepared.prior_occurrences
            or (
                prepared.relation is None
                and prepared.staged_relations
                != prepared.prior_relations
            )
            or (
                prepared.relation is not None
                and (
                    len(prepared.staged_relations)
                    != len(prepared.prior_relations) + 1
                    or prepared.staged_relations[:-1]
                    != prepared.prior_relations
                    or prepared.staged_relations[-1]
                    != prepared.relation
                )
            )
        ):
            raise ValueError(
                "perturbed ordered lived preparation changed mutation"
            )
        return prepared

    def commit(
        self,
        prepared: PreparedOrderedLivedExperience,
    ) -> OrderedLivedExperienceUndo:
        with self._lock:
            current = self._require_prepared(prepared)
            committed_body = self._state_body(
                current.staged_occurrences,
                current.staged_relations,
            )
            committed_encoded = self._encoded(
                current.staged_occurrences,
                current.staged_relations,
            )
            self._occurrences = current.staged_occurrences
            self._relations = current.staged_relations
            self._committed_state_receipt_sha256 = _digest(
                committed_body
            )
            self._committed_encoded = committed_encoded
            current._state.phase = "committed"
            self._prepared = None
            return OrderedLivedExperienceUndo(
                prepared=current,
                _owner_authority=self._owner_authority,
            )

    def rollback(self, undo: OrderedLivedExperienceUndo) -> None:
        with self._lock:
            if (
                not isinstance(undo, OrderedLivedExperienceUndo)
                or undo._owner_authority is not self._owner_authority
                or undo.prepared._state.phase != "committed"
                or self._occurrences
                != undo.prepared.staged_occurrences
                or self._relations != undo.prepared.staged_relations
            ):
                raise ValueError(
                    "ordered lived-experience rollback authority changed"
                )
            prior_body = self._state_body(
                undo.prepared.prior_occurrences,
                undo.prepared.prior_relations,
            )
            prior_encoded = self._encoded(
                undo.prepared.prior_occurrences,
                undo.prepared.prior_relations,
            )
            self._occurrences = undo.prepared.prior_occurrences
            self._relations = undo.prepared.prior_relations
            self._committed_state_receipt_sha256 = _digest(prior_body)
            self._committed_encoded = prior_encoded
            undo.prepared._state.phase = "rolled_back"

    def discard(
        self,
        prepared: PreparedOrderedLivedExperience,
    ) -> None:
        with self._lock:
            current = self._require_prepared(prepared)
            current._state.phase = "discarded"
            self._prepared = None

    def _state_body(
        self,
        occurrences: tuple[SettledLivedExperienceOccurrence, ...],
        relations: tuple[OrderedLivedExperienceRelation, ...],
    ) -> dict[str, object]:
        return {
            "occurrences": [
                value.custody_record() for value in occurrences
            ],
            "profile": self._profile.record(),
            "relations": [value.record() for value in relations],
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        occurrences: tuple[SettledLivedExperienceOccurrence, ...],
        relations: tuple[OrderedLivedExperienceRelation, ...],
    ) -> bytes:
        body = self._state_body(occurrences, relations)
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
                "ordered lived-experience state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "ordered lived-experience snapshot crossed preparation"
                )
            current_body = self._state_body(
                self._occurrences,
                self._relations,
            )
            if (
                _digest(current_body)
                != self._committed_state_receipt_sha256
            ):
                self._verify_graph(self._occurrences, self._relations)
                raise ValueError(
                    "ordered lived-experience committed state changed"
                )
            return self._committed_encoded

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: OrderedLivedExperienceProfile,
        evidence_authority: SettledLivedExperienceAuthority,
        source_custody: OrderedLivedExperienceSourceCustody | None = None,
        encoded: bytes,
    ) -> "OrganismOrderedLivedExperienceOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError(
                "ordered lived-experience cold state is absent"
            )
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            evidence_authority=evidence_authority,
            source_custody=source_custody,
        )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "ordered lived-experience cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
        ):
            raise ValueError(
                "ordered lived-experience cold envelope changed"
            )
        body = envelope["body"]
        expected_state = hmac.new(
            owner._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_state,
            envelope.get("state_hmac_sha256", ""),
        ):
            raise ValueError(
                "ordered lived-experience cold authority changed"
            )
        if (
            set(body) != {"occurrences", "profile", "relations", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != profile.record()
            or not isinstance(body.get("occurrences"), list)
            or not isinstance(body.get("relations"), list)
        ):
            raise ValueError(
                "ordered lived-experience cold body changed"
            )
        occurrences = tuple(
            owner._occurrence_from_record(value)
            for value in body["occurrences"]
        )
        relations = tuple(
            owner._relation_from_record(value)
            for value in body["relations"]
        )
        owner._verify_graph(occurrences, relations)
        canonical_encoded = owner._encoded(occurrences, relations)
        if canonical_encoded != encoded:
            raise ValueError(
                "ordered lived-experience cold encoding changed"
            )
        owner._occurrences = occurrences
        owner._relations = relations
        owner._committed_state_receipt_sha256 = _digest(
            owner._state_body(occurrences, relations)
        )
        owner._committed_encoded = encoded
        return owner

    def _occurrence_from_record(
        self,
        value: object,
    ) -> SettledLivedExperienceOccurrence:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "causal_story_receipt_sha256",
            "entity_continuity_hmac_sha256",
            "episode_phase",
            "episode_receipt_sha256",
            "full_field_root_count",
            "full_field_roots_receipt_sha256",
            "learning_kind",
            "learning_receipt_sha256",
            "mosaic_receipt_sha256",
            "schema",
            "settlement_receipt_sha256",
            "settlement_structural_fingerprint",
            "source_occurrence_id",
            "source_time_end",
            "source_time_start",
            "story_chain_receipt_sha256",
            "terminal_partition_receipt_sha256",
            "thing_id",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != OCCURRENCE_SCHEMA
        ):
            raise ValueError(
                "cold settled lived occurrence changed"
            )
        if self._source_custody is None:
            raise ValueError(
                "cold settled lived occurrence lacks source custody"
            )
        episode = self._source_custody.episode(
            value["episode_receipt_sha256"]
        )
        roots = episode.full_field_roots
        if (
            isinstance(value["full_field_root_count"], bool)
            or not isinstance(value["full_field_root_count"], int)
            or value["full_field_root_count"] != len(roots)
            or value["full_field_roots_receipt_sha256"]
            != _roots_receipt(roots)
        ):
            raise ValueError(
                "cold settled lived full-field custody changed"
            )
        occurrence = SettledLivedExperienceOccurrence(
            learning_kind=value["learning_kind"],
            thing_id=value["thing_id"],
            mosaic_receipt_sha256=value["mosaic_receipt_sha256"],
            terminal_partition_receipt_sha256=(
                value["terminal_partition_receipt_sha256"]
            ),
            learning_receipt_sha256=value["learning_receipt_sha256"],
            episode_receipt_sha256=value["episode_receipt_sha256"],
            episode_phase=value["episode_phase"],
            settlement_receipt_sha256=value["settlement_receipt_sha256"],
            settlement_structural_fingerprint=(
                value["settlement_structural_fingerprint"]
            ),
            source_occurrence_id=value["source_occurrence_id"],
            causal_story_receipt_sha256=(
                value["causal_story_receipt_sha256"]
            ),
            story_chain_receipt_sha256=(
                value["story_chain_receipt_sha256"]
            ),
            entity_continuity_hmac_sha256=(
                value["entity_continuity_hmac_sha256"]
            ),
            source_time_start=_fraction_from_text(
                value["source_time_start"],
                "cold settled lived source start",
            ),
            source_time_end=_fraction_from_text(
                value["source_time_end"],
                "cold settled lived source end",
            ),
            full_field_roots=roots,
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )
        self._evidence.verify(occurrence)
        return occurrence

    def _relation_from_record(
        self,
        value: object,
    ) -> OrderedLivedExperienceRelation:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "chronology_authority_receipt_sha256",
            "chronology_sequence",
            "predecessor_relation_receipt_sha256",
            "same_thing",
            "schema",
            "source_occurrence_receipt_sha256",
            "source_thing_id",
            "target_occurrence_receipt_sha256",
            "target_thing_id",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != RELATION_SCHEMA
        ):
            raise ValueError(
                "cold ordered lived relation changed"
            )
        relation = OrderedLivedExperienceRelation(
            chronology_authority_receipt_sha256=(
                value["chronology_authority_receipt_sha256"]
            ),
            chronology_sequence=value["chronology_sequence"],
            predecessor_relation_receipt_sha256=(
                value["predecessor_relation_receipt_sha256"]
            ),
            source_occurrence_receipt_sha256=(
                value["source_occurrence_receipt_sha256"]
            ),
            target_occurrence_receipt_sha256=(
                value["target_occurrence_receipt_sha256"]
            ),
            source_thing_id=value["source_thing_id"],
            target_thing_id=value["target_thing_id"],
            same_thing=value["same_thing"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )
        self._verify_relation(relation)
        return relation

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded(
                self._occurrences,
                self._relations,
            )
            return {
                "chronology": "organism_owned",
                "chronology_authority_receipt_sha256": (
                    self._chronology_authority_receipt_sha256
                ),
                "cross_thing_relations": sum(
                    not value.same_thing for value in self._relations
                ),
                "full_field": True,
                "mechanism_state": (
                    "perturbed" if self._relations else "quiescent"
                ),
                "occurrences": len(self._occurrences),
                "reduced_approximation": False,
                "relations": len(self._relations),
                "retained_roots": sum(
                    len(value.full_field_roots)
                    for value in self._occurrences
                ),
                "same_thing_relations": sum(
                    value.same_thing for value in self._relations
                ),
                "schema": STATUS_SCHEMA,
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._profile.max_state_bytes,
            }


__all__ = [
    "OrderedLivedExperienceProfile",
    "OrderedLivedExperienceRelation",
    "OrderedLivedExperienceSourceCustody",
    "OrderedLivedExperienceUndo",
    "OrganismOrderedLivedExperienceOwner",
    "PreparedOrderedLivedExperience",
    "SettledLivedExperienceAuthority",
    "SettledLivedExperienceOccurrence",
]
