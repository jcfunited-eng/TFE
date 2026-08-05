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
import secrets
import threading
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
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
from dsf_ai_service.substrate.native_evidence_custody import (
    NativeEvidenceAdmissionCommitUndo,
    NativeEvidenceCustodyOwner,
    NativeEvidenceCustodyWitness,
    PreparedNativeEvidenceAdmission,
    VerifiedNativeEvidenceWitnessCapability,
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


def _field_texts(
    item: ExactFieldTuple,
    cache: dict[
        int,
        tuple[
            ExactFieldTuple,
            tuple[tuple[str, str], ...],
        ],
    ] | None,
) -> tuple[tuple[str, str], ...]:
    if cache is None:
        return tuple(
            (name, _fraction_text(value))
            for name, value in item.fields
        )
    key = id(item)
    mounted = cache.get(key)
    if mounted is not None:
        if mounted[0] is not item:
            raise RuntimeError(
                "causal field-text transaction identity changed"
            )
        return mounted[1]
    result = tuple(
        (name, _fraction_text(value))
        for name, value in item.fields
    )
    cache[key] = (item, result)
    return result


SETTLEMENT_PROFILE_PAYLOAD = b"guala.exact_causal_experience.settlement.profile.v7"
SETTLEMENT_SCHEMA = "guala.exact_causal_experience.settlement.v7"
SOURCE_EVIDENCE_STREAM_SCHEMA = "glew.provider.source_evidence_stream.v1"
SOURCE_SAMPLE_COMMITMENT_SCHEMA = (
    "guala.exact_causal_experience.source_samples.v2"
)
MAX_CAUSAL_RESERVATION_WAITERS = len(SENSE_ORDER)
_COMPLETE_L0_L4_TRACE_SCHEMAS = {
    "glew.provider.complete_signed_port_l0_l4_trace.v3",
    "glew.provider.complete_physical_port_l0_l4_trace.v4",
}


@dataclass(slots=True)
class _AtomicSequenceState:
    token: str
    owner_thread_id: int
    previous_by_sense: dict[str, str]
    transitions: OrderedDict[tuple[str, str, str], int]
    settled: int
    native_evidence_preparations: list[
        PreparedNativeEvidenceAdmission
    ]


@dataclass(frozen=True, slots=True)
class _AtomicSequenceCommitUndo:
    sequence: _AtomicSequenceState
    prior_previous_by_sense: tuple[tuple[str, str], ...]
    prior_transitions: tuple[tuple[tuple[str, str, str], int], ...]
    prior_settled: int
    native_evidence_undos: tuple[
        NativeEvidenceAdmissionCommitUndo,
        ...,
    ]


_ATOMIC_VISIBILITY_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class CausalAtomicVisibilityInstall:
    _sequence: _AtomicSequenceState
    _owner_authority: object
    _construction_authority: object


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
    samples: tuple[
        tuple[int, Fraction, Fraction, Fraction, Fraction],
        ...,
    ],
) -> str:
    """Commit one ordered source grid without retaining its sample array."""
    if not isinstance(samples, tuple) or not samples:
        raise ReceiptError("source sample commitment requires immutable samples")
    previous_time: Fraction | None = None
    payload_samples = []
    for expected_index, sample in enumerate(samples):
        if not isinstance(sample, tuple) or len(sample) != 5:
            raise ReceiptError("source sample commitment changed shape")
        source_index, timestamp, signal, relevance, phase_turns = sample
        if (
            isinstance(source_index, bool)
            or not isinstance(source_index, int)
            or source_index != expected_index
        ):
            raise ReceiptError("source sample commitment indices are not contiguous")
        for value, name in (
            (timestamp, "timestamp"),
            (signal, "signal"),
            (relevance, "relevance"),
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
            "relevance": _fraction_text(relevance),
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
    source_index_start: int
    source_index_end: int
    source_l0_l4_trace_receipt_sha256: str


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
    source_signal_commitment_sha256: str | None = None

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
        if self.source_signal_commitment_sha256 is not None:
            sha256_digest(
                self.source_signal_commitment_sha256,
                "causal substream source signal commitment",
            )
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
        samples: tuple[
            tuple[int, Fraction, Fraction, Fraction, Fraction],
            ...,
        ],
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
    *,
    _field_text_cache: dict[
        int,
        tuple[
            ExactFieldTuple,
            tuple[tuple[str, str], ...],
        ],
    ] | None = None,
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
                        "fields": _field_texts(
                            item,
                            _field_text_cache,
                        ),
                        "source_index_end": item.source_index_end,
                        "source_index_start": item.source_index_start,
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
        if (
            isinstance(field_tuple.source_index_start, bool)
            or not isinstance(field_tuple.source_index_start, int)
            or isinstance(field_tuple.source_index_end, bool)
            or not isinstance(field_tuple.source_index_end, int)
            or not 0
            <= field_tuple.source_index_start
            <= field_tuple.source_index_end
            < value.source_sample_count
        ):
            raise ReceiptError(
                "causal substream L4 tuple support left its source grid"
            )
        sha256_digest(
            field_tuple.source_l0_l4_trace_receipt_sha256,
            "causal substream L4 source trace receipt",
        )
        sha256_digest(
            field_tuple.authority_receipt_sha256,
            "causal substream L4 tuple receipt",
        )
    prior_end = -1
    source_traces = set()
    for field_tuple in value.field_tuples:
        if field_tuple.source_index_start != prior_end + 1:
            raise ReceiptError(
                "causal substream L4 support skipped a source interval"
            )
        prior_end = field_tuple.source_index_end
        source_traces.add(
            field_tuple.source_l0_l4_trace_receipt_sha256
        )
    if (
        prior_end != value.source_sample_count - 1
        or len(source_traces) != 1
    ):
        raise ReceiptError(
            "causal substream L4 support is incomplete or crosses traces"
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
    allowed_states = {"observed", "quiescent", "sensor_unavailable", "unknown"}
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
class _VerifiedSettlementIntegrity:
    event_id: str
    structural_fingerprint: str
    assembly_id: str
    source_time_start: Fraction
    source_time_end: Fraction
    interpretations: tuple[ExactSenseInterpretation, ...]
    language_events: tuple[ExactRecognizedLanguageEvent, ...]
    native_evidence_witness: NativeEvidenceCustodyWitness
    routing_chis: tuple[int, ...]
    source_tags: tuple[str, ...]
    assembly_receipt_sha256: str
    authority_receipt_sha256: str
    receipt_registry: ReceiptRegistry

    def matches(self, settlement: "CausalExperienceSettlement") -> bool:
        return (
            self.event_id == settlement.event_id
            and self.structural_fingerprint
            == settlement.structural_fingerprint
            and self.assembly_id == settlement.assembly_id
            and self.source_time_start == settlement.source_time_start
            and self.source_time_end == settlement.source_time_end
            and self.interpretations is settlement.interpretations
            and self.language_events is settlement.language_events
            and self.native_evidence_witness
            is settlement.native_evidence_witness
            and self.routing_chis is settlement.routing_chis
            and self.source_tags is settlement.source_tags
            and self.assembly_receipt_sha256
            == settlement.assembly_receipt_sha256
            and self.authority_receipt_sha256
            == settlement.authority_receipt_sha256
            and self.receipt_registry is settlement.receipt_registry
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
    native_evidence_witness: NativeEvidenceCustodyWitness
    routing_chis: tuple[int, ...]
    source_tags: tuple[str, ...]
    assembly_receipt_sha256: str
    authority_receipt_sha256: str
    receipt_registry: ReceiptRegistry
    _verified_integrity: _VerifiedSettlementIntegrity | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    _shared_full_field_roots: object | None = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def _retain_verified_integrity(self) -> None:
        object.__setattr__(
            self,
            "_verified_integrity",
            _VerifiedSettlementIntegrity(
                event_id=self.event_id,
                structural_fingerprint=self.structural_fingerprint,
                assembly_id=self.assembly_id,
                source_time_start=self.source_time_start,
                source_time_end=self.source_time_end,
                interpretations=self.interpretations,
                language_events=self.language_events,
                native_evidence_witness=self.native_evidence_witness,
                routing_chis=self.routing_chis,
                source_tags=self.source_tags,
                assembly_receipt_sha256=self.assembly_receipt_sha256,
                authority_receipt_sha256=self.authority_receipt_sha256,
                receipt_registry=self.receipt_registry,
            ),
        )

    def verify(self) -> None:
        verified = self._verified_integrity
        if verified is not None:
            if not verified.matches(self):
                raise ReceiptError(
                    "causal settlement changed after verified integrity"
                )
            return
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
        if not isinstance(
            self.native_evidence_witness,
            NativeEvidenceCustodyWitness,
        ):
            raise ReceiptError(
                "causal settlement native evidence witness is not typed"
            )
        self.native_evidence_witness.verify()
        native_registry = ReceiptRegistry(
            self.native_evidence_witness.original_profile_binding_sha256,
            self.native_evidence_witness.receipt_records,
        )
        witness_ports = {
            (
                value.sense,
                value.topology_index,
                value.substream_id,
            ): value
            for value in self.native_evidence_witness.ports
        }
        expected_port_keys = tuple(
            (
                sense.sense,
                substream.topology_index,
                substream.substream_id,
            )
            for sense in self.interpretations
            for substream in sense.substreams
        )
        if (
            len(witness_ports)
            != len(self.native_evidence_witness.ports)
            or set(witness_ports) != set(expected_port_keys)
        ):
            raise ReceiptError(
                "causal settlement native evidence topology changed"
            )
        for sense in self.interpretations:
            for substream in sense.substreams:
                witness = witness_ports[
                    (
                        sense.sense,
                        substream.topology_index,
                        substream.substream_id,
                    )
                ]
                trace_receipts = {
                    value.source_l0_l4_trace_receipt_sha256
                    for value in substream.field_tuples
                }
                if (
                    witness.sensor_id != substream.sensor_id
                    or witness.source_evidence_stream_receipt_sha256
                    != substream.source_evidence_stream_receipt_sha256
                    or witness.source_sample_count
                    != substream.source_sample_count
                    or trace_receipts
                    != {
                        witness.complete_l0_l4_trace_receipt_sha256
                    }
                    or len(witness.n_gates)
                    != len(substream.field_tuples)
                ):
                    raise ReceiptError(
                        "causal settlement native evidence linkage changed"
                    )
                native_registry.resolve(
                    substream.profile_receipt_sha256,
                    "native substream profile",
                )
                native_registry.resolve(
                    substream.kernel_basin_receipt_sha256,
                    "native substream kernel basin",
                )
                for item in substream.field_tuples:
                    native_registry.resolve(
                        item.authority_receipt_sha256,
                        "native exact L4 tuple",
                    )
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
            native_evidence_witness=self.native_evidence_witness,
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
        mounted_expected = {
            receipt_sha256(SETTLEMENT_PROFILE_PAYLOAD):
            SETTLEMENT_PROFILE_PAYLOAD,
            self.native_evidence_witness.authority_receipt_sha256:
            self.native_evidence_witness.authority_payload(),
            self.authority_receipt_sha256: payload,
        }
        for record in self.native_evidence_witness.receipt_records:
            existing = mounted_expected.get(record.digest)
            if existing is not None and existing != record.payload:
                raise ReceiptError(
                    "causal settlement receipt dependency collided"
                )
            mounted_expected[record.digest] = record.payload
        if len(self.receipt_registry.records) != len(mounted_expected):
            raise ReceiptError(
                "causal settlement receipt dependency custody changed"
            )
        for digest, expected in mounted_expected.items():
            if self.receipt_registry.resolve(
                digest,
                "causal settlement native dependency",
            ) != expected:
                raise ReceiptError(
                    "causal settlement native dependency changed"
                )
        self._retain_verified_integrity()


_VERIFIED_CAUSAL_TRANSACTION_AUTHORITY = object()


@dataclass(frozen=True, slots=True)
class VerifiedCausalSettlementCapability:
    """Request-local identity authority for one owner-held exact settlement."""

    settlement: CausalExperienceSettlement
    canonical_payload: bytes
    decoded_payload: dict[str, object]
    _construction_authority: object

    def verify_linkage(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        if (
            self._construction_authority
            is not _VERIFIED_CAUSAL_TRANSACTION_AUTHORITY
            or self.settlement is not settlement
            or receipt_sha256(self.canonical_payload)
            != settlement.authority_receipt_sha256
        ):
            raise ReceiptError(
                "verified causal settlement changed transaction identity"
            )


def causal_experience_settlement_receipt_payload(
    *,
    event_id: str,
    structural_fingerprint: str,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    interpretations: tuple[ExactSenseInterpretation, ...],
    language_events: tuple[ExactRecognizedLanguageEvent, ...],
    native_evidence_witness: NativeEvidenceCustodyWitness,
    routing_chis: tuple[int, ...],
    source_tags: tuple[str, ...],
    assembly_receipt_sha256: str,
    _field_text_cache: dict[
        int,
        tuple[
            ExactFieldTuple,
            tuple[tuple[str, str], ...],
        ],
    ] | None = None,
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
                                "fields": _field_texts(
                                    item,
                                    _field_text_cache,
                                ),
                                "source_index_end": (
                                    item.source_index_end
                                ),
                                "source_index_start": (
                                    item.source_index_start
                                ),
                                "source_l0_l4_trace_receipt_sha256": (
                                    item
                                    .source_l0_l4_trace_receipt_sha256
                                ),
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
                        **({
                            "source_signal_commitment_sha256": (
                                substream.source_signal_commitment_sha256
                            ),
                        } if (
                            substream.source_signal_commitment_sha256
                            is not None
                        ) else {}),
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
        "native_evidence_witness": native_evidence_witness.payload(),
        "routing_chis": list(routing_chis),
        "schema": SETTLEMENT_SCHEMA,
        "source_tags": list(source_tags),
        "source_time_end": _fraction_text(source_time_end),
        "source_time_start": _fraction_text(source_time_start),
        "structural_fingerprint": structural_fingerprint,
    })


def _verify_fresh_constructed_settlement(
    *,
    settlement: CausalExperienceSettlement,
    built: BuiltSixSenseFullField,
    interpretations: tuple[ExactSenseInterpretation, ...],
    language_events: tuple[ExactRecognizedLanguageEvent, ...],
    routing_chis: tuple[int, ...],
    source_tags: tuple[str, ...],
    settlement_payload: bytes,
    native_evidence_capability: (
        VerifiedNativeEvidenceWitnessCapability
    ),
) -> None:
    """Authenticate one complete settlement while its construction is live."""
    built.verify_construction()
    native_evidence_capability.verify_linkage(
        settlement.native_evidence_witness
    )
    boundary = built.boundary
    if (
        settlement.interpretations is not interpretations
        or settlement.language_events is not language_events
        or not isinstance(
            settlement.native_evidence_witness,
            NativeEvidenceCustodyWitness,
        )
        or settlement.routing_chis is not routing_chis
        or settlement.source_tags is not source_tags
        or settlement.assembly_id != boundary.assembly_id
        or settlement.source_time_start
        != boundary.boundaries[0].source_time_start
        or settlement.source_time_end
        != boundary.boundaries[0].source_time_end
        or settlement.assembly_receipt_sha256
        != boundary.authority_receipt_sha256
        or settlement.receipt_registry.profile_binding_sha256
        != receipt_sha256(SETTLEMENT_PROFILE_PAYLOAD)
        or settlement.authority_receipt_sha256
        != receipt_sha256(settlement_payload)
        or settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "fresh causal experience settlement receipt",
        )
        != settlement_payload
        or settlement.native_evidence_witness.receipt_records
        is not built.receipt_registry.records
    ):
        raise ReceiptError(
            "fresh causal settlement left its verified construction"
        )
    native_evidence_capability.retain_verified_integrity(
        settlement.native_evidence_witness
    )
    settlement._retain_verified_integrity()


class ExactCausalExperienceOwner:
    """Serial, bounded structural relation owner for verified experiences."""

    def __init__(
        self,
        *,
        on_settlement: Callable[[CausalExperienceSettlement], None],
        log_event: Callable[..., None],
        max_transitions: int = 1024,
        native_evidence_custody: NativeEvidenceCustodyOwner | None = None,
    ) -> None:
        if max_transitions <= 0:
            raise ValueError("max_transitions must be positive")
        self._on_settlement = on_settlement
        self._log_event = log_event
        self._max_transitions = int(max_transitions)
        if (
            native_evidence_custody is not None
            and not isinstance(
                native_evidence_custody,
                NativeEvidenceCustodyOwner,
            )
        ):
            raise TypeError(
                "causal owner native evidence custody is not typed"
            )
        self._native_evidence_custody = (
            native_evidence_custody
            if native_evidence_custody is not None
            else NativeEvidenceCustodyOwner()
        )
        self._lock = threading.RLock()
        self._reservation_condition = threading.Condition(self._lock)
        self._prepared_reservation: CausalExperienceSettlement | None = None
        self._prepared_native_evidence_reservation: (
            PreparedNativeEvidenceAdmission | None
        ) = None
        self._reservation_waiters = 0
        self._previous_by_sense: dict[str, str] = {}
        self._transitions: OrderedDict[tuple[str, str, str], int] = OrderedDict()
        self._settled = 0
        self._atomic_sequence: _AtomicSequenceState | None = None
        self._active_verified_settlement: CausalExperienceSettlement | None = None
        self._active_verified_thread_id: int | None = None
        self._visibility_install: CausalAtomicVisibilityInstall | None = None
        self._visibility_rollback: _AtomicSequenceCommitUndo | None = None
        self._visibility_owner_authority = object()

    def _require_public_visibility_locked(self) -> None:
        if (
            self._visibility_install is not None
            or self._visibility_rollback is not None
        ):
            raise RuntimeError(
                "causal sensory visibility transaction is in progress"
            )

    def _require_sequence_owner_locked(self) -> None:
        self._require_public_visibility_locked()
        sequence = self._atomic_sequence
        if (
            sequence is not None
            and sequence.owner_thread_id != threading.get_ident()
        ):
            raise RuntimeError(
                "causal owner is reserved by an atomic sensory sequence"
            )

    def begin_atomic_sequence(self) -> str:
        """Reserve rollback authority for one same-thread sensory sequence."""
        with self._lock:
            self._require_public_visibility_locked()
            if self._prepared_reservation is not None:
                raise RuntimeError(
                    "causal owner has a prepared settlement"
                )
            if self._atomic_sequence is not None:
                raise RuntimeError(
                    "causal owner already has an atomic sensory sequence"
                )
            token = secrets.token_urlsafe(24)
            self._atomic_sequence = _AtomicSequenceState(
                token=token,
                owner_thread_id=threading.get_ident(),
                previous_by_sense=dict(self._previous_by_sense),
                transitions=OrderedDict(self._transitions),
                settled=self._settled,
                native_evidence_preparations=[],
            )
            return token

    def verify_atomic_sequence(self, token: str) -> None:
        with self._lock:
            self._require_public_visibility_locked()
            sequence = self._atomic_sequence
            if (
                sequence is None
                or sequence.token != token
                or sequence.owner_thread_id != threading.get_ident()
                or self._prepared_reservation is not None
            ):
                raise ValueError("causal atomic sensory sequence changed")

    def preverify_atomic_visibility_install(
        self,
        token: str,
    ) -> CausalAtomicVisibilityInstall:
        """Preverify the exact state references installed after world commit."""

        with self._lock:
            self.verify_atomic_sequence(token)
            sequence = self._atomic_sequence
            if sequence is None:
                raise RuntimeError(
                    "causal atomic sensory sequence disappeared"
                )
            return CausalAtomicVisibilityInstall(
                _sequence=sequence,
                _owner_authority=self._visibility_owner_authority,
                _construction_authority=(
                    _ATOMIC_VISIBILITY_AUTHORITY
                ),
            )

    def _commit_native_preparations_locked(
        self,
        preparations: list[PreparedNativeEvidenceAdmission],
    ) -> tuple[NativeEvidenceAdmissionCommitUndo, ...]:
        undos: list[NativeEvidenceAdmissionCommitUndo] = []
        try:
            for prepared in preparations:
                undos.append(
                    self._native_evidence_custody
                    .commit_prepared_admission(prepared)
                )
        except BaseException:
            for undo in reversed(undos):
                (
                    self._native_evidence_custody
                    .rollback_committed_admission(undo)
                )
            raise
        return tuple(undos)

    def _rollback_native_undos_locked(
        self,
        undos: tuple[NativeEvidenceAdmissionCommitUndo, ...],
    ) -> None:
        for undo in reversed(undos):
            (
                self._native_evidence_custody
                .rollback_committed_admission(undo)
            )

    def _discard_native_preparations_locked(
        self,
        preparations: list[PreparedNativeEvidenceAdmission],
    ) -> None:
        for prepared in reversed(preparations):
            (
                self._native_evidence_custody
                .discard_prepared_admission(prepared)
            )

    @contextmanager
    def atomic_visibility_transaction(
        self,
        install: CausalAtomicVisibilityInstall,
    ):
        """Hide the old/new boundary until a preverified install completes."""

        with self._lock:
            self._require_public_visibility_locked()
            if (
                not isinstance(install, CausalAtomicVisibilityInstall)
                or install._construction_authority
                is not _ATOMIC_VISIBILITY_AUTHORITY
                or install._owner_authority
                is not self._visibility_owner_authority
                or self._visibility_install is not None
                or self._atomic_sequence is not install._sequence
                or install._sequence.owner_thread_id
                != threading.get_ident()
            ):
                raise ValueError(
                    "causal visibility install changed custody"
                )
            self._visibility_install = install
            installed = [False]

            def install_now() -> _AtomicSequenceCommitUndo:
                assert self._visibility_install is install
                assert not installed[0]
                sequence = install._sequence
                native_undos = (
                    self._commit_native_preparations_locked(
                        sequence.native_evidence_preparations
                    )
                )
                undo = _AtomicSequenceCommitUndo(
                    sequence=sequence,
                    prior_previous_by_sense=tuple(
                        self._previous_by_sense.items()
                    ),
                    prior_transitions=tuple(self._transitions.items()),
                    prior_settled=self._settled,
                    native_evidence_undos=native_undos,
                )
                self._previous_by_sense = sequence.previous_by_sense
                self._transitions = sequence.transitions
                self._settled = sequence.settled
                self._atomic_sequence = None
                installed[0] = True
                return undo

            try:
                yield install_now
            finally:
                self._visibility_install = None

    @contextmanager
    def committed_atomic_sequence_rollback_transaction(
        self,
        undo: _AtomicSequenceCommitUndo,
    ):
        """Hold public visibility while one current committed tail is undone."""

        with self._lock:
            self._require_public_visibility_locked()
            if (
                not isinstance(undo, _AtomicSequenceCommitUndo)
                or self._atomic_sequence is not None
                or self._previous_by_sense
                != undo.sequence.previous_by_sense
                or self._transitions != undo.sequence.transitions
                or self._settled != undo.sequence.settled
            ):
                raise ValueError("causal published atomic sequence changed")
            rolled_back = [False]
            self._visibility_rollback = undo

            def rollback_now() -> None:
                assert not rolled_back[0]
                self._rollback_native_undos_locked(
                    undo.native_evidence_undos
                )
                self._discard_native_preparations_locked(
                    undo.sequence.native_evidence_preparations
                )
                self._previous_by_sense = dict(
                    undo.prior_previous_by_sense
                )
                self._transitions = OrderedDict(
                    undo.prior_transitions
                )
                self._settled = undo.prior_settled
                rolled_back[0] = True

            try:
                yield rollback_now
            finally:
                self._visibility_rollback = None

    def commit_atomic_sequence(self, token: str) -> _AtomicSequenceCommitUndo:
        """Publish sequence state without replaying per-block callbacks."""
        with self._lock:
            self.verify_atomic_sequence(token)
            sequence = self._atomic_sequence
            if sequence is None:
                raise RuntimeError("causal atomic sensory sequence disappeared")
            undo = _AtomicSequenceCommitUndo(
                sequence=sequence,
                prior_previous_by_sense=tuple(
                    self._previous_by_sense.items()
                ),
                prior_transitions=tuple(self._transitions.items()),
                prior_settled=self._settled,
                native_evidence_undos=(
                    self._commit_native_preparations_locked(
                        sequence.native_evidence_preparations
                    )
                ),
            )
            self._previous_by_sense = sequence.previous_by_sense
            self._transitions = sequence.transitions
            self._settled = sequence.settled
            self._atomic_sequence = None
            return undo

    def rollback_committed_atomic_sequence(
        self,
        undo: _AtomicSequenceCommitUndo,
    ) -> None:
        with self._lock:
            self._require_public_visibility_locked()
            if (
                not isinstance(undo, _AtomicSequenceCommitUndo)
                or self._atomic_sequence is not None
                or self._previous_by_sense != undo.sequence.previous_by_sense
                or self._transitions != undo.sequence.transitions
                or self._settled != undo.sequence.settled
            ):
                raise ValueError("causal published atomic sequence changed")
            self._rollback_native_undos_locked(
                undo.native_evidence_undos
            )
            self._previous_by_sense = dict(undo.prior_previous_by_sense)
            self._transitions = OrderedDict(undo.prior_transitions)
            self._settled = undo.prior_settled
            self._atomic_sequence = undo.sequence

    def rollback_atomic_sequence(self, token: str) -> None:
        """Restore the exact pre-sequence relation state."""
        with self._lock:
            self._require_public_visibility_locked()
            sequence = self._atomic_sequence
            if (
                sequence is None
                or sequence.token != token
                or sequence.owner_thread_id != threading.get_ident()
                or self._prepared_reservation is not None
            ):
                raise ValueError("causal atomic sensory sequence changed")
            self._discard_native_preparations_locked(
                sequence.native_evidence_preparations
            )
            self._atomic_sequence = None

    @staticmethod
    def _source_commitment(
        built: BuiltSixSenseFullField,
        sense: str,
        value,
    ) -> tuple[str, int, str]:
        digest = value.profile.physical_derivation_receipt_sha256
        if (
            value.profile.sense.value != sense
            or not value.profile.substream_id
            or not value.profile.physical_quantity
            or not value.profile.physical_unit
        ):
            raise ReceiptError(
                "causal substream source evidence belongs to another field"
            )
        if built.has_transaction_construction_authority:
            sample_count, commitment = built.source_sample_commitment(digest)
            return digest, sample_count, commitment
        payload = built.receipt_registry.resolve(
            digest,
            "causal substream source evidence",
        )
        if receipt_sha256(payload) != digest:
            raise ReceiptError(
                "causal substream source evidence digest changed"
            )
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
            raise ReceiptError(
                "causal substream source evidence is empty"
            )
        samples = []
        for expected_index, sample in enumerate(raw_samples):
            if (
                not isinstance(sample, dict)
                or sample.get("source_index") != expected_index
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
                    sample.get("relevance"),
                    "causal substream source relevance",
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

    @staticmethod
    def _source_signal_commitment(
        built: BuiltSixSenseFullField,
        source_digest: str,
        source_count: int,
    ) -> str:
        """Commit exact amplitudes without observation time or phase."""

        payload = built.receipt_registry.resolve(
            source_digest,
            "causal substream source signal evidence",
        )
        try:
            source = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReceiptError(
                "causal substream source signal evidence is unreadable"
            ) from error
        samples = source.get("samples") if isinstance(source, dict) else None
        if (
            not isinstance(samples, list)
            or len(samples) != source_count
            or any(
                not isinstance(sample, dict)
                or sample.get("source_index") != index
                or not isinstance(sample.get("signal"), str)
                for index, sample in enumerate(samples)
            )
        ):
            raise ReceiptError(
                "causal substream source signal evidence changed"
            )
        return _digest({
            "signals": [sample["signal"] for sample in samples],
        })

    @staticmethod
    def _exact_tuple_support(
        built: BuiltSixSenseFullField,
        sense: str,
        value,
        source_count: int,
    ) -> tuple[str, tuple[tuple[int, int], ...]]:
        exact_tuples = value.kernel_basin.exact_dsf_field_tuples
        if not exact_tuples:
            raise ReceiptError(
                "causal substream has no exact L4 tuples"
            )
        trace_digests = {
            item.source_l0_l4_trace_receipt_sha256
            for item in exact_tuples
        }
        if len(trace_digests) != 1:
            raise ReceiptError(
                "causal substream L4 tuples cross source traces"
            )
        trace_digest = next(iter(trace_digests))
        if built.has_transaction_construction_authority:
            intervals = built.source_l0_l4_support(
                trace_receipt_sha256=trace_digest,
                sense=sense,
                substream_id=value.profile.substream_id,
                source_count=source_count,
            )
            if (
                len(intervals) != len(exact_tuples)
                or any(
                    start != prior_end + 1
                    for prior_end, (start, _end) in zip(
                        (-1, *(
                            end
                            for _start, end in intervals[:-1]
                        )),
                        intervals,
                        strict=True,
                    )
                )
                or intervals[-1][1] != source_count - 1
            ):
                raise ReceiptError(
                    "causal substream construction support changed"
                )
            return trace_digest, intervals
        payload = built.receipt_registry.resolve(
            trace_digest,
            "causal substream complete L0-L4 trace",
        )
        if receipt_sha256(payload) != trace_digest:
            raise ReceiptError(
                "causal substream L0-L4 trace digest changed"
            )
        try:
            trace = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReceiptError(
                "causal substream L0-L4 trace is not canonical JSON"
            ) from error
        if (
            not isinstance(trace, dict)
            or trace.get("schema")
            not in _COMPLETE_L0_L4_TRACE_SCHEMAS
            or trace.get("lane_id") != sense
            or trace.get("port_id") != value.profile.substream_id
            or _canonical_bytes(trace) != payload
        ):
            raise ReceiptError(
                "causal substream L0-L4 trace belongs to another port"
            )
        layer_intervals = []
        for layer_name in (
            "L1_GateL1State",
            "L2_GateInterpretation",
            "L3_ResonanceResult",
        ):
            layer = trace.get(layer_name)
            if (
                not isinstance(layer, list)
                or len(layer) != len(exact_tuples)
            ):
                raise ReceiptError(
                    "causal substream L0-L4 gate layer is incomplete"
                )
            intervals = []
            for row in layer:
                if not isinstance(row, dict):
                    raise ReceiptError(
                        "causal substream L0-L4 gate changed shape"
                    )
                start = row.get("start_idx")
                end = row.get("end_idx")
                if (
                    isinstance(start, bool)
                    or not isinstance(start, int)
                    or isinstance(end, bool)
                    or not isinstance(end, int)
                    or not 0 <= start <= end < source_count
                ):
                    raise ReceiptError(
                        "causal substream L4 support left its source grid"
                    )
                intervals.append((start, end))
            layer_intervals.append(tuple(intervals))
        if len(set(layer_intervals)) != 1:
            raise ReceiptError(
                "causal substream L1-L3 gate supports diverged"
            )
        intervals = layer_intervals[0]
        l4 = trace.get("L4_DSF")
        if not isinstance(l4, list) or len(l4) != len(exact_tuples):
            raise ReceiptError(
                "causal substream trace lost its L4 field"
            )
        prior_end = -1
        for item, row, interval in zip(
            exact_tuples,
            l4,
            intervals,
            strict=True,
        ):
            if (
                interval[0] != prior_end + 1
                or not isinstance(row, dict)
                or set(row) != set(DSF_FIELD_ORDER)
                or tuple(
                    _exact_fraction(
                        row.get(name),
                        f"causal substream trace {name}",
                    )
                    for name in DSF_FIELD_ORDER
                )
                != item.as_tuple()
            ):
                raise ReceiptError(
                    "causal substream trace differs from its exact L4 field"
                )
            prior_end = interval[1]
        if prior_end != source_count - 1:
            raise ReceiptError(
                "causal substream L4 support did not close its source grid"
            )
        return trace_digest, intervals

    @classmethod
    def _exact_substream(
        cls,
        built: BuiltSixSenseFullField,
        sense: str,
        value,
    ) -> ExactSubstreamInterpretation:
        source_digest, source_count, source_commitment = cls._source_commitment(
            built,
            sense,
            value,
        )
        trace_digest, intervals = cls._exact_tuple_support(
            built,
            sense,
            value,
            source_count,
        )
        tuples = tuple(
            ExactFieldTuple(
                tuple_index=item.tuple_index,
                fields=tuple(
                    (name, getattr(item, name)) for name in DSF_FIELD_ORDER),
                authority_receipt_sha256=item.authority_receipt_sha256,
                source_index_start=interval[0],
                source_index_end=interval[1],
                source_l0_l4_trace_receipt_sha256=trace_digest,
            )
            for item, interval in zip(
                value.kernel_basin.exact_dsf_field_tuples,
                intervals,
                strict=True,
            )
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
            source_signal_commitment_sha256=(
                cls._source_signal_commitment(
                    built,
                    source_digest,
                    source_count,
                )
                if sense == "sight"
                else None
            ),
        )

    @staticmethod
    def _sense_fingerprint(
        state: str,
        substreams: tuple[ExactSubstreamInterpretation, ...],
        *,
        _field_text_cache: dict[
            int,
            tuple[
                ExactFieldTuple,
                tuple[tuple[str, str], ...],
            ],
        ] | None = None,
    ) -> str:
        return _sense_structural_fingerprint(
            state,
            substreams,
            _field_text_cache=_field_text_cache,
        )

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
        if built.has_transaction_construction_authority:
            built.verify_construction()
        else:
            built.boundary.verify(built.receipt_registry)
        with self._lock:
            self._require_sequence_owner_locked()
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
            field_text_cache: dict[
                int,
                tuple[
                    ExactFieldTuple,
                    tuple[tuple[str, str], ...],
                ],
            ] = {}
            sequence_state = self._atomic_sequence
            previous_by_sense = (
                sequence_state.previous_by_sense
                if sequence_state is not None
                else self._previous_by_sense
            )
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
                    boundary.state.value,
                    substreams,
                    _field_text_cache=field_text_cache,
                )
                previous = previous_by_sense.get(boundary.sense.value)
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
            interpretation_tuple = tuple(interpretations)
            structural_fingerprint = _settlement_structural_fingerprint(
                interpretation_tuple,
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
            (
                native_evidence_witness,
                native_evidence_capability,
            ) = (
                NativeEvidenceCustodyWitness.verified_from_built(
                    built
                )
            )
            native_evidence_preparation = (
                self._native_evidence_custody.prepare_admission(
                    native_evidence_witness,
                    verified_capability=native_evidence_capability,
                )
                if commit or reserve
                else None
            )
            native_preparation_pending_cleanup = (
                native_evidence_preparation is not None
            )
            settlement_payload = causal_experience_settlement_receipt_payload(
                event_id=event_id,
                structural_fingerprint=structural_fingerprint,
                assembly_id=built.boundary.assembly_id,
                source_time_start=(
                    built.boundary.boundaries[0].source_time_start),
                source_time_end=built.boundary.boundaries[0].source_time_end,
                interpretations=interpretation_tuple,
                language_events=language_events,
                native_evidence_witness=native_evidence_witness,
                routing_chis=routing,
                source_tags=sources,
                assembly_receipt_sha256=built.boundary.authority_receipt_sha256,
                _field_text_cache=field_text_cache,
            )
            settlement_registry = ReceiptRegistry.from_payloads(
                profile_payload=SETTLEMENT_PROFILE_PAYLOAD,
                receipt_payloads=(
                    *(
                        record.payload
                        for record
                        in native_evidence_witness.receipt_records
                    ),
                    native_evidence_witness.authority_payload(),
                    settlement_payload,
                ),
            )
            settlement = CausalExperienceSettlement(
                event_id=event_id,
                structural_fingerprint=structural_fingerprint,
                assembly_id=built.boundary.assembly_id,
                source_time_start=(
                    built.boundary.boundaries[0].source_time_start),
                source_time_end=built.boundary.boundaries[0].source_time_end,
                interpretations=interpretation_tuple,
                language_events=language_events,
                native_evidence_witness=native_evidence_witness,
                routing_chis=routing,
                source_tags=sources,
                assembly_receipt_sha256=built.boundary.authority_receipt_sha256,
                authority_receipt_sha256=receipt_sha256(settlement_payload),
                receipt_registry=settlement_registry,
            )
            try:
                if built.has_transaction_construction_authority:
                    _verify_fresh_constructed_settlement(
                        settlement=settlement,
                        built=built,
                        interpretations=interpretation_tuple,
                        language_events=language_events,
                        routing_chis=routing,
                        source_tags=sources,
                        settlement_payload=settlement_payload,
                        native_evidence_capability=(
                            native_evidence_capability
                        ),
                    )
                else:
                    settlement.verify()
                if commit:
                    if native_evidence_preparation is None:
                        raise RuntimeError(
                            "causal native evidence preparation disappeared"
                        )
                    if sequence_state is not None:
                        sequence_state.native_evidence_preparations.append(
                            native_evidence_preparation
                        )
                        native_preparation_pending_cleanup = False
                        try:
                            self._commit_prepared_locked(settlement)
                        except BaseException:
                            sequence_state.native_evidence_preparations.pop()
                            (
                                self._native_evidence_custody
                                .discard_prepared_admission(
                                    native_evidence_preparation
                                )
                            )
                            raise
                    else:
                        native_undo = (
                            self._native_evidence_custody
                            .commit_prepared_admission(
                                native_evidence_preparation
                            )
                        )
                        native_preparation_pending_cleanup = False
                        try:
                            self._commit_prepared_locked(settlement)
                        except BaseException:
                            (
                                self._native_evidence_custody
                                .rollback_committed_admission(
                                    native_undo
                                )
                            )
                            (
                                self._native_evidence_custody
                                .discard_prepared_admission(
                                    native_evidence_preparation
                                )
                            )
                            raise
                elif reserve:
                    if native_evidence_preparation is None:
                        raise RuntimeError(
                            "reserved native evidence preparation disappeared"
                        )
                    self._prepared_reservation = settlement
                    self._prepared_native_evidence_reservation = (
                        native_evidence_preparation
                    )
                    native_preparation_pending_cleanup = False
                return settlement
            except BaseException:
                if (
                    native_evidence_preparation is not None
                    and native_preparation_pending_cleanup
                ):
                    (
                        self._native_evidence_custody
                        .discard_prepared_admission(
                            native_evidence_preparation
                        )
                    )
                raise

    def _commit_prepared_locked(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        current_by_sense = {
            item.sense: item.structural_fingerprint
            for item in settlement.interpretations
            if item.state == "observed"
        }
        sequence_state = self._atomic_sequence
        previous_by_sense = (
            sequence_state.previous_by_sense
            if sequence_state is not None
            else self._previous_by_sense
        )
        transitions = (
            sequence_state.transitions
            if sequence_state is not None
            else self._transitions
        )
        for item in settlement.interpretations:
            previous = previous_by_sense.get(item.sense)
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
        if self._atomic_sequence is None:
            if self._active_verified_settlement is not None:
                raise RuntimeError(
                    "causal verified transaction is already active"
                )
            self._active_verified_settlement = settlement
            self._active_verified_thread_id = threading.get_ident()
            try:
                self._on_settlement(settlement)
            finally:
                self._active_verified_settlement = None
                self._active_verified_thread_id = None
        for sense, current in current_by_sense.items():
            previous = previous_by_sense.get(sense)
            if previous is not None:
                key = (sense, previous, current)
                transitions[key] = transitions.get(key, 0) + 1
                transitions.move_to_end(key)
                while len(transitions) > self._max_transitions:
                    transitions.popitem(last=False)
            previous_by_sense[sense] = current
        if sequence_state is not None:
            sequence_state.settled += 1
        else:
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

    def verify_active_transaction(
        self,
        settlement: CausalExperienceSettlement,
    ) -> bool:
        """Authenticate the exact settlement inside its owner callback."""
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "causal transaction requires a typed settlement"
            )
        with self._lock:
            self._require_public_visibility_locked()
            active = self._active_verified_settlement
            if active is None:
                return False
            if (
                active is not settlement
                or self._active_verified_thread_id != threading.get_ident()
            ):
                raise ReceiptError(
                    "causal settlement left its active transaction"
                )
            return True

    def active_transaction_capability(
        self,
        settlement: CausalExperienceSettlement,
    ) -> VerifiedCausalSettlementCapability:
        """Issue authority only inside this owner's exact callback."""
        if not self.verify_active_transaction(settlement):
            raise ReceiptError(
                "causal settlement has no active transaction"
            )
        canonical_payload = settlement.receipt_registry.resolve(
            settlement.authority_receipt_sha256,
            "active causal settlement",
        )
        try:
            decoded_payload = json.loads(
                canonical_payload.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReceiptError(
                "active causal settlement payload is invalid"
            ) from error
        if (
            not isinstance(decoded_payload, dict)
            or _canonical_bytes(decoded_payload) != canonical_payload
        ):
            raise ReceiptError(
                "active causal settlement payload is not canonical"
            )
        return VerifiedCausalSettlementCapability(
            settlement=settlement,
            canonical_payload=canonical_payload,
            decoded_payload=decoded_payload,
            _construction_authority=(
                _VERIFIED_CAUSAL_TRANSACTION_AUTHORITY
            ),
        )

    def prepared_transaction_capability(
        self,
        settlement: CausalExperienceSettlement,
    ) -> VerifiedCausalSettlementCapability:
        """Authenticate one already-verified owner-held reservation.

        The settlement was fully verified before the owner admitted it as the
        capacity-one prepared transaction.  This capability lets downstream
        constructors prove that they still hold that exact frozen object
        without recursively re-verifying its complete native receipt graph.
        """
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "prepared causal transaction requires a typed settlement"
            )
        with self._lock:
            self._require_sequence_owner_locked()
            native_prepared = self._prepared_native_evidence_reservation
            if (
                self._prepared_reservation is not settlement
                or native_prepared is None
                or native_prepared.witness
                is not settlement.native_evidence_witness
            ):
                raise ReceiptError(
                    "causal settlement left its prepared transaction"
                )
            canonical_payload = settlement.receipt_registry.resolve(
                settlement.authority_receipt_sha256,
                "prepared causal settlement",
            )
            try:
                decoded_payload = json.loads(
                    canonical_payload.decode("utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ReceiptError(
                    "prepared causal settlement payload is invalid"
                ) from error
            if (
                not isinstance(decoded_payload, dict)
                or _canonical_bytes(decoded_payload) != canonical_payload
            ):
                raise ReceiptError(
                    "prepared causal settlement payload is not canonical"
                )
            return VerifiedCausalSettlementCapability(
                settlement=settlement,
                canonical_payload=canonical_payload,
                decoded_payload=decoded_payload,
                _construction_authority=(
                    _VERIFIED_CAUSAL_TRANSACTION_AUTHORITY
                ),
            )

    def commit_prepared(
        self,
        settlement: CausalExperienceSettlement,
        *,
        verified_capability: (
            VerifiedCausalSettlementCapability | None
        ) = None,
    ) -> None:
        """Commit one verified settlement only if its prepared state is current."""
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("prepared causal settlement has the wrong type")
        if verified_capability is None:
            settlement.verify()
        else:
            verified_capability.verify_linkage(settlement)
        with self._lock:
            self._require_sequence_owner_locked()
            native_prepared = (
                self._prepared_native_evidence_reservation
            )
            if (
                self._prepared_reservation is not settlement
                or native_prepared is None
                or native_prepared.witness
                is not settlement.native_evidence_witness
            ):
                raise ValueError(
                    "prepared causal settlement has no live reservation"
                )
            sequence_state = self._atomic_sequence
            previous_by_sense = (
                sequence_state.previous_by_sense
                if sequence_state is not None
                else self._previous_by_sense
            )
            transitions = (
                sequence_state.transitions
                if sequence_state is not None
                else self._transitions
            )
            prior_previous_by_sense = dict(previous_by_sense)
            prior_transitions = OrderedDict(transitions)
            prior_settled = (
                sequence_state.settled
                if sequence_state is not None else self._settled
            )
            native_undo = None
            if sequence_state is not None:
                sequence_state.native_evidence_preparations.append(
                    native_prepared
                )
            else:
                native_undo = (
                    self._native_evidence_custody
                    .commit_prepared_admission(native_prepared)
                )
            try:
                self._commit_prepared_locked(settlement)
            except BaseException:
                if sequence_state is not None:
                    sequence_state.previous_by_sense = prior_previous_by_sense
                    sequence_state.transitions = prior_transitions
                    sequence_state.settled = prior_settled
                    if (
                        not sequence_state
                        .native_evidence_preparations
                        or sequence_state
                        .native_evidence_preparations.pop()
                        is not native_prepared
                    ):
                        raise RuntimeError(
                            "causal native evidence sequence order changed"
                        )
                else:
                    self._previous_by_sense = prior_previous_by_sense
                    self._transitions = prior_transitions
                    self._settled = prior_settled
                    if native_undo is None:
                        raise RuntimeError(
                            "causal native evidence undo disappeared"
                        )
                    (
                        self._native_evidence_custody
                        .rollback_committed_admission(native_undo)
                    )
                raise
            self._prepared_reservation = None
            self._prepared_native_evidence_reservation = None
            self._reservation_condition.notify_all()

    def reserve_prepared(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Reserve one fully verified settlement without committing it."""
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("prepared causal settlement has the wrong type")
        settlement.verify()
        with self._lock:
            self._require_sequence_owner_locked()
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
            sequence_state = self._atomic_sequence
            previous_by_sense = (
                sequence_state.previous_by_sense
                if sequence_state is not None
                else self._previous_by_sense
            )
            for item in settlement.interpretations:
                previous = previous_by_sense.get(item.sense)
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
                        "prepared causal settlement state changed before reserve"
                    )
            native_prepared = (
                self._native_evidence_custody.prepare_admission(
                    settlement.native_evidence_witness
                )
            )
            self._prepared_reservation = settlement
            self._prepared_native_evidence_reservation = native_prepared

    def discard_prepared(
        self,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Release one uncommitted ordering reservation after intake failure."""
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("prepared causal settlement has the wrong type")
        settlement.verify()
        with self._lock:
            self._require_sequence_owner_locked()
            native_prepared = (
                self._prepared_native_evidence_reservation
            )
            if (
                self._prepared_reservation != settlement
                or native_prepared is None
            ):
                raise ValueError(
                    "prepared causal settlement has no live reservation"
                )
            self._native_evidence_custody.discard_prepared_admission(
                native_prepared
            )
            self._prepared_reservation = None
            self._prepared_native_evidence_reservation = None
            self._reservation_condition.notify_all()

    def discard_prepared_for_source_event(self, source_event_id: str) -> bool:
        """Release only the reservation owned by one terminal source event."""
        sha256_digest(source_event_id, "prepared causal source event")
        with self._lock:
            self._require_public_visibility_locked()
            prepared = self._prepared_reservation
            if prepared is None:
                return False
            if (
                len(prepared.language_events) != 1
                or prepared.language_events[0].source_event_id != source_event_id
            ):
                return False
            native_prepared = (
                self._prepared_native_evidence_reservation
            )
            if native_prepared is None:
                raise RuntimeError(
                    "prepared causal reservation lost native evidence"
                )
            self._native_evidence_custody.discard_prepared_admission(
                native_prepared
            )
            self._prepared_reservation = None
            self._prepared_native_evidence_reservation = None
            self._reservation_condition.notify_all()
            return True

    def sequence_snapshot(self) -> dict[str, object]:
        """Return the exact bounded relation-classification state.

        Settlements and sensor samples remain with their owning custody
        authorities.  This snapshot retains only the immediately prior
        structural fingerprint per sense, the bounded transition census,
        and the settled count required for exact recurrence/change
        continuity after restart.
        """

        with self._lock:
            self._require_public_visibility_locked()
            if (
                self._prepared_reservation is not None
                or self._atomic_sequence is not None
                or self._active_verified_settlement is not None
            ):
                raise RuntimeError(
                    "causal sequence cannot snapshot an active transaction"
                )
            sense_order = tuple(value.value for value in SENSE_ORDER)
            payload = {
                "max_transitions": self._max_transitions,
                "previous_by_sense": [
                    {
                        "sense": sense,
                        "structural_fingerprint": (
                            self._previous_by_sense[sense]
                        ),
                    }
                    for sense in sense_order
                    if sense in self._previous_by_sense
                ],
                "schema": "guala.exact_causal_sequence.state.v1",
                "settled": self._settled,
                "transitions": [
                    {
                        "count": count,
                        "current_structural_fingerprint": current,
                        "previous_structural_fingerprint": previous,
                        "sense": sense,
                    }
                    for (sense, previous, current), count
                    in self._transitions.items()
                ],
            }
            return payload | {
                "state_sha256": receipt_sha256(
                    _canonical_bytes(payload)
                ),
            }

    def restore_sequence_snapshot(self, value: object) -> None:
        """Restore one exact sequence snapshot into a fresh owner."""

        expected_fields = {
            "max_transitions",
            "previous_by_sense",
            "schema",
            "settled",
            "state_sha256",
            "transitions",
        }
        if (
            not isinstance(value, dict)
            or set(value) != expected_fields
            or value.get("schema")
            != "guala.exact_causal_sequence.state.v1"
            or value.get("max_transitions") != self._max_transitions
        ):
            raise ValueError("causal sequence snapshot fields changed")
        state_sha = value.get("state_sha256")
        payload = {
            key: value[key]
            for key in expected_fields
            if key != "state_sha256"
        }
        if (
            not isinstance(state_sha, str)
            or receipt_sha256(_canonical_bytes(payload)) != state_sha
        ):
            raise ValueError("causal sequence snapshot identity changed")
        settled = value.get("settled")
        prior_records = value.get("previous_by_sense")
        transition_records = value.get("transitions")
        sense_order = tuple(item.value for item in SENSE_ORDER)
        if (
            isinstance(settled, bool)
            or not isinstance(settled, int)
            or settled < 0
            or not isinstance(prior_records, list)
            or not isinstance(transition_records, list)
            or len(transition_records) > self._max_transitions
        ):
            raise ValueError("causal sequence snapshot capacity changed")
        previous: dict[str, str] = {}
        prior_senses = []
        for record in prior_records:
            if (
                not isinstance(record, dict)
                or set(record)
                != {"sense", "structural_fingerprint"}
                or record.get("sense") not in sense_order
            ):
                raise ValueError(
                    "causal sequence prior-sense record changed"
                )
            sense = record["sense"]
            fingerprint = sha256_digest(
                record.get("structural_fingerprint"),
                "causal sequence prior structure",
            )
            if sense in previous:
                raise ValueError(
                    "causal sequence repeats a prior sense"
                )
            previous[sense] = fingerprint
            prior_senses.append(sense)
        if tuple(prior_senses) != tuple(
            sense for sense in sense_order if sense in previous
        ):
            raise ValueError(
                "causal sequence prior senses are not canonical"
            )
        transitions: OrderedDict[tuple[str, str, str], int] = (
            OrderedDict()
        )
        for record in transition_records:
            if (
                not isinstance(record, dict)
                or set(record)
                != {
                    "count",
                    "current_structural_fingerprint",
                    "previous_structural_fingerprint",
                    "sense",
                }
                or record.get("sense") not in sense_order
            ):
                raise ValueError(
                    "causal sequence transition record changed"
                )
            count = record.get("count")
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
            ):
                raise ValueError(
                    "causal sequence transition count changed"
                )
            key = (
                record["sense"],
                sha256_digest(
                    record.get("previous_structural_fingerprint"),
                    "causal sequence transition prior",
                ),
                sha256_digest(
                    record.get("current_structural_fingerprint"),
                    "causal sequence transition current",
                ),
            )
            if key in transitions:
                raise ValueError(
                    "causal sequence repeats a transition"
                )
            transitions[key] = count
        with self._lock:
            self._require_public_visibility_locked()
            if (
                self._prepared_reservation is not None
                or self._atomic_sequence is not None
                or self._active_verified_settlement is not None
                or self._previous_by_sense
                or self._transitions
                or self._settled
            ):
                raise RuntimeError(
                    "causal sequence restore requires a fresh owner"
                )
            self._previous_by_sense = previous
            self._transitions = transitions
            self._settled = settled
            if self.sequence_snapshot() != value:
                raise ValueError(
                    "causal sequence cold restore changed state"
                )

    def status(self) -> dict:
        with self._lock:
            self._require_public_visibility_locked()
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
                "atomic_sequence": int(self._atomic_sequence is not None),
                "atomic_sequence_staged_settled": (
                    self._atomic_sequence.settled - self._settled
                    if self._atomic_sequence is not None else 0
                ),
                "native_evidence_custody": (
                    self._native_evidence_custody.status()
                ),
            }


__all__ = (
    "CausalExperienceSettlement",
    "CausalAtomicVisibilityInstall",
    "ExactCausalExperienceOwner",
    "ExactFieldTuple",
    "ExactRecognizedLanguageEvent",
    "ExactSenseInterpretation",
    "ExactSubstreamInterpretation",
    "MAX_CAUSAL_RESERVATION_WAITERS",
    "SETTLEMENT_SCHEMA",
    "VerifiedCausalSettlementCapability",
    "causal_experience_settlement_receipt_payload",
    "source_evidence_sample_commitment_sha256",
)
