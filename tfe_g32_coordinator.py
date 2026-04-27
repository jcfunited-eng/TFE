#!/usr/bin/env python3
"""
TFE G32 Epoch Coordinator — deterministic epoch mosaic engine.

Built from TFE Specification v3.0, Sections 14-16.

The G32 coordinator maintains the live epoch mosaic, computes sector
and company epoch pressure, and provides the epoch field to L5 governance.

Core objects (from spec):
  Ξ_t        = epoch mosaic (channel amplitudes at time t)
  Ξ̄_t        = EMA-smoothed mosaic (structural trend)
  ΔΞ_t       = Ξ_t - Ξ̄_t (epoch delta — deviation from trend)
  Ω_sec(s,t) = sector-specific epoch pressure
  ω_k(t)     = temporal amplitude of epoch object k at time t

No ML. No heuristics. Deterministic operators on measured quantities.
Coupling matrix values are governed constants from domain knowledge.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np


# ═════════════════════════════════════════════════════════════════════════
# Epoch Channel Registry — extensible to 32 channels per spec
# ═════════════════════════════════════════════════════════════════════════

# Active channels (currently 3, extensible)
EPOCH_CHANNELS = [
    "RATES_PRESSURE",       # Channel 0: interest rates, yield curve, credit stress
    "CONSUMER_STRESS",      # Channel 1: consumer spending rotation, fear
    "WAR_GEOPOLITICS",      # Channel 2: conflict, energy shock, defense rotation
    "ENERGY_COMMODITY",     # Channel 3: oil/gas/commodity input costs
    "TECH_CYCLE",           # Channel 4: semiconductor/tech rotation
    "CURRENCY_FX",          # Channel 5: dollar strength, EM stress
    "FISCAL_INFRA",         # Channel 6: infrastructure/fiscal spending
    "VOLATILITY_REGIME",    # Channel 7: VIX level and acceleration
    # Future channels (spec allows up to 32):
    # "REGULATION",         # Channel 8: regulatory/litigation pressure
    # "LABOR_MARKET",       # Channel 9: employment, wage pressure
    # "PANDEMIC_HEALTH",    # Channel 10: health crisis, supply chain
]

N_CHANNELS = len(EPOCH_CHANNELS)

# ═════════════════════════════════════════════════════════════════════════
# Sector-Epoch Coupling Matrix M^sec — governed constants
#
# Values represent how each sector responds to each epoch channel.
# Positive = sector benefits from this epoch pressure.
# Negative = sector is hurt by this epoch pressure.
# These are domain knowledge, not fitted parameters.
# ═════════════════════════════════════════════════════════════════════════

SECTOR_COUPLING: Dict[str, Dict[str, float]] = {
    # Each value: how sector responds to this epoch channel.
    # Positive = benefits. Negative = hurt. Zero = neutral.
    # 8 channels: RATES, CONSUMER, WAR, ENERGY, TECH, FX, FISCAL, VOL
    "Communication Services": {
        "RATES_PRESSURE": -0.2, "CONSUMER_STRESS": -0.3, "WAR_GEOPOLITICS": -0.1,
        "ENERGY_COMMODITY": -0.1, "TECH_CYCLE": -0.5,     "CURRENCY_FX": -0.2,
        "FISCAL_INFRA": 0.1,     "VOLATILITY_REGIME": -0.3,
    },
    "Consumer Discretionary": {
        "RATES_PRESSURE": -0.5, "CONSUMER_STRESS": -1.0, "WAR_GEOPOLITICS": -0.2,
        "ENERGY_COMMODITY": -0.4, "TECH_CYCLE": -0.1,     "CURRENCY_FX": -0.2,
        "FISCAL_INFRA": 0.1,     "VOLATILITY_REGIME": -0.5,
    },
    "Consumer Staples": {
        "RATES_PRESSURE": 0.1,  "CONSUMER_STRESS": 0.4,  "WAR_GEOPOLITICS": -0.1,
        "ENERGY_COMMODITY": -0.3, "TECH_CYCLE": 0.0,      "CURRENCY_FX": -0.2,
        "FISCAL_INFRA": 0.0,     "VOLATILITY_REGIME": 0.2,  # defensive
    },
    "Energy": {
        "RATES_PRESSURE": 0.0,  "CONSUMER_STRESS": -0.2, "WAR_GEOPOLITICS": 0.9,
        "ENERGY_COMMODITY": 0.9,  "TECH_CYCLE": 0.0,      "CURRENCY_FX": 0.3,
        "FISCAL_INFRA": 0.2,     "VOLATILITY_REGIME": 0.1,
    },
    "Financial Services": {
        "RATES_PRESSURE": 0.2,  "CONSUMER_STRESS": -0.5, "WAR_GEOPOLITICS": -0.2,
        "ENERGY_COMMODITY": 0.0,  "TECH_CYCLE": -0.1,     "CURRENCY_FX": 0.1,
        "FISCAL_INFRA": 0.1,     "VOLATILITY_REGIME": -0.4,
    },
    "Financials": {
        "RATES_PRESSURE": 0.2,  "CONSUMER_STRESS": -0.5, "WAR_GEOPOLITICS": -0.2,
        "ENERGY_COMMODITY": 0.0,  "TECH_CYCLE": -0.1,     "CURRENCY_FX": 0.1,
        "FISCAL_INFRA": 0.1,     "VOLATILITY_REGIME": -0.4,
    },
    "Health Care": {
        "RATES_PRESSURE": 0.0,  "CONSUMER_STRESS": 0.3,  "WAR_GEOPOLITICS": 0.1,
        "ENERGY_COMMODITY": -0.1, "TECH_CYCLE": 0.1,      "CURRENCY_FX": -0.1,
        "FISCAL_INFRA": 0.1,     "VOLATILITY_REGIME": 0.1,  # defensive
    },
    "Healthcare": {
        "RATES_PRESSURE": 0.0,  "CONSUMER_STRESS": 0.3,  "WAR_GEOPOLITICS": 0.1,
        "ENERGY_COMMODITY": -0.1, "TECH_CYCLE": 0.1,      "CURRENCY_FX": -0.1,
        "FISCAL_INFRA": 0.1,     "VOLATILITY_REGIME": 0.1,
    },
    "Industrials": {
        "RATES_PRESSURE": -0.2, "CONSUMER_STRESS": -0.3, "WAR_GEOPOLITICS": 0.2,
        "ENERGY_COMMODITY": -0.3, "TECH_CYCLE": 0.0,      "CURRENCY_FX": -0.2,
        "FISCAL_INFRA": 0.8,     "VOLATILITY_REGIME": -0.3,  # big fiscal beneficiary
    },
    "Information Technology": {
        "RATES_PRESSURE": -0.4,   # growth stocks hurt by rates
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Technology": {
        "RATES_PRESSURE": -0.4,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Materials": {
        "RATES_PRESSURE": -0.1,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.3,   # commodity demand
    },
    "Real Estate": {
        "RATES_PRESSURE": -1.0,   # most rate-sensitive sector
        "CONSUMER_STRESS": -0.5,
        "WAR_GEOPOLITICS": 0.0,
    },
    "Utilities": {
        "RATES_PRESSURE": -0.3,
        "CONSUMER_STRESS": 0.2,   # defensive
        "WAR_GEOPOLITICS": 0.1,
    },
    "Banking": {
        "RATES_PRESSURE": 0.3,
        "CONSUMER_STRESS": -0.6,
        "WAR_GEOPOLITICS": -0.2,
    },
    "Basic Materials": {
        "RATES_PRESSURE": -0.1,
        "CONSUMER_STRESS": -0.3,
        "WAR_GEOPOLITICS": 0.3,
    },
}

# ═════════════════════════════════════════════════════════════════════════
# G32 State
# ═════════════════════════════════════════════════════════════════════════

# EMA smoothing constant (spec: α_g)
ALPHA_G = 0.85  # strong smoothing — epoch trends are slow

# Adverse pressure threshold (from existing epoch library)
ADVERSE_THRESHOLD = -0.5


@dataclass
class G32State:
    """The G32 coordinator state vector per spec."""

    # Ξ_t: current epoch mosaic (channel amplitudes)
    xi: np.ndarray = field(default_factory=lambda: np.zeros(len(EPOCH_CHANNELS)))

    # Ξ̄_t: EMA-smoothed mosaic
    xi_ema: np.ndarray = field(default_factory=lambda: np.zeros(len(EPOCH_CHANNELS)))

    # ΔΞ_t: epoch delta (deviation from trend)
    xi_delta: np.ndarray = field(default_factory=lambda: np.zeros(len(EPOCH_CHANNELS)))

    # Metadata
    updated_at: Optional[str] = None
    source: str = "uninitialized"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "xi": {ch: float(self.xi[i]) for i, ch in enumerate(EPOCH_CHANNELS)},
            "xi_ema": {ch: float(self.xi_ema[i]) for i, ch in enumerate(EPOCH_CHANNELS)},
            "xi_delta": {ch: float(self.xi_delta[i]) for i, ch in enumerate(EPOCH_CHANNELS)},
            "updated_at": self.updated_at,
            "source": self.source,
        }


# ═════════════════════════════════════════════════════════════════════════
# G32 Coordinator
# ═════════════════════════════════════════════════════════════════════════

class G32Coordinator:
    """Deterministic epoch mosaic coordinator per TFE Spec v3.0."""

    def __init__(self) -> None:
        self._state = G32State()
        self._cache_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "g32_state.json",
        )
        self._load_cached_state()

    def _load_cached_state(self) -> None:
        """Load previous state from disk if available."""
        try:
            with open(self._cache_path) as f:
                cached = json.load(f)
            for i, ch in enumerate(EPOCH_CHANNELS):
                self._state.xi[i] = cached.get("xi", {}).get(ch, 0.0)
                self._state.xi_ema[i] = cached.get("xi_ema", {}).get(ch, 0.0)
            self._state.updated_at = cached.get("updated_at")
            self._state.source = "cached"
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            self._state.source = "fresh"

    def _save_state(self) -> None:
        """Persist state to disk."""
        try:
            with open(self._cache_path, "w") as f:
                json.dump(self._state.to_dict(), f, indent=2)
        except Exception as exc:
            print(f"[G32] State save failed: {exc}", flush=True)

    def update(self, live_severities: Dict[str, float]) -> G32State:
        """Update the epoch mosaic with new live severity scores.

        This is the core G32 update per spec:
          Ξ_t = severity vector (from live market data)
          Ξ̄_t = α_g · Ξ̄_{t-1} + (1 - α_g) · Ξ_t
          ΔΞ_t = Ξ_t - Ξ̄_t
        """
        # Build current mosaic vector from live data
        xi_new = np.zeros(N_CHANNELS)
        for i, ch in enumerate(EPOCH_CHANNELS):
            xi_new[i] = float(live_severities.get(ch, 0.0))

        # EMA update
        if self._state.source == "fresh":
            # First update — initialize EMA to current
            xi_ema_new = xi_new.copy()
        else:
            xi_ema_new = ALPHA_G * self._state.xi_ema + (1 - ALPHA_G) * xi_new

        # Delta
        xi_delta_new = xi_new - xi_ema_new

        # Update state
        self._state.xi = xi_new
        self._state.xi_ema = xi_ema_new
        self._state.xi_delta = xi_delta_new
        self._state.updated_at = datetime.now(timezone.utc).isoformat()
        self._state.source = "live"

        self._save_state()

        print(
            f"[G32] Mosaic updated: "
            + " | ".join(f"{ch}={xi_new[i]:.3f}(Δ={xi_delta_new[i]:+.3f})" for i, ch in enumerate(EPOCH_CHANNELS)),
            flush=True,
        )

        return self._state

    def get_state(self) -> G32State:
        """Return current G32 state."""
        return self._state

    def compute_sector_pressure(self, sector: str) -> Dict[str, Any]:
        """Compute epoch pressure for a sector.

        Ω_sec(s,t) = Σ_j Ξ_{t,j} · M^sec_{j,σ(s)}

        Returns dict with pressure value, channel breakdown, and pass/fail.
        """
        normalized = str(sector).strip()

        # Try exact match, then common variations
        coupling = SECTOR_COUPLING.get(normalized)
        if coupling is None:
            # Try case-insensitive
            for key in SECTOR_COUPLING:
                if key.lower() == normalized.lower():
                    coupling = SECTOR_COUPLING[key]
                    break

        if coupling is None:
            return {
                "status": "UNKNOWN_SECTOR",
                "sector": normalized,
                "pressure": 0.0,
                "note": "Sector not in coupling matrix — epoch neutral",
            }

        # Compute Ω_sec per spec
        total_pressure = 0.0
        channel_breakdown = {}
        for i, ch in enumerate(EPOCH_CHANNELS):
            weight = coupling.get(ch, 0.0)
            contribution = float(self._state.xi[i]) * weight
            total_pressure += contribution
            channel_breakdown[ch] = {
                "severity": float(self._state.xi[i]),
                "coupling": weight,
                "contribution": round(contribution, 4),
            }

        total_pressure = round(total_pressure, 4)

        # Adverse check
        if total_pressure <= ADVERSE_THRESHOLD:
            status = "ADVERSE"
        elif total_pressure <= 0:
            status = "HEADWIND"
        elif total_pressure > 0.3:
            status = "TAILWIND"
        else:
            status = "NEUTRAL"

        return {
            "status": status,
            "sector": normalized,
            "pressure": total_pressure,
            "channels": channel_breakdown,
            "adverse": total_pressure <= ADVERSE_THRESHOLD,
        }

    def compute_epoch_delta_signal(self) -> Dict[str, Any]:
        """Compute the epoch delta signal — deviation from trend.

        Large positive ΔΞ = epoch pressure INCREASING (new stress arriving)
        Large negative ΔΞ = epoch pressure DECREASING (stress abating)
        Near zero = stable epoch environment

        This is the G32's contribution to detecting upheaval → settling patterns.
        """
        delta_magnitude = float(np.linalg.norm(self._state.xi_delta))
        delta_direction = {}
        for i, ch in enumerate(EPOCH_CHANNELS):
            delta_direction[ch] = {
                "current": float(self._state.xi[i]),
                "trend": float(self._state.xi_ema[i]),
                "delta": float(self._state.xi_delta[i]),
            }

        if delta_magnitude > 0.15:
            phase = "UPHEAVAL"
        elif delta_magnitude > 0.05:
            phase = "TRANSITIONING"
        else:
            phase = "SETTLED"

        return {
            "phase": phase,
            "delta_magnitude": round(delta_magnitude, 4),
            "channels": delta_direction,
        }


# ═════════════════════════════════════════════════════════════════════════
# Convenience: one-shot evaluation
# ═════════════════════════════════════════════════════════════════════════

def evaluate_epoch_environment() -> Dict[str, Any]:
    """Full G32 evaluation: update from live data, return state + signals."""
    from tfe_epoch_auto_severity import load_live_epochs

    coordinator = G32Coordinator()
    live = load_live_epochs()
    state = coordinator.update(live)

    return {
        "g32_state": state.to_dict(),
        "delta_signal": coordinator.compute_epoch_delta_signal(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    result = evaluate_epoch_environment()
    print(json.dumps(result, indent=2))
