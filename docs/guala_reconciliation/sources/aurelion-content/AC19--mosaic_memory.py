
from __future__ import annotations
import json, datetime
from pathlib import Path
from typing import List, Dict, Any

class MosaicMemory:
    def __init__(self, path: str = "mosaic_memory.jsonl", min_phi: float = 0.40, max_keep: int = 256):
        self.path = Path(path)
        self.min_phi = float(min_phi)
        self.max_keep = int(max_keep)
        self.items: List[Dict[str, Any]] = []
        if self.path.exists():
            for ln in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
                try:
                    self.items.append(json.loads(ln))
                except Exception:
                    pass
        self.items = self.items[-self.max_keep:]

    def load_domain(self, domain: str) -> List[Dict[str, Any]]:
        d = domain.lower()
        return [x for x in self.items if x.get("domain","") == d]

    def add_meta_mosaics(self, domain: str, metas: List[Dict[str, Any]], embed=None):
        now = datetime.datetime.now().isoformat(timespec="seconds")
        for m in metas:
            phi = float(m.get("phi", 0.0))
            toks = m.get("tokens", [])
            if not toks or phi < self.min_phi:
                continue
            centroid = None
            if embed is not None:
                try:
                    vec = embed.encode([" ".join(toks)])
                    centroid = vec[0].tolist()
                except Exception:
                    centroid = None
            self._merge({
                "domain": domain.lower(),
                "tokens": toks[:16],
                "centroid": centroid,
                "phi": round(phi, 3),
                "count": 1,
                "last_seen": now
            })
        with self.path.open("w", encoding="utf-8") as f:
            for x in self.items[-self.max_keep:]:
                f.write(json.dumps(x) + "\n")

    def _merge(self, proto: Dict[str, Any]):
        def jacc(a, b):
            A, B = set(a), set(b)
            inter = len(A & B); union = len(A | B) or 1
            return inter / union
        best_i, best_j = None, 0.0
        for i, it in enumerate(self.items):
            if it.get("domain") != proto.get("domain"):
                continue
            j = jacc(it.get("tokens",[]), proto.get("tokens",[]))
            if j > best_j:
                best_j, best_i = j, i
        if best_j >= 0.5 and best_i is not None:
            it = self.items[best_i]
            it["count"] = int(it.get("count",1)) + 1
            it["phi"] = float((it.get("phi",0.0) + proto.get("phi",0.0)) / 2.0)
            it["last_seen"] = proto.get("last_seen")
            if it.get("centroid") is None and proto.get("centroid") is not None:
                it["centroid"] = proto["centroid"]
            a = it.get("tokens", []); b = proto.get("tokens", [])
            merged = list(dict.fromkeys(a + b))[:16]
            it["tokens"] = merged
        else:
            self.items.append(proto)
            self.items[:] = self.items[-self.max_keep:]

    def seeds_for_domain(self, domain: str, limit: int = 8) -> List[Dict[str, Any]]:
        xs = sorted(self.load_domain(domain), key=lambda r: (r.get("phi",0.0), r.get("count",1)), reverse=True)
        return xs[:limit]
