"""
uf_core.config
----------------
Core configuration module for the Unified Framework (UF) kernel
used by the Tao Financial Engine.

This module centralizes:
- UF and SES version identifiers
- High-level kernel configuration parameters
- Thresholds and tunable constants aligned with UF-Spec v1.4.0
"""

from dataclasses import dataclass


# ----------------------------------------------------------------------
# Version identifiers
# ----------------------------------------------------------------------

UF_VERSION: str = "1.4.0"
SES_VERSION: str = "0.1.0"


# ----------------------------------------------------------------------
# Kernel thresholds & parameters
# ----------------------------------------------------------------------

@dataclass
class KernelThresholds:
    """
    Global kernel thresholds for the UF v1.4.0 implementation.

    Adjusted directional threshold epsilon_D = 0.00073
    to allow L4 directional detection of realistic ΔR(t)
    produced by L3 resonance transitions.
    """

    # L1 — Gate deviation threshold τ_D
    tau_D: float = 0.20

    # L0 — Negative-space operator thresholds
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6

    # L0 — Rolling window length for variance computation σ(t)
    variance_window: int = 20

    # L4 — Directional signal ΔR(k) threshold
    epsilon_D: float = 0.00073

    # L2 — Uncertainty threshold for IAS_k
    U_max: float = 0.75


# Global instance
KERNEL_THRESHOLDS = KernelThresholds()
