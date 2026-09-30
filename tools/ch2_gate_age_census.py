"""CH2 gate-age census — day-by-day, causal, declared 2026-09-30 before running.

FOLLOWS tools/ch2_gate_transition_census.py (2,887 tradable names, own
resolution). That census showed: what came BEFORE a gate does not say which
way price goes across it (every context 46–56% up, both halves). What
holds in both halves is CONCURRENT: long undisturbed gates (> 60 bars) rose
59–61% of the time and carry the big moves; the gate after a long gate is
flat. So the ride is INSIDE the undisturbed stretch and the shock ends it.

Finished gate length is hindsight. But the AGE of the current gate is not:
L1's boundary operator D(t) = |dF| + sigma(20-bar) + kappa uses close[t+1]
only through kappa, so a boundary at bar i is known at close i+1. On day t
the boundaries up to t-1 are known. Age = days since the last known
boundary. Price since the gate's start is known too. Nothing else is used
(psi, R, U, D_k are not prefix-stable and are not read here).

RESOLUTION (HIS: per ticker by size/price; MINE: the setting), causal:
tau_D(t) = 3.77 x median of D over the trailing 252 bars ending at t-1.
A boundary at bar i is declared when D[i] > tau_D(i). Kernel unmodified;
its L0/L1 operators are called; the threshold is applied in this process.

READ each day t (2021-01-01 on), for each tradable name with >= 1,000 bars:
  age    = t - (last known boundary bar) ; bands 1-5, 6-20, 21-60, > 60
  since  = close[t] / close[gate start] - 1 ; UP (> 0) / DOWN
OUTCOMES from close[t]: 20-session return; and the RIDE: return to the
  close after the next boundary (exit at i+1 where i is the next boundary).
HALVES: t < 2024-01-01 (seen) / >= (confirm).
OUTPUT: artifacts/ch4_uf/ch2_gate_age_census.json; sampled rows .parquet.
This is a count. A rule, if any, is declared afterwards from the seen half
and judged on the confirm half.
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
sys.path.insert(0, str(ROOT))

C = 3.77
WINDOW = 252
MIN_BARS = 1000
START = np.datetime64("2021-01-01")
CONFIRM_FROM = pd.Timestamp("2024-01-01")
HOLD = 20
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_gate_age_census"
UNIVERSE = ROOT / "artifacts" / "ch2_life" / "universe_tradable_20260930.csv"


def causal_boundaries(closes: np.ndarray) -> np.ndarray:
    """Boundary flags on the kernel's own D(t) with a trailing per-ticker tau."""
    from uf_core.layer0 import compute_sev_series
    from uf_core.layer1 import compute_deviation
    D = compute_deviation(compute_sev_series(pd.DataFrame({"Close": closes})))
    tau = pd.Series(D).shift(1).rolling(WINDOW, min_periods=WINDOW).median().values * C
    return (D > tau) & np.isfinite(tau)


def one_symbol(task):
    symbol, dates, closes = task
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    b = causal_boundaries(closes)
    start_idx = int(np.searchsorted(dates, START))
    # last boundary known at day t: the latest i <= t-1 with b[i]; gate start = that i
    last = -1
    last_known = np.full(n, -1)
    for t in range(n):
        if t >= 1 and b[t - 1]:
            last = t - 1
        last_known[t] = last
    # next boundary i > t-1 (i >= t); exit at i+1
    nxt = np.full(n, -1)
    upcoming = -1
    for t in range(n - 1, -1, -1):
        if b[t]:
            upcoming = t
        nxt[t] = upcoming
    rows = []
    for t in range(max(start_idx, WINDOW + 2), n - 2):
        s = last_known[t]
        if s < 0:
            continue
        age = t - s
        since = closes[t] / closes[s] - 1.0
        r20 = closes[t + HOLD] / closes[t] - 1.0 if t + HOLD < n else np.nan
        i = nxt[t]
        ride = closes[i + 1] / closes[t] - 1.0 if 0 <= i and i + 1 < n else np.nan
        ride_len = (i + 1 - t) if 0 <= i and i + 1 < n else -1
        rows.append((symbol, str(dates[t])[:10], age, since, r20, ride, ride_len))
    return symbol, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=1)
    args = ap.parse_args()
    uni = pd.read_csv(UNIVERSE)
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    store = store[store.Symbol.isin(set(uni.ticker))]
    counts = store.groupby("Symbol").size()
    symbols = sorted(counts[counts >= MIN_BARS].index)[:: args.every]
    print(f"[age] tradable in store with >= {MIN_BARS} bars: {len(symbols)}; workers {args.workers}", flush=True)
    tasks = [(s, g.Date.values.astype("datetime64[D]"), g.Close.values)
             for s, g in store[store.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).groupby("Symbol")]
    del store
    t0 = time.time()
    parts, done = [], 0
    with Pool(args.workers) as pool:
        for symbol, rows in pool.imap_unordered(one_symbol, tasks, chunksize=4):
            parts.append(pd.DataFrame(rows, columns=["symbol", "date", "age", "since", "r20", "ride", "ride_len"]))
            done += 1
            if done % 250 == 0:
                print(f"[age] {done}/{len(tasks)} symbols, {time.time() - t0:.0f}s", flush=True)
    ev = pd.concat(parts, ignore_index=True)
    ev["half"] = np.where(pd.to_datetime(ev.date) < CONFIRM_FROM, "seen", "confirm")
    ev["age_band"] = pd.cut(ev.age, [0, 5, 20, 60, 10 ** 6], labels=["1-5", "6-20", "21-60", ">60"])
    ev["since_dir"] = np.where(ev.since > 0, "UP", "DOWN")
    ev.sample(min(len(ev), 2_000_000), random_state=0).to_parquet(OUT.with_suffix(".parquet"), index=False)
    res = {"declared": "resolution, reading, outcomes, halves in the docstring, before results",
           "universe": len(symbols), "days": int(len(ev)), "tables": {}}
    pd.set_option("display.width", 200)
    for name, keys in (("by_age", ["age_band"]), ("by_age_and_since", ["age_band", "since_dir"]), ("all", ["half"])):
        res["tables"][name] = {}
        for half in ("seen", "confirm"):
            h = ev[ev.half == half]
            g = h.groupby(keys, observed=True)
            t = pd.DataFrame({"n": g.size(),
                              "up_share_20d": g.r20.apply(lambda s: float((s.dropna() > 0).mean())),
                              "mean_r20_pct": g.r20.mean() * 100,
                              "ride_up_share": g.ride.apply(lambda s: float((s.dropna() > 0).mean())),
                              "mean_ride_pct": g.ride.mean() * 100,
                              "median_ride_len": g.ride_len.median()})
            res["tables"][name][half] = {(" | ".join(map(str, k)) if isinstance(k, tuple) else str(k)):
                                         {c: round(float(v), 4) for c, v in row.items()} for k, row in t.iterrows()}
            print(f"\n== {name} [{half}]"); print(t.round(4).to_string())
    json.dump(res, open(OUT.with_suffix(".json"), "w"), indent=1)
    print("filed:", OUT.with_suffix(".json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
