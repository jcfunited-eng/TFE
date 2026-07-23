from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodimentWorldAuthority,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


AUTHORITY_KEY = "embodied-sensory-outcome-test-key"


def _owner():
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )


def _execute(world, command, intent: int, *, port_id=PORT_ID):
    before = world.observation_snapshot()
    return world.execute_port_command(
        port_id=port_id,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=f"{intent:064x}",
        expected_revision=before.revision,
    )


def _observed(settlement, sense):
    return next(item for item in settlement.interpretations if item.sense == sense)


def test_exact_geometry_change_changes_native_full_dsf_field() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    first = transducer.transduce(
        world.observation_snapshot(), causal_owner=_owner(), commit=False
    )

    moved = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(1000, 1400, 0), 90_000)),
        1,
    )
    assert moved.disposition == "applied"
    second = transducer.transduce(
        moved.after,
        causal_owner=_owner(),
        execution_receipt=moved,
        commit=False,
    )

    assert (
        first.causal_settlement.structural_fingerprint
        != second.causal_settlement.structural_fingerprint
    )
    assert (
        _observed(first.causal_settlement, "sight").structural_fingerprint
        != _observed(second.causal_settlement, "sight").structural_fingerprint
    )
    assert (
        _observed(first.causal_settlement, "body").structural_fingerprint
        != _observed(second.causal_settlement, "body").structural_fingerprint
    )
    for interpretation in second.causal_settlement.interpretations:
        for substream in interpretation.substreams:
            for field_tuple in substream.field_tuples:
                assert tuple(name for name, _value in field_tuple.fields) == DSF_FIELD_ORDER
    assert second.causal_settlement.routing_chis == ()
    second.built_full_field.boundary.verify(
        second.built_full_field.receipt_registry
    )
    second.causal_settlement.verify()


def test_repeated_exact_world_state_is_byte_identity_deterministic() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    observation = world.observation_snapshot()
    left = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY).transduce(
        observation, causal_owner=_owner(), commit=False
    )
    right = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY).transduce(
        observation, causal_owner=_owner(), commit=False
    )

    assert left.observation_receipt == right.observation_receipt
    assert (
        left.built_full_field.boundary.authority_receipt_sha256
        == right.built_full_field.boundary.authority_receipt_sha256
    )
    assert left.causal_settlement.event_id == right.causal_settlement.event_id
    assert (
        left.causal_settlement.structural_fingerprint
        == right.causal_settlement.structural_fingerprint
    )
    assert left.causal_settlement == right.causal_settlement


def test_same_geometry_at_later_revision_has_same_structural_identity() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    initial = transducer.transduce(
        world.observation_snapshot(), causal_owner=_owner(), commit=False
    )
    _execute(
        world,
        MoveCommand(PoseMM(PositionMM(1000, 1400, 0), 90_000)),
        30,
    )
    returned = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(1000, 1000, 0), 0)),
        31,
    )
    later = transducer.transduce(
        returned.after,
        causal_owner=_owner(),
        execution_receipt=returned,
        commit=False,
    )

    assert initial.observation_receipt.world_revision == 0
    assert later.observation_receipt.world_revision == 2
    assert initial.observation_receipt != later.observation_receipt
    assert (
        initial.causal_settlement.structural_fingerprint
        == later.causal_settlement.structural_fingerprint
    )


def test_world_observation_and_outcome_receipt_tamper_fail_closed() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    observation = world.observation_snapshot()
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)

    with pytest.raises(ValueError, match="state identity"):
        transducer.transduce(
            replace(observation, revision=observation.revision + 1),
            causal_owner=_owner(),
            commit=False,
        )
    with pytest.raises(ValueError, match="HMAC"):
        EmbodimentSensoryOutcomeAuthority(authority_key="wrong-key").transduce(
            observation, causal_owner=_owner(), commit=False
        )

    outcome = transducer.transduce(
        observation, causal_owner=_owner(), commit=False
    )
    with pytest.raises(ValueError, match="HMAC"):
        transducer.verify_outcome_observation_receipt(
            replace(outcome.observation_receipt, world_revision=17)
        )


def test_applied_execution_receipt_is_authenticated_and_bound_to_after_field() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    before = world.observation_snapshot()
    execution = _execute(world, PickCommand("W1-object-1"), 2)
    assert execution.disposition == "applied"
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    outcome = transducer.transduce(
        execution.after,
        causal_owner=_owner(),
        execution_receipt=execution,
        commit=False,
    )

    assert (
        outcome.observation_receipt.execution_receipt_sha256
        == execution.authority_receipt_sha256
    )
    assert (
        outcome.observation_receipt.world_observation_receipt_sha256
        == execution.after.authority_receipt_sha256
    )
    assert outcome.built_full_field.boundary.assembly_id == (
        f"embodied-outcome-{outcome.observation_receipt.authority_receipt_sha256}"
    )
    assert _observed(outcome.causal_settlement, "touch").state == "observed"
    assert len(_observed(outcome.causal_settlement, "touch").substreams) == 1

    with pytest.raises(ValueError, match="does not end"):
        transducer.transduce(
            before,
            causal_owner=_owner(),
            execution_receipt=execution,
            commit=False,
        )
    with pytest.raises(ValueError, match="command identity changed|HMAC"):
        transducer.transduce(
            execution.after,
            causal_owner=_owner(),
            execution_receipt=replace(execution, command_sha256="0" * 64),
            commit=False,
        )


def test_other_body_is_visual_while_body_and_touch_remain_self_only() -> None:
    world = EmbodimentWorldAuthority(authority_key=AUTHORITY_KEY)
    transducer = EmbodimentSensoryOutcomeAuthority(authority_key=AUTHORITY_KEY)
    before = transducer.transduce(
        world.observation_snapshot(), causal_owner=_owner(), commit=False
    )
    moved = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(4000, 4000, 0), 90_000)),
        70,
        port_id=SECOND_BODY_PORT_ID,
    )
    after = transducer.transduce(
        moved.after,
        causal_owner=_owner(),
        execution_receipt=moved,
        commit=False,
    )
    before_sight = _observed(before.causal_settlement, "sight")
    after_sight = _observed(after.causal_settlement, "sight")
    assert before_sight.structural_fingerprint != after_sight.structural_fingerprint
    assert any(
        item.substream_id == "W1-visible-body-w1-body-2"
        and ("physical-body-track", "w1-body-2") in item.coordinates
        for item in after_sight.substreams
    )
    assert (
        _observed(before.causal_settlement, "body").structural_fingerprint
        == _observed(after.causal_settlement, "body").structural_fingerprint
    )
    assert (
        _observed(before.causal_settlement, "touch").structural_fingerprint
        == _observed(after.causal_settlement, "touch").structural_fingerprint
    )
    for sense in ("sound", "smell", "taste"):
        assert _observed(after.causal_settlement, sense).state == "sensor_unavailable"
    assert after.causal_settlement.routing_chis == ()
