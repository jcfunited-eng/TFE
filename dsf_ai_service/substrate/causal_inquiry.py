"""Bounded causal inquiry over unresolved multisensory lived experience.

This owner does one narrowly defined job.  It retains exact unresolved or
ambiguous lived occurrences, opens one bounded inquiry need for one such
occurrence, and retains an articulatory action only after that
action is followed by a verified companion response and an exact reduction of
the prior routing uncertainty.

It does not recognize sounds, words, objects, or meanings.  It admits no
text, transcript, label, Unicode form, PCM, media, similarity, score,
threshold, probability, chi, or Atlas address.  Passive physical custody keeps
only its authenticated world observation; it cannot claim a source body or a
causal continuation.  Complete
``D/M/R/U/C/P/B`` roots are retained because an unresolved occurrence has no
other durable owner from which cold restore could reconstruct them.

World publication remains outside this owner.  Every local mutation is
prepared without visibility, committed with a typed undo, discardable, and
exactly rollbackable.
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
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.articulatory_exploration_selector import (
    ArticulatoryExplorationSelection,
    ArticulatoryExplorationSelector,
    ArticulatoryExplorationState,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingRoute,
    FullFieldSensoryRoot,
    full_field_sensory_roots,
)
from dsf_ai_service.substrate.causal_inquiry_tutor_authority import (
    TUTOR_AUTHORIZATION_SCHEMA,
    CausalInquiryTutorAuthorizationReceipt,
    CausalInquiryTutorAuthorizationVerifier,
)
from dsf_ai_service.substrate.embodiment_world import (
    SECOND_BODY_PORT_ID,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
    FreshArticulatorySelfAcousticCustodyAuthority,
    FreshArticulatorySelfAcousticCustodyReceipt,
    fresh_articulatory_receipt_from_record,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceConsumerView,
    SettledExperienceCustodyAuthority,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveRelationGapCapability,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.w1_companion_vocal_experience import (
    CompanionVocalEpisodeIntentReceipt,
    W1CompanionVocalExperienceAuthority,
)


PROFILE_SCHEMA = "guala.causal_inquiry.profile.v1"
WITNESS_SCHEMA = "guala.causal_inquiry.witness.v3"
NEED_SCHEMA = "guala.causal_inquiry.need.v1"
BINDING_SCHEMA = "guala.causal_inquiry.action_binding.v3"
OPPORTUNITY_SCHEMA = "guala.causal_inquiry.opportunity.v1"
ATTEMPT_SCHEMA = "guala.causal_inquiry.attempt.v2"
BODY_OWNED_FRAGMENT_CLOSURE_SCHEMA = (
    "guala.causal_inquiry.body_owned_fragment_closure.v1"
)
STATE_SCHEMA = "guala.causal_inquiry.state.v4"
LEGACY_STATE_SCHEMA = "guala.causal_inquiry.state.v3"
ENVELOPE_SCHEMA = "guala.causal_inquiry.state_hmac.v1"
STATUS_SCHEMA = "guala.causal_inquiry.status.v1"
CAUSAL_INQUIRY_CONSUMER_ID = "causal-inquiry"

_PROFILE_DOMAIN = b"guala-causal-inquiry-profile-v1\0"
_WITNESS_DOMAIN = b"guala-causal-inquiry-witness-v1\0"
_NEED_DOMAIN = b"guala-causal-inquiry-need-v1\0"
_BINDING_DOMAIN = b"guala-causal-inquiry-action-binding-v1\0"
_OPPORTUNITY_DOMAIN = b"guala-causal-inquiry-opportunity-v1\0"
_ATTEMPT_DOMAIN = b"guala-causal-inquiry-attempt-v1\0"
_BODY_OWNED_FRAGMENT_CLOSURE_DOMAIN = (
    b"guala-causal-inquiry-body-owned-fragment-closure-v1\0"
)
_STATE_DOMAIN = b"guala-causal-inquiry-state-v1\0"

_HEX = frozenset("0123456789abcdef")
_ROUTE_STATES = frozenset(("unresolved", "ambiguous", "unique"))
_CONTINUATION_RELATIONS = frozenset((
    "genesis",
    "exact_world_transition",
    "exact_inquiry_resolution_chain",
))
_ATTEMPT_MODES = frozenset(("exploratory", "learned"))
_MAX_PROFILE_ID_BYTES = 256
_MAX_CONFIGURED_RECORDS = 1_000_000
_MAX_CONFIGURED_ROOTS = 1_000_000
_MAX_CONFIGURED_STATE_BYTES = 256 * 1024 * 1024
_MIN_AUTHORITY_KEY_BYTES = 32
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()

_SENSE_INDEX = {
    value.value: index for index, value in enumerate(SENSE_ORDER)
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("causal inquiry authority key changed type")
    if not _MIN_AUTHORITY_KEY_BYTES <= len(result) <= 4_096:
        raise ValueError("causal inquiry authority key boundary changed")
    return result


def _ascii_identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ValueError(f"{label} changed")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(f"{label} must be ASCII") from error
    if len(encoded) > _MAX_PROFILE_ID_BYTES:
        raise ValueError(f"{label} changed")
    return value


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} changed")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("causal inquiry source time is not exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction_from_text(value: object, label: str) -> Fraction:
    if not isinstance(value, str):
        raise ValueError(f"{label} changed")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} changed") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is noncanonical")
    return result


def _capacity(value: object, label: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= maximum
    ):
        raise ValueError(f"{label} changed")
    return value


def _sign(key: bytes, domain: bytes, payload: object) -> str:
    return hmac.new(
        key,
        domain + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()


def _root_from_record(value: object) -> FullFieldSensoryRoot:
    if (
        not isinstance(value, Mapping)
        or set(value) != {
            "full_evidence_json",
            "physical_value_sha256",
            "schema",
            "sense",
            "topology_index",
        }
    ):
        raise ValueError("causal inquiry full-field root changed")
    root = FullFieldSensoryRoot(
        sense=value["sense"],
        topology_index=value["topology_index"],
        physical_value_sha256=value["physical_value_sha256"],
        full_evidence_json=value["full_evidence_json"],
    )
    root.verify()
    if root.record() != dict(value):
        raise ValueError("causal inquiry full-field root is noncanonical")
    return root


def _verify_complete_root(root: FullFieldSensoryRoot) -> None:
    root.verify()
    try:
        root.full_evidence_json.encode("ascii")
        evidence = json.loads(root.full_evidence_json)
    except (UnicodeEncodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "causal inquiry root is not canonical ASCII evidence"
        ) from error
    tuples = evidence.get("field_tuples")
    if not isinstance(tuples, list) or not tuples:
        raise ValueError("causal inquiry root lost its full field")
    for item in tuples:
        if (
            not isinstance(item, Mapping)
            or not isinstance(item.get("fields"), list)
            or tuple(
                field_value[0]
                for field_value in item["fields"]
                if isinstance(field_value, list)
                and len(field_value) == 2
            ) != DSF_FIELD_ORDER
            or len(item["fields"]) != len(DSF_FIELD_ORDER)
        ):
            raise ValueError("causal inquiry root flattened its DSF field")


def _route_shape(route: CausalThingRoute, *, allow_unique: bool) -> None:
    if not isinstance(route, CausalThingRoute):
        raise TypeError("causal inquiry route is not typed")
    allowed = {"unresolved", "ambiguous"}
    if allow_unique:
        allowed.add("unique")
    if (
        route.state not in allowed
        or route.thing_ids != tuple(sorted(set(route.thing_ids)))
        or route.matching_route_keys
        != tuple(sorted(set(route.matching_route_keys)))
        or (
            route.state == "unresolved"
            and (
                route.thing_ids
                or route.matching_route_keys
            )
        )
        or (
            route.state == "ambiguous"
            and len(route.thing_ids) < 2
        )
        or (
            route.state == "unique"
            and len(route.thing_ids) != 1
        )
    ):
        raise ValueError("causal inquiry route changed structure")
    for thing_id in route.thing_ids:
        _sha(thing_id, "causal inquiry THING")
    for sense, physical in route.matching_route_keys:
        if sense not in _SENSE_INDEX:
            raise ValueError("causal inquiry route sense changed")
        _sha(physical, "causal inquiry route physical value")


@dataclass(frozen=True, slots=True)
class CausalInquiryProfile:
    profile_id: str
    max_witnesses: int
    max_bindings: int
    max_roots_per_witness: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_witnesses: int,
        max_bindings: int,
        max_roots_per_witness: int,
        max_state_bytes: int,
    ) -> "CausalInquiryProfile":
        provisional = cls(
            profile_id=_ascii_identifier(
                profile_id,
                "causal inquiry profile",
            ),
            max_witnesses=_capacity(
                max_witnesses,
                "causal inquiry witness capacity",
                _MAX_CONFIGURED_RECORDS,
            ),
            max_bindings=_capacity(
                max_bindings,
                "causal inquiry binding capacity",
                _MAX_CONFIGURED_RECORDS,
            ),
            max_roots_per_witness=_capacity(
                max_roots_per_witness,
                "causal inquiry root capacity",
                _MAX_CONFIGURED_ROOTS,
            ),
            max_state_bytes=_capacity(
                max_state_bytes,
                "causal inquiry state capacity",
                _MAX_CONFIGURED_STATE_BYTES,
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_witnesses=provisional.max_witnesses,
            max_bindings=provisional.max_bindings,
            max_roots_per_witness=(
                provisional.max_roots_per_witness
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_bindings": self.max_bindings,
            "max_roots_per_witness": self.max_roots_per_witness,
            "max_state_bytes": self.max_state_bytes,
            "max_witnesses": self.max_witnesses,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }

    def verify(self) -> None:
        _ascii_identifier(self.profile_id, "causal inquiry profile")
        _capacity(
            self.max_witnesses,
            "causal inquiry witness capacity",
            _MAX_CONFIGURED_RECORDS,
        )
        _capacity(
            self.max_bindings,
            "causal inquiry binding capacity",
            _MAX_CONFIGURED_RECORDS,
        )
        _capacity(
            self.max_roots_per_witness,
            "causal inquiry root capacity",
            _MAX_CONFIGURED_ROOTS,
        )
        _capacity(
            self.max_state_bytes,
            "causal inquiry state capacity",
            _MAX_CONFIGURED_STATE_BYTES,
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("causal inquiry profile authority changed")


@dataclass(frozen=True, slots=True)
class InquiryWitness:
    sequence: int
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    custody_capability_receipt_sha256: str
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    source_time_start: Fraction
    source_time_end: Fraction
    origin: str
    world_observation_receipt_sha256: str
    world_observation_revision: int
    world_execution_receipt_sha256: str | None
    world_before_receipt_sha256: str | None
    world_after_receipt_sha256: str | None
    world_before_revision: int | None
    world_after_revision: int | None
    observed_senses: tuple[str, ...]
    boundary_receipts: tuple[tuple[str, str], ...]
    full_field_roots: tuple[FullFieldSensoryRoot, ...]
    route_state: str
    thing_ids: tuple[str, ...]
    matching_route_keys: tuple[tuple[str, str], ...]
    prior_witness_receipt_sha256: str | None
    causal_continuation_relation: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    @property
    def has_causal_predecessor(self) -> bool:
        return self.prior_witness_receipt_sha256 is not None

    def payload(self) -> dict[str, object]:
        return {
            "boundary_receipts": [
                [sense, receipt]
                for sense, receipt in self.boundary_receipts
            ],
            "custody_capability_receipt_sha256": (
                self.custody_capability_receipt_sha256
            ),
            "full_field_roots": [
                value.record() for value in self.full_field_roots
            ],
            "matching_route_keys": [
                [sense, value]
                for sense, value in self.matching_route_keys
            ],
            "observed_senses": list(self.observed_senses),
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "prior_witness_receipt_sha256": (
                self.prior_witness_receipt_sha256
            ),
            "causal_continuation_relation": (
                self.causal_continuation_relation
            ),
            "origin": self.origin,
            "route_state": self.route_state,
            "schema": WITNESS_SCHEMA,
            "sequence": self.sequence,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_time_end": _fraction_text(
                self.source_time_end
            ),
            "source_time_start": _fraction_text(
                self.source_time_start
            ),
            "source_occurrence_id": self.source_occurrence_id,
            "thing_ids": list(self.thing_ids),
            "world_after_receipt_sha256": (
                self.world_after_receipt_sha256
            ),
            "world_after_revision": self.world_after_revision,
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_before_revision": self.world_before_revision,
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_observation_revision": (
                self.world_observation_revision
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InquiryNeed:
    need_id: str
    witness_receipt_sha256: str
    origin: str
    route_state: str
    action_role: str
    meaning_authority: bool
    word_authority: bool
    label_authority: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_role": self.action_role,
            "label_authority": self.label_authority,
            "meaning_authority": self.meaning_authority,
            "need_id": self.need_id,
            "origin": self.origin,
            "route_state": self.route_state,
            "schema": NEED_SCHEMA,
            "witness_receipt_sha256": self.witness_receipt_sha256,
            "word_authority": self.word_authority,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InquiryActionBinding:
    binding_id: str
    program_id: str
    program_authority_receipt_sha256: str
    learning_witness_receipt_sha256: str
    attempt_receipt_sha256: str
    exploratory_tutor_authorization: (
        CausalInquiryTutorAuthorizationReceipt | None
    )
    fresh_articulatory_receipt: (
        FreshArticulatorySelfAcousticCustodyReceipt
    )
    companion_episode_intent: (
        CompanionVocalEpisodeIntentReceipt | None
    )
    tutor_response: ActionExecutionReceipt
    later_source_occurrence_id: str
    later_custody_receipt_sha256: str
    later_custody_capability_receipt_sha256: str
    later_settlement_receipt_sha256: str
    prior_route_state: str
    prior_thing_ids: tuple[str, ...]
    later_route_state: str
    later_thing_ids: tuple[str, ...]
    later_boundary_receipts: tuple[tuple[str, str], ...]
    later_full_field_roots: tuple[FullFieldSensoryRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "attempt_receipt_sha256": self.attempt_receipt_sha256,
            "binding_id": self.binding_id,
            "companion_episode_intent": (
                None
                if self.companion_episode_intent is None
                else {
                    **self.companion_episode_intent.payload(),
                    "authority_hmac_sha256": (
                        self.companion_episode_intent
                        .authority_hmac_sha256
                    ),
                    "authority_receipt_sha256": (
                        self.companion_episode_intent
                        .authority_receipt_sha256
                    ),
                }
            ),
            "fresh_articulatory_receipt": (
                self.fresh_articulatory_receipt.record()
            ),
            "exploratory_tutor_authorization": (
                None
                if self.exploratory_tutor_authorization is None
                else self.exploratory_tutor_authorization.record()
            ),
            "later_boundary_receipts": [
                [sense, receipt]
                for sense, receipt in self.later_boundary_receipts
            ],
            "later_custody_capability_receipt_sha256": (
                self.later_custody_capability_receipt_sha256
            ),
            "later_custody_receipt_sha256": (
                self.later_custody_receipt_sha256
            ),
            "later_full_field_roots": [
                value.record()
                for value in self.later_full_field_roots
            ],
            "later_route_state": self.later_route_state,
            "later_settlement_receipt_sha256": (
                self.later_settlement_receipt_sha256
            ),
            "later_source_occurrence_id": (
                self.later_source_occurrence_id
            ),
            "later_thing_ids": list(self.later_thing_ids),
            "learning_witness_receipt_sha256": (
                self.learning_witness_receipt_sha256
            ),
            "prior_route_state": self.prior_route_state,
            "prior_thing_ids": list(self.prior_thing_ids),
            "program_authority_receipt_sha256": (
                self.program_authority_receipt_sha256
            ),
            "program_id": self.program_id,
            "schema": BINDING_SCHEMA,
            "tutor_response": self.tutor_response.as_record(),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InquiryOpportunity:
    opportunity_id: str
    witness_receipt_sha256: str
    binding_receipt_sha256: str
    program_id: str
    owner_state_sha256: str
    action_role: str
    meaning_authority: bool
    word_authority: bool
    label_authority: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_role": self.action_role,
            "binding_receipt_sha256": (
                self.binding_receipt_sha256
            ),
            "label_authority": self.label_authority,
            "meaning_authority": self.meaning_authority,
            "opportunity_id": self.opportunity_id,
            "owner_state_sha256": self.owner_state_sha256,
            "program_id": self.program_id,
            "schema": OPPORTUNITY_SCHEMA,
            "witness_receipt_sha256": (
                self.witness_receipt_sha256
            ),
            "word_authority": self.word_authority,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InquiryAttempt:
    mode: str
    witness_receipt_sha256: str
    opportunity_receipt_sha256: str | None
    tutor_authorization: (
        CausalInquiryTutorAuthorizationReceipt | None
    )
    program_id: str
    fresh_articulatory_receipt: (
        FreshArticulatorySelfAcousticCustodyReceipt
    )
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "fresh_articulatory_receipt": (
                self.fresh_articulatory_receipt.record()
            ),
            "mode": self.mode,
            "opportunity_receipt_sha256": (
                self.opportunity_receipt_sha256
            ),
            "tutor_authorization": (
                None
                if self.tutor_authorization is None
                else self.tutor_authorization.record()
            ),
            "program_id": self.program_id,
            "schema": ATTEMPT_SCHEMA,
            "witness_receipt_sha256": (
                self.witness_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
        }


@dataclass(frozen=True, slots=True)
class InquiryDecision:
    state: str
    reason: str
    witness_receipt_sha256: str
    candidate_program_ids: tuple[str, ...]
    opportunity: InquiryOpportunity | None
    meaning_authority: bool = False
    word_authority: bool = False
    label_authority: bool = False


@dataclass(frozen=True, slots=True)
class InquiryAttemptAbandonment:
    reason: str
    attempt_receipt_sha256: str
    tutor_response_receipt_sha256: str | None
    later_settlement_receipt_sha256: str | None
    later_route_state: str | None
    binding_created: bool = False
    opportunity_created: bool = False


@dataclass(frozen=True, slots=True)
class BodyOwnedFragmentInquiryClosure:
    need_receipt_sha256: str
    witness_receipt_sha256: str
    fragment_receipt_sha256: str
    pending_custody_receipt_sha256: str
    consequence_settlement_receipt_sha256: str
    program_authority_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "consequence_settlement_receipt_sha256": (
                self.consequence_settlement_receipt_sha256
            ),
            "fragment_receipt_sha256": self.fragment_receipt_sha256,
            "need_receipt_sha256": self.need_receipt_sha256,
            "pending_custody_receipt_sha256": (
                self.pending_custody_receipt_sha256
            ),
            "program_authority_receipt_sha256": (
                self.program_authority_receipt_sha256
            ),
            "schema": BODY_OWNED_FRAGMENT_CLOSURE_SCHEMA,
            "witness_receipt_sha256": self.witness_receipt_sha256,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class _InquiryState:
    witnesses: tuple[InquiryWitness, ...]
    bindings: tuple[InquiryActionBinding, ...]
    active_need: InquiryNeed | None
    pending_needs: tuple[InquiryNeed, ...]
    active_opportunity: InquiryOpportunity | None
    pending_attempt: InquiryAttempt | None


@dataclass(slots=True)
class _MutationState:
    phase: str


@dataclass(frozen=True, slots=True)
class PreparedCausalInquiryMutation:
    operation: str
    result: object
    _prior_state: _InquiryState = field(repr=False)
    _staged_state: _InquiryState = field(repr=False)
    _transaction_state: _MutationState = field(
        repr=False,
        compare=False,
    )
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class CausalInquiryUndo:
    _prepared: PreparedCausalInquiryMutation = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)
    _construction_authority: object = field(
        repr=False,
        compare=False,
    )


class CausalInquiryCapacityError(RuntimeError):
    """A configured durable resource boundary refused publication."""


class CausalInquiryOwner:
    """Own bounded uncertainty-to-tutor-action causal relations."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: CausalInquiryProfile,
        thing_owner: CausalThingMosaicOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        fresh_articulatory_authority: (
            FreshArticulatorySelfAcousticCustodyAuthority
        ),
        companion_vocal_authority: (
            W1CompanionVocalExperienceAuthority
        ),
        world_authority: EmbodimentWorldAuthority,
        tutor_authorization_verifier: (
            CausalInquiryTutorAuthorizationVerifier
        ),
    ) -> None:
        self._key = _key(authority_key)
        if not isinstance(profile, CausalInquiryProfile):
            raise TypeError("causal inquiry profile is not typed")
        profile.verify()
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError("causal inquiry requires its THING owner")
        if not isinstance(
            articulatory_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "causal inquiry requires its articulatory owner"
            )
        if not isinstance(
            fresh_articulatory_authority,
            FreshArticulatorySelfAcousticCustodyAuthority,
        ):
            raise TypeError(
                "causal inquiry requires fresh articulatory custody"
            )
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("causal inquiry requires its world authority")
        if not isinstance(
            tutor_authorization_verifier,
            CausalInquiryTutorAuthorizationVerifier,
        ):
            raise TypeError(
                "causal inquiry requires external tutor authorization "
                "verification"
            )
        if not isinstance(
            companion_vocal_authority,
            W1CompanionVocalExperienceAuthority,
        ):
            raise TypeError(
                "causal inquiry requires companion vocal authority"
            )
        if (
            companion_vocal_authority._world is not world_authority
            or companion_vocal_authority._companion_port_id
            != SECOND_BODY_PORT_ID
        ):
            raise ValueError(
                "causal inquiry crossed companion vocal ownership"
            )
        fresh_articulatory_authority.verify_dependency_ownership(
            articulatory_owner=articulatory_owner,
            world_authority=world_authority,
        )
        fresh_articulatory_authority.verify_world_ownership(
            world_authority=world_authority,
        )
        self._profile = profile
        self._things = thing_owner
        self._articulatory = articulatory_owner
        self._fresh = fresh_articulatory_authority
        self._companion = companion_vocal_authority
        self._world = world_authority
        self._tutor_authorization_verifier = (
            tutor_authorization_verifier
        )
        self._witness_key = hashlib.sha256(
            _WITNESS_DOMAIN + self._key
        ).digest()
        self._need_key = hashlib.sha256(
            _NEED_DOMAIN + self._key
        ).digest()
        self._binding_key = hashlib.sha256(
            _BINDING_DOMAIN + self._key
        ).digest()
        self._opportunity_key = hashlib.sha256(
            _OPPORTUNITY_DOMAIN + self._key
        ).digest()
        self._attempt_key = hashlib.sha256(
            _ATTEMPT_DOMAIN + self._key
        ).digest()
        self._body_owned_fragment_closure_key = hashlib.sha256(
            _BODY_OWNED_FRAGMENT_CLOSURE_DOMAIN + self._key
        ).digest()
        self._state_key = hashlib.sha256(
            _STATE_DOMAIN + self._key
        ).digest()
        self._state = _InquiryState(
            witnesses=(),
            bindings=(),
            active_need=None,
            pending_needs=(),
            active_opportunity=None,
            pending_attempt=None,
        )
        self._prepared: PreparedCausalInquiryMutation | None = None
        self._latest_undo_prepared: (
            PreparedCausalInquiryMutation | None
        ) = None
        self._owner_authority = object()
        self._lock = threading.RLock()

    @property
    def witnesses(self) -> tuple[InquiryWitness, ...]:
        with self._lock:
            return self._state.witnesses

    @property
    def bindings(self) -> tuple[InquiryActionBinding, ...]:
        with self._lock:
            return self._state.bindings

    @property
    def active_opportunity(self) -> InquiryOpportunity | None:
        with self._lock:
            return self._state.active_opportunity

    @property
    def active_need(self) -> InquiryNeed | None:
        with self._lock:
            return self._state.active_need

    @property
    def pending_needs(self) -> tuple[InquiryNeed, ...]:
        with self._lock:
            return self._state.pending_needs

    @property
    def pending_attempt(self) -> InquiryAttempt | None:
        with self._lock:
            return self._state.pending_attempt

    def retained_need_for_witness(
        self,
        witness: InquiryWitness,
    ) -> InquiryNeed:
        """Return the one active-or-pending need owned by this witness."""

        with self._lock:
            self._verify_witness(witness)
            retained = self._witness_by_receipt(
                witness.authority_receipt_sha256
            )
            if retained != witness:
                raise ValueError(
                    "causal inquiry witness changed before need lookup"
                )
            matches = tuple(
                need
                for need in (
                    (
                        ()
                        if self._state.active_need is None
                        else (self._state.active_need,)
                    )
                    + self._state.pending_needs
                )
                if need.witness_receipt_sha256
                == witness.authority_receipt_sha256
            )
            if len(matches) != 1:
                raise ValueError(
                    "causal inquiry witness has no unique retained need"
                )
            self._verify_need(matches[0], require_active=False)
            return matches[0]

    def _owned_program(self, program_id: str) -> ArticulatoryProgram:
        _sha(program_id, "causal inquiry articulatory program")
        matches = tuple(
            value
            for value in self._articulatory.programs
            if value.program_id == program_id
        )
        if len(matches) != 1:
            raise ValueError(
                "causal inquiry program is not uniquely retained"
            )
        matches[0].verify()
        return matches[0]

    def _witness_by_receipt(self, receipt: str) -> InquiryWitness:
        _sha(receipt, "causal inquiry witness")
        matches = tuple(
            value
            for value in self._state.witnesses
            if value.authority_receipt_sha256 == receipt
        )
        if len(matches) != 1:
            raise ValueError("causal inquiry witness is not retained")
        self._verify_witness(matches[0])
        return matches[0]

    @staticmethod
    def _boundary_receipts(
        view: SettledExperienceConsumerView,
    ) -> tuple[tuple[str, str], ...]:
        observed = tuple(
            value
            for value in view.causal_settlement.interpretations
            if value.state == "observed"
        )
        if len({value.sense for value in observed}) < 2:
            raise ValueError(
                "causal inquiry requires at least two observed senses"
            )
        if any(
            not value.substreams
            for value in observed
        ):
            raise ValueError(
                "causal inquiry observed sense has no full-field boundary"
            )
        result = tuple(
            sorted(
                (
                    (
                        value.sense,
                        _sha(
                            value.boundary_receipt_sha256,
                            "causal inquiry sense boundary",
                        ),
                    )
                    for value in observed
                ),
                key=lambda value: _SENSE_INDEX[value[0]],
            )
        )
        return result

    def _open_lived_child(
        self,
        authority: SettledExperienceCustodyAuthority,
        capability: SettledExperienceConsumerCapability,
    ) -> SettledExperienceConsumerView:
        if not isinstance(authority, SettledExperienceCustodyAuthority):
            raise TypeError(
                "causal inquiry requires settled-experience custody"
            )
        if (
            not isinstance(
                capability,
                SettledExperienceConsumerCapability,
            )
            or capability.consumer_id != CAUSAL_INQUIRY_CONSUMER_ID
        ):
            raise ValueError(
                "causal inquiry requires its custody capability"
            )
        view = authority.open_child(capability)
        settlement = view.causal_settlement
        settlement.verify()
        if settlement.language_events or settlement.routing_chis:
            raise ValueError(
                "causal inquiry rejects symbolic or chi authority"
            )
        return view

    def _lived_evidence(
        self,
        view: SettledExperienceConsumerView,
    ) -> tuple[
        tuple[str, ...],
        tuple[tuple[str, str], ...],
        tuple[FullFieldSensoryRoot, ...],
    ]:
        boundaries = self._boundary_receipts(view)
        senses = tuple(sense for sense, _receipt in boundaries)
        roots = full_field_sensory_roots(
            view.causal_settlement
        )
        if len(roots) > self._profile.max_roots_per_witness:
            raise CausalInquiryCapacityError(
                "causal inquiry root capacity exhausted"
            )
        for root in roots:
            _verify_complete_root(root)
        if not set(senses).issubset({
            value.sense for value in roots
        }):
            raise ValueError(
                "causal inquiry boundaries lost their full-field roots"
            )
        return senses, boundaries, roots

    def _causal_continuation_predecessors(
        self,
        witness: InquiryWitness,
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        if witness.world_after_receipt_sha256 is not None:
            result[witness.world_after_receipt_sha256] = (
                "exact_world_transition"
            )
        for binding in self._state.bindings:
            if (
                binding.learning_witness_receipt_sha256
                == witness.authority_receipt_sha256
                and binding.fresh_articulatory_receipt
                .world_before_receipt_sha256
                == witness.world_after_receipt_sha256
            ):
                result[
                    binding.tutor_response.after
                    .authority_receipt_sha256
                ] = "exact_inquiry_resolution_chain"
        return result

    def _seal_witness(
        self,
        *,
        sequence: int,
        view: SettledExperienceConsumerView,
        capability: SettledExperienceConsumerCapability,
        senses: tuple[str, ...],
        boundaries: tuple[tuple[str, str], ...],
        roots: tuple[FullFieldSensoryRoot, ...],
        route: CausalThingRoute,
        prior: InquiryWitness | None,
        causal_continuation_relation: str,
    ) -> InquiryWitness:
        execution = view.world_execution
        observation = view.world_observation
        provisional = InquiryWitness(
            sequence=sequence,
            source_occurrence_id=view.source_occurrence_id,
            parent_custody_receipt_sha256=(
                view.parent_custody_receipt_sha256
            ),
            custody_capability_receipt_sha256=(
                capability.authority_receipt_sha256
            ),
            settlement_receipt_sha256=(
                view.causal_settlement.authority_receipt_sha256
            ),
            settlement_structural_fingerprint=(
                view.causal_settlement.structural_fingerprint
            ),
            source_time_start=(
                view.causal_settlement.source_time_start
            ),
            source_time_end=(
                view.causal_settlement.source_time_end
            ),
            origin=(
                "active_execution"
                if execution is not None
                else "passive_observation"
            ),
            world_observation_receipt_sha256=(
                observation.authority_receipt_sha256
            ),
            world_observation_revision=observation.revision,
            world_execution_receipt_sha256=(
                execution.authority_receipt_sha256
                if execution is not None else None
            ),
            world_before_receipt_sha256=(
                execution.before.authority_receipt_sha256
                if execution is not None else None
            ),
            world_after_receipt_sha256=(
                execution.after.authority_receipt_sha256
                if execution is not None else None
            ),
            world_before_revision=(
                execution.before.revision
                if execution is not None else None
            ),
            world_after_revision=(
                execution.after.revision
                if execution is not None else None
            ),
            observed_senses=senses,
            boundary_receipts=boundaries,
            full_field_roots=roots,
            route_state=route.state,
            thing_ids=route.thing_ids,
            matching_route_keys=route.matching_route_keys,
            prior_witness_receipt_sha256=(
                prior.authority_receipt_sha256
                if prior is not None else None
            ),
            causal_continuation_relation=(
                causal_continuation_relation
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._witness_key,
            _WITNESS_DOMAIN,
            provisional.payload(),
        )
        result = InquiryWitness(
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
        self._verify_witness(result)
        return result

    def _verify_witness(self, value: InquiryWitness) -> None:
        if not isinstance(value, InquiryWitness):
            raise TypeError("causal inquiry witness is not typed")
        if (
            isinstance(value.sequence, bool)
            or not isinstance(value.sequence, int)
            or value.sequence <= 0
            or value.route_state not in _ROUTE_STATES
            or value.origin
            not in {"active_execution", "passive_observation"}
            or value.causal_continuation_relation
            not in _CONTINUATION_RELATIONS
            or (
                value.prior_witness_receipt_sha256 is None
            ) != (
                value.causal_continuation_relation == "genesis"
            )
            or len(value.observed_senses) < 2
            or value.observed_senses
            != tuple(sorted(
                set(value.observed_senses),
                key=_SENSE_INDEX.__getitem__,
            ))
            or tuple(
                sense for sense, _receipt in value.boundary_receipts
            ) != value.observed_senses
            or not value.full_field_roots
            or len(value.full_field_roots)
            > self._profile.max_roots_per_witness
            or not isinstance(value.source_time_start, Fraction)
            or not isinstance(value.source_time_end, Fraction)
            or value.source_time_end <= value.source_time_start
        ):
            raise ValueError("causal inquiry witness structure changed")
        active_world = (
            value.world_execution_receipt_sha256,
            value.world_before_receipt_sha256,
            value.world_after_receipt_sha256,
            value.world_before_revision,
            value.world_after_revision,
        )
        if value.origin == "passive_observation":
            if (
                any(item is not None for item in active_world)
                or value.prior_witness_receipt_sha256 is not None
                or value.causal_continuation_relation != "genesis"
            ):
                raise ValueError(
                    "passive inquiry witness invented a causal edge"
                )
        elif (
            any(item is None for item in active_world)
            or value.world_after_revision
            != value.world_before_revision + 1
            or value.world_observation_receipt_sha256
            != value.world_after_receipt_sha256
            or value.world_observation_revision
            != value.world_after_revision
        ):
            raise ValueError(
                "active inquiry witness lost its causal edge"
            )
        for digest, label in (
            (value.source_occurrence_id, "witness occurrence"),
            (
                value.parent_custody_receipt_sha256,
                "witness custody",
            ),
            (
                value.custody_capability_receipt_sha256,
                "witness capability",
            ),
            (value.settlement_receipt_sha256, "witness settlement"),
            (
                value.settlement_structural_fingerprint,
                "witness structure",
            ),
            (
                value.world_observation_receipt_sha256,
                "witness world observation",
            ),
            (value.authority_hmac_sha256, "witness HMAC"),
            (value.authority_receipt_sha256, "witness authority"),
        ):
            _sha(digest, f"causal inquiry {label}")
        for digest, label in (
            (
                value.world_execution_receipt_sha256,
                "witness execution",
            ),
            (value.world_before_receipt_sha256, "witness world before"),
            (value.world_after_receipt_sha256, "witness world after"),
        ):
            if digest is not None:
                _sha(digest, f"causal inquiry {label}")
        if value.prior_witness_receipt_sha256 is not None:
            _sha(
                value.prior_witness_receipt_sha256,
                "causal inquiry prior witness",
            )
        for sense, receipt in value.boundary_receipts:
            if sense not in _SENSE_INDEX:
                raise ValueError(
                    "causal inquiry witness sense changed"
                )
            _sha(receipt, "causal inquiry boundary")
        for root in value.full_field_roots:
            _verify_complete_root(root)
        _route_shape(
            CausalThingRoute(
                state=value.route_state,
                thing_ids=value.thing_ids,
                matching_route_keys=value.matching_route_keys,
            ),
            allow_unique=value.route_state == "unique",
        )
        signature = _sign(
            self._witness_key,
            _WITNESS_DOMAIN,
            value.payload(),
        )
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
            raise ValueError(
                "causal inquiry witness authority changed"
            )

    def _seal_need(self, witness: InquiryWitness) -> InquiryNeed:
        identity = _digest({
            "schema": "guala.causal_inquiry.need_identity.v1",
            "witness_receipt_sha256": (
                witness.authority_receipt_sha256
            ),
        })
        provisional = InquiryNeed(
            need_id=identity,
            witness_receipt_sha256=(
                witness.authority_receipt_sha256
            ),
            origin=witness.origin,
            route_state=witness.route_state,
            action_role="request_tutor_attention",
            meaning_authority=False,
            word_authority=False,
            label_authority=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._need_key,
            _NEED_DOMAIN,
            provisional.payload(),
        )
        result = InquiryNeed(
            need_id=provisional.need_id,
            witness_receipt_sha256=(
                provisional.witness_receipt_sha256
            ),
            origin=provisional.origin,
            route_state=provisional.route_state,
            action_role=provisional.action_role,
            meaning_authority=False,
            word_authority=False,
            label_authority=False,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_need(result, require_active=False)
        return result

    def _verify_need(
        self,
        value: InquiryNeed,
        *,
        require_active: bool,
    ) -> None:
        if not isinstance(value, InquiryNeed):
            raise TypeError("causal inquiry need is not typed")
        for digest, label in (
            (value.need_id, "need identity"),
            (value.witness_receipt_sha256, "need witness"),
            (value.authority_hmac_sha256, "need HMAC"),
            (value.authority_receipt_sha256, "need authority"),
        ):
            _sha(digest, f"causal inquiry {label}")
        if (
            value.origin
            not in {"active_execution", "passive_observation"}
            or value.route_state not in _ROUTE_STATES
            or value.action_role != "request_tutor_attention"
            or value.meaning_authority
            or value.word_authority
            or value.label_authority
        ):
            raise ValueError("causal inquiry need claimed meaning")
        signature = _sign(
            self._need_key,
            _NEED_DOMAIN,
            value.payload(),
        )
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
            raise ValueError("causal inquiry need authority changed")
        if require_active and self._state.active_need != value:
            raise ValueError("causal inquiry need is not active")

    def _state_after_active_need_closure(
        self,
        *,
        bindings: tuple[InquiryActionBinding, ...],
    ) -> _InquiryState:
        """Advance exact witness-ordered inquiry custody by one need."""

        if self._state.active_need is None:
            raise ValueError(
                "causal inquiry cannot advance an absent active need"
            )
        promoted = (
            self._state.pending_needs[0]
            if self._state.pending_needs
            else None
        )
        remaining = (
            self._state.pending_needs[1:]
            if self._state.pending_needs
            else ()
        )
        return _InquiryState(
            witnesses=self._state.witnesses,
            bindings=bindings,
            active_need=promoted,
            pending_needs=remaining,
            active_opportunity=None,
            pending_attempt=None,
        )

    def _body(self, state: _InquiryState) -> dict[str, object]:
        return {
            "active_need": (
                state.active_need.record()
                if state.active_need is not None
                else None
            ),
            "active_opportunity": (
                state.active_opportunity.record()
                if state.active_opportunity is not None
                else None
            ),
            "bindings": [
                value.record() for value in state.bindings
            ],
            "pending_needs": [
                value.record() for value in state.pending_needs
            ],
            "pending_attempt": (
                state.pending_attempt.record()
                if state.pending_attempt is not None
                else None
            ),
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
            "witnesses": [
                value.record() for value in state.witnesses
            ],
        }

    def _encoded(self, state: _InquiryState) -> bytes:
        self._verify_state(state)
        body = self._body(state)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": _sign(
                self._state_key,
                _STATE_DOMAIN,
                body,
            ),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise CausalInquiryCapacityError(
                "causal inquiry state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "causal inquiry cannot snapshot an active mutation"
                )
            return self._encoded(self._state)

    def _state_sha(self, state: _InquiryState) -> str:
        return hashlib.sha256(self._encoded(state)).hexdigest()

    def _prepare(
        self,
        *,
        operation: str,
        result: object,
        staged: _InquiryState,
    ) -> PreparedCausalInquiryMutation:
        if self._prepared is not None:
            raise RuntimeError(
                "causal inquiry already has a prepared mutation"
            )
        self._encoded(staged)
        prepared = PreparedCausalInquiryMutation(
            operation=operation,
            result=result,
            _prior_state=self._state,
            _staged_state=staged,
            _transaction_state=_MutationState("prepared"),
            _owner_authority=self._owner_authority,
            _construction_authority=_PREPARED_AUTHORITY,
        )
        self._prepared = prepared
        return prepared

    def _verify_prepared(
        self,
        prepared: PreparedCausalInquiryMutation,
    ) -> None:
        if (
            not isinstance(prepared, PreparedCausalInquiryMutation)
            or prepared._construction_authority
            is not _PREPARED_AUTHORITY
            or prepared._owner_authority
            is not self._owner_authority
            or self._prepared is not prepared
            or prepared._transaction_state.phase != "prepared"
            or self._state != prepared._prior_state
        ):
            raise ValueError(
                "causal inquiry prepared mutation changed custody"
            )
        self._encoded(prepared._prior_state)
        self._encoded(prepared._staged_state)

    def commit_prepared(
        self,
        prepared: PreparedCausalInquiryMutation,
    ) -> CausalInquiryUndo:
        with self._lock:
            self._verify_prepared(prepared)
            self._state = prepared._staged_state
            self._prepared = None
            prepared._transaction_state.phase = "committed"
            self._latest_undo_prepared = prepared
            return CausalInquiryUndo(
                _prepared=prepared,
                _owner_authority=self._owner_authority,
                _construction_authority=_UNDO_AUTHORITY,
            )

    def discard_prepared(
        self,
        prepared: PreparedCausalInquiryMutation,
    ) -> None:
        with self._lock:
            self._verify_prepared(prepared)
            self._prepared = None
            prepared._transaction_state.phase = "discarded"

    def rollback_committed(
        self,
        undo: CausalInquiryUndo,
    ) -> None:
        if (
            not isinstance(undo, CausalInquiryUndo)
            or undo._construction_authority is not _UNDO_AUTHORITY
            or undo._owner_authority is not self._owner_authority
        ):
            raise ValueError("causal inquiry undo changed custody")
        with self._lock:
            prepared = undo._prepared
            if (
                prepared._owner_authority is not self._owner_authority
                or prepared._transaction_state.phase != "committed"
                or self._latest_undo_prepared is not prepared
                or self._prepared is not None
                or self._state != prepared._staged_state
            ):
                raise ValueError("causal inquiry undo is stale")
            self._encoded(prepared._prior_state)
            self._state = prepared._prior_state
            self._latest_undo_prepared = None
            prepared._transaction_state.phase = "rolled_back"

    def verify_committed(
        self,
        undo: CausalInquiryUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(undo, CausalInquiryUndo)
                or undo._construction_authority is not _UNDO_AUTHORITY
                or undo._owner_authority is not self._owner_authority
            ):
                raise ValueError("causal inquiry undo changed custody")
            prepared = undo._prepared
            if (
                prepared._owner_authority is not self._owner_authority
                or prepared._transaction_state.phase != "committed"
                or self._latest_undo_prepared is not prepared
                or self._prepared is not None
                or self._state != prepared._staged_state
            ):
                raise ValueError("causal inquiry undo is stale")
            self._encoded(prepared._staged_state)

    def finalize_committed(
        self,
        undo: CausalInquiryUndo,
    ) -> None:
        with self._lock:
            self.verify_committed(undo)
            prepared = undo._prepared
            self._latest_undo_prepared = None
            prepared._transaction_state.phase = "finalized"

    def _seal_body_owned_fragment_closure(
        self,
        *,
        need: InquiryNeed,
        witness: InquiryWitness,
        fragment_receipt_sha256: str,
        pending_custody_receipt_sha256: str,
        consequence_settlement_receipt_sha256: str,
        program_authority_receipt_sha256: str,
    ) -> BodyOwnedFragmentInquiryClosure:
        provisional = BodyOwnedFragmentInquiryClosure(
            need_receipt_sha256=need.authority_receipt_sha256,
            witness_receipt_sha256=witness.authority_receipt_sha256,
            fragment_receipt_sha256=_sha(
                fragment_receipt_sha256,
                "body-owned fragment inquiry fragment",
            ),
            pending_custody_receipt_sha256=_sha(
                pending_custody_receipt_sha256,
                "body-owned fragment inquiry pending custody",
            ),
            consequence_settlement_receipt_sha256=_sha(
                consequence_settlement_receipt_sha256,
                "body-owned fragment inquiry consequence",
            ),
            program_authority_receipt_sha256=_sha(
                program_authority_receipt_sha256,
                "body-owned fragment inquiry program",
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._body_owned_fragment_closure_key,
            _BODY_OWNED_FRAGMENT_CLOSURE_DOMAIN,
            provisional.payload(),
        )
        return BodyOwnedFragmentInquiryClosure(
            need_receipt_sha256=provisional.need_receipt_sha256,
            witness_receipt_sha256=provisional.witness_receipt_sha256,
            fragment_receipt_sha256=provisional.fragment_receipt_sha256,
            pending_custody_receipt_sha256=(
                provisional.pending_custody_receipt_sha256
            ),
            consequence_settlement_receipt_sha256=(
                provisional.consequence_settlement_receipt_sha256
            ),
            program_authority_receipt_sha256=(
                provisional.program_authority_receipt_sha256
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def verify_body_owned_fragment_closure(
        self,
        value: BodyOwnedFragmentInquiryClosure,
    ) -> None:
        if not isinstance(value, BodyOwnedFragmentInquiryClosure):
            raise TypeError(
                "body-owned fragment inquiry closure is not typed"
            )
        for digest, name in (
            (value.need_receipt_sha256, "body-owned closure need"),
            (value.witness_receipt_sha256, "body-owned closure witness"),
            (value.fragment_receipt_sha256, "body-owned closure fragment"),
            (
                value.pending_custody_receipt_sha256,
                "body-owned closure pending custody",
            ),
            (
                value.consequence_settlement_receipt_sha256,
                "body-owned closure consequence",
            ),
            (
                value.program_authority_receipt_sha256,
                "body-owned closure program",
            ),
            (value.authority_hmac_sha256, "body-owned closure HMAC"),
            (
                value.authority_receipt_sha256,
                "body-owned closure authority",
            ),
        ):
            _sha(digest, name)
        expected = _sign(
            self._body_owned_fragment_closure_key,
            _BODY_OWNED_FRAGMENT_CLOSURE_DOMAIN,
            value.payload(),
        )
        if (
            not hmac.compare_digest(
                expected,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": value.payload(),
            })
        ):
            raise ValueError(
                "body-owned fragment inquiry closure authority changed"
            )

    def prepare_body_owned_fragment_closure(
        self,
        *,
        need: InquiryNeed,
        witness: InquiryWitness,
        fragment_receipt_sha256: str,
        pending_custody_receipt_sha256: str,
        consequence_settlement_receipt_sha256: str,
        program_authority_receipt_sha256: str,
    ) -> PreparedCausalInquiryMutation:
        """Prepare exact need closure without the retired binding chain."""

        with self._lock:
            self._verify_need(need, require_active=True)
            self._verify_witness(witness)
            if (
                self._state.active_need != need
                or need.witness_receipt_sha256
                != witness.authority_receipt_sha256
                or sum(
                    retained == witness
                    for retained in self._state.witnesses
                )
                != 1
                or witness.route_state not in _ROUTE_STATES
                or self._state.active_opportunity is not None
                or self._state.pending_attempt is not None
            ):
                raise ValueError(
                    "body-owned fragment closure changed its exact active need"
                )
            closure = self._seal_body_owned_fragment_closure(
                need=need,
                witness=witness,
                fragment_receipt_sha256=fragment_receipt_sha256,
                pending_custody_receipt_sha256=(
                    pending_custody_receipt_sha256
                ),
                consequence_settlement_receipt_sha256=(
                    consequence_settlement_receipt_sha256
                ),
                program_authority_receipt_sha256=(
                    program_authority_receipt_sha256
                ),
            )
            self.verify_body_owned_fragment_closure(closure)
            return self._prepare(
                operation="close_body_owned_fragment",
                result=closure,
                staged=self._state_after_active_need_closure(
                    bindings=self._state.bindings,
                ),
            )

    def prepare_witness(
        self,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
        prior_witness: InquiryWitness | None = None,
        passive_relation_gap_authority: (
            PassiveWholeOrganismThingLearningOwner | None
        ) = None,
        passive_relation_gap_capability: (
            PassiveRelationGapCapability | None
        ) = None,
    ) -> PreparedCausalInquiryMutation:
        with self._lock:
            view = self._open_lived_child(
                custody_authority,
                custody_capability,
            )
            senses, boundaries, roots = self._lived_evidence(view)
            route = self._things.route(view.causal_settlement)
            relation_gap = (
                passive_relation_gap_authority is not None
                or passive_relation_gap_capability is not None
            )
            if relation_gap:
                if (
                    not isinstance(
                        passive_relation_gap_authority,
                        PassiveWholeOrganismThingLearningOwner,
                    )
                    or not isinstance(
                        passive_relation_gap_capability,
                        PassiveRelationGapCapability,
                    )
                    or not passive_relation_gap_authority
                    .owns_thing_owner(self._things)
                ):
                    raise ValueError(
                        "causal inquiry relation gap lacks exact passive "
                        "THING ownership"
                    )
                passive_relation_gap_authority.verify_relation_gap_capability(
                    passive_relation_gap_capability
                )
                if (
                    passive_relation_gap_capability
                    .settlement_receipt_sha256
                    != view.causal_settlement.authority_receipt_sha256
                    or (
                        route.state == "unique"
                        and route.thing_ids
                        != (
                            passive_relation_gap_capability.thing_id,
                        )
                    )
                ):
                    raise ValueError(
                        "passive relation gap crossed settled THING custody"
                    )
            elif route.state == "unique":
                raise ValueError(
                    "causal inquiry hands unique routes to the THING "
                    "owner without a passive relation gap"
                )
            _route_shape(
                route,
                allow_unique=route.state == "unique",
            )
            existing = next(
                (
                    value
                    for value in self._state.witnesses
                    if value.source_occurrence_id
                    == view.source_occurrence_id
                ),
                None,
            )
            if prior_witness is None:
                relation = "genesis"
            else:
                retained = self._witness_by_receipt(
                    prior_witness.authority_receipt_sha256
                )
                if retained != prior_witness:
                    raise ValueError(
                        "causal inquiry prior witness changed"
                    )
                execution = view.world_execution
                if execution is None:
                    raise ValueError(
                        "causal inquiry continuation lost its action"
                    )
                relation = self._causal_continuation_predecessors(
                    retained
                ).get(
                    execution.before.authority_receipt_sha256
                )
                if relation is None:
                    raise ValueError(
                        "causal inquiry continuation has no exact causal edge"
                    )
            witness = self._seal_witness(
                sequence=(
                    existing.sequence
                    if existing is not None
                    else len(self._state.witnesses) + 1
                ),
                view=view,
                capability=custody_capability,
                senses=senses,
                boundaries=boundaries,
                roots=roots,
                route=route,
                prior=prior_witness,
                causal_continuation_relation=relation,
            )
            if existing is not None:
                if existing.payload() != witness.payload():
                    raise ValueError(
                        "causal inquiry occurrence crossed custody"
                    )
                witness = existing
                staged = self._state
            else:
                if (
                    len(self._state.witnesses)
                    >= self._profile.max_witnesses
                ):
                    raise CausalInquiryCapacityError(
                        "causal inquiry witness and need capacity exhausted"
                    )
                need = self._seal_need(witness)
                staged = _InquiryState(
                    witnesses=self._state.witnesses + (witness,),
                    bindings=self._state.bindings,
                    active_need=(
                        need
                        if self._state.active_need is None
                        else self._state.active_need
                    ),
                    pending_needs=(
                        self._state.pending_needs
                        if self._state.active_need is None
                        else self._state.pending_needs + (need,)
                    ),
                    active_opportunity=(
                        self._state.active_opportunity
                    ),
                    pending_attempt=self._state.pending_attempt,
                )
            return self._prepare(
                operation="admit_witness",
                result=witness,
                staged=staged,
            )

    def _seal_opportunity(
        self,
        *,
        witness: InquiryWitness,
        binding: InquiryActionBinding,
    ) -> InquiryOpportunity:
        state_sha = self._state_sha(self._state)
        identity = _digest({
            "binding_receipt_sha256": (
                binding.authority_receipt_sha256
            ),
            "owner_state_sha256": state_sha,
            "schema": (
                "guala.causal_inquiry.opportunity_identity.v1"
            ),
            "witness_receipt_sha256": (
                witness.authority_receipt_sha256
            ),
        })
        provisional = InquiryOpportunity(
            opportunity_id=identity,
            witness_receipt_sha256=(
                witness.authority_receipt_sha256
            ),
            binding_receipt_sha256=(
                binding.authority_receipt_sha256
            ),
            program_id=binding.program_id,
            owner_state_sha256=state_sha,
            action_role="attention_seeking_attempt",
            meaning_authority=False,
            word_authority=False,
            label_authority=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._opportunity_key,
            _OPPORTUNITY_DOMAIN,
            provisional.payload(),
        )
        result = InquiryOpportunity(
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
        self._verify_opportunity(result, require_active=False)
        return result

    def _verify_opportunity(
        self,
        value: InquiryOpportunity,
        *,
        require_active: bool,
    ) -> None:
        if not isinstance(value, InquiryOpportunity):
            raise TypeError("causal inquiry opportunity is not typed")
        for digest, label in (
            (value.opportunity_id, "opportunity identity"),
            (value.witness_receipt_sha256, "opportunity witness"),
            (value.binding_receipt_sha256, "opportunity binding"),
            (value.program_id, "opportunity program"),
            (value.owner_state_sha256, "opportunity owner state"),
            (value.authority_hmac_sha256, "opportunity HMAC"),
            (value.authority_receipt_sha256, "opportunity authority"),
        ):
            _sha(digest, f"causal inquiry {label}")
        if (
            value.action_role != "attention_seeking_attempt"
            or value.meaning_authority
            or value.word_authority
            or value.label_authority
        ):
            raise ValueError(
                "causal inquiry opportunity claimed meaning"
            )
        signature = _sign(
            self._opportunity_key,
            _OPPORTUNITY_DOMAIN,
            value.payload(),
        )
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
            raise ValueError(
                "causal inquiry opportunity authority changed"
            )
        if require_active and self._state.active_opportunity != value:
            raise ValueError(
                "causal inquiry opportunity is not active"
            )

    def prepare_resolution(
        self,
        need: InquiryNeed,
    ) -> InquiryDecision | PreparedCausalInquiryMutation:
        with self._lock:
            self._verify_need(need, require_active=True)
            witness = self._witness_by_receipt(
                need.witness_receipt_sha256
            )
            retained = self._witness_by_receipt(
                witness.authority_receipt_sha256
            )
            if retained != witness:
                raise ValueError(
                    "causal inquiry need lost its lived witness"
                )
            if self._state.pending_attempt is not None:
                raise RuntimeError(
                    "causal inquiry already has a pending attempt"
                )
            program_ids = tuple(sorted({
                value.program_id for value in self._state.bindings
            }))
            if not program_ids:
                return InquiryDecision(
                    state="silent",
                    reason="awaiting_explicit_tutor_authorization",
                    witness_receipt_sha256=(
                        witness.authority_receipt_sha256
                    ),
                    candidate_program_ids=(),
                    opportunity=None,
                )
            if len(program_ids) != 1:
                return InquiryDecision(
                    state="action_ambiguous",
                    reason="multiple_learned_tutor_actions",
                    witness_receipt_sha256=(
                        witness.authority_receipt_sha256
                    ),
                    candidate_program_ids=program_ids,
                    opportunity=None,
                )
            binding = next(
                value
                for value in self._state.bindings
                if value.program_id == program_ids[0]
            )
            active = self._state.active_opportunity
            if active is not None:
                self._verify_opportunity(active, require_active=True)
                if (
                    active.witness_receipt_sha256
                    != witness.authority_receipt_sha256
                    or active.program_id != binding.program_id
                ):
                    raise RuntimeError(
                        "causal inquiry has another active opportunity"
                    )
                opportunity = active
                staged = self._state
            else:
                opportunity = self._seal_opportunity(
                    witness=witness,
                    binding=binding,
                )
                staged = _InquiryState(
                    witnesses=self._state.witnesses,
                    bindings=self._state.bindings,
                    active_need=self._state.active_need,
                    pending_needs=self._state.pending_needs,
                    active_opportunity=opportunity,
                    pending_attempt=None,
                )
            return self._prepare(
                operation="issue_opportunity",
                result=InquiryDecision(
                    state="ready",
                    reason="one_learned_tutor_action",
                    witness_receipt_sha256=(
                        witness.authority_receipt_sha256
                    ),
                    candidate_program_ids=program_ids,
                    opportunity=opportunity,
                ),
                staged=staged,
            )

    def _verify_tutor_authorization(
        self,
        value: CausalInquiryTutorAuthorizationReceipt,
    ) -> None:
        self._tutor_authorization_verifier.verify(value)

    def _seal_attempt(
        self,
        *,
        mode: str,
        witness: InquiryWitness,
        opportunity: InquiryOpportunity | None,
        tutor_authorization: (
            CausalInquiryTutorAuthorizationReceipt | None
        ),
        receipt: FreshArticulatorySelfAcousticCustodyReceipt,
    ) -> InquiryAttempt:
        provisional = InquiryAttempt(
            mode=mode,
            witness_receipt_sha256=(
                witness.authority_receipt_sha256
            ),
            opportunity_receipt_sha256=(
                opportunity.authority_receipt_sha256
                if opportunity is not None else None
            ),
            tutor_authorization=tutor_authorization,
            program_id=receipt.program_id,
            fresh_articulatory_receipt=receipt,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._attempt_key,
            _ATTEMPT_DOMAIN,
            provisional.payload(),
        )
        result = InquiryAttempt(
            mode=provisional.mode,
            witness_receipt_sha256=(
                provisional.witness_receipt_sha256
            ),
            opportunity_receipt_sha256=(
                provisional.opportunity_receipt_sha256
            ),
            tutor_authorization=provisional.tutor_authorization,
            program_id=provisional.program_id,
            fresh_articulatory_receipt=(
                provisional.fresh_articulatory_receipt
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_attempt(result)
        return result

    def _verify_attempt(self, value: InquiryAttempt) -> None:
        if not isinstance(value, InquiryAttempt):
            raise TypeError("causal inquiry attempt is not typed")
        if (
            value.mode not in _ATTEMPT_MODES
            or (
                value.mode == "learned"
            ) != (value.opportunity_receipt_sha256 is not None)
            or (
                value.mode == "exploratory"
            ) != (value.tutor_authorization is not None)
        ):
            raise ValueError("causal inquiry attempt mode changed")
        for digest, label in (
            (value.witness_receipt_sha256, "attempt witness"),
            (value.program_id, "attempt program"),
            (value.authority_hmac_sha256, "attempt HMAC"),
            (value.authority_receipt_sha256, "attempt authority"),
        ):
            _sha(digest, f"causal inquiry {label}")
        if value.opportunity_receipt_sha256 is not None:
            _sha(
                value.opportunity_receipt_sha256,
                "causal inquiry attempt opportunity",
            )
        if value.tutor_authorization is not None:
            self._verify_tutor_authorization(
                value.tutor_authorization
            )
        self._fresh.verify_receipt(
            value.fresh_articulatory_receipt
        )
        if (
            value.fresh_articulatory_receipt.program_id
            != value.program_id
        ):
            raise ValueError(
                "causal inquiry attempt changed articulatory program"
            )
        self._owned_program(value.program_id)
        signature = _sign(
            self._attempt_key,
            _ATTEMPT_DOMAIN,
            value.payload(),
        )
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
            raise ValueError(
                "causal inquiry attempt authority changed"
            )

    def prepare_attempt(
        self,
        *,
        need: InquiryNeed,
        fresh_articulatory_receipt: (
            FreshArticulatorySelfAcousticCustodyReceipt
        ),
        opportunity: InquiryOpportunity | None = None,
        tutor_authorization: (
            CausalInquiryTutorAuthorizationReceipt | None
        ) = None,
        exploration_selector: (
            ArticulatoryExplorationSelector | None
        ) = None,
        exploration_selection: (
            ArticulatoryExplorationSelection | None
        ) = None,
    ) -> PreparedCausalInquiryMutation:
        with self._lock:
            self._verify_need(need, require_active=True)
            witness = self._witness_by_receipt(
                need.witness_receipt_sha256
            )
            retained = self._witness_by_receipt(
                witness.authority_receipt_sha256
            )
            if retained != witness:
                raise ValueError(
                    "causal inquiry attempt lost its need witness"
                )
            if self._state.pending_attempt is not None:
                raise CausalInquiryCapacityError(
                    "causal inquiry pending-attempt capacity exhausted"
                )
            self._fresh.verify_receipt(
                fresh_articulatory_receipt
            )
            if (
                fresh_articulatory_receipt
                .world_before_receipt_sha256
                != witness.world_observation_receipt_sha256
            ):
                raise ValueError(
                    "causal inquiry articulation is not the next world edge"
                )
            if opportunity is not None:
                self._verify_opportunity(
                    opportunity,
                    require_active=True,
                )
                if (
                    opportunity.witness_receipt_sha256
                    != witness.authority_receipt_sha256
                    or opportunity.program_id
                    != fresh_articulatory_receipt.program_id
                    or exploration_selector is not None
                    or exploration_selection is not None
                    or tutor_authorization is not None
                ):
                    raise ValueError(
                        "causal inquiry learned attempt changed opportunity"
                    )
                mode = "learned"
            else:
                if self._state.bindings:
                    raise ValueError(
                        "tutor bootstrap is only available before learning"
                    )
                if tutor_authorization is None:
                    raise PermissionError(
                        "exploratory articulation requires explicit "
                        "tutor authorization"
                    )
                self._verify_tutor_authorization(
                    tutor_authorization
                )
                if (
                    not isinstance(
                        exploration_selector,
                        ArticulatoryExplorationSelector,
                    )
                    or not isinstance(
                        exploration_selection,
                        ArticulatoryExplorationSelection,
                    )
                ):
                    raise ValueError(
                        "causal inquiry exploratory attempt lacks exact "
                        "physical selection"
                    )
                if (
                    tutor_authorization.need_receipt_sha256
                    != need.authority_receipt_sha256
                    or tutor_authorization.program_id
                    != fresh_articulatory_receipt.program_id
                    or tutor_authorization
                    .world_observation_receipt_sha256
                    != witness.world_observation_receipt_sha256
                ):
                    raise ValueError(
                        "causal inquiry tutor authorization changed its "
                        "need or physical act"
                    )
                if (
                    exploration_selector._motor
                    is not self._articulatory
                ):
                    raise ValueError(
                        "causal inquiry exploration crossed motor ownership"
                    )
                exploration_selector.verify_selection(
                    exploration_selection
                )
                if (
                    exploration_selection.state
                    is not ArticulatoryExplorationState.SELECTED
                    or exploration_selection.program is None
                    or exploration_selection.program.program_id
                    != fresh_articulatory_receipt.program_id
                ):
                    raise ValueError(
                        "causal inquiry exploration did not select this act"
                    )
                mode = "exploratory"
            attempt = self._seal_attempt(
                mode=mode,
                witness=witness,
                opportunity=opportunity,
                tutor_authorization=tutor_authorization,
                receipt=fresh_articulatory_receipt,
            )
            staged = _InquiryState(
                witnesses=self._state.witnesses,
                bindings=self._state.bindings,
                active_need=self._state.active_need,
                pending_needs=self._state.pending_needs,
                active_opportunity=self._state.active_opportunity,
                pending_attempt=attempt,
            )
            return self._prepare(
                operation="arm_attempt",
                result=attempt,
                staged=staged,
            )

    @staticmethod
    def _route_reduced(
        prior: InquiryWitness,
        later: CausalThingRoute,
    ) -> bool:
        if prior.route_state == "unresolved":
            return (
                later.state == "unique"
                and len(later.thing_ids) == 1
            )
        return (
            later.state in {"ambiguous", "unique"}
            and bool(later.thing_ids)
            and set(later.thing_ids) < set(prior.thing_ids)
        )

    def _verify_tutor_response_link(
        self,
        *,
        fresh_receipt: FreshArticulatorySelfAcousticCustodyReceipt,
        tutor_response: ActionExecutionReceipt,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ),
    ) -> None:
        self._world.verify_execution_receipt(tutor_response)
        if (
            tutor_response.disposition != "applied"
            or tutor_response.port_id != SECOND_BODY_PORT_ID
            or tutor_response.before.authority_receipt_sha256
            != fresh_receipt.world_after_receipt_sha256
        ):
            raise ValueError(
                "causal inquiry tutor response is not the immediate "
                "causal consequence"
            )
        if companion_episode_intent is None:
            if (
                tutor_response.causal_intent_receipt_sha256
                != fresh_receipt.authority_receipt_sha256
            ):
                raise ValueError(
                    "causal inquiry direct tutor response changed intent"
                )
            return
        self._companion.verify_episode_intent(
            companion_episode_intent
        )
        if (
            companion_episode_intent.companion_port_id
            != SECOND_BODY_PORT_ID
            or companion_episode_intent.block_count != 1
            or companion_episode_intent
            .world_observation_receipt_sha256
            != tutor_response.before.authority_receipt_sha256
            or companion_episode_intent
            .causal_parent_receipt_sha256
            != fresh_receipt.authority_receipt_sha256
            or tutor_response.causal_intent_receipt_sha256
            != companion_episode_intent.authority_receipt_sha256
        ):
            raise ValueError(
                "causal inquiry companion intent lost its exact chain"
            )

    def _seal_binding(
        self,
        *,
        witness: InquiryWitness,
        attempt: InquiryAttempt,
        tutor_response: ActionExecutionReceipt,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ),
        later_view: SettledExperienceConsumerView,
        later_capability: SettledExperienceConsumerCapability,
        later_route: CausalThingRoute,
        later_boundaries: tuple[tuple[str, str], ...],
        later_roots: tuple[FullFieldSensoryRoot, ...],
    ) -> InquiryActionBinding:
        program = self._owned_program(attempt.program_id)
        identity_payload = {
            "attempt_receipt_sha256": (
                attempt.authority_receipt_sha256
            ),
            "later_settlement_receipt_sha256": (
                later_view.causal_settlement.authority_receipt_sha256
            ),
            "learning_witness_receipt_sha256": (
                witness.authority_receipt_sha256
            ),
            "program_id": program.program_id,
            "schema": (
                "guala.causal_inquiry.action_binding_identity.v1"
            ),
            "tutor_response_receipt_sha256": (
                tutor_response.authority_receipt_sha256
            ),
        }
        binding_id = _digest(identity_payload)
        provisional = InquiryActionBinding(
            binding_id=binding_id,
            program_id=program.program_id,
            program_authority_receipt_sha256=(
                program.authority_receipt_sha256
            ),
            learning_witness_receipt_sha256=(
                witness.authority_receipt_sha256
            ),
            attempt_receipt_sha256=(
                attempt.authority_receipt_sha256
            ),
            exploratory_tutor_authorization=(
                attempt.tutor_authorization
            ),
            fresh_articulatory_receipt=(
                attempt.fresh_articulatory_receipt
            ),
            companion_episode_intent=companion_episode_intent,
            tutor_response=tutor_response,
            later_source_occurrence_id=(
                later_view.source_occurrence_id
            ),
            later_custody_receipt_sha256=(
                later_view.parent_custody_receipt_sha256
            ),
            later_custody_capability_receipt_sha256=(
                later_capability.authority_receipt_sha256
            ),
            later_settlement_receipt_sha256=(
                later_view.causal_settlement.authority_receipt_sha256
            ),
            prior_route_state=witness.route_state,
            prior_thing_ids=witness.thing_ids,
            later_route_state=later_route.state,
            later_thing_ids=later_route.thing_ids,
            later_boundary_receipts=later_boundaries,
            later_full_field_roots=later_roots,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = _sign(
            self._binding_key,
            _BINDING_DOMAIN,
            provisional.payload(),
        )
        result = InquiryActionBinding(
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
        self._verify_binding(result)
        return result

    def _verify_binding(
        self,
        value: InquiryActionBinding,
    ) -> None:
        if not isinstance(value, InquiryActionBinding):
            raise TypeError("causal inquiry binding is not typed")
        for digest, label in (
            (value.binding_id, "binding identity"),
            (value.program_id, "binding program"),
            (
                value.program_authority_receipt_sha256,
                "binding program authority",
            ),
            (
                value.learning_witness_receipt_sha256,
                "binding witness",
            ),
            (value.attempt_receipt_sha256, "binding attempt"),
            (
                value.later_source_occurrence_id,
                "binding later occurrence",
            ),
            (
                value.later_custody_receipt_sha256,
                "binding later custody",
            ),
            (
                value.later_custody_capability_receipt_sha256,
                "binding later capability",
            ),
            (
                value.later_settlement_receipt_sha256,
                "binding later settlement",
            ),
            (value.authority_hmac_sha256, "binding HMAC"),
            (value.authority_receipt_sha256, "binding authority"),
        ):
            _sha(digest, f"causal inquiry {label}")
        program = self._owned_program(value.program_id)
        if (
            program.authority_receipt_sha256
            != value.program_authority_receipt_sha256
        ):
            raise ValueError(
                "causal inquiry binding changed its program authority"
            )
        self._fresh.verify_receipt(
            value.fresh_articulatory_receipt
        )
        if value.exploratory_tutor_authorization is not None:
            self._verify_tutor_authorization(
                value.exploratory_tutor_authorization
            )
            if (
                value.exploratory_tutor_authorization.program_id
                != value.program_id
                or value.exploratory_tutor_authorization
                .world_observation_receipt_sha256
                != value.fresh_articulatory_receipt
                .world_before_receipt_sha256
            ):
                raise ValueError(
                    "causal inquiry binding changed external "
                    "authorization"
                )
        self._verify_tutor_response_link(
            fresh_receipt=value.fresh_articulatory_receipt,
            tutor_response=value.tutor_response,
            companion_episode_intent=(
                value.companion_episode_intent
            ),
        )
        if (
            value.fresh_articulatory_receipt.program_id
            != value.program_id
        ):
            raise ValueError(
                "causal inquiry binding lost tutor response causality"
            )
        for sense, receipt in value.later_boundary_receipts:
            if sense not in _SENSE_INDEX:
                raise ValueError(
                    "causal inquiry binding later sense changed"
                )
            _sha(receipt, "causal inquiry binding later boundary")
        if len(value.later_boundary_receipts) < 2:
            raise ValueError(
                "causal inquiry binding lost multisensory resolution"
            )
        for root in value.later_full_field_roots:
            _verify_complete_root(root)
        prior = CausalThingRoute(
            state=value.prior_route_state,
            thing_ids=value.prior_thing_ids,
            matching_route_keys=(),
        )
        later = CausalThingRoute(
            state=value.later_route_state,
            thing_ids=value.later_thing_ids,
            matching_route_keys=(),
        )
        if prior.state == "unresolved":
            _route_shape(prior, allow_unique=False)
        elif (
            prior.state != "ambiguous"
            or len(prior.thing_ids) < 2
        ):
            raise ValueError(
                "causal inquiry binding prior route changed"
            )
        _route_shape(later, allow_unique=True)
        if not self._route_reduced(
            InquiryWitness(
                sequence=1,
                source_occurrence_id="0" * 64,
                parent_custody_receipt_sha256="0" * 64,
                custody_capability_receipt_sha256="0" * 64,
                settlement_receipt_sha256="0" * 64,
                settlement_structural_fingerprint="0" * 64,
                source_time_start=Fraction(0),
                source_time_end=Fraction(1),
                origin="active_execution",
                world_observation_receipt_sha256="0" * 64,
                world_observation_revision=1,
                world_execution_receipt_sha256="0" * 64,
                world_before_receipt_sha256="0" * 64,
                world_after_receipt_sha256="0" * 64,
                world_before_revision=0,
                world_after_revision=1,
                observed_senses=("sight", "touch"),
                boundary_receipts=(
                    ("sight", "0" * 64),
                    ("touch", "0" * 64),
                ),
                full_field_roots=value.later_full_field_roots,
                route_state=value.prior_route_state,
                thing_ids=value.prior_thing_ids,
                matching_route_keys=(),
                prior_witness_receipt_sha256=None,
                causal_continuation_relation="genesis",
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            ),
            later,
        ):
            raise ValueError(
                "causal inquiry binding did not reduce its route"
            )
        signature = _sign(
            self._binding_key,
            _BINDING_DOMAIN,
            value.payload(),
        )
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
            raise ValueError(
                "causal inquiry binding authority changed"
            )

    def prepare_closure(
        self,
        *,
        attempt: InquiryAttempt,
        tutor_response: ActionExecutionReceipt,
        later_custody_authority: SettledExperienceCustodyAuthority,
        later_custody_capability: (
            SettledExperienceConsumerCapability
        ),
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ) = None,
    ) -> PreparedCausalInquiryMutation:
        with self._lock:
            if self._state.pending_attempt != attempt:
                raise ValueError(
                    "causal inquiry attempt is not pending"
                )
            self._verify_attempt(attempt)
            witness = self._witness_by_receipt(
                attempt.witness_receipt_sha256
            )
            self._verify_tutor_response_link(
                fresh_receipt=attempt.fresh_articulatory_receipt,
                tutor_response=tutor_response,
                companion_episode_intent=companion_episode_intent,
            )
            later_view = self._open_lived_child(
                later_custody_authority,
                later_custody_capability,
            )
            if later_view.world_execution != tutor_response:
                raise ValueError(
                    "causal inquiry resolution is not the tutor response"
                )
            (
                _later_senses,
                later_boundaries,
                later_roots,
            ) = self._lived_evidence(later_view)
            later_route = self._things.route(
                later_view.causal_settlement
            )
            _route_shape(later_route, allow_unique=True)
            if not self._route_reduced(witness, later_route):
                raise ValueError(
                    "causal inquiry tutor response did not reduce routing "
                    "uncertainty"
                )
            binding = self._seal_binding(
                witness=witness,
                attempt=attempt,
                tutor_response=tutor_response,
                companion_episode_intent=companion_episode_intent,
                later_view=later_view,
                later_capability=later_custody_capability,
                later_route=later_route,
                later_boundaries=later_boundaries,
                later_roots=later_roots,
            )
            existing = next(
                (
                    value
                    for value in self._state.bindings
                    if value.binding_id == binding.binding_id
                ),
                None,
            )
            if existing is not None:
                if existing != binding:
                    raise ValueError(
                        "causal inquiry binding identity conflicted"
                    )
                binding = existing
                bindings = self._state.bindings
            else:
                if (
                    len(self._state.bindings)
                    >= self._profile.max_bindings
                ):
                    raise CausalInquiryCapacityError(
                        "causal inquiry binding capacity exhausted"
                    )
                bindings = tuple(sorted(
                    (*self._state.bindings, binding),
                    key=lambda value: value.binding_id,
                ))
            staged = self._state_after_active_need_closure(
                bindings=bindings,
            )
            return self._prepare(
                operation="close_attempt",
                result=binding,
                staged=staged,
            )

    def prepare_abandonment(
        self,
        *,
        attempt: InquiryAttempt,
        tutor_response: ActionExecutionReceipt | None = None,
        later_custody_authority: (
            SettledExperienceCustodyAuthority | None
        ) = None,
        later_custody_capability: (
            SettledExperienceConsumerCapability | None
        ) = None,
        companion_episode_intent: (
            CompanionVocalEpisodeIntentReceipt | None
        ) = None,
    ) -> PreparedCausalInquiryMutation:
        """Prepare exact release of one stale or non-resolving attempt."""

        with self._lock:
            if self._state.pending_attempt != attempt:
                raise ValueError(
                    "causal inquiry attempt is not pending"
                )
            self._verify_attempt(attempt)
            witness = self._witness_by_receipt(
                attempt.witness_receipt_sha256
            )
            response_arguments = (
                tutor_response,
                later_custody_authority,
                later_custody_capability,
            )
            if all(value is None for value in response_arguments):
                if companion_episode_intent is not None:
                    raise ValueError(
                        "stale abandonment cannot carry companion intent"
                    )
                current = self._world.observation_snapshot()
                if (
                    current.authority_receipt_sha256
                    == attempt.fresh_articulatory_receipt
                    .world_after_receipt_sha256
                ):
                    raise ValueError(
                        "causal inquiry attempt is not stale"
                    )
                result = InquiryAttemptAbandonment(
                    reason="stale_world",
                    attempt_receipt_sha256=(
                        attempt.authority_receipt_sha256
                    ),
                    tutor_response_receipt_sha256=None,
                    later_settlement_receipt_sha256=None,
                    later_route_state=None,
                )
            elif any(value is None for value in response_arguments):
                raise ValueError(
                    "non-resolving abandonment requires its complete "
                    "verified consequence"
                )
            else:
                self._verify_tutor_response_link(
                    fresh_receipt=(
                        attempt.fresh_articulatory_receipt
                    ),
                    tutor_response=tutor_response,
                    companion_episode_intent=(
                        companion_episode_intent
                    ),
                )
                later_view = self._open_lived_child(
                    later_custody_authority,
                    later_custody_capability,
                )
                if later_view.world_execution != tutor_response:
                    raise ValueError(
                        "causal inquiry abandonment is not the tutor "
                        "response"
                    )
                self._lived_evidence(later_view)
                later_route = self._things.route(
                    later_view.causal_settlement
                )
                _route_shape(later_route, allow_unique=True)
                if self._route_reduced(witness, later_route):
                    raise ValueError(
                        "resolving response requires causal closure"
                    )
                result = InquiryAttemptAbandonment(
                    reason="verified_nonresolving_response",
                    attempt_receipt_sha256=(
                        attempt.authority_receipt_sha256
                    ),
                    tutor_response_receipt_sha256=(
                        tutor_response.authority_receipt_sha256
                    ),
                    later_settlement_receipt_sha256=(
                        later_view.causal_settlement
                        .authority_receipt_sha256
                    ),
                    later_route_state=later_route.state,
                )
            staged = self._state_after_active_need_closure(
                bindings=self._state.bindings,
            )
            return self._prepare(
                operation="abandon_attempt",
                result=result,
                staged=staged,
            )

    def _verify_state(self, state: _InquiryState) -> None:
        if not isinstance(state, _InquiryState):
            raise TypeError("causal inquiry state is not typed")
        if (
            len(state.witnesses) > self._profile.max_witnesses
            or len(state.bindings) > self._profile.max_bindings
            or len(state.pending_needs)
            > max(0, self._profile.max_witnesses - 1)
            or (
                (1 if state.active_need is not None else 0)
                + len(state.pending_needs)
                > self._profile.max_witnesses
            )
            or tuple(
                value.sequence for value in state.witnesses
            ) != tuple(range(1, len(state.witnesses) + 1))
            or len({
                value.source_occurrence_id
                for value in state.witnesses
            }) != len(state.witnesses)
            or tuple(
                value.binding_id for value in state.bindings
            ) != tuple(sorted({
                value.binding_id for value in state.bindings
            }))
        ):
            raise ValueError("causal inquiry state structure changed")
        witness_receipts = {
            value.authority_receipt_sha256
            for value in state.witnesses
        }
        witness_sequence_by_receipt = {
            value.authority_receipt_sha256: value.sequence
            for value in state.witnesses
        }
        for witness in state.witnesses:
            self._verify_witness(witness)
            if (
                witness.prior_witness_receipt_sha256 is not None
                and witness.prior_witness_receipt_sha256
                not in witness_receipts
            ):
                raise ValueError(
                    "causal inquiry witness lost its prior"
                )
        ordered_needs = (
            (() if state.active_need is None else (state.active_need,))
            + state.pending_needs
        )
        if (
            state.active_need is None
            and (
                state.pending_needs
                or state.active_opportunity is not None
                or state.pending_attempt is not None
            )
        ):
            raise ValueError(
                "causal inquiry inactive state retained active work"
            )
        need_witness_receipts = tuple(
            value.witness_receipt_sha256 for value in ordered_needs
        )
        if (
            len(set(need_witness_receipts))
            != len(need_witness_receipts)
            or need_witness_receipts
            and tuple(
                witness_sequence_by_receipt.get(receipt, 0)
                for receipt in need_witness_receipts
            )
            != tuple(sorted(
                witness_sequence_by_receipt.get(receipt, 0)
                for receipt in need_witness_receipts
            ))
        ):
            raise ValueError(
                "causal inquiry needs changed witness order"
            )
        for need in ordered_needs:
            self._verify_need(
                need,
                require_active=False,
            )
            if (
                need.witness_receipt_sha256
                not in witness_receipts
            ):
                raise ValueError(
                    "causal inquiry need lost its witness"
                )
            witness = next(
                value
                for value in state.witnesses
                if value.authority_receipt_sha256
                == need.witness_receipt_sha256
            )
            if need != self._seal_need(witness):
                raise ValueError(
                    "causal inquiry need changed its witness"
                )
        for binding in state.bindings:
            self._verify_binding(binding)
            if (
                binding.learning_witness_receipt_sha256
                not in witness_receipts
            ):
                raise ValueError(
                    "causal inquiry binding lost its witness"
                )
            if binding.exploratory_tutor_authorization is not None:
                learning_witness = next(
                    witness
                    for witness in state.witnesses
                    if witness.authority_receipt_sha256
                    == binding.learning_witness_receipt_sha256
                )
                if (
                    binding.exploratory_tutor_authorization
                    .need_receipt_sha256
                    != self._seal_need(learning_witness)
                    .authority_receipt_sha256
                ):
                    raise ValueError(
                        "causal inquiry binding lost external "
                        "authorization need"
                    )
        if state.active_opportunity is not None:
            self._verify_opportunity(
                state.active_opportunity,
                require_active=False,
            )
            if (
                state.active_opportunity.witness_receipt_sha256
                not in witness_receipts
                or state.active_need is None
                or state.active_opportunity.witness_receipt_sha256
                != state.active_need.witness_receipt_sha256
                or state.active_opportunity.binding_receipt_sha256
                not in {
                    value.authority_receipt_sha256
                    for value in state.bindings
                }
            ):
                raise ValueError(
                    "causal inquiry opportunity lost its authority"
                )
        if state.pending_attempt is not None:
            self._verify_attempt(state.pending_attempt)
            if (
                state.pending_attempt.witness_receipt_sha256
                not in witness_receipts
                or state.active_need is None
                or state.pending_attempt.witness_receipt_sha256
                != state.active_need.witness_receipt_sha256
                or (
                    state.pending_attempt.mode == "learned"
                    and (
                        state.active_opportunity is None
                        or state.pending_attempt
                        .opportunity_receipt_sha256
                        != state.active_opportunity
                        .authority_receipt_sha256
                    )
                )
            ):
                raise ValueError(
                    "causal inquiry pending attempt lost its authority"
                )

    @staticmethod
    def _witness_from_record(value: object) -> InquiryWitness:
        if not isinstance(value, Mapping):
            raise ValueError("causal inquiry witness record changed")
        fields = set(InquiryWitness.__dataclass_fields__)
        payload_fields = fields - {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
        }
        if set(value) != payload_fields | {
            "schema",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
        }:
            raise ValueError("causal inquiry witness record changed")
        return InquiryWitness(
            sequence=value["sequence"],
            source_occurrence_id=value["source_occurrence_id"],
            parent_custody_receipt_sha256=(
                value["parent_custody_receipt_sha256"]
            ),
            custody_capability_receipt_sha256=(
                value["custody_capability_receipt_sha256"]
            ),
            settlement_receipt_sha256=(
                value["settlement_receipt_sha256"]
            ),
            settlement_structural_fingerprint=(
                value["settlement_structural_fingerprint"]
            ),
            source_time_start=_fraction_from_text(
                value["source_time_start"],
                "causal inquiry witness source start",
            ),
            source_time_end=_fraction_from_text(
                value["source_time_end"],
                "causal inquiry witness source end",
            ),
            origin=value["origin"],
            world_observation_receipt_sha256=(
                value["world_observation_receipt_sha256"]
            ),
            world_observation_revision=(
                value["world_observation_revision"]
            ),
            world_execution_receipt_sha256=(
                value["world_execution_receipt_sha256"]
            ),
            world_before_receipt_sha256=(
                value["world_before_receipt_sha256"]
            ),
            world_after_receipt_sha256=(
                value["world_after_receipt_sha256"]
            ),
            world_before_revision=value["world_before_revision"],
            world_after_revision=value["world_after_revision"],
            observed_senses=tuple(value["observed_senses"]),
            boundary_receipts=tuple(
                tuple(item) for item in value["boundary_receipts"]
            ),
            full_field_roots=tuple(
                _root_from_record(item)
                for item in value["full_field_roots"]
            ),
            route_state=value["route_state"],
            thing_ids=tuple(value["thing_ids"]),
            matching_route_keys=tuple(
                tuple(item)
                for item in value["matching_route_keys"]
            ),
            prior_witness_receipt_sha256=(
                value["prior_witness_receipt_sha256"]
            ),
            causal_continuation_relation=(
                value["causal_continuation_relation"]
            ),
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=(
                value["authority_receipt_sha256"]
            ),
        )

    @staticmethod
    def _need_from_record(value: object) -> InquiryNeed:
        if not isinstance(value, Mapping):
            raise ValueError("causal inquiry need record changed")
        expected = set(InquiryNeed.__dataclass_fields__) | {"schema"}
        if set(value) != expected:
            raise ValueError("causal inquiry need record changed")
        return InquiryNeed(
            need_id=value["need_id"],
            witness_receipt_sha256=value["witness_receipt_sha256"],
            origin=value["origin"],
            route_state=value["route_state"],
            action_role=value["action_role"],
            meaning_authority=value["meaning_authority"],
            word_authority=value["word_authority"],
            label_authority=value["label_authority"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )

    @staticmethod
    def _tutor_authorization_from_record(
        value: object,
    ) -> CausalInquiryTutorAuthorizationReceipt:
        return CausalInquiryTutorAuthorizationReceipt.from_record(
            value
        )

    def _binding_from_record(
        self,
        value: object,
    ) -> InquiryActionBinding:
        if not isinstance(value, Mapping):
            raise ValueError("causal inquiry binding record changed")
        expected = {
            "attempt_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "binding_id",
            "companion_episode_intent",
            "exploratory_tutor_authorization",
            "fresh_articulatory_receipt",
            "later_boundary_receipts",
            "later_custody_capability_receipt_sha256",
            "later_custody_receipt_sha256",
            "later_full_field_roots",
            "later_route_state",
            "later_settlement_receipt_sha256",
            "later_source_occurrence_id",
            "later_thing_ids",
            "learning_witness_receipt_sha256",
            "prior_route_state",
            "prior_thing_ids",
            "program_authority_receipt_sha256",
            "program_id",
            "schema",
            "tutor_response",
        }
        if set(value) != expected:
            raise ValueError("causal inquiry binding record changed")
        return InquiryActionBinding(
            binding_id=value["binding_id"],
            program_id=value["program_id"],
            program_authority_receipt_sha256=(
                value["program_authority_receipt_sha256"]
            ),
            learning_witness_receipt_sha256=(
                value["learning_witness_receipt_sha256"]
            ),
            attempt_receipt_sha256=(
                value["attempt_receipt_sha256"]
            ),
            exploratory_tutor_authorization=(
                None
                if value["exploratory_tutor_authorization"] is None
                else self._tutor_authorization_from_record(
                    value["exploratory_tutor_authorization"]
                )
            ),
            fresh_articulatory_receipt=(
                fresh_articulatory_receipt_from_record(
                    value["fresh_articulatory_receipt"]
                )
            ),
            companion_episode_intent=(
                None
                if value["companion_episode_intent"] is None
                else self._companion.episode_intent_from_record(
                    value["companion_episode_intent"]
                )
            ),
            tutor_response=(
                self._world.execution_receipt_from_record(
                    value["tutor_response"]
                )
            ),
            later_source_occurrence_id=(
                value["later_source_occurrence_id"]
            ),
            later_custody_receipt_sha256=(
                value["later_custody_receipt_sha256"]
            ),
            later_custody_capability_receipt_sha256=(
                value["later_custody_capability_receipt_sha256"]
            ),
            later_settlement_receipt_sha256=(
                value["later_settlement_receipt_sha256"]
            ),
            prior_route_state=value["prior_route_state"],
            prior_thing_ids=tuple(value["prior_thing_ids"]),
            later_route_state=value["later_route_state"],
            later_thing_ids=tuple(value["later_thing_ids"]),
            later_boundary_receipts=tuple(
                tuple(item)
                for item in value["later_boundary_receipts"]
            ),
            later_full_field_roots=tuple(
                _root_from_record(item)
                for item in value["later_full_field_roots"]
            ),
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=(
                value["authority_receipt_sha256"]
            ),
        )

    @staticmethod
    def _opportunity_from_record(
        value: object,
    ) -> InquiryOpportunity:
        if not isinstance(value, Mapping):
            raise ValueError(
                "causal inquiry opportunity record changed"
            )
        expected = set(InquiryOpportunity.__dataclass_fields__) | {
            "schema"
        }
        if set(value) != expected:
            raise ValueError(
                "causal inquiry opportunity record changed"
            )
        return InquiryOpportunity(
            opportunity_id=value["opportunity_id"],
            witness_receipt_sha256=(
                value["witness_receipt_sha256"]
            ),
            binding_receipt_sha256=(
                value["binding_receipt_sha256"]
            ),
            program_id=value["program_id"],
            owner_state_sha256=value["owner_state_sha256"],
            action_role=value["action_role"],
            meaning_authority=value["meaning_authority"],
            word_authority=value["word_authority"],
            label_authority=value["label_authority"],
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=(
                value["authority_receipt_sha256"]
            ),
        )

    @staticmethod
    def _attempt_from_record(value: object) -> InquiryAttempt:
        if not isinstance(value, Mapping):
            raise ValueError("causal inquiry attempt record changed")
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "fresh_articulatory_receipt",
            "mode",
            "opportunity_receipt_sha256",
            "program_id",
            "schema",
            "tutor_authorization",
            "witness_receipt_sha256",
        }
        if set(value) != expected:
            raise ValueError("causal inquiry attempt record changed")
        return InquiryAttempt(
            mode=value["mode"],
            witness_receipt_sha256=(
                value["witness_receipt_sha256"]
            ),
            opportunity_receipt_sha256=(
                value["opportunity_receipt_sha256"]
            ),
            tutor_authorization=(
                None
                if value["tutor_authorization"] is None
                else CausalInquiryOwner
                ._tutor_authorization_from_record(
                    value["tutor_authorization"]
                )
            ),
            program_id=value["program_id"],
            fresh_articulatory_receipt=(
                fresh_articulatory_receipt_from_record(
                    value["fresh_articulatory_receipt"]
                )
            ),
            authority_hmac_sha256=value["authority_hmac_sha256"],
            authority_receipt_sha256=(
                value["authority_receipt_sha256"]
            ),
        )

    def _state_from_encoded(
        self,
        encoded: bytes,
    ) -> tuple[_InquiryState, bool]:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._profile.max_state_bytes
        ):
            raise ValueError("causal inquiry restore extent changed")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "causal inquiry state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope) != {
                "body",
                "schema",
                "state_hmac_sha256",
            }
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError("causal inquiry state envelope changed")
        body = envelope["body"]
        schema = body.get("schema") if isinstance(body, Mapping) else None
        migrated = schema == LEGACY_STATE_SCHEMA
        expected_body_keys = {
            "active_need",
            "active_opportunity",
            "bindings",
            "pending_attempt",
            "profile",
            "schema",
            "witnesses",
        }
        if not migrated:
            expected_body_keys.add("pending_needs")
        if (
            not isinstance(body, Mapping)
            or set(body) != expected_body_keys
            or schema not in {STATE_SCHEMA, LEGACY_STATE_SCHEMA}
            or body.get("profile") != self._profile.record()
            or not isinstance(body.get("witnesses"), list)
            or not isinstance(body.get("bindings"), list)
            or (
                not migrated
                and not isinstance(body.get("pending_needs"), list)
            )
            or len(body["witnesses"]) > self._profile.max_witnesses
            or len(body["bindings"]) > self._profile.max_bindings
            or (
                not migrated
                and len(body["pending_needs"])
                > max(0, self._profile.max_witnesses - 1)
            )
        ):
            raise ValueError("causal inquiry state body changed")
        expected_hmac = _sign(
            self._state_key,
            _STATE_DOMAIN,
            body,
        )
        if not hmac.compare_digest(
            expected_hmac,
            envelope["state_hmac_sha256"],
        ):
            raise ValueError("causal inquiry state authority changed")
        state = _InquiryState(
            witnesses=tuple(
                self._witness_from_record(value)
                for value in body["witnesses"]
            ),
            bindings=tuple(
                self._binding_from_record(value)
                for value in body["bindings"]
            ),
            active_need=(
                None
                if body["active_need"] is None
                else self._need_from_record(body["active_need"])
            ),
            pending_needs=(
                ()
                if migrated
                else tuple(
                    self._need_from_record(value)
                    for value in body["pending_needs"]
                )
            ),
            active_opportunity=(
                None
                if body["active_opportunity"] is None
                else self._opportunity_from_record(
                    body["active_opportunity"]
                )
            ),
            pending_attempt=(
                None
                if body["pending_attempt"] is None
                else self._attempt_from_record(
                    body["pending_attempt"]
                )
            ),
        )
        self._verify_state(state)
        canonical = self._encoded(state)
        if not migrated and canonical != encoded:
            raise ValueError(
                "causal inquiry restore changed canonical state"
            )
        if migrated and canonical == encoded:
            raise ValueError(
                "causal inquiry legacy state did not migrate forward"
            )
        return state, migrated

    def restore_current_encoded(self, encoded: bytes) -> None:
        """Restore exact prior state without changing this owner's identity."""

        with self._lock:
            if (
                self._prepared is not None
                or self._latest_undo_prepared is not None
            ):
                raise RuntimeError(
                    "causal inquiry cannot restore an active transaction"
                )
            state, migrated = self._state_from_encoded(encoded)
            prior = self._state
            self._state = state
            try:
                restored = self.snapshot_encoded()
                if (
                    (not migrated and restored != encoded)
                    or (migrated and restored == encoded)
                ):
                    raise ValueError(
                        "causal inquiry in-place restore changed state"
                    )
            except BaseException:
                self._state = prior
                raise

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        profile: CausalInquiryProfile,
        encoded: bytes,
        thing_owner: CausalThingMosaicOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        fresh_articulatory_authority: (
            FreshArticulatorySelfAcousticCustodyAuthority
        ),
        companion_vocal_authority: (
            W1CompanionVocalExperienceAuthority
        ),
        world_authority: EmbodimentWorldAuthority,
        tutor_authorization_verifier: (
            CausalInquiryTutorAuthorizationVerifier
        ),
    ) -> "CausalInquiryOwner":
        owner = cls(
            authority_key=authority_key,
            profile=profile,
            thing_owner=thing_owner,
            articulatory_owner=articulatory_owner,
            fresh_articulatory_authority=(
                fresh_articulatory_authority
            ),
            companion_vocal_authority=companion_vocal_authority,
            world_authority=world_authority,
            tutor_authorization_verifier=(
                tutor_authorization_verifier
            ),
        )
        owner.restore_current_encoded(encoded)
        return owner

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = (
                self._encoded(self._state)
                if self._prepared is None
                else self._encoded(
                    self._prepared._prior_state
                )
            )
            return {
                "active_need": self._state.active_need is not None,
                "active_opportunity": (
                    self._state.active_opportunity is not None
                ),
                "binding_capacity": self._profile.max_bindings,
                "binding_count": len(self._state.bindings),
                "full_dsf_field_preserved": True,
                "label_authority": False,
                "meaning_authority": False,
                "need_capacity": self._profile.max_witnesses,
                "active_need_capacity": 1,
                "pending_need_capacity": max(
                    0,
                    self._profile.max_witnesses - 1,
                ),
                "pending_need_count": len(
                    self._state.pending_needs
                ),
                "pending_attempt": (
                    self._state.pending_attempt is not None
                ),
                "reduced_approximation": False,
                "retained_media_bytes": 0,
                "schema": STATUS_SCHEMA,
                "state_bytes": len(encoded),
                "state_capacity_bytes": (
                    self._profile.max_state_bytes
                ),
                "witness_capacity": (
                    self._profile.max_witnesses
                ),
                "witness_count": len(self._state.witnesses),
                "word_authority": False,
            }


__all__ = (
    "ATTEMPT_SCHEMA",
    "BINDING_SCHEMA",
    "BODY_OWNED_FRAGMENT_CLOSURE_SCHEMA",
    "BodyOwnedFragmentInquiryClosure",
    "CAUSAL_INQUIRY_CONSUMER_ID",
    "CausalInquiryCapacityError",
    "CausalInquiryOwner",
    "CausalInquiryProfile",
    "CausalInquiryUndo",
    "InquiryActionBinding",
    "InquiryAttempt",
    "InquiryAttemptAbandonment",
    "InquiryDecision",
    "InquiryNeed",
    "InquiryOpportunity",
    "LEGACY_STATE_SCHEMA",
    "InquiryWitness",
    "PreparedCausalInquiryMutation",
    "PROFILE_SCHEMA",
    "NEED_SCHEMA",
    "STATE_SCHEMA",
    "STATUS_SCHEMA",
    "TUTOR_AUTHORIZATION_SCHEMA",
    "WITNESS_SCHEMA",
)
