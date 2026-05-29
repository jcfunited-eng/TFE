#!/usr/bin/env python3
"""
Portfolio simulation on horse backtest trade list.

Takes the trade list JSON from horse_backtest.py and simulates:
- Starting capital: $100,000
- Equal weight: 2.5% per position ($2,500)
- Max concurrent positions: 30
- Sequential entry from cash; skip signals when no cash
- Equity curve, max drawdown, Sharpe, comparison vs SPY
"""

import json
import sys
import os
import numpy as np
import psycopg2
import pandas as pd
from collections import defaultdict


STARTING_CAPITAL = 100_000.0
POSITION_WEIGHT = 0.025  # 2.5% per position
MAX_POSITIONS = 30


def load_spy_daily():
    """Load SPY daily closes for benchmark comparison."""
    conn = psycopg2.connect(
        host="/var/run/postgresql", dbname="tfe_validation", user="postgres"
    )
    cur = conn.cursor()
    cur.execute("SELECT bar_date, close FROM daily_bars WHERE symbol = 'SPY' ORDER BY bar_date ASC")
    rows = cur.fetchall()
    conn.close()
    return {str(r[0]): float(r[1]) for r in rows}


def load_all_bars(tickers):
    """Load daily closes for all tickers in the trade list."""
    conn = psycopg2.connect(
        host="/var/run/postgresql", dbname="tfe_validation", user="postgres"
    )
    cur = conn.cursor()
    bars = {}
    for ticker in tickers:
        cur.execute(
            "SELECT bar_date, close FROM daily_bars WHERE symbol = %s ORDER BY bar_date ASC",
            (ticker,),
        )
        rows = cur.fetchall()
        bars[ticker] = {str(r[0]): float(r[1]) for r in rows}
    conn.close()
    return bars


def simulate(trades, threshold_label):
    """Run the portfolio simulation."""
    if not trades:
        print(f"  No trades for {threshold_label}")
        return

    # Get all unique tickers
    tickers = list(set(t["ticker"] for t in trades))

    # Load bar data for mark-to-market
    print(f"  Loading bars for {len(tickers)} tickers...")
    all_bars = load_all_bars(tickers)
    spy_daily = load_spy_daily()

    # Sort trades by entry date
    trades_sorted = sorted(trades, key=lambda t: t["entry_date"])

    # Build a timeline of all trading days from all bars
    all_dates = set()
    for bars in all_bars.values():
        all_dates.update(bars.keys())
    all_dates.update(spy_daily.keys())
    timeline = sorted(all_dates)

    if not timeline:
        print("  No timeline data")
        return

    # Find the date range from first entry to last exit
    first_entry = trades_sorted[0]["entry_date"]
    last_exit = max(t.get("exit_date", t["entry_date"]) for t in trades_sorted)
    timeline = [d for d in timeline if first_entry <= d <= last_exit]

    # Simulation state
    cash = STARTING_CAPITAL
    positions = {}  # ticker -> {shares, entry_price, entry_date, exit_date, exit_reason}
    equity_curve = []
    daily_returns = []
    prev_equity = STARTING_CAPITAL
    peak_equity = STARTING_CAPITAL
    max_drawdown = 0.0

    # Pre-index trades by entry_date for fast lookup
    trades_by_entry = defaultdict(list)
    for t in trades_sorted:
        trades_by_entry[t["entry_date"]].append(t)

    # Pre-index trades by exit_date
    trades_by_exit = defaultdict(list)
    for t in trades_sorted:
        if t.get("exit_date"):
            trades_by_exit[t["exit_date"]].append(t)

    total_trades_entered = 0
    total_trades_skipped = 0

    for date in timeline:
        # 1. Process exits first (free up cash and slots)
        for t in trades_by_exit.get(date, []):
            ticker = t["ticker"]
            if ticker in positions:
                pos = positions[ticker]
                exit_price = t.get("exit_price", pos["entry_price"])
                pnl = pos["shares"] * (exit_price - pos["entry_price"])
                cash += pos["shares"] * exit_price
                del positions[ticker]

        # 2. Process entries
        for t in trades_by_entry.get(date, []):
            ticker = t["ticker"]
            if ticker in positions:
                continue  # already holding

            if len(positions) >= MAX_POSITIONS:
                total_trades_skipped += 1
                continue

            position_size = STARTING_CAPITAL * POSITION_WEIGHT  # fixed $2,500
            if cash < position_size:
                total_trades_skipped += 1
                continue

            entry_price = t["entry_price"]
            shares = position_size / entry_price
            cash -= position_size
            positions[ticker] = {
                "shares": shares,
                "entry_price": entry_price,
                "entry_date": date,
                "exit_date": t.get("exit_date"),
            }
            total_trades_entered += 1

        # 3. Mark-to-market
        portfolio_value = cash
        for ticker, pos in positions.items():
            bars = all_bars.get(ticker, {})
            current_price = bars.get(date, pos["entry_price"])
            portfolio_value += pos["shares"] * current_price

        equity_curve.append((date, portfolio_value))

        # Daily return
        if prev_equity > 0:
            dr = (portfolio_value - prev_equity) / prev_equity
            daily_returns.append(dr)
        prev_equity = portfolio_value

        # Drawdown
        if portfolio_value > peak_equity:
            peak_equity = portfolio_value
        dd = (peak_equity - portfolio_value) / peak_equity
        if dd > max_drawdown:
            max_drawdown = dd

    # Results
    final_equity = equity_curve[-1][1] if equity_curve else STARTING_CAPITAL
    total_return = (final_equity - STARTING_CAPITAL) / STARTING_CAPITAL

    # SPY benchmark over same window
    spy_start_price = spy_daily.get(timeline[0])
    spy_end_price = spy_daily.get(timeline[-1])
    if spy_start_price and spy_end_price:
        spy_return = (spy_end_price - spy_start_price) / spy_start_price
    else:
        spy_return = None

    # Sharpe ratio (annualized, assuming 252 trading days)
    if len(daily_returns) > 30:
        dr_arr = np.array(daily_returns)
        mean_daily = np.mean(dr_arr)
        std_daily = np.std(dr_arr, ddof=1)
        if std_daily > 0:
            sharpe = (mean_daily / std_daily) * np.sqrt(252)
        else:
            sharpe = None
    else:
        sharpe = None

    # CAGR
    n_days = len(timeline)
    n_years = n_days / 252
    if n_years > 0 and final_equity > 0:
        cagr = (final_equity / STARTING_CAPITAL) ** (1 / n_years) - 1
    else:
        cagr = None

    print(f"\n  {'─' * 55}")
    print(f"  PORTFOLIO SIMULATION: Entry >= {threshold_label}")
    print(f"  {'─' * 55}")
    print(f"  Period:            {timeline[0]} → {timeline[-1]} ({n_days} trading days, {n_years:.1f} years)")
    print(f"  Starting Capital:  ${STARTING_CAPITAL:,.0f}")
    print(f"  Final Equity:      ${final_equity:,.0f}")
    print(f"  Total Return:      {total_return*100:+.1f}%")
    if cagr is not None:
        print(f"  CAGR:              {cagr*100:+.1f}%")
    print(f"  Max Drawdown:      {max_drawdown*100:.1f}%")
    if sharpe is not None:
        print(f"  Sharpe Ratio:      {sharpe:.2f}")
    if spy_return is not None:
        print(f"  SPY B&H Return:    {spy_return*100:+.1f}%")
        spy_cagr = ((1 + spy_return) ** (1 / n_years) - 1) if n_years > 0 else None
        if spy_cagr is not None:
            print(f"  SPY CAGR:          {spy_cagr*100:+.1f}%")
    print(f"  Trades Entered:    {total_trades_entered}")
    print(f"  Trades Skipped:    {total_trades_skipped} (no cash or max positions)")
    print(f"  Avg Positions:     {np.mean([len([p for p in positions]) for _ in range(1)]):.0f} (at end)")

    # Equity curve summary (quarterly snapshots)
    if len(equity_curve) > 60:
        print(f"\n  Equity Curve (quarterly snapshots):")
        step = len(equity_curve) // 8
        for i in range(0, len(equity_curve), step):
            d, eq = equity_curve[i]
            ret = (eq - STARTING_CAPITAL) / STARTING_CAPITAL
            print(f"    {d}: ${eq:>10,.0f}  ({ret*100:+.1f}%)")
        d, eq = equity_curve[-1]
        ret = (eq - STARTING_CAPITAL) / STARTING_CAPITAL
        print(f"    {d}: ${eq:>10,.0f}  ({ret*100:+.1f}%)")


def main():
    print("=" * 60)
    print("HORSE PORTFOLIO SIMULATION")
    print("=" * 60)
    print(f"Capital: ${STARTING_CAPITAL:,.0f} | Position: {POSITION_WEIGHT*100:.1f}% | Max: {MAX_POSITIONS}")
    print()

    for threshold in ["0.65", "0.70"]:
        trades_file = f"/tmp/horse_trades_{threshold}.json"
        if not os.path.exists(trades_file):
            print(f"  Trade file not found: {trades_file}")
            continue

        with open(trades_file) as f:
            trades = json.load(f)

        print(f"Loaded {len(trades)} trades for threshold >= {threshold}")
        simulate(trades, threshold)
        print()

    print("=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
