"""One exact membrane charge transition, isolated for falsification.

The organism boundary has already resolved one local outward-positive current,
one physical interval, and one mounted membrane capacitance.  Charge changes by
minus current times interval; potential changes by charge divided by
capacitance.  No threshold, clamp, timer, phase map, or recovery is introduced.
"""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class MembraneLocation:
    neuron: int
    membrane_compartment: int


@dataclass(frozen=True, slots=True)
class MembraneState:
    potential: Fraction
    capacitance: Fraction


@dataclass(frozen=True, slots=True)
class CurrentInterval:
    location: MembraneLocation
    outward_current: Fraction
    duration: Fraction


@dataclass(frozen=True, slots=True)
class MembraneTransition:
    state: MembraneState
    location: MembraneLocation | None = None
    charge_delta: Fraction = Fraction(0)


def transition_membrane_charge(
    state: MembraneState,
    event: CurrentInterval | None,
) -> MembraneTransition:
    """Integrate one constant local current over one exact interval."""

    if event is None:
        return MembraneTransition(state=state)

    charge_delta = -event.outward_current * event.duration
    return MembraneTransition(
        state=MembraneState(
            potential=state.potential + charge_delta / state.capacitance,
            capacitance=state.capacitance,
        ),
        location=event.location,
        charge_delta=charge_delta,
    )
