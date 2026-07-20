"""Autonomous release contract after verbatim-window retirement."""

from dsf_ai_service.v4.gualaloom_v5_engine import (
    EmissionCandidateProvenance,
    EmissionSettlement,
    Guala,
)


def _assemblage(word: str, tick: int) -> EmissionSettlement:
    provenance = EmissionCandidateProvenance(
        section="subject", mode_id=0, word=word)
    return EmissionSettlement(
        content=word,
        committed_sections=("subject",),
        n_commits=1,
        tick=tick,
        commit_provenance=(provenance,),
    )


def _guala() -> Guala:
    guala = Guala()
    guala._enqueue_organism_remember = lambda _word: None
    guala._enqueue_tapestry_expose = lambda _left, _right: None
    return guala


def test_curriculum_builds_structural_memory_not_verbatim_seed_windows():
    guala = _guala()
    guala.read_sentence("red fox runs warm", source="curriculum")

    assert guala.atlas.entries
    assert any(section.modes for section in guala.sections.values())
    assert guala.window_manager.closed_window_count() == 0
    assert guala._ordered_language_windows == {}
    assert guala._autonomous_composer_seed_attempts() == []


def test_autonomy_releases_the_chi_atlas_assemblage(monkeypatch):
    guala = _guala()
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds",
        lambda *_args, **_kwargs: [{"chi_key": 17, "strength": 1.0}],
    )
    monkeypatch.setattr(
        guala, "_emit_from_invariants",
        lambda *_args, **_kwargs: _assemblage("awake", guala.tick),
    )

    with guala.lock:
        result = guala.compose_autonomous(seed_attempts=[])

    assert result["content"] == "awake"
    assert result["response_source"] == "assemblage_commit"


def test_organism_remains_the_autonomous_fallback(monkeypatch):
    guala = _guala()
    monkeypatch.setattr(guala, "_sample_autonomous_seeds", lambda **_kwargs: [])
    expected = {
        "content": "felt",
        "source": "guala",
        "response_source": "organism_attempt",
        "category": "autonomous",
    }
    monkeypatch.setattr(
        guala, "_compose_organism_attempt",
        lambda *_args, **_kwargs: expected,
    )

    with guala.lock:
        result = guala.compose_autonomous(
            seed_attempts=[{"words": ("warm",), "provenance": "test"}],
            organism_votes={"queries": ["warm"], "merged": {"felt": 1}},
        )

    assert result == expected


def test_pending_human_turn_blocks_every_autonomous_authority(monkeypatch):
    guala = _guala()
    with guala._live_converse_state_lock:
        guala._live_converse_pending = 1
    monkeypatch.setattr(
        guala, "_sample_autonomous_seeds",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("autonomy ran in front of a human turn")),
    )

    try:
        with guala.lock:
            assert guala.compose_autonomous(seed_attempts=[]) is None
    finally:
        with guala._live_converse_state_lock:
            guala._live_converse_pending = 0
