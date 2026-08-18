"""
ch3_vehicle_refusal.py — the kernel's vehicle signature as a refusal law
========================================================================

DECLARED 2026-08-18 BEFORE THE RUN. Joe's frame, verbatim: "the FAIL
are these stocks - these are the short killers and the kernel (when
used correctly) provides a very clear way to avoid them." Confirmed
on two live killers (WETO -112%, IPST -117%): both carry the same
lifetime field signature, readable long before the spike.

SIGNATURE FACTS per event t (kernel outputs over the stock's ENTIRE
prior life at daily resolution — the engine's own instrument; all
causal, all exact counts, no fitted constants):
  bfloor   share of prior bars with B_k <= -0.999 (carry dead),
           dyadic classes {<50%, 50-75%, 75-87.5%, >=87.5%}
  extN     count of prior extinction events (channel deaths),
           dyadic {0, 1-3, 4-15, 16+}
  extRun   longest run of consecutive prior DAYS carrying an
           extinction, dyadic {0-1, 2-3, 4+}  (death epochs)
  crush    max prior close / current close, dyadic {<2, 2-4, 4-16,
           16+}  (born-high collapse depth)
  VEHICLE  := bfloor >= 75% AND extN >= 4 AND crush >= 4
           (the WETO/IPST species; conjunction of exact facts,
           declared here before any outcome is touched)

OUTCOMES per event (TRUE GAP ACCOUNTING — the flaw in the earlier
scar sweep, disclosed: a -20% stop does not fill at -20%; the exit
books the ACTUAL close that crossed it, exactly as the live book did
with WETO):
  fade return: short at c(t); exit at the first close <= 0.95x entry
  or the first close >= 1.20x entry — booked AT THAT CLOSE, however
  deep the gap — else the 5th close. ran / unwound as before.

REFUSAL SIMULATION: fade dollars per 100 events for ALL events, for
non-vehicle events only, and for vehicle events only — plus the
worst single event in each class (the tail is the point). Split
derive <= 2021-12-31 / confirm 2022+; the 70 taxonomy events
excluded; n >= 50 to speak.

Usage:  python tools/ch3_vehicle_refusal.py
Output: artifacts/ch4_uf/ch3_vehicle_refusal.json
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
SAMPLE = os.path.join(ROOT, "docs", "CH3_JEWELER_SAMPLE_70.json")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_vehicle_refusal.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X, HARVEST_X = 1.20, 0.95
DERIVE_END = 20211231
WARMUP = 60
MIN_CLASS_N = 50


def dyad_share(x):
    return ("<50" if x < 0.5 else "50-75" if x < 0.75
            else "75-87" if x < 0.875 else ">=87")


def dyad_count(n):
    return "0" if n == 0 else "1-3" if n <= 3 else "4-15" if n <= 15 else "16+"


def dyad_run(n):
    return "0-1" if n <= 1 else "2-3" if n <= 3 else "4+"


def dyad_crush(r):
    return "<2" if r < 2 else "2-4" if r < 4 else "4-16" if r < 16 else "16+"


def main():
    t0 = time.time()
    read70 = {(r["sym"], int(r["date"])) for r in json.load(open(SAMPLE))}
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)
    herd_keys = set(zip(herd["sym"], herd["date"]))

    rows = []
    n_done = skipped = 0
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        dates = s["Date"].to_numpy()
        n = len(c)
        if n < WARMUP + HOLD + 5:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        evs = []
        for t in range(WARMUP + 2, n - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            key = (sym, int(d[t]))
            if key in herd_keys or key in read70:
                continue
            evs.append(t)
        if not evs:
            continue
        try:
            states = replay_symbol_v2(dates, c, v, warmup=WARMUP)
        except Exception:  # noqa: BLE001
            skipped += len(evs)
            continue
        bflo = np.array([1 if (st is not None and st.B_k <= -0.999) else 0
                         for st in states])
        extv = np.array([1 if (st is not None and st.extinction) else 0
                         for st in states])
        cum_b = np.cumsum(bflo)
        cum_e = np.cumsum(extv)
        valid = np.cumsum([1 if st is not None else 0 for st in states])
        # longest prior extinction-day run (daily bars: run of ext days)
        runlen = np.zeros(n, dtype=np.int64)
        cur = 0
        for k in range(n):
            cur = cur + 1 if extv[k] else 0
            runlen[k] = max(runlen[k - 1] if k else 0, cur)
        cmax = np.maximum.accumulate(c)
        for t in evs:
            nv = valid[t - 1]
            if nv < 20:
                continue
            share = cum_b[t - 1] / nv
            extn = int(cum_e[t - 1])
            erun = int(runlen[t - 1])
            crush = float(cmax[t - 1] / c[t]) if c[t] > 0 else 1.0
            vehicle = (share >= 0.75 and extn >= 4 and crush >= 4)
            entry = c[t]
            exit_px = c[t + HOLD]
            for k in range(t + 1, t + HOLD + 1):
                if c[k] <= HARVEST_X * entry or c[k] >= GRENADE_X * entry:
                    exit_px = c[k]      # TRUE gap accounting: book this close
                    break
            rows.append({
                "sym": sym, "date": int(d[t]),
                "bfloor": dyad_share(share), "extN": dyad_count(extn),
                "extRun": dyad_run(erun), "crush": dyad_crush(crush),
                "vehicle": bool(vehicle),
                "ran": bool(np.any(c[t + 1: t + HOLD + 1]
                                   >= GRENADE_X * entry)),
                "unwound": bool(c[t + HOLD] <= c[t - 1]),
                "fade_ret": 100 * (entry - exit_px) / entry,
            })
        n_done += 1
        if n_done % 500 == 0:
            print(f"  [{n_done}] symbols, {len(rows)} events, "
                  f"{time.time() - t0:.0f}s", flush=True)

    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT.replace(".json", "_events.parquet"), index=False)
    print(f"events: {len(ev)}, replay-skipped: {skipped}")

    def ledger(sub):
        if len(sub) == 0:
            return {"n": 0}
        return {
            "n": int(len(sub)),
            "ran": f"{int(sub['ran'].sum())}/{len(sub)}"
                   f" = {100 * sub['ran'].mean():.1f}%",
            "unwound": f"{int(sub['unwound'].sum())}/{len(sub)}"
                       f" = {100 * sub['unwound'].mean():.1f}%",
            "fade_per_100ev": round(100 * float(sub["fade_ret"].sum())
                                    / len(sub), 1),
            "worst_event_pct": round(float(sub["fade_ret"].min()), 1),
            "events_below_-50pct": int((sub["fade_ret"] < -50).sum()),
        }

    def half(sub, name):
        return {
            "ALL": ledger(sub),
            "NON_VEHICLE_kept": ledger(sub[~sub["vehicle"]]),
            "VEHICLE_refused": ledger(sub[sub["vehicle"]]),
        }

    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]

    def marginal(col):
        out = {}
        for cls, g in confirm.groupby(col):
            if len(g) >= MIN_CLASS_N:
                out[str(cls)] = ledger(g)
        return out

    result = {
        "declared": "signature facts, dyadic classes, the VEHICLE "
                    "conjunction, true-gap exit accounting, and the refusal "
                    "simulation all declared in docstring before results",
        "replay_skipped_events": skipped,
        "derive_le_2021": half(derive, "derive"),
        "CONFIRM_2022_plus": half(confirm, "confirm"),
        "confirm_marginals": {
            "bfloor": marginal("bfloor"), "extN": marginal("extN"),
            "extRun": marginal("extRun"), "crush": marginal("crush"),
        },
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:6000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
