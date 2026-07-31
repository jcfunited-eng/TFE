"""
ch4_field_cohorts.py — the full field, partitioned into peer cohorts
====================================================================

The 60-name CH4 watchlist was an inherited restriction with no physics
or compute justification (one joint-field pass over 60 names: 34 s,
fetch included). This builds the FULL eligible field's cohort roster:

  ELIGIBLE  >= 1200 daily bars in the store, median close >= $5,
            life fraction >= 0.90 (the structural weed rule).
  COHORT    peer groups of 30 by median daily dollar-volume rank —
            liquidity pedigree, deterministic, declared. (The herd
            frame conditions on peers; richer pedigree axes can
            replace the ranking without touching the wiring.)

Output: artifacts/ch4_uf/ch4_field_cohorts.json
Usage:  python tools/ch4_field_cohorts.py
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_spectrum import life_fraction  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch4_field_cohorts.json")
MIN_BARS, PRICE_FLOOR, LIFE_MIN, COHORT_SIZE = 1200, 5.0, 0.90, 30


def main():
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    recent = df[df["Date"] >= df["Date"].max() - pd.Timedelta(days=400)]
    g = df.groupby("Symbol")
    stats = pd.DataFrame({
        "bars": g["Close"].size(),
        "med": g["Close"].median()})
    dv = recent.assign(dv=recent["Close"] * recent["Volume"]) \
        .groupby("Symbol")["dv"].median()
    stats["dollar_vol"] = dv
    elig = stats[(stats["bars"] >= MIN_BARS) & (stats["med"] >= PRICE_FLOOR)
                 & stats["dollar_vol"].notna()]
    # life fraction pass (structural weed rule)
    alive = []
    for sym in elig.index:
        closes = df[df["Symbol"] == sym].sort_values("Date")["Close"] \
            .to_numpy(dtype=float)
        if life_fraction(closes)[-1] >= LIFE_MIN:
            alive.append(sym)
    elig = elig.loc[alive].sort_values("dollar_vol", ascending=False)
    syms = elig.index.tolist()
    cohorts = [syms[i:i + COHORT_SIZE]
               for i in range(0, len(syms), COHORT_SIZE)]
    if cohorts and len(cohorts[-1]) < 10:      # merge a tiny tail cohort
        cohorts[-2].extend(cohorts.pop())
    result = {
        "frame": "full eligible field in liquidity-pedigree cohorts of "
                 f"{COHORT_SIZE}; deterministic, declared",
        "eligible": len(syms),
        "cohorts": len(cohorts),
        "est_nightly_minutes_single_process": round(len(cohorts) * 17 / 60),
        "roster": cohorts,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(f"eligible {len(syms)} names -> {len(cohorts)} cohorts of "
          f"~{COHORT_SIZE}; est nightly pass "
          f"{result['est_nightly_minutes_single_process']} min single-process")
    print("filed:", OUT)


if __name__ == "__main__":
    main()
