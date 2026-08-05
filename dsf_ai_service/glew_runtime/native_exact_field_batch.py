"""Exact current-organism boundary reconstructed from one native field bank.

Rust settles every physical port through canonical L0--L4 in one call.  This
module validates the immutable bank and reconstructs only the existing typed
Python boundary objects consumed above L4.  It performs no field mathematics,
meaning assignment, similarity scoring, or reduced projection.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import struct
from typing import Mapping

from .model import ReceiptRecord, receipt_sha256
from .native_l0_l4_full_field_bank import (
    ImmutableFullFieldBank,
    settle_native_l0_l4_full_field_bank,
)
from .sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from .structural_port_basin import port_kernel_basin_from_trace_record


_BANK_MAGIC = b"GLNBK003"
_BANK_VERSION = 3
_FIELD_WIDTH_BYTES = 7 * 8
_HEX = frozenset("0123456789abcdef")


class NativeExactFieldBatchError(RuntimeError):
    """The native bank differs from the current exact boundary contract."""


@dataclass(frozen=True, slots=True)
class _PortAuthority:
    global_index: int
    native: object
    assembly_id: str
    profile: object
    input_payloads: tuple[bytes, ...]
    trace_digest: str
    trace_payload: bytes
    basin: object
    basin_payloads: tuple[bytes, ...]
    source_sample_commitment_sha256: str
    source_l0_l4_intervals: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class NativeExactFieldPortResult:
    global_index: int
    profile: object
    input_payloads: tuple[bytes, ...]
    trace_digest: str
    trace_payload: bytes
    basin: object
    basin_payloads: tuple[bytes, ...]
    source_sample_commitment_sha256: str
    source_l0_l4_intervals: tuple[tuple[int, int], ...]
    _authority: _PortAuthority

    def verify_construction(
        self,
        *,
        global_index: int,
        native: object,
        assembly_id: str,
    ) -> None:
        authority = self._authority
        if (
            not isinstance(authority, _PortAuthority)
            or global_index != self.global_index
            or global_index != authority.global_index
            or native is not authority.native
            or assembly_id != authority.assembly_id
            or self.profile is not authority.profile
            or self.input_payloads is not authority.input_payloads
            or self.trace_digest != authority.trace_digest
            or self.trace_payload is not authority.trace_payload
            or self.basin is not authority.basin
            or self.basin_payloads is not authority.basin_payloads
            or self.source_sample_commitment_sha256
            != authority.source_sample_commitment_sha256
            or self.source_l0_l4_intervals
            is not authority.source_l0_l4_intervals
        ):
            raise NativeExactFieldBatchError(
                "native exact-field result left its admitted physical input"
            )


@dataclass(frozen=True, slots=True)
class _BankPort:
    sense_index: int
    topology_index: int
    sensor_id: str
    substream_id: str
    trace_sha256: str
    basin_sha256: str
    tuple_sha256s: tuple[str, ...]
    gates: tuple[tuple[int, int], ...]
    field_row_count: int


@dataclass(frozen=True, slots=True)
class NativeExactFieldBatch:
    bank: ImmutableFullFieldBank
    results: tuple[NativeExactFieldPortResult, ...]
    record_payloads: tuple[bytes, ...]


class _Reader:
    def __init__(self, payload: bytes) -> None:
        if not isinstance(payload, bytes):
            raise TypeError("native field bank must be immutable bytes")
        self.payload = payload
        self.offset = 0

    def take(self, length: int) -> bytes:
        if isinstance(length, bool) or not isinstance(length, int) or length < 0:
            raise NativeExactFieldBatchError("native bank length is invalid")
        end = self.offset + length
        if end > len(self.payload):
            raise NativeExactFieldBatchError(
                "native bank ended before its declared structure"
            )
        value = self.payload[self.offset:end]
        self.offset = end
        return value

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def text(self) -> str:
        try:
            return self.take(self.u16()).decode("utf-8")
        except UnicodeDecodeError as error:
            raise NativeExactFieldBatchError(
                "native bank text is not UTF-8"
            ) from error

    def digest(self) -> str:
        return self.take(32).hex()


def _require_digest(value: str, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise NativeExactFieldBatchError(f"{label} is not a SHA-256")
    return value


def _parse_bank(
    bank: ImmutableFullFieldBank,
    *,
    assembly_id: str,
    states: Mapping[PhysicalSense, SenseBoundaryState],
) -> tuple[tuple[_BankPort, ...], dict[str, bytes]]:
    if bank.python_callback_count != 0:
        raise NativeExactFieldBatchError(
            "native L0-L4 settlement called back into Python"
        )
    payload = bytes(bank.as_bytes())
    if hashlib.sha256(payload).hexdigest() != bank.payload_sha256:
        raise NativeExactFieldBatchError("native field bank bytes changed")
    reader = _Reader(payload)
    if reader.take(8) != _BANK_MAGIC or reader.u16() != _BANK_VERSION:
        raise NativeExactFieldBatchError("native field bank schema changed")
    config_sha256 = reader.digest()
    candidate_sha256 = reader.digest()
    root_sha256 = reader.digest()
    for value, label in (
        (config_sha256, "kernel configuration"),
        (candidate_sha256, "physical episode"),
        (root_sha256, "field root"),
    ):
        _require_digest(value, label)
    if root_sha256 != bank.root_sha256:
        raise NativeExactFieldBatchError("native field root changed")
    if reader.text() != assembly_id:
        raise NativeExactFieldBatchError(
            "native field bank belongs to another causal assembly"
        )
    state_codes = tuple(reader.u8() for _sense in SENSE_ORDER)
    expected_codes = {
        SenseBoundaryState.OBSERVED: 0,
        SenseBoundaryState.QUIESCENT: 1,
        SenseBoundaryState.SENSOR_UNAVAILABLE: 2,
        SenseBoundaryState.UNKNOWN: 3,
    }
    if state_codes != tuple(expected_codes[states[sense]] for sense in SENSE_ORDER):
        raise NativeExactFieldBatchError("native sense states changed")
    source_sample_count = reader.u32()
    field_row_count = reader.u32()
    port_count = reader.u32()
    ports = []
    observed_field_rows = 0
    for _port_index in range(port_count):
        sense_index = reader.u8()
        topology_index = reader.u32()
        sensor_id = reader.text()
        substream_id = reader.text()
        trace_sha256 = reader.digest()
        basin_sha256 = reader.digest()
        tuple_sha256s = tuple(reader.digest() for _item in range(reader.u32()))
        gates = tuple(
            (reader.u32(), reader.u32())
            for _item in range(reader.u32())
        )
        row_count = reader.u32()
        reader.take(row_count * _FIELD_WIDTH_BYTES)
        observed_field_rows += row_count
        ports.append(
            _BankPort(
                sense_index=sense_index,
                topology_index=topology_index,
                sensor_id=sensor_id,
                substream_id=substream_id,
                trace_sha256=trace_sha256,
                basin_sha256=basin_sha256,
                tuple_sha256s=tuple_sha256s,
                gates=gates,
                field_row_count=row_count,
            )
        )
    records: dict[str, bytes] = {}
    for _record_index in range(reader.u32()):
        digest = reader.digest()
        body = reader.take(reader.u32())
        if receipt_sha256(body) != digest:
            raise NativeExactFieldBatchError(
                "native bank record differs from its digest"
            )
        prior = records.setdefault(digest, body)
        if prior != body:
            raise NativeExactFieldBatchError(
                "native bank contains a receipt collision"
            )
    if reader.offset != len(payload):
        raise NativeExactFieldBatchError(
            "native bank has undeclared trailing bytes"
        )
    if (
        port_count != bank.port_count
        or source_sample_count != bank.source_sample_count
        or field_row_count != bank.field_row_count
        or observed_field_rows != field_row_count
    ):
        raise NativeExactFieldBatchError(
            "native bank counts changed across its immutable boundary"
        )
    return tuple(ports), records


def build_native_exact_field_batch(
    *,
    assembly_id: str,
    observed_substreams: Mapping[
        PhysicalSense, tuple[object, ...]
    ],
    states: Mapping[PhysicalSense, SenseBoundaryState],
) -> NativeExactFieldBatch:
    from .native_sensory_full_field import (
        _prepare_port,
        _source_l0_l4_intervals_from_trace,
    )

    bank = settle_native_l0_l4_full_field_bank(
        assembly_id=assembly_id,
        observed_substreams=observed_substreams,
        states=states,
    )
    bank_ports, records = _parse_bank(
        bank,
        assembly_id=assembly_id,
        states=states,
    )
    ordered_native = tuple(
        native
        for sense in SENSE_ORDER
        for native in observed_substreams.get(sense, ())
    )
    if len(bank_ports) != len(ordered_native):
        raise NativeExactFieldBatchError(
            "native field bank changed physical port cardinality"
        )
    results = []
    for global_index, (native, bank_port) in enumerate(
        zip(ordered_native, bank_ports, strict=True)
    ):
        expected_sense_index = tuple(SENSE_ORDER).index(native.sense)
        if (
            bank_port.sense_index != expected_sense_index
            or bank_port.topology_index != native.topology_index
            or bank_port.sensor_id != native.sensor_id
            or bank_port.substream_id != native.substream_id
        ):
            raise NativeExactFieldBatchError(
                "native field bank changed physical topology"
            )
        prepared = _prepare_port(native, assembly_id=assembly_id)
        for payload in prepared.input_payloads[:-1]:
            digest = receipt_sha256(payload)
            if records.get(digest) != payload:
                raise NativeExactFieldBatchError(
                    "native bank changed source or transduction evidence"
                )
        trace_payload = records.get(bank_port.trace_sha256)
        if trace_payload is None:
            raise NativeExactFieldBatchError(
                "native bank omitted an L0-L4 trace"
            )
        try:
            trace_identity = json.loads(trace_payload)
        except (TypeError, ValueError) as error:
            raise NativeExactFieldBatchError(
                "native L0-L4 trace is not canonical JSON"
            ) from error
        if (
            trace_identity.get("lane_id") != native.sense.value
            or trace_identity.get("port_id") != native.substream_id
        ):
            raise NativeExactFieldBatchError(
                "native L0-L4 trace crossed its physical port"
            )
        trace_record = ReceiptRecord(
            bank_port.trace_sha256,
            trace_payload,
        )
        basin, basin_payloads = port_kernel_basin_from_trace_record(
            lane_id=native.sense.value,
            port_id=native.substream_id,
            trace_record=trace_record,
        )
        tuple_payloads = basin_payloads[:-1]
        if (
            tuple(receipt_sha256(value) for value in tuple_payloads)
            != bank_port.tuple_sha256s
            or receipt_sha256(basin_payloads[-1])
            != bank_port.basin_sha256
            or basin.authority_receipt_sha256
            != bank_port.basin_sha256
            or len(basin.exact_dsf_field_tuples)
            != bank_port.field_row_count
        ):
            raise NativeExactFieldBatchError(
                "native bank changed an exact DSF tuple or basin"
            )
        source_intervals = _source_l0_l4_intervals_from_trace(
            trace_record,
            source_count=len(native.normalized_signal),
            tuple_count=len(basin.exact_dsf_field_tuples),
        )
        if source_intervals != bank_port.gates:
            raise NativeExactFieldBatchError(
                "native bank changed L0-L4 gate support"
            )
        input_payloads = prepared.input_payloads
        authority = _PortAuthority(
            global_index=global_index,
            native=native,
            assembly_id=assembly_id,
            profile=prepared.profile,
            input_payloads=input_payloads,
            trace_digest=bank_port.trace_sha256,
            trace_payload=trace_payload,
            basin=basin,
            basin_payloads=basin_payloads,
            source_sample_commitment_sha256=(
                prepared.source_sample_commitment_sha256
            ),
            source_l0_l4_intervals=source_intervals,
        )
        results.append(
            NativeExactFieldPortResult(
                global_index=global_index,
                profile=prepared.profile,
                input_payloads=input_payloads,
                trace_digest=bank_port.trace_sha256,
                trace_payload=trace_payload,
                basin=basin,
                basin_payloads=basin_payloads,
                source_sample_commitment_sha256=(
                    prepared.source_sample_commitment_sha256
                ),
                source_l0_l4_intervals=source_intervals,
                _authority=authority,
            )
        )
    return NativeExactFieldBatch(
        bank=bank,
        results=tuple(results),
        record_payloads=tuple(records.values()),
    )


__all__ = (
    "NativeExactFieldBatch",
    "NativeExactFieldBatchError",
    "NativeExactFieldPortResult",
    "build_native_exact_field_batch",
)
