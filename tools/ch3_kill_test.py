"""
ch3_kill_test.py — does the live book sit inside its own object?
================================================================

DECLARED 2026-08-13 BEFORE the 20th closure books. The live CH3 record
looks bad in dollars. "Looks bad" is not a verdict; a verdict needs the
null: the decade object (traded stratum, clock exit, +2.507%/event,
n=18,622) has enormous per-event dispersion (p1 = -85%), so a small
live sample can sit far from the mean and still be the same animal.

THE TEST (threshold declared now, before the percentile is known):
draw 100,000 random samples of size n_live from the decade traded-
stratum per-event clock returns; find the percentile of the live mean
in that distribution.

  live mean BELOW the 5th percentile  -> BROKEN: the live channel is
      not drawing from the measured object. New entries HALT until the
      difference is found and named.
  otherwise -> the live record is inside the object's own dispersion.
      The channel keeps running, and green-tape droughts are the
      sit-out the physics demands, not a defect.

Live sample: engine ch3_reveal_fade_v1.1 closures only (status TIME),
per-event ret_pct — same accounting as the object. Run after the close
pass books exits.

Usage:  python tools/ch3_kill_test.py
Output: artifacts/ch4_uf/ch3_kill_test.json (+ event returns cached in
        artifacts/ch4_uf/ch3_fade_event_returns.parquet on first run)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
HERD = os.path.join(ROOT, "artifacts", "ch4_uf", "herd_state_daily.parquet")
CACHE = os.path.join(ROOT, "artifacts", "ch4_uf",
                     "ch3_fade_event_returns.parquet")
LOG = os.path.join(ROOT, "artifacts", "vtvr_observer", "ch3_shadow_log.json")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_kill_test.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
KILL_PCTL = 5.0
DRAWS = 100_000


def build_event_returns():
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
        if len(c) < 26:
            continue
        sv = np.concatenate(([0.0], np.cumsum(v)))
        for t in range(20, len(c) - HOLD):
            if d[t] > HERD_END:
                break
            if c[t] < PRICE_FLOOR or c[t - 1] <= 0:
                continue
            if 100 * (c[t] / c[t - 1] - 1) < EVENT_GAIN:
                continue
            vavg = (sv[t] - sv[t - 20]) / 20.0
            if vavg <= 0 or v[t] < VOL_MULT * vavg:
                continue
            rows.append((sym, int(d[t]),
                         100 * (1 - c[t + HOLD] / c[t])))
    ev = pd.DataFrame(rows, columns=["sym", "date", "clock"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    ev = ev[(ev["gband"].isna()) | (ev["gband"] == 0)]
    ev[["sym", "date", "clock"]].to_parquet(CACHE, index=False)
    return ev[["sym", "date", "clock"]]


def main():
    ev = (pd.read_parquet(CACHE) if os.path.exists(CACHE)
          else build_event_returns())
    obj = ev["clock"].to_numpy(dtype=float)

    log = json.load(open(LOG))
    # v1.1 and v2 share the event law and clock exit; v2 changes only
    # sizing, so per-event returns pool into one live sample
    live = [f["ret_pct"] for f in log["finds"]
            if str(f.get("engine", "")).startswith("ch3_reveal_fade")
            and f["status"] == "TIME"]
    n = len(live)
    if n == 0:
        print("no live closures yet")
        return
    live_mean = float(np.mean(live))

    rng = np.random.default_rng(20260813)
    means = obj[rng.integers(0, len(obj), size=(DRAWS, n))].mean(axis=1)
    pctl = float(100.0 * (means < live_mean).mean())
    broken = pctl < KILL_PCTL

    result = {
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "object": {"n_events": int(len(obj)),
                   "mean_pct": round(float(obj.mean()), 3)},
        "live": {"n_closures": n, "mean_pct": round(live_mean, 3),
                 "total_pnl_usd": round(sum(
                     f["pnl"] for f in log["finds"]
                     if f.get("engine") == "ch3_reveal_fade_v1.1"
                     and f["status"] == "TIME"), 2)},
        "bootstrap": {"draws": DRAWS,
                      "live_mean_percentile": round(pctl, 2),
                      "kill_threshold_pctl": KILL_PCTL},
        "verdict": ("BROKEN — halt new entries; find and name the "
                    "difference before another position") if broken
        else ("INSIDE THE OBJECT — the live record is within the "
              "decade object's own dispersion at this sample size; "
              "the channel keeps running"),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
