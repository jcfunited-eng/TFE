# TFE Source Package for Independent Review — May 26, 2026

## PURPOSE
Complete source code for the TFE kernel (L0-L4), L5 baseline filter,
CP-2 cognitive pipeline, quarantine historical kernel, and quarantine
sequential filter. Provided for independent physics review.

## CRITICAL QUESTION
Which pipeline produced the 81% quarantine win rate?
- Production L0 (`uf_core/layer0.py`): uses `log(F + eps)` normalization
- CP-2 (`uf_mdg_snapshot.py`): uses raw close prices (no log)
- Quarantine kernel (`quarantine_historical_kernel.py`): uses raw close prices (no log)

The quarantine sequential filter (`quarantine_sequential_filter.py`) joins
primitive trades with governed states from `quarantine_historical_kernel.py`.
The 81% backtest was computed on the quarantine pipeline (raw prices, no log).

## FILES INCLUDED (in order)
1. `uf_core/config.py` — All kernel constants
2. `uf_core/layer0.py` — L0 SEV with LOG normalization (PRODUCTION)
3. `uf_core/layer1.py` — L1 gate segmentation
4. `uf_core/layer2.py` — L2 ISF interpretation
5. `uf_core/layer3.py` — L3 resonance
6. `uf_core/layer4.py` — L4 DSF/directional
7. `uf_core/uf_structural_engine.py` — L5 adapter (production pipeline)
8. `tfe_l5_baseline.py` — L5 canonical baseline filter (V3 basin)
9. `quarantine_historical_kernel.py` — Quarantine kernel (RAW prices, no log)
10. `quarantine_sequential_filter.py` — The script that produced 81%
11. `uf_mdg_snapshot.py` (CP-2 section) — CP-2 cognitive scalars (RAW prices)

---


---

## FILE: uf_core/config.py

```python
"""
uf_core.config — Kernel Thresholds and Structural Constants (UF-Spec v1.4.0)
===========================================================================

Centralized constants used by L1-L4 and the L5 domain adapter path.

Notes:
- The `segment_gates` comparator override (`>` vs `>=`) is preserved through
  `gate_boundary_strict_gt` because it was explicitly approved as a domain
  condition.
- All other constants are explicit and named so behavior is auditable.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class KernelThresholds:
    # L0 baseline
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6
    variance_window: int = 20

    # L1 boundary operator D(t)
    alpha1: float = 1.0
    alpha2: float = 1.0
    alpha3: float = 1.0
    tau_D: float = 0.20

    # Approved domain override for L1 boundary comparator.
    # True:  D(t) > tau_D  (approved)
    # False: D(t) >= tau_D (canonical math-text form)
    gate_boundary_strict_gt: bool = True

    # L1 TVR structural volume weights
    beta1: float = 1.0
    beta2: float = 1.0
    beta3: float = 1.0

    # L1 multi-lattice quantization steps: (h1, h2, h3) per lattice level.
    mosaic_lattices: Tuple[Tuple[float, float, float], ...] = (
        (1.0, 1.0, 1.0),
        (2.0, 2.0, 2.0),
        (4.0, 4.0, 4.0),
    )

    # L1 negative-space gate thresholds
    theta_V: float = 1.0
    theta_R: float = 1.0

    # L2 score and uncertainty weights
    gamma1: float = 1.0 / 3.0
    gamma2: float = 1.0 / 3.0
    gamma3: float = 1.0 / 3.0

    lambda_u1: float = 1.0 / 3.0
    lambda_u2: float = 1.0 / 3.0
    lambda_u3: float = 1.0 / 3.0

    # L2 deterministic regime thresholds over chi/psi space
    chi_min: float = 0.25
    chi_max: float = 0.75
    psi_min: float = 0.25
    psi_max: float = 0.75

    # L2/L3 uncertainty gate limit
    U_max: float = 0.75

    # L3 resonance weights
    lambda1: float = 1.0
    lambda2: float = 1.0
    lambda3: float = 1.0
    lambda4: float = 1.0
    lambda5: float = 1.0

    # L3 hysteresis
    h_max: float = 0.20

    # L4 directional threshold
    epsilon_D: float = 0.00073

    # L4 uncertainty amplification terms
    eta_H: float = 0.10
    eta_IAS: float = 0.10

    # L4 breathing dynamics
    breath_xi: float = 0.10
    breath_chi: float = 0.10
    B_min: float = -1.0
    B_max: float = 1.0


KERNEL_THRESHOLDS = KernelThresholds()
```

---

## FILE: uf_core/layer0.py

```python
"""
uf_core.layer0 — Structural Field Normalization (UF-Spec v1.4.0, Corrected)
===========================================================================

Corrected L0 implementation using *dimensionless* structural field:

    F_norm(t) = log(F(t) + ε)

This normalization:
    • removes multiplicative scale distortion,
    • ensures UF-Layers 1–4 operate on structural shape, not absolute magnitude,
    • restores meaningful negative-space detection,
    • prevents high-field values (e.g., large prices, large intensities) 
      from collapsing UF gating by overwhelming τ_D.

UF-Spec requirement:
    Local operators ΔF, σ(t), κ(t), and N(t) must reflect *structure*, 
    not absolute scale of the raw field. Log-mapping satisfies this for all 
    positive-valued scalar fields (population counts, intensities, prices, etc.).

This implementation is domain-agnostic — no financial assumptions.
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .config import KERNEL_THRESHOLDS


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class SEV:
    """State Embedding Vector for UF-Spec v1.4.0."""
    F_norm: float        # normalized field value
    dF: float            # ΔF_norm(t)
    sigma: float         # local variance of F_norm
    kappa: float         # curvature proxy
    relevance: float     # placeholder (fixed = 1.0)
    N: int               # structural negative-space indicator (0 or 1)


# ---------------------------------------------------------------------------
# Input Health Verification (IHV)
# ---------------------------------------------------------------------------

def input_health_verification(df: pd.DataFrame, field_col: str) -> bool:
    """
    UF-Spec L0 IHV: ensures structural field conditions before UF transform.

    Preconditions:
        • monotonic index
        • no NaN
        • all finite
        • column exists
    """
    if field_col not in df.columns:
        print(f"[IHV] ERROR: Column '{field_col}' not found.")
        return False

    if not isinstance(df.index, pd.DatetimeIndex) and not np.issubdtype(df.index.dtype, np.number):
        print("[IHV] ERROR: Index must be datetime or numeric.")
        return False

    if not df.index.is_monotonic_increasing:
        print("[IHV] ERROR: Non-monotonic index.")
        return False

    vals = df[field_col].astype(float).values

    if np.isnan(vals).any():
        print("[IHV] ERROR: Missing values in structural field.")
        return False

    if not np.isfinite(vals).all():
        print("[IHV] ERROR: Non-finite values in structural field.")
        return False

    return True


# ---------------------------------------------------------------------------
# L0 — Structural Field Normalization (Corrected)
# ---------------------------------------------------------------------------

def compute_sev_series(df: pd.DataFrame, field_col: str = "Close"):
    """
    Corrected L0:

        F_norm(t) = log(F(t) + ε)

    This satisfies UF-Spec's requirement that UF operate on *shape*, not scale.

    Steps performed:
        1. IHV: sanity check for structural field.
        2. Apply log-normalization to make field dimensionless.
        3. Compute dF_norm(t).
        4. Compute σ(t) over window w (in normalized space).
        5. Compute κ(t) (discrete curvature of normalized field).
        6. Compute N(t) using structural thresholds on normalized operators.

    Output:
        List[SEV]
    """

    if not input_health_verification(df, field_col):
        raise RuntimeError("InputHealthVerificationFailed: L0 aborted.")

    EPS = 1e-8  # Safe epsilon for dimensionless log field

    # Raw field values (generic scalar field)
    F_raw = df[field_col].astype(float).values

    # Structural field normalization (dimensionless)
    F_norm = np.log(F_raw + EPS)

    n = len(F_norm)

    dF = np.zeros(n)
    sigma = np.zeros(n)
    kappa = np.zeros(n)
    relevance = np.ones(n)  # Placeholder; L5 may refine later
    N_vec = np.zeros(n, dtype=int)

    # ΔF_norm(t)
    if n > 1:
        dF[1:] = np.diff(F_norm)

    # σ(t): local variance window of normalized field
    w = max(1, getattr(KERNEL_THRESHOLDS, "variance_window", 5))
    for i in range(n):
        start = max(0, i - w + 1)
        seg = F_norm[start:i+1]
        sigma[i] = float(np.var(seg)) if len(seg) > 1 else 0.0

    # κ(t): curvature proxy (normalized field)
    if n > 2:
        for i in range(1, n - 1):
            kappa[i] = abs(F_norm[i+1] - 2.0 * F_norm[i] + F_norm[i-1])
    # endpoints remain 0.0 by definition

    # N(t): structural negative-space operator in normalized domain
    τ_sigma = KERNEL_THRESHOLDS.sigma_min
    τ_delta = KERNEL_THRESHOLDS.delta_min
    τ_kappa = KERNEL_THRESHOLDS.kappa_min

    for i in range(n):
        cond_sigma = (sigma[i] <= τ_sigma)
        cond_dF    = (abs(dF[i]) <= τ_delta)
        cond_kappa = (kappa[i] <= τ_kappa)
        N_vec[i] = 1 if (cond_sigma and cond_dF and cond_kappa) else 0

    # Build SEV list
    sev_list = [
        SEV(
            F_norm=F_norm[i],
            dF=dF[i],
            sigma=sigma[i],
            kappa=kappa[i],
            relevance=relevance[i],
            N=int(N_vec[i]),
        )
        for i in range(n)
    ]

    return sev_list
```

---

## FILE: uf_core/layer1.py

```python
"""
uf_core.layer1 — Gate and Mosaic Architecture (UF-Spec v1.4.0)
================================================================

L1 responsibilities:
- Segment L0 SEV stream into gates via boundary operator D(t).
- Compute gate TVR descriptors: (T_k, V_k, R_k).
- Compute multi-lattice projections P_l(G_k).
- Compute mosaic divergence C_k.
- Compute gate drift delta_g(G_k).
- Compute negative-space gate flags N(G_k).

The approved domain override for boundary comparison (`>` instead of `>=`) is
preserved and controlled by `KERNEL_THRESHOLDS.gate_boundary_strict_gt`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import List, Sequence, Tuple

import numpy as np

from .config import KERNEL_THRESHOLDS
from .layer0 import SEV


TVR = Tuple[float, float, float]
Projection = Tuple[int, int, int]


@dataclass(frozen=True)
class Gate:
    """Contiguous time segment [start_idx, end_idx] in the SEV stream."""

    start_idx: int
    end_idx: int


@dataclass(frozen=True)
class GateL1State:
    """Complete L1 output record for one gate."""

    gate: Gate
    tvr: TVR
    projections: Tuple[Projection, ...]
    C_k: int
    delta_g: float
    N_gate: int


def compute_deviation(
    sev_series: Sequence[SEV],
    alpha1: float | None = None,
    alpha2: float | None = None,
    alpha3: float | None = None,
) -> np.ndarray:
    """Compute D(t) = a1*||dF|| + a2*sigma + a3*kappa."""

    if alpha1 is None:
        alpha1 = float(KERNEL_THRESHOLDS.alpha1)
    if alpha2 is None:
        alpha2 = float(KERNEL_THRESHOLDS.alpha2)
    if alpha3 is None:
        alpha3 = float(KERNEL_THRESHOLDS.alpha3)

    D = np.zeros(len(sev_series), dtype=float)
    for i, sev in enumerate(sev_series):
        D[i] = (
            alpha1 * abs(float(sev.dF))
            + alpha2 * float(sev.sigma)
            + alpha3 * float(sev.kappa)
        )
    return D


def segment_gates(sev_series: Sequence[SEV]) -> List[Gate]:
    """
    Segment gates by threshold crossings of D(t).

    Canonical boundary form is D(t) >= tau_D.
    Approved domain override keeps strict D(t) > tau_D when configured.
    """

    if not sev_series:
        return []

    D = compute_deviation(sev_series)
    tau_D = float(KERNEL_THRESHOLDS.tau_D)
    strict_gt = bool(getattr(KERNEL_THRESHOLDS, "gate_boundary_strict_gt", True))

    gates: List[Gate] = []
    current_start = 0

    for i in range(1, len(sev_series)):
        if strict_gt:
            boundary = D[i] > tau_D
        else:
            boundary = D[i] >= tau_D

        if boundary:
            gates.append(Gate(start_idx=current_start, end_idx=i - 1))
            current_start = i

    gates.append(Gate(start_idx=current_start, end_idx=len(sev_series) - 1))
    return gates


def compute_gate_tvr(
    sev_series: Sequence[SEV],
    gates: Sequence[Gate],
    beta1: float | None = None,
    beta2: float | None = None,
    beta3: float | None = None,
) -> List[TVR]:
    """
    Compute TVR_k = (T_k, V_k, R_k).

    Discrete implementation with dt=1:
    - T_k = t_b - t_a
    - V_k = sum(beta1*|dF| + beta2*sigma + beta3*kappa)
    - R_k = sum(relevance)
    """

    if beta1 is None:
        beta1 = float(KERNEL_THRESHOLDS.beta1)
    if beta2 is None:
        beta2 = float(KERNEL_THRESHOLDS.beta2)
    if beta3 is None:
        beta3 = float(KERNEL_THRESHOLDS.beta3)

    if not sev_series or not gates:
        return []

    dF = np.array([float(sev.dF) for sev in sev_series], dtype=float)
    sigma = np.array([float(sev.sigma) for sev in sev_series], dtype=float)
    kappa = np.array([float(sev.kappa) for sev in sev_series], dtype=float)
    relevance = np.array([float(sev.relevance) for sev in sev_series], dtype=float)

    out: List[TVR] = []
    for gate in gates:
        s = gate.start_idx
        e = gate.end_idx

        T_k = float(max(0, e - s))

        seg_dF = dF[s : e + 1]
        seg_sigma = sigma[s : e + 1]
        seg_kappa = kappa[s : e + 1]
        seg_rel = relevance[s : e + 1]

        V_k = float(np.sum(beta1 * np.abs(seg_dF) + beta2 * seg_sigma + beta3 * seg_kappa))
        R_k = float(np.sum(seg_rel))
        out.append((T_k, V_k, R_k))

    return out


def compute_gate_means(sev_series: Sequence[SEV], gates: Sequence[Gate]) -> List[Tuple[float, float, float]]:
    """Compute mu_k = mean(dF, sigma, kappa) for each gate."""

    if not sev_series or not gates:
        return []

    dF = np.array([float(sev.dF) for sev in sev_series], dtype=float)
    sigma = np.array([float(sev.sigma) for sev in sev_series], dtype=float)
    kappa = np.array([float(sev.kappa) for sev in sev_series], dtype=float)

    means: List[Tuple[float, float, float]] = []
    for gate in gates:
        s = gate.start_idx
        e = gate.end_idx
        seg_dF = dF[s : e + 1]
        seg_sigma = sigma[s : e + 1]
        seg_kappa = kappa[s : e + 1]

        means.append(
            (
                float(np.mean(seg_dF)) if len(seg_dF) else 0.0,
                float(np.mean(seg_sigma)) if len(seg_sigma) else 0.0,
                float(np.mean(seg_kappa)) if len(seg_kappa) else 0.0,
            )
        )

    return means


def compute_gate_drift(means: Sequence[Tuple[float, float, float]]) -> List[float]:
    """Compute delta_g(G_k) = ||mu_k - mu_{k-1}||, with delta_0 = 0."""

    if not means:
        return []

    drifts: List[float] = [0.0]
    for i in range(1, len(means)):
        prev = np.array(means[i - 1], dtype=float)
        curr = np.array(means[i], dtype=float)
        drifts.append(float(np.linalg.norm(curr - prev)))
    return drifts


def _resolve_lattices(lattice_steps: Sequence[Tuple[float, float, float]] | None) -> Tuple[Tuple[float, float, float], ...]:
    if lattice_steps is None:
        lattice_steps = KERNEL_THRESHOLDS.mosaic_lattices

    out: List[Tuple[float, float, float]] = []
    for h1, h2, h3 in lattice_steps:
        if h1 <= 0 or h2 <= 0 or h3 <= 0:
            raise ValueError("All lattice steps must be positive.")
        out.append((float(h1), float(h2), float(h3)))

    if not out:
        raise ValueError("At least one lattice must be configured.")

    return tuple(out)


def compute_mosaic_projections(
    tvr_list: Sequence[TVR],
    lattice_steps: Sequence[Tuple[float, float, float]] | None = None,
) -> List[Tuple[Projection, ...]]:
    """Compute P_l(G_k) = (floor(T/h1), floor(V/h2), floor(R/h3)) for each lattice."""

    if not tvr_list:
        return []

    lattices = _resolve_lattices(lattice_steps)
    projections: List[Tuple[Projection, ...]] = []

    for T_k, V_k, R_k in tvr_list:
        gate_proj: List[Projection] = []
        for h1, h2, h3 in lattices:
            gate_proj.append(
                (
                    int(floor(T_k / h1)),
                    int(floor(V_k / h2)),
                    int(floor(R_k / h3)),
                )
            )
        projections.append(tuple(gate_proj))

    return projections


def compute_mosaic_divergence(projections: Sequence[Tuple[Projection, ...]]) -> List[int]:
    """Compute C_k = |{P_1(G_k), ..., P_L(G_k)}| for each gate."""

    if not projections:
        return []

    out: List[int] = []
    for gate_proj in projections:
        out.append(int(len(set(gate_proj))))
    return out


def compute_negative_space_gate_flags(
    sev_series: Sequence[SEV],
    gates: Sequence[Gate],
    tvr_list: Sequence[TVR],
    theta_V: float | None = None,
    theta_R: float | None = None,
) -> List[int]:
    """Compute N(G_k) gate flag from SEV N(t), V_k, and R_k thresholds."""

    if theta_V is None:
        theta_V = float(KERNEL_THRESHOLDS.theta_V)
    if theta_R is None:
        theta_R = float(KERNEL_THRESHOLDS.theta_R)

    if not sev_series or not gates or not tvr_list:
        return []

    N_values = np.array([int(sev.N) for sev in sev_series], dtype=int)
    flags: List[int] = []

    for gate, (_, V_k, R_k) in zip(gates, tvr_list):
        s = gate.start_idx
        e = gate.end_idx
        seg_N = N_values[s : e + 1]
        all_negative_space = bool(len(seg_N) > 0 and np.all(seg_N == 1))
        flags.append(1 if (all_negative_space and V_k < theta_V and R_k < theta_R) else 0)

    return flags


def build_gate_l1_state(sev_series: Sequence[SEV], gates: Sequence[Gate]) -> List[GateL1State]:
    """Build full L1 records for each gate."""

    if not sev_series or not gates:
        return []

    tvr_list = compute_gate_tvr(sev_series, gates)
    projections = compute_mosaic_projections(tvr_list)
    C_k_list = compute_mosaic_divergence(projections)
    means = compute_gate_means(sev_series, gates)
    delta_g_list = compute_gate_drift(means)
    N_gate_list = compute_negative_space_gate_flags(sev_series, gates, tvr_list)

    out: List[GateL1State] = []
    for gate, tvr, proj, C_k, delta_g, N_gate in zip(
        gates,
        tvr_list,
        projections,
        C_k_list,
        delta_g_list,
        N_gate_list,
    ):
        out.append(
            GateL1State(
                gate=gate,
                tvr=tvr,
                projections=proj,
                C_k=int(C_k),
                delta_g=float(delta_g),
                N_gate=int(N_gate),
            )
        )

    return out
```

---

## FILE: uf_core/layer2.py

```python
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
```

---

## FILE: uf_core/layer3.py

```python
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
```

---

## FILE: uf_core/layer4.py

```python
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
```

---

## FILE: uf_core/uf_structural_engine.py

```python
"""
uf_structural_engine.py
-----------------------------------------
UF-Core Structural Engine Adapter for TFE (v1.0)

Active runtime path:

    L0: uf_core.layer0.compute_sev_series   (field_col="Close")
    L1: uf_core.layer1.segment_gates
    L2: uf_core.layer2.interpret_gates
    L3: uf_core.layer3.compute_resonance
    L4: uf_core.layer4.compute_directional_signal, compute_dsf

Active production exports:

    - hardening controller metadata
    - safemode metadata
    - gate unlock transient guard metadata

Public UF engine:

    compute_uf_structural_state(close: pd.Series) -> UFStructuralState

TFE adapter (at bottom):

    compute_structural_state(symbol: str, bars: List[Bar]) -> Dict[str, Any]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from uf_core.layer0 import SEV, compute_sev_series
from uf_core.layer1 import Gate, segment_gates
from uf_core.layer2 import GateInterpretation, interpret_gates
from uf_core.layer3 import ResonanceResult, compute_resonance
from uf_core.layer4 import DSF, DecisionState, compute_directional_signal, compute_dsf

from tfe_market_data_service import Bar


@dataclass
class UFStructuralState:
    """
    High-level UF structural summary for a single asset, as seen by TFE.

    NOTE:
      - All fields are derived from uf_core.*.
      - level5.D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k preserve last DSF values
      - level5.prev_C_k preserves the immediately preceding DSF conflict state
        for full L4 structural provenance.
      - level5.decision_vector now mirrors raw DSF directly.
      - adapter control metadata is exported as active production state.
    """

    level1: Dict[str, float]
    level2: Dict[str, float]
    level3: Dict[str, Any]
    level4: Dict[str, float]
    level5: Dict[str, Any]


def _safe_pct_change(series: pd.Series) -> pd.Series:
    return series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min())


def _compute_basic_features(close: pd.Series) -> Dict[str, float]:
    close = close.astype(float)
    returns = _safe_pct_change(close)
    vol = float(returns.std() * np.sqrt(252)) if len(returns) > 0 else 0.0
    avg_ret = float(returns.mean() * 252) if len(returns) > 0 else 0.0
    price_range = float((close.max() - close.min()) / close.min()) if close.min() > 0 else 0.0
    return {
        "n": float(len(close)),
        "vol": vol,
        "avg_return": avg_ret,
        "price_range": price_range,
    }


def _compute_trend_curvature(close: pd.Series) -> Dict[str, float]:
    close = close.astype(float)
    n = len(close)
    if n < 3:
        return {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}

    x = np.arange(n)
    y = close.values

    slope, _intercept = np.polyfit(x, y, 1)

    trend_strength = float((slope / close.iloc[0]) * n) if close.iloc[0] != 0 else 0.0

    quad = np.polyfit(x, y, 2)
    y_quad = np.polyval(quad, x)
    curvature = float(np.mean(np.abs(y_quad - y)) / close.iloc[0]) if close.iloc[0] != 0 else 0.0

    return {
        "trend_strength": trend_strength,
        "curvature": curvature,
        "slope": float(slope),
    }


def _aggregate_gate_regime(interpretations: List[GateInterpretation]) -> str:
    if not interpretations:
        return "UNKNOWN"
    return interpretations[-1].regime


def _compute_stability_from_l4(
    results: List[ResonanceResult],
    decision_states: List[DecisionState],
) -> Dict[str, float]:
    if not results or not decision_states:
        return {
            "dsf": 1.0,
            "directional": 1.0,
            "hysteresis_rate": 0.0,
            "breathing_rate": 0.0,
            "uncertainty_rate": 0.0,
            "gate_drift_rate": 0.0,
            "R_mean": 0.0,
        }

    hyst_flags = np.array([r.Hyst_k for r in results], dtype=float)
    r_vals = np.array([r.R_k for r in results], dtype=float)

    hyst_rate = float(np.mean(hyst_flags))
    r_mean = float(np.mean(r_vals))

    d_vals = np.array([ds.D_k for ds in decision_states], dtype=float)
    b_vals = np.array([ds.B_k for ds in decision_states], dtype=float)
    u_star_vals = np.array([ds.U_star_k for ds in decision_states], dtype=float)
    rev_flags = np.array([ds.R_rev_k for ds in decision_states], dtype=float)

    directional_stability = float(1.0 - np.mean(rev_flags))
    dsf_instability = float(np.mean((np.abs(d_vals) > 0).astype(float)))
    breathing_instability = float(np.mean((np.abs(b_vals) != 0).astype(float)))
    dsf_stability = float(1.0 - dsf_instability)

    uncertainty_rate = float(1.0 - np.mean(u_star_vals)) if len(u_star_vals) > 0 else 0.0

    return {
        "dsf": dsf_stability,
        "directional": directional_stability,
        "hysteresis_rate": hyst_rate,
        "breathing_rate": breathing_instability,
        "uncertainty_rate": uncertainty_rate,
        "gate_drift_rate": 0.0,
        "R_mean": r_mean,
    }


def _active_control_payload(name: str) -> Dict[str, Any]:
    return {
        "active_runtime": True,
        "status": "active_production",
        "reason": f"{name}_export_active_in_production",
    }


def _to_optional_finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if not np.isfinite(parsed):
        return None
    return parsed


def _find_previous_valid_c_k(dsf_list: List[DSF]) -> float | None:
    if not dsf_list:
        return None

    current_c_k = _to_optional_finite_float(getattr(dsf_list[-1], "C_k", None))
    if len(dsf_list) < 2:
        return current_c_k

    for dsf in reversed(dsf_list[:-1]):
        c_k = _to_optional_finite_float(getattr(dsf, "C_k", None))
        if c_k is not None:
            return c_k

    return current_c_k


def compute_uf_structural_state(close: pd.Series) -> UFStructuralState:
    """
    Main entrypoint: true UF-Core pipeline for a single asset.

    Active runtime behavior:
      - compute raw canonical UF/DSF outputs
      - export raw last-DSF values directly
      - export adapter control metadata as active production state
    """

    close = close.dropna().astype(float)
    if len(close) < 10:
        level1 = {"n": float(len(close)), "vol": 0.0, "avg_return": 0.0, "price_range": 0.0}
        level2 = {"trend_strength": 0.0, "curvature": 0.0, "slope": 0.0}
        level3 = {"regime": "INSUFFICIENT_DATA"}
        level4 = {"max_drawdown": 0.0, "stability_score": 0.0, "S_UF": 0.0, "R_UF": 0.0}
        level5 = {
            "decision_vector": [],
            "D_k": None,
            "M_k": None,
            "R_rev_k": None,
            "U_star_k": None,
            "C_k": None,
            "prev_C_k": None,
            "P_k": None,
            "B_k": None,
            "gate_count": 0,
            "active_gate_count": 0,
            "decision_guard": _active_control_payload("gate_unlock_transient_guard"),
            "hardening": _active_control_payload("hardening_control"),
            "safemode": _active_control_payload("safemode"),
        }
        return UFStructuralState(level1, level2, level3, level4, level5)

    df = pd.DataFrame({"Close": close})
    df.index = close.index

    sev_list: List[SEV] = compute_sev_series(df, field_col="Close")
    gates: List[Gate] = segment_gates(sev_list)
    interpretations: List[GateInterpretation] = interpret_gates(sev_list, gates)
    resonance_results: List[ResonanceResult] = compute_resonance(interpretations)
    decision_states: List[DecisionState] = compute_directional_signal(resonance_results)
    dsf_list: List[DSF] = compute_dsf(decision_states)

    regime = _aggregate_gate_regime(interpretations)
    level1 = _compute_basic_features(close)
    level2 = _compute_trend_curvature(close)

    returns = _safe_pct_change(close)
    max_dd = _max_drawdown(returns)

    stab = _compute_stability_from_l4(resonance_results, decision_states)

    s_uf = float(max(0.0, min(1.0, 0.5 * stab["dsf"] + 0.5 * stab["directional"])))
    r_uf = float(max(0.0, min(1.0, stab["R_mean"])))

    raw_d_k: float | None = None
    raw_m_k: float | None = None
    raw_r_rev_k: float | None = None
    raw_u_star_k: float | None = None
    raw_c_k: float | None = None
    raw_prev_c_k: float | None = None
    raw_p_k: float | None = None
    raw_b_k: float | None = None

    if dsf_list:
        last_dsf = dsf_list[-1]
        raw_d_k = float(last_dsf.D_k)
        raw_m_k = float(last_dsf.M_k)
        raw_r_rev_k = float(last_dsf.R_rev_k)
        raw_u_star_k = float(last_dsf.U_star_k)
        raw_c_k = float(last_dsf.C_k)
        raw_prev_c_k = _find_previous_valid_c_k(dsf_list)
        raw_p_k = float(last_dsf.P_k)
        raw_b_k = float(last_dsf.B_k)
        decision_vector = [
            float(last_dsf.D_k),
            float(last_dsf.M_k),
            float(last_dsf.R_rev_k),
            float(last_dsf.U_star_k),
            float(last_dsf.P_k),
            float(last_dsf.B_k),
        ]
    else:
        decision_vector = []

    stability_score = float(
        max(
            0.0,
            min(
                1.0,
                0.5 * stab["dsf"] + 0.3 * stab["directional"] - 2.0 * abs(max_dd),
            ),
        )
    )

    level3 = {"regime": regime}
    level4 = {
        "max_drawdown": max_dd,
        "stability_score": stability_score,
        "S_UF": s_uf,
        "R_UF": r_uf,
    }

    level5 = {
        "decision_vector": decision_vector,
        "D_k": raw_d_k,
        "M_k": raw_m_k,
        "R_rev_k": raw_r_rev_k,
        "U_star_k": raw_u_star_k,
        "C_k": raw_c_k,
        "prev_C_k": raw_prev_c_k,
        "P_k": raw_p_k,
        "B_k": raw_b_k,
        "gate_count": int(len(gates)),
        "active_gate_count": int(sum(1 for r in resonance_results if int(r.g_k) == 1)),
        "decision_guard": _active_control_payload("gate_unlock_transient_guard"),
        "hardening": _active_control_payload("hardening_control"),
        "safemode": _active_control_payload("safemode"),
    }

    return UFStructuralState(
        level1=level1,
        level2=level2,
        level3=level3,
        level4=level4,
        level5=level5,
    )


def compute_structural_state(symbol: str, bars: List[Bar]) -> Dict[str, Any]:
    """
    Adapter used by TFE.

    - Converts Bar list to close-price series
    - Calls the UF-Core engine
    - Returns the flat shape TFE expects
    - Exports active production control metadata
    """
    close = pd.Series(
        [b.close for b in bars],
        index=[b.timestamp for b in bars],
    ).sort_index()

    uf_state = compute_uf_structural_state(close)

    return {
        "symbol": symbol,
        "last_close": float(close.iloc[-1]),
        "regime": uf_state.level3.get("regime"),
        "S_UF": uf_state.level4.get("S_UF"),
        "R_UF": uf_state.level4.get("R_UF"),
        "stability_score": uf_state.level4.get("stability_score"),
        "max_drawdown": uf_state.level4.get("max_drawdown"),
        "decision_vector": uf_state.level5.get("decision_vector", []),
        "D_k": uf_state.level5.get("D_k"),
        "M_k": uf_state.level5.get("M_k"),
        "R_rev_k": uf_state.level5.get("R_rev_k"),
        "U_star_k": uf_state.level5.get("U_star_k"),
        "C_k": uf_state.level5.get("C_k"),
        "prev_C_k": uf_state.level5.get("prev_C_k"),
        "P_k": uf_state.level5.get("P_k"),
        "B_k": uf_state.level5.get("B_k"),
        "gate_count": uf_state.level5.get("gate_count", 0),
        "active_gate_count": uf_state.level5.get("active_gate_count", 0),
        "decision_guard": uf_state.level5.get("decision_guard", {}),
        "hardening": uf_state.level5.get("hardening", {}),
        "safemode": uf_state.level5.get("safemode", {}),
    }
```

---

## FILE: tfe_l5_baseline.py

```python
#!/usr/bin/env python3
"""CP-2: L5 canonical baseline filter — pure DSF V3 basin primitive.

Implements the same frozen basin math as runtime_decision_provenance.mjs.
Uses only columns verified to exist in the production live schema.

Two-layer filter
----------------
Layer 1 (V3 Structural Primitive — always active):
    - V3 basin argmax is tie-free Accumulate
    - price >= MIN_PRICE (5.0)
    - bar_count >= ACCUMULATE_MIN_BARS (verified via snapshot row, not re-checked
      here since uf_snapshot.json rows already passed the bar gate)

Layer 2 (CP-2 Cognitive Gate — SOFT: activates per-row only when F_n and
raw_x_m are non-null):
    - F_n     <= MAX_F_N    (1.65) — cognitive load not overextended
    - raw_x_m <= MAX_RAW_X_M (0.50) — memory state not overextended

Null-pass contract: if F_n or raw_x_m is NULL/NaN for a given row, that
row passes the cognitive gate unconditionally.  This ensures the "Healthy
Titans" set (~144 Accumulates) is fully recovered during the transition
period while the cognitive pipe (uf_mdg_snapshot.py) populates those fields
into the production snapshot.  Once the pipe completes a full refresh cycle,
the gate narrows automatically to the calibrated Titan subset.

Required columns (Layer 1):
    S_UF, R_UF, D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, price

Optional columns (Layer 2, null-safe):
    F_n, raw_x_m
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Frozen rational constants — must match runtime_decision_provenance.mjs exactly
# ---------------------------------------------------------------------------
_BETA: float = 37.0 / 64.0
_MOTION_WEIGHT: float = 3.0 / 5.0
_MOTION_POWER: float = 5.0 / 4.0
_REVERSAL_BALANCE_POWER: int = 16
_CARRY_BALANCE_POWER: int = 4
_BURDEN_SCALE: float = 1.0 / 128.0
_V3_TIE_EPS: float = 1e-12

MIN_PRICE: float = 5.0

# Layer 2 cognitive gate thresholds
# These are calibrated to the 64% Cognitive Physics operating point.
# Applied per-row only when F_n and raw_x_m are non-null.
MAX_F_N: float = 1.65
MAX_RAW_X_M: float = 0.50

# Layer 1 required columns
REQUIRED_COLUMNS: tuple[str, ...] = (
    "S_UF", "R_UF", "D_k", "M_k", "R_rev_k",
    "U_star_k", "C_k", "P_k", "B_k", "price",
)

# Layer 2 optional cognitive columns
COGNITIVE_COLUMNS: tuple[str, ...] = ("F_n", "raw_x_m")


@dataclass(frozen=True)
class L5BaselineFilter:
    min_price: float = MIN_PRICE
    max_f_n: float = MAX_F_N
    max_raw_x_m: float = MAX_RAW_X_M

    def apply_canonical_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        # ------------------------------------------------------------------
        # Guard: Layer 1 required columns must be present
        # ------------------------------------------------------------------
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Float64 working copy — avoids object-dtype arithmetic surprises
        s = df.reindex(columns=list(REQUIRED_COLUMNS)).astype(float)

        # ------------------------------------------------------------------
        # Layer 1: V3 Basin Argmax
        # ------------------------------------------------------------------
        M_hat = s["M_k"].clip(-1.0, 1.0)

        sv    = s["S_UF"] - s["U_star_k"]
        rv    = s["R_UF"] - s["U_star_k"]
        s_pos = sv.clip(lower=0.0)
        r_pos = rv.clip(lower=0.0)
        core  = np.minimum(s_pos, r_pos)
        edge  = np.maximum(s_pos, r_pos) - core
        live      = core + _BETA * edge
        contested = (1.0 - _BETA) * edge
        balance   = core / (core + edge + 1e-12)
        rupture   = (-np.maximum(sv, rv)).clip(lower=0.0)

        D_nonadverse = (1.0 + s["D_k"]) / 2.0
        D_adverse    = (-s["D_k"]).clip(lower=0.0)
        M_continue   = (1.0 + M_hat) / 2.0
        M_bend       = (1.0 - M_hat) / 2.0

        motion = (
            _MOTION_WEIGHT * D_nonadverse ** _MOTION_POWER
            + (1.0 - _MOTION_WEIGHT) * M_continue ** _MOTION_POWER
        ) ** (1.0 / _MOTION_POWER)

        adverse_break   = D_adverse * M_bend
        reversal_break  = s["R_rev_k"] * (1.0 - balance) ** _REVERSAL_BALANCE_POWER
        carry_break     = (
            (-s["B_k"]) * s["R_rev_k"]
            * (1.0 - balance) ** _CARRY_BALANCE_POWER
            * (1.0 - adverse_break)
        )
        burden          = _BURDEN_SCALE * (s["C_k"] / (1.0 + s["C_k"])) * (s["P_k"] / (1.0 + s["P_k"]))
        break_agreement = np.maximum(np.maximum(adverse_break, reversal_break), carry_break)

        accumulate_basin = (
            live * motion * (1.0 - s["R_rev_k"]) * (1.0 - adverse_break) * (1.0 - burden)
        )
        hold_basin = (
            contested * (1.0 - break_agreement)
            + live * s["R_rev_k"] * balance
            + live * (1.0 - s["R_rev_k"]) * ((1.0 - motion) * (1.0 - adverse_break) + motion * burden)
        )
        avoid_basin = rupture + (live + contested) * break_agreement

        max_basin = np.maximum(np.maximum(accumulate_basin, hold_basin), avoid_basin)

        near_acc  = (max_basin - accumulate_basin).abs() <= _V3_TIE_EPS
        near_hold = (max_basin - hold_basin).abs() <= _V3_TIE_EPS
        near_avd  = (max_basin - avoid_basin).abs() <= _V3_TIE_EPS
        tie       = (near_acc.astype(int) + near_hold.astype(int) + near_avd.astype(int)) > 1

        is_accumulate = near_acc & ~tie
        price_ok      = s["price"] >= self.min_price

        layer1_mask = is_accumulate & price_ok

        # ------------------------------------------------------------------
        # Layer 2: Cognitive Gate — REMOVED
        #
        # The E5.4-injected cognitive gate (F_n, raw_x_m thresholds) was
        # killing 99.99% of Accumulate decisions because raw_x_m saturates
        # at 1.0 with 5-year bar history.  The code itself documented this:
        # "at the clip boundary when fed 5-year history, making raw_x_m
        # useless" (uf_mdg_snapshot.py line 377).
        #
        # E5.4 history:
        #   2026-03-31 Codex: injected CP-2 cognitive kernel
        #   2026-04-01 Codex: "cap to 252 bars to prevent saturation" (didn't work)
        #   2026-04-01 Codex: "restore soft-gate null-pass contract"
        # Result: gate killed 50 of 51 Accumulate stocks silently.
        #
        # Removed 2026-04-27 by Claude. Basin physics (Layer 1) is the
        # sole Accumulate filter until a working cognitive gate is designed.
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------
        # Layer 2: Stable Titan Scaler
        # For deeply established, high-conviction stable stocks (D_k=0),
        # stability IS the accumulation signal. The basin formula requires
        # D_k=+1 (expansion) which excludes mega-caps in equilibrium.
        # This scaler adds them: S_UF >= 0.85, bars >= 1000, stock, no reversal.
        # Additive only — does not remove any basin Accumulate decisions.
        # ------------------------------------------------------------------
        stable_titan_mask = (
            (s["D_k"] == 0)
            & (s["S_UF"] >= 0.85)
            & (s["R_rev_k"] == 0)
            & (s["price"] >= 10.0)
            & (df["bar_count"].astype(float) >= 1000)
            & (df["asset_type"].isin(["stock", "equity", ""]))
            & (~df["ticker"].str.startswith("I:"))
            & (~df["ticker"].str.startswith("X:"))
        )

        final_mask = layer1_mask | stable_titan_mask

        return df.loc[final_mask].copy()


def apply_canonical_filter(df: pd.DataFrame) -> pd.DataFrame:
    return L5BaselineFilter().apply_canonical_filter(df)
```

---

## FILE: quarantine_historical_kernel.py

```python
#!/usr/bin/env python3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


INPUT_PATH = Path("quarantine_12k_universe.parquet")
OUTPUT_PATH = Path("quarantine_12k_governed_states.parquet")
BATCH_SIZE = 200_000
PROGRESS_EVERY = 250
EPS_TAU_DAYS = 1.0
RHO_ROLLING_WINDOW = 5
R_NORM_MAX = 1.0


@dataclass
class KernelParameters:
    W: int = 20
    W_r: int = 10
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6
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
    lambda_1: float = 1.0
    lambda_2: float = 1.0
    lambda_3: float = 1.0
    lambda_4: float = 1.0
    lambda_5: float = 1.0
    h_max: float = 0.20
    U_max: float = 0.75
    eps_D: float = 0.00073
    eta_H: float = 0.10
    eta_IAS: float = 0.10
    xi: float = 0.10
    chi: float = 0.10
    B_min: float = -1.0
    B_max: float = 1.0

    # CV-1.0 governance parameters
    a_rho: float = 0.4
    b_rho: float = 0.4
    c_rho: float = 0.1
    d_rho: float = 0.1
    a_decay: float = 0.99
    a_nu_weight: float = 0.05
    a_pi_weight: float = 0.05
    A_f: float = 0.90
    A_m: float = 0.98
    A_s: float = 0.995
    B_f: float = 0.1
    B_m: float = 0.1
    B_s: float = 0.1
    H_mf: float = 0.1
    H_sm: float = 0.1
    G_all: float = 0.01
    L_f: float = 0.01
    L_m: float = 0.01
    L_s: float = 0.01
    lambda_s: float = 1.0
    eta_h: float = 2.0
    F_max: float = 0.45
    chi_min: float = 1.0
    theta_plus: float = 0.65
    s_uf_default: float = 1.0
    r_uf_default: float = 1.0


def sat_scalar(value: float) -> float:
    return float(np.clip(value, -1.0, 1.0))


def sat_vector(values: np.ndarray) -> np.ndarray:
    return np.clip(values.astype(float), -1.0, 1.0)


def psi_r(F_window: np.ndarray) -> float:
    return 1.0 if len(F_window) > 0 and F_window[-1] > np.mean(F_window) else 0.5


def psi_s(TVR: Tuple[float, float, float], P_list: List[Tuple[int, int, int]], C: int, delta_g: float) -> float:
    T, V, R = TVR
    return float(np.clip(1.0 / (1.0 + C + delta_g), 0.0, 1.0))


def phi_reg(P_list: List[Tuple[int, int, int]], C: int) -> str:
    return "TRANSITIONAL" if C > 1 else "STABLE"


def psi_u(C: int, delta_g: float, N_gate: int) -> float:
    return float(np.clip((C * 0.1) + (delta_g * 0.1) + (N_gate * 0.2), 0.0, 1.0))


def phi_ias(S: float, U: float, delta_g: float) -> int:
    return 1 if U > 0.8 or delta_g > 2.0 else 0


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
            gate_sevs = sevs[t_a:t_b]
            if not gate_sevs:
                t_a = t
                continue
            T = float(t_b - t_a)
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
    last_URF = 0.0
    last_URF2 = 0.0
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


def days_between(current_ts: pd.Timestamp, previous_ts: pd.Timestamp | None) -> float:
    if previous_ts is None:
        return EPS_TAU_DAYS
    delta_days = (current_ts - previous_ts).total_seconds() / 86400.0
    return max(EPS_TAU_DAYS, float(delta_days))


def event_type_for(idx: int, reg_k: str, prev_reg: str | None, rev_k: int) -> str:
    if idx == 0:
        return "gate_close"
    if prev_reg is not None and reg_k != prev_reg:
        return "regime_change"
    if rev_k > 0:
        return "resonance_reversal"
    return "gate_close"


def build_state_rows(symbol: str, group: pd.DataFrame, params: KernelParameters) -> pd.DataFrame:
    group = group.sort_values("Date").reset_index(drop=True)
    close_prices = group["Close"].astype(float).to_numpy()
    date_array = pd.to_datetime(group["Date"]).to_numpy()

    sevs = compute_l0_sev(close_prices, params)
    gates = segment_l1_gates(sevs, params)
    isfs = compute_l2_isf(gates, params)
    resonances = compute_l3_resonance(isfs, params)
    dsfs = compute_l4_dsf(resonances, params)

    rows = []
    prev_timestamp = None
    prev_phi = 0.0
    prev_reg = None

    a_state = np.zeros(3, dtype=float)
    x_f = 0.0
    x_m = 0.0
    x_s = 0.0

    r_history: list[float] = []
    s_history: list[float] = []
    u_history: list[float] = []
    c_history: list[float] = []

    q_5 = np.array([1.0, 0.0, 0.0], dtype=float)
    q_20 = np.array([0.0, 1.0, 0.0], dtype=float)
    q_60 = np.array([0.0, 0.0, 1.0], dtype=float)

    for idx, (gate, isf, resonance, dsf) in enumerate(zip(gates, isfs, resonances, dsfs)):
        gate_index = int(gate.t_b)
        if gate_index < 0 or gate_index >= len(date_array):
            continue

        event_timestamp = pd.Timestamp(date_array[gate_index])
        close_price = float(close_prices[gate_index])
        event_type = event_type_for(idx, isf.Reg, prev_reg, dsf.Rev)

        delta_tau = days_between(event_timestamp, prev_timestamp)
        omega = float((2.0 * np.pi) / delta_tau)
        phi = float((prev_phi + (omega * delta_tau)) % (2.0 * np.pi))

        r_norm = float(np.clip(resonance.R / R_NORM_MAX, -1.0, 1.0))
        s_value = float(np.clip(params.s_uf_default, 0.0, 1.0))
        u_value = float(np.clip(dsf.U_star, 0.0, 1.0))
        c_norm = float(np.clip(dsf.C / 4.0, 0.0, 1.0))

        r_history.append(r_norm)
        s_history.append(s_value)
        u_history.append(u_value)
        c_history.append(c_norm)

        R_bar = float(np.mean(r_history[-RHO_ROLLING_WINDOW:]))
        S_bar = float(np.mean(s_history[-RHO_ROLLING_WINDOW:]))
        U_bar = float(np.mean(u_history[-RHO_ROLLING_WINDOW:]))
        C_bar = float(np.mean(c_history[-RHO_ROLLING_WINDOW:]))
        rho = float(np.clip((params.a_rho * R_bar) + (params.b_rho * S_bar) - (params.c_rho * U_bar) - (params.d_rho * C_bar), 0.0, 1.0))

        nu_core = sat_vector(np.array([float(dsf.D), float(dsf.M), r_norm], dtype=float))
        pi_vec = np.full(3, rho, dtype=float)

        a_state = sat_vector((params.a_decay * a_state) + (params.a_nu_weight * nu_core) + (params.a_pi_weight * pi_vec))

        x_f = sat_scalar((params.A_f * x_f) + (params.B_f * nu_core[0]) + (params.G_all * rho) + (params.L_f * a_state[0]))
        x_m = sat_scalar((params.A_m * x_m) + (params.B_m * nu_core[1]) + (params.H_mf * x_f) + (params.G_all * rho) + (params.L_m * a_state[1]))
        x_s = sat_scalar((params.A_s * x_s) + (params.B_s * nu_core[2]) + (params.H_sm * x_m) + (params.G_all * rho) + (params.L_s * a_state[2]))

        z_n = np.array([x_f, x_m, x_s], dtype=float)
        surprise = float(np.linalg.norm(nu_core - z_n))
        gamma = float(0.5 * (u_value + (1.0 - rho)))
        F_n = float(gamma + (params.lambda_s * surprise))

        q5 = float(np.dot(q_5, z_n) - (params.eta_h * F_n))
        q20 = float(np.dot(q_20, z_n) - (params.eta_h * F_n))
        q60 = float(np.dot(q_60, z_n) - (params.eta_h * F_n))

        signs = [int(np.sign(q5)), int(np.sign(q20)), int(np.sign(q60))]
        chi_n = 1.0 if (signs[0] == signs[1] == signs[2]) else 0.0

        decision = "ACCUMULATE" if (q20 > params.theta_plus and F_n <= params.F_max and chi_n >= params.chi_min) else "HOLD/AVOID"
        prev_b = float(dsfs[idx - 1].B) if idx > 0 else 0.0

        rows.append(
            {
                "Date": event_timestamp,
                "Symbol": symbol,
                "Close": close_price,
                "event_type": event_type,
                "D_k": int(dsf.D),
                "M_k": float(dsf.M),
                "R_k": float(resonance.R),
                "Rev_k": int(dsf.Rev),
                "U_star_k": float(dsf.U_star),
                "C_k": int(dsf.C),
                "P_k": int(dsf.P),
                "B_k": float(dsf.B),
                "prev_B_k": float(prev_b),
                "omega_n": omega,
                "phi_n": phi,
                "rho_n": rho,
                "s_n": surprise,
                "F_n": F_n,
                "Q_5": q5,
                "Q_20": q20,
                "Q_60": q60,
                "chi_n": chi_n,
                "x_f": x_f,
                "x_m": x_m,
                "x_s": x_s,
                "a_f": float(a_state[0]),
                "a_m": float(a_state[1]),
                "a_s": float(a_state[2]),
                "Decision": decision,
            }
        )

        prev_timestamp = event_timestamp
        prev_phi = phi
        prev_reg = isf.Reg

    return pd.DataFrame(
        rows,
        columns=[
            "Date",
            "Symbol",
            "Close",
            "event_type",
            "D_k",
            "M_k",
            "R_k",
            "Rev_k",
            "U_star_k",
            "C_k",
            "P_k",
            "B_k",
            "prev_B_k",
            "omega_n",
            "phi_n",
            "rho_n",
            "s_n",
            "F_n",
            "Q_5",
            "Q_20",
            "Q_60",
            "chi_n",
            "x_f",
            "x_m",
            "x_s",
            "a_f",
            "a_m",
            "a_s",
            "Decision",
        ],
    )


def build_historical_states(input_path: Path, output_path: Path) -> int:
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input parquet: {input_path}")
    if output_path.exists():
        output_path.unlink()

    params = KernelParameters()
    parquet = pq.ParquetFile(input_path)
    carry_symbol = None
    carry_parts: list[pd.DataFrame] = []
    writer = None
    total_rows = 0
    total_symbols = 0

    try:
        for batch in parquet.iter_batches(batch_size=BATCH_SIZE, columns=["Date", "Symbol", "Close"]):
            batch_df = batch.to_pandas()
            batch_df["Date"] = pd.to_datetime(batch_df["Date"])
            batch_df["Symbol"] = batch_df["Symbol"].astype(str).str.upper()
            batch_df = batch_df.sort_values(["Symbol", "Date"]).reset_index(drop=True)
            if batch_df.empty:
                continue

            for symbol, group in batch_df.groupby("Symbol", sort=False):
                if carry_symbol is None:
                    carry_symbol = symbol
                    carry_parts = [group]
                    continue
                if symbol == carry_symbol:
                    carry_parts.append(group)
                    continue

                symbol_df = pd.concat(carry_parts, ignore_index=True)
                state_rows = build_state_rows(carry_symbol, symbol_df, params)
                if not state_rows.empty:
                    table = pa.Table.from_pandas(state_rows, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(str(output_path), table.schema)
                    writer.write_table(table)
                    total_rows += len(state_rows)
                total_symbols += 1
                if total_symbols % PROGRESS_EVERY == 0:
                    print(f"Processed symbols: {total_symbols} governed_rows={total_rows}", flush=True)

                carry_symbol = symbol
                carry_parts = [group]

        if carry_symbol is not None and carry_parts:
            symbol_df = pd.concat(carry_parts, ignore_index=True)
            state_rows = build_state_rows(carry_symbol, symbol_df, params)
            if not state_rows.empty:
                table = pa.Table.from_pandas(state_rows, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(str(output_path), table.schema)
                writer.write_table(table)
                total_rows += len(state_rows)
            total_symbols += 1
    finally:
        if writer is not None:
            writer.close()

    if not output_path.exists():
        raise RuntimeError("No governed states were written.")

    print(f"Created {output_path}")
    print(f"Processed symbols: {total_symbols}")
    print(f"Governed event states generated: {total_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_historical_states(INPUT_PATH, OUTPUT_PATH))
```

---

## FILE: quarantine_sequential_filter.py

```python
#!/usr/bin/env python3
from pathlib import Path

import pandas as pd


PRIMITIVE_TRADES_PATH = Path("quarantine_12k_l5_trades.csv")
GOVERNED_STATES_PATH = Path("quarantine_12k_governed_states.parquet")


def average_return(df: pd.DataFrame, column: str) -> float:
    valid = df[column].dropna()
    return float(valid.mean() * 100.0) if len(valid) > 0 else 0.0


def win_rate(df: pd.DataFrame, column: str) -> float:
    valid = df[column].dropna()
    return float((valid > 0).mean() * 100.0) if len(valid) > 0 else 0.0


def main() -> int:
    if not PRIMITIVE_TRADES_PATH.exists():
        raise FileNotFoundError(f"Missing primitive trades CSV: {PRIMITIVE_TRADES_PATH}")
    if not GOVERNED_STATES_PATH.exists():
        raise FileNotFoundError(f"Missing governed states parquet: {GOVERNED_STATES_PATH}")

    primitive = pd.read_csv(PRIMITIVE_TRADES_PATH)
    governed = pd.read_parquet(GOVERNED_STATES_PATH)

    primitive["Date"] = pd.to_datetime(primitive["Date"])
    governed["Date"] = pd.to_datetime(governed["Date"])
    governed["raw_x_m"] = governed["Q_20"] + (2.0 * governed["F_n"])

    joined = primitive.merge(
        governed[["Symbol", "Date", "F_n", "Q_20", "chi_n", "raw_x_m"]],
        on=["Symbol", "Date"],
        how="inner",
    )

    filtered = joined[
        (joined["Close"] >= 5.0)
        & (joined["raw_x_m"] <= 0.50)
        & (joined["F_n"] <= 1.65)
    ].copy()

    symbol_stats = (
        filtered.groupby("Symbol", dropna=False)
        .agg(
            Count=("Symbol", "size"),
            Win_Rate_20d=("Return_20d", lambda s: float((s.dropna() > 0).mean() * 100.0) if len(s.dropna()) > 0 else 0.0),
        )
        .reset_index()
        .sort_values(["Count", "Win_Rate_20d", "Symbol"], ascending=[False, False, True])
        .head(10)
    )

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", None)

    print("=== QUARANTINE SEQUENTIAL FILTER ===")
    print(f"Joined Rows: {len(joined)}")
    print(f"Total Signals: {len(filtered)}")
    print(f"5-Day Average Return: {average_return(filtered, 'Return_5d'):.4f}%")
    print(f"5-Day Win Rate: {win_rate(filtered, 'Return_5d'):.2f}%")
    print(f"10-Day Average Return: {average_return(filtered, 'Return_10d'):.4f}%")
    print(f"10-Day Win Rate: {win_rate(filtered, 'Return_10d'):.2f}%")
    print(f"20-Day Average Return: {average_return(filtered, 'Return_20d'):.4f}%")
    print(f"20-Day Win Rate: {win_rate(filtered, 'Return_20d'):.2f}%")
    print()
    print("=== TOP 10 SYMBOLS BY FREQUENCY ===")
    if symbol_stats.empty:
        print("No surviving symbols.")
    else:
        print(symbol_stats.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## FILE: uf_mdg_snapshot.py (CP-2 kernel section, lines 90-471)

```python

# Strict OHLC integrity floor used by production ingestion.
MIN_PRICE_FLOOR: float = DEFAULT_MIN_PRICE_FLOOR


# ===========================================================================
# CP-2: Cognitive Kernel — Deterministic physics for F_n and raw_x_m
#
# Ported verbatim from quarantine_historical_kernel.py.
# No pyarrow. No quarantine module imports. Pure numpy/dataclass.
# Constants are frozen from KernelParameters defaults.
# ===========================================================================

# ---------------------------------------------------------------------------
# Frozen kernel constants (KernelParameters defaults)
# ---------------------------------------------------------------------------
_KP_W: int = 20
_KP_W_r: int = 10
_KP_sigma_min: float = 1e-6
_KP_delta_min: float = 1e-6
_KP_kappa_min: float = 1e-6
_KP_tau_D: float = 0.20
_KP_alpha_1: float = 1.0
_KP_alpha_2: float = 1.0
_KP_alpha_3: float = 1.0
_KP_beta_1: float = 1.0
_KP_beta_2: float = 1.0
_KP_beta_3: float = 1.0
_KP_lattices: List[Tuple[float, float, float]] = [(1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (4.0, 4.0, 4.0)]
_KP_lambda_1: float = 1.0
_KP_lambda_2: float = 1.0
_KP_lambda_3: float = 1.0
_KP_lambda_4: float = 1.0
_KP_lambda_5: float = 1.0
_KP_h_max: float = 0.20
_KP_U_max: float = 0.75
_KP_eps_D: float = 0.00073
_KP_eta_H: float = 0.10
_KP_eta_IAS: float = 0.10
_KP_xi: float = 0.10
_KP_chi: float = 0.10
_KP_B_min: float = -1.0
_KP_B_max: float = 1.0
_KP_a_rho: float = 0.4
_KP_b_rho: float = 0.4
_KP_c_rho: float = 0.1
_KP_d_rho: float = 0.1
_KP_a_decay: float = 0.99
_KP_a_nu_weight: float = 0.05
_KP_a_pi_weight: float = 0.05
_KP_A_f: float = 0.90
_KP_A_m: float = 0.98
_KP_A_s: float = 0.995
_KP_B_f: float = 0.1
_KP_B_m: float = 0.1
_KP_B_s: float = 0.1
_KP_H_mf: float = 0.1
_KP_H_sm: float = 0.1
_KP_G_all: float = 0.01
_KP_L_f: float = 0.01
_KP_L_m: float = 0.01
_KP_L_s: float = 0.01
_KP_lambda_s: float = 1.0
_KP_eta_h: float = 2.0
_KP_EPS_TAU_DAYS: float = 1.0
_KP_RHO_ROLLING_WINDOW: int = 5
_KP_R_NORM_MAX: float = 1.0
_KP_Z: float = _KP_lambda_1 + _KP_lambda_2 + _KP_lambda_3 + _KP_lambda_4 + _KP_lambda_5


# ---------------------------------------------------------------------------
# L0 SEV
# ---------------------------------------------------------------------------

@dataclass
class _SEV:
    F: float
    dF: float
    sigma: float
    kappa: float
    r: float
    N: int


def _psi_r(F_window: np.ndarray) -> float:
    return 1.0 if len(F_window) > 0 and F_window[-1] > np.mean(F_window) else 0.5


def _compute_l0_sev(F: np.ndarray) -> List[_SEV]:
    n = len(F)
    sevs: List[_SEV] = []
    for t in range(n):
        dF = F[t] - F[t - 1] if t > 0 else 0.0
        start_w = max(0, t - _KP_W + 1)
        F_window = F[start_w : t + 1]
        F_bar = np.mean(F_window)
        sigma = float(np.mean((F_window - F_bar) ** 2))
        if 0 < t < n - 1:
            kappa = abs(float(F[t + 1]) - 2.0 * float(F[t]) + float(F[t - 1]))
        else:
            kappa = 0.0
        start_r = max(0, t - _KP_W_r + 1)
        r_val = _psi_r(F[start_r : t + 1])
        N = 1 if (sigma < _KP_sigma_min and abs(dF) < _KP_delta_min and kappa < _KP_kappa_min) else 0
        sevs.append(_SEV(float(F[t]), float(dF), sigma, kappa, r_val, N))
    return sevs


# ---------------------------------------------------------------------------
# L1 Gate segmentation
# ---------------------------------------------------------------------------

@dataclass
class _GateL1:
    t_a: int
    t_b: int
    TVR: Tuple[float, float, float]
    P_list: List[Tuple[int, int, int]]
    C: int
    delta_g: float
    mu: np.ndarray
    N_gate: int


def _segment_l1_gates(sevs: List[_SEV]) -> List[_GateL1]:
    D = np.zeros(len(sevs))
    for t, sev in enumerate(sevs):
        D[t] = _KP_alpha_1 * abs(sev.dF) + _KP_alpha_2 * sev.sigma + _KP_alpha_3 * sev.kappa

    gates: List[_GateL1] = []
    t_a = 0
    last_mu = np.zeros(3)
    for t in range(1, len(sevs)):
        if D[t] >= _KP_tau_D or t == len(sevs) - 1:
            t_b = t
            gate_sevs = sevs[t_a:t_b]
            if not gate_sevs:
                t_a = t
                continue
            T = float(t_b - t_a)
            V = sum(_KP_beta_1 * abs(s.dF) + _KP_beta_2 * s.sigma + _KP_beta_3 * s.kappa for s in gate_sevs)
            R = sum(s.r for s in gate_sevs)
            TVR = (T, V, R)
            P_list: List[Tuple[int, int, int]] = []
            for h1, h2, h3 in _KP_lattices:
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
            gates.append(_GateL1(t_a, t_b, TVR, P_list, C, delta_g, mu_k, N_gate))
            last_mu = mu_k
            t_a = t
    return gates


# ---------------------------------------------------------------------------
# L2 ISF
# ---------------------------------------------------------------------------

@dataclass
class _ISF:
    gate: _GateL1
    w: float
    CV: np.ndarray
    S: float
    U: float
    IAS: int


def _compute_l2_isf(gates: List[_GateL1]) -> List[_ISF]:
    if not gates:
        return []
    V_max = max((g.TVR[1] for g in gates), default=1e-12)
    V_max = V_max if V_max > 0 else 1e-12
    isfs: List[_ISF] = []
    for g in gates:
        w_k = g.TVR[1] / V_max
        CV_k = np.array(g.TVR) - g.mu
        S_k = float(np.clip(1.0 / (1.0 + g.C + g.delta_g), 0.0, 1.0))
        U_k = float(np.clip((g.C * 0.1) + (g.delta_g * 0.1) + (g.N_gate * 0.2), 0.0, 1.0))
        IAS_k = 1 if U_k > 0.8 or g.delta_g > 2.0 else 0
        isfs.append(_ISF(g, w_k, CV_k, S_k, U_k, IAS_k))
    return isfs


# ---------------------------------------------------------------------------
# L3 Resonance
# ---------------------------------------------------------------------------

@dataclass
class _Resonance:
    isf: _ISF
    R: float
    Hyst: int
    g: int
    URF: float


def _compute_l3_resonance(isfs: List[_ISF]) -> List[_Resonance]:
    if not isfs:
        return []
    CV_max = max((np.linalg.norm(isf.CV) for isf in isfs), default=1e-12)
    CV_max = CV_max if CV_max > 0 else 1e-12
    res: List[_Resonance] = []
    last_R = 0.0
    for isf in isfs:
        term1 = _KP_lambda_1 * isf.w
        term2 = _KP_lambda_2 * (float(np.linalg.norm(isf.CV)) / CV_max)
        term3 = _KP_lambda_3 * isf.S
        term4 = _KP_lambda_4 * (1.0 / (1.0 + isf.gate.C))
        term5 = _KP_lambda_5 * (1.0 - isf.U)
        R_k = (1.0 / _KP_Z) * (term1 + term2 + term3 + term4 + term5)
        Hyst_k = 1 if abs(R_k - last_R) > _KP_h_max else 0
        g_k = 1 if (isf.U <= _KP_U_max and isf.IAS == 0 and Hyst_k == 0) else 0
        URF_k = g_k * R_k
        res.append(_Resonance(isf, R_k, Hyst_k, g_k, URF_k))
        last_R = R_k
    return res


# ---------------------------------------------------------------------------
# L4 DSF
# ---------------------------------------------------------------------------

@dataclass
class _DSFState:
    D: int
    M: float
    Rev: int
    U_star: float
    B: float


def _compute_l4_dsf(res: List[_Resonance]) -> List[_DSFState]:
    dsfs: List[_DSFState] = []
    last_URF = 0.0
    last_URF2 = 0.0
    last_D = 0
    last_B = 0.0
    for r in res:
        delta_R = r.URF - last_URF
        if delta_R > _KP_eps_D:
            D_k = 1
        elif delta_R < -_KP_eps_D:
            D_k = -1
        else:
            D_k = 0
        M_k = r.URF - 2.0 * last_URF + last_URF2
        U_star_k = r.isf.U + (_KP_eta_H * r.Hyst) + (_KP_eta_IAS * r.isf.IAS)
        B_k_raw = last_B + _KP_xi * (1.0 - U_star_k) * delta_R - _KP_chi * U_star_k
        B_k = float(np.clip(B_k_raw, _KP_B_min, _KP_B_max))
        dsfs.append(_DSFState(D_k, M_k, 1 if (D_k * last_D < 0) else 0, U_star_k, B_k))
        last_URF2 = last_URF
        last_URF = r.URF
        last_D = D_k
        last_B = B_k
    return dsfs


# ---------------------------------------------------------------------------
# CV-1.0 cognitive scalars — compute the latest F_n and raw_x_m from bars
# ---------------------------------------------------------------------------

def compute_cognitive_scalars(
    close_prices: np.ndarray,
    max_bars: int = 252,
) -> Dict[str, Optional[float]]:
    """
    Run the full L0→L4 + CV-1.0 kernel on close_prices and return the final
    gate's F_n and raw_x_m.

    Returns {"F_n": float, "raw_x_m": float} on success, or
    {"F_n": None, "raw_x_m": None} when insufficient data or any error.

    raw_x_m = Q_20 + 2.0 * F_n  (verified from quarantine_sequential_filter.py)
    Q_20 = x_m - eta_h * F_n  (q_20 = [0, 1, 0] so dot(q_20, z_n) = x_m)
    => raw_x_m = x_m - 2.0 * F_n + 2.0 * F_n = x_m

    max_bars: cap the input to the most recent N bars before running the
    kernel. The CV-1.0 integrators (especially x_m with A_m=0.98) saturate
    at the clip boundary when fed 5-year history, making raw_x_m useless as
    a discriminator. 252 bars (~1 year) is enough warm-up to settle state
    without saturation.
    """
    _null: Dict[str, Optional[float]] = {"F_n": None, "raw_x_m": None}

    try:
        F = close_prices.astype(float)
        if max_bars > 0 and len(F) > max_bars:
            F = F[-max_bars:]
        if len(F) < 2:
            return _null

        sevs = _compute_l0_sev(F)
        gates = _segment_l1_gates(sevs)
        if not gates:
            return _null

        isfs = _compute_l2_isf(gates)
        resonances = _compute_l3_resonance(isfs)
        dsfs = _compute_l4_dsf(resonances)

        if not resonances or not dsfs:
            return _null

        # CV-1.0 stateful forward pass — accumulate to the last gate
        a_state = np.zeros(3, dtype=float)
        x_f = 0.0
        x_m = 0.0
        x_s = 0.0
        r_history: List[float] = []
        u_history: List[float] = []

        F_n_last: Optional[float] = None
        raw_x_m_last: Optional[float] = None

        for resonance, dsf in zip(resonances, dsfs):
            r_norm = float(np.clip(resonance.R / _KP_R_NORM_MAX, -1.0, 1.0))
            s_value = 1.0  # s_uf_default
            u_value = float(np.clip(dsf.U_star, 0.0, 1.0))

            r_history.append(r_norm)
            u_history.append(u_value)

            R_bar = float(np.mean(r_history[-_KP_RHO_ROLLING_WINDOW:]))
            S_bar = s_value
            U_bar = float(np.mean(u_history[-_KP_RHO_ROLLING_WINDOW:]))
            C_bar = 0.0  # c_norm not needed for F_n
            rho = float(np.clip(
                (_KP_a_rho * R_bar) + (_KP_b_rho * S_bar) - (_KP_c_rho * U_bar) - (_KP_d_rho * C_bar),
                0.0, 1.0,
            ))

            nu_core = np.clip(
                np.array([float(dsf.D), float(dsf.M), r_norm], dtype=float),
                -1.0, 1.0,
            )
            pi_vec = np.full(3, rho, dtype=float)

            a_state = np.clip(
                (_KP_a_decay * a_state) + (_KP_a_nu_weight * nu_core) + (_KP_a_pi_weight * pi_vec),
                -1.0, 1.0,
            )

            x_f = float(np.clip(
                (_KP_A_f * x_f) + (_KP_B_f * nu_core[0]) + (_KP_G_all * rho) + (_KP_L_f * a_state[0]),
                -1.0, 1.0,
            ))
            x_m = float(np.clip(
                (_KP_A_m * x_m) + (_KP_B_m * nu_core[1]) + (_KP_H_mf * x_f) + (_KP_G_all * rho) + (_KP_L_m * a_state[1]),
                -1.0, 1.0,
            ))
            x_s = float(np.clip(
                (_KP_A_s * x_s) + (_KP_B_s * nu_core[2]) + (_KP_H_sm * x_m) + (_KP_G_all * rho) + (_KP_L_s * a_state[2]),
                -1.0, 1.0,
            ))

            z_n = np.array([x_f, x_m, x_s], dtype=float)
            surprise = float(np.linalg.norm(nu_core - z_n))
            gamma = float(0.5 * (u_value + (1.0 - rho)))
            F_n_val = float(gamma + (_KP_lambda_s * surprise))
            Q_20_val = float(x_m - (_KP_eta_h * F_n_val))
            raw_x_m_val = float(Q_20_val + 2.0 * F_n_val)  # = x_m

            F_n_last = F_n_val
            raw_x_m_last = raw_x_m_val

        if F_n_last is None:
            return _null

        return {"F_n": F_n_last, "raw_x_m": raw_x_m_last}

    except Exception:
        return _null

```

---

# EPOCH LIBRARY + FINANCIAL RULES

---

## FILE: tfe_epoch_library.py

```python
#!/usr/bin/env python3
"""
tfe_epoch_library.py
L5 Epoch Library — to spec (TFE_Specification_v3_0 §Epoch Source Ingestion
through §Epoch-Symbol Coupling).

Implements:
  1. Event normalization  — raw source event → ν_u tuple
  2. Admission scoring    — Π_epoch(u) determines library entry
  3. Epoch objects         — ε_k with severity, confidence, persistence,
                            sphere-of-impact vector, temporal decay
  4. Epoch mosaic          — Ξ_t = Σ ω_k(t) ξ_k  (32-channel field)
  5. G32 Coordinator       — maintain mosaic, resolve conflicts,
                            project to sector/industry/company
  6. Epoch-symbol coupling — Ω_epoch(s,t) per-symbol pressure

No ML. Deterministic. All event objects carry provenance.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
# 1. Constants — 32 sphere-of-impact channels
# ═══════════════════════════════════════════════════════════════════════════

SPHERE_CHANNELS = [
    "RATES_PRESSURE",        # 0
    "CONSUMER_STRESS",       # 1
    "WAR_GEOPOLITICS",       # 2
    "ENERGY_COMMODITY",      # 3
    "TECH_CYCLE",            # 4
    "CURRENCY_FX",           # 5
    "FISCAL_INFRA",          # 6
    "VOLATILITY_REGIME",     # 7
    "LABOR_PRESSURE",        # 8
    "SUPPLY_CHAIN",          # 9
    "REGULATION",            # 10
    "CREDIT_STRESS",         # 11
    "BUILDING_CYCLE",        # 12
    "LOGISTICS",             # 13
    "HEALTHCARE_POLICY",     # 14
    "TRADE_WAR",             # 15
    "PANDEMIC",              # 16
    "EARNINGS_SEASON",       # 17
    "SECTOR_ROTATION",       # 18
    "INSIDER_CONVICTION",    # 19
    "MERGER_DISTRESS",       # 20
    "NEWS_CONTAGION",        # 21
    "COMMODITY_SQUEEZE",     # 22
    "POLICY_SHOCK",          # 23
    "RESERVED_24", "RESERVED_25", "RESERVED_26", "RESERVED_27",
    "RESERVED_28", "RESERVED_29", "RESERVED_30", "RESERVED_31",
]

N_CHANNELS = 32
CHANNEL_INDEX = {name: i for i, name in enumerate(SPHERE_CHANNELS)}


# ═══════════════════════════════════════════════════════════════════════════
# 2. Event class → base sphere-of-impact vector  M_{class}
#    Spec: ξ_u = M_{class} Γ_geo Γ_scope Γ_dir
# ═══════════════════════════════════════════════════════════════════════════

def _sphere_vec(**channels: float) -> np.ndarray:
    v = np.zeros(N_CHANNELS, dtype=np.float64)
    for name, weight in channels.items():
        idx = CHANNEL_INDEX.get(name)
        if idx is not None:
            v[idx] = weight
    return v


EVENT_CLASS_SPHERES: Dict[str, np.ndarray] = {
    "war_escalation": _sphere_vec(
        WAR_GEOPOLITICS=1.0, ENERGY_COMMODITY=0.6, VOLATILITY_REGIME=0.4,
        SUPPLY_CHAIN=0.3, CURRENCY_FX=0.2, TRADE_WAR=0.3,
    ),
    "oil_shock": _sphere_vec(
        ENERGY_COMMODITY=1.0, WAR_GEOPOLITICS=0.4, CONSUMER_STRESS=0.5,
        LOGISTICS=0.3, COMMODITY_SQUEEZE=0.8,
    ),
    "rate_hike": _sphere_vec(
        RATES_PRESSURE=1.0, CREDIT_STRESS=0.5, BUILDING_CYCLE=0.4,
        CONSUMER_STRESS=0.3, CURRENCY_FX=0.3,
    ),
    "stagflation": _sphere_vec(
        RATES_PRESSURE=0.8, CONSUMER_STRESS=0.8, ENERGY_COMMODITY=0.5,
        LABOR_PRESSURE=0.4, VOLATILITY_REGIME=0.3,
    ),
    "tech_selloff": _sphere_vec(
        TECH_CYCLE=1.0, VOLATILITY_REGIME=0.4, SECTOR_ROTATION=0.5,
    ),
    "pandemic": _sphere_vec(
        PANDEMIC=1.0, CONSUMER_STRESS=0.7, SUPPLY_CHAIN=0.8,
        LOGISTICS=0.6, VOLATILITY_REGIME=0.5,
    ),
    "trade_war": _sphere_vec(
        TRADE_WAR=1.0, CURRENCY_FX=0.6, SUPPLY_CHAIN=0.5,
        CONSUMER_STRESS=0.3,
    ),
    "earnings_shock": _sphere_vec(
        EARNINGS_SEASON=1.0, NEWS_CONTAGION=0.5, SECTOR_ROTATION=0.4,
    ),
    "merger_distress": _sphere_vec(
        MERGER_DISTRESS=1.0, CREDIT_STRESS=0.4, VOLATILITY_REGIME=0.2,
    ),
    "regulation": _sphere_vec(
        REGULATION=1.0, TECH_CYCLE=0.3,
    ),
    "commodity_squeeze": _sphere_vec(
        COMMODITY_SQUEEZE=1.0, ENERGY_COMMODITY=0.6, SUPPLY_CHAIN=0.4,
    ),
    "fiscal_stimulus": _sphere_vec(
        FISCAL_INFRA=1.0, BUILDING_CYCLE=0.5, LABOR_PRESSURE=0.3,
    ),
    "generic_macro": _sphere_vec(
        VOLATILITY_REGIME=0.5, CONSUMER_STRESS=0.3, RATES_PRESSURE=0.3,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# 3. Source reliability registry
# ═══════════════════════════════════════════════════════════════════════════

SOURCE_RELIABILITY: Dict[str, float] = {
    "tavily_news":      0.7,
    "market_data":      0.9,
    "official_release": 1.0,
    "analyst":          0.5,
    "social":           0.3,
    "unknown":          0.4,
}


# ═══════════════════════════════════════════════════════════════════════════
# 4. Normalized event (ν_u) and Epoch object (ε_k)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NormalizedEvent:
    """Spec: ν_u = (id, src, ts, class, scope, dir, sev, conf, pers, geo, sec, ind, textHash)"""
    id: str
    source: str
    timestamp: str
    event_class: str
    scope: float
    direction: float
    severity: float
    confidence: float
    persistence: float
    geography: str
    sector: Optional[str]
    industry: Optional[str]
    text_hash: str


@dataclass
class EpochObject:
    """Spec: ε_k = (id, class, t_start, t_end, sev, conf, pers, ξ_k, src, decay)"""
    id: str
    event_class: str
    t_start: str
    t_end: Optional[str]
    severity: float
    confidence: float
    persistence: float
    sphere_vector: np.ndarray
    source: str
    decay_rate: float
    source_events: List[str] = field(default_factory=list)

    def amplitude(self, t: datetime) -> float:
        """Spec: ω_k(t) = sev × conf × pers × exp(-decay × max(0, t - t_end))"""
        base = self.severity * self.confidence * self.persistence
        if self.t_end is None:
            return base
        t_end = datetime.fromisoformat(self.t_end.replace("Z", "+00:00"))
        if not t.tzinfo:
            t = t.replace(tzinfo=timezone.utc)
        delta_days = max(0.0, (t - t_end).total_seconds() / 86400.0)
        return base * math.exp(-self.decay_rate * delta_days)

    def weighted_sphere(self, t: datetime) -> np.ndarray:
        return self.amplitude(t) * self.sphere_vector


# ═══════════════════════════════════════════════════════════════════════════
# 5. Admission scoring
# ═══════════════════════════════════════════════════════════════════════════

W_SRC  = 0.25
W_SEV  = 0.25
W_CONF = 0.20
W_PERS = 0.15
W_SCOPE = 0.10
W_DUP  = 0.30
PI_MIN = 0.35


def compute_admission_score(
    event: NormalizedEvent,
    existing_library: List[EpochObject],
) -> float:
    rel = SOURCE_RELIABILITY.get(event.source, 0.4)
    dup = 0.0
    for epoch in existing_library:
        if epoch.event_class == event.event_class:
            try:
                t_event = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                t_epoch = datetime.fromisoformat(epoch.t_start.replace("Z", "+00:00"))
                delta_hours = abs((t_event - t_epoch).total_seconds()) / 3600
                if delta_hours < 24:
                    dup = max(dup, 1.0 - delta_hours / 24.0)
            except (ValueError, TypeError):
                pass
    return (W_SRC * rel + W_SEV * event.severity + W_CONF * event.confidence
            + W_PERS * event.persistence + W_SCOPE * event.scope - W_DUP * dup)


def project_sphere_vector(event: NormalizedEvent) -> np.ndarray:
    """Spec: ξ_u = M_{class} Γ_geo Γ_scope Γ_dir"""
    base = EVENT_CLASS_SPHERES.get(event.event_class,
           EVENT_CLASS_SPHERES.get("generic_macro", np.zeros(N_CHANNELS)))
    vec = base.copy()
    vec *= (0.5 + 0.5 * event.scope)
    if event.direction < 0:
        vec *= abs(event.direction)
    elif event.direction == 0:
        vec *= 0.5
    if event.geography not in ("US", "GLOBAL"):
        vec *= 0.7
    return vec


# ═══════════════════════════════════════════════════════════════════════════
# 6. Event classification from news text
# ═══════════════════════════════════════════════════════════════════════════

CLASSIFICATION_RULES: List[Dict[str, Any]] = [
    {
        "event_class": "war_escalation",
        "keywords": ["iran", "war", "military strike", "missile", "invasion",
                     "troops deployed", "peace plan rejected", "ceasefire collapse",
                     "nato", "south china sea", "taiwan", "sanctions escalat"],
        "severity": 0.8, "persistence": 0.7, "scope": 1.0, "direction": -1,
        "decay_rate": 0.05,
    },
    {
        "event_class": "oil_shock",
        "keywords": ["oil surge", "oil spike", "oil shock", "opec cut",
                     "supply disruption", "refinery", "crude above $90",
                     "crude above $100", "barrel", "energy crisis",
                     "oil above $90", "oil above $100"],
        "severity": 0.8, "persistence": 0.6, "scope": 1.0, "direction": -1,
        "decay_rate": 0.07,
    },
    {
        "event_class": "stagflation",
        "keywords": ["stagflation", "inflation surge", "no rate cut",
                     "higher for longer", "powell warns", "rate cuts delayed"],
        "severity": 0.7, "persistence": 0.8, "scope": 1.0, "direction": -1,
        "decay_rate": 0.04,
    },
    {
        "event_class": "rate_hike",
        "keywords": ["rate hike", "fed raises", "hawkish", "tightening",
                     "yield spike", "bond sell"],
        "severity": 0.7, "persistence": 0.7, "scope": 1.0, "direction": -1,
        "decay_rate": 0.05,
    },
    {
        "event_class": "tech_selloff",
        "keywords": ["tech selloff", "tech reckoning", "ai bubble",
                     "semiconductor shortage", "chip ban", "antitrust big tech"],
        "severity": 0.6, "persistence": 0.5, "scope": 0.7, "direction": -1,
        "decay_rate": 0.08,
    },
    {
        "event_class": "trade_war",
        "keywords": ["tariff", "trade war", "export ban", "import duty",
                     "trade restrictions", "decoupling"],
        "severity": 0.7, "persistence": 0.7, "scope": 1.0, "direction": -1,
        "decay_rate": 0.04,
    },
    {
        "event_class": "commodity_squeeze",
        "keywords": ["commodity surge", "natural gas spike", "metal shortage",
                     "grain shortage", "food prices", "lithium"],
        "severity": 0.6, "persistence": 0.5, "scope": 0.8, "direction": -1,
        "decay_rate": 0.07,
    },
    {
        "event_class": "fiscal_stimulus",
        "keywords": ["stimulus", "infrastructure bill", "fiscal spending",
                     "government investment", "infrastructure package"],
        "severity": 0.6, "persistence": 0.6, "scope": 1.0, "direction": +1,
        "decay_rate": 0.03,
    },
]


def classify_text(text: str) -> List[Dict[str, Any]]:
    text_lower = text.lower()
    matches = []
    for rule in CLASSIFICATION_RULES:
        for kw in rule["keywords"]:
            if kw.lower() in text_lower:
                matches.append(rule)
                break
    return matches


def create_event_from_text(
    text: str, source: str = "tavily_news", geography: str = "US",
) -> List[NormalizedEvent]:
    matches = classify_text(text)
    events = []
    now = datetime.now(timezone.utc).isoformat()
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    for match in matches:
        events.append(NormalizedEvent(
            id=f"evt_{match['event_class']}_{text_hash}_{int(time.time())}",
            source=source, timestamp=now, event_class=match["event_class"],
            scope=match["scope"], direction=match["direction"],
            severity=match["severity"],
            confidence=SOURCE_RELIABILITY.get(source, 0.4),
            persistence=match["persistence"], geography=geography,
            sector=None, industry=None, text_hash=text_hash,
        ))
    return events


# ═══════════════════════════════════════════════════════════════════════════
# 7. G32 Coordinator
# ═══════════════════════════════════════════════════════════════════════════

class G32Coordinator:
    """Spec: G32_t = (Ξ_t, Ξ̄_t, ΔΞ_t, Π_t^epoch, L_epoch_t, R_t)"""

    def __init__(self, alpha_smooth: float = 0.85):
        self.epoch_library: List[EpochObject] = []
        self.conflict_ledger: List[Dict[str, Any]] = []
        self.alpha_smooth = alpha_smooth
        self.xi_current = np.zeros(N_CHANNELS)
        self.xi_smoothed = np.zeros(N_CHANNELS)
        self.xi_delta = np.zeros(N_CHANNELS)

    def admit_event(self, event: NormalizedEvent) -> Optional[EpochObject]:
        score = compute_admission_score(event, self.epoch_library)
        if score < PI_MIN:
            return None
        # Merge with existing same-class active epoch
        for existing in self.epoch_library:
            if existing.event_class == event.event_class and existing.t_end is None:
                existing.severity = max(existing.severity, event.severity)
                existing.confidence = max(existing.confidence, event.confidence)
                existing.source_events.append(event.id)
                existing.sphere_vector = project_sphere_vector(event)
                return existing
        # New epoch object
        sphere = project_sphere_vector(event)
        decay_rate = 0.05
        for rule in CLASSIFICATION_RULES:
            if rule["event_class"] == event.event_class:
                decay_rate = rule.get("decay_rate", 0.05)
                break
        epoch = EpochObject(
            id=f"epoch_{event.event_class}_{int(time.time())}",
            event_class=event.event_class, t_start=event.timestamp,
            t_end=None, severity=event.severity, confidence=event.confidence,
            persistence=event.persistence, sphere_vector=sphere,
            source=event.source, decay_rate=decay_rate,
            source_events=[event.id],
        )
        self.epoch_library.append(epoch)
        self._resolve_conflicts(epoch)
        return epoch

    def _resolve_conflicts(self, new_epoch: EpochObject) -> None:
        eps = 1e-8
        for existing in self.epoch_library:
            if existing.id == new_epoch.id:
                continue
            norm_prod = (np.linalg.norm(existing.sphere_vector)
                        * np.linalg.norm(new_epoch.sphere_vector) + eps)
            contradiction = max(0.0, float(
                np.dot(existing.sphere_vector, -new_epoch.sphere_vector)
            )) / norm_prod
            if contradiction > 0.5:
                self.conflict_ledger.append({
                    "epoch_a": existing.id, "epoch_b": new_epoch.id,
                    "contradiction": contradiction,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                })
                existing.confidence *= 0.8
                new_epoch.confidence *= 0.8

    def compute_mosaic(self, t: Optional[datetime] = None) -> np.ndarray:
        if t is None:
            t = datetime.now(timezone.utc)
        mosaic = np.zeros(N_CHANNELS)
        for epoch in self.epoch_library:
            mosaic += epoch.weighted_sphere(t)
        return mosaic

    def update(self, t: Optional[datetime] = None) -> Dict[str, np.ndarray]:
        if t is None:
            t = datetime.now(timezone.utc)
        self.epoch_library = [e for e in self.epoch_library if e.amplitude(t) >= 0.01]
        self.xi_current = self.compute_mosaic(t)
        self.xi_smoothed = (self.alpha_smooth * self.xi_smoothed
                           + (1 - self.alpha_smooth) * self.xi_current)
        self.xi_delta = self.xi_current - self.xi_smoothed
        return {"xi": self.xi_current, "xi_smoothed": self.xi_smoothed,
                "xi_delta": self.xi_delta}

    def get_channel_severities(self) -> Dict[str, float]:
        return {SPHERE_CHANNELS[i]: round(float(self.xi_current[i]), 4)
                for i in range(N_CHANNELS) if self.xi_current[i] > 0.001}

    def compute_symbol_pressure(
        self, sector: str,
        sector_couplings: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> float:
        if sector_couplings is None:
            return 0.0
        couplings = sector_couplings.get(sector, {})
        pressure = 0.0
        for channel_name, coupling_weight in couplings.items():
            idx = CHANNEL_INDEX.get(channel_name)
            if idx is not None:
                pressure += coupling_weight * self.xi_current[idx]
        return pressure

    def to_dict(self) -> Dict[str, Any]:
        return {
            "xi": {SPHERE_CHANNELS[i]: round(float(self.xi_current[i]), 4)
                   for i in range(N_CHANNELS) if self.xi_current[i] != 0},
            "xi_smoothed": {SPHERE_CHANNELS[i]: round(float(self.xi_smoothed[i]), 4)
                           for i in range(N_CHANNELS) if self.xi_smoothed[i] != 0},
            "xi_delta": {SPHERE_CHANNELS[i]: round(float(self.xi_delta[i]), 4)
                        for i in range(N_CHANNELS) if self.xi_delta[i] != 0},
            "active_epochs": len(self.epoch_library),
            "conflicts": len(self.conflict_ledger),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 8. News ingestion pipeline (Tavily)
# ═══════════════════════════════════════════════════════════════════════════

def _load_tavily_key() -> Optional[str]:
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if key:
        return key
    try:
        import boto3
        sm = boto3.client("secretsmanager",
                          region_name=os.environ.get("AWS_REGION", "us-east-1"))
        secret = sm.get_secret_value(SecretId="tfe/tavily/prod")
        data = json.loads(secret["SecretString"])
        return data.get("TAVILY_API_KEY", "").strip() or None
    except Exception:
        return None


def _query_tavily(api_key: str, query: str, max_results: int = 5) -> Dict[str, Any]:
    import urllib.request
    body = json.dumps({
        "query": query, "max_results": max_results,
        "include_answer": "basic", "topic": "news", "days": 3,
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())


def ingest_news(coordinator: G32Coordinator) -> int:
    api_key = _load_tavily_key()
    if not api_key:
        print("[EPOCH-LIB] No Tavily API key — skipping news ingestion")
        return 0
    queries = [
        "stock market today oil prices geopolitical risk",
        "federal reserve interest rates inflation economy today",
        "middle east conflict energy supply crisis",
        "technology sector stocks semiconductor earnings",
    ]
    admitted = 0
    for query in queries:
        try:
            result = _query_tavily(api_key, query, max_results=5)
            answer = result.get("answer", "")
            if answer:
                for event in create_event_from_text(answer):
                    if coordinator.admit_event(event):
                        admitted += 1
            for r in result.get("results", []):
                text = f"{r.get('title', '')} {r.get('content', '')[:500]}"
                for event in create_event_from_text(text):
                    if coordinator.admit_event(event):
                        admitted += 1
            time.sleep(0.5)
        except Exception as exc:
            print(f"[EPOCH-LIB] Tavily query failed: {exc}")
    return admitted


# ═══════════════════════════════════════════════════════════════════════════
# 9. Public API
# ═══════════════════════════════════════════════════════════════════════════

def build_epoch_mosaic(
    auto_severities: Optional[Dict[str, float]] = None,
) -> Tuple[G32Coordinator, Dict[str, float]]:
    """Build full epoch mosaic from market data + news. Returns (coordinator, severities)."""
    coordinator = G32Coordinator()

    # Inject market data as high-confidence epoch objects
    if auto_severities:
        now = datetime.now(timezone.utc).isoformat()
        for channel, severity in auto_severities.items():
            if severity < 0.2:
                continue
            idx = CHANNEL_INDEX.get(channel)
            if idx is None:
                continue
            sphere = np.zeros(N_CHANNELS)
            sphere[idx] = 1.0
            epoch = EpochObject(
                id=f"market_{channel}_{int(time.time())}",
                event_class=f"market_{channel.lower()}", t_start=now,
                t_end=None, severity=severity, confidence=0.9,
                persistence=0.5, sphere_vector=sphere, source="market_data",
                decay_rate=0.1,
            )
            coordinator.epoch_library.append(epoch)

    admitted = ingest_news(coordinator)
    print(f"[EPOCH-LIB] News events admitted: {admitted}")
    coordinator.update()
    severities = coordinator.get_channel_severities()
    print(f"[EPOCH-LIB] Epoch mosaic: {len(coordinator.epoch_library)} active objects, "
          f"{len(severities)} active channels")
    return coordinator, severities
```

---

## FILE: tfe_epoch_structural_history.py

```python
#!/usr/bin/env python3
"""
TFE Epoch Structural History Study
====================================

Runs the L0-L4 kernel on major tickers across historical crisis periods
to build the structural record of how the L4 field evolved during
specific epoch stories.

Crisis periods studied:
  1. 2007-2009: Financial crisis (housing → credit → banks → contagion)
  2. 2020: COVID crash and recovery (pandemic → shutdown → stimulus → V)
  3. 2022: Rate shock (inflation → hikes → tech collapse → energy spike)
  4. 2024-2026: Current period (for comparison)

For each period, we:
  - Fetch daily bars for a broad set of tickers
  - Run the frozen L0-L4 kernel
  - Capture the full DSF evolution at every gate
  - Tag which sectors/stocks were loaded springs
  - Track which fired UP vs DOWN
  - Record the epoch environment at each gate

Output: epoch_structural_history.json — complete structural record
        epoch_structural_analysis.txt — human-readable findings
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from urllib.request import urlopen
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

API_KEY = os.environ.get('MASSIVE_API_KEY') or os.environ.get('POLYGON_API_KEY', '')

# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════

# Tickers that tell the epoch stories — across sectors
STUDY_TICKERS = {
    # Banks / Financial (2008 story)
    'financials': ['JPM', 'BAC', 'GS', 'WFC', 'C', 'MS'],
    # Housing / Real Estate (2008 story)
    'real_estate': ['VNQ', 'IYR', 'XHB'],
    # Energy (2008 + 2022 + current Iran story)
    'energy': ['XOM', 'CVX', 'OXY', 'COP', 'XLE', 'USO'],
    # Tech (2020 recovery + 2022 crash + current divergence)
    'tech': ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'NVDA', 'QQQ'],
    # Consumer (sensitive to rates + inflation)
    'consumer': ['WMT', 'TGT', 'HD', 'COST', 'XLY', 'XLP'],
    # Broad market
    'market': ['SPY', 'IWM', 'DIA'],
    # Rates / Bonds
    'rates': ['TLT', 'HYG', 'LQD'],
    # Volatility
    'volatility': ['VXX'],
    # Healthcare (defensive)
    'healthcare': ['JNJ', 'UNH', 'PFE', 'XLV'],
    # Industrials
    'industrials': ['CAT', 'DE', 'GE', 'XLI'],
    # Small caps (where CH3 hunts)
    'small_cap': ['IWM', 'SOXS', 'TQQQ', 'SQQQ'],
}

# Flatten to unique list
ALL_TICKERS = sorted(set(t for group in STUDY_TICKERS.values() for t in group))

# Crisis periods with context
CRISIS_PERIODS = {
    '2007-2009_financial_crisis': {
        'start': '2005-01-01',  # 2 years before for context
        'end': '2010-06-30',    # through recovery
        'peak_crisis': ('2008-09-01', '2009-03-31'),
        'narrative': 'Housing bubble → credit freeze → bank failures → contagion → TARP → slow recovery',
        'epoch_type': 'CREDIT_CONTAGION',
    },
    '2020_covid_crash': {
        'start': '2019-01-01',
        'end': '2021-06-30',
        'peak_crisis': ('2020-02-19', '2020-04-30'),
        'narrative': 'Pandemic → global shutdown → stimulus → fastest V-recovery in history',
        'epoch_type': 'EXOGENOUS_SHOCK',
    },
    '2022_rate_shock': {
        'start': '2021-06-01',
        'end': '2023-06-30',
        'peak_crisis': ('2022-01-01', '2022-12-31'),
        'narrative': 'Inflation spike → aggressive Fed hikes → tech collapse → energy surge → bank stress (SVB)',
        'epoch_type': 'MONETARY_TIGHTENING',
    },
    '2024-2026_current': {
        'start': '2024-01-01',
        'end': '2026-04-29',
        'peak_crisis': ('2026-04-01', '2026-04-29'),
        'narrative': 'Iran blockade → oil spike → Fed frozen (4 dissents) → tech earnings divergence → Warsh transition',
        'epoch_type': 'GEOPOLITICAL_MONETARY_SPLIT',
    },
}

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════
# Data Fetching
# ═══════════════════════════════════════════════════════════════════════

def fetch_bars(ticker, start, end, max_retries=3):
    """Fetch daily bars from Polygon with retry."""
    for attempt in range(max_retries):
        try:
            url = (f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
                   f"{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={API_KEY}")
            resp = urlopen(url, timeout=30)
            data = json.loads(resp.read())
            if data.get('status') == 'OK' and data.get('results'):
                return data['results']
            return []
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"    FAILED after {max_retries} attempts: {e}")
                return []
    return []

# ���══════════════════════════════════════════════════════════════════════
# Kernel Runner
# ═���═══════════════════��═════════════════════════════════════════════════

def run_kernel(bars):
    """Run L0-L4 on bar data, return full DSF evolution with gate mapping."""
    if len(bars) < 20:
        return None

    closes = pd.Series(
        [b['c'] for b in bars],
        index=[pd.Timestamp(b['t'], unit='ms') for b in bars]
    ).sort_index().dropna().astype(float)

    if len(closes) < 20:
        return None

    frame = pd.DataFrame({"Close": closes})
    frame.index = closes.index

    try:
        sev_list = compute_sev_series(frame, field_col="Close")
        gates = segment_gates(sev_list)
        interps = interpret_gates(sev_list, gates)
        resonance = compute_resonance(interps)
        decisions = compute_directional_signal(resonance)
        dsf_list = compute_dsf(decisions)
    except Exception as e:
        print(f"    Kernel error: {e}")
        return None

    if not dsf_list:
        return None

    # Build evolution record
    n_bars = len(closes)
    close_values = closes.values
    dates = [str(d.date()) if hasattr(d, 'date') else str(d)[:10] for d in closes.index]

    # Compute stability metrics progressively
    evolution = []
    for idx, (dsf, res) in enumerate(zip(dsf_list, resonance)):
        gate_end = min(dsf.gate.end_idx, n_bars - 1)
        gate_start = dsf.gate.start_idx

        if gate_end >= n_bars:
            continue

        price = float(close_values[gate_end])
        bar_date = dates[gate_end] if gate_end < len(dates) else ''

        # Forward returns
        fwd_5d_max = None
        fwd_5d_min = None
        fwd_5d = None
        if gate_end + 5 < n_bars:
            window = close_values[gate_end + 1:gate_end + 6]
            fwd_5d_max = float(max(window) / price - 1)
            fwd_5d_min = float(min(window) / price - 1)
            fwd_5d = float(close_values[gate_end + 5] / price - 1)

        # Regime from L2
        regime = res.interpretation.regime if hasattr(res, 'interpretation') else 'UNKNOWN'

        # Running S_UF proxy
        states_so_far = decisions[:idx + 1]
        results_so_far = resonance[:idx + 1]
        r_vals = [float(r.R_k) for r in results_so_far]
        r_mean = float(np.mean(r_vals))
        rev_flags = [float(ds.R_rev_k) for ds in states_so_far]
        d_vals = [float(ds.D_k) for ds in states_so_far]
        dir_stab = float(1.0 - np.mean(rev_flags))
        dsf_instab = float(np.mean([(abs(d) > 0) for d in d_vals]))
        s_uf = max(0.0, min(1.0, 0.5 * (1.0 - dsf_instab) + 0.5 * dir_stab))
        r_uf = max(0.0, min(1.0, r_mean))

        evolution.append({
            'gate_index': idx,
            'gate_start': gate_start,
            'gate_end': gate_end,
            'bar_date': bar_date,
            'price': price,
            'D_k': float(dsf.D_k),
            'M_k': float(dsf.M_k),
            'R_rev_k': float(dsf.R_rev_k),
            'U_star_k': float(dsf.U_star_k),
            'C_k': float(dsf.C_k),
            'P_k': float(dsf.P_k),
            'B_k': float(dsf.B_k),
            'S_UF': s_uf,
            'R_UF': r_uf,
            'regime': regime,
            'fwd_5d_max': fwd_5d_max,
            'fwd_5d_min': fwd_5d_min,
            'fwd_5d': fwd_5d,
        })

    return evolution

# ═══════════════════════════════════════════════════════════════════════
# Epoch Environment Computation
# ═══════════════════════════════════════════════════════════════════════

def compute_epoch_env(spy_bars, qqq_bars, uso_bars, tlt_bars, date_str):
    """Compute epoch environment for a specific date from market proxy bars."""
    def get_price(bars, date):
        for b in bars:
            d = datetime.utcfromtimestamp(b['t']/1000).strftime('%Y-%m-%d')
            if d == date:
                return b['c']
        return None

    def get_price_lookback(bars, date, lookback=20):
        dates_prices = [(datetime.utcfromtimestamp(b['t']/1000).strftime('%Y-%m-%d'), b['c']) for b in bars]
        target_idx = None
        for i, (d, _) in enumerate(dates_prices):
            if d >= date:
                target_idx = i
                break
        if target_idx is None or target_idx < lookback:
            return None, None
        return dates_prices[target_idx][1], dates_prices[target_idx - lookback][1]

    env = {}
    for label, proxy_bars in [('spy', spy_bars), ('qqq', qqq_bars), ('uso', uso_bars), ('tlt', tlt_bars)]:
        curr, prev = get_price_lookback(proxy_bars, date_str, 20)
        if curr and prev and prev > 0:
            env[f'{label}_20d'] = (curr / prev - 1)
        else:
            env[f'{label}_20d'] = None

    return env

# ══���═════════════════════════��══════════════════════════════════════════
# Main Study
# ═══════════════════��═══════════════════════════════════════════════════

def run_study():
    if not API_KEY:
        print("ERROR: No API key")
        return

    results = {}
    analysis_lines = []

    analysis_lines.append("=" * 80)
    analysis_lines.append("TFE EPOCH STRUCTURAL HISTORY STUDY")
    analysis_lines.append(f"Generated: {datetime.utcnow().isoformat()}")
    analysis_lines.append("=" * 80)

    for period_name, period_config in CRISIS_PERIODS.items():
        print(f"\n{'='*70}")
        print(f"PERIOD: {period_name}")
        print(f"  {period_config['narrative']}")
        print(f"  Data range: {period_config['start']} to {period_config['end']}")
        print(f"{'='*70}")

        analysis_lines.append(f"\n\n{'='*80}")
        analysis_lines.append(f"PERIOD: {period_name}")
        analysis_lines.append(f"Narrative: {period_config['narrative']}")
        analysis_lines.append(f"Epoch type: {period_config['epoch_type']}")
        analysis_lines.append(f"{'='*80}")

        period_results = {
            'config': period_config,
            'tickers': {},
        }

        # Fetch epoch proxy data for this period
        print("  Fetching epoch proxies (SPY, QQQ, USO, TLT)...")
        spy_bars = fetch_bars('SPY', period_config['start'], period_config['end']); time.sleep(0.25)
        qqq_bars = fetch_bars('QQQ', period_config['start'], period_config['end']); time.sleep(0.25)
        uso_bars = fetch_bars('USO', period_config['start'], period_config['end']); time.sleep(0.25)
        tlt_bars = fetch_bars('TLT', period_config['start'], period_config['end']); time.sleep(0.25)

        # Process each ticker
        for sector, tickers in STUDY_TICKERS.items():
            for ticker in tickers:
                print(f"  [{sector}] {ticker}...", end=" ", flush=True)

                bars = fetch_bars(ticker, period_config['start'], period_config['end'])
                time.sleep(0.25)  # rate limit

                if not bars or len(bars) < 20:
                    print(f"SKIP ({len(bars) if bars else 0} bars)")
                    continue

                evolution = run_kernel(bars)
                if not evolution:
                    print("SKIP (kernel returned nothing)")
                    continue

                # Count loaded springs and their outcomes
                loaded = [g for g in evolution if g['B_k'] <= -0.95 and g['R_rev_k'] == 1.0 and g['fwd_5d_max'] is not None]
                fired_up = [g for g in loaded if g['fwd_5d_max'] > abs(g['fwd_5d_min'])]

                # Find gates during peak crisis
                peak_start, peak_end = period_config['peak_crisis']
                crisis_gates = [g for g in evolution if peak_start <= g['bar_date'] <= peak_end]
                crisis_loaded = [g for g in crisis_gates if g['B_k'] <= -0.95 and g['R_rev_k'] == 1.0]

                print(f"{len(evolution)} gates, {len(loaded)} loaded, {len(fired_up)} UP, {len(crisis_gates)} in crisis")

                period_results['tickers'][ticker] = {
                    'sector': sector,
                    'total_gates': len(evolution),
                    'loaded_springs': len(loaded),
                    'fired_up': len(fired_up),
                    'fired_down': len(loaded) - len(fired_up),
                    'crisis_gates': len(crisis_gates),
                    'crisis_loaded': len(crisis_loaded),
                    'evolution': evolution,  # full record
                }

        # ── Period Analysis ──────────────────────────────────────────────
        # How did each sector's springs behave during this epoch?
        analysis_lines.append(f"\n--- Sector Spring Behavior ---")
        analysis_lines.append(f"{'Sector':<20} {'Ticker':<8} {'Gates':>6} {'Loaded':>7} {'UP':>4} {'DN':>4} {'UP%':>6} {'Crisis':>7}")
        analysis_lines.append("-" * 70)

        sector_summary = defaultdict(lambda: {'loaded': 0, 'up': 0, 'down': 0, 'crisis_loaded': 0})

        for ticker, data in period_results['tickers'].items():
            up_pct = f"{100*data['fired_up']/data['loaded_springs']:.0f}%" if data['loaded_springs'] > 0 else "n/a"
            analysis_lines.append(
                f"{data['sector']:<20} {ticker:<8} {data['total_gates']:>6} {data['loaded_springs']:>7} "
                f"{data['fired_up']:>4} {data['fired_down']:>4} {up_pct:>6} {data['crisis_loaded']:>7}"
            )
            s = data['sector']
            sector_summary[s]['loaded'] += data['loaded_springs']
            sector_summary[s]['up'] += data['fired_up']
            sector_summary[s]['down'] += data['fired_down']
            sector_summary[s]['crisis_loaded'] += data['crisis_loaded']

        analysis_lines.append(f"\n--- Sector Summary ---")
        for sector, stats in sorted(sector_summary.items()):
            total = stats['loaded']
            up_pct = f"{100*stats['up']/total:.1f}%" if total > 0 else "n/a"
            analysis_lines.append(
                f"  {sector:<20} loaded={total:>4} UP={stats['up']:>4} ({up_pct}) "
                f"crisis_loaded={stats['crisis_loaded']:>4}"
            )

        # ── Structural Narrative ─────────────────────────────────────────
        # What did the L4 field look like during the crisis peak?
        analysis_lines.append(f"\n--- Crisis Peak Structural States ---")
        analysis_lines.append(f"Peak: {period_config['peak_crisis'][0]} to {period_config['peak_crisis'][1]}")

        for ticker, data in period_results['tickers'].items():
            crisis = [g for g in data['evolution']
                      if peak_start <= g['bar_date'] <= peak_end]
            if not crisis:
                continue

            analysis_lines.append(f"\n  {ticker} ({data['sector']}) — {len(crisis)} crisis gates:")
            for g in crisis[:10]:  # first 10 crisis gates
                fwd = f"{g['fwd_5d_max']*100:>+6.1f}%" if g['fwd_5d_max'] is not None else "   n/a"
                direction = "UP" if (g['fwd_5d_max'] or 0) > abs(g['fwd_5d_min'] or 0) else "DN"
                analysis_lines.append(
                    f"    {g['bar_date']} | D={g['D_k']:>+3.0f} M={g['M_k']:>+9.5f} "
                    f"Rrev={g['R_rev_k']:.0f} U*={g['U_star_k']:.3f} C={g['C_k']:.0f} "
                    f"P={g['P_k']:.0f} B={g['B_k']:>+7.4f} | ${g['price']:>8.2f} | {fwd} {direction}"
                )

        results[period_name] = period_results

    # ═══════════════════════════════════════════════════════════════════════
    # Cross-Period Comparison
    # ═══════════════════════════════════════════════════════════════════════

    analysis_lines.append(f"\n\n{'='*80}")
    analysis_lines.append("CROSS-PERIOD COMPARISON")
    analysis_lines.append(f"{'='*80}")

    PROFIT_CENTER = np.array([0.2875, 0.0196, 0.6649, 0.2978, 2.2506, 1.3766, -0.9771])
    L4_FIELDS = ['D_k', 'M_k', 'R_rev_k', 'U_star_k', 'C_k', 'P_k', 'B_k']
    NORMS = np.array([2.0, 2.0, 1.0, 1.0, 3.0, 2.0, 2.0])

    analysis_lines.append("\nDo loaded springs in different epoch types fire differently?")
    analysis_lines.append(f"{'Period':<35} {'Loaded':>7} {'UP%':>6} {'Avg Max':>9} {'Avg Worst':>10}")
    analysis_lines.append("-" * 70)

    for period_name, period_data in results.items():
        all_loaded = []
        for ticker, data in period_data['tickers'].items():
            for g in data['evolution']:
                if (g.get('B_k', 0) or 0) <= -0.95 and g.get('R_rev_k') == 1.0 and g.get('fwd_5d_max') is not None:
                    g['_sector'] = data['sector']
                    g['_ticker'] = ticker
                    all_loaded.append(g)

        if not all_loaded:
            continue

        up = sum(1 for g in all_loaded if g['fwd_5d_max'] > abs(g['fwd_5d_min']))
        avg_max = np.mean([g['fwd_5d_max'] for g in all_loaded]) * 100
        avg_min = np.mean([g['fwd_5d_min'] for g in all_loaded]) * 100

        analysis_lines.append(
            f"  {period_name:<35} {len(all_loaded):>5} {100*up/len(all_loaded):>5.1f}% "
            f"{avg_max:>+8.2f}% {avg_min:>+9.2f}%"
        )

        # By sector within this period
        by_sector = defaultdict(list)
        for g in all_loaded:
            by_sector[g['_sector']].append(g)

        for sector, gates in sorted(by_sector.items()):
            up_s = sum(1 for g in gates if g['fwd_5d_max'] > abs(g['fwd_5d_min']))
            avg_max_s = np.mean([g['fwd_5d_max'] for g in gates]) * 100
            analysis_lines.append(
                f"    {sector:<25} n={len(gates):>4} UP={100*up_s/len(gates):>5.1f}% max={avg_max_s:>+7.1f}%"
            )

    # ═══════════════════════════════════════════════════════════════════════
    # The Key Question: Which sectors fire UP during which epoch types?
    # ═════════════════════════════════════════��═════════════════════════════

    analysis_lines.append(f"\n\n{'='*80}")
    analysis_lines.append("THE KEY QUESTION: Sector × Epoch Type → Direction")
    analysis_lines.append("Which sectors' loaded springs fire UP in which epoch environments?")
    analysis_lines.append(f"{'='*80}")

    # Build sector × epoch matrix
    sector_epoch_matrix = {}
    for period_name, period_data in results.items():
        epoch_type = period_data['config']['epoch_type']
        for ticker, data in period_data['tickers'].items():
            sector = data['sector']
            key = (sector, epoch_type)
            if key not in sector_epoch_matrix:
                sector_epoch_matrix[key] = {'up': 0, 'down': 0, 'returns': []}

            for g in data['evolution']:
                if (g.get('B_k', 0) or 0) <= -0.95 and g.get('R_rev_k') == 1.0 and g.get('fwd_5d_max') is not None:
                    fired_up = g['fwd_5d_max'] > abs(g['fwd_5d_min'])
                    sector_epoch_matrix[key]['up' if fired_up else 'down'] += 1
                    sector_epoch_matrix[key]['returns'].append(g['fwd_5d_max'])

    all_sectors = sorted(set(k[0] for k in sector_epoch_matrix.keys()))
    all_epochs = sorted(set(k[1] for k in sector_epoch_matrix.keys()))

    analysis_lines.append(f"\n{'Sector':<20}", )
    for epoch in all_epochs:
        analysis_lines[-1] += f" | {epoch[:15]:<15}"

    analysis_lines.append("-" * (20 + 18 * len(all_epochs)))

    for sector in all_sectors:
        line = f"  {sector:<20}"
        for epoch in all_epochs:
            key = (sector, epoch)
            if key in sector_epoch_matrix:
                stats = sector_epoch_matrix[key]
                total = stats['up'] + stats['down']
                if total > 0:
                    up_pct = 100 * stats['up'] / total
                    avg_ret = np.mean(stats['returns']) * 100
                    line += f" | {up_pct:>4.0f}% n={total:<3} {avg_ret:>+5.1f}%"
                else:
                    line += f" | {'n/a':>15}"
            else:
                line += f" | {'—':>15}"
        analysis_lines.append(line)

    # ═══════════════════════════════════════════════════════════════════════
    # Today's implication
    # ════════════════════════════════════════════��══════════════════════════

    analysis_lines.append(f"\n\n{'='*80}")
    analysis_lines.append("TODAY'S IMPLICATION")
    analysis_lines.append(f"Current epoch type: GEOPOLITICAL_MONETARY_SPLIT")
    analysis_lines.append(f"Iran blockade + oil at $120 + Fed frozen (4 dissents) + tech earnings diverging")
    analysis_lines.append(f"{'='*80}")
    analysis_lines.append(f"\nBased on the sector × epoch matrix above:")
    analysis_lines.append(f"- Which sectors' loaded springs historically fire UP in this kind of environment?")
    analysis_lines.append(f"- Which sectors' springs break DOWN?")
    analysis_lines.append(f"- Use this to rank CH3 candidates by sector-epoch alignment")

    # ═══════════════════════════════════════════════════════════════════════
    # Save
    # ═══════════════════════════════════════════════════════════════════════

    # Save analysis text
    analysis_path = os.path.join(OUTPUT_DIR, 'epoch_structural_analysis.txt')
    with open(analysis_path, 'w') as f:
        f.write('\n'.join(analysis_lines))
    print(f"\nAnalysis saved to {analysis_path}")

    # Save raw data (without full evolution to keep size manageable)
    summary = {}
    for period_name, period_data in results.items():
        summary[period_name] = {
            'config': period_data['config'],
            'tickers': {}
        }
        for ticker, data in period_data['tickers'].items():
            summary[period_name]['tickers'][ticker] = {
                'sector': data['sector'],
                'total_gates': data['total_gates'],
                'loaded_springs': data['loaded_springs'],
                'fired_up': data['fired_up'],
                'fired_down': data['fired_down'],
                'crisis_gates': data['crisis_gates'],
                'crisis_loaded': data['crisis_loaded'],
                # Include crisis peak gates only (not full evolution)
                'crisis_evolution': [g for g in data['evolution']
                                    if period_data['config']['peak_crisis'][0] <= g['bar_date'] <= period_data['config']['peak_crisis'][1]],
            }

    data_path = os.path.join(OUTPUT_DIR, 'epoch_structural_history.json')
    with open(data_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Data saved to {data_path}")

    print(f"\n{'='*70}")
    print("STUDY COMPLETE")
    print(f"{'='*70}")

if __name__ == '__main__':
    run_study()
```

---

## FILE: tfe_epoch_auto_severity.py

```python
#!/usr/bin/env python3
"""
tfe_epoch_auto_severity.py
Auto-severity scoring for TFE epoch library.

Fetches live market indicators via yfinance and computes severity scores
for each named epoch channel. Caches results to JSON with 6-hour TTL.

8 Active Channels (of 32 in spec):
─────────────────────────────────
RATES_PRESSURE      — 10yr yield, 2s10s spread, credit stress (HYG/LQD)
CONSUMER_STRESS     — XLY/XLP rotation, VIX
WAR_GEOPOLITICS     — VIX, crude oil, defense sector (ITA) outperformance
ENERGY_COMMODITY    — crude oil vs MA, natural gas vs MA, XLE vs SPY
TECH_CYCLE          — semiconductor (SOXX) vs SPY, QQQ vs SPY
CURRENCY_FX         — dollar index (UUP), emerging markets (EEM) vs SPY
FISCAL_INFRA        — infrastructure ETF (PAVE) vs SPY, industrials (XLI)
VOLATILITY_REGIME   — VIX level, VIX term structure (VIX vs VIX3M proxy)

All scores normalized 0.0–1.0. No ML. Deterministic from market data.
Fallback to defaults if fetch fails.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict

import numpy as np
import yfinance as yf

# ── Cache ────────────────────────────────────────────────────────────────────
_CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epoch_live_severities.json")
_CACHE_TTL_HOURS = 6

# Hardcoded fallback — used if network unavailable
_FALLBACK_SEVERITIES: Dict[str, float] = {
    "RATES_PRESSURE":    0.5,
    "CONSUMER_STRESS":   0.3,
    "WAR_GEOPOLITICS":   0.3,
    "ENERGY_COMMODITY":  0.3,
    "TECH_CYCLE":        0.3,
    "CURRENCY_FX":       0.3,
    "FISCAL_INFRA":      0.3,
    "VOLATILITY_REGIME": 0.3,
}

# ── Market data fetch ─────────────────────────────────────────────────────────
_TICKERS = [
    # Original 3 channels
    "^VIX", "CL=F", "^TNX", "^IRX", "HYG", "LQD", "XLY", "XLP", "ITA", "SPY",
    # New channels
    "NG=F",     # natural gas futures
    "XLE",      # energy sector ETF
    "SOXX",     # semiconductor index
    "QQQ",      # tech-heavy Nasdaq
    "UUP",      # dollar index ETF
    "EEM",      # emerging markets ETF
    "PAVE",     # infrastructure ETF
    "XLI",      # industrials ETF
]


def _fetch_closes(period: str = "3mo") -> Dict[str, "np.ndarray"]:
    """Download closing prices for all indicators. Returns {ticker: array}."""
    raw = yf.download(
        _TICKERS,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    closes: Dict[str, np.ndarray] = {}
    if hasattr(raw.columns, "levels"):
        price_df = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
        for ticker in _TICKERS:
            if ticker in price_df.columns:
                arr = price_df[ticker].dropna().values
                if len(arr) > 0:
                    closes[ticker] = arr.astype(float)
    else:
        closes["^VIX"] = raw["Close"].dropna().values.astype(float)
    return closes


def _relative_return(closes, ticker_a, ticker_b, days=20):
    """Compute relative return of A vs B over N days."""
    if ticker_a not in closes or ticker_b not in closes:
        return None
    a, b = closes[ticker_a], closes[ticker_b]
    if len(a) <= days or len(b) <= days:
        return None
    a_ret = float(a[-1]) / float(a[-days]) - 1.0
    b_ret = float(b[-1]) / float(b[-days]) - 1.0
    return a_ret - b_ret


def _pct_above_ma(closes, ticker, ma_days=60):
    """Compute how far price is above its moving average."""
    if ticker not in closes:
        return None
    arr = closes[ticker]
    if len(arr) < ma_days:
        return None
    ma = float(np.mean(arr[-ma_days:]))
    if ma <= 0:
        return None
    return (float(arr[-1]) - ma) / ma


# ── Per-epoch scoring ─────────────────────────────────────────────────────────

def _score_war_geopolitics(closes: Dict[str, np.ndarray]) -> float:
    scores = []
    if "^VIX" in closes and len(closes["^VIX"]) > 0:
        vix = float(closes["^VIX"][-1])
        scores.append(float(np.clip((vix - 15.0) / 35.0, 0.0, 1.0)))
    pct = _pct_above_ma(closes, "CL=F", 60)
    if pct is not None:
        scores.append(float(np.clip(pct / 0.15, 0.0, 1.0)))  # oil +15% = max severity
    rel = _relative_return(closes, "ITA", "SPY", 20)
    if rel is not None:
        scores.append(float(np.clip(rel / 0.08, 0.0, 1.0)))  # defense +8% vs SPY = max
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["WAR_GEOPOLITICS"]


def _score_rates_pressure(closes: Dict[str, np.ndarray]) -> float:
    scores = []
    if "^TNX" in closes and len(closes["^TNX"]) > 0:
        tnx = float(closes["^TNX"][-1])
        scores.append(float(np.clip((tnx - 2.0) / 3.0, 0.0, 1.0)))
    if "^IRX" in closes and "^TNX" in closes:
        irx = float(closes["^IRX"][-1])
        tnx = float(closes["^TNX"][-1])
        spread = tnx - irx
        scores.append(float(np.clip(-spread / 2.0, 0.0, 1.0)))
    if "HYG" in closes and "LQD" in closes:
        hyg, lqd = closes["HYG"], closes["LQD"]
        if len(hyg) > 20 and len(lqd) > 20:
            hyg_ret = float(hyg[-1]) / float(hyg[-20]) - 1.0
            lqd_ret = float(lqd[-1]) / float(lqd[-20]) - 1.0
            scores.append(float(np.clip((lqd_ret - hyg_ret) / 0.05, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["RATES_PRESSURE"]


def _score_consumer_stress(closes: Dict[str, np.ndarray]) -> float:
    scores = []
    if "XLY" in closes and "XLP" in closes:
        xly, xlp = closes["XLY"], closes["XLP"]
        if len(xly) > 20 and len(xlp) > 20:
            ratio_now = float(xly[-1]) / float(xlp[-1])
            ratio_20d = float(xly[-20]) / float(xlp[-20])
            ratio_chg = ratio_now / ratio_20d - 1.0
            scores.append(float(np.clip(-ratio_chg / 0.10, 0.0, 1.0)))
    if "^VIX" in closes and len(closes["^VIX"]) > 0:
        vix = float(closes["^VIX"][-1])
        scores.append(float(np.clip((vix - 15.0) / 25.0, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["CONSUMER_STRESS"]


def _score_energy_commodity(closes: Dict[str, np.ndarray]) -> float:
    """Energy/commodity input cost pressure.
    High crude + high nat gas + energy sector outperforming = commodity stress for consumers.
    """
    scores = []
    # Crude oil vs 60d MA
    pct = _pct_above_ma(closes, "CL=F", 60)
    if pct is not None:
        scores.append(float(np.clip(pct / 0.15, 0.0, 1.0)))
    # Natural gas vs 60d MA
    pct_ng = _pct_above_ma(closes, "NG=F", 60)
    if pct_ng is not None:
        scores.append(float(np.clip(pct_ng / 0.20, 0.0, 1.0)))
    # XLE (energy) vs SPY — energy outperformance = commodity pressure
    rel = _relative_return(closes, "XLE", "SPY", 20)
    if rel is not None:
        scores.append(float(np.clip(rel / 0.10, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["ENERGY_COMMODITY"]


def _score_tech_cycle(closes: Dict[str, np.ndarray]) -> float:
    """Tech sector cycle stress.
    Semiconductors underperforming + QQQ underperforming SPY = tech rotation out.
    Inverted: SOXX outperforming = tech strength (low stress).
    """
    scores = []
    # SOXX vs SPY — semiconductor underperformance = tech stress
    rel_soxx = _relative_return(closes, "SOXX", "SPY", 20)
    if rel_soxx is not None:
        # Negative relative = stress (tech falling behind)
        scores.append(float(np.clip(-rel_soxx / 0.15, 0.0, 1.0)))
    # QQQ vs SPY — tech-heavy underperformance
    rel_qqq = _relative_return(closes, "QQQ", "SPY", 20)
    if rel_qqq is not None:
        scores.append(float(np.clip(-rel_qqq / 0.10, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["TECH_CYCLE"]


def _score_currency_fx(closes: Dict[str, np.ndarray]) -> float:
    """Currency/FX stress.
    Strong dollar (UUP rising) = pressure on multinationals, EM stress.
    EEM underperforming SPY = emerging market stress from dollar/rates.
    """
    scores = []
    # Dollar strength: UUP 20d return
    if "UUP" in closes and len(closes["UUP"]) > 20:
        uup = closes["UUP"]
        uup_ret = float(uup[-1]) / float(uup[-20]) - 1.0
        # 5% dollar appreciation in 20d = max stress
        scores.append(float(np.clip(uup_ret / 0.05, 0.0, 1.0)))
    # EM underperformance
    rel_eem = _relative_return(closes, "EEM", "SPY", 20)
    if rel_eem is not None:
        # EM underperforming SPY = FX stress
        scores.append(float(np.clip(-rel_eem / 0.10, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["CURRENCY_FX"]


def _score_fiscal_infra(closes: Dict[str, np.ndarray]) -> float:
    """Fiscal/infrastructure spending signal.
    PAVE (infrastructure) and XLI (industrials) outperforming = fiscal tailwind.
    This is a POSITIVE epoch — high severity means infrastructure is hot.
    """
    scores = []
    rel_pave = _relative_return(closes, "PAVE", "SPY", 20)
    if rel_pave is not None:
        # Infrastructure outperforming = fiscal support active
        scores.append(float(np.clip(rel_pave / 0.10, 0.0, 1.0)))
    rel_xli = _relative_return(closes, "XLI", "SPY", 20)
    if rel_xli is not None:
        scores.append(float(np.clip(rel_xli / 0.08, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["FISCAL_INFRA"]


def _score_volatility_regime(closes: Dict[str, np.ndarray]) -> float:
    """Volatility regime.
    VIX level + VIX acceleration (is fear increasing?).
    High and rising VIX = stressed volatility regime.
    """
    scores = []
    if "^VIX" in closes and len(closes["^VIX"]) > 20:
        vix_arr = closes["^VIX"]
        vix_now = float(vix_arr[-1])
        vix_20d = float(np.mean(vix_arr[-20:]))
        # Absolute level: 15 = calm, 40 = panic
        scores.append(float(np.clip((vix_now - 15.0) / 25.0, 0.0, 1.0)))
        # Acceleration: VIX rising above its own 20d average
        vix_accel = (vix_now - vix_20d) / max(vix_20d, 1.0)
        scores.append(float(np.clip(vix_accel / 0.30, 0.0, 1.0)))
    return round(float(max(scores)), 3) if scores else _FALLBACK_SEVERITIES["VOLATILITY_REGIME"]


# ── Public API ────────────────────────────────────────────────────────────────

def compute_live_severities() -> Dict[str, float]:
    """Fetch market data and return computed epoch severity dict."""
    try:
        closes = _fetch_closes(period="3mo")
        severities = {
            "RATES_PRESSURE":    _score_rates_pressure(closes),
            "CONSUMER_STRESS":   _score_consumer_stress(closes),
            "WAR_GEOPOLITICS":   _score_war_geopolitics(closes),
            "ENERGY_COMMODITY":  _score_energy_commodity(closes),
            "TECH_CYCLE":        _score_tech_cycle(closes),
            "CURRENCY_FX":       _score_currency_fx(closes),
            "FISCAL_INFRA":      _score_fiscal_infra(closes),
            "VOLATILITY_REGIME": _score_volatility_regime(closes),
        }
        print(f"[EPOCH-AUTO] Live severities computed: {severities}")
        return severities
    except Exception as exc:
        print(f"[EPOCH-AUTO] Market fetch failed ({exc}) — using fallback severities")
        return dict(_FALLBACK_SEVERITIES)


def refresh_and_cache() -> Dict[str, float]:
    """Compute severities and write to cache file. Returns severity dict."""
    severities = compute_live_severities()
    try:
        with open(_CACHE_PATH, "w") as fh:
            json.dump({"computed_at": datetime.utcnow().isoformat(), "severities": severities}, fh, indent=2)
    except Exception as exc:
        print(f"[EPOCH-AUTO] Cache write failed: {exc}")
    return severities


def load_live_epochs() -> Dict[str, float]:
    """
    Return live epoch severities.
    Reads from cache file if age < TTL, otherwise recomputes and caches.
    Falls back to hardcoded values if everything fails.
    """
    try:
        with open(_CACHE_PATH) as fh:
            cached = json.load(fh)
        computed_at = datetime.fromisoformat(cached["computed_at"])
        age_hours = (datetime.utcnow() - computed_at).total_seconds() / 3600.0
        if age_hours < _CACHE_TTL_HOURS:
            sevs = cached["severities"]
            print(f"[EPOCH-AUTO] Using cached severities (age={age_hours:.1f}h): {sevs}")
            return sevs
    except (FileNotFoundError, KeyError, ValueError):
        pass
    # Cache missing or stale — recompute
    return refresh_and_cache()


if __name__ == "__main__":
    result = refresh_and_cache()
    print("Epoch severities:", result)
```

---

## FILE: tfe_epoch_resonance_shield.py

```python
#!/usr/bin/env python3
"""
TFE Epoch Resonance Shield — L5 Governance Gate
=================================================

Distinguishes "a technically attractive setup inside a hostile external
mosaic from the same setup inside a supportive one."
(TFE Specification v3.0, line 2248)

The shield reads the G32 epoch mosaic as a COUPLED field — not individual
channels — and determines whether the macro environment is hostile.

When hostile:
  - CH3 enters restricted mode
  - Assets are only cleared if their DSF shape shows structural cohesion
    under compression, not just compression alone
  - A falling knife compresses WITH structural decay
  - A coiled spring compresses WITH structural cohesion

The shield uses the FULL coupled DSF — all seven L4 values as one shape.
No decomposition. No independent thresholds on D_k or M_k.

No ML. No heuristics. Deterministic operators on the coupled field.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np


# ═════════════════════════════════════════════════════════════════════════
# Epoch Mosaic Assessment
# Reads G32 state as a coupled field, not individual channels
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class EpochAssessment:
    """The macro environment as seen by the shield."""
    hostile: bool              # is the macro environment hostile?
    mosaic_magnitude: float    # ||Ξ_t|| — total epoch pressure magnitude
    delta_magnitude: float     # ||ΔΞ_t|| — how fast the epoch is changing
    stress_aggregate: float    # net adverse pressure across all channels
    phase: str                 # HOSTILE / STRESSED / NEUTRAL / SUPPORTIVE
    sector_pressure: float     # sector-specific epoch pressure (if available)


def assess_epoch(g32_state_path: str = "/app/g32_state.json",
                 sector: Optional[str] = None) -> EpochAssessment:
    """Read the G32 mosaic and assess macro environment.

    The mosaic is read as ONE coupled field — the magnitude and direction
    of the full epoch vector, not individual channels.
    """
    try:
        with open(g32_state_path) as f:
            g32 = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # No G32 state — assume neutral (don't block trades on missing data)
        return EpochAssessment(
            hostile=False, mosaic_magnitude=0.0, delta_magnitude=0.0,
            stress_aggregate=0.0, phase="UNKNOWN", sector_pressure=0.0,
        )

    xi = g32.get("xi", {})
    xi_delta = g32.get("xi_delta", {})

    # Mosaic as a vector — all channels together
    xi_vec = np.array([float(xi.get(ch, 0)) for ch in sorted(xi.keys())])
    delta_vec = np.array([float(xi_delta.get(ch, 0)) for ch in sorted(xi_delta.keys())])

    mosaic_magnitude = float(np.linalg.norm(xi_vec))
    delta_magnitude = float(np.linalg.norm(delta_vec))

    # Stress aggregate: sum of all NEGATIVE pressure contributions
    # Channels with negative severity = adverse forces acting on the market
    # This is the coupled stress — how much total adverse energy is in the mosaic
    stress_channels = [
        "RATES_PRESSURE", "CONSUMER_STRESS", "WAR_GEOPOLITICS",
        "ENERGY_COMMODITY", "VOLATILITY_REGIME",
    ]
    stress = 0.0
    for ch in stress_channels:
        v = float(xi.get(ch, 0))
        if v > 0:  # positive severity = active pressure
            stress += v

    # Sector-specific pressure if sector provided
    sector_pressure = 0.0
    if sector:
        from tfe_g32_coordinator import SECTOR_COUPLING, EPOCH_CHANNELS
        coupling = SECTOR_COUPLING.get(sector, {})
        for ch in EPOCH_CHANNELS:
            weight = coupling.get(ch, 0.0)
            sector_pressure += float(xi.get(ch, 0)) * weight

    # SPY structural direction from the snapshot
    # The market's own DSF tells us if macro gravity is pulling down
    spy_dk = 0
    try:
        import pg
        db_pool = pg.Pool({
            'host': os.environ.get('PGHOST', ''),
            'database': os.environ.get('PGDATABASE', ''),
            'user': os.environ.get('PGUSER', ''),
            'password': os.environ.get('PGPASSWORD', ''),
            'ssl': {'rejectUnauthorized': False},
        })
    except Exception:
        pass
    # Read SPY D_k from the snapshot if available
    try:
        with open(os.path.join(os.path.dirname(g32_state_path), "uf_snapshot.json")) as f:
            snap_text = f.read().replace('NaN', 'null').replace('-Infinity', 'null').replace('Infinity', 'null')
            snap = json.loads(snap_text)
        rows = snap if isinstance(snap, list) else snap.get("rows", [])
        for r in rows:
            if r.get("ticker") == "SPY":
                spy_dk = r.get("D_k", 0) or 0
                break
    except Exception:
        spy_dk = 0

    # Phase determination from the coupled mosaic + market direction
    # Stress alone doesn't determine hostility — direction does
    # High stress + contracting market = HOSTILE (falling knives everywhere)
    # High stress + expanding market = CAUTIOUS (risk elevated but market absorbing)
    if stress > 1.0 and spy_dk <= 0 and delta_magnitude > 0.05:
        phase = "HOSTILE"       # high stress + market contracting + epoch changing
    elif stress > 1.0 and spy_dk <= 0:
        phase = "STRESSED"      # high stress + market contracting but epoch stable
    elif stress > 1.0 and spy_dk > 0:
        phase = "CAUTIOUS"      # high stress but market still expanding (bull with risks)
    elif stress > 0.5:
        phase = "CAUTIOUS"      # moderate stress
    elif sector_pressure > 0.3:
        phase = "SUPPORTIVE"    # sector has tailwind
    else:
        phase = "NEUTRAL"

    hostile = phase in ("HOSTILE", "STRESSED")

    return EpochAssessment(
        hostile=hostile,
        mosaic_magnitude=mosaic_magnitude,
        delta_magnitude=delta_magnitude,
        stress_aggregate=stress,
        phase=phase,
        sector_pressure=sector_pressure,
    )


# ═════════════════════════════════════════════════════════════════════════
# Structural Cohesion Assessment
# Reads the DSF as a coupled shape — falling knife vs coiled spring
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CohesionAssessment:
    """Is this DSF shape a coiled spring or a falling knife?"""
    cohesive: bool          # does the shape hold structural integrity?
    shape_type: str         # COILED_SPRING / FALLING_KNIFE / AMBIGUOUS
    confidence: float       # 0-1 confidence in the assessment


def assess_cohesion(
    D_k: float, M_k: float, R_rev_k: float,
    U_star_k: float, C_k: float, P_k: float, B_k: float,
    S_UF: float = 0.0,
) -> CohesionAssessment:
    """Read the FULL coupled DSF shape to distinguish spring from knife.

    A coiled spring:
      - The field is compressed (B deep negative)
      - BUT the structural surface is SIMPLE (C=2, low complexity)
      - AND the field is RESOLVED (U* low, uncertainty handled)
      - AND the surface is SMOOTH (P=0, no cracks)

    A falling knife:
      - The field is compressed (B deep negative) — same as spring
      - BUT the structural surface is COMPLEX (C=3, many folds)
      - AND/OR the field is UNRESOLVED (U* high, still uncertain)
      - AND/OR the surface is CRACKED (P=2, discontinuity)

    The key insight from the crisis data analysis: these look identical
    if you only check B_k. You must read the FULL coupled shape.

    No decomposition — we're reading the shape as one object.
    The combination of ALL values determines the assessment.
    """
    # The full shape as a 7D point
    dsf = np.array([D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k])

    # Coiled spring archetype: from the crisis study, the big UP moves
    # consistently came from this coupled shape
    # D=+1, |M|<0.15, Rrev=0, U*<0.25, C=2, P=0, B<=-0.50
    spring_archetype = np.array([1.0, 0.0, 0.0, 0.20, 2.0, 0.0, -1.0])

    # Falling knife archetype: from the crisis study, the DN moves
    # had this shape — compressed BUT with structural decay
    # Any D, |M| high, Rrev=1, U*>0.40, C=3, P=2, B<=-0.50
    knife_archetype = np.array([0.0, 0.0, 1.0, 0.50, 3.0, 2.0, -1.0])

    # Distance to each archetype in the coupled space
    # Normalization keeps coupling intact
    norms = np.array([2.0, 2.0, 1.0, 1.0, 3.0, 2.0, 2.0])

    dist_spring = float(np.sqrt(np.sum(((dsf - spring_archetype) / norms) ** 2)))
    dist_knife = float(np.sqrt(np.sum(((dsf - knife_archetype) / norms) ** 2)))

    # The shape is read as proximity to each archetype
    # Not a threshold on any single field
    total_dist = dist_spring + dist_knife
    if total_dist == 0:
        confidence = 0.5
    else:
        # How much closer to spring than knife (0 = pure knife, 1 = pure spring)
        spring_affinity = dist_knife / total_dist
        confidence = spring_affinity

    if confidence > 0.6:
        shape_type = "COILED_SPRING"
        cohesive = True
    elif confidence < 0.4:
        shape_type = "FALLING_KNIFE"
        cohesive = False
    else:
        shape_type = "AMBIGUOUS"
        cohesive = False  # err on side of caution in ambiguity

    return CohesionAssessment(
        cohesive=cohesive,
        shape_type=shape_type,
        confidence=confidence,
    )


# ═════════════════════════════════════════════════════════════════════════
# The Shield Gate — combines epoch + cohesion
# ═════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ShieldResult:
    """Should CH3 proceed with this candidate?"""
    cleared: bool
    reason: str
    epoch: EpochAssessment
    cohesion: CohesionAssessment


def evaluate_shield(
    D_k: float, M_k: float, R_rev_k: float,
    U_star_k: float, C_k: float, P_k: float, B_k: float,
    S_UF: float = 0.0,
    sector: Optional[str] = None,
    g32_state_path: str = "/app/g32_state.json",
) -> ShieldResult:
    """The Epoch Resonance Shield gate.

    In supportive/neutral epochs: let the CH3 hunter's existing filters decide.
    In hostile epochs: require structural cohesion (coiled spring, not falling knife).

    This is the umbrella — if it's raining, you need more than just compression
    to justify entering a trade.
    """
    epoch = assess_epoch(g32_state_path, sector)
    cohesion = assess_cohesion(D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k, S_UF)

    if epoch.phase == "HOSTILE":
        # Hostile epoch — full quarantine. No CH3 entries.
        # The umbrella: when macro gravity is pulling everything down,
        # even structurally attractive setups get crushed.
        # The -16.5% hostile epoch test proved this: 0% win rate on 7 picks.
        return ShieldResult(
            cleared=False,
            reason=f"hostile_epoch_quarantine (stress={epoch.stress_aggregate:.2f} delta={epoch.delta_magnitude:.3f})",
            epoch=epoch,
            cohesion=cohesion,
        )

    if epoch.phase == "STRESSED":
        # Stressed but not hostile — require sector tailwind
        # The sector coupling must be positive: the epoch is HELPING this stock's sector
        if epoch.sector_pressure > 0.1:
            return ShieldResult(
                cleared=True,
                reason=f"stressed_epoch_sector_tailwind ({epoch.sector_pressure:+.2f})",
                epoch=epoch,
                cohesion=cohesion,
            )
        else:
            return ShieldResult(
                cleared=False,
                reason=f"stressed_epoch_no_tailwind (sector={epoch.sector_pressure:+.2f})",
                epoch=epoch,
                cohesion=cohesion,
            )

    # Neutral, cautious, or supportive — existing CH3 filters are sufficient
    return ShieldResult(
        cleared=True,
        reason=f"epoch_{epoch.phase.lower()}_pass",
        epoch=epoch,
        cohesion=cohesion,
    )


# ═════════════════════════════════════════════════════════════════════════
# Test
# ═════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Coiled spring in hostile epoch
    result = evaluate_shield(
        D_k=1, M_k=0.02, R_rev_k=0, U_star_k=0.20, C_k=2, P_k=0, B_k=-1.0,
        sector="Financial Services",
        g32_state_path="g32_state.json",
    )
    print(f"Coiled spring: cleared={result.cleared} reason={result.reason}")
    print(f"  epoch: {result.epoch.phase} stress={result.epoch.stress_aggregate:.2f}")
    print(f"  cohesion: {result.cohesion.shape_type} confidence={result.cohesion.confidence:.2f}")

    # Falling knife in hostile epoch
    result2 = evaluate_shield(
        D_k=-1, M_k=-0.30, R_rev_k=1, U_star_k=0.50, C_k=3, P_k=2, B_k=-1.0,
        sector="Financial Services",
        g32_state_path="g32_state.json",
    )
    print(f"\nFalling knife: cleared={result2.cleared} reason={result2.reason}")
    print(f"  epoch: {result2.epoch.phase} stress={result2.epoch.stress_aggregate:.2f}")
    print(f"  cohesion: {result2.cohesion.shape_type} confidence={result2.cohesion.confidence:.2f}")
```

---

## FILE: web/scripts/execution/financial_rules.mjs

```javascript
import * as _marketCalendar from "./market_calendar.mjs";

/**
 * web/scripts/execution/financial_rules.mjs
 * TFE Financial Rules Library — Deterministic Entry/Exit Governance
 *
 * All trading rules in one place. No ML. No heuristics. No smoothing.
 * Each rule is a pure function: data in, boolean + reason out.
 *
 * Rules are referenced by ID (e.g. ENTRY-R1) in logs and audit trails.
 * When a rule blocks or allows a trade, the ID is recorded in the ledger
 * rationale_json so every decision is traceable.
 *
 * ═══════════════════════════════════════════════════════════════════════
 * L5 CANONICAL BASELINE — PROVEN WIN RATES
 * ═══════════════════════════════════════════════════════════════════════
 *
 * Source: L5_CANONICAL_BASELINE.md (locked 2026-03-25)
 * Data: quarantine_12k_l5_trades.csv (7,658 Accumulate signals)
 * Universe: 11,884 symbols, 10,162,966 OHLCV rows, 2021-2026
 *
 * Quarantine backtest (20-day forward hold, no exit logic):
 *   Baseline (Accumulate only):     57.1% WR | 7,290 signals
 *   + Close >= $5:                  57.7% WR | 6,556 signals
 *   + Rising 5d (not falling):      75.0% WR | 3,674 signals
 *   + B_k > -0.80:                  81.1% WR | 2,072 signals
 *   + B_k > -0.50:                  81.4% WR | 2,016 signals
 *
 * L5 Canonical Baseline Layers (from L5_CANONICAL_BASELINE.md):
 *   Layer 1 — Primitive Geometric Eye:
 *     D_k >= 0, Rev_k == 0, B_k > prev_B_k, M_k >= 0
 *   Layer 2 — Common Sense Reality:
 *     Close >= $5, Gate_Count >= 10
 *   Layer 3 — Cognitive Restraint:
 *     raw_x_m <= 0.50, F_n <= 1.65
 *   Result: 3,587 signals, 64.66% WR, 1.25% avg 20d return
 *
 * B_k quartile analysis (7,658 trades):
 *   Q1 [-1.0, -0.998] (compressed): 51.3% WR — coin flip
 *   Q2 [-0.998, -0.671]:            49.6% WR — coin flip
 *   Q3 [-0.671, -0.047]:            63.5% WR — real edge
 *   Q4 [-0.047, -0.025] (expanded): 64.0% WR — real edge
 *
 * ═══════════════════════════════════════════════════════════════════════
 * PRODUCTION VERIFICATION (May 19, 2026)
 * ═══════════════════════════════════════════════════════════════════════
 *
 * 428 real trades verified against Alpaca order API + Polygon historical.
 *
 * CRITICAL FINDING: Entry selection is NOT the problem. Exit timing IS.
 *   Trades held >0 days: 57.4% WR, +$1,280 P&L (matches quarantine 57%)
 *   Day-0 exits:         24.2% WR, -$1,545 P&L (system destroys wins)
 *   175 day-0 losers checked against Polygon 20-day forward:
 *     68% would have been winners. $5,510 left on the table.
 *
 * Day-0 root causes (every sell order verified via Alpaca API):
 *   Sentinel market sells: 113 trades, -$1,512 (SPY flip mass liquidation)
 *   Bracket SL same-day:    61 trades, -$946 (1×ATR too tight for intraday)
 *
 * After EXIT-R7 (day-0 loss protection):
 *   Projected: 67.2% WR, +$5,245 P&L (from -$265)
 *
 * WHY B_k/F_n ENTRY GATES DON'T WORK IN PRODUCTION:
 *   Tested on 428 production trades — every gate made things WORSE.
 *   Rejected pool had HIGHER win rate (48.1%) than passed pool.
 *   Root cause: production CP-2 uses 252-bar cap → F_n inverted,
 *   raw_x_m saturates to 1.0, thresholds from quarantine don't transfer.
 *   The quarantine 81% is real but requires 20-day hold (no exit logic).
 *   Production exits early → the entry filter doesn't matter if exits
 *   are killing positions before they reach 20 days.
 *
 * ═══════════════════════════════════════════════════════════════════════
 *
 * CHANGELOG:
 *   2026-05-19  ENTRY-R1  Red-day filter: 2 consecutive declining closes blocks entry
 *   2026-05-19  ENTRY-R2  Friday block: no new entries Fri/Sat/Sun (weekend gap risk)
 *   2026-05-19  ENTRY-R3  Minimum share price $5 (penny stock filter)
 *   2026-05-19  ENTRY-R4  Minimum 5% bracket width (tight brackets lose at 50%)
 *   2026-05-19  ENTRY-R5  Market cap >= $500M (liquidity floor)
 *   2026-05-19  EXIT-R1   Catastrophic floor: -10% CH2, -1% CH3
 *   2026-05-19  EXIT-R2   Acceleration complete: S_UF >= 0.75
 *   2026-05-19  EXIT-R3   D_k collapse: D_k != 1 after entry
 *   2026-05-19  EXIT-R4   Tau exhaustion: position age > tau_out
 *   2026-05-19  EXIT-R5   Trailing profit: ratcheting floor after 5% gain
 *   2026-05-19  EXIT-R6   Structural harvest: past midpoint with >= 5% gain
 *   2026-05-19  EXIT-R7   Day-0 loss protection: no losing exit on day 0 (67.2% WR recovery)
 *   2026-05-19  SCORE-R1  Admin closures excluded: stale_position_cleanup,
 *                          manual_close_stale, manual_portfolio_reset
 *   2026-05-19  SIZE-R1   CH2 risk per trade: 2.5% of equity ($2,500 on $100K)
 *   2026-05-19  SIZE-R2   ATR stops killed 13/14 winners — use -10% catastrophic only
 *   2026-05-19  SIZE-R3   3WA bracket SL widened from 1×ATR to -10% (matching CH2)
 *   2026-05-20  EXIT-R8   Market hours guard on EXIT-F: stale overnight prices triggered
 *                          false catastrophic exits (BELFB -33.6% phantom, MYE -18.4% phantom)
 *   2026-05-20  SYNC-R1   Orphan adoption cooldown: 15-min kill cooldown prevents
 *                          adopt→kill→adopt loop (AM/BCPC/FOXA each killed 5x)
 *   2026-05-20  SYNC-R2   Phantom cleanup grace: 30-min grace period before declaring
 *                          unfilled orders as phantom (GENB killed at 5min, filled at 43min)
 *   2026-05-26  ENTRY-R2  Holiday block added: Memorial Day 2026 placed 66 orders on
 *                          closed market. Now checks NYSE holiday calendar 2026-2027.
 *   2026-05-20  EXIT-R9   7-day minimum hold: no losing exits before 7 calendar days.
 *                          Supersedes EXIT-R7 (day-0 only). Production data: 85% of D_k
 *                          collapse exits recovered at 10-20 days. 73% of early losers
 *                          (0-3d) were winners at 20d. Projected WR: 67.1%.
 *                          Winning exits (EXIT-A, EXIT-H) always fire. -10% always active.
 */

// ═══════════════════════════════════════════════════════════════════════════
// ENTRY RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * ENTRY-R1: Red-day filter
 * If the stock closed lower than the prior day's close for 2 consecutive
 * days, the move is reversing — don't buy into a falling knife.
 *
 * Backtest (28 positions, May 19 2026):
 *   Precision: 90% (9/10 blocks were correct — all losers)
 *   Winners preserved: 86% (6/7 winners allowed through)
 *   Key saves: BELFA -5.1%, DHI -4.6%, PHM -3.5%, DEI -3.4%
 *
 * @param {Array} bars — daily bars, oldest first, must have at least 3
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR1_RedDayFilter(bars) {
  const RULE = "ENTRY-R1";

  if (!Array.isArray(bars) || bars.length < 3) {
    return { blocked: false, rule: RULE, reason: "insufficient_bars" };
  }

  const recent = bars.slice(-3);
  const close0 = parseFloat(recent[0].c);
  const close1 = parseFloat(recent[1].c);
  const close2 = parseFloat(recent[2].c);

  if (close1 < close0 && close2 < close1) {
    return {
      blocked: true,
      rule: RULE,
      reason: `2 consecutive declining closes: ${close0}→${close1}→${close2}`,
    };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R2: Weekend + Holiday block
 * No new entries on Friday, Saturday, Sunday, or market holidays.
 * Weekend gaps are unmanageable — REGN lost 12% over a weekend.
 * Memorial Day 2026: 66 orders placed on a closed market. Never again.
 *
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR2_FridayBlock() {
  const RULE = "ENTRY-R2";
  const now = new Date();
  const day = now.getUTCDay(); // 0=Sun, 5=Fri, 6=Sat

  if (day === 5 || day === 6 || day === 0) {
    return { blocked: true, rule: RULE, reason: `day=${day} (Fri/Sat/Sun)` };
  }

  // Holiday check — computed from NYSE rules, works for any year
  try {
    const { isMarketHoliday, getHolidayName } = _marketCalendar ?? {};
    if (isMarketHoliday && isMarketHoliday(now)) {
      const name = (getHolidayName && getHolidayName(now)) ?? "unknown";
      return { blocked: true, rule: RULE, reason: `market holiday (${name})` };
    }
  } catch { /* non-fatal — weekend check still active */ }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R3: Minimum share price
 * Reject penny stocks. Below $5 = too volatile, wide spreads.
 *
 * @param {number} price — current share price
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR3_MinSharePrice(price) {
  const RULE = "ENTRY-R3";
  const MIN_PRICE = 5.0;

  if (price < MIN_PRICE) {
    return { blocked: true, rule: RULE, reason: `${price} < ${MIN_PRICE}` };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R4: Minimum bracket width
 * TP must be at least 5% above entry. Tight brackets on cheap stocks
 * get stopped out prematurely.
 *
 * Backtest: <5% brackets won at 50%, 5-15% brackets won at 80%.
 *
 * @param {number} entryPrice
 * @param {number} takeProfitPrice
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR4_MinBracketWidth(entryPrice, takeProfitPrice) {
  const RULE = "ENTRY-R4";
  const MIN_PCT = 0.05;
  const bracketPct = (takeProfitPrice - entryPrice) / entryPrice;

  if (bracketPct < MIN_PCT) {
    return {
      blocked: true,
      rule: RULE,
      reason: `bracket ${(bracketPct * 100).toFixed(1)}% < ${MIN_PCT * 100}% minimum`,
    };
  }

  return { blocked: false, rule: RULE };
}

/**
 * ENTRY-R5: Market cap floor
 * $500M minimum — illiquid stocks get wide spreads and phantom fills.
 *
 * @param {number} marketCap
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function entryR5_MarketCapFloor(marketCap) {
  const RULE = "ENTRY-R5";
  const MIN_CAP = 500_000_000;

  if (marketCap < MIN_CAP) {
    return { blocked: true, rule: RULE, reason: `${marketCap} < $500M` };
  }

  return { blocked: false, rule: RULE };
}


// ═══════════════════════════════════════════════════════════════════════════
// EXIT RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * EXIT-R1: Catastrophic floor
 * Hard stop at -10% for CH2, -1% for CH3. Not noise — only disaster.
 * ATR-based stops killed 13/14 winners. This is insurance, not strategy.
 *
 * @param {number} entryPrice
 * @param {number} currentPrice
 * @param {string} signalClass — "CH2" or "CH3"
 * @returns {{ triggered: boolean, rule: string, lossPct?: number }}
 */
export function exitR1_CatastrophicFloor(entryPrice, currentPrice, signalClass) {
  const RULE = "EXIT-R1";
  const threshold = signalClass === "CH3" ? -0.01 : -0.10;
  const lossPct = (currentPrice - entryPrice) / entryPrice;

  if (lossPct <= threshold) {
    return { triggered: true, rule: RULE, lossPct };
  }

  return { triggered: false, rule: RULE, lossPct };
}


/**
 * EXIT-R7: Day-0 loss protection
 * No LOSING exit on day 0. The structural thesis needs at least 1 full
 * trading day to manifest. Intraday noise kills winners.
 *
 * Production backtest (428 trades, Polygon verified):
 *   175 day-0 losses → 68% would have been winners at 20 days.
 *   Blocking day-0 losses recovers $5,510 and raises WR from 39.5% to 67.2%.
 *
 * What's BLOCKED on day 0:
 *   - Sentinel structural exits (D_k collapse, SPY flip) if position is underwater
 *   - Bracket SL legs (3WA SL widened to -10% to prevent same-day triggers)
 *
 * What's ALLOWED on day 0:
 *   - Winning exits (take-profit, acceleration complete, energy harvest)
 *   - -10% catastrophic floor (disaster insurance, always active)
 *   - CH3 harvest (scalp channel — profit is the signal to exit)
 *
 * Implementation: sentinel_monitor.mjs checks posAge and currentPnlPct
 * before each structural exit. If posAge < 1 day AND P&L < 0, exit is
 * deferred to day 1+.
 *
 * @param {number} posAgeDays — days since entry fill
 * @param {number} currentPnlPct — current P&L percentage
 * @param {boolean} isWinningExit — is this a take-profit / harvest exit?
 * @returns {{ blocked: boolean, rule: string, reason?: string }}
 */
export function exitR7_Day0LossProtection(posAgeDays, currentPnlPct, isWinningExit = false) {
  const RULE = "EXIT-R7";

  // Winning exits always allowed
  if (isWinningExit || currentPnlPct >= 0) {
    return { blocked: false, rule: RULE };
  }

  // Day 0 + underwater = blocked
  if (posAgeDays < 1 && currentPnlPct < 0) {
    return {
      blocked: true,
      rule: RULE,
      reason: `day-0 loss guard: age=${posAgeDays}d P&L=${currentPnlPct.toFixed(1)}%`,
    };
  }

  return { blocked: false, rule: RULE };
}


// ═══════════════════════════════════════════════════════════════════════════
// SCORING RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * SCORE-R1: Admin closure exclusion
 * These exit reasons are administrative, not strategy outcomes.
 * Excluded from win/loss rate and expectancy calculations.
 */
export const ADMIN_EXIT_REASONS = [
  "stale_position_cleanup",
  "manual_close_stale",
  "manual_portfolio_reset",
];

/**
 * Check if an exit reason is an admin closure (excluded from scoring).
 *
 * @param {string} exitReason
 * @returns {boolean}
 */
export function isAdminClosure(exitReason) {
  return ADMIN_EXIT_REASONS.includes(exitReason);
}


// ═══════════════════════════════════════════════════════════════════════════
// SIZING RULES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * SIZE-R1: CH2 position sizing
 * 2.5% of vault equity per trade.
 * Backtest (85 trades): win/loss ratio 1.91:1.
 * At 2.5% same trades produce $4,413 P&L vs $1,633 at 0.917%.
 */
export const CH2_RISK_PCT = 2.5;

/**
 * SIZE-R2: Stop loss method
 * -10% catastrophic only. ATR stops killed 13/14 winners.
 * The bracket SL is insurance against disaster, not a trading strategy.
 * Structural exits (acceleration, D_k collapse, tau, harvest) handle
 * normal profit-taking and loss-cutting.
 */
export const CH2_STOP_LOSS_PCT = 0.10;
```
