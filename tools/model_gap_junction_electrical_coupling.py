"""Sparse exact gap-junction coupling with ensemble channel occupancy.

Each explicit gap junction derives conductance from population count, exact open
occupancy, and unit conductance.  Every edge moves equal and opposite charge
from one immutable predecessor; successors are constructed atomically.  This
module does not infer anatomy, execute receptor gating, or claim cognition.
"""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class Membrane:
    lineage: int
    surface_area: Fraction
    specific_capacitance: Fraction
    potential: Fraction

    @property
    def capacitance(self) -> Fraction:
        return self.surface_area * self.specific_capacitance


@dataclass(frozen=True, slots=True)
class GapJunction:
    left_lineage: int
    right_lineage: int
    population_count: int
    open_occupancy: Fraction
    unit_conductance: Fraction

    @property
    def conductance(self) -> Fraction:
        return (
            self.population_count
            * self.open_occupancy
            * self.unit_conductance
        )


@dataclass(frozen=True, slots=True)
class EdgeTransfer:
    left_lineage: int
    right_lineage: int
    left_outward_current: Fraction
    left_charge_delta: Fraction
    right_charge_delta: Fraction


@dataclass(frozen=True, slots=True)
class CoupledTransition:
    membranes: tuple[Membrane, ...]
    transfers: tuple[EdgeTransfer, ...]


def maximum_admitted_interval(
    membranes: tuple[Membrane, ...],
    junctions: tuple[GapJunction, ...],
) -> Fraction | None:
    incident = {membrane.lineage: Fraction(0) for membrane in membranes}
    for junction in junctions:
        incident[junction.left_lineage] += junction.conductance
        incident[junction.right_lineage] += junction.conductance
    bounds = tuple(
        membrane.capacitance / incident[membrane.lineage]
        for membrane in membranes
        if incident[membrane.lineage] != 0
    )
    return min(bounds) if bounds else None


def transition_gap_junctions(
    membranes: tuple[Membrane, ...],
    junctions: tuple[GapJunction, ...],
    duration: Fraction,
) -> CoupledTransition:
    prior = {membrane.lineage: membrane for membrane in membranes}
    charge_delta = {
        membrane.lineage: Fraction(0) for membrane in membranes
    }
    transfers = []
    for junction in junctions:
        left = prior[junction.left_lineage]
        right = prior[junction.right_lineage]
        current = junction.conductance * (
            left.potential - right.potential
        )
        left_delta = -current * duration
        right_delta = current * duration
        charge_delta[left.lineage] += left_delta
        charge_delta[right.lineage] += right_delta
        transfers.append(
            EdgeTransfer(
                left_lineage=left.lineage,
                right_lineage=right.lineage,
                left_outward_current=current,
                left_charge_delta=left_delta,
                right_charge_delta=right_delta,
            )
        )
    return CoupledTransition(
        membranes=tuple(
            Membrane(
                lineage=membrane.lineage,
                surface_area=membrane.surface_area,
                specific_capacitance=membrane.specific_capacitance,
                potential=(
                    membrane.potential
                    + charge_delta[membrane.lineage]
                    / membrane.capacitance
                ),
            )
            for membrane in membranes
        ),
        transfers=tuple(transfers),
    )
