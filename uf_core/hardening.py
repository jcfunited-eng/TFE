"""
UF-Spec v1.4.0 — Section 23 Hardening Framework
===============================================

Module: hardening.py

Purpose:
    Implement strict Hardening Trigger Conditions (HTC) and Section-23
    control interfaces used by UF kernel integrations.

Implemented HTC (strict mode):
    - HTC-1: DSF stability collapse          (dsf_stability < 0.3)
    - HTC-2: Directional stability collapse  (directional_stability < 0.4)
    - HTC-3: Hysteresis overload             (hysteresis_rate > 0.25)
    - HTC-4: Breathing instability           (breathing_rate > 0.20)
    - HTC-5: Composite metric collapse       (S(UF) < 0.50, R(UF) < 0.15)
    - HTC-6: Uncertainty excess              (uncertainty_rate > 0.20)
    - HTC-7: Gate drift excess               (gate_drift_rate > 0.25)

Implemented Section-23 interfaces:
    - hardening_actions()
    - safemode_criteria()
    - recovery_rules()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from uf_core.layer1 import Gate
from uf_core.layer4 import DSF


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
HYST_RATE_MAX = 0.25
BREATH_RATE_MAX = 0.20
S_UF_MIN = 0.50
R_UF_MIN = 0.15
U_RATE_MAX = 0.20
DRIFT_RATE_MAX = 0.25

# SafeMode recovery thresholds (strict but higher than collapse floor)
S_UF_RECOVERY_MIN = 0.60
R_UF_RECOVERY_MIN = 0.20


# ---------------------------------------------------------------------------
# HTC Evaluation
# ---------------------------------------------------------------------------

def evaluate_htc(
    stability_scores: Optional[Dict[str, float]] = None,
    sensitivity_data: Optional[List[Dict[str, float]]] = None,
    composite_metrics: Optional[Dict[str, float]] = None,
    l3_data=None,
    l2_data=None,
) -> HardeningEvaluationResult:
    """
    Evaluate Hardening Trigger Conditions in strict mode.
    """

    _ = l3_data
    _ = l2_data

    flags = kernel_status_flags()
    raw_metrics: Dict[str, float] = {}
    notes: List[str] = []

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

    hyst_rate = None
    if stability_scores and "hysteresis_rate" in stability_scores:
        hyst_rate = float(stability_scores["hysteresis_rate"])

    if hyst_rate is not None:
        raw_metrics["hysteresis_rate"] = hyst_rate
        if hyst_rate > HYST_RATE_MAX:
            flags.hysteresis_overload = True
            notes.append(f"Hysteresis rate above threshold ({HYST_RATE_MAX})")

    breath_rate = None
    if stability_scores and "breathing_rate" in stability_scores:
        breath_rate = float(stability_scores["breathing_rate"])

    if breath_rate is not None:
        raw_metrics["breathing_rate"] = breath_rate
        if breath_rate > BREATH_RATE_MAX:
            flags.breathing_instability = True
            notes.append(f"Breathing rate above threshold ({BREATH_RATE_MAX})")

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

    u_rate = None
    if stability_scores and "uncertainty_rate" in stability_scores:
        u_rate = float(stability_scores["uncertainty_rate"])

    if u_rate is not None:
        raw_metrics["uncertainty_rate"] = u_rate
        if u_rate > U_RATE_MAX:
            flags.uncertainty_excess = True
            notes.append(f"Uncertainty rate above threshold ({U_RATE_MAX})")

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
# Section-23 Interface Helpers
# ---------------------------------------------------------------------------

def _has_any_flags(flags: KernelStatusFlags) -> bool:
    return any(
        [
            flags.dsf_collapse,
            flags.directional_collapse,
            flags.hysteresis_overload,
            flags.breathing_instability,
            flags.composite_S_low,
            flags.composite_R_low,
            flags.uncertainty_excess,
            flags.gate_drift_excess,
        ]
    )


def _has_severe_flags(flags: KernelStatusFlags) -> bool:
    return bool(flags.dsf_collapse or flags.composite_S_low or flags.composite_R_low)


def hardening_actions(
    htc_result: HardeningEvaluationResult,
    dsf_list: List[DSF],
    current_gates: List[Gate],
    frozen_gates: Optional[List[Gate]] = None,
    enforce: bool = True,
) -> Tuple[List[DSF], List[Gate], List[str]]:
    """
    Apply Section-23 hardening actions in deterministic order.

    Action order:
      1) HA-2 stability ramp-down (if any HTC flag)
      2) HA-1 signal suppression  (if severe collapse)
      3) HA-3 gate freeze         (if gate drift excess)
    """

    if not enforce:
        return dsf_list, current_gates, ["hardening_actions_enforcement_disabled"]

    if htc_result is None:
        return dsf_list, current_gates, ["hardening_actions_skipped_no_htc_result"]

    flags = htc_result.flags
    if not _has_any_flags(flags):
        return dsf_list, current_gates, []

    from uf_core.hardening_actions import (
        apply_gate_freeze,
        apply_signal_suppression,
        apply_stability_rampdown,
    )

    notes: List[str] = []
    dsf_after = dsf_list
    gates_after = current_gates

    dsf_after = apply_stability_rampdown(htc_result, dsf_after)
    notes.append("HA-2_stability_rampdown_applied")

    if _has_severe_flags(flags):
        dsf_after = apply_signal_suppression(htc_result, dsf_after)
        notes.append("HA-1_signal_suppression_applied")

    if flags.gate_drift_excess:
        gates_after = apply_gate_freeze(
            htc_result=htc_result,
            current_gates=current_gates,
            frozen_gates=frozen_gates,
        )
        notes.append("HA-3_gate_freeze_applied")

    return dsf_after, gates_after, notes


def safemode_criteria(
    htc_result: HardeningEvaluationResult,
    composite_metrics: Optional[Dict[str, float]] = None,
    stability_scores: Optional[Dict[str, float]] = None,
) -> bool:
    """
    Strict SafeMode entry criteria.

    SafeMode enters when severe collapse semantics are present.
    Mirrors Section-23 severe mode and safemode.py entry policy.
    """

    _ = composite_metrics
    _ = stability_scores

    if htc_result is None:
        return False

    return _has_severe_flags(htc_result.flags)


def recovery_rules(
    htc_result: HardeningEvaluationResult,
    composite_metrics: Optional[Dict[str, float]] = None,
    stability_scores: Optional[Dict[str, float]] = None,
) -> bool:
    """
    Strict recovery rules for SafeMode exit readiness.

    Required:
      - Composite recovery floor is met.
      - No severe collapse flags are active.
      - If stability rates are provided, they are within HTC ceilings.
    """

    if htc_result is None:
        return False

    if composite_metrics is None:
        return False

    try:
        s_val = float(composite_metrics.get("S_UF", -1.0))
        r_val = float(composite_metrics.get("R_UF", -1.0))
    except Exception:
        return False

    if s_val <= S_UF_RECOVERY_MIN or r_val <= R_UF_RECOVERY_MIN:
        return False

    flags = htc_result.flags
    if _has_severe_flags(flags):
        return False

    if stability_scores is None:
        return True

    def _read(metric: str) -> Optional[float]:
        if metric not in stability_scores:
            return None
        try:
            return float(stability_scores[metric])
        except Exception:
            return None

    hyst_rate = _read("hysteresis_rate")
    breath_rate = _read("breathing_rate")
    u_rate = _read("uncertainty_rate")
    drift_rate = _read("gate_drift_rate")

    if hyst_rate is not None and hyst_rate > HYST_RATE_MAX:
        return False
    if breath_rate is not None and breath_rate > BREATH_RATE_MAX:
        return False
    if u_rate is not None and u_rate > U_RATE_MAX:
        return False
    if drift_rate is not None and drift_rate > DRIFT_RATE_MAX:
        return False

    return True
