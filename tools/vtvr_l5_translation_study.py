"""
vtvr_l5_translation_study.py
=============================

NON-CANONICAL — L5-style translation over the frozen side kernel's states.

Mandate (Joe, 2026-07-28): free play over the un-flattened physics outputs
and combinations, INCLUDING L5 decision logic. Kernel untouched.

Takes the holdout-surviving states from the structure search and asks the
questions an L5 layer would ask before acting on them:

  Q1  HORIZON — does the edge extend to the CH2-length hold (90 bars)?
  Q2  MEADOW  — does the FIELD's own regime (herd coherence / herd
      breathing at entry) change the state's odds? (horse/herd/meadow)
  Q3  ENSEMBLE — union of surviving laggard states: coverage vs quality.
  Q4  DEPTH   — within the star state, does the MOST coherent laggard
      (rank-1 by 30-bar coherence) beat the rest of the state?

All evaluated on the same 30-ticker, ~1500-day joint field with the same
70/30 search/holdout date split as the structure search; holdout numbers
are the ones that matter.

Usage: python tools/vtvr_l5_translation_study.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import (  # noqa: E402
    build_field,
    per_step_arrays,
    window_desc,
    W_LONG,
    W_SHORT,
    SEARCH_FRACTION,
    _mean,
)

HORIZONS = (20, 60, 90)


def thirds(descs, key, n):
    order = sorted(range(n), key=lambda i: descs[i][key])
    return {i: ("LO", "MID", "HI")[min(2, (p * 3) // n)]
            for p, i in enumerate(order)}


def main():
    symbols, common, field, px = build_field()
    arrs = per_step_arrays(symbols, field)
    n, m_total = arrs["n"], arrs["m"]

    max_h = max(HORIZONS)
    eval_dates = list(range(W_LONG, m_total - max_h))
    n_search = int(len(eval_dates) * SEARCH_FRACTION)
    holdout_start = eval_dates[n_search]
    print(f"Eval dates: {len(eval_dates)} | holdout from {common[holdout_start][:10]}")

    fcoh_cut = sorted(arrs["fcoh"][d] for d in eval_dates[:n_search])
    fbrth_cut = sorted(arrs["fbrth"][d] for d in eval_dates[:n_search])

    def fband(val, cuts):
        t1, t2 = cuts[len(cuts) // 3], cuts[2 * len(cuts) // 3]
        return "LO" if val <= t1 else ("MID" if val <= t2 else "HI")

    # bucket -> list of (horizon-return per horizon dict, in_holdout)
    star_rows, star_field, ens_rows, depth_rows = [], [], [], []

    for m in eval_dates:
        dl = window_desc(arrs, m, W_LONG)
        ds = window_desc(arrs, m, W_SHORT)
        brth_l = thirds(dl, "BRTH", n)
        coh_s = thirds(ds, "COH", n)
        ltrnd_l = thirds(dl, "LTRND", n)
        rev_l = thirds(dl, "REV", n)
        brth_s = thirds(ds, "BRTH", n)

        star = [i for i in range(n)
                if brth_l[i] == "MID" and coh_s[i] == "HI" and ltrnd_l[i] == "LO"]
        smooth = [i for i in range(n)
                  if ltrnd_l[i] == "LO" and rev_l[i] == "LO" and brth_s[i] == "LO"]
        ens = sorted(set(star) | set(smooth))

        hold = m >= holdout_start
        f_regime = (fband(arrs["fcoh"][m], fcoh_cut),
                    fband(arrs["fbrth"][m], fbrth_cut))

        def fwd(i):
            return {h: (px[m + h][i] - px[m][i]) / px[m][i] for h in HORIZONS}

        for i in star:
            star_rows.append((fwd(i), hold))
            star_field.append((fwd(i), hold, f_regime))
        for i in ens:
            ens_rows.append((fwd(i), hold))
        if star:
            deepest = max(star, key=lambda i: ds[i]["COH"])
            depth_rows.append((fwd(deepest), hold))

    def report(name, rows, hold_only=True):
        sel = [r for r in rows if (r[1] if hold_only else True)]
        if not sel:
            print(f"  {name:<44} (no holdout observations)")
            return
        for h in HORIZONS:
            xs = [r[0][h] for r in sel]
            wr = _mean([1.0 if x > 0 else 0.0 for x in xs]) * 100
            print(f"  {name:<44} +{h:<3} N={len(xs):<5} "
                  f"WR={wr:5.1f}%  mean={_mean(xs)*100:+6.2f}%")

    print()
    print("Q1 — HORIZON (holdout only)")
    report("coherent_laggard (star)", star_rows)
    print()
    print("Q2 — MEADOW: star state by field regime at entry (holdout only)")
    for coh_band in ("LO", "MID", "HI"):
        rows = [(f, h) for f, h, (fc, _) in star_field if fc == coh_band]
        report(f"star | field coherence {coh_band}", rows)
    for br_band in ("LO", "MID", "HI"):
        rows = [(f, h) for f, h, (_, fb) in star_field if fb == br_band]
        report(f"star | field breathing {br_band}", rows)
    print()
    print("Q3 — ENSEMBLE: star ∪ smooth_laggard (holdout only)")
    report("ensemble", ens_rows)
    print()
    print("Q4 — DEPTH: most-coherent member of star per date (holdout only)")
    report("deepest coherent laggard", depth_rows)

    # Universe baseline
    base = []
    for m in eval_dates[n_search:]:
        for i in range(n):
            base.append(({h: (px[m + h][i] - px[m][i]) / px[m][i]
                          for h in HORIZONS}, True))
    print()
    report("UNIVERSE BASELINE", base)


if __name__ == "__main__":
    main()
