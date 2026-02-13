#!/usr/bin/env python3
"""
UF-Core MDG v0.3 – Trade distribution from structural_episodes.csv

Purpose
-------
Use the precomputed structural episodes (LONG/SHORT phases) to:

1) Rebuild the same non-overlapping LONG-only portfolio that uf_mdg_v02_regime_backtest.py used:
   - Only LONG episodes.
   - Episodes sorted by entry_time.
   - Only one position at a time (skip overlapping episodes).
   - Full capital per trade.
   - Simple round-trip cost applied to each trade.

2) Print, for the used trades:
   - symbol, entry_time, exit_time, forward_return, net_return, holding_bars
   - basic stats: count, min, max, mean, median net_return

3) Print stats for:
   - All LONG episodes (STABLE + TRANSITIONAL)
   - TRANSITIONAL-only LONG episodes

This script DOES NOT call UF-Core or fetch any new market data.
It only consumes structural_episodes.csv.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional

import math
import pandas as pd
import numpy as np

EPISODES_CSV_PATH: str = "structural_episodes.csv"

INITIAL_CAPITAL: float = 10_000.0
COST_RATE: float = 0.002  # 0.2% round-trip cost per trade


# ------------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------------

@dataclass
class Episode:
    symbol: str
    side: str           # "LONG" or "SHORT"
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    forward_return: float
    holding_bars: int
    entry_regime: str
    exit_regime: str


@dataclass
class UsedTrade:
    symbol: str
    entry_time: datetime
    exit_time: datetime
    forward_return: float
    net_return: float
    holding_bars: int
    entry_regime: str
    exit_regime: str


# ------------------------------------------------------------------------
# Loading structural episodes
# ------------------------------------------------------------------------

def load_episodes(path: str) -> List[Episode]:
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        print(f"ERROR: failed to read '{path}': {exc}")
        return []

    required_cols = [
        "symbol",
        "side",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "forward_return",
        "holding_bars",
        "entry_regime",
        "exit_regime",
    ]
    for col in required_cols:
        if col not in df.columns:
            print(f"ERROR: '{path}' missing required column '{col}'")
            return []

    # Parse times
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce", utc=True)
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce", utc=True)

    episodes: List[Episode] = []
    for _, row in df.iterrows():
        try:
            if pd.isna(row["entry_time"]) or pd.isna(row["exit_time"]):
                continue

            ep = Episode(
                symbol=str(row["symbol"]).strip().upper(),
                side=str(row["side"]).strip().upper(),
                entry_time=row["entry_time"].to_pydatetime(),
                exit_time=row["exit_time"].to_pydatetime(),
                entry_price=float(row["entry_price"]),
                exit_price=float(row["exit_price"]),
                forward_return=float(row["forward_return"]),
                holding_bars=int(row["holding_bars"]),
                entry_regime=str(row["entry_regime"]).strip().upper(),
                exit_regime=str(row["exit_regime"]).strip().upper(),
            )
            episodes.append(ep)
        except Exception:
            # Skip any malformed rows
            continue

    return episodes


# ------------------------------------------------------------------------
# Non-overlapping LONG-only portfolio reconstruction
# ------------------------------------------------------------------------

def build_non_overlapping_long_portfolio(
    episodes: List[Episode],
    initial_capital: float,
    cost_rate: float,
) -> Tuple[float, List[UsedTrade]]:
    """
    Rebuild the same style of portfolio as MDG v0.2:

    - Use only LONG episodes.
    - Sort by entry_time.
    - Only one active trade at a time (skip overlapping episodes).
    - Full capital per trade.
    - net_return = forward_return - cost_rate.
    """
    longs = [ep for ep in episodes if ep.side == "LONG"]
    if not longs:
        return initial_capital, []

    longs_sorted = sorted(longs, key=lambda e: e.entry_time)

    capital = float(initial_capital)
    used_trades: List[UsedTrade] = []
    next_free_time: Optional[datetime] = None

    for ep in longs_sorted:
        # Enforce non-overlap
        if next_free_time is not None and ep.entry_time < next_free_time:
            continue

        # Compute net return for this episode
        f_ret = float(ep.forward_return)
        net_ret = f_ret - cost_rate

        # Sanity: skip totally insane values (NaN, +/- inf)
        if math.isnan(net_ret) or math.isinf(net_ret):
            continue

        # Apply to capital
        capital *= (1.0 + net_ret)

        used_trades.append(
            UsedTrade(
                symbol=ep.symbol,
                entry_time=ep.entry_time,
                exit_time=ep.exit_time,
                forward_return=f_ret,
                net_return=net_ret,
                holding_bars=ep.holding_bars,
                entry_regime=ep.entry_regime,
                exit_regime=ep.exit_regime,
            )
        )

        next_free_time = ep.exit_time

    return capital, used_trades


# ------------------------------------------------------------------------
# Simple stats helper
# ------------------------------------------------------------------------

def _print_return_stats(label: str, returns: List[float]) -> None:
    print(f"\n[{label}]")
    if not returns:
        print("  count=0")
        return

    arr = np.array(returns, dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        print("  count=0 (all NaN)")
        return

    count = arr.size
    mean = float(np.mean(arr))
    med = float(np.median(arr))
    minv = float(np.min(arr))
    maxv = float(np.max(arr))

    # Print in percent for readability
    print(f"  count = {count}")
    print(f"  mean  = {mean * 100.0:6.2f}%")
    print(f"  median= {med  * 100.0:6.2f}%")
    print(f"  min   = {minv * 100.0:6.2f}%")
    print(f"  max   = {maxv * 100.0:6.2f}%")


# ------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------

def main() -> None:
    episodes = load_episodes(EPISODES_CSV_PATH)
    if not episodes:
        print("No episodes loaded; aborting.")
        return

    print("UF-Core MDG v0.3 – Trade distribution from structural_episodes.csv")
    print(f"Episodes loaded: {len(episodes)}")
    print(f"Cost per trade (round-trip): {COST_RATE * 100.0:.2f}%")
    print("-" * 80)

    # Rebuild non-overlapping LONG-only portfolio
    final_capital, used_trades = build_non_overlapping_long_portfolio(
        episodes, INITIAL_CAPITAL, COST_RATE
    )

    profit = final_capital - INITIAL_CAPITAL
    sign = "+" if profit >= 0.0 else "-"

    print("Reconstructed non-overlapping LONG-only portfolio (ALL regimes)")
    print(f"Initial capital : {INITIAL_CAPITAL:10.2f}")
    print(f"Final capital   : {final_capital:10.2f}")
    print(f"Profit          : {sign}{abs(profit):.2f}")
    print(f"Trades used     : {len(used_trades)}")
    print("-" * 80)

    # Per-trade table
    print("Used trades:")
    print(
        f"{'idx':>3s}  {'symbol':6s}  {'entry':19s}  {'exit':19s}  "
        f"{'f_ret%':>8s}  {'net_ret%':>8s}  {'bars':>5s}  {'regime':10s}"
    )
    for i, tr in enumerate(used_trades, start=1):
        f_pct = tr.forward_return * 100.0
        n_pct = tr.net_return * 100.0
        print(
            f"{i:3d}  {tr.symbol:6s}  "
            f"{tr.entry_time.date().isoformat():19s}  "
            f"{tr.exit_time.date().isoformat():19s}  "
            f"{f_pct:8.2f}  {n_pct:8.2f}  "
            f"{tr.holding_bars:5d}  {tr.entry_regime:10s}"
        )

    # Stats for used trades
    used_net = [tr.net_return for tr in used_trades]
    _print_return_stats("USED TRADES (net returns)", used_net)

    # All LONG episodes (regardless of overlap)
    longs_all = [ep for ep in episodes if ep.side == "LONG"]
    longs_all_net = [float(ep.forward_return) - COST_RATE for ep in longs_all]
    _print_return_stats("ALL LONG EPISODES (net)", longs_all_net)

    # TRANSITIONAL-only LONG episodes
    longs_trans = [
        ep for ep in episodes
        if ep.side == "LONG" and ep.entry_regime.upper() == "TRANSITIONAL"
    ]
    longs_trans_net = [float(ep.forward_return) - COST_RATE for ep in longs_trans]
    _print_return_stats("TRANSITIONAL LONG EPISODES (net)", longs_trans_net)


if __name__ == "__main__":
    main()
