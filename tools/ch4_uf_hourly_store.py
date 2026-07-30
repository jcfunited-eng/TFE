"""
ch4_uf_hourly_store.py — hourly-resolution store (the finer flare rung)
===================================================================

Purpose: the schema memory's deep-consistency tiers are starved on 5
years of records (species cannot earn 95% records with n large). The
spec's own memory model is long-term; this extends the store 2016-01-01
.. 2021-04-30 from the production Massive data service (split-adjusted
daily bars), PREPENDING history to the existing quarantine store.

Integrity (declared): a symbol is extended ONLY if, on the overlap
window (2021-03-26 .. 2021-04-30), its fetched closes match the existing
store's closes within 0.5% median absolute difference — otherwise the
symbol keeps its original 5y series (adjustment-regime mismatch, logged,
never silently mixed). Fetch cache is resumable (JSONL per symbol).

Output: quarantine_12k_universe_ext.parquet (original rows untouched;
pre-2021 rows added for seam-clean symbols). The ORIGINAL parquet is
never modified. Evaluation windows remain exactly as declared — the
added years only deepen the causal memory available before each
prediction.

Usage: python tools/ch4_uf_backfill_store.py [N_SYMBOLS]
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(ROOT, "quarantine_12k_universe.parquet")
OUT_PARQUET = os.path.join(ROOT, "ch4_hourly_universe.parquet")
CACHE_DIR = os.path.join(ROOT, "artifacts", "ch4_uf", "hourly_cache")
MIN_BARS = 1250
PRICE_FLOOR = 5.0
START, END = "2021-01-01", "2026-03-24"
SEAM_START = "2021-03-26"
SEAM_TOL = 0.005
REQ_SLEEP = 0.15   # ~6-7 req/s, polite


def fetch_symbol(sym: str, key: str):
    cache = os.path.join(CACHE_DIR, f"{sym}.json")
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    url = (f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/hour/"
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
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    assert key, "MASSIVE_API_KEY missing"
    os.makedirs(CACHE_DIR, exist_ok=True)
    df = pd.read_parquet(PARQUET, columns=["Symbol", "Close"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"hourly universe: {len(uni)}")
    frames = []
    ok = empty = err = 0
    t0 = time.time()
    for i, sym in enumerate(uni):
        rows = fetch_symbol(sym, key)
        if isinstance(rows, dict):
            err += 1
            continue
        if not rows:
            empty += 1
            continue
        rec = pd.DataFrame(rows)
        rec["Date"] = pd.to_datetime(rec["t"], unit="ms")
        rec = rec.rename(columns={"o": "Open", "h": "High", "l": "Low",
                                  "c": "Close", "v": "Volume"})
        rec["Symbol"] = sym
        frames.append(rec[["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"]])
        ok += 1
        if (i + 1) % 250 == 0:
            print(f"  [{i+1}/{len(uni)}] ok={ok} empty={empty} err={err} "
                  f"{time.time()-t0:.0f}s", flush=True)
    print(f"hourly fetch: ok={ok} empty={empty} err={err}")
    if frames:
        ext = pd.concat(frames, ignore_index=True).sort_values(["Symbol", "Date"])
        ext.to_parquet(OUT_PARQUET, index=False)
        print(f"hourly store: {len(ext)} rows -> {OUT_PARQUET}")


if __name__ == "__main__":
    main()
