"""
vtvr_adversarial_null_test.py
==============================

NON-CANONICAL — adversarial falsification of the coherent-laggard state.

Physics discipline (Joe, 2026-07-28): this is a physics problem with
adversarial data, not a quant exercise. A physical structure must satisfy
a destruction test: when the structure it claims to read is destroyed —
while every per-stock return distribution is preserved exactly — its edge
must VANISH. If the edge survives destruction, the "state" was a
statistical artifact of the return distributions, not structure.

NULL A (relational + temporal shred): each stock's daily return sequence
is permuted independently by a deterministic permutation (SHA-256 order,
no randomness). Marginal distributions identical; autocorrelation and all
cross-stock relations destroyed.

NULL B (temporal shred, relations preserved): one shared deterministic
permutation of DATES applied to all stocks jointly. Each day's cross-
sectional relations survive intact; temporal ordering (trends, breathing,
windows) is destroyed.

The frozen state definition and the frozen kernel run unchanged on the
shredded fields. Expectation if the state is physical: WR collapses to
that shredded universe's own baseline in both nulls.

Usage: python tools/vtvr_adversarial_null_test.py
"""

from __future__ import annotations

import hashlib
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.isolated_market_vtvr_side_kernel import dimensionalize  # noqa: E402
from tools.vtvr_structure_search import (  # noqa: E402
    build_field,
    per_step_arrays,
    window_desc,
    W_LONG,
    W_SHORT,
    _mean,
)

HORIZONS = (20, 60, 90)


def det_perm(count: int, tag: str):
    """Deterministic permutation of range(count) via SHA-256 ordering."""
    return sorted(range(count),
                  key=lambda k: hashlib.sha256(f"{tag}:{k}".encode()).digest())


def rebuild_prices(px, perm_per_stock):
    """Rebuild price paths from permuted return sequences (same start)."""
    m, n = len(px), len(px[0])
    rets = [[px[k][i] / px[k - 1][i] for i in range(n)] for k in range(1, m)]
    out = [list(px[0])]
    for k in range(1, m):
        row = []
        for i in range(n):
            r = rets[perm_per_stock[i][k - 1]][i]
            row.append(out[-1][i] * r)
        out.append(row)
    return out


def thirds(descs, key, n):
    order = sorted(range(n), key=lambda i: descs[i][key])
    return {i: ("LO", "MID", "HI")[min(2, (p * 3) // n)]
            for p, i in enumerate(order)}


def evaluate(symbols, times, price_rows, label):
    obs = [[Fraction(v).limit_denominator(10**9) for v in row]
           for row in price_rows]
    field = dimensionalize(symbols, times, obs)
    arrs = per_step_arrays(symbols, field)
    n, m_total = arrs["n"], arrs["m"]
    px = [[float(v) for v in row] for row in obs]

    max_h = max(HORIZONS)
    eval_dates = list(range(W_LONG, m_total - max_h))

    star_rows, base_rows = [], []
    for m in eval_dates:
        dl = window_desc(arrs, m, W_LONG)
        ds = window_desc(arrs, m, W_SHORT)
        brth_l = thirds(dl, "BRTH", n)
        coh_s = thirds(ds, "COH", n)
        ltrnd_l = thirds(dl, "LTRND", n)
        members = [i for i in range(n)
                   if brth_l[i] == "MID" and coh_s[i] == "HI"
                   and ltrnd_l[i] == "LO"]
        for i in range(n):
            fwd = {h: (px[m + h][i] - px[m][i]) / px[m][i] for h in HORIZONS}
            base_rows.append(fwd)
            if i in members:
                star_rows.append(fwd)

    print(f"{label}:")
    for h in HORIZONS:
        s = [r[h] for r in star_rows]
        b = [r[h] for r in base_rows]
        wr_s = _mean([1.0 if x > 0 else 0.0 for x in s]) * 100 if s else 0.0
        wr_b = _mean([1.0 if x > 0 else 0.0 for x in b]) * 100
        print(f"  +{h:<3} star N={len(s):<6} WR={wr_s:5.1f}% "
              f"mean={_mean(s)*100 if s else 0:+6.2f}%   "
              f"| baseline WR={wr_b:5.1f}% mean={_mean(b)*100:+6.2f}%   "
              f"| edge={wr_s - wr_b:+5.1f}pp")
    print()


def main():
    symbols, common, field, px = build_field()
    times = list(field.times)
    m, n = len(px), len(symbols)

    # NULL A: independent per-stock shred
    perm_a = {i: det_perm(m - 1, f"nullA:{symbols[i]}") for i in range(n)}
    px_a = rebuild_prices(px, perm_a)

    # NULL B: joint date shred (same permutation for every stock)
    shared = det_perm(m - 1, "nullB:joint")
    perm_b = {i: shared for i in range(n)}
    px_b = rebuild_prices(px, perm_b)

    print(f"Universe: {n} tickers, {m} days. Frozen state: coherent laggard.")
    print()
    evaluate(symbols, times, px_a, "NULL A — relations + time destroyed")
    evaluate(symbols, times, px_b, "NULL B — time destroyed, relations kept")
    print("If both edges collapse toward 0pp, the live-data edge is reading")
    print("real temporal-relational structure — physics, not distribution.")


if __name__ == "__main__":
    main()
