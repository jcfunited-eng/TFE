"""
binding_atlas.py — Per-neuron BindingAtlas for cognition path.

Separate from existing ChiAtlas. Stores 7-dim state vectors with concept labels.
Vectorized recall via grandurun.recall_best.
"""

import numpy as np
from typing import List, Tuple, Optional

from .grandurun import recall_best, STATE_DIM


class BindingAtlas:
    """Per-neuron cognition atlas. Bindings are (concept, state_vec, tick) triples.

    Atlas matrix is built lazily and cached. Cache invalidates on any record() call.
    """

    def __init__(self):
        self._bindings: List[dict] = []
        self._matrix_cache: Optional[np.ndarray] = None
        self._concepts_cache: Optional[List[str]] = None

    def record(self, concept: str, state_vec: np.ndarray, tick: int) -> None:
        """Append a binding. Invalidates the matrix cache. Stores whatever 1-D
        encoding the neuron produces (grandurun R⁶, or resonant ternary chi)."""
        assert state_vec.ndim == 1, f"state_vec must be 1-D, got shape {state_vec.shape}"
        self._bindings.append({"concept": concept, "state_vec": state_vec, "tick": tick})
        self._matrix_cache = None
        self._concepts_cache = None

    def _ensure_cache(self):
        if self._matrix_cache is None and self._bindings:
            self._matrix_cache = np.stack([b["state_vec"] for b in self._bindings])
            self._concepts_cache = [b["concept"] for b in self._bindings]

    def recall_best(self, target_vec: np.ndarray) -> Tuple[Optional[str], float]:
        """Find binding with maximum |<target, binding>|."""
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
