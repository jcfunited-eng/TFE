"""CH2 L5 governance test — declared 2026-09-30 before running.

Joe: "the remaining pieces are the L5 governance layer and filters for
zombies, pump and dumps, too few bars, and other non tradeable — so start
there and see what the numbers start looking like."

KERNEL: the canon kernel on the raw bar (O,H,L,C,V), causal single pass
(tools/canon_kernel_causal.py). Three RESOLUTIONS (the spec's multi-core):
  R0  tau_D = 0.20 (canon; a boundary every bar)
  R1  tau_D = 3.77 x the ticker's trailing median D   (MINE)
  R2  tau_D = 8.00 x the ticker's trailing median D   (MINE)
At R1/R2 a reading is produced when a gate ends; between gate ends the last
reading stands (what the system would hold that day).

STATE per resolution (MINE, from the seen-half census, fixed here):
  ACTIVE  = R_k at or above the 80th percentile of that resolution's own
            readings in the seen half of the filtered pool (computed once
            on the seen half; the same number is applied to the confirm
            half — no re-tuning).
L5 GATE (MINE): on day t the name is tradeable (tools/ch2_canon_census.py
filters), the quorum holds — at least Q of the 3 resolutions ACTIVE — and
it has held for P consecutive days (persistence). Enter at close t. Hold
20 sessions, one position per name at a time (cooldown = the hold).
ARMS: Q in {1, 2, 3} x P in {1, 3, 5}.  NULL: every tradeable day, same hold.
PASS BAR (declared): an arm's 20-session win rate beats the null by >= 3
points in BOTH halves with >= 2,000 trades in each. Filed either way.
Costs not modelled; close-only; survivorship not handled.
OUTPUT: artifacts/ch4_uf/ch2_l5_governance_test.json
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

RES = {"R0": ("fixed", 0.20), "R1": ("own", 3.77), "R2": ("own", 8.0)}
START = pd.Timestamp("2021-01-01")
CONFIRM = pd.Timestamp("2024-01-01")
HOLD = 20
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_l5_governance_test.json"


def one(task):
    from canon_kernel_causal import readings
    from ch2_canon_census import tradeable_flags
    symbol, df = task
    df = df.sort_values("Date").reset_index(drop=True)
    F = df[["Open", "High", "Low", "Close", "Volume"]].values.astype(float)
    close = df.Close.values.astype(float)
    n = len(close)
    out = pd.DataFrame({"symbol": symbol, "date": df.Date.values, "close": close})
    for name, (kind, v) in RES.items():
        r = readings(F, tau_D=(v if kind == "fixed" else "own"), c=(v if kind == "own" else 3.77))
        s = pd.Series(np.nan, index=np.arange(n)); s.iloc[r.t.values] = r.R_k.values
        out["R_" + name] = s.ffill().values.astype("float32")         # the standing reading on each day
    fl = tradeable_flags(df)
    out["tradeable"] = fl.tradeable.values
    fwd = np.full(n, np.nan); fwd[: n - HOLD] = close[HOLD:] / close[: n - HOLD] - 1.0
    out["r20"] = fwd.astype("float32")
    return out[out.date >= START]


def trades(g: pd.DataFrame, signal: np.ndarray):
    """One position per name at a time: enter on a signal day, hold HOLD sessions."""
    idx = np.where(signal)[0]
    taken, last_exit = [], -1
    for i in idx:
        if i <= last_exit:
            continue
        taken.append(i); last_exit = i + HOLD
    return g.r20.values[taken]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    bars = pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet")
    symbols = sorted(bars.Symbol.unique())[:: a.every]
    tasks = [(s, g) for s, g in bars[bars.Symbol.isin(symbols)].groupby("Symbol")]
    del bars
    print(f"[l5] symbols {len(tasks)} resolutions {RES} workers {a.workers}", flush=True)
    t0 = time.time(); parts = []
    with Pool(a.workers) as pool:
        for i, r in enumerate(pool.imap_unordered(one, tasks, chunksize=4), 1):
            parts.append(r)
            if i % 250 == 0:
                print(f"[l5] {i}/{len(tasks)} {time.time() - t0:.0f}s", flush=True)
    ev = pd.concat(parts, ignore_index=True); del parts
    ev = ev.sort_values(["symbol", "date"]).reset_index(drop=True)
    ev["half"] = np.where(ev.date < CONFIRM, "seen", "confirm")
    seen_tr = ev[(ev.half == "seen") & ev.tradeable]
    thr = {name: float(np.nanpercentile(seen_tr["R_" + name], 80)) for name in RES}
    print("[l5] ACTIVE thresholds (80th pct of seen-half tradeable readings):", thr, flush=True)
    for name in RES:
        ev["A_" + name] = (ev["R_" + name] >= thr[name]).astype(int)
    ev["quorum"] = ev[["A_" + n for n in RES]].sum(axis=1)
    res = {"declared": "kernel, resolutions, state, gate, arms, null and pass bar in the docstring, before results",
           "thresholds": thr, "symbols": len(tasks), "arms": {}, "null": {}}
    for half in ("seen", "confirm"):
        h = ev[(ev.half == half) & ev.tradeable]
        base = h.r20.dropna()
        res["null"][half] = {"n_days": int(len(base)), "win_rate": round(float((base > 0).mean()), 4), "mean_r20_pct": round(float(base.mean() * 100), 3)}
    print("[l5] null:", res["null"], flush=True)
    for Q in (1, 2, 3):
        for P in (1, 3, 5):
            arm = {}
            for half in ("seen", "confirm"):
                rets = []
                for sym, g in ev[ev.half == half].groupby("symbol", sort=False):
                    q = (g.quorum.values >= Q)
                    run = np.zeros(len(g), dtype=int)
                    for i in range(len(g)):
                        run[i] = run[i - 1] + 1 if (q[i] and i > 0) else int(q[i])
                    sig = (run >= P) & g.tradeable.values & ~np.isnan(g.r20.values)
                    rets.append(trades(g, sig))
                rets = np.concatenate(rets) if rets else np.array([])
                arm[half] = {"n_trades": int(len(rets)), "win_rate": round(float((rets > 0).mean()), 4) if len(rets) else None,
                             "mean_r20_pct": round(float(rets.mean() * 100), 3) if len(rets) else None,
                             "lift_pts": round(float(((rets > 0).mean() - res["null"][half]["win_rate"]) * 100), 2) if len(rets) else None}
            arm["PASS"] = bool(all(arm[hf]["n_trades"] >= 2000 and (arm[hf]["lift_pts"] or -99) >= 3.0 for hf in ("seen", "confirm")))
            res["arms"][f"Q{Q}_P{P}"] = arm
            print(f"[l5] Q>={Q} P>={P}: seen n={arm['seen']['n_trades']} WR={arm['seen']['win_rate']} lift={arm['seen']['lift_pts']} | "
                  f"confirm n={arm['confirm']['n_trades']} WR={arm['confirm']['win_rate']} lift={arm['confirm']['lift_pts']} | PASS={arm['PASS']}", flush=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("filed:", OUT)


if __name__ == "__main__":
    main()
