
# language_bridge.py
import re, numpy as np, random
class TinyVocab:
    def __init__(self, dim=128, seed=2024):
        self.dim = dim
        self.rng = np.random.default_rng(seed)
        self.emb = {}
        self.templates = [
            "Stabilizing around {topic}; clarity grows as patterns settle.",
            "Exploring {topic}; small signals hint at deeper order.",
            "Resonance rising near {topic}; let's test for persistence.",
            "Low coherence in {topic}; softening the field and searching anew.",
            "Energy conserved around {topic}; preparing for a deliberate push."
        ]

    def _vec(self, token: str):
        if token not in self.emb:
            h = abs(hash(token)) % (10**9)
            r = np.random.default_rng(h)
            self.emb[token] = r.normal(0, 0.7, size=(self.dim,))
        return self.emb[token]

    def encode(self, text: str):
        toks = re.findall(r"[A-Za-z0-9]+", text.lower())
        if not toks: return np.zeros((self.dim,))
        v = np.zeros((self.dim,))
        for t in toks[:128]: v += self._vec(t)
        n = np.linalg.norm(v); return v/n if n>0 else v

    def nearest_tokens(self, v, k=5):
        if not self.emb:
            for w in ["validation","mission","storm","market","coherence","growth","safety","policy","energy","resonance","stability"]:
                _ = self._vec(w)
        sims = []
        nv = np.linalg.norm(v)+1e-9
        for w,e in self.emb.items():
            s = float(np.dot(v,e)/((np.linalg.norm(e)+1e-9)*nv))
            sims.append((s,w))
        sims.sort(reverse=True)
        return [w for _,w in sims[:k]]

    def phrase_from_state(self, v):
        toks = self.nearest_tokens(v, k=4)
        topic = ", ".join(toks[:3]) if toks else "current focus"
        return random.choice(self.templates).format(topic=topic)
