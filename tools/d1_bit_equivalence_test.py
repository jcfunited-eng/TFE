#!/usr/bin/env python3
"""
tools/d1_bit_equivalence_test.py — Gate D1 bit-equivalence gate.

Compares s_n from quarantine_historical_kernel.py (reference) against
s_n from the modified uf_mdg_snapshot.py (production path) for the
same 2,194-ticker universe over the last 22 trading days of the replay
window (2026-02-22 → 2026-03-24).

Pass criteria (ALL must hold):
  1. Joint row count ≥ 95% of cartesian product (≥ 0.95 × n_tickers × n_days)
  2. max(|s_n_q - s_n_p|) ≤ 1e-3
  3. p99.9(|s_n_q - s_n_p|) ≤ 1e-4
  4. Zero rows where one side is NULL and other is finite
  5. Zero rows with NaN, inf, or negative s_n on either side

If any criterion fails: prints which and emits first 20 failing rows.
Does NOT modify any kernel constant or formula.

Output:
  tools/d1_bit_equivalence_report.csv
  tools/d1_bit_equivalence_report.json
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
sys.path.insert(0, str(ROOT))

# Gate integrity: confirm quarantine kernel is unmodified
from quarantine_historical_kernel import build_state_rows, KernelParameters
from uf_mdg_snapshot import compute_cognitive_scalars

LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
OUTPUT_DIR  = ROOT / "tools"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"

EXPECTED_KERNEL_SHA = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"
WINDOW_START = "2026-02-22"
WINDOW_END   = "2026-03-24"
WARMUP_BARS  = 252

MAX_ABS_DIFF   = 1e-3
P999_ABS_DIFF  = 1e-4
MIN_COVERAGE   = 0.95


def log(m):
    print(f"[D1-GATE {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def get_kernel_sha():
    return hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()


def load_universe():
    """Load 2,194-ticker universe. Try multiple paths for the kernel cache."""
    # Try the main workspace first (canonical location), then worktree-relative
    candidate_caches = [
        Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl"),
        ROOT / "backups" / "walkforward_kernel_cache_20260624.pkl",
    ]
    for cache in candidate_caches:
        if cache.exists():
            log(f"Loading universe from {cache}")
            with open(cache, "rb") as f:
                kdb = pickle.load(f)
            return sorted(kdb.keys())
    # fallback: quarantine CSV (5,768 tickers; no bar-coverage filter)
    csv_path = Path("/workspaces/Tao_Financial_Engine/quarantine_12k_l5_trades.csv")
    if csv_path.exists():
        log(f"Kernel cache not found; using quarantine CSV ({csv_path.name})")
        import pandas as _pd
        return sorted(_pd.read_csv(csv_path)["Symbol"].unique().tolist())
    log("STOP: cannot locate universe (kernel cache or quarantine CSV)")
    sys.exit(1)


def load_bars(tickers):
    """Load bars for all tickers from daily_bars."""
    log(f"Loading bars for {len(tickers)} tickers...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    tstr = ",".join(f"'{t}'" for t in tickers)
    cur.execute(f"""
        SELECT UPPER(symbol), bar_date, close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({tstr})
          AND bar_date >= '2020-01-01'
          AND bar_date <= '2026-04-30'
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
        df = df.set_index("bar_date").sort_index()
        result[sym] = df
    log(f"  Loaded {len(result)} tickers")
    return result


def compute_quarantine_s_n(ticker, bars_df, window_start, window_end):
    """Run quarantine_historical_kernel on ticker's bars, extract s_n per date in window."""
    df = bars_df.copy()
    df.index = pd.to_datetime(df.index)

    # Need warmup bars before window_start
    all_dates = df.index
    window_mask = (all_dates >= window_start) & (all_dates <= window_end)
    window_dates = all_dates[window_mask]
    if len(window_dates) == 0:
        return {}

    # Build input: up to the end of the window (kernel uses all bars up to t)
    # For each date in window, we need bars[:date+1]
    # Efficiency: run once on full series, then index by gate's t_b date
    group = df.reset_index()
    group.columns = ["Date", "Close"]
    group["Symbol"] = ticker

    params = KernelParameters()
    try:
        result = build_state_rows(ticker, group, params)
    except Exception:
        return {}

    if result.empty or "s_n" not in result.columns:
        return {}

    result["Date"] = pd.to_datetime(result["Date"])
    result = result.set_index("Date")
    # Filter to window dates
    window_result = result[(result.index >= window_start) & (result.index <= window_end)]
    return window_result["s_n"].to_dict()


def compute_production_s_n(ticker, bars_df, window_start, window_end):
    """
    Run uf_mdg_snapshot.compute_cognitive_scalars on ticker's bars for each date
    in the window. Uses a rolling window matching WARMUP_BARS.
    Returns {date: s_n} dict.
    """
    df = bars_df.copy()
    df.index = pd.to_datetime(df.index)
    all_dates = df.index
    closes = df["close"].to_numpy(dtype=float)
    date_list = list(all_dates)

    result = {}
    for i, date in enumerate(date_list):
        if date < pd.Timestamp(window_start) or date > pd.Timestamp(window_end):
            continue
        if i < WARMUP_BARS:
            continue
        window = closes[max(0, i - WARMUP_BARS): i + 1]
        cog = compute_cognitive_scalars(window)
        s_n = cog.get("s_n")
        result[date] = s_n
    return result


def main():
    t0 = time.time()

    # Gate integrity: quarantine kernel unmodified
    actual_sha = get_kernel_sha()
    if actual_sha != EXPECTED_KERNEL_SHA:
        log(f"STOP: quarantine kernel SHA mismatch. got={actual_sha}")
        sys.exit(1)
    log(f"Kernel SHA: {actual_sha} ✓")

    universe = load_universe()
    bars_db = load_bars(universe + ["SPY"])

    # Determine actual trading days in window (from SPY bars)
    spy_bars = bars_db.get("SPY")
    if spy_bars is None:
        log("STOP: SPY bars not found — cannot determine trading calendar")
        sys.exit(1)
    trading_days = [d for d in spy_bars.index
                    if WINDOW_START <= d.strftime("%Y-%m-%d") <= WINDOW_END]
    n_days = len(trading_days)
    n_tickers = len(universe)
    expected_min_rows = int(MIN_COVERAGE * n_tickers * n_days)
    log(f"Window: {WINDOW_START} → {WINDOW_END} = {n_days} trading days, "
        f"{n_tickers} tickers, expected ≥{expected_min_rows:,} joint rows")

    # Collect comparison rows
    log("Running quarantine kernel + production path per ticker...")
    all_rows = []
    n_processed = 0
    bars_db_upper = {k.upper(): v for k, v in bars_db.items()}
    for ticker in universe:
        bars = bars_db_upper.get(ticker.upper())
        if bars is None:
            continue

        q_dict = compute_quarantine_s_n(ticker, bars, WINDOW_START, WINDOW_END)
        p_dict = compute_production_s_n(ticker, bars, WINDOW_START, WINDOW_END)

        # Intersect on dates present in both
        common_dates = set(q_dict.keys()) & set(pd.Timestamp(d) if not isinstance(d, pd.Timestamp) else d
                                                 for d in p_dict.keys())
        for d in common_dates:
            q_val = q_dict.get(d)
            p_val = p_dict.get(d)
            if q_val is None and p_val is None:
                continue
            ds = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
            abs_diff = abs(float(q_val) - float(p_val)) if (q_val is not None and p_val is not None) else None
            all_rows.append({
                "ticker":         ticker,
                "date":           ds,
                "s_n_quarantine": q_val,
                "s_n_production": p_val,
                "abs_diff":       abs_diff,
                "pass":           (abs_diff is not None and abs_diff <= MAX_ABS_DIFF),
            })
        n_processed += 1
        if n_processed % 200 == 0:
            log(f"  {n_processed}/{n_tickers} tickers")

    log(f"Total joint rows: {len(all_rows):,}")
    df = pd.DataFrame(all_rows)

    # ── Criteria evaluation ────────────────────────────────────────────────────
    failures = []

    # 1. Coverage
    joint_count = len(df)
    if joint_count < expected_min_rows:
        failures.append(f"Criterion 1 FAIL: joint rows {joint_count:,} < expected {expected_min_rows:,}")

    # 2. Max abs diff
    valid_diff = df["abs_diff"].dropna()
    max_diff = float(valid_diff.max()) if len(valid_diff) > 0 else 0.0
    if max_diff > MAX_ABS_DIFF:
        failures.append(f"Criterion 2 FAIL: max abs_diff={max_diff:.2e} > {MAX_ABS_DIFF:.2e}")
        bad = df[df["abs_diff"] > MAX_ABS_DIFF].head(20)
        log(f"  First 20 rows exceeding max tolerance:\n{bad.to_string()}")

    # 3. p99.9 abs diff
    p999 = float(np.nanpercentile(valid_diff.to_numpy(), 99.9)) if len(valid_diff) > 0 else 0.0
    if p999 > P999_ABS_DIFF:
        failures.append(f"Criterion 3 FAIL: p99.9 abs_diff={p999:.2e} > {P999_ABS_DIFF:.2e}")

    # 4. Asymmetric NULL
    null_asym = df[
        (df["s_n_quarantine"].isna() & df["s_n_production"].notna()) |
        (df["s_n_quarantine"].notna() & df["s_n_production"].isna())
    ]
    if len(null_asym) > 0:
        failures.append(f"Criterion 4 FAIL: {len(null_asym)} asymmetric NULL rows")
        log(f"  First 20 asymmetric NULL rows:\n{null_asym.head(20).to_string()}")

    # 5. NaN / inf / negative
    def check_validity(col):
        arr = df[col].dropna().to_numpy(dtype=float)
        return int(np.any(~np.isfinite(arr)) or np.any(arr < 0))
    n_invalid_q = check_validity("s_n_quarantine")
    n_invalid_p = check_validity("s_n_production")
    if n_invalid_q > 0 or n_invalid_p > 0:
        failures.append(f"Criterion 5 FAIL: NaN/inf/negative in quarantine={n_invalid_q}, production={n_invalid_p}")

    gate_pass = len(failures) == 0

    # ── Write outputs ──────────────────────────────────────────────────────────
    csv_path = OUTPUT_DIR / "d1_bit_equivalence_report.csv"
    df.to_csv(csv_path, index=False)
    log(f"Report CSV → {csv_path} ({csv_path.stat().st_size/1e3:.0f}KB)")

    report = {
        "command":            "TFE-CMD-GATE-D1-S_N-EMISSION-WC-20260625",
        "kernel_sha":         actual_sha,
        "window":             f"{WINDOW_START} → {WINDOW_END}",
        "n_tickers_universe": n_tickers,
        "n_trading_days":     n_days,
        "joint_row_count":    joint_count,
        "expected_min_rows":  expected_min_rows,
        "coverage_pct":       round(joint_count / (n_tickers * n_days) * 100, 2) if n_days > 0 else 0,
        "max_abs_diff":       round(max_diff, 10),
        "p99_9_abs_diff":     round(p999, 10),
        "n_null_asymmetric":  len(null_asym),
        "n_nan_or_inf_or_neg_quarantine": n_invalid_q,
        "n_nan_or_inf_or_neg_production": n_invalid_p,
        "gate_pass":          gate_pass,
        "failures":           failures,
        "pass_criteria": {
            "min_coverage":   f"≥{MIN_COVERAGE*100:.0f}% ({expected_min_rows:,} rows)",
            "max_abs_diff":   f"≤{MAX_ABS_DIFF:.0e}",
            "p99_9_abs_diff": f"≤{P999_ABS_DIFF:.0e}",
            "null_asymmetric":  "= 0",
            "nan_inf_negative": "= 0",
        },
        "wall_time_seconds":  round(time.time() - t0, 1),
    }

    json_path = OUTPUT_DIR / "d1_bit_equivalence_report.json"
    json_path.write_text(json.dumps(report, indent=2))
    log(f"Report JSON → {json_path}")

    log("")
    log("=== GATE D1 BIT-EQUIVALENCE RESULT ===")
    log(f"  Joint rows:    {joint_count:,}  (coverage {report['coverage_pct']:.1f}%)")
    log(f"  max abs_diff:  {max_diff:.2e}")
    log(f"  p99.9 diff:    {p999:.2e}")
    log(f"  Null asymm:    {len(null_asym)}")
    log(f"  Gate result:   {'PASS' if gate_pass else 'FAIL'}")
    if failures:
        for f in failures:
            log(f"  ✗ {f}")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
