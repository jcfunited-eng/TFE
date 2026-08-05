"""Exact presemantic temporal assemblies over authenticated auditory q events.

Local q cells are intentionally small peak-to-peak temporal relations.  A
sound-sized structure is the exact contextual conjunction of those cells
which survives every source-disjoint positive acoustic experience and no
explicit contrast.  It is not a single cell and not a whole isolated-window
firing set.

Each admitted exposure is converted to exact, time-ordered activation events.
Consecutive repetitions of the same q cell on the same cochlear component are
run-collapsed.  Learning retains only q event identities present in every
clean/noisy/overlap positive exposure and removes every identity present in an
explicit acoustic contrast.  Firing requires the entire resulting contextual
ensemble to cross the canonical integer ``n_eff < n/e`` L6 lock; the same law
selects cells whose positive-exposure recurrence has structurally locked while
their contrast recurrence has not.  Exact Allen relations between retained
cells remain authenticated structural evidence, but are not allowed to erase
a component merely because an additional room event changed cross-cell timing.
There is no LCS score, tuned tolerance, threshold, vote, probability,
transcript, word label, source identity, or scalar field.

Activation support roots link every event to the complete authenticated
D/M/R/U/C/P/B occurrence witnesses retained by the q/full-field authorities.
Those large witnesses are not duplicated across process IPC.  State here is
bounded, canonical, and HMAC authenticated.
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

from dsf_ai_service.substrate.auditory_live_motif import AuditoryLiveMotifResult
from dsf_ai_service.substrate.auditory_full_field_occurrence_validation import (
    validate_auditory_full_field_occurrence,
)
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)

TEMPORAL_ASSEMBLY_PROFILE_SCHEMA = (
    "guala.auditory.temporal_relation_assembly_profile.v1"
)
TEMPORAL_EXPOSURE_SCHEMA = (
    "guala.auditory.temporal_relation_exposure.v1"
)
TEMPORAL_ASSEMBLY_SCHEMA = (
    "guala.auditory.temporal_relation_assembly.v3"
)
TEMPORAL_STATE_SCHEMA = (
    "guala.auditory.temporal_relation_assembly_state.v3"
)
TEMPORAL_ENVELOPE_SCHEMA = (
    "guala.auditory.temporal_relation_assembly_hmac.v3"
)
_STATE_DOMAIN = b"guala-auditory-temporal-relation-state-v3\0"
_HEX = frozenset("0123456789abcdef")
AUDITORY_TEMPORAL_RELATION_STATE_MAX_BYTES = 128 * 1024 * 1024


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


def _sha(value: object, name: str) -> str:
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


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} must be an exact fraction")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} must be an exact fraction") from error
    if f"{result.numerator}/{result.denominator}" != value:
        raise ValueError(f"{name} is not canonical")
    return result


def _key(value: bytes | str) -> bytes:
    result = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(result, bytes) or not 32 <= len(result) <= 4_096:
        raise ValueError("temporal assembly authority key is invalid")
    return result


@dataclass(frozen=True, slots=True)
class AuditoryTemporalAssemblyProfile:
    profile_id: str
    max_exposures: int
    max_events_per_exposure: int
    max_assemblies: int
    max_relations_per_assembly: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_exposures: int,
        max_events_per_exposure: int,
        max_assemblies: int,
        max_relations_per_assembly: int,
        max_state_bytes: int,
    ) -> "AuditoryTemporalAssemblyProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
        ):
            raise ValueError("temporal assembly profile id is invalid")
        values = {
            "max_exposures": _positive(max_exposures, "exposure boundary"),
            "max_events_per_exposure": _positive(
                max_events_per_exposure, "event boundary"
            ),
            "max_assemblies": _positive(
                max_assemblies, "assembly boundary"
            ),
            "max_relations_per_assembly": _positive(
                max_relations_per_assembly, "relation boundary"
            ),
            "max_state_bytes": _positive(
                max_state_bytes, "state byte boundary"
            ),
        }
        payload = {
            **values,
            "profile_id": profile_id,
            "schema": TEMPORAL_ASSEMBLY_PROFILE_SCHEMA,
        }
        return cls(
            profile_id=profile_id,
            **values,
            authority_receipt_sha256=_digest(payload),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_assemblies": self.max_assemblies,
            "max_events_per_exposure": self.max_events_per_exposure,
            "max_exposures": self.max_exposures,
            "max_relations_per_assembly": (
                self.max_relations_per_assembly
            ),
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": TEMPORAL_ASSEMBLY_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        expected = type(self).create(
            profile_id=self.profile_id,
            max_exposures=self.max_exposures,
            max_events_per_exposure=self.max_events_per_exposure,
            max_assemblies=self.max_assemblies,
            max_relations_per_assembly=self.max_relations_per_assembly,
            max_state_bytes=self.max_state_bytes,
        )
        if expected != self:
            raise ValueError("temporal assembly profile authority changed")


@dataclass(frozen=True, slots=True, order=True)
class TemporalEventIdentity:
    neuron_id: str
    segment_index: int

    def verify(self) -> None:
        _sha(self.neuron_id, "temporal q neuron")
        if (
            isinstance(self.segment_index, bool)
            or not isinstance(self.segment_index, int)
            or not 0 <= self.segment_index < 32
        ):
            raise ValueError("temporal q segment left cochlear topology")

    def payload(self) -> list[object]:
        self.verify()
        return [self.neuron_id, self.segment_index]


@dataclass(frozen=True, slots=True)
class TemporalActivationEvent:
    identity: TemporalEventIdentity
    source_time_start: Fraction
    source_time_end: Fraction
    source_index_start: int
    source_index_end: int
    occurrence_count: int
    occurrence_supports: tuple[
        tuple[str, tuple[str, ...]], ...
    ]

    def verify(self) -> None:
        self.identity.verify()
        if (
            not isinstance(self.source_time_start, Fraction)
            or not isinstance(self.source_time_end, Fraction)
            or self.source_time_end <= self.source_time_start
            or isinstance(self.source_index_start, bool)
            or not isinstance(self.source_index_start, int)
            or isinstance(self.source_index_end, bool)
            or not isinstance(self.source_index_end, int)
            or self.source_index_start < 0
            or self.source_index_end < self.source_index_start
            or self.occurrence_count <= 0
            or not self.occurrence_supports
        ):
            raise ValueError("temporal q activation support changed")
        for root, receipts in self.occurrence_supports:
            _sha(root, "temporal occurrence support root")
            if not receipts:
                continue
            for value in receipts:
                _sha(value, "temporal occurrence receipt")
            expected = _digest({
                "ordered_full_field_occurrence_receipt_sha256s": list(
                    receipts
                ),
                "schema": "guala.auditory.activation_support_root.v1",
            })
            if expected != root:
                raise ValueError(
                    "temporal occurrence support root is unresolved"
                )

    def payload(self) -> dict[str, object]:
        self.verify()
        return {
            "identity": self.identity.payload(),
            "occurrence_count": self.occurrence_count,
            "occurrence_supports": [
                [root, list(receipts)]
                for root, receipts in self.occurrence_supports
            ],
            "source_index_end": self.source_index_end,
            "source_index_start": self.source_index_start,
            "source_time_end": (
                f"{self.source_time_end.numerator}/"
                f"{self.source_time_end.denominator}"
            ),
            "source_time_start": (
                f"{self.source_time_start.numerator}/"
                f"{self.source_time_start.denominator}"
            ),
        }


class ExactIntervalRelation(str, Enum):
    BEFORE = "before"
    MEETS = "meets"
    OVERLAPS = "overlaps"
    STARTS = "starts"
    DURING = "during"
    FINISHES = "finishes"
    EQUAL = "equal"
    AFTER = "after"
    MET_BY = "met_by"
    OVERLAPPED_BY = "overlapped_by"
    STARTED_BY = "started_by"
    CONTAINS = "contains"
    FINISHED_BY = "finished_by"


def _interval_relation(
    left: TemporalActivationEvent,
    right: TemporalActivationEvent,
) -> ExactIntervalRelation:
    a, b = left.source_time_start, left.source_time_end
    c, d = right.source_time_start, right.source_time_end
    if b < c:
        return ExactIntervalRelation.BEFORE
    if b == c:
        return ExactIntervalRelation.MEETS
    if a < c < b < d:
        return ExactIntervalRelation.OVERLAPS
    if a == c and b < d:
        return ExactIntervalRelation.STARTS
    if c < a and b < d:
        return ExactIntervalRelation.DURING
    if c < a and b == d:
        return ExactIntervalRelation.FINISHES
    if a == c and b == d:
        return ExactIntervalRelation.EQUAL
    if a > d:
        return ExactIntervalRelation.AFTER
    if a == d:
        return ExactIntervalRelation.MET_BY
    if c < a < d < b:
        return ExactIntervalRelation.OVERLAPPED_BY
    if a == c and b > d:
        return ExactIntervalRelation.STARTED_BY
    if a < c and d < b:
        return ExactIntervalRelation.CONTAINS
    if a < c and b == d:
        return ExactIntervalRelation.FINISHED_BY
    raise RuntimeError("exact interval relation is incomplete")


@dataclass(frozen=True, slots=True, order=True)
class TemporalEventRelation:
    left: TemporalEventIdentity
    relation: ExactIntervalRelation
    right: TemporalEventIdentity

    def payload(self) -> list[object]:
        return [
            self.left.payload(),
            self.relation.value,
            self.right.payload(),
        ]


@dataclass(frozen=True, slots=True)
class AuditoryTemporalExposure:
    exposure_receipt_sha256: str
    source_component_receipt_sha256s: tuple[str, ...]
    q_result_authority_receipt_sha256: str
    events: tuple[TemporalActivationEvent, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "events": [value.payload() for value in self.events],
            "exposure_receipt_sha256": self.exposure_receipt_sha256,
            "q_result_authority_receipt_sha256": (
                self.q_result_authority_receipt_sha256
            ),
            "schema": TEMPORAL_EXPOSURE_SCHEMA,
            "source_component_receipt_sha256s": list(
                self.source_component_receipt_sha256s
            ),
        }

    def verify(self) -> None:
        _sha(self.exposure_receipt_sha256, "temporal exposure")
        _sha(self.q_result_authority_receipt_sha256, "temporal q result")
        if (
            not self.source_component_receipt_sha256s
            or len(set(self.source_component_receipt_sha256s))
            != len(self.source_component_receipt_sha256s)
            or not self.events
        ):
            raise ValueError("temporal exposure support changed")
        for value in self.source_component_receipt_sha256s:
            _sha(value, "temporal source component")
        for value in self.events:
            value.verify()
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("temporal exposure authority changed")


@dataclass(frozen=True, slots=True)
class AuditoryTemporalAssembly:
    assembly_id: str
    positive_exposure_receipt_sha256s: tuple[str, ...]
    contrast_exposure_receipt_sha256s: tuple[str, ...]
    required_event_identities: tuple[TemporalEventIdentity, ...]
    identity_supports: tuple[
        tuple[TemporalEventIdentity, int, int], ...
    ]
    relations: tuple[TemporalEventRelation, ...]
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "assembly_id": self.assembly_id,
            "contrast_exposure_receipt_sha256s": list(
                self.contrast_exposure_receipt_sha256s
            ),
            "positive_exposure_receipt_sha256s": list(
                self.positive_exposure_receipt_sha256s
            ),
            "required_event_identities": [
                value.payload()
                for value in self.required_event_identities
            ],
            "identity_supports": [
                [identity.payload(), positive, contrast]
                for identity, positive, contrast
                in self.identity_supports
            ],
            "relations": [value.payload() for value in self.relations],
            "schema": TEMPORAL_ASSEMBLY_SCHEMA,
        }

    def verify(self) -> None:
        _sha(self.assembly_id, "temporal assembly")
        if (
            len(self.positive_exposure_receipt_sha256s) < 2
            or not self.contrast_exposure_receipt_sha256s
            or not self.required_event_identities
            or tuple(sorted(set(
                self.required_event_identities
            ))) != self.required_event_identities
            or tuple(
                value[0] for value in self.identity_supports
            ) != self.required_event_identities
            or tuple(sorted(set(self.relations))) != self.relations
        ):
            raise ValueError("temporal assembly structure changed")
        for value in self.required_event_identities:
            value.verify()
        for identity, positive, contrast in self.identity_supports:
            identity.verify()
            if (
                isinstance(positive, bool)
                or not isinstance(positive, int)
                or isinstance(contrast, bool)
                or not isinstance(contrast, int)
                or positive < 0
                or contrast < 0
                or not canonical_l6_direction(
                    dimensions=len(
                        self.positive_exposure_receipt_sha256s
                    ),
                    matching_non_null=positive,
                    matching_quiescent=0,
                ).locked
                or canonical_l6_direction(
                    dimensions=len(
                        self.contrast_exposure_receipt_sha256s
                    ),
                    matching_non_null=contrast,
                    matching_quiescent=0,
                ).locked
            ):
                raise ValueError(
                    "temporal assembly L6 support changed"
                )
        for value in (
            self.positive_exposure_receipt_sha256s
            + self.contrast_exposure_receipt_sha256s
        ):
            _sha(value, "temporal assembly exposure")
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError("temporal assembly authority changed")


class TemporalAssemblyFiringState(str, Enum):
    UNKNOWN = "unknown"
    OBSERVED = "observed"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class TemporalAssemblyFiring:
    state: TemporalAssemblyFiringState
    complete_assembly_ids: tuple[str, ...]
    source_exposure_receipt_sha256: str
    l6_directions: tuple[dict[str, object], ...] = ()

    def payload(self) -> dict[str, object]:
        return {
            "complete_assembly_ids": list(
                self.complete_assembly_ids
            ),
            "schema": (
                "guala.auditory.temporal_relation_firing.v2"
            ),
            "l6_directions": list(self.l6_directions),
            "source_exposure_receipt_sha256": (
                self.source_exposure_receipt_sha256
            ),
            "state": self.state.value,
        }


def _event_from_span(span: Mapping[str, object]) -> TemporalActivationEvent:
    expected = {
        "full_field_occurrence_count",
        "full_field_occurrence_receipt_root_sha256",
        "motif_neuron_id",
        "segment_index",
        "source_index_end",
        "source_index_start",
        "source_time_end",
        "source_time_start",
        "state_ordinal_end",
        "state_ordinal_start",
    }
    if set(span) != expected:
        raise ValueError("temporal activation span fields changed")
    event = TemporalActivationEvent(
        identity=TemporalEventIdentity(
            neuron_id=_sha(
                span["motif_neuron_id"], "temporal motif neuron"
            ),
            segment_index=int(span["segment_index"]),
        ),
        source_time_start=_fraction(
            span["source_time_start"], "temporal activation start"
        ),
        source_time_end=_fraction(
            span["source_time_end"], "temporal activation end"
        ),
        source_index_start=int(span["source_index_start"]),
        source_index_end=int(span["source_index_end"]),
        occurrence_count=int(span["full_field_occurrence_count"]),
        occurrence_supports=((
            _sha(
                span["full_field_occurrence_receipt_root_sha256"],
                "temporal occurrence support root",
            ),
            (),
        ),),
    )
    event.verify()
    return event


def _run_collapsed_events(
    spans: object,
) -> tuple[TemporalActivationEvent, ...]:
    if not isinstance(spans, list) or not spans:
        raise ValueError("temporal exposure has no activation spans")
    ordered = sorted(
        (_event_from_span(value) for value in spans),
        key=lambda value: (
            value.source_time_start,
            value.source_time_end,
            value.identity,
            value.source_index_start,
            value.source_index_end,
        ),
    )
    collapsed: list[TemporalActivationEvent] = []
    for event in ordered:
        if collapsed and collapsed[-1].identity == event.identity:
            prior = collapsed[-1]
            collapsed[-1] = TemporalActivationEvent(
                identity=prior.identity,
                source_time_start=min(
                    prior.source_time_start, event.source_time_start
                ),
                source_time_end=max(
                    prior.source_time_end, event.source_time_end
                ),
                source_index_start=min(
                    prior.source_index_start, event.source_index_start
                ),
                source_index_end=max(
                    prior.source_index_end, event.source_index_end
                ),
                occurrence_count=(
                    prior.occurrence_count + event.occurrence_count
                ),
                occurrence_supports=tuple(dict.fromkeys(
                    prior.occurrence_supports
                    + event.occurrence_supports
                )),
            )
        else:
            collapsed.append(event)
    return tuple(collapsed)


def _relation_set(
    events: tuple[TemporalActivationEvent, ...],
    *,
    maximum: int,
) -> set[TemporalEventRelation]:
    result: set[TemporalEventRelation] = set()
    for left_index, left in enumerate(events):
        for right in events[left_index + 1:]:
            if left.identity == right.identity:
                continue
            result.add(TemporalEventRelation(
                left=left.identity,
                relation=_interval_relation(left, right),
                right=right.identity,
            ))
            if len(result) > maximum:
                raise RuntimeError(
                    "temporal relation construction exceeded its boundary"
                )
    return result


def _has_relation(
    relation: TemporalEventRelation,
    by_identity: Mapping[
        TemporalEventIdentity,
        tuple[TemporalActivationEvent, ...],
    ],
) -> bool:
    return any(
        _interval_relation(left, right) is relation.relation
        for left in by_identity.get(relation.left, ())
        for right in by_identity.get(relation.right, ())
    )


class AuditoryTemporalRelationAssemblyOwner:
    """Bounded owner of exact presemantic acoustic temporal assemblies."""

    def __init__(
        self,
        *,
        profile: AuditoryTemporalAssemblyProfile,
        authority_key: bytes | str,
    ) -> None:
        profile.verify()
        self._profile = profile
        self._key = _key(authority_key)
        self._exposures: dict[str, AuditoryTemporalExposure] = {}
        self._assemblies: dict[str, AuditoryTemporalAssembly] = {}
        self._occurrence_registry: dict[str, dict[str, object]] = {}
        self._lock = threading.RLock()

    def observe(
        self,
        result_record: Mapping[str, object],
        *,
        source_component_receipt_sha256s: tuple[str, ...],
    ) -> AuditoryTemporalExposure:
        if not isinstance(result_record, Mapping):
            raise TypeError("temporal observation requires a q result record")
        record = dict(result_record)
        authority = _sha(
            record.pop("authority_receipt_sha256", None),
            "temporal q result",
        )
        if _digest(record) != authority:
            raise ValueError("temporal q result authority changed")
        source_exposure = _sha(
            record.get("source_experience_receipt_sha256"),
            "temporal source experience",
        )
        events = _run_collapsed_events(record.get("activation_spans"))
        if len(events) > self._profile.max_events_per_exposure:
            raise RuntimeError(
                "temporal exposure exceeded its event boundary"
            )
        draft = AuditoryTemporalExposure(
            exposure_receipt_sha256=source_exposure,
            source_component_receipt_sha256s=tuple(
                source_component_receipt_sha256s
            ),
            q_result_authority_receipt_sha256=authority,
            events=events,
            authority_receipt_sha256="0" * 64,
        )
        exposure = AuditoryTemporalExposure(
            exposure_receipt_sha256=draft.exposure_receipt_sha256,
            source_component_receipt_sha256s=(
                draft.source_component_receipt_sha256s
            ),
            q_result_authority_receipt_sha256=(
                draft.q_result_authority_receipt_sha256
            ),
            events=draft.events,
            authority_receipt_sha256=_digest(draft.payload()),
        )
        exposure.verify()
        with self._lock:
            existing = self._exposures.get(source_exposure)
            if existing is not None and existing != exposure:
                raise ValueError("temporal exposure receipt was reused")
            if (
                existing is None
                and len(self._exposures) >= self._profile.max_exposures
            ):
                raise RuntimeError(
                    "temporal exposure capacity exhausted"
                )
            self._exposures[source_exposure] = exposure
        return exposure

    def observe_typed(
        self,
        result: AuditoryLiveMotifResult,
        *,
        source_component_receipt_sha256s: tuple[str, ...],
    ) -> AuditoryTemporalExposure:
        """Admit full activation witnesses without crossing q-process IPC."""

        if not isinstance(result, AuditoryLiveMotifResult):
            raise TypeError(
                "typed temporal observation requires a live q result"
            )
        result.verify()
        events = []
        occurrence_records: dict[str, dict[str, object]] = {}
        for activation in result.internal_activations:
            receipts = []
            for occurrence in activation.full_field_occurrences:
                occurrence.verify()
                receipt = occurrence.authority_receipt_sha256
                record = occurrence.payload() | {
                    "authority_receipt_sha256": receipt,
                }
                validate_auditory_full_field_occurrence(record)
                prior = occurrence_records.get(receipt)
                if prior is not None and prior != record:
                    raise ValueError(
                        "temporal occurrence receipt was reused"
                    )
                occurrence_records[receipt] = record
                receipts.append(receipt)
            support_root = _digest({
                "ordered_full_field_occurrence_receipt_sha256s": receipts,
                "schema": "guala.auditory.activation_support_root.v1",
            })
            event = TemporalActivationEvent(
                identity=TemporalEventIdentity(
                    neuron_id=activation.neuron_id,
                    segment_index=activation.segment_index,
                ),
                source_time_start=activation.source_time_start,
                source_time_end=activation.source_time_end,
                source_index_start=activation.source_index_start,
                source_index_end=activation.source_index_end,
                occurrence_count=len(receipts),
                occurrence_supports=((
                    support_root,
                    tuple(receipts),
                ),),
            )
            event.verify()
            events.append(event)
        if not events:
            raise ValueError(
                "typed temporal exposure has no q activations"
            )
        ordered = sorted(
            events,
            key=lambda value: (
                value.source_time_start,
                value.source_time_end,
                value.identity,
                value.source_index_start,
                value.source_index_end,
            ),
        )
        collapsed = []
        for event in ordered:
            if collapsed and collapsed[-1].identity == event.identity:
                prior = collapsed[-1]
                collapsed[-1] = TemporalActivationEvent(
                    identity=prior.identity,
                    source_time_start=min(
                        prior.source_time_start,
                        event.source_time_start,
                    ),
                    source_time_end=max(
                        prior.source_time_end,
                        event.source_time_end,
                    ),
                    source_index_start=min(
                        prior.source_index_start,
                        event.source_index_start,
                    ),
                    source_index_end=max(
                        prior.source_index_end,
                        event.source_index_end,
                    ),
                    occurrence_count=(
                        prior.occurrence_count
                        + event.occurrence_count
                    ),
                    occurrence_supports=(
                        prior.occurrence_supports
                        + event.occurrence_supports
                    ),
                )
            else:
                collapsed.append(event)
        if len(collapsed) > self._profile.max_events_per_exposure:
            raise RuntimeError(
                "typed temporal exposure exceeded its event boundary"
            )
        draft = AuditoryTemporalExposure(
            exposure_receipt_sha256=(
                result.source_experience_receipt_sha256
            ),
            source_component_receipt_sha256s=tuple(
                source_component_receipt_sha256s
            ),
            q_result_authority_receipt_sha256=(
                result.authority_receipt_sha256
            ),
            events=tuple(collapsed),
            authority_receipt_sha256="0" * 64,
        )
        exposure = AuditoryTemporalExposure(
            exposure_receipt_sha256=draft.exposure_receipt_sha256,
            source_component_receipt_sha256s=(
                draft.source_component_receipt_sha256s
            ),
            q_result_authority_receipt_sha256=(
                draft.q_result_authority_receipt_sha256
            ),
            events=draft.events,
            authority_receipt_sha256=_digest(draft.payload()),
        )
        exposure.verify()
        with self._lock:
            existing = self._exposures.get(
                exposure.exposure_receipt_sha256
            )
            if existing is not None and existing != exposure:
                raise ValueError("typed temporal exposure was reused")
            if (
                existing is None
                and len(self._exposures) >= self._profile.max_exposures
            ):
                raise RuntimeError(
                    "temporal exposure capacity exhausted"
                )
            for receipt, record in occurrence_records.items():
                prior = self._occurrence_registry.get(receipt)
                if prior is not None and prior != record:
                    raise ValueError(
                        "temporal occurrence registry was reused"
                    )
                self._occurrence_registry[receipt] = record
            self._exposures[
                exposure.exposure_receipt_sha256
            ] = exposure
        return exposure

    def learn_acoustic_contrast(
        self,
        *,
        positive_exposure_receipt_sha256s: tuple[str, ...],
        contrast_exposure_receipt_sha256s: tuple[str, ...],
    ) -> AuditoryTemporalAssembly | None:
        positives = tuple(sorted(set(
            positive_exposure_receipt_sha256s
        )))
        contrasts = tuple(sorted(set(
            contrast_exposure_receipt_sha256s
        )))
        if (
            len(positives) < 2
            or not contrasts
            or set(positives).intersection(contrasts)
        ):
            raise ValueError(
                "temporal acoustic contrast support is incomplete"
            )
        with self._lock:
            positive_values = tuple(
                self._exposures[value] for value in positives
            )
            contrast_values = tuple(
                self._exposures[value] for value in contrasts
            )
            source_sets = tuple(
                set(value.source_component_receipt_sha256s)
                for value in positive_values
            )
            if any(
                left.intersection(right)
                for index, left in enumerate(source_sets)
                for right in source_sets[index + 1:]
            ):
                raise ValueError(
                    "temporal positives are not source-disjoint"
                )
            if any(
                not receipts
                for exposure in positive_values + contrast_values
                for event in exposure.events
                for _root, receipts in event.occurrence_supports
            ):
                raise ValueError(
                    "temporal learning lacks resolvable full-field witnesses"
                )
            positive_counts: dict[TemporalEventIdentity, int] = {}
            contrast_counts: dict[TemporalEventIdentity, int] = {}
            for exposure in positive_values:
                for identity in {
                    event.identity for event in exposure.events
                }:
                    positive_counts[identity] = (
                        positive_counts.get(identity, 0) + 1
                    )
            for exposure in contrast_values:
                for identity in {
                    event.identity for event in exposure.events
                }:
                    contrast_counts[identity] = (
                        contrast_counts.get(identity, 0) + 1
                    )
            required_identities = {
                identity
                for identity, positive_count
                in positive_counts.items()
                if (
                    canonical_l6_direction(
                        dimensions=len(positive_values),
                        matching_non_null=positive_count,
                        matching_quiescent=0,
                    ).locked
                    and not canonical_l6_direction(
                        dimensions=len(contrast_values),
                        matching_non_null=contrast_counts.get(
                            identity, 0
                        ),
                        matching_quiescent=0,
                    ).locked
                )
            }
            if not required_identities:
                return None
            candidates = _relation_set(
                positive_values[0].events,
                maximum=self._profile.max_relations_per_assembly,
            )
            for exposure in positive_values[1:]:
                by_identity: dict[
                    TemporalEventIdentity,
                    list[TemporalActivationEvent],
                ] = {}
                for event in exposure.events:
                    by_identity.setdefault(event.identity, []).append(event)
                mounted = {
                    key: tuple(values)
                    for key, values in by_identity.items()
                }
                candidates = {
                    relation for relation in candidates
                    if _has_relation(relation, mounted)
                }
            for exposure in contrast_values:
                by_identity = {}
                for event in exposure.events:
                    by_identity.setdefault(event.identity, []).append(event)
                mounted = {
                    key: tuple(values)
                    for key, values in by_identity.items()
                }
                candidates = {
                    relation for relation in candidates
                    if not _has_relation(relation, mounted)
                }
            relations = tuple(sorted(
                relation for relation in candidates
                if (
                    relation.left in required_identities
                    and relation.right in required_identities
                )
            ))
            required = tuple(sorted(required_identities))
            identity_supports = tuple(
                (
                    identity,
                    positive_counts[identity],
                    contrast_counts.get(identity, 0),
                )
                for identity in required
            )
            identity_payload = {
                "contrast_exposure_receipt_sha256s": list(contrasts),
                "positive_exposure_receipt_sha256s": list(positives),
                "required_event_identities": [
                    value.payload() for value in required
                ],
                "identity_supports": [
                    [identity.payload(), positive, contrast]
                    for identity, positive, contrast
                    in identity_supports
                ],
                "relations": [
                    value.payload() for value in relations
                ],
                "schema": TEMPORAL_ASSEMBLY_SCHEMA,
            }
            assembly_id = _digest(identity_payload)
            draft = AuditoryTemporalAssembly(
                assembly_id=assembly_id,
                positive_exposure_receipt_sha256s=positives,
                contrast_exposure_receipt_sha256s=contrasts,
                required_event_identities=required,
                identity_supports=identity_supports,
                relations=relations,
                authority_receipt_sha256="0" * 64,
            )
            assembly = AuditoryTemporalAssembly(
                assembly_id=draft.assembly_id,
                positive_exposure_receipt_sha256s=(
                    draft.positive_exposure_receipt_sha256s
                ),
                contrast_exposure_receipt_sha256s=(
                    draft.contrast_exposure_receipt_sha256s
                ),
                required_event_identities=(
                    draft.required_event_identities
                ),
                identity_supports=draft.identity_supports,
                relations=draft.relations,
                authority_receipt_sha256=_digest(draft.payload()),
            )
            assembly.verify()
            existing = self._assemblies.get(assembly_id)
            if existing is not None and existing != assembly:
                raise ValueError("temporal assembly identity was reused")
            if (
                existing is None
                and len(self._assemblies) >= self._profile.max_assemblies
            ):
                raise RuntimeError(
                    "temporal assembly capacity exhausted"
                )
            self._assemblies[assembly_id] = assembly
            return assembly

    def fire(
        self,
        result_record: Mapping[str, object],
    ) -> TemporalAssemblyFiring:
        source = _sha(
            result_record.get("source_experience_receipt_sha256"),
            "temporal firing source",
        )
        raw_spans = result_record.get("activation_spans")
        if raw_spans == []:
            return TemporalAssemblyFiring(
                state=TemporalAssemblyFiringState.UNKNOWN,
                complete_assembly_ids=(),
                source_exposure_receipt_sha256=source,
                l6_directions=(),
            )
        events = _run_collapsed_events(raw_spans)
        by_identity: dict[
            TemporalEventIdentity,
            list[TemporalActivationEvent],
        ] = {}
        for event in events:
            by_identity.setdefault(event.identity, []).append(event)
        mounted = {
            key: tuple(values)
            for key, values in by_identity.items()
        }
        with self._lock:
            directions = []
            complete_values = []
            for assembly_id, assembly in sorted(
                self._assemblies.items()
            ):
                matching = sum(
                    identity in mounted
                    for identity in (
                        assembly.required_event_identities
                    )
                )
                direction = canonical_l6_direction(
                    dimensions=len(
                        assembly.required_event_identities
                    ),
                    matching_non_null=matching,
                    matching_quiescent=0,
                )
                directions.append({
                    "assembly_id": assembly_id,
                    "dimensions": direction.dimensions,
                    "effective_dimensions": (
                        direction.effective_dimensions
                    ),
                    "knee": direction.knee,
                    "locked": direction.locked,
                    "matching_non_null": (
                        direction.matching_non_null
                    ),
                    "matching_quiescent": (
                        direction.matching_quiescent
                    ),
                })
                if direction.locked:
                    complete_values.append(assembly_id)
            complete = tuple(complete_values)
        state = (
            TemporalAssemblyFiringState.UNKNOWN
            if not complete
            else TemporalAssemblyFiringState.OBSERVED
            if len(complete) == 1
            else TemporalAssemblyFiringState.AMBIGUOUS
        )
        return TemporalAssemblyFiring(
            state=state,
            complete_assembly_ids=complete,
            source_exposure_receipt_sha256=source,
            l6_directions=tuple(directions),
        )

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            payload = {
                "assemblies": [
                    value.payload()
                    | {
                        "authority_receipt_sha256": (
                            value.authority_receipt_sha256
                        )
                    }
                    for value in sorted(
                        self._assemblies.values(),
                        key=lambda item: item.assembly_id,
                    )
                ],
                "exposures": [
                    value.payload()
                    | {
                        "authority_receipt_sha256": (
                            value.authority_receipt_sha256
                        )
                    }
                    for value in sorted(
                        self._exposures.values(),
                        key=lambda item: item.exposure_receipt_sha256,
                    )
                ],
                "profile": self._profile.payload()
                | {
                    "authority_receipt_sha256": (
                        self._profile.authority_receipt_sha256
                    )
                },
                "occurrence_registry": [
                    [receipt, record]
                    for receipt, record in sorted(
                        self._occurrence_registry.items()
                    )
                ],
                "schema": TEMPORAL_STATE_SCHEMA,
            }
            envelope = {
                "payload": payload,
                "schema": TEMPORAL_ENVELOPE_SCHEMA,
                "state_hmac_sha256": hmac.new(
                    self._key,
                    _STATE_DOMAIN + _canonical(payload),
                    hashlib.sha256,
                ).hexdigest(),
            }
            encoded = _canonical(envelope)
            if len(encoded) > self._profile.max_state_bytes:
                raise RuntimeError(
                    "temporal assembly state exceeded its byte boundary"
                )
            return encoded

    @classmethod
    def restore_encoded(
        cls,
        encoded: bytes,
        *,
        authority_key: bytes | str,
    ) -> "AuditoryTemporalRelationAssemblyOwner":
        key = _key(authority_key)
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("temporal assembly state is not bytes")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "temporal assembly state is unreadable"
            ) from error
        if _canonical(envelope) != encoded or set(envelope) != {
            "payload", "schema", "state_hmac_sha256"
        } or envelope["schema"] != TEMPORAL_ENVELOPE_SCHEMA:
            raise ValueError(
                "temporal assembly envelope changed"
            )
        payload = envelope["payload"]
        expected_hmac = hmac.new(
            key,
            _STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected_hmac,
            envelope["state_hmac_sha256"],
        ):
            raise ValueError(
                "temporal assembly state authority changed"
            )
        profile_record = dict(payload["profile"])
        profile = AuditoryTemporalAssemblyProfile(
            profile_id=profile_record["profile_id"],
            max_exposures=profile_record["max_exposures"],
            max_events_per_exposure=(
                profile_record["max_events_per_exposure"]
            ),
            max_assemblies=profile_record["max_assemblies"],
            max_relations_per_assembly=(
                profile_record["max_relations_per_assembly"]
            ),
            max_state_bytes=profile_record["max_state_bytes"],
            authority_receipt_sha256=profile_record[
                "authority_receipt_sha256"
            ],
        )
        profile.verify()
        if len(encoded) > profile.max_state_bytes:
            raise ValueError(
                "temporal assembly state exceeds its byte boundary"
            )
        owner = cls(profile=profile, authority_key=key)
        registry = {}
        for receipt, record in payload["occurrence_registry"]:
            _sha(receipt, "restored temporal occurrence")
            validate_auditory_full_field_occurrence(record)
            if record["authority_receipt_sha256"] != receipt:
                raise ValueError(
                    "restored temporal occurrence receipt changed"
                )
            registry[receipt] = record
        owner._occurrence_registry = registry

        def identity(value):
            result = TemporalEventIdentity(
                neuron_id=value[0],
                segment_index=value[1],
            )
            result.verify()
            return result

        def event(value):
            result = TemporalActivationEvent(
                identity=identity(value["identity"]),
                source_time_start=_fraction(
                    value["source_time_start"],
                    "restored temporal event start",
                ),
                source_time_end=_fraction(
                    value["source_time_end"],
                    "restored temporal event end",
                ),
                source_index_start=value["source_index_start"],
                source_index_end=value["source_index_end"],
                occurrence_count=value["occurrence_count"],
                occurrence_supports=tuple(
                    (
                        support[0],
                        tuple(support[1]),
                    )
                    for support in value["occurrence_supports"]
                ),
            )
            result.verify()
            for _root, receipts in result.occurrence_supports:
                if any(receipt not in registry for receipt in receipts):
                    raise ValueError(
                        "restored temporal support lost its occurrence"
                    )
            return result

        for value in payload["exposures"]:
            exposure = AuditoryTemporalExposure(
                exposure_receipt_sha256=value[
                    "exposure_receipt_sha256"
                ],
                source_component_receipt_sha256s=tuple(
                    value["source_component_receipt_sha256s"]
                ),
                q_result_authority_receipt_sha256=value[
                    "q_result_authority_receipt_sha256"
                ],
                events=tuple(event(item) for item in value["events"]),
                authority_receipt_sha256=value[
                    "authority_receipt_sha256"
                ],
            )
            exposure.verify()
            owner._exposures[
                exposure.exposure_receipt_sha256
            ] = exposure
        for value in payload["assemblies"]:
            relations = tuple(
                TemporalEventRelation(
                    left=identity(item[0]),
                    relation=ExactIntervalRelation(item[1]),
                    right=identity(item[2]),
                )
                for item in value["relations"]
            )
            assembly = AuditoryTemporalAssembly(
                assembly_id=value["assembly_id"],
                positive_exposure_receipt_sha256s=tuple(
                    value["positive_exposure_receipt_sha256s"]
                ),
                contrast_exposure_receipt_sha256s=tuple(
                    value["contrast_exposure_receipt_sha256s"]
                ),
                required_event_identities=tuple(
                    identity(item)
                    for item in value[
                        "required_event_identities"
                    ]
                ),
                identity_supports=tuple(
                    (
                        identity(item[0]),
                        item[1],
                        item[2],
                    )
                    for item in value["identity_supports"]
                ),
                relations=relations,
                authority_receipt_sha256=value[
                    "authority_receipt_sha256"
                ],
            )
            assembly.verify()
            if any(
                receipt not in owner._exposures
                for receipt in (
                    assembly.positive_exposure_receipt_sha256s
                    + assembly.contrast_exposure_receipt_sha256s
                )
            ):
                raise ValueError(
                    "restored temporal assembly lost an exposure"
                )
            owner._assemblies[assembly.assembly_id] = assembly
        if (
            len(owner._exposures) > profile.max_exposures
            or len(owner._assemblies) > profile.max_assemblies
            or any(
                len(value.relations)
                > profile.max_relations_per_assembly
                for value in owner._assemblies.values()
            )
            or owner.snapshot_encoded() != encoded
        ):
            raise ValueError(
                "restored temporal assembly state changed"
            )
        return owner

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "assembly_count": len(self._assemblies),
                "exposure_count": len(self._exposures),
                "relation_count": sum(
                    len(value.relations)
                    for value in self._assemblies.values()
                ),
                "required_event_identity_count": sum(
                    len(value.required_event_identities)
                    for value in self._assemblies.values()
                ),
                "schema": (
                    "guala.auditory.temporal_relation_status.v1"
                ),
            }


__all__ = (
    "AuditoryTemporalAssembly",
    "AuditoryTemporalAssemblyProfile",
    "AuditoryTemporalExposure",
    "AuditoryTemporalRelationAssemblyOwner",
    "ExactIntervalRelation",
    "TemporalAssemblyFiring",
    "TemporalAssemblyFiringState",
    "TemporalEventIdentity",
    "TemporalEventRelation",
)
