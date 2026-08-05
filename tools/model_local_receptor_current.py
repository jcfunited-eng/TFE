"""One exact local receptor current, isolated for falsification.

Receptor binding and channel kinetics have already produced an exact open
conductance at one named receiving membrane compartment.  The current follows
from that conductance and the compartment's present reversal relation.  This
law does not assign excitatory or inhibitory meaning and does not advance
membrane voltage or Krimelack phase without their missing physical parameters.
"""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, slots=True)
class ReceptorLocation:
    neuron: int
    membrane_compartment: int
    receptor_population: int


@dataclass(frozen=True, slots=True)
class ReceptorCurrentState:
    membrane_potential: Fraction
    reversal_potential: Fraction
    open_conductance: Fraction


@dataclass(frozen=True, slots=True)
class ReceptorCurrent:
    location: ReceptorLocation
    current: Fraction


def resolve_receptor_current(
    location: ReceptorLocation,
    state: ReceptorCurrentState,
) -> ReceptorCurrent:
    """Resolve exact outward-positive current at one reached receptor."""

    return ReceptorCurrent(
        location=location,
        current=state.open_conductance
        * (state.membrane_potential - state.reversal_potential),
    )
