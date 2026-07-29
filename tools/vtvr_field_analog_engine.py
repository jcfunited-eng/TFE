"""
vtvr_field_analog_engine.py
============================

NON-CANONICAL — full-field structural analog retrieval. The first test in
this project whose decision input is the kernel's COMPLETE retained
structure, not scalar descriptors of it.

METHOD (declared before first run)

  Object      for stock i at date m: the trailing W=120 bars of its entire
              field row —
                x̂ trajectory            (W values)
                swept-volume trajectory (W values)
                ALL its edges × 4 relation components × W
              Nothing is summarized. Gauge alignment only (declared):
              each block is centered by its own window mean and scaled by
              its own mean absolute value — a per-object choice of units,
              the same freedom the group-gain quotient already grants.
  Sampling    two resolutions of the SAME object: coarse (12 time samples,
              block means) for candidate retrieval, fine (all 120 bars)
              for the final ranking. Resolution reduction preserves shape;
              it is not a statistic.
  Analogs     for each query object, the K=25 nearest PAST objects (any
              stock, same cohort, dates ended ≥ 90 bars before the query —
              no outcome overlap), by L1 distance over the full fine
              object among the 300 best coarse candidates.
  Prediction  the analogs' realized forward 60-bar returns. Signal fires
              iff ≥ 70% of analogs were positive. No other condition.
  Evaluation  strict temporal walk-forward: queries are the LAST 30% of
              dates (stride 3); analogs always precede them. Report
              signal WR/mean vs same-period all-stock baseline, and the
              consensus-decile table. Every number reported.

Universe: cohort A (30 names). Kernel frozen; simulation only.
Usage: python tools/vtvr_field_analog_engine.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field, _mean  # noqa: E402

W = 120
HORIZON = 60
K_ANALOGS = 25
COARSE_KEEP = 300
CONSENSUS = 0.70
QUERY_FRACTION = 0.30
QUERY_STRIDE = 3
GAP = 90  # bars between analog window end and query window start
MIN_ANALOG_SEP = 20  # bars between selected analogs of the SAME stock —
                     # 25 analogs must be 25 distinct episodes, not one echo


def gauge(block):
    """Center by window mean, scale by window mean-abs. Per-object units."""
    b = block - block.mean(axis=-1, keepdims=True)
    s = np.abs(b).mean(axis=-1, keepdims=True)
    s[s == 0] = 1.0
    return b / s


def build_objects(symbols, field):
    """Fine and coarse full-field objects for every (stock, date)."""
    m_total, n = len(field.times), len(symbols)
    e_count = n * (n - 1) // 2
    edges = [(r.i, r.j) for r in field.relations[0]]

    xhat = np.array([[float(v) for v in row] for row in field.xhat])      # M×N
    vol = np.array([[float(v) for v in row] for row in field.volume])     # M×N
    rel = np.zeros((m_total, e_count, 4))
    for k in range(m_total):
        for e, r in enumerate(field.relations[k]):
            rel[k, e] = (float(r.r_minus), float(r.r_plus),
                         float(r.r_delta), float(r.r_wedge))

    # per-stock edge index lists
    stock_edges = [[] for _ in range(n)]
    for e, (i, j) in enumerate(edges):
        stock_edges[i].append(e)
        stock_edges[j].append(e)
    stock_edges = [np.array(es) for es in stock_edges]

    fine = {}
    coarse = {}
    blocks = 12
    bs = W // blocks
    for m in range(W, m_total):
        lo = m - W + 1
        window_rel = rel[lo:m + 1]                       # W×E×4
        for i in range(n):
            xb = gauge(xhat[lo:m + 1, i][None, :])[0]                    # W
            vb = gauge(vol[lo:m + 1, i][None, :])[0]                     # W
            eb = window_rel[:, stock_edges[i], :]                         # W×(n-1)×4
            eb = gauge(eb.reshape(W, -1).T).T                             # W×((n-1)*4)
            obj = np.concatenate([xb[:, None], vb[:, None], eb], axis=1)  # W×D
            fine[(m, i)] = obj.astype(np.float32)
            coarse[(m, i)] = obj.reshape(blocks, bs, -1).mean(axis=1) \
                                .astype(np.float32)
    return fine, coarse


def main():
    symbols, common, field, px_frac = build_field()  # cohort A default
    px = [[float(v) for v in row] for row in px_frac]
    m_total, n = len(common), len(symbols)
    print(f"Cohort A: {n} names, {m_total} days. Building full-field objects...")
    fine, coarse = build_objects(symbols, field)

    eval_last = m_total - HORIZON
    all_dates = list(range(W, eval_last))
    q_start = all_dates[int(len(all_dates) * (1 - QUERY_FRACTION))]
    queries = [m for m in range(q_start, eval_last, QUERY_STRIDE)]
    print(f"Analog base: dates {W}..{q_start - GAP} | "
          f"queries: {len(queries)} dates from {common[q_start][:10]}")

    fwd = np.zeros((m_total, n))
    for m in range(m_total - HORIZON):
        for i in range(n):
            fwd[m, i] = (px[m + HORIZON][i] - px[m][i]) / px[m][i]

    # Flatten analog base into matrices for vectorized coarse search
    base_keys = [(m, i) for m in range(W, q_start - GAP) for i in range(n)]
    C = np.stack([coarse[k].ravel() for k in base_keys])          # B×Dc
    print(f"Analog objects: {len(base_keys)} | coarse dim {C.shape[1]} | "
          f"fine dim {fine[base_keys[0]].size}")

    signals = []      # (m, i, consensus, analog_mean)
    all_rows = []     # (consensus, fwd)
    for qn, m in enumerate(queries):
        for i in range(n):
            qc = coarse[(m, i)].ravel()
            d = np.abs(C - qc).sum(axis=1)
            cand = np.argpartition(d, COARSE_KEEP)[:COARSE_KEEP]
            qf = fine[(m, i)]
            fd = np.array([np.abs(fine[base_keys[c]] - qf).sum() for c in cand])
            # Echo guard: distinct episodes only — same-stock analogs must
            # be at least MIN_ANALOG_SEP bars apart.
            best = []
            taken = {}
            for idx in np.argsort(fd):
                b = cand[idx]
                bm, bi = base_keys[b]
                if any(abs(bm - t) < MIN_ANALOG_SEP for t in taken.get(bi, ())):
                    continue
                best.append(b)
                taken.setdefault(bi, []).append(bm)
                if len(best) == K_ANALOGS:
                    break
            outs = np.array([fwd[base_keys[b][0], base_keys[b][1]] for b in best])
            cons = float((outs > 0).mean())
            all_rows.append((cons, fwd[m, i]))
            if cons >= CONSENSUS:
                signals.append((m, i, cons, float(outs.mean())))
        if qn % 20 == 0:
            print(f"  query date {qn + 1}/{len(queries)}")

    base_rets = [r for _, r in all_rows]
    print()
    print("=" * 66)
    print("FULL-FIELD ANALOG RETRIEVAL — temporal walk-forward, cohort A")
    print("=" * 66)
    print(f"Query stock-dates: {len(all_rows)} | baseline WR "
          f"{100 * _mean([1.0 if r > 0 else 0.0 for r in base_rets]):.1f}% "
          f"mean {100 * _mean(base_rets):+.2f}%")
    if signals:
        s_rets = [fwd[m, i] for m, i, _, _ in signals]
        print(f"SIGNALS (analog consensus ≥ {CONSENSUS:.0%}): {len(signals)}")
        print(f"  WR {100 * _mean([1.0 if r > 0 else 0.0 for r in s_rets]):.1f}% "
              f"| mean {100 * _mean(s_rets):+.2f}% per {HORIZON} bars")
    else:
        print("No signals at the declared consensus bar.")

    print()
    print("Consensus deciles (does analog agreement grade the future at all?):")
    rows = sorted(all_rows)
    dec = len(rows) // 10
    for d10 in range(10):
        seg = rows[d10 * dec:(d10 + 1) * dec]
        rs = [r for _, r in seg]
        cs = [c for c, _ in seg]
        print(f"  consensus {min(cs):.2f}-{max(cs):.2f}: "
              f"WR {100 * _mean([1.0 if r > 0 else 0.0 for r in rs]):5.1f}% "
              f"mean {100 * _mean(rs):+6.2f}%  (n={len(seg)})")


if __name__ == "__main__":
    main()
