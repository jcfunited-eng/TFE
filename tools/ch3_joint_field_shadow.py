"""
ch3_joint_field_shadow.py — the joint-field shadow, per THE SPEC
================================================================

DECLARED 2026-08-18 BEFORE THE RUN, under the UF v1.3 Joint-Field
Reconstruction constitution (Joe: "that is the spec... central to the
entire purpose of this work"). Skill: uf-joint-field-spec. Shadow
discipline: runs BESIDE the canonical chain run (ch3_kernel_full_chain
.py, in progress), both filed, no automatic winner, routes nothing
into production.

FINANCIAL PROJECTION (declared): single-vertex field per stock.
Custody: prices as exact integers in ten-thousandths of a dollar
(the books' own fill precision); volumes as exact integers. ALL facts
below are exact integer arithmetic — no floats, no logs, no fitted
constants, no thresholds.

FIELD FACTS at bar k (x = price int, s in dyadic scales {2,4,8,16,32}):
  D_k       = x_k - x_{k-1}                      displacement (int)
  K_k       = D_k - D_{k-1}                      curvature (int)
  VS(s,k)   = s*sum(x^2 over I_{k,s}) - (sum x over I_{k,s})^2
              where I_{k,s} = the s bars ending at k    (int; equals
              s^2 * variance — sign-exact for equal-length windows)
  dVS(s,k)  = VS(s,k) - VS(s,k-1)                variance motion (int)
  N_k       = 1 iff the last 4 closes are identical    negative space

SIGNATURE at bar k (thresholdless, exact):
  SIG_k = ( sgn K_k ; ( sgn dVS(s,k) for each s ) ; N_k )
  (sgn D_k is omitted from the event structure because the event
  filter fixes it: every event bar has D_k > 0 by construction —
  disclosed per the constitution's quotient-loss rule.)

TWO QUOTIENTS, declared now, no third after labels:
  Q_A  the event-bar signature SIG_k alone.
       Discards: all magnitudes, gate durations, TVR components,
       prior structure. <= 2*3^6 = 1458 classes.
  Q_B  SIG_k together with the componentwise sign of structural
       displacement from the previous bar: ( sgn(K_k - K_{k-1}) ;
       ( sgn(dVS(s,k) - dVS(s,k-1)) for each s ) ) — the L4 D-field
       restricted to the event bar. Discards: same as Q_A plus all
       deeper history.

EVENT SET (domain law, L5, outside the kernel — declared): the fade's
uncovered spikes (day gain >= +8%, volume >= 3x trailing-20 mean,
close >= $5, no herd row). LABEL (revealed only after structures are
built): grenade = any of the next 5 closes >= 1.20 x entry.

PROCEDURE: structures computed label-blind for all events; split
derive (date <= 2021-12-31) / confirm (later); labels revealed;
per-class grenade frequencies with counts in BOTH halves; a derive
class makes a claim only with n >= 50 there, and the claim is judged
solely by its frozen confirm-half frequency. Sparse classes are
reported as sparse, never folded into a scalar.

Usage:  python tools/ch3_joint_field_shadow.py
Output: artifacts/ch4_uf/ch3_joint_field_shadow.json
        artifacts/ch4_uf/ch3_joint_field_events.parquet (raw table)
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_joint_field_shadow.json")
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_joint_field_events.parquet")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20
DERIVE_END = 20211231
SCALES = (2, 4, 8, 16, 32)
MIN_CLASS_N = 50


def sgn(z: int) -> int:
    return (z > 0) - (z < 0)


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    for sym, s_df in df.groupby("Symbol", sort=False):
        s_df = s_df.sort_values("Date")
        cf = s_df["Close"].to_numpy(dtype=float)
        vf = s_df["Volume"].to_numpy(dtype=float)
        d = s_df["day"].to_numpy()
        n = len(cf)
        if n < max(SCALES) + 8:
            continue
        # exact integer custody: ten-thousandths of a dollar
        x = np.round(cf * 10000).astype(np.int64)
        sv = np.concatenate(([0.0], np.cumsum(vf)))
        # integer prefix sums for exact windowed variance comparison
        px1 = np.concatenate(([0], np.cumsum(x, dtype=object)))
        px2 = np.concatenate(([0], np.cumsum(x.astype(object) ** 2)))

        def VS(s, k):
            """s * sum(x^2) - (sum x)^2 over the s bars ending at k. Exact."""
            a, b = k - s + 1, k + 1
            sx = px1[b] - px1[a]
            sxx = px2[b] - px2[a]
            return s * sxx - sx * sx

        for t in range(max(SCALES) + 2, n - HOLD):
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
            D_t = int(x[t] - x[t - 1])
            D_p = int(x[t - 1] - x[t - 2])
            D_pp = int(x[t - 2] - x[t - 3])
            K_t = D_t - D_p
            K_p = D_p - D_pp
            N_t = int(x[t] == x[t - 1] == x[t - 2] == x[t - 3])
            dvs_t, dvs_p = [], []
            for s in SCALES:
                dvs_t.append(sgn(VS(s, t) - VS(s, t - 1)))
                dvs_p.append(sgn(VS(s, t - 1) - VS(s, t - 2)))
            qa = (sgn(K_t),) + tuple(dvs_t) + (N_t,)
            qb = qa + (sgn(K_t - K_p),) + tuple(
                sgn(a - b) for a, b in zip(dvs_t, dvs_p))
            rows.append({
                "sym": sym, "date": int(d[t]),
                "QA": "".join("+0-"[1 - v] for v in qa),
                "QB": "".join("+0-"[1 - v] for v in qb),
                "grenade": bool(np.any(cf[t + 1: t + HOLD + 1]
                                       >= GRENADE_X * cf[t])),
            })

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)})")

    def freq_table(col):
        base_d = float(derive["grenade"].mean())
        base_c = float(confirm["grenade"].mean())
        claims, sparse_n = [], 0
        d_groups = derive.groupby(col)
        c_counts = {k: (int(g["grenade"].sum()), len(g))
                    for k, g in confirm.groupby(col)}
        for cls, g in d_groups:
            nd = len(g)
            if nd < MIN_CLASS_N:
                sparse_n += nd
                continue
            gd = int(g["grenade"].sum())
            gc, nc = c_counts.get(cls, (0, 0))
            claims.append({
                "structure": cls,
                "derive": f"{gd}/{nd} = {100 * gd / nd:.1f}%",
                "confirm": f"{gc}/{nc} = {100 * gc / nc:.1f}%" if nc else "0/0",
                "derive_vs_base": round(100 * gd / nd - 100 * base_d, 1),
                "confirm_vs_base": round(100 * gc / nc - 100 * base_c, 1)
                if nc else None,
            })
        claims.sort(key=lambda r: -abs(r["derive_vs_base"]))
        return {"base_derive": f"{int(derive['grenade'].sum())}/{len(derive)}"
                               f" = {100 * base_d:.1f}%",
                "base_confirm": f"{int(confirm['grenade'].sum())}/{len(confirm)}"
                                f" = {100 * base_c:.1f}%",
                "classes_with_claims": claims,
                "sparse_events_no_claim": sparse_n,
                "n_distinct_structures_derive": int(d_groups.ngroups)}

    result = {
        "declared": "quotients Q_A/Q_B, scales, custody, event set, labels, "
                    "and the n>=50 claim rule all declared in the docstring "
                    "before any label was revealed; exact integer arithmetic "
                    "throughout; shadow beside canonical, no auto-winner",
        "Q_A_event_signature": freq_table("QA"),
        "Q_B_signature_plus_displacement": freq_table("QB"),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:4000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
