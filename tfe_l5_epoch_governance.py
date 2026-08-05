#!/usr/bin/env python3
"""
tfe_l5_epoch_governance.py
L5 Epoch Governance — Interpretation Layer

L4 shows the structural reality (what IS happening).
The epoch mosaic shows the context (WHY it's happening).
L5 combines them to produce governed meaning.

Spec: Ω_epoch(s,t) = Σ_j ρ_{s,j} Ξ_{t,j} + Ω_sec(s,t) + Ω_ind(s,t)

The coupling weight ρ_{s,j} is NOT derived from L4 output alone.
It is L5's governance rule that says HOW TO READ L4's output
in the context of the current epoch.

Example: L4 shows Energy as "turbulent" (volatile, contracting).
  - Without epoch context: turbulence = risk → penalize
  - With WAR_GEOPOLITICS high: turbulence in Energy = opportunity
    because oil companies BENEFIT from high oil prices even though
    the price action is volatile
  - With PANDEMIC high: turbulence in Energy = real risk
    because demand collapsed

Same L4 output, different L5 meaning, depending on epoch.

No ML. Deterministic. Auditable. All coupling rules documented.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from tfe_epoch_library import (
    SPHERE_CHANNELS, CHANNEL_INDEX, N_CHANNELS,
    G32Coordinator,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Sector-Epoch Coupling Matrix  ρ_{sector,channel}
#
#    Positive = epoch SUPPORTS this sector (opportunity)
#    Negative = epoch HURTS this sector (risk/penalty)
#    Zero     = no meaningful coupling
#
#    These are L5 governance rules, not L4-derived statistics.
#    They encode: "when this epoch channel is active, how does it
#    change the meaning of L4's structural output for this sector?"
#
#    Source: sector_sphere_coupling_registry_v1.json (scaffold)
#    + domain knowledge of how epoch types affect business fundamentals
# ═══════════════════════════════════════════════════════════════════════════

SECTOR_EPOCH_COUPLING: Dict[str, Dict[str, float]] = {
    "Energy": {
        # Oil companies benefit from high oil prices (revenue up)
        # even though L4 shows structural turbulence
        "WAR_GEOPOLITICS":   +0.6,   # war → oil supply fear → oil price up → revenue up
        "ENERGY_COMMODITY":  +0.7,   # direct commodity beneficiary
        "COMMODITY_SQUEEZE": +0.5,   # supply squeeze = pricing power
        "RATES_PRESSURE":    -0.2,   # capex sensitive to rates
        "CONSUMER_STRESS":   -0.1,   # demand destruction at extreme
        "TRADE_WAR":         +0.2,   # energy independence premium
    },
    "Defense": {
        # Defense spending surges during war/geopolitical tension
        "WAR_GEOPOLITICS":   +0.8,   # direct beneficiary of conflict spending
        "FISCAL_INFRA":      +0.3,   # government spending channel
        "TRADE_WAR":         +0.3,   # national security spending
        "RATES_PRESSURE":    -0.1,   # government contracts less rate-sensitive
    },
    "Healthcare": {
        # Defensive sector — less epoch-sensitive, structural shelter
        "WAR_GEOPOLITICS":   +0.1,   # mild safe-haven flow
        "PANDEMIC":          +0.7,   # direct beneficiary
        "CONSUMER_STRESS":   +0.2,   # inelastic demand
        "RATES_PRESSURE":    -0.2,   # some rate sensitivity (hospital capex)
        "REGULATION":        -0.5,   # drug pricing regulation risk
    },
    "Consumer Discretionary": {
        # First to suffer from inflation, fuel costs, consumer stress
        "CONSUMER_STRESS":   -0.8,   # direct hit to discretionary spending
        "ENERGY_COMMODITY":  -0.5,   # fuel costs reduce consumer wallet
        "RATES_PRESSURE":    -0.5,   # big-ticket purchases rate-sensitive
        "WAR_GEOPOLITICS":   -0.3,   # uncertainty reduces spending
        "COMMODITY_SQUEEZE": -0.4,   # input cost pressure
        "TRADE_WAR":         -0.4,   # supply chain disruption, tariffs
    },
    "Financial Services": {
        # Complex — higher rates help margins but hurt credit quality
        "RATES_PRESSURE":    +0.2,   # net interest margin benefit
        "CREDIT_STRESS":     -0.7,   # credit losses, provisions
        "WAR_GEOPOLITICS":   -0.3,   # uncertainty, market volatility
        "VOLATILITY_REGIME": -0.4,   # trading desk risk, client activity
        "CONSUMER_STRESS":   -0.3,   # consumer credit losses
    },
    "Real Estate": {
        # Most rate-sensitive sector
        "RATES_PRESSURE":    -0.9,   # direct mortgage/cap rate impact
        "CREDIT_STRESS":     -0.5,   # refinancing risk
        "BUILDING_CYCLE":    +0.4,   # construction activity (when positive)
        "CONSUMER_STRESS":   -0.3,   # rent affordability, vacancy
        "PANDEMIC":          -0.5,   # work-from-home, vacancy
    },
    "Technology": {
        # Growth stocks rate-sensitive, but also innovation beneficiary
        "RATES_PRESSURE":    -0.6,   # growth stock DCF discount
        "TECH_CYCLE":        -0.7,   # semiconductor, AI bubble risk
        "WAR_GEOPOLITICS":   -0.2,   # supply chain, China risk
        "TRADE_WAR":         -0.5,   # chip bans, export restrictions
        "REGULATION":        -0.4,   # antitrust, privacy
        "FISCAL_INFRA":      +0.2,   # government tech spending
    },
    "Consumer Staples": {
        # Defensive — minimal epoch sensitivity
        "CONSUMER_STRESS":   +0.3,   # trade-down effect (staples benefit)
        "WAR_GEOPOLITICS":   +0.1,   # mild safe-haven
        "RATES_PRESSURE":    -0.1,   # minimal sensitivity
        "ENERGY_COMMODITY":  -0.2,   # input cost (packaging, transport)
        "COMMODITY_SQUEEZE": -0.3,   # commodity inputs
    },
    "Industrials": {
        # Cyclical — sensitive to capex cycles and commodity costs
        "FISCAL_INFRA":      +0.7,   # direct infrastructure beneficiary
        "WAR_GEOPOLITICS":   +0.2,   # defense-adjacent, reconstruction
        "ENERGY_COMMODITY":  -0.4,   # fuel/material input costs
        "RATES_PRESSURE":    -0.3,   # capex cycle sensitivity
        "TRADE_WAR":         -0.4,   # global supply chain exposure
        "BUILDING_CYCLE":    +0.5,   # construction equipment
        "LABOR_PRESSURE":    -0.3,   # labor-intensive operations
    },
    "Utilities": {
        # Regulated, rate-sensitive, but also defensive
        "RATES_PRESSURE":    -0.6,   # capital-intensive, high leverage
        "CONSUMER_STRESS":   +0.2,   # inelastic demand
        "ENERGY_COMMODITY":  -0.3,   # fuel costs for generation (partially passed through)
        "REGULATION":        -0.3,   # regulatory risk on rates/returns
        "FISCAL_INFRA":      +0.3,   # grid infrastructure spending
    },
    "Materials": {
        "ENERGY_COMMODITY":  +0.5,   # commodity producers benefit from prices
        "COMMODITY_SQUEEZE": +0.6,   # pricing power
        "BUILDING_CYCLE":    +0.4,   # construction demand
        "TRADE_WAR":         -0.3,   # export restrictions
        "RATES_PRESSURE":    -0.2,   # capex sensitivity
    },
    "Communication Services": {
        "TECH_CYCLE":        -0.4,   # ad spending cyclical
        "CONSUMER_STRESS":   -0.3,   # ad budget cuts
        "REGULATION":        -0.5,   # content regulation, antitrust
        "RATES_PRESSURE":    -0.3,   # growth stock discount
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 2. Compute epoch pressure per symbol
#    Spec: Ω_epoch(s,t) = Σ_j ρ_{s,j} Ξ_{t,j}
# ═══════════════════════════════════════════════════════════════════════════

def compute_epoch_pressure(
    sector: str,
    epoch_mosaic: np.ndarray,
) -> float:
    """
    Compute the L5-governed epoch pressure for a symbol's sector.

    Positive = epoch conditions SUPPORT this sector
    Negative = epoch conditions HURT this sector

    The pressure combines the epoch mosaic (what's happening in the world)
    with the sector coupling (how that affects this sector's fundamentals).
    """
    couplings = SECTOR_EPOCH_COUPLING.get(sector, {})
    if not couplings:
        return 0.0

    pressure = 0.0
    for channel_name, coupling_weight in couplings.items():
        idx = CHANNEL_INDEX.get(channel_name)
        if idx is not None and idx < len(epoch_mosaic):
            pressure += coupling_weight * epoch_mosaic[idx]

    return pressure


def compute_all_sector_pressures(
    epoch_mosaic: np.ndarray,
) -> Dict[str, float]:
    """Compute epoch pressure for all sectors."""
    pressures = {}
    for sector in SECTOR_EPOCH_COUPLING:
        p = compute_epoch_pressure(sector, epoch_mosaic)
        if abs(p) > 0.01:
            pressures[sector] = round(p, 4)
    return pressures


# ═══════════════════════════════════════════════════════════════════════════
# 3. L5 Governance Decision: combine L4 DSF + epoch pressure
#
#    This is where L4 (structural reality) meets L5 (governed meaning).
#    The epoch pressure modifies how we interpret the DSF tuple.
# ═══════════════════════════════════════════════════════════════════════════

def interpret_dsf_with_epoch(
    dsf_tuple: Dict[str, float],
    sector: str,
    epoch_mosaic: np.ndarray,
    decision_label: str,
) -> Dict[str, Any]:
    """
    L5 governance interpretation.

    Takes L4 DSF output + epoch context and produces:
      - epoch_pressure: how much the epoch helps/hurts this sector
      - structural_profile: what L4 says about the stock's current state
      - governed_signal: the combined L5 interpretation
      - epoch_aligned: whether the epoch and structure agree

    This is NOT modifying L4's output. It's interpreting it in context.
    """
    pressure = compute_epoch_pressure(sector, epoch_mosaic)

    # Read the DSF tuple as a coupled whole
    d_k = dsf_tuple.get("D_k", 0)
    m_k = dsf_tuple.get("M_k", 0)
    b_k = dsf_tuple.get("B_k", 0)

    # Is L4 showing structural activity?
    has_signal = not (d_k == 0 and m_k == 0 and b_k == 0)

    # Determine alignment
    if not has_signal:
        alignment = "no_signal"
        governed = "epoch_only"
    elif pressure > 0.2 and d_k >= 0:
        alignment = "aligned_positive"
        governed = "strong_opportunity"
    elif pressure > 0.2 and d_k < 0:
        alignment = "epoch_positive_structure_negative"
        governed = "opportunity_with_structural_risk"
    elif pressure < -0.2 and d_k <= 0:
        alignment = "aligned_negative"
        governed = "avoid"
    elif pressure < -0.2 and d_k > 0:
        alignment = "epoch_negative_structure_positive"
        governed = "structural_strength_against_headwind"
    else:
        alignment = "neutral"
        governed = "no_epoch_effect"

    return {
        "sector": sector,
        "decision_label": decision_label,
        "epoch_pressure": round(pressure, 4),
        "has_structural_signal": has_signal,
        "alignment": alignment,
        "governed_signal": governed,
        "dsf": dsf_tuple,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. Batch evaluation — run epoch governance on a set of stocks
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_accumulate_pool(
    stocks: List[Dict[str, Any]],
    coordinator: G32Coordinator,
) -> List[Dict[str, Any]]:
    """
    Apply epoch governance to all Accumulate stocks.

    Each stock dict should have:
      - ticker, sector, decision_label
      - DSF fields: D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k

    Returns list of governed interpretations sorted by epoch alignment.
    """
    mosaic = coordinator.xi_current
    results = []

    for stock in stocks:
        sector = stock.get("sector", "Unknown")
        dsf = {
            f: stock.get(f, 0)
            for f in ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"]
        }
        interpretation = interpret_dsf_with_epoch(
            dsf_tuple=dsf,
            sector=sector,
            epoch_mosaic=mosaic,
            decision_label=stock.get("decision_label", "Unknown"),
        )
        interpretation["ticker"] = stock.get("ticker", "?")
        results.append(interpretation)

    # Sort: strong opportunities first, avoids last
    signal_order = {
        "strong_opportunity": 0,
        "opportunity_with_structural_risk": 1,
        "structural_strength_against_headwind": 2,
        "epoch_only": 3,
        "no_epoch_effect": 4,
        "avoid": 5,
    }
    results.sort(key=lambda r: signal_order.get(r["governed_signal"], 4))

    return results
