"""
tools/compute_species_profiles.py

Component 2: Per-Ticker Species Profile Computation
====================================================

Purpose:
  Compute the structural activity baseline δ̄_i for each ticker in the
  Accumulate universe. This implements Wave 2 of the Three-Wave Alignment
  (3WA) model from docs/structural_wave_alignment_spec.tex.

  Species classification (from quarantine_12k forensics, spec Definition 4):
    - Calm species (δ̄_i ≤ p25 of universe): +13.7pp premium on Wave 1 signals
    - Normal species (p25 < δ̄_i ≤ p75): standard structural dynamics
    - Volatile species (δ̄_i > p75): large routine transitions

  In production, the ideal proxy is mean|Δs_n| (bar-to-bar structural entropy
  change) per ticker from runtime_decisions_history. Since s_n is not yet in
  snapshot_row_json, this tool uses mean|ΔD_k| as the available proxy.

  When s_n becomes available in snapshot_row_json, update DELTA_FIELD below.

Measurement:
  For each ticker with ≥ MIN_BARS_REQUIRED history in runtime_decisions_history:
    1. Extract the ordered D_k (or s_n) time series
    2. Compute δ_t = |field[t] - field[t-1]| for consecutive bars
    3. δ̄_i = mean(δ_t) for bars > 5 (warm-up exclusion)
    4. Classify: calm if δ̄_i ≤ p25 of universe δ̄ distribution

Output (writes to stdout + optional --out-csv):
  ticker, delta_bar, classification, n_bars, n_deltas

Usage (requires DB tunnel on localhost:5432):
    python3 tools/compute_species_profiles.py
    python3 tools/compute_species_profiles.py --out-csv /tmp/species_profiles.csv
    python3 tools/compute_species_profiles.py --days 90

Environment:
    PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
    (source from tools/run_local_sync_via_tunnel.sh)
"""

from __future__ import annotations

import csv
import math
import os
import statistics
import sys
from collections import defaultdict
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────
HISTORY_DAYS      = 60    # look-back window for delta series
MIN_BARS_REQUIRED = 10    # minimum bars per ticker to include in distribution
WARMUP_BARS       = 5     # exclude first N bars from delta computation

# Primary field: D_k (available now).
# When s_n is in snapshot_row_json, change to "s_n" for the formal Wave 2 metric.
DELTA_FIELD = "D_k"


def parse_args() -> dict:
    args = {"out_csv": None, "days": HISTORY_DAYS, "dry_run": False}
    i = 1
    while i < len(sys.argv):
        tok = sys.argv[i]
        nxt = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        if tok == "--out-csv" and nxt:
            args["out_csv"] = nxt
            i += 2
        elif tok == "--days" and nxt:
            try:
                args["days"] = int(nxt)
            except ValueError:
                pass
            i += 2
        elif tok == "--dry-run":
            args["dry_run"] = True
            i += 1
        else:
            i += 1
    return args


def connect():
    required = ("PGHOST", "PGDATABASE", "PGUSER")
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print("Run: source <(tools/run_local_sync_via_tunnel.sh --print-env)", file=sys.stderr)
        sys.exit(1)

    conn_kwargs = dict(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", 5432)),
        user=os.environ["PGUSER"],
        dbname=os.environ["PGDATABASE"],
        sslmode="disable" if os.environ.get("TFE_DB_SSL_REJECT_UNAUTHORIZED") == "false" else "prefer",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    if os.environ.get("PGPASSWORD"):
        conn_kwargs["password"] = os.environ["PGPASSWORD"]
    return psycopg2.connect(**conn_kwargs)


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def fetch_field_history(cur, field: str, days: int) -> dict[str, list[float]]:
    """
    Fetch ordered field time series per Accumulate ticker from
    runtime_decisions_history for the given look-back window.

    Returns {ticker: [field_oldest, ..., field_newest]}.
    """
    json_key = field  # D_k, s_n, F_n etc.
    # Species baseline uses ALL bars regardless of decision label —
    # we're measuring the ticker's inherent structural activity, not filtering
    # to a decision cohort.
    cur.execute(f"""
        SELECT
            ticker,
            generated_at_utc,
            snapshot_row_json->>%s AS field_raw
        FROM runtime_decisions_history
        WHERE generated_at_utc >= NOW() - INTERVAL '{days} days'
        ORDER BY ticker, generated_at_utc ASC
    """, [json_key])

    result: dict[str, list[float]] = defaultdict(list)
    for row in cur.fetchall():
        val = safe_float(row["field_raw"])
        if val is not None:
            result[row["ticker"]].append(val)

    return dict(result)


def compute_delta_bar(series: list[float], warmup: int = WARMUP_BARS) -> Optional[float]:
    """
    Compute δ̄_i = mean|Δfield| for bars > warmup.
    Returns None if fewer than 2 post-warmup data points.
    """
    post_warmup = series[warmup:] if len(series) > warmup else []
    if len(post_warmup) < 2:
        return None
    deltas = [abs(post_warmup[i] - post_warmup[i - 1]) for i in range(1, len(post_warmup))]
    return statistics.mean(deltas) if deltas else None


def percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return float("nan")
    idx = int(len(sorted_vals) * pct / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def main() -> None:
    args = parse_args()
    days = args["days"]

    print("=" * 70)
    print(f"TFE COMPONENT 2: Species Profile Computation")
    print(f"Field: {DELTA_FIELD} | Window: {days} days | Warm-up: {WARMUP_BARS} bars")
    print("=" * 70)

    conn = connect()
    cur = conn.cursor()

    print(f"\nFetching {DELTA_FIELD} history from runtime_decisions_history...")
    field_history = fetch_field_history(cur, DELTA_FIELD, days)
    print(f"  {len(field_history)} tickers with {DELTA_FIELD} history (all decision labels).")

    if not field_history:
        print("No history found. Ensure runtime_decisions_history is populated.", file=sys.stderr)
        cur.close()
        conn.close()
        return

    # ── Compute δ̄_i per ticker ────────────────────────────────────────────────
    profiles: list[dict] = []
    skipped = 0

    for ticker, series in sorted(field_history.items()):
        n_bars = len(series)
        if n_bars < MIN_BARS_REQUIRED:
            skipped += 1
            continue
        delta_bar = compute_delta_bar(series, warmup=WARMUP_BARS)
        if delta_bar is None:
            skipped += 1
            continue
        profiles.append({
            "ticker": ticker,
            "delta_bar": delta_bar,
            "n_bars": n_bars,
            "n_deltas": max(0, n_bars - WARMUP_BARS - 1),
        })

    print(f"  Computed δ̄_i for {len(profiles)} tickers ({skipped} skipped — insufficient bars).")

    if not profiles:
        print("No profiles computed. Nothing to classify.", file=sys.stderr)
        cur.close()
        conn.close()
        return

    # ── Universe percentile distribution ──────────────────────────────────────
    delta_bars_sorted = sorted(p["delta_bar"] for p in profiles)
    n = len(delta_bars_sorted)
    p25 = percentile(delta_bars_sorted, 25)
    p50 = percentile(delta_bars_sorted, 50)
    p75 = percentile(delta_bars_sorted, 75)

    print(f"\n=== δ̄_i Distribution (n={n} tickers) ===")
    print(f"  min:    {delta_bars_sorted[0]:.6f}")
    print(f"  p25:    {p25:.6f}  ← calm/active boundary")
    print(f"  median: {p50:.6f}")
    print(f"  p75:    {p75:.6f}")
    print(f"  max:    {delta_bars_sorted[-1]:.6f}")
    try:
        print(f"  mean:   {statistics.mean(delta_bars_sorted):.6f}")
        print(f"  stdev:  {statistics.stdev(delta_bars_sorted):.6f}")
    except statistics.StatisticsError:
        pass

    # ── Classify each ticker (3-tier per spec Definition 4) ────────────────
    calm_count = 0
    normal_count = 0
    volatile_count = 0
    for p in profiles:
        if p["delta_bar"] <= p25:
            p["classification"] = "calm"
            calm_count += 1
        elif p["delta_bar"] > p75:
            p["classification"] = "volatile"
            volatile_count += 1
        else:
            p["classification"] = "normal"
            normal_count += 1

    print(f"\n=== Species Classification (DELTA_FIELD={DELTA_FIELD}) ===")
    print(f"  Calm species     (δ̄_i ≤ p25={p25:.6f}): {calm_count}/{n} ({100*calm_count/n:.1f}%)")
    print(f"  Normal species   (p25 < δ̄_i ≤ p75={p75:.6f}): {normal_count}/{n} ({100*normal_count/n:.1f}%)")
    print(f"  Volatile species (δ̄_i > p75):           {volatile_count}/{n} ({100*volatile_count/n:.1f}%)")
    print(f"\n  Note: Calm species in Wave 1 context → +13.7pp premium")
    print(f"  (Waves 1+2+3 backtest: 86.7% vs Waves 1+3: 84.5%, n=75)")

    print(f"\n=== Top 20 Calm Species ===")
    calm = sorted([p for p in profiles if p["classification"] == "calm"], key=lambda x: x["delta_bar"])
    for p in calm[:20]:
        print(f"  {p['ticker']:<8}  δ̄={p['delta_bar']:.6f}  n={p['n_bars']}")

    print(f"\n=== Top 10 Most Active Species (highest δ̄_i) ===")
    active_sorted = sorted(profiles, key=lambda x: x["delta_bar"], reverse=True)
    for p in active_sorted[:10]:
        print(f"  {p['ticker']:<8}  δ̄={p['delta_bar']:.6f}  n={p['n_bars']}")

    # ── Optional CSV output ───────────────────────────────────────────────────
    if args["out_csv"]:
        out_path = args["out_csv"]
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["ticker", "delta_bar", "classification", "n_bars", "n_deltas"])
            writer.writeheader()
            for p in sorted(profiles, key=lambda x: x["delta_bar"]):
                writer.writerow(p)
        print(f"\nWrote {len(profiles)} profiles to: {out_path}")

    # ── Write to species_profiles table ──────────────────────────────────────
    if not args.get("dry_run"):
        print(f"\n=== Writing to species_profiles table ===")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS species_profiles (
                ticker TEXT PRIMARY KEY,
                delta_bar DOUBLE PRECISION,
                sigma_bar DOUBLE PRECISION,
                classification TEXT,
                field_used TEXT,
                computed_at TIMESTAMPTZ,
                n_bars INT
            );
        """)
        # Truncate and repopulate — species profiles are a full recomputation
        cur.execute("DELETE FROM species_profiles;")
        insert_sql = """
            INSERT INTO species_profiles (ticker, delta_bar, classification, field_used, computed_at, n_bars)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        """
        for p in profiles:
            cur.execute(insert_sql, (
                p["ticker"], p["delta_bar"], p["classification"],
                DELTA_FIELD, p["n_bars"],
            ))
        conn.commit()
        verify_cur = conn.cursor()
        verify_cur.execute("SELECT COUNT(*) AS cnt FROM species_profiles;")
        row_count = verify_cur.fetchone()["cnt"]
        verify_cur.execute("SELECT classification, COUNT(*) AS cnt FROM species_profiles GROUP BY classification ORDER BY classification;")
        dist = {r["classification"]: r["cnt"] for r in verify_cur.fetchall()}
        verify_cur.close()
        print(f"  Wrote {row_count} rows to species_profiles.")
        for cls, cnt in sorted(dist.items()):
            print(f"    {cls}: {cnt}")
    else:
        print(f"\n=== DRY RUN — no DB write ===")

    print(f"\n=== 3WA Readiness ===")
    print(f"  Wave 2 (species profiles) computed from {n} tickers.")
    print(f"  Field used: {DELTA_FIELD} (proxy; upgrade to s_n when available in snapshot_row_json).")
    print(f"  p25 boundary: {p25:.6f}")
    print(f"  p75 boundary: {p75:.6f}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
