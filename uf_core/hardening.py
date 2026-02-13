"""
UF-Spec v1.4.0 — Section 23 Hardening Framework
===============================================

Module: hardening.py

Purpose:
    Implement strict Hardening Trigger Conditions (HTC) for UF Kernel.

Implemented HTC (strict mode):
    - HTC-1: DSF stability collapse          (dsf_stability < 0.3)
    - HTC-2: Directional stability collapse  (directional_stability < 0.4)
    - HTC-3: Hysteresis overload             (hysteresis_rate > 0.25)
    - HTC-4: Breathing instability           (breathing_rate > 0.20)
    - HTC-5: Composite metric collapse       (S(UF) < 0.50, R(UF) < 0.15)
    - HTC-6: Uncertainty excess              (uncertainty_rate > 0.20)
    - HTC-7: Gate drift excess               (gate_drift_rate > 0.25)

Placeholders:
    - hardening_actions()
    - safemode_criteria()
    - recovery_rules()
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Kernel Status Flags
# ---------------------------------------------------------------------------

@dataclass
class KernelStatusFlags:
    dsf_collapse: bool = False
    directional_collapse: bool = False
    hysteresis_overload: bool = False
    breathing_instability: bool = False
    composite_S_low: bool = False
    composite_R_low: bool = False
    uncertainty_excess: bool = False
    gate_drift_excess: bool = False


def kernel_status_flags() -> KernelStatusFlags:
    return KernelStatusFlags()


# ---------------------------------------------------------------------------
# Hardening Evaluation Result
# ---------------------------------------------------------------------------

@dataclass
class HardeningEvaluationResult:
    flags: KernelStatusFlags
    raw_metrics: Dict[str, float]
    notes: List[str]


# ---------------------------------------------------------------------------
# Hardening Trigger Thresholds (STRICT)
# ---------------------------------------------------------------------------

DSF_STABILITY_MIN = 0.3
DIR_STABILITY_MIN = 0.4
HYST_RATE_MAX     = 0.25
BREATH_RATE_MAX   = 0.20
S_UF_MIN          = 0.50
R_UF_MIN          = 0.15
U_RATE_MAX        = 0.20
DRIFT_RATE_MAX    = 0.25   # HTC-7


# ---------------------------------------------------------------------------
# HTC Evaluation
# ---------------------------------------------------------------------------

def evaluate_htc(
    stability_scores: Optional[Dict[str, float]] = None,
    sensitivity_data: Optional[List[Dict[str, float]]] = None,
    composite_metrics: Optional[Dict[str, float]] = None,
    l3_data=None,
    l2_data=None,
):
    """
    Evaluate Hardening Trigger Conditions in strict mode.
    """

    flags = kernel_status_flags()
    raw_metrics: Dict[str, float] = {}
    notes: List[str] = []

    # ============================================================
    # HTC-1: DSF Collapse
    # ============================================================
    dsf_stab = None
    if stability_scores and "dsf" in stability_scores:
        dsf_stab = float(stability_scores["dsf"])
    elif sensitivity_data:
        try:
            dsf_stab = float(sensitivity_data[0]["dsf"])
        except Exception:
            dsf_stab = None

    if dsf_stab is not None:
        raw_metrics["dsf_stability"] = dsf_stab
        if dsf_stab < DSF_STABILITY_MIN:
            flags.dsf_collapse = True
            notes.append(f"DSF stability below threshold ({DSF_STABILITY_MIN})")

    # ============================================================
    # HTC-2: Directional Collapse
    # ============================================================
    dir_stab = None
    if stability_scores and "directional" in stability_scores:
        dir_stab = float(stability_scores["directional"])
    elif sensitivity_data:
        try:
            dir_stab = float(sensitivity_data[0]["directional"])
        except Exception:
            dir_stab = None

    if dir_stab is not None:
        raw_metrics["directional_stability"] = dir_stab
        if dir_stab < DIR_STABILITY_MIN:
            flags.directional_collapse = True
            notes.append(f"Directional stability below threshold ({DIR_STABILITY_MIN})")

    # ============================================================
    # HTC-3: Hysteresis Overload
    # ============================================================
    hyst_rate = None
    if stability_scores and "hysteresis_rate" in stability_scores:
        hyst_rate = float(stability_scores["hysteresis_rate"])

    if hyst_rate is not None:
        raw_metrics["hysteresis_rate"] = hyst_rate
        if hyst_rate > HYST_RATE_MAX:
            flags.hysteresis_overload = True
            notes.append(f"Hysteresis rate above threshold ({HYST_RATE_MAX})")

    # ============================================================
    # HTC-4: Breathing Instability
    # ============================================================
    breath_rate = None
    if stability_scores and "breathing_rate" in stability_scores:
        breath_rate = float(stability_scores["breathing_rate"])

    if breath_rate is not None:
        raw_metrics["breathing_rate"] = breath_rate
        if breath_rate > BREATH_RATE_MAX:
            flags.breathing_instability = True
            notes.append(f"Breathing rate above threshold ({BREATH_RATE_MAX})")

    # ============================================================
    # HTC-5: Composite Collapse
    # ============================================================
    if composite_metrics:
        S_val = composite_metrics.get("S_UF", None)
        R_val = composite_metrics.get("R_UF", None)

        if S_val is not None:
            S_val = float(S_val)
            raw_metrics["S_UF"] = S_val
            if S_val < S_UF_MIN:
                flags.composite_S_low = True
                notes.append(f"S(UF) below threshold ({S_UF_MIN})")

        if R_val is not None:
            R_val = float(R_val)
            raw_metrics["R_UF"] = R_val
            if R_val < R_UF_MIN:
                flags.composite_R_low = True
                notes.append(f"R(UF) below threshold ({R_UF_MIN})")

    # ============================================================
    # HTC-6: Uncertainty Excess
    # ============================================================
    u_rate = None
    if stability_scores and "uncertainty_rate" in stability_scores:
        u_rate = float(stability_scores["uncertainty_rate"])

    if u_rate is not None:
        raw_metrics["uncertainty_rate"] = u_rate
        if u_rate > U_RATE_MAX:
            flags.uncertainty_excess = True
            notes.append(f"Uncertainty rate above threshold ({U_RATE_MAX})")

    # ============================================================
    # HTC-7: Gate Drift Excess
    # ============================================================
    drift_rate = None
    if stability_scores and "gate_drift_rate" in stability_scores:
        drift_rate = float(stability_scores["gate_drift_rate"])

    if drift_rate is not None:
        raw_metrics["gate_drift_rate"] = drift_rate
        if drift_rate > DRIFT_RATE_MAX:
            flags.gate_drift_excess = True
            notes.append(f"Gate drift rate above threshold ({DRIFT_RATE_MAX})")

    return HardeningEvaluationResult(
        flags=flags,
        raw_metrics=raw_metrics,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Hardening Actions (HA) — Placeholder
# ---------------------------------------------------------------------------

def hardening_actions():
    raise NotImplementedError("hardening_actions() not implemented yet.")


# ---------------------------------------------------------------------------
# SafeMode Entry Criteria — Placeholder
# ---------------------------------------------------------------------------

def safemode_criteria():
    raise NotImplementedError("safemode_criteria() not implemented yet.")


# ---------------------------------------------------------------------------
# Recovery Rules — Placeholder
# ---------------------------------------------------------------------------

def recovery_rules():
    raise NotImplementedError("recovery_rules() not implemented yet.")
