# selfweave.py
# Minimal schema builder with activation pulses and JSON persistence.

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict, Counter
import itertools

class SelfWeave:
    def __init__(self, path:str="associations_v6.json"):
        self.path = Path(path)
        self.cooc: Dict[Tuple[str,str], int] = defaultdict(int)
        self.schemas: Dict[str, Dict] = {}  # name -> {"tokens": set(list), "strength": float}
        self.threshold = 3  # co-occurrence threshold to promote schema

        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.cooc = defaultdict(int, {tuple(k.split("||")):v for k,v in data.get("cooc", {}).items()})
                raw = data.get("schemas", {})
                self.schemas = {k: {"tokens": set(v.get("tokens", [])),
                                    "strength": float(v.get("strength", 1.0))}
                                for k,v in raw.items()}
            except Exception:
                self.cooc = defaultdict(int)
                self.schemas = {}

    def save(self):
        data = {
            "cooc": {"||".join(k): v for k,v in self.cooc.items()},
            "schemas": {k: {"tokens": list(v["tokens"]), "strength": v["strength"]}
                        for k,v in self.schemas.items()}
        }
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def learn_from_tokens(self, tokens:List[str]) -> None:
        toks = [t for t in tokens if t.strip()]
        # update co-occurrence
        for a,b in itertools.combinations(sorted(set(toks)), 2):
            self.cooc[(a,b)] += 1

        # promote to schemas if over threshold
        for (a,b), cnt in list(self.cooc.items()):
            if cnt >= self.threshold:
                name = f"{a}↔{b}"
                if name not in self.schemas:
                    self.schemas[name] = {"tokens": set([a,b]), "strength": 1.0}
                else:
                    self.schemas[name]["strength"] = min(2.0, self.schemas[name]["strength"] + 0.05)

    def active_schemas(self, tokens:List[str]) -> List[str]:
        act = []
        tokset = set(tokens)
        for name, meta in self.schemas.items():
            if meta["tokens"] & tokset:
                act.append(name)
        return act

    def list_schemas(self) -> List[str]:
        # return sorted by strength
        return sorted(self.schemas.keys(),
                      key=lambda n: self.schemas[n]["strength"],
                      reverse=True)
