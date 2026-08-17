"""
ch3_kernel_full_chain.py — the WHOLE kernel, L0 through L4, on every
====================================================================
uncovered spike. No summaries. The raw state table is kept on disk.

DECLARED 2026-08-18 BEFORE THE RUN. Provenance: Joe caught the prior
pass ("SO YOU LIED") using only L0 reduced to scalars while claiming
the kernel had read the trades. This run uses replay_symbol_v2 — the
full causal chain: gates, contrast, structure S, resonance R_res,
URF, hysteresis, D_k, B_k, U*, S_UF, F_n, chi, regime classes — and
records the kernel's COMPLETE DayState at every event bar, per event,
to a parquet nothing is allowed to flatten.

EVENT / GRENADE definitions: identical to ch3_kernel_eyes.py (filed).
PROCEDURE: identical two-stage honesty — class comparison and any
derived single rule come from events dated <= 2021-12-31 ONLY; the
frozen rule is then tested on 2022+. Ships only if it survives the
future it never saw.

Usage:  python tools/ch3_kernel_full_chain.py
Output: artifacts/ch4_uf/ch3_kernel_full_events.parquet  (raw table)
        artifacts/ch4_uf/ch3_kernel_full_chain.json      (comparison)
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
OUT_TABLE = os.path.join(ROOT, "artifacts", "ch4_uf",
                         "ch3_kernel_full_events.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_kernel_full_chain.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X = 1.20
DERIVE_END = 20211231
WARMUP = 60

NUM_FIELDS = ["S_UF", "R_res", "URF", "F_n", "chi_n", "Q_20",
              "x_f", "x_m", "x_s", "rho_n", "s_n", "B_k", "U_star_k",
              "D_k", "Rev_k", "gate_count"]
CAT_FIELDS = ["regime", "action", "event_type"]


def main():
    t0 = time.time()
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    n_sym = n_done = 0
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
        for t in range(WARMUP, len(c) - HOLD):
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
        n_sym += 1
        try:
            states = replay_symbol_v2(dates, c, v, warmup=WARMUP)
        except Exception as err:  # noqa: BLE001 — one bad series must not kill the run
            print(f"  {sym}: replay failed ({type(err).__name__}) — skipped")
            continue
        for t in evs:
            st = states[t]
            if st is None:
                continue
            row = {"sym": sym, "date": int(d[t]),
                   "grenade": bool(np.any(c[t + 1: t + HOLD + 1]
                                          >= GRENADE_X * c[t]))}
            for f in NUM_FIELDS:
                row[f] = float(getattr(st, f))
            for f in CAT_FIELDS:
                row[f] = str(getattr(st, f))
            rows.append(row)
        n_done += 1
        if n_done % 100 == 0:
            print(f"  [{n_done}] symbols chained, {len(rows)} events, "
                  f"{time.time() - t0:.0f}s", flush=True)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT_TABLE, index=False)
    print(f"raw table filed: {len(ev)} events x {len(ev.columns)} cols "
          f"-> {OUT_TABLE} ({time.time() - t0:.0f}s)")

    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]

    def num_table(sub):
        g, w = sub[sub["grenade"]], sub[~sub["grenade"]]
        out = {}
        for f in NUM_FIELDS:
            gm, wm = float(g[f].median()), float(w[f].median())
            gs = float(g[f].std()) or 1.0
            ws = float(w[f].std()) or 1.0
            out[f] = {"grenade_med": round(gm, 5), "winner_med": round(wm, 5),
                      "separation": round(abs(gm - wm) / ((gs + ws) / 2), 3)}
        return out

    def cat_table(sub):
        out = {}
        for f in CAT_FIELDS:
            out[f] = {}
            for val, gg in sub.groupby(f):
                out[f][str(val)] = {
                    "n": int(len(gg)),
                    "grenade_rate_pct": round(100 * float(gg["grenade"].mean()), 1)}
        return out

    d_num = num_table(derive)
    best = max(d_num, key=lambda f: d_num[f]["separation"])
    thr = (d_num[best]["grenade_med"] + d_num[best]["winner_med"]) / 2
    hi_side = d_num[best]["grenade_med"] > d_num[best]["winner_med"]

    def rule_perf(sub):
        if len(sub) == 0:
            return {}
        flag = (sub[best] > thr) if hi_side else (sub[best] < thr)
        fl, pa = sub[flag], sub[~flag]
        return {"flagged": f"{int(fl['grenade'].sum())}/{len(fl)}"
                           f" = {100 * fl['grenade'].mean():.1f}%" if len(fl) else "0/0",
                "passed": f"{int(pa['grenade'].sum())}/{len(pa)}"
                          f" = {100 * pa['grenade'].mean():.1f}%" if len(pa) else "0/0"}

    result = {
        "declared": "full chain L0-L4 via replay_symbol_v2; complete DayState "
                    "per event kept raw in the parquet; derive <=2021, "
                    "confirm frozen 2022+; procedure declared before the run",
        "events": {"derive": int(len(derive)), "confirm": int(len(confirm)),
                   "grenade_rate_derive_pct":
                       round(100 * float(derive["grenade"].mean()), 1),
                   "grenade_rate_confirm_pct":
                       round(100 * float(confirm["grenade"].mean()), 1)},
        "derive_numeric_table": d_num,
        "derive_categorical_table": cat_table(derive),
        "confirm_categorical_table": cat_table(confirm),
        "derived_rule": {"feature": best, "threshold": round(thr, 5),
                         "grenade_side": "above" if hi_side else "below"},
        "derive_half": rule_perf(derive),
        "CONFIRM_frozen_2022_plus": rule_perf(confirm),
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
