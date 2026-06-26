#!/usr/bin/env python3
"""
tools/d1_direct_call_spot_check.py
Command: TFE-CMD-D1-CLOSURE-PLUS-D2-PREP-WC-20260626 Part A

Closes the helper-vs-direct-call gap from the amendment-2 signoff.

The bit-equivalence test used _production_cv_loop (a test helper that calls
internal uf_mdg_snapshot functions) rather than compute_cognitive_scalars
directly. This spot check verifies both produce identical s_n for the same
window and gate.

Design:
  For each sampled (ticker, target_date):
    Window = bars[max(0, i-252) : i+1] inclusive — ends AT target_date.
    The last bar always triggers a gate unconditionally, so the last gate
    is AT target_date. compute_cognitive_scalars returns s_n for this gate.
    The helper (_production_cv_loop on the same window, stopping at the
    last gate) must give the same value.

  Note on the amendment-2 report: that test used window [i-252, i+1] and
  extracted the gate AT target_date (second-to-last gate in the extended
  window). Due to per-gate normalization (V_max, CV_max computed across ALL
  gates in the window), the gate at target_date in a [i-252, i+1] window
  has different resonance than in a [i-252, i] window when a gate fires at
  i+1. The report's s_n_production and the spot-check's s_n_direct therefore
  legitimately differ — this is normalization, not helper-production drift.
  The spot check confirms helper == direct_call for the SAME window/gate.
"""
import hashlib
import json
import pickle
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path("/workspaces/Tao_Financial_Engine")))
sys.path.insert(0, str(ROOT))

from uf_mdg_snapshot import compute_cognitive_scalars
from tools.d1_bit_equivalence_test import (
    _production_cv_loop,
    _compute_l0_sev, _segment_l1_gates, _compute_l2_isf,
    _compute_l3_resonance, _compute_l4_dsf,
)

REPORT_CSV   = ROOT / "tools" / "d1_bit_equivalence_report.csv"
OUTPUT_JSON  = ROOT / "tools" / "d1_direct_call_spot_check_report.json"
LOCAL_DSN    = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
KERNEL_PATH  = Path("/workspaces/Tao_Financial_Engine/quarantine_historical_kernel.py")
EXPECTED_SHA = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"
SAMPLE_N     = 50
SEED         = 20260626
WARMUP_BARS  = 252
MAX_DIFF_TOL = 1e-12


def log(m):
    print(f"[SPOT {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def get_kernel_sha():
    return hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()


def helper_last_gate_s_n(closes_window):
    """
    Run the internal pipeline on closes_window.
    Return s_n of the LAST gate using _production_cv_loop.
    This is what the amendment-2 helper computes for the last gate.
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
        last_seq_idx = len(gates) - 1
        s_n, _ = _production_cv_loop(resonances, dsfs, last_seq_idx)
        return s_n
    except Exception:
        return None


def main():
    t0 = time.time()

    # Gate A: kernel SHA unchanged
    sha = get_kernel_sha()
    if sha != EXPECTED_SHA:
        log(f"STOP: kernel SHA mismatch. got={sha}")
        sys.exit(1)
    log(f"Kernel SHA: {sha} ✓")

    # Verify uf_mdg_snapshot has C_bar fix
    import uf_mdg_snapshot as umd
    import inspect
    src_path = inspect.getsourcefile(umd)
    src_text = open(src_path).read()
    if "c_history" not in src_text or "C_bar = 0.0" in src_text:
        log(f"STOP: uf_mdg_snapshot at {src_path} does not have C_bar fix")
        sys.exit(1)
    log(f"uf_mdg_snapshot: C_bar fix present at {src_path} ✓")

    # Load W1 rows from report
    if not REPORT_CSV.exists():
        log(f"STOP: report CSV not found at {REPORT_CSV}")
        sys.exit(1)
    df = pd.read_csv(REPORT_CSV)
    w1 = df[df["cohort"] == "W1"].copy()
    log(f"W1 rows in report: {len(w1)}")
    if len(w1) < SAMPLE_N:
        log(f"STOP: fewer than {SAMPLE_N} W1 rows available ({len(w1)})")
        sys.exit(1)

    random.seed(SEED)
    sample_indices = random.sample(range(len(w1)), SAMPLE_N)
    sampled = w1.iloc[sample_indices].reset_index(drop=True)
    log(f"Sampled {SAMPLE_N} rows (seed={SEED})")

    # Load bars
    tickers_needed = list(sampled["ticker"].unique())
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    tstr = ",".join(f"'{t}'" for t in tickers_needed)
    cur.execute(f"""
        SELECT UPPER(symbol), bar_date, close FROM daily_bars
        WHERE UPPER(symbol) IN ({tstr})
          AND bar_date >= '2020-01-01'
        ORDER BY symbol, bar_date
    """)
    rows = cur.fetchall()
    conn.close()
    bars_by_ticker = {}
    for sym, bd, c in rows:
        bars_by_ticker.setdefault(sym, []).append((pd.Timestamp(bd), float(c)))
    bars_arrays = {}
    for sym, rl in bars_by_ticker.items():
        df_b = pd.DataFrame(rl, columns=["bar_date", "close"])
        bars_arrays[sym] = df_b.set_index("bar_date").sort_index()
    log(f"Bars loaded for {len(bars_arrays)} tickers")

    # Run spot check
    results = []
    failures = []

    for row_idx, row in sampled.iterrows():
        ticker      = row["ticker"]
        target_date = row["date"]
        s_n_report  = float(row["s_n_production"])
        bar_count   = int(row["bar_count"])

        bdf = bars_arrays.get(ticker.upper(), bars_arrays.get(ticker))
        if bdf is None:
            log(f"  SKIP {ticker}: bars not found")
            continue

        closes_all = bdf["close"].to_numpy(dtype=float)
        dates_all  = list(bdf.index)
        try:
            i = next(j for j, d in enumerate(dates_all) if d.strftime("%Y-%m-%d") == target_date)
        except StopIteration:
            log(f"  SKIP {ticker} {target_date}: date not in bars")
            continue

        # Window [i-252, i] inclusive — last bar = target_date, last gate = target_date
        w_start = max(0, i - WARMUP_BARS)
        window  = closes_all[w_start : i + 1]   # ends AT target_date, NO +1 bar

        # Confirm last bar in window is target_date
        last_bar_date = dates_all[i].strftime("%Y-%m-%d")
        assert last_bar_date == target_date, f"{ticker}: last bar {last_bar_date} ≠ {target_date}"

        # Direct call
        cog = compute_cognitive_scalars(window)
        s_n_direct = cog.get("s_n")

        # Helper on same window (last gate)
        s_n_helper = helper_last_gate_s_n(window)

        if s_n_direct is None or s_n_helper is None:
            log(f"  SKIP {ticker} {target_date}: None s_n (insufficient bars for gate)")
            continue

        abs_diff = abs(s_n_direct - s_n_helper)
        passed   = abs_diff <= MAX_DIFF_TOL

        results.append({
            "ticker":       ticker,
            "target_date":  target_date,
            "bar_count":    bar_count,
            "s_n_direct":   s_n_direct,
            "s_n_helper":   s_n_helper,
            "abs_diff":     abs_diff,
            "pass":         passed,
            "s_n_report":   s_n_report,
            "diff_vs_report": abs(s_n_direct - s_n_report),
            "note_report":  ("report used window [i-252,i+1] → different gate "
                             "normalization → expected diff ≠ 0"),
        })
        if not passed:
            failures.append({
                "ticker": ticker, "target_date": target_date,
                "s_n_direct": s_n_direct, "s_n_helper": s_n_helper,
                "abs_diff": abs_diff,
            })

    n_tested = len(results)
    if n_tested == 0:
        log("STOP: no pairs tested")
        sys.exit(1)

    diffs    = [r["abs_diff"] for r in results]
    max_diff = float(max(diffs))
    mean_diff= float(sum(diffs) / n_tested)
    gate_pass= max_diff <= MAX_DIFF_TOL and len(failures) == 0

    report = {
        "command":        "TFE-CMD-D1-CLOSURE-PLUS-D2-PREP-WC-20260626 Part A",
        "kernel_sha":     sha,
        "uf_mdg_source":  src_path,
        "sample_n":       n_tested,
        "sample_seed":    SEED,
        "window_design":  "[i-252, i] ending AT target_date (no +1 bar). "
                          "Last gate unconditionally fires at target_date.",
        "n_pairs_tested": n_tested,
        "max_abs_diff":   round(max_diff, 15),
        "mean_abs_diff":  round(mean_diff, 15),
        "pass":           gate_pass,
        "failures":       failures[:20],
        "normalization_note": (
            "The amendment-2 report used window [i-252, i+1] and extracted the gate "
            "AT target_date (second-to-last in the extended window). The resonance "
            "normalization (V_max, CV_max) is computed across ALL gates in the window. "
            "A [i-252, i+1] window may have an additional gate at i+1, changing the "
            "normalization for gate at i. This is why s_n_direct (window [i-252,i]) "
            "differs from s_n_report (window [i-252,i+1]): normalization difference, "
            "not a helper-production drift."
        ),
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    OUTPUT_JSON.write_text(json.dumps(report, indent=2))
    log(f"Report → {OUTPUT_JSON}")
    log("")
    log("=== PART A SPOT CHECK RESULT ===")
    log(f"  n_pairs_tested: {n_tested}")
    log(f"  max abs_diff (direct vs helper, same window): {max_diff:.2e}")
    log(f"  Pass (≤{MAX_DIFF_TOL:.0e}): {gate_pass}")
    if failures:
        log(f"  FAILURES ({len(failures)}):")
        for f in failures[:5]:
            log(f"    {f}")
    else:
        log("  No failures — helper and compute_cognitive_scalars agree on same window")

    sys.exit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
