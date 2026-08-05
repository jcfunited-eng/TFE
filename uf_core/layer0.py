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
from enum import Enum
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
    relevance: float     # deterministic domain-adapter relevance r(t)
    N: int               # structural negative-space indicator (0 or 1)


class RelevanceMode(str, Enum):
    """Deterministic domain-adapter authority for the SEV relevance field."""

    LEGACY_UNIT = "legacy_unit"
    STRUCTURAL_ACTIVITY_DIAGNOSTIC = "structural_activity_diagnostic"


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

def compute_sev_series(
    df: pd.DataFrame,
    field_col: str = "Close",
    *,
    relevance_mode: RelevanceMode | str = RelevanceMode.LEGACY_UNIT,
):
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
        7. Resolve r(t) from the explicit domain-adapter relevance mode.

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

    try:
        resolved_relevance_mode = RelevanceMode(relevance_mode)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in RelevanceMode)
        raise ValueError(
            f"Unsupported relevance_mode={relevance_mode!r}; expected one of: {allowed}"
        ) from exc

    if resolved_relevance_mode is RelevanceMode.LEGACY_UNIT:
        # Preserve the frozen financial-domain behavior for existing callers.
        relevance = np.ones(n, dtype=float)
    else:
        # Diagnostic only: this proves that replacing the legacy hardcoded
        # relevance restores Negative Space while preserving graded activity.
        # It is not GLEW production authority; the ratified bioequivalent
        # chemical transducer must supply production relevance.
        alpha1 = float(KERNEL_THRESHOLDS.alpha1)
        alpha2 = float(KERNEL_THRESHOLDS.alpha2)
        alpha3 = float(KERNEL_THRESHOLDS.alpha3)
        tau_D = float(KERNEL_THRESHOLDS.tau_D)
        if tau_D <= 0.0:
            raise ValueError("KERNEL_THRESHOLDS.tau_D must be positive.")

        deviation = alpha1 * np.abs(dF) + alpha2 * sigma + alpha3 * kappa
        relevance = np.where(
            N_vec == 1,
            0.0,
            deviation / (deviation + tau_D),
        )

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
