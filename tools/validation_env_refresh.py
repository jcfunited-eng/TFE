#!/usr/bin/env python3
"""
tools/validation_env_refresh.py — TFE Validation Environment Refresh

Fetches daily bars from Polygon, runs L0-L4 kernel + CP-2 cognitive scalars,
writes structural output to local PostgreSQL. Mirrors production pipeline.

Usage:
    python3 tools/validation_env_refresh.py                    # incremental (new bars only)
    python3 tools/validation_env_refresh.py --full             # full refresh (all history)
    python3 tools/validation_env_refresh.py --tickers SPY,AAPL # specific tickers only

Database: tfe_validation on localhost (PostgreSQL 17)
API: Polygon (MASSIVE_API_KEY from .env)
Kernel: production L0-L4 (uf_core/) + CP-2 (uf_mdg_snapshot.py)
"""

import sys
import os
import json
import time
import subprocess
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import psycopg2
import psycopg2.extras
import numpy as np
import pandas as pd
import urllib.request

from uf_core.uf_structural_engine import compute_uf_structural_state
from uf_mdg_snapshot import compute_cognitive_scalars

POLYGON_KEY = os.environ.get("MASSIVE_API_KEY", "")
YEARS_HISTORY = 5  # Must match production exactly (uf_mdg_snapshot.py line 84)
BATCH_LOG_EVERY = 200


def get_kernel_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path(__file__).resolve().parent.parent)
        ).decode().strip()
    except Exception:
        return "unknown"


def connect_local():
    return psycopg2.connect(
        host="/var/run/postgresql",
        dbname="tfe_validation",
        user="postgres"
    )


def load_universe():
    path = Path(__file__).resolve().parent.parent / "massive_universe_stocks.json"
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        tickers = []
        for item in data:
            if isinstance(item, dict):
                t = item.get("ticker", "")
            else:
                t = str(item)
            t = t.strip().upper()
            if t:
                tickers.append(t)
        return tickers
    return []


def fetch_bars(ticker, start, end):
    url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
           f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_KEY}")
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(url, timeout=30)
            data = json.loads(resp.read())
            if data.get("status") == "OK":
                return data.get("results", [])
            return []
        except Exception:
            if attempt < 2:
                time.sleep(2)
    return []


def get_last_bar_date(cur, ticker):
    cur.execute(
        "SELECT MAX(bar_date) FROM daily_bars WHERE symbol = %s",
        (ticker,)
    )
    row = cur.fetchone()
    return row[0] if row and row[0] else None


def cache_bars(cur, ticker, bars):
    for b in bars:
        bar_date = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        cur.execute("""
            INSERT INTO daily_bars (symbol, bar_date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, bar_date) DO NOTHING
        """, (ticker, bar_date, b["o"], b["h"], b["l"], b["c"], b.get("v", 0)))


def load_cached_bars(cur, ticker):
    cur.execute(
        "SELECT bar_date, close FROM daily_bars WHERE symbol = %s ORDER BY bar_date ASC",
        (ticker,)
    )
    return cur.fetchall()


def run_kernel(ticker, bar_rows):
    if len(bar_rows) < 20:
        return None

    closes = pd.Series(
        [float(r[1]) for r in bar_rows],
        index=[pd.Timestamp(r[0]) for r in bar_rows]
    ).sort_index()

    uf_state = compute_uf_structural_state(closes)

    close_array = np.array([float(r[1]) for r in bar_rows], dtype=float)
    cognitive = compute_cognitive_scalars(close_array)

    snap = {
        "ticker": ticker,
        "price": float(closes.iloc[-1]),
        "bar_count": len(bar_rows),
        "asset_type": "stock",
        "regime": uf_state.level3.get("regime"),
        "S_UF": uf_state.level4.get("S_UF"),
        "R_UF": uf_state.level4.get("R_UF"),
        "stability_score": uf_state.level4.get("stability_score"),
        "max_dd": uf_state.level4.get("max_drawdown"),
        "D_k": uf_state.level5.get("D_k"),
        "M_k": uf_state.level5.get("M_k"),
        "R_rev_k": uf_state.level5.get("R_rev_k"),
        "U_star_k": uf_state.level5.get("U_star_k"),
        "C_k": uf_state.level5.get("C_k"),
        "P_k": uf_state.level5.get("P_k"),
        "B_k": uf_state.level5.get("B_k"),
        "prev_C_k": uf_state.level5.get("prev_C_k"),
        "gate_count": uf_state.level5.get("gate_count"),
        "active_gate_count": uf_state.level5.get("active_gate_count"),
        "decision_vector": uf_state.level5.get("decision_vector"),
        "F_n": cognitive.get("F_n"),
        "raw_x_m": cognitive.get("raw_x_m"),
    }

    return snap


def write_output(cur, ticker, snap, run_id, kernel_sha):
    decision = "Hold"
    d_k = snap.get("D_k")
    s_uf = snap.get("S_UF")
    if d_k == 1 and s_uf is not None and s_uf >= 0.5:
        decision = "Accumulate"

    snap_json = json.dumps(snap)

    cur.execute("""
        INSERT INTO runtime_decisions_latest
            (ticker, decision_label, snapshot_row_json, generated_at_utc, run_id, kernel_sha, source)
        VALUES (%s, %s, %s, NOW(), %s, %s, 'validation_runner')
        ON CONFLICT (ticker) DO UPDATE SET
            decision_label = EXCLUDED.decision_label,
            snapshot_row_json = EXCLUDED.snapshot_row_json,
            generated_at_utc = EXCLUDED.generated_at_utc,
            run_id = EXCLUDED.run_id,
            kernel_sha = EXCLUDED.kernel_sha,
            source = EXCLUDED.source
    """, (ticker, decision, snap_json, run_id, kernel_sha))

    cur.execute("""
        INSERT INTO runtime_decisions_history
            (ticker, decision_label, snapshot_row_json, generated_at_utc, run_id, kernel_sha, source)
        VALUES (%s, %s, %s, NOW(), %s, %s, 'validation_runner')
    """, (ticker, decision, snap_json, run_id, kernel_sha))


def main():
    parser = argparse.ArgumentParser(description="TFE Validation Environment Refresh")
    parser.add_argument("--full", action="store_true", help="Full refresh (all history)")
    parser.add_argument("--tickers", type=str, help="Comma-separated ticker list")
    args = parser.parse_args()

    if not POLYGON_KEY:
        print("ERROR: No MASSIVE_API_KEY in .env")
        sys.exit(1)

    kernel_sha = get_kernel_sha()
    run_id = f"val_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    print("=" * 70)
    print("TFE VALIDATION ENVIRONMENT REFRESH")
    print(f"Kernel SHA: {kernel_sha[:12]}")
    print(f"Run ID: {run_id}")
    print(f"Mode: {'FULL' if args.full else 'INCREMENTAL'}")
    print("=" * 70)

    conn = connect_local()
    conn.autocommit = True
    cur = conn.cursor()

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = load_universe()

    print(f"Universe: {len(tickers)} tickers")

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    t0 = time.time()
    processed = 0
    errors = 0

    for ticker in tickers:
        try:
            if args.full:
                start = (datetime.now(timezone.utc) - timedelta(days=YEARS_HISTORY * 365)).strftime("%Y-%m-%d")
            else:
                last = get_last_bar_date(cur, ticker)
                if last:
                    start = (last + timedelta(days=1)).strftime("%Y-%m-%d")
                    if start >= end_date:
                        bar_rows = load_cached_bars(cur, ticker)
                        if bar_rows:
                            snap = run_kernel(ticker, bar_rows)
                            if snap:
                                write_output(cur, ticker, snap, run_id, kernel_sha)
                                processed += 1
                        if processed % BATCH_LOG_EVERY == 0 and processed > 0:
                            elapsed = time.time() - t0
                            rate = processed / elapsed * 3600
                            print(f"  {processed}/{len(tickers)} | {elapsed:.0f}s | {rate:.0f}/hr | errors={errors}")
                        continue
                else:
                    start = (datetime.now(timezone.utc) - timedelta(days=YEARS_HISTORY * 365)).strftime("%Y-%m-%d")

            bars = fetch_bars(ticker, start, end_date)
            if bars:
                cache_bars(cur, ticker, bars)

            bar_rows = load_cached_bars(cur, ticker)
            if not bar_rows:
                errors += 1
                continue

            snap = run_kernel(ticker, bar_rows)
            if snap is None:
                errors += 1
                continue

            write_output(cur, ticker, snap, run_id, kernel_sha)
            processed += 1

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR {ticker}: {e}")

        if processed % BATCH_LOG_EVERY == 0 and processed > 0:
            elapsed = time.time() - t0
            rate = processed / elapsed * 3600
            print(f"  {processed}/{len(tickers)} | {elapsed:.0f}s | {rate:.0f}/hr | errors={errors}")

    elapsed = time.time() - t0

    cur.execute("SELECT COUNT(*) FROM runtime_decisions_latest")
    latest = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM runtime_decisions_history")
    history = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM daily_bars")
    bars_total = cur.fetchone()[0]

    print(f"\n{'=' * 70}")
    print(f"REFRESH COMPLETE")
    print(f"  Processed: {processed} | Errors: {errors} | Time: {elapsed:.0f}s")
    print(f"  runtime_decisions_latest: {latest}")
    print(f"  runtime_decisions_history: {history}")
    print(f"  daily_bars: {bars_total}")
    print(f"{'=' * 70}")

    conn.close()


if __name__ == "__main__":
    main()
