"""
cross_hemi.py — Cross-hemisphere coupling for projection neurons.

GL-CMD-113 V2.3.

Sibling to CouplingsJij. Separate budget K_INTERHEMI=2, initial strength
J_BASE * CROSS_HEMI_INITIAL_STRENGTH. Same signal-carry mechanism as
intra-cluster couplings (spike → signal_accumulator + ω modulation).

Does NOT count toward intra K_TOTAL for contact inhibition.
"""

import numpy as np
from typing import List, Tuple

from .neuron import PSI_DIM, J_BASE
from .topology import K_INTERHEMI, CROSS_HEMI_INITIAL_STRENGTH


class CrossHemiCouplings:
    """Cross-hemisphere coupling matrix for a projection neuron.

    K_INTERHEMI connections to neurons in adjacent hemispheres.
    Initial strength: J_BASE * CROSS_HEMI_INITIAL_STRENGTH (weak at seed).
    """

    def __init__(self, n_modes: int = PSI_DIM,
                 targets: List[Tuple[str, str]] = None):
        """
        Args:
            n_modes: PSI_DIM (must match intra couplings)
            targets: list of (target_neuron_id, target_hemi_id) tuples
        """
        self.n_modes = n_modes
        self.targets: List[Tuple[str, str]] = targets or []
        K = len(self.targets)
        initial_j = J_BASE * CROSS_HEMI_INITIAL_STRENGTH
        self.J = np.full((K, n_modes), initial_j, dtype=np.float64)

    def get_weight(self, idx: int) -> float:
        """Mean J weight for target at index idx."""
        if idx >= len(self.targets):
            return 0.0
        return float(np.mean(self.J[idx]))
