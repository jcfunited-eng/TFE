# primitive_sensory_pack.py
# unified dimension definitions for multimodal morphospace
import numpy as np

# Use same dim for every modality to avoid shape mismatch
DIMS = {
    "visual": 8,
    "auditory": 8,
    "smell": 8,
    "taste": 8,
    "touch": 8,
    "emotion": 8,
    "lexical": 8,
}

def zeros(name: str) -> np.ndarray:
    return np.zeros(DIMS[name], dtype=np.float32)

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

# --- Primitive sense generators ---

def _visual_features(text: str) -> np.ndarray:
    v = np.random.default_rng(abs(hash(text + "vis")) % (2**32)).random(DIMS["visual"])
    return v / (np.linalg.norm(v) + 1e-8)


def _auditory_features(text: str) -> np.ndarray:
    v = np.random.default_rng(abs(hash(text + "aud")) % (2**32)).random(DIMS["auditory"])
    return v / (np.linalg.norm(v) + 1e-8)


def _smell_features(text: str) -> np.ndarray:
    v = np.random.default_rng(abs(hash(text + "smell")) % (2**32)).random(DIMS["smell"])
    return v / (np.linalg.norm(v) + 1e-8)


def _taste_features(text: str) -> np.ndarray:
    v = np.random.default_rng(abs(hash(text + "taste")) % (2**32)).random(DIMS["taste"])
    return v / (np.linalg.norm(v) + 1e-8)


def _touch_features(text: str) -> np.ndarray:
    v = np.random.default_rng(abs(hash(text + "touch")) % (2**32)).random(DIMS["touch"])
    return v / (np.linalg.norm(v) + 1e-8)


def _emotion_features(text: str) -> np.ndarray:
    # Emotions derived from simple sentiment heuristics
    text_lower = text.lower()
    pos_words = ["love", "joy", "calm", "peace", "happy", "trust"]
    neg_words = ["anger", "sad", "fear", "hate", "pain", "grief"]

    valence = sum(w in text_lower for w in pos_words) - sum(w in text_lower for w in neg_words)
    arousal = (abs(valence) / (len(pos_words) + len(neg_words))) + 0.1

    # Generate a stable emotion vector and pad if short
    base = np.array([valence, arousal], dtype=np.float32)
    if base.shape[0] < DIMS["emotion"]:
        base = np.pad(base, (0, DIMS["emotion"] - base.shape[0]))
    return base / (np.linalg.norm(base) + 1e-8)


# --- Main sense assembler ---

def senses_from_text(text: str) -> dict:
    """Produce a multimodal dictionary of sensory activations from text."""
    senses = {
        "visual": _visual_features(text),
        "auditory": _auditory_features(text),
        "smell": _smell_features(text),
        "taste": _taste_features(text),
        "touch": _touch_features(text),
        "emotion": _emotion_features(text),
    }
    return senses
