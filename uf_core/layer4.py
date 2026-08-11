"""
uf_core.layer4 — Decision Dynamics (UF-Spec v1.4.0)
====================================================

L4 consumes URF_k from L3 and emits DSF_k.

Implemented equations:
- D_k from fixed epsilon_D and delta R
- M_k = R_k - 2R_{k-1} + R_{k-2}
- R_rev_k = 1 iff D_k * D_{k-1} < 0
- U*_k = clamp(U_k + eta_H*Hyst_k + eta_IAS*IAS_k)
- P_k = |D_k - D_{k-1}|
- B_k = clamp(B_{k-1} + xi*(1-U*_k)*deltaR - chi*U*_k)

Note: DSF includes C_k in-kernel. The TFE decision vector remains a domain
adapter projection and is preserved in uf_structural_engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Union

import numpy as np

from .config import KERNEL_THRESHOLDS
from .layer1 import Gate
from .layer3 import ResonanceResult


Number = Union[float, int]
ArrayLike = Union[np.ndarray, Number]


EPSILON_D: float = float(KERNEL_THRESHOLDS.epsilon_D)
B_MIN: float = float(KERNEL_THRESHOLDS.B_min)
B_MAX: float = float(KERNEL_THRESHOLDS.B_max)
XI: float = float(KERNEL_THRESHOLDS.breath_xi)
CHI: float = float(KERNEL_THRESHOLDS.breath_chi)
ETA_H: float = float(KERNEL_THRESHOLDS.eta_H)
ETA_IAS: float = float(KERNEL_THRESHOLDS.eta_IAS)


@dataclass(frozen=True)
class DecisionState:
    gate: Gate
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    C_k: float
    P_k: float
    B_k: float


@dataclass(frozen=True)
class DSF:
    gate: Gate
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    C_k: float
    P_k: float
    B_k: float


def _clamp(value: float, vmin: float, vmax: float) -> float:
    return float(max(vmin, min(vmax, value)))


def compute_directional_signal(resonance_results: List[ResonanceResult]) -> List[DecisionState]:
    """Compute L4 state sequence from L3 resonance results."""

    n = len(resonance_results)
    if n == 0:
        return []

    # L4 input signal from L3 is URF_k = g_k * R_k.
    R_tilde = np.array([float(r.URF_k) for r in resonance_results], dtype=float)

    U_vals = np.array([float(r.U_k) for r in resonance_results], dtype=float)
    IAS_vals = np.array([int(r.IAS_k) for r in resonance_results], dtype=int)
    Hyst_vals = np.array([int(r.Hyst_k) for r in resonance_results], dtype=int)
    C_vals = np.array([float(r.interpretation.C_k) for r in resonance_results], dtype=float)

    D = np.zeros(n, dtype=float)
    M = np.zeros(n, dtype=float)
    R_rev = np.zeros(n, dtype=float)
    U_star = np.zeros(n, dtype=float)
    P = np.zeros(n, dtype=float)
    B = np.zeros(n, dtype=float)

    B[0] = _clamp(0.0, B_MIN, B_MAX)
    U_star[0] = _clamp(U_vals[0] + ETA_H * Hyst_vals[0] + ETA_IAS * IAS_vals[0], 0.0, 1.0)
    P[0] = 0.0

    for k in range(1, n):
        delta_R = R_tilde[k] - R_tilde[k - 1]

        if delta_R > EPSILON_D:
            D[k] = 1.0
        elif delta_R < -EPSILON_D:
            D[k] = -1.0
        else:
            D[k] = 0.0

        if k >= 2:
            M[k] = R_tilde[k] - 2.0 * R_tilde[k - 1] + R_tilde[k - 2]
        else:
            M[k] = 0.0

        R_rev[k] = 1.0 if (D[k] * D[k - 1] < 0.0) else 0.0

        U_star[k] = _clamp(
            U_vals[k] + ETA_H * Hyst_vals[k] + ETA_IAS * IAS_vals[k],
            0.0,
            1.0,
        )

        P[k] = abs(D[k] - D[k - 1])

        B_k = B[k - 1] + XI * (1.0 - U_star[k]) * delta_R - CHI * U_star[k]
        B[k] = _clamp(B_k, B_MIN, B_MAX)

    out: List[DecisionState] = []
    for idx, r in enumerate(resonance_results):
        out.append(
            DecisionState(
                gate=r.gate,
                D_k=float(D[idx]),
                M_k=float(M[idx]),
                R_rev_k=float(R_rev[idx]),
                U_star_k=float(U_star[idx]),
                C_k=float(C_vals[idx]),
                P_k=float(P[idx]),
                B_k=float(B[idx]),
            )
        )

    return out


def compute_dsf(decision_states: List[DecisionState]) -> List[DSF]:
    """Map DecisionState -> DSF one-to-one."""

    out: List[DSF] = []
    for ds in decision_states:
        out.append(
            DSF(
                gate=ds.gate,
                D_k=float(ds.D_k),
                M_k=float(ds.M_k),
                R_rev_k=float(ds.R_rev_k),
                U_star_k=float(ds.U_star_k),
                C_k=float(ds.C_k),
                P_k=float(ds.P_k),
                B_k=float(ds.B_k),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Optional hardening utility (kept for compatibility)
# ---------------------------------------------------------------------------

A_LOWER: float = 0.20
B_UPPER: float = 0.70


@dataclass(frozen=True)
class Layer4Raw:
    D: ArrayLike
    M: ArrayLike
    P: ArrayLike
    B: ArrayLike
    R: ArrayLike


@dataclass(frozen=True)
class Layer4Hardened:
    D: np.ndarray
    M: np.ndarray
    P: np.ndarray
    B: np.ndarray
    R: np.ndarray
    s: np.ndarray


def _to_ndarray(x: ArrayLike, dtype=float) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x.astype(dtype, copy=False)
    return np.asarray(x, dtype=dtype)


def hardening_factor(R: ArrayLike, a: float = A_LOWER, b: float = B_UPPER) -> np.ndarray:
    R_arr = _to_ndarray(R, dtype=float)

    if not (0.0 <= a < b <= 1.0):
        raise ValueError(f"Invalid hardening parameters: require 0 <= a < b <= 1, got a={a}, b={b}")

    s = np.zeros_like(R_arr, dtype=float)

    mid_mask = (R_arr > a) & (R_arr < b)
    s[mid_mask] = (R_arr[mid_mask] - a) / (b - a)

    high_mask = R_arr >= b
    s[high_mask] = 1.0

    return s


def apply_hardening(raw: Layer4Raw, a: float = A_LOWER, b: float = B_UPPER) -> Layer4Hardened:
    D = _to_ndarray(raw.D, dtype=float)
    M = _to_ndarray(raw.M, dtype=float)
    P = _to_ndarray(raw.P, dtype=float)
    B = _to_ndarray(raw.B, dtype=float)
    R = _to_ndarray(raw.R, dtype=float)

    try:
        s = hardening_factor(R, a=a, b=b)
        D_h = D * s
        M_h = M * s
        P_h = P * s
        B_h = B * s
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Layer 4 hardening failed due to shape or integration mismatch: {exc}") from exc

    return Layer4Hardened(D=D_h, M=M_h, P=P_h, B=B_h, R=R, s=s)


def harden_fields(
    D: ArrayLike,
    M: ArrayLike,
    P: ArrayLike,
    B: ArrayLike,
    R: ArrayLike,
    a: float = A_LOWER,
    b: float = B_UPPER,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    raw = Layer4Raw(D=D, M=M, P=P, B=B, R=R)
    hardened = apply_hardening(raw, a=a, b=b)
    return hardened.D, hardened.M, hardened.P, hardened.B, hardened.s
