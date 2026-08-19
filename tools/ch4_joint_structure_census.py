"""
ch4_joint_structure_census.py — the structures that pay, read jointly
=====================================================================

DECLARED 2026-08-19 BEFORE RESULTS (Rule 9). Joseph's instruction,
same day: grab the structures that pay and evaluate their geometries;
seeing what to AVOID matters as much as what to choose; never
single-signal the evaluations.

FRAME: fade events on the validated clean universe only
(population_universe_20260819.csv): completed close with day gain
>= 8%, volume >= 3x the trailing-20 mean, price >= $5 (the live
engine's own event law). Outcome under the LIVE exit law (bank at
first close <= 0.95x entry, anomaly at first close >= 1.20x booked
at that close however deep, else the 5th close). True gap
accounting. Split derive <= 2023-12-31 / CONFIRM 2024+.

THE JOINT STRUCTURE at the event close — eight facts from the
population reading layer, boundaries structural (presence/sign) or
self-relative (the life's own trailing two years), never fitted
across the population, and never one alone:
  deaths      extinctions in trailing 90 readings: D0 (none) / D1 (some)
  slope       trailing 90 vs prior 90 deaths: R (resuming) / Q
              (quieting) / S (steady)
  channel     any URF == 0 in trailing 90: UNBROKEN / BROKEN
  push        sign of the sum of nonzero D over trailing 45:
              UP / DN / BAL
  buzz        Rev count in trailing 45 vs the life's own trailing-504
              median of that count: B+ / B-
  strain      U* mean over trailing 10 vs own trailing-504 median:
              U+ / U-
  lock        L64 vs own trailing-504 median: L+ / L-
  depth       close >= half the prior life peak: HIGH / DEEP
              (Joseph's constant)

REPORTING: configurations with n >= 30 in the derive half — per
half: n, fade money per 100 events, wins/losses, worst event, events
below -50%. The PAY list (positive and tail-light in BOTH halves,
ranked by confirm money) and the AVOID list (negative or
tail-heavy in BOTH halves). Aggregate coverage: what share of
supply the two lists claim. Per-event rows filed for drawing.

Usage:  python tools/ch4_joint_structure_census.py
Output: artifacts/ch4_uf/ch4_joint_structure_census.json (+ events
        parquet beside it)
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
UNIVERSE = os.path.join(ROOT, "artifacts", "ch4_uf",
                        "population_universe_20260819.csv")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf",
                   "ch4_joint_structure_census.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD = 8.0, 3.0, 5.0, 5
HARVEST_X, STOP_X = 0.95, 1.20
DERIVE_END = 20231231
SELF_W = 504          # the life's own trailing two years
MIN_N = 30


def facts_at(lane: pd.DataFrame, t: int) -> dict | None:
    """Joint structure at lane index t (the event close's reading)."""
    if t < 180:
        return None
    ext = lane["ext"]
    d90, p90 = int(ext[t - 89:t + 1].sum()), int(ext[t - 179:t - 89].sum())
    urf90 = lane["urf"][t - 89:t + 1]
    D45 = lane["D"][t - 44:t + 1]
    nz = D45[D45 != 0]
    push = "BAL" if not len(nz) else ("UP" if nz.sum() > 0
                                      else "DN" if nz.sum() < 0 else "BAL")
    j0 = max(0, t - SELF_W)
    rev45 = int(lane["rev"][t - 44:t + 1].sum())
    rev_med = float(np.median(lane["rev45"][j0:t + 1]))
    u10 = float(lane["U"][t - 9:t + 1].mean())
    u_med = float(np.median(lane["U"][j0:t + 1]))
    l64 = float(lane["L64"][t])
    l_med = float(np.median(lane["L64"][j0:t + 1]))
    peak = float(lane["close"][:t].max())
    price = float(lane["close"][t])
    return {
        "deaths": "D1" if d90 else "D0",
        "slope": "R" if d90 > p90 else ("Q" if d90 < p90 else "S"),
        "channel": "BROKEN" if (urf90 <= 0).any() else "UNBROKEN",
        "push": push,
        "buzz": "B+" if rev45 > rev_med else "B-",
        "strain": "U+" if u10 > u_med else "U-",
        "lock": "L+" if l64 > l_med else "L-",
        "depth": "HIGH" if price >= 0.5 * peak else "DEEP",
    }


def main() -> None:
    symbols = set(pd.read_csv(UNIVERSE)["Symbol"].astype(str))
    store = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    store = store[store["Symbol"].isin(symbols)]
    store["day"] = store["Date"].dt.strftime("%Y%m%d").astype(int)

    rows = []
    n_events = 0
    for sym, sub in store.groupby("Symbol", sort=False):
        sub = sub.sort_values("Date")
        c = sub["Close"].to_numpy(dtype=float)
        v = sub["Volume"].to_numpy(dtype=float)
        d = sub["day"].to_numpy()
        if len(c) < 240 + HOLD:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        ev_idx = []
        for t in range(21, len(c) - HOLD):
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            ev_idx.append(t)
        if not ev_idx:
            continue
        lp = os.path.join(LANES, f"{sym}.parquet")
        if not os.path.exists(lp):
            continue
        lf = pd.read_parquet(lp)
        date_ix = {dt: i for i, dt in enumerate(lf["date"])}
        D = lf["D_k"].to_numpy(dtype=float)
        rev = lf["Rev_k"].to_numpy(dtype=float)
        rev45 = pd.Series(rev).rolling(45, min_periods=1).sum().to_numpy()
        nzmask = D != 0
        l64 = np.zeros(len(D))
        for i in range(len(D)):
            w = D[max(0, i - 63):i + 1]
            nzw = w[w != 0]
            l64[i] = abs(nzw.sum()) / max(1, len(nzw))
        lane = {"ext": lf["extinction"].to_numpy(dtype=float),
                "urf": lf["URF"].to_numpy(),
                "D": D, "rev": rev, "rev45": rev45,
                "U": lf["U_star_k"].to_numpy(),
                "L64": l64, "close": lf["close"].to_numpy()}
        for t in ev_idx:
            day_s = f"{d[t] // 10000:04d}-{(d[t] // 100) % 100:02d}-{d[t] % 100:02d}"
            li = date_ix.get(day_s)
            if li is None:
                continue
            fx = facts_at(lane, li)
            if fx is None:
                continue
            entry = c[t]
            exit_px, status = c[t + HOLD], "TIME"
            for k in range(1, HOLD + 1):
                if c[t + k] <= HARVEST_X * entry:
                    exit_px, status = c[t + k], "HARVEST"
                    break
                if c[t + k] >= STOP_X * entry:
                    exit_px, status = c[t + k], "STOP"
                    break
            cfg = " ".join(fx[k] for k in ("deaths", "slope", "channel",
                                           "push", "buzz", "strain",
                                           "lock", "depth"))
            rows.append({"sym": sym, "date": int(d[t]), "config": cfg,
                         **fx, "ret": 100 * (entry - exit_px) / entry,
                         "status": status})
            n_events += 1
    ev = pd.DataFrame(rows)
    ev.to_parquet(OUT.replace(".json", "_events.parquet"))
    print(f"events on the clean universe: {n_events}")

    def ledger(sub: pd.DataFrame) -> dict:
        r = sub["ret"]
        return {"n": int(len(sub)),
                "money_per_100ev": round(100 * float(r.sum()) / len(sub), 1),
                "wins_losses": f"{int((r > 0).sum())}W/{int((r < 0).sum())}L",
                "worst_pct": round(float(r.min()), 1),
                "below_-50": int((r < -50).sum())}

    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    table = {}
    for cfg, dsub in derive.groupby("config"):
        if len(dsub) < MIN_N:
            continue
        csub = confirm[confirm["config"] == cfg]
        table[cfg] = {"derive": ledger(dsub),
                      "confirm": ledger(csub) if len(csub) else {"n": 0}}
    pay, avoid = [], []
    for cfg, t in table.items():
        dv, cf = t["derive"], t["confirm"]
        if cf.get("n", 0) < 10:
            continue
        d_ok = dv["money_per_100ev"] > 0 and dv["below_-50"] == 0
        c_ok = cf["money_per_100ev"] > 0 and cf["below_-50"] == 0
        d_bad = dv["money_per_100ev"] <= 0 or dv["below_-50"] > 0
        c_bad = cf["money_per_100ev"] <= 0 or cf["below_-50"] > 0
        if d_ok and c_ok:
            pay.append((cf["money_per_100ev"], cfg))
        elif d_bad and c_bad:
            avoid.append((cf["money_per_100ev"], cfg))
    pay.sort(reverse=True)
    avoid.sort()
    result = {
        "declared": "frame, eight joint facts, self-relative boundaries, "
                    "split and both lists' criteria in the docstring "
                    "before results",
        "events": {"total": n_events, "derive": len(derive),
                   "confirm": len(confirm)},
        "configs_with_n>=30_derive": len(table),
        "PAY_both_halves": [
            {"config": c, **{"derive": table[c]["derive"],
                             "confirm": table[c]["confirm"]}}
            for _, c in pay],
        "AVOID_both_halves": [
            {"config": c, **{"derive": table[c]["derive"],
                             "confirm": table[c]["confirm"]}}
            for _, c in avoid],
        "coverage": {
            "pay_share_of_confirm_supply": round(sum(
                table[c]["confirm"]["n"] for _, c in pay)
                / max(1, len(confirm)), 3),
            "avoid_share_of_confirm_supply": round(sum(
                table[c]["confirm"]["n"] for _, c in avoid)
                / max(1, len(confirm)), 3)},
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1)[:4000])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
