"""Definitive neuronal Chi/Binding retirement and migration contracts."""

from __future__ import annotations

import itertools
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from dsf_ai_service.loom_model import structural_graph_state
from dsf_ai_service.loom_model.binding_atlas import BindingAtlas
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.neuronal_l6 import L6_TCL
from dsf_ai_service.loom_model.neuron import LoomNeuron
from dsf_ai_service.loom_model.physical_oscillators import (
    PhysicalSignalOscillator,
)
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphError,
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
    structural_registry_contract,
)
from dsf_ai_service.loom_model.tapestry import LoomTapestry
from dsf_ai_service.substrate.retired_legacy_cognition import (
    assert_legacy_bindings_retired,
)
from dsf_ai_service.v4.gualaloom_v4_chi_atlas_l6 import (
    ChiAtlas,
    L6_TCL as LegacyL6TCL,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
from tools.guala_legacy_organism_graph_reader import (
    _retired_registry,
    load_authenticated_legacy_organism_graph,
)
from wave_spillover import Cell as LegacyWaveCell


LIMITS = StructuralGraphLimits(
    max_encoded_bytes=256 * 1024 * 1024,
    max_nodes=1_000_000,
    max_depth=256,
)


def _retired_writer_registry(**_ignored):
    by_type, by_tag = _retired_registry()
    by_type[LegacyWaveCell] = by_tag["wave_cell"]
    return by_type, by_tag


def _neurons(organism: Embryo):
    return [
        neuron
        for hemisphere in organism.brain.hemispheres
        for neuron in hemisphere.cluster.neurons
    ]


def _freeze(value):
    if isinstance(value, np.ndarray):
        return (
            "ndarray",
            value.dtype.str,
            value.shape,
            value.strides,
            value.flags.writeable,
            value.tobytes(),
        )
    if isinstance(value, dict):
        return tuple(
            (key, _freeze(item))
            for key, item in sorted(value.items(), key=lambda pair: repr(pair[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if hasattr(value, "__dict__"):
        physical_state = {
            key: item
            for key, item in value.__dict__.items()
            if key != "last_input_word"
        }
        return (
            type(value).__module__,
            type(value).__qualname__,
            _freeze(physical_state),
        )
    return value


def _physical_fingerprint(organism: Embryo):
    neuron_state = []
    for neuron in _neurons(organism):
        dsf = None
        if neuron._last_dsf is not None:
            dsf = neuron._last_dsf.to_array().tobytes()
        sensory = tuple(
            (name, _freeze(krimelack))
            for name, krimelack in sorted(neuron.krimelack_bank.items())
        )
        neuron_state.append(
            (
                neuron.neuron_id,
                tuple(neuron.couplings.neighbors),
                tuple(neuron.couplings.ring_distances),
                _freeze(neuron.couplings.J),
                _freeze(neuron.psi_lattice.psi),
                (
                    neuron.membrane_potential,
                    neuron.membrane_rest,
                    neuron.membrane_threshold,
                    neuron.tau_m_ms,
                    neuron.refractory_period_ms,
                    neuron.last_update_time_s,
                    neuron.refractory_until_s,
                ),
                (neuron.l6_tcl.n_start, neuron.l6_tcl.capture_threshold),
                dsf,
                sensory,
            )
        )
    cross_hemi = tuple(
        (
            hemisphere.hemi_id,
            tuple(
                (
                    neuron_id,
                    tuple(couplings.targets),
                    _freeze(couplings.J),
                )
                for neuron_id, couplings in sorted(
                    hemisphere.cross_hemi_couplings.items()
                )
            ),
        )
        for hemisphere in organism.brain.hemispheres
    )
    return tuple(neuron_state), cross_hemi


def _retired_sql_census(path: Path):
    with sqlite3.connect(path) as connection:
        return (
            connection.execute(
                "SELECT COUNT(*) FROM nodes "
                "WHERE type_tag IN ('chi_atlas','binding_atlas')"
            ).fetchone()[0],
            connection.execute(
                "SELECT COUNT(*) FROM edges "
                "WHERE field_name IN ('chi_atlas','binding_atlas')"
            ).fetchone()[0],
            connection.execute(
                "SELECT COUNT(*) FROM edges "
                "WHERE field_name IN "
                "('last_input_word','_word_firing_callback')"
            ).fetchone()[0],
        )


def test_chi_free_l6_is_exactly_the_pre_split_l6() -> None:
    current = L6_TCL()
    legacy = LegacyL6TCL()
    for values in itertools.product((-0.75, 0.0, 0.75), repeat=8):
        dsf = DSF(
            D_k=values[0],
            M_k=values[1],
            R_rev=values[2],
            U_star=values[3],
            C_k=values[4],
            P_k=values[5],
            B_k=values[6],
            S_UF=values[7],
        )
        assert current.n_eff(dsf) == legacy.n_eff(dsf)
        assert current.captured(dsf) is legacy.captured(dsf)
        assert current.structural_lock(dsf) is legacy.structural_lock(dsf)
    assert current.__dict__ == legacy.__dict__


def test_fresh_neurons_and_graph_emit_no_chi_or_binding(
    tmp_path: Path,
) -> None:
    organism = Embryo(brain_seed=42, seed_size=5)
    for neuron in _neurons(organism):
        assert "chi_atlas" not in neuron.__dict__
        assert "binding_atlas" not in neuron.__dict__
        assert "_word_firing_callback" not in neuron.__dict__
        for krimelack in neuron.krimelack_bank.values():
            assert "last_input_word" not in krimelack.__dict__
    registry = structural_registry_contract()
    assert "chi_atlas" not in registry
    assert "binding_atlas" not in registry
    assert {
        "chi_atlas",
        "binding_atlas",
    }.isdisjoint(registry["loom_neuron"]["durable_fields"])

    graph = tmp_path / "fresh.sgr"
    save_structural_graph(organism, graph, limits=LIMITS)
    assert _retired_sql_census(graph) == (0, 0, 0)


def test_neuron_refuses_symbols_without_mutating_physical_state() -> None:
    neuron = LoomNeuron("physical-refusal")
    assert not hasattr(neuron, "set_word_firing_callback")
    assert not hasattr(neuron, "last_input_word")
    assert not hasattr(neuron, "experience_moment")
    assert not hasattr(neuron, "encode_state")
    before = _freeze(neuron.__getstate__())

    for symbolic in ("hello", b"hello", bytearray(b"hello"), {"word": "hello"}):
        with np.testing.assert_raises(TypeError):
            neuron.step(symbolic, tick=11)
        assert _freeze(neuron.__getstate__()) == before


def test_numeric_signal_advances_full_neuronal_field() -> None:
    neuron = LoomNeuron("physical-signal")
    signal = np.sin(np.linspace(0.0, 12.0 * np.pi, 512))
    result = neuron.step(signal, tick=11)

    assert neuron._tick == 11
    assert result["dsf"] is neuron._last_dsf
    assert result["n_eff"] == neuron.l6_tcl.n_eff(neuron._last_dsf)
    assert tuple(result["dsf"].to_array()) == (
        result["dsf"].D_k,
        result["dsf"].M_k,
        result["dsf"].R_rev,
        result["dsf"].U_star,
        result["dsf"].C_k,
        result["dsf"].P_k,
        result["dsf"].B_k,
        result["dsf"].S_UF,
    )
    assert "_word_firing_callback" not in neuron.__dict__
    assert all(
        "last_input_word" not in krimelack.__dict__
        for krimelack in neuron.krimelack_bank.values()
    )


def test_legacy_object_state_discards_callback_and_label_with_physical_parity(
) -> None:
    source = LoomNeuron("legacy-object")
    legacy_language = PhysicalSignalOscillator(label="retired-language")
    legacy_language.last_input_word = "retired-label"
    source.krimelack_bank["language"] = legacy_language
    state = source.__getstate__()
    state["_word_firing_callback"] = lambda *_args: None
    expected_state = dict(state)
    expected_state.pop("_word_firing_callback")
    expected = _freeze(expected_state)

    restored = LoomNeuron.__new__(LoomNeuron)
    restored.__setstate__(state)

    assert "_word_firing_callback" not in restored.__dict__
    assert (
        "last_input_word"
        not in restored.krimelack_bank["language"].__dict__
    )
    assert _freeze(restored.__getstate__()) == expected


def test_authenticated_old_graph_migrates_with_exact_physical_parity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    organism = Embryo(brain_seed=42, seed_size=5)
    neuron = _neurons(organism)[0]
    neuron.binding_atlas = BindingAtlas()
    neuron.chi_atlas = ChiAtlas()
    neuron.binding_atlas.record(
        "retired-label",
        {"auditory": np.arange(12, dtype=np.float64)},
        17,
    )
    neuron.chi_atlas.record("retired-label", 7, 31, tick=17)
    neuron._lane_P = {
        ("retired", "auditory"): np.arange(
            24, dtype=np.float64).reshape(2, 12)
    }
    organism._scP = {"retired": np.eye(3, dtype=np.float64)}
    legacy_language = PhysicalSignalOscillator(label="retired-language")
    legacy_language.last_input_word = "retired-label"
    neuron.krimelack_bank["language"] = legacy_language
    neuron._last_dsf = DSF(
        D_k=-0.25,
        M_k=0.5,
        R_rev=0.125,
        U_star=0.75,
        C_k=0.625,
        P_k=0.375,
        B_k=0.875,
        S_UF=1.0,
    )
    cochlear = neuron.krimelack_bank["auditory"]
    cochlear._authenticated_full_field_exact_state = {
        "D_k": "D",
        "M_k": "M",
        "R_rev_k": "R",
        "U_star_k": "U",
        "C_k": "C",
        "P_k": "P",
        "B_k": "B",
    }
    cochlear._authenticated_full_field_lanes = {
        "left": ("full", "field"),
        "right": ("full", "field"),
    }
    cochlear._authenticated_full_field_latest = "receipt"
    expected = _physical_fingerprint(organism)

    old_graph = tmp_path / "old-authenticated.sgr"
    with monkeypatch.context() as migration_writer:
        migration_writer.setattr(
            structural_graph_state,
            "_registry",
            _retired_writer_registry,
        )
        save_structural_graph(organism, old_graph, limits=LIMITS)
    assert _retired_sql_census(old_graph) == (2, 2, 1)

    migrated = load_authenticated_legacy_organism_graph(
        Embryo,
        old_graph,
    )
    assert assert_legacy_bindings_retired(migrated) == len(_neurons(migrated))
    assert "_scP" not in migrated.__dict__
    assert all("_lane_P" not in item.__dict__ for item in _neurons(migrated))
    assert _physical_fingerprint(migrated) == expected

    cold_one = tmp_path / "cold-one.sgr"
    cold_two = tmp_path / "cold-two.sgr"
    save_structural_graph(migrated, cold_one, limits=LIMITS)
    assert _retired_sql_census(cold_one) == (0, 0, 0)
    restored = load_structural_graph(
        cold_one,
        expected_root_type=Embryo,
        limits=LIMITS,
    )
    assert _physical_fingerprint(restored) == expected
    save_structural_graph(restored, cold_two, limits=LIMITS)
    assert cold_two.read_bytes() == cold_one.read_bytes()


def test_authenticated_old_tapestry_graph_migrates_without_retired_types(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tapestry = LoomTapestry(
        "migration",
        n_mosaics=1,
        mosaic_kwargs={
            "n_clusters": 1,
            "neurons_per_cluster": 5,
            "k_neighbors": 4,
        },
        seed=19,
    )
    assert not hasattr(tapestry, "compose")
    assert not hasattr(tapestry, "_dominant_word")
    assert not hasattr(tapestry, "expose_corpus")
    neurons = [
        neuron
        for mosaic in tapestry.mosaics
        for cluster in mosaic.clusters
        for neuron in cluster.neurons
    ]
    neuron = neurons[0]
    neuron.binding_atlas = BindingAtlas()
    neuron.chi_atlas = ChiAtlas()
    neuron.binding_atlas.record(
        "retired-label",
        np.arange(6, dtype=np.float64),
        3,
    )
    neuron.chi_atlas.record("retired-label", 2, 9, tick=3)

    old_graph = tmp_path / "old-tapestry.sgr"
    with monkeypatch.context() as migration_writer:
        migration_writer.setattr(
            structural_graph_state,
            "_registry",
            _retired_writer_registry,
        )
        save_structural_graph(tapestry, old_graph, limits=LIMITS)
    assert _retired_sql_census(old_graph) == (2, 2, 0)

    migrated = load_authenticated_legacy_organism_graph(
        LoomTapestry,
        old_graph,
    )
    assert assert_legacy_bindings_retired(migrated) == len(neurons)
    assert "tapestry" not in structural_registry_contract()
    with pytest.raises(
        StructuralGraphError,
        match="unregistered structural class: .*LoomTapestry",
    ):
        save_structural_graph(
            migrated,
            tmp_path / "forbidden-current-tapestry.sgr",
            limits=LIMITS,
        )
