from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter

from tools import model_conservative_fluid_passoff as physics


LOCATION = physics.FlowLocation(
    species=4,
    source_compartment=2,
    target_compartment=9,
)


def test_one_pass_off_conserves_internal_quantity_exactly_at_named_location():
    source = physics.CompartmentState(quantity=7, capacity=10)
    target = physics.CompartmentState(quantity=1, capacity=5)

    result = physics.transition_pass_off(
        source,
        target,
        physics.PassOffEvent(location=LOCATION, requested_quantity=3),
    )

    assert result.location == LOCATION
    assert result.source.quantity == 4
    assert result.target.quantity == 4
    assert result.moved_quantity == 3
    assert result.unmet_request == 0
    assert source.quantity + target.quantity == result.source.quantity + result.target.quantity


def test_source_availability_physically_limits_pass_off():
    result = physics.transition_pass_off(
        physics.CompartmentState(quantity=2, capacity=10),
        physics.CompartmentState(quantity=0, capacity=10),
        physics.PassOffEvent(location=LOCATION, requested_quantity=5),
    )

    assert result.source.quantity == 0
    assert result.target.quantity == 2
    assert result.moved_quantity == 2
    assert result.unmet_request == 3


def test_destination_capacity_physically_limits_pass_off():
    result = physics.transition_pass_off(
        physics.CompartmentState(quantity=8, capacity=10),
        physics.CompartmentState(quantity=4, capacity=5),
        physics.PassOffEvent(location=LOCATION, requested_quantity=6),
    )

    assert result.source.quantity == 7
    assert result.target.quantity == 5
    assert result.moved_quantity == 1
    assert result.unmet_request == 5


def test_empty_source_and_full_target_are_exact_quiescence():
    empty = physics.transition_pass_off(
        physics.CompartmentState(quantity=0, capacity=8),
        physics.CompartmentState(quantity=2, capacity=8),
        physics.PassOffEvent(location=LOCATION, requested_quantity=1),
    )
    full = physics.transition_pass_off(
        physics.CompartmentState(quantity=8, capacity=8),
        physics.CompartmentState(quantity=3, capacity=3),
        physics.PassOffEvent(location=LOCATION, requested_quantity=1),
    )

    assert empty.moved_quantity == 0
    assert empty.source.quantity == 0
    assert empty.target.quantity == 2
    assert full.moved_quantity == 0
    assert full.source.quantity == 8
    assert full.target.quantity == 3


def test_no_event_performs_no_work_and_creates_no_state():
    source = physics.CompartmentState(quantity=4, capacity=8)
    target = physics.CompartmentState(quantity=1, capacity=8)

    result = physics.transition_pass_off(source, target, None)

    assert result.source is source
    assert result.target is target
    assert result.location is None
    assert result.moved_quantity == 0
    assert not hasattr(result, "history")


def profile_module_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)

    def profiler(frame, event, _arg):
        if event == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    source = physics.CompartmentState(quantity=iterations, capacity=iterations)
    target = physics.CompartmentState(quantity=0, capacity=iterations)
    pass_off = physics.PassOffEvent(location=LOCATION, requested_quantity=1)
    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            result = physics.transition_pass_off(source, target, pass_off)
            source = result.source
            target = result.target
    finally:
        sys.setprofile(None)
    return calls


def test_work_is_one_non_recursive_physics_call_per_reached_lane():
    one_thousand = profile_module_calls(1_000)
    ten_thousand = profile_module_calls(10_000)

    assert one_thousand == Counter({"transition_pass_off": 1_000})
    assert ten_thousand == Counter({"transition_pass_off": 10_000})


def test_module_imports_no_custody_or_infrastructure_dependency():
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
