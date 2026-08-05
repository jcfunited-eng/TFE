"""Canonical two-component mount for the native auditory kernel boundary.

Each physical cochlear band contributes two independent L0--L4 inputs in a
stable interleaved order: pressure envelope, then carrier-phase advance.  The
phase component uses the provider's physically derived Nyquist fraction as its
signed signal while retaining the provider's cumulative carrier phase as its
cyclic coordinate.  This module never derives a replacement and never
introduces a chi, word, source identity, or meaning.
"""

from __future__ import annotations

import math
import threading
from fractions import Fraction
from dataclasses import dataclass
from typing import Any

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    NativeSensorySubstreamInput,
    PAIRED_SOURCE_RELEVANCE_RULE,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
)
from dsf_ai_service.substrate.auditory_pressure_kernel_input import (
    AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
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


AUDITORY_KERNEL_MOUNT_SCHEMA = "guala.native_sensory_input.v4"
LEGACY_AUDITORY_KERNEL_MOUNT_SCHEMA = "guala.native_sensory_input.v2"
LEGACY_PHYSICAL_AUDITORY_KERNEL_MOUNT_SCHEMA = (
    "guala.native_sensory_input.v3"
)
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


def _canonical_json_equal(left: object, right: object) -> bool:
    """Exact JSON-tree equality without numeric coercion or serialization."""

    if isinstance(left, dict) and isinstance(right, dict):
        return (
            left.keys() == right.keys()
            and all(
                _canonical_json_equal(left[key], right[key])
                for key in left
            )
        )
    if isinstance(left, list) and isinstance(right, list):
        return (
            len(left) == len(right)
            and all(
                _canonical_json_equal(a, b)
                for a, b in zip(left, right, strict=True)
            )
        )
    if type(left) is not type(right):
        return False
    if isinstance(left, tuple):
        return (
            len(left) == len(right)
            and all(
                _canonical_json_equal(a, b)
                for a, b in zip(left, right, strict=True)
            )
        )
    return left == right


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
            == len(channel.carrier_phase_turns)
            == len(channel.carrier_phase_advance_turns)
            == len(channel.carrier_phase_advance_nyquist_fraction)
            == sample_count
        ):
            raise ValueError("auditory kernel mount component cardinality changed")
        for sample_index, (
            pressure,
            cumulative_phase,
            advance,
            normalized,
        ) in enumerate(
            zip(
                channel.pressure_envelope_full_scale,
                channel.carrier_phase_turns,
                channel.carrier_phase_advance_turns,
                channel.carrier_phase_advance_nyquist_fraction,
                strict=True,
            )
        ):
            pressure_value = _finite_binary64(
                pressure,
                f"auditory band {band_index} pressure {sample_index}",
            )
            _finite_binary64(
                cumulative_phase,
                f"auditory band {band_index} cumulative phase {sample_index}",
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
        pressure_substream_id = f"{channel.definition.name}_pressure"
        pressure_relevance = tuple(
            Fraction.from_float(float(value)) ** 2
            for value in channel.pressure_envelope_full_scale
        )
        mounted.append(NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id=AUDITORY_KERNEL_SENSOR_ID,
            substream_id=pressure_substream_id,
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
            source_relevance=pressure_relevance,
            source_relevance_rule=PAIRED_SOURCE_RELEVANCE_RULE,
            source_relevance_origin_substream_id=pressure_substream_id,
            kernel_input_map=AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
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
                for value in channel.carrier_phase_turns
            ),
            source_relevance=pressure_relevance,
            source_relevance_rule=PAIRED_SOURCE_RELEVANCE_RULE,
            source_relevance_origin_substream_id=pressure_substream_id,
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


def _component_records(
    capture: AuditoryFullFieldCapture,
    *,
    source_anchor: Fraction,
    inputs: tuple[NativeSensorySubstreamInput, ...],
) -> tuple[dict[str, object], ...]:
    anchor = _fraction_pair(source_anchor)
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
            "kernel_input_map": (
                value.kernel_input_map.receipt_record()
            ),
            "source_relevance_fraction": [
                _fraction_pair(item)
                for item in (
                    value.source_relevance
                    if value.source_relevance is not None
                    else ()
                )
            ],
            "source_relevance_rule": value.source_relevance_rule,
            "source_relevance_origin_substream_id": (
                value.source_relevance_origin_substream_id
            ),
            "source_anchor_fraction": list(anchor),
            "causal_offsets_fraction": [
                _fraction_pair(offset) for offset in offsets
            ],
            "normalized_signal": list(value.normalized_signal),
            "phase_turns": [float(item) for item in value.phase_turns],
        })
    return tuple(records)


@dataclass(frozen=True, slots=True)
class BoundAuditoryKernelMount:
    """Request-local authority for an already serialized auditory mount."""

    window_id: str
    context_id: str
    entry_indices: tuple[int, ...]
    native_inputs: tuple[NativeSensorySubstreamInput, ...]

    def inputs_for_settlement(
        self,
        *,
        window_id: str,
        context_id: str,
    ) -> tuple[tuple[int, NativeSensorySubstreamInput], ...]:
        if (
            window_id != self.window_id
            or context_id != self.context_id
            or len(self.entry_indices) != len(self.native_inputs)
        ):
            raise RuntimeError(
                "auditory kernel mount left its bound causal window"
            )
        return tuple(zip(
            self.entry_indices,
            self.native_inputs,
            strict=True,
        ))


class _MountBindingAuthority:
    """Non-serializable one-window issuance authority."""

    __slots__ = ("_lock", "_bound")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bound = False

    def bind_once(self) -> None:
        with self._lock:
            if self._bound:
                raise RuntimeError(
                    "auditory kernel mount was already bound"
                )
            self._bound = True


@dataclass(frozen=True, slots=True)
class AuditoryKernelMount:
    """Canonical records plus the exact typed inputs that produced them.

    The typed objects are private request-local custody.  They become usable
    only after ``WindowManager`` supplies its already admitted entry records
    to ``_bind_to_window_entries`` and those records are byte-exact to the
    canonical serialization retained here.
    """

    records: tuple[dict[str, object], ...]
    native_inputs: tuple[NativeSensorySubstreamInput, ...]
    _binding_authority: _MountBindingAuthority

    def _bind_to_window_entries(
        self,
        *,
        window_id: str,
        context_id: str,
        entry_indices: tuple[int, ...],
        entry_records: tuple[dict[str, object], ...],
    ) -> BoundAuditoryKernelMount:
        if (
            len(entry_indices) != len(self.records)
            or len(entry_records) != len(self.records)
            or len(set(entry_indices)) != len(entry_indices)
        ):
            raise RuntimeError(
                "auditory kernel mount binding cardinality changed"
            )
        admitted = []
        for entry in entry_records:
            try:
                admitted.append(entry["full_field"])
            except (KeyError, TypeError) as error:
                raise RuntimeError(
                    "auditory kernel mount binding lost its native record"
                ) from error
        if not _canonical_json_equal(admitted, list(self.records)):
            raise RuntimeError(
                "auditory kernel mount binding changed canonical bytes"
            )
        self._binding_authority.bind_once()
        return BoundAuditoryKernelMount(
            window_id=window_id,
            context_id=context_id,
            entry_indices=entry_indices,
            native_inputs=self.native_inputs,
        )


def auditory_kernel_mount(
    capture: AuditoryFullFieldCapture,
    *,
    source_anchor: Fraction,
) -> AuditoryKernelMount:
    """Create one verified typed mount and its byte-exact public records."""

    inputs = _component_inputs(capture, source_anchor=source_anchor)
    records = _component_records(
        capture,
        source_anchor=source_anchor,
        inputs=inputs,
    )
    return AuditoryKernelMount(
        records=records,
        native_inputs=inputs,
        _binding_authority=_MountBindingAuthority(),
    )


def auditory_kernel_component_records(
    capture: AuditoryFullFieldCapture,
    *,
    source_anchor: Fraction,
) -> tuple[dict[str, object], ...]:
    """Return canonical v4 records consumed by causal-window settlement."""

    return auditory_kernel_mount(
        capture,
        source_anchor=source_anchor,
    ).records


__all__ = (
    "AUDITORY_KERNEL_COMPONENT_COUNT",
    "AUDITORY_KERNEL_MOUNT_SCHEMA",
    "AUDITORY_KERNEL_SENSOR_ID",
    "AuditoryKernelMount",
    "BoundAuditoryKernelMount",
    "LEGACY_AUDITORY_KERNEL_MOUNT_SCHEMA",
    "LEGACY_PHYSICAL_AUDITORY_KERNEL_MOUNT_SCHEMA",
    "auditory_kernel_component_inputs",
    "auditory_kernel_component_records",
    "auditory_kernel_mount",
)
