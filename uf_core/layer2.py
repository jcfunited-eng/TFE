"""
uf_core.layer2 — Interpretive Structural Metrics (UF-Spec v1.4.0)
==================================================================

L2 consumes full L1 descriptors and produces:
ISF_k = (w_k, CV_k, S_k, Reg_k, U_k, IAS_k)

Implemented per spec:
- CV_k = TVR_k - mu_k
- S_k = g1*w_k + g2*||CV_k||/||CV||_max + g3*(1/(1 + C_k))
- U_k = l1*((C_k-1)/(L-1)) + l2*(delta_g/delta_max) + l3*N(G_k)
- IAS_k = 1 iff U_k > U_max
- Reg_k partitions over (chi_k, psi_k)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

from .config import KERNEL_THRESHOLDS
from .layer0 import SEV
from .layer1 import Gate, TVR, build_gate_l1_state


@dataclass(frozen=True)
class GateInterpretation:
    gate: Gate
    w_k: float
    CV_k: Tuple[float, float, float]
    S_k: float
    U_k: float
    IAS_k: int
    regime: str
    C_k: int
    delta_g: float
    N_gate: int
    T_k: float
    V_k: float
    R_k: float
    chi_k: float
    psi_k: float


def _compute_global_mean_tvr(tvr_list: Sequence[TVR]) -> np.ndarray:
    if not tvr_list:
        return np.zeros(3, dtype=float)
    return np.mean(np.array(tvr_list, dtype=float), axis=0)


def _compute_CV_vectors(tvr_list: Sequence[TVR], mu: np.ndarray) -> List[np.ndarray]:
    return [np.array(tvr, dtype=float) - mu for tvr in tvr_list]


def _compute_density(tvr_list: Sequence[TVR]) -> List[float]:
    out: List[float] = []
    for T_k, V_k, _ in tvr_list:
        denom = max(float(T_k), 1e-12)
        out.append(float(V_k) / denom)
    return out


def _compute_w_k_from_density(chi_list: Sequence[float]) -> List[float]:
    if not chi_list:
        return []

    max_chi = max(float(x) for x in chi_list)
    if max_chi <= 0:
        return [0.0 for _ in chi_list]

    out: List[float] = []
    for chi_k in chi_list:
        w_k = float(chi_k) / max_chi
        out.append(float(max(0.0, min(1.0, w_k))))
    return out


def _compute_psi(CV_list: Sequence[np.ndarray]) -> Tuple[List[float], float]:
    if not CV_list:
        return [], 0.0

    norms = np.array([float(np.linalg.norm(cv)) for cv in CV_list], dtype=float)
    max_norm = float(np.max(norms)) if norms.size else 0.0

    if max_norm <= 0:
        return [0.0 for _ in CV_list], 0.0

    psi_list = [float(max(0.0, min(1.0, n / max_norm))) for n in norms]
    return psi_list, max_norm


def _compute_S_k(
    w_list: Sequence[float],
    psi_list: Sequence[float],
    C_k_list: Sequence[int],
) -> List[float]:
    g1 = float(KERNEL_THRESHOLDS.gamma1)
    g2 = float(KERNEL_THRESHOLDS.gamma2)
    g3 = float(KERNEL_THRESHOLDS.gamma3)

    S_list: List[float] = []
    for w_k, psi_k, C_k in zip(w_list, psi_list, C_k_list):
        ck_term = 1.0 / (1.0 + float(C_k))
        S_k = g1 * float(w_k) + g2 * float(psi_k) + g3 * ck_term
        S_list.append(float(max(0.0, min(1.0, S_k))))

    return S_list


def _compute_U_k(
    C_k_list: Sequence[int],
    delta_g_list: Sequence[float],
    N_gate_list: Sequence[int],
) -> List[float]:
    l1 = float(KERNEL_THRESHOLDS.lambda_u1)
    l2 = float(KERNEL_THRESHOLDS.lambda_u2)
    l3 = float(KERNEL_THRESHOLDS.lambda_u3)

    lattice_count = int(len(getattr(KERNEL_THRESHOLDS, "mosaic_lattices", (1,))))
    denom_L = max(1, lattice_count - 1)

    delta_max = max((float(x) for x in delta_g_list), default=0.0)
    if delta_max <= 0.0:
        delta_max = 1.0

    U_list: List[float] = []
    for C_k, delta_g, N_gate in zip(C_k_list, delta_g_list, N_gate_list):
        if lattice_count <= 1:
            c_term = 0.0
        else:
            c_term = (float(C_k) - 1.0) / float(denom_L)

        drift_term = float(delta_g) / delta_max
        neg_term = float(int(N_gate))

        U_raw = l1 * c_term + l2 * drift_term + l3 * neg_term
        U_list.append(float(max(0.0, min(1.0, U_raw))))

    return U_list


def _compute_IAS_k(U_list: Sequence[float]) -> List[int]:
    U_max = float(KERNEL_THRESHOLDS.U_max)
    return [1 if float(U_k) > U_max else 0 for U_k in U_list]


def _classify_regime(chi_k: float, psi_k: float) -> str:
    chi_min = float(KERNEL_THRESHOLDS.chi_min)
    chi_max = float(KERNEL_THRESHOLDS.chi_max)
    psi_min = float(KERNEL_THRESHOLDS.psi_min)
    psi_max = float(KERNEL_THRESHOLDS.psi_max)

    if float(psi_k) > psi_max:
        return "DEGENERATE"
    if float(chi_k) < chi_min and float(psi_k) < psi_min:
        return "STABLE"
    if float(chi_k) > chi_max:
        return "VOLATILE"
    return "TRANSITIONAL"


def interpret_gates(sev_series: Sequence[SEV], gates: Sequence[Gate]) -> List[GateInterpretation]:
    if not sev_series or not gates:
        return []

    l1_state = build_gate_l1_state(sev_series, gates)
    if not l1_state:
        return []

    tvr_list = [entry.tvr for entry in l1_state]
    C_k_list = [entry.C_k for entry in l1_state]
    delta_g_list = [entry.delta_g for entry in l1_state]
    N_gate_list = [entry.N_gate for entry in l1_state]

    mu = _compute_global_mean_tvr(tvr_list)
    CV_list = _compute_CV_vectors(tvr_list, mu)

    chi_list = _compute_density(tvr_list)
    w_list = _compute_w_k_from_density(chi_list)
    psi_list, _ = _compute_psi(CV_list)

    S_list = _compute_S_k(w_list, psi_list, C_k_list)
    U_list = _compute_U_k(C_k_list, delta_g_list, N_gate_list)
    IAS_list = _compute_IAS_k(U_list)
    regimes = [_classify_regime(chi_k, psi_k) for chi_k, psi_k in zip(chi_list, psi_list)]

    out: List[GateInterpretation] = []
    for entry, cv, w_k, S_k, U_k, IAS_k, regime, chi_k, psi_k in zip(
        l1_state,
        CV_list,
        w_list,
        S_list,
        U_list,
        IAS_list,
        regimes,
        chi_list,
        psi_list,
    ):
        T_k, V_k, R_k = entry.tvr
        out.append(
            GateInterpretation(
                gate=entry.gate,
                w_k=float(w_k),
                CV_k=(float(cv[0]), float(cv[1]), float(cv[2])),
                S_k=float(S_k),
                U_k=float(U_k),
                IAS_k=int(IAS_k),
                regime=regime,
                C_k=int(entry.C_k),
                delta_g=float(entry.delta_g),
                N_gate=int(entry.N_gate),
                T_k=float(T_k),
                V_k=float(V_k),
                R_k=float(R_k),
                chi_k=float(chi_k),
                psi_k=float(psi_k),
            )
        )

    return out
