# morphospace_multimodal.py
# v4.5 compatible multimodal morphospace utilities

import numpy as np
from primitive_sensory_pack import DIMS, zeros

# Define canonical modality order used across modules
MOD_ORDER = ["visual", "auditory", "smell", "taste", "touch", "emotion", "lexical"]

class Modality:
    def __init__(self, name):
        self.name = name
        self.dim = int(DIMS[name])
        self.state = np.zeros(self.dim, dtype=np.float32)

    def stimulate(self, vec, alpha=0.6):
        v = np.asarray(vec, dtype=np.float32)
        # dimension safety
        if v.shape[0] < self.dim:
            v = np.pad(v, (0, self.dim - v.shape[0]))
        elif v.shape[0] > self.dim:
            v = v[: self.dim]
        self.state = (1 - alpha) * self.state + alpha * v

    def reset(self):
        self.state[:] = 0

    def norm(self):
        return float(np.linalg.norm(self.state))


class MorphospaceMultimodal:
    def __init__(self):
        self.modalities = {m: Modality(m) for m in MOD_ORDER}

    def stimulate(self, senses, alpha=0.6, weights=None):
        if weights is None:
            weights = {m: 1.0 for m in MOD_ORDER}
        for m in MOD_ORDER:
            v = senses.get(m, zeros(m))
            self.modalities[m].stimulate(v * weights.get(m, 1.0), alpha)

    def reset(self):
        for m in MOD_ORDER:
            self.modalities[m].reset()


def senses_from_text(text: str):
    """
    Primitive multimodal text → sensory encoding.
    Produces normalized random-hash vectors per modality.
    """
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    senses = {}
    for m in MOD_ORDER:
        v = rng.random(DIMS[m], dtype=np.float32)
        v = v / max(1e-6, np.linalg.norm(v))
        senses[m] = v
    return senses
