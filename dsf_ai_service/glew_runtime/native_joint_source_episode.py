"""One-way exact GLJSRC02 source carrier for the native joint field.

The carrier preserves typed receptor evidence and source-declared joint
occurrences.  A joint occurrence supplies exact ``T``, declared ``V`` and
``G``, ``F`` by reference to the admitted receptor records, and an explicit
source-law ``r``.  Neuronal contact topology ``E`` is deliberately absent: it
belongs to resident neuron physics and must be joined inside the native
organism transition.

This module neither infers occurrences from equal clocks nor promotes
port-local relevance into joint relevance.  It has no GLJSRC01 compatibility
path.
"""

from __future__ import annotations

import importlib
import math
import struct
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping, Protocol, runtime_checkable

from .native_sensory_full_field import NativeSensorySubstreamInput
from .sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)


UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR = (
    b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1"
)


@dataclass(frozen=True, slots=True)
class NativeJointSourceOccurrenceInput:
    """One explicitly declared source occurrence, before resident ``E``.

    ``port_indices`` address the global canonical port order encoded in the
    same GLJSRC02 body. Group members address local positions within that
    tuple. ``joint_intersample_profile_payload`` explicitly declares the law
    between sampled L1 volume-integrand and joint-relevance values; the native
    UF adapter, not this custody carrier, interprets it.
    """

    port_indices: tuple[int, ...]
    source_times: tuple[Fraction, ...]
    joint_intersample_profile_payload: bytes
    groups: tuple[tuple[int, ...], ...]
    joint_relevance_profile_payload: bytes
    joint_relevance: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.port_indices, tuple)
            or not self.port_indices
            or any(
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < 0
                for index in self.port_indices
            )
            or any(
                right <= left
                for left, right in zip(
                    self.port_indices, self.port_indices[1:]
                )
            )
        ):
            raise ValueError(
                "joint-source occurrence ports are not strictly canonical"
            )
        if (
            not isinstance(self.source_times, tuple)
            or not self.source_times
            or any(not isinstance(value, Fraction) for value in self.source_times)
            or any(
                right <= left
                for left, right in zip(
                    self.source_times, self.source_times[1:]
                )
            )
        ):
            raise ValueError(
                "joint-source occurrence times are not exact and increasing"
            )
        if (
            not isinstance(self.joint_intersample_profile_payload, bytes)
            or not self.joint_intersample_profile_payload
        ):
            raise ValueError(
                "joint-source occurrence intersample profile is empty"
            )
        if (
            not isinstance(self.groups, tuple)
            or not self.groups
            or any(not isinstance(group, tuple) or not group for group in self.groups)
        ):
            raise ValueError("joint-source occurrence groups are incomplete")
        for group in self.groups:
            if any(
                isinstance(index, bool)
                or not isinstance(index, int)
                or index < 0
                for index in group
            ) or any(
                right <= left for left, right in zip(group, group[1:])
            ):
                raise ValueError(
                    "joint-source occurrence group is not strictly canonical"
                )
        if self.groups != tuple(sorted(self.groups)):
            raise ValueError(
                "joint-source occurrence groups are not canonically ordered"
            )
        covered = sorted(index for group in self.groups for index in group)
        if covered != list(range(len(self.port_indices))):
            raise ValueError(
                "joint-source occurrence groups do not partition its vertices"
            )
        if (
            not isinstance(self.joint_relevance_profile_payload, bytes)
            or not self.joint_relevance_profile_payload
        ):
            raise ValueError(
                "joint-source occurrence relevance profile is empty"
            )
        if (
            not isinstance(self.joint_relevance, tuple)
            or len(self.joint_relevance) != len(self.source_times)
            or any(
                not isinstance(value, Fraction) or not 0 <= value <= 1
                for value in self.joint_relevance
            )
        ):
            raise ValueError(
                "joint-source occurrence relevance is not exact, aligned, and in [0,1]"
            )


@runtime_checkable
class ImmutableJointSourceEpisode(Protocol):
    @property
    def schema(self) -> str: ...

    @property
    def payload_sha256(self) -> str: ...

    @property
    def port_count(self) -> int: ...

    @property
    def source_sample_count(self) -> int: ...

    @property
    def occurrence_count(self) -> int: ...

    @property
    def occurrence_frame_count(self) -> int: ...

    @property
    def python_callback_count(self) -> int: ...

    def as_bytes(self) -> bytes: ...


_STATE_CODE = {
    SenseBoundaryState.OBSERVED: 0,
    SenseBoundaryState.QUIESCENT: 1,
    SenseBoundaryState.SENSOR_UNAVAILABLE: 2,
    SenseBoundaryState.UNKNOWN: 3,
}


def _native_core():
    return importlib.import_module("guala_core")


def _u16(output: bytearray, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise ValueError("joint-source u16 field exceeds its representation")
    output.extend(struct.pack("<H", value))


def _u32(output: bytearray, value: int) -> None:
    if not 0 <= value <= 0xFFFF_FFFF:
        raise ValueError("joint-source u32 field exceeds its representation")
    output.extend(struct.pack("<I", value))


def _text(output: bytearray, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("joint-source text is not a string")
    encoded = value.encode("utf-8")
    _u16(output, len(encoded))
    output.extend(encoded)


def _bytes(output: bytearray, value: bytes) -> None:
    if not isinstance(value, bytes) or not value:
        raise ValueError("joint-source byte field is empty")
    _u32(output, len(value))
    output.extend(value)


def _rational(output: bytearray, value: Fraction) -> None:
    if not isinstance(value, Fraction):
        raise TypeError("joint-source causal value is not exact")
    _text(output, str(value.numerator))
    _text(output, str(value.denominator))


def _binary64(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is not finite binary64")
    return result


def _ordered_ports(
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]
    ],
) -> tuple[NativeSensorySubstreamInput, ...]:
    ordered: list[NativeSensorySubstreamInput] = []
    for sense in SENSE_ORDER:
        ports = observed_substreams.get(sense, ())
        if not isinstance(ports, tuple):
            raise TypeError("joint-source receptor collection is not immutable")
        if any(
            not isinstance(port, NativeSensorySubstreamInput)
            or port.sense is not sense
            for port in ports
        ):
            raise TypeError("joint-source receptor crossed a physical sense")
        if tuple(port.topology_index for port in ports) != tuple(
            range(len(ports))
        ):
            raise ValueError("joint-source topology is incomplete or reordered")
        ordered.extend(ports)
    return tuple(ordered)


def _validate_occurrences(
    ordered_ports: tuple[NativeSensorySubstreamInput, ...],
    occurrences: tuple[NativeJointSourceOccurrenceInput, ...],
) -> int:
    if not isinstance(occurrences, tuple) or any(
        not isinstance(value, NativeJointSourceOccurrenceInput)
        for value in occurrences
    ):
        raise TypeError("joint-source occurrence collection is not immutable and typed")
    if bool(ordered_ports) != bool(occurrences):
        raise ValueError(
            "joint-source occurrences do not cover the observed receptor topology"
        )
    if occurrences != tuple(sorted(occurrences, key=lambda value: value.port_indices)):
        raise ValueError("joint-source occurrences are not canonically ordered")

    covered: list[int] = []
    occurrence_frames = 0
    for occurrence in occurrences:
        if occurrence.port_indices[-1] >= len(ordered_ports):
            raise ValueError(
                "joint-source occurrence references a receptor outside topology"
            )
        for port_index in occurrence.port_indices:
            if ordered_ports[port_index].source_times != occurrence.source_times:
                raise ValueError(
                    "joint-source occurrence clock differs from a referenced receptor"
                )
        covered.extend(occurrence.port_indices)
        occurrence_frames += len(occurrence.source_times)
        if occurrence_frames > 0xFFFF_FFFF:
            raise ValueError(
                "joint-source occurrence frames exceed their representation"
            )
    if sorted(covered) != list(range(len(ordered_ports))):
        raise ValueError(
            "joint-source occurrences do not partition every receptor exactly once"
        )
    return occurrence_frames


def encode_native_joint_source_episode(
    *,
    assembly_id: str,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]
    ],
    states: Mapping[PhysicalSense, SenseBoundaryState],
    occurrences: tuple[NativeJointSourceOccurrenceInput, ...],
) -> tuple[bytes, int, int, int, int]:
    if (
        not isinstance(assembly_id, str)
        or not assembly_id
        or assembly_id.strip() != assembly_id
    ):
        raise ValueError("joint-source assembly identity is not canonical")
    if set(states) != set(SENSE_ORDER):
        raise ValueError("joint-source states do not cover all physical senses")
    if not all(isinstance(value, SenseBoundaryState) for value in states.values()):
        raise TypeError("joint-source sense state is not typed")
    expected_observed = {
        sense
        for sense, state in states.items()
        if state is SenseBoundaryState.OBSERVED
    }
    if set(observed_substreams) != expected_observed:
        raise ValueError("joint-source observations disagree with sense state")

    ordered_ports = _ordered_ports(observed_substreams)
    occurrence_frame_count = _validate_occurrences(ordered_ports, occurrences)
    sample_count = sum(len(port.normalized_signal) for port in ordered_ports)
    output = bytearray(b"GLJSRC02")
    _u16(output, 2)
    _text(output, assembly_id)
    output.extend(_STATE_CODE[states[sense]] for sense in SENSE_ORDER)
    _u32(output, len(ordered_ports))
    for port in ordered_ports:
        output.append(tuple(SENSE_ORDER).index(port.sense))
        _u32(output, port.topology_index)
        _text(output, port.sensor_id)
        _text(output, port.substream_id)
        _u16(output, len(port.coordinates))
        for coordinate in port.coordinates:
            _text(output, coordinate.axis_id)
            _text(output, coordinate.coordinate_id)
        _text(output, port.physical_quantity)
        _text(output, port.physical_unit)
        _text(output, port.source_relevance_rule)
        _text(output, port.source_relevance_origin_substream_id or "")
        input_map = port.kernel_input_map
        _text(output, input_map.map_id)
        _rational(output, input_map.source_min)
        _rational(output, input_map.source_max)
        _rational(output, input_map.field_offset)
        _rational(output, input_map.field_scale)
        _bytes(output, input_map.profile_payload)
        relevances = (
            port.source_relevance
            if port.source_relevance is not None
            else (Fraction(1),) * len(port.normalized_signal)
        )
        _u32(output, len(port.normalized_signal))
        for index, (timestamp, signal, phase, relevance) in enumerate(
            zip(
                port.source_times,
                port.normalized_signal,
                port.phase_turns,
                relevances,
                strict=True,
            )
        ):
            _rational(output, timestamp)
            exact_signal_value = _binary64(signal, f"joint-source signal {index}")
            output.extend(struct.pack("<d", exact_signal_value))
            _rational(output, phase)
            _rational(output, relevance)
            exact_signal = Fraction.from_float(exact_signal_value)
            _rational(output, input_map.forward(exact_signal))

    _u32(output, len(occurrences))
    for occurrence in occurrences:
        _u32(output, len(occurrence.port_indices))
        for port_index in occurrence.port_indices:
            _u32(output, port_index)
        _u32(output, len(occurrence.source_times))
        for timestamp in occurrence.source_times:
            _rational(output, timestamp)
        _bytes(output, occurrence.joint_intersample_profile_payload)
        _u32(output, len(occurrence.groups))
        for group in occurrence.groups:
            _u32(output, len(group))
            for vertex_position in group:
                _u32(output, vertex_position)
        _bytes(output, occurrence.joint_relevance_profile_payload)
        _u32(output, len(occurrence.joint_relevance))
        for relevance in occurrence.joint_relevance:
            _rational(output, relevance)
    return (
        bytes(output),
        len(ordered_ports),
        sample_count,
        len(occurrences),
        occurrence_frame_count,
    )


def settle_native_joint_source_episode(
    *,
    assembly_id: str,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]
    ],
    states: Mapping[PhysicalSense, SenseBoundaryState],
    occurrences: tuple[NativeJointSourceOccurrenceInput, ...],
) -> ImmutableJointSourceEpisode:
    candidate, port_count, sample_count, occurrence_count, occurrence_frames = (
        encode_native_joint_source_episode(
            assembly_id=assembly_id,
            observed_substreams=observed_substreams,
            states=states,
            occurrences=occurrences,
        )
    )
    result = _native_core().settle_native_joint_source_episode(
        candidate,
        port_count,
        sample_count,
        occurrence_count,
        occurrence_frames,
    )
    if not isinstance(result, ImmutableJointSourceEpisode):
        raise TypeError("native joint-source settlement changed its result type")
    if result.python_callback_count != 0:
        raise RuntimeError("native joint-source settlement crossed Python")
    if (
        result.schema != "guala.native.exact_joint_source_episode.v2"
        or result.port_count != port_count
        or result.source_sample_count != sample_count
        or result.occurrence_count != occurrence_count
        or result.occurrence_frame_count != occurrence_frames
        or result.as_bytes() != candidate
    ):
        raise RuntimeError("native joint-source settlement changed source custody")
    return result


def settle_native_joint_source_episode_batch_from_anatomy(
    *,
    anatomy: object,
    assembly_ids: tuple[str, ...],
    source_times: tuple[tuple[Fraction, ...], ...],
    signal_bodies: tuple[bytes, ...],
) -> tuple[ImmutableJointSourceEpisode, ...]:
    """Build exact episodes natively from one authored receptor anatomy."""

    if not (
        isinstance(assembly_ids, tuple)
        and isinstance(source_times, tuple)
        and isinstance(signal_bodies, tuple)
        and len(assembly_ids) == len(source_times) == len(signal_bodies)
        and assembly_ids
    ):
        raise ValueError("compact joint-source batch changed cardinality")
    clocks: list[list[tuple[int, int]]] = []
    for clock in source_times:
        if not isinstance(clock, tuple) or not clock:
            raise ValueError("compact joint-source clock is empty or mutable")
        encoded_clock: list[tuple[int, int]] = []
        for value in clock:
            if not isinstance(value, Fraction):
                raise TypeError("compact joint-source clock is not exact")
            if not -(1 << 63) <= value.numerator < (1 << 63):
                raise ValueError("compact joint-source clock numerator exceeds i64")
            if not 0 < value.denominator < (1 << 63):
                raise ValueError("compact joint-source clock denominator exceeds i64")
            encoded_clock.append((value.numerator, value.denominator))
        clocks.append(encoded_clock)
    if any(not isinstance(value, bytes) or not value for value in signal_bodies):
        raise ValueError("compact joint-source signal body is empty or untyped")
    result = _native_core().settle_native_joint_source_episode_batch_from_anatomy(
        anatomy,
        list(assembly_ids),
        clocks,
        list(signal_bodies),
    )
    if not isinstance(result, list) or len(result) != len(assembly_ids):
        raise RuntimeError("native compact joint-source batch changed cardinality")
    if any(
        not isinstance(episode, ImmutableJointSourceEpisode)
        or episode.schema != "guala.native.exact_joint_source_episode.v2"
        or episode.python_callback_count != 0
        for episode in result
    ):
        raise RuntimeError("native compact joint-source batch lost authority")
    return tuple(result)


__all__ = (
    "ImmutableJointSourceEpisode",
    "NativeJointSourceOccurrenceInput",
    "UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR",
    "encode_native_joint_source_episode",
    "settle_native_joint_source_episode",
    "settle_native_joint_source_episode_batch_from_anatomy",
)
