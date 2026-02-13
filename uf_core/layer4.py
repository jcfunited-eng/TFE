"""
uf_core.layer4 — Decision State Fields (DSF) + Hardening (with adaptive epsilon_D)
==================================================================================

Implements:
  • Spec-compliant DSF (L4) as in UF-Spec v1.4.0 Section 7.
  • Piecewise-linear hardening operator (reliability → softening factor).
  • Adaptive epsilon_D per symbol:

        epsilon_D_eff = epsilon_D * (1 + alpha_eps * sigma_delta_R)

    where:
        delta_R_k = R_tilde_k - R_tilde_{k-1}
        sigma_delta_R = std({delta_R_k})

    This does NOT change the D_k formula, only how epsilon_D is instantiated.

    D_k =
        +1  if  ΔR(k) >  epsilon_D_eff
         0  if |ΔR(k)| ≤ epsilon_D_eff
        -1  if  ΔR(k) < -epsilon_D_eff

    This is a domain-conditioning variant of UF-Core L4, not the canonical fixed
    epsilon_D baseline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Union, Any

import numpy as np

from .layer1 import Gate
from .layer3 import ResonanceResult
from .config import KERNEL_THRESHOLDS  # kernel thresholds and parameters


Number = Union[float, int]
ArrayLike = Union[np.ndarray, Number]


# ---------------------------------------------------------------------------
# L4 / DSF parameters from config (with safe defaults)
# ---------------------------------------------------------------------------

EPSILON_D: float = getattr(KERNEL_THRESHOLDS, "epsilon_D", 0.01)

# Adaptive scaling factor for epsilon_D; if not present, default = 1.0
ALPHA_EPS: float = getattr(KERNEL_THRESHOLDS, "epsilon_D_alpha", 1.0)

B_MIN: float = getattr(KERNEL_THRESHOLDS, "B_min", -1.0)
B_MAX: float = getattr(KERNEL_THRESHOLDS, "B_max", 1.0)

XI: float = getattr(KERNEL_THRESHOLDS, "breath_xi", 0.10)
CHI: float = getattr(KERNEL_THRESHOLDS, "breath_chi", 0.10)

ETA_H: float = getattr(KERNEL_THRESHOLDS, "eta_H", 0.1)
ETA_IAS: float = getattr(KERNEL_THRESHOLDS, "eta_IAS", 0.1)


# ---------------------------------------------------------------------------
# L4 Data structures
# ---------------------------------------------------------------------------

@dataclass
class DecisionState:
    """
    Intermediate L4 decision dynamics state (per gate).

    gate      : Gate index range from L1
    D_k       : directional component in {-1, 0, +1}
    M_k       : momentum component
    R_rev_k   : reversal flag (0 or 1)
    U_star_k  : adjusted uncertainty in [0, 1]
    P_k       : pressure = |D_k - D_{k-1}|
    B_k       : breathing state, clamped to [B_min, B_max]
    """
    gate: Gate
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    P_k: float
    B_k: float


@dataclass
class DSF:
    """
    Decision State Field (DSF) object as consumed by:

        • uf_structural_engine.compute_uf_structural_state
        • uf_core.hardening_controller.hardening_control_step
        • uf_core.safemode

    Structurally identical to DecisionState; separated for clarity and
    future extension.
    """
    gate: Gate
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    P_k: float
    B_k: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, vmin: float, vmax: float) -> float:
    return float(max(vmin, min(vmax, value)))


# ---------------------------------------------------------------------------
# L4 – Spec DSF + adaptive epsilon_D
# ---------------------------------------------------------------------------

def compute_directional_signal(resonance_results: List[ResonanceResult]) -> List[DecisionState]:
    """
    Compute L4 DecisionState sequence from L3 resonance results.

    Spec mapping (UF-Spec v1.4.0 Section 7):

        ΔR(k) = R_tilde(k) − R_tilde(k−1)

        D_k = +1  if  ΔR(k) >  epsilon_D_eff
              0   if |ΔR(k)| ≤ epsilon_D_eff
             −1  if  ΔR(k) < −epsilon_D_eff

        M_k = R_tilde(k) − 2 R_tilde(k−1) + R_tilde(k−2)
        R_rev_k = 1  iff  D_k D_{k−1} < 0  else 0
        U*_k = U_k + η_H · Hyst_k + η_IAS · IAS_k  (clamped to [0,1])
        P_k = |D_k − D_{k−1}|
        B_k = B_{k−1} + ξ (1 − U*_k) ΔR(k) − χ U*_k, with clamping

    Here:
        • R_tilde = URF_k = g_k · R_k from L3.
        • U_k, IAS_k, Hyst_k are taken from ResonanceResult / L2.

    Adaptive epsilon_D:
        epsilon_D_eff = EPSILON_D * (1 + ALPHA_EPS * sigma_delta_R)

        where sigma_delta_R = std of ΔR over the entire symbol window.
    """

    n = len(resonance_results)
    if n == 0:
        return []

    # Effective resonance for L4: URF_k (already gated by g_k in L3)
    R_tilde = np.array([float(r.URF_k) for r in resonance_results], dtype=float)

    # L2 inputs
    U_vals = np.array([float(r.U_k) for r in resonance_results], dtype=float)
    IAS_vals = np.array([int(r.IAS_k) for r in resonance_results], dtype=int)
    Hyst_vals = np.array([int(r.Hyst_k) for r in resonance_results], dtype=int)

    # Adaptive epsilon_D based on resonance volatility
    if n >= 2:
        delta_R_arr = np.diff(R_tilde)
        sigma_delta_R = float(np.std(delta_R_arr))
    else:
        sigma_delta_R = 0.0

    epsilon_D_eff = EPSILON_D * (1.0 + ALPHA_EPS * sigma_delta_R)

    # Initialize sequences
    D = np.zeros(n, dtype=float)
    M = np.zeros(n, dtype=float)
    R_rev = np.zeros(n, dtype=float)
    U_star = np.zeros(n, dtype=float)
    P = np.zeros(n, dtype=float)
    B = np.zeros(n, dtype=float)

    # Initial breathing state
    B[0] = _clamp(0.0, B_MIN, B_MAX)

    # k = 0 initialization
    U_star[0] = _clamp(U_vals[0] + ETA_H * Hyst_vals[0] + ETA_IAS * IAS_vals[0], 0.0, 1.0)
    P[0] = 0.0

    # Main DSF loop
    for k in range(1, n):
        # ΔR(k)
        delta_R = R_tilde[k] - R_tilde[k - 1]

        # Direction D_k with adaptive epsilon_D_eff
        if delta_R > epsilon_D_eff:
            D[k] = 1.0
        elif delta_R < -epsilon_D_eff:
            D[k] = -1.0
        else:
            D[k] = 0.0

        # Momentum M_k
        if k >= 2:
            M[k] = R_tilde[k] - 2.0 * R_tilde[k - 1] + R_tilde[k - 2]
        else:
            M[k] = 0.0

        # Reversal flag R_rev_k
        if D[k] * D[k - 1] < 0.0:
            R_rev[k] = 1.0
        else:
            R_rev[k] = 0.0

        # Adjusted uncertainty U*_k
        u_base = U_vals[k]
        hyst_term = ETA_H * Hyst_vals[k]
        ias_term = ETA_IAS * IAS_vals[k]
        U_star[k] = _clamp(u_base + hyst_term + ias_term, 0.0, 1.0)

        # Pressure P_k
        P[k] = abs(D[k] - D[k - 1])

        # Breathing B_k with clamping
        B_k_prev = B[k - 1]
        B_k = B_k_prev + XI * (1.0 - U_star[k]) * delta_R - CHI * U_star[k]
        B[k] = _clamp(B_k, B_MIN, B_MAX)

    # Build DecisionState list
    decision_states: List[DecisionState] = []
    for idx, r in enumerate(resonance_results):
        decision_states.append(
            DecisionState(
                gate=r.gate,
                D_k=float(D[idx]),
                M_k=float(M[idx]),
                R_rev_k=float(R_rev[idx]),
                U_star_k=float(U_star[idx]),
                P_k=float(P[idx]),
                B_k=float(B[idx]),
            )
        )

    return decision_states


def compute_dsf(decision_states: List[DecisionState]) -> List[DSF]:
    """
    Map DecisionState → DSF 1:1.
    """
    dsf_list: List[DSF] = []

    for ds in decision_states:
        dsf_list.append(
            DSF(
                gate=ds.gate,
                D_k=float(ds.D_k),
                M_k=float(ds.M_k),
                R_rev_k=float(ds.R_rev_k),
                U_star_k=float(ds.U_star_k),
                P_k=float(ds.P_k),
                B_k=float(ds.B_k),
            )
        )

    return dsf_list


# ---------------------------------------------------------------------------
# L4 Hardening – Piecewise-Linear Reliability Mapping
# ---------------------------------------------------------------------------

# Initial test defaults for validation (not hard-coded UF invariants)
A_LOWER: float = 0.20  # a: lower reliability cutoff
B_UPPER: float = 0.70  # b: upper reliability cutoff


@dataclass
class Layer4Raw:
    """
    Container for raw L4 outputs before hardening.

    D, M, P, B must be broadcast-compatible; R is reliability in [0,1].
    """
    D: ArrayLike
    M: ArrayLike
    P: ArrayLike
    B: ArrayLike
    R: ArrayLike


@dataclass
class Layer4Hardened:
    """
    Container for hardened L4 outputs after applying s_k = f(R_k).
    """
    D: np.ndarray
    M: np.ndarray
    P: np.ndarray
    B: np.ndarray
    R: np.ndarray
    s: np.ndarray  # hardening / softening factor applied per bar


def _to_ndarray(x: ArrayLike, dtype=float) -> np.ndarray:
    """
    Promote scalars or arrays to a numpy.ndarray of the given dtype.
    """
    if isinstance(x, np.ndarray):
        return x.astype(dtype, copy=False)
    return np.asarray(x, dtype=dtype)


def hardening_factor(
    R: ArrayLike,
    a: float = A_LOWER,
    b: float = B_UPPER,
) -> np.ndarray:
    """
    Compute the piecewise-linear hardening / softening factor s_k = f(R_k).

    R: reliability field in [0, 1]
    """
    R_arr = _to_ndarray(R, dtype=float)

    if not (0.0 <= a < b <= 1.0):
        raise ValueError(
            f"Invalid hardening parameters: require 0 <= a < b <= 1, got a={a}, b={b}"
        )

    s = np.zeros_like(R_arr, dtype=float)

    mid_mask = (R_arr > a) & (R_arr < b)
    s[mid_mask] = (R_arr[mid_mask] - a) / (b - a)

    high_mask = R_arr >= b
    s[high_mask] = 1.0

    # Low region (R_k <= a) stays 0 explicitly.

    return s


def apply_hardening(
    raw: Layer4Raw,
    a: float = A_LOWER,
    b: float = B_UPPER,
) -> Layer4Hardened:
    """
    Apply the piecewise-linear hardening mapping to raw L4 outputs.
    """
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
        raise RuntimeError(
            f"Layer 4 hardening failed due to shape or integration mismatch: {exc}"
        ) from exc

    return Layer4Hardened(
        D=D_h,
        M=M_h,
        P=P_h,
        B=B_h,
        R=R,
        s=s,
    )


def harden_fields(
    D: ArrayLike,
    M: ArrayLike,
    P: ArrayLike,
    B: ArrayLike,
    R: ArrayLike,
    a: float = A_LOWER,
    b: float = B_UPPER,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Convenience wrapper: apply hardening directly to separate fields.
    """
    raw = Layer4Raw(D=D, M=M, P=P, B=B, R=R)
    hardened = apply_hardening(raw, a=a, b=b)
    return hardened.D, hardened.M, hardened.P, hardened.B, hardened.s
