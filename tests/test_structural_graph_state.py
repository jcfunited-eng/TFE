"""Exact, bounded persistence contracts for organism and tapestry graphs."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import threading
from collections import deque

import numpy as np
import pytest

from dsf_ai_service.loom_model.structural_graph_state import (
    SCHEMA,
    StructuralGraphError,
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
    structural_registry_contract,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("WAVE_ATLAS_ENABLED", "0")
    instance = Guala()
    try:
        yield instance
    finally:
        instance.shutdown()


@pytest.fixture
def limits():
    return StructuralGraphLimits(
        max_encoded_bytes=256 * 1024 * 1024,
        max_nodes=1_000_000,
        max_depth=256,
    )


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _first_neuron(organism):
    return organism.brain.hemispheres[0].cluster.neurons[0]


def test_organism_roundtrip_preserves_state_aliases_arrays_and_runtime_rewire(
        engine, limits, tmp_path):
    organism = engine.organism
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
    shared = {
        "section": "sound",
        "motif_id": 7,
        "chi": 23,
        "tick": 41,
    }
    neuron.chi_atlas.entries[22] = deque([shared], maxlen=16)
    neuron.chi_atlas.entries[23] = deque([shared], maxlen=16)
    neuron._spike_bus = object()
    neuron._word_firing_callback = lambda *_args: None
    neuron._mood_source = object()
    organism.brain._spike_bus = object()
    organism.brain._guala_ref = object()

    target = tmp_path / "organism.sgr"
    result = save_structural_graph(
        organism, target, limits=limits)
    restored = load_structural_graph(
        target,
        expected_root_type=type(organism),
        limits=limits,
    )

    assert result["schema"] == SCHEMA
    assert result["bytes"] == target.stat().st_size
    assert result["sha256"] == _digest(target)
    assert restored.identity_uuid == organism.identity_uuid
    assert restored.tick == organism.tick
    assert restored.hemi_by_op["em"] is restored.brain.hemispheres[0]
    assert restored.brain._hemi_map["H0"] is restored.brain.hemispheres[0]
    cluster = restored.brain.hemispheres[0].cluster
    restored_neuron = cluster.neurons[0]
    assert restored_neuron._q == 0.625
    assert cluster._neuron_map[restored_neuron.neuron_id] is restored_neuron
    assert (
        restored_neuron.krimelack_bank[restored_neuron.primary_modality]
        is restored_neuron.krimelack
    )
    assert (
        restored_neuron.chi_atlas.entries[22][0]
        is restored_neuron.chi_atlas.entries[23][0]
    )
    restored_dsf = restored_neuron._last_dsf
    assert restored_dsf.to_array().tobytes() == neuron._last_dsf.to_array().tobytes()
    array = restored_neuron._coupling_injection
    assert array.tolist() == view.tolist()
    assert array.dtype == view.dtype
    assert array.shape == view.shape
    assert array.strides == view.strides
    assert array.flags.writeable is False
    assert restored_neuron._spike_bus is None
    assert restored_neuron._word_firing_callback is None
    assert restored_neuron._mood_source is None
    assert isinstance(restored_neuron._neuron_lock, type(threading.Lock()))
    assert restored_neuron._neuron_lock is not neuron._neuron_lock
    assert restored.brain.__dict__.get("_spike_bus") is None
    assert restored.brain.__dict__.get("_guala_ref") is None


def test_tapestry_roundtrip_preserves_voice_state_and_cluster_aliases(
        engine, limits, tmp_path):
    tapestry = engine.tapestry
    tapestry._engine_prev_word = "hello"
    target = tmp_path / "tapestry.sgr"

    save_structural_graph(tapestry, target, limits=limits)
    restored = load_structural_graph(
        target,
        expected_root_type=type(tapestry),
        limits=limits,
    )

    assert restored._engine_prev_word == "hello"
    assert restored._tick == tapestry._tick
    assert restored.total_neurons == tapestry.total_neurons
    assert len(restored.mosaics) == restored.n_mosaics
    cluster = restored.mosaics[0].clusters[0]
    neuron = cluster.neurons[0]
    assert cluster._neuron_map[neuron.neuron_id] is neuron


def test_large_array_uses_bounded_streaming_roundtrip(
        engine, limits, tmp_path):
    neuron = _first_neuron(engine.organism)
    source = np.arange(160_000, dtype=np.float64).reshape(400, 400)
    neuron._coupling_injection = source
    target = tmp_path / "large-array.sgr"

    save_structural_graph(engine.organism, target, limits=limits)
    restored = load_structural_graph(
        target,
        expected_root_type=type(engine.organism),
        limits=limits,
    )

    actual = _first_neuron(restored)._coupling_injection
    assert actual.shape == source.shape
    assert actual.dtype == source.dtype
    assert actual.tobytes() == source.tobytes()


def test_two_pass_output_is_stable(engine, limits, tmp_path):
    first = tmp_path / "first.sgr"
    second = tmp_path / "second.sgr"
    save_structural_graph(engine.organism, first, limits=limits)
    save_structural_graph(engine.organism, second, limits=limits)
    assert first.read_bytes() == second.read_bytes()


def test_mutation_between_passes_fails_and_preserves_existing_artifact(
        engine, limits, tmp_path, monkeypatch):
    import dsf_ai_service.loom_model.structural_graph_state as module

    target = tmp_path / "organism.sgr"
    target.write_bytes(b"prior-authoritative-artifact")
    original = target.read_bytes()
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
            match="mutated during serialization"):
        save_structural_graph(
            engine.organism, target, limits=limits)
    assert target.read_bytes() == original


def test_registry_rejects_unregistered_durable_field(
        engine, limits, tmp_path):
    neuron = _first_neuron(engine.organism)
    neuron._unregistered_state = "must not disappear"
    with pytest.raises(
            StructuralGraphError,
            match="unregistered durable fields.*_unregistered_state"):
        save_structural_graph(
            engine.organism, tmp_path / "bad.sgr", limits=limits)


def test_registry_covers_every_fresh_object_field(engine):
    contract = structural_registry_contract()
    seen = set()

    def walk(value):
        if value is None or isinstance(
                value, (bool, int, float, complex, str, bytes, np.generic)):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        if isinstance(value, np.ndarray):
            return
        if type(value) is dict:
            for key, item in value.items():
                walk(key)
                walk(item)
            return
        if type(value) in (list, tuple, set, frozenset) or isinstance(
                value, deque):
            for item in value:
                walk(item)
            return
        matching = [
            row for row in contract.values()
            if set(value.__dict__).issubset(
                set(row["durable_fields"]) | set(row["runtime_fields"]))
        ]
        assert matching, (
            f"no registry contract covers "
            f"{type(value).__module__}.{type(value).__qualname__}: "
            f"{sorted(value.__dict__)}"
        )
        for field, item in value.__dict__.items():
            if all(field not in row["runtime_fields"] for row in matching):
                walk(item)

    walk(engine.organism)
    walk(engine.tapestry)


def test_node_capacity_fails_closed(engine, tmp_path):
    limits = StructuralGraphLimits(
        max_encoded_bytes=256 * 1024 * 1024,
        max_nodes=10,
        max_depth=256,
    )
    with pytest.raises(StructuralGraphError, match="node capacity"):
        save_structural_graph(
            engine.organism, tmp_path / "too-many.sgr", limits=limits)


def test_encoded_capacity_fails_closed(engine, tmp_path):
    limits = StructuralGraphLimits(
        max_encoded_bytes=4096,
        max_nodes=1_000_000,
        max_depth=256,
    )
    with pytest.raises(StructuralGraphError, match="encoded-byte capacity"):
        save_structural_graph(
            engine.organism, tmp_path / "too-large.sgr", limits=limits)


def test_depth_capacity_fails_closed(engine, limits, tmp_path):
    neuron = _first_neuron(engine.organism)
    nested = []
    cursor = nested
    for _ in range(12):
        child = []
        cursor.append(child)
        cursor = child
    neuron._last_events = nested
    shallow = StructuralGraphLimits(
        max_encoded_bytes=limits.max_encoded_bytes,
        max_nodes=limits.max_nodes,
        max_depth=8,
    )
    with pytest.raises(StructuralGraphError, match="nesting depth"):
        save_structural_graph(
            engine.organism, tmp_path / "too-deep.sgr", limits=shallow)


def test_unknown_class_tag_and_extra_sqlite_object_are_rejected(
        engine, limits, tmp_path):
    target = tmp_path / "organism.sgr"
    save_structural_graph(engine.organism, target, limits=limits)

    connection = sqlite3.connect(target)
    root_id = connection.execute(
        "SELECT value FROM metadata WHERE key='root_id'").fetchone()[0]
    root_id = int(__import__("json").loads(root_id))
    connection.execute(
        "UPDATE nodes SET type_tag='unregistered' WHERE node_id=?",
        (root_id,),
    )
    connection.commit()
    connection.close()
    with pytest.raises(StructuralGraphError, match="root node differs"):
        load_structural_graph(
            target,
            expected_root_type=type(engine.organism),
            limits=limits,
        )

    save_structural_graph(engine.organism, target, limits=limits)
    connection = sqlite3.connect(target)
    connection.execute("CREATE TABLE injected(value TEXT)")
    connection.commit()
    connection.close()
    with pytest.raises(
            StructuralGraphError,
            match="unexpected SQLite object"):
        load_structural_graph(
            target,
            expected_root_type=type(engine.organism),
            limits=limits,
        )


def test_persistence_admission_is_the_only_publication_writer(
        engine, limits, tmp_path):
    class Admission:
        def __init__(self):
            self.calls = []

        def copy_regular_file(self, source, target):
            self.calls.append((os.fspath(source), os.fspath(target)))
            shutil.copyfile(source, target)

    admission = Admission()
    target = tmp_path / "admitted.sgr"
    result = save_structural_graph(
        engine.organism,
        target,
        limits=limits,
        persistence_admission=admission,
    )
    assert len(admission.calls) == 1
    assert admission.calls[0][1] == os.fspath(target)
    assert result["sha256"] == _digest(target)


def test_wrong_root_type_is_rejected(engine, limits, tmp_path):
    target = tmp_path / "organism.sgr"
    save_structural_graph(engine.organism, target, limits=limits)
    with pytest.raises(StructuralGraphError, match="root type differs"):
        load_structural_graph(
            target,
            expected_root_type=type(engine.tapestry),
            limits=limits,
        )


def test_traversal_indexes_do_not_remain_in_finished_artifact(
        engine, limits, tmp_path):
    target = tmp_path / "organism.sgr"
    save_structural_graph(engine.organism, target, limits=limits)
    connection = sqlite3.connect(
        f"{target.resolve().as_uri()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%'"
            )
        }
        assert names == {"metadata", "nodes", "edges"}
        assert connection.execute(
            "PRAGMA freelist_count").fetchone()[0] == 0
    finally:
        connection.close()


def test_symlink_is_rejected_before_sqlite_open(
        engine, limits, tmp_path, monkeypatch):
    import dsf_ai_service.loom_model.structural_graph_state as module

    target = tmp_path / "organism.sgr"
    save_structural_graph(engine.organism, target, limits=limits)
    link = tmp_path / "linked.sgr"
    link.symlink_to(target)
    calls = []

    def record_connect(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("SQLite must not open a linked artifact")

    monkeypatch.setattr(module, "_connect", record_connect)
    with pytest.raises(
            StructuralGraphError,
            match="not a regular file"):
        load_structural_graph(
            link,
            expected_root_type=type(engine.organism),
            limits=limits,
        )
    assert calls == []


def test_unreachable_node_is_rejected(engine, limits, tmp_path):
    target = tmp_path / "organism.sgr"
    save_structural_graph(engine.organism, target, limits=limits)
    connection = sqlite3.connect(target)
    node_id = connection.execute(
        "INSERT INTO nodes(kind,payload) VALUES('none',NULL)"
    ).lastrowid
    connection.execute(
        "UPDATE metadata SET value=? WHERE key='node_count'",
        (__import__("json").dumps(node_id).encode("utf-8"),),
    )
    connection.commit()
    connection.close()
    with pytest.raises(
            StructuralGraphError,
            match="unreachable nodes"):
        load_structural_graph(
            target,
            expected_root_type=type(engine.organism),
            limits=limits,
        )
