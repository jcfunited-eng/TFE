"""
vtvr_field_analog_engine_v2.py
===============================

NON-CANONICAL — whole-object analog engine, v2. The single pre-declared
iteration allowed after v1's null (see vtvr_field_analog_engine.py).

Changes from v1 — both named in the v1 after-review BEFORE any v2 code:

  TEMPO TOLERANCE   v1 compared bar-for-bar in lockstep. v2 distance is
                    the mean of L1 at four resolutions (120, 60, 30, 12
                    time samples of the SAME object), and at the finest
                    resolution the minimum over ±5-bar shifts. Identical
                    structure at slightly different tempo now matches.
  DIMENSION BUDGET  v1 gave all 118 components equal voice (relations
                    outvoted the share trajectory 116-to-2). v2 gives the
                    three typed physical dimensions — Vector (share),
                    Volume, Relation — one third of the distance budget
                    each, per the intent's own typed structure.

Everything else is identical to v1 by construction: same objects, same
gauge, same echo guard (25 distinct episodes), same 90-bar analog gap,
same 70% consensus bar, same temporal walk-forward split, same universe
(cohort A). One shot; the result stands as it lands.

Usage: python tools/vtvr_field_analog_engine_v2.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field, _mean  # noqa: E402
from tools.vtvr_field_analog_engine import (  # noqa: E402
    gauge, W, HORIZON, K_ANALOGS, COARSE_KEEP, CONSENSUS,
    QUERY_FRACTION, QUERY_STRIDE, GAP, MIN_ANALOG_SEP,
)

RESOLUTIONS = (120, 60, 30, 12)
MAX_SHIFT = 5


def build_objects_v2(symbols, field):
    """Per (stock, date): dict of per-dimension blocks at full resolution."""
    m_total, n = len(field.times), len(symbols)
    e_count = n * (n - 1) // 2
    edges = [(r.i, r.j) for r in field.relations[0]]

    xhat = np.array([[float(v) for v in row] for row in field.xhat])
    vol = np.array([[float(v) for v in row] for row in field.volume])
    rel = np.zeros((m_total, e_count, 4))
    for k in range(m_total):
        for e, r in enumerate(field.relations[k]):
            rel[k, e] = (float(r.r_minus), float(r.r_plus),
                         float(r.r_delta), float(r.r_wedge))

    stock_edges = [[] for _ in range(n)]
    for e, (i, j) in enumerate(edges):
        stock_edges[i].append(e)
        stock_edges[j].append(e)
    stock_edges = [np.array(es) for es in stock_edges]

    objs = {}
    for m in range(W, m_total):
        lo = m - W + 1
        wrel = rel[lo:m + 1]
        for i in range(n):
            xb = gauge(xhat[lo:m + 1, i][None, :])[0].astype(np.float32)
            vb = gauge(vol[lo:m + 1, i][None, :])[0].astype(np.float32)
            eb = wrel[:, stock_edges[i], :].reshape(W, -1)
            eb = gauge(eb.T).T.astype(np.float32)
            objs[(m, i)] = (xb, vb, eb)
    return objs


def _res(block, r):
    """Resample a (W,...) block to r time samples by block means."""
    bs = W // r
    if block.ndim == 1:
        return block.reshape(r, bs).mean(axis=1)
    return block.reshape(r, bs, -1).mean(axis=1)


def dim_distance(a, b):
    """Multi-resolution L1 for one dimension block pair, shift-tolerant
    at full resolution. Normalized by element count per resolution."""
    total = 0.0
    for r in RESOLUTIONS:
        if r == W:
            best = None
            for s in range(-MAX_SHIFT, MAX_SHIFT + 1):
                if s >= 0:
                    aa = a[s:] if a.ndim == 1 else a[s:, :]
                    bb = b[:W - s] if b.ndim == 1 else b[:W - s, :]
                else:
                    aa = a[:W + s] if a.ndim == 1 else a[:W + s, :]
                    bb = b[-s:] if b.ndim == 1 else b[-s:, :]
                v = float(np.abs(aa - bb).mean())
                best = v if best is None else min(best, v)
            total += best
        else:
            ra, rb = _res(a, r), _res(b, r)
            total += float(np.abs(ra - rb).mean())
    return total / len(RESOLUTIONS)


def object_distance(oa, ob):
    """Equal budget per typed dimension: Vector, Volume, Relation."""
    return (dim_distance(oa[0], ob[0])
            + dim_distance(oa[1], ob[1])
            + dim_distance(oa[2], ob[2])) / 3.0


def coarse_vec(o):
    """Cheap prefilter vector: 12-sample resample of all three dims,
    each dim scaled to unit budget."""
    parts = []
    for blk in o:
        r = _res(blk, 12).ravel()
        m = np.abs(r).mean()
        parts.append(r / (m if m > 0 else 1.0) / len(r))
    return np.concatenate(parts)


def main():
    symbols, common, field, px_frac = build_field()  # cohort A
    px = [[float(v) for v in row] for row in px_frac]
    m_total, n = len(common), len(symbols)
    print(f"Cohort A: {n} names, {m_total} days. Building v2 objects...")
    objs = build_objects_v2(symbols, field)

    eval_last = m_total - HORIZON
    all_dates = list(range(W, eval_last))
    q_start = all_dates[int(len(all_dates) * (1 - QUERY_FRACTION))]
    queries = [m for m in range(q_start, eval_last, QUERY_STRIDE)]
    print(f"Analog base: {W}..{q_start - GAP} | queries {len(queries)} dates "
          f"from {common[q_start][:10]}")

    fwd = np.zeros((m_total, n))
    for m in range(m_total - HORIZON):
        for i in range(n):
            fwd[m, i] = (px[m + HORIZON][i] - px[m][i]) / px[m][i]

    base_keys = [(m, i) for m in range(W, q_start - GAP) for i in range(n)]
    C = np.stack([coarse_vec(objs[k]) for k in base_keys])
    print(f"Analog objects: {len(base_keys)}")

    signals = []
    all_rows = []
    for qn, m in enumerate(queries):
        for i in range(n):
            qo = objs[(m, i)]
            qc = coarse_vec(qo)
            d = np.abs(C - qc).sum(axis=1)
            cand = np.argpartition(d, COARSE_KEEP)[:COARSE_KEEP]
            fd = np.array([object_distance(objs[base_keys[c]], qo)
                           for c in cand])
            best = []
            taken = {}
            for idx in np.argsort(fd):
                b = cand[idx]
                bm, bi = base_keys[b]
                if any(abs(bm - t) < MIN_ANALOG_SEP
                       for t in taken.get(bi, ())):
                    continue
                best.append(b)
                taken.setdefault(bi, []).append(bm)
                if len(best) == K_ANALOGS:
                    break
            outs = np.array([fwd[base_keys[b][0], base_keys[b][1]]
                             for b in best])
            cons = float((outs > 0).mean())
            all_rows.append((cons, fwd[m, i]))
            if cons >= CONSENSUS:
                signals.append((m, i))
        if qn % 20 == 0:
            print(f"  query date {qn + 1}/{len(queries)}")

    base_rets = [r for _, r in all_rows]
    print()
    print("=" * 66)
    print("FULL-FIELD ANALOG v2 — tempo-tolerant, dimension-budgeted")
    print("=" * 66)
    print(f"Query stock-dates: {len(all_rows)} | baseline WR "
          f"{100 * _mean([1.0 if r > 0 else 0.0 for r in base_rets]):.1f}% "
          f"mean {100 * _mean(base_rets):+.2f}%")
    if signals:
        s_rets = [fwd[m, i] for m, i in signals]
        print(f"SIGNALS (consensus ≥ {CONSENSUS:.0%}): {len(signals)} | "
              f"WR {100 * _mean([1.0 if r > 0 else 0.0 for r in s_rets]):.1f}% "
              f"| mean {100 * _mean(s_rets):+.2f}%/{HORIZON} bars")
    else:
        print("No signals at the declared consensus bar.")

    print()
    print("Consensus deciles:")
    rows = sorted(all_rows)
    dec = len(rows) // 10
    for d10 in range(10):
        seg = rows[d10 * dec:(d10 + 1) * dec]
        rs = [r for _, r in seg]
        cs = [c for c, _ in seg]
        print(f"  {min(cs):.2f}-{max(cs):.2f}: "
              f"WR {100 * _mean([1.0 if r > 0 else 0.0 for r in rs]):5.1f}% "
              f"mean {100 * _mean(rs):+6.2f}%  (n={len(seg)})")


if __name__ == "__main__":
    main()
