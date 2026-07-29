"""
vtvr_universe_builder.py
=========================

NON-CANONICAL — declared full-scale universe for the CH4 joint-field
channel. Mechanical rule, no outcome peeking:

  1. All active, tradable, exchange-listed US equities at Alpaca
     (NYSE/NASDAQ/ARCA/BATS/AMEX), excluding dot-class tickers.
  2. Liquidity: rank by 30-day average dollar volume (IEX snapshots).
  3. Sanity: last price between $5 and $1,000.
  4. Take the top N (default 300), alphabetize, freeze to JSON.

The frozen list is committed so every future run uses the same declared
universe. Usage:
    python tools/vtvr_universe_builder.py [N] [out.json]
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

DATA_URL = "https://data.alpaca.markets"
TRADE_URL = "https://paper-api.alpaca.markets"
DEFAULT_N = 300
DEFAULT_OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tools", "vtvr_universe_300.json",
)


def _headers():
    key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY") or ""
    sec = (os.environ.get("APCA_API_SECRET_KEY")
           or os.environ.get("ALPACA_API_SECRET_KEY")
           or os.environ.get("ALPACA_SECRET_KEY") or "")
    if not key or not sec:
        raise SystemExit("Alpaca keys missing from environment.")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def get(url):
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_N
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT

    print("Fetching active tradable assets...")
    assets = get(f"{TRADE_URL}/v2/assets?status=active&asset_class=us_equity")
    symbols = sorted(
        a["symbol"] for a in assets
        if a.get("tradable")
        and a.get("exchange") in ("NYSE", "NASDAQ", "ARCA", "BATS", "AMEX")
        and "." not in a["symbol"] and "/" not in a["symbol"]
        and len(a["symbol"]) <= 5
    )
    print(f"Eligible symbols: {len(symbols)}")

    # 30-day dollar volume via daily bars, batched
    print("Ranking by 30-day dollar volume (batched bars)...")
    from datetime import datetime, timedelta, timezone
    start = (datetime.now(timezone.utc) - timedelta(days=45)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    dollar_vol = {}
    last_px = {}
    B = 200
    for b in range(0, len(symbols), B):
        batch = symbols[b:b + B]
        url = (f"{DATA_URL}/v2/stocks/bars?symbols={','.join(batch)}"
               f"&timeframe=1Day&start={start}&limit=10000&feed=iex")
        try:
            data = get(url)
        except Exception as e:
            print(f"  batch {b//B}: failed ({e}) — skipped")
            continue
        for sym, bars in (data.get("bars") or {}).items():
            if not bars:
                continue
            dv = sum(bar["c"] * bar["v"] for bar in bars) / len(bars)
            dollar_vol[sym] = dv
            last_px[sym] = bars[-1]["c"]
        if (b // B) % 10 == 0:
            print(f"  ...{b + len(batch)}/{len(symbols)}")

    ranked = sorted(
        (s for s in dollar_vol
         if 5.0 <= last_px.get(s, 0) <= 1000.0),
        key=lambda s: dollar_vol[s], reverse=True,
    )[:n_target]
    universe = sorted(ranked)
    print(f"Universe frozen: {len(universe)} symbols")

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({
            "generated": datetime.now(timezone.utc).isoformat(),
            "rule": "top dollar-volume, active tradable exchange-listed, $5-$1000",
            "n": len(universe),
            "symbols": universe,
        }, fh, indent=1)
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
