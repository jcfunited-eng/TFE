"""
vtvr_ch4_paper_sim.py
======================

NON-CANONICAL — "CH4" paper simulation of the coherent-laggard state with
CH2's economics and an L5 domain translation. Simulation only: no orders,
no production import, kernel untouched.

ECONOMICS (mirrors CH2):
    funded          $100,000
    per position    $2,500 (2.5% of funded)
    cash-constrained: skip entries when cash < position size

L5 TRANSLATION (declared, physics-grounded, no tuned constants):
    ENTRY   stock enters COHERENT LAGGARD at close of day t
            (BRTH.L:MID & COH.S:HI & LTRND.L:LO, thirds within its
            cohort) → buy at close of day t+1 (one-bar lag, no
            look-ahead). No re-entry while held; 20-bar cooldown
            after any exit.
    EXIT    whichever comes first:
      restored   leadership trend reaches the TOP third for 3
                 consecutive bars — the drain has fully reversed; the
                 restoring flow has completed (structure complete)
      timeout    90 bars in position (the physics horizon)
      failsafe   close below -15% from entry (disaster guard —
                 structure claims are not crash claims)

UNIVERSE  cohorts A + B (60 names), state evaluated within each cohort
          exactly as validated. Signals merge into ONE cash book.

MODES
    --backtest              dress rehearsal over all available dates;
                            writes equity/trades JSON for visualization
    (default: live)         update the persistent paper book with the
                            latest bar; book lives in
                            artifacts/vtvr_observer/ch4_book.json

Usage:
    python tools/vtvr_ch4_paper_sim.py --backtest
    python tools/vtvr_ch4_paper_sim.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.vtvr_leadlag_walkforward as wf  # noqa: E402
from tools.vtvr_structure_search import (  # noqa: E402
    build_field,
    per_step_arrays,
    window_desc,
    W_LONG,
    W_SHORT,
    _mean,
)
from tools.vtvr_star_state_replication import COHORT_B  # noqa: E402

FUNDED = 100_000.0
POSITION = 2_500.0
HOLD_MAX = 90
RESTORE_BARS = 3
FAILSAFE = -0.15
COOLDOWN = 20

ART_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "artifacts", "vtvr_observer",
)
BOOK_PATH = os.path.join(ART_DIR, "ch4_book.json")
BACKTEST_JSON = os.path.join(ART_DIR, "ch4_backtest.json")


def cohort_signals(universe):
    """Per-date state membership + per-stock LTRND band + prices, one cohort."""
    wf.UNIVERSE = universe
    symbols, common, field, px = build_field()
    arrs = per_step_arrays(symbols, field)
    n, m_total = arrs["n"], arrs["m"]

    dates = [d[:10] for d in common]
    in_state = {}   # date -> set(sym)
    ltrnd_lo = {}   # date -> set(sym) in bottom third
    for m in range(W_LONG, m_total):
        dl = window_desc(arrs, m, W_LONG)
        ds = window_desc(arrs, m, W_SHORT)

        def band(descs, key):
            order = sorted(range(n), key=lambda i: descs[i][key])
            return {i: ("LO", "MID", "HI")[min(2, (p * 3) // n)]
                    for p, i in enumerate(order)}

        brth = band(dl, "BRTH")
        coh = band(ds, "COH")
        ltr = band(dl, "LTRND")
        d = dates[m]
        in_state[d] = {symbols[i] for i in range(n)
                       if brth[i] == "MID" and coh[i] == "HI" and ltr[i] == "LO"}
        ltrnd_lo[d] = {symbols[i] for i in range(n) if ltr[i] == "HI"}

    prices = {dates[k]: {symbols[i]: px[k][i] for i in range(n)}
              for k in range(m_total)}
    return dates, in_state, ltrnd_lo, prices


def merged_universe_data():
    print("Building cohort A field...")
    da, sa, la, pa = cohort_signals(list(wf.UNIVERSE))
    print("Building cohort B field...")
    db, sb, lb, pb = cohort_signals(COHORT_B)
    dates = sorted(set(da) & set(db))
    in_state = {d: sa.get(d, set()) | sb.get(d, set()) for d in dates}
    ltrnd_lo = {d: la.get(d, set()) | lb.get(d, set()) for d in dates}
    prices = {d: {**pa.get(d, {}), **pb.get(d, {})} for d in dates}
    return dates, in_state, ltrnd_lo, prices


def simulate(dates, in_state, ltrnd_lo, prices, start_idx):
    cash = FUNDED
    open_pos = {}       # sym -> dict
    cooldown = {}       # sym -> release date index
    closed = []
    equity_curve = []
    pending_entries = set()

    for k in range(start_idx, len(dates)):
        d = dates[k]
        px_d = prices[d]

        # 1. Fill yesterday's pending entries at today's close
        for sym in sorted(pending_entries):
            if sym in open_pos or px_d.get(sym) is None:
                continue
            if cash < POSITION:
                continue
            shares = POSITION / px_d[sym]
            open_pos[sym] = {
                "entry_date": d, "entry_px": px_d[sym], "shares": shares,
                "bars": 0, "restore_run": 0,
            }
            cash -= POSITION
        pending_entries = set()

        # 2. Manage open positions
        for sym in list(open_pos):
            p = open_pos[sym]
            px_now = px_d.get(sym)
            if px_now is None:
                continue
            p["bars"] += 1
            ret = px_now / p["entry_px"] - 1
            # ltrnd_lo holds the TOP-third members (drain fully reversed)
            if sym in ltrnd_lo.get(d, set()):
                p["restore_run"] += 1
            else:
                p["restore_run"] = 0
            reason = None
            if ret <= FAILSAFE:
                reason = "failsafe"
            elif p["restore_run"] >= RESTORE_BARS:
                reason = "restored"
            elif p["bars"] >= HOLD_MAX:
                reason = "timeout"
            if reason:
                proceeds = p["shares"] * px_now
                cash += proceeds
                closed.append({
                    "sym": sym, "entry_date": p["entry_date"],
                    "exit_date": d, "entry_px": round(p["entry_px"], 4),
                    "exit_px": round(px_now, 4),
                    "pnl": round(proceeds - POSITION, 2),
                    "ret_pct": round(ret * 100, 2),
                    "bars": p["bars"], "reason": reason,
                })
                cooldown[sym] = k + COOLDOWN
                del open_pos[sym]

        # 3. New signals at today's close -> enter tomorrow
        for sym in in_state.get(d, set()):
            if sym in open_pos or cooldown.get(sym, -1) > k:
                continue
            pending_entries.add(sym)

        mark = cash + sum(
            p["shares"] * prices[d].get(sym, p["entry_px"])
            for sym, p in open_pos.items()
        )
        equity_curve.append({"date": d, "equity": round(mark, 2),
                             "open": len(open_pos), "cash": round(cash, 2)})

    return equity_curve, closed, open_pos, cash


def backtest():
    dates, in_state, ltrnd_lo, prices = merged_universe_data()
    start_idx = next(i for i, d in enumerate(dates) if d in in_state)
    eq, closed, still_open, cash = simulate(
        dates, in_state, ltrnd_lo, prices, start_idx)

    wins = [t for t in closed if t["pnl"] > 0]
    total_pnl = sum(t["pnl"] for t in closed)
    final = eq[-1]["equity"]
    peak, mdd = float("-inf"), 0.0
    for row in eq:
        peak = max(peak, row["equity"])
        mdd = min(mdd, row["equity"] - peak)

    by_reason = {}
    for t in closed:
        r = by_reason.setdefault(t["reason"], {"n": 0, "pnl": 0.0, "w": 0})
        r["n"] += 1
        r["pnl"] += t["pnl"]
        r["w"] += 1 if t["pnl"] > 0 else 0

    print()
    print("=" * 66)
    print("CH4 PAPER DRESS REHEARSAL — coherent laggard, CH2 economics")
    print("=" * 66)
    print(f"Window: {eq[0]['date']} .. {eq[-1]['date']} "
          f"({len(eq)} trading days)")
    print(f"Funded ${FUNDED:,.0f} | ${POSITION:,.0f}/position")
    print(f"Closed trades: {len(closed)} | open at end: {len(still_open)}")
    print(f"Win rate (closed): "
          f"{100 * len(wins) / len(closed) if closed else 0:.1f}%")
    print(f"Realized P&L: ${total_pnl:+,.2f}")
    print(f"Final equity: ${final:,.2f}  "
          f"({(final / FUNDED - 1) * 100:+.2f}% on funded)")
    print(f"Max drawdown: ${mdd:,.2f}")
    print(f"Avg hold: {_mean([t['bars'] for t in closed]):.0f} bars")
    print()
    print("Exits by reason:")
    for r, v in sorted(by_reason.items()):
        print(f"  {r:<10} n={v['n']:<4} win={100 * v['w'] / v['n']:5.1f}%  "
              f"pnl=${v['pnl']:+,.2f}")

    os.makedirs(ART_DIR, exist_ok=True)
    with open(BACKTEST_JSON, "w", encoding="utf-8") as fh:
        json.dump({"equity": eq, "closed": closed,
                   "funded": FUNDED, "position": POSITION}, fh)
    print(f"\nBacktest data: {BACKTEST_JSON}")


def live():
    dates, in_state, ltrnd_lo, prices = merged_universe_data()
    os.makedirs(ART_DIR, exist_ok=True)
    if os.path.exists(BOOK_PATH):
        with open(BOOK_PATH, encoding="utf-8") as fh:
            book = json.load(fh)
    else:
        book = {"started": dates[-1], "cash": FUNDED, "open": {},
                "closed": [], "cooldown": {}}
        print(f"New CH4 paper book opened {dates[-1]} with ${FUNDED:,.0f}")

    # Replay simulate() mechanics for just the latest bar
    d = dates[-1]
    k = len(dates) - 1
    px_d = prices[d]

    for sym in sorted(book.get("pending", [])):
        if sym in book["open"] or px_d.get(sym) is None:
            continue
        if book["cash"] < POSITION:
            continue
        book["open"][sym] = {
            "entry_date": d, "entry_px": px_d[sym],
            "shares": POSITION / px_d[sym], "bars": 0, "restore_run": 0,
        }
        book["cash"] -= POSITION
        print(f"ENTER {sym} @ {px_d[sym]:.2f}")

    for sym in list(book["open"]):
        p = book["open"][sym]
        px_now = px_d.get(sym)
        if px_now is None:
            continue
        p["bars"] += 1
        ret = px_now / p["entry_px"] - 1
        p["restore_run"] = p["restore_run"] + 1 \
            if sym in ltrnd_lo.get(d, set()) else 0
        reason = ("failsafe" if ret <= FAILSAFE else
                  "restored" if p["restore_run"] >= RESTORE_BARS else
                  "timeout" if p["bars"] >= HOLD_MAX else None)
        if reason:
            proceeds = p["shares"] * px_now
            book["cash"] += proceeds
            book["closed"].append({
                "sym": sym, "entry_date": p["entry_date"], "exit_date": d,
                "pnl": round(proceeds - POSITION, 2),
                "ret_pct": round(ret * 100, 2), "reason": reason,
            })
            book["cooldown"][sym] = d
            del book["open"][sym]
            print(f"EXIT {sym} ({reason}) pnl={proceeds - POSITION:+.2f}")

    cooldown_block = set()
    for sym, cd_date in book["cooldown"].items():
        if cd_date in dates and len(dates) - 1 - dates.index(cd_date) < COOLDOWN:
            cooldown_block.add(sym)
    book["pending"] = sorted(
        sym for sym in in_state.get(d, set())
        if sym not in book["open"] and sym not in cooldown_block
    )

    mark = book["cash"] + sum(
        p["shares"] * px_d.get(sym, p["entry_px"])
        for sym, p in book["open"].items()
    )
    book["last_update"] = datetime.now(timezone.utc).isoformat()
    book["last_bar"] = d
    book["equity"] = round(mark, 2)
    with open(BOOK_PATH, "w", encoding="utf-8") as fh:
        json.dump(book, fh, indent=1)

    print(f"\nCH4 paper book @ {d}: equity=${mark:,.2f} "
          f"cash=${book['cash']:,.2f} open={len(book['open'])} "
          f"pending={book['pending']}")
    print(f"Book: {BOOK_PATH}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--backtest", action="store_true")
    args = ap.parse_args()
    (backtest if args.backtest else live)()
