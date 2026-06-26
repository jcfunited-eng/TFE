#!/usr/bin/env python3
"""
tools/wave_diagnostic_20260625.py
Command: TFE-CMD-WAVE-DIAGNOSTIC-WC-20260625

Read-only distributional summary of wave_kernel_state_20260625.parquet.
No new kernel computation. Stops if parquet or fields are missing.
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT        = Path(__file__).resolve().parent.parent
PARQUET     = ROOT / "tools" / "wave_kernel_state_20260625.parquet"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"
OUTPUT      = ROOT / "tools" / "wave_diagnostic_20260625.json"

EXPECTED_SHA  = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"
EXPECTED_ROWS = 2_964_881

W1_SN_LO   = 0.954;  W1_SN_HI   = 0.969
W1_DSN_LO  = 0.67;   W1_DSN_HI  = 0.72
W1_BC_MIN  = 1;       W1_BC_MAX  = 20


def log(m):
    print(f"[DIAG {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def pct(series, q):
    return float(np.nanpercentile(series.to_numpy(dtype=float), q * 100))


def distrib(series, label=""):
    s = series.dropna()
    n = len(s)
    arr = s.to_numpy(dtype=float)
    d = {
        "count": n,
        "min":   round(float(np.min(arr)), 8) if n else None,
        "p1":    round(float(np.percentile(arr,  1)), 8) if n else None,
        "p5":    round(float(np.percentile(arr,  5)), 8) if n else None,
        "p25":   round(float(np.percentile(arr, 25)), 8) if n else None,
        "p50":   round(float(np.percentile(arr, 50)), 8) if n else None,
        "p75":   round(float(np.percentile(arr, 75)), 8) if n else None,
        "p95":   round(float(np.percentile(arr, 95)), 8) if n else None,
        "p99":   round(float(np.percentile(arr, 99)), 8) if n else None,
        "max":   round(float(np.max(arr)), 8) if n else None,
    }
    return d


def main():
    t0 = time.time()

    # ── Integrity: kernel SHA ─────────────────────────────────────────────────
    actual_sha = hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_SHA:
        log(f"STOP: kernel SHA mismatch. got={actual_sha} expected={EXPECTED_SHA}")
        sys.exit(1)
    log(f"Kernel SHA: {actual_sha} ✓")

    # ── Load parquet ──────────────────────────────────────────────────────────
    if not PARQUET.exists():
        log(f"STOP: parquet not found at {PARQUET}")
        sys.exit(1)

    log("Loading parquet...")
    needed = ["Symbol", "Date", "D_k", "s_n", "delta_s_n", "bar_count", "F_n", "chi_n"]
    df = pd.read_parquet(PARQUET, columns=needed)
    log(f"  {len(df):,} rows, {df['Symbol'].nunique()} tickers")

    # ── Integrity: row count ──────────────────────────────────────────────────
    if len(df) != EXPECTED_ROWS:
        log(f"STOP: row count mismatch. got={len(df):,} expected={EXPECTED_ROWS:,}")
        sys.exit(1)
    log(f"Row count: {len(df):,} ✓")

    # ── Check required fields ─────────────────────────────────────────────────
    missing_cols = [c for c in needed if c not in df.columns]
    if missing_cols:
        log(f"STOP: missing columns: {missing_cols}")
        sys.exit(1)

    # ── D_k transitions (within ticker) ──────────────────────────────────────
    log("Computing D_k transitions...")
    df = df.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    df["D_k_prev"] = df.groupby("Symbol")["D_k"].shift(1)

    # Mask: valid transitions (not first row per ticker)
    tr = df.dropna(subset=["D_k_prev"])
    d_prev = tr["D_k_prev"].astype(int)
    d_curr = tr["D_k"].astype(int)

    def tr_count(prev_val, curr_val):
        return int(((d_prev == prev_val) & (d_curr == curr_val)).sum())

    dk_transitions = {
        "n_dk_0_to_plus1":       tr_count(0,  1),
        "n_dk_0_to_minus1":      tr_count(0, -1),
        "n_dk_plus1_to_0":       tr_count(1,  0),
        "n_dk_minus1_to_0":      tr_count(-1, 0),
        "n_dk_plus1_to_minus1":  tr_count(1, -1),
        "n_dk_minus1_to_plus1":  tr_count(-1, 1),
        "n_dk_unchanged":        int((d_prev == d_curr).sum()),
    }
    log(f"  D_k transitions: {dk_transitions}")

    # ── s_n distribution ──────────────────────────────────────────────────────
    log("Computing s_n distribution...")
    sn = df["s_n"]
    sn_dist = distrib(sn)
    sn_dist["count_in_wave1_band"] = int(sn.between(W1_SN_LO, W1_SN_HI).sum())
    sn_dist["wave1_band"] = [W1_SN_LO, W1_SN_HI]

    # ── |delta_s_n| distribution ──────────────────────────────────────────────
    log("Computing |delta_s_n| distribution...")
    dsn = df["delta_s_n"].dropna()
    dsn_dist = distrib(dsn)
    dsn_dist["count_in_wave1_band"] = int(dsn.between(W1_DSN_LO, W1_DSN_HI).sum())
    dsn_dist["wave1_band"] = [W1_DSN_LO, W1_DSN_HI]

    # ── Joint W1 count (all, regardless of D_k) ───────────────────────────────
    log("Computing joint Wave 1 counts...")
    non_spy = df[df["Symbol"] != "SPY"]

    w1_mask = (
        non_spy["bar_count"].between(W1_BC_MIN, W1_BC_MAX)
        & non_spy["s_n"].between(W1_SN_LO, W1_SN_HI)
        & non_spy["delta_s_n"].between(W1_DSN_LO, W1_DSN_HI)
    )
    joint_w1_count = int(w1_mask.sum())
    log(f"  joint_wave1_count (W1, no D_k filter): {joint_w1_count}")

    # W1 ∩ D_k transition 0→+1
    w1_and_dk_trig = (
        w1_mask
        & (non_spy["D_k_prev"] == 0)
        & (non_spy["D_k"] == 1)
    )
    joint_w1_at_dk_transition = int(w1_and_dk_trig.sum())
    log(f"  joint_wave1_at_dk_transition_count: {joint_w1_at_dk_transition}")

    # ── F_n distribution ──────────────────────────────────────────────────────
    log("Computing F_n distribution...")
    fn = df["F_n"]
    fn_dist = distrib(fn)
    fn_dist["count_lte_1_65"] = int((fn <= 1.65).sum())   # Mar 26 F_n/raw_x_m gate
    fn_dist["count_lte_0_45"] = int((fn <= 0.45).sum())   # kernel F_max

    # ── chi_n distribution ────────────────────────────────────────────────────
    chi_vals = df["chi_n"].value_counts().to_dict()
    chi_dist = {
        "count_0": int(chi_vals.get(0.0, 0)),
        "count_1": int(chi_vals.get(1.0, 0)),
    }

    # ── SPY D_k transition counts ─────────────────────────────────────────────
    log("Computing SPY D_k stats...")
    spy = df[df["Symbol"] == "SPY"].sort_values("Date")
    spy_dk_prev = spy["D_k"].shift(1).dropna().astype(int)
    spy_dk_curr = spy["D_k"][spy_dk_prev.index].astype(int)

    spy_counts = {
        "n_spy_dk_0_to_plus1": int(((spy_dk_prev == 0) & (spy_dk_curr == 1)).sum()),
        "n_spy_dk_at_plus1":   int((spy["D_k"] == 1).sum()),
        "note": (
            "quarantine kernel on SPY: D_k=+1 on 41 rows. "
            "Prior dispatch (uf_core kernel on SPY): 55 rows. "
            "Different kernels, different gate counts."
        ),
    }

    # ── Assemble output ───────────────────────────────────────────────────────
    out = {
        "command":       "TFE-CMD-WAVE-DIAGNOSTIC-WC-20260625",
        "source_parquet": str(PARQUET.name),
        "kernel_sha":    actual_sha,
        "n_rows_total":  len(df),
        "n_tickers":     int(df["Symbol"].nunique()),
        "dk_transition_counts":               dk_transitions,
        "s_n_distribution":                   sn_dist,
        "abs_delta_s_n_distribution":         dsn_dist,
        "joint_wave1_count":                  joint_w1_count,
        "joint_wave1_at_dk_transition_count": joint_w1_at_dk_transition,
        "F_n_distribution":                   fn_dist,
        "chi_n_distribution":                 chi_dist,
        "spy_dk_transition_counts":           spy_counts,
        "integrity_checks": {
            "kernel_sha_match": actual_sha == EXPECTED_SHA,
            "row_count_match":  len(df) == EXPECTED_ROWS,
        },
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    OUTPUT.write_text(json.dumps(out, indent=2))
    log(f"→ {OUTPUT} ({OUTPUT.stat().st_size/1024:.0f}KB)")
    log("")
    log(f"joint_wave1_at_dk_transition_count = {joint_w1_at_dk_transition}")


if __name__ == "__main__":
    main()
