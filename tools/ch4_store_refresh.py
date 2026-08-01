"""
ch4_store_refresh.py — bring the daily store current for the live engine
========================================================================

The research store (quarantine_12k_universe_ext.parquet) ends
2026-03-24. The live nightly pass needs bars through today, from the
SAME data source and adjustment regime (Massive grouped-daily,
adjusted): one request per missing trading day, all symbols at once,
filtered to the eligible roster.

Seam integrity (declared): any symbol whose close jumps by more than
1.8x across the seam (a split/adjustment-regime break in the gap) is
DROPPED from the live store and logged — never silently mixed.

Output: ch4_live_store.parquet (research store + appended tail).
Idempotent: refreshes from the live store's own max date when present.
Usage: python tools/ch4_store_refresh.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
LIVE = os.path.join(ROOT, "ch4_live_store.parquet")
ROSTER = os.path.join(ROOT, "artifacts", "ch4_uf", "ch4_field_cohorts.json")
SEAM_RATIO = 1.8
REQ_SLEEP = 0.15


def fetch_day(day: str, key: str):
    url = (f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/"
           f"{day}?adjusted=true&apiKey={key}")
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.loads(r.read())
    return d.get("results") or []


def main():
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not key:
        print("no data key in environment")
        return 1
    roster = set(s for c in json.load(open(ROSTER))["roster"] for s in c)
    src = LIVE if os.path.exists(LIVE) else BASE
    df = pd.read_parquet(src)
    df["Date"] = pd.to_datetime(df["Date"])
    last = df["Date"].max().date()
    today = dt.datetime.now(dt.timezone.utc).date()
    print(f"store {os.path.basename(src)} ends {last}; refreshing to {today}")

    rows = []
    day = last + dt.timedelta(days=1)
    fetched_days = 0
    while day <= today:
        if day.weekday() < 5:
            try:
                res = fetch_day(day.isoformat(), key)
            except Exception as e:
                print(f"  {day}: fetch failed ({e})")
                res = []
            for rec in res:
                sym = rec.get("T")
                if sym in roster and rec.get("c") is not None:
                    rows.append((pd.Timestamp(day), sym, float(rec["c"]),
                                 float(rec.get("v") or 0.0)))
            if res:
                fetched_days += 1
            time.sleep(REQ_SLEEP)
        day += dt.timedelta(days=1)
    print(f"fetched {fetched_days} trading days, {len(rows)} rows")
    if not rows:
        if src != LIVE:
            df.to_parquet(LIVE, index=False)
            print(f"no gap rows; live store initialized from base -> {LIVE}")
        else:
            print("already current")
        return 0

    tail = pd.DataFrame(rows, columns=["Date", "Symbol", "Close", "Volume"])
    # seam check: last base close vs first tail close per symbol
    base_last = df.sort_values("Date").groupby("Symbol")["Close"].last()
    tail_first = tail.sort_values("Date").groupby("Symbol")["Close"].first()
    joined = pd.concat([base_last, tail_first], axis=1, keys=["b", "t"]).dropna()
    ratio = (joined["t"] / joined["b"]).clip(lower=1e-9)
    bad = set(joined[(ratio > SEAM_RATIO) | (ratio < 1 / SEAM_RATIO)].index)
    if bad:
        print(f"seam breaks dropped from live store ({len(bad)}): "
              f"{sorted(bad)[:20]}{'...' if len(bad) > 20 else ''}")
    keep_cols = [c for c in df.columns if c in
                 ("Date", "Symbol", "Close", "Volume")]
    out = pd.concat([df[keep_cols][~df["Symbol"].isin(bad)],
                     tail[~tail["Symbol"].isin(bad)]], ignore_index=True)
    out = out.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    out.to_parquet(LIVE, index=False)
    print(f"live store: {len(out)} rows, "
          f"{out['Symbol'].nunique()} symbols, ends {out['Date'].max().date()}"
          f" -> {LIVE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
