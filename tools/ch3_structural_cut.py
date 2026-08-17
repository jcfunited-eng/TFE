"""
ch3_structural_cut.py — can the day-after field structure cut grenades early?
=============================================================================

DECLARED 2026-08-17 BEFORE THE RUN, under the joint-field constitution.

PROVENANCE: the gate-depth study's descriptive after-field table
(ch3_joint_field_gates.json) shows the next-bar structure D+K+V+
(price still climbing, curvature bending up, variance building at all
five scales) occurs in 511/2001 grenades vs 134/10997 winners. As an
ENTRY predictor that is partly mechanical (a grenade must rise), but
CH3's exits are close-of-bar laws already — so the honest question is:
does adding a STRUCTURAL CUT at the t+1 close, when t+1 shows D+K+V+,
improve the book against the current law? Measured on the decade
BEFORE any engine change; the engine changes only if this survives
its frozen half.

LAWS COMPARED per uncovered event (short at c[t], path c[t+1..t+5]):
  LAW A (current v3): exit at first close <= 0.95*entry (HARVEST) or
        >= 1.20*entry (ANOMALY-CUT); else the 5th close (TIME).
  LAW B: at t+1 close, if the t+1 structure is D+K+V+ (exact integer
        sign facts: D=x[t+1]-x[t] > 0; K=x[t+1]-2x[t]+x[t-1] > 0;
        VS(s,t+1)-VS(s,t) > 0 for ALL s in {2,4,8,16,32}) -> exit at
        c[t+1] (STRUCT-CUT). Otherwise LAW A from t+1 onward.
  All structure facts at t+1 use only closes <= t+1: causal for a
  close-of-bar exit, same convention as the engine's existing laws.

REPORTING (counts and money, no naked scalars): per law and half —
  outcome counts (HARVEST / ANOMALY / STRUCT / TIME), summed short
  return per 100 events (additive money, not an opinion), win/loss
  counts, worst single event, and the false-cut ledger for LAW B
  (winners cut at t+1: their exit return vs what LAW A got them).
  Split: derive <= 2023-12-31, confirm frozen 2024+ (same split as
  the gates round, disclosure carried over).

Usage:  python tools/ch3_structural_cut.py
Output: artifacts/ch4_uf/ch3_structural_cut.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_structural_cut.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
HARVEST_X, STOP_X = 0.95, 1.20
DERIVE_END = 20231231
SCALES = (2, 4, 8, 16, 32)


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    guard = max(SCALES) + 4
    for sym, s_df in df.groupby("Symbol", sort=False):
        s_df = s_df.sort_values("Date")
        cf = s_df["Close"].to_numpy(dtype=float)
        vf = s_df["Volume"].to_numpy(dtype=float)
        d = s_df["day"].to_numpy()
        n = len(cf)
        if n < guard + HOLD + 4:
            continue
        x = np.round(cf * 10000).astype(np.int64)
        sv = np.concatenate(([0.0], np.cumsum(vf)))
        xo = x.astype(object)
        px1 = np.concatenate(([0], np.cumsum(xo)))
        px2 = np.concatenate(([0], np.cumsum(xo * xo)))

        def VS(s, k):
            a, b = k - s + 1, k + 1
            sx = px1[b] - px1[a]
            sxx = px2[b] - px2[a]
            return s * sxx - sx * sx

        for t in range(guard, n - HOLD):
            if d[t] > HERD_END:
                break
            if cf[t] < PRICE_FLOOR or cf[t - 1] <= 0:
                continue
            if 100 * (cf[t] / cf[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or vf[t] < VOL_MULT * va:
                continue
            if (sym, int(d[t])) in herd_keys:
                continue
            entry = cf[t]

            def law_a():
                for k in range(t + 1, t + HOLD + 1):
                    if cf[k] <= HARVEST_X * entry:
                        return cf[k], "HARVEST"
                    if cf[k] >= STOP_X * entry:
                        return cf[k], "ANOMALY"
                return cf[t + HOLD], "TIME"

            exit_a, st_a = law_a()
            dkv = (x[t + 1] - x[t] > 0
                   and x[t + 1] - 2 * x[t] + x[t - 1] > 0
                   and all(VS(s, t + 1) - VS(s, t) > 0 for s in SCALES))
            if dkv and cf[t + 1] < STOP_X * entry \
                    and cf[t + 1] > HARVEST_X * entry:
                exit_b, st_b = cf[t + 1], "STRUCT"
            else:
                exit_b, st_b = exit_a, st_a
            ra = 100 * (entry - exit_a) / entry
            rb = 100 * (entry - exit_b) / entry
            rows.append({"sym": sym, "date": int(d[t]),
                         "ra": ra, "rb": rb, "sa": st_a, "sb": st_b})

    ev = pd.DataFrame(rows)
    print(f"events: {len(ev)}")

    def ledger(sub):
        out = {}
        for tag, rcol, scol in (("LAW_A_current", "ra", "sa"),
                                ("LAW_B_struct_cut", "rb", "sb")):
            g = sub
            out[tag] = {
                "outcome_counts": {str(k): int(v) for k, v in
                                   g[scol].value_counts().items()},
                "sum_return_per_100_events":
                    round(100 * float(g[rcol].sum()) / len(g), 1) if len(g)
                    else None,
                "wins_losses": f"{int((g[rcol] > 0).sum())}W/"
                               f"{int((g[rcol] < 0).sum())}L of {len(g)}",
                "worst_event_pct": round(float(g[rcol].min()), 1) if len(g)
                else None,
            }
        # false-cut ledger: LAW B cut it, LAW A ended better for the short
        fc = sub[(sub["sb"] == "STRUCT") & (sub["ra"] > sub["rb"])]
        tc = sub[(sub["sb"] == "STRUCT") & (sub["ra"] <= sub["rb"])]
        out["struct_cuts"] = {
            "total": int((sub["sb"] == "STRUCT").sum()),
            "good_cuts_ra_worse_or_equal": int(len(tc)),
            "false_cuts_ra_was_better": int(len(fc)),
            "false_cut_cost_per_100_events":
                round(100 * float((fc["ra"] - fc["rb"]).sum()) / len(sub), 1)
                if len(sub) else None,
            "good_cut_save_per_100_events":
                round(100 * float((tc["rb"] - tc["ra"]).sum()) / len(sub), 1)
                if len(sub) else None,
        }
        return out

    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    result = {
        "declared": "laws, structure test, split, and reporting declared in "
                    "docstring before the run; close-of-bar convention same "
                    "as the live engine's existing exit laws",
        "derive_le_2023": ledger(derive),
        "CONFIRM_frozen_2024_plus": ledger(confirm),
        "by_year_sum_per_100": {
            str(y): {
                "n": int(len(g)),
                "LAW_A": round(100 * float(g["ra"].sum()) / len(g), 1),
                "LAW_B": round(100 * float(g["rb"].sum()) / len(g), 1),
            } for y, g in ev.groupby(ev["date"] // 10000)},
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
