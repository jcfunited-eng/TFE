"""
GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 6): the organism voice,
partial-and-honest version -- organism_attempt as the third autonomous
release authority through the ONE existing release path.

Proves:
  - organism-recall candidates release as response_source
    'organism_attempt', end-to-end labeled (release dict + loud
    autonomous_organism_attempt event), seed words excluded from content
    (association, not parroting);
  - the label is voiced (in VOICED_RELEASE_SOURCES -- one mouth) but can
    NEVER be treated certified (certification gate rejects it);
  - the shared guards hold: the SAME repeat-suppression window, the SAME
    cycle compose budget, the SAME conversation-barrier re-check;
  - honest empty: no organism votes -> explained silence with a logged
    stop reason, never fabricated content;
  - compose_autonomous falls through to the organism attempt when the
    certified and assemblage tiers have nothing (babble beats silence).

organism.recall_fast is stubbed with a fixed vote Counter here: the
recall mechanism itself (including STDP vote weighting) is proven against
the real spike path in tests/test_stdp_recall_consumer.py -- this file
tests the release plumbing, labeling, and guards built on top of it.
"""

import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SUBSTRATE_MODE", "embedded")

from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    Guala, VOICED_RELEASE_SOURCES)

_SEEDS = [{"words": ("blue", "river"), "provenance": "test_window"}]


def _events(g, kind):
    return [ev for ev in g._substrate_events if ev.kind == kind]


def _deadline():
    return time.monotonic() + 5.0


def test_organism_attempt_releases_labeled_babble():
    g = Guala()
    try:
        g.organism.recall_fast = lambda _sig: Counter(
            {"sky": 5.0, "blue": 3.0, "stone": 2.0})
        with g.lock:
            result = g._compose_organism_attempt(_SEEDS, _deadline())
        assert result is not None, "organism attempt released nothing"
        assert result["response_source"] == "organism_attempt"
        assert result["category"] == "autonomous"
        # Seed words are queries, never parroted back as content.
        assert "blue" not in result["content"].split()
        assert "river" not in result["content"].split()
        assert "sky" in result["content"].split()
        assert result["committed_sections"] == []  # honest: no settlement
        ev = _events(g, "autonomous_organism_attempt")[-1]
        assert ev.detail["released"] is True
        assert ev.detail["queries"] == ["blue", "river"]
        print("test_organism_attempt_releases_labeled_babble: PASS "
              f"(content={result['content']!r})")
    finally:
        g.shutdown()


def test_organism_attempt_is_voiced_but_never_certified():
    assert "organism_attempt" in VOICED_RELEASE_SOURCES, (
        "organism_attempt is not voiced -- babble would be a second, "
        "silent mouth instead of the one mouth")
    g = Guala()
    try:
        fake_record = {"response_source": "organism_attempt",
                       "text": "sky stone",
                       "commit_provenance": []}
        assert not g._fact_record_has_certified_provenance(fake_record), (
            "an organism_attempt record passed the certification gate -- "
            "babble must NEVER certify")
        print("test_organism_attempt_is_voiced_but_never_certified: PASS")
    finally:
        g.shutdown()


def test_repeat_suppression_shared_window():
    g = Guala()
    try:
        g.organism.recall_fast = lambda _sig: Counter({"sky": 5.0})
        with g.lock:
            first = g._compose_organism_attempt(_SEEDS, _deadline())
            second = g._compose_organism_attempt(_SEEDS, _deadline())
        assert first is not None
        assert second is None, (
            "identical babble re-released inside the repeat window -- "
            "the F1b guard does not cover organism attempts")
        kinds = [ev.detail.get("response_source")
                 for ev in _events(g, "autonomous_repeat_suppressed")]
        assert "organism_attempt" in kinds
        print("test_repeat_suppression_shared_window: PASS")
    finally:
        g.shutdown()


def test_compose_budget_shared_clock():
    g = Guala()
    try:
        g.organism.recall_fast = lambda _sig: Counter({"sky": 5.0})
        with g.lock:
            result = g._compose_organism_attempt(
                _SEEDS, time.monotonic() - 0.001)  # budget already spent
        assert result is None, "an exhausted compose budget still released"
        ev = _events(g, "autonomous_organism_attempt")[-1]
        assert ev.detail["stop_reason"] == "compose_budget"
        print("test_compose_budget_shared_clock: PASS")
    finally:
        g.shutdown()


def test_conversation_barrier_recheck():
    g = Guala()
    try:
        g.organism.recall_fast = lambda _sig: Counter({"sky": 5.0})
        with g._live_converse_state_lock:
            g._live_converse_pending = 1
        try:
            with g.lock:
                result = g._compose_organism_attempt(_SEEDS, _deadline())
        finally:
            with g._live_converse_state_lock:
                g._live_converse_pending = 0
        assert result is None, "babble front-ran a pending human turn"
        ev = _events(g, "autonomous_organism_attempt")[-1]
        assert ev.detail["stop_reason"] == "conversation_arrived"
        print("test_conversation_barrier_recheck: PASS")
    finally:
        g.shutdown()


def test_honest_empty_when_organism_has_nothing():
    g = Guala()
    try:
        g.organism.recall_fast = lambda _sig: Counter()
        with g.lock:
            result = g._compose_organism_attempt(_SEEDS, _deadline())
        assert result is None, "empty organism recall fabricated content"
        ev = _events(g, "autonomous_organism_attempt")[-1]
        assert ev.detail["stop_reason"] == "organism_empty"
        print("test_honest_empty_when_organism_has_nothing: PASS")
    finally:
        g.shutdown()


def test_compose_autonomous_falls_through_to_organism_attempt():
    g = Guala()
    try:
        g._autonomous_composer_seed_attempts = lambda: list(_SEEDS)
        g._sample_autonomous_seeds = lambda n=12: []  # no assemblage seeds
        g.organism.recall_fast = lambda _sig: Counter({"sky": 4.0})
        with g.lock:
            result = g.compose_autonomous()
        assert result is not None, (
            "compose_autonomous returned silence although the organism "
            "had an attempt -- babble beats silence was not wired")
        assert result["response_source"] == "organism_attempt"
        assert result["content"] == "sky"
        print("test_compose_autonomous_falls_through_to_organism_attempt: "
              "PASS")
    finally:
        g.shutdown()


if __name__ == "__main__":
    test_organism_attempt_releases_labeled_babble()
    test_organism_attempt_is_voiced_but_never_certified()
    test_repeat_suppression_shared_window()
    test_compose_budget_shared_clock()
    test_conversation_barrier_recheck()
    test_honest_empty_when_organism_has_nothing()
    test_compose_autonomous_falls_through_to_organism_attempt()
    print("ALL PASS: test_autonomous_organism_attempt")
