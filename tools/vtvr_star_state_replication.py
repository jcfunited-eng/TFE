"""
vtvr_star_state_replication.py
===============================

NON-CANONICAL — replication of the frozen star state on a virgin universe.

The structure search (cohort A: 30 tickers, 2020-2026) surfaced and
holdout-verified the state:

    COHERENT LAGGARD  =  BRTH.L:MID  &  COH.S:HI  &  LTRND.L:LO
    (moderate 120-bar breathing, top-third 30-bar herd coherence,
     bottom-third 120-bar leadership trend)

    Cohort A holdout: WR@60 78.0%, WR@90 82.7% (+10.5%);
    in LO field-coherence meadows: WR@90 88.9% (+12.4%).

This script tests the SAME frozen definition on COHORT B — 30 tickers
sharing no member with cohort A — over the full available history. Every
cohort-B stock-date is out-of-sample by construction: the state was
defined before this universe was ever dimensionalized.

Also reports the L5 meadow conditioning (field-coherence thirds, cut
points from cohort B's own first 70% of dates to avoid look-ahead).

Usage: python tools/vtvr_star_state_replication.py
"""

from __future__ import annotations

import os
import sys

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

COHORT_B = [
    "ADBE", "CRM", "ORCL", "INTC", "AMD", "QCOM", "TXN", "MU", "CSCO", "IBM",
    "GS", "MS", "WFC", "C", "BLK", "SPGI", "AXP", "V", "MA", "T",
    "VZ", "DIS", "NKE", "MCD", "SBUX", "LOW", "TGT", "COST", "UNP", "HON",
]
HORIZONS = (20, 60, 90)


def thirds(descs, key, n):
    order = sorted(range(n), key=lambda i: descs[i][key])
    return {i: ("LO", "MID", "HI")[min(2, (p * 3) // n)]
            for p, i in enumerate(order)}


def main():
    overlap = set(COHORT_B) & set(wf.UNIVERSE)
    assert not overlap, f"cohort overlap: {overlap}"

    symbols, common, field, px = build_field(COHORT_B)
    assert set(symbols) <= set(COHORT_B), "universe plumbing broken"
    arrs = per_step_arrays(symbols, field)
    n, m_total = arrs["n"], arrs["m"]

    max_h = max(HORIZONS)
    eval_dates = list(range(W_LONG, m_total - max_h))
    print(f"Cohort B eval dates: {len(eval_dates)} "
          f"({common[eval_dates[0]][:10]} .. {common[eval_dates[-1]][:10]})")

    cut_src = eval_dates[:int(len(eval_dates) * 0.7)]
    fcoh_cut = sorted(arrs["fcoh"][d] for d in cut_src)

    def fband(val):
        t1 = fcoh_cut[len(fcoh_cut) // 3]
        t2 = fcoh_cut[2 * len(fcoh_cut) // 3]
        return "LO" if val <= t1 else ("MID" if val <= t2 else "HI")

    star_rows = []
    for m in eval_dates:
        dl = window_desc(arrs, m, W_LONG)
        ds = window_desc(arrs, m, W_SHORT)
        brth_l = thirds(dl, "BRTH", n)
        coh_s = thirds(ds, "COH", n)
        ltrnd_l = thirds(dl, "LTRND", n)
        members = [i for i in range(n)
                   if brth_l[i] == "MID" and coh_s[i] == "HI"
                   and ltrnd_l[i] == "LO"]
        regime = fband(arrs["fcoh"][m])
        for i in members:
            star_rows.append((
                {h: (px[m + h][i] - px[m][i]) / px[m][i] for h in HORIZONS},
                regime,
            ))

    def report(name, rows):
        if not rows:
            print(f"  {name:<40} (no observations)")
            return
        for h in HORIZONS:
            xs = [r[0][h] for r in rows]
            wr = _mean([1.0 if x > 0 else 0.0 for x in xs]) * 100
            print(f"  {name:<40} +{h:<3} N={len(xs):<6} "
                  f"WR={wr:5.1f}%  mean={_mean(xs)*100:+6.2f}%")

    print()
    print("COHERENT LAGGARD on virgin cohort B (all dates out-of-sample):")
    report("star state", star_rows)
    print()
    for band in ("LO", "MID", "HI"):
        rows = [r for r in star_rows if r[1] == band]
        report(f"star | field coherence {band}", rows)

    base = []
    for m in eval_dates:
        for i in range(n):
            base.append(({h: (px[m + h][i] - px[m][i]) / px[m][i]
                          for h in HORIZONS}, None))
    print()
    report("COHORT B UNIVERSE BASELINE", base)


if __name__ == "__main__":
    main()
