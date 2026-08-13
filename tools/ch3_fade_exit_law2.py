"""
ch3_fade_exit_law2.py — depth-anchored exits for the fade (pass 2)
==================================================================

DECLARED 2026-08-13 BEFORE THE RUN, after pass 1 (ch3_fade_exit_law.py)
FALSIFIED the decay-break exit: one up-close is breathing, not the end
of relaxation (traded stratum: decay +1.224%/ev vs clock +2.507%/ev).
Pass 1 is filed untouched as that falsification record.

What the live book actually showed was DEPTH REACHED, THEN GIVEN BACK.
So pass 2 tests exits conditioned on the depth of relaxation, not on
one day's direction. Every anchor below pre-dates tonight — either the
event's own geometry or Joe's harvest rule declared 2026-08-11 for CH6.
No level scans; these five rules and nothing else.

Event set, strata, store, accounting: identical to pass 1. All entries
short at the event close; all exits at closes; 5th-session close is
the universal backstop. Fills honest, per-event accounting.

  R1 LAUNCH   exit at the first close <= the launch price (the close
              the day BEFORE the spike): displacement fully relaxed,
              thesis complete. Anchor = the event's own geometry.
  R2 HARVEST5 exit at the first close giving the short >= +5%
              (close <= 0.95 x entry). Anchor = Joe's CH6 harvest
              rule, declared 2026-08-11, prior to this measurement.
  R3 REFUTE   exit at the first close ABOVE entry: the field closed
              higher than the spike itself — the displacement was not
              unsupported; the thesis is refuted, not breathing.
              Anchor = the entry itself. (Structural squeeze cap.)
  R2+R3       harvest the depth, abandon on refutation, else clock.
  R1+R3       full relaxation target with the refutation cap.

Also filed for the CLOCK: how often a position touches >= +5% at some
close inside the window and then finishes under +5% (the give-back
rate — the thing Joe watched happen).

PRIMARY METRIC unchanged from pass 1's declaration: per-event mean AND
return per session held; yearly consistency at the v1 bar; left tail
as tiebreaker. Filed as-is whatever comes out.

Usage:  python tools/ch3_fade_exit_law2.py
Output: artifacts/ch4_uf/ch3_fade_exit_law2.json
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_fade_exit_law2.json")

EVENT_GAIN = 8.0
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
HOLD = 5
HERD_END = 20260324
HARVEST = 0.95  # close <= 0.95 x entry == short P&L >= +5% (Joe's rule)


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
        if n < 26:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        for t in range(20, n - HOLD):
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
            launch = c[t - 1]
            win = c[t + 1: t + HOLD + 1]

            def first(cond):
                idx = np.flatnonzero(cond)
                return int(idx[0]) + 1 if len(idx) else None

            k_launch = first(win <= launch)
            k_harv = first(win <= HARVEST * entry)
            k_ref = first(win > entry)

            def settle(*ks):
                ks = [k for k in ks if k is not None]
                k = min(ks) if ks else HOLD
                return 100 * (1 - c[t + k] / entry), k

            clock = 100 * (1 - c[t + HOLD] / entry)
            r1, h1 = settle(k_launch)
            r2, h2 = settle(k_harv)
            r3, h3 = settle(k_ref)
            r23, h23 = settle(k_harv, k_ref)
            r13, h13 = settle(k_launch, k_ref)
            touched5 = k_harv is not None
            giveback = touched5 and clock < 5.0
            rows.append((sym, int(d[t]), int(d[t]) // 10000, clock,
                         r1, h1, r2, h2, r3, h3, r23, h23, r13, h13,
                         touched5, giveback))

    ev = pd.DataFrame(rows, columns=[
        "sym", "date", "year", "clock", "r1", "h1", "r2", "h2",
        "r3", "h3", "r23", "h23", "r13", "h13", "touched5", "giveback"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    ev["stratum"] = np.where(ev["gband"].isna(), "none",
                             np.where(ev["gband"] >= 1, "backed", "low"))
    tr = ev[ev["stratum"].isin(["low", "none"])]
    print(f"traded-stratum events: {len(tr)}")

    def stats(col, hold_col=None):
        x = tr[col].to_numpy(dtype=float)
        h = (tr[hold_col].to_numpy(dtype=float).mean()
             if hold_col else float(HOLD))
        yr = {str(y): {"n": int(len(g)),
                       "mean_pct": round(float(g[col].mean()), 3)}
              for y, g in tr.groupby("year")}
        return {"n": int(len(x)),
                "mean_pct": round(float(x.mean()), 3),
                "median_pct": round(float(np.median(x)), 3),
                "wr_pct": round(100 * float((x > 0).mean()), 1),
                "p1_pct": round(float(np.percentile(x, 1)), 2),
                "min_pct": round(float(x.min()), 2),
                "mean_hold_sessions": round(h, 2),
                "ret_per_session_pct": round(float(x.mean()) / h, 3),
                "neg_years": [y for y, s in yr.items()
                              if s["mean_pct"] <= 0],
                "by_year": yr}

    result = {
        "declared": "five depth-anchored rules pre-registered in the "
                    "docstring; anchors pre-date tonight; no scans",
        "traded_events": int(len(tr)),
        "clock_giveback_diagnostic": {
            "touched_+5pct_at_a_close_pct":
                round(100 * float(tr["touched5"].mean()), 1),
            "of_those_gave_it_back_pct":
                round(100 * float(tr[tr["touched5"]]["giveback"].mean()), 1)
                if tr["touched5"].any() else None},
        "CLOCK_v1.1": stats("clock"),
        "R1_LAUNCH": stats("r1", "h1"),
        "R2_HARVEST5": stats("r2", "h2"),
        "R3_REFUTE": stats("r3", "h3"),
        "R2+R3": stats("r23", "h23"),
        "R1+R3": stats("r13", "h13"),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    for k in ("CLOCK_v1.1", "R1_LAUNCH", "R2_HARVEST5", "R3_REFUTE",
              "R2+R3", "R1+R3"):
        s = result[k]
        print(f"{k:12s} mean {s['mean_pct']:+.3f}  med {s['median_pct']:+.3f} "
              f" wr {s['wr_pct']:.1f}  hold {s['mean_hold_sessions']:.2f} "
              f" /sess {s['ret_per_session_pct']:+.3f}  p1 {s['p1_pct']:.1f} "
              f" min {s['min_pct']:.0f}  negyrs {s['neg_years']}")
    print("giveback:", result["clock_giveback_diagnostic"])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
