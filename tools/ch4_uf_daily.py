"""
ch4_uf_daily.py — CH4 UF-engine forward paper book (daily, causal, live)
========================================================================

The forward evidence channel for the true-to-original CH4 engine: each
weekday after the close, evaluate the FULL known history of every universe
symbol through the unflattened kernel + L5 governance (RAW field mode —
declared primary) and update the paper book. PAPER ONLY; no trading API;
never touches production.

DECLARED MECHANICS (fixed before first run, identical to the filed
whole-history evaluation):
  Universe   — cohorts A + B (60 names, the CH4 side channel's declared
               universes; symbols only, no selection by outcome).
  Entry      — fresh CP-2 governed ACCUMULATE (resonance ignition +
               F_n <= 1.65, x_m <= 0.50), close >= $5, at that close.
  Exit       — first extinction (AVOID) event or +20 bars, whichever
               first.
  Sizing     — $100,000 book, 10% equity slices, max 10 concurrent, one
               position per symbol.
  Same-bar guard — a bar is processed at most once; holidays are no-ops.

State: artifacts/ch4_uf/ch4_uf_live_book.json
Usage: python tools/ch4_uf_daily.py            # process latest closed bar
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_engine import replay_symbol  # noqa: E402
from tools.vtvr_star_state_replication import COHORT_B  # noqa: E402

COHORT_A = ["MSBI", "HDB", "PHM", "TRMB", "DORM", "NBIX", "BDX", "VRTS",
            "DEI", "PFE", "UNH", "HD", "PEP", "KO", "JNJ", "PG", "XOM",
            "CVX", "JPM", "BAC", "WMT", "COST", "CAT", "DE", "LIN", "AAPL",
            "MSFT", "AMZN", "NVDA", "GOOGL"]

BOOK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "artifacts", "ch4_uf", "ch4_uf_live_book.json")
FIELD_MODE = "RAW"
CASH0 = 100_000.0
SLICE = 0.10
MAX_POS = 10
HORIZON = 20
PRICE_FLOOR = 5.0
MIN_BARS = 300


def _load_universe_a():
    """Cohort A authoritative list from the structure-search module when
    importable; falls back to the frozen copy above (same 30 names)."""
    try:
        import tools.vtvr_structure_search as vss
        u = getattr(vss, "UNIVERSE", None) or getattr(vss, "COHORT_A", None)
        if u:
            return list(u)
    except Exception:
        pass
    return COHORT_A


def fetch_daily_closes(symbol: str, limit: int = 1600):
    key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY", "")
    sec = (os.environ.get("APCA_API_SECRET_KEY")
           or os.environ.get("ALPACA_API_SECRET_KEY", ""))
    url = (f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?timeframe=1Day"
           f"&limit={limit}&adjustment=split&feed=iex&sort=asc")
    req = urllib.request.Request(url, headers={
        "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    bars = data.get("bars") or []
    dates = [b["t"][:10] for b in bars]
    closes = np.array([float(b["c"]) for b in bars])
    # today's bar counts as CLOSED only after 20:30 UTC (16:30 ET);
    # before that it is forming and is dropped
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    if dates and dates[-1] == today and (now.hour * 60 + now.minute) < 20 * 60 + 30:
        dates, closes = dates[:-1], closes[:-1]
    return dates, closes


def load_book():
    if os.path.exists(BOOK_PATH):
        with open(BOOK_PATH) as f:
            return json.load(f)
    return {"cash": CASH0, "positions": {}, "closed": [],
            "last_processed": None, "field_mode": FIELD_MODE,
            "declared": "10% slices, max 10, exit extinction or +20 bars"}


def save_book(book):
    os.makedirs(os.path.dirname(BOOK_PATH), exist_ok=True)
    with open(BOOK_PATH, "w") as f:
        json.dump(book, f, indent=1)


def main() -> int:
    universe = sorted(set(_load_universe_a() + list(COHORT_B)))
    book = load_book()

    evals = {}
    bar_date = None
    for sym in universe:
        try:
            dates, closes = fetch_daily_closes(sym)
        except Exception as e:
            print(f"  {sym}: fetch failed {e}")
            continue
        if len(closes) < MIN_BARS:
            print(f"  {sym}: only {len(closes)} bars, skipped")
            continue
        states = replay_symbol(dates, closes, field_mode=FIELD_MODE,
                               warmup=max(0, len(closes) - 2))
        s = states[-1]
        s_prev = states[-2] if len(states) >= 2 else None
        fresh = (s is not None and s.action_cp2 == "ACCUMULATE"
                 and (s_prev is None or s_prev.action_cp2 != "ACCUMULATE"))
        evals[sym] = {"date": dates[-1], "close": float(closes[-1]),
                      "action": s.action_cp2 if s else None,
                      "fresh_accumulate": bool(fresh),
                      "n_bars": len(closes)}
        bar_date = max(bar_date or dates[-1], dates[-1])

    if not evals:
        print("no evaluations; abort")
        return 1

    if book["last_processed"] == bar_date:
        print(f"bar {bar_date} already processed; no-op")
        return 0

    # exits
    for sym in sorted(list(book["positions"].keys())):
        pos = book["positions"][sym]
        ev = evals.get(sym)
        if ev is None or ev["date"] != bar_date:
            continue
        pos["bars_held"] = pos.get("bars_held", 0) + 1
        hit_avoid = ev["action"] == "AVOID"
        at_horizon = pos["bars_held"] >= HORIZON
        if hit_avoid or at_horizon:
            px = ev["close"]
            pnl = pos["shares"] * (px - pos["entry_px"])
            book["cash"] += pos["shares"] * px
            book["closed"].append({
                "sym": sym, "entry_date": pos["entry_date"], "exit_date": bar_date,
                "entry_px": pos["entry_px"], "exit_px": px,
                "bars_held": pos["bars_held"],
                "reason": "AVOID" if hit_avoid else "HORIZON",
                "ret_pct": round(100.0 * (px / pos["entry_px"] - 1.0), 3),
                "pnl": round(pnl, 2),
            })
            del book["positions"][sym]

    # entries — fresh ACCUMULATE only (today governed ACCUMULATE, yesterday
    # not), matching the filed backtest's signal definition exactly
    equity = book["cash"] + sum(
        p["shares"] * evals.get(s, {"close": p["entry_px"]})["close"]
        for s, p in book["positions"].items())
    for sym in sorted(evals.keys()):
        ev = evals[sym]
        if ev["date"] != bar_date:
            continue  # stale feed for this symbol — never enter on old bars
        if not ev.get("fresh_accumulate") or ev["close"] < PRICE_FLOOR:
            continue
        if sym in book["positions"] or len(book["positions"]) >= MAX_POS:
            continue
        budget = min(book["cash"], SLICE * equity)
        if budget <= 0:
            continue
        shares = budget / ev["close"]
        book["positions"][sym] = {
            "shares": shares, "entry_px": ev["close"],
            "entry_date": bar_date, "bars_held": 0,
        }
        book["cash"] -= shares * ev["close"]

    book["last_processed"] = bar_date
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    book["equity_mark"] = round(book["cash"] + sum(
        p["shares"] * evals.get(s, {"close": p["entry_px"]})["close"]
        for s, p in book["positions"].items()), 2)
    save_book(book)
    print(f"bar {bar_date}: open={len(book['positions'])} "
          f"closed_total={len(book['closed'])} cash=${book['cash']:,.2f} "
          f"equity=${book['equity_mark']:,.2f}")
    actions = {s: e["action"] for s, e in evals.items() if e["action"] not in (None, "HOLD")}
    if actions:
        print("non-HOLD today:", actions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
