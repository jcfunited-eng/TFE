"""Experience-grown ordered grounded turn-to-vocal-motor constructions.

This owner learns no text and contains no scripted replies.  A prompt cue is
the ordered/simultaneous structure of causally grounded referents released by
the auditory motif grounding owner.  A response is an authenticated,
physically self-heard PCM motor exemplar.

Two independent lived turn episodes are required.  Exact recurrence of one
cue structure and one response motor settles a construction.  Any different
response assembly or motor for the same cue makes the construction explicitly
ambiguous; there is no vote, score, frequency preference, or fallback.
Persistence is bounded, canonical, authenticated, and never silently evicts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    AuditoryMotifCausalGroundingOwner,
    GroundingResolution,
    GroundingResolutionState,
    GroundingRoot,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalHearingReceipt,
    SelfVocalPCMExemplar,
    SelfVocalPCMMotorOwner,
)


TURN_PROFILE_SCHEMA = "guala.grounded_turn.profile.v1"
TURN_EPISODE_SCHEMA = "guala.grounded_turn.episode.v1"
TURN_CONSTRUCTION_SCHEMA = "guala.grounded_turn.construction.v1"
TURN_STATE_SCHEMA = "guala.grounded_turn.state.v1"
TURN_ENVELOPE_SCHEMA = "guala.grounded_turn.state_hmac.v1"

_EPISODE_DOMAIN = b"guala-grounded-turn-episode-v1\0"
_CONSTRUCTION_DOMAIN = b"guala-grounded-turn-construction-v1\0"
_STATE_DOMAIN = b"guala-grounded-turn-state-v1\0"
_HEX = frozenset("0123456789abcdef")
_REQUIRED_INDEPENDENT_TURNS = 2


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
    elif isinstance(value, bytes):
        result = value
    else:
        raise TypeError("grounded turn key must be bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError("grounded turn key has an invalid boundary")
    return result


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(key, domain + _canonical(value), hashlib.sha256).hexdigest()


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("grounded turn time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not an exact fraction") from exc
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class GroundedTurnResourceProfile:
    profile_id: str
    max_episodes: int
    max_constructions: int
    max_elements_per_cue: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_episodes: int,
        max_constructions: int,
        max_elements_per_cue: int,
        max_state_bytes: int,
    ) -> "GroundedTurnResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("grounded turn profile identifier changed")
        provisional = cls(
            profile_id=profile_id,
            max_episodes=_positive(max_episodes, "turn episode capacity"),
            max_constructions=_positive(
                max_constructions, "turn construction capacity"
            ),
            max_elements_per_cue=_positive(
                max_elements_per_cue, "turn cue element capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "turn state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_episodes=provisional.max_episodes,
            max_constructions=provisional.max_constructions,
            max_elements_per_cue=provisional.max_elements_per_cue,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_constructions": self.max_constructions,
            "max_elements_per_cue": self.max_elements_per_cue,
            "max_episodes": self.max_episodes,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": TURN_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _positive(self.max_episodes, "turn episode capacity")
        _positive(self.max_constructions, "turn construction capacity")
        _positive(self.max_elements_per_cue, "turn cue element capacity")
        _positive(self.max_state_bytes, "turn state capacity")
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("grounded turn profile authority changed")


@dataclass(frozen=True, slots=True)
class GroundedCueElement:
    ordinal: int
    temporal_relation: str
    root: GroundingRoot
    source_time_start: Fraction
    source_time_end: Fraction
    contributing_motif_neuron_ids: tuple[str, ...]

    def structural_record(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "physical_referent_sha256": self.root.value_sha256,
            "referent_root_id": self.root.root_id,
            "temporal_relation": self.temporal_relation,
        }

    def as_record(self) -> dict[str, object]:
        return {
            "contributing_motif_neuron_ids": list(
                self.contributing_motif_neuron_ids
            ),
            "ordinal": self.ordinal,
            "root": self.root.as_record(),
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "temporal_relation": self.temporal_relation,
        }

    def verify(self) -> None:
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or self.ordinal < 0
            or self.temporal_relation
            not in {"first", "after", "overlapping"}
            or not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or not self.contributing_motif_neuron_ids
            or tuple(sorted(set(self.contributing_motif_neuron_ids)))
            != self.contributing_motif_neuron_ids
        ):
            raise ValueError("grounded cue element changed")
        self.root.verify()
        for value in self.contributing_motif_neuron_ids:
            _sha256(value, "grounded cue motif")


@dataclass(frozen=True, slots=True)
class GroundedTurnCue:
    cue_id: str
    structure_id: str
    elements: tuple[GroundedCueElement, ...]

    def verify(self, max_elements: int) -> None:
        _sha256(self.cue_id, "grounded turn cue")
        _sha256(self.structure_id, "grounded turn cue structure")
        if (
            not self.elements
            or len(self.elements) > max_elements
            or tuple(value.ordinal for value in self.elements)
            != tuple(range(len(self.elements)))
        ):
            raise ValueError("grounded turn cue crossed its boundary")
        prior = None
        for value in self.elements:
            value.verify()
            expected = (
                "first"
                if prior is None
                else "after"
                if value.source_time_start >= prior.source_time_end
                else "overlapping"
            )
            if value.temporal_relation != expected:
                raise ValueError("grounded turn temporal relation changed")
            prior = value
        structure = {
            "elements": [
                value.structural_record() for value in self.elements
            ],
            "schema": "guala.grounded_turn.cue_structure.v1",
        }
        if (
            self.structure_id != _digest(structure)
            or self.cue_id != _digest({
                "elements": [value.as_record() for value in self.elements],
                "structure_id": self.structure_id,
            })
        ):
            raise ValueError("grounded turn cue authority changed")

    def as_record(self) -> dict[str, object]:
        return {
            "cue_id": self.cue_id,
            "elements": [value.as_record() for value in self.elements],
            "structure_id": self.structure_id,
        }


def cue_from_resolution(
    resolution: GroundingResolution,
    *,
    max_elements: int,
) -> GroundedTurnCue:
    if (
        not isinstance(resolution, GroundingResolution)
        or resolution.state is not GroundingResolutionState.RESOLVED
        or not resolution.referents
    ):
        raise ValueError("grounded turn requires resolved causal referents")
    staged = []
    for referent in resolution.referents:
        if not referent.contributing_activations:
            raise ValueError(
                "grounded turn referent lacks exact activation interval"
            )
        staged.append((
            min(
                value.source_time_start
                for value in referent.contributing_activations
            ),
            max(
                value.source_time_end
                for value in referent.contributing_activations
            ),
            referent,
        ))
    staged.sort(key=lambda value: (
        value[0],
        value[1],
        value[2].root.root_id,
        value[2].root.value_sha256,
    ))
    elements = []
    prior_end = None
    for ordinal, (start, end, referent) in enumerate(staged):
        relation = (
            "first"
            if prior_end is None
            else "after"
            if start >= prior_end
            else "overlapping"
        )
        elements.append(GroundedCueElement(
            ordinal=ordinal,
            temporal_relation=relation,
            root=referent.root,
            source_time_start=start,
            source_time_end=end,
            contributing_motif_neuron_ids=(
                referent.contributing_motif_neuron_ids
            ),
        ))
        prior_end = end
    if len(elements) > max_elements:
        raise GroundedTurnCapacityError(
            "grounded turn cue element capacity exhausted"
        )
    structure = {
        "elements": [value.structural_record() for value in elements],
        "schema": "guala.grounded_turn.cue_structure.v1",
    }
    structure_id = _digest(structure)
    cue = GroundedTurnCue(
        cue_id=_digest({
            "elements": [value.as_record() for value in elements],
            "structure_id": structure_id,
        }),
        structure_id=structure_id,
        elements=tuple(elements),
    )
    cue.verify(max_elements)
    return cue


def cue_from_record(
    value: object,
    *,
    max_elements: int,
) -> GroundedTurnCue:
    """Restore one canonical cue without conversation-owner state."""

    return GroundedTurnConversationOwner._cue_from_record(
        value,
        max_elements=max_elements,
    )


@dataclass(frozen=True, slots=True)
class GroundedTurnEpisode:
    episode_id: str
    cue: GroundedTurnCue
    prompt_settlement_receipt_sha256: str
    outcome_settlement_receipt_sha256: str
    motor_id: str
    response_firing_motif_neuron_ids: tuple[str, ...]
    self_hearing_receipt_sha256: str
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "cue": self.cue.as_record(),
            "motor_id": self.motor_id,
            "outcome_settlement_receipt_sha256": (
                self.outcome_settlement_receipt_sha256
            ),
            "prompt_settlement_receipt_sha256": (
                self.prompt_settlement_receipt_sha256
            ),
            "response_firing_motif_neuron_ids": list(
                self.response_firing_motif_neuron_ids
            ),
            "schema": TURN_EPISODE_SCHEMA,
            "self_hearing_receipt_sha256": (
                self.self_hearing_receipt_sha256
            ),
        }

    def verify(self, key: bytes, max_elements: int) -> None:
        for value, name in (
            (self.episode_id, "grounded turn episode"),
            (
                self.prompt_settlement_receipt_sha256,
                "grounded turn prompt settlement",
            ),
            (
                self.outcome_settlement_receipt_sha256,
                "grounded turn outcome settlement",
            ),
            (self.motor_id, "grounded turn motor"),
            (
                self.self_hearing_receipt_sha256,
                "grounded turn self hearing",
            ),
        ):
            _sha256(value, name)
        self.cue.verify(max_elements)
        if (
            not self.response_firing_motif_neuron_ids
            or tuple(sorted(set(self.response_firing_motif_neuron_ids)))
            != self.response_firing_motif_neuron_ids
        ):
            raise ValueError("grounded turn response assembly changed")
        identity = _digest({
            "cue_id": self.cue.cue_id,
            "motor_id": self.motor_id,
            "outcome_settlement_receipt_sha256": (
                self.outcome_settlement_receipt_sha256
            ),
            "prompt_settlement_receipt_sha256": (
                self.prompt_settlement_receipt_sha256
            ),
            "self_hearing_receipt_sha256": (
                self.self_hearing_receipt_sha256
            ),
        })
        if (
            self.episode_id != identity
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(key, _EPISODE_DOMAIN, self.payload()),
            )
        ):
            raise ValueError("grounded turn episode authority changed")

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "episode_id": self.episode_id,
        }


class GroundedTurnConstructionState(str, Enum):
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class GroundedTurnConstruction:
    construction_id: str
    cue_structure_id: str
    state: GroundedTurnConstructionState
    motor_ids: tuple[str, ...]
    response_assembly_ids: tuple[str, ...]
    proof_episode_ids: tuple[str, ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "cue_structure_id": self.cue_structure_id,
            "motor_ids": list(self.motor_ids),
            "proof_episode_ids": list(self.proof_episode_ids),
            "response_assembly_ids": list(self.response_assembly_ids),
            "schema": TURN_CONSTRUCTION_SCHEMA,
            "state": self.state.value,
        }

    def verify(self, key: bytes) -> None:
        _sha256(self.construction_id, "grounded turn construction")
        _sha256(self.cue_structure_id, "grounded turn cue structure")
        if (
            tuple(sorted(set(self.motor_ids))) != self.motor_ids
            or not self.motor_ids
            or tuple(sorted(set(self.response_assembly_ids)))
            != self.response_assembly_ids
            or not self.response_assembly_ids
            or len(self.proof_episode_ids) < _REQUIRED_INDEPENDENT_TURNS
            or tuple(sorted(set(self.proof_episode_ids)))
            != self.proof_episode_ids
        ):
            raise ValueError("grounded turn construction changed")
        expected_state = (
            GroundedTurnConstructionState.UNIQUE
            if len(self.motor_ids) == 1
            and len(self.response_assembly_ids) == 1
            else GroundedTurnConstructionState.AMBIGUOUS
        )
        if (
            self.state is not expected_state
            or self.construction_id != _digest(self.payload())
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(key, _CONSTRUCTION_DOMAIN, self.payload()),
            )
        ):
            raise ValueError("grounded turn construction authority changed")


@dataclass(frozen=True, slots=True)
class GroundedReplyResolution:
    state: str
    reason: str
    cue_structure_id: str
    motor_id: str | None
    construction_id: str | None


class GroundedTurnConversationOwner:
    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: GroundedTurnResourceProfile,
    ) -> None:
        if not isinstance(resource_profile, GroundedTurnResourceProfile):
            raise TypeError("grounded turn owner requires a resource profile")
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._episode_key = hashlib.sha256(
            _EPISODE_DOMAIN + root
        ).digest()
        self._construction_key = hashlib.sha256(
            _CONSTRUCTION_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._episodes: dict[str, GroundedTurnEpisode] = {}
        self._constructions: dict[
            str, GroundedTurnConstruction
        ] = {}
        self._lock = threading.RLock()

    @property
    def episodes(self) -> tuple[GroundedTurnEpisode, ...]:
        with self._lock:
            return tuple(
                self._episodes[key] for key in sorted(self._episodes)
            )

    @property
    def constructions(self) -> tuple[GroundedTurnConstruction, ...]:
        with self._lock:
            return tuple(
                self._constructions[key]
                for key in sorted(self._constructions)
            )

    def admit_turn(
        self,
        *,
        prompt_resolution: GroundingResolution,
        prompt_settlement: CausalExperienceSettlement,
        response_exemplar: SelfVocalPCMExemplar,
        self_hearing: SelfVocalHearingReceipt,
        outcome_settlement: CausalExperienceSettlement,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> GroundedTurnEpisode:
        prompt_settlement.verify()
        outcome_settlement.verify()
        motor_owner.verify_exemplar(response_exemplar)
        motor_owner.verify_hearing(self_hearing)
        if (
            self_hearing.motor_id != response_exemplar.motor_id
            or self_hearing.firing_motif_neuron_ids
            != response_exemplar.firing_motif_neuron_ids
        ):
            raise ValueError("grounded turn response left self-heard motor")
        cue = cue_from_resolution(
            prompt_resolution,
            max_elements=self._profile.max_elements_per_cue,
        )
        if any(
            value.source_time_start < prompt_settlement.source_time_start
            or value.source_time_end > prompt_settlement.source_time_end
            for value in cue.elements
        ):
            raise ValueError(
                "grounded turn cue is outside prompt causal settlement"
            )
        identity = {
            "cue_id": cue.cue_id,
            "motor_id": response_exemplar.motor_id,
            "outcome_settlement_receipt_sha256": (
                outcome_settlement.authority_receipt_sha256
            ),
            "prompt_settlement_receipt_sha256": (
                prompt_settlement.authority_receipt_sha256
            ),
            "self_hearing_receipt_sha256": (
                self_hearing.authority_receipt_sha256
            ),
        }
        provisional = GroundedTurnEpisode(
            episode_id=_digest(identity),
            cue=cue,
            prompt_settlement_receipt_sha256=(
                prompt_settlement.authority_receipt_sha256
            ),
            outcome_settlement_receipt_sha256=(
                outcome_settlement.authority_receipt_sha256
            ),
            motor_id=response_exemplar.motor_id,
            response_firing_motif_neuron_ids=(
                self_hearing.firing_motif_neuron_ids
            ),
            self_hearing_receipt_sha256=(
                self_hearing.authority_receipt_sha256
            ),
            authority_hmac_sha256="",
        )
        episode = GroundedTurnEpisode(
            episode_id=provisional.episode_id,
            cue=provisional.cue,
            prompt_settlement_receipt_sha256=(
                provisional.prompt_settlement_receipt_sha256
            ),
            outcome_settlement_receipt_sha256=(
                provisional.outcome_settlement_receipt_sha256
            ),
            motor_id=provisional.motor_id,
            response_firing_motif_neuron_ids=(
                provisional.response_firing_motif_neuron_ids
            ),
            self_hearing_receipt_sha256=(
                provisional.self_hearing_receipt_sha256
            ),
            authority_hmac_sha256=_sign(
                self._episode_key,
                _EPISODE_DOMAIN,
                provisional.payload(),
            ),
        )
        episode.verify(
            self._episode_key,
            self._profile.max_elements_per_cue,
        )
        with self._lock:
            existing = self._episodes.get(episode.episode_id)
            if existing is not None:
                if existing != episode:
                    raise ValueError("grounded turn episode conflicted")
                return existing
            if len(self._episodes) >= self._profile.max_episodes:
                raise GroundedTurnCapacityError(
                    "grounded turn episode capacity exhausted"
                )
            staged = dict(self._episodes)
            staged[episode.episode_id] = episode
            self._encoded(staged, self._constructions)
            self._episodes = staged
        return episode

    def settle_construction(
        self,
        cue_structure_id: str,
    ) -> GroundedTurnConstruction | None:
        _sha256(cue_structure_id, "grounded turn cue structure")
        with self._lock:
            episodes = tuple(
                value for value in self._episodes.values()
                if value.cue.structure_id == cue_structure_id
            )
            if len(episodes) < _REQUIRED_INDEPENDENT_TURNS:
                return None
            if len({
                value.prompt_settlement_receipt_sha256
                for value in episodes
            }) < _REQUIRED_INDEPENDENT_TURNS or len({
                value.self_hearing_receipt_sha256
                for value in episodes
            }) < _REQUIRED_INDEPENDENT_TURNS:
                return None
            motor_ids = tuple(sorted({
                value.motor_id for value in episodes
            }))
            assemblies = tuple(sorted({
                _digest({
                    "firing_motif_neuron_ids": list(
                        value.response_firing_motif_neuron_ids
                    )
                })
                for value in episodes
            }))
            state = (
                GroundedTurnConstructionState.UNIQUE
                if len(motor_ids) == 1 and len(assemblies) == 1
                else GroundedTurnConstructionState.AMBIGUOUS
            )
            provisional = GroundedTurnConstruction(
                construction_id="0" * 64,
                cue_structure_id=cue_structure_id,
                state=state,
                motor_ids=motor_ids,
                response_assembly_ids=assemblies,
                proof_episode_ids=tuple(sorted(
                    value.episode_id for value in episodes
                )),
                authority_hmac_sha256="",
            )
            construction = GroundedTurnConstruction(
                construction_id=_digest(provisional.payload()),
                cue_structure_id=cue_structure_id,
                state=state,
                motor_ids=motor_ids,
                response_assembly_ids=assemblies,
                proof_episode_ids=provisional.proof_episode_ids,
                authority_hmac_sha256=_sign(
                    self._construction_key,
                    _CONSTRUCTION_DOMAIN,
                    provisional.payload(),
                ),
            )
            construction.verify(self._construction_key)
            staged = dict(self._constructions)
            if (
                cue_structure_id not in staged
                and len(staged) >= self._profile.max_constructions
            ):
                raise GroundedTurnCapacityError(
                    "grounded turn construction capacity exhausted"
                )
            staged[cue_structure_id] = construction
            self._encoded(self._episodes, staged)
            self._constructions = staged
            return construction

    def resolve_reply(
        self,
        prompt_resolution: GroundingResolution,
    ) -> GroundedReplyResolution:
        cue = cue_from_resolution(
            prompt_resolution,
            max_elements=self._profile.max_elements_per_cue,
        )
        with self._lock:
            construction = self._constructions.get(cue.structure_id)
        if construction is None:
            return GroundedReplyResolution(
                state="unknown",
                reason="no lived grounded turn construction",
                cue_structure_id=cue.structure_id,
                motor_id=None,
                construction_id=None,
            )
        construction.verify(self._construction_key)
        if construction.state is GroundedTurnConstructionState.AMBIGUOUS:
            return GroundedReplyResolution(
                state="ambiguous",
                reason="grounded cue has divergent self-heard responses",
                cue_structure_id=cue.structure_id,
                motor_id=None,
                construction_id=construction.construction_id,
            )
        return GroundedReplyResolution(
            state="resolved",
            reason="one recurrent grounded turn construction resolved",
            cue_structure_id=cue.structure_id,
            motor_id=construction.motor_ids[0],
            construction_id=construction.construction_id,
        )

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            encoded = self._encoded(
                self._episodes, self._constructions
            )
            unique = sum(
                value.state is GroundedTurnConstructionState.UNIQUE
                for value in self._constructions.values()
            )
            ambiguous = len(self._constructions) - unique
            return {
                "episode_count": len(self._episodes),
                "episode_capacity": self._profile.max_episodes,
                "episode_capacity_exhausted": (
                    len(self._episodes) >= self._profile.max_episodes
                ),
                "construction_count": len(self._constructions),
                "construction_capacity": (
                    self._profile.max_constructions
                ),
                "unique_construction_count": unique,
                "ambiguous_construction_count": ambiguous,
                "encoded_state_bytes": len(encoded),
                "state_byte_capacity": self._profile.max_state_bytes,
            }

    def cross_validate_restored(
        self,
        *,
        grounding_owner: AuditoryMotifCausalGroundingOwner,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> None:
        """Cross-mount restored cues and motors before reply authority lives."""

        if not isinstance(
            grounding_owner, AuditoryMotifCausalGroundingOwner
        ):
            raise TypeError(
                "grounded turn restore requires grounding owner"
            )
        if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
            raise TypeError(
                "grounded turn restore requires self-vocal motor owner"
            )
        grounded_roots = {
            (
                alternative.root.root_id,
                alternative.root.value_sha256,
            )
            for distinction in grounding_owner.distinctions
            for alternative in distinction.alternatives
            if alternative.diagnostic_motif_neuron_ids
        }
        motor_by_id = {
            exemplar.motor_id: exemplar
            for exemplar in motor_owner.exemplars
        }
        with self._lock:
            episodes = tuple(self._episodes.values())
            constructions = tuple(self._constructions.values())
        for episode in episodes:
            episode.verify(
                self._episode_key,
                self._profile.max_elements_per_cue,
            )
            for element in episode.cue.elements:
                if (
                    element.root.root_id,
                    element.root.value_sha256,
                ) not in grounded_roots:
                    raise ValueError(
                        "restored turn cue lacks grounded distinction"
                    )
            exemplar = motor_by_id.get(episode.motor_id)
            if exemplar is None:
                raise ValueError(
                    "restored turn episode lacks motor exemplar"
                )
            motor_owner.verify_exemplar(exemplar)
            if exemplar.firing_motif_neuron_ids != (
                episode.response_firing_motif_neuron_ids
            ):
                raise ValueError(
                    "restored turn response differs from motor assembly"
                )
        for construction in constructions:
            construction.verify(self._construction_key)
            for motor_id in construction.motor_ids:
                exemplar = motor_by_id.get(motor_id)
                if exemplar is None:
                    raise ValueError(
                        "restored construction lacks motor exemplar"
                    )
                motor_owner.verify_exemplar(exemplar)

    def _encoded(
        self,
        episodes: Mapping[str, GroundedTurnEpisode],
        constructions: Mapping[str, GroundedTurnConstruction],
    ) -> bytes:
        body = {
            "constructions": [
                constructions[key].payload()
                | {
                    "authority_hmac_sha256": (
                        constructions[key].authority_hmac_sha256
                    ),
                    "construction_id": constructions[key].construction_id,
                }
                for key in sorted(constructions)
            ],
            "episodes": [
                episodes[key].as_record() for key in sorted(episodes)
            ],
            "resource_profile": (
                self._profile.payload()
                | {
                    "authority_receipt_sha256": (
                        self._profile.authority_receipt_sha256
                    )
                }
            ),
            "schema": TURN_STATE_SCHEMA,
        }
        envelope = {
            "body": body,
            "schema": TURN_ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(
                self._state_key, _STATE_DOMAIN, body
            ),
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._profile.max_state_bytes:
            raise GroundedTurnCapacityError(
                "grounded turn state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(
                self._episodes, self._constructions
            )

    @staticmethod
    def _cue_from_record(
        value: object,
        *,
        max_elements: int,
    ) -> GroundedTurnCue:
        if (
            not isinstance(value, Mapping)
            or set(value) != {"cue_id", "elements", "structure_id"}
            or not isinstance(value.get("elements"), list)
        ):
            raise ValueError("grounded turn cue record changed")
        elements = []
        for raw in value["elements"]:
            if (
                not isinstance(raw, Mapping)
                or set(raw)
                != {
                    "contributing_motif_neuron_ids",
                    "ordinal",
                    "root",
                    "source_time_end",
                    "source_time_start",
                    "temporal_relation",
                }
                or not isinstance(
                    raw.get("contributing_motif_neuron_ids"), list
                )
                or not isinstance(raw.get("root"), Mapping)
                or set(raw["root"])
                != {"root_id", "value_json", "value_sha256"}
            ):
                raise ValueError("grounded cue element record changed")
            root = GroundingRoot(
                root_id=raw["root"].get("root_id"),
                value_sha256=raw["root"].get("value_sha256"),
                value_json=raw["root"].get("value_json"),
            )
            root.verify()
            elements.append(GroundedCueElement(
                ordinal=raw.get("ordinal"),
                temporal_relation=raw.get("temporal_relation"),
                root=root,
                source_time_start=_fraction(
                    raw.get("source_time_start"),
                    "grounded cue source start",
                ),
                source_time_end=_fraction(
                    raw.get("source_time_end"),
                    "grounded cue source end",
                ),
                contributing_motif_neuron_ids=tuple(
                    raw["contributing_motif_neuron_ids"]
                ),
            ))
        cue = GroundedTurnCue(
            cue_id=value.get("cue_id"),
            structure_id=value.get("structure_id"),
            elements=tuple(elements),
        )
        cue.verify(max_elements)
        if cue.as_record() != dict(value):
            raise ValueError("grounded turn cue is not canonical")
        return cue

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
    ) -> "GroundedTurnConversationOwner":
        if not isinstance(encoded, bytes):
            raise TypeError("grounded turn state must be immutable bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("grounded turn state is not JSON") from exc
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != TURN_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("body"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("grounded turn state envelope changed")
        body = envelope["body"]
        if (
            set(body)
            != {
                "constructions",
                "episodes",
                "resource_profile",
                "schema",
            }
            or body.get("schema") != TURN_STATE_SCHEMA
            or not isinstance(body.get("constructions"), list)
            or not isinstance(body.get("episodes"), list)
            or not isinstance(body.get("resource_profile"), Mapping)
        ):
            raise ValueError("grounded turn state body changed")
        raw_profile = body["resource_profile"]
        if set(raw_profile) != {
            "authority_receipt_sha256",
            "max_constructions",
            "max_elements_per_cue",
            "max_episodes",
            "max_state_bytes",
            "profile_id",
            "schema",
        }:
            raise ValueError("grounded turn profile record changed")
        profile = GroundedTurnResourceProfile(
            profile_id=raw_profile.get("profile_id"),
            max_episodes=raw_profile.get("max_episodes"),
            max_constructions=raw_profile.get("max_constructions"),
            max_elements_per_cue=raw_profile.get(
                "max_elements_per_cue"
            ),
            max_state_bytes=raw_profile.get("max_state_bytes"),
            authority_receipt_sha256=raw_profile.get(
                "authority_receipt_sha256"
            ),
        )
        profile.verify()
        owner = cls(
            authority_key=authority_key,
            resource_profile=profile,
        )
        if not hmac.compare_digest(
            envelope["state_hmac_sha256"],
            _sign(owner._state_key, _STATE_DOMAIN, body),
        ):
            raise ValueError("grounded turn state HMAC changed")
        for raw in body["episodes"]:
            if (
                not isinstance(raw, Mapping)
                or set(raw)
                != {
                    "authority_hmac_sha256",
                    "cue",
                    "episode_id",
                    "motor_id",
                    "outcome_settlement_receipt_sha256",
                    "prompt_settlement_receipt_sha256",
                    "response_firing_motif_neuron_ids",
                    "schema",
                    "self_hearing_receipt_sha256",
                }
                or raw.get("schema") != TURN_EPISODE_SCHEMA
                or not isinstance(
                    raw.get("response_firing_motif_neuron_ids"), list
                )
            ):
                raise ValueError("grounded turn episode record changed")
            episode = GroundedTurnEpisode(
                episode_id=raw.get("episode_id"),
                cue=owner._cue_from_record(
                    raw.get("cue"),
                    max_elements=profile.max_elements_per_cue,
                ),
                prompt_settlement_receipt_sha256=raw.get(
                    "prompt_settlement_receipt_sha256"
                ),
                outcome_settlement_receipt_sha256=raw.get(
                    "outcome_settlement_receipt_sha256"
                ),
                motor_id=raw.get("motor_id"),
                response_firing_motif_neuron_ids=tuple(
                    raw["response_firing_motif_neuron_ids"]
                ),
                self_hearing_receipt_sha256=raw.get(
                    "self_hearing_receipt_sha256"
                ),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
            )
            episode.verify(
                owner._episode_key,
                profile.max_elements_per_cue,
            )
            if (
                episode.as_record() != dict(raw)
                or episode.episode_id in owner._episodes
            ):
                raise ValueError(
                    "grounded turn episode is not canonical or duplicated"
                )
            owner._episodes[episode.episode_id] = episode
        for raw in body["constructions"]:
            if (
                not isinstance(raw, Mapping)
                or set(raw)
                != {
                    "authority_hmac_sha256",
                    "construction_id",
                    "cue_structure_id",
                    "motor_ids",
                    "proof_episode_ids",
                    "response_assembly_ids",
                    "schema",
                    "state",
                }
                or raw.get("schema") != TURN_CONSTRUCTION_SCHEMA
                or not isinstance(raw.get("motor_ids"), list)
                or not isinstance(raw.get("proof_episode_ids"), list)
                or not isinstance(raw.get("response_assembly_ids"), list)
            ):
                raise ValueError("grounded turn construction record changed")
            try:
                state = GroundedTurnConstructionState(raw.get("state"))
            except ValueError as exc:
                raise ValueError(
                    "grounded turn construction state changed"
                ) from exc
            construction = GroundedTurnConstruction(
                construction_id=raw.get("construction_id"),
                cue_structure_id=raw.get("cue_structure_id"),
                state=state,
                motor_ids=tuple(raw["motor_ids"]),
                response_assembly_ids=tuple(
                    raw["response_assembly_ids"]
                ),
                proof_episode_ids=tuple(raw["proof_episode_ids"]),
                authority_hmac_sha256=raw.get(
                    "authority_hmac_sha256"
                ),
            )
            construction.verify(owner._construction_key)
            canonical = construction.payload() | {
                "authority_hmac_sha256": (
                    construction.authority_hmac_sha256
                ),
                "construction_id": construction.construction_id,
            }
            if (
                canonical != dict(raw)
                or construction.cue_structure_id
                in owner._constructions
                or any(
                    episode_id not in owner._episodes
                    for episode_id in construction.proof_episode_ids
                )
            ):
                raise ValueError(
                    "grounded turn construction is not canonical"
                )
            owner._constructions[
                construction.cue_structure_id
            ] = construction
        if (
            len(owner._episodes) > profile.max_episodes
            or len(owner._constructions) > profile.max_constructions
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError("grounded turn restored state changed")
        return owner


class GroundedTurnCapacityError(RuntimeError):
    pass


__all__ = (
    "GroundedCueElement",
    "GroundedReplyResolution",
    "GroundedTurnCapacityError",
    "GroundedTurnConstruction",
    "GroundedTurnConstructionState",
    "GroundedTurnConversationOwner",
    "GroundedTurnCue",
    "GroundedTurnEpisode",
    "GroundedTurnResourceProfile",
    "cue_from_resolution",
)
