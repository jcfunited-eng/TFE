# WorkingMemory — short-term dialogue memory with decayed recall
# Stores recent turns (text + per-modality vectors + metrics),
# provides a decayed context bias vector per modality.

import json, os
from typing import Dict, Any, List
import numpy as np

from primitive_sensory_pack import DIMS, zeros

MOD_ORDER = ["visual","auditory","smell","taste","touch","emotion","lexical"]

class WorkingMemory:
    def __init__(self, memory_path: str = "dialogue_memory.json", max_turns: int = 200):
        self.path = memory_path
        self.max_turns = int(max_turns)
        self.turns: List[Dict[str, Any]] = []
        self.load()

    # ------------- persistence -------------
    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.turns = data.get("turns", [])
            except Exception:
                self.turns = []
        else:
            self.turns = []

    def save(self):
        data = {"turns": self.turns[-self.max_turns:]}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ------------- memory ops -------------
    def size(self) -> int:
        return len(self.turns)

    def push_turn(self, text: str, senses: Dict[str, np.ndarray], phi: float, H: float, E: float):
        rec = {
            "text": text,
            "phi": float(phi),
            "H": float(H),
            "E": float(E),
            "mods": {}
        }
        for name in MOD_ORDER:
            v = senses.get(name, zeros(name))
            rec["mods"][name] = (v.astype(float)).tolist()
        self.turns.append(rec)
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def recall_bias(self, decay: float = 0.90) -> Dict[str, np.ndarray]:
        """Return a decayed weighted average per modality from recent turns."""
        out: Dict[str, np.ndarray] = {name: zeros(name) for name in MOD_ORDER}
        if not self.turns:
            return out
        w = 1.0
        Z = 0.0
        # Walk backwards: most recent has highest weight
        for rec in reversed(self.turns):
            for name in MOD_ORDER:
                v = np.array(rec["mods"][name], dtype=np.float32)
                out[name] += w * v
            Z += w
            w *= float(decay)
        if Z <= 1e-9:
            return out
        for name in MOD_ORDER:
            out[name] = out[name] / Z
        return out

    def summarize(self) -> str:
        n = len(self.turns)
        if n == 0:
            return "No dialogue yet."
        last = self.turns[-1]
        return f"Turns={n}, last φ={last['phi']:.3f}, H={last['H']:.3f}, E={last['E']:.3f}"
