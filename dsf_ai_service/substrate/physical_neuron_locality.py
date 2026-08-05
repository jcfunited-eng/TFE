"""Exact nearest-neighbor locality for physical receptor neurons.

ArcLoom's coupling fabric is local: co-perturbation may strengthen an
anatomically available relation, but one causal settlement does not fabricate
an all-to-all graph.  This module derives the available relation directly from
the immutable native receptor topology already carried by each neuron.

Two receptor neurons are neighbors only when they:

* belong to the same physical sense and sensor;
* carry the same ordered coordinate axes;
* differ on exactly one axis; and
* occupy adjacent declared coordinate values on that axis.

Coordinate order is recovered from the sensor's authenticated topology order,
not from lexical sorting, numeric parsing, distance thresholds, or a tuned
neighbor count.  The result is deterministic, symmetric, sparse, and uses no
sensory magnitude or semantic label.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class PhysicalNeuronTopologyView(Protocol):
    """The immutable anatomical fields required for local coupling."""

    neuron_id: str
    sense: str
    sensor_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class PhysicalNeuronTopologyRecord:
    """One immutable topology-only neuron projection."""

    neuron_id: str
    sense: str
    sensor_id: str
    topology_index: int
    coordinates: tuple[tuple[str, str], ...]

    def verify(self) -> None:
        _verified_view(self)


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError(f"{label} changed")
    return value


def _verified_view(
    value: PhysicalNeuronTopologyView,
) -> tuple[
    str,
    str,
    str,
    int,
    tuple[tuple[str, str], ...],
]:
    if not isinstance(value, PhysicalNeuronTopologyView):
        raise TypeError("physical neuron topology view is not typed")
    neuron_id = _identifier(value.neuron_id, "physical neuron id")
    sense = _identifier(value.sense, "physical neuron sense")
    sensor_id = _identifier(value.sensor_id, "physical neuron sensor")
    topology_index = value.topology_index
    if (
        isinstance(topology_index, bool)
        or not isinstance(topology_index, int)
        or topology_index < 0
    ):
        raise ValueError("physical neuron topology index changed")
    coordinates = value.coordinates
    if (
        not isinstance(coordinates, tuple)
        or not coordinates
        or any(
            not isinstance(item, tuple)
            or len(item) != 2
            for item in coordinates
        )
    ):
        raise ValueError("physical neuron coordinates changed")
    verified_coordinates = tuple(
        (
            _identifier(axis, "physical neuron coordinate axis"),
            _identifier(coordinate, "physical neuron coordinate"),
        )
        for axis, coordinate in coordinates
    )
    axes = tuple(axis for axis, _coordinate in verified_coordinates)
    if len(set(axes)) != len(axes):
        raise ValueError("physical neuron coordinate axis repeated")
    return (
        neuron_id,
        sense,
        sensor_id,
        topology_index,
        verified_coordinates,
    )


def nearest_neighbor_coupling_pairs(
    neurons: tuple[PhysicalNeuronTopologyView, ...],
) -> tuple[tuple[str, str], ...]:
    """Return exact symmetric nearest-neighbor pairs in canonical order."""

    if not isinstance(neurons, tuple):
        raise TypeError("physical neuron collection must be immutable")
    verified = tuple(_verified_view(value) for value in neurons)
    ids = tuple(value[0] for value in verified)
    if len(set(ids)) != len(ids):
        raise ValueError("physical neuron collection repeats an identity")

    groups: dict[
        tuple[str, str, tuple[str, ...]],
        list[
            tuple[
                str,
                str,
                str,
                int,
                tuple[tuple[str, str], ...],
            ]
        ],
    ] = defaultdict(list)
    for value in verified:
        axes = tuple(axis for axis, _coordinate in value[4])
        groups[(value[1], value[2], axes)].append(value)

    result: set[tuple[str, str]] = set()
    for group_key in sorted(groups):
        ordered = tuple(
            sorted(
                groups[group_key],
                key=lambda value: (value[3], value[0]),
            )
        )
        coordinate_to_id: dict[tuple[str, ...], str] = {}
        axis_orders: list[list[str]] = [
            [] for _axis in group_key[2]
        ]
        for value in ordered:
            coordinate_vector = tuple(
                coordinate for _axis, coordinate in value[4]
            )
            if coordinate_vector in coordinate_to_id:
                raise ValueError(
                    "physical receptor topology repeats one coordinate"
                )
            coordinate_to_id[coordinate_vector] = value[0]
            for axis_index, coordinate in enumerate(coordinate_vector):
                if coordinate not in axis_orders[axis_index]:
                    axis_orders[axis_index].append(coordinate)

        axis_positions = tuple(
            {
                coordinate: index
                for index, coordinate in enumerate(order)
            }
            for order in axis_orders
        )
        for coordinate_vector, neuron_id in sorted(
            coordinate_to_id.items()
        ):
            for axis_index, position_by_coordinate in enumerate(
                axis_positions
            ):
                position = position_by_coordinate[
                    coordinate_vector[axis_index]
                ]
                for neighbor_position in (position - 1, position + 1):
                    if not 0 <= neighbor_position < len(
                        axis_orders[axis_index]
                    ):
                        continue
                    neighbor_vector = list(coordinate_vector)
                    neighbor_vector[axis_index] = (
                        axis_orders[axis_index][neighbor_position]
                    )
                    neighbor_id = coordinate_to_id.get(
                        tuple(neighbor_vector)
                    )
                    if neighbor_id is None or neighbor_id == neuron_id:
                        continue
                    result.add(tuple(sorted((neuron_id, neighbor_id))))
    return tuple(sorted(result))


__all__ = (
    "PhysicalNeuronTopologyRecord",
    "PhysicalNeuronTopologyView",
    "nearest_neighbor_coupling_pairs",
)
