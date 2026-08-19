"""
ch_entry_reading.py — the Rules, run inside the engines at entry time
=====================================================================

Joseph's order 2026-08-18: apply the Rules to entries. For every
candidate the engines want to short, this module runs the full-life
kernel reading at fine resolution (45-minute bars, the stock's whole
existence) and issues the verdict BEFORE any position opens. Every
verdict is filed with its complete reading in docs/readings/ so any
misfire is auditable the next morning.

This is the executable projection of the filed Rules
(docs/TFE_KERNEL_STOCK_RULES_20260818.md). The criteria below are
declared translations of the week's proven readings — UGI/HAE/FLXS
(sound), CNSP/WETO/IPST (charging vehicles), HTHT/HTFL (the cut
mistakes) — and every constant is stated here, versioned v1, never
silently changed:

REFUSE — SOUND STRUCTURE (Rule 3: never short a sound company):
  life >= 2 years AND price >= half its lifetime peak AND lifetime
  peak/price < 4.
REFUSE — CHARGING VEHICLE (Rules 4+5: the killer launch shape):
  lifetime peak/price >= 4 (a drained vehicle) AND the rehearsal
  floor is clean right now (channel deaths in the last 2 weeks <= 2
  while its lifetime rate is >= 30/yr) AND the week is loading
  (majority of pushes up OR at least 3 of the last 5 sessions
  closing higher).
ALLOW — everything else: the exhausted-phase supply the fade exists
  to harvest, still under every cap, cut line, and clock.
FAIL CLOSED: no data, short life (< ~6 months of readings), or any
error refuses the candidate.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402

READINGS_DIR = ROOT / "docs" / "readings"
CACHE_DIR = ROOT / "artifacts" / "ch4_uf" / "entry_reading_cache"
MIN_READINGS = 320          # ~6 weeks of 9/day plus warmup — else fail closed


def _key() -> str:
    for ln in open(ROOT / ".env"):
        if ln.startswith("MASSIVE_API_KEY"):
            return ln.split("=", 1)[1].strip().strip('"')
    raise RuntimeError("MASSIVE_API_KEY missing")


def _bars(symbol: str) -> list:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache = CACHE_DIR / f"{symbol}_{today}.json"
    if cache.exists():
        return json.load(open(cache))
    key = _key()
    url = (f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/45/minute/"
           f"2021-01-01/{today}?adjusted=true&sort=asc&limit=50000&apiKey={key}")
    bars = []
    while url:
        d = json.load(urllib.request.urlopen(url, timeout=60))
        bars.extend(d.get("results", []))
        nxt = d.get("next_url")
        url = f"{nxt}&apiKey={key}" if nxt else None
        time.sleep(0.2)
    json.dump(bars, open(cache, "w"))
    return bars


def read_symbol(symbol: str) -> dict:
    """Full-life reading + verdict. Fail closed on anything."""
    try:
        bars = _bars(symbol)
        rows = []
        for b in bars:
            dt = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc)
            off = 4 if 3 < dt.month < 11 else 5
            et = dt - timedelta(hours=off)
            hm = et.hour * 60 + et.minute
            if 9 * 60 + 30 <= hm < 16 * 60 and et.weekday() < 5:
                rows.append((dt, float(b["c"]), float(b["v"]),
                             et.strftime("%Y-%m-%d")))
        if len(rows) < MIN_READINGS:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "fail-closed: insufficient life "
                            f"({len(rows)} readings)"}
        states = replay_symbol_v2(
            np.array([r[0] for r in rows]),
            np.array([r[1] for r in rows]),
            np.array([r[2] for r in rows]), warmup=60)
        c = np.array([r[1] for r in rows])
        R = np.array([s.URF if s is not None else np.nan for s in states])
        D = np.array([s.D_k if s is not None else 0 for s in states])
        ext = np.array([1 if (s is not None and s.extinction) else 0
                        for s in states])
        T = len(rows) - 1
        yrs = T / 2260
        peak = float(c[:T].max())
        crush = peak / c[T] if c[T] > 0 else 999.0
        deaths_yr = float(ext.sum()) / max(0.1, yrs)
        deaths_2wk = int(ext[T - 90:T].sum())
        push_up = float((D[T - 45:T + 1] == 1).mean())
        day_closes = {}
        for i, r in enumerate(rows):
            day_closes[r[3]] = c[i]
        last6 = list(day_closes.values())[-6:]
        up_sessions = sum(1 for a, b2 in zip(last6, last6[1:]) if b2 > a)
        W = min(256, T - 60)
        alive = (R[T - W + 1:T + 1] > 0).astype(float)
        b_health = float(alive.mean() * 2 - 1)
        dw = D[T - 63:T + 1]
        lock = abs(int((dw == 1).sum()) - int((dw == -1).sum())) / max(
            1, int((dw == 1).sum()) + int((dw == -1).sum()))
        vv = np.array([r[2] for r in rows], dtype=float)
        dollar = c * vv
        day_last = {}
        for i, r in enumerate(rows):
            day_last[r[3]] = dollar[i]
        dvals = list(day_last.values())
        med20_dollar = float(np.median(dvals[-21:-1])) if len(dvals) >= 21 else 0.0
        facts = {
            "normal_day_dollars": round(med20_dollar),
            "life_years": round(yrs, 1), "price": round(float(c[T]), 3),
            "life_peak": round(peak, 2), "crush": round(crush, 1),
            "deaths_per_year": round(deaths_yr), "deaths_2wk": deaths_2wk,
            "push_up_week": round(push_up, 2), "up_sessions_of_5": up_sessions,
            "B_health": round(b_health, 2), "L_lock": round(lock, 2),
        }
        # Joseph 2026-08-19, verbatim order: "don't buy suicide pills."
        # A stock destroyed a thousand-fold or worse (split-adjusted
        # lifetime peak >= 1000x today's price) is a dead shell that can
        # gap 60% overnight in the window no rule can act. Refused
        # always, before any other consideration. Cost disclosed: this
        # also refuses occasional winners of the same class (one in the
        # record); Joseph priced that and ordered the ban.
        # Joseph 2026-08-19: "can you even fill an order on a sucker bet
        # like that" — a slice must hide inside a NORMAL day. If 1% of
        # the normal day's traded money cannot absorb a $2,000 slice,
        # the name is untradable at our smallest size. Refused.
        day_list = sorted(day_last.keys())
        spike_gain = 0.0
        day_low_vs_prior = 1.0
        halt_jumps = 0
        if len(day_list) >= 2:
            prior_day, spike_day = day_list[-2], day_list[-1]
            prior_close = None
            spike_prices = []
            for i, r in enumerate(rows):
                if r[3] == prior_day:
                    prior_close = c[i]
                elif r[3] == spike_day:
                    spike_prices.append(c[i])
            if prior_close and spike_prices:
                spike_gain = 100 * (spike_prices[-1] / prior_close - 1)
                day_low_vs_prior = min(spike_prices) / prior_close
                for a2, b2 in zip(spike_prices, spike_prices[1:]):
                    if a2 > 0 and abs(b2 / a2 - 1) >= 0.15:
                        halt_jumps += 1
        facts["spike_gain_pct"] = round(spike_gain, 1)
        facts["halt_jumps"] = halt_jumps
        # Desk floor #3 (borrow): a violent pump in a thin name has no
        # shares to locate — the classic no-borrow class. Refused.
        if med20_dollar < 500_000 and spike_gain >= 50:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "desk floor — no-borrow class (thin name, "
                            f"+{spike_gain:.0f}% pump): nothing to locate",
                    "facts": facts}
        # Desk floor #5 (uptick rule): traded below -10% intraday, so
        # short sales fill only on upticks today. Refused.
        if day_low_vs_prior <= 0.90:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "desk floor — uptick restriction active "
                            "(fell 10%+ intraday): fills degrade",
                    "facts": facts}
        # Desk floor #6 (halts): repeated 15%+ jumps between readings on
        # the spike day mean halt-and-reopen trading. Refused.
        if halt_jumps >= 2:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": f"desk floor — halt-prone ({halt_jumps} violent "
                            "reopens today): stops cannot protect",
                    "facts": facts}
        if med20_dollar < 200_000:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "Joseph's fillability law — normal day trades "
                            f"${med20_dollar:,.0f}; a $2k slice cannot hide",
                    "facts": facts}
        if crush >= 1000:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "Joseph's ban — destroyed shell (lifetime peak "
                            f"{crush:,.0f}x today's price): never traded",
                    "facts": facts}
        sound = (yrs >= 2 and c[T] >= 0.5 * peak and crush < 4)
        charging = (crush >= 4 and deaths_2wk <= 2 and deaths_yr >= 30
                    and (push_up >= 0.5 or up_sessions >= 3))
        if sound:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "Rule 3 — sound structure, never a short",
                    "facts": facts}
        if charging:
            return {"symbol": symbol, "verdict": "REFUSE",
                    "rule": "Rules 4+5 — drained vehicle, rehearsal floor "
                            "clean, loading: the killer launch shape",
                    "facts": facts}
        return {"symbol": symbol, "verdict": "ALLOW",
                "rule": "no rule refuses; caps, cut line and clock govern",
                "facts": facts}
    except Exception as err:  # noqa: BLE001 — fail closed, always
        return {"symbol": symbol, "verdict": "REFUSE",
                "rule": f"fail-closed: {type(err).__name__}: {err}"}


def gate(symbols: list, channel: str) -> dict:
    """Read every candidate, file the sheet, return {sym: verdict-dict}."""
    out = {}
    for s in symbols:
        out[str(s)] = read_symbol(str(s))
    READINGS_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sheet = READINGS_DIR / f"{channel}_ENTRY_READINGS_{day}.json"
    existing = json.load(open(sheet)) if sheet.exists() else {}
    existing.update({k: v for k, v in out.items()})
    json.dump(existing, open(sheet, "w"), indent=1)
    for s, v in out.items():
        print(f"  [reading] {s}: {v['verdict']} — {v['rule']}")
    return out
