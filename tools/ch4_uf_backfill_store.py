"""
ch4_uf_backfill_store.py — extend the evaluation store back to 2016
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
OUT_PARQUET = os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
CACHE_DIR = os.path.join(ROOT, "artifacts", "ch4_uf", "backfill_cache")
MIN_BARS = 1250
PRICE_FLOOR = 5.0
START, END = "2016-01-01", "2021-04-30"
SEAM_START = "2021-03-26"
SEAM_TOL = 0.005
REQ_SLEEP = 0.15   # ~6-7 req/s, polite


def fetch_symbol(sym: str, key: str):
    cache = os.path.join(CACHE_DIR, f"{sym}.json")
    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)
    url = (f"https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/day/"
           f"{START}/{END}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            d = json.loads(r.read())
        rows = [
            {"t": rec["t"], "o": rec.get("o"), "h": rec.get("h"),
             "l": rec.get("l"), "c": rec.get("c"), "v": rec.get("v")}
            for rec in (d.get("results") or [])
        ]
    except Exception as e:
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

    df = pd.read_parquet(PARQUET)
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe to backfill: {len(uni)}")

    seam_ref = {}
    sub_all = df[df["Date"] >= SEAM_START]
    for sym, grp in sub_all.groupby("Symbol"):
        seam_ref[sym] = {d.strftime("%Y-%m-%d"): c
                         for d, c in zip(grp["Date"], grp["Close"])}

    added_frames = []
    ok = mismatch = empty = err = 0
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
        rec["Date"] = pd.to_datetime(rec["t"], unit="ms").dt.normalize()
        rec = rec.rename(columns={"o": "Open", "h": "High", "l": "Low",
                                  "c": "Close", "v": "Volume"})
        # seam check on overlap dates
        ref = seam_ref.get(sym, {})
        ov = rec[rec["Date"] >= SEAM_START]
        diffs = []
        for d, c in zip(ov["Date"], ov["Close"]):
            k = d.strftime("%Y-%m-%d")
            if k in ref and ref[k] > 0:
                diffs.append(abs(c / ref[k] - 1.0))
        if len(diffs) < 5 or float(np.median(diffs)) > SEAM_TOL:
            mismatch += 1
            continue
        pre = rec[rec["Date"] < df["Date"].min()][
            ["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
        if pre.empty:
            empty += 1
            continue
        pre["Symbol"] = sym
        added_frames.append(pre)
        ok += 1
        if (i + 1) % 250 == 0:
            el = time.time() - t0
            print(f"  [{i+1}/{len(uni)}] ok={ok} mismatch={mismatch} "
                  f"empty={empty} err={err} elapsed={el:.0f}s", flush=True)

    print(f"backfill: ok={ok} mismatch={mismatch} empty={empty} err={err}")
    if added_frames:
        add = pd.concat(added_frames, ignore_index=True)
        ext = pd.concat([df, add], ignore_index=True).sort_values(["Symbol", "Date"])
        ext.to_parquet(OUT_PARQUET, index=False)
        print(f"extended store: {len(ext)} rows -> {OUT_PARQUET}")
    else:
        print("nothing added")


if __name__ == "__main__":
    main()
