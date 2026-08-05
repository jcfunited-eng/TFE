"""Authenticated lived external-form to self-vocal teaching episodes.

This authority admits one relationship only when every constituent is already
owned by its physical substrate authority:

* one exact W1 multisensory settlement caused by an external embodied actor;
* full binaural recurrent-q activation evidence mounted in that settlement;
* one immediately subsequent self-body vocal motor execution; and
* the resulting physical two-ear self-acoustic settlement.

The retained witness contains the complete causal settlement payloads and the
complete upstream authority records.  No text, transcript, semantic label,
speaker label, chi, TTS artifact, score, threshold, legacy teaching record, or
reduced decision vector participates in admission or identity.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticState,
)


LIVED_VOCAL_TEACHING_PROFILE_SCHEMA = (
    "guala.lived_vocal_teaching.profile.v1"
)
LIVED_VOCAL_TEACHING_WITNESS_SCHEMA = (
    "guala.lived_vocal_teaching.witness.v1"
)
LIVED_VOCAL_TEACHING_EPISODE_SCHEMA = (
    "guala.lived_vocal_teaching.episode.v1"
)
LIVED_VOCAL_TEACHING_STATE_SCHEMA = (
    "guala.lived_vocal_teaching.state.v1"
)
LIVED_VOCAL_TEACHING_ENVELOPE_SCHEMA = (
    "guala.lived_vocal_teaching.state_hmac.v1"
)
_EPISODE_DOMAIN = b"guala-lived-vocal-teaching-episode-v1\0"
_STATE_DOMAIN = b"guala-lived-vocal-teaching-state-v1\0"
_HEX = frozenset("0123456789abcdef")
LIVED_VOCAL_TEACHING_CONSUMER_ID = "lived-vocal-teaching"
_FORBIDDEN_WITNESS_KEYS = frozenset({
    "chi",
    "decision_vector",
    "label",
    "legacy_binding",
    "score",
    "text",
    "transcript",
    "tts",
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


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("lived teaching authority key is not typed")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("lived teaching authority key boundary changed")
    return result


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or "\x00" in value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{name} must be a bounded identifier")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _settlement_payload(
    settlement: CausalExperienceSettlement,
    *,
    max_bytes: int,
    role: str,
) -> bytes:
    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError(f"{role} requires an exact causal settlement")
    settlement.verify()
    if settlement.language_events:
        raise ValueError(f"{role} cannot contain language authority")
    if settlement.routing_chis:
        raise ValueError(f"{role} cannot contain chi routing")
    if settlement.source_tags:
        raise ValueError(f"{role} cannot contain source labels")
    payload = settlement.receipt_registry.resolve(
        settlement.authority_receipt_sha256,
        f"{role} settlement custody",
    )
    if len(payload) > max_bytes:
        raise RuntimeError(f"{role} settlement byte capacity exhausted")
    decoded = json.loads(payload.decode("utf-8"))
    if _canonical(decoded) != payload:
        raise ValueError(f"{role} settlement is not canonical")
    return payload


def _signed_record(value) -> dict[str, object]:
    return {
        **value.payload(),
        "authority_hmac_sha256": value.authority_hmac_sha256,
        "authority_receipt_sha256": value.authority_receipt_sha256,
    }


def _grounding_record(
    value: W1BinauralGroundingEvidence,
) -> dict[str, object]:
    return {
        **value.payload(),
        "authority_hmac_sha256": value.authority_hmac_sha256,
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "episode_id": value.episode_id,
    }


def _motif_record(value) -> dict[str, object]:
    return {
        **value.payload(),
        "authority_receipt_sha256": value.authority_receipt_sha256,
    }


def _validate_witness_keys(value: object) -> None:
    if isinstance(value, Mapping):
        forbidden = _FORBIDDEN_WITNESS_KEYS.intersection(value)
        if forbidden:
            raise ValueError(
                "lived teaching witness contains forbidden semantic keys: "
                + ",".join(sorted(forbidden))
            )
        for nested in value.values():
            _validate_witness_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_witness_keys(nested)


@dataclass(frozen=True, slots=True)
class LivedVocalTeachingResourceProfile:
    profile_id: str
    max_episodes: int
    max_external_settlement_bytes: int
    max_self_settlement_bytes: int
    max_motor_pcm_bytes: int
    max_auditory_activations: int
    max_witness_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_episodes: int,
        max_external_settlement_bytes: int,
        max_self_settlement_bytes: int,
        max_motor_pcm_bytes: int,
        max_auditory_activations: int,
        max_witness_bytes: int,
        max_state_bytes: int,
    ) -> "LivedVocalTeachingResourceProfile":
        provisional = cls(
            profile_id=_identifier(
                profile_id, "lived teaching profile"
            ),
            max_episodes=_positive(
                max_episodes, "lived teaching episode capacity"
            ),
            max_external_settlement_bytes=_positive(
                max_external_settlement_bytes,
                "external settlement byte capacity",
            ),
            max_self_settlement_bytes=_positive(
                max_self_settlement_bytes,
                "self settlement byte capacity",
            ),
            max_motor_pcm_bytes=_positive(
                max_motor_pcm_bytes, "self motor PCM byte capacity"
            ),
            max_auditory_activations=_positive(
                max_auditory_activations,
                "auditory activation capacity",
            ),
            max_witness_bytes=_positive(
                max_witness_bytes, "lived teaching witness capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "lived teaching state capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        if provisional.max_state_bytes <= provisional.max_witness_bytes:
            raise ValueError(
                "lived teaching state capacity must exceed one witness"
            )
        return cls(
            **{
                field: getattr(provisional, field)
                for field in (
                    "profile_id",
                    "max_episodes",
                    "max_external_settlement_bytes",
                    "max_self_settlement_bytes",
                    "max_motor_pcm_bytes",
                    "max_auditory_activations",
                    "max_witness_bytes",
                    "max_state_bytes",
                )
            },
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_auditory_activations": self.max_auditory_activations,
            "max_episodes": self.max_episodes,
            "max_external_settlement_bytes": (
                self.max_external_settlement_bytes
            ),
            "max_motor_pcm_bytes": self.max_motor_pcm_bytes,
            "max_self_settlement_bytes": (
                self.max_self_settlement_bytes
            ),
            "max_state_bytes": self.max_state_bytes,
            "max_witness_bytes": self.max_witness_bytes,
            "profile_id": self.profile_id,
            "schema": LIVED_VOCAL_TEACHING_PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256
        }

    def verify(self) -> None:
        _identifier(self.profile_id, "lived teaching profile")
        for value, name in (
            (self.max_episodes, "lived teaching episode capacity"),
            (
                self.max_external_settlement_bytes,
                "external settlement byte capacity",
            ),
            (
                self.max_self_settlement_bytes,
                "self settlement byte capacity",
            ),
            (self.max_motor_pcm_bytes, "self motor PCM byte capacity"),
            (
                self.max_auditory_activations,
                "auditory activation capacity",
            ),
            (self.max_witness_bytes, "lived teaching witness capacity"),
            (self.max_state_bytes, "lived teaching state capacity"),
        ):
            _positive(value, name)
        _sha256(
            self.authority_receipt_sha256,
            "lived teaching profile authority",
        )
        if (
            self.max_state_bytes <= self.max_witness_bytes
            or self.authority_receipt_sha256 != _digest(self.payload())
        ):
            raise ValueError("lived teaching resource profile changed")


@dataclass(frozen=True, slots=True)
class LivedVocalTeachingEpisode:
    episode_id: str
    witness_json: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "schema": LIVED_VOCAL_TEACHING_EPISODE_SCHEMA,
            "witness_json": self.witness_json,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def witness(
        self,
        *,
        authority_key: bytes,
        profile: LivedVocalTeachingResourceProfile,
    ) -> dict[str, object]:
        self.verify(authority_key=authority_key, profile=profile)
        return json.loads(self.witness_json)

    def verify(
        self,
        *,
        authority_key: bytes,
        profile: LivedVocalTeachingResourceProfile,
    ) -> None:
        profile.verify()
        _sha256(self.episode_id, "lived teaching episode")
        _sha256(
            self.authority_hmac_sha256,
            "lived teaching episode HMAC",
        )
        _sha256(
            self.authority_receipt_sha256,
            "lived teaching episode authority",
        )
        if not isinstance(self.witness_json, str):
            raise ValueError("lived teaching witness is not canonical JSON")
        try:
            witness = json.loads(self.witness_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "lived teaching witness is unreadable"
            ) from error
        encoded = _canonical(witness)
        expected_keys = {
            "auditory_form_evidence",
            "causal_junction",
            "external_execution",
            "external_multisensory",
            "resource_profile_authority_receipt_sha256",
            "schema",
            "self_vocal_response",
        }
        if (
            encoded.decode("utf-8") != self.witness_json
            or not isinstance(witness, dict)
            or set(witness) != expected_keys
            or witness.get("schema")
            != LIVED_VOCAL_TEACHING_WITNESS_SCHEMA
            or witness.get(
                "resource_profile_authority_receipt_sha256"
            ) != profile.authority_receipt_sha256
            or len(encoded) > profile.max_witness_bytes
        ):
            raise ValueError("lived teaching witness boundary changed")
        _validate_witness_keys(witness)
        payload = self.payload()
        signature = hmac.new(
            authority_key,
            _EPISODE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            self.episode_id != _digest(witness)
            or not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError("lived teaching episode authority changed")


class LivedVocalTeachingEpisodeAuthority:
    """Bounded owner of exact lived external-form/self-vocal relations."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: LivedVocalTeachingResourceProfile,
        world_authority: EmbodimentWorldAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("lived teaching requires the W1 world authority")
        if not isinstance(
            grounding_authority,
            W1BinauralGroundingEvidenceAuthority,
        ):
            raise TypeError(
                "lived teaching requires binaural grounding authority"
            )
        resource_profile.verify()
        root = hashlib.sha256(_key(authority_key)).digest()
        self._episode_key = hashlib.sha256(
            _EPISODE_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = resource_profile
        self._world = world_authority
        self._grounding = grounding_authority
        self._episodes: dict[str, LivedVocalTeachingEpisode] = {}
        self._lock = threading.RLock()

    @property
    def episodes(self) -> tuple[LivedVocalTeachingEpisode, ...]:
        with self._lock:
            return tuple(
                self._episodes[key] for key in sorted(self._episodes)
            )

    def admit(
        self,
        *,
        external_custody_authority: SettledExperienceCustodyAuthority,
        external_custody_capability: SettledExperienceConsumerCapability,
        self_custody_authority: SettledExperienceCustodyAuthority,
        self_custody_capability: SettledExperienceConsumerCapability,
        auditory_form_evidence: W1BinauralGroundingEvidence,
    ) -> LivedVocalTeachingEpisode:
        if not isinstance(
            external_custody_authority,
            SettledExperienceCustodyAuthority,
        ) or not isinstance(
            self_custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "lived teaching requires settled-experience custody"
            )
        if (
            not isinstance(
                external_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or external_custody_capability.consumer_id
            != LIVED_VOCAL_TEACHING_CONSUMER_ID
            or not isinstance(
                self_custody_capability,
                SettledExperienceConsumerCapability,
            )
            or self_custody_capability.consumer_id
            != LIVED_VOCAL_TEACHING_CONSUMER_ID
        ):
            raise ValueError(
                "lived teaching requires its own custody capability"
            )
        external_view = external_custody_authority.open_child(
            external_custody_capability
        )
        self_view = self_custody_authority.open_child(
            self_custody_capability
        )
        if external_view.world_execution is None:
            raise ValueError(
                "lived teaching requires applied-execution custody"
            )
        external_execution = external_view.world_execution
        settlement = external_view.causal_settlement
        evidence_receipt = external_view.physical_evidence_receipt
        self_execution = self_view.world_execution
        self_receipt = self_view.self_acoustic_receipt
        self._grounding.verify(auditory_form_evidence)
        if (
            external_execution.disposition != "applied"
            or external_execution.actor_body_id is None
            or external_execution.actor_body_id
            == external_execution.after.self_body_id
            or external_execution.port_id == self._world.port_id
            or evidence_receipt is None
            or evidence_receipt.world_execution_receipt_sha256
            != external_execution.authority_receipt_sha256
            or evidence_receipt.world_observation_before_receipt_sha256
            != external_execution.before.authority_receipt_sha256
            or evidence_receipt.world_observation_after_receipt_sha256
            != external_execution.after.authority_receipt_sha256
        ):
            raise ValueError(
                "lived teaching lacks authenticated external physical presence"
            )
        observed = {
            value.sense
            for value in settlement.interpretations
            if value.state == "observed" and value.substreams
        }
        if not {"sight", "sound", "body"}.issubset(observed):
            raise ValueError(
                "lived teaching requires observed sight, sound, and body"
            )
        if (
            auditory_form_evidence.causal_settlement_receipt_sha256
            != settlement.authority_receipt_sha256
            or external_view.binaural_receptor_settlement is None
            or external_view.binaural_auditory_l5 is None
            or auditory_form_evidence
            .receptor_settlement_receipt_sha256
            != external_view.binaural_receptor_settlement
            .authority_receipt_sha256
            or not auditory_form_evidence.activations
            or len(auditory_form_evidence.activations)
            > self._profile.max_auditory_activations
        ):
            raise ValueError(
                "learned auditory form is not mounted in this experience"
            )
        external_payload = _settlement_payload(
            settlement,
            max_bytes=self._profile.max_external_settlement_bytes,
            role="external lived teaching",
        )
        if (
            self_view.source_kind
            is not SettledExperienceSourceKind.SELF_ACOUSTIC
            or self_execution is None
            or self_receipt is None
            or self_view.binaural_auditory_l5 is None
            or self_view.binaural_receptor_settlement is None
            or self_execution.before
            != external_execution.after
            or self_execution.before.authority_receipt_sha256
            != external_execution.after.authority_receipt_sha256
            or self_execution.port_id != self._world.port_id
            or self_execution.actor_body_id
            != self_execution.before.self_body_id
            or self_receipt.state
            is not W1SelfAcousticState.OBSERVED
            or self_receipt.world_execution_receipt_sha256
            != self_execution.authority_receipt_sha256
            or self_receipt.world_before_receipt_sha256
            != self_execution.before.authority_receipt_sha256
            or self_receipt.world_after_receipt_sha256
            != self_execution.after.authority_receipt_sha256
        ):
            raise ValueError(
                "self vocal response is not the immediate physical outcome"
            )
        self_payload = _settlement_payload(
            self_view.causal_settlement,
            max_bytes=self._profile.max_self_settlement_bytes,
            role="self vocal outcome",
        )
        if (
            settlement.authority_receipt_sha256
            == self_view.causal_settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "external experience and self outcome must be distinct"
            )
        witness = {
            "auditory_form_evidence": _grounding_record(
                auditory_form_evidence
            ),
            "causal_junction": {
                "external_after_revision": (
                    external_execution.after.revision
                ),
                "self_before_revision": self_execution.before.revision,
                "world_observation_receipt_sha256": (
                    external_execution.after.authority_receipt_sha256
                ),
            },
            "external_execution": external_execution.as_record(),
            "external_multisensory": {
                "binaural_auditory_l5": (
                    external_view.binaural_auditory_l5
                    .persistence_record()
                ),
                "binaural_receptors": (
                    external_view.binaural_receptor_settlement
                    .authority_record()
                ),
                "custody_capability": (
                    external_custody_capability.as_record()
                ),
                "occurrence_counter": (
                    external_view.occurrence_counter.as_record()
                ),
                "parent_custody_receipt_sha256": (
                    external_view.parent_custody_receipt_sha256
                ),
                "physical_evidence": evidence_receipt.as_record(),
                "settlement_payload_base64": base64.b64encode(
                    external_payload
                ).decode("ascii"),
                "settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
                "source_occurrence_id": (
                    external_view.source_occurrence_id
                ),
            },
            "resource_profile_authority_receipt_sha256": (
                self._profile.authority_receipt_sha256
            ),
            "schema": LIVED_VOCAL_TEACHING_WITNESS_SCHEMA,
            "self_vocal_response": {
                "acoustic_outcome": _signed_record(
                    self_receipt
                ),
                "binaural_auditory_l5": (
                    self_view.binaural_auditory_l5.persistence_record()
                ),
                "binaural_receptors": (
                    self_view.binaural_receptor_settlement
                    .authority_record()
                ),
                "custody_capability": (
                    self_custody_capability.as_record()
                ),
                "execution": self_execution.as_record(),
                "occurrence_counter": (
                    self_view.occurrence_counter.as_record()
                ),
                "parent_custody_receipt_sha256": (
                    self_view.parent_custody_receipt_sha256
                ),
                "settlement_payload_base64": base64.b64encode(
                    self_payload
                ).decode("ascii"),
                "settlement_receipt_sha256": (
                    self_view.causal_settlement
                    .authority_receipt_sha256
                ),
                "source_occurrence_id": (
                    self_view.source_occurrence_id
                ),
            },
        }
        _validate_witness_keys(witness)
        encoded_witness = _canonical(witness)
        if len(encoded_witness) > self._profile.max_witness_bytes:
            raise RuntimeError("lived teaching witness capacity exhausted")
        episode_id = _digest(witness)
        provisional = LivedVocalTeachingEpisode(
            episode_id=episode_id,
            witness_json=encoded_witness.decode("utf-8"),
            authority_hmac_sha256="",
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._episode_key,
            _EPISODE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        episode = LivedVocalTeachingEpisode(
            episode_id=provisional.episode_id,
            witness_json=provisional.witness_json,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        episode.verify(
            authority_key=self._episode_key,
            profile=self._profile,
        )
        with self._lock:
            existing = self._episodes.get(episode_id)
            if existing is not None:
                if existing != episode:
                    raise ValueError(
                        "lived teaching episode identity conflicted"
                    )
                return existing
            if len(self._episodes) >= self._profile.max_episodes:
                raise RuntimeError(
                    "lived teaching episode capacity exhausted"
                )
            staged = dict(self._episodes)
            staged[episode_id] = episode
            self._encoded(staged)
            self._episodes = staged
        return episode

    def verify(self, episode: LivedVocalTeachingEpisode) -> None:
        if not isinstance(episode, LivedVocalTeachingEpisode):
            raise TypeError("lived teaching episode is not typed")
        episode.verify(
            authority_key=self._episode_key,
            profile=self._profile,
        )
        with self._lock:
            if self._episodes.get(episode.episode_id) != episode:
                raise ValueError("lived teaching episode is not owned")

    def witness(
        self,
        episode: LivedVocalTeachingEpisode,
    ) -> dict[str, object]:
        """Return a verified decoded copy of one owned immutable witness."""

        self.verify(episode)
        return json.loads(episode.witness_json)

    def status(self) -> dict[str, int | bool]:
        with self._lock:
            encoded = self._encoded(self._episodes)
            return {
                "count": len(self._episodes),
                "episode_capacity": self._profile.max_episodes,
                "episode_capacity_exhausted": (
                    len(self._episodes) >= self._profile.max_episodes
                ),
                "state_bytes": len(encoded),
                "state_byte_capacity": self._profile.max_state_bytes,
                "state_byte_capacity_exhausted": (
                    len(encoded) >= self._profile.max_state_bytes
                ),
            }

    def _body(
        self,
        episodes: Mapping[str, LivedVocalTeachingEpisode],
    ) -> dict[str, object]:
        return {
            "episodes": [
                episodes[key].record() for key in sorted(episodes)
            ],
            "resource_profile": self._profile.record(),
            "schema": LIVED_VOCAL_TEACHING_STATE_SCHEMA,
        }

    def _encoded(
        self,
        episodes: Mapping[str, LivedVocalTeachingEpisode],
    ) -> bytes:
        if len(episodes) > self._profile.max_episodes:
            raise RuntimeError(
                "lived teaching episode capacity exhausted"
            )
        body = self._body(episodes)
        envelope = {
            "body": body,
            "schema": LIVED_VOCAL_TEACHING_ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        }
        encoded = _canonical(envelope)
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError("lived teaching state capacity exhausted")
        return encoded

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded(self._episodes)

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or len(encoded) > self._profile.max_state_bytes
        ):
            raise ValueError("lived teaching state boundary changed")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("lived teaching state is unreadable") from error
        if _canonical(envelope) != encoded or not isinstance(
            envelope, dict
        ) or set(envelope) != {
            "body", "schema", "state_hmac_sha256"
        } or envelope.get("schema") != (
            LIVED_VOCAL_TEACHING_ENVELOPE_SCHEMA
        ):
            raise ValueError("lived teaching state envelope changed")
        body = envelope["body"]
        state_hmac = envelope["state_hmac_sha256"]
        if not isinstance(body, dict) or set(body) != {
            "episodes", "resource_profile", "schema"
        } or body.get("schema") != LIVED_VOCAL_TEACHING_STATE_SCHEMA or (
            body.get("resource_profile") != self._profile.record()
        ) or not isinstance(body.get("episodes"), list) or not isinstance(
            state_hmac, str
        ):
            raise ValueError("lived teaching state authority changed")
        signature = hmac.new(
            self._state_key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, state_hmac):
            raise ValueError("lived teaching state authority changed")
        restored: dict[str, LivedVocalTeachingEpisode] = {}
        for raw in body["episodes"]:
            if not isinstance(raw, dict) or set(raw) != {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "episode_id",
                "schema",
                "witness_json",
            } or raw.get("schema") != LIVED_VOCAL_TEACHING_EPISODE_SCHEMA:
                raise ValueError("lived teaching episode record changed")
            episode = LivedVocalTeachingEpisode(
                episode_id=raw["episode_id"],
                witness_json=raw["witness_json"],
                authority_hmac_sha256=raw["authority_hmac_sha256"],
                authority_receipt_sha256=(
                    raw["authority_receipt_sha256"]
                ),
            )
            episode.verify(
                authority_key=self._episode_key,
                profile=self._profile,
            )
            if episode.episode_id in restored:
                raise ValueError("lived teaching state repeats an episode")
            restored[episode.episode_id] = episode
        if len(restored) > self._profile.max_episodes:
            raise ValueError("lived teaching state exceeds capacity")
        self._encoded(restored)
        with self._lock:
            self._episodes = restored


__all__ = (
    "LIVED_VOCAL_TEACHING_ENVELOPE_SCHEMA",
    "LIVED_VOCAL_TEACHING_EPISODE_SCHEMA",
    "LIVED_VOCAL_TEACHING_CONSUMER_ID",
    "LIVED_VOCAL_TEACHING_PROFILE_SCHEMA",
    "LIVED_VOCAL_TEACHING_STATE_SCHEMA",
    "LIVED_VOCAL_TEACHING_WITNESS_SCHEMA",
    "LivedVocalTeachingEpisode",
    "LivedVocalTeachingEpisodeAuthority",
    "LivedVocalTeachingResourceProfile",
)
