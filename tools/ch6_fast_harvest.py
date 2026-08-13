"""
ch6_fast_harvest.py — CH6: its own channel (2026-08-06, separated 2026-08-11)
==================================================================

ENGINE VERSION: ch6_fast_harvest_v1. Hypothesis (Joe's): the fade
front-loads — harvest any short past +5% the same day instead of
holding 5 sessions.

Rules (constants declared 2026-08-06 before first trade):
  START    clean book, NO inherited positions (Joe: "I don't want to
           cheat") — it trades nothing dated before START_DATE.
  ENTRIES  ITS OWN SCAN. CH6 runs the same event rule CH3 runs, against
           the same store, into its own $100k book. It does not read,
           mirror or adopt CH3's positions. Two independent records of
           the same entries, differing only in the exit.
  HARVEST  at the end-of-day sweep, ANY position standing at +5% or
           better is sold. Nothing that is up 5% is carried overnight.
  BACKSTOP anything not harvested exits after HOLD_SESSIONS (5) at the
           day's mark, same as CH3's time exit.
  No loss-stop. One variable only: the harvest rule.

CORRECTED 2026-08-11 (Joe): "the only difference from CH3 is it sells off
any stock that is 5% or better before the end of a trading day." The
build had two rules he never asked for on top of that one — a position
was ARMED once it touched +5% and then sold intraday if it slipped a
point off its peak, and once armed it was swept at the close whatever it
was worth. Both sold positions BELOW 5%, which is the opposite of the
stated rule and made CH6 a second variable against CH3 rather than one.
Arming, peak tracking and the give-back sale are gone.

CH3 house rules carry over: shorts only, one position per symbol,
whole shares, $2k stakes as adopted, borrow costs NOT modeled (stated
on the page), and the freeze discipline — these constants are FROZEN
until 20 CH6 positions have closed; no retuning on the way.
Known divergence, declared: CH6's sweep/backstop exits price at the
19:55 UTC mark (5-min feed), not the official close CH3 settles on.

Usage:
  python tools/ch6_fast_harvest.py hunt     # its own entry scan
  python tools/ch6_fast_harvest.py poll     # 5-min check: arm/harvest
  python tools/ch6_fast_harvest.py sweep    # end-of-day: sell >=+5%, time exits
Loop: tools/ch6_loop.sh (poll every 5 min in market hours; sweep 19:55 UTC).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ENGINE = "ch6_fast_harvest_v2"   # v2: own entry scan, not CH3 adoption
EVENT_GAIN = 8.0       # same event as CH3
VOL_MULT = 3.0
PRICE_FLOOR = 5.0
SLICE_USD = 2000.0
MAX_NEW_PER_DAY = 10
START_DATE = "2026-08-07"      # no positions born before this — no cheating
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK_PATH = os.path.join(ROOT, "artifacts", "vtvr_observer", "ch6_book.json")
CASH0 = 100_000.0
HARVEST_PCT = 5.0      # a winner is armed at or above this gain
GIVEBACK_PP = 1.0      # points off its peak that harvests an armed winner
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
    """REMOVED 2026-08-11. CH6 does not adopt CH3's positions.

    Joe: "CH6 is its own channel." It finds its own entries in hunt().
    Kept only so an old runner calling `sync` fails loudly instead of
    silently doing nothing.
    """
    raise SystemExit(
        "ch6 sync is removed — CH6 runs its own entry scan (use: hunt)"
    )


def hunt(dry: bool = False):
    """CH6's OWN entry pass. It does not read CH3's book.

    Joe, 2026-08-11: "CH6 should be separate." It was built as a mirror
    that adopted CH3's positions, which made it a dependent of CH3's book
    rather than a channel — if CH3's book was empty, CH6 was empty, and
    the two could never be compared as independent records.

    This runs the SAME event rule CH3 runs, against the same store, into
    CH6's own $100k book: a close-of-day gain of +8% or more, volume at
    three times the trailing twenty-day average, a close of $5 or better,
    and the herd NOT backing the spike. Same $2,000 slices, same limit of
    ten new per day, same whole-share arithmetic.

    The one and only difference from CH3 lives in sweep(): anything at
    +5% or better is sold before the day ends.
    """
    import numpy as np
    import pandas as pd

    book = load_book()
    now = datetime.now(timezone.utc).isoformat()
    df = pd.read_parquet(os.path.join(ROOT, "ch4_live_store.parquet"),
                         columns=["Date", "Symbol", "Close", "Volume"])
    days = sorted(df["Date"].unique())
    latest = days[-1]
    latest_s = pd.Timestamp(latest).strftime("%Y-%m-%d")
    # 2026-08-13 plumbing repair (same blindness CH3 had): the roster
    # store misses the small/young names where qualifying spikes mostly
    # live — 75% of the decade's tradeable supply. The whole-market tail
    # (tools/ch3_supply_tail.py, refreshed nightly by the same runner)
    # is added to the SCAN only; every CH6 rule — entries, 5% harvest,
    # sweep, slices, caps — is unchanged. Names the roster still
    # refreshes stay roster-only (single source per name, no seams).
    tail_path = os.path.join(ROOT, "ch3_supply_tail.parquet")
    if os.path.exists(tail_path):
        tail = pd.read_parquet(tail_path)
        tail["Date"] = pd.to_datetime(tail["Date"])
        refreshed = set(df[df["Date"] == latest]["Symbol"])
        tail = tail[~tail["Symbol"].isin(refreshed)
                    & (tail["Date"] <= latest)]
        df = pd.concat([df[df["Symbol"].isin(refreshed)], tail],
                       ignore_index=True)
    if latest_s < START_DATE:
        print(f"[ch6 hunt] latest close {latest_s} precedes CH6's start "
              f"{START_DATE} — nothing to do")
        return
    if book.get("last_hunted") == latest_s:
        print(f"[ch6 hunt] {latest_s} already processed — no double entry")
        return

    # TIME BACKSTOP, SETTLED EXACTLY AS CH3 SETTLES IT (parity fix
    # 2026-08-11): a never-harvested position exits at its 5th session's
    # CLOSE, from the store, the moment that close exists — the same
    # instant and same price CH3's own settle uses. This used to live in
    # the 19:55 sweep, where the store's newest bar is still yesterday's,
    # so the backstop fired one session late at a delayed intraday mark —
    # a second hidden variable in what must be a one-variable experiment.
    px_latest = dict(df[df["Date"] == latest][["Symbol", "Close"]].values)
    day_ix = {d: i for i, d in enumerate(
        pd.Timestamp(x).strftime("%Y-%m-%d") for x in days)}
    for sym in sorted(list(book["positions"].keys())):
        pos = book["positions"][sym]
        ei = day_ix.get(pos.get("entry_date"))
        px = px_latest.get(sym)
        if ei is None or px is None:
            continue
        if (len(days) - 1) - ei >= HOLD_SESSIONS:
            _close(book, sym, pos, float(px), "TIME",
                   datetime.now(timezone.utc).isoformat())

    herd = pd.read_parquet(os.path.join(
        ROOT, "artifacts", "ch4_uf", "herd_state_live.parquet"))
    hday = int(pd.Timestamp(latest).strftime("%Y%m%d"))
    gband = {sym: int(g) for sym, d, g in zip(
        herd["sym"], herd["date"].astype(int), herd["gband"]) if int(d) == hday}

    # RACE GUARD. The price store and the herd export are both written by
    # the nightly pass, and this scan runs every five minutes. Landing in
    # the gap — new bar present, herd state not yet written — would leave
    # every spike unfiltered and open up to ten positions CH3 correctly
    # refuses, making CH6 differ from CH3 by far more than the exit. With
    # no herd reading for the day there is no scan: it waits and retries
    # on the next cycle, and does NOT stamp the day as processed.
    if not gband:
        print(f"[ch6 hunt] {latest_s}: herd state not published yet — "
              f"waiting rather than trading an unfiltered field")
        return

    sub = df[df["Date"].isin(days[-25:])]
    events = []
    for sym, srows in sub.groupby("Symbol"):
        srows = srows.sort_values("Date")
        c = srows["Close"].to_numpy()
        v = srows["Volume"].to_numpy()
        if len(c) < 21 or srows["Date"].iloc[-1] != latest:
            continue
        if c[-1] < PRICE_FLOOR or c[-2] <= 0:
            continue
        gain = 100 * (c[-1] / c[-2] - 1)
        vavg = float(np.mean(v[-21:-1]))
        if gain >= EVENT_GAIN and vavg > 0 and v[-1] >= VOL_MULT * vavg:
            g = gband.get(sym)
            if g is not None and g >= 1:
                continue
            events.append({"symbol": sym, "gain": round(gain, 1),
                           "close": float(c[-1]),
                           "dollar_vol": float(v[-1] * c[-1])})
    events.sort(key=lambda e: -e["dollar_vol"])

    opened = 0
    for e in events:
        if opened >= MAX_NEW_PER_DAY:
            break
        if e["symbol"] in book["positions"] or book["cash"] < SLICE_USD:
            continue
        shares = int(SLICE_USD // e["close"])
        if shares < 1:
            continue
        notional = round(shares * round(e["close"], 4), 2)
        if dry:
            print(f"  WOULD SHORT {shares} {e['symbol']} @ {e['close']} "
                  f"(+{e['gain']}% day)")
            opened += 1
            continue
        book["cash"] = round(book["cash"] - notional, 2)
        book["positions"][e["symbol"]] = {
            "engine": ENGINE, "entry_date": latest_s, "opened_at": now,
            "side": -1, "entry_px": round(e["close"], 4), "shares": shares,
            "notional": notional,
            "armed": False, "peak_gain_pct": 0.0}
        opened += 1
        print(f"  SHORT {shares} {e['symbol']} @ {e['close']} (+{e['gain']}% day)")
    if not dry:
        book["last_hunted"] = latest_s
        save_book(book)
    print(f"[ch6 hunt] {latest_s}: {len(events)} qualifying spikes, "
          f"{opened} opened, open {len(book['positions'])}, "
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
    """Intraday: arm winners at +5%, trail their peak, never round-trip one.

    Joe's intent, stated 2026-08-11: "give stock room to go as high as they
    can and not lose say a 30% win." So a position that reaches +5% is
    ARMED — from that point its best level is tracked, and it is sold the
    moment it gives back GIVEBACK_PP points from that peak. A 30% run gets
    harvested near 30, not watched back down to 6. Anything still armed at
    the end-of-day sweep sells there. Below +5% nothing is touched.
    GIVEBACK_PP = 1.0 is the constant declared when this book opened
    (2026-08-06); marks are the ~15-min-delayed feed, checked every 5 min.
    """
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
        if not p.get("armed") and gain >= HARVEST_PCT:
            p["armed"] = True
            print(f"  ARMED {sym} at {gain:+.2f}% — trailing its peak now")
        if p.get("armed") and p["peak_gain_pct"] - gain > GIVEBACK_PP:
            _close(book, sym, p, px, "HARVEST", now)
    save_book(book)
    armed = sum(1 for q in book["positions"].values() if q.get("armed"))
    print(f"[ch6 poll] open {len(book['positions'])} "
          f"armed {armed} cash ${book['cash']:,.2f}")


def sweep():
    """End of day: sell anything at +5% or better; time-exit the rest."""
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
        # Day's end (Joe, 2026-08-11): sell ONLY what STANDS at +5% or
        # better right now. Not "sell at any cost" — a position at +4.5%
        # or -1.5% is left completely alone here, even one that was armed
        # earlier today. Its armed flag and peak survive to the next
        # session, so the trail keeps protecting it; otherwise only the
        # other declared exits (intraday give-back, 5-session backstop)
        # can touch it.
        if gain >= HARVEST_PCT:
            _close(book, sym, p, px, "HARVEST", now)
        # TIME backstop moved to hunt() 2026-08-11: it settles at the 5th
        # session close from the store, exactly where CH3's settle lands.
    save_book(book)
    print(f"[ch6 sweep] open {len(book['positions'])} "
          f"closed {len(book['closed'])} cash ${book['cash']:,.2f}")


if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "poll").lower()
    {"hunt": hunt, "poll": poll, "sweep": sweep, "sync": sync}[cmd]()
