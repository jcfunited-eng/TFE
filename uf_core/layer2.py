"""
uf_core.layer2 — Interpretive Layer (UF-Spec v1.4.0)
====================================================

Implements L2 components defined by UF-Spec v1.4.0:

Completed in this module:
-------------------------
- Baseline structural weight w_k
- Contrast vectors CV_k
- Structural significance score S_k
- Uncertainty U_k  ∈ [0, 1]
- Interpretive Anomaly Suppression IAS_k
- Regime classification Reg_k (STABLE, TRANSITIONAL, VOLATILE, DEGENERATE)

Regime classification uses:
- χ_k = S_k   (structural significance)
- ψ_k = U_k   (structural uncertainty)

NO domain semantics or TA are used here; regimes are purely structural.
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

# S_k is typically in [0, 1.5] for real data; these values ensure that
# all four regimes are meaningfully populated.
S_LOW  = 0.25
S_HIGH = 0.60
U_LOW  = 0.25
U_HIGH = 0.75  # ties naturally to KERNEL_THRESHOLDS.U_max


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
    - U_k:     uncertainty in [0, 1]
    - IAS_k:   interpretive anomaly suppression flag (0 or 1)
    - regime:  structural regime label (STABLE, TRANSITIONAL, VOLATILE, DEGENERATE)
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
    """
    Baseline structural weight:

        num = |ΔF̄_k| + σ̄_k + κ̄_k
        w_k = num / (1 + num)

    Ensures w_k ∈ [0, 1].
    """
    w_list = []
    for (_, dF_mean, sigma_mean, kappa_mean) in tvr_list:
        num = abs(dF_mean) + sigma_mean + kappa_mean
        den = 1.0 + num
        w_list.append(num / den if den > 0.0 else 0.0)
    return w_list


def _compute_S_k(w_list: List[float],
                 CV_list: List[np.ndarray],
                 C_k_list: List[float] = None,
                 gamma1: float = 1.0,
                 gamma2: float = 1.0,
                 gamma3: float = 1.0) -> List[float]:
    """
    Structural significance score S_k:

        Sk = γ1 * w_k
           + γ2 * (||CV_k|| / max_j ||CV_j||)
           + γ3 * (1 / (1 + C_k))

    Pre-MLMA: C_k = 1 for all gates.
    """
    if C_k_list is None:
        C_k_list = [1.0 for _ in w_list]  # pre-MLMA: C_k = 1

    norms = np.array([np.linalg.norm(cv) for cv in CV_list], dtype=float)
    max_norm = float(np.max(norms)) if norms.size > 0 else 0.0
    eps = 1e-12

    S_list: List[float] = []
    for i, w_k in enumerate(w_list):
        cv_norm = norms[i]
        C_k = C_k_list[i]

        term_w = gamma1 * w_k
        term_cv = gamma2 * (cv_norm / (max_norm + eps)) if max_norm > 0 else 0.0
        term_ck = gamma3 * (1.0 / (1.0 + C_k))

        S_list.append(term_w + term_cv + term_ck)

    return S_list


# ---------------------------------------------------------------------------
# U_k (uncertainty) computation — corrected to [0, 1]
# ---------------------------------------------------------------------------

def _compute_U_k(sev_series: List[SEV],
                 gates: List[Gate],
                 C_k_list: List[float] = None,
                 lambda2: float = 0.5,
                 lambda3: float = 0.5) -> List[float]:
    """
    Compute structural uncertainty U_k in [0, 1].

    Spec guidance (Section 5.9):
        U_k should reflect:
          - mosaic divergence / complexity,
          - gate drift,
          - negative-space occupancy.

    Pre-MLMA, we approximate:
        • C_k term omitted (always 1),
        • use normalized |ΔF| amplitude in gate,
        • penalize gates that intersect negative-space regions.

    Construction:

        delta_g_k = max_t |ΔF(t)| over gate k
        N_gate_k  = 1 if any N(t) = 1 in gate k else 0

        u_amp  = delta_g_k / max_j delta_g_j  ∈ [0, 1]
        u_neg  = N_gate_k                     ∈ {0, 1}

        U_k_raw = λ2 * u_amp + λ3 * u_neg

        U_k = clamp(U_k_raw, 0, 1)

    With λ2 = λ3 = 0.5, U_k ∈ [0, 1] by construction.
    """

    if not sev_series or not gates:
        return []

    # C_k_list kept for future MLMA, unused for now.
    if C_k_list is None:
        C_k_list = [1.0 for _ in gates]  # placeholder to stay structurally aligned

    dF_series = np.array([sev.dF for sev in sev_series], dtype=float)
    N_series = np.array([sev.N for sev in sev_series], dtype=int)

    delta_g_list: List[float] = []
    N_gate_list: List[float] = []

    for gate in gates:
        s, e = gate.start_idx, gate.end_idx
        seg_dF = dF_series[s:e+1]
        seg_N = N_series[s:e+1]

        delta_g = float(np.max(np.abs(seg_dF))) if len(seg_dF) > 0 else 0.0
        N_gate = 1.0 if np.any(seg_N == 1) else 0.0

        delta_g_list.append(delta_g)
        N_gate_list.append(N_gate)

    delta_max = max(delta_g_list) if delta_g_list else 1.0
    if delta_max == 0.0:
        delta_max = 1.0

    U_list: List[float] = []
    for delta_g, N_gate in zip(delta_g_list, N_gate_list):
        u_amp = float(delta_g / delta_max)  # ∈ [0, 1]
        u_neg = float(N_gate)              # ∈ {0, 1}

        U_raw = lambda2 * u_amp + lambda3 * u_neg
        U_k = max(0.0, min(1.0, U_raw))
        U_list.append(U_k)

    return U_list


# ---------------------------------------------------------------------------
# IAS_k (Interpretive Anomaly Suppression)
# ---------------------------------------------------------------------------

def _compute_IAS_k(U_list: List[float],
                   U_max: float = None) -> List[int]:
    """
    IAS_k = 1  iff  U_k > U_max
             0  otherwise

    With U_k ∈ [0, 1], IAS_k fires only for genuinely high-uncertainty gates,
    instead of most of the time.
    """

    if U_max is None:
        U_max = KERNEL_THRESHOLDS.U_max

    IAS_list: List[int] = []
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

    # U_k (now correctly in [0, 1])
    U_list = _compute_U_k(sev_series, gates)

    # IAS_k
    IAS_list = _compute_IAS_k(U_list, KERNEL_THRESHOLDS.U_max)

    # Reg_k
    regimes = [_classify_regime(S_k, U_k) for S_k, U_k in zip(S_list, U_list)]

    # Aggregate
    output: List[GateInterpretation] = []
    for gate, w_k, CV_vec, S_k, U_k, IAS_k, reg in zip(
        gates, w_list, CV_list, S_list, U_list, IAS_list, regimes
    ):
        CV_tuple = tuple(float(x) for x in CV_vec.tolist())
        output.append(
            GateInterpretation(
                gate=gate,
                w_k=float(w_k),
                CV_k=CV_tuple,
                S_k=float(S_k),
                U_k=float(U_k),
                IAS_k=int(IAS_k),
                regime=reg,
            )
        )

    return output
