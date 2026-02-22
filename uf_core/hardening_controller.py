"""
UF-Spec v1.4.0 — Section 23 Hardening Controller
=================================================

Policy behavior:
- Default: monitor-only telemetry (no enforcement) to preserve current TFE runtime behavior.
- Optional: deterministic enforcement path when `TFE_HARDENING_ENFORCE=1`.

This module keeps one control surface for both modes and always emits
hardening notes/flags for observability.
"""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from uf_core.hardening import (
    HardeningEvaluationResult,
    evaluate_htc,
    hardening_actions,
    recovery_rules,
    safemode_criteria,
)
from uf_core.layer1 import Gate
from uf_core.layer4 import DSF
from uf_core.safemode import (
    SafeModeState,
    apply_safemode_transform,
    enter_safemode,
    exit_safemode,
)


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


def _hardening_enforce_enabled() -> bool:
    value = str(os.environ.get("TFE_HARDENING_ENFORCE", "0")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def hardening_control_step(
    current_step: int,
    dsf_list: List[DSF],
    gates: List[Gate],
    composite_metrics: Dict[str, float],
    stability_scores: Dict[str, float],
    sensitivity_data: List[Dict[str, float]],
    safemode_state: SafeModeState,
) -> Tuple[List[DSF], List[Gate], SafeModeState, HardeningEvaluationResult]:
    """
    Hardening step with monitor-by-default runtime policy.

    Returns:
      - DSF list (possibly transformed in enforcement mode)
      - Gate list (possibly frozen in enforcement mode)
      - SafeMode state (unchanged in monitor-only mode)
      - HardeningEvaluationResult (always populated)
    """

    htc_result: HardeningEvaluationResult = evaluate_htc(
        stability_scores=stability_scores,
        sensitivity_data=sensitivity_data,
        composite_metrics=composite_metrics,
        l3_data=None,
        l2_data=None,
    )

    enforce = _hardening_enforce_enabled()

    if not enforce:
        if _has_any_flags(htc_result):
            htc_result.notes.append("hardening_monitor_only_no_enforcement")
        return dsf_list, gates, safemode_state, htc_result

    dsf_after, gates_after, action_notes = hardening_actions(
        htc_result=htc_result,
        dsf_list=dsf_list,
        current_gates=gates,
        frozen_gates=safemode_state.frozen_gates,
        enforce=True,
    )
    htc_result.notes.extend(action_notes)

    state_after = safemode_state

    if not state_after.safe_mode and safemode_criteria(
        htc_result=htc_result,
        composite_metrics=composite_metrics,
        stability_scores=stability_scores,
    ):
        state_after = enter_safemode(
            htc_result=htc_result,
            current_step=current_step,
            current_gates=gates_after,
            composite_metrics=composite_metrics,
            stability_scores=stability_scores,
            current_state=state_after,
        )
        if state_after.safe_mode:
            htc_result.notes.append("safemode_entered")

    if state_after.safe_mode:
        dsf_after = apply_safemode_transform(dsf_after, state_after)
        htc_result.notes.append("safemode_transform_applied")

        if recovery_rules(
            htc_result=htc_result,
            composite_metrics=composite_metrics,
            stability_scores=stability_scores,
        ):
            state_after = exit_safemode(state_after)
            htc_result.notes.append("safemode_exited")

    return dsf_after, gates_after, state_after, htc_result
