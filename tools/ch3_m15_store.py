"""
ch3_m15_store.py — 15-minute store for the CH3 watchlist (native rung)
======================================================================

The CH3 shadow hunter operates on 15-minute bars. Its decade validation
must happen at that rung: hourly bars provably cannot resolve the
same-session flare species (artifacts/ch4_uf/ch3_hourly_replay.json).

Fetches 15-minute aggregates 2016-01-01 .. today for the exact live
watchlist (cohorts A + B, 60 names) from the production Massive data
service, pagination-complete, resumable per-symbol cache.

Output: ch3_m15_watchlist.parquet (Date UTC-naive, Symbol, OHLCV).
Usage:  python tools/ch3_m15_store.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PARQUET = os.path.join(ROOT, "ch3_m15_watchlist.parquet")
CACHE_DIR = os.path.join(ROOT, "artifacts", "ch4_uf", "m15_cache")
START = "2016-01-01"
END = datetime.now(timezone.utc).strftime("%Y-%m-%d")
REQ_SLEEP = 0.15


def watchlist():
    from tools.vtvr_structure_search import UNIVERSE as COHORT_A
    from tools.vtvr_star_state_replication import COHORT_B
    return sorted(set(list(COHORT_A) + list(COHORT_B)))


def fetch_symbol(sym: str, key: str):
    cache = os.path.join(CACHE_DIR, f"{sym}.json")
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    url = (f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/15/minute/"
           f"{START}/{END}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    rows = []
    try:
        while url:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.loads(r.read())
            rows.extend(
                {"t": rec["t"], "o": rec.get("o"), "h": rec.get("h"),
                 "l": rec.get("l"), "c": rec.get("c"), "v": rec.get("v")}
                for rec in (d.get("results") or []))
            nxt = d.get("next_url")
            url = (nxt + f"&apiKey={key}") if nxt else None
            if url:
                time.sleep(REQ_SLEEP)
    except Exception as e:
        if not rows:
            rows = {"error": str(e)}
    with open(cache, "w") as f:
        json.dump(rows, f)
    time.sleep(REQ_SLEEP)
    return rows


def main():
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not key:
        print("no data key in environment")
        return 1
    os.makedirs(CACHE_DIR, exist_ok=True)
    syms = watchlist()
    frames, ok, err = [], 0, 0
    t0 = time.time()
    for i, sym in enumerate(syms):
        rows = fetch_symbol(sym, key)
        if isinstance(rows, dict) or not rows:
            err += 1
            print(f"  {sym}: ERROR {rows if isinstance(rows, dict) else 'empty'}",
                  flush=True)
            continue
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={"o": "Open", "h": "High", "l": "Low",
                                "c": "Close", "v": "Volume"})
        df["Symbol"] = sym
        frames.append(df[["Date", "Symbol", "Open", "High", "Low",
                          "Close", "Volume"]])
        ok += 1
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(syms)}] ok={ok} err={err} "
                  f"{time.time()-t0:.0f}s", flush=True)
    full = pd.concat(frames, ignore_index=True).sort_values(
        ["Symbol", "Date"]).reset_index(drop=True)
    full.to_parquet(OUT_PARQUET, index=False)
    print(f"m15 fetch: ok={ok} err={err}")
    print(f"m15 store: {len(full)} rows -> {OUT_PARQUET}")
    print("M15-READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
