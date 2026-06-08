"""
GL-PRM-PLASTICITY-WC-20260608-01

Gate-to-section feedback: mode_strength lives ON the section, not the gate.
Section.arcs() returns effective arcs (raw * (1 + strength)). This means
LTP from the NMDA gate propagates into Section.commit_check / commit /
cascade dynamics — not just into post-hoc reads.

This is the actin-cytoskeleton remodeling primitive from the spec: when
the NMDA gate opens and calcium floods, the spine swells. In substrate
terms, mode_strength permanently changes the mode's apparent magnitude.
"""

import numpy as np
import types


def install_plasticity(section, initial_strength=0.0):
    """Add mode_strength list and patch arcs() to use it."""
    section.mode_strength = [initial_strength] * len(section.mode_bank)

    def plastic_arcs(self):
        if not self.mode_bank:
            return np.array([])
        # Keep strength array sized to mode bank
        while len(self.mode_strength) < len(self.mode_bank):
            self.mode_strength.append(0.0)
        raw = np.array([np.abs(np.vdot(m, self.psi)) ** 2 for m in self.mode_bank])
        multiplier = np.array([1.0 + self.mode_strength[i] for i in range(len(raw))])
        return raw * multiplier

    section.arcs = types.MethodType(plastic_arcs, section)
    return section


def decay_plasticity(section, decay=0.998):
    """Per-tick decay of mode strength (fast-LTP decay; without
       reinforcement, the spine shrinks back)."""
    if not hasattr(section, "mode_strength"):
        return
    for i in range(len(section.mode_strength)):
        section.mode_strength[i] *= decay


def reinforce_mode(section, mode_id, boost=0.05, ceiling=2.0):
    """Apply LTP boost to a specific mode. Called by the NMDA gate when
       coincidence fires."""
    if not hasattr(section, "mode_strength"):
        return
    while len(section.mode_strength) <= mode_id:
        section.mode_strength.append(0.0)
    section.mode_strength[mode_id] = min(ceiling,
                                          section.mode_strength[mode_id] + boost)
