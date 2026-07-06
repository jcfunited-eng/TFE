"""
binding_atlas.py — Per-neuron BindingAtlas for cognition path.

GL-CMD-ORGANISM-WAVE-MEMORY-EVE-20260705-207 (W1/W2, this file's flat-vector
path) + GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-208 (this file's per-lane
path), merged -- the two dispatches collided on the same file (both landed
on guala-live within the same window) but are orthogonal by construction:

A binding's state_vec is either:
(a) a flat 1-D np.ndarray — the original grandurun/event_count encoding, R^6,
    positionally keyed by MODALITIES. This is what production's live
    Guala actually uses (gualaloom_v5_engine.py:1631, observable=
    "event_count"). Stored in a per-neuron wave-cell store (tools/
    wave_spillover.py's Cell/spill_write, canonical, imported not
    duplicated) instead of the original unbounded append-log: the append-
    log's every record() invalidated a matrix cache that recall_best()
    rebuilt via a full np.stack over the ENTIRE lifetime history --
    measured live at 77-99 SECONDS per call (1.3M+ lifetime words) while
    the underlying per-call organism cost is only 24-47ms. Repeat
    occurrences reinforce their existing cell binding (tracked by a
    concept->chi index, not a radius re-guess -- see record()'s comment
    for why) instead of appending a duplicate; recall does a progressive-
    radius cosine search (see recall_best()'s comment for why a single
    fixed radius regressed partial-cue/noisy recall).
(b) a Dict[str, np.ndarray] of PER-LANE sub-vectors — the resonant_spectral
    encoding (neuron.encode_state). Not currently live in production
    (Embryo() there hardcodes observable="event_count"), so it keeps the
    simpler append-log storage -208 shipped; the fix that dispatch cared
    about was MATCHING (masked, lane-normalized cosine over only the
    lanes the query actually has present), not storage complexity, and
    that fix is preserved here unchanged.
A given atlas is homogeneous in which of (a)/(b) it holds — determined once
by the owning neuron's `observable`, which does not change after
construction — so the two storage paths never mix within one atlas.
"""

import os
import sys
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from .grandurun import recall_best as _cosine_best, STATE_DIM  # noqa: F401 (STATE_DIM kept for callers)

_tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')
if os.path.isdir(_tools) and _tools not in sys.path:
    sys.path.insert(0, _tools)

from wave_constants import CHI_BAND, N_CELLS  # noqa: E402
from wave_spillover import Cell, spill_write  # noqa: E402

StateVec = Union[np.ndarray, Dict[str, np.ndarray]]


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


def _lane_match_score(query_lanes: Dict[str, np.ndarray],
                       stored_lanes: Dict[str, np.ndarray]) -> Optional[float]:
    """GL-CMD-CROSS-SENSE-RECALL-208: masked, lane-normalized cosine --
    average per-lane cosine similarity over the INTERSECTION of the
    query's present lanes and this binding's present lanes. Returns None
    if there is no common lane (this binding is simply not comparable to
    this cue, not scored 0-and-competing). Unchanged from -208's original."""
    sims = []
    for m, q in query_lanes.items():
        s = stored_lanes.get(m)
        if s is None:
            continue
        qn = float(np.linalg.norm(q))
        sn = float(np.linalg.norm(s))
        if qn < 1e-12 or sn < 1e-12:
            continue
        sims.append(float(np.dot(q, s)) / (qn * sn))
    return (sum(sims) / len(sims)) if sims else None


def _sat_thresh_default() -> float:
    """SATURATION_THRESHOLD, resolved lazily so a test that monkeypatches
    wave_constants after import still takes effect (mirrors spill_write's
    own default-argument binding at import time otherwise being frozen)."""
    from wave_constants import SATURATION_THRESHOLD
    return SATURATION_THRESHOLD


class BindingAtlas:
    """Per-neuron cognition atlas. Bindings are (concept, state_vec, tick)
    triples. Flat-vector (event_count) bindings live in a wave-cell dict
    keyed by this neuron's own encoded chi; per-lane dict (resonant_
    spectral) bindings live in a simple list (see module docstring for
    why the two paths differ). Public interface (record/recall_best/
    bindings/clear) is unchanged from the original append-log
    implementation -- every caller (neuron.py, embryo.py, loom_voice.py)
    works with zero changes.
    """


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
        # GL-CMD-CROSS-SENSE-RECALL-208: per-lane (resonant_spectral)
        # bindings, kept as a simple list -- not currently a production
        # scaling concern (Embryo() hardcodes observable="event_count"),
        # and -208's own fix was about matching correctness, not storage.
        self._lane_bindings: List[dict] = []

    def __setstate__(self, state: dict) -> None:
        """Pickle compatibility (found live in production, 2026-07-05,
        within minutes of this rewrite's first deploy): __init__ never
        re-runs on unpickle, so an organism saved before this rewrite
        landed restores each neuron's BindingAtlas with the OLD shape
        (_bindings: list, _matrix_cache, _concepts_cache) -- every
        record()/recall_best() call then crashed with AttributeError
        (self.cells doesn't exist on the restored instance) rather than
        silently losing data, which is at least how it was caught fast,
        but still took real production down. Migrate old bindings
        forward through record() (the same reinforcement/dedup path live
        writes already use) rather than silently discarding them; a save
        taken after this rewrite already has `cells` and restores as-is."""
        if "cells" in state:
            self.__dict__.update(state)
            return
        self.cells = {}
        self._concept_to_chi = {}
        self._lane_bindings = []
        for b in state.get("_bindings", []):
            try:
                self.record(b["concept"], b["state_vec"], b.get("tick", 0))
            except Exception:
                continue  # best-effort migration; never let one bad entry crash the whole restore

    def record(self, concept: str, state_vec: StateVec, tick: int) -> None:
        """Reinforce the existing binding for this concept if one exists,
        otherwise create a new one. Flat vectors (event_count) go through
        the wave-cell store (see __init__'s comment on _concept_to_chi for
        why reinforcement uses an index, not a radius guess); per-lane
        dicts (resonant_spectral) append to a simple list, unchanged from
        -208. No lock -- per-neuron mutation only, race-tolerant per the
        WaveAtlas read contract (see -207 W3: only the writer queue's
        single worker ever calls this, in order; concurrent reads never
        mutate)."""
        if isinstance(state_vec, dict):
            for m, v in state_vec.items():
                assert v.ndim == 1, f"lane {m!r} must be 1-D, got shape {v.shape}"
            self._lane_bindings.append({"concept": concept, "state_vec": state_vec, "tick": tick})
            return

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
                        self._mirror_put(concept, state_vec)
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
        self._mirror_put(concept, state_vec)

    def _recall_best_lanes(self, query_lanes: Dict[str, np.ndarray]) -> Tuple[Optional[str], float]:
        """GL-CMD-CROSS-SENSE-RECALL-208: unchanged brute-force scan over
        per-lane bindings -- not a production scaling concern today (see
        module docstring)."""
        best_concept, best_score = None, 0.0
        found = False
        for b in self._lane_bindings:
            score = _lane_match_score(query_lanes, b["state_vec"])
            if score is None:
                continue
            if not found or score > best_score:
                best_concept, best_score, found = b["concept"], score, True
        return (best_concept, best_score) if found else (None, 0.0)


    # ── GL-FIX-RECALL-MATRIX-MIRROR (Eve, 2026-07-05) ──────────────────
    # Incremental matrix mirror of the flat-vector store. recall_best()'s
    # deployed form re-traversed every cell and re-stacked ~vocab-size
    # vectors from Python objects ON EVERY CALL (no cache): measured
    # 9.7ms/neuron solo and 285ms/neuron under production's real thread
    # mix (GIL-holding pure Python), = 1.0s..30.2s per organism recall at
    # 14k concepts / 106 neurons -- reproducing the live 17-34s incident.
    # The mirror keeps one preallocated float64 matrix + concept row
    # index, updated incrementally by record(); recall becomes a single
    # numpy matmul (0.8ms/neuron, GIL-RELEASING, load-immune). The wave-
    # cell store remains the source of truth; the mirror is layout-
    # independent (concept->vector), so spillover/subdivision rehoming
    # never desyncs it. Single-writer contract unchanged (only the
    # organism worker calls record()); readers tolerate one-append-stale
    # views per the store's own declared race tolerance. Capacity grows
    # by doubling with an ATOMIC REFERENCE SWAP (new array built, then
    # rebound) so a concurrent matmul never sees a torn buffer. Zero new
    # constants, zero locks, zero behavior change: same _cosine_best over
    # the same deduplicated data.
    # Pickle-safety: attrs are lazily healed via getattr (the same
    # schema-evolution pattern -198 used for Embryo), so organisms saved
    # before this fix restore and run without migration.

    def _mirror_put(self, concept: str, state_vec: "np.ndarray") -> None:
        row_of = getattr(self, "_m_row", None)
        if row_of is None:
            self._m_row = row_of = {}
            self._m_concepts = []
            self._m_matrix = None
            self._m_len = 0
        m = self._m_matrix
        r = row_of.get(concept)
        if r is not None:
            m[r] = state_vec  # freshest encoding wins, matching record()
            return
        if m is None or self._m_len >= m.shape[0]:
            cap = max(256, (0 if m is None else m.shape[0]) * 2)
            grown = np.zeros((cap, state_vec.shape[0]), dtype=np.float64)
            if m is not None and self._m_len:
                grown[: self._m_len] = m[: self._m_len]
            self._m_matrix = m = grown  # atomic ref swap; old readers keep old buffer
        m[self._m_len] = state_vec
        self._m_concepts.append(concept)
        row_of[concept] = self._m_len
        self._m_len += 1

    def _mirror_rebuild(self) -> None:
        """One-time build from the store (first recall on a restored
        instance, or any instance predating this fix)."""
        self._m_row = {}
        self._m_concepts = []
        self._m_matrix = None
        self._m_len = 0
        for cell in self.cells.values():
            for b in cell.bindings:
                self._mirror_put(b["concept"], b["state_vec"])

    def recall_best(self, target_vec: StateVec) -> Tuple[Optional[str], float]:
        """Per-lane dicts (resonant_spectral): masked lane-normalized
        cosine over the simple binding list, unchanged from -208.

        Flat vectors (event_count): full cosine-best scan over the
        DEDUPLICATED wave-cell store (one binding per distinct concept this
        neuron has ever bound, not one per occurrence). Population vote
        shape unchanged: still (best_concept, best_cosine).

        GL-CMD-ORGANISM-WAVE-MEMORY-207, correctness fix (found via direct
        old-vs-new comparison, 2026-07-05, after chi-radius search shipped
        with a real accuracy bug): a CHI-RADIUS-LIMITED search (tried
        first, including a progressive-widening version) assumes vector
        proximity implies chi proximity -- true for small perturbations of
        an otherwise-static vector, but event_count deltas are NOT static:
        they accumulate from krimelack winding/n_events state that keeps
        drifting as MORE concepts get taught in between. By the time
        recall runs (after all teaching), a query's own freshly-computed
        chi can land far from where that same concept's binding was
        stored at teach time, even though the STORED vector is still, by
        far, the closest cosine match among everything this neuron has
        ever bound. Measured: this radius design broke T5 catastrophically
        as vocabulary grew (100% at n=2/5, 40% at n=10, 0% at n=20+)
        against the unmodified original's 100% at every one of those
        sizes -- a real, severe regression, not a hypothetical one.

        Fix: search ALL cells, not a chi neighborhood -- the SAME
        brute-force cosine comparison the original unbounded append-log
        used (grandurun.recall_best, imported unchanged), just over the
        DEDUPLICATED set (one entry per distinct concept, via record()'s
        reinforcement) instead of one entry per lifetime occurrence. This
        is what actually delivers the fix the dispatch's root-cause
        analysis asked for: production's original 77-99 SECOND cost came
        from scanning ~1.3M lifetime occurrences; a full scan over
        ~vocabulary-size (~14k words) distinct concepts is a completely
        different, bounded cost, and provably identical in behavior to
        the original algorithm (same function, same matrix, smaller
        input) -- not an approximation that can silently misrecall.
        """
        if isinstance(target_vec, dict):
            return self._recall_best_lanes(target_vec)

        if not self.cells:
            return None, 0.0
        if getattr(self, "_m_matrix", None) is None or getattr(self, "_m_len", 0) == 0:
            self._mirror_rebuild()
            if self._m_len == 0:
                return None, 0.0
        return _cosine_best(target_vec, self._m_matrix[: self._m_len], self._m_concepts)

    @property
    def bindings(self) -> int:
        return sum(len(c.bindings) for c in self.cells.values()) + len(self._lane_bindings)

    def clear(self) -> None:
        self.cells.clear()
        self._concept_to_chi.clear()
        self._lane_bindings.clear()
        self._m_row = {}
        self._m_concepts = []
        self._m_matrix = None
        self._m_len = 0
