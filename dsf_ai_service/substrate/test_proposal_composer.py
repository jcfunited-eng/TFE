"""Tests for GL-CMD-SYNTAX-ARC-20260718 Piece 2: the proposal composer.

Statistics propose, the organism disposes.  A candidate is valid ONLY
when stitched across >=2 distinct lived windows and reproducing no
single lived sequence verbatim — recombination by construction, never
certified, honestly labeled composed_attempt."""

import os

import pytest


@pytest.fixture()
def engine(tmp_path):
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    os.environ.setdefault("PYTHONHASHSEED", "0")
    g = Guala()
    g.add_corpus("seed", "Seed", ["the sun rises in the morning"])
    g.load_full_state(str(tmp_path / "state"))
    yield g
    try:
        g.shutdown()
    except Exception:
        pass


def _teach(engine, sentence):
    # Ordered windows require a multimodal OR taught language experience
    # (meaning = senses, by design); teaching=True is the tutor's own
    # gateway and the honest way to create citable windows in a test.
    engine.read_sentence(sentence, source="corpus", teaching=True)


def test_candidates_are_cross_window_and_never_verbatim(engine):
    _teach(engine, "the cat sat on the mat")
    _teach(engine, "the dog sat on the rug tonight")
    seeds = [{"words": ["the", "cat", "dog"], "provenance": "test"}]
    cands = engine.build_proposal_candidates(seeds)
    assert cands, "two overlapping lived windows must yield a proposal"
    with engine._language_fact_lock:
        lived = [" ".join(str(o.fact.language_form).lower()
                          for o in w.tokens)
                 for w in engine._ordered_language_windows.values()]
    for c in cands:
        assert c["n_source_windows"] >= 2, "must stitch >= 2 windows"
        assert len(c["words"]) >= 3
        assert not any(f" {c['text']} " in f" {seq} " for seq in lived), \
            f"candidate {c['text']!r} is a verbatim replay"


def test_single_window_yields_nothing(engine):
    _teach(engine, "the cat sat on the mat")
    seeds = [{"words": ["the"], "provenance": "test"}]
    assert engine.build_proposal_candidates(seeds) == [], \
        "recombination requires at least two lived windows"


def test_release_labels_composed_attempt_and_repeat_guards(engine):
    _teach(engine, "the cat sat on the mat")
    _teach(engine, "the dog sat on the rug tonight")
    seeds = [{"words": ["the", "cat", "dog"], "provenance": "test"}]
    cands = engine.build_proposal_candidates(seeds)
    assert cands
    scores = engine.precompute_proposal_votes(cands)
    assert len(scores) == len(cands)
    with engine.lock:
        first = engine._release_proposal_attempt(cands, scores,
                                                 conversational=True)
    assert first is not None
    assert first["response_source"] == "composed_attempt"
    assert first["n_source_windows"] >= 2
    assert first["committed_sections"] == []  # never certified
    with engine.lock:
        again = engine._release_proposal_attempt(
            [cands[0]], [scores[0]], conversational=True)
    if first["content"] == cands[0]["text"]:
        assert again is None, "same content must repeat-guard"
