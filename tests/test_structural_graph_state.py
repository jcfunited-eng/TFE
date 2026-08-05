"""Exact bounded graph contracts for the current physical organism."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
from pathlib import Path

import numpy as np
import pytest

from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.physical_oscillators import (
    PhysicalSensoryOscillatorBank,
    PhysicalSignalOscillator,
)
from dsf_ai_service.loom_model.structural_graph_state import (
    SCHEMA,
    StructuralGraphError,
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
    structural_registry_contract,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF


@pytest.fixture
def organism() -> Embryo:
    return Embryo(brain_seed=42, seed_size=4)


@pytest.fixture
def limits() -> StructuralGraphLimits:
    return StructuralGraphLimits(
        max_encoded_bytes=256 * 1024 * 1024,
        max_nodes=1_000_000,
        max_depth=256,
    )


def _first_neuron(organism: Embryo):
    return organism.brain.hemispheres[0].cluster.neurons[0]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(
    organism: Embryo,
    path: Path,
    limits: StructuralGraphLimits,
):
    return save_structural_graph(organism, path, limits=limits)


def _load(path: Path, limits: StructuralGraphLimits) -> Embryo:
    return load_structural_graph(
        path,
        expected_root_type=Embryo,
        limits=limits,
    )


def test_roundtrip_preserves_full_neuron_and_dsf_state(
    organism,
    limits,
    tmp_path,
):
    neuron = _first_neuron(organism)
    neuron._q = 0.625
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
    source = np.arange(30, dtype=np.float64).reshape(5, 6)
    view = source[::-1, ::2]
    view.flags.writeable = False
    neuron._coupling_injection = view
    neuron._spike_bus = object()
    neuron._mood_source = object()
    organism.brain._spike_bus = object()
    organism.brain._guala_ref = object()

    target = tmp_path / "organism.sgr"
    result = _save(organism, target, limits)
    restored = _load(target, limits)
    restored_neuron = _first_neuron(restored)

    assert result == {
        "bytes": target.stat().st_size,
        "schema": SCHEMA,
        "sha256": _digest(target),
    }
    assert restored.identity_uuid == organism.identity_uuid
    assert restored.hemi_by_op["em"] is restored.brain.hemispheres[0]
    assert (
        restored.brain._hemi_map["H0"]
        is restored.brain.hemispheres[0]
    )
    cluster = restored.brain.hemispheres[0].cluster
    assert (
        cluster._neuron_map[restored_neuron.neuron_id]
        is restored_neuron
    )
    assert (
        restored_neuron.krimelack_bank[
            restored_neuron.primary_modality
        ]
        is restored_neuron.krimelack
    )
    assert type(restored_neuron.krimelack) is PhysicalSignalOscillator
    assert (
        type(restored_neuron.sensory_bank)
        is PhysicalSensoryOscillatorBank
    )
    assert restored_neuron.primary_modality == "physical_signal"
    assert "binding_atlas" not in restored_neuron.__dict__
    assert "chi_atlas" not in restored_neuron.__dict__
    assert (
        restored_neuron._last_dsf.to_array().tobytes()
        == neuron._last_dsf.to_array().tobytes()
    )
    array = restored_neuron._coupling_injection
    assert array.tolist() == view.tolist()
    assert array.dtype == view.dtype
    assert array.shape == view.shape
    assert array.strides == view.strides
    assert array.flags.writeable is False
    assert restored_neuron._spike_bus is None
    assert restored_neuron._mood_source is None
    assert isinstance(restored_neuron._neuron_lock, type(threading.Lock()))
    assert restored.brain.__dict__.get("_spike_bus") is None
    assert restored.brain.__dict__.get("_guala_ref") is None

    with sqlite3.connect(target) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM nodes "
            "WHERE type_tag IN ('chi_atlas','binding_atlas')"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM edges "
            "WHERE field_name IN ('chi_atlas','binding_atlas')"
        ).fetchone()[0] == 0


def test_large_array_roundtrip_is_exact(
    organism,
    limits,
    tmp_path,
):
    source = np.arange(160_000, dtype=np.float64).reshape(400, 400)
    _first_neuron(organism)._coupling_injection = source
    target = tmp_path / "large-array.sgr"
    _save(organism, target, limits)
    actual = _first_neuron(_load(target, limits))._coupling_injection
    assert actual.shape == source.shape
    assert actual.dtype == source.dtype
    assert actual.tobytes() == source.tobytes()


def test_two_independent_writes_are_byte_exact(
    organism,
    limits,
    tmp_path,
):
    first = tmp_path / "first.sgr"
    second = tmp_path / "second.sgr"
    _save(organism, first, limits)
    _save(organism, second, limits)
    assert first.read_bytes() == second.read_bytes()


def test_mutation_between_passes_fails_without_overwrite(
    organism,
    limits,
    tmp_path,
    monkeypatch,
):
    import dsf_ai_service.loom_model.structural_graph_state as module

    target = tmp_path / "organism.sgr"
    target.write_bytes(b"prior-authoritative-artifact")
    real_write = module._write_pass
    calls = 0

    def mutate_after_first(root, path, **kwargs):
        nonlocal calls
        calls += 1
        real_write(root, path, **kwargs)
        if calls == 1:
            root.tick += 1

    monkeypatch.setattr(module, "_write_pass", mutate_after_first)
    with pytest.raises(
        StructuralGraphError,
        match="mutated during serialization",
    ):
        _save(organism, target, limits)
    assert target.read_bytes() == b"prior-authoritative-artifact"


def test_unregistered_durable_field_fails_closed(
    organism,
    limits,
    tmp_path,
):
    _first_neuron(organism)._unregistered_state = "not admissible"
    with pytest.raises(
        StructuralGraphError,
        match="unregistered durable fields.*_unregistered_state",
    ):
        _save(organism, tmp_path / "bad.sgr", limits)


def test_registry_preserves_full_physical_neuron_surface():
    contract = structural_registry_contract()
    neuron_fields = set(contract["loom_neuron"]["durable_fields"])
    assert {
        "_last_commit_chi",
        "_last_dsf",
        "chi_position",
        "krimelack",
        "krimelack_bank",
        "sensory_bank",
    }.issubset(neuron_fields)
    assert contract["language_krimelack"]["durable_fields"] == (
        "dt",
        "events",
        "kappa",
        "label",
        "n_events",
        "omega_0",
        "phase",
        "t",
        "threshold",
        "winding",
    )


@pytest.mark.parametrize(
    ("capacity", "match"),
    (
        (
            StructuralGraphLimits(
                max_encoded_bytes=256 * 1024 * 1024,
                max_nodes=10,
                max_depth=256,
            ),
            "node capacity",
        ),
        (
            StructuralGraphLimits(
                max_encoded_bytes=4096,
                max_nodes=1_000_000,
                max_depth=256,
            ),
            "encoded-byte capacity",
        ),
    ),
)
def test_capacity_limits_fail_closed(
    organism,
    capacity,
    match,
    tmp_path,
):
    with pytest.raises(StructuralGraphError, match=match):
        _save(organism, tmp_path / "over-capacity.sgr", capacity)


def test_depth_limit_fails_closed(organism, limits, tmp_path):
    nested = []
    cursor = nested
    for _ in range(12):
        child = []
        cursor.append(child)
        cursor = child
    _first_neuron(organism)._last_events = nested
    shallow = StructuralGraphLimits(
        max_encoded_bytes=limits.max_encoded_bytes,
        max_nodes=limits.max_nodes,
        max_depth=8,
    )
    with pytest.raises(StructuralGraphError, match="nesting depth"):
        _save(organism, tmp_path / "too-deep.sgr", shallow)


def test_unknown_root_and_injected_table_are_rejected(
    organism,
    limits,
    tmp_path,
):
    target = tmp_path / "organism.sgr"
    _save(organism, target, limits)
    with sqlite3.connect(target) as connection:
        root_id = json.loads(
            connection.execute(
                "SELECT value FROM metadata WHERE key='root_id'"
            ).fetchone()[0]
        )
        connection.execute(
            "UPDATE nodes SET type_tag='unregistered' WHERE node_id=?",
            (root_id,),
        )
    with pytest.raises(StructuralGraphError, match="root node differs"):
        _load(target, limits)

    _save(organism, target, limits)
    with sqlite3.connect(target) as connection:
        connection.execute("CREATE TABLE injected(value TEXT)")
    with pytest.raises(
        StructuralGraphError,
        match="unexpected SQLite object",
    ):
        _load(target, limits)


def test_publication_uses_supplied_admission(
    organism,
    limits,
    tmp_path,
):
    class Admission:
        def __init__(self):
            self.calls = []

        def copy_regular_file(self, source, target):
            self.calls.append((os.fspath(source), os.fspath(target)))
            shutil.copyfile(source, target)

    admission = Admission()
    target = tmp_path / "admitted.sgr"
    result = save_structural_graph(
        organism,
        target,
        limits=limits,
        persistence_admission=admission,
    )
    assert len(admission.calls) == 1
    assert admission.calls[0][1] == os.fspath(target)
    assert result["sha256"] == _digest(target)


def test_wrong_root_type_is_rejected(
    organism,
    limits,
    tmp_path,
):
    target = tmp_path / "organism.sgr"
    _save(organism, target, limits)
    with pytest.raises(StructuralGraphError, match="root type differs"):
        load_structural_graph(
            target,
            expected_root_type=PhysicalSignalOscillator,
            limits=limits,
        )


def test_symlink_rejected_before_sqlite_open(
    organism,
    limits,
    tmp_path,
    monkeypatch,
):
    import dsf_ai_service.loom_model.structural_graph_state as module

    target = tmp_path / "organism.sgr"
    _save(organism, target, limits)
    link = tmp_path / "linked.sgr"
    link.symlink_to(target)
    calls = []

    def record_connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("SQLite must not open a linked artifact")

    monkeypatch.setattr(module, "_connect", record_connect)
    with pytest.raises(
        StructuralGraphError,
        match="not a regular file",
    ):
        _load(link, limits)
    assert calls == []


def test_unreachable_node_is_rejected(
    organism,
    limits,
    tmp_path,
):
    target = tmp_path / "organism.sgr"
    _save(organism, target, limits)
    with sqlite3.connect(target) as connection:
        namespace_size = json.loads(
            connection.execute(
                "SELECT value FROM metadata "
                "WHERE key='scalar_namespace_size'"
            ).fetchone()[0]
        )
        composite_count = connection.execute(
            "SELECT COUNT(*) FROM nodes WHERE node_id <= ?",
            (namespace_size,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO nodes(node_id,kind,payload) VALUES(?,?,NULL)",
            (composite_count + 1, "list"),
        )
        node_count = connection.execute(
            "SELECT COUNT(*) FROM nodes"
        ).fetchone()[0]
        connection.execute(
            "UPDATE metadata SET value=? WHERE key='node_count'",
            (json.dumps(node_count).encode("utf-8"),),
        )
    with pytest.raises(StructuralGraphError, match="unreachable nodes"):
        _load(target, limits)
