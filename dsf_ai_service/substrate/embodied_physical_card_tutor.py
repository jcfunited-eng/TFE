"""Label-free conductor for repeated physical card tutoring experiences.

An external tutor chooses a physical card and supplies its exact material
geometry plus real recorded tutor pressure.  This conductor supplies no card
name, pronunciation, meaning, transcript, roster, sensory profile, or chat
content.  It serializes occurrences through the existing durable embodied
reading transaction and proves that the retained occurrence still owns the
exact full-field roots and one contribution from every mounted mechanism.

The conductor owns no card or room persistence.  Repetition is a sequence of
ordinary lived occurrences in the existing organism stores, not a parallel
curriculum state or an A-Z/0-9 lookup table.  L0-L4 remains upstream,
explicit, and unchanged.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Mapping, Protocol, runtime_checkable

from dsf_ai_service.substrate.causal_thing_mosaic import (
    FullFieldSensoryRoot,
)
from dsf_ai_service.substrate.embodied_glyph_tutoring import (
    AuthenticatedTutorAcousticActuator,
    GlyphBearingW1MaterialAuthority,
    GlyphMaterialPresentation,
    TutorAcousticActuation,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveThingLearningRecord,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    WholeOrganismEpisodeRecord,
)


RECEIPT_SCHEMA = "guala.embodied_physical_card_tutor.receipt.v1"
NEUTRAL_DISPLAY_PROVENANCE = "physical card occurrence"
_HEX = frozenset("0123456789abcdef")


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


def _root_receipt(root: FullFieldSensoryRoot) -> str:
    if not isinstance(root, FullFieldSensoryRoot):
        raise TypeError("physical card full-field root is not typed")
    root.verify()
    return _digest(root.record())


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(f"{name} changed")
    return value


@runtime_checkable
class EmbodiedPhysicalCardRuntime(Protocol):
    """Existing durable runtime surface used by the conductor."""

    _whole_organism_episode_authority: object
    _passive_whole_organism_thing_learning: object

    def durably_experience_embodied_reading_lesson(
        self,
        *,
        context_id: str,
        tutor_designation: str,
        presentation_authority: GlyphBearingW1MaterialAuthority,
        presentation: GlyphMaterialPresentation,
        acoustic_authority: AuthenticatedTutorAcousticActuator,
        acoustic_actuation: TutorAcousticActuation,
        wav_bytes: bytes,
        state_dir: str,
    ) -> Mapping[str, object]:
        ...


@dataclass(frozen=True, slots=True)
class EmbodiedPhysicalCardExperienceReceipt:
    """Receipt-only proof for one label-free physical card occurrence."""

    sequence: int
    boundary_authority_receipt_sha256: str
    settlement_authority_receipt_sha256: str
    whole_organism_episode_authority_receipt_sha256: str
    passive_learning_authority_receipt_sha256: str
    thing_id: str
    full_field_root_receipt_sha256s: tuple[str, ...]
    mechanism_contribution_receipt_sha256s: tuple[str, ...]
    supplied_identity_state: str = "unresolved"
    external_identity_authority: bool = False
    external_meaning_authority: bool = False
    external_pronunciation_authority: bool = False
    external_recognition_authority: bool = False
    retained_pcm_bytes: int = 0
    schema: str = RECEIPT_SCHEMA

    def verify(self) -> None:
        _positive(self.sequence, "physical card experience sequence")
        for value, name in (
            (
                self.boundary_authority_receipt_sha256,
                "physical card boundary",
            ),
            (
                self.settlement_authority_receipt_sha256,
                "physical card settlement",
            ),
            (
                self.whole_organism_episode_authority_receipt_sha256,
                "physical card whole-organism episode",
            ),
            (
                self.passive_learning_authority_receipt_sha256,
                "physical card passive learning",
            ),
            (self.thing_id, "physical card causal THING"),
        ):
            _sha(value, name)
        if (
            not self.full_field_root_receipt_sha256s
            or not self.mechanism_contribution_receipt_sha256s
        ):
            raise ValueError(
                "physical card experience lost field or organism custody"
            )
        for value in self.full_field_root_receipt_sha256s:
            _sha(value, "physical card full-field root")
        for value in self.mechanism_contribution_receipt_sha256s:
            _sha(value, "physical card mechanism contribution")
        if (
            self.supplied_identity_state != "unresolved"
            or self.external_identity_authority
            or self.external_meaning_authority
            or self.external_pronunciation_authority
            or self.external_recognition_authority
            or self.retained_pcm_bytes != 0
            or self.schema != RECEIPT_SCHEMA
        ):
            raise ValueError(
                "physical card experience gained external semantic authority"
            )


class EmbodiedPhysicalCardTutor:
    """Serialize repeatable physical card occurrences through Guala."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    @staticmethod
    def _claims_are_empty(value: object) -> bool:
        return (
            isinstance(value, Mapping)
            and bool(value)
            and all(claim is False for claim in value.values())
        )

    @staticmethod
    def _matching_episode(
        runtime: EmbodiedPhysicalCardRuntime,
        settlement_receipt: str,
    ) -> WholeOrganismEpisodeRecord:
        authority = runtime._whole_organism_episode_authority
        matches = tuple(
            value
            for value in authority.episodes
            if value.settlement_authority_receipt_sha256
            == settlement_receipt
        )
        if len(matches) != 1:
            raise RuntimeError(
                "physical card occurrence lacks one whole-organism episode"
            )
        episode = matches[0]
        if (
            tuple(
                value.mechanism_id
                for value in authority.manifest.mechanisms
            )
            != tuple(
                value.mechanism_id for value in episode.contributions
            )
            or not episode.contributions
        ):
            raise RuntimeError(
                "physical card occurrence lost mounted mechanisms"
            )
        return episode

    @staticmethod
    def _matching_passive_record(
        runtime: EmbodiedPhysicalCardRuntime,
        settlement_receipt: str,
    ) -> PassiveThingLearningRecord:
        matches = tuple(
            value
            for value
            in runtime._passive_whole_organism_thing_learning.records
            if value.story.settlement_authority_receipt_sha256
            == settlement_receipt
        )
        if len(matches) != 1:
            raise RuntimeError(
                "physical card occurrence lacks one passive learned record"
            )
        return matches[0]

    def conduct_experience(
        self,
        *,
        runtime: EmbodiedPhysicalCardRuntime,
        context_id: str,
        presentation_authority: GlyphBearingW1MaterialAuthority,
        presentation: GlyphMaterialPresentation,
        acoustic_authority: AuthenticatedTutorAcousticActuator,
        acoustic_actuation: TutorAcousticActuation,
        wav_bytes: bytes,
        state_dir: str,
    ) -> EmbodiedPhysicalCardExperienceReceipt:
        """Conduct and durably retain one card geometry plus real tutor WAV."""

        if not isinstance(runtime, EmbodiedPhysicalCardRuntime):
            raise TypeError(
                "physical card tutoring requires the durable embodied runtime"
            )
        with self._lock:
            result = runtime.durably_experience_embodied_reading_lesson(
                context_id=context_id,
                tutor_designation=NEUTRAL_DISPLAY_PROVENANCE,
                presentation_authority=presentation_authority,
                presentation=presentation,
                acoustic_authority=acoustic_authority,
                acoustic_actuation=acoustic_actuation,
                wav_bytes=wav_bytes,
                state_dir=state_dir,
            )
            if (
                not isinstance(result, Mapping)
                or result.get("retained_pcm_bytes") != 0
                or not isinstance(result.get("boundary"), Mapping)
                or not isinstance(result.get("lesson"), Mapping)
            ):
                raise RuntimeError(
                    "physical card durable transaction changed its receipt"
                )
            boundary = result["boundary"]
            lesson = result["lesson"]
            latest_boundary = boundary.get("latest_boundary")
            latest_lesson = lesson.get("latest_lesson")
            if (
                not self._claims_are_empty(boundary.get("claims"))
                or not self._claims_are_empty(lesson.get("claims"))
                or not isinstance(latest_boundary, Mapping)
                or not isinstance(latest_lesson, Mapping)
                or latest_boundary.get("tutor_designation")
                != NEUTRAL_DISPLAY_PROVENANCE
                or latest_lesson.get("tutor_designation")
                != NEUTRAL_DISPLAY_PROVENANCE
                or latest_lesson.get("tutor_designation_authority")
                != "display_only"
                or boundary.get("retained_pcm_bytes") != 0
                or lesson.get("retained_pcm_bytes") != 0
            ):
                raise RuntimeError(
                    "physical card occurrence gained semantic authority"
                )
            settlement_receipt = _sha(
                latest_boundary.get(
                    "settlement_authority_receipt_sha256"
                ),
                "physical card settlement",
            )
            episode = self._matching_episode(
                runtime,
                settlement_receipt,
            )
            passive = self._matching_passive_record(
                runtime,
                settlement_receipt,
            )
            passive_roots = tuple(
                _root_receipt(value)
                for value in passive.full_field_roots
            )
            episode_roots = tuple(
                _root_receipt(value)
                for value in episode.full_field_roots
            )
            if (
                passive.thing_id != latest_boundary.get("thing_id")
                or passive.thing_id != latest_lesson.get("thing_id")
                or passive_roots != episode_roots
            ):
                raise RuntimeError(
                    "physical card occurrence crossed learned field custody"
                )
            receipt = EmbodiedPhysicalCardExperienceReceipt(
                sequence=_positive(
                    latest_boundary.get("sequence"),
                    "physical card experience sequence",
                ),
                boundary_authority_receipt_sha256=_sha(
                    result.get(
                        "boundary_record_authority_receipt_sha256"
                    ),
                    "physical card boundary",
                ),
                settlement_authority_receipt_sha256=(
                    settlement_receipt
                ),
                whole_organism_episode_authority_receipt_sha256=(
                    episode.authority_receipt_sha256
                ),
                passive_learning_authority_receipt_sha256=(
                    passive.authority_receipt_sha256
                ),
                thing_id=passive.thing_id,
                full_field_root_receipt_sha256s=passive_roots,
                mechanism_contribution_receipt_sha256s=tuple(
                    value.authority_receipt_sha256
                    for value in episode.contributions
                ),
            )
            receipt.verify()
            return receipt


__all__ = (
    "EmbodiedPhysicalCardExperienceReceipt",
    "EmbodiedPhysicalCardRuntime",
    "EmbodiedPhysicalCardTutor",
    "NEUTRAL_DISPLAY_PROVENANCE",
    "RECEIPT_SCHEMA",
)
