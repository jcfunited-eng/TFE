#!/usr/bin/env python3
"""
tools/wave_cohort_reval_20260625.py
Command: TFE-CMD-WAVE-COHORT-REVAL-WC-20260625

Post-processing on wave_kernel_state_20260625.parquet.
No kernel re-run. Uses D_k(t-1)=0 → D_k(t)=+1 as the Accumulate trigger.
"""
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT        = Path(__file__).resolve().parent.parent
PARQUET     = ROOT / "tools" / "wave_kernel_state_20260625.parquet"
SPECIES_CSV = ROOT / "tools" / "wave_species_profiles_20260625.csv"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"
OUTPUT_DIR  = ROOT / "tools"

EXPECTED_SHA  = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"
EXPECTED_C0   = 108274   # from diagnostic 52a9563 (all symbols); non-SPY = 108237

W1_BC_MIN  = 1;    W1_BC_MAX  = 20
W1_SN_LO   = 0.954; W1_SN_HI   = 0.969
W1_DSN_LO  = 0.67;  W1_DSN_HI  = 0.72
CLOSE_MIN  = 5.0
FWD_BARS   = 20     # emission-order bars forward within same ticker


def log(m):
    print(f"[RV {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def wilson_ci(p, n, z=1.96):
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (None, None)
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    margin = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return (round(max(0.0, center - margin), 6), round(min(1.0, center + margin), 6))


def cohort_stats(grp):
    n = len(grp)
    valid = grp["fwd_20d_return"].dropna()
    nv = len(valid)
    if nv == 0:
        return {
            "N_signals": n, "N_with_fwd20": 0,
            "WR_20d": None, "mean_fwd_20d_return": None,
            "median_fwd_20d_return": None,
            "p10": None, "p25": None, "p75": None, "p90": None,
            "n_unique_tickers": int(grp["Symbol"].nunique()),
            "date_range_min": str(grp["Date"].min()) if n else None,
            "date_range_max": str(grp["Date"].max()) if n else None,
            "binomial_95ci_lower": None, "binomial_95ci_upper": None,
            "small_n_flag": n < 5,
        }
    wr = float((valid > 0).mean())
    ci_lo, ci_hi = wilson_ci(wr, nv)
    arr = valid.to_numpy(dtype=float)
    return {
        "N_signals":              n,
        "N_with_fwd20":           nv,
        "WR_20d":                 round(wr, 6),
        "mean_fwd_20d_return":    round(float(valid.mean()), 6),
        "median_fwd_20d_return":  round(float(valid.median()), 6),
        "p10":  round(float(np.percentile(arr, 10)), 6),
        "p25":  round(float(np.percentile(arr, 25)), 6),
        "p75":  round(float(np.percentile(arr, 75)), 6),
        "p90":  round(float(np.percentile(arr, 90)), 6),
        "n_unique_tickers":       int(grp["Symbol"].nunique()),
        "date_range_min":         str(grp["Date"].min()),
        "date_range_max":         str(grp["Date"].max()),
        "binomial_95ci_lower":    ci_lo,
        "binomial_95ci_upper":    ci_hi,
        "small_n_flag":           n < 5,
    }


def main():
    t0 = time.time()

    # ── Gate 1: kernel SHA ─────────────────────────────────────────────────────
    actual_sha = hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_SHA:
        log(f"STOP: kernel SHA mismatch. got={actual_sha} expected={EXPECTED_SHA}")
        sys.exit(1)
    log(f"Kernel SHA: {actual_sha} ✓")

    # ── Load parquet ───────────────────────────────────────────────────────────
    if not PARQUET.exists():
        log(f"STOP: parquet not found at {PARQUET}")
        sys.exit(1)
    log("Loading parquet...")
    df = pd.read_parquet(PARQUET, columns=[
        "Symbol", "Date", "Close", "D_k", "M_k", "B_k", "U_star_k",
        "s_n", "delta_s_n", "F_n", "bar_count",
    ])
    df["Date"] = pd.to_datetime(df["Date"])
    log(f"  {len(df):,} rows, {df['Symbol'].nunique()} tickers")

    # ── Sort and compute D_k_prev within each ticker ───────────────────────────
    log("Computing D_k_prev...")
    df = df.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    df["D_k_prev"] = df.groupby("Symbol")["D_k"].shift(1)

    # ── Load species ───────────────────────────────────────────────────────────
    if SPECIES_CSV.exists():
        sp = pd.read_csv(SPECIES_CSV)[["ticker", "classification"]]
        sp_map = dict(zip(sp["ticker"], sp["classification"]))
        log(f"Species loaded from CSV: {len(sp_map)} tickers")
    else:
        # Recompute on the fly using the same method as prior dispatch
        log("Species CSV not found — recomputing from delta_s_n...")
        sn_records = []
        non_spy_g = df[df["Symbol"] != "SPY"].groupby("Symbol")
        for ticker, grp in non_spy_g:
            if len(grp) <= 5:
                continue
            tail = grp.sort_values("Date").iloc[5:]
            delta_vals = tail["delta_s_n"].dropna()
            if len(delta_vals) == 0:
                continue
            sn_records.append({"ticker": ticker, "delta_bar": float(delta_vals.mean())})
        sdf = pd.DataFrame(sn_records)
        p25 = float(sdf["delta_bar"].quantile(0.25))
        p75 = float(sdf["delta_bar"].quantile(0.75))
        sdf["classification"] = sdf["delta_bar"].apply(
            lambda v: "calm" if v <= p25 else ("volatile" if v > p75 else "normal")
        )
        sp_map = dict(zip(sdf["ticker"], sdf["classification"]))
        log(f"  Recomputed species for {len(sp_map)} tickers")

    # ── SPY D_k per Date for W3 (from THIS parquet) ────────────────────────────
    spy_dk = (
        df[df["Symbol"] == "SPY"][["Date", "D_k"]]
        .rename(columns={"D_k": "spy_D_k"})
        .drop_duplicates("Date")
    )
    log(f"SPY rows in parquet: {len(spy_dk)}")

    # Gate 3: SPY coverage
    replay_dates = pd.date_range("2021-04-01", "2026-03-24", freq="B")
    spy_cov = len(spy_dk[spy_dk["Date"].between("2021-04-01", "2026-03-24")]) / len(replay_dates)
    log(f"Gate 3: SPY coverage = {spy_cov*100:.1f}% of business days in replay window")
    gate3_pass = spy_cov >= 0.90

    # ── Step 1: Accumulate triggers (non-SPY) ─────────────────────────────────
    log("Step 1: identifying accumulate triggers...")
    non_spy = df[df["Symbol"] != "SPY"].copy()
    non_spy["is_acc_trigger"] = (
        (non_spy["D_k"] == 1) & (non_spy["D_k_prev"] == 0)
    )
    triggers = non_spy[non_spy["is_acc_trigger"]].copy()
    c0_n = len(triggers)
    log(f"  C0 (all triggers): {c0_n}")

    # Gate 4: compare to diagnostic
    gate4_ok = abs(c0_n - (EXPECTED_C0 - 37)) <= 50   # -37 for SPY transitions
    log(f"Gate 4: C0={c0_n}, expected ~{EXPECTED_C0-37}={EXPECTED_C0}-37(SPY) → {'PASS' if gate4_ok else 'NOTE'}")

    # ── Step 2: Wave evaluation ────────────────────────────────────────────────
    log("Step 2: evaluating waves...")
    triggers["species"] = triggers["Symbol"].map(sp_map)

    # W1
    triggers["W1"] = (
        triggers["bar_count"].between(W1_BC_MIN, W1_BC_MAX)
        & triggers["s_n"].between(W1_SN_LO, W1_SN_HI)
        & triggers["delta_s_n"].between(W1_DSN_LO, W1_DSN_HI)
    )

    # W2
    triggers["W2"] = triggers["species"] == "calm"

    # W3: SPY D_k == +1 on same Date (from quarantine kernel SPY)
    triggers = triggers.merge(spy_dk, on="Date", how="left")
    triggers["W3"] = triggers["spy_D_k"] == 1
    n_missing_spy = int(triggers["spy_D_k"].isna().sum())
    log(f"  W3 missing SPY dates: {n_missing_spy}")

    # ── Step 3: Forward 20d return via parquet emission order ─────────────────
    log("Step 3: computing 20d forward returns from parquet emission order...")
    # For trigger at bar_count=k, join to same ticker's bar_count=k+20 Close
    fwd_lookup = non_spy[["Symbol", "bar_count", "Close"]].copy()
    fwd_lookup = fwd_lookup.rename(columns={"Close": "close_fwd20"})
    fwd_lookup["bar_count"] = fwd_lookup["bar_count"] - FWD_BARS   # key = trigger's bar_count

    triggers = triggers.merge(
        fwd_lookup[["Symbol", "bar_count", "close_fwd20"]],
        on=["Symbol", "bar_count"], how="left"
    )
    cur = triggers["Close"].to_numpy(dtype=float)
    fwd = triggers["close_fwd20"].to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        triggers["fwd_20d_return"] = np.where(
            (cur > 0) & np.isfinite(fwd),
            (fwd - cur) / cur,
            float("nan")
        )
    n_fwd_valid = int(np.isfinite(triggers["fwd_20d_return"].to_numpy()).sum())
    log(f"  {n_fwd_valid}/{len(triggers)} triggers have 20d forward return")

    # ── Step 4: Cohort assignment ──────────────────────────────────────────────
    log("Step 4: cohort aggregation...")
    c0   = triggers
    c0p  = c0[c0["Close"] >= CLOSE_MIN]
    c1   = c0p[c0p["W1"]]
    c12  = c1[c1["W2"]]
    c13  = c1[c1["W3"]]
    c123 = c1[c1["W2"] & c1["W3"]]

    cohorts = {"C0": c0, "C0p": c0p, "C1": c1, "C12": c12, "C13": c13, "C123": c123}
    labels = {
        "C0":   "All Accumulate triggers (D_k: 0→+1)",
        "C0p":  "C0 ∩ Close >= $5.0",
        "C1":   "C0p ∩ W1 (bar 1-20, s_n band, |Δs_n| band)",
        "C12":  "C1 ∩ W2 (calm species)",
        "C13":  "C1 ∩ W3 (SPY D_k=+1 from quarantine kernel)",
        "C123": "C1 ∩ W2 ∩ W3",
    }

    # Gate 2: subset monotonicity
    gate2_checks = {
        "|C0|>=|C0p|": len(c0) >= len(c0p),
        "|C0p|>=|C1|": len(c0p) >= len(c1),
        "|C1|>=|C12|": len(c1) >= len(c12),
        "|C1|>=|C13|": len(c1) >= len(c13),
        "|C13|>=|C123|": len(c13) >= len(c123),
    }
    gate2_pass = all(gate2_checks.values())
    log(f"Gate 2: {gate2_checks} → {'PASS' if gate2_pass else 'FAIL'}")

    cohort_table_rows = []
    summary_cohorts = {}
    for code, grp in cohorts.items():
        stats = cohort_stats(grp)
        cohort_table_rows.append({
            "cohort_code":    code,
            "cohort_label":   labels[code],
            "N_signals":      stats["N_signals"],
            "N_with_fwd20":   stats["N_with_fwd20"],
            "WR_20d":         stats["WR_20d"],
            "mean_fwd_20d_return": stats["mean_fwd_20d_return"],
            "n_unique_tickers": stats["n_unique_tickers"],
            "binomial_95ci_lower": stats["binomial_95ci_lower"],
            "binomial_95ci_upper": stats["binomial_95ci_upper"],
            "small_n_flag":   stats["small_n_flag"],
        })
        summary_cohorts[code] = stats
        log(f"  {code}: N={stats['N_signals']} WR={stats['WR_20d']} CI=[{stats['binomial_95ci_lower']},{stats['binomial_95ci_upper']}]")

    # ── Step 5: Per-row dump of C13 ∪ C123 ────────────────────────────────────
    tight = pd.concat([c13, c123]).drop_duplicates().copy()
    tight["cohort_label"] = tight.apply(
        lambda r: "C123" if (r["W1"] and r["W2"] and r["W3"]) else "C13",
        axis=1
    )
    tight["species_classification"] = tight["species"]
    tight_cols = [
        "Date", "Symbol", "Close", "bar_count", "s_n", "delta_s_n", "F_n",
        "D_k", "M_k", "B_k", "U_star_k",
        "species_classification", "W1", "W2", "W3",
        "cohort_label", "fwd_20d_return",
    ]
    tight_out = tight[[c for c in tight_cols if c in tight.columns]].sort_values(["Date", "Symbol"])
    log(f"Tight signals (C13 ∪ C123): {len(tight_out)} rows")

    # ── Write outputs ──────────────────────────────────────────────────────────
    cohort_df = pd.DataFrame(cohort_table_rows)
    cohort_path = OUTPUT_DIR / "wave_cohort_reval_20260625.csv"
    cohort_df.to_csv(cohort_path, index=False)
    log(f"  → {cohort_path}")

    tight_path = OUTPUT_DIR / "wave_cohort_tight_signals_20260625.csv"
    tight_out.to_csv(tight_path, index=False)
    log(f"  → {tight_path}")

    summary = {
        "command":       "TFE-CMD-WAVE-COHORT-REVAL-WC-20260625",
        "kernel_sha":    actual_sha,
        "n_rows_parquet": len(df),
        "n_tickers":     int(df["Symbol"].nunique()),
        "accumulate_trigger": "D_k(t-1)==0 AND D_k(t)==+1",
        "species_source": "wave_species_profiles_20260625.csv" if SPECIES_CSV.exists() else "recomputed",
        "spy_source":    "quarantine kernel SPY rows in parquet (NOT uf_core)",
        "n_spy_rows_in_parquet": len(spy_dk),
        "n_missing_spy_w3":  n_missing_spy,
        "integrity_gates": {
            "gate1_sha_match":       actual_sha == EXPECTED_SHA,
            "gate2_subset_monotonic": gate2_pass,
            "gate2_checks":          gate2_checks,
            "gate3_spy_coverage_pct": round(spy_cov * 100, 2),
            "gate3_pass":            gate3_pass,
            "gate4_c0_count":        c0_n,
            "gate4_expected_approx": EXPECTED_C0 - 37,
            "gate4_ok":              gate4_ok,
        },
        "cohort_counts": {k: len(v) for k, v in cohorts.items()},
        "cohorts":       summary_cohorts,
        "wave_bands": {
            "W1_bar_count": [W1_BC_MIN, W1_BC_MAX],
            "W1_s_n":       [W1_SN_LO,  W1_SN_HI],
            "W1_delta_s_n": [W1_DSN_LO, W1_DSN_HI],
            "W2":           "species == calm",
            "W3":           "SPY.D_k == +1 (quarantine kernel)",
            "Close_min":    CLOSE_MIN,
        },
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    summary_path = OUTPUT_DIR / "wave_cohort_reval_20260625_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    log(f"  → {summary_path}")

    log("")
    log("=== COHORT TABLE ===")
    for row in cohort_table_rows:
        wr = f"{row['WR_20d']*100:.1f}%" if row["WR_20d"] is not None else "N/A"
        ci = f"[{row['binomial_95ci_lower']:.3f},{row['binomial_95ci_upper']:.3f}]" if row["binomial_95ci_lower"] is not None else "N/A"
        flag = " ← SMALL-N" if row["small_n_flag"] else ""
        log(f"  {row['cohort_code']:<5} N={row['N_signals']:7,}  WR={wr:6s}  CI={ci}{flag}")
    log(f"\n  Wall time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
