"""Non-authoritative cochlear-band chemical relevance diagnostic.

The packaged virtual-story auditory R/A/D receiver profile exposes one
emulator-only auditory port.  This probe does not relabel that port or invent
16 authorities.  It runs 16 isolated state trajectories of the same mounted
one-port law, one per measured cochlear pressure band.  Each band is driven by
the provider's pressure-envelope RMS at its native observation hop; its paired
phase component receives the same certified binary64 receptor relevance.

The five exposures form one continuous chemical sequence.  Receiver state is
never reset between exposures.  Constant and structural-activity relevance
are recomputed as non-stateful comparison branches.  Nothing is mounted into
Guala, persisted as learned state, or asserted to be physically calibrated.
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

from dsf_ai_service.glew_runtime.chemical_receiver import (
    CHEMICAL_AFFINE_CONSTRAINT_ID,
    CertifiedReceiverState,
    ExactReceiverState,
)
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.story_chemistry import (
    Binary64RoundingStatus,
    PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE,
    StoryChemistryStatus,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
    evolve_story_chemistry_event,
    mount_packaged_production_story_chemistry,
    story_boundary_observation_receipt_payload,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
from tools.probe_auditory_relevance_diagnostic_comparison import (
    LAYERS,
    _add_ledgers,
    _compare_component,
    _dimensionless_values,
    _identity_record,
    _kernel,
    _metric_summary,
    _serialize_kernel,
    _support_summary,
    _transition_record,
)
from tools.probe_auditory_surrounded_event_recognition import _experience
from uf_core.layer0 import RelevanceMode, SEV, compute_sev_series
from uf_core.layer1 import build_gate_l1_state, segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


AUDITORY_PORT = "story-auditory.native-port-0"
AUDITORY_UNIT = "virtual-normalized-acoustic-boundary-flux"
MODES = (
    "current_unit_relevance",
    "structural_activity_diagnostic",
    "continuous_chemical_receiver_diagnostic",
)
HOP_DURATION = Fraction(
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
WITNESS_LIMIT = 3
RUNTIME_KEY = (
    b"isolated non-authoritative auditory chemical diagnostic only"
)
RUNTIME_KEY_ID = "auditory-chemical-diagnostic-not-production"


@dataclass(frozen=True, slots=True)
class Exposure:
    name: str
    category: str
    path: Path


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _ball_bounds(value) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.lower_mantissa)
        * Fraction(2) ** value.lower_exponent,
        Fraction(value.upper_mantissa)
        * Fraction(2) ** value.upper_exponent,
    )


def _state_record(state) -> dict[str, object]:
    if isinstance(state, ExactReceiverState):
        components = {
            name: {
                "lower": _fraction_text(value),
                "upper": _fraction_text(value),
            }
            for name, value in zip(
                ("R", "A", "D"),
                state.components,
                strict=True,
            )
        }
        constraint = "exact_R_plus_A_plus_D_equals_R_total"
    elif isinstance(state, CertifiedReceiverState):
        components = {
            name: {
                "lower": _fraction_text(bounds[0]),
                "upper": _fraction_text(bounds[1]),
            }
            for name, bounds in zip(
                ("R", "A", "D"),
                (_ball_bounds(value) for value in state.components),
                strict=True,
            )
        }
        constraint = state.exact_affine_constraint_id
    else:
        raise RuntimeError("chemical state changed type")
    return {
        "affine_constraint": constraint,
        "component_enclosures": components,
        "port_id": state.port_id,
        "receipt_sha256": state.receipt_sha256,
        "source_time": _fraction_text(state.source_time),
        "total_receptor_mass": _fraction_text(
            state.total_receptor_mass
        ),
    }


def _observation(
    *,
    band_index: int,
    exposure_index: int,
    sample_index: int,
    start: Fraction,
    flux: Fraction,
) -> StoryPhysicalBoundaryEvent:
    event_id = (
        f"chem-diag-b{band_index:02d}-e{exposure_index:02d}-"
        f"s{sample_index:04d}"
    )
    observation_id = f"{event_id}:auditory-rms"
    provenance = _canonical({
        "authority": "non-authoritative-diagnostic-only",
        "band_index": band_index,
        "exposure_index": exposure_index,
        "measurement": "provider-pressure-envelope-rms-full-scale",
        "sample_index": sample_index,
        "schema": "guala.diagnostic.auditory_chemical_flux.v1",
        "warning": (
            "numeric assignment to virtual acoustic flux has no physical "
            "calibration authority"
        ),
    })
    provenance_digest = receipt_sha256(provenance)
    payload = story_boundary_observation_receipt_payload(
        event_id=event_id,
        observation_id=observation_id,
        port_id=AUDITORY_PORT,
        source_time_start=start,
        source_time_end=start + HOP_DURATION,
        signed_native_flux=flux,
        native_flux_unit=AUDITORY_UNIT,
        provenance_receipt_sha256=provenance_digest,
    )
    observation = StoryPhysicalBoundaryObservation(
        event_id=event_id,
        observation_id=observation_id,
        port_id=AUDITORY_PORT,
        source_time_start=start,
        source_time_end=start + HOP_DURATION,
        signed_native_flux=flux,
        native_flux_unit=AUDITORY_UNIT,
        provenance_receipt_sha256=provenance_digest,
        provenance_receipt_payload=provenance,
        observation_receipt_sha256=receipt_sha256(payload),
        observation_receipt_payload=payload,
    )
    return StoryPhysicalBoundaryEvent(
        event_id=event_id,
        observations=(observation,),
    )


def _kernel_with_relevance(
    values: list[float],
    relevance: list[Fraction],
):
    if len(values) != len(relevance):
        raise RuntimeError("chemical relevance left component grid")
    base = tuple(compute_sev_series(
        pd.DataFrame({"field": values}),
        "field",
        relevance_mode=RelevanceMode.LEGACY_UNIT,
    ))
    sev = tuple(
        SEV(
            F_norm=value.F_norm,
            dF=value.dF,
            sigma=value.sigma,
            kappa=value.kappa,
            relevance=float(relevance_value),
            N=value.N,
        )
        for value, relevance_value in zip(
            base,
            relevance,
            strict=True,
        )
    )
    gates = tuple(segment_gates(sev))
    l1 = tuple(build_gate_l1_state(sev, gates))
    l2 = tuple(interpret_gates(sev, gates))
    l3 = tuple(compute_resonance(l2))
    l4 = tuple(compute_dsf(compute_directional_signal(list(l3))))
    if not gates or len({len(gates), len(l1), len(l2), len(l3), len(l4)}) != 1:
        raise RuntimeError("chemical diagnostic L0-L4 trajectory incomplete")
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
        raise RuntimeError("chemical diagnostic gate trajectory diverged")
    return sev, l1, l2, l3, l4


def _empty_rows() -> dict[str, list[dict[str, object]]]:
    return {
        layer: []
        for layer in ("L0_SEV", *LAYERS)
    }


def _merge_rows(
    target: dict[str, list[dict[str, object]]],
    source: dict[str, list[dict[str, object]]],
) -> None:
    for layer in target:
        target[layer].extend(source[layer])


def _add_change_counts(
    target: dict[str, Any],
    comparison: dict[str, object],
) -> None:
    layer_changes = comparison["layer_changed_row_counts"]
    field_changes = comparison["L4_changed_field_coordinate_counts"]
    if not isinstance(layer_changes, dict) or not isinstance(
        field_changes,
        dict,
    ):
        raise RuntimeError("comparison summary changed shape")
    for name, count in layer_changes.items():
        target["layer_changed_row_counts"][name] += int(count)
    for name, count in field_changes.items():
        target["L4_changed_field_coordinate_counts"][name] += int(
            count
        )
    for witness in comparison[
        "bounded_first_causal_L4_change_witnesses"
    ]:
        if len(target["bounded_first_causal_L4_change_witnesses"]) < (
            WITNESS_LIMIT
        ):
            target["bounded_first_causal_L4_change_witnesses"].append(
                witness
            )


def _change_accumulator() -> dict[str, object]:
    return {
        "layer_changed_row_counts": {
            layer: 0 for layer in LAYERS
        },
        "L4_changed_field_coordinate_counts": {
            name: 0
            for name in (
                "D_k",
                "M_k",
                "R_rev_k",
                "U_star_k",
                "C_k",
                "P_k",
                "B_k",
            )
        },
        "bounded_first_causal_L4_change_witnesses": [],
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
    if Counter(value.category for value in exposures) != Counter({
        "independent_hello": 3,
        "unrelated_phrase": 1,
        "noise_variant": 1,
    }):
        raise SystemExit(
            "requires three independent hello, one unrelated, one noise"
        )
    if len({value.name for value in exposures}) != len(exposures):
        raise SystemExit("exposure names must be unique")
    for exposure in exposures:
        if not exposure.path.is_file():
            raise SystemExit(f"exposure is absent: {exposure.path}")

    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=RUNTIME_KEY,
        runtime_key_id=RUNTIME_KEY_ID,
    )
    if (
        mounted.status is not StoryChemistryStatus.MOUNTED
        or mounted.runtime is None
    ):
        raise SystemExit(
            "packaged emulator chemistry cannot mount: "
            f"{mounted.reason}"
        )
    base_runtime = mounted.runtime
    if (
        base_runtime.manifest.authority_scope
        != PRODUCTION_STORY_CHEMISTRY_AUTHORITY_SCOPE
        or tuple(
            port.port_id
            for port in base_runtime.manifest.ports
            if port.kernel_binding.lane_id == "sound"
        )
        != (AUDITORY_PORT,)
    ):
        raise SystemExit(
            "emulator profile does not expose exactly one auditory law"
        )
    auditory_port = base_runtime.manifest.port(AUDITORY_PORT)
    if (
        auditory_port.native_signal_unit != AUDITORY_UNIT
        or auditory_port.time_unit.seconds_per_unit != 1
        or auditory_port.initial_state.total_receptor_mass != 1
    ):
        raise SystemExit("auditory emulator law changed")

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

    band_runtimes = [base_runtime] * COCHLEAR_CHANNEL_COUNT
    prior_endpoint_receipts: list[str] | None = None
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
    all_mode_rows = {
        mode: _empty_rows() for mode in MODES
    }
    changes = {
        "chemical_vs_current": _change_accumulator(),
        "chemical_vs_structural_activity": _change_accumulator(),
    }
    exposure_records = []
    chemical_evolution_count = 0
    certified_rounding_count = 0
    state_verification_count = 0
    continuity_match_count = 0

    for exposure_index, (
        exposure,
        experience,
        source_event,
    ) in enumerate(settled):
        experience.verify()
        if len(experience.channels) != COCHLEAR_CHANNEL_COUNT:
            raise RuntimeError("cochlear topology changed")
        pressure_components = tuple(
            channel.pressure for channel in experience.channels
        )
        sample_count = len(pressure_components[0].samples)
        if any(
            len(component.samples) != sample_count
            for component in pressure_components
        ):
            raise RuntimeError("cochlear pressure grids diverged")
        start_states = tuple(
            runtime.state(AUDITORY_PORT)
            for runtime in band_runtimes
        )
        start_receipts = [
            state.receipt_sha256 for state in start_states
        ]
        if prior_endpoint_receipts is not None:
            matches = sum(
                left == right
                for left, right in zip(
                    start_receipts,
                    prior_endpoint_receipts,
                    strict=True,
                )
            )
            if matches != COCHLEAR_CHANNEL_COUNT:
                raise RuntimeError(
                    "chemical state reset between exposures"
                )
            continuity_match_count += matches

        relevance_by_band: list[list[Fraction]] = [
            [] for _ in range(COCHLEAR_CHANNEL_COUNT)
        ]
        for sample_index in range(sample_count):
            for band_index, component in enumerate(
                pressure_components
            ):
                runtime = band_runtimes[band_index]
                state = runtime.state(AUDITORY_PORT)
                flux = component.samples[sample_index].signal
                if not 0 <= flux <= 1:
                    raise RuntimeError(
                        "measured pressure RMS left full scale"
                    )
                evolved = evolve_story_chemistry_event(
                    runtime=runtime,
                    event=_observation(
                        band_index=band_index,
                        exposure_index=exposure_index,
                        sample_index=sample_index,
                        start=state.source_time,
                        flux=flux,
                    ),
                )
                if (
                    evolved.status is not StoryChemistryStatus.EVOLVED
                    or len(evolved.outputs) != 1
                ):
                    raise RuntimeError(
                        "chemical diagnostic evolution failed: "
                        f"{evolved.reason}"
                    )
                output = evolved.outputs[0]
                rounding = output.kernel_binary64_relevance
                if (
                    rounding.status
                    is not Binary64RoundingStatus.CERTIFIED
                    or rounding.exact_binary64 is None
                ):
                    raise RuntimeError(
                        "chemical relevance lacks certified binary64"
                    )
                output.state.verify(evolved.runtime.receipt_registry)
                if (
                    output.state.total_receptor_mass != 1
                    or output.state.exact_affine_constraint_id
                    != CHEMICAL_AFFINE_CONSTRAINT_ID
                ):
                    raise RuntimeError(
                        "chemical receptor mass/state was not conserved"
                    )
                band_runtimes[band_index] = evolved.runtime
                relevance_by_band[band_index].append(
                    rounding.exact_binary64
                )
                chemical_evolution_count += 1
                certified_rounding_count += 1
                state_verification_count += 1

        end_states = tuple(
            runtime.state(AUDITORY_PORT)
            for runtime in band_runtimes
        )
        end_receipts = [
            state.receipt_sha256 for state in end_states
        ]
        prior_endpoint_receipts = end_receipts
        state_changed_band_count = sum(
            left != right
            for left, right in zip(
                start_receipts,
                end_receipts,
                strict=True,
            )
        )
        if state_changed_band_count != COCHLEAR_CHANNEL_COUNT:
            raise RuntimeError(
                "one or more chemical band states did not evolve"
            )

        exposure_mode_rows = {
            mode: _empty_rows() for mode in MODES
        }
        for band_index, channel in enumerate(experience.channels):
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            ):
                values = _dimensionless_values(component)
                current = _serialize_kernel(*_kernel(
                    values,
                    RelevanceMode.LEGACY_UNIT,
                ))
                structural = _serialize_kernel(*_kernel(
                    values,
                    RelevanceMode.STRUCTURAL_ACTIVITY_DIAGNOSTIC,
                ))
                chemical = _serialize_kernel(*_kernel_with_relevance(
                    values,
                    relevance_by_band[band_index],
                ))
                rows_by_mode = {
                    "current_unit_relevance": current,
                    "structural_activity_diagnostic": structural,
                    "continuous_chemical_receiver_diagnostic": chemical,
                }
                for mode, rows in rows_by_mode.items():
                    _merge_rows(exposure_mode_rows[mode], rows)
                    _merge_rows(all_mode_rows[mode], rows)
                    _add_ledgers(
                        exposure_name=exposure.name,
                        component=component,
                        mode_rows=rows,
                        state_ledgers=state_ledgers[mode],
                        transition_ledgers=transition_ledgers[mode],
                    )
                _add_change_counts(
                    changes["chemical_vs_current"],
                    _compare_component(
                        component,
                        current,
                        chemical,
                    ),
                )
                _add_change_counts(
                    changes["chemical_vs_structural_activity"],
                    _compare_component(
                        component,
                        structural,
                        chemical,
                    ),
                )

        chemical_relevances = [
            value
            for band in relevance_by_band
            for value in band
        ]
        exposure_records.append({
            "category": exposure.category,
            "chemical_receptor_sequence": {
                "band_state_changed_count": state_changed_band_count,
                "certified_relevance_count": len(
                    chemical_relevances
                ),
                "distinct_exact_relevance_count": len(set(
                    chemical_relevances
                )),
                "exact_relevance_minimum": _fraction_text(
                    min(chemical_relevances)
                ),
                "exact_relevance_maximum": _fraction_text(
                    max(chemical_relevances)
                ),
                "first_three_band_endpoint_witnesses": [
                    {
                        "band_id": AUDITORY_CHANNELS[index].name,
                        "band_index": index,
                        "start_state": _state_record(
                            start_states[index]
                        ),
                        "end_state": _state_record(end_states[index]),
                    }
                    for index in range(min(
                        WITNESS_LIMIT,
                        COCHLEAR_CHANNEL_COUNT,
                    ))
                ],
            },
            "index": exposure_index,
            "mode_aggregate_counts": {
                mode: _metric_summary(rows)
                for mode, rows in exposure_mode_rows.items()
            },
            "name": exposure.name,
            "path": str(exposure.path.resolve()),
            "source_event": source_event,
            "source_sha256": hashlib.sha256(
                exposure.path.read_bytes()
            ).hexdigest(),
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
    recurrence = {
        mode: {
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
        for mode in MODES
    }
    separability_change = {
        layer: {
            "current_state_exclusive_count": recurrence[
                "current_unit_relevance"
            ][layer]["exact_native_states"][
                "all_three_hello_absent_both_controls"
            ],
            "structural_state_exclusive_count": recurrence[
                "structural_activity_diagnostic"
            ][layer]["exact_native_states"][
                "all_three_hello_absent_both_controls"
            ],
            "continuous_chemical_state_exclusive_count": recurrence[
                "continuous_chemical_receiver_diagnostic"
            ][layer]["exact_native_states"][
                "all_three_hello_absent_both_controls"
            ],
            "continuous_chemical_increased_exact_state_separability": (
                recurrence[
                    "continuous_chemical_receiver_diagnostic"
                ][layer]["exact_native_states"][
                    "all_three_hello_absent_both_controls"
                ]
                > max(
                    recurrence["current_unit_relevance"][layer][
                        "exact_native_states"
                    ]["all_three_hello_absent_both_controls"],
                    recurrence[
                        "structural_activity_diagnostic"
                    ][layer]["exact_native_states"][
                        "all_three_hello_absent_both_controls"
                    ],
                )
            ),
        }
        for layer in LAYERS
    }

    print(json.dumps({
        "schema": (
            "guala.diagnostic.auditory_chemical_receiver_comparison.v1"
        ),
        "authority_status": {
            "production_authority": False,
            "production_edits": False,
            "production_mount_or_persistence": False,
            "physical_calibration_authority": False,
            "threshold_tuning": False,
            "profile_authority_scope_as_declared": (
                base_runtime.manifest.authority_scope
            ),
            "warning": (
                "The profile is a virtual-story emulator authority with one "
                "auditory port. Sixteen isolated trajectories replicate its "
                "law for diagnosis only; they are not sixteen calibrated "
                "cochlear authorities. Pressure RMS is assigned numerically "
                "to virtual flux only because this diagnostic requested it."
            ),
        },
        "topology_and_law": {
            "declared_auditory_profile_port_count": 1,
            "declared_auditory_profile_port_id": AUDITORY_PORT,
            "diagnostic_independent_band_trajectory_count": (
                COCHLEAR_CHANNEL_COUNT
            ),
            "kernel_component_count_receiving_relevance": (
                COCHLEAR_CHANNEL_COUNT * 2
            ),
            "paired_phase_relevance_rule": (
                "exact certified binary64 relevance inherited from the "
                "same band pressure-envelope RMS receiver"
            ),
            "observation_hop_duration_seconds": _fraction_text(
                HOP_DURATION
            ),
            "rates_and_susceptibility": {
                "activation_susceptibility": _fraction_text(
                    auditory_port.activation_susceptibility
                    .susceptibility_per_native_signal_unit_per_time_unit
                ),
                "ordered_rates": [
                    {
                        "transition": value.transition.value,
                        "rate_per_time_unit": _fraction_text(
                            value.rate_per_time_unit
                        ),
                    }
                    for value in auditory_port.rates
                ],
            },
        },
        "conservation_and_continuity": {
            "affine_constraint": CHEMICAL_AFFINE_CONSTRAINT_ID,
            "total_receptor_mass": "1/1",
            "chemical_evolution_count": chemical_evolution_count,
            "certified_binary64_relevance_count": (
                certified_rounding_count
            ),
            "verified_evolved_state_count": state_verification_count,
            "exposure_boundary_count": len(exposures) - 1,
            "band_state_continuity_match_count": (
                continuity_match_count
            ),
            "expected_band_state_continuity_match_count": (
                (len(exposures) - 1) * COCHLEAR_CHANNEL_COUNT
            ),
            "receiver_state_reset_between_exposures": False,
        },
        "exposures": exposure_records,
        "all_exposure_mode_aggregate_counts": {
            mode: _metric_summary(rows)
            for mode, rows in all_mode_rows.items()
        },
        "complete_field_reorganization": changes,
        "repeated_hello_vs_controls": recurrence,
        "continuous_repeated_exposure_separability": (
            separability_change
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
