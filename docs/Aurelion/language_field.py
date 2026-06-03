# language_field.py
# Unified for Aurelion v6.x — supports persistent load/save helpers

import json, os
import numpy as np
from typing import Dict
from primitive_sensory_pack import DIMS

class LanguageFieldLearner:
    """
    Simplified multimodal associative learner.
    Stores an average sensory vector per token and persists it as JSON.
    """

    def __init__(self, memory_path: str = "language_memory.json"):
        self.memory_path = memory_path
        self.memory: Dict[str, Dict[str, list]] = {}
        # Try to load immediately
        if os.path.exists(memory_path):
            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
                print(f"[INFO] Loaded {len(self.memory)} learned tokens from {memory_path}")
            except Exception:
                print(f"[WARN] Could not read {memory_path}, starting empty.")
        else:
            print("[INFO] No prior language memory found; starting fresh.")

    # ------------------------------------------------------------------

    def learn(self, text: str, senses: Dict[str, np.ndarray]):
        """
        Update token memories by averaging in the new sensory vectors.
        """
        tokens = [t.strip(",.!?;:\"'").lower() for t in text.split() if t.strip()]
        for tok in tokens:
            if tok not in self.memory:
                self.memory[tok] = {m: senses[m].tolist() for m in DIMS.keys()}
            else:
                for m in DIMS.keys():
                    prev = np.array(self.memory[tok][m], dtype=np.float32)
                    newv = senses[m]
                    self.memory[tok][m] = ((prev + newv) / 2.0).tolist()

    # ------------------------------------------------------------------

    def recall(self, text: str) -> Dict[str, np.ndarray]:
        """
        Return average sensory signature for a sequence of tokens.
        """
        tokens = [t.strip(",.!?;:\"'").lower() for t in text.split() if t.strip()]
        rec = {m: np.zeros(DIMS[m], dtype=np.float32) for m in DIMS.keys()}
        count = 0
        for tok in tokens:
            if tok in self.memory:
                for m in DIMS.keys():
                    rec[m] += np.array(self.memory[tok][m], dtype=np.float32)
                count += 1
        if count > 0:
            for m in DIMS.keys():
                rec[m] /= count
        return rec

    # ------------------------------------------------------------------

    def load_memory(self):
        """
        Explicit load (used by v6.x+ cores)
        """
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    self.memory = json.load(f)
                print(f"[INFO] Reloaded {len(self.memory)} tokens from {self.memory_path}")
            except Exception as e:
                print(f"[WARN] Failed to reload memory: {e}")
        else:
            print("[INFO] No saved memory found.")

    def save_memory(self, path: str = None) -> bool:
        """
        Save current memory to disk
        """
        path = path or self.memory_path
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2)
            return True
        except Exception as e:
            print(f"[WARN] Failed to save language memory: {e}")
            return False
