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

ENGINE = "ch3_mover_grab_v1"
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


# --- real-life awareness: the day's actual energy ---------------------
# ch3_mover_grab_v1 (2026-08-04). The quick-grabber goes WHERE THE
# ENERGY ALREADY IS: the day's real movers on real volume, right now —
# not a fixed watchlist, not a predicted spring. Selection is by
# REALIZED energy (an observable), entry is continuation while the move
# still presses, risk is a hard bracket, always flat by the close.
MIN_PX = 3.0
MIN_CHG = 7.0          # day move %, both sides
MAX_CHG = 100.0
MIN_DOLLAR_VOL = 25e6  # real participation, not a ghost print
PRESS_PCT = 2.0        # within 2% of the day extreme = still pressing
STOP_PCT = 1.5
TARGET_PCT = 3.0       # 2:1 bracket
MAX_OPEN = 5
SLICE_MAX_PCT = 20.0


def _mkey():
    return (os.environ.get("MASSIVE_API_KEY")
            or os.environ.get("POLYGON_API_KEY", ""))


def movers():
    """Top gainers/losers snapshots — the day's realized energy."""
    out = []
    for kind, side in (("gainers", 1), ("losers", -1)):
        url = (f"https://api.polygon.io/v2/snapshot/locale/us/markets/"
               f"stocks/{kind}?apiKey={_mkey()}")
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.loads(r.read())
        except Exception:
            continue
        for t in d.get("tickers") or []:
            day = t.get("day") or {}
            mn = t.get("min") or {}
            px = float(mn.get("c") or day.get("c") or 0)
            chg = float(t.get("todaysChangePerc") or 0)
            dv = float(day.get("v") or 0) * float(day.get("vw") or 0)
            sym = t.get("ticker", "")
            if (px < MIN_PX or "." in sym or abs(chg) < MIN_CHG
                    or abs(chg) > MAX_CHG or dv < MIN_DOLLAR_VOL):
                continue
            out.append({"symbol": sym, "side": side, "px": px, "chg": chg,
                        "hi": float(day.get("h") or px),
                        "lo": float(day.get("l") or px),
                        "dollar_vol": dv})
    return out


NEG_NEWS = ("offering", "dilution", "registered direct", "reverse split",
            "going concern", "delisting", "warrant", "at-the-market",
            "shelf", "convertible")
POS_NEWS = ("earnings", "beats", "beat", "raises", "guidance", "fda",
            "approval", "clearance", "contract", "acquisition", "merger",
            "partnership", "buyback", "award")


def ticker_type(log, sym):
    """CS = common stock. Cached; anything else (leveraged ETPs, funds,
    warrants) is not a company and gets skipped."""
    cache = log.setdefault("tick_types", {})
    if sym in cache:
        return cache[sym]
    try:
        url = f"https://api.polygon.io/v3/reference/tickers/{sym}?apiKey={_mkey()}"
        with urllib.request.urlopen(url, timeout=20) as r:
            t = (json.loads(r.read()).get("results") or {}).get("type", "?")
    except Exception:
        t = "?"
    cache[sym] = t
    return t


def catalyst(sym):
    """Read the candidate's actual headlines. Returns 'NEG', 'POS',
    'NONE', or 'OTHER'."""
    try:
        url = (f"https://api.polygon.io/v2/reference/news?ticker={sym}"
               f"&limit=6&apiKey={_mkey()}")
        with urllib.request.urlopen(url, timeout=20) as r:
            arts = json.loads(r.read()).get("results") or []
    except Exception:
        return "OTHER"
    if not arts:
        return "NONE"
    text = " ".join((a.get("title") or "").lower() for a in arts[:6])
    if any(k in text for k in NEG_NEWS):
        return "NEG"
    if any(k in text for k in POS_NEWS):
        return "POS"
    return "OTHER"


def last_price(sym):
    url = (f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/"
           f"tickers/{sym}?apiKey={_mkey()}")
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read())
    t = d.get("ticker") or {}
    mn = t.get("min") or {}
    day = t.get("day") or {}
    return float(mn.get("c") or day.get("c") or 0)


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
    """Besides direction/flip/origin, expose at each flip bar the leg
    that just ENDED: its origin price (prev_org) and its extreme
    (ext_px). For an up-flip that is the finished decline: peak ->
    trough — the energy the spring actually stored."""
    n = len(closes)
    moves = np.abs(np.diff(closes))
    dirs = np.zeros(n, dtype=int)
    flips = np.zeros(n, dtype=int)
    origin = np.zeros(n)
    prev_org = np.zeros(n)
    ext_px = np.zeros(n)
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
            prev_org[t] = org
            ext_px[t] = closes[ext_i]
            org = closes[ext_i]
            direction, ext_i = -1, t
            flips[t] = -1
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            prev_org[t] = org
            ext_px[t] = closes[ext_i]
            org = closes[ext_i]
            direction, ext_i = 1, t
            flips[t] = 1
        dirs[t] = direction
        origin[t] = org
    return dirs, flips, origin, moves, prev_org, ext_px


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
    traded_today = {f["symbol"] for f in log["finds"] if f["date"] == today}
    new_finds, graded = 0, 0

    # 1) grade open grabs at current prices (theoretical sells)
    for sym, f in list(live.items()):
        try:
            px = last_price(sym)
        except Exception:
            continue
        if px <= 0:
            continue
        if f["side"] == 1 and px >= f["target_px"]:
            settle(log["book"], f, "HIT", now,
                   100 * (f["target_px"] / f["entry_px"] - 1))
            graded += 1
        elif f["side"] == -1 and px <= f["target_px"]:
            settle(log["book"], f, "HIT", now,
                   100 * (1 - f["target_px"] / f["entry_px"]))
            graded += 1
        else:
            adverse = 100 * (px / f["entry_px"] - 1) * f["side"]
            if adverse <= -f["bound_pct"]:
                settle(log["book"], f, "MISS", now, adverse)
                graded += 1

    # 2) hunt where the energy already is: today's real movers
    open_now = sum(1 for f in log["finds"] if f["status"] == "OPEN")
    for m in sorted(movers(), key=lambda x: -x["dollar_vol"]):
        if open_now >= MAX_OPEN:
            break
        sym, side, px = m["symbol"], m["side"], m["px"]
        if sym in traded_today or px <= 0:
            continue
        # still pressing: within PRESS_PCT of the day extreme in the
        # move's direction (energy not yet faded)
        if side == 1 and 100 * (m["hi"] - px) / m["hi"] > PRESS_PCT:
            continue
        if side == -1 and 100 * (px - m["lo"]) / max(m["lo"], 1e-9) > PRESS_PCT:
            continue
        # a real company, not a leveraged/inverse product or fund
        if ticker_type(log, sym) != "CS":
            continue
        # read the actual news before touching it
        cat = catalyst(sym)
        if side == 1 and cat == "NEG":
            continue                 # up big while announcing dilution: fade, not ride
        if side == -1 and cat == "POS":
            continue                 # down big against good news: fighting a recovery
        size_frac = 1.0 if cat in ("POS", "NEG") else 0.5
        # no news on a violent move = pump risk: half size
        tgt_px = px * (1 + TARGET_PCT / 100) if side == 1 \
            else px * (1 - TARGET_PCT / 100)
        notional = size_find(log["book"], open_notional(log), STOP_PCT)
        notional = min(notional,
                       round((log["book"]["cash"] + open_notional(log))
                             * SLICE_MAX_PCT / 100 * size_frac, 2))
        if notional <= 0:
            continue
        log["book"]["cash"] = round(log["book"]["cash"] - notional, 2)
        log["finds"].append({
            "engine": ENGINE, "date": today, "found_at": now,
            "symbol": sym, "side": side, "entry_px": round(px, 4),
            "target_pct": TARGET_PCT, "target_px": round(tgt_px, 4),
            "bound_pct": STOP_PCT, "notional": notional,
            "day_chg_pct": round(m["chg"], 1), "catalyst": cat,
            "status": "OPEN"})
        traded_today.add(sym)
        open_now += 1
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
            px = float(last_price(sym))
        except Exception:
            continue
        if px <= 0:
            continue
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
