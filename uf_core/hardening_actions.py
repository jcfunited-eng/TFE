"""
UF-Spec v1.4.0 — Section 23 Hardening Actions
==============================================

Implemented:
- HA-1: Signal Suppression
- HA-2: Stability Ramp-Down
- HA-3: Gate Freeze
"""

from __future__ import annotations

from typing import List, Optional

from uf_core.hardening import HardeningEvaluationResult
from uf_core.layer1 import Gate
from uf_core.layer4 import DSF


def _has_any_flags(htc_result: HardeningEvaluationResult) -> bool:
    f = htc_result.flags
    return any(
        [
            f.dsf_collapse,
            f.directional_collapse,
            f.hysteresis_overload,
            f.breathing_instability,
            f.composite_S_low,
            f.composite_R_low,
            f.uncertainty_excess,
            f.gate_drift_excess,
        ]
    )


def _has_critical_flags(htc_result: HardeningEvaluationResult) -> bool:
    return _has_any_flags(htc_result)


def apply_signal_suppression(htc_result: HardeningEvaluationResult, dsf_list: List[DSF]) -> List[DSF]:
    if not _has_critical_flags(htc_result):
        return dsf_list

    suppressed: List[DSF] = []
    for dsf in dsf_list:
        suppressed.append(
            DSF(
                gate=dsf.gate,
                D_k=0.0,
                M_k=0.0,
                R_rev_k=0.0,
                U_star_k=float(dsf.U_star_k),
                C_k=float(dsf.C_k),
                P_k=0.0,
                B_k=0.0,
            )
        )

    return suppressed


DAMPING_FACTOR = 0.25


def apply_stability_rampdown(htc_result: HardeningEvaluationResult, dsf_list: List[DSF]) -> List[DSF]:
    if not _has_any_flags(htc_result):
        return dsf_list

    damped: List[DSF] = []
    for dsf in dsf_list:
        damped.append(
            DSF(
                gate=dsf.gate,
                D_k=float(dsf.D_k) * DAMPING_FACTOR,
                M_k=float(dsf.M_k) * DAMPING_FACTOR,
                R_rev_k=float(dsf.R_rev_k) * DAMPING_FACTOR,
                U_star_k=float(dsf.U_star_k),
                C_k=float(dsf.C_k),
                P_k=float(dsf.P_k) * DAMPING_FACTOR,
                B_k=float(dsf.B_k) * DAMPING_FACTOR,
            )
        )

    return damped


def apply_gate_freeze(
    htc_result: HardeningEvaluationResult,
    current_gates: List[Gate],
    frozen_gates: Optional[List[Gate]] = None,
) -> List[Gate]:
    f = htc_result.flags

    if not f.gate_drift_excess:
        return current_gates

    if frozen_gates is not None:
        return frozen_gates

    snapshot: List[Gate] = [g for g in current_gates]
    return snapshot
