"""The historical-window proposal composer is retired from production."""

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def test_verbatim_successor_proposals_have_no_live_memory_source():
    guala = Guala()
    guala._enqueue_organism_remember = lambda _word: None
    guala._enqueue_tapestry_expose = lambda _left, _right: None
    guala.read_sentence("the cat sat on the mat", source="curriculum")
    guala.read_sentence("the dog sat on the rug", source="curriculum")

    candidates = guala.build_proposal_candidates([
        {"words": ["the", "cat"], "provenance": "test"},
    ])

    assert candidates == []
    assert guala._ordered_language_windows == {}
    assert guala.window_manager.closed_window_count() == 0
