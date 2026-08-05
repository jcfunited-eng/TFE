"""Exact neuronal L6 Topological Constraint Layer.

This module is the Chi-free home of the neuronal L6 state that was formerly
bundled with ``ChiAtlas``.  The equations and durable fields are intentionally
unchanged; only the obsolete identity/binding container was split away.
"""

from __future__ import annotations

import math


N_START = 8


class L6_TCL:
    """L6 Topological Constraint Layer / dimensional grinder."""

    def __init__(self, n_start=N_START):
        self.n_start = n_start
        self.capture_threshold = n_start / math.e

    def n_eff(self, dsf):
        """Return the effective dimension for the complete eight-field DSF."""
        constraints = 0
        for value in (
            dsf.D_k,
            dsf.M_k,
            dsf.R_rev,
            dsf.U_star,
            dsf.C_k,
            dsf.P_k,
            dsf.B_k,
            dsf.S_UF,
        ):
            if abs(value) > 0.5:
                constraints += 1
        return self.n_start - constraints

    def captured(self, dsf):
        """Return whether the field has entered the existing capture basin."""
        return self.n_eff(dsf) < self.capture_threshold

    def structural_lock(self, dsf):
        """Return whether the existing SL-1 relation is present."""
        return (
            self.captured(dsf)
            and dsf.B_k > 0.5
            and dsf.U_star < 0.4
            and dsf.S_UF > 0.4
        )
