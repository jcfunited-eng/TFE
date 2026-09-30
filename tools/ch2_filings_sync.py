#!/usr/bin/env python3
"""Reality's calendar, inside production: quarterly/annual filing dates for
the CH2 pool from the provider's financials endpoint into ch2_filings.

Full pass (--full): every name in the pool (about 3,700 calls; minutes).
Nightly pass (default): only names whose last stored filing is older than
75 days (the ones whose next report is due) — a few hundred calls.
Usage: python3 tools/ch2_filings_sync.py [--full]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ch2_field_nightly_db import connect, ensure_tables, load_pool  # noqa: E402

BASE = (os.environ.get("MASSIVE_API_URL") or "https://api.polygon.io").rstrip("/")


def fetch(symbol, key):
    rows, url = [], f"{BASE}/vX/reference/financials?{urllib.parse.urlencode({'ticker': symbol, 'limit': 100, 'sort': 'filing_date', 'order': 'desc', 'apiKey': key})}"
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                p = json.load(r)
        except Exception:  # noqa: BLE001
            time.sleep(2); continue
        for f in p.get("results") or []:
            if f.get("filing_date") and f.get("timeframe") in ("quarterly", "annual"):
                rows.append((symbol, f["filing_date"], f.get("end_date"), f["timeframe"]))
        return symbol, rows
    return symbol, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--full", action="store_true"); a = ap.parse_args()
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    conn = connect(); ensure_tables(conn)
    pool = [s for s in load_pool(conn) if s != "SPY"]
    if a.full:
        todo = pool
    else:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker, max(filing_date) FROM ch2_filings GROUP BY ticker"); last = dict(cur.fetchall())
        import datetime as dt
        cutoff = dt.date.today() - dt.timedelta(days=75)
        todo = [s for s in pool if s not in last or last[s] <= cutoff]
    print(f"[filings] pool {len(pool)}, fetching {len(todo)} ({'full' if a.full else 'due'})", flush=True)
    rows, t0 = [], time.time()
    with ThreadPoolExecutor(6) as ex:
        for i, f in enumerate(as_completed([ex.submit(fetch, s, key) for s in todo]), 1):
            rows.extend(f.result()[1])
            if i % 500 == 0:
                print(f"[filings] {i}/{len(todo)} {len(rows)} rows {time.time() - t0:.0f}s", flush=True)
    if rows:
        import psycopg2.extras
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, "INSERT INTO ch2_filings (ticker, filing_date, period_end, timeframe) VALUES %s ON CONFLICT (ticker, filing_date) DO NOTHING", rows, page_size=1000)
        conn.commit()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*), count(DISTINCT ticker), max(filing_date) FROM ch2_filings"); n, k, last = cur.fetchone()
    conn.close()
    print(f"[filings] ch2_filings now {n} rows, {k} names, latest {last} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
