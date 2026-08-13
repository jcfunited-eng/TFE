"""
ch3_kill_test.py — does the live book sit inside its own object?
================================================================

DECLARED 2026-08-13 BEFORE the 20th closure books; extended the same
night for v3 (harvest exits) BEFORE any v3 closure exists. The live
CH3 record looks bad in dollars. "Looks bad" is not a verdict; a
verdict needs the null: the decade objects have enormous per-event
dispersion, so a small live sample can sit far from the mean and
still be the same animal.

THE TEST (thresholds declared before any percentile is known): for
each live sample, draw 100,000 random samples of the same size from
the matching decade per-event return distribution; find the
percentile of the live mean.

  live mean BELOW the 5th percentile  -> BROKEN: the live channel is
      not drawing from the measured object. New entries HALT until
      the difference is found and named.
  otherwise -> the live record is inside the object's own dispersion.

MATCHING (each engine judged against the exit law it actually ran):
  v1.1 / v2 closures  -> CLOCK object (5th-session close returns)
  v3 closures         -> R2 object (first close <= 0.95 x entry,
                         else 5th-session close)
Sizing differences (v2/v3 force allocation) do not change per-event
accounting, so per-event pooling within each exit law is exact.

Run after each close pass books exits.

Usage:  python tools/ch3_kill_test.py
Output: artifacts/ch4_uf/ch3_kill_test.json (+ event returns cached
        in artifacts/ch4_uf/ch3_fade_event_returns2.parquet)
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
                     "ch3_fade_event_returns2.parquet")
LOG = os.path.join(ROOT, "artifacts", "vtvr_observer", "ch3_shadow_log.json")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch3_kill_test.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD, HERD_END = 8.0, 3.0, 5.0, 5, 20260324
HARVEST_X = 0.95
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
            entry = c[t]
            k = HOLD
            for j in range(1, HOLD + 1):
                if c[t + j] <= HARVEST_X * entry:
                    k = j
                    break
            rows.append((sym, int(d[t]),
                         100 * (1 - c[t + HOLD] / entry),
                         100 * (1 - c[t + k] / entry)))
    ev = pd.DataFrame(rows, columns=["sym", "date", "clock", "r2"])
    ev = ev.merge(herd, on=["sym", "date"], how="left")
    ev = ev[(ev["gband"].isna()) | (ev["gband"] == 0)]
    ev = ev[["sym", "date", "clock", "r2"]]
    ev.to_parquet(CACHE, index=False)
    return ev


def main():
    ev = (pd.read_parquet(CACHE) if os.path.exists(CACHE)
          else build_event_returns())
    log = json.load(open(LOG))
    closures = [f for f in log["finds"]
                if str(f.get("engine", "")).startswith("ch3_reveal_fade")
                and f["status"] in ("TIME", "HARVEST")]
    samples = {
        "clock_engines_v1.1_v2": {
            "object_col": "clock",
            "rets": [f["ret_pct"] for f in closures
                     if not f.get("engine", "").endswith("_v3")]},
        "harvest_engine_v3": {
            "object_col": "r2",
            "rets": [f["ret_pct"] for f in closures
                     if f.get("engine", "").endswith("_v3")]},
    }
    rng = np.random.default_rng(20260813)
    out_samples, any_broken = {}, False
    for name, s in samples.items():
        n = len(s["rets"])
        if n == 0:
            out_samples[name] = {"n_closures": 0, "note": "no closures yet"}
            continue
        obj = ev[s["object_col"]].to_numpy(dtype=float)
        live_mean = float(np.mean(s["rets"]))
        means = obj[rng.integers(0, len(obj), size=(DRAWS, n))].mean(axis=1)
        pctl = float(100.0 * (means < live_mean).mean())
        broken = pctl < KILL_PCTL
        any_broken = any_broken or broken
        out_samples[name] = {
            "n_closures": n, "live_mean_pct": round(live_mean, 3),
            "object_mean_pct": round(float(obj.mean()), 3),
            "live_mean_percentile": round(pctl, 2),
            "broken": broken}
    result = {
        "ran_at_utc": datetime.now(timezone.utc).isoformat(),
        "object_events": int(len(ev)),
        "kill_threshold_pctl": KILL_PCTL,
        "samples": out_samples,
        "verdict": ("BROKEN — halt new entries; find and name the "
                    "difference before another position") if any_broken
        else ("INSIDE THE OBJECT — every populated live sample is "
              "within its own object's dispersion; the channel keeps "
              "running"),
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
