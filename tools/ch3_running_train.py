"""
ch3_running_train.py — don't step in front of it; maybe ride it
===============================================================

DECLARED 2026-08-17 BEFORE THE RUN (Joe, after WETO: "there should be
protection against... getting into a stock"; and "if you see a ~99%
increase coming shouldn't that be a buy!"). One pass, no scans, filed
as-is.

THE TELL: both grenades were trains already running BEFORE the spike
we shorted — WETO +54% in the prior two weeks, +857% YTD. A crowd
that the herd frame cannot see for young names is still visible in
the name's OWN chart. Two pre-registered questions on the decade's
uncovered stratum (herd row absent — the blind-spot class):

  Q1 REFUSAL: split events by PRERUN = trailing 20-session return
     ending the day BEFORE the spike. Declared line: prerun >= +50%
     is a RUNNING TRAIN (a-priori round number marking "already up
     half again before the spike" — the WETO class; not fitted).
     Compare short returns under the LIVE law (harvest at first
     close <= 0.95x entry, cut at first close >= 1.20x entry,
     5-session backstop) for trains vs non-trains. The refusal
     ships iff trains lose or earn ~nothing while non-trains keep
     the edge.

  Q2 RIDE: the train stratum taken LONG at the spike close, mirror
     law (harvest at first close >= 1.05x entry, cut at first close
     <= 0.80x entry, 5-session backstop). Reported with per-year
     means and supply. Becomes a construction only if positive with
     yearly consistency — and then its own book, not a CH4 graft.

Usage:  python tools/ch3_running_train.py
Output: artifacts/ch4_uf/ch3_running_train.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_running_train.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
HARVEST_X, STOP_X = 0.95, 1.20            # live short law
L_HARVEST_X, L_STOP_X = 1.05, 0.80        # mirrored long law
TRAIN_PRERUN = 50.0                       # a-priori: +50% trailing 20 sessions


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
        if len(c) < 42:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        for t in range(21, len(c) - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            va = (sv[t] - sv[t - 20]) / 20.0
            if va <= 0 or v[t] < VOL_MULT * va:
                continue
            base = c[t - 21] if t >= 21 and c[t - 21] > 0 else np.nan
            prerun = 100 * (c[t - 1] / base - 1) if np.isfinite(base) else np.nan
            entry = c[t]
            ks = HOLD
            for j in range(1, HOLD + 1):
                if c[t + j] <= HARVEST_X * entry or c[t + j] >= STOP_X * entry:
                    ks = j
                    break
            short_ret = 100 * (1 - c[t + ks] / entry)
            kl = HOLD
            for j in range(1, HOLD + 1):
                if c[t + j] >= L_HARVEST_X * entry or c[t + j] <= L_STOP_X * entry:
                    kl = j
                    break
            long_ret = 100 * (c[t + kl] / entry - 1)
            rows.append((sym, int(d[t]), int(d[t]) // 10000,
                         prerun, short_ret, long_ret))
    ev = pd.DataFrame(rows, columns=["sym", "date", "year", "prerun",
                                     "short_ret", "long_ret"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    unc = ev[ev["gband"].isna() & ev["prerun"].notna()].copy()
    unc["train"] = unc["prerun"] >= TRAIN_PRERUN
    print(f"uncovered events with prerun: {len(unc)} "
          f"(trains {int(unc['train'].sum())})")

    def stats(x, sub=None, col=None):
        x = np.asarray(x, dtype=float)
        out = {"n": int(len(x))}
        if len(x) == 0:
            return out
        out.update({"mean_pct": round(float(x.mean()), 3),
                    "median_pct": round(float(np.median(x)), 3),
                    "wr_pct": round(100 * float((x > 0).mean()), 1),
                    "p1_pct": round(float(np.percentile(x, 1)), 2)})
        if sub is not None:
            yr = {str(y): round(float(g[col].mean()), 3)
                  for y, g in sub.groupby("year")}
            out["neg_years"] = [y for y, m in yr.items() if m <= 0]
            out["by_year"] = yr
        return out

    trains = unc[unc["train"]]
    calm = unc[~unc["train"]]
    n_days = ev["date"].nunique()
    result = {
        "declared": "train line +50% trailing-20 prerun, a-priori; live "
                    "short law and mirrored long law; one pass, filed as-is",
        "Q1_refusal_short_side": {
            "trains_SHORT (refusal candidates)": stats(
                trains["short_ret"], trains, "short_ret"),
            "non_trains_SHORT (kept)": stats(
                calm["short_ret"], calm, "short_ret"),
        },
        "Q2_ride_long_side": {
            "trains_LONG (Joe's ride)": stats(
                trains["long_ret"], trains, "long_ret"),
            "supply_trains_per_day": round(len(trains) / max(n_days, 1), 2),
        },
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
