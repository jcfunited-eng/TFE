"""CH2 resolution ladder — declared 2026-09-30 BEFORE running (Joe: "do whatever").

THE FINDING THAT PROMPTED IT (docs/CH2_OLD_BATCH_CLEARED_20260928.md):
  CH2's daily buy list is a standing label, not a moment. 26 of today's 30
  passers were passers six weeks ago; thirteen holdings have been rated
  "buy" every night since July 9. At tau_D = 0.20 the kernel registers 4–5
  structural events in 5.5 years for a typical stock, so between events
  the reading drifts and the verdict never flips. The buy date is set by
  when cash is free, not by anything the stock did.

WHAT IS MEASURED — the PRODUCTION kernel, unmodified code
  uf_core L0–L4 through the production adapter (compute_uf_structural_state)
  on daily closes, exactly as CH2 is fed. The only thing varied is the
  segmentation threshold tau_D, set per arm in this offline process. The
  V3 basin math is imported from tfe_l5_baseline (constants included) and
  the live CH2 gate is applied unchanged:
    Accumulate argmax, basin >= 0.15, break_agreement < 0.20, B_k > -0.50,
    price >= 5, bar_count >= 21.

ARMS (fixed, no re-tuning after results): tau_D in {0.20 (live), 0.10, 0.05, 0.02}

UNIVERSE: operating companies (ticker_types CS/ADRC) in ch4_live_store with
  >= 1,000 daily closes; sorted; every 10th symbol. Deterministic, ~500 names.
  The store is the current roster — survivorship is NOT handled; say so.

TWO ENTRY KINDS, same gate, same forward window
  EVENT  — the moment: a gate boundary forms at bar t (knowable at the
           close of t+1 because kappa reads t+1); run the chain on the
           prefix through t+1; if the gate passes, enter at close t+1.
  LABEL  — what CH2 does now: every 10th session from 2021-01-01, run the
           chain on the prefix through that day; if the gate passes,
           enter at that close.
  Forward: 20-session return from the entry close (also 5-session). No
  costs. Close-only. Both halves: derive <= 2023-12-31, confirm 2024+.

REPORT per arm: median events per stock-year; for EVENT and LABEL, per
  half: n, win rate (ret20 > 0), mean ret20, mean ret5.

PASS BAR, declared: an arm is worth carrying forward only if EVENT beats
  LABEL in win rate in BOTH halves at that arm AND the median stock sees
  >= 4 events a year there. The live arm (0.20) cannot pass the second
  test — that is the point. Results are filed whichever way they fall.
Usage: nice -n 15 python3 tools/ch2_resolution_ladder.py [--workers 6] [--every 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ARMS = (0.20, 0.10, 0.05, 0.02)
START = "2021-01-01"
CONFIRM_FROM = "2024-01-01"
LABEL_STEP = 10
HOLD = 20
MIN_BARS = 1000
OUT = ROOT / "artifacts" / "ch4_uf" / "ch2_resolution_ladder.json"


def basin_gate(f: dict, price: float, bar_count: int) -> tuple[bool, str]:
    """The live CH2 gate on one reading. Returns (passes, reason)."""
    import tfe_l5_baseline as L
    need = ("S_UF", "R_UF", "D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k")
    v = {}
    for k in need:
        x = f.get(k)
        if x is None or not np.isfinite(float(x)):
            return False, "incomplete"
        v[k] = float(x)
    if bar_count < 21:
        return False, "bars"
    if price < 5.0:
        return False, "price"
    M_hat = min(1.0, max(-1.0, v["M_k"]))
    sv, rv = v["S_UF"] - v["U_star_k"], v["R_UF"] - v["U_star_k"]
    s_pos, r_pos = max(sv, 0.0), max(rv, 0.0)
    core = min(s_pos, r_pos)
    edge = max(s_pos, r_pos) - core
    live = core + L._BETA * edge
    contested = (1.0 - L._BETA) * edge
    balance = core / (core + edge + 1e-12)
    rupture = max(-max(sv, rv), 0.0)
    D_non, D_adv = (1.0 + v["D_k"]) / 2.0, max(-v["D_k"], 0.0)
    M_cont, M_bend = (1.0 + M_hat) / 2.0, (1.0 - M_hat) / 2.0
    motion = (L._MOTION_WEIGHT * D_non ** L._MOTION_POWER
              + (1.0 - L._MOTION_WEIGHT) * M_cont ** L._MOTION_POWER) ** (1.0 / L._MOTION_POWER)
    adverse = D_adv * M_bend
    reversal = v["R_rev_k"] * (1.0 - balance) ** L._REVERSAL_BALANCE_POWER
    carry = (-v["B_k"]) * v["R_rev_k"] * (1.0 - balance) ** L._CARRY_BALANCE_POWER * (1.0 - adverse)
    burden = L._BURDEN_SCALE * (v["C_k"] / (1.0 + v["C_k"])) * (v["P_k"] / (1.0 + v["P_k"]))
    brk = max(adverse, reversal, carry)
    acc = live * motion * (1.0 - v["R_rev_k"]) * (1.0 - adverse) * (1.0 - burden)
    hold = (contested * (1.0 - brk) + live * v["R_rev_k"] * balance
            + live * (1.0 - v["R_rev_k"]) * ((1.0 - motion) * (1.0 - adverse) + motion * burden))
    avoid = rupture + (live + contested) * brk
    mx = max(acc, hold, avoid)
    near = [abs(mx - x) <= L._V3_TIE_EPS for x in (acc, hold, avoid)]
    if sum(near) > 1 or not near[0]:
        return False, "argmax"
    if acc < 0.15:
        return False, "basin"
    if brk >= 0.20:
        return False, "break"
    if v["B_k"] <= -0.50:
        return False, "carry"
    return True, "pass"


def reading(close_prefix: pd.Series) -> dict:
    from uf_core.uf_structural_engine import compute_uf_structural_state
    st = compute_uf_structural_state(close_prefix)
    f = dict(st.level5)
    f["S_UF"] = st.level4.get("S_UF")
    f["R_UF"] = st.level4.get("R_UF")
    return f


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
    for tau in ARMS:
        cfg.KERNEL_THRESHOLDS.tau_D = float(tau)
        sev = compute_sev_series(pd.DataFrame({"Close": closes}, index=series.index))
        gates = segment_gates(sev)
        boundaries = [g.start_idx for g in gates[1:]]          # bar t where a new gate starts
        recent = [t for t in boundaries if t >= start_idx]
        rates[str(tau)] = len(recent) / years
        # EVENT: boundary at t is knowable at close t+1; enter at close t+1
        for t in recent:
            e = t + 1
            if e + HOLD >= n:
                continue
            f = reading(series.iloc[: e + 1])
            ok, why = basin_gate(f, closes[e], e + 1)
            if not ok:
                continue
            rows.append((symbol, tau, "EVENT", str(dates[e])[:10],
                         closes[e + 5] / closes[e] - 1.0, closes[e + HOLD] / closes[e] - 1.0))
        # LABEL: every 10th session, enter at that close if the standing reading passes
        for i in range(start_idx, n - HOLD, LABEL_STEP):
            f = reading(series.iloc[: i + 1])
            ok, why = basin_gate(f, closes[i], i + 1)
            if not ok:
                continue
            rows.append((symbol, tau, "LABEL", str(dates[i])[:10],
                         closes[i + 5] / closes[i] - 1.0, closes[i + HOLD] / closes[i] - 1.0))
    return symbol, rates, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--every", type=int, default=10)
    args = ap.parse_args()
    types = json.loads((ROOT / "artifacts" / "ch6_harvest" / "ticker_types.json").read_text())
    stocks = {s for s, t in types.items() if t in ("CS", "ADRC")}
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Date", "Symbol", "Close"])
    store = store[store.Symbol.isin(stocks)]
    counts = store.groupby("Symbol").size()
    symbols = sorted(counts[counts >= MIN_BARS].index)[:: args.every]
    print(f"[ladder] universe {len(symbols)} of {len(counts)} operating companies with >= {MIN_BARS} closes; arms {ARMS}; workers {args.workers}", flush=True)
    tasks = []
    for s, g in store[store.Symbol.isin(symbols)].sort_values(["Symbol", "Date"]).groupby("Symbol"):
        tasks.append((s, g.Date.values.astype("datetime64[D]"), g.Close.values))
    del store
    t0 = time.time()
    rates_all, rows_all, done = {}, [], 0
    with Pool(args.workers) as pool:
        for symbol, rates, rows in pool.imap_unordered(one_symbol, tasks, chunksize=2):
            rates_all[symbol] = rates
            rows_all.extend(rows)
            done += 1
            if done % 25 == 0:
                print(f"[ladder] {done}/{len(tasks)} symbols, {len(rows_all)} entries, {time.time() - t0:.0f}s", flush=True)
    ev = pd.DataFrame(rows_all, columns=["symbol", "tau", "kind", "date", "ret5", "ret20"])
    ev.to_parquet(OUT.with_suffix(".parquet"), index=False)
    res = {"declared": "arms, universe, timing, gate and pass bar in the docstring, before results",
           "universe": len(symbols), "start": START, "confirm_from": CONFIRM_FROM, "hold": HOLD,
           "survivorship": "NOT handled — current store roster only", "arms": {}}
    for tau in ARMS:
        r = pd.Series({s: v[str(tau)] for s, v in rates_all.items()})
        arm = {"events_per_stock_year_median": round(float(r.median()), 2),
               "events_per_stock_year_p25_p75": [round(float(r.quantile(.25)), 2), round(float(r.quantile(.75)), 2)],
               "stocks_under_4_per_year": int((r < 4).sum())}
        for kind in ("EVENT", "LABEL"):
            d = ev[(ev.tau == tau) & (ev.kind == kind)]
            for half, g in (("derive", d[d.date < CONFIRM_FROM]), ("confirm", d[d.date >= CONFIRM_FROM])):
                arm[f"{kind}_{half}"] = {"n": int(len(g)),
                                         "win_rate_20d": round(float((g.ret20 > 0).mean()), 3) if len(g) else None,
                                         "mean_ret20_pct": round(100 * float(g.ret20.mean()), 2) if len(g) else None,
                                         "mean_ret5_pct": round(100 * float(g.ret5.mean()), 2) if len(g) else None}
        ok_rate = arm["events_per_stock_year_median"] >= 4
        beats = all((arm[f"EVENT_{h}"]["win_rate_20d"] or 0) > (arm[f"LABEL_{h}"]["win_rate_20d"] or 0)
                    and arm[f"EVENT_{h}"]["n"] >= 100 for h in ("derive", "confirm"))
        arm["PASS"] = bool(ok_rate and beats)
        res["arms"][str(tau)] = arm
    OUT.parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print(json.dumps(res, indent=1))
    print("filed:", OUT, "and", OUT.with_suffix(".parquet"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
