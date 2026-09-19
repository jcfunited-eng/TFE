"""Verbatim Python port of web/scripts/execution/v3_basin.mjs (computeV3Basin).

The live entry gate's coupled math, transcribed constant for constant so a
historical measurement asks the SAME question the live door asks. Verified
against the JavaScript module on real tuples by
tools/ch2_v3_basin_port_check.py — exact match required, no tolerance beyond
floating-point identity. Do not "improve" the formulas here: this file exists
only to mirror the frozen module.
"""
from __future__ import annotations

import math
from typing import Any

BETA = 37 / 64
CONTESTED_WEIGHT = 27 / 64
MOTION_WEIGHT = 3 / 5
MOTION_POWER = 5 / 4
REVERSAL_BALANCE_POWER = 16
CARRY_BALANCE_POWER = 4
BURDEN_SCALE = 1 / 128
V3_TIE_EPS = 1e-12

REQUIRED = ("S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k")


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_v3_basin(tuple_: dict[str, Any]) -> dict[str, Any] | None:
    for f in REQUIRED:
        v = tuple_.get(f)
        if v is None:
            return None
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(fv):
            return None

    S_UF = float(tuple_["S_UF"]); R_UF = float(tuple_["R_UF"]); D_k = float(tuple_["D_k"])
    M_k = float(tuple_["M_k"]); R_rev_k = float(tuple_["R_rev_k"]); U_star_k = float(tuple_["U_star_k"])
    C_k = float(tuple_["C_k"]); P_k = float(tuple_["P_k"]); B_k = float(tuple_["B_k"])

    M_hat = _clamp(M_k, -1, 1)

    s = S_UF - U_star_k
    r = R_UF - U_star_k
    s_pos = max(s, 0)
    r_pos = max(r, 0)

    core = min(s_pos, r_pos)
    edge = max(s_pos, r_pos) - core
    live = core + BETA * edge
    contested = CONTESTED_WEIGHT * edge
    balance = core / (core + edge + 1e-12)
    rupture = max(0, -max(s, r))

    D_nonadverse = (1 + D_k) / 2
    D_adverse = max(0, -D_k)
    M_continue = (1 + M_hat) / 2
    M_bend = (1 - M_hat) / 2

    motion = math.pow(
        MOTION_WEIGHT * math.pow(D_nonadverse, MOTION_POWER)
        + (1 - MOTION_WEIGHT) * math.pow(M_continue, MOTION_POWER),
        1 / MOTION_POWER,
    )

    adverse_break = D_adverse * M_bend
    reversal_break = R_rev_k * math.pow(1 - balance, REVERSAL_BALANCE_POWER)
    carry_break = (-B_k) * R_rev_k * math.pow(1 - balance, CARRY_BALANCE_POWER) * (1 - adverse_break)
    burden = BURDEN_SCALE * (C_k / (1 + C_k)) * (P_k / (1 + P_k))
    break_agreement = max(adverse_break, reversal_break, carry_break)

    accumulate_basin = live * motion * (1 - R_rev_k) * (1 - adverse_break) * (1 - burden)
    hold_basin = (
        contested * (1 - break_agreement)
        + live * R_rev_k * balance
        + live * (1 - R_rev_k) * ((1 - motion) * (1 - adverse_break) + motion * burden)
    )
    avoid_basin = rupture + (live + contested) * break_agreement

    max_b = max(accumulate_basin, hold_basin, avoid_basin)
    near_acc = abs(max_b - accumulate_basin) <= V3_TIE_EPS
    near_hold = abs(max_b - hold_basin) <= V3_TIE_EPS
    near_avd = abs(max_b - avoid_basin) <= V3_TIE_EPS
    n_near = int(near_acc) + int(near_hold) + int(near_avd)
    if n_near > 1:
        decision_argmax = "Tie"
    elif near_acc:
        decision_argmax = "Accumulate"
    elif near_hold:
        decision_argmax = "Hold"
    else:
        decision_argmax = "Avoid"

    return {
        "s": s, "r": r, "core": core, "edge": edge, "live": live,
        "contested": contested, "balance": balance, "rupture": rupture,
        "D_nonadverse": D_nonadverse, "D_adverse": D_adverse,
        "M_continue": M_continue, "M_bend": M_bend, "motion": motion,
        "adverse_break": adverse_break, "reversal_break": reversal_break,
        "carry_break": carry_break, "burden": burden,
        "break_agreement": break_agreement,
        "accumulate_basin": accumulate_basin, "hold_basin": hold_basin,
        "avoid_basin": avoid_basin, "decision_argmax": decision_argmax,
    }
