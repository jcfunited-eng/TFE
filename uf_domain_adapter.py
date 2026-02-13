"""
uf_domain_adapter.py
-----------------------------------------
UF → TFE Decision Adapter (4-Action Model)

Official decision language:
    - "accumulate"
    - "hold"
    - "trim"
    - "avoid"

Input:
    UFStructuralState (from uf_structural_engine.compute_uf_structural_state)

Output:
    DomainDecision:
        - action              ∈ {accumulate, hold, trim, avoid}
        - confidence          ∈ [0,1]
        - risk_score          ∈ [0,1] (1 = high risk)
        - opportunity_score   ∈ [0,1] (1 = high opportunity)
        - regime              (UF L3 regime)
        - rationale           (dict for explanations/debug)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from uf_structural_engine import UFStructuralState


@dataclass
class DomainDecision:
    action: str
    confidence: float
    risk_score: float
    opportunity_score: float
    regime: str
    rationale: Dict[str, Any]


def evaluate_domain_decision(state: UFStructuralState) -> DomainDecision:
    """
    Map UFStructuralState → DomainDecision (4 actions).

    This v1.0 adapter uses:
      - Level1: vol, avg_return, price_range, n
      - Level2: trend_strength, curvature
      - Level3: regime
      - Level4: max_drawdown, stability_score, S_UF, R_UF
      - Level5: last DSF_k (D_k, M_k, P_k, B_k, U*_k)

    Rules (hard, interpretable):

      1. Compute risk_score:
         - Higher volatility increases risk
         - Deeper max drawdown increases risk
         - Low stability_score increases risk

      2. Compute opportunity_score:
         - Positive trend_strength increases opportunity
         - High S_UF and R_UF increase opportunity
         - Expansion phase (P_k=+1, D_k=+1) increases opportunity
         - Excessive volatility / negative drawdown penalize opportunity

      3. Map to actions:
         - ACCUMULATE if opportunity high, risk moderate/low
         - HOLD       if opportunity moderate or balanced with risk
         - TRIM       if risk high, opportunity modest
         - AVOID      if risk very high or opportunity very low

    Thresholds will need calibration, but this is a clear starting point.
    """
    L1 = state.level1
    L2 = state.level2
    L3 = state.level3
    L4 = state.level4
    L5 = state.level5

    vol = float(L1.get("vol", 0.0))                     # annualized volatility
    avg_ret = float(L1.get("avg_return", 0.0))          # annualized
    trend = float(L2.get("trend_strength", 0.0))
    curvature = float(abs(L2.get("curvature", 0.0)))
    regime = str(L3.get("regime", "UNKNOWN"))
    max_dd = float(L4.get("max_drawdown", 0.0))         # negative
    stability = float(L4.get("stability_score", 0.0))
    S_UF = float(L4.get("S_UF", 0.0))
    R_UF = float(L4.get("R_UF", 0.0))

    dsf_list = L5.get("dsf_list", [])
    if dsf_list:
        last = dsf_list[-1]
        D_k = int(last.get("D_k", 0))
        M_k = int(last.get("M_k", 0))
        P_k = int(last.get("P_k", 0))
        B_k = int(last.get("B_k", 0))
        U_star = float(last.get("U_star_k", 0.0))
    else:
        D_k = M_k = P_k = B_k = 0
        U_star = 0.0

    # --------------------------------------------------
    # RISK SCORE (0–1) – high = bad
    # --------------------------------------------------
    # Volatility: saturate around 60%+
    risk = 0.0
    risk += min(1.0, vol / 0.6) * 0.5          # 50% weight
    # Drawdown: saturate around 30% drawdown
    risk += min(1.0, abs(max_dd) / 0.3) * 0.3  # 30% weight
    # Low stability increases risk
    risk += max(0.0, 0.5 - stability) * 0.4    # up to +0.2

    # Clip to [0,1]
    risk_score = max(0.0, min(1.0, risk))

    # --------------------------------------------------
    # OPPORTUNITY SCORE (0–1) – high = good
    # --------------------------------------------------
    opp = 0.0

    # Positive trend and avg_ret help
    if trend > 0.02:
        opp += 0.25
    elif trend > 0.0:
        opp += 0.15

    if avg_ret > 0.0:
        opp += 0.15

    # S_UF and R_UF boost opportunity if above mid thresholds
    if S_UF >= 0.5:
        opp += 0.25
    elif S_UF >= 0.3:
        opp += 0.15

    if R_UF >= 0.3:
        opp += 0.2
    elif R_UF >= 0.15:
        opp += 0.1

    # Expansion phase & positive direction (D_k, P_k)
    if D_k == 1 and P_k == 1:
        opp += 0.15
    elif D_k == 1 or P_k == 1:
        opp += 0.05

    # Penalize with volatility, curvature, and deep drawdowns
    opp -= min(0.3, vol * 0.5)
    opp -= min(0.2, curvature * 5.0)
    opp -= min(0.3, abs(max_dd) * 1.0)

    opportunity_score = max(0.0, min(1.0, opp))

    # --------------------------------------------------
    # ACTION MAPPING (4 actions)
    # --------------------------------------------------

    # Heuristic bands – will need calibration
    if opportunity_score >= 0.6 and risk_score <= 0.4:
        action = "accumulate"
    elif opportunity_score >= 0.4 and risk_score <= 0.6:
        action = "hold"
    elif risk_score >= 0.7 and opportunity_score <= 0.3:
        action = "avoid"
    elif risk_score >= 0.6 and trend <= 0.0:
        action = "trim"
    else:
        # default: hold under ambiguous conditions
        action = "hold"

    # Confidence: difference between opportunity and risk, normalized
    confidence = max(0.0, min(1.0, 0.5 + (opportunity_score - risk_score)))

    rationale = {
        "vol": vol,
        "avg_return": avg_ret,
        "trend_strength": trend,
        "curvature": curvature,
        "regime": regime,
        "max_drawdown": max_dd,
        "stability_score": stability,
        "S_UF": S_UF,
        "R_UF": R_UF,
        "D_k": D_k,
        "M_k": M_k,
        "P_k": P_k,
        "B_k": B_k,
        "U_star": U_star,
        "risk_score": risk_score,
        "opportunity_score": opportunity_score,
    }

    return DomainDecision(
        action=action,
        confidence=confidence,
        risk_score=risk_score,
        opportunity_score=opportunity_score,
        regime=regime,
        rationale=rationale,
    )
