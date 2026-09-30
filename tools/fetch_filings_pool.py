"""Reality's calendar for the particles: quarterly report filing dates for
the tradeable pool from the provider's financials endpoint.

Joe, 2026-09-30: "the analytics of the real are abundant." The pool's
releases are scheduled — the field's quarterly heartbeat is the reporting
calendar. This pulls each name's 10-Q/10-K filing dates (and the period
they cover) so a particle's position in its own reporting cycle is known.

Output: artifacts/ch2_life/filings_pool.parquet (Symbol, filing_date,
period_end, fiscal_period, fiscal_year, timeframe).
"""
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ch2_life" / "filings_pool.parquet"


def fetch(symbol, key):
    rows, url = [], f"https://api.polygon.io/vX/reference/financials?{urllib.parse.urlencode({'ticker': symbol, 'limit': 100, 'sort': 'filing_date', 'order': 'asc', 'apiKey': key})}"
    for _ in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                p = json.load(r)
        except Exception as e:  # noqa: BLE001
            time.sleep(2); err = e; continue
        for f in p.get("results") or []:
            rows.append((symbol, f.get("filing_date"), f.get("end_date"), f.get("fiscal_period"), f.get("fiscal_year"), f.get("timeframe")))
        nxt = p.get("next_url")
        if not nxt:
            return symbol, rows
        url = nxt + f"&apiKey={key}"
    return symbol, rows


def main():
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    symbols = sorted(pd.read_parquet(ROOT / "artifacts" / "ch2_life" / "ohlcv_pool.parquet", columns=["Symbol"]).Symbol.unique())
    have = set(pd.read_parquet(OUT, columns=["Symbol"]).Symbol.unique()) if OUT.exists() else set()
    todo = [s for s in symbols if s not in have]
    print(f"[filings] pool {len(symbols)}, stored {len(have)}, fetching {len(todo)}", flush=True)
    rows, t0 = [], time.time()
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(fetch, s, key) for s in todo]
        for i, f in enumerate(as_completed(futs), 1):
            s, r = f.result(); rows.extend(r)
            if i % 250 == 0:
                print(f"[filings] {i}/{len(todo)} {len(rows)} filings {time.time() - t0:.0f}s", flush=True)
    new = pd.DataFrame(rows, columns=["Symbol", "filing_date", "period_end", "fiscal_period", "fiscal_year", "timeframe"])
    if OUT.exists():
        new = pd.concat([pd.read_parquet(OUT), new], ignore_index=True)
    new = new.dropna(subset=["filing_date"]).drop_duplicates()
    new.to_parquet(OUT, index=False)
    print(f"[filings] wrote {OUT}: {new.Symbol.nunique()} symbols, {len(new)} filings", flush=True)


if __name__ == "__main__":
    main()
