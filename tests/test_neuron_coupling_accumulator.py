"""Fixed-memory coupling-signal accumulation and migration contracts."""

from __future__ import annotations

import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

from dsf_ai_service.loom_model import structural_graph_state
from dsf_ai_service.loom_model.embryo import Embryo
from dsf_ai_service.loom_model.neuron import J_MAX, LoomNeuron
from dsf_ai_service.loom_model.structural_graph_state import (
    StructuralGraphLimits,
    load_structural_graph,
    save_structural_graph,
    structural_registry_contract,
)
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF


LIMITS = StructuralGraphLimits(
    max_encoded_bytes=256 * 1024 * 1024,
    max_nodes=1_000_000,
    max_depth=256,
)


def _source_field() -> DSF:
    return DSF(
        D_k=0.25,
        M_k=-0.5,
        R_rev=0.125,
        U_star=0.75,
        C_k=0.625,
        P_k=0.375,
        B_k=1.0,
        S_UF=0.875,
    )


def _float_bits(value: float) -> bytes:
    return struct.pack(">d", value)


def _receive(neuron: LoomNeuron, values: list[float]) -> None:
    source = _source_field()
    for tick, value in enumerate(values):
        neuron.receive_coupling_spike(
            "physical-source",
            value,
            source,
            tick,
        )


def _former_contributions(values: list[float]) -> list[float]:
    return [min(value, J_MAX) for value in values]


def _first_neuron(organism: Embryo) -> LoomNeuron:
    return organism.brain.hemispheres[0].cluster.neurons[0]


def test_repeated_receives_retain_only_fixed_size_scalars() -> None:
    neuron = LoomNeuron("bounded-coupling")
    field_names = tuple(neuron.__dict__)
    retained_shape = (
        len(neuron.__dict__),
        neuron._coupling_injection.shape,
        neuron._coupling_injection.nbytes,
        sys.getsizeof(neuron._coupling_signal_sum),
        sys.getsizeof(neuron._coupling_signal_pending),
    )

    _receive(neuron, [0.125] * 100_000)

    assert tuple(neuron.__dict__) == field_names
    assert (
        len(neuron.__dict__),
        neuron._coupling_injection.shape,
        neuron._coupling_injection.nbytes,
        sys.getsizeof(neuron._coupling_signal_sum),
        sys.getsizeof(neuron._coupling_signal_pending),
    ) == retained_shape
    assert type(neuron._coupling_signal_sum) is float
    assert neuron._coupling_signal_pending is True
    assert "_coupling_signal_accum" not in neuron.__dict__


@pytest.mark.parametrize(
    "values",
    (
        [0.125, 0.5, -0.25, 1.75],
        [
            1.0,
            2.0 ** -53,
            -1.0,
            2.0 ** -1074,
            -(2.0 ** -1074),
            0.1,
            -0.1,
            1.0e-300,
            -1.0e-300,
        ],
    ),
)
def test_ordered_sum_and_next_step_match_former_list_bits(
    values: list[float],
) -> None:
    current = LoomNeuron("current")
    former = LoomNeuron("former")
    _receive(current, values)
    _receive(former, values)

    former_ordered_sum = sum(_former_contributions(values))
    assert _float_bits(current._coupling_signal_sum) == _float_bits(
        former_ordered_sum
    )

    # This assignment is the exact state the former implementation produced
    # at `sum(_coupling_signal_accum)` immediately before transduction.
    former._coupling_signal_sum = former_ordered_sum
    former._coupling_signal_pending = bool(values)
    physical_signal = np.array(
        [0.0, 0.25, -0.5, 0.75, -1.0, 0.5],
        dtype=np.float64,
    )

    current_result = current.step(physical_signal, tick=29)
    former_result = former.step(physical_signal, tick=29)

    assert current_result["committed"] is former_result["committed"]
    assert current_result["n_eff"] == former_result["n_eff"]
    assert (
        current_result["dsf"].to_array().tobytes()
        == former_result["dsf"].to_array().tobytes()
    )
    assert (
        current.psi_lattice.psi.tobytes()
        == former.psi_lattice.psi.tobytes()
    )
    assert current.krimelack.phase == former.krimelack.phase
    assert current.krimelack.winding == former.krimelack.winding
    assert current._last_events == former._last_events
    assert current._coupling_signal_sum == former._coupling_signal_sum == 0.0
    assert current._coupling_signal_pending is False
    assert former._coupling_signal_pending is False


def test_old_list_graph_migrates_to_exact_scalar_and_cold_restores(
    tmp_path: Path,
    monkeypatch,
) -> None:
    organism = Embryo(brain_seed=42, seed_size=5)
    neuron = _first_neuron(organism)
    old_values = [
        1.0,
        2.0 ** -53,
        -1.0,
        0.1,
        -0.1,
        1.0e-300,
    ]
    expected = sum(old_values)
    neuron.__dict__.pop("_coupling_signal_sum")
    neuron.__dict__.pop("_coupling_signal_pending")
    neuron._coupling_signal_accum = list(old_values)

    old_graph = tmp_path / "old-list.sgr"
    current_registry = structural_graph_state._registry
    with monkeypatch.context() as migration_writer:
        migration_writer.setattr(
            structural_graph_state,
            "_registry",
            lambda **kwargs: current_registry(
                include_retired_neuronal_cognition=kwargs.get(
                    "include_retired_neuronal_cognition",
                    False,
                ),
                include_legacy_coupling_backlog=True,
            ),
        )
        save_structural_graph(organism, old_graph, limits=LIMITS)

    with sqlite3.connect(old_graph) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM edges "
            "WHERE field_name='_coupling_signal_accum'"
        ).fetchone()[0] == 1

    migrated = load_structural_graph(
        old_graph,
        expected_root_type=Embryo,
        limits=LIMITS,
    )
    migrated_neuron = _first_neuron(migrated)
    assert "_coupling_signal_accum" not in migrated_neuron.__dict__
    assert migrated_neuron._coupling_signal_pending is True
    assert _float_bits(migrated_neuron._coupling_signal_sum) == (
        _float_bits(expected)
    )

    cold_one = tmp_path / "cold-one.sgr"
    cold_two = tmp_path / "cold-two.sgr"
    save_structural_graph(migrated, cold_one, limits=LIMITS)
    with sqlite3.connect(cold_one) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM edges "
            "WHERE field_name='_coupling_signal_accum'"
        ).fetchone()[0] == 0
        scalar_kinds = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT n.kind FROM edges AS e "
                "JOIN nodes AS n ON n.node_id=e.value_id "
                "WHERE e.field_name IN "
                "('_coupling_signal_sum','_coupling_signal_pending')"
            )
        }
    assert scalar_kinds == {"float", "bool"}

    restored = load_structural_graph(
        cold_one,
        expected_root_type=Embryo,
        limits=LIMITS,
    )
    restored_neuron = _first_neuron(restored)
    assert _float_bits(restored_neuron._coupling_signal_sum) == (
        _float_bits(expected)
    )
    assert restored_neuron._coupling_signal_pending is True
    save_structural_graph(restored, cold_two, limits=LIMITS)
    assert cold_two.read_bytes() == cold_one.read_bytes()


def test_new_registry_contains_no_coupling_backlog() -> None:
    durable = structural_registry_contract()["loom_neuron"][
        "durable_fields"
    ]
    assert "_coupling_signal_accum" not in durable
    assert "_coupling_signal_sum" in durable
    assert "_coupling_signal_pending" in durable
