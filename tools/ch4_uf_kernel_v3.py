"""
ch4_uf_kernel_v3.py — v3: the spatial field axis restored (side channel)
========================================================================

UF-Spec v1.3.0 §2.3/§11.1 defines SEV(t) = [x_1(t),…,x_n(t), Δx, σ, R, N]
— the FIELD IS MULTI-COMPONENT. Every financial realization to date
(deployed, lineage, v1, v2) flattened x to the closing price alone. The
original four axes are T, V, R, S — and S (spatial configuration) was
never implemented. For a daily bar, the spatial configuration IS the bar
geometry.

DECLARED (before measurement):
  x(t)  = (log O, log H, log L, log C)   — the bar's spatial vector
          (log per §2.4 normalization; the S axis restored)
  Δx    = x(t) − x(t−1); magnitude ‖Δx‖ used where v2 used |ΔF|
  σ(t)  = trailing-W mean of ‖x − x̄_win‖² (trace variance, W=20)
  κ(t)  = ‖x(t+1) − 2·x(t) + x(t−1)‖ (vector curvature, endpoint rule)
  r(t)  = volume attention (as v2, H3)
  N(t)  = σ<1e-6 ∧ ‖Δx‖<1e-6 ∧ κ<1e-6 (pinned minima)
  Gate  = adaptive ‖ΔSEV‖ boundary exactly as v2, over the concatenated
          SEV [x(4), ‖Δx‖, σ, κ, r, N] (9 components) ∨ N-flip
  Gate content (T, V=Σ(‖Δx‖+σ+κ), R=Σr, lattices, C, δ_g over the
          (‖Δx‖, σ, κ) means, N_gate) — GateV2-shaped, so the ENTIRE
          v2 chain (L2→L5, all channels) is reused verbatim: no
          re-implementation, no new constants.

Causality: identical no-cheat law; all windows trail; endpoint-κ rule;
assert_causal_v3 re-derives sampled days from truncated OHLCV.
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.ch4_uf_kernel_v2 import (  # noqa: E402  (reused verbatim)
    ChainV2,
    DayStateV2,
    GateV2,
    EPS_LOG,
    LATTICES,
    W,
    W_R,
    SELF_CHECK_EVERY,
    step_chain_v2,
)


class L0V3:
    __slots__ = ("X", "dX_mag", "sigma", "kappa", "r", "N", "boundary",
                 "perV", "cs_perV", "cs_r", "cs_dxm", "cs_sigma",
                 "cs_kappa", "cs_N")


def compute_l0_v3(o, h, l, c, volumes) -> L0V3:
    X = np.log(np.stack([o, h, l, c], axis=1).astype(float) + EPS_LOG)  # (n,4)
    n = X.shape[0]
    dX = np.zeros_like(X)
    if n > 1:
        dX[1:] = np.diff(X, axis=0)
    dX_mag = np.linalg.norm(dX, axis=1)

    sigma = np.zeros(n)
    for t in range(n):
        w0 = max(0, t - W + 1)
        win = X[w0: t + 1]
        mu = win.mean(axis=0)
        sigma[t] = float(np.mean(np.sum((win - mu) ** 2, axis=1)))

    kappa = np.zeros(n)
    if n > 2:
        kappa[1: n - 1] = np.linalg.norm(X[2:] - 2.0 * X[1: n - 1] + X[: n - 2], axis=1)

    r = np.ones(n)
    if volumes is not None:
        v = volumes.astype(float)
        for t in range(n):
            w0 = max(0, t - W_R + 1)
            med = float(np.median(v[w0: t + 1]))
            r[t] = (v[t] / med) if med > 0 else 1.0

    N = ((sigma < 1e-6) & (dX_mag < 1e-6) & (kappa < 1e-6)).astype(np.int64)

    # adaptive boundary: step over concatenated SEV [x(4), ‖Δx‖, σ, κ, r, N]
    step2 = np.zeros(n)
    for t in range(1, n):
        d = float(np.sum((X[t] - X[t - 1]) ** 2))
        d += (dX_mag[t] - dX_mag[t - 1]) ** 2
        d += (sigma[t] - sigma[t - 1]) ** 2
        d += (kappa[t] - kappa[t - 1]) ** 2
        d += (r[t] - r[t - 1]) ** 2
        d += float(N[t] - N[t - 1]) ** 2
        step2[t] = d
    boundary = np.zeros(n, dtype=bool)
    for t in range(1, n - 1):
        w0 = max(1, t - W)
        trail = step2[w0:t]
        thresh = float(np.mean(trail)) if len(trail) else 0.0
        boundary[t] = (step2[t] > thresh) or (N[t] != N[t - 1])

    perV = dX_mag + sigma + kappa

    out = L0V3()
    out.X = X
    out.dX_mag = dX_mag
    out.sigma = sigma
    out.kappa = kappa
    out.r = r
    out.N = N
    out.boundary = boundary
    out.perV = perV

    def cs(a):
        z = np.zeros(n + 1)
        np.cumsum(a, out=z[1:])
        return z

    out.cs_perV = cs(perV)
    out.cs_r = cs(r)
    out.cs_dxm = cs(dX_mag)
    out.cs_sigma = cs(sigma)
    out.cs_kappa = cs(kappa)
    out.cs_N = cs(N.astype(float))
    return out


def gate_from_span_v3(l0: L0V3, t_a: int, t_b: int, last_mu: np.ndarray) -> GateV2:
    ln = t_b - t_a
    T = float(ln)
    V = float(l0.cs_perV[t_b] - l0.cs_perV[t_a])
    R = float(l0.cs_r[t_b] - l0.cs_r[t_a])
    P_list = tuple((int(T // h1), int(V // h2), int(R // h3))
                   for h1, h2, h3 in LATTICES)
    C = len(set(P_list))
    mu = np.array([
        (l0.cs_dxm[t_b] - l0.cs_dxm[t_a]) / ln,
        (l0.cs_sigma[t_b] - l0.cs_sigma[t_a]) / ln,
        (l0.cs_kappa[t_b] - l0.cs_kappa[t_a]) / ln,
    ])
    delta_g = float(np.linalg.norm(mu - last_mu))
    N_gate = 1 if (l0.cs_N[t_b] - l0.cs_N[t_a]) == ln else 0
    return GateV2(t_a, t_b, T, V, R, C, delta_g,
                  (float(mu[0]), float(mu[1]), float(mu[2])), N_gate,
                  sigma_g=float(mu[1]), kappa_g=float(mu[2]),
                  r_g=R / ln if ln else 1.0)


def replay_symbol_v3(dates: Sequence, o, h, l, c, volumes=None,
                     warmup: int = 60) -> List[Optional[DayStateV2]]:
    o = np.asarray(o, dtype=float)
    h = np.asarray(h, dtype=float)
    l = np.asarray(l, dtype=float)
    c = np.asarray(c, dtype=float)
    n = len(c)
    vols = np.asarray(volumes, dtype=float) if volumes is not None else None
    dates_ord = np.array([np.datetime64(d, "D").astype("int64") for d in dates],
                         dtype="float64")
    l0 = compute_l0_v3(o, h, l, c, vols)
    bounds = np.flatnonzero(l0.boundary)

    closed: List[GateV2] = []
    base = ChainV2()
    out: List[Optional[DayStateV2]] = [None] * n
    made = 0
    for t in range(warmup, n):
        valid_upto = int(np.searchsorted(bounds, t))
        while made < valid_upto:
            b = int(bounds[made])
            t_a = int(bounds[made - 1]) if made >= 1 else 0
            last_mu = np.array(closed[-1].mu) if closed else np.zeros(3)
            gg = gate_from_span_v3(l0, t_a, b, last_mu)
            closed.append(gg)
            step_chain_v2(base, gg, dates_ord[b])
            made += 1
        t_a = int(closed[-1].t_b) if closed else 0
        if t <= t_a:
            out[t] = None
            continue
        last_mu = np.array(closed[-1].mu) if closed else np.zeros(3)
        final_gate = gate_from_span_v3(l0, t_a, t, last_mu)
        st_day = base.copy()
        out[t] = step_chain_v2(st_day, final_gate, dates_ord[t])

        if (t - warmup) % SELF_CHECK_EVERY == 0 or t == n - 1:
            st_ref = ChainV2()
            for gg in closed:
                step_chain_v2(st_ref, gg, dates_ord[gg.t_b])
            ref = step_chain_v2(st_ref, final_gate, dates_ord[t])
            got = out[t]
            if not (ref.action == got.action and abs(ref.Q_20 - got.Q_20) < 1e-9
                    and abs(ref.F_n - got.F_n) < 1e-9):
                raise AssertionError(f"v3 self-check divergence at t={t}")
    return out


def assert_causal_v3(dates, o, h, l, c, volumes, states, sample) -> None:
    for t in sample:
        if states[t] is None:
            continue
        redo = replay_symbol_v3(
            dates[: t + 1], o[: t + 1], h[: t + 1], l[: t + 1], c[: t + 1],
            volumes[: t + 1] if volumes is not None else None, warmup=t)[t]
        assert redo is not None, f"v3 causality: no state at t={t}"
        ok = (redo.action == states[t].action
              and redo.ignition == states[t].ignition
              and redo.extinction == states[t].extinction
              and abs(redo.F_n - states[t].F_n) < 1e-9
              and redo.gate_count == states[t].gate_count)
        assert ok, f"V3 CAUSALITY VIOLATION t={t}"
