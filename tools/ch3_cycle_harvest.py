"""
ch3_cycle_harvest.py — the cycle read under live-true timing
============================================================

The per-gate expression is falsified at every rung: the reveal slip is
paid on every boundary crossing and eats the (real, proven) sign edge.
The cycle read pays the slip ONCE per position:

  ENTRY   a band>=BAND prediction (n>=W at issue, as-of-issue record)
          — LONG on +1, SHORT on -1 — filled at the prediction's issue
          close (the reveal bar; live-true).
  EXIT    the FIRST later prediction on the same symbol (any
          consistency, n>=W) whose majority reads AGAINST the position
          — filled at ITS issue close. Force-close at the symbol's
          last prediction event if no reversal arrives.
  BOOK    fresh $100,000 per calendar year of entry; 10% slices,
          max 10 concurrent, one position per symbol.

All prediction events come from the strict as-of-issue ledger
(CH3_KEEP_ALL streams). Nothing here re-reads prices: every fill is a
prediction event's own issue close.

Usage: CH3_PREDS=... python tools/ch3_cycle_harvest.py [BAND]
Output: CH3_HARVEST_OUT (json)
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDS = os.environ.get("CH3_PREDS")
OUT = os.environ.get("CH3_HARVEST_OUT") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_cycle_harvest.json")
CASH0 = 100_000.0
SLICE_PCT = 10.0
MAX_OPEN = 10
# CH3_MORPH=1: morphology exits — each species' own causal median
# gates-to-peak (>=3 completed cycles required; before that, the
# ordinary opposing-majority exit applies). Peak = best return at any
# prediction event during the cycle; the gate clock is the symbol's
# prediction-event stream. All stores causal.
MORPH = os.environ.get("CH3_MORPH") == "1"


def main():
    band_min = float(sys.argv[1]) if len(sys.argv) > 1 else 0.75
    df = pd.read_parquet(PREDS)
    df = df[df["alpha"] == "bigram"].copy()
    df = df.sort_values(["issue_d", "sym"], kind="mergesort")
    key_div = 10 ** 8 if df["issue_d"].max() > 10 ** 10 else 10 ** 6
    print(f"prediction events: {len(df)} (bigram, all n>=W); "
          f"entries at band>={band_min}")

    books = {}                  # entry-year -> dict(cash, trades, wins)
    held = {}                   # sym -> position dict
    hold_hours = []
    last_event = {}             # sym -> (issue_d, issue_px) for force-close
    morph_store = defaultdict(list)   # species -> peak-gate history

    def book(y):
        if y not in books:
            books[y] = {"cash": CASH0, "rets": [], "made": 0.0}
        return books[y]

    def settle(sym, px, d):
        h = held.pop(sym)
        ret = 100 * (px / h["epx"] - 1.0) * h["side"]
        b = books[h["y"]]
        b["cash"] += h["notional"] * (1 + ret / 100.0)
        b["rets"].append(ret)
        if MORPH:                       # record the completed cycle's shape
            morph_store[h["sp"]].append(h["peak_gate"])
        t0 = pd.to_datetime(str(h["ed"]), format="%Y%m%d%H%M")
        t1 = pd.to_datetime(str(d), format="%Y%m%d%H%M")
        hold_hours.append((t1 - t0).total_seconds() / 3600)

    cols = ["issue_d", "sym", "pred", "band", "issue_px", "species"]
    for issue_d, sym, pred, band, ipx, spc in zip(
            *(df[c].to_numpy() for c in cols)):
        last_event[sym] = (issue_d, ipx)
        h = held.get(sym)
        if h is not None:
            h["gates"] += 1
            r = 100 * (float(ipx) / h["epx"] - 1.0) * h["side"]
            if r > h["peak_ret"]:
                h["peak_ret"], h["peak_gate"] = r, h["gates"]
            hist = morph_store.get(h["sp"], []) if MORPH else []
            if MORPH and len(hist) >= 3:
                if h["gates"] >= int(np.median(hist)):
                    settle(sym, ipx, issue_d)
                    continue
            if int(pred) == -h["side"]:     # ordinary collapse exit
                settle(sym, ipx, issue_d)
            continue
        if band < band_min:
            continue
        y = int(issue_d // key_div)
        b = book(y)
        open_here = sum(1 for x in held.values() if x["y"] == y)
        notional = min(b["cash"] * SLICE_PCT / 100.0, b["cash"])
        if open_here >= MAX_OPEN or notional <= 0:
            continue
        b["cash"] -= notional
        held[sym] = {"y": y, "notional": notional, "epx": float(ipx),
                     "side": int(pred), "ed": int(issue_d),
                     "sp": int(spc), "gates": 0,
                     "peak_ret": 0.0, "peak_gate": 0}

    for sym in list(held.keys()):           # force-close leftovers
        d, px = last_event[sym]
        settle(sym, px, d)

    by_year = {}
    for y in sorted(books):
        b = books[y]
        rets = b["rets"]
        wins = sum(1 for r in rets if r > 0)
        by_year[str(y)] = {
            "trades": len(rets),
            "wr_pct": round(100 * wins / len(rets), 1) if rets else None,
            "mean_ret_pct": round(float(np.mean(rets)), 3) if rets else None,
            "made_usd": round(b["cash"] - CASH0, 2),
            "end_value": round(b["cash"], 2),
            "ret_pct": round(100 * (b["cash"] / CASH0 - 1), 2)}
    hh = np.array(hold_hours) if hold_hours else np.array([0.0])
    result = {
        "frame": f"{'morphology' if MORPH else 'cycle'} read, live-true "
                 f"fills — entry band>={band_min} at reveal close, exit "
                 f"{'species median gates-to-peak (causal, >=3 cycles) else ' if MORPH else ''}"
                 "first opposing majority at its reveal close, both "
                 "polarities, 10% slices max-10, fresh $100k per entry-year",
        "holding_hours_median": round(float(np.median(hh)), 1),
        "holding_hours_p90": round(float(np.percentile(hh, 90)), 1),
        "by_year": by_year}
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
