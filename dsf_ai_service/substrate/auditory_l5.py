"""Deterministic auditory L5 ownership of paired cochlear kernel fields.

The native auditory mount presents thirty-two interleaved L0--L4 streams:
pressure envelope then carrier-phase advance for each of sixteen physical
cochlear channels. Auditory L5 retains those streams independently and groups
only each physically corresponding pair. It does not project them back to a
single port, combine their L4 fields, infer a word or source, or use chi as
identity.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Callable

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    sha256_digest,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT,
    MAX_NATIVE_SOUND_SUBSTREAMS,
    MAX_NATIVE_SUBSTREAMS_PER_SENSE,
    PROFILE_PAYLOAD as NATIVE_SENSORY_AUTHORITY_PROFILE,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
    SensoryFullFieldBoundary,
    SensorySubstreamFullField,
    SixSenseFullFieldBoundary,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    AUDITORY_KERNEL_SENSOR_ID,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    COCHLEAR_ORDER,
    OBSERVATION_HOP_SAMPLES,
    PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP,
)


AUDITORY_L5_SCHEMA = "guala.auditory_l5.full_field.v3"
AUDITORY_L5_COMPONENT_SCHEMA = "guala.auditory_l5.kernel_component.v1"
AUDITORY_L5_PAIR_SCHEMA = "guala.auditory_l5.cochlear_pair.v1"
AUDITORY_L5_AUTHORITY_SCHEMA = "guala.auditory_l5.authority.v3"
AUDITORY_L5_AUTHORITY_PROFILE = b"guala.auditory_l5.authority.profile.v3"

_PRESSURE_COMPONENT_COORDINATE = "pressure-envelope"
_PHASE_ADVANCE_COMPONENT_COORDINATE = "carrier-phase-advance"
_PRESSURE_QUANTITY = "cochlear-pressure-envelope"
_PRESSURE_UNIT = "full-scale-pressure"
_PHASE_ADVANCE_QUANTITY = "cochlear-carrier-phase-advance"
_PHASE_ADVANCE_UNIT = "nyquist-fraction-per-observation-hop"

# Exact receipt-count boundary inherited from the native settlement limits.
# Each admitted substream has calibration, source, adapter, profile, trace,
# and basin receipts, plus one tuple receipt per admitted sample. The remaining
# terms are the exact shared provider, causal-window, six boundary/state,
# assembly, and L5-local authorities.
_MAX_SIX_SENSE_SUBSTREAMS = (
    MAX_NATIVE_SOUND_SUBSTREAMS
    + (len(SENSE_ORDER) - 1) * MAX_NATIVE_SUBSTREAMS_PER_SENSE
)
_UPSTREAM_SHARED_PROVIDER_RECEIPTS = 3
_UPSTREAM_FIXED_RECEIPTS_PER_SUBSTREAM = 6
_UPSTREAM_CAUSAL_WINDOW_RECEIPTS = 1
_UPSTREAM_BOUNDARY_RECEIPTS = 2 * len(SENSE_ORDER)
_UPSTREAM_ASSEMBLY_RECEIPTS = 1
_L5_LOCAL_RECEIPTS = (
    1
    + AUDITORY_KERNEL_COMPONENT_COUNT
    + COCHLEAR_CHANNEL_COUNT
    + 1
)
MAX_AUDITORY_L5_RECEIPT_RECORDS = (
    _UPSTREAM_SHARED_PROVIDER_RECEIPTS
    + _UPSTREAM_FIXED_RECEIPTS_PER_SUBSTREAM * _MAX_SIX_SENSE_SUBSTREAMS
    + MAX_NATIVE_SAMPLES_PER_SETTLEMENT
    + len(SENSE_ORDER)
    + _UPSTREAM_CAUSAL_WINDOW_RECEIPTS
    + _UPSTREAM_BOUNDARY_RECEIPTS
    + _UPSTREAM_ASSEMBLY_RECEIPTS
    + _L5_LOCAL_RECEIPTS
)


class AuditoryL5ComponentKind(str, Enum):
    PRESSURE = "pressure"
    CARRIER_PHASE_ADVANCE = "carrier_phase_advance"


def _fraction(value: object, name: str) -> Fraction:
    try:
        result = Fraction(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        raise ReceiptError(f"{name} is not an exact fraction") from exc
    return result


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "auditory L5 fraction")
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


def _binary64(value: Fraction, name: str) -> float:
    require_fraction(value, name)
    mounted = float(value)
    if not math.isfinite(mounted) or Fraction.from_float(mounted) != value:
        raise ReceiptError(f"{name} is not an exact finite provider binary64")
    return mounted


def _component_coordinate(kind: AuditoryL5ComponentKind) -> str:
    return (
        _PRESSURE_COMPONENT_COORDINATE
        if kind is AuditoryL5ComponentKind.PRESSURE
        else _PHASE_ADVANCE_COMPONENT_COORDINATE
    )


def _expected_coordinates(
    channel_index: int,
    kind: AuditoryL5ComponentKind,
) -> tuple[tuple[str, str], ...]:
    definition = AUDITORY_CHANNELS[channel_index]
    return (
        ("cochlear-channel", definition.name),
        ("kernel-component", _component_coordinate(kind)),
        ("centre-hz", str(definition.centre_hz)),
        ("erb-width-hz", str(definition.erb_width_hz)),
        ("gammatone-order", str(COCHLEAR_ORDER)),
        ("observation-hop-samples", str(OBSERVATION_HOP_SAMPLES)),
    )


@dataclass(frozen=True, slots=True)
class AuditoryL5ComponentSample:
    source_index: int
    source_time: Fraction
    causal_offset: Fraction
    signal: Fraction
    phase_turns: Fraction


@dataclass(frozen=True, slots=True)
class AuditoryL5FieldTuple:
    tuple_index: int
    fields: tuple[tuple[str, Fraction], ...]
    source_l0_l4_trace_receipt_sha256: str
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class AuditoryL5KernelComponent:
    kind: AuditoryL5ComponentKind
    sensor_id: str
    substream_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]
    physical_quantity: str
    physical_unit: str
    samples: tuple[AuditoryL5ComponentSample, ...]
    l4_field_tuples: tuple[AuditoryL5FieldTuple, ...]
    source_stream_receipt_sha256: str
    l0_l4_trace_receipt_sha256: str
    kernel_basin_receipt_sha256: str
    authority_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        _validate_component(self)
        payload = _component_payload(self)
        mounted = receipt_registry.resolve(
            self.authority_receipt_sha256,
            "auditory L5 kernel-component authority",
        )
        if (
            mounted != payload
            or receipt_sha256(payload) != self.authority_receipt_sha256
        ):
            raise ReceiptError("auditory L5 kernel component was altered")


@dataclass(frozen=True, slots=True)
class AuditoryL5CochlearChannel:
    cochlear_index: int
    channel_id: str
    pressure: AuditoryL5KernelComponent
    carrier_phase_advance: AuditoryL5KernelComponent
    pair_receipt_sha256: str

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        _validate_channel(self)
        self.pressure.verify(receipt_registry)
        self.carrier_phase_advance.verify(receipt_registry)
        payload = _pair_payload(self)
        mounted = receipt_registry.resolve(
            self.pair_receipt_sha256,
            "auditory L5 cochlear-pair authority",
        )
        if (
            mounted != payload
            or receipt_sha256(payload) != self.pair_receipt_sha256
        ):
            raise ReceiptError("auditory L5 cochlear pair was altered")


@dataclass(frozen=True, slots=True)
class AuditoryL5Experience:
    experience_id: str
    structural_fingerprint: str
    assembly_id: str
    relation: str
    event_boundary: str
    source_time_start: Fraction
    source_time_end: Fraction
    channels: tuple[AuditoryL5CochlearChannel, ...]
    assembly_receipt_sha256: str
    authority_receipt_sha256: str
    upstream_boundary: SixSenseFullFieldBoundary
    upstream_receipt_registry: ReceiptRegistry
    receipt_registry: ReceiptRegistry

    def verify(self) -> None:
        _verify_experience(
            self,
            verify_upstream=True,
        )


def _validate_sample(sample: AuditoryL5ComponentSample, index: int) -> None:
    if not isinstance(sample, AuditoryL5ComponentSample):
        raise ReceiptError("auditory L5 component sample is not typed")
    if sample.source_index != index:
        raise ReceiptError("auditory L5 source indices are not contiguous")
    for name, value in (
        ("source time", sample.source_time),
        ("causal offset", sample.causal_offset),
        ("signal", sample.signal),
        ("phase", sample.phase_turns),
    ):
        require_fraction(value, f"auditory L5 {name}")


def _validate_field_tuple(
    value: AuditoryL5FieldTuple,
    expected_index: int,
    expected_trace_receipt: str,
) -> None:
    if not isinstance(value, AuditoryL5FieldTuple):
        raise ReceiptError("auditory L5 L4 field tuple is not typed")
    if value.tuple_index != expected_index:
        raise ReceiptError("auditory L5 L4 tuple sequence is incomplete")
    if tuple(name for name, _field in value.fields) != DSF_FIELD_ORDER:
        raise ReceiptError("auditory L5 L4 field structure changed")
    for name, field in value.fields:
        require_fraction(field, f"auditory L5 L4 {name}")
    if value.source_l0_l4_trace_receipt_sha256 != expected_trace_receipt:
        raise ReceiptError("auditory L5 L4 tuple belongs to another trace")
    sha256_digest(
        value.authority_receipt_sha256,
        "auditory L5 L4 tuple receipt",
    )


def _validate_component(component: AuditoryL5KernelComponent) -> None:
    if not isinstance(component, AuditoryL5KernelComponent):
        raise ReceiptError("auditory L5 kernel component is not typed")
    if not isinstance(component.kind, AuditoryL5ComponentKind):
        raise ReceiptError("auditory L5 component kind is not typed")
    if not component.samples:
        raise ReceiptError("auditory L5 component samples are empty")
    previous_time: Fraction | None = None
    for index, sample in enumerate(component.samples):
        _validate_sample(sample, index)
        if sample.causal_offset < 0:
            raise ReceiptError("auditory L5 component precedes its causal window")
        if previous_time is not None and sample.source_time <= previous_time:
            raise ReceiptError("auditory L5 component grid is not causal")
        previous_time = sample.source_time
        signal = _binary64(sample.signal, "auditory L5 component signal")
        if component.kind is AuditoryL5ComponentKind.PRESSURE:
            if not 0.0 <= signal <= 1.0:
                raise ReceiptError("auditory L5 pressure left full scale")
            if sample.phase_turns != 0:
                raise ReceiptError("auditory L5 pressure component phase is not zero")
        else:
            phase = _binary64(sample.phase_turns, "auditory L5 component phase")
            if not -1.0 <= signal <= 1.0:
                raise ReceiptError("auditory L5 phase advance exceeded Nyquist")
            if not (
                -PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
                <= phase
                <= PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            ):
                raise ReceiptError("auditory L5 carrier phase exceeded Nyquist")
            if signal != phase / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP:
                raise ReceiptError(
                    "auditory L5 phase normalization differs from provider binary64"
                )
    if not component.l4_field_tuples:
        raise ReceiptError("auditory L5 component has no complete L4 field")
    for index, value in enumerate(component.l4_field_tuples):
        _validate_field_tuple(
            value,
            index,
            component.l0_l4_trace_receipt_sha256,
        )
    for name, value in (
        ("source stream", component.source_stream_receipt_sha256),
        ("L0-L4 trace", component.l0_l4_trace_receipt_sha256),
        ("kernel basin", component.kernel_basin_receipt_sha256),
        ("component authority", component.authority_receipt_sha256),
    ):
        sha256_digest(value, f"auditory L5 {name} receipt")


def _component_grid(
    component: AuditoryL5KernelComponent,
) -> tuple[tuple[int, Fraction, Fraction], ...]:
    return tuple(
        (sample.source_index, sample.source_time, sample.causal_offset)
        for sample in component.samples
    )


def _validate_channel(channel: AuditoryL5CochlearChannel) -> None:
    if not isinstance(channel, AuditoryL5CochlearChannel):
        raise ReceiptError("auditory L5 cochlear channel is not typed")
    if not 0 <= channel.cochlear_index < COCHLEAR_CHANNEL_COUNT:
        raise ReceiptError("auditory L5 cochlear index is invalid")
    definition = AUDITORY_CHANNELS[channel.cochlear_index]
    if channel.channel_id != definition.name:
        raise ReceiptError("auditory L5 cochlear channel identity changed")
    pressure = channel.pressure
    phase = channel.carrier_phase_advance
    if (
        pressure.kind is not AuditoryL5ComponentKind.PRESSURE
        or phase.kind is not AuditoryL5ComponentKind.CARRIER_PHASE_ADVANCE
    ):
        raise ReceiptError("auditory L5 cochlear pair is untyped or reordered")
    expected = (
        (
            pressure,
            channel.cochlear_index * 2,
            f"{definition.name}_pressure",
            _PRESSURE_QUANTITY,
            _PRESSURE_UNIT,
        ),
        (
            phase,
            channel.cochlear_index * 2 + 1,
            f"{definition.name}_phase_advance",
            _PHASE_ADVANCE_QUANTITY,
            _PHASE_ADVANCE_UNIT,
        ),
    )
    for component, topology_index, substream_id, quantity, unit in expected:
        if (
            component.sensor_id != AUDITORY_KERNEL_SENSOR_ID
            or component.substream_id != substream_id
            or component.topology_index != topology_index
            or component.coordinates
            != _expected_coordinates(channel.cochlear_index, component.kind)
            or component.physical_quantity != quantity
            or component.physical_unit != unit
        ):
            raise ReceiptError("auditory L5 kernel mount is not canonical v3")
        _validate_component(component)
    if _component_grid(pressure) != _component_grid(phase):
        raise ReceiptError("auditory L5 cochlear component grids differ")
    if (
        pressure.source_stream_receipt_sha256
        == phase.source_stream_receipt_sha256
        or pressure.l0_l4_trace_receipt_sha256
        == phase.l0_l4_trace_receipt_sha256
        or pressure.kernel_basin_receipt_sha256
        == phase.kernel_basin_receipt_sha256
        or pressure.authority_receipt_sha256 == phase.authority_receipt_sha256
    ):
        raise ReceiptError("auditory L5 cochlear components are not independent")
    sha256_digest(
        channel.pair_receipt_sha256,
        "auditory L5 cochlear pair receipt",
    )


def _validate_channels(
    channels: tuple[AuditoryL5CochlearChannel, ...],
) -> None:
    if (
        not isinstance(channels, tuple)
        or len(channels) != COCHLEAR_CHANNEL_COUNT
        or tuple(channel.cochlear_index for channel in channels)
        != tuple(range(COCHLEAR_CHANNEL_COUNT))
    ):
        raise ReceiptError("auditory L5 requires exactly 16 ordered cochlear pairs")
    for channel in channels:
        _validate_channel(channel)


def _sample_payload(sample: AuditoryL5ComponentSample) -> dict[str, object]:
    return {
        "causal_offset": _fraction_text(sample.causal_offset),
        "phase_turns": _fraction_text(sample.phase_turns),
        "signal": _fraction_text(sample.signal),
        "source_index": sample.source_index,
        "source_time": _fraction_text(sample.source_time),
    }


def _field_tuple_payload(value: AuditoryL5FieldTuple) -> dict[str, object]:
    return {
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "fields": [
            [name, _fraction_text(field)] for name, field in value.fields
        ],
        "source_l0_l4_trace_receipt_sha256": (
            value.source_l0_l4_trace_receipt_sha256
        ),
        "tuple_index": value.tuple_index,
    }


def _component_payload(component: AuditoryL5KernelComponent) -> bytes:
    return _canonical_bytes({
        "coordinates": [list(value) for value in component.coordinates],
        "kind": component.kind.value,
        "kernel_basin_receipt_sha256": (
            component.kernel_basin_receipt_sha256
        ),
        "l0_l4_trace_receipt_sha256": (
            component.l0_l4_trace_receipt_sha256
        ),
        "l4_field_tuples": [
            _field_tuple_payload(value) for value in component.l4_field_tuples
        ],
        "physical_quantity": component.physical_quantity,
        "physical_unit": component.physical_unit,
        "samples": [_sample_payload(value) for value in component.samples],
        "schema": AUDITORY_L5_COMPONENT_SCHEMA,
        "sensor_id": component.sensor_id,
        "source_stream_receipt_sha256": (
            component.source_stream_receipt_sha256
        ),
        "substream_id": component.substream_id,
        "topology_index": component.topology_index,
    })


def _pair_payload(channel: AuditoryL5CochlearChannel) -> bytes:
    definition = AUDITORY_CHANNELS[channel.cochlear_index]
    return _canonical_bytes({
        "carrier_phase_advance_component_receipt_sha256": (
            channel.carrier_phase_advance.authority_receipt_sha256
        ),
        "channel_id": channel.channel_id,
        "cochlear_index": channel.cochlear_index,
        "coordinates": {
            "centre_hz": str(definition.centre_hz),
            "erb_width_hz": str(definition.erb_width_hz),
        },
        "pressure_component_receipt_sha256": (
            channel.pressure.authority_receipt_sha256
        ),
        "schema": AUDITORY_L5_PAIR_SCHEMA,
    })


def _authority_payload(
    *,
    experience_id: str,
    structural_fingerprint: str,
    assembly_id: str,
    relation: str,
    event_boundary: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    channels: tuple[AuditoryL5CochlearChannel, ...],
    assembly_receipt_sha256: str,
) -> bytes:
    return _canonical_bytes({
        "assembly_id": assembly_id,
        "assembly_receipt_sha256": assembly_receipt_sha256,
        "channels": [
            {
                "carrier_phase_advance": {
                    "component_receipt_sha256": (
                        channel.carrier_phase_advance.authority_receipt_sha256
                    ),
                    "l4_field_receipt_sha256s": [
                        value.authority_receipt_sha256
                        for value in (
                            channel.carrier_phase_advance.l4_field_tuples
                        )
                    ],
                },
                "channel_id": channel.channel_id,
                "cochlear_index": channel.cochlear_index,
                "pair_receipt_sha256": channel.pair_receipt_sha256,
                "pressure": {
                    "component_receipt_sha256": (
                        channel.pressure.authority_receipt_sha256
                    ),
                    "l4_field_receipt_sha256s": [
                        value.authority_receipt_sha256
                        for value in channel.pressure.l4_field_tuples
                    ],
                },
            }
            for channel in channels
        ],
        "event_boundary": event_boundary,
        "experience_id": experience_id,
        "relation": relation,
        "schema": AUDITORY_L5_AUTHORITY_SCHEMA,
        "source_time_end": _fraction_text(source_time_end),
        "source_time_start": _fraction_text(source_time_start),
        "structural_fingerprint": structural_fingerprint,
    })


def _source_samples(
    receipt_registry: ReceiptRegistry,
    assembly_id: str,
    sound: SensoryFullFieldBoundary,
    substream: SensorySubstreamFullField,
) -> tuple[AuditoryL5ComponentSample, ...]:
    digest = substream.profile.physical_derivation_receipt_sha256
    raw = json.loads(
        receipt_registry.resolve(digest, "auditory L5 source evidence")
    )
    if (
        raw.get("schema") != "glew.provider.source_evidence_stream.v1"
        or raw.get("lane_id") != PhysicalSense.SOUND.value
        or raw.get("port_id") != substream.profile.substream_id
        or raw.get("port_kind") != substream.profile.physical_quantity
        or raw.get("physical_unit") != substream.profile.physical_unit
        or raw.get("source_epoch") != assembly_id
    ):
        raise ReceiptError("auditory L5 source evidence belongs to another component")
    samples = raw.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ReceiptError("auditory L5 source evidence is empty")
    interpreted = []
    for expected_index, value in enumerate(samples):
        if not isinstance(value, dict) or value.get("source_index") != expected_index:
            raise ReceiptError("auditory L5 source indices are not contiguous")
        source_time = _fraction(value.get("timestamp"), "auditory timestamp")
        if not sound.source_time_start <= source_time <= sound.source_time_end:
            raise ReceiptError("auditory L5 sample left its causal interval")
        interpreted.append(AuditoryL5ComponentSample(
            source_index=expected_index,
            source_time=source_time,
            causal_offset=source_time - sound.source_time_start,
            signal=_fraction(value.get("signal"), "auditory signal"),
            phase_turns=_fraction(value.get("phase_turns"), "auditory phase"),
        ))
    return tuple(interpreted)


def _field_tuples(substream) -> tuple[AuditoryL5FieldTuple, ...]:
    values = substream.kernel_basin.exact_dsf_field_tuples
    if not values or tuple(value.tuple_index for value in values) != tuple(
        range(len(values))
    ):
        raise ReceiptError("auditory L5 component L4 field is incomplete")
    return tuple(
        AuditoryL5FieldTuple(
            tuple_index=value.tuple_index,
            fields=tuple(
                (name, getattr(value, name)) for name in DSF_FIELD_ORDER
            ),
            source_l0_l4_trace_receipt_sha256=(
                value.source_l0_l4_trace_receipt_sha256
            ),
            authority_receipt_sha256=value.authority_receipt_sha256,
        )
        for value in values
    )


def _verify_component_upstream(
    *,
    component: AuditoryL5KernelComponent,
    assembly_id: str,
    sound: SensoryFullFieldBoundary,
    substream: SensorySubstreamFullField,
    receipt_registry: ReceiptRegistry,
) -> None:
    profile = substream.profile
    if (
        component.sensor_id != profile.sensor_id
        or component.substream_id != profile.substream_id
        or component.topology_index != profile.topology_index
        or component.coordinates
        != tuple(
            (coordinate.axis_id, coordinate.coordinate_id)
            for coordinate in profile.coordinates
        )
        or component.physical_quantity != profile.physical_quantity
        or component.physical_unit != profile.physical_unit
        or component.source_stream_receipt_sha256
        != profile.physical_derivation_receipt_sha256
        or component.l0_l4_trace_receipt_sha256
        != substream.l0_l4_trace_receipt_sha256
        or component.kernel_basin_receipt_sha256
        != substream.kernel_basin.authority_receipt_sha256
    ):
        raise ReceiptError(
            "auditory L5 component differs from its upstream full field"
        )
    if component.samples != _source_samples(
        receipt_registry,
        assembly_id,
        sound,
        substream,
    ):
        raise ReceiptError(
            "auditory L5 component samples differ from source evidence"
        )
    if component.l4_field_tuples != _field_tuples(substream):
        raise ReceiptError(
            "auditory L5 component differs from its exact upstream L4 field"
        )


def _verify_upstream_chain(experience: AuditoryL5Experience) -> None:
    boundary = experience.upstream_boundary
    if not isinstance(boundary, SixSenseFullFieldBoundary):
        raise ReceiptError("auditory L5 upstream boundary is not typed")
    upstream_registry = experience.upstream_receipt_registry
    if (
        not isinstance(upstream_registry, ReceiptRegistry)
        or upstream_registry.profile_binding_sha256
        != receipt_sha256(NATIVE_SENSORY_AUTHORITY_PROFILE)
    ):
        raise ReceiptError("auditory L5 upstream authority profile changed")
    boundary.verify(upstream_registry)
    if (
        experience.assembly_id != boundary.assembly_id
        or experience.assembly_receipt_sha256
        != boundary.authority_receipt_sha256
    ):
        raise ReceiptError("auditory L5 belongs to another sensory assembly")
    sound = next(
        value
        for value in boundary.boundaries
        if value.sense is PhysicalSense.SOUND
    )
    if (
        sound.state is not SenseBoundaryState.OBSERVED
        or sound.source_time_start != experience.source_time_start
        or sound.source_time_end != experience.source_time_end
        or len(sound.substreams) != AUDITORY_KERNEL_COMPONENT_COUNT
    ):
        raise ReceiptError("auditory L5 sound boundary changed")
    components = tuple(
        component
        for channel in experience.channels
        for component in (channel.pressure, channel.carrier_phase_advance)
    )
    for component, substream in zip(
        components,
        sound.substreams,
        strict=True,
    ):
        _verify_component_upstream(
            component=component,
            assembly_id=boundary.assembly_id,
            sound=sound,
            substream=substream,
            receipt_registry=upstream_registry,
        )


def _verify_experience(
    experience: AuditoryL5Experience,
    *,
    verify_upstream: bool,
) -> None:
    """Verify all L5 authority, optionally rewalking its upstream graph."""
    if experience.event_boundary not in ("ambient", "utterance"):
        raise ReceiptError("auditory L5 event boundary is invalid")
    if experience.relation not in (
        "first_observation",
        "recurrence",
        "structural_change",
    ):
        raise ReceiptError("auditory L5 relation is invalid")
    require_fraction(
        experience.source_time_start,
        "auditory L5 source start",
    )
    require_fraction(
        experience.source_time_end,
        "auditory L5 source end",
    )
    if experience.source_time_end <= experience.source_time_start:
        raise ReceiptError("auditory L5 source interval is invalid")
    if (
        experience.receipt_registry.profile_binding_sha256
        != receipt_sha256(AUDITORY_L5_AUTHORITY_PROFILE)
    ):
        raise ReceiptError("auditory L5 authority profile changed")
    _validate_channels(experience.channels)
    if verify_upstream:
        _verify_upstream_chain(experience)
    for channel in experience.channels:
        channel.verify(experience.receipt_registry)
    structural = _digest(
        AuditoryL5Owner._structural_payload(experience.channels)
    )
    if structural != experience.structural_fingerprint:
        raise ReceiptError("auditory L5 structural field was altered")
    expected_id = _digest({
        "assembly_id": experience.assembly_id,
        "auditory_structural_fingerprint": structural,
    })
    if expected_id != experience.experience_id:
        raise ReceiptError("auditory L5 experience identity was altered")
    payload = _authority_payload(
        experience_id=experience.experience_id,
        structural_fingerprint=experience.structural_fingerprint,
        assembly_id=experience.assembly_id,
        relation=experience.relation,
        event_boundary=experience.event_boundary,
        source_time_start=experience.source_time_start,
        source_time_end=experience.source_time_end,
        channels=experience.channels,
        assembly_receipt_sha256=experience.assembly_receipt_sha256,
    )
    mounted = experience.receipt_registry.resolve(
        experience.authority_receipt_sha256,
        "auditory L5 authority",
    )
    if (
        mounted != payload
        or receipt_sha256(payload)
        != experience.authority_receipt_sha256
    ):
        raise ReceiptError("auditory L5 authority receipt was altered")


def _verify_receipt_capacity(
    upstream_registry: ReceiptRegistry,
) -> None:
    if (
        len(upstream_registry.records) + _L5_LOCAL_RECEIPTS
        > MAX_AUDITORY_L5_RECEIPT_RECORDS
    ):
        raise ReceiptError("auditory L5 receipt registry exceeds its boundary")


def _build_component(
    built: BuiltSixSenseFullField,
    sound,
    substream,
    kind: AuditoryL5ComponentKind,
) -> tuple[AuditoryL5KernelComponent, bytes]:
    component = AuditoryL5KernelComponent(
        kind=kind,
        sensor_id=substream.profile.sensor_id,
        substream_id=substream.profile.substream_id,
        topology_index=substream.profile.topology_index,
        coordinates=tuple(
            (coordinate.axis_id, coordinate.coordinate_id)
            for coordinate in substream.profile.coordinates
        ),
        physical_quantity=substream.profile.physical_quantity,
        physical_unit=substream.profile.physical_unit,
        samples=_source_samples(
            built.receipt_registry,
            built.boundary.assembly_id,
            sound,
            substream,
        ),
        l4_field_tuples=_field_tuples(substream),
        source_stream_receipt_sha256=(
            substream.profile.physical_derivation_receipt_sha256
        ),
        l0_l4_trace_receipt_sha256=(
            substream.l0_l4_trace_receipt_sha256
        ),
        kernel_basin_receipt_sha256=(
            substream.kernel_basin.authority_receipt_sha256
        ),
        authority_receipt_sha256="0" * 64,
    )
    payload = _component_payload(component)
    component = AuditoryL5KernelComponent(
        kind=component.kind,
        sensor_id=component.sensor_id,
        substream_id=component.substream_id,
        topology_index=component.topology_index,
        coordinates=component.coordinates,
        physical_quantity=component.physical_quantity,
        physical_unit=component.physical_unit,
        samples=component.samples,
        l4_field_tuples=component.l4_field_tuples,
        source_stream_receipt_sha256=component.source_stream_receipt_sha256,
        l0_l4_trace_receipt_sha256=component.l0_l4_trace_receipt_sha256,
        kernel_basin_receipt_sha256=component.kernel_basin_receipt_sha256,
        authority_receipt_sha256=receipt_sha256(payload),
    )
    return component, payload


def _build_channels(
    built: BuiltSixSenseFullField,
    sound,
    *,
    transaction_verified: bool,
) -> tuple[
    tuple[AuditoryL5CochlearChannel, ...],
    tuple[bytes, ...],
]:
    substreams = sound.substreams
    if (
        len(substreams) != AUDITORY_KERNEL_COMPONENT_COUNT
        or tuple(value.profile.topology_index for value in substreams)
        != tuple(range(AUDITORY_KERNEL_COMPONENT_COUNT))
    ):
        raise ReceiptError(
            "auditory L5 requires the canonical 32-component interleaved mount"
        )
    channels = []
    payloads: list[bytes] = []
    for channel_index in range(COCHLEAR_CHANNEL_COUNT):
        pressure, pressure_payload = _build_component(
            built,
            sound,
            substreams[channel_index * 2],
            AuditoryL5ComponentKind.PRESSURE,
        )
        phase, phase_payload = _build_component(
            built,
            sound,
            substreams[channel_index * 2 + 1],
            AuditoryL5ComponentKind.CARRIER_PHASE_ADVANCE,
        )
        provisional = AuditoryL5CochlearChannel(
            cochlear_index=channel_index,
            channel_id=AUDITORY_CHANNELS[channel_index].name,
            pressure=pressure,
            carrier_phase_advance=phase,
            pair_receipt_sha256="0" * 64,
        )
        if not transaction_verified:
            _validate_channel(provisional)
        pair_payload = _pair_payload(provisional)
        channel = AuditoryL5CochlearChannel(
            cochlear_index=provisional.cochlear_index,
            channel_id=provisional.channel_id,
            pressure=provisional.pressure,
            carrier_phase_advance=provisional.carrier_phase_advance,
            pair_receipt_sha256=receipt_sha256(pair_payload),
        )
        channels.append(channel)
        payloads.extend((pressure_payload, phase_payload, pair_payload))
    result = tuple(channels)
    if transaction_verified:
        if (
            len(result) != COCHLEAR_CHANNEL_COUNT
            or tuple(channel.cochlear_index for channel in result)
            != tuple(range(COCHLEAR_CHANNEL_COUNT))
        ):
            raise ReceiptError(
                "constructed auditory L5 channel topology changed"
            )
    else:
        _validate_channels(result)
    return result, tuple(payloads)


def _verify_constructed_experience(
    *,
    experience: AuditoryL5Experience,
    built: BuiltSixSenseFullField,
) -> None:
    """Verify all new L5 authority inside one authenticated build.

    Only the immutable upstream graph traversal is skipped: the native builder
    already verified that exact boundary and registry, and their per-build
    authority binds both object identities.  Every L5 field, identity, channel,
    and newly issued receipt is still verified exactly once before publication.
    """
    built.verify_construction(
        boundary=experience.upstream_boundary,
        receipt_registry=experience.upstream_receipt_registry,
    )
    if (
        experience.assembly_id != built.boundary.assembly_id
        or experience.assembly_receipt_sha256
        != built.boundary.authority_receipt_sha256
    ):
        raise ReceiptError(
            "constructed auditory L5 authority left its verified field"
        )
    _verify_experience(
        experience,
        verify_upstream=False,
    )


class AuditoryL5Owner:
    """Serial, bounded owner of complete paired auditory interpretations."""

    def __init__(
        self,
        *,
        log_event: Callable[..., None],
        max_transitions: int = 1_024,
        max_pending_tutor_experiences: int = 4,
    ) -> None:
        if max_transitions <= 0:
            raise ValueError("auditory L5 transition capacity must be positive")
        if max_pending_tutor_experiences <= 0:
            raise ValueError("auditory L5 tutor window capacity must be positive")
        self._log_event = log_event
        self._max_transitions = int(max_transitions)
        self._max_pending_tutor_experiences = int(
            max_pending_tutor_experiences
        )
        self._lock = threading.RLock()
        self._latest: AuditoryL5Experience | None = None
        self._pending: OrderedDict[str, AuditoryL5Experience] = OrderedDict()
        self._recent_experience_ids: OrderedDict[str, None] = OrderedDict()
        self._transitions: OrderedDict[tuple[str, str], int] = OrderedDict()
        self._settled = 0

    @staticmethod
    def _component_structural_payload(
        component: AuditoryL5KernelComponent,
    ) -> dict[str, object]:
        return {
            "coordinates": [list(value) for value in component.coordinates],
            "kind": component.kind.value,
            "l4_field_tuples": [
                {
                    "fields": [
                        [name, _fraction_text(field)]
                        for name, field in value.fields
                    ],
                    "tuple_index": value.tuple_index,
                }
                for value in component.l4_field_tuples
            ],
            "physical_quantity": component.physical_quantity,
            "physical_unit": component.physical_unit,
            "samples": [
                {
                    "causal_offset": _fraction_text(value.causal_offset),
                    "phase_turns": _fraction_text(value.phase_turns),
                    "signal": _fraction_text(value.signal),
                    "source_index": value.source_index,
                }
                for value in component.samples
            ],
            "sensor_id": component.sensor_id,
            "substream_id": component.substream_id,
            "topology_index": component.topology_index,
        }

    @classmethod
    def _structural_payload(
        cls,
        channels: tuple[AuditoryL5CochlearChannel, ...],
    ) -> dict[str, object]:
        return {
            "channels": [
                {
                    "carrier_phase_advance": cls._component_structural_payload(
                        channel.carrier_phase_advance
                    ),
                    "channel_id": channel.channel_id,
                    "cochlear_index": channel.cochlear_index,
                    "pressure": cls._component_structural_payload(
                        channel.pressure
                    ),
                }
                for channel in channels
            ],
            "schema": AUDITORY_L5_SCHEMA,
        }

    def settle(
        self,
        built: BuiltSixSenseFullField,
        *,
        event_boundary: str = "ambient",
    ) -> AuditoryL5Experience | None:
        if event_boundary not in ("ambient", "utterance"):
            raise ValueError("auditory event boundary must be ambient or utterance")
        if not isinstance(built, BuiltSixSenseFullField):
            raise TypeError("auditory L5 requires a built six-sense full field")
        transaction_verified = (
            built.has_transaction_construction_authority
        )
        if transaction_verified:
            built.verify_construction()
        else:
            try:
                built.boundary.verify(built.receipt_registry)
            except IndexError as exc:
                raise ReceiptError(
                    "auditory L5 upstream kernel basin is incomplete"
                ) from exc
        sound = next(
            boundary
            for boundary in built.boundary.boundaries
            if boundary.sense is PhysicalSense.SOUND
        )
        if sound.state is not SenseBoundaryState.OBSERVED:
            return None

        # Every structural, receipt, topology, grid, and binary64 relation
        # check completes before acquiring the owner lock or mutating state.
        channels, component_and_pair_payloads = _build_channels(
            built,
            sound,
            transaction_verified=transaction_verified,
        )
        _verify_receipt_capacity(built.receipt_registry)
        fingerprint = _digest(self._structural_payload(channels))
        with self._lock:
            previous = (
                self._latest.structural_fingerprint
                if self._latest is not None
                else None
            )
            relation = (
                "first_observation"
                if previous is None
                else "recurrence"
                if previous == fingerprint
                else "structural_change"
            )
            experience_id = _digest({
                "assembly_id": built.boundary.assembly_id,
                "auditory_structural_fingerprint": fingerprint,
            })
            authority_payload = _authority_payload(
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                assembly_id=built.boundary.assembly_id,
                relation=relation,
                event_boundary=event_boundary,
                source_time_start=sound.source_time_start,
                source_time_end=sound.source_time_end,
                channels=channels,
                assembly_receipt_sha256=(
                    built.boundary.authority_receipt_sha256
                ),
            )
            receipt_registry = ReceiptRegistry.from_payloads(
                profile_payload=AUDITORY_L5_AUTHORITY_PROFILE,
                receipt_payloads=(
                    *component_and_pair_payloads,
                    authority_payload,
                ),
            )
            experience = AuditoryL5Experience(
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                assembly_id=built.boundary.assembly_id,
                relation=relation,
                event_boundary=event_boundary,
                source_time_start=sound.source_time_start,
                source_time_end=sound.source_time_end,
                channels=channels,
                assembly_receipt_sha256=(
                    built.boundary.authority_receipt_sha256
                ),
                authority_receipt_sha256=receipt_sha256(authority_payload),
                upstream_boundary=built.boundary,
                upstream_receipt_registry=built.receipt_registry,
                receipt_registry=receipt_registry,
            )
            if transaction_verified:
                _verify_constructed_experience(
                    experience=experience,
                    built=built,
                )
            else:
                experience.verify()
            if previous is not None:
                key = (previous, fingerprint)
                self._transitions[key] = self._transitions.get(key, 0) + 1
                self._transitions.move_to_end(key)
                while len(self._transitions) > self._max_transitions:
                    self._transitions.popitem(last=False)
            self._latest = experience
            self._recent_experience_ids[experience.experience_id] = None
            self._recent_experience_ids.move_to_end(experience.experience_id)
            while (
                len(self._recent_experience_ids)
                > self._max_pending_tutor_experiences
            ):
                expired_id, _ = self._recent_experience_ids.popitem(last=False)
                self._pending.pop(expired_id, None)
            if event_boundary == "utterance":
                self._pending[experience.experience_id] = experience
                self._pending.move_to_end(experience.experience_id)
            self._settled += 1
            self._log_event(
                "auditory_l5_experience_settled",
                experience_id=experience_id,
                structural_fingerprint=fingerprint,
                relation=relation,
                channel_count=len(channels),
                kernel_component_count=AUDITORY_KERNEL_COMPONENT_COUNT,
                event_boundary=event_boundary,
            )
            return experience

    @property
    def latest(self) -> AuditoryL5Experience | None:
        with self._lock:
            return self._latest

    def pending_experience(
        self,
        experience_id: str,
    ) -> AuditoryL5Experience | None:
        with self._lock:
            return self._pending.get(experience_id)

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "settled": self._settled,
                "has_latest": self._latest is not None,
                "pending_tutor_experiences": len(self._pending),
                "pending_tutor_capacity": self._max_pending_tutor_experiences,
                "transition_relations": len(self._transitions),
                "transition_capacity": self._max_transitions,
            }


__all__ = (
    "AUDITORY_L5_AUTHORITY_PROFILE",
    "AUDITORY_L5_AUTHORITY_SCHEMA",
    "AUDITORY_L5_COMPONENT_SCHEMA",
    "AUDITORY_L5_PAIR_SCHEMA",
    "AUDITORY_L5_SCHEMA",
    "MAX_AUDITORY_L5_RECEIPT_RECORDS",
    "AuditoryL5CochlearChannel",
    "AuditoryL5ComponentKind",
    "AuditoryL5ComponentSample",
    "AuditoryL5Experience",
    "AuditoryL5FieldTuple",
    "AuditoryL5KernelComponent",
    "AuditoryL5Owner",
)
