"""CH2 direction episodes — declared 2026-10-01 BEFORE running.

Joe: "there will be a pattern for when the price goes up and the price
goes down." Seen first (artifacts/ch2_life/MTD_tau0.1*.png, HRB): with the
FINISHED stretch values, +1 stretches ride rises and -1 stretches ride
falls; with the DAY-BY-DAY reading (each day's own prefix) the direction
agrees with the finished value on 72% of bars for MTD and lags on several
of the largest rises. Only the day-by-day reading exists on the day.

THE RULE UNDER TEST (causal, episode-based, no fixed window):
  Each trading day, run the production chain on the history through that
  day; read the last gate's D_k. LONG episode: enter at the close of the
  first day D_k = +1, exit at the close of the first later day D_k != +1.
  SHORT-SIDE mirror: episodes of D_k = -1 (price change over the
  episode; a negative change is a "win" for the mirror).
  Nothing else — no basin, no averages, no other field.

ARMS: tau_D in {0.20 (live), 0.10, 0.05}, set in this offline process.
UNIVERSE: operating companies with >= 1,000 closes, every 40th (~70).
PERIOD: episodes starting 2021-01-01 or later; halves <= 2023 / 2024+.
REPORT per arm and half: long episodes n, win rate, mean/median return,
  median length in sessions, sum of episode returns; the -1 mirror the
  same; and buy-and-hold over the same period for the same names as the
  null (the market's drift is what "always long" earns).
PASS BAR, declared: at an arm, long-while-+1 episodes win > 50% in BOTH
  halves with n >= 300 each AND the -1 episodes' mean return is negative
  in both halves AND long-while-+1 total beats buy-and-hold in both
  halves. Filed either way. Costs not modelled; close-only; survivorship
  not handled; each day's chain run is the production adapter unmodified.
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

ARMS = (0.20, 0.10, 0.05)
START = "2021-01-01"
CONFIRM_FROM = "2024-01-01"
MIN_BARS = 1000
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_direction_episodes.json"


def daily_direction(close: pd.Series, start_idx: int) -> np.ndarray:
    from tools.ch2_draw_life import chain
    d = np.full(len(close), np.nan)
    for i in range(start_idx, len(close)):
        _, _, _, _, dsf = chain(close.iloc[: i + 1])
        if dsf:
            d[i] = dsf[-1].D_k
    return d


def episodes(d: np.ndarray, closes: np.ndarray, dates, value: float):
    out = []
    i, n = 0, len(d)
    while i < n:
        if d[i] == value:
            j = i + 1
            while j < n and d[j] == value:
                j += 1
            if j < n:                       # exit at the close of the first day it is not `value`
                out.append((str(dates[i])[:10], closes[j] / closes[i] - 1.0, j - i))
            i = j
        else:
            i += 1
    return out


def one_symbol(task):
    symbol, dates, closes = task
    import uf_core.config as cfg
    dates = np.asarray(dates)
    closes = np.asarray(closes, dtype=float)
    series = pd.Series(closes, index=pd.to_datetime(dates))
    start_idx = int(np.searchsorted(dates, np.datetime64(START)))
    rows = []
    for tau in ARMS:
        cfg.KERNEL_THRESHOLDS.tau_D = float(tau)
        d = daily_direction(series, start_idx)
        for value, kind in ((1.0, "LONG_PLUS1"), (-1.0, "MINUS1")):
            for date, ret, length in episodes(d, closes, dates, value):
                rows.append((symbol, tau, kind, date, ret, length))
    bh = (str(dates[start_idx])[:10], closes[-1] / closes[start_idx] - 1.0,
          closes[int(np.searchsorted(dates, np.datetime64(CONFIRM_FROM)))] / closes[start_idx] - 1.0)
    return symbol, rows, bh


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=40)
    args = ap.parse_args()
    types = json.loads((ROOT / "artifacts" / "ch6_harvest" / "ticker_types.json").read_text())
    stocks = {s for s, t in types.items() if t in ("CS", "ADRC")}
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    store = store[store.Symbol.isin(stocks)]
    counts = store.groupby("Symbol").size()
    symbols = sorted(counts[counts >= MIN_BARS].index)[:: args.every]
    print(f"[episodes] universe {len(symbols)}; arms {ARMS}; workers {args.workers}", flush=True)
    tasks = [(s, g.Date.values.astype("datetime64[D]"), g.Close.values)
             for s, g in store[store.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).groupby("Symbol")]
    del store
    t0 = time.time()
    rows_all, bh_all, done = [], {}, 0
    with Pool(args.workers) as pool:
        for symbol, rows, bh in pool.imap_unordered(one_symbol, tasks, chunksize=1):
            rows_all.extend(rows); bh_all[symbol] = bh; done += 1
            if done % 10 == 0:
                print(f"[episodes] {done}/{len(tasks)} symbols, {len(rows_all)} episodes, {time.time() - t0:.0f}s", flush=True)
    ev = pd.DataFrame(rows_all, columns=["symbol", "tau", "kind", "date", "ret", "length"])
    ev.to_parquet(OUT.with_suffix(".parquet"), index=False)
    bh = pd.DataFrame([(s, v[0], v[1], v[2]) for s, v in bh_all.items()], columns=["symbol", "start", "bh_total", "bh_to_2024"])
    res = {"declared": "rule, arms, universe, timing, null and pass bar in the docstring, before results",
           "universe": len(symbols), "start": START, "confirm_from": CONFIRM_FROM,
           "buy_and_hold": {"mean_total_pct": round(100 * float(bh.bh_total.mean()), 2),
                            "mean_to_2024_pct": round(100 * float(bh.bh_to_2024.mean()), 2),
                            "share_positive_total": round(float((bh.bh_total > 0).mean()), 3)},
           "arms": {}}
    for tau in ARMS:
        arm = {}
        for kind in ("LONG_PLUS1", "MINUS1"):
            for half, g in (("derive", ev[(ev.tau == tau) & (ev.kind == kind) & (ev.date < CONFIRM_FROM)]),
                            ("confirm", ev[(ev.tau == tau) & (ev.kind == kind) & (ev.date >= CONFIRM_FROM)])):
                arm[f"{kind}_{half}"] = {
                    "n": int(len(g)),
                    "win_rate": round(float((g.ret > 0).mean()), 3) if len(g) else None,
                    "mean_ret_pct": round(100 * float(g.ret.mean()), 2) if len(g) else None,
                    "median_ret_pct": round(100 * float(g.ret.median()), 2) if len(g) else None,
                    "median_len": int(g.length.median()) if len(g) else None,
                    "sum_ret_per_symbol_pct": round(100 * float(g.ret.sum()) / max(1, len(symbols)), 1) if len(g) else None}
        lp, lc = arm["LONG_PLUS1_derive"], arm["LONG_PLUS1_confirm"]
        mp, mc = arm["MINUS1_derive"], arm["MINUS1_confirm"]
        bh_d, bh_c = res["buy_and_hold"]["mean_to_2024_pct"], res["buy_and_hold"]["mean_total_pct"] - res["buy_and_hold"]["mean_to_2024_pct"]
        arm["PASS"] = bool(all(x["n"] >= 300 and (x["win_rate"] or 0) > 0.50 for x in (lp, lc))
                           and all((x["mean_ret_pct"] or 0) < 0 for x in (mp, mc))
                           and (lp["sum_ret_per_symbol_pct"] or -1e9) > bh_d and (lc["sum_ret_per_symbol_pct"] or -1e9) > bh_c)
        res["arms"][str(tau)] = arm
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))
    print("filed:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
