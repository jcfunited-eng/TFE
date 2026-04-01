#!/usr/bin/env python3
"""CP-2: L5 canonical baseline filter — pure DSF V3 basin primitive.

Implements the same frozen basin math as runtime_decision_provenance.mjs.
Uses only columns verified to exist in the production live schema.

Two-layer filter
----------------
Layer 1 (V3 Structural Primitive — always active):
    - V3 basin argmax is tie-free Accumulate
    - price >= MIN_PRICE (5.0)
    - bar_count >= ACCUMULATE_MIN_BARS (verified via snapshot row, not re-checked
      here since uf_snapshot.json rows already passed the bar gate)

Layer 2 (CP-2 Cognitive Gate — SOFT: activates per-row only when F_n and
raw_x_m are non-null):
    - F_n     <= MAX_F_N    (1.65) — cognitive load not overextended
    - raw_x_m <= MAX_RAW_X_M (0.50) — memory state not overextended

Null-pass contract: if F_n or raw_x_m is NULL/NaN for a given row, that
row passes the cognitive gate unconditionally.  This ensures the "Healthy
Titans" set (~144 Accumulates) is fully recovered during the transition
period while the cognitive pipe (uf_mdg_snapshot.py) populates those fields
into the production snapshot.  Once the pipe completes a full refresh cycle,
the gate narrows automatically to the calibrated Titan subset.

Required columns (Layer 1):
    S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, price

Optional columns (Layer 2, null-safe):
    F_n, raw_x_m
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Frozen rational constants — must match runtime_decision_provenance.mjs exactly
# ---------------------------------------------------------------------------
_BETA: float = 37.0 / 64.0
_MOTION_WEIGHT: float = 3.0 / 5.0
_MOTION_POWER: float = 5.0 / 4.0
_REVERSAL_BALANCE_POWER: int = 16
_CARRY_BALANCE_POWER: int = 4
_BURDEN_SCALE: float = 1.0 / 128.0
_V3_TIE_EPS: float = 1e-12

MIN_PRICE: float = 5.0

# Layer 2 cognitive gate thresholds
# These are calibrated to the 64% Cognitive Physics operating point.
# Applied per-row only when F_n and raw_x_m are non-null.
MAX_F_N: float = 1.65
MAX_RAW_X_M: float = 0.50

# Layer 1 required columns
REQUIRED_COLUMNS: tuple[str, ...] = (
    "S_UF", "R_UF", "D_k", "M_k", "R_rev_k",
    "U_star_k", "C_k", "P_k", "B_k", "price",
)

# Layer 2 optional cognitive columns
COGNITIVE_COLUMNS: tuple[str, ...] = ("F_n", "raw_x_m")


@dataclass(frozen=True)
class L5BaselineFilter:
    min_price: float = MIN_PRICE
    max_f_n: float = MAX_F_N
    max_raw_x_m: float = MAX_RAW_X_M

    def apply_canonical_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        # ------------------------------------------------------------------
        # Guard: Layer 1 required columns must be present
        # ------------------------------------------------------------------
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Float64 working copy — avoids object-dtype arithmetic surprises
        s = df.reindex(columns=list(REQUIRED_COLUMNS)).astype(float)

        # ------------------------------------------------------------------
        # Layer 1: V3 Basin Argmax
        # ------------------------------------------------------------------
        M_hat = s["M_k"].clip(-1.0, 1.0)

        sv    = s["S_UF"] - s["U_star_k"]
        rv    = s["R_UF"] - s["U_star_k"]
        s_pos = sv.clip(lower=0.0)
        r_pos = rv.clip(lower=0.0)
        core  = np.minimum(s_pos, r_pos)
        edge  = np.maximum(s_pos, r_pos) - core
        live      = core + _BETA * edge
        contested = (1.0 - _BETA) * edge
        balance   = core / (core + edge + 1e-12)
        rupture   = (-np.maximum(sv, rv)).clip(lower=0.0)

        D_nonadverse = (1.0 + s["D_k"]) / 2.0
        D_adverse    = (-s["D_k"]).clip(lower=0.0)
        M_continue   = (1.0 + M_hat) / 2.0
        M_bend       = (1.0 - M_hat) / 2.0

        motion = (
            _MOTION_WEIGHT * D_nonadverse ** _MOTION_POWER
            + (1.0 - _MOTION_WEIGHT) * M_continue ** _MOTION_POWER
        ) ** (1.0 / _MOTION_POWER)

        adverse_break   = D_adverse * M_bend
        reversal_break  = s["R_rev_k"] * (1.0 - balance) ** _REVERSAL_BALANCE_POWER
        carry_break     = (
            (-s["B_k"]) * s["R_rev_k"]
            * (1.0 - balance) ** _CARRY_BALANCE_POWER
            * (1.0 - adverse_break)
        )
        burden          = _BURDEN_SCALE * (s["C_k"] / (1.0 + s["C_k"])) * (s["P_k"] / (1.0 + s["P_k"]))
        break_agreement = np.maximum(np.maximum(adverse_break, reversal_break), carry_break)

        accumulate_basin = (
            live * motion * (1.0 - s["R_rev_k"]) * (1.0 - adverse_break) * (1.0 - burden)
        )
        hold_basin = (
            contested * (1.0 - break_agreement)
            + live * s["R_rev_k"] * balance
            + live * (1.0 - s["R_rev_k"]) * ((1.0 - motion) * (1.0 - adverse_break) + motion * burden)
        )
        avoid_basin = rupture + (live + contested) * break_agreement

        max_basin = np.maximum(np.maximum(accumulate_basin, hold_basin), avoid_basin)

        near_acc  = (max_basin - accumulate_basin).abs() <= _V3_TIE_EPS
        near_hold = (max_basin - hold_basin).abs() <= _V3_TIE_EPS
        near_avd  = (max_basin - avoid_basin).abs() <= _V3_TIE_EPS
        tie       = (near_acc.astype(int) + near_hold.astype(int) + near_avd.astype(int)) > 1

        is_accumulate = near_acc & ~tie
        price_ok      = s["price"] >= self.min_price

        layer1_mask = is_accumulate & price_ok

        # ------------------------------------------------------------------
        # Layer 2: Cognitive Gate (soft — null-pass per row)
        # Applied only when BOTH F_n and raw_x_m columns exist in the frame.
        # ------------------------------------------------------------------
        fn_present  = "F_n"    in df.columns
        rxm_present = "raw_x_m" in df.columns

        if fn_present and rxm_present:
            fn_series  = pd.to_numeric(df["F_n"],    errors="coerce")
            rxm_series = pd.to_numeric(df["raw_x_m"], errors="coerce")

            both_populated = fn_series.notna() & rxm_series.notna()

            # Null-pass contract: rows where either field is null are not disqualified
            cognitive_ok = (
                ~both_populated
                | (
                    (fn_series  <= self.max_f_n)
                    & (rxm_series <= self.max_raw_x_m)
                )
            )
            cognitive_ok = cognitive_ok.reindex(df.index).fillna(True)
        else:
            # Cognitive columns absent — pass all rows (pre-pipe state)
            cognitive_ok = pd.Series(True, index=df.index)

        final_mask = layer1_mask & cognitive_ok

        return df.loc[final_mask].copy()


def apply_canonical_filter(df: pd.DataFrame) -> pd.DataFrame:
    return L5BaselineFilter().apply_canonical_filter(df)
