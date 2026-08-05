from __future__ import annotations

import base64
import hashlib
import inspect
import json
import math
import threading
from fractions import Fraction

import pytest

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
from dsf_ai_service.substrate.causal_deliberation import (
    CausalDeliberation,
    DEFAULT_ENCODED_STATE_BYTES,
    DEFAULT_MAX_WITNESS_BYTES,
    LEGACY_MAX_WITNESS_BYTES,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


def _action(value: str) -> ActionCommand:
    return ActionCommand.embodiment("test.body", value.encode("utf-8"))


def test_default_witness_capacity_is_derived_from_state_envelope():
    assert DEFAULT_MAX_WITNESS_BYTES == (
        3 * (DEFAULT_ENCODED_STATE_BYTES - 1_024) // 4
    )
    owner = CausalDeliberation(
        authority_key=b"causal-deliberation-derived-capacity-key"
    )
    assert (
        owner._capacities()["max_witness_bytes"]
        == DEFAULT_MAX_WITNESS_BYTES
    )


def test_legacy_witness_boundary_cold_migrates_to_derived_capacity():
    key = b"causal-deliberation-legacy-capacity-migration-key"
    legacy = CausalDeliberation(
        authority_key=key,
        max_witness_bytes=LEGACY_MAX_WITNESS_BYTES,
    )
    restored = CausalDeliberation(authority_key=key)

    restored.restore_encoded(legacy.encoded_snapshot())

    assert (
        restored._capacities()["max_witness_bytes"]
        == DEFAULT_MAX_WITNESS_BYTES
    )


def _settlement(
    name: str,
    *,
    frequency: int = 8,
    coordinate: str = "center",
    routing_chis: tuple[int, ...] = (),
    source: str | None = None,
):
    count = 96
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="deliberation-camera",
        substream_id="fixation-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("fixation", coordinate),),
        physical_quantity="light-intensity",
        physical_unit="normalized-intensity",
        source_times=tuple(Fraction(index, 200) for index in range(count)),
        normalized_signal=tuple(
            math.sin(2 * math.pi * frequency * index / 200)
            for index in range(count)
        ),
        phase_turns=tuple(Fraction(index // 12) for index in range(count)),
    )
    built = build_six_sense_full_field(
        assembly_id=name,
        source_time_start=Fraction(0),
        source_time_end=Fraction(count, 200),
        observed_substreams={PhysicalSense.SIGHT: (sight,)}, occurrences=joint_occurrences_for({PhysicalSense.SIGHT: (sight,)}),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SIGHT
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=routing_chis,
        source_tags=(source or f"source:{name}",),
    )


def _teach(cycle, trigger, action, nonce):
    cycle.accept(trigger)
    return cycle.teach(
        trigger_reference=trigger.event_id,
        action=action,
        source="joe",
        nonce=nonce,
    )


def _close(cycle, trigger, outcome, label):
    selected = cycle.select(trigger)
    assert selected.status == "committed"
    execution = cycle.record_execution(
        intent_receipt_sha256=selected.intent.authority_receipt_sha256,
        executor_receipt_sha256=hashlib.sha256(label.encode()).hexdigest(),
        disposition="executed",
    )
    observed = cycle.observe_outcome(
        execution_receipt_sha256=execution.authority_receipt_sha256,
        settlement=outcome,
    )
    cycle.close_observed(
        outcome_receipt_sha256=observed.authority_receipt_sha256
    )


def _learn_transition(cycle, trigger, action, outcome, nonce):
    _teach(cycle, trigger, action, nonce)
    _close(cycle, trigger, outcome, f"executor:{nonce}")


def test_full_field_coordinate_changes_identity_but_chi_and_source_do_not() -> None:
    left = _settlement(
        "field-left-a", coordinate="left", routing_chis=(3,), source="camera:a"
    )
    same = _settlement(
        "field-left-b", coordinate="left", routing_chis=(91,), source="camera:b"
    )
    right = _settlement(
        "field-right", coordinate="right", routing_chis=(3,), source="camera:a"
    )
    assert left.structural_fingerprint == same.structural_fingerprint
    assert left.authority_receipt_sha256 != same.authority_receipt_sha256
    assert left.structural_fingerprint != right.structural_fingerprint

    cycle = CausalActionCycle(authority_key="field-cycle")
    action = ActionCommand.embodiment("body.motion", b"left")
    _learn_transition(
        cycle,
        left,
        action,
        _settlement("field-outcome", frequency=9),
        "field-teacher-nonce-0001",
    )
    core = CausalDeliberation(authority_key="field-deliberation")
    turn = core.start(same, action_cycle=cycle)
    assert turn.status == "action"
    assert turn.action == action
    changed = CausalDeliberation(authority_key="field-changed")
    assert changed.start(right, action_cycle=cycle).stop_reason == "action_unknown"


def test_action_and_outcome_cardinalities_fail_closed() -> None:
    field = _settlement("cardinality-field")
    no_actions = CausalDeliberation(authority_key="no-action-core")
    empty_cycle = CausalActionCycle(authority_key="no-action-cycle")
    assert (
        no_actions.start(field, action_cycle=empty_cycle).stop_reason
        == "action_unknown"
    )

    no_outcome_cycle = CausalActionCycle(authority_key="no-outcome-cycle")
    _teach(
        no_outcome_cycle,
        field,
        _action("look"),
        "no-outcome-teacher-0001",
    )
    no_outcome = CausalDeliberation(authority_key="no-outcome-core")
    assert (
        no_outcome.start(field, action_cycle=no_outcome_cycle).stop_reason
        == "outcome_unknown"
    )

    two_action_cycle = CausalActionCycle(authority_key="two-action-cycle")
    _teach(
        two_action_cycle,
        field,
        _action("first"),
        "two-action-teacher-0001",
    )
    _teach(
        two_action_cycle,
        field,
        ActionCommand.embodiment("body.motion", b"second"),
        "two-action-teacher-0002",
    )
    two_actions = CausalDeliberation(authority_key="two-action-core")
    assert (
        two_actions.start(field, action_cycle=two_action_cycle).stop_reason
        == "action_ambiguous"
    )


def test_exact_outcome_advances_a_multi_step_chain() -> None:
    first = _settlement("chain-first", frequency=8)
    second = _settlement("chain-second", frequency=9)
    third = _settlement("chain-third", frequency=10)
    cycle = CausalActionCycle(authority_key="chain-cycle")
    first_action = ActionCommand.embodiment("body.motion", b"one")
    second_action = _action("two")
    _learn_transition(
        cycle,
        first,
        first_action,
        second,
        "chain-teacher-nonce-0001",
    )
    _learn_transition(
        cycle,
        second,
        second_action,
        third,
        "chain-teacher-nonce-0002",
    )
    core = CausalDeliberation(authority_key="chain-core")
    one = core.start(first, action_cycle=cycle)
    assert one.status == "action"
    assert one.action == first_action
    assert one.expected_outcome.structural_fingerprint == (
        second.structural_fingerprint
    )
    two = core.advance(second, action_cycle=cycle)
    assert two.status == "action"
    assert two.action == second_action
    assert two.depth == 2
    stopped = core.advance(third, action_cycle=cycle)
    assert stopped.status == "stopped"
    assert stopped.stop_reason == "action_unknown"


def test_transition_outcome_closes_action_while_stable_state_selects_next() -> None:
    first = _settlement("separated-first", frequency=31)
    transition = _settlement("separated-transition", frequency=32)
    stable = _settlement("separated-stable", frequency=33)
    final = _settlement("separated-final", frequency=34)
    cycle = CausalActionCycle(authority_key="separated-cycle")
    first_action = ActionCommand.embodiment("body.motion", b"one")
    second_action = ActionCommand.embodiment("body.motion", b"two")
    _learn_transition(
        cycle,
        first,
        first_action,
        transition,
        "separated-teacher-0001",
    )
    _learn_transition(
        cycle,
        stable,
        second_action,
        final,
        "separated-teacher-0002",
    )
    core = CausalDeliberation(authority_key="separated-core")

    assert core.start(first, action_cycle=cycle).action == first_action
    continued = core.advance(
        stable,
        action_outcome=transition,
        action_cycle=cycle,
    )

    assert continued.status == "action"
    assert continued.action == second_action
    assert continued.expected_outcome.structural_fingerprint == (
        final.structural_fingerprint
    )


def test_verified_mismatch_becomes_one_counterexample_and_ambiguous() -> None:
    trigger = _settlement("mismatch-trigger", frequency=8)
    expected = _settlement("mismatch-expected", frequency=9)
    counterexample = _settlement("mismatch-counterexample", frequency=10)
    cycle = CausalActionCycle(authority_key="mismatch-cycle")
    action = ActionCommand.embodiment("body.motion", b"step")
    _learn_transition(
        cycle,
        trigger,
        action,
        expected,
        "mismatch-teacher-nonce-0001",
    )
    core = CausalDeliberation(authority_key="mismatch-core")
    assert core.start(trigger, action_cycle=cycle).status == "action"
    _close(cycle, trigger, counterexample, "mismatch-executor-2")
    stopped = core.advance(counterexample, action_cycle=cycle)
    assert stopped.stop_reason == "outcome_mismatch"
    assert core.status()["retained_outcomes"] == 2
    assert core.status()["ambiguous_relations"] == 1

    changed_world = _settlement("mismatch-trigger-new", frequency=8)
    again = core.start(changed_world, action_cycle=cycle)
    assert again.stop_reason == "outcome_ambiguous"

    third = _settlement("mismatch-third", frequency=11)
    _close(cycle, trigger, third, "mismatch-executor-3")
    assert core.start(trigger, action_cycle=cycle).stop_reason == "outcome_ambiguous"
    assert core.status()["retained_outcomes"] == 2


def test_unverified_outcome_cannot_advance_or_become_evidence() -> None:
    trigger = _settlement("unverified-trigger", frequency=8)
    expected = _settlement("unverified-expected", frequency=9)
    unverified = _settlement("unverified-other", frequency=10)
    cycle = CausalActionCycle(authority_key="unverified-cycle")
    _learn_transition(
        cycle,
        trigger,
        _action("go"),
        expected,
        "unverified-teacher-0001",
    )
    core = CausalDeliberation(authority_key="unverified-core")
    assert core.start(trigger, action_cycle=cycle).status == "action"
    stopped = core.advance(unverified, action_cycle=cycle)
    assert stopped.stop_reason == "outcome_unverified"
    assert core.status()["retained_outcomes"] == 1


def test_recurrence_and_terminal_survive_restore_until_authority_changes() -> None:
    first = _settlement("recurrence-first", frequency=8)
    second = _settlement("recurrence-second", frequency=9)
    repeated_first = _settlement(
        "recurrence-first-again", frequency=8, routing_chis=(99,)
    )
    cycle = CausalActionCycle(authority_key="recurrence-cycle")
    _learn_transition(
        cycle,
        first,
        _action("one"),
        second,
        "recurrence-teacher-0001",
    )
    _learn_transition(
        cycle,
        second,
        _action("two"),
        repeated_first,
        "recurrence-teacher-0002",
    )
    core = CausalDeliberation(authority_key="recurrence-core")
    assert core.start(first, action_cycle=cycle).status == "action"
    assert core.advance(second, action_cycle=cycle).status == "action"
    stopped = core.advance(repeated_first, action_cycle=cycle)
    assert stopped.stop_reason == "recurrence"

    snapshot = core.encoded_snapshot()
    restored = CausalDeliberation(authority_key="recurrence-core")
    restored.restore_encoded(snapshot)
    blocked = restored.start(
        _settlement("recurrence-same-world", frequency=8, routing_chis=(1,)),
        action_cycle=cycle,
    )
    assert blocked.stop_reason == "recurrence"
    different = restored.start(
        _settlement("recurrence-different-world", frequency=12),
        action_cycle=cycle,
    )
    assert different.stop_reason == "action_unknown"


def test_terminal_reopens_when_verified_relation_state_changes() -> None:
    field = _settlement("reopen-field", frequency=8)
    outcome = _settlement("reopen-outcome", frequency=9)
    cycle = CausalActionCycle(authority_key="reopen-cycle")
    core = CausalDeliberation(authority_key="reopen-core")
    assert core.start(field, action_cycle=cycle).stop_reason == "action_unknown"
    action = _action("learned")
    _learn_transition(
        cycle,
        field,
        action,
        outcome,
        "reopen-teacher-nonce-0001",
    )
    reopened = core.start(
        _settlement("reopen-same-field", frequency=8), action_cycle=cycle
    )
    assert reopened.status == "action"
    assert reopened.action == action


def test_capacity_one_episode_is_concurrency_safe_and_persistent() -> None:
    trigger = _settlement("concurrent-trigger", frequency=8)
    outcome = _settlement("concurrent-outcome", frequency=9)
    cycle = CausalActionCycle(authority_key="concurrent-cycle")
    _learn_transition(
        cycle,
        trigger,
        _action("once"),
        outcome,
        "concurrent-teacher-0001",
    )
    core = CausalDeliberation(authority_key="concurrent-core")
    barrier = threading.Barrier(6)
    turns = []
    turn_lock = threading.Lock()

    def worker():
        barrier.wait()
        turn = core.start(trigger, action_cycle=cycle)
        with turn_lock:
            turns.append(turn)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(item.status == "action" for item in turns) == 1
    assert sum(item.stop_reason == "outcome_unverified" for item in turns) == 5

    snapshot = core.encoded_snapshot()
    restored = CausalDeliberation(authority_key="concurrent-core")
    restored.restore_encoded(snapshot)
    after_restart = restored.start(trigger, action_cycle=cycle)
    assert after_restart.status == "stopped"
    assert after_restart.stop_reason == "outcome_unverified"


def test_relation_and_outcome_storage_plateaus_at_hard_bounds() -> None:
    cycle = CausalActionCycle(
        authority_key="plateau-cycle", binding_capacity=8
    )
    fields = [_settlement(f"plateau-{index}", frequency=20 + index) for index in range(5)]
    for index, field in enumerate(fields):
        _teach(
            cycle,
            field,
            _action(f"action-{index}"),
            f"plateau-teacher-{index:04d}",
        )
    core = CausalDeliberation(
        authority_key="plateau-core", relation_capacity=3
    )
    core.start(fields[-1], action_cycle=cycle)
    assert core.status()["relations"] == 3
    first_size = core.status()["encoded_state_bytes"]

    sixth = _settlement("plateau-sixth", frequency=30)
    _teach(
        cycle,
        sixth,
        _action("action-sixth"),
        "plateau-teacher-9999",
    )
    core.start(sixth, action_cycle=cycle)
    assert core.status()["relations"] == 3
    assert core.status()["encoded_state_bytes"] < first_size * 2


def test_hmac_tamper_and_explicit_field_tamper_are_rejected() -> None:
    trigger = _settlement("tamper-trigger", frequency=8)
    outcome = _settlement("tamper-outcome", frequency=9)
    cycle = CausalActionCycle(authority_key="tamper-cycle")
    _learn_transition(
        cycle,
        trigger,
        _action("tamper"),
        outcome,
        "tamper-teacher-0001",
    )
    core = CausalDeliberation(authority_key="tamper-core")
    core.start(trigger, action_cycle=cycle)
    snapshot = core.encoded_snapshot()
    bad_hmac = dict(snapshot)
    bad_hmac["state_hmac_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="authority changed"):
        CausalDeliberation(authority_key="tamper-core").restore_encoded(bad_hmac)

    payload = json.loads(base64.b64decode(snapshot["payload_base64"]))
    relation = payload["relations"][0]
    decoded_witness = json.loads(
        base64.b64decode(relation["trigger"]["settlement_payload_base64"])
    )
    fields = decoded_witness["interpretations"][0]["substreams"][0][
        "field_tuples"
    ][0]["fields"]
    fields[0][1] = "999/1"
    forged_payload = json.dumps(
        decoded_witness,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    relation["trigger"]["settlement_payload_base64"] = base64.b64encode(
        forged_payload
    ).decode()
    relation["trigger"]["settlement_receipt_sha256"] = hashlib.sha256(
        forged_payload
    ).hexdigest()
    state_payload = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    forged = {
        "payload_base64": base64.b64encode(state_payload).decode(),
        "schema": snapshot["schema"],
        "state_hmac_sha256": __import__("hmac").new(
            b"tamper-core",
            b"guala-causal-deliberation-state-v1\0" + state_payload,
            hashlib.sha256,
        ).hexdigest(),
    }
    with pytest.raises(ValueError, match="explicit DSF field changed"):
        CausalDeliberation(authority_key="tamper-core").restore_encoded(forged)


def test_forbidden_mechanisms_are_absent() -> None:
    import dsf_ai_service.substrate.causal_deliberation as module

    source = inspect.getsource(module).lower()
    forbidden_imports = (
        "import random",
        "import numpy",
        "import torch",
        "import sklearn",
        "from dsf_ai_service.substrate.needs",
        "from dsf_ai_service.substrate.atlas",
    )
    assert all(item not in source for item in forbidden_imports)
    assert "weighted score" not in source
    assert "top_k" not in source
    assert "sleep(" not in source


def test_filtered_evidence_turn_identity_resume_and_authenticated_stop() -> None:
    trigger = _settlement("filtered-trigger", frequency=41)
    outcome = _settlement("filtered-outcome", frequency=42)
    cycle = CausalActionCycle(authority_key="filtered-cycle")
    cycle.accept(trigger)
    binding = cycle.teach(
        trigger_reference=trigger.event_id,
        action=ActionCommand.embodiment("guala.embodiment.w1", b"move"),
        source="joe",
        nonce="filtered-v2-teacher-0001",
        teaching_evidence_receipt_sha256="a" * 64,
    )
    _close(cycle, trigger, outcome, "filtered-executor")
    admitted = tuple(
        item for item in cycle.verified_relation_evidence()
        if item.binding_id == binding.binding_id
    )
    core = CausalDeliberation(authority_key="filtered-core")
    turn = core.start(trigger, admitted_evidence=admitted)
    assert turn.status == "action"
    assert turn.binding_id == binding.binding_id
    assert turn.action_receipt_sha256 == (
        turn.action.authority_receipt_sha256
    )
    assert core.current_turn() == turn
    active = core.active_episode_record()
    assert active["current"]["structural_fingerprint"] == (
        trigger.structural_fingerprint
    )
    stopped = core.terminate_active(
        reason="dispatcher_rejected",
        evidence_receipt_sha256="b" * 64,
    )
    assert stopped.stop_reason == "dispatcher_rejected"
    restored = CausalDeliberation(authority_key="filtered-core")
    restored.restore_encoded(core.encoded_snapshot())
    assert restored.status()["terminal_reason"] == "dispatcher_rejected"
