"""
tools/measure_exhaustion_telemetry.py

ALTE Quiescence Telemetry — Measurement Only

Purpose: Measure the real-world distribution of |ΔD_k| and consecutive
Quiescence durations (τ_in) across current Accumulate signals, to calibrate
the ALTE physics constants before any implementation.

This script does NOT apply or validate any constants. It measures distributions
so the architect can confirm or reject proposed threshold values.

Confirmed spec concepts being measured (ALTE Spec 1.3, Section 2.1):
  - Quiescence: ΔD_k ≈ 0 within a tolerance bound
  - τ_in: CONSECUTIVE bars the asset remains in Quiescence

NOT applied (pending spec completion):
  - LAMBDA_DECAY (not in any spec — Gemini hallucination)
  - Cohesion buffer epsilon decay (not in ALTE spec)
  - τ_out = floor(τ_in/3) ratio (pending Section 3.4 completion)
  - ZOMBIE_WARNING / CALAMITY_TRIGGER labels (Section 3.4 cut off)

Data source:
  - runtime_decisions_history: multi-run time series for consecutive D_k tracking
  - Falls back to runtime_decisions_latest if history unavailable

Usage (requires DB tunnel open on localhost:5432):
    python3 tools/measure_exhaustion_telemetry.py

Environment:
    PGHOST / PGPORT / PGUSER / PGPASSWORD / PGDATABASE
    (use tools/run_local_sync_via_tunnel.sh to export before calling)
"""

from __future__ import annotations

import json
import os
import sys
import math
import statistics
from collections import defaultdict
from typing import Optional

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

# ── Candidate thresholds to test (NOT confirmed constants) ───────────────────
# The measurement will report what fraction of bars qualify as Quiescent
# at each candidate threshold, so the architect can choose.
DELTA_Q_CANDIDATES = [0.01, 0.02, 0.05, 0.10, 0.20]

# How many historical runs to look back for τ_in measurement
HISTORY_DAYS = 30


def connect():
    required = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("Run: source <(tools/run_local_sync_via_tunnel.sh --print-env)", file=sys.stderr)
        sys.exit(1)

    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=int(os.environ.get("PGPORT", 5432)),
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        dbname=os.environ["PGDATABASE"],
        sslmode="disable" if os.environ.get("TFE_DB_SSL_REJECT_UNAUTHORIZED") == "false" else "prefer",
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def fetch_accumulate_tickers(cur) -> list[str]:
    """Get the current list of Accumulate tickers from the latest snapshot."""
    cur.execute("""
        SELECT ticker
        FROM runtime_decisions_latest
        WHERE decision_label = 'Accumulate'
        ORDER BY ticker
    """)
    return [row["ticker"] for row in cur.fetchall()]


def fetch_dk_history(cur, tickers: list[str]) -> dict[str, list[float]]:
    """
    Fetch ordered D_k time series per ticker from runtime_decisions_history.
    Returns {ticker: [d_k_oldest, ..., d_k_newest]}.
    """
    if not tickers:
        return {}

    placeholders = ",".join(["%s"] * len(tickers))
    cur.execute(f"""
        SELECT
            ticker,
            generated_at_utc,
            snapshot_row_json->>'D_k' AS d_k_raw
        FROM runtime_decisions_history
        WHERE ticker IN ({placeholders})
          AND generated_at_utc >= NOW() - INTERVAL '{HISTORY_DAYS} days'
          AND decision_label = 'Accumulate'
        ORDER BY ticker, generated_at_utc ASC
    """, tickers)

    result: dict[str, list[float]] = defaultdict(list)
    for row in cur.fetchall():
        dk = safe_float(row["d_k_raw"])
        if dk is not None:
            result[row["ticker"]].append(dk)

    return dict(result)


def fetch_dk_latest(cur, tickers: list[str]) -> dict[str, list[float]]:
    """
    Fallback: fetch D_k from latest snapshot only (single point, no history).
    Returns {ticker: [d_k]} — can only report point-in-time, not τ_in.
    """
    if not tickers:
        return {}

    placeholders = ",".join(["%s"] * len(tickers))
    cur.execute(f"""
        SELECT
            ticker,
            snapshot_row_json->>'D_k' AS d_k_raw
        FROM runtime_decisions_latest
        WHERE ticker IN ({placeholders})
    """, tickers)

    result: dict[str, list[float]] = {}
    for row in cur.fetchall():
        dk = safe_float(row["d_k_raw"])
        if dk is not None:
            result[row["ticker"]] = [dk]

    return result


def compute_delta_dk(series: list[float]) -> list[float]:
    """Compute |ΔD_k| = |D_k[i] - D_k[i-1]| for consecutive bars."""
    if len(series) < 2:
        return []
    return [abs(series[i] - series[i - 1]) for i in range(1, len(series))]


def max_consecutive_quiescence(delta_series: list[float], threshold: float) -> int:
    """
    Compute the maximum consecutive run of bars where |ΔD_k| <= threshold.
    This is τ_in per the ALTE spec (consecutive bar count in Quiescence state).
    """
    max_run = 0
    current_run = 0
    for delta in delta_series:
        if delta <= threshold:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run


def current_consecutive_quiescence(delta_series: list[float], threshold: float) -> int:
    """
    Compute the CURRENT (most recent trailing) consecutive run of quiescent bars.
    This is the live τ_in at the time of measurement.
    """
    run = 0
    for delta in reversed(delta_series):
        if delta <= threshold:
            run += 1
        else:
            break
    return run


def analyze(dk_history: dict[str, list[float]]) -> None:
    """
    Report distributions of |ΔD_k| and τ_in across all tickers.
    Pure measurement — no constants applied, no statuses assigned.
    """
    all_deltas: list[float] = []
    for series in dk_history.values():
        all_deltas.extend(compute_delta_dk(series))

    if not all_deltas:
        print("\nNo |ΔD_k| data available. Check history table population.")
        return

    all_deltas_sorted = sorted(all_deltas)
    n = len(all_deltas_sorted)

    print(f"\n=== |ΔD_k| Distribution (n={n} deltas across {len(dk_history)} tickers) ===")
    print(f"  min:    {all_deltas_sorted[0]:.6f}")
    print(f"  p10:    {all_deltas_sorted[int(n * 0.10)]:.6f}")
    print(f"  p25:    {all_deltas_sorted[int(n * 0.25)]:.6f}")
    print(f"  median: {all_deltas_sorted[int(n * 0.50)]:.6f}")
    print(f"  p75:    {all_deltas_sorted[int(n * 0.75)]:.6f}")
    print(f"  p90:    {all_deltas_sorted[int(n * 0.90)]:.6f}")
    print(f"  p95:    {all_deltas_sorted[int(n * 0.95)]:.6f}")
    print(f"  max:    {all_deltas_sorted[-1]:.6f}")
    try:
        print(f"  mean:   {statistics.mean(all_deltas):.6f}")
        print(f"  stdev:  {statistics.stdev(all_deltas):.6f}")
    except statistics.StatisticsError:
        pass

    print(f"\n=== Quiescence Coverage by Candidate DELTA_Q Threshold ===")
    print(f"  (What % of all delta bars qualify as Quiescent at each threshold)")
    for dq in DELTA_Q_CANDIDATES:
        quiescent = sum(1 for d in all_deltas if d <= dq)
        pct = 100.0 * quiescent / n if n else 0.0
        print(f"  DELTA_Q={dq:.2f}  →  {quiescent}/{n} bars quiescent ({pct:.1f}%)")

    print(f"\n=== Current τ_in (trailing consecutive quiescence) per ticker ===")
    print(f"  (Using each DELTA_Q candidate — shows live τ_in per ticker)")

    for dq in DELTA_Q_CANDIDATES:
        tau_ins = []
        for ticker, series in dk_history.items():
            deltas = compute_delta_dk(series)
            if deltas:
                tau_ins.append(current_consecutive_quiescence(deltas, dq))

        if not tau_ins:
            continue

        tau_ins_sorted = sorted(tau_ins)
        m = len(tau_ins_sorted)
        nonzero = [t for t in tau_ins if t > 0]
        print(f"\n  DELTA_Q={dq:.2f}:")
        print(f"    tickers with τ_in > 0: {len(nonzero)}/{m}")
        if tau_ins_sorted:
            print(f"    max τ_in:    {tau_ins_sorted[-1]}")
            print(f"    median τ_in: {tau_ins_sorted[m // 2]}")
            print(f"    p75 τ_in:    {tau_ins_sorted[int(m * 0.75)]}")
        if nonzero:
            top = sorted(
                [(t, tick) for tick, series in dk_history.items()
                 for t in [current_consecutive_quiescence(compute_delta_dk(series), dq)]
                 if t > 0],
                reverse=True,
            )[:10]
            print(f"    top τ_in tickers: {[(tick, t) for t, tick in top]}")

    print(f"\n=== 3:1 Ratio Validation (τ_out = floor(τ_in/3)) ===")
    print(f"  (Informational only — ALTE Spec 2.3. Pending Section 3.4 confirmation.)")
    for dq in [0.05]:
        for ticker, series in sorted(dk_history.items()):
            deltas = compute_delta_dk(series)
            if not deltas:
                continue
            tau_in = current_consecutive_quiescence(deltas, dq)
            if tau_in >= 3:
                tau_out = tau_in // 3
                print(f"  {ticker}: τ_in={tau_in}  →  τ_out={tau_out}")


def main() -> None:
    print("=== TFE ALTE Quiescence Telemetry — Measurement Only ===")
    print(f"Note: LAMBDA_DECAY=0.064 is not in any confirmed spec — not applied.")
    print(f"Note: epsilon decay formula is not in ALTE spec — not applied.")
    print(f"Note: Section 3.4 Calamity Mapping is incomplete — no status labels assigned.\n")

    conn = connect()
    cur = conn.cursor()

    print("Fetching current Accumulate tickers...")
    tickers = fetch_accumulate_tickers(cur)
    print(f"  {len(tickers)} Accumulate tickers in current snapshot.")

    if not tickers:
        print("No Accumulate tickers found. Exiting.")
        return

    print(f"Fetching D_k history (last {HISTORY_DAYS} days) from runtime_decisions_history...")
    dk_history = fetch_dk_history(cur, tickers)

    if not dk_history:
        print(f"  No history found. Falling back to runtime_decisions_latest (single point).")
        print(f"  WARNING: τ_in cannot be computed from a single point. Reporting D_k values only.")
        dk_history = fetch_dk_latest(cur, tickers)
        print(f"  {len(dk_history)} tickers with D_k in latest snapshot.")

        print(f"\n=== D_k Point-in-Time Distribution ({len(dk_history)} tickers) ===")
        dk_vals = sorted(v[0] for v in dk_history.values())
        n = len(dk_vals)
        if n:
            print(f"  min:    {dk_vals[0]:.6f}")
            print(f"  median: {dk_vals[n // 2]:.6f}")
            print(f"  max:    {dk_vals[-1]:.6f}")
        return

    tickers_with_history = len(dk_history)
    total_bars = sum(len(s) for s in dk_history.values())
    print(f"  {tickers_with_history} tickers with history, {total_bars} total D_k data points.")

    analyze(dk_history)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
