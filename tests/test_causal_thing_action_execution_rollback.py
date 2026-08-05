from __future__ import annotations

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PoseMM,
    PositionMM,
)
from tests.test_causal_thing_action_execution import (
    _executable_graph,
)
from tests.test_causal_thing_mosaic import _execute


def _physical_state(physical, causal_owner) -> tuple[object, ...]:
    return (
        causal_owner.sequence_snapshot(),
        physical._binaural_auditory_l5_owner.encoded_snapshot(),
        physical._anonymous_av_continuity_owner.encoded_snapshot(),
        physical.status(),
    )


def test_downstream_failure_rolls_execution_back_and_retry_is_identical():
    world, physical, causal_owner, intents, intent, executor = (
        _executable_graph()
    )
    before_world = world.encoded_snapshot()
    before_intents = intents.snapshot_encoded()
    before_physical = _physical_state(physical, causal_owner)

    executed = executor.execute(intent=intent)
    committed_world = world.encoded_snapshot()
    assert committed_world != before_world
    assert not intents.verify_live(intent)
    executor.verify(executed.execution)
    assert (
        executed.execution.world_execution_receipt_sha256
        == executed.world_execution.authority_receipt_sha256
    )
    assert (
        executed.execution.actual_outcome_settlement_receipt_sha256
        == executed.physical_mount.causal_settlement
        .authority_receipt_sha256
    )
    assert (
        executed.execution.outcome_custody_receipt_sha256
        == executed.custody_view.parent_custody_receipt_sha256
    )
    retained_field_orders = tuple(
        tuple(name for name, _value in field_tuple.fields)
        for interpretation in (
            executed.physical_mount.causal_settlement.interpretations
        )
        if interpretation.state == "observed"
        for substream in interpretation.substreams
        for field_tuple in substream.field_tuples
    )
    assert retained_field_orders
    assert all(
        value == DSF_FIELD_ORDER for value in retained_field_orders
    )

    executor.rollback_committed_execution(executed.undo)
    assert world.encoded_snapshot() == before_world
    assert intents.snapshot_encoded() == before_intents
    assert intents.verify_live(intent)
    assert _physical_state(physical, causal_owner) == before_physical

    retried = executor.execute(intent=intent)
    assert retried.execution == executed.execution
    assert retried.world_execution == executed.world_execution
    assert (
        retried.physical_mount.evidence_receipt
        == executed.physical_mount.evidence_receipt
    )
    assert (
        retried.physical_mount.causal_settlement
        == executed.physical_mount.causal_settlement
    )
    assert retried.custody_view == executed.custody_view
    assert world.encoded_snapshot() == committed_world


def test_execution_undo_is_owner_bound_single_use_and_stale_safe():
    world, physical, causal_owner, intents, intent, executor = (
        _executable_graph()
    )
    executed = executor.execute(intent=intent)

    (
        _other_world,
        _other_physical,
        _other_causal,
        _other_intents,
        _other_intent,
        other_executor,
    ) = _executable_graph()
    with pytest.raises(ValueError, match="changed custody"):
        other_executor.rollback_committed_execution(executed.undo)

    executor.rollback_committed_execution(executed.undo)
    with pytest.raises(ValueError, match="changed custody"):
        executor.rollback_committed_execution(executed.undo)

    replay = executor.execute(intent=intent)
    later = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(800, 1_400, 0), 90_000), 200_000),
        901,
    )
    assert later.disposition == "applied"
    stale_world = world.encoded_snapshot()
    stale_intents = intents.snapshot_encoded()
    stale_physical = _physical_state(physical, causal_owner)

    with pytest.raises(ValueError, match="action tail changed"):
        executor.rollback_committed_execution(replay.undo)
    assert world.encoded_snapshot() == stale_world
    assert intents.snapshot_encoded() == stale_intents
    assert _physical_state(physical, causal_owner) == stale_physical
