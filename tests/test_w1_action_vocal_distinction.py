from __future__ import annotations

from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.w1_action_vocal_distinction import (
    W1ActionVocalDistinctionOwner,
    W1ActionVocalDistinctionResourceProfile,
)
from tests.test_w1_action_vocal_lesson import (
    _grounding,
    _lesson_owner,
    _q_owner,
    _vocal_mount,
)
from tests.test_w1_audiovisual_physical_evidence import (
    _authority,
    _emission,
    _vocal_execution,
    _world,
)
from tests.test_w1_self_acoustic_propagation import (
    _modulated_tone_pcm,
)


KEY = b"W1-action-vocal-distinction-test-key"


def _action(world, action_kind: str, intent_digit: str):
    before = world.observation_snapshot()
    command = (
        PickCommand("teaching-object")
        if action_kind == "pick"
        else MoveCommand(PoseMM(
            PositionMM(1_000, 800, 0),
            0,
        ))
    )
    result = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=intent_digit * 64,
        expected_revision=before.revision,
    )
    assert result.disposition == "applied"
    return result


def _observe_form(q_owner, action_kind: str, intent_digit: str):
    world = _world()
    physical = _authority(world)
    _action(world, action_kind, intent_digit)
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
    return q_owner.observe_binaural(
        mount.binaural_receptor_settlement
    )


def _lesson(q_owner, action_kind: str, intent_digit: str):
    grounding = _grounding()
    world = _world()
    physical = _authority(world)
    action_execution = _action(world, action_kind, intent_digit)
    action_mount = physical.mount_action_outcome(action_execution)
    vocal_execution, vocal_mount, vocal_grounding = _vocal_mount(
        world, physical, q_owner, grounding
    )
    owner = _lesson_owner(world, physical, grounding)
    return owner.compose(
        action_execution=action_execution,
        action_mount=action_mount,
        vocal_execution=vocal_execution,
        vocal_mount=vocal_mount,
        vocal_grounding=vocal_grounding,
    ), owner


def test_complete_action_fields_grow_exact_vocal_conjunctions():
    q_owner = _q_owner()
    for action_kind, digits in (
        ("pick", ("1", "2")),
        ("move", ("3", "4")),
    ):
        first = _observe_form(q_owner, action_kind, digits[0])
        second = _observe_form(q_owner, action_kind, digits[1])
        assert second.observation.newly_grown_motif_neuron_ids or (
            first.observation.firing_motif_neuron_ids
        )
    lessons = []
    verifier = None
    for action_kind, digits in (
        ("pick", ("5", "6")),
        ("move", ("7", "8")),
    ):
        for digit in digits:
            lesson, verifier = _lesson(
                q_owner, action_kind, digit
            )
            lessons.append(lesson)
    assert verifier is not None
    owner = W1ActionVocalDistinctionOwner(
        authority_key=KEY,
        resource_profile=(
            W1ActionVocalDistinctionResourceProfile.create(
                profile_id="W1-action-vocal-distinction-proof",
                max_distinctions=8,
                max_lessons_per_distinction=16,
                max_alternatives_per_distinction=8,
                max_roots_per_alternative=256,
                max_diagnostic_cells_per_alternative=24_192,
                max_distinction_bytes=16 * 1024 * 1024,
            )
        ),
        lesson_authority=verifier,
    )

    distinction = owner.learn(tuple(lessons))

    owner.verify(distinction)
    assert len(distinction.alternatives) == 2
    assert all(
        len(value.positive_lesson_receipt_sha256s) == 2
        for value in distinction.alternatives
    )
    assert all(
        value.diagnostic_vocal_cells
        for value in distinction.alternatives
    )
    assert {
        cell.ear_id
        for value in distinction.alternatives
        for cell in value.diagnostic_vocal_cells
    } == {"left", "right"}
    assert not set(
        distinction.alternatives[0].diagnostic_vocal_cells
    ).intersection(
        distinction.alternatives[1].diagnostic_vocal_cells
    )
    resolved_first = owner.resolve(
        distinction=distinction,
        active_vocal_cells=lessons[0].vocal_cells,
    )
    resolved_second = owner.resolve(
        distinction=distinction,
        active_vocal_cells=lessons[-1].vocal_cells,
    )
    assert len(resolved_first) == 1
    assert len(resolved_second) == 1
    assert (
        resolved_first[0].action_field_identity
        != resolved_second[0].action_field_identity
    )
