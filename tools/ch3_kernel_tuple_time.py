"""
ch3_kernel_tuple_time.py — the kernel tuple, dimensionalized across time
========================================================================

DECLARED 2026-08-17 BEFORE THE RUN. Joe's directive, verbatim intent:
ticker data is time series -> it flows through the kernel (full L0-L4,
replay_symbol_v2) -> THE TUPLE is what gets evaluated -> AND
DIMENSIONALIZED ACROSS TIME. So the evaluated object here is the
kernel's complete state tuple as a TRAJECTORY into each event, and
comparison is frequencies over exact discrete trajectory classes.
All stocks, all time (the whole store through HERD_END).

TUPLE COMPONENTS USED (kernel-native only; nothing invented):
  discrete in the tuple itself:  event_type, regime, sgn(D_k), Rev_k
  continuous fields enter ONLY through the sign of their own change
  across time (exact discrete facts of the trajectory, no fitted
  thresholds):  S_UF, R_res, URF
DEGENERACIES DISCLOSED (measured on the full event table first):
  action == HOLD and chi_n == 1 on every event; B_k < 0 always;
  U_star_k, F_n, Q_20, x_*, rho_n, s_n are continuous and are NOT
  used in this pass (their change-signs are a lawful future quotient;
  keeping this pass compact because the derive half has only ~1.1k
  events and claims need n >= 50).

TWO TRAJECTORY QUOTIENTS, declared now, none added after labels:
  T1 (one step into the event):
     ( sgn dS_UF(t-1,t), sgn dR_res(t-1,t), sgn dURF(t-1,t),
       sgn D_k(t), Rev_k(t) )
  T2 (the three-bar approach, net):
     ( sgn dS_UF(t-3,t), sgn dR_res(t-3,t), sgn dURF(t-3,t),
       event_type(t-1), event_type(t) )
EVENT SET / LABEL / SPLIT: identical to ch3_kernel_full_chain.py
(uncovered spikes, grenade = any next-5 close >= 1.20x, derive
<= 2021-12-31, confirm frozen 2022+). Claims need n >= 50 in derive
and are judged solely on confirm. Universe imbalance across the
split is disclosed (coverage triples). Sparse classes stay sparse.

Usage:  python tools/ch3_kernel_tuple_time.py
Output: artifacts/ch4_uf/ch3_kernel_tuple_time.json
        artifacts/ch4_uf/ch3_kernel_tuple_events.parquet
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_kernel_tuple_time.json")
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_kernel_tuple_events.parquet")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20
DERIVE_END = 20211231
WARMUP = 60
MIN_CLASS_N = 50

ET_CODE = {"resonance_reversal": "R", "gate_close": "G",
           "regime_change": "C", "negative_space_release": "N"}


def sgn(z: float) -> str:
    return "+" if z > 0 else ("-" if z < 0 else "0")


def main():
    t0 = time.time()
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    n_done = skipped_replay = 0
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        dates = s["Date"].to_numpy()
        if len(c) < WARMUP + HOLD + 5:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        evs = []
        for t in range(WARMUP + 3, len(c) - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            if (sym, int(d[t])) in herd_keys:
                continue
            evs.append(t)
        if not evs:
            continue
        try:
            states = replay_symbol_v2(dates, c, v, warmup=WARMUP)
        except Exception as err:  # noqa: BLE001
            skipped_replay += len(evs)
            print(f"  {sym}: replay failed ({type(err).__name__}) — "
                  f"{len(evs)} events skipped")
            continue
        for t in evs:
            w = [states[k] for k in (t - 3, t - 2, t - 1, t)]
            if any(x is None for x in w):
                continue
            s3, s2, s1, s0 = w
            t1 = (sgn(s0.S_UF - s1.S_UF) + sgn(s0.R_res - s1.R_res)
                  + sgn(s0.URF - s1.URF) + sgn(s0.D_k)
                  + str(int(s0.Rev_k > 0)))
            t2 = (sgn(s0.S_UF - s3.S_UF) + sgn(s0.R_res - s3.R_res)
                  + sgn(s0.URF - s3.URF)
                  + ET_CODE.get(str(s1.event_type), "?")
                  + ET_CODE.get(str(s0.event_type), "?"))
            rows.append({
                "sym": sym, "date": int(d[t]), "T1": t1, "T2": t2,
                "regime": str(s0.regime),
                "grenade": bool(np.any(c[t + 1: t + HOLD + 1]
                                       >= GRENADE_X * c[t])),
            })
        n_done += 1
        if n_done % 500 == 0:
            print(f"  [{n_done}] symbols, {len(rows)} events, "
                  f"{time.time() - t0:.0f}s", flush=True)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)}), "
          f"replay-skipped: {skipped_replay}")

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
                "trajectory": cls,
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
                "n_distinct_trajectories_derive": int(d_groups.ngroups)}

    result = {
        "declared": "kernel tuple trajectories (T1 one-step, T2 three-bar "
                    "approach) declared in docstring before the run; kernel-"
                    "native components only; continuous fields via change-"
                    "sign across time only; degeneracies and universe "
                    "imbalance disclosed; replay-skipped events counted",
        "replay_skipped_events": skipped_replay,
        "T1_one_step_into_event": freq_table("T1"),
        "T2_three_bar_approach": freq_table("T2"),
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:6000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
