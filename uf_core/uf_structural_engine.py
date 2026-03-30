"""
uf_structural_engine.py
-----------------------------------------
UF-Core Structural Engine Adapter for TFE (v1.0)

Active runtime path:

    L0: uf_core.layer0.compute_sev_series   (field_col="Close")
    L1: uf_core.layer1.segment_gates
    L2: uf_core.layer2.interpret_gates
    L3: uf_core.layer3.compute_resonance
    L4: uf_core.layer4.compute_directional_signal, compute_dsf

Parked for lab-only evaluation:

    - hardening controller
    - safemode
    - gate unlock transient guard

Public UF engine:

    compute_uf_structural_state(close: pd.Series) -> UFStructuralState

TFE adapter (at bottom):

    compute_structural_state(symbol: str, bars: List[Bar]) -> Dict[str, Any]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from uf_core.layer0 import SEV, compute_sev_series
from uf_core.layer1 import Gate, segment_gates
from uf_core.layer2 import GateInterpretation, interpret_gates
from uf_core.layer3 import ResonanceResult, compute_resonance
from uf_core.layer4 import DSF, DecisionState, compute_directional_signal, compute_dsf

from tfe_market_data_service import Bar


PARKED_ADAPTER_CONTROLS: Dict[str, Dict[str, str | bool]] = {
    "hardening_control": {
        "active_runtime": False,
        "status": "parked_for_lab",
        "reason": "user directed adapter hardening rules to be ignored in active runtime",
    },
    "safemode": {
        "active_runtime": False,
        "status": "parked_for_lab",
        "reason": "user directed safemode path to be ignored in active runtime",
    },
    "gate_unlock_transient_guard": {
        "active_runtime": False,
        "status": "parked_for_lab",
        "reason": "held for later lab test only; not allowed to mutate active decision export",
    },
}


@dataclass
class UFStructuralState:
    """
    High-level UF structural summary for a single asset, as seen by TFE.

    NOTE:
      - All fields are derived from uf_core.*.
      - level5.D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k preserve last DSF values
      - level5.prev_C_k preserves the immediately preceding DSF conflict state
        for full L4 structural provenance.
      - level5.decision_vector now mirrors raw DSF directly.
      - prior adapter-only controls are parked and inactive.
    """

    level1: Dict[str, float]
    level2: Dict[str, float]
    level3: Dict[str, Any]
    level4: Dict[str, float]
    level5: Dict[str, Any]


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
    close = close.astype(float)
    n = len(close)
    if n < 3:
        return {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}

    x = np.arange(n)
    y = close.values

    slope, _intercept = np.polyfit(x, y, 1)

    trend_strength = float((slope / close.iloc[0]) * n) if close.iloc[0] != 0 else 0.0

    quad = np.polyfit(x, y, 2)
    y_quad = np.polyval(quad, x)
    curvature = float(np.mean(np.abs(y_quad - y)) / close.iloc[0]) if close.iloc[0] != 0 else 0.0

    return {
        "trend_strength": trend_strength,
        "curvature": curvature,
        "slope": float(slope),
    }


def _aggregate_gate_regime(interpretations: List[GateInterpretation]) -> str:
    if not interpretations:
        return "UNKNOWN"
    return interpretations[-1].regime


def _compute_stability_from_l4(
    results: List[ResonanceResult],
    decision_states: List[DecisionState],
) -> Dict[str, float]:
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

    hyst_flags = np.array([r.Hyst_k for r in results], dtype=float)
    r_vals = np.array([r.R_k for r in results], dtype=float)

    hyst_rate = float(np.mean(hyst_flags))
    r_mean = float(np.mean(r_vals))

    d_vals = np.array([ds.D_k for ds in decision_states], dtype=float)
    b_vals = np.array([ds.B_k for ds in decision_states], dtype=float)
    u_star_vals = np.array([ds.U_star_k for ds in decision_states], dtype=float)
    rev_flags = np.array([ds.R_rev_k for ds in decision_states], dtype=float)

    directional_stability = float(1.0 - np.mean(rev_flags))
    dsf_instability = float(np.mean((np.abs(d_vals) > 0).astype(float)))
    breathing_instability = float(np.mean((np.abs(b_vals) != 0).astype(float)))
    dsf_stability = float(1.0 - dsf_instability)

    uncertainty_rate = float(1.0 - np.mean(u_star_vals)) if len(u_star_vals) > 0 else 0.0

    return {
        "dsf": dsf_stability,
        "directional": directional_stability,
        "hysteresis_rate": hyst_rate,
        "breathing_rate": breathing_instability,
        "uncertainty_rate": uncertainty_rate,
        "gate_drift_rate": 0.0,
        "R_mean": r_mean,
    }


def _inactive_control_payload(name: str) -> Dict[str, Any]:
    item = PARKED_ADAPTER_CONTROLS[name]
    return {
        "active_runtime": bool(item["active_runtime"]),
        "status": str(item["status"]),
        "reason": str(item["reason"]),
    }


def _to_optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if not np.isfinite(parsed):
        return None
    return parsed


def _find_previous_valid_c_k(dsf_list: List[DSF]) -> float | None:
    if len(dsf_list) < 2:
        return None

    for dsf in reversed(dsf_list[:-1]):
        c_k = _to_optional_finite_float(getattr(dsf, "C_k", None))
        if c_k is not None:
            return c_k

    return None


def compute_uf_structural_state(close: pd.Series) -> UFStructuralState:
    """
    Main entrypoint: true UF-Core pipeline for a single asset.

    Active runtime behavior:
      - compute raw canonical UF/DSF outputs
      - export raw last-DSF values directly
      - do not apply adapter-only hardening or transient guards
    """

    close = close.dropna().astype(float)
    if len(close) < 10:
        level1 = {"n": float(len(close)), "vol": 0.0, "avg_return": 0.0, "price_range": 0.0}
        level2 = {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}
        level3 = {"regime": "INSUFFICIENT_DATA"}
        level4 = {"max_drawdown": 0.0, "stability_score": 0.0, "S_UF": 0.0, "R_UF": 0.0}
        level5 = {
            "decision_vector": [],
            "D_k": None,
            "M_k": None,
            "R_rev_k": None,
            "U_star_k": None,
            "C_k": None,
            "prev_C_k": None,
            "P_k": None,
            "B_k": None,
            "gate_count": 0,
            "active_gate_count": 0,
            "decision_guard": _inactive_control_payload("gate_unlock_transient_guard"),
            "hardening": _inactive_control_payload("hardening_control"),
            "safemode": _inactive_control_payload("safemode"),
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

    s_uf = float(max(0.0, min(1.0, 0.5 * stab["dsf"] + 0.5 * stab["directional"])))
    r_uf = float(max(0.0, min(1.0, stab["R_mean"])))

    raw_d_k: float | None = None
    raw_m_k: float | None = None
    raw_r_rev_k: float | None = None
    raw_u_star_k: float | None = None
    raw_c_k: float | None = None
    raw_prev_c_k: float | None = None
    raw_p_k: float | None = None
    raw_b_k: float | None = None

    if dsf_list:
        last_dsf = dsf_list[-1]
        raw_d_k = float(last_dsf.D_k)
        raw_m_k = float(last_dsf.M_k)
        raw_r_rev_k = float(last_dsf.R_rev_k)
        raw_u_star_k = float(last_dsf.U_star_k)
        raw_c_k = float(last_dsf.C_k)
        raw_prev_c_k = _find_previous_valid_c_k(dsf_list)
        raw_p_k = float(last_dsf.P_k)
        raw_b_k = float(last_dsf.B_k)
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
                0.5 * stab["dsf"] + 0.3 * stab["directional"] - 2.0 * abs(max_dd),
            ),
        )
    )

    level3 = {"regime": regime}
    level4 = {
        "max_drawdown": max_dd,
        "stability_score": stability_score,
        "S_UF": s_uf,
        "R_UF": r_uf,
    }

    level5 = {
        "decision_vector": decision_vector,
        "D_k": raw_d_k,
        "M_k": raw_m_k,
        "R_rev_k": raw_r_rev_k,
        "U_star_k": raw_u_star_k,
        "C_k": raw_c_k,
        "prev_C_k": raw_prev_c_k,
        "P_k": raw_p_k,
        "B_k": raw_b_k,
        "gate_count": int(len(gates)),
        "active_gate_count": int(sum(1 for r in resonance_results if int(r.g_k) == 1)),
        "decision_guard": _inactive_control_payload("gate_unlock_transient_guard"),
        "hardening": _inactive_control_payload("hardening_control"),
        "safemode": _inactive_control_payload("safemode"),
    }

    return UFStructuralState(
        level1=level1,
        level2=level2,
        level3=level3,
        level4=level4,
        level5=level5,
    )


def compute_structural_state(symbol: str, bars: List[Bar]) -> Dict[str, Any]:
    """
    Adapter used by TFE.

    - Converts Bar list to close-price series
    - Calls the UF-Core engine
    - Returns the flat shape TFE expects
    - Leaves parked controls inactive
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
        "D_k": uf_state.level5.get("D_k"),
        "M_k": uf_state.level5.get("M_k"),
        "R_rev_k": uf_state.level5.get("R_rev_k"),
        "U_star_k": uf_state.level5.get("U_star_k"),
        "C_k": uf_state.level5.get("C_k"),
        "prev_C_k": uf_state.level5.get("prev_C_k"),
        "P_k": uf_state.level5.get("P_k"),
        "B_k": uf_state.level5.get("B_k"),
        "gate_count": uf_state.level5.get("gate_count", 0),
        "active_gate_count": uf_state.level5.get("active_gate_count", 0),
        "decision_guard": uf_state.level5.get("decision_guard", {}),
        "hardening": uf_state.level5.get("hardening", {}),
        "safemode": uf_state.level5.get("safemode", {}),
    }
