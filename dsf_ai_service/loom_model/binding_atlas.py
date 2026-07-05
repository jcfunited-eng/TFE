"""
binding_atlas.py — Per-neuron BindingAtlas for cognition path.

Separate from existing ChiAtlas. Stores 7-dim state vectors with concept labels.
Vectorized recall via grandurun.recall_best.

GL-CMD-CROSS-SENSE-RECALL-EVE-20260705-207: a binding's state_vec is either
(a) a flat 1-D np.ndarray — the original grandurun/event_count encoding,
    R^6, positionally keyed by MODALITIES. Unchanged, still matched via
    grandurun.recall_best (whole-vector cosine).
(b) a Dict[str, np.ndarray] of PER-LANE sub-vectors — the resonant_spectral
    encoding (neuron.encode_state). Matched via masked, lane-normalized
    inner product over only the lanes the QUERY actually has present —
    the honest-absence convention -191 set at teach time, now applied at
    match time too. This is what makes partial-cue recall possible: a
    lane's shape never depends on which other lanes are present, so a
    1-lane query is directly comparable to the matching lane of a
    6-lane teach-time binding.
A given atlas is homogeneous in which of (a)/(b) it holds — determined
once by the owning neuron's `observable`, which does not change after
construction — so the two never mix within one atlas.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Union

from .grandurun import recall_best, STATE_DIM

StateVec = Union[np.ndarray, Dict[str, np.ndarray]]


def _lane_match_score(query_lanes: Dict[str, np.ndarray],
                       stored_lanes: Dict[str, np.ndarray]) -> Optional[float]:
    """Masked, lane-normalized cosine: average per-lane cosine similarity
    over the INTERSECTION of the query's present lanes and this binding's
    present lanes. Returns None if there is no common lane (this binding
    is simply not comparable to this cue, not scored 0-and-competing)."""
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


class BindingAtlas:
    """Per-neuron cognition atlas. Bindings are (concept, state_vec, tick) triples.

    Atlas matrix is built lazily and cached. Cache invalidates on any record() call.
    """

    def __init__(self):
        self._bindings: List[dict] = []
        self._matrix_cache: Optional[np.ndarray] = None
        self._concepts_cache: Optional[List[str]] = None

    def record(self, concept: str, state_vec: StateVec, tick: int) -> None:
        """Append a binding. Invalidates the matrix cache. Stores whatever
        encoding the neuron produces: a flat 1-D vector (grandurun R⁶) or
        a dict of per-lane 1-D sub-vectors (resonant ternary chi)."""
        if isinstance(state_vec, dict):
            for m, v in state_vec.items():
                assert v.ndim == 1, f"lane {m!r} must be 1-D, got shape {v.shape}"
        else:
            assert state_vec.ndim == 1, f"state_vec must be 1-D, got shape {state_vec.shape}"
        self._bindings.append({"concept": concept, "state_vec": state_vec, "tick": tick})
        self._matrix_cache = None
        self._concepts_cache = None

    def _ensure_cache(self):
        if self._matrix_cache is None and self._bindings:
            self._matrix_cache = np.stack([b["state_vec"] for b in self._bindings])
            self._concepts_cache = [b["concept"] for b in self._bindings]

    def _recall_best_lanes(self, query_lanes: Dict[str, np.ndarray]) -> Tuple[Optional[str], float]:
        best_concept, best_score = None, 0.0
        found = False
        for b in self._bindings:
            score = _lane_match_score(query_lanes, b["state_vec"])
            if score is None:
                continue
            if not found or score > best_score:
                best_concept, best_score, found = b["concept"], score, True
        return (best_concept, best_score) if found else (None, 0.0)

    def recall_best(self, target_vec: StateVec) -> Tuple[Optional[str], float]:
        """Find binding with maximum |<target, binding>| (flat vectors) or
        maximum masked lane-normalized cosine (per-lane dicts)."""
        if isinstance(target_vec, dict):
            return self._recall_best_lanes(target_vec)
        self._ensure_cache()
        if self._matrix_cache is None:
            return None, 0.0
        return recall_best(target_vec, self._matrix_cache, self._concepts_cache)

    @property
    def bindings(self) -> int:
        return len(self._bindings)

    def clear(self) -> None:
        self._bindings.clear()
        self._matrix_cache = None
        self._concepts_cache = None
