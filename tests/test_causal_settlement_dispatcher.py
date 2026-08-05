from __future__ import annotations

import base64
import hashlib
import math
from dataclasses import replace
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
from dsf_ai_service.substrate.causal_settlement_dispatcher import (
    CausalSettlementDispatcher,
    authenticate_executor_acknowledgement,
    authenticate_outcome_observation,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


def _action(value: str) -> ActionCommand:
    return ActionCommand.embodiment("test.body", value.encode("utf-8"))


DISPATCHER_KEY = "dispatcher-test-authority"
BODY_KEY = "dispatcher-test-body-authority"
OBSERVER_KEY = "dispatcher-test-outcome-observer-authority"


def _settlement(
    assembly_id: str,
    *,
    frequency: int = 8,
    routing_chis: tuple[int, ...] = (),
    source_tag: str | None = None,
    return_capability: bool = False,
):
    count = 96
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="dispatcher-test-camera",
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
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
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
    capabilities = []
    owner = None

    def retain_capability(value):
        if return_capability:
            capabilities.append(
                owner.active_transaction_capability(value)
            )

    owner = ExactCausalExperienceOwner(
        on_settlement=retain_capability,
        log_event=lambda *_args, **_kwargs: None,
    )
    settlement = owner.settle(
        built,
        routing_chis=routing_chis,
        source_tags=(source_tag or f"source:{assembly_id}",),
    )
    if not return_capability:
        return settlement
    assert len(capabilities) == 1
    return settlement, capabilities[0]


def _teach(cycle: CausalActionCycle, trigger, action: ActionCommand) -> None:
    cycle.accept(trigger)
    cycle.teach(
        trigger_reference=trigger.event_id,
        action=action,
        source="joe",
        nonce=f"teacher:{trigger.event_id}",
    )


class _Executor:
    def __init__(self, executor_id: str, key: str, disposition: str = "executed"):
        self.executor_id = executor_id
        self.key = key
        self.disposition = disposition
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return authenticate_executor_acknowledgement(
            request=request,
            executor_id=self.executor_id,
            authority_key=self.key,
            executor_action_receipt_sha256=hashlib.sha256(
                b"executor-result:" + request.authority_receipt_sha256.encode("ascii")
            ).hexdigest(),
            disposition=self.disposition,
        )


def _dispatcher(cycle, body):
    return CausalSettlementDispatcher(
        cycle=cycle,
        authority_key=DISPATCHER_KEY,
        embodiment_executor=body,
        embodiment_executor_id="body.primary",
        embodiment_executor_authority_key=BODY_KEY,
        outcome_observer_id="sensory.boundary.primary",
        outcome_observer_authority_key=OBSERVER_KEY,
    )


def _attestation(pending, outcome, *, nonce="observation-nonce-0001"):
    return authenticate_outcome_observation(
        observer_id="sensory.boundary.primary",
        authority_key=OBSERVER_KEY,
        execution_receipt_sha256=pending.execution_receipt_sha256,
        outcome_settlement_receipt_sha256=outcome.authority_receipt_sha256,
        observation_nonce=nonce,
    )


def test_expected_dispatch_correlates_exact_binding_and_action() -> None:
    trigger = _settlement("expected-dispatch-trigger", frequency=51)
    cycle = CausalActionCycle(authority_key="expected-dispatch-cycle")
    action = ActionCommand.embodiment("body.primary", b"step")
    _teach(cycle, trigger, action)
    evidence = cycle.verified_relation_evidence()[0]
    body = _Executor("body.primary", BODY_KEY)
    dispatcher = CausalSettlementDispatcher(
        cycle=cycle,
        authority_key=DISPATCHER_KEY,
        embodiment_executor=body,
        embodiment_executor_id="body.primary",
        embodiment_executor_authority_key=BODY_KEY,
        outcome_observer_id="sensory.boundary.primary",
        outcome_observer_authority_key=OBSERVER_KEY,
    )

    with pytest.raises(ValueError, match="expected action binding"):
        dispatcher.dispatch_expected(
            trigger,
            binding_id="0" * 64,
            action_receipt_sha256=action.authority_receipt_sha256,
        )
    assert dispatcher.status()["active"] is False
    pending = dispatcher.dispatch_expected(
        trigger,
        binding_id=evidence.binding_id,
        action_receipt_sha256=action.authority_receipt_sha256,
    )
    assert pending.binding_id == evidence.binding_id
    assert pending.action_receipt_sha256 == action.authority_receipt_sha256


@pytest.mark.parametrize("expected", (False, True))
def test_dispatch_threads_issued_causal_capability_without_deep_reverify(
        monkeypatch, expected) -> None:
    trigger, capability = _settlement(
        f"verified-dispatch-{expected}",
        frequency=53,
        return_capability=True,
    )
    cycle = CausalActionCycle(
        authority_key=f"verified-dispatch-cycle-{expected}"
    )
    action = ActionCommand.embodiment("body.primary", b"step")
    _teach(cycle, trigger, action)
    evidence = cycle.verified_relation_evidence()[0]
    dispatcher = _dispatcher(
        cycle,
        _Executor("body.primary", BODY_KEY),
    )

    def duplicate_verification(_value):
        raise AssertionError("issued causal authority was traversed twice")

    monkeypatch.setattr(
        type(trigger),
        "verify",
        duplicate_verification,
    )
    result = (
        dispatcher.dispatch_expected(
            trigger,
            binding_id=evidence.binding_id,
            action_receipt_sha256=action.authority_receipt_sha256,
            verified_transaction=capability,
        )
        if expected
        else dispatcher.dispatch(
            trigger,
            verified_transaction=capability,
        )
    )
    assert result.status == "pending"


def test_capacity_one_embodiment_dispatch_is_idempotent_and_closes_only_bound_outcome():
    taught = _settlement("dispatch-teach", routing_chis=(3,), source_tag="teacher")
    trigger = _settlement("dispatch-trigger", routing_chis=(99,), source_tag="microphone")
    unrelated = _settlement("dispatch-unrelated", frequency=12)
    outcome = _settlement("dispatch-outcome", frequency=15)
    assert taught.structural_fingerprint == trigger.structural_fingerprint
    cycle = CausalActionCycle(authority_key="dispatch-cycle-key")
    _teach(cycle, taught, _action("hello"))
    body = _Executor("body.primary", BODY_KEY)
    dispatcher = _dispatcher(cycle, body)

    pending = dispatcher.dispatch(trigger)
    assert pending.status == "pending"
    assert pending.phase == "outcome_observation"
    assert len(body.requests) == 1
    assert dispatcher.dispatch(trigger) == pending
    assert len(body.requests) == 1

    blocked = dispatcher.dispatch(unrelated)
    assert blocked.status == "pending"
    assert blocked.reason == "causal_action_capacity_one_busy"
    assert blocked.trigger_settlement_receipt_sha256 == trigger.authority_receipt_sha256
    assert cycle.status()["outcomes"] == 0

    trigger_attestation = _attestation(
        pending, trigger, nonce="trigger-observation-0001"
    )
    with pytest.raises(ValueError, match="cannot be its own outcome"):
        dispatcher.bind_outcome_observation(
            settlement=trigger, attestation=trigger_attestation
        )

    wrong = _attestation(pending, unrelated, nonce="wrong-observation-0001")
    with pytest.raises(ValueError, match="another causal chain"):
        dispatcher.bind_outcome_observation(settlement=outcome, attestation=wrong)
    assert cycle.status()["outcomes"] == 0

    attestation = _attestation(pending, outcome)
    binding = dispatcher.bind_outcome_observation(
        settlement=outcome, attestation=attestation
    )
    with pytest.raises(ValueError, match="only the live exact outcome binding"):
        dispatcher.close_bound_outcome(binding=binding, settlement=unrelated)
    completed = dispatcher.close_bound_outcome(binding=binding, settlement=outcome)
    assert completed.status == "completed"
    assert completed.phase == "closed"
    assert dispatcher.dispatch(trigger) == completed
    assert len(body.requests) == 1
    assert cycle.status()["intents"] == 0
    assert cycle.status()["executions"] == 0
    assert cycle.status()["outcomes"] == 0
    assert dispatcher.status()["capacity"] == 1
    assert dispatcher.status()["phase"] == "idle"


def test_unknown_ambiguous_and_authenticated_rejection_are_explicit():
    unknown_cycle = CausalActionCycle(authority_key="unknown-cycle-key")
    unknown_dispatcher = _dispatcher(
        unknown_cycle,
        _Executor("body.primary", BODY_KEY),
    )
    unknown = unknown_dispatcher.dispatch(_settlement("unknown"))
    assert (unknown.status, unknown.reason) == (
        "unknown",
        "causal_action_unknown",
    )

    trigger = _settlement("ambiguous-teach")
    ambiguous_cycle = CausalActionCycle(authority_key="ambiguous-cycle-key")
    _teach(ambiguous_cycle, trigger, _action("one"))
    ambiguous_cycle.teach(
        trigger_reference=trigger.event_id,
        action=_action("two"),
        source="joe",
        nonce="teacher-ambiguous-nonce-0002",
    )
    ambiguous_dispatcher = _dispatcher(
        ambiguous_cycle,
        _Executor("body.primary", BODY_KEY),
    )
    ambiguous = ambiguous_dispatcher.dispatch(
        _settlement("ambiguous-repeat", routing_chis=(44,))
    )
    assert (ambiguous.status, ambiguous.reason) == (
        "ambiguous",
        "causal_action_ambiguous",
    )
    assert ambiguous_cycle.status()["intents"] == 0

    rejected_cycle = CausalActionCycle(authority_key="rejected-cycle-key")
    _teach(rejected_cycle, trigger, _action("no"))
    rejecting = _Executor("body.primary", BODY_KEY, disposition="rejected")
    rejected_dispatcher = _dispatcher(rejected_cycle, rejecting)
    repeated = _settlement("rejected-repeat", routing_chis=(55,))
    rejected = rejected_dispatcher.dispatch(repeated)
    assert rejected.status == "rejected"
    assert rejected.reason == "authenticated_executor_rejected"
    assert rejected_dispatcher.dispatch(repeated) == rejected
    assert len(rejecting.requests) == 1
    assert rejected_cycle.status()["intents"] == 0


def test_executor_failure_stays_pending_without_implicit_retry_and_accepts_later_ack():
    trigger = _settlement("late-ack-teach")
    cycle = CausalActionCycle(authority_key="late-ack-cycle-key")
    _teach(cycle, trigger, _action("later"))
    requests = []

    def unavailable(request):
        requests.append(request)
        raise RuntimeError("executor unavailable")

    dispatcher = _dispatcher(cycle, unavailable)
    repeated = _settlement("late-ack-repeat", routing_chis=(7,))
    pending = dispatcher.dispatch(repeated)
    assert pending.status == "pending"
    assert pending.phase == "executor_acknowledgement"
    assert pending.reason == "executor_acknowledgement_pending"
    assert dispatcher.dispatch(repeated).status == "pending"
    assert len(requests) == 1

    acknowledgement = authenticate_executor_acknowledgement(
        request=requests[0],
        executor_id="body.primary",
        authority_key=BODY_KEY,
        executor_action_receipt_sha256=hashlib.sha256(b"late-ack").hexdigest(),
        disposition="executed",
    )
    awaiting_outcome = dispatcher.accept_executor_acknowledgement(acknowledgement)
    assert awaiting_outcome.phase == "outcome_observation"
    assert awaiting_outcome.execution_receipt_sha256


def test_embodiment_routes_only_to_embodiment_executor_and_rejects_wrong_authority():
    trigger = _settlement("body-dispatch-teach")
    cycle = CausalActionCycle(authority_key="body-dispatch-cycle-key")
    _teach(
        cycle,
        trigger,
        ActionCommand.embodiment("guala.embodiment.w1", b"exact-command"),
    )
    body = _Executor("body.primary", BODY_KEY)
    dispatcher = CausalSettlementDispatcher(
        cycle=cycle,
        authority_key=DISPATCHER_KEY,
        embodiment_executor=body,
        embodiment_executor_id="body.primary",
        embodiment_executor_authority_key=BODY_KEY,
        outcome_observer_id="sensory.boundary.primary",
        outcome_observer_authority_key=OBSERVER_KEY,
    )
    pending = dispatcher.dispatch(
        _settlement("body-dispatch-repeat", routing_chis=(90,))
    )
    assert pending.status == "pending"
    assert len(body.requests) == 1

    false_attestation = authenticate_outcome_observation(
        observer_id="sensory.boundary.primary",
        authority_key="wrong-observer-key",
        execution_receipt_sha256=pending.execution_receipt_sha256,
        outcome_settlement_receipt_sha256=_settlement(
            "false-outcome", frequency=19
        ).authority_receipt_sha256,
        observation_nonce="false-observation-nonce-0001",
    )
    with pytest.raises(ValueError, match="HMAC"):
        dispatcher.bind_outcome_observation(
            settlement=_settlement("false-outcome-copy", frequency=19),
            attestation=false_attestation,
        )


def test_authenticated_pending_state_restores_and_tampering_fails_closed():
    trigger = _settlement("restore-teach")
    repeated = _settlement("restore-repeat", routing_chis=(27,))
    cycle = CausalActionCycle(authority_key="restore-cycle-key")
    _teach(cycle, trigger, _action("persist"))
    body = _Executor("body.primary", BODY_KEY)
    dispatcher = _dispatcher(cycle, body)
    pending = dispatcher.dispatch(repeated)
    assert pending.execution_receipt_sha256

    cycle_snapshot = cycle.encoded_snapshot()
    dispatcher_snapshot = dispatcher.encoded_snapshot()
    restored_cycle = CausalActionCycle(authority_key="restore-cycle-key")
    restored_cycle.restore_encoded(cycle_snapshot)
    restored = _dispatcher(restored_cycle, body)
    restored.restore_encoded(dispatcher_snapshot)
    assert restored.encoded_snapshot() == dispatcher_snapshot
    assert restored.status()["active"] is True
    assert restored.status()["phase"] == "outcome_observation"

    tampered = dict(dispatcher_snapshot)
    payload = bytearray(base64.b64decode(tampered["payload_base64"]))
    payload[-2] ^= 1
    tampered["payload_base64"] = base64.b64encode(payload).decode("ascii")
    with pytest.raises(ValueError, match="HMAC"):
        restored.restore_encoded(tampered)


def test_authenticated_bound_outcome_restores_and_closes_exact_settlement():
    trigger = _settlement("bound-restore-teach")
    repeated = _settlement("bound-restore-repeat", routing_chis=(31,))
    outcome = _settlement("bound-restore-outcome", frequency=21)
    cycle = CausalActionCycle(authority_key="bound-restore-cycle-key")
    _teach(cycle, trigger, _action("bound"))
    body = _Executor("body.primary", BODY_KEY)
    dispatcher = _dispatcher(cycle, body)
    pending = dispatcher.dispatch(repeated)
    binding = dispatcher.bind_outcome_observation(
        settlement=outcome,
        attestation=_attestation(
            pending, outcome, nonce="bound-restore-observation-0001"
        ),
    )

    cycle_snapshot = cycle.encoded_snapshot()
    dispatcher_snapshot = dispatcher.encoded_snapshot()
    restored_cycle = CausalActionCycle(authority_key="bound-restore-cycle-key")
    restored_cycle.restore_encoded(cycle_snapshot)
    restored = _dispatcher(restored_cycle, body)
    restored.restore_encoded(dispatcher_snapshot)
    assert restored.status()["phase"] == "outcome_bound"
    completed = restored.close_bound_outcome(
        binding=binding, settlement=outcome
    )
    assert completed.status == "completed"
    assert restored.status()["active"] is False


def test_wrong_executor_acknowledgement_cannot_advance_live_intent():
    trigger = _settlement("wrong-ack-teach")
    cycle = CausalActionCycle(authority_key="wrong-ack-cycle-key")
    _teach(cycle, trigger, _action("authenticate"))
    requests = []

    def unavailable(request):
        requests.append(request)
        raise RuntimeError("deferred")

    dispatcher = _dispatcher(cycle, unavailable)
    pending = dispatcher.dispatch(_settlement("wrong-ack-repeat"))
    assert pending.phase == "executor_acknowledgement"
    forged = authenticate_executor_acknowledgement(
        request=requests[0],
        executor_id="body.primary",
        authority_key="forged-key",
        executor_action_receipt_sha256=hashlib.sha256(b"forged").hexdigest(),
        disposition="executed",
    )
    with pytest.raises(ValueError, match="HMAC"):
        dispatcher.accept_executor_acknowledgement(forged)
    assert dispatcher.status()["phase"] == "executor_acknowledgement"
    assert cycle.status()["executions"] == 0


def test_dispatch_rejects_non_settlement_and_tampered_settlement():
    cycle = CausalActionCycle(authority_key="typed-cycle-key")
    dispatcher = _dispatcher(
        cycle,
        _Executor("body.primary", BODY_KEY),
    )
    with pytest.raises(TypeError, match="exact causal settlement"):
        dispatcher.dispatch(object())
    valid = _settlement("tampered-settlement")
    tampered = replace(valid, routing_chis=(2, 1))
    with pytest.raises(Exception, match="routing chis"):
        dispatcher.dispatch(tampered)
