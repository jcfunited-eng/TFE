"""
uf_core.layer3 — Resonance Engine (UF-Spec v1.4.0)
===================================================

L3 maps L2 ISF into resonance and gated resonance:
- R(k) = (1/Z) * (lambda1*w + lambda2*psi + lambda3*S + lambda4/(1+C) + lambda5*(1-U))
- Hyst_k = 1 iff |R(k)-R(k-1)| > h_max
- g_k = 1 iff U_k <= U_max and IAS_k == 0 and Hyst_k == 0
- URF_k = g_k * R(k)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from .config import KERNEL_THRESHOLDS
from .layer2 import GateInterpretation


@dataclass(frozen=True)
class ResonanceResult:
    gate: object
    R_k: float
    URF_k: float
    g_k: int
    U_k: float
    IAS_k: int
    Hyst_k: int
    interpretation: GateInterpretation
    raw_k: float


def _lambda_sum() -> float:
    z_val = (
        float(KERNEL_THRESHOLDS.lambda1)
        + float(KERNEL_THRESHOLDS.lambda2)
        + float(KERNEL_THRESHOLDS.lambda3)
        + float(KERNEL_THRESHOLDS.lambda4)
        + float(KERNEL_THRESHOLDS.lambda5)
    )
    if z_val <= 0.0:
        raise ValueError("Resonance normalization constant Z must be > 0.")
    return z_val


def compute_raw_resonance(interps: Sequence[GateInterpretation]) -> List[float]:
    """Compute unnormalized resonance numerators for each gate."""

    if not interps:
        return []

    l1 = float(KERNEL_THRESHOLDS.lambda1)
    l2 = float(KERNEL_THRESHOLDS.lambda2)
    l3 = float(KERNEL_THRESHOLDS.lambda3)
    l4 = float(KERNEL_THRESHOLDS.lambda4)
    l5 = float(KERNEL_THRESHOLDS.lambda5)

    cv_norms = np.array([float(np.linalg.norm(np.array(ip.CV_k, dtype=float))) for ip in interps], dtype=float)
    max_norm = float(np.max(cv_norms)) if cv_norms.size else 0.0

    raw: List[float] = []
    for ip, cv_norm in zip(interps, cv_norms):
        psi_k = (cv_norm / max_norm) if max_norm > 0.0 else 0.0
        ck_term = 1.0 / (1.0 + float(ip.C_k))

        value = (
            l1 * float(ip.w_k)
            + l2 * float(psi_k)
            + l3 * float(ip.S_k)
            + l4 * ck_term
            + l5 * (1.0 - float(ip.U_k))
        )
        raw.append(float(value))

    return raw


def normalize_resonance(raw_list: Sequence[float]) -> List[float]:
    """Normalize raw resonance by Z = sum(lambda_i)."""

    if not raw_list:
        return []

    z_val = _lambda_sum()
    out: List[float] = []
    for raw in raw_list:
        r_k = float(raw) / z_val
        out.append(float(max(0.0, min(1.0, r_k))))
    return out


def compute_hysteresis(R_list: Sequence[float]) -> List[int]:
    """Compute Hyst_k = 1 iff |R(k)-R(k-1)| > h_max (Hyst_0 = 0)."""

    if not R_list:
        return []

    h_max = float(KERNEL_THRESHOLDS.h_max)
    hyst: List[int] = [0]
    for i in range(1, len(R_list)):
        delta = abs(float(R_list[i]) - float(R_list[i - 1]))
        hyst.append(1 if delta > h_max else 0)
    return hyst


def compute_gating(interps: Sequence[GateInterpretation], hyst_list: Sequence[int]) -> List[int]:
    """Compute g_k from U_k, IAS_k, and Hyst_k."""

    if not interps:
        return []

    U_max = float(KERNEL_THRESHOLDS.U_max)
    out: List[int] = []

    for ip, Hyst_k in zip(interps, hyst_list):
        gate_open = (
            float(ip.U_k) <= U_max
            and int(ip.IAS_k) == 0
            and int(Hyst_k) == 0
        )
        out.append(1 if gate_open else 0)

    return out


def compute_resonance(interps: Sequence[GateInterpretation]) -> List[ResonanceResult]:
    """Run full L3 pipeline and return per-gate resonance results."""

    if not interps:
        return []

    raw_list = compute_raw_resonance(interps)
    R_list = normalize_resonance(raw_list)
    hyst_list = compute_hysteresis(R_list)
    g_list = compute_gating(interps, hyst_list)

    out: List[ResonanceResult] = []
    for ip, raw_k, R_k, Hyst_k, g_k in zip(interps, raw_list, R_list, hyst_list, g_list):
        URF_k = float(g_k) * float(R_k)
        out.append(
            ResonanceResult(
                gate=ip.gate,
                R_k=float(R_k),
                URF_k=float(URF_k),
                g_k=int(g_k),
                U_k=float(ip.U_k),
                IAS_k=int(ip.IAS_k),
                Hyst_k=int(Hyst_k),
                interpretation=ip,
                raw_k=float(raw_k),
            )
        )

    return out
