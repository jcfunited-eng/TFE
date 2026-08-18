"""
ch3_kernel_scar.py — the vehicle's scar record, per the kernel itself
=====================================================================

DECLARED 2026-08-18 BEFORE THE RUN. Provenance: Joe caught the prior
"scar" (1.5x pump / 0.6x collapse) as what it was — an invented
price indicator with two hand-picked knobs, not kernel analysis.
This rebuild uses the kernel's OWN collapse marker and nothing else:

  EXTINCTION (defined inside ch4_uf_kernel_v2.step_chain_v2, not by
  me):  URF(k) = 0  after  URF(k-1) > 0  and  URF(k-2) > 0
  — the admissibility channel dying after being alive. The kernel
  computes this as a formal event of the field.

SCAR RECORD at event t: the COUNT of extinction events in the
stock's own life BEFORE t (strictly causal), in dyadic classes
{0, 1, 2-3, 4-7, 8+}. No price ratios, no thresholds of mine —
the only constants are the kernel's own pinned laws.

EVENT SET / OUTCOMES / SPLIT: identical to the precedent sweep
(uncovered spikes; ran = any next-5 close >= 1.20x; unwound =
c(t+5) <= c(t-1); fade money under the live law summed per 100;
derive <= 2021-12-31 / confirm 2022+; the 70 taxonomy events
excluded; sparse < 50 stays sparse).

Usage:  python tools/ch3_kernel_scar.py
Output: artifacts/ch4_uf/ch3_kernel_scar.json
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
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_kernel_scar.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
GRENADE_X, HARVEST_X = 1.20, 0.95
DERIVE_END = 20211231
WARMUP = 60
MIN_CLASS_N = 50


def dyad(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 7:
        return "4-7"
    return "8+"


def main():
    t0 = time.time()
    read70 = {(r["sym"], int(r["date"]))
              for r in json.load(open(SAMPLE))}
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
            if (sym, int(d[t])) in herd_keys or (sym, int(d[t])) in read70:
                continue
            evs.append(t)
        if not evs:
            continue
        try:
            states = replay_symbol_v2(dates, c, v, warmup=WARMUP)
        except Exception:  # noqa: BLE001
            skipped += len(evs)
            continue
        urf = np.array([x.URF if x is not None else np.nan for x in states])
        # the kernel's own extinction: URF hits 0 after two alive bars
        ext = np.zeros(n, dtype=np.int64)
        for k in range(2, n):
            if (urf[k] == 0.0 and urf[k - 1] > 0.0 and urf[k - 2] > 0.0):
                ext[k] = 1
        cum_ext = np.cumsum(ext)
        for t in evs:
            entry = c[t]
            exit_px = c[t + HOLD]
            for k in range(t + 1, t + HOLD + 1):
                if c[k] <= HARVEST_X * entry or c[k] >= GRENADE_X * entry:
                    exit_px = c[k]
                    break
            rows.append({
                "sym": sym, "date": int(d[t]),
                "ext_class": dyad(int(cum_ext[t - 1])),
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
    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    print(f"events: {len(ev)} (derive {len(derive)}, confirm {len(confirm)}), "
          f"replay-skipped: {skipped}")

    def table(sub):
        out = {}
        for cls in ["0", "1", "2-3", "4-7", "8+"]:
            g = sub[sub["ext_class"] == cls]
            if len(g) < MIN_CLASS_N:
                out[cls] = {"n": int(len(g)), "sparse": True}
                continue
            out[cls] = {
                "n": int(len(g)),
                "ran": f"{int(g['ran'].sum())}/{len(g)}"
                       f" = {100 * g['ran'].mean():.1f}%",
                "unwound": f"{int(g['unwound'].sum())}/{len(g)}"
                           f" = {100 * g['unwound'].mean():.1f}%",
                "fade_per_100ev": round(100 * float(g["fade_ret"].sum())
                                        / len(g), 1),
            }
        return out

    result = {
        "declared": "scar = the kernel's OWN extinction event count before "
                    "t (URF dies after two alive bars — defined inside the "
                    "fixed chain, no invented constants); procedure in "
                    "docstring, committed before results",
        "replay_skipped_events": skipped,
        "derive_le_2021": table(derive),
        "confirm_2022_plus": table(confirm),
        "runtime_s": round(time.time() - t0),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
