"""
ch3_hourly_harvest.py — dollars from the hourly species law
===========================================================

The law is established at the hourly rung (ch3_hourly_law.json:
bigram band>=0.75 causal predictions hit 62.7-68.1% EVERY year,
2016-2026, field-wide). This converts those exact predictions into a
declared book — the construction proven at the daily rung, nothing
new invented:

  ENTRY   at the prediction's issue close (the gate close), LONG on
          +1, SHORT on -1 (both polarities collected).
  EXIT    at the next gate's close (the completion the species
          predicts) — the structure's own boundary; median holding
          ~1 session.
  BOOK    fresh $100,000 per calendar year (by issue date); 10%
          slices, max 10 concurrent, one position per symbol —
          identical to the daily harvest-ladder declaration.

Usage: python tools/ch3_hourly_harvest.py [BAND]
Output: artifacts/ch4_uf/ch3_hourly_harvest.json
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.environ.get("CH3_PREDS") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_hourly_band_preds.parquet")
OUT = os.environ.get("CH3_HARVEST_OUT") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_hourly_harvest.json")
CASH0 = 100_000.0
SLICE_PCT = 10.0
MAX_OPEN = 10


def main():
    band_min = float(sys.argv[1]) if len(sys.argv) > 1 else 0.75
    df = pd.read_parquet(PREDS)
    df = df[(df["alpha"] == "bigram") & (df["band"] >= band_min)].copy()
    df = df.sort_values(["issue_d", "sym"], kind="mergesort")
    print(f"predictions: {len(df)} (bigram, band>={band_min})")

    import heapq
    by_year = {}
    hold_hours = []
    key_div = 10 ** 8 if df["issue_d"].max() > 10 ** 10 else 10 ** 6
    for year, sub in df.groupby(df["issue_d"] // key_div):
        cash, held, heap, settled = CASH0, {}, [], []
        skipped = 0
        for r in sub.itertuples(index=False):
            while heap and heap[0][0] <= r.issue_d:
                _d, hsym, notional, ret = heapq.heappop(heap)
                cash += notional * (1 + ret / 100.0)
                settled.append(ret)
                held.pop(hsym, None)
            if r.sym in held or len(held) >= MAX_OPEN:
                skipped += 1
                continue
            equity = cash + sum(held.values())
            notional = min(equity * SLICE_PCT / 100.0, cash)
            if notional <= 0:
                skipped += 1
                continue
            ret = 100 * (r.exit_px / r.issue_px - 1.0) * r.pred
            cash -= notional
            held[r.sym] = notional
            heapq.heappush(heap, (r.exit_d, r.sym, notional, ret))
            fmt = "%Y%m%d%H%M" if key_div == 10 ** 8 else "%Y%m%d%H"
            t0 = pd.to_datetime(str(r.issue_d), format=fmt)
            t1 = pd.to_datetime(str(r.exit_d), format=fmt)
            hold_hours.append((t1 - t0).total_seconds() / 3600)
        while heap:
            _d, hsym, notional, ret = heapq.heappop(heap)
            cash += notional * (1 + ret / 100.0)
            settled.append(ret)
        wins = sum(1 for x in settled if x > 0)
        by_year[str(year)] = {
            "trades": len(settled), "skipped": skipped,
            "wr_pct": round(100 * wins / len(settled), 1) if settled else None,
            "mean_ret_pct": round(float(np.mean(settled)), 3) if settled else None,
            "made_usd": round(cash - CASH0, 2),
            "end_value": round(cash, 2),
            "ret_pct": round(100 * (cash / CASH0 - 1), 2)}

    hh = np.array(hold_hours)
    result = {
        "frame": f"hourly species harvest — bigram band>={band_min}, "
                 "long/short at issue close, exit next gate close, "
                 "10% slices max-10, fresh $100k/yr",
        "note_2026": "store ends 2026-03-24 (partial year)",
        "holding_hours_median": round(float(np.median(hh)), 1),
        "holding_hours_p90": round(float(np.percentile(hh, 90)), 1),
        "by_year": by_year,
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
