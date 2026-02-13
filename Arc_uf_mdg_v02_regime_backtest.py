#!/usr/bin/env python3
"""
UF-Core MDG v0.2 – Regime-based backtest using structural_episodes.csv

- DOES NOT run UF-Core.
- Uses structural_episodes.csv produced by uf_structural_episodes_log.py.
- Treats UF-Core as a structural field; governance decides when to act.

What it does
------------
1) Loads structural_episodes.csv.
2) Builds a simple regime table:

       entry_regime,
       count_long, avg_long_trade_ret,
       count_short, avg_short_trade_ret

   where trade_ret is:
       LONG  -> forward_return
       SHORT -> -forward_return   (short P&L)

3) Simulates two long-only portfolios (one position at a time):

   A) BASELINE: all LONG episodes, regardless of regime.
   B) REGIME_FILTERED: only LONG episodes with entry_regime="TRANSITIONAL".

   For each scenario:
       - Start with INITIAL_CAPITAL.
       - Process episodes in time order.
       - Each trade uses full capital; net_return = trade_return - COST_RATE.
       - Capital compounds; we record equity at each exit.

4) Compares each portfolio to SPY buy-and-hold over the same period.

Config knobs
------------
- EPISODES_CSV_PATH: path to structural_episodes.csv.
- INDEX_SYMBOL: index/ETF for baseline comparison (default "SPY").
- COST_RATE: rough per-trade cost (round-trip).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict

import math
import pandas as pd

# TFE data layer (for index only)
from unified_market_data_service import get_unified_market_data  # type: ignore
from tfe_market_data_service import Bar, HistoryRequest, Timespan  # type: ignore

# ------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------

EPISODES_CSV_PATH: str = "structural_episodes.csv"
INDEX_SYMBOL: str = "SPY"

COST_RATE: float = 0.0020  # ~0.20% per trade (same scale as earlier tests)
INITIAL_CAPITAL: float = 10_000.0

# ------------------------------------------------------------------------
# Helpers – data access
# ------------------------------------------------------------------------

def _fetch_index_history(
    symbol: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Bar]:
    """
    Fetch daily bars for the index using TFE's unified market data service.
    """
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
    bars = sorted(bars, key=lambda b: b.timestamp)
    return bars

# ------------------------------------------------------------------------
# Portfolio simulation on structural episodes
# ------------------------------------------------------------------------

@dataclass
class EpisodeTrade:
    """
    A single trade derived from a structural episode.
    Trade return is from the trader's perspective (LONG or SHORT).
    """
    symbol: str
    side: str           # "LONG" or "SHORT"
    entry_time: datetime
    exit_time: datetime
    forward_return: float   # raw price return (exit/entry - 1)
    trade_return: float     # LONG: forward_return; SHORT: -forward_return
    holding_bars: int
    entry_regime: str
    exit_regime: str


def load_episodes(path: str) -> pd.DataFrame:
    """
    Load structural_episodes.csv and add:
        - entry_time_dt / exit_time_dt (datetime)
        - trade_return (P&L-aware)
    """
    df = pd.read_csv(path)
    if df.empty:
        raise RuntimeError(f"'{path}' is empty; nothing to backtest.")

    df["entry_time_dt"] = pd.to_datetime(df["entry_time"])
    df["exit_time_dt"] = pd.to_datetime(df["exit_time"])

    # Price return (already in CSV)
    # LONG P&L = forward_return
    # SHORT P&L = -forward_return
    df["trade_return"] = df.apply(
        lambda r: float(r["forward_return"])
        if str(r["side"]).upper() == "LONG"
        else -float(r["forward_return"]),
        axis=1,
    )
    return df


def build_regime_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a simple regime diagnostics table:

        regime, count_long, avg_long_ret, count_short, avg_short_ret
    """
    rows: List[Dict[str, object]] = []
    regimes = sorted(df["entry_regime"].dropna().unique().tolist())

    for reg in regimes:
        sub = df[df["entry_regime"] == reg]
        long = sub[sub["side"] == "LONG"]
        short = sub[sub["side"] == "SHORT"]

        def _stats(x: pd.Series) -> Tuple[int, float]:
            if x.empty:
                return 0, 0.0
            return int(len(x)), float(x.mean())

        cl, ml = _stats(long["trade_return"])
        cs, ms = _stats(short["trade_return"])

        rows.append(
            {
                "regime": reg,
                "count_long": cl,
                "avg_long_ret": ml,
                "count_short": cs,
                "avg_short_ret": ms,
            }
        )

    return pd.DataFrame(rows)


def simulate_episode_portfolio(
    trades: List[EpisodeTrade],
    initial_capital: float,
    cost_rate: float,
) -> Tuple[float, int, float, float, List[Tuple[datetime, float]]]:
    """
    One position at a time, full capital per trade, non-overlapping.
    net_return = trade_return - cost_rate.
    """
    if not trades:
        return initial_capital, 0, 0.0, 0.0, []

    trades = sorted(trades, key=lambda t: t.entry_time)

    capital = float(initial_capital)
    trades_used = 0
    sum_net_ret = 0.0
    sum_hold = 0.0
    equity_curve: List[Tuple[datetime, float]] = []

    next_free_time: Optional[datetime] = None

    for tr in trades:
        if next_free_time is not None and tr.entry_time <= next_free_time:
            # Skip overlapping episodes; capital is already committed.
            continue

        net_ret = tr.trade_return - cost_rate
        capital *= (1.0 + net_ret)
        trades_used += 1
        sum_net_ret += net_ret
        sum_hold += float(tr.holding_bars)
        equity_curve.append((tr.exit_time, capital))
        next_free_time = tr.exit_time

    avg_net = sum_net_ret / trades_used if trades_used > 0 else 0.0
    avg_hold = sum_hold / trades_used if trades_used > 0 else 0.0

    return capital, trades_used, avg_net, avg_hold, equity_curve


def simulate_index_buy_hold(
    index_symbol: str,
    start_time: datetime,
    end_time: datetime,
    initial_capital: float,
) -> Tuple[float, List[Tuple[datetime, float]]]:
    """
    Buy index at first bar >= start_time, hold until last bar <= end_time.
    """
    bars = _fetch_index_history(index_symbol, start_time, end_time)
    if not bars:
        print(f"WARNING: no data for index symbol '{index_symbol}'")
        return initial_capital, []

    bars = [b for b in bars if b.timestamp >= start_time and b.timestamp <= end_time]
    if not bars:
        print("WARNING: index has no bars in UF episode window; treating as flat.")
        return initial_capital, []

    bars = sorted(bars, key=lambda b: b.timestamp)

    entry_bar: Optional[Bar] = None
    for b in bars:
        if b.timestamp >= start_time:
            entry_bar = b
            break

    if entry_bar is None:
        print("WARNING: index has no bars after UF start; treating as flat.")
        return initial_capital, []

    entry_price = float(entry_bar.close)
    if entry_price <= 0.0 or math.isnan(entry_price):
        print("WARNING: invalid index entry price; treating as flat.")
        return initial_capital, []

    shares = initial_capital / entry_price

    curve: List[Tuple[datetime, float]] = []
    for b in bars:
        cur_val = shares * float(b.close)
        curve.append((b.timestamp, cur_val))

    if not curve:
        return initial_capital, []

    final_value = curve[-1][1]
    return final_value, curve

# ------------------------------------------------------------------------
# Main: MDG v0.2 backtest on structural_episodes.csv
# ------------------------------------------------------------------------

def run_experiment() -> None:
    # 1) Load episodes
    df = load_episodes(EPISODES_CSV_PATH)

    start_time = df["entry_time_dt"].min().to_pydatetime()
    end_time = df["exit_time_dt"].max().to_pydatetime()

    print("UF-Core MDG v0.2 – Regime-based backtest from structural_episodes.csv")
    print(f"Episodes file: {EPISODES_CSV_PATH}")
    print(f"Episode time range: {start_time.isoformat()} → {end_time.isoformat()}")
    print(f"INITIAL_CAPITAL={INITIAL_CAPITAL:.2f}, COST_RATE={COST_RATE:.4f}")
    print("-" * 120)

    # 2) Regime diagnostics
    reg_table = build_regime_table(df)
    if reg_table.empty:
        print("No episodes found; nothing to backtest.")
        return

    print("Regime diagnostics (trade_return means per episode):")
    print("regime          count_long  avg_long_ret   count_short  avg_short_ret")
    for _, row in reg_table.iterrows():
        print(
            f"{row['regime']:<15s}"
            f"{int(row['count_long']):11d}  {float(row['avg_long_ret']):12.4f}"
            f"{int(row['count_short']):13d}  {float(row['avg_short_ret']):13.4f}"
        )
    print("-" * 120)

    # 3) Build EpisodeTrade lists for scenarios
    #    A) All LONG episodes (baseline)
    long_all_df = df[df["side"].str.upper() == "LONG"].copy()

    def _df_to_trades(sub: pd.DataFrame) -> List[EpisodeTrade]:
        trades: List[EpisodeTrade] = []
        for _, r in sub.iterrows():
            trades.append(
                EpisodeTrade(
                    symbol=str(r["symbol"]),
                    side=str(r["side"]).upper(),
                    entry_time=r["entry_time_dt"].to_pydatetime(),
                    exit_time=r["exit_time_dt"].to_pydatetime(),
                    forward_return=float(r["forward_return"]),
                    trade_return=float(r["trade_return"]),
                    holding_bars=int(r["holding_bars"]),
                    entry_regime=str(r["entry_regime"]),
                    exit_regime=str(r["exit_regime"]),
                )
            )
        return trades

    trades_all_long = _df_to_trades(long_all_df)

    #    B) LONG episodes with entry_regime == "TRANSITIONAL"
    long_transitional_df = long_all_df[long_all_df["entry_regime"] == "TRANSITIONAL"].copy()
    trades_long_trans = _df_to_trades(long_transitional_df)

    # 4) Portfolio simulations
    final_all, used_all, avg_all, avg_hold_all, curve_all = simulate_episode_portfolio(
        trades_all_long, INITIAL_CAPITAL, COST_RATE
    )
    final_trans, used_trans, avg_trans, avg_hold_trans, curve_trans = simulate_episode_portfolio(
        trades_long_trans, INITIAL_CAPITAL, COST_RATE
    )

    profit_all = final_all - INITIAL_CAPITAL
    profit_trans = final_trans - INITIAL_CAPITAL

    sign_all = "+" if profit_all >= 0.0 else "-"
    sign_trans = "+" if profit_trans >= 0.0 else "-"

    print("UF-CORE EPISODE PORTFOLIO – BASELINE (ALL LONG EPISODES, NON-OVERLAPPING)")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final capital  : {final_all:10.2f}")
    print(f"Profit         : {sign_all}{abs(profit_all):.2f}")
    print(f"Trades used    : {used_all}")
    print(f"Avg net return : {avg_all * 100.0:6.2f}% per trade (after cost)")
    print(f"Avg holding    : {avg_hold_all:6.1f} bars per trade")
    print("-" * 120)

    print("UF-CORE EPISODE PORTFOLIO – REGIME FILTERED (LONG, TRANSITIONAL ONLY, NON-OVERLAPPING)")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final capital  : {final_trans:10.2f}")
    print(f"Profit         : {sign_trans}{abs(profit_trans):.2f}")
    print(f"Trades used    : {used_trans}")
    print(f"Avg net return : {avg_trans * 100.0:6.2f}% per trade (after cost)")
    print(f"Avg holding    : {avg_hold_trans:6.1f} bars per trade")
    print("-" * 120)

    # 5) Index comparison
    index_final, index_curve = simulate_index_buy_hold(
        INDEX_SYMBOL, start_time, end_time, INITIAL_CAPITAL
    )

    print("INDEX (SPY) BUY-AND-HOLD")
    print(f"Initial capital: {INITIAL_CAPITAL:10.2f}")
    print(f"Final value    : {index_final:10.2f}")
    print(f"UF (ALL LONG)  : {final_all:10.2f}")
    print(f"UF (TRANS LONG): {final_trans:10.2f}")
    print("-" * 120)

    # Small equity curve sample at UF exits for baseline scenario
    if curve_all and index_curve:
        # Build index dict for quick lookup
        idx_series: Dict[datetime, float] = {t: v for (t, v) in index_curve}
        print("EQUITY CURVE SAMPLES (UF BASELINE VS INDEX) AT UF EXIT TIMES")
        print("Time                       UF_Portfolio           Index")
        # Take up to 80 samples evenly spaced
        step = max(1, len(curve_all) // 80)
        for i in range(0, len(curve_all), step):
            t, cap = curve_all[i]
            idx_val = idx_series.get(t, 0.0)
            print(f"{t.isoformat():<26s}{cap:12.2f}{idx_val:16.2f}")

def main() -> None:
    run_experiment()

if __name__ == "__main__":
    main()
