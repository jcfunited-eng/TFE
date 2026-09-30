"""The canon kernel (tools/canon_kernel.py) as a single causal pass.

The reading on day t is the kernel run on the bars through t. The canon
kernel's only history-wide operations are maxima over gates (chi_max,
||CV||_max, delta_max) and the recurrences in L3/L4 (Hyst, B). In a prefix
through t those maxima are maxima over the gates in the prefix, i.e. the
running maxima. So one pass with running maxima reproduces the prefix
readings exactly — verified against the prefix loop by
tools/verify_causal_pass.py before this file was used for anything.

Gate k here is bar k−1 (the literal L1 excludes the boundary bar from the
gate and every bar is a boundary on the raw bar field), so the reading on
day t describes bar t−1 with everything known at the close of t.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.modules.setdefault("yfinance", types.ModuleType("yfinance"))
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from uf_core.config import KERNEL_THRESHOLDS as KT   # noqa: E402  (gamma, lambda_u, U_max, h_max, eps_D, eta, xi, chi, B bounds)

FIELDS = ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k", "R_k", "URF_k", "g_k", "Hyst_k",
          "w_k", "psi_k", "S_k", "U_k", "IAS_k", "regime", "T_k", "V_k", "delta_g"]
LATTICES = ((1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0))


def readings(F: np.ndarray, tau_D: float | str = 0.20, W: int = 20, c: float = 3.77) -> pd.DataFrame:
    """F: (n, m) field, one row per bar. Returns one row per day t >= 2 (the
    first day with a finished gate), each the causal reading on that day.

    tau_D: a number (the canon's fixed threshold, 0.20) or "own" — the
    resolution consideration (HIS: per ticker by its scale; MINE: the
    setting): tau_D(t) = c x the median of D over the trailing 252 bars
    ending at t-1 (expanding median during the first year). Causal."""
    n = len(F)
    # ---- L0 on the vector (literal file's operators) ----
    dF = np.zeros_like(F); dF[1:] = F[1:] - F[:-1]
    ndF = np.linalg.norm(dF, axis=1)
    sigma = np.zeros(n)
    for t in range(n):
        win = F[max(0, t - W + 1): t + 1]
        sigma[t] = float(np.mean(np.sum((win - win.mean(axis=0)) ** 2, axis=1)))
    kappa = np.zeros(n)
    kappa[1:-1] = np.linalg.norm(F[2:] - 2 * F[1:-1] + F[:-2], axis=1)
    N = ((sigma < 1e-6) & (ndF < 1e-6) & (kappa < 1e-6)).astype(int)
    D = ndF + sigma + kappa
    # ---- L1: boundaries D >= tau_D; gate = [t_a, t_b) ----
    if tau_D == "own":
        tau = pd.Series(D).shift(1).rolling(252, min_periods=20).median().values * c
        tau = np.where(np.isfinite(tau), tau, np.inf)
    else:
        tau = np.full(n, float(tau_D))
    bounds = [t for t in range(1, n) if D[t] >= tau[t]]
    if not bounds or bounds[-1] != n - 1:
        bounds.append(n - 1)
    rows = []
    t_a = 0
    chi_max = cv_max = d_max = 0.0
    R_prev = 0.0; URF_prev = URF_prev2 = 0.0; D_prev = 0; B_prev = 0.0
    mu_prev = np.zeros(3)
    for t_b in bounds:
        if t_b <= t_a:
            continue
        sl = slice(t_a, t_b)
        T = float(t_b - t_a)
        V = float(np.sum(ndF[sl] + sigma[sl] + kappa[sl]))
        Rr = float(T)                                     # relevance r = 1 per bar
        P_list = [(int(T // h1), int(V // h2), int(Rr // h3)) for h1, h2, h3 in LATTICES]
        C = len(set(P_list))
        mu = np.array([ndF[sl].mean(), sigma[sl].mean(), kappa[sl].mean()])
        delta_g = float(np.linalg.norm(mu - mu_prev))
        N_gate = int(N[sl].all())
        # ---- L2 with running maxima (what a prefix run sees) ----
        chi = V / max(T, 1e-12)
        chi_max = max(chi_max, chi)
        w = min(1.0, max(0.0, chi / chi_max)) if chi_max > 0 else 0.0
        cv = np.array([T, V, Rr]) - mu
        cvn = float(np.linalg.norm(cv))
        cv_max = max(cv_max, cvn)
        psi = min(1.0, max(0.0, cvn / cv_max)) if cv_max > 0 else 0.0
        d_max = max(d_max, delta_g)
        S = min(1.0, max(0.0, KT.gamma1 * w + KT.gamma2 * psi + KT.gamma3 / (1.0 + C)))
        L = len(LATTICES)
        U = min(1.0, max(0.0, KT.lambda_u1 * (C - 1) / (L - 1) + KT.lambda_u2 * (delta_g / d_max if d_max > 0 else 0.0) + KT.lambda_u3 * N_gate))
        IAS = int(U > KT.U_max)
        regime = ("DEGENERATE" if psi > KT.psi_max else "STABLE" if (chi < KT.chi_min and psi < KT.psi_min)
                  else "VOLATILE" if chi > KT.chi_max else "TRANSITIONAL")
        # ---- L3 ----
        Rk = min(1.0, max(0.0, (KT.lambda1 * w + KT.lambda2 * psi + KT.lambda3 * S + KT.lambda4 / (1.0 + C) + KT.lambda5 * (1.0 - U))
                                / (KT.lambda1 + KT.lambda2 + KT.lambda3 + KT.lambda4 + KT.lambda5)))
        Hyst = int(abs(Rk - R_prev) > KT.h_max) if rows else 0
        g = int(U <= KT.U_max and IAS == 0 and Hyst == 0)
        URF = g * Rk
        # ---- L4 ----
        dR = URF - URF_prev if rows else 0.0
        Dk = 1 if dR > KT.epsilon_D else -1 if dR < -KT.epsilon_D else 0
        if not rows:
            Dk = 0
        M = URF - 2 * URF_prev + URF_prev2 if len(rows) >= 2 else 0.0
        Rev = int(Dk * D_prev < 0)
        Ustar = min(1.0, max(0.0, U + KT.eta_H * Hyst + KT.eta_IAS * IAS))
        Pk = abs(Dk - D_prev)
        B = float(np.clip(B_prev + KT.breath_xi * (1.0 - Ustar) * dR - KT.breath_chi * Ustar, KT.B_min, KT.B_max))
        rows.append((t_b, Dk, M, Rev, Ustar, C, Pk, B, Rk, URF, g, Hyst, w, psi, S, U, IAS, regime, T, V, delta_g))
        R_prev = Rk; URF_prev2 = URF_prev; URF_prev = URF; D_prev = Dk; B_prev = B; mu_prev = mu
        t_a = t_b
    return pd.DataFrame(rows, columns=["t"] + FIELDS)
