"""CH2 gate-transition census — SEEING at scale, declared 2026-09-30 before running.

Joe: "the resolution was daily — and there are the prefilters for the Non
tradables so it's not fair to make you look at them all — and there is a
'resolution' consideration for D_k for tickers at market cap and price
points that alter what volatility looks like i.e. the Smooth Glass
conundrum." And: "there will be a pattern for when the price goes up and
the price goes down."

WHAT THIS IS: a count, not a rule. For every gate the production chain
draws on every tradable name, record what came BEFORE the gate (knowable
at the boundary) and what the price did ACROSS the gate. Tabulate.

UNIVERSE (HIS prefilters): the live CH2 entry pool — asset_type stock and
price x avg volume >= $2M, pulled from production 2026-09-30 (3,755 names,
artifacts/ch2_life/universe_tradable_20260930.csv) — intersected with the
store, >= 1,000 daily closes.

RESOLUTION (HIS: per ticker by size/price; MINE: the setting): tau_D per
ticker = 3.77 x that ticker's median daily deviation D(t) over its life.
Whole-life chain, so tau and psi use the life (the kernel's own psi is
normalized over all gates). This is a seeing pass, not the causal test.
Kernel unmodified; tau_D set in this process only.

BEFORE (context at gate k's first bar, all from gates < k and the price tape):
  prev_kind   SHOCK (gate k-1 is 1 bar and VOLATILE) | SHORT (<= 20 bars)
              | MID (21-60) | LONG (> 60)
  jump        price change from the last close of gate k-1 to the first
              close of gate k: UP (> +3%), DOWN (< -3%), FLAT
  prev_move   price change across gate k-1: SHARP_UP (> +15%), UP, FLAT
              (within +-3%), DOWN, SHARP_DOWN (< -15%)
  shock_run   number of consecutive 1-bar VOLATILE gates ending at k-1
  prev_g, prev_regime, prev_psi, prev_U*, prev_R   the tuple of gate k-1
RIDE (the trader's clock): a boundary at bar i is knowable at close i+1,
  because kappa[i] uses close[i+1]. Enter at close i+1. The gate's end e is
  knowable at close e+2. Exit at close e+2. `jump` = close[i+1]/close[i-1].
  Also the 20-session return from close i+1 (fixed horizon).
HALVES: gate start < 2024-01-01 (seen) / >= 2024-01-01 (confirmed).
OUTPUT: artifacts/ch4_uf/ch2_gate_transition_census.parquet (every gate)
  and .json (tables). Read; do not select on it.
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
MIN_BARS = 1000
CONFIRM_FROM = np.datetime64("2024-01-01")
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_gate_transition_census"
UNIVERSE = ROOT / "artifacts" / "ch2_life" / "universe_tradable_20260930.csv"


def one_symbol(task):
    symbol, dates, closes = task
    import uf_core.config as cfg
    from tools.ch2_draw_life import chain
    from tools.ch2_tuples_over_time import own_resolution
    closes = np.asarray(closes, dtype=float)
    tau, typical = own_resolution(closes, C)
    cfg.KERNEL_THRESHOLDS.tau_D = float(tau)
    series = pd.Series(closes, index=pd.to_datetime(dates))
    sev, gates, interps, res, dsf = chain(series)
    n = len(closes)
    rows = []
    shock_run = 0
    # The trader's clock: a boundary at bar i is knowable at close i+1 (kappa[i]
    # uses close[i+1]). Enter at close i+1; the gate's end e is knowable at
    # close e+2 (its boundary is at e+1). Exit at close e+2. Everything below
    # is measured on that clock, so every number here is one a trader gets.
    for k in range(1, len(gates)):
        g, p = gates[k], gates[k - 1]
        i, e = g.start_idx, g.end_idx
        if i + 1 >= n or e + 2 >= n:
            continue
        pi, pr = interps[k - 1], res[k - 1]
        plen = p.end_idx - p.start_idx + 1
        prev_shock = plen == 1 and pi.regime == "VOLATILE"
        shock_run = shock_run + 1 if prev_shock else 0
        prev_kind = "SHOCK" if prev_shock else "SHORT" if plen <= 20 else "MID" if plen <= 60 else "LONG"
        jump = closes[i + 1] / closes[i - 1] - 1.0            # the shock: two closes around the boundary
        pmove = closes[p.end_idx] / closes[p.start_idx] - 1.0  # price across the previous gate
        ride = closes[e + 2] / closes[i + 1] - 1.0            # enter close i+1, exit close e+2
        r20 = closes[i + 21] / closes[i + 1] - 1.0 if i + 21 < n else np.nan
        rows.append((symbol, str(dates[i])[:10], k, tau, prev_kind, plen, shock_run,
                     jump, pmove, int(pr.g_k), pi.regime, float(pi.psi_k), float(dsf[k - 1].U_star_k), float(pr.R_k),
                     float(pi.w_k), int(dsf[k - 1].D_k), ride, e - i + 1, r20, False))
    return symbol, rows


def band(x, lo, hi, names):
    return np.where(x > hi, names[0], np.where(x < lo, names[2], names[1]))


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
    print(f"[census] tradable in store with >= {MIN_BARS} bars: {len(symbols)}; workers {args.workers}", flush=True)
    tasks = [(s, g.Date.values.astype("datetime64[D]"), g.Close.values)
             for s, g in store[store.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).groupby("Symbol")]
    del store
    t0 = time.time()
    rows_all, done = [], 0
    with Pool(args.workers) as pool:
        for symbol, rows in pool.imap_unordered(one_symbol, tasks, chunksize=4):
            rows_all.extend(rows); done += 1
            if done % 250 == 0:
                print(f"[census] {done}/{len(tasks)} symbols, {len(rows_all)} gates, {time.time() - t0:.0f}s", flush=True)
    cols = ["symbol", "date", "k", "tau", "prev_kind", "prev_len", "shock_run", "jump", "prev_move", "prev_g",
            "prev_regime", "prev_psi", "prev_U", "prev_R", "prev_w", "prev_D", "ride", "len", "r20", "open_ended"]
    ev = pd.DataFrame(rows_all, columns=cols)
    ev.to_parquet(OUT.with_suffix(".parquet"), index=False)
    ev = ev[~ev.open_ended]                      # the last gate of a life has no end yet
    ev["jump_dir"] = band(ev.jump.values, -0.03, 0.03, ("UP", "FLAT", "DOWN"))
    pm = ev.prev_move.values
    ev["prev_move_band"] = np.select([pm > 0.15, pm > 0.03, pm >= -0.03, pm >= -0.15],
                                     ["SHARP_UP", "UP", "FLAT", "DOWN"], "SHARP_DOWN")
    ev["half"] = np.where(pd.to_datetime(ev.date) < pd.Timestamp(CONFIRM_FROM), "seen", "confirm")
    ev["shock_run_capped"] = np.minimum(ev.shock_run, 5)
    ev["all"] = "all"

    def table(keys):
        out = {}
        for half in ("seen", "confirm"):
            h = ev[ev.half == half]
            grp = h.groupby(keys)
            t = pd.DataFrame({"n": grp.size(),
                              "up_share": grp.ride.apply(lambda s: float((s > 0).mean())),
                              "mean_ride_pct": grp.ride.mean() * 100,
                              "median_len": grp.len.median(),
                              "up_share_20d": grp.r20.apply(lambda s: float((s.dropna() > 0).mean())),
                              "mean_r20_pct": grp.r20.mean() * 100})
            out[half] = {(" | ".join(map(str, idx)) if isinstance(idx, tuple) else str(idx)):
                         {c: (round(float(v), 4) if isinstance(v, (float, np.floating)) else int(v)) for c, v in row.items()}
                         for idx, row in t.iterrows()}
        return out

    res = {"declared": "universe, resolution, context and outcome definitions in the docstring, before results",
           "universe": len(symbols), "gates": int(len(ev)),
           "by_prev_kind": table(["prev_kind"]),
           "by_prev_kind_and_jump": table(["prev_kind", "jump_dir"]),
           "by_prev_move": table(["prev_move_band"]),
           "by_prev_kind_and_prev_move": table(["prev_kind", "prev_move_band"]),
           "by_shock_run": table(["shock_run_capped"]),
           "by_prev_g": table(["prev_g"]),
           "by_prev_regime": table(["prev_regime"]),
           "all": table(["all"])}
    json.dump(res, open(OUT.with_suffix(".json"), "w"), indent=1)
    pd.set_option("display.width", 220)
    for name in ("all", "by_prev_kind", "by_prev_kind_and_jump", "by_prev_move", "by_shock_run", "by_prev_g", "by_prev_regime"):
        for half in ("seen", "confirm"):
            print(f"\n== {name} [{half}]")
            print(pd.DataFrame(res[name][half]).T.to_string())
    print("filed:", OUT.with_suffix(".json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
