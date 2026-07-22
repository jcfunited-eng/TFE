"""GL-FIX reply-formation trio (C1, 2026-07-22): the three defects that
kept heard phrases from ever producing a spoken reply.

1. CANDIDATE-CHI: emission candidates carried no "chi" key, so the
   agency backtrack measured every candidate at chi=0 against the real
   input centroid and stripped them all (live trace: "your name is
   guala" — 3 candidates, 3 agency_backtrack pops, silence).
2. HEARD-GROUNDING: a heard sentence's causal window held no real
   sensory entry, so heard words never passed the grounded-speech
   insert gate into the speakable index (live emission_diag:
   n_with_section_home=0 → organism_empty).
3. INTAKE-BACKPRESSURE: the per-sentence autonomous intake gate
   demanded an exactly-empty organism worker queue, which is never
   empty mid-chunk (live block_intake_ledger: planned=30 actual=1).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_auditory_causal_conversation_boundary import (  # noqa: E402
    _issue,
    _terminal,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (  # noqa: E402
    Guala,
    LanguageKrimelack,
)


@pytest.fixture
def guala(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    engine = Guala()
    try:
        yield engine
    finally:
        engine.shutdown()


# ---------------------------------------------------------------------------
# Fix 1 — real candidate chi
# ---------------------------------------------------------------------------

def test_candidate_word_chi_uses_nearest_real_binding(guala):
    guala._word_to_chi_index["blue"] = {7, 40}
    # Input centroid 9 → binding 7 is the honest witness, not 40.
    assert guala._candidate_word_chi("blue", input_chis=[9]) == 7
    # Centroid 39 → binding 40 wins.
    assert guala._candidate_word_chi("blue", input_chis=[39]) == 40
    # No input context → deterministic low binding.
    assert guala._candidate_word_chi("blue") == 7


def test_candidate_word_chi_falls_back_to_transduction(guala):
    guala._word_to_chi_index.pop("zephyr", None)
    krim = LanguageKrimelack()
    krim.transduce("zephyr")
    assert guala._candidate_word_chi("zephyr") == krim.winding


def test_brain_candidates_carry_real_chi(guala):
    guala._word_to_chi_index["blue"] = {7}
    guala._word_to_emission_sections["blue"] = [("subject", 0, "blue")]
    guala.organism.recall_fast = lambda signal: {"blue": 3}
    candidates = guala._brain_emission_candidates(
        ["hello"], input_chis=[9])
    assert candidates, "voted word with a section home must be a candidate"
    de = candidates[0][0]
    assert de["chi"] == 7, (
        "candidate must carry its real chi binding, not the placeholder 0")


# ---------------------------------------------------------------------------
# Fix 2 — heard words become speakable via the causal window
# ---------------------------------------------------------------------------

def test_heard_sentence_window_carries_terminal_citation(guala):
    terminal = _issue(guala, _terminal("hello"))
    settled = []
    real_settle = guala.window_manager._settle_window

    def capture(record):
        settled.append(record)
        return real_settle(record)

    guala.window_manager._settle_window = capture
    guala.read_sentence(
        "hello", source="auditory:unresolved_source",
        causal_intake=terminal)
    heard = [r for r in settled
             if str(r.get("context_id", "")).startswith("causal-experience:")]
    assert heard, "heard sentence must settle a causal-experience window"
    entries = heard[0].get("entries") or []
    citations = [e for e in entries
                 if e.get("modality") == "sound"
                 and e.get("section") == "audio_terminal"]
    assert len(citations) == 1, (
        "exactly one auditory terminal citation per heard sentence")
    fact = (citations[0].get("provenance") or {}).get("structural_fact")
    assert fact["causal_experience_id"] == terminal.event_id
    assert fact["causal_intake_receipt_sha256"] == (
        terminal.authority_receipt_sha256)


def test_heard_words_enter_speakable_index(guala):
    # Multi-word: position routing sends first/middle/last words to the
    # subject/verb/object emission sections. (A standalone single word
    # routes only to "listen" by design — _choose_role_sections — and
    # stays unspeakable until heard inside a sentence, e.g. "hello" via
    # "daddy says hello".)
    terminal = _issue(guala, _terminal("daddy says hello"))
    guala.read_sentence(
        "daddy says hello", source="auditory:unresolved_source",
        causal_intake=terminal)
    indexed = set(guala._word_to_emission_sections)
    assert indexed & {"daddy", "says", "hello"}, (
        "heard sentence words must gain section homes (really experienced); "
        f"index after read: {sorted(indexed)}")


def test_merely_read_word_stays_ungrounded(guala):
    guala.read_sentence("zymurgy", source="joe")
    assert "zymurgy" not in guala._word_to_emission_sections, (
        "reading alone (no real sensory entry) must not ground a word — "
        "the credo gate is unchanged for non-heard text")


# ---------------------------------------------------------------------------
# Fix 3 — bounded intake backpressure
# ---------------------------------------------------------------------------

class _FakeQueue:
    def __init__(self, unfinished):
        self.unfinished_tasks = unfinished


def test_backlog_gate_allows_small_backlog(guala):
    guala._organism_queue = _FakeQueue(guala.ORGANISM_INTAKE_BACKLOG_LIMIT)
    assert guala.organism_experience_pending() is True
    assert guala.organism_experience_backlogged() is False


def test_backlog_gate_yields_above_bound(guala):
    guala._organism_queue = _FakeQueue(
        guala.ORGANISM_INTAKE_BACKLOG_LIMIT + 1)
    assert guala.organism_experience_backlogged() is True


def test_backlog_gate_empty_queue(guala):
    guala._organism_queue = _FakeQueue(0)
    assert guala.organism_experience_pending() is False
    assert guala.organism_experience_backlogged() is False
