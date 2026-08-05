#!/usr/bin/env python3
"""
Verify the tuple-proximity produces real WR values on backfilled history.
Runs on the validation env. Simulates what production sync would do.
"""

import json
import os
import sys
import numpy as np
import psycopg2
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

N_NEIGHBORS = 30
FORWARD_DAYS = 20
ENTRY_THRESHOLD = 0.65
EXIT_THRESHOLD = 0.40
TUPLE_FIELDS = ["D_k", "M_k", "B_k", "R_rev_k", "U_star_k", "C_k", "P_k"]
SAMPLE_SIZE = 200


def connect():
    return psycopg2.connect(
        host="/var/run/postgresql", dbname="tfe_validation", user="postgres"
    )


def extract_tuple(snap):
    vals = []
    for f in TUPLE_FIELDS:
        v = snap.get(f)
        if v is None:
            v = snap.get(f.lower())
        if v is None or np.isnan(float(v)):
            return None
        vals.append(float(v))
    return np.array(vals)


def compute_neighbor_wr(current, history_tuples, history_returns):
    if len(history_tuples) <= N_NEIGHBORS:
        return None
    ranges = np.ptp(history_tuples, axis=0)
    ranges = np.where(ranges < 1e-10, 1.0, ranges)
    diff = (history_tuples - current) / ranges
    dists = np.sqrt(np.sum(diff ** 2, axis=1))
    idx = np.argpartition(dists, N_NEIGHBORS)[:N_NEIGHBORS]
    wins = np.sum(history_returns[idx] > 0)
    return float(wins) / N_NEIGHBORS


def main():
    conn = connect()
    cur = conn.cursor()

    # Get tickers with enough backfill history
    cur.execute("""
        SELECT ticker, COUNT(*) as n
        FROM runtime_decisions_history
        WHERE source = 'backfill'
        GROUP BY ticker
        HAVING COUNT(*) > 50
        ORDER BY random()
        LIMIT %s
    """, (SAMPLE_SIZE,))
    tickers = [(r[0], r[1]) for r in cur.fetchall()]
    print(f"Sampled {len(tickers)} tickers with 50+ history rows")

    results = []
    for i, (ticker, hist_count) in enumerate(tickers):
        # Load history snapshots
        cur.execute("""
            SELECT snapshot_row_json, generated_at_utc::text
            FROM runtime_decisions_history
            WHERE ticker = %s AND source = 'backfill'
            ORDER BY generated_at_utc ASC
        """, (ticker,))
        history_rows = cur.fetchall()

        # Load price history
        cur.execute("""
            SELECT bar_date::text, close
            FROM daily_bars WHERE symbol = %s
            ORDER BY bar_date ASC
        """, (ticker,))
        price_rows = cur.fetchall()
        prices = {str(r[0]): float(r[1]) for r in price_rows}
        dates_sorted = sorted(prices.keys())

        # Build history tuples + forward returns
        hist_tuples = []
        hist_returns = []
        for snap_json, gen_date in history_rows:
            snap = snap_json if isinstance(snap_json, dict) else json.loads(snap_json)
            t = extract_tuple(snap)
            if t is None:
                continue
            date_str = gen_date[:10]
            date_idx = dates_sorted.index(date_str) if date_str in dates_sorted else -1
            if date_idx < 0:
                continue
            fwd_idx = date_idx + FORWARD_DAYS
            if fwd_idx >= len(dates_sorted):
                continue
            entry_p = prices[date_str]
            exit_p = prices[dates_sorted[fwd_idx]]
            if entry_p <= 0:
                continue
            hist_tuples.append(t)
            hist_returns.append((exit_p - entry_p) / entry_p)

        if len(hist_tuples) <= N_NEIGHBORS:
            continue

        hist_tuples = np.array(hist_tuples)
        hist_returns = np.array(hist_returns)

        # Use the LAST history point as "current" (simulates today's snapshot)
        current = hist_tuples[-1]
        # Use all but the last as history
        wr = compute_neighbor_wr(current, hist_tuples[:-1], hist_returns[:-1])
        if wr is None:
            continue

        decision = "Accumulate" if wr >= ENTRY_THRESHOLD else ("Avoid" if wr < EXIT_THRESHOLD else "Hold")
        results.append({
            "ticker": ticker,
            "wr": wr,
            "decision": decision,
            "history_size": len(hist_tuples),
        })

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(tickers)} done, {len(results)} with WR", flush=True)

    conn.close()

    # Report
    print(f"\n{'=' * 60}")
    print(f"TP VERIFICATION ON BACKFILLED DATA")
    print(f"{'=' * 60}")
    print(f"Tickers sampled: {len(tickers)}")
    print(f"Tickers with WR: {len(results)}")

    if not results:
        print("NO RESULTS — something is still wrong")
        return

    wrs = [r["wr"] for r in results]
    decisions = [r["decision"] for r in results]

    print(f"WR range: {min(wrs):.3f} – {max(wrs):.3f}")
    print(f"WR mean: {np.mean(wrs):.3f}")
    print(f"WR median: {np.median(wrs):.3f}")
    print()
    print(f"Decisions:")
    for d in ["Accumulate", "Hold", "Avoid"]:
        n = sum(1 for x in decisions if x == d)
        print(f"  {d}: {n} ({n/len(results)*100:.1f}%)")

    print()
    print("Sample of Accumulate signals (WR >= 0.65):")
    accum = [r for r in results if r["decision"] == "Accumulate"]
    for r in sorted(accum, key=lambda x: -x["wr"])[:15]:
        print(f"  {r['ticker']:8s} WR={r['wr']:.3f} history={r['history_size']}")

    print()
    print("Sample of Avoid signals (WR < 0.40):")
    avoid = [r for r in results if r["decision"] == "Avoid"]
    for r in sorted(avoid, key=lambda x: x["wr"])[:10]:
        print(f"  {r['ticker']:8s} WR={r['wr']:.3f} history={r['history_size']}")


if __name__ == "__main__":
    main()
