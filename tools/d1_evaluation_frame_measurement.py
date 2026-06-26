#!/usr/bin/env python3
"""
tools/d1_evaluation_frame_measurement.py
Command: TFE-CMD-D1-EVALUATION-FRAME-MEASUREMENT-WC-20260626

Measures the numerical difference between two s_n evaluation frames:

  FRAME-A: s_n at bar i with kappa[i] = |F[i+1] - 2F[i] + F[i-1]|
           (F[i+1] available — full-history quarantine kernel output,
            stored in wave_kernel_state_20260625.parquet)

  FRAME-B: s_n at bar i with kappa[i] = |F[i+1]-2F[i]+F[i-1]|
           (Amendment 4 emission contract — build_snapshot_state_row on
            history ending AT bar i+1; returns second-to-last gate = bar i
            with correct kappa, matching the canonical measurement frame)

No modification to any production file. Read-only measurement.
"""
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
# Use worktree (D1-amended uf_mdg_snapshot with s_n emission) first,
# then workspace for other dependencies.
sys.path.insert(0, str(Path("/workspaces/Tao_Financial_Engine")))
sys.path.insert(0, str(Path("/tmp/tfe-wt-d1")))  # D1 worktree first

from uf_mdg_snapshot import build_snapshot_state_row

PARQUET   = ROOT / "tools" / "wave_kernel_state_20260625.parquet"
OUT_CSV   = ROOT / "tools" / "d1_evaluation_frame_measurement.csv"
OUT_JSON  = ROOT / "tools" / "d1_evaluation_frame_measurement_summary.json"
LOCAL_DSN = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
SEED      = 20260626
SAMPLE_N  = 200
W1_SN_LO, W1_SN_HI = 0.954, 0.969


def log(m):
    print(f"[EFM {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    t0 = time.time()

    # ── Read parquet, build W1 candidate pool ─────────────────────────────────
    log("Loading parquet (read-only)...")
    df = pd.read_parquet(
        PARQUET,
        columns=["Symbol", "Date", "D_k", "s_n", "bar_count", "delta_s_n"],
    )
    df["Date"]    = pd.to_datetime(df["Date"])
    df["D_k_prev"] = df.groupby("Symbol")["D_k"].shift(1)
    df = df[df["Symbol"] != "SPY"]
    log(f"  {len(df):,} rows loaded, {df['Symbol'].nunique()} non-SPY tickers")

    w1 = df[
        df["bar_count"].between(1, 20) &
        (df["D_k"] == 1) &
        (df["D_k_prev"] == 0)
    ].copy()
    log(f"  W1 candidates (bar_count 1-20, D_k 0→+1): {len(w1):,}")

    # ── Sample ────────────────────────────────────────────────────────────────
    random.seed(SEED)
    idx = random.sample(range(len(w1)), min(SAMPLE_N, len(w1)))
    sampled = w1.iloc[idx].reset_index(drop=True)
    log(f"  Sampled {len(sampled)} rows (seed={SEED})")

    # ── Load bars for sampled tickers ─────────────────────────────────────────
    tickers = list(sampled["Symbol"].unique())
    log(f"Loading bars for {len(tickers)} tickers...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur  = conn.cursor()
    tstr = ",".join(f"'{t}'" for t in tickers)
    cur.execute(f"""
        SELECT UPPER(symbol), bar_date, close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({tstr})
          AND bar_date >= '2019-01-01'
        ORDER BY symbol, bar_date
    """)
    bar_rows = cur.fetchall()
    conn.close()

    bars = {}
    for sym, bd, c in bar_rows:
        bars.setdefault(sym, []).append((pd.Timestamp(bd), float(c)))
    bars_df = {}
    for sym, rl in bars.items():
        tmp = pd.DataFrame(rl, columns=["date", "close"])
        bars_df[sym] = tmp.set_index("date").sort_index()
    log(f"  Bars loaded for {len(bars_df)} tickers")

    # ── Compute Frame-A and Frame-B per row ───────────────────────────────────
    log("Computing Frame-A (from parquet) and Frame-B (build_snapshot_state_row)...")
    results = []
    n_skipped = 0

    for _, row in sampled.iterrows():
        ticker      = row["Symbol"]
        target_date = pd.Timestamp(row["Date"]).strftime("%Y-%m-%d")
        bar_count   = int(row["bar_count"])
        s_n_a       = float(row["s_n"])          # Frame-A: quarantine kernel, full history

        bdf = bars_df.get(ticker.upper(), bars_df.get(ticker))
        if bdf is None:
            n_skipped += 1
            continue

        # Frame-B (Amendment 4 emission contract): window ending at target_date+1.
        # build_snapshot_state_row returns second-to-last gate = target_date gate
        # with correct kappa (interior bar, F[target_date+1] available).
        target_ts = pd.Timestamp(target_date)
        all_dates = bdf.index.tolist()
        target_idx = next((j for j, d in enumerate(all_dates) if d >= target_ts), None)
        if target_idx is None or target_idx + 1 >= len(all_dates):
            n_skipped += 1
            continue
        # Window through target_date+1 (one extra bar for correct kappa at target_date)
        next_ts = all_dates[target_idx + 1]
        closes = bdf.loc[bdf.index <= next_ts, "close"].to_numpy(dtype=float)
        if len(closes) < 3:  # need at least 3 bars for second-to-last to exist
            n_skipped += 1
            continue

        cog = build_snapshot_state_row(closes)
        s_n_b = cog.get("s_n")
        if s_n_b is None:
            n_skipped += 1
            continue
        s_n_b = float(s_n_b)

        abs_diff  = abs(s_n_a - s_n_b)
        in_band_a = W1_SN_LO <= s_n_a <= W1_SN_HI
        in_band_b = W1_SN_LO <= s_n_b <= W1_SN_HI

        if in_band_a and in_band_b:
            band_label = "both_in_band"
        elif in_band_a:
            band_label = "only_A_in_band"
        elif in_band_b:
            band_label = "only_B_in_band"
        else:
            band_label = "neither_in_band"

        results.append({
            "ticker":       ticker,
            "target_date":  target_date,
            "bar_count":    bar_count,
            "frame_a_s_n":  s_n_a,
            "frame_b_s_n":  s_n_b,
            "abs_diff":     abs_diff,
            "both_in_w1_band":   in_band_a and in_band_b,
            "only_a":       in_band_a and not in_band_b,
            "only_b":       not in_band_a and in_band_b,
            "band_label":   band_label,
        })

    log(f"  Computed {len(results)} pairs, {n_skipped} skipped")

    # ── Write CSV ─────────────────────────────────────────────────────────────
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUT_CSV, index=False)
    log(f"  CSV → {OUT_CSV}")

    # ── Stats ─────────────────────────────────────────────────────────────────
    diffs = out_df["abs_diff"].to_numpy(dtype=float)
    W1_TOL = 0.969 - 0.954          # = 0.015 (full band width)
    W1_HALF = W1_TOL / 2            # = 0.0075

    n_total = len(diffs)
    band_counts = out_df["band_label"].value_counts().to_dict()

    summary = {
        "command":         "TFE-CMD-D1-EVALUATION-FRAME-MEASUREMENT-WC-20260626",
        "parquet_path":    str(PARQUET.name),
        "w1_candidate_pool_size":  int(len(w1)),
        "sample_n":        len(results),
        "sample_seed":     SEED,
        "n_skipped":       n_skipped,
        "frame_a_note":    ("quarantine kernel s_n from parquet: full-history run, "
                            "kappa[i] uses F[i+1] (next bar available)"),
        "frame_b_note":    ("build_snapshot_state_row on history ending AT target_date: "
                            "kappa[last_bar] = 0 (no F[i+1])"),
        "abs_diff_stats": {
            "max":    round(float(diffs.max()),  8),
            "mean":   round(float(diffs.mean()), 8),
            "median": round(float(np.median(diffs)), 8),
            "p90":    round(float(np.percentile(diffs, 90)), 8),
            "p95":    round(float(np.percentile(diffs, 95)), 8),
            "p99":    round(float(np.percentile(diffs, 99)), 8),
        },
        "threshold_counts": {
            "gt_0_015_full_band_tolerance":  int((diffs > 0.015).sum()),
            "gt_0_0075_half_tolerance":      int((diffs > 0.0075).sum()),
            "gt_0_001_negligible_threshold": int((diffs > 0.001).sum()),
        },
        "w1_band_analysis": {
            "w1_band": [W1_SN_LO, W1_SN_HI],
            "n_frame_a_in_band": int(((out_df["frame_a_s_n"] >= W1_SN_LO) &
                                      (out_df["frame_a_s_n"] <= W1_SN_HI)).sum()),
            "n_frame_b_in_band": int(((out_df["frame_b_s_n"] >= W1_SN_LO) &
                                      (out_df["frame_b_s_n"] <= W1_SN_HI)).sum()),
            "n_both_in_band":    int(band_counts.get("both_in_band", 0)),
            "n_only_A_in_band":  int(band_counts.get("only_A_in_band", 0)),
            "n_only_B_in_band":  int(band_counts.get("only_B_in_band", 0)),
            "n_neither_in_band": int(band_counts.get("neither_in_band", 0)),
        },
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2))
    log(f"  JSON → {OUT_JSON}")

    # ── Stdout report ─────────────────────────────────────────────────────────
    log("")
    log("=== FRAME-A vs FRAME-B MEASUREMENT ===")
    log(f"  W1 pool (parquet gate-count bar_count 1-20, D_k 0→+1): {len(w1):,}")
    log(f"  Sample: {len(results)}")
    log(f"  max abs_diff:    {diffs.max():.6f}")
    log(f"  mean abs_diff:   {diffs.mean():.6f}")
    log(f"  median abs_diff: {np.median(diffs):.6f}")
    log(f"  p90 abs_diff:    {np.percentile(diffs,90):.6f}")
    log(f"  p95 abs_diff:    {np.percentile(diffs,95):.6f}")
    log(f"  p99 abs_diff:    {np.percentile(diffs,99):.6f}")
    log(f"  > full band (0.015): {(diffs>0.015).sum()}")
    log(f"  > half band (0.0075):{(diffs>0.0075).sum()}")
    log(f"  > 0.001:             {(diffs>0.001).sum()}")
    log("")
    log(f"  W1 band [0.954, 0.969]:")
    log(f"    Frame-A in band: {summary['w1_band_analysis']['n_frame_a_in_band']}")
    log(f"    Frame-B in band: {summary['w1_band_analysis']['n_frame_b_in_band']}")
    log(f"    both in band:    {summary['w1_band_analysis']['n_both_in_band']}")
    log(f"    only A in band:  {summary['w1_band_analysis']['n_only_A_in_band']}")
    log(f"    only B in band:  {summary['w1_band_analysis']['n_only_B_in_band']}")
    log(f"    neither:         {summary['w1_band_analysis']['n_neither_in_band']}")
    log(f"\n  Wall time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
