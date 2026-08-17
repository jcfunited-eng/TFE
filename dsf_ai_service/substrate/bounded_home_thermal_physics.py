"""Exact bounded heat exchange for Guala's virtual home and body.

This module is deliberately smaller than the authenticated embodiment world.
It receives already-admitted local thermal nodes and sparse physical edges,
advances every reached edge once from one common predecessor, and returns only
the successor physical state and exact energy transfers.  It owns no lock,
identity, digest, receipt, serializer, persistence, sensory meaning, comfort
score, controller, or action selection.

Energy is stored on an explicit one-microjoule lattice.  A conductance edge may
produce a rational fraction of one microjoule during an interval; its signed
numerator residue is retained modulo that edge's fixed denominator.  Residue
therefore stays bounded and energy is never rounded away or manufactured.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


MAX_THERMAL_NODES = 8
MAX_THERMAL_EDGES = 16
MAX_DURATION_MICROSECONDS = 5_000_000
MAX_ENERGY_MICROJOULES = (1 << 63) - 1
MAX_CAPACITY_MICROJOULES_PER_MILLIKELVIN = (1 << 48) - 1
MAX_CONDUCTANCE_MICROWATTS_PER_KELVIN = (1 << 40) - 1
MAX_POWER_MICROWATTS = (1 << 40) - 1
MAX_TEMPERATURE_MILLIKELVIN = 1_000_000


def _integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{name} is outside its exact integer bounds")
    return value


def _whole_toward_zero(numerator: int, denominator: int) -> tuple[int, int]:
    """Return a signed whole quantum and a same-sign bounded residue."""

    if denominator <= 0:
        raise ValueError("thermal exchange denominator must be positive")
    if numerator >= 0:
        whole, residue = divmod(numerator, denominator)
        return whole, residue
    whole, residue = divmod(-numerator, denominator)
    return -whole, -residue


@dataclass(frozen=True, slots=True)
class ThermalNodeState:
    """One finite thermal energy stock with an immutable heat capacity."""

    energy_microjoules: int
    capacity_microjoules_per_millikelvin: int

    def verify(self) -> None:
        _integer(
            self.energy_microjoules,
            "thermal-node energy",
            minimum=0,
            maximum=MAX_ENERGY_MICROJOULES,
        )
        _integer(
            self.capacity_microjoules_per_millikelvin,
            "thermal-node heat capacity",
            minimum=1,
            maximum=MAX_CAPACITY_MICROJOULES_PER_MILLIKELVIN,
        )
        if self.temperature_millikelvin > MAX_TEMPERATURE_MILLIKELVIN:
            raise ValueError("thermal-node temperature exceeds its physical bound")

    @property
    def temperature_millikelvin(self) -> Fraction:
        return Fraction(
            self.energy_microjoules,
            self.capacity_microjoules_per_millikelvin,
        )


@dataclass(frozen=True, slots=True)
class ConductiveThermalEdge:
    """One oriented sparse conductance; positive heat moves left to right."""

    left_node_index: int
    right_node_index: int
    conductance_microwatts_per_kelvin: int

    def verify(self, node_count: int) -> None:
        left = _integer(
            self.left_node_index,
            "thermal-edge left node",
            minimum=0,
            maximum=node_count - 1,
        )
        right = _integer(
            self.right_node_index,
            "thermal-edge right node",
            minimum=0,
            maximum=node_count - 1,
        )
        if left == right:
            raise ValueError("thermal conductance cannot join a node to itself")
        _integer(
            self.conductance_microwatts_per_kelvin,
            "thermal-edge conductance",
            # A fixed sparse anatomy may contain mutually exclusive contact
            # edges.  Zero means this exact edge is physically separated for
            # the interval; retaining it keeps residue identity stable when a
            # body changes rooms without fabricating a second topology.
            minimum=0,
            maximum=MAX_CONDUCTANCE_MICROWATTS_PER_KELVIN,
        )


@dataclass(frozen=True, slots=True)
class ThermalBathEdge:
    """One open physical boundary held at a declared external temperature."""

    node_index: int
    bath_temperature_millikelvin: int
    conductance_microwatts_per_kelvin: int

    def verify(self, node_count: int) -> None:
        _integer(
            self.node_index,
            "thermal-bath node",
            minimum=0,
            maximum=node_count - 1,
        )
        _integer(
            self.bath_temperature_millikelvin,
            "thermal-bath temperature",
            minimum=1,
            maximum=MAX_TEMPERATURE_MILLIKELVIN,
        )
        _integer(
            self.conductance_microwatts_per_kelvin,
            "thermal-bath conductance",
            minimum=1,
            maximum=MAX_CONDUCTANCE_MICROWATTS_PER_KELVIN,
        )


@dataclass(frozen=True, slots=True)
class ThermalPowerSource:
    """One constant physical power entering one node during the interval."""

    node_index: int
    power_microwatts: int

    def verify(self, node_count: int) -> None:
        _integer(
            self.node_index,
            "thermal-power node",
            minimum=0,
            maximum=node_count - 1,
        )
        _integer(
            self.power_microwatts,
            "thermal source power",
            minimum=1,
            maximum=MAX_POWER_MICROWATTS,
        )


@dataclass(frozen=True, slots=True)
class BoundedThermalState:
    """Current-only energy and fixed-width exchange residues."""

    nodes: tuple[ThermalNodeState, ...]
    conductive_residue_numerators: tuple[int, ...]
    bath_residue_numerators: tuple[int, ...]
    power_residue_numerators: tuple[int, ...]

    def verify(
        self,
        conductive_edges: tuple[ConductiveThermalEdge, ...],
        bath_edges: tuple[ThermalBathEdge, ...],
        power_sources: tuple[ThermalPowerSource, ...],
    ) -> None:
        if not 1 <= len(self.nodes) <= MAX_THERMAL_NODES:
            raise ValueError("thermal-node inventory exceeds its fixed bound")
        if len(conductive_edges) > MAX_THERMAL_EDGES:
            raise ValueError("conductive-edge inventory exceeds its fixed bound")
        if len(bath_edges) > MAX_THERMAL_EDGES:
            raise ValueError("thermal-bath inventory exceeds its fixed bound")
        if len(power_sources) > MAX_THERMAL_EDGES:
            raise ValueError("thermal-power inventory exceeds its fixed bound")
        if len(self.conductive_residue_numerators) != len(conductive_edges):
            raise ValueError("conductive residues differ from sparse edge anatomy")
        if len(self.bath_residue_numerators) != len(bath_edges):
            raise ValueError("bath residues differ from boundary anatomy")
        if len(self.power_residue_numerators) != len(power_sources):
            raise ValueError("power residues differ from source anatomy")
        for node in self.nodes:
            node.verify()
        conductive_pairs: set[tuple[int, int]] = set()
        for edge, residue in zip(
            conductive_edges,
            self.conductive_residue_numerators,
            strict=True,
        ):
            edge.verify(len(self.nodes))
            pair = tuple(sorted((edge.left_node_index, edge.right_node_index)))
            if pair in conductive_pairs:
                raise ValueError("thermal conductance repeats one physical edge")
            conductive_pairs.add(pair)
            denominator = (
                1_000_000
                * 1_000
                * self.nodes[edge.left_node_index].capacity_microjoules_per_millikelvin
                * self.nodes[edge.right_node_index].capacity_microjoules_per_millikelvin
            )
            if (
                isinstance(residue, bool)
                or not isinstance(residue, int)
                or abs(residue) >= denominator
            ):
                raise ValueError("conductive residue escaped its fixed denominator")
        bath_nodes: set[int] = set()
        for edge, residue in zip(
            bath_edges,
            self.bath_residue_numerators,
            strict=True,
        ):
            edge.verify(len(self.nodes))
            if edge.node_index in bath_nodes:
                raise ValueError("thermal bath repeats one physical boundary")
            bath_nodes.add(edge.node_index)
            denominator = (
                1_000_000
                * 1_000
                * self.nodes[edge.node_index].capacity_microjoules_per_millikelvin
            )
            if (
                isinstance(residue, bool)
                or not isinstance(residue, int)
                or abs(residue) >= denominator
            ):
                raise ValueError("bath residue escaped its fixed denominator")
        powered_nodes: set[int] = set()
        for source, residue in zip(
            power_sources,
            self.power_residue_numerators,
            strict=True,
        ):
            source.verify(len(self.nodes))
            if source.node_index in powered_nodes:
                raise ValueError("thermal power repeats one physical source node")
            powered_nodes.add(source.node_index)
            if (
                isinstance(residue, bool)
                or not isinstance(residue, int)
                or abs(residue) >= 1_000_000
            ):
                raise ValueError("power residue escaped its fixed denominator")


@dataclass(frozen=True, slots=True)
class ThermalTransition:
    """Pure physical result; values are signed microjoules per declared edge."""

    successor: BoundedThermalState
    conductive_transfers_microjoules: tuple[int, ...]
    bath_transfers_into_nodes_microjoules: tuple[int, ...]
    powered_into_nodes_microjoules: tuple[int, ...]

    @property
    def external_energy_into_nodes_microjoules(self) -> int:
        return sum(self.bath_transfers_into_nodes_microjoules) + sum(
            self.powered_into_nodes_microjoules
        )


def _conductive_transfer(
    left: ThermalNodeState,
    right: ThermalNodeState,
    conductance_microwatts_per_kelvin: int,
    duration_microseconds: int,
    residue_numerator: int,
) -> tuple[int, int]:
    # Temperature difference is retained as
    #   E_left/C_left - E_right/C_right [mK].
    # microwatt * microsecond / 1_000_000 = microjoule, and
    # millikelvin / 1_000 = kelvin.
    numerator = (
        conductance_microwatts_per_kelvin
        * duration_microseconds
        * (
            left.energy_microjoules
            * right.capacity_microjoules_per_millikelvin
            - right.energy_microjoules
            * left.capacity_microjoules_per_millikelvin
        )
        + residue_numerator
    )
    denominator = (
        1_000_000
        * 1_000
        * left.capacity_microjoules_per_millikelvin
        * right.capacity_microjoules_per_millikelvin
    )
    return _whole_toward_zero(numerator, denominator)


def _bath_transfer(
    node: ThermalNodeState,
    edge: ThermalBathEdge,
    duration_microseconds: int,
    residue_numerator: int,
) -> tuple[int, int]:
    # Positive transfer enters the node from the external thermal boundary.
    numerator = (
        edge.conductance_microwatts_per_kelvin
        * duration_microseconds
        * (
            edge.bath_temperature_millikelvin
            * node.capacity_microjoules_per_millikelvin
            - node.energy_microjoules
        )
        + residue_numerator
    )
    denominator = (
        1_000_000
        * 1_000
        * node.capacity_microjoules_per_millikelvin
    )
    return _whole_toward_zero(numerator, denominator)


def _power_transfer(
    source: ThermalPowerSource,
    duration_microseconds: int,
    residue_numerator: int,
) -> tuple[int, int]:
    return _whole_toward_zero(
        source.power_microwatts * duration_microseconds + residue_numerator,
        1_000_000,
    )


def advance_bounded_thermal_state(
    predecessor: BoundedThermalState,
    *,
    conductive_edges: tuple[ConductiveThermalEdge, ...],
    bath_edges: tuple[ThermalBathEdge, ...],
    power_sources: tuple[ThermalPowerSource, ...],
    duration_microseconds: int,
) -> ThermalTransition:
    """Advance each reached sparse thermal path once from one predecessor."""

    predecessor.verify(conductive_edges, bath_edges, power_sources)
    duration = _integer(
        duration_microseconds,
        "thermal causal interval",
        minimum=1,
        maximum=MAX_DURATION_MICROSECONDS,
    )
    deltas = [0] * len(predecessor.nodes)
    conductive_transfers: list[int] = []
    conductive_residues: list[int] = []
    for edge, residue in zip(
        conductive_edges,
        predecessor.conductive_residue_numerators,
        strict=True,
    ):
        transfer, next_residue = _conductive_transfer(
            predecessor.nodes[edge.left_node_index],
            predecessor.nodes[edge.right_node_index],
            edge.conductance_microwatts_per_kelvin,
            duration,
            residue,
        )
        deltas[edge.left_node_index] -= transfer
        deltas[edge.right_node_index] += transfer
        conductive_transfers.append(transfer)
        conductive_residues.append(next_residue)

    bath_transfers: list[int] = []
    bath_residues: list[int] = []
    for edge, residue in zip(
        bath_edges,
        predecessor.bath_residue_numerators,
        strict=True,
    ):
        transfer, next_residue = _bath_transfer(
            predecessor.nodes[edge.node_index],
            edge,
            duration,
            residue,
        )
        deltas[edge.node_index] += transfer
        bath_transfers.append(transfer)
        bath_residues.append(next_residue)

    powered: list[int] = []
    power_residues: list[int] = []
    for source, residue in zip(
        power_sources,
        predecessor.power_residue_numerators,
        strict=True,
    ):
        transfer, next_residue = _power_transfer(source, duration, residue)
        deltas[source.node_index] += transfer
        powered.append(transfer)
        power_residues.append(next_residue)

    successor_nodes = tuple(
        ThermalNodeState(
            energy_microjoules=node.energy_microjoules + deltas[index],
            capacity_microjoules_per_millikelvin=(
                node.capacity_microjoules_per_millikelvin
            ),
        )
        for index, node in enumerate(predecessor.nodes)
    )
    successor = BoundedThermalState(
        nodes=successor_nodes,
        conductive_residue_numerators=tuple(conductive_residues),
        bath_residue_numerators=tuple(bath_residues),
        power_residue_numerators=tuple(power_residues),
    )
    successor.verify(conductive_edges, bath_edges, power_sources)
    if sum(node.energy_microjoules for node in successor.nodes) != (
        sum(node.energy_microjoules for node in predecessor.nodes)
        + sum(bath_transfers)
        + sum(powered)
    ):
        raise RuntimeError("thermal successor does not conserve admitted energy")
    return ThermalTransition(
        successor=successor,
        conductive_transfers_microjoules=tuple(conductive_transfers),
        bath_transfers_into_nodes_microjoules=tuple(bath_transfers),
        powered_into_nodes_microjoules=tuple(powered),
    )


__all__ = [
    "BoundedThermalState",
    "ConductiveThermalEdge",
    "ThermalBathEdge",
    "ThermalNodeState",
    "ThermalPowerSource",
    "ThermalTransition",
    "advance_bounded_thermal_state",
]
