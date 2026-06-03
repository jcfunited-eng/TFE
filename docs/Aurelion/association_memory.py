# association_memory.py
# v4.9 — Lightweight associative memory (concept ↔ concept graph)

from __future__ import annotations
import json, math, os, time
from collections import defaultdict
from typing import Dict, List, Tuple, Iterable, Optional

import numpy as np

def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

class AssociationMemory:
    """
    Stores a weighted, undirected association graph between tokens.
    Each edge weight accumulates by co-activation strength (mean cross-modal cosine).
    """
    def __init__(self, path: str = "association_memory.json"):
        self.path = path
        self.graph: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.meta = {"version": "4.9", "created": time.time(), "updated": time.time()}
        self.load(self.path)

    # ---------- Persistence ----------
    def load(self, path: Optional[str] = None) -> None:
        p = path or self.path
        if not os.path.exists(p):
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            g = obj.get("graph", {})
            self.graph = defaultdict(dict, {k: dict(v) for k, v in g.items()})
            self.meta = obj.get("meta", self.meta)
        except Exception:
            # keep empty graph on any error
            pass

    def save(self, path: Optional[str] = None) -> None:
        p = path or self.path
        obj = {"graph": self.graph, "meta": self.meta}
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            self.meta["updated"] = time.time()
        except Exception:
            pass

    # ---------- Core update ----------
    def update_from_tokens(
        self,
        tokens: List[str],
        senses_by_token: Dict[str, Dict[str, np.ndarray]],
        min_strength: float = 0.15,
        gain: float = 0.6,
        cap: float = 5.0,
    ) -> None:
        """
        For every unordered pair in `tokens`, compute a strength as the mean
        cosine across any common modalities present in senses_by_token.
        Accumulate into an undirected edge weight.
        """
        toks = [t for t in tokens if t]  # keep simple
        n = len(toks)
        if n < 2:
            return

        for i in range(n):
            ti = toks[i]
            vi = senses_by_token.get(ti, {})
            for j in range(i + 1, n):
                tj = toks[j]
                vj = senses_by_token.get(tj, {})
                if not vi or not vj:
                    continue
                scores: List[float] = []
                for m in vi.keys():
                    if m in vj:
                        scores.append(_cos(vi[m], vj[m]))
                if not scores:
                    continue
                s = float(np.clip(np.mean(scores), 0.0, 1.0))
                if s < min_strength:
                    continue
                # symmetric accumulation with gentle gain
                wij = self.graph[ti].get(tj, 0.0)
                wji = self.graph[tj].get(ti, 0.0)
                w = min(cap, (wij + wji) * 0.5 + gain * s)
                self.graph[ti][tj] = w
                self.graph[tj][ti] = w

    # ---------- Queries ----------
    def neighbors(self, token: str, topn: int = 7) -> List[Tuple[str, float]]:
        nbrs = self.graph.get(token, {})
        if not nbrs:
            return []
        return sorted(nbrs.items(), key=lambda kv: kv[1], reverse=True)[:topn]

    def explain(self, token: str, topn: int = 7) -> List[str]:
        rows = []
        nbrs = self.neighbors(token, topn=topn)
        for nb, w in nbrs:
            rows.append(f"{token} ↔ {nb}  (w={w:.3f})")
        if not rows:
            rows.append(f"[no associations yet for '{token}']")
        return rows

    def stats(self) -> Tuple[int, int]:
        nodes = len(self.graph)
        edges = sum(len(v) for v in self.graph.values()) // 2
        return nodes, edges
