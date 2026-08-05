"""Bounded provenance ownership for dream, wake-test, and weave growth.

This owner has no background loop and no sensory authority.  A dream can only
re-enter and reorder relations already retained by the causal tapestry owner.
Its immutable origin is ``internally_simulated`` and every transition names
the settled tapestry relation that supports it.  It cannot create an external
episode, THING, receptor root, elapsed world time, label, word, or meaning.

A wake test remains counterfactual until a later embodied action has one
authenticated external consequence.  Resolution binds the exact action
execution and learned whole-organism consequence without deciding whether the
dream was semantically right.  A weave is the organism-originated embodied
expression proven by that settled wake path.  It stores only causal receipts;
there is no text, transcript, token, TTS payload, response, score, or script.

State is fixed-capacity, atomic, canonical, HMAC-authenticated, and cold
restorable.  Hashes provide custody and ordering only; they never supply
identity, similarity, salience, or meaning.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.organism_ordered_lived_experience import (
    OrganismOrderedLivedExperienceOwner,
)


PROFILE_SCHEMA = "guala.organism_dream_wake_weave.profile.v1"
DREAM_TRANSITION_SCHEMA = (
    "guala.organism_dream_wake_weave.dream_transition.v1"
)
DREAM_SCHEMA = "guala.organism_dream_wake_weave.dream.v1"
ORDERED_DREAM_TRANSITION_SCHEMA = (
    "guala.organism_dream_wake_weave.ordered_dream_transition.v1"
)
ORDERED_DREAM_SCHEMA = (
    "guala.organism_dream_wake_weave.ordered_dream.v1"
)
WAKE_SCHEMA = "guala.organism_dream_wake_weave.wake_test.v2"
WEAVE_SCHEMA = "guala.organism_dream_wake_weave.weave.v2"
PREPARED_SCHEMA = "guala.organism_dream_wake_weave.prepared.v1"
STATE_SCHEMA = "guala.organism_dream_wake_weave.state.v2"
ENVELOPE_SCHEMA = "guala.organism_dream_wake_weave.state_hmac.v2"
_LEGACY_STATE_SCHEMA = "guala.organism_dream_wake_weave.state.v1"
_LEGACY_ENVELOPE_SCHEMA = (
    "guala.organism_dream_wake_weave.state_hmac.v1"
)

_DREAM_DOMAIN = b"guala-organism-dream-v1\0"
_ORDERED_DREAM_DOMAIN = b"guala-organism-ordered-dream-v1\0"
_WAKE_DOMAIN = b"guala-organism-wake-test-v1\0"
_WEAVE_DOMAIN = b"guala-organism-weave-v1\0"
_PREPARED_DOMAIN = b"guala-organism-dream-wake-weave-prepared-v1\0"
_STATE_DOMAIN = b"guala-organism-dream-wake-weave-state-v1\0"
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


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("dream/wake/weave authority key changed")
    return hashlib.sha256(
        b"guala-organism-dream-wake-weave-owner-v1\0" + raw
    ).digest()


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


def _nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be nonnegative")
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
        raise TypeError("dream/wake causal time must be an exact Fraction")
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


class OriginState(str, Enum):
    EXTERNALLY_OBSERVED = "externally_observed"
    REMEMBERED_EXTERNAL = "remembered_external"
    INTERNALLY_SIMULATED = "internally_simulated"
    COUNTERFACTUAL = "counterfactual"
    SOURCE_UNRESOLVED = "source_unresolved"


@dataclass(frozen=True, slots=True)
class DreamWakeWeaveProfile:
    profile_id: str
    max_dreams: int
    max_wake_tests: int
    max_weaves: int
    max_transitions_per_dream: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_dreams: int,
        max_wake_tests: int,
        max_weaves: int,
        max_transitions_per_dream: int,
        max_state_bytes: int,
    ) -> "DreamWakeWeaveProfile":
        provisional = cls(
            profile_id=_identifier(profile_id, "dream profile id"),
            max_dreams=_positive(max_dreams, "dream capacity"),
            max_wake_tests=_positive(
                max_wake_tests,
                "wake-test capacity",
            ),
            max_weaves=_positive(max_weaves, "weave capacity"),
            max_transitions_per_dream=_positive(
                max_transitions_per_dream,
                "dream transition capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "dream/wake/weave state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_dreams=provisional.max_dreams,
            max_wake_tests=provisional.max_wake_tests,
            max_weaves=provisional.max_weaves,
            max_transitions_per_dream=(
                provisional.max_transitions_per_dream
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_dreams": self.max_dreams,
            "max_state_bytes": self.max_state_bytes,
            "max_transitions_per_dream": (
                self.max_transitions_per_dream
            ),
            "max_wake_tests": self.max_wake_tests,
            "max_weaves": self.max_weaves,
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
            max_dreams=self.max_dreams,
            max_wake_tests=self.max_wake_tests,
            max_weaves=self.max_weaves,
            max_transitions_per_dream=(
                self.max_transitions_per_dream
            ),
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError("dream/wake/weave profile changed")


@dataclass(frozen=True, slots=True)
class InternallyExecutedDreamTransition:
    internal_transition_index: int
    source_tapestry_receipt_sha256: str
    target_tapestry_receipt_sha256: str
    support_relation_receipt_sha256: str
    origin: OriginState

    def record(self) -> dict[str, object]:
        return {
            "internal_transition_index": self.internal_transition_index,
            "origin": self.origin.value,
            "schema": DREAM_TRANSITION_SCHEMA,
            "source_tapestry_receipt_sha256": (
                self.source_tapestry_receipt_sha256
            ),
            "support_relation_receipt_sha256": (
                self.support_relation_receipt_sha256
            ),
            "target_tapestry_receipt_sha256": (
                self.target_tapestry_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InternallyExecutedOrderedDreamTransition:
    internal_transition_index: int
    chronology_authority_receipt_sha256: str
    chronology_sequence: int
    predecessor_relation_receipt_sha256: str | None
    source_occurrence_receipt_sha256: str
    target_occurrence_receipt_sha256: str
    source_thing_id: str
    target_thing_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    target_time_start: Fraction
    target_time_end: Fraction
    source_full_field_root_receipt_sha256s: tuple[str, ...]
    target_full_field_root_receipt_sha256s: tuple[str, ...]
    support_relation_receipt_sha256: str
    origin: OriginState

    def record(self) -> dict[str, object]:
        return {
            "chronology_authority_receipt_sha256": (
                self.chronology_authority_receipt_sha256
            ),
            "chronology_sequence": self.chronology_sequence,
            "internal_transition_index": self.internal_transition_index,
            "origin": self.origin.value,
            "predecessor_relation_receipt_sha256": (
                self.predecessor_relation_receipt_sha256
            ),
            "schema": ORDERED_DREAM_TRANSITION_SCHEMA,
            "source_full_field_root_receipt_sha256s": list(
                self.source_full_field_root_receipt_sha256s
            ),
            "source_occurrence_receipt_sha256": (
                self.source_occurrence_receipt_sha256
            ),
            "source_thing_id": self.source_thing_id,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "support_relation_receipt_sha256": (
                self.support_relation_receipt_sha256
            ),
            "target_full_field_root_receipt_sha256s": list(
                self.target_full_field_root_receipt_sha256s
            ),
            "target_occurrence_receipt_sha256": (
                self.target_occurrence_receipt_sha256
            ),
            "target_thing_id": self.target_thing_id,
            "target_time_end": _fraction_text(self.target_time_end),
            "target_time_start": _fraction_text(self.target_time_start),
        }


@dataclass(frozen=True, slots=True)
class OrganismDreamRecord:
    organism_state_receipt_sha256: str
    source_tapestry_receipt_sha256s: tuple[str, ...]
    source_relation_receipt_sha256s: tuple[str, ...]
    source_latest_external_time_end: Fraction
    internal_transition_start: int
    internal_transition_end: int
    transitions: tuple[InternallyExecutedDreamTransition, ...]
    origin: OriginState
    external_embodiment_state: str
    external_event_claimed: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "external_embodiment_state": self.external_embodiment_state,
            "external_event_claimed": self.external_event_claimed,
            "internal_transition_end": self.internal_transition_end,
            "internal_transition_start": self.internal_transition_start,
            "organism_state_receipt_sha256": (
                self.organism_state_receipt_sha256
            ),
            "origin": self.origin.value,
            "schema": DREAM_SCHEMA,
            "source_latest_external_time_end": _fraction_text(
                self.source_latest_external_time_end
            ),
            "source_relation_receipt_sha256s": list(
                self.source_relation_receipt_sha256s
            ),
            "source_tapestry_receipt_sha256s": list(
                self.source_tapestry_receipt_sha256s
            ),
            "transitions": [
                transition.record() for transition in self.transitions
            ],
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class OrganismOrderedDreamRecord:
    organism_state_receipt_sha256: str
    chronology_authority_receipt_sha256: str
    source_occurrence_receipt_sha256s: tuple[str, ...]
    source_relation_receipt_sha256s: tuple[str, ...]
    source_latest_external_time_end: Fraction
    internal_transition_start: int
    internal_transition_end: int
    transitions: tuple[InternallyExecutedOrderedDreamTransition, ...]
    origin: OriginState
    external_embodiment_state: str
    external_event_claimed: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "chronology_authority_receipt_sha256": (
                self.chronology_authority_receipt_sha256
            ),
            "external_embodiment_state": self.external_embodiment_state,
            "external_event_claimed": self.external_event_claimed,
            "internal_transition_end": self.internal_transition_end,
            "internal_transition_start": self.internal_transition_start,
            "organism_state_receipt_sha256": (
                self.organism_state_receipt_sha256
            ),
            "origin": self.origin.value,
            "schema": ORDERED_DREAM_SCHEMA,
            "source_latest_external_time_end": _fraction_text(
                self.source_latest_external_time_end
            ),
            "source_occurrence_receipt_sha256s": list(
                self.source_occurrence_receipt_sha256s
            ),
            "source_relation_receipt_sha256s": list(
                self.source_relation_receipt_sha256s
            ),
            "transitions": [
                transition.record() for transition in self.transitions
            ],
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class OrganismWakeTestRecord:
    dream_receipt_sha256: str
    action_intent_receipt_sha256: str
    origin: OriginState
    state: str
    execution_receipt_sha256: str | None
    world_execution_receipt_sha256: str | None
    consequence_learning_receipt_sha256: str | None
    consequence_episode_receipt_sha256: str | None
    consequence_world_observation_receipt_sha256: str | None
    consequence_origin: OriginState | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_intent_receipt_sha256": (
                self.action_intent_receipt_sha256
            ),
            "consequence_episode_receipt_sha256": (
                self.consequence_episode_receipt_sha256
            ),
            "consequence_learning_receipt_sha256": (
                self.consequence_learning_receipt_sha256
            ),
            "consequence_origin": (
                self.consequence_origin.value
                if self.consequence_origin is not None
                else None
            ),
            "consequence_world_observation_receipt_sha256": (
                self.consequence_world_observation_receipt_sha256
            ),
            "dream_receipt_sha256": self.dream_receipt_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "origin": self.origin.value,
            "schema": WAKE_SCHEMA,
            "state": self.state,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class OrganismWeaveRecord:
    wake_test_receipt_sha256: str
    dream_receipt_sha256: str
    support_tapestry_receipt_sha256s: tuple[str, ...]
    organism_state_receipt_sha256: str
    action_intent_receipt_sha256: str
    execution_receipt_sha256: str
    world_execution_receipt_sha256: str
    consequence_learning_receipt_sha256: str
    consequence_world_observation_receipt_sha256: str
    expression_origin: str
    consequence_origin: OriginState
    stored_language_content: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_intent_receipt_sha256": (
                self.action_intent_receipt_sha256
            ),
            "consequence_learning_receipt_sha256": (
                self.consequence_learning_receipt_sha256
            ),
            "consequence_origin": self.consequence_origin.value,
            "consequence_world_observation_receipt_sha256": (
                self.consequence_world_observation_receipt_sha256
            ),
            "dream_receipt_sha256": self.dream_receipt_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "expression_origin": self.expression_origin,
            "organism_state_receipt_sha256": (
                self.organism_state_receipt_sha256
            ),
            "schema": WEAVE_SCHEMA,
            "stored_language_content": self.stored_language_content,
            "support_tapestry_receipt_sha256s": list(
                self.support_tapestry_receipt_sha256s
            ),
            "wake_test_receipt_sha256": (
                self.wake_test_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


GrowthRecord = (
    OrganismDreamRecord
    | OrganismOrderedDreamRecord
    | OrganismWakeTestRecord
    | OrganismWeaveRecord
)


@dataclass(frozen=True, slots=True)
class PreparedDreamWakeWeaveMutation:
    kind: str
    before_state_sha256: str
    prior_record_receipt_sha256: str | None
    staged_record: GrowthRecord
    staged_internal_transition_cursor: int
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "before_state_sha256": self.before_state_sha256,
            "kind": self.kind,
            "prior_record_receipt_sha256": (
                self.prior_record_receipt_sha256
            ),
            "schema": PREPARED_SCHEMA,
            "staged_internal_transition_cursor": (
                self.staged_internal_transition_cursor
            ),
            "staged_record": self.staged_record.record(),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class DreamWakeWeaveUndo:
    prepared: PreparedDreamWakeWeaveMutation
    prior_record: GrowthRecord | None
    prior_internal_transition_cursor: int
    committed_state_sha256: str
    _owner_authority: object = field(repr=False, compare=False)


class OrganismDreamWakeWeaveOwner:
    """Own one bounded, non-sensory dream/wake/weave transaction at a time."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: DreamWakeWeaveProfile,
        tapestry_owner: object,
        structural_state_owner: object,
        learning_owner: object,
        action_intent_owner: object,
        action_execution_authority: object,
    ) -> None:
        if not isinstance(profile, DreamWakeWeaveProfile):
            raise TypeError("dream/wake/weave profile is not typed")
        profile.verify()
        for authority, attributes, label in (
            (tapestry_owner, ("tapestries", "relations"), "tapestry"),
            (
                structural_state_owner,
                ("current_state",),
                "whole-organism structural state",
            ),
            (learning_owner, ("records",), "whole-organism learning"),
            (
                action_intent_owner,
                ("verify_live",),
                "embodied action intent",
            ),
            (
                action_execution_authority,
                ("verify",),
                "embodied action execution",
            ),
        ):
            if any(not hasattr(authority, name) for name in attributes):
                raise TypeError(
                    f"dream/wake/weave requires {label} authority"
                )
        root = _key(authority_key)
        self._dream_key = hashlib.sha256(_DREAM_DOMAIN + root).digest()
        self._ordered_dream_key = hashlib.sha256(
            _ORDERED_DREAM_DOMAIN + root
        ).digest()
        self._wake_key = hashlib.sha256(_WAKE_DOMAIN + root).digest()
        self._weave_key = hashlib.sha256(_WEAVE_DOMAIN + root).digest()
        self._prepared_key = hashlib.sha256(
            _PREPARED_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._tapestry_owner = tapestry_owner
        self._structural_state_owner = structural_state_owner
        self._learning_owner = learning_owner
        self._action_intent_owner = action_intent_owner
        self._action_execution_authority = action_execution_authority
        self._dreams: dict[str, OrganismDreamRecord] = {}
        self._ordered_dreams: dict[
            str, OrganismOrderedDreamRecord
        ] = {}
        self._ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner | None
        ) = None
        self._wake_tests: dict[str, OrganismWakeTestRecord] = {}
        self._weaves: dict[str, OrganismWeaveRecord] = {}
        self._internal_transition_cursor = 0
        self._prepared: PreparedDreamWakeWeaveMutation | None = None
        self._undo_authority = object()
        self._lock = threading.RLock()
        self._encoded_locked()

    @property
    def dreams(
        self,
    ) -> tuple[OrganismDreamRecord | OrganismOrderedDreamRecord, ...]:
        with self._lock:
            combined = self._dreams | self._ordered_dreams
            return tuple(combined[key] for key in sorted(combined))

    @property
    def ordered_dreams(self) -> tuple[OrganismOrderedDreamRecord, ...]:
        with self._lock:
            return tuple(
                self._ordered_dreams[key]
                for key in sorted(self._ordered_dreams)
            )

    @property
    def wake_tests(self) -> tuple[OrganismWakeTestRecord, ...]:
        with self._lock:
            return tuple(
                self._wake_tests[key] for key in sorted(self._wake_tests)
            )

    @property
    def weaves(self) -> tuple[OrganismWeaveRecord, ...]:
        with self._lock:
            return tuple(self._weaves[key] for key in sorted(self._weaves))

    @property
    def prepared(self) -> PreparedDreamWakeWeaveMutation | None:
        with self._lock:
            return self._prepared

    def _sign_record(self, domain: bytes, key: bytes, payload: object) -> str:
        return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()

    def _seal_dream(
        self,
        *,
        organism_state_receipt_sha256: str,
        source_tapestry_receipt_sha256s: tuple[str, ...],
        source_relation_receipt_sha256s: tuple[str, ...],
        source_latest_external_time_end: Fraction,
        transitions: tuple[InternallyExecutedDreamTransition, ...],
    ) -> OrganismDreamRecord:
        start = transitions[0].internal_transition_index
        end = transitions[-1].internal_transition_index + 1
        provisional = OrganismDreamRecord(
            organism_state_receipt_sha256=organism_state_receipt_sha256,
            source_tapestry_receipt_sha256s=(
                source_tapestry_receipt_sha256s
            ),
            source_relation_receipt_sha256s=(
                source_relation_receipt_sha256s
            ),
            source_latest_external_time_end=(
                source_latest_external_time_end
            ),
            internal_transition_start=start,
            internal_transition_end=end,
            transitions=transitions,
            origin=OriginState.INTERNALLY_SIMULATED,
            external_embodiment_state="quiescent",
            external_event_claimed=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = self._sign_record(
            _DREAM_DOMAIN,
            self._dream_key,
            provisional.payload(),
        )
        return OrganismDreamRecord(
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

    def _seal_ordered_dream(
        self,
        *,
        organism_state_receipt_sha256: str,
        chronology_authority_receipt_sha256: str,
        source_occurrence_receipt_sha256s: tuple[str, ...],
        source_relation_receipt_sha256s: tuple[str, ...],
        source_latest_external_time_end: Fraction,
        transitions: tuple[
            InternallyExecutedOrderedDreamTransition, ...
        ],
    ) -> OrganismOrderedDreamRecord:
        start = transitions[0].internal_transition_index
        end = transitions[-1].internal_transition_index + 1
        provisional = OrganismOrderedDreamRecord(
            organism_state_receipt_sha256=(
                organism_state_receipt_sha256
            ),
            chronology_authority_receipt_sha256=(
                chronology_authority_receipt_sha256
            ),
            source_occurrence_receipt_sha256s=(
                source_occurrence_receipt_sha256s
            ),
            source_relation_receipt_sha256s=(
                source_relation_receipt_sha256s
            ),
            source_latest_external_time_end=(
                source_latest_external_time_end
            ),
            internal_transition_start=start,
            internal_transition_end=end,
            transitions=transitions,
            origin=OriginState.INTERNALLY_SIMULATED,
            external_embodiment_state="quiescent",
            external_event_claimed=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = self._sign_record(
            _ORDERED_DREAM_DOMAIN,
            self._ordered_dream_key,
            provisional.payload(),
        )
        return OrganismOrderedDreamRecord(
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

    def _seal_wake(
        self,
        *,
        dream_receipt_sha256: str,
        action_intent_receipt_sha256: str,
        state: str,
        execution_receipt_sha256: str | None = None,
        world_execution_receipt_sha256: str | None = None,
        consequence_learning_receipt_sha256: str | None = None,
        consequence_episode_receipt_sha256: str | None = None,
        consequence_world_observation_receipt_sha256: str | None = None,
    ) -> OrganismWakeTestRecord:
        provisional = OrganismWakeTestRecord(
            dream_receipt_sha256=dream_receipt_sha256,
            action_intent_receipt_sha256=action_intent_receipt_sha256,
            origin=OriginState.COUNTERFACTUAL,
            state=state,
            execution_receipt_sha256=execution_receipt_sha256,
            world_execution_receipt_sha256=(
                world_execution_receipt_sha256
            ),
            consequence_learning_receipt_sha256=(
                consequence_learning_receipt_sha256
            ),
            consequence_episode_receipt_sha256=(
                consequence_episode_receipt_sha256
            ),
            consequence_world_observation_receipt_sha256=(
                consequence_world_observation_receipt_sha256
            ),
            consequence_origin=(
                OriginState.EXTERNALLY_OBSERVED
                if state == "externally_settled"
                else None
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = self._sign_record(
            _WAKE_DOMAIN,
            self._wake_key,
            provisional.payload(),
        )
        return OrganismWakeTestRecord(
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

    def _seal_weave(
        self,
        *,
        wake: OrganismWakeTestRecord,
        dream: OrganismDreamRecord | OrganismOrderedDreamRecord,
        organism_state_receipt_sha256: str,
    ) -> OrganismWeaveRecord:
        support_tapestry_receipts = (
            dream.source_tapestry_receipt_sha256s
            if isinstance(dream, OrganismDreamRecord)
            else ()
        )
        provisional = OrganismWeaveRecord(
            wake_test_receipt_sha256=wake.authority_receipt_sha256,
            dream_receipt_sha256=dream.authority_receipt_sha256,
            support_tapestry_receipt_sha256s=(
                support_tapestry_receipts
            ),
            organism_state_receipt_sha256=organism_state_receipt_sha256,
            action_intent_receipt_sha256=(
                wake.action_intent_receipt_sha256
            ),
            execution_receipt_sha256=wake.execution_receipt_sha256 or "",
            world_execution_receipt_sha256=(
                wake.world_execution_receipt_sha256 or ""
            ),
            consequence_learning_receipt_sha256=(
                wake.consequence_learning_receipt_sha256 or ""
            ),
            consequence_world_observation_receipt_sha256=(
                wake.consequence_world_observation_receipt_sha256 or ""
            ),
            expression_origin="organism_originated_embodied_action",
            consequence_origin=OriginState.EXTERNALLY_OBSERVED,
            stored_language_content=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = self._sign_record(
            _WEAVE_DOMAIN,
            self._weave_key,
            provisional.payload(),
        )
        return OrganismWeaveRecord(
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

    def _tapestry_maps(self) -> tuple[dict[str, object], dict[str, object]]:
        tapestries = tuple(self._tapestry_owner.tapestries)
        relations = tuple(self._tapestry_owner.relations)
        tapestry_map = {
            value.authority_receipt_sha256: value for value in tapestries
        }
        relation_map = {
            value.authority_receipt_sha256: value for value in relations
        }
        if len(tapestry_map) != len(tapestries):
            raise ValueError("tapestry authority repeats a receipt")
        if len(relation_map) != len(relations):
            raise ValueError("tapestry relation authority repeats a receipt")
        return tapestry_map, relation_map

    def _verify_current_structural_state(self, value: object) -> str:
        current = self._structural_state_owner.current_state
        if value != current:
            raise ValueError("dream/weave crossed current organism state")
        receipt = _sha(
            value.authority_receipt_sha256,
            "whole-organism structural state",
        )
        try:
            provenance = json.loads(value.provenance_json)
        except (AttributeError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(
                "whole-organism structural provenance changed"
            ) from error
        if (
            not isinstance(provenance, dict)
            or provenance.get("origin")
            != "settled_whole_organism_episode"
        ):
            raise ValueError(
                "dream/weave requires settled organism perturbation"
            )
        return receipt

    def _relation_candidates(self) -> tuple[object, ...]:
        tapestry_map, relation_map = self._tapestry_maps()
        candidates = tuple(
            relation_map[key] for key in sorted(relation_map)
        )
        for relation in candidates:
            if (
                relation.source_tapestry_receipt_sha256
                not in tapestry_map
                or relation.target_tapestry_receipt_sha256
                not in tapestry_map
            ):
                raise ValueError(
                    "tapestry relation left retained tapestry custody"
                )
        return candidates

    @staticmethod
    def _ordered_maps(
        owner: OrganismOrderedLivedExperienceOwner,
    ) -> tuple[
        tuple[object, ...],
        dict[str, object],
        dict[str, object],
    ]:
        if not isinstance(owner, OrganismOrderedLivedExperienceOwner):
            raise TypeError(
                "ordered dream requires typed ordered lived-experience "
                "authority"
            )
        before = owner.snapshot_encoded()
        occurrences = tuple(owner.occurrences)
        relations = tuple(owner.relations)
        if owner.snapshot_encoded() != before:
            raise RuntimeError(
                "ordered lived-experience changed during dream custody"
            )
        occurrence_map = {
            value.authority_receipt_sha256: value
            for value in occurrences
        }
        relation_map = {
            value.authority_receipt_sha256: value
            for value in relations
        }
        if (
            len(occurrence_map) != len(occurrences)
            or len(relation_map) != len(relations)
        ):
            raise ValueError(
                "ordered lived-experience repeats retained authority"
            )
        return relations, occurrence_map, relation_map

    @staticmethod
    def _root_custody_receipts(occurrence: object) -> tuple[str, ...]:
        roots = tuple(occurrence.full_field_roots)
        if not roots:
            raise ValueError(
                "ordered dream occurrence lacks full-field custody"
            )
        return tuple(_digest(value.record()) for value in roots)

    def _seal_prepared(
        self,
        *,
        kind: str,
        before_state_sha256: str,
        prior_record_receipt_sha256: str | None,
        staged_record: GrowthRecord,
        staged_internal_transition_cursor: int,
    ) -> PreparedDreamWakeWeaveMutation:
        provisional = PreparedDreamWakeWeaveMutation(
            kind=kind,
            before_state_sha256=before_state_sha256,
            prior_record_receipt_sha256=prior_record_receipt_sha256,
            staged_record=staged_record,
            staged_internal_transition_cursor=(
                staged_internal_transition_cursor
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = self._sign_record(
            _PREPARED_DOMAIN,
            self._prepared_key,
            provisional.payload(),
        )
        return PreparedDreamWakeWeaveMutation(
            kind=provisional.kind,
            before_state_sha256=provisional.before_state_sha256,
            prior_record_receipt_sha256=(
                provisional.prior_record_receipt_sha256
            ),
            staged_record=provisional.staged_record,
            staged_internal_transition_cursor=(
                provisional.staged_internal_transition_cursor
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def prepare_dream(
        self,
        *,
        organism_state: object,
    ) -> PreparedDreamWakeWeaveMutation | None:
        """Prepare bounded internal re-entry or remain exactly quiescent."""

        organism_receipt = self._verify_current_structural_state(
            organism_state
        )
        candidates = self._relation_candidates()
        if not candidates:
            return None
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("one growth mutation is already prepared")
            if (
                len(self._dreams) + len(self._ordered_dreams)
                >= self._profile.max_dreams
            ):
                raise RuntimeError("dream capacity exhausted")
            count = min(
                len(candidates),
                self._profile.max_transitions_per_dream,
            )
            offset = self._internal_transition_cursor % len(candidates)
            selected = tuple(
                candidates[(offset + index) % len(candidates)]
                for index in range(count)
            )
            transitions = tuple(
                InternallyExecutedDreamTransition(
                    internal_transition_index=(
                        self._internal_transition_cursor + index
                    ),
                    source_tapestry_receipt_sha256=(
                        relation.target_tapestry_receipt_sha256
                        if (
                            self._internal_transition_cursor + index
                        )
                        % 2
                        else relation.source_tapestry_receipt_sha256
                    ),
                    target_tapestry_receipt_sha256=(
                        relation.source_tapestry_receipt_sha256
                        if (
                            self._internal_transition_cursor + index
                        )
                        % 2
                        else relation.target_tapestry_receipt_sha256
                    ),
                    support_relation_receipt_sha256=(
                        relation.authority_receipt_sha256
                    ),
                    origin=OriginState.INTERNALLY_SIMULATED,
                )
                for index, relation in enumerate(selected)
            )
            tapestry_map, _relation_map = self._tapestry_maps()
            tapestry_receipts = tuple(sorted({
                value
                for transition in transitions
                for value in (
                    transition.source_tapestry_receipt_sha256,
                    transition.target_tapestry_receipt_sha256,
                )
            }))
            latest_external = max(
                tapestry_map[receipt].observation.target_time_end
                for receipt in tapestry_receipts
            )
            relation_receipts = tuple(sorted({
                transition.support_relation_receipt_sha256
                for transition in transitions
            }))
            dream = self._seal_dream(
                organism_state_receipt_sha256=organism_receipt,
                source_tapestry_receipt_sha256s=tapestry_receipts,
                source_relation_receipt_sha256s=relation_receipts,
                source_latest_external_time_end=latest_external,
                transitions=transitions,
            )
            before = self._committed_state_sha256_locked()
            prepared = self._seal_prepared(
                kind="dream",
                before_state_sha256=before,
                prior_record_receipt_sha256=None,
                staged_record=dream,
                staged_internal_transition_cursor=(
                    dream.internal_transition_end
                ),
            )
            self._validate_staged_locked(prepared)
            self._prepared = prepared
            self._encoded_locked()
            return prepared

    def prepare_ordered_dream(
        self,
        *,
        organism_state: object,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner
        ),
    ) -> PreparedDreamWakeWeaveMutation | None:
        """Prepare exact forward traversal of retained cross-THING life."""

        organism_receipt = self._verify_current_structural_state(
            organism_state
        )
        relations, occurrence_map, _relation_map = self._ordered_maps(
            ordered_lived_experience_owner
        )
        candidates = tuple(
            relation for relation in relations if not relation.same_thing
        )
        if not candidates:
            return None
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("one growth mutation is already prepared")
            if (
                len(self._dreams) + len(self._ordered_dreams)
                >= self._profile.max_dreams
            ):
                raise RuntimeError("dream capacity exhausted")
            if (
                self._ordered_lived_experience_owner is not None
                and self._ordered_lived_experience_owner
                is not ordered_lived_experience_owner
            ):
                raise ValueError(
                    "ordered dream crossed lived-experience authority"
                )
            offset = self._internal_transition_cursor % len(candidates)
            selected = candidates[
                offset:offset + self._profile.max_transitions_per_dream
            ]
            transitions = tuple(
                InternallyExecutedOrderedDreamTransition(
                    internal_transition_index=(
                        self._internal_transition_cursor + index
                    ),
                    chronology_authority_receipt_sha256=(
                        relation.chronology_authority_receipt_sha256
                    ),
                    chronology_sequence=relation.chronology_sequence,
                    predecessor_relation_receipt_sha256=(
                        relation.predecessor_relation_receipt_sha256
                    ),
                    source_occurrence_receipt_sha256=(
                        relation.source_occurrence_receipt_sha256
                    ),
                    target_occurrence_receipt_sha256=(
                        relation.target_occurrence_receipt_sha256
                    ),
                    source_thing_id=relation.source_thing_id,
                    target_thing_id=relation.target_thing_id,
                    source_time_start=occurrence_map[
                        relation.source_occurrence_receipt_sha256
                    ].source_time_start,
                    source_time_end=occurrence_map[
                        relation.source_occurrence_receipt_sha256
                    ].source_time_end,
                    target_time_start=occurrence_map[
                        relation.target_occurrence_receipt_sha256
                    ].source_time_start,
                    target_time_end=occurrence_map[
                        relation.target_occurrence_receipt_sha256
                    ].source_time_end,
                    source_full_field_root_receipt_sha256s=(
                        self._root_custody_receipts(occurrence_map[
                            relation.source_occurrence_receipt_sha256
                        ])
                    ),
                    target_full_field_root_receipt_sha256s=(
                        self._root_custody_receipts(occurrence_map[
                            relation.target_occurrence_receipt_sha256
                        ])
                    ),
                    support_relation_receipt_sha256=(
                        relation.authority_receipt_sha256
                    ),
                    origin=OriginState.INTERNALLY_SIMULATED,
                )
                for index, relation in enumerate(selected)
            )
            occurrence_receipts = tuple(
                receipt
                for transition in transitions
                for receipt in (
                    transition.source_occurrence_receipt_sha256,
                    transition.target_occurrence_receipt_sha256,
                )
            )
            relation_receipts = tuple(
                transition.support_relation_receipt_sha256
                for transition in transitions
            )
            latest_external = max(
                transition.target_time_end
                for transition in transitions
            )
            dream = self._seal_ordered_dream(
                organism_state_receipt_sha256=organism_receipt,
                chronology_authority_receipt_sha256=(
                    ordered_lived_experience_owner
                    .chronology_authority_receipt_sha256
                ),
                source_occurrence_receipt_sha256s=(
                    occurrence_receipts
                ),
                source_relation_receipt_sha256s=relation_receipts,
                source_latest_external_time_end=latest_external,
                transitions=transitions,
            )
            prepared = self._seal_prepared(
                kind="dream",
                before_state_sha256=(
                    self._committed_state_sha256_locked()
                ),
                prior_record_receipt_sha256=None,
                staged_record=dream,
                staged_internal_transition_cursor=(
                    dream.internal_transition_end
                ),
            )
            prior_owner = self._ordered_lived_experience_owner
            self._ordered_lived_experience_owner = (
                ordered_lived_experience_owner
            )
            try:
                self._validate_staged_locked(prepared)
                self._prepared = prepared
                self._encoded_locked()
            except BaseException:
                self._ordered_lived_experience_owner = prior_owner
                raise
            return prepared

    def _retained_dream_locked(
        self,
        dream_receipt_sha256: str,
    ) -> OrganismDreamRecord | OrganismOrderedDreamRecord | None:
        """Return one verified retained dream without changing its geometry."""

        legacy = self._dreams.get(dream_receipt_sha256)
        ordered = self._ordered_dreams.get(dream_receipt_sha256)
        if legacy is not None and ordered is not None:
            raise RuntimeError("dream receipt crosses retained dream kinds")
        dream = legacy if legacy is not None else ordered
        if isinstance(dream, OrganismDreamRecord):
            self._verify_dream(dream)
        elif isinstance(dream, OrganismOrderedDreamRecord):
            self._verify_ordered_dream(dream)
        return dream

    def prepare_wake_test(
        self,
        *,
        dream_receipt_sha256: str,
        action_intent: object,
    ) -> PreparedDreamWakeWeaveMutation:
        """Bind a dream to one live embodied intent without claiming outcome."""

        _sha(dream_receipt_sha256, "wake-test dream")
        if not self._action_intent_owner.verify_live(action_intent):
            raise ValueError("wake test requires one live embodied intent")
        intent_receipt = _sha(
            action_intent.authority_receipt_sha256,
            "wake-test action intent",
        )
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("one growth mutation is already prepared")
            dream = self._retained_dream_locked(
                dream_receipt_sha256
            )
            if dream is None:
                raise ValueError("wake test names no retained dream")
            if len(self._wake_tests) >= self._profile.max_wake_tests:
                raise RuntimeError("wake-test capacity exhausted")
            if any(
                value.dream_receipt_sha256 == dream_receipt_sha256
                for value in self._wake_tests.values()
            ):
                raise ValueError("dream already has a wake test")
            wake = self._seal_wake(
                dream_receipt_sha256=dream_receipt_sha256,
                action_intent_receipt_sha256=intent_receipt,
                state="unresolved",
            )
            prepared = self._seal_prepared(
                kind="wake_test",
                before_state_sha256=self._committed_state_sha256_locked(),
                prior_record_receipt_sha256=None,
                staged_record=wake,
                staged_internal_transition_cursor=(
                    self._internal_transition_cursor
                ),
            )
            self._validate_staged_locked(prepared)
            self._prepared = prepared
            self._encoded_locked()
            return prepared

    def _require_learning_record(self, value: object) -> object:
        records = tuple(self._learning_owner.records)
        receipt = _sha(
            value.authority_receipt_sha256,
            "wake consequence learning",
        )
        matches = tuple(
            record for record in records
            if record.authority_receipt_sha256 == receipt
        )
        if len(matches) != 1 or matches[0] != value:
            raise ValueError(
                "wake consequence lacks retained learning custody"
            )
        return matches[0]

    def prepare_wake_resolution(
        self,
        *,
        wake_test_receipt_sha256: str,
        execution: object,
        consequence_learning_record: object,
    ) -> PreparedDreamWakeWeaveMutation:
        """Resolve only from a later applied action and external consequence."""

        _sha(wake_test_receipt_sha256, "wake-test authority")
        self._action_execution_authority.verify(execution)
        learning = self._require_learning_record(
            consequence_learning_record
        )
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("one growth mutation is already prepared")
            prior = self._wake_tests.get(wake_test_receipt_sha256)
            if prior is None or prior.state != "unresolved":
                raise ValueError("wake test is not unresolved")
            dream = self._retained_dream_locked(
                prior.dream_receipt_sha256
            )
            if dream is None:
                raise ValueError("wake test left retained dream custody")
            if (
                execution.intent_receipt_sha256
                != prior.action_intent_receipt_sha256
                or execution.world_execution_receipt_sha256
                != learning.story.action_execution_receipt_sha256
                or execution.actual_outcome_settlement_receipt_sha256
                != learning.story.settlement_authority_receipt_sha256
                or learning.partition.world_observation_receipt_sha256
                != learning.story.world_observation_receipt_sha256
                or learning.story.source_time_start
                < dream.source_latest_external_time_end
            ):
                raise ValueError(
                    "wake consequence crossed action, settlement, or time"
                )
            wake = self._seal_wake(
                dream_receipt_sha256=prior.dream_receipt_sha256,
                action_intent_receipt_sha256=(
                    prior.action_intent_receipt_sha256
                ),
                state="externally_settled",
                execution_receipt_sha256=(
                    execution.authority_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    execution.world_execution_receipt_sha256
                ),
                consequence_learning_receipt_sha256=(
                    learning.authority_receipt_sha256
                ),
                consequence_episode_receipt_sha256=(
                    learning.story.episode_authority_receipt_sha256
                ),
                consequence_world_observation_receipt_sha256=(
                    learning.story.world_observation_receipt_sha256
                ),
            )
            prepared = self._seal_prepared(
                kind="wake_resolution",
                before_state_sha256=self._committed_state_sha256_locked(),
                prior_record_receipt_sha256=(
                    prior.authority_receipt_sha256
                ),
                staged_record=wake,
                staged_internal_transition_cursor=(
                    self._internal_transition_cursor
                ),
            )
            self._validate_staged_locked(prepared)
            self._prepared = prepared
            self._encoded_locked()
            return prepared

    def prepare_weave(
        self,
        *,
        wake_test_receipt_sha256: str,
        organism_state: object,
    ) -> PreparedDreamWakeWeaveMutation:
        """Prepare one receipt-only embodied expression from settled support."""

        organism_receipt = self._verify_current_structural_state(
            organism_state
        )
        _sha(wake_test_receipt_sha256, "weave wake test")
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("one growth mutation is already prepared")
            if len(self._weaves) >= self._profile.max_weaves:
                raise RuntimeError("weave capacity exhausted")
            wake = self._wake_tests.get(wake_test_receipt_sha256)
            if wake is None or wake.state != "externally_settled":
                raise ValueError(
                    "weave requires one externally settled wake test"
                )
            if any(
                value.wake_test_receipt_sha256
                == wake_test_receipt_sha256
                for value in self._weaves.values()
            ):
                raise ValueError("wake test already has a weave")
            dream = self._retained_dream_locked(
                wake.dream_receipt_sha256
            )
            if dream is None:
                raise ValueError("weave left retained dream custody")
            weave = self._seal_weave(
                wake=wake,
                dream=dream,
                organism_state_receipt_sha256=organism_receipt,
            )
            prepared = self._seal_prepared(
                kind="weave",
                before_state_sha256=self._committed_state_sha256_locked(),
                prior_record_receipt_sha256=None,
                staged_record=weave,
                staged_internal_transition_cursor=(
                    self._internal_transition_cursor
                ),
            )
            self._validate_staged_locked(prepared)
            self._prepared = prepared
            self._encoded_locked()
            return prepared

    def _record_key(self, record: GrowthRecord) -> bytes:
        if isinstance(record, OrganismDreamRecord):
            return self._dream_key
        if isinstance(record, OrganismOrderedDreamRecord):
            return self._ordered_dream_key
        if isinstance(record, OrganismWakeTestRecord):
            return self._wake_key
        if isinstance(record, OrganismWeaveRecord):
            return self._weave_key
        raise TypeError("growth record is not typed")

    def _record_domain(self, record: GrowthRecord) -> bytes:
        if isinstance(record, OrganismDreamRecord):
            return _DREAM_DOMAIN
        if isinstance(record, OrganismOrderedDreamRecord):
            return _ORDERED_DREAM_DOMAIN
        if isinstance(record, OrganismWakeTestRecord):
            return _WAKE_DOMAIN
        if isinstance(record, OrganismWeaveRecord):
            return _WEAVE_DOMAIN
        raise TypeError("growth record is not typed")

    def _verify_record_authority(self, record: GrowthRecord) -> None:
        _sha(record.authority_hmac_sha256, "growth record HMAC")
        _sha(record.authority_receipt_sha256, "growth record authority")
        expected = self._sign_record(
            self._record_domain(record),
            self._record_key(record),
            record.payload(),
        )
        if (
            not hmac.compare_digest(
                expected,
                record.authority_hmac_sha256,
            )
            or record.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": record.payload(),
            })
        ):
            raise ValueError("growth record authority changed")

    def _verify_dream(self, dream: OrganismDreamRecord) -> None:
        self._verify_record_authority(dream)
        if (
            dream.origin is not OriginState.INTERNALLY_SIMULATED
            or dream.external_embodiment_state != "quiescent"
            or dream.external_event_claimed
            or not dream.transitions
            or len(dream.transitions)
            > self._profile.max_transitions_per_dream
            or dream.internal_transition_end
            != dream.internal_transition_start + len(dream.transitions)
        ):
            raise ValueError("dream provenance or extent changed")
        _sha(
            dream.organism_state_receipt_sha256,
            "dream organism state",
        )
        tapestry_map, relation_map = self._tapestry_maps()
        if (
            dream.source_tapestry_receipt_sha256s
            != tuple(sorted(set(
                dream.source_tapestry_receipt_sha256s
            )))
            or dream.source_relation_receipt_sha256s
            != tuple(sorted(set(
                dream.source_relation_receipt_sha256s
            )))
        ):
            raise ValueError("dream source order changed")
        for offset, transition in enumerate(dream.transitions):
            if (
                transition.origin
                is not OriginState.INTERNALLY_SIMULATED
                or transition.internal_transition_index
                != dream.internal_transition_start + offset
                or transition.source_tapestry_receipt_sha256
                not in tapestry_map
                or transition.target_tapestry_receipt_sha256
                not in tapestry_map
            ):
                raise ValueError("dream internal transition changed")
            relation = relation_map.get(
                transition.support_relation_receipt_sha256
            )
            if relation is None or {
                relation.source_tapestry_receipt_sha256,
                relation.target_tapestry_receipt_sha256,
            } != {
                transition.source_tapestry_receipt_sha256,
                transition.target_tapestry_receipt_sha256,
            }:
                raise ValueError(
                    "dream transition lacks retained relation custody"
                )
        latest = max(
            tapestry_map[receipt].observation.target_time_end
            for receipt in dream.source_tapestry_receipt_sha256s
        )
        if latest != dream.source_latest_external_time_end:
            raise ValueError("dream source causal time changed")

    def _verify_ordered_dream(
        self,
        dream: OrganismOrderedDreamRecord,
    ) -> None:
        self._verify_record_authority(dream)
        owner = self._ordered_lived_experience_owner
        if owner is None:
            raise ValueError(
                "ordered dream lacks lived-experience authority"
            )
        relations, occurrence_map, relation_map = self._ordered_maps(
            owner
        )
        relation_positions = {
            value.authority_receipt_sha256: index
            for index, value in enumerate(relations)
        }
        if (
            dream.origin is not OriginState.INTERNALLY_SIMULATED
            or dream.external_embodiment_state != "quiescent"
            or dream.external_event_claimed
            or not dream.transitions
            or len(dream.transitions)
            > self._profile.max_transitions_per_dream
            or dream.internal_transition_end
            != dream.internal_transition_start + len(dream.transitions)
            or dream.chronology_authority_receipt_sha256
            != owner.chronology_authority_receipt_sha256
        ):
            raise ValueError("ordered dream provenance or extent changed")
        _sha(
            dream.organism_state_receipt_sha256,
            "ordered dream organism state",
        )
        expected_occurrences: list[str] = []
        expected_relations: list[str] = []
        prior_position: int | None = None
        for offset, transition in enumerate(dream.transitions):
            relation = relation_map.get(
                transition.support_relation_receipt_sha256
            )
            source = occurrence_map.get(
                transition.source_occurrence_receipt_sha256
            )
            target = occurrence_map.get(
                transition.target_occurrence_receipt_sha256
            )
            position = relation_positions.get(
                transition.support_relation_receipt_sha256
            )
            if (
                transition.origin
                is not OriginState.INTERNALLY_SIMULATED
                or transition.internal_transition_index
                != dream.internal_transition_start + offset
                or relation is None
                or source is None
                or target is None
                or relation.same_thing
                or position is None
                or (
                    prior_position is not None
                    and position <= prior_position
                )
                or transition.chronology_authority_receipt_sha256
                != relation.chronology_authority_receipt_sha256
                or transition.chronology_sequence
                != relation.chronology_sequence
                or transition.predecessor_relation_receipt_sha256
                != relation.predecessor_relation_receipt_sha256
                or transition.source_occurrence_receipt_sha256
                != relation.source_occurrence_receipt_sha256
                or transition.target_occurrence_receipt_sha256
                != relation.target_occurrence_receipt_sha256
                or transition.source_thing_id != relation.source_thing_id
                or transition.target_thing_id != relation.target_thing_id
                or transition.source_time_start
                != source.source_time_start
                or transition.source_time_end != source.source_time_end
                or transition.target_time_start
                != target.source_time_start
                or transition.target_time_end != target.source_time_end
                or transition.source_full_field_root_receipt_sha256s
                != self._root_custody_receipts(source)
                or transition.target_full_field_root_receipt_sha256s
                != self._root_custody_receipts(target)
            ):
                raise ValueError(
                    "ordered dream transition left exact lived custody"
                )
            prior_position = position
            expected_occurrences.extend((
                source.authority_receipt_sha256,
                target.authority_receipt_sha256,
            ))
            expected_relations.append(
                relation.authority_receipt_sha256
            )
        if (
            dream.source_occurrence_receipt_sha256s
            != tuple(expected_occurrences)
            or dream.source_relation_receipt_sha256s
            != tuple(expected_relations)
            or dream.source_latest_external_time_end
            != max(
                transition.target_time_end
                for transition in dream.transitions
            )
        ):
            raise ValueError("ordered dream source custody changed")

    def _verify_wake(self, wake: OrganismWakeTestRecord) -> None:
        self._verify_record_authority(wake)
        dream = self._retained_dream_locked(
            wake.dream_receipt_sha256
        )
        if (
            wake.origin is not OriginState.COUNTERFACTUAL
            or dream is None
        ):
            raise ValueError("wake-test provenance changed")
        _sha(wake.action_intent_receipt_sha256, "wake-test action")
        optional = (
            wake.execution_receipt_sha256,
            wake.world_execution_receipt_sha256,
            wake.consequence_learning_receipt_sha256,
            wake.consequence_episode_receipt_sha256,
            wake.consequence_world_observation_receipt_sha256,
        )
        if wake.state == "unresolved":
            if any(value is not None for value in optional):
                raise ValueError(
                    "unresolved wake test fabricated consequence"
                )
            if wake.consequence_origin is not None:
                raise ValueError(
                    "unresolved wake test fabricated external origin"
                )
        elif wake.state == "externally_settled":
            if (
                any(value is None for value in optional)
                or wake.consequence_origin
                is not OriginState.EXTERNALLY_OBSERVED
            ):
                raise ValueError(
                    "settled wake test lacks external consequence"
                )
            for index, value in enumerate(optional):
                _sha(value, f"wake-test consequence {index}")
        else:
            raise ValueError("wake-test state changed")

    def _verify_weave(self, weave: OrganismWeaveRecord) -> None:
        self._verify_record_authority(weave)
        wake = self._wake_tests.get(weave.wake_test_receipt_sha256)
        dream = self._retained_dream_locked(
            weave.dream_receipt_sha256
        )
        expected_tapestry_receipts = (
            dream.source_tapestry_receipt_sha256s
            if isinstance(dream, OrganismDreamRecord)
            else ()
        )
        if (
            wake is None
            or wake.state != "externally_settled"
            or dream is None
            or wake.dream_receipt_sha256
            != dream.authority_receipt_sha256
            or weave.support_tapestry_receipt_sha256s
            != expected_tapestry_receipts
            or weave.action_intent_receipt_sha256
            != wake.action_intent_receipt_sha256
            or weave.execution_receipt_sha256
            != wake.execution_receipt_sha256
            or weave.world_execution_receipt_sha256
            != wake.world_execution_receipt_sha256
            or weave.consequence_learning_receipt_sha256
            != wake.consequence_learning_receipt_sha256
            or weave.consequence_world_observation_receipt_sha256
            != wake.consequence_world_observation_receipt_sha256
            or weave.expression_origin
            != "organism_originated_embodied_action"
            or weave.consequence_origin
            is not OriginState.EXTERNALLY_OBSERVED
            or weave.stored_language_content
        ):
            raise ValueError("weave custody or expression boundary changed")
        _sha(
            weave.organism_state_receipt_sha256,
            "weave organism state",
        )

    def _verify_prepared(
        self,
        prepared: PreparedDreamWakeWeaveMutation,
    ) -> None:
        if not isinstance(prepared, PreparedDreamWakeWeaveMutation):
            raise TypeError("prepared growth mutation is not typed")
        if prepared.kind not in {
            "dream",
            "wake_test",
            "wake_resolution",
            "weave",
        }:
            raise ValueError("prepared growth kind changed")
        _sha(prepared.before_state_sha256, "prepared prior state")
        _nonnegative(
            prepared.staged_internal_transition_cursor,
            "prepared internal transition cursor",
        )
        if prepared.prior_record_receipt_sha256 is not None:
            _sha(
                prepared.prior_record_receipt_sha256,
                "prepared prior record",
            )
        self._verify_record_authority(prepared.staged_record)
        expected = self._sign_record(
            _PREPARED_DOMAIN,
            self._prepared_key,
            prepared.payload(),
        )
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
            raise ValueError("prepared growth authority changed")

    def _committed_body_locked(self) -> dict[str, object]:
        return {
            "dreams": [
                self._dreams[key].record() for key in sorted(self._dreams)
            ],
            "internal_transition_cursor": self._internal_transition_cursor,
            "mounted_mechanisms": {
                "dream": (
                    "perturbed"
                    if self._dreams or self._ordered_dreams
                    else "quiescent"
                ),
                "wake_test": (
                    "perturbed" if self._wake_tests else "quiescent"
                ),
                "weave": (
                    "perturbed" if self._weaves else "quiescent"
                ),
            },
            "ordered_dreams": [
                self._ordered_dreams[key].record()
                for key in sorted(self._ordered_dreams)
            ],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "wake_tests": [
                self._wake_tests[key].record()
                for key in sorted(self._wake_tests)
            ],
            "weaves": [
                self._weaves[key].record() for key in sorted(self._weaves)
            ],
        }

    def _committed_state_sha256_locked(self) -> str:
        return _digest(self._committed_body_locked())

    def _state_body_locked(self) -> dict[str, object]:
        return self._committed_body_locked() | {
            "prepared": (
                self._prepared.record()
                if self._prepared is not None
                else None
            )
        }

    def _encoded_locked(self) -> bytes:
        body = self._state_body_locked()
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
            raise RuntimeError("dream/wake/weave state capacity exhausted")
        return encoded

    def _apply_staged_locked(
        self,
        prepared: PreparedDreamWakeWeaveMutation,
    ) -> GrowthRecord | None:
        record = prepared.staged_record
        prior: GrowthRecord | None = None
        if isinstance(record, OrganismDreamRecord):
            self._dreams[record.authority_receipt_sha256] = record
        elif isinstance(record, OrganismOrderedDreamRecord):
            self._ordered_dreams[
                record.authority_receipt_sha256
            ] = record
        elif isinstance(record, OrganismWakeTestRecord):
            if prepared.prior_record_receipt_sha256 is not None:
                prior = self._wake_tests.pop(
                    prepared.prior_record_receipt_sha256
                )
            self._wake_tests[record.authority_receipt_sha256] = record
        elif isinstance(record, OrganismWeaveRecord):
            self._weaves[record.authority_receipt_sha256] = record
        else:
            raise TypeError("prepared growth record is not typed")
        self._internal_transition_cursor = (
            prepared.staged_internal_transition_cursor
        )
        return prior

    def _remove_staged_locked(
        self,
        prepared: PreparedDreamWakeWeaveMutation,
        prior: GrowthRecord | None,
        prior_cursor: int,
    ) -> None:
        record = prepared.staged_record
        target = (
            self._dreams
            if isinstance(record, OrganismDreamRecord)
            else self._ordered_dreams
            if isinstance(record, OrganismOrderedDreamRecord)
            else self._wake_tests
            if isinstance(record, OrganismWakeTestRecord)
            else self._weaves
        )
        if target.pop(record.authority_receipt_sha256, None) != record:
            raise ValueError("committed growth mutation is not current")
        if prior is not None:
            if not isinstance(prior, OrganismWakeTestRecord):
                raise TypeError("growth rollback prior record changed")
            self._wake_tests[prior.authority_receipt_sha256] = prior
        self._internal_transition_cursor = prior_cursor

    def _validate_staged_locked(
        self,
        prepared: PreparedDreamWakeWeaveMutation,
    ) -> None:
        prior_cursor = self._internal_transition_cursor
        prior = self._apply_staged_locked(prepared)
        active = self._prepared
        self._prepared = prepared
        try:
            self._verify_all_locked()
            self._encoded_locked()
        finally:
            self._prepared = active
            self._remove_staged_locked(
                prepared,
                prior,
                prior_cursor,
            )

    def _verify_all_locked(self) -> None:
        if (
            len(self._dreams) + len(self._ordered_dreams)
            > self._profile.max_dreams
            or len(self._wake_tests) > self._profile.max_wake_tests
            or len(self._weaves) > self._profile.max_weaves
        ):
            raise RuntimeError("dream/wake/weave record capacity exhausted")
        for dream in self._dreams.values():
            self._verify_dream(dream)
        for dream in self._ordered_dreams.values():
            self._verify_ordered_dream(dream)
        for wake in self._wake_tests.values():
            self._verify_wake(wake)
        for weave in self._weaves.values():
            self._verify_weave(weave)
        if self._prepared is not None:
            self._verify_prepared(self._prepared)

    def rebind_restored_authorities(
        self,
        *,
        structural_state_owner: object,
        learning_owner: object,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner | None
        ),
    ) -> None:
        """Atomically reconnect equivalent authorities replaced by rollback."""

        if not hasattr(structural_state_owner, "current_state"):
            raise TypeError(
                "dream/wake/weave requires structural-state authority"
            )
        if not hasattr(learning_owner, "records"):
            raise TypeError(
                "dream/wake/weave requires whole-organism learning authority"
            )
        if (
            ordered_lived_experience_owner is not None
            and not isinstance(
                ordered_lived_experience_owner,
                OrganismOrderedLivedExperienceOwner,
            )
        ):
            raise TypeError(
                "dream/wake/weave requires ordered lived-experience authority"
            )
        with self._lock:
            prior = (
                self._structural_state_owner,
                self._learning_owner,
                self._ordered_lived_experience_owner,
            )
            if structural_state_owner.current_state != prior[0].current_state:
                raise ValueError(
                    "restored structural-state authority changed current state"
                )
            self._structural_state_owner = structural_state_owner
            self._learning_owner = learning_owner
            self._ordered_lived_experience_owner = (
                ordered_lived_experience_owner
            )
            try:
                retained_learning_receipts = {
                    record.authority_receipt_sha256
                    for record in learning_owner.records
                }
                for wake in self._wake_tests.values():
                    if (
                        wake.state == "externally_settled"
                        and wake.consequence_learning_receipt_sha256
                        not in retained_learning_receipts
                    ):
                        raise ValueError(
                            "restored learning authority lost wake consequence"
                        )
                self._verify_all_locked()
                self._encoded_locked()
            except BaseException:
                (
                    self._structural_state_owner,
                    self._learning_owner,
                    self._ordered_lived_experience_owner,
                ) = prior
                raise

    def commit(
        self,
        prepared: PreparedDreamWakeWeaveMutation,
    ) -> DreamWakeWeaveUndo:
        with self._lock:
            self._verify_prepared(prepared)
            if isinstance(
                prepared.staged_record,
                OrganismOrderedDreamRecord,
            ):
                self._verify_ordered_dream(prepared.staged_record)
            if self._prepared != prepared:
                raise ValueError("prepared growth mutation is not current")
            if (
                self._committed_state_sha256_locked()
                != prepared.before_state_sha256
            ):
                raise RuntimeError("growth state changed before commit")
            prior_cursor = self._internal_transition_cursor
            prior = self._apply_staged_locked(prepared)
            self._prepared = None
            try:
                self._verify_all_locked()
                self._encoded_locked()
            except BaseException:
                self._remove_staged_locked(
                    prepared,
                    prior,
                    prior_cursor,
                )
                self._prepared = prepared
                raise
            return DreamWakeWeaveUndo(
                prepared=prepared,
                prior_record=prior,
                prior_internal_transition_cursor=prior_cursor,
                committed_state_sha256=(
                    self._committed_state_sha256_locked()
                ),
                _owner_authority=self._undo_authority,
            )

    def discard(
        self,
        prepared: PreparedDreamWakeWeaveMutation,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            if self._prepared != prepared:
                raise ValueError("prepared growth mutation is not current")
            self._prepared = None
            self._encoded_locked()

    def rollback(self, undo: DreamWakeWeaveUndo) -> None:
        if (
            not isinstance(undo, DreamWakeWeaveUndo)
            or undo._owner_authority is not self._undo_authority
        ):
            raise ValueError("growth undo authority changed")
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "cannot roll back through an in-flight growth mutation"
                )
            if (
                self._committed_state_sha256_locked()
                != undo.committed_state_sha256
            ):
                raise ValueError("committed growth mutation is not current")
            self._remove_staged_locked(
                undo.prepared,
                undo.prior_record,
                undo.prior_internal_transition_cursor,
            )
            self._verify_all_locked()
            self._encoded_locked()

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            self._verify_all_locked()
            return self._encoded_locked()

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded_locked()
            unresolved = sum(
                value.state == "unresolved"
                for value in self._wake_tests.values()
            )
            return {
                "dreams": len(self._dreams) + len(self._ordered_dreams),
                "external_event_claimed_by_dream": False,
                "internal_transition_cursor": (
                    self._internal_transition_cursor
                ),
                "mechanism_states": (
                    self._committed_body_locked()["mounted_mechanisms"]
                ),
                "prepared": (
                    self._prepared.kind
                    if self._prepared is not None
                    else None
                ),
                "schema": (
                    "guala.organism_dream_wake_weave.status.v1"
                ),
                "state_bytes": len(encoded),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "ordered_dreams": len(self._ordered_dreams),
                "unresolved_wake_tests": unresolved,
                "wake_tests": len(self._wake_tests),
                "weaves": len(self._weaves),
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: DreamWakeWeaveProfile,
        tapestry_owner: object,
        structural_state_owner: object,
        learning_owner: object,
        action_intent_owner: object,
        action_execution_authority: object,
        encoded: bytes,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner | None
        ) = None,
    ) -> "OrganismDreamWakeWeaveOwner":
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > profile.max_state_bytes
        ):
            raise ValueError("dream/wake/weave cold state is invalid")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "dream/wake/weave cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema")
            not in {ENVELOPE_SCHEMA, _LEGACY_ENVELOPE_SCHEMA}
            or _canonical(envelope) != encoded
        ):
            raise ValueError("dream/wake/weave cold envelope changed")
        body = envelope.get("body")
        current_body = {
            "dreams",
            "internal_transition_cursor",
            "mounted_mechanisms",
            "ordered_dreams",
            "prepared",
            "profile",
            "schema",
            "wake_tests",
            "weaves",
        }
        legacy_body = current_body - {"ordered_dreams"}
        legacy = envelope.get("schema") == _LEGACY_ENVELOPE_SCHEMA
        if (
            not isinstance(body, dict)
            or set(body) != (legacy_body if legacy else current_body)
            or body.get("schema")
            != (_LEGACY_STATE_SCHEMA if legacy else STATE_SCHEMA)
            or body.get("profile") != profile.record()
            or not isinstance(body.get("dreams"), list)
            or (
                not legacy
                and not isinstance(body.get("ordered_dreams"), list)
            )
            or not isinstance(body.get("wake_tests"), list)
            or not isinstance(body.get("weaves"), list)
        ):
            raise ValueError("dream/wake/weave cold payload changed")
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            tapestry_owner=tapestry_owner,
            structural_state_owner=structural_state_owner,
            learning_owner=learning_owner,
            action_intent_owner=action_intent_owner,
            action_execution_authority=action_execution_authority,
        )
        if ordered_lived_experience_owner is not None:
            if not isinstance(
                ordered_lived_experience_owner,
                OrganismOrderedLivedExperienceOwner,
            ):
                raise TypeError(
                    "cold ordered dream requires typed lived-experience "
                    "authority"
                )
            owner._ordered_lived_experience_owner = (
                ordered_lived_experience_owner
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
                "dream/wake/weave cold state authority changed"
            )
        if legacy:
            if (
                body["dreams"]
                or body["wake_tests"]
                or body["weaves"]
                or body["prepared"] is not None
                or body["internal_transition_cursor"] != 0
                or body["mounted_mechanisms"]
                != {
                    "dream": "quiescent",
                    "wake_test": "quiescent",
                    "weave": "quiescent",
                }
            ):
                raise ValueError(
                    "populated legacy dreams have no ordered custody"
                )
            return owner
        with owner._lock:
            owner._dreams = {
                value.authority_receipt_sha256: value
                for value in (
                    owner._dream_from_raw(raw)
                    for raw in body["dreams"]
                )
            }
            owner._ordered_dreams = {
                value.authority_receipt_sha256: value
                for value in (
                    owner._ordered_dream_from_raw(raw)
                    for raw in body["ordered_dreams"]
                )
            }
            owner._wake_tests = {
                value.authority_receipt_sha256: value
                for value in (
                    owner._wake_from_raw(raw)
                    for raw in body["wake_tests"]
                )
            }
            owner._weaves = {
                value.authority_receipt_sha256: value
                for value in (
                    owner._weave_from_raw(raw)
                    for raw in body["weaves"]
                )
            }
            owner._internal_transition_cursor = _nonnegative(
                body.get("internal_transition_cursor"),
                "cold internal transition cursor",
            )
            owner._prepared = (
                owner._prepared_from_raw(body["prepared"])
                if body["prepared"] is not None
                else None
            )
            owner._verify_all_locked()
            if owner._state_body_locked() != body:
                raise ValueError(
                    "dream/wake/weave cold state changed structure"
                )
            if owner._encoded_locked() != encoded:
                raise ValueError(
                    "dream/wake/weave cold round-trip changed state"
                )
        return owner

    @staticmethod
    def _transition_from_raw(
        raw: object,
    ) -> InternallyExecutedDreamTransition:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "internal_transition_index",
                "origin",
                "schema",
                "source_tapestry_receipt_sha256",
                "support_relation_receipt_sha256",
                "target_tapestry_receipt_sha256",
            }
            or raw.get("schema") != DREAM_TRANSITION_SCHEMA
        ):
            raise ValueError("cold dream transition changed")
        return InternallyExecutedDreamTransition(
            internal_transition_index=_nonnegative(
                raw["internal_transition_index"],
                "cold dream transition index",
            ),
            source_tapestry_receipt_sha256=_sha(
                raw["source_tapestry_receipt_sha256"],
                "cold dream source tapestry",
            ),
            target_tapestry_receipt_sha256=_sha(
                raw["target_tapestry_receipt_sha256"],
                "cold dream target tapestry",
            ),
            support_relation_receipt_sha256=_sha(
                raw["support_relation_receipt_sha256"],
                "cold dream support relation",
            ),
            origin=OriginState(raw["origin"]),
        )

    @staticmethod
    def _ordered_transition_from_raw(
        raw: object,
    ) -> InternallyExecutedOrderedDreamTransition:
        expected = {
            "chronology_authority_receipt_sha256",
            "chronology_sequence",
            "internal_transition_index",
            "origin",
            "predecessor_relation_receipt_sha256",
            "schema",
            "source_full_field_root_receipt_sha256s",
            "source_occurrence_receipt_sha256",
            "source_thing_id",
            "source_time_end",
            "source_time_start",
            "support_relation_receipt_sha256",
            "target_full_field_root_receipt_sha256s",
            "target_occurrence_receipt_sha256",
            "target_thing_id",
            "target_time_end",
            "target_time_start",
        }
        if (
            not isinstance(raw, Mapping)
            or set(raw) != expected
            or raw.get("schema") != ORDERED_DREAM_TRANSITION_SCHEMA
            or not isinstance(
                raw["source_full_field_root_receipt_sha256s"],
                list,
            )
            or not isinstance(
                raw["target_full_field_root_receipt_sha256s"],
                list,
            )
        ):
            raise ValueError("cold ordered dream transition changed")
        predecessor = raw["predecessor_relation_receipt_sha256"]
        return InternallyExecutedOrderedDreamTransition(
            internal_transition_index=_nonnegative(
                raw["internal_transition_index"],
                "cold ordered dream transition index",
            ),
            chronology_authority_receipt_sha256=_sha(
                raw["chronology_authority_receipt_sha256"],
                "cold ordered dream chronology",
            ),
            chronology_sequence=_positive(
                raw["chronology_sequence"],
                "cold ordered dream chronology sequence",
            ),
            predecessor_relation_receipt_sha256=(
                None
                if predecessor is None
                else _sha(
                    predecessor,
                    "cold ordered dream predecessor relation",
                )
            ),
            source_occurrence_receipt_sha256=_sha(
                raw["source_occurrence_receipt_sha256"],
                "cold ordered dream source occurrence",
            ),
            target_occurrence_receipt_sha256=_sha(
                raw["target_occurrence_receipt_sha256"],
                "cold ordered dream target occurrence",
            ),
            source_thing_id=_sha(
                raw["source_thing_id"],
                "cold ordered dream source THING",
            ),
            target_thing_id=_sha(
                raw["target_thing_id"],
                "cold ordered dream target THING",
            ),
            source_time_start=_fraction_from_text(
                raw["source_time_start"],
                "cold ordered dream source start",
            ),
            source_time_end=_fraction_from_text(
                raw["source_time_end"],
                "cold ordered dream source end",
            ),
            target_time_start=_fraction_from_text(
                raw["target_time_start"],
                "cold ordered dream target start",
            ),
            target_time_end=_fraction_from_text(
                raw["target_time_end"],
                "cold ordered dream target end",
            ),
            source_full_field_root_receipt_sha256s=tuple(
                _sha(value, "cold ordered dream source root")
                for value in raw[
                    "source_full_field_root_receipt_sha256s"
                ]
            ),
            target_full_field_root_receipt_sha256s=tuple(
                _sha(value, "cold ordered dream target root")
                for value in raw[
                    "target_full_field_root_receipt_sha256s"
                ]
            ),
            support_relation_receipt_sha256=_sha(
                raw["support_relation_receipt_sha256"],
                "cold ordered dream support relation",
            ),
            origin=OriginState(raw["origin"]),
        )

    def _dream_from_raw(self, raw: object) -> OrganismDreamRecord:
        if (
            not isinstance(raw, Mapping)
            or raw.get("schema") != DREAM_SCHEMA
        ):
            raise ValueError("cold dream changed")
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "external_embodiment_state",
            "external_event_claimed",
            "internal_transition_end",
            "internal_transition_start",
            "organism_state_receipt_sha256",
            "origin",
            "schema",
            "source_latest_external_time_end",
            "source_relation_receipt_sha256s",
            "source_tapestry_receipt_sha256s",
            "transitions",
        }
        if set(raw) != expected or not isinstance(raw["transitions"], list):
            raise ValueError("cold dream fields changed")
        return OrganismDreamRecord(
            organism_state_receipt_sha256=_sha(
                raw["organism_state_receipt_sha256"],
                "cold dream organism state",
            ),
            source_tapestry_receipt_sha256s=tuple(
                _sha(value, "cold dream tapestry")
                for value in raw["source_tapestry_receipt_sha256s"]
            ),
            source_relation_receipt_sha256s=tuple(
                _sha(value, "cold dream relation")
                for value in raw["source_relation_receipt_sha256s"]
            ),
            source_latest_external_time_end=_fraction_from_text(
                raw["source_latest_external_time_end"],
                "cold dream latest external time",
            ),
            internal_transition_start=_nonnegative(
                raw["internal_transition_start"],
                "cold dream transition start",
            ),
            internal_transition_end=_positive(
                raw["internal_transition_end"],
                "cold dream transition end",
            ),
            transitions=tuple(
                self._transition_from_raw(value)
                for value in raw["transitions"]
            ),
            origin=OriginState(raw["origin"]),
            external_embodiment_state=raw["external_embodiment_state"],
            external_event_claimed=raw["external_event_claimed"],
            authority_hmac_sha256=_sha(
                raw["authority_hmac_sha256"],
                "cold dream HMAC",
            ),
            authority_receipt_sha256=_sha(
                raw["authority_receipt_sha256"],
                "cold dream authority",
            ),
        )

    def _ordered_dream_from_raw(
        self,
        raw: object,
    ) -> OrganismOrderedDreamRecord:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "chronology_authority_receipt_sha256",
            "external_embodiment_state",
            "external_event_claimed",
            "internal_transition_end",
            "internal_transition_start",
            "organism_state_receipt_sha256",
            "origin",
            "schema",
            "source_latest_external_time_end",
            "source_occurrence_receipt_sha256s",
            "source_relation_receipt_sha256s",
            "transitions",
        }
        if (
            not isinstance(raw, Mapping)
            or set(raw) != expected
            or raw.get("schema") != ORDERED_DREAM_SCHEMA
            or not isinstance(
                raw["source_occurrence_receipt_sha256s"], list
            )
            or not isinstance(
                raw["source_relation_receipt_sha256s"], list
            )
            or not isinstance(raw["transitions"], list)
        ):
            raise ValueError("cold ordered dream changed")
        return OrganismOrderedDreamRecord(
            organism_state_receipt_sha256=_sha(
                raw["organism_state_receipt_sha256"],
                "cold ordered dream organism state",
            ),
            chronology_authority_receipt_sha256=_sha(
                raw["chronology_authority_receipt_sha256"],
                "cold ordered dream chronology",
            ),
            source_occurrence_receipt_sha256s=tuple(
                _sha(value, "cold ordered dream occurrence")
                for value in raw[
                    "source_occurrence_receipt_sha256s"
                ]
            ),
            source_relation_receipt_sha256s=tuple(
                _sha(value, "cold ordered dream relation")
                for value in raw["source_relation_receipt_sha256s"]
            ),
            source_latest_external_time_end=_fraction_from_text(
                raw["source_latest_external_time_end"],
                "cold ordered dream latest external time",
            ),
            internal_transition_start=_nonnegative(
                raw["internal_transition_start"],
                "cold ordered dream transition start",
            ),
            internal_transition_end=_positive(
                raw["internal_transition_end"],
                "cold ordered dream transition end",
            ),
            transitions=tuple(
                self._ordered_transition_from_raw(value)
                for value in raw["transitions"]
            ),
            origin=OriginState(raw["origin"]),
            external_embodiment_state=raw[
                "external_embodiment_state"
            ],
            external_event_claimed=raw["external_event_claimed"],
            authority_hmac_sha256=_sha(
                raw["authority_hmac_sha256"],
                "cold ordered dream HMAC",
            ),
            authority_receipt_sha256=_sha(
                raw["authority_receipt_sha256"],
                "cold ordered dream authority",
            ),
        )

    def _wake_from_raw(self, raw: object) -> OrganismWakeTestRecord:
        if (
            not isinstance(raw, Mapping)
            or raw.get("schema") != WAKE_SCHEMA
        ):
            raise ValueError("cold wake test changed")
        expected = {
            "action_intent_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "consequence_episode_receipt_sha256",
            "consequence_learning_receipt_sha256",
            "consequence_origin",
            "consequence_world_observation_receipt_sha256",
            "dream_receipt_sha256",
            "execution_receipt_sha256",
            "origin",
            "schema",
            "state",
            "world_execution_receipt_sha256",
        }
        if set(raw) != expected:
            raise ValueError("cold wake-test fields changed")

        def optional_sha(value: object, label: str) -> str | None:
            return None if value is None else _sha(value, label)

        return OrganismWakeTestRecord(
            dream_receipt_sha256=_sha(
                raw["dream_receipt_sha256"],
                "cold wake dream",
            ),
            action_intent_receipt_sha256=_sha(
                raw["action_intent_receipt_sha256"],
                "cold wake action",
            ),
            origin=OriginState(raw["origin"]),
            state=raw["state"],
            execution_receipt_sha256=optional_sha(
                raw["execution_receipt_sha256"],
                "cold wake execution",
            ),
            world_execution_receipt_sha256=optional_sha(
                raw["world_execution_receipt_sha256"],
                "cold wake world execution",
            ),
            consequence_learning_receipt_sha256=optional_sha(
                raw["consequence_learning_receipt_sha256"],
                "cold wake learning",
            ),
            consequence_episode_receipt_sha256=optional_sha(
                raw["consequence_episode_receipt_sha256"],
                "cold wake episode",
            ),
            consequence_world_observation_receipt_sha256=optional_sha(
                raw["consequence_world_observation_receipt_sha256"],
                "cold wake observation",
            ),
            consequence_origin=(
                OriginState(raw["consequence_origin"])
                if raw["consequence_origin"] is not None
                else None
            ),
            authority_hmac_sha256=_sha(
                raw["authority_hmac_sha256"],
                "cold wake HMAC",
            ),
            authority_receipt_sha256=_sha(
                raw["authority_receipt_sha256"],
                "cold wake authority",
            ),
        )

    def _weave_from_raw(self, raw: object) -> OrganismWeaveRecord:
        if (
            not isinstance(raw, Mapping)
            or raw.get("schema") != WEAVE_SCHEMA
        ):
            raise ValueError("cold weave changed")
        expected = {
            "action_intent_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "consequence_learning_receipt_sha256",
            "consequence_origin",
            "consequence_world_observation_receipt_sha256",
            "dream_receipt_sha256",
            "execution_receipt_sha256",
            "expression_origin",
            "organism_state_receipt_sha256",
            "schema",
            "stored_language_content",
            "support_tapestry_receipt_sha256s",
            "wake_test_receipt_sha256",
            "world_execution_receipt_sha256",
        }
        if set(raw) != expected:
            raise ValueError("cold weave fields changed")
        return OrganismWeaveRecord(
            wake_test_receipt_sha256=_sha(
                raw["wake_test_receipt_sha256"],
                "cold weave wake test",
            ),
            dream_receipt_sha256=_sha(
                raw["dream_receipt_sha256"],
                "cold weave dream",
            ),
            support_tapestry_receipt_sha256s=tuple(
                _sha(value, "cold weave tapestry")
                for value in raw["support_tapestry_receipt_sha256s"]
            ),
            organism_state_receipt_sha256=_sha(
                raw["organism_state_receipt_sha256"],
                "cold weave organism state",
            ),
            action_intent_receipt_sha256=_sha(
                raw["action_intent_receipt_sha256"],
                "cold weave action",
            ),
            execution_receipt_sha256=_sha(
                raw["execution_receipt_sha256"],
                "cold weave execution",
            ),
            world_execution_receipt_sha256=_sha(
                raw["world_execution_receipt_sha256"],
                "cold weave world execution",
            ),
            consequence_learning_receipt_sha256=_sha(
                raw["consequence_learning_receipt_sha256"],
                "cold weave learning",
            ),
            consequence_world_observation_receipt_sha256=_sha(
                raw["consequence_world_observation_receipt_sha256"],
                "cold weave observation",
            ),
            expression_origin=raw["expression_origin"],
            consequence_origin=OriginState(raw["consequence_origin"]),
            stored_language_content=raw["stored_language_content"],
            authority_hmac_sha256=_sha(
                raw["authority_hmac_sha256"],
                "cold weave HMAC",
            ),
            authority_receipt_sha256=_sha(
                raw["authority_receipt_sha256"],
                "cold weave authority",
            ),
        )

    def _prepared_from_raw(
        self,
        raw: object,
    ) -> PreparedDreamWakeWeaveMutation:
        if (
            not isinstance(raw, Mapping)
            or raw.get("schema") != PREPARED_SCHEMA
            or set(raw)
            != {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "before_state_sha256",
                "kind",
                "prior_record_receipt_sha256",
                "schema",
                "staged_internal_transition_cursor",
                "staged_record",
            }
        ):
            raise ValueError("cold prepared growth mutation changed")
        staged = raw["staged_record"]
        if not isinstance(staged, Mapping):
            raise ValueError("cold prepared growth record changed")
        schema = staged.get("schema")
        record: GrowthRecord
        if schema == DREAM_SCHEMA:
            record = self._dream_from_raw(staged)
        elif schema == ORDERED_DREAM_SCHEMA:
            record = self._ordered_dream_from_raw(staged)
        elif schema == WAKE_SCHEMA:
            record = self._wake_from_raw(staged)
        elif schema == WEAVE_SCHEMA:
            record = self._weave_from_raw(staged)
        else:
            raise ValueError("cold prepared growth schema changed")
        prior = raw["prior_record_receipt_sha256"]
        return PreparedDreamWakeWeaveMutation(
            kind=raw["kind"],
            before_state_sha256=_sha(
                raw["before_state_sha256"],
                "cold prepared prior state",
            ),
            prior_record_receipt_sha256=(
                _sha(prior, "cold prepared prior record")
                if prior is not None
                else None
            ),
            staged_record=record,
            staged_internal_transition_cursor=_nonnegative(
                raw["staged_internal_transition_cursor"],
                "cold prepared transition cursor",
            ),
            authority_hmac_sha256=_sha(
                raw["authority_hmac_sha256"],
                "cold prepared HMAC",
            ),
            authority_receipt_sha256=_sha(
                raw["authority_receipt_sha256"],
                "cold prepared authority",
            ),
        )


__all__ = (
    "DREAM_SCHEMA",
    "DreamWakeWeaveProfile",
    "DreamWakeWeaveUndo",
    "InternallyExecutedDreamTransition",
    "InternallyExecutedOrderedDreamTransition",
    "OrganismDreamRecord",
    "OrganismDreamWakeWeaveOwner",
    "OrganismOrderedDreamRecord",
    "OrganismWakeTestRecord",
    "OrganismWeaveRecord",
    "ORDERED_DREAM_SCHEMA",
    "ORDERED_DREAM_TRANSITION_SCHEMA",
    "OriginState",
    "PREPARED_SCHEMA",
    "PreparedDreamWakeWeaveMutation",
    "STATE_SCHEMA",
    "WAKE_SCHEMA",
    "WEAVE_SCHEMA",
)
