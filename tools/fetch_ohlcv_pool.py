"""Fetch full daily bars (Open, High, Low, Close, Volume; adjusted) for the
tradable pool from the provider and store them as one parquet.

The kernel's field is the whole bar (Joe, 2026-09-30). The store
(ch4_live_store.parquet) holds only Close and Volume.

Universe: artifacts/ch2_life/universe_tradable_20260930.csv (the live CH2
entry pool) intersected with names having >= 1,000 closes in the store.
Output: artifacts/ch2_life/ohlcv_pool.parquet (Date, Symbol, Open, High,
Low, Close, Volume). Re-runs skip symbols already present.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet"
START, END = "2016-01-01", "2026-09-29"


def fetch(symbol, key):
    q = urllib.parse.urlencode({"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": key})
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{START}/{END}?{q}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                p = json.load(r)
            if p.get("status") not in ("OK", "DELAYED"):
                raise RuntimeError(p.get("status"))
            return symbol, [(dt.datetime.fromtimestamp(b["t"] / 1000, dt.timezone.utc).date(), symbol,
                             float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"]), float(b["v"])) for b in p.get("results") or []]
        except Exception as e:  # noqa: BLE001
            time.sleep(2 * (attempt + 1))
            err = e
    return symbol, err


def main():
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    uni = set(pd.read_csv(ROOT / "artifacts" / "ch2_life" / "universe_tradable_20260930.csv").ticker)
    store = pd.read_parquet(ROOT / "ch4_live_store.parquet", columns=["Symbol"])
    counts = store.Symbol.value_counts()
    symbols = sorted(s for s in uni if counts.get(s, 0) >= 1000)
    have = set(pd.read_parquet(OUT, columns=["Symbol"]).Symbol.unique()) if OUT.exists() else set()
    todo = [s for s in symbols if s not in have]
    print(f"[ohlcv] pool {len(symbols)}, already stored {len(have)}, fetching {len(todo)}", flush=True)
    rows, failed, t0 = [], [], time.time()
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(fetch, s, key) for s in todo]
        for i, f in enumerate(as_completed(futs), 1):
            s, res = f.result()
            if isinstance(res, list):
                rows.extend(res)
            else:
                failed.append((s, str(res)))
            if i % 200 == 0:
                print(f"[ohlcv] {i}/{len(todo)} symbols, {len(rows)} bars, {time.time() - t0:.0f}s, failed {len(failed)}", flush=True)
    new = pd.DataFrame(rows, columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    new["Date"] = pd.to_datetime(new.Date)
    if OUT.exists():
        new = pd.concat([pd.read_parquet(OUT), new], ignore_index=True)
    new.sort_values(["Symbol", "Date"]).to_parquet(OUT, index=False)
    print(f"[ohlcv] wrote {OUT}: {new.Symbol.nunique()} symbols, {len(new)} bars; failed {failed[:10]}{'...' if len(failed) > 10 else ''}", flush=True)


if __name__ == "__main__":
    main()
