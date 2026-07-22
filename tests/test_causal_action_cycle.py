from __future__ import annotations

import base64
import hashlib
import math
import os
import sys
from fractions import Fraction

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


def _built(assembly_id: str, *, frequency: int = 8):
    count = 96
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="cycle-test-camera",
        substream_id="fixation-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("fixation", "center"),),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(Fraction(index, 200) for index in range(count)),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 200)
            for index in range(count)
        ),
        phase_turns=tuple(Fraction(index // 12) for index in range(count)),
    )
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(count, 200),
        observed_substreams={PhysicalSense.SIGHT: (sight,)},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SIGHT
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )


def _settlement(
    assembly_id: str,
    *,
    frequency: int = 8,
    routing_chis: tuple[int, ...] = (),
):
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        _built(assembly_id, frequency=frequency),
        routing_chis=routing_chis,
        source_tags=(f"source:{assembly_id}",),
    )


def _teach(
    cycle: CausalActionCycle,
    trigger,
    action: ActionCommand,
    nonce: str,
):
    cycle.accept(trigger)
    relation = cycle.issue_teacher_relation(
        trigger_reference=trigger.event_id,
        action=action,
        source="joe",
        nonce=nonce,
    )
    return cycle.learn(
        trigger_reference=trigger.event_id,
        action=action,
        teacher_relation=relation,
    )


def _close(
    cycle: CausalActionCycle,
    trigger,
    outcome,
    *,
    executor_label: str,
    decision: str,
    feedback_nonce: str,
):
    selection = cycle.select(trigger)
    assert selection.status == "committed"
    execution = cycle.record_execution(
        intent_receipt_sha256=selection.intent.authority_receipt_sha256,
        executor_receipt_sha256=hashlib.sha256(
            executor_label.encode("utf-8")
        ).hexdigest(),
        disposition="executed",
    )
    observed = cycle.observe_outcome(
        execution_receipt_sha256=execution.authority_receipt_sha256,
        settlement=outcome,
    )
    feedback = cycle.apply_feedback(
        outcome_receipt_sha256=observed.authority_receipt_sha256,
        decision=decision,
        source="joe",
        nonce=feedback_nonce,
    )
    return selection.intent, execution, observed, feedback


def test_full_field_identity_ignores_chi_and_distinguishes_changed_field() -> None:
    trigger = _settlement("identity-a", routing_chis=(3,))
    same = _settlement("identity-b", routing_chis=(91,))
    changed = _settlement("identity-c", frequency=9, routing_chis=(3,))
    assert trigger.structural_fingerprint == same.structural_fingerprint
    assert trigger.routing_chis != same.routing_chis
    assert trigger.structural_fingerprint != changed.structural_fingerprint

    cycle = CausalActionCycle(authority_key="cycle-identity-key")
    action = ActionCommand.speech("I see it")
    _teach(cycle, trigger, action, "identity-teacher-nonce-0001")
    selected = cycle.select(same)
    assert selected.status == "committed"
    assert selected.intent.action == action
    unknown = cycle.select(changed)
    assert unknown.status == "unknown"
    assert unknown.intent is None
    assert unknown.stop_reason == "causal_action_unknown"


def test_embodiment_cycle_closes_and_restores_with_full_receipt_chain() -> None:
    trigger = _settlement("embodiment-trigger", routing_chis=(4, 12))
    repeated = _settlement("embodiment-repeat", routing_chis=(77,))
    outcome = _settlement("embodiment-outcome", frequency=11)
    cycle = CausalActionCycle(authority_key="cycle-embodiment-key")
    action = ActionCommand.embodiment(
        "body.motion.primary",
        b"\x01\x00\x7f\x22exact-port-command\x00",
    )
    binding = _teach(
        cycle,
        trigger,
        action,
        "embodiment-teacher-nonce-0001",
    )
    assert binding.status == "provisional"
    intent, execution, observed, feedback = _close(
        cycle,
        repeated,
        outcome,
        executor_label="embodiment-executor-1",
        decision="confirm",
        feedback_nonce="embodiment-feedback-nonce-0001",
    )
    assert intent.action == action
    assert execution.executor_receipt_sha256
    assert observed.outcome_structural_fingerprint == outcome.structural_fingerprint
    assert feedback.decision == "confirm"
    status = cycle.status()
    assert status["binding_statuses"]["confirmed"] == 1
    assert status["closures"] == 1
    assert status["intents"] == status["executions"] == status["outcomes"] == 0

    snapshot = cycle.encoded_snapshot()
    restored = CausalActionCycle(authority_key="cycle-embodiment-key")
    restored.restore_encoded(snapshot)
    assert restored.encoded_snapshot() == snapshot
    assert restored.status()["binding_statuses"]["confirmed"] == 1
    selected = restored.select(
        _settlement("embodiment-after-restart", routing_chis=(1, 99))
    )
    assert selected.status == "committed"
    assert selected.intent.action == action


def test_negative_feedback_revokes_and_ambiguous_relations_fail_closed() -> None:
    trigger = _settlement("revoke-trigger")
    cycle = CausalActionCycle(authority_key="cycle-revoke-key")
    _teach(
        cycle,
        trigger,
        ActionCommand.speech("stop"),
        "revoke-teacher-nonce-0001",
    )
    _close(
        cycle,
        _settlement("revoke-repeat", routing_chis=(2,)),
        _settlement("revoke-outcome", frequency=12),
        executor_label="revoke-executor",
        decision="revoke",
        feedback_nonce="revoke-feedback-nonce-0001",
    )
    revoked = cycle.select(_settlement("revoke-after", routing_chis=(88,)))
    assert revoked.status == "unknown"
    assert revoked.intent is None

    other = CausalActionCycle(authority_key="cycle-ambiguous-key")
    _teach(
        other,
        trigger,
        ActionCommand.speech("first"),
        "ambiguous-teacher-nonce-0001",
    )
    _teach(
        other,
        trigger,
        ActionCommand.embodiment("body.indicator", b"second"),
        "ambiguous-teacher-nonce-0002",
    )
    ambiguous = other.select(_settlement("ambiguous-repeat", routing_chis=(90,)))
    assert ambiguous.status == "ambiguous"
    assert ambiguous.intent is None
    assert other.status()["intents"] == 0


def test_closed_cycles_compact_and_continue_beyond_transaction_capacity() -> None:
    trigger = _settlement("compact-teach")
    cycle = CausalActionCycle(
        authority_key="cycle-compact-key",
        transaction_capacity=1,
        evidence_capacity=5,
    )
    _teach(
        cycle,
        trigger,
        ActionCommand.speech("again"),
        "compact-teacher-nonce-0001",
    )
    for index in range(4):
        _close(
            cycle,
            _settlement(f"compact-trigger-{index}", routing_chis=(index + 20,)),
            _settlement(f"compact-outcome-{index}", frequency=20 + index),
            executor_label=f"compact-executor-{index}",
            decision="confirm",
            feedback_nonce=f"compact-feedback-nonce-{index:04d}",
        )
        status = cycle.status()
        assert status["closures"] == 1
        assert status["intents"] == 0
        assert status["executions"] == 0
        assert status["outcomes"] == 0
        assert status["evidence"] <= 3

    snapshot = cycle.encoded_snapshot()
    restored = CausalActionCycle(
        authority_key="cycle-compact-key",
        transaction_capacity=1,
        evidence_capacity=5,
    )
    restored.restore_encoded(snapshot)
    assert restored.encoded_snapshot() == snapshot


def test_nonce_replay_and_rejected_execution_fail_without_capacity_leaks() -> None:
    trigger = _settlement("replay-teach")
    cycle = CausalActionCycle(
        authority_key="cycle-replay-key",
        transaction_capacity=1,
        evidence_capacity=5,
    )
    action = ActionCommand.speech("retry")
    _teach(cycle, trigger, action, "single-teacher-nonce-0001")
    with pytest.raises(ValueError, match="teacher nonce was already used"):
        cycle.issue_teacher_relation(
            trigger_reference=trigger.event_id,
            action=ActionCommand.speech("different"),
            source="joe",
            nonce="single-teacher-nonce-0001",
        )

    rejected = cycle.select(_settlement("rejected-trigger"))
    receipt = cycle.record_execution(
        intent_receipt_sha256=rejected.intent.authority_receipt_sha256,
        executor_receipt_sha256=hashlib.sha256(b"executor-rejected").hexdigest(),
        disposition="rejected",
    )
    assert receipt.disposition == "rejected"
    assert cycle.status()["intents"] == 0
    assert cycle.status()["executions"] == 0

    first_nonce = "single-feedback-nonce-0001"
    _close(
        cycle,
        _settlement("replay-trigger-one"),
        _settlement("replay-outcome-one", frequency=31),
        executor_label="replay-executor-one",
        decision="confirm",
        feedback_nonce=first_nonce,
    )
    selection = cycle.select(_settlement("replay-trigger-two"))
    execution = cycle.record_execution(
        intent_receipt_sha256=selection.intent.authority_receipt_sha256,
        executor_receipt_sha256=hashlib.sha256(b"replay-executor-two").hexdigest(),
        disposition="executed",
    )
    outcome = cycle.observe_outcome(
        execution_receipt_sha256=execution.authority_receipt_sha256,
        settlement=_settlement("replay-outcome-two", frequency=32),
    )
    with pytest.raises(ValueError, match="feedback nonce was already used"):
        cycle.apply_feedback(
            outcome_receipt_sha256=outcome.authority_receipt_sha256,
            decision="confirm",
            source="joe",
            nonce=first_nonce,
        )
    cycle.apply_feedback(
        outcome_receipt_sha256=outcome.authority_receipt_sha256,
        decision="confirm",
        source="joe",
        nonce="single-feedback-nonce-0002",
    )
    assert cycle.status()["intents"] == 0
    assert cycle.status()["executions"] == 0
    assert cycle.status()["outcomes"] == 0


def test_capacity_and_state_hmac_reject_without_partial_mutation() -> None:
    first = _settlement("bounded-first")
    second = _settlement("bounded-second", frequency=10)
    cycle = CausalActionCycle(
        authority_key="cycle-bounds-key",
        working_capacity=1,
        binding_capacity=1,
        max_command_bytes=8,
    )
    cycle.accept(first)
    cycle.accept(second)
    assert cycle.status()["working_perceptions"] == 1
    with pytest.raises(ValueError, match="working memory"):
        cycle.issue_teacher_relation(
            trigger_reference=first.event_id,
            action=ActionCommand.speech("gone"),
            source="joe",
            nonce="bounded-teacher-nonce-0001",
        )
    with pytest.raises(ValueError, match="byte boundary"):
        cycle.issue_teacher_relation(
            trigger_reference=second.event_id,
            action=ActionCommand.embodiment("body.test", b"123456789"),
            source="joe",
            nonce="bounded-teacher-nonce-0002",
        )
    _teach(
        cycle,
        second,
        ActionCommand.speech("bounded"),
        "bounded-teacher-nonce-0003",
    )
    with pytest.raises(RuntimeError, match="binding capacity"):
        _teach(
            cycle,
            second,
            ActionCommand.speech("other"),
            "bounded-teacher-nonce-0004",
        )

    snapshot = cycle.encoded_snapshot()
    damaged = dict(snapshot)
    payload = bytearray(base64.b64decode(damaged["payload_base64"]))
    payload[-2] ^= 1
    damaged["payload_base64"] = base64.b64encode(payload).decode("ascii")
    restored = CausalActionCycle(
        authority_key="cycle-bounds-key",
        working_capacity=1,
        binding_capacity=1,
        max_command_bytes=8,
    )
    with pytest.raises(ValueError, match="HMAC changed"):
        restored.restore_encoded(damaged)
    assert restored.status()["bindings"] == 0
