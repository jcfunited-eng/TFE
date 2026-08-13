"""
ch3_relaxation_field.py — the relaxation law, created from the field
====================================================================

DECLARED 2026-08-13 BEFORE THE RUN. One pass, no scans, filed as-is.

This is a CREATION, not an audit. The existing fade is a price screen
(+8%, 3x volume) that happens to work. The physics underneath it, made
explicit and testable, is a RESTORING FORCE in the herd frame:

    Tension exists when a stock is displaced and its own herd is not.
    Displacement with the herd = repricing (no anchor, no trade —
    measured: coin flip). Displacement against a calm herd = a
    stretched spring; it relaxes back over ~5 sessions (measured:
    +2.5%/ev on the up side). A force law has no sign preference and
    no dollar units. Therefore two claims nobody has measured:

  LAW A (symmetry): a stock CRATERING while its herd stays calm
    relaxes UP. Event: day move <= -8%, volume >= 3x trailing 20-day
    mean, close >= $5. Herd condition (mirror of v1.1's): tradeable
    when the herd is NOT fearful — greed band g >= 1, or no herd row
    (no evidence of participation, v1.1's own convention). g == 0
    (the cohort's greed at its own low band — the herd is falling
    too) = the anchor itself moved: refused, predicted no edge.
    Entry LONG at event close, exit at the 5th session close (the
    clock defended earlier tonight). Control: unconditioned crash
    longs (v1 measured these lose; must reproduce).

  LAW B (scale-freedom): the true displacement unit is the stock's
    own structural noise, not a percentage. z = |day log-move| /
    (trailing 20-day std of daily log-moves, through yesterday).
    Candidate event law z >= 3 (outside own noise — the onset is
    a priori, NOT fitted), same volume/price/herd conditions, both
    sides. Head-to-head vs the dollar form on the same metrics.
    z-bucket table is DIAGNOSTIC ONLY (is relaxation monotone in
    structural displacement, i.e. law-shaped?) — declared now: no
    threshold will be chosen from that table.

METRICS (same as every pass tonight): per-event mean, median, wr,
p1/min, by-year, and for LAW A the SUPPLY it adds (events/day,
fraction of days with >= 1 tradeable event) — the starvation cure is
part of the claim. Store: ch4_live_store.parquet; herd frame
herd_state_daily.parquet; events cut at the frame end 2026-03-24;
full 5-session forward window required.

Usage:  python tools/ch3_relaxation_field.py
Output: artifacts/ch4_uf/ch3_relaxation_field.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_relaxation_field.json")

GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
HOLD = 5
Z_ONSET = 3.0
HERD_END = 20260324
ZBUCKETS = [(3, 4), (4, 5), (5, 6), (6, 8), (8, 12), (12, 1e9)]


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)

    rows = []
    all_days = set()
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        n = len(c)
        if n < 27:
            continue
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.diff(np.log(np.maximum(c, 1e-12)))  # lr[i] = move into bar i+1
        sv = np.concatenate(([0.0], np.cumsum(v)))
        slr = np.concatenate(([0.0], np.cumsum(lr)))
        slr2 = np.concatenate(([0.0], np.cumsum(lr * lr)))
        for t in range(21, n - HOLD):
            if d[t] > HERD_END:
                break
            all_days.add(int(d[t]))
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            vavg = (sv[t] - sv[t - 20]) / 20.0
            if vavg <= 0 or v[t] < VOL_MULT * vavg:
                continue
            move = 100 * (c[t] / c[t - 1] - 1)
            # trailing 20 log-moves THROUGH yesterday: lr[t-21 .. t-2]
            m = (slr[t - 1] - slr[t - 21]) / 20.0
            var = (slr2[t - 1] - slr2[t - 21]) / 20.0 - m * m
            sd = np.sqrt(max(var, 0.0))
            z = abs(lr[t - 1]) / sd if sd > 1e-9 else np.nan
            dollar_evt = abs(move) >= GAIN
            sigma_evt = np.isfinite(z) and z >= Z_ONSET
            if not (dollar_evt or sigma_evt):
                continue
            ret5_long = 100 * (c[t + HOLD] / c[t] - 1)
            rows.append((sym, int(d[t]), int(d[t]) // 10000,
                         1 if move > 0 else -1, move,
                         float(z) if np.isfinite(z) else -1.0,
                         dollar_evt, sigma_evt, ret5_long))

    ev = pd.DataFrame(rows, columns=["sym", "date", "year", "side", "move",
                                     "z", "dollar", "sigma", "ret5_long"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    g = ev["gband"]
    ev["up_tradeable"] = (g.isna() | (g == 0))          # v1.1's law
    ev["down_tradeable"] = (g.isna() | (g >= 1))        # LAW A mirror
    print(f"event rows: {len(ev)} (dollar {int(ev['dollar'].sum())}, "
          f"sigma {int(ev['sigma'].sum())})")

    def stats(sub, long_side, with_years=True):
        x = sub["ret5_long"].to_numpy(dtype=float)
        if not long_side:
            x = -x
        if len(x) == 0:
            return {"n": 0}
        out = {"n": int(len(x)),
               "mean_pct": round(float(x.mean()), 3),
               "median_pct": round(float(np.median(x)), 3),
               "wr_pct": round(100 * float((x > 0).mean()), 1),
               "p1_pct": round(float(np.percentile(x, 1)), 2),
               "min_pct": round(float(x.min()), 2)}
        if with_years:
            yr = {}
            for y, gg in sub.groupby("year"):
                xx = gg["ret5_long"].to_numpy(dtype=float)
                if not long_side:
                    xx = -xx
                yr[str(y)] = {"n": int(len(xx)),
                              "mean_pct": round(float(xx.mean()), 3)}
            out["neg_years"] = [y for y, s in yr.items()
                                if s["mean_pct"] <= 0]
            out["by_year"] = yr
        return out

    down_dollar = ev[(ev["side"] == -1) & ev["dollar"]]
    down_sigma = ev[(ev["side"] == -1) & ev["sigma"]]
    up_sigma = ev[(ev["side"] == 1) & ev["sigma"]]

    lawA = down_dollar[down_dollar["down_tradeable"]]
    n_days = len(all_days)
    supply = {
        "trading_days_in_frame": n_days,
        "events_per_day": round(len(lawA) / n_days, 2),
        "days_with_>=1_event_pct": round(
            100 * lawA["date"].nunique() / n_days, 1)}

    def zbuckets(sub, long_side):
        out = {}
        for lo, hi in ZBUCKETS:
            b = sub[(sub["z"] >= lo) & (sub["z"] < hi)]
            x = b["ret5_long"].to_numpy(dtype=float)
            if not long_side:
                x = -x
            out[f"[{lo},{hi if hi < 1e9 else 'inf'})"] = {
                "n": int(len(x)),
                "mean_pct": round(float(x.mean()), 3) if len(x) else None}
        return out

    result = {
        "declared": "laws, conditions, onset and metrics pre-registered "
                    "in the docstring before the run; buckets diagnostic "
                    "only; filed as-is",
        "LAW_A_crater_long_dollar_form": {
            "unconditioned_control (v1 said crashes lose)":
                stats(down_dollar, True, with_years=False),
            "TRADEABLE herd-calm (the created law)": stats(lawA, True),
            "REFUSED herd-fearful (predicted no edge)":
                stats(down_dollar[~down_dollar["down_tradeable"]], True,
                      with_years=False),
            "supply": supply},
        "LAW_B_sigma_form": {
            "up_side_short_z3_tradeable (vs dollar form +2.507)":
                stats(up_sigma[up_sigma["up_tradeable"]], False),
            "down_side_long_z3_tradeable":
                stats(down_sigma[down_sigma["down_tradeable"]], True),
            "diagnostic_zbuckets_up_short_tradeable":
                zbuckets(up_sigma[up_sigma["up_tradeable"]], False),
            "diagnostic_zbuckets_down_long_tradeable":
                zbuckets(down_sigma[down_sigma["down_tradeable"]], True)},
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
