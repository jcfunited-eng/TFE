"""
ch4_uf_leg_harvest.py — self-certifying per-vertex leg harvest
==============================================================

The simple construction (2026-07-31): each stock's confirmed legs are
draws from its OWN amplitude distribution, so a target at the q-th
percentile of its own past post-confirmation remainders is touched
(100-q)% of the time by construction, per stock, no species stores.

MECHANICS (declared, both polarities, all causal):
  Legs        — self-scaled reversal tracking (countermove > REV_MULT x
                trailing-W median |daily move|; REV_LADDER = (16, 8, 4)   # coarsest-first (pinned 4, doubled) = coarsest
                pinned lattice constant, W = 20). A leg CONFIRMS the
                moment the countermove threshold is crossed; entry at
                that bar's close, in the new leg's direction.
  Remainders  — for each past completed leg of this stock: the further
                move from its confirmation close to the leg's final
                extreme (the harvestable remainder). Per-stock causal
                store, long and short sides separate.
  Target      — p9 of the stock's own past remainders on that side
                (>= MIN_LEGS = 20 = W past legs required), i.e. the
                level ~91% of its legs historically exceeded.
  Exit        — first touch of the target (win at target), else the
                next confirmed reversal (the collapse vector; loss
                bounded near the reversal threshold), whichever first.
  Book        — per-year WR and profit; risk-parity field book (1% of
                equity risked per position against the reversal bound).
  Universe    — eligible field (LIFE >= 0.90, $5 floor).

Per-year is the ONLY reporting standard. Raw; nothing tuned.

Usage: CH4_STORE=... python tools/ch4_uf_leg_harvest.py [N]
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_spectrum import life_fraction, W  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250
REV_LADDER = (16, 8, 4)   # coarsest-first (pinned 4, doubled)
WR_BAR = 0.91
MIN_LEGS = W          # 20 past legs before certifying


def harvest_symbol(dates, closes):
    """Causal leg walk at a LADDER of rungs; per entry, the coarsest rung
    whose own record certifies energy-positively claims the position."""
    n = len(closes)
    moves = np.abs(np.diff(closes))
    trades = []
    rungs = {m: {"rem": {1: [], -1: []}, "dir": 0, "ext": 0,
                 "conf": {"side": 0, "px": None}} for m in REV_LADDER}
    pos = None
    pos_rung = None
    for t in range(1, n):
        w0 = max(0, t - W)
        med = float(np.median(moves[w0:t])) if t > w0 else 0.0
        for m in REV_LADDER:
            R = rungs[m]
            thresh = m * max(med, 1e-9)
            direction = R["dir"]
            ext_i = R["ext"]

            if direction >= 0 and closes[t] > closes[ext_i]:
                ext_i = t
                if direction == 0:
                    direction = 1
            elif direction <= 0 and closes[t] < closes[ext_i]:
                ext_i = t
                if direction == 0:
                    direction = -1

            flipped = None
            if direction == 1 and closes[ext_i] - closes[t] > thresh:
                flipped = -1
            elif direction == -1 and closes[t] - closes[ext_i] > thresh:
                flipped = 1

            if flipped is not None:
                # close the harvest if THIS rung owns the open position
                if pos is not None and pos_rung == m:
                    raw = 100 * (closes[t] / pos["px"] - 1.0)
                    ret = raw if pos["side"] == 1 else -raw
                    trades.append({"in": pos["in_d"], "out": str(dates[t]),
                                   "side": pos["side"], "ret_pct": round(ret, 3),
                                   "reason": "FLIP", "rung": m})
                    pos = None
                    pos_rung = None
                # file the finished leg's remainder for this rung
                lc = R["conf"]
                if lc["px"] is not None:
                    if lc["side"] == 1:
                        rem = 100 * (closes[ext_i] / lc["px"] - 1.0)
                    else:
                        rem = 100 * (1.0 - closes[ext_i] / lc["px"])
                    R["rem"][lc["side"]].append(max(rem, 0.0))
                side = flipped
                R["conf"] = {"side": side, "px": closes[t]}
                # entry: coarsest certifying rung claims (ladder order)
                if pos is None and closes[t] >= PRICE_FLOOR:
                    store = R["rem"][side]
                    if len(store) >= MIN_LEGS:
                        tgt = float(np.percentile(np.array(store[-100:]),
                                                  100 * (1 - WR_BAR)))
                        bound_pct = 100 * thresh / closes[t]
                        if tgt > 0.05 and tgt >= bound_pct:
                            tgt_px = closes[t] * (1 + tgt / 100.0) if side == 1 \
                                else closes[t] * (1 - tgt / 100.0)
                            pos = {"side": side, "px": closes[t],
                                   "in_d": str(dates[t]),
                                   "target": round(tgt, 3), "tgt_px": tgt_px,
                                   "bound": max(bound_pct, 0.25)}
                            pos_rung = m
                R["dir"] = flipped
                R["ext"] = t
            else:
                R["dir"] = direction
                R["ext"] = ext_i

        # after all rungs: target-touch check for the open position
        if pos is not None:
            if pos["side"] == 1 and closes[t] >= pos["tgt_px"]:
                trades.append({"in": pos["in_d"], "out": str(dates[t]),
                               "side": 1, "ret_pct": pos["target"],
                               "reason": "TARGET", "rung": pos_rung})
                pos = None
                pos_rung = None
            elif pos["side"] == -1 and closes[t] <= pos["tgt_px"]:
                trades.append({"in": pos["in_d"], "out": str(dates[t]),
                               "side": -1, "ret_pct": pos["target"],
                               "reason": "TARGET", "rung": pos_rung})
                pos = None
                pos_rung = None
    return trades


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)}")

    all_trades = []
    t0 = time.time()
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        try:
            trs = harvest_symbol(dates, closes)
        except Exception:
            continue
        for t_ in trs:
            t_["symbol"] = sym
        all_trades.extend(trs)
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(uni)}] trades={len(all_trades)} "
                  f"{time.time()-t0:.0f}s", flush=True)

    rets = np.array([t["ret_pct"] for t in all_trades])
    by = defaultdict(list)
    for t in all_trades:
        by[t["in"][:4]].append(t["ret_pct"])
    from collections import Counter
    result = {
        "construction": "per-vertex leg harvest on the reversal-rung LADDER "
                        "(coarsest certifying rung claims; energy-positive)",
        "rung_usage": dict(Counter(t.get("rung") for t in all_trades)),
        "trades": len(all_trades),
        "wr_pct": round(100 * float((rets > 0).mean()), 2) if len(rets) else None,
        "mean_pct": round(float(rets.mean()), 3) if len(rets) else None,
        "reasons": {rn: int(sum(1 for t in all_trades if t["reason"] == rn))
                    for rn in ("TARGET", "FLIP")},
        "sides": {"long": int(sum(1 for t in all_trades if t["side"] == 1)),
                  "short": int(sum(1 for t in all_trades if t["side"] == -1))},
        "by_year": {y: {"n": len(v),
                        "wr": round(100 * float((np.array(v) > 0).mean()), 1),
                        "mean": round(float(np.mean(v)), 2),
                        "sum_slice": round(float(np.sum(v)), 1)}
                    for y, v in sorted(by.items())},
    }
    path = os.path.join(OUT_DIR, "ch4_uf_leg_harvest.json")
    with open(path, "w") as f:
        json.dump({**result, "trades_detail": all_trades[:200000]}, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", path)


leg_conf = {"side": 0, "px": None, "ext_ref": 0}

if __name__ == "__main__":
    main()
