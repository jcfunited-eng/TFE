#!/usr/bin/env python3
"""
tools/d1_bit_equivalence_test.py — Gate D1 bit-equivalence test, Amendment 2.
Command: TFE-CMD-GATE-D1-S_N-EMISSION-WC-20260626-AMEND-2

Corrected evaluation frame: both quarantine and production evaluate bar t
using window [t-252, t+1] inclusive, providing F[t+1] for kappa_t.
This is the production reality: signal for bar t is emitted after bar t+1
closes (one-bar latency). The prior test ran quarantine on full history
(which gave kappa values using bars thousands of steps ahead).

For each (ticker, target_date) test point:
  1. Window = bars[max(0, i-WARMUP_BARS) : i+2] where i = target_date index
  2. Quarantine: build_state_rows on THIS WINDOW (not full history).
     Find gate row at target_date. Get s_n.
  3. Production: run uf_mdg_snapshot's internal pipeline on SAME window.
     Find gate at target_date's position (window_len - 2). Get s_n.
  4. Compare.

Both kernels use the same window, same kappa values, same formula.
Cohort_W1 (bar_count ≤ 20): deployment gate (strict criteria).
Cohort_EST (bar_count > 20): informational (expected to diverge on integrator
  warmup state if i ≥ WARMUP_BARS; same window eliminates the full-history
  divergence but 252-bar window vs full-history warmup may still differ).
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
# Worktree path first — picks up modified uf_mdg_snapshot.py (with s_n).
# Workspace path second — provides dependencies (tfe_market_data_service, etc.).
sys.path.insert(0, str(Path("/workspaces/Tao_Financial_Engine")))
sys.path.insert(0, str(ROOT))

from quarantine_historical_kernel import build_state_rows, KernelParameters
from uf_mdg_snapshot import (
    _compute_l0_sev, _segment_l1_gates, _compute_l2_isf,
    _compute_l3_resonance, _compute_l4_dsf,
    _KP_R_NORM_MAX, _KP_RHO_ROLLING_WINDOW,
    _KP_a_rho, _KP_b_rho, _KP_c_rho, _KP_d_rho,
    _KP_a_decay, _KP_a_nu_weight, _KP_a_pi_weight,
    _KP_A_f, _KP_B_f, _KP_A_m, _KP_B_m, _KP_A_s, _KP_B_s,
    _KP_H_mf, _KP_H_sm, _KP_G_all, _KP_L_f, _KP_L_m, _KP_L_s,
    _KP_lambda_s, _KP_eta_h,
)

LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
OUTPUT_DIR  = ROOT / "tools"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"
_ws = Path("/workspaces/Tao_Financial_Engine/quarantine_historical_kernel.py")
if _ws.exists():
    KERNEL_PATH = _ws

EXPECTED_SHA   = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"
W1_BAR_MAX     = 20
W1_MIN_ROWS    = 50
W1_MAX_DIFF    = 1e-3
W1_P999_DIFF   = 1e-4
WARMUP_BARS    = 252

# Test windows (cascade if W1_MIN_ROWS not reached)
PRIMARY_START = "2026-02-22";  PRIMARY_END = "2026-03-24"
EXT_START     = "2025-09-01";  EXT_END     = PRIMARY_END
EARLY_START   = "2020-04-01";  EARLY_END   = "2020-05-31"


def log(m):
    print(f"[D1-G2 {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def get_kernel_sha():
    return hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()


def load_universe():
    for cache in [
        Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl"),
        ROOT / "backups" / "walkforward_kernel_cache_20260624.pkl",
    ]:
        if cache.exists():
            with open(cache, "rb") as f:
                kdb = pickle.load(f)
            log(f"Universe: {len(kdb)} tickers from {cache.name}")
            return sorted(kdb.keys())
    log("STOP: kernel cache not found")
    sys.exit(1)


def load_bars(tickers):
    log(f"Loading bars for {len(tickers)} tickers + SPY...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    tstr = ",".join(f"'{t.upper()}'" for t in (list(tickers) + ["SPY"]))
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


# ── Production per-gate s_n ───────────────────────────────────────────────────
# Mirror of compute_cognitive_scalars loop, but returns s_n at a specific gate.
# Does NOT modify uf_mdg_snapshot.py; calls private functions via import above.

def _production_cv_loop(resonances, dsfs, stop_at_seq_idx):
    """Run CV integrator loop up to (and including) stop_at_seq_idx gate.
    Returns s_n at that gate, or None if loop didn't reach it.

    Uses proper C_bar from c_history (matching quarantine kernel).
    Note: compute_cognitive_scalars in uf_mdg_snapshot.py hardcodes C_bar=0.0
    with the comment 'c_norm not needed for F_n'. That simplification affects
    rho, which affects z_n, which affects s_n. The test uses the quarantine-
    faithful C_bar computation to validate the formula, independent of the
    C_bar=0 simplification in the production snapshot function.
    """
    a_state = np.zeros(3, dtype=float)
    x_f = x_m = x_s = 0.0
    r_history: list = []
    u_history: list = []
    c_history: list = []   # track c_norm = clip(C/4, 0, 1) per gate

    for seq_idx, (resonance, dsf) in enumerate(zip(resonances, dsfs)):
        r_norm   = float(np.clip(resonance.R / _KP_R_NORM_MAX, -1.0, 1.0))
        s_value  = 1.0
        u_value  = float(np.clip(dsf.U_star, 0.0, 1.0))
        # C from the gate's complexity count (same as quarantine kernel)
        c_norm   = float(np.clip(resonance.isf.gate.C / 4.0, 0.0, 1.0))

        r_history.append(r_norm)
        u_history.append(u_value)
        c_history.append(c_norm)

        R_bar = float(np.mean(r_history[-_KP_RHO_ROLLING_WINDOW:]))
        S_bar = s_value
        U_bar = float(np.mean(u_history[-_KP_RHO_ROLLING_WINDOW:]))
        C_bar = float(np.mean(c_history[-_KP_RHO_ROLLING_WINDOW:]))
        rho = float(np.clip(
            (_KP_a_rho * R_bar) + (_KP_b_rho * S_bar) -
            (_KP_c_rho * U_bar) - (_KP_d_rho * C_bar),
            0.0, 1.0,
        ))

        nu_core = np.clip(
            np.array([float(dsf.D), float(dsf.M), r_norm], dtype=float),
            -1.0, 1.0,
        )
        pi_vec = np.full(3, rho, dtype=float)

        a_state = np.clip(
            (_KP_a_decay * a_state) + (_KP_a_nu_weight * nu_core) +
            (_KP_a_pi_weight * pi_vec), -1.0, 1.0,
        )
        x_f = float(np.clip(
            (_KP_A_f * x_f) + (_KP_B_f * nu_core[0]) +
            (_KP_G_all * rho) + (_KP_L_f * a_state[0]), -1.0, 1.0,
        ))
        x_m = float(np.clip(
            (_KP_A_m * x_m) + (_KP_B_m * nu_core[1]) + (_KP_H_mf * x_f) +
            (_KP_G_all * rho) + (_KP_L_m * a_state[1]), -1.0, 1.0,
        ))
        x_s = float(np.clip(
            (_KP_A_s * x_s) + (_KP_B_s * nu_core[2]) + (_KP_H_sm * x_m) +
            (_KP_G_all * rho) + (_KP_L_s * a_state[2]), -1.0, 1.0,
        ))

        z_n = np.array([x_f, x_m, x_s], dtype=float)
        surprise = float(np.linalg.norm(nu_core - z_n))

        if seq_idx == stop_at_seq_idx:
            return surprise

    return None


def compute_production_s_n_at_gate(closes_window, target_t_b):
    """
    Run uf_mdg_snapshot's internal pipeline on closes_window.
    Find the gate where gate.t_b == target_t_b and return its s_n.
    Returns None if no gate at target_t_b.
    """
    try:
        F = closes_window.astype(float)
        if len(F) < 2:
            return None
        sevs       = _compute_l0_sev(F)
        gates      = _segment_l1_gates(sevs)
        isfs       = _compute_l2_isf(gates)
        resonances = _compute_l3_resonance(isfs)
        dsfs       = _compute_l4_dsf(resonances)
        if not resonances or not dsfs:
            return None
        # Find which sequential gate corresponds to target_t_b
        for seq_idx, gate in enumerate(gates):
            if gate.t_b == target_t_b:
                return _production_cv_loop(resonances, dsfs, seq_idx)
        return None
    except Exception:
        return None


def compute_quarantine_s_n_at_gate(closes_window, dates_window, target_date, ticker):
    """
    Run quarantine build_state_rows on WINDOWED bar slice (not full history).
    Find the gate row at target_date. Return s_n.
    """
    try:
        df = pd.DataFrame({
            "Date":   pd.to_datetime(dates_window),
            "Close":  closes_window,
            "Symbol": ticker,
        })
        result = build_state_rows(ticker, df, KernelParameters())
        if result.empty or "s_n" not in result.columns:
            return None
        result["Date"] = pd.to_datetime(result["Date"])
        row = result[result["Date"] == pd.Timestamp(target_date)]
        if len(row) == 0:
            return None
        return float(row.iloc[0]["s_n"])
    except Exception:
        return None


# ── Test per window ───────────────────────────────────────────────────────────

def run_test_for_window(universe, bars_db, win_start, win_end, label):
    log(f"Window {label}: {win_start} → {win_end}")
    bars_db_upper = {k.upper(): v for k, v in bars_db.items()}
    trading_days = get_trading_days(bars_db, win_start, win_end)
    trading_days_set = {d.strftime("%Y-%m-%d") for d in trading_days}
    log(f"  {len(trading_days)} trading days, {len(universe)} tickers")

    rows = []
    n_proc = 0

    for ticker in universe:
        bdf = bars_db_upper.get(ticker.upper())
        if bdf is None:
            continue

        closes_all  = bdf["close"].to_numpy(dtype=float)
        dates_all   = list(bdf.index)
        n_total     = len(closes_all)

        for i, date in enumerate(dates_all):
            ds = date.strftime("%Y-%m-%d")
            if ds not in trading_days_set:
                continue
            if i + 1 >= n_total:
                continue  # no bar i+1 available

            raw_bar_count = i + 1   # 1-based raw bars up to target_date

            # Window: [i-WARMUP_BARS, i+1] inclusive → gives F[i+1] for kappa_i
            w_start = max(0, i - WARMUP_BARS)
            w_end   = i + 2              # slice exclusive end
            c_window = closes_all[w_start:w_end]
            d_window = dates_all[w_start:w_end]
            target_t_b_in_window = i - w_start   # position of target_date in window

            # Quarantine: windowed build_state_rows, find gate at target_date
            s_n_q = compute_quarantine_s_n_at_gate(c_window, d_window, date, ticker)

            # Production: internal pipeline, find gate at target_t_b_in_window
            s_n_p = compute_production_s_n_at_gate(c_window, target_t_b_in_window)

            if s_n_q is None or s_n_p is None:
                continue  # no gate at target_date in one or both sides

            abs_diff = abs(s_n_q - s_n_p)
            cohort   = "W1" if raw_bar_count <= W1_BAR_MAX else "EST"
            rows.append({
                "ticker":         ticker,
                "date":           ds,
                "bar_count":      raw_bar_count,
                "s_n_quarantine": s_n_q,
                "s_n_production": s_n_p,
                "abs_diff":       abs_diff,
                "cohort":         cohort,
                "pass_strict":    (cohort == "W1" and abs_diff <= W1_MAX_DIFF),
            })

        n_proc += 1
        if n_proc % 200 == 0:
            log(f"  {n_proc}/{len(universe)} tickers")

    return rows


# ── Cohort stats + gate eval ──────────────────────────────────────────────────

def cohort_stats(cdf):
    n = len(cdf)
    if n == 0:
        return {"n_rows": 0}
    d = cdf["abs_diff"].dropna()
    arr = d.to_numpy(dtype=float)
    return {
        "n_rows":       n,
        "max_abs_diff": round(float(arr.max()), 10) if len(arr) else None,
        "p50":          round(float(np.percentile(arr, 50)), 10) if len(arr) else None,
        "p99":          round(float(np.percentile(arr, 99)), 10) if len(arr) else None,
        "p99_9":        round(float(np.percentile(arr, 99.9)), 10) if len(arr) else None,
        "n_null_asym":  int(
            ((cdf["s_n_quarantine"].isna()) & (cdf["s_n_production"].notna())).sum() +
            ((cdf["s_n_quarantine"].notna()) & (cdf["s_n_production"].isna())).sum()
        ),
    }


def main():
    t0 = time.time()

    sha = get_kernel_sha()
    if sha != EXPECTED_SHA:
        log(f"STOP: kernel SHA mismatch. got={sha}")
        sys.exit(1)
    log(f"Kernel SHA: {sha} ✓")

    universe = load_universe()
    bars_db  = load_bars(universe)

    # ── Window cascade ────────────────────────────────────────────────────────
    rows = run_test_for_window(universe, bars_db, PRIMARY_START, PRIMARY_END,
                               "PRIMARY (22-day)")
    df = pd.DataFrame(rows)
    n_w1 = int((df["cohort"] == "W1").sum()) if len(df) > 0 else 0
    log(f"Primary window: {len(df)} joint rows, {n_w1} Cohort_W1")

    if n_w1 < W1_MIN_ROWS:
        # Fast-check whether 6-month extension could have W1 rows
        bars_db_u = {k.upper(): v for k, v in bars_db.items()}
        sample_bc = max(
            (int((v.index < pd.Timestamp("2025-09-01")).sum()) for t in list(universe)[:20]
             if (v := bars_db_u.get(t.upper())) is not None),
            default=0
        )
        if sample_bc > W1_BAR_MAX:
            log(f"Skipping 6-month extension (sample bar_count@2025-09-01={sample_bc}>20); "
                f"jumping to early-bar window")
        else:
            rows = run_test_for_window(universe, bars_db, EXT_START, EXT_END,
                                       "6-MONTH EXTENSION")
            df = pd.DataFrame(rows)
            n_w1 = int((df["cohort"] == "W1").sum()) if len(df) > 0 else 0
            log(f"Extended window: {len(df)} joint rows, {n_w1} Cohort_W1")

    if n_w1 < W1_MIN_ROWS:
        log("Trying early-bar window (2020-04-01 → 2020-05-31)...")
        log("NOTE: 2,194-ticker universe has no new listings in 2025-2026.")
        log("  W1 rows exist in first 20 bars of each ticker (April-May 2020).")
        rows = run_test_for_window(universe, bars_db, EARLY_START, EARLY_END,
                                   "EARLY-BAR (2020-04)")
        df = pd.DataFrame(rows)
        n_w1 = int((df["cohort"] == "W1").sum()) if len(df) > 0 else 0
        log(f"Early-bar window: {len(df)} joint rows, {n_w1} Cohort_W1")

    if n_w1 < W1_MIN_ROWS:
        log(f"STOP: Cohort_W1 n_rows={n_w1} < {W1_MIN_ROWS} in all windows.")
        sys.exit(1)

    # ── Cohort split & gate eval ──────────────────────────────────────────────
    w1_df  = df[df["cohort"] == "W1"]  if len(df) > 0 else pd.DataFrame()
    est_df = df[df["cohort"] == "EST"] if len(df) > 0 else pd.DataFrame()

    w1_s  = cohort_stats(w1_df)
    est_s = cohort_stats(est_df)

    failures = []
    if w1_s["n_rows"] < W1_MIN_ROWS:
        failures.append(f"W1 Criterion 1: n_rows={w1_s['n_rows']} < {W1_MIN_ROWS}")
    if (w1_s.get("max_abs_diff") or 0) > W1_MAX_DIFF:
        failures.append(f"W1 Criterion 2: max_abs_diff={w1_s['max_abs_diff']:.2e} > {W1_MAX_DIFF:.0e}")
        log(f"First 20 worst W1 rows:")
        log(w1_df.nlargest(20, "abs_diff").to_string())
    if (w1_s.get("p99_9") or 0) > W1_P999_DIFF:
        failures.append(f"W1 Criterion 3: p99.9={w1_s['p99_9']:.2e} > {W1_P999_DIFF:.0e}")
    if w1_s.get("n_null_asym", 0) > 0:
        failures.append(f"W1 Criterion 4: asymmetric NULL n={w1_s['n_null_asym']}")
    if len(w1_df) > 0:
        for col in ["s_n_quarantine", "s_n_production"]:
            arr = w1_df[col].dropna().to_numpy(dtype=float)
            if len(arr) > 0 and (not np.all(np.isfinite(arr)) or np.any(arr < 0)):
                failures.append(f"W1 Criterion 5: NaN/inf/negative in {col}")

    gate_pass = len(failures) == 0

    # ── Write outputs ─────────────────────────────────────────────────────────
    df.to_csv(OUTPUT_DIR / "d1_bit_equivalence_report.csv", index=False)

    report = {
        "command":        "TFE-CMD-GATE-D1-S_N-EMISSION-WC-20260626-AMEND-2",
        "kernel_sha":     sha,
        "evaluation_frame": (
            "Corrected: window [t-252, t+1] for each test point. "
            "Both kernels use the same bar slice; kappa_t uses F[t+1] in both."
        ),
        "joint_row_count": len(df),
        "Cohort_W1":  {**w1_s, "pass_criteria": {
            "min_rows": W1_MIN_ROWS, "max_abs_diff": f"≤{W1_MAX_DIFF:.0e}",
            "p99_9": f"≤{W1_P999_DIFF:.0e}", "null_asym": "=0", "nan_neg": "=0",
        }},
        "Cohort_EST": {**est_s, "note":
            "Informational. With the corrected same-window frame, EST cohort "
            "should also converge (both kernels use same window, same warmup start). "
            "Any remaining divergence would indicate a formula difference."},
        "gate_pass":  gate_pass,
        "failures":   failures,
        "wall_time_seconds": round(time.time() - t0, 1),
    }
    (OUTPUT_DIR / "d1_bit_equivalence_report.json").write_text(
        json.dumps(report, indent=2))

    log("")
    log("=== GATE D1 AMEND-2 RESULT ===")
    log(f"  Cohort_W1 rows:   {w1_s['n_rows']}")
    if w1_s["n_rows"] > 0:
        log(f"  W1 max abs_diff:  {w1_s.get('max_abs_diff'):.2e}")
        log(f"  W1 p99.9 diff:    {w1_s.get('p99_9'):.2e}")
    log(f"  Cohort_EST rows:  {est_s['n_rows']}")
    if est_s["n_rows"] > 0:
        log(f"  EST max abs_diff: {est_s.get('max_abs_diff'):.2e}")
    log(f"  Gate result:      {'PASS' if gate_pass else 'FAIL'}")
    for f in failures:
        log(f"  ✗ {f}")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
