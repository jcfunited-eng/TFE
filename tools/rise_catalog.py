"""rise_catalog.py — the price rises, cataloged before any gauge is read.

Joe's frame: find the historical rises first, then study the tuple story
5/25/90 sessions before and 25 after. This tool does only the first part,
from prices alone, so the catalog cannot be shaped by the gauges.

A rise: from a start session t0, the close reaches >= 1.15x close(t0)
within the next 25 sessions. Overlapping candidate starts collapse to one
episode; the episode's start is its lowest close. Each rise records its
tier (15/25/50%), peak gain, timing, and the life's age (bar_count) so
young Apple-like listings are distinguishable.

Clean frame at t0 (declared, the same weeding the recovery law passed
under): close >= $5, no destroyed shells (lifetime max/close >= 1000x),
20-session median dollar volume >= $200k (floor only), no 25%+ single day
in the prior 10 sessions (the pump signature).

Output: artifacts/ninegauge/rise_catalog.parquet
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "artifacts", "ninegauge", "rise_catalog.parquet")
START = "2021-09-01"
FWD = 25
TIER1 = 1.15


def main() -> None:
    tt = json.load(open(os.path.join(ROOT, "artifacts", "ch6_harvest",
                                     "ticker_types.json")))
    op = {s for s, t in tt.items() if t in ("CS", "ADRC")}
    store = pd.read_parquet(os.path.join(ROOT, "ch4_live_store.parquet"),
                            columns=["Date", "Symbol", "Close", "Volume"])
    store["d"] = store["Date"].astype(str).str[:10]
    rises = []
    for sym, g in store.groupby("Symbol"):
        if sym not in op:
            continue
        g = g.sort_values("d")
        d = g["d"].to_numpy()
        c = g["Close"].to_numpy(float)
        v = g["Volume"].to_numpy(float)
        n = len(c)
        if n < 40:
            continue
        dv = c * v
        life_max = np.maximum.accumulate(c)
        # forward 25-session max close (excluding t0 itself)
        fwd_max = np.full(n, np.nan)
        for i in range(n - 1):
            hi = min(n, i + 1 + FWD)
            fwd_max[i] = c[i + 1:hi].max()
        ratio = fwd_max / c
        # candidate starts under the clean frame
        cand = np.zeros(n, bool)
        for i in range(20, n - 1):
            if d[i] < START or ratio[i] < TIER1 or c[i] < 5:
                continue
            if life_max[i] / c[i] >= 1000:
                continue
            w = dv[max(0, i - 19):i + 1]
            med = float(np.median(w))
            # floor only: junk weeding. No ceiling — a ceiling would
            # exclude every large-cap (Apple itself), against the
            # study's stated purpose. Corrected before any counting.
            if med < 200_000:
                continue
            r10 = c[i - 10:i + 1]
            if any(a > 0 and b / a >= 1.25 for a, b in zip(r10, r10[1:])):
                continue
            cand[i] = True
        # collapse runs of candidates into episodes; start = lowest close
        i = 0
        while i < n:
            if not cand[i]:
                i += 1
                continue
            j = i
            while j + 1 < n and cand[j + 1]:
                j += 1
            seg = slice(i, j + 1)
            t0 = i + int(np.argmin(c[seg]))
            hi = min(n, t0 + 1 + FWD)
            pk = t0 + 1 + int(np.argmax(c[t0 + 1:hi]))
            gain = c[pk] / c[t0] - 1
            after_hi = min(n, pk + 1 + FWD)
            after_ret = (c[after_hi - 1] / c[pk] - 1) if after_hi - 1 > pk else np.nan
            rises.append({
                "symbol": sym, "t0_date": d[t0], "t0_idx": int(t0),
                "peak_date": d[pk], "sessions_to_peak": int(pk - t0),
                "gain_pct": round(100 * gain, 2),
                "tier": 50 if gain >= 0.50 else (25 if gain >= 0.25 else 15),
                "age_bars": int(t0 + 1),
                "young": bool(t0 + 1 <= 60),
                "med20_dollar": round(float(np.median(dv[max(0, t0 - 19):t0 + 1])), 0),
                "after25_from_peak_pct": (round(100 * after_ret, 2)
                                          if np.isfinite(after_ret) else None),
            })
            i = j + 1
    df = pd.DataFrame(rises)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_parquet(OUT)
    print(f"rises: {len(df)} | by tier: {df['tier'].value_counts().to_dict()}"
          f" | young: {int(df['young'].sum())}"
          f" | by year: {df['t0_date'].str[:4].value_counts().sort_index().to_dict()}")


if __name__ == "__main__":
    main()
