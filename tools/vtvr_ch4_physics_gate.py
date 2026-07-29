"""
vtvr_ch4_physics_gate.py
=========================

NON-CANONICAL — CH4 engine candidate v3: the Mar-26 physics conditions
computed from the un-flattened joint field. No scores, no weights, no
thresholds to tune — every condition is a sign, a comparison to the
vertex's own history (rank-based), or a kernel field read directly.

THE GATE (per vertex i at closed bar t; ALL must hold — AND, like the
original filter; conditions 1-4 are the kernel's own L4 fields):

  STATE-SCALE REVISION (declared 2026-07-29, single shot): v1 used
  instantaneous signs — each ~coin-flip-true, full gate fired 197/yr,
  curve flat. The original filter's conditions were SLOW STATES
  (integrator saturation, bounded energy), not instants. v2 measures
  the same six physics quantities as persistent states over K=5 bars
  (one trading week, declared a priori, not searched):

  C1 DIRECTION    net share displacement over last 5 bars ≥ 0
  C2 NO REVERSAL  zero reversals in the last 5 bars (L4 field clean)
  C3 BREATHING    mean swept volume last 5 bars > mean prior 5
                  (window-scale expansion, not a one-bar tick)
  C4 MOTION       mean share acceleration over last 5 bars ≥ 0
  C5 DEEP CYCLE   x̂_i(t) in the BOTTOM TERCILE of its trailing 120
                  bars (deep early-cycle, ~1/3 rarity by construction)
  C6 SUSTAINED    field-cohesion ≤ its trailing p80 for ALL of the
     COHERENCE    last 5 bars (no relational storm all week)
  plus: 120-bar history minimum; price ≥ $5 (domain floor, declared).

  v3 (declared 2026-07-29, Joe's key): ZOMBIE EXCLUSION as an
  ELIGIBILITY precondition — a vertex enters evaluation at t only if
  ≥90% of its trailing 120 bars show nonzero displacement (the stock
  actually lived; the gate_count≥10 principle). Zombies pollute both
  signal and baseline on a thin feed: an unchanged close passes
  "no reversal / direction / motion" while meaning "no data."

ACCEPTANCE BAR (the physics signature): precision must RISE as
conditions stack. The full instrument curve — 0 through 6 conditions
met — is reported at 20/60/90 bars with firings/year. Flat curve =
finance = dead, by the standard that executed the previous engines.

Universe: cohort A joint field, closed bars only. Kernel untouched.
Usage: python tools/vtvr_ch4_physics_gate.py
"""

from __future__ import annotations

import math
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field, _mean  # noqa: E402

W = 120
HORIZONS = (20, 60, 90)
PRICE_FLOOR = 5.0


def run_universe(universe, label):
    print(f"UNIVERSE: {label}")
    symbols, common, field, px_frac = build_field(universe, min_days=1200)
    return gate_curve(symbols, common, field, px_frac)


def main():
    if len(sys.argv) > 1 and sys.argv[1].upper() == "FULL300":
        import json as _json
        u = _json.load(open(os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "vtvr_universe_300.json")))["symbols"]
        cohorts = [u[i:i + 30] for i in range(0, len(u), 30)]
        pooled = {k: {h: [] for h in HORIZONS} for k in range(7)}
        pooled_fire = []
        yrs = None
        for ci, cohort in enumerate(cohorts):
            print(f"--- cohort {ci + 1}/{len(cohorts)} ---")
            try:
                rows, fires, years = run_universe(cohort, f"300-list c{ci + 1}")
            except Exception as e:
                print(f"cohort {ci + 1} failed: {e}")
                continue
            yrs = years
            for k in range(7):
                for h in HORIZONS:
                    pooled[k][h].extend(rows[k][h])
            pooled_fire.extend(fires)
        print()
        print("=" * 70)
        print("POOLED INSTRUMENT CURVE — 300-name universe, zombie-filtered")
        print("=" * 70)
        print_curve(pooled, pooled_fire, yrs * len(cohorts) if yrs else 1)
        return

    universe = None
    label = "cohort A"
    if len(sys.argv) > 1 and sys.argv[1].upper() == "B":
        from tools.vtvr_star_state_replication import COHORT_B
        universe = COHORT_B
        label = "cohort B (virgin)"
    rows, fires, years = run_universe(universe, label)
    print_curve(rows, fires, years)


def gate_curve(symbols, common, field, px_frac):
    px = np.array([[float(v) for v in row] for row in px_frac])
    px = np.array([[float(v) for v in row] for row in px_frac])
    m_total, n = len(common), len(symbols)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if common[-1][:10] == today:
        m_total -= 1
        print(f"Excluded forming bar {today}")

    dx = np.array([[float(v) for v in row] for row in field.dxhat])[:m_total]
    vol = np.array([[float(v) for v in row] for row in field.volume])[:m_total]
    xh = np.array([[float(v) for v in row] for row in field.xhat])[:m_total]
    dts = np.array([float(t) for t in field.dts])[:m_total]
    px = px[:m_total]

    # L4 motion (acceleration of structural share, exact-time)
    acc = np.zeros((m_total, n))
    for t in range(2, m_total):
        u1 = dx[t] / dts[t] if dts[t] else 0.0
        u0 = dx[t - 1] / dts[t - 1] if dts[t - 1] else 0.0
        acc[t] = (u1 - u0) / dts[t] if dts[t] else 0.0

    # Vertex field-cohesion per bar: sum over partners of |rΔ|
    coh = np.zeros((m_total, n))
    edges = [(r.i, r.j) for r in field.relations[0]]
    for t in range(m_total):
        row = field.relations[t]
        for e, (i, j) in enumerate(edges):
            rd = abs(float(row[e].r_delta))
            coh[t, i] += rd
            coh[t, j] += rd

    max_h = max(HORIZONS)
    fwd = {h: np.full((m_total, n), np.nan) for h in HORIZONS}
    for h in HORIZONS:
        fwd[h][:m_total - h] = (px[h:] - px[:m_total - h]) / px[:m_total - h]

    # Evaluate conditions per (t, i)
    counts_rows = {k: {h: [] for h in HORIZONS} for k in range(7)}
    full_gate_firings = []
    years = (m_total - W - max_h) / 252

    for t in range(W, m_total - max_h):
        x_terc = np.percentile(xh[t - W + 1:t + 1], 33.3, axis=0)
        coh_p80 = np.percentile(coh[t - W + 1:t + 1], 80, axis=0)
        alive = (np.abs(dx[t - W + 1:t + 1]) > 0).mean(axis=0) >= 0.90
        for i in range(n):
            if px[t, i] < PRICE_FLOOR or not alive[i]:
                continue
            c = 0
            c += (xh[t, i] - xh[t - 5, i]) >= 0                    # C1
            c += all(dx[s - 1, i] * dx[s, i] >= 0
                     for s in range(t - 4, t + 1))                 # C2
            c += vol[t - 4:t + 1, i].mean() > vol[t - 9:t - 4, i].mean()  # C3
            c += acc[t - 4:t + 1, i].mean() >= 0                   # C4
            c += xh[t, i] <= x_terc[i]                             # C5
            c += bool((coh[t - 4:t + 1, i] <= coh_p80[i]).all())   # C6
            for h in HORIZONS:
                r = fwd[h][t, i]
                if not math.isnan(r):
                    counts_rows[c][h].append(r)
            if c == 6:
                full_gate_firings.append((common[t][:10], symbols[i]))

    return counts_rows, full_gate_firings, years


def print_curve(counts_rows, full_gate_firings, years):
    print(f"{'conditions':<11}{'firings/yr':>11}"
          + "".join(f"{f'WR@{h}':>9}{f'avg@{h}':>9}" for h in HORIZONS))
    for k in range(7):
        rows20 = counts_rows[k][20]
        rate = len(rows20) / years / 1.0 if years else 0
        line = f"{k:<11}{rate:>11.1f}"
        for h in HORIZONS:
            rs = counts_rows[k][h]
            if rs:
                wr = 100 * _mean([1.0 if r > 0 else 0.0 for r in rs])
                line += f"{wr:>9.1f}{100 * _mean(rs):>+9.2f}"
            else:
                line += f"{'—':>9}{'—':>9}"
        print(line)

    print()
    base = [r for k in range(7) for r in counts_rows[k][60]]
    print(f"Universe base @60: WR "
          f"{100 * _mean([1.0 if r > 0 else 0.0 for r in base]):.1f}% "
          f"mean {100 * _mean(base):+.2f}%")
    print()
    if full_gate_firings:
        print(f"Full-gate firings (all 6): {len(full_gate_firings)} "
              f"({len(full_gate_firings) / years:.1f}/yr). Last 10:")
        for d, s in full_gate_firings[-10:]:
            print(f"  {d}  {s}")
    print()
    print("Raw. Nothing tuned. The curve is the verdict.")


if __name__ == "__main__":
    main()
