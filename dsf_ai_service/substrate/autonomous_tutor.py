"""autonomous_tutor.py — the teach → ask → correct loop, automated.

GL-CMD-AUTOMATED-TEACHING-20260717.  This module holds the tutor's PURE
logic (item selection, stem/expected split, verdict) so it is unit-testable
without booting the engine.  The runner's interleave slot supplies the live
pieces: her real converse() answer path and the real teacher gateway
(apply_teacher_correction, source="curriculum").

Substrate-true boundaries (NO COMMUNICATION CHEATS):
  - The tutor is ENVIRONMENT speaking TO her — exactly like Joe typing a
    question.  Her answers come only from her own emission path (certified
    strand, or honest organism babble, or silence).
  - Verdicts are graded by REALITY: the expected continuation is the actual
    next words of a sentence from her own reading life, never a model's
    opinion of a good answer.
  - Corrections flow through the one real teacher gateway with
    source="curriculum" — permanent like Joe's but weighted below him
    (source weight 0.7 vs 1.6): a parent's word outranks a textbook's.
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z]+")

# A tutor item needs enough words for a meaningful stem and a real
# continuation, and short enough to be one honest exchange.
MIN_SENTENCE_WORDS = 4
MAX_SENTENCE_WORDS = 12
MAX_STEM_WORDS = 6


def _words(text):
    return _WORD_RE.findall(str(text or "").lower())


def split_stem(sentence_words, gap_word=None):
    """Split a sentence into (stem_words, expected_words).

    With a gap word present at position >= 2, the stem is everything
    before it and the expected continuation starts AT the gap word —
    the ask literally walks her up to the missing word.  Otherwise the
    expected continuation is the final third (at least one word).
    Returns None if no valid split exists.
    """
    n = len(sentence_words)
    if n < MIN_SENTENCE_WORDS or n > MAX_SENTENCE_WORDS:
        return None
    if gap_word:
        gw = str(gap_word).lower()
        for i, w in enumerate(sentence_words):
            if w == gw and 2 <= i <= MAX_STEM_WORDS:
                return sentence_words[:i], sentence_words[i:]
    cut = max(2, min(MAX_STEM_WORDS, n - max(1, n // 3)))
    if cut >= n:
        return None
    return sentence_words[:cut], sentence_words[cut:]


def pick_tutor_item(gap_words, archive_sentences, rotation=0):
    """Choose one exchange: {stem, expected, sentence, gap_word|None}.

    Gap-targeted first: the earliest top-gap word that appears mid-sentence
    in her own reading archive.  Fallback: rotate through the archive so
    repeated slots quiz different sentences, not the same one forever.
    """
    archive = [s for s in archive_sentences if s]
    for gw in gap_words or ():
        for sent in archive:
            sw = _words(sent)
            split = split_stem(sw, gap_word=gw)
            if split and split[1] and split[1][0] == str(gw).lower():
                return {"stem": " ".join(split[0]),
                        "expected": " ".join(split[1]),
                        "sentence": sent, "gap_word": gw}
    eligible = [s for s in archive
                if MIN_SENTENCE_WORDS <= len(_words(s)) <= MAX_SENTENCE_WORDS]
    if not eligible:
        return None
    sent = eligible[rotation % len(eligible)]
    split = split_stem(_words(sent))
    if not split:
        return None
    return {"stem": " ".join(split[0]),
            "expected": " ".join(split[1]),
            "sentence": sent, "gap_word": None}


def judge_attempt(attempt_text, expected_text):
    """Reality-graded verdict: did her attempt begin the true continuation?

    Correct iff the first expected word appears within the first three
    words of her attempt.  Silence is always incorrect (and still
    teachable: the gateway ingests the expected continuation).
    """
    attempt = _words(attempt_text)
    expected = _words(expected_text)
    if not expected:
        return False
    return bool(attempt) and expected[0] in attempt[:3]
