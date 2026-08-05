"""grammar.py -- grammatical pattern encoding.

Produces grammatical_patterns entries per the dispatch's own breakdown:
  - verbs get subject-target and object-target coupling patterns
  - nouns get modifier-source patterns
  - question words get inversion couplings
  - tense markers get temporal-sequence couplings

Each pattern's chi_sequence is built from REAL representative words
already in the seeded vocabulary (picked by actual Universal Dependencies
usage frequency for the relevant UPOS role, via UDSource), not invented
placeholder chis -- every chi in a pattern resolves to a real vocabulary
entry. Patterns are emitted once per language organ (sf=H5, aff=H7 --
config.LANGUAGE_ORGANS), matching where vocabulary itself lives.

coupling_weights is left EMPTY for all generated patterns. Populating it
requires real neuron_id strings from one specific running organism's
CURRENT ring topology (CouplingsJij.neighbors) -- but neuron ids are not
fixed across an organism's lifetime (population growth/division adds
daughter neurons with new ids, per embryo.py's own conservation-pool
mechanism). A generic, source-driven seed file meant to load into
whichever organism state exists at load time cannot safely hardcode ids
that may not exist in that state. seed_loader.py already treats an
unresolvable neighbor id as skip-with-warning, not an error or a
fabricated relationship -- so an empty dict here is the honest choice,
not a shortcut. Flagged as a finding for Eve (a real coupling_weights
population would need to run against one specific live organism at
load/deploy time, out of scope for a generation-only dispatch).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from generator.language_seed import config

WH_WORDS = ["what", "who", "how", "which", "why", "where", "when"]
AUX_PRESENT = ["is", "are", "do", "does"]
AUX_PAST = ["was", "were", "did", "had"]
MODAL_FUTURE = ["will", "would", "should", "could"]


def _top_word_for_upos(upos: str, word_to_chi: Dict[str, int], ud_source,
                        exclude: Optional[set] = None) -> Optional[str]:
    exclude = exclude or set()
    best, best_count = None, 0
    for word, counts in ud_source.word_pos_counts.items():
        if word not in word_to_chi or word in exclude:
            continue
        c = counts.get(upos, 0)
        if c > best_count:
            best_count, best = c, word
    return best


def _first_present(candidates: List[str], word_to_chi: Dict[str, int]) -> Optional[str]:
    for w in candidates:
        if w in word_to_chi:
            return w
    return None


def _pattern(pattern_id: str, chi_sequence: List[int], organ: str) -> dict:
    return {
        "pattern_id": pattern_id,
        "chi_sequence": chi_sequence,
        "coupling_weights": {},
        "hemisphere": organ,
    }


def build_patterns(word_to_chi: Dict[str, int], ud_source) -> List[dict]:
    subject_word = _top_word_for_upos("PRON", word_to_chi, ud_source)
    verb_word = _top_word_for_upos("VERB", word_to_chi, ud_source)
    object_word = _top_word_for_upos("NOUN", word_to_chi, ud_source, exclude={subject_word})
    adj_word = _top_word_for_upos("ADJ", word_to_chi, ud_source)
    wh_word = _first_present(WH_WORDS, word_to_chi)
    aux_present = _first_present(AUX_PRESENT, word_to_chi)
    aux_past = _first_present(AUX_PAST, word_to_chi)
    modal_future = _first_present(MODAL_FUTURE, word_to_chi)

    patterns: List[dict] = []
    for organ in config.LANGUAGE_ORGANS:
        if subject_word and verb_word:
            patterns.append(_pattern(
                "subject_verb_target",
                [word_to_chi[subject_word], word_to_chi[verb_word]], organ))
        if verb_word and object_word:
            patterns.append(_pattern(
                "verb_object_target",
                [word_to_chi[verb_word], word_to_chi[object_word]], organ))
        if adj_word and object_word:
            patterns.append(_pattern(
                "noun_modifier_source",
                [word_to_chi[object_word], word_to_chi[adj_word]], organ))
        if wh_word and aux_present and subject_word:
            patterns.append(_pattern(
                "question_inversion",
                [word_to_chi[wh_word], word_to_chi[aux_present], word_to_chi[subject_word]], organ))
        if aux_past and verb_word:
            patterns.append(_pattern(
                "tense_temporal_sequence_past",
                [word_to_chi[aux_past], word_to_chi[verb_word]], organ))
        if modal_future and verb_word:
            patterns.append(_pattern(
                "tense_temporal_sequence_future",
                [word_to_chi[modal_future], word_to_chi[verb_word]], organ))

    return patterns
