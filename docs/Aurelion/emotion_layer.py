
from __future__ import annotations
import json, time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from modules.affective_mapper import AffectiveMapper
from modules.emotion_reflector import EmotionReflector, Tone

@dataclass
class EmotionState:
    valence: float
    arousal: float
    tags: List[str]
    confidence: float
    source: str
    explanation: str = ""
    timestamp: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp or time.strftime("%Y-%m-%dT%H:%M:%S")
        return d

class EmotionEngine:
    """Drop-in emotional layer for Aurelion v6.1.
    Responsibilities:
      - infer affect from user text
      - decay and smooth state between turns
      - blend system tone with user tone
      - produce meta summary for the Self-Explaining layer
    """
    def __init__(self, config_path: str = "config_emotion.json"):
        with open(config_path,"r",encoding="utf-8") as f:
            self.cfg: Dict[str, Any] = json.load(f)
        self.mapper = AffectiveMapper()
        self.reflector = EmotionReflector(self.cfg)
        self.state = EmotionState(0.0, 0.25, [], 0.5, source="system", explanation="initialized calm")
        self.history: List[Dict[str, Any]] = []

    def _decay(self, v: float, a: float) -> (float, float):
        # simple per-turn decay toward (0,0.25)
        half_life = max(1, self.cfg["decay"]["half_life_turns"])
        factor = 0.5 ** (1/half_life)
        v *= factor
        a = (a - 0.25) * factor + 0.25
        return v, a

    def update_from_text(self, user_text: str) -> EmotionState:
        prev = self.state
        dv, da, tags = self.mapper.analyze(user_text)
        # confidence heuristic proportional to arousal magnitude and tag hits
        confidence = min(1.0, 0.4 + 0.1*len(tags) + 0.3*abs(da) + 0.2*abs(dv))
        v = max(-1.0, min(1.0, prev.valence + dv))
        a = max(0.0, min(1.0, prev.arousal + da))
        v, a = self._decay(v, a)
        explanation = f"from text cues {tags or ['neutral']} (Δv={dv:.2f}, Δa={da:.2f}, decay applied)"
        self.state = EmotionState(v, a, tags, confidence, source="user", explanation=explanation)
        self._persist("user_update", prev, self.state)
        return self.state

    def blend_with_system_tone(self, system_target: Tone) -> Tone:
        user_tone = Tone(self.state.valence, self.state.arousal, label="user")
        blended = self.reflector.blend(user_tone, system_target)
        # safety: limit per-turn shift
        max_shift = self.cfg["safety"]["max_shift_per_turn"]
        dv = max(-max_shift, min(max_shift, blended.valence - self.state.valence))
        da = max(-max_shift, min(max_shift, blended.arousal - self.state.arousal))
        final = Tone(self.state.valence + dv, self.state.arousal + da, blended.label)
        self._persist("blend", self.state, asdict(final))
        return final

    def meta_summary(self, intent: str, tone: Tone) -> Dict[str, Any]:
        label = tone.label
        tone_shift = abs(tone.valence - self.state.valence) + abs(tone.arousal - self.state.arousal)
        return {
            "intent": intent,
            "confidence": round(self.state.confidence, 2),
            "explain": f"Applied emotional blend → {label}; tone_shift={tone_shift:.2f}; tags={self.state.tags}",
            "emotion": self.state.to_dict(),
            "tone_shift": round(min(1.0, tone_shift), 2),
            "tone_label": label
        }

    def _persist(self, kind: str, prev: Any, new: Any):
        record = {
            "kind": kind,
            "t": time.time(),
            "prev": prev if isinstance(prev, dict) else (prev.to_dict() if hasattr(prev, 'to_dict') else prev),
            "new": new if isinstance(new, dict) else (new.to_dict() if hasattr(new, 'to_dict') else new),
        }
        self.history.append(record)
        if len(self.history) > self.cfg["memory"]["persist_last_n"]:
            self.history.pop(0)
