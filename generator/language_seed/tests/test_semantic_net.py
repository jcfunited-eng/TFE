import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from generator.language_seed import semantic_net as sn


def _entry(synonyms=(), hypernyms=(), hyponyms=(), primary_hypernym=None):
    return SimpleNamespace(synonyms=set(synonyms), hypernyms=set(hypernyms),
                            hyponyms=set(hyponyms), primary_hypernym=primary_hypernym)


def test_build_semantic_network_filters_to_seeded_words_only():
    entry = _entry(synonyms={"canine", "unseeded_synonym"}, hypernyms={"animal"})
    word_to_chi = {"dog": 10, "canine": 11, "animal": 12}
    net = sn.build_semantic_network("dog", 10, entry, [], word_to_chi)
    related_words_chis = {r["chi"] for r in net["related_chis"]}
    assert 11 in related_words_chis  # canine (seeded)
    assert 12 in related_words_chis  # animal (seeded)
    assert len(net["related_chis"]) == 2  # unseeded_synonym excluded


def test_build_semantic_network_combines_conceptnet_edges():
    entry = _entry()
    word_to_chi = {"dog": 10, "pet": 13}
    cn_edges = [("/r/IsA", "pet", 0.9)]
    net = sn.build_semantic_network("dog", 10, entry, cn_edges, word_to_chi)
    assert net["related_chis"] == [{"chi": 13, "strength": 0.9}]


def test_build_semantic_network_none_when_no_candidates():
    entry = _entry()
    word_to_chi = {"dog": 10}
    net = sn.build_semantic_network("dog", 10, entry, [], word_to_chi)
    assert net is None


def test_build_semantic_network_caps_at_max_related():
    entry = _entry(hyponyms={f"breed{i}" for i in range(50)})
    word_to_chi = {"dog": 10}
    word_to_chi.update({f"breed{i}": 100 + i for i in range(50)})
    net = sn.build_semantic_network("dog", 10, entry, [], word_to_chi)
    assert len(net["related_chis"]) == sn.MAX_RELATED_PER_WORD


def test_build_minimal_anchor_only_targets_rich_words():
    entry = _entry(primary_hypernym="animal")
    rich_word_to_chi = {"animal": 12}
    net = sn.build_minimal_anchor("dog", 10, entry, rich_word_to_chi)
    assert net == {
        "center_chi": 10,
        "related_chis": [{"chi": 12, "strength": sn.WORDNET_RELATION_WEIGHTS["hypernym"]}],
        "applies_to_hemispheres": list(__import__(
            "generator.language_seed.config", fromlist=["LANGUAGE_ORGANS"]).LANGUAGE_ORGANS),
    }


def test_build_minimal_anchor_none_when_hypernym_not_rich():
    entry = _entry(primary_hypernym="obscure_word")
    net = sn.build_minimal_anchor("dog", 10, entry, {})
    assert net is None


if __name__ == "__main__":
    test_build_semantic_network_filters_to_seeded_words_only()
    test_build_semantic_network_combines_conceptnet_edges()
    test_build_semantic_network_none_when_no_candidates()
    test_build_semantic_network_caps_at_max_related()
    test_build_minimal_anchor_only_targets_rich_words()
    test_build_minimal_anchor_none_when_hypernym_not_rich()
    print("ALL PASS: test_semantic_net")
