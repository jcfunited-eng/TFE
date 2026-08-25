"""ch6_pool.py — nightly admission to the readings door.

Admits every operating company in the store roster whose last ten
daily sessions carry structural damage (a channel death, a
dead-channel reading, or stability sagging 0.05+ over the month) —
kernel facts admit, readings select, laws govern staging. The two
triage cuts here mirror in-force laws only (fillability floor and
the poison ceiling); the real laws re-run fresh at staging.

Output: artifacts/ch6_harvest/door/pool_<latest>.json
Usage: python tools/ch6_pool.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DAY_LANES = os.path.join(ROOT, "artifacts", "ch4_uf", "population_lanes")
TYPES = os.path.join(ROOT, "artifacts", "ch6_harvest", "ticker_types.json")
STORE = os.path.join(ROOT, "ch4_live_store.parquet")
DOOR = os.path.join(ROOT, "artifacts", "ch6_harvest", "door")
OPERATING = ("CS", "ADRC")


def _resolve_missing(symbols: list, cache: dict, key: str) -> None:
    """Identity for uncached names; UNKNOWN is never cached."""
    def one(sym):
        url = (f"https://api.polygon.io/v3/reference/tickers?ticker={sym}"
               f"&apiKey={key}")
        try:
            res = json.load(urllib.request.urlopen(url, timeout=30)).get(
                "results") or []
            return sym, (str(res[0].get("type", "UNKNOWN")) if res else None)
        except Exception:  # noqa: BLE001
            return sym, None
    todo = [s for s in symbols if s not in cache]
    if not todo:
        return
    with ThreadPoolExecutor(16) as ex:
        for sym, t in ex.map(one, todo):
            if t and t != "UNKNOWN":
                cache[sym] = t
    tmp = TYPES + f".tmp{os.getpid()}"
    json.dump(cache, open(tmp, "w"))
    os.replace(tmp, TYPES)


def main() -> None:
    key = ""
    for ln in open(os.path.join(ROOT, ".env")):
        if ln.startswith("MASSIVE_API_KEY"):
            key = ln.split("=", 1)[1].strip().strip('"')
    store = pd.read_parquet(STORE)
    latest = str(store["Date"].max())[:10]
    day = store[store["Date"] == store["Date"].max()]
    roster = sorted(set(day["Symbol"].astype(str)))
    med20 = {}
    for sym, g in store.groupby("Symbol"):
        g = g.sort_values("Date").tail(21).head(20)
        med20[str(sym)] = float((g["Close"] * g["Volume"]).median())

    cache = json.load(open(TYPES)) if os.path.exists(TYPES) else {}
    _resolve_missing(roster, cache, key)

    admitted, skipped = [], {"zombie": 0, "no_lane": 0, "fill": 0,
                             "ceiling": 0, "healthy": 0, "unknown_type": 0}
    for sym in roster:
        t = cache.get(sym)
        if t is None:
            skipped["unknown_type"] += 1
            continue
        if t not in OPERATING:
            skipped["zombie"] += 1
            continue
        nd = med20.get(sym, 0.0)
        if not (nd and np.isfinite(nd)) or nd < 200_000:
            skipped["fill"] += 1
            continue
        if nd >= 100_000_000:
            skipped["ceiling"] += 1
            continue
        path = os.path.join(DAY_LANES, f"{sym}.parquet")
        if not os.path.exists(path):
            skipped["no_lane"] += 1
            continue
        lf = pd.read_parquet(path, columns=["date", "URF", "S_UF",
                                            "extinction"])
        if len(lf) < 40 or str(lf["date"].iloc[-1]) != latest:
            skipped["no_lane"] += 1
            continue
        t10 = lf.tail(10)
        s = lf["S_UF"].to_numpy(float)
        damaged = (int(t10["extinction"].sum()) >= 1
                   or int((t10["URF"].to_numpy(float) <= 0).sum()) >= 1
                   or (len(s) > 22 and float(s[-23] - s[-1]) >= 0.05))
        if damaged:
            admitted.append(sym)
        else:
            skipped["healthy"] += 1

    os.makedirs(DOOR, exist_ok=True)
    out = {"decided_close": latest, "admitted": admitted,
           "skipped": skipped}
    path = os.path.join(DOOR, f"pool_{latest}.json")
    tmp = path + f".tmp{os.getpid()}"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, path)
    print(f"[ch6 pool] {latest}: admitted {len(admitted)}  "
          f"skipped {skipped}")
    print(f"filed: {path}")


if __name__ == "__main__":
    main()
