"""
ch4_uf_birth_harvest.py — harvest census-recognized birth species, time-split
=============================================================================

Closing Joe's loop: reverse-engineered structures (census v2) → live
recognition → harvest. Honesty protocol (declared):

  SELECTION WINDOW  2016-01-01 .. 2020-12-31 — census asymmetries are
                    computed HERE ONLY (rise-birth vs fall-birth species
                    occupancy, bigram vocabulary, self-scaled zigzag).
  SPECIES SET       every bigram species with n >= 100 in selection-
                    window birth phases and asymmetry >= 4 (rise side
                    and, mirrored, fall side). 4 = coarsest pinned
                    lattice constant; no other constant exists to cite
                    and the census tail runs 6-12, so 4 is inclusive,
                    not curve-fit. The set is FROZEN before evaluation.
  EVALUATION        2021-01-01 .. store end, strictly causal: when a
                    frozen rise-birth species completes (its second
                    gate's end bar), enter long at that close; exit at
                    the FIRST completion of any frozen fall-birth
                    species on that symbol, or at the symbol's zigzag
                    reversal... zigzag needs the future — NOT usable
                    causally; exits are therefore: first frozen
                    fall-birth species completion, or the ordinary
                    collapse call (established DOWN-majority
                    prediction) whichever first — both causal.
  MEASUREMENT       per-trade WR / returns / per-year; declared field
                    book (risk-parity 1% on the species' adverse bound
                    where known, else 2%).

Everything raw; the frozen set is filed with the result.

Usage: CH4_STORE=... python tools/ch4_uf_birth_harvest.py [N]
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

from tools.ch4_uf_spectrum import gate_stream, life_fraction, W  # noqa: E402
from tools.ch4_uf_reverse_census import zigzag, PHASE_LEN  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.environ.get("CH4_STORE") or os.path.join(ROOT, "quarantine_12k_universe_ext.parquet")
OUT_DIR = os.path.join(ROOT, "artifacts", "ch4_uf")
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
MIN_BARS = 1250
SPLIT = "2021-01-01"
MIN_N = 100
MIN_ASYM = 4.0


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10 ** 9
    df = pd.read_parquet(PARQUET, columns=["Date", "Symbol", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    g = df.groupby("Symbol")["Close"]
    stats = pd.DataFrame({"bars": g.size(), "med": g.median()})
    uni = sorted(stats[(stats["bars"] >= MIN_BARS)
                       & (stats["med"] >= PRICE_FLOOR)].index.tolist())[:limit]
    print(f"universe: {len(uni)}")

    # ---- pass 1: SELECTION census on the first window only
    rise_birth = defaultdict(int)
    fall_birth = defaultdict(int)
    frames = {}
    t0 = time.time()
    for i, sym in enumerate(uni):
        sub = df[df["Symbol"] == sym].sort_values("Date")
        dates = sub["Date"].dt.strftime("%Y-%m-%d").tolist()
        closes = sub["Close"].to_numpy(dtype=float)
        vols = sub["Volume"].to_numpy(dtype=float)
        lf = life_fraction(closes)
        if lf[-1] < LIFE_MIN:
            continue
        try:
            gs = gate_stream(dates, closes, vols)
        except Exception:
            continue
        frames[sym] = (dates, closes, vols, gs)
        bar_bigram = [None] * len(closes)
        prev_cls = None
        for (d_end, cls, disp, ta, tb) in gs:
            for t in range(ta, min(tb, len(closes))):
                if prev_cls is not None:
                    bar_bigram[t] = (prev_cls, cls)
            prev_cls = cls
        piv = zigzag(closes)
        for a, b in zip(piv[:-1], piv[1:]):
            if b <= a or closes[a] <= 0 or dates[a] >= SPLIT:
                continue
            kind = rise_birth if closes[b] > closes[a] else fall_birth
            for t in range(a, min(a + PHASE_LEN, b + 1)):
                k = bar_bigram[t]
                if k is not None and closes[t] >= PRICE_FLOOR:
                    kind[k] += 1
        if (i + 1) % 500 == 0:
            print(f"  pass1 [{i+1}/{len(uni)}] {time.time()-t0:.0f}s", flush=True)

    r_tot = max(1, sum(rise_birth.values()))
    f_tot = max(1, sum(fall_birth.values()))
    rise_set = set()
    fall_set = set()
    for k, v in rise_birth.items():
        if v >= MIN_N:
            asym = (v / r_tot) / max(fall_birth.get(k, 0) / f_tot, 1e-9)
            if asym >= MIN_ASYM:
                rise_set.add(k)
    for k, v in fall_birth.items():
        if v >= MIN_N:
            asym = (v / f_tot) / max(rise_birth.get(k, 0) / r_tot, 1e-9)
            if asym >= MIN_ASYM:
                fall_set.add(k)
    print(f"FROZEN sets: rise-birth species={len(rise_set)}, fall-birth={len(fall_set)}")

    # ---- pass 2: causal evaluation on the second window
    # collapse fallback: established DOWN-majority via the causal schema
    # store (same machinery as always), accumulated over the whole obs
    # stream in date order (warm from 2016, predictions used post-split)
    obs = []
    for sym, (dates, closes, vols, gs) in frames.items():
        for k in range(2, len(gs)):
            d_prev, cls_prev, _, _, _ = gs[k - 2]
            d_cur, cls_cur, _, ta_c, tb_c = gs[k - 1]
            d_next, cls_next, disp_next, ta_n, tb_n = gs[k]
            issue_d = dates[tb_c - 1]
            issue_px = float(closes[tb_c - 1])
            obs.append((str(d_next), (cls_prev, cls_cur), disp_next, sym,
                        issue_d, issue_px))
    obs.sort(key=lambda x: (x[0], x[3]))
    print(f"observations: {len(obs)}")

    Sp, Sn = defaultdict(int), defaultdict(int)
    open_pos = {}
    trades = []
    for d_next, sp, disp, sym, issue_d, issue_px in obs:
        p, q = Sp[sp], Sn[sp]
        n = p + q
        pred_up = p >= q if n >= W else True
        # exits first
        po = open_pos.get(sym)
        if po is not None and issue_px > 0 and issue_d > po["in"]:
            fall_hit = sp in fall_set
            collapse = (n >= W and not pred_up)
            if fall_hit or collapse:
                ret = 100 * (issue_px / po["px"] - 1.0)
                trades.append({"symbol": sym, "in": po["in"], "out": issue_d,
                               "ret_pct": round(ret, 3),
                               "reason": "FALLBIRTH" if fall_hit else "COLLAPSE"})
                open_pos.pop(sym, None)
        # entries: frozen rise-birth species completing, post-split
        if sym not in open_pos and sp in rise_set and issue_d >= SPLIT \
                and issue_px >= PRICE_FLOOR:
            open_pos[sym] = {"in": issue_d, "px": issue_px}
        if disp > 0:
            Sp[sp] += 1
        elif disp < 0:
            Sn[sp] += 1
    # force-close at last seen price per symbol
    for sym, po in open_pos.items():
        dates, closes, vols, gs = frames[sym]
        ret = 100 * (float(closes[-1]) / po["px"] - 1.0)
        trades.append({"symbol": sym, "in": po["in"], "out": dates[-1],
                       "ret_pct": round(ret, 3), "reason": "EOD"})

    rets = np.array([t["ret_pct"] for t in trades]) if trades else np.array([])
    by = defaultdict(list)
    for t in trades:
        by[t["in"][:4]].append(t["ret_pct"])
    result = {
        "frozen_sets": {"rise_birth": len(rise_set), "fall_birth": len(fall_set)},
        "selection_window": f"2016..{SPLIT} (census only)",
        "evaluation_window": f"{SPLIT}.. (causal, species frozen)",
        "trades": len(trades),
        "wr_pct": round(100 * float((rets > 0).mean()), 2) if len(rets) else None,
        "mean_pct": round(float(rets.mean()), 3) if len(rets) else None,
        "median_pct": round(float(np.median(rets)), 3) if len(rets) else None,
        "by_year": {y: {"n": len(v),
                        "wr": round(100 * float((np.array(v) > 0).mean()), 1),
                        "mean": round(float(np.mean(v)), 2)}
                    for y, v in sorted(by.items())},
        "reasons": {rn: int(sum(1 for t in trades if t["reason"] == rn))
                    for rn in ("FALLBIRTH", "COLLAPSE", "EOD")},
    }
    path = os.path.join(OUT_DIR, "ch4_uf_birth_harvest.json")
    with open(path, "w") as f:
        json.dump({**result,
                   "frozen_rise_species": [str(s) for s in sorted(map(str, rise_set))],
                   "frozen_fall_species": [str(s) for s in sorted(map(str, fall_set))],
                   "trades_detail": trades}, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", path)


if __name__ == "__main__":
    main()
