"""grounding.py -- cross-modal grounding generation.

For each word, determine which of the substrate's REAL sensory modalities
(visual, auditory, tactile, olfactory, gustatory -- topology.py's
HEMISPHERE_PRIMARY_MODALITY; there is no "kinesthetic" hemisphere, see
note below) it can ground through, and which chi address to reference for
that modality.

Grounding chi choice: the word's OWN chi. This generator produces purely
symbolic/relational data -- no images, audio, or other non-text sensory
content exists to build separate "picture of X" entries from (and doing
so would require either hand-authored content or an ML-derived
embedding, both explicitly out of scope). The substrate's own binding
mechanism (ChiAtlas/WaveAtlas: "Binds events across modal + word + role
krimelacks within chi-band delta") is what actually produces cross-modal
grounding at runtime -- it works by multiple modality *sections* recording
commits at the SAME chi. Writing a word into the visual/auditory/tactile/
etc. wave_atlas sections at its own chi (in addition to the "modifier"
section every vocabulary entry already gets from seed_loader) is that
mechanism working as designed, not a workaround. This also trivially
satisfies the dispatch's own validation requirement ("All grounding chi
references point to real seeded entries") -- the reference IS the entry.

Modality assignment rules (dispatch: "Concrete nouns get visual + often
auditory (via phonetic rep). Motion verbs get visual + kinesthetic.
Sensory adjectives get their specific modality. Abstract words return
empty grounding."):
  - concrete noun (WordNet physical_entity descendant, or ImageNet-
    synset-aligned) -> visual, plus auditory IF a CMU pronunciation exists
  - sound/communication-primary-sense word -> auditory (if CMU entry exists)
  - motion verb (primary_lexname == 'verb.motion') -> visual + tactile.
    FINDING: the dispatch's own "kinesthetic" has no substrate hemisphere
    (topology.py's 5 real sensory hemispheres are visual/auditory/tactile/
    olfactory/gustatory only) -- tactile is the nearest real modality
    (proprioception/kinesthesia is conventionally grouped with the touch
    family), used as a substitution, not a literal kinesthetic channel.
  - sensory adjective (touch/smell/taste anchor match, direct or via
    WordNet synonymy / ConceptNet Synonym|SimilarTo propagation from a
    small curated anchor list per modality -- explicitly named as a
    source in the dispatch: "ConceptNet HasProperty edges + curated
    adjective lists per modality") -> ONLY that specific modality,
    overriding any broader default
  - everything else (abstract nouns, non-motion verbs, function words,
    etc.) -> empty grounding; they ground through semantic-net coupling
    to concrete anchors instead, per the dispatch's own design intent
"""

from __future__ import annotations

from typing import Dict, Optional, Set

from generator.language_seed import config

# Small, closed, canonical sensory-adjective anchor sets -- classification
# anchors used to detect which modality a sensory adjective belongs to,
# not hand-authored vocabulary content (the vocabulary itself comes
# entirely from WordNet/SCOWL). Standard linguistic sensory-modality
# adjective classes.
SENSORY_ANCHORS = {
    "tactile": {
        "rough", "smooth", "soft", "hard", "wet", "dry", "sticky",
        "slippery", "bumpy", "sharp", "blunt", "cold", "hot", "warm",
        "cool", "fuzzy", "slimy", "silky", "coarse", "furry", "prickly",
        "tender", "firm", "gritty", "greasy",
    },
    "olfactory": {
        "fragrant", "pungent", "musty", "smoky", "fishy", "floral",
        "acrid", "rancid", "perfumed", "stinky", "aromatic", "stale",
        "moldy", "putrid", "odorous", "scented", "reeking",
    },
    "gustatory": {
        "sweet", "sour", "bitter", "salty", "savory", "spicy", "bland",
        "tangy", "tart", "sugary", "zesty", "delicious", "yummy",
        "creamy", "juicy", "flavorful",
    },
}

_ANCHOR_TO_MODALITY: Dict[str, str] = {
    w: m for m, words in SENSORY_ANCHORS.items() for w in words
}

_PROPAGATING_RELATIONS = {"/r/Synonym", "/r/SimilarTo", "/r/RelatedTo"}


class GroundingBuilder:
    def __init__(self, wn_source, imagenet_source, cmu_source, cn_source):
        self.wn = wn_source
        self.imagenet = imagenet_source
        self.cmu = cmu_source
        self.cn = cn_source

    def _sensory_adjective_modality(self, word: str, wn_entry) -> Optional[str]:
        if word in _ANCHOR_TO_MODALITY:
            return _ANCHOR_TO_MODALITY[word]
        if wn_entry is None or "a" not in wn_entry.pos_set:
            return None
        # WordNet synonym propagation
        for syn in wn_entry.synonyms:
            if syn in _ANCHOR_TO_MODALITY:
                return _ANCHOR_TO_MODALITY[syn]
        # ConceptNet Synonym/SimilarTo/RelatedTo propagation from anchors
        for relation, other, _weight in self.cn.lookup(word):
            if relation in _PROPAGATING_RELATIONS and other in _ANCHOR_TO_MODALITY:
                return _ANCHOR_TO_MODALITY[other]
        return None

    def modalities_for(self, word: str, wn_entry) -> Set[str]:
        modalities: Set[str] = set()

        sensory_modality = self._sensory_adjective_modality(word, wn_entry)
        if sensory_modality:
            return {sensory_modality}

        is_concrete = bool(wn_entry and wn_entry.is_concrete) or self.imagenet.lookup(word)
        has_phonetic = self.cmu.lookup(word) is not None

        if is_concrete:
            modalities.add("visual")
            if has_phonetic:
                modalities.add("auditory")

        if wn_entry and wn_entry.primary_lexname in ("noun.sound", "verb.communication") and has_phonetic:
            modalities.add("auditory")

        if wn_entry and wn_entry.primary_lexname == "verb.motion":
            modalities.add("visual")
            modalities.add("tactile")

        return modalities

    def build(self, word: str, chi: int, wn_entry) -> Dict[str, int]:
        """grounding dict: modality name -> chi (the word's own chi -- see
        module docstring for why)."""
        modalities = self.modalities_for(word, wn_entry)
        return {m: chi for m in modalities if m in config.MODALITY_TO_ORGAN}
