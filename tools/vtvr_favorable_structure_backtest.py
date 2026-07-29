"""
vtvr_favorable_structure_backtest.py
=====================================

NON-CANONICAL — backtest of the FAVORABLE STRUCTURE the joint field surfaced
in the 120-bar forward study (vtvr_structural_forward_study.py):

    CALM-COHERENT STATE:
      smooth   — reversal rate in the bottom half of the cross-section
      moderate — pressure in the middle two quartiles
      moderate — cohesion in the middle two quartiles

This is an L5-style translation hypothesis over the side kernel's joint
field: "a stock whose structural share moves smoothly, with moderate energy,
moderately coherent with the field, is in a favorable configuration for the
next 20-60 bars."

Backtest discipline: same joint field, W=120 trailing bars, forward 20/60
bar outcomes, gated set vs full-universe baseline, reported for the full
window AND per half. The gate was formed from the pooled band tables of the
prior study; the per-half columns and the forward-only design are the
stability evidence. Final authority would require fresh data going forward.

Usage: python tools/vtvr_favorable_structure_backtest.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structural_forward_study import (  # noqa: E402
    build_field,
    compute_descriptors,
    WINDOW,
    HORIZONS,
    _mean,
)


def main():
    symbols, common, field, px = build_field()
    window_descriptors, px, m_total, n = compute_descriptors(symbols, field, px)

    max_h = max(HORIZONS)
    eval_dates = list(range(WINDOW, m_total - max_h))
    half = eval_dates[len(eval_dates) // 2]
    print(f"Evaluation dates: {len(eval_dates)} "
          f"({common[eval_dates[0]][:10]} .. {common[eval_dates[-1]][:10]})")

    gated = {h: {0: [], 1: []} for h in HORIZONS}
    base = {h: {0: [], 1: []} for h in HORIZONS}
    gate_sizes = []
    latest_gate = None

    for m in eval_dates:
        descs = window_descriptors(m)

        def band(dkey):
            order = sorted(range(n), key=lambda i: descs[i][dkey])
            pos = {i: p for p, i in enumerate(order)}
            return pos

        p_rev = band("D4")
        p_pre = band("D5")
        p_coh = band("D2")

        in_gate = [
            i for i in range(n)
            if p_rev[i] < n // 2                      # smooth half
            and n // 4 <= p_pre[i] < 3 * n // 4       # moderate pressure
            and n // 4 <= p_coh[i] < 3 * n // 4       # moderate cohesion
        ]
        gate_sizes.append(len(in_gate))
        latest_gate = (m, in_gate)
        which = 0 if m < half else 1
        for h in HORIZONS:
            fwd = [(px[m + h][i] - px[m][i]) / px[m][i] for i in range(n)]
            for i in range(n):
                base[h][which].append(fwd[i])
            for i in in_gate:
                gated[h][which].append(fwd[i])

    print(f"Gate size: mean {sum(gate_sizes)/len(gate_sizes):.1f} of {n} "
          f"stocks per date")
    print()
    print("CALM-COHERENT STRUCTURE vs full universe")
    print("=" * 66)
    for h in HORIZONS:
        g_all = gated[h][0] + gated[h][1]
        b_all = base[h][0] + base[h][1]
        print(f"Forward {h} bars:")
        print(f"  {'':<18}{'N':>7}{'mean fwd%':>11}{'win%':>7}")
        print(f"  {'universe':<18}{len(b_all):>7}{_mean(b_all)*100:>11.2f}"
              f"{_mean([1.0 if x>0 else 0.0 for x in b_all])*100:>7.1f}")
        print(f"  {'calm-coherent':<18}{len(g_all):>7}{_mean(g_all)*100:>11.2f}"
              f"{_mean([1.0 if x>0 else 0.0 for x in g_all])*100:>7.1f}")
        edge = (_mean(g_all) - _mean(b_all)) * 100
        e1 = (_mean(gated[h][0]) - _mean(base[h][0])) * 100
        e2 = (_mean(gated[h][1]) - _mean(base[h][1])) * 100
        print(f"  edge vs universe = {edge:+.2f}%  "
              f"(H1 {e1:+.2f}% | H2 {e2:+.2f}%)")
        print()

    m, ig = latest_gate
    print(f"Most recent evaluation date ({common[m][:10]}) — stocks currently")
    print(f"in the calm-coherent structure: {', '.join(symbols[i] for i in ig)}")


if __name__ == "__main__":
    main()
