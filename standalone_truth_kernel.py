#!/usr/bin/env python3
"""
Literal Spec-Compliant TFE Kernel
---------------------------------
Direct mathematical translation of the TFE DSF-AI Specification (L0-L4).
No external heuristic feature engineering or `uf_core` dependencies.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import pandas as pd
import yfinance as yf


# ==============================================================================
# 0. KERNEL PARAMETERS & GREEK WEIGHTS
# ==============================================================================


@dataclass
class KernelParameters:
    # L0
    W: int = 20
    W_r: int = 10
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6

    # L1
    alpha_1: float = 1.0
    alpha_2: float = 1.0
    alpha_3: float = 1.0
    tau_D: float = 0.20

    beta_1: float = 1.0
    beta_2: float = 1.0
    beta_3: float = 1.0

    lattices: List[Tuple[float, float, float]] = field(
        default_factory=lambda: [(1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0)]
    )

    # L3
    lambda_1: float = 1.0
    lambda_2: float = 1.0
    lambda_3: float = 1.0
    lambda_4: float = 1.0
    lambda_5: float = 1.0
    h_max: float = 0.20
    U_max: float = 0.75

    # L4
    eps_D: float = 0.00073
    eta_H: float = 0.10
    eta_IAS: float = 0.10
    xi: float = 0.10
    chi: float = 0.10
    B_min: float = -1.0
    B_max: float = 1.0


# ==============================================================================
# 1. CANONICAL OPERATOR STUBS
# ==============================================================================


def psi_r(F_window: np.ndarray) -> float:
    """psi_r(F_c(t - W_r*Delta t : t)): Local state relevance operator."""
    return 1.0 if len(F_window) > 0 and F_window[-1] > np.mean(F_window) else 0.5


def psi_s(TVR: Tuple[float, float, float], P_list: List[Tuple[int, int, int]], C: int, delta_g: float) -> float:
    """psi_s: Domain-independent structural score."""
    T, V, R = TVR
    return float(np.clip(1.0 / (1.0 + C + delta_g), 0.0, 1.0))


def phi_reg(P_list: List[Tuple[int, int, int]], C: int) -> str:
    """phi_reg: Ordering-invariant structural regime classification."""
    return "TRANSITIONAL" if C > 1 else "STABLE"


def psi_u(C: int, delta_g: float, N_gate: int) -> float:
    """psi_u: Structural uncertainty."""
    return float(np.clip((C * 0.1) + (delta_g * 0.1) + (N_gate * 0.2), 0.0, 1.0))


def phi_ias(S: float, U: float, delta_g: float) -> int:
    """phi_ias: Interpretive anomaly or instability flag."""
    return 1 if U > 0.8 or delta_g > 2.0 else 0


# ==============================================================================
# 2. L0: STRUCTURAL EVALUATION VECTOR
# ==============================================================================


@dataclass
class SEV:
    F: float
    dF: float
    sigma: float
    kappa: float
    r: float
    N: int


def compute_l0_sev(F: np.ndarray, params: KernelParameters) -> List[SEV]:
    n = len(F)
    sevs = []

    for t in range(n):
        dF = F[t] - F[t - 1] if t > 0 else 0.0

        start_w = max(0, t - params.W + 1)
        F_window = F[start_w : t + 1]
        F_bar = np.mean(F_window)
        sigma = np.mean((F_window - F_bar) ** 2)

        if 0 < t < n - 1:
            kappa = abs(F[t + 1] - 2 * F[t] + F[t - 1])
        else:
            kappa = 0.0

        start_r = max(0, t - params.W_r + 1)
        r_val = psi_r(F[start_r : t + 1])

        N = 1 if (sigma < params.sigma_min and abs(dF) < params.delta_min and kappa < params.kappa_min) else 0

        sevs.append(SEV(F[t], dF, sigma, kappa, r_val, N))

    return sevs


# ==============================================================================
# 3. L1: GATE SEGMENTATION & QUANTIZATION
# ==============================================================================


@dataclass
class GateL1:
    t_a: int
    t_b: int
    TVR: Tuple[float, float, float]
    P_list: List[Tuple[int, int, int]]
    C: int
    delta_g: float
    mu: np.ndarray
    N_gate: int


def segment_l1_gates(sevs: List[SEV], params: KernelParameters) -> List[GateL1]:
    D = np.zeros(len(sevs))
    for t, sev in enumerate(sevs):
        D[t] = params.alpha_1 * abs(sev.dF) + params.alpha_2 * sev.sigma + params.alpha_3 * sev.kappa

    gates = []
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

            V = sum(params.beta_1 * abs(s.dF) + params.beta_2 * s.sigma + params.beta_3 * s.kappa for s in gate_sevs)
            R = sum(s.r for s in gate_sevs)
            TVR = (T, V, R)

            P_list = []
            for h1, h2, h3 in params.lattices:
                P_list.append((int(T // h1), int(V // h2), int(R // h3)))
            C = len(set(P_list))

            mu_k = np.array(
                [
                    np.mean([s.dF for s in gate_sevs]),
                    np.mean([s.sigma for s in gate_sevs]),
                    np.mean([s.kappa for s in gate_sevs]),
                ]
            )
            delta_g = float(np.linalg.norm(mu_k - last_mu))

            N_gate = 1 if all(s.N == 1 for s in gate_sevs) else 0

            gates.append(GateL1(t_a, t_b, TVR, P_list, C, delta_g, mu_k, N_gate))

            last_mu = mu_k
            t_a = t

    return gates


# ==============================================================================
# 4. L2: INTERPRETIVE STRUCTURAL FIELD
# ==============================================================================


@dataclass
class ISF:
    gate: GateL1
    w: float
    CV: np.ndarray
    S: float
    Reg: str
    U: float
    IAS: int


def compute_l2_isf(gates: List[GateL1], params: KernelParameters) -> List[ISF]:
    if not gates:
        return []

    V_max = max((g.TVR[1] for g in gates), default=1e-12)
    V_max = V_max if V_max > 0 else 1e-12

    isfs = []
    for g in gates:
        w_k = g.TVR[1] / V_max
        CV_k = np.array(g.TVR) - g.mu
        S_k = psi_s(g.TVR, g.P_list, g.C, g.delta_g)
        Reg_k = phi_reg(g.P_list, g.C)
        U_k = psi_u(g.C, g.delta_g, g.N_gate)
        IAS_k = phi_ias(S_k, U_k, g.delta_g)

        isfs.append(ISF(g, w_k, CV_k, S_k, Reg_k, U_k, IAS_k))

    return isfs


# ==============================================================================
# 5. L3: RESONANCE ENGINE
# ==============================================================================


@dataclass
class Resonance:
    isf: ISF
    R: float
    Hyst: int
    g: int
    URF: float


def compute_l3_resonance(isfs: List[ISF], params: KernelParameters) -> List[Resonance]:
    if not isfs:
        return []

    Z = params.lambda_1 + params.lambda_2 + params.lambda_3 + params.lambda_4 + params.lambda_5
    CV_max = max((np.linalg.norm(isf.CV) for isf in isfs), default=1e-12)
    CV_max = CV_max if CV_max > 0 else 1e-12

    res = []
    last_R = 0.0

    for isf in isfs:
        term1 = params.lambda_1 * isf.w
        term2 = params.lambda_2 * (np.linalg.norm(isf.CV) / CV_max)
        term3 = params.lambda_3 * isf.S
        term4 = params.lambda_4 * (1.0 / (1.0 + isf.gate.C))
        term5 = params.lambda_5 * (1.0 - isf.U)

        R_k = (1.0 / Z) * (term1 + term2 + term3 + term4 + term5)
        Hyst_k = 1 if abs(R_k - last_R) > params.h_max else 0
        g_k = 1 if (isf.U <= params.U_max and isf.IAS == 0 and Hyst_k == 0) else 0
        URF_k = g_k * R_k

        res.append(Resonance(isf, R_k, Hyst_k, g_k, URF_k))
        last_R = R_k

    return res


# ==============================================================================
# 6. L4: DECISION STATE FIELD
# ==============================================================================


@dataclass
class DSFState:
    D: int
    M: float
    Rev: int
    U_star: float
    C: int
    P: int
    B: float


def compute_l4_dsf(res: List[Resonance], params: KernelParameters) -> List[DSFState]:
    dsfs = []
    last_URF, last_URF2 = 0.0, 0.0
    last_D = 0
    last_B = 0.0

    for r in res:
        delta_R = r.URF - last_URF

        if delta_R > params.eps_D:
            D_k = 1
        elif delta_R < -params.eps_D:
            D_k = -1
        else:
            D_k = 0

        M_k = r.URF - 2 * last_URF + last_URF2
        Rev_k = 1 if (D_k * last_D < 0) else 0

        U_star_k = r.isf.U + (params.eta_H * r.Hyst) + (params.eta_IAS * r.isf.IAS)
        P_k = abs(D_k - last_D)

        B_k_raw = last_B + params.xi * (1 - U_star_k) * delta_R - params.chi * U_star_k
        B_k = float(np.clip(B_k_raw, params.B_min, params.B_max))

        dsfs.append(DSFState(D_k, M_k, Rev_k, U_star_k, r.isf.gate.C, P_k, B_k))

        last_URF2 = last_URF
        last_URF = r.URF
        last_D = D_k
        last_B = B_k

    return dsfs


# ==============================================================================
# EXECUTION (YFINANCE INGESTION)
# ==============================================================================


if __name__ == "__main__":
    symbols = sys.argv[1:] if len(sys.argv) > 1 else ["AAOI"]

    results = []
    for sym in symbols:
        data = yf.download(sym, period="1y", interval="1d", progress=False)
        if data.empty:
            continue

        if isinstance(data.columns, pd.MultiIndex):
            close_prices = data["Close"].squeeze().values
        else:
            close_prices = data["Close"].values

        params = KernelParameters()
        sevs = compute_l0_sev(close_prices, params)
        gates = segment_l1_gates(sevs, params)
        isfs = compute_l2_isf(gates, params)
        resonances = compute_l3_resonance(isfs, params)
        dsfs = compute_l4_dsf(resonances, params)

        if dsfs:
            final_dsf = dsfs[-1]
            prev_B = dsfs[-2].B if len(dsfs) > 1 else 0.0

            if (final_dsf.D >= 0) and (final_dsf.Rev == 0) and (final_dsf.B > prev_B) and (final_dsf.M >= 0):
                l5_decision = "ACCUMULATE"
            else:
                l5_decision = "HOLD/AVOID"

            results.append(
                {
                    "symbol": sym,
                    "D_k": final_dsf.D,
                    "M_k": round(final_dsf.M, 6),
                    "Rev_k": final_dsf.Rev,
                    "U_star_k": round(final_dsf.U_star, 6),
                    "C_k": final_dsf.C,
                    "P_k": final_dsf.P,
                    "B_k": round(final_dsf.B, 6),
                    "L5_Decision": l5_decision,
                }
            )

    print(json.dumps(results, indent=2))
