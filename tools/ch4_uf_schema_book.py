"""
ch4_uf_schema_book.py — honest overlap-constrained book on schema predictions
=============================================================================

Consumes the persisted causal band predictions (ch4_uf_spectrum.json) and
runs the DECLARED book mechanics on the UP side: $100,000; 10% equity
slices; max 10 concurrent; one position per symbol; enter at the
prediction's issue-date close; exit at its exit-date close realizing the
recorded next-gate displacement; capital is unavailable while held; ties
broken alphabetically; no costs. DOWN predictions are the avoid channel
(not shorted). Reported whole-span and per calendar year, per tier.

Usage: python tools/ch4_uf_schema_book.py [min_live_cons]
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "artifacts", "ch4_uf")
CASH0, SLICE, MAX_POS = 100_000.0, 0.10, 10


def run(min_cons: float):
    d = json.load(open(os.path.join(OUT_DIR, "ch4_uf_spectrum.json")))
    alpha = os.environ.get("SCHEMA_ALPHA", "bigram")
    rows = [r for r in d["band_prediction_rows"]
            if r["dir"] == "UP" and r["live_cons"] >= min_cons
            and r.get("alpha", "bigram") == alpha]
    rows.sort(key=lambda r: (r["issue_date"], r["symbol"]))

    # event calendar
    events = defaultdict(lambda: {"enter": [], "exit": []})
    for i, r in enumerate(rows):
        events[r["issue_date"]]["enter"].append(i)
        events[r["exit_date"]]["exit"].append(i)
    all_days = sorted(events.keys())

    cash = CASH0
    open_pos = {}          # row_idx -> invested amount
    held_syms = set()
    equity_by_day = []
    trades = []
    for day in all_days:
        # exits first
        for i in sorted(events[day]["exit"]):
            if i in open_pos:
                amt = open_pos.pop(i)
                r = rows[i]
                held_syms.discard(r["symbol"])
                proceeds = amt * (1.0 + r["disp_pct"] / 100.0)
                cash += proceeds
                trades.append({"symbol": r["symbol"], "in": r["issue_date"],
                               "out": r["exit_date"], "ret_pct": r["disp_pct"],
                               "hit": r["hit"]})
        # entries
        for i in sorted(events[day]["enter"], key=lambda j: rows[j]["symbol"]):
            r = rows[i]
            if r["symbol"] in held_syms or len(open_pos) >= MAX_POS:
                continue
            if r["exit_date"] <= r["issue_date"]:
                continue
            equity = cash + sum(open_pos.values())   # mark at cost (conservative)
            budget = min(cash, SLICE * equity)
            if budget <= 0:
                continue
            open_pos[i] = budget
            held_syms.add(r["symbol"])
            cash -= budget
        equity_by_day.append((day, cash + sum(open_pos.values())))

    # force-close leftovers at recorded outcome
    for i in sorted(list(open_pos.keys())):
        amt = open_pos.pop(i)
        r = rows[i]
        cash += amt * (1.0 + r["disp_pct"] / 100.0)
        trades.append({"symbol": r["symbol"], "in": r["issue_date"],
                       "out": r["exit_date"], "ret_pct": r["disp_pct"],
                       "hit": r["hit"]})
    final = cash

    rets = [t["ret_pct"] for t in trades]
    wins = sum(1 for t in trades if t["ret_pct"] > 0)
    by_year = {}
    prev = CASH0
    ys = CASH0
    cy = equity_by_day[0][0][:4] if equity_by_day else None
    for day, eq in equity_by_day:
        if day[:4] != cy:
            by_year[cy] = round(100 * (prev / ys - 1), 2)
            cy, ys = day[:4], prev
        prev = eq
    if cy:
        by_year[cy] = round(100 * (final / ys - 1), 2)

    out = {
        "alpha": alpha,
        "tier_min_live_cons": min_cons,
        "trades": len(trades),
        "wr_pct": round(100 * wins / len(rets), 2) if rets else None,
        "mean_trade_pct": round(sum(rets) / len(rets), 3) if rets else None,
        "final_equity": round(final, 2),
        "total_return_pct": round(100 * (final / CASH0 - 1), 2),
        "by_year": by_year,
        "skipped_full_book": None,
    }
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    tier = float(sys.argv[1]) if len(sys.argv) > 1 else 0.75
    results = {}
    for t in ([tier] if len(sys.argv) > 1 else [0.75, 0.80, 0.85, 0.90, 0.95]):
        results[str(t)] = run(t)
    with open(os.path.join(OUT_DIR, "ch4_uf_schema_book.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("filed:", os.path.join(OUT_DIR, "ch4_uf_schema_book.json"))
