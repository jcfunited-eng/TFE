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

from .neuron import PSI_DIM, J_BASE, J_MAX
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

    def update_from_dsf(self, dsf) -> None:
        """Update cross-hemi J from DSF — same mechanism as CouplingsJij.

        Per -98: coupling_matrix_diag produces 8 values from DSF, repeated
        2× for 16 modes. No ring-distance scaling for cross-hemi (all
        connections are topologically equivalent at this level).
        Uses same J_BASE and J_MAX as intra couplings — no new constants.
        """
        if len(self.targets) == 0 or dsf is None:
            return
        diag = dsf.coupling_matrix_diag(J_base=J_BASE, J_max=J_MAX)
        values = np.array(list(diag.values()), dtype=np.float64)
        row = np.repeat(values, 2)  # 16 modes
        for i in range(len(self.targets)):
            self.J[i] = row  # no ring-distance scaling for cross-hemi
