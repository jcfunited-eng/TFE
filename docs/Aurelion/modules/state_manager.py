
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from modules.emotion_reflector import Tone

@dataclass
class SystemToneTarget:
    valence: float = 0.2
    arousal: float = 0.3
    label: str = "supportive"

    def to_tone(self) -> Tone:
        return Tone(self.valence, self.arousal, self.label)
