"""
UF-Spec v1.4.0 — Section 23 Hardening Controller

Controller policy (corrected):

    1. SafeMode (highest priority)
    2. HA-1 Signal Suppression ONLY for true collapse:
         - dsf_collapse
         - composite_S_low
         - composite_R_low
    3. HA-3 Gate Freeze
    4. HA-2 Stability Ramp-Down
    5. Else: normal behavior
"""

from typing import Dict, List, Tuple

from uf_core.hardening import evaluate_htc, HardeningEvaluationResult
from uf_core.hardening_actions import (
    apply_signal_suppression,
    apply_stability_rampdown,
    apply_gate_freeze,
)
from uf_core.safemode import (
    SafeModeState,
    enter_safemode,
    apply_safemode_transform,
    should_attempt_recovery,
    exit_safemode,
)
from uf_core.layer1 import Gate
from uf_core.layer4 import DSF


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
    Perform one hardening control step.

    Priority:
        1. SafeMode
        2. HA-1 Signal Suppression (true collapse only)
        3. HA-3 Gate Freeze
        4. HA-2 Stability Ramp-Down
        5. Normal
    """

    # 1) Evaluate HTC
    htc_result: HardeningEvaluationResult = evaluate_htc(
        stability_scores=stability_scores,
        sensitivity_data=sensitivity_data,
        composite_metrics=composite_metrics,
        l3_data=None,
        l2_data=None,
    )

    # 2) Update SafeMode state
    new_safemode = enter_safemode(
        htc_result=htc_result,
        current_step=current_step,
        current_gates=gates,
        composite_metrics=composite_metrics,
        stability_scores=stability_scores,
        current_state=safemode_state,
    )

    # 3) Priority 1 — SafeMode
    if new_safemode.safe_mode:
        if new_safemode.frozen_gates is not None:
            new_gates = new_safemode.frozen_gates
        else:
            new_gates = gates

        new_dsf = apply_safemode_transform(dsf_list, new_safemode)
        return new_dsf, new_gates, new_safemode, htc_result

    # From here on, SafeMode is OFF.
    f = htc_result.flags

    # Extract directional and DSF stability where possible
    dir_stab = stability_scores.get("directional", None)
    dsf_stab = stability_scores.get("dsf", None)

    # 4) Priority 2 — HA-1 Signal Suppression (STRICT collapse only)
    if f.dsf_collapse or f.composite_S_low or f.composite_R_low:
        new_dsf = apply_signal_suppression(htc_result, dsf_list)
        new_gates = gates
        return new_dsf, new_gates, new_safemode, htc_result

    # 5) Priority 3 — HA-3 Gate Freeze
    if f.gate_drift_excess:
        new_gates = apply_gate_freeze(
            htc_result=htc_result,
            current_gates=gates,
            frozen_gates=None,
        )
        new_dsf = dsf_list
        return new_dsf, new_gates, new_safemode, htc_result

    # 6) Priority 4 — HA-2 Stability Ramp-Down
    ramp_condition = False
    if dir_stab is not None and dir_stab < 0.4:
        ramp_condition = True
    if dsf_stab is not None and dsf_stab < 0.3:
        ramp_condition = True

    if ramp_condition:
        new_dsf = apply_stability_rampdown(htc_result, dsf_list)
        new_gates = gates
        return new_dsf, new_gates, new_safemode, htc_result

    # 7) Priority 5 — Normal behavior
    return dsf_list, gates, new_safemode, htc_result
