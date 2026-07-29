"""
vtvr_ch4_null_book.py
======================

NON-CANONICAL — the blind book: identical mechanics to the CH4 full-scale
rehearsal ($5k positions, 20 slots, next-bar entry, 90-bar hold, -15%
failsafe, 20-bar cooldown, same 300-name universe and dates) but entries
are chosen DETERMINISTICALLY-BLINDLY (SHA-256 order per date) instead of
by the coherent-laggard state.

Purpose: separate physics from market. CH4's edge is ONLY the amount by
which the state book beats this blind book on the same window.

Usage: python tools/vtvr_ch4_null_book.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.run_market_vtvr_capture import fetch_exact_bars  # noqa: E402
from tools.vtvr_structure_search import _mean  # noqa: E402

FUNDED = 100_000.0
POSITION = 5_000.0
HOLD_MAX = 90
FAILSAFE = -0.15
COOLDOWN = 20
SLOTS = 20

UNIVERSE_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vtvr_universe_300.json")
ART_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts", "vtvr_observer")
OUT_JSON = os.path.join(ART_DIR, "ch4_null_book.json")


def main():
    with open(UNIVERSE_JSON, encoding="utf-8") as fh:
        symbols = json.load(fh)["symbols"]

    start_iso = (datetime.now(timezone.utc) - timedelta(days=2600)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    prices = {}
    kept = 0
    for s in symbols:
        try:
            bars = fetch_exact_bars(s, "1Day", 1700, start_iso)
        except Exception:
            continue
        if len(bars) < 1200:
            continue
        kept += 1
        for t, c in bars.items():
            prices.setdefault(t[:10], {})[s] = float(c)
    dates = sorted(prices.keys())
    print(f"{kept} symbols, {len(dates)} dates")

    # Align start with the state book's window (first signal ~2021-01)
    start_idx = next(i for i, d in enumerate(dates) if d >= "2021-01-15")

    cash = FUNDED
    open_pos = {}
    cooldown = {}
    closed = []
    eq = []

    for k in range(start_idx, len(dates)):
        d = dates[k]
        px_d = prices[d]

        for sym in list(open_pos):
            p = open_pos[sym]
            px_now = px_d.get(sym)
            if px_now is None:
                continue
            p["bars"] += 1
            ret = px_now / p["entry_px"] - 1
            reason = ("failsafe" if ret <= FAILSAFE else
                      "horizon" if p["bars"] >= HOLD_MAX else None)
            if reason:
                cash += p["shares"] * px_now
                closed.append({"pnl": p["shares"] * px_now - POSITION,
                               "ret": ret})
                cooldown[sym] = k + COOLDOWN
                del open_pos[sym]

        # Blind fills: deterministic SHA order over today's tradable names
        if len(open_pos) < SLOTS and cash >= POSITION:
            ranked = sorted(
                (s for s in px_d
                 if s not in open_pos and cooldown.get(s, -1) <= k),
                key=lambda s: hashlib.sha256(f"{d}:{s}".encode()).digest())
            for sym in ranked:
                if len(open_pos) >= SLOTS or cash < POSITION:
                    break
                open_pos[sym] = {"entry_px": px_d[sym],
                                 "shares": POSITION / px_d[sym], "bars": 0}
                cash -= POSITION

        mark = cash + sum(p["shares"] * px_d.get(s, p["entry_px"])
                          for s, p in open_pos.items())
        eq.append({"date": d, "equity": round(mark, 2)})

    final = eq[-1]["equity"]
    years = len(eq) / 252
    cagr = (final / FUNDED) ** (1 / years) - 1
    peak, mdd = float("-inf"), 0.0
    for r in eq:
        peak = max(peak, r["equity"])
        mdd = min(mdd, (r["equity"] - peak) / peak)
    wins = [t for t in closed if t["pnl"] > 0]

    print()
    print("BLIND BOOK (same mechanics, sightless entries):")
    print(f"  Window: {eq[0]['date']} .. {eq[-1]['date']} ({years:.1f}y)")
    print(f"  Closed: {len(closed)} | win rate {100*len(wins)/len(closed):.1f}% "
          f"| avg {100*_mean([t['ret'] for t in closed]):+.2f}%/trade")
    print(f"  FINAL EQUITY: ${final:,.2f} ({(final/FUNDED-1)*100:+.1f}%)")
    print(f"  CAGR: {cagr*100:+.2f}%/yr | max DD {mdd*100:.2f}%")

    os.makedirs(ART_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({"equity": eq, "final": final, "cagr": cagr, "mdd": mdd,
                   "n_closed": len(closed)}, fh)
    print(f"  Data: {OUT_JSON}")


if __name__ == "__main__":
    main()
