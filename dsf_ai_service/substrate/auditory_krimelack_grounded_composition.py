"""Experience-grown ordered composition of grounded auditory kinds.

This owner composes no text and selects no reply.  It accepts two confirmed
auditory causal admissions whose kinds are alternatives in one verified
grounded referent construction.  Their exact physical intervals establish
order.  Two distinct lived pair episodes are required before the ordered
composition is released.

The grounded construction retains each complete non-auditory explicit DSF
referent value.  Episode closures retain both occurrence, association,
full-field witness, and interval authorities.  A digest is only an index.
Replays do not reinforce, reversed order is a different unknown composition,
and overlapping occurrences fail closed.  State is bounded, canonical, and
HMAC authenticated.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AuditoryKrimelackDeliberationAdmission,
)
from dsf_ai_service.substrate.auditory_krimelack_grounded_referent import (
    AUDITORY_GROUNDED_CONSTRUCTION_SCHEMA,
    AuditoryGroundedAlternative,
    AuditoryGroundedConstruction,
)


AUDITORY_GROUNDED_COMPOSITION_EPISODE_SCHEMA = (
    "guala.auditory.krimelack_grounded_composition_episode.v1"
)
AUDITORY_GROUNDED_COMPOSITION_SCHEMA = (
    "guala.auditory.krimelack_grounded_composition.v1"
)
AUDITORY_GROUNDED_COMPOSITION_STATE_SCHEMA = (
    "guala.auditory.krimelack_grounded_composition_state.v1"
)
AUDITORY_GROUNDED_COMPOSITION_ENVELOPE_SCHEMA = (
    "guala.auditory.krimelack_grounded_composition_hmac.v1"
)

REQUIRED_COMPOSITION_EPISODES = 2
MAX_AUDITORY_GROUNDED_COMPOSITIONS = 64
MAX_AUDITORY_GROUNDED_COMPOSITION_STATE_BYTES = 32 * 1024 * 1024

_EPISODE_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_grounded_composition_episode.v1\0"
)
_COMPOSITION_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_grounded_composition.v1\0"
)
_STATE_HMAC_DOMAIN = (
    b"guala.auditory.krimelack_grounded_composition_state.v1\0"
)


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


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(
            "auditory grounded composition key must be bytes or text"
        )
    if not 32 <= len(result) <= 4096:
        raise ValueError(
            "auditory grounded composition key has an invalid boundary"
        )
    return result


def _sign(domain: bytes, key: bytes, value: object) -> str:
    return hmac.new(
        key,
        domain + _canonical(value),
        hashlib.sha256,
    ).hexdigest()


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("grounded composition time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    if (
        not numerator.lstrip("-").isdigit()
        or not denominator.isdigit()
        or int(denominator) <= 0
    ):
        raise ValueError(f"{name} is not an exact fraction")
    result = Fraction(int(numerator), int(denominator))
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonical")
    return result


def _construction_record(
    value: AuditoryGroundedConstruction,
    *,
    authority_key: object,
) -> dict[str, object]:
    value.verify(authority_key)
    return {
        **value.payload(),
        "authority_hmac_sha256": value.authority_hmac_sha256,
        "construction_id": value.construction_id,
    }


def _construction_from_record(
    value: object,
    *,
    authority_key: object,
) -> AuditoryGroundedConstruction:
    expected = {
        "alternatives",
        "authority_hmac_sha256",
        "construction_id",
        "proof_episode_ids",
        "referent_root",
        "schema",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema")
        != AUDITORY_GROUNDED_CONSTRUCTION_SCHEMA
        or not isinstance(value.get("alternatives"), list)
        or not isinstance(value.get("proof_episode_ids"), list)
    ):
        raise ValueError(
            "auditory grounded construction record changed"
        )
    alternatives = []
    for item in value["alternatives"]:
        if (
            not isinstance(item, Mapping)
            or set(item)
            != {
                "kind_id",
                "referent_value",
                "referent_value_sha256",
            }
        ):
            raise ValueError(
                "auditory grounded alternative record changed"
            )
        alternatives.append(AuditoryGroundedAlternative(
            kind_id=item.get("kind_id"),
            referent_value_sha256=item.get(
                "referent_value_sha256"
            ),
            referent_value=item.get("referent_value"),
        ))
    result = AuditoryGroundedConstruction(
        construction_id=value.get("construction_id"),
        referent_root=value.get("referent_root"),
        alternatives=tuple(alternatives),
        proof_episode_ids=tuple(value["proof_episode_ids"]),
        authority_hmac_sha256=value.get(
            "authority_hmac_sha256"
        ),
    )
    result.verify(authority_key)
    if _construction_record(
        result,
        authority_key=authority_key,
    ) != dict(value):
        raise ValueError(
            "auditory grounded construction is not canonical"
        )
    return result


@dataclass(frozen=True, slots=True)
class AuditoryGroundedCompositionEpisode:
    episode_id: str
    left_kind_id: str
    right_kind_id: str
    left_referent_value_sha256: str
    right_referent_value_sha256: str
    left_association_id: str
    right_association_id: str
    left_occurrence_id: str
    right_occurrence_id: str
    left_world_witness_receipts: tuple[str, ...]
    right_world_witness_receipts: tuple[str, ...]
    left_source_time_start: Fraction
    left_source_time_end: Fraction
    right_source_time_start: Fraction
    right_source_time_end: Fraction
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "left_association_id": self.left_association_id,
            "left_kind_id": self.left_kind_id,
            "left_occurrence_id": self.left_occurrence_id,
            "left_referent_value_sha256": (
                self.left_referent_value_sha256
            ),
            "left_source_time_end": _fraction_text(
                self.left_source_time_end
            ),
            "left_source_time_start": _fraction_text(
                self.left_source_time_start
            ),
            "left_world_witness_receipts": list(
                self.left_world_witness_receipts
            ),
            "right_association_id": self.right_association_id,
            "right_kind_id": self.right_kind_id,
            "right_occurrence_id": self.right_occurrence_id,
            "right_referent_value_sha256": (
                self.right_referent_value_sha256
            ),
            "right_source_time_end": _fraction_text(
                self.right_source_time_end
            ),
            "right_source_time_start": _fraction_text(
                self.right_source_time_start
            ),
            "right_world_witness_receipts": list(
                self.right_world_witness_receipts
            ),
            "schema": AUDITORY_GROUNDED_COMPOSITION_EPISODE_SCHEMA,
        }

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key)
        for value, name in (
            (self.episode_id, "episode"),
            (self.left_kind_id, "left kind"),
            (self.right_kind_id, "right kind"),
            (
                self.left_referent_value_sha256,
                "left referent",
            ),
            (
                self.right_referent_value_sha256,
                "right referent",
            ),
            (self.left_association_id, "left association"),
            (self.right_association_id, "right association"),
            (self.left_occurrence_id, "left occurrence"),
            (self.right_occurrence_id, "right occurrence"),
            (self.authority_hmac_sha256, "authority"),
        ):
            sha256_digest(value, f"grounded composition {name}")
        if (
            self.left_kind_id == self.right_kind_id
            or self.left_occurrence_id == self.right_occurrence_id
            or not self.left_source_time_start
            < self.left_source_time_end
            <= self.right_source_time_start
            < self.right_source_time_end
            or not self.left_world_witness_receipts
            or not self.right_world_witness_receipts
        ):
            raise ValueError(
                "grounded composition causal order changed"
            )
        for receipts in (
            self.left_world_witness_receipts,
            self.right_world_witness_receipts,
        ):
            for receipt in receipts:
                sha256_digest(
                    receipt,
                    "grounded composition world witness",
                )
        if (
            self.episode_id != _digest(self.payload())
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(
                    _EPISODE_HMAC_DOMAIN,
                    key,
                    self.payload(),
                ),
            )
        ):
            raise ValueError(
                "grounded composition episode authority changed"
            )

    def as_record(self, authority_key: object) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "episode_id": self.episode_id,
        }


@dataclass(frozen=True, slots=True)
class AuditoryGroundedComposition:
    composition_id: str
    grounding: AuditoryGroundedConstruction
    left_kind_id: str
    right_kind_id: str
    episodes: tuple[AuditoryGroundedCompositionEpisode, ...]
    authority_hmac_sha256: str

    @property
    def state(self) -> str:
        return (
            "confirmed"
            if len(self.episodes) == REQUIRED_COMPOSITION_EPISODES
            else "unconfirmed"
        )

    def payload(self, authority_key: object) -> dict[str, object]:
        return {
            "episode_ids": [
                value.episode_id for value in self.episodes
            ],
            "grounding": _construction_record(
                self.grounding,
                authority_key=authority_key,
            ),
            "left_kind_id": self.left_kind_id,
            "right_kind_id": self.right_kind_id,
            "schema": AUDITORY_GROUNDED_COMPOSITION_SCHEMA,
        }

    def verify(self, authority_key: object) -> None:
        key = _key(authority_key)
        self.grounding.verify(key)
        sha256_digest(
            self.composition_id,
            "grounded composition identity",
        )
        sha256_digest(
            self.authority_hmac_sha256,
            "grounded composition authority",
        )
        alternatives = {
            value.kind_id: value.referent_value_sha256
            for value in self.grounding.alternatives
        }
        if (
            self.left_kind_id == self.right_kind_id
            or self.left_kind_id not in alternatives
            or self.right_kind_id not in alternatives
            or not 1
            <= len(self.episodes)
            <= REQUIRED_COMPOSITION_EPISODES
            or len({
                value.episode_id for value in self.episodes
            })
            != len(self.episodes)
        ):
            raise ValueError(
                "grounded composition evidence changed"
            )
        for episode in self.episodes:
            episode.verify(key)
            if (
                episode.left_kind_id != self.left_kind_id
                or episode.right_kind_id != self.right_kind_id
                or episode.left_referent_value_sha256
                != alternatives[self.left_kind_id]
                or episode.right_referent_value_sha256
                != alternatives[self.right_kind_id]
            ):
                raise ValueError(
                    "grounded composition episode left its referents"
                )
        identity = _digest({
            "grounding_construction_id": (
                self.grounding.construction_id
            ),
            "left_kind_id": self.left_kind_id,
            "right_kind_id": self.right_kind_id,
            "schema": (
                "guala.auditory.krimelack_grounded_composition_identity.v1"
            ),
        })
        if (
            self.composition_id != identity
            or not hmac.compare_digest(
                self.authority_hmac_sha256,
                _sign(
                    _COMPOSITION_HMAC_DOMAIN,
                    key,
                    self.payload(key),
                ),
            )
        ):
            raise ValueError(
                "grounded composition authority changed"
            )

    def as_record(self, authority_key: object) -> dict[str, object]:
        self.verify(authority_key)
        return {
            **self.payload(authority_key),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "composition_id": self.composition_id,
            "episodes": [
                value.as_record(authority_key)
                for value in self.episodes
            ],
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class AuditoryGroundedCompositionObservation:
    state: str
    repeated: bool
    composition_id: str
    distinct_episodes: int


@dataclass(frozen=True, slots=True)
class AuditoryGroundedCompositionResolution:
    state: str
    reason: str
    composition: AuditoryGroundedComposition | None


class AuditoryKrimelackGroundedCompositionOwner:
    """Bounded serial owner of repeated exact grounded order."""

    def __init__(
        self,
        *,
        authority_key: object,
        log_event: Callable[..., None],
        composition_capacity: int = MAX_AUDITORY_GROUNDED_COMPOSITIONS,
        encoded_state_capacity: int = (
            MAX_AUDITORY_GROUNDED_COMPOSITION_STATE_BYTES
        ),
    ) -> None:
        if (
            isinstance(composition_capacity, bool)
            or not isinstance(composition_capacity, int)
            or not 1
            <= composition_capacity
            <= MAX_AUDITORY_GROUNDED_COMPOSITIONS
            or isinstance(encoded_state_capacity, bool)
            or not isinstance(encoded_state_capacity, int)
            or not 1
            <= encoded_state_capacity
            <= MAX_AUDITORY_GROUNDED_COMPOSITION_STATE_BYTES
        ):
            raise ValueError(
                "grounded composition capacity is invalid"
            )
        self._key = _key(authority_key)
        self._log_event = log_event
        self._composition_capacity = composition_capacity
        self._encoded_state_capacity = encoded_state_capacity
        self._lock = threading.RLock()
        self._compositions: dict[str, AuditoryGroundedComposition] = {}
        self._encoded_bytes = len(
            self._encoded(self._compositions)
        )

    @staticmethod
    def _alternative(
        grounding: AuditoryGroundedConstruction,
        kind_id: str,
    ) -> AuditoryGroundedAlternative:
        matches = tuple(
            value
            for value in grounding.alternatives
            if value.kind_id == kind_id
        )
        if len(matches) != 1:
            raise ValueError(
                "grounded composition kind is not grounded"
            )
        return matches[0]

    def _composition(
        self,
        *,
        grounding: AuditoryGroundedConstruction,
        left_kind_id: str,
        right_kind_id: str,
        episodes: tuple[
            AuditoryGroundedCompositionEpisode, ...
        ],
    ) -> AuditoryGroundedComposition:
        identity = _digest({
            "grounding_construction_id": grounding.construction_id,
            "left_kind_id": left_kind_id,
            "right_kind_id": right_kind_id,
            "schema": (
                "guala.auditory.krimelack_grounded_composition_identity.v1"
            ),
        })
        provisional = AuditoryGroundedComposition(
            composition_id=identity,
            grounding=grounding,
            left_kind_id=left_kind_id,
            right_kind_id=right_kind_id,
            episodes=episodes,
            authority_hmac_sha256="0" * 64,
        )
        result = AuditoryGroundedComposition(
            composition_id=provisional.composition_id,
            grounding=provisional.grounding,
            left_kind_id=provisional.left_kind_id,
            right_kind_id=provisional.right_kind_id,
            episodes=provisional.episodes,
            authority_hmac_sha256=_sign(
                _COMPOSITION_HMAC_DOMAIN,
                self._key,
                provisional.payload(self._key),
            ),
        )
        result.verify(self._key)
        return result

    def _state(
        self,
        values: Mapping[str, AuditoryGroundedComposition],
    ) -> dict[str, object]:
        return {
            "composition_capacity": self._composition_capacity,
            "compositions": [
                values[key].as_record(self._key)
                for key in sorted(values)
            ],
            "encoded_state_capacity": self._encoded_state_capacity,
            "required_distinct_episodes": (
                REQUIRED_COMPOSITION_EPISODES
            ),
            "schema": AUDITORY_GROUNDED_COMPOSITION_STATE_SCHEMA,
        }

    def _encoded(
        self,
        values: Mapping[str, AuditoryGroundedComposition],
    ) -> bytes:
        payload = _canonical(self._state(values))
        if len(payload) > self._encoded_state_capacity:
            raise RuntimeError(
                "grounded composition state capacity is full"
            )
        return payload

    def observe(
        self,
        *,
        grounding: AuditoryGroundedConstruction,
        left: AuditoryKrimelackDeliberationAdmission,
        right: AuditoryKrimelackDeliberationAdmission,
    ) -> AuditoryGroundedCompositionObservation:
        if not isinstance(
            grounding,
            AuditoryGroundedConstruction,
        ):
            raise TypeError(
                "grounded composition requires grounding authority"
            )
        if not isinstance(
            left,
            AuditoryKrimelackDeliberationAdmission,
        ) or not isinstance(
            right,
            AuditoryKrimelackDeliberationAdmission,
        ):
            raise TypeError(
                "grounded composition requires confirmed admissions"
            )
        grounding.verify(self._key)
        left.verify(self._key)
        right.verify(self._key)
        left_alternative = self._alternative(
            grounding, left.kind_id
        )
        right_alternative = self._alternative(
            grounding, right.kind_id
        )
        left_occurrence = left.current_occurrence
        right_occurrence = right.current_occurrence
        if (
            left.kind_id == right.kind_id
            or left_occurrence.source_time_end
            > right_occurrence.source_time_start
        ):
            raise ValueError(
                "grounded composition has no exact causal order"
            )
        episode_payload = {
            "left_association_id": left.association_id,
            "left_kind_id": left.kind_id,
            "left_occurrence_id": left_occurrence.occurrence_id,
            "left_referent_value_sha256": (
                left_alternative.referent_value_sha256
            ),
            "left_source_time_end": _fraction_text(
                left_occurrence.source_time_end
            ),
            "left_source_time_start": _fraction_text(
                left_occurrence.source_time_start
            ),
            "left_world_witness_receipts": [
                value.settlement_receipt_sha256
                for value in left.world_witnesses
            ],
            "right_association_id": right.association_id,
            "right_kind_id": right.kind_id,
            "right_occurrence_id": right_occurrence.occurrence_id,
            "right_referent_value_sha256": (
                right_alternative.referent_value_sha256
            ),
            "right_source_time_end": _fraction_text(
                right_occurrence.source_time_end
            ),
            "right_source_time_start": _fraction_text(
                right_occurrence.source_time_start
            ),
            "right_world_witness_receipts": [
                value.settlement_receipt_sha256
                for value in right.world_witnesses
            ],
            "schema": AUDITORY_GROUNDED_COMPOSITION_EPISODE_SCHEMA,
        }
        episode_id = _digest(episode_payload)
        episode = AuditoryGroundedCompositionEpisode(
            episode_id=episode_id,
            left_kind_id=left.kind_id,
            right_kind_id=right.kind_id,
            left_referent_value_sha256=(
                left_alternative.referent_value_sha256
            ),
            right_referent_value_sha256=(
                right_alternative.referent_value_sha256
            ),
            left_association_id=left.association_id,
            right_association_id=right.association_id,
            left_occurrence_id=left_occurrence.occurrence_id,
            right_occurrence_id=right_occurrence.occurrence_id,
            left_world_witness_receipts=tuple(
                value.settlement_receipt_sha256
                for value in left.world_witnesses
            ),
            right_world_witness_receipts=tuple(
                value.settlement_receipt_sha256
                for value in right.world_witnesses
            ),
            left_source_time_start=left_occurrence.source_time_start,
            left_source_time_end=left_occurrence.source_time_end,
            right_source_time_start=right_occurrence.source_time_start,
            right_source_time_end=right_occurrence.source_time_end,
            authority_hmac_sha256=_sign(
                _EPISODE_HMAC_DOMAIN,
                self._key,
                episode_payload,
            ),
        )
        episode.verify(self._key)
        identity = _digest({
            "grounding_construction_id": grounding.construction_id,
            "left_kind_id": left.kind_id,
            "right_kind_id": right.kind_id,
            "schema": (
                "guala.auditory.krimelack_grounded_composition_identity.v1"
            ),
        })
        with self._lock:
            prior = self._compositions.get(identity)
            if prior is None:
                if (
                    len(self._compositions)
                    >= self._composition_capacity
                ):
                    raise RuntimeError(
                        "grounded composition capacity is full"
                    )
                episodes = ()
            else:
                if prior.grounding != grounding:
                    raise ValueError(
                        "grounded composition authority changed"
                    )
                episodes = prior.episodes
            repeated = any(
                value.episode_id == episode_id for value in episodes
            )
            if repeated or len(episodes) >= (
                REQUIRED_COMPOSITION_EPISODES
            ):
                learned = prior
            else:
                learned = self._composition(
                    grounding=grounding,
                    left_kind_id=left.kind_id,
                    right_kind_id=right.kind_id,
                    episodes=(*episodes, episode),
                )
                prospective = dict(self._compositions)
                prospective[identity] = learned
                encoded = self._encoded(prospective)
                self._compositions = prospective
                self._encoded_bytes = len(encoded)
            if learned is None:
                raise RuntimeError(
                    "grounded composition repeated absent evidence"
                )
            result = AuditoryGroundedCompositionObservation(
                state=learned.state,
                repeated=repeated,
                composition_id=learned.composition_id,
                distinct_episodes=len(learned.episodes),
            )
        self._log_event(
            "auditory_krimelack_grounded_composition_observed",
            composition_id=result.composition_id,
            distinct_episodes=result.distinct_episodes,
            state=result.state,
        )
        return result

    def resolve(
        self,
        *,
        grounding_construction_id: str,
        left_kind_id: str,
        right_kind_id: str,
    ) -> AuditoryGroundedCompositionResolution:
        for value, name in (
            (grounding_construction_id, "grounding"),
            (left_kind_id, "left kind"),
            (right_kind_id, "right kind"),
        ):
            sha256_digest(value, f"grounded composition query {name}")
        identity = _digest({
            "grounding_construction_id": grounding_construction_id,
            "left_kind_id": left_kind_id,
            "right_kind_id": right_kind_id,
            "schema": (
                "guala.auditory.krimelack_grounded_composition_identity.v1"
            ),
        })
        with self._lock:
            value = self._compositions.get(identity)
            if value is None:
                return AuditoryGroundedCompositionResolution(
                    state="unknown",
                    reason="ordered_grounded_composition_absent",
                    composition=None,
                )
            value.verify(self._key)
            if value.state != "confirmed":
                return AuditoryGroundedCompositionResolution(
                    state="unconfirmed",
                    reason="repeated_lived_order_absent",
                    composition=None,
                )
            return AuditoryGroundedCompositionResolution(
                state="confirmed",
                reason="repeated_exact_grounded_order",
                composition=value,
            )

    def encoded_snapshot(self) -> dict[str, object]:
        with self._lock:
            payload = self._encoded(self._compositions)
        body = {
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": AUDITORY_GROUNDED_COMPOSITION_ENVELOPE_SCHEMA,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        return {
            **body,
            "authority_hmac_sha256": _sign(
                _STATE_HMAC_DOMAIN,
                self._key,
                body,
            ),
        }

    def restore_encoded(self, envelope: object) -> None:
        expected = {
            "authority_hmac_sha256",
            "payload_base64",
            "schema",
            "sha256",
        }
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != expected
            or envelope.get("schema")
            != AUDITORY_GROUNDED_COMPOSITION_ENVELOPE_SCHEMA
        ):
            raise ValueError(
                "grounded composition envelope changed"
            )
        body = {
            "payload_base64": envelope.get("payload_base64"),
            "schema": envelope.get("schema"),
            "sha256": envelope.get("sha256"),
        }
        if not hmac.compare_digest(
            str(envelope.get("authority_hmac_sha256")),
            _sign(_STATE_HMAC_DOMAIN, self._key, body),
        ):
            raise ValueError(
                "grounded composition state HMAC changed"
            )
        text = envelope.get("payload_base64")
        if not isinstance(text, str):
            raise ValueError(
                "grounded composition state is unreadable"
            )
        try:
            payload = base64.b64decode(text, validate=True)
            decoded = json.loads(payload)
        except Exception as error:
            raise ValueError(
                "grounded composition state is unreadable"
            ) from error
        if (
            base64.b64encode(payload).decode("ascii") != text
            or hashlib.sha256(payload).hexdigest()
            != envelope.get("sha256")
            or len(payload) > self._encoded_state_capacity
            or not isinstance(decoded, Mapping)
            or set(decoded)
            != {
                "composition_capacity",
                "compositions",
                "encoded_state_capacity",
                "required_distinct_episodes",
                "schema",
            }
            or decoded.get("schema")
            != AUDITORY_GROUNDED_COMPOSITION_STATE_SCHEMA
            or decoded.get("composition_capacity")
            != self._composition_capacity
            or decoded.get("encoded_state_capacity")
            != self._encoded_state_capacity
            or decoded.get("required_distinct_episodes")
            != REQUIRED_COMPOSITION_EPISODES
            or not isinstance(decoded.get("compositions"), list)
            or len(decoded["compositions"])
            > self._composition_capacity
            or _canonical(decoded) != payload
        ):
            raise ValueError(
                "grounded composition state boundary changed"
            )
        restored: dict[str, AuditoryGroundedComposition] = {}
        for record in decoded["compositions"]:
            composition = self._composition_from_record(record)
            if composition.composition_id in restored:
                raise ValueError(
                    "grounded composition is duplicated"
                )
            restored[composition.composition_id] = composition
        encoded = self._encoded(restored)
        if encoded != payload:
            raise ValueError(
                "grounded composition state is not canonical"
            )
        with self._lock:
            self._compositions = restored
            self._encoded_bytes = len(encoded)

    def _composition_from_record(
        self,
        value: object,
    ) -> AuditoryGroundedComposition:
        expected = {
            "authority_hmac_sha256",
            "composition_id",
            "episode_ids",
            "episodes",
            "grounding",
            "left_kind_id",
            "right_kind_id",
            "schema",
            "state",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_GROUNDED_COMPOSITION_SCHEMA
            or not isinstance(value.get("episodes"), list)
            or not isinstance(value.get("episode_ids"), list)
        ):
            raise ValueError(
                "grounded composition record changed"
            )
        grounding = _construction_from_record(
            value.get("grounding"),
            authority_key=self._key,
        )
        episodes = tuple(
            self._episode_from_record(item)
            for item in value["episodes"]
        )
        result = AuditoryGroundedComposition(
            composition_id=value.get("composition_id"),
            grounding=grounding,
            left_kind_id=value.get("left_kind_id"),
            right_kind_id=value.get("right_kind_id"),
            episodes=episodes,
            authority_hmac_sha256=value.get(
                "authority_hmac_sha256"
            ),
        )
        if (
            value["episode_ids"]
            != [item.episode_id for item in episodes]
            or value.get("state") != result.state
        ):
            raise ValueError(
                "grounded composition record links changed"
            )
        result.verify(self._key)
        if result.as_record(self._key) != dict(value):
            raise ValueError(
                "grounded composition record is not canonical"
            )
        return result

    def _episode_from_record(
        self,
        value: object,
    ) -> AuditoryGroundedCompositionEpisode:
        payload_fields = {
            "left_association_id",
            "left_kind_id",
            "left_occurrence_id",
            "left_referent_value_sha256",
            "left_source_time_end",
            "left_source_time_start",
            "left_world_witness_receipts",
            "right_association_id",
            "right_kind_id",
            "right_occurrence_id",
            "right_referent_value_sha256",
            "right_source_time_end",
            "right_source_time_start",
            "right_world_witness_receipts",
            "schema",
        }
        expected = payload_fields | {
            "authority_hmac_sha256",
            "episode_id",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_GROUNDED_COMPOSITION_EPISODE_SCHEMA
            or not isinstance(
                value.get("left_world_witness_receipts"), list
            )
            or not isinstance(
                value.get("right_world_witness_receipts"), list
            )
        ):
            raise ValueError(
                "grounded composition episode record changed"
            )
        result = AuditoryGroundedCompositionEpisode(
            episode_id=value.get("episode_id"),
            left_kind_id=value.get("left_kind_id"),
            right_kind_id=value.get("right_kind_id"),
            left_referent_value_sha256=value.get(
                "left_referent_value_sha256"
            ),
            right_referent_value_sha256=value.get(
                "right_referent_value_sha256"
            ),
            left_association_id=value.get("left_association_id"),
            right_association_id=value.get(
                "right_association_id"
            ),
            left_occurrence_id=value.get("left_occurrence_id"),
            right_occurrence_id=value.get("right_occurrence_id"),
            left_world_witness_receipts=tuple(
                value["left_world_witness_receipts"]
            ),
            right_world_witness_receipts=tuple(
                value["right_world_witness_receipts"]
            ),
            left_source_time_start=_fraction(
                value.get("left_source_time_start"),
                "grounded composition left start",
            ),
            left_source_time_end=_fraction(
                value.get("left_source_time_end"),
                "grounded composition left end",
            ),
            right_source_time_start=_fraction(
                value.get("right_source_time_start"),
                "grounded composition right start",
            ),
            right_source_time_end=_fraction(
                value.get("right_source_time_end"),
                "grounded composition right end",
            ),
            authority_hmac_sha256=value.get(
                "authority_hmac_sha256"
            ),
        )
        result.verify(self._key)
        if result.as_record(self._key) != dict(value):
            raise ValueError(
                "grounded composition episode is not canonical"
            )
        return result

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "composition_count": len(self._compositions),
                "confirmed_count": sum(
                    value.state == "confirmed"
                    for value in self._compositions.values()
                ),
                "encoded_bytes": self._encoded_bytes,
                "schema": (
                    "guala.auditory.krimelack_grounded_composition_status.v1"
                ),
            }


__all__ = (
    "AUDITORY_GROUNDED_COMPOSITION_ENVELOPE_SCHEMA",
    "AUDITORY_GROUNDED_COMPOSITION_EPISODE_SCHEMA",
    "AUDITORY_GROUNDED_COMPOSITION_SCHEMA",
    "AUDITORY_GROUNDED_COMPOSITION_STATE_SCHEMA",
    "AuditoryGroundedComposition",
    "AuditoryGroundedCompositionObservation",
    "AuditoryGroundedCompositionResolution",
    "AuditoryKrimelackGroundedCompositionOwner",
)
