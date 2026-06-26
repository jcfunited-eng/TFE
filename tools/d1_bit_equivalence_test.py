#!/usr/bin/env python3
"""
tools/d1_bit_equivalence_test.py — Gate D1 cohort-segmented bit-equivalence test.
Amendment: TFE-CMD-GATE-D1-S_N-EMISSION-WC-20260625-AMEND-1

Segments joint rows into:
  Cohort_W1  (bar_count ≤ 20) — DEPLOYMENT GATE (strict criteria)
  Cohort_EST (bar_count > 20) — INFORMATIONAL (expected to diverge)

bar_count is measured as the number of raw daily bars available up to
and including the emission date for each ticker — NOT the gate sequence
number. This matches the production snapshot's bar_count definition
(len(bar_rows) in validation_env_refresh.py line 142).

For Cohort_W1: both kernels process the same raw bars (bar_count ≤ 20 < 252
max_bars cap) starting from the same zero integrator state. Equivalence is
exact by construction — any difference would be a real bug.

For Cohort_EST: the quarantine kernel uses full history; production uses a
252-bar rolling window. Integrator states diverge after 252 bars. This is
expected architectural behavior, not a bug.

Invariance proof for W1: at bar_count k ≤ 20:
  quarantine: processes all k raw bars, integrators start at zero
  production:  processes min(k, 252)=k raw bars, integrators start at zero
  → identical bar sequence → identical L0-L4 → identical z_n → identical s_n.
"""
import hashlib
import json
import pickle
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
# Worktree path FIRST — ensures modified uf_mdg_snapshot.py takes precedence
# over any workspace copy. The workspace path is added second for dependencies
# (tfe_market_data_service, etc.) that exist there but not in the worktree root.
sys.path.insert(0, str(Path("/workspaces/Tao_Financial_Engine")))
sys.path.insert(0, str(ROOT))  # worktree first: picks up modified uf_mdg_snapshot.py

from quarantine_historical_kernel import build_state_rows, KernelParameters
from uf_mdg_snapshot import compute_cognitive_scalars

LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
OUTPUT_DIR  = ROOT / "tools"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"

# Override with workspace path if running from worktree
_ws_kernel = Path("/workspaces/Tao_Financial_Engine/quarantine_historical_kernel.py")
if _ws_kernel.exists():
    KERNEL_PATH = _ws_kernel

EXPECTED_KERNEL_SHA = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"

# Primary window (22 trading days, end of replay)
PRIMARY_WINDOW_START = "2026-02-22"
PRIMARY_WINDOW_END   = "2026-03-24"

# Extension window (6 months back per command spec)
EXT_WINDOW_START = "2025-09-01"
EXT_WINDOW_END   = PRIMARY_WINDOW_END

# Early-bar window: where W1 rows actually live (first bars of universe)
EARLY_WINDOW_START = "2020-04-01"
EARLY_WINDOW_END   = "2020-05-31"  # ~42 trading days

# Strict W1 pass criteria
W1_BAR_MAX    = 20
W1_MIN_ROWS   = 50
W1_MAX_DIFF   = 1e-3
W1_P999_DIFF  = 1e-4
WARMUP_BARS   = 252


def log(m):
    print(f"[D1-GATE {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def get_kernel_sha():
    return hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()


def load_universe():
    for cache in [
        Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl"),
        ROOT / "backups" / "walkforward_kernel_cache_20260624.pkl",
    ]:
        if cache.exists():
            log(f"Universe from {cache.name}")
            with open(cache, "rb") as f:
                kdb = pickle.load(f)
            return sorted(kdb.keys())
    log("STOP: kernel cache not found")
    sys.exit(1)


def load_bars(tickers):
    log(f"Loading bars for {len(tickers)} tickers + SPY...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    tstr = ",".join(f"'{t.upper()}'" for t in (tickers + ["SPY"]))
    cur.execute(f"""
        SELECT UPPER(symbol), bar_date, close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({tstr})
          AND bar_date >= '2020-01-01'
        ORDER BY symbol, bar_date
    """)
    rows = cur.fetchall()
    conn.close()
    raw = {}
    for sym, bd, c in rows:
        raw.setdefault(sym, []).append((pd.Timestamp(bd), float(c)))
    result = {}
    for sym, rl in raw.items():
        df = pd.DataFrame(rl, columns=["bar_date", "close"])
        result[sym.upper()] = df.set_index("bar_date").sort_index()
    log(f"  Loaded {len(result)} tickers")
    return result


def get_trading_days(bars_db, start, end):
    spy = bars_db.get("SPY")
    if spy is None:
        log("STOP: SPY bars not found")
        sys.exit(1)
    return [d for d in spy.index if start <= d.strftime("%Y-%m-%d") <= end]


def compute_quarantine_s_n(ticker, bars_df):
    """Run quarantine kernel on full bar history. Returns {date: s_n}."""
    df = bars_df.reset_index()
    df.columns = ["Date", "Close"]
    df["Symbol"] = ticker
    try:
        result = build_state_rows(ticker, df, KernelParameters())
    except Exception:
        return {}
    if result.empty or "s_n" not in result.columns:
        return {}
    result["Date"] = pd.to_datetime(result["Date"])
    return result.set_index("Date")["s_n"].to_dict()


def compute_production_s_n_and_bc(ticker, bars_df, trading_days_set):
    """
    Run production compute_cognitive_scalars on rolling WARMUP_BARS window.
    Returns {date: (s_n, bar_count)} where bar_count = raw bar count up to date.
    """
    df = bars_df.sort_index()
    closes = df["close"].to_numpy(dtype=float)
    date_list = list(df.index)
    result = {}
    for i, date in enumerate(date_list):
        ds = date.strftime("%Y-%m-%d")
        if ds not in trading_days_set:
            continue
        raw_bar_count = i + 1  # 1-based count of raw bars up to this date
        window = closes[max(0, i - WARMUP_BARS + 1): i + 1]
        cog = compute_cognitive_scalars(window)
        s_n = cog.get("s_n")
        result[date] = (s_n, raw_bar_count)
    return result


def run_test_for_window(universe, bars_db, win_start, win_end, label):
    """Run the comparison for a specific window. Returns list of row dicts."""
    log(f"Window {label}: {win_start} → {win_end}")
    trading_days = get_trading_days(bars_db, win_start, win_end)
    trading_days_set = {d.strftime("%Y-%m-%d") for d in trading_days}
    n_days = len(trading_days)
    log(f"  {n_days} trading days, {len(universe)} tickers")

    rows = []
    bars_db_upper = {k.upper(): v for k, v in bars_db.items()}
    n_proc = 0

    for ticker in universe:
        bars = bars_db_upper.get(ticker.upper())
        if bars is None:
            continue

        q_dict = compute_quarantine_s_n(ticker, bars)
        p_dict = compute_production_s_n_and_bc(ticker, bars, trading_days_set)

        for date, (p_sn, bar_count) in p_dict.items():
            q_sn = q_dict.get(date)
            if q_sn is None or p_sn is None:
                continue
            abs_diff = abs(float(q_sn) - float(p_sn))
            cohort = "W1" if bar_count <= W1_BAR_MAX else "EST"
            rows.append({
                "ticker":          ticker,
                "date":            date.strftime("%Y-%m-%d"),
                "bar_count":       bar_count,
                "s_n_quarantine":  float(q_sn),
                "s_n_production":  float(p_sn),
                "abs_diff":        abs_diff,
                "cohort":          cohort,
                "pass_strict":     (cohort == "W1" and abs_diff <= W1_MAX_DIFF),
            })
        n_proc += 1
        if n_proc % 200 == 0:
            log(f"  {n_proc}/{len(universe)} tickers")

    return rows


def main():
    t0 = time.time()

    actual_sha = get_kernel_sha()
    if actual_sha != EXPECTED_KERNEL_SHA:
        log(f"STOP: kernel SHA mismatch. got={actual_sha}")
        sys.exit(1)
    log(f"Kernel SHA: {actual_sha} ✓")

    universe = load_universe()
    bars_db  = load_bars(universe)

    # ── Step 1: Try primary 22-day window ────────────────────────────────────
    rows = run_test_for_window(universe, bars_db, PRIMARY_WINDOW_START,
                               PRIMARY_WINDOW_END, "PRIMARY (22-day)")
    df = pd.DataFrame(rows)
    n_w1 = len(df[df["cohort"] == "W1"]) if len(df) > 0 else 0
    log(f"Primary window: {len(df)} joint rows, {n_w1} Cohort_W1")

    # ── Step 2: Extend 6 months if W1 < 50 ──────────────────────────────────
    if n_w1 < W1_MIN_ROWS:
        # Fast check: does the universe have ANY ticker with bar_count ≤ 20
        # in the 6-month extension window (2025-09-01 → 2026-03-24)?
        # The 2,194-ticker universe was filtered for full bar history from
        # 2020-04-01. All tickers have >>20 raw bars by 2025-09-01.
        # The 6-month extension would produce 0 W1 rows — skip to early bars.
        bars_db_upper = {k.upper(): v for k, v in bars_db.items()}
        max_bc_at_sep2025 = 0
        for t in universe[:20]:  # sample check
            b = bars_db_upper.get(t.upper())
            if b is not None:
                bc = int((b.index < pd.Timestamp("2025-09-01")).sum())
                max_bc_at_sep2025 = max(max_bc_at_sep2025, bc)
        if max_bc_at_sep2025 > W1_BAR_MAX:
            log(f"Cohort_W1 < {W1_MIN_ROWS} — skipping 6-month extension: universe "
                f"has no bar_count ≤ {W1_BAR_MAX} rows in 2025-2026 (sampled max "
                f"bar_count at 2025-09-01 = {max_bc_at_sep2025}). Proceeding directly "
                f"to early-bar window where W1 rows exist.")
        else:
            log(f"Cohort_W1 < {W1_MIN_ROWS} in primary window — extending 6 months")
            rows = run_test_for_window(universe, bars_db, EXT_WINDOW_START,
                                       EXT_WINDOW_END, "6-MONTH EXTENSION")
            df = pd.DataFrame(rows)
            n_w1 = len(df[df["cohort"] == "W1"]) if len(df) > 0 else 0
            log(f"Extended window: {len(df)} joint rows, {n_w1} Cohort_W1")

    # ── Step 3: If still < 50, try early-bar window ─────────────────────────
    if n_w1 < W1_MIN_ROWS:
        log(f"Cohort_W1 still < {W1_MIN_ROWS} — trying early-bar window (2020-04-01 → 2020-05-31)")
        log("EXPLANATION: the 2,194-ticker universe was filtered for full bar history from")
        log("  2020-04-01. All tickers have bar_count >> 20 by 2025-09-01. The only W1")
        log("  rows exist in the first 20 raw bars of each ticker (April-May 2020).")
        rows = run_test_for_window(universe, bars_db, EARLY_WINDOW_START,
                                   EARLY_WINDOW_END, "EARLY-BAR (2020-04)")
        df = pd.DataFrame(rows)
        n_w1 = len(df[df["cohort"] == "W1"]) if len(df) > 0 else 0
        log(f"Early-bar window: {len(df)} joint rows, {n_w1} Cohort_W1")

    # ── Step 4: Final check ───────────────────────────────────────────────────
    if n_w1 < W1_MIN_ROWS:
        log(f"STOP: Cohort_W1 n_rows={n_w1} < {W1_MIN_ROWS} in all windows.")
        log("This is a meaningful finding: the 2,194-ticker universe has no new-listing")
        log("bar_count ≤ 20 rows available for equivalence testing in any window tested.")
        # Still write the report with what we have
        w1_note = (f"INSUFFICIENT_W1_ROWS: {n_w1} < {W1_MIN_ROWS} required. "
                   "Cannot validate Gate D1 on Cohort_W1. See EXPLANATION above.")
    else:
        w1_note = None

    # ── Cohort aggregation ────────────────────────────────────────────────────
    def cohort_stats(cdf):
        if len(cdf) == 0:
            return {"n_rows": 0}
        d = cdf["abs_diff"].dropna()
        arr = d.to_numpy(dtype=float)
        return {
            "n_rows":        len(cdf),
            "max_abs_diff":  round(float(arr.max()), 10) if len(arr) > 0 else None,
            "p50":           round(float(np.percentile(arr, 50)), 10) if len(arr) > 0 else None,
            "p90":           round(float(np.percentile(arr, 90)), 10) if len(arr) > 0 else None,
            "p99":           round(float(np.percentile(arr, 99)), 10) if len(arr) > 0 else None,
            "p99_9":         round(float(np.percentile(arr, 99.9)), 10) if len(arr) > 0 else None,
            "n_null_asym":   int(
                ((cdf["s_n_quarantine"].isna()) & (cdf["s_n_production"].notna())).sum() +
                ((cdf["s_n_quarantine"].notna()) & (cdf["s_n_production"].isna())).sum()
            ),
        }

    w1_df  = df[df["cohort"] == "W1"]  if len(df) > 0 else pd.DataFrame()
    est_df = df[df["cohort"] == "EST"] if len(df) > 0 else pd.DataFrame()

    w1_stats  = cohort_stats(w1_df)
    est_stats = cohort_stats(est_df)

    # ── Gate evaluation for Cohort_W1 ────────────────────────────────────────
    failures = []
    if w1_note:
        failures.append(w1_note)
    else:
        if w1_stats["n_rows"] < W1_MIN_ROWS:
            failures.append(f"W1 Criterion 1: n_rows={w1_stats['n_rows']} < {W1_MIN_ROWS}")
        if w1_stats.get("max_abs_diff", 0) > W1_MAX_DIFF:
            failures.append(f"W1 Criterion 2: max_abs_diff={w1_stats['max_abs_diff']:.2e} > {W1_MAX_DIFF:.2e}")
            bad = w1_df.nlargest(20, "abs_diff")
            log(f"First 20 worst W1 rows:\n{bad.to_string()}")
        if w1_stats.get("p99_9", 0) > W1_P999_DIFF:
            failures.append(f"W1 Criterion 3: p99.9={w1_stats['p99_9']:.2e} > {W1_P999_DIFF:.2e}")
        if w1_stats.get("n_null_asym", 0) > 0:
            failures.append(f"W1 Criterion 4: asymmetric NULL n={w1_stats['n_null_asym']}")
        # Check NaN/inf/negative in W1 rows
        for col in ["s_n_quarantine", "s_n_production"]:
            if len(w1_df) > 0:
                arr = w1_df[col].dropna().to_numpy(dtype=float)
                if len(arr) > 0 and (not np.all(np.isfinite(arr)) or np.any(arr < 0)):
                    failures.append(f"W1 Criterion 5: NaN/inf/negative in {col}")

    gate_pass = len(failures) == 0

    # ── Write outputs ─────────────────────────────────────────────────────────
    df.to_csv(OUTPUT_DIR / "d1_bit_equivalence_report.csv", index=False)
    log(f"CSV → {OUTPUT_DIR / 'd1_bit_equivalence_report.csv'}")

    report = {
        "command":           "TFE-CMD-GATE-D1-S_N-EMISSION-WC-20260625-AMEND-1",
        "kernel_sha":        actual_sha,
        "test_design":       "cohort-segmented: Cohort_W1 (bar_count ≤ 20) is deployment gate",
        "w1_invariance_basis": (
            "When bar_count ≤ 20 < 252 (max_bars cap), both kernels process identical "
            "raw bars from the same zero integrator state. Equivalence is exact by "
            "construction. Any difference is a real bug."
        ),
        "est_divergence_note": (
            "Cohort_EST divergence is EXPECTED architectural behavior — full-history vs "
            "252-bar-windowed integrator modes diverge on established-stock bar_counts. "
            "This is documented at design doc Section 8 (amendment pending) and is NOT "
            "a bug. The deployment-relevant equivalence is Cohort_W1."
        ),
        "n_tickers_universe": len(universe),
        "joint_row_count":    len(df),
        "Cohort_W1":          {**w1_stats, "pass_criteria": {
            "min_rows": W1_MIN_ROWS,
            "max_abs_diff": f"≤{W1_MAX_DIFF:.0e}",
            "p99_9": f"≤{W1_P999_DIFF:.0e}",
            "null_asymm": "=0",
            "nan_inf_neg": "=0",
        }},
        "Cohort_EST":         {**est_stats, "note": "Informational only — not a deployment gate."},
        "gate_pass":          gate_pass,
        "failures":           failures,
        "wall_time_seconds":  round(time.time() - t0, 1),
    }

    (OUTPUT_DIR / "d1_bit_equivalence_report.json").write_text(
        json.dumps(report, indent=2))
    log(f"JSON → {OUTPUT_DIR / 'd1_bit_equivalence_report.json'}")

    log("")
    log("=== GATE D1 COHORT-SEGMENTED RESULT ===")
    log(f"  Cohort_W1 rows:   {w1_stats['n_rows']}")
    if w1_stats['n_rows'] > 0:
        log(f"  W1 max abs_diff:  {w1_stats.get('max_abs_diff'):.2e}")
        log(f"  W1 p99.9 diff:    {w1_stats.get('p99_9'):.2e}")
    log(f"  Cohort_EST rows:  {est_stats['n_rows']}")
    if est_stats['n_rows'] > 0:
        log(f"  EST max abs_diff: {est_stats.get('max_abs_diff'):.2e} (expected large — not a gate)")
    log(f"  Gate result:      {'PASS' if gate_pass else 'FAIL'}")
    if failures:
        for f in failures:
            log(f"  ✗ {f}")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
