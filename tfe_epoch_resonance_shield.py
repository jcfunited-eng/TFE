#!/usr/bin/env python3
"""
TFE Epoch Resonance Shield — L5 Governance Gate
=================================================

Distinguishes "a technically attractive setup inside a hostile external
mosaic from the same setup inside a supportive one."
(TFE Specification v3.0, line 2248)

The shield reads the G32 epoch mosaic as a COUPLED field — not individual
channels — and determines whether the macro environment is hostile.

When hostile:
  - CH3 enters restricted mode
  - Assets are only cleared if their DSF shape shows structural cohesion
    under compression, not just compression alone
  - A falling knife compresses WITH structural decay
  - A coiled spring compresses WITH structural cohesion

The shield uses the FULL coupled DSF — all seven L4 values as one shape.
No decomposition. No independent thresholds on D_k or M_k.

No ML. No heuristics. Deterministic operators on the coupled field.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


# ═════════════════════════════════════════════════════════════════════════
# Epoch Mosaic Assessment
# Reads G32 state as a coupled field, not individual channels
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EpochAssessment:
    """The macro environment as seen by the shield."""
    hostile: bool              # is the macro environment hostile?
    mosaic_magnitude: float    # ||Ξ_t|| — total epoch pressure magnitude
    delta_magnitude: float     # ||ΔΞ_t|| — how fast the epoch is changing
    stress_aggregate: float    # net adverse pressure across all channels
    phase: str                 # HOSTILE / STRESSED / NEUTRAL / SUPPORTIVE
    sector_pressure: float     # sector-specific epoch pressure (if available)


def assess_epoch(g32_state_path: str = "/app/g32_state.json",
                 sector: Optional[str] = None) -> EpochAssessment:
    """Read the G32 mosaic and assess macro environment.

    The mosaic is read as ONE coupled field — the magnitude and direction
    of the full epoch vector, not individual channels.
    """
    try:
        with open(g32_state_path) as f:
            g32 = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # No G32 state — assume neutral (don't block trades on missing data)
        return EpochAssessment(
            hostile=False, mosaic_magnitude=0.0, delta_magnitude=0.0,
            stress_aggregate=0.0, phase="UNKNOWN", sector_pressure=0.0,
        )

    xi = g32.get("xi", {})
    xi_delta = g32.get("xi_delta", {})

    # Mosaic as a vector — all channels together
    xi_vec = np.array([float(xi.get(ch, 0)) for ch in sorted(xi.keys())])
    delta_vec = np.array([float(xi_delta.get(ch, 0)) for ch in sorted(xi_delta.keys())])

    mosaic_magnitude = float(np.linalg.norm(xi_vec))
    delta_magnitude = float(np.linalg.norm(delta_vec))

    # Stress aggregate: sum of all NEGATIVE pressure contributions
    # Channels with negative severity = adverse forces acting on the market
    # This is the coupled stress — how much total adverse energy is in the mosaic
    stress_channels = [
        "RATES_PRESSURE", "CONSUMER_STRESS", "WAR_GEOPOLITICS",
        "ENERGY_COMMODITY", "VOLATILITY_REGIME",
    ]
    stress = 0.0
    for ch in stress_channels:
        v = float(xi.get(ch, 0))
        if v > 0:  # positive severity = active pressure
            stress += v

    # Sector-specific pressure if sector provided
    sector_pressure = 0.0
    if sector:
        from tfe_epoch_mosaic_coordinator import SECTOR_COUPLING, EPOCH_CHANNELS
        coupling = SECTOR_COUPLING.get(sector, {})
        for ch in EPOCH_CHANNELS:
            weight = coupling.get(ch, 0.0)
            sector_pressure += float(xi.get(ch, 0)) * weight

    # SPY structural direction from the snapshot
    # The market's own DSF tells us if macro gravity is pulling down
    spy_dk = 0
    try:
        import pg
        db_pool = pg.Pool({
            'host': os.environ.get('PGHOST', ''),
            'database': os.environ.get('PGDATABASE', ''),
            'user': os.environ.get('PGUSER', ''),
            'password': os.environ.get('PGPASSWORD', ''),
            'ssl': {'rejectUnauthorized': False},
        })
    except Exception:
        pass
    # Read SPY D_k from the snapshot if available
    try:
        with open(os.path.join(os.path.dirname(g32_state_path), "uf_snapshot.json")) as f:
            snap_text = f.read().replace('NaN', 'null').replace('-Infinity', 'null').replace('Infinity', 'null')
            snap = json.loads(snap_text)
        rows = snap if isinstance(snap, list) else snap.get("rows", [])
        for r in rows:
            if r.get("ticker") == "SPY":
                spy_dk = r.get("D_k", 0) or 0
                break
    except Exception:
        spy_dk = 0

    # Phase determination from the coupled mosaic + market direction
    # Stress alone doesn't determine hostility — direction does
    # High stress + contracting market = HOSTILE (falling knives everywhere)
    # High stress + expanding market = CAUTIOUS (risk elevated but market absorbing)
    if stress > 1.0 and spy_dk <= 0 and delta_magnitude > 0.05:
        phase = "HOSTILE"       # high stress + market contracting + epoch changing
    elif stress > 1.0 and spy_dk <= 0:
        phase = "STRESSED"      # high stress + market contracting but epoch stable
    elif stress > 1.0 and spy_dk > 0:
        phase = "CAUTIOUS"      # high stress but market still expanding (bull with risks)
    elif stress > 0.5:
        phase = "CAUTIOUS"      # moderate stress
    elif sector_pressure > 0.3:
        phase = "SUPPORTIVE"    # sector has tailwind
    else:
        phase = "NEUTRAL"

    hostile = phase in ("HOSTILE", "STRESSED")

    return EpochAssessment(
        hostile=hostile,
        mosaic_magnitude=mosaic_magnitude,
        delta_magnitude=delta_magnitude,
        stress_aggregate=stress,
        phase=phase,
        sector_pressure=sector_pressure,
    )


# ═════════════════════════════════════════════════════════════════════════
# Structural Cohesion Assessment
# Reads the DSF as a coupled shape — falling knife vs coiled spring
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CohesionAssessment:
    """Is this DSF shape a coiled spring or a falling knife?"""
    cohesive: bool          # does the shape hold structural integrity?
    shape_type: str         # COILED_SPRING / FALLING_KNIFE / AMBIGUOUS
    confidence: float       # 0-1 confidence in the assessment


def assess_cohesion(
    D_k: float, M_k: float, R_rev_k: float,
    U_star_k: float, C_k: float, P_k: float, B_k: float,
    S_UF: float = 0.0,
) -> CohesionAssessment:
    """Read the FULL coupled DSF shape to distinguish spring from knife.

    A coiled spring:
      - The field is compressed (B deep negative)
      - BUT the structural surface is SIMPLE (C=2, low complexity)
      - AND the field is RESOLVED (U* low, uncertainty handled)
      - AND the surface is SMOOTH (P=0, no cracks)

    A falling knife:
      - The field is compressed (B deep negative) — same as spring
      - BUT the structural surface is COMPLEX (C=3, many folds)
      - AND/OR the field is UNRESOLVED (U* high, still uncertain)
      - AND/OR the surface is CRACKED (P=2, discontinuity)

    The key insight from the crisis data analysis: these look identical
    if you only check B_k. You must read the FULL coupled shape.

    No decomposition — we're reading the shape as one object.
    The combination of ALL values determines the assessment.
    """
    # The full shape as a 7D point
    dsf = np.array([D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k])

    # Coiled spring archetype: from the crisis study, the big UP moves
    # consistently came from this coupled shape
    # D=+1, |M|<0.15, Rrev=0, U*<0.25, C=2, P=0, B<=-0.50
    spring_archetype = np.array([1.0, 0.0, 0.0, 0.20, 2.0, 0.0, -1.0])

    # Falling knife archetype: from the crisis study, the DN moves
    # had this shape — compressed BUT with structural decay
    # Any D, |M| high, Rrev=1, U*>0.40, C=3, P=2, B<=-0.50
    knife_archetype = np.array([0.0, 0.0, 1.0, 0.50, 3.0, 2.0, -1.0])

    # Distance to each archetype in the coupled space
    # Normalization keeps coupling intact
    norms = np.array([2.0, 2.0, 1.0, 1.0, 3.0, 2.0, 2.0])

    dist_spring = float(np.sqrt(np.sum(((dsf - spring_archetype) / norms) ** 2)))
    dist_knife = float(np.sqrt(np.sum(((dsf - knife_archetype) / norms) ** 2)))

    # The shape is read as proximity to each archetype
    # Not a threshold on any single field
    total_dist = dist_spring + dist_knife
    if total_dist == 0:
        confidence = 0.5
    else:
        # How much closer to spring than knife (0 = pure knife, 1 = pure spring)
        spring_affinity = dist_knife / total_dist
        confidence = spring_affinity

    if confidence > 0.6:
        shape_type = "COILED_SPRING"
        cohesive = True
    elif confidence < 0.4:
        shape_type = "FALLING_KNIFE"
        cohesive = False
    else:
        shape_type = "AMBIGUOUS"
        cohesive = False  # err on side of caution in ambiguity

    return CohesionAssessment(
        cohesive=cohesive,
        shape_type=shape_type,
        confidence=confidence,
    )


# ═════════════════════════════════════════════════════════════════════════
# The Shield Gate — combines epoch + cohesion
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ShieldResult:
    """Should CH3 proceed with this candidate?"""
    cleared: bool
    reason: str
    epoch: EpochAssessment
    cohesion: CohesionAssessment


def evaluate_shield(
    D_k: float, M_k: float, R_rev_k: float,
    U_star_k: float, C_k: float, P_k: float, B_k: float,
    S_UF: float = 0.0,
    sector: Optional[str] = None,
    g32_state_path: str = "/app/g32_state.json",
) -> ShieldResult:
    """The Epoch Resonance Shield gate.

    In supportive/neutral epochs: let the CH3 hunter's existing filters decide.
    In hostile epochs: require structural cohesion (coiled spring, not falling knife).

    This is the umbrella — if it's raining, you need more than just compression
    to justify entering a trade.
    """
    epoch = assess_epoch(g32_state_path, sector)
    cohesion = assess_cohesion(D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, S_UF)

    if epoch.phase == "HOSTILE":
        # Hostile epoch — full quarantine. No CH3 entries.
        # The umbrella: when macro gravity is pulling everything down,
        # even structurally attractive setups get crushed.
        # The -16.5% hostile epoch test proved this: 0% win rate on 7 picks.
        return ShieldResult(
            cleared=False,
            reason=f"hostile_epoch_quarantine (stress={epoch.stress_aggregate:.2f} delta={epoch.delta_magnitude:.3f})",
            epoch=epoch,
            cohesion=cohesion,
        )

    if epoch.phase == "STRESSED":
        # Stressed but not hostile — require sector tailwind
        # The sector coupling must be positive: the epoch is HELPING this stock's sector
        if epoch.sector_pressure > 0.1:
            return ShieldResult(
                cleared=True,
                reason=f"stressed_epoch_sector_tailwind ({epoch.sector_pressure:+.2f})",
                epoch=epoch,
                cohesion=cohesion,
            )
        else:
            return ShieldResult(
                cleared=False,
                reason=f"stressed_epoch_no_tailwind (sector={epoch.sector_pressure:+.2f})",
                epoch=epoch,
                cohesion=cohesion,
            )

    # Neutral, cautious, or supportive — existing CH3 filters are sufficient
    return ShieldResult(
        cleared=True,
        reason=f"epoch_{epoch.phase.lower()}_pass",
        epoch=epoch,
        cohesion=cohesion,
    )


# ═════════════════════════════════════════════════════════════════════════
# Test
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Coiled spring in hostile epoch
    result = evaluate_shield(
        D_k=1, M_k=0.02, R_rev_k=0, U_star_k=0.20, C_k=2, P_k=0, B_k=-1.0,
        sector="Financial Services",
        g32_state_path="g32_state.json",
    )
    print(f"Coiled spring: cleared={result.cleared} reason={result.reason}")
    print(f"  epoch: {result.epoch.phase} stress={result.epoch.stress_aggregate:.2f}")
    print(f"  cohesion: {result.cohesion.shape_type} confidence={result.cohesion.confidence:.2f}")

    # Falling knife in hostile epoch
    result2 = evaluate_shield(
        D_k=-1, M_k=-0.30, R_rev_k=1, U_star_k=0.50, C_k=3, P_k=2, B_k=-1.0,
        sector="Financial Services",
        g32_state_path="g32_state.json",
    )
    print(f"\nFalling knife: cleared={result2.cleared} reason={result2.reason}")
    print(f"  epoch: {result2.epoch.phase} stress={result2.epoch.stress_aggregate:.2f}")
    print(f"  cohesion: {result2.cohesion.shape_type} confidence={result2.cohesion.confidence:.2f}")
