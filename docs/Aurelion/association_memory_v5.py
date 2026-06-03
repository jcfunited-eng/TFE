# association_memory_v5.py
# Lightweight associative store with weights and simple queries

from __future__ import annotations
from typing import Dict, List, Tuple
import json
import math

class AssociationMemoryV5:
    """
    Weighted, undirected association graph:
      weights[a][b] == weights[b][a] == strength (float)
    """

    def __init__(self) -> None:
        self.weights: Dict[str, Dict[str, float]] = {}

    # ---------- core ops ----------
    def _bump(self, a: str, b: str, delta: float) -> None:
        if a == b:
            return
        wa = self.weights.setdefault(a, {})
        wb = self.weights.setdefault(b, {})
        wa[b] = wa.get(b, 0.0) + delta
        wb[a] = wb.get(a, 0.0) + delta

    def add_links(self, center: str, neighbors: List[str], lr: float = 0.05) -> None:
        """Hebbian bump: center co-activates with neighbors"""
        for n in neighbors:
            self._bump(center, n, lr)

    def add_cooccurrence_ring(self, tokens: List[str], lr: float = 0.02) -> None:
        """Bump all pairs within a short window"""
        w = min(4, max(2, len(tokens)))
        for i, a in enumerate(tokens):
            for j in range(i+1, min(len(tokens), i+w)):
                b = tokens[j]
                self._bump(a, b, lr)

    def decay(self, gamma: float = 0.995, floor: float = 1e-6) -> None:
        """Exponential decay with pruning"""
        to_del_a = []
        for a, nbrs in self.weights.items():
            to_del_b = []
            for b, w in nbrs.items():
                nw = w * gamma
                if nw < floor:
                    to_del_b.append(b)
                else:
                    nbrs[b] = nw
            for b in to_del_b:
                del nbrs[b]
            if not nbrs:
                to_del_a.append(a)
        for a in to_del_a:
            del self.weights[a]

    # ---------- queries ----------
    def top_neighbors(self, term: str, k: int = 5) -> List[Tuple[str, float]]:
        nbrs = self.weights.get(term, {})
        return sorted(nbrs.items(), key=lambda x: x[1], reverse=True)[:k]

    def all_edges(self, threshold: float = 0.05) -> List[Tuple[str, str, float]]:
        out = []
        seen = set()
        for a, nbrs in self.weights.items():
            for b, w in nbrs.items():
                if w >= threshold:
                    key = tuple(sorted((a, b)))
                    if key not in seen:
                        seen.add(key)
                        out.append((key[0], key[1], w))
        return out

    # ---------- persistence ----------
    def to_dict(self) -> Dict:
        return {"weights": self.weights}

    @classmethod
    def from_dict(cls, d: Dict) -> "AssociationMemoryV5":
        obj = cls()
        obj.weights = d.get("weights", {})
        return obj

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "AssociationMemoryV5":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
