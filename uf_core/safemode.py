"""
UF-Spec v1.4.0 — Section 23 SafeMode Framework
==============================================

Module: safemode.py

Purpose:
    Define the SafeMode state and interfaces for:
        - SafeMode entry
        - SafeMode DSF transforms
        - Recovery evaluation
        - SafeMode exit

This version implements:
    - SafeModeState dataclass
    - init_safemode_state()
    - enter_safemode() (strict severe-collapse only)
    - apply_safemode_transform() (total action freeze)
    - should_attempt_recovery() (composite-only criteria)
    - exit_safemode() (strict reset of SafeMode flags)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from uf_core.hardening import HardeningEvaluationResult
from uf_core.layer1 import Gate
from uf_core.layer4 import DSF
from uf_core.hardening_actions import apply_signal_suppression


@dataclass
class SafeModeState:
    safe_mode: bool = False
    entry_step: Optional[int] = None
    entry_reasons: List[str] = field(default_factory=list)
    frozen_gates: Optional[List[Gate]] = None
    latest_metrics: Dict[str, float] = field(default_factory=dict)


def init_safemode_state() -> SafeModeState:
    """
    Initialize and return a neutral SafeModeState.
    """
    return SafeModeState()


def enter_safemode(
    htc_result: HardeningEvaluationResult,
    current_step: int,
    current_gates: List[Gate],
    composite_metrics: Dict[str, float],
    stability_scores: Dict[str, float],
    current_state: Optional[SafeModeState] = None,
) -> SafeModeState:
    """
    Enter SafeMode based on strict severe-collapse criteria:

        SafeMode triggers ONLY if ANY of:
            - dsf_collapse
            - composite_S_low
            - composite_R_low
    """

    if current_state is None:
        current_state = init_safemode_state()

    # If already in SafeMode, do nothing
    if current_state.safe_mode:
        return current_state

    f = htc_result.flags

    severe = (
        f.dsf_collapse
        or f.composite_S_low
        or f.composite_R_low
    )

    if not severe:
        return current_state

    entry_reasons: List[str] = []

    if f.dsf_collapse:
        entry_reasons.append("dsf_collapse")
    if f.composite_S_low:
        entry_reasons.append("composite_S_low")
    if f.composite_R_low:
        entry_reasons.append("composite_R_low")

    entry_reasons.extend(htc_result.notes)

    if current_state.frozen_gates is not None:
        frozen = current_state.frozen_gates
    else:
        frozen = [g for g in current_gates]

    latest_metrics = {}
    latest_metrics.update(composite_metrics or {})
    latest_metrics.update(stability_scores or {})

    return SafeModeState(
        safe_mode=True,
        entry_step=current_step,
        entry_reasons=entry_reasons,
        frozen_gates=frozen,
        latest_metrics=latest_metrics,
    )


def apply_safemode_transform(
    dsf_list: List[DSF],
    safemode_state: SafeModeState,
) -> List[DSF]:
    """
    Apply SafeMode DSF transform: TOTAL ACTION FREEZE (HA-1 semantics).
    """

    if not safemode_state.safe_mode:
        return dsf_list

    from uf_core.hardening import KernelStatusFlags, HardeningEvaluationResult as HER

    flags = KernelStatusFlags(dsf_collapse=True)
    htc_result = HER(flags=flags, raw_metrics={}, notes=[])

    return apply_signal_suppression(htc_result, dsf_list)


def should_attempt_recovery(
    safemode_state: SafeModeState,
    composite_metrics: Dict[str, float],
    stability_scores: Dict[str, float],
) -> bool:
    """
    Composite-only recovery criteria:
        S(UF) > 0.60 AND R(UF) > 0.20
    """

    if not safemode_state.safe_mode:
        return False

    if composite_metrics is None:
        return False

    S_val = composite_metrics.get("S_UF", None)
    R_val = composite_metrics.get("R_UF", None)

    if S_val is None or R_val is None:
        return False

    try:
        S_val = float(S_val)
        R_val = float(R_val)
    except (TypeError, ValueError):
        return False

    return (S_val > 0.60 and R_val > 0.20)


def exit_safemode(
    safemode_state: SafeModeState,
) -> SafeModeState:
    """
    Exit SafeMode with strict reset of SafeMode flags.

    Behavior:
        - safe_mode      → False
        - entry_step     → None
        - entry_reasons  → []
        - frozen_gates   → None
        - latest_metrics → preserved (for audit)
    """

    if not safemode_state.safe_mode:
        # Already not in SafeMode; return state unchanged
        return safemode_state

    return SafeModeState(
        safe_mode=False,
        entry_step=None,
        entry_reasons=[],
        frozen_gates=None,
        latest_metrics=dict(safemode_state.latest_metrics),
    )
