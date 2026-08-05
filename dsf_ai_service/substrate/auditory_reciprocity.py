"""Bounded joint causal-path reciprocity for auditory L5.

Spoken forms are ordered paths through the complete mounted auditory field.
Tutor reinforcement adds another witnessed path; it never widens independent
per-coordinate minima and maxima.  A query belongs to a learned class only
when one monotone, duration-normalized traversal and one shared interpolation
coordinate satisfy every pressure sample, every resolved phase advance, and
every named L4 field together.  There is no distance score, nearest-neighbour
fallback, probability, chi identity, or lifetime experience index.
This is an explicitly tutor-grounded deterministic geometric rule, not a
claim that the interpolation geometry is DSF physics.

The microphone is monaural.  It cannot provide physical agent identity.
``source_continuity`` consequently remains UNKNOWN without independently
receipted acoustic-source correspondence.  Uninterrupted acquisition proves
only microphone-stream continuity, not who spoke.  This module does not turn
an acoustic resemblance or a client source string into an agent.

Witnesses are packed as sixteen physical cochlear channels.  Each channel
contains one binary64 pressure/phase-advance sample pair and two independent
exact rational L4 tuple banks evaluated under the same interpolation
coordinate.  Four distinct branches per spoken form, a class cap, and a hard
encoded-snapshot cap bound both learned state and persistence.  Every
admission is encoded and checked before the live state is mutated.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import math
import struct
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    MAX_NATIVE_SUBSTREAMS_PER_SENSE,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AUDITORY_L5_AUTHORITY_SCHEMA,
    AUDITORY_L5_SCHEMA,
    AuditoryL5CochlearChannel,
    AuditoryL5Experience,
    AuditoryL5KernelComponent,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
    PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAdmissionReceipt,
    AuditoryTutorAuthority,
    AuditoryTutorAuthorityReceipt,
    canonical_tutor_label,
)

try:
    from guala_core import (
        auditory_joint_path_contains as _native_joint_path_contains,
    )
except ImportError:
    _native_joint_path_contains = None


MAX_RECIPROCAL_CLASSES_PER_KIND = 64
MAX_PATH_BRANCHES_PER_CLASS = 4
MAX_ENCODED_SNAPSHOT_BYTES = 15 * 1024 * 1024
MAX_DECODED_SNAPSHOT_BYTES = 64 * 1024 * 1024
MAX_REACHABILITY_CELLS_PER_RECOGNITION = 1_000_000
MAX_INTERVAL_COMPONENTS_PER_CELL = 64
PCM_PRESSURE_QUANTUM = Fraction(1, 32_768)
AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA = "guala.auditory.causal_path.v5"
AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA = (
    "guala.auditory.causal_path.gzip.v5"
)
AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA = (
    "guala.auditory.recognition_occurrence.v2"
)
AUDITORY_RECOGNITION_OPERATOR = "auditory_joint_causal_path_contains.v2"
LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA = (
    "guala.auditory.causal_path.v4"
)
LEGACY_AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA = (
    "guala.auditory.causal_path.gzip.v4"
)


@dataclass(frozen=True, slots=True)
class LegacyAuditoryReciprocityEnvelopeInspection:
    """Integrity facts for an opaque v4 envelope.

    Inspection proves only bounded, canonical persistence and the two v4
    schema identities.  It deliberately does not construct reciprocal
    classes or grant the archived state any live recognition authority.
    """

    envelope_canonical_sha256: str
    encoded_payload_bytes: int
    decoded_payload_bytes: int
    payload_sha256: str


def _canonical_persistence_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def inspect_legacy_v4_envelope(
    envelope: object,
) -> LegacyAuditoryReciprocityEnvelopeInspection:
    """Verify one v4 envelope without interpreting or restoring its field."""

    if not isinstance(envelope, dict) or set(envelope) != {
        "encoding", "payload", "payload_sha256", "schema"
    }:
        raise ValueError("legacy auditory reciprocity envelope is malformed")
    if (
        envelope.get("schema")
        != LEGACY_AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA
        or envelope.get("encoding") != "gzip+base64"
    ):
        raise ValueError("legacy auditory reciprocity envelope schema is invalid")
    encoded = envelope.get("payload")
    expected_digest = envelope.get("payload_sha256")
    if not isinstance(encoded, str) or not isinstance(expected_digest, str):
        raise ValueError("legacy auditory reciprocity envelope is malformed")
    try:
        encoded_bytes = encoded.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(
            "legacy auditory reciprocity payload is not canonical base64"
        ) from exc
    if not encoded_bytes or len(encoded_bytes) > MAX_ENCODED_SNAPSHOT_BYTES:
        raise ValueError(
            "legacy auditory reciprocity envelope exceeds its encoded boundary"
        )
    if (
        len(expected_digest) != 64
        or any(character not in "0123456789abcdef" for character in expected_digest)
    ):
        raise ValueError("legacy auditory reciprocity digest is malformed")
    try:
        compressed = base64.b64decode(encoded_bytes, validate=True)
        if base64.b64encode(compressed) != encoded_bytes:
            raise ValueError("legacy auditory reciprocity base64 is not canonical")
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            payload = stream.read(MAX_DECODED_SNAPSHOT_BYTES + 1)
    except Exception as exc:
        raise ValueError(
            "legacy auditory reciprocity envelope cannot be decoded"
        ) from exc
    if len(payload) > MAX_DECODED_SNAPSHOT_BYTES:
        raise ValueError(
            "legacy auditory reciprocity decoded snapshot is oversized"
        )
    if hashlib.sha256(payload).hexdigest() != expected_digest:
        raise ValueError(
            "legacy auditory reciprocity envelope failed integrity check"
        )
    try:
        snapshot = json.loads(payload)
    except Exception as exc:
        raise ValueError(
            "legacy auditory reciprocity payload is not JSON"
        ) from exc
    if not isinstance(snapshot, dict) or (
        snapshot.get("schema")
        != LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
    ):
        raise ValueError("legacy auditory reciprocity snapshot schema is invalid")
    if _canonical_persistence_bytes(snapshot) != payload:
        raise ValueError("legacy auditory reciprocity payload is not canonical")
    return LegacyAuditoryReciprocityEnvelopeInspection(
        envelope_canonical_sha256=hashlib.sha256(
            _canonical_persistence_bytes(envelope)
        ).hexdigest(),
        encoded_payload_bytes=len(encoded_bytes),
        decoded_payload_bytes=len(payload),
        payload_sha256=expected_digest,
    )


class AuditoryReciprocityKind(str, Enum):
    SPOKEN_FORM = "spoken_form"
    SOURCE_CONTINUITY = "source_continuity"


class AuditoryRecognitionState(str, Enum):
    UNKNOWN = "unknown"
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True, slots=True)
class AuditoryComponentTopology:
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]
    physical_quantity: str
    physical_unit: str
    source_stream_receipt_sha256: str
    l0_l4_trace_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryChannelTopology:
    cochlear_index: int
    channel_id: str
    pressure: AuditoryComponentTopology
    carrier_phase_advance: AuditoryComponentTopology
    pair_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class PackedL4Tuple:
    tuple_index: int
    fields: tuple[tuple[str, Fraction], ...]
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryPathWitness:
    """One verified tutor witness, packed without Python sample objects."""

    experience_id: str
    structural_fingerprint: str
    topology: tuple[AuditoryChannelTopology, ...]
    sample_count: int
    source_indices: tuple[int, ...]
    source_time_start: Fraction
    causal_offset_start: Fraction
    causal_offset_step: Fraction
    # Per channel: little-endian (normalized pressure, provider-settled
    # carrier phase advance turns) binary64 pairs.
    packed_samples: tuple[bytes, ...]
    pressure_l4_field_tuples: tuple[tuple[PackedL4Tuple, ...], ...]
    carrier_phase_advance_l4_field_tuples: tuple[
        tuple[PackedL4Tuple, ...], ...
    ]


@dataclass(frozen=True, slots=True)
class AuditoryReciprocalClass:
    kind: AuditoryReciprocityKind
    tutor_label: str
    branches: tuple[AuditoryPathWitness, ...]
    reinforcement_count: int
    first_experience_id: str
    last_experience_id: str
    authority_receipts: tuple[AuditoryTutorAuthorityReceipt, ...]
    admission_receipts: tuple[AuditoryTutorAdmissionReceipt, ...]
    admission_evidence_sha256: tuple[str, ...]


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


def _class_authority_receipt(value: AuditoryReciprocalClass) -> str:
    """Stable identity of one tutor-grounded learned auditory class."""
    if not isinstance(value, AuditoryReciprocalClass) or not value.branches:
        raise ValueError("auditory learned class authority is invalid")
    first_authority = (
        value.authority_receipts[0].authority_hmac_sha256
        if value.authority_receipts else None
    )
    first_admission = (
        value.admission_receipts[0].admission_hmac_sha256
        if value.admission_receipts else None
    )
    return _digest({
        "first_admission_hmac_sha256": first_admission,
        "first_authority_hmac_sha256": first_authority,
        "first_experience_id": value.first_experience_id,
        "first_structural_fingerprint": (
            value.branches[0].structural_fingerprint
        ),
        "kind": value.kind.value,
        "schema": "guala.auditory.learned_class_authority.v1",
        "tutor_label": value.tutor_label,
    })


@dataclass(frozen=True, slots=True)
class AuditoryRecognitionOccurrence:
    """Receipt-bound result of one complete full-field recognition act."""

    kind: AuditoryReciprocityKind
    state: AuditoryRecognitionState
    experience_id: str
    structural_fingerprint: str
    l5_authority_receipt_sha256: str
    candidate_class_authority_receipts: tuple[str, ...]
    selected_class_authority_receipt_sha256: str | None
    operator: str
    authority_receipt_sha256: str

    def _payload(self) -> dict[str, object]:
        return {
            "candidate_class_authority_receipts": list(
                self.candidate_class_authority_receipts
            ),
            "experience_id": self.experience_id,
            "kind": self.kind.value,
            "l5_authority_receipt_sha256": (
                self.l5_authority_receipt_sha256
            ),
            "operator": self.operator,
            "schema": AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA,
            "selected_class_authority_receipt_sha256": (
                self.selected_class_authority_receipt_sha256
            ),
            "state": self.state.value,
            "structural_fingerprint": self.structural_fingerprint,
        }

    def verify(self) -> None:
        sha256_digest(self.experience_id, "auditory recognition experience")
        sha256_digest(
            self.structural_fingerprint,
            "auditory recognition structural fingerprint",
        )
        sha256_digest(
            self.l5_authority_receipt_sha256,
            "auditory recognition L5 authority",
        )
        if (
            self.operator != AUDITORY_RECOGNITION_OPERATOR
            or not isinstance(self.candidate_class_authority_receipts, tuple)
            or tuple(sorted(set(self.candidate_class_authority_receipts)))
            != self.candidate_class_authority_receipts
        ):
            raise ValueError("auditory recognition occurrence is malformed")
        for receipt in self.candidate_class_authority_receipts:
            sha256_digest(receipt, "auditory recognition candidate class")
        if self.state is AuditoryRecognitionState.UNIQUE:
            if (
                len(self.candidate_class_authority_receipts) != 1
                or self.selected_class_authority_receipt_sha256
                != self.candidate_class_authority_receipts[0]
            ):
                raise ValueError(
                    "unique auditory recognition lost its selected class"
                )
        elif self.selected_class_authority_receipt_sha256 is not None:
            raise ValueError(
                "non-unique auditory recognition selected a class"
            )
        if _digest(self._payload()) != sha256_digest(
            self.authority_receipt_sha256,
            "auditory recognition occurrence authority",
        ):
            raise ValueError("auditory recognition occurrence receipt changed")

    def as_record(self) -> dict[str, object]:
        self.verify()
        return {
            **self._payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    @classmethod
    def from_record(cls, value: object) -> "AuditoryRecognitionOccurrence":
        if not isinstance(value, Mapping):
            raise ValueError("auditory recognition occurrence must be an object")
        expected = {
            "authority_receipt_sha256",
            "candidate_class_authority_receipts",
            "experience_id",
            "kind",
            "l5_authority_receipt_sha256",
            "operator",
            "schema",
            "selected_class_authority_receipt_sha256",
            "state",
            "structural_fingerprint",
        }
        if set(value) != expected or value.get("schema") != (
            AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA
        ):
            raise ValueError("auditory recognition occurrence fields changed")
        candidates = value.get("candidate_class_authority_receipts")
        if not isinstance(candidates, list):
            raise ValueError("auditory recognition candidates are malformed")
        try:
            occurrence = cls(
                kind=AuditoryReciprocityKind(value.get("kind")),
                state=AuditoryRecognitionState(value.get("state")),
                experience_id=value.get("experience_id"),
                structural_fingerprint=value.get("structural_fingerprint"),
                l5_authority_receipt_sha256=value.get(
                    "l5_authority_receipt_sha256"
                ),
                candidate_class_authority_receipts=tuple(candidates),
                selected_class_authority_receipt_sha256=value.get(
                    "selected_class_authority_receipt_sha256"
                ),
                operator=value.get("operator"),
                authority_receipt_sha256=value.get(
                    "authority_receipt_sha256"
                ),
            )
        except (TypeError, ValueError) as error:
            raise ValueError(
                "auditory recognition occurrence values changed"
            ) from error
        occurrence.verify()
        if occurrence.as_record() != dict(value):
            raise ValueError("auditory recognition occurrence is not canonical")
        return occurrence


@dataclass(frozen=True, slots=True)
class AuditoryRecognition:
    kind: AuditoryReciprocityKind
    state: AuditoryRecognitionState
    tutor_label: str | None
    candidate_labels: tuple[str, ...]
    experience_id: str
    occurrence: AuditoryRecognitionOccurrence


def _label(value: object) -> str:
    return canonical_tutor_label(value)


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise ValueError("auditory path field is not an exact fraction")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an exact fraction string")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"{name} is not an exact fraction") from exc


def _binary64_exact(value: Fraction, name: str) -> float:
    encoded = float(value)
    if not math.isfinite(encoded) or Fraction.from_float(encoded) != value:
        raise ValueError(f"{name} is not an exact mounted binary64 value")
    return encoded


def _component_topology(
    component: AuditoryL5KernelComponent,
) -> AuditoryComponentTopology:
    return AuditoryComponentTopology(
        sensor_id=component.sensor_id,
        substream_id=component.substream_id,
        topology_index=component.topology_index,
        coordinates=component.coordinates,
        physical_quantity=component.physical_quantity,
        physical_unit=component.physical_unit,
        source_stream_receipt_sha256=component.source_stream_receipt_sha256,
        l0_l4_trace_receipt_sha256=component.l0_l4_trace_receipt_sha256,
        kernel_basin_receipt_sha256=component.kernel_basin_receipt_sha256,
        authority_receipt_sha256=component.authority_receipt_sha256,
    )


def _channel_topology(
    channel: AuditoryL5CochlearChannel,
) -> AuditoryChannelTopology:
    return AuditoryChannelTopology(
        cochlear_index=channel.cochlear_index,
        channel_id=channel.channel_id,
        pressure=_component_topology(channel.pressure),
        carrier_phase_advance=_component_topology(
            channel.carrier_phase_advance
        ),
        pair_receipt_sha256=channel.pair_receipt_sha256,
    )


def _common_causal_grid(
    channels: tuple[AuditoryL5CochlearChannel, ...],
) -> tuple[int, Fraction, Fraction]:
    if not channels or not channels[0].pressure.samples:
        raise ValueError("auditory path requires a nonempty mounted field")
    components = tuple(
        component
        for channel in channels
        for component in (channel.pressure, channel.carrier_phase_advance)
    )
    reference = tuple(
        sample.causal_offset for sample in components[0].samples
    )
    if any(
        tuple(sample.causal_offset for sample in component.samples) != reference
        for component in components[1:]
    ):
        raise ValueError("auditory path components are not on one causal grid")
    if len(reference) == 1:
        return 1, reference[0], Fraction(0)
    step = reference[1] - reference[0]
    if step <= 0 or any(
        right - left != step
        for left, right in zip(reference, reference[1:], strict=False)
    ):
        raise ValueError("auditory path causal grid is not uniform")
    return len(reference), reference[0], step


def _pack_experience(experience: AuditoryL5Experience) -> AuditoryPathWitness:
    if not isinstance(experience, AuditoryL5Experience):
        raise ValueError("auditory reciprocity requires an exact L5 experience")
    experience.verify()
    channels = experience.channels
    if (
        len(channels) != COCHLEAR_CHANNEL_COUNT
        or len(channels) > MAX_NATIVE_SUBSTREAMS_PER_SENSE
        or tuple(channel.cochlear_index for channel in channels)
        != tuple(range(COCHLEAR_CHANNEL_COUNT))
    ):
        raise ValueError("auditory path requires exactly 16 ordered channels")
    sample_count, offset_start, offset_step = _common_causal_grid(channels)
    if sample_count > MAX_NATIVE_SAMPLES_PER_SUBSTREAM:
        raise ValueError("auditory path exceeds the mounted sample boundary")
    source_indices = tuple(
        sample.source_index for sample in channels[0].pressure.samples
    )
    components = tuple(
        component
        for channel in channels
        for component in (channel.pressure, channel.carrier_phase_advance)
    )
    if any(
        tuple(sample.source_index for sample in component.samples)
        != source_indices
        for component in components[1:]
    ):
        raise ValueError("auditory path components changed source sample identity")

    def pack_l4(
        component: AuditoryL5KernelComponent,
        channel_index: int,
    ) -> tuple[PackedL4Tuple, ...]:
        tuples = []
        for expected_index, field_tuple in enumerate(component.l4_field_tuples):
            if (
                field_tuple.tuple_index != expected_index
                or tuple(name for name, _ in field_tuple.fields)
                != DSF_FIELD_ORDER
            ):
                raise ValueError("auditory path L4 field order changed")
            tuples.append(PackedL4Tuple(
                tuple_index=field_tuple.tuple_index,
                fields=field_tuple.fields,
                authority_receipt_sha256=sha256_digest(
                    field_tuple.authority_receipt_sha256,
                    f"auditory channel {channel_index} L4 receipt",
                ),
            ))
        if not tuples:
            raise ValueError("auditory path has no explicit L4 field tuple")
        return tuple(tuples)

    packed_channels: list[bytes] = []
    pressure_l4: list[tuple[PackedL4Tuple, ...]] = []
    phase_l4: list[tuple[PackedL4Tuple, ...]] = []
    for channel_index, channel in enumerate(channels):
        values: list[float] = []
        for sample_index, (pressure, phase) in enumerate(zip(
            channel.pressure.samples,
            channel.carrier_phase_advance.samples,
            strict=True,
        )):
            values.extend((
                _binary64_exact(
                    pressure.signal,
                    f"auditory channel {channel_index} pressure {sample_index}",
                ),
                _binary64_exact(
                    Fraction.from_float(
                        float(phase.signal)
                        * PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
                    ),
                    f"auditory channel {channel_index} phase advance {sample_index}",
                ),
            ))
        packed_channels.append(struct.pack(f"<{len(values)}d", *values))
        pressure_l4.append(pack_l4(channel.pressure, channel_index))
        phase_l4.append(pack_l4(
            channel.carrier_phase_advance, channel_index
        ))
    return AuditoryPathWitness(
        experience_id=sha256_digest(
            experience.experience_id, "auditory path experience id"
        ),
        structural_fingerprint=sha256_digest(
            experience.structural_fingerprint,
            "auditory path structural fingerprint",
        ),
        topology=tuple(_channel_topology(channel) for channel in channels),
        sample_count=sample_count,
        source_indices=source_indices,
        source_time_start=experience.source_time_start,
        causal_offset_start=offset_start,
        causal_offset_step=offset_step,
        packed_samples=tuple(packed_channels),
        pressure_l4_field_tuples=tuple(pressure_l4),
        carrier_phase_advance_l4_field_tuples=tuple(phase_l4),
    )


def _witness_structural_fingerprint(witness: AuditoryPathWitness) -> str:
    def component_payload(
        topology: AuditoryComponentTopology,
        l4_bank: tuple[PackedL4Tuple, ...],
        channel_index: int,
        *,
        pressure: bool,
    ) -> dict[str, object]:
        samples = []
        for sample_index in range(witness.sample_count):
            pressure_value, phase_advance = struct.unpack_from(
                "<dd",
                witness.packed_samples[channel_index],
                sample_index * 16,
            )
            signal = (
                pressure_value
                if pressure
                else phase_advance
                / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            )
            phase_turns = 0.0 if pressure else phase_advance
            causal_offset = (
                witness.causal_offset_start
                + sample_index * witness.causal_offset_step
            )
            samples.append({
                "causal_offset": _fraction_text(causal_offset),
                "phase_turns": _fraction_text(
                    Fraction.from_float(phase_turns)
                ),
                "signal": _fraction_text(Fraction.from_float(signal)),
                "source_index": witness.source_indices[sample_index],
            })
        return {
            "coordinates": [list(value) for value in topology.coordinates],
            "kind": "pressure" if pressure else "carrier_phase_advance",
            "l4_field_tuples": [
                {
                    "fields": [
                        [name, _fraction_text(field)]
                        for name, field in field_tuple.fields
                    ],
                    "tuple_index": field_tuple.tuple_index,
                }
                for field_tuple in l4_bank
            ],
            "physical_quantity": topology.physical_quantity,
            "physical_unit": topology.physical_unit,
            "samples": samples,
            "sensor_id": topology.sensor_id,
            "substream_id": topology.substream_id,
            "topology_index": topology.topology_index,
        }

    payload = {
        "channels": [
            {
                "carrier_phase_advance": component_payload(
                    channel.carrier_phase_advance,
                    witness.carrier_phase_advance_l4_field_tuples[channel_index],
                    channel_index,
                    pressure=False,
                ),
                "channel_id": channel.channel_id,
                "cochlear_index": channel.cochlear_index,
                "pressure": component_payload(
                    channel.pressure,
                    witness.pressure_l4_field_tuples[channel_index],
                    channel_index,
                    pressure=True,
                ),
            }
            for channel_index, channel in enumerate(witness.topology)
        ],
        "schema": AUDITORY_L5_SCHEMA,
    }
    return hashlib.sha256(json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _witness_admission_evidence(
    witness: AuditoryPathWitness,
) -> dict[str, object]:
    return {
        "channels": [
            {
                "carrier_phase_advance": {
                    "component_receipt_sha256": (
                        topology.carrier_phase_advance.authority_receipt_sha256
                    ),
                    "l4_field_receipt_sha256s": [
                        value.authority_receipt_sha256
                        for value in (
                            witness.carrier_phase_advance_l4_field_tuples[index]
                        )
                    ],
                },
                "channel_id": topology.channel_id,
                "cochlear_index": topology.cochlear_index,
                "pair_receipt_sha256": topology.pair_receipt_sha256,
                "pressure": {
                    "component_receipt_sha256": (
                        topology.pressure.authority_receipt_sha256
                    ),
                    "l4_field_receipt_sha256s": [
                        value.authority_receipt_sha256
                        for value in witness.pressure_l4_field_tuples[index]
                    ],
                },
            }
            for index, topology in enumerate(witness.topology)
        ],
        "source_time_start": _fraction_text(witness.source_time_start),
        "structural_fingerprint": witness.structural_fingerprint,
    }


def _admission_evidence_from_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        "channels": payload.get("channels"),
        "source_time_start": payload.get("source_time_start"),
        "structural_fingerprint": payload.get("structural_fingerprint"),
    }


def _verify_l5_admission_evidence(
    admission: AuditoryTutorAdmissionReceipt,
    witnesses: tuple[AuditoryPathWitness, ...],
    *,
    witnesses_verified: bool = False,
    expected_evidence_sha256: str | None = None,
) -> None:
    if not isinstance(witnesses_verified, bool):
        raise TypeError("auditory witness verification state must be boolean")
    if expected_evidence_sha256 is not None:
        expected_evidence_sha256 = sha256_digest(
            expected_evidence_sha256,
            "auditory persisted admission evidence",
        )
    try:
        payload = json.loads(admission.l5_authority_payload)
    except Exception as exc:
        raise ValueError("auditory L5 admission payload is not JSON") from exc
    canonical = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if canonical != admission.l5_authority_payload:
        raise ValueError("auditory L5 admission payload is not canonical")
    if not isinstance(payload, dict) or set(payload) != {
        "assembly_id",
        "assembly_receipt_sha256",
        "channels",
        "event_boundary",
        "experience_id",
        "relation",
        "schema",
        "source_time_end",
        "source_time_start",
        "structural_fingerprint",
    }:
        raise ValueError("auditory L5 admission payload is malformed")
    if (
        payload.get("schema") != AUDITORY_L5_AUTHORITY_SCHEMA
        or payload.get("event_boundary") != "utterance"
        or admission.event_boundary != "utterance"
        or payload.get("experience_id") != admission.experience_id
        or payload.get("relation") not in (
            "first_observation", "recurrence", "structural_change"
        )
    ):
        raise ValueError("auditory L5 admission does not prove utterance eligibility")
    assembly_id = payload.get("assembly_id")
    if not isinstance(assembly_id, str) or not assembly_id:
        raise ValueError("auditory L5 admission assembly is invalid")
    fingerprint = sha256_digest(
        payload.get("structural_fingerprint"),
        "auditory L5 admission structural fingerprint",
    )
    expected_experience_id = hashlib.sha256(json.dumps(
        {
            "assembly_id": assembly_id,
            "auditory_structural_fingerprint": fingerprint,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()
    if expected_experience_id != admission.experience_id:
        raise ValueError("auditory L5 admission experience identity changed")
    sha256_digest(
        payload.get("assembly_receipt_sha256"),
        "auditory L5 admission assembly receipt",
    )
    start = _fraction(
        payload.get("source_time_start"),
        "auditory L5 admission source start",
    )
    end = _fraction(
        payload.get("source_time_end"),
        "auditory L5 admission source end",
    )
    if end <= start:
        raise ValueError("auditory L5 admission source time is invalid")
    channels = payload.get("channels")
    if (
        not isinstance(channels, list)
        or len(channels) != COCHLEAR_CHANNEL_COUNT
    ):
        raise ValueError("auditory L5 admission channels are malformed")
    matching = tuple(
        witness
        for witness in witnesses
        if witness.structural_fingerprint == fingerprint
        and witness.source_time_start == start
        and (
            witnesses_verified
            or _witness_structural_fingerprint(witness) == fingerprint
        )
    )
    if expected_evidence_sha256 is not None:
        if not any(
            witness.structural_fingerprint == fingerprint
            and (
                witnesses_verified
                or _witness_structural_fingerprint(witness) == fingerprint
            )
            for witness in witnesses
        ):
            raise ValueError(
                "auditory L5 admission does not match a persisted witness"
            )
        if _digest(_admission_evidence_from_payload(payload)) != (
            expected_evidence_sha256
        ):
            raise ValueError(
                "auditory L5 admission ordered receipt evidence changed"
            )
        return
    for witness in matching:
        if len(channels) != len(witness.topology):
            continue
        valid = True
        for channel_index, (raw, topology) in enumerate(
            zip(channels, witness.topology, strict=True)
        ):
            if not isinstance(raw, dict) or set(raw) != {
                "carrier_phase_advance",
                "channel_id",
                "cochlear_index",
                "pair_receipt_sha256",
                "pressure",
            }:
                valid = False
                break
            if (
                raw.get("cochlear_index") != topology.cochlear_index
                or raw.get("channel_id") != topology.channel_id
                or raw.get("pair_receipt_sha256")
                != topology.pair_receipt_sha256
            ):
                valid = False
                break
            sha256_digest(
                raw.get("pair_receipt_sha256"),
                "auditory L5 cochlear pair receipt",
            )
            component_evidence = (
                (
                    raw.get("pressure"),
                    topology.pressure,
                    witness.pressure_l4_field_tuples[channel_index],
                ),
                (
                    raw.get("carrier_phase_advance"),
                    topology.carrier_phase_advance,
                    witness.carrier_phase_advance_l4_field_tuples[
                        channel_index
                    ],
                ),
            )
            for component_raw, component_topology, l4_bank in component_evidence:
                if not isinstance(component_raw, dict) or set(component_raw) != {
                    "component_receipt_sha256",
                    "l4_field_receipt_sha256s",
                }:
                    valid = False
                    break
                receipts = component_raw.get("l4_field_receipt_sha256s")
                expected_receipts = tuple(
                    value.authority_receipt_sha256 for value in l4_bank
                )
                if (
                    component_raw.get("component_receipt_sha256")
                    != component_topology.authority_receipt_sha256
                    or not isinstance(receipts, list)
                    or tuple(receipts) != expected_receipts
                ):
                    valid = False
                    break
                sha256_digest(
                    component_raw.get("component_receipt_sha256"),
                    "auditory L5 component receipt",
                )
                for digest in receipts:
                    sha256_digest(digest, "auditory L5 ordered L4 receipt")
            if not valid:
                break
        if valid:
            return
    raise ValueError("auditory L5 admission does not match a persisted witness")


def _sample(
    witness: AuditoryPathWitness, channel: int, index: int
) -> tuple[float, float]:
    return struct.unpack_from(
        "<dd", witness.packed_samples[channel], index * 16
    )


def _interpolated_sample(
    witness: AuditoryPathWitness,
    port: int,
    query_index: int,
    query_count: int,
) -> tuple[float, float]:
    if witness.sample_count == 1 or query_count == 1:
        return _sample(witness, port, 0)
    position = query_index * (witness.sample_count - 1) / (query_count - 1)
    left = int(math.floor(position))
    right = min(left + 1, witness.sample_count - 1)
    weight = position - left
    left_pressure = _sample(witness, port, left)[0]
    right_pressure = _sample(witness, port, right)[0]
    left_phase = _sample(witness, port, left)[1]
    right_phase = _sample(witness, port, right)[1]
    return (
        left_pressure + weight * (right_pressure - left_pressure),
        left_phase + weight * (right_phase - left_phase),
    )


def _interpolated_phase_prior_pressure(
    witness: AuditoryPathWitness,
    port: int,
    query_index: int,
    query_count: int,
) -> float:
    if witness.sample_count == 1:
        return _sample(witness, port, 0)[0]
    position = (
        0.0
        if query_count == 1
        else query_index * (witness.sample_count - 1) / (query_count - 1)
    )
    prior_position = position - 1.0 if position >= 1.0 else position + 1.0
    left = int(math.floor(prior_position))
    right = min(left + 1, witness.sample_count - 1)
    weight = prior_position - left
    left_pressure = _sample(witness, port, left)[0]
    right_pressure = _sample(witness, port, right)[0]
    return left_pressure + weight * (right_pressure - left_pressure)


def _intersect_lambda(
    interval: tuple[float, float],
    *,
    query: float,
    left: float,
    right: float,
    uncertainty: float,
) -> tuple[float, float] | None:
    lower, upper = interval
    difference = right - left
    if difference == 0.0:
        return interval if abs(query - left) <= uncertainty else None
    first = (query - uncertainty - left) / difference
    second = (query + uncertainty - left) / difference
    coordinate_lower = min(first, second)
    coordinate_upper = max(first, second)
    lower = max(lower, coordinate_lower)
    upper = min(upper, coordinate_upper)
    return (lower, upper) if lower <= upper else None


def _phase_uncertainty(*pressures: float) -> float | None:
    quantum = float(PCM_PRESSURE_QUANTUM)
    if any(value <= quantum for value in pressures):
        return None
    # A component error q on a complex response of magnitude A turns its
    # direction by at most asin(q/A).  A phase advance has two endpoints for
    # each of query/left/right, hence six explicitly propagated terms.
    return sum(
        math.asin(min(1.0, quantum / value)) / (2.0 * math.pi)
        for value in pressures
    )


def _same_topology(*witnesses: AuditoryPathWitness) -> bool:
    def physical(value: AuditoryPathWitness) -> tuple[object, ...]:
        return tuple(
            (
                channel.cochlear_index,
                channel.channel_id,
                *(
                    (
                        component.sensor_id,
                        component.substream_id,
                        component.topology_index,
                        component.coordinates,
                        component.physical_quantity,
                        component.physical_unit,
                    )
                    for component in (
                        channel.pressure,
                        channel.carrier_phase_advance,
                    )
                ),
            )
            for channel in value.topology
        )

    return bool(witnesses) and all(
        physical(witness) == physical(witnesses[0])
        for witness in witnesses[1:]
    )


def _l4_lambda_interval(
    query: AuditoryPathWitness,
    left: AuditoryPathWitness,
    right: AuditoryPathWitness,
    interval: tuple[float, float],
) -> tuple[float, float] | None:
    exact_lambda: Fraction | None = None
    banks = (
        (
            query.pressure_l4_field_tuples,
            left.pressure_l4_field_tuples,
            right.pressure_l4_field_tuples,
        ),
        (
            query.carrier_phase_advance_l4_field_tuples,
            left.carrier_phase_advance_l4_field_tuples,
            right.carrier_phase_advance_l4_field_tuples,
        ),
    )
    for query_bank, left_bank, right_bank in banks:
        if not (
            len(query_bank) == len(left_bank) == len(right_bank)
            == COCHLEAR_CHANNEL_COUNT
        ):
            return None
        for query_channel, left_channel, right_channel in zip(
            query_bank, left_bank, right_bank, strict=True
        ):
            if not (
                len(query_channel)
                == len(left_channel)
                == len(right_channel)
            ):
                return None
            for q_tuple, l_tuple, r_tuple in zip(
                query_channel, left_channel, right_channel, strict=True
            ):
                if not (
                    q_tuple.tuple_index
                    == l_tuple.tuple_index
                    == r_tuple.tuple_index
                    and tuple(name for name, _ in q_tuple.fields)
                    == DSF_FIELD_ORDER
                    and tuple(name for name, _ in l_tuple.fields)
                    == DSF_FIELD_ORDER
                    and tuple(name for name, _ in r_tuple.fields)
                    == DSF_FIELD_ORDER
                ):
                    return None
                for (_, q_value), (_, l_value), (_, r_value) in zip(
                    q_tuple.fields,
                    l_tuple.fields,
                    r_tuple.fields,
                    strict=True,
                ):
                    difference = r_value - l_value
                    if difference == 0:
                        if q_value != l_value:
                            return None
                        continue
                    candidate = (q_value - l_value) / difference
                    if not 0 <= candidate <= 1:
                        return None
                    if exact_lambda is None:
                        exact_lambda = candidate
                    elif exact_lambda != candidate:
                        return None
    if exact_lambda is None:
        return interval
    encoded = float(exact_lambda)
    if not interval[0] <= encoded <= interval[1]:
        return None
    return (encoded, encoded)


def _joint_cell_contains_python(
    query: AuditoryPathWitness,
    left: AuditoryPathWitness,
    right: AuditoryPathWitness,
    *,
    max_work: int,
) -> tuple[bool | None, int]:
    """Evaluate one directed joint cell by monotone free-space reachability.

    Every reachable dynamic-programming state carries the still-feasible
    interval of the *same* interpolation coordinate.  Thus changing the
    mixture independently at each time or field cannot manufacture a path.
    ``None`` is a fail-closed resource result, never a negative observation.
    """

    if not _same_topology(query, left, right):
        return False, 0
    reference_count = max(left.sample_count, right.sample_count)
    cell_count = query.sample_count * reference_count
    needs_recurrence = (
        query.sample_count != reference_count
        and left.structural_fingerprint == right.structural_fingerprint
    )
    recurrence_checks = (
        reference_count * (reference_count - 1) // 2
        if needs_recurrence
        else 0
    )
    work_count = cell_count + recurrence_checks
    if work_count > max_work:
        return None, work_count
    l4_interval = _l4_lambda_interval(
        query, left, right, (0.0, 1.0)
    )
    if l4_interval is None:
        return False, work_count
    pressure_uncertainty = 2.0 * float(PCM_PRESSURE_QUANTUM)

    def direct_state_equivalent(first: int, second: int) -> bool:
        """Physical recurrence in one witnessed path creates a real loop."""
        if left.structural_fingerprint != right.structural_fingerprint:
            return False
        for port_index in range(len(left.topology)):
            first_pressure, first_phase = _interpolated_sample(
                left, port_index, first, reference_count
            )
            second_pressure, second_phase = _interpolated_sample(
                left, port_index, second, reference_count
            )
            if abs(first_pressure - second_pressure) > pressure_uncertainty:
                return False
            if first == 0 or second == 0:
                continue
            uncertainty = _phase_uncertainty(
                first_pressure,
                _interpolated_phase_prior_pressure(
                    left, port_index, first, reference_count
                ),
                second_pressure,
                _interpolated_phase_prior_pressure(
                    left, port_index, second, reference_count
                ),
            )
            if uncertainty is not None and abs(first_phase - second_phase) > uncertainty:
                return False
        return True

    recurrence_incoming: list[tuple[int, ...]] = [
        () for _ in range(reference_count)
    ]
    if needs_recurrence:
        mutable_incoming: list[list[int]] = [
            [] for _ in range(reference_count)
        ]
        for later in range(2, reference_count):
            for earlier in range(later - 2, -1, -1):
                if direct_state_equivalent(earlier, later):
                    # Skip a witnessed closed recurrence when the query is
                    # faster, or traverse it again when the query is slower.
                    mutable_incoming[later].append(earlier)
                    mutable_incoming[earlier + 1].append(later)
                    break
        recurrence_incoming = [tuple(value) for value in mutable_incoming]

    def local_interval(
        query_index: int, reference_index: int
    ) -> tuple[float, float] | None:
        interval: tuple[float, float] | None = l4_interval
        for port_index in range(len(query.topology)):
            query_pressure, query_phase = _interpolated_sample(
                query, port_index, query_index, query.sample_count
            )
            left_pressure, left_phase = _interpolated_sample(
                left, port_index, reference_index, reference_count
            )
            right_pressure, right_phase = _interpolated_sample(
                right, port_index, reference_index, reference_count
            )
            interval = _intersect_lambda(
                interval,
                query=query_pressure,
                left=left_pressure,
                right=right_pressure,
                uncertainty=pressure_uncertainty,
            )
            if interval is None:
                return None
            if query_index == 0 or reference_index == 0:
                continue
            phase_uncertainty = _phase_uncertainty(
                query_pressure,
                _interpolated_phase_prior_pressure(
                    query, port_index, query_index, query.sample_count
                ),
                left_pressure,
                _interpolated_phase_prior_pressure(
                    left, port_index, reference_index, reference_count
                ),
                right_pressure,
                _interpolated_phase_prior_pressure(
                    right, port_index, reference_index, reference_count
                ),
            )
            if phase_uncertainty is None:
                # Phase is physically unresolved at the PCM quantum.  It is
                # not assigned a fabricated value or used as negative proof.
                continue
            interval = _intersect_lambda(
                interval,
                query=query_phase,
                left=left_phase,
                right=right_phase,
                uncertainty=phase_uncertainty,
            )
            if interval is None:
                return None
        return interval

    def intersect_many(
        intervals: tuple[tuple[float, float], ...],
        local: tuple[float, float],
    ) -> tuple[tuple[float, float], ...] | None:
        clipped = []
        for lower, upper in intervals:
            candidate = (
                max(lower, local[0]), min(upper, local[1])
            )
            if candidate[0] <= candidate[1]:
                clipped.append(candidate)
        if not clipped:
            return ()
        clipped.sort()
        merged = [clipped[0]]
        for lower, upper in clipped[1:]:
            prior_lower, prior_upper = merged[-1]
            if lower <= prior_upper:
                merged[-1] = (prior_lower, max(prior_upper, upper))
            else:
                merged.append((lower, upper))
        if len(merged) > MAX_INTERVAL_COMPONENTS_PER_CELL:
            return None
        return tuple(merged)

    previous: list[tuple[tuple[float, float], ...]] = [
        () for _ in range(reference_count)
    ]
    for query_index in range(query.sample_count):
        current: list[tuple[tuple[float, float], ...]] = [
            () for _ in range(reference_count)
        ]
        for reference_index in range(reference_count):
            if query_index == 0 and reference_index == 0:
                predecessors = (l4_interval,)
            else:
                predecessor_values = []
                if query_index > 0:
                    predecessor_values.extend(previous[reference_index])
                if reference_index > 0:
                    predecessor_values.extend(current[reference_index - 1])
                if query_index > 0 and reference_index > 0:
                    predecessor_values.extend(previous[reference_index - 1])
                if query_index > 0:
                    for recurrent_predecessor in recurrence_incoming[
                        reference_index
                    ]:
                        predecessor_values.extend(
                            previous[recurrent_predecessor]
                        )
                predecessors = tuple(predecessor_values)
            if not predecessors:
                continue
            local = local_interval(query_index, reference_index)
            if local is None:
                continue
            reachable = intersect_many(predecessors, local)
            if reachable is None:
                return None, work_count
            current[reference_index] = reachable
        previous = current
    return bool(previous[-1]), work_count


def _native_port_values(
    witness: AuditoryPathWitness,
) -> list[list[float]]:
    """Unpack the exact stored binary64 pairs for the native pure function."""
    return [
        list(struct.unpack(f"<{witness.sample_count * 2}d", values))
        for values in witness.packed_samples
    ]


def _joint_cell_contains_native(
    query: AuditoryPathWitness,
    left: AuditoryPathWitness,
    right: AuditoryPathWitness,
    *,
    max_work: int,
) -> tuple[bool | None, int]:
    """Run the exact sample-path recurrence after Python resolves exact L4."""
    if _native_joint_path_contains is None:
        raise RuntimeError("native auditory joint-path kernel is unavailable")
    if not _same_topology(query, left, right):
        return False, 0
    reference_count = max(left.sample_count, right.sample_count)
    cell_count = query.sample_count * reference_count
    needs_recurrence = (
        query.sample_count != reference_count
        and left.structural_fingerprint == right.structural_fingerprint
    )
    recurrence_checks = (
        reference_count * (reference_count - 1) // 2
        if needs_recurrence
        else 0
    )
    work_count = cell_count + recurrence_checks
    if work_count > max_work:
        return None, work_count
    l4_interval = _l4_lambda_interval(
        query, left, right, (0.0, 1.0)
    )
    if l4_interval is None:
        return False, work_count
    matched = _native_joint_path_contains(
        _native_port_values(query),
        query.sample_count,
        _native_port_values(left),
        left.sample_count,
        _native_port_values(right),
        right.sample_count,
        left.structural_fingerprint == right.structural_fingerprint,
        l4_interval[0],
        l4_interval[1],
        MAX_INTERVAL_COMPONENTS_PER_CELL,
    )
    if matched is not None and not isinstance(matched, bool):
        raise RuntimeError("native auditory joint-path kernel changed result type")
    return matched, work_count


def _joint_cell_contains(
    query: AuditoryPathWitness,
    left: AuditoryPathWitness,
    right: AuditoryPathWitness,
    *,
    max_work: int,
) -> tuple[bool | None, int]:
    """Select native execution only when its exact symbol is installed."""
    if _native_joint_path_contains is None:
        return _joint_cell_contains_python(
            query, left, right, max_work=max_work
        )
    return _joint_cell_contains_native(
        query, left, right, max_work=max_work
    )


def _class_contains(
    learned: AuditoryReciprocalClass,
    query: AuditoryPathWitness,
    *,
    max_work: int,
) -> tuple[bool | None, int]:
    branches = learned.branches
    if any(
        branch.structural_fingerprint == query.structural_fingerprint
        for branch in branches
    ):
        return True, 0
    consumed = 0
    for left in range(len(branches)):
        for right in range(left, len(branches)):
            matched, cells = _joint_cell_contains(
                query,
                branches[left],
                branches[right],
                max_work=max_work - consumed,
            )
            if matched is None:
                return None, consumed
            consumed += cells
            if matched:
                return True, consumed
    return False, consumed


def _component_topology_snapshot(value: AuditoryComponentTopology) -> dict:
    return {
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "coordinates": [list(item) for item in value.coordinates],
        "kernel_basin_receipt_sha256": value.kernel_basin_receipt_sha256,
        "l0_l4_trace_receipt_sha256": value.l0_l4_trace_receipt_sha256,
        "physical_quantity": value.physical_quantity,
        "physical_unit": value.physical_unit,
        "sensor_id": value.sensor_id,
        "source_stream_receipt_sha256": value.source_stream_receipt_sha256,
        "substream_id": value.substream_id,
        "topology_index": value.topology_index,
    }


def _channel_topology_snapshot(value: AuditoryChannelTopology) -> dict:
    return {
        "carrier_phase_advance": _component_topology_snapshot(
            value.carrier_phase_advance
        ),
        "channel_id": value.channel_id,
        "cochlear_index": value.cochlear_index,
        "pair_receipt_sha256": value.pair_receipt_sha256,
        "pressure": _component_topology_snapshot(value.pressure),
    }


def _l4_snapshot(value: PackedL4Tuple) -> dict:
    return {
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "fields": [[name, _fraction_text(field)] for name, field in value.fields],
        "tuple_index": value.tuple_index,
    }


def _witness_snapshot(value: AuditoryPathWitness) -> dict:
    return {
        "causal_offset_start": _fraction_text(value.causal_offset_start),
        "causal_offset_step": _fraction_text(value.causal_offset_step),
        "carrier_phase_advance_l4_field_tuples": [
            [_l4_snapshot(field_tuple) for field_tuple in channel]
            for channel in value.carrier_phase_advance_l4_field_tuples
        ],
        "experience_id": value.experience_id,
        "packed_samples": [
            base64.b64encode(samples).decode("ascii")
            for samples in value.packed_samples
        ],
        "pressure_l4_field_tuples": [
            [_l4_snapshot(field_tuple) for field_tuple in channel]
            for channel in value.pressure_l4_field_tuples
        ],
        "sample_count": value.sample_count,
        "source_indices": list(value.source_indices),
        "source_time_start": _fraction_text(value.source_time_start),
        "structural_fingerprint": value.structural_fingerprint,
        "topology": [
            _channel_topology_snapshot(channel) for channel in value.topology
        ],
    }


def _snapshot_for(
    classes: Mapping[AuditoryReciprocityKind, Mapping[str, AuditoryReciprocalClass]],
    *,
    class_capacity: int,
    tutor_authority_required: bool,
) -> dict:
    return {
        "branch_capacity_per_class": MAX_PATH_BRANCHES_PER_CLASS,
        "class_capacity_per_kind": class_capacity,
        "classes": [
            {
                "admission_receipts": [
                    receipt.as_dict() for receipt in learned.admission_receipts
                ],
                "admission_evidence_sha256": list(
                    learned.admission_evidence_sha256
                ),
                "authority_receipts": [
                    receipt.as_dict() for receipt in learned.authority_receipts
                ],
                "branches": [_witness_snapshot(item) for item in learned.branches],
                "first_experience_id": learned.first_experience_id,
                "kind": kind.value,
                "last_experience_id": learned.last_experience_id,
                "reinforcement_count": learned.reinforcement_count,
                "tutor_label": learned.tutor_label,
            }
            for kind in AuditoryReciprocityKind
            for learned in sorted(
                classes[kind].values(), key=lambda item: item.tutor_label
            )
        ],
        "schema": AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        "source_continuity": "unavailable_without_receipted_stream_authority",
        "tutor_authority_required": tutor_authority_required,
    }


def _envelope(snapshot: dict) -> dict:
    payload = json.dumps(
        snapshot,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(payload) > MAX_DECODED_SNAPSHOT_BYTES:
        raise RuntimeError("auditory causal-path decoded snapshot capacity is full")
    compressed = gzip.compress(payload, compresslevel=6, mtime=0)
    return {
        "encoding": "gzip+base64",
        "payload": base64.b64encode(compressed).decode("ascii"),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "schema": AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
    }


def _restore_component_topology(
    value: object, name: str
) -> AuditoryComponentTopology:
    if not isinstance(value, dict):
        raise ValueError(f"{name} is malformed")
    topology_index = value.get("topology_index")
    coordinates_raw = value.get("coordinates")
    if (
        isinstance(topology_index, bool)
        or not isinstance(topology_index, int)
        or topology_index < 0
        or not isinstance(coordinates_raw, list)
        or not coordinates_raw
    ):
        raise ValueError(f"{name} is malformed")
    coordinates = tuple(
        (str(item[0]), str(item[1]))
        for item in coordinates_raw
        if isinstance(item, list) and len(item) == 2
    )
    if len(coordinates) != len(coordinates_raw):
        raise ValueError(f"{name} coordinates are malformed")
    result = AuditoryComponentTopology(
        sensor_id=str(value.get("sensor_id", "")),
        substream_id=str(value.get("substream_id", "")),
        topology_index=topology_index,
        coordinates=coordinates,
        physical_quantity=str(value.get("physical_quantity", "")),
        physical_unit=str(value.get("physical_unit", "")),
        source_stream_receipt_sha256=sha256_digest(
            value.get("source_stream_receipt_sha256"),
            f"{name} source stream receipt",
        ),
        l0_l4_trace_receipt_sha256=sha256_digest(
            value.get("l0_l4_trace_receipt_sha256"),
            f"{name} L0-L4 trace receipt",
        ),
        kernel_basin_receipt_sha256=sha256_digest(
            value.get("kernel_basin_receipt_sha256"),
            f"{name} kernel basin receipt",
        ),
        authority_receipt_sha256=sha256_digest(
            value.get("authority_receipt_sha256"),
            f"{name} component receipt",
        ),
    )
    if not all((result.sensor_id, result.substream_id,
                result.physical_quantity, result.physical_unit)):
        raise ValueError(f"{name} identifiers are empty")
    return result


def _restore_channel_topology(
    value: object, name: str
) -> AuditoryChannelTopology:
    if not isinstance(value, dict) or set(value) != {
        "carrier_phase_advance",
        "channel_id",
        "cochlear_index",
        "pair_receipt_sha256",
        "pressure",
    }:
        raise ValueError(f"{name} is malformed")
    cochlear_index = value.get("cochlear_index")
    channel_id = value.get("channel_id")
    if (
        isinstance(cochlear_index, bool)
        or not isinstance(cochlear_index, int)
        or not 0 <= cochlear_index < COCHLEAR_CHANNEL_COUNT
        or not isinstance(channel_id, str)
        or not channel_id
    ):
        raise ValueError(f"{name} identity is malformed")
    return AuditoryChannelTopology(
        cochlear_index=cochlear_index,
        channel_id=channel_id,
        pressure=_restore_component_topology(
            value.get("pressure"), f"{name}.pressure"
        ),
        carrier_phase_advance=_restore_component_topology(
            value.get("carrier_phase_advance"),
            f"{name}.carrier_phase_advance",
        ),
        pair_receipt_sha256=sha256_digest(
            value.get("pair_receipt_sha256"), f"{name} pair receipt"
        ),
    )


def _restore_l4(value: object, name: str) -> PackedL4Tuple:
    if not isinstance(value, dict):
        raise ValueError(f"{name} is malformed")
    tuple_index = value.get("tuple_index")
    fields_raw = value.get("fields")
    if (
        isinstance(tuple_index, bool)
        or not isinstance(tuple_index, int)
        or tuple_index < 0
        or not isinstance(fields_raw, list)
    ):
        raise ValueError(f"{name} is malformed")
    fields = tuple(
        (str(item[0]), _fraction(item[1], f"{name}.{item[0]}"))
        for item in fields_raw
        if isinstance(item, list) and len(item) == 2
    )
    if len(fields) != len(fields_raw) or tuple(n for n, _ in fields) != DSF_FIELD_ORDER:
        raise ValueError(f"{name} field order changed")
    return PackedL4Tuple(
        tuple_index=tuple_index,
        fields=fields,
        authority_receipt_sha256=sha256_digest(
            value.get("authority_receipt_sha256"), f"{name} receipt"
        ),
    )


def _restore_witness(value: object, name: str) -> AuditoryPathWitness:
    if not isinstance(value, dict):
        raise ValueError(f"{name} is malformed")
    sample_count = value.get("sample_count")
    topology_raw = value.get("topology")
    samples_raw = value.get("packed_samples")
    pressure_l4_raw = value.get("pressure_l4_field_tuples")
    phase_l4_raw = value.get("carrier_phase_advance_l4_field_tuples")
    source_indices_raw = value.get("source_indices")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count <= 0
        or not isinstance(topology_raw, list)
        or len(topology_raw) != COCHLEAR_CHANNEL_COUNT
        or not isinstance(samples_raw, list)
        or not isinstance(pressure_l4_raw, list)
        or not isinstance(phase_l4_raw, list)
        or not len(topology_raw) == len(samples_raw)
        == len(pressure_l4_raw) == len(phase_l4_raw)
        or not isinstance(source_indices_raw, list)
        or len(source_indices_raw) != sample_count
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in source_indices_raw
        )
        or sample_count > MAX_NATIVE_SAMPLES_PER_SUBSTREAM
    ):
        raise ValueError(f"{name} is malformed")
    topology = tuple(
        _restore_channel_topology(item, f"{name}.topology[{index}]")
        for index, item in enumerate(topology_raw)
    )
    if tuple(channel.cochlear_index for channel in topology) != tuple(
        range(COCHLEAR_CHANNEL_COUNT)
    ):
        raise ValueError(f"{name} topology is reordered")
    packed = []
    for index, item in enumerate(samples_raw):
        if not isinstance(item, str):
            raise ValueError(f"{name}.packed_samples[{index}] is malformed")
        try:
            decoded = base64.b64decode(item, validate=True)
        except Exception as exc:
            raise ValueError(
                f"{name}.packed_samples[{index}] cannot be decoded"
            ) from exc
        if len(decoded) != sample_count * 16:
            raise ValueError(f"{name}.packed_samples[{index}] changed cardinality")
        if any(not math.isfinite(number) for number in struct.unpack(
            f"<{sample_count * 2}d", decoded
        )):
            raise ValueError(f"{name}.packed_samples[{index}] is not finite")
        packed.append(decoded)
    def restore_l4_bank(
        raw_bank: list[object], bank_name: str
    ) -> tuple[tuple[PackedL4Tuple, ...], ...]:
        restored_channels = []
        for channel_index, raw_channel in enumerate(raw_bank):
            if not isinstance(raw_channel, list) or not raw_channel:
                raise ValueError(
                    f"{name}.{bank_name}[{channel_index}] is malformed"
                )
            restored_channel = tuple(
                _restore_l4(
                    item,
                    f"{name}.{bank_name}[{channel_index}][{index}]",
                )
                for index, item in enumerate(raw_channel)
            )
            if tuple(item.tuple_index for item in restored_channel) != tuple(
                range(len(restored_channel))
            ):
                raise ValueError(f"{name}.{bank_name} is reordered")
            restored_channels.append(restored_channel)
        return tuple(restored_channels)

    pressure_l4 = restore_l4_bank(
        pressure_l4_raw, "pressure_l4_field_tuples"
    )
    phase_l4 = restore_l4_bank(
        phase_l4_raw, "carrier_phase_advance_l4_field_tuples"
    )
    return AuditoryPathWitness(
        experience_id=sha256_digest(
            value.get("experience_id"), f"{name} experience id"
        ),
        structural_fingerprint=sha256_digest(
            value.get("structural_fingerprint"), f"{name} fingerprint"
        ),
        topology=topology,
        sample_count=sample_count,
        source_indices=tuple(source_indices_raw),
        source_time_start=_fraction(
            value.get("source_time_start"), f"{name} source time start"
        ),
        causal_offset_start=_fraction(
            value.get("causal_offset_start"), f"{name} causal start"
        ),
        causal_offset_step=_fraction(
            value.get("causal_offset_step"), f"{name} causal step"
        ),
        packed_samples=tuple(packed),
        pressure_l4_field_tuples=pressure_l4,
        carrier_phase_advance_l4_field_tuples=phase_l4,
    )


class AuditoryReciprocityOwner:
    """Serial owner of bounded tutor-confirmed spoken causal paths."""

    def __init__(
        self,
        *,
        log_event: Callable[..., None],
        max_classes_per_kind: int = MAX_RECIPROCAL_CLASSES_PER_KIND,
        max_encoded_snapshot_bytes: int = MAX_ENCODED_SNAPSHOT_BYTES,
        tutor_authority: AuditoryTutorAuthority | None = None,
    ) -> None:
        if max_classes_per_kind <= 0:
            raise ValueError("auditory reciprocal class capacity must be positive")
        if max_encoded_snapshot_bytes <= 0:
            raise ValueError("auditory snapshot capacity must be positive")
        self._log_event = log_event
        self._max_classes_per_kind = int(max_classes_per_kind)
        self._max_encoded_snapshot_bytes = int(max_encoded_snapshot_bytes)
        self._tutor_authority = (
            tutor_authority
            if tutor_authority is not None
            else AuditoryTutorAuthority.from_environment()
        )
        if not isinstance(self._tutor_authority, AuditoryTutorAuthority):
            raise TypeError("auditory tutor authority has an invalid type")
        self._accepted_authority_nonces: set[str] = set()
        self._lock = threading.RLock()
        self._classes: dict[
            AuditoryReciprocityKind, dict[str, AuditoryReciprocalClass]
        ] = {kind: {} for kind in AuditoryReciprocityKind}
        self._encoded_snapshot_bytes = len(_envelope(self.snapshot())["payload"])
        self._resource_exhausted_recognitions = 0

    def _prospective_envelope(
        self,
        classes: Mapping[
            AuditoryReciprocityKind, Mapping[str, AuditoryReciprocalClass]
        ],
    ) -> dict:
        envelope = _envelope(_snapshot_for(
            classes,
            class_capacity=self._max_classes_per_kind,
            tutor_authority_required=self._tutor_authority.required,
        ))
        if len(envelope["payload"].encode("ascii")) > self._max_encoded_snapshot_bytes:
            raise RuntimeError("auditory causal-path snapshot capacity is full")
        return envelope

    def teach(
        self,
        experience: AuditoryL5Experience,
        *,
        kind: AuditoryReciprocityKind,
        tutor_label: str,
        authority_receipt: object | None = None,
    ) -> AuditoryReciprocalClass:
        if not isinstance(kind, AuditoryReciprocityKind):
            raise ValueError("auditory reciprocity kind is invalid")
        experience.verify()
        if experience.event_boundary != "utterance":
            raise ValueError(
                "auditory tutoring requires verified utterance boundary"
            )
        if kind is AuditoryReciprocityKind.SOURCE_CONTINUITY:
            raise ValueError(
                "monaural audio has no physical acoustic-source "
                "correspondence authority"
            )
        label = _label(tutor_label)
        witness = _pack_experience(experience)
        mounted_authority = None
        mounted_admission = None
        mounted_admission_evidence = None
        if authority_receipt is None:
            if self._tutor_authority.required:
                raise RuntimeError(
                    "auditory tutoring requires authenticated authority receipt"
                )
        elif not self._tutor_authority.required:
            raise ValueError(
                "unrequired auditory owner does not admit authority receipts"
            )
        else:
            mounted_authority = self._tutor_authority.verify(
                authority_receipt,
                experience_id=witness.experience_id,
                kind=kind.value,
                tutor_label=label,
            )
            l5_authority_payload = experience.receipt_registry.resolve(
                experience.authority_receipt_sha256,
                "auditory L5 tutor admission authority",
            )
            mounted_admission = self._tutor_authority.seal_admission(
                mounted_authority,
                experience_id=witness.experience_id,
                kind=kind.value,
                tutor_label=label,
                event_boundary=experience.event_boundary,
                l5_authority_receipt_sha256=(
                    experience.authority_receipt_sha256
                ),
                l5_authority_payload=l5_authority_payload,
            )
            _verify_l5_admission_evidence(
                mounted_admission, (witness,)
            )
            mounted_admission_evidence = _digest(
                _witness_admission_evidence(witness)
            )
        with self._lock:
            if (
                mounted_authority is not None
                and mounted_authority.nonce in self._accepted_authority_nonces
            ):
                raise RuntimeError("auditory tutor authority nonce was already used")
            existing = self._classes[kind].get(label)
            if existing is None:
                if len(self._classes[kind]) >= self._max_classes_per_kind:
                    raise RuntimeError(f"auditory {kind.value} class capacity is full")
                learned = AuditoryReciprocalClass(
                    kind=kind,
                    tutor_label=label,
                    branches=(witness,),
                    reinforcement_count=1,
                    first_experience_id=witness.experience_id,
                    last_experience_id=witness.experience_id,
                    authority_receipts=(
                        (mounted_authority,)
                        if mounted_authority is not None
                        else ()
                    ),
                    admission_receipts=(
                        (mounted_admission,)
                        if mounted_admission is not None
                        else ()
                    ),
                    admission_evidence_sha256=(
                        (mounted_admission_evidence,)
                        if mounted_admission_evidence is not None
                        else ()
                    ),
                )
            else:
                if not _same_topology(existing.branches[0], witness):
                    raise ValueError("auditory experience has a different physical topology")
                repeated = next((
                    item for item in existing.branches
                    if item.structural_fingerprint == witness.structural_fingerprint
                ), None)
                if repeated is None and len(existing.branches) >= MAX_PATH_BRANCHES_PER_CLASS:
                    raise RuntimeError("auditory spoken-form branch capacity is full")
                branches = (
                    existing.branches
                    if repeated is not None
                    else (*existing.branches, witness)
                )
                learned = AuditoryReciprocalClass(
                    kind=kind,
                    tutor_label=label,
                    branches=branches,
                    reinforcement_count=existing.reinforcement_count + 1,
                    first_experience_id=existing.first_experience_id,
                    last_experience_id=witness.experience_id,
                    authority_receipts=(
                        (*existing.authority_receipts, mounted_authority)
                        if mounted_authority is not None
                        else existing.authority_receipts
                    ),
                    admission_receipts=(
                        (*existing.admission_receipts, mounted_admission)
                        if mounted_admission is not None
                        else existing.admission_receipts
                    ),
                    admission_evidence_sha256=(
                        (
                            *existing.admission_evidence_sha256,
                            mounted_admission_evidence,
                        )
                        if mounted_admission_evidence is not None
                        else existing.admission_evidence_sha256
                    ),
                )
            prospective = {
                typed_kind: dict(values)
                for typed_kind, values in self._classes.items()
            }
            prospective[kind][label] = learned
            envelope = self._prospective_envelope(prospective)
            self._classes = prospective
            if mounted_authority is not None:
                self._accepted_authority_nonces.add(mounted_authority.nonce)
            self._encoded_snapshot_bytes = len(envelope["payload"].encode("ascii"))
        self._log_event(
            "auditory_causal_path_taught",
            branch_count=len(learned.branches),
            experience_id=witness.experience_id,
            kind=kind.value,
            reinforcement_count=learned.reinforcement_count,
            tutor_admission_receipted=mounted_admission is not None,
            tutor_authority_receipted=mounted_authority is not None,
            tutor_label=label,
        )
        return learned

    def issue_tutor_authority(
        self,
        *,
        experience_id: str,
        kind: AuditoryReciprocityKind,
        tutor_label: str,
    ) -> dict | None:
        """Issue one gateway receipt from this owner's mounted authority."""
        if not isinstance(kind, AuditoryReciprocityKind):
            raise ValueError("auditory reciprocity kind is invalid")
        if not self._tutor_authority.required:
            return None
        return self._tutor_authority.issue(
            experience_id=experience_id,
            kind=kind.value,
            tutor_label=tutor_label,
        ).as_dict()

    def recognize_bounded(
        self,
        experience: AuditoryL5Experience,
        *,
        kind: AuditoryReciprocityKind,
        max_work: int,
    ) -> tuple[AuditoryRecognition, int]:
        """Recognize under an exact caller-owned cumulative work grant.

        The returned cell count is the authority actually consumed.  A caller
        may pass its remaining grant across several candidate gates without
        multiplying the existing recognition boundary.
        """
        if not isinstance(kind, AuditoryReciprocityKind):
            raise ValueError("auditory reciprocity kind is invalid")
        if (
            isinstance(max_work, bool)
            or not isinstance(max_work, int)
            or max_work < 0
            or max_work > MAX_REACHABILITY_CELLS_PER_RECOGNITION
        ):
            raise ValueError("auditory recognition work authority is invalid")
        experience.verify()
        if kind is AuditoryReciprocityKind.SOURCE_CONTINUITY:
            candidates: tuple[str, ...] = ()
            candidate_class_receipts: tuple[str, ...] = ()
            exhausted = False
            consumed_cells = 0
        else:
            query = _pack_experience(experience)
            with self._lock:
                matched_classes = []
                consumed_cells = 0
                exhausted = False
                for learned in self._classes[kind].values():
                    matched, cells = _class_contains(
                        learned,
                        query,
                        max_work=(
                            max_work - consumed_cells
                        ),
                    )
                    if (
                        matched is None
                    ):
                        exhausted = True
                        break
                    consumed_cells += cells
                    if matched:
                        matched_classes.append(learned)
                if exhausted:
                    candidates = ()
                    candidate_class_receipts = ()
                else:
                    ordered_matches = tuple(sorted(
                        matched_classes,
                        key=lambda value: value.tutor_label,
                    ))
                    candidates = tuple(
                        value.tutor_label for value in ordered_matches
                    )
                    candidate_class_receipts = tuple(sorted(
                        _class_authority_receipt(value)
                        for value in ordered_matches
                    ))
        state = (
            AuditoryRecognitionState.INDETERMINATE
            if exhausted
            else AuditoryRecognitionState.UNKNOWN
            if not candidates
            else AuditoryRecognitionState.UNIQUE
            if len(candidates) == 1
            else AuditoryRecognitionState.AMBIGUOUS
        )
        selected_class_receipt = (
            candidate_class_receipts[0]
            if state is AuditoryRecognitionState.UNIQUE else None
        )
        occurrence_payload = {
            "candidate_class_authority_receipts": list(
                candidate_class_receipts
            ),
            "experience_id": experience.experience_id,
            "kind": kind.value,
            "l5_authority_receipt_sha256": (
                experience.authority_receipt_sha256
            ),
            "operator": AUDITORY_RECOGNITION_OPERATOR,
            "schema": AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA,
            "selected_class_authority_receipt_sha256": (
                selected_class_receipt
            ),
            "state": state.value,
            "structural_fingerprint": experience.structural_fingerprint,
        }
        occurrence = AuditoryRecognitionOccurrence(
            kind=kind,
            state=state,
            experience_id=experience.experience_id,
            structural_fingerprint=experience.structural_fingerprint,
            l5_authority_receipt_sha256=(
                experience.authority_receipt_sha256
            ),
            candidate_class_authority_receipts=(
                candidate_class_receipts
            ),
            selected_class_authority_receipt_sha256=(
                selected_class_receipt
            ),
            operator=AUDITORY_RECOGNITION_OPERATOR,
            authority_receipt_sha256=_digest(occurrence_payload),
        )
        occurrence.verify()
        result = AuditoryRecognition(
            kind=kind,
            state=state,
            tutor_label=(
                candidates[0]
                if state is AuditoryRecognitionState.UNIQUE else None
            ),
            candidate_labels=candidates,
            experience_id=experience.experience_id,
            occurrence=occurrence,
        )
        if exhausted:
            with self._lock:
                self._resource_exhausted_recognitions += 1
        self._log_event(
            "auditory_causal_path_recognized",
            candidate_count=len(candidates),
            experience_id=experience.experience_id,
            kind=kind.value,
            resource_exhausted=exhausted,
            state=state.value,
        )
        return result, consumed_cells

    def recognize(
        self,
        experience: AuditoryL5Experience,
        *,
        kind: AuditoryReciprocityKind,
    ) -> AuditoryRecognition:
        result, _consumed_cells = self.recognize_bounded(
            experience,
            kind=kind,
            max_work=MAX_REACHABILITY_CELLS_PER_RECOGNITION,
        )
        return result

    def recognize_all(
        self, experience: AuditoryL5Experience
    ) -> tuple[AuditoryRecognition, ...]:
        return tuple(
            self.recognize(experience, kind=kind)
            for kind in AuditoryReciprocityKind
        )

    def snapshot(self) -> dict:
        with self._lock:
            return _snapshot_for(
                self._classes,
                class_capacity=self._max_classes_per_kind,
                tutor_authority_required=self._tutor_authority.required,
            )

    def encoded_snapshot(self) -> dict:
        envelope = _envelope(self.snapshot())
        if len(envelope["payload"].encode("ascii")) > self._max_encoded_snapshot_bytes:
            raise RuntimeError("auditory causal-path snapshot capacity is full")
        return envelope

    def restore_encoded(self, envelope: object) -> None:
        if not isinstance(envelope, dict):
            raise ValueError("auditory reciprocity envelope must be an object")
        if envelope.get("schema") == LEGACY_AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA:
            raise ValueError(
                "legacy auditory reciprocity v4 envelope is preserved but "
                "cannot be applied to paired v5 channels"
            )
        if (
            envelope.get("schema") != AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA
            or envelope.get("encoding") != "gzip+base64"
        ):
            raise ValueError("auditory reciprocity envelope is invalid")
        encoded = envelope.get("payload")
        expected_digest = envelope.get("payload_sha256")
        if (
            not isinstance(encoded, str)
            or len(encoded.encode("ascii", errors="ignore"))
            > self._max_encoded_snapshot_bytes
            or not isinstance(expected_digest, str)
        ):
            raise ValueError("auditory reciprocity envelope exceeds its boundary")
        try:
            compressed = base64.b64decode(encoded, validate=True)
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
                payload = stream.read(MAX_DECODED_SNAPSHOT_BYTES + 1)
            if len(payload) > MAX_DECODED_SNAPSHOT_BYTES:
                raise ValueError("auditory reciprocity decoded snapshot is oversized")
            snapshot = json.loads(payload)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("auditory reciprocity envelope cannot be decoded") from exc
        if hashlib.sha256(payload).hexdigest() != expected_digest:
            raise ValueError("auditory reciprocity envelope failed integrity check")
        self.restore(snapshot)

    def restore(self, snapshot: object) -> None:
        if not isinstance(snapshot, dict):
            raise ValueError("auditory reciprocity snapshot must be an object")
        if snapshot.get("schema") == LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA:
            raise ValueError(
                "legacy auditory reciprocity v4 snapshot is preserved but "
                "cannot be applied to paired v5 channels"
            )
        if snapshot.get("schema") != AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA:
            raise ValueError("auditory reciprocity snapshot schema is invalid")
        if (
            snapshot.get("class_capacity_per_kind") != self._max_classes_per_kind
            or snapshot.get("branch_capacity_per_class")
            != MAX_PATH_BRANCHES_PER_CLASS
            or snapshot.get("source_continuity")
            != "unavailable_without_receipted_stream_authority"
            or snapshot.get("tutor_authority_required")
            is not self._tutor_authority.required
        ):
            raise ValueError("auditory reciprocity capacity or authority changed")
        raw_classes = snapshot.get("classes")
        if not isinstance(raw_classes, list):
            raise ValueError("auditory reciprocity classes are malformed")
        restored: dict[
            AuditoryReciprocityKind, dict[str, AuditoryReciprocalClass]
        ] = {kind: {} for kind in AuditoryReciprocityKind}
        restored_authority_nonces: set[str] = set()
        for class_index, value in enumerate(raw_classes):
            if not isinstance(value, dict):
                raise ValueError("auditory reciprocal class is malformed")
            try:
                kind = AuditoryReciprocityKind(str(value.get("kind")))
            except ValueError as exc:
                raise ValueError("auditory reciprocal class kind is invalid") from exc
            if kind is not AuditoryReciprocityKind.SPOKEN_FORM:
                raise ValueError("monaural snapshot asserts source identity")
            label = _label(value.get("tutor_label"))
            if label in restored[kind] or len(restored[kind]) >= self._max_classes_per_kind:
                raise ValueError("auditory reciprocal snapshot exceeds class capacity")
            raw_branches = value.get("branches")
            if (
                not isinstance(raw_branches, list)
                or not 0 < len(raw_branches) <= MAX_PATH_BRANCHES_PER_CLASS
            ):
                raise ValueError("auditory reciprocal branches exceed capacity")
            branches = tuple(
                _restore_witness(
                    item, f"auditory.class[{class_index}].branch[{index}]"
                )
                for index, item in enumerate(raw_branches)
            )
            if not _same_topology(*branches):
                raise ValueError("auditory reciprocal branches changed topology")
            if len({item.structural_fingerprint for item in branches}) != len(branches):
                raise ValueError("auditory reciprocal branch is duplicated")
            if any(
                _witness_structural_fingerprint(branch)
                != branch.structural_fingerprint
                for branch in branches
            ):
                raise ValueError(
                    "auditory persisted witness structural field changed"
                )
            count = value.get("reinforcement_count")
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count < len(branches)
            ):
                raise ValueError("auditory reinforcement count is invalid")
            raw_authority_receipts = value.get("authority_receipts")
            raw_admission_receipts = value.get("admission_receipts")
            raw_admission_evidence = value.get("admission_evidence_sha256")
            if not isinstance(raw_authority_receipts, list):
                raise ValueError("auditory tutor authority receipts are malformed")
            if not isinstance(raw_admission_receipts, list):
                raise ValueError("auditory tutor admission receipts are malformed")
            if not isinstance(raw_admission_evidence, list):
                raise ValueError("auditory tutor admission evidence is malformed")
            admission_evidence = tuple(
                sha256_digest(
                    item, "auditory tutor ordered admission evidence"
                )
                for item in raw_admission_evidence
            )
            if self._tutor_authority.required:
                if (
                    len(raw_authority_receipts) != count
                    or len(raw_admission_receipts) != count
                    or len(admission_evidence) != count
                ):
                    raise ValueError(
                        "auditory reinforcement lacks tutor admission authority"
                    )
            elif (
                raw_authority_receipts
                or raw_admission_receipts
                or admission_evidence
            ):
                raise ValueError(
                    "unrequired auditory snapshot contains authority receipts"
                )
            authority_receipts = tuple(
                self._tutor_authority.verify(
                    item,
                    experience_id=AuditoryTutorAuthorityReceipt.from_payload(
                        item
                    ).experience_id,
                    kind=kind.value,
                    tutor_label=label,
                )
                for item in raw_authority_receipts
            )
            admission_receipts = tuple(
                self._tutor_authority.verify_admission(
                    admission_item,
                    authority_receipt,
                    experience_id=authority_receipt.experience_id,
                    kind=kind.value,
                    tutor_label=label,
                )
                for admission_item, authority_receipt in zip(
                    raw_admission_receipts,
                    authority_receipts,
                    strict=True,
                )
            )
            for admission, evidence_sha256 in zip(
                admission_receipts, admission_evidence, strict=True
            ):
                _verify_l5_admission_evidence(
                    admission,
                    branches,
                    witnesses_verified=True,
                    expected_evidence_sha256=evidence_sha256,
                )
            for receipt in authority_receipts:
                if receipt.nonce in restored_authority_nonces:
                    raise ValueError("auditory tutor authority nonce is duplicated")
                restored_authority_nonces.add(receipt.nonce)
            first_id = sha256_digest(
                value.get("first_experience_id"), "auditory first experience id"
            )
            last_id = sha256_digest(
                value.get("last_experience_id"), "auditory last experience id"
            )
            if first_id != branches[0].experience_id:
                raise ValueError("auditory first experience reference changed")
            if last_id not in {item.experience_id for item in branches}:
                # Repeated reinforcement may reference an already-stored branch.
                if count == len(branches):
                    raise ValueError("auditory last experience reference changed")
            if authority_receipts:
                authority_experience_ids = tuple(
                    receipt.experience_id for receipt in authority_receipts
                )
                if (
                    authority_experience_ids[0] != first_id
                    or authority_experience_ids[-1] != last_id
                    or not {
                        branch.experience_id for branch in branches
                    }.issubset(authority_experience_ids)
                ):
                    raise ValueError(
                        "auditory tutor authority history changed"
                    )
            restored[kind][label] = AuditoryReciprocalClass(
                kind=kind,
                tutor_label=label,
                branches=branches,
                reinforcement_count=count,
                first_experience_id=first_id,
                last_experience_id=last_id,
                authority_receipts=authority_receipts,
                admission_receipts=admission_receipts,
                admission_evidence_sha256=admission_evidence,
            )
        envelope = self._prospective_envelope(restored)
        with self._lock:
            self._classes = restored
            self._accepted_authority_nonces = restored_authority_nonces
            self._encoded_snapshot_bytes = len(envelope["payload"].encode("ascii"))
        self._log_event(
            "auditory_causal_path_restored",
            class_count=sum(len(value) for value in restored.values()),
        )

    def status(self) -> dict:
        with self._lock:
            return {
                "branch_capacity_per_class": MAX_PATH_BRANCHES_PER_CLASS,
                "branch_counts": {
                    kind.value: sum(
                        len(value.branches) for value in self._classes[kind].values()
                    )
                    for kind in AuditoryReciprocityKind
                },
                "class_capacity_per_kind": self._max_classes_per_kind,
                "class_counts": {
                    kind.value: len(self._classes[kind])
                    for kind in AuditoryReciprocityKind
                },
                "encoded_snapshot_bytes": self._encoded_snapshot_bytes,
                "encoded_snapshot_capacity_bytes": self._max_encoded_snapshot_bytes,
                "mechanism": "directed_joint_causal_path_complex",
                "tutor_authority_required": self._tutor_authority.required,
                "tutor_authority_nonce_count": len(
                    self._accepted_authority_nonces
                ),
                "reinforcements": {
                    kind.value: sum(
                        value.reinforcement_count
                        for value in self._classes[kind].values()
                    )
                    for kind in AuditoryReciprocityKind
                },
                "resource_exhausted_recognitions": (
                    self._resource_exhausted_recognitions
                ),
                "source_continuity": (
                    "unknown_without_physical_acoustic_source_correspondence"
                ),
            }


__all__ = (
    "AuditoryRecognition",
    "AuditoryRecognitionState",
    "AuditoryReciprocalClass",
    "AuditoryReciprocityKind",
    "AuditoryReciprocityOwner",
    "LegacyAuditoryReciprocityEnvelopeInspection",
    "LEGACY_AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA",
    "LEGACY_AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA",
    "MAX_ENCODED_SNAPSHOT_BYTES",
    "MAX_PATH_BRANCHES_PER_CLASS",
    "MAX_RECIPROCAL_CLASSES_PER_KIND",
    "inspect_legacy_v4_envelope",
)
