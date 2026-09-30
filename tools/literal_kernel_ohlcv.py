"""The literal spec kernel (standalone_truth_kernel.py, L0–L4 unchanged) fed
the field the canon describes: F(t) is the whole daily bar, the vector
(Open, High, Low, Close, Volume). Joe, 2026-09-30: "there should be Date,
Open, High, Low, Close, Volume" — "no wonder it is flat".

The canon writes norms — ||dF||, ||F − Fbar||², ||F(t+dt) − 2F(t) + F(t−dt)||
— and this file applies them to the 5-vector. Nothing is scaled, logged,
averaged over the history or normalized before the kernel. Where the
scalar file had to be generalized, the choice is marked MINE:
  MINE  r(t): psi_r on ||F|| (the scalar file compared F to its 10-bar mean).
  MINE  mu_k: the gate mean of (||dF||, sigma, kappa), so that CV_k = TVR_k − mu_k
        stays a 3-vector as in the scalar file (which used the signed dF).
Everything else is the scalar file's line, with abs(dF) → ||dF||.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from standalone_truth_kernel import (KernelParameters, GateL1, ISF, Resonance, DSFState,
                                     psi_s, phi_reg, psi_u, phi_ias,
                                     compute_l2_isf, compute_l3_resonance, compute_l4_dsf)


@dataclass
class SEV5:
    F: np.ndarray
    dF: np.ndarray
    ndF: float
    sigma: float
    kappa: float
    r: float
    N: int


def compute_l0_sev(F: np.ndarray, params: KernelParameters) -> List[SEV5]:
    """F: (n, 5) array of (Open, High, Low, Close, Volume)."""
    n = len(F)
    normF = np.linalg.norm(F, axis=1)
    sevs = []
    for t in range(n):
        dF = F[t] - F[t - 1] if t > 0 else np.zeros(F.shape[1])
        start_w = max(0, t - params.W + 1)
        win = F[start_w: t + 1]
        F_bar = win.mean(axis=0)
        sigma = float(np.mean(np.sum((win - F_bar) ** 2, axis=1)))
        kappa = float(np.linalg.norm(F[t + 1] - 2 * F[t] + F[t - 1])) if 0 < t < n - 1 else 0.0
        start_r = max(0, t - params.W_r + 1)
        rw = normF[start_r: t + 1]
        r_val = 1.0 if len(rw) > 0 and rw[-1] > np.mean(rw) else 0.5          # MINE: psi_r on ||F||
        ndF = float(np.linalg.norm(dF))
        N = 1 if (sigma < params.sigma_min and ndF < params.delta_min and kappa < params.kappa_min) else 0
        sevs.append(SEV5(F[t], dF, ndF, sigma, kappa, r_val, N))
    return sevs


def segment_l1_gates(sevs: List[SEV5], params: KernelParameters) -> List[GateL1]:
    D = np.array([params.alpha_1 * s.ndF + params.alpha_2 * s.sigma + params.alpha_3 * s.kappa for s in sevs])
    gates: List[GateL1] = []
    t_a = 0
    last_mu = np.zeros(3)
    for t in range(1, len(sevs)):
        if D[t] >= params.tau_D or t == len(sevs) - 1:
            t_b = t
            T = float(t_b - t_a)
            gate_sevs = sevs[t_a:t_b]
            if not gate_sevs:
                t_a = t
                continue
            V = sum(params.beta_1 * s.ndF + params.beta_2 * s.sigma + params.beta_3 * s.kappa for s in gate_sevs)
            R = sum(s.r for s in gate_sevs)
            TVR = (T, V, R)
            P_list = [(int(T // h1), int(V // h2), int(R // h3)) for h1, h2, h3 in params.lattices]
            C = len(set(P_list))
            mu_k = np.array([np.mean([s.ndF for s in gate_sevs]),                # MINE: ||dF|| in place of signed dF
                             np.mean([s.sigma for s in gate_sevs]),
                             np.mean([s.kappa for s in gate_sevs])])
            delta_g = float(np.linalg.norm(mu_k - last_mu))
            N_gate = 1 if all(s.N == 1 for s in gate_sevs) else 0
            gates.append(GateL1(t_a, t_b, TVR, P_list, C, delta_g, mu_k, N_gate))
            last_mu = mu_k
            t_a = t
    return gates


def run(F: np.ndarray, params: KernelParameters | None = None):
    params = params or KernelParameters()
    sevs = compute_l0_sev(F, params)
    gates = segment_l1_gates(sevs, params)
    isfs = compute_l2_isf(gates, params)
    res = compute_l3_resonance(isfs, params)
    dsfs = compute_l4_dsf(res, params)
    return sevs, gates, isfs, res, dsfs
