"""CH2 event direction — declared 2026-10-01 BEFORE running.

FOLLOWS tools/ch2_resolution_ladder.py, which showed the live buy gate (V3
basin on the adapter's lifetime means) says "buy" only when the kernel has
registered almost nothing: at tau_D 0.05 and 0.02 it produced ZERO buys
across 142 companies and 5.7 years; at 0.20, 67 of its 76 buys were one
stock. The dial cannot be turned with that gate in place.

THE QUESTION: does the kernel's OWN reading at the moment an event forms
say anything about the next 20 sessions? No averages, no basin, no
checklist — the last L4 tuple of the production chain, read at the
kernel's own clock.

  At a gate boundary at bar t (knowable at close t+1), run the production
  chain on the prefix through t+1 and take the latest tuple's D_k (the
  thresholded change of gated resonance: +1 / 0 / -1). Enter at close t+1.
  Score the 20-session and 5-session return.

ARMS: tau_D in {0.20 (live), 0.10, 0.05}. Universe: the ladder's 142.
NULL: coin flip. Also the standing-label read (every 10th session, same
D_k of the latest tuple) for comparison at each arm.

PASS BAR, declared: at an arm with median >= 4 events/stock-year, D_k=+1
events show win rate > 0.50 in BOTH halves with n >= 200 each, AND the
D_k=+1 minus D_k=-1 spread in mean 20-session return is positive in both
halves. Anything less: the kernel's raw direction at its event clock is
not a timing signal at daily resolution, and that is filed too.
Costs not modelled; close-only; survivorship not handled.
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
from tools.ch2_resolution_ladder import reading, START, CONFIRM_FROM, HOLD, MIN_BARS  # noqa: E402

ARMS = (0.20, 0.10, 0.05)
LABEL_STEP = 10
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_event_direction.json"


def one_symbol(task):
    symbol, dates, closes = task
    import uf_core.config as cfg
    from uf_core.layer0 import compute_sev_series
    from uf_core.layer1 import segment_gates
    dates = np.asarray(dates)
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    series = pd.Series(closes, index=pd.to_datetime(dates))
    start_idx = int(np.searchsorted(dates, np.datetime64(START)))
    years = max(1e-9, (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[start_idx])).days / 365.25)
    rows, rates = [], {}

    def rec(kind, tau, e, f):
        d = f.get("D_k")
        if d is None or not np.isfinite(float(d)):
            return
        rows.append((symbol, tau, kind, str(dates[e])[:10], int(np.sign(float(d))),
                     float(f.get("M_k") or 0.0), float(f.get("B_k") or 0.0), float(f.get("U_star_k") or 0.0),
                     int(f.get("gate_count") or 0),
                     closes[e + 5] / closes[e] - 1.0, closes[e + HOLD] / closes[e] - 1.0))

    for tau in ARMS:
        cfg.KERNEL_THRESHOLDS.tau_D = float(tau)
        sev = compute_sev_series(pd.DataFrame({"Close": closes}, index=series.index))
        gates = segment_gates(sev)
        recent = [g.start_idx for g in gates[1:] if g.start_idx >= start_idx]
        rates[str(tau)] = len(recent) / years
        for t in recent:
            e = t + 1
            if e + HOLD >= n or closes[e] < 5.0:
                continue
            rec("EVENT", tau, e, reading(series.iloc[: e + 1]))
        for i in range(start_idx, n - HOLD, LABEL_STEP):
            if closes[i] < 5.0:
                continue
            rec("LABEL", tau, i, reading(series.iloc[: i + 1]))
    return symbol, rates, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=20)
    args = ap.parse_args()
    types = json.loads((ROOT / "artifacts" / "ch6_harvest" / "ticker_types.json").read_text())
    stocks = {s for s, t in types.items() if t in ("CS", "ADRC")}
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    store = store[store.Symbol.isin(stocks)]
    counts = store.groupby("Symbol").size()
    symbols = sorted(counts[counts >= MIN_BARS].index)[:: args.every]
    print(f"[direction] universe {len(symbols)}; arms {ARMS}; workers {args.workers}", flush=True)
    tasks = [(s, g.Date.values.astype("datetime64[D]"), g.Close.values)
             for s, g in store[store.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).groupby("Symbol")]
    del store
    t0 = time.time()
    rates_all, rows_all, done = {}, [], 0
    with Pool(args.workers) as pool:
        for symbol, rates, rows in pool.imap_unordered(one_symbol, tasks, chunksize=2):
            rates_all[symbol] = rates
            rows_all.extend(rows)
            done += 1
            if done % 25 == 0:
                print(f"[direction] {done}/{len(tasks)} symbols, {len(rows_all)} readings, {time.time() - t0:.0f}s", flush=True)
    cols = ["symbol", "tau", "kind", "date", "D", "M", "B", "U", "gates", "ret5", "ret20"]
    ev = pd.DataFrame(rows_all, columns=cols)
    ev.to_parquet(OUT.with_suffix(".parquet"), index=False)
    res = {"declared": "question, arms, universe, timing, null and pass bar in the docstring, before results",
           "universe": len(symbols), "start": START, "confirm_from": CONFIRM_FROM, "hold": HOLD, "arms": {}}
    for tau in ARMS:
        r = pd.Series({s: v[str(tau)] for s, v in rates_all.items()})
        arm = {"events_per_stock_year_median": round(float(r.median()), 2)}
        for kind in ("EVENT", "LABEL"):
            for half, g in (("derive", ev[(ev.tau == tau) & (ev.kind == kind) & (ev.date < CONFIRM_FROM)]),
                            ("confirm", ev[(ev.tau == tau) & (ev.kind == kind) & (ev.date >= CONFIRM_FROM)])):
                h = {}
                for dsign, name in ((1, "up"), (0, "flat"), (-1, "down")):
                    s = g[g.D == dsign]
                    h[name] = {"n": int(len(s)),
                               "win_rate_20d": round(float((s.ret20 > 0).mean()), 3) if len(s) else None,
                               "mean_ret20_pct": round(100 * float(s.ret20.mean()), 2) if len(s) else None,
                               "mean_ret5_pct": round(100 * float(s.ret5.mean()), 2) if len(s) else None}
                h["all"] = {"n": int(len(g)), "win_rate_20d": round(float((g.ret20 > 0).mean()), 3) if len(g) else None,
                            "mean_ret20_pct": round(100 * float(g.ret20.mean()), 2) if len(g) else None}
                arm[f"{kind}_{half}"] = h
        up_d, up_c = arm["EVENT_derive"]["up"], arm["EVENT_confirm"]["up"]
        dn_d, dn_c = arm["EVENT_derive"]["down"], arm["EVENT_confirm"]["down"]
        ok = (arm["events_per_stock_year_median"] >= 4
              and all(x["n"] >= 200 and (x["win_rate_20d"] or 0) > 0.50 for x in (up_d, up_c))
              and all((u["mean_ret20_pct"] or 0) > (d["mean_ret20_pct"] or 0) for u, d in ((up_d, dn_d), (up_c, dn_c)) if d["n"]))
        arm["PASS"] = bool(ok)
        res["arms"][str(tau)] = arm
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))
    print("filed:", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
