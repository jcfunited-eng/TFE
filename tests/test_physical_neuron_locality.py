from __future__ import annotations

from dataclasses import dataclass

import pytest

from dsf_ai_service.substrate.physical_neuron_locality import (
    nearest_neighbor_coupling_pairs,
)


@dataclass(frozen=True, slots=True)
class _Neuron:
    neuron_id: str
    sense: str
    sensor_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]


def _retinal(
    row: int,
    column: int,
    band: int,
    topology_index: int,
) -> _Neuron:
    return _Neuron(
        neuron_id=f"retina-{row}-{column}-{band}",
        sense="sight",
        sensor_id="W1-retina",
        topology_index=topology_index,
        coordinates=(
            ("retinal-row", str(row)),
            ("retinal-column", str(column)),
            ("optical-band", str(band)),
        ),
    )


def test_exact_lattice_neighbors_do_not_form_a_complete_graph() -> None:
    neurons = tuple(
        _retinal(row, column, band, index)
        for index, (row, column, band) in enumerate(
            (
                (0, 0, 0),
                (0, 0, 1),
                (0, 1, 0),
                (0, 1, 1),
                (1, 0, 0),
                (1, 0, 1),
                (1, 1, 0),
                (1, 1, 1),
            )
        )
    )

    pairs = nearest_neighbor_coupling_pairs(neurons)

    assert len(pairs) == 12
    assert (
        "retina-0-0-0",
        "retina-0-0-1",
    ) in pairs
    assert (
        "retina-0-0-0",
        "retina-0-1-0",
    ) in pairs
    assert (
        "retina-0-0-0",
        "retina-1-0-0",
    ) in pairs
    assert (
        "retina-0-0-0",
        "retina-1-1-1",
    ) not in pairs


def test_different_sensors_and_senses_never_gain_a_pair() -> None:
    neurons = (
        _Neuron(
            "left",
            "sound",
            "left-cochlea",
            0,
            (("cochlear-band", "0"),),
        ),
        _Neuron(
            "right",
            "sound",
            "right-cochlea",
            0,
            (("cochlear-band", "0"),),
        ),
        _Neuron(
            "sight",
            "sight",
            "left-cochlea",
            0,
            (("cochlear-band", "0"),),
        ),
    )

    assert nearest_neighbor_coupling_pairs(neurons) == ()


def test_declared_topology_order_not_lexical_order_controls_adjacency() -> None:
    neurons = (
        _Neuron(
            "first",
            "sound",
            "cochlea",
            0,
            (("band", "low"),),
        ),
        _Neuron(
            "second",
            "sound",
            "cochlea",
            1,
            (("band", "high"),),
        ),
        _Neuron(
            "third",
            "sound",
            "cochlea",
            2,
            (("band", "middle"),),
        ),
    )

    assert nearest_neighbor_coupling_pairs(neurons) == (
        ("first", "second"),
        ("second", "third"),
    )


def test_duplicate_physical_coordinate_fails_closed() -> None:
    neurons = (
        _Neuron(
            "first",
            "touch",
            "skin",
            0,
            (("surface", "palm"),),
        ),
        _Neuron(
            "second",
            "touch",
            "skin",
            1,
            (("surface", "palm"),),
        ),
    )

    with pytest.raises(ValueError, match="repeats one coordinate"):
        nearest_neighbor_coupling_pairs(neurons)
