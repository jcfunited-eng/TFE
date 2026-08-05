#!/usr/bin/env python3
"""
aurelion_fmm_script.py

Aurelion FMM-Script: Internal Representational Language

This module defines:
- FMMFeatures: (Intensity, Coherence, Novelty, Affect)
- G32Token: a 32-dimensional internal "geometry token" with:
    - 16 fixed structural dimensions
    - 16 fractal / dynamic dimensions
- encode_text_to_fmm() and encode_text_to_g32()
- estimate_uncertainty() from FMM
- blend_dream_influence(): non-destructive layering for dreams
- update_familiarity(): sliding-scale uncertainty reduction (sunglasses effect)

This is the "language of the brain" layer for Aurelion.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import math
import json
import os
from pathlib import Path
from collections import defaultdict
import re
import time
from datetime import datetime

def now_iso():
    """UTC timestamp in ISO format."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def nowz():
    """Alias/compatibility wrapper."""
    return now_iso()

ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
MEM.mkdir(parents=True, exist_ok=True)
FMM_DIR = MEM / "fmm"
FMM_DIR.mkdir(parents=True, exist_ok=True)

FAMILIARITY_F = FMM_DIR / "familiarity.json"


# ============================================================
# FMM FEATURES (I, C, N, A)
# ============================================================

@dataclass
class FMMFeatures:
    """
    Fractal Mind Model primitive features:
    I — Intensity (0..1)
    C — Coherence (0..1)
    N — Novelty (0..1)
    A — Affect/Valence (0..1, where 0=negative, 0.5=neutral, 1=positive)
    """
    intensity: float
    coherence: float
    novelty: float
    affect: float

    def clamp(self):
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.coherence = max(0.0, min(1.0, self.coherence))
        self.novelty   = max(0.0, min(1.0, self.novelty))
        self.affect    = max(0.0, min(1.0, self.affect))
        return self


# ============================================================
# G32 TOKEN (HYBRID GEOMETRY + SEMANTIC META)
# ============================================================

@dataclass
class G32Token:
    """
    Internal geometry token: 32-dimensional vector + rich metadata.

    vec: List[float] of length 32
        [0-15]  fixed structural components
        [16-31] fractal dynamic components

    meta: Dict[str, Any]
        Includes:
         - 'modality': 'text' | 'audio' | 'vision' | ...
         - 'topic': optional topic string
         - 'uncertainty': 0..1
         - 'fmm': original FMMFeatures as dict
         - 'familiarity': 0..1 (higher = more familiar)
         - 'tags': list of labels
         - 'timestamp': ISO time
    """
    vec: List[float] = field(default_factory=lambda: [0.0]*32)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {"vec": self.vec, "meta": self.meta}

    def copy(self) -> "G32Token":
        return G32Token(vec=list(self.vec), meta=dict(self.meta))


# ============================================================
# FAMILIARITY STORE (for sunglasses effect)
# ============================================================

def load_familiarity() -> Dict[str, float]:
    if FAMILIARITY_F.exists():
        try:
            return json.loads(FAMILIARITY_F.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_familiarity(fam: Dict[str, float]):
    FAMILIARITY_F.write_text(json.dumps(fam, indent=2), encoding="utf-8")


def update_familiarity(key: str, fam: Dict[str, float], amount: float = 0.05) -> float:
    """
    Increase familiarity for a given key (e.g. topic, phrase root) by a small amount.
    Max at 1.0. This is your "sunglasses adaptation" — repeated exposure -> less uncertainty.
    """
    old = fam.get(key, 0.0)
    new = max(0.0, min(1.0, old + amount))
    fam[key] = new
    return new


# ============================================================
# FMM ENCODING FROM TEXT (SIMPLE BUT STRUCTURED)
# ============================================================

def encode_text_to_fmm(text: str, context: Optional[Dict[str, Any]] = None) -> FMMFeatures:
    """
    Encode text input into FMM features (I, C, N, A).
    This is a first-pass, RRE-consistent heuristic encoder.

    We will refine this later; for now:
      - Intensity: based on length and punctuation
      - Coherence: based on word structure & punctuation
      - Novelty: based on presence of 'learn', 'new', topic words, etc.
      - Affect: naive sentimentish based on a few keywords
    """
    context = context or {}
    t = text.strip().lower()
    length = len(t)
    words = re.findall(r"[a-z]+", t)

    # Intensity: how "strong" / "full" the input is
    intensity = min(1.0, length / 80.0)

    # Coherence: more words, moderate length, fewer weird chars -> higher coherence
    if not words:
        coherence = 0.2
    else:
        avg_len = sum(len(w) for w in words) / len(words)
        # prefer moderate-length words and moderate length overall
        coherence = 0.0
        # crude baseline
        coherence += min(1.0, len(words) / 20.0) * 0.4    # enough words
        coherence += (1.0 - abs(avg_len - 5.0)/5.0) * 0.4 # word length near 5 chars
        coherence = max(0.0, min(1.0, coherence))

    # Novelty: words not in known topics / presence of "learn", "new", question marks, etc.
    known_topics = [k.lower() for k in context.get("known_topics", [])]
    is_question = "?" in t or t.startswith("what") or t.startswith("why") or t.startswith("how")
    # base novelty on ratio of words not in known topics
    novel_count = sum(1 for w in words if w not in known_topics)
    novelty = 0.0
    if words:
        novelty = novel_count / len(words)
    if "learn" in t or "study" in t or "new" in t:
        novelty = max(novelty, 0.6)
    if is_question:
        novelty = max(novelty, 0.4)
    novelty = max(0.0, min(1.0, novelty))

    # Affect: extremely crude; will refine later
    pos_words = ["good","love","like","happy","hope","curious","excited","cool","interesting"]
    neg_words = ["bad","hate","angry","scared","worried","sad","tired","frustrated","upset"]
    pos_hits = sum(1 for w in words if w in pos_words)
    neg_hits = sum(1 for w in words if w in neg_words)
    if pos_hits == 0 and neg_hits == 0:
        affect = 0.5
    else:
        # map pos:neg to [0,1]
        score = (pos_hits - neg_hits) / max(1, pos_hits + neg_hits)
        affect = 0.5 + 0.4*score
    affect = max(0.0, min(1.0, affect))

    return FMMFeatures(intensity, coherence, novelty, affect).clamp()


def estimate_uncertainty(fmm: FMMFeatures) -> float:
    """
    Estimate uncertainty from FMM dimensions.
    High uncertainty = low coherence + low intensity + high novelty.
    """
    I = fmm.intensity
    C = fmm.coherence
    N = fmm.novelty

    # Weighted combination
    #  - missing information (1-C) is big driver
    #  - novelty adds some uncertainty
    #  - very low intensity also adds uncertainty
    base = (1.0 - C) * 0.6 + N * 0.3 + (1.0 - I) * 0.1
    return max(0.0, min(1.0, base))


# ============================================================
# G32 HYBRID ENCODER
# ============================================================

def encode_text_to_g32(text: str, context: Optional[Dict[str, Any]] = None) -> G32Token:
    """
    Encode text into a G32Token: a 32-dimensional internal code + metadata.
    This is a hybrid of fixed and fractal features.

    Fixed indices [0..15]:
      0: radial_intensity
      1: angular_coherence
      2: harmonic_low
      3: harmonic_high
      4: curvature_index
      5: symmetry_score
      6: shape_regularity
      7: center_of_mass_shift
      8: orientation_signature
      9: contrast_vector
      10: temporal_decay_anchor
      11: structural_rigidity
      12: baseline_smoothness
      13: positional_phase
      14: identity_residue
      15: resonance_stability

    Fractal indices [16..31]:
      16: fractal_roughness
      17: recursive_depth
      18: novelty_burst
      19: emotional_tint
      20: uncertainty_shadow
      21: attractor_offset
      22: memory_flavor
      23: associative_drift
      24: dream_perturbation
      25: context_warp
      26: attention_ripple
      27: curiosity_pull
      28: valence_modulation
      29: interpretive_layer
      30: confabulation_tendency
      31: normalization_factor
    """
    context = context or {}
    fmm = encode_text_to_fmm(text, context)
    uncertainty = estimate_uncertainty(fmm)

    # Load familiarity map
    fam = load_familiarity()
    # Use a simple key: canonicalized topic root (we can refine this)
    topic_key = context.get("topic_key", "").lower().strip() or "global"
    familiarity = update_familiarity(topic_key, fam, amount=0.05)
    save_familiarity(fam)

    # Simple heuristics for fixed dims
    I = fmm.intensity
    C = fmm.coherence
    N = fmm.novelty
    A = fmm.affect

    # Fixed components (0-15) derived from FMM + simple transforms
    fixed = [0.0]*16
    fixed[0]  = I                     # radial_intensity
    fixed[1]  = C                     # angular_coherence
    fixed[2]  = I * C                 # harmonic_low
    fixed[3]  = (I * (1.0 - C))       # harmonic_high
    fixed[4]  = 1.0 - C               # curvature_index (less coherent -> more "curved")
    fixed[5]  = 1.0 - abs(0.5 - A)*2  # symmetry: neutral affect ~ more symmetric
    fixed[6]  = C                     # shape_regularity
    fixed[7]  = (N - 0.5) * 0.5 + 0.5 # center_of_mass_shift
    fixed[8]  = (A + N) / 2.0         # orientation_signature
    fixed[9]  = abs(I - C)            # contrast_vector
    fixed[10] = 0.8                   # temporal_decay_anchor (tunable)
    fixed[11] = 0.7                   # structural_rigidity (tunable)
    fixed[12] = 0.6 + 0.2*C           # baseline_smoothness
    fixed[13] = 0.5                   # positional_phase (placeholder)
    fixed[14] = 0.9                   # identity_residue (high by default)
    fixed[15] = C                     # resonance_stability

    # Fractal components (16-31) derived from FMM + uncertainty + familiarity
    fractal = [0.0]*16
    fractal[0]  = N                        # fractal_roughness
    fractal[1]  = 0.3 + 0.5*N              # recursive_depth
    fractal[2]  = N * (1.0 - familiarity)  # novelty_burst decays with familiarity
    fractal[3]  = A                        # emotional_tint
    fractal[4]  = uncertainty              # uncertainty_shadow
    fractal[5]  = (1.0 - familiarity)*0.5  # attractor_offset (less familiar -> more shift)
    fractal[6]  = (1.0 - uncertainty)*0.5  # memory_flavor (more certain -> stronger flavor)
    fractal[7]  = N * (1.0 - C)            # associative_drift
    fractal[8]  = 0.0                      # dream_perturbation (to be modulated separately)
    fractal[9]  = 0.2                      # context_warp (placeholder baseline)
    fractal[10] = I * (1.0 - C)           # attention_ripple
    fractal[11] = N * (1.0 - familiarity) # curiosity_pull
    fractal[12] = A                        # valence_modulation
    fractal[13] = 0.3 + 0.4*C             # interpretive_layer
    fractal[14] = N * uncertainty         # confabulation_tendency
    fractal[15] = familiarity             # normalization_factor

    vec = fixed + fractal

    meta = {
        "modality": context.get("modality", "text"),
        "topic": context.get("topic", None),
        "topic_key": topic_key,
        "uncertainty": uncertainty,
        "familiarity": familiarity,
        "fmm": {
            "intensity": fmm.intensity,
            "coherence": fmm.coherence,
            "novelty": fmm.novelty,
            "affect": fmm.affect,
        },
        "tags": context.get("tags", []),
        "timestamp": nowz()
    }

    return G32Token(vec=vec, meta=meta)


def nowz():  # alias to keep naming consistent
    return now_iso()


# ============================================================
# Dream Influence (Non-destructive blending)
# ============================================================

def blend_dream_influence(token: G32Token, dream_strength: float = 0.1) -> G32Token:
    """
    Apply non-destructive dream influence to the FRACTAL part of the token.

    dream_strength: 0..1
      0.0 -> no change
      ~0.1-0.3 -> gentle modulation (recommended)
      higher would be more intense dreaming

    We respect the principle:
      "Dreams do not rewrite the fractal components.
       They influence them via blending and layering,
       without destroying the underlying structure."
    """
    dream_strength = max(0.0, min(1.0, dream_strength))
    new_token = token.copy()
    # Only modify fractal components [16..31]
    for i in range(16, 32):
        base = token.vec[i]
        # simple perturbation around base
        noise = (random_noise() - 0.5) * 0.2  # slight perturbation
        new_token.vec[i] = max(0.0, min(1.0, base*(1.0 - dream_strength) + (base + noise)*dream_strength))
    # Increase interpretive layer slightly as dreams add meaning
    new_token.vec[16 + 13] = max(0.0, min(1.0, new_token.vec[16 + 13] + 0.05*dream_strength))
    return new_token


def random_noise():
    # simple placeholder; we can replace with more structured noise later
    import random
    return random.random()


# ============================================================
# Public API for orchestrator / other modules
# ============================================================

def fmm_from_text(text: str, known_topics: Optional[list[str]] = None) -> FMMFeatures:
    """Convenience wrapper to encode text into FMM."""
    return encode_text_to_fmm(text, {"known_topics": known_topics or []})


def g32_from_text(text: str, topic: Optional[str] = None, modality: str = "text") -> G32Token:
    """Convenience wrapper to encode text into G32Token."""
    context = {
        "modality": modality,
        "topic": topic,
        "topic_key": (topic or "").lower(),
        "tags": []
    }
    return encode_text_to_g32(text, context)


def get_uncertainty_from_text(text: str, known_topics: Optional[list[str]] = None) -> float:
    """Compute uncertainty directly from text (for quick checks)."""
    fmm = encode_text_to_fmm(text, {"known_topics": known_topics or []})
    return estimate_uncertainty(fmm)


def register_topic_familiarity(topic: str, amount: float = 0.05) -> float:
    """Manually increase familiarity with a topic (e.g. after reading a lesson)."""
    fam = load_familiarity()
    new_value = update_familiarity(topic.lower(), fam, amount=amount)
    save_familiarity(fam)
    return new_value
