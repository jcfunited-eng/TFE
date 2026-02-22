"""
uf_core.layer4 — Decision Dynamics (UF-Spec v1.4.0: Complete L4 Kernel)
======================================================================

Implements L4 components defined by UF-Spec v1.4.0:

Completed in this module:
-------------------------
- ΔR(k)        : resonance change per gate
- D_k          : directional structural signal (+1, 0, -1)
- M_k          : directional momentum (sign persistence)
- R_rev_k      : reversal flag (0 or 1)
- U*_k         : corrected uncertainty influence (bounded [0,1])
- P_k          : pressure band (+1 expansion, -1 compression, 0 neutral)
- B_k          : breathing influence (+1, 0, -1)
- DSF_k        : final decision-surface vector

DSF_k is defined as:

    DSF_k = (D_k, M_k, R_rev_k, U*_k, P_k, B_k)

NOTE:
- This module computes both intermediate DecisionState objects (for debugging /
  structural inspection) and DSF vectors (for downstream UF/TFE logic).
"""

from dataclasses import dataclass
from typing import List, Optional

from .layer3 import ResonanceResult
from .layer1 import Gate
from .config import KERNEL_THRESHOLDS


# ----------------------------------------------------------------------------
# Core L4 state containers
# ----------------------------------------------------------------------------

@dataclass
class DecisionState:
    """
    Decision state for L4 (structural internal state):

    - resonance_result : L3 ResonanceResult
    - delta_R          : ΔR(k)
    - D_k              : directional signal (+1, 0, -1)
    - M_k              : directional momentum (+1, 0, -1)
    - R_rev_k          : reversal flag (0 or 1)
    - U_star_k         : corrected uncertainty influence in [0, 1]
    - P_k              : pressure band (+1 expansion, -1 compression, 0 neutral)
    - B_k              : breathing influence (+1, 0, -1)
    """
    resonance_result: ResonanceResult
    delta_R: float
    D_k: int
    M_k: int
    R_rev_k: int
    U_star_k: float
    P_k: int
    B_k: int


@dataclass
class DSF:
    """
    Final Decision Surface Field representation per gate:

    DSF_k = (D_k, M_k, R_rev_k, U*_k, P_k, B_k)
    plus a reference to the original gate (for indexing in TFE).

    - gate      : underlying gate (index range)
    - D_k       : directional signal
    - M_k       : momentum
    - R_rev_k   : reversal flag
    - U_star_k  : corrected uncertainty influence
    - P_k       : pressure band
    - B_k       : breathing influence
    """
    gate: Gate
    D_k: int
    M_k: int
    R_rev_k: int
    U_star_k: float
    P_k: int
    B_k: int


# ----------------------------------------------------------------------------
# Internal calculations
# ----------------------------------------------------------------------------

def _compute_delta_R(resonance_results: List[ResonanceResult]) -> List[float]:
    """Compute ΔR(k) = R_k - R_{k-1} with ΔR(0) = 0."""
    if not resonance_results:
        return []
    delta_R_list: List[float] = []
    prev_R = None
    for res in resonance_results:
        R_k = res.R_k
        delta_R = 0.0 if prev_R is None else (R_k - prev_R)
        delta_R_list.append(float(delta_R))
        prev_R = R_k
    return delta_R_list


def _compute_D_k(delta_R_list: List[float], epsilon_D: float) -> List[int]:
    """Compute D_k from ΔR(k) and epsilon_D."""
    D_list: List[int] = []
    for delta_R in delta_R_list:
        if delta_R > epsilon_D:
            D_k = 1
        elif delta_R < -epsilon_D:
            D_k = -1
        else:
            D_k = 0
        D_list.append(D_k)
    return D_list


def _compute_M_k(D_list: List[int]) -> List[int]:
    """
    Structural momentum:

        M_k = +1 if D_k = +1 and D_{k-1} = +1
              -1 if D_k = -1 and D_{k-1} = -1
               0 otherwise

        M_0 = 0
    """
    if not D_list:
        return []
    M_list: List[int] = [0]  # M_0 = 0
    for i in range(1, len(D_list)):
        prev_D = D_list[i - 1]
        D_k = D_list[i]
        if D_k == 1 and prev_D == 1:
            M_k = 1
        elif D_k == -1 and prev_D == -1:
            M_k = -1
        else:
            M_k = 0
        M_list.append(M_k)
    return M_list


def _compute_R_rev(D_list: List[int]) -> List[int]:
    """
    Boolean reversal detection:

        R_rev_k = 1 if D_k != 0 and D_k == -D_{k-1}
                  0 otherwise

        R_rev_0 = 0
    """
    if not D_list:
        return []
    R_rev_list: List[int] = [0]  # R_rev_0 = 0
    for i in range(1, len(D_list)):
        prev_D = D_list[i - 1]
        D_k = D_list[i]
        if D_k != 0 and D_k == -prev_D:
            R_rev_k = 1
        else:
            R_rev_k = 0
        R_rev_list.append(R_rev_k)
    return R_rev_list


def _compute_U_star(resonance_results: List[ResonanceResult]) -> List[float]:
    """
    Compute corrected uncertainty influence:

        U*_k = bounded(1 - U_k) ∈ [0, 1]
    """
    U_star_list: List[float] = []
    for res in resonance_results:
        U_k = float(res.interpretation.U_k)
        raw = 1.0 - U_k
        bounded = max(0.0, min(1.0, raw))
        U_star_list.append(bounded)
    return U_star_list


def _compute_P_k(delta_R_list: List[float], D_list: List[int]) -> List[int]:
    """
    Compute pressure band P_k:

        P_k = +1 if ΔR(k) > 0 and |D_k| = 1    (expansion)
              -1 if ΔR(k) < 0 and |D_k| = 1    (compression)
               0 otherwise
    """
    P_list: List[int] = []
    for delta_R, D_k in zip(delta_R_list, D_list):
        if abs(D_k) == 1:
            if delta_R > 0:
                P_k = 1
            elif delta_R < 0:
                P_k = -1
            else:
                P_k = 0
        else:
            P_k = 0
        P_list.append(P_k)
    return P_list


def _compute_B_k(P_list: List[int]) -> List[int]:
    """
    Compute breathing influence B_k based on transitions in P_k:

        B_k = +1  if P_k = +1 and P_{k-1} = -1  (expansion after compression)
              -1  if P_k = -1 and P_{k-1} = +1  (compression after expansion)
               0   otherwise

        B_0 = 0
    """
    if not P_list:
        return []
    B_list: List[int] = [0]  # B_0 = 0
    for i in range(1, len(P_list)):
        prev_P = P_list[i - 1]
        P_k = P_list[i]
        if P_k == 1 and prev_P == -1:
            B_k = 1
        elif P_k == -1 and prev_P == 1:
            B_k = -1
        else:
            B_k = 0
        B_list.append(B_k)
    return B_list


# ----------------------------------------------------------------------------
# Public APIs
# ----------------------------------------------------------------------------

def compute_directional_signal(resonance_results: List[ResonanceResult],
                               epsilon_D: Optional[float] = None) -> List[DecisionState]:
    """
    Compute ΔR(k), D_k, M_k, R_rev_k, U*_k, P_k, B_k.

    epsilon_D is drawn from KERNEL_THRESHOLDS.epsilon_D when None.
    """

    if epsilon_D is None:
        epsilon_D = KERNEL_THRESHOLDS.epsilon_D

    if not resonance_results:
        return []

    # ΔR(k)
    delta_R_list = _compute_delta_R(resonance_results)

    # D_k
    D_list = _compute_D_k(delta_R_list, epsilon_D)

    # M_k
    M_list = _compute_M_k(D_list)

    # R_rev_k
    R_rev_list = _compute_R_rev(D_list)

    # U*_k
    U_star_list = _compute_U_star(resonance_results)

    # P_k
    P_list = _compute_P_k(delta_R_list, D_list)

    # B_k
    B_list = _compute_B_k(P_list)

    decision_states: List[DecisionState] = []
    for res, dR, D_k, M_k, R_rev_k, U_star_k, P_k, B_k in zip(
        resonance_results, delta_R_list, D_list, M_list, R_rev_list, U_star_list, P_list, B_list
    ):
        decision_states.append(DecisionState(
            resonance_result=res,
            delta_R=dR,
            D_k=D_k,
            M_k=M_k,
            R_rev_k=R_rev_k,
            U_star_k=U_star_k,
            P_k=P_k,
            B_k=B_k,
        ))

    return decision_states


def compute_dsf(decision_states: List[DecisionState]) -> List[DSF]:
    """
    Construct DSF_k vectors from a list of DecisionState objects.

    DSF_k = (D_k, M_k, R_rev_k, U*_k, P_k, B_k) plus the underlying Gate.
    """

    dsf_list: List[DSF] = []
    for ds in decision_states:
        gate = ds.resonance_result.interpretation.gate
        dsf_list.append(DSF(
            gate=gate,
            D_k=ds.D_k,
            M_k=ds.M_k,
            R_rev_k=ds.R_rev_k,
            U_star_k=ds.U_star_k,
            P_k=ds.P_k,
            B_k=ds.B_k,
        ))
    return dsf_list
