"""
uf_core.layer2 — Interpretive Layer (UF-Spec v1.4.0)
====================================================

Implements L2 components defined by UF-Spec v1.4.0:

Completed in this module:
-------------------------
- Baseline structural weight w_k
- Contrast vectors CV_k
- Structural significance score S_k
- Uncertainty U_k
- Interpretive Anomaly Suppression IAS_k
- Regime classification Reg_k (STABLE, TRANSITIONAL, VOLATILE, DEGENERATE)

Regime classification uses:
- χ_k = S_k
- ψ_k = U_k

NO cognitive semantics are used here; regimes are purely structural.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .layer1 import Gate, compute_gate_tvr
from .layer0 import SEV
from .config import KERNEL_THRESHOLDS


# ---------------------------------------------------------------------------
# Regime thresholds (structural, kernel-level defaults)
# ---------------------------------------------------------------------------

# These values are kernel parameters and MUST be calibrated via Section 13.
# They are local here to keep this step to a single file change.
S_LOW = 1.0
S_HIGH = 2.0
U_LOW = 0.3
U_HIGH = 0.8  # ties naturally to KERNEL_THRESHOLDS.U_max


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GateInterpretation:
    """
    L2 interpretation for a single gate:

    - gate:    gate index range
    - w_k:     baseline structural weight
    - CV_k:    contrast vector from TVR_k - μ
    - S_k:     structural significance
    - U_k:     uncertainty
    - IAS_k:   interpretive anomaly suppression flag (0 or 1)
    - regime:  structural regime label (one of STABLE, TRANSITIONAL, VOLATILE, DEGENERATE)
    """
    gate: Gate
    w_k: float
    CV_k: Tuple[float, float, float, float]
    S_k: float
    U_k: float
    IAS_k: int
    regime: str


# ---------------------------------------------------------------------------
# Helper functions for TVR-based interpretation
# ---------------------------------------------------------------------------

def _compute_global_mean_tvr(tvr_list: List[Tuple[float, float, float, float]]) -> np.ndarray:
    if not tvr_list:
        return np.zeros(4, dtype=float)
    return np.mean(np.array(tvr_list, dtype=float), axis=0)


def _compute_CV_vectors(tvr_list: List[Tuple[float, float, float, float]],
                        mu: np.ndarray) -> List[np.ndarray]:
    return [np.array(tvr, dtype=float) - mu for tvr in tvr_list]


def _compute_w_k(tvr_list: List[Tuple[float, float, float, float]]) -> List[float]:
    w_list = []
    for (_, dF_mean, sigma_mean, kappa_mean) in tvr_list:
        num = abs(dF_mean) + sigma_mean + kappa_mean
        den = 1.0 + num
        w_list.append(num / den if den > 0 else 0.0)
    return w_list


def _compute_S_k(w_list: List[float],
                 CV_list: List[np.ndarray],
                 C_k_list: List[float] = None,
                 gamma1: float = 1.0,
                 gamma2: float = 1.0,
                 gamma3: float = 1.0) -> List[float]:

    if C_k_list is None:
        C_k_list = [1.0 for _ in w_list]  # pre-MLMA: C_k = 1

    norms = np.array([np.linalg.norm(cv) for cv in CV_list], dtype=float)
    max_norm = float(np.max(norms)) if norms.size > 0 else 0.0
    eps = 1e-12

    S_list = []
    for i, w_k in enumerate(w_list):
        cv_norm = norms[i]
        C_k = C_k_list[i]

        term_w = gamma1 * w_k
        term_cv = gamma2 * (cv_norm / (max_norm + eps)) if max_norm > 0 else 0.0
        term_ck = gamma3 * (1.0 / (1.0 + C_k))

        S_list.append(term_w + term_cv + term_ck)

    return S_list


# ---------------------------------------------------------------------------
# U_k (uncertainty) computation
# ---------------------------------------------------------------------------

def _compute_U_k(sev_series: List[SEV],
                 gates: List[Gate],
                 C_k_list: List[float] = None,
                 lambda1: float = 0.0,
                 lambda2: float = 1.0,
                 lambda3: float = 1.0) -> List[float]:

    if not sev_series or not gates:
        return []

    if C_k_list is None:
        C_k_list = [1.0 for _ in gates]  # pre-MLMA: C_k = 1

    dF_series = np.array([sev.dF for sev in sev_series], dtype=float)
    N_series = np.array([sev.N for sev in sev_series], dtype=int)

    delta_g_list = []
    N_gate_list = []

    for gate in gates:
        s, e = gate.start_idx, gate.end_idx
        seg_dF = dF_series[s:e+1]
        seg_N = N_series[s:e+1]

        delta_g = float(np.max(np.abs(seg_dF))) if len(seg_dF) > 0 else 0.0
        N_gate = 1.0 if np.any(seg_N == 1) else 0.0

        delta_g_list.append(delta_g)
        N_gate_list.append(N_gate)

    delta_max = max(delta_g_list) if delta_g_list else 1.0
    if delta_max == 0:
        delta_max = 1.0

    U_list = []
    for i in range(len(gates)):
        # First term = 0 because C_k=1 pre-MLMA
        term1 = 0.0
        term2 = lambda2 * (delta_g_list[i] / delta_max)
        term3 = lambda3 * N_gate_list[i]
        U_list.append(term1 + term2 + term3)

    return U_list


# ---------------------------------------------------------------------------
# IAS_k (Interpretive Anomaly Suppression)
# ---------------------------------------------------------------------------

def _compute_IAS_k(U_list: List[float],
                   U_max: float = None) -> List[int]:
    """
    IAS_k = 1  iff  U_k > U_max
             0  otherwise
    """

    if U_max is None:
        U_max = KERNEL_THRESHOLDS.U_max

    IAS_list = []
    for U_k in U_list:
        IAS_k = 1 if U_k > U_max else 0
        IAS_list.append(IAS_k)

    return IAS_list


# ---------------------------------------------------------------------------
# Regime classification (Reg_k)
# ---------------------------------------------------------------------------

def _classify_regime(S_k: float, U_k: float) -> str:
    """
    Classify regime based on (χ_k, ψ_k) = (S_k, U_k):

    - STABLE:       S_k >= S_HIGH and U_k <= U_LOW
    - DEGENERATE:   S_k <= S_LOW  and U_k >= U_HIGH
    - VOLATILE:     S_k >= S_HIGH and U_k >= U_HIGH
    - TRANSITIONAL: everything else
    """
    if S_k >= S_HIGH and U_k <= U_LOW:
        return "STABLE"
    if S_k <= S_LOW and U_k >= U_HIGH:
        return "DEGENERATE"
    if S_k >= S_HIGH and U_k >= U_HIGH:
        return "VOLATILE"
    return "TRANSITIONAL"


# ---------------------------------------------------------------------------
# Public L2 API
# ---------------------------------------------------------------------------

def interpret_gates(sev_series: List[SEV],
                    gates: List[Gate]) -> List[GateInterpretation]:

    if not sev_series or not gates:
        return []

    # TVR_k
    tvr_list = compute_gate_tvr(sev_series, gates)

    # μ (mean TVR)
    mu = _compute_global_mean_tvr(tvr_list)

    # CV_k
    CV_list = _compute_CV_vectors(tvr_list, mu)

    # w_k
    w_list = _compute_w_k(tvr_list)

    # S_k
    S_list = _compute_S_k(w_list, CV_list)

    # U_k
    U_list = _compute_U_k(sev_series, gates)

    # IAS_k
    IAS_list = _compute_IAS_k(U_list, KERNEL_THRESHOLDS.U_max)

    # Reg_k
    regimes = [_classify_regime(S_k, U_k) for S_k, U_k in zip(S_list, U_list)]

    # Aggregate
    output: List[GateInterpretation] = []
    for gate, w_k, CV_vec, S_k, U_k, IAS_k, reg in zip(gates, w_list, CV_list, S_list, U_list, IAS_list, regimes):
        CV_tuple = tuple(float(x) for x in CV_vec.tolist())
        output.append(GateInterpretation(
            gate=gate,
            w_k=w_k,
            CV_k=CV_tuple,
            S_k=S_k,
            U_k=U_k,
            IAS_k=IAS_k,
            regime=reg
        ))

    return output
