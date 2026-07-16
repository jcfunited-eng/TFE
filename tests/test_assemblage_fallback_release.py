"""Release-authority contract after Joe's 2026-07-16 ruling.

Fact-Strand certification remains the preferred authority (untouched, still
strict).  When the certified composer has nothing to release, the substrate's
own assemblage settlement — a real dynamics commit with complete candidate
provenance — releases under its own distinct label.  Fabricated or
inconsistent settlements still settle to silence.  This partially reverses
8835cfc's sole-authority clause, which had muted every voice path since
2026-07-13 while the assemblage verifiably kept committing real words.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    EmissionCandidateProvenance,
    EmissionSettlement,
)
from tests.test_language_fact_engine_vertical import guala  # fixture reuse


def _assemblage(words, *, n_commits=None, content=None):
    provenance = tuple(
        EmissionCandidateProvenance(section="subject", mode_id=i, word=w)
        for i, w in enumerate(words))
    return EmissionSettlement(
        content=" ".join(words) if content is None else content,
        committed_sections=tuple("subject" for _ in words),
        n_commits=len(words) if n_commits is None else n_commits,
        tick=1,
        commit_provenance=provenance,
    )


def test_real_assemblage_commit_releases_with_its_own_label(guala):
    settlement = _assemblage(["dog"])
    assert guala._committed_emission_response(settlement) == (
        "dog", "assemblage_commit")


def test_assemblage_label_is_never_fact_strand(guala):
    settlement = _assemblage(["warm", "sun"])
    content, source = guala._committed_emission_response(settlement)
    assert content == "warm sun"
    assert source == "assemblage_commit"
    assert source != "fact_strand_commit"


def test_commitless_settlement_still_settles_to_silence(guala):
    assert guala._committed_emission_response(
        EmissionSettlement(tick=1)) == ("", "silence_no_commit")


def test_inconsistent_provenance_does_not_release(guala):
    # Content that does not match its own commit provenance is not hers.
    forged = _assemblage(["dog"], content="dog cat")
    assert guala._committed_emission_response(forged) == (
        "", "silence_no_commit")
    # Commit count disagreeing with provenance length is not hers either.
    padded = _assemblage(["dog"], n_commits=2)
    assert guala._committed_emission_response(padded) == (
        "", "silence_no_commit")


def test_converse_falls_back_only_when_fact_settlement_is_empty(
        guala, monkeypatch):
    calls = []

    def fake_invariants(input_chis, input_words, mode_override=None,
                        v7_session=None):
        calls.append(tuple(input_words))
        return _assemblage(["dog"])

    monkeypatch.setattr(guala, "_emit_from_invariants", fake_invariants)
    turn = guala.converse("hello", source="joe")
    assert calls, "empty fact settlement must consult the assemblage voice"
    assert turn.response == "dog"
    assert turn.response_source == "assemblage_commit"
