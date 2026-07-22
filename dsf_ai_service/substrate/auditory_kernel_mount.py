"""Canonical two-component mount for the native auditory kernel boundary.

Each physical cochlear band contributes two independent L0--L4 inputs in a
stable interleaved order: pressure envelope, then carrier-phase advance.  The
phase component uses the provider's physically derived Nyquist fraction; this
module never derives a replacement from absolute phase and never introduces a
chi, word, source identity, or meaning.
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    AUDITORY_FULL_FIELD_PROVIDER_SCHEMA,
    COCHLEAR_CHANNEL_COUNT,
    COCHLEAR_ORDER,
    OBSERVATION_HOP_SAMPLES,
    PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP,
    REQUIRED_SAMPLE_RATE_HZ,
    AuditoryFullFieldCapture,
)


AUDITORY_KERNEL_MOUNT_SCHEMA = "guala.native_sensory_input.v2"
AUDITORY_KERNEL_SENSOR_ID = "microphone-gammatone-cochlear-field"
AUDITORY_KERNEL_COMPONENT_COUNT = COCHLEAR_CHANNEL_COUNT * 2

_PRESSURE_COMPONENT = "pressure-envelope"
_PHASE_ADVANCE_COMPONENT = "carrier-phase-advance"
_PRESSURE_QUANTITY = "cochlear-pressure-envelope"
_PRESSURE_UNIT = "full-scale-pressure"
_PHASE_ADVANCE_QUANTITY = "cochlear-carrier-phase-advance"
_PHASE_ADVANCE_UNIT = "nyquist-fraction-per-observation-hop"


def _fraction_pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _finite_binary64(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite binary64 value")
    try:
        mounted = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite binary64 value") from exc
    if not math.isfinite(mounted):
        raise ValueError(f"{name} must be a finite binary64 value")
    return mounted


def _validated_capture(capture: AuditoryFullFieldCapture) -> tuple[Any, ...]:
    if not isinstance(capture, AuditoryFullFieldCapture):
        raise TypeError("auditory kernel mount requires a full-field capture")
    if capture.provider_schema != AUDITORY_FULL_FIELD_PROVIDER_SCHEMA:
        raise ValueError("auditory kernel mount provider schema changed")
    if capture.source_sample_rate_hz != REQUIRED_SAMPLE_RATE_HZ:
        raise ValueError("auditory kernel mount source rate changed")
    if capture.observation_hop_samples != OBSERVATION_HOP_SAMPLES:
        raise ValueError("auditory kernel mount causal hop changed")
    if len(capture.channels) != COCHLEAR_CHANNEL_COUNT:
        raise ValueError("auditory kernel mount topology changed")
    if tuple(channel.definition for channel in capture.channels) != AUDITORY_CHANNELS:
        raise ValueError("auditory kernel mount channel definitions changed")

    reference_offsets = capture.channels[0].causal_offsets_ns
    if (
        not reference_offsets
        or len(reference_offsets) > MAX_NATIVE_SAMPLES_PER_SUBSTREAM
        or reference_offsets[0] < 0
        or any(
            right <= left
            for left, right in zip(reference_offsets, reference_offsets[1:])
        )
    ):
        raise ValueError("auditory kernel mount causal grid is invalid")

    sample_count = len(reference_offsets)
    for band_index, channel in enumerate(capture.channels):
        if channel.causal_offsets_ns != reference_offsets:
            raise ValueError("auditory kernel mount channels are not synchronized")
        if not (
            len(channel.pressure_envelope_full_scale)
            == len(channel.carrier_phase_advance_turns)
            == len(channel.carrier_phase_advance_nyquist_fraction)
            == sample_count
        ):
            raise ValueError("auditory kernel mount component cardinality changed")
        for sample_index, (pressure, advance, normalized) in enumerate(
            zip(
                channel.pressure_envelope_full_scale,
                channel.carrier_phase_advance_turns,
                channel.carrier_phase_advance_nyquist_fraction,
                strict=True,
            )
        ):
            pressure_value = _finite_binary64(
                pressure,
                f"auditory band {band_index} pressure {sample_index}",
            )
            advance_value = _finite_binary64(
                advance,
                f"auditory band {band_index} phase advance {sample_index}",
            )
            normalized_value = _finite_binary64(
                normalized,
                f"auditory band {band_index} normalized phase {sample_index}",
            )
            if not 0.0 <= pressure_value <= 1.0:
                raise ValueError("auditory pressure left full-scale calibration")
            if not (
                -PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
                <= advance_value
                <= PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            ):
                raise ValueError("auditory phase advance exceeded Nyquist")
            if not -1.0 <= normalized_value <= 1.0:
                raise ValueError("auditory normalized phase advance exceeded Nyquist")
            if (
                normalized_value
                != advance_value / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
            ):
                raise ValueError("auditory phase-advance normalization changed")
    return capture.channels


def _coordinates(channel: Any, component: str) -> tuple[NativeAxisCoordinate, ...]:
    definition = channel.definition
    return (
        NativeAxisCoordinate("cochlear-channel", definition.name),
        NativeAxisCoordinate("kernel-component", component),
        NativeAxisCoordinate("centre-hz", str(definition.centre_hz)),
        NativeAxisCoordinate("erb-width-hz", str(definition.erb_width_hz)),
        NativeAxisCoordinate("gammatone-order", str(COCHLEAR_ORDER)),
        NativeAxisCoordinate(
            "observation-hop-samples", str(OBSERVATION_HOP_SAMPLES)
        ),
    )


def _component_inputs(
    capture: AuditoryFullFieldCapture,
    *,
    source_anchor: Fraction,
) -> tuple[NativeSensorySubstreamInput, ...]:
    if not isinstance(source_anchor, Fraction):
        raise TypeError("auditory kernel mount source anchor must be exact Fraction")
    channels = _validated_capture(capture)
    offsets = tuple(
        Fraction(value, 1_000_000_000)
        for value in channels[0].causal_offsets_ns
    )
    source_times = tuple(source_anchor + value for value in offsets)
    zero_phase = (Fraction(0),) * len(source_times)
    mounted: list[NativeSensorySubstreamInput] = []
    for band_index, channel in enumerate(channels):
        pressure_index = band_index * 2
        phase_index = pressure_index + 1
        mounted.append(NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id=AUDITORY_KERNEL_SENSOR_ID,
            substream_id=f"{channel.definition.name}_pressure",
            topology_index=pressure_index,
            coordinates=_coordinates(channel, _PRESSURE_COMPONENT),
            physical_quantity=_PRESSURE_QUANTITY,
            physical_unit=_PRESSURE_UNIT,
            source_times=source_times,
            normalized_signal=tuple(channel.pressure_envelope_full_scale),
            # A pressure envelope has no cyclic component phase.  Keeping this
            # exactly zero prevents carrier phase from leaking into its kernel
            # stream; the adjacent phase-advance stream owns that observation.
            phase_turns=zero_phase,
        ))
        mounted.append(NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id=AUDITORY_KERNEL_SENSOR_ID,
            substream_id=f"{channel.definition.name}_phase_advance",
            topology_index=phase_index,
            coordinates=_coordinates(channel, _PHASE_ADVANCE_COMPONENT),
            physical_quantity=_PHASE_ADVANCE_QUANTITY,
            physical_unit=_PHASE_ADVANCE_UNIT,
            source_times=source_times,
            normalized_signal=tuple(
                channel.carrier_phase_advance_nyquist_fraction
            ),
            phase_turns=tuple(
                Fraction.from_float(float(value))
                for value in channel.carrier_phase_advance_turns
            ),
        ))
    if (
        len(mounted) != AUDITORY_KERNEL_COMPONENT_COUNT
        or tuple(value.topology_index for value in mounted)
        != tuple(range(AUDITORY_KERNEL_COMPONENT_COUNT))
    ):
        raise RuntimeError("auditory kernel mount did not settle its full topology")
    return tuple(mounted)


def auditory_kernel_component_inputs(
    capture: AuditoryFullFieldCapture,
    *,
    source_anchor: Fraction,
) -> tuple[NativeSensorySubstreamInput, ...]:
    """Return the canonical typed 32-component auditory kernel mount."""
    return _component_inputs(capture, source_anchor=source_anchor)


def auditory_kernel_component_records(
    capture: AuditoryFullFieldCapture,
    *,
    source_anchor: Fraction,
) -> tuple[dict[str, object], ...]:
    """Return canonical v2 records consumed by causal-window settlement."""
    anchor = _fraction_pair(source_anchor)
    inputs = _component_inputs(capture, source_anchor=source_anchor)
    offsets = tuple(
        Fraction(value, 1_000_000_000)
        for value in capture.channels[0].causal_offsets_ns
    )
    records = []
    for value in inputs:
        records.append({
            "schema": AUDITORY_KERNEL_MOUNT_SCHEMA,
            "sense": value.sense.value,
            "sensor_id": value.sensor_id,
            "substream_id": value.substream_id,
            "topology_index": value.topology_index,
            "coordinates": [
                [coordinate.axis_id, coordinate.coordinate_id]
                for coordinate in value.coordinates
            ],
            "physical_quantity": value.physical_quantity,
            "physical_unit": value.physical_unit,
            "source_anchor_fraction": list(anchor),
            "causal_offsets_fraction": [
                _fraction_pair(offset) for offset in offsets
            ],
            "normalized_signal": list(value.normalized_signal),
            "phase_turns": [float(item) for item in value.phase_turns],
        })
    return tuple(records)


__all__ = (
    "AUDITORY_KERNEL_COMPONENT_COUNT",
    "AUDITORY_KERNEL_MOUNT_SCHEMA",
    "AUDITORY_KERNEL_SENSOR_ID",
    "auditory_kernel_component_inputs",
    "auditory_kernel_component_records",
)
