"""
3_Watchlist.py

UF-Core Watchlist (live evaluation)

Features:
- Add/remove symbols to watchlist.csv
- On page load:
    * Load watchlist symbols
    * Fetch recent history via unified market data
    * Call UF-Core compute_structural_state(symbol, bars)
    * Classify BUY / HOLD / SELL from decision_vector + S_UF/R_UF
    * Display structural metrics + price and small history chart
"""

from __future__ import annotations

import datetime
import os
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

from tfe_market_data import get_unified_market_data
from tfe_market_data_service import HistoryRequest, Timespan
from uf_core.uf_structural_engine import compute_structural_state

WATCHLIST_FILE = "watchlist.csv"


# ------------------------------------------------------------
# Helpers for CSV persistence
# ------------------------------------------------------------
def load_watchlist() -> List[str]:
    if not os.path.exists(WATCHLIST_FILE):
        return []
    try:
        df = pd.read_csv(WATCHLIST_FILE)
        return df["symbol"].dropna().astype(str).str.upper().unique().tolist()
    except Exception:
        return []


def save_watchlist(symbols: List[str]) -> None:
    df = pd.DataFrame({"symbol": sorted(set(symbols))})
    df.to_csv(WATCHLIST_FILE, index=False)


# ------------------------------------------------------------
# UF-Core based classification
# ------------------------------------------------------------
def classify_from_state(state: Dict[str, Any]) -> str:
    dv = state.get("decision_vector") or []
    if len(dv) < 6:
        return "HOLD"

    D_k, M_k, R_rev_k, U_star_k, P_k, B_k = dv
    S_UF = float(state.get("S_UF") or 0.0)
    R_UF = float(state.get("R_UF") or 0.0)
    regime = str(state.get("regime") or "UNKNOWN")

    # Simple structural rules; no TA:
    # - BUY: strong structure, favorable direction, low uncertainty
    if (
        D_k < 0
        and S_UF >= 0.6
        and R_UF >= 0.5
        and U_star_k <= 0.4
        and regime not in ("DEGENERATE", "INSUFFICIENT_DATA")
    ):
        return "BUY"

    # - SELL: weak structure, adverse direction, high uncertainty
    if (
        D_k > 0
        and (S_UF <= 0.4 or R_UF <= 0.3)
        and U_star_k >= 0.6
    ):
        return "SELL"

    # Otherwise HOLD
    return "HOLD"


# ------------------------------------------------------------
# Page UI
# ------------------------------------------------------------
st.title("Watchlist")

symbols = load_watchlist()
symbols = [s for s in symbols if s]  # clean

# Add symbol
st.subheader("Manage Watchlist")

col1, col2 = st.columns([3, 1])
with col1:
    new_symbol = st.text_input("Add symbol (e.g. AAPL, SPX, X:BTCUSD)").strip().upper()
with col2:
    if st.button("Add"):
        if new_symbol:
            if new_symbol not in symbols:
                symbols.append(new_symbol)
                save_watchlist(symbols)
                st.success(f"Added {new_symbol} to watchlist.")
            else:
                st.info(f"{new_symbol} already in watchlist.")
        else:
            st.warning("Please enter a symbol before adding.")

# Remove symbol(s)
if symbols:
    remove_sel = st.multiselect("Remove selected symbols", symbols)
    if st.button("Remove selected"):
        if remove_sel:
            symbols = [s for s in symbols if s not in remove_sel]
            save_watchlist(symbols)
            st.success(f"Removed {', '.join(remove_sel)}.")
        else:
            st.info("No symbols selected to remove.")

if not symbols:
    st.info("Your watchlist is currently empty.")
    st.stop()

# ------------------------------------------------------------
# Live UF-Core evaluation
# ------------------------------------------------------------
st.subheader("Live UF Structural Evaluation")

mds = get_unified_market_data()

lookback_days = st.slider("History window (days)", 60, 730, 365)

rows: List[Dict[str, Any]] = []
history_map: Dict[str, pd.DataFrame] = {}

for sym in symbols:
    end = datetime.date.today()
    start = end - datetime.timedelta(days=int(lookback_days))

    req = HistoryRequest(
        symbol=sym,
        multiplier=1,
        timespan=Timespan.DAY,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )

    try:
        hist = mds.get_history(req)
        bars = hist.bars
    except Exception as exc:
        st.warning(f"{sym}: error fetching history: {exc}")
        continue

    if len(bars) < 30:
        st.warning(f"{sym}: too few bars ({len(bars)}); skipping UF evaluation.")
        continue

    # UF-Core structural state
    try:
        state = compute_structural_state(sym, bars)
    except Exception as exc:
        st.warning(f"{sym}: UF-Core evaluation failed: {exc}")
        continue

    classification = classify_from_state(state)

    rows.append(
        {
            "ticker": sym,
            "classification": classification,
            "price": state.get("last_close"),
            "regime": state.get("regime"),
            "S_UF": state.get("S_UF"),
            "R_UF": state.get("R_UF"),
            "stability_score": state.get("stability_score"),
            "max_dd": state.get("max_drawdown"),
        }
    )

    # save simple history df for charting
    df_hist = pd.DataFrame(
        [{"time": b.t, "close": b.c} for b in bars]
    )
    history_map[sym] = df_hist

if not rows:
    st.info("No symbols yielded valid UF evaluation.")
    st.stop()

st.dataframe(rows, width=900)

# ------------------------------------------------------------
# Single-symbol chart
# ------------------------------------------------------------
st.subheader("Price History")

sym_pick = st.selectbox("Pick a symbol to chart", [r["ticker"] for r in rows])

if sym_pick and sym_pick in history_map:
    df_hist = history_map[sym_pick]
    st.line_chart(df_hist.set_index("time"))
