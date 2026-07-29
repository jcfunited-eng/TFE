"""
vtvr_ch4_full_scale.py
=======================

NON-CANONICAL — full-scale CH4 dress rehearsal: the coherent-laggard state
deployed the way capital actually earns.

Fixes the two failures of the first rehearsal:
  STARVATION  universe scales from 60 to 300 declared names (10 cohorts of
              30; each cohort is one joint field, exactly the validated
              construction). ~5x the opportunity flow.
  LEAKY L5    the validated protocol is the trade: enter any day a stock
              is in state (one position per ticker), hold the 90-bar
              physics horizon, -15% failsafe only. No early exits.

ECONOMICS
  funded      $100,000
  position    $5,000 (20-slot book at full deployment)
  entry       next-bar close after signal (no look-ahead)
  cooldown    20 bars per ticker after exit

Universe: tools/vtvr_universe_300.json (frozen, mechanical rule).
Kernel untouched; simulation only; no production import.

Usage: python tools/vtvr_ch4_full_scale.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_ch4_paper_sim import cohort_signals  # noqa: E402
from tools.vtvr_structure_search import _mean  # noqa: E402

FUNDED = 100_000.0
POSITION = 5_000.0
HOLD_MAX = 90
FAILSAFE = -0.15
COOLDOWN = 20
COHORT_SIZE = 30

UNIVERSE_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vtvr_universe_300.json")
ART_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts", "vtvr_observer")
OUT_JSON = os.path.join(ART_DIR, "ch4_full_scale.json")


def main():
    with open(UNIVERSE_JSON, encoding="utf-8") as fh:
        symbols = json.load(fh)["symbols"]
    cohorts = [symbols[i:i + COHORT_SIZE]
               for i in range(0, len(symbols), COHORT_SIZE)]
    cohorts = [c for c in cohorts if len(c) >= 10]
    print(f"{len(symbols)} symbols in {len(cohorts)} cohorts")

    all_dates = set()
    in_state = {}
    prices = {}
    for ci, cohort in enumerate(cohorts):
        print(f"Cohort {ci + 1}/{len(cohorts)}: building joint field...")
        try:
            # 1200+ bars required per symbol; one IPO must not gut a cohort
            dates, st, _ltr, px = cohort_signals(cohort, min_days=1200)
        except Exception as e:
            print(f"  cohort {ci + 1} failed ({e}) — skipped")
            continue
        if len(px[dates[0]]) < 15:
            print(f"  cohort {ci + 1}: fewer than 15 usable symbols — skipped")
            continue
        # UNION across cohorts: each cohort trades on its own dates
        all_dates.update(dates)
        for d, syms in st.items():
            in_state.setdefault(d, set()).update(syms)
        for d, m in px.items():
            prices.setdefault(d, {}).update(m)

    dates = sorted(all_dates)
    print(f"Union of cohort dates: {len(dates)}")

    # ── book simulation: validated protocol ─────────────────────────────
    cash = FUNDED
    open_pos = {}
    cooldown = {}
    closed = []
    eq = []
    pending = set()

    start_idx = next(i for i, d in enumerate(dates) if in_state.get(d))
    for k in range(start_idx, len(dates)):
        d = dates[k]
        px_d = prices.get(d, {})

        for sym in sorted(pending):
            if sym in open_pos or px_d.get(sym) is None:
                continue
            if cash < POSITION:
                continue
            open_pos[sym] = {"entry_date": d, "entry_px": px_d[sym],
                             "shares": POSITION / px_d[sym], "bars": 0}
            cash -= POSITION
        pending = set()

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
                proceeds = p["shares"] * px_now
                cash += proceeds
                closed.append({"sym": sym, "entry_date": p["entry_date"],
                               "exit_date": d,
                               "entry_px": round(p["entry_px"], 4),
                               "exit_px": round(px_now, 4),
                               "pnl": round(proceeds - POSITION, 2),
                               "ret_pct": round(ret * 100, 2),
                               "bars": p["bars"], "reason": reason})
                cooldown[sym] = k + COOLDOWN
                del open_pos[sym]

        for sym in in_state.get(d, set()):
            if sym in open_pos or cooldown.get(sym, -1) > k:
                continue
            pending.add(sym)

        mark = cash + sum(p["shares"] * px_d.get(s, p["entry_px"])
                          for s, p in open_pos.items())
        eq.append({"date": d, "equity": round(mark, 2),
                   "open": len(open_pos), "cash": round(cash, 2)})

    wins = [t for t in closed if t["pnl"] > 0]
    total_pnl = sum(t["pnl"] for t in closed)
    final = eq[-1]["equity"]
    years = len(eq) / 252
    cagr = (final / FUNDED) ** (1 / years) - 1 if years > 0 else 0
    peak, mdd = float("-inf"), 0.0
    for r in eq:
        peak = max(peak, r["equity"])
        mdd = min(mdd, (r["equity"] - peak) / peak)
    avg_open = _mean([r["open"] for r in eq])

    print()
    print("=" * 68)
    print("CH4 FULL SCALE — 300 names, validated protocol, $5k positions")
    print("=" * 68)
    print(f"Window: {eq[0]['date']} .. {eq[-1]['date']} ({years:.1f} years)")
    print(f"Closed trades: {len(closed)} | open at end: {len(open_pos)}")
    print(f"Win rate (closed): {100 * len(wins) / len(closed):.1f}%")
    print(f"Avg per trade: {_mean([t['ret_pct'] for t in closed]):+.2f}%")
    print(f"Realized P&L: ${total_pnl:+,.2f}")
    print(f"FINAL EQUITY: ${final:,.2f}  ({(final / FUNDED - 1) * 100:+.1f}% total)")
    print(f"CAGR: {cagr * 100:+.2f}%/yr")
    print(f"Max drawdown: {mdd * 100:.2f}%")
    print(f"Avg positions open: {avg_open:.1f} of 20 "
          f"(avg deployment ${avg_open * POSITION:,.0f})")

    os.makedirs(ART_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({"equity": eq, "closed": closed, "funded": FUNDED,
                   "position": POSITION}, fh)
    print(f"\nData: {OUT_JSON}")


if __name__ == "__main__":
    main()
