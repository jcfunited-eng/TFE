import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from generator.language_seed import sources


def test_normalize_word():
    assert sources.normalize_word("  Dog  ") == "dog"
    assert sources.normalize_word("ice_cream") == "ice cream"
    assert sources.normalize_word("CAT") == "cat"


def test_is_wellformed_word():
    assert sources.is_wellformed_word("dog")
    assert sources.is_wellformed_word("well-known")
    assert sources.is_wellformed_word("don't")
    assert not sources.is_wellformed_word("dog2")
    assert not sources.is_wellformed_word("")
    assert not sources.is_wellformed_word("dog!")


def test_conceptnet_uri_parsing():
    cn = sources.ConceptNetSource()
    assert cn._parse_uri("/c/en/dog") == "dog"
    assert cn._parse_uri("/c/en/ice_cream/n") == "ice cream"
    assert cn._parse_uri("/c/fr/chien") is None


def test_relation_weights_have_sane_defaults():
    assert sources.RELATION_WEIGHTS["/r/Synonym"] > sources.RELATION_WEIGHTS["/r/RelatedTo"]
    assert 0.0 <= sources.DEFAULT_RELATION_WEIGHT <= 1.0


if __name__ == "__main__":
    test_normalize_word()
    test_is_wellformed_word()
    test_conceptnet_uri_parsing()
    test_relation_weights_have_sane_defaults()
    print("ALL PASS: test_sources")
