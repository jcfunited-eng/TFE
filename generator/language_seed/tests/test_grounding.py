import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from generator.language_seed import grounding as grounding_mod


class _FakeImageNet:
    def __init__(self, grounded=()):
        self.grounded = set(grounded)

    def lookup(self, word):
        return word in self.grounded


class _FakeCmu:
    def __init__(self, has=()):
        self.has = set(has)

    def lookup(self, word):
        return [["X"]] if word in self.has else None


class _FakeCn:
    def __init__(self, edges=None):
        self.edges = edges or {}

    def lookup(self, word):
        return self.edges.get(word, [])


def _entry(is_concrete=False, primary_lexname="noun.artifact", pos_set=("n",), synonyms=()):
    return SimpleNamespace(is_concrete=is_concrete, primary_lexname=primary_lexname,
                            pos_set=set(pos_set), synonyms=set(synonyms))


def test_concrete_noun_gets_visual_and_auditory_with_phonetic():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has={"ball"}), _FakeCn())
    entry = _entry(is_concrete=True)
    mods = gb.modalities_for("ball", entry)
    assert mods == {"visual", "auditory"}


def test_concrete_noun_without_phonetic_gets_visual_only():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has=set()), _FakeCn())
    entry = _entry(is_concrete=True)
    mods = gb.modalities_for("xyzzy", entry)
    assert mods == {"visual"}


def test_abstract_word_gets_no_grounding():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has={"justice"}), _FakeCn())
    entry = _entry(is_concrete=False, primary_lexname="noun.attribute")
    mods = gb.modalities_for("justice", entry)
    assert mods == set()


def test_motion_verb_gets_visual_and_tactile():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has=set()), _FakeCn())
    entry = _entry(is_concrete=False, primary_lexname="verb.motion", pos_set=("v",))
    mods = gb.modalities_for("run", entry)
    assert mods == {"visual", "tactile"}


def test_sensory_adjective_anchor_overrides_default():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has={"rough"}), _FakeCn())
    entry = _entry(is_concrete=False, primary_lexname="adj.all", pos_set=("a",))
    mods = gb.modalities_for("rough", entry)
    assert mods == {"tactile"}


def test_sensory_adjective_propagates_via_wordnet_synonym():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has=set()), _FakeCn())
    entry = _entry(is_concrete=False, primary_lexname="adj.all", pos_set=("a",), synonyms={"rough"})
    mods = gb.modalities_for("coarse", entry)
    assert mods == {"tactile"}


def test_sensory_adjective_propagates_via_conceptnet():
    cn = _FakeCn({"zesty2": [("/r/SimilarTo", "spicy", 0.8)]})
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has=set()), cn)
    entry = _entry(is_concrete=False, primary_lexname="adj.all", pos_set=("a",))
    mods = gb.modalities_for("zesty2", entry)
    assert mods == {"gustatory"}


def test_build_uses_own_chi_for_all_modalities():
    gb = grounding_mod.GroundingBuilder(None, _FakeImageNet(), _FakeCmu(has={"ball"}), _FakeCn())
    entry = _entry(is_concrete=True)
    grounding = gb.build("ball", chi=555, wn_entry=entry)
    assert grounding == {"visual": 555, "auditory": 555}


if __name__ == "__main__":
    test_concrete_noun_gets_visual_and_auditory_with_phonetic()
    test_concrete_noun_without_phonetic_gets_visual_only()
    test_abstract_word_gets_no_grounding()
    test_motion_verb_gets_visual_and_tactile()
    test_sensory_adjective_anchor_overrides_default()
    test_sensory_adjective_propagates_via_wordnet_synonym()
    test_sensory_adjective_propagates_via_conceptnet()
    test_build_uses_own_chi_for_all_modalities()
    print("ALL PASS: test_grounding")
