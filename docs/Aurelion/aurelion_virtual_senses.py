#!/usr/bin/env python3
"""
aurelion_virtual_senses.py

Aurelion Virtual Sensory Layer

This module defines a virtual multi-sensory interface for Aurelion.

Even without physical sensors, text input can be decomposed into:

- Conceptual auditory field
- Conceptual visual field
- Conceptual olfactory field
- Conceptual tactile / kinesthetic field
- Conceptual emotional field

Each sense produces one or more G32 tokens via the FMM-Script layer
(aurelion_fmm_script.py), and these are combined into a VirtualMosaic,
which is the multi-sensory representation the higher layers (RRE, Self-Field,
Dreams, etc.) can work with.

This keeps us fully aligned with the RRE/FMM/not-math framework:
raw input → FMM → G32 → multi-sensory mosaics.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import re
import json
import os
import time

# Import the FMM-Script layer
from aurelion_fmm_script import (
    G32Token,
    g32_from_text,
    get_uncertainty_from_text,
    register_topic_familiarity,
)

ROOT = Path(__file__).resolve().parent
MEM = ROOT / "memory"
MEM.mkdir(exist_ok=True)
SENSE_DIR = MEM / "senses"
SENSE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Dataclasses
# ============================================================

@dataclass
class VirtualMosaic:
    """
    A multi-sensory mosaic built from multiple G32 tokens (one per virtual sense).

    - tokens: mapping from sense name to G32Token
    - combined_vec: a single 32-dim vector representing the aggregated geometry
    - meta: aggregated metadata (senses, overall uncertainty, topic, familiarity, etc.)
    """
    tokens: Dict[str, G32Token] = field(default_factory=dict)
    combined_vec: List[float] = field(default_factory=lambda: [0.0]*32)
    meta: Dict[str, Any] = field(default_factory=dict)

    def senses(self) -> List[str]:
        return list(self.tokens.keys())


# ============================================================
# Sensory Keywords / Cues
# ============================================================

# These lists are intentionally simple. They give us a mapping
# from text cues to which virtual senses should be excited.

AUDITORY_CUES = [
    "hear", "heard", "listened", "sound", "noise", "voice", "shout", "shouted",
    "screamed", "engine", "honk", "siren", "truck", "car horn", "bang", "crash"
]

VISUAL_CUES = [
    "see", "saw", "look", "looked", "watch", "watched", "bright", "dark",
    "sun", "light", "shadow", "face", "faces", "sky", "tree", "car", "road",
    "blood", "clothes", "torn", "color", "colors"
]

OLFAC_CUES = [
    "smell", "smelled", "odor", "scent", "perfume", "stink", "stinky",
    "burnt", "burned", "smoke", "smoky", "rubber", "oil", "gasoline", "fuel"
]

TACTILE_CUES = [
    "touch", "touched", "hit", "hurt", "pain", "fell", "fall", "falling",
    "slid", "slide", "sliding", "cold", "hot", "warm", "cool", "breeze",
    "impact", "threw", "thrown", "pulled", "pushed", "scraped", "splinter"
]

EMO_CUES = [
    "angry", "anger", "sad", "happy", "afraid", "scared", "fear", "worried",
    "frustrated", "upset", "hurt", "lonely", "abandoned", "relieved", "calm",
    "curious", "excited", "ashamed", "guilty", "shocked"
]


# ============================================================
# Helper Functions
# ============================================================

def lowercase_words(text: str) -> List[str]:
    return re.findall(r"[a-z]+", text.lower())


def detect_sensory_cues(text: str) -> Dict[str, float]:
    """
    Return a mapping from virtual sense to an activation weight (0..1),
    based on keywords found in the text.

    Weight is approximate, just to bias relative contribution.
    """
    t = text.lower()
    words = lowercase_words(text)
    sense_weights = {
        "auditory": 0.0,
        "visual": 0.0,
        "olfactory": 0.0,
        "tactile": 0.0,
        "emotional": 0.0
    }

    def match_count(cues):
        return sum(1 for w in words for cue in cues if cue in w or w in cue)

    # Auditory
    aud_hits = match_count(AUDITORY_CUES)
    if aud_hits > 0:
        sense_weights["auditory"] = min(1.0, 0.3 + 0.2*aud_hits)

    # Visual
    vis_hits = match_count(VISUAL_CUES)
    if vis_hits > 0:
        sense_weights["visual"] = min(1.0, 0.3 + 0.15*vis_hits)

    # Olfactory
    olf_hits = match_count(OLFAC_CUES)
    if olf_hits > 0:
        sense_weights["olfactory"] = min(1.0, 0.3 + 0.25*olf_hits)

    # Tactile
    tac_hits = match_count(TACTILE_CUES)
    if tac_hits > 0:
        sense_weights["tactile"] = min(1.0, 0.3 + 0.2*tac_hits)

    # Emotional
    emo_hits = match_count(EMO_CUES)
    if emo_hits > 0:
        sense_weights["emotional"] = min(1.0, 0.3 + 0.2*emo_hits)
    else:
        # even without explicit cue words, emotional field always has some baseline
        sense_weights["emotional"] = max(sense_weights["emotional"], 0.2)

    # If nothing else triggers, auditory and emotional get a small baseline
    if all(v <= 0.0 for v in sense_weights.values()):
        sense_weights["auditory"] = 0.4
        sense_weights["emotional"] = 0.4

    return sense_weights


def build_g32_for_sense(text: str, sense: str, topic: Optional[str] = None) -> G32Token:
    """
    Build a G32 token for a given sense, using FMM-Script.

    We pass 'modality' and 'tags' so the token knows which sense it came from.
    """
    context = {
        "modality": sense,
        "topic": topic,
        "topic_key": (topic or "").lower().strip() or sense,
        "tags": [sense]
    }
    return g32_from_text(text, topic=topic, modality=sense)


def combine_tokens_weighted(tokens: Dict[str, G32Token], weights: Dict[str, float]) -> List[float]:
    """
    Combine multiple G32 vectors into one, using sense weights as contributions.
    """
    combined = [0.0]*32
    total_w = 0.0
    for sense, token in tokens.items():
        w = max(0.0, min(1.0, weights.get(sense, 0.0)))
        if w <= 0.0:
            continue
        total_w += w
        for i, val in enumerate(token.vec):
            combined[i] += w * val
    if total_w > 0:
        combined = [v/total_w for v in combined]
    return combined


# ============================================================
# Public API
# ============================================================

def virtual_senses_from_text(text: str, topic: Optional[str] = None) -> Dict[str, G32Token]:
    """
    Given a text input, return a dict of G32 tokens keyed by sense:
      { 'auditory': G32Token, 'emotional': G32Token, ... }

    This is the core "virtual sensory excitation" stage.
    """
    sense_weights = detect_sensory_cues(text)
    out: Dict[str, G32Token] = {}

    for sense, weight in sense_weights.items():
        if weight <= 0.0:
            continue
        token = build_g32_for_sense(text, sense=sense, topic=topic)
        # annotate sense-specific weight
        token.meta.setdefault("sense_weight", weight)
        token.meta.setdefault("sense_name", sense)
        out[sense] = token

    return out


def build_mosaic_from_text(text: str, topic: Optional[str] = None) -> VirtualMosaic:
    """
    Turn raw text into a VirtualMosaic composed of multiple G32 tokens (one per sense).
    """
    tokens = virtual_senses_from_text(text, topic=topic)
    if not tokens:
        # fallback: at least something
        tokens = {"auditory": build_g32_for_sense(text, "auditory", topic=topic)}

    sense_weights = {k: t.meta.get("sense_weight", 0.5) for k, t in tokens.items()}
    combined_vec = combine_tokens_weighted(tokens, sense_weights)

    # Build mosaic meta
    all_uncertainties = [t.meta.get("uncertainty", 0.5) for t in tokens.values()]
    avg_uncertainty = sum(all_uncertainties)/len(all_uncertainties) if all_uncertainties else 0.5

    mosaic_meta = {
        "senses": list(tokens.keys()),
        "sense_weights": sense_weights,
        "uncertainty": avg_uncertainty,
        "topic": topic,
        "timestamp": time.time()
    }

    return VirtualMosaic(tokens=tokens, combined_vec=combined_vec, meta=mosaic_meta)


def describe_mosaic(mos: VirtualMosaic) -> str:
    """
    Return a human-readable description of a VirtualMosaic for debugging / introspection.
    """
    senses = mos.meta.get("senses", [])
    sense_weights = mos.meta.get("sense_weights", {})
    uncertainty = mos.meta.get("uncertainty", 0.5)
    topic = mos.meta.get("topic") or "unknown"

    parts = []
    parts.append(f"Senses active: {', '.join(senses)}")
    parts.append("Weights: " + ", ".join(f"{s}={sense_weights.get(s,0.0):.2f}" for s in senses))
    parts.append(f"Overall uncertainty: {uncertainty:.2f}")
    parts.append(f"Topic: {topic}")
    return " | ".join(parts)


# ============================================================
# Optional CLI for testing
# ============================================================

if __name__ == "__main__":
    print("Aurelion Virtual Senses — quick test mode.")
    while True:
        try:
            t = input("You (type text, 'quit' to exit): ").strip()
        except EOFError:
            break
        if not t:
            continue
        if t.lower() in ("quit","exit"):
            break
        mosaic = build_mosaic_from_text(t)
        print(describe_mosaic(mosaic))
        print("combined_vec (first 8 dims):", [round(x,3) for x in mosaic.combined_vec[:8]])
        print()
