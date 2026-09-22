"""Exact external-vocal to self-vocal W1 imitation chains.

An imitation is admitted only when an authenticated action-vocal lesson's
external execution is immediately followed by an authenticated self motor
execution in the same world revision chain.  Both regimes retain complete
left/right q activation evidence.  Their intersection is recorded as a
physical cross-regime candidate, never as a label or intended word.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
)
from dsf_ai_service.substrate.embodiment_world import EmbodimentWorldAuthority
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    W1ActionVocalLesson,
    W1ActionVocalLessonAuthority,
)
from dsf_ai_service.substrate.w1_binaural_controlled_distinction import (
    W1DiagnosticCell,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralActivationEvidence,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticState,
)


W1_IMITATION_PROFILE_SCHEMA = (
    "guala.w1.external_self_imitation.profile.v1"
)
W1_IMITATION_SCHEMA = "guala.w1.external_self_imitation.v1"
_IMITATION_DOMAIN = b"guala-w1-external-self-imitation-v1\0"
_HEX = frozenset("0123456789abcdef")
W1_IMITATION_EXTERNAL_CONSUMER_ID = (
    "w1-external-self-imitation.external"
)
W1_IMITATION_SELF_CONSUMER_ID = "w1-external-self-imitation.self"


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
        raise TypeError("W1 imitation key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 imitation key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class W1ImitationResourceProfile:
    profile_id: str
    max_imitation_episodes: int
    max_activations_per_regime: int
    max_episode_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_imitation_episodes: int,
        max_activations_per_regime: int,
        max_episode_bytes: int,
    ) -> "W1ImitationResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("W1 imitation profile changed")
        provisional = cls(
            profile_id=profile_id,
            max_imitation_episodes=_positive(
                max_imitation_episodes,
                "W1 imitation episode capacity",
            ),
            max_activations_per_regime=_positive(
                max_activations_per_regime,
                "W1 imitation activation capacity",
            ),
            max_episode_bytes=_positive(
                max_episode_bytes,
                "W1 imitation byte capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_imitation_episodes=(
                provisional.max_imitation_episodes
            ),
            max_activations_per_regime=(
                provisional.max_activations_per_regime
            ),
            max_episode_bytes=provisional.max_episode_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_activations_per_regime": (
                self.max_activations_per_regime
            ),
            "max_episode_bytes": self.max_episode_bytes,
            "max_imitation_episodes": self.max_imitation_episodes,
            "profile_id": self.profile_id,
            "schema": W1_IMITATION_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _positive(
            self.max_imitation_episodes,
            "W1 imitation episode capacity",
        )
        _positive(
            self.max_activations_per_regime,
            "W1 imitation activation capacity",
        )
        _positive(self.max_episode_bytes, "W1 imitation byte capacity")
        _sha256(
            self.authority_receipt_sha256,
            "W1 imitation profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 imitation profile authority changed")


@dataclass(frozen=True, slots=True)
class W1ExternalSelfImitation:
    imitation_id: str
    lesson_receipt_sha256: str
    action_before_world_state_sha256: str
    action_roots: tuple[GroundingRoot, ...]
    external_execution_receipt_sha256: str
    self_execution_receipt_sha256: str
    self_emission_receipt_sha256: str
    self_acoustic_receipt_sha256: str
    motor_id: str
    external_activations: tuple[
        W1BinauralActivationEvidence, ...
    ]
    self_activations: tuple[W1BinauralActivationEvidence, ...]
    cross_regime_cells: tuple[W1DiagnosticCell, ...]
    external_after_revision: int
    self_after_revision: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_before_world_state_sha256": (
                self.action_before_world_state_sha256
            ),
            "action_roots": [
                value.as_record() for value in self.action_roots
            ],
            "cross_regime_cells": [
                value.record() for value in self.cross_regime_cells
            ],
            "external_activations": [
                value.record() for value in self.external_activations
            ],
            "external_after_revision": self.external_after_revision,
            "external_execution_receipt_sha256": (
                self.external_execution_receipt_sha256
            ),
            "lesson_receipt_sha256": self.lesson_receipt_sha256,
            "motor_id": self.motor_id,
            "schema": W1_IMITATION_SCHEMA,
            "self_acoustic_receipt_sha256": (
                self.self_acoustic_receipt_sha256
            ),
            "self_activations": [
                value.record() for value in self.self_activations
            ],
            "self_after_revision": self.self_after_revision,
            "self_emission_receipt_sha256": (
                self.self_emission_receipt_sha256
            ),
            "self_execution_receipt_sha256": (
                self.self_execution_receipt_sha256
            ),
        }


class W1ExternalSelfImitationAuthority:
    """Bounded source-disjoint owner of exact imitation chains."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1ImitationResourceProfile,
        world_authority: EmbodimentWorldAuthority,
        lesson_authority: W1ActionVocalLessonAuthority,
        motor_owner: SelfVocalPCMMotorOwner,
    ) -> None:
        resource_profile.verify()
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 imitation requires its world")
        if not isinstance(
            lesson_authority, W1ActionVocalLessonAuthority
        ):
            raise TypeError("W1 imitation requires lesson authority")
        if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
            raise TypeError("W1 imitation requires self motor authority")
        root = hashlib.sha256(_key(authority_key)).digest()
        self._imitation_key = hashlib.sha256(
            _IMITATION_DOMAIN + root
        ).digest()
        self._profile = resource_profile
        self._world = world_authority
        self._lessons = lesson_authority
        self._motor = motor_owner
        self._episodes: dict[str, W1ExternalSelfImitation] = {}
        self._used_sources: set[str] = set()
        self._lock = threading.RLock()

    def _verify(self, episode: W1ExternalSelfImitation) -> None:
        for value, name in (
            (episode.imitation_id, "W1 imitation"),
            (episode.lesson_receipt_sha256, "W1 imitation lesson"),
            (
                episode.action_before_world_state_sha256,
                "W1 imitation controlled world",
            ),
            (
                episode.external_execution_receipt_sha256,
                "W1 imitation external execution",
            ),
            (
                episode.self_execution_receipt_sha256,
                "W1 imitation self execution",
            ),
            (
                episode.self_emission_receipt_sha256,
                "W1 imitation self emission",
            ),
            (
                episode.self_acoustic_receipt_sha256,
                "W1 imitation self hearing",
            ),
            (episode.motor_id, "W1 imitation motor"),
            (
                episode.authority_hmac_sha256,
                "W1 imitation HMAC",
            ),
            (
                episode.authority_receipt_sha256,
                "W1 imitation authority",
            ),
        ):
            _sha256(value, name)
        if (
            not episode.action_roots
            or not episode.external_activations
            or not episode.self_activations
            or not episode.cross_regime_cells
            or len(episode.external_activations)
            > self._profile.max_activations_per_regime
            or len(episode.self_activations)
            > self._profile.max_activations_per_regime
            or episode.self_after_revision
            != episode.external_after_revision + 1
            or episode.cross_regime_cells
            != tuple(sorted(set(episode.cross_regime_cells)))
        ):
            raise ValueError("W1 imitation episode changed")
        for root in episode.action_roots:
            root.verify()
        for activation in (
            *episode.external_activations,
            *episode.self_activations,
        ):
            activation.verify()
        for cell in episode.cross_regime_cells:
            cell.verify()
        external = {
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in episode.external_activations
        }
        self_cells = {
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in episode.self_activations
        }
        if set(episode.cross_regime_cells) != external.intersection(
            self_cells
        ):
            raise ValueError("W1 imitation cross-regime field changed")
        payload = episode.payload()
        signature = hmac.new(
            self._imitation_key,
            _IMITATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            episode.imitation_id != _digest(payload)
            or len(_canonical(payload)) > self._profile.max_episode_bytes
            or not hmac.compare_digest(
                signature, episode.authority_hmac_sha256
            )
            or episode.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("W1 imitation authority changed")

    def admit(
        self,
        *,
        lesson: W1ActionVocalLesson,
        external_custody_authority: SettledExperienceCustodyAuthority,
        external_custody_capability: SettledExperienceConsumerCapability,
        self_custody_authority: SettledExperienceCustodyAuthority,
        self_custody_capability: SettledExperienceConsumerCapability,
    ) -> W1ExternalSelfImitation:
        self._lessons.verify(lesson)
        if (
            not isinstance(
                external_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                self_custody_authority,
                SettledExperienceCustodyAuthority,
            )
            or not isinstance(
                external_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or not isinstance(
                self_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or external_custody_capability.consumer_id
            != W1_IMITATION_EXTERNAL_CONSUMER_ID
            or self_custody_capability.consumer_id
            != W1_IMITATION_SELF_CONSUMER_ID
        ):
            raise ValueError(
                "W1 imitation requires its purpose-bound custody"
            )
        external_view = external_custody_authority.open_child(
            external_custody_capability
        )
        self_view = self_custody_authority.open_child(
            self_custody_capability
        )
        external_execution = external_view.world_execution
        self_execution = self_view.world_execution
        self_receipt = self_view.self_acoustic_receipt
        self_firing = self_view.self_acoustic_prelearning_firing
        exemplars = tuple(
            value for value in self._motor.exemplars
            if self_receipt is not None
            and value.motor_id == self_receipt.motor_id
        )
        if len(exemplars) != 1:
            raise ValueError("W1 imitation self motor is not owned")
        self_exemplar = exemplars[0]
        self._motor.verify_exemplar(self_exemplar)
        if (
            external_view.source_kind
            is not SettledExperienceSourceKind.PHYSICAL_EVIDENCE
            or self_view.source_kind
            is not SettledExperienceSourceKind.SELF_ACOUSTIC
            or external_execution is None
            or self_execution is None
            or self_receipt is None
            or self_firing is None
            or lesson.vocal_execution_receipt_sha256
            != external_execution.authority_receipt_sha256
            or external_execution.after != self_execution.before
            or external_execution.after.revision
            != self_execution.before.revision
            or self_execution.after.revision
            != external_execution.after.revision + 1
            or self_receipt.state
            is not W1SelfAcousticState.OBSERVED
            or self_receipt.world_execution_receipt_sha256
            != self_execution.authority_receipt_sha256
            or self_receipt.motor_id != self_exemplar.motor_id
        ):
            raise ValueError(
                "W1 imitation physical revision or motor chain changed"
            )
        external_activations = lesson.vocal_activations
        self_activations = tuple(
            W1BinauralActivationEvidence.from_activation(value)
            for value in self_firing.activations
        )
        external_cells = {
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in external_activations
        }
        self_cells = {
            W1DiagnosticCell(value.ear_id, value.neuron_id)
            for value in self_activations
        }
        cross = tuple(sorted(
            external_cells.intersection(self_cells)
        ))
        if not cross:
            raise ValueError(
                "W1 imitation has no exact cross-regime q conjunction"
            )
        source_receipts = {
            lesson.authority_receipt_sha256,
            external_execution.authority_receipt_sha256,
            external_view.parent_custody_receipt_sha256,
            external_custody_capability.authority_receipt_sha256,
            self_execution.authority_receipt_sha256,
            self_receipt.self_vocal_emission_receipt_sha256,
            self_receipt.authority_receipt_sha256,
            self_view.parent_custody_receipt_sha256,
            self_custody_capability.authority_receipt_sha256,
        }
        if len(source_receipts) != 9:
            raise ValueError("W1 imitation source identities overlap")
        provisional = W1ExternalSelfImitation(
            imitation_id="0" * 64,
            lesson_receipt_sha256=lesson.authority_receipt_sha256,
            action_before_world_state_sha256=(
                lesson.action_before_world_state_sha256
            ),
            action_roots=lesson.action_roots,
            external_execution_receipt_sha256=(
                external_execution.authority_receipt_sha256
            ),
            self_execution_receipt_sha256=(
                self_execution.authority_receipt_sha256
            ),
            self_emission_receipt_sha256=(
                self_receipt.self_vocal_emission_receipt_sha256
            ),
            self_acoustic_receipt_sha256=(
                self_receipt.authority_receipt_sha256
            ),
            motor_id=self_exemplar.motor_id,
            external_activations=external_activations,
            self_activations=self_activations,
            cross_regime_cells=cross,
            external_after_revision=external_execution.after.revision,
            self_after_revision=self_execution.after.revision,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._imitation_key,
            _IMITATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        episode = W1ExternalSelfImitation(
            imitation_id=_digest(payload),
            lesson_receipt_sha256=provisional.lesson_receipt_sha256,
            action_before_world_state_sha256=(
                provisional.action_before_world_state_sha256
            ),
            action_roots=provisional.action_roots,
            external_execution_receipt_sha256=(
                provisional.external_execution_receipt_sha256
            ),
            self_execution_receipt_sha256=(
                provisional.self_execution_receipt_sha256
            ),
            self_emission_receipt_sha256=(
                provisional.self_emission_receipt_sha256
            ),
            self_acoustic_receipt_sha256=(
                provisional.self_acoustic_receipt_sha256
            ),
            motor_id=provisional.motor_id,
            external_activations=provisional.external_activations,
            self_activations=provisional.self_activations,
            cross_regime_cells=provisional.cross_regime_cells,
            external_after_revision=provisional.external_after_revision,
            self_after_revision=provisional.self_after_revision,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        self._verify(episode)
        with self._lock:
            if self._used_sources.intersection(source_receipts):
                raise ValueError("W1 imitation reuses a physical source")
            if (
                len(self._episodes)
                >= self._profile.max_imitation_episodes
            ):
                raise RuntimeError("W1 imitation capacity exhausted")
            self._episodes[episode.imitation_id] = episode
            self._used_sources.update(source_receipts)
        return episode

    def verify(self, episode: W1ExternalSelfImitation) -> None:
        if not isinstance(episode, W1ExternalSelfImitation):
            raise TypeError("W1 imitation episode is not typed")
        self._verify(episode)

    @property
    def episodes(self) -> tuple[W1ExternalSelfImitation, ...]:
        with self._lock:
            return tuple(
                self._episodes[key] for key in sorted(self._episodes)
            )


__all__ = [
    "W1_IMITATION_EXTERNAL_CONSUMER_ID",
    "W1_IMITATION_SELF_CONSUMER_ID",
    "W1ExternalSelfImitation",
    "W1ExternalSelfImitationAuthority",
    "W1ImitationResourceProfile",
]
