"""
ch4_charging_finder.py — CH4 v1: the charging-vehicle launch finder
===================================================================

DECLARED BEFORE MEASUREMENT (Rule 9), 2026-08-19.

Conception (the picture first): the 36.7% riser class is not a signal
in returns — it is a SPECIES OF VEHICLE in a phase. This week's live
short-gate work proved the shape on specimens (WETO, IPST, CNSP): a
DRAINED vehicle (price far below its lifetime peak) whose CHANNEL
DEATHS PAUSE while the week LOADS is rehearsing a launch. The short
desk refuses that shape on sight (Rules 4+5 — the killer launch
shape). CH4 harvests the same animal from the other side.

The reading, translated to the daily modality (constants declared,
scaled from the live 45-minute gate; every miss is a waypoint):

  DRAINED   crush_T = lifetime_high[..T] / close_T >= 4
  MORTAL    lifetime channel-death rate >= 12/yr (a vehicle whose
            channels routinely die — extinction events from the fixed
            kernel, whole life to date)
  FLOOR     clean rehearsal floor NOW: <= 1 extinction in the last
            10 sessions
  LOADING   direction locked up: D=+1 on >= 3 of the last 5 readings,
            OR >= 3 of the last 5 sessions closing higher

  FIND      all four true (one open find per stock at a time).
  ENTRY     the FIRST ACTIONABLE close, T+1 (the reveal-bar theorem
            falsified acting on the bar that revealed).
  COMPLETE  High touches entry x 1.367 before failure.
  FAIL      the rehearsal floor breaks — >= 2 extinctions inside any
            trailing 10 sessions after entry — priced at that close;
            TIME backstop 250 sessions (priced at that close).

  Universe  whole store, whole lives, strictly as-of; price >= $1 at
            find; life >= 0.90; >= 500 bars of life before a find.
            (Fillability is a TRADING law applied at entry time by the
            desk; the field is measured before the desk trims it.)

  REPORT    per year: finds, completion fidelity vs the 91% bar, mean
            failure return, expectancy. Raw. Nothing tunable exists
            after this header; changing any constant = new version.

Usage: python tools/ch4_charging_finder.py [N_SYMBOLS] [--workers K]
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402
from tools.ch4_uf_spectrum import life_fraction  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch4_charging_finder_v1.json")

YIELD_X = 1.367
CRUSH_MIN = 4.0
DEATHS_PER_YR_MIN = 12.0
FLOOR_WINDOW = 10
FLOOR_MAX_DEATHS = 1
LOAD_WINDOW = 5
LOAD_MIN = 3
PRICE_FLOOR = 1.0
LIFE_MIN = 0.90
MIN_BARS = 500
TIME_CAP = 250
SESSIONS_PER_YEAR = 252


def read_symbol(args):
    symbol, dates, opens, highs, lows, closes, vols = args
    n = len(closes)
    if n < MIN_BARS + 2:
        return []
    states = replay_symbol_v2(dates, closes, vols, warmup=60)
    ext = np.array([1 if (s is not None and s.extinction) else 0 for s in states])
    D = np.array([s.D_k if s is not None else 0 for s in states])
    life = life_fraction(closes)
    lifetime_high = np.maximum.accumulate(highs)
    ext_cum = np.cumsum(ext)
    finds = []
    t = MIN_BARS
    while t < n - 1:
        c = closes[t]
        if c < PRICE_FLOOR or life[t] < LIFE_MIN:
            t += 1
            continue
        crush = lifetime_high[t] / c if c > 0 else 0.0
        yrs = (t + 1) / SESSIONS_PER_YEAR
        deaths_yr = ext_cum[t] / max(yrs, 0.1)
        floor_deaths = int(ext[t - FLOOR_WINDOW + 1:t + 1].sum())
        d_up = int((D[t - LOAD_WINDOW + 1:t + 1] == 1).sum())
        px_up = int((np.diff(closes[t - LOAD_WINDOW:t + 1]) > 0).sum())
        if (crush >= CRUSH_MIN and deaths_yr >= DEATHS_PER_YR_MIN
                and floor_deaths <= FLOOR_MAX_DEATHS
                and (d_up >= LOAD_MIN or px_up >= LOAD_MIN)):
            entry_i = t + 1
            entry = closes[entry_i]           # first actionable close
            if entry <= 0:
                t += 1
                continue
            target = entry * YIELD_X
            window_end = entry_i + TIME_CAP
            outcome, exit_i, ret = "TIME", min(window_end, n - 1), None
            if window_end > n - 1:
                outcome = "CENSORED"          # store ends inside the window:
            for j in range(entry_i + 1, min(window_end, n)):
                if highs[j] >= target:
                    outcome, exit_i, ret = "COMPLETE", j, 36.7
                    break
                if int(ext[j - FLOOR_WINDOW + 1:j + 1].sum()) >= 2:
                    outcome, exit_i = "FAIL", j
                    break
            if ret is None:
                ret = round(100 * (closes[exit_i] / entry - 1), 2)
            finds.append({
                "symbol": symbol,
                "find_day": str(dates[t])[:10],
                "entry_day": str(dates[entry_i])[:10],
                "entry": round(float(entry), 4),
                "crush": round(float(crush), 1),
                "deaths_yr": round(float(deaths_yr), 1),
                "outcome": outcome,
                "ret_pct": float(ret),
                "held": int(exit_i - entry_i),
            })
            t = exit_i + 1                    # one open find per stock
        else:
            t += 1
    return finds


def main():
    n_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
    workers = 14
    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    df = df.sort_values(["Symbol", "Date"])
    # cheap prefilter: only stocks that were EVER drained 4x with a life
    tasks = []
    for symbol, g in df.groupby("Symbol", sort=False):
        if len(g) < MIN_BARS + 2:
            continue
        h = np.maximum.accumulate(g["High"].to_numpy(dtype=float))
        c = g["Close"].to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            if np.nanmax(np.where(c > 0, h / c, 0)) < CRUSH_MIN:
                continue
        tasks.append((symbol, g["Date"].to_numpy(), g["Open"].to_numpy(dtype=float),
                      g["High"].to_numpy(dtype=float), g["Low"].to_numpy(dtype=float),
                      c, g["Volume"].to_numpy(dtype=float)))
    del df
    if n_arg:
        tasks = tasks[:n_arg]
    print(f"[ch4-charging] {len(tasks)} drained-vehicle candidates "
          f"(prefilter {time.time()-t0:.0f}s); replaying whole lives on {workers} workers")
    all_finds = []
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(read_symbol, task) for task in tasks]
        for fut in as_completed(futures):
            all_finds.extend(fut.result())
            done += 1
            if done % 250 == 0:
                print(f"  {done}/{len(tasks)} lives read, {len(all_finds)} finds, "
                      f"{time.time()-t0:.0f}s")
    by_year = {}
    for f in all_finds:
        y = f["entry_day"][:4]
        by_year.setdefault(y, []).append(f)
    report = {"declared": "see tool header — v1, nothing tuned after declaration",
              "candidates": len(tasks), "finds": len(all_finds), "by_year": {}}
    for y in sorted(by_year):
        fs = [f for f in by_year[y] if f["outcome"] != "CENSORED"]
        if not fs:
            report["by_year"][y] = {"finds": 0, "censored": len(by_year[y])}
            continue
        comp = [f for f in fs if f["outcome"] == "COMPLETE"]
        fails = [f["ret_pct"] for f in fs if f["outcome"] != "COMPLETE"]
        fid = 100 * len(comp) / len(fs)
        exp = float(np.mean([f["ret_pct"] for f in fs]))
        report["by_year"][y] = {
            "finds": len(fs), "fidelity_pct": round(fid, 1),
            "mean_fail_ret_pct": round(float(np.mean(fails)), 1) if fails else None,
            "expectancy_pct": round(exp, 2),
            "censored": len(by_year[y]) - len(fs),
        }
    resolved = [f for f in all_finds if f["outcome"] != "CENSORED"]
    total_comp = sum(1 for f in resolved if f["outcome"] == "COMPLETE")
    report["fidelity_pct"] = round(100 * total_comp / max(1, len(resolved)), 1)
    report["censored"] = len(all_finds) - len(resolved)
    report["runtime_s"] = round(time.time() - t0)
    report["finds_detail"] = all_finds
    json.dump(report, open(OUT, "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k != "finds_detail"}, indent=1))
    print(f"[ch4-charging] filed {OUT}")


if __name__ == "__main__":
    main()
