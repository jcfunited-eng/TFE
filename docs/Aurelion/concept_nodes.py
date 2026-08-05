# concept_nodes.py
# Online concept abstraction: tokens aggregate into concept nodes via resonance.

from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np

# Same modal contract as language_field
MODAL_DIMS = {
    "visual": 16, "auditory": 12, "smell": 8, "taste": 6, "touch": 10, "emotion": 8, "lexical": 32,
}
MODALS = list(MODAL_DIMS.keys())

def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v));  return v if n == 0 else (v / n)

def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a); nb = np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

class ConceptNodes:
    """
    Maintains a small set of concept centroids.
    Each concept has a centroid per modality; tokens attach if resonance >= tau.
    """
    def __init__(self, tau: float = 0.62, max_nodes: int = 64):
        self.tau = tau
        self.max_nodes = max_nodes
        self.centroids: List[Dict[str, np.ndarray]] = []
        self.members: List[List[str]] = []

    def _concept_similarity(self, vecs: Dict[str, np.ndarray], cid: int) -> float:
        c = self.centroids[cid]
        sims = []
        for m in MODALS:
            sims.append(_cos(vecs[m], c[m]))
        return float(np.mean(sims))

    def add_or_attach(self, token: str, vecs: Dict[str, np.ndarray]):
        # find best node
        if self.centroids:
            sims = [self._concept_similarity(vecs, i) for i in range(len(self.centroids))]
            best_i = int(np.argmax(sims)); best_s = float(np.max(sims))
        else:
            best_i, best_s = -1, 0.0

        if best_s >= self.tau:
            # attach and update centroid (EMA)
            self.members[best_i].append(token)
            c = self.centroids[best_i]
            for m in MODALS:
                c[m] = _unit(0.85 * c[m] + 0.15 * vecs[m])
        else:
            if len(self.centroids) < self.max_nodes:
                self.centroids.append({m: _unit(vecs[m]) for m in MODALS})
                self.members.append([token])
            else:
                # if full, attach to best anyway (soft clustering)
                self.members[best_i].append(token)
                c = self.centroids[best_i]
                for m in MODALS:
                    c[m] = _unit(0.95 * c[m] + 0.05 * vecs[m])

    def snapshot(self) -> List[Tuple[List[str], Dict[str, np.ndarray]]]:
        return [(self.members[i], self.centroids[i]) for i in range(len(self.centroids))]
