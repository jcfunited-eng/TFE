"""Change 4 (spec v3 release-policy note b): autonomous certified speech.

The 90s autonomous loop used to be structurally unable to produce a
fact_strand_commit — composer queries only happened on conversation turns.
compose_autonomous now queries the certified composer FIRST, seeded from the
organism's own lived content, then falls through to the substrate's own
assemblage commit, then to explained silence.  Ordering is identical to
conversation.

HARD CONSTRAINT under test (documented production regression, 2026-07-06
recall wiring): composer seeds must derive from the organism's live/lived
content — recently committed BindingWindow words and the current activity's
target — NEVER from atlas candidate/neighborhood dumps.  Seed provenance is
carried on every certified autonomous release and asserted here.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dsf_ai_service.v4.gualaloom_v5_engine import (
    EmissionCandidateProvenance,
    EmissionSettlement,
)
from tests.test_language_fact_engine_vertical import guala  # fixture reuse


class _PoisonAtlas:
    """Fails the test on ANY attribute access — proof of zero atlas reads."""

    def __getattr__(self, name):
        pytest.fail(
            f"autonomous composer seeding touched the atlas (.{name}) — "
            "seeds must come from lived windows/activity, never atlas dumps")


def _assemblage(words):
    provenance = tuple(
        EmissionCandidateProvenance(section="subject", mode_id=i, word=w)
        for i, w in enumerate(words))
    return EmissionSettlement(
        content=" ".join(words),
        committed_sections=tuple("subject" for _ in words),
        n_commits=len(words),
        tick=1,
        commit_provenance=provenance,
    )


def test_autonomous_loop_produces_certified_release_from_lived_windows(
        guala, monkeypatch):
    guala.read_sentence("red fox runs warm", source="corpus")
    # Certified is PREFERRED: the assemblage voice must not even be asked.
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: pytest.fail(
            "assemblage must not be consulted when the composer releases"))
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds",
        lambda *_args, **_kwargs: pytest.fail(
            "atlas chi sampling must not run when the composer releases"))

    with guala.lock:
        result = guala.compose_autonomous()

    assert result is not None
    assert result["content"] == "runs warm"
    assert result["response_source"] == "fact_strand_commit"
    assert result["committed_sections"] == ["language_fact", "language_fact"]
    assert all(item["supports"] for item in result["commit_provenance"])
    # A released cycle logs its seed decision.
    seed_events = [ev for ev in guala._substrate_events
                   if ev.kind == "autonomous_fact_seed"]
    assert seed_events and seed_events[-1].detail["released"] is True


def test_autonomous_seed_provenance_is_organism_sourced(guala, monkeypatch):
    guala.read_sentence("red fox runs warm", source="corpus")

    real_atlas = guala.atlas
    guala.atlas = _PoisonAtlas()
    try:
        attempts = guala._autonomous_composer_seed_attempts()
    finally:
        guala.atlas = real_atlas

    assert attempts, "lived windows must yield seed attempts"
    with guala._language_fact_lock:
        windows = dict(guala._ordered_language_windows)
    for attempt in attempts:
        assert attempt["words"]
        for record in attempt["provenance"]:
            assert record["origin"] in (
                "recent_window_commit", "current_activity_target")
            if record["origin"] == "recent_window_commit":
                # Each seed word maps back to the EXACT lived window entry.
                window = windows[record["window_id"]]
                token = next(
                    t for t in window.tokens
                    if t.entry_index == record["entry_index"])
                assert token.fact.language_form == record["word"]


def test_autonomous_certified_release_never_reads_the_atlas(
        guala, monkeypatch):
    guala.read_sentence("red fox runs warm", source="corpus")
    real_atlas = guala.atlas
    guala.atlas = _PoisonAtlas()
    try:
        with guala.lock:
            result = guala.compose_autonomous()
    finally:
        guala.atlas = real_atlas
    assert result is not None
    assert result["response_source"] == "fact_strand_commit"
    provenance = result["seed_provenance"]
    assert provenance
    assert all(item["origin"] == "recent_window_commit"
               for item in provenance)


def test_current_activity_target_seeds_the_certified_composer(
        guala, monkeypatch):
    guala.read_sentence("red fox runs warm", source="corpus")
    guala._pictures["p1"] = SimpleNamespace(title="red fox portrait")
    guala._current_activity = SimpleNamespace(
        kind="ATTENDING_VISUAL", target="p1")

    attempts = guala._autonomous_composer_seed_attempts()
    assert attempts[0]["words"] == ("red", "fox")
    assert all(item["origin"] == "current_activity_target"
               and item["target_id"] == "p1"
               for item in attempts[0]["provenance"])

    with guala.lock:
        result = guala.compose_autonomous()
    assert result is not None
    assert result["content"] == "runs warm"
    assert result["response_source"] == "fact_strand_commit"
    assert all(item["origin"] == "current_activity_target"
               for item in result["seed_provenance"])


def test_autonomous_falls_through_to_assemblage_when_composer_stops(
        guala, monkeypatch):
    # Two lived windows sharing a prefix with DIVERGENT successors: the
    # unique-successor law stops the composer honestly (no certified
    # release possible), so the substrate's own assemblage commit releases.
    guala.read_sentence("red fox runs warm", source="corpus")
    guala.read_sentence("red fox sleeps cold", source="corpus")
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds",
        lambda *_args, **_kwargs: [{"chi_key": 4, "strength": 1.0}])
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: _assemblage(["dog"]))

    with guala.lock:
        result = guala.compose_autonomous()

    assert result is not None
    assert result["content"] == "dog"
    assert result["response_source"] == "assemblage_commit"
    # The certified attempt happened and logged an honest stop.
    seed_events = [ev for ev in guala._substrate_events
                   if ev.kind == "autonomous_fact_seed"]
    assert seed_events and seed_events[-1].detail["released"] is False
    stop_reasons = {ev.detail.get("stop_reason")
                    for ev in guala._substrate_events
                    if ev.kind == "fact_compose"}
    assert "ambiguous_successor_classes" in stop_reasons


def test_autonomous_settles_to_explained_silence_when_nothing_commits(
        guala, monkeypatch):
    guala.read_sentence("red fox runs warm", source="corpus")
    guala.read_sentence("red fox sleeps cold", source="corpus")
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds",
        lambda *_args, **_kwargs: [{"chi_key": 4, "strength": 1.0}])
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: EmissionSettlement(tick=guala.tick))

    with guala.lock:
        result = guala.compose_autonomous()

    # Explained silence is first-class: no content is ever manufactured,
    # and the composer's stop reasons are already on the event stream.
    assert result is None
    assert any(ev.kind == "fact_compose" and ev.detail.get("stop_reason")
               for ev in guala._substrate_events)


def test_pending_conversation_bars_certified_autonomous_release(guala):
    """A conversation counted first is a hard barrier for EVERY autonomous
    release authority — certified included, not just the assemblage lock."""
    guala.read_sentence("red fox runs warm", source="corpus")
    with guala._live_converse_state_lock:
        guala._live_converse_pending += 1
    try:
        with guala.lock:
            assert guala.compose_autonomous() is None
    finally:
        with guala._live_converse_state_lock:
            guala._live_converse_pending -= 1


def test_autonomous_release_ordering_is_certified_then_assemblage(
        guala, monkeypatch):
    """When both authorities could speak, the certified one releases."""
    guala.read_sentence("red fox runs warm", source="corpus")
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: _assemblage(["dog"]))

    with guala.lock:
        result = guala.compose_autonomous()

    assert result is not None
    assert result["content"] == "runs warm"
    assert result["response_source"] == "fact_strand_commit"


# ── 2026-07-16 adversarial-review fixes: the self-hear loop must not close ──


def _events(guala, kind):
    return [ev for ev in guala._substrate_events if ev.kind == kind]


def _silence_assemblage(guala, monkeypatch):
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds", lambda *_a, **_k: [])
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: pytest.fail(
            "assemblage must not run in this scenario"))


def test_self_heard_only_corpus_never_seeds_autonomous_speech(
        guala, monkeypatch):
    """F1a: her own released words are memory, never autonomous seeds.

    Without this gate the loop closes: release -> _self_hear ->
    read_sentence(source='guala') -> fresh multimodal emulated window ->
    freshest entry of _ordered_language_windows -> next cycle's seed ->
    she re-releases a shrinking suffix of her own last utterance forever.
    """
    # The exact shape a self-heard release produces: source 'guala'.
    guala.read_sentence("red fox runs warm", source="guala")
    assert len(guala._ordered_language_windows) == 1  # memory kept

    attempts = guala._autonomous_composer_seed_attempts()
    assert attempts == [], "self-heard windows must never seed"
    excluded = _events(guala, "autonomous_seed_self_excluded")
    assert excluded and excluded[-1].detail["n_windows"] == 1

    # No certified autonomous release is possible from this corpus.
    _silence_assemblage(guala, monkeypatch)
    with guala.lock:
        assert guala.compose_autonomous() is None

    # But the window is still MEMORY: conversation recall still certifies.
    settlement = guala._compose_language_fact_settlement(("red", "fox"))
    assert guala._committed_emission_response(settlement) == (
        "runs warm", "fact_strand_commit")


def test_mixed_source_window_still_seeds(guala):
    """A real exchange (her words + the other speaker's) is shared lived
    experience, not an echo — it stays seed-eligible."""
    guala.read_sentence("red fox runs warm", source="joe")
    attempts = guala._autonomous_composer_seed_attempts()
    assert attempts and attempts[0]["words"] == ("red", "fox")


def test_repeated_autonomous_release_is_suppressed(guala, monkeypatch):
    """F1b: identical-to-recent autonomous text never releases twice."""
    guala.read_sentence("red fox runs warm", source="corpus")
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds", lambda *_a, **_k: [])

    with guala.lock:
        first = guala.compose_autonomous()
    assert first is not None and first["content"] == "runs warm"
    assert "runs warm" in guala._recent_autonomous_releases

    with guala.lock:
        second = guala.compose_autonomous()
    assert second is None, "an identical release must be suppressed"
    suppressed = _events(guala, "autonomous_repeat_suppressed")
    assert suppressed and suppressed[-1].detail["content"] == "runs warm"
    summary = _events(guala, "autonomous_fact_seed")[-1]
    assert summary.detail["released"] is False
    assert summary.detail["stop_reason"] == "repeat_suppressed"


def test_repeated_assemblage_release_is_suppressed(guala, monkeypatch):
    """F1b applies to every autonomous authority, assemblage included."""
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds",
        lambda *_a, **_k: [{"chi_key": 4, "strength": 1.0}])
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: _assemblage(["dog"]))

    with guala.lock:
        first = guala.compose_autonomous()
    assert first is not None
    assert first["response_source"] == "assemblage_commit"
    assert first["chi_seeds_used"] == 1

    with guala.lock:
        second = guala.compose_autonomous()
    assert second is None
    suppressed = _events(guala, "autonomous_repeat_suppressed")
    assert suppressed
    assert suppressed[-1].detail["response_source"] == "assemblage_commit"


def test_conversation_arriving_mid_compose_wins(guala, monkeypatch):
    """F2: the entry barrier is re-checked after settlement — a turn that
    arrives while the composer is settling is never talked over."""
    guala.read_sentence("red fox runs warm", source="corpus")
    _silence_assemblage(guala, monkeypatch)

    original = guala._compose_language_fact_settlement

    def arriving_mid_compose(words, composer=None):
        with guala._live_converse_state_lock:
            guala._live_converse_pending += 1
        return original(words, composer=composer)

    monkeypatch.setattr(
        guala, "_compose_language_fact_settlement", arriving_mid_compose)
    try:
        with guala.lock:
            assert guala.compose_autonomous() is None
    finally:
        with guala._live_converse_state_lock:
            guala._live_converse_pending = 0

    summary = _events(guala, "autonomous_fact_seed")[-1]
    assert summary.detail["stop_reason"] == "conversation_arrived"
    assert summary.detail["released"] is False
    assert "runs warm" not in guala._recent_autonomous_releases


def test_compose_budget_exhaustion_aborts_remaining_attempts(
        guala, monkeypatch):
    """F3: the wall-clock budget bounds the certified compose section.

    Setup: attempt 1 stops honestly (terminal token, no successor); attempt
    2 would release.  With a zero budget, attempt 2 is aborted with stop
    reason compose_budget; with a generous budget the same state releases.
    The snapshot plus attempt 1 always complete (checked BETWEEN attempts).
    """
    guala.read_sentence("red fox runs warm", source="corpus")
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds", lambda *_a, **_k: [])
    attempts = [
        {"words": ("warm",),  # last lived token: honest stop, no commit
         "provenance": [
             {"word": "warm", "origin": "recent_window_commit"}]},
        {"words": ("red", "fox"),  # would release "runs warm"
         "provenance": [
             {"word": "red", "origin": "recent_window_commit"},
             {"word": "fox", "origin": "recent_window_commit"}]},
    ]
    monkeypatch.setattr(
        guala, "_autonomous_composer_seed_attempts",
        lambda: [dict(a) for a in attempts])

    monkeypatch.setenv("AUTONOMOUS_COMPOSE_BUDGET_MS", "0")
    with guala.lock:
        assert guala.compose_autonomous() is None
    summary = _events(guala, "autonomous_fact_seed")[-1]
    assert summary.detail["released"] is False
    assert summary.detail["stop_reason"] == "compose_budget"

    monkeypatch.setenv("AUTONOMOUS_COMPOSE_BUDGET_MS", "10000")
    with guala.lock:
        result = guala.compose_autonomous()
    assert result is not None
    assert result["content"] == "runs warm"
    assert result["response_source"] == "fact_strand_commit"
