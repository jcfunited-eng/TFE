"""
ch3_supply_tail.py — restore CH3's missing supply stratum
=========================================================

FINDING (2026-08-13, surfaced by Joe's call of "bullshit" on the
drought story): 75% of the decade fade object's tradeable supply —
and the rich end of its edge (+2.66%/ev under harvest exits, vs
+1.07 for covered-but-cool names) — came from names with NO herd
coverage: young and small names outside the 5,016-name field roster,
plus names that have since died. The live store refreshes only the
roster, so the live pipe could reach ~2 events/day on 39% of days at
+0.73%/ev — a seventh of the morning's promised dollars. The nightly
refresh already downloads the WHOLE market (grouped daily, one call)
and discards the un-rostered rows. This tool keeps them.

A second, CH3-ONLY store: every US listing from the same source, no
roster filter, trailing window only (the engine needs 22 bars for z
and forward closes for settlement). The shared CH4 store is NOT
touched; CH4's field math is unaffected. Names already present in
the live store are excluded at scan time by the engine (they carry
herd rows; this file exists for the uncovered).

PRE-REGISTERED LIVE HYPOTHESIS (stated before the first tail trade):
the uncovered-stratum edge measured on the decade exists on TODAY'S
uncovered names, not only on the dead ones. The tripwire judges it —
v3 closures vs the harvest object, halt below the 5th percentile.

Output: ch3_supply_tail.parquet (Date, Symbol, Close, Volume)
Usage:  python tools/ch3_supply_tail.py  (idempotent; keeps ~80 sessions)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "ch3_supply_tail.parquet")
BACKFILL_SESSIONS = 45
KEEP_SESSIONS = 80
REQ_SLEEP = 0.15


def fetch_day(day: str, key: str):
    url = (f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/"
           f"{day}?adjusted=true&apiKey={key}")
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.loads(r.read())
    return d.get("results") or []


TICKERS_CACHE = os.path.join(ROOT, "artifacts", "ch4_uf",
                             "ch3_supply_tickers.json")


def common_stock_set(key: str):
    """Common stock + ADR tickers per the source's own metadata. The
    grouped feed includes warrants/units/rights — instrument classes
    the decade object never contained; they must not enter the book.
    Cached 7 days."""
    if os.path.exists(TICKERS_CACHE):
        cache = json.load(open(TICKERS_CACHE))
        age = time.time() - cache.get("fetched_at", 0)
        if age < 7 * 86400 and cache.get("tickers"):
            return set(cache["tickers"])
    tickers = []
    for typ in ("CS", "ADRC"):
        url = (f"https://api.polygon.io/v3/reference/tickers?market=stocks"
               f"&type={typ}&active=true&limit=1000&apiKey={key}")
        while url:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.loads(r.read())
            tickers += [t["ticker"] for t in d.get("results", [])]
            url = d.get("next_url")
            if url:
                url += f"&apiKey={key}"
            time.sleep(REQ_SLEEP)
    json.dump({"fetched_at": time.time(), "tickers": tickers},
              open(TICKERS_CACHE, "w"))
    return set(tickers)


def main():
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not key:
        print("no data key in environment")
        return 1

    have = None
    if os.path.exists(OUT):
        have = pd.read_parquet(OUT)
        have["Date"] = pd.to_datetime(have["Date"])
        start = have["Date"].max() + dt.timedelta(days=1)
    else:
        start = pd.Timestamp(dt.date.today() - dt.timedelta(
            days=int(BACKFILL_SESSIONS * 1.6)))

    frames = [] if have is None else [have]
    day = start.date()
    today = dt.date.today()
    fetched = 0
    while day <= today:
        if day.isoweekday() <= 5:
            try:
                res = fetch_day(day.isoformat(), key)
            except Exception as err:  # noqa: BLE001 — a bad day must not kill the tail
                print(f"  {day}: fetch failed ({type(err).__name__}), skipped")
                res = []
            if res:
                rows = [(pd.Timestamp(day), r["T"], float(r["c"]),
                         float(r.get("v") or 0.0))
                        for r in res
                        if r.get("T") and r.get("c") and float(r["c"]) > 0]
                frames.append(pd.DataFrame(
                    rows, columns=["Date", "Symbol", "Close", "Volume"]))
                fetched += 1
            time.sleep(REQ_SLEEP)
        day += dt.timedelta(days=1)

    if not frames:
        print("nothing fetched and no existing tail")
        return 1
    df = pd.concat(frames, ignore_index=True)
    cs = common_stock_set(key)
    before = df["Symbol"].nunique()
    df = df[df["Symbol"].isin(cs)]
    print(f"[supply-tail] instrument filter: {before} -> "
          f"{df['Symbol'].nunique()} names (common stock + ADR only)")
    df = df.drop_duplicates(subset=["Date", "Symbol"], keep="last")
    keep_days = sorted(df["Date"].unique())[-KEEP_SESSIONS:]
    df = df[df["Date"].isin(keep_days)].sort_values(["Symbol", "Date"])
    df.to_parquet(OUT, index=False)
    print(f"[supply-tail] fetched {fetched} new sessions; store now "
          f"{df['Date'].nunique()} sessions x {df['Symbol'].nunique()} names "
          f"({len(df)} rows) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
