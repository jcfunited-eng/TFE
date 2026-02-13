#!/usr/bin/env python3
"""
UF-Core MDG v0.2 – Regime-based backtest from structural_episodes.csv

Purpose
-------
Light job, NO new UF-Core computation, NO re-download of the whole universe.

Inputs:
  - structural_episodes.csv (produced by uf_structural_episodes_log.py)
      columns:
        symbol, side, entry_time, exit_time, entry_price, exit_price,
        forward_return, holding_bars, entry_regime, exit_regime,
        entry_S_UF, exit_S_UF, entry_D, exit_D

What this script does:
  1. Loads all episodes.
  2. Computes regime diagnostics:
        regime, count_long, avg_long_ret, count_short, avg_short_ret
     using forward_return (no costs).
  3. Builds a portfolio using ONLY LONG episodes:
        - Baseline: all LONG episodes, non-overlapping, full capital per trade.
        - Regime-filtered: LONG episodes with entry_regime == "TRANSITIONAL".
     Uses a simple trading cost COST_RATE per episode (round-trip).
  4. Compares UF portfolio to index (SPY) buy-and-hold over the same period.

This uses:
  - structural_episodes.csv for UF trades,
  - unified_market_data_service only once, for SPY.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional
import math

import pandas as pd

# ------------------------------------------------------------------------
# Config
# ------------------------------------------------------------------------

EPISODES_CSV_PATH: str = "structural_episodes.csv"
INDEX_SYMBOL: str = "SPY"

INITIAL_CAPITAL: float = 10_000.0
COST_RATE: float = 0.0020  # 0.20% per episode


# ------------------------------------------------------------------------
# TFE data layer for index only
# ------------------------------------------------------------------------

from unified_market_data_service import get_unified_market_data  # type: ignore
from tfe_market_data_service import Bar, HistoryRequest, Timespan  # type: ignore


def _fetch_index_history(symbol: str, start_time: datetime, end_time: datetime) -> List[Bar]:
    client = get_unified_market_data()
    req = HistoryRequest(
        symbol=symbol,
        timespan=Timespan.DAY,
        multiplier=1,
        start=start_time,
        end=end_time,
        adjusted=True,
        limit=None,
    )
    result = client.get_history(req)
    bars: List[Bar] = getattr(result, "bars", []) or []
    bars = [b for b in bars if b.timestamp >= start_time and b.timestamp <= end_time]
    return sorted(bars, key=lambda b: b.timestamp)


# ------------------------------------------------------------------------
# Trade structure & portfolio sim over episodes
# ------------------------------------------------------------------------

@dataclass
class EpisodeTrade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    net_return: float  # forward_return - COST_RATE
    holding_bars: int
    entry_regime: str
    exit_regime: str


def _to_datetime(s: str) -> datetime:
    # structural_episodes.csv uses isoformat
    return datetime.fromisoformat(s)


def build_long_trades_from_episodes(df: pd.DataFrame) -> List[EpisodeTrade]:
    trades: List[EpisodeTrade] = []
    for _, row in df.iterrows():
        side = str(row["side"]).upper()
        if side != "LONG":
            continue

        try:
            entry_time = _to_datetime(str(row["entry_time"]))
            exit_time = _to_datetime(str(row["exit_time"]))
        except Exception:
            continue

        try:
            fwd_ret = float(row["forward_return"])
        except Exception:
            continue

        net_ret = fwd_ret - COST_RATE

        try:
            holding = int(row["holding_bars"])
        except Exception:
            holding = 0

        entry_regime = str(row["entry_regime"])
        exit_regime = str(row["exit_regime"])

        trades.append(
            EpisodeTrade(
                symbol=str(row["symbol"]),
                entry_time=entry_time,
                exit_time=exit_time,
                net_return=net_ret,
                holding_bars=holding,
                entry_regime=entry_regime,
                exit_regime=exit_regime,
            )
        )
    return trades


def simulate_non_overlapping(trades: List[EpisodeTrade], initial_capital: float) -> Tuple[float, int, float, float, List[Tuple[datetime, float]]]:
    if not trades:
        return initial_capital, 0, 0.0, 0.0, []

    trades_sorted = sorted(trades, key=lambda t: t.entry_time)
    capital = float(initial_capital)
    trades_used = 0
    sum_net = 0.0
    sum_hold = 0.0
    eq_curve: List[Tuple[datetime, float]] = []
    next_free: Optional[datetime] = None

    for tr in trades_sorted:
        if next_free is not None and tr.entry_time < next_free:
            continue  # overlapping, skip

        capital *= (1.0 + tr.net_return)
        trades_used += 1
        sum_net += tr.net_return
        sum_hold += float(tr.holding_bars)
        eq_curve.append((tr.exit_time, capital))
        next_free = tr.exit_time

    avg_net = sum_net / trades_used if trades_used > 0 else 0.0
    avg_hold = sum_hold / trades_used if trades_used > 0 else 0.0
    return capital, trades_used, avg_net, avg_hold, eq_curve


def simulate_index_buy_hold(start_time: datetime, end_time: datetime, initial_capital: float) -> Tuple[float, List[Tuple[datetime, float]]]:
    bars = _fetch_index_history(INDEX_SYMBOL, start_time, end_time)
    if not bars:
        print(f"WARNING: no data for index {INDEX_SYMBOL}")
        return initial_capital, []

    entry_bar = bars[0]
    entry_price = float(entry_bar.close)
    if entry_price <= 0.0 or math.isnan(entry_price):
        print(f"WARNING: invalid index entry price; treating as flat.")
        return initial_capital, []

    shares = initial_capital / entry_price
    curve: List[Tuple[datetime, float]] = []
    for b in bars:
        value = shares * float(b.close)
        curve.append((b.timestamp, value))

    return curve[-1][1], curve


# ------------------------------------------------------------------------
# Regime diagnostics
# ------------------------------------------------------------------------

def compute_regime_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns:
        regime, count_long, avg_long_ret, count_short, avg_short_ret
    """
    rows = []
    regimes = sorted(set(df["entry_regime"].astype(str).tolist()))
    for reg in regimes:
        sub = df[df["entry_regime"] == reg]

        long_eps = sub[sub["side"].str.upper() == "LONG"]
        short_eps = sub[sub["side"].str.upper() == "SHORT"]

        def _mean_or_zero(series: pd.Series) -> float:
            if len(series) == 0:
                return 0.0
            return float(series.mean())

        rows.append(
            {
                "regime": reg,
                "count_long": int(len(long_eps)),
                "avg_long_ret": _mean_or_zero(long_eps["forward_return"]),
                "count_short": int(len(short_eps)),
                "avg_short_ret": _mean_or_zero(short_eps["forward_return"]),
            }
        )

    return pd.DataFrame(rows)


# ------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------

def main() -> None:
    try:
        df = pd.read_csv(EPISODES_CSV_PATH)
    except Exception as exc:
        print(f"ERROR: could not read '{EPISODES_CSV_PATH}': {exc}")
        return

    if df.empty:
        print(f"'{EPISODES_CSV_PATH}' is empty; nothing to do.")
        return

    print("UF-Core MDG v0.2 – Regime-based backtest from structural_episodes.csv")
    print(f"Episodes file: {EPISODES_CSV_PATH}")
    entry_times = [ _to_datetime(str(t)) for t in df["entry_time"] ]
    exit_times  = [ _to_datetime(str(t)) for t in df["exit_time"] ]
    start_time = min(entry_times)
    end_time = max(exit_times)
    print(f"Episode time range: {start_time.isoformat()} → {end_time.isoformat()}")
    print(f"INITIAL_CAPITAL={INITIAL_CAPITAL:.2f}, COST_RATE={COST_RATE:.4f}")
    print("-" * 120)

    # 1) Regime diagnostics
    diag = compute_regime_diagnostics(df)
    print("Regime diagnostics (trade_return means per episode):")
    print(f"{'regime':16s}  {'count_long':>10s}  {'avg_long_ret':>12s}  {'count_short':>11s}  {'avg_short_ret':>12s}")
    for _, row in diag.iterrows():
        print(
            f"{str(row['regime']):16s}  "
            f"{int(row['count_long']):10d}  "
            f"{float(row['avg_long_ret']):12.4f}  "
            f"{int(row['count_short']):11d}  "
            f"{float(row['avg_short_ret']):12.4f}"
        )
    print("-" * 120)

    # 2) Build trades from episodes
    all_long_trades = build_long_trades_from_episodes(df)
    trans_long_trades = [t for t in all_long_trades if t.entry_regime.upper() == "TRANSITIONAL"]

    # 3) Baseline portfolio: all LONG episodes, non-overlapping
    final_all, used_all, avg_net_all, avg_hold_all, eq_all = simulate_non_overlapping(all_long_trades, INITIAL_CAPITAL)

    profit_all = final_all - INITIAL_CAPITAL
    sign_all = "+" if profit_all >= 0 else "-"

    print("UF-CORE EPISODE PORTFOLIO – BASELINE (ALL LONG EPISODES, NON-OVERLAPPING)")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final capital  : {final_all:10.2f}")
    print(f"Profit         : {sign_all}{abs(profit_all):.2f}")
    print(f"Trades used    : {used_all}")
    print(f"Avg net return : {avg_net_all * 100.0:6.2f}% per trade (after cost)")
    print(f"Avg holding    : {avg_hold_all:6.1f} bars per trade")
    print("-" * 120)

    # 4) Regime-filtered portfolio: TRANSITIONAL longs only
    final_trans, used_trans, avg_net_trans, avg_hold_trans, eq_trans = simulate_non_overlapping(trans_long_trades, INITIAL_CAPITAL)

    profit_trans = final_trans - INITIAL_CAPITAL
    sign_trans = "+" if profit_trans >= 0 else "-"

    print("UF-CORE EPISODE PORTFOLIO – REGIME FILTERED (LONG, TRANSITIONAL ONLY, NON-OVERLAPPING)")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final capital  : {final_trans:10.2f}")
    print(f"Profit         : {sign_trans}{abs(profit_trans):.2f}")
    print(f"Trades used    : {used_trans}")
    print(f"Avg net return : {avg_net_trans * 100.0:6.2f}% per trade (after cost)")
    print(f"Avg holding    : {avg_hold_trans:6.1f} bars per trade")
    print("-" * 120)

    # 5) Index comparison (buy-and-hold)
    index_final, index_curve = simulate_index_buy_hold(start_time, end_time, INITIAL_CAPITAL)
    print("INDEX (SPY) BUY-AND-HOLD")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final value    : {index_final:10.2f}")
    print(f"UF (ALL LONG)  : {final_all:10.2f}")
    print(f"UF (TRANS LONG): {final_trans:10.2f}")
    print("-" * 120)

    # 6) Simple equity curve samples at UF exits (baseline)
    if eq_all and index_curve:
        index_curve_sorted = sorted(index_curve, key=lambda x: x[0])
        eq_all_sorted = sorted(eq_all, key=lambda x: x[0])
        idx_ptr = 0
        n_idx = len(index_curve_sorted)

        def index_value_at_or_before(ts: datetime) -> float:
            nonlocal idx_ptr
            while idx_ptr + 1 < n_idx and index_curve_sorted[idx_ptr + 1][0] <= ts:
                idx_ptr += 1
            return float(index_curve_sorted[idx_ptr][1])

        print("EQUITY CURVE SAMPLES (UF BASELINE VS INDEX) AT UF EXIT TIMES")
        print(f"{'Time':25s}  {'UF_Portfolio':>12s}  {'Index':>12s}")
        for ts, uf_val in eq_all_sorted:
            idx_val = index_value_at_or_before(ts)
            print(f"{ts.isoformat():25s}  {uf_val:12.2f}  {idx_val:12.2f}")


if __name__ == "__main__":
    main()
