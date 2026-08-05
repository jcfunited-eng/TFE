"""
uf_core.layer3 — Resonance Engine (UF-Spec v1.4.0, Complete L3 Kernel)
=====================================================================

Implements the L3 resonance subsystem, as defined in UF-Spec v1.4.0:

Completed components in this module:
------------------------------------
- Resonance magnitude R_k  (normalized via Z = max numerator)
- Hysteresis Hyst_k        (instability detector)
- Gating g_k               (structural gating)
- Unified Resonance Field URF_k = g_k * R_k

NOT YET IMPLEMENTED (elsewhere in pipeline):
--------------------------------------------
- Cluster-level coherence metrics
- Any cognitive or semantic interpretations
"""

from dataclasses import dataclass
from typing import List

import numpy as np

from .layer2 import GateInterpretation
from .config import KERNEL_THRESHOLDS


# ---------------------------------------------------------------------------
# Hysteresis threshold (kernel parameter)
# ---------------------------------------------------------------------------

HYSTERESIS_THRESHOLD = 0.20  # h_max


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ResonanceResult:
    """
    Resonance result per gate.

    - interpretation: L2 GateInterpretation
    - R_k:            resonance magnitude in [0, 1]
    - Hyst_k:         hysteresis flag (0 or 1)
    - g_k:            gating flag (0 or 1)
    - URF_k:          gated resonance (Unified Resonance Field value)
    """
    interpretation: GateInterpretation
    R_k: float
    Hyst_k: int
    g_k: int
    URF_k: float


# ---------------------------------------------------------------------------
# Internal hysteresis computation
# ---------------------------------------------------------------------------

def _compute_hysteresis(R_list: List[float],
                        h_max: float = HYSTERESIS_THRESHOLD) -> List[int]:
    """
    Compute hysteresis flags Hyst_k using:

        Hyst_k = 1  iff  |R(k) - R(k-1)| > h_max
        Hyst_0 = 0
    """
    if not R_list:
        return []

    H = [0]  # Hyst_0 = 0
    for i in range(1, len(R_list)):
        delta = abs(R_list[i] - R_list[i - 1])
        H_k = 1 if delta > h_max else 0
        H.append(H_k)

    return H


# ---------------------------------------------------------------------------
# Resonance magnitude R_k
# ---------------------------------------------------------------------------

def _compute_raw_resonance(interpretations: List[GateInterpretation],
                           lambda1: float = 1.0,
                           lambda2: float = 1.0,
                           lambda3: float = 1.0,
                           lambda4: float = 1.0,
                           lambda5: float = 1.0) -> List[float]:
    """
    Compute raw resonance magnitudes R_k (without gating), normalized to [0, 1].

    num_k =
        λ1 * w_k
      + λ2 * (||CV_k|| / max_j ||CV_j||)
      + λ3 * S_k
      + λ4 * (1 / (1 + C_k))
      + λ5 * (1 - U_k)

    Z = max_k num_k
    R_k = num_k / Z
    """

    if not interpretations:
        return []

    w_arr = np.array([interp.w_k for interp in interpretations], dtype=float)
    S_arr = np.array([interp.S_k for interp in interpretations], dtype=float)
    U_arr = np.array([interp.U_k for interp in interpretations], dtype=float)

    CV_norms = np.array(
        [np.linalg.norm(np.array(interp.CV_k, dtype=float)) for interp in interpretations],
        dtype=float
    )
    max_cv_norm = float(np.max(CV_norms)) if CV_norms.size > 0 else 0.0
    eps = 1e-12

    # Pre-MLMA C_k = 1 → 1/(1 + C_k) = 1/2
    C_term = 0.5

    num_list = []
    for w_k, S_k, U_k, cv_n in zip(w_arr, S_arr, U_arr, CV_norms):
        term_w = lambda1 * w_k
        term_cv = lambda2 * (cv_n / (max_cv_norm + eps)) if max_cv_norm > 0 else 0.0
        term_s = lambda3 * S_k
        term_ck = lambda4 * C_term
        term_u = lambda5 * (1.0 - U_k)
        num_list.append(term_w + term_cv + term_s + term_ck + term_u)

    num_arr = np.array(num_list, dtype=float)
    Z = float(np.max(num_arr)) if num_arr.size > 0 else 0.0

    if Z <= 0.0:
        # Degenerate case: all numerators zero or negative
        return [0.0 for _ in interpretations]

    R_list = (num_arr / Z).tolist()
    return R_list


# ---------------------------------------------------------------------------
# Gating g_k and URF_k
# ---------------------------------------------------------------------------

def _compute_gating(interpretations: List[GateInterpretation],
                    Hyst_list: List[int],
                    U_max: float = None) -> List[int]:
    """
    Compute gating flags g_k using:

        g_k = 1  iff  (U_k <= U_max) and (IAS_k == 0) and (Hyst_k == 0)
              0  otherwise
    """

    if U_max is None:
        U_max = KERNEL_THRESHOLDS.U_max

    g_list: List[int] = []

    for interp, H_k in zip(interpretations, Hyst_list):
        U_k = interp.U_k
        IAS_k = interp.IAS_k

        if (U_k <= U_max) and (IAS_k == 0) and (H_k == 0):
            g_list.append(1)
        else:
            g_list.append(0)

    return g_list


def _compute_urf(R_list: List[float], g_list: List[int]) -> List[float]:
    """
    URF_k = g_k * R_k
    """
    return [float(R_k * g_k) for R_k, g_k in zip(R_list, g_list)]


# ---------------------------------------------------------------------------
# Public L3 API
# ---------------------------------------------------------------------------

def compute_resonance(interpretations: List[GateInterpretation],
                      lambda1: float = 1.0,
                      lambda2: float = 1.0,
                      lambda3: float = 1.0,
                      lambda4: float = 1.0,
                      lambda5: float = 1.0) -> List[ResonanceResult]:
    """
    Compute resonance magnitude, hysteresis, gating, and URF_k per gate.

    Pipeline:

    1) R_list  = _compute_raw_resonance(interpretations, λ₁..λ₅)
    2) Hyst    = _compute_hysteresis(R_list, h_max)
    3) g_list  = _compute_gating(interpretations, Hyst, U_max)
    4) URF     = g_k * R_k
    """

    if not interpretations:
        return []

    # 1) Raw resonance magnitudes
    R_list = _compute_raw_resonance(
        interpretations,
        lambda1=lambda1,
        lambda2=lambda2,
        lambda3=lambda3,
        lambda4=lambda4,
        lambda5=lambda5,
    )

    # 2) Hysteresis flags
    Hyst_list = _compute_hysteresis(R_list, HYSTERESIS_THRESHOLD)

    # 3) Gating flags
    g_list = _compute_gating(interpretations, Hyst_list, KERNEL_THRESHOLDS.U_max)

    # 4) URF_k
    URF_list = _compute_urf(R_list, g_list)

    # Build results
    results: List[ResonanceResult] = []
    for interp, R_k, H_k, g_k, URF_k in zip(interpretations, R_list, Hyst_list, g_list, URF_list):
        results.append(ResonanceResult(
            interpretation=interp,
            R_k=float(R_k),
            Hyst_k=int(H_k),
            g_k=int(g_k),
            URF_k=float(URF_k),
        ))

    return results
