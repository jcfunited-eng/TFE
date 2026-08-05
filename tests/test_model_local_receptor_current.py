from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter
from fractions import Fraction

from tools import model_local_receptor_current as physics


LOCATION = physics.ReceptorLocation(
    neuron=7,
    membrane_compartment=3,
    receptor_population=2,
)


def test_current_is_exactly_zero_at_local_reversal():
    result = physics.resolve_receptor_current(
        LOCATION,
        physics.ReceptorCurrentState(
            membrane_potential=Fraction(-7, 10),
            reversal_potential=Fraction(-7, 10),
            open_conductance=Fraction(3, 5),
        ),
    )

    assert result.location == LOCATION
    assert result.current == 0


def test_same_receptor_conductance_changes_direction_with_receiving_state():
    below_reversal = physics.resolve_receptor_current(
        LOCATION,
        physics.ReceptorCurrentState(
            membrane_potential=Fraction(-4, 5),
            reversal_potential=Fraction(-7, 10),
            open_conductance=Fraction(3, 5),
        ),
    )
    above_reversal = physics.resolve_receptor_current(
        LOCATION,
        physics.ReceptorCurrentState(
            membrane_potential=Fraction(-3, 5),
            reversal_potential=Fraction(-7, 10),
            open_conductance=Fraction(3, 5),
        ),
    )

    assert below_reversal.current == Fraction(-3, 50)
    assert above_reversal.current == Fraction(3, 50)


def test_zero_open_conductance_is_exact_quiescence_at_any_potential():
    result = physics.resolve_receptor_current(
        LOCATION,
        physics.ReceptorCurrentState(
            membrane_potential=Fraction(91, 37),
            reversal_potential=Fraction(-13, 29),
            open_conductance=Fraction(0),
        ),
    )

    assert result.current == 0


def test_rational_current_has_no_float_rounding_or_stored_polarity():
    state = physics.ReceptorCurrentState(
        membrane_potential=Fraction(1, 3),
        reversal_potential=Fraction(-2, 7),
        open_conductance=Fraction(5, 11),
    )

    result = physics.resolve_receptor_current(LOCATION, state)

    assert result.current == Fraction(65, 231)
    assert not hasattr(state, "polarity")
    assert not hasattr(state, "excitatory")
    assert not hasattr(state, "inhibitory")


def profile_module_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)
    state = physics.ReceptorCurrentState(
        membrane_potential=Fraction(-3, 5),
        reversal_potential=Fraction(-7, 10),
        open_conductance=Fraction(3, 5),
    )

    def profiler(frame, event, _arg):
        if event == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            physics.resolve_receptor_current(LOCATION, state)
    finally:
        sys.setprofile(None)
    return calls


def test_work_is_one_non_recursive_call_per_reached_receptor():
    assert profile_module_calls(1_000) == Counter(
        {"resolve_receptor_current": 1_000}
    )
    assert profile_module_calls(10_000) == Counter(
        {"resolve_receptor_current": 10_000}
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
