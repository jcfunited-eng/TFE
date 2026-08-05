from __future__ import annotations

import ast
import base64
import inspect
import json
from dataclasses import dataclass, replace

import pytest

from dsf_ai_service.substrate.causal_action_cycle import (
    ActionCommand,
    CausalActionCycle,
    TEACHER_EVIDENCE_SCHEMA,
)
from dsf_ai_service.substrate.embodied_action_teaching import (
    EMBODIED_ACTION_TEACHING_CONSUMER_ID,
    EmbodiedActionTeachingAuthority,
)
import dsf_ai_service.substrate.embodied_action_teaching as teaching_module
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceConsumerCapability,
    SettledExperienceConsumerView,
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_acoustic_emitter import (
    W1AcousticEmitterAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1PhysicalEvidenceMount,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)


WORLD_KEY = "guided-body-world-key"
TEACHING_KEY = "guided-body-teaching-key"
PHYSICAL_KEY = "guided-body-physical-evidence-key-0001"
ACOUSTIC_KEY = "guided-body-acoustic-emitter-key-0001"
CONTINUITY_KEY = "guided-body-continuity-owner-key-0001"
CUSTODY_KEY = "guided-body-settled-custody-key-0001"


@dataclass(frozen=True, slots=True)
class _Occurrence:
    authority: SettledExperienceCustodyAuthority
    capability: SettledExperienceConsumerCapability
    view: SettledExperienceConsumerView


def _owner() -> ExactCausalExperienceOwner:
    return ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )


def _physical_authority(
    world: EmbodimentWorldAuthority,
) -> W1AudiovisualPhysicalEvidenceAuthority:
    return W1AudiovisualPhysicalEvidenceAuthority(
        authority_key=PHYSICAL_KEY,
        world_authority=world,
        causal_owner=_owner(),
        acoustic_emitter=W1AcousticEmitterAuthority(
            authority_key=ACOUSTIC_KEY,
            world_authority=world,
        ),
        binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
        anonymous_av_continuity_owner=(
            W1AnonymousAudiovisualContinuityOwner(
                authority_key=CONTINUITY_KEY,
                physical_authority_key=PHYSICAL_KEY,
            )
        ),
    )


def _custody(
    mount: W1PhysicalEvidenceMount,
    *,
    execution=None,
    observation=None,
    extra_consumer: str | None = None,
) -> _Occurrence:
    profile = SettledExperienceCustodyProfile.create(
        profile_id=EMBODIED_ACTION_TEACHING_CONSUMER_ID,
        max_children=2 if extra_consumer is not None else 1,
        max_snapshot_bytes=32 * 1024 * 1024,
    )
    authority = SettledExperienceCustodyAuthority(
        authority_key=CUSTODY_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        profile=profile,
    )
    authority.admit(
        mount,
        execution,
        world_observation=observation,
    )
    if extra_consumer is not None:
        authority.issue_child(extra_consumer)
    capability = authority.issue_child(
        EMBODIED_ACTION_TEACHING_CONSUMER_ID
    )
    return _Occurrence(
        authority=authority,
        capability=capability,
        view=authority.open_child(capability),
    )


def _authorities(*, capacity: int = 4):
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    physical = _physical_authority(world)
    cycle = CausalActionCycle(authority_key="guided-body-cycle-key")
    teaching = EmbodiedActionTeachingAuthority(
        authority_key=TEACHING_KEY,
        authorized_tutors=("joe",),
        world_authority=world,
        action_cycle=cycle,
        demonstration_capacity=capacity,
    )
    return world, physical, cycle, teaching


def _move_proof(world, physical, *, y_mm: int, intent: int):
    before = world.observation_snapshot()
    pre_mount = physical.mount_authenticated_observation(
        before,
        commit=False,
    )
    pre = _custody(pre_mount, observation=before)
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
    post_mount = physical.mount_authenticated_action_outcome(
        execution,
        commit=False,
    )
    post = _custody(post_mount, execution=execution)
    return payload, pre, execution, post


def _demonstrate(
    teaching: EmbodiedActionTeachingAuthority,
    *,
    tutor_id: str,
    nonce: str,
    command_payload: bytes,
    pre: _Occurrence,
    post: _Occurrence,
):
    return teaching.demonstrate(
        tutor_id=tutor_id,
        nonce=nonce,
        command_payload=command_payload,
        pre_custody_authority=pre.authority,
        pre_custody_capability=pre.capability,
        post_custody_authority=post.authority,
        post_custody_capability=post.capability,
    )


def _cycle_payload(cycle: CausalActionCycle) -> dict[str, object]:
    snapshot = cycle.encoded_snapshot()
    return json.loads(
        base64.b64decode(
            snapshot["payload_base64"],
            validate=True,
        ).decode("utf-8")
    )


def test_complete_guided_transition_is_the_only_teaching_authority() -> None:
    world, physical, cycle, teaching = _authorities()
    payload, pre, execution, post = _move_proof(
        world, physical, y_mm=1400, intent=1
    )
    learned = _demonstrate(
        teaching,
        tutor_id="joe",
        nonce="guided-body-nonce-0001",
        command_payload=payload,
        pre=pre,
        post=post,
    )

    teaching.verify_demonstration_receipt(learned.demonstration)
    assert learned.demonstration.execution_receipt_sha256 == (
        execution.authority_receipt_sha256
    )
    assert learned.demonstration.pre_settlement_receipt_sha256 == (
        pre.view.causal_settlement.authority_receipt_sha256
    )
    assert learned.demonstration.post_settlement_receipt_sha256 == (
        post.view.causal_settlement.authority_receipt_sha256
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
    selection = cycle.select(pre.view.causal_settlement)
    assert selection.status == "committed"
    assert selection.intent.action == ActionCommand.embodiment(
        PORT_ID,
        payload,
    )


def test_downstream_teaching_has_no_producer_authority() -> None:
    tree = ast.parse(inspect.getsource(teaching_module))
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    }
    assert called_attributes.isdisjoint({
        "admit",
        "mount_action_outcome",
        "mount_authenticated_action_outcome",
        "mount_authenticated_observation",
        "mount_current_observation",
        "settle",
        "transduce",
    })
    constructor = inspect.signature(
        EmbodiedActionTeachingAuthority
    ).parameters
    demonstrate = inspect.signature(
        EmbodiedActionTeachingAuthority.demonstrate
    ).parameters
    assert "sensory_authority" not in constructor
    assert {
        "pre_outcome",
        "post_outcome",
        "execution_receipt",
    }.isdisjoint(demonstrate)


def test_wrong_purpose_or_crossed_custody_teaches_nothing() -> None:
    world, physical, cycle, teaching = _authorities()
    payload, pre, _execution, post = _move_proof(
        world, physical, y_mm=1400, intent=2
    )
    prediction_capability = pre.authority.issue_child(
        "full-field-prediction"
    ) if len(pre.authority.children) == 0 else None
    if prediction_capability is None:
        pre_mount = physical.mount_authenticated_observation(
            pre.view.world_observation,
            commit=False,
        )
        alternate = _custody(
            pre_mount,
            observation=pre.view.world_observation,
            extra_consumer="full-field-prediction",
        )
        prediction_capability = alternate.authority.children[0]
        wrong_authority = alternate.authority
    else:
        wrong_authority = pre.authority
    with pytest.raises(ValueError, match="another consumer"):
        teaching.demonstrate(
            tutor_id="joe",
            nonce="guided-body-wrong-purpose-0002",
            command_payload=payload,
            pre_custody_authority=wrong_authority,
            pre_custody_capability=prediction_capability,
            post_custody_authority=post.authority,
            post_custody_capability=post.capability,
        )
    with pytest.raises(ValueError, match="not an applied occurrence"):
        _demonstrate(
            teaching,
            tutor_id="joe",
            nonce="guided-body-crossed-proof-0002",
            command_payload=payload,
            pre=pre,
            post=pre,
        )
    assert cycle.status()["bindings"] == 0
    assert teaching.status()["demonstrations"] == 0


def test_unauthorized_tutor_or_different_command_teaches_nothing() -> None:
    world, physical, cycle, teaching = _authorities()
    payload, pre, _execution, post = _move_proof(
        world, physical, y_mm=1400, intent=3
    )
    with pytest.raises(ValueError, match="not authorized"):
        _demonstrate(
            teaching,
            tutor_id="television",
            nonce="guided-body-unauthorized-0003",
            command_payload=payload,
            pre=pre,
            post=post,
        )
    with pytest.raises(ValueError, match="command differs"):
        _demonstrate(
            teaching,
            tutor_id="joe",
            nonce="guided-body-wrong-command-0003",
            command_payload=encode_command(
                MoveCommand(PoseMM(
                    PositionMM(1000, 1600, 0),
                    90_000,
                ))
            ),
            pre=pre,
            post=post,
        )
    assert cycle.status()["bindings"] == 0
    assert teaching.status()["demonstrations"] == 0


def test_other_body_execution_is_never_taught_as_self_action() -> None:
    world, physical, cycle, teaching = _authorities()
    before = world.observation_snapshot()
    pre = _custody(
        physical.mount_authenticated_observation(before, commit=False),
        observation=before,
    )
    payload = encode_command(
        MoveCommand(PoseMM(PositionMM(4000, 4000, 0), 90_000))
    )
    execution = world.execute_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=payload,
        causal_intent_receipt_sha256=f"{301:064x}",
        expected_revision=before.revision,
    )
    post = _custody(
        physical.mount_authenticated_action_outcome(
            execution,
            commit=False,
        ),
        execution=execution,
    )
    with pytest.raises(ValueError, match="self-body"):
        _demonstrate(
            teaching,
            tutor_id="joe",
            nonce="guided-body-other-0301",
            command_payload=payload,
            pre=pre,
            post=post,
        )
    assert cycle.status()["bindings"] == 0


def test_nonce_replay_mismatch_and_capacity_fail_before_learning() -> None:
    world, physical, cycle, teaching = _authorities(capacity=1)
    first = _move_proof(world, physical, y_mm=1400, intent=4)
    learned = _demonstrate(
        teaching,
        tutor_id="joe",
        nonce="guided-body-nonce-0007",
        command_payload=first[0],
        pre=first[1],
        post=first[3],
    )
    assert _demonstrate(
        teaching,
        tutor_id="joe",
        nonce="guided-body-nonce-0007",
        command_payload=first[0],
        pre=first[1],
        post=first[3],
    ) == learned

    second = _move_proof(world, physical, y_mm=1800, intent=5)
    with pytest.raises(ValueError, match="nonce was already used"):
        _demonstrate(
            teaching,
            tutor_id="joe",
            nonce="guided-body-nonce-0007",
            command_payload=second[0],
            pre=second[1],
            post=second[3],
        )
    with pytest.raises(RuntimeError, match="capacity is full"):
        _demonstrate(
            teaching,
            tutor_id="joe",
            nonce="guided-body-nonce-0008",
            command_payload=second[0],
            pre=second[1],
            post=second[3],
        )
    assert cycle.status()["bindings"] == 1
    assert teaching.status()["demonstrations"] == 1


def test_cycle_capacity_failure_restores_pre_demonstration_state() -> None:
    world, physical, _cycle, _teaching = _authorities()
    cycle = CausalActionCycle(
        authority_key="guided-body-cycle-key",
        binding_capacity=1,
    )
    teaching = EmbodiedActionTeachingAuthority(
        authority_key=TEACHING_KEY,
        authorized_tutors=("joe",),
        world_authority=world,
        action_cycle=cycle,
        demonstration_capacity=4,
    )
    proof = _move_proof(world, physical, y_mm=1400, intent=402)
    initial = proof[1].view.causal_settlement
    cycle.accept(initial)
    cycle.teach(
        trigger_reference=initial.event_id,
        action=ActionCommand.embodiment("test.body", b"occupied"),
        source="joe",
        nonce="guided-body-existing-binding-0001",
    )
    before_status = cycle.status()
    before_encoded = cycle.encoded_snapshot()
    with pytest.raises(RuntimeError, match="binding capacity is full"):
        _demonstrate(
            teaching,
            tutor_id="joe",
            nonce="guided-body-capacity-rollback-0402",
            command_payload=proof[0],
            pre=proof[1],
            post=proof[3],
        )
    assert cycle.status() == before_status
    assert cycle.encoded_snapshot() == before_encoded
    assert teaching.status()["demonstrations"] == 0


def test_persistence_retains_authenticated_custody_derived_link() -> None:
    world, physical, cycle, teaching = _authorities()
    payload, pre, _execution, post = _move_proof(
        world, physical, y_mm=1400, intent=6
    )
    learned = _demonstrate(
        teaching,
        tutor_id="joe",
        nonce="guided-body-nonce-0009",
        command_payload=payload,
        pre=pre,
        post=post,
    )
    teaching_snapshot = teaching.encoded_snapshot()
    cycle_snapshot = cycle.encoded_snapshot()

    restored_cycle = CausalActionCycle(authority_key="guided-body-cycle-key")
    restored_cycle.restore_encoded(cycle_snapshot)
    restored = EmbodiedActionTeachingAuthority(
        authority_key=TEACHING_KEY,
        authorized_tutors=("joe",),
        world_authority=world,
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
        action_cycle=absent_cycle,
        demonstration_capacity=4,
    )
    with pytest.raises(ValueError, match="absent from the causal cycle"):
        unlinked.restore_encoded(teaching_snapshot)


def test_legacy_speech_teaching_remains_v1_and_byte_stable() -> None:
    world, physical, cycle, _teaching = _authorities()
    observation = world.observation_snapshot()
    trigger = _custody(
        physical.mount_authenticated_observation(
            observation,
            commit=False,
        ),
        observation=observation,
    ).view.causal_settlement
    cycle.accept(trigger)
    cycle.teach(
        trigger_reference=trigger.event_id,
        action=ActionCommand.embodiment("test.body", b"hello"),
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
