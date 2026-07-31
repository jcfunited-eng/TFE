"""
ch4_vtvr_spring.py — CH4 live engine: VTVR kernel + spring governance
=====================================================================

ENGINE VERSION: vtvr_spring_v1 (2026-07-31). Stamped on every trade.

The CH4 channel as originally mandated: the ORIGINAL VTVR joint-field
kernel (tools/isolated_vtvr_side_kernel.py via build_field — exact
rational L0-L4, full retention) is the structural engine; the spring
physics is the governance:

  ENERGY      price has declined >= 26.8% from the coarse structure's
              origin (26.8 derived from the 36.7 yield: 1/(1-.268)).
  COMPRESSION the kernel's own volume field has gone quiet for the
              vertex: mean swept volume over the last 5 bars below its
              trailing-20 mean (kernel-native negative space).
  RELEASE     the kernel's structural-share momentum has turned: dxhat
              positive over the last fine leg AND the fine (8-rung)
              price leg has flipped up.
  MIRROR      shorts by exact symmetry (rise >= 36.7% overhead, quiet,
              dxhat negative turn, fine down-flip).

  ENTRY       at the close of the bar where all conditions stand
              (decisions from CLOSED bars only; the daily pass runs
              after the close).
  EXIT        +36.7% touch (longs; -26.8% shorts) = harvest complete;
              or the coarse (16-rung) price leg flips against the
              position; or adverse move beyond the reversal bound
              (16 x trailing median move) — first to occur.
  BOOK        $100,000 paper; risk-parity: each position risks 1% of
              equity against its reversal bound; gross <= 100%; one
              position per symbol; same-bar guard.

Universe: cohorts A + B (the CH4 side channel's declared 60 names).
PAPER ONLY. No production contact. State: artifacts/vtvr_observer/
ch4_spring_book.json.

Usage: python tools/ch4_vtvr_spring.py          # process latest closed bar
       python tools/ch4_vtvr_spring.py DRY      # evaluate, change nothing
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field  # noqa: E402  (VTVR kernel path)
from tools.vtvr_star_state_replication import COHORT_B  # noqa: E402

ENGINE_VERSION = "vtvr_spring_v1"
BOOK_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "artifacts", "vtvr_observer", "ch4_spring_book.json")
CASH0 = 100_000.0
RISK_PCT = 1.0
MAX_GROSS_PCT = 100.0
YIELD_PCT = 36.7
DRAW_REQ = 100 * (1 - 1 / (1 + YIELD_PCT / 100))    # 26.8, derived
W = 20
COARSE, FINE = 16, 8
PRICE_FLOOR = 5.0


def leg_state(closes, mult):
    n = len(closes)
    moves = np.abs(np.diff(closes))
    direction, ext_i, org = 0, 0, closes[0]
    dirs = np.zeros(n, dtype=int)
    flips = np.zeros(n, dtype=int)
    origin = np.zeros(n)
    for t in range(1, n):
        w0 = max(0, t - W)
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


def evaluate_field():
    """Run the VTVR kernel on cohorts A+B and read the spring state of
    every vertex at the latest CLOSED bar."""
    from tools.vtvr_structure_search import UNIVERSE as COHORT_A  # authoritative
    decisions = []
    bar_date = None
    for label, universe in (("A", None), ("B", list(COHORT_B))):
        symbols, common, field, px_frac = build_field(universe, min_days=1200)
        m = len(common)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if common[-1][:10] == today and datetime.now(timezone.utc).hour < 21:
            m -= 1                       # drop the forming bar
        px = np.array([[float(v) for v in row] for row in px_frac])[:m]
        vol = np.array([[float(v) for v in row] for row in field.volume])[:m]
        dx = np.array([[float(v) for v in row] for row in field.dxhat])[:m]
        bar_date = common[m - 1][:10]
        for i, sym in enumerate(symbols):
            closes = px[:, i]
            if closes[-1] < PRICE_FLOOR:
                continue
            dirs_c, flips_c, origin_c, moves = leg_state(closes, COARSE)
            dirs_f, flips_f, _, _ = leg_state(closes, FINE)
            t = m - 1
            org = origin_c[t]
            state = {"symbol": sym, "cohort": label, "close": float(closes[t]),
                     "bar": bar_date, "engine": ENGINE_VERSION}
            # kernel-native compression: swept volume quiet
            v_now = float(np.mean(vol[max(0, t - 4):t + 1, i]))
            v_ref = float(np.mean(vol[max(0, t - W + 1):t + 1, i]))
            compressed = v_now < v_ref
            # kernel share momentum over the last 5 bars
            dx_turn = float(np.sum(dx[max(0, t - 4):t + 1, i]))
            bound_pct = 100 * COARSE * float(np.median(
                moves[max(0, t - W):t])) / closes[t] if t > 1 else 5.0
            long_ok = (org > 0 and 100 * (1 - closes[t] / org) >= DRAW_REQ
                       and compressed and dx_turn > 0
                       and dirs_f[t] == 1 and dirs_c[t] == -1)
            short_ok = (closes[t] > 0 and org > 0
                        and 100 * (org / closes[t] - 1) >= YIELD_PCT
                        and compressed and dx_turn < 0
                        and dirs_f[t] == -1 and dirs_c[t] == 1)
            state.update(side=1 if long_ok else (-1 if short_ok else 0),
                         bound_pct=round(max(bound_pct, 0.5), 2),
                         coarse_dir=int(dirs_c[t]), fine_dir=int(dirs_f[t]),
                         draw_pct=round(100 * (1 - closes[t] / org), 1) if org > 0 else None,
                         compressed=bool(compressed), dx_turn=round(dx_turn, 6))
            decisions.append(state)
    return bar_date, decisions


def load_book():
    if os.path.exists(BOOK_PATH):
        with open(BOOK_PATH) as f:
            return json.load(f)
    return {"engine": ENGINE_VERSION, "cash": CASH0, "positions": {},
            "closed": [], "last_processed": None,
            "declared": "risk-parity 1%/bound, gross<=100%, exits: "
                        "36.7 touch | coarse flip | bound breach"}


def main():
    dry = len(sys.argv) > 1 and sys.argv[1].upper() == "DRY"
    bar_date, decisions = evaluate_field()
    book = load_book()
    print(f"bar {bar_date} | decisions: "
          f"{sum(1 for d in decisions if d['side'] == 1)} long finds, "
          f"{sum(1 for d in decisions if d['side'] == -1)} short finds, "
          f"{len(decisions)} vertices")
    for d in decisions:
        if d["side"] != 0:
            print(f"  FIND {'LONG' if d['side'] == 1 else 'SHORT'} "
                  f"{d['symbol']} close={d['close']} draw={d['draw_pct']}% "
                  f"bound={d['bound_pct']}%")
    if dry:
        print("DRY run - no book changes")
        return 0
    if book["last_processed"] == bar_date:
        print("bar already processed; no-op")
        return 0

    dmap = {d["symbol"]: d for d in decisions}
    # exits
    for sym in sorted(list(book["positions"].keys())):
        pos = book["positions"][sym]
        d = dmap.get(sym)
        if d is None or d["bar"] != bar_date:
            continue
        px = d["close"]
        side = pos["side"]
        ret = 100 * (px / pos["entry_px"] - 1.0) * side
        tgt = YIELD_PCT if side == 1 else DRAW_REQ
        hit_target = ret >= tgt
        coarse_flip = (d["coarse_dir"] == -side)
        bound_breach = ret <= -pos["bound_pct"]
        if hit_target or coarse_flip or bound_breach:
            pnl = pos["notional"] * ret / 100.0
            book["cash"] += pos["notional"] + pnl
            book["closed"].append({
                "sym": sym, "side": side, "entry_date": pos["entry_date"],
                "exit_date": bar_date, "entry_px": pos["entry_px"],
                "exit_px": px, "ret_pct": round(ret, 2),
                "pnl": round(pnl, 2), "engine": pos.get("engine", ENGINE_VERSION),
                "reason": ("TARGET" if hit_target else
                           "COARSE_FLIP" if coarse_flip else "BOUND")})
            del book["positions"][sym]
    # entries
    equity = book["cash"] + sum(p["notional"] for p in book["positions"].values())
    gross = sum(p["notional"] for p in book["positions"].values())
    for d in sorted(decisions, key=lambda x: x["symbol"]):
        if d["side"] == 0 or d["symbol"] in book["positions"]:
            continue
        notional = equity * (RISK_PCT / max(d["bound_pct"], 0.5))
        if gross + notional > equity * (MAX_GROSS_PCT / 100.0):
            notional = max(0.0, equity * (MAX_GROSS_PCT / 100.0) - gross)
        if notional <= 0 or notional > book["cash"]:
            continue
        book["positions"][d["symbol"]] = {
            "side": d["side"], "entry_px": d["close"], "entry_date": bar_date,
            "notional": round(notional, 2), "bound_pct": d["bound_pct"],
            "engine": ENGINE_VERSION}
        book["cash"] -= notional
        gross += notional
    book["last_processed"] = bar_date
    book["last_run_utc"] = datetime.now(timezone.utc).isoformat()
    book["equity_mark"] = round(book["cash"] + sum(
        p["notional"] * (1 + (dmap.get(s, {"close": p["entry_px"]})["close"]
                              / p["entry_px"] - 1) * p["side"])
        for s, p in book["positions"].items()), 2)
    os.makedirs(os.path.dirname(BOOK_PATH), exist_ok=True)
    with open(BOOK_PATH, "w") as f:
        json.dump(book, f, indent=1)
    print(f"book: open={len(book['positions'])} closed={len(book['closed'])} "
          f"cash=${book['cash']:,.2f} equity=${book['equity_mark']:,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
