"""Vertical gates for bounded language experience settlement.

Completed sentence windows are transient causal workspaces. Their explicit
DSF fields and source-linked Atlas effects remain available to cognition, but
the verbatim windows and the retired Fact-Strand replay index do not persist.
"""

import copy
import pytest

from dsf_ai_service.substrate.language_fact_strand import DSF_FIELD_NAMES
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


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


def test_sentence_settles_one_bounded_full_field_experience(
        guala, monkeypatch):
    captured = []
    real_add_entry = guala.window_manager.add_entry

    def capture_entry(*args, **kwargs):
        captured.append(copy.deepcopy(kwargs))
        return real_add_entry(*args, **kwargs)

    monkeypatch.setattr(
        guala.window_manager, "add_entry", capture_entry)
    guala.read_sentence("red fox runs warm", source="corpus")

    word_entries = [
        entry for entry in captured if entry.get("modality") == "word"
    ]
    assert [entry["detail"]["language_form"]
            for entry in word_entries] == ["red", "fox", "runs", "warm"]
    assert [entry["language_position"]
            for entry in word_entries] == [0, 1, 2, 3]
    for entry in word_entries:
        structural_fact = entry["structural_fact"]
        assert set(structural_fact["dsf"]) == set(DSF_FIELD_NAMES)
        assert structural_fact["events"]
        assert structural_fact["structural_fingerprint"]

    touch_entries = [
        entry for entry in captured if entry.get("modality") == "touch"
    ]
    assert touch_entries
    for entry in touch_entries:
        structural_fact = entry["structural_fact"]
        assert structural_fact["schema"] == "canonical_sensory_field_v1"
        assert structural_fact["waveform"]
        assert set(structural_fact["dsf"]) == set(DSF_FIELD_NAMES)

    closed = _events(guala, "window_closed")
    released = _events(guala, "binding_context_released_to_atlas")
    assert len(closed) == 1
    assert closed[0].detail["close_reason"] == "context_complete"
    assert released[-1].detail["window_id"] == closed[0].detail["window_id"]
    assert guala.window_manager.closed_window(
        closed[0].detail["window_id"]) is None
    assert not guala.window_manager.snapshot()["windows"]
    assert len(guala.language_fact_memory) == 0
    assert not guala._ordered_language_windows
    assert {"red", "fox", "runs", "warm"} <= _mode_words(guala)


def test_repeated_sentences_never_recreate_lifetime_verbatim_index(guala):
    guala.read_sentence("red fox runs warm", source="corpus")
    guala.read_sentence("blue fox sleeps cold", source="corpus")

    assert len(_events(guala, "window_closed")) == 2
    assert len(_events(
        guala, "binding_context_released_to_atlas")) == 2
    assert not guala.window_manager.snapshot()["windows"]
    assert len(guala.language_fact_memory) == 0
    assert not guala._ordered_language_windows
    assert {"red", "blue", "fox", "runs", "sleeps", "warm", "cold"} <= (
        _mode_words(guala)
    )


def test_retired_fact_composer_cannot_reopen_released_window(guala):
    guala.read_sentence("red fox runs warm", source="corpus")

    settlement = guala._compose_language_fact_settlement(("red", "fox"))

    assert settlement.content == ""
    assert settlement.n_commits == 0
    assert guala._committed_emission_response(settlement) == (
        "", "silence_no_commit")


def test_failed_partial_sentence_leaves_no_replay_state(
        guala, monkeypatch):
    real_read_word = guala.read_word
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected word failure")
        return real_read_word(*args, **kwargs)

    monkeypatch.setattr(guala, "read_word", fail_second)
    with pytest.raises(RuntimeError, match="injected word failure"):
        guala.read_sentence("red fox runs warm", source="corpus")

    closed = _events(guala, "window_closed")
    assert closed[-1].detail["close_reason"] == "context_failed"
    assert not guala.window_manager.snapshot()["windows"]
    assert not guala.window_manager.open_context_ids()
    assert len(guala.language_fact_memory) == 0
    assert not guala._ordered_language_windows


def test_label_only_observed_sight_cannot_become_language_authority(guala):
    guala.window_manager.open(
        "give_experience", experience_origin="observed", bundle_name="fox")
    outer_context = guala.window_manager.active_context_id
    guala.window_manager.add_entry(
        modality="sight", section="sight", motif_id=7, chi=11,
        tick=guala.tick, source_tag="joe", mirror_atlas=False)

    guala.read_sentence("red fox", source="joe")

    assert guala.window_manager.active_context_id == outer_context
    window_id = guala.window_manager.close("give_experience_complete")
    assert guala.window_manager.closed_window(window_id) is None
    with pytest.raises(RuntimeError, match="is absent"):
        guala._remember_closed_language_window(window_id)
    assert len(guala.language_fact_memory) == 0
    assert not guala._ordered_language_windows


def test_transient_snapshot_restore_cannot_resurrect_fact_replay(guala):
    guala.read_sentence("red fox runs warm", source="corpus")
    snapshot = guala.window_manager.snapshot()
    assert not snapshot["windows"]

    restored = Guala()
    try:
        restored.window_manager.restore(snapshot)
        restored._rebuild_language_fact_memory_from_windows()
        assert restored.window_manager.snapshot() == snapshot
        assert len(restored.language_fact_memory) == 0
        settlement = restored._compose_language_fact_settlement(("red", "fox"))
        assert restored._committed_emission_response(settlement) == (
            "", "silence_no_commit")
    finally:
        restored.shutdown()


def test_full_save_restart_preserves_atlas_not_verbatim_windows(
        tmp_path, monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    first = Guala()
    second = None
    try:
        first._generate_genesis_identity(str(tmp_path))
        first.read_sentence("red fox runs warm", source="corpus")
        expected_words = _mode_words(first)
        result = first.save_full_state(str(tmp_path))
        assert "guala_windows.json" not in result
        assert not (tmp_path / "guala_windows.json").exists()
        first.shutdown()
        first = None

        second = Guala()
        second.load_full_state(str(tmp_path))
        assert second._load_successful
        assert not second.window_manager.window_ids()
        assert len(second.language_fact_memory) == 0
        assert not second._ordered_language_windows
        assert expected_words <= _mode_words(second)
    finally:
        if first is not None:
            first.shutdown()
        if second is not None:
            second.shutdown()


def test_current_save_set_does_not_reintroduce_window_store(
        tmp_path, monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    writer = Guala()
    reader = None
    try:
        writer._generate_genesis_identity(str(tmp_path))
        writer.read_sentence("red fox runs warm", source="corpus")
        result = writer.save_full_state(str(tmp_path))
        assert "guala_windows.json" not in result
        assert not (tmp_path / "guala_windows.json").exists()
        writer.shutdown()
        writer = None

        reader = Guala()
        reader.load_full_state(str(tmp_path))
        assert reader._load_successful
        assert len(reader.language_fact_memory) == 0
        assert not reader.window_manager.window_ids()
    finally:
        if writer is not None:
            writer.shutdown()
        if reader is not None:
            reader.shutdown()
