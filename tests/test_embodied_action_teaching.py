from __future__ import annotations

import base64
import json
from dataclasses import replace

import pytest

from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
    TEACHER_EVIDENCE_SCHEMA,
)
from dsf_ai_service.substrate.embodied_action_teaching import (
    EmbodiedActionTeachingAuthority,
)
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    EmbodimentSensoryOutcomeAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


WORLD_KEY = "guided-body-world-key"
TEACHING_KEY = "guided-body-teaching-key"


def _owner():
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )


def _authorities(*, capacity: int = 4):
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    sensory = EmbodimentSensoryOutcomeAuthority(authority_key=WORLD_KEY)
    cycle = CausalActionCycle(authority_key="guided-body-cycle-key")
    teaching = EmbodiedActionTeachingAuthority(
        authority_key=TEACHING_KEY,
        authorized_tutors=("joe",),
        world_authority=world,
        sensory_authority=sensory,
        action_cycle=cycle,
        demonstration_capacity=capacity,
    )
    return world, sensory, cycle, teaching


def _move_proof(world, sensory, *, y_mm: int, intent: int):
    owner = _owner()
    before = world.observation_snapshot()
    pre = sensory.transduce(before, causal_owner=owner, commit=False)
    payload = encode_command(
        MoveCommand(PoseMM(PositionMM(1000, y_mm, 0), 90_000))
    )
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=payload,
        causal_intent_receipt_sha256=f"{intent:064x}",
        expected_revision=before.revision,
    )
    assert execution.disposition == "applied"
    post = sensory.transduce(
        execution.after,
        causal_owner=owner,
        execution_receipt=execution,
        commit=False,
    )
    return payload, pre, execution, post


def _cycle_payload(cycle: CausalActionCycle) -> dict[str, object]:
    snapshot = cycle.encoded_snapshot()
    return json.loads(
        base64.b64decode(snapshot["payload_base64"], validate=True).decode("utf-8")
    )


def test_complete_guided_transition_is_the_only_teaching_authority() -> None:
    world, sensory, cycle, teaching = _authorities()
    payload, pre, execution, post = _move_proof(
        world, sensory, y_mm=1400, intent=1
    )
    learned = teaching.demonstrate(
        tutor_id="joe",
        nonce="guided-body-nonce-0001",
        command_payload=payload,
        pre_outcome=pre,
        execution_receipt=execution,
        post_outcome=post,
    )

    teaching.verify_demonstration_receipt(learned.demonstration)
    assert learned.demonstration.execution_receipt_sha256 == (
        execution.authority_receipt_sha256
    )
    assert learned.demonstration.pre_settlement_receipt_sha256 == (
        pre.causal_settlement.authority_receipt_sha256
    )
    assert learned.demonstration.post_settlement_receipt_sha256 == (
        post.causal_settlement.authority_receipt_sha256
    )
    with pytest.raises(ValueError, match="demonstration HMAC changed"):
        teaching.verify_demonstration_receipt(
            replace(
                learned.demonstration,
                post_structural_fingerprint="0" * 64,
            )
        )
    binding = _cycle_payload(cycle)["bindings"][0]
    assert binding["teacher_relation"]["schema"] == TEACHER_EVIDENCE_SCHEMA
    assert binding["teacher_relation"][
        "teaching_evidence_receipt_sha256"
    ] == learned.demonstration.authority_receipt_sha256

    repeated_world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    repeated = sensory.transduce(
        repeated_world.observation_snapshot(),
        causal_owner=_owner(),
        commit=False,
    )
    selection = cycle.select(repeated.causal_settlement)
    assert selection.status == "committed"
    assert selection.intent.action == ActionCommand.embodiment(PORT_ID, payload)


def test_tampered_or_incomplete_physical_evidence_teaches_nothing() -> None:
    world, sensory, cycle, teaching = _authorities()
    payload, pre, execution, post = _move_proof(
        world, sensory, y_mm=1400, intent=2
    )

    with pytest.raises(ValueError, match="not authorized"):
        teaching.demonstrate(
            tutor_id="television",
            nonce="guided-body-nonce-0002",
            command_payload=payload,
            pre_outcome=pre,
            execution_receipt=execution,
            post_outcome=post,
        )
    with pytest.raises(ValueError, match="command differs"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-nonce-0003",
            command_payload=encode_command(
                MoveCommand(PoseMM(PositionMM(1000, 1600, 0), 90_000))
            ),
            pre_outcome=pre,
            execution_receipt=execution,
            post_outcome=post,
        )
    with pytest.raises(ValueError, match="execution HMAC changed"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-nonce-0004",
            command_payload=payload,
            pre_outcome=pre,
            execution_receipt=replace(execution, command_sha256="0" * 64),
            post_outcome=post,
        )
    with pytest.raises(ValueError, match="different world evidence"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-nonce-0005",
            command_payload=payload,
            pre_outcome=pre,
            execution_receipt=execution,
            post_outcome=pre,
        )

    assert cycle.status()["bindings"] == 0
    assert teaching.status()["demonstrations"] == 0


def test_rejected_w1_execution_teaches_nothing() -> None:
    world, sensory, cycle, teaching = _authorities()
    owner = _owner()
    before = world.observation_snapshot()
    pre = sensory.transduce(before, causal_owner=owner, commit=False)
    payload = encode_command(
        MoveCommand(PoseMM(PositionMM(4900, 4900, 0), 0))
    )
    rejected = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=payload,
        causal_intent_receipt_sha256=f"{3:064x}",
        expected_revision=before.revision,
    )
    assert rejected.disposition == "rejected"

    with pytest.raises(ValueError, match="retained execution must be applied"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-nonce-0006",
            command_payload=payload,
            pre_outcome=pre,
            execution_receipt=rejected,
            post_outcome=pre,
        )
    assert cycle.status()["bindings"] == 0
    assert teaching.status()["demonstrations"] == 0


def test_nonce_replay_mismatch_and_capacity_fail_before_learning() -> None:
    world, sensory, cycle, teaching = _authorities(capacity=1)
    first = _move_proof(world, sensory, y_mm=1400, intent=4)
    learned = teaching.demonstrate(
        tutor_id="joe",
        nonce="guided-body-nonce-0007",
        command_payload=first[0],
        pre_outcome=first[1],
        execution_receipt=first[2],
        post_outcome=first[3],
    )
    assert teaching.demonstrate(
        tutor_id="joe",
        nonce="guided-body-nonce-0007",
        command_payload=first[0],
        pre_outcome=first[1],
        execution_receipt=first[2],
        post_outcome=first[3],
    ) == learned

    second = _move_proof(world, sensory, y_mm=1800, intent=5)
    with pytest.raises(ValueError, match="nonce was already used"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-nonce-0007",
            command_payload=second[0],
            pre_outcome=second[1],
            execution_receipt=second[2],
            post_outcome=second[3],
        )
    with pytest.raises(RuntimeError, match="capacity is full"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-nonce-0008",
            command_payload=second[0],
            pre_outcome=second[1],
            execution_receipt=second[2],
            post_outcome=second[3],
        )
    assert cycle.status()["bindings"] == 1
    assert teaching.status()["demonstrations"] == 1


def test_demonstration_and_cycle_persistence_retain_authenticated_link() -> None:
    world, sensory, cycle, teaching = _authorities()
    payload, pre, execution, post = _move_proof(
        world, sensory, y_mm=1400, intent=6
    )
    learned = teaching.demonstrate(
        tutor_id="joe",
        nonce="guided-body-nonce-0009",
        command_payload=payload,
        pre_outcome=pre,
        execution_receipt=execution,
        post_outcome=post,
    )
    teaching_snapshot = teaching.encoded_snapshot()
    cycle_snapshot = cycle.encoded_snapshot()

    restored_cycle = CausalActionCycle(authority_key="guided-body-cycle-key")
    restored_cycle.restore_encoded(cycle_snapshot)
    restored = EmbodiedActionTeachingAuthority(
        authority_key=TEACHING_KEY,
        authorized_tutors=("joe",),
        world_authority=world,
        sensory_authority=sensory,
        action_cycle=restored_cycle,
        demonstration_capacity=4,
    )
    restored.restore_encoded(teaching_snapshot)
    assert restored.encoded_snapshot() == teaching_snapshot
    binding = _cycle_payload(restored_cycle)["bindings"][0]
    assert binding["teacher_relation"][
        "teaching_evidence_receipt_sha256"
    ] == learned.demonstration.authority_receipt_sha256

    damaged = bytearray(teaching_snapshot)
    damaged[-2] = ord("0") if damaged[-2] != ord("0") else ord("1")
    with pytest.raises(ValueError):
        restored.restore_encoded(bytes(damaged))

    absent_cycle = CausalActionCycle(authority_key="guided-body-cycle-key")
    unlinked = EmbodiedActionTeachingAuthority(
        authority_key=TEACHING_KEY,
        authorized_tutors=("joe",),
        world_authority=world,
        sensory_authority=sensory,
        action_cycle=absent_cycle,
        demonstration_capacity=4,
    )
    with pytest.raises(ValueError, match="absent from the causal cycle"):
        unlinked.restore_encoded(teaching_snapshot)


def test_legacy_speech_teaching_remains_v1_and_byte_stable() -> None:
    _world, sensory, cycle, _teaching = _authorities()
    initial_world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    trigger = sensory.transduce(
        initial_world.observation_snapshot(),
        causal_owner=_owner(),
        commit=False,
    ).causal_settlement
    cycle.accept(trigger)
    cycle.teach(
        trigger_reference=trigger.event_id,
        action=ActionCommand.speech("hello"),
        source="joe",
        nonce="legacy-speech-nonce-0001",
    )
    before = cycle.encoded_snapshot()
    relation = _cycle_payload(cycle)["bindings"][0]["teacher_relation"]
    assert relation["schema"] == "guala.causal_action_cycle.teacher.v1"
    assert "teaching_evidence_receipt_sha256" not in relation

    restored = CausalActionCycle(authority_key="guided-body-cycle-key")
    restored.restore_encoded(before)
    assert restored.encoded_snapshot() == before
