"""Reconcile a local channel book and measure its return above SPY.

Observation only: no signals, orders, data fetching, or kernel changes.
Every SPY session is valued, including sessions without entries. Missing
marks, inconsistent cash, duplicate source bars and invalid records fail.
Recorded P&L includes the book's charged costs; open-position costs not yet
charged by the book are explicitly excluded. This is not broker fill proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path

import pandas as pd


def finite(value, name, *, positive=False):
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"invalid {name}")
    return number


def measure(book, market, start, end):
    """Start/end are explicit completed-close valuation dates, inclusive.

    Starting cash is invested in the benchmark at the start close. All
    strategy entries must occur strictly after that close. The entire book
    must belong to this interval; a partial ledger is not silently accepted.
    """
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start >= end:
        raise ValueError("start must precede end")
    capital = finite(book["start"], "starting capital", positive=True)
    cash_recorded = finite(book["cash"], "cash")
    trades = []
    for record in book["closed"]:
        trades.append(dict(record, closed=True))
    for symbol, record in book["positions"].items():
        if "symbol" in record and record["symbol"] != symbol:
            raise ValueError("position symbol disagrees with book key")
        trades.append(dict(record, symbol=symbol, closed=False))
    for trade in trades:
        trade["entry_day"] = date.fromisoformat(str(trade["entry_date"])[:10])
        trade["exit_day"] = (
            date.fromisoformat(str(trade["exit_at"])[:10]) if trade["closed"] else None
        )
        if not start < trade["entry_day"] <= end:
            raise ValueError(f"entry outside valuation interval: {trade['symbol']}")
        if trade["closed"] and not trade["entry_day"] <= trade["exit_day"] <= end:
            raise ValueError(f"exit outside valuation interval: {trade['symbol']}")
        trade["shares"] = finite(trade["shares"], "shares", positive=True)
        trade["entry_px"] = finite(trade["entry_px"], "entry price", positive=True)
        if trade["side"] not in (-1, 1):
            raise ValueError("side must be -1 or 1")
        trade["notional"] = trade["shares"] * trade["entry_px"]
        if not trade["closed"] and abs(
            finite(book["positions"][trade["symbol"]]["notional"], "notional")
            - trade["notional"]
        ) > 0.011:
            raise ValueError(f"position notional mismatch: {trade['symbol']}")
        if trade["closed"]:
            trade["exit_px"] = finite(trade["exit_px"], "exit price", positive=True)
            trade["pnl"] = finite(trade["pnl"], "net P&L")

    expected_cash = capital + sum(t["pnl"] for t in trades if t["closed"]) - sum(
        t["notional"] for t in trades if not t["closed"]
    )
    if abs(cash_recorded - expected_cash) > 0.011:
        raise ValueError(f"cash reconciliation failed: recorded={cash_recorded}, ledger={expected_cash}")

    frame = market.copy()
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.date
    frame = frame[(frame.Date >= start) & (frame.Date <= end)]
    wanted = {t["symbol"] for t in trades} | {"SPY"}
    frame = frame[frame.Symbol.isin(wanted)]
    if frame.duplicated(["Symbol", "Date"]).any():
        raise ValueError("duplicate source bars")
    marks = {}
    for row in frame.itertuples(index=False):
        marks[(row.Symbol, row.Date)] = finite(row.Close, "mark", positive=True)
    sessions = sorted(day for symbol, day in marks if symbol == "SPY")
    if not sessions or sessions[0] != start or sessions[-1] != end:
        raise ValueError("SPY must cover both exact valuation endpoints")
    session_set = set(sessions)
    for t in trades:
        if t["entry_day"] not in session_set or (
            t["closed"] and t["exit_day"] not in session_set
        ):
            raise ValueError("trade date missing from SPY session calendar")

    curve = []
    for day in sessions:
        realized = sum(t["pnl"] for t in trades if t["closed"] and t["exit_day"] <= day)
        unrealized = 0.0
        for t in trades:
            if t["entry_day"] <= day and (not t["closed"] or t["exit_day"] > day):
                key = (t["symbol"], day)
                if key not in marks:
                    raise ValueError(f"missing held-position mark: {key[0]} {day}")
                unrealized += t["shares"] * (marks[key] - t["entry_px"]) * t["side"]
        curve.append({"date": str(day), "equity": capital + realized + unrealized,
                      "spy_equity": capital * marks[("SPY", day)] / marks[("SPY", start)]})
    strategy_return = 100 * (curve[-1]["equity"] / capital - 1)
    spy_return = 100 * (curve[-1]["spy_equity"] / capital - 1)
    closed = [t for t in trades if t["closed"]]
    wins = sum(t["pnl"] > 0 for t in closed)
    peak = capital
    drawdown = 0.0
    for point in curve:
        peak = max(peak, point["equity"])
        drawdown = min(drawdown, 100 * (point["equity"] / peak - 1))
    return {
        "valuation_start": str(start), "valuation_end": str(end),
        "strategy_return_pct": strategy_return, "spy_return_pct": spy_return,
        "lift_percentage_points": strategy_return - spy_return,
        "closed_positions": len(closed), "winning_closed_positions": wins,
        "win_rate_pct": 100 * wins / len(closed) if closed else None,
        "open_positions": len(trades) - len(closed),
        "recorded_realized_pnl": sum(t["pnl"] for t in closed),
        "max_drawdown_pct": drawdown, "cash_reconciled": True,
        "benchmark_basis": "SPY supplied close-price return; distributions not separately credited",
        "cost_basis": "recorded closed P&L; uncharged open carry/liquidation costs excluded",
        "evidence_class": "local book reconstruction, not verified broker execution",
        "curve": curve,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.book.read_bytes()
    book = json.loads(raw)
    symbols = sorted({r["symbol"] for r in book["closed"]} | set(book["positions"]) | {"SPY"})
    bars = pd.read_parquet(args.bars, columns=["Date", "Symbol", "Close"],
                           filters=[("Symbol", "in", symbols)])
    report = measure(book, bars, args.start, args.end)
    report["source_book_sha256"] = hashlib.sha256(raw).hexdigest()
    report["source_book"] = str(args.book)
    report["source_bars"] = str(args.bars)
    canonical_bars = bars.sort_values(["Symbol", "Date"]).to_csv(index=False).encode()
    report["selected_source_bars_sha256"] = hashlib.sha256(canonical_bars).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        json.dump(report, out, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in report.items() if k != "curve"}, indent=2))


if __name__ == "__main__":
    main()
