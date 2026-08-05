from __future__ import annotations

from tools.model_sparse_krimelack_coupling import (
    LocalFractal,
    MODEL_VERDICT,
    SparseCoupling,
    transition_sparse_krimelack,
)


MAX_STATE = 1_000_000
MAX_WORKING = 1_000_000
FIELD = "a" * 64
ANATOMY = "b" * 64


def _local(lineage: str, trits: tuple[int, ...]) -> LocalFractal:
    return LocalFractal.create(
        neuron_lineage=lineage,
        complete_field_receipt_sha256=FIELD,
        perspective_receipt_sha256=(lineage[-1] * 64),
        trits=trits,
    )


def _edge(
    source: str,
    target: str,
    *,
    polarity: int = 1,
    shift: int = 0,
) -> SparseCoupling:
    return SparseCoupling(
        source_lineage=source,
        target_lineage=target,
        polarity=polarity,
        positional_shift=shift,
        anatomy_receipt_sha256=ANATOMY,
    )


def _transition(*, prior=None, locals_, couplings=()):
    return transition_sparse_krimelack(
        prior=prior,
        current_local_fractals=tuple(locals_),
        couplings=tuple(couplings),
        max_state_bytes=MAX_STATE,
        max_working_bytes=MAX_WORKING,
    )


def _settlement(state, lineage):
    return next(
        value for value in state.settlements
        if value.neuron_lineage == lineage
    )


def test_one_neuron_has_only_its_exact_local_settlement():
    assert MODEL_VERDICT == "rejected_not_typed_krimelack_coupling"
    local = _local("neuron-1", (1, 0, -1, 1))
    state = _transition(locals_=(local,))

    assert state.generation == 1
    assert _settlement(state, "neuron-1").trits == local.trits
    assert _settlement(state, "neuron-1").contributions == ()


def test_three_neuron_cycle_has_no_arrivals_at_genesis_then_exact_arrivals():
    locals_ = (
        _local("neuron-1", (1, 0, -1)),
        _local("neuron-2", (-1, 1, 0)),
        _local("neuron-3", (0, -1, 1)),
    )
    cycle = (
        _edge("neuron-1", "neuron-2"),
        _edge("neuron-2", "neuron-3"),
        _edge("neuron-3", "neuron-1"),
    )
    genesis = _transition(locals_=locals_, couplings=cycle)
    successor = _transition(
        prior=genesis,
        locals_=locals_,
        couplings=cycle,
    )

    assert all(not item.contributions for item in genesis.settlements)
    assert all(len(item.contributions) == 1 for item in successor.settlements)
    assert _settlement(successor, "neuron-1").trits != locals_[0].trits
    assert _settlement(successor, "neuron-2").trits != locals_[1].trits
    assert _settlement(successor, "neuron-3").trits != locals_[2].trits


def test_changing_only_predecessor_changes_reached_target_settlement():
    first = (
        _local("neuron-1", (1, 0, 1)),
        _local("neuron-2", (0, 1, 0)),
    )
    changed = (
        _local("neuron-1", (-1, 0, -1)),
        first[1],
    )
    coupling = (_edge("neuron-1", "neuron-2", shift=1),)
    baseline_prior = _transition(locals_=first, couplings=coupling)
    changed_prior = _transition(locals_=changed, couplings=coupling)
    baseline = _transition(
        prior=baseline_prior,
        locals_=first,
        couplings=coupling,
    )
    altered = _transition(
        prior=changed_prior,
        locals_=first,
        couplings=coupling,
    )

    assert _settlement(baseline, "neuron-2").trits != (
        _settlement(altered, "neuron-2").trits
    )
    assert _settlement(baseline, "neuron-1").trits == (
        _settlement(altered, "neuron-1").trits
    )


def test_opposed_predecessors_cancel_exactly_without_a_score():
    locals_ = (
        _local("neuron-1", (1, -1, 1)),
        _local("neuron-2", (1, -1, 1)),
        _local("neuron-3", (-1, 0, 1)),
    )
    couplings = (
        _edge("neuron-1", "neuron-3", polarity=1),
        _edge("neuron-2", "neuron-3", polarity=-1),
    )
    prior = _transition(locals_=locals_, couplings=couplings)
    successor = _transition(
        prior=prior,
        locals_=locals_,
        couplings=couplings,
    )

    target = _settlement(successor, "neuron-3")
    assert target.trits == locals_[2].trits
    assert len(target.contributions) == 2


def test_four_neuron_cycle_is_deterministic_and_state_size_does_not_run_away():
    locals_ = tuple(
        _local(f"neuron-{index}", trits)
        for index, trits in enumerate((
            (1, 0, -1, 1),
            (-1, 1, 0, -1),
            (0, -1, 1, 0),
            (1, 1, -1, 0),
        ), start=1)
    )
    cycle = (
        _edge("neuron-1", "neuron-2", shift=0),
        _edge("neuron-2", "neuron-3", shift=1),
        _edge("neuron-3", "neuron-4", shift=2),
        _edge("neuron-4", "neuron-1", shift=0),
    )
    state = _transition(locals_=locals_, couplings=cycle)
    encoded_sizes = []
    generations = []
    settlement_shapes = []
    for _ in range(1_000):
        state = _transition(
            prior=state,
            locals_=locals_,
            couplings=cycle,
        )
        encoded_sizes.append(len(state.encode(max_state_bytes=MAX_STATE)))
        generations.append(state.generation)
        settlement_shapes.append(tuple(
            value.trits for value in state.settlements
        ))

    # Only the canonical decimal generation field changes width.  The coupled
    # neuronal result itself remains constant because it is not reinjected.
    # Generation is written once at state level and once in each of four
    # settlement records. Its decimal width is the exact 15-byte difference.
    expected_metadata_growth = 5 * (
        len(str(max(generations))) - len(str(min(generations)))
    )
    assert max(encoded_sizes) - min(encoded_sizes) == (
        expected_metadata_growth
    )
    assert len(set(settlement_shapes)) == 1


def test_whole_word_addition_crosses_typed_positions_and_is_rejected():
    locals_ = (
        _local("neuron-1", (1,)),
        _local("neuron-2", (1,)),
    )
    coupling = (_edge("neuron-1", "neuron-2"),)
    prior = _transition(locals_=locals_, couplings=coupling)
    successor = _transition(
        prior=prior,
        locals_=locals_,
        couplings=coupling,
    )

    # 1 + 1 = 2 = (-1, +1) in balanced ternary.  A carry created a second
    # position that was absent from both one-trit typed inputs.  Exact
    # arithmetic therefore does not preserve typed DSF coordinate boundaries.
    assert _settlement(successor, "neuron-2").trits == (-1, 1)
    assert MODEL_VERDICT == "rejected_not_typed_krimelack_coupling"


def test_topology_change_and_physical_byte_overrun_fail_closed():
    locals_ = (
        _local("neuron-1", (1, 0, -1)),
        _local("neuron-2", (-1, 1, 0)),
    )
    coupling = (_edge("neuron-1", "neuron-2"),)
    prior = _transition(locals_=locals_, couplings=coupling)

    try:
        transition_sparse_krimelack(
            prior=prior,
            current_local_fractals=locals_,
            couplings=(_edge("neuron-2", "neuron-1"),),
            max_state_bytes=MAX_STATE,
            max_working_bytes=MAX_WORKING,
        )
    except ValueError as error:
        assert "growth law" in str(error)
    else:
        raise AssertionError("unratified topology change was admitted")

    huge_shift = (_edge("neuron-1", "neuron-2", shift=10_000),)
    huge_prior = _transition(locals_=locals_, couplings=huge_shift)
    try:
        transition_sparse_krimelack(
            prior=huge_prior,
            current_local_fractals=locals_,
            couplings=huge_shift,
            max_state_bytes=MAX_STATE,
            max_working_bytes=100,
        )
    except ValueError as error:
        assert "working bytes" in str(error)
    else:
        raise AssertionError("unadmitted positional work was allocated")
