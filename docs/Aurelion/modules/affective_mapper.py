
from __future__ import annotations
import re
from typing import Dict, Tuple, List

class AffectiveMapper:
    """Lightweight lexical→affect mapper.
    Produces (valence, arousal) deltas and tags based on words/emoji/punctuation.
    This is intentionally simple, fast, and deterministic for a plugin layer.
    """
    def __init__(self) -> None:
        # Base lexicon: valence in [-1,1], arousal in [0,1]
        self.lexicon: Dict[str, Tuple[float, float, str]] = {
            "love": (0.7, 0.5, "warmth"),
            "like": (0.4, 0.3, "affinity"),
            "thanks": (0.4, 0.4, "gratitude"),
            "great": (0.5, 0.5, "admire"),
            "wow": (0.3, 0.6, "surprise"),
            "amazing": (0.6, 0.6, "admire"),
            "hug": (0.6, 0.4, "comfort"),
            "calm": (0.3, 0.2, "soothe"),
            "patient": (0.3, 0.2, "stability"),
            "kind": (0.5, 0.3, "prosocial"),
            "safe": (0.4, 0.2, "safety"),
            "sad": (-0.6, 0.3, "sadness"),
            "sorry": (-0.2, 0.4, "remorse"),
            "angry": (-0.8, 0.8, "anger"),
            "frustrated": (-0.6, 0.6, "frustration"),
            "anxious": (-0.4, 0.7, "anxiety"),
            "fear": (-0.7, 0.8, "fear"),
            "hurt": (-0.5, 0.6, "hurt"),
            "hate": (-0.9, 0.7, "hostility"),
            "stop": (-0.2, 0.5, "boundary"),
            "please": (0.2, 0.3, "polite"),
            "question": (0.0, 0.2, "curiosity"),
            "!!": (0.1, 0.4, "emphasis"),
            "!!!": (0.0, 0.6, "intensity"),
            "?!": (-0.1, 0.5, "confusion"),
            ":)": (0.4, 0.3, "smile"),
            ":D": (0.6, 0.5, "joy"),
            "<3": (0.6, 0.4, "affection"),
            "😃": (0.7, 0.6, "joy"),
            "😞": (-0.6, 0.3, "sadness"),
            "😠": (-0.7, 0.7, "anger"),
            "😭": (-0.7, 0.6, "grief"),
            "😅": (0.2, 0.5, "nervous_laugh")
        }
        # Regex shortcuts for fast punctuation cues
        self.exclaim_re = re.compile(r"!{2,}")
        self.qe_re = re.compile(r"\?!")

    def analyze(self, text: str) -> Tuple[float, float, List[str]]:
        text_l = text.lower()
        v_delta, a_delta = 0.0, 0.0
        tags: List[str] = []
        tokens = re.findall(r"[\w<:;)(D3]+|\S", text_l)
        for t in tokens:
            if t in self.lexicon:
                dv, da, tag = self.lexicon[t]
                v_delta += dv
                a_delta += da
                tags.append(tag)
        # punctuation regex
        if self.exclaim_re.search(text_l):
            v_delta += 0.05
            a_delta += 0.2
            tags.append("excited")
        if self.qe_re.search(text_l):
            v_delta -= 0.05
            a_delta += 0.15
            tags.append("confused")
        # normalize rough scale to [-1,1] x [0,1]
        v_delta = max(-1.0, min(1.0, v_delta))
        a_delta = max(0.0,  min(1.0, a_delta))
        return v_delta, a_delta, tags
