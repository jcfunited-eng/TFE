#!/usr/bin/env python3
"""
tools/3wa_cohort_decomp_20260625.py
Command: TFE-CMD-3WA-COHORT-DECOMPOSITION-WC-20260625

Pure data join — no new kernel runs on universe tickers.
SPY D_k computed from SPY bars (prerequisite for W3; SPY not in kernel cache).
Species_profiles: table/CSV not found anywhere → W2 = None for all trades.

Wave conditions (VERBATIM from command spec):
  W1 = (bar_count != null AND 1 <= bar_count <= 20)
  W2 = (species_classification == "calm")
  W3 = (SPY.D_k == 1 at trade's entry_date)

Note: 3wa_strategist.mjs line 136 also requires S_UF > 0 for W1.
Command's W1 definition omits this condition; using command definition.

Cohorts:
  W123   : W1 AND W2 AND W3
  W13    : W1 AND W3 AND NOT W2
  W3only : W3 AND NOT W1
  noW3   : NOT W3
"""
import json
import pickle
import sys
import time
from datetime import timezone, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from uf_core.uf_structural_engine import compute_uf_structural_state

CACHE_FILE  = Path("/workspaces/Tao_Financial_Engine/backups/walkforward_kernel_cache_20260624.pkl")
TRADES_FILE = Path("/workspaces/Tao_Financial_Engine/tools/walkforward_bet_20260624.csv")
OUTPUT_DIR  = Path("/workspaces/Tao_Financial_Engine/tools")
LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"

W1_BAR_MIN = 1
W1_BAR_MAX = 20
WARM_UP    = 252


def log(m):
    print(f"[3WA {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


# ── Compute SPY D_k per trading day ─────────────────────────────────────────

def compute_spy_dk(trading_days_set):
    """
    Compute SPY D_k for each trading day using the local daily_bars table.
    SPY was not included in the kernel precompute; this is computed as a
    prerequisite for W3. Uses the same kernel path as the walkforward.
    Returns {date_str: d_k} or None on failure.
    """
    log("Loading SPY bars from DB...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT bar_date, close FROM daily_bars
        WHERE UPPER(symbol) = 'SPY'
          AND bar_date >= '2020-01-01'
          AND bar_date <= '2026-06-30'
        ORDER BY bar_date
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        log("STOP: SPY bars not found in local DB")
        return None

    spy_df = pd.DataFrame(rows, columns=["bar_date","close"])
    spy_df["bar_date"] = pd.to_datetime(spy_df["bar_date"])
    spy_df = spy_df.set_index("bar_date").sort_index()
    closes = spy_df["close"]
    all_dates = closes.index.tolist()
    log(f"  SPY bars: {len(all_dates)} days ({all_dates[0].date()} → {all_dates[-1].date()})")

    spy_dk = {}
    for i, date in enumerate(all_dates):
        ds = date.strftime("%Y-%m-%d")
        if ds not in trading_days_set:
            continue
        if i < WARM_UP:
            continue
        window = closes.iloc[i - WARM_UP : i + 1]
        try:
            state = compute_uf_structural_state(window)
            spy_dk[ds] = int(state.level5.get("D_k", 0) or 0)
        except Exception:
            spy_dk[ds] = None

    log(f"  SPY D_k computed for {len(spy_dk)} trading days")
    return spy_dk


def main():
    t0 = time.time()

    # ── Load kernel cache ─────────────────────────────────────────────────────
    log("Loading kernel cache (467MB)...")
    with open(CACHE_FILE, "rb") as f:
        kernel_db = pickle.load(f)
    log(f"  {len(kernel_db)} tickers in cache")

    # ── Load trades ───────────────────────────────────────────────────────────
    log("Loading trades...")
    trades = pd.read_csv(TRADES_FILE)
    log(f"  {len(trades)} trades")

    # ── Collect all unique entry dates + trading day set ─────────────────────
    entry_dates = sorted(set(trades["entry_date"].tolist()))
    all_cache_days = set()
    for ticker_snaps in kernel_db.values():
        all_cache_days.update(ticker_snaps.keys())
    log(f"  {len(entry_dates)} unique entry dates in trades, {len(all_cache_days)} days in cache")

    # ── Gate 3 pre-check: can we get SPY D_k for all entry dates? ────────────
    # SPY not in kernel_db — compute from bars
    spy_dk_map = compute_spy_dk(all_cache_days)
    if spy_dk_map is None:
        log("STOP: cannot compute SPY D_k — SPY bars missing from local DB")
        sys.exit(1)

    missing_spy_dates = [d for d in entry_dates if d not in spy_dk_map]
    if missing_spy_dates:
        log(f"STOP: Gate 3 FAIL — SPY snapshot missing for {len(missing_spy_dates)} entry dates:")
        for d in missing_spy_dates:
            log(f"  {d}")
        sys.exit(1)
    log(f"Gate 3: PASS — SPY D_k available for all {len(entry_dates)} unique entry dates")

    # ── Species profiles: not found anywhere ─────────────────────────────────
    # production species_profiles table: relation does not exist
    # local DB species_profiles: 0 rows
    # May 29 2026 CSV: not on disk
    # → species_classification = None for all tickers → W2 = False for all
    log("Species profiles: NOT FOUND (production table missing, no CSV, local table empty)")
    log("  W2 = False for all 835 trades — reported as n_with_missing_species = 835")
    species_map = {}  # empty → all unknown

    # ── Build per-trade rows ─────────────────────────────────────────────────
    log("Building per-trade cohort rows...")
    rows_out = []
    n_missing_bar_count = 0
    n_missing_spy_dk    = 0
    n_missing_species   = 0

    for idx, tr in trades.iterrows():
        ticker      = tr["ticker"]
        entry_date  = tr["entry_date"]
        days_held   = int(tr["days_held"])
        pnl_pct     = float(tr["pnl_pct"])
        exit_reason = tr["exit_reason"]

        # bar_count from kernel cache at entry_date
        entry_snap = kernel_db.get(ticker, {}).get(entry_date)
        if entry_snap is not None:
            bc_raw = entry_snap.get("bar_count")
            bar_count = int(bc_raw) if bc_raw is not None else None
            s_uf      = float(entry_snap.get("S_UF", float("nan")))
        else:
            bar_count = None
            s_uf      = float("nan")

        # SPY D_k at entry_date (Gate 3 already verified this exists)
        spy_dk = spy_dk_map.get(entry_date)

        # Species classification (all None/unknown)
        species_class = species_map.get(ticker.upper(), None)

        # Missing-data counters
        if bar_count is None:
            n_missing_bar_count += 1
        if spy_dk is None:
            n_missing_spy_dk += 1
        if species_class is None:
            n_missing_species += 1

        # Wave conditions per command spec
        W1 = (bar_count is not None) and (W1_BAR_MIN <= bar_count <= W1_BAR_MAX)
        W2 = (species_class == "calm")
        W3 = (spy_dk == 1) if spy_dk is not None else False

        # If any input is None, wave condition evaluates to False (most conservative)
        # W1 → False if bar_count is None (already handled above)
        # W2 → False if species_class is None (already "calm" comparison fails)
        # W3 → False if spy_dk is None

        # Cohort assignment (exactly one per trade — Gate 1/2)
        if W1 and W2 and W3:
            cohort = "W123"
        elif W1 and W3 and not W2:
            cohort = "W13"
        elif W3 and not W1:
            cohort = "W3only"
        else:
            cohort = "noW3"

        rows_out.append({
            "trade_idx":          idx,
            "ticker":             ticker,
            "entry_date":         entry_date,
            "bar_count_at_entry": bar_count,
            "spy_dk_at_entry":    spy_dk,
            "species_classification": species_class,
            "W1":                 W1,
            "W2":                 W2,
            "W3":                 W3,
            "cohort":             cohort,
            "days_held":          days_held,
            "pnl_pct":            pnl_pct,
            "exit_reason":        exit_reason,
        })

    out_df = pd.DataFrame(rows_out)
    log(f"  {len(out_df)} rows built")

    # ── Integrity gates ───────────────────────────────────────────────────────
    log("Running integrity gates...")
    gate_results = {}

    # Gate 1: sum(n_trades across 4 cohorts) == 835
    total_assigned = len(out_df)
    gate1_pass = (total_assigned == len(trades))
    gate_results["gate1_total_assigned"] = {
        "pass": gate1_pass,
        "n_assigned": total_assigned, "n_expected": len(trades),
    }
    if not gate1_pass:
        log(f"STOP: Gate 1 FAIL — {total_assigned} assigned, expected {len(trades)}")
        sys.exit(1)
    log(f"Gate 1: PASS — all {total_assigned} trades assigned")

    # Gate 2: every trade_idx in {0,...,834} appears in exactly one cohort
    expected_idxs = set(range(len(trades)))
    got_idxs = set(out_df["trade_idx"].tolist())
    duplicates = out_df["trade_idx"][out_df["trade_idx"].duplicated()].tolist()
    gate2_pass = (got_idxs == expected_idxs) and (len(duplicates) == 0)
    gate_results["gate2_unique_trade_idx"] = {
        "pass": gate2_pass,
        "missing": sorted(expected_idxs - got_idxs),
        "duplicates": duplicates[:10],
    }
    if not gate2_pass:
        log(f"STOP: Gate 2 FAIL — {len(expected_idxs - got_idxs)} missing idx, {len(duplicates)} duplicates")
        sys.exit(1)
    log(f"Gate 2: PASS — all trade_idx 0..{len(trades)-1} appear exactly once")

    # Gate 3: already verified above (SPY D_k present for all entry dates)
    gate_results["gate3_spy_dk_present"] = {
        "pass": True, "missing_dates": [],
        "note": "SPY not in kernel cache; D_k computed from SPY bars in local DB",
    }

    # Gate 4: spot-check raw inputs for at least one trade per cohort
    gate4_examples = {}
    for cohort_name in ["W123", "W13", "W3only", "noW3"]:
        sample = out_df[out_df["cohort"] == cohort_name]
        if len(sample) == 0:
            gate4_examples[cohort_name] = {"n": 0, "examples": []}
            continue
        picks = sample.head(2)
        examples = []
        for _, r in picks.iterrows():
            examples.append({
                "trade_idx":   int(r["trade_idx"]),
                "ticker":      r["ticker"],
                "entry_date":  r["entry_date"],
                "bar_count_at_entry": r["bar_count_at_entry"],
                "spy_dk_at_entry":    r["spy_dk_at_entry"],
                "species_classification": r["species_classification"],
                "W1": bool(r["W1"]), "W2": bool(r["W2"]), "W3": bool(r["W3"]),
            })
        gate4_examples[cohort_name] = {"n": len(sample), "examples": examples}
    gate_results["gate4_spot_check"] = gate4_examples
    log("Gate 4: spot-check raw inputs populated (see summary JSON)")

    # ── Per-cohort aggregates ─────────────────────────────────────────────────
    cohort_aggregates = {}
    for cohort_name in ["W123", "W13", "W3only", "noW3"]:
        grp = out_df[out_df["cohort"] == cohort_name]
        n = len(grp)
        if n == 0:
            cohort_aggregates[cohort_name] = {
                "n_trades": 0, "win_rate": None, "mean_pnl_pct": None,
                "median_pnl_pct": None, "mean_days_held": None,
                "aggregate_pnl_contribution": None,
                "n_with_missing_bar_count": 0, "n_with_missing_spy_dk": 0,
                "n_with_missing_species": 0,
            }
            continue
        pnl = grp["pnl_pct"]
        cohort_aggregates[cohort_name] = {
            "n_trades":         n,
            "win_rate":         round(float((pnl > 0).mean()), 6),
            "mean_pnl_pct":     round(float(pnl.mean()), 6),
            "median_pnl_pct":   round(float(pnl.median()), 6),
            "mean_days_held":   round(float(grp["days_held"].mean()), 2),
            "aggregate_pnl_contribution": round(float(pnl.sum()), 6),
            "n_with_missing_bar_count": int((grp["bar_count_at_entry"].isna()).sum()),
            "n_with_missing_spy_dk":    int((grp["spy_dk_at_entry"].isna()).sum()),
            "n_with_missing_species":   int((grp["species_classification"].isna()).sum()),
        }

    # ── Write output ──────────────────────────────────────────────────────────
    csv_path = OUTPUT_DIR / "3wa_cohort_decomposition_20260625.csv"
    out_df.to_csv(csv_path, index=False)
    log(f"  → {csv_path} ({csv_path.stat().st_size/1e3:.0f}KB)")

    summary = {
        "command":         "TFE-CMD-3WA-COHORT-DECOMPOSITION-WC-20260625",
        "source_replay":   "060b9aa (walkforward_bet_20260624.csv)",
        "n_trades_total":  len(trades),
        "data_notes": {
            "species_profiles": {
                "status": "NOT FOUND",
                "checked": [
                    "production DB (species_profiles): relation does not exist",
                    "local tfe_validation DB: 0 rows",
                    "disk (species_profiles.csv from May 29 2026): not found",
                ],
                "consequence": "W2 = False for all 835 trades; n_with_missing_species = 835",
            },
            "spy_dk": {
                "status": "COMPUTED",
                "note": "SPY not in kernel_db (precompute only covered universe_kept). "
                        "SPY D_k computed from SPY bars in local daily_bars using same "
                        "kernel path as walkforward (WARM_UP=252).",
            },
            "W1_definition": {
                "command_spec": "bar_count != null AND 1 <= bar_count <= 20",
                "strategist_code": ("bar_count >= 1 AND bar_count <= 20 AND s_uf != null AND s_uf > 0 "
                                    "(3wa_strategist.mjs line 136)"),
                "used": "command_spec — S_UF > 0 clause omitted per command definition",
            },
        },
        "integrity_gates": gate_results,
        "cohort_aggregates": cohort_aggregates,
        "totals_check": {
            "sum_n_trades": sum(v["n_trades"] for v in cohort_aggregates.values()),
            "expected":     len(trades),
            "pass":         sum(v["n_trades"] for v in cohort_aggregates.values()) == len(trades),
        },
        "n_with_missing_bar_count": n_missing_bar_count,
        "n_with_missing_spy_dk":    n_missing_spy_dk,
        "n_with_missing_species":   n_missing_species,
        "wall_time_seconds":        round(time.time() - t0, 1),
    }

    summary_path = OUTPUT_DIR / "3wa_cohort_decomposition_20260625_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"  → {summary_path}")

    log("")
    log("=== COHORT DECOMPOSITION ===")
    for name, agg in cohort_aggregates.items():
        if agg["n_trades"] == 0:
            log(f"  {name:10s}: 0 trades")
            continue
        log(f"  {name:10s}: {agg['n_trades']:4d} trades | "
            f"WR={agg['win_rate']*100:.1f}% | "
            f"mean_pnl={agg['mean_pnl_pct']*100:.2f}% | "
            f"agg_pnl={agg['aggregate_pnl_contribution']*100:.1f}pp | "
            f"avg_hold={agg['mean_days_held']:.1f}d")
    log(f"  TOTAL:     {len(trades):4d} trades | "
        f"missing: bar_count={n_missing_bar_count} spy_dk={n_missing_spy_dk} species={n_missing_species}")
    log(f"\n  Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
