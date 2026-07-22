"""Bounded causal settlement over the verified six-sense full field.

This owner receives only a mounted ``SixSenseFullFieldBoundary`` whose native
topologies and exact canonical L0--L4 receipts already verify.  It preserves
the structured field, classifies only exact recurrence/change, and keeps chi
and capture source outside structural identity.  It retains no raw sensor data
and no lifetime settlement ledger.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    sha256_digest,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AuditoryRecognitionOccurrence,
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
)


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


SETTLEMENT_PROFILE_PAYLOAD = b"guala.exact_causal_experience.settlement.profile.v3"


@dataclass(frozen=True, slots=True)
class ExactFieldTuple:
    tuple_index: int
    fields: tuple[tuple[str, Fraction], ...]
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class ExactSubstreamInterpretation:
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]
    physical_quantity: str
    physical_unit: str
    profile_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    field_tuples: tuple[ExactFieldTuple, ...]


@dataclass(frozen=True, slots=True)
class ExactSenseInterpretation:
    sense: str
    state: str
    relation: str
    structural_fingerprint: str
    topology_receipt_sha256: str | None
    substreams: tuple[ExactSubstreamInterpretation, ...]
    boundary_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class ExactRecognizedLanguageEvent:
    """One terminal-recognized symbolic event; never its meaning authority."""

    form: str
    unicode_scalars: tuple[int, ...]
    source_event_id: str
    source_authority_receipt_sha256: str
    source_l5_authority_receipt_sha256: str
    recognition_occurrence: AuditoryRecognitionOccurrence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.form, str) or not self.form:
            raise ValueError("recognized language event requires a nonempty form")
        if (
            not isinstance(self.unicode_scalars, tuple)
            or not self.unicode_scalars
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                or value > 0x10FFFF
                or 0xD800 <= value <= 0xDFFF
                for value in self.unicode_scalars
            )
        ):
            raise ValueError("recognized language event has invalid Unicode scalars")
        if "".join(chr(value) for value in self.unicode_scalars) != self.form:
            raise ValueError("recognized language form differs from its scalar order")
        sha256_digest(self.source_event_id, "recognized language source event")
        sha256_digest(
            self.source_authority_receipt_sha256,
            "recognized language source authority",
        )
        sha256_digest(
            self.source_l5_authority_receipt_sha256,
            "recognized language source L5 authority",
        )
        if self.recognition_occurrence is not None:
            self.recognition_occurrence.verify()
            if (
                self.recognition_occurrence.kind
                is not AuditoryReciprocityKind.SPOKEN_FORM
                or self.recognition_occurrence.state
                is not AuditoryRecognitionState.UNIQUE
                or self.recognition_occurrence.l5_authority_receipt_sha256
                != self.source_l5_authority_receipt_sha256
            ):
                raise ValueError(
                    "recognized language occurrence lost auditory authority"
                )


@dataclass(frozen=True, slots=True)
class CausalExperienceSettlement:
    event_id: str
    structural_fingerprint: str
    assembly_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    interpretations: tuple[ExactSenseInterpretation, ...]
    language_events: tuple[ExactRecognizedLanguageEvent, ...]
    routing_chis: tuple[int, ...]
    source_tags: tuple[str, ...]
    assembly_receipt_sha256: str
    authority_receipt_sha256: str
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        payload = causal_experience_settlement_receipt_payload(
            event_id=self.event_id,
            structural_fingerprint=self.structural_fingerprint,
            assembly_id=self.assembly_id,
            source_time_start=self.source_time_start,
            source_time_end=self.source_time_end,
            interpretations=self.interpretations,
            language_events=self.language_events,
            routing_chis=self.routing_chis,
            source_tags=self.source_tags,
            assembly_receipt_sha256=self.assembly_receipt_sha256,
        )
        mounted = self.receipt_registry.resolve(
            self.authority_receipt_sha256,
            "causal experience settlement receipt",
        )
        if mounted != payload or receipt_sha256(payload) != self.authority_receipt_sha256:
            raise ReceiptError("causal experience settlement differs from mounted authority")


def causal_experience_settlement_receipt_payload(
    *,
    event_id: str,
    structural_fingerprint: str,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    interpretations: tuple[ExactSenseInterpretation, ...],
    language_events: tuple[ExactRecognizedLanguageEvent, ...],
    routing_chis: tuple[int, ...],
    source_tags: tuple[str, ...],
    assembly_receipt_sha256: str,
) -> bytes:
    """Canonical compact authority retained after the transient registry dies."""
    return _canonical_bytes({
        "assembly_id": assembly_id,
        "assembly_receipt_sha256": assembly_receipt_sha256,
        "event_id": event_id,
        "interpretations": [
            {
                "boundary_receipt_sha256": sense.boundary_receipt_sha256,
                "relation": sense.relation,
                "sense": sense.sense,
                "state": sense.state,
                "structural_fingerprint": sense.structural_fingerprint,
                "topology_receipt_sha256": sense.topology_receipt_sha256,
                "substreams": [
                    {
                        "coordinates": [list(value) for value in substream.coordinates],
                        "field_tuples": [
                            {
                                "authority_receipt_sha256": item.authority_receipt_sha256,
                                "fields": [
                                    [name, _fraction_text(value)]
                                    for name, value in item.fields
                                ],
                                "tuple_index": item.tuple_index,
                            }
                            for item in substream.field_tuples
                        ],
                        "kernel_basin_receipt_sha256": substream.kernel_basin_receipt_sha256,
                        "physical_quantity": substream.physical_quantity,
                        "physical_unit": substream.physical_unit,
                        "profile_receipt_sha256": substream.profile_receipt_sha256,
                        "sensor_id": substream.sensor_id,
                        "substream_id": substream.substream_id,
                        "topology_index": substream.topology_index,
                    }
                    for substream in sense.substreams
                ],
            }
            for sense in interpretations
        ],
        "language_events": [
            {
                "form": value.form,
                "source_authority_receipt_sha256": (
                    value.source_authority_receipt_sha256
                ),
                "source_event_id": value.source_event_id,
                "source_l5_authority_receipt_sha256": (
                    value.source_l5_authority_receipt_sha256
                ),
                "recognition_occurrence": (
                    value.recognition_occurrence.as_record()
                    if value.recognition_occurrence is not None else None
                ),
                "unicode_scalars": list(value.unicode_scalars),
            }
            for value in language_events
        ],
        "routing_chis": list(routing_chis),
        "schema": "guala.exact_causal_experience.settlement.v3",
        "source_tags": list(source_tags),
        "source_time_end": _fraction_text(source_time_end),
        "source_time_start": _fraction_text(source_time_start),
        "structural_fingerprint": structural_fingerprint,
    })


class ExactCausalExperienceOwner:
    """Serial, bounded structural relation owner for verified experiences."""

    def __init__(
        self,
        *,
        on_settlement: Callable[[CausalExperienceSettlement], None],
        log_event: Callable[..., None],
        max_transitions: int = 1024,
    ) -> None:
        if max_transitions <= 0:
            raise ValueError("max_transitions must be positive")
        self._on_settlement = on_settlement
        self._log_event = log_event
        self._max_transitions = int(max_transitions)
        self._lock = threading.RLock()
        self._previous_by_sense: dict[str, str] = {}
        self._transitions: OrderedDict[tuple[str, str, str], int] = OrderedDict()
        self._settled = 0

    @staticmethod
    def _exact_substream(value) -> ExactSubstreamInterpretation:
        tuples = tuple(
            ExactFieldTuple(
                tuple_index=item.tuple_index,
                fields=tuple(
                    (name, getattr(item, name)) for name in DSF_FIELD_ORDER),
                authority_receipt_sha256=item.authority_receipt_sha256,
            )
            for item in value.kernel_basin.exact_dsf_field_tuples
        )
        return ExactSubstreamInterpretation(
            sensor_id=value.profile.sensor_id,
            substream_id=value.profile.substream_id,
            topology_index=value.profile.topology_index,
            coordinates=tuple(
                (item.axis_id, item.coordinate_id)
                for item in value.profile.coordinates
            ),
            physical_quantity=value.profile.physical_quantity,
            physical_unit=value.profile.physical_unit,
            profile_receipt_sha256=value.profile.authority_receipt_sha256,
            kernel_basin_receipt_sha256=(
                value.kernel_basin.authority_receipt_sha256),
            field_tuples=tuples,
        )

    @staticmethod
    def _sense_fingerprint(
        state: str,
        substreams: tuple[ExactSubstreamInterpretation, ...],
    ) -> str:
        return _digest({
            "state": state,
            "substreams": [
                {
                    "substream_id": substream.substream_id,
                    "topology_index": substream.topology_index,
                    "coordinates": [list(value) for value in substream.coordinates],
                    "physical_quantity": substream.physical_quantity,
                    "physical_unit": substream.physical_unit,
                    "field_tuples": [
                        {
                            "tuple_index": item.tuple_index,
                            "fields": [
                                [name, _fraction_text(value)]
                                for name, value in item.fields
                            ],
                        }
                        for item in substream.field_tuples
                    ],
                }
                for substream in substreams
            ],
        })

    def settle(
        self,
        built: BuiltSixSenseFullField,
        *,
        recognized_language_record: dict[str, object] | None = None,
        routing_chis: tuple[int, ...],
        source_tags: tuple[str, ...],
    ) -> CausalExperienceSettlement:
        built.boundary.verify(built.receipt_registry)
        with self._lock:
            interpretations = []
            current_by_sense = {}
            for boundary in built.boundary.boundaries:
                substreams = tuple(
                    self._exact_substream(value)
                    for value in boundary.substreams
                )
                fingerprint = self._sense_fingerprint(
                    boundary.state.value, substreams)
                previous = self._previous_by_sense.get(boundary.sense.value)
                relation = (
                    "not_observed"
                    if boundary.state.value != "observed"
                    else "first_observation"
                    if previous is None
                    else "recurrence"
                    if previous == fingerprint
                    else "structural_change"
                )
                if boundary.state.value == "observed":
                    current_by_sense[boundary.sense.value] = fingerprint
                interpretations.append(ExactSenseInterpretation(
                    sense=boundary.sense.value,
                    state=boundary.state.value,
                    relation=relation,
                    structural_fingerprint=fingerprint,
                    topology_receipt_sha256=(
                        boundary.topology.authority_receipt_sha256
                        if boundary.topology is not None else None),
                    substreams=substreams,
                    boundary_receipt_sha256=(
                        boundary.authority_receipt_sha256),
                ))
            if tuple(item.sense for item in interpretations) != tuple(
                    sense.value for sense in SENSE_ORDER):
                raise RuntimeError("causal settlement lost six-sense order")
            language_events: tuple[ExactRecognizedLanguageEvent, ...] = ()
            if recognized_language_record is not None:
                from dsf_ai_service.substrate.auditory_incremental_terminal import (
                    AuditoryIncrementalTerminalEvent,
                )

                terminal = AuditoryIncrementalTerminalEvent.from_record(
                    dict(recognized_language_record)
                )
                language_events = (ExactRecognizedLanguageEvent(
                    form=terminal.tutor_label,
                    unicode_scalars=tuple(
                        ord(value) for value in terminal.tutor_label
                    ),
                    source_event_id=terminal.event_id,
                    source_authority_receipt_sha256=(
                        terminal.authority_receipt_sha256
                    ),
                    source_l5_authority_receipt_sha256=(
                        terminal.l5_authority_receipt_sha256
                    ),
                    recognition_occurrence=terminal.recognition_occurrence,
                ),)
            structural_fingerprint = _digest({
                "interpretations": {
                    item.sense: {
                        "state": item.state,
                        "structural_fingerprint": item.structural_fingerprint,
                    }
                    for item in interpretations
                },
                "language_events": [
                    {
                        "form": value.form,
                        "recognition_class_authority_receipt_sha256": (
                            value.recognition_occurrence
                            .selected_class_authority_receipt_sha256
                            if value.recognition_occurrence is not None
                            else None
                        ),
                        "unicode_scalars": list(value.unicode_scalars),
                    }
                    for value in language_events
                ],
            })
            event_id = _digest({
                "assembly_id": built.boundary.assembly_id,
                "authority_receipt_sha256": (
                    built.boundary.authority_receipt_sha256),
                "structural_fingerprint": structural_fingerprint,
            })
            routing = tuple(sorted(set(int(value) for value in routing_chis)))
            sources = tuple(sorted(set(str(value) for value in source_tags)))
            settlement_payload = causal_experience_settlement_receipt_payload(
                event_id=event_id,
                structural_fingerprint=structural_fingerprint,
                assembly_id=built.boundary.assembly_id,
                source_time_start=(
                    built.boundary.boundaries[0].source_time_start),
                source_time_end=built.boundary.boundaries[0].source_time_end,
                interpretations=tuple(interpretations),
                language_events=language_events,
                routing_chis=routing,
                source_tags=sources,
                assembly_receipt_sha256=built.boundary.authority_receipt_sha256,
            )
            settlement_registry = ReceiptRegistry.from_payloads(
                profile_payload=SETTLEMENT_PROFILE_PAYLOAD,
                receipt_payloads=(settlement_payload,),
            )
            settlement = CausalExperienceSettlement(
                event_id=event_id,
                structural_fingerprint=structural_fingerprint,
                assembly_id=built.boundary.assembly_id,
                source_time_start=(
                    built.boundary.boundaries[0].source_time_start),
                source_time_end=built.boundary.boundaries[0].source_time_end,
                interpretations=tuple(interpretations),
                language_events=language_events,
                routing_chis=routing,
                source_tags=sources,
                assembly_receipt_sha256=built.boundary.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(settlement_payload),
                receipt_registry=settlement_registry,
            )
            settlement.verify()
            self._on_settlement(settlement)
            for sense, current in current_by_sense.items():
                previous = self._previous_by_sense.get(sense)
                if previous is not None:
                    key = (sense, previous, current)
                    self._transitions[key] = self._transitions.get(key, 0) + 1
                    self._transitions.move_to_end(key)
                    while len(self._transitions) > self._max_transitions:
                        self._transitions.popitem(last=False)
                self._previous_by_sense[sense] = current
            self._settled += 1
            self._log_event(
                "causal_experience_settled",
                event_id=event_id,
                structural_fingerprint=structural_fingerprint,
                observed_senses=[
                    item.sense for item in interpretations
                    if item.state == "observed"
                ],
                recognized_language_events=len(language_events),
                unavailable_senses=[
                    item.sense for item in interpretations
                    if item.state == "sensor_unavailable"
                ],
                routing_candidate_count=len(settlement.routing_chis),
            )
            return settlement

    def status(self) -> dict:
        with self._lock:
            return {
                "settled": self._settled,
                "tracked_senses": sorted(self._previous_by_sense),
                "transition_relations": len(self._transitions),
                "transition_capacity": self._max_transitions,
            }


__all__ = (
    "CausalExperienceSettlement",
    "ExactCausalExperienceOwner",
    "ExactFieldTuple",
    "ExactRecognizedLanguageEvent",
    "ExactSenseInterpretation",
    "ExactSubstreamInterpretation",
    "causal_experience_settlement_receipt_payload",
)
