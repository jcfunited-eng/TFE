"""
UF-Spec v1.4.0 — Section 23 Hardening Actions
=============================================

Module: hardening_actions.py

Purpose:
    Define and implement Hardening Actions (HA) for the UF Kernel.

Implemented:
    - HA-1: Signal Suppression
    - HA-2: Stability Ramp-Down (φ = 0.25)
    - HA-3: Gate Freeze (Absolute Freeze Mode)
"""

from typing import List, Optional

from uf_core.hardening import HardeningEvaluationResult
from uf_core.layer1 import Gate
from uf_core.layer4 import DSF


# ---------------------------------------------------------------------------
# Helper: Determine if any hardening flag is raised
# ---------------------------------------------------------------------------

def _has_any_flags(htc_result: HardeningEvaluationResult) -> bool:
    f = htc_result.flags
    return any([
        f.dsf_collapse,
        f.directional_collapse,
        f.hysteresis_overload,
        f.breathing_instability,
        f.composite_S_low,
        f.composite_R_low,
        f.uncertainty_excess,
        f.gate_drift_excess,
    ])


def _has_critical_flags(htc_result: HardeningEvaluationResult) -> bool:
    """
    For HA-1, we treat ANY hardening flag as critical in this strict mode.
    A higher level controller can choose when to call HA-1 vs HA-2 vs HA-3.
    """
    return _has_any_flags(htc_result)


# ---------------------------------------------------------------------------
# HA-1: Signal Suppression (Strict Mode)
# ---------------------------------------------------------------------------

def apply_signal_suppression(
    htc_result: HardeningEvaluationResult,
    dsf_list: List[DSF],
) -> List[DSF]:
    if not _has_critical_flags(htc_result):
        return dsf_list

    suppressed: List[DSF] = []

    for dsf in dsf_list:
        suppressed.append(
            DSF(
                gate=dsf.gate,
                D_k=0,
                M_k=0,
                R_rev_k=0,
                U_star_k=dsf.U_star_k,
                P_k=0,
                B_k=0,
            )
        )

    return suppressed


# ---------------------------------------------------------------------------
# HA-2: Stability Ramp-Down (φ = 0.25)
# ---------------------------------------------------------------------------

DAMPING_FACTOR = 0.25  # φ


def apply_stability_rampdown(
    htc_result: HardeningEvaluationResult,
    dsf_list: List[DSF],
) -> List[DSF]:
    if not _has_any_flags(htc_result):
        return dsf_list

    damped: List[DSF] = []

    for dsf in dsf_list:
        damped.append(
            DSF(
                gate=dsf.gate,
                D_k=dsf.D_k * DAMPING_FACTOR,
                M_k=dsf.M_k * DAMPING_FACTOR,
                R_rev_k=dsf.R_rev_k * DAMPING_FACTOR,
                U_star_k=dsf.U_star_k,
                P_k=dsf.P_k * DAMPING_FACTOR,
                B_k=dsf.B_k * DAMPING_FACTOR,
            )
        )

    return damped


# ---------------------------------------------------------------------------
# HA-3: Gate Freeze (Absolute Freeze Mode)
# ---------------------------------------------------------------------------

def apply_gate_freeze(
    htc_result: HardeningEvaluationResult,
    current_gates: List[Gate],
    frozen_gates: Optional[List[Gate]] = None,
) -> List[Gate]:
    """
    Apply absolute freeze semantics to gate boundaries.

    Logic:
        - If gate_drift_excess flag is True:
            * If frozen_gates is not None:
                - Return frozen_gates unchanged.
            * Else:
                - Take a snapshot of current_gates and return it.
        - If gate_drift_excess is False:
            - Return current_gates unchanged.

    NOTE:
        - This function is stateless; it does not store frozen gates.
        - The caller is responsible for retaining any frozen snapshot and
          passing it back as frozen_gates on subsequent calls.
    """
    f = htc_result.flags

    # If no gate drift excess, gates pass through unchanged
    if not f.gate_drift_excess:
        return current_gates

    # If we already have a frozen snapshot, keep using it
    if frozen_gates is not None:
        return frozen_gates

    # Otherwise, snapshot current gates
    snapshot: List[Gate] = [g for g in current_gates]
    return snapshot
