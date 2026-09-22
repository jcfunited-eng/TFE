"""Bounded causal episodes over already-durable full-field THING records.

This owner is an ordering and reference authority.  It is not a second sensory
archive.  A lived event can exist only when its occurrence is already retained
as either an authenticated ``ThingEncounterPartition`` or an authenticated
``CausalThingSensoryExpansion``.  Complete D/M/R/U/C/P/B evidence remains in
that durable record.  Context stores exact commitments and receipts, never a
settlement, field tuple, PCM block, video frame, label, or meaning.

Live partition admission still uses settled custody to authenticate source and
world provenance.  Cold restore never needs that transient custody.  It
resolves each event receipt against the restored THING/expansion graph,
recomputes both full-field and route-key commitments from the durable roots,
and verifies a bounded journal of compact action-execution records.

Within one episode, order has only two physical authorities:

* exact source continuation: adjacent source receipt, sequence, rational
  interval, and world boundary; or
* exact world transition: the next durable partition starts from the prior
  observation and advances one world revision.

An unlinked later world revision starts a new episode.  A sensory expansion
with no W1 world boundary starts a reference-only episode and claims no order
against other episodes.  Same/earlier unlinked W1 occurrences are refused.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.causal_thing_action_execution import (
    EXECUTION_SCHEMA,
    CausalThingActionExecution,
    CausalThingActionExecutionAuthority,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingRoute,
    FullFieldSensoryRoot,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    THING_SENSORY_EXPANSION_CONSUMER_ID,
    CausalThingSensoryExpansion,
    CausalThingSensoryExpansionOwner,
    RetainedAudiovisualCustodyAuthority,
    RetainedAudiovisualCustodyCapability,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceCustody,
    SettledExperienceCustodyAuthority,
    SettledExperienceSourceKind,
)


PROFILE_SCHEMA = "guala.causal_thing_lived_context.profile.v2"
FULL_FIELD_REFERENCE_SCHEMA = (
    "guala.causal_thing_lived_context.full_field_reference.v2"
)
ROUTE_REFERENCE_SCHEMA = (
    "guala.causal_thing_lived_context.route_reference.v2"
)
BODY_PROVENANCE_SCHEMA = (
    "guala.causal_thing_lived_context.body_provenance.v2"
)
EVENT_SCHEMA = "guala.causal_thing_lived_context.event.v2"
EPISODE_SCHEMA = "guala.causal_thing_lived_context.episode.v2"
STATE_SCHEMA = "guala.causal_thing_lived_context.state.v2"
ENVELOPE_SCHEMA = "guala.causal_thing_lived_context.state_hmac.v2"
STATUS_SCHEMA = "guala.causal_thing_lived_context.status.v2"

_EVENT_DOMAIN = b"guala-causal-thing-lived-context-event-v2\0"
_EPISODE_DOMAIN = b"guala-causal-thing-lived-context-episode-v2\0"
_STATE_DOMAIN = b"guala-causal-thing-lived-context-state-v2\0"
_BODY_DOMAIN = b"guala-causal-thing-lived-context-body-v2\0"
_HEX = frozenset("0123456789abcdef")
_REFERENCE_KINDS = frozenset(("thing_partition", "sensory_expansion"))
_CONTINUITIES = frozenset((
    "episode_genesis",
    "discontinuous_world_gap_genesis",
    "reference_only_genesis",
    "exact_source_continuation",
    "exact_world_transition",
))

MAX_CONFIGURED_EPISODES = 65_536
MAX_CONFIGURED_EVENTS_PER_EPISODE = 65_536
MAX_CONFIGURED_TOTAL_EVENTS = 1_048_576
MAX_CONFIGURED_ROOTS_PER_EVENT = 65_536
MAX_CONFIGURED_STATE_BYTES = 512 * 1024 * 1024


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


def _key(value: bytes | str, label: str, *, minimum: int = 32) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not minimum <= len(raw) <= 4_096:
        raise ValueError(f"{label} key boundary changed")
    return hashlib.sha256(label.encode("utf-8") + b"\0" + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _optional_sha(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _sha(value, label)


def _positive(value: object, label: str, *, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 < value <= maximum
    ):
        raise ValueError(f"{label} is outside its exact capacity")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("lived-context interval is not exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not an exact fraction")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{label} is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class CausalThingLivedContextResourceProfile:
    profile_id: str
    max_episodes: int
    max_events_per_episode: int
    max_total_events: int
    max_full_field_roots_per_event: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_episodes: int,
        max_events_per_episode: int,
        max_total_events: int,
        max_full_field_roots_per_event: int,
        max_state_bytes: int,
    ) -> "CausalThingLivedContextResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError("lived-context profile id changed")
        provisional = cls(
            profile_id=profile_id,
            max_episodes=_positive(
                max_episodes,
                "lived-context episode capacity",
                maximum=MAX_CONFIGURED_EPISODES,
            ),
            max_events_per_episode=_positive(
                max_events_per_episode,
                "lived-context per-episode capacity",
                maximum=MAX_CONFIGURED_EVENTS_PER_EPISODE,
            ),
            max_total_events=_positive(
                max_total_events,
                "lived-context total event capacity",
                maximum=MAX_CONFIGURED_TOTAL_EVENTS,
            ),
            max_full_field_roots_per_event=_positive(
                max_full_field_roots_per_event,
                "lived-context root capacity",
                maximum=MAX_CONFIGURED_ROOTS_PER_EVENT,
            ),
            max_state_bytes=_positive(
                max_state_bytes,
                "lived-context state byte capacity",
                maximum=MAX_CONFIGURED_STATE_BYTES,
            ),
            authority_receipt_sha256="0" * 64,
        )
        if (
            provisional.max_total_events
            > provisional.max_episodes
            * provisional.max_events_per_episode
        ):
            raise ValueError(
                "lived-context total capacity exceeds episode topology"
            )
        return cls(
            profile_id=provisional.profile_id,
            max_episodes=provisional.max_episodes,
            max_events_per_episode=provisional.max_events_per_episode,
            max_total_events=provisional.max_total_events,
            max_full_field_roots_per_event=(
                provisional.max_full_field_roots_per_event
            ),
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_episodes": self.max_episodes,
            "max_events_per_episode": self.max_events_per_episode,
            "max_full_field_roots_per_event": (
                self.max_full_field_roots_per_event
            ),
            "max_state_bytes": self.max_state_bytes,
            "max_total_events": self.max_total_events,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        if type(self).create(
            profile_id=self.profile_id,
            max_episodes=self.max_episodes,
            max_events_per_episode=self.max_events_per_episode,
            max_total_events=self.max_total_events,
            max_full_field_roots_per_event=(
                self.max_full_field_roots_per_event
            ),
            max_state_bytes=self.max_state_bytes,
        ) != self:
            raise ValueError("lived-context resource profile changed")

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "CausalThingLivedContextResourceProfile":
        expected = {
            "authority_receipt_sha256",
            "max_episodes",
            "max_events_per_episode",
            "max_full_field_roots_per_event",
            "max_state_bytes",
            "max_total_events",
            "profile_id",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != PROFILE_SCHEMA
        ):
            raise ValueError("lived-context profile record changed")
        result = cls(
            profile_id=value.get("profile_id"),
            max_episodes=value.get("max_episodes"),
            max_events_per_episode=value.get(
                "max_events_per_episode"
            ),
            max_total_events=value.get("max_total_events"),
            max_full_field_roots_per_event=value.get(
                "max_full_field_roots_per_event"
            ),
            max_state_bytes=value.get("max_state_bytes"),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        result.verify()
        if result.record() != dict(value):
            raise ValueError("lived-context profile is not canonical")
        return result


def _verified_root_record(
    root: FullFieldSensoryRoot,
) -> dict[str, object]:
    if not isinstance(root, FullFieldSensoryRoot):
        raise TypeError("lived-context durable root is not typed")
    root.verify()
    try:
        evidence = json.loads(root.full_evidence_json)
    except json.JSONDecodeError as error:
        raise ValueError("lived-context durable root is unreadable") from error
    if not isinstance(evidence, Mapping):
        raise ValueError("lived-context durable root evidence changed")
    field_tuples = evidence.get("field_tuples")
    if not isinstance(field_tuples, list) or not field_tuples:
        raise ValueError("lived-context durable root lost its DSF tuples")
    for item in field_tuples:
        fields = item.get("fields") if isinstance(item, Mapping) else None
        if (
            not isinstance(fields, list)
            or tuple(
                pair[0]
                for pair in fields
                if isinstance(pair, list) and len(pair) == 2
            )
            != DSF_FIELD_ORDER
        ):
            raise ValueError("lived-context durable root flattened DSF")
        for _name, value in fields:
            _fraction(value, "lived-context durable field")
    return root.record()


def _root_commitments(
    roots: tuple[FullFieldSensoryRoot, ...],
) -> tuple[str, int, str, int]:
    if not isinstance(roots, tuple) or not roots:
        raise ValueError("lived-context durable reference has no roots")
    records = tuple(
        sorted(
            (_verified_root_record(root) for root in roots),
            key=lambda value: (
                value["sense"],
                value["topology_index"],
                value["physical_value_sha256"],
                value["full_evidence_json"],
            ),
        )
    )
    route_keys = tuple(sorted(root.route_key for root in roots))
    if len(set(route_keys)) != len(route_keys):
        raise ValueError("lived-context durable roots repeat route authority")
    full_commitment = _digest({
        "roots": list(records),
        "schema": FULL_FIELD_REFERENCE_SCHEMA,
    })
    route_commitment = _digest({
        "matching_route_keys": [list(value) for value in route_keys],
        "schema": ROUTE_REFERENCE_SCHEMA,
    })
    return (
        full_commitment,
        len(records),
        route_commitment,
        len(route_keys),
    )


@dataclass(frozen=True, slots=True)
class LivedBodyProvenance:
    role: str
    body_continuity_hmac_sha256: str
    physical_state_sha256: str

    def record(self) -> dict[str, object]:
        return {
            "body_continuity_hmac_sha256": (
                self.body_continuity_hmac_sha256
            ),
            "physical_state_sha256": self.physical_state_sha256,
            "role": self.role,
            "schema": BODY_PROVENANCE_SCHEMA,
        }

    def verify(self) -> None:
        if self.role not in {"self", "other"}:
            raise ValueError("lived-context body provenance role changed")
        _sha(
            self.body_continuity_hmac_sha256,
            "lived-context body continuity",
        )
        _sha(
            self.physical_state_sha256,
            "lived-context body physical state",
        )

    @classmethod
    def from_record(cls, value: object) -> "LivedBodyProvenance":
        expected = {
            "body_continuity_hmac_sha256",
            "physical_state_sha256",
            "role",
            "schema",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != BODY_PROVENANCE_SCHEMA
        ):
            raise ValueError("lived-context body provenance record changed")
        result = cls(
            role=value.get("role"),
            body_continuity_hmac_sha256=value.get(
                "body_continuity_hmac_sha256"
            ),
            physical_state_sha256=value.get("physical_state_sha256"),
        )
        result.verify()
        if result.record() != dict(value):
            raise ValueError("lived-context body provenance is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CausalThingLivedContextEvent:
    ordinal: int
    episode_ordinal: int
    continuity: str
    prior_event_receipt_sha256: str | None
    durable_reference_kind: str
    durable_reference_receipt_sha256: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    source_kind: str
    source_receipt_sha256: str
    prior_source_receipt_sha256: str | None
    source_sequence: int | None
    source_time_start: Fraction
    source_time_end: Fraction
    world_revision: int | None
    world_observation_receipt_sha256: str | None
    world_before_receipt_sha256: str | None
    world_execution_receipt_sha256: str | None
    actor_body_provenance: LivedBodyProvenance | None
    thing_route_state: str
    thing_ids: tuple[str, ...]
    matching_route_commitment_sha256: str
    matching_route_key_count: int
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    full_field_commitment_sha256: str
    full_field_root_count: int
    action_consequence_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_consequence_receipt_sha256": (
                self.action_consequence_receipt_sha256
            ),
            "actor_body_provenance": (
                self.actor_body_provenance.record()
                if self.actor_body_provenance is not None else None
            ),
            "continuity": self.continuity,
            "durable_reference_kind": self.durable_reference_kind,
            "durable_reference_receipt_sha256": (
                self.durable_reference_receipt_sha256
            ),
            "episode_ordinal": self.episode_ordinal,
            "full_field_commitment_sha256": (
                self.full_field_commitment_sha256
            ),
            "full_field_root_count": self.full_field_root_count,
            "matching_route_commitment_sha256": (
                self.matching_route_commitment_sha256
            ),
            "matching_route_key_count": self.matching_route_key_count,
            "ordinal": self.ordinal,
            "parent_custody_receipt_sha256": (
                self.parent_custody_receipt_sha256
            ),
            "prior_event_receipt_sha256": (
                self.prior_event_receipt_sha256
            ),
            "prior_source_receipt_sha256": (
                self.prior_source_receipt_sha256
            ),
            "schema": EVENT_SCHEMA,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "settlement_structural_fingerprint": (
                self.settlement_structural_fingerprint
            ),
            "source_kind": self.source_kind,
            "source_occurrence_id": self.source_occurrence_id,
            "source_receipt_sha256": self.source_receipt_sha256,
            "source_sequence": self.source_sequence,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
            "thing_ids": list(self.thing_ids),
            "thing_route_state": self.thing_route_state,
            "world_before_receipt_sha256": (
                self.world_before_receipt_sha256
            ),
            "world_execution_receipt_sha256": (
                self.world_execution_receipt_sha256
            ),
            "world_observation_receipt_sha256": (
                self.world_observation_receipt_sha256
            ),
            "world_revision": self.world_revision,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CausalThingLivedContextEpisode:
    episode_id: str
    ordinal: int
    cross_episode_order_authority: str
    events: tuple[CausalThingLivedContextEvent, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "cross_episode_order_authority": (
                self.cross_episode_order_authority
            ),
            "episode_id": self.episode_id,
            "events": [value.record() for value in self.events],
            "ordinal": self.ordinal,
            "schema": EPISODE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class CausalThingLivedContextAdmission:
    state: str
    episode: CausalThingLivedContextEpisode
    event: CausalThingLivedContextEvent


@dataclass(slots=True)
class _AdmissionTransactionState:
    phase: str


@dataclass(frozen=True, slots=True)
class PreparedCausalThingLivedContextAdmission:
    admission: CausalThingLivedContextAdmission
    _prior_episodes: tuple[CausalThingLivedContextEpisode, ...] = field(
        repr=False,
    )
    _staged_episodes: tuple[CausalThingLivedContextEpisode, ...] = field(
        repr=False,
    )
    _prior_actions: tuple[CausalThingActionExecution, ...] = field(
        repr=False,
    )
    _staged_actions: tuple[CausalThingActionExecution, ...] = field(
        repr=False,
    )
    _transaction_state: _AdmissionTransactionState = field(
        repr=False,
        compare=False,
    )
    _authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CommittedCausalThingLivedContextAdmissionUndo:
    prepared: PreparedCausalThingLivedContextAdmission
    _authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class _DurableReference:
    kind: str
    receipt: str
    source_occurrence_id: str
    parent_custody_receipt_sha256: str
    settlement_receipt_sha256: str
    settlement_structural_fingerprint: str
    roots: tuple[FullFieldSensoryRoot, ...]
    owning_thing_id: str
    world_revision: int | None
    world_observation_receipt_sha256: str | None
    world_execution_receipt_sha256: str | None


@dataclass(frozen=True, slots=True)
class _LiveBoundary:
    reference: _DurableReference
    source_kind: str
    source_receipt_sha256: str
    prior_source_receipt_sha256: str | None
    source_sequence: int | None
    source_time_start: Fraction
    source_time_end: Fraction
    world_before_receipt_sha256: str | None
    actor_body_provenance: LivedBodyProvenance | None
    route: CausalThingRoute


class CausalThingLivedContextOwner:
    """Own bounded causal ordering over durable full-field THING records."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        custody_authority_key: bytes | str,
        w1_physical_authority_key: bytes | str,
        world_authority_key: bytes | str,
        thing_owner: CausalThingMosaicOwner,
        resource_profile: CausalThingLivedContextResourceProfile,
        sensory_expansion_owner: (
            CausalThingSensoryExpansionOwner | None
        ) = None,
        w1_self_acoustic_authority_key: bytes | str | None = None,
        action_execution_authority: (
            CausalThingActionExecutionAuthority | None
        ) = None,
    ) -> None:
        if not isinstance(thing_owner, CausalThingMosaicOwner):
            raise TypeError("lived context requires the causal THING owner")
        if not isinstance(
            resource_profile,
            CausalThingLivedContextResourceProfile,
        ):
            raise TypeError("lived context requires its resource profile")
        resource_profile.verify()
        if (
            sensory_expansion_owner is not None
            and not isinstance(
                sensory_expansion_owner,
                CausalThingSensoryExpansionOwner,
            )
        ):
            raise TypeError("lived context sensory expansion is not typed")
        if (
            action_execution_authority is not None
            and not isinstance(
                action_execution_authority,
                CausalThingActionExecutionAuthority,
            )
        ):
            raise TypeError(
                "lived context action consequence authority is not typed"
            )
        root = _key(authority_key, "causal THING lived context")
        self._event_key = hashlib.sha256(_EVENT_DOMAIN + root).digest()
        self._episode_key = hashlib.sha256(
            _EPISODE_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        self._body_key = hashlib.sha256(_BODY_DOMAIN + root).digest()
        self._custody_key = custody_authority_key
        self._w1_key = w1_physical_authority_key
        self._world_key = world_authority_key
        self._self_acoustic_key = w1_self_acoustic_authority_key
        self._things = thing_owner
        self._expansions = sensory_expansion_owner
        self._actions = action_execution_authority
        self._profile = resource_profile
        self._prepared_authority = object()
        self._undo_authority = object()
        self._episodes: tuple[CausalThingLivedContextEpisode, ...] = ()
        self._action_records: tuple[CausalThingActionExecution, ...] = ()
        self._replay: dict[str, tuple[int, int]] = {}
        self._lock = threading.RLock()

    @property
    def episodes(self) -> tuple[CausalThingLivedContextEpisode, ...]:
        with self._lock:
            return self._episodes

    @property
    def action_records(self) -> tuple[CausalThingActionExecution, ...]:
        with self._lock:
            return self._action_records

    def resolve_action_execution(
        self,
        execution_receipt_sha256: str,
    ) -> CausalThingActionExecution:
        """Resolve one durably lived action consequence by exact receipt."""

        _sha(
            execution_receipt_sha256,
            "resolved lived-context action execution",
        )
        with self._lock:
            matches = tuple(
                value
                for value in self._action_records
                if value.authority_receipt_sha256
                == execution_receipt_sha256
            )
            if len(matches) != 1:
                raise ValueError(
                    "lived-context action execution is not exactly retained"
                )
            self._verify_action(matches[0])
            return matches[0]

    def _body_provenance(
        self,
        custody: SettledExperienceCustody,
    ) -> LivedBodyProvenance | None:
        execution = custody.world_execution
        if execution is None or execution.actor_body_id is None:
            return None
        matching = tuple(
            body
            for body in custody.world_observation.bodies
            if body.body_id == execution.actor_body_id
        )
        if len(matching) != 1:
            raise ValueError(
                "lived-context actor lacks physical body provenance"
            )
        body = matching[0]
        result = LivedBodyProvenance(
            role=(
                "self"
                if body.body_id
                == custody.world_observation.self_body_id
                else "other"
            ),
            body_continuity_hmac_sha256=hmac.new(
                self._body_key,
                _BODY_DOMAIN + body.body_id.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest(),
            physical_state_sha256=_digest(body.as_record()),
        )
        result.verify()
        return result

    @staticmethod
    def _source_extent(
        custody: SettledExperienceCustody,
    ) -> tuple[str, str | None, int | None, Fraction, Fraction, str]:
        if custody.physical_evidence_receipt is not None:
            receipt = custody.physical_evidence_receipt
            return (
                receipt.authority_receipt_sha256,
                receipt.prior_evidence_receipt_sha256,
                receipt.sequence,
                receipt.source_time_start,
                receipt.source_time_end,
                receipt.world_observation_before_receipt_sha256,
            )
        receipt = custody.self_acoustic_receipt
        if receipt is None:
            raise ValueError("lived context lacks an authenticated W1 source")
        return (
            receipt.authority_receipt_sha256,
            None,
            None,
            receipt.source_time_start,
            receipt.source_time_end,
            receipt.world_before_receipt_sha256,
        )

    def _partition_reference(
        self,
        partition: ThingEncounterPartition,
    ) -> _DurableReference:
        if not isinstance(partition, ThingEncounterPartition):
            raise TypeError("lived context partition reference is not typed")
        matches = tuple(
            (mosaic.thing_id, candidate)
            for mosaic in self._things.mosaics
            for candidate in mosaic.partitions
            if candidate.authority_receipt_sha256
            == partition.authority_receipt_sha256
        )
        if len(matches) != 1 or matches[0][1] != partition:
            raise ValueError(
                "lived context partition is absent from durable THING state"
            )
        thing_id, owned = matches[0]
        if (
            owned.source_occurrence_id is None
            or owned.parent_custody_receipt_sha256 is None
        ):
            raise ValueError(
                "lived context partition lacks settled custody provenance"
            )
        return _DurableReference(
            kind="thing_partition",
            receipt=owned.authority_receipt_sha256,
            source_occurrence_id=owned.source_occurrence_id,
            parent_custody_receipt_sha256=(
                owned.parent_custody_receipt_sha256
            ),
            settlement_receipt_sha256=owned.settlement_receipt_sha256,
            settlement_structural_fingerprint=(
                owned.settlement_structural_fingerprint
            ),
            roots=owned.full_field_roots,
            owning_thing_id=thing_id,
            world_revision=owned.world_revision,
            world_observation_receipt_sha256=(
                owned.world_observation_receipt_sha256
            ),
            world_execution_receipt_sha256=(
                owned.execution_receipt_sha256
            ),
        )

    def _expansion_reference(
        self,
        expansion: CausalThingSensoryExpansion,
    ) -> _DurableReference:
        if not isinstance(expansion, CausalThingSensoryExpansion):
            raise TypeError("lived context expansion reference is not typed")
        if self._expansions is None:
            raise ValueError("lived context has no sensory expansion owner")
        self._expansions.snapshot_encoded()
        matches = tuple(
            candidate
            for candidate in self._expansions.expansions
            if candidate.authority_receipt_sha256
            == expansion.authority_receipt_sha256
        )
        if len(matches) != 1 or matches[0] != expansion:
            raise ValueError(
                "lived context expansion is absent from durable THING state"
            )
        owned = matches[0]
        direct_settled = (
            owned.admission_basis
            == "settled_known_sight_continuation"
        )
        return _DurableReference(
            kind="sensory_expansion",
            receipt=owned.authority_receipt_sha256,
            source_occurrence_id=owned.source_occurrence_id,
            parent_custody_receipt_sha256=(
                owned.parent_custody_receipt_sha256
            ),
            settlement_receipt_sha256=owned.settlement_receipt_sha256,
            settlement_structural_fingerprint=(
                owned.settlement_structural_fingerprint
            ),
            roots=owned.full_field_roots,
            owning_thing_id=owned.thing_id,
            world_revision=(
                owned.world_revision if direct_settled else None
            ),
            world_observation_receipt_sha256=(
                owned.world_observation_receipt_sha256
                if direct_settled else None
            ),
            world_execution_receipt_sha256=(
                owned.world_execution_receipt_sha256
                if direct_settled else None
            ),
        )

    def _partition_boundary(
        self,
        custody: SettledExperienceCustody,
        partition: ThingEncounterPartition,
    ) -> _LiveBoundary:
        if not isinstance(custody, SettledExperienceCustody):
            raise TypeError(
                "lived context partition requires settled custody"
            )
        custody.verify(
            authority_key=self._custody_key,
            w1_physical_authority_key=self._w1_key,
            world_authority_key=self._world_key,
            w1_self_acoustic_authority_key=self._self_acoustic_key,
        )
        reference = self._partition_reference(partition)
        if (
            reference.source_occurrence_id != custody.source_occurrence_id
            or reference.parent_custody_receipt_sha256
            != custody.authority_receipt_sha256
            or reference.settlement_receipt_sha256
            != custody.causal_settlement.authority_receipt_sha256
            or reference.settlement_structural_fingerprint
            != custody.causal_settlement.structural_fingerprint
            or reference.world_revision != custody.world_observation.revision
            or reference.world_observation_receipt_sha256
            != custody.world_observation.authority_receipt_sha256
            or custody.world_execution is None
            or reference.world_execution_receipt_sha256
            != custody.world_execution.authority_receipt_sha256
        ):
            raise ValueError(
                "lived context partition crossed live physical custody"
            )
        route = self._things.route(custody.causal_settlement)
        expected_keys = tuple(sorted(root.route_key for root in reference.roots))
        if (
            not isinstance(route, CausalThingRoute)
            or route.state not in {"unique", "ambiguous"}
            or reference.owning_thing_id not in route.thing_ids
            or route.matching_route_keys != expected_keys
        ):
            raise ValueError(
                "lived context partition lacks exact durable THING route"
            )
        (
            source_receipt,
            prior_source_receipt,
            source_sequence,
            source_time_start,
            source_time_end,
            world_before_receipt,
        ) = self._source_extent(custody)
        return _LiveBoundary(
            reference=reference,
            source_kind=custody.source_kind.value,
            source_receipt_sha256=source_receipt,
            prior_source_receipt_sha256=prior_source_receipt,
            source_sequence=source_sequence,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            world_before_receipt_sha256=world_before_receipt,
            actor_body_provenance=self._body_provenance(custody),
            route=route,
        )

    def _expansion_boundary(
        self,
        expansion: CausalThingSensoryExpansion,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> _LiveBoundary:
        if not isinstance(
            custody_authority,
            RetainedAudiovisualCustodyAuthority,
        ):
            raise TypeError(
                "lived context expansion requires audiovisual custody"
            )
        if not isinstance(
            custody_capability,
            RetainedAudiovisualCustodyCapability,
        ):
            raise TypeError(
                "lived context expansion capability is not typed"
            )
        custody = custody_authority.open_child(custody_capability)
        if (
            expansion.admission_basis
            == "settled_known_sight_continuation"
        ):
            raise ValueError(
                "direct settled expansion requires original settled custody"
            )
        reference = self._expansion_reference(expansion)
        if (
            reference.source_occurrence_id != custody.source_occurrence_id
            or reference.parent_custody_receipt_sha256
            != custody.authority_receipt_sha256
            or expansion.custody_capability_receipt_sha256
            != custody_capability.authority_receipt_sha256
            or reference.settlement_receipt_sha256
            != custody.settlement.authority_receipt_sha256
            or reference.settlement_structural_fingerprint
            != custody.settlement.structural_fingerprint
        ):
            raise ValueError(
                "lived context expansion crossed audiovisual custody"
            )
        return _LiveBoundary(
            reference=reference,
            source_kind="retained_audiovisual",
            source_receipt_sha256=expansion.authority_receipt_sha256,
            prior_source_receipt_sha256=None,
            source_sequence=expansion.sequence,
            source_time_start=custody.settlement.source_time_start,
            source_time_end=custody.settlement.source_time_end,
            world_before_receipt_sha256=None,
            actor_body_provenance=None,
            route=CausalThingRoute(
                state="unique",
                thing_ids=(expansion.thing_id,),
                matching_route_keys=tuple(
                    sorted(root.route_key for root in expansion.full_field_roots)
                ),
            ),
        )

    def _settled_expansion_boundary(
        self,
        expansion: CausalThingSensoryExpansion,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> _LiveBoundary:
        if not isinstance(
            custody_authority,
            SettledExperienceCustodyAuthority,
        ):
            raise TypeError(
                "lived context direct expansion requires settled custody"
            )
        if (
            not isinstance(
                custody_capability,
                SettledExperienceConsumerCapability,
            )
            or custody_capability.consumer_id
            != THING_SENSORY_EXPANSION_CONSUMER_ID
        ):
            raise ValueError(
                "lived context direct expansion requires its capability"
            )
        custody = custody_authority.open_child(custody_capability)
        settled = custody_authority.custody
        reference = self._expansion_reference(expansion)
        execution = custody.world_execution
        if (
            settled is None
            or
            expansion.admission_basis
            != "settled_known_sight_continuation"
            or execution is None
            or reference.source_occurrence_id
            != custody.source_occurrence_id
            or reference.parent_custody_receipt_sha256
            != custody.parent_custody_receipt_sha256
            or expansion.custody_capability_receipt_sha256
            != custody_capability.authority_receipt_sha256
            or reference.settlement_receipt_sha256
            != custody.causal_settlement.authority_receipt_sha256
            or reference.settlement_structural_fingerprint
            != custody.causal_settlement.structural_fingerprint
            or reference.world_revision
            != custody.world_observation.revision
            or reference.world_observation_receipt_sha256
            != custody.world_observation.authority_receipt_sha256
            or reference.world_execution_receipt_sha256
            != execution.authority_receipt_sha256
            or expansion.world_before_receipt_sha256
            != execution.before.authority_receipt_sha256
        ):
            raise ValueError(
                "lived context direct expansion crossed settled custody"
            )
        (
            source_receipt,
            prior_source_receipt,
            source_sequence,
            source_time_start,
            source_time_end,
            world_before_receipt,
        ) = self._source_extent(settled)
        return _LiveBoundary(
            reference=reference,
            source_kind=custody.source_kind.value,
            source_receipt_sha256=source_receipt,
            prior_source_receipt_sha256=prior_source_receipt,
            source_sequence=source_sequence,
            source_time_start=source_time_start,
            source_time_end=source_time_end,
            world_before_receipt_sha256=world_before_receipt,
            actor_body_provenance=self._body_provenance(
                settled
            ),
            route=CausalThingRoute(
                state="unique",
                thing_ids=(expansion.thing_id,),
                matching_route_keys=tuple(sorted(
                    root.route_key
                    for root in expansion.full_field_roots
                )),
            ),
        )

    @staticmethod
    def _continuity(
        previous: CausalThingLivedContextEvent,
        boundary: _LiveBoundary,
    ) -> str | None:
        reference = boundary.reference
        exact_source = (
            reference.world_revision is not None
            and previous.world_revision is not None
            and boundary.source_kind == previous.source_kind
            and boundary.prior_source_receipt_sha256
            == previous.source_receipt_sha256
            and boundary.source_sequence is not None
            and previous.source_sequence is not None
            and boundary.source_sequence == previous.source_sequence + 1
            and boundary.source_time_start == previous.source_time_end
            and boundary.world_before_receipt_sha256
            == previous.world_observation_receipt_sha256
            and reference.world_revision
            in {previous.world_revision, previous.world_revision + 1}
        )
        if exact_source:
            return "exact_source_continuation"
        exact_world = (
            reference.world_revision is not None
            and previous.world_revision is not None
            and boundary.world_before_receipt_sha256
            == previous.world_observation_receipt_sha256
            and reference.world_revision == previous.world_revision + 1
        )
        if exact_world:
            return "exact_world_transition"
        return None

    def _seal_event(
        self,
        provisional: CausalThingLivedContextEvent,
    ) -> CausalThingLivedContextEvent:
        signature = hmac.new(
            self._event_key,
            _EVENT_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        values = {
            name: getattr(provisional, name)
            for name in provisional.__dataclass_fields__
            if name not in {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
            }
        }
        return CausalThingLivedContextEvent(
            **values,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _verify_event(self, event: CausalThingLivedContextEvent) -> None:
        if not isinstance(event, CausalThingLivedContextEvent):
            raise TypeError("lived-context event is not typed")
        if (
            isinstance(event.ordinal, bool)
            or not isinstance(event.ordinal, int)
            or event.ordinal < 0
            or isinstance(event.episode_ordinal, bool)
            or not isinstance(event.episode_ordinal, int)
            or event.episode_ordinal < 0
            or event.continuity not in _CONTINUITIES
            or event.durable_reference_kind not in _REFERENCE_KINDS
            or not isinstance(event.source_kind, str)
            or not event.source_kind
            or (
                event.source_sequence is not None
                and (
                    isinstance(event.source_sequence, bool)
                    or not isinstance(event.source_sequence, int)
                    or event.source_sequence < 0
                )
            )
            or event.source_time_end <= event.source_time_start
            or event.thing_route_state not in {"unique", "ambiguous"}
            or not event.thing_ids
            or tuple(sorted(set(event.thing_ids))) != event.thing_ids
            or (
                event.thing_route_state == "unique"
                and len(event.thing_ids) != 1
            )
            or (
                event.thing_route_state == "ambiguous"
                and len(event.thing_ids) < 2
            )
            or isinstance(event.full_field_root_count, bool)
            or not isinstance(event.full_field_root_count, int)
            or not 0 < event.full_field_root_count <= (
                self._profile.max_full_field_roots_per_event
            )
            or isinstance(event.matching_route_key_count, bool)
            or not isinstance(event.matching_route_key_count, int)
            or event.matching_route_key_count
            != event.full_field_root_count
        ):
            raise ValueError("lived-context event boundary changed")
        for digest, label in (
            (event.durable_reference_receipt_sha256, "durable reference"),
            (event.source_occurrence_id, "source occurrence"),
            (event.parent_custody_receipt_sha256, "parent custody"),
            (event.source_receipt_sha256, "source receipt"),
            (event.settlement_receipt_sha256, "settlement"),
            (
                event.settlement_structural_fingerprint,
                "settlement structure",
            ),
            (
                event.full_field_commitment_sha256,
                "full-field commitment",
            ),
            (
                event.matching_route_commitment_sha256,
                "route commitment",
            ),
            (event.authority_hmac_sha256, "event HMAC"),
            (event.authority_receipt_sha256, "event authority"),
        ):
            _sha(digest, f"lived-context {label}")
        for optional, label in (
            (event.prior_event_receipt_sha256, "prior event"),
            (event.prior_source_receipt_sha256, "prior source"),
            (event.world_observation_receipt_sha256, "world observation"),
            (event.world_before_receipt_sha256, "world before"),
            (event.world_execution_receipt_sha256, "world execution"),
            (event.action_consequence_receipt_sha256, "action consequence"),
        ):
            _optional_sha(optional, f"lived-context {label}")
        for thing_id in event.thing_ids:
            _sha(thing_id, "lived-context THING")
        if event.actor_body_provenance is not None:
            event.actor_body_provenance.verify()
        if event.durable_reference_kind == "thing_partition":
            if (
                isinstance(event.world_revision, bool)
                or not isinstance(event.world_revision, int)
                or event.world_revision < 0
                or event.world_observation_receipt_sha256 is None
                or event.world_before_receipt_sha256 is None
                or event.world_execution_receipt_sha256 is None
                or event.source_kind
                not in tuple(value.value for value in SettledExperienceSourceKind)
            ):
                raise ValueError(
                    "lived-context partition world boundary changed"
                )
        elif event.source_kind == "retained_audiovisual":
            if (
                event.world_revision is not None
                or event.world_observation_receipt_sha256 is not None
                or event.world_before_receipt_sha256 is not None
                or event.world_execution_receipt_sha256 is not None
                or event.actor_body_provenance is not None
            ):
                raise ValueError(
                    "lived-context expansion invented W1 world authority"
                )
        elif (
            event.source_kind
            not in tuple(
                value.value for value in SettledExperienceSourceKind
            )
            or isinstance(event.world_revision, bool)
            or not isinstance(event.world_revision, int)
            or event.world_revision < 0
            or event.world_observation_receipt_sha256 is None
            or event.world_before_receipt_sha256 is None
            or event.world_execution_receipt_sha256 is None
        ):
            raise ValueError(
                "lived-context direct expansion lost W1 authority"
            )
        expected = hmac.new(
            self._event_key,
            _EVENT_DOMAIN + _canonical(event.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, event.authority_hmac_sha256)
            or event.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": event.payload(),
            })
        ):
            raise ValueError("lived-context event authority changed")

    def _seal_episode(
        self,
        *,
        ordinal: int,
        episode_id: str,
        events: tuple[CausalThingLivedContextEvent, ...],
    ) -> CausalThingLivedContextEpisode:
        provisional = CausalThingLivedContextEpisode(
            episode_id=episode_id,
            ordinal=ordinal,
            cross_episode_order_authority="none",
            events=events,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._episode_key,
            _EPISODE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return CausalThingLivedContextEpisode(
            episode_id=episode_id,
            ordinal=ordinal,
            cross_episode_order_authority="none",
            events=events,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _verify_episode(
        self,
        episode: CausalThingLivedContextEpisode,
    ) -> None:
        if (
            not isinstance(episode, CausalThingLivedContextEpisode)
            or isinstance(episode.ordinal, bool)
            or not isinstance(episode.ordinal, int)
            or episode.ordinal < 0
            or episode.cross_episode_order_authority != "none"
            or not episode.events
            or len(episode.events) > self._profile.max_events_per_episode
            or tuple(value.episode_ordinal for value in episode.events)
            != tuple(range(len(episode.events)))
        ):
            raise ValueError("lived-context episode boundary changed")
        for event in episode.events:
            self._verify_event(event)
        for digest, label in (
            (episode.episode_id, "episode id"),
            (episode.authority_hmac_sha256, "episode HMAC"),
            (episode.authority_receipt_sha256, "episode authority"),
        ):
            _sha(digest, f"lived-context {label}")
        expected = hmac.new(
            self._episode_key,
            _EPISODE_DOMAIN + _canonical(episode.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected, episode.authority_hmac_sha256
            )
            or episode.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": episode.payload(),
            })
        ):
            raise ValueError("lived-context episode authority changed")

    def _verify_action(
        self,
        action: CausalThingActionExecution,
    ) -> None:
        if self._actions is None:
            raise ValueError(
                "lived context has no action consequence authority"
            )
        self._actions.verify(action)

    def _verify_event_reference(
        self,
        event: CausalThingLivedContextEvent,
        reference: _DurableReference,
        action: CausalThingActionExecution | None,
    ) -> None:
        (
            full_commitment,
            root_count,
            route_commitment,
            route_count,
        ) = _root_commitments(reference.roots)
        if (
            event.durable_reference_kind != reference.kind
            or event.durable_reference_receipt_sha256 != reference.receipt
            or event.source_occurrence_id != reference.source_occurrence_id
            or event.parent_custody_receipt_sha256
            != reference.parent_custody_receipt_sha256
            or event.settlement_receipt_sha256
            != reference.settlement_receipt_sha256
            or event.settlement_structural_fingerprint
            != reference.settlement_structural_fingerprint
            or event.full_field_commitment_sha256 != full_commitment
            or event.full_field_root_count != root_count
            or event.matching_route_commitment_sha256 != route_commitment
            or event.matching_route_key_count != route_count
            or reference.owning_thing_id not in event.thing_ids
            or event.world_revision != reference.world_revision
            or event.world_observation_receipt_sha256
            != reference.world_observation_receipt_sha256
            or event.world_execution_receipt_sha256
            != reference.world_execution_receipt_sha256
        ):
            raise ValueError(
                "lived-context event crossed its durable reference"
            )
        current_thing_ids = {
            mosaic.thing_id for mosaic in self._things.mosaics
        }
        root_index: dict[tuple[str, str], set[str]] = {}
        for mosaic in self._things.mosaics:
            for partition in mosaic.partitions:
                for root in partition.full_field_roots:
                    root_index.setdefault(root.route_key, set()).add(
                        mosaic.thing_id
                    )
        if self._expansions is not None:
            for expansion in self._expansions.expansions:
                for root in expansion.full_field_roots:
                    root_index.setdefault(root.route_key, set()).add(
                        expansion.thing_id
                    )
        currently_related = {
            thing_id
            for root in reference.roots
            for thing_id in root_index.get(root.route_key, ())
        }
        if (
            not set(event.thing_ids).issubset(current_thing_ids)
            or not set(event.thing_ids).issubset(currently_related)
        ):
            raise ValueError(
                "lived-context historical route left durable THING state"
            )
        if reference.kind == "sensory_expansion" and (
            event.thing_route_state != "unique"
            or event.thing_ids != (reference.owning_thing_id,)
        ):
            raise ValueError(
                "lived-context expansion changed its owned THING"
            )
        if action is None:
            if event.action_consequence_receipt_sha256 is not None:
                raise ValueError(
                    "lived-context action consequence record is absent"
                )
        else:
            self._verify_action(action)
            if (
                event.action_consequence_receipt_sha256
                != action.authority_receipt_sha256
                or action.world_execution_receipt_sha256
                != event.world_execution_receipt_sha256
                or action.actual_outcome_settlement_receipt_sha256
                != event.settlement_receipt_sha256
                or action.actual_outcome_structural_fingerprint
                != event.settlement_structural_fingerprint
                or action.outcome_custody_receipt_sha256
                != event.parent_custody_receipt_sha256
                or action.thing_id not in event.thing_ids
            ):
                raise ValueError(
                    "lived-context action crossed durable occurrence"
                )

    def _body(
        self,
        episodes: tuple[CausalThingLivedContextEpisode, ...],
        actions: tuple[CausalThingActionExecution, ...],
    ) -> dict[str, object]:
        return {
            "action_execution_records": [
                value.record() for value in actions
            ],
            "durable_reference_law": (
                "thing_partition_or_sensory_expansion"
            ),
            "episodes": [value.record() for value in episodes],
            "full_field": True,
            "meaning_authority": False,
            "profile": self._profile.record(),
            "reduced_approximation": False,
            "schema": STATE_SCHEMA,
            "transient_custody_archive": False,
        }

    def _encoded(
        self,
        episodes: tuple[CausalThingLivedContextEpisode, ...],
        actions: tuple[CausalThingActionExecution, ...],
    ) -> bytes:
        event_count = sum(len(value.events) for value in episodes)
        if (
            len(episodes) > self._profile.max_episodes
            or event_count > self._profile.max_total_events
            or len(actions) > event_count
            or any(
                len(value.events)
                > self._profile.max_events_per_episode
                for value in episodes
            )
        ):
            raise RuntimeError("lived-context event capacity exhausted")
        payload = _canonical(self._body(episodes, actions))
        encoded = _canonical({
            "authority_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + payload,
                hashlib.sha256,
            ).hexdigest(),
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "lived-context state byte capacity exhausted"
            )
        return encoded

    def _prepare_boundary(
        self,
        boundary: _LiveBoundary,
        *,
        action_consequence: CausalThingActionExecution | None,
    ) -> PreparedCausalThingLivedContextAdmission:
        reference = boundary.reference
        (
            full_commitment,
            root_count,
            route_commitment,
            route_count,
        ) = _root_commitments(reference.roots)
        if root_count > self._profile.max_full_field_roots_per_event:
            raise RuntimeError(
                "lived-context field root capacity exhausted"
            )
        if action_consequence is not None:
            self._verify_action(action_consequence)
        with self._lock:
            replay = self._replay.get(reference.source_occurrence_id)
            if replay is not None:
                episode = self._episodes[replay[0]]
                event = episode.events[replay[1]]
                expected_action = (
                    action_consequence.authority_receipt_sha256
                    if action_consequence is not None else None
                )
                if (
                    event.durable_reference_receipt_sha256
                    != reference.receipt
                    or event.action_consequence_receipt_sha256
                    != expected_action
                ):
                    raise ValueError(
                        "lived-context replay changed durable authority"
                    )
                prepared = PreparedCausalThingLivedContextAdmission(
                    admission=CausalThingLivedContextAdmission(
                        state="replayed",
                        episode=episode,
                        event=event,
                    ),
                    _prior_episodes=self._episodes,
                    _staged_episodes=self._episodes,
                    _prior_actions=self._action_records,
                    _staged_actions=self._action_records,
                    _transaction_state=_AdmissionTransactionState(
                        phase="prepared"
                    ),
                    _authority=self._prepared_authority,
                )
                return prepared
            total = sum(len(value.events) for value in self._episodes)
            if total >= self._profile.max_total_events:
                raise RuntimeError(
                    "lived-context total event capacity exhausted"
                )
            prior = self._episodes[-1].events[-1] if self._episodes else None
            append = False
            if prior is None:
                continuity = "episode_genesis"
            elif reference.world_revision is None or prior.world_revision is None:
                continuity = "reference_only_genesis"
            else:
                exact = self._continuity(prior, boundary)
                if exact is not None:
                    if (
                        len(self._episodes[-1].events)
                        >= self._profile.max_events_per_episode
                    ):
                        raise RuntimeError(
                            "lived-context episode capacity exhausted"
                        )
                    continuity = exact
                    append = True
                elif reference.world_revision > prior.world_revision:
                    continuity = "discontinuous_world_gap_genesis"
                else:
                    raise ValueError(
                        "lived-context occurrence lacks exact causal "
                        "continuity"
                    )
            if not append and len(self._episodes) >= self._profile.max_episodes:
                raise RuntimeError(
                    "lived-context episode capacity exhausted"
                )
            episode_index = (
                len(self._episodes) - 1 if append else len(self._episodes)
            )
            event_index = (
                len(self._episodes[-1].events) if append else 0
            )
            provisional = CausalThingLivedContextEvent(
                ordinal=total,
                episode_ordinal=event_index,
                continuity=continuity,
                prior_event_receipt_sha256=(
                    prior.authority_receipt_sha256
                    if append and prior is not None else None
                ),
                durable_reference_kind=reference.kind,
                durable_reference_receipt_sha256=reference.receipt,
                source_occurrence_id=reference.source_occurrence_id,
                parent_custody_receipt_sha256=(
                    reference.parent_custody_receipt_sha256
                ),
                source_kind=boundary.source_kind,
                source_receipt_sha256=boundary.source_receipt_sha256,
                prior_source_receipt_sha256=(
                    boundary.prior_source_receipt_sha256
                ),
                source_sequence=boundary.source_sequence,
                source_time_start=boundary.source_time_start,
                source_time_end=boundary.source_time_end,
                world_revision=reference.world_revision,
                world_observation_receipt_sha256=(
                    reference.world_observation_receipt_sha256
                ),
                world_before_receipt_sha256=(
                    boundary.world_before_receipt_sha256
                ),
                world_execution_receipt_sha256=(
                    reference.world_execution_receipt_sha256
                ),
                actor_body_provenance=boundary.actor_body_provenance,
                thing_route_state=boundary.route.state,
                thing_ids=boundary.route.thing_ids,
                matching_route_commitment_sha256=route_commitment,
                matching_route_key_count=route_count,
                settlement_receipt_sha256=(
                    reference.settlement_receipt_sha256
                ),
                settlement_structural_fingerprint=(
                    reference.settlement_structural_fingerprint
                ),
                full_field_commitment_sha256=full_commitment,
                full_field_root_count=root_count,
                action_consequence_receipt_sha256=(
                    action_consequence.authority_receipt_sha256
                    if action_consequence is not None else None
                ),
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            event = self._seal_event(provisional)
            self._verify_event(event)
            self._verify_event_reference(
                event,
                reference,
                action_consequence,
            )
            if append:
                old = self._episodes[-1]
                episode = self._seal_episode(
                    ordinal=old.ordinal,
                    episode_id=old.episode_id,
                    events=old.events + (event,),
                )
                staged_episodes = self._episodes[:-1] + (episode,)
            else:
                episode = self._seal_episode(
                    ordinal=len(self._episodes),
                    episode_id=_digest({
                        "episode_genesis_event_receipt_sha256": (
                            event.authority_receipt_sha256
                        )
                    }),
                    events=(event,),
                )
                staged_episodes = self._episodes + (episode,)
            self._verify_episode(episode)
            staged_actions = self._action_records
            if action_consequence is not None:
                if any(
                    value.authority_receipt_sha256
                    == action_consequence.authority_receipt_sha256
                    for value in staged_actions
                ):
                    raise ValueError(
                        "lived-context action record repeats another event"
                    )
                staged_actions += (action_consequence,)
            self._encoded(staged_episodes, staged_actions)
            return PreparedCausalThingLivedContextAdmission(
                admission=CausalThingLivedContextAdmission(
                    state="admitted",
                    episode=episode,
                    event=event,
                ),
                _prior_episodes=self._episodes,
                _staged_episodes=staged_episodes,
                _prior_actions=self._action_records,
                _staged_actions=staged_actions,
                _transaction_state=_AdmissionTransactionState(
                    phase="prepared"
                ),
                _authority=self._prepared_authority,
            )

    def prepare_admission(
        self,
        custody: SettledExperienceCustody,
        *,
        durable_reference: ThingEncounterPartition,
        action_consequence: CausalThingActionExecution | None = None,
    ) -> PreparedCausalThingLivedContextAdmission:
        return self._prepare_boundary(
            self._partition_boundary(custody, durable_reference),
            action_consequence=action_consequence,
        )

    def prepare_expansion_admission(
        self,
        durable_reference: CausalThingSensoryExpansion,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> PreparedCausalThingLivedContextAdmission:
        return self._prepare_boundary(
            self._expansion_boundary(
                durable_reference,
                custody_authority=custody_authority,
                custody_capability=custody_capability,
            ),
            action_consequence=None,
        )

    def prepare_settled_expansion_admission(
        self,
        durable_reference: CausalThingSensoryExpansion,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> PreparedCausalThingLivedContextAdmission:
        return self._prepare_boundary(
            self._settled_expansion_boundary(
                durable_reference,
                custody_authority=custody_authority,
                custody_capability=custody_capability,
            ),
            action_consequence=None,
        )

    def _verify_prepared(
        self,
        prepared: PreparedCausalThingLivedContextAdmission,
    ) -> None:
        if (
            not isinstance(
                prepared, PreparedCausalThingLivedContextAdmission
            )
            or prepared._authority is not self._prepared_authority
        ):
            raise TypeError("lived-context prepared admission is not owned")

    def commit_prepared_admission(
        self,
        prepared: PreparedCausalThingLivedContextAdmission,
    ) -> CommittedCausalThingLivedContextAdmissionUndo:
        self._verify_prepared(prepared)
        with self._lock:
            if prepared._transaction_state.phase != "prepared":
                raise ValueError(
                    "lived-context prepared admission is not committable"
                )
            if (
                self._episodes != prepared._prior_episodes
                or self._action_records != prepared._prior_actions
            ):
                raise RuntimeError("lived-context prepared admission is stale")
            self._episodes = prepared._staged_episodes
            self._action_records = prepared._staged_actions
            self._rebuild_replay()
            prepared._transaction_state.phase = "committed"
            return CommittedCausalThingLivedContextAdmissionUndo(
                prepared=prepared,
                _authority=self._undo_authority,
            )

    def discard_prepared_admission(
        self,
        prepared: PreparedCausalThingLivedContextAdmission,
    ) -> None:
        self._verify_prepared(prepared)
        with self._lock:
            if prepared._transaction_state.phase != "prepared":
                raise ValueError(
                    "lived-context prepared admission is not discardable"
                )
            prepared._transaction_state.phase = "discarded"

    def rollback_committed_admission(
        self,
        undo: CommittedCausalThingLivedContextAdmissionUndo,
    ) -> None:
        if (
            not isinstance(
                undo, CommittedCausalThingLivedContextAdmissionUndo
            )
            or undo._authority is not self._undo_authority
        ):
            raise TypeError("lived-context admission undo is not owned")
        prepared = undo.prepared
        self._verify_prepared(prepared)
        with self._lock:
            if prepared._transaction_state.phase != "committed":
                raise ValueError(
                    "lived-context committed admission is not rollbackable"
                )
            if (
                self._episodes != prepared._staged_episodes
                or self._action_records != prepared._staged_actions
            ):
                raise RuntimeError(
                    "lived-context committed admission undo is stale"
                )
            self._episodes = prepared._prior_episodes
            self._action_records = prepared._prior_actions
            self._rebuild_replay()
            prepared._transaction_state.phase = "rolled_back"

    def admit(
        self,
        custody: SettledExperienceCustody,
        *,
        durable_reference: ThingEncounterPartition,
        action_consequence: CausalThingActionExecution | None = None,
    ) -> CausalThingLivedContextAdmission:
        prepared = self.prepare_admission(
            custody,
            durable_reference=durable_reference,
            action_consequence=action_consequence,
        )
        self.commit_prepared_admission(prepared)
        return prepared.admission

    def admit_expansion(
        self,
        durable_reference: CausalThingSensoryExpansion,
        *,
        custody_authority: RetainedAudiovisualCustodyAuthority,
        custody_capability: RetainedAudiovisualCustodyCapability,
    ) -> CausalThingLivedContextAdmission:
        prepared = self.prepare_expansion_admission(
            durable_reference,
            custody_authority=custody_authority,
            custody_capability=custody_capability,
        )
        self.commit_prepared_admission(prepared)
        return prepared.admission

    def admit_settled_expansion(
        self,
        durable_reference: CausalThingSensoryExpansion,
        *,
        custody_authority: SettledExperienceCustodyAuthority,
        custody_capability: SettledExperienceConsumerCapability,
    ) -> CausalThingLivedContextAdmission:
        prepared = self.prepare_settled_expansion_admission(
            durable_reference,
            custody_authority=custody_authority,
            custody_capability=custody_capability,
        )
        self.commit_prepared_admission(prepared)
        return prepared.admission

    def verify_owned_event(
        self,
        event: CausalThingLivedContextEvent,
    ) -> None:
        """Verify one immutable event and its retained durable provenance."""

        self._verify_event(event)
        with self._lock:
            matches = tuple(
                (episode, candidate)
                for episode in self._episodes
                for candidate in episode.events
                if candidate.authority_receipt_sha256
                == event.authority_receipt_sha256
            )
            if len(matches) != 1 or matches[0][1] != event:
                raise ValueError(
                    "lived-context event is not exactly owned"
                )
            episode = matches[0][0]
            self._verify_episode(episode)
            if event.durable_reference_kind == "sensory_expansion":
                references = tuple(
                    value
                    for value in self._expansions.expansions
                    if value.authority_receipt_sha256
                    == event.durable_reference_receipt_sha256
                ) if self._expansions is not None else ()
                if len(references) != 1:
                    raise ValueError(
                        "lived-context event lost expansion provenance"
                    )
                reference = self._expansion_reference(references[0])
            else:
                references = tuple(
                    partition
                    for mosaic in self._things.mosaics
                    for partition in mosaic.partitions
                    if partition.authority_receipt_sha256
                    == event.durable_reference_receipt_sha256
                )
                if len(references) != 1:
                    raise ValueError(
                        "lived-context event lost partition provenance"
                    )
                reference = self._partition_reference(references[0])
            actions = tuple(
                value
                for value in self._action_records
                if value.authority_receipt_sha256
                == event.action_consequence_receipt_sha256
            )
            if event.action_consequence_receipt_sha256 is not None:
                if len(actions) != 1:
                    raise ValueError(
                        "lived-context event lost action provenance"
                    )
                action = actions[0]
            else:
                action = None
            self._verify_event_reference(event, reference, action)

    def _rebuild_replay(self) -> None:
        replay: dict[str, tuple[int, int]] = {}
        for episode_index, episode in enumerate(self._episodes):
            for event_index, event in enumerate(episode.events):
                if event.source_occurrence_id in replay:
                    raise ValueError(
                        "lived-context durable occurrence repeats"
                    )
                replay[event.source_occurrence_id] = (
                    episode_index,
                    event_index,
                )
        self._replay = replay

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._episodes, self._action_records)

    def status(self) -> dict[str, object]:
        with self._lock:
            events = tuple(
                event
                for episode in self._episodes
                for event in episode.events
            )
            return {
                "action_execution_records": len(self._action_records),
                "durable_partition_references": sum(
                    event.durable_reference_kind == "thing_partition"
                    for event in events
                ),
                "durable_sensory_expansion_references": sum(
                    event.durable_reference_kind == "sensory_expansion"
                    for event in events
                ),
                "episodes": len(self._episodes),
                "events": len(events),
                "full_field": True,
                "meaning_authority": False,
                "reduced_approximation": False,
                "schema": STATUS_SCHEMA,
                "state_bytes": len(
                    self._encoded(self._episodes, self._action_records)
                ),
                "state_capacity_bytes": self._profile.max_state_bytes,
                "transient_custody_archive": False,
            }

    @staticmethod
    def _action_from_record(
        value: object,
    ) -> CausalThingActionExecution:
        expected = {
            "actual_outcome_settlement_receipt_sha256",
            "actual_outcome_structural_fingerprint",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "expected_outcome_settlement_receipt_sha256",
            "expected_outcome_structural_fingerprint",
            "intent_receipt_sha256",
            "outcome_custody_capability_receipt_sha256",
            "outcome_custody_receipt_sha256",
            "prediction_verification",
            "schema",
            "source_binding_id",
            "thing_id",
            "world_disposition",
            "world_execution_receipt_sha256",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != EXECUTION_SCHEMA
        ):
            raise ValueError(
                "lived-context action execution record changed"
            )
        result = CausalThingActionExecution(
            intent_receipt_sha256=value.get("intent_receipt_sha256"),
            thing_id=value.get("thing_id"),
            source_binding_id=value.get("source_binding_id"),
            world_execution_receipt_sha256=value.get(
                "world_execution_receipt_sha256"
            ),
            world_disposition=value.get("world_disposition"),
            expected_outcome_settlement_receipt_sha256=value.get(
                "expected_outcome_settlement_receipt_sha256"
            ),
            expected_outcome_structural_fingerprint=value.get(
                "expected_outcome_structural_fingerprint"
            ),
            actual_outcome_settlement_receipt_sha256=value.get(
                "actual_outcome_settlement_receipt_sha256"
            ),
            actual_outcome_structural_fingerprint=value.get(
                "actual_outcome_structural_fingerprint"
            ),
            outcome_custody_receipt_sha256=value.get(
                "outcome_custody_receipt_sha256"
            ),
            outcome_custody_capability_receipt_sha256=value.get(
                "outcome_custody_capability_receipt_sha256"
            ),
            prediction_verification=value.get("prediction_verification"),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        if result.record() != dict(value):
            raise ValueError(
                "lived-context action execution is not canonical"
            )
        return result

    def _event_from_record(
        self,
        value: object,
    ) -> CausalThingLivedContextEvent:
        if (
            not isinstance(value, Mapping)
            or value.get("schema") != EVENT_SCHEMA
        ):
            raise ValueError("lived-context event record changed")
        actor = value.get("actor_body_provenance")
        event = CausalThingLivedContextEvent(
            ordinal=value.get("ordinal"),
            episode_ordinal=value.get("episode_ordinal"),
            continuity=value.get("continuity"),
            prior_event_receipt_sha256=value.get(
                "prior_event_receipt_sha256"
            ),
            durable_reference_kind=value.get(
                "durable_reference_kind"
            ),
            durable_reference_receipt_sha256=value.get(
                "durable_reference_receipt_sha256"
            ),
            source_occurrence_id=value.get("source_occurrence_id"),
            parent_custody_receipt_sha256=value.get(
                "parent_custody_receipt_sha256"
            ),
            source_kind=value.get("source_kind"),
            source_receipt_sha256=value.get("source_receipt_sha256"),
            prior_source_receipt_sha256=value.get(
                "prior_source_receipt_sha256"
            ),
            source_sequence=value.get("source_sequence"),
            source_time_start=_fraction(
                value.get("source_time_start"),
                "lived-context source start",
            ),
            source_time_end=_fraction(
                value.get("source_time_end"),
                "lived-context source end",
            ),
            world_revision=value.get("world_revision"),
            world_observation_receipt_sha256=value.get(
                "world_observation_receipt_sha256"
            ),
            world_before_receipt_sha256=value.get(
                "world_before_receipt_sha256"
            ),
            world_execution_receipt_sha256=value.get(
                "world_execution_receipt_sha256"
            ),
            actor_body_provenance=(
                LivedBodyProvenance.from_record(actor)
                if actor is not None else None
            ),
            thing_route_state=value.get("thing_route_state"),
            thing_ids=tuple(value.get("thing_ids", ())),
            matching_route_commitment_sha256=value.get(
                "matching_route_commitment_sha256"
            ),
            matching_route_key_count=value.get(
                "matching_route_key_count"
            ),
            settlement_receipt_sha256=value.get(
                "settlement_receipt_sha256"
            ),
            settlement_structural_fingerprint=value.get(
                "settlement_structural_fingerprint"
            ),
            full_field_commitment_sha256=value.get(
                "full_field_commitment_sha256"
            ),
            full_field_root_count=value.get("full_field_root_count"),
            action_consequence_receipt_sha256=value.get(
                "action_consequence_receipt_sha256"
            ),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        self._verify_event(event)
        if event.record() != dict(value):
            raise ValueError("lived-context event is not canonical")
        return event

    def _episode_from_record(
        self,
        value: object,
    ) -> CausalThingLivedContextEpisode:
        if (
            not isinstance(value, Mapping)
            or value.get("schema") != EPISODE_SCHEMA
            or not isinstance(value.get("events"), list)
        ):
            raise ValueError("lived-context episode record changed")
        episode = CausalThingLivedContextEpisode(
            episode_id=value.get("episode_id"),
            ordinal=value.get("ordinal"),
            cross_episode_order_authority=value.get(
                "cross_episode_order_authority"
            ),
            events=tuple(
                self._event_from_record(item)
                for item in value.get("events")
            ),
            authority_hmac_sha256=value.get("authority_hmac_sha256"),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        self._verify_episode(episode)
        if episode.record() != dict(value):
            raise ValueError("lived-context episode is not canonical")
        return episode

    def _reference_for_event(
        self,
        event: CausalThingLivedContextEvent,
    ) -> _DurableReference:
        if event.durable_reference_kind == "thing_partition":
            matches = tuple(
                partition
                for mosaic in self._things.mosaics
                for partition in mosaic.partitions
                if partition.authority_receipt_sha256
                == event.durable_reference_receipt_sha256
            )
            if len(matches) != 1:
                raise ValueError(
                    "lived-context durable partition reference is absent"
                )
            return self._partition_reference(matches[0])
        if self._expansions is None:
            raise ValueError(
                "lived-context durable expansion reference is absent"
            )
        matches = tuple(
            expansion
            for expansion in self._expansions.expansions
            if expansion.authority_receipt_sha256
            == event.durable_reference_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "lived-context durable expansion reference is absent"
            )
        return self._expansion_reference(matches[0])

    @classmethod
    def restore_encoded(
        cls,
        encoded: bytes,
        *,
        authority_key: bytes | str,
        custody_authority_key: bytes | str,
        w1_physical_authority_key: bytes | str,
        world_authority_key: bytes | str,
        thing_owner: CausalThingMosaicOwner,
        sensory_expansion_owner: (
            CausalThingSensoryExpansionOwner | None
        ) = None,
        w1_self_acoustic_authority_key: bytes | str | None = None,
        action_execution_authority: (
            CausalThingActionExecutionAuthority | None
        ) = None,
    ) -> "CausalThingLivedContextOwner":
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > MAX_CONFIGURED_STATE_BYTES
        ):
            raise ValueError(
                "lived-context snapshot is outside its safety boundary"
            )
        root = _key(authority_key, "causal THING lived context")
        state_key = hashlib.sha256(_STATE_DOMAIN + root).digest()
        try:
            envelope = json.loads(encoded.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "lived-context snapshot is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"authority_hmac_sha256", "payload_base64", "schema"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
        ):
            raise ValueError("lived-context snapshot envelope changed")
        try:
            payload = base64.b64decode(
                envelope.get("payload_base64"),
                validate=True,
            )
        except (TypeError, ValueError) as error:
            raise ValueError(
                "lived-context snapshot payload is unreadable"
            ) from error
        expected = hmac.new(
            state_key,
            _STATE_DOMAIN + payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected, envelope.get("authority_hmac_sha256", "")
        ):
            raise ValueError("lived-context snapshot authority changed")
        try:
            body = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "lived-context snapshot body is unreadable"
            ) from error
        expected_keys = {
            "action_execution_records",
            "durable_reference_law",
            "episodes",
            "full_field",
            "meaning_authority",
            "profile",
            "reduced_approximation",
            "schema",
            "transient_custody_archive",
        }
        if (
            not isinstance(body, Mapping)
            or _canonical(body) != payload
            or set(body) != expected_keys
            or body.get("schema") != STATE_SCHEMA
            or body.get("durable_reference_law")
            != "thing_partition_or_sensory_expansion"
            or body.get("full_field") is not True
            or body.get("meaning_authority") is not False
            or body.get("reduced_approximation") is not False
            or body.get("transient_custody_archive") is not False
        ):
            raise ValueError("lived-context snapshot body changed")
        profile = CausalThingLivedContextResourceProfile.from_record(
            body.get("profile")
        )
        owner = cls(
            authority_key=authority_key,
            custody_authority_key=custody_authority_key,
            w1_physical_authority_key=w1_physical_authority_key,
            world_authority_key=world_authority_key,
            thing_owner=thing_owner,
            sensory_expansion_owner=sensory_expansion_owner,
            resource_profile=profile,
            w1_self_acoustic_authority_key=(
                w1_self_acoustic_authority_key
            ),
            action_execution_authority=action_execution_authority,
        )
        raw_actions = body.get("action_execution_records")
        raw_episodes = body.get("episodes")
        if not isinstance(raw_actions, list) or not isinstance(
            raw_episodes, list
        ):
            raise ValueError("lived-context retained state changed")
        actions = tuple(
            owner._action_from_record(value) for value in raw_actions
        )
        for action in actions:
            owner._verify_action(action)
        if len({
            action.authority_receipt_sha256 for action in actions
        }) != len(actions):
            raise ValueError(
                "lived-context action journal repeats a record"
            )
        episodes = tuple(
            owner._episode_from_record(value) for value in raw_episodes
        )
        if tuple(value.ordinal for value in episodes) != tuple(
            range(len(episodes))
        ):
            raise ValueError("lived-context episode ordinals changed")
        action_index = {
            action.authority_receipt_sha256: action for action in actions
        }
        reference_receipts: set[str] = set()
        action_receipts: set[str] = set()
        expected_ordinal = 0
        prior_global: CausalThingLivedContextEvent | None = None
        replay: dict[str, tuple[int, int]] = {}
        for episode_index, episode in enumerate(episodes):
            owner._verify_episode(episode)
            prior_in_episode: CausalThingLivedContextEvent | None = None
            for event_index, event in enumerate(episode.events):
                if (
                    event.ordinal != expected_ordinal
                    or event.source_occurrence_id in replay
                    or event.durable_reference_receipt_sha256
                    in reference_receipts
                ):
                    raise ValueError(
                        "lived-context reference cardinality changed"
                    )
                replay[event.source_occurrence_id] = (
                    episode_index,
                    event_index,
                )
                reference_receipts.add(
                    event.durable_reference_receipt_sha256
                )
                action = None
                if event.action_consequence_receipt_sha256 is not None:
                    if (
                        event.action_consequence_receipt_sha256
                        in action_receipts
                    ):
                        raise ValueError(
                            "lived-context action journal cardinality "
                            "changed"
                        )
                    action_receipts.add(
                        event.action_consequence_receipt_sha256
                    )
                    action = action_index.get(
                        event.action_consequence_receipt_sha256
                    )
                    if action is None:
                        raise ValueError(
                            "lived-context action journal record is absent"
                        )
                reference = owner._reference_for_event(event)
                owner._verify_event_reference(event, reference, action)
                if prior_in_episode is None:
                    expected_genesis = (
                        "episode_genesis"
                        if prior_global is None
                        else (
                            "reference_only_genesis"
                            if event.world_revision is None
                            or prior_global.world_revision is None
                            else "discontinuous_world_gap_genesis"
                        )
                    )
                    if event.continuity != expected_genesis:
                        raise ValueError(
                            "lived-context restored genesis changed"
                        )
                    if (
                        expected_genesis
                        == "discontinuous_world_gap_genesis"
                        and event.world_revision <= prior_global.world_revision
                    ):
                        raise ValueError(
                            "lived-context restored world gap changed"
                        )
                else:
                    boundary = _LiveBoundary(
                        reference=reference,
                        source_kind=event.source_kind,
                        source_receipt_sha256=(
                            event.source_receipt_sha256
                        ),
                        prior_source_receipt_sha256=(
                            event.prior_source_receipt_sha256
                        ),
                        source_sequence=event.source_sequence,
                        source_time_start=event.source_time_start,
                        source_time_end=event.source_time_end,
                        world_before_receipt_sha256=(
                            event.world_before_receipt_sha256
                        ),
                        actor_body_provenance=(
                            event.actor_body_provenance
                        ),
                        route=CausalThingRoute(
                            state=event.thing_route_state,
                            thing_ids=event.thing_ids,
                            matching_route_keys=(),
                        ),
                    )
                    if event.continuity != owner._continuity(
                        prior_in_episode, boundary
                    ):
                        raise ValueError(
                            "lived-context restored continuity changed"
                        )
                    if event.prior_event_receipt_sha256 != (
                        prior_in_episode.authority_receipt_sha256
                    ):
                        raise ValueError(
                            "lived-context prior event link changed"
                        )
                prior_in_episode = event
                prior_global = event
                expected_ordinal += 1
        if action_receipts != set(action_index):
            raise ValueError(
                "lived-context action journal cardinality changed"
            )
        if len(reference_receipts) != expected_ordinal:
            raise ValueError(
                "lived-context durable reference cardinality changed"
            )
        if owner._encoded(episodes, actions) != encoded:
            raise ValueError("lived-context snapshot is not canonical")
        owner._episodes = episodes
        owner._action_records = actions
        owner._replay = replay
        return owner


__all__ = (
    "CausalThingLivedContextAdmission",
    "CausalThingLivedContextEpisode",
    "CausalThingLivedContextEvent",
    "CausalThingLivedContextOwner",
    "CausalThingLivedContextResourceProfile",
    "CommittedCausalThingLivedContextAdmissionUndo",
    "LivedBodyProvenance",
    "PreparedCausalThingLivedContextAdmission",
)
