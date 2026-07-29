"""
vtvr_structural_forward_study.py
=================================

NON-CANONICAL — structural-perception forward study over the joint field.

QUESTION (Joe, 2026-07-28): viewed over a trailing window of W bars, do the
joint-field structures the side kernel perceives indicate favorable
near-term / future-term structure?

This is NOT a trading rule. It is the band-table discipline of the 835-trade
CH2 walkforward applied to the side kernel's relation dimensions: perceive
structure over the window, band cross-sectionally, measure what the market
did NEXT, report every band.

REGISTERED PROTOCOL (frozen before first run):

  Universe    30 declared tickers (same as vtvr_leadlag_walkforward).
  History     ~1100 calendar days of daily closes, joint simultaneous field.
  Window      W = 120 trailing bars per evaluation date (causal only).
  Horizons    Forward 20 bars ("near") and 60 bars ("future").
  Descriptors (per stock i at date m, from the joint field only):
    D1 LEADERSHIP  window-integrated signed wedge of i vs the rest of the
                   field (daily signs are noise — the 120-bar integral is
                   the structure).
    D2 COHESION    mean co-movement intensity: mean over window and partners
                   of |r_delta(i,j)| — is i moving WITH the field?
    D3 BREATHING   window swept-volume share of i (sum v_{m,i}).
    D4 REVERSAL    fraction of window steps where i's displacement flips
                   sign (choppiness).
    D5 PRESSURE    mean |acceleration| of i's structural share.
  Banding     Cross-sectional quartiles per date per descriptor (rank-based;
              no tunable thresholds exist anywhere in this study).
  Metrics     Per quartile: mean forward return, mean EXCESS forward return
              (vs date cross-section mean), win rate. Reported for the full
              set AND for first/second half separately (stability check).
  Materiality (pre-registered): a descriptor "sorts the future" if the
              Q4−Q1 excess-return spread at the 60-bar horizon is ≥ 1.0%
              with the same sign in both halves. Everything is reported
              regardless.

Read-only; data API only; no production import; no trading claim.
Usage: python tools/vtvr_structural_forward_study.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.isolated_vtvr_side_kernel import dimensionalize  # noqa: E402
from tools.run_market_vtvr_capture import (  # noqa: E402
    fetch_exact_bars,
    iso_to_rational_seconds,
)
from tools.vtvr_leadlag_walkforward import UNIVERSE  # noqa: E402

WINDOW = 120
HORIZONS = (20, 60)
HISTORY_DAYS = 1100
BAR_LIMIT = 800
MATERIAL_SPREAD = 0.010  # 1.0% at 60 bars


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def build_field():
    from datetime import datetime, timedelta, timezone
    start_iso = (datetime.now(timezone.utc) - timedelta(days=HISTORY_DAYS)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    per_symbol = {}
    for s in UNIVERSE:
        try:
            per_symbol[s] = fetch_exact_bars(s, "1Day", BAR_LIMIT, start_iso)
        except Exception as e:
            print(f"  {s}: fetch failed ({e}) — dropped")
    symbols = [s for s in UNIVERSE if per_symbol.get(s)]
    common = sorted(set.intersection(*(set(per_symbol[s].keys()) for s in symbols)))
    print(f"Symbols: {len(symbols)} | simultaneous days: {len(common)}")
    times = [iso_to_rational_seconds(t) for t in common]
    observations = [[per_symbol[s][t] for s in symbols] for t in common]
    field = dimensionalize(symbols, times, observations)
    px = [[float(v) for v in row] for row in observations]
    return symbols, common, field, px


def compute_descriptors(symbols, field, px):
    """Float study layer over the exact field. All causal."""
    m_total, n = len(field.times), len(symbols)
    edges = [(r.i, r.j) for r in field.relations[0]]

    wedge = [[float(r.r_wedge) for r in row] for row in field.relations]
    rdelta = [[abs(float(r.r_delta)) for r in row] for row in field.relations]
    vol = [[float(v) for v in row] for row in field.volume]
    dx = [[float(v) for v in row] for row in field.dxhat]
    dts = [float(t) for t in field.dts]

    # Per-step leadership of i: sum over partners of signed wedge toward i.
    lead_step = [[0.0] * n for _ in range(m_total)]
    coh_step = [[0.0] * n for _ in range(m_total)]
    for k in range(m_total):
        for e, (i, j) in enumerate(edges):
            w = wedge[k][e]
            # wedge>0 <=> j outperformed i on this step
            lead_step[k][j] += w
            lead_step[k][i] -= w
            coh_step[k][i] += rdelta[k][e]
            coh_step[k][j] += rdelta[k][e]

    # Acceleration of structural share (per unit time), causal
    acc = [[0.0] * n for _ in range(m_total)]
    for k in range(2, m_total):
        for i in range(n):
            u1 = dx[k][i] / dts[k] if dts[k] else 0.0
            u0 = dx[k - 1][i] / dts[k - 1] if dts[k - 1] else 0.0
            acc[k][i] = (u1 - u0) / dts[k] if dts[k] else 0.0

    def window_descriptors(m):
        """Descriptors from bars (m-WINDOW, m]."""
        lo = m - WINDOW + 1
        out = []
        for i in range(n):
            d1 = sum(lead_step[k][i] for k in range(lo, m + 1))
            d2 = _mean([coh_step[k][i] / (n - 1) for k in range(lo, m + 1)])
            d3 = sum(vol[k][i] for k in range(lo, m + 1))
            d4 = _mean([
                1.0 if dx[k - 1][i] * dx[k][i] < 0 else 0.0
                for k in range(lo + 1, m + 1)
            ])
            d5 = _mean([abs(acc[k][i]) for k in range(lo, m + 1)])
            out.append({"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5})
        return out

    return window_descriptors, px, m_total, n


def quartile(ranks_sorted_idx, n):
    """Map cross-sectional rank position to quartile 1..4."""
    q = {}
    for pos, i in enumerate(ranks_sorted_idx):
        q[i] = 1 + min(3, (pos * 4) // n)
    return q


def run_study():
    symbols, common, field, px = build_field()
    window_descriptors, px, m_total, n = compute_descriptors(symbols, field, px)

    max_h = max(HORIZONS)
    eval_dates = list(range(WINDOW, m_total - max_h))
    if len(eval_dates) < 40:
        raise SystemExit("Insufficient history for the protocol.")
    half = eval_dates[len(eval_dates) // 2]
    print(f"Evaluation dates: {len(eval_dates)} "
          f"({common[eval_dates[0]][:10]} .. {common[eval_dates[-1]][:10]}), "
          f"half-split at {common[half][:10]}")

    # rows[desc][horizon][half][quartile] -> list of (fwd, excess)
    rows = {d: {h: {0: {q: [] for q in (1, 2, 3, 4)},
                    1: {q: [] for q in (1, 2, 3, 4)}}
                for h in HORIZONS}
            for d in ("D1", "D2", "D3", "D4", "D5")}

    for m in eval_dates:
        descs = window_descriptors(m)
        fwd = {}
        for h in HORIZONS:
            fwd[h] = [(px[m + h][i] - px[m][i]) / px[m][i] for i in range(n)]
        which_half = 0 if m < half else 1
        for d in ("D1", "D2", "D3", "D4", "D5"):
            order = sorted(range(n), key=lambda i: descs[i][d])
            qmap = quartile(order, n)
            for h in HORIZONS:
                xmean = _mean(fwd[h])
                for i in range(n):
                    rows[d][h][which_half][qmap[i]].append(
                        (fwd[h][i], fwd[h][i] - xmean)
                    )

    names = {
        "D1": "LEADERSHIP (window-integrated wedge)",
        "D2": "COHESION (co-movement with field)",
        "D3": "BREATHING (swept-volume share)",
        "D4": "REVERSAL (choppiness)",
        "D5": "PRESSURE (mean |accel|)",
    }

    print()
    for d in ("D1", "D2", "D3", "D4", "D5"):
        print("=" * 72)
        print(f"{d} — {names[d]}")
        for h in HORIZONS:
            print(f"  Forward {h} bars:")
            print(f"    {'Q':<3}{'fwd%':>8}{'excess%':>9}{'win%':>7}   "
                  f"{'H1 exc%':>8}{'H2 exc%':>8}")
            spreads = {}
            for q in (1, 2, 3, 4):
                both = rows[d][h][0][q] + rows[d][h][1][q]
                fwd_m = _mean([x[0] for x in both]) * 100
                exc_m = _mean([x[1] for x in both]) * 100
                win = _mean([1.0 if x[0] > 0 else 0.0 for x in both]) * 100
                h1 = _mean([x[1] for x in rows[d][h][0][q]]) * 100
                h2 = _mean([x[1] for x in rows[d][h][1][q]]) * 100
                spreads[q] = (exc_m, h1, h2)
                print(f"    Q{q:<2}{fwd_m:>8.2f}{exc_m:>9.2f}{win:>7.1f}   "
                      f"{h1:>8.2f}{h2:>8.2f}")
            if h == 60:
                sp = spreads[4][0] - spreads[1][0]
                stable = (spreads[4][1] - spreads[1][1]) * (spreads[4][2] - spreads[1][2]) > 0
                material = abs(sp) >= MATERIAL_SPREAD * 100 and stable
                print(f"    Q4−Q1 excess spread @60 = {sp:+.2f}% | "
                      f"same sign both halves: {stable} | "
                      f"PRE-REGISTERED MATERIALITY: "
                      f"{'YES' if material else 'no'}")
    print("=" * 72)
    print("Every band reported; no descriptor was added or dropped after")
    print("seeing results. Materiality bar was frozen before the run.")


if __name__ == "__main__":
    run_study()
