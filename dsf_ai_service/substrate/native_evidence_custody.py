"""Lossless bounded custody for one verified native six-sense construction.

This module does not run or reinterpret L0--L4.  It preserves the exact
receipt bytes already produced by ``build_six_sense_full_field`` and indexes
the source, adapter, trace, and L1 ``N_gate`` evidence needed to revalidate
those bytes after the construction transaction ends.
"""

from __future__ import annotations

import base64
import json
import secrets
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_identifier,
    sha256_digest,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT,
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    MAX_NATIVE_SIGHT_SUBSTREAMS,
    MAX_NATIVE_SOUND_SUBSTREAMS,
    MAX_NATIVE_SUBSTREAMS_PER_SENSE,
    BuiltSixSenseFullField,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    SENSE_ORDER,
    SenseBoundaryState,
)


NATIVE_EVIDENCE_WITNESS_SCHEMA = (
    "guala.native_evidence_custody.witness.v1"
)
NATIVE_EVIDENCE_PORT_SCHEMA = (
    "guala.native_evidence_custody.port.v1"
)
NATIVE_EVIDENCE_RECORD_SCHEMA = (
    "guala.native_evidence_custody.record.v1"
)
NATIVE_EVIDENCE_TRANSITION_SCHEMA = (
    "guala.native_evidence_custody.transition_index.v1"
)
NATIVE_EVIDENCE_CUSTODY_AUTHORITY_PAYLOAD = (
    b"guala.native_evidence_custody.authority.v1"
)
SOURCE_EVIDENCE_STREAM_SCHEMA = "glew.provider.source_evidence_stream.v1"
KERNEL_NATIVE_INPUT_SCHEMAS = {
    "glew.provider.kernel_native_input_result.v2",
    "glew.provider.kernel_native_input_result.v3",
}
COMPLETE_L0_L4_TRACE_SCHEMAS = {
    "glew.provider.complete_signed_port_l0_l4_trace.v3",
    "glew.provider.complete_physical_port_l0_l4_trace.v4",
}

# The maximum port count is derived from the already-enforced native topology
# boundary: sound + sight + the other four physical senses.
MAX_NATIVE_EVIDENCE_PORTS = (
    MAX_NATIVE_SOUND_SUBSTREAMS
    + MAX_NATIVE_SIGHT_SUBSTREAMS
    + (len(SENSE_ORDER) - 2) * MAX_NATIVE_SUBSTREAMS_PER_SENSE
)
# A trace may produce one exact tuple receipt per admitted sample.  Ten
# additional receipts per port cover source, calibration, relevance, adapter,
# profile, topology, trace, basin, boundary, and assembly dependencies.
MAX_NATIVE_EVIDENCE_RECEIPTS = (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT
    + MAX_NATIVE_EVIDENCE_PORTS * 10
    + len(SENSE_ORDER)
    + 2
)
# One admitted sample can appear in seven exact receipt structures: source,
# adapter, L0, L1, L2, L3, and L4/tuple support.  The transient live ceiling
# allows 512 canonical bytes for each structure plus 64 KiB of fixed
# topology/authority metadata per possible port.  Raw custody lasts only for
# the recent audit window; learned state uses ``NativeEvidenceTransitionIndex``.
MAX_NATIVE_EVIDENCE_RECEIPT_BYTES = (
    MAX_NATIVE_SAMPLES_PER_SETTLEMENT * (7 * 512)
    + MAX_NATIVE_EVIDENCE_PORTS * 65536
)
# Base64 is bounded by four output bytes per three input bytes, plus the
# canonical record manifest and fixed per-receipt metadata.
MAX_NATIVE_EVIDENCE_RECORD_BYTES = (
    ((MAX_NATIVE_EVIDENCE_RECEIPT_BYTES + 2) // 3) * 4
    + MAX_NATIVE_EVIDENCE_RECEIPTS * 256
)
MAX_NATIVE_EVIDENCE_PREPARED_ADMISSIONS = 8
_VERIFIED_NATIVE_EVIDENCE_CONSTRUCTION_AUTHORITY = object()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str):
        raise ReceiptError(f"{name} is not an exact fraction")
    try:
        exact = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ReceiptError(f"{name} is not an exact fraction") from error
    if f"{exact.numerator}/{exact.denominator}" != value:
        raise ReceiptError(f"{name} is not canonical")
    return exact


def _json(payload: bytes, name: str) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReceiptError(f"{name} is not canonical JSON") from error
    if not isinstance(value, dict) or _canonical(value) != payload:
        raise ReceiptError(f"{name} is not canonical JSON")
    return value


def _receipt_references(value: object) -> tuple[str, ...]:
    values: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if (
                    isinstance(key, str)
                    and key.endswith("_receipt_sha256")
                    and isinstance(child, str)
                ):
                    values.append(child)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return tuple(values)


@dataclass(frozen=True, slots=True)
class NativePortEvidenceWitness:
    port_ordinal: int
    sense: str
    sensor_id: str
    substream_id: str
    topology_index: int
    source_evidence_stream_receipt_sha256: str
    kernel_native_input_receipt_sha256: str
    complete_l0_l4_trace_receipt_sha256: str
    source_sample_count: int
    source_timestamps: tuple[Fraction, ...]
    n_gates: tuple[int, ...]
    gate_supports: tuple[tuple[int, int], ...]

    def payload(self) -> dict[str, object]:
        return {
            "complete_l0_l4_trace_receipt_sha256": (
                self.complete_l0_l4_trace_receipt_sha256
            ),
            "kernel_native_input_receipt_sha256": (
                self.kernel_native_input_receipt_sha256
            ),
            "n_gates": list(self.n_gates),
            "gate_supports": [
                [start, end] for start, end in self.gate_supports
            ],
            "port_ordinal": self.port_ordinal,
            "schema": NATIVE_EVIDENCE_PORT_SCHEMA,
            "sense": self.sense,
            "sensor_id": self.sensor_id,
            "source_evidence_stream_receipt_sha256": (
                self.source_evidence_stream_receipt_sha256
            ),
            "source_sample_count": self.source_sample_count,
            "source_timestamps": [
                f"{value.numerator}/{value.denominator}"
                for value in self.source_timestamps
            ],
            "substream_id": self.substream_id,
            "topology_index": self.topology_index,
        }

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "NativePortEvidenceWitness":
        expected = {
            "complete_l0_l4_trace_receipt_sha256",
            "gate_supports",
            "kernel_native_input_receipt_sha256",
            "n_gates",
            "port_ordinal",
            "schema",
            "sense",
            "sensor_id",
            "source_evidence_stream_receipt_sha256",
            "source_sample_count",
            "source_timestamps",
            "substream_id",
            "topology_index",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != NATIVE_EVIDENCE_PORT_SCHEMA
            or not isinstance(value.get("n_gates"), list)
            or not isinstance(value.get("gate_supports"), list)
            or not isinstance(value.get("source_timestamps"), list)
        ):
            raise ReceiptError("native evidence port record changed")
        return cls(
            port_ordinal=value["port_ordinal"],
            sense=value["sense"],
            sensor_id=value["sensor_id"],
            substream_id=value["substream_id"],
            topology_index=value["topology_index"],
            source_evidence_stream_receipt_sha256=(
                value["source_evidence_stream_receipt_sha256"]
            ),
            kernel_native_input_receipt_sha256=(
                value["kernel_native_input_receipt_sha256"]
            ),
            complete_l0_l4_trace_receipt_sha256=(
                value["complete_l0_l4_trace_receipt_sha256"]
            ),
            source_sample_count=value["source_sample_count"],
            source_timestamps=tuple(
                _fraction(item, "native evidence source timestamp")
                for item in value["source_timestamps"]
            ),
            n_gates=tuple(value["n_gates"]),
            gate_supports=tuple(
                (item[0], item[1])
                for item in value["gate_supports"]
                if isinstance(item, list) and len(item) == 2
            ),
        )

    def verify_index(self) -> None:
        for value, name in (
            (self.sense, "native evidence sense"),
            (self.sensor_id, "native evidence sensor"),
            (self.substream_id, "native evidence substream"),
        ):
            require_identifier(value, name)
        if (
            isinstance(self.port_ordinal, bool)
            or not isinstance(self.port_ordinal, int)
            or self.port_ordinal < 0
            or isinstance(self.topology_index, bool)
            or not isinstance(self.topology_index, int)
            or self.topology_index < 0
        ):
            raise ReceiptError("native evidence topology index changed")
        if (
            isinstance(self.source_sample_count, bool)
            or not isinstance(self.source_sample_count, int)
            or not 0 < self.source_sample_count
            <= MAX_NATIVE_SAMPLES_PER_SUBSTREAM
            or len(self.source_timestamps) != self.source_sample_count
        ):
            raise ReceiptError("native evidence sample count exceeds custody")
        previous: Fraction | None = None
        for timestamp in self.source_timestamps:
            if (
                not isinstance(timestamp, Fraction)
                or (previous is not None and timestamp <= previous)
            ):
                raise ReceiptError("native evidence timestamp index changed")
            previous = timestamp
        for value, name in (
            (
                self.source_evidence_stream_receipt_sha256,
                "native source evidence",
            ),
            (
                self.kernel_native_input_receipt_sha256,
                "native kernel input",
            ),
            (
                self.complete_l0_l4_trace_receipt_sha256,
                "native complete L0-L4 trace",
            ),
        ):
            sha256_digest(value, name)
        if (
            not self.n_gates
            or len(self.gate_supports) != len(self.n_gates)
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in self.n_gates
            )
        ):
            raise ReceiptError("native L1 N_gate index changed")
        prior_end = -1
        for support in self.gate_supports:
            if (
                not isinstance(support, tuple)
                or len(support) != 2
                or isinstance(support[0], bool)
                or not isinstance(support[0], int)
                or isinstance(support[1], bool)
                or not isinstance(support[1], int)
                or support[0] != prior_end + 1
                or not support[0] <= support[1]
                < self.source_sample_count
            ):
                raise ReceiptError("native gate support index changed")
            prior_end = support[1]
        if prior_end != self.source_sample_count - 1:
            raise ReceiptError("native gate support index did not close")

    def verify(
        self,
        registry: ReceiptRegistry,
    ) -> tuple[tuple[int, Fraction, Fraction, Fraction, Fraction], ...]:
        self.verify_index()

        source = _json(
            registry.resolve(
                self.source_evidence_stream_receipt_sha256,
                "native source evidence",
            ),
            "native source evidence",
        )
        raw_samples = source.get("samples")
        if (
            source.get("schema") != SOURCE_EVIDENCE_STREAM_SCHEMA
            or source.get("lane_id") != self.sense
            or source.get("port_id") != self.substream_id
            or not isinstance(raw_samples, list)
            or len(raw_samples) != self.source_sample_count
        ):
            raise ReceiptError("native source evidence changed identity")
        samples = []
        previous_time: Fraction | None = None
        for index, raw_sample in enumerate(raw_samples):
            if (
                not isinstance(raw_sample, dict)
                or raw_sample.get("source_index") != index
            ):
                raise ReceiptError("native source evidence changed order")
            timestamp = _fraction(
                raw_sample.get("timestamp"),
                "native source timestamp",
            )
            signal = _fraction(
                raw_sample.get("signal"),
                "native source signal",
            )
            relevance = _fraction(
                raw_sample.get("relevance"),
                "native source relevance",
            )
            phase = _fraction(
                raw_sample.get("phase_turns"),
                "native source phase",
            )
            if previous_time is not None and timestamp <= previous_time:
                raise ReceiptError("native source time is not causal")
            if not -1 <= signal <= 1 or not 0 <= relevance <= 1:
                raise ReceiptError("native source sample left calibration")
            previous_time = timestamp
            samples.append((index, timestamp, signal, relevance, phase))
        if tuple(value[1] for value in samples) != self.source_timestamps:
            raise ReceiptError("native source timestamp index changed")

        adapter = _json(
            registry.resolve(
                self.kernel_native_input_receipt_sha256,
                "native kernel input",
            ),
            "native kernel input",
        )
        adapter_samples = adapter.get("samples")
        if (
            adapter.get("schema") not in KERNEL_NATIVE_INPUT_SCHEMAS
            or adapter.get("lane_id") != self.sense
            or adapter.get("port_id") != self.substream_id
            or adapter.get("source_stream_receipt_sha256")
            != self.source_evidence_stream_receipt_sha256
            or not isinstance(adapter_samples, list)
            or len(adapter_samples) != self.source_sample_count
        ):
            raise ReceiptError("native kernel input changed identity")
        for source_sample, adapted in zip(
            samples,
            adapter_samples,
            strict=True,
        ):
            if (
                not isinstance(adapted, dict)
                or adapted.get("source_index") != source_sample[0]
                or _fraction(
                    adapted.get("timestamp"),
                    "native adapter timestamp",
                )
                != source_sample[1]
                or _fraction(
                    adapted.get("l0_relevance"),
                    "native adapter relevance",
                )
                != source_sample[3]
            ):
                raise ReceiptError("native kernel input changed source custody")
            _fraction(
                adapted.get("dimensionless_field"),
                "native adapter field",
            )

        trace = _json(
            registry.resolve(
                self.complete_l0_l4_trace_receipt_sha256,
                "native complete L0-L4 trace",
            ),
            "native complete L0-L4 trace",
        )
        l0 = trace.get("L0_SEV")
        l1 = trace.get("L1_GateL1State")
        l2 = trace.get("L2_GateInterpretation")
        l3 = trace.get("L3_ResonanceResult")
        l4 = trace.get("L4_DSF")
        if (
            trace.get("schema") not in COMPLETE_L0_L4_TRACE_SCHEMAS
            or trace.get("lane_id") != self.sense
            or trace.get("port_id") != self.substream_id
            or trace.get("source_stream_receipt_sha256")
            != self.source_evidence_stream_receipt_sha256
            or trace.get("adapter_result_receipt_sha256")
            != self.kernel_native_input_receipt_sha256
            or not isinstance(l0, list)
            or len(l0) != self.source_sample_count
            or not all(
                isinstance(layer, list)
                for layer in (l1, l2, l3, l4)
            )
            or not len(l1) == len(l2) == len(l3) == len(l4)
            or not l1
        ):
            raise ReceiptError("native complete L0-L4 trace is incomplete")
        actual_n_gates = tuple(
            row.get("N_gate") if isinstance(row, dict) else None
            for row in l1
        )
        if (
            any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in actual_n_gates
            )
            or actual_n_gates != self.n_gates
        ):
            raise ReceiptError("native L1 N_gate evidence changed")
        prior_end = -1
        actual_supports = []
        for rows in zip(l1, l2, l3, strict=True):
            intervals = []
            for row in rows:
                if not isinstance(row, dict):
                    raise ReceiptError("native gate evidence changed shape")
                start = row.get("start_idx")
                end = row.get("end_idx")
                if (
                    isinstance(start, bool)
                    or not isinstance(start, int)
                    or isinstance(end, bool)
                    or not isinstance(end, int)
                    or not 0 <= start <= end
                    < self.source_sample_count
                ):
                    raise ReceiptError("native gate left its source grid")
                intervals.append((start, end))
            if len(set(intervals)) != 1 or intervals[0][0] != prior_end + 1:
                raise ReceiptError("native gate supports diverged")
            prior_end = intervals[0][1]
            actual_supports.append(intervals[0])
        if prior_end != self.source_sample_count - 1:
            raise ReceiptError("native gate support did not close source grid")
        if tuple(actual_supports) != self.gate_supports:
            raise ReceiptError("native gate support index changed")
        return tuple(samples)


@dataclass(frozen=True, slots=True)
class _VerifiedNativeEvidenceIntegrity:
    original_profile_binding_sha256: str
    ports: tuple[NativePortEvidenceWitness, ...]
    receipt_records: tuple[ReceiptRecord, ...]
    total_receipt_bytes: int
    authority_receipt_sha256: str

    def matches(self, witness: "NativeEvidenceCustodyWitness") -> bool:
        return (
            self.original_profile_binding_sha256
            == witness.original_profile_binding_sha256
            and self.ports is witness.ports
            and self.receipt_records is witness.receipt_records
            and self.total_receipt_bytes == witness.total_receipt_bytes
            and self.authority_receipt_sha256
            == witness.authority_receipt_sha256
        )


@dataclass(frozen=True, slots=True)
class NativeEvidenceCustodyWitness:
    original_profile_binding_sha256: str
    ports: tuple[NativePortEvidenceWitness, ...]
    receipt_records: tuple[ReceiptRecord, ...]
    total_receipt_bytes: int
    authority_receipt_sha256: str
    _verified_integrity: _VerifiedNativeEvidenceIntegrity | None = field(
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
            _VerifiedNativeEvidenceIntegrity(
                original_profile_binding_sha256=(
                    self.original_profile_binding_sha256
                ),
                ports=self.ports,
                receipt_records=self.receipt_records,
                total_receipt_bytes=self.total_receipt_bytes,
                authority_receipt_sha256=self.authority_receipt_sha256,
            ),
        )

    def payload(self) -> dict[str, object]:
        return {
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "original_profile_binding_sha256": (
                self.original_profile_binding_sha256
            ),
            "ports": [value.payload() for value in self.ports],
            "receipt_manifest": [
                {
                    "byte_count": len(value.payload),
                    "digest": value.digest,
                }
                for value in self.receipt_records
            ],
            "receipt_record_count": len(self.receipt_records),
            "schema": NATIVE_EVIDENCE_WITNESS_SCHEMA,
            "total_receipt_bytes": self.total_receipt_bytes,
        }

    def authority_payload(self) -> bytes:
        payload = self.payload()
        payload["authority_receipt_sha256"] = None
        return _canonical(payload)

    def record(self) -> dict[str, object]:
        self.verify()
        value = {
            **self.payload(),
            "receipt_records": [
                {
                    "digest": record.digest,
                    "payload_base64": base64.b64encode(
                        record.payload
                    ).decode("ascii"),
                    "schema": NATIVE_EVIDENCE_RECORD_SCHEMA,
                }
                for record in self.receipt_records
            ],
        }
        if len(_canonical(value)) > MAX_NATIVE_EVIDENCE_RECORD_BYTES:
            raise ReceiptError("native evidence cold record exceeds custody")
        return value

    @classmethod
    def from_built(
        cls,
        built: BuiltSixSenseFullField,
    ) -> "NativeEvidenceCustodyWitness":
        if not isinstance(built, BuiltSixSenseFullField):
            raise TypeError("native evidence witness requires a typed build")
        transaction_owned = (
            built.has_transaction_construction_authority
        )
        if transaction_owned:
            built.verify_construction(
                boundary=built.boundary,
                receipt_registry=built.receipt_registry,
            )
        else:
            built.boundary.verify(built.receipt_registry)
        records = built.receipt_registry.records
        registry = ReceiptRegistry(
            built.receipt_registry.profile_binding_sha256,
            records,
        )
        ports = []
        for boundary in built.boundary.boundaries:
            if boundary.state is not SenseBoundaryState.OBSERVED:
                continue
            for substream in boundary.substreams:
                trace_receipts = {
                    item.source_l0_l4_trace_receipt_sha256
                    for item in substream.kernel_basin.exact_dsf_field_tuples
                }
                if len(trace_receipts) != 1:
                    raise ReceiptError(
                        "native evidence port crosses L0-L4 traces"
                    )
                trace_digest = next(iter(trace_receipts))
                trace = _json(
                    registry.resolve(
                        trace_digest,
                        "native complete L0-L4 trace",
                    ),
                    "native complete L0-L4 trace",
                )
                l1 = trace.get("L1_GateL1State")
                if not isinstance(l1, list):
                    raise ReceiptError("native evidence lacks L1 N_gate")
                source = _json(
                    registry.resolve(
                        substream.profile
                        .physical_derivation_receipt_sha256,
                        "native source evidence",
                    ),
                    "native source evidence",
                )
                source_samples = source.get("samples")
                if not isinstance(source_samples, list):
                    raise ReceiptError(
                        "native source evidence lacks exact timestamps"
                    )
                port = NativePortEvidenceWitness(
                    port_ordinal=len(ports),
                    sense=boundary.sense.value,
                    sensor_id=substream.profile.sensor_id,
                    substream_id=substream.profile.substream_id,
                    topology_index=substream.profile.topology_index,
                    source_evidence_stream_receipt_sha256=(
                        substream.profile
                        .physical_derivation_receipt_sha256
                    ),
                    kernel_native_input_receipt_sha256=(
                        trace.get("adapter_result_receipt_sha256")
                    ),
                    complete_l0_l4_trace_receipt_sha256=trace_digest,
                    source_sample_count=len(source_samples),
                    source_timestamps=tuple(
                        _fraction(
                            item.get("timestamp")
                            if isinstance(item, dict) else None,
                            "native source timestamp",
                        )
                        for item in source_samples
                    ),
                    n_gates=tuple(
                        row.get("N_gate")
                        if isinstance(row, dict) else None
                        for row in l1
                    ),
                    gate_supports=tuple(
                        (
                            row.get("start_idx"),
                            row.get("end_idx"),
                        )
                        if isinstance(row, dict)
                        else (None, None)
                        for row in l1
                    ),
                )
                if transaction_owned:
                    port.verify_index()
                else:
                    port.verify(registry)
                ports.append(port)
        total = sum(len(record.payload) for record in records)
        provisional = cls(
            original_profile_binding_sha256=(
                built.receipt_registry.profile_binding_sha256
            ),
            ports=tuple(ports),
            receipt_records=records,
            total_receipt_bytes=total,
            authority_receipt_sha256="0" * 64,
        )
        authority = receipt_sha256(provisional.authority_payload())
        witness = cls(
            original_profile_binding_sha256=(
                provisional.original_profile_binding_sha256
            ),
            ports=provisional.ports,
            receipt_records=provisional.receipt_records,
            total_receipt_bytes=provisional.total_receipt_bytes,
            authority_receipt_sha256=authority,
        )
        if transaction_owned:
            if (
                witness.receipt_records
                is not built.receipt_registry.records
                or witness.original_profile_binding_sha256
                != built.receipt_registry.profile_binding_sha256
                or not witness.ports
                or len(witness.ports) > MAX_NATIVE_EVIDENCE_PORTS
                or not witness.receipt_records
                or len(witness.receipt_records)
                > MAX_NATIVE_EVIDENCE_RECEIPTS
                or witness.total_receipt_bytes
                != sum(
                    len(record.payload)
                    for record in witness.receipt_records
                )
                or witness.total_receipt_bytes
                > MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
                or tuple(
                    port.port_ordinal for port in witness.ports
                )
                != tuple(range(len(witness.ports)))
                or receipt_sha256(witness.authority_payload())
                != witness.authority_receipt_sha256
            ):
                raise ReceiptError(
                    "fresh native witness left verified construction"
                )
        else:
            witness.verify()
        return witness

    @classmethod
    def verified_from_built(
        cls,
        built: BuiltSixSenseFullField,
    ) -> tuple[
        "NativeEvidenceCustodyWitness",
        "VerifiedNativeEvidenceWitnessCapability",
    ]:
        """Return one freshly verified witness and unforgeable linkage."""
        witness = cls.from_built(built)
        return (
            witness,
            VerifiedNativeEvidenceWitnessCapability(
                witness=witness,
                _construction_authority=(
                    _VERIFIED_NATIVE_EVIDENCE_CONSTRUCTION_AUTHORITY
                ),
            ),
        )

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "NativeEvidenceCustodyWitness":
        expected = {
            "authority_receipt_sha256",
            "original_profile_binding_sha256",
            "ports",
            "receipt_manifest",
            "receipt_record_count",
            "receipt_records",
            "schema",
            "total_receipt_bytes",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != NATIVE_EVIDENCE_WITNESS_SCHEMA
            or not isinstance(value.get("ports"), list)
            or not isinstance(value.get("receipt_records"), list)
            or not isinstance(value.get("receipt_manifest"), list)
            or len(_canonical(dict(value)))
            > MAX_NATIVE_EVIDENCE_RECORD_BYTES
        ):
            raise ReceiptError("native evidence cold witness changed")
        records = []
        for item in value["receipt_records"]:
            if (
                not isinstance(item, Mapping)
                or set(item) != {
                    "digest",
                    "payload_base64",
                    "schema",
                }
                or item.get("schema") != NATIVE_EVIDENCE_RECORD_SCHEMA
            ):
                raise ReceiptError("native evidence cold receipt changed")
            try:
                payload = base64.b64decode(
                    item["payload_base64"],
                    validate=True,
                )
            except (TypeError, ValueError) as error:
                raise ReceiptError(
                    "native evidence cold receipt is unreadable"
                ) from error
            records.append(ReceiptRecord(item["digest"], payload))
        witness = cls(
            original_profile_binding_sha256=(
                value["original_profile_binding_sha256"]
            ),
            ports=tuple(
                NativePortEvidenceWitness.from_record(item)
                for item in value["ports"]
            ),
            receipt_records=tuple(records),
            total_receipt_bytes=value["total_receipt_bytes"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )
        witness.verify()
        if witness.payload()["receipt_manifest"] != list(
            value["receipt_manifest"]
        ) or len(witness.receipt_records) != value["receipt_record_count"]:
            raise ReceiptError("native evidence cold manifest changed")
        return witness

    def verify(self) -> None:
        verified = self._verified_integrity
        if verified is not None:
            if not verified.matches(self):
                raise ReceiptError(
                    "native evidence changed after verified integrity"
                )
            return
        sha256_digest(
            self.original_profile_binding_sha256,
            "native evidence original profile",
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "native evidence witness authority",
        )
        if (
            not isinstance(self.ports, tuple)
            or not self.ports
            or len(self.ports) > MAX_NATIVE_EVIDENCE_PORTS
            or not isinstance(self.receipt_records, tuple)
            or not self.receipt_records
            or len(self.receipt_records) > MAX_NATIVE_EVIDENCE_RECEIPTS
        ):
            raise ReceiptError("native evidence custody extent changed")
        actual_total = sum(
            len(record.payload) for record in self.receipt_records
        )
        if (
            isinstance(self.total_receipt_bytes, bool)
            or not isinstance(self.total_receipt_bytes, int)
            or self.total_receipt_bytes != actual_total
            or actual_total > MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
        ):
            raise ReceiptError("native evidence byte custody changed")
        if (
            len({record.digest for record in self.receipt_records})
            != len(self.receipt_records)
        ):
            raise ReceiptError("native evidence receipt repeats")
        registry = ReceiptRegistry(
            self.original_profile_binding_sha256,
            self.receipt_records,
        )
        keys = tuple(
            (
                port.port_ordinal,
                port.sense,
                port.topology_index,
                port.substream_id,
            )
            for port in self.ports
        )
        if (
            tuple(port.port_ordinal for port in self.ports)
            != tuple(range(len(self.ports)))
            or len(set(keys)) != len(keys)
            or sum(port.source_sample_count for port in self.ports)
            > MAX_NATIVE_SAMPLES_PER_SETTLEMENT
        ):
            raise ReceiptError("native evidence port order changed")
        for port in self.ports:
            port.verify(registry)
        for record in self.receipt_records:
            try:
                decoded = json.loads(record.payload)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            for dependency in _receipt_references(decoded):
                registry.resolve(
                    dependency,
                    "native evidence receipt dependency",
                )
        if receipt_sha256(self.authority_payload()) != (
            self.authority_receipt_sha256
        ):
            raise ReceiptError("native evidence witness authority changed")
        self._retain_verified_integrity()

    def registry(self) -> ReceiptRegistry:
        self.verify()
        return ReceiptRegistry(
            self.original_profile_binding_sha256,
            self.receipt_records,
        )

    def transition_index(self) -> "NativeEvidenceTransitionIndex":
        return NativeEvidenceTransitionIndex.from_witness(self)


@dataclass(frozen=True, slots=True)
class VerifiedNativeEvidenceWitnessCapability:
    """Identity authority for one freshly verified native witness."""

    witness: NativeEvidenceCustodyWitness
    _construction_authority: object

    def verify_linkage(
        self,
        witness: NativeEvidenceCustodyWitness,
    ) -> None:
        if (
            self._construction_authority
            is not _VERIFIED_NATIVE_EVIDENCE_CONSTRUCTION_AUTHORITY
            or self.witness is not witness
            or receipt_sha256(witness.authority_payload())
            != witness.authority_receipt_sha256
        ):
            raise ReceiptError(
                "verified native witness changed construction identity"
            )

    def retain_verified_integrity(
        self,
        witness: NativeEvidenceCustodyWitness,
    ) -> None:
        self.verify_linkage(witness)
        witness._retain_verified_integrity()


@dataclass(frozen=True, slots=True)
class _VerifiedNativeEvidenceTransitionIntegrity:
    transient_witness_receipt_sha256: str
    original_profile_binding_sha256: str
    ports: tuple[NativePortEvidenceWitness, ...]
    transient_receipt_manifest_sha256: str
    transient_receipt_record_count: int
    transient_receipt_bytes: int
    authority_receipt_sha256: str

    def matches(self, index: "NativeEvidenceTransitionIndex") -> bool:
        return (
            self.transient_witness_receipt_sha256
            == index.transient_witness_receipt_sha256
            and self.original_profile_binding_sha256
            == index.original_profile_binding_sha256
            and self.ports is index.ports
            and self.transient_receipt_manifest_sha256
            == index.transient_receipt_manifest_sha256
            and self.transient_receipt_record_count
            == index.transient_receipt_record_count
            and self.transient_receipt_bytes
            == index.transient_receipt_bytes
            and self.authority_receipt_sha256
            == index.authority_receipt_sha256
        )


@dataclass(frozen=True, slots=True)
class NativeEvidenceTransitionIndex:
    """Durable structural-temporal index after transient raw retirement."""

    transient_witness_receipt_sha256: str
    original_profile_binding_sha256: str
    ports: tuple[NativePortEvidenceWitness, ...]
    transient_receipt_manifest_sha256: str
    transient_receipt_record_count: int
    transient_receipt_bytes: int
    authority_receipt_sha256: str
    _verified_integrity: (
        _VerifiedNativeEvidenceTransitionIntegrity | None
    ) = field(
        init=False,
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def payload(self) -> dict[str, object]:
        return {
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "original_profile_binding_sha256": (
                self.original_profile_binding_sha256
            ),
            "ports": [value.payload() for value in self.ports],
            "raw_retention_policy": "bounded-recent-audit-window",
            "schema": NATIVE_EVIDENCE_TRANSITION_SCHEMA,
            "transient_receipt_bytes": self.transient_receipt_bytes,
            "transient_receipt_manifest_sha256": (
                self.transient_receipt_manifest_sha256
            ),
            "transient_receipt_record_count": (
                self.transient_receipt_record_count
            ),
            "transient_witness_receipt_sha256": (
                self.transient_witness_receipt_sha256
            ),
        }

    def authority_payload(self) -> bytes:
        payload = self.payload()
        payload["authority_receipt_sha256"] = None
        return _canonical(payload)

    def record(self) -> dict[str, object]:
        self.verify()
        return self.payload()

    @classmethod
    def from_witness(
        cls,
        witness: NativeEvidenceCustodyWitness,
    ) -> "NativeEvidenceTransitionIndex":
        if not isinstance(witness, NativeEvidenceCustodyWitness):
            raise TypeError(
                "native transition index requires a typed witness"
            )
        witness.verify()
        manifest = [
            {
                "byte_count": len(value.payload),
                "digest": value.digest,
            }
            for value in witness.receipt_records
        ]
        provisional = cls(
            transient_witness_receipt_sha256=(
                witness.authority_receipt_sha256
            ),
            original_profile_binding_sha256=(
                witness.original_profile_binding_sha256
            ),
            ports=witness.ports,
            transient_receipt_manifest_sha256=receipt_sha256(
                _canonical(manifest)
            ),
            transient_receipt_record_count=len(witness.receipt_records),
            transient_receipt_bytes=witness.total_receipt_bytes,
            authority_receipt_sha256="0" * 64,
        )
        result = cls(
            transient_witness_receipt_sha256=(
                provisional.transient_witness_receipt_sha256
            ),
            original_profile_binding_sha256=(
                provisional.original_profile_binding_sha256
            ),
            ports=provisional.ports,
            transient_receipt_manifest_sha256=(
                provisional.transient_receipt_manifest_sha256
            ),
            transient_receipt_record_count=(
                provisional.transient_receipt_record_count
            ),
            transient_receipt_bytes=(
                provisional.transient_receipt_bytes
            ),
            authority_receipt_sha256=receipt_sha256(
                provisional.authority_payload()
            ),
        )
        result.verify()
        return result

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "NativeEvidenceTransitionIndex":
        expected = {
            "authority_receipt_sha256",
            "original_profile_binding_sha256",
            "ports",
            "raw_retention_policy",
            "schema",
            "transient_receipt_bytes",
            "transient_receipt_manifest_sha256",
            "transient_receipt_record_count",
            "transient_witness_receipt_sha256",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema") != NATIVE_EVIDENCE_TRANSITION_SCHEMA
            or value.get("raw_retention_policy")
            != "bounded-recent-audit-window"
            or not isinstance(value.get("ports"), list)
        ):
            raise ReceiptError("native transition index record changed")
        result = cls(
            transient_witness_receipt_sha256=(
                value["transient_witness_receipt_sha256"]
            ),
            original_profile_binding_sha256=(
                value["original_profile_binding_sha256"]
            ),
            ports=tuple(
                NativePortEvidenceWitness.from_record(item)
                for item in value["ports"]
            ),
            transient_receipt_manifest_sha256=(
                value["transient_receipt_manifest_sha256"]
            ),
            transient_receipt_record_count=(
                value["transient_receipt_record_count"]
            ),
            transient_receipt_bytes=value["transient_receipt_bytes"],
            authority_receipt_sha256=value["authority_receipt_sha256"],
        )
        result.verify()
        return result

    def verify(self) -> None:
        verified = self._verified_integrity
        if verified is not None:
            if not verified.matches(self):
                raise ReceiptError(
                    "native transition changed after verified integrity"
                )
            return
        for value, name in (
            (
                self.transient_witness_receipt_sha256,
                "native transient witness",
            ),
            (
                self.original_profile_binding_sha256,
                "native original profile",
            ),
            (
                self.transient_receipt_manifest_sha256,
                "native transient manifest",
            ),
            (
                self.authority_receipt_sha256,
                "native transition index",
            ),
        ):
            sha256_digest(value, name)
        if (
            not isinstance(self.ports, tuple)
            or not self.ports
            or len(self.ports) > MAX_NATIVE_EVIDENCE_PORTS
            or isinstance(self.transient_receipt_record_count, bool)
            or not isinstance(self.transient_receipt_record_count, int)
            or not 0 < self.transient_receipt_record_count
            <= MAX_NATIVE_EVIDENCE_RECEIPTS
            or isinstance(self.transient_receipt_bytes, bool)
            or not isinstance(self.transient_receipt_bytes, int)
            or not 0 < self.transient_receipt_bytes
            <= MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
        ):
            raise ReceiptError("native transition index extent changed")
        if tuple(value.port_ordinal for value in self.ports) != tuple(
            range(len(self.ports))
        ):
            raise ReceiptError("native transition port order changed")
        for port in self.ports:
            port.verify_index()
        if receipt_sha256(self.authority_payload()) != (
            self.authority_receipt_sha256
        ):
            raise ReceiptError("native transition index authority changed")
        object.__setattr__(
            self,
            "_verified_integrity",
            _VerifiedNativeEvidenceTransitionIntegrity(
                transient_witness_receipt_sha256=(
                    self.transient_witness_receipt_sha256
                ),
                original_profile_binding_sha256=(
                    self.original_profile_binding_sha256
                ),
                ports=self.ports,
                transient_receipt_manifest_sha256=(
                    self.transient_receipt_manifest_sha256
                ),
                transient_receipt_record_count=(
                    self.transient_receipt_record_count
                ),
                transient_receipt_bytes=self.transient_receipt_bytes,
                authority_receipt_sha256=self.authority_receipt_sha256,
            ),
        )


_PREPARED_NATIVE_EVIDENCE_ADMISSION_AUTHORITY = object()
_NATIVE_EVIDENCE_ADMISSION_UNDO_AUTHORITY = object()


@dataclass(slots=True)
class _NativeEvidenceAdmissionState:
    phase: str
    commit_token: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedNativeEvidenceAdmission:
    """One owner-issued, still-unpublished exact native witness."""

    witness: NativeEvidenceCustodyWitness
    _token: str
    _state: _NativeEvidenceAdmissionState
    _owner_authority: object
    _construction_authority: object


@dataclass(frozen=True, slots=True)
class NativeEvidenceAdmissionCommitUndo:
    """Exact inverse authority for one still-current custody admission."""

    _prepared: PreparedNativeEvidenceAdmission
    _canonical_witness: NativeEvidenceCustodyWitness
    _retired_witnesses: tuple[NativeEvidenceCustodyWitness, ...]
    _prior_witness_order: tuple[str, ...]
    _was_duplicate: bool
    _commit_token: str
    _prior_mutation_tail: str
    _owner_authority: object
    _construction_authority: object


class NativeEvidenceCustodyOwner:
    """One bounded content-addressed recent/audit window for native bytes."""

    def __init__(
        self,
        *,
        max_retained_witnesses: int = 1,
        max_total_receipt_bytes: int = (
            MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
        ),
        max_receipt_bytes_per_witness: int = (
            MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
        ),
    ) -> None:
        if (
            isinstance(max_retained_witnesses, bool)
            or not isinstance(max_retained_witnesses, int)
            or not 1 <= max_retained_witnesses <= 8
            or isinstance(max_total_receipt_bytes, bool)
            or not isinstance(max_total_receipt_bytes, int)
            or not 1 <= max_total_receipt_bytes
            <= MAX_NATIVE_EVIDENCE_RECEIPT_BYTES * 8
            or isinstance(max_receipt_bytes_per_witness, bool)
            or not isinstance(max_receipt_bytes_per_witness, int)
            or not 1 <= max_receipt_bytes_per_witness
            <= MAX_NATIVE_EVIDENCE_RECEIPT_BYTES
            or max_receipt_bytes_per_witness > max_total_receipt_bytes
        ):
            raise ValueError("native evidence custody capacity changed")
        self._max_witnesses = max_retained_witnesses
        self._max_total_bytes = max_total_receipt_bytes
        self._max_per_witness = max_receipt_bytes_per_witness
        self._witnesses: OrderedDict[
            str,
            NativeEvidenceCustodyWitness,
        ] = OrderedDict()
        self._records: dict[str, ReceiptRecord] = {}
        self._record_refcounts: dict[str, int] = {}
        self._retired = 0
        self._mutation_tail = "0" * 64
        self._owner_authority = object()
        self._prepared: dict[
            str,
            PreparedNativeEvidenceAdmission,
        ] = {}
        self._lock = threading.RLock()

    def _require_prepared_locked(
        self,
        prepared: PreparedNativeEvidenceAdmission,
    ) -> PreparedNativeEvidenceAdmission:
        if (
            not isinstance(prepared, PreparedNativeEvidenceAdmission)
            or prepared._construction_authority
            is not _PREPARED_NATIVE_EVIDENCE_ADMISSION_AUTHORITY
            or prepared._owner_authority is not self._owner_authority
            or prepared._state.phase != "prepared"
            or self._prepared.get(prepared._token) is not prepared
        ):
            raise ValueError(
                "prepared native evidence admission changed custody"
            )
        return prepared

    @staticmethod
    def _remove_witness_locked(
        witness: NativeEvidenceCustodyWitness,
        *,
        witnesses: OrderedDict[str, NativeEvidenceCustodyWitness],
        records: dict[str, ReceiptRecord],
        refcounts: dict[str, int],
    ) -> None:
        digest = witness.authority_receipt_sha256
        if witnesses.get(digest) is not witness:
            raise RuntimeError(
                "native evidence inverse lost its admitted witness"
            )
        del witnesses[digest]
        for record in witness.receipt_records:
            remaining = refcounts.get(record.digest)
            if remaining is None or remaining <= 0:
                raise RuntimeError(
                    "native evidence inverse lost a receipt reference"
                )
            if remaining == 1:
                del refcounts[record.digest]
                retained = records.pop(record.digest, None)
                if retained is None or retained.payload != record.payload:
                    raise RuntimeError(
                        "native evidence inverse lost retained bytes"
                    )
            else:
                refcounts[record.digest] = remaining - 1

    @staticmethod
    def _add_witness_locked(
        witness: NativeEvidenceCustodyWitness,
        *,
        witnesses: OrderedDict[str, NativeEvidenceCustodyWitness],
        records: dict[str, ReceiptRecord],
        refcounts: dict[str, int],
    ) -> None:
        digest = witness.authority_receipt_sha256
        if digest in witnesses:
            raise RuntimeError(
                "native evidence inverse repeated a witness"
            )
        canonical_records: list[ReceiptRecord] = []
        for record in witness.receipt_records:
            retained = records.get(record.digest)
            if retained is not None and retained.payload != record.payload:
                raise RuntimeError(
                    "native evidence inverse found a content collision"
                )
            canonical = retained if retained is not None else record
            records[record.digest] = canonical
            refcounts[record.digest] = (
                refcounts.get(record.digest, 0) + 1
            )
            canonical_records.append(canonical)
        canonical_witness = (
            witness
            if all(
                canonical is original
                for canonical, original in zip(
                    canonical_records,
                    witness.receipt_records,
                    strict=True,
                )
            )
            else NativeEvidenceCustodyWitness(
                original_profile_binding_sha256=(
                    witness.original_profile_binding_sha256
                ),
                ports=witness.ports,
                receipt_records=tuple(canonical_records),
                total_receipt_bytes=witness.total_receipt_bytes,
                authority_receipt_sha256=(
                    witness.authority_receipt_sha256
                ),
            )
        )
        canonical_witness.verify()
        witnesses[digest] = canonical_witness

    def prepare_admission(
        self,
        witness: NativeEvidenceCustodyWitness,
        *,
        verified_capability: (
            VerifiedNativeEvidenceWitnessCapability | None
        ) = None,
    ) -> PreparedNativeEvidenceAdmission:
        """Retain one bounded preparation without publishing the witness."""

        if not isinstance(witness, NativeEvidenceCustodyWitness):
            raise TypeError("native custody requires a typed witness")
        if verified_capability is None:
            witness.verify()
        else:
            verified_capability.verify_linkage(witness)
        if witness.total_receipt_bytes > self._max_per_witness:
            raise ReceiptError(
                "native evidence occurrence exceeds live custody ceiling"
            )
        with self._lock:
            if (
                len(self._prepared)
                >= MAX_NATIVE_EVIDENCE_PREPARED_ADMISSIONS
            ):
                raise RuntimeError(
                    "native evidence prepared admission capacity is full"
                )
            prepared_bytes = sum(
                value.witness.total_receipt_bytes
                for value in self._prepared.values()
            )
            if (
                prepared_bytes + witness.total_receipt_bytes
                > self._max_total_bytes
            ):
                raise ReceiptError(
                    "native evidence prepared byte capacity is full"
                )
            token = secrets.token_urlsafe(24)
            prepared = PreparedNativeEvidenceAdmission(
                witness=witness,
                _token=token,
                _state=_NativeEvidenceAdmissionState(
                    phase="prepared"
                ),
                _owner_authority=self._owner_authority,
                _construction_authority=(
                    _PREPARED_NATIVE_EVIDENCE_ADMISSION_AUTHORITY
                ),
            )
            self._prepared[token] = prepared
            return prepared

    def verify_prepared_admission(
        self,
        prepared: PreparedNativeEvidenceAdmission,
    ) -> None:
        with self._lock:
            self._require_prepared_locked(prepared)

    def commit_prepared_admission(
        self,
        prepared: PreparedNativeEvidenceAdmission,
    ) -> NativeEvidenceAdmissionCommitUndo:
        """Publish one preparation and return its exact event inverse."""

        with self._lock:
            current_prepared = self._require_prepared_locked(prepared)
            witness = current_prepared.witness
            current = self._witnesses.get(
                witness.authority_receipt_sha256
            )
            prior_order = tuple(self._witnesses)
            retired_witnesses: list[
                NativeEvidenceCustodyWitness
            ] = []
            if current is not None:
                if current.payload() != witness.payload():
                    raise ReceiptError(
                        "native content address changed witness"
                    )
                for record in witness.receipt_records:
                    retained = self._records.get(record.digest)
                    if (
                        retained is None
                        or retained.payload != record.payload
                    ):
                        raise ReceiptError(
                            "native duplicate left retained byte custody"
                        )
                self._witnesses.move_to_end(
                    witness.authority_receipt_sha256
                )
                canonical_witness = current
                was_duplicate = True
            else:
                witnesses = OrderedDict(self._witnesses)
                records = dict(self._records)
                refcounts = dict(self._record_refcounts)
                retired = self._retired

                def retire_oldest() -> None:
                    nonlocal retired
                    _digest_value, oldest = witnesses.popitem(
                        last=False
                    )
                    retired_witnesses.append(oldest)
                    for record in oldest.receipt_records:
                        remaining = refcounts[record.digest] - 1
                        if remaining == 0:
                            del refcounts[record.digest]
                            del records[record.digest]
                        else:
                            refcounts[record.digest] = remaining
                    retired += 1

                new_unique_bytes = sum(
                    len(record.payload)
                    for record in witness.receipt_records
                    if record.digest not in records
                )
                while witnesses and (
                    len(witnesses) >= self._max_witnesses
                    or sum(
                        len(record.payload)
                        for record in records.values()
                    )
                    + new_unique_bytes
                    > self._max_total_bytes
                ):
                    retire_oldest()
                    new_unique_bytes = sum(
                        len(record.payload)
                        for record in witness.receipt_records
                        if record.digest not in records
                    )
                if (
                    len(witnesses) >= self._max_witnesses
                    or sum(
                        len(record.payload)
                        for record in records.values()
                    )
                    + new_unique_bytes
                    > self._max_total_bytes
                ):
                    raise ReceiptError(
                        "native evidence recent custody capacity exhausted"
                    )
                canonical_records: list[ReceiptRecord] = []
                for record in witness.receipt_records:
                    mounted = records.get(record.digest)
                    if (
                        mounted is not None
                        and mounted.payload != record.payload
                    ):
                        raise ReceiptError(
                            "native evidence content address collided"
                        )
                    canonical = (
                        mounted if mounted is not None else record
                    )
                    records[record.digest] = canonical
                    refcounts[record.digest] = (
                        refcounts.get(record.digest, 0) + 1
                    )
                    canonical_records.append(canonical)
                canonical_witness = (
                    witness
                    if all(
                        canonical is original
                        for canonical, original in zip(
                            canonical_records,
                            witness.receipt_records,
                            strict=True,
                        )
                    )
                    else NativeEvidenceCustodyWitness(
                        original_profile_binding_sha256=(
                            witness.original_profile_binding_sha256
                        ),
                        ports=witness.ports,
                        receipt_records=tuple(canonical_records),
                        total_receipt_bytes=witness.total_receipt_bytes,
                        authority_receipt_sha256=(
                            witness.authority_receipt_sha256
                        ),
                    )
                )
                if canonical_witness is not witness:
                    canonical_witness.verify()
                witnesses[
                    canonical_witness.authority_receipt_sha256
                ] = canonical_witness
                self._witnesses = witnesses
                self._records = records
                self._record_refcounts = refcounts
                self._retired = retired
                was_duplicate = False

            prior_tail = self._mutation_tail
            commit_token = receipt_sha256(_canonical({
                "native_evidence_witness_receipt_sha256": (
                    canonical_witness.authority_receipt_sha256
                ),
                "preparation_token": current_prepared._token,
                "prior_mutation_tail": prior_tail,
            }))
            del self._prepared[current_prepared._token]
            self._mutation_tail = commit_token
            current_prepared._state.phase = "committed"
            current_prepared._state.commit_token = commit_token
            return NativeEvidenceAdmissionCommitUndo(
                _prepared=current_prepared,
                _canonical_witness=canonical_witness,
                _retired_witnesses=tuple(retired_witnesses),
                _prior_witness_order=prior_order,
                _was_duplicate=was_duplicate,
                _commit_token=commit_token,
                _prior_mutation_tail=prior_tail,
                _owner_authority=self._owner_authority,
                _construction_authority=(
                    _NATIVE_EVIDENCE_ADMISSION_UNDO_AUTHORITY
                ),
            )

    def rollback_committed_admission(
        self,
        undo: NativeEvidenceAdmissionCommitUndo,
    ) -> None:
        """Apply the inverse of one still-current admission event."""

        with self._lock:
            if (
                not isinstance(
                    undo,
                    NativeEvidenceAdmissionCommitUndo,
                )
                or undo._construction_authority
                is not _NATIVE_EVIDENCE_ADMISSION_UNDO_AUTHORITY
                or undo._owner_authority is not self._owner_authority
                or undo._commit_token != self._mutation_tail
                or undo._prepared._state.phase != "committed"
                or undo._prepared._state.commit_token
                != undo._commit_token
                or undo._prepared._token in self._prepared
            ):
                raise ValueError(
                    "native evidence admission undo changed custody"
                )
            if undo._was_duplicate:
                if (
                    self._witnesses.get(
                        undo._canonical_witness
                        .authority_receipt_sha256
                    )
                    is not undo._canonical_witness
                ):
                    raise ValueError(
                        "native duplicate admission no longer current"
                    )
            else:
                self._remove_witness_locked(
                    undo._canonical_witness,
                    witnesses=self._witnesses,
                    records=self._records,
                    refcounts=self._record_refcounts,
                )
                for witness in undo._retired_witnesses:
                    self._add_witness_locked(
                        witness,
                        witnesses=self._witnesses,
                        records=self._records,
                        refcounts=self._record_refcounts,
                    )
                self._retired -= len(undo._retired_witnesses)
            if set(self._witnesses) != set(
                undo._prior_witness_order
            ):
                raise RuntimeError(
                    "native evidence inverse changed witness membership"
                )
            self._witnesses = OrderedDict(
                (digest, self._witnesses[digest])
                for digest in undo._prior_witness_order
            )
            self._mutation_tail = undo._prior_mutation_tail
            undo._prepared._state.phase = "prepared"
            undo._prepared._state.commit_token = None
            self._prepared[
                undo._prepared._token
            ] = undo._prepared

    def discard_prepared_admission(
        self,
        prepared: PreparedNativeEvidenceAdmission,
    ) -> None:
        """Release temporary exact bytes without publishing an occurrence."""

        with self._lock:
            current = self._require_prepared_locked(prepared)
            del self._prepared[current._token]
            current._state.phase = "discarded"

    def admit(
        self,
        witness: NativeEvidenceCustodyWitness,
    ) -> NativeEvidenceCustodyWitness:
        """Publish one witness through the owner transaction boundary."""

        prepared = self.prepare_admission(witness)
        undo = self.commit_prepared_admission(prepared)
        return undo._canonical_witness

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "content_addressed_receipts": len(self._records),
                "max_receipt_bytes_per_witness": self._max_per_witness,
                "max_prepared_admissions": (
                    MAX_NATIVE_EVIDENCE_PREPARED_ADMISSIONS
                ),
                "max_prepared_receipt_bytes": self._max_total_bytes,
                "max_retained_witnesses": self._max_witnesses,
                "max_total_receipt_bytes": self._max_total_bytes,
                "prepared_admissions": len(self._prepared),
                "prepared_raw_receipt_bytes": sum(
                    value.witness.total_receipt_bytes
                    for value in self._prepared.values()
                ),
                "raw_receipt_bytes": sum(
                    len(value.payload) for value in self._records.values()
                ),
                "retained_witnesses": len(self._witnesses),
                "retired_witnesses": self._retired,
                "schema": "guala.native_evidence_custody.status.v1",
            }


__all__ = (
    "MAX_NATIVE_EVIDENCE_PORTS",
    "MAX_NATIVE_EVIDENCE_PREPARED_ADMISSIONS",
    "MAX_NATIVE_EVIDENCE_RECEIPTS",
    "MAX_NATIVE_EVIDENCE_RECEIPT_BYTES",
    "MAX_NATIVE_EVIDENCE_RECORD_BYTES",
    "NATIVE_EVIDENCE_WITNESS_SCHEMA",
    "NATIVE_EVIDENCE_TRANSITION_SCHEMA",
    "NATIVE_EVIDENCE_CUSTODY_AUTHORITY_PAYLOAD",
    "NativeEvidenceAdmissionCommitUndo",
    "NativeEvidenceCustodyOwner",
    "NativeEvidenceCustodyWitness",
    "NativeEvidenceTransitionIndex",
    "NativePortEvidenceWitness",
    "PreparedNativeEvidenceAdmission",
    "VerifiedNativeEvidenceWitnessCapability",
)
