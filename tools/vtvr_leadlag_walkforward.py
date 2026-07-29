"""
vtvr_leadlag_walkforward.py
============================

NON-CANONICAL — pre-registered walk-forward falsification of the side
kernel's RELATION field: does retained pairwise lead-lag structure carry
out-of-sample expectancy?

PROTOCOL (registered before first run; constants below are frozen):

  Universe   30 declared tickers: the 10 live CH2 holdings plus 20 liquid
             large caps across sectors. Declared here, not screened.
  Window     Daily closes, lookback WINDOW_DAYS calendar days (~1 year+).
  Split      First IS_FRACTION of observations = IN-SAMPLE (measurement +
             mechanical rule construction). Remainder = OUT-OF-SAMPLE,
             untouched by any choice.
  Field      One joint L0 dimensionalization from the side kernel (exact).
             All relation facts are causal: wedge_m uses only m-1, m.

  MEASUREMENT (in-sample only):
    M1  Wedge persistence: P(sign(wedge_{m+1}) == sign(wedge_m)) over all
        edges/times with nonzero consecutive wedges.
    M2  Pairwise lead: for each ordered pair (i,j), corr(ret_i[m], ret_j[m+1])
        over in-sample days.

  RULES (mechanical, from measurements; no tuning, K and thresholds frozen):
    R1  Relation persistence/reversal: each OOS day m, take the K1=10 edges
        with largest |wedge_m|. If M1 > 0.5 FOLLOW (long the step's
        outperformer vs short the underperformer for the next day),
        else FADE (long the underperformer / short the outperformer).
        Equal weight, one-day hold, both legs.
    R2  Lead harvest: the K2=10 ordered pairs with largest |M2 corr|,
        subject to |corr| >= 0.10, are frozen from in-sample. Each OOS day,
        for each frozen pair (i leads j): position in j for the next day
        with sign = sign(corr) * sign(ret_i today). Equal weight.

  ACCOUNTING:
    Per-position daily returns, hit rate, mean, cumulative sum, max
    drawdown; then a COST haircut of 5 bps per position-day (10 bps round
    trip on half the book is approximated conservatively as 5 bps/day on
    every position).

  PRE-REGISTERED SUCCESS BAR (per rule):
    OOS mean per-position daily return AFTER cost > 0
    AND OOS hit rate > 51%.
    Anything else = NOT CONFIRMED, reported as such.

Read-only; market-data API only; no production import; no trading.
Usage: python tools/vtvr_leadlag_walkforward.py
"""

from __future__ import annotations

import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.isolated_market_vtvr_side_kernel import dimensionalize  # noqa: E402
from tools.run_market_vtvr_capture import (  # noqa: E402
    fetch_exact_bars,
    iso_to_rational_seconds,
)

UNIVERSE = [
    # live CH2 holdings (declared 2026-07-28)
    "MSBI", "HDB", "PHM", "TRMB", "DORM", "NBIX", "BDX", "VRTS", "AZZ", "DEI",
    # declared liquid large caps across sectors
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "JPM", "BAC", "XOM",
    "CVX", "JNJ", "PFE", "UNH", "HD", "WMT", "KO", "PEP", "CAT", "DE", "LIN",
]
WINDOW_DAYS = 480
BAR_LIMIT = 400
IS_FRACTION = 0.6
K1 = 10
K2 = 10
MIN_LEAD_CORR = 0.10
COST_PER_POSITION_DAY = 0.0005  # 5 bps


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _corr(a, b):
    n = len(a)
    if n < 3:
        return 0.0
    ma, mb = _mean(a), _mean(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va == 0 or vb == 0:
        return 0.0
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return cov / (va ** 0.5 * vb ** 0.5)


def _max_drawdown(cum):
    peak, mdd = float("-inf"), 0.0
    for v in cum:
        peak = max(peak, v)
        mdd = min(mdd, v - peak)
    return mdd


def _summarize(name, day_positions):
    """day_positions: list of per-day lists of per-position returns."""
    flat = [r for day in day_positions for r in day]
    if not flat:
        print(f"{name}: no positions taken")
        return None
    hits = sum(1 for r in flat if r > 0)
    hit_rate = hits / len(flat)
    gross_mean = _mean(flat)
    net = [r - COST_PER_POSITION_DAY for r in flat]
    net_mean = _mean(net)
    daily = [_mean([r - COST_PER_POSITION_DAY for r in day]) for day in day_positions if day]
    cum = []
    s = 0.0
    for d in daily:
        s += d
        cum.append(s)
    mdd = _max_drawdown(cum) if cum else 0.0
    confirmed = net_mean > 0 and hit_rate > 0.51
    print(f"{name}:")
    print(f"  positions={len(flat)}  days={len([d for d in day_positions if d])}")
    print(f"  hit rate           = {hit_rate*100:.1f}%")
    print(f"  mean/position gross= {gross_mean*10000:+.2f} bps")
    print(f"  mean/position net  = {net_mean*10000:+.2f} bps  (cost {COST_PER_POSITION_DAY*10000:.0f} bps)")
    print(f"  cumulative net     = {s*100:+.2f}% (sum of daily book returns)")
    print(f"  max drawdown       = {mdd*100:.2f}%")
    print(f"  PRE-REGISTERED BAR = {'CONFIRMED' if confirmed else 'NOT CONFIRMED'}")
    return {"hit": hit_rate, "net": net_mean, "confirmed": confirmed}


def main():
    from datetime import datetime, timedelta, timezone
    start_iso = (datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Fetching {len(UNIVERSE)} tickers, {WINDOW_DAYS}d lookback...")
    per_symbol = {}
    for s in UNIVERSE:
        try:
            per_symbol[s] = fetch_exact_bars(s, "1Day", BAR_LIMIT, start_iso)
        except Exception as e:
            print(f"  {s}: fetch failed ({e}) — dropped")
    symbols = [s for s in UNIVERSE if per_symbol.get(s)]
    common = sorted(set.intersection(*(set(per_symbol[s].keys()) for s in symbols)))
    print(f"Symbols with data: {len(symbols)} | simultaneous days: {len(common)}")
    if len(symbols) < 5 or len(common) < 120:
        raise SystemExit("Insufficient joint data for the protocol.")

    times = [iso_to_rational_seconds(t) for t in common]
    observations = [[per_symbol[s][t] for s in symbols] for t in common]

    print("Dimensionalizing joint field (exact)...")
    field = dimensionalize(symbols, times, observations)
    m_total, n = len(common), len(symbols)
    edges = [(r.i, r.j) for r in field.relations[0]]

    # Simple returns (float, evaluation layer only)
    px = [[float(v) for v in row] for row in observations]
    rets = [[0.0] * n] + [
        [(px[k][i] - px[k - 1][i]) / px[k - 1][i] for i in range(n)]
        for k in range(1, m_total)
    ]
    wedge = [[float(r.r_wedge) for r in row] for row in field.relations]

    split = int(m_total * IS_FRACTION)
    print(f"Split: in-sample days 1..{split - 1}, out-of-sample {split}..{m_total - 1}")

    # ── M1: wedge sign persistence (in-sample) ──────────────────────────
    same = 0
    total = 0
    for k in range(1, split - 1):
        for e in range(len(edges)):
            w0, w1 = wedge[k][e], wedge[k + 1][e]
            if w0 != 0 and w1 != 0:
                total += 1
                if (w0 > 0) == (w1 > 0):
                    same += 1
    m1 = same / total if total else 0.5
    follow = m1 > 0.5
    print(f"M1 wedge persistence = {m1*100:.1f}% -> R1 mode: {'FOLLOW' if follow else 'FADE'}")

    # ── M2: pairwise lead correlations (in-sample) ──────────────────────
    lead = {}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a = [rets[k][i] for k in range(1, split - 1)]
            b = [rets[k + 1][j] for k in range(1, split - 1)]
            lead[(i, j)] = _corr(a, b)
    frozen_pairs = sorted(
        ((p, c) for p, c in lead.items() if abs(c) >= MIN_LEAD_CORR),
        key=lambda pc: abs(pc[1]), reverse=True,
    )[:K2]
    print(f"M2 frozen lead pairs (|corr|>={MIN_LEAD_CORR}): "
          f"{[(symbols[i]+'->'+symbols[j], round(c,3)) for (i,j),c in frozen_pairs]}")

    # ── OOS: R1 ─────────────────────────────────────────────────────────
    r1_days = []
    for k in range(split, m_total - 1):
        ranked = sorted(range(len(edges)), key=lambda e: abs(wedge[k][e]), reverse=True)[:K1]
        day = []
        for e in ranked:
            i, j = edges[e]
            w = wedge[k][e]
            if w == 0:
                continue
            # wedge>0 <=> j outperformed i on step k
            out_idx, under_idx = (j, i) if w > 0 else (i, j)
            spread_next = rets[k + 1][out_idx] - rets[k + 1][under_idx]
            day.append(spread_next if follow else -spread_next)
        r1_days.append(day)

    # ── OOS: R2 ─────────────────────────────────────────────────────────
    r2_days = []
    for k in range(split, m_total - 1):
        day = []
        for (i, j), c in frozen_pairs:
            sig = (1 if c > 0 else -1) * (1 if rets[k][i] > 0 else -1 if rets[k][i] < 0 else 0)
            if sig == 0:
                continue
            day.append(sig * rets[k + 1][j])
        r2_days.append(day)

    print()
    print("=" * 64)
    print("OUT-OF-SAMPLE RESULTS (untouched by any choice)")
    print("=" * 64)
    s1 = _summarize("R1 relation persistence/reversal (top-|wedge| spreads)", r1_days)
    print()
    s2 = _summarize("R2 lead harvest (frozen in-sample lead pairs)", r2_days)

    print()
    print("Honest reading: a CONFIRMED bar on either rule means the retained")
    print("relation field carried real out-of-sample expectancy under the")
    print("frozen protocol. NOT CONFIRMED means it did not, on this window,")
    print("with these mechanical rules — and that is the reported result.")
    return s1, s2


if __name__ == "__main__":
    main()
