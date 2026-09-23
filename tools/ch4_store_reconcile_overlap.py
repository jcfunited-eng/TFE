"""Reconcile the daily store after the provider re-bases a symbol's history.

tools/ch4_store_refresh.py refuses to publish when a stored close on the
overlap day (the store's last session) no longer equals the provider's
adjusted close for that day — a split or reverse split re-bases the whole
history, and appending new bars onto the old basis would corrupt every
trailing figure read from it. The refresh asks for "history reconciliation"
and nothing in the repo did it, so the store froze.

Receipt 2026-09-23: WHLR reverse-split 9:1 on 09-22 (its fifth split of
the year); the store held 0.2676 for 09-18, the provider 2.4084. The
close pass failed three times that night and the store sat at 09-18
while CH6's door, CH4's herd and CH3's tail all read from it.

What this does, and only this:
  1. take the store's overlap day and fetch the provider's grouped bars
     for it (the refresh's own call);
  2. list every roster symbol whose stored overlap close differs;
  3. for each, fetch the provider's current adjusted daily series over the
     symbol's stored span and REPLACE that symbol's rows with it — the
     provider's series is the truth for that symbol now; the provider's
     history endpoint must agree with its grouped endpoint on the overlap
     day or the symbol is refused;
  4. validate and publish atomically under the refresh's own lock.
Then the refresh runs clean. Symbols not on the roster and the untouched
histories are exactly as they were. A JSON receipt is printed.

Usage:  python tools/ch4_store_reconcile_overlap.py [--dry]
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.ch4_store_refresh import (  # noqa: E402
    COLUMNS, LIVE, ROSTER, fetch_day, publish_atomic, validate_frame,
)

LOCK = ROOT / "artifacts/vtvr_observer/.daily_store_refresh.lock"


def fetch_history(symbol: str, start: str, end: str, key: str) -> list[tuple]:
    query = urllib.parse.urlencode({"adjusted": "true", "sort": "asc",
                                    "limit": 50000, "apiKey": key})
    url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/"
           f"{start}/{end}?{query}")
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
    except Exception as error:  # noqa: BLE001 — loud, nothing published
        raise RuntimeError(f"provider history fetch failed for {symbol}: "
                           f"{type(error).__name__}") from None
    if payload.get("status") not in ("OK", "DELAYED") or not isinstance(payload.get("results"), list):
        raise RuntimeError(f"provider did not confirm a complete history for {symbol}")
    rows = []
    for bar in payload["results"]:
        day = dt.datetime.fromtimestamp(bar["t"] / 1000, dt.timezone.utc).date()
        rows.append((pd.Timestamp(day), symbol, float(bar["c"]), float(bar["v"])))
    return rows


def reconcile(frame: pd.DataFrame, roster: set, key: str, *, dry: bool) -> tuple[pd.DataFrame, dict]:
    overlap_day = frame.Date.max().date()
    grouped = {row["T"]: (float(row["c"]), float(row["v"]))
               for row in fetch_day(overlap_day.isoformat(), key) if row["T"] in roster}
    overlap = frame[frame.Date.dt.date == overlap_day].set_index("Symbol")
    changed = sorted(s for s in overlap.index
                     if s in grouped and grouped[s][0] != float(overlap.loc[s].Close))
    receipt = {"overlap_day": str(overlap_day), "roster_on_overlap": len(overlap),
               "changed": []}
    if not changed:
        receipt["status"] = "clean"
        return frame, receipt
    for symbol in changed:
        old = frame[frame.Symbol == symbol]
        start, end = old.Date.min().date(), overlap_day
        rows = [r for r in fetch_history(symbol, start.isoformat(), end.isoformat(), key)
                if start <= r[0].date() <= end]
        if not rows:
            raise RuntimeError(f"{symbol}: provider returned no history over {start}..{end}")
        on_overlap = [r for r in rows if r[0].date() == end]
        if not on_overlap or on_overlap[0][2] != grouped[symbol][0]:
            raise RuntimeError(f"{symbol}: history endpoint ({on_overlap[0][2] if on_overlap else None}) "
                               f"disagrees with grouped endpoint ({grouped[symbol][0]}) on {end}; refused")
        receipt["changed"].append({
            "symbol": symbol,
            "stored_close": float(overlap.loc[symbol].Close),
            "provider_close": grouped[symbol][0],
            "factor": round(grouped[symbol][0] / float(overlap.loc[symbol].Close), 6),
            "stored_rows": int(len(old)), "provider_rows": len(rows),
            "span": [str(start), str(end)],
        })
        if not dry:
            frame = frame[frame.Symbol != symbol]
            frame = pd.concat([frame, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
    receipt["status"] = "dry" if dry else "reconciled"
    if dry:
        return frame, receipt
    frame = validate_frame(frame.sort_values(["Symbol", "Date"]).reset_index(drop=True))
    return frame, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry", action="store_true", help="report, publish nothing")
    args = parser.parse_args()
    key = os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
    if not key:
        raise RuntimeError("Massive API key missing")
    with LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        frame = validate_frame(pd.read_parquet(LIVE, columns=COLUMNS))
        roster = {s for group in json.loads(ROSTER.read_text())["roster"] for s in group}
        proposed, receipt = reconcile(frame, roster, key, dry=args.dry)
        if receipt["status"] == "reconciled":
            publish_atomic(proposed, LIVE)
        print(json.dumps(receipt, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
