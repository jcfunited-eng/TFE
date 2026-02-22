"""
uf_structural_engine.py
-----------------------------------------
UF-Core Structural Engine Adapter for TFE (v1.0)

THIS MODULE USES THE REAL UF-CORE PIPELINE:

    L0: uf_core.layer0.compute_sev_series   (field_col="Close")
    L1: uf_core.layer1.segment_gates
    L2: uf_core.layer2.interpret_gates
    L3: uf_core.layer3.compute_resonance
    L4: uf_core.layer4.compute_directional_signal, compute_dsf
    Hardening: uf_core.hardening_controller.hardening_control_step
    SafeMode: uf_core.safemode

Public UF engine:

    compute_uf_structural_state(close: pd.Series) -> UFStructuralState

TFE adapter (at bottom):

    compute_structural_state(symbol: str, bars: List[Bar]) -> Dict[str, Any]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List

import numpy as np
import pandas as pd

from uf_core.layer0 import compute_sev_series, SEV
from uf_core.layer1 import segment_gates, Gate
from uf_core.layer2 import interpret_gates, GateInterpretation
from uf_core.layer3 import compute_resonance, ResonanceResult
from uf_core.layer4 import (
    compute_directional_signal,
    compute_dsf,
    DecisionState,
    DSF,
)
from uf_core.hardening_controller import hardening_control_step
from uf_core.safemode import init_safemode_state

from tfe_market_data_service import Bar


# ============================================================
# UF Structural State for TFE
# ============================================================

@dataclass
class UFStructuralState:
    """
    High-level UF structural summary for a single asset, as seen by TFE.

    NOTE:
      - All fields are derived from uf_core.*.
      - Level5.decision_vector is taken directly from the final DSF_k,
        except for deterministic structural guardrails.
    """

    level1: Dict[str, float]
    level2: Dict[str, float]
    level3: Dict[str, Any]
    level4: Dict[str, float]
    level5: Dict[str, Any]


# ============================================================
# Helper functions
# ============================================================

def _safe_pct_change(series: pd.Series) -> pd.Series:
    return series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())


def _compute_basic_features(close: pd.Series) -> Dict[str, float]:
    """
    Basic structural features from the raw scalar field (for TFE readability).
    These are *not* TA indicators; they are scale-aware aggregate descriptors.
    """
    close = close.astype(float)
    returns = _safe_pct_change(close)
    vol = float(returns.std() * np.sqrt(252)) if len(returns) > 0 else 0.0
    avg_ret = float(returns.mean() * 252) if len(returns) > 0 else 0.0
    price_range = float((close.max() - close.min()) / close.min()) if close.min() > 0 else 0.0
    return {
        "n": float(len(close)),
        "vol": vol,
        "avg_return": avg_ret,
        "price_range": price_range,
    }


def _compute_trend_curvature(close: pd.Series) -> Dict[str, float]:
    """
    L2-style aggregate of trend and curvature from the raw scalar field.
    """
    close = close.astype(float)
    n = len(close)
    if n < 3:
        return {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}

    x = np.arange(n)
    y = close.values

    # Linear trend
    slope, intercept = np.polyfit(x, y, 1)
    trend_strength = float((slope / close.iloc[0]) * n) if close.iloc[0] != 0 else 0.0

    # Quadratic curvature
    quad = np.polyfit(x, y, 2)
    y_quad = np.polyval(quad, x)
    curvature = float(np.mean(np.abs(y_quad - y)) / close.iloc[0]) if close.iloc[0] != 0 else 0.0

    return {
        "trend_strength": trend_strength,
        "curvature": curvature,
        "slope": float(slope),
    }


def _aggregate_gate_regime(interpretations: List[GateInterpretation]) -> str:
    """
    Aggregate L2 regimes across gates; we bias towards the last gate
    (most recent structural state).
    """
    if not interpretations:
        return "UNKNOWN"
    return interpretations[-1].regime


def _compute_stability_from_l4(
    results: List[ResonanceResult],
    decision_states: List[DecisionState],
) -> Dict[str, float]:
    """
    Derive stability-like metrics from L3/L4 outputs to feed into the
    hardening framework and TFE-level stability view.

    These are grounded in UF-Core data; threshold calibration lives in UF validation.
    """
    if not results or not decision_states:
        return {
            "dsf": 1.0,
            "directional": 1.0,
            "hysteresis_rate": 0.0,
            "breathing_rate": 0.0,
            "uncertainty_rate": 0.0,
            "gate_drift_rate": 0.0,
            "R_mean": 0.0,
        }

    # L3 hysteresis & resonance
    hyst_flags = np.array([r.Hyst_k for r in results], dtype=float)
    R_vals = np.array([r.R_k for r in results], dtype=float)

    hyst_rate = float(np.mean(hyst_flags))
    R_mean = float(np.mean(R_vals))

    # L4 directional characteristics
    D_vals = np.array([ds.D_k for ds in decision_states], dtype=float)
    B_vals = np.array([ds.B_k for ds in decision_states], dtype=float)
    U_star_vals = np.array([ds.U_star_k for ds in decision_states], dtype=float)
    rev_flags = np.array([ds.R_rev_k for ds in decision_states], dtype=float)

    directional_stability = float(1.0 - np.mean(rev_flags))
    dsf_instability = float(np.mean((np.abs(D_vals) > 0).astype(float)))
    breathing_instability = float(np.mean((np.abs(B_vals) != 0).astype(float)))
    dsf_stability = float(1.0 - dsf_instability)

    uncertainty_rate = float(1.0 - np.mean(U_star_vals)) if len(U_star_vals) > 0 else 0.0

    return {
        "dsf": dsf_stability,
        "directional": directional_stability,
        "hysteresis_rate": hyst_rate,
        "breathing_rate": breathing_instability,
        "uncertainty_rate": uncertainty_rate,
        "gate_drift_rate": 0.0,
        "R_mean": R_mean,
    }


def _gate_unlock_transient_meta(results: List[ResonanceResult]) -> Dict[str, Any]:
    """
    Detect one-step gate-unlock transients at the current edge.

    Structural condition:
    - at least two resonance points
    - previous gate is fully gated out (g=0, URF=0)
    - current gate is active (g=1, URF>0)

    This pattern can emit a positive/negative D from a pure activation jump,
    not from persistent directional field evolution. We neutralize direction for
    the latest decision vector in this specific case.
    """

    meta: Dict[str, Any] = {
        "active": False,
        "prev_g": 0,
        "curr_g": 0,
        "prev_urf": 0.0,
        "curr_urf": 0.0,
    }

    if len(results) < 2:
        return meta

    prev_res = results[-2]
    curr_res = results[-1]

    prev_g = int(prev_res.g_k)
    curr_g = int(curr_res.g_k)
    prev_urf = float(prev_res.URF_k)
    curr_urf = float(curr_res.URF_k)

    is_unlock = (prev_g == 0) and (curr_g == 1) and (prev_urf <= 0.0) and (curr_urf > 0.0)

    meta["active"] = bool(is_unlock)
    meta["prev_g"] = prev_g
    meta["curr_g"] = curr_g
    meta["prev_urf"] = prev_urf
    meta["curr_urf"] = curr_urf
    return meta


# ============================================================
# CORE PUBLIC API (YOUR ORIGINAL ENGINE)
# ============================================================

def compute_uf_structural_state(close: pd.Series) -> UFStructuralState:
    """
    MAIN ENTRYPOINT: true UF-Core pipeline for a single asset.
    """

    close = close.dropna().astype(float)
    if len(close) < 10:
        level1 = {"n": float(len(close)), "vol": 0.0, "avg_return": 0.0, "price_range": 0.0}
        level2 = {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}
        level3 = {"regime": "INSUFFICIENT_DATA"}
        level4 = {"max_drawdown": 0.0, "stability_score": 0.0, "S_UF": 0.0, "R_UF": 0.0}
        level5 = {
            "decision_vector": [],
            "gate_count": 0,
            "active_gate_count": 0,
            "decision_guard": {"gate_unlock_transient_neutralized": False},
            "dsf_list": [],
            "hardening": {},
            "safemode": {},
        }
        return UFStructuralState(level1, level2, level3, level4, level5)

    df = pd.DataFrame({"Close": close})
    df.index = close.index

    sev_list: List[SEV] = compute_sev_series(df, field_col="Close")
    gates: List[Gate] = segment_gates(sev_list)
    interpretations: List[GateInterpretation] = interpret_gates(sev_list, gates)
    resonance_results: List[ResonanceResult] = compute_resonance(interpretations)
    decision_states: List[DecisionState] = compute_directional_signal(resonance_results)
    dsf_list: List[DSF] = compute_dsf(decision_states)

    regime = _aggregate_gate_regime(interpretations)
    level1 = _compute_basic_features(close)
    level2 = _compute_trend_curvature(close)

    returns = _safe_pct_change(close)
    max_dd = _max_drawdown(returns)

    stab = _compute_stability_from_l4(resonance_results, decision_states)

    S_UF = float(max(0.0, min(1.0, 0.5 * stab["dsf"] + 0.5 * stab["directional"])))
    R_UF = float(max(0.0, min(1.0, stab["R_mean"])))

    composite_metrics = {"S_UF": S_UF, "R_UF": R_UF}
    stability_scores = {
        "dsf": stab["dsf"],
        "directional": stab["directional"],
        "hysteresis_rate": stab["hysteresis_rate"],
        "breathing_rate": stab["breathing_rate"],
        "uncertainty_rate": stab["uncertainty_rate"],
        "gate_drift_rate": stab["gate_drift_rate"],
    }
    sensitivity_data: List[Dict[str, float]] = []

    safemode_state = init_safemode_state()

    dsf_after, gates_after, safemode_state, htc_result = hardening_control_step(
        current_step=0,
        dsf_list=dsf_list,
        gates=gates,
        composite_metrics=composite_metrics,
        stability_scores=stability_scores,
        sensitivity_data=sensitivity_data,
        safemode_state=safemode_state,
    )

    final_dsf_list = dsf_after
    gate_count = int(len(gates))
    active_gate_count = int(sum(1 for r in resonance_results if int(r.g_k) == 1))

    unlock_meta = _gate_unlock_transient_meta(resonance_results)
    unlock_guard_active = bool(unlock_meta.get("active", False))

    if final_dsf_list:
        last_dsf = final_dsf_list[-1]
        if unlock_guard_active:
            # Neutralize direction for one-step gate-unlock transient at edge.
            decision_vector = [
                0.0,
                0.0,
                0.0,
                float(last_dsf.U_star_k),
                0.0,
                float(last_dsf.B_k),
            ]
        else:
            decision_vector = [
                float(last_dsf.D_k),
                float(last_dsf.M_k),
                float(last_dsf.R_rev_k),
                float(last_dsf.U_star_k),
                float(last_dsf.P_k),
                float(last_dsf.B_k),
            ]
    else:
        decision_vector = []

    stability_score = float(
        max(
            0.0,
            min(
                1.0,
                0.5 * stab["dsf"]
                + 0.3 * stab["directional"]
                - 2.0 * abs(max_dd),
            ),
        )
    )

    level3 = {"regime": regime}
    level4 = {
        "max_drawdown": max_dd,
        "stability_score": stability_score,
        "S_UF": S_UF,
        "R_UF": R_UF,
    }

    level5 = {
        "decision_vector": decision_vector,
        "gate_count": gate_count,
        "active_gate_count": active_gate_count,
        "decision_guard": {
            "gate_unlock_transient_neutralized": unlock_guard_active,
            "prev_g": int(unlock_meta.get("prev_g", 0)),
            "curr_g": int(unlock_meta.get("curr_g", 0)),
            "prev_urf": float(unlock_meta.get("prev_urf", 0.0)),
            "curr_urf": float(unlock_meta.get("curr_urf", 0.0)),
        },
        "dsf_list": [],
        "hardening": {
            "flags": vars(htc_result.flags),
            "raw_metrics": htc_result.raw_metrics,
            "notes": htc_result.notes,
        },
        "safemode": {
            "safe_mode": safemode_state.safe_mode,
            "entry_step": safemode_state.entry_step,
            "entry_reasons": safemode_state.entry_reasons,
        },
    }

    return UFStructuralState(
        level1=level1,
        level2=level2,
        level3=level3,
        level4=level4,
        level5=level5,
    )


# ============================================================
# TFE ADAPTER
# ============================================================

def compute_structural_state(symbol: str, bars: List[Bar]) -> Dict[str, Any]:
    """
    Adapter used by TFE (rebuild_uf_snapshot, Watchlist, etc.).

    - Converts Bar list → close price Series
    - Calls the true UF-Core engine: compute_uf_structural_state
    - Returns a flat dict with fields TFE expects.
    """
    close = pd.Series(
        [b.close for b in bars],
        index=[b.timestamp for b in bars],
    ).sort_index()

    uf_state = compute_uf_structural_state(close)

    return {
        "symbol": symbol,
        "last_close": float(close.iloc[-1]),
        "regime": uf_state.level3.get("regime"),
        "S_UF": uf_state.level4.get("S_UF"),
        "R_UF": uf_state.level4.get("R_UF"),
        "stability_score": uf_state.level4.get("stability_score"),
        "max_drawdown": uf_state.level4.get("max_drawdown"),
        "decision_vector": uf_state.level5.get("decision_vector", []),
        "gate_count": uf_state.level5.get("gate_count", 0),
        "active_gate_count": uf_state.level5.get("active_gate_count", 0),
        "decision_guard": uf_state.level5.get("decision_guard", {}),
    }
