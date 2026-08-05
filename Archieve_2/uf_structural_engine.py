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

AND IT APPLIES STRUCTURAL-DOMAIN THRESHOLDING:

    - Per-symbol structural profile from the *raw* scalar field
      (volatility, price_range, etc.)
    - Bounded scaling of:
        τ_D       (gate deviation threshold)
        ε_D       (directional-signal threshold)
        U_max     (uncertainty gating threshold)

    - Scaling is:
        * static per symbol (no online drift),
        * bounded (no runaway multipliers),
        * invariant-preserving (no sign flips, no redefinition of metrics).

Public API exposed to TFE:

    compute_uf_structural_state(close: pd.Series) -> UFStructuralState

UFStructuralState is a high-level view suitable for Advisor/Recommendations,
but all structural information is derived from TRUE UF-Core pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd

import uf_core.config as uf_config
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


# ============================================================
# UF Structural State for TFE
# ============================================================

@dataclass
class UFStructuralState:
    """
    High-level UF structural summary for a single asset, as seen by TFE.

    NOTE:
      - All fields are derived from uf_core.*.
      - level5.decision_vector is taken directly from the final DSF_k.
    """

    level1: Dict[str, float]
    level2: Dict[str, float]
    level3: Dict[str, Any]
    level4: Dict[str, float]
    level5: Dict[str, Any]


# ============================================================
# Helper functions (generic structural math)
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
    Basic structural features from the scalar field F(t).

    These are *not* TA indicators; they are scale-aware aggregate descriptors:
        - n           : number of points
        - vol         : annualized volatility of log-returns
        - avg_return  : annualized mean return
        - price_range : (max - min) / min  (dimensionless)
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
    L2-style aggregate of trend and curvature from the scalar field F(t).

    This is a coarse structural view of:
        - trend_strength : normalized linear slope over the window
        - curvature      : mean |quad_fit - actual| normalized by initial price
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
    Aggregate L2 regimes across gates; bias to the LAST gate (most recent state).
    """
    if not interpretations:
        return "UNKNOWN"
    return interpretations[-1].regime


def _compute_stability_from_l4(
    results: List[ResonanceResult],
    decision_states: List[DecisionState],
) -> Dict[str, float]:
    """
    Derive stability-like metrics from L3/L4 outputs to feed:

        - Hardening controller
        - TFE-facing stability metrics
        - Composite S_UF / R_UF

    These are grounded in UF-Core data; threshold calibration belongs
    in the UF Validation Suite.
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
        "gate_drift_rate": 0.0,   # true drift requires cross-run tracking
        "R_mean": R_mean,
    }


# ============================================================
# Structural-Domain Thresholding (Option A)
# ============================================================

def _compute_domain_profile(close: pd.Series) -> Dict[str, float]:
    """
    Domain profile P(domain) computed *before* UF-Core L0.

    This is intentionally simple and relies only on F(t), not on any
    UF internals:

        - n           : length
        - vol         : annualized vol of log-returns
        - price_range : (max - min) / min
    """
    profile = _compute_basic_features(close)
    return profile


def _compute_threshold_scaling(profile: Dict[str, float]) -> Dict[str, float]:
    """
    Map domain profile → bounded scaling factors for kernel thresholds.

    We enforce:

        - factor_tau_D ∈ [0.5, 2.0]
        - factor_eps_D ∈ [0.5, 2.0]
        - delta_U_max  ∈ [0.0, 0.15]

    Heuristics (structural, not financial):

        - Low-vol, low-range domains:
            * gates can be more sensitive (lower τ_D)
        - High-vol OR high-range domains:
            * gates should be less trigger-happy (higher τ_D, ε_D)
            * U_max relaxed slightly so URF is not zeroed out.
    """
    vol = float(profile.get("vol", 0.0))
    pr = float(profile.get("price_range", 0.0))

    # Base factors
    factor_tau = 1.0
    factor_eps = 1.0
    delta_U = 0.0

    # Low-vol / tight-range: increase sensitivity (smaller τ_D)
    if vol < 0.20 and pr < 0.30:
        factor_tau = 0.75
        factor_eps = 0.75

    # High-vol or wide-range: reduce sensitivity (larger thresholds)
    if vol > 0.60 or pr > 1.00:
        factor_tau = 1.50
        factor_eps = 1.50
        delta_U = 0.10

    # Clamp
    factor_tau = float(max(0.5, min(2.0, factor_tau)))
    factor_eps = float(max(0.5, min(2.0, factor_eps)))
    delta_U = float(max(0.0, min(0.15, delta_U)))

    return {
        "factor_tau_D": factor_tau,
        "factor_epsilon_D": factor_eps,
        "delta_U_max": delta_U,
    }


def _apply_threshold_scaling(
    scaling: Dict[str, float],
) -> Tuple[uf_config.KernelThresholds, uf_config.KernelThresholds]:
    """
    Given scaling factors, construct a *new* KernelThresholds instance.

    We do NOT mutate fields in-place; we compute a new struct and return:
        (orig_thresholds, new_thresholds)

    The caller is responsible for:

        - assigning uf_config.KERNEL_THRESHOLDS = new_thresholds
        - restoring uf_config.KERNEL_THRESHOLDS = orig_thresholds
    """
    orig = uf_config.KERNEL_THRESHOLDS

    tau = orig.tau_D
    eps = orig.epsilon_D
    U_max = orig.U_max

    f_tau = scaling["factor_tau_D"]
    f_eps = scaling["factor_epsilon_D"]
    d_U = scaling["delta_U_max"]

    new_tau = float(tau * f_tau)
    new_eps = float(eps * f_eps)
    new_U = float(max(0.0, min(0.99, U_max + d_U)))  # hard cap at 0.99

    new_thresholds = uf_config.KernelThresholds(
        tau_D=new_tau,
        sigma_min=orig.sigma_min,
        delta_min=orig.delta_min,
        kappa_min=orig.kappa_min,
        variance_window=orig.variance_window,
        epsilon_D=new_eps,
        U_max=new_U,
    )

    return orig, new_thresholds


# ============================================================
# CORE PUBLIC API
# ============================================================

def compute_uf_structural_state(close: pd.Series) -> UFStructuralState:
    """
    MAIN ENTRYPOINT: true UF-Core pipeline for a single asset with
    structural-domain thresholding (Option A).

    Steps:
      0) Domain profile P(domain) from raw scalar field.
      1) Compute bounded scaling for UF kernel thresholds.
      2) Temporarily apply scaled thresholds (per symbol).
      3) Run L0 → L1 → L2 → L3 → L4 (uf_core.*).
      4) Aggregate gates, interpretations, resonance, and DSF.
      5) Compute stability metrics + composite S_UF / R_UF.
      6) Run hardening controller (SafeMode + HA).
      7) Build UFStructuralState for TFE layers to consume.

    NOTE:
      - Threshold scaling is:
            static per symbol,
            bounded,
            invariant-preserving.
      - This function does NOT make buy/sell decisions.
      - It exposes structure for uf_decision_surface and TFE pages.
    """

    close = close.dropna().astype(float)
    if len(close) < 10:
        # Degenerate state
        level1 = {"n": float(len(close)), "vol": 0.0, "avg_return": 0.0, "price_range": 0.0}
        level2 = {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}
        level3 = {"regime": "INSUFFICIENT_DATA"}
        level4 = {"max_drawdown": 0.0, "stability_score": 0.0, "S_UF": 0.0, "R_UF": 0.0}
        level5 = {
            "decision_vector": [],
            "dsf_list": [],
            "hardening": {},
            "safemode": {},
        }
        return UFStructuralState(level1, level2, level3, level4, level5)

    # --------------------------------------------------------
    # 0) Domain profile + threshold scaling (per symbol)
    # --------------------------------------------------------

    domain_profile = _compute_domain_profile(close)
    scaling = _compute_threshold_scaling(domain_profile)
    orig_thresholds, new_thresholds = _apply_threshold_scaling(scaling)

    # --------------------------------------------------------
    # 1) Build DF once
    # --------------------------------------------------------
    df = pd.DataFrame({"Close": close})
    df.index = close.index

    # We will restore thresholds no matter what.
    try:
        # ----------------------------------------------------
        # 2) Apply scaled thresholds for this symbol
        # ----------------------------------------------------
        uf_config.KERNEL_THRESHOLDS = new_thresholds

        # ----------------------------------------------------
        # 3) L0 → L1 → L2 → L3 → L4
        # ----------------------------------------------------

        # L0: SEV series (uses uf_config.KERNEL_THRESHOLDS internally)
        sev_list: List[SEV] = compute_sev_series(df, field_col="Close")

        # L1: Gate segmentation
        gates: List[Gate] = segment_gates(sev_list)

        # L2: Interpret gates
        interpretations: List[GateInterpretation] = interpret_gates(sev_list, gates)

        # L3: Resonance
        resonance_results: List[ResonanceResult] = compute_resonance(interpretations)

        # L4: Directional signal & DSF
        decision_states: List[DecisionState] = compute_directional_signal(resonance_results)
        dsf_list: List[DSF] = compute_dsf(decision_states)

    finally:
        # Always restore original thresholds to avoid cross-symbol contamination
        uf_config.KERNEL_THRESHOLDS = orig_thresholds

    # --------------------------------------------------------
    # 4) Aggregate regimes & stability metrics
    # --------------------------------------------------------

    regime = _aggregate_gate_regime(interpretations)

    # level1: we already have profile from _compute_basic_features()
    level1 = domain_profile
    level2 = _compute_trend_curvature(close)

    returns = _safe_pct_change(close)
    max_dd = _max_drawdown(returns)

    stab = _compute_stability_from_l4(resonance_results, decision_states)

    # Composite UF metrics S_UF, R_UF (simplified proxies)
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

    # --------------------------------------------------------
    # 5) Hardening + SafeMode (strict controller)
    # --------------------------------------------------------

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

    # Last DSF represents most recent structural decision surface
    if final_dsf_list:
        last_dsf = final_dsf_list[-1]
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

    # Stability score for TFE: include drawdown penalty
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

    # --------------------------------------------------------
    # 6) Build output state
    # --------------------------------------------------------

    level3 = {"regime": regime}
    level4 = {
        "max_drawdown": max_dd,
        "stability_score": stability_score,
        "S_UF": S_UF,
        "R_UF": R_UF,
    }

    level5 = {
        "decision_vector": decision_vector,
        "dsf_list": [
            {
                "gate": {
                    "start_idx": dsf.gate.start_idx,
                    "end_idx": dsf.gate.end_idx,
                },
                "D_k": dsf.D_k,
                "M_k": dsf.M_k,
                "R_rev_k": dsf.R_rev_k,
                "U_star_k": dsf.U_star_k,
                "P_k": dsf.P_k,
                "B_k": dsf.B_k,
            }
            for dsf in final_dsf_list
        ],
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
