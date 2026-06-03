# aurelion_core_v4_multimodal.py
# Multimodal Cognition (recall + concepts + goals) with dimension-safe coherence.

from __future__ import annotations
import numpy as np
import sys
from typing import Dict
from language_field import LanguageFieldLearner, MODALS, MODAL_DIMS
from concept_nodes import ConceptNodes
from attention_goal import GoalAttention

# ---- minimal multimodal morphospace ----
class ModSpace:
    def __init__(self, name: str, dim: int):
        self.name = name
        self.dim = dim
        self.state = np.zeros(dim, dtype=np.float32)

    def stimulate(self, x: np.ndarray, alpha: float, weight: float = 1.0):
        x = x.astype(np.float32)
        if x.shape[0] != self.dim:
            # dimension safeguard: resize via padding/truncation
            if x.shape[0] > self.dim:
                x = x[:self.dim]
            else:
                x = np.pad(x, (0, self.dim - x.shape[0]))
        a = alpha * float(weight)
        self.state = (1.0 - a) * self.state + a * x

    def norm(self) -> float:
        n = float(np.linalg.norm(self.state))
        return 0.0 if n == 0 else min(1.0, n)


class MorphospaceMultimodal:
    def __init__(self):
        self.modalities = {m: ModSpace(m, MODAL_DIMS[m]) for m in MODALS}

    def stimulate(self, senses: Dict[str, np.ndarray], alpha: float, weights: Dict[str, float]):
        for m, space in self.modalities.items():
            x = senses.get(m, np.zeros(space.dim, dtype=np.float32))
            space.stimulate(x, alpha=alpha, weight=weights.get(m, 1.0))

    def _align(self, a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Ensure equal length by zero-padding or truncation."""
        n = min(a.shape[0], b.shape[0])
        if a.shape[0] != n:
            a = a[:n] if a.shape[0] > n else np.pad(a, (0, n - a.shape[0]))
        if b.shape[0] != n:
            b = b[:n] if b.shape[0] > n else np.pad(b, (0, n - b.shape[0]))
        return a, b

    def coherence(self) -> float:
        vecs = [s.state for s in self.modalities.values()]
        if len(vecs) < 2:
            return 0.0
        cs = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                a, b = self._align(vecs[i], vecs[j])
                na, nb = np.linalg.norm(a), np.linalg.norm(b)
                if na == 0 or nb == 0:
                    continue
                cs.append(float(np.dot(a, b) / (na * nb)))
        return 0.0 if not cs else float(np.clip(np.mean(cs), 0.0, 1.0))

    def entropy(self) -> float:
        mags = np.array([s.norm() for s in self.modalities.values()], dtype=np.float32) + 1e-6
        p = mags / np.sum(mags)
        return float(-np.sum(p * np.log(p)) / np.log(len(mags)))

    def energy(self) -> float:
        return float(np.mean([s.norm() for s in self.modalities.values()]))


# ---- primitive multimodal encoding ----
_rng = np.random.default_rng(7)
def _hash_vec(n: int, token: str) -> np.ndarray:
    h = abs(hash(token)) % (10**9 + 7)
    _loc = _rng.random(n)
    v = ((h % 997) * _loc) % 1.0
    return v.astype(np.float32)


def senses_from_text(text: str) -> Dict[str, np.ndarray]:
    words = [w for w in "".join(ch if ch.isalnum() else " " for ch in text.lower()).split() if w]
    if not words:
        return {m: np.zeros(MODAL_DIMS[m], dtype=np.float32) for m in MODALS}
    senses = {}
    for m in MODALS:
        dim = MODAL_DIMS[m]
        v = np.zeros(dim, dtype=np.float32)
        for w in words:
            v += _hash_vec(dim, f"{m}:{w}")
        n = np.linalg.norm(v)
        senses[m] = v if n == 0 else (v / n)
    return senses


# ---- interface helpers ----
def fmt_status(phi: float, H: float, E: float, field: MorphospaceMultimodal) -> str:
    mods = "  ".join(f"{m}:{field.modalities[m].norm():0.2f}" for m in MODALS)
    return f"φ={phi:0.3f}  H={H:0.3f}  Energy={E:0.3f}  |  {mods}"


# ---- main interactive chat ----
def run_chat():
    field = MorphospaceMultimodal()
    learner = LanguageFieldLearner(path="language_memory.json")
    concepts = ConceptNodes(tau=0.64, max_nodes=96)
    goals = GoalAttention()

    print("Aurelion v4 — Multimodal Cognition (recall + concepts + goals)")
    print("Commands: /state  /reset  /goal <stabilize|explore|focus>  /show <word>  /cluster  /save  /quit")

    while True:
        try:
            msg = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[EXIT]")
            break
        if not msg:
            continue

        if msg.startswith("/"):
            parts = msg.split()
            cmd = parts[0].lower()
            if cmd == "/quit":
                break
            elif cmd == "/reset":
                field = MorphospaceMultimodal()
                print("[OK] Field reset.")
                continue
            elif cmd == "/state":
                phi = field.coherence()
                H = field.entropy()
                E = field.energy()
                print(fmt_status(phi, H, E, field))
                continue
            elif cmd == "/goal":
                if len(parts) >= 2:
                    goals.set_goal(parts[1])
                print(f"[GOAL] {goals.goal}")
                continue
            elif cmd == "/save":
                learner.save()
                print("[OK] Memory saved.")
                continue
            elif cmd == "/show":
                if len(parts) < 2:
                    print("Usage: /show <word>")
                    continue
                w = parts[1].lower()
                if w not in learner.tokens:
                    print(f"[INFO] Unknown token: {w}")
                    continue
                mods = learner.tokens[w]
                print(f"Concept: '{w}' — Learned Modal Signatures")
                for m in MODALS:
                    v = np.array(mods[m], dtype=np.float32)
                    s = ", ".join(f"{float(x):0.2f}" for x in v[:5])
                    print(f"  {m:<8}: |v|={np.linalg.norm(v):0.3f}  sample=[{s}]")
                continue
            elif cmd == "/cluster":
                for tok in learner.known_tokens():
                    vecs = {m: np.array(learner.tokens[tok][m], dtype=np.float32) for m in MODALS}
                    concepts.add_or_attach(tok, vecs)
                snap = concepts.snapshot()
                print("\n=== Resonance Concept Nodes ===")
                for i, (members, centroid) in enumerate(snap):
                    label = ", ".join(members[:6]) + ("..." if len(members) > 6 else "")
                    print(f"Node {i:02d}: {label}")
                continue
            else:
                print("[INFO] Unknown command.")
                continue

        # --- normal text processing ---
        raw = senses_from_text(msg)
        recalled = learner.recall(msg, k=6)
        fused = {m: _unit(0.6 * recalled[m] + 0.4 * raw[m]) for m in MODALS}
        phi = field.coherence()
        H = field.entropy()
        E = field.energy()
        alpha, weights = goals.decide(phi, E, recalled)
        field.stimulate(fused, alpha=alpha, weights=weights)
        learner.learn(msg, fused, alpha=alpha)
        for t in learner._tok(msg):
            if t in learner.tokens:
                vecs = {m: np.array(learner.tokens[t][m], dtype=np.float32) for m in MODALS}
                concepts.add_or_attach(t, vecs)
        phi = field.coherence()
        H = field.entropy()
        E = field.energy()
        print(fmt_status(phi, H, E, field))


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v if n == 0 else (v / n)


if __name__ == "__main__":
    run_chat()
