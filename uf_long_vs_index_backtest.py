#!/usr/bin/env python3
"""
UF-Core Long-Only vs Index Portfolio Backtest

Goal:
    Compare a simple UF-driven long-only portfolio against an S&P500 proxy
    over the same ~5-year period using the same TFE data layer.

Key properties:
    - Universe: S&P500 symbols from sp500.csv (no header, one symbol per line).
    - Engine: UF-Core L0–L4 + aggregation ONLY.
      NO Hardening / NO SafeMode controllers.
    - Trades:
        * Use BUY signals only (D_k > 0).
        * Require S_UF >= S_UF_MIN_FOR_TRADE.
        * Horizon H = 40 daily bars (~2 months).
        * Non-overlapping per price bucket (high/mid/low) for capital.
    - Costs:
        * Simple round-trip trading cost COST_RATE applied per trade:
              net_return = forward_return - COST_RATE
          (COST_RATE = 0.002 → 0.2% per trade).
    - Portfolio:
        * Initial capital = 10,000.
        * Split: 4,000 high-price, 3,000 mid-price, 3,000 low-price.
        * Each bucket can only have ONE active trade at a time.
        * Trades executed sequentially as they appear in time, skipping overlaps.
    - Index:
        * Symbol INDEX_SYMBOL = "SPY" (can be changed if needed).
        * Uses the same TFE data layer.
        * Buy-and-hold:
              index_shares = 10,000 / index_price_at_first_trade
              index_value_t = index_shares * index_price_at_time_t
    - Output:
        * Number of trades used per bucket.
        * Final capital per bucket and total.
        * Final index value for the same time span.
        * Simple equity curve samples: portfolio vs index at each UF trade exit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, DefaultDict
from collections import defaultdict
import math

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

SP500_CSV_PATH: str = "sp500.csv"
INDEX_SYMBOL: str = "SPY"  # S&P500 proxy ETF; change if needed.

YEARS_HISTORY: int = 5
MIN_BARS_STRUCTURAL: int = 10
S_UF_MIN_FOR_TRADE: float = 0.30

HORIZON: int = 40  # portfolio trade horizon (bars)

# Portfolio initial capital split
PORTFOLIO_INIT_HIGH: float = 4000.0
PORTFOLIO_INIT_MID: float = 3000.0
PORTFOLIO_INIT_LOW: float = 3000.0

TOTAL_INIT_CAPITAL: float = (
    PORTFOLIO_INIT_HIGH + PORTFOLIO_INIT_MID + PORTFOLIO_INIT_LOW
)

# Simple round-trip trading cost (e.g. 0.002 = 0.2% per trade)
COST_RATE: float = 0.002


# ------------------------------------------------------------------------
# Imports from UF-Core and TFE
# ------------------------------------------------------------------------

from uf_core.layer0 import compute_sev_series, SEV
from uf_core.layer1 import segment_gates, Gate
from uf_core.layer2 import interpret_gates, GateInterpretation
from uf_core.layer3 import compute_resonance, ResonanceResult
from uf_core.layer4 import (
    compute_directional_signal,
    compute_dsf,
    DecisionState,
    DSF,
)

try:
    from uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )
except ModuleNotFoundError:
    # If uf_core is packaged differently; adjust import path if needed.
    from uf_core.uf_structural_engine import (  # type: ignore
        _safe_pct_change,
        _max_drawdown,
        _compute_basic_features,
        _compute_trend_curvature,
        _aggregate_gate_regime,
        _compute_stability_from_l4,
    )

from unified_market_data_service import get_unified_market_data
from tfe_market_data_service import Bar, HistoryRequest, Timespan


# ------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------

def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, float(x))))


def _safe_avg(total: float, count: int) -> float:
    return float(total / count) if count > 0 else 0.0


def _load_sp500_symbols(path: str) -> List[str]:
    """
    Load S&P500 symbols from CSV with:
        - no header
        - one symbol per line
    """
    try:
        df = pd.read_csv(path, header=None)
    except Exception as exc:
        print(f"ERROR: could not load S&P 500 symbols from '{path}': {exc}")
        return []

    if df.empty:
        print(f"ERROR: file '{path}' is empty or has no rows.")
        return []

    raw = df.iloc[:, 0].tolist()
    syms: List[str] = []
    for x in raw:
        if isinstance(x, str):
            s = x.strip().upper()
        else:
            try:
                s = str(x).strip().upper()
            except Exception:
                continue
        if not s:
            continue
        syms.append(s)

    syms = sorted(set(syms))
    if not syms:
        print(f"ERROR: no valid symbols extracted from '{path}'.")
    return syms


def _bucket_price(price: float, q1: float, q2: float) -> str:
    if math.isnan(price):
        return "Price_mid"
    if q1 == q2:
        return "Price_mid"
    if price < q1:
        return "Price_low"
    if price < q2:
        return "Price_mid"
    return "Price_high"


# ------------------------------------------------------------------------
# Data access
# ------------------------------------------------------------------------

def _fetch_history(symbol: str, years: int = YEARS_HISTORY) -> List[Bar]:
    """
    Use unified TFE data layer to fetch daily OHLCV bars.
    """
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
    return sorted(bars, key=lambda b: b.timestamp)


# ------------------------------------------------------------------------
# UF-Core evaluation: raw L0–L4 only
# ------------------------------------------------------------------------

def compute_raw_uf_state(close: pd.Series) -> Dict[str, Any]:
    """
    Compute UF-Core structural state (L0–L4 + simple aggregation) for a close series,
    NO Hardening / SafeMode.
    """
    close = close.dropna().astype(float)
    n = len(close)
    if n < MIN_BARS_STRUCTURAL:
        return {
            "n_bars": float(n),
            "level1": {"n": float(n), "vol": 0.0, "avg_return": 0.0, "price_range": 0.0},
            "level2": {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0},
            "regime": "INSUFFICIENT_DATA",
            "S_UF": 0.0,
            "R_UF": 0.0,
            "stability_score": 0.0,
            "max_drawdown": 0.0,
            "num_gates": 0,
            "decision_vector": [],
            "sev_list": [],
            "gates": [],
            "interpretations": [],
            "resonance_results": [],
            "decision_states": [],
            "dsf_list": [],
        }

    df = pd.DataFrame({"Close": close})

    sev_list: List[SEV] = compute_sev_series(df, field_col="Close")
    gates: List[Gate] = segment_gates(sev_list)
    interpretations: List[GateInterpretation] = interpret_gates(sev_list, gates)
    resonance_results: List[ResonanceResult] = compute_resonance(interpretations)
    decision_states: List[DecisionState] = compute_directional_signal(resonance_results)
    dsf_list: List[DSF] = compute_dsf(decision_states)

    regime: str = _aggregate_gate_regime(interpretations)
    level1: Dict[str, float] = _compute_basic_features(close)
    level2: Dict[str, float] = _compute_trend_curvature(close)

    returns = _safe_pct_change(close)
    max_dd: float = _max_drawdown(returns)

    stab = _compute_stability_from_l4(resonance_results, decision_states)
    dsf_stab = float(stab.get("dsf", 0.0))
    directional_stab = float(stab.get("directional", 0.0))
    R_mean = float(stab.get("R_mean", 0.0))

    S_UF = _clamp01(0.5 * dsf_stab + 0.5 * directional_stab)
    R_UF = _clamp01(R_mean)
    stability_score = _clamp01(
        0.5 * dsf_stab + 0.3 * directional_stab - 2.0 * abs(max_dd)
    )

    if dsf_list:
        last = dsf_list[-1]
        decision_vector = [
            float(last.D_k),
            float(last.M_k),
            float(last.R_rev_k),
            float(last.U_star_k),
            float(last.P_k),
            float(last.B_k),
        ]
    else:
        decision_vector = []

    return {
        "n_bars": float(n),
        "level1": level1,
        "level2": level2,
        "regime": regime,
        "S_UF": S_UF,
        "R_UF": R_UF,
        "stability_score": stability_score,
        "max_drawdown": float(max_dd),
        "num_gates": len(gates),
        "decision_vector": decision_vector,
        "sev_list": sev_list,
        "gates": gates,
        "interpretations": interpretations,
        "resonance_results": resonance_results,
        "decision_states": decision_states,
        "dsf_list": dsf_list,
    }


# ------------------------------------------------------------------------
# Trade record definition
# ------------------------------------------------------------------------

@dataclass
class Trade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    forward_return: float
    net_return: float
    price_bucket: str


# ------------------------------------------------------------------------
# Build UF long-only trades for the universe
# ------------------------------------------------------------------------

def build_long_trades() -> Tuple[List[Trade], float, float]:
    """
    Build a list of long-only trades (D_k>0, S_UF>=threshold) at HORIZON bars
    across all SP500 symbols, and compute price quantiles for bucket assignment.
    """
    symbols = _load_sp500_symbols(SP500_CSV_PATH)
    if not symbols:
        print("No symbols loaded from sp500.csv; aborting.")
        return [], 0.0, 0.0

    print("UF-Core Long-only Trade Generation")
    print(f"Universe: {len(symbols)} symbols from {SP500_CSV_PATH}")
    print(f"Horizon: H={HORIZON} bars, S_UF_MIN_FOR_TRADE={S_UF_MIN_FOR_TRADE:.2f}")
    print("-" * 120)

    trades: List[Trade] = []
    all_entry_prices: List[float] = []

    for symbol in symbols:
        try:
            bars = _fetch_history(symbol)
            if not bars:
                print(f"{symbol:8s} NO_DATA")
                continue

            n = len(bars)
            closes = np.array([float(b.close) for b in bars], dtype=float)
            times = [b.timestamp for b in bars]

            if n < MIN_BARS_STRUCTURAL + HORIZON:
                print(f"{symbol:8s} INSUFFICIENT_BARS n={n}")
                continue

            evals = 0
            usable = 0
            trades_symbol = 0

            max_eval_index = n - HORIZON - 1

            for idx in range(max_eval_index + 1):
                if idx + 1 < MIN_BARS_STRUCTURAL:
                    continue

                close_window = pd.Series(closes[: idx + 1], index=times[: idx + 1])
                state = compute_raw_uf_state(close_window)
                evals += 1

                if int(state.get("num_gates", 0)) <= 0:
                    continue

                S_val = float(state.get("S_UF", 0.0))
                if S_val < S_UF_MIN_FOR_TRADE:
                    continue

                dv = state.get("decision_vector", [])
                if not dv or len(dv) < 1:
                    continue

                D_val = float(dv[0])
                if D_val <= 0.0:  # BUY signals only
                    continue

                usable += 1

                entry_time = times[idx]
                entry_price = closes[idx]
                if entry_price <= 0.0 or math.isnan(entry_price):
                    continue

                exit_index = idx + HORIZON
                if exit_index >= n:
                    continue

                exit_price = closes[exit_index]
                if exit_price <= 0.0 or math.isnan(exit_price):
                    continue

                forward_ret = float(exit_price / entry_price - 1.0)
                net_ret = forward_ret - COST_RATE  # apply cost

                trade = Trade(
                    symbol=symbol,
                    entry_time=entry_time,
                    exit_time=times[exit_index],
                    entry_price=float(entry_price),
                    forward_return=forward_ret,
                    net_return=net_ret,
                    price_bucket="",  # filled later
                )
                trades.append(trade)
                trades_symbol += 1
                all_entry_prices.append(float(entry_price))

            print(
                f"{symbol:8s} n_bars={n:4d} evals={evals:4d} usable={usable:4d} "
                f"long_trades={trades_symbol:4d}"
            )

        except Exception as exc:
            print(f"{symbol:8s} ERROR: {exc}")

    print("-" * 120)
    print(f"TOTAL raw long trades (before bucketing, before non-overlap): {len(trades)}")

    if not all_entry_prices:
        return trades, 0.0, 0.0

    P_q1, P_q2 = np.quantile(np.array(all_entry_prices, dtype=float), [0.33, 0.66])
    for tr in trades:
        tr.price_bucket = _bucket_price(tr.entry_price, P_q1, P_q2)

    print(f"Price quantiles (entry_price): q1={P_q1:.4f}, q2={P_q2:.4f}")
    return trades, float(P_q1), float(P_q2)


# ------------------------------------------------------------------------
# Non-overlapping bucket simulation
# ------------------------------------------------------------------------

def simulate_bucket_non_overlapping(
    initial_capital: float, trades: List[Trade]
) -> Tuple[float, int, List[Tuple[datetime, float]]]:
    """
    Simulate one price bucket:
        - Trades sorted by entry_time.
        - Only one active trade at a time.
        - Capital updated at trade exit as:
              capital *= (1 + net_return)
        - Returns:
              final_capital, trades_used, equity_curve_samples
        - equity_curve_samples: list of (exit_time, capital_after_trade)
    """
    if not trades:
        return initial_capital, 0, []

    trades_sorted = sorted(trades, key=lambda t: t.entry_time)
    capital = float(initial_capital)
    trades_used = 0
    equity_curve: List[Tuple[datetime, float]] = []

    next_free_time: datetime | None = None

    for tr in trades_sorted:
        if next_free_time is not None and tr.entry_time < next_free_time:
            continue
        capital *= (1.0 + tr.net_return)
        trades_used += 1
        equity_curve.append((tr.exit_time, capital))
        next_free_time = tr.exit_time

    return capital, trades_used, equity_curve


# ------------------------------------------------------------------------
# Index buy-and-hold simulation
# ------------------------------------------------------------------------

def simulate_index_buy_hold(
    index_symbol: str,
    start_time: datetime,
    end_time: datetime,
    initial_capital: float,
) -> Tuple[float, List[Tuple[datetime, float]]]:
    """
    Buy-and-hold index from first UF trade entry time to last UF trade exit time.
        - Uses TFE data layer for INDEX_SYMBOL.
        - Buys at the first bar with timestamp >= start_time.
        - Holds until last bar with timestamp <= end_time.
        - Returns final_index_value and equity_curve_samples aligned to UF dates
          (only samples where UF exits trades).
    """
    bars = _fetch_history(index_symbol)
    if not bars:
        print(f"WARNING: no index data for {index_symbol}; treating index as flat.")
        return initial_capital, []

    # Sort just in case
    bars = sorted(bars, key=lambda b: b.timestamp)

    # Find entry bar
    entry_bar = None
    for b in bars:
        if b.timestamp >= start_time:
            entry_bar = b
            break

    if entry_bar is None:
        print(
            f"WARNING: no index bars after UF start time; index treated as flat."
        )
        return initial_capital, []

    entry_price = float(entry_bar.close)
    if entry_price <= 0.0 or math.isnan(entry_price):
        print("WARNING: invalid index entry price; index treated as flat.")
        return initial_capital, []

    shares = initial_capital / entry_price

    # Build full index curve for query by time
    index_curve: List[Tuple[datetime, float]] = []
    for b in bars:
        if b.timestamp < entry_bar.timestamp:
            continue
        if b.timestamp > end_time:
            break
        index_curve.append((b.timestamp, shares * float(b.close)))

    # If nothing in window, treat as flat
    if not index_curve:
        return initial_capital, []

    final_value = index_curve[-1][1]
    return final_value, index_curve


# ------------------------------------------------------------------------
# Main experiment
# ------------------------------------------------------------------------

def run_experiment() -> None:
    trades, P_q1, P_q2 = build_long_trades()
    if not trades:
        print("No trades generated; nothing to simulate.")
        return

    # Separate trades by price bucket
    high_trades = [tr for tr in trades if tr.price_bucket == "Price_high"]
    mid_trades = [tr for tr in trades if tr.price_bucket == "Price_mid"]
    low_trades = [tr for tr in trades if tr.price_bucket == "Price_low"]

    # Determine global start / end times for portfolio and index
    all_entry_times = [tr.entry_time for tr in trades]
    all_exit_times = [tr.exit_time for tr in trades]
    start_time = min(all_entry_times)
    end_time = max(all_exit_times)

    print("-" * 120)
    print(
        f"Portfolio simulation period: {start_time.isoformat()} → {end_time.isoformat()}"
    )
    print(
        f"Initial capital: total={TOTAL_INIT_CAPITAL:.2f} "
        f"(high={PORTFOLIO_INIT_HIGH:.2f}, mid={PORTFOLIO_INIT_MID:.2f}, low={PORTFOLIO_INIT_LOW:.2f})"
    )
    print(f"Price quantiles for buckets: q1={P_q1:.4f}, q2={P_q2:.4f}")
    print(f"Cost per trade (round-trip): {COST_RATE * 100:.2f}%")
    print("-" * 120)

    # Simulate each bucket
    final_high, trades_high, curve_high = simulate_bucket_non_overlapping(
        PORTFOLIO_INIT_HIGH, high_trades
    )
    final_mid, trades_mid, curve_mid = simulate_bucket_non_overlapping(
        PORTFOLIO_INIT_MID, mid_trades
    )
    final_low, trades_low, curve_low = simulate_bucket_non_overlapping(
        PORTFOLIO_INIT_LOW, low_trades
    )

    total_final = final_high + final_mid + final_low
    total_profit = total_final - TOTAL_INIT_CAPITAL

    sign_tot = "+" if total_profit >= 0.0 else "-"
    print("UF-CORE LONG-ONLY PORTFOLIO RESULTS (NON-OVERLAPPING, WITH COSTS)")
    print(
        f"Price_high: trades_used={trades_high:5d}  "
        f"start={PORTFOLIO_INIT_HIGH:10.2f}  final={final_high:10.2f}  "
        f"profit={'+' if final_high >= PORTFOLIO_INIT_HIGH else '-'}{abs(final_high - PORTFOLIO_INIT_HIGH):.2f}"
    )
    print(
        f"Price_mid : trades_used={trades_mid:5d}  "
        f"start={PORTFOLIO_INIT_MID:10.2f}  final={final_mid:10.2f}  "
        f"profit={'+' if final_mid >= PORTFOLIO_INIT_MID else '-'}{abs(final_mid - PORTFOLIO_INIT_MID):.2f}"
    )
    print(
        f"Price_low : trades_used={trades_low:5d}  "
        f"start={PORTFOLIO_INIT_LOW:10.2f}  final={final_low:10.2f}  "
        f"profit={'+' if final_low >= PORTFOLIO_INIT_LOW else '-'}{abs(final_low - PORTFOLIO_INIT_LOW):.2f}"
    )
    print(
        f"{'TOTAL UF PORTFOLIO':18s} "
        f"start={TOTAL_INIT_CAPITAL:10.2f}  final={total_final:10.2f}  "
        f"profit={sign_tot}{abs(total_profit):.2f}"
    )

    # Build a combined portfolio equity curve sampled at each trade exit
    # (sum of bucket capitals at each exit time; sorted by time).
    combined_curve: List[Tuple[datetime, float]] = []
    # We treat bucket curves as piecewise constant; at each bucket exit,
    # the other buckets keep their last known capital.
    # For simplicity, we only sample at union of all exit times.
    all_events = []
    for t, v in curve_high:
        all_events.append((t, "high", v))
    for t, v in curve_mid:
        all_events.append((t, "mid", v))
    for t, v in curve_low:
        all_events.append((t, "low", v))

    if not all_events:
        print("No completed trades for equity curve; skipping index comparison.")
        return

    all_events.sort(key=lambda x: x[0])
    cap_high = PORTFOLIO_INIT_HIGH
    cap_mid = PORTFOLIO_INIT_MID
    cap_low = PORTFOLIO_INIT_LOW

    portfolio_curve: List[Tuple[datetime, float]] = []
    for t, bucket, val in all_events:
        if bucket == "high":
            cap_high = val
        elif bucket == "mid":
            cap_mid = val
        elif bucket == "low":
            cap_low = val
        total_cap = cap_high + cap_mid + cap_low
        portfolio_curve.append((t, total_cap))

    # Index buy-and-hold
    index_final, index_curve_full = simulate_index_buy_hold(
        INDEX_SYMBOL, start_time, end_time, TOTAL_INIT_CAPITAL
    )

    print("-" * 120)
    print(f"INDEX ({INDEX_SYMBOL}) BUY-AND-HOLD RESULTS")
    print(
        f"Index final value: {index_final:10.2f} (start={TOTAL_INIT_CAPITAL:10.2f})"
    )
    print(
        f"UF portfolio final vs index final: UF={total_final:10.2f}  INDEX={index_final:10.2f}"
    )

    # Build index values at UF portfolio sample times
    # (nearest index point at or before each UF exit time).
    if not index_curve_full or not portfolio_curve:
        print("No index or portfolio curve for comparison; done.")
        return

    index_curve_full.sort(key=lambda x: x[0])
    idx_ptr = 0
    n_index = len(index_curve_full)

    def _index_value_at_or_before(ts: datetime) -> float:
        nonlocal idx_ptr
        # Move pointer forward while index times <= ts
        while idx_ptr + 1 < n_index and index_curve_full[idx_ptr + 1][0] <= ts:
            idx_ptr += 1
        return float(index_curve_full[idx_ptr][1])

    print("-" * 120)
    print("EQUITY CURVE SAMPLES (UF PORTFOLIO VS INDEX) AT UF TRADE EXITS")
    print(f"{'Time':25s}  {'UF_Portfolio':>12s}  {INDEX_SYMBOL:>12s}")
    for ts, uf_val in portfolio_curve:
        idx_val = _index_value_at_or_before(ts)
        print(f"{ts.isoformat():25s}  {uf_val:12.2f}  {idx_val:12.2f}")


# ------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------

def main() -> None:
    run_experiment()


if __name__ == "__main__":
    main()
