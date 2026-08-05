import inspect

import pytest

from dsf_ai_service.substrate.language_fact_composer import (
    ContinuationStopReason,
    DeterministicWindowComposer,
    OrderedBindingWindow,
    WindowTokenOccurrence,
)
from dsf_ai_service.substrate.language_fact_strand import (
    BindingWindowCitation,
    FactProvenance,
    LanguageFactMemory,
    RecallReason,
    construct_language_fact_strand,
)


def _window_fact(word, window_id, origin="emulated", trace_id="trace-1"):
    return construct_language_fact_strand(
        word,
        provenance=FactProvenance(
            source_tag="story_emulator" if origin == "emulated" else "embodied_sensor",
            trace_id=trace_id,
            windows=(
                BindingWindowCitation(
                    window_id=window_id,
                    experience_origin=origin,
                    modalities=("word", "sight", "sound"),
                ),
            ),
        ),
    )


def _window(window_id, words, indexes, origin="emulated", trace_id="trace-1"):
    facts = tuple(
        _window_fact(word, window_id, origin=origin, trace_id=trace_id)
        for word in words
    )
    ordered = OrderedBindingWindow(
        window_id=window_id,
        experience_origin=origin,
        tokens=tuple(
            WindowTokenOccurrence(fact=fact, window_id=window_id, entry_index=index)
            for fact, index in zip(facts, indexes)
        ),
    )
    return facts, ordered


def test_multiword_continuation_follows_one_emulated_window_to_its_end():
    facts, window = _window("win-story", ("red", "fox", "runs"), (2, 5, 9))
    composer = DeterministicWindowComposer(LanguageFactMemory(facts), (window,))

    result = composer.continue_from(construct_language_fact_strand("red"))

    assert result.language_forms == ("fox", "runs")
    assert result.stop_reason is ContinuationStopReason.NO_SUCCESSOR
    assert tuple(
        (token.entry_provenance[0].window_id, token.entry_provenance[0].entry_index)
        for token in result.emitted_tokens
    ) == (("win-story", 5), ("win-story", 9))
    assert all(
        token.entry_provenance[0].experience_origin == "emulated"
        for token in result.emitted_tokens
    )


def test_observed_window_origin_and_trace_are_preserved_exactly():
    facts, window = _window(
        "win-observed", ("hello", "world"), (4, 11),
        origin="observed", trace_id="sensor-trace-88",
    )
    composer = DeterministicWindowComposer(LanguageFactMemory(facts), (window,))

    result = composer.continue_from(construct_language_fact_strand("hello"))

    provenance = result.emitted_tokens[0].entry_provenance[0]
    assert result.language_forms == ("world",)
    assert provenance.window_id == "win-observed"
    assert provenance.entry_index == 11
    assert provenance.experience_origin == "observed"
    assert provenance.source_tag == "embodied_sensor"
    assert provenance.trace_id == "sensor-trace-88"
    assert provenance.source_strand_id == facts[1].strand_id


def test_no_successor_stops_without_manufacturing_a_token():
    facts, window = _window("win-end", ("hello",), (3,))
    result = DeterministicWindowComposer(LanguageFactMemory(facts), (window,)).continue_from(
        construct_language_fact_strand("hello")
    )

    assert result.emitted_tokens == ()
    assert result.stop_reason is ContinuationStopReason.NO_SUCCESSOR


def test_repetition_never_outvotes_one_distinct_successor():
    windows = []
    facts = []
    for number in range(3):
        window_facts, window = _window(
            f"win-fox-{number}", ("red", "fox"), (1, 2), trace_id=f"fox-{number}"
        )
        facts.extend(window_facts)
        windows.append(window)
    bird_facts, bird_window = _window("win-bird", ("red", "bird"), (1, 2))
    facts.extend(bird_facts)
    windows.append(bird_window)

    result = DeterministicWindowComposer(
        LanguageFactMemory(facts), windows
    ).continue_from(construct_language_fact_strand("red"))

    assert result.emitted_tokens == ()
    assert result.stop_reason is ContinuationStopReason.AMBIGUOUS_SUCCESSOR_CLASSES


def test_longest_structural_suffix_disambiguates_blue_fox_and_red_fox():
    blue_facts, blue_window = _window(
        "win-blue", ("blue", "fox", "sleeps"), (1, 3, 8)
    )
    red_facts, red_window = _window(
        "win-red", ("red", "fox", "runs"), (2, 4, 9)
    )
    composer = DeterministicWindowComposer(
        LanguageFactMemory(blue_facts + red_facts), (blue_window, red_window)
    )

    blue_result = composer.continue_from_sequence(
        tuple(construct_language_fact_strand(word) for word in ("blue", "fox"))
    )
    red_result = composer.continue_from_sequence(
        tuple(construct_language_fact_strand(word) for word in ("red", "fox"))
    )
    fox_alone = composer.continue_from(construct_language_fact_strand("fox"))

    assert blue_result.language_forms == ("sleeps",)
    assert blue_result.emitted_tokens[0].entry_provenance[0].window_id == "win-blue"
    assert red_result.language_forms == ("runs",)
    assert red_result.emitted_tokens[0].entry_provenance[0].window_id == "win-red"
    assert fox_alone.emitted_tokens == ()
    assert fox_alone.stop_reason is ContinuationStopReason.AMBIGUOUS_SUCCESSOR_CLASSES


def test_all_paths_at_the_longest_suffix_remain_subject_to_unique_successor_law():
    first_facts, first_window = _window(
        "win-blue-one", ("blue", "fox", "sleeps"), (1, 3, 8)
    )
    second_facts, second_window = _window(
        "win-blue-two", ("blue", "fox", "runs"), (2, 6, 11)
    )
    composer = DeterministicWindowComposer(
        LanguageFactMemory(first_facts + second_facts),
        (first_window, second_window),
    )

    result = composer.continue_from_sequence(
        tuple(construct_language_fact_strand(word) for word in ("blue", "fox"))
    )

    assert result.emitted_tokens == ()
    assert result.stop_reason is ContinuationStopReason.AMBIGUOUS_SUCCESSOR_CLASSES


def test_every_query_token_must_pass_full_field_recall_before_suffix_selection():
    facts, window = _window("win-known", ("red", "fox", "runs"), (1, 2, 3))
    composer = DeterministicWindowComposer(LanguageFactMemory(facts), (window,))

    result = composer.continue_from_sequence(
        (
            construct_language_fact_strand("unremembered"),
            construct_language_fact_strand("fox"),
        )
    )

    assert result.emitted_tokens == ()
    assert result.stop_reason is ContinuationStopReason.INPUT_UNKNOWN
    assert result.recall_reason is RecallReason.NO_STRUCTURAL_CANDIDATE


def test_terminal_paths_do_not_veto_a_unique_continuation():
    """Ratified 2026-07-16 (teaching-correction fix): a window that merely
    ENDS at the query is absence of evidence, not a competing claim --
    every heard question mints such a window, and the old mixed-terminal
    veto made any question permanently unanswerable once asked. The
    unique-successor law applies among windows that actually testify."""
    end_facts, end_window = _window("win-terminal", ("red",), (1,))
    next_facts, next_window = _window("win-continuing", ("red", "fox"), (1, 4))
    result = DeterministicWindowComposer(
        LanguageFactMemory(end_facts + next_facts), (end_window, next_window)
    ).continue_from(construct_language_fact_strand("red"))

    assert [t.recognized_strands[0].language_form
            for t in result.emitted_tokens] == ["fox"]
    assert result.stop_reason is not ContinuationStopReason.MIXED_TERMINAL_AND_SUCCESSOR


def test_structurally_ambiguous_successor_is_unknown_and_stops():
    source_facts, source_window = _window("win-source", ("red", "aeu"), (1, 3))
    alternative = _window_fact("aeo", "win-alternative")
    _, alternative_window = _window("win-alternative", ("aeo",), (2,))
    memory = LanguageFactMemory(source_facts + (alternative,))
    composer = DeterministicWindowComposer(
        memory, (source_window, alternative_window)
    )

    result = composer.continue_from(construct_language_fact_strand("red"))

    assert result.emitted_tokens == ()
    assert result.stop_reason is ContinuationStopReason.SUCCESSOR_UNKNOWN
    assert result.recall_reason is RecallReason.AMBIGUOUS_RECIPROCAL_CLASSES


def test_same_successor_class_keeps_every_exact_window_entry_provenance():
    facts_one, window_one = _window(
        "win-one", ("hello", "world"), (2, 7), trace_id="trace-one"
    )
    facts_two, window_two = _window(
        "win-two", ("hello", "world"), (6, 14), trace_id="trace-two"
    )
    result = DeterministicWindowComposer(
        LanguageFactMemory(facts_one + facts_two), (window_one, window_two)
    ).continue_from(construct_language_fact_strand("hello"))

    assert result.language_forms == ("world",)
    provenance = result.emitted_tokens[0].entry_provenance
    assert tuple((item.window_id, item.entry_index) for item in provenance) == (
        ("win-one", 7),
        ("win-two", 14),
    )
    assert {item.trace_id for item in provenance} == {"trace-one", "trace-two"}


def test_unknown_input_and_memory_without_ordered_occurrence_stop():
    fact = _window_fact("hello", "win-memory-only")
    memory = LanguageFactMemory((fact,))
    composer = DeterministicWindowComposer(memory, ())

    absent = composer.continue_from(construct_language_fact_strand("unremembered"))
    no_order = composer.continue_from(construct_language_fact_strand("hello"))

    assert absent.stop_reason is ContinuationStopReason.INPUT_UNKNOWN
    assert absent.recall_reason is RecallReason.NO_STRUCTURAL_CANDIDATE
    assert no_order.stop_reason is ContinuationStopReason.NO_CITED_OCCURRENCE


def test_empty_or_mutable_query_sequence_fails_without_guessing_context():
    composer = DeterministicWindowComposer(LanguageFactMemory(), ())

    empty = composer.continue_from_sequence(())
    assert empty.stop_reason is ContinuationStopReason.EMPTY_QUERY
    with pytest.raises(TypeError, match="immutable tuple"):
        composer.continue_from_sequence([])


def test_word_only_window_citation_cannot_enter_composer():
    fact = construct_language_fact_strand(
        "hello",
        provenance=FactProvenance(
            source_tag="typed",
            windows=(
                BindingWindowCitation(
                    window_id="win-word-only",
                    experience_origin="emulated",
                    modalities=("word",),
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="multimodal BindingWindow"):
        WindowTokenOccurrence(fact=fact, window_id="win-word-only", entry_index=1)


def test_window_order_must_be_explicit_and_strictly_increasing():
    first = _window_fact("hello", "win-order")
    second = _window_fact("world", "win-order")
    with pytest.raises(ValueError, match="strictly increasing"):
        OrderedBindingWindow(
            window_id="win-order",
            experience_origin="emulated",
            tokens=(
                WindowTokenOccurrence(first, "win-order", 5),
                WindowTokenOccurrence(second, "win-order", 4),
            ),
        )


def test_composer_source_contains_no_forbidden_candidate_authority():
    source = inspect.getsource(DeterministicWindowComposer).lower()
    assert "random" not in source
    assert "top_k" not in source
    assert "top-k" not in source
    assert "threshold" not in source
    assert "vocabulary" not in source
    assert "atlas" not in source
    assert "count(" not in source
