#!/usr/bin/env python3
"""
UF-Core MDG Snapshot Evaluator

Purpose
-------
Single place that turns:
    (symbol, recent market history)
into one UF snapshot row that matches the existing uf_snapshot.json
schema used by TFE pages (Recommendations, etc.).

This module:
    - Uses UF-Core structural engine only (no TA).
    - Uses the same structural adapter as Watchlist / live views.
    - Returns a dict with keys:
        ticker, asset_type, price, regime,
        S_UF, R_UF, stability_score, max_dd, decision_vector

Intended usage
--------------
Typical integration point is the snapshot rebuild path (e.g. refresh_snapshot_full):

    from uf_mdg_snapshot import evaluate_symbol_snapshot

    row = evaluate_symbol_snapshot("AAPL", asset_type="stock")
    # collect rows and write uf_snapshot.json

This file does NOT know anything about Streamlit or UI.
It is purely a governance-aware structural snapshot builder.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import math

# ----------------------------------------------------------------------
# Data layer imports
# ----------------------------------------------------------------------
# We follow the same pattern as the other TFE scripts:
# - Prefer tfe_market_data if present.
# - Fallback to unified_market_data_service if this is run standalone.

try:
    # TFE-local wrapper (used by Portfolio, Watchlist, etc.)
    from tfe_market_data import get_unified_market_data  # type: ignore
except ModuleNotFoundError:
    # Direct UF/TFE data service
    from unified_market_data_service import get_unified_market_data  # type: ignore

from tfe_market_data_service import Bar, HistoryRequest, Timespan  # type: ignore

# ----------------------------------------------------------------------
# UF-Core structural engine import
# ----------------------------------------------------------------------
# Same adapter used by Watchlist and other TFE pages.

try:
    # Package-style import
    from uf_core.uf_structural_engine import compute_structural_state  # type: ignore
except ModuleNotFoundError:
    # Flat module-style import
    from uf_structural_engine import compute_structural_state  # type: ignore


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# How much history we give UF-Core for a snapshot evaluation.
YEARS_HISTORY: int = 5


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _fetch_history(
    symbol: str,
    years: int = YEARS_HISTORY,
    client: Optional[Any] = None,
) -> List[Bar]:
    """
    Fetch daily OHLCV bars for `symbol` using the unified market data service.

    This is the same shape as used in the backtest scripts and Watchlist:
    - Bars are sorted by timestamp.
    - Only bars with a valid `close` are kept.
    """
    if client is None:
        client = get_unified_market_data()

    end = datetime.utcnow()
    start = end - timedelta(days=years * 365)

    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start,
        end=end,
        adjusted=True,
        limit=None,
    )

    result = client.get_history(req)
    bars: List[Bar] = getattr(result, "bars", []) or []

    # Keep only bars with a usable close
    clean: List[Bar] = []
    for b in bars:
        try:
            c = getattr(b, "close", None)
        except Exception:
            c = None
        if c is None:
            continue
        try:
            _ = float(c)
        except Exception:
            continue
        clean.append(b)

    clean.sort(key=lambda b: b.timestamp)
    return clean


def _pad_decision_vector(raw_dv: Any, length: int = 6) -> List[float]:
    """
    Normalize the decision_vector so that:
        - It is always a list[float] of fixed length (default 6).
        - Missing values are padded with 0.0.
        - Extra values are truncated.
    """
    if raw_dv is None:
        return [0.0] * length

    try:
        dv = list(raw_dv)
    except Exception:
        return [0.0] * length

    if len(dv) < length:
        dv = dv + [0.0] * (length - len(dv))
    elif len(dv) > length:
        dv = dv[:length]

    out: List[float] = []
    for x in dv:
        try:
            out.append(float(x))
        except Exception:
            out.append(0.0)
    return out


# ----------------------------------------------------------------------
# Public API: single-row UF snapshot evaluator
# ----------------------------------------------------------------------

def evaluate_symbol_snapshot(
    symbol: str,
    asset_type: str = "stock",
    years_history: int = YEARS_HISTORY,
    client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Compute a UF-Core + MDG snapshot row for one symbol.

    Inputs
    ------
    symbol      : ticker symbol (e.g. "AAPL", "SPY", "BTC-USD")
    asset_type  : semantic label used by TFE snapshot:
                    "stock", "etf", "index", "crypto", ...
                  For now, callers typically pass "stock" for equities/ETFs,
                  "index" for indices, "crypto" for BTC-USD, etc.
    years_history : number of years of daily bars to use.
    client      : optional unified market data client; if None, a new one
                  is obtained via get_unified_market_data().

    Output
    ------
    A dict with the same fields used in uf_snapshot.json:

        {
            "ticker": "AAPL",
            "asset_type": "stock",
            "price": 186.88,
            "regime": "TRANSITIONAL",
            "S_UF": 0.73,
            "R_UF": 0.81,
            "stability_score": 0.62,
            "max_dd": -0.24,
            "decision_vector": [D, M, R_rev, U*, P, B],
        }

    Notes
    -----
    - NO TA is computed here; everything comes from UF-Core structural fields.
    - This function is deliberately small so it can be called from
      refresh_snapshot_full without dragging in any Streamlit / UI code.
    """
    bars = _fetch_history(symbol, years=years_history, client=client)

    # If we truly have no usable data, still return a row so the UI doesn't break.
    if not bars:
        return {
            "ticker": symbol,
            "asset_type": asset_type,
            "price": float("nan"),
            "regime": "NO_DATA",
            "S_UF": 0.0,
            "R_UF": 0.0,
            "stability_score": 0.0,
            "max_dd": 0.0,
            "decision_vector": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        }

    # Use the same structural adapter as Watchlist and other TFE pages.
    state = compute_structural_state(symbol, bars)

    # Defensive extraction of fields
    try:
        last_close = float(state.get("last_close", float("nan")))
    except Exception:
        last_close = float("nan")

    regime = str(state.get("regime", "UNKNOWN"))

    try:
        S_UF = float(state.get("S_UF", 0.0))
    except Exception:
        S_UF = 0.0

    try:
        R_UF = float(state.get("R_UF", 0.0))
    except Exception:
        R_UF = 0.0

    try:
        stability_score = float(state.get("stability_score", 0.0))
    except Exception:
        stability_score = 0.0

    try:
        max_dd = float(state.get("max_drawdown", 0.0))
    except Exception:
        max_dd = 0.0

    decision_vector = _pad_decision_vector(state.get("decision_vector"))

    row: Dict[str, Any] = {
        "ticker": symbol,
        "asset_type": asset_type,
        "price": last_close,
        "regime": regime,
        "S_UF": S_UF,
        "R_UF": R_UF,
        "stability_score": stability_score,
        "max_dd": max_dd,
        "decision_vector": decision_vector,
    }

    return row


# ----------------------------------------------------------------------
# Minimal CLI helper (optional)
# ----------------------------------------------------------------------

def _demo_single_ticker() -> None:
    """
    Tiny demo if you run this file directly.

    Example:
        python uf_mdg_snapshot.py AAPL
    """
    import sys
    import json as _json

    if len(sys.argv) < 2:
        print("Usage: python uf_mdg_snapshot.py TICKER [ASSET_TYPE]")
        print("Example: python uf_mdg_snapshot.py AAPL stock")
        return

    ticker = sys.argv[1].upper().strip()
    a_type = sys.argv[2] if len(sys.argv) >= 3 else "stock"

    row = evaluate_symbol_snapshot(ticker, asset_type=a_type)
    print(_json.dumps(row, indent=2, default=str))


if __name__ == "__main__":
    _demo_single_ticker()
