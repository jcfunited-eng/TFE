"""One locally supplied synaptic terminal, isolated for falsification.

Organism topology has already routed a source winding to this named terminal.
The terminal may spend one locally available transmitter quantum to produce one
arrival at its exact target component.  The arrival retains causal direction,
but does not invent the receiving component's phase displacement.  Receptor,
compartment, ion, and fluid physics must determine that later local effect.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SynapseLocation:
    source_component: int
    target_component: int
    terminal: int


@dataclass(frozen=True, slots=True)
class SynapseState:
    transmitter_available: bool = True


@dataclass(frozen=True, slots=True)
class LocalSynapseEvent:
    source_winding: int = 0
    transmitter_recovery: bool = False


@dataclass(frozen=True, slots=True)
class SynapticArrival:
    location: SynapseLocation
    source_winding: int


@dataclass(frozen=True, slots=True)
class SynapseTransition:
    state: SynapseState
    arrival: SynapticArrival | None = None
    depleted_attempt: bool = False


def transition_synapse(
    location: SynapseLocation,
    state: SynapseState,
    event: LocalSynapseEvent | None,
) -> SynapseTransition:
    """Spend at most one transmitter quantum at one reached terminal."""

    if event is None:
        return SynapseTransition(state=state)

    transmitter_available = (
        state.transmitter_available or event.transmitter_recovery
    )
    if not event.source_winding:
        return SynapseTransition(
            state=SynapseState(transmitter_available=transmitter_available)
        )

    if not transmitter_available:
        return SynapseTransition(state=state, depleted_attempt=True)

    return SynapseTransition(
        state=SynapseState(transmitter_available=False),
        arrival=SynapticArrival(
            location=location,
            source_winding=event.source_winding,
        ),
    )
