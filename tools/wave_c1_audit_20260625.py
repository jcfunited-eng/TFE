#!/usr/bin/env python3
"""
tools/wave_c1_audit_20260625.py
Command: TFE-CMD-WAVE-COHORT-DIAGNOSTIC-WC-20260625-B

Extracts the 372 C1 signals from the parquet and computes three
forward-return methods:
  20gates : 20 gate-event rows forward per ticker (what prior cohort used)
  20cal   : 20 SPY-calendar trading days forward, matched to ticker's
            nearest emission
  20bars  : 20 bars forward from daily_bars table (raw, cleanest reference)

Integrity: must reproduce 372 signals and WR_20gates ≈ 92.2%.
"""
import hashlib
import json
import sys
import time
from datetime import timezone, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

ROOT        = Path(__file__).resolve().parent.parent
PARQUET     = ROOT / "tools" / "wave_kernel_state_20260625.parquet"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"
OUTPUT_DIR  = ROOT / "tools"
LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"

EXPECTED_SHA     = "02e0d373658c2703f1916e0b9cc5b0e229d49646740efbc18fefc58bf770abd4"
EXPECTED_N       = 372
EXPECTED_WR_GATE = 0.922  # 92.2% from prior cohort; tolerance ±0.005

W1_BC_MIN = 1;  W1_BC_MAX = 20
W1_SN_LO  = 0.954; W1_SN_HI  = 0.969
W1_DSN_LO = 0.67;  W1_DSN_HI = 0.72
CLOSE_MIN = 5.0
FWD_BARS  = 20


def log(m):
    print(f"[AUD {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def pctile(arr, q):
    return round(float(np.nanpercentile(arr, q)), 4) if len(arr) > 0 else None


def main():
    t0 = time.time()

    # ── Integrity: kernel SHA ─────────────────────────────────────────────────
    actual_sha = hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_SHA:
        log(f"STOP: kernel SHA mismatch. got={actual_sha}")
        sys.exit(1)
    log(f"Kernel SHA: {actual_sha} ✓")

    # ── Load parquet — only needed columns ────────────────────────────────────
    log("Loading parquet...")
    cols = ["Symbol", "Date", "Close", "D_k", "M_k", "B_k", "U_star_k",
            "s_n", "delta_s_n", "F_n", "bar_count"]
    df = pd.read_parquet(PARQUET, columns=cols)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    df["D_k_prev"] = df.groupby("Symbol")["D_k"].shift(1)
    log(f"  {len(df):,} rows loaded")

    # ── Reproduce C1 filter ───────────────────────────────────────────────────
    log("Applying C1 filter...")
    non_spy = df[df["Symbol"] != "SPY"].copy()
    acc_mask = (non_spy["D_k"] == 1) & (non_spy["D_k_prev"] == 0)
    c0p_mask = acc_mask & (non_spy["Close"] >= CLOSE_MIN)
    w1_mask  = (
        c0p_mask
        & non_spy["bar_count"].between(W1_BC_MIN, W1_BC_MAX)
        & non_spy["s_n"].between(W1_SN_LO, W1_SN_HI)
        & non_spy["delta_s_n"].between(W1_DSN_LO, W1_DSN_HI)
    )
    c1 = non_spy[w1_mask].copy().reset_index(drop=True)
    c1.index.name = None

    n_found = len(c1)
    log(f"  C1 signals found: {n_found}")
    if n_found != EXPECTED_N:
        log(f"STOP: expected {EXPECTED_N} signals, got {n_found}")
        sys.exit(1)
    log(f"  n_signals_total = {n_found} ✓")

    # ── Build per-ticker emission lookup (bar_count → Close/Date) ─────────────
    log("Building per-ticker emission lookup...")
    bc_lookup = non_spy[["Symbol", "bar_count", "Date", "Close"]].set_index(
        ["Symbol", "bar_count"]
    )

    # ── Method 1: 20 gate-events forward (what prior cohort used) ─────────────
    log("Method 1: 20 gate-events forward...")
    fwd_keys = [
        (row["Symbol"], row["bar_count"] + FWD_BARS)
        for _, row in c1.iterrows()
    ]
    fwd_dates_gates = []
    fwd_closes_gates = []
    for sym, fwd_bc in fwd_keys:
        if (sym, fwd_bc) in bc_lookup.index:
            r = bc_lookup.loc[(sym, fwd_bc)]
            fwd_dates_gates.append(pd.Timestamp(r["Date"]))
            fwd_closes_gates.append(float(r["Close"]))
        else:
            fwd_dates_gates.append(pd.NaT)
            fwd_closes_gates.append(float("nan"))

    c1["Date_fwd20gates"] = fwd_dates_gates
    c1["Close_fwd20gates"] = fwd_closes_gates
    c1["n_calendar_days_to_fwd20gates"] = (
        c1["Date_fwd20gates"] - c1["Date"]
    ).dt.days
    cur = c1["Close"].to_numpy(dtype=float)
    fwd = c1["Close_fwd20gates"].to_numpy(dtype=float)
    c1["fwd_return_20gates"] = np.where(
        np.isfinite(fwd) & (cur > 0), (fwd - cur) / cur, float("nan")
    )

    # Sanity check: WR_20gates must match prior
    valid_gates = c1["fwd_return_20gates"].dropna()
    wr_gates = float((valid_gates > 0).mean()) if len(valid_gates) > 0 else float("nan")
    if abs(wr_gates - EXPECTED_WR_GATE) > 0.005:
        log(f"STOP: WR_20gates = {wr_gates:.4f}, expected ≈ {EXPECTED_WR_GATE:.3f} (|diff|>0.005)")
        log("Prior cohort reval is non-reproducible — investigate before proceeding")
        sys.exit(1)
    log(f"  WR_20gates = {wr_gates:.4f} ✓ (matches prior {EXPECTED_WR_GATE:.3f})")

    # ── Method 2: 20 SPY-calendar trading days forward ────────────────────────
    log("Method 2: 20 SPY-calendar trading days forward...")
    spy_dates = sorted(df[df["Symbol"] == "SPY"]["Date"].dt.normalize().unique())
    spy_date_to_idx = {d: i for i, d in enumerate(spy_dates)}

    # Per-ticker: date → (Close) lookup for nearest-on-or-before date
    ticker_date_sorted = (
        non_spy[["Symbol", "Date", "Close"]]
        .copy()
        .sort_values(["Symbol", "Date"])
    )
    # For each ticker, create sorted date array for searchsorted
    ticker_dates = {
        sym: grp["Date"].dt.normalize().to_numpy()
        for sym, grp in ticker_date_sorted.groupby("Symbol")
    }
    ticker_closes = {
        sym: grp["Close"].to_numpy(dtype=float)
        for sym, grp in ticker_date_sorted.groupby("Symbol")
    }

    fwd_dates_cal = []
    fwd_closes_cal = []
    for _, row in c1.iterrows():
        trig_date = pd.Timestamp(row["Date"]).normalize()
        sym = row["Symbol"]
        spy_idx = spy_date_to_idx.get(trig_date)
        if spy_idx is None or spy_idx + FWD_BARS >= len(spy_dates):
            fwd_dates_cal.append(pd.NaT)
            fwd_closes_cal.append(float("nan"))
            continue
        target_date = spy_dates[spy_idx + FWD_BARS]
        # Find ticker's emission on or before target_date
        t_dates = ticker_dates.get(sym)
        t_closes = ticker_closes.get(sym)
        if t_dates is None or len(t_dates) == 0:
            fwd_dates_cal.append(pd.NaT)
            fwd_closes_cal.append(float("nan"))
            continue
        pos = np.searchsorted(t_dates, target_date, side="right") - 1
        if pos < 0:
            fwd_dates_cal.append(pd.NaT)
            fwd_closes_cal.append(float("nan"))
        else:
            fwd_dates_cal.append(pd.Timestamp(t_dates[pos]))
            fwd_closes_cal.append(float(t_closes[pos]))

    c1["Date_fwd20cal"] = fwd_dates_cal
    c1["Close_fwd20cal"] = fwd_closes_cal
    cur = c1["Close"].to_numpy(dtype=float)
    fwd = c1["Close_fwd20cal"].to_numpy(dtype=float)
    c1["fwd_return_20cal"] = np.where(
        np.isfinite(fwd) & (cur > 0), (fwd - cur) / cur, float("nan")
    )

    # ── Method 3: 20 bars forward from daily_bars table ───────────────────────
    log("Method 3: 20 bars forward from daily_bars...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur_db = conn.cursor()

    # Build the query: for each (symbol, date), find the 20th trading bar after
    # that date using daily_bars. Batch all tickers at once.
    symbols = list(c1["Symbol"].unique())
    sym_str = ",".join(f"'{s}'" for s in symbols)

    # Load all relevant bars for these tickers
    cur_db.execute(f"""
        SELECT UPPER(symbol), bar_date, close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({sym_str})
          AND bar_date >= '2020-01-01'
        ORDER BY symbol, bar_date
    """)
    bar_rows = cur_db.fetchall()
    conn.close()

    bar_df = pd.DataFrame(bar_rows, columns=["Symbol", "bar_date", "close"])
    bar_df["bar_date"] = pd.to_datetime(bar_df["bar_date"])
    # per-ticker sorted arrays
    bar_dates_by_sym = {}
    bar_closes_by_sym = {}
    for sym, grp in bar_df.groupby("Symbol"):
        bar_dates_by_sym[sym]  = grp["bar_date"].to_numpy()
        bar_closes_by_sym[sym] = grp["close"].to_numpy(dtype=float)

    fwd_dates_bars = []
    fwd_closes_bars = []
    for _, row in c1.iterrows():
        sym  = row["Symbol"]
        trig = pd.Timestamp(row["Date"]).normalize()
        bd   = bar_dates_by_sym.get(sym)
        bc   = bar_closes_by_sym.get(sym)
        if bd is None:
            fwd_dates_bars.append(pd.NaT)
            fwd_closes_bars.append(float("nan"))
            continue
        # find first bar strictly after trigger date
        pos = np.searchsorted(bd, trig, side="right")
        fwd_pos = pos + FWD_BARS - 1   # 20th bar after trigger (1-indexed: pos, pos+1, ..., pos+19)
        if fwd_pos >= len(bd):
            fwd_dates_bars.append(pd.NaT)
            fwd_closes_bars.append(float("nan"))
        else:
            fwd_dates_bars.append(pd.Timestamp(bd[fwd_pos]))
            fwd_closes_bars.append(float(bc[fwd_pos]))

    c1["Close_fwd20bars"] = fwd_closes_bars
    c1["Date_fwd20bars"]  = fwd_dates_bars
    cur_arr = c1["Close"].to_numpy(dtype=float)
    fwd_arr = c1["Close_fwd20bars"].to_numpy(dtype=float)
    c1["fwd_return_20bars"] = np.where(
        np.isfinite(fwd_arr) & (cur_arr > 0), (fwd_arr - cur_arr) / cur_arr, float("nan")
    )

    # ── Build per-row audit CSV ───────────────────────────────────────────────
    log("Building per-row audit CSV...")
    c1 = c1.sort_values("Date").reset_index(drop=True)
    c1.index.name = "trigger_idx"
    c1 = c1.reset_index()

    out_cols = [
        "trigger_idx", "Symbol", "Date", "Close",
        "bar_count", "s_n", "delta_s_n", "F_n", "B_k", "M_k", "D_k",
        # Method 1: gates
        "Date_fwd20gates", "Close_fwd20gates",
        "n_calendar_days_to_fwd20gates", "fwd_return_20gates",
        # Method 2: calendar
        "Date_fwd20cal", "Close_fwd20cal", "fwd_return_20cal",
        # Method 3: bars
        "Date_fwd20bars", "Close_fwd20bars", "fwd_return_20bars",
    ]
    c1 = c1.rename(columns={"Date": "Date_trigger", "Close": "Close_trigger"})
    out_cols[2] = "Date_trigger"
    out_cols[3] = "Close_trigger"

    audit_path = OUTPUT_DIR / "wave_c1_audit_20260625.csv"
    c1[out_cols].to_csv(audit_path, index=False)
    log(f"  → {audit_path} ({audit_path.stat().st_size/1e3:.0f}KB)")

    # ── Summary stats ─────────────────────────────────────────────────────────
    def method_stats(ret_col, date_col):
        valid = c1[ret_col].dropna()
        nv = len(valid)
        arr = valid.to_numpy(dtype=float)
        return {
            "n_with_fwd": nv,
            "WR": round(float((valid > 0).mean()), 6) if nv > 0 else None,
            "mean_fwd_return": round(float(valid.mean()), 6) if nv > 0 else None,
        }

    gates_valid = c1["fwd_return_20gates"].dropna()
    n_all3 = int(
        c1[["fwd_return_20gates","fwd_return_20cal","fwd_return_20bars"]]
        .notna().all(axis=1).sum()
    )
    cal_days_arr = c1["n_calendar_days_to_fwd20gates"].dropna().to_numpy(dtype=float)

    subset_3 = c1[
        c1[["fwd_return_20gates","fwd_return_20cal","fwd_return_20bars"]].notna().all(axis=1)
    ]

    summary = {
        "command":        "TFE-CMD-WAVE-COHORT-DIAGNOSTIC-WC-20260625-B",
        "kernel_sha":     actual_sha,
        "n_signals_total": n_found,
        "n_with_fwd20gates":  int(gates_valid.count()),
        "WR_20gates":         round(wr_gates, 6),
        "mean_fwd_return_20gates": round(float(gates_valid.mean()), 6),
        "distribution_of_n_calendar_days_to_fwd20gates": {
            "min": pctile(cal_days_arr,  0),
            "p10": pctile(cal_days_arr, 10),
            "p25": pctile(cal_days_arr, 25),
            "p50": pctile(cal_days_arr, 50),
            "p75": pctile(cal_days_arr, 75),
            "p90": pctile(cal_days_arr, 90),
            "max": pctile(cal_days_arr,100),
        },
        **{k: v for k, v in {
            "n_with_fwd20cal":   method_stats("fwd_return_20cal","Date_fwd20cal")["n_with_fwd"],
            "WR_20cal":          method_stats("fwd_return_20cal","Date_fwd20cal")["WR"],
            "mean_fwd_return_20cal": method_stats("fwd_return_20cal","Date_fwd20cal")["mean_fwd_return"],
        }.items()},
        **{k: v for k, v in {
            "n_with_fwd20bars":  method_stats("fwd_return_20bars","Date_fwd20bars")["n_with_fwd"],
            "WR_20bars":         method_stats("fwd_return_20bars","Date_fwd20bars")["WR"],
            "mean_fwd_return_20bars": method_stats("fwd_return_20bars","Date_fwd20bars")["mean_fwd_return"],
        }.items()},
        "n_signals_with_all_three": n_all3,
        "WR_20gates_on_subset_all3": round(float((subset_3["fwd_return_20gates"] > 0).mean()), 6) if n_all3 > 0 else None,
        "WR_20cal_on_subset_all3":   round(float((subset_3["fwd_return_20cal"]   > 0).mean()), 6) if n_all3 > 0 else None,
        "WR_20bars_on_subset_all3":  round(float((subset_3["fwd_return_20bars"]  > 0).mean()), 6) if n_all3 > 0 else None,
        "integrity": {
            "sha_match":   actual_sha == EXPECTED_SHA,
            "n_exact_372": n_found == EXPECTED_N,
            "wr_gates_reproduced": abs(wr_gates - EXPECTED_WR_GATE) <= 0.005,
        },
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    summary_path = OUTPUT_DIR / "wave_c1_audit_20260625_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    log(f"  → {summary_path}")

    log("")
    log(f"n_signals_total = {n_found}")
    log(f"WR_20gates = {wr_gates:.4f}  ({int(gates_valid.count())} valid)")
    log(f"WR_20cal   = {summary['WR_20cal']}  ({summary['n_with_fwd20cal']} valid)")
    log(f"WR_20bars  = {summary['WR_20bars']}  ({summary['n_with_fwd20bars']} valid)")
    log(f"All-3 subset: N={n_all3}  gates={summary['WR_20gates_on_subset_all3']}  cal={summary['WR_20cal_on_subset_all3']}  bars={summary['WR_20bars_on_subset_all3']}")
    log(f"Calendar days to fwd20gates: p50={summary['distribution_of_n_calendar_days_to_fwd20gates']['p50']}  p90={summary['distribution_of_n_calendar_days_to_fwd20gates']['p90']}  max={summary['distribution_of_n_calendar_days_to_fwd20gates']['max']}")
    log(f"Wall time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
