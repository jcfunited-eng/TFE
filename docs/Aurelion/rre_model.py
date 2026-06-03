"""
rre_model.py — Core Relational Resonance Engine (RRE)
-----------------------------------------------------
Implements the base model used by Aurelion and other modules.

Features
- Exponential moving averages (multi-scale)
- Non-numeric relational evaluation (sign coherence)
- Resonance smoothing via Λα (lambda-alpha)
- Transaction cost variance overlay
- Backtesting framework for signal-to-decision pipeline
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict

# =========================================================
# Configuration Dataclass
# =========================================================

@dataclass
class RREConfig:
    ema_windows: list = (5, 20, 60)
    alpha: float = 0.6
    resonance_threshold: float = 0.15
    transaction_cost_bps: float = 1.0
    allow_short: bool = True
    drawdown_brake: float = 0.25


# =========================================================
# Core Model Class
# =========================================================

class RRE:
    def __init__(self, config=None):
        self.cfg = config or RREConfig()

    # -----------------------------------------------------
    # Compute exponential moving averages (multi-scale)
    # -----------------------------------------------------
    def compute_emas(self, series: pd.Series) -> pd.DataFrame:
        df = pd.DataFrame(index=series.index)
        for w in self.cfg.ema_windows:
            df[f"ema_{w}"] = series.ewm(span=w, adjust=False).mean()
        return df

    # -----------------------------------------------------
    # Relational coherence measure φ
    # -----------------------------------------------------
    def compute_phi(self, ema_df: pd.DataFrame) -> pd.Series:
        diff_signs = np.sign(ema_df.diff()).fillna(0)
        coherence = diff_signs.mean(axis=1)
        phi = coherence.ewm(alpha=self.cfg.alpha).mean()
        return phi.clip(-1, 1)

    # -----------------------------------------------------
    # Decision logic — converts φ to trading or activation signal
    # -----------------------------------------------------
    def decide_positions(self, phi: pd.Series) -> pd.Series:
        thr = self.cfg.resonance_threshold
        if self.cfg.allow_short:
            pos = np.where(phi > thr, 1, np.where(phi < -thr, -1, 0))
        else:
            pos = np.where(phi > thr, 1, 0)
        return pd.Series(pos, index=phi.index)

    # -----------------------------------------------------
    # Backtesting pipeline
    # -----------------------------------------------------
    def backtest(self, price_series: pd.Series, costs_bps=None) -> pd.DataFrame:
        costs = (costs_bps or self.cfg.transaction_cost_bps) / 10000.0

        emas = self.compute_emas(price_series)
        phi = self.compute_phi(emas)
        positions = self.decide_positions(phi)

        rets = price_series.pct_change().fillna(0)
        strat = positions.shift(1) * rets - costs * (positions.diff().abs().fillna(0))

        eq = (1 + strat).cumprod()
        drawdown = (eq / eq.cummax() - 1)
        eq[drawdown < -self.cfg.drawdown_brake] = np.nan

        df = pd.DataFrame({
            "price": price_series,
            "phi": phi,
            "pos": positions,
            "equity": eq,
            "drawdown": drawdown
        })
        return df

    # -----------------------------------------------------
    # Utility loader
    # -----------------------------------------------------
    @staticmethod
    def load_price_from_csv(path: str) -> pd.Series:
        df = pd.read_csv(path)
        cols = [c for c in df.columns if any(x in c.lower() for x in ["close", "price", "value"])]
        if not cols:
            raise ValueError("No price column found in CSV.")
        series = pd.to_numeric(df[cols[0]], errors="coerce").dropna()
        series.index = pd.RangeIndex(len(series))
        return series

# =========================================================
# Example usage
# =========================================================

if __name__ == "__main__":
    print("RRE model module loaded. Run via aurelion_interface.py for interactive use.")
