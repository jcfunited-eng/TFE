from __future__ import annotations

import json

import pytest

from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    W1ActionVocalLessonAuthority,
    W1ActionVocalLessonResourceProfile,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidenceAuthority,
    W1BinauralGroundingResourceProfile,
)
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _emission,
    _execution,
    _vocal_execution,
    _world,
)
from tests.test_w1_self_acoustic_propagation import (
    _modulated_tone_pcm,
)


KEY = b"W1-action-vocal-lesson-authority-test-key"


def _q_owner():
    return AuditoryRecurrentMotifOwner(
        AuditoryMotifResourceProfile.create(
            profile_id="W1-action-vocal-lesson-q-proof",
            ear_count=2,
            max_motif_neurons=24_192,
            max_pending_experiences=8,
            max_work_cells_per_observation=8_000_000,
            max_exact_fraction_text_bytes=4_096,
            encoded_state_allocation_bytes=128 * 1024 * 1024,
        ),
        ear_ids=("left", "right"),
    )


def _grounding():
    return W1BinauralGroundingEvidenceAuthority(
        authority_key=KEY,
        resource_profile=W1BinauralGroundingResourceProfile.create(
            profile_id="W1-action-vocal-grounding-proof",
            max_activations=4_096,
            max_roots=256,
            max_evidence_bytes=32 * 1024 * 1024,
        ),
    )


def _train(q_owner):
    world = _world()
    physical = _authority(world)
    epoch = physical.open_epoch()
    sample_start = 0
    for sequence in range(2):
        pressure = _modulated_tone_pcm(11_000)
        execution = _vocal_execution(
            world,
            epoch,
            sequence=sequence,
            source_sample_start=sample_start,
            pcm=pressure,
        )
        mount = physical.mount(
            epoch_token=epoch,
            sequence=sequence,
            execution_receipt=execution,
            acoustic_emission=_emission(
                physical,
                epoch,
                execution,
                sequence=sequence,
                source_sample_start=sample_start,
                pcm=pressure,
            ),
        )
        observed = q_owner.observe_binaural(
            mount.binaural_receptor_settlement
        )
        sample_start += len(pressure) // 2
    assert observed.observation.newly_grown_motif_neuron_ids


def _vocal_mount(world, physical, q_owner, grounding):
    epoch = physical.open_epoch()
    pressure = _modulated_tone_pcm(11_000)
    execution = _vocal_execution(
        world,
        epoch,
        sequence=0,
        source_sample_start=0,
        pcm=pressure,
    )
    mount = physical.mount(
        epoch_token=epoch,
        sequence=0,
        execution_receipt=execution,
        acoustic_emission=_emission(
            physical,
            epoch,
            execution,
            sequence=0,
            source_sample_start=0,
            pcm=pressure,
        ),
    )
    firing = q_owner.fire_binaural(
        mount.binaural_receptor_settlement
    )
    assert firing.activations
    evidence = grounding.admit(
        settlement=mount.causal_settlement,
        receptor_settlement=mount.binaural_receptor_settlement,
        firing=firing,
        motif_owner=q_owner,
    )
    return execution, mount, evidence


def _lesson_owner(world, physical, grounding):
    return W1ActionVocalLessonAuthority(
        authority_key=KEY,
        resource_profile=W1ActionVocalLessonResourceProfile.create(
            profile_id="W1-action-vocal-lesson-proof",
            max_lessons=8,
            max_action_roots_per_lesson=256,
            max_vocal_activations_per_lesson=4_096,
            max_lesson_bytes=32 * 1024 * 1024,
        ),
        world_authority=world,
        physical_authority=physical,
        grounding_authority=grounding,
    )


def test_dynamic_action_then_immediate_external_vocal_is_one_lesson():
    q_owner = _q_owner()
    _train(q_owner)
    grounding = _grounding()
    world = _world()
    physical = _authority(world)
    action_execution = _execution(world)
    action_mount = physical.mount_action_outcome(action_execution)
    vocal_execution, vocal_mount, vocal_grounding = _vocal_mount(
        world, physical, q_owner, grounding
    )
    owner = _lesson_owner(world, physical, grounding)

    lesson = owner.compose(
        action_execution=action_execution,
        action_mount=action_mount,
        vocal_execution=vocal_execution,
        vocal_mount=vocal_mount,
        vocal_grounding=vocal_grounding,
    )

    owner.verify(lesson)
    assert lesson.junction_revision == (
        action_execution.after.revision
        == vocal_execution.before.revision
    )
    assert lesson.action_roots
    assert all(
        any(
            value != "0/1"
            for field_tuple in json.loads(root.value_json)[
                "field_tuples"
            ]
            for _name, value in field_tuple["fields"]
        )
        for root in lesson.action_roots
    )
    assert {
        cell.ear_id for cell in lesson.vocal_cells
    } == {"left", "right"}
    assert not hasattr(lesson, "action_name")
    assert not hasattr(lesson, "text")
    with pytest.raises(ValueError, match="reuses a physical source"):
        owner.compose(
            action_execution=action_execution,
            action_mount=action_mount,
            vocal_execution=vocal_execution,
            vocal_mount=vocal_mount,
            vocal_grounding=vocal_grounding,
        )


def test_intervening_world_revision_cannot_be_hidden_as_immediate():
    q_owner = _q_owner()
    _train(q_owner)
    grounding = _grounding()
    world = _world()
    physical = _authority(world)
    action_execution = _execution(world)
    action_mount = physical.mount_action_outcome(action_execution)
    before_gap = world.observation_snapshot()
    gap_execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(PoseMM(
            PositionMM(1_100, 1_000, 0),
            0,
        ), 200_000)),
        causal_intent_receipt_sha256="7" * 64,
        expected_revision=before_gap.revision,
    )
    assert gap_execution.disposition == "applied"
    vocal_execution, vocal_mount, vocal_grounding = _vocal_mount(
        world, physical, q_owner, grounding
    )
    owner = _lesson_owner(world, physical, grounding)

    with pytest.raises(
        ValueError,
        match="world revision or physical source chain changed",
    ):
        owner.compose(
            action_execution=action_execution,
            action_mount=action_mount,
            vocal_execution=vocal_execution,
            vocal_mount=vocal_mount,
            vocal_grounding=vocal_grounding,
        )
