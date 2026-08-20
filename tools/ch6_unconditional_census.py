"""
ch6_unconditional_census.py — every life, every close, no doorbell
==================================================================

DECLARED 2026-08-20 BEFORE RESULTS (Rule 9). Joseph: "you have at
least 1000 good stocks to choose from when you use the kernel
correctly — why is CH6 so anemic?" The spike-event precondition was
the junk experiment's doorbell. This measures the SAME eight-fact
joint structures with NO precondition: all validated lives, every
completed close of the decade, from the population reading layer.

OUTCOME per stock-night (the live CH6 exit law, true gap): short at
that close; first later close 2%+ in favor banks; first 20%+ against
cuts at that close; else the 5th close. Overlap within one life is
NOT deduplicated (each night is a separate claim the structure
makes); breadth per night is reported so supply is judged honestly.

INTEGRITY GATE: structures are computed vectorized for speed and
MUST match tools.ch6_structure_census.facts_at exactly — the
run validates 200 random stock-nights on 12 random lives and ABORTS
on any mismatch.

REPORTING: per structure per half (derive <= 2023-12-31 /
CONFIRM 2024+, n >= 200): n, money per $100k-at-2%-per... plainly:
dollars per $2,000 short, wins/losses, worst, below -50 count; the
PAY/AVOID lists under the census's own criteria; and mean candidates
per night in the top structures (the supply answer).

Usage: python tools/ch6_unconditional_census.py [workers]
Output: artifacts/ch4_uf/ch6_unconditional_census.json
"""

from __future__ import annotations

import json
import os
import random
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch6_unconditional_census.json")

BANK_X, STOP_X, HOLD = 0.98, 1.20, 5
DERIVE_END = "2023-12-31"
SELF_W = 504
T_MIN = 180
SLICE = 2000.0


def vector_facts(lf: pd.DataFrame) -> pd.DataFrame:
    """All eight facts for every t, vectorized; must equal facts_at."""
    ext = pd.Series(lf["extinction"].to_numpy(dtype=float))
    urf = pd.Series(lf["URF"].to_numpy(dtype=float))
    D = pd.Series(lf["D_k"].to_numpy(dtype=float))
    rev = pd.Series(lf["Rev_k"].to_numpy(dtype=float))
    U = pd.Series(lf["U_star_k"].to_numpy(dtype=float))
    close = pd.Series(lf["close"].to_numpy(dtype=float))

    d90 = ext.rolling(90).sum()
    p90 = ext.rolling(90).sum().shift(90)
    urf_min90 = urf.rolling(90).min()
    dsum45 = D.rolling(45).sum()
    dnz45 = (D != 0).rolling(45).sum()
    rev45 = rev.rolling(45, min_periods=1).sum()
    # expanding-tail medians over the trailing SELF_W window INCLUSIVE,
    # exactly as facts_at's [max(0, t-SELF_W):t+1] slices
    rev45_med = rev45.rolling(SELF_W + 1, min_periods=1).median()
    u10 = U.rolling(10).mean()
    u_med = U.rolling(SELF_W + 1, min_periods=1).median()
    nz = (D != 0).astype(float)
    l64 = (D.rolling(64, min_periods=1).sum().abs()
           / nz.rolling(64, min_periods=1).sum().clip(lower=1))
    l_med = l64.rolling(SELF_W + 1, min_periods=1).median()
    peak_prior = close.shift(1).expanding().max()

    out = pd.DataFrame({
        "deaths": np.where(d90 > 0, "D1", "D0"),
        "slope": np.where(d90 > p90, "R", np.where(d90 < p90, "Q", "S")),
        "channel": np.where(urf_min90 <= 0, "BROKEN", "UNBROKEN"),
        "push": np.where(dnz45 == 0, "BAL",
                         np.where(dsum45 > 0, "UP",
                                  np.where(dsum45 < 0, "DN", "BAL"))),
        "buzz": np.where(rev45 > rev45_med, "B+", "B-"),
        "strain": np.where(u10 > u_med, "U+", "U-"),
        "lock": np.where(l64 > l_med, "L+", "L-"),
        "depth": np.where(close >= 0.5 * peak_prior, "HIGH", "DEEP"),
        "close": close, "date": lf["date"],
    })
    return out


def config_col(fx: pd.DataFrame) -> pd.Series:
    return (fx["deaths"] + " " + fx["slope"] + " " + fx["channel"] + " "
            + fx["push"] + " " + fx["buzz"] + " " + fx["strain"] + " "
            + fx["lock"] + " " + fx["depth"])


def validate(sample_files: list) -> None:
    from tools.ch6_structure_census import build_lane, facts_at
    rng = random.Random(20260820)
    checked = 0
    for path in sample_files:
        lf = pd.read_parquet(path)
        if len(lf) < T_MIN + 10:
            continue
        fx = vector_facts(lf)
        cfg = config_col(fx)
        lane = build_lane(lf)
        for _ in range(17):
            t = rng.randrange(T_MIN, len(lf))
            ref = facts_at(lane, t)
            ref_cfg = " ".join(ref[k] for k in (
                "deaths", "slope", "channel", "push", "buzz", "strain",
                "lock", "depth"))
            if ref_cfg != cfg.iloc[t]:
                raise AssertionError(
                    f"INTEGRITY GATE FAILED {path} t={t}: "
                    f"facts_at [{ref_cfg}] != vector [{cfg.iloc[t]}]")
            checked += 1
    print(f"integrity gate: {checked} stock-nights match exactly")


def one_life(path: str) -> list:
    lf = pd.read_parquet(path)
    n = len(lf)
    if n < T_MIN + HOLD + 1:
        return []
    fx = vector_facts(lf)
    cfg = config_col(fx).to_numpy()
    c = lf["close"].to_numpy(dtype=float)
    dates = lf["date"].to_numpy()
    rows = []
    for t in range(T_MIN, n - HOLD):
        entry = c[t]
        if entry <= 0:
            continue
        exit_px = c[t + HOLD]
        for k in range(1, HOLD + 1):
            if c[t + k] <= BANK_X * entry:
                exit_px = c[t + k]
                break
            if c[t + k] >= STOP_X * entry:
                exit_px = c[t + k]
                break
        rows.append((dates[t], cfg[t], 100 * (entry - exit_px) / entry))
    return rows


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    files = sorted(os.path.join(LANES, f) for f in os.listdir(LANES)
                   if f.endswith(".parquet"))
    rng = random.Random(20260820)
    validate(rng.sample(files, 12))
    all_rows = []
    with Pool(workers) as pool:
        for i, rows in enumerate(pool.imap_unordered(one_life, files,
                                                     chunksize=16)):
            all_rows.extend(rows)
            if (i + 1) % 400 == 0:
                print(f"[{i + 1}/{len(files)}] {len(all_rows):,} "
                      "stock-nights", flush=True)
    ev = pd.DataFrame(all_rows, columns=["date", "config", "ret"])
    print(f"stock-nights: {len(ev):,}")

    def ledger(sub: pd.DataFrame) -> dict:
        r = sub["ret"]
        return {"n": int(len(sub)),
                "usd_per_2k": round(float(r.mean()) * SLICE / 100, 2),
                "wins_losses": f"{int((r > 0).sum())}W/{int((r < 0).sum())}L",
                "worst_pct": round(float(r.min()), 1),
                "below_-50": int((r < -50).sum())}

    derive = ev[ev["date"] <= DERIVE_END]
    confirm = ev[ev["date"] > DERIVE_END]
    table, pay, avoid = {}, [], []
    for cfg2, dsub in derive.groupby("config"):
        if len(dsub) < 200:
            continue
        csub = confirm[confirm["config"] == cfg2]
        if len(csub) < 100:
            continue
        dv, cf = ledger(dsub), ledger(csub)
        table[cfg2] = {"derive": dv, "confirm": cf}
        d_ok = dv["usd_per_2k"] > 0 and dv["below_-50"] == 0
        c_ok = cf["usd_per_2k"] > 0 and cf["below_-50"] == 0
        if d_ok and c_ok:
            pay.append((min(dv["usd_per_2k"], cf["usd_per_2k"]), cfg2))
        elif (dv["usd_per_2k"] <= 0 or dv["below_-50"] > 0) and \
                (cf["usd_per_2k"] <= 0 or cf["below_-50"] > 0):
            avoid.append(cfg2)
    pay.sort(reverse=True)
    pay_set = {c2 for _, c2 in pay}
    conf_pay = confirm[confirm["config"].isin(pay_set)]
    per_night = conf_pay.groupby("date").size()
    result = {
        "declared": "no-precondition frame, integrity gate, split, and "
                    "criteria in the docstring before results",
        "stock_nights": len(ev),
        "structures_with_n": len(table),
        "PAY_both_halves": [
            {"config": c2, "worse_half_usd_per_2k": m,
             **{"derive": table[c2]["derive"],
                "confirm": table[c2]["confirm"]}} for m, c2 in pay],
        "AVOID_count": len(avoid),
        "supply": {
            "paying_candidates_per_night_mean":
                round(float(per_night.mean()), 1) if len(per_night) else 0,
            "nights_with_zero": int(
                (confirm["date"].nunique()) - len(per_night)),
            "confirm_nights": int(confirm["date"].nunique())},
    }
    json.dump(result, open(OUT, "w"), indent=1)
    ev.to_parquet(OUT.replace(".json", "_events.parquet"))
    print(json.dumps({k: result[k] for k in
                      ("stock_nights", "structures_with_n", "AVOID_count",
                       "supply")}, indent=1))
    print("top paying:", [c2 for _, c2 in pay[:5]])
    print("filed:", OUT)


if __name__ == "__main__":
    main()
