"""
vtvr_field_dynamics.py
=======================

NON-CANONICAL — the physics of the conserved share field. No returns,
no win rates, no trades anywhere in this program.

SYSTEM: rho(t) = the kernel's structural share vector (n vertices),
with the exact conservation law sum_i rho_i(t) = 1 for every t.
The field is a conserved flow network: d(rho)/dt is a redistribution.

MODEL (linear response, conservation enforced):
    delta_rho(t) = M · rho(t-1) + xi
where M has zero column sums (no source, no sink — conservation).

PHYSICS QUESTIONS, each with its measurement and its null:

  P1 EXISTENCE & STABILITY of dynamics — estimate M independently on
     three non-overlapping eras; operator similarity across eras vs
     the similarity of operators fit to time-shuffled data. If the
     real eras agree no better than shuffled data, there is no
     dynamics to speak of.
  P2 RELAXATION SPECTRUM — eigenvalues of (I + M): decay modes and
     their timescales in bars. A physical field shows a spectrum of
     relaxation times; noise shows none distinguishable.
  P3 IRREVERSIBILITY — persistent currents: the time-mean wedge per
     edge against a sign-flip surrogate. Nonzero steady currents =
     driven system (detailed balance broken); zero = equilibrium.
  P4 FIELD FORECAST — the falsifiable core: fit M on eras 1-2, then
     on virgin era 3 predict delta_rho(t) and score the cross-
     sectional correlation with the realized delta_rho(t), against
     (a) persistence (predict zero change) and (b) shuffled-M.
     The field either has capturable dynamics or it does not.

Universe: cohort A joint field, closed bars. Kernel untouched.
Usage: python tools/vtvr_field_dynamics.py
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.vtvr_structure_search import build_field  # noqa: E402


def _rng(tag):
    return np.random.default_rng(
        int.from_bytes(hashlib.sha256(tag.encode()).digest()[:8], "big"))


def fit_M(rho, t0, t1):
    """Least-squares delta_rho(t) = M rho(t-1) on bars [t0, t1);
    conservation enforced (zero column sums)."""
    X = rho[t0 - 1:t1 - 1]          # rho(t-1)
    Y = rho[t0:t1] - rho[t0 - 1:t1 - 1]
    M, *_ = np.linalg.lstsq(X, Y, rcond=None)
    M = M.T                          # so delta = M @ rho
    M -= M.mean(axis=0, keepdims=True)   # zero column sums
    return M


def op_sim(A, B):
    a, b = A.ravel(), B.ravel()
    return float(np.corrcoef(a, b)[0, 1])


def main():
    symbols, common, field, px_frac = build_field()
    n = len(symbols)
    m_total = len(common)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if common[-1][:10] == today:
        m_total -= 1
    rho = np.array([[float(v) for v in row] for row in field.xhat])[:m_total]
    print(f"Field: {n} vertices, {m_total} closed bars. "
          f"Conservation check: max |sum(rho)-1| = "
          f"{np.max(np.abs(rho.sum(axis=1) - 1)):.2e}")

    thirds = [(1, m_total // 3), (m_total // 3, 2 * m_total // 3),
              (2 * m_total // 3, m_total)]

    # ── P1: existence & stability ───────────────────────────────────────
    Ms = [fit_M(rho, a, b) for a, b in thirds]
    real_sims = [op_sim(Ms[0], Ms[1]), op_sim(Ms[1], Ms[2]),
                 op_sim(Ms[0], Ms[2])]

    sh_sims = []
    for trial in range(20):
        g = _rng(f"shuffle:{trial}")
        Mssh = []
        for a, b in thirds:
            idx = np.arange(a, b)
            perm = g.permutation(len(idx))
            X = rho[idx - 1]
            Y = (rho[idx] - rho[idx - 1])[perm]   # break the t pairing
            M, *_ = np.linalg.lstsq(X, Y, rcond=None)
            M = M.T
            M -= M.mean(axis=0, keepdims=True)
            Mssh.append(M)
        sh_sims += [op_sim(Mssh[0], Mssh[1]), op_sim(Mssh[1], Mssh[2]),
                    op_sim(Mssh[0], Mssh[2])]

    print()
    print("P1 OPERATOR STABILITY (era-to-era similarity of M):")
    print(f"  real eras:      {['%+.3f' % s for s in real_sims]}  "
          f"mean {np.mean(real_sims):+.3f}")
    print(f"  shuffled null:  mean {np.mean(sh_sims):+.3f} "
          f"(p95 {np.percentile(sh_sims, 95):+.3f}, 60 draws)")
    verdict1 = np.mean(real_sims) > np.percentile(sh_sims, 95)
    print(f"  → dynamics {'EXIST and persist' if verdict1 else 'NOT distinguishable from noise'}")

    # ── P2: relaxation spectrum ─────────────────────────────────────────
    M_all = fit_M(rho, 1, m_total)
    lam = np.linalg.eigvals(np.eye(n) + M_all)
    mod = np.sort(np.abs(lam))[::-1]
    taus = -1.0 / np.log(np.clip(mod[1:], 1e-9, 0.999999))
    print()
    print("P2 RELAXATION SPECTRUM (full-record operator):")
    print(f"  leading |eigenvalues|: {['%.4f' % v for v in mod[:6]]}")
    print(f"  implied decay times:   "
          f"{['%.0f bars' % t for t in taus[:5]]}")

    # ── P3: irreversibility (persistent currents) ───────────────────────
    edges = [(r.i, r.j) for r in field.relations[0]]
    e_count = len(edges)
    wedge = np.zeros((m_total, e_count))
    for t in range(m_total):
        row = field.relations[t]
        for e in range(e_count):
            wedge[t, e] = float(row[e].r_wedge)
    mean_w = wedge[1:].mean(axis=0)
    # sign-flip surrogate: currents under time-reversal symmetry
    thr = []
    for trial in range(200):
        g = _rng(f"flip:{trial}")
        signs = g.choice([-1.0, 1.0], size=m_total - 1)
        thr.append(np.abs((wedge[1:] * signs[:, None]).mean(axis=0)))
    thr95 = np.percentile(np.array(thr), 95, axis=0)
    sig = np.abs(mean_w) > thr95
    print()
    print("P3 IRREVERSIBILITY (steady pairwise currents):")
    print(f"  edges with persistent current beyond the time-reversal "
          f"null: {int(sig.sum())} of {e_count}")
    if sig.sum():
        order = np.argsort(-np.abs(mean_w) * sig)[:5]
        for e in order:
            if not sig[e]:
                continue
            i, j = edges[e]
            d = "→" if mean_w[e] > 0 else "←"
            print(f"    {symbols[i]} {d} {symbols[j]}  "
                  f"mean current {mean_w[e]:+.2e}")

    # ── P4: field forecast on the virgin era ────────────────────────────
    a3, b3 = thirds[2]
    M_fit = fit_M(rho, 1, thirds[1][1])          # eras 1-2 only
    cors, cors_null = [], []
    g = _rng("Mnull")
    M_shuf = M_fit.ravel()[g.permutation(n * n)].reshape(n, n)
    M_shuf -= M_shuf.mean(axis=0, keepdims=True)
    for t in range(a3, b3):
        pred = M_fit @ rho[t - 1]
        real = rho[t] - rho[t - 1]
        if np.std(pred) > 0 and np.std(real) > 0:
            cors.append(float(np.corrcoef(pred, real)[0, 1]))
        predn = M_shuf @ rho[t - 1]
        if np.std(predn) > 0 and np.std(real) > 0:
            cors_null.append(float(np.corrcoef(predn, real)[0, 1]))
    print()
    print("P4 FIELD FORECAST (fit eras 1-2, predict virgin era 3):")
    print(f"  mean corr(predicted Δρ, realized Δρ): {np.mean(cors):+.4f} "
          f"over {len(cors)} steps")
    print(f"  shuffled-operator null:               {np.mean(cors_null):+.4f}")
    print(f"  persistence null (predict no change):  0 by definition")
    se = np.std(cors) / max(len(cors), 1) ** 0.5
    print(f"  standard error: {se:.4f} → "
          f"{'the field HAS capturable dynamics' if np.mean(cors) > 2 * se and np.mean(cors) > np.mean(cors_null) + 2 * se else 'dynamics NOT captured by this operator'}")
    print()
    print("All measurements raw; nulls declared; no financial quantity "
          "appears anywhere above.")


if __name__ == "__main__":
    main()
