"""affect.py -- affect associations.

For each word, valence (-1..+1), arousal (0..1), dominance (0..1).
Direct lexicon coverage (NRC-VAD primary, Warriner fallback, NRC Emotion
Lexicon polarity as a weak tertiary signal) for the RICH layer only --
dispatch: programmatic layer gets "affect via inheritance only," so
programmatic entries never consult the lexicons directly, only neighbor
inheritance. Words with no direct coverage and no resolved neighbors fall
back to a neutral default (0.0, 0.5, 0.5), counted and reported (not
silently produced as if it were real signal).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

NEUTRAL_DEFAULT = (0.0, 0.5, 0.5)


def _from_nrc_vad(vad) -> Tuple[float, float, float]:
    v, a, d = vad
    return (v * 2.0 - 1.0, a, d)  # NRC-VAD is 0..1 on all three; rescale valence only


def _from_warriner(w) -> Tuple[float, float, float]:
    v, a, d = w  # 1..9 SAM scale
    return ((v - 5.0) / 4.0, (a - 1.0) / 8.0, (d - 1.0) / 8.0)


def _from_nrc_emotion(flags: dict) -> Optional[Tuple[float, float, float]]:
    pos, neg = flags.get("positive", 0), flags.get("negative", 0)
    if pos == neg:
        return None  # no net polarity signal
    valence = 0.5 if pos else -0.5
    high_arousal = any(flags.get(k, 0) for k in ("anger", "fear", "surprise", "joy"))
    arousal = 0.65 if high_arousal else 0.4
    dominance = 0.6 if flags.get("anger") or flags.get("trust") else 0.45
    return (valence, arousal, dominance)


def resolve_direct(word: str, nrc_vad_source, warriner_source, nrc_emotion_source
                    ) -> Optional[Tuple[float, float, float, str]]:
    vad = nrc_vad_source.lookup(word)
    if vad is not None:
        v, a, d = _from_nrc_vad(vad)
        return (v, a, d, "nrc_vad")
    warr = warriner_source.lookup(word)
    if warr is not None:
        v, a, d = _from_warriner(warr)
        return (v, a, d, "warriner")
    flags = nrc_emotion_source.lookup(word)
    if flags is not None:
        result = _from_nrc_emotion(flags)
        if result is not None:
            v, a, d = result
            return (v, a, d, "nrc_emotion")
    return None


class AffectResolver:
    """Stateful: chi_affect fills in as words resolve (in generation order),
    so inheritance can draw on both earlier-in-run and cross-layer
    neighbors, not just a fixed pre-pass."""

    def __init__(self, nrc_vad_source, warriner_source, nrc_emotion_source):
        self.nrc_vad = nrc_vad_source
        self.warriner = warriner_source
        self.nrc_emotion = nrc_emotion_source
        self.chi_affect: Dict[int, Tuple[float, float, float]] = {}
        self.defaulted_count = 0
        self.source_counts: Dict[str, int] = {}

    def _inherit(self, related_chis: List[dict]) -> Optional[Tuple[float, float, float]]:
        if not related_chis:
            return None
        scored = []
        for rel in related_chis:
            affect = self.chi_affect.get(rel["chi"])
            if affect is not None:
                scored.append((rel["strength"], affect))
        if not scored:
            return None
        scored.sort(key=lambda x: -x[0])
        top = scored[:3]
        total_w = sum(s for s, _ in top) or 1.0
        v = sum(s * a[0] for s, a in top) / total_w
        a_ = sum(s * a[1] for s, a in top) / total_w
        d = sum(s * a[2] for s, a in top) / total_w
        return (v, a_, d)

    def resolve(self, word: str, chi: int, tier: str,
                related_chis: Optional[List[dict]]) -> Tuple[float, float, float, str]:
        result = None
        source = None

        if tier == "rich":
            direct = resolve_direct(word, self.nrc_vad, self.warriner, self.nrc_emotion)
            if direct is not None:
                v, a, d, source = direct
                result = (v, a, d)

        if result is None:
            inherited = self._inherit(related_chis or [])
            if inherited is not None:
                result = inherited
                source = "inherited"

        if result is None:
            result = NEUTRAL_DEFAULT
            source = "default"
            self.defaulted_count += 1

        self.source_counts[source] = self.source_counts.get(source, 0) + 1
        self.chi_affect[chi] = result
        return (result[0], result[1], result[2], source)
