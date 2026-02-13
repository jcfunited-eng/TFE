"""
1_Dashboard.py

TFE Portfolio Dashboard

- Uses live SES/TFE portfolio via tfe_portfolio_api.
- Summarizes portfolio value and weights.
- Overlays UF snapshot metrics for current holdings.
- No TA logic. UF-Core math is not modified.
"""

from __future__ import annotations

import math
from typing import Dict, Any, List

import pandas as pd
import streamlit as st

from tfe_portfolio_api import get_portfolio_df, get_portfolio_valuation
from uf_snapshot_cache import load_snapshot


st.set_page_config(layout="wide")
st.title("Dashboard")


# ------------------------------------------------------------
# Load portfolio
# ------------------------------------------------------------
portfolio_df = get_portfolio_df()

if portfolio_df is None or portfolio_df.empty:
    st.warning(
        "Your portfolio is empty. Use **Portfolio Manager** to add positions."
    )
    st.stop()

portfolio_df = portfolio_df.copy()
portfolio_df["ticker"] = portfolio_df["ticker"].astype(str).str.upper()

# ------------------------------------------------------------
# Live valuation snapshot
# ------------------------------------------------------------
valuation = get_portfolio_valuation()
if valuation is None:
    st.error("Unable to compute portfolio valuation.")
    st.stop()

total_value = float(getattr(valuation, "total_value", 0.0) or 0.0)
unrealized_pl = float(getattr(valuation, "unrealized_pl", 0.0) or 0.0)
pl_pct = float(getattr(valuation, "pl_pct", 0.0) or 0.0)
weights: Dict[str, float] = getattr(valuation, "weights", {}) or {}

# Normalize tickers to uppercase
weights = {str(t).upper(): float(w or 0.0) for t, w in weights.items()}

num_positions = len(weights)


# ------------------------------------------------------------
# Top-level metrics (Finviz-style header)
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("Portfolio Value", f"${total_value:,.2f}")
col2.metric("Unrealized P/L", f"${unrealized_pl:,.2f}")
col3.metric("Unrealized P/L %", f"{pl_pct * 100:.2f}%")
col4.metric("Positions", f"{num_positions:d}")


# ------------------------------------------------------------
# Build holdings table (joins portfolio + weights)
# ------------------------------------------------------------
rows: List[Dict[str, Any]] = []

for ticker, w in sorted(weights.items(), key=lambda kv: kv[1], reverse=True):
    row = portfolio_df.loc[portfolio_df["ticker"] == ticker]
    if row.empty:
        continue

    qty = float(row["quantity"].iloc[0] or 0.0)
    cost_basis = float(row["cost_basis"].iloc[0] or 0.0)
    asset_type = (
        str(row["asset_type"].iloc[0])
        if "asset_type" in row.columns
        else "stock"
    )

    weight_val = float(w or 0.0)
    position_value = total_value * weight_val if total_value > 0 else 0.0
    cost_value = qty * cost_basis
    pl = position_value - cost_value
    pl_pct_pos = pl / cost_value if cost_value > 0 else 0.0
    price_implied = (
        position_value / qty if qty > 0 else math.nan
    )

    rows.append(
        {
            "Ticker": ticker,
            "Asset Type": asset_type,
            "Quantity": qty,
            "Implied Price": price_implied,
            "Market Value": position_value,
            "Cost Basis Value": cost_value,
            "Unrealized P/L": pl,
            "Unrealized P/L %": pl_pct_pos * 100.0,
            "Weight %": weight_val * 100.0,
        }
    )

holdings_df = pd.DataFrame(rows)

if holdings_df.empty:
    st.warning("No valued positions found in portfolio.")
    st.stop()

# Sort by weight descending
holdings_df = holdings_df.sort_values("Weight %", ascending=False).reset_index(
    drop=True
)


# ------------------------------------------------------------
# Allocation by ticker and asset type
# ------------------------------------------------------------
st.markdown("### Portfolio Overview")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Top Holdings")
    st.dataframe(
        holdings_df.head(25),
        width="stretch",
    )

with col_right:
    st.subheader("Allocation by Ticker")
    st.bar_chart(
        holdings_df.set_index("Ticker")["Weight %"].head(15)
    )

    # Merge asset_type from portfolio_df
    merged = holdings_df.merge(
        portfolio_df[["ticker", "asset_type"]],
        left_on="Ticker",
        right_on="ticker",
        how="left",
    )
    merged["asset_type"] = merged["asset_type"].fillna("unknown")

    alloc_by_type = (
        merged.groupby("asset_type")["Weight %"]
        .sum()
        .sort_values(ascending=False)
    )

    st.subheader("Allocation by Asset Type")
    st.bar_chart(alloc_by_type)


# ------------------------------------------------------------
# UF structural overlay for current holdings
# ------------------------------------------------------------
st.markdown("### UF Structural Snapshot for Portfolio")

snapshot_rows = load_snapshot()
if not snapshot_rows:
    st.info("No UF snapshot found. Run a UF snapshot rebuild from the **Recommendations** page.")
else:
    snap_df = pd.DataFrame(snapshot_rows)
    if "ticker" in snap_df.columns:
        snap_df["ticker"] = snap_df["ticker"].astype(str).str.upper()

        structural_cols = [
            "ticker",
            "regime",
            "S_UF",
            "R_UF",
            "stability_score",
            "max_dd",
        ]
        for c in structural_cols:
            if c not in snap_df.columns:
                snap_df[c] = None

        uf_view = holdings_df.merge(
            snap_df[structural_cols],
            left_on="Ticker",
            right_on="ticker",
            how="left",
        )

        uf_view = uf_view.drop(columns=["ticker"])

        # Keep a compact, informative subset of columns
        display_cols = [
            "Ticker",
            "Weight %",
            "Market Value",
            "regime",
            "S_UF",
            "R_UF",
            "stability_score",
            "max_dd",
        ]

        st.dataframe(
            uf_view[display_cols].head(25),
            width="stretch",
        )
    else:
        st.warning("UF snapshot is missing the 'ticker' field; unable to join.")
