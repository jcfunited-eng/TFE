"""
uf_core.layer3 — Resonance Layer (UF-Spec v1.4.0)
=================================================

Implements UF-Core L3 resonance as defined structurally by the Spec:

Given each gate interpretation (L2):
    w_k      – baseline structural weight
    CV_k     – contrast vector (4D)
    S_k      – structural significance
    U_k      – uncertainty in [0, 1]
    IAS_k    – interpretive anomaly suppression
    Hyst_k   – hysteresis flag

Resonance R_k:
--------------
UF-Spec v1.4.0 defines resonance R_k as a composite of:
    • structural weight                      (w_k)
    • contrast magnitude                     (||CV_k||)
    • structural significance                (S_k)
    • uncertainty penalty                    (1 - U_k)
    • base cohesion term                     (1 / (1 + C_k))  with pre-MLMA C_k = 1

Spec-compliant normalized form:

    raw_k = ( λ1 * w_k )
          + ( λ2 * (||CV_k|| / max_j ||CV_j||) )
          + ( λ3 * S_k )
          + ( λ4 * (1 / (1 + C_k)) )
          + ( λ5 * (1 - U_k) )

    R_k = raw_k / max_j raw_j       if max_j raw_j > 0
          0                         otherwise

Gating g_k:
-----------
UF-Spec v1.4.0 Section 6.5:

    g_k = 1  iff (U_k <= U_max) AND (IAS_k == 0) AND (Hyst_k == 0)
           0  otherwise

Effective resonance:
    URF_k = g_k * R_k

This file provides:
-------------------
• ResonanceResult dataclass
• compute_raw_resonance()     – Spec-compliant raw_k and R_k
• compute_gating()            – Spec gating logic
• compute_resonance()         – full L3 pipeline producing R_k, URF_k, Hyst_k, etc.

NO TA. NO domain hacks. Pure structural UF-Core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from .config import KERNEL_THRESHOLDS
from .layer2 import GateInterpretation


# ============================================================
# Resonance Result Structure
# ============================================================

@dataclass
class ResonanceResult:
    """
    L3 resonance state for a single gate:

    gate       : Gate index range
    R_k        : normalized resonance in [0, 1]
    URF_k      : gated resonance (g_k · R_k)
    g_k        : gating mask (0 or 1)

    U_k        : L2 uncertainty for reference
    IAS_k      : anomaly flag
    Hyst_k     : hysteresis flag

    interpretation : the L2 GateInterpretation object
    raw_k     : raw composite resonance score before normalization
    """
    gate: any
    R_k: float
    URF_k: float
    g_k: int
    U_k: float
    IAS_k: int
    Hyst_k: int
    interpretation: GateInterpretation
    raw_k: float


# ============================================================
# Resonance computation
# ============================================================

def compute_raw_resonance(interps: List[GateInterpretation]) -> List[float]:
    """
    Compute raw_k according to Spec Section 6.

    raw_k = λ1 * w_k
          + λ2 * (||CV_k|| / max ||CV||)
          + λ3 * S_k
          + λ4 * (1 / (1 + C_k))       with C_k = 1  (pre-MLMA)
          + λ5 * (1 - U_k)

    All terms ∈ [0, 1], except S_k which may exceed 1 but is scaled by λ3.
    """

    if not interps:
        return []

    λ1 = KERNEL_THRESHOLDS.lambda1
    λ2 = KERNEL_THRESHOLDS.lambda2
    λ3 = KERNEL_THRESHOLDS.lambda3
    λ4 = KERNEL_THRESHOLDS.lambda4
    λ5 = KERNEL_THRESHOLDS.lambda5

    # Compute CV norms and max norm
    CV_norms = np.array([np.linalg.norm(ip.CV_k) for ip in interps], dtype=float)
    max_norm = float(np.max(CV_norms)) if CV_norms.size > 0 else 0.0
    eps = 1e-12

    raw_list = []

    for ip in interps:
        w_k = float(ip.w_k)
        CV_k = np.array(ip.CV_k, dtype=float)
        S_k = float(ip.S_k)
        U_k = float(ip.U_k)

        term1 = λ1 * w_k
        term2 = λ2 * (np.linalg.norm(CV_k) / (max_norm + eps)) if max_norm > 0 else 0.0
        term3 = λ3 * S_k
        term4 = λ4 * (1.0 / (1.0 + 1.0))     # since C_k = 1 pre-MLMA
        term5 = λ5 * (1.0 - U_k)

        raw_k = term1 + term2 + term3 + term4 + term5
        raw_list.append(raw_k)

    return raw_list


def normalize_resonance(raw_list: List[float]) -> List[float]:
    """
    Normalize raw_k values to R_k ∈ [0, 1].

    R_k = raw_k / max(raw_list)
    """
    if not raw_list:
        return []

    max_raw = max(raw_list)
    if max_raw <= 0:
        return [0.0 for _ in raw_list]

    return [float(r / max_raw) for r in raw_list]


def compute_gating(interps: List[GateInterpretation]) -> List[int]:
    """
    Spec gating:

        g_k = 1  iff  U_k <= U_max  AND IAS_k == 0  AND Hyst_k == 0
             0  otherwise
    """

    if not interps:
        return []

    U_max = KERNEL_THRESHOLDS.U_max
    g_list = []

    for ip in interps:
        U_k = float(ip.U_k)
        IAS_k = int(ip.IAS_k)
        Hyst_k = int(getattr(ip, "Hyst_k", 0))  # L2 doesn't assign Hyst; L3 will update later

        if (U_k <= U_max) and (IAS_k == 0) and (Hyst_k == 0):
            g_list.append(1)
        else:
            g_list.append(0)

    return g_list


# ============================================================
# MAIN RESONANCE PIPELINE
# ============================================================

def compute_resonance(interps: List[GateInterpretation]) -> List[ResonanceResult]:
    """
    Full L3 pipeline:

        1. Compute raw_k
        2. Compute normalized R_k
        3. Compute gating g_k
        4. Apply URF_k = g_k * R_k
        5. Pass hysteresis flags from interpretations (if present)
    """

    if not interps:
        return []

    raw_list = compute_raw_resonance(interps)
    R_list = normalize_resonance(raw_list)
    g_list = compute_gating(interps)

    results: List[ResonanceResult] = []

    # Hysteresis flag from L2 regime transitions:
    # This uses change in regime as proxy for Hyst signal (Structural Spec practice)
    Hyst_vals = []
    prev_reg = None
    for ip in interps:
        curr_reg = ip.regime
        if prev_reg is None:
            Hyst_vals.append(0)
        else:
            Hyst_vals.append(1 if curr_reg != prev_reg else 0)
        prev_reg = curr_reg

    for ip, raw_k, R_k, g_k, Hyst_k in zip(interps, raw_list, R_list, g_list, Hyst_vals):
        U_k = float(ip.U_k)
        IAS_k = int(ip.IAS_k)
        URF_k = float(g_k) * float(R_k)

        results.append(
            ResonanceResult(
                gate=ip.gate,
                R_k=float(R_k),
                URF_k=float(URF_k),
                g_k=int(g_k),
                U_k=U_k,
                IAS_k=IAS_k,
                Hyst_k=int(Hyst_k),
                interpretation=ip,
                raw_k=float(raw_k),
            )
        )

    return results
