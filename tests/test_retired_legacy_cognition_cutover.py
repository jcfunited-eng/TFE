import copy
import inspect
import json
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
from dsf_ai_service.loom_model import structural_graph_state
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
)
from dsf_ai_service.substrate.retired_legacy_cognition import (
    PURGED_RETIREMENT_SCHEMA,
    RECOVERY_AUTHORITY,
    RetiredLegacyCognitionError,
    assert_legacy_bindings_retired,
    prepare_purge_proof_from_active_generation,
    retire_neuron_legacy_bindings,
    validate_purge_proof,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from dsf_ai_service.v4 import guala_physical_runtime
from dsf_ai_service.v4 import guala_physical_runtime_core
from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import ChiAtlas
from dsf_ai_service.v4.gualaloom_v4_krimelack_dna import (
    LanguageKrimelack,
)
from tests.physical_inquiry_test_support import RUNTIME_KEY
from tools.guala_legacy_organism_graph_reader import (
    _retired_registry,
    load_authenticated_legacy_organism_graph,
)
from wave_spillover import Cell as LegacyWaveCell
IDENTITY = "retired-legacy-cognition-test-identity"


def _retired_writer_registry(**_ignored):
    by_type, by_tag = _retired_registry()
    by_type[LegacyWaveCell] = by_tag["wave_cell"]
    return by_type, by_tag


def _disable_background_substrate(monkeypatch) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    monkeypatch.setenv("SELF_HEARING_ENABLED", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)


def _write_exact_state(state_dir, monkeypatch, *, wave=False) -> None:
    _disable_background_substrate(monkeypatch)
    if wave:
        monkeypatch.setenv("WAVE_ATLAS_ENABLED", "1")
    writer = Guala()
    try:
        writer._generate_genesis_identity(str(state_dir))
        writer.tick = 17
        if wave:
            writer.wave_atlas.record(
                "object", 0, 17, tick=writer.tick, salience=1.0)
        writer.save_full_state(str(state_dir))
        if wave:
            writer._save_wave_atlas(str(state_dir))
    finally:
        writer.strict_shutdown(timeout=30.0)


def _source_generation(root: Path) -> None:
    files = {
        "guala_core.json": b'{"core":"old"}',
        "guala_atlas.json": b'{"atlas":"old"}',
        "guala_sections.json": b'{"sections":"old"}',
        "guala_deep_atlas.json": b'{"deep":"old"}',
        "guala_teaching.json": b'{"teaching":"old"}',
        "guala_organism.sgr": b"old organism",
        "guala_organism.sgr.binding.json": b'{"binding":"organism"}',
        "guala_tapestry.sgr": b"old tapestry",
        "guala_tapestry.sgr.binding.json": b'{"binding":"tapestry"}',
        "wave_atlas.npz": b"old wave",
        "wave_atlas.npz.binding.json": b'{"binding":"wave"}',
        "owner_state/self_vocal_pcm_motor.json": b"opaque-self-vocal",
        "owner_state/lived_vocal_teaching.json": b"opaque-lived-vocal",
        "owner_state/causal_thing_vocal_route.json": b"opaque-vocal-route",
        "owner_state/articulatory_thing_vocal_custody.json": (
            b"opaque-articulatory-vocal"
        ),
        "owner_state/learned_substrate_vocal_cycle.json": (
            b"opaque-learned-vocal-cycle"
        ),
    }
    for name, payload in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def test_purge_proof_names_exact_bytes_without_copying_them(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _source_generation(source)
    proof = prepare_purge_proof_from_active_generation(
        str(source),
        identity=IDENTITY,
        source_generation_tick=41,
    )
    proof["migration"] = {
        label: {
            "binding_records_retired": 0,
            "chi_records_retired": 0,
            "language_labels_retired": 0,
            "neurons_preserved": 64,
        }
        for label in ("organism", "tapestry")
    }
    restored = validate_purge_proof(
        proof,
        expected_identity=IDENTITY,
        maximum_tick=41,
    )
    assert restored["schema"] == PURGED_RETIREMENT_SCHEMA
    assert restored["recovery_authority"] == RECOVERY_AUTHORITY
    assert {
        record["classification"]
        for record in restored["source_components"]
    } == {
        "pre_cutover_generation_core",
        "retired_legacy_chi_word_authority",
        "retired_word_labelled_dsf_mode_authority",
        "retired_deep_chi_association_authority",
        "retired_multi_owner_cognition_monolith",
        "migrated_pre_cutover_neuron_graph",
        "pre_cutover_organism_authentication_receipt",
        "migrated_pre_cutover_tapestry_graph",
        "pre_cutover_tapestry_authentication_receipt",
        "retired_wave_chi_binding_authority",
        "pre_cutover_wave_authentication_receipt",
        "retired_self_vocal_pcm_owner_envelope",
        "retired_lived_vocal_teaching_owner_envelope",
        "retired_causal_thing_vocal_route_owner_envelope",
        "retired_articulatory_thing_vocal_owner_envelope",
        "retired_learned_vocal_cycle_owner_envelope",
    }
    assert list(target.iterdir()) == []
    changed = copy.deepcopy(restored)
    changed["source_components"][0]["size_bytes"] += 1
    with pytest.raises(
        RetiredLegacyCognitionError,
        match="component root changed",
    ):
        validate_purge_proof(
            changed,
            expected_identity=IDENTITY,
            maximum_tick=41,
        )


def test_active_engine_imports_no_retired_owner_or_language_decoder() -> None:
    source = "\n".join(
        (
            inspect.getsource(guala_physical_runtime),
            inspect.getsource(guala_physical_runtime_core),
        )
    )
    for module_name in (
        "grounded_turn_conversation",
        "self_vocal_pcm_motor",
        "w1_grounded_demonstration",
        "w1_loom_auditory_bridge",
        "auditory_token_sequence",
        "auditory_batch_causal_intake",
        "causal_language_construction",
    ):
        assert f"substrate.{module_name}" not in source
    for owner_name in (
        "GroundedTurnConversationOwner",
        "SelfVocalPCMMotorOwner",
        "W1GroundedDemonstrationOwner",
        "W1LoomAuditoryBridge",
        "AuditoryTokenSequenceAuthority",
        "AuditoryBatchCausalIntakeAuthority",
        "CausalLanguageConstructionAuthority",
    ):
        assert owner_name not in source


def test_neuron_retirement_preserves_physics_and_new_auditory_state() -> None:
    organism = Embryo(brain_seed=42, seed_size=5)
    neurons = [
        neuron
        for hemisphere in organism.brain.hemispheres
        for neuron in hemisphere.cluster.neurons
    ]
    first = neurons[0]
    first.binding_atlas = BindingAtlas()
    first.chi_atlas = ChiAtlas()
    first.binding_atlas.record(
        "legacy-word",
        {"language": np.arange(6, dtype=np.float64)},
        7,
    )
    first.chi_atlas.record("legacy-word", 3, 11, tick=7)
    legacy_language = LanguageKrimelack()
    legacy_language.last_input_word = "legacy-word"
    first.krimelack_bank["language"] = legacy_language
    cochlear = first.krimelack_bank["auditory"]
    cochlear._authenticated_full_field_exact_state = {
        "D_k": "exact-D",
        "M_k": "exact-M",
        "R_rev_k": "exact-R",
        "U_star_k": "exact-U",
        "C_k": "exact-C",
        "P_k": "exact-P",
        "B_k": "exact-B",
    }
    cochlear._authenticated_full_field_lanes = {
        "left": ("full", "field"),
        "right": ("full", "field"),
    }
    cochlear._authenticated_full_field_latest = "receipt"

    retired_names = {
        "binding_atlas",
        "chi_atlas",
    }
    before_objects = {
        name: value
        for name, value in first.__dict__.items()
        if name not in retired_names
    }
    before_auditory = copy.deepcopy({
        "exact": cochlear._authenticated_full_field_exact_state,
        "lanes": cochlear._authenticated_full_field_lanes,
        "latest": cochlear._authenticated_full_field_latest,
    })
    neuron_ids_before = tuple(neuron.neuron_id for neuron in neurons)
    couplings_before = copy.deepcopy(first.couplings.__dict__)
    psi_before = copy.deepcopy(first.psi_lattice.__dict__)
    membrane_before = (
        first.membrane_potential,
        first.membrane_rest,
        first.membrane_threshold,
    )
    omega_history_before = copy.deepcopy(first._omega_history)
    krimelack_objects_before = {
        name: id(value)
        for name, value in first.krimelack_bank.items()
    }
    population = organism.growth_snapshot()["total_neurons"]

    proof = retire_neuron_legacy_bindings(organism)

    assert proof["neurons_preserved"] == population
    assert proof["binding_records_retired"] == 1
    assert proof["chi_records_retired"] > 0
    assert proof["language_labels_retired"] == 1
    assert assert_legacy_bindings_retired(organism) == population
    assert organism.growth_snapshot()["total_neurons"] == population
    assert tuple(neuron.neuron_id for neuron in neurons) == (
        neuron_ids_before
    )
    for name, value in before_objects.items():
        assert first.__dict__[name] is value
    assert first.couplings.neighbors == couplings_before["neighbors"]
    assert first.couplings.ring_distances == (
        couplings_before["ring_distances"]
    )
    np.testing.assert_array_equal(
        first.couplings.J,
        couplings_before["J"],
    )
    np.testing.assert_array_equal(
        first.psi_lattice.psi,
        psi_before["psi"],
    )
    assert (
        first.membrane_potential,
        first.membrane_rest,
        first.membrane_threshold,
    ) == membrane_before
    assert first._omega_history == omega_history_before
    assert {
        name: id(value)
        for name, value in first.krimelack_bank.items()
    } == krimelack_objects_before
    assert {
        "exact": cochlear._authenticated_full_field_exact_state,
        "lanes": cochlear._authenticated_full_field_lanes,
        "latest": cochlear._authenticated_full_field_latest,
    } == before_auditory
    assert (
        "last_input_word"
        not in first.krimelack_bank["language"].__dict__
    )
    assert "binding_atlas" not in first.__dict__
    assert "chi_atlas" not in first.__dict__


def _graph_census(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        node_count = json.loads(
            connection.execute(
                "SELECT value FROM metadata WHERE key='node_count'"
            ).fetchone()[0]
        )
        return {
            "bytes": path.stat().st_size,
            "edges": connection.execute(
                "SELECT COUNT(*) FROM edges"
            ).fetchone()[0],
            "nodes": node_count,
            "wave_cells": connection.execute(
                "SELECT COUNT(*) FROM nodes WHERE type_tag='wave_cell'"
            ).fetchone()[0],
            "retired_types": connection.execute(
                "SELECT COUNT(*) FROM nodes "
                "WHERE type_tag IN ('binding_atlas','chi_atlas')"
            ).fetchone()[0],
            "retired_fields": connection.execute(
                "SELECT COUNT(*) FROM edges "
                "WHERE field_name IN ("
                "'binding_atlas','chi_atlas','last_input_word',"
                "'_word_firing_callback')"
            ).fetchone()[0],
        }


def test_retired_neuron_graph_serializes_no_legacy_wave_or_chi_baggage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    organism = Embryo(brain_seed=42, seed_size=5)
    neuron = organism.brain.hemispheres[0].cluster.neurons[0]
    neuron.binding_atlas = BindingAtlas()
    neuron.chi_atlas = ChiAtlas()
    for index in range(128):
        neuron.binding_atlas.record(
            f"legacy-word-{index}",
            np.arange(6, dtype=np.float64) + index,
            index,
        )
        neuron.chi_atlas.record(
            "legacy-word",
            index,
            index,
            tick=index,
        )
    limits = StructuralGraphLimits(
        max_encoded_bytes=256 * 1024 * 1024,
        max_nodes=1_000_000,
        max_depth=256,
    )
    before_path = tmp_path / "organism-before-retirement.sgr"
    retired_path = tmp_path / "organism-retired.sgr"
    restored_path = tmp_path / "organism-restored.sgr"
    with monkeypatch.context() as migration_writer:
        migration_writer.setattr(
            structural_graph_state,
            "_registry",
            _retired_writer_registry,
        )
        save_structural_graph(
            organism,
            before_path,
            limits=limits,
        )
    before = _graph_census(before_path)
    population = organism.growth_snapshot()["total_neurons"]

    restored_legacy = load_authenticated_legacy_organism_graph(
        Embryo,
        before_path,
    )
    assert assert_legacy_bindings_retired(restored_legacy) == population
    save_structural_graph(
        restored_legacy,
        retired_path,
        limits=limits,
    )
    retired = _graph_census(retired_path)

    assert before["wave_cells"] > 0
    assert before["retired_types"] == 2
    assert before["retired_fields"] == 2
    assert retired["wave_cells"] == 0
    assert retired["retired_types"] == 0
    assert retired["retired_fields"] == 0
    assert retired["nodes"] < before["nodes"]
    assert retired["edges"] < before["edges"]
    assert retired["bytes"] < before["bytes"]

    restored = load_structural_graph(
        retired_path,
        expected_root_type=Embryo,
        limits=limits,
    )
    assert restored.growth_snapshot()["total_neurons"] == population
    assert assert_legacy_bindings_retired(restored) == population
    save_structural_graph(
        restored,
        restored_path,
        limits=limits,
    )
    assert restored_path.read_bytes() == retired_path.read_bytes()
    assert _graph_census(restored_path) == retired


def test_current_runtime_requires_explicit_migration_for_retired_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _disable_background_substrate(monkeypatch)
    retired_generation = tmp_path / "retired-generation"
    retired_generation.mkdir()
    _source_generation(retired_generation)
    runtime = Guala()
    try:
        with pytest.raises(
            RuntimeError,
            match="explicit one-way migration tool",
        ):
            runtime.load_full_state(
                str(retired_generation),
                require_exact_binary=True,
            )
    finally:
        runtime.strict_shutdown(timeout=30.0)


def test_post_cutover_save_has_no_legacy_authority_to_regenerate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    baseline = tmp_path / "baseline"
    saved_again = tmp_path / "saved-again"
    _write_exact_state(baseline, monkeypatch)
    cutover = Guala()
    try:
        cutover.load_full_state(
            str(baseline),
            require_exact_binary=True,
        )
        assert cutover._load_successful, cutover._load_errors
        for retired_attribute in (
            "atlas",
            "sections",
            "deep_atlas",
            "_atlas_record",
            "_on_word_firing",
            "_build_emission_system",
        ):
            assert not hasattr(cutover, retired_attribute)
        cutover.save_full_state(str(saved_again))
        assert not {
            path.name
            for path in saved_again.rglob("*")
            if path.is_file()
        }.intersection(cutover.RETIRED_BOOT_FILES)
    finally:
        cutover.strict_shutdown(timeout=30.0)


def test_runtime_legacy_producers_refuse_before_state_changes() -> None:
    guala = Guala()
    try:
        for retired_attribute in (
            "atlas",
            "sections",
            "deep_atlas",
            "_atlas_record",
            "_on_word_firing",
            "_build_emission_system",
        ):
            assert not hasattr(guala, retired_attribute)
    finally:
        guala.strict_shutdown(timeout=30.0)


def test_hot_and_cold_saves_never_recreate_retired_component_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    baseline = tmp_path / "baseline"
    hot_target = tmp_path / "hot-target"
    later_cold = tmp_path / "later-cold"
    _write_exact_state(baseline, monkeypatch)
    cutover = Guala()
    try:
        cutover.load_full_state(
            str(baseline),
            require_exact_binary=True,
        )
        assert cutover._load_successful, cutover._load_errors
        cutover.save_full_state(str(hot_target))
        cutover.save_hot_state(str(hot_target))
        cutover.tick += 1
        cutover.save_full_state(str(later_cold))
        for generation in (hot_target, later_cold):
            assert not (
                generation / "legacy_cognition_archive"
            ).exists()
            core = json.loads(
                (generation / "guala_core.json").read_text()
            )
            assert (
                core["data"]["continuity_contract"]
                == "guala.physical_runtime.v1"
            )
            assert not {
                path.name
                for path in generation.rglob("*")
                if path.is_file()
            }.intersection(cutover.RETIRED_BOOT_FILES)
    finally:
        cutover.strict_shutdown(timeout=30.0)
