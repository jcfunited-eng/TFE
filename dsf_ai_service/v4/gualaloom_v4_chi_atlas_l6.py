"""
chi_atlas_l6.py — Chi Atlas (binding) + L6-TCL (dimensional grinder)

Spec L6-TCL: n_eff = n_start - Σ rank(C_i). When n_eff < n_start/e,
capture basin → SL-1 (structural lock) → emit.

Chi atlas: binds commits across krimelacks by chi-state co-occurrence
within band δ. Encoding = the cross-modal co-firing recorded here.
"""
import math
from collections import defaultdict


CHI_BAND = 2  # soft band width (δ)
N_START = 8   # initial dimensionality (matches DSF dim)

# 2026-07-08 pruning fix: entries[key] was an unbounded, never-pruned
# list -- every record() call appends across 2*CHI_BAND+1=5 keys with no
# cap anywhere in this class, confirmed live against a real running
# neuron: 80,355 total accumulated records in one neuron's chi_atlas
# (single chi-keys past 6,000 entries each), still growing. match_score()
# below only sums per-entry contributions and clamps the result to 1.0 --
# it saturates well before a key's list reaches even a few dozen
# entries, so recent history is exactly as informative as unbounded
# history for everything this class is actually read for
# (match_score/cross_modal_bindings/query_associations all just scan
# whatever's present, none need the full lifetime record). Bounded to
# 16, matching PSI_DIM's existing role elsewhere in this codebase as the
# "how much recent structure a neuron tracks" scale (neuron.py's
# SpikeBuffer.DEPTH = PSI_DIM = 16, the same append-then-evict-oldest
# pattern reused here) -- duplicated as a local constant rather than
# imported to avoid a circular import (neuron.py imports FROM this
# module already).
MAX_ENTRIES_PER_CHI_KEY = 16


class ChiAtlas:
    """Binds events across modal + word + role krimelacks within chi-band δ."""

    def __init__(self, band=CHI_BAND):
        self.band = band
        # chi_value -> list of {section, motif_id, chi, tick}
        self.entries = defaultdict(list)
        self.tick = 0

    def record(self, section_name, motif_id, chi_value, tick=None):
        """Record a commit at chi_value. Replicate across band for soft binding.

        Each key's list is capped at MAX_ENTRIES_PER_CHI_KEY, oldest
        evicted first -- same convention as neuron.py's SpikeBuffer."""
        if tick is None:
            tick = self.tick
        self.tick += 1
        for d in range(-self.band, self.band + 1):
            bucket = self.entries[chi_value + d]
            bucket.append({
                "section": section_name,
                "motif": motif_id,
                "chi": chi_value,
                "tick": tick,
            })
            if len(bucket) > MAX_ENTRIES_PER_CHI_KEY:
                del bucket[0]

    def trim_all(self, max_len=MAX_ENTRIES_PER_CHI_KEY):
        """One-time reclaim for entries accumulated before this cap
        existed (an already-restored organism's chi_atlas has no way to
        have been capped on append if it predates this fix) -- keeps
        only the most recent max_len records per key. Safe to call
        repeatedly (a no-op once every key is already within bound)."""
        for key, bucket in self.entries.items():
            if len(bucket) > max_len:
                del bucket[:len(bucket) - max_len]

    def cross_modal_bindings(self):
        """Atlas entries where >= 2 distinct sections committed in same band."""
        out = []
        for k, entries in self.entries.items():
            secs = set(e["section"] for e in entries)
            if len(secs) >= 2:
                out.append((k, secs, entries))
        return out

    def match_score(self, chi_value, section_name):
        """Familiarity feedback hook: how much existing structure is in this band?
        Returns score ∈ [0,1]. Spec Ch.21: this raises the dead zone."""
        score = 0.0
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["section"] != section_name:
                    score += 0.3  # cross-modal evidence weighted heavier
                else:
                    score += 0.1
        return min(score, 1.0)

    def query_associations(self, section_name, chi_value):
        """For introspection / recall: what other sections bound at this chi?"""
        associated = defaultdict(list)
        for d in range(-self.band, self.band + 1):
            for e in self.entries.get(chi_value + d, []):
                if e["section"] != section_name:
                    associated[e["section"]].append(e["motif"])
        return dict(associated)


class L6_TCL:
    """L6 Topological Constraint Layer / Dimensional Grinder.

    As constraints from the kernel restrict the coupling matrix, effective
    dimensionality reduces: n_eff = n_start - Σ rank(C_i).
    When n_eff < n_start/e ≈ n_start * 0.368, fabric enters capture basin
    → SL-1 (Structural Lock Level 1) → emit.
    """

    def __init__(self, n_start=N_START):
        self.n_start = n_start
        self.capture_threshold = n_start / math.e

    def n_eff(self, dsf):
        """Effective dimension given current DSF. Each high-magnitude DSF
        component is a constraint that reduces dimensionality."""
        constraints = 0
        # Each DSF component above 0.5 magnitude is a rank-1 constraint
        for v in (dsf.D_k, dsf.M_k, dsf.R_rev, dsf.U_star,
                  dsf.C_k, dsf.P_k, dsf.B_k, dsf.S_UF):
            if abs(v) > 0.5:
                constraints += 1
        return self.n_start - constraints

    def captured(self, dsf):
        """Return True if capture basin reached → emit ready."""
        return self.n_eff(dsf) < self.capture_threshold

    def structural_lock(self, dsf):
        """SL-1 fires when captured AND conviction is high AND freedom is low."""
        return (self.captured(dsf) and dsf.B_k > 0.5 and dsf.U_star < 0.4
                and dsf.S_UF > 0.4)
