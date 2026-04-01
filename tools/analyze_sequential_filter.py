"""
tools/analyze_sequential_filter.py

Sequential cognitive filter validation against the current production snapshot.

Reads Accumulate rows from runtime_decisions_latest, extracts F_n / raw_x_m / close
from snapshot_row_json, applies the three-condition filter:

    Close  >= 5.0
    raw_x_m <= 0.50
    F_n    <= 1.65

Reports:
  - Total Accumulate count
  - F_n / raw_x_m population rate (how many rows have these fields populated)
  - Distribution stats for both fields
  - How many survive the filter, concentration by sector/symbol
  - Sample of surviving symbols

Usage (requires DB tunnel open on localhost:5432):
    python3 tools/analyze_sequential_filter.py

Environment:
    PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE   — or use tools/run_local_sync_via_tunnel.sh
    to export them before calling this script.
"""

from __future__ import annotations

import json
import os
import sys
import statistics
from collections import Counter
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)


# ── filter thresholds ────────────────────────────────────────────────────────
CLOSE_MIN   = 5.0
RAW_XM_MAX  = 0.50
FN_MAX      = 1.65


def connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", 5432)),
        user=os.environ.get("PGUSER", ""),
        password=os.environ.get("PGPASSWORD", ""),
        dbname=os.environ.get("PGDATABASE", "tfe_runtime"),
        sslmode="disable" if os.environ.get("TFE_DB_SSL_REJECT_UNAUTHORIZED") == "false" else "prefer",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if (f != f) else f  # NaN check
    except (TypeError, ValueError):
        return None


def main():
    print("Connecting to DB …")
    conn = connect()
    cur = conn.cursor()

    # ── pull all Accumulate rows ─────────────────────────────────────────────
    cur.execute("""
        SELECT
            ticker,
            decision,
            snapshot_row_json
        FROM runtime_decisions_latest
        WHERE decision = 'Accumulate'
        ORDER BY ticker
    """)
    rows = cur.fetchall()
    conn.close()

    total_accum = len(rows)
    print(f"\nTotal Accumulate rows: {total_accum}")
    if total_accum == 0:
        print("No Accumulate rows found. Nothing to analyze.")
        return

    # ── extract fields from snapshot JSON ────────────────────────────────────
    parsed = []
    fn_missing = 0
    xm_missing = 0
    close_missing = 0

    for r in rows:
        ticker = r["ticker"]
        snap_raw = r.get("snapshot_row_json")

        if snap_raw is None:
            snap = {}
        elif isinstance(snap_raw, str):
            try:
                snap = json.loads(snap_raw)
            except Exception:
                snap = {}
        else:
            snap = snap_raw  # already dict (jsonb column)

        close   = safe_float(snap.get("price") or snap.get("close") or snap.get("Close"))
        raw_x_m = safe_float(snap.get("raw_x_m"))
        f_n     = safe_float(snap.get("F_n") or snap.get("f_n"))

        if close   is None: close_missing += 1
        if raw_x_m is None: xm_missing    += 1
        if f_n     is None: fn_missing     += 1

        parsed.append({
            "ticker": ticker,
            "close":   close,
            "raw_x_m": raw_x_m,
            "f_n":     f_n,
            "snap":    snap,
        })

    print(f"\nField population out of {total_accum} Accumulate rows:")
    print(f"  close    populated: {total_accum - close_missing:>5}  ({(total_accum - close_missing)/total_accum*100:.1f}%)")
    print(f"  raw_x_m  populated: {total_accum - xm_missing:>5}  ({(total_accum - xm_missing)/total_accum*100:.1f}%)")
    print(f"  F_n      populated: {total_accum - fn_missing:>5}  ({(total_accum - fn_missing)/total_accum*100:.1f}%)")

    # ── distribution stats for populated fields ───────────────────────────────
    closes   = [p["close"]   for p in parsed if p["close"]   is not None]
    xm_vals  = [p["raw_x_m"] for p in parsed if p["raw_x_m"] is not None]
    fn_vals  = [p["f_n"]     for p in parsed if p["f_n"]     is not None]

    def pct(lst, pct_val):
        if not lst: return None
        s = sorted(lst)
        idx = int(len(s) * pct_val / 100)
        return s[min(idx, len(s) - 1)]

    if closes:
        print(f"\nClose price distribution (n={len(closes)}):")
        print(f"  min={min(closes):.2f}  p10={pct(closes,10):.2f}  p25={pct(closes,25):.2f}  median={statistics.median(closes):.2f}  p75={pct(closes,75):.2f}  p90={pct(closes,90):.2f}  max={max(closes):.2f}")

    if xm_vals:
        print(f"\nraw_x_m distribution (n={len(xm_vals)}):")
        print(f"  min={min(xm_vals):.4f}  p10={pct(xm_vals,10):.4f}  p25={pct(xm_vals,25):.4f}  median={statistics.median(xm_vals):.4f}  p75={pct(xm_vals,75):.4f}  p90={pct(xm_vals,90):.4f}  max={max(xm_vals):.4f}")

    if fn_vals:
        print(f"\nF_n distribution (n={len(fn_vals)}):")
        print(f"  min={min(fn_vals):.4f}  p10={pct(fn_vals,10):.4f}  p25={pct(fn_vals,25):.4f}  median={statistics.median(fn_vals):.4f}  p75={pct(fn_vals,75):.4f}  p90={pct(fn_vals,90):.4f}  max={max(fn_vals):.4f}")

    # ── apply filter ──────────────────────────────────────────────────────────
    print(f"\nApplying sequential filter:")
    print(f"  close >= {CLOSE_MIN}  AND  raw_x_m <= {RAW_XM_MAX}  AND  F_n <= {FN_MAX}")

    # Step through filter stages
    after_close   = [p for p in parsed if p["close"]   is not None and p["close"]   >= CLOSE_MIN]
    after_xm      = [p for p in after_close  if p["raw_x_m"] is not None and p["raw_x_m"] <= RAW_XM_MAX]
    after_fn      = [p for p in after_xm     if p["f_n"]     is not None and p["f_n"]     <= FN_MAX]

    print(f"\n  Stage 1 — Close >= {CLOSE_MIN}:            {len(after_close):>5} / {total_accum}  ({len(after_close)/total_accum*100:.1f}%)")
    print(f"  Stage 2 — raw_x_m <= {RAW_XM_MAX}:         {len(after_xm):>5} / {total_accum}  ({len(after_xm)/total_accum*100:.1f}%)")
    print(f"  Stage 3 — F_n <= {FN_MAX}:               {len(after_fn):>5} / {total_accum}  ({len(after_fn)/total_accum*100:.1f}%)")

    survivors = after_fn
    print(f"\nFilter survivors: {len(survivors)}")

    if not survivors:
        print("\nNo survivors — filter is too aggressive for current snapshot population.")
        return

    # ── concentration check ───────────────────────────────────────────────────
    # Pull sector/industry if available in snapshot
    sector_counts: Counter = Counter()
    for p in survivors:
        sector = p["snap"].get("sector") or p["snap"].get("industry") or "Unknown"
        sector_counts[sector] += 1

    print(f"\nSector concentration ({len(sector_counts)} sectors):")
    for sector, cnt in sector_counts.most_common(15):
        pct_of_survivors = cnt / len(survivors) * 100
        print(f"  {sector:<40} {cnt:>4}  ({pct_of_survivors:.1f}%)")

    # ── symbol list ───────────────────────────────────────────────────────────
    survivor_tickers = sorted(p["ticker"] for p in survivors)
    print(f"\nSurviving symbols ({len(survivor_tickers)}):")
    # Print in columns of 10
    for i in range(0, len(survivor_tickers), 10):
        print("  " + "  ".join(f"{t:<8}" for t in survivor_tickers[i:i+10]))

    # ── summary of filter survivor field values ───────────────────────────────
    s_closes = [p["close"]   for p in survivors if p["close"]   is not None]
    s_xm     = [p["raw_x_m"] for p in survivors if p["raw_x_m"] is not None]
    s_fn     = [p["f_n"]     for p in survivors if p["f_n"]     is not None]

    if s_closes:
        print(f"\nSurvivor close stats: min={min(s_closes):.2f}  median={statistics.median(s_closes):.2f}  max={max(s_closes):.2f}")
    if s_xm:
        print(f"Survivor raw_x_m stats: min={min(s_xm):.4f}  median={statistics.median(s_xm):.4f}  max={max(s_xm):.4f}")
    if s_fn:
        print(f"Survivor F_n stats: min={min(s_fn):.4f}  median={statistics.median(s_fn):.4f}  max={max(s_fn):.4f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
