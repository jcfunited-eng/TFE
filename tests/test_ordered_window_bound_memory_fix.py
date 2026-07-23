"""Regression gates for the retired verbatim-window OOM mechanism.

The former mitigation capped ``_ordered_language_windows`` while retaining a
separate lifetime Fact-Strand index. The production boundary is now stricter:
completed windows settle into the learned substrate and their verbatim content
is released immediately. Neither replay structure may grow during reading.
"""

from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def _events(engine, kind):
    return [event for event in engine._substrate_events
            if event.kind == kind]


def _mode_words(engine):
    return {
        word
        for section in engine.sections.values()
        for _left, _right, word in section.modes
        if isinstance(word, str) and word
    }


def test_repeated_real_reading_retains_no_completed_windows():
    engine = Guala()
    try:
        sentences = (
            "red fox runs warm",
            "blue bird sleeps cold",
            "green cat walks softly",
        )
        for index in range(36):
            engine.read_sentence(
                sentences[index % len(sentences)],
                source="curriculum",
            )
            assert not engine.window_manager.window_ids()
            assert not engine.window_manager.open_context_ids()
            assert not engine._ordered_language_windows
            assert len(engine.language_fact_memory) == 0

        assert len(_events(engine, "window_closed")) == 36
        assert len(_events(
            engine, "binding_context_released_to_atlas")) == 36
        assert {
            "red", "fox", "runs", "warm",
            "blue", "bird", "sleeps", "cold",
            "green", "cat", "walks", "softly",
        } <= _mode_words(engine)
    finally:
        engine.shutdown()


def test_large_curriculum_registration_does_not_allocate_replay_windows():
    engine = Guala()
    try:
        engine.add_corpus(
            "book",
            "Book",
            ["the cat sat on the mat"] * 5000,
        )

        assert not engine.window_manager.window_ids()
        assert not engine._ordered_language_windows
        assert len(engine.language_fact_memory) == 0
    finally:
        engine.shutdown()


def test_rebuild_from_transient_window_store_remains_empty():
    engine = Guala()
    try:
        engine.read_sentence(
            "the cat sat on the mat",
            source="curriculum",
        )
        assert not engine.window_manager.window_ids()

        remembered = engine._rebuild_language_fact_memory_from_windows()

        assert remembered == 0
        assert not engine._ordered_language_windows
        assert len(engine.language_fact_memory) == 0
    finally:
        engine.shutdown()
