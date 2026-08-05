"""One local Krimelack component transition, isolated for falsification.

The organism boundary has already authenticated and routed the event. Coupling
geometry and exact locality have already resolved a same-component physical
displacement. Distinct component locations never enter this transition together.

Three local steps complete one winding because the Krimelack relation has three
phase nodes. State retains only bounded sub-winding displacement. One available
channel and one local energy expenditure permit at most one winding per clock;
any further signed displacement is returned as a momentary shunted quantity for
later fluid/body accounting rather than silently dropped or stored as history.
"""

from dataclasses import dataclass


TRIADIC_STEPS_PER_WINDING = 3
MAX_REMAINDER_STEPS = TRIADIC_STEPS_PER_WINDING - 1


@dataclass(frozen=True, slots=True)
class ComponentState:
    """Physical state retained by one routed neuron component."""

    phase_steps: int = 0
    channel_ready: bool = True
    energy_available: bool = True


@dataclass(frozen=True, slots=True)
class LocalEvent:
    """Same-location contributions already resolved by organism topology."""

    phase_step: int = 0
    channel_recovery: bool = False
    energy_supply: bool = False


@dataclass(frozen=True, slots=True)
class Transition:
    """Successor state and momentary physical outflows."""

    state: ComponentState
    winding_transition: int = 0
    shunted_phase_steps: int = 0


def transition_component(
    state: ComponentState,
    event: LocalEvent | None,
) -> Transition:
    """Apply one exact-clock local displacement with no authority machinery."""

    if event is None:
        return Transition(state=state)

    channel_ready = state.channel_ready or event.channel_recovery
    energy_available = state.energy_available or event.energy_supply
    raw_phase = state.phase_steps + event.phase_step

    if -MAX_REMAINDER_STEPS <= raw_phase <= MAX_REMAINDER_STEPS:
        return Transition(
            state=ComponentState(
                phase_steps=raw_phase,
                channel_ready=channel_ready,
                energy_available=energy_available,
            )
        )

    crossing = 1 if raw_phase > MAX_REMAINDER_STEPS else -1
    if channel_ready and energy_available:
        winding_transition = crossing
        retained_phase = raw_phase - crossing * TRIADIC_STEPS_PER_WINDING
        channel_ready = False
        energy_available = False
    else:
        winding_transition = 0
        retained_phase = raw_phase

    bounded_phase = max(
        -MAX_REMAINDER_STEPS,
        min(MAX_REMAINDER_STEPS, retained_phase),
    )
    return Transition(
        state=ComponentState(
            phase_steps=bounded_phase,
            channel_ready=channel_ready,
            energy_available=energy_available,
        ),
        winding_transition=winding_transition,
        shunted_phase_steps=retained_phase - bounded_phase,
    )
