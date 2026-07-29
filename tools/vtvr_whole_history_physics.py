"""
vtvr_whole_history_physics.py
==============================

NON-CANONICAL — whole-history physics of the conserved share field.
Joe's law (2026-07-29): decisions may not be made on points in time;
the object of evaluation is the ENTIRE structure — the full physics of
the entire history. Accordingly, NO WINDOWS APPEAR IN THIS PROGRAM.
Every state quantity is an expanding integral over a vertex's whole
life, computed from the kernel's exact retained field.

WHOLE-HISTORY STATE of vertex i at time t (all integrals from bar 1):

  LIFE      fraction of its bars with real displacement (a zombie
            never qualifies; the gate_count principle, lifetime form)
  SAT       lifetime saturation: percentile of current share within
            its ENTIRE history (the raw_x_m analog — a lifetime
            integrator, not a window statistic)
  DRAIN     lifetime flow-arc position: cumulative net share-flow
            with the whole field (sum of all wedge relations over the
            entire life — the path integral of oriented area), ranked
            within its OWN lifetime arc. Low = maximally drained over
            its whole life.
  ACTION    lifetime swept volume (total structural action)

DECLARED PHYSICS HYPOTHESIS (one shot, stated before running):
  In a conserved, driven field, a vertex that is
     alive (LIFE ≥ 0.9),
     deep in lifetime saturation (SAT ≤ 0.2 of its own history),
     and at the drained extreme of its lifetime flow arc
        (DRAIN ≤ 0.2 of its own history)
  is the configuration where restored flow accumulates.
  PREDICTION (about the FIELD, not money): its structural share rises
  over the next 60-90 bars relative to the field.

MEASUREMENT: forward change in share, and forward share vs the
all-vertex baseline, at 60 and 90 bars. Both cohorts, identical frozen
definition. Only after the field-level result is L5 allowed one line
(price follows share within a group by construction).

Usage: python tools/vtvr_whole_history_physics.py [B]
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field, _mean  # noqa: E402

MIN_LIFE_BARS = 252          # a vertex must have lived a year to be judged
HORIZONS = (60, 90)


def main():
    universe = None
    label = "cohort A"
    if "GAIN" in [a.upper() for a in sys.argv[1:]]:
        label += " [GAIN mode: lifetime top-of-flow-arc, my persistence law]"
    if len(sys.argv) > 1 and sys.argv[1].upper() == "B":
        from tools.vtvr_star_state_replication import COHORT_B
        universe = COHORT_B
        label = "cohort B (virgin)"
    print(f"UNIVERSE: {label}")
    symbols, common, field, px_frac = build_field(universe)
    n, m_total = len(symbols), len(common)
    if common[-1][:10] == datetime.now(timezone.utc).strftime("%Y-%m-%d"):
        m_total -= 1

    xh = np.array([[float(v) for v in row] for row in field.xhat])[:m_total]
    dx = np.array([[float(v) for v in row] for row in field.dxhat])[:m_total]
    px = np.array([[float(v) for v in row] for row in px_frac])[:m_total]

    # lifetime net flow per vertex: cumulative signed wedge with the field
    edges = [(r.i, r.j) for r in field.relations[0]]
    flow_step = np.zeros((m_total, n))
    for t in range(m_total):
        row = field.relations[t]
        for e, (i, j) in enumerate(edges):
            w = float(row[e].r_wedge)
            flow_step[t, j] += w
            flow_step[t, i] -= w
    flow_cum = np.cumsum(flow_step, axis=0)
    alive_cum = np.cumsum((np.abs(dx) > 0).astype(float), axis=0)

    fwd_share = {h: np.full((m_total, n), np.nan) for h in HORIZONS}
    fwd_px = {h: np.full((m_total, n), np.nan) for h in HORIZONS}
    for h in HORIZONS:
        fwd_share[h][:m_total - h] = xh[h:] - xh[:m_total - h]
        fwd_px[h][:m_total - h] = (px[h:] - px[:m_total - h]) / px[:m_total - h]

    sel_rows = {h: [] for h in HORIZONS}
    base_rows = {h: [] for h in HORIZONS}
    sel_px = {h: [] for h in HORIZONS}
    base_px = {h: [] for h in HORIZONS}
    firings = []

    for t in range(MIN_LIFE_BARS, m_total - max(HORIZONS)):
        for i in range(n):
            life = alive_cum[t, i] / t
            hist_x = xh[1:t + 1, i]
            hist_f = flow_cum[1:t + 1, i]
            sat = float((hist_x <= xh[t, i]).mean())
            drain = float((hist_f <= flow_cum[t, i]).mean())
            for h in HORIZONS:
                if not np.isnan(fwd_share[h][t, i]):
                    base_rows[h].append(fwd_share[h][t, i])
                    base_px[h].append(fwd_px[h][t, i])
            gain_mode = "GAIN" in [a.upper() for a in sys.argv[1:]]
            hit = (life >= 0.9 and drain >= 0.8) if gain_mode                 else (life >= 0.9 and sat <= 0.2 and drain <= 0.2)
            if hit:
                for h in HORIZONS:
                    if not np.isnan(fwd_share[h][t, i]):
                        sel_rows[h].append(fwd_share[h][t, i])
                        sel_px[h].append(fwd_px[h][t, i])
                firings.append((common[t][:10], symbols[i]))

    years = (m_total - MIN_LIFE_BARS - max(HORIZONS)) / 252
    print(f"Field: {n} vertices, {m_total} closed bars | "
          f"qualifying configurations: {len(firings)} "
          f"({len(firings) / max(years, 1e-9):.1f}/yr)")
    print()
    print("FIELD-LEVEL RESULT (the physics claim — forward SHARE change):")
    for h in HORIZONS:
        s, b = sel_rows[h], base_rows[h]
        s_up = 100 * _mean([1.0 if v > 0 else 0.0 for v in s]) if s else 0
        b_up = 100 * _mean([1.0 if v > 0 else 0.0 for v in b])
        print(f"  +{h} bars: share ROSE in {s_up:5.1f}% of drained-alive "
              f"configurations (n={len(s)}) vs {b_up:5.1f}% baseline "
              f"(n={len(b)})")
        print(f"           mean Δshare {np.mean(s) if s else 0:+.2e} "
              f"vs baseline {np.mean(b):+.2e}")
    print()
    print("L5 TRANSLATION (one line, after the physics):")
    for h in HORIZONS:
        s, b = sel_px[h], base_px[h]
        if s:
            print(f"  +{h} bars price: {100*_mean([1.0 if v>0 else 0.0 for v in s]):5.1f}% up, "
                  f"avg {100*np.mean(s):+.2f}% | baseline "
                  f"{100*_mean([1.0 if v>0 else 0.0 for v in b]):5.1f}%, "
                  f"avg {100*np.mean(b):+.2f}%")
    if firings:
        print()
        print(f"Most recent qualifying configurations:")
        for d, s in firings[-8:]:
            print(f"  {d}  {s}")


if __name__ == "__main__":
    main()
