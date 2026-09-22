"""Exact non-semantic port basin construction from canonical L0--L4 traces."""

from __future__ import annotations

import json
from fractions import Fraction
from typing import Mapping

from .closed_experience import RatifiedNativeL0L4Trace
from .global_uf import (
    ExactDSFFieldTupleReceipt,
    LayerBranchGateSignature,
    NamedSignZeroClass,
    PortKernelBasinSignature,
    SignZeroClass,
    exact_dsf_field_tuple_receipt_payload,
    port_kernel_basin_receipt_payload,
)
from .model import ReceiptError, ReceiptRecord, receipt_sha256


_DSF_FIELDS = (
    "D_k",
    "M_k",
    "R_rev_k",
    "U_star_k",
    "C_k",
    "P_k",
    "B_k",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sign(value: Fraction) -> SignZeroClass:
    return (
        SignZeroClass.NEGATIVE
        if value < 0
        else SignZeroClass.POSITIVE
        if value > 0
        else SignZeroClass.EXACT_ZERO
    )


def _fraction(value: object, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ReceiptError(f"{name} is not an exact numeric coordinate")
    try:
        return Fraction(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, ZeroDivisionError) as error:
        raise ReceiptError(f"{name} is not an exact rational") from error


def _classes(
    values: Mapping[str, object],
) -> tuple[NamedSignZeroClass, ...]:
    return tuple(
        NamedSignZeroClass(name, _sign(_fraction(value, name)))
        for name, value in sorted(values.items())
    )


def _lossless_id(prefix: str, value: object) -> str:
    return f"{prefix}-{_canonical_bytes(value).hex()}"


def _port_kernel_basin(
    *,
    lane_id: str,
    port_id: str,
    trace_digest: str,
    l0_count: int,
    l1_gates: tuple[tuple[int, int], ...],
    l2_regimes: tuple[str, ...],
    l3_count: int,
    l4_values: tuple[Mapping[str, Fraction], ...],
) -> tuple[PortKernelBasinSignature, tuple[bytes, ...]]:
    tuples = []
    tuple_payloads = []
    for index, values in enumerate(l4_values):
        payload = exact_dsf_field_tuple_receipt_payload(
            lane_id=lane_id,
            port_id=port_id,
            tuple_index=index,
            source_l0_l4_trace_receipt_sha256=trace_digest,
            **values,
        )
        tuples.append(ExactDSFFieldTupleReceipt(
            lane_id,
            port_id,
            index,
            *(values[name] for name in _DSF_FIELDS),
            trace_digest,
            receipt_sha256(payload),
        ))
        tuple_payloads.append(payload)
    layers = (
        LayerBranchGateSignature(
            0,
            f"L0-trace-{trace_digest}",
            (f"samples-{l0_count:08d}",),
            (),
        ),
        LayerBranchGateSignature(
            1,
            f"L1-trace-{trace_digest}",
            tuple(
                f"gate-{index:08d}-{start:08d}-{end:08d}"
                for index, (start, end) in enumerate(l1_gates)
            ),
            (),
        ),
        LayerBranchGateSignature(
            2,
            f"L2-trace-{trace_digest}",
            tuple(
                f"gate-{index:08d}-{regime}"
                for index, regime in enumerate(l2_regimes)
            ),
            (),
        ),
        LayerBranchGateSignature(
            3,
            f"L3-trace-{trace_digest}",
            tuple(
                f"gate-{index:08d}"
                for index in range(l3_count)
            ),
            (),
        ),
        LayerBranchGateSignature(
            4,
            f"L4-trace-{trace_digest}",
            tuple(
                f"gate-{index:08d}"
                for index in range(len(l4_values))
            ),
            _classes({
                f"{index:08d}:{name}": getattr(item, name)
                for index, item in enumerate(tuples)
                for name in _DSF_FIELDS
            }),
        ),
    )
    payload = port_kernel_basin_receipt_payload(
        lane_id=lane_id,
        port_id=port_id,
        layers=layers,
        exact_dsf_field_tuples=tuple(tuples),
    )
    return (
        PortKernelBasinSignature(
            lane_id,
            port_id,
            layers,
            tuple(tuples),
            receipt_sha256(payload),
        ),
        (*tuple_payloads, payload),
    )


def port_kernel_basin_from_trace_record(
    *,
    lane_id: str,
    port_id: str,
    trace_record: ReceiptRecord,
) -> tuple[PortKernelBasinSignature, tuple[bytes, ...]]:
    """Bind one canonical native L0--L4 trace to its exact port basin."""

    raw = json.loads(trace_record.payload)
    if (
        raw.get("lane_id") != lane_id
        or raw.get("port_id") != port_id
    ):
        raise ReceiptError(
            "canonical L0-L4 trace belongs to another native port"
        )
    return _port_kernel_basin(
        lane_id=lane_id,
        port_id=port_id,
        trace_digest=trace_record.digest,
        l0_count=len(raw["L0_SEV"]),
        l1_gates=tuple(
            (row["start_idx"], row["end_idx"])
            for row in raw["L1_GateL1State"]
        ),
        l2_regimes=tuple(
            row["regime"] for row in raw["L2_GateInterpretation"]
        ),
        l3_count=len(raw["L3_ResonanceResult"]),
        l4_values=tuple(
            {
                name: _fraction(row[name], name)
                for name in _DSF_FIELDS
            }
            for row in raw["L4_DSF"]
        ),
    )


def port_kernel_basin_from_typed_trace(
    *,
    lane_id: str,
    port_id: str,
    trace: RatifiedNativeL0L4Trace,
) -> tuple[PortKernelBasinSignature, tuple[bytes, ...]]:
    """Build the exact basin directly from the settled typed trajectory."""
    if (
        trace.stream.lane_id != lane_id
        or trace.stream.port_id != port_id
    ):
        raise ReceiptError(
            "canonical typed L0-L4 trace belongs to another native port"
        )
    trace_digest = receipt_sha256(trace.raw_payload)
    return _port_kernel_basin(
        lane_id=lane_id,
        port_id=port_id,
        trace_digest=trace_digest,
        l0_count=len(trace.sev),
        l1_gates=tuple(
            (value.gate.start_idx, value.gate.end_idx)
            for value in trace.l1
        ),
        l2_regimes=tuple(value.regime for value in trace.l2),
        l3_count=len(trace.l3),
        l4_values=tuple(
            {
                name: _fraction(getattr(value, name), name)
                for name in _DSF_FIELDS
            }
            for value in trace.l4
        ),
    )


__all__ = (
    "port_kernel_basin_from_trace_record",
    "port_kernel_basin_from_typed_trace",
)
