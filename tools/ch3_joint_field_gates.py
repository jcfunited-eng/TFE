"""
ch3_joint_field_gates.py — gate DEPTH into the spike, and the after-field
=========================================================================

DECLARED 2026-08-17 BEFORE THE RUN, under the UF v1.3 Joint-Field
Reconstruction constitution. Provenance: Joe — "those spikes have
structure before and after." He is right, and the first shadow pass
proved it in counts: the bar-slice quotient Q_A produced NO surviving
class, while Q_B (one bar of prior structure) produced the ONE
survivor — sustained all-scale variance build with accelerating
curvature, 20.8% grenades derive, 19.9% frozen confirm vs 16.0% base.
The information lives in the before-structure. This study measures how
DEEP it goes, per the spec's own gate law (maximal runs of unchanged
signature, dyadic durations).

HONESTY DISCLOSURE (declared): this is a REFINEMENT of the Q_B
survivor, so the 2022+ half has been seen once (aggregate counts).
To keep a genuinely frozen test, the split moves: DERIVE on events
dated <= 2023-12-31, CONFIRM FROZEN on 2024-01-01+. The 2024+ half
has never had a per-class claim judged on it. Second look at any
data is stated here, not hidden.

CUSTODY + EVENT SET: identical to ch3_joint_field_shadow.py (exact
integer ten-thousandths, uncovered spikes, grenade = any of next 5
closes >= 1.20x entry).

QUOTIENT Q_C (declared, compact — derive half is small, so classes
must be few; every discard listed):
  For each event bar t define the BUILD RUN
    B = number of consecutive bars k ending at t with
        dVS(s,k) > 0 for ALL scales s in {2,4,8,16,32}
    (B = 0 if the event bar itself is not all-rising)
  and curvature acceleration a = sgn(K_t - K_{t-1}).
  Q_C = ( dyadic class of B: 0, 1, 2-3, 4-7, 8+ ; a )
      -> at most 5 x 3 = 15 classes.
  Discards: which scale broke the run first, per-scale gate ages,
  magnitudes, N, all deeper gate history. Runs censored by series
  start count at the depth reached (disclosed, affects <1% of events
  given the loop guard).

AFTER-FIELD (descriptive ONLY — declared non-causal, no rule, never
tradable): for grenades vs winners separately, the frequency table of
the NEXT bar's structure ( sgn D_{t+1} ; sgn K_{t+1} ; all-scale
dVS sign summary at t+1: +1 if all rising, -1 if all falling, else 0 ).
This documents what the two classes' relaxation looks like — the
physics of the after — and is labelled as knowledge, not law.

PRICE-RESOLUTION STRATA (declared, per Joe 2026-08-17: the thin
points need resolution awareness — high-price/large names are stable
at fine resolution, cheap tickers are noise at the same absolute
grid; a $5 stock's cent lattice is ~10x coarser relative to itself
than a $50 stock's): dyadic entry-price bands
    P in { [5,10), [10,20), [20,40), [40,80), [80,inf) }.
No fitted knob — resolution is handled by DISCLOSURE: every table
below is also produced per stratum, and per-stratum claims obey the
same n >= 50 derive rule. Additionally a sign-noise diagnostic per
stratum: the distribution of build-depth classes (noise flips break
runs, so noisy strata should pile up at depth 0-1) and the share of
events whose event-bar signature contains any zero component.

CLAIM RULE: n >= 50 in derive; judged solely on frozen 2024+.

Usage:  python tools/ch3_joint_field_gates.py
Output: artifacts/ch4_uf/ch3_joint_field_gates.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_joint_field_gates.json")
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_joint_field_gate_events.parquet")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20
DERIVE_END = 20231231          # moved split — disclosure in docstring
SCALES = (2, 4, 8, 16, 32)
MIN_CLASS_N = 50
MAX_DEPTH = 16                 # bars scanned back for the build run


def sgn(z: int) -> int:
    return (z > 0) - (z < 0)


def depth_class(b: int) -> str:
    if b == 0:
        return "0"
    if b == 1:
        return "1"
    if b <= 3:
        return "2-3"
    if b <= 7:
        return "4-7"
    return "8+"


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    guard = max(SCALES) + 2 + MAX_DEPTH
    for sym, s_df in df.groupby("Symbol", sort=False):
        s_df = s_df.sort_values("Date")
        cf = s_df["Close"].to_numpy(dtype=float)
        vf = s_df["Volume"].to_numpy(dtype=float)
        d = s_df["day"].to_numpy()
        n = len(cf)
        if n < guard + 8:
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

        def all_rising(k):
            return all(VS(s, k) - VS(s, k - 1) > 0 for s in SCALES)

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
            b = 0
            k = t
            while k > t - MAX_DEPTH and k > max(SCALES) + 1 and all_rising(k):
                b += 1
                k -= 1
            K_t = int(x[t] - 2 * x[t - 1] + x[t - 2])
            K_p = int(x[t - 1] - 2 * x[t - 2] + x[t - 3])
            qc = f"{depth_class(b)};a{'+0-'[1 - sgn(K_t - K_p)]}"
            # after-field, descriptive only (t+1 exists: loop stops at n-HOLD)
            D_n = sgn(int(x[t + 1] - x[t]))
            K_n = sgn(int(x[t + 1] - 2 * x[t] + x[t - 1]))
            dv = [sgn(VS(s, t + 1) - VS(s, t)) for s in SCALES]
            allv = 1 if all(v > 0 for v in dv) else (-1 if all(v < 0 for v in dv)
                                                     else 0)
            after = f"D{'+0-'[1 - D_n]}K{'+0-'[1 - K_n]}V{'+0-'[1 - allv]}"
            p = cf[t]
            band = ("5-10" if p < 10 else "10-20" if p < 20 else
                    "20-40" if p < 40 else "40-80" if p < 80 else "80+")
            zero0 = int(any(sgn(VS(s, t) - VS(s, t - 1)) == 0
                            for s in SCALES))
            rows.append({
                "sym": sym, "date": int(d[t]), "QC": qc, "after": after,
                "band": band, "zero0": zero0,
                "grenade": bool(np.any(cf[t + 1: t + HOLD + 1]
                                       >= GRENADE_X * cf[t])),
            })

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)   # every stone keeps its full record
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)})")

    def freq_table():
        base_d = float(derive["grenade"].mean())
        base_c = float(confirm["grenade"].mean())
        claims, sparse_n = [], 0
        c_counts = {k: (int(g["grenade"].sum()), len(g))
                    for k, g in confirm.groupby("QC")}
        for cls, g in derive.groupby("QC"):
            nd = len(g)
            if nd < MIN_CLASS_N:
                sparse_n += nd
                continue
            gd = int(g["grenade"].sum())
            gc, nc = c_counts.get(cls, (0, 0))
            claims.append({
                "structure": cls,
                "derive": f"{gd}/{nd} = {100 * gd / nd:.1f}%",
                "confirm_frozen_2024plus":
                    f"{gc}/{nc} = {100 * gc / nc:.1f}%" if nc else "0/0",
                "derive_vs_base": round(100 * gd / nd - 100 * base_d, 1),
                "confirm_vs_base": round(100 * gc / nc - 100 * base_c, 1)
                if nc else None,
            })
        claims.sort(key=lambda r: r["structure"])
        return {"base_derive": f"{int(derive['grenade'].sum())}/{len(derive)}"
                               f" = {100 * base_d:.1f}%",
                "base_confirm": f"{int(confirm['grenade'].sum())}/{len(confirm)}"
                                f" = {100 * base_c:.1f}%",
                "classes": claims, "sparse_events_no_claim": sparse_n}

    def after_table(sub):
        out = {}
        for cls, g in sub.groupby("after"):
            if len(g) >= 30:
                out[cls] = int(len(g))
        return out

    def stratum_tables():
        out = {}
        for band in ["5-10", "10-20", "20-40", "40-80", "80+"]:
            g = ev[ev["band"] == band]
            if len(g) == 0:
                continue
            gd = g[g["date"] <= DERIVE_END]
            gc = g[g["date"] > DERIVE_END]
            depth = {str(cls): int(nn) for cls, nn in
                     g["QC"].str.split(";").str[0].value_counts().items()}
            claims = []
            cc = {k: (int(x["grenade"].sum()), len(x))
                  for k, x in gc.groupby("QC")}
            for cls, gg in gd.groupby("QC"):
                if len(gg) < MIN_CLASS_N:
                    continue
                gsum = int(gg["grenade"].sum())
                c1, c2 = cc.get(cls, (0, 0))
                claims.append({
                    "structure": cls,
                    "derive": f"{gsum}/{len(gg)}"
                              f" = {100 * gsum / len(gg):.1f}%",
                    "confirm_frozen_2024plus":
                        f"{c1}/{c2} = {100 * c1 / c2:.1f}%" if c2 else "0/0"})
            out[band] = {
                "derive_base": f"{int(gd['grenade'].sum())}/{len(gd)}",
                "confirm_base": f"{int(gc['grenade'].sum())}/{len(gc)}",
                "zero_component_events": f"{int(g['zero0'].sum())}/{len(g)}",
                "build_depth_distribution": depth,
                "claims": claims,
            }
        return out

    g_all = ev[ev["grenade"]]
    w_all = ev[~ev["grenade"]]
    result = {
        "declared": "Q_C depth quotient + moved split (derive<=2023, frozen "
                    "2024+) + after-field as descriptive-only, all declared "
                    "in docstring before the run; second look at 2022-2023 "
                    "disclosed there",
        "Q_C_build_depth": freq_table(),
        "per_price_stratum": stratum_tables(),
        "after_field_descriptive_NON_CAUSAL": {
            "note": "next-bar structure by outcome class; knowledge not law",
            "grenades_n": int(len(g_all)),
            "winners_n": int(len(w_all)),
            "grenades": after_table(g_all),
            "winners": after_table(w_all),
        },
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
