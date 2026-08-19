"""
ch4_perception_nightly.py — the perception layer's nightly claims
=================================================================

2026-08-19, Joseph: "put your work in that page — make it a thing on
production so we can evaluate it against live data." This tool makes
the perception FALSIFIABLE in production: every night, at the
completed close, it files a verdict for every clean-universe spike
event — PAY / AVOID / UNDECIDED by joint-structure membership in the
decade census lists — BEFORE the outcome exists, then updates every
prior verdict with what actually happened. The scoreboard accumulates
in public; the physics is graded by live data, nothing else.

Observation law (no book, no dollars, declared): FADED = first
completed close 5%+ below the event close within 5 sessions;
RAN = first completed close 20%+ above within 5 sessions;
FLAT = neither by the fifth; PENDING otherwise. Gaps count as what
they are: the close that crossed is the close recorded.

Outputs:
  artifacts/ch4_uf/ch4_perception_record.json  (full rolling record)
  artifacts/ch4_uf/ch4_perception.json         (published summary)

Runs in the CH4 nightly pass after the population reading append.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.ch4_joint_structure_census import build_lane, facts_at  # noqa: E402

LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
UNIVERSE = os.path.join(ROOT, "artifacts", "ch4_uf",
                        "population_universe_20260819.csv")
CENSUS = os.path.join(ROOT, "artifacts", "ch4_uf",
                      "ch4_joint_structure_census.json")
RECORD = os.path.join(ROOT, "artifacts", "ch4_uf",
                      "ch4_perception_record.json")
OUT = os.path.join(ROOT, "artifacts", "ch4_uf", "ch4_perception.json")

EVENT_GAIN, VOL_MULT, PRICE_FLOOR, HOLD = 8.0, 3.0, 5.0, 5
FADE_X, RUN_X = 0.95, 1.20


def config_of(fx: dict) -> str:
    return " ".join(fx[k] for k in ("deaths", "slope", "channel", "push",
                                    "buzz", "strain", "lock", "depth"))


def main() -> None:
    census = json.load(open(CENSUS))
    pay = {e["config"] for e in census["PAY_both_halves"]}
    avoid = {e["config"] for e in census["AVOID_both_halves"]}

    symbols = set(pd.read_csv(UNIVERSE)["Symbol"].astype(str))
    store = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close", "Volume"])
    store = store[store["Symbol"].isin(symbols)]
    store["day"] = store["Date"].dt.strftime("%Y-%m-%d")
    days = sorted(store["day"].unique())
    latest = days[-1]

    record = []
    if os.path.exists(RECORD):
        record = json.load(open(RECORD))
    by_key = {(r["symbol"], r["event_close"]): r for r in record}

    # tonight's verdicts at the latest completed close
    latest_rows = store[store["day"] == latest]
    tonight = []
    for sym in sorted(latest_rows["Symbol"].unique()):
        hist = store[store["Symbol"] == sym].sort_values("Date")
        c = hist["Close"].to_numpy(dtype=float)
        v = hist["Volume"].to_numpy(dtype=float)
        if len(c) < 22 or c[-1] < PRICE_FLOOR or c[-2] <= 0:
            continue
        if 100 * (c[-1] / c[-2] - 1) < EVENT_GAIN:
            continue
        va = float(np.mean(v[-21:-1]))
        if va <= 0 or v[-1] < VOL_MULT * va:
            continue
        lp = os.path.join(LANES, f"{sym}.parquet")
        if not os.path.exists(lp):
            continue
        lf = pd.read_parquet(lp)
        if lf["date"].iloc[-1] != latest:
            continue  # lane lags the store: no verdict without perception
        fx = facts_at(build_lane(lf), len(lf) - 1)
        if fx is None:
            continue
        cfg = config_of(fx)
        verdict = ("PAY" if cfg in pay else
                   "AVOID" if cfg in avoid else "UNDECIDED")
        filed = by_key.get((sym, latest))
        if filed is None:
            filed = {"symbol": sym, "event_close": latest,
                     "close": round(float(c[-1]), 4), "structure": cfg,
                     "verdict": verdict, "outcome": "PENDING",
                     "filed_at": datetime.now(timezone.utc).isoformat()}
            record.append(filed)
            by_key[(sym, latest)] = filed
        # tonight ALWAYS shows the filed entry — a rerun must never
        # display a verdict that differs from the immutable record
        tonight.append(filed)

    # outcomes for every pending prior verdict, from completed closes only
    day_index = {d: i for i, d in enumerate(days)}
    for r in record:
        if r["outcome"] != "PENDING":
            continue
        i0 = day_index.get(r["event_close"])
        if i0 is None or i0 + 1 > len(days) - 1:
            continue
        hist = store[store["Symbol"] == r["symbol"]].sort_values("Date")
        path = hist[hist["day"] > r["event_close"]]["Close"].to_numpy(dtype=float)
        entry_px = float(r["close"])
        for k, px in enumerate(path[:HOLD], start=1):
            if px <= FADE_X * entry_px:
                r["outcome"] = "FADED"
                r["outcome_ret_pct"] = round(100 * (entry_px - px) / entry_px, 2)
                break
            if px >= RUN_X * entry_px:
                r["outcome"] = "RAN"
                r["outcome_ret_pct"] = round(100 * (entry_px - px) / entry_px, 2)
                break
        else:
            if len(path) >= HOLD:
                r["outcome"] = "FLAT"
                r["outcome_ret_pct"] = round(
                    100 * (entry_px - float(path[HOLD - 1])) / entry_px, 2)

    tmp = RECORD + f".tmp{os.getpid()}"
    with open(tmp, "w") as handle:
        json.dump(record, handle, indent=1)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, RECORD)

    scoreboard: dict[str, dict[str, int]] = {}
    for r in record:
        s = scoreboard.setdefault(r["verdict"], {"n": 0, "FADED": 0, "RAN": 0,
                                                 "FLAT": 0, "PENDING": 0})
        s["n"] += 1
        s[r["outcome"]] += 1

    universe_n = len(symbols)
    lane_files = len([f for f in os.listdir(LANES) if f.endswith(".parquet")])
    summary = {
        "as_of_close": latest,
        "layer": {"lives": lane_files, "universe": universe_n,
                  "through": latest},
        "standing_census": {
            "events_decade": census["events"]["total"],
            "pay_structures": len(pay), "avoid_structures": len(avoid),
            "pay_share_of_supply": census["coverage"][
                "pay_share_of_confirm_supply"],
            "avoid_share_of_supply": census["coverage"][
                "avoid_share_of_confirm_supply"]},
        "tonight": tonight,
        "scoreboard": scoreboard,
        "law": ("Verdicts are filed at the completed close, before any "
                "outcome exists, and are never edited. Outcomes: FADED = "
                "first completed close 5%+ below the event close within the "
                "symbol's own next five closes; RAN = 20%+ above; FLAT = "
                "neither by the fifth. The close that crossed is the close "
                "recorded, gaps included. No orders; this is the perception "
                "being graded by live data."),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp = OUT + f".tmp{os.getpid()}"
    with open(tmp, "w") as handle:
        json.dump(summary, handle, indent=1)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, OUT)
    print(f"[ch4-perception] {latest}: {len(tonight)} verdicts tonight "
          f"({sum(1 for t in tonight if t['verdict']=='PAY')} pay, "
          f"{sum(1 for t in tonight if t['verdict']=='AVOID')} avoid); "
          f"record {len(record)} events; filed {OUT}")


if __name__ == "__main__":
    main()
