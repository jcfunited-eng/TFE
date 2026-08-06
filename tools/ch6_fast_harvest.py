"""
ch6_fast_harvest.py — CH6: CH3's entries, Joe's exits (2026-08-06)
==================================================================

ENGINE VERSION: ch6_fast_harvest_v1. Hypothesis (Joe's): the fade
front-loads — harvest any short past +5% the same day instead of
holding 5 sessions.

Rules (constants declared 2026-08-06 before first trade):
  START    clean book, NO inherited positions (Joe: "I don't want to
           cheat") — only CH3 entries dated >= START_DATE are adopted.
  ENTRIES  mirror CH3 (ch3_reveal_fade) exactly: whenever CH3's book
           has an OPEN position dated >= START_DATE that CH6 doesn't
           know, CH6 adopts it at CH3's entry price/shares into its
           own $100k book.
  ARM      a position whose gain reaches ARM_PCT (+5%) is armed;
           its peak gain is tracked from then on.
  HARVEST  armed + gain gives back > GIVEBACK_PP from peak -> sell now.
           armed at the end-of-day sweep (EOD_SWEEP) -> sell at mark.
  BACKSTOP never-armed positions exit after HOLD_SESSIONS (5) at the
           day's mark, same as CH3's time exit.
  No loss-stop. One variable only: the harvest rule.

CH3 house rules carry over: shorts only, one position per symbol,
whole shares, $2k stakes as adopted, borrow costs NOT modeled (stated
on the page), and the freeze discipline — these constants are FROZEN
until 20 CH6 positions have closed; no retuning on the way.
Known divergence, declared: CH6's sweep/backstop exits price at the
19:55 UTC mark (5-min feed), not the official close CH3 settles on.

Usage:
  python tools/ch6_fast_harvest.py sync     # adopt new CH3 entries
  python tools/ch6_fast_harvest.py poll     # 5-min check: arm/harvest
  python tools/ch6_fast_harvest.py sweep    # end-of-day: sell armed, time exits
Loop: tools/ch6_loop.sh (poll every 5 min in market hours; sweep 19:55 UTC).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENGINE = "ch6_fast_harvest_v1"
START_DATE = "2026-08-07"      # no positions born before this — no cheating
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH3_LOG = os.path.join(ROOT, "artifacts", "vtvr_observer", "ch3_shadow_log.json")
BOOK_PATH = os.path.join(ROOT, "artifacts", "vtvr_observer", "ch6_book.json")
CASH0 = 100_000.0
ARM_PCT = 5.0          # gain that arms a position
GIVEBACK_PP = 1.0      # points off peak gain that forces a sale
HOLD_SESSIONS = 5      # backstop, same as CH3


def load_book():
    if os.path.exists(BOOK_PATH):
        return json.load(open(BOOK_PATH))
    return {"engine": ENGINE, "cash": CASH0, "start": CASH0,
            "positions": {}, "closed": []}


def save_book(book):
    book["engine"] = ENGINE
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(BOOK_PATH), exist_ok=True)
    with open(BOOK_PATH, "w") as f:
        json.dump(book, f, indent=1)


def sync():
    """Adopt CH3's open positions CH6 doesn't hold yet, at CH3's basis."""
    book = load_book()
    log = json.load(open(CH3_LOG))
    known = set(book["positions"]) | {t["symbol"] for t in book["closed"]
                                      if t.get("ch3_entry_date")
                                      == t.get("entry_date")}
    adopted = 0
    for f in log.get("finds", []):
        if f.get("engine") != "ch3_reveal_fade_v1.1" or f["status"] != "OPEN":
            continue
        if f["date"] < START_DATE:
            continue
        sym = f["symbol"]
        # adopt only positions we have never held for this entry date
        held_same = any(t["symbol"] == sym and t.get("entry_date")
                        == f["date"] for t in book["closed"])
        if sym in book["positions"] or held_same:
            continue
        notional = f["notional"]
        if book["cash"] < notional:
            print(f"  skip {sym}: insufficient cash")
            continue
        book["positions"][sym] = {
            "side": f["side"], "entry_px": f["entry_px"],
            "shares": f.get("shares") or int(notional // f["entry_px"]),
            "notional": notional, "entry_date": f["date"],
            "armed": False, "peak_gain_pct": 0.0}
        book["cash"] = round(book["cash"] - notional, 2)
        adopted += 1
    save_book(book)
    print(f"[ch6 sync] adopted {adopted}, open {len(book['positions'])}, "
          f"cash ${book['cash']:,.2f}")


def _close(book, sym, p, px, reason, now):
    ret = 100 * (px / p["entry_px"] - 1.0) * p["side"]
    pnl = round(p["shares"] * (px - p["entry_px"]) * p["side"], 2)
    book["cash"] = round(book["cash"] + p["notional"] + pnl, 2)
    book["closed"].append({
        "symbol": sym, "side": p["side"], "shares": p["shares"],
        "entry_px": p["entry_px"], "exit_px": round(px, 4),
        "entry_date": p["entry_date"], "exit_at": now,
        "ret_pct": round(ret, 2), "pnl": pnl, "reason": reason,
        "peak_gain_pct": p.get("peak_gain_pct", 0.0)})
    del book["positions"][sym]
    print(f"  {reason} {sym} @{px:.2f} ret {ret:+.2f}% pnl ${pnl:+,.2f}")


def poll():
    """5-minute check: update peaks, arm at +5%, harvest give-backs."""
    from tools.ch3_shadow_hunter import last_price
    book = load_book()
    now = datetime.now(timezone.utc).isoformat()
    for sym in sorted(list(book["positions"].keys())):
        p = book["positions"][sym]
        try:
            px = last_price(sym)
        except Exception:
            continue
        if not px:
            continue
        gain = 100 * (px / p["entry_px"] - 1.0) * p["side"]
        if gain > p.get("peak_gain_pct", 0.0):
            p["peak_gain_pct"] = round(gain, 3)
        if not p["armed"] and gain >= ARM_PCT:
            p["armed"] = True
            print(f"  ARMED {sym} at {gain:+.2f}%")
        if p["armed"] and p["peak_gain_pct"] - gain > GIVEBACK_PP:
            _close(book, sym, p, px, "GIVEBACK", now)
    save_book(book)
    print(f"[ch6 poll] open {len(book['positions'])} "
          f"armed {sum(1 for p in book['positions'].values() if p['armed'])} "
          f"cash ${book['cash']:,.2f}")


def sweep():
    """End of day: sell everything armed; time-exit stale positions."""
    import pandas as pd
    from tools.ch3_shadow_hunter import last_price
    book = load_book()
    now = datetime.now(timezone.utc).isoformat()
    # session count for the backstop, from the live store's calendar
    df = pd.read_parquet(os.path.join(ROOT, "ch4_live_store.parquet"),
                         columns=["Date"])
    days = sorted(d.strftime("%Y-%m-%d") for d in
                  pd.to_datetime(df["Date"].unique()))
    ix = {d: i for i, d in enumerate(days)}
    today_i = len(days) - 1
    for sym in sorted(list(book["positions"].keys())):
        p = book["positions"][sym]
        try:
            px = last_price(sym)
        except Exception:
            continue
        if not px:
            continue
        gain = 100 * (px / p["entry_px"] - 1.0) * p["side"]
        if p["armed"] or gain >= ARM_PCT:
            _close(book, sym, p, px, "HARVEST", now)
        elif p["entry_date"] in ix and today_i - ix[p["entry_date"]] >= HOLD_SESSIONS:
            _close(book, sym, p, px, "TIME", now)
    save_book(book)
    print(f"[ch6 sweep] open {len(book['positions'])} "
          f"closed {len(book['closed'])} cash ${book['cash']:,.2f}")


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "poll").lower()
    {"sync": sync, "poll": poll, "sweep": sweep}[cmd]()
