"""
ch4_uf_spring_finder.py — the deterministic spring: energy, compression, release
================================================================================

Zero learning, zero labels, zero majority votes. The physics:

  ENERGY      the decline itself. A coarse structure that has fallen
              d >= 26.8% from its origin peak has an algebraic path of
              +36.7% back to that origin: 1/(1 - 0.268) = 1.367. The
              26.8 is DERIVED from Joe's 36.7 — nothing fitted.
  COMPRESSION the spring loads: at the trough the field goes quiet —
              trailing 5-bar median |move| below the trailing W=20
              median (kernel-native negative-space contraction).
  RELEASE     ignition: the fine(8-rung) up-flip while the coarse(16)
              structure is still marked down.

  FIND        all three facts standing at once. Target = +36.7% from
              the find close (the return toward origin). Window = the
              structure's own recovery: until the coarse leg, having
              turned up, flips down again — or 250 bars (the yearly
              class scale from the definition itself).
  MIRROR      shorts: coarse rise >= +36.7% overhead, quiet stall,
              fine down-flip; target -26.8% (the give-back, same
              algebra); same window logic.

Every constant is either pinned (W=20, rungs 8/16 = the lattice ladder)
or derived from 36.7. All years evaluated identically — there is no
training window because nothing is trained. Report: finds and fidelity
PER YEAR, mean failure, the pick lists. Raw.

Usage: CH4_STORE=... python tools/ch4_uf_spring_finder.py [N]
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
LIFE_MIN, PRICE_FLOOR, MIN_BARS = 0.90, 5.0, 1250
YIELD_PCT = 36.7
DRAW_REQ = 100 * (1 - 1 / (1 + YIELD_PCT / 100))   # 26.8% — derived
HORIZON = 250
COARSE, FINE = 16, 8


def leg_walk(closes, mult):
    """Directions, flip marks, and the running origin (the extreme that
    began the current leg) — all causal."""
    n = len(closes)
    moves = np.abs(np.diff(closes))
    dirs = np.zeros(n, dtype=int)
    flips = np.zeros(n, dtype=int)
    origin = np.zeros(n)             # price where the current leg began
    direction, ext_i, org = 0, 0, closes[0]
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
            org = closes[ext_i]      # the peak: origin of the new decline
            direction, ext_i = -1, t
            flips[t] = -1
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            org = closes[ext_i]      # the trough: origin of the new rise
            direction, ext_i = 1, t
            flips[t] = 1
        dirs[t] = direction
        origin[t] = org
    return dirs, flips, origin


def find_symbol(dates, closes):
    n = len(closes)
    moves = np.abs(np.diff(closes))
    dirs_c, flips_c, origin_c = leg_walk(closes, COARSE)
    dirs_f, flips_f, _ = leg_walk(closes, FINE)
    finds = []
    open_f = None
    for t in range(1, n):
        if open_f is not None:
            side = open_f["side"]
            open_f["age"] += 1
            if side == 1 and closes[t] >= open_f["tgt"]:
                open_f.update(out=dates[t], outcome="COMPLETE", ret=YIELD_PCT)
                finds.append(open_f); open_f = None
            elif side == -1 and closes[t] <= open_f["tgt"]:
                open_f.update(out=dates[t], outcome="COMPLETE",
                              ret=round(DRAW_REQ, 2))
                finds.append(open_f); open_f = None
            else:
                if not open_f["turned"] and dirs_c[t] == side:
                    open_f["turned"] = True
                ended = (open_f["turned"] and flips_c[t] == -side) \
                    or open_f["age"] >= HORIZON
                if ended:
                    raw = 100 * (closes[t] / open_f["px"] - 1.0)
                    open_f.update(out=dates[t], outcome="FAIL",
                                  ret=round(raw if side == 1 else -raw, 3))
                    finds.append(open_f); open_f = None
        if open_f is None and closes[t] >= PRICE_FLOOR and flips_f[t] != 0:
            side = int(flips_f[t])
            if dirs_c[t] != -side:
                continue                    # the coarse structure must still be against
            org = origin_c[t]
            if org <= 0:
                continue
            if side == 1:
                draw = 100 * (1 - closes[t] / org)
                energy_ok = draw >= DRAW_REQ
            else:
                rise = 100 * (org and (org / closes[t] - 1) or 0) if closes[t] > 0 else 0
                rise = 100 * (org / closes[t] - 1) if closes[t] > 0 else 0
                energy_ok = rise >= YIELD_PCT
            if not energy_ok:
                continue
            w0 = max(1, t - 5)
            w1 = max(1, t - W)
            q_now = float(np.median(moves[w0 - 1:t]))
            q_ref = float(np.median(moves[w1 - 1:t]))
            if not (q_now < q_ref):
                continue                    # spring not loaded
            tgt = closes[t] * (1 + YIELD_PCT / 100.0) if side == 1 \
                else closes[t] * (1 - DRAW_REQ / 100.0)
            open_f = {"symbol": None, "in": dates[t], "px": closes[t],
                      "side": side, "tgt": tgt, "turned": False, "age": 0,
                      "draw_pct": round(draw if side == 1 else rise, 1)}
    return finds


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)} | derived drawdown requirement: {DRAW_REQ:.1f}%")

    all_finds = []
    t0 = time.time()
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        try:
            fs = find_symbol(dates, closes)
        except Exception:
            continue
        for f_ in fs:
            f_["symbol"] = sym
            f_.pop("tgt", None)
        all_finds.extend(fs)
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(uni)}] finds={len(all_finds)} "
                  f"{time.time()-t0:.0f}s", flush=True)

    def table(sel):
        if not sel:
            return {"finds": 0}
        c = sum(1 for f in sel if f["outcome"] == "COMPLETE")
        fails = [f["ret"] for f in sel if f["outcome"] == "FAIL"]
        byy = defaultdict(lambda: [0, 0, []])
        for f in sel:
            y = f["in"][:4]
            byy[y][0] += 1 if f["outcome"] == "COMPLETE" else 0
            byy[y][1] += 1
            if f["outcome"] == "FAIL":
                byy[y][2].append(f["ret"])
        return {"finds": len(sel),
                "fidelity_pct": round(100 * c / len(sel), 2),
                "mean_fail_pct": round(float(np.mean(fails)), 2) if fails else None,
                "by_year": {y: {"finds": v[1],
                                "fidelity_pct": round(100 * v[0] / v[1], 1),
                                "mean_fail": round(float(np.mean(v[2])), 1) if v[2] else None}
                            for y, v in sorted(byy.items())}}

    result = {
        "frame": "deterministic spring: energy(decline>=26.8 derived) + "
                 "compression + release; target = return to origin",
        "all": table(all_finds),
        "longs": table([f for f in all_finds if f["side"] == 1]),
        "shorts": table([f for f in all_finds if f["side"] == -1]),
    }
    path = os.path.join(OUT_DIR, "ch4_uf_spring_finder.json")
    with open(path, "w") as f:
        json.dump({**result, "detail": all_finds[:100000]}, f, indent=1, default=str)
    print(json.dumps(result, indent=1, default=str))
    print("filed:", path)


if __name__ == "__main__":
    main()
