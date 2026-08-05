from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter

from tools import model_local_synapse_physics as physics


def test_release_reaches_only_the_exact_mounted_target():
    location = physics.SynapseLocation(
        source_component=3,
        target_component=11,
        terminal=2,
    )

    result = physics.transition_synapse(
        location,
        physics.SynapseState(),
        physics.LocalSynapseEvent(source_winding=1),
    )

    assert result.arrival == physics.SynapticArrival(
        location=location,
        source_winding=1,
    )
    assert not result.state.transmitter_available


def test_transport_preserves_causal_direction_without_inventing_target_effect():
    location = physics.SynapseLocation(
        source_component=3,
        target_component=11,
        terminal=2,
    )

    positive = physics.transition_synapse(
        location,
        physics.SynapseState(),
        physics.LocalSynapseEvent(source_winding=1),
    )
    negative = physics.transition_synapse(
        location,
        physics.SynapseState(),
        physics.LocalSynapseEvent(source_winding=-1),
    )

    assert positive.arrival.source_winding == 1
    assert negative.arrival.source_winding == -1
    assert not hasattr(positive, "target_phase_step")


def test_constant_source_event_releases_once_without_terminal_recovery():
    location = physics.SynapseLocation(
        source_component=0,
        target_component=1,
        terminal=0,
    )
    state = physics.SynapseState()
    source_event = physics.LocalSynapseEvent(source_winding=1)
    releases = 0
    depleted_attempts = 0

    for _ in range(100_000):
        result = physics.transition_synapse(location, state, source_event)
        state = result.state
        releases += result.arrival is not None
        depleted_attempts += result.depleted_attempt

    assert releases == 1
    assert depleted_attempts == 99_999
    assert state == physics.SynapseState(transmitter_available=False)
    assert not hasattr(state, "release_count")
    assert not hasattr(state, "event_history")


def test_local_fluid_recovery_enables_exactly_one_later_release():
    location = physics.SynapseLocation(
        source_component=0,
        target_component=1,
        terminal=0,
    )
    depleted = physics.SynapseState(transmitter_available=False)

    recovered = physics.transition_synapse(
        location,
        depleted,
        physics.LocalSynapseEvent(transmitter_recovery=True),
    ).state
    released = physics.transition_synapse(
        location,
        recovered,
        physics.LocalSynapseEvent(source_winding=1),
    )
    blocked = physics.transition_synapse(
        location,
        released.state,
        physics.LocalSynapseEvent(source_winding=1),
    )

    assert recovered.transmitter_available
    assert released.arrival is not None
    assert not released.state.transmitter_available
    assert blocked.depleted_attempt


def test_coincident_recovery_is_consumed_by_the_release_it_enables():
    result = physics.transition_synapse(
        physics.SynapseLocation(
            source_component=2,
            target_component=0,
            terminal=1,
        ),
        physics.SynapseState(transmitter_available=False),
        physics.LocalSynapseEvent(source_winding=1, transmitter_recovery=True),
    )

    assert result.arrival is not None
    assert not result.state.transmitter_available


def profile_module_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)

    def profiler(frame, event, _arg):
        if event == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    location = physics.SynapseLocation(
        source_component=0,
        target_component=1,
        terminal=0,
    )
    state = physics.SynapseState()
    source_event = physics.LocalSynapseEvent(source_winding=1)
    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            state = physics.transition_synapse(location, state, source_event).state
    finally:
        sys.setprofile(None)
    return calls


def test_synapse_work_is_one_non_recursive_physics_call_per_reached_terminal():
    one_thousand = profile_module_calls(1_000)
    ten_thousand = profile_module_calls(10_000)

    assert one_thousand == Counter({"transition_synapse": 1_000})
    assert ten_thousand == Counter({"transition_synapse": 10_000})


def test_synapse_module_imports_no_custody_or_infrastructure_dependency():
    tree = ast.parse(inspect.getsource(physics))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    identifiers = {
        node.id.lower()
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    }

    assert imports == {"dataclass"}
    assert identifiers.isdisjoint(
        {"hashlib", "json", "receipt", "authority", "database", "owner", "lock", "verify"}
    )
