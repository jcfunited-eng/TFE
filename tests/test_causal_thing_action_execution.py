from __future__ import annotations

import pytest

from dsf_ai_service.substrate.causal_action_cycle import ActionCommand
from dsf_ai_service.substrate.causal_thing_action_execution import (
    CausalThingActionExecutionAuthority,
)
from dsf_ai_service.substrate.causal_thing_action_intent import (
    CausalThingActionIntentOwner,
    CausalThingActionIntentProfile,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PickCommand,
    PlaceCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.settled_experience_custody import (
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
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from tests.test_causal_thing_action_deliberation import (
    KEY as ACTION_KEY,
    _admission_custody,
    _close_relation,
    _closure_receipt,
    _owners,
)
from tests.test_causal_thing_mosaic import (
    KEY as WORLD_KEY,
    _execute,
    _fixture,
    _outcome,
)


def _physical_authority(world):
    causal_owner = ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    return (
        W1AudiovisualPhysicalEvidenceAuthority(
            authority_key=ACTION_KEY,
            world_authority=world,
            causal_owner=causal_owner,
            acoustic_emitter=W1AcousticEmitterAuthority(
                authority_key=ACTION_KEY,
                world_authority=world,
            ),
            binaural_auditory_l5_owner=W1BinauralAuditoryL5Owner(),
            anonymous_av_continuity_owner=(
                W1AnonymousAudiovisualContinuityOwner(
                    authority_key=ACTION_KEY,
                    physical_authority_key=ACTION_KEY,
                )
            ),
        ),
        causal_owner,
    )


def _executable_graph():
    world, sensory, partitions, thing_owner = _fixture(max_partitions=4)
    picked = _execute(
        world,
        PickCommand("W1-object-1", duration_microseconds=200_000),
        141,
    )
    first_outcome = _outcome(sensory, picked)
    first_partition = partitions.partition(
        outcome=first_outcome,
        observation=picked.after,
        execution=picked,
    )
    thing_owner.admit(first_partition)
    held_world = world.encoded_snapshot()

    place_action = ActionCommand.embodiment(
        PORT_ID,
        encode_command(
            PlaceCommand(
                "W1-object-1",
                PositionMM(1_500, 1_500, 0),
                duration_microseconds=200_000,
            )
        ),
    )
    trained_place = _execute(
        world,
        PlaceCommand(
            "W1-object-1",
            PositionMM(1_500, 1_500, 0),
            duration_microseconds=200_000,
        ),
        142,
    )
    trained_outcome = _outcome(sensory, trained_place)
    world.restore_encoded(held_world)

    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1_000, 1_400, 0), 90_000),
            duration_microseconds=200_000,
        ),
        143,
    )
    current_outcome = _outcome(sensory, moved)
    current_partition = partitions.partition(
        outcome=current_outcome,
        observation=moved.after,
        execution=moved,
        prior=first_partition,
    )
    current_mosaic = thing_owner.admit(current_partition)

    actions, _reciprocal, deliberation = _owners(thing_owner)
    binding = _close_relation(
        actions,
        trigger=first_outcome.causal_settlement,
        outcome=trained_outcome.causal_settlement,
        action=place_action,
        ordinal=144,
    )
    custody = _admission_custody(
        current_outcome.causal_settlement,
        thing_mosaic_receipt_sha256=(
            current_mosaic.authority_receipt_sha256
        ),
        focused_relation_receipt_sha256=_closure_receipt(
            actions,
            binding.binding_id,
        ),
        world_receipt_sha256=(
            world.observation_snapshot().authority_receipt_sha256
        ),
    )
    resolution = deliberation.resolve(
        current_outcome.causal_settlement,
        cue_senses=("touch",),
        **custody,
    )
    assert resolution is not None
    assert resolution.state == "ready"
    intents = CausalThingActionIntentOwner(
        authority_key=ACTION_KEY,
        profile=CausalThingActionIntentProfile.create(
            profile_id="causal-thing-action-execution-test",
            max_live_intents=2,
            max_witness_bytes=4 * 1024 * 1024,
            max_state_bytes=32 * 1024 * 1024,
        ),
        deliberation_owner=deliberation,
    )
    intent = intents.issue(
        settlement=current_outcome.causal_settlement,
        resolution=resolution,
        **custody,
    )
    physical, causal_owner = _physical_authority(world)
    executor = CausalThingActionExecutionAuthority(
        authority_key=ACTION_KEY,
        intent_owner=intents,
        world_authority=world,
        physical_authority=physical,
        custody_authority_key=ACTION_KEY,
        w1_physical_authority_key=ACTION_KEY,
        world_authority_key=WORLD_KEY,
        custody_profile=SettledExperienceCustodyProfile.create(
            profile_id="causal-thing-action-execution-custody",
            max_children=4,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    return world, physical, causal_owner, intents, intent, executor


def test_same_thing_variant_executes_one_physical_action_and_settles_once():
    world, _physical, causal_owner, intents, intent, executor = (
        _executable_graph()
    )
    before = world.observation_snapshot()
    settled_before = causal_owner.status()["settled"]
    result = executor.execute(intent=intent)

    executor.verify(result.execution)
    assert result.world_execution.before == before
    assert result.world_execution.disposition == "applied"
    assert result.world_execution.after == world.observation_snapshot()
    assert causal_owner.status()["settled"] == settled_before + 1
    assert (
        result.execution.actual_outcome_settlement_receipt_sha256
        == result.physical_mount.causal_settlement.authority_receipt_sha256
    )
    assert (
        result.custody_view.causal_settlement
        is result.physical_mount.causal_settlement
    )
    assert result.execution.prediction_verification in {
        "predicted_exact",
        "predicted_mismatch",
    }
    assert not intents.verify_live(intent)
    assert intents.status()["live_intents"] == 0


def test_failed_physical_mount_restores_world_and_keeps_intent(monkeypatch):
    world, physical, causal_owner, intents, intent, executor = (
        _executable_graph()
    )
    before = world.encoded_snapshot()
    settled_before = causal_owner.status()["settled"]

    def fail_mount(*_args, **_kwargs):
        raise RuntimeError("physical receptor failure")

    monkeypatch.setattr(physical, "mount_action_outcome", fail_mount)
    with pytest.raises(RuntimeError, match="physical receptor failure"):
        executor.execute(intent=intent)
    assert world.encoded_snapshot() == before
    assert intents.verify_live(intent)
    assert causal_owner.status()["settled"] == settled_before


def test_stale_world_refuses_intent_without_consuming_it() -> None:
    world, _physical, causal_owner, intents, intent, executor = (
        _executable_graph()
    )
    world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(
            PoseMM(PositionMM(1_200, 1_400, 0), 90_000),
            duration_microseconds=200_000,
        )),
        causal_intent_receipt_sha256="f" * 64,
        expected_revision=world.observation_snapshot().revision,
    )
    settled_before = causal_owner.status()["settled"]

    with pytest.raises(
        ValueError,
        match="crossed current world custody",
    ):
        executor.execute(intent=intent)

    assert intents.verify_live(intent)
    assert causal_owner.status()["settled"] == settled_before
