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
    require_fraction,
    require_identifier,
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


SETTLEMENT_PROFILE_PAYLOAD = b"guala.exact_causal_experience.settlement.profile.v4"
SETTLEMENT_SCHEMA = "guala.exact_causal_experience.settlement.v4"
SOURCE_EVIDENCE_STREAM_SCHEMA = "glew.provider.source_evidence_stream.v1"
SOURCE_SAMPLE_COMMITMENT_SCHEMA = (
    "guala.exact_causal_experience.source_samples.v1"
)
MAX_CAUSAL_RESERVATION_WAITERS = len(SENSE_ORDER)


def _exact_fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str):
        raise ReceiptError(f"{name} must be an exact fraction string")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ReceiptError(f"{name} is not an exact fraction") from exc
    if _fraction_text(result) != value:
        raise ReceiptError(f"{name} is not canonical")
    return result


def source_evidence_sample_commitment_sha256(
    samples: tuple[tuple[int, Fraction, Fraction, Fraction], ...],
) -> str:
    """Commit one ordered source grid without retaining its sample array."""
    if not isinstance(samples, tuple) or not samples:
        raise ReceiptError("source sample commitment requires immutable samples")
    previous_time: Fraction | None = None
    payload_samples = []
    for expected_index, sample in enumerate(samples):
        if not isinstance(sample, tuple) or len(sample) != 4:
            raise ReceiptError("source sample commitment changed shape")
        source_index, timestamp, signal, phase_turns = sample
        if (
            isinstance(source_index, bool)
            or not isinstance(source_index, int)
            or source_index != expected_index
        ):
            raise ReceiptError("source sample commitment indices are not contiguous")
        for value, name in (
            (timestamp, "timestamp"),
            (signal, "signal"),
            (phase_turns, "phase"),
        ):
            if not isinstance(value, Fraction):
                raise ReceiptError(
                    f"source sample commitment {name} is not exact"
                )
        if previous_time is not None and timestamp <= previous_time:
            raise ReceiptError("source sample commitment times are not causal")
        previous_time = timestamp
        payload_samples.append({
            "phase_turns": _fraction_text(phase_turns),
            "signal": _fraction_text(signal),
            "source_index": source_index,
            "timestamp": _fraction_text(timestamp),
        })
    return _digest({
        "samples": payload_samples,
        "schema": SOURCE_SAMPLE_COMMITMENT_SCHEMA,
    })


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
    source_evidence_stream_receipt_sha256: str
    source_sample_count: int
    source_sample_commitment_sha256: str
    kernel_basin_receipt_sha256: str
    field_tuples: tuple[ExactFieldTuple, ...]

    def __post_init__(self) -> None:
        for value, name in (
            (self.profile_receipt_sha256, "profile"),
            (
                self.source_evidence_stream_receipt_sha256,
                "source evidence stream",
            ),
            (self.source_sample_commitment_sha256, "source sample commitment"),
            (self.kernel_basin_receipt_sha256, "kernel basin"),
        ):
            sha256_digest(value, f"causal substream {name} receipt")
        if (
            isinstance(self.source_sample_count, bool)
            or not isinstance(self.source_sample_count, int)
            or self.source_sample_count <= 0
        ):
            raise ReceiptError("causal substream source sample count is invalid")

    def matches_source_claim(
        self,
        *,
        source_evidence_stream_receipt_sha256: str,
        samples: tuple[tuple[int, Fraction, Fraction, Fraction], ...],
    ) -> bool:
        """Compare an exact L5 sample claim across graph-local assemblies.

        The stream receipt remains authority for its own graph, but includes
        ``source_epoch`` and therefore cannot identify equal evidence across
        two assemblies.  Cross-graph equality rests only on the exact ordered
        sample commitment and cardinality.
        """
        sha256_digest(
            source_evidence_stream_receipt_sha256,
            "claimed source evidence stream receipt",
        )
        return (
            len(samples) == self.source_sample_count
            and source_evidence_sample_commitment_sha256(samples)
            == self.source_sample_commitment_sha256
        )


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


def _sense_structural_fingerprint(
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


def _settlement_structural_fingerprint(
    interpretations: tuple[ExactSenseInterpretation, ...],
    language_events: tuple[ExactRecognizedLanguageEvent, ...],
) -> str:
    return _digest({
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


def _validate_exact_substream(
    value: ExactSubstreamInterpretation,
    expected_topology_index: int,
) -> None:
    if not isinstance(value, ExactSubstreamInterpretation):
        raise ReceiptError("causal substream interpretation is not typed")
    value.__post_init__()
    for identifier, name in (
        (value.sensor_id, "sensor_id"),
        (value.substream_id, "substream_id"),
        (value.physical_quantity, "physical_quantity"),
        (value.physical_unit, "physical_unit"),
    ):
        require_identifier(identifier, f"causal substream {name}")
    if value.topology_index != expected_topology_index:
        raise ReceiptError(
            "causal substream topology is not complete and ordered"
        )
    if (
        not isinstance(value.coordinates, tuple)
        or not value.coordinates
        or any(
            not isinstance(coordinate, tuple)
            or len(coordinate) != 2
            for coordinate in value.coordinates
        )
    ):
        raise ReceiptError("causal substream coordinates are not canonical")
    axes = []
    for axis, coordinate in value.coordinates:
        require_identifier(axis, "causal substream coordinate axis")
        require_identifier(coordinate, "causal substream coordinate")
        axes.append(axis)
    if len(set(axes)) != len(axes):
        raise ReceiptError("causal substream coordinate axes are not unique")
    if (
        not isinstance(value.field_tuples, tuple)
        or not value.field_tuples
        or len(value.field_tuples) > value.source_sample_count
    ):
        raise ReceiptError("causal substream L4 tuple cardinality is invalid")
    for expected_tuple_index, field_tuple in enumerate(value.field_tuples):
        if not isinstance(field_tuple, ExactFieldTuple):
            raise ReceiptError("causal substream L4 field tuple is not typed")
        if field_tuple.tuple_index != expected_tuple_index:
            raise ReceiptError("causal substream L4 tuple indices are not contiguous")
        if (
            not isinstance(field_tuple.fields, tuple)
            or any(
                not isinstance(field, tuple) or len(field) != 2
                for field in field_tuple.fields
            )
            or tuple(name for name, _field in field_tuple.fields)
            != DSF_FIELD_ORDER
        ):
            raise ReceiptError("causal substream L4 field order changed")
        for _name, field in field_tuple.fields:
            require_fraction(field, "causal substream exact L4 field")
        sha256_digest(
            field_tuple.authority_receipt_sha256,
            "causal substream L4 tuple receipt",
        )


def _validate_exact_interpretations(
    interpretations: tuple[ExactSenseInterpretation, ...],
) -> None:
    expected_senses = tuple(sense.value for sense in SENSE_ORDER)
    if (
        not isinstance(interpretations, tuple)
        or len(interpretations) != len(expected_senses)
        or not all(
            isinstance(value, ExactSenseInterpretation)
            for value in interpretations
        )
    ):
        raise ReceiptError(
            "causal settlement must cover six senses in canonical order"
        )
    if tuple(value.sense for value in interpretations) != expected_senses:
        raise ReceiptError(
            "causal settlement must cover six senses in canonical order"
        )
    allowed_states = {"observed", "sensor_unavailable", "unknown"}
    observed_relations = {
        "first_observation",
        "recurrence",
        "structural_change",
    }
    for interpretation in interpretations:
        if interpretation.state not in allowed_states:
            raise ReceiptError("causal sense state is invalid")
        if interpretation.state == "observed":
            if (
                interpretation.relation not in observed_relations
                or interpretation.topology_receipt_sha256 is None
                or not interpretation.substreams
            ):
                raise ReceiptError("observed causal sense lost its full topology")
            sha256_digest(
                interpretation.topology_receipt_sha256,
                "causal sense topology receipt",
            )
        elif (
            interpretation.relation != "not_observed"
            or interpretation.topology_receipt_sha256 is not None
            or interpretation.substreams
        ):
            raise ReceiptError(
                "unobserved causal sense carries observed field structure"
            )
        sha256_digest(
            interpretation.boundary_receipt_sha256,
            "causal sense boundary receipt",
        )
        if not isinstance(interpretation.substreams, tuple):
            raise ReceiptError("causal sense substreams are not immutable")
        identities = []
        for topology_index, substream in enumerate(interpretation.substreams):
            _validate_exact_substream(substream, topology_index)
            identities.append((substream.sensor_id, substream.substream_id))
        if len(set(identities)) != len(identities) or len({
            value.substream_id for value in interpretation.substreams
        }) != len(interpretation.substreams):
            raise ReceiptError("causal sense topology repeats a substream")
        expected_fingerprint = _sense_structural_fingerprint(
            interpretation.state,
            interpretation.substreams,
        )
        if interpretation.structural_fingerprint != expected_fingerprint:
            raise ReceiptError("causal sense structural fingerprint changed")


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
        require_identifier(self.assembly_id, "causal settlement assembly_id")
        require_fraction(self.source_time_start, "causal settlement source start")
        require_fraction(self.source_time_end, "causal settlement source end")
        if self.source_time_end <= self.source_time_start:
            raise ReceiptError("causal settlement source interval is invalid")
        sha256_digest(self.assembly_receipt_sha256, "causal assembly receipt")
        sha256_digest(self.authority_receipt_sha256, "causal settlement receipt")
        _validate_exact_interpretations(self.interpretations)
        if (
            not isinstance(self.language_events, tuple)
            or len(self.language_events) > 1
            or not all(
                isinstance(value, ExactRecognizedLanguageEvent)
                for value in self.language_events
            )
        ):
            raise ReceiptError("causal settlement language events are not typed")
        for value in self.language_events:
            value.__post_init__()
        if (
            not isinstance(self.routing_chis, tuple)
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in self.routing_chis
            )
            or self.routing_chis != tuple(sorted(set(self.routing_chis)))
        ):
            raise ReceiptError("causal settlement routing chis are not canonical")
        if (
            not isinstance(self.source_tags, tuple)
            or any(
                not isinstance(value, str) for value in self.source_tags
            )
            or self.source_tags != tuple(sorted(set(self.source_tags)))
        ):
            raise ReceiptError("causal settlement source tags are not canonical")
        expected_structural_fingerprint = _settlement_structural_fingerprint(
            self.interpretations,
            self.language_events,
        )
        if self.structural_fingerprint != expected_structural_fingerprint:
            raise ReceiptError("causal settlement structural fingerprint changed")
        expected_event_id = _digest({
            "assembly_id": self.assembly_id,
            "authority_receipt_sha256": self.assembly_receipt_sha256,
            "structural_fingerprint": expected_structural_fingerprint,
        })
        if self.event_id != expected_event_id:
            raise ReceiptError("causal settlement event identity changed")
        if (
            self.receipt_registry.profile_binding_sha256
            != receipt_sha256(SETTLEMENT_PROFILE_PAYLOAD)
        ):
            raise ReceiptError("causal experience settlement profile changed")
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
                        "source_evidence_stream_receipt_sha256": (
                            substream.source_evidence_stream_receipt_sha256
                        ),
                        "source_sample_commitment_sha256": (
                            substream.source_sample_commitment_sha256
                        ),
                        "source_sample_count": substream.source_sample_count,
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
        "schema": SETTLEMENT_SCHEMA,
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
        self._reservation_condition = threading.Condition(self._lock)
        self._prepared_reservation: CausalExperienceSettlement | None = None
        self._reservation_waiters = 0
        self._previous_by_sense: dict[str, str] = {}
        self._transitions: OrderedDict[tuple[str, str, str], int] = OrderedDict()
        self._settled = 0

    @staticmethod
    def _source_commitment(
        built: BuiltSixSenseFullField,
        sense: str,
        value,
    ) -> tuple[str, int, str]:
        digest = value.profile.physical_derivation_receipt_sha256
        payload = built.receipt_registry.resolve(
            digest,
            "causal substream source evidence",
        )
        if receipt_sha256(payload) != digest:
            raise ReceiptError("causal substream source evidence digest changed")
        try:
            raw = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReceiptError(
                "causal substream source evidence is not canonical JSON"
            ) from exc
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != SOURCE_EVIDENCE_STREAM_SCHEMA
            or raw.get("lane_id") != sense
            or raw.get("port_id") != value.profile.substream_id
            or raw.get("port_kind") != value.profile.physical_quantity
            or raw.get("physical_unit") != value.profile.physical_unit
            or raw.get("source_epoch") != built.boundary.assembly_id
        ):
            raise ReceiptError(
                "causal substream source evidence belongs to another field"
            )
        raw_samples = raw.get("samples")
        if not isinstance(raw_samples, list) or not raw_samples:
            raise ReceiptError("causal substream source evidence is empty")
        samples = []
        for expected_index, sample in enumerate(raw_samples):
            if (
                not isinstance(sample, dict)
                or sample.get("source_index") != expected_index
                or sample.get("relevance") != "1/1"
            ):
                raise ReceiptError(
                    "causal substream source evidence changed sample order"
                )
            samples.append((
                expected_index,
                _exact_fraction(
                    sample.get("timestamp"),
                    "causal substream source timestamp",
                ),
                _exact_fraction(
                    sample.get("signal"),
                    "causal substream source signal",
                ),
                _exact_fraction(
                    sample.get("phase_turns"),
                    "causal substream source phase",
                ),
            ))
        sample_tuple = tuple(samples)
        return (
            digest,
            len(sample_tuple),
            source_evidence_sample_commitment_sha256(sample_tuple),
        )

    @classmethod
    def _exact_substream(
        cls,
        built: BuiltSixSenseFullField,
        sense: str,
        value,
    ) -> ExactSubstreamInterpretation:
        tuples = tuple(
            ExactFieldTuple(
                tuple_index=item.tuple_index,
                fields=tuple(
                    (name, getattr(item, name)) for name in DSF_FIELD_ORDER),
                authority_receipt_sha256=item.authority_receipt_sha256,
            )
            for item in value.kernel_basin.exact_dsf_field_tuples
        )
        source_digest, source_count, source_commitment = cls._source_commitment(
            built,
            sense,
            value,
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
            source_evidence_stream_receipt_sha256=source_digest,
            source_sample_count=source_count,
            source_sample_commitment_sha256=source_commitment,
            kernel_basin_receipt_sha256=(
                value.kernel_basin.authority_receipt_sha256),
            field_tuples=tuples,
        )

    @staticmethod
    def _sense_fingerprint(
        state: str,
        substreams: tuple[ExactSubstreamInterpretation, ...],
    ) -> str:
        return _sense_structural_fingerprint(state, substreams)

    def settle(
        self,
        built: BuiltSixSenseFullField,
        *,
        recognized_language_record: dict[str, object] | None = None,
        routing_chis: tuple[int, ...],
        source_tags: tuple[str, ...],
        commit: bool = True,
        reserve: bool = False,
    ) -> CausalExperienceSettlement:
        if not isinstance(commit, bool):
            raise TypeError("causal settlement commit flag must be boolean")
        if not isinstance(reserve, bool):
            raise TypeError("causal settlement reserve flag must be boolean")
        if reserve and commit:
            raise ValueError("causal settlement cannot reserve and commit together")
        built.boundary.verify(built.receipt_registry)
        with self._lock:
            if self._prepared_reservation is not None:
                if (
                    self._reservation_waiters
                    >= MAX_CAUSAL_RESERVATION_WAITERS
                ):
                    raise RuntimeError(
                        "causal settlement reservation waiter capacity is full"
                    )
                self._reservation_waiters += 1
                try:
                    while self._prepared_reservation is not None:
                        self._reservation_condition.wait()
                finally:
                    self._reservation_waiters -= 1
            interpretations = []
            current_by_sense = {}
            for boundary in built.boundary.boundaries:
                substreams = tuple(
                    self._exact_substream(
                        built,
                        boundary.sense.value,
                        value,
                    )
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
            structural_fingerprint = _settlement_structural_fingerprint(
                tuple(interpretations),
                language_events,
            )
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
            if commit:
                self._commit_prepared_locked(settlement)
            elif reserve:
                self._prepared_reservation = settlement
            return settlement

    def _commit_prepared_locked(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        current_by_sense = {
            item.sense: item.structural_fingerprint
            for item in settlement.interpretations
            if item.state == "observed"
        }
        for item in settlement.interpretations:
            previous = self._previous_by_sense.get(item.sense)
            expected_relation = (
                "not_observed"
                if item.state != "observed"
                else "first_observation"
                if previous is None
                else "recurrence"
                if previous == item.structural_fingerprint
                else "structural_change"
            )
            if item.relation != expected_relation:
                raise RuntimeError(
                    "prepared causal settlement state changed before commit"
                )
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
        try:
            self._log_event(
                "causal_experience_settled",
                event_id=settlement.event_id,
                structural_fingerprint=settlement.structural_fingerprint,
                observed_senses=[
                    item.sense for item in settlement.interpretations
                    if item.state == "observed"
                ],
                recognized_language_events=len(settlement.language_events),
                unavailable_senses=[
                    item.sense for item in settlement.interpretations
                    if item.state == "sensor_unavailable"
                ],
                routing_candidate_count=len(settlement.routing_chis),
            )
        except Exception:
            # Observation occurs after the authority commit and cannot reopen it.
            pass

    def commit_prepared(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Commit one verified settlement only if its prepared state is current."""
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("prepared causal settlement has the wrong type")
        settlement.verify()
        with self._lock:
            if self._prepared_reservation != settlement:
                raise ValueError(
                    "prepared causal settlement has no live reservation"
                )
            self._commit_prepared_locked(settlement)
            self._prepared_reservation = None
            self._reservation_condition.notify_all()

    def discard_prepared(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Release one uncommitted ordering reservation after intake failure."""
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("prepared causal settlement has the wrong type")
        settlement.verify()
        with self._lock:
            if self._prepared_reservation != settlement:
                raise ValueError(
                    "prepared causal settlement has no live reservation"
                )
            self._prepared_reservation = None
            self._reservation_condition.notify_all()

    def discard_prepared_for_source_event(self, source_event_id: str) -> bool:
        """Release only the reservation owned by one terminal source event."""
        sha256_digest(source_event_id, "prepared causal source event")
        with self._lock:
            prepared = self._prepared_reservation
            if prepared is None:
                return False
            if (
                len(prepared.language_events) != 1
                or prepared.language_events[0].source_event_id != source_event_id
            ):
                return False
            self._prepared_reservation = None
            self._reservation_condition.notify_all()
            return True

    def status(self) -> dict:
        with self._lock:
            return {
                "settled": self._settled,
                "tracked_senses": sorted(self._previous_by_sense),
                "transition_relations": len(self._transitions),
                "transition_capacity": self._max_transitions,
                "prepared_reservation": int(
                    self._prepared_reservation is not None
                ),
                "reservation_waiters": self._reservation_waiters,
                "reservation_waiter_capacity": (
                    MAX_CAUSAL_RESERVATION_WAITERS
                ),
            }


__all__ = (
    "CausalExperienceSettlement",
    "ExactCausalExperienceOwner",
    "ExactFieldTuple",
    "ExactRecognizedLanguageEvent",
    "ExactSenseInterpretation",
    "ExactSubstreamInterpretation",
    "MAX_CAUSAL_RESERVATION_WAITERS",
    "SETTLEMENT_SCHEMA",
    "causal_experience_settlement_receipt_payload",
    "source_evidence_sample_commitment_sha256",
)
