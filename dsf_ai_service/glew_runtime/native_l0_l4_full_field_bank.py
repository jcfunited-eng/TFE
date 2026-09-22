"""One-call typed adapter into the native immutable L0--L4 field bank.

This boundary serializes the already-admitted physical
``NativeSensorySubstreamInput`` values directly.  It does not construct a
Python owner/receipt graph, interpret meaning, reconstruct L4 rows, or call
back from Rust.  The single settlement call returns the immutable native bank
unchanged.
"""

from __future__ import annotations

import importlib
import json
import math
import struct
from fractions import Fraction
from typing import Mapping, Protocol, runtime_checkable

from .native_sensory_full_field import NativeSensorySubstreamInput
from .sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)


@runtime_checkable
class ImmutableFullFieldBank(Protocol):
    """Read-only native result; no Python-owned field-row reconstruction."""

    @property
    def schema(self) -> str: ...

    @property
    def payload_sha256(self) -> str: ...

    @property
    def root_sha256(self) -> str: ...

    @property
    def port_count(self) -> int: ...

    @property
    def source_sample_count(self) -> int: ...

    @property
    def field_row_count(self) -> int: ...

    @property
    def python_callback_count(self) -> int: ...

    def as_bytes(self) -> bytes: ...


_STATE_CODE = {
    SenseBoundaryState.OBSERVED: 0,
    SenseBoundaryState.QUIESCENT: 1,
    SenseBoundaryState.SENSOR_UNAVAILABLE: 2,
    SenseBoundaryState.UNKNOWN: 3,
}
_CONFIG_PAYLOAD: bytes | None = None


def _native_core():
    return importlib.import_module("guala_core")


def _canonical_config_payload(native_core) -> bytes:
    global _CONFIG_PAYLOAD
    if _CONFIG_PAYLOAD is None:
        payload, _digest = native_core.canonical_l0_l4_current_config()
        _CONFIG_PAYLOAD = bytes(payload)
    return _CONFIG_PAYLOAD


def _u16(output: bytearray, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise ValueError("native episode u16 field exceeds its schema")
    output.extend(struct.pack("<H", value))


def _u32(output: bytearray, value: int) -> None:
    if not 0 <= value <= 0xFFFF_FFFF:
        raise ValueError("native episode u32 field exceeds its schema")
    output.extend(struct.pack("<I", value))


def _u64(output: bytearray, value: int) -> None:
    output.extend(struct.pack("<Q", value))


def _text(output: bytearray, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("native episode text field is not a string")
    raw = value.encode("utf-8")
    _u16(output, len(raw))
    output.extend(raw)


def _bytes(output: bytearray, value: bytes) -> None:
    if not isinstance(value, bytes) or not value:
        raise ValueError("native episode byte field must be nonempty bytes")
    _u32(output, len(value))
    output.extend(value)


def _rational(output: bytearray, value: Fraction) -> None:
    if not isinstance(value, Fraction):
        raise TypeError("native episode rational field is not exact")
    _text(output, str(value.numerator))
    _text(output, str(value.denominator))


def _binary64_bits(value: object, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} is not numeric")
    encoded = float(value)
    if not math.isfinite(encoded):
        raise ValueError(f"{name} is not finite binary64")
    return struct.unpack("<Q", struct.pack("<d", encoded))[0]


def _map_json(value) -> bytes:
    return json.dumps(
        value.receipt_record(),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def encode_native_l0_l4_episode(
    *,
    assembly_id: str,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]
    ],
    states: Mapping[PhysicalSense, SenseBoundaryState],
    config_payload: bytes,
) -> bytes:
    """Encode one complete admitted physical boundary without settling it."""

    if not isinstance(assembly_id, str) or not assembly_id or assembly_id.strip() != assembly_id:
        raise ValueError("native bank assembly_id is not a canonical identifier")
    if set(states) != set(SENSE_ORDER):
        raise ValueError("native bank states must explicitly cover all six senses")
    if not all(isinstance(value, SenseBoundaryState) for value in states.values()):
        raise TypeError("native bank sense states are not typed")
    expected_observed = {
        sense
        for sense, state in states.items()
        if state is SenseBoundaryState.OBSERVED
    }
    if set(observed_substreams) != expected_observed:
        raise ValueError("native bank observed inputs and sense states disagree")

    ordered_ports: list[NativeSensorySubstreamInput] = []
    for sense in SENSE_ORDER:
        ports = observed_substreams.get(sense, ())
        if not isinstance(ports, tuple):
            raise TypeError("native bank sensory ports must be immutable tuples")
        if any(
            not isinstance(port, NativeSensorySubstreamInput)
            or port.sense is not sense
            for port in ports
        ):
            raise TypeError("native bank topology crosses sense boundaries")
        if tuple(port.topology_index for port in ports) != tuple(range(len(ports))):
            raise ValueError("native bank topology is incomplete or reordered")
        ordered_ports.extend(ports)

    output = bytearray(b"GLNEPI03")
    _u16(output, 3)
    _bytes(output, config_payload)
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
        _text(
            output,
            port.source_relevance_origin_substream_id or "",
        )
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
        for index, (timestamp, signal, phase, relevance) in enumerate(zip(
            port.source_times,
            port.normalized_signal,
            port.phase_turns,
            relevances,
            strict=True,
        )):
            _rational(output, timestamp)
            signal_bits = _binary64_bits(
                signal,
                f"native signal {index}",
            )
            _u64(output, signal_bits)
            _rational(output, phase)
            _rational(output, relevance)
            exact_signal = Fraction.from_float(float(signal))
            exact_field = input_map.forward(exact_signal)
            _rational(output, exact_field)
            _u64(
                output,
                _binary64_bits(
                    exact_field,
                    f"dimensionless field {index}",
                ),
            )
            _u64(
                output,
                _binary64_bits(
                    relevance,
                    f"source relevance {index}",
                ),
            )
    return bytes(output)


def settle_native_l0_l4_full_field_bank(
    *,
    assembly_id: str,
    observed_substreams: Mapping[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]
    ],
    states: Mapping[PhysicalSense, SenseBoundaryState],
) -> ImmutableFullFieldBank:
    """Settle the complete boundary with one Python-to-Rust batch call."""

    native_core = _native_core()
    candidate = encode_native_l0_l4_episode(
        assembly_id=assembly_id,
        observed_substreams=observed_substreams,
        states=states,
        config_payload=_canonical_config_payload(native_core),
    )
    result = native_core.settle_native_l0_l4_full_field_batch(candidate)
    if not isinstance(result, ImmutableFullFieldBank):
        raise TypeError("native settlement did not return an immutable full-field bank")
    return result


__all__ = (
    "ImmutableFullFieldBank",
    "encode_native_l0_l4_episode",
    "settle_native_l0_l4_full_field_bank",
)
