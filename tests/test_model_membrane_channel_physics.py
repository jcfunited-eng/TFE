from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter
from fractions import Fraction

from tools import model_membrane_channel_physics as physics


ANATOMY = physics.MembraneAnatomy(
    surface_area=Fraction(3),
    specific_capacitance=Fraction(1, 2),
)


def test_ensemble_open_population_is_exact_and_never_rounded() -> None:
    state = physics.ChannelEnsembleState(
        state_occupancies=(Fraction(2, 3), Fraction(1, 3)),
        open_state_indices=(1,),
    )
    channel = physics.OhmicChannelPopulation(
        population_count=10,
        unit_conductance=Fraction(3, 5),
        reversal_potential=Fraction(1, 4),
    )

    assert state.open_occupancy == Fraction(1, 3)
    assert channel.open_population(state) == Fraction(10, 3)
    assert channel.outward_current_at(state, Fraction(-3, 4)) == -2


def test_membrane_charge_balance_does_not_wrap_voltage() -> None:
    state = physics.MembraneState(potential=Fraction(0))
    event = physics.CurrentInterval(
        outward_current=Fraction(-3, 2),
        duration=Fraction(1),
    )

    for expected in (Fraction(1), Fraction(2), Fraction(3)):
        result = physics.transition_membrane_charge_balance(
            ANATOMY, state, event
        )
        assert (
            result.successor_charge
            == result.predecessor_charge + result.charge_delta
        )
        assert result.state.potential == expected
        state = result.state

    assert not hasattr(result, "winding_transition")
    assert not hasattr(result, "phase_node")


def test_channel_current_is_zero_at_reversal_and_changes_direction() -> None:
    state = physics.ChannelEnsembleState(
        state_occupancies=(Fraction(0), Fraction(1)),
        open_state_indices=(1,),
    )
    channel = physics.OhmicChannelPopulation(
        population_count=3,
        unit_conductance=Fraction(2, 5),
        reversal_potential=Fraction(-1, 2),
    )

    assert channel.outward_current_at(state, Fraction(-1, 2)) == 0
    assert channel.outward_current_at(state, Fraction(0)) > 0
    assert channel.outward_current_at(state, Fraction(-1)) < 0


def test_no_current_is_exact_quiescence() -> None:
    prior = physics.MembraneState(potential=Fraction(-7, 11))
    result = physics.transition_membrane_charge_balance(
        ANATOMY, prior, None
    )

    assert result.state == prior
    assert result.charge_delta == 0


def profile_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)
    state = physics.MembraneState(potential=Fraction(0))
    event = physics.CurrentInterval(Fraction(-1, 17), Fraction(1))

    def profiler(frame, event_name, _arg):
        if event_name == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            state = physics.transition_membrane_charge_balance(
                ANATOMY, state, event
            ).state
    finally:
        sys.setprofile(None)
    return calls


def test_work_is_one_nonrecursive_transition_per_reached_membrane() -> None:
    one_thousand = profile_calls(1_000)
    ten_thousand = profile_calls(10_000)
    assert one_thousand == Counter(
        {"transition_membrane_charge_balance": 1_000}
    )
    assert ten_thousand == Counter(
        {"transition_membrane_charge_balance": 10_000}
    )


def test_physics_has_no_owner_database_lock_or_authority_machinery() -> None:
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
    assert imports == {"dataclass", "Fraction"}
    assert identifiers.isdisjoint(
        {
            "authority",
            "database",
            "hashlib",
            "history",
            "json",
            "lock",
            "owner",
            "receipt",
            "score",
            "verify",
        }
    )
