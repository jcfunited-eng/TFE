"""
ch4_uf_class_finder.py — whole-portrait recognition of the big-riser class
==========================================================================

Joe's class (2026-07-31): stocks that rise ~36.7%+ inside a year — they
are abundant, they all have structures, and DSF-AI finds them by their
INDICATIONS. This tool does that literally, with the full kernel
portrait and majority co-occurrence — no single signal anywhere.

PIPELINE (declared):
  CLASS       — ground truth per stock: every trough from which the
                close rises >= 36.7% within the next 250 bars (the
                in-year rise class; abundant). PRE-RISE window = the W
                bars before the trough. Mirror class for fallers.
  PORTRAIT    — per bar, the kernel's full state tuple: D sign, URF>0,
                regime, F_n band, S_UF band (trailing 25/75), gate
                species class, compression flag (5-bar median move below
                trailing-W median), coarse(16) leg direction, fine(8)
                leg direction. Nine dimensions, all causal.
  INDICATIONS — training years (2016-2020) ONLY: for each dimension,
                the value(s) whose share in pre-rise windows exceeds
                its baseline share (lift > 1) with support >= 1000 bars.
                One indication per dimension (the top-lift value).
  FIND        — evaluation years (2021+): a stock-day where a MAJORITY
                (>= 5 of 9) of indications hold, the coarse leg is
                still down (early), and no live find is open for the
                stock. Outcome: +36.7% from the flag close within 250
                bars (class definition). Mirror for shorts.
  REPORT      — per year: finds, fidelity, mean shortfall of failures;
                indication list filed. Raw. Majority = the only
                combining rule; no thresholds tuned.

Usage: CH4_STORE=... python tools/ch4_uf_class_finder.py [N]
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict, Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_kernel_v2 import replay_symbol_v2  # noqa: E402
from tools.ch4_uf_spectrum import gate_stream, life_fraction, W  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN, PRICE_FLOOR, MIN_BARS = 0.90, 5.0, 1250
YIELD_PCT = 36.7
HORIZON = 250
SPLIT = "2021-01-01"
MAJORITY = 5


def leg_dirs(closes, mult):
    n = len(closes)
    moves = np.abs(np.diff(closes))
    out = np.zeros(n, dtype=int)
    direction, ext_i = 0, 0
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
            direction, ext_i = -1, t
        elif direction == -1 and closes[t] - closes[ext_i] > thresh:
            direction, ext_i = 1, t
        out[t] = direction
    return out


def portrait_arrays(sym, dates, closes, vols):
    """Per-bar 9-dimension portrait, all causal."""
    n = len(closes)
    states = replay_symbol_v2(dates, closes, vols, warmup=60)
    gs = gate_stream(dates, closes, vols)
    cls_of = [None] * n
    for (d_end, cls, disp, ta, tb) in gs:
        for t in range(ta, min(tb, n)):
            cls_of[t] = cls[0][2]      # coarsest-lattice signature (compact)
    fn = np.array([s.F_n if s else np.nan for s in states])
    suf = np.array([s.S_UF if s else np.nan for s in states])
    moves = np.abs(np.diff(closes))
    coarse = leg_dirs(closes, 16)
    fine = leg_dirs(closes, 8)

    def band(series, t):
        w0 = max(0, t - W)
        win = series[w0:t]
        win = win[np.isfinite(win)]
        if len(win) < W // 2 or not np.isfinite(series[t]):
            return "?"
        lo, hi = np.percentile(win, 25), np.percentile(win, 75)
        return "L" if series[t] <= lo else ("H" if series[t] >= hi else "M")

    P = []
    for t in range(n):
        s = states[t]
        if s is None:
            P.append(None)
            continue
        w0 = max(1, t - 5)
        w1 = max(1, t - W)
        q_now = float(np.median(moves[w0 - 1:t])) if t > 1 else 0.0
        q_ref = float(np.median(moves[w1 - 1:t])) if t > 1 else 1.0
        P.append({
            "D": int(np.sign(s.D_k)),
            "URF": int(s.URF > 0),
            "REG": s.regime[:4],
            "FN": band(fn, t),
            "SUF": band(suf, t),
            "SPC": cls_of[t] if cls_of[t] is not None else "?",
            "CMP": int(q_now < q_ref),
            "CRS": int(coarse[t]),
            "FIN": int(fine[t]),
        })
    return P


DIMS = ("D", "URF", "REG", "FN", "SUF", "SPC", "CMP", "CRS", "FIN")


def class_troughs(closes, dates):
    """All bars t that begin a >= YIELD_PCT rise within HORIZON bars
    (ground truth; hindsight — used on training years only for the
    census, and as evaluation labels)."""
    n = len(closes)
    out = np.zeros(n, dtype=bool)
    # forward max via reverse scan windows
    for t in range(n - 5):
        hi = np.max(closes[t + 1: min(n, t + 1 + HORIZON)])
        if closes[t] > 0 and hi / closes[t] - 1.0 >= YIELD_PCT / 100.0:
            out[t] = True
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)}")

    # ---- pass 1: indication census on training years
    pre_counts = {d: Counter() for d in DIMS}
    base_counts = {d: Counter() for d in DIMS}
    frames = {}
    t0 = time.time()
    class_per_year = Counter()
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        try:
            P = portrait_arrays(sym, dates, closes, vols)
        except Exception:
            continue
        troughs = class_troughs(closes, dates)
        frames[sym] = (dates, closes, P)
        for t in range(len(closes)):
            if P[t] is None or closes[t] < PRICE_FLOOR:
                continue
            if troughs[t]:
                class_per_year[dates[t][:4]] += 1
            if dates[t] >= SPLIT:
                continue
            for d in DIMS:
                base_counts[d][P[t][d]] += 1
            if troughs[t]:
                for dt in range(max(0, t - W), t + 1):
                    if P[dt] is not None:
                        for d in DIMS:
                            pre_counts[d][P[dt][d]] += 1
        if (i + 1) % 500 == 0:
            print(f"  pass1 [{i+1}/{len(uni)}] {time.time()-t0:.0f}s", flush=True)

    indications = {}
    for d in DIMS:
        tot_pre = sum(pre_counts[d].values()) or 1
        tot_base = sum(base_counts[d].values()) or 1
        best, best_lift = None, 0.0
        for v, c in pre_counts[d].items():
            if c < 1000:
                continue
            lift = (c / tot_pre) / max(base_counts[d][v] / tot_base, 1e-9)
            if lift > best_lift:
                best, best_lift = v, lift
        indications[d] = {"value": best, "lift": round(best_lift, 3)}
    print("indications:", json.dumps({k: v for k, v in indications.items()}, default=str))

    # ---- pass 2: majority-co-occurrence finder on evaluation years
    finds = []
    for sym, (dates, closes, P) in frames.items():
        n = len(closes)
        live_until = -1
        for t in range(n):
            if dates[t] < SPLIT or P[t] is None or closes[t] < PRICE_FLOOR:
                continue
            if t <= live_until:
                continue
            hits = sum(1 for d in DIMS
                       if indications[d]["value"] is not None
                       and P[t][d] == indications[d]["value"])
            if hits >= MAJORITY and P[t]["CRS"] == -1:
                hi = np.max(closes[t + 1: min(n, t + 1 + HORIZON)]) if t + 1 < n else 0
                complete = closes[t] > 0 and hi / closes[t] - 1.0 >= YIELD_PCT / 100.0
                end_i = min(n - 1, t + HORIZON)
                ret = YIELD_PCT if complete else 100 * (closes[end_i] / closes[t] - 1.0)
                finds.append({"symbol": sym, "in": dates[t], "hits": hits,
                              "outcome": "COMPLETE" if complete else "FAIL",
                              "ret_pct": round(float(ret), 2)})
                live_until = t + HORIZON if not complete else t + 20
    byy = defaultdict(lambda: [0, 0, []])
    for f in finds:
        y = f["in"][:4]
        byy[y][0] += 1 if f["outcome"] == "COMPLETE" else 0
        byy[y][1] += 1
        if f["outcome"] == "FAIL":
            byy[y][2].append(f["ret_pct"])
    comp = sum(1 for f in finds if f["outcome"] == "COMPLETE")
    result = {
        "class_size_per_year (trough-days of >=36.7% rises)": dict(sorted(class_per_year.items())),
        "indications": {k: v for k, v in indications.items()},
        "finds": len(finds),
        "fidelity_pct": round(100 * comp / len(finds), 2) if finds else None,
        "by_year": {y: {"finds": v[1],
                        "fidelity_pct": round(100 * v[0] / v[1], 1) if v[1] else None,
                        "mean_fail_ret_pct": round(float(np.mean(v[2])), 1) if v[2] else None}
                    for y, v in sorted(byy.items())},
    }
    path = os.path.join(OUT_DIR, "ch4_uf_class_finder.json")
    with open(path, "w") as f:
        json.dump({**result, "finds_detail": finds[:100000]}, f, indent=1, default=str)
    print(json.dumps(result, indent=1, default=str))
    print("filed:", path)


if __name__ == "__main__":
    main()
