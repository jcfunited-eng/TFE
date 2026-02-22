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
