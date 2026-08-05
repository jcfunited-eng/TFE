"""Non-authoritative comparison of two existing auditory relevance modes.

This standalone diagnostic recomputes the unchanged L0--L4 kernel from the
same settled auditory component samples under:

* current_unit_relevance: the current auditory relevance identity, r(t)=1;
* structural_activity_diagnostic: the existing explicitly diagnostic L0
  adapter mode.

The current-unit recomputation must exactly reproduce every complete receipted
production trace before any comparison is admitted.  The structural-activity
branch is not receipted production evidence and is never mounted, persisted,
or used for recognition.  No thresholds are supplied or tuned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import pandas as pd

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.closed_experience import (
    SIGNED_UNIT_KERNEL_INPUT_MAP,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5ComponentKind,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_pressure_kernel_input import (
    AUDITORY_PRESSURE_KERNEL_INPUT_MAP,
)
from tools.probe_auditory_native_l0_l4_recurrence import (
    _canonical,
    _trace_from_component,
)
from tools.probe_auditory_surrounded_event_recognition import _experience
from uf_core.layer0 import RelevanceMode, compute_sev_series
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


MODES = (
    "current_unit_relevance",
    "structural_activity_diagnostic",
)
LAYERS = (
    "L1_GateL1State",
    "L2_GateInterpretation",
    "L3_ResonanceResult",
    "L4_DSF",
)
WITNESS_LIMIT = 3


@dataclass(frozen=True, slots=True)
class Exposure:
    name: str
    category: str
    path: Path


@dataclass(frozen=True, slots=True)
class Identity:
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


def _text(value: float) -> str:
    exact = Fraction.from_float(float(value))
    return f"{exact.numerator}/{exact.denominator}"


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _kernel(values: list[float], mode: RelevanceMode):
    frame = pd.DataFrame({"field": values})
    sev = tuple(
        compute_sev_series(
            frame,
            "field",
            relevance_mode=mode,
        )
    )
    gates = tuple(segment_gates(sev))
    l1 = tuple(build_gate_l1_state(sev, gates))
    l2 = tuple(interpret_gates(sev, gates))
    l3 = tuple(compute_resonance(l2))
    l4 = tuple(compute_dsf(compute_directional_signal(list(l3))))
    if not gates or len({len(gates), len(l1), len(l2), len(l3), len(l4)}) != 1:
        raise RuntimeError("diagnostic L0-L4 trajectory is incomplete")
    if any(
        not (gate == one.gate == two.gate == three.gate == four.gate)
        for gate, one, two, three, four in zip(
            gates,
            l1,
            l2,
            l3,
            l4,
            strict=True,
        )
    ):
        raise RuntimeError("diagnostic gate identities diverged")
    return sev, l1, l2, l3, l4


def _dimensionless_values(component) -> list[float]:
    input_map = (
        AUDITORY_PRESSURE_KERNEL_INPUT_MAP
        if component.kind is AuditoryL5ComponentKind.PRESSURE
        else SIGNED_UNIT_KERNEL_INPUT_MAP
    )
    return [
        float(input_map.forward(sample.signal))
        for sample in component.samples
    ]


def _serialize_kernel(sev, l1, l2, l3, l4) -> dict[str, list[dict[str, object]]]:
    return {
        "L0_SEV": [
            {
                "F_norm": _text(value.F_norm),
                "N": value.N,
                "dF": _text(value.dF),
                "kappa": _text(value.kappa),
                "relevance": _text(value.relevance),
                "sigma": _text(value.sigma),
            }
            for value in sev
        ],
        "L1_GateL1State": [
            {
                "C_k": value.C_k,
                "N_gate": value.N_gate,
                "TVR": [_text(item) for item in value.tvr],
                "delta_g": _text(value.delta_g),
                "end_idx": value.gate.end_idx,
                "projections": [list(item) for item in value.projections],
                "start_idx": value.gate.start_idx,
            }
            for value in l1
        ],
        "L2_GateInterpretation": [
            {
                "CV_k": [_text(item) for item in value.CV_k],
                "IAS_k": value.IAS_k,
                "S_k": _text(value.S_k),
                "U_k": _text(value.U_k),
                "end_idx": value.gate.end_idx,
                "regime": value.regime,
                "start_idx": value.gate.start_idx,
                "w_k": _text(value.w_k),
            }
            for value in l2
        ],
        "L3_ResonanceResult": [
            {
                "Hyst_k": value.Hyst_k,
                "R_k": _text(value.R_k),
                "URF_k": _text(value.URF_k),
                "end_idx": value.gate.end_idx,
                "g_k": value.g_k,
                "start_idx": value.gate.start_idx,
            }
            for value in l3
        ],
        "L4_DSF": [
            {
                name: _text(getattr(value, name))
                for name in DSF_FIELD_ORDER
            }
            for value in l4
        ],
    }


def _state_payload(layer: str, row: dict[str, object]) -> bytes:
    return _canonical({
        name: value
        for name, value in row.items()
        if name not in {"start_idx", "end_idx"}
    })


def _identity(component, payload: bytes) -> Identity:
    return Identity(
        component_index=component.topology_index,
        component_id=component.substream_id,
        component_kind=component.kind.value,
        payload=payload,
    )


def _transition(
    component,
    left_payload: bytes,
    right_payload: bytes,
) -> TransitionIdentity:
    return TransitionIdentity(
        component_index=component.topology_index,
        component_id=component.substream_id,
        component_kind=component.kind.value,
        left_payload=left_payload,
        right_payload=right_payload,
    )


def _identity_record(value: Identity) -> dict[str, object]:
    authority = {
        "component_id": value.component_id,
        "component_index": value.component_index,
        "component_kind": value.component_kind,
        "native_state": json.loads(value.payload),
    }
    return {
        "identity_sha256": _digest(authority),
        **authority,
    }


def _transition_record(value: TransitionIdentity) -> dict[str, object]:
    authority = {
        "component_id": value.component_id,
        "component_index": value.component_index,
        "component_kind": value.component_kind,
        "native_state_from": json.loads(value.left_payload),
        "native_state_to": json.loads(value.right_payload),
    }
    return {
        "identity_sha256": _digest(authority),
        **authority,
    }


def _support_summary(
    ledger: dict[Any, set[str]],
    *,
    hello_names: set[str],
    unrelated_names: set[str],
    variant_names: set[str],
    record,
) -> dict[str, object]:
    hello_common = [
        (identity, support)
        for identity, support in ledger.items()
        if hello_names <= support
    ]
    exclusive = [
        (identity, support)
        for identity, support in hello_common
        if not support & unrelated_names and not support & variant_names
    ]
    contaminated = [
        (identity, support)
        for identity, support in hello_common
        if support & unrelated_names or support & variant_names
    ]

    def witnesses(values):
        return [
            {
                **record(identity),
                "exposure_support": sorted(support),
            }
            for identity, support in sorted(
                values,
                key=lambda item: _canonical(record(item[0])),
            )[:WITNESS_LIMIT]
        ]

    return {
        "identity_count": len(ledger),
        "recurring_in_at_least_two_exposures": sum(
            len(support) >= 2 for support in ledger.values()
        ),
        "present_in_all_three_independent_hello": len(hello_common),
        "all_three_hello_also_in_unrelated_phrase": sum(
            bool(support & unrelated_names)
            for _identity_value, support in hello_common
        ),
        "all_three_hello_also_in_noise_variant": sum(
            bool(support & variant_names)
            for _identity_value, support in hello_common
        ),
        "all_three_hello_absent_both_controls": len(exclusive),
        "bounded_exact_witnesses": {
            "hello_exclusive": witnesses(exclusive),
            "hello_common_but_present_in_control": witnesses(contaminated),
        },
    }


def _metric_summary(rows: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    l1 = rows["L1_GateL1State"]
    l2 = rows["L2_GateInterpretation"]
    l3 = rows["L3_ResonanceResult"]
    l4 = rows["L4_DSF"]
    relevances = rows["L0_SEV"]
    u_values = {
        Fraction(value["U_k"])
        for value in l2
    }
    urf_values = {
        Fraction(value["URF_k"])
        for value in l3
    }
    b_values = {
        Fraction(value["B_k"])
        for value in l4
    }
    relevance_values = {
        Fraction(value["relevance"])
        for value in relevances
    }
    return {
        "L0_relevance": {
            "sample_count": len(relevances),
            "zero_count": sum(
                Fraction(value["relevance"]) == 0
                for value in relevances
            ),
            "unit_count": sum(
                Fraction(value["relevance"]) == 1
                for value in relevances
            ),
            "strictly_between_zero_and_one_count": sum(
                0 < Fraction(value["relevance"]) < 1
                for value in relevances
            ),
            "distinct_exact_value_count": len(relevance_values),
        },
        "L1_gate_activation": {
            "gate_count": len(l1),
            "N_gate_zero_count": sum(value["N_gate"] == 0 for value in l1),
            "N_gate_one_count": sum(value["N_gate"] == 1 for value in l1),
        },
        "L2_uncertainty_and_IAS": {
            "IAS_zero_count": sum(value["IAS_k"] == 0 for value in l2),
            "IAS_one_count": sum(value["IAS_k"] == 1 for value in l2),
            "U_exact_distinct_count": len(u_values),
            "U_exact_minimum": (
                f"{min(u_values).numerator}/{min(u_values).denominator}"
            ),
            "U_exact_maximum": (
                f"{max(u_values).numerator}/{max(u_values).denominator}"
            ),
        },
        "L3_gate_and_URF": {
            "g_closed_count": sum(value["g_k"] == 0 for value in l3),
            "g_open_count": sum(value["g_k"] == 1 for value in l3),
            "URF_exact_zero_count": sum(
                Fraction(value["URF_k"]) == 0 for value in l3
            ),
            "URF_exact_nonzero_count": sum(
                Fraction(value["URF_k"]) != 0 for value in l3
            ),
            "URF_exact_distinct_count": len(urf_values),
        },
        "L4_breathing_and_complete_field": {
            "tuple_count": len(l4),
            "B_exact_zero_count": sum(
                Fraction(value["B_k"]) == 0 for value in l4
            ),
            "B_exact_nonzero_count": sum(
                Fraction(value["B_k"]) != 0 for value in l4
            ),
            "B_exact_distinct_count": len(b_values),
            "complete_seven_field_distinct_count": len({
                _canonical(value) for value in l4
            }),
        },
    }


def _component_rows(experience):
    return tuple(
        component
        for channel in experience.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
    )


def _compare_component(
    component,
    current: dict[str, list[dict[str, object]]],
    diagnostic: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    layer_changes = {}
    for layer in LAYERS:
        left = current[layer]
        right = diagnostic[layer]
        if len(left) != len(right):
            raise RuntimeError("relevance modes changed gate cardinality")
        layer_changes[layer] = sum(
            one != two
            for one, two in zip(left, right, strict=True)
        )
    field_changes = {
        name: sum(
            left[name] != right[name]
            for left, right in zip(
                current["L4_DSF"],
                diagnostic["L4_DSF"],
                strict=True,
            )
        )
        for name in DSF_FIELD_ORDER
    }
    witnesses = []
    for index, (left, right) in enumerate(zip(
        current["L4_DSF"],
        diagnostic["L4_DSF"],
        strict=True,
    )):
        if left != right and len(witnesses) < WITNESS_LIMIT:
            witnesses.append({
                "component_id": component.substream_id,
                "component_index": component.topology_index,
                "component_kind": component.kind.value,
                "current_unit_relevance": left,
                "structural_activity_diagnostic": right,
                "tuple_index": index,
            })
    return {
        "layer_changed_row_counts": layer_changes,
        "L4_changed_field_coordinate_counts": field_changes,
        "bounded_first_causal_L4_change_witnesses": witnesses,
    }


def _add_ledgers(
    *,
    exposure_name: str,
    component,
    mode_rows: dict[str, list[dict[str, object]]],
    state_ledgers,
    transition_ledgers,
) -> None:
    for layer in LAYERS:
        payloads = [
            _state_payload(layer, row)
            for row in mode_rows[layer]
        ]
        for payload in payloads:
            state_ledgers[layer][
                _identity(component, payload)
            ].add(exposure_name)
        for left, right in zip(payloads, payloads[1:], strict=False):
            transition_ledgers[layer][
                _transition(component, left, right)
            ].add(exposure_name)


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
    if Counter(value.category for value in exposures) != Counter({
        "independent_hello": 3,
        "unrelated_phrase": 1,
        "noise_variant": 1,
    }):
        raise SystemExit(
            "requires three independent hello, one unrelated phrase, "
            "and one noise variant"
        )
    if len({value.name for value in exposures}) != len(exposures):
        raise SystemExit("exposure names must be unique")
    for exposure in exposures:
        if not exposure.path.is_file():
            raise SystemExit(f"exposure is absent: {exposure.path}")

    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        settled = tuple(
            (
                exposure,
                *_experience(exposure.path, index, l5_owner),
            )
            for index, exposure in enumerate(exposures)
        )
    finally:
        stop_exact_field_executor()

    state_ledgers = {
        mode: {
            layer: defaultdict(set) for layer in LAYERS
        }
        for mode in MODES
    }
    transition_ledgers = {
        mode: {
            layer: defaultdict(set) for layer in LAYERS
        }
        for mode in MODES
    }
    exposure_records = []
    production_trace_match_count = 0
    production_trace_count = 0
    total_changes = {
        layer: 0 for layer in LAYERS
    }
    total_field_changes = {
        name: 0 for name in DSF_FIELD_ORDER
    }
    change_witnesses = []
    all_exposure_mode_rows = {
        mode: {
            layer: []
            for layer in ("L0_SEV", *LAYERS)
        }
        for mode in MODES
    }

    for exposure, experience, source_event in settled:
        experience.verify()
        mode_rows_aggregate = {
            mode: {
                layer: []
                for layer in ("L0_SEV", *LAYERS)
            }
            for mode in MODES
        }
        exposure_changes = {
            layer: 0 for layer in LAYERS
        }
        exposure_field_changes = {
            name: 0 for name in DSF_FIELD_ORDER
        }
        for component in _component_rows(experience):
            values = _dimensionless_values(component)
            current_kernel = _kernel(values, RelevanceMode.LEGACY_UNIT)
            diagnostic_kernel = _kernel(
                values,
                RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC,
            )
            current = _serialize_kernel(*current_kernel)
            diagnostic = _serialize_kernel(*diagnostic_kernel)
            production = _trace_from_component(experience, component)
            production_trace_count += 1
            if all(current[layer] == production[layer] for layer in (
                "L0_SEV",
                *LAYERS,
            )):
                production_trace_match_count += 1
            else:
                raise RuntimeError(
                    "current relevance recomputation differs from receipted "
                    "production trace"
                )
            for mode, rows in (
                ("current_unit_relevance", current),
                ("structural_activity_diagnostic", diagnostic),
            ):
                _add_ledgers(
                    exposure_name=exposure.name,
                    component=component,
                    mode_rows=rows,
                    state_ledgers=state_ledgers[mode],
                    transition_ledgers=transition_ledgers[mode],
                )
                for layer in ("L0_SEV", *LAYERS):
                    mode_rows_aggregate[mode][layer].extend(rows[layer])
                    all_exposure_mode_rows[mode][layer].extend(rows[layer])
            comparison = _compare_component(
                component,
                current,
                diagnostic,
            )
            for layer, count in comparison[
                "layer_changed_row_counts"
            ].items():
                exposure_changes[layer] += count
                total_changes[layer] += count
            for name, count in comparison[
                "L4_changed_field_coordinate_counts"
            ].items():
                exposure_field_changes[name] += count
                total_field_changes[name] += count
            for witness in comparison[
                "bounded_first_causal_L4_change_witnesses"
            ]:
                if len(change_witnesses) < WITNESS_LIMIT:
                    change_witnesses.append({
                        "exposure_name": exposure.name,
                        **witness,
                    })
        record_modes = {
            mode: _metric_summary(mode_rows_aggregate[mode])
            for mode in MODES
        }
        exposure_records.append({
            "category": exposure.category,
            "mode_aggregate_counts": record_modes,
            "name": exposure.name,
            "path": str(exposure.path.resolve()),
            "source_event": source_event,
            "source_sha256": hashlib.sha256(
                exposure.path.read_bytes()
            ).hexdigest(),
            "unit_to_diagnostic_reorganization": {
                "layer_changed_row_counts": exposure_changes,
                "L4_changed_field_coordinate_counts": (
                    exposure_field_changes
                ),
            },
        })

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
        if value.category == "noise_variant"
    }
    discrimination = {}
    for mode in MODES:
        discrimination[mode] = {
            layer: {
                "exact_native_states": _support_summary(
                    state_ledgers[mode][layer],
                    hello_names=hello_names,
                    unrelated_names=unrelated_names,
                    variant_names=variant_names,
                    record=_identity_record,
                ),
                "exact_native_adjacent_transitions": _support_summary(
                    transition_ledgers[mode][layer],
                    hello_names=hello_names,
                    unrelated_names=unrelated_names,
                    variant_names=variant_names,
                    record=_transition_record,
                ),
            }
            for layer in LAYERS
        }

    print(json.dumps({
        "schema": (
            "guala.diagnostic.auditory_relevance_mode_comparison.v1"
        ),
        "authority_status": {
            "production_authority": False,
            "production_edits": False,
            "persistence_or_mount": False,
            "threshold_tuning": False,
            "diagnostic_mode": (
                RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC.value
            ),
            "warning": (
                "The structural-activity relevance branch is an existing "
                "unratified adapter diagnostic. Its outputs are not Guala "
                "production evidence and cannot authorize recognition."
            ),
        },
        "method": {
            "current_baseline": (
                "existing LEGACY_UNIT r(t)=1 recomputed from settled "
                "component samples"
            ),
            "baseline_trace_requirement": (
                "every recomputed current-unit L0-L4 row must exactly equal "
                "the complete canonical receipted production trace"
            ),
            "diagnostic_branch": (
                "existing STRUCTURAL_ACTIVITY_DIAGNOSTIC passed to "
                "compute_sev_series; all repository thresholds unchanged"
            ),
            "complete_field_comparison": (
                "topology-preserving L1, L2, L3, and ordered complete "
                "D/M/R/U/C/P/B L4 states and adjacent transitions"
            ),
            "forbidden_uses": [
                "classification authority",
                "production mounting",
                "scores",
                "sign projection",
                "templates",
                "threshold selection",
                "threshold tuning",
                "trits",
            ],
        },
        "production_baseline_verification": {
            "complete_trace_count": production_trace_count,
            "exact_match_count": production_trace_match_count,
            "all_exact": (
                production_trace_match_count == production_trace_count
            ),
        },
        "exposures": exposure_records,
        "all_exposure_mode_aggregate_counts": {
            mode: _metric_summary(all_exposure_mode_rows[mode])
            for mode in MODES
        },
        "unit_to_diagnostic_total_reorganization": {
            "layer_changed_row_counts": total_changes,
            "L4_changed_field_coordinate_counts": total_field_changes,
            "bounded_first_causal_L4_change_witnesses": change_witnesses,
        },
        "repeated_hello_vs_controls": discrimination,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
