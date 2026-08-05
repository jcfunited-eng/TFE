from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter

from tools import model_biophysical_krimelack_physics as physics


def apply(state: physics.ComponentState, *events: physics.LocalEvent | None):
    results = []
    for event in events:
        result = physics.transition_component(state, event)
        results.append(result)
        state = result.state
    return state, results


def test_three_positive_local_steps_emit_one_winding_and_consume_resources():
    state, results = apply(
        physics.ComponentState(),
        physics.LocalEvent(phase_step=1),
        physics.LocalEvent(phase_step=1),
        physics.LocalEvent(phase_step=1),
    )

    assert [result.winding_transition for result in results] == [0, 0, 1]
    assert state == physics.ComponentState(
        phase_steps=0,
        channel_ready=False,
        energy_available=False,
    )
    assert sum(result.shunted_phase_steps for result in results) == 0


def test_opposite_local_orientation_is_exactly_symmetric():
    state, results = apply(
        physics.ComponentState(),
        physics.LocalEvent(phase_step=-1),
        physics.LocalEvent(phase_step=-1),
        physics.LocalEvent(phase_step=-1),
    )

    assert [result.winding_transition for result in results] == [0, 0, -1]
    assert state == physics.ComponentState(
        phase_steps=0,
        channel_ready=False,
        energy_available=False,
    )
    assert sum(result.shunted_phase_steps for result in results) == 0


def test_constant_drive_cannot_self_fire_after_resource_expenditure():
    state = physics.ComponentState()
    event = physics.LocalEvent(phase_step=1)
    windings = 0
    shunted = 0

    for _ in range(100_000):
        result = physics.transition_component(state, event)
        state = result.state
        windings += abs(result.winding_transition)
        shunted += abs(result.shunted_phase_steps)

    assert windings == 1
    assert shunted == 99_995
    assert state == physics.ComponentState(
        phase_steps=2,
        channel_ready=False,
        energy_available=False,
    )
    assert not hasattr(state, "winding_count")
    assert not hasattr(state, "event_history")


def test_local_fluid_contributions_recover_channel_and_energy_independently():
    depleted = physics.transition_component(
        physics.ComponentState(),
        physics.LocalEvent(phase_step=3),
    ).state

    energy_only = physics.transition_component(
        depleted,
        physics.LocalEvent(energy_supply=True),
    ).state
    assert energy_only.energy_available
    assert not energy_only.channel_ready

    held = physics.transition_component(
        energy_only,
        physics.LocalEvent(phase_step=3),
    )
    assert held.winding_transition == 0
    assert held.state.phase_steps == 2
    assert held.shunted_phase_steps == 1

    ready = physics.transition_component(
        held.state,
        physics.LocalEvent(channel_recovery=True),
    ).state
    fired = physics.transition_component(ready, physics.LocalEvent(phase_step=1))
    assert fired.winding_transition == 1
    assert fired.state == physics.ComponentState(
        phase_steps=0,
        channel_ready=False,
        energy_available=False,
    )


def test_coincident_local_recovery_is_consumed_by_the_crossing_it_enables():
    state = physics.ComponentState(
        phase_steps=2,
        channel_ready=False,
        energy_available=False,
    )

    result = physics.transition_component(
        state,
        physics.LocalEvent(
            phase_step=1,
            channel_recovery=True,
            energy_supply=True,
        ),
    )

    assert result.winding_transition == 1
    assert result.state == physics.ComponentState(
        phase_steps=0,
        channel_ready=False,
        energy_available=False,
    )


def test_recovery_saturates_without_accumulation():
    state = physics.ComponentState(
        phase_steps=-2,
        channel_ready=False,
        energy_available=False,
    )
    event = physics.LocalEvent(channel_recovery=True, energy_supply=True)

    once = physics.transition_component(state, event).state
    repeatedly, _ = apply(once, *([event] * 10_000))

    assert once == repeatedly == physics.ComponentState(phase_steps=-2)


def test_quiescence_and_zero_local_displacement_are_bounded():
    state = physics.ComponentState(phase_steps=1)

    quiescent = physics.transition_component(state, None)
    local_zero = physics.transition_component(state, physics.LocalEvent())

    assert quiescent.state is state
    assert local_zero.state == state
    assert quiescent.winding_transition == local_zero.winding_transition == 0
    assert quiescent.shunted_phase_steps == local_zero.shunted_phase_steps == 0


def test_arbitrary_same_location_fanin_is_bounded_and_exactly_conserved():
    for phase_steps in range(-2, 3):
        for channel_ready in (False, True):
            for energy_available in (False, True):
                for local_displacement in range(-50, 51):
                    prior = physics.ComponentState(
                        phase_steps=phase_steps,
                        channel_ready=channel_ready,
                        energy_available=energy_available,
                    )
                    result = physics.transition_component(
                        prior,
                        physics.LocalEvent(phase_step=local_displacement),
                    )

                    assert -2 <= result.state.phase_steps <= 2
                    assert (
                        result.state.phase_steps
                        + 3 * result.winding_transition
                        + result.shunted_phase_steps
                        == phase_steps + local_displacement
                    )
                    assert abs(result.winding_transition) <= 1


def profile_module_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)

    def profiler(frame, event, _arg):
        if event == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    state = physics.ComponentState()
    local_event = physics.LocalEvent(phase_step=1)
    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            state = physics.transition_component(state, local_event).state
    finally:
        sys.setprofile(None)
    return calls


def test_physics_call_work_is_constant_per_transition_not_recursive():
    one_thousand = profile_module_calls(1_000)
    two_thousand = profile_module_calls(2_000)

    assert one_thousand["transition_component"] == 1_000
    assert two_thousand["transition_component"] == 2_000
    assert two_thousand == Counter(
        {name: count * 2 for name, count in one_thousand.items()}
    )
    assert "verify" not in one_thousand


def test_physics_module_imports_no_custody_or_infrastructure_dependency():
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
