"""End-to-end gates for the canonical language Fact-Strand voice path."""

import copy
import json

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


def test_sentence_is_one_completed_full_field_emulated_experience(guala):
    guala.read_sentence("red fox runs warm", source="corpus")

    windows = guala.window_manager.snapshot()["windows"]
    assert len(windows) == 1
    window = next(iter(windows.values()))
    assert window["close_reason"] == "context_complete"
    assert window["context_detail"]["experience_origin"] == "emulated"

    words = [entry for entry in window["entries"]
             if entry["modality"] == "word"]
    assert [entry["provenance"]["detail"]["language_form"]
            for entry in words] == ["red", "fox", "runs", "warm"]
    assert [entry["language_position"] for entry in words] == [0, 1, 2, 3]
    assert all(entry["section"] == "language_fact" for entry in words)

    touch = [entry for entry in window["entries"]
             if entry["modality"] == "touch"]
    assert touch
    for entry in touch:
        sensory = entry["provenance"]["structural_fact"]
        assert sensory["schema"] == "canonical_sensory_field_v1"
        assert sensory["waveform"]
        assert set(sensory["dsf"]) == set(DSF_FIELD_NAMES)

    assert len(guala.language_fact_memory) == 4
    assert len(guala._ordered_language_windows) == 1


def test_prior_memory_produces_certified_multiword_fact_emission(guala):
    guala.read_sentence("red fox runs warm", source="corpus")

    settlement = guala._compose_language_fact_settlement(("red", "fox"))

    assert settlement.content == "runs warm"
    assert settlement.n_commits == 2
    assert guala._committed_emission_response(settlement) == (
        "runs warm", "fact_strand_commit")
    assert all(item.supports for item in settlement.commit_provenance)


def test_multiword_context_distinguishes_successor_and_single_word_stops(guala):
    guala.read_sentence("red fox runs warm", source="corpus")
    guala.read_sentence("blue fox sleeps cold", source="corpus")

    red = guala._compose_language_fact_settlement(("red", "fox"))
    blue = guala._compose_language_fact_settlement(("blue", "fox"))
    lone = guala._compose_language_fact_settlement(("fox",))

    assert red.content == "runs warm"
    assert blue.content == "sleeps cold"
    assert lone.content == ""


def test_label_only_observed_sight_cannot_certify_language(guala):
    guala.window_manager.open(
        "give_experience", experience_origin="observed", bundle_name="fox")
    outer_context = guala.window_manager.active_context_id
    guala.window_manager.add_entry(
        modality="sight", section="sight", motif_id=7, chi=11,
        tick=guala.tick, source_tag="joe", mirror_atlas=False)

    guala.read_sentence("red fox", source="joe")

    assert guala.window_manager.active_context_id == outer_context
    assert not guala.window_manager.snapshot()["windows"]
    window_id = guala.window_manager.close("give_experience_complete")
    with pytest.raises(ValueError, match="lacks certified native sight"):
        guala._remember_closed_language_window(window_id)
    window = guala.window_manager.closed_window(window_id)
    assert {entry["modality"] for entry in window["entries"]} >= {
        "sight", "word"}
    assert not guala._ordered_language_windows


def test_failed_partial_sentence_never_enters_memory_or_rebuild(guala, monkeypatch):
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

    window = next(iter(guala.window_manager.snapshot()["windows"].values()))
    assert window["close_reason"] == "context_failed"
    assert len(guala.language_fact_memory) == 0
    guala._rebuild_language_fact_memory_from_windows()
    assert len(guala.language_fact_memory) == 0
    assert not guala._ordered_language_windows


def test_window_restore_rebuild_is_bit_exact_and_tampering_silences(
        guala, monkeypatch):
    guala.read_sentence("red fox runs warm", source="corpus")
    snapshot = guala.window_manager.snapshot()
    settlement = guala._compose_language_fact_settlement(("red", "fox"))

    restored = Guala()
    try:
        restored.window_manager.restore(snapshot)
        restored._rebuild_language_fact_memory_from_windows()
        assert restored.window_manager.snapshot() == snapshot
        rebuilt = restored._compose_language_fact_settlement(("red", "fox"))
        assert rebuilt.content == settlement.content
        assert restored._committed_emission_response(rebuilt) == (
            "runs warm", "fact_strand_commit")

        broken = copy.deepcopy(rebuilt)
        support = broken.commit_provenance[0].supports[0]
        object.__setattr__(support, "entry_index", support.entry_index + 1000)
        assert restored._committed_emission_response(broken) == (
            "", "silence_no_commit")
    finally:
        restored.shutdown()


@pytest.mark.parametrize("phased", ("0", "1"))
def test_converse_uses_fact_path_and_never_calls_legacy_emission(
        guala, monkeypatch, phased):
    monkeypatch.setenv("CONVERSE_PHASED", phased)
    guala.read_sentence("red fox runs warm", source="corpus")
    monkeypatch.setattr(
        guala,
        "_emit_from_invariants",
        lambda *_args, **_kwargs: pytest.fail(
            "legacy reduced emission path must not run"),
    )

    turn = guala.converse("red fox", source="joe")

    assert turn.response == "runs warm"
    assert turn.response_source == "fact_strand_commit"
    assert turn.committed_sections == ("language_fact", "language_fact")
    assert guala._fact_record_has_certified_provenance(
        guala._last_emission_record)


def test_full_save_restart_restores_windows_facts_and_composition(
        tmp_path, monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    first = Guala()
    second = None
    try:
        first._generate_genesis_identity(str(tmp_path))
        first.read_sentence("red fox runs warm", source="corpus")
        expected = first.window_manager.snapshot()
        result = first.save_full_state(str(tmp_path))
        assert result["guala_windows.json"] > 0
        first.shutdown()
        first = None

        second = Guala()
        second.load_full_state(str(tmp_path))
        assert second._load_successful
        # GL-FIX-CHI-INDEX-ELIMINATION-20260720: chi_index is deliberately
        # NOT restored at boot anymore -- chi routing lives on the atlas
        # now, and nothing else reads the window store's own copy, so
        # rebuilding it from her whole history at every boot was pure cost
        # with no reader. window_manager.snapshot() (unlike the real WAL
        # boot path) still self-validates that chi_index exactly derives
        # from window content -- a real, still-correct invariant for that
        # LEGACY full-snapshot format, just no longer true immediately
        # after a real boot, so it can't be called here anymore. Compare
        # windows/open_contexts/sequences directly instead -- everything
        # actually restored, and the only things save/restart ever
        # promised to preserve going forward.
        first_window_ids = tuple(expected["windows"])
        assert set(second.window_manager.window_ids()) == set(first_window_ids)
        for window_id in first_window_ids:
            assert (second.window_manager.closed_window(window_id)
                    == expected["windows"][window_id])
        assert (second.window_manager.snapshot_incremental()["open_contexts"]
                == expected["open_contexts"])
        assert len(second.language_fact_memory) == 4
        settlement = second._compose_language_fact_settlement(("red", "fox"))
        assert second._committed_emission_response(settlement) == (
            "runs warm", "fact_strand_commit")
    finally:
        if first is not None:
            first.shutdown()
        if second is not None:
            second.shutdown()


def test_v73_missing_window_state_fails_closed_but_v72_migrates_empty(
        tmp_path, monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    writer = Guala()
    current_reader = None
    legacy_reader = None
    try:
        writer._generate_genesis_identity(str(tmp_path))
        writer.read_sentence("red fox runs warm", source="corpus")
        writer.save_full_state(str(tmp_path))
        writer.shutdown()
        writer = None
        (tmp_path / "guala_windows.json").unlink()

        current_reader = Guala()
        current_reader.load_full_state(str(tmp_path))
        assert not current_reader._load_successful
        assert "guala_windows.json" in " ".join(current_reader._load_errors)
        current_reader.shutdown()
        current_reader = None

        core_path = tmp_path / "guala_core.json"
        core = json.loads(core_path.read_text())
        core["schema_version"] = "v7.2.0"
        core_path.write_text(json.dumps(core))
        legacy_reader = Guala()
        legacy_reader.load_full_state(str(tmp_path))
        assert legacy_reader._load_successful
        assert len(legacy_reader.language_fact_memory) == 0
        assert not legacy_reader.window_manager.snapshot()["windows"]
    finally:
        if writer is not None:
            writer.shutdown()
        if current_reader is not None:
            current_reader.shutdown()
        if legacy_reader is not None:
            legacy_reader.shutdown()
