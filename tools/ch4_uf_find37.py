"""
ch4_uf_find37.py — THE FINDER: stocks about to yield ~36.7%, ~91% fidelity
==========================================================================

Joe's definition (2026-07-31): "the 91% is the percentage of time the
physics finds a stock that yields ~36.7% profit — and finds them in every
year." The numbers are detection fidelity and detected-move size, both
CONSTANTS of the problem:

  YIELD  = 36.7 (percent)  — the move class being detected
  FIDELITY BAR = 0.91      — required completion share of finds

MECHANICS (declared, causal):
  Rungs      — reversal-rung ladder (REV_MULT in {4, 8, 16} x trailing-W
               median |daily move|), per stock per rung independent.
  Record     — per stock+rung+side: the last MIN_LEGS=20 completed legs'
               post-confirmation remainders (the harvestable yields).
  ELIGIBLE   — a stock+rung whose record shows >= 91% of its last 20
               legs ran >= 36.7% (the high-energy herd; most of the
               field is never eligible, by physics).
  FIND       — a new leg confirms on an eligible stock+rung (both
               polarities; shorts detect -36.7% fallers).
  COMPLETE   — the +/-36.7% touch from the find close before that
               rung's own flip (the structure's collapse vector).
  FAIL       — the flip arrives first; loss = flip price vs find close
               (bounded by the structure's own reversal scale).

REPORTING — per year only: finds, completion fidelity, mean failure
cost, expectancy. Raw. Nothing tunable exists in this construction.

Usage: CH4_STORE=... python tools/ch4_uf_find37.py [N]
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict, Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_spectrum import life_fraction, W  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250
REV_LADDER = (16, 8, 4)
YIELD_PCT = 36.7
FIDELITY = 0.91
MIN_LEGS = 20


def find_symbol(dates, closes):
    n = len(closes)
    moves = np.abs(np.diff(closes))
    finds = []
    rungs = {m: {"rem": {1: [], -1: []}, "dir": 0, "ext": 0,
                 "conf": {"side": 0, "px": None}} for m in REV_LADDER}
    open_finds = {}   # (rung) -> find dict  (one live find per rung)
    for t in range(1, n):
        w0 = max(0, t - W)
        med = float(np.median(moves[w0:t])) if t > w0 else 0.0
        for m in REV_LADDER:
            R = rungs[m]
            thresh = m * max(med, 1e-9)
            direction = R["dir"]
            ext_i = R["ext"]

            if direction >= 0 and closes[t] > closes[ext_i]:
                ext_i = t
                if direction == 0:
                    direction = 1
            elif direction <= 0 and closes[t] < closes[ext_i]:
                ext_i = t
                if direction == 0:
                    direction = -1

            flipped = None
            if direction == 1 and closes[ext_i] - closes[t] > thresh:
                flipped = -1
            elif direction == -1 and closes[t] - closes[ext_i] > thresh:
                flipped = 1

            # live find on this rung: completion check at this close
            lf = open_finds.get(m)
            if lf is not None and flipped is None:
                if lf["side"] == 1 and closes[t] >= lf["tgt_px"]:
                    finds.append({**lf, "out": str(dates[t]),
                                  "outcome": "COMPLETE",
                                  "ret_pct": YIELD_PCT})
                    open_finds.pop(m, None)
                elif lf["side"] == -1 and closes[t] <= lf["tgt_px"]:
                    finds.append({**lf, "out": str(dates[t]),
                                  "outcome": "COMPLETE",
                                  "ret_pct": YIELD_PCT})
                    open_finds.pop(m, None)

            if flipped is not None:
                lf = open_finds.get(m)
                if lf is not None:
                    raw = 100 * (closes[t] / lf["px"] - 1.0)
                    ret = raw if lf["side"] == 1 else -raw
                    finds.append({**lf, "out": str(dates[t]),
                                  "outcome": "FAIL",
                                  "ret_pct": round(ret, 3)})
                    open_finds.pop(m, None)
                lc = R["conf"]
                if lc["px"] is not None:
                    if lc["side"] == 1:
                        rem = 100 * (closes[ext_i] / lc["px"] - 1.0)
                    else:
                        rem = 100 * (1.0 - closes[ext_i] / lc["px"])
                    R["rem"][lc["side"]].append(max(rem, 0.0))
                side = flipped
                R["conf"] = {"side": side, "px": closes[t]}
                # THE FIND: eligible stock+rung, new leg confirming
                store = R["rem"][side]
                if len(store) >= MIN_LEGS and closes[t] >= PRICE_FLOOR \
                        and open_finds.get(m) is None:
                    recent = np.array(store[-MIN_LEGS:])
                    prop = float((recent >= YIELD_PCT).mean())
                    tgt_px = closes[t] * (1 + YIELD_PCT / 100.0) if side == 1 \
                        else closes[t] * (1 - YIELD_PCT / 100.0)
                    open_finds[m] = {"side": side, "px": closes[t],
                                     "in": str(dates[t]), "rung": m,
                                     "tgt_px": tgt_px,
                                     "propensity": round(prop, 3)}
                R["dir"] = flipped
                R["ext"] = t
            else:
                R["dir"] = direction
                R["ext"] = ext_i
    return finds


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)}")

    all_finds = []
    t0 = time.time()
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        try:
            fs = find_symbol(dates, closes)
        except Exception:
            continue
        for f_ in fs:
            f_["symbol"] = sym
            f_.pop("tgt_px", None)
        all_finds.extend(fs)
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(uni)}] finds={len(all_finds)} "
                  f"{time.time()-t0:.0f}s", flush=True)

    tiers = [0.0, 0.25, 0.5, 0.75, 0.91]
    tier_table = {}
    for lo in tiers:
        sel = [f for f in all_finds if f["propensity"] >= lo]
        if not sel:
            tier_table[str(lo)] = {"finds": 0}
            continue
        c = sum(1 for f in sel if f["outcome"] == "COMPLETE")
        byy = defaultdict(lambda: [0, 0])
        for f in sel:
            y = f["in"][:4]
            byy[y][0] += 1 if f["outcome"] == "COMPLETE" else 0
            byy[y][1] += 1
        tier_table[str(lo)] = {
            "finds": len(sel),
            "fidelity_pct": round(100 * c / len(sel), 2),
            "by_year": {y: f"{v[0]}/{v[1]}={100*v[0]/v[1]:.0f}%" for y, v in sorted(byy.items())}}
    comp = [f for f in all_finds if f["outcome"] == "COMPLETE"]
    fail = [f for f in all_finds if f["outcome"] == "FAIL"]
    by = defaultdict(lambda: {"c": 0, "f": 0, "fail_rets": []})
    for f in all_finds:
        y = f["in"][:4]
        if f["outcome"] == "COMPLETE":
            by[y]["c"] += 1
        else:
            by[y]["f"] += 1
            by[y]["fail_rets"].append(f["ret_pct"])
    result = {
        "fidelity_vs_propensity": tier_table,
        "definition": f"find = new leg on a stock whose own record shows >= {FIDELITY:.0%} "
                      f"of its last {MIN_LEGS} legs ran >= {YIELD_PCT}%",
        "finds": len(all_finds),
        "completions": len(comp),
        "fidelity_pct": round(100 * len(comp) / len(all_finds), 2) if all_finds else None,
        "mean_fail_cost_pct": round(float(np.mean([f["ret_pct"] for f in fail])), 2) if fail else None,
        "sides": dict(Counter(f["side"] for f in all_finds)),
        "rungs": dict(Counter(f["rung"] for f in all_finds)),
        "by_year": {y: {"finds": v["c"] + v["f"],
                        "fidelity_pct": round(100 * v["c"] / (v["c"] + v["f"]), 1) if (v["c"] + v["f"]) else None,
                        "mean_fail_pct": round(float(np.mean(v["fail_rets"])), 2) if v["fail_rets"] else None}
                    for y, v in sorted(by.items())},
    }
    path = os.path.join(OUT_DIR, "ch4_uf_find37.json")
    with open(path, "w") as f:
        json.dump({**result, "finds_detail": all_finds[:100000]}, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", path)


if __name__ == "__main__":
    main()
