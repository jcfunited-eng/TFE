from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate import causal_thing_mosaic as module
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
    ThingEncounterPartition,
)
from dsf_ai_service.substrate.causal_thing_mosaic_persistence import (
    restore_causal_thing_mosaic_owner,
)
from dsf_ai_service.substrate.custodied_thing_encounter import (
    CustodiedW1ContactThingEncounterAuthority,
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


def _custody_derived(
    partition: ThingEncounterPartition,
    *,
    partition_authority,
    ordinal: int,
) -> ThingEncounterPartition:
    provisional = replace(
        partition,
        source_occurrence_id=f"{ordinal:064x}",
        parent_custody_receipt_sha256=f"{ordinal + 100:064x}",
        thing_custody_capability_receipt_sha256=(
            f"{ordinal + 200:064x}"
        ),
        entity_root_keys=tuple(sorted(
            root.route_key
            for root in partition.full_field_roots
        )),
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    signature = hmac.new(
        partition_authority._partition_key,
        module._PARTITION_DOMAIN + module._canonical(
            provisional.payload()
        ),
        hashlib.sha256,
    ).hexdigest()
    result = replace(
        provisional,
        authority_hmac_sha256=signature,
        authority_receipt_sha256=module._digest({
            "authority_hmac_sha256": signature,
            "payload": provisional.payload(),
        }),
    )
    partition_authority.verify(result)
    return result


def _ordered_episode(*, max_partitions: int = 5):
    world, sensory, _legacy_partitions, _legacy_owner = _fixture(
        max_partitions=max_partitions
    )
    partitions = CustodiedW1ContactThingEncounterAuthority(
        authority_key=KEY,
        world_authority=world,
        sensory_authority=sensory,
        max_roots_per_partition=512,
    )
    owner = _owner(
        partitions=partitions,
        max_partitions=max_partitions,
        max_routes=512,
        max_state_bytes=32 * 1024 * 1024,
    )
    picked = _execute(world, PickCommand("W1-object-1", 200_000), 31)
    first = _custody_derived(
        partitions.partition(
            outcome=_outcome(sensory, picked),
            observation=picked.after,
            execution=picked,
        ),
        partition_authority=partitions,
        ordinal=1,
    )

    moved = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(1000, 1400, 0), 90_000), 200_000),
        32,
    )
    second = _custody_derived(
        partitions.partition(
            outcome=_outcome(sensory, moved),
            observation=moved.after,
            execution=moved,
            prior=first,
        ),
        partition_authority=partitions,
        ordinal=2,
    )

    moved_again = _execute(
        world,
        MoveCommand(PoseMM(PositionMM(1200, 1400, 0), 90_000), 200_000),
        33,
    )
    third = _custody_derived(
        partitions.partition(
            outcome=_outcome(sensory, moved_again),
            observation=moved_again.after,
            execution=moved_again,
            prior=second,
        ),
        partition_authority=partitions,
        ordinal=3,
    )
    return partitions, owner, first, second, third


def _owner(
    *,
    partitions,
    max_partitions: int,
    max_routes: int,
    max_state_bytes: int,
) -> CausalThingMosaicOwner:
    return CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="ordered-custody-continuation",
            max_mosaics=2,
            max_partitions_per_mosaic=max_partitions,
            max_roots_per_partition=64,
            max_routes=max_routes,
            max_state_bytes=max_state_bytes,
        ),
        partition_authority=partitions,
    )


def test_ordered_custody_episode_is_one_full_field_mutation():
    partitions, owner, first, second, third = _ordered_episode()
    genesis = owner.admit(first)
    before = owner.snapshot_encoded()

    expanded = owner.admit_ordered_custody_continuation(
        (second, third)
    )

    assert expanded.thing_id == genesis.thing_id
    assert expanded.version == genesis.version + 2
    assert expanded.partitions == (first, second, third)
    assert owner.mosaics == (expanded,)
    assert owner.snapshot_encoded() != before
    assert json.loads(owner.snapshot_encoded())["body"]["schema"] == (
        module.STATE_SCHEMA
    )
    retained_fields = tuple(
        tuple(name for name, _value in field_tuple["fields"])
        for partition in expanded.partitions
        for root in partition.full_field_roots
        for field_tuple in json.loads(root.full_evidence_json)[
            "field_tuples"
        ]
    )
    assert retained_fields
    assert all(fields == DSF_FIELD_ORDER for fields in retained_fields)
    assert owner.status()["full_field"] is True
    assert owner.status()["reduced_approximation"] is False
    restored = restore_causal_thing_mosaic_owner(
        authority_key=KEY,
        partition_authority=partitions,
        encoded=owner.snapshot_encoded(),
    )
    assert restored.snapshot_encoded() == owner.snapshot_encoded()
    assert restored.mosaics == owner.mosaics


def test_wrong_order_and_non_custody_input_publish_nothing():
    partitions, owner, first, second, third = _ordered_episode()
    owner.admit(first)
    before = owner.snapshot_encoded()

    with pytest.raises(ValueError, match="does not name|physical chain"):
        owner.admit_ordered_custody_continuation((third, second))
    assert owner.snapshot_encoded() == before

    non_custody = partitions.partition
    assert callable(non_custody)
    raw = replace(
        second,
        source_occurrence_id=None,
        parent_custody_receipt_sha256=None,
        thing_custody_capability_receipt_sha256=None,
        entity_root_keys=tuple(sorted(
            root.route_key
            for root in second.full_field_roots
            if root.sense == "touch"
        )),
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    signature = hmac.new(
        partitions._partition_key,
        module._PARTITION_DOMAIN + module._canonical(raw.payload()),
        hashlib.sha256,
    ).hexdigest()
    raw = replace(
        raw,
        authority_hmac_sha256=signature,
        authority_receipt_sha256=module._digest({
            "authority_hmac_sha256": signature,
            "payload": raw.payload(),
        }),
    )
    with pytest.raises(ValueError, match="custody-derived"):
        owner.admit_ordered_custody_continuation((raw,))
    assert owner.snapshot_encoded() == before


def test_partition_route_and_state_capacity_fail_before_publication():
    partitions, _owner_unused, first, second, third = _ordered_episode()
    partition_limited = _owner(
        partitions=partitions,
        max_partitions=2,
        max_routes=2_048,
        max_state_bytes=32 * 1024 * 1024,
    )
    partition_limited.admit(first)
    before = partition_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="partition capacity exhausted"):
        partition_limited.prepare_ordered_custody_continuation(
            (second, third)
        )
    assert partition_limited.snapshot_encoded() == before

    genesis_routes = len({
        root.route_key for root in first.full_field_roots
    })
    route_limited = _owner(
        partitions=partitions,
        max_partitions=5,
        max_routes=genesis_routes,
        max_state_bytes=32 * 1024 * 1024,
    )
    route_limited.admit(first)
    before = route_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="route capacity exhausted"):
        route_limited.prepare_ordered_custody_continuation(
            (second, third)
        )
    assert route_limited.snapshot_encoded() == before

    probe = _owner(
        partitions=partitions,
        max_partitions=5,
        max_routes=2_048,
        max_state_bytes=32 * 1024 * 1024,
    )
    probe.admit(first)
    genesis_bytes = len(probe.snapshot_encoded())
    state_limited = _owner(
        partitions=partitions,
        max_partitions=5,
        max_routes=2_048,
        max_state_bytes=genesis_bytes + 1_024,
    )
    state_limited.admit(first)
    before = state_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="state capacity exhausted"):
        state_limited.prepare_ordered_custody_continuation(
            (second, third)
        )
    assert state_limited.snapshot_encoded() == before


def test_prepare_commit_and_rollback_are_byte_exact_and_exactly_once():
    _partitions, owner, first, second, third = _ordered_episode()
    owner.admit(first)
    before = owner.snapshot_encoded()

    prepared = owner.prepare_ordered_custody_continuation(
        (second, third)
    )
    owner.verify_prepared_ordered_custody_continuation(prepared)
    assert owner.snapshot_encoded() == before
    assert prepared.staged_mosaic.partitions == (
        first,
        second,
        third,
    )

    undo = owner.commit_prepared_ordered_custody_continuation(
        prepared
    )
    committed = owner.snapshot_encoded()
    assert committed != before
    assert owner.mosaics == (prepared.staged_mosaic,)
    with pytest.raises(ValueError, match="changed custody"):
        owner.commit_prepared_ordered_custody_continuation(prepared)

    owner.rollback_committed_ordered_custody_continuation(undo)
    assert owner.snapshot_encoded() == before
    with pytest.raises(ValueError, match="changed custody"):
        owner.rollback_committed_ordered_custody_continuation(undo)


def test_crossed_owner_prepared_capability_fails_closed():
    partitions, owner, first, second, _third = _ordered_episode()
    owner.admit(first)
    prepared = owner.prepare_ordered_custody_continuation((second,))
    before = owner.snapshot_encoded()

    other = _owner(
        partitions=partitions,
        max_partitions=5,
        max_routes=512,
        max_state_bytes=32 * 1024 * 1024,
    )
    other.admit(first)
    other_before = other.snapshot_encoded()
    with pytest.raises(ValueError, match="changed custody"):
        other.verify_prepared_ordered_custody_continuation(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        other.commit_prepared_ordered_custody_continuation(prepared)

    assert owner.snapshot_encoded() == before
    assert other.snapshot_encoded() == other_before
    owner.discard_prepared_ordered_custody_continuation(prepared)
    assert owner.snapshot_encoded() == before


def test_undo_is_stale_until_the_later_committed_tail_is_rolled_back():
    _partitions, owner, first, second, third = _ordered_episode()
    owner.admit(first)
    genesis = owner.snapshot_encoded()

    second_prepared = owner.prepare_ordered_custody_continuation(
        (second,)
    )
    second_undo = owner.commit_prepared_ordered_custody_continuation(
        second_prepared
    )
    after_second = owner.snapshot_encoded()
    third_prepared = owner.prepare_ordered_custody_continuation((third,))
    third_undo = owner.commit_prepared_ordered_custody_continuation(
        third_prepared
    )

    with pytest.raises(RuntimeError, match="undo is stale"):
        owner.rollback_committed_ordered_custody_continuation(
            second_undo
        )
    owner.rollback_committed_ordered_custody_continuation(third_undo)
    assert owner.snapshot_encoded() == after_second
    owner.rollback_committed_ordered_custody_continuation(second_undo)
    assert owner.snapshot_encoded() == genesis
