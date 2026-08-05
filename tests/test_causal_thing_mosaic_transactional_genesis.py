from __future__ import annotations

import hashlib
import hmac
from dataclasses import replace

import pytest

from dsf_ai_service.substrate import causal_thing_mosaic as mosaic_module
from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
    CausalThingMosaicProfile,
)
from tests.test_causal_thing_mosaic import KEY
from tests.test_causal_thing_mosaic_ordered_continuation import (
    _ordered_episode,
)


def _owner(
    partition_authority,
    *,
    max_mosaics: int = 2,
    max_routes: int = 2_048,
    max_state_bytes: int = 32 * 1024 * 1024,
) -> CausalThingMosaicOwner:
    return CausalThingMosaicOwner(
        authority_key=KEY,
        profile=CausalThingMosaicProfile.create(
            profile_id="transactional-custody-genesis",
            max_mosaics=max_mosaics,
            max_partitions_per_mosaic=5,
            max_roots_per_partition=64,
            max_routes=max_routes,
            max_state_bytes=max_state_bytes,
        ),
        partition_authority=partition_authority,
    )


def test_failed_downstream_work_rolls_genesis_back_byte_identically():
    partitions, owner, first, _second, _third = _ordered_episode()
    before = owner.snapshot_encoded()

    prepared = owner.prepare_custody_genesis_admission(first)
    owner.verify_prepared_custody_genesis_admission(prepared)
    assert owner.snapshot_encoded() == before

    undo = owner.commit_prepared_custody_genesis_admission(prepared)
    committed = owner.snapshot_encoded()
    assert committed != before
    assert owner.mosaics == (prepared.staged_mosaic,)

    downstream_error = RuntimeError("downstream lived-context refusal")
    assert str(downstream_error) == "downstream lived-context refusal"
    owner.rollback_committed_custody_genesis_admission(undo)
    assert owner.snapshot_encoded() == before
    assert owner.mosaics == ()

    retried = owner.prepare_custody_genesis_admission(first)
    owner.commit_prepared_custody_genesis_admission(retried)
    assert retried.staged_mosaic == prepared.staged_mosaic
    assert owner.snapshot_encoded() == committed
    assert len(owner.mosaics) == 1


def test_committed_genesis_replay_and_concurrent_prepare_cannot_duplicate_thing():
    _partitions, owner, first, _second, _third = _ordered_episode()
    first_prepared = owner.prepare_custody_genesis_admission(first)
    concurrent = owner.prepare_custody_genesis_admission(first)

    owner.commit_prepared_custody_genesis_admission(first_prepared)
    committed = owner.snapshot_encoded()

    with pytest.raises(RuntimeError, match="genesis is stale"):
        owner.commit_prepared_custody_genesis_admission(concurrent)
    with pytest.raises(ValueError, match="replays retained"):
        owner.prepare_custody_genesis_admission(first)

    assert owner.snapshot_encoded() == committed
    assert len(owner.mosaics) == 1
    assert owner.mosaics[0].partitions == (first,)


def test_genesis_capabilities_are_owner_bound_and_exactly_once():
    partitions, owner, first, _second, _third = _ordered_episode()
    prepared = owner.prepare_custody_genesis_admission(first)
    before = owner.snapshot_encoded()

    other = _owner(partitions)
    other_before = other.snapshot_encoded()
    with pytest.raises(ValueError, match="changed custody"):
        other.verify_prepared_custody_genesis_admission(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        other.commit_prepared_custody_genesis_admission(prepared)
    assert other.snapshot_encoded() == other_before

    owner.discard_prepared_custody_genesis_admission(prepared)
    assert owner.snapshot_encoded() == before
    with pytest.raises(ValueError, match="changed custody"):
        owner.commit_prepared_custody_genesis_admission(prepared)

    committed_prepared = owner.prepare_custody_genesis_admission(first)
    undo = owner.commit_prepared_custody_genesis_admission(
        committed_prepared
    )
    owner.rollback_committed_custody_genesis_admission(undo)
    with pytest.raises(ValueError, match="changed custody"):
        owner.rollback_committed_custody_genesis_admission(undo)
    assert owner.snapshot_encoded() == before


def test_genesis_type_custody_and_capacity_fail_before_publication():
    partitions, _owner_unused, first, second, _third = _ordered_episode()

    owner = _owner(partitions)
    before = owner.snapshot_encoded()
    with pytest.raises(TypeError, match="partition is not typed"):
        owner.prepare_custody_genesis_admission(object())
    with pytest.raises(ValueError, match="cannot continue"):
        owner.prepare_custody_genesis_admission(second)
    non_custody = replace(
        first,
        source_occurrence_id=None,
        parent_custody_receipt_sha256=None,
        thing_custody_capability_receipt_sha256=None,
        authority_hmac_sha256="0" * 64,
        authority_receipt_sha256="0" * 64,
    )
    signature = hmac.new(
        partitions._partition_key,
        mosaic_module._PARTITION_DOMAIN
        + mosaic_module._canonical(non_custody.payload()),
        hashlib.sha256,
    ).hexdigest()
    non_custody = replace(
        non_custody,
        authority_hmac_sha256=signature,
        authority_receipt_sha256=mosaic_module._digest({
            "authority_hmac_sha256": signature,
            "payload": non_custody.payload(),
        }),
    )
    with pytest.raises(ValueError, match="custody-derived"):
        owner.prepare_custody_genesis_admission(non_custody)
    assert owner.snapshot_encoded() == before

    route_count = len({root.route_key for root in first.full_field_roots})
    route_limited = _owner(
        partitions,
        max_routes=route_count - 1,
    )
    route_before = route_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="route capacity exhausted"):
        route_limited.prepare_custody_genesis_admission(first)
    assert route_limited.snapshot_encoded() == route_before

    probe = _owner(partitions)
    probe.admit_custody_genesis(first)
    genesis_bytes = len(probe.snapshot_encoded())
    state_limited = _owner(
        partitions,
        max_state_bytes=genesis_bytes - 1_024,
    )
    state_before = state_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="state capacity exhausted"):
        state_limited.prepare_custody_genesis_admission(first)
    assert state_limited.snapshot_encoded() == state_before

    mosaic_limited = _owner(partitions, max_mosaics=1)
    mosaic_limited.admit_custody_genesis(first)
    mosaic_before = mosaic_limited.snapshot_encoded()
    with pytest.raises(RuntimeError, match="mosaic capacity exhausted"):
        mosaic_limited.prepare_custody_genesis_admission(first)
    assert mosaic_limited.snapshot_encoded() == mosaic_before


def test_genesis_undo_refuses_to_erase_a_later_continuation():
    _partitions, owner, first, second, _third = _ordered_episode()
    genesis_prepared = owner.prepare_custody_genesis_admission(first)
    genesis_undo = owner.commit_prepared_custody_genesis_admission(
        genesis_prepared
    )
    genesis_snapshot = owner.snapshot_encoded()

    continuation = owner.prepare_ordered_custody_continuation((second,))
    continuation_undo = (
        owner.commit_prepared_ordered_custody_continuation(continuation)
    )
    with pytest.raises(RuntimeError, match="genesis undo is stale"):
        owner.rollback_committed_custody_genesis_admission(genesis_undo)

    owner.rollback_committed_ordered_custody_continuation(
        continuation_undo
    )
    assert owner.snapshot_encoded() == genesis_snapshot
    owner.rollback_committed_custody_genesis_admission(genesis_undo)
    assert owner.mosaics == ()
