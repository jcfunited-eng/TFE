"""
binding_atlas.py — Per-neuron BindingAtlas for cognition path.

GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207 (W1/W2): replaces the original
unbounded append-log (one dict per word occurrence EVER experienced by this
neuron; every record() invalidated a matrix cache that recall_best() then
rebuilt via a full np.stack over the ENTIRE history) with a per-neuron
wave-cell store on the canonical -59 physics (tools/wave_spillover.py's
Cell/spill_write -- imported, never duplicated; tools/wave_constants.py
constants only, no new ones).

Root cause this replaces (measured live, 2026-07-05): with population-vote
architecture cost O(population) already known-and-accepted (-179), the
UNBOUNDED PER-NEURON HISTORY was the actual multiplier -- 1.3M+ lifetime
words meant some neurons' _bindings lists held comparable order-of-magnitude
entries, and any record() (i.e. every single word) invalidated the cache
so the NEXT recall_best() paid a full-history np.stack + brute-force cosine
scan. Two production converse_timing samples showed recall_ms/read_ms of
77-99 SECONDS EACH while the underlying per-call organism cost (verified via
cProfile at a realistic population=120) was only 24-47ms -- the gap was the
unbounded-history rebuild, not per-call compute.

Fix: same "reinforce, don't append" dedup pattern dsf_ai_service/v4/
wave_atlas.py's WaveAtlas.record() already uses at the shell level. A
repeat occurrence of a concept updates the EXISTING cell binding's strength
in place; genuinely new concepts spill-write into a bounded neighborhood.
Growth of the store is bounded by the physics (saturation → spillover →
subdivision), not a cap, and not by how many times she has ever experienced
anything. Recall reads only cells within a bounded chi radius of the query's
own encoding (O(radius), the WaveAtlas contract), then does the SAME cosine
best-match math as before (grandurun.recall_best, imported unchanged) over
that small local set instead of the full lifetime history.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

from .grandurun import recall_best as _cosine_best, STATE_DIM  # noqa: F401 (STATE_DIM kept for callers)

_tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')
if os.path.isdir(_tools) and _tools not in sys.path:
    sys.path.insert(0, _tools)

from wave_constants import CHI_BAND, N_CELLS  # noqa: E402
from wave_spillover import Cell, spill_write  # noqa: E402


_state_chi_projections: Dict[int, np.ndarray] = {}


def _state_chi_projection(dim: int) -> np.ndarray:
    """Fixed, deterministic projection basis (one per vector dimension seen).
    Not a tuned threshold -- an arbitrary but constant coordinate system,
    the same role tools/resonant_chi.py's neuron_projection() plays for the
    resonant_spectral observable. Cached so every call for a given dim
    reuses the identical basis (required for locality to mean anything)."""
    if dim not in _state_chi_projections:
        rng = np.random.default_rng(20260630)  # -59 ratification date; fixed, not tuned
        _state_chi_projections[dim] = rng.standard_normal(dim)
    return _state_chi_projections[dim]


def _state_chi(state_vec: np.ndarray) -> int:
    """Locality-preserving chi address from a neuron's OWN encoded state
    vector: project onto a fixed random basis, floor to an integer, wrap
    into the cell space. Similar vectors (a noisy re-query of the same
    concept) project to the same or adjacent integer -- well within
    CHI_BAND's spillover radius -- so recall_best's radius read actually
    finds them. A cryptographic hash (md5, tried first) was measured to
    NOT have this property by construction (the avalanche effect is the
    opposite of locality): exact-match recall passed, but a noisy query
    (+0.1 per dimension) landed at a completely unrelated chi and found
    nothing (T1/T2 regression, caught before this shipped).

    Different neurons still naturally place the SAME concept at DIFFERENT
    chi, because their state_vec differs (ring-position/kappa attenuation
    is already baked into _unwrapped_deltas before this ever sees the
    vector) -- the projection basis is identical across neurons, but its
    input isn't, so the diversity -59's dispatch requires (the mechanism
    that broke the 6/22 population degeneracy) is preserved. Only N_CELLS
    (existing -59 constant) gates the final range; the projection itself
    introduces no tuned threshold, just a fixed coordinate system.
    """
    proj = _state_chi_projection(state_vec.shape[0])
    scalar = float(np.dot(state_vec, proj))
    return int(np.floor(scalar)) % N_CELLS


class BindingAtlas:
    """Per-neuron cognition atlas. Bindings are (concept, state_vec, tick)
    triples, stored in a wave-cell dict keyed by this neuron's own encoded
    chi. Public interface (record/recall_best/bindings/clear) is unchanged
    from the prior append-log implementation -- every caller (neuron.py,
    embryo.py, loom_voice.py) works with zero changes.
    """

    # Progressive recall widening: try the cheap CHI_BAND radius first (the
    # common case -- clean or lightly-noisy queries). Only when that comes
    # back empty do we pay for a wider look, in a small number of doubling
    # steps, capped well below N_CELLS -- still O(radius), never
    # O(total_history). See recall_best's docstring for why this exists.
    _RECALL_WIDEN_STEPS = 4  # CHI_BAND, then x2, x4, x8 -- four tries, then honest empty

    def __init__(self):
        self.cells: Dict[int, Cell] = {}
        # GL-CMD-ORGANISM-WAVE-MEMORY-207 bugfix (independent review,
        # 2026-07-05): record()'s dedup used to re-derive chi_target from
        # the CURRENT state_vec and search only ±CHI_BAND around it. But
        # spill_write can chain up to 512 hops once a neighborhood
        # saturates, so an existing binding can sit far outside that
        # radius -- the dedup scan missed it and silently wrote a
        # DUPLICATE, exactly the failure mode this whole rewrite exists to
        # eliminate (reproduced: same concept, same vector, recorded
        # twice, ended up as two bindings 45 and 44 cells from chi_target).
        # This index remembers where each concept ACTUALLY landed, so
        # reinforcement goes straight there -- O(1), not a radius guess.
        self._concept_to_chi: Dict[str, int] = {}

    def record(self, concept: str, state_vec: np.ndarray, tick: int) -> None:
        """Reinforce the existing binding for this concept if one exists
        (found via the concept->chi index, not a radius guess -- see
        __init__'s comment); otherwise spill-write a new one. No lock --
        per-neuron dict mutation only, race-tolerant per the WaveAtlas read
        contract (see W3: only the writer queue's single worker ever calls
        this, in order; concurrent reads never mutate)."""
        assert state_vec.ndim == 1, f"state_vec must be 1-D, got shape {state_vec.shape}"
        strength = 1.0

        known_chi = self._concept_to_chi.get(concept)
        if known_chi is not None:
            cell = self.cells.get(known_chi)
            if cell is not None:
                for b in cell.bindings:
                    if b.get("concept") == concept:
                        b["strength"] = b.get("strength", 0.0) + strength
                        b["state_vec"] = state_vec  # freshest encoding wins
                        b["tick"] = tick
                        cell.aggregate_strength += strength
                        cell.last_tick = tick
                        cell.saturated = cell.aggregate_strength > _sat_thresh_default()
                        return
            # Index pointed somewhere stale (shouldn't happen in practice,
            # but honest fall-through rather than trusting a dangling
            # pointer): fall through to a fresh spill_write below.

        chi_target = _state_chi(state_vec)
        binding = {"concept": concept, "state_vec": state_vec, "tick": tick, "strength": strength}
        final_chi, _hops = spill_write(self.cells, chi_target, None, binding)
        self._concept_to_chi[concept] = final_chi
        cell = self.cells.get(final_chi)
        if cell is not None:
            cell.last_tick = tick

    def recall_best(self, target_vec: np.ndarray) -> Tuple[Optional[str], float]:
        """Radius read around the query's own encoded chi (O(radius), no
        lock -- WaveAtlas contract), then best cosine match within that
        neighborhood only. Population vote shape unchanged: still
        (best_concept, best_cosine).

        GL-CMD-ORGANISM-WAVE-MEMORY-207 bugfix (independent review,
        2026-07-05): a SINGLE fixed CHI_BAND radius measurably regressed
        partial-cue and noisy recall (T7 2.0%->0.0%, T8 30/20/12%->
        24/12/4%) -- a single linear projection only preserves locality
        for small, near-isotropic perturbations; missing modalities and
        real sensory noise are larger, structured ones that can land just
        outside (or well outside) CHI_BAND. Progressive widening tries the
        cheap radius first (the common case stays fast) and only pays for
        a wider look on the rarer miss -- still bounded, never the
        O(total_history) scan this whole rewrite exists to eliminate.
        """
        target_chi = _state_chi(target_vec)
        radius = CHI_BAND
        for _step in range(self._RECALL_WIDEN_STEPS):
            local: List[dict] = []
            for d in range(-radius, radius + 1):
                cell = self.cells.get((target_chi + d) % N_CELLS)
                if cell is not None:
                    local.extend(cell.bindings)
            if local:
                matrix = np.stack([b["state_vec"] for b in local])
                concepts = [b["concept"] for b in local]
                return _cosine_best(target_vec, matrix, concepts)
            radius *= 2
        return None, 0.0

    @property
    def bindings(self) -> int:
        return sum(len(c.bindings) for c in self.cells.values())

    def clear(self) -> None:
        self.cells.clear()
        self._concept_to_chi.clear()


def _sat_thresh_default() -> float:
    """SATURATION_THRESHOLD, resolved lazily so a test that monkeypatches
    wave_constants after import still takes effect (mirrors spill_write's
    own default-argument binding at import time otherwise being frozen)."""
    from wave_constants import SATURATION_THRESHOLD
    return SATURATION_THRESHOLD
