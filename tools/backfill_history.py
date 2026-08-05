#!/usr/bin/env python3
"""
Backfill runtime_decisions_history with historical kernel outputs.

Runs the kernel at weekly bar positions for each CS-only ticker,
producing ~260 historical snapshots per ticker (5 years × 52 weeks).
Writes results to runtime_decisions_history so the tuple-proximity decision
engine has enough neighbors (needs 30+) to compute WR.

Validation env only. Do not run against production without explicit approval.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from uf_core.uf_structural_engine import compute_uf_structural_state

# ── Config ──────────────────────────────────────────────────────────
STEP = 5            # Run kernel every 5 bars (~weekly)
MIN_BARS = 100      # Minimum bars before first kernel run
BATCH_SIZE = 50     # Commit every N tickers
RUN_ID = f"backfill_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def connect_db():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "/var/run/postgresql"),
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ.get("PGDATABASE", "tfeapp"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )


def load_cs_tickers():
    # Works both from tools/ dir and from /tmp/ inside container
    path = os.path.join(os.path.dirname(__file__), "..", "massive_universe_stocks.json")
    if not os.path.exists(path):
        path = os.path.join(os.getcwd(), "massive_universe_stocks.json")
    if not os.path.exists(path):
        path = "/app/massive_universe_stocks.json"
    with open(path) as f:
        data = json.load(f)
    return [
        item["ticker"].upper()
        for item in data
        if isinstance(item, dict) and item.get("type") == "CS" and item.get("active")
    ]


def ensure_history_table(cur):
    # Table may already exist in production — just add source column if missing
    cur.execute("""
        CREATE TABLE IF NOT EXISTS runtime_decisions_history (
            id SERIAL PRIMARY KEY,
            ticker TEXT NOT NULL,
            decision_label TEXT,
            snapshot_row_json JSONB,
            generated_at_utc TIMESTAMPTZ NOT NULL,
            run_id TEXT,
            kernel_sha TEXT,
            source TEXT DEFAULT 'backfill',
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    # No ALTER TABLE — production schema is authoritative. Backfill rows
    # are identified by run_id LIKE 'backfill_%' instead of a source column.
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rdh_ticker_date
        ON runtime_decisions_history(ticker, generated_at_utc)
    """)


def run_kernel_at_position(closes_series, i):
    """Run kernel on close series up to position i. Returns snapshot dict or None."""
    sub = closes_series.iloc[:i + 1]
    if len(sub) < 20:
        return None

    try:
        state = compute_uf_structural_state(sub)
    except Exception:
        return None

    l5 = state.level5
    D_k = l5.get("D_k")
    if D_k is None:
        return None

    return {
        "D_k": l5.get("D_k"),
        "M_k": l5.get("M_k"),
        "B_k": l5.get("B_k"),
        "R_rev_k": l5.get("R_rev_k"),
        "U_star_k": l5.get("U_star_k"),
        "C_k": l5.get("C_k"),
        "P_k": l5.get("P_k"),
        "S_UF": state.level4.get("S_UF"),
        "R_UF": state.level4.get("R_UF"),
        "stability_score": state.level4.get("stability_score"),
        "max_dd": state.level4.get("max_drawdown"),
        "regime": state.level3.get("regime"),
        "bar_count": len(sub),
        "gate_count": l5.get("gate_count"),
        "price": float(sub.iloc[-1]),
    }


def backfill_ticker(cur, ticker, bars_df):
    """Run kernel at every STEP-th bar and insert into history."""
    closes = bars_df["close"].values.astype(float)
    dates = bars_df["bar_date"].values
    n_bars = len(closes)

    if n_bars < MIN_BARS:
        return 0

    close_series = pd.Series(
        closes,
        index=[pd.Timestamp(d) for d in dates],
    ).sort_index()

    inserted = 0
    for i in range(MIN_BARS, n_bars, STEP):
        snap = run_kernel_at_position(close_series, i)
        if snap is None:
            continue

        snap["ticker"] = ticker
        bar_date = str(dates[i])

        # Production PK is (run_id, ticker) — use unique run_id per date
        bar_run_id = f"backfill_{bar_date}"
        cur.execute(
            """INSERT INTO runtime_decisions_history
               (run_id, ticker, generated_at_utc, snapshot_row_json, updated_at)
               VALUES (%s, %s, %s, %s::jsonb, NOW())
               ON CONFLICT (run_id, ticker) DO NOTHING""",
            (bar_run_id, ticker, bar_date, json.dumps(snap)),
        )
        inserted += 1

    return inserted


def main():
    print("=" * 60)
    print("HISTORY BACKFILL — kernel at historical bar positions")
    print("=" * 60)
    print(f"Config: step={STEP} bars, min_bars={MIN_BARS}")
    print(f"Run ID: {RUN_ID}")
    print()

    conn = connect_db()
    conn.autocommit = False
    cur = conn.cursor()

    ensure_history_table(cur)
    conn.commit()

    # Check existing backfill
    cur.execute("SELECT COUNT(*) FROM runtime_decisions_history WHERE run_id LIKE 'backfill_%'")
    existing = cur.fetchone()[0]
    if existing > 0:
        print(f"WARNING: {existing} existing backfill rows found. Skipping already-backfilled tickers.")

    # Load CS-only tickers
    all_cs = load_cs_tickers()
    print(f"CS-only universe: {len(all_cs)} tickers")

    # Find tickers with enough bars
    cur.execute("""
        SELECT ticker, COUNT(*) as n
        FROM daily_bars
        WHERE ticker = ANY(%s)
        GROUP BY ticker
        HAVING COUNT(*) >= %s
        ORDER BY ticker
    """, (all_cs, MIN_BARS))
    eligible = cur.fetchall()
    print(f"Eligible (>= {MIN_BARS} bars): {len(eligible)} tickers")

    # Skip already-backfilled tickers
    if existing > 0:
        cur.execute("""
            SELECT DISTINCT ticker FROM runtime_decisions_history
            WHERE run_id LIKE 'backfill_%'
        """)
        done_tickers = {r[0] for r in cur.fetchall()}
        eligible = [(t, n) for t, n in eligible if t not in done_tickers]
        print(f"After skipping already-backfilled: {len(eligible)} tickers")

    print()

    total_inserted = 0
    t0 = time.time()

    for idx, (ticker, bar_count) in enumerate(eligible):
        cur.execute(
            "SELECT bar_date, close FROM daily_bars WHERE ticker = %s ORDER BY bar_date ASC",
            (ticker,),
        )
        rows = cur.fetchall()
        bars_df = pd.DataFrame(rows, columns=["bar_date", "close"])

        inserted = backfill_ticker(cur, ticker, bars_df)
        total_inserted += inserted

        if (idx + 1) % BATCH_SIZE == 0:
            conn.commit()
            elapsed = time.time() - t0
            rate = (idx + 1) / elapsed
            eta = (len(eligible) - idx - 1) / rate
            print(
                f"  {idx + 1}/{len(eligible)} tickers | "
                f"{total_inserted} rows | "
                f"{rate:.1f}/s | ETA {eta/60:.0f}m",
                flush=True,
            )

    conn.commit()
    elapsed = time.time() - t0

    print()
    print("=" * 60)
    print(f"Backfill complete.")
    print(f"  Tickers processed: {len(eligible)}")
    print(f"  Rows inserted: {total_inserted}")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Avg rows/ticker: {total_inserted / max(len(eligible), 1):.0f}")
    print("=" * 60)

    # Verify
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM runtime_decisions_history WHERE run_id LIKE 'backfill_%'")
    total, tickers = cur.fetchone()
    print(f"\nVerification: {total} backfill rows across {tickers} tickers")

    cur.execute("""
        SELECT ticker, COUNT(*) as n
        FROM runtime_decisions_history
        WHERE run_id LIKE 'backfill_%'
        GROUP BY ticker
        ORDER BY n DESC
        LIMIT 5
    """)
    print("Top tickers by history depth:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]} rows")

    conn.close()


if __name__ == "__main__":
    main()
