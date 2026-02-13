"""
portfolio_valuation_engine.py
-----------------------------------------
Portfolio Valuation Engine for Tao Financial Engine (TFE)

Corrected version:
  - Fixes .upper() call on Series → .str.upper()
  - Ensures robust handling of dtype conversions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional

import pandas as pd

from tfe_market_data import get_unified_market_data


PORTFOLIO_PATH = "portfolio.csv"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class PositionValuation:
    ticker: str
    quantity: float
    cost_basis: float
    market_price: Optional[float]
    market_value: float
    cost_value: float
    unrealized_pl: float
    pl_pct: float


@dataclass
class PortfolioValuation:
    positions: List[PositionValuation]
    total_cost: float
    total_value: float
    unrealized_pl: float
    pl_pct: float
    weights: Dict[str, float]  # ticker -> fraction of total_value


# ============================================================
# Load Portfolio
# ============================================================

def load_portfolio_df(path: str = PORTFOLIO_PATH) -> pd.DataFrame:
    """
    Load the portfolio CSV and normalize column names.
    """
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"ticker", "quantity", "cost_basis"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"portfolio.csv missing required columns: {', '.join(sorted(missing))}"
        )

    # Optional asset_type column
    if "asset_type" not in df.columns:
        df["asset_type"] = "equity"

    # Corrections ↓↓↓ (the bug fix)
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["quantity"] = df["quantity"].astype(float)
    df["cost_basis"] = df["cost_basis"].astype(float)

    return df


# ============================================================
# Compute Portfolio Valuation
# ============================================================

def compute_portfolio_valuation(df: pd.DataFrame) -> PortfolioValuation:
    mds = get_unified_market_data()

    positions: List[PositionValuation] = []
    total_cost = 0.0
    total_value = 0.0

    for _, row in df.iterrows():
        ticker = str(row["ticker"]).upper()
        qty = float(row["quantity"])
        cost_basis = float(row["cost_basis"])

        # Market price from unified provider (Massive → Alpaca fallback)
        snap = mds.get_snapshot(ticker)
        price = snap.last_price

        cost_val = qty * cost_basis

        # If no price → zero value, full loss (until fixed by crypto support)
        if price is None:
            market_val = 0.0
            unreal = -cost_val
            pl_pct = 0.0
        else:
            market_val = price * qty
            unreal = market_val - cost_val
            pl_pct = (unreal / cost_val * 100) if cost_val > 0 else 0.0

        positions.append(
            PositionValuation(
                ticker=ticker,
                quantity=qty,
                cost_basis=cost_basis,
                market_price=price,
                market_value=market_val,
                cost_value=cost_val,
                unrealized_pl=unreal,
                pl_pct=pl_pct,
            )
        )

        total_cost += cost_val
        total_value += market_val

    unreal_total = total_value - total_cost
    pl_pct_total = (unreal_total / total_cost * 100) if total_cost > 0 else 0.0

    # Weight calculation
    weights = {}
    if total_value > 0:
        for p in positions:
            weights[p.ticker] = p.market_value / total_value
    else:
        for p in positions:
            weights[p.ticker] = 0.0

    return PortfolioValuation(
        positions=positions,
        total_cost=total_cost,
        total_value=total_value,
        unrealized_pl=unreal_total,
        pl_pct=pl_pct_total,
        weights=weights,
    )
