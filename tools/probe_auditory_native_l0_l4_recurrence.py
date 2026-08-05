"""Bounded audit of native auditory L0--L4 state and transition recurrence.

Every exposure is independently transduced through the unchanged auditory
provider and frozen L0--L4 kernel.  Exact state identities retain component
topology and every native field.  Gate positions are recorded as causal
occurrence support but are not part of a state identity, so the same native
state may lawfully recur at a different source position.  The report contains
aggregate counts and a bounded number of exact witnesses; it never emits a
tuple inventory, score, sign projection, template, threshold, or ranking.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


LAYERS = (
    "L0_SEV",
    "L1_GateL1State",
    "L2_GateInterpretation",
    "L3_ResonanceResult",
    "L4_DSF",
)
GATE_LAYERS = (
    "L1_GateL1State",
    "L2_GateInterpretation",
    "L3_ResonanceResult",
)
TRACE_SCHEMAS = {
    "glew.provider.complete_signed_port_l0_l4_trace.v3",
    "glew.provider.complete_physical_port_l0_l4_trace.v4",
}
WITNESS_LIMIT = 3


@dataclass(frozen=True, slots=True)
class Exposure:
    name: str
    category: str
    path: Path


@dataclass(frozen=True, slots=True)
class Occurrence:
    exposure_index: int
    exposure_name: str
    component_index: int
    component_id: str
    component_kind: str
    row_index: int
    source_index_start: int
    source_index_end: int
    trace_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class StateIdentity:
    component_index: int
    component_id: str
    component_kind: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class TransitionIdentity:
    component_index: int
    component_id: str
    component_kind: str
    left_payload: bytes
    right_payload: bytes


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _decode(payload: bytes) -> Any:
    return json.loads(payload.decode("utf-8"))


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _state_payload(layer: str, row: dict[str, object]) -> bytes:
    if layer in GATE_LAYERS:
        return _canonical({
            name: value
            for name, value in row.items()
            if name not in {"start_idx", "end_idx"}
        })
    return _canonical(row)


def _state_identity(
    component_index: int,
    component_id: str,
    component_kind: str,
    payload: bytes,
) -> StateIdentity:
    return StateIdentity(
        component_index=component_index,
        component_id=component_id,
        component_kind=component_kind,
        payload=payload,
    )


def _transition_identity(
    state: StateIdentity,
    right_payload: bytes,
) -> TransitionIdentity:
    return TransitionIdentity(
        component_index=state.component_index,
        component_id=state.component_id,
        component_kind=state.component_kind,
        left_payload=state.payload,
        right_payload=right_payload,
    )


def _support_names(
    occurrences: list[Occurrence],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        value.exposure_name
        for value in sorted(
            occurrences,
            key=lambda item: (
                item.exposure_index,
                item.component_index,
                item.row_index,
            ),
        )
    ))


def _occurrence_record(value: Occurrence) -> dict[str, object]:
    return {
        "component_id": value.component_id,
        "component_index": value.component_index,
        "component_kind": value.component_kind,
        "exposure_index": value.exposure_index,
        "exposure_name": value.exposure_name,
        "row_index": value.row_index,
        "source_index_end_inclusive": value.source_index_end,
        "source_index_start_inclusive": value.source_index_start,
        "trace_receipt_sha256": value.trace_receipt_sha256,
    }


def _state_record(value: StateIdentity) -> dict[str, object]:
    payload = _decode(value.payload)
    authority = {
        "component_id": value.component_id,
        "component_index": value.component_index,
        "component_kind": value.component_kind,
        "native_state": payload,
    }
    return {
        "identity_sha256": _digest(authority),
        **authority,
    }


def _transition_record(
    value: TransitionIdentity,
) -> dict[str, object]:
    authority = {
        "component_id": value.component_id,
        "component_index": value.component_index,
        "component_kind": value.component_kind,
        "native_state_from": _decode(value.left_payload),
        "native_state_to": _decode(value.right_payload),
    }
    return {
        "identity_sha256": _digest(authority),
        **authority,
    }


def _cross_group_counts(
    ledger: dict[object, list[Occurrence]],
    *,
    hello_names: set[str],
    unrelated_names: set[str],
    variant_names: set[str],
) -> dict[str, int]:
    supports = [
        set(_support_names(values))
        for values in ledger.values()
    ]
    hello_common = [
        value for value in supports if hello_names <= value
    ]
    return {
        "identity_count": len(ledger),
        "recurring_in_at_least_two_exposures": sum(
            len(value) >= 2 for value in supports
        ),
        "present_in_all_three_independent_hello": len(hello_common),
        "all_three_hello_also_in_unrelated_phrase": sum(
            bool(value & unrelated_names) for value in hello_common
        ),
        "all_three_hello_also_in_noise_or_gain_variant": sum(
            bool(value & variant_names) for value in hello_common
        ),
        "all_three_hello_absent_both_controls": sum(
            not value & unrelated_names and not value & variant_names
            for value in hello_common
        ),
    }


def _receipt_support_counts(
    ledger: dict[str, set[str]],
    *,
    hello_names: set[str],
    unrelated_names: set[str],
    variant_names: set[str],
) -> dict[str, object]:
    hello_common = [
        support
        for support in ledger.values()
        if hello_names <= support
    ]
    return {
        "exact_complete_trace_receipt_count": len(ledger),
        "receipts_recurring_in_at_least_two_exposures": sum(
            len(support) >= 2 for support in ledger.values()
        ),
        "receipts_present_in_all_three_independent_hello": len(
            hello_common
        ),
        "all_three_hello_receipts_absent_both_controls": sum(
            not support & unrelated_names
            and not support & variant_names
            for support in hello_common
        ),
        "bounded_recurring_exact_receipt_witnesses": [
            {
                "trace_receipt_sha256": digest,
                "exposure_support": sorted(support),
            }
            for digest, support in sorted(ledger.items())
            if len(support) >= 2
        ][:WITNESS_LIMIT],
    }


def _select_witnesses(
    ledger: dict[object, list[Occurrence]],
    *,
    hello_names: set[str],
    unrelated_names: set[str],
    variant_names: set[str],
    identity_record,
) -> dict[str, list[dict[str, object]]]:
    groups: dict[str, list[tuple[object, list[Occurrence]]]] = {
        "all_three_hello_absent_both_controls": [],
        "all_three_hello_also_in_unrelated": [],
        "all_three_hello_also_in_variant": [],
    }
    for identity, occurrences in ledger.items():
        support = set(_support_names(occurrences))
        if hello_names <= support:
            if not support & unrelated_names and not support & variant_names:
                groups["all_three_hello_absent_both_controls"].append(
                    (identity, occurrences)
                )
            if support & unrelated_names:
                groups["all_three_hello_also_in_unrelated"].append(
                    (identity, occurrences)
                )
            if support & variant_names:
                groups["all_three_hello_also_in_variant"].append(
                    (identity, occurrences)
                )
    result: dict[str, list[dict[str, object]]] = {}
    for group, values in groups.items():
        selected = sorted(
            values,
            key=lambda item: _canonical(identity_record(item[0])),
        )[:WITNESS_LIMIT]
        result[group] = [
            {
                **identity_record(identity),
                "exposure_support": list(_support_names(occurrences)),
                "first_occurrence_per_exposure": [
                    _occurrence_record(value)
                    for value in _first_per_exposure(occurrences)
                ],
            }
            for identity, occurrences in selected
        ]
    return result


def _first_per_exposure(
    occurrences: list[Occurrence],
) -> list[Occurrence]:
    selected: dict[int, Occurrence] = {}
    for value in sorted(
        occurrences,
        key=lambda item: (
            item.exposure_index,
            item.component_index,
            item.row_index,
        ),
    ):
        selected.setdefault(value.exposure_index, value)
    return list(selected.values())


def _trace_from_component(experience, component) -> dict[str, object]:
    payload = experience.upstream_receipt_registry.resolve(
        component.l0_l4_trace_receipt_sha256,
        "native L0-L4 recurrence probe trace",
    )
    if receipt_sha256(payload) != component.l0_l4_trace_receipt_sha256:
        raise RuntimeError("source trace digest changed")
    try:
        trace = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("source trace is not JSON") from error
    if (
        not isinstance(trace, dict)
        or trace.get("schema") not in TRACE_SCHEMAS
        or trace.get("lane_id") != "sound"
        or trace.get("port_id") != component.substream_id
        or _canonical(trace) != payload
    ):
        raise RuntimeError("source trace authority changed")
    if any(not isinstance(trace.get(layer), list) for layer in LAYERS):
        raise RuntimeError("source trace lost a native layer")
    return trace


def _gate_intervals(
    trace: dict[str, object],
    source_count: int,
) -> tuple[tuple[int, int], ...]:
    layer_intervals = []
    for layer in GATE_LAYERS:
        values = trace[layer]
        if not isinstance(values, list):
            raise RuntimeError("gate layer changed shape")
        intervals = []
        for row in values:
            if not isinstance(row, dict):
                raise RuntimeError("gate row changed shape")
            start = row.get("start_idx")
            end = row.get("end_idx")
            if (
                isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or not 0 <= start <= end < source_count
            ):
                raise RuntimeError("gate interval left source grid")
            intervals.append((start, end))
        layer_intervals.append(tuple(intervals))
    if len(set(layer_intervals)) != 1:
        raise RuntimeError("L1-L3 gate partitions diverged")
    intervals = layer_intervals[0]
    prior_end = -1
    for start, end in intervals:
        if start != prior_end + 1:
            raise RuntimeError("gate partition overlaps or omits samples")
        prior_end = end
    if not intervals or intervals[-1][1] != source_count - 1:
        raise RuntimeError("gate partition does not cover source")
    return intervals


def _component_rows(experience):
    return tuple(
        component
        for channel in experience.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
    )


def _trace_inventory(
    *,
    exposure: Exposure,
    exposure_index: int,
    experience,
    state_ledgers: dict[
        str, dict[StateIdentity, list[Occurrence]]
    ],
    transition_ledgers: dict[
        str, dict[TransitionIdentity, list[Occurrence]]
    ],
    b_ledgers: dict[str, dict[StateIdentity, list[Occurrence]]],
    trace_receipt_support: dict[str, set[str]],
) -> dict[str, object]:
    experience.verify()
    schemas: Counter[str] = Counter()
    layer_rows: Counter[str] = Counter()
    layer_states: dict[str, set[StateIdentity]] = {
        layer: set() for layer in LAYERS
    }
    layer_transitions: dict[str, set[TransitionIdentity]] = {
        layer: set() for layer in LAYERS
    }
    gate_partition_count = 0
    gate_partition_lengths: set[int] = set()
    trace_receipts = set()
    source_stream_receipts = set()
    l4_tuple_receipts = set()
    b_values: set[StateIdentity] = set()
    b_transitions: set[TransitionIdentity] = set()
    components = _component_rows(experience)
    if len(components) != 32:
        raise RuntimeError("auditory component topology is not 32")
    for expected_index, component in enumerate(components):
        if component.topology_index != expected_index:
            raise RuntimeError("auditory component topology reordered")
        trace = _trace_from_component(experience, component)
        schema = trace["schema"]
        if not isinstance(schema, str):
            raise RuntimeError("trace schema is not text")
        schemas[schema] += 1
        trace_receipts.add(component.l0_l4_trace_receipt_sha256)
        trace_receipt_support[
            component.l0_l4_trace_receipt_sha256
        ].add(exposure.name)
        source_stream_receipts.add(component.source_stream_receipt_sha256)
        l4_tuple_receipts.update(
            value.authority_receipt_sha256
            for value in component.l4_field_tuples
        )
        source_count = len(component.samples)
        intervals = _gate_intervals(trace, source_count)
        gate_partition_count += len(intervals)
        gate_partition_lengths.update(
            end - start + 1 for start, end in intervals
        )
        l0 = trace["L0_SEV"]
        l4 = trace["L4_DSF"]
        if (
            not isinstance(l0, list)
            or len(l0) != source_count
            or not isinstance(l4, list)
            or len(l4) != len(component.l4_field_tuples)
            or any(
                not isinstance(trace[layer], list)
                or len(trace[layer]) != len(intervals)
                for layer in GATE_LAYERS
            )
        ):
            raise RuntimeError("native trace cardinality changed")
        for row, exact in zip(
            l4,
            component.l4_field_tuples,
            strict=True,
        ):
            exact_map = {
                name: f"{value.numerator}/{value.denominator}"
                for name, value in exact.fields
            }
            if (
                not isinstance(row, dict)
                or set(row) != set(DSF_FIELD_ORDER)
                or row != exact_map
            ):
                raise RuntimeError("L4 trace differs from exact authority")
        component_kind = component.kind.value
        for layer in LAYERS:
            values = trace[layer]
            if not isinstance(values, list):
                raise RuntimeError("native layer changed shape")
            payloads = []
            occurrences = []
            for row_index, row in enumerate(values):
                if not isinstance(row, dict):
                    raise RuntimeError("native state row changed shape")
                if layer == "L0_SEV":
                    start = row_index
                    end = row_index
                else:
                    start, end = intervals[row_index]
                payload = _state_payload(layer, row)
                identity = _state_identity(
                    component.topology_index,
                    component.substream_id,
                    component_kind,
                    payload,
                )
                occurrence = Occurrence(
                    exposure_index=exposure_index,
                    exposure_name=exposure.name,
                    component_index=component.topology_index,
                    component_id=component.substream_id,
                    component_kind=component_kind,
                    row_index=row_index,
                    source_index_start=start,
                    source_index_end=end,
                    trace_receipt_sha256=(
                        component.l0_l4_trace_receipt_sha256
                    ),
                )
                state_ledgers[layer][identity].append(occurrence)
                layer_states[layer].add(identity)
                layer_rows[layer] += 1
                payloads.append(payload)
                occurrences.append(occurrence)
                if layer == "L4_DSF":
                    b_payload = _canonical({"B_k": row["B_k"]})
                    b_identity = _state_identity(
                        component.topology_index,
                        component.substream_id,
                        component_kind,
                        b_payload,
                    )
                    b_ledgers["states"][b_identity].append(occurrence)
                    b_values.add(b_identity)
            for row_index, (left, right) in enumerate(
                zip(payloads, payloads[1:], strict=False)
            ):
                left_state = _state_identity(
                    component.topology_index,
                    component.substream_id,
                    component_kind,
                    left,
                )
                transition = _transition_identity(left_state, right)
                occurrence = occurrences[row_index]
                transition_ledgers[layer][transition].append(occurrence)
                layer_transitions[layer].add(transition)
                if layer == "L4_DSF":
                    left_row = _decode(left)
                    right_row = _decode(right)
                    b_left = _canonical({"B_k": left_row["B_k"]})
                    b_right = _canonical({"B_k": right_row["B_k"]})
                    b_transition = _transition_identity(
                        _state_identity(
                            component.topology_index,
                            component.substream_id,
                            component_kind,
                            b_left,
                        ),
                        b_right,
                    )
                    b_ledgers["transitions"][b_transition].append(
                        occurrence
                    )
                    b_transitions.add(b_transition)
    return {
        "category": exposure.category,
        "component_count": len(components),
        "distinct_l4_tuple_authority_receipts": len(l4_tuple_receipts),
        "distinct_source_stream_receipts": len(source_stream_receipts),
        "distinct_trace_receipts": len(trace_receipts),
        "gate_partition_count": gate_partition_count,
        "gate_partition_distinct_exact_lengths": len(
            gate_partition_lengths
        ),
        "index": exposure_index,
        "layer_occurrence_counts": {
            layer: layer_rows[layer] for layer in LAYERS
        },
        "layer_distinct_native_state_counts": {
            layer: len(layer_states[layer]) for layer in LAYERS
        },
        "layer_distinct_native_transition_counts": {
            layer: len(layer_transitions[layer]) for layer in LAYERS
        },
        "l4_breathing_coordinate": {
            "distinct_exact_component_B_k_states": len(b_values),
            "distinct_exact_component_B_k_transitions": len(b_transitions),
        },
        "name": exposure.name,
        "path": str(exposure.path.resolve()),
        "source_sha256": hashlib.sha256(
            exposure.path.read_bytes()
        ).hexdigest(),
        "trace_schema_counts": dict(sorted(schemas.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exposure",
        action="append",
        nargs=3,
        metavar=("NAME", "CATEGORY", "PATH"),
        required=True,
    )
    args = parser.parse_args()
    exposures = tuple(
        Exposure(name=name, category=category, path=Path(path))
        for name, category, path in args.exposure
    )
    if len(exposures) != 5:
        raise SystemExit(
            "probe requires exactly five exposures: three independent "
            "hello, one unrelated phrase, and one noise/gain variant"
        )
    if len({value.name for value in exposures}) != len(exposures):
        raise SystemExit("exposure names must be unique")
    if Counter(value.category for value in exposures) != Counter({
        "independent_hello": 3,
        "unrelated_phrase": 1,
        "noise_or_gain_variant": 1,
    }):
        raise SystemExit("exposure category composition changed")
    for exposure in exposures:
        if not exposure.path.is_file():
            raise SystemExit(f"exposure is absent: {exposure.path}")

    state_ledgers: dict[
        str, dict[StateIdentity, list[Occurrence]]
    ] = {
        layer: defaultdict(list) for layer in LAYERS
    }
    transition_ledgers: dict[
        str, dict[TransitionIdentity, list[Occurrence]]
    ] = {
        layer: defaultdict(list) for layer in LAYERS
    }
    b_ledgers: dict[str, dict[Any, list[Occurrence]]] = {
        "states": defaultdict(list),
        "transitions": defaultdict(list),
    }
    trace_receipt_support: dict[str, set[str]] = defaultdict(set)

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        traced = tuple(
            (
                exposure,
                *_experience(exposure.path, index, l5_owner),
            )
            for index, exposure in enumerate(exposures)
        )
    finally:
        stop_exact_field_executor()

    exposure_records = []
    for index, (exposure, experience, source_report) in enumerate(traced):
        record = _trace_inventory(
            exposure=exposure,
            exposure_index=index,
            experience=experience,
            state_ledgers=state_ledgers,
            transition_ledgers=transition_ledgers,
            b_ledgers=b_ledgers,
            trace_receipt_support=trace_receipt_support,
        )
        record["source_event"] = source_report
        exposure_records.append(record)

    hello_names = {
        value.name
        for value in exposures
        if value.category == "independent_hello"
    }
    unrelated_names = {
        value.name
        for value in exposures
        if value.category == "unrelated_phrase"
    }
    variant_names = {
        value.name
        for value in exposures
        if value.category == "noise_or_gain_variant"
    }

    layer_results = {}
    for layer in LAYERS:
        layer_results[layer] = {
            "native_states": {
                **_cross_group_counts(
                    state_ledgers[layer],
                    hello_names=hello_names,
                    unrelated_names=unrelated_names,
                    variant_names=variant_names,
                ),
                "bounded_exact_witnesses": _select_witnesses(
                    state_ledgers[layer],
                    hello_names=hello_names,
                    unrelated_names=unrelated_names,
                    variant_names=variant_names,
                    identity_record=_state_record,
                ),
            },
            "native_adjacent_transitions": {
                **_cross_group_counts(
                    transition_ledgers[layer],
                    hello_names=hello_names,
                    unrelated_names=unrelated_names,
                    variant_names=variant_names,
                ),
                "bounded_exact_witnesses": _select_witnesses(
                    transition_ledgers[layer],
                    hello_names=hello_names,
                    unrelated_names=unrelated_names,
                    variant_names=variant_names,
                    identity_record=_transition_record,
                ),
            },
        }

    b_results = {
        "notice": (
            "This is a coordinate inventory for emphasis only. It is not "
            "used as authority in place of the complete seven-field L4 "
            "state and transition comparison above."
        ),
        "exact_component_B_k_states": {
            **_cross_group_counts(
                b_ledgers["states"],
                hello_names=hello_names,
                unrelated_names=unrelated_names,
                variant_names=variant_names,
            ),
            "bounded_exact_witnesses": _select_witnesses(
                b_ledgers["states"],
                hello_names=hello_names,
                unrelated_names=unrelated_names,
                variant_names=variant_names,
                identity_record=_state_record,
            ),
        },
        "exact_component_B_k_transitions": {
            **_cross_group_counts(
                b_ledgers["transitions"],
                hello_names=hello_names,
                unrelated_names=unrelated_names,
                variant_names=variant_names,
            ),
            "bounded_exact_witnesses": _select_witnesses(
                b_ledgers["transitions"],
                hello_names=hello_names,
                unrelated_names=unrelated_names,
                variant_names=variant_names,
                identity_record=_transition_record,
            ),
        },
    }

    print(json.dumps({
        "schema": "guala.audit.auditory_native_l0_l4_recurrence.v1",
        "method": {
            "native_state_identity": (
                "component topology plus every native row field; only "
                "L1-L3 start_idx/end_idx are occurrence support rather than "
                "state identity"
            ),
            "native_transition_identity": (
                "component topology plus exact adjacent native state pair"
            ),
            "complete_field_status": (
                "L0 SEV, L1 gate state, L2 gate interpretation, L3 "
                "resonance result, and complete ordered L4 "
                "D/M/R/U/C/P/B are inspected"
            ),
            "receipt_verification": (
                "canonical trace bytes, SHA-256 authority, lane, port, "
                "schema, component topology, L1-L3 common contiguous "
                "partition, and exact L4 tuple authority are verified"
            ),
            "bounded_output": (
                "aggregate identity/support counts plus at most three "
                "lexicographically first exact witnesses per stated group"
            ),
            "forbidden_reductions": [
                "averages",
                "classifiers",
                "rankings",
                "scores",
                "sign projections",
                "templates",
                "thresholds",
                "trits",
            ],
        },
        "exposures": exposure_records,
        "complete_trace_receipt_authority_recurrence": (
            _receipt_support_counts(
                trace_receipt_support,
                hello_names=hello_names,
                unrelated_names=unrelated_names,
                variant_names=variant_names,
            )
        ),
        "native_layer_recurrence_and_discrimination": layer_results,
        "l4_breathing_coordinate_emphasis": b_results,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
