#!/usr/bin/env python3
"""
UF-Core MDG Snapshot Evaluator

Purpose
-------
Single place that turns:
    (symbol, recent market history)
into one UF snapshot row that matches the active snapshot row schema
schema used by TFE pages (Recommendations, etc.).

This module:
    - Uses UF-Core structural engine only (no TA).
    - Uses the same structural adapter as Watchlist / live views.
    - Materializes structural recency fields from published decision lineage.
    - Returns a dict with keys:
        ticker, asset_type, price, regime,
        S_UF, R_UF, stability_score, max_dd,
        decision_vector, D_k, M_k, R_rev_k, U_star_k, C_k, prev_C_k, P_k, B_k,
        bar_count

Intended usage
--------------
Typical integration point is the snapshot rebuild path (e.g. refresh_snapshot_full):

    from uf_mdg_snapshot import evaluate_symbol_snapshot

    row = evaluate_symbol_snapshot("AAPL", asset_type="stock")
    # collect rows and write snapshot envelope payload rows

This file does NOT know anything about Streamlit or UI.
It is purely a governance-aware structural snapshot builder.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

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

from structural_recency_snapshot import (
    build_structural_recency_payload,
    history_metadata_from_bars,
)
from tfe_bar_integrity import DEFAULT_MIN_PRICE_FLOOR, sanitize_daily_bars
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

# Production policy evidence floor:
# decision layer requires this many daily bars before allowing Accumulate.
ACCUMULATE_MIN_BARS: int = 514
RECENT_BAR_LOOKBACK_DAYS: int = 10

# Strict OHLC integrity floor used by production ingestion.
MIN_PRICE_FLOOR: float = DEFAULT_MIN_PRICE_FLOOR


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _fetch_history(
    symbol: str,
    years: int = YEARS_HISTORY,
    client: Optional[Any] = None,
) -> Tuple[List[Bar], Dict[str, int]]:
    """
    Fetch daily OHLCV bars for `symbol` using the unified market data service.

    Production ingestion behavior:
    - Apply strict bar integrity filter via sanitize_daily_bars
      (finite/positive/consistent OHLC + min price floor + timestamp dedupe).
    - Keep only bars with parseable close values after integrity filtering.
    - Return bars sorted by timestamp.
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
    raw_bars: List[Bar] = getattr(result, "bars", []) or []

    cleaned_bars, dropped = sanitize_daily_bars(raw_bars, min_price_floor=MIN_PRICE_FLOOR)

    # Keep only bars with a usable close
    close_clean: List[Bar] = []
    for b in cleaned_bars:
        try:
            close_value = getattr(b, "close", None)
            if close_value is None:
                continue
            float(close_value)
        except Exception:
            continue
        close_clean.append(b)

    close_clean.sort(key=lambda b: b.timestamp)
    return close_clean, dropped


def load_recent_daily_bar_metrics(
    symbol: str,
    client: Optional[Any] = None,
    lookback_days: int = RECENT_BAR_LOOKBACK_DAYS,
) -> Dict[str, Any]:
    if client is None:
        client = get_unified_market_data()

    end = datetime.utcnow()
    start = end - timedelta(days=max(2, int(lookback_days)))

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
    raw_bars: List[Bar] = getattr(result, "bars", []) or []
    cleaned_bars, dropped = sanitize_daily_bars(raw_bars, min_price_floor=MIN_PRICE_FLOOR)

    close_clean: List[Bar] = []
    for bar in cleaned_bars:
        try:
            close_value = getattr(bar, "close", None)
            if close_value is None:
                continue
            float(close_value)
        except Exception:
            continue
        close_clean.append(bar)

    close_clean.sort(key=lambda bar: bar.timestamp)
    latest = close_clean[-1] if close_clean else None
    previous = close_clean[-2] if len(close_clean) >= 2 else None

    latest_close = _safe_optional_float(getattr(latest, "close", None)) if latest is not None else None
    latest_volume = _safe_optional_float(getattr(latest, "volume", None)) if latest is not None else None
    previous_close = _safe_optional_float(getattr(previous, "close", None)) if previous is not None else None
    previous_volume = _safe_optional_float(getattr(previous, "volume", None)) if previous is not None else None

    latest_timestamp = None
    if latest is not None:
        try:
            latest_timestamp = getattr(latest, "timestamp", None)
            if latest_timestamp is not None:
                latest_timestamp = latest_timestamp.isoformat()
        except Exception:
            latest_timestamp = None

    latest_traded_dollar_volume = None
    if latest_close is not None and latest_volume is not None:
        latest_traded_dollar_volume = float(latest_close) * float(latest_volume)

    return {
        "bar_count": len(close_clean),
        "dropped": dropped,
        "latest_close": latest_close,
        "latest_volume": latest_volume,
        "previous_close": previous_close,
        "previous_volume": previous_volume,
        "latest_traded_dollar_volume": latest_traded_dollar_volume,
        "latest_timestamp": latest_timestamp,
    }


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_vector_value(vector: List[float], index: int, default: float = 0.0) -> float:
    if index < 0 or index >= len(vector):
        return float(default)
    try:
        return float(vector[index])
    except Exception:
        return float(default)


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
    A dict with the same row fields used in the snapshot envelope payload, plus bar_count.

    Notes
    -----
    - NO TA is computed here; everything comes from UF-Core structural fields.
    - Structural recency fields are materialized from published decision lineage,
      not from request-time heuristics.
    - This function is deliberately small so it can be called from
      refresh_snapshot_full without dragging in any Streamlit / UI code.
    """
    bars, dropped = _fetch_history(symbol, years=years_history, client=client)
    bar_count = len(bars)
    history_meta = history_metadata_from_bars(bars)

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
            "D_k": 0.0,
            "M_k": 0.0,
            "R_rev_k": 0.0,
            "U_star_k": 0.0,
            "C_k": 0.0,
            "prev_C_k": None,
            "P_k": 0.0,
            "B_k": 0.0,
            "bar_count": 0,
            "gate_count": 0,
            "active_gate_count": 0,
            "decision_guard": {"gate_unlock_transient_neutralized": False},
            "integrity_dropped": dropped,
            "history_available_steps": int(history_meta["history_available_steps"]),
            "ts_gap_days_from_prev": float(history_meta["ts_gap_days_from_prev"]),
            "structural_recency_schema_version": "v1",
            "steps_since_regime_change": 0,
            "steps_since_pattern_change": 0,
            "steps_since_reversal_sign_flip": -1,
            "D_steps_since_sign_flip": -1,
            "M_steps_since_sign_flip": -1,
            "R_rev_steps_since_sign_flip": -1,
            "U_star_steps_since_sign_flip": -1,
            "C_steps_since_sign_flip": -1,
            "P_steps_since_sign_flip": -1,
            "B_steps_since_sign_flip": -1,
            "S_UF_steps_since_sign_flip": -1,
            "R_UF_steps_since_sign_flip": -1,
        }

    # Use the same structural adapter as Watchlist and other TFE pages.
    state = compute_structural_state(symbol, bars)

    # Defensive extraction of fields
    last_close = _safe_float(state.get("last_close"), float("nan"))
    regime = str(state.get("regime", "UNKNOWN"))
    s_uf = _safe_float(state.get("S_UF"), 0.0)
    r_uf = _safe_float(state.get("R_UF"), 0.0)
    stability_score = _safe_float(state.get("stability_score"), 0.0)
    max_dd = _safe_float(state.get("max_drawdown"), 0.0)

    decision_vector = _pad_decision_vector(state.get("decision_vector"))
    d_k = _safe_optional_float(state.get("D_k"))
    m_k = _safe_optional_float(state.get("M_k"))
    r_rev_k = _safe_optional_float(state.get("R_rev_k"))
    u_star_k = _safe_optional_float(state.get("U_star_k"))
    c_k = _safe_optional_float(state.get("C_k"))
    prev_c_k = _safe_optional_float(state.get("prev_C_k"))
    p_k = _safe_optional_float(state.get("P_k"))
    b_k = _safe_optional_float(state.get("B_k"))

    # Keep L4 basis complete for downstream strict checks; low-data rows are
    # decision-gated to Hold by bar-count policy in the recommendation layer.
    if d_k is None:
        d_k = _safe_vector_value(decision_vector, 0, 0.0)
    if m_k is None:
        m_k = _safe_vector_value(decision_vector, 1, 0.0)
    if r_rev_k is None:
        r_rev_k = _safe_vector_value(decision_vector, 2, 0.0)
    if u_star_k is None:
        u_star_k = _safe_vector_value(decision_vector, 3, 0.0)
    if c_k is None:
        c_k = 0.0
    if p_k is None:
        p_k = _safe_vector_value(decision_vector, 4, 0.0)
    if b_k is None:
        b_k = _safe_vector_value(decision_vector, 5, 0.0)

    gate_count = _safe_int(state.get("gate_count"), 0)
    active_gate_count = _safe_int(state.get("active_gate_count"), 0)

    decision_guard_raw = state.get("decision_guard", {})
    decision_guard = decision_guard_raw if isinstance(decision_guard_raw, dict) else {}

    row: Dict[str, Any] = {
        "ticker": symbol,
        "asset_type": asset_type,
        "price": last_close,
        "regime": regime,
        "S_UF": s_uf,
        "R_UF": r_uf,
        "stability_score": stability_score,
        "max_dd": max_dd,
        "decision_vector": decision_vector,
        "D_k": d_k,
        "M_k": m_k,
        "R_rev_k": r_rev_k,
        "U_star_k": u_star_k,
        "C_k": c_k,
        "prev_C_k": prev_c_k,
        "P_k": p_k,
        "B_k": b_k,
        "bar_count": int(bar_count),
        "gate_count": gate_count,
        "active_gate_count": active_gate_count,
        "decision_guard": decision_guard,
        "integrity_dropped": dropped,
    }
    row.update(
        build_structural_recency_payload(
            symbol=symbol,
            current_state=row,
            history_available_steps=int(history_meta["history_available_steps"]),
            ts_gap_days_from_prev=float(history_meta["ts_gap_days_from_prev"]),
        )
    )

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
    import json as _json
    import sys

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
