"""Exact biological membrane and deterministic ensemble-channel model.

Membrane voltage follows ordinary capacitor charge balance and does not wrap.
Channel state is an exact population occupancy distribution; expected open
population is retained as a rational quantity and is never rounded to an
integer.  The model does not define receptor gating, ion recovery, Krimelack
transduction, DSF, memory, or production authority.
"""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class MembraneAnatomy:
    surface_area: Fraction
    specific_capacitance: Fraction

    @property
    def capacitance(self) -> Fraction:
        return self.surface_area * self.specific_capacitance


@dataclass(frozen=True, slots=True)
class MembraneState:
    potential: Fraction


@dataclass(frozen=True, slots=True)
class CurrentInterval:
    outward_current: Fraction
    duration: Fraction


@dataclass(frozen=True, slots=True)
class MembraneTransition:
    state: MembraneState
    charge_delta: Fraction
    predecessor_charge: Fraction
    successor_charge: Fraction


@dataclass(frozen=True, slots=True)
class ChannelEnsembleState:
    state_occupancies: tuple[Fraction, ...]
    open_state_indices: tuple[int, ...]

    @property
    def open_occupancy(self) -> Fraction:
        return sum(
            (self.state_occupancies[index] for index in self.open_state_indices),
            Fraction(0),
        )


@dataclass(frozen=True, slots=True)
class OhmicChannelPopulation:
    population_count: int
    unit_conductance: Fraction
    reversal_potential: Fraction

    def open_population(self, state: ChannelEnsembleState) -> Fraction:
        return self.population_count * state.open_occupancy

    def outward_current_at(
        self,
        state: ChannelEnsembleState,
        membrane_potential: Fraction,
    ) -> Fraction:
        return (
            self.open_population(state)
            * self.unit_conductance
            * (membrane_potential - self.reversal_potential)
        )


def transition_membrane_charge_balance(
    anatomy: MembraneAnatomy,
    state: MembraneState,
    event: CurrentInterval | None,
) -> MembraneTransition:
    """Advance one reached membrane without thresholding or voltage wrap."""

    capacitance = anatomy.surface_area * anatomy.specific_capacitance
    predecessor_charge = capacitance * state.potential
    charge_delta = (
        Fraction(0)
        if event is None
        else -event.outward_current * event.duration
    )
    successor_charge = predecessor_charge + charge_delta
    return MembraneTransition(
        state=MembraneState(potential=successor_charge / capacitance),
        charge_delta=charge_delta,
        predecessor_charge=predecessor_charge,
        successor_charge=successor_charge,
    )
