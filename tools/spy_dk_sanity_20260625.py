#!/usr/bin/env python3
"""
tools/spy_dk_sanity_20260625.py
Command: TFE-CMD-SPY-DK-SANITY-WC-20260625

Validates the SPY kernel run used in 3wa_cohort_decomposition_20260625.
Calls L0→L1→L2→L3→L4 directly to expose per-day intermediates.

Output columns: date, spy_close, spy_R_k, spy_URF_k, spy_Hyst_k,
                spy_g_k, spy_D_k, spy_M_k, spy_B_k, spy_U_star_k

R_k    : normalized resonance of last gate in 252-bar window (L3)
URF_k  : gated resonance = g_k × R_k (L3 output to L4)
Hyst_k : hysteresis flag = 1 iff |R_k - R_{k-1}| > h_max (L3)
g_k    : gate open = 1 iff U_k ≤ U_max AND IAS_k==0 AND Hyst_k==0 (L3)
D_k    : directional signal ∈ {-1, 0, +1} (L4, last gate)
M_k    : curvature = R_k - 2R_{k-1} + R_{k-2} (L4, last gate)
B_k    : breathing state (L4, last gate)
U_star_k: adjusted uncertainty (L4, last gate)
"""
import json
import sys
import time
from datetime import timezone, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf
from uf_core.config import KERNEL_THRESHOLDS

LOCAL_DSN   = "host=/var/run/postgresql dbname=tfe_validation user=postgres"
OUTPUT_DIR  = Path("/workspaces/Tao_Financial_Engine/tools")
REPLAY_START = "2021-04-01"
REPLAY_END   = "2026-03-24"
WARM_UP      = 252


def log(m):
    print(f"[SPY {datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def echo_constants():
    """Return the kernel constants from config.py verbatim."""
    return {
        "epsilon_D":  float(KERNEL_THRESHOLDS.epsilon_D),
        "h_max":      float(KERNEL_THRESHOLDS.h_max),
        "U_max":      float(KERNEL_THRESHOLDS.U_max),
        "breath_xi":  float(KERNEL_THRESHOLDS.breath_xi),
        "breath_chi": float(KERNEL_THRESHOLDS.breath_chi),
        "source":     "uf_core/config.py  KERNEL_THRESHOLDS (no override)",
    }


def compute_spy_snapshot(closes_window: pd.Series):
    """
    Run L0→L4 on the given close-price window.
    Returns dict with R_k, URF_k, Hyst_k, g_k, D_k, M_k, B_k, U_star_k
    for the LAST gate, or None values if pipeline yields no gates.
    """
    closes_window = closes_window.dropna().astype(float)
    if len(closes_window) < 10:
        return {k: None for k in ["R_k","URF_k","Hyst_k","g_k","D_k","M_k","B_k","U_star_k"]}

    df = pd.DataFrame({"Close": closes_window}, index=closes_window.index)

    sev_list        = compute_sev_series(df, field_col="Close")
    gates           = segment_gates(sev_list)
    interpretations = interpret_gates(sev_list, gates)
    resonance_res   = compute_resonance(interpretations)
    decision_states = compute_directional_signal(resonance_res)
    dsf_list        = compute_dsf(decision_states)

    if not resonance_res or not dsf_list:
        return {k: None for k in ["R_k","URF_k","Hyst_k","g_k","D_k","M_k","B_k","U_star_k"]}

    last_r = resonance_res[-1]
    last_d = dsf_list[-1]

    return {
        "R_k":     float(last_r.R_k),
        "URF_k":   float(last_r.URF_k),
        "Hyst_k":  int(last_r.Hyst_k),
        "g_k":     int(last_r.g_k),
        "D_k":     float(last_d.D_k),
        "M_k":     float(last_d.M_k),
        "B_k":     float(last_d.B_k),
        "U_star_k":float(last_d.U_star_k),
    }


def main():
    t0 = time.time()

    # ── Load SPY bars ─────────────────────────────────────────────────────────
    log("Loading SPY bars from local DB...")
    conn = psycopg2.connect(LOCAL_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT bar_date, close FROM daily_bars
        WHERE UPPER(symbol) = 'SPY'
          AND bar_date >= '2020-01-01' AND bar_date <= '2026-06-30'
        ORDER BY bar_date
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        log("STOP: SPY bars not in local DB")
        sys.exit(1)

    spy_df = pd.DataFrame(rows, columns=["bar_date", "close"])
    spy_df["bar_date"] = pd.to_datetime(spy_df["bar_date"])
    spy_df = spy_df.set_index("bar_date").sort_index()
    closes = spy_df["close"]
    all_dates = closes.index.tolist()
    log(f"  {len(all_dates)} SPY bars ({all_dates[0].date()} → {all_dates[-1].date()})")

    # ── Compute per-day snapshots for replay window ───────────────────────────
    log(f"Computing SPY kernel snapshots for {REPLAY_START} → {REPLAY_END}...")
    output_rows = []
    n_warmup = 0

    for i, date in enumerate(all_dates):
        ds = date.strftime("%Y-%m-%d")
        if ds < REPLAY_START or ds > REPLAY_END:
            continue
        if i < WARM_UP:
            n_warmup += 1
            continue

        window = closes.iloc[i - WARM_UP : i + 1]
        snap = compute_spy_snapshot(window)

        output_rows.append({
            "date":       ds,
            "spy_close":  float(closes.iloc[i]),
            "spy_R_k":    snap["R_k"],
            "spy_URF_k":  snap["URF_k"],
            "spy_Hyst_k": snap["Hyst_k"],
            "spy_g_k":    snap["g_k"],
            "spy_D_k":    snap["D_k"],
            "spy_M_k":    snap["M_k"],
            "spy_B_k":    snap["B_k"],
            "spy_U_star_k": snap["U_star_k"],
        })

    log(f"  {len(output_rows)} days computed, {n_warmup} days skipped (warmup period < {WARM_UP} bars)")

    # ── Write CSV ─────────────────────────────────────────────────────────────
    out_df = pd.DataFrame(output_rows)
    csv_path = OUTPUT_DIR / "spy_dk_sanity_20260625.csv"
    out_df.to_csv(csv_path, index=False)
    log(f"  → {csv_path} ({csv_path.stat().st_size/1e3:.0f}KB)")

    # ── Summary stats ─────────────────────────────────────────────────────────
    valid = out_df.dropna(subset=["spy_D_k"])

    def count_vals(series, vals):
        return {str(v): int((series == v).sum()) for v in vals}

    dk_dist  = count_vals(valid["spy_D_k"],    [-1.0, 0.0, 1.0])
    gk_dist  = count_vals(valid["spy_g_k"],    [0, 1])
    hk_dist  = count_vals(valid["spy_Hyst_k"], [0, 1])

    dk_plus_dates = sorted(
        out_df.loc[out_df["spy_D_k"] == 1.0, "date"].tolist()
    )

    n_total     = len(out_df)
    n_valid     = len(valid)
    n_null      = n_total - n_valid
    pct_gk0     = int(gk_dist.get("0", 0)) / max(n_valid, 1)
    pct_dk0     = int(dk_dist.get("0.0", 0)) / max(n_valid, 1)

    summary = {
        "command":          "TFE-CMD-SPY-DK-SANITY-WC-20260625",
        "source_job":       "c44b9f6 3wa_cohort_decomp_20260625.py",
        "replay_window":    f"{REPLAY_START} → {REPLAY_END}",
        "n_days":           n_total,
        "n_valid":          n_valid,
        "n_null_snapshots": n_null,
        "n_days_warmup_used_for_spy": WARM_UP,
        "kernel_constants_used": echo_constants(),
        "dk_distribution": dk_dist,
        "gk_distribution": gk_dist,
        "hyst_distribution": hk_dist,
        "dk_plus_one_dates": dk_plus_dates,
        "n_dk_plus_one":    len(dk_plus_dates),
        "flags": {
            "gk0_majority": pct_gk0 > 0.50,
            "gk0_pct":      round(pct_gk0, 4),
            "dk_dead_zone": pct_dk0 > 0.70,
            "dk0_pct":      round(pct_dk0, 4),
        },
        "wall_time_seconds": round(time.time() - t0, 1),
    }

    summary_path = OUTPUT_DIR / "spy_dk_sanity_20260625_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log(f"  → {summary_path}")

    log("")
    log("=== SPY D_k SANITY ===")
    log(f"  n_days:        {n_total}")
    log(f"  D_k +1:        {dk_dist.get('1.0',0)}  ({100*int(dk_dist.get('1.0',0))/max(n_valid,1):.1f}%)")
    log(f"  D_k  0:        {dk_dist.get('0.0',0)}  ({100*pct_dk0:.1f}%)  dead-zone flag: {pct_dk0>0.70}")
    log(f"  D_k -1:        {dk_dist.get('-1.0',0)}")
    log(f"  g_k  0:        {gk_dist.get('0',0)}  ({100*pct_gk0:.1f}%)  pathology flag: {pct_gk0>0.50}")
    log(f"  g_k  1:        {gk_dist.get('1',0)}")
    log(f"  Hyst open:     {hk_dist.get('1',0)}")
    log(f"  D_k=+1 dates:  {dk_plus_dates[:10]}{'...' if len(dk_plus_dates)>10 else ''}")
    log(f"  Done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
