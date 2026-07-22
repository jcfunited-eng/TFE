"""Release-authority contract after Joe's 2026-07-16 ruling.

Fact-Strand certification remains the preferred authority (untouched, still
strict).  When the certified composer has nothing to release, the substrate's
own assemblage settlement — a real dynamics commit with complete candidate
provenance — releases under its own distinct label.  Fabricated or
inconsistent settlements still settle to silence.  This partially reverses
8835cfc's sole-authority clause, which had muted every voice path since
2026-07-13 while the assemblage verifiably kept committing real words.

Change 4 (spec GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3, release-policy
note a — ONE MOUTH): every RELEASED label — fact_strand_commit AND
assemblage_commit — passes the same voice (TTS) + self-hearing boundary,
with its label kept distinct end-to-end.  Silence and retired legacy labels
never gain a voice.  The one-mouth tests below guard that.
"""
import inspect
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    VOICED_RELEASE_SOURCES,
    EmissionCandidateProvenance,
    EmissionSettlement,
    Guala,
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
                        v7_session=None, causal_settlement=None):
        calls.append(tuple(input_words))
        return _assemblage(["dog"])

    monkeypatch.setattr(guala, "_emit_from_invariants", fake_invariants)
    turn = guala.converse("hello", source="joe")
    assert calls, "empty fact settlement must consult the assemblage voice"
    assert turn.response == "dog"
    assert turn.response_source == "assemblage_commit"


# ── Change 4, one mouth: voice + self-hearing for every released label ──────


def _self_hear_stub():
    """Minimal state double around the production Guala._self_hear."""
    g = Guala.__new__(Guala)
    g.tick = 10
    g.atlas = SimpleNamespace(band=0, entries={})
    g._self_hearing = False
    g.reads = []
    g.windows = []
    g.events = []

    def read_sentence(text, **kwargs):
        g.reads.append((text, kwargs))
        g.tick += 1

    g.read_sentence = read_sentence
    g._open_response_window = lambda *args, **kwargs: g.windows.append(
        (args, kwargs))
    g._tag_response_bindings = lambda *_args, **_kwargs: None
    g._log_substrate_event = lambda kind, **detail: g.events.append(
        (kind, detail))
    return g


def test_assemblage_release_self_hears_with_its_own_label(monkeypatch):
    monkeypatch.setenv("SELF_HEARING_ENABLED", "1")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    g = _self_hear_stub()

    Guala._self_hear(
        g, "warm sun", "joe", emission_id="e2",
        response_source="assemblage_commit")

    assert g.reads, "a released assemblage commit must re-enter as heard experience"
    assert g.reads[0][1]["source"] == "guala"
    # The label stays distinct end-to-end: episode_ref and telemetry both
    # say assemblage_commit, never fact_strand_commit.
    assert g.reads[0][1]["episode_ref"] == "emission:e2:assemblage_commit"
    assert len(g.windows) == 1
    assert g.events[-1][0] == "self_heard"
    assert g.events[-1][1]["response_source"] == "assemblage_commit"


def test_unreleased_labels_still_never_self_hear(monkeypatch):
    monkeypatch.setenv("SELF_HEARING_ENABLED", "1")
    monkeypatch.setenv("SELF_VOICE_AUDIO_ENABLED", "0")
    g = _self_hear_stub()

    # Silence, retired legacy labels, and label-less releases stay mute.
    Guala._self_hear(g, "manufactured", "joe", emission_id="e3",
                     response_source="silence_no_commit")
    Guala._self_hear(g, "legacy", "joe", emission_id="e4",
                     response_source="v5_commit")
    Guala._self_hear(g, "unlabeled", "joe", emission_id=None,
                     response_source="assemblage_commit")
    assert g.reads == []
    assert g.windows == []


def test_converse_assemblage_release_reaches_the_self_hear_boundary(
        guala, monkeypatch):
    """The live converse wiring hands the assemblage label to _self_hear."""
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: _assemblage(["dog"]))
    heard = []
    done = threading.Event()

    def record_self_hear(reply, responding_to_source, reply_chis=None,
                         emission_id=None, response_source=None):
        heard.append((reply, emission_id, response_source))
        done.set()

    monkeypatch.setattr(guala, "_self_hear", record_self_hear)
    turn = guala.converse("hello", source="joe")
    assert turn.response == "dog"
    assert done.wait(timeout=10), "self-hear continuation never ran"
    assert heard == [("dog", turn.emission_id, "assemblage_commit")]


def test_assemblage_release_is_voiced_through_the_same_tts_boundary(
        monkeypatch):
    import dsf_ai_service.substrate_runner as runner
    from tests.test_honest_emission_boundary import (
        _ConversationStub,
        _dynamics_result,
    )

    voiced = []

    def record_synthesize(text):
        voiced.append(text)
        return "d2F2"  # any non-None wav payload

    monkeypatch.setattr(runner, "_synthesize_voice", record_synthesize)

    # A released assemblage commit is voiced, label kept distinct.
    stub = _ConversationStub(
        "dog", "assemblage_commit", _dynamics_result("dog", ["subject"], 1))
    monkeypatch.setattr(runner, "_guala", stub)
    result = runner._cmd_converse("hello", "joe", emission_mode="grandurun")
    assert voiced == ["dog"]
    assert result["speech"] == "d2F2"
    assert result["response_source"] == "assemblage_commit"

    # Certified releases keep their voice unchanged.
    stub = _ConversationStub(
        "warm", "fact_strand_commit",
        _dynamics_result("warm", ["language_fact"], 1))
    monkeypatch.setattr(runner, "_guala", stub)
    result = runner._cmd_converse("hello", "joe", emission_mode="grandurun")
    assert voiced == ["dog", "warm"]
    assert result["response_source"] == "fact_strand_commit"

    # Explained silence is never voiced.
    stub = _ConversationStub("", "silence_no_commit", _dynamics_result())
    monkeypatch.setattr(runner, "_guala", stub)
    result = runner._cmd_converse("hello", "joe", emission_mode="grandurun")
    assert voiced == ["dog", "warm"]
    assert "speech" not in result


def test_engine_and_runner_share_one_voiced_release_authority():
    """One mouth means ONE gate definition — no forked label lists.

    GL-CMD-SINGLE-STACK-ALL-LIVE-20260716 (organ 6): the tuple gained
    'organism_attempt' — the organism's honestly-labeled babble releases
    through the same mouth. Certification gates stay pinned to
    fact_strand_commit only (see tests/test_autonomous_organism_attempt.py).
    """
    import dsf_ai_service.substrate_runner as runner

    assert VOICED_RELEASE_SOURCES == (
        "fact_strand_commit",
        "assemblage_commit",
        "organism_attempt",
        "composed_attempt",
        "causal_action_commit",
    )
    assert "VOICED_RELEASE_SOURCES" in inspect.getsource(Guala._self_hear)
    assert "VOICED_RELEASE_SOURCES" in inspect.getsource(
        runner._cmd_converse)
    # The retired hardcoded certified-only gates must not resurface.
    assert 'response_source != "fact_strand_commit"' not in inspect.getsource(
        Guala._self_hear)
    assert 'response_source == "fact_strand_commit" and response' not in (
        inspect.getsource(runner._cmd_converse))
