#!/usr/bin/env python3
"""CP-2 Recommendation Quality Audit.

Generates recommendation-quality-latest.json using deterministic DSF V3 basin
physics. Replaces the legacy L5 learning tournament pipeline entirely.

Metrics computed
----------------
  5D / 20D / 60D outcome-over-index (% of Accumulate decisions that beat SPY):
    - Query runtime_decisions_history for the last HISTORY_DAYS calendar days.
    - Re-derive the CP-2 V3 decision for each row using frozen basin physics
      (imported from evaluate_recommendation_policy_snapshot).
    - For "Accumulate" decisions that are sufficiently mature, fetch forward
      close prices via yfinance and compare against SPY return over the same
      window.  A decision is "mature" when at least (horizon * 1.5) calendar
      days have elapsed since snapshot_date.
    - If a horizon has < MIN_SAMPLE mature decisions the metric is emitted as
      null and status is "insufficient_history".

  Coverage / Fallback rates from runtime_decisions_latest reason_code
  distribution (falls back to fallback_used flag when reason_code is not yet
  populated).

  6 quality gates (same frozen targets as legacy):
    gate_5day, gate_20day, gate_60day, gate_sp_plus_4_proxy_avg (avg),
    gate_coverage, gate_fallback.

No ML. No policy cells. No PSCF. No tournament. Pure deterministic math.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import evaluate_recommendation_policy_snapshot as ev  # noqa: E402

OUTPUT_PATH = REPO_ROOT / "web" / "data" / "recommendation-quality-latest.json"

# ---------------------------------------------------------------------------
# Frozen gate targets — match legacy values exactly
# ---------------------------------------------------------------------------
TARGET_5: float = 95.0
TARGET_20: float = 97.0
TARGET_60: float = 69.0
TARGET_AVG: float = 64.0
TARGET_COVERAGE: float = 0.95
TARGET_FALLBACK_MAX: float = 0.05

# Minimum number of mature decisions required to emit a horizon metric
MIN_SAMPLE: int = 10

# Calendar-day lookback window for history (120d ≈ 85 trading days)
HISTORY_DAYS: int = 120

# Trading-day horizons
HORIZONS: Tuple[int, ...] = (5, 20, 60)

# Required PostgreSQL env vars
REQUIRED_PG_ENV = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _check_pg_env() -> None:
    missing = [k for k in REQUIRED_PG_ENV if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required PostgreSQL env vars: {missing}")


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def _connect_db():
    """Open a psycopg2 connection using environment variables."""
    import psycopg2
    import psycopg2.extras  # noqa: F401 — ensure RealDictCursor is available

    conn_kwargs: Dict[str, Any] = {
        "host": os.environ["PGHOST"],
        "port": int(os.environ.get("PGPORT", "5432")),
        "dbname": os.environ["PGDATABASE"],
        "user": os.environ["PGUSER"],
        "password": os.environ["PGPASSWORD"],
    }
    sslmode = os.environ.get("PGSSLMODE", "require")
    if sslmode and sslmode != "disable":
        conn_kwargs["sslmode"] = sslmode
        sslrootcert = os.environ.get("PGSSLROOTCERT", "/app/certs/rds-global-bundle.pem")
        if sslrootcert and Path(sslrootcert).exists():
            conn_kwargs["sslrootcert"] = sslrootcert
    # 300-second statement timeout — history table can exceed 500K rows
    conn_kwargs["options"] = "-c statement_timeout=300000"
    conn_kwargs["connect_timeout"] = 10
    return psycopg2.connect(**conn_kwargs)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _query_current_stats(conn) -> Dict[str, Any]:
    """
    Pull decision distribution from runtime_decisions_latest.

    Returns: {total, evaluated, fallback, reason_code_distribution}

    Strategy: prefer reason_code when populated (post-fix); fall back to
    fallback_used flag (pre-fix) so the generator works before and after the
    reason_code INSERT fix reaches production.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                                              AS total,
                COUNT(*) FILTER (WHERE reason_code = 'DSF_V3_ACCUMULATE')            AS acc,
                COUNT(*) FILTER (WHERE reason_code = 'DSF_V3_HOLD')                  AS hold,
                COUNT(*) FILTER (WHERE reason_code = 'DSF_V3_TIE_HOLD')              AS tie_hold,
                COUNT(*) FILTER (WHERE reason_code = 'DSF_V3_AVOID')                 AS avoid,
                COUNT(*) FILTER (WHERE reason_code IN (
                    'DSF_V3_MISSING_REQUIRED_FIELDS',
                    'DSF_V3_INSUFFICIENT_BARS'
                ))                                                                    AS fallback_rc,
                COUNT(*) FILTER (WHERE reason_code IS NOT NULL)                       AS rc_populated,
                COUNT(*) FILTER (WHERE fallback_used = TRUE)                          AS fallback_flag
            FROM runtime_decisions_latest
        """)
        row = cur.fetchone()

    if row is None:
        return {"total": 0, "evaluated": 0, "fallback": 0, "reason_code_distribution": {}}

    total, acc, hold, tie_hold, avoid, fallback_rc, rc_populated, fallback_flag = row
    total = total or 0

    if rc_populated and rc_populated > 0:
        # reason_code is populated — use it as ground truth
        evaluated = (acc or 0) + (hold or 0) + (tie_hold or 0) + (avoid or 0)
        fallback = fallback_rc or 0
    else:
        # Pre-fix: derive from fallback_used flag
        evaluated = total - (fallback_flag or 0)
        fallback = fallback_flag or 0

    reason_dist: Dict[str, int] = {}
    if acc:        reason_dist["DSF_V3_ACCUMULATE"]             = int(acc)
    if hold:       reason_dist["DSF_V3_HOLD"]                   = int(hold)
    if tie_hold:   reason_dist["DSF_V3_TIE_HOLD"]               = int(tie_hold)
    if avoid:      reason_dist["DSF_V3_AVOID"]                   = int(avoid)
    if fallback_rc:reason_dist["DSF_V3_FALLBACK"]               = int(fallback_rc)

    return {
        "total": int(total),
        "evaluated": int(evaluated),
        "fallback": int(fallback),
        "reason_code_distribution": reason_dist,
    }


def _query_history(conn) -> List[Dict[str, Any]]:
    """
    Return candidate Accumulate rows from runtime_decisions_history.

    Pre-filters in SQL: bar_count >= ACCUMULATE_MIN_BARS and all 9 required
    V3 fields present. Only extracts the 9 basin-physics fields (not the full
    JSONB blob) to keep memory and transfer time low on 500K+ row tables.
    """
    min_bars = ev.ACCUMULATE_MIN_BARS
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                ticker,
                run_id,
                generated_at_utc,
                jsonb_build_object(
                    'bar_count',  (snapshot_row_json->>'bar_count')::int,
                    'S_UF',       (snapshot_row_json->>'S_UF')::float,
                    'R_UF',       (snapshot_row_json->>'R_UF')::float,
                    'D_k',        (snapshot_row_json->>'D_k')::float,
                    'M_k',        (snapshot_row_json->>'M_k')::float,
                    'R_rev_k',    (snapshot_row_json->>'R_rev_k')::float,
                    'U_star_k',   (snapshot_row_json->>'U_star_k')::float,
                    'C_k',        (snapshot_row_json->>'C_k')::float,
                    'P_k',        (snapshot_row_json->>'P_k')::float,
                    'B_k',        (snapshot_row_json->>'B_k')::float
                ) AS snapshot_row_json
            FROM runtime_decisions_history
            WHERE generated_at_utc >= %s
              AND (snapshot_row_json->>'bar_count')::int >= %s
              AND snapshot_row_json->>'S_UF'     IS NOT NULL
              AND snapshot_row_json->>'R_UF'     IS NOT NULL
              AND snapshot_row_json->>'D_k'      IS NOT NULL
              AND snapshot_row_json->>'M_k'      IS NOT NULL
              AND snapshot_row_json->>'R_rev_k'  IS NOT NULL
              AND snapshot_row_json->>'U_star_k' IS NOT NULL
              AND snapshot_row_json->>'C_k'      IS NOT NULL
              AND snapshot_row_json->>'P_k'      IS NOT NULL
              AND snapshot_row_json->>'B_k'      IS NOT NULL
            ORDER BY generated_at_utc ASC
            """,
            (cutoff, min_bars),
        )
        rows = cur.fetchall()

    result: List[Dict[str, Any]] = []
    for ticker, run_id, generated_at, snap_json in rows:
        if isinstance(snap_json, str):
            try:
                snap_json = json.loads(snap_json)
            except Exception:
                continue
        result.append({
            "ticker": ticker,
            "run_id": run_id,
            "generated_at_utc": generated_at,
            "snapshot_row_json": snap_json or {},
        })
    return result


# ---------------------------------------------------------------------------
# CP-2 decision re-derivation
# ---------------------------------------------------------------------------

def _derive_cp2_decision(snapshot_json: Dict[str, Any]) -> str:
    """
    Re-derive the CP-2 V3 decision from a snapshot row using frozen basin
    physics.  Returns "Accumulate", "Hold", or "Avoid".

    This is the authoritative re-evaluation — identical physics to
    runtime_decision_provenance.mjs and evaluate_recommendation_policy_snapshot.py.
    """
    try:
        bar_count = max(0, int(snapshot_json.get("bar_count") or 0))
    except (TypeError, ValueError):
        bar_count = 0

    if bar_count < ev.ACCUMULATE_MIN_BARS:
        return "Hold"

    inputs = ev.resolve_v3_inputs(snapshot_json)
    if inputs.missing_fields:
        return "Hold"

    basins = ev.compute_v3_basins(inputs)
    reason = ev.v3_reason_code(basins)
    return ev.decision_from_reason_code(reason)


# ---------------------------------------------------------------------------
# Forward return computation via yfinance
# ---------------------------------------------------------------------------

def _fetch_forward_returns(
    accumulate_records: List[Dict[str, Any]],
) -> Dict[int, Tuple[int, int]]:
    """
    For each (ticker, snapshot_ts) in accumulate_records compute whether the
    ticker beat SPY over each HORIZONS trading-day window.

    Maturity rule: a decision is eligible for horizon H only if at least
    H * 1.5 calendar days have elapsed since generated_at_utc.

    Returns: {horizon: (wins, total_mature_evaluated)}
    """
    import pandas as pd
    import yfinance as yf

    if not accumulate_records:
        return {h: (0, 0) for h in HORIZONS}

    now_date = datetime.now(timezone.utc).date()

    # Collect unique tickers and global date bounds
    tickers: List[str] = list({r["ticker"] for r in accumulate_records})

    raw_dates = []
    for r in accumulate_records:
        dt = r["generated_at_utc"]
        raw_dates.append(dt.date() if hasattr(dt, "date") else dt)
    min_date = min(raw_dates)
    # Give generous end buffer: max horizon + 10 extra trading days ≈ 100 days
    fetch_start = min_date - timedelta(days=5)
    fetch_end   = now_date + timedelta(days=10)

    all_symbols = tickers + ["SPY"]
    print(
        f"[cp2_quality_audit] Fetching price data: {len(tickers)} tickers + SPY "
        f"({fetch_start} → {fetch_end})"
    )
    try:
        raw = yf.download(
            all_symbols,
            start=str(fetch_start),
            end=str(fetch_end),
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as exc:
        print(f"[cp2_quality_audit] yfinance download failed: {exc}")
        return {h: (0, 0) for h in HORIZONS}

    # Normalise to a simple (date, ticker) → close price DataFrame
    if isinstance(raw.columns, pd.MultiIndex):
        try:
            closes = raw["Close"]
        except KeyError:
            closes = raw.xs("Close", axis=1, level=0)
    else:
        closes = raw[["Close"]] if "Close" in raw.columns else raw

    closes = closes.sort_index()
    trading_dates = list(closes.index)

    def _close_at_offset(ticker: str, ref_date, offset: int) -> Optional[float]:
        """Return close price `offset` trading days after ref_date."""
        if ticker not in closes.columns:
            return None
        ref_ts = pd.Timestamp(ref_date)
        positions = [i for i, d in enumerate(trading_dates) if pd.Timestamp(d) >= ref_ts]
        if not positions:
            return None
        base = positions[0]
        target = base + offset
        if target >= len(trading_dates):
            return None
        val = closes[ticker].iloc[target]
        if val is None:
            return None
        try:
            f = float(val)
        except (TypeError, ValueError):
            return None
        if not (f > 0):
            return None
        return f

    wins:   Dict[int, int] = {h: 0 for h in HORIZONS}
    counts: Dict[int, int] = {h: 0 for h in HORIZONS}

    for record in accumulate_records:
        ticker   = record["ticker"]
        snap_dt  = record["generated_at_utc"]
        snap_day = snap_dt.date() if hasattr(snap_dt, "date") else snap_dt
        cal_age  = (now_date - snap_day).days

        for h in HORIZONS:
            if cal_age < h * 1.5:
                continue  # decision not yet mature for this horizon

            base_t  = _close_at_offset(ticker,  snap_day, 0)
            fwd_t   = _close_at_offset(ticker,  snap_day, h)
            base_s  = _close_at_offset("SPY",   snap_day, 0)
            fwd_s   = _close_at_offset("SPY",   snap_day, h)

            if None in (base_t, fwd_t, base_s, fwd_s):
                continue

            ret_t = (fwd_t - base_t) / base_t   # type: ignore[operator]
            ret_s = (fwd_s - base_s) / base_s   # type: ignore[operator]

            wins[h]   += int(ret_t > ret_s)
            counts[h] += 1

    return {h: (wins[h], counts[h]) for h in HORIZONS}


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def run_audit(output_path: Path = OUTPUT_PATH) -> Dict[str, Any]:
    """Execute the full CP-2 quality audit and write output JSON."""
    _check_pg_env()

    # -----------------------------------------------------------------------
    # 1. Connect and query
    # -----------------------------------------------------------------------
    print("[cp2_quality_audit] Connecting to database ...")
    conn = _connect_db()
    try:
        print("[cp2_quality_audit] Querying runtime_decisions_latest ...")
        stats = _query_current_stats(conn)

        print("[cp2_quality_audit] Querying runtime_decisions_history ...")
        history_rows = _query_history(conn)
        print(f"[cp2_quality_audit] {len(history_rows)} history rows in last {HISTORY_DAYS}d.")
    finally:
        conn.close()

    total_rows    = stats["total"]
    evaluated_rows = stats["evaluated"]
    fallback_rows  = stats["fallback"]
    reason_dist    = stats["reason_code_distribution"]

    coverage_rate = evaluated_rows / total_rows if total_rows > 0 else 0.0
    fallback_rate  = fallback_rows  / total_rows if total_rows > 0 else 0.0

    # -----------------------------------------------------------------------
    # 2. Re-derive CP-2 Accumulate decisions from history
    # -----------------------------------------------------------------------
    accumulate_records: List[Dict[str, Any]] = []
    for row in history_rows:
        try:
            decision = _derive_cp2_decision(row["snapshot_row_json"])
        except Exception:
            continue
        if decision == "Accumulate":
            accumulate_records.append({
                "ticker":           row["ticker"],
                "generated_at_utc": row["generated_at_utc"],
                "run_id":           row["run_id"],
            })
    print(
        f"[cp2_quality_audit] {len(accumulate_records)} Accumulate decisions "
        f"in history window."
    )

    # -----------------------------------------------------------------------
    # 3. Compute forward returns
    # -----------------------------------------------------------------------
    if accumulate_records:
        horizon_results = _fetch_forward_returns(accumulate_records)
    else:
        horizon_results = {h: (0, 0) for h in HORIZONS}

    # -----------------------------------------------------------------------
    # 4. Horizon outcome metrics
    # -----------------------------------------------------------------------
    horizon_pcts: Dict[str, Optional[float]] = {}
    for h in HORIZONS:
        w, n = horizon_results[h]
        if n >= MIN_SAMPLE:
            horizon_pcts[str(h)] = round((w / n) * 100.0, 4)
        else:
            horizon_pcts[str(h)] = None

    valid_pcts = [v for v in horizon_pcts.values() if v is not None]
    avg_pct: Optional[float] = (
        round(sum(valid_pcts) / len(valid_pcts), 4) if valid_pcts else None
    )

    # -----------------------------------------------------------------------
    # 5. Gate evaluation
    # -----------------------------------------------------------------------
    def _gate_gte(metric: Optional[float], target: float) -> bool:
        return metric is not None and metric >= target

    def _gate_lte(metric: Optional[float], target: float) -> bool:
        return metric is not None and metric <= target

    gate_5day    = _gate_gte(horizon_pcts.get("5"),  TARGET_5)
    gate_20day   = _gate_gte(horizon_pcts.get("20"), TARGET_20)
    gate_60day   = _gate_gte(horizon_pcts.get("60"), TARGET_60)
    gate_avg     = _gate_gte(avg_pct,                TARGET_AVG)
    gate_coverage= _gate_gte(coverage_rate * 100.0,  TARGET_COVERAGE * 100.0)
    gate_fallback= _gate_lte(fallback_rate * 100.0,  TARGET_FALLBACK_MAX * 100.0)

    quality_gate_count     = sum([gate_5day, gate_20day, gate_60day, gate_avg])
    reliability_gate_count = sum([gate_coverage, gate_fallback])
    total_gate_count       = quality_gate_count + reliability_gate_count

    # -----------------------------------------------------------------------
    # 6. Status + reason text
    # -----------------------------------------------------------------------
    any_horizon_ready = any(v is not None for v in horizon_pcts.values())
    if not any_horizon_ready:
        status = "insufficient_history"
        reason_text = (
            f"Insufficient history for outcome scoring: "
            f"{len(accumulate_records)} Accumulate decisions found in last "
            f"{HISTORY_DAYS}d, need >= {MIN_SAMPLE} mature decisions per horizon."
        )
    elif total_gate_count >= 4:
        status = "pass"
        reason_text = (
            f"CP-2 DSF V3 deterministic basin argmax. "
            f"{len(accumulate_records)} Accumulate decisions evaluated. "
            f"Gates passed: {total_gate_count}/6."
        )
    else:
        status = "warn"
        reason_text = (
            f"CP-2 DSF V3 deterministic basin argmax. "
            f"{len(accumulate_records)} Accumulate decisions evaluated. "
            f"Gates passed: {total_gate_count}/6 — below 4-gate threshold."
        )

    # -----------------------------------------------------------------------
    # 7. Build output (backwards-compatible JSON schema)
    # -----------------------------------------------------------------------
    summary: Dict[str, Any] = {
        "generated_at_utc": _utc_now_iso(),
        "status": status,
        "cp_profile": "CP-2",
        "inputs": {
            "snapshot": str(REPO_ROOT / "uf_snapshot.json"),
            "runtime_policy": "CP-2 DSF V3 deterministic basin physics",
            "targets": {
                "target_5":            TARGET_5,
                "target_20":           TARGET_20,
                "target_60":           TARGET_60,
                "target_avg":          TARGET_AVG,
                "target_coverage":     TARGET_COVERAGE,
                "target_fallback_max": TARGET_FALLBACK_MAX,
            },
            "notes": {
                "accuracy_assessment_contract": (
                    "Outcome-over-index metrics are computed on CP-2 V3 Accumulate "
                    "decisions re-derived from runtime_decisions_history using frozen "
                    "DSF V3 basin physics.  Fallback rows (insufficient bars or missing "
                    "fields) are excluded from outcome scoring.  A decision is considered "
                    "mature for horizon H when at least H*1.5 calendar days have elapsed "
                    "since the snapshot timestamp."
                ),
            },
        },
        # winner block — kept schema-identical to legacy for API/UI backwards compat
        "winner": {
            "variant_name":                 "CP2_DSF_V3",
            "source_mode":                  "deterministic",
            "eval_mode":                    "deterministic",
            "min_bars":                     ev.ACCUMULATE_MIN_BARS,
            "policy_path":                  "web/scripts/runtime_decision_provenance.mjs",
            "gates": {
                "gate_5day":                gate_5day,
                "gate_20day":               gate_20day,
                "gate_60day":               gate_60day,
                # Legacy key kept for backwards-compat; semantically = avg gate
                "gate_sp_plus_4_proxy_avg": gate_avg,
                "gate_coverage":            gate_coverage,
                "gate_fallback":            gate_fallback,
                "quality_gate_count":       quality_gate_count,
                "reliability_gate_count":   reliability_gate_count,
                "total_gate_count":         total_gate_count,
            },
            "horizon_outcome_over_index_pct": horizon_pcts,
            "avg_outcome_over_index_pct":     avg_pct,
            "coverage_rate":                  round(coverage_rate, 6),
            "fallback_rate":                  round(fallback_rate,  6),
            "reason":                         reason_text,
        },
        # cp2_audit — new block consumed by the simplified API route
        "cp2_audit": {
            "profile":                          "CP-2",
            "decision_physics":                 "DSF_V3_DETERMINISTIC_BASIN",
            "total_rows":                        total_rows,
            "evaluated_rows":                    evaluated_rows,
            "fallback_rows":                     fallback_rows,
            "accumulate_decisions_in_window":    len(accumulate_records),
            "history_window_days":               HISTORY_DAYS,
            "min_sample_per_horizon":            MIN_SAMPLE,
            "horizon_sample_counts": {
                str(h): horizon_results[h][1] for h in HORIZONS
            },
            "reason_code_distribution":          reason_dist,
        },
    }

    # -----------------------------------------------------------------------
    # 8. Write output
    # -----------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    print(f"[cp2_quality_audit] Written: {output_path}")
    print(f"[cp2_quality_audit] Status:   {status}")
    print(f"[cp2_quality_audit] Gates:    {total_gate_count}/6")
    print(f"[cp2_quality_audit] Coverage: {coverage_rate:.4f} | Fallback: {fallback_rate:.4f}")
    for h in HORIZONS:
        w, n = horizon_results[h]
        pct  = horizon_pcts.get(str(h))
        print(f"[cp2_quality_audit] {h:>3}D:   {pct} % ({n} mature samples, {w} wins)")

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="CP-2 Recommendation Quality Audit — deterministic DSF V3 basin physics."
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help=f"Output path for JSON (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()
    run_audit(output_path=Path(args.output))


if __name__ == "__main__":
    main()
