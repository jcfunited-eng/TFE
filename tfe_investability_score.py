#!/usr/bin/env python3
"""
TFE Investability Score — per TFE Specification v3.0, Section 16.

Combines structural state, fundamentals, and epoch pressure into one
governed investability quantity per stock per horizon.

IS_h(s,t) = α·Q_h - β·F_n + γ·Q_fund - δ·Δ_spec + η·Ω_epoch + ζ·Ω_strat

Current implementation (CP-2 profile):
  - Q_h from S_UF (structural conviction proxy)
  - F_n from U_star_k (residual uncertainty)
  - Q_fund from l5_fundamentals_normalized (if available)
  - Δ_spec from price/bar_count heuristics (thin stocks get penalty)
  - Ω_epoch from G32 sector pressure
  - Ω_strat = 0 (strategy classes not yet implemented)

No ML. Deterministic. Governed constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# ═════════════════════════════════════════════════════════════════════════
# Investability Score Weights — governed constants
#
# These are NOT fitted. They reflect the relative importance of each
# component in the investment decision. The spec requires them to be
# fixed at deployment and revisited only through controlled change.
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ISWeights:
    """Investability score weight tuple Θ for a given profile."""
    alpha: float = 1.0    # structural action score weight
    beta:  float = 0.5    # free energy penalty weight
    gamma: float = 0.3    # fundamental quality weight
    delta: float = 0.2    # speculative penalty weight
    eta:   float = 0.4    # epoch pressure weight
    zeta:  float = 0.0    # strategy class weight (not yet active)


# Default weights — single horizon, no strategy class
DEFAULT_WEIGHTS = ISWeights()


# ═════════════════════════════════════════════════════════════════════════
# Component Scoring Functions
# ═════════════════════════════════════════════════════════════════════════

def compute_structural_score(s_uf: float, d_k: float, r_rev_k: float) -> float:
    """Q_h: Structural action score.

    Combines S_UF (conviction) with D_k (direction) and R_rev (reversal).
    Range: [0, 1]. Higher = stronger structural case for accumulation.
    """
    if s_uf is None or d_k is None:
        return 0.0

    # Base: S_UF is the structural conviction
    base = max(0.0, min(1.0, float(s_uf)))

    # Direction multiplier: D_k = +1 → full, D_k = 0 → half, D_k = -1 → zero
    direction = max(0.0, (float(d_k) + 1.0) / 2.0)

    # Reversal penalty: R_rev active → halve the score
    reversal_mult = 0.5 if (r_rev_k is not None and float(r_rev_k) > 0) else 1.0

    return base * direction * reversal_mult


def compute_free_energy(u_star_k: float, stability_score: float) -> float:
    """F_n: Free structural energy (uncertainty/instability).

    High uncertainty = high free energy = penalty.
    Range: [0, 1]. Higher = more uncertain = worse.
    """
    if u_star_k is None:
        return 0.5  # unknown → moderate penalty

    u = max(0.0, min(1.0, float(u_star_k)))

    # Stability reduces free energy, uncertainty increases it
    stab = max(0.0, min(1.0, float(stability_score or 0.0)))
    return u * (1.0 - 0.5 * stab)


def compute_fundamental_score(
    gross_margin: Optional[float],
    current_ratio: Optional[float],
    free_cash_flow: Optional[float],
    revenues: Optional[float],
) -> float:
    """Q_fund: Fundamental quality score.

    Deterministic scoring of financial health.
    Range: [0, 1]. Higher = better fundamentals.
    """
    scores = []

    # Gross margin: >50% = excellent, >30% = good, >0% = ok, <=0% = bad
    if gross_margin is not None:
        gm = float(gross_margin)
        if gm > 1.0:
            gm = gm / 100.0  # normalize if stored as percentage
        scores.append(max(0.0, min(1.0, gm / 0.5)))

    # Current ratio: >2 = strong, >1 = adequate, <1 = weak
    if current_ratio is not None:
        cr = float(current_ratio)
        scores.append(max(0.0, min(1.0, cr / 2.0)))

    # Free cash flow: positive = good, scaled by revenue
    if free_cash_flow is not None and revenues is not None and float(revenues) > 0:
        fcf_margin = float(free_cash_flow) / float(revenues)
        scores.append(max(0.0, min(1.0, fcf_margin / 0.15)))  # 15% FCF margin = perfect
    elif free_cash_flow is not None:
        scores.append(1.0 if float(free_cash_flow) > 0 else 0.0)

    if not scores:
        return 0.5  # no fundamental data → neutral

    return sum(scores) / len(scores)


def compute_speculative_penalty(
    bar_count: Optional[int],
    price: Optional[float],
    market_cap: Optional[float],
) -> float:
    """Δ_spec: Speculative penalty.

    Thin, low-bar, micro-cap stocks get penalized.
    Range: [0, 1]. Higher = more speculative = worse.
    """
    penalty = 0.0

    # Low bar count → speculative (new/thin stock)
    if bar_count is not None:
        bc = int(bar_count)
        if bc < 50:
            penalty += 0.4
        elif bc < 100:
            penalty += 0.2
        elif bc < 200:
            penalty += 0.1

    # Very low price → penny stock risk
    if price is not None and float(price) < 5.0:
        penalty += 0.3
    elif price is not None and float(price) < 10.0:
        penalty += 0.1

    # Micro cap → speculative
    if market_cap is not None:
        mc = float(market_cap)
        if mc < 300_000_000:       # < $300M
            penalty += 0.3
        elif mc < 2_000_000_000:   # < $2B
            penalty += 0.1

    return min(1.0, penalty)


# ═════════════════════════════════════════════════════════════════════════
# Main Investability Score
# ═════════════════════════════════════════════════════════════════════════

def compute_investability_score(
    # Structural state (from snapshot)
    s_uf: float,
    d_k: float,
    r_rev_k: float,
    u_star_k: float,
    stability_score: float,
    # Fundamentals (from l5_fundamentals_normalized)
    gross_margin: Optional[float] = None,
    current_ratio: Optional[float] = None,
    free_cash_flow: Optional[float] = None,
    revenues: Optional[float] = None,
    # Speculative flags
    bar_count: Optional[int] = None,
    price: Optional[float] = None,
    market_cap: Optional[float] = None,
    # Epoch (from G32)
    epoch_pressure: float = 0.0,
    # Weights
    weights: ISWeights = DEFAULT_WEIGHTS,
) -> Dict[str, Any]:
    """Compute the full investability score per spec.

    Returns dict with score, components, and interpretation.
    """
    q_h = compute_structural_score(s_uf, d_k, r_rev_k)
    f_n = compute_free_energy(u_star_k, stability_score)
    q_fund = compute_fundamental_score(gross_margin, current_ratio, free_cash_flow, revenues)
    delta_spec = compute_speculative_penalty(bar_count, price, market_cap)
    omega_epoch = float(epoch_pressure)
    omega_strat = 0.0  # strategy classes not yet implemented

    # IS_h(s,t) = α·Q_h - β·F_n + γ·Q_fund - δ·Δ_spec + η·Ω_epoch + ζ·Ω_strat
    score = (
        weights.alpha * q_h
        - weights.beta * f_n
        + weights.gamma * q_fund
        - weights.delta * delta_spec
        + weights.eta * omega_epoch
        + weights.zeta * omega_strat
    )

    # Interpretation
    if score >= 0.7:
        tier = "STRONG_BUY"
    elif score >= 0.5:
        tier = "BUY"
    elif score >= 0.3:
        tier = "HOLD"
    elif score >= 0.1:
        tier = "WEAK_HOLD"
    else:
        tier = "AVOID"

    return {
        "investability_score": round(score, 4),
        "tier": tier,
        "components": {
            "structural_score": round(q_h, 4),
            "free_energy": round(f_n, 4),
            "fundamental_score": round(q_fund, 4),
            "speculative_penalty": round(delta_spec, 4),
            "epoch_pressure": round(omega_epoch, 4),
            "strategy_adjustment": round(omega_strat, 4),
        },
        "weights": {
            "alpha": weights.alpha,
            "beta": weights.beta,
            "gamma": weights.gamma,
            "delta": weights.delta,
            "eta": weights.eta,
            "zeta": weights.zeta,
        },
    }


if __name__ == "__main__":
    # Example: AMZN-like stock
    result = compute_investability_score(
        s_uf=0.889, d_k=1.0, r_rev_k=0.0, u_star_k=0.34, stability_score=0.0,
        gross_margin=0.50, current_ratio=1.05, free_cash_flow=139e9, revenues=600e9,
        bar_count=1255, price=259.0, market_cap=2.27e12,
        epoch_pressure=0.1,  # slight tailwind
    )
    print(f"AMZN investability: {result['investability_score']} ({result['tier']})")
    for k, v in result["components"].items():
        print(f"  {k}: {v}")

    # Example: low-conviction stock
    result2 = compute_investability_score(
        s_uf=0.3, d_k=-1.0, r_rev_k=1.0, u_star_k=0.7, stability_score=0.0,
        bar_count=50, price=3.0, market_cap=100e6,
        epoch_pressure=-0.5,  # adverse
    )
    print(f"\nLow-conviction: {result2['investability_score']} ({result2['tier']})")
    for k, v in result2["components"].items():
        print(f"  {k}: {v}")
