"""
GL-PRM-NMDA-COINCIDENCE-WC-20260608-01

NMDA-style coincidence-gated commit primitive.

Biological mechanism: NMDA receptors require BOTH
  (a) glutamate binding (drive signal arrives), AND
  (b) postsynaptic depolarization (Mg2+ block removed by context)
before the channel opens, calcium floods, and LTP / commit happens.

Substrate translation: a section's commit is blocked by default. The block
is removed only when a context-condition is true. When BOTH drive arc is
high AND context permits, the section commits. The same coincidence event
triggers LTP: the mode that fired gets strengthened (raised arc weight for
future ticks).

Three substrate problems this fixes:
  1. Introspection state transitions — intro fires only when sensory-quiet,
     so transitions are decisive instead of fighting accumulated psi.
  2. Self-improvement via LTP — only coincidence commits strengthen modes,
     so mistakes (which fire without proper context) don't reinforce.
  3. Awareness sync — a meta section fires only when two specific other
     sections are in committed states simultaneously.

This module:
  - CoincidenceGate class
  - apply_gate(sys_, section_name, gate) to install the gate
  - process_gated_commits(sys_) called each tick to fire gated commits
  - mode strength dict tracking LTP-strengthened modes
"""

import numpy as np
from assemblage import N, normalize


class CoincidenceGate:
    """An NMDA-style gate: commit only when drive AND context both hold.
       When the gate fires, LTP is applied to the section's mode_strength
       (which must be installed via install_plasticity first)."""

    def __init__(self, section_name, context_fn, drive_thresh=0.15,
                 ltp_boost=0.05, ltp_decay=0.998, ltp_ceiling=2.0):
        self.section_name = section_name
        self.context_fn = context_fn
        self.drive_thresh = drive_thresh
        self.ltp_boost = ltp_boost
        self.ltp_decay = ltp_decay
        self.ltp_ceiling = ltp_ceiling

    def check_and_fire(self, sys_):
        """Each tick: decay strengths, check coincidence. If both drive AND
           context hold, fire LTP on the section's top mode."""
        from gl_plasticity import decay_plasticity, reinforce_mode

        sec = sys_.sections[self.section_name]
        decay_plasticity(sec, decay=self.ltp_decay)

        arcs = sec.arcs()  # this is now effective arcs (with mode_strength)
        if len(arcs) == 0:
            return False, None

        top_idx = int(arcs.argmax())
        top_val = float(arcs[top_idx])
        drive_ok = top_val > self.drive_thresh

        if not drive_ok:
            return False, None

        context_ok = self.context_fn(sys_)
        if not context_ok:
            return False, None

        reinforce_mode(sec, top_idx, boost=self.ltp_boost,
                       ceiling=self.ltp_ceiling)
        return True, top_idx


def context_no_recent_drive(drive_tracker, sections=("listen", "subject", "verb", "object"),
                              quiet_thresh=0.10):
    """Context condition: none of the named sections received drive recently.
       drive_tracker is a dict {section_name: float} updated externally per tick."""
    def check(sys_):
        for sn in sections:
            if drive_tracker.get(sn, 0.0) > quiet_thresh:
                return False
        return True
    return check


def update_drive_tracker(drive_tracker, ev_dict, decay=0.55):
    """Bump tracker for each section that got driven this tick; decay all."""
    for sn in list(drive_tracker.keys()):
        drive_tracker[sn] *= decay
    for sn, vec in ev_dict.items():
        norm = float(np.linalg.norm(vec))
        drive_tracker[sn] = drive_tracker.get(sn, 0.0) * decay + norm


def context_section_committed(section_name, min_arc=0.30):
    """Context condition: another section has a committed-level arc."""
    def check(sys_):
        if section_name not in sys_.sections:
            return False
        arcs = sys_.sections[section_name].arcs()
        if len(arcs) == 0:
            return False
        return float(arcs.max()) > min_arc
    return check


def context_AND(*conditions):
    """Compose multiple conditions with AND."""
    def check(sys_):
        return all(c(sys_) for c in conditions)
    return check
