from fractions import Fraction

import pytest

from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    BoundedThermalState,
    ConductiveThermalEdge,
    ThermalBathEdge,
    ThermalNodeState,
    ThermalPowerSource,
    advance_bounded_thermal_state,
)


def _state(
    temperatures: tuple[int, ...],
    capacities: tuple[int, ...],
    *,
    conductive_count: int,
    bath_count: int,
    power_count: int,
) -> BoundedThermalState:
    return BoundedThermalState(
        nodes=tuple(
            ThermalNodeState(
                energy_microjoules=temperature * capacity,
                capacity_microjoules_per_millikelvin=capacity,
            )
            for temperature, capacity in zip(
                temperatures, capacities, strict=True
            )
        ),
        conductive_residue_numerators=(0,) * conductive_count,
        bath_residue_numerators=(0,) * bath_count,
        power_residue_numerators=(0,) * power_count,
    )


def test_quiescent_equal_temperatures_create_no_heat() -> None:
    edges = (ConductiveThermalEdge(0, 1, 4_000_000),)
    state = _state(
        (295_150, 295_150),
        (90_000_000, 4_700_000),
        conductive_count=1,
        bath_count=0,
        power_count=0,
    )

    result = advance_bounded_thermal_state(
        state,
        conductive_edges=edges,
        bath_edges=(),
        power_sources=(),
        duration_microseconds=2_000_000,
    )

    assert result.successor == state
    assert result.conductive_transfers_microjoules == (0,)


def test_hot_node_heats_cold_node_and_internal_energy_is_exact() -> None:
    edges = (ConductiveThermalEdge(0, 1, 4_000_000),)
    state = _state(
        (310_000, 295_000),
        (40_000_000, 4_000_000),
        conductive_count=1,
        bath_count=0,
        power_count=0,
    )

    result = advance_bounded_thermal_state(
        state,
        conductive_edges=edges,
        bath_edges=(),
        power_sources=(),
        duration_microseconds=2_000_000,
    )

    transferred = result.conductive_transfers_microjoules[0]
    assert transferred == 120_000_000
    assert result.successor.nodes[0].energy_microjoules == (
        state.nodes[0].energy_microjoules - transferred
    )
    assert result.successor.nodes[1].energy_microjoules == (
        state.nodes[1].energy_microjoules + transferred
    )
    assert result.external_energy_into_nodes_microjoules == 0


def test_opposed_sparse_edges_settle_from_one_common_predecessor() -> None:
    edges = (
        ConductiveThermalEdge(0, 1, 1_000_000),
        ConductiveThermalEdge(1, 2, 1_000_000),
    )
    state = _state(
        (310_000, 300_000, 290_000),
        (1_000_000, 1_000_000, 1_000_000),
        conductive_count=2,
        bath_count=0,
        power_count=0,
    )

    result = advance_bounded_thermal_state(
        state,
        conductive_edges=edges,
        bath_edges=(),
        power_sources=(),
        duration_microseconds=1_000_000,
    )

    assert result.conductive_transfers_microjoules == (10_000_000, 10_000_000)
    assert result.successor.nodes[1] == state.nodes[1]


def test_thermal_bath_and_metabolic_power_are_exact_external_energy() -> None:
    baths = (ThermalBathEdge(0, 295_150, 5_000_000),)
    sources = (ThermalPowerSource(1, 41_000_000),)
    state = _state(
        (294_150, 309_950),
        (90_000_000, 40_000_000),
        conductive_count=0,
        bath_count=1,
        power_count=1,
    )

    result = advance_bounded_thermal_state(
        state,
        conductive_edges=(),
        bath_edges=baths,
        power_sources=sources,
        duration_microseconds=2_000_000,
    )

    assert result.bath_transfers_into_nodes_microjoules == (10_000_000,)
    assert result.powered_into_nodes_microjoules == (82_000_000,)
    assert result.external_energy_into_nodes_microjoules == 92_000_000


def test_sub_quantum_exchange_accumulates_only_in_fixed_residue() -> None:
    edges = (ConductiveThermalEdge(0, 1, 1),)
    state = _state(
        (300_001, 300_000),
        (1_000_000, 1_000_000),
        conductive_count=1,
        bath_count=0,
        power_count=0,
    )
    first = advance_bounded_thermal_state(
        state,
        conductive_edges=edges,
        bath_edges=(),
        power_sources=(),
        duration_microseconds=1,
    )

    assert first.conductive_transfers_microjoules == (0,)
    assert first.successor.nodes == state.nodes
    assert first.successor.conductive_residue_numerators[0] != 0
    assert abs(first.successor.conductive_residue_numerators[0]) < (
        1_000_000 * 1_000 * 1_000_000 * 1_000_000
    )


def test_fixed_state_size_does_not_depend_on_elapsed_interval_count() -> None:
    edges = (ConductiveThermalEdge(0, 1, 1_000_000),)
    baths = (ThermalBathEdge(1, 295_150, 2_000_000),)
    sources = (ThermalPowerSource(0, 41_000_000),)
    current = _state(
        (309_950, 306_150),
        (42_000_000, 4_700_000),
        conductive_count=1,
        bath_count=1,
        power_count=1,
    )

    for _ in range(10_000):
        current = advance_bounded_thermal_state(
            current,
            conductive_edges=edges,
            bath_edges=baths,
            power_sources=sources,
            duration_microseconds=1_000,
        ).successor

    assert len(current.nodes) == 2
    assert len(current.conductive_residue_numerators) == 1
    assert len(current.bath_residue_numerators) == 1
    assert len(current.power_residue_numerators) == 1


def test_transition_refuses_depletion_below_zero() -> None:
    edges = (ConductiveThermalEdge(0, 1, 1_000_000_000_000),)
    state = _state(
        (1, 0),
        (1, 1),
        conductive_count=1,
        bath_count=0,
        power_count=0,
    )

    with pytest.raises(ValueError, match="thermal-node energy"):
        advance_bounded_thermal_state(
            state,
            conductive_edges=edges,
            bath_edges=(),
            power_sources=(),
            duration_microseconds=5_000_000,
        )


def test_temperature_is_retained_as_exact_rational() -> None:
    node = ThermalNodeState(10, 3)

    assert node.temperature_millikelvin == Fraction(10, 3)


def test_duplicate_edge_and_unbounded_residue_are_refused() -> None:
    state = _state(
        (300_000, 300_000),
        (1, 1),
        conductive_count=2,
        bath_count=0,
        power_count=0,
    )
    duplicate_edges = (
        ConductiveThermalEdge(0, 1, 1),
        ConductiveThermalEdge(1, 0, 1),
    )
    with pytest.raises(ValueError, match="repeats one physical edge"):
        state.verify(duplicate_edges, (), ())

    invalid_residue = BoundedThermalState(
        nodes=state.nodes,
        conductive_residue_numerators=(1_000_000_000_000,),
        bath_residue_numerators=(),
        power_residue_numerators=(),
    )
    with pytest.raises(ValueError, match="escaped its fixed denominator"):
        invalid_residue.verify((ConductiveThermalEdge(0, 1, 1),), (), ())


def test_separated_fixed_topology_edge_retains_identity_without_transfer() -> None:
    edges = (
        ConductiveThermalEdge(0, 1, 1_000_000),
        ConductiveThermalEdge(0, 2, 0),
    )
    state = _state(
        (310_000, 295_000, 280_000),
        (1_000_000, 1_000_000, 1_000_000),
        conductive_count=2,
        bath_count=0,
        power_count=0,
    )

    result = advance_bounded_thermal_state(
        state,
        conductive_edges=edges,
        bath_edges=(),
        power_sources=(),
        duration_microseconds=1_000_000,
    )

    assert result.conductive_transfers_microjoules == (15_000_000, 0)
    assert result.successor.conductive_residue_numerators[1] == 0
    assert result.successor.nodes[2] == state.nodes[2]
