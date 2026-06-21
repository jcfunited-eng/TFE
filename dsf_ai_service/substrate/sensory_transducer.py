"""
sensory_transducer.py — Substrate-true sensory parameter generation.

GL-CMD-F1-SENSORY-TRANSDUCER-EVE-20260621-107

Replaces TOUCH_LIBRARY / SMELL_LIBRARY / TASTE_LIBRARY fixed dicts.
Parameters are discovered from substrate state, not pre-assigned by label.

First encounter: uniform random sample in physical range [0, 1] per channel.
Subsequent encounters: sample from distribution of prior atlas bindings.

NO label-keyed branches. NO fixed defaults. NO "warm should be higher temperature."
The substrate learns what "warm" FEELS like through exposure, not pre-programming.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Protocol


# ---------------------------------------------------------------------------
# AtlasReader protocol — read-only interface to whichever atlas is in scope
# ---------------------------------------------------------------------------

class AtlasReader(Protocol):
    """Protocol for reading prior sensory bindings from an atlas."""

    def has_bindings(self, label: str, modality: str) -> bool:
        """Return True if atlas has prior parameter bindings for (label, modality)."""
        ...

    def get_binding_params(self, label: str, modality: str) -> List[Dict[str, float]]:
        """Return list of prior parameter dicts for (label, modality).

        Each dict maps channel_name → float value from a prior transduce call.
        """
        ...


class NullAtlasReader:
    """Atlas reader that reports no prior bindings (every encounter is first).

    Used when no atlas is available or atlas integration is deferred.
    """

    def has_bindings(self, label: str, modality: str) -> bool:
        return False

    def get_binding_params(self, label: str, modality: str) -> List[Dict[str, float]]:
        return []


# ---------------------------------------------------------------------------
# Channel definitions per modality — physical ranges only
# ---------------------------------------------------------------------------

TOUCH_CHANNELS = ("temperature", "pressure", "texture_freq", "sharpness", "wetness")
SMELL_CHANNELS = ("sweet", "putrid", "floral", "fruity", "smoky", "earthy", "sour", "fresh")
TASTE_CHANNELS = ("sweet", "sour", "salty", "bitter", "umami")
VISUAL_CHANNELS = ("dominant_hue", "saturation", "brightness", "spatial_complexity", "motion")
SOUND_CHANNELS = ("fundamental_freq", "harmonic_richness", "amplitude", "duration_class")

MODALITY_CHANNELS = {
    "touch": TOUCH_CHANNELS,
    "smell": SMELL_CHANNELS,
    "taste": TASTE_CHANNELS,
    "visual": VISUAL_CHANNELS,
    "sound": SOUND_CHANNELS,
}


# ---------------------------------------------------------------------------
# SensoryTransducer
# ---------------------------------------------------------------------------

class SensoryTransducer:
    """Substrate-true sensory parameter generator.

    Replaces static label-to-parameter lookup tables. Parameters are either:
    - Sampled uniformly (first encounter, no prior bindings)
    - Sampled from distribution of prior bindings (subsequent encounters)

    Deterministic within a session: same (label, modality, tick) → same params.
    Different ticks → different params (exploration across encounters).
    """

    def __init__(self, atlas_reader: Optional[Any] = None):
        self.atlas_reader = atlas_reader or NullAtlasReader()

    def transduce(self, modality: str, label: str, tick: int) -> Dict[str, float]:
        """Generate physical parameters for a sensory experience.

        Args:
            modality: one of "touch", "smell", "taste", "visual", "sound"
            label: the descriptor (e.g., "warm", "floral", "sweet")
            tick: substrate tick (provides temporal variation)

        Returns:
            dict mapping channel_name → float ∈ [0, 1]
        """
        if modality not in MODALITY_CHANNELS:
            raise ValueError(f"unknown modality: {modality}")

        if self.atlas_reader.has_bindings(label, modality):
            return self._sample_from_bindings(label, modality, tick)
        return self._generate_initial(label, modality, tick)

    def _generate_initial(self, label: str, modality: str, tick: int) -> Dict[str, float]:
        """First encounter: uniform sample in [0, 1] per channel.

        Seed is deterministic from (label, modality, tick) so replay works.
        """
        seed = hash((label, modality, tick)) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        channels = MODALITY_CHANNELS[modality]
        return {ch: float(rng.uniform(0.0, 1.0)) for ch in channels}

    def _sample_from_bindings(self, label: str, modality: str, tick: int) -> Dict[str, float]:
        """Subsequent encounter: sample from distribution of prior bindings."""
        prior_params = self.atlas_reader.get_binding_params(label, modality)
        distribution = self._compute_distribution(prior_params)
        seed = hash((label, modality, tick)) & 0xFFFFFFFF
        rng = np.random.default_rng(seed)
        channels = MODALITY_CHANNELS[modality]
        params = {}
        for ch in channels:
            mean = distribution[ch]["mean"]
            std = distribution[ch]["std"]
            val = float(rng.normal(mean, std))
            params[ch] = max(0.0, min(1.0, val))
        return params

    def _compute_distribution(self, prior_params: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Compute per-channel mean and std from prior binding params."""
        if not prior_params:
            return {}
        all_channels = set()
        for p in prior_params:
            all_channels.update(p.keys())

        dist = {}
        for ch in all_channels:
            values = [p.get(ch, 0.5) for p in prior_params]
            dist[ch] = {
                "mean": float(np.mean(values)),
                "std": max(float(np.std(values)), 0.01),  # floor to prevent collapse
            }
        return dist
