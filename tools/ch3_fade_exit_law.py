"""
ch3_fade_exit_law.py — the exit is physics, not a clock (pre-registered)
========================================================================

DECLARED 2026-08-13 BEFORE THE RUN. One pass, no parameter scans. This
is the owner's own question, unprompted: the live CH3 book showed the
fade's profit is front-loaded (6/10 of the watched batch crossed +5%
at a close inside the window, 5 on day one) and the 5-session CLOCK
then holds through the rebound and gives it back. The 5-session hold
was an artifact of how the decade object was first measured, not a law
of how spikes relax. Same defect class as the 0.75 band and the 25-day
cap: an underived constant doing physics' job.

THE THESIS: an unbacked spike is unsupported displacement. It relaxes
while it relaxes; the first up-close after entry is the measurable
signature that relaxation has stopped. Past that point the position is
thesis-dead — raw exposure to a high-volatility name with no edge.

EVENT (identical to ch3_reveal_fade v1.1, all knowable at the close):
  day gain >= +8%, volume >= 3x trailing 20-day mean (excluding today),
  close >= $5, >= 21 bars of history. Per-event accounting (the
  original decade object's convention). Events cut at 2026-03-24, the
  end of the causal herd frame (herd_state_daily.parquet), so every
  event carries a true herd state; events needing sessions past the
  store end are dropped from ALL rules identically.

STRATA by the herd's greed band at the event day (the live engine's
own law): BACKED g>=1 (v1.1 refuses these), LOW g==0, NONE no herd row.
The live engine trades LOW+NONE.

RULES (all entries at the event close, exits at closes — honest fills):
  CLOCK   short, exit at the 5th session's close. The v1.1 object;
          reproducing it on this store is the internal check.
  DECAY   short, exit at the FIRST close higher than the previous
          close (relaxation broken), else the 5th session's close.
          No stop parameter: an immediate up-close IS the exit, so
          the squeeze tail is capped structurally, not by a knob.
  BIRTH   the BACKED stratum taken LONG (Joe's inversion, and the
          engine's own comment: "a birth, not a collapse"):
          B5 = exit at the 5th session's close;
          BD = exit at the first close LOWER than the previous
          (continuation broken), else the 5th session's close.

PRIMARY METRIC, declared now: per-event mean return AND return per
session held (capital velocity), with the v1 ship-bar intact — the
traded stratum must be positive every year. Left-tail (p1, min) is
the tiebreaker. Whatever comes out is filed as-is.

Usage:  python tools/ch3_fade_exit_law.py
Output: artifacts/ch4_uf/ch3_fade_exit_law.json
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_fade_exit_law.json")

EVENT_GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
HOLD_SESSIONS = 5
HERD_END = 20260324  # last day of the causal herd frame


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["day"] = df["Date"].dt.strftime("%Y%m%d").astype(int)

    herd = pd.read_parquet(HERD, columns=["sym", "date", "gband"])
    herd["date"] = herd["date"].astype(int)

    events = []  # sym, day-int, year, ret arrays computed inline
    rows = []
    for sym, s in df.groupby("Symbol", sort=False):
        s = s.sort_values("Date")
        c = s["Close"].to_numpy(dtype=float)
        v = s["Volume"].to_numpy(dtype=float)
        d = s["day"].to_numpy()
        n = len(c)
        if n < 26:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        for t in range(20, n - HOLD_SESSIONS):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            gain = 100 * (c[t] / c[t - 1] - 1)
            if gain < EVENT_GAIN:
                continue
            vavg = (sv[t] - sv[t - 20]) / 20.0
            if vavg <= 0 or v[t] < VOL_MULT * vavg:
                continue
            entry = c[t]
            # CLOCK: 5th session close
            clock_ret = 100 * (1 - c[t + 5] / entry)
            # DECAY: first up-close, else 5th
            dk = HOLD_SESSIONS
            for k in range(1, HOLD_SESSIONS + 1):
                if c[t + k] > c[t + k - 1]:
                    dk = k
                    break
            decay_ret = 100 * (1 - c[t + dk] / entry)
            # BIRTH long exits
            b5_ret = 100 * (c[t + 5] / entry - 1)
            bk = HOLD_SESSIONS
            for k in range(1, HOLD_SESSIONS + 1):
                if c[t + k] < c[t + k - 1]:
                    bk = k
                    break
            bd_ret = 100 * (c[t + bk] / entry - 1)
            rows.append((sym, int(d[t]), int(d[t]) // 10000,
                         clock_ret, decay_ret, dk, b5_ret, bd_ret, bk))
    ev = pd.DataFrame(rows, columns=[
        "sym", "date", "year", "clock", "decay", "decay_hold",
        "b5", "bd", "bd_hold"])
    print(f"events with full forward window, <= herd frame end: {len(ev)}")

    ev = ev.merge(herd, left_on=["sym", "date"], right_on=["sym", "date"],
                  how="left")
    ev["stratum"] = np.where(ev["gband"].isna(), "none",
                             np.where(ev["gband"] >= 1, "backed", "low"))

    def stats(x, hold=None):
        x = np.asarray(x, dtype=float)
        out = {"n": int(len(x)),
               "mean_pct": round(float(x.mean()), 3),
               "median_pct": round(float(np.median(x)), 3),
               "wr_pct": round(100 * float((x > 0).mean()), 1),
               "p1_pct": round(float(np.percentile(x, 1)), 2),
               "min_pct": round(float(x.min()), 2)}
        if hold is not None:
            h = float(np.mean(hold))
            out["mean_hold_sessions"] = round(h, 2)
            out["ret_per_session_pct"] = round(out["mean_pct"] / h, 3)
        else:
            out["mean_hold_sessions"] = 5.0
            out["ret_per_session_pct"] = round(out["mean_pct"] / 5.0, 3)
        return out

    def by_year(sub, col):
        return {str(y): {"n": int(len(g)),
                         "mean_pct": round(float(g[col].mean()), 3)}
                for y, g in sub.groupby("year")}

    traded = ev[ev["stratum"].isin(["low", "none"])]   # what v1.1 trades
    backed = ev[ev["stratum"] == "backed"]

    result = {
        "declared": "rules and metrics pre-registered in this file's "
                    "docstring before the run; one pass, no scans",
        "store": os.path.basename(STORE),
        "events_total": int(len(ev)),
        "strata_counts": ev["stratum"].value_counts().to_dict(),
        "internal_check_clock_all": stats(ev["clock"]),
        "traded_stratum (low+none, the live engine's supply)": {
            "CLOCK_v1.1": {**stats(traded["clock"]),
                           "by_year": by_year(traded, "clock")},
            "DECAY_v2": {**stats(traded["decay"], traded["decay_hold"]),
                         "by_year": by_year(traded, "decay")},
        },
        "backed_stratum (v1.1 refuses; taken LONG)": {
            "SHORT_clock (what v1.1 would have earned)": stats(backed["clock"]),
            "BIRTH_5d_long": {**stats(backed["b5"]),
                              "by_year": by_year(backed, "b5")},
            "BIRTH_decaybreak_long": {**stats(backed["bd"], backed["bd_hold"]),
                                      "by_year": by_year(backed, "bd")},
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
