"""
ch4_uf_arc_morphology.py — the geometry verdict on the conformant kernel
========================================================================

Joe's criterion (2026-07-30): a correct kernel exposes causal temporal
geometries with positive-trend harvesting targets, and their CYCLE
MORPHOLOGY (build → peak → collapse vector); a failed kernel shows quant
noise (~51%±3%, ~3%±2%). This is the direct measurement, from the filed
v2 state matrices, of whether the kernel's own admitted structure carves
forward yield — BEFORE any trade rule:

  ARC       — a maximal run of days with URF > 0 (admitted resonance) on
              an eligible (LIFE ≥ 0.90), $5-floor vertex.
  Measures  — (1) mean daily close-to-close forward return INSIDE arcs
              vs OUTSIDE arcs vs baseline (the field-level yield split);
              (2) the same split conditioned on the arc's D state
              (building vs decaying phase);
              (3) the average arc yield path in normalized phase
              (cycle morphology: does build→peak→collapse exist?);
              (4) post-extinction drawdown (the collapse vector's
              forward validity) vs matched baseline;
              (5) arc duration / per-arc total-return distributions.

No thresholds, no trade rule, no tuning — a pure geometry audit. If (1)
and (2) show no separation, the kernel realization is wrong per the
stated criterion, and that verdict gets filed.

Usage: python tools/ch4_uf_arc_morphology.py artifacts/ch4_uf/v2_states_universe5016.npz
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "artifacts", "ch4_uf")
COL_R, COL_URF, COL_IGN, COL_EXT, COL_FN, COL_SUF, COL_D, COL_CLOSE = range(8)
LIFE_MIN = 0.90
PRICE_FLOOR = 5.0
PHASE_BINS = 10


def life_fraction(closes):
    n = len(closes)
    moved = np.zeros(n)
    if n > 1:
        moved[1:] = (np.abs(np.diff(closes)) > 0).astype(float)
    return np.cumsum(moved) / np.maximum(np.arange(n), 1)


def main():
    npz = sys.argv[1]
    z = np.load(npz, allow_pickle=False)
    syms = sorted({k[:-7] for k in z.files if k.endswith("__dates")})

    in_arc, out_arc, all_ret = [], [], []
    in_arc_up, in_arc_dn = [], []          # D=+1 vs D=-1 inside arcs
    phase_sum = np.zeros(PHASE_BINS)
    phase_cnt = np.zeros(PHASE_BINS)
    arc_lens, arc_rets = [], []
    post_ext_5, post_ext_20 = [], []
    base_5, base_20 = [], []

    for si, s in enumerate(syms):
        mat = z[f"{s}__mat"]
        closes = mat[:, COL_CLOSE].astype(float)
        n = len(closes)
        if n < 100:
            continue
        lf = life_fraction(closes)
        fwd1 = np.full(n, np.nan)
        fwd1[:-1] = closes[1:] / closes[:-1] - 1.0

        urf = mat[:, COL_URF]
        d_k = mat[:, COL_D]
        ext = mat[:, COL_EXT]
        valid = np.isfinite(urf) & (lf >= LIFE_MIN) & (closes >= PRICE_FLOOR)

        # arcs: maximal URF>0 runs over valid region
        t = 0
        while t < n - 1:
            if not (valid[t] and urf[t] > 0):
                if valid[t] and np.isfinite(fwd1[t]):
                    out_arc.append(fwd1[t])
                    all_ret.append(fwd1[t])
                t += 1
                continue
            a = t
            while t < n and valid[t] and np.isfinite(urf[t]) and urf[t] > 0:
                t += 1
            b = t  # arc = [a, b)
            L = b - a
            arc_lens.append(L)
            if closes[a] > 0 and b - 1 < n:
                arc_rets.append(float(closes[b - 1] / closes[a] - 1.0))
            for u in range(a, min(b, n - 1)):
                r = fwd1[u]
                if not np.isfinite(r):
                    continue
                in_arc.append(r)
                all_ret.append(r)
                if d_k[u] == 1:
                    in_arc_up.append(r)
                elif d_k[u] == -1:
                    in_arc_dn.append(r)
                if L > 1:
                    ph = min(PHASE_BINS - 1, int(PHASE_BINS * (u - a) / L))
                    phase_sum[ph] += r
                    phase_cnt[ph] += 1

        # collapse vector: post-extinction forward vs baseline
        for t2 in range(n - 20):
            if not (valid[t2] and np.isfinite(closes[t2 + 20])):
                continue
            r5 = closes[t2 + 5] / closes[t2] - 1.0 if t2 + 5 < n else np.nan
            r20 = closes[t2 + 20] / closes[t2] - 1.0
            if ext[t2] == 1.0:
                if np.isfinite(r5):
                    post_ext_5.append(r5)
                post_ext_20.append(r20)
            elif t2 % 7 == 0:   # deterministic baseline thinning
                if np.isfinite(r5):
                    base_5.append(r5)
                base_20.append(r20)

        if (si + 1) % 1000 == 0:
            print(f"  [{si+1}/{len(syms)}]", flush=True)

    def stats(a):
        a = np.array(a)
        a = a[np.isfinite(a)]
        if not len(a):
            return {}
        return {"n": int(len(a)),
                "mean_bp_day": round(1e4 * float(a.mean()), 2),
                "wr_pct": round(100 * float((a > 0).mean()), 2),
                "ann_pct": round(100 * (float((1 + a.mean()) ** 252) - 1), 1)}

    def stats_h(a):
        a = np.array(a)
        a = a[np.isfinite(a)]
        if not len(a):
            return {}
        return {"n": int(len(a)),
                "wr_pct": round(100 * float((a > 0).mean()), 2),
                "mean_pct": round(100 * float(a.mean()), 3)}

    phase_path = [round(1e4 * float(phase_sum[i] / phase_cnt[i]), 2)
                  if phase_cnt[i] else None for i in range(PHASE_BINS)]

    result = {
        "verdict_inputs": {
            "in_arc_daily": stats(in_arc),
            "out_arc_daily": stats(out_arc),
            "baseline_daily": stats(all_ret),
            "in_arc_D_plus": stats(in_arc_up),
            "in_arc_D_minus": stats(in_arc_dn),
        },
        "cycle_morphology_phase_bp_per_day": phase_path,
        "arc_length": {"n": len(arc_lens),
                       "median": float(np.median(arc_lens)) if arc_lens else None,
                       "p90": float(np.percentile(arc_lens, 90)) if arc_lens else None},
        "arc_total_return": stats_h(arc_rets),
        "collapse_vector": {
            "post_extinction_h5": stats_h(post_ext_5),
            "post_extinction_h20": stats_h(post_ext_20),
            "baseline_h5": stats_h(base_5),
            "baseline_h20": stats_h(base_20),
        },
    }
    out = os.path.join(OUT_DIR, "ch4_uf_arc_morphology.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    print("filed:", out)


if __name__ == "__main__":
    main()
