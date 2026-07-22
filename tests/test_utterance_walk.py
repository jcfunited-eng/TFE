"""GL-FEAT-UTTERANCE-WALK-C1-20260722: an utterance is a walk, not a
single shot — the settle physics iterated with evolving anchors, every
per-step gate unchanged, bounded by word cap and wall budget.

These tests exercise the walk ORCHESTRATION (step sequencing, anchor/
anti-echo evolution, caps, honest stop conditions) with the per-step
settle stubbed; the settle physics itself has its own suites.
"""

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    EmissionSettlement,
    Guala,
)


@pytest.fixture
def guala(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("EMISSION_DYNAMICS", "1")
    monkeypatch.setenv("EMISSION_MODE", "grandurun")
    # Pin walk bounds — other test modules (emission budget) disable the
    # walk via a process-level env var that must not leak in here.
    monkeypatch.setenv("UTTERANCE_WALK_MAX_WORDS", "5")
    monkeypatch.setenv("UTTERANCE_WALK_BUDGET_S", "8.0")
    engine = Guala()
    try:
        yield engine
    finally:
        engine.shutdown()


def _wire(guala, step_results, gathered=None):
    """Stub the per-step settle and candidate gather; record call args."""
    calls = {"gather": [], "settle": []}
    results = list(step_results)

    def fake_candidates(input_words, input_chis=None):
        calls["gather"].append((list(input_words), list(input_chis or [])))
        return gathered if gathered is not None else [({}, {}, 1.0)]

    def fake_dynamics(input_chis, input_words_set, deep_candidates,
                      v7_session=None, input_words=None):
        calls["settle"].append(set(input_words_set))
        return results.pop(0) if results else EmissionSettlement(
            tick=guala.tick)

    guala._brain_emission_candidates = fake_candidates
    guala._emit_dynamics = fake_dynamics
    guala._candidate_word_chi = lambda w, input_chis=None: 40
    return calls


def _settle(text, n):
    return EmissionSettlement(content=text, n_commits=n,
                              committed_sections=("ground",) * n)


def test_walk_chains_words_until_dynamics_go_quiet(guala):
    calls = _wire(guala, [
        _settle("there", 1),
        _settle("in", 1),
        _settle("", 0),          # dynamics go quiet — honest stop
    ])
    out = guala._emit_from_invariants([17], ["hello"])
    assert out.content == "there in"
    assert out.n_commits == 2
    # step 2 queried the committed word, not the input
    assert calls["gather"][1][0] == ["there"]
    # anchors grew: input chi plus the committed word's real chi
    assert calls["gather"][1][1][:2] == [17, 40]
    # anti-echo grew: the second settle saw "there" as unspeakable
    assert "there" in calls["settle"][1]


def test_walk_never_repeats_a_spoken_word(guala):
    _wire(guala, [
        _settle("there", 1),
        _settle("there", 1),     # echo of the chain — must terminate
    ])
    out = guala._emit_from_invariants([17], ["hello"])
    assert out.content == "there"
    assert out.n_commits == 1


def test_walk_respects_word_cap(guala, monkeypatch):
    monkeypatch.setenv("UTTERANCE_WALK_MAX_WORDS", "3")
    _wire(guala, [
        _settle("a", 1), _settle("b", 1), _settle("c", 1),
        _settle("d", 1),         # beyond cap — must not be requested
    ])
    out = guala._emit_from_invariants([17], ["hello"])
    assert out.content == "a b c"


def test_walk_disabled_returns_single_settle(guala, monkeypatch):
    monkeypatch.setenv("UTTERANCE_WALK_MAX_WORDS", "1")
    calls = _wire(guala, [_settle("there", 1), _settle("in", 1)])
    out = guala._emit_from_invariants([17], ["hello"])
    assert out.content == "there"
    assert len(calls["settle"]) == 1


def test_walk_budget_zero_means_no_extra_steps(guala, monkeypatch):
    monkeypatch.setenv("UTTERANCE_WALK_BUDGET_S", "0")
    calls = _wire(guala, [_settle("there", 1), _settle("in", 1)])
    out = guala._emit_from_invariants([17], ["hello"])
    assert out.content == "there"
    assert len(calls["settle"]) == 1


def test_silent_first_settle_returns_unchanged(guala):
    calls = _wire(guala, [_settle("", 0)])
    out = guala._emit_from_invariants([17], ["hello"])
    assert out.content == ""
    assert out.n_commits == 0
    assert len(calls["settle"]) == 1
