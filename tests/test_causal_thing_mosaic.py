from __future__ import annotations

import json
from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
    W1ContactThingEncounterAuthority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
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
from dsf_ai_service.substrate.w1_physical_receptors import (
    EmbodimentSensoryOutcomeAuthority,
)


KEY = "new-causal-thing-mosaic-authority-key-20260727"
ACTION_DURATION_MICROSECONDS = 200_000


def _causal_owner() -> ExactCausalExperienceOwner:
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    )


def _execute(world, command, ordinal):
    before = world.observation_snapshot()
    return world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256=f"{ordinal:064x}",
        expected_revision=before.revision,
    )


def _fixture(*, max_partitions=3):
    world = EmbodimentWorldAuthority(authority_key=KEY)
    sensory = EmbodimentSensoryOutcomeAuthority(authority_key=KEY)
    partition_authority = W1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=512,
    )
    owner = CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="new-production-THING-mosaic",
            max_mosaics=4,
            max_partitions_per_mosaic=max_partitions,
            max_roots_per_partition=512,
            max_routes=512,
            max_state_bytes=32 * 1024 * 1024,
        ),
        partition_authority=partition_authority,
    )
    return world, sensory, partition_authority, owner


def _outcome(sensory, execution):
    return sensory.transduce(
        execution.after,
        causal_owner=_causal_owner(),
        execution_receipt=execution,
        commit=True,
    )


def test_new_THING_mosaic_expands_only_through_exact_physical_chain():
    world, sensory, partitions, owner = _fixture()

    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        1,
    )
    first_outcome = _outcome(sensory, picked)
    first = partitions.partition(
        outcome=first_outcome,
        observation=picked.after,
        execution=picked,
    )
    genesis = owner.admit(first)

    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            ACTION_DURATION_MICROSECONDS,
        ),
        2,
    )
    second_outcome = _outcome(sensory, moved)
    second = partitions.partition(
        outcome=second_outcome,
        observation=moved.after,
        execution=moved,
        prior=first,
    )
    expanded = owner.admit(second)

    assert expanded.thing_id == genesis.thing_id
    assert expanded.version == 1
    assert expanded.partitions == (first, second)
    assert first.entity_continuity_hmac_sha256 == (
        second.entity_continuity_hmac_sha256
    )
    assert first.authority_receipt_sha256 == (
        second.prior_partition_receipt_sha256
    )
    assert all(key[0] == "touch" for key in first.entity_root_keys)
    assert owner.route(second_outcome.causal_settlement).thing_ids == (
        genesis.thing_id,
    )

    retained_fields = tuple(
        tuple(
            name
            for name, _value in item["fields"]
        )
        for partition in expanded.partitions
        for root in partition.full_field_roots
        for item in json.loads(root.full_evidence_json)["field_tuples"]
    )
    assert retained_fields
    assert all(value == DSF_FIELD_ORDER for value in retained_fields)
    assert owner.status()["full_field"] is True
    assert owner.status()["reduced_approximation"] is False


def test_scene_overlap_cannot_create_a_partition_or_mutate_identity():
    world, sensory, partitions, owner = _fixture()
    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            ACTION_DURATION_MICROSECONDS,
        ),
        3,
    )
    outcome = _outcome(sensory, moved)
    before = owner.snapshot_encoded()

    with pytest.raises(ValueError, match="contacted entity"):
        partitions.partition(
            outcome=outcome,
            observation=moved.after,
            execution=moved,
        )
    assert owner.snapshot_encoded() == before


def test_capacity_and_tampering_fail_without_changing_the_mosaic():
    world, sensory, partitions, owner = _fixture(max_partitions=2)
    picked = _execute(
        world,
        PickCommand("W1-object-1", ACTION_DURATION_MICROSECONDS),
        4,
    )
    first = partitions.partition(
        outcome=_outcome(sensory, picked),
        observation=picked.after,
        execution=picked,
    )
    owner.admit(first)
    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            ACTION_DURATION_MICROSECONDS,
        ),
        5,
    )
    second = partitions.partition(
        outcome=_outcome(sensory, moved),
        observation=moved.after,
        execution=moved,
        prior=first,
    )
    owner.admit(second)
    before = owner.snapshot_encoded()

    with pytest.raises(ValueError, match="authority changed"):
        owner.admit(replace(second, entity_continuity_hmac_sha256="0" * 64))
    assert owner.snapshot_encoded() == before

    moved_again = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1200, 1400, 0), 90_000),
            ACTION_DURATION_MICROSECONDS,
        ),
        6,
    )
    third = partitions.partition(
        outcome=_outcome(sensory, moved_again),
        observation=moved_again.after,
        execution=moved_again,
        prior=second,
    )
    with pytest.raises(RuntimeError, match="partition capacity exhausted"):
        owner.admit(third)
    assert owner.snapshot_encoded() == before
