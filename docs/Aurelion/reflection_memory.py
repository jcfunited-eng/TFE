# reflection_memory.py
# v4.8 — simple reflection state for adaptive prompts & anchors

from __future__ import annotations
from typing import Dict, List, Tuple
from pathlib import Path
import json, re, numpy as np

STOP = set("""
a an the and or of to in on at for with from as by is are was were be being been do does did has have had it this that these those i you he she we they them his her our your their my me mine ours yours theirs
""".split())

def _clean(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z0-9\-']+", text.lower())
    return [t for t in toks if t not in STOP and len(t) > 1]

class ReflectionState:
    def __init__(self):
        self.counts: Dict[str, int] = {}
        self.recent: List[str] = []

    def observe(self, text: str, senses: Dict[str, np.ndarray]):
        toks = _clean(text)
        for t in toks:
            self.counts[t] = self.counts.get(t, 0) + 1
        self.recent.append(text)
        self.recent = self.recent[-20:]

    def top_tokens(self, k: int = 5) -> List[Tuple[str, int]]:
        return sorted(self.counts.items(), key=lambda x: -x[1])[:k]

    def make_prompts(self) -> List[str]:
        tips = []
        tops = [t for t, _ in self.top_tokens(5)]
        if not tops:
            return tips
        if len(tops) >= 2:
            tips.append(f"How do “{tops[0]}” and “{tops[1]}” connect?")
        tips.append(f"Should we clarify “{tops[0]}” with an example?")
        if len(self.recent) >= 2:
            tips.append("What changed between the last two ideas?")
        return tips

    def to_json(self) -> Dict:
        return {"counts": self.counts, "recent": self.recent}

    @classmethod
    def from_json(cls, obj: Dict) -> "ReflectionState":
        r = cls()
        r.counts = dict(obj.get("counts", {}))
        r.recent = list(obj.get("recent", []))
        return r

    def save(self, path: Path):
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ReflectionState":
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return cls.from_json(data)
            except Exception:
                pass
        return cls()
