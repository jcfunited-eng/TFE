"""Executable properties and counterexamples for the rejected D3 candidate.

The exact arithmetic properties are retained because they are useful negative
evidence.  The final tests demonstrate why this candidate cannot become the
Guala neuronal coupling law: constant drive yields unbounded winding and
fan-out copies transition quantity into a self-sustaining recurrent graph.
"""

from __future__ import annotations

from tools.model_typed_krimelack_phase_coupling import (
    ComponentAddress,
    CoordinateType,
    LocalPhaseDrive,
    PhaseComponent,
    SparsePhaseRoute,
    create_phase_fabric,
    decode_phase_fabric,
    transition_phase_fabric,
)


MAX_STATE = 2_000_000
MAX_TRITS = 10_000
TOPOLOGY = "a" * 64
FIELD = "b" * 64
PERSPECTIVE = "c" * 64
FRACTAL = "d" * 64
D_TYPE = CoordinateType("D_k", "vertex_value")


def _address(neuron: int, component: str = "D:vertex") -> ComponentAddress:
    return ComponentAddress(f"neuron-{neuron}", component)


def _component(
    neuron: int,
    *,
    width: int = 1,
    phase_residue: int = 0,
) -> PhaseComponent:
    return PhaseComponent.create(
        address=_address(neuron),
        coordinate_type=D_TYPE,
        ternary_width=width,
        phase_residue=phase_residue,
        winding=0,
        last_transition_generation=0,
        max_working_trits=MAX_TRITS,
    )


def _route(source: int, target: int) -> SparsePhaseRoute:
    return SparsePhaseRoute.create(
        source=_address(source),
        target=_address(target),
        coordinate_type=D_TYPE,
        topology_generation=1,
        topology_authority_receipt_sha256=TOPOLOGY,
    )


def _drive(neuron: int, trit: int) -> LocalPhaseDrive:
    return LocalPhaseDrive.create(
        target=_address(neuron),
        coordinate_type=D_TYPE,
        structural_trit=trit,
        complete_field_receipt_sha256=FIELD,
        perspective_receipt_sha256=PERSPECTIVE,
        local_fractal_receipt_sha256=FRACTAL,
    )


def _fabric(neuron_count: int, routes=(), *, phase_residue: int = 0):
    return create_phase_fabric(
        components=tuple(
            _component(index, phase_residue=phase_residue)
            for index in range(1, neuron_count + 1)
        ),
        routes=tuple(routes),
        max_state_bytes=MAX_STATE,
        max_working_trits=MAX_TRITS,
    )


def _step(state, *drives):
    return transition_phase_fabric(
        prior=state,
        local_drives=tuple(drives),
        max_state_bytes=MAX_STATE,
        max_working_trits=MAX_TRITS,
    )


def _component_from(state, neuron):
    return next(
        value for value in state.components
        if value.address == _address(neuron)
    )


def _settlement_from(state, neuron):
    return next(
        value for value in state.settlements
        if value.target == _address(neuron)
    )


def test_one_neuron_centered_word_arithmetic_is_exact():
    state = _fabric(1)
    state = _step(state, _drive(1, 1))
    assert (_component_from(state, 1).phase_residue,
            _component_from(state, 1).winding) == (1, 0)

    state = _step(state, _drive(1, 1))
    component = _component_from(state, 1)
    settlement = _settlement_from(state, 1)
    assert (component.phase_residue, component.winding) == (-1, 1)
    assert settlement.winding_delta == 1
    assert settlement.net_drive == 1

    state = _step(state, _drive(1, 1))
    assert (_component_from(state, 1).phase_residue,
            _component_from(state, 1).winding) == (0, 1)


def test_three_neuron_cycle_can_carry_one_causal_transition_path():
    cycle = (_route(1, 2), _route(2, 3), _route(3, 1))
    state = _fabric(3, cycle)

    state = _step(state, _drive(1, 1))
    state = _step(state, _drive(1, 1))
    assert len(state.pending_events) == 1
    assert state.pending_events[0].target == _address(2)

    state = _step(state)
    assert _component_from(state, 2).phase_residue == 1
    assert _settlement_from(state, 2).consumed_event_receipts

    # Neuron 1 needs three further +1 impulses to cross its centered word
    # again.  The second received transition then crosses neuron 2.
    for _ in range(3):
        state = _step(state, _drive(1, 1))
    assert state.pending_events[0].target == _address(2)
    state = _step(state)
    assert _component_from(state, 2).winding == 1
    assert state.pending_events[0].target == _address(3)
    state = _step(state)
    assert _component_from(state, 3).phase_residue == 1


def test_opposed_events_preserve_participation_but_cancel_net_drive():
    routes = (_route(1, 4), _route(2, 4), _route(4, 3))
    state = _fabric(4, routes)
    state = _step(state, _drive(1, 1), _drive(2, -1))
    state = _step(state, _drive(1, 1), _drive(2, -1))
    assert len(state.pending_events) == 2
    assert {value.signed_crossing_count for value in state.pending_events} == {
        -1, 1
    }

    state = _step(state)
    target = _settlement_from(state, 4)
    assert target.net_drive == 0
    assert target.winding_delta == 0
    assert len(target.consumed_event_receipts) == 2
    assert _component_from(state, 4).phase_residue == 0
    assert state.pending_events == ()


def test_cold_round_trip_preserves_next_transition_byte_for_byte():
    state = _fabric(3, (_route(1, 2), _route(2, 3)))
    state = _step(state, _drive(1, 1))
    state = _step(state, _drive(1, 1))
    encoded = state.encode(max_state_bytes=MAX_STATE)
    cold = decode_phase_fabric(
        encoded,
        max_state_bytes=MAX_STATE,
        max_working_trits=MAX_TRITS,
    )

    assert cold == state
    warm_successor = _step(state)
    cold_successor = _step(cold)
    assert cold_successor == warm_successor
    assert cold_successor.encode(max_state_bytes=MAX_STATE) == (
        warm_successor.encode(max_state_bytes=MAX_STATE)
    )


def test_zero_local_drive_remains_distinct_from_no_local_evidence():
    state = _fabric(1)
    absent = _step(state)
    quiescent = _step(state, _drive(1, 0))

    assert _component_from(absent, 1) == _component_from(quiescent, 1)
    assert _settlement_from(absent, 1).local_drive_receipt_sha256 is None
    assert _settlement_from(quiescent, 1).local_drive_receipt_sha256 is not None
    assert absent.authority_receipt_sha256 != quiescent.authority_receipt_sha256


def test_fixed_topology_retains_only_current_settlement_and_pending_arena():
    state = _fabric(3, (_route(1, 2), _route(2, 3)))
    component_counts = set()
    route_counts = set()
    pending_counts = []
    sizes = []
    for _ in range(1_000):
        state = _step(state, _drive(1, 1))
        component_counts.add(len(state.components))
        route_counts.add(len(state.routes))
        pending_counts.append(len(state.pending_events))
        sizes.append(len(state.encode(max_state_bytes=MAX_STATE)))

    assert component_counts == {3}
    assert route_counts == {2}
    assert max(pending_counts) <= 1
    # Event and settlement histories are replaced, not appended.  The bounded
    # variation is the current pending-event body plus growing integer digits.
    assert max(sizes) - min(sizes) < 800


def test_cross_type_route_and_unadmitted_width_fail_before_transition():
    c_component = PhaseComponent.create(
        address=_address(2),
        coordinate_type=CoordinateType("C_k", "oriented_area"),
        ternary_width=1,
        phase_residue=0,
        winding=0,
        last_transition_generation=0,
        max_working_trits=MAX_TRITS,
    )
    route = _route(1, 2)
    try:
        create_phase_fabric(
            components=(_component(1), c_component),
            routes=(route,),
            max_state_bytes=MAX_STATE,
            max_working_trits=MAX_TRITS,
        )
    except ValueError as error:
        assert "coordinate types" in str(error)
    else:
        raise AssertionError("cross-type neuronal route was admitted")

    try:
        PhaseComponent.create(
            address=_address(1),
            coordinate_type=D_TYPE,
            ternary_width=MAX_TRITS + 1,
            phase_residue=0,
            winding=0,
            last_transition_generation=0,
            max_working_trits=MAX_TRITS,
        )
    except ValueError as error:
        assert "working trits" in str(error)
    else:
        raise AssertionError("unadmitted phase width was allocated")


def test_counterexample_constant_unchanged_drive_makes_winding_unbounded():
    state = _fabric(1)
    for _ in range(300):
        state = _step(state, _drive(1, 1))
    first_winding = _component_from(state, 1).winding
    for _ in range(600):
        state = _step(state, _drive(1, 1))
    second_winding = _component_from(state, 1).winding

    assert first_winding == 100
    assert second_winding == 300
    assert second_winding > first_winding


def test_counterexample_fanout_copies_one_transition_to_every_edge():
    routes = tuple(_route(1, target) for target in (2, 3, 4))
    state = _fabric(4, routes)
    state = _step(state, _drive(1, 1))
    state = _step(state, _drive(1, 1))

    assert len(state.pending_events) == 3
    assert sum(abs(event.signed_crossing_count)
               for event in state.pending_events) == 3


def test_counterexample_complete_four_neuron_graph_never_quiesces():
    routes = tuple(
        _route(source, target)
        for source in range(1, 5)
        for target in range(1, 5)
        if source != target
    )
    state = _fabric(4, routes)
    all_positive = tuple(_drive(neuron, 1) for neuron in range(1, 5))
    state = _step(state, *all_positive)
    state = _step(state, *all_positive)
    assert len(state.pending_events) == 12

    windings = []
    for _ in range(20):
        state = _step(state)
        assert len(state.pending_events) == 12
        windings.append(sum(component.winding for component in state.components))

    assert windings == sorted(windings)
    assert windings[-1] > windings[0]
