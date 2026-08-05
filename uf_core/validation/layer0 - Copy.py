"""
uf_core.layer0 — Structural Field Normalization (UF-Spec v1.4.0)
================================================================

Implements L0 from the Unified Framework Specification v1.4.0.

This module produces the Normalized Structural Field (NSF) by converting
raw input time series F(t) into State Embedding Vectors SEV(t) with
well-defined structural interpretations:

    SEV(t) = (F(t), ΔF(t), σ(t), κ(t), r(t), N(t))

Key properties enforced here:

- Negative-space N(t) is a structural operator, not a heuristic flag.
- Input Health Verification (IHV) is a HARD precondition.
- Local variance σ(t) is computed using a kernel parameterized window
  size (see KERNEL_THRESHOLDS), calibrated via the validation suite.
"""

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .config import KERNEL_THRESHOLDS


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SEV:
    """State Embedding Vector for UF-Spec v1.4.0."""
    F: float         # raw field value
    dF: float        # ΔF(t)
    sigma: float     # local variance
    kappa: float     # curvature proxy
    relevance: float # r(t), to be refined
    N: int           # structural negative-space indicator (0 or 1)


# ---------------------------------------------------------------------------
# Input Health Verification (IHV)
# ---------------------------------------------------------------------------

def input_health_verification(df: pd.DataFrame, price_col: str) -> bool:
    """
    Validate input according to UF-Spec v1.4.0 L0 requirements.

    Preconditions:
    - Index is datetime-like or numeric.
    - Index is strictly monotonic increasing.
    - No missing values in the price column.
    - All values finite.
    """

    # Ensure price column exists
    if price_col not in df.columns:
        print(f"[IHV] ERROR: Column '{price_col}' not found.")
        return False

    # Index type check
    if not isinstance(df.index, pd.DatetimeIndex) and not np.issubdtype(df.index.dtype, np.number):
        print("[IHV] ERROR: Index must be datetime or numeric.")
        return False

    # Monotonic index
    if not df.index.is_monotonic_increasing:
        print("[IHV] ERROR: Non-monotonic index.")
        return False

    # Missing values
    if df[price_col].isna().any():
        print("[IHV] ERROR: Missing price values.")
        return False

    # Finite values
    if not np.isfinite(df[price_col].values).all():
        print("[IHV] ERROR: Non-finite numerical price encountered.")
        return False

    return True


# ---------------------------------------------------------------------------
# L0 — Structural Field Normalization
# ---------------------------------------------------------------------------

def compute_sev_series(df: pd.DataFrame, price_col: str = "Close"):
    """
    Convert raw data (df) into a sequence of SEV objects (NSF).

    df: pandas DataFrame with at least a price column (default: 'Close').

    This function enforces:
    - IHV as a precondition.
    - σ(t) computed with a finite rolling window of size
      KERNEL_THRESHOLDS.variance_window.
    - N(t) based on σ(t), |ΔF(t)|, and κ(t) relative to kernel thresholds.

    NOTE:
    - The window length and thresholds are kernel parameters that MUST be
      validated and tuned via the UF validation suite (Section 13).
    """

    if not input_health_verification(df, price_col):
        raise RuntimeError("InputHealthVerificationFailed: L0 aborted.")

    F = df[price_col].astype(float).values
    n = len(F)

    dF = np.zeros(n)
    sigma = np.zeros(n)
    kappa = np.zeros(n)
    relevance = np.ones(n)  # r(t) will be specialized later
    N_vec = np.zeros(n, dtype=int)

    # ΔF(t)
    if n > 1:
        dF[1:] = np.diff(F)

    # σ(t): local variance with kernel window from config
    w = max(1, getattr(KERNEL_THRESHOLDS, "variance_window", 5))
    for i in range(n):
        start = max(0, i - w + 1)
        segment = F[start:i+1]
        sigma[i] = float(np.var(segment)) if len(segment) > 1 else 0.0

    # κ(t): curvature proxy (discrete 2nd derivative)
    if n > 2:
        for i in range(1, n - 1):
            kappa[i] = abs(F[i+1] - 2.0*F[i] + F[i-1])
    # endpoints remain 0.0 by definition

    # N(t): structural negative-space operator
    for i in range(n):
        cond1 = sigma[i] < KERNEL_THRESHOLDS.sigma_min
        cond2 = abs(dF[i]) < KERNEL_THRESHOLDS.delta_min
        cond3 = kappa[i] < KERNEL_THRESHOLDS.kappa_min
        N_vec[i] = 1 if (cond1 and cond2 and cond3) else 0

    # Build NSF as list of SEV
    sev_list = [
        SEV(
            F=F[i],
            dF=dF[i],
            sigma=sigma[i],
            kappa=kappa[i],
            relevance=relevance[i],
            N=N_vec[i],
        )
        for i in range(n)
    ]

    return sev_list
