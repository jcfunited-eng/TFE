"""
ch_premarket_cut.py — desk floor #10: a position already beyond its cut
line before the open is cut at the first available price, never held
for a scheduled check. Runs 13:00-13:30 UTC via the CH6 loop; covers
BOTH books. Joseph 2026-08-19: "who in their right mind would shoot
themselves."

Rule 11 rebuild 2026-08-19: atomic saves through each engine's own
loader (never raw json.dump over a live book), one batched quote call,
loud reporting of every symbol that could not be quoted (a silent skip
defeats the protection), CH3 records filtered to this engine family's
open shorts only, and carry costs charged on CH3 cuts exactly as the
engine itself charges them.
"""
from __future__ import annotations

import fcntl
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from ch_desk import calendar_days, carry_costs  # noqa: E402

CUT_PCT = 20.0
NOTE = "premarket cut, desk floor #10"
LOCK_PATH = ROOT / "artifacts" / "vtvr_observer" / ".premarket_cut.lock"


def _alpaca_keys() -> dict:
    keys = {}
    for line in open(ROOT / ".env"):
        for name in ("ALPACA_API_KEY", "ALPACA_API_SECRET_KEY"):
            if line.startswith(f"{name}="):
                keys[name] = line.split("=", 1)[1].strip().strip('"')
    if len(keys) != 2:
        raise RuntimeError("Alpaca keys missing from .env")
    return keys


def latest_marks(symbols: list) -> dict:
    """One batched latest-trade call. Returns {symbol: price} for every
    symbol a price came back for; callers must treat absence loudly."""
    if not symbols:
        return {}
    keys = _alpaca_keys()
    marks = {}
    batch = sorted(set(str(s).upper() for s in symbols))
    for start in range(0, len(batch), 100):
        chunk = batch[start:start + 100]
        req = urllib.request.Request(
            "https://data.alpaca.markets/v2/stocks/trades/latest"
            f"?feed=iex&symbols={','.join(chunk)}",
            headers={"APCA-API-KEY-ID": keys["ALPACA_API_KEY"],
                     "APCA-API-SECRET-KEY": keys["ALPACA_API_SECRET_KEY"]})
        payload = json.load(urllib.request.urlopen(req, timeout=30))
        for sym, trade in (payload.get("trades") or {}).items():
            price = float(trade.get("p", 0.0))
            if price > 0:
                marks[sym] = price
    return marks


def main() -> None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[premarket-cut] another run holds the lock; standing down")
        return

    from ch6_fast_harvest import close_position, closed, load_book, positions, save_book
    from ch3_reveal_fade import ENGINE_FAMILY as CH3_FAMILY
    from ch3_reveal_fade import load_log, save_log

    now = datetime.now(timezone.utc).isoformat()
    today = now[:10]

    book = load_book()
    log = load_log()
    ch3_open = [f for f in log["finds"]
                if isinstance(f, dict) and f.get("status") == "OPEN"
                and str(f.get("engine", "")).startswith(CH3_FAMILY)
                and int(f.get("side", -1)) == -1]
    wanted = sorted(set(positions(book).keys())
                    | {str(f["symbol"]) for f in ch3_open})
    if not wanted:
        print("[premarket-cut] no open positions in either book")
        return

    try:
        marks = latest_marks(wanted)
    except Exception as err:  # noqa: BLE001 — the whole feed failed; say so
        print(f"[premarket-cut] QUOTE FEED FAILED ({type(err).__name__}: {err}) "
              f"— NO positions checked; {len(wanted)} unprotected until next pass")
        return
    unquoted = [s for s in wanted if s not in marks]
    if unquoted:
        print(f"[premarket-cut] WARNING: no quote for {', '.join(unquoted)} "
              "— these stay UNCHECKED and unprotected this pass")

    cut6 = 0
    for sym, pos in list(positions(book).items()):
        price = marks.get(sym)
        if price is None:
            continue
        if 100 * (price / float(pos["entry_px"]) - 1) >= CUT_PCT:  # short 20% underwater
            close_position(book, sym, pos, price, "ANOMALY-CUT", now)
            closed(book)[-1]["note"] = NOTE
            cut6 += 1
    if cut6:
        save_book(book)

    cut3 = 0
    for find in ch3_open:
        price = marks.get(str(find["symbol"]))
        if price is None:
            continue
        entry = float(find["entry_px"])
        if 100 * (price / entry - 1) < CUT_PCT:
            continue
        notional = float(find["notional"])
        short_return = 100 * (1 - price / entry)
        pnl = round(notional * short_return / 100, 2)
        pnl = round(pnl - carry_costs(notional,
                                      float(find.get("normal_day_dollars", 0.0)),
                                      calendar_days(str(find.get("date", today)),
                                                    today)), 2)
        log["book"]["cash"] = round(float(log["book"]["cash"]) + notional + pnl, 2)
        find.update(status="ANOMALY-CUT", resolved=now,
                    ret_pct=round(short_return, 2), pnl=pnl,
                    exit_px=round(price, 4), note=NOTE)
        print(f"  ANOMALY-CUT {find['symbol']} @{price:.2f} "
              f"ret {short_return:+.2f}% pnl ${pnl:+,.2f} (CH3 premarket)")
        cut3 += 1
    if cut3:
        save_log(log)

    print(f"[premarket-cut] checked {len(marks)}/{len(wanted)}; "
          f"ch6 cut {cut6}, ch3 cut {cut3}")


if __name__ == "__main__":
    main()
