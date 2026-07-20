"""Production contract for transient experience binding.

Closed verbatim BindingWindows are not cognition state.  Krimelack/DSF atlas
bindings remain authoritative and durable; the context is released after its
entries have reached that structure.
"""

from pathlib import Path

from dsf_ai_service.substrate.atomic_state_generation import _snapshot_relpaths
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


def test_closed_experience_survives_in_atlas_without_a_window_ledger():
    guala = Guala()
    context_id = "observed:test"
    guala.window_manager.begin_context(
        context_id,
        trigger_reason="observed_test",
        context_detail={"experience_origin": "observed"},
    )
    guala.window_manager.add_entry(
        modality="word",
        section="listen",
        motif_id=41,
        chi=17,
        tick=1,
        source_tag="test",
        context_id=context_id,
        structural_fact={
            "schema": "explicit_dsf_test_v1",
            "dsf": {
                "D_k": [1.0], "S_UF": 0.9, "M_k": [0.1],
                "R_rev_k": [0.0], "U_star_k": [0.2],
                "C_k": [0.8], "P_k": [0.3], "B_k": [0.4],
            },
        },
    )

    window_id = guala.window_manager.end_context(
        context_id, "context_complete")

    assert window_id is not None
    assert guala.window_manager.window_ids() == ()
    assert guala.window_manager.closed_window_count() == 0
    assert guala.window_manager.chi_index == {}
    bindings = guala.atlas.entries[17]
    assert any(entry["section"] == "listen" and entry["motif"] == 41
               for entry in bindings)
    exact = next(entry for entry in bindings
                 if entry["section"] == "listen" and entry["motif"] == 41)
    assert exact["structural_fact"]["dsf"]["D_k"] == [1.0]
    assert all("window_id" not in entry and "window_entry_index" not in entry
               for entry in bindings)


def test_retired_verbatim_files_are_not_generation_state(tmp_path: Path):
    (tmp_path / "guala_core.json").write_text("{}")
    (tmp_path / "guala_windows.json").write_text("{}")
    wal_dir = tmp_path / "guala_windows_wal"
    wal_dir.mkdir()
    (wal_dir / "seg-00000000-00000000.jsonl").write_text("legacy")

    relpaths = _snapshot_relpaths(str(tmp_path))

    assert "guala_core.json" in relpaths
    assert "guala_windows.json" not in relpaths
    assert not any(path.startswith("guala_windows_wal/") for path in relpaths)


def test_curriculum_descriptor_preserves_full_field_without_closed_window(
        tmp_path: Path):
    guala = Guala()
    guala._enqueue_organism_remember = lambda _word: None
    guala._enqueue_tapestry_expose = lambda _left, _right: None

    guala.read_sentence("warm", source="curriculum")

    assert guala.window_manager.closed_window_count() == 0
    exact_facts = [
        entry["structural_fact"]
        for entries in guala.atlas.entries.values()
        for entry in entries
        if entry.get("section") == "emulator_touch"
        and "structural_fact" in entry
    ]
    assert exact_facts
    assert all(set(fact["dsf"]) == {
        "D_k", "M_k", "R_rev", "U_star",
        "C_k", "P_k", "B_k", "S_UF",
    } for fact in exact_facts)

    guala.save_full_state(str(tmp_path))
    restored = Guala()
    restored.load_full_state(str(tmp_path))
    restored_facts = [
        entry["structural_fact"]
        for entries in restored.atlas.entries.values()
        for entry in entries
        if entry.get("section") == "emulator_touch"
        and "structural_fact" in entry
    ]
    assert restored_facts == exact_facts
    assert restored.window_manager.closed_window_count() == 0


def test_engine_continuity_contract_has_no_verbatim_window_artifact():
    guala = Guala()
    assert guala.window_manager._retain_closed_windows is False
    assert "guala_windows.json" not in Guala.STATE_FILES
    assert "guala_windows.json" not in Guala.FULL_SAVE_MANIFEST_FILES
    assert "guala_windows.json" not in Guala.HOT_SAVE_MANIFEST_FILES
