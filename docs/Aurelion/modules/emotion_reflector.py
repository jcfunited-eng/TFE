
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass
class Tone:
    valence: float   # [-1, 1]
    arousal: float   # [0, 1]
    label: str

class EmotionReflector:
    """Blends user tone with model's target tone and applies stabilizing biases."""
    def __init__(self, config: Dict):
        self.cfg = config

    def _clamp(self, v, lo, hi):
        return max(lo, min(hi, v))

    def _label(self, v, a) -> str:
        if v > 0.4 and a < 0.4: return "warm-calm"
        if v > 0.4 and a >= 0.4: return "warm-bright"
        if v < -0.4 and a >= 0.5: return "cool-tense"
        if v < -0.2 and a < 0.4: return "cool-flat"
        if abs(v) < 0.2 and a < 0.3: return "neutral"
        return "balanced"

    def blend(self, user: Tone, system: Tone) -> Tone:
        m = self.cfg["blend"]["mirror_strength"]
        s = self.cfg["blend"]["stability_bias"]
        n = self.cfg["blend"]["novelty_bias"]

        # Start from system, mirror toward user
        v = system.valence * (1-m) + user.valence * m
        a = system.arousal * (1-m) + user.arousal * m

        # Stability bias toward neutral calm
        v = v * (1 - s)
        a = a * (1 - s) + 0.2 * s

        # Small novelty: nudge away from exact neutrality
        v += (0.1 if v >= 0 else -0.1) * n
        a += 0.05 * n

        # Safety clamps
        if user.valence < -0.5 and user.arousal > 0.6:
            a = min(a, self.cfg["safety"]["clamp_aggression"])
            v = max(v, self.cfg["safety"]["negative_valence_floor"])

        v = self._clamp(v, -1.0, 1.0)
        a = self._clamp(a, 0.0, 1.0)
        return Tone(v, a, self._label(v, a))
