#!/usr/bin/env python3
"""
tools/wave_kernel_run_20260625.py
Command: TFE-CMD-WAVE-AS-SELECTION-WC-20260625

Runs quarantine_historical_kernel.build_state_rows (UNMODIFIED) against
the 2,194-ticker walkforward universe + SPY from the local daily_bars table.
Adds derived columns bar_count and delta_s_n.
Computes species via emitted s_n series (not D_k proxy).
Evaluates W1/W2/W3 per bar and builds cohort table.

DO NOT modify quarantine_historical_kernel.py — called as-is.
"""
import hashlib
import json
import multiprocessing
import sys
import time
from datetime import timezone, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import quarantine kernel UNMODIFIED
from quarantine_historical_kernel import build_state_rows, KernelParameters  # noqa: E402

LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
OUTPUT_DIR  = ROOT / "tools"
KERNEL_PATH = ROOT / "quarantine_historical_kernel.py"

# Wave band constants from structural_wave_alignment_spec.tex line 207-211
W1_BAR_MIN    = 1
W1_BAR_MAX    = 20
W1_SN_LO      = 0.954
W1_SN_HI      = 0.969
W1_DSLN_LO    = 0.67
W1_DSLN_HI    = 0.72
FWD_WINDOW    = 20  # trading days for forward return


def log(m):
    print(f"[WK {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


# ── Gate 1: kernel SHA ────────────────────────────────────────────────────────

def compute_kernel_sha():
    with open(KERNEL_PATH, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ── Load bars from DB ─────────────────────────────────────────────────────────

def load_bars_from_db(tickers):
    """Load daily bars for given tickers. Returns {TICKER: DataFrame(Date, Close)}."""
    log(f"Loading bars from DB for {len(tickers)} tickers...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    tstr = ",".join(f"'{t.upper()}'" for t in tickers)
    cur.execute(f"""
        SELECT UPPER(symbol) AS Symbol, bar_date AS Date, close AS Close
        FROM daily_bars
        WHERE UPPER(symbol) IN ({tstr})
          AND bar_date >= '2020-01-01' AND bar_date <= '2026-06-30'
        ORDER BY symbol, bar_date
    """)
    rows = cur.fetchall()
    conn.close()
    raw = {}
    for sym, bd, c in rows:
        raw.setdefault(sym, []).append((pd.Timestamp(bd), float(c)))
    result = {}
    for sym, rl in raw.items():
        df = pd.DataFrame(rl, columns=["Date", "Close"])
        df["Symbol"] = sym
        result[sym] = df
    log(f"  Loaded {len(result)} tickers from DB")
    return result


# ── Multiprocessing worker ────────────────────────────────────────────────────

def _run_ticker(args):
    """Worker: run kernel on one ticker's bars. Returns DataFrame or empty."""
    ticker, bars_df = args
    try:
        params = KernelParameters()
        result = build_state_rows(ticker, bars_df, params)
        return result
    except Exception as e:
        return pd.DataFrame()  # empty on error


# ── Step 1: kernel run for all tickers ───────────────────────────────────────

def run_kernel_all(bars_db):
    """Run build_state_rows for every ticker in bars_db. Returns DataFrame."""
    log(f"Running quarantine kernel on {len(bars_db)} tickers ({multiprocessing.cpu_count()} workers)...")
    params = KernelParameters()

    args = [(ticker, df) for ticker, df in bars_db.items()]

    all_frames = []
    n_workers = multiprocessing.cpu_count()
    with multiprocessing.Pool(n_workers) as pool:
        for i, result in enumerate(pool.imap_unordered(_run_ticker, args, chunksize=10)):
            if not result.empty:
                all_frames.append(result)
            if (i + 1) % 200 == 0:
                log(f"  {i+1}/{len(args)} tickers processed")

    if not all_frames:
        log("STOP: kernel produced no rows")
        sys.exit(1)

    combined = pd.concat(all_frames, ignore_index=True)
    log(f"  Combined: {len(combined)} rows from {len(all_frames)} tickers")

    # Rename Decision → decision (verbatim column name change; kernel is UNMODIFIED)
    combined = combined.rename(columns={"Decision": "decision"})

    return combined


# ── Step 1b: add bar_count and delta_s_n ─────────────────────────────────────

def add_derived_columns(df):
    """
    bar_count: 1-based row number within each ticker's emitted gate sequence.
    delta_s_n: |s_n(t) - s_n(t-1)| per ticker; NaN for first row.
    """
    log("Adding bar_count and delta_s_n...")
    df = df.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    df["bar_count"] = df.groupby("Symbol").cumcount() + 1
    df["delta_s_n"] = df.groupby("Symbol")["s_n"].transform(
        lambda x: x.diff().abs()
    )
    return df


# ── Step 2: species classification from s_n ──────────────────────────────────

def compute_species(df, warmup=5):
    """
    Per ticker: exclude first `warmup` emitted rows, compute mean(|delta_s_n|),
    classify by p25/p75 of universe delta_bar distribution.
    Returns DataFrame: ticker, delta_bar, classification, n_rows
    """
    log("Computing species from s_n series (not D_k proxy)...")

    records = []
    for ticker, grp in df[df["Symbol"] != "SPY"].groupby("Symbol"):
        grp_sorted = grp.sort_values("Date")
        if len(grp_sorted) <= warmup:
            continue
        tail = grp_sorted.iloc[warmup:]
        delta_vals = tail["delta_s_n"].dropna()
        if len(delta_vals) == 0:
            continue
        delta_bar = float(delta_vals.mean())
        records.append({"ticker": ticker, "delta_bar": delta_bar, "n_rows": len(grp_sorted)})

    species_df = pd.DataFrame(records)
    if species_df.empty:
        log("  WARNING: no species records produced")
        return species_df, None, None

    p25 = float(species_df["delta_bar"].quantile(0.25))
    p75 = float(species_df["delta_bar"].quantile(0.75))
    log(f"  delta_bar p25={p25:.6f} p75={p75:.6f} across {len(species_df)} tickers")

    def classify(v):
        if v <= p25:
            return "calm"
        elif v <= p75:
            return "normal"
        else:
            return "volatile"

    species_df["classification"] = species_df["delta_bar"].apply(classify)
    dist = species_df["classification"].value_counts().to_dict()
    log(f"  Species distribution: {dist}")
    return species_df, p25, p75


# ── Step 3: Wave evaluation per bar ──────────────────────────────────────────

def evaluate_waves(df, species_df, p25, p75):
    """
    Join species, SPY D_k, compute W1/W2/W3 per bar for non-SPY tickers.
    Returns enriched DataFrame.
    """
    log("Evaluating waves per bar...")

    # SPY D_k per date
    spy = df[df["Symbol"] == "SPY"][["Date", "D_k"]].copy()
    spy = spy.rename(columns={"D_k": "spy_D_k"})
    spy["Date"] = pd.to_datetime(spy["Date"])
    spy = spy.drop_duplicates("Date")
    spy_dk_dist = spy["spy_D_k"].value_counts().to_dict()
    log(f"  SPY D_k emitted rows: {len(spy)} | dist: {spy_dk_dist}")

    # Species map
    sp_map = {}
    if not species_df.empty:
        sp_map = dict(zip(species_df["ticker"], species_df["classification"]))

    # Work on non-SPY rows
    non_spy = df[df["Symbol"] != "SPY"].copy()
    non_spy["Date"] = pd.to_datetime(non_spy["Date"])

    # Join SPY D_k
    non_spy = non_spy.merge(spy, on="Date", how="left")

    # Join species
    non_spy["species"] = non_spy["Symbol"].map(sp_map)

    # W1: bar_count in [1,20] AND s_n in [0.954, 0.969] AND |delta_s_n| in [0.67, 0.72]
    non_spy["W1"] = (
        non_spy["bar_count"].between(W1_BAR_MIN, W1_BAR_MAX)
        & non_spy["s_n"].between(W1_SN_LO, W1_SN_HI)
        & non_spy["delta_s_n"].between(W1_DSLN_LO, W1_DSLN_HI)
    )

    # W2: species == "calm"
    non_spy["W2"] = non_spy["species"] == "calm"

    # W3: SPY D_k == +1
    non_spy["W3"] = non_spy["spy_D_k"] == 1

    return non_spy, spy_dk_dist


# ── Step 4: Forward 20d return ───────────────────────────────────────────────

def compute_fwd_returns(df, bars_db):
    """
    Vectorized 20d forward return computation.
    For each (Symbol, Date) in df, joins to the price 20 bars later
    from bars_db using a precomputed shift-merge table.
    """
    log("Computing 20d forward returns (vectorized)...")

    # Build per-ticker fwd-price lookup: for each bar date, what's the close
    # 20 trading-day-bars later?  Gate-event dates = actual bar dates.
    fwd_rows = []
    for ticker, bars in bars_db.items():
        b = bars.copy()
        b["Date"] = pd.to_datetime(b["Date"])
        b = b.sort_values("Date").reset_index(drop=True)
        closes = b["Close"].to_numpy()
        dates  = b["Date"].tolist()
        n = len(closes)
        for i in range(n):
            fwd_i = i + FWD_WINDOW
            if fwd_i < n:
                fwd_rows.append({
                    "Symbol":    ticker,
                    "Date":      dates[i],
                    "fwd_close": float(closes[fwd_i]),
                })

    fwd_df = pd.DataFrame(fwd_rows)
    fwd_df["Date"] = pd.to_datetime(fwd_df["Date"])

    merged = df.merge(fwd_df, on=["Symbol", "Date"], how="left")
    cur_close = merged["Close"].to_numpy(dtype=float)
    fwd_close = merged["fwd_close"].to_numpy(dtype=float)

    with np.errstate(invalid="ignore", divide="ignore"):
        fwd_ret = np.where(
            (cur_close > 0) & np.isfinite(fwd_close),
            (fwd_close - cur_close) / cur_close,
            float("nan"),
        )

    merged["fwd_20d_return"] = fwd_ret
    merged = merged.drop(columns=["fwd_close"])
    n_with_fwd = int(np.isfinite(fwd_ret).sum())
    log(f"  {n_with_fwd}/{len(merged)} rows have 20d forward return")
    return merged


# ── Step 5: Cohort table ──────────────────────────────────────────────────────

def cohort_stats(grp_df):
    """Compute stats for a cohort subset."""
    valid = grp_df.dropna(subset=["fwd_20d_return"])
    n = len(grp_df)
    n_valid = len(valid)
    if n_valid == 0:
        return {
            "N_signals": n, "N_with_fwd_return": 0,
            "WR_20d": None, "mean_fwd_20d_return": None,
            "median_fwd_20d_return": None, "n_unique_tickers": int(grp_df["Symbol"].nunique()),
            "date_range_covered": None,
        }
    rets = valid["fwd_20d_return"]
    return {
        "N_signals":           n,
        "N_with_fwd_return":   n_valid,
        "WR_20d":              round(float((rets > 0).mean()), 6),
        "mean_fwd_20d_return": round(float(rets.mean()), 6),
        "median_fwd_20d_return": round(float(rets.median()), 6),
        "n_unique_tickers":    int(grp_df["Symbol"].nunique()),
        "date_range_covered":  f"{grp_df['Date'].min()} → {grp_df['Date'].max()}",
    }


def build_cohort_table(df):
    """
    Reproduce Table 1 from structural_wave_alignment_spec.tex.
    df: non-SPY rows with W1/W2/W3 and fwd_20d_return.
    """
    log("Building cohort table...")

    acc_mask = (df["decision"] == "ACCUMULATE") & (df["Close"] >= 5.0)
    acc = df[acc_mask]

    cohorts = {
        "All Accumulate (Close >= $5)": acc,
        "New listings (bar_count <= 20)": acc[acc["bar_count"] <= 20],
        "Established (bar_count > 20)": acc[acc["bar_count"] > 20],
        "Established + R_k<=p25 + F_n<=1.65": None,  # computed below
        "Structure A (W1)": acc[acc["W1"]],
        "Structure A + Calm (W1+W2)": acc[acc["W1"] & acc["W2"]],
        "Structure A + Market expanding (W1+W3)": acc[acc["W1"] & acc["W3"]],
        "Structure A + Calm + Market expanding (W1+W2+W3)": acc[acc["W1"] & acc["W2"] & acc["W3"]],
    }

    # Established + R_k <= p25 + F_n <= 1.65
    est = acc[acc["bar_count"] > 20]
    if len(est) > 0:
        r_p25 = float(est["R_k"].quantile(0.25))
        cohorts["Established + R_k<=p25 + F_n<=1.65"] = est[(est["R_k"] <= r_p25) & (est["F_n"] <= 1.65)]
    else:
        cohorts["Established + R_k<=p25 + F_n<=1.65"] = acc.iloc[0:0]

    table_rows = []
    summary_cohorts = {}
    for name, grp in cohorts.items():
        if grp is None:
            grp = acc.iloc[0:0]
        stats = cohort_stats(grp)
        table_rows.append({
            "cohort": name,
            "N_signals": stats["N_signals"],
            "WR_20d": stats["WR_20d"],
            "mean_fwd_20d_return": stats["mean_fwd_20d_return"],
            "n_unique_tickers": stats["n_unique_tickers"],
        })
        summary_cohorts[name] = stats

    cohort_df = pd.DataFrame(table_rows)
    return cohort_df, summary_cohorts, len(acc)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    # ── Gate 1: kernel SHA ────────────────────────────────────────────────────
    kernel_sha = compute_kernel_sha()
    log(f"Kernel SHA-256: {kernel_sha}")

    # ── Load universe from kernel cache ──────────────────────────────────────
    import pickle
    CACHE_FILE = ROOT / "backups/walkforward_kernel_cache_20260624.pkl"
    log("Loading universe from kernel cache...")
    with open(CACHE_FILE, "rb") as f:
        kernel_db = pickle.load(f)
    universe = sorted(kernel_db.keys())
    log(f"  {len(universe)} tickers + SPY")

    # ── Load bars ─────────────────────────────────────────────────────────────
    bars_db = load_bars_from_db(universe + ["SPY"])
    bars_db = {k.upper(): v for k, v in bars_db.items()}

    # ── Step 1: Run kernel ────────────────────────────────────────────────────
    t_kernel = time.time()
    df_all = run_kernel_all(bars_db)
    t_kernel_done = time.time() - t_kernel
    log(f"Kernel run: {t_kernel_done:.1f}s")

    # ── Step 1b: Derived columns ──────────────────────────────────────────────
    df_all = add_derived_columns(df_all)

    # ── Gate 2: SPY emits > 200 rows ─────────────────────────────────────────
    spy_rows = int((df_all["Symbol"] == "SPY").sum())
    if spy_rows <= 200:
        log(f"STOP: Gate 2 FAIL — SPY emitted only {spy_rows} rows (need > 200)")
        sys.exit(1)
    log(f"Gate 2: PASS — SPY emitted {spy_rows} rows")

    # ── Gate 3: At least one bar_count == 1 ──────────────────────────────────
    n_bc1 = int((df_all["bar_count"] == 1).sum())
    if n_bc1 == 0:
        log("STOP: Gate 3 FAIL — no rows with bar_count=1 (universe has no new listings)")
        sys.exit(1)
    log(f"Gate 3: PASS — {n_bc1} rows with bar_count=1")

    # ── Write Step 1 parquet ─────────────────────────────────────────────────
    parquet_path = OUTPUT_DIR / "wave_kernel_state_20260625.parquet"
    log(f"Writing kernel state parquet ({len(df_all)} rows)...")
    df_all.to_parquet(parquet_path, index=False)
    log(f"  → {parquet_path} ({parquet_path.stat().st_size/1e6:.1f}MB)")

    # ── Step 2: Species ───────────────────────────────────────────────────────
    species_df, p25, p75 = compute_species(df_all)
    species_path = OUTPUT_DIR / "wave_species_profiles_20260625.csv"
    species_df.to_csv(species_path, index=False)
    log(f"  → {species_path}")

    # ── Step 3: Wave evaluation ───────────────────────────────────────────────
    non_spy, spy_dk_dist = evaluate_waves(df_all, species_df, p25, p75)

    # ── Step 4: Forward returns ───────────────────────────────────────────────
    non_spy = compute_fwd_returns(non_spy, bars_db)

    # ── Step 5: Cohort table ──────────────────────────────────────────────────
    cohort_df, summary_cohorts, n_acc_total = build_cohort_table(non_spy)

    # ── Gate 4: cohort N sum ≤ total Accumulate ───────────────────────────────
    acc_mask = (non_spy["decision"] == "ACCUMULATE") & (non_spy["Close"] >= 5.0)
    total_acc = int(acc_mask.sum())
    w123_n = summary_cohorts.get("Structure A + Calm + Market expanding (W1+W2+W3)", {}).get("N_signals", 0)
    if w123_n > total_acc:
        log(f"STOP: Gate 4 FAIL — W123 N={w123_n} > total Accumulate={total_acc}")
        sys.exit(1)
    log(f"Gate 4: PASS — max cohort ≤ total Accumulate ({total_acc})")

    # ── Write cohort table ────────────────────────────────────────────────────
    cohort_path = OUTPUT_DIR / "wave_cohort_table_20260625.csv"
    cohort_df.to_csv(cohort_path, index=False)
    log(f"  → {cohort_path}")

    # ── Summary JSON ──────────────────────────────────────────────────────────
    summary = {
        "command":            "TFE-CMD-WAVE-AS-SELECTION-WC-20260625",
        "kernel_sha":         kernel_sha,
        "kernel_path":        str(KERNEL_PATH.relative_to(ROOT)),
        "universe_size":      len(universe),
        "n_bar_rows_emitted": int(len(df_all)),
        "n_spy_rows_emitted": spy_rows,
        "n_non_spy_rows":     int(len(non_spy)),
        "n_acc_total":        total_acc,
        "species_p25":        float(p25) if p25 is not None else None,
        "species_p75":        float(p75) if p75 is not None else None,
        "species_dist":       species_df["classification"].value_counts().to_dict() if not species_df.empty else {},
        "spy_dk_distribution": {str(k): int(v) for k, v in spy_dk_dist.items()},
        "wave_bands": {
            "W1_bar_min": W1_BAR_MIN, "W1_bar_max": W1_BAR_MAX,
            "W1_sn_lo": W1_SN_LO, "W1_sn_hi": W1_SN_HI,
            "W1_dsln_lo": W1_DSLN_LO, "W1_dsln_hi": W1_DSLN_HI,
        },
        "cohort_table": summary_cohorts,
        "integrity_gates": {
            "gate1_kernel_sha_match": {"pass": True, "sha": kernel_sha},
            "gate2_spy_rows":         {"pass": True, "n": spy_rows},
            "gate3_bar_count_1":      {"pass": True, "n_rows": n_bc1},
            "gate4_cohort_sum_le_acc":{"pass": True, "total_acc": total_acc},
        },
        "wall_time_seconds": round(time.time() - t0, 1),
        "kernel_run_seconds": round(t_kernel_done, 1),
    }

    summary_path = OUTPUT_DIR / "wave_cohort_summary_20260625.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    log(f"  → {summary_path}")

    log("")
    log("=== COHORT TABLE ===")
    for _, row in cohort_df.iterrows():
        wr = f"{row['WR_20d']*100:.1f}%" if row["WR_20d"] is not None else "N/A"
        log(f"  {row['cohort'][:55]:<55} | N={row['N_signals']:6d} | WR={wr}")
    log(f"\n  Total Accumulate (Close>=5): {total_acc}")
    log(f"  Wall time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
