"""CH2 L5 — exposure follows the field, selection follows the particle.
Declared 2026-09-30 before running.

PHYSICS (measured today): the stock's own geometry gives magnitude — the
capacitor law holds (shock size grows with the quiet before it) — and no
sign. The sign is in the field the stock sits in: SPY's own kernel reading.

FIELD STATE (causal): SPY's w_k from the canon kernel on SPY's raw bar,
each day against SPY's own trailing 252 readings: BUSY = at or above the
80th percentile, QUIET = at or below the 20th, MID otherwise. Known at the
close of the day it describes.
PARTICLE STATE (causal): the age of the stock's standing gate at herd
resolution (field B: prices in the norm, volume as relevance) — how long
the quiet has been storing — and whether a boundary formed that day.
ENTRY: at the close of day t, if the arm's condition holds and the name is
tradeable (ch2_canon_census filters). HOLD: 20 sessions. One position per
name at a time. Equal weight per position.
ARMS
  A0  every tradeable day                                (the null)
  A1  field not QUIET
  A2  field BUSY
  A3  field BUSY  and particle quiet >= 21 bars (stored)
  A4  field not QUIET and particle quiet >= 21 bars
  A5  field BUSY  and a boundary formed today (release)
  A6  field QUIET (the state to avoid — reported to show the other side)
REPORT per YEAR: positions, win rate, mean 20-day return, sum of returns
per $1 per position, days with the gate open (exposure). Both halves are
in the years. PASS BAR (declared): an arm beats A0's win rate in at least
5 of 6 years 2021–2026 by >= 3 points and its mean return in 5 of 6.
Costs not modelled; close-only; survivorship not handled.
OUTPUT: artifacts/ch4_uf/ch2_l5_field_gate_test.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
W = 20
HOLD = 20
START = "2021-01-01"
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_l5_field_gate_test.json"
_TAU = {}


def _init(tau_map):
    global _TAU
    _TAU = tau_map


def one(task):
    from canon_kernel_causal import readings
    from ch2_canon_census import tradeable_flags
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[["Open", "High", "Low", "Close"]].values.astype(float)
    v = df.Volume.astype(float); med = v.rolling(W, min_periods=1).median()
    rel = np.where(med > 0, v / med.replace(0, np.nan), 1.0); rel = np.where(np.isfinite(rel), rel, 1.0)
    close = df.Close.values.astype(float); n = len(close)
    r = readings(F, tau_D=_TAU[symbol], r=rel)
    bnd = np.zeros(n, dtype=bool); bnd[r.t.values] = True
    last = -1; age = np.zeros(n, dtype=int)
    for t in range(n):
        if t >= 1 and bnd[t - 1]:
            last = t - 1
        age[t] = t - last if last >= 0 else 0
    known_bnd = np.zeros(n, dtype=bool); known_bnd[1:] = bnd[:-1]     # a boundary at t-1 is knowable at close t
    fwd = np.full(n, np.nan); fwd[: n - HOLD] = close[HOLD:] / close[: n - HOLD] - 1.0
    out = pd.DataFrame({"symbol": symbol, "date": df.Date.astype(str).str[:10].values, "age": age, "release": known_bnd,
                        "tradeable": tradeable_flags(df).tradeable.values, "r20": fwd.astype("float32")})
    return out[out.date >= START]


def positions(g: pd.DataFrame, cond: np.ndarray):
    idx = np.where(cond)[0]; taken, last_exit = [], -1
    for i in idx:
        if i <= last_exit:
            continue
        taken.append(i); last_exit = i + HOLD
    return g.iloc[taken]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    from ch2_herd_census import herd_state
    t0 = time.time()
    spy = pd.read_csv(ROOT / "artifacts" / "ch2_life" / "SPY_causal_state.csv"); spy["date"] = spy.date.astype(str)
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars.Symbol.unique())[:: a.every]
    bars = bars[bars.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).reset_index(drop=True)
    tau, cs, weather = herd_state(bars, cols=("Open", "High", "Low", "Close"))
    tau_map = {s: tau[s].reindex(g.Date.values).values for s, g in bars.groupby("Symbol", sort=False)}
    tasks = [(s, g) for s, g in bars.groupby("Symbol", sort=False)]
    del bars
    parts = []
    with Pool(a.workers, initializer=_init, initargs=(tau_map,)) as pool:
        for r in pool.imap_unordered(one, tasks, chunksize=4):
            parts.append(r)
    ev = pd.concat(parts, ignore_index=True); del parts
    ev = ev.merge(spy[["date", "spy_causal"]], on="date", how="left")
    ev = ev[ev.spy_causal.notna() & ev.r20.notna()].sort_values(["symbol", "date"]).reset_index(drop=True)
    ev["year"] = ev.date.str[:4]
    print(f"[l5] stock-days {len(ev)} ({time.time() - t0:.0f}s)", flush=True)
    busy = (ev.spy_causal == "busy").values; quiet = (ev.spy_causal == "quiet").values
    stored = (ev.age >= 21).values; release = ev.release.values; trad = ev.tradeable.values
    arms = {"A0 every tradeable day": trad,
            "A1 field not quiet": trad & ~quiet,
            "A2 field busy": trad & busy,
            "A3 busy & particle quiet>=21": trad & busy & stored,
            "A4 not quiet & particle quiet>=21": trad & ~quiet & stored,
            "A5 busy & release today": trad & busy & release,
            "A6 field quiet (avoid)": trad & quiet}
    res = {"declared": "physics, states, entry, hold, arms, per-year report and pass bar in the docstring before results", "arms": {}}
    days_open = ev.groupby("year").apply(lambda g: {"busy": float((g.spy_causal == "busy").mean()), "not_quiet": float((g.spy_causal != "quiet").mean())})
    pd.set_option("display.width", 220)
    per_year_tables = {}
    for name, cond in arms.items():
        ev["_c"] = cond
        pos = pd.concat([positions(g, g._c.values) for _, g in ev.groupby("symbol", sort=False)], ignore_index=True)
        t = pos.groupby("year").r20.agg(positions="size", win_rate=lambda s: float((s > 0).mean()), mean_r20_pct=lambda s: float(s.mean() * 100),
                                        sum_per_position=lambda s: float(s.sum()))
        per_year_tables[name] = t
        res["arms"][name] = {y: {c: round(float(v), 4) for c, v in row.items()} for y, row in t.iterrows()}
        res["arms"][name]["total"] = {"positions": int(len(pos)), "win_rate": round(float((pos.r20 > 0).mean()), 4), "mean_r20_pct": round(float(pos.r20.mean() * 100), 3)}
        print(f"\n== {name}: total positions {len(pos)}, WR {float((pos.r20 > 0).mean()):.4f}, mean {float(pos.r20.mean() * 100):.3f}%")
        print(t.round(4).to_string())
    base = per_year_tables["A0 every tradeable day"]
    for name, t in per_year_tables.items():
        if name.startswith("A0"): continue
        j = t.join(base, rsuffix="_base")
        wr_ok = int(((j.win_rate - j.win_rate_base) >= 0.03).sum()); mean_ok = int((j.mean_r20_pct > j.mean_r20_pct_base).sum())
        res["arms"][name]["PASS"] = bool(wr_ok >= 5 and mean_ok >= 5)
        res["arms"][name]["years_wr_ge_plus3"] = wr_ok; res["arms"][name]["years_mean_better"] = mean_ok
        print(f"[l5] {name}: years WR >= base+3pts: {wr_ok}/6, years mean > base: {mean_ok}/6, PASS={res['arms'][name]['PASS']}")
    res["field_state_share_of_days"] = {y: v for y, v in days_open.items()}
    json.dump(res, open(OUT, "w"), indent=1)
    print("filed:", OUT)


if __name__ == "__main__":
    main()
