import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from generator.language_seed import affect as affect_mod


class _FakeSource:
    def __init__(self, data):
        self.data = data

    def lookup(self, word):
        return self.data.get(word)


def test_direct_nrc_vad_preferred_over_warriner():
    nrc_vad = _FakeSource({"happy": (1.0, 0.8, 0.7)})
    warriner = _FakeSource({"happy": (8.0, 7.0, 6.0)})
    nrc_emotion = _FakeSource({})
    result = affect_mod.resolve_direct("happy", nrc_vad, warriner, nrc_emotion)
    assert result[3] == "nrc_vad"
    assert result[0] == 1.0  # v*2-1 = 1.0*2-1 = 1.0
    assert 0.0 <= result[1] <= 1.0
    assert 0.0 <= result[2] <= 1.0


def test_warriner_fallback_and_rescale():
    nrc_vad = _FakeSource({})
    warriner = _FakeSource({"gloom": (2.0, 3.0, 3.0)})  # 1..9 scale
    nrc_emotion = _FakeSource({})
    result = affect_mod.resolve_direct("gloom", nrc_vad, warriner, nrc_emotion)
    assert result[3] == "warriner"
    assert result[0] == (2.0 - 5.0) / 4.0
    assert result[1] == (3.0 - 1.0) / 8.0


def test_no_direct_coverage_returns_none():
    nrc_vad, warriner = _FakeSource({}), _FakeSource({})
    nrc_emotion = _FakeSource({"neutral_word": {"positive": 0, "negative": 0}})
    result = affect_mod.resolve_direct("neutral_word", nrc_vad, warriner, nrc_emotion)
    assert result is None


def test_resolver_programmatic_tier_never_uses_direct_lexicon():
    nrc_vad = _FakeSource({"foo": (1.0, 0.8, 0.7)})
    warriner, nrc_emotion = _FakeSource({}), _FakeSource({})
    resolver = affect_mod.AffectResolver(nrc_vad, warriner, nrc_emotion)
    v, a, d, source = resolver.resolve("foo", chi=1, tier="programmatic", related_chis=None)
    assert source == "default", "programmatic tier must not consult direct lexicons"


def test_resolver_inherits_from_neighbors():
    nrc_vad = _FakeSource({"anchor": (1.0, 0.8, 0.7)})
    warriner, nrc_emotion = _FakeSource({}), _FakeSource({})
    resolver = affect_mod.AffectResolver(nrc_vad, warriner, nrc_emotion)
    resolver.resolve("anchor", chi=1, tier="rich", related_chis=None)
    v, a, d, source = resolver.resolve(
        "orphan", chi=2, tier="rich", related_chis=[{"chi": 1, "strength": 0.9}])
    assert source == "inherited"
    assert v == 1.0  # single neighbor, weighted avg == its own value


def test_resolver_defaults_when_nothing_resolves():
    nrc_vad, warriner, nrc_emotion = _FakeSource({}), _FakeSource({}), _FakeSource({})
    resolver = affect_mod.AffectResolver(nrc_vad, warriner, nrc_emotion)
    v, a, d, source = resolver.resolve("mystery", chi=1, tier="rich", related_chis=None)
    assert source == "default"
    assert (v, a, d) == affect_mod.NEUTRAL_DEFAULT
    assert resolver.defaulted_count == 1


if __name__ == "__main__":
    test_direct_nrc_vad_preferred_over_warriner()
    test_warriner_fallback_and_rescale()
    test_no_direct_coverage_returns_none()
    test_resolver_programmatic_tier_never_uses_direct_lexicon()
    test_resolver_inherits_from_neighbors()
    test_resolver_defaults_when_nothing_resolves()
    print("ALL PASS: test_affect")
