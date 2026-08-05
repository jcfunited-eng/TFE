"""semantic_net.py -- semantic network builder.

For each word, generate its associated chi neighborhood from WordNet
(synonym/hypernym/hyponym) + ConceptNet edges. Each association carries a
strength in [0, 1] from relation-type weight; when both sources agree on
an edge the stronger of the two wins. Only edges landing on another
SEEDED word (one with an assigned chi) are kept -- the dispatch's own
integrity rule ("All semantic net edges point to seeded entries").

applies_to_hemispheres is set to the language organs (sf, aff -- see
config.LANGUAGE_ORGANS / H5+H7 per topology.py) since these are word-level
associative links, living where the vocabulary itself lives.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from generator.language_seed import config

WORDNET_RELATION_WEIGHTS = {
    "synonym": 0.9,
    "hypernym": 0.75,
    "hyponym": 0.65,
}

MAX_RELATED_PER_WORD = 20


def build_semantic_network(word: str, chi: int, wn_entry, cn_edges,
                            word_to_chi: Dict[str, int]) -> Optional[dict]:
    candidates: Dict[str, float] = {}  # other_word -> strength

    if wn_entry is not None:
        for other in wn_entry.synonyms:
            if other in word_to_chi:
                candidates[other] = max(candidates.get(other, 0.0), WORDNET_RELATION_WEIGHTS["synonym"])
        for other in wn_entry.hypernyms:
            if other in word_to_chi:
                candidates[other] = max(candidates.get(other, 0.0), WORDNET_RELATION_WEIGHTS["hypernym"])
        for other in wn_entry.hyponyms:
            if other in word_to_chi:
                candidates[other] = max(candidates.get(other, 0.0), WORDNET_RELATION_WEIGHTS["hyponym"])

    for relation, other, weight in cn_edges:
        if other == word or other not in word_to_chi:
            continue
        candidates[other] = max(candidates.get(other, 0.0), weight)

    candidates.pop(word, None)
    if not candidates:
        return None

    ranked = sorted(candidates.items(), key=lambda kv: -kv[1])[:MAX_RELATED_PER_WORD]
    related_chis: List[dict] = [
        {"chi": word_to_chi[other], "strength": round(strength, 4)}
        for other, strength in ranked
    ]

    return {
        "center_chi": chi,
        "related_chis": related_chis,
        "applies_to_hemispheres": list(config.LANGUAGE_ORGANS),
    }


def build_minimal_anchor(word: str, chi: int, wn_entry,
                          rich_word_to_chi: Dict[str, int]) -> Optional[dict]:
    """Programmatic layer: "just the primary synset link" -- at most one
    related_chi, the primary sense's direct hypernym, and only if that
    hypernym is itself a rich-tier word (guaranteed loaded before any
    programmatic entry, since rich loads blocking-first)."""
    if wn_entry is None or not wn_entry.primary_hypernym:
        return None
    target = wn_entry.primary_hypernym
    if target not in rich_word_to_chi:
        return None
    return {
        "center_chi": chi,
        "related_chis": [{"chi": rich_word_to_chi[target],
                           "strength": WORDNET_RELATION_WEIGHTS["hypernym"]}],
        "applies_to_hemispheres": list(config.LANGUAGE_ORGANS),
    }
