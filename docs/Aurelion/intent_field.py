# language_field.py
# Aurelion — Language Field Learner (v4.1)
# Adds persistent memory path support for the Learning Harness

import json
import numpy as np
from pathlib import Path
from primitive_sensory_pack import DIMS, zeros

class LanguageFieldLearner:
    """
    Maps tokens to multimodal signatures (visual, auditory, etc.)
    with persistence on disk for reuse across runs.
    """

    def __init__(self, memory_path: str = "language_memory.json"):
        self.memory_path = Path(memory_path)
        self.memory = {m: {} for m in list(DIMS.keys()) + ["lexical"]}

        if self.memory_path.exists():
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.memory = {
                    m: {k: np.array(v, dtype=np.float32) for k, v in data.get(m, {}).items()}
                    for m in self.memory
                }
                print(f"[INFO] Loaded {len(self.memory['lexical'])} learned tokens from {self.memory_path.name}")
            except Exception as e:
                print(f"[WARN] Could not load existing memory: {e}")
        else:
            print("[INFO] No prior language memory found; starting fresh.")

    # -------------------------------
    # Core learning and recall
    # -------------------------------

    def learn(self, text: str, senses: dict):
        """
        Learns the multimodal signature of a chunk of text.
        Each token gets an averaged signature update.
        """
        tokens = [w.lower() for w in text.split() if w.isalpha() or w.isalnum()]
        for tok in tokens:
            for m, vec in senses.items():
                if m not in self.memory:
                    continue
                v_old = self.memory[m].get(tok)
                if v_old is None:
                    self.memory[m][tok] = vec.copy()
                else:
                    # Weighted update (slow forgetting, gentle learning)
                    self.memory[m][tok] = 0.9 * v_old + 0.1 * vec

    def recall(self, word: str):
        """
        Returns all modality vectors for a given word if known.
        """
        word = word.lower()
        rec = {}
        for m in self.memory:
            v = self.memory[m].get(word)
            if v is not None:
                rec[m] = v
        return rec if rec else None

    # -------------------------------
    # Persistence
    # -------------------------------

    def save(self):
        """Writes current memory to disk."""
        try:
            data = {
                m: {k: v.tolist() for k, v in self.memory[m].items()}
                for m in self.memory
            }
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[INFO] Language memory saved to {self.memory_path}")
        except Exception as e:
            print(f"[ERROR] Could not save memory: {e}")

    # -------------------------------
    # Maintenance
    # -------------------------------

    def reset(self):
        """Clears all learned tokens (keeps structure)."""
        self.memory = {m: {} for m in self.memory}
        if self.memory_path.exists():
            self.memory_path.unlink()
        print("[INFO] Language memory reset.")
