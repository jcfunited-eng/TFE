from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter
from fractions import Fraction

from tools import model_exact_membrane_charge as physics


LOCATION = physics.MembraneLocation(neuron=7, membrane_compartment=3)


def test_outward_current_removes_charge_and_lowers_potential():
    prior = physics.MembraneState(
        potential=Fraction(-7, 10),
        capacitance=Fraction(2, 5),
    )

    result = physics.transition_membrane_charge(
        prior,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(3, 10),
            duration=Fraction(1, 5),
        ),
    )

    assert result.location == LOCATION
    assert result.charge_delta == Fraction(-3, 50)
    assert result.state.potential == Fraction(-17, 20)
    assert result.state.capacitance == prior.capacitance


def test_inward_current_adds_charge_and_raises_potential():
    result = physics.transition_membrane_charge(
        physics.MembraneState(
            potential=Fraction(-7, 10),
            capacitance=Fraction(2, 5),
        ),
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(-3, 10),
            duration=Fraction(1, 5),
        ),
    )

    assert result.charge_delta == Fraction(3, 50)
    assert result.state.potential == Fraction(-11, 20)


def test_charge_and_voltage_change_obey_capacitance_identity_exactly():
    prior = physics.MembraneState(
        potential=Fraction(13, 17),
        capacitance=Fraction(19, 23),
    )
    result = physics.transition_membrane_charge(
        prior,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(29, 31),
            duration=Fraction(37, 41),
        ),
    )

    assert (
        prior.capacitance * (result.state.potential - prior.potential)
        == result.charge_delta
    )


def test_two_adjacent_constant_current_intervals_equal_one_combined_interval():
    prior = physics.MembraneState(
        potential=Fraction(-2, 3),
        capacitance=Fraction(5, 7),
    )
    first = physics.transition_membrane_charge(
        prior,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(11, 13),
            duration=Fraction(1, 17),
        ),
    )
    second = physics.transition_membrane_charge(
        first.state,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(11, 13),
            duration=Fraction(2, 17),
        ),
    )
    combined = physics.transition_membrane_charge(
        prior,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(11, 13),
            duration=Fraction(3, 17),
        ),
    )

    assert second.state == combined.state
    assert first.charge_delta + second.charge_delta == combined.charge_delta


def test_zero_current_or_zero_duration_is_exact_quiescence():
    prior = physics.MembraneState(
        potential=Fraction(-7, 10),
        capacitance=Fraction(2, 5),
    )
    zero_current = physics.transition_membrane_charge(
        prior,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(0),
            duration=Fraction(19, 7),
        ),
    )
    zero_duration = physics.transition_membrane_charge(
        prior,
        physics.CurrentInterval(
            location=LOCATION,
            outward_current=Fraction(19, 7),
            duration=Fraction(0),
        ),
    )

    assert zero_current.state == prior
    assert zero_current.charge_delta == 0
    assert zero_duration.state == prior
    assert zero_duration.charge_delta == 0


def test_no_event_preserves_object_and_creates_no_history():
    prior = physics.MembraneState(
        potential=Fraction(-7, 10),
        capacitance=Fraction(2, 5),
    )

    result = physics.transition_membrane_charge(prior, None)

    assert result.state is prior
    assert result.location is None
    assert result.charge_delta == 0
    assert not hasattr(result, "history")


def profile_module_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)
    state = physics.MembraneState(
        potential=Fraction(-7, 10),
        capacitance=Fraction(2, 5),
    )
    event = physics.CurrentInterval(
        location=LOCATION,
        outward_current=Fraction(0),
        duration=Fraction(1, 5),
    )

    def profiler(frame, call_event, _arg):
        if call_event == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            state = physics.transition_membrane_charge(state, event).state
    finally:
        sys.setprofile(None)
    return calls


def test_work_is_one_non_recursive_call_per_reached_compartment():
    assert profile_module_calls(1_000) == Counter(
        {"transition_membrane_charge": 1_000}
    )
    assert profile_module_calls(10_000) == Counter(
        {"transition_membrane_charge": 10_000}
    )


def test_module_imports_only_exact_local_math_dependencies():
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
        {"hashlib", "json", "receipt", "authority", "database", "owner", "lock", "verify"}
    )
