from __future__ import annotations

import json

import pytest

from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
    THING_MOSAIC_CONSUMER_ID,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PickCommand,
    PoseMM,
    PositionMM,
)
from tests.test_causal_thing_mosaic import (
    KEY,
    _execute,
    _fixture,
    _outcome,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    _authority as _physical_authority,
)


def _learned_state():
    world, sensory, _legacy_partitions, _legacy_owner = _fixture()
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=256,
    )
    owner = CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="cold-custodied-thing-mosaic",
            max_mosaics=4,
            max_partitions_per_mosaic=4,
            max_roots_per_partition=256,
            max_routes=512,
            max_state_bytes=64 * 1024 * 1024,
        ),
        partition_authority=partitions,
    )
    physical = _physical_authority(world)

    def partition(execution, ordinal, prior=None):
        mount = physical.mount_action_outcome(execution)
        custody = SettledExperienceCustodyAuthority(
            authority_key=f"{KEY}-cold-{ordinal}",
            w1_physical_authority_key=EVIDENCE_KEY,
            world_authority_key=KEY,
            profile=SettledExperienceCustodyProfile.create(
                profile_id=f"cold-thing-custody-{ordinal}",
                max_children=1,
                max_snapshot_bytes=64 * 1024 * 1024,
            ),
        )
        custody.admit(mount, execution)
        capability = custody.issue_child(THING_MOSAIC_CONSUMER_ID)
        return (
            partitions.partition_from_custody(
                custody_authority=custody,
                capability=capability,
                prior=prior,
            ),
            mount,
        )

    picked = _execute(
        world,
        PickCommand("W1-object-1", duration_microseconds=100_000),
        101,
    )
    first, _first_mount = partition(picked, 101)
    genesis = owner.admit(first)
    moved = _execute(
        world,
        MoveCommand(
            PoseMM(PositionMM(1000, 1400, 0), 90_000),
            duration_microseconds=100_000,
        ),
        102,
    )
    second, second_mount = partition(moved, 102, first)
    owner.admit(second)
    return partitions, owner, genesis.thing_id, second_mount


def test_cold_restore_is_byte_identical_and_routes_the_same_lived_field():
    partitions, owner, thing_id, second_mount = _learned_state()
    encoded = owner.snapshot_encoded()

    restored = restore_causal_thing_mosaic_owner(
        authority_key=KEY,
        partition_authority=partitions,
        encoded=encoded,
    )

    assert restored.snapshot_encoded() == encoded
    assert restored.mosaics[0].thing_id == thing_id
    assert restored.route(second_mount.causal_settlement).thing_ids == (
        thing_id,
    )
    assert restored.status() == owner.status()


def test_tampered_or_cross_key_state_cannot_restore():
    partitions, owner, _thing_id, _second_outcome = _learned_state()
    encoded = owner.snapshot_encoded()

    changed = json.loads(encoded)
    changed["body"]["mosaics"][0]["version"] += 1
    tampered = json.dumps(
        changed,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError):
        restore_causal_thing_mosaic_owner(
            authority_key=KEY,
            partition_authority=partitions,
            encoded=tampered,
        )

    with pytest.raises(ValueError, match="state authority changed"):
        restore_causal_thing_mosaic_owner(
            authority_key="different-causal-thing-mosaic-key-20260727",
            partition_authority=partitions,
            encoded=encoded,
        )


def test_legacy_uncustodied_partition_requires_authenticated_migration():
    world, sensory, legacy_partitions, legacy_owner = _fixture()
    picked = _execute(
        world,
        PickCommand("W1-object-1", duration_microseconds=100_000),
        901,
    )
    legacy_owner.admit(legacy_partitions.partition(
        outcome=_outcome(sensory, picked),
        observation=picked.after,
        execution=picked,
    ))
    custody_native = CustodiedW1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=64,
    )

    with pytest.raises(
        ValueError,
        match="authenticated migration is required",
    ):
        restore_causal_thing_mosaic_owner(
            authority_key=KEY,
            partition_authority=custody_native,
            encoded=legacy_owner.snapshot_encoded(),
        )
