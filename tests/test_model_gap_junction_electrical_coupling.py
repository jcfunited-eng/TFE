from __future__ import annotations

import ast
import inspect
import sys
from collections import Counter
from fractions import Fraction

from tools import model_gap_junction_electrical_coupling as physics


def line(*potentials: Fraction) -> tuple[physics.Membrane, ...]:
    return tuple(
        physics.Membrane(
            lineage=index + 1,
            surface_area=Fraction(2),
            specific_capacitance=Fraction(1, 2),
            potential=potential,
        )
        for index, potential in enumerate(potentials)
    )


def ring(size: int) -> tuple[physics.GapJunction, ...]:
    return tuple(
        physics.GapJunction(
            left_lineage=index + 1,
            right_lineage=(index + 1) % size + 1,
            population_count=2,
            open_occupancy=Fraction(1),
            unit_conductance=Fraction(1, 2),
        )
        for index in range(size)
    )


def total_charge(membranes: tuple[physics.Membrane, ...]) -> Fraction:
    return sum(
        (
            membrane.capacitance * membrane.potential
            for membrane in membranes
        ),
        Fraction(0),
    )


def test_fractional_ensemble_occupancy_derives_conductance() -> None:
    junction = physics.GapJunction(
        left_lineage=1,
        right_lineage=2,
        population_count=10,
        open_occupancy=Fraction(1, 3),
        unit_conductance=Fraction(3, 10),
    )
    assert junction.conductance == 1


def test_one_uncoupled_neuron_is_exact_quiescence() -> None:
    prior = line(Fraction(7, 11))
    result = physics.transition_gap_junctions(
        prior, (), Fraction(10_000)
    )
    assert result.membranes == prior
    assert result.transfers == ()
    assert physics.maximum_admitted_interval(prior, ()) is None


def test_three_neuron_ring_derives_its_interval_from_local_anatomy() -> None:
    membranes = line(Fraction(1), Fraction(0), Fraction(-1))
    assert physics.maximum_admitted_interval(
        membranes, ring(3)
    ) == Fraction(1, 2)


def test_three_neuron_ring_conserves_every_edge_and_total_charge() -> None:
    prior = line(Fraction(1), Fraction(0), Fraction(-1))
    result = physics.transition_gap_junctions(
        prior, ring(3), Fraction(1, 2)
    )
    assert all(
        transfer.left_charge_delta + transfer.right_charge_delta == 0
        for transfer in result.transfers
    )
    assert total_charge(result.membranes) == total_charge(prior)


def test_repeated_three_neuron_coupling_is_bounded_without_new_energy() -> None:
    state = line(Fraction(1), Fraction(0), Fraction(-1))
    junctions = ring(3)
    duration = physics.maximum_admitted_interval(state, junctions)
    assert duration is not None
    for _ in range(10_000):
        state = physics.transition_gap_junctions(
            state, junctions, duration
        ).membranes
    assert total_charge(state) == 0
    assert all(-1 <= value.potential <= 1 for value in state)


def test_nine_neuron_sparse_ring_remains_local_and_bounded() -> None:
    state = line(*(Fraction(value) for value in range(-4, 5)))
    junctions = ring(9)
    duration = physics.maximum_admitted_interval(state, junctions)
    assert duration == Fraction(1, 2)
    charge = total_charge(state)
    for _ in range(1_000):
        result = physics.transition_gap_junctions(
            state, junctions, duration
        )
        assert len(result.transfers) == 9
        state = result.membranes
    assert total_charge(state) == charge
    assert all(-4 <= value.potential <= 4 for value in state)


def profile_calls(iterations: int) -> Counter[str]:
    calls: Counter[str] = Counter()
    module_file = inspect.getsourcefile(physics)
    state = line(Fraction(1), Fraction(0), Fraction(-1))
    junctions = ring(3)

    def profiler(frame, event_name, _arg):
        if event_name == "call" and frame.f_code.co_filename == module_file:
            calls[frame.f_code.co_name] += 1
        return profiler

    sys.setprofile(profiler)
    try:
        for _ in range(iterations):
            state = physics.transition_gap_junctions(
                state, junctions, Fraction(1, 2)
            ).membranes
    finally:
        sys.setprofile(None)
    return calls


def test_calls_scale_linearly_with_transitions_not_history() -> None:
    one_thousand = profile_calls(1_000)
    two_thousand = profile_calls(2_000)
    assert one_thousand["transition_gap_junctions"] == 1_000
    assert two_thousand == Counter(
        {name: count * 2 for name, count in one_thousand.items()}
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
