#!/usr/bin/env python3
"""
Tuple-proximity-driven backtest — pure numpy nearest-neighbor tuple distance.

Entry: gate event where neighbor-WR >= threshold
Exit: neighbor-WR < 0.40, -10% catastrophic floor, 20d max hold
No SPY gate. No Mar 26 region. No threshold conjunctions.
Reads whatever the kernel emits. The tuple-proximity IS the L5 signal.
"""

import json
import os
import sys
import time
import random
from datetime import datetime, timezone
from collections import defaultdict

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from uf_core.uf_structural_engine import compute_uf_structural_state

# ── Config ──────────────────────────────────────────────────────────
N_NEIGHBORS = 30
FORWARD_DAYS = 20       # win/loss horizon
MAX_HOLD = 20           # max hold days
CATASTROPHIC_FLOOR = -0.10  # -10% stop
EXIT_WR_THRESHOLD = 0.40    # exit when neighbor-WR drops below this
ENTRY_THRESHOLDS = [0.55, 0.60, 0.65, 0.70]
MIN_HISTORY = 100       # minimum bars before first signal
SAMPLE_SIZE = 200       # random CS-only sample
TUPLE_FIELDS = ["D_k", "M_k", "B_k", "R_rev_k", "U_star_k", "C_k", "P_k"]
N_DIM = len(TUPLE_FIELDS)


def connect_db():
    return psycopg2.connect(
        host="/var/run/postgresql",
        dbname="tfe_validation",
        user="postgres",
    )


def load_cs_tickers():
    with open(os.path.join(os.path.dirname(__file__), "..", "massive_universe_stocks.json")) as f:
        data = json.load(f)
    return [
        item["ticker"].upper()
        for item in data
        if isinstance(item, dict) and item.get("type") == "CS" and item.get("active")
    ]


def extract_tuple(level5):
    """Extract the 7-dim tuple from kernel level5 output."""
    vals = []
    for f in TUPLE_FIELDS:
        v = level5.get(f)
        if v is None:
            return None
        vals.append(float(v))
    return np.array(vals)


def compute_neighbor_wr(current_tuple, history_tuples, history_returns, n=N_NEIGHBORS):
    """Pure numpy nearest-neighbor WR in per-stock normalized tuple space.

    current_tuple: np.array shape (7,)
    history_tuples: np.array shape (N, 7)
    history_returns: np.array shape (N,) — forward returns at each historical point

    Returns: neighbor_wr (float), or None if insufficient history
    """
    if len(history_tuples) <= n:
        return None

    # Per-stock normalization: range of each field across this stock's history
    ranges = np.ptp(history_tuples, axis=0)
    ranges = np.where(ranges < 1e-10, 1.0, ranges)  # avoid div-by-zero

    # Normalized Euclidean distance
    diff = (history_tuples - current_tuple) / ranges
    dists = np.sqrt(np.sum(diff ** 2, axis=1))

    # Find N nearest neighbors
    idx = np.argpartition(dists, n)[:n]
    neighbor_returns = history_returns[idx]

    # WR = fraction of neighbors with positive forward return
    wins = np.sum(neighbor_returns > 0)
    return float(wins) / n


def run_backtest_for_ticker(ticker, bars_df):
    """Run the tuple-proximity backtest for one ticker.

    bars_df: DataFrame with columns [bar_date, close], sorted ascending.

    Returns list of signal dicts.
    """
    closes = bars_df["close"].values
    dates = bars_df["bar_date"].values
    n_bars = len(closes)

    if n_bars < MIN_HISTORY + FORWARD_DAYS:
        return []

    # Step 1: Run kernel at every 3rd bar to get tuple history (3x speedup)
    STEP = 3
    close_series_base = pd.Series(
        closes.astype(float),
        index=[pd.Timestamp(d) for d in dates],
    ).sort_index()

    tuples = []  # (index, tuple_array)
    for i in range(MIN_HISTORY, n_bars, STEP):
        sub = close_series_base.iloc[: i + 1]
        state = compute_uf_structural_state(sub)
        t = extract_tuple(state.level5)
        if t is not None:
            tuples.append((i, t))

    if len(tuples) < N_NEIGHBORS + 1:
        return []

    # Step 2: Compute forward returns for each tuple point
    tuple_indices = np.array([t[0] for t in tuples])
    tuple_arrays = np.array([t[1] for t in tuples])

    forward_returns = np.full(len(tuples), np.nan)
    for j, idx in enumerate(tuple_indices):
        fwd_idx = idx + FORWARD_DAYS
        if fwd_idx < n_bars:
            forward_returns[j] = (closes[fwd_idx] - closes[idx]) / closes[idx]

    # Step 3: Walk forward — at each bar, compute tuple-proximity using ONLY past history
    signals = []
    for j in range(N_NEIGHBORS, len(tuples)):
        bar_idx = tuple_indices[j]

        # Can only use history BEFORE this point
        hist_tuples = tuple_arrays[:j]
        hist_returns = forward_returns[:j]

        # Remove NaN returns from history (those too close to the end)
        valid = ~np.isnan(hist_returns)
        if np.sum(valid) < N_NEIGHBORS:
            continue

        current_tuple = tuple_arrays[j]
        wr = compute_neighbor_wr(
            current_tuple, hist_tuples[valid], hist_returns[valid], N_NEIGHBORS
        )
        if wr is None:
            continue

        # Record signal with forward return if available
        fwd_ret = forward_returns[j] if not np.isnan(forward_returns[j]) else None
        signals.append({
            "ticker": ticker,
            "bar_idx": int(bar_idx),
            "date": str(dates[bar_idx]),
            "price": float(closes[bar_idx]),
            "neighbor_wr": wr,
            "fwd_return_20d": fwd_ret,
            "tuple": current_tuple.tolist(),
        })

    return signals


def simulate_trades(signals, bars_lookup, entry_threshold):
    """Simulate trades with entry/exit rules.

    Entry: neighbor_wr >= entry_threshold
    Exit: neighbor_wr < 0.40, -10% floor, 20d max hold
    """
    trades = []
    active_trade = None

    for sig in signals:
        ticker = sig["ticker"]
        price = sig["price"]
        wr = sig["neighbor_wr"]
        bar_idx = sig["bar_idx"]
        date = sig["date"]
        bars = bars_lookup[ticker]

        # Check active trade exit conditions
        if active_trade and active_trade["ticker"] == ticker:
            hold_days = bar_idx - active_trade["entry_bar_idx"]
            current_return = (price - active_trade["entry_price"]) / active_trade["entry_price"]

            exit_reason = None
            if current_return <= CATASTROPHIC_FLOOR:
                exit_reason = "STOP_LOSS"
            elif hold_days >= MAX_HOLD:
                exit_reason = "TIME_CAP"
            elif wr < EXIT_WR_THRESHOLD:
                exit_reason = "TP_EXIT"

            if exit_reason:
                active_trade["exit_price"] = price
                active_trade["exit_date"] = date
                active_trade["exit_bar_idx"] = bar_idx
                active_trade["exit_reason"] = exit_reason
                active_trade["return"] = current_return
                active_trade["hold_days"] = hold_days
                trades.append(active_trade)
                active_trade = None

        # Entry: no active trade, WR >= threshold
        if active_trade is None and wr >= entry_threshold:
            active_trade = {
                "ticker": ticker,
                "entry_price": price,
                "entry_date": date,
                "entry_bar_idx": bar_idx,
                "entry_wr": wr,
            }

    # Close any remaining active trade at last bar
    if active_trade:
        ticker = active_trade["ticker"]
        bars = bars_lookup[ticker]
        last_price = bars["close"].values[-1]
        last_date = str(bars["bar_date"].values[-1])
        hold_days = len(bars) - 1 - active_trade["entry_bar_idx"]
        active_trade["exit_price"] = float(last_price)
        active_trade["exit_date"] = last_date
        active_trade["exit_bar_idx"] = len(bars) - 1
        active_trade["exit_reason"] = "END_OF_DATA"
        active_trade["return"] = (float(last_price) - active_trade["entry_price"]) / active_trade["entry_price"]
        active_trade["hold_days"] = hold_days
        trades.append(active_trade)

    return trades


def main():
    print("=" * 70)
    print("TP BACKTEST — pure numpy, no ML, no SPY gate, no conjunctions")
    print("=" * 70)
    print(f"Config: {N_NEIGHBORS} neighbors, {N_DIM}-dim tuple, {FORWARD_DAYS}d horizon")
    print(f"Entry thresholds: {ENTRY_THRESHOLDS}")
    print(f"Exit: WR < {EXIT_WR_THRESHOLD}, floor {CATASTROPHIC_FLOOR*100:.0f}%, max hold {MAX_HOLD}d")
    print()

    conn = connect_db()
    cur = conn.cursor()

    # Load CS-only tickers
    all_cs = load_cs_tickers()
    print(f"CS-only universe: {len(all_cs)} tickers")

    # Find tickers with enough bars
    cur.execute("""
        SELECT symbol, COUNT(*) as n
        FROM daily_bars
        WHERE symbol = ANY(%s)
        GROUP BY symbol
        HAVING COUNT(*) >= %s
        ORDER BY symbol
    """, (all_cs, MIN_HISTORY + FORWARD_DAYS))
    eligible = cur.fetchall()
    print(f"Eligible (>= {MIN_HISTORY + FORWARD_DAYS} bars): {len(eligible)} tickers")

    # Sample with explicit seed for reproducibility
    seed = int(os.environ.get("TP_SEED", "42"))
    rng = random.Random(seed)
    eligible_shuffled = list(eligible)
    rng.shuffle(eligible_shuffled)
    sample = eligible_shuffled[:SAMPLE_SIZE]
    sample_tickers = [r[0] for r in sample]
    print(f"Sampled: {len(sample_tickers)} tickers (seed={seed})")
    print(f"Sampled: {len(sample_tickers)} tickers")
    print()

    # Load all bars for sampled tickers
    print("Loading bars...", flush=True)
    bars_lookup = {}
    for ticker in sample_tickers:
        cur.execute(
            "SELECT bar_date, close FROM daily_bars WHERE symbol = %s ORDER BY bar_date ASC",
            (ticker,),
        )
        rows = cur.fetchall()
        bars_lookup[ticker] = pd.DataFrame(rows, columns=["bar_date", "close"])

    conn.close()

    # Load SPY for benchmark
    conn2 = connect_db()
    cur2 = conn2.cursor()
    cur2.execute("SELECT bar_date, close FROM daily_bars WHERE symbol = 'SPY' ORDER BY bar_date ASC")
    spy_rows = cur2.fetchall()
    conn2.close()
    if spy_rows:
        spy_start = float(spy_rows[0][1])
        spy_end = float(spy_rows[-1][1])
        spy_return = (spy_end - spy_start) / spy_start
        print(f"SPY benchmark: {spy_start:.2f} → {spy_end:.2f} = {spy_return*100:+.1f}%")
    else:
        spy_return = None
        print("SPY: not available")
    print()

    # Run kernel on each ticker
    print(f"Running kernel on {len(sample_tickers)} tickers (this takes a while)...")
    all_signals = {}
    t0 = time.time()
    done = 0
    for ticker in sample_tickers:
        bars_df = bars_lookup[ticker]
        signals = run_backtest_for_ticker(ticker, bars_df)
        if signals:
            all_signals[ticker] = signals
        done += 1
        if done % 25 == 0:
            elapsed = time.time() - t0
            rate = done / elapsed
            eta = (len(sample_tickers) - done) / rate
            print(f"  {done}/{len(sample_tickers)} tickers done ({rate:.1f}/s, ETA {eta/60:.0f}m)", flush=True)

    elapsed = time.time() - t0
    total_sigs = sum(len(s) for s in all_signals.values())
    print(f"\nKernel complete: {len(all_signals)} tickers with signals, {total_sigs} total data points, {elapsed:.0f}s")
    print()

    # Simulate trades at each entry threshold
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    for threshold in ENTRY_THRESHOLDS:
        all_trades = []
        for ticker, signals in all_signals.items():
            trades = simulate_trades(signals, bars_lookup, threshold)
            all_trades.extend(trades)

        n_signals = sum(
            1 for sigs in all_signals.values()
            for s in sigs
            if s["neighbor_wr"] >= threshold
        )
        n_trades = len(all_trades)

        if n_trades == 0:
            print(f"\nEntry >= {threshold:.2f}: {n_signals} signals, 0 trades")
            continue

        returns = [t["return"] for t in all_trades]
        wins = sum(1 for r in returns if r > 0)
        wr = wins / n_trades

        # Exit reason breakdown
        exit_reasons = defaultdict(int)
        for t in all_trades:
            exit_reasons[t["exit_reason"]] += 1

        # Simulated portfolio return (equal weight, sequential per stock)
        total_return = sum(returns)
        avg_return = np.mean(returns)
        median_return = np.median(returns)
        avg_hold = np.mean([t["hold_days"] for t in all_trades])

        # Wilson confidence interval for WR
        z = 1.96
        p = wr
        n = n_trades
        denom = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denom
        margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
        ci_low = max(0, center - margin)
        ci_high = min(1, center + margin)

        print(f"\n{'─' * 50}")
        print(f"Entry >= {threshold:.2f}")
        print(f"{'─' * 50}")
        print(f"  Signals:       {n_signals}")
        print(f"  Trades:        {n_trades}")
        print(f"  Win Rate:      {wr*100:.1f}%  (95% CI: {ci_low*100:.1f}% – {ci_high*100:.1f}%)")
        print(f"  Avg Return:    {avg_return*100:+.2f}%")
        print(f"  Median Return: {median_return*100:+.2f}%")
        print(f"  Total Return:  {total_return*100:+.1f}% (sum of all trade returns)")
        print(f"  Avg Hold:      {avg_hold:.1f} days")
        if spy_return is not None:
            print(f"  SPY B&H:       {spy_return*100:+.1f}%")
        print(f"  Exits:")
        for reason, count in sorted(exit_reasons.items()):
            print(f"    {reason}: {count} ({count/n_trades*100:.0f}%)")

        # Save trade list for portfolio simulation
        trades_file = f"/tmp/tp_trades_{threshold:.2f}.json"
        with open(trades_file, "w") as f:
            json.dump(all_trades, f)
        print(f"  Trades saved: {trades_file}")

    print(f"\n{'=' * 70}")
    print("Done.")


if __name__ == "__main__":
    main()
