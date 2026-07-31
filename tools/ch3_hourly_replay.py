"""
ch3_hourly_replay.py — the CH3 intraday spring replayed over a decade
=====================================================================

PURPOSE: the re-arm evidence for the live CH3 channel. The shadow
hunter's exact find logic (post energy-fix 8cefa573), ported to hourly
bars 2016-2026 from the full-depth store, session-aware, run through a
theoretical book — per-year dollars on a fresh $100,000 each year.

FAITHFUL PORT of tools/ch3_shadow_hunter.py, scaled one rung up:
  bars      hourly, regular session only (New York 9:00-15:00 bar
            starts = 7 bars/session; the 15:00 bar closes at 16:00)
  W         7 bars = one session (the hunter uses 26 fifteen-minute
            bars = one session)
  walk      identical leg walk, REV_MULT=4, ended-leg origin/extreme
  find      flip bar + ended leg spanned >= target + last-4-bars quiet
            vs session + target >= bound + >=10 prior remainders
  target    median of the stock's last 40 same-side leg remainders,
            legs completed on PRIOR days only (no same-session echo)
  exits     close-based: target crossed = HIT, adverse close beyond
            bound = MISS, else session's last bar = EOD. Never held
            overnight.
  book      chronological across ALL symbols: risk-parity (stop-out
            costs 1% of equity), gross <= 100%, cash-limited, one open
            position per symbol. Fresh $100,000 each calendar year.

CAVEAT (stated, not hidden): fills are at hourly closes; the live
shadow grades at 15-minute closes. Hourly grading is coarser in both
directions (later stop recognition, later target recognition).

Usage: python tools/ch3_hourly_replay.py [max_symbols]
Output: artifacts/ch4_uf/ch3_hourly_replay.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.environ.get("CH3_STORE") or os.path.join(
    ROOT, "ch4_hourly_universe_full.parquet")
OUT = os.environ.get("CH3_OUT") or os.path.join(
    ROOT, "artifacts", "ch4_uf", "ch3_hourly_replay.json")

# rung: "hour" (7 bars/session) or "m15" (26 bars/session, the live rung)
RUNG = os.environ.get("CH3_RUNG", "hour")
W_BARS = 26 if RUNG == "m15" else 7        # one session, either rung
REV_MULT = 4
PRICE_FLOOR = 5.0
CASH0 = 100_000.0
RISK_PCT = 1.0
MAX_GROSS_PCT = 100.0
MIN_REMS = 10


def replay_symbol(day_ids, closes):
    """One pass over a symbol's session-hour closes. Returns finds with
    their (book-independent) resolutions. Identical physics to the
    hunter's leg_walk + quick_yield_record + find condition."""
    n = len(closes)
    moves = np.abs(np.diff(closes))
    finds = []
    rems = {1: [], -1: []}          # (available_from_day, remainder_pct)
    conf_px, conf_side, rext = None, 0, closes[0]
    conf_t, rext_t = 0, 0
    direction, ext_i, org, p_org, p_ext = 0, 0, closes[0], 0.0, 0.0
    open_f = None
    for t in range(1, n):
        new_day = day_ids[t] != day_ids[t - 1]
        # session close settlement for the open find
        if open_f is not None and new_day:
            px = closes[t - 1]
            r = 100 * (px / open_f["entry_px"] - 1) * open_f["side"]
            open_f.update(status="EOD", ret_pct=round(r, 3),
                          res_t=t - 1)
            finds.append(open_f)
            open_f = None
        w0 = max(0, t - W_BARS)
        med = float(np.median(moves[w0:t])) if t > w0 else 0.0
        thresh = REV_MULT * max(med, 1e-9)
        if direction >= 0 and closes[t] > closes[ext_i]:
            ext_i = t
            direction = direction or 1
        elif direction <= 0 and closes[t] < closes[ext_i]:
            ext_i = t
            direction = direction or -1
        flip = 0
        if direction == 1 and closes[ext_i] - closes[t] > thresh:
            p_org, p_ext = org, closes[ext_i]
            org = closes[ext_i]
            direction, ext_i, flip = -1, t, -1
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            p_org, p_ext = org, closes[ext_i]
            org = closes[ext_i]
            direction, ext_i, flip = 1, t, 1
        # remainder bookkeeping (quick_yield_record, incremental):
        # a flip closes the previously CONFIRMED leg; its remainder is
        # a QUICK yield only if confirmation and extreme fell in the
        # SAME session (CH3's species is the intraday flare); usable
        # from the next day
        if flip != 0:
            if conf_px is not None and conf_side != 0 \
                    and day_ids[conf_t] == day_ids[rext_t]:
                if conf_side == 1:
                    val = max(100 * (rext / conf_px - 1.0), 0.0)
                else:
                    val = max(100 * (1.0 - rext / conf_px), 0.0)
                rems[conf_side].append((day_ids[t] + 1, val))
            conf_px, conf_side, rext = closes[t], flip, closes[t]
            conf_t, rext_t = t, t
        else:
            if conf_side == 1 and closes[t] > rext:
                rext, rext_t = closes[t], t
            elif conf_side == -1 and closes[t] < rext:
                rext, rext_t = closes[t], t
        # grade the open find at this close
        if open_f is not None:
            side = open_f["side"]
            if side == 1 and closes[t] >= open_f["target_px"]:
                open_f.update(status="HIT", res_t=t,
                              ret_pct=round(open_f["target_pct"], 3))
                finds.append(open_f)
                open_f = None
            elif side == -1 and closes[t] <= open_f["target_px"]:
                open_f.update(status="HIT", res_t=t,
                              ret_pct=round(open_f["target_pct"], 3))
                finds.append(open_f)
                open_f = None
            else:
                adverse = 100 * (closes[t] / open_f["entry_px"] - 1) * side
                if adverse <= -open_f["bound_pct"]:
                    open_f.update(status="MISS", res_t=t,
                                  ret_pct=round(adverse, 3))
                    finds.append(open_f)
                    open_f = None
            continue                       # holding: no re-entry this bar
        # the find condition (post energy-fix)
        if flip == 0 or closes[t] < PRICE_FLOOR or p_org <= 0 or p_ext <= 0:
            continue
        side = flip
        usable = [v for d, v in rems[side] if d <= day_ids[t]][-40:]
        if len(usable) < MIN_REMS:
            continue
        tgt_pct = float(np.median(np.array(usable)))
        w1 = max(1, t - W_BARS)
        bound_pct = 100 * REV_MULT * float(np.median(moves[w1 - 1:t])) / closes[t]
        drawn = 100 * (1 - p_ext / p_org) if side == 1 \
            else 100 * (p_ext / p_org - 1)
        q_now = float(np.median(moves[max(1, t - 4) - 1:t]))
        q_ref = float(np.median(moves[w1 - 1:t]))
        if drawn < tgt_pct or not (q_now < q_ref) or tgt_pct < bound_pct:
            continue
        tgt_px = closes[t] * (1 + tgt_pct / 100) if side == 1 \
            else closes[t] * (1 - tgt_pct / 100)
        open_f = {"t": t, "day": int(day_ids[t]), "side": side,
                  "entry_px": float(closes[t]),
                  "target_pct": round(tgt_pct, 3),
                  "target_px": float(tgt_px),
                  "bound_pct": round(max(bound_pct, 0.2), 3),
                  "drawn_pct": round(drawn, 2)}
    if open_f is not None:                 # settle a dangling last find
        r = 100 * (closes[-1] / open_f["entry_px"] - 1) * open_f["side"]
        open_f.update(status="EOD", ret_pct=round(r, 3), res_t=n - 1)
        finds.append(open_f)
    return finds


def run_book(events):
    """Chronological theoretical book, fresh $100k per calendar year.
    events: list of (open_key, close_key, year, sym, find)."""
    years = defaultdict(list)
    for ev in events:
        years[ev[2]].append(ev)
    out = {}
    for year in sorted(years):
        evs = sorted(years[year], key=lambda e: (e[0], e[3]))
        cash, held = CASH0, {}
        settled = []
        # process opens in time order; settle anything due first
        import heapq
        heap = []
        n_skip = 0
        for open_key, close_key, _y, sym, f in evs:
            while heap and heap[0][0] <= open_key:
                _ck, hsym, hf = heapq.heappop(heap)
                cash += hf["notional"] * (1 + hf["ret_pct"] / 100.0)
                settled.append(hf)
                held.pop(hsym, None)
            if sym in held:
                n_skip += 1
                continue
            gross = sum(x["notional"] for x in held.values())
            equity = cash + gross
            notional = equity * RISK_PCT / max(f["bound_pct"], 0.2)
            notional = min(notional, equity * MAX_GROSS_PCT / 100 - gross, cash)
            if notional <= 0:
                n_skip += 1
                continue
            f = dict(f, notional=round(notional, 2))
            cash -= f["notional"]
            held[sym] = f
            heapq.heappush(heap, (close_key, sym, f))
        while heap:
            _ck, hsym, hf = heapq.heappop(heap)
            cash += hf["notional"] * (1 + hf["ret_pct"] / 100.0)
            settled.append(hf)
        wins = sum(1 for f in settled if f["ret_pct"] > 0)
        hits = sum(1 for f in settled if f["status"] == "HIT")
        out[str(year)] = {
            "trades": len(settled), "skipped_no_capital": n_skip,
            "hits": hits,
            "hit_rate_pct": round(100 * hits / len(settled), 1) if settled else None,
            "win_rate_pct": round(100 * wins / len(settled), 1) if settled else None,
            "made_usd": round(cash - CASH0, 2),
            "end_value": round(cash, 2),
            "ret_pct": round(100 * (cash / CASH0 - 1), 2)}
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    t0 = time.time()
    df = pd.read_parquet(STORE, columns=["Date", "Symbol", "Close"])
    ts = pd.to_datetime(df["Date"]).dt.tz_localize("UTC") \
        .dt.tz_convert("America/New_York")
    mod = ts.dt.hour * 60 + ts.dt.minute
    if RUNG == "m15":
        # bar starts 9:30 .. 15:45 New York = the 26 session bars
        rth = (mod >= 570) & (mod <= 945) & (ts.dt.weekday <= 4)
    else:
        rth = (ts.dt.hour >= 9) & (ts.dt.hour <= 15) & (ts.dt.weekday <= 4)
    df = df[rth].copy()
    ts = ts[rth]
    df["day"] = (ts.dt.year * 10000 + ts.dt.month * 100 + ts.dt.day).to_numpy()
    df["yr"] = ts.dt.year.to_numpy()
    df["hkey"] = ts.dt.strftime("%Y%m%d%H%M").to_numpy()
    print(f"session-hour rows: {len(df)} ({time.time()-t0:.0f}s)", flush=True)

    med = df.groupby("Symbol")["Close"].median()
    uni = sorted(med[med >= PRICE_FLOOR].index.tolist())[:limit]
    print(f"universe: {len(uni)} symbols", flush=True)

    events = []
    per_sym_counts = 0
    uni_set = set(uni)
    for i, (sym, sub) in enumerate(df.groupby("Symbol", sort=True)):
        if sym not in uni_set:
            continue
        sub = sub.sort_values("hkey")
        closes = sub["Close"].to_numpy(dtype=float)
        if len(closes) < 3 * W_BARS:
            continue
        # dense day ids
        days_raw = sub["day"].to_numpy()
        uniq, day_ids = np.unique(days_raw, return_inverse=True)
        hkeys = sub["hkey"].to_numpy()
        yrs = sub["yr"].to_numpy()
        try:
            fs = replay_symbol(day_ids, closes)
        except Exception:
            continue
        for f in fs:
            f["sym"] = sym
            events.append((hkeys[f["t"]], hkeys[f["res_t"]],
                           int(yrs[f["t"]]), sym, f))
        per_sym_counts += len(fs)
        if (i + 1) % 250 == 0:
            print(f"  [{i+1}] finds={per_sym_counts} "
                  f"{time.time()-t0:.0f}s", flush=True)

    print(f"total raw finds: {len(events)} ({time.time()-t0:.0f}s)", flush=True)
    book = run_book(events)

    # ungoverned per-find stats (book-independent)
    allf = [e[4] for e in events]
    byy = defaultdict(list)
    for e in events:
        byy[e[2]].append(e[4])
    raw = {str(y): {
        "finds": len(v),
        "hit_rate_pct": round(100 * sum(1 for f in v if f["status"] == "HIT")
                              / len(v), 1),
        "mean_ret_pct": round(float(np.mean([f["ret_pct"] for f in v])), 3)}
        for y, v in sorted(byy.items())}

    result = {"frame": f"CH3 intraday spring, rung={RUNG} "
                       f"(W={W_BARS} bars/session), decade replay "
                       "(post energy-fix, same-session yield record); "
                       "fresh $100k per year",
              "caveat": "close-based fills at the store's own rung",
              "store": os.path.basename(STORE), "rung": RUNG,
              "book_by_year": book, "raw_by_year": raw,
              "universe": len(uni), "total_finds": len(allf)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps({"book_by_year": book}, indent=1))
    print("filed:", OUT)


if __name__ == "__main__":
    main()
