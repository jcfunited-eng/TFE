"""
ch4_uf_find37_pure.py — EARLY finder: fine detection inside coarse potential
=================================================================

The find IS the structure: at the coarse rung (REV_MULT=16, the pinned
constant doubled twice), an up-flip out of a confirmed decline is a find
(mirror for shorts). Completion = the +/-36.7% touch from the find close
before the SAME coarse structure's next flip. No per-stock statistics,
no propensity — the field's own completion rate at the scale where
36.7% moves live. Context columns measured (not selected): whether the
finer rungs (8, 4) agree at find time, and whether the decline ended in
compression (last-5-bar median move below the trailing-W median — quiet
tail). Per-year everything. Raw.
"""
from __future__ import annotations
import json, os, sys, time
from collections import defaultdict
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.ch4_uf_spectrum import life_fraction, W

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN, PRICE_FLOOR, MIN_BARS = 0.90, 5.0, 1250
COARSE, FINE = 16, (8, 4)
YIELD_PCT = 36.7


def leg_dirs(closes, mult, W_=W):
    n = len(closes)
    moves = np.abs(np.diff(closes))
    out = np.zeros(n, dtype=int)
    flips = np.zeros(n, dtype=int)   # +1/-1 at flip bars
    direction, ext_i = 0, 0
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
            direction, ext_i = -1, t
            flips[t] = -1
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            direction, ext_i = 1, t
            flips[t] = 1
        out[t] = direction
    return out, flips


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)}")

    finds = []
    t0 = time.time()
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        dirs_c, flips_c = leg_dirs(closes, COARSE)
        moves = np.abs(np.diff(closes))
        n = len(closes)
        fine8_dirs, fine8_flips = leg_dirs(closes, 8)
        fine4_dirs, fine4_flips = leg_dirs(closes, 4)
        open_f = None
        for t in range(1, n):
            if open_f is not None:
                side = open_f["side"]
                if side == 1 and closes[t] >= open_f["tgt"]:
                    open_f.update(out=dates[t], outcome="COMPLETE", ret=YIELD_PCT)
                    finds.append(open_f); open_f = None
                elif side == -1 and closes[t] <= open_f["tgt"]:
                    open_f.update(out=dates[t], outcome="COMPLETE", ret=YIELD_PCT)
                    finds.append(open_f); open_f = None
                else:
                    # STOCK-LEVEL WINDOW: the find lives until the coarse
                    # structure, having turned with it, flips against it —
                    # or 250 bars pass. Fine-scale churn never kills the
                    # find (that is harvest mechanics, not detection).
                    open_f["age"] = open_f.get("age", 0) + 1
                    if not open_f["coarse_turned"] and dirs_c[t] == side:
                        open_f["coarse_turned"] = True
                    ended = (open_f["coarse_turned"] and flips_c[t] == -side) or \
                            open_f["age"] >= 250
                    if ended:
                        raw = 100 * (closes[t] / open_f["px"] - 1.0)
                        open_f.update(out=dates[t], outcome="FAIL",
                                      ret=round(raw if side == 1 else -raw, 3))
                        finds.append(open_f); open_f = None
            # THE EARLY FIND: fine(8) flip while the coarse structure is
            # still on the OTHER side — the birth at the coarse trough
            if open_f is None and closes[t] >= PRICE_FLOOR and fine8_flips[t] != 0:
                side = int(fine8_flips[t])
                if dirs_c[t] == -side:      # coarse still declining (or rising, mirror)
                    w0 = max(1, t - 5)
                    q_now = float(np.median(moves[w0 - 1:t]))
                    w1 = max(1, t - W)
                    q_ref = float(np.median(moves[w1 - 1:t]))
                    compressed = int(q_now < q_ref)
                    agree = int(fine4_dirs[t] == side)
                    tgt = closes[t] * (1 + YIELD_PCT / 100.0) if side == 1 \
                        else closes[t] * (1 - YIELD_PCT / 100.0)
                    open_f = {"symbol": sym, "in": dates[t], "px": closes[t],
                              "side": side, "tgt": tgt, "compressed": compressed,
                              "fine_agree": agree, "coarse_turned": False}
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(uni)}] finds={len(finds)} {time.time()-t0:.0f}s",
                  flush=True)

    def table(sel):
        if not sel:
            return {"finds": 0}
        c = sum(1 for f in sel if f["outcome"] == "COMPLETE")
        byy = defaultdict(lambda: [0, 0])
        fails = [f["ret"] for f in sel if f["outcome"] == "FAIL"]
        for f in sel:
            y = f["in"][:4]
            byy[y][0] += 1 if f["outcome"] == "COMPLETE" else 0
            byy[y][1] += 1
        return {"finds": len(sel),
                "fidelity_pct": round(100 * c / len(sel), 2),
                "mean_fail_pct": round(float(np.mean(fails)), 2) if fails else None,
                "by_year": {y: f"{v[0]}/{v[1]}={100*v[0]/v[1]:.0f}%"
                            for y, v in sorted(byy.items())}}

    closed = [f for f in finds if "outcome" in f]
    result = {
        "frame": "EARLY finder — fine(8) birth inside coarse(16) decline; window = the coarse rise lifetime",
        "all": table(closed),
        "longs": table([f for f in closed if f["side"] == 1]),
        "shorts": table([f for f in closed if f["side"] == -1]),
        "compressed_births": table([f for f in closed if f["compressed"]]),
        "fine_agree": table([f for f in closed if f["fine_agree"]]),
        "compressed_and_agree": table([f for f in closed
                                       if f["compressed"] and f["fine_agree"]]),
    }
    path = os.path.join(OUT_DIR, "ch4_uf_find37_pure.json")
    with open(path, "w") as f:
        json.dump({**result, "detail": closed[:100000]}, f, indent=1, default=str)
    print(json.dumps(result, indent=1)[:3000])
    print("filed:", path)


if __name__ == "__main__":
    main()
