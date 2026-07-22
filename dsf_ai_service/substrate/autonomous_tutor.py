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

# ── GL-CMD-TUTOR-JUNK-GATE-20260722 (open item since 07-18) ──────────────
# The tutor drills from _GAP_ARCHIVE — her real reading — but world feeds
# and book headers leak navigation junk into that archive ("Home About
# Contact", "CHAPTER XII", "www.gutenberg.org terms of use").  Automated
# teaching must not quiz her on garbage.  This gate is a SOURCE-QUALITY
# filter on drill material only: it decides what the tutor may quiz from,
# it never touches what she reads (intake is untouched).  All rules are
# simple, deterministic string checks — no models, no randomness.

# Substrings that mark URL / web-navigation fragments.
_URL_MARKERS = ("http://", "https://", "www.", "://")
# "gutenberg.org", "index.html": a letter/digit, a dot, then 2+ letters.
# Ordinary sentence-final periods ("sat. the") never match (space after dot).
_DOMAIN_RE = re.compile(r"[a-z0-9]\.[a-z]{2,}")
# A token made entirely of capital letters, length >= 2 ("CHAPTER", "XII").
_ALLCAPS_RE = re.compile(r"^[A-Z]{2,}$")

# Closed set of structure words (articles / pronouns / prepositions /
# conjunctions / common prose adverbs).  Real 4-12-word prose essentially
# always contains one; navigation menus and boilerplate lists essentially
# never do.
_FUNCTION_WORDS = frozenset((
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
    "with", "for", "from", "by", "as", "that", "this", "these", "those",
    "it", "its", "he", "she", "they", "we", "you", "i", "her", "his",
    "their", "our", "your", "my", "me", "him", "them", "us", "who",
    "what", "when", "where", "so", "if", "then", "than", "there", "here",
    "not", "no", "up", "down", "out", "into", "over", "under", "through",
    "together", "away", "very", "too", "also", "again", "always", "never",
))

# Verb evidence, part 1: closed set — be/have/do forms, modals, and the
# frequent irregular verbs of children's prose (which carry no -ed/-ing).
_VERB_WORDS = frozenset((
    "is", "are", "was", "were", "am", "be", "been", "being",
    "has", "have", "had", "do", "does", "did",
    "will", "would", "can", "could", "shall", "should", "may", "might",
    "must",
    "said", "sat", "ran", "went", "came", "saw", "made", "got", "took",
    "put", "held", "felt", "knew", "found", "gave", "told", "heard",
    "thought", "let", "met", "set", "stood", "ate", "fell", "flew",
    "grew", "slept", "spoke", "wrote", "won", "kept", "began", "brought",
    "sang", "sent", "wore", "threw", "swam", "rose", "lay",
))


def _has_verb_evidence(tokens):
    """Verb-like structure, deterministically, from the ORIGINAL tokens:
    a closed-set verb form, an -ed/-ing inflection, or a lowercase
    third-person -s form ("shines", "purrs", "laughs").  The -s rule is
    weak (plural nouns match too) so it (a) only counts when the token is
    written lowercase — prose verbs are; Title-Case nav nouns ("Products
    Services") are not — and (b) is_quality_material ALSO requires a
    function word."""
    for t in tokens:
        raw = t.strip("*.,:;!?()[]\"'")
        w = raw.lower()
        if not w.isalpha():
            continue
        if w in _VERB_WORDS:
            return True
        if len(w) >= 4 and (w.endswith("ed") or w.endswith("ing")):
            return True
        if (raw == w and len(w) >= 4 and w.endswith("s")
                and not w.endswith(("ss", "us", "is"))):
            return True
    return False


def is_quality_material(sentence):
    """True iff a sentence is fit to DRILL from (quality rules only — the
    existing 4-12 word window stays enforced where it already lives).
    Rejection rules, in order, each deterministic:
      R1  mostly-non-alpha   — letters < 70% of non-space characters
      R2  URL/domain junk    — http/www/:// or a domain-shaped token
      R3  ALL-CAPS runs      — 2+ consecutive ALL-CAPS tokens, or ALL-CAPS
                               tokens making up half or more of the tokens
      R4  repeated boilerplate — any non-function word appearing 3+ times
      R5  no sentence structure — must contain at least one function word
                               AND at least one verb-evidence token
    """
    text = str(sentence or "").strip()
    if not text:
        return False
    # R1: mostly-non-alpha (separators, ascii art, "= = = =", markup).
    non_space = [c for c in text if not c.isspace()]
    if not non_space:
        return False
    alpha = sum(1 for c in non_space if c.isalpha())
    if alpha < 0.7 * len(non_space):
        return False
    low = text.lower()
    # R2: URL / domain fragments.
    if any(m in low for m in _URL_MARKERS) or _DOMAIN_RE.search(low):
        return False
    # R3: ALL-CAPS runs (headers, "*** START OF ... EBOOK ***", shouting nav).
    tokens = text.split()
    caps = [bool(_ALLCAPS_RE.match(t.strip("*.,:;!?()[]\"'"))) for t in tokens]
    if any(a and b for a, b in zip(caps, caps[1:])):
        return False
    if tokens and sum(caps) * 2 >= len(tokens):
        return False
    # R4: repeated boilerplate ("next next next", "menu menu menu search").
    words = _words(text)
    counts = {}
    for w in words:
        if w not in _FUNCTION_WORDS:
            counts[w] = counts.get(w, 0) + 1
            if counts[w] >= 3:
                return False
    # R5: no verb-like structure (nav menus, tag clouds, link lists).
    # Structure = a function word OR a closed-set verb form ("guala is
    # loved" has no article, but "is" is real structure); verb evidence
    # is checked separately so "click here to subscribe" (structure, no
    # verb form) still rejects.
    if not any(w in _FUNCTION_WORDS or w in _VERB_WORDS for w in words):
        return False
    if not _has_verb_evidence(tokens):
        return False
    return True


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

    GL-CMD-TUTOR-JUNK-GATE-20260722: drill material passes the source-
    quality gate (is_quality_material) before EITHER path may pick it —
    the tutor never quizzes on navigation junk, headers, or boilerplate.
    """
    archive = [s for s in archive_sentences if s and is_quality_material(s)]
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
    sw = _words(sent)
    # GL-CMD-SYNTAX-TUTOR-20260718: rotate the stem CUT as well as the
    # sentence, so successor statistics get teaching pressure at every
    # position — order drilling, not just first-word recall.
    n = len(sw)
    lo, hi = 2, min(MAX_STEM_WORDS, n - 1)
    cut = lo + (rotation // max(1, len(eligible))) % max(1, hi - lo + 1)
    if cut >= n:
        return None
    return {"stem": " ".join(sw[:cut]),
            "expected": " ".join(sw[cut:]),
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


def judge_attempt_detail(attempt_text, expected_text):
    """GL-CMD-SYNTAX-TUTOR-20260718 (Joe: "syntax guidance as well as
    grading"): classify the attempt so the correction can target WORD
    ORDER, not just word choice.

    verdicts:
      correct           — began the true continuation
      wrong_order       — she has the right words but scrambled: half or
                          more of the expected words appear in her attempt,
                          yet it does not begin correctly.  This is a
                          SYNTAX failure, not a vocabulary failure.
      wrong             — everything else (silence included)
    """
    attempt = _words(attempt_text)
    expected = _words(expected_text)
    if not expected or not attempt:
        return {"verdict": "wrong", "overlap": 0}
    overlap = len(set(attempt) & set(expected))
    # Position-exact for syntax: "correct" means the continuation BEGINS
    # correctly — stricter than judge_attempt's vocabulary-era leniency
    # (expected word merely somewhere in her first three).
    if attempt[0] == expected[0]:
        return {"verdict": "correct", "overlap": overlap}
    if expected[0] in attempt[:3] or overlap * 2 >= len(expected):
        return {"verdict": "wrong_order", "overlap": overlap}
    return {"verdict": "wrong", "overlap": overlap}
