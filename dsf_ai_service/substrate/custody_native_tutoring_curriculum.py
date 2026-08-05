"""Bounded tutoring progression over authenticated lived THING experiences.

This owner schedules physical distinctions; it does not supply their content.
Every retained experience arrives through a child of settled-experience
custody, contains one applied body action, routes uniquely to an already-owned
causal THING, and preserves the complete six-sense field by upstream receipt.

The curriculum asks only for the first unresolved
``(THING, sense, causal-relation)`` in canonical physical order.  It never
stores sensor samples, words, transcripts, labels, meanings, action commands,
scores, clocks, or probabilistic state.

Books, courses, and videos are not privileged knowledge inputs.  They may
participate only when their light, sound, body action, and physical consequence
arrive through the same authenticated lived-experience custody as every other
stimulus.  Text tokens, scripted object recognition, external concept graphs,
LLM-authored sensory descriptions, and preinterpreted lesson bundles have no
admission surface here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Mapping

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustodyAuthority,
)


PROFILE_SCHEMA = "guala.custody_native_tutoring_curriculum.profile.v1"
EXPERIENCE_SCHEMA = "guala.custody_native_tutoring_curriculum.experience.v1"
OPPORTUNITY_SCHEMA = (
    "guala.custody_native_tutoring_curriculum.opportunity.v1"
)
STATE_SCHEMA = "guala.custody_native_tutoring_curriculum.state.v1"
ENVELOPE_SCHEMA = (
    "guala.custody_native_tutoring_curriculum.state_hmac.v1"
)
STATUS_SCHEMA = "guala.custody_native_tutoring_curriculum.status.v1"
TUTORING_CURRICULUM_CONSUMER_ID = "custody-native-tutoring-curriculum"

CAUSAL_RELATION_ORDER = (
    "first_observation",
    "recurrence",
    "structural_change",
)

_PROFILE_DOMAIN = b"guala-custody-native-tutoring-profile-v1\0"
_EXPERIENCE_DOMAIN = b"guala-custody-native-tutoring-experience-v1\0"
_OPPORTUNITY_DOMAIN = b"guala-custody-native-tutoring-opportunity-v1\0"
_STATE_DOMAIN = b"guala-custody-native-tutoring-state-v1\0"
_HEX = frozenset("0123456789abcdef")
_CANONICAL_SENSES = tuple(value.value for value in SENSE_ORDER)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


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


def _key(value: bytes | str) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("tutoring curriculum authority key changed")
    return raw


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} changed")
    return value


@dataclass(frozen=True, slots=True)
class CustodyNativeTutoringProfile:
    profile_id: str
    available_senses: tuple[str, ...]
    max_things: int
    max_experiences: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        available_senses: tuple[str, ...],
        max_things: int,
        max_experiences: int,
        max_state_bytes: int,
    ) -> "CustodyNativeTutoringProfile":
        senses = tuple(
            sense
            for sense in _CANONICAL_SENSES
            if sense in frozenset(available_senses)
        )
        if (
            not available_senses
            or senses != available_senses
            or len(senses) != len(set(senses))
        ):
            raise ValueError(
                "tutoring available senses must be a canonical subset"
            )
        provisional = cls(
            profile_id=_identifier(profile_id, "tutoring profile id"),
            available_senses=senses,
            max_things=_positive(max_things, "tutoring THING capacity"),
            max_experiences=_positive(
                max_experiences,
                "tutoring experience capacity",
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "tutoring state capacity",
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            available_senses=provisional.available_senses,
            max_things=provisional.max_things,
            max_experiences=provisional.max_experiences,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "available_senses": list(self.available_senses),
            "causal_relation_order": list(CAUSAL_RELATION_ORDER),
            "max_experiences": self.max_experiences,
            "max_state_bytes": self.max_state_bytes,
            "max_things": self.max_things,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            available_senses=self.available_senses,
            max_things=self.max_things,
            max_experiences=self.max_experiences,
            max_state_bytes=self.max_state_bytes,
        )
        if self != expected:
            raise ValueError("tutoring profile authority changed")


@dataclass(frozen=True, order=True, slots=True)
class CustodyNativeSenseReceipt:
    sense: str
    state: str
    relation: str
    structural_fingerprint: str
    boundary_receipt_sha256: str
    topology_receipt_sha256: str | None

    def record(self) -> dict[str, object]:
        return {
            "boundary_receipt_sha256": self.boundary_receipt_sha256,
            "relation": self.relation,
            "sense": self.sense,
            "state": self.state,
            "structural_fingerprint": self.structural_fingerprint,
            "topology_receipt_sha256": self.topology_receipt_sha256,
        }

    def verify(self) -> None:
        if (
            self.sense not in _CANONICAL_SENSES
            or self.state
            not in ("observed", "sensor_unavailable", "unknown")
        ):
            raise ValueError("tutoring sense boundary changed")
        _sha(self.structural_fingerprint, "sense structural fingerprint")
        _sha(self.boundary_receipt_sha256, "sense boundary receipt")
        if self.state == "observed":
            if self.relation not in CAUSAL_RELATION_ORDER:
                raise ValueError("observed tutoring relation changed")
            _sha(self.topology_receipt_sha256, "sense topology receipt")
        elif (
            self.relation != "not_observed"
            or self.topology_receipt_sha256 is not None
        ):
            raise ValueError(
                "unobserved tutoring sense gained field authority"
            )


@dataclass(frozen=True, slots=True)
class CustodyNativeTutoringExperience:
    sequence: int
    thing_id: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    custody_capability_receipt_sha256: str
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    action_execution_receipt_sha256: str
    world_observation_receipt_sha256: str
    senses: tuple[CustodyNativeSenseReceipt, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_execution_receipt_sha256": (
                self.action_execution_receipt_sha256
            ),
            "custody_capability_receipt_sha256": (
                self.custody_capability_receipt_sha256
            ),
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "schema": EXPERIENCE_SCHEMA,
            "sense_receipts": [value.record() for value in self.senses],
            "sequence": self.sequence,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "thing_id": self.thing_id,
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CustodyNativeTutoringOpportunity:
    opportunity_id: str
    curriculum_state_sha256: str
    thing_id: str
    target_sense: str
    target_relation: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "curriculum_state_sha256": self.curriculum_state_sha256,
            "opportunity_id": self.opportunity_id,
            "schema": OPPORTUNITY_SCHEMA,
            "target_relation": self.target_relation,
            "target_sense": self.target_sense,
            "thing_id": self.thing_id,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CustodyNativeTutoringAdmission:
    experience: CustodyNativeTutoringExperience
    resolved_active_opportunity: bool


@dataclass(frozen=True, slots=True)
class CommittedCustodyNativeTutoringProgression:
    admission: CustodyNativeTutoringAdmission
    scheduled: CustodyNativeTutoringOpportunity | None
    before_experiences: tuple[CustodyNativeTutoringExperience, ...]
    before_thing_order: tuple[str, ...]
    before_active: CustodyNativeTutoringOpportunity | None
    after_experiences: tuple[CustodyNativeTutoringExperience, ...]
    after_thing_order: tuple[str, ...]
    after_active: CustodyNativeTutoringOpportunity | None


class CustodyNativeTutoringCurriculumOwner:
    """Own exact bounded progression across lived physical distinctions."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: CustodyNativeTutoringProfile,
        thing_owner: CausalThingMosaicOwner,
    ) -> None:
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError(
                "tutoring curriculum requires the causal THING owner"
            )
        profile.verify()
        root = hashlib.sha256(
            _PROFILE_DOMAIN + _key(authority_key)
        ).digest()
        self._experience_key = hashlib.sha256(
            _EXPERIENCE_DOMAIN + root
        ).digest()
        self._opportunity_key = hashlib.sha256(
            _OPPORTUNITY_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._profile = profile
        self._things = thing_owner
        self._experiences: tuple[
            CustodyNativeTutoringExperience, ...
        ] = ()
        self._thing_order: tuple[str, ...] = ()
        self._active: CustodyNativeTutoringOpportunity | None = None
        self._lock = threading.RLock()

    @property
    def experiences(
        self,
    ) -> tuple[CustodyNativeTutoringExperience, ...]:
        with self._lock:
            return self._experiences

    def _verify_experience(
        self,
        value: CustodyNativeTutoringExperience,
    ) -> None:
        if not isinstance(value, CustodyNativeTutoringExperience):
            raise TypeError("tutoring experience is not typed")
        if (
            isinstance(value.sequence, bool)
            or not isinstance(value.sequence, int)
            or value.sequence <= 0
        ):
            raise ValueError("tutoring experience sequence changed")
        for item, label in (
            (value.thing_id, "tutoring THING"),
            (value.source_occurrence_id, "tutoring source occurrence"),
            (
                value.parent_custody_receipt_sha256,
                "tutoring parent custody",
            ),
            (
                value.custody_capability_receipt_sha256,
                "tutoring custody capability",
            ),
            (
                value.settlement_receipt_sha256,
                "tutoring settlement",
            ),
            (
                value.settlement_structural_fingerprint,
                "tutoring settlement structure",
            ),
            (
                value.action_execution_receipt_sha256,
                "tutoring action execution",
            ),
            (
                value.world_observation_receipt_sha256,
                "tutoring world observation",
            ),
            (value.authority_hmac_sha256, "tutoring experience HMAC"),
            (
                value.authority_receipt_sha256,
                "tutoring experience authority",
            ),
        ):
            _sha(item, label)
        if (
            len(value.senses) != len(_CANONICAL_SENSES)
            or tuple(item.sense for item in value.senses)
            != _CANONICAL_SENSES
        ):
            raise ValueError(
                "tutoring experience lost canonical six-sense coverage"
            )
        for sense in value.senses:
            sense.verify()
        signature = hmac.new(
            self._experience_key,
            _EXPERIENCE_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError("tutoring experience authority changed")

    def _verify_opportunity_record(
        self,
        value: CustodyNativeTutoringOpportunity,
    ) -> None:
        if not isinstance(value, CustodyNativeTutoringOpportunity):
            raise TypeError("tutoring opportunity is not typed")
        for item, label in (
            (value.opportunity_id, "tutoring opportunity"),
            (
                value.curriculum_state_sha256,
                "tutoring curriculum state",
            ),
            (value.thing_id, "tutoring opportunity THING"),
            (value.authority_hmac_sha256, "tutoring opportunity HMAC"),
            (
                value.authority_receipt_sha256,
                "tutoring opportunity authority",
            ),
        ):
            _sha(item, label)
        if (
            value.target_sense not in self._profile.available_senses
            or value.target_relation not in CAUSAL_RELATION_ORDER
        ):
            raise ValueError("tutoring opportunity distinction changed")
        identity = _digest({
            "curriculum_state_sha256": value.curriculum_state_sha256,
            "schema": "guala.custody_native_tutoring_curriculum.identity.v1",
            "target_relation": value.target_relation,
            "target_sense": value.target_sense,
            "thing_id": value.thing_id,
        })
        signature = hmac.new(
            self._opportunity_key,
            _OPPORTUNITY_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            value.opportunity_id != identity
            or not hmac.compare_digest(
                signature,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError("tutoring opportunity authority changed")

    def verify_opportunity(
        self,
        value: CustodyNativeTutoringOpportunity,
    ) -> None:
        self._verify_opportunity_record(value)
        with self._lock:
            if self._active != value:
                raise ValueError("tutoring opportunity is not active")

    def opportunity_is_fresh(
        self,
        value: CustodyNativeTutoringOpportunity,
    ) -> bool:
        """Return whether no lived occurrence followed this opportunity.

        The opportunity's curriculum-state receipt is taken immediately
        before issuance.  Comparing it with the current authenticated
        progression makes one autonomous attempt self-bounding without an
        extra clock, retry counter, or second persistence owner.  A later
        externally supplied lived occurrence may still resolve the active
        distinction through :meth:`admit_experience`.
        """

        self.verify_opportunity(value)
        with self._lock:
            return hmac.compare_digest(
                value.curriculum_state_sha256,
                self._curriculum_state(
                    self._experiences,
                    self._thing_order,
                ),
            )

    @staticmethod
    def _coverage(
        experiences: tuple[CustodyNativeTutoringExperience, ...],
    ) -> frozenset[tuple[str, str, str]]:
        return frozenset(
            (experience.thing_id, sense.sense, sense.relation)
            for experience in experiences
            for sense in experience.senses
            if sense.state == "observed"
        )

    def _next_unresolved(
        self,
        experiences: tuple[CustodyNativeTutoringExperience, ...],
        thing_order: tuple[str, ...],
    ) -> tuple[str, str, str] | None:
        coverage = self._coverage(experiences)
        return next(
            (
                (thing_id, sense, relation)
                for thing_id in thing_order
                for sense in self._profile.available_senses
                for relation in CAUSAL_RELATION_ORDER
                if (thing_id, sense, relation) not in coverage
            ),
            None,
        )

    def _curriculum_state(
        self,
        experiences: tuple[CustodyNativeTutoringExperience, ...],
        thing_order: tuple[str, ...],
    ) -> str:
        return _digest({
            "experience_receipts": [
                value.authority_receipt_sha256 for value in experiences
            ],
            "profile_authority_receipt_sha256": (
                self._profile.authority_receipt_sha256
            ),
            "schema": (
                "guala.custody_native_tutoring_curriculum.progress.v1"
            ),
            "thing_order": list(thing_order),
        })

    def schedule(
        self,
    ) -> CustodyNativeTutoringOpportunity | None:
        with self._lock:
            if self._active is not None:
                self._verify_opportunity_record(self._active)
                return self._active
            target = self._next_unresolved(
                self._experiences,
                self._thing_order,
            )
            if target is None:
                return None
            thing_id, sense, relation = target
            state = self._curriculum_state(
                self._experiences,
                self._thing_order,
            )
            opportunity_id = _digest({
                "curriculum_state_sha256": state,
                "schema": (
                    "guala.custody_native_tutoring_curriculum.identity.v1"
                ),
                "target_relation": relation,
                "target_sense": sense,
                "thing_id": thing_id,
            })
            provisional = CustodyNativeTutoringOpportunity(
                opportunity_id=opportunity_id,
                curriculum_state_sha256=state,
                thing_id=thing_id,
                target_sense=sense,
                target_relation=relation,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._opportunity_key,
                _OPPORTUNITY_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            active = CustodyNativeTutoringOpportunity(
                opportunity_id=provisional.opportunity_id,
                curriculum_state_sha256=(
                    provisional.curriculum_state_sha256
                ),
                thing_id=provisional.thing_id,
                target_sense=provisional.target_sense,
                target_relation=provisional.target_relation,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._verify_opportunity_record(active)
            self._encoded(
                self._experiences,
                self._thing_order,
                active,
            )
            self._active = active
            return active

    def admit_experience(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> CustodyNativeTutoringAdmission:
        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "tutoring curriculum requires settled-experience custody"
            )
        if (
            not isinstance(
                custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody_capability.consumer_id
            != TUTORING_CURRICULUM_CONSUMER_ID
        ):
            raise ValueError(
                "tutoring curriculum requires its own custody capability"
            )
        view = custody_authority.open_child(custody_capability)
        if view.world_execution is None:
            raise ValueError(
                "tutoring curriculum requires an applied action experience"
            )
        route = self._things.route(view.causal_settlement)
        if route.state != "unique" or len(route.thing_ids) != 1:
            raise ValueError(
                "tutoring experience does not resolve one causal THING"
            )
        thing_id = route.thing_ids[0]
        if not any(
            mosaic.thing_id == thing_id
            for mosaic in self._things.mosaics
        ):
            raise ValueError("tutoring experience THING is not owned")
        senses = tuple(
            CustodyNativeSenseReceipt(
                sense=value.sense,
                state=value.state,
                relation=value.relation,
                structural_fingerprint=value.structural_fingerprint,
                boundary_receipt_sha256=(
                    value.boundary_receipt_sha256
                ),
                topology_receipt_sha256=(
                    value.topology_receipt_sha256
                ),
            )
            for value in view.causal_settlement.interpretations
        )
        with self._lock:
            existing = next(
                (
                    value
                    for value in self._experiences
                    if value.source_occurrence_id
                    == view.source_occurrence_id
                ),
                None,
            )
            if existing is not None:
                if (
                    existing.parent_custody_receipt_sha256
                    != view.parent_custody_receipt_sha256
                    or existing.custody_capability_receipt_sha256
                    != custody_capability.authority_receipt_sha256
                ):
                    raise ValueError(
                        "tutoring source occurrence crossed custody"
                    )
                return CustodyNativeTutoringAdmission(
                    experience=existing,
                    resolved_active_opportunity=False,
                )
            if len(self._experiences) >= self._profile.max_experiences:
                raise RuntimeError(
                    "tutoring experience capacity exhausted"
                )
            if (
                thing_id not in self._thing_order
                and len(self._thing_order) >= self._profile.max_things
            ):
                raise RuntimeError("tutoring THING capacity exhausted")
            provisional = CustodyNativeTutoringExperience(
                sequence=len(self._experiences) + 1,
                thing_id=thing_id,
                source_occurrence_id=view.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    view.parent_custody_receipt_sha256
                ),
                custody_capability_receipt_sha256=(
                    custody_capability.authority_receipt_sha256
                ),
                settlement_receipt_sha256=(
                    view.causal_settlement.authority_receipt_sha256
                ),
                settlement_structural_fingerprint=(
                    view.causal_settlement.structural_fingerprint
                ),
                action_execution_receipt_sha256=(
                    view.world_execution.authority_receipt_sha256
                ),
                world_observation_receipt_sha256=(
                    view.world_observation.authority_receipt_sha256
                ),
                senses=senses,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._experience_key,
                _EXPERIENCE_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            experience = CustodyNativeTutoringExperience(
                **{
                    field: getattr(provisional, field)
                    for field in (
                        "sequence",
                        "thing_id",
                        "source_occurrence_id",
                        "parent_custody_receipt_sha256",
                        "custody_capability_receipt_sha256",
                        "settlement_receipt_sha256",
                        "settlement_structural_fingerprint",
                        "action_execution_receipt_sha256",
                        "world_observation_receipt_sha256",
                        "senses",
                    )
                },
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": provisional.payload(),
                }),
            )
            self._verify_experience(experience)
            staged_experiences = self._experiences + (experience,)
            staged_things = (
                self._thing_order
                if thing_id in self._thing_order
                else self._thing_order + (thing_id,)
            )
            resolved = (
                self._active is not None
                and any(
                    sense.sense == self._active.target_sense
                    and sense.state == "observed"
                    and sense.relation == self._active.target_relation
                    for sense in senses
                )
                and thing_id == self._active.thing_id
            )
            staged_active = None if resolved else self._active
            self._encoded(
                staged_experiences,
                staged_things,
                staged_active,
            )
            self._experiences = staged_experiences
            self._thing_order = staged_things
            self._active = staged_active
            return CustodyNativeTutoringAdmission(
                experience=experience,
                resolved_active_opportunity=resolved,
            )

    def admit_experience_and_schedule(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> CommittedCustodyNativeTutoringProgression:
        """Atomically admit one custody and schedule its exact successor."""
        with self._lock:
            before_experiences = self._experiences
            before_thing_order = self._thing_order
            before_active = self._active
            before_encoded = self.snapshot_encoded()
            try:
                admission = self.admit_experience(
                    custody_authority=custody_authority,
                    custody_capability=custody_capability,
                )
                scheduled = self.schedule()
                self.snapshot_encoded()
            except BaseException:
                self._experiences = before_experiences
                self._thing_order = before_thing_order
                self._active = before_active
                if self.snapshot_encoded() != before_encoded:
                    raise RuntimeError(
                        "tutoring failed admission changed exact state"
                    )
                raise
            return CommittedCustodyNativeTutoringProgression(
                admission=admission,
                scheduled=scheduled,
                before_experiences=before_experiences,
                before_thing_order=before_thing_order,
                before_active=before_active,
                after_experiences=self._experiences,
                after_thing_order=self._thing_order,
                after_active=self._active,
            )

    def rollback_committed_progression(
        self,
        committed: CommittedCustodyNativeTutoringProgression,
    ) -> None:
        """Restore the exact pre-admission state after a larger rollback."""
        if not isinstance(
            committed,
            CommittedCustodyNativeTutoringProgression,
        ):
            raise TypeError("tutoring rollback requires committed progression")
        with self._lock:
            if (
                self._experiences != committed.after_experiences
                or self._thing_order != committed.after_thing_order
                or self._active != committed.after_active
            ):
                raise RuntimeError(
                    "tutoring progression changed before rollback"
                )
            self._experiences = committed.before_experiences
            self._thing_order = committed.before_thing_order
            self._active = committed.before_active
            self.snapshot_encoded()

    def _body(
        self,
        experiences: tuple[CustodyNativeTutoringExperience, ...],
        thing_order: tuple[str, ...],
        active: CustodyNativeTutoringOpportunity | None,
    ) -> dict[str, object]:
        return {
            "active_opportunity": (
                None if active is None else active.record()
            ),
            "experiences": [value.record() for value in experiences],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "thing_order": list(thing_order),
        }

    def _encoded(
        self,
        experiences: tuple[CustodyNativeTutoringExperience, ...],
        thing_order: tuple[str, ...],
        active: CustodyNativeTutoringOpportunity | None,
    ) -> bytes:
        body = self._body(experiences, thing_order, active)
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
            raise RuntimeError("tutoring state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(
                self._experiences,
                self._thing_order,
                self._active,
            )

    def status(self) -> dict[str, object]:
        with self._lock:
            unresolved = sum(
                1
                for thing_id in self._thing_order
                for sense in self._profile.available_senses
                for relation in CAUSAL_RELATION_ORDER
                if (
                    thing_id,
                    sense,
                    relation,
                )
                not in self._coverage(self._experiences)
            )
            return {
                "active_opportunity": self._active is not None,
                "experiences": len(self._experiences),
                "full_field_authority_retained_upstream": True,
                "reduced_approximation": False,
                "schema": STATUS_SCHEMA,
                "state_bytes": len(self.snapshot_encoded()),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "things": len(self._thing_order),
                "unresolved_causal_distinctions": unresolved,
            }


def _sense_from_record(
    value: Mapping[str, object],
) -> CustodyNativeSenseReceipt:
    result = CustodyNativeSenseReceipt(
        sense=value["sense"],
        state=value["state"],
        relation=value["relation"],
        structural_fingerprint=value["structural_fingerprint"],
        boundary_receipt_sha256=value["boundary_receipt_sha256"],
        topology_receipt_sha256=value["topology_receipt_sha256"],
    )
    result.verify()
    return result


def _experience_from_record(
    value: Mapping[str, object],
) -> CustodyNativeTutoringExperience:
    if value.get("schema") != EXPERIENCE_SCHEMA:
        raise ValueError("restored tutoring experience schema changed")
    return CustodyNativeTutoringExperience(
        sequence=value["sequence"],
        thing_id=value["thing_id"],
        source_occurrence_id=value["source_occurrence_id"],
        parent_custody_receipt_sha256=(
            value["parent_custody_receipt_sha256"]
        ),
        custody_capability_receipt_sha256=(
            value["custody_capability_receipt_sha256"]
        ),
        settlement_receipt_sha256=value["settlement_receipt_sha256"],
        settlement_structural_fingerprint=(
            value["settlement_structural_fingerprint"]
        ),
        action_execution_receipt_sha256=(
            value["action_execution_receipt_sha256"]
        ),
        world_observation_receipt_sha256=(
            value["world_observation_receipt_sha256"]
        ),
        senses=tuple(
            _sense_from_record(item)
            for item in value["sense_receipts"]
        ),
        authority_hmac_sha256=value["authority_hmac_sha256"],
        authority_receipt_sha256=value["authority_receipt_sha256"],
    )


def _opportunity_from_record(
    value: Mapping[str, object],
) -> CustodyNativeTutoringOpportunity:
    if value.get("schema") != OPPORTUNITY_SCHEMA:
        raise ValueError("restored tutoring opportunity schema changed")
    return CustodyNativeTutoringOpportunity(
        opportunity_id=value["opportunity_id"],
        curriculum_state_sha256=value["curriculum_state_sha256"],
        thing_id=value["thing_id"],
        target_sense=value["target_sense"],
        target_relation=value["target_relation"],
        authority_hmac_sha256=value["authority_hmac_sha256"],
        authority_receipt_sha256=value["authority_receipt_sha256"],
    )


def restore_custody_native_tutoring_curriculum(
    encoded: bytes,
    *,
    authority_key: bytes | str,
    thing_owner: CausalThingMosaicOwner,
) -> CustodyNativeTutoringCurriculumOwner:
    try:
        envelope = json.loads(encoded)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("tutoring state is unreadable") from error
    if (
        not isinstance(envelope, Mapping)
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or not isinstance(envelope.get("body"), Mapping)
    ):
        raise ValueError("tutoring state envelope changed")
    body = envelope["body"]
    profile_record = body["profile"]
    profile = CustodyNativeTutoringProfile(
        profile_id=profile_record["profile_id"],
        available_senses=tuple(profile_record["available_senses"]),
        max_things=profile_record["max_things"],
        max_experiences=profile_record["max_experiences"],
        max_state_bytes=profile_record["max_state_bytes"],
        authority_receipt_sha256=(
            profile_record["authority_receipt_sha256"]
        ),
    )
    owner = CustodyNativeTutoringCurriculumOwner(
        authority_key=authority_key,
        profile=profile,
        thing_owner=thing_owner,
    )
    expected_hmac = hmac.new(
        owner._state_key,
        _STATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    if (
        body.get("schema") != STATE_SCHEMA
        or envelope.get("state_hmac_sha256") != expected_hmac
        or _canonical(envelope) != encoded
    ):
        raise ValueError("tutoring state authority changed")
    experiences = tuple(
        _experience_from_record(value)
        for value in body["experiences"]
    )
    for experience in experiences:
        owner._verify_experience(experience)
    thing_order = tuple(body["thing_order"])
    active = (
        None
        if body["active_opportunity"] is None
        else _opportunity_from_record(body["active_opportunity"])
    )
    if active is not None:
        owner._verify_opportunity_record(active)
    first_seen = tuple(dict.fromkeys(
        value.thing_id for value in experiences
    ))
    owned = frozenset(value.thing_id for value in thing_owner.mosaics)
    if (
        tuple(value.sequence for value in experiences)
        != tuple(range(1, len(experiences) + 1))
        or len({
            value.source_occurrence_id for value in experiences
        }) != len(experiences)
        or thing_order != first_seen
        or len(thing_order) > profile.max_things
        or len(experiences) > profile.max_experiences
        or not set(thing_order).issubset(owned)
        or (
            active is not None
            and (
                active.thing_id,
                active.target_sense,
                active.target_relation,
            )
            in owner._coverage(experiences)
        )
    ):
        raise ValueError("tutoring restored progression changed")
    owner._experiences = experiences
    owner._thing_order = thing_order
    owner._active = active
    if owner.snapshot_encoded() != encoded:
        raise ValueError("tutoring cold restore changed state")
    return owner


__all__ = (
    "CAUSAL_RELATION_ORDER",
    "CommittedCustodyNativeTutoringProgression",
    "CustodyNativeSenseReceipt",
    "CustodyNativeTutoringAdmission",
    "CustodyNativeTutoringCurriculumOwner",
    "CustodyNativeTutoringExperience",
    "CustodyNativeTutoringOpportunity",
    "CustodyNativeTutoringProfile",
    "TUTORING_CURRICULUM_CONSUMER_ID",
    "restore_custody_native_tutoring_curriculum",
)
