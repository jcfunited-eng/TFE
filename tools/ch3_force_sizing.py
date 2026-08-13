"""
ch3_force_sizing.py — does force-proportional sizing pay, in dollars?
=====================================================================

DECLARED 2026-08-13 BEFORE THE RUN. The relaxation-field pass measured
the pull monotone in z (displacement / own 20-day noise). A monotone
force law licenses exactly one parameter-free refinement of the live
fade: same events, same exits, same total capital per day — allocated
across that day's taken events IN PROPORTION TO z instead of flat.
No onset, no cap, no new constant. This pass computes what that
reweighting is worth on the decade, and what it does to the tail:

  FLAT: every event weighted 1.
  FORCE: every event weighted z (its displacement in own-noise units),
         normalized within its entry DAY (the book allocates per day).

Metrics: day-normalized weighted mean return per event-dollar, and the
worst single-day dollar outcome under each weighting at equal daily
capital. Filed as-is; shipping decision follows the numbers.

Usage:  python tools/ch3_force_sizing.py
Output: artifacts/ch4_uf/ch3_force_sizing.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_force_sizing.json")

GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)

    rows = []
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        n = len(c)
        if n < 27:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.diff(np.log(np.maximum(c, 1e-12)))
        sv = np.concatenate(([0.0], np.cumsum(v)))
        slr = np.concatenate(([0.0], np.cumsum(lr)))
        slr2 = np.concatenate(([0.0], np.cumsum(lr * lr)))
        for t in range(21, n - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < GAIN:
                continue
            vavg = (sv[t] - sv[t - 20]) / 20.0
            if vavg <= 0 or v[t] < VOL_MULT * vavg:
                continue
            m = (slr[t - 1] - slr[t - 21]) / 20.0
            var = (slr2[t - 1] - slr2[t - 21]) / 20.0 - m * m
            sd = np.sqrt(max(var, 0.0))
            if sd <= 1e-9 or not np.isfinite(lr[t - 1]):
                continue
            z = abs(lr[t - 1]) / sd
            rows.append((sym, int(d[t]), float(z),
                         100 * (1 - c[t + HOLD] / c[t])))

    ev = pd.DataFrame(rows, columns=["sym", "date", "z", "ret_short"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    ev = ev[(ev["gband"].isna()) | (ev["gband"] == 0)]
    print(f"traded events with z: {len(ev)}")

    day_flat, day_force = [], []
    for _, g in ev.groupby("date"):
        r = g["ret_short"].to_numpy(dtype=float)
        z = g["z"].to_numpy(dtype=float)
        day_flat.append(float(r.mean()))
        day_force.append(float((z * r).sum() / z.sum()))
    day_flat = np.array(day_flat)
    day_force = np.array(day_force)

    result = {
        "declared": "flat vs z-proportional daily allocation, same events,"
                    " same exits, same capital; no new constants",
        "n_events": int(len(ev)),
        "n_entry_days": int(len(day_flat)),
        "per_dollar_mean_ret_pct": {
            "flat": round(float(day_flat.mean()), 3),
            "force": round(float(day_force.mean()), 3)},
        "worst_entry_day_ret_pct": {
            "flat": round(float(day_flat.min()), 2),
            "force": round(float(day_force.min()), 2)},
        "p1_entry_day_ret_pct": {
            "flat": round(float(np.percentile(day_flat, 1)), 2),
            "force": round(float(np.percentile(day_force, 1)), 2)},
        "share_of_days_force_beats_flat_pct": round(
            100 * float((day_force > day_flat).mean()), 1),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
