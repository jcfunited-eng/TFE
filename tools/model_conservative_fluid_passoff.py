"""One sparse conservative fluid pass-off, isolated for falsification.

The organism boundary has already resolved one typed mounted lane and exact
nonnegative request.  This transition moves only what the source contains and
the destination can physically hold.  It creates no supply, meaning, schedule,
history, or whole-organism polling.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FlowLocation:
    species: int
    source_compartment: int
    target_compartment: int


@dataclass(frozen=True, slots=True)
class CompartmentState:
    quantity: int
    capacity: int


@dataclass(frozen=True, slots=True)
class PassOffEvent:
    location: FlowLocation
    requested_quantity: int


@dataclass(frozen=True, slots=True)
class PassOffTransition:
    source: CompartmentState
    target: CompartmentState
    location: FlowLocation | None = None
    moved_quantity: int = 0
    unmet_request: int = 0


def transition_pass_off(
    source: CompartmentState,
    target: CompartmentState,
    event: PassOffEvent | None,
) -> PassOffTransition:
    """Move one requested quantity without creation, loss, or overfilling."""

    if event is None:
        return PassOffTransition(source=source, target=target)

    destination_room = target.capacity - target.quantity
    moved = min(event.requested_quantity, source.quantity, destination_room)
    return PassOffTransition(
        source=CompartmentState(
            quantity=source.quantity - moved,
            capacity=source.capacity,
        ),
        target=CompartmentState(
            quantity=target.quantity + moved,
            capacity=target.capacity,
        ),
        location=event.location,
        moved_quantity=moved,
        unmet_request=event.requested_quantity - moved,
    )
