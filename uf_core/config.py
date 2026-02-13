"""
uf_core.config — Kernel Thresholds (UF-Spec v1.4.0)
===================================================

This file defines all kernel-level structural constants used by
UF-Core L1–L4, including:

    • τ_D          – minimum gate delta threshold
    • epsilon_D    – directional epsilon for DSF (L4)
    • U_max        – maximum uncertainty allowed before gating (L3)
    • λ1–λ5        – resonance weights (L3)
    • B_min/max    – breathing clamps (L4)
    • η_H, η_IAS   – uncertainty amplification weights (L4)
"""

from dataclasses import dataclass


@dataclass
class KernelThresholds:
    # ------------------------------------------------------------
    # L1 / L2 thresholds
    # ------------------------------------------------------------
    tau_D: float = 0.20            # minimum gate structural delta
    sigma_min: float = 1e-6
    delta_min: float = 1e-6
    kappa_min: float = 1e-6
    variance_window: int = 20

    # ------------------------------------------------------------
    # L4 directional epsilon (DSF)
    # ------------------------------------------------------------
    epsilon_D: float = 0.00073     # controls D_k sensitivity

    # ------------------------------------------------------------
    # L3 gating threshold
    # ------------------------------------------------------------
    U_max: float = 0.75            # gates suppressed if U_k > U_max

    # ------------------------------------------------------------
    # L3 resonance weights (UF-Spec v1.4.0 Section 6)
    # These are REQUIRED for compute_raw_resonance()
    # ------------------------------------------------------------
    lambda1: float = 1.0           # weight for w_k
    lambda2: float = 1.0           # weight for CV norm
    lambda3: float = 1.0           # weight for S_k
    lambda4: float = 1.0           # weight for cohesion term 1/(1+C_k)
    lambda5: float = 1.0           # weight for (1 - U_k)

    # ------------------------------------------------------------
    # L4 uncertainty amplification terms (Spec Section 7.6)
    # ------------------------------------------------------------
    eta_H: float = 0.10            # hysteresis uncertainty injection
    eta_IAS: float = 0.10          # anomaly uncertainty injection

    # ------------------------------------------------------------
    # L4 breathing clamps
    # ------------------------------------------------------------
    B_min: float = -1.0
    B_max: float = 1.0

    # L4 breathing coefficients
    breath_xi: float = 0.10        # expansion on low uncertainty
    breath_chi: float = 0.10       # contraction on high uncertainty


# Create singleton
KERNEL_THRESHOLDS = KernelThresholds()
