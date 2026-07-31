"""
ch3_shadow_hunter.py — CH3 shadow brain: intraday finds, zero orders
====================================================================

ENGINE: ch3_spring_intraday_v1 (2026-07-31). SHADOW ONLY — this process
never places orders; it logs what it WOULD do and grades itself at the
close. The live CH3 channel remains halted.

THE HUNT (every 15 minutes during market hours):
  Bars      15-minute intraday bars, today plus the prior 10 sessions,
            per watchlist symbol (Alpaca IEX, read-only).
  Structure fast-rung leg walk on the 15-minute closes (reversal at
            4 x trailing-26-bar median move — one session's bars).
  FIND      the spring at day speed: the stock is down at least its
            own quick-yield requirement from the session structure's
            origin, the last hour has gone quiet versus the day
            (compression), and the fine leg flips up (ignition).
            Mirror for shorts.
  TARGET    the stock's own median quick-move remainder over the prior
            10 sessions (its demonstrated intraday yield), capped need:
            target must exceed the reversal bound (energy-positive).
  GRADE     at each later cycle and at the close: target touched =
            HIT; reversal bound breached or session end = MISS with
            the would-be cost.
  BOOK      theoretical $100,000: every find is a simulated fill at
            the find close, sized risk-parity (a stop-out costs 1% of
            equity; gross <= 100%), sold at target / stop / close —
            flat overnight always (quick cash, never a bag). Dollars
            are the record.

State: artifacts/vtvr_observer/ch3_shadow_log.json (grades included).
Usage:
  python tools/ch3_shadow_hunter.py cycle    # one hunt cycle (cron/loop)
  python tools/ch3_shadow_hunter.py close    # end-of-day grading
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_star_state_replication import COHORT_B  # noqa: E402

ENGINE = "ch3_spring_intraday_v1"
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "artifacts", "vtvr_observer", "ch3_shadow_log.json")
BARS_PER_SESSION = 26          # 15-min bars in 6.5h
W_BARS = 26                    # trailing window = one session
REV_MULT = 4
PRICE_FLOOR = 5.0
CASH0 = 100_000.0
RISK_PCT = 1.0                 # a stop-out costs 1% of equity
MAX_GROSS_PCT = 100.0


def watchlist():
    from tools.vtvr_structure_search import UNIVERSE as COHORT_A
    return sorted(set(list(COHORT_A) + list(COHORT_B)))


def fetch_15m(symbol, days=11):
    key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY", "")
    sec = (os.environ.get("APCA_API_SECRET_KEY")
           or os.environ.get("ALPACA_API_SECRET_KEY", ""))
    url = (f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?timeframe=15Min"
           f"&limit=1000&adjustment=split&feed=iex&sort=desc")
    req = urllib.request.Request(url, headers={
        "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": sec})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read())
    bars = list(reversed(data.get("bars") or []))
    ts = [b["t"] for b in bars]
    closes = np.array([float(b["c"]) for b in bars])
    return ts, closes


def leg_walk(closes, mult=REV_MULT, W_=W_BARS):
    n = len(closes)
    moves = np.abs(np.diff(closes))
    dirs = np.zeros(n, dtype=int)
    flips = np.zeros(n, dtype=int)
    origin = np.zeros(n)
    direction, ext_i, org = 0, 0, closes[0] if n else 0
    for t in range(1, n):
        w0 = max(0, t - W_)
        med = float(np.median(moves[w0:t])) if t > w0 else 0.0
        thresh = mult * max(med, 1e-9)
        if direction >= 0 and closes[t] > closes[ext_i]:
            ext_i = t
            direction = direction or 1
        elif direction <= 0 and closes[t] < closes[ext_i]:
            ext_i = t
            direction = direction or -1
        if direction == 1 and closes[ext_i] - closes[t] > thresh:
            org = closes[ext_i]
            direction, ext_i = -1, t
            flips[t] = -1
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            org = closes[ext_i]
            direction, ext_i = 1, t
            flips[t] = 1
        dirs[t] = direction
        origin[t] = org
    return dirs, flips, origin, moves


def quick_yield_record(closes, flips):
    """Per side: remainders of past intraday legs (confirmation to
    extreme), the stock's demonstrated quick-move yields."""
    rems = {1: [], -1: []}
    conf_px, conf_side = None, 0
    ext = closes[0] if len(closes) else 0
    for t in range(1, len(closes)):
        side = flips[t]
        if side != 0:
            if conf_px is not None and conf_side != 0:
                if conf_side == 1:
                    rems[1].append(max(100 * (ext / conf_px - 1.0), 0.0))
                else:
                    rems[-1].append(max(100 * (1.0 - ext / conf_px), 0.0))
            conf_px, conf_side = closes[t], side
            ext = closes[t]
        else:
            if conf_side == 1:
                ext = max(ext, closes[t])
            elif conf_side == -1:
                ext = min(ext, closes[t])
    return rems


def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            log = json.load(f)
    else:
        log = {"engine": ENGINE, "finds": [], "days": {}}
    log.setdefault("book", {"cash": CASH0, "start": CASH0})
    return log


def save_log(log):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=1)


def open_notional(log):
    return sum(f.get("notional", 0.0) for f in log["finds"]
               if f["status"] == "OPEN")


def size_find(book, held, bound_pct):
    """Risk-parity theoretical fill: losing the stop costs RISK_PCT of
    equity; gross capped at MAX_GROSS_PCT; never exceeds cash."""
    equity = book["cash"] + held
    notional = equity * RISK_PCT / max(bound_pct, 0.2)
    notional = min(notional, equity * MAX_GROSS_PCT / 100.0 - held,
                   book["cash"])
    return round(notional, 2) if notional > 0 else 0.0


def settle(book, f, status, now, ret_pct):
    """Simulated sell: return the notional plus its result to cash."""
    pnl = round(f.get("notional", 0.0) * ret_pct / 100.0, 2)
    book["cash"] = round(book["cash"] + f.get("notional", 0.0) + pnl, 2)
    f.update(status=status, resolved=now, ret_pct=round(ret_pct, 2),
             pnl=pnl)


def cycle():
    log = load_log()
    now = datetime.now(timezone.utc).isoformat()
    today = now[:10]
    live = {f["symbol"]: f for f in log["finds"]
            if f["date"] == today and f["status"] == "OPEN"}
    new_finds, graded = 0, 0
    for sym in watchlist():
        try:
            ts, closes = fetch_15m(sym)
        except Exception:
            continue
        if len(closes) < 3 * W_BARS or closes[-1] < PRICE_FLOOR:
            continue
        dirs, flips, origin, moves = leg_walk(closes)
        t = len(closes) - 1

        # grade any live find on this symbol (theoretical sell)
        f = live.get(sym)
        if f is not None:
            if f["side"] == 1 and closes[t] >= f["target_px"]:
                settle(log["book"], f, "HIT", now,
                       100 * (f["target_px"] / f["entry_px"] - 1))
                graded += 1
            elif f["side"] == -1 and closes[t] <= f["target_px"]:
                settle(log["book"], f, "HIT", now,
                       100 * (1 - f["target_px"] / f["entry_px"]))
                graded += 1
            else:
                adverse = 100 * (closes[t] / f["entry_px"] - 1) * f["side"]
                if adverse <= -f["bound_pct"]:
                    settle(log["book"], f, "MISS", now, adverse)
                    graded += 1
            continue

        # hunt: the intraday spring
        side = int(flips[t]) if flips[t] != 0 else 0
        if side == 0 or dirs[t] != side:
            continue
        org = origin[t]
        if org <= 0:
            continue
        rems = quick_yield_record(closes[:-W_BARS], flips[:-W_BARS])
        store = rems[side]
        if len(store) < 10:
            continue
        tgt_pct = float(np.median(np.array(store[-40:])))
        w0 = max(1, t - W_BARS)
        bound_pct = 100 * REV_MULT * float(np.median(moves[w0 - 1:t])) / closes[t]
        # energy present: the countertrend structure moved at least the
        # target's worth from its origin; spring loaded: last 4 bars
        # quieter than the session
        drawn = 100 * abs(1 - closes[t] / org)
        q_now = float(np.median(moves[max(1, t - 4) - 1:t]))
        q_ref = float(np.median(moves[w0 - 1:t]))
        if drawn < tgt_pct or not (q_now < q_ref) or tgt_pct < bound_pct:
            continue
        tgt_px = closes[t] * (1 + tgt_pct / 100) if side == 1 \
            else closes[t] * (1 - tgt_pct / 100)
        bnd = round(max(bound_pct, 0.2), 2)
        notional = size_find(log["book"], open_notional(log), bnd)
        log["book"]["cash"] = round(log["book"]["cash"] - notional, 2)
        log["finds"].append({
            "engine": ENGINE, "date": today, "found_at": now,
            "symbol": sym, "side": side, "entry_px": round(float(closes[t]), 4),
            "target_pct": round(tgt_pct, 2), "target_px": round(float(tgt_px), 4),
            "bound_pct": bnd, "notional": notional,
            "status": "OPEN"})
        new_finds += 1
    save_log(log)
    print(f"[shadow] {now} cycle: {new_finds} new finds, {graded} graded, "
          f"{sum(1 for f in log['finds'] if f['date'] == today)} today total, "
          f"cash=${log['book']['cash']:,.2f} held=${open_notional(log):,.2f}")


def close_day():
    log = load_log()
    now = datetime.now(timezone.utc).isoformat()
    today = now[:10]
    for sym in {f["symbol"] for f in log["finds"]
                if f["date"] == today and f["status"] == "OPEN"}:
        try:
            ts, closes = fetch_15m(sym, days=2)
        except Exception:
            continue
        px = float(closes[-1])
        for f in log["finds"]:
            if f["symbol"] == sym and f["date"] == today and f["status"] == "OPEN":
                ret = 100 * (px / f["entry_px"] - 1) * f["side"]
                settle(log["book"], f, "EOD", now, ret)
    # any find that could not be priced at the close still settles flat
    # at entry (the book never carries positions overnight)
    for f in log["finds"]:
        if f["status"] == "OPEN":
            settle(log["book"], f, "EOD", now, 0.0)
    day = [f for f in log["finds"] if f["date"] == today]
    hits = sum(1 for f in day if f["status"] == "HIT")
    done = [f for f in day if f["status"] in ("HIT", "MISS", "EOD")]
    rets = [f["ret_pct"] for f in done if "ret_pct" in f]
    log["days"][today] = {
        "finds": len(day), "hits": hits,
        "hit_rate_pct": round(100 * hits / len(done), 1) if done else None,
        "mean_ret_pct": round(float(np.mean(rets)), 2) if rets else None,
        "pnl_usd": round(sum(f.get("pnl", 0.0) for f in done), 2),
        "book_value": log["book"]["cash"]}
    save_log(log)
    print(f"[shadow] close {today}: {json.dumps(log['days'][today])}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cycle"
    if mode == "cycle":
        cycle()
    elif mode == "close":
        close_day()
