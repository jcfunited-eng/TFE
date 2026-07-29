"""
run_market_vtvr_capture.py
===========================

NON-CANONICAL — one authenticated joint market capture through the isolated
TFE VTVR side kernel (see tools/isolated_market_vtvr_side_kernel.py).

This is the side kernel's lawful next walk-up step: real simultaneous market
observations, exact decimal custody from the wire (JSON numbers are parsed
directly into exact Fractions — no float ever touches a price), one joint
field, full receipts, and a human-readable view of the RELATION dimension
that the production per-ticker kernel cannot represent.

Read-only: uses the Alpaca market-data API only. No trading endpoint, no
database, no production import, no persistence beyond an optional JSON
receipt file passed as --out.

Usage:
    python tools/run_market_vtvr_capture.py MSBI HDB PHM TRMB \
        --timeframe 1Day --limit 30 [--out receipt.json]

Env: ALPACA_API_KEY/APCA_API_KEY_ID + ALPACA_API_SECRET_KEY/APCA_API_SECRET_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.isolated_market_vtvr_side_kernel import run_experience  # noqa: E402

DATA_URL = "https://data.alpaca.markets"


def _headers():
    key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY") or ""
    sec = (os.environ.get("APCA_API_SECRET_KEY")
           or os.environ.get("ALPACA_API_SECRET_KEY")
           or os.environ.get("ALPACA_SECRET_KEY") or "")
    if not key or not sec:
        raise SystemExit("Alpaca data keys missing from environment.")
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec}


def fetch_exact_bars(symbol: str, timeframe: str, limit: int, start_iso: str) -> dict:
    """Fetch bars, parsing every JSON number as an exact Fraction."""
    url = (f"{DATA_URL}/v2/stocks/{symbol}/bars"
           f"?timeframe={timeframe}&limit={limit}&feed=iex&adjustment=split"
           f"&start={start_iso}")
    req = urllib.request.Request(url, headers=_headers())
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    payload = json.loads(
        text,
        parse_float=lambda s: Fraction(s),
        parse_int=lambda s: Fraction(s),
    )
    bars = payload.get("bars") or []
    return {b["t"]: b["c"] for b in bars}  # ISO time -> exact close


def iso_to_rational_seconds(iso: str) -> Fraction:
    """Exact epoch seconds for ISO-8601 Z timestamps (no float)."""
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return Fraction(int(dt.astimezone(timezone.utc).timestamp()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+", help="2..64 tickers")
    ap.add_argument("--timeframe", default="1Day")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--days", type=int, default=60, help="lookback window in days")
    ap.add_argument("--out", default=None, help="optional receipt JSON path")
    args = ap.parse_args()

    from datetime import datetime, timedelta, timezone
    start_iso = (datetime.now(timezone.utc) - timedelta(days=args.days)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")

    symbols = [s.upper() for s in args.symbols]
    per_symbol = {
        s: fetch_exact_bars(s, args.timeframe, args.limit, start_iso)
        for s in symbols
    }

    # Simultaneity: keep only timestamps observed for EVERY vertex.
    common = sorted(set.intersection(*(set(d.keys()) for d in per_symbol.values())))
    if len(common) < 2:
        raise SystemExit("Fewer than 2 simultaneous observations across symbols.")

    times = [iso_to_rational_seconds(t) for t in common]
    observations = [[per_symbol[s][t] for s in symbols] for t in common]

    exp = run_experience(symbols, times, observations)
    f = exp.l0

    print("=" * 70)
    print("NON-CANONICAL JOINT MARKET VTVR CAPTURE")
    print("=" * 70)
    print(f"Vertices (N={len(symbols)}): {', '.join(symbols)}")
    print(f"Simultaneous observations (M={len(common)}): "
          f"{common[0]} .. {common[-1]}")
    print(f"Edges retained per time: {len(f.relations[0])}")
    print(f"Quiescent: {exp.l3.quiescent}")
    print()
    print("Receipts:")
    print(f"  H_raw        = {f.h_raw}")
    for name, h in exp.h_layers.items():
        print(f"  H_{name:<10} = {h}")
    print(f"  H_experience = {exp.h_experience}")
    print()

    # Componentwise swept volume (never summed across vertices for authority)
    print("Accumulated swept volume per vertex (exact, shown to 6dp):")
    for s, v in zip(symbols, f.volume_accum):
        print(f"  {s:<6} {float(v):.6f}")
    print()

    # The relation field: strongest lead-lag (wedge) edges over the window
    wedge_max: dict = {}
    for k, row in enumerate(f.relations):
        for r in row:
            key = (r.i, r.j)
            mag = abs(r.r_wedge)
            if key not in wedge_max or mag > wedge_max[key][0]:
                wedge_max[key] = (mag, k)
    ranked = sorted(wedge_max.items(), key=lambda kv: kv[1][0], reverse=True)
    print("Lead-lag structure (oriented-area wedge, invisible to the")
    print("production per-ticker kernel) — strongest edges:")
    for (i, j), (mag, k) in ranked[:6]:
        print(f"  {symbols[i]}~{symbols[j]:<6} max |wedge| = {float(mag):.3e} "
              f"at {common[k]}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({
                "symbols": symbols,
                "times_iso": common,
                "h_raw": f.h_raw,
                "h_layers": exp.h_layers,
                "h_experience": exp.h_experience,
            }, fh, indent=2)
        print(f"\nReceipt written: {args.out}")


if __name__ == "__main__":
    main()
