"""Capacity-one durable custody for an unresolved articulatory attempt."""

from __future__ import annotations

import json

import pytest

from dsf_ai_service.substrate.pending_articulatory_causal_attempt import (
    PendingArticulatoryAttemptCapacityError,
    PendingArticulatoryAttemptStaleError,
    PendingArticulatoryCausalAttemptOwner,
    PendingArticulatoryCausalAttemptProfile,
)
from tests.test_articulatory_consequence_closure import (
    _Harness,
    _intent,
)


KEY = b"pending-articulatory-attempt-test-authority-key"


def _profile(
    *,
    max_state_bytes: int = 2 * 1024 * 1024,
) -> PendingArticulatoryCausalAttemptProfile:
    return PendingArticulatoryCausalAttemptProfile.create(
        profile_id="pending-articulatory-attempt-test",
        max_state_bytes=max_state_bytes,
    )


def _owner(
    harness: _Harness,
    *,
    profile=None,
) -> PendingArticulatoryCausalAttemptOwner:
    return PendingArticulatoryCausalAttemptOwner(
        authority_key=KEY,
        profile=profile or _profile(),
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        world_authority=harness.world,
        consequence_closure_owner=harness.closure,
    )


def _attempt(harness: _Harness):
    mosaic = harness.start_first_thing()
    mosaic, receipt, _synthesis = harness.attempt(
        mosaic,
        program_id=harness.programs[0].program_id,
        name="pending-owner-attempt",
    )
    return mosaic, receipt


def test_arm_is_owner_bound_capacity_one_media_free_and_reversible():
    harness = _Harness(
        world_key=b"pending-arm-world-authority-key"
    )
    mosaic, receipt = _attempt(harness)
    owner = _owner(harness)
    empty = owner.snapshot_encoded()

    prepared = owner.prepare_arm(receipt)
    assert owner.snapshot_encoded() == empty
    assert owner.pending_attempt is None
    undo = owner.commit_prepared_arm(prepared)
    armed = owner.snapshot_encoded()

    assert owner.pending_attempt == receipt
    assert owner.status() == {
        "capacity": 1,
        "pending": 1,
        "prepared": 0,
        "retained_pcm_bytes": 0,
        "schema": (
            "guala.pending_articulatory_causal_attempt.status.v1"
        ),
        "stale_world": False,
        "state_bytes": len(armed),
        "state_capacity_bytes": 2 * 1024 * 1024,
    }
    body = json.loads(armed)["body"]
    assert set(body) == {"pending_attempt", "profile", "schema"}
    assert body["pending_attempt"] == receipt.record()
    assert body["pending_attempt"][
        "acoustic_settlement_receipt_sha256"
    ] == mosaic.partitions[-1].settlement_receipt_sha256
    assert b"pcm" not in armed.lower()
    assert b"waveform" not in armed.lower()
    assert b"transcript" not in armed.lower()
    assert b"cursor" not in armed.lower()
    assert b"timestamp" not in armed.lower()
    assert b"score" not in armed.lower()

    with pytest.raises(
        PendingArticulatoryAttemptCapacityError,
        match="capacity exhausted",
    ):
        owner.prepare_arm(receipt)
    with pytest.raises(ValueError, match="changed custody"):
        owner.commit_prepared_arm(prepared)
    assert owner.snapshot_encoded() == armed

    owner.rollback_committed_arm(undo)
    assert owner.snapshot_encoded() == empty
    assert owner.pending_attempt is None
    with pytest.raises(ValueError, match="changed state"):
        owner.rollback_committed_arm(undo)


def test_consume_is_prepared_one_use_and_exactly_rollbackable():
    harness = _Harness(
        world_key=b"pending-consume-world-authority-key"
    )
    _mosaic, receipt = _attempt(harness)
    owner = _owner(harness)
    owner.commit_prepared_arm(owner.prepare_arm(receipt))
    armed = owner.snapshot_encoded()
    attempt_world = harness.world.encoded_snapshot()

    prepared = owner.prepare_consume()
    assert prepared.attempt_custody == receipt
    assert owner.pending_attempt == receipt
    assert owner.snapshot_encoded() == armed
    consequence = harness.companion_action(
        causal_intent_receipt_sha256=(
            receipt.authority_receipt_sha256
        )
    )
    prepared_closure = harness.closure.prepare(
        receipt,
        consequence,
    )
    with pytest.raises(ValueError, match="not retained"):
        owner.commit_prepared_consume(
            prepared,
            binding=prepared_closure._candidate_binding,
        )
    assert owner.pending_attempt == receipt
    changed = harness.closure.commit_prepared(
        prepared_closure
    )
    binding = harness.closure.bindings[0]
    undo = owner.commit_prepared_consume(
        prepared,
        binding=binding,
    )
    empty = owner.snapshot_encoded()
    assert owner.pending_attempt is None
    assert json.loads(empty)["body"]["pending_attempt"] is None

    with pytest.raises(ValueError, match="changed custody"):
        owner.commit_prepared_consume(
            prepared,
            binding=binding,
        )
    harness.closure.rollback_committed(changed.undo)
    harness.world.restore_encoded(attempt_world)
    owner.rollback_committed_consume(undo)
    assert owner.snapshot_encoded() == armed
    assert owner.pending_attempt == receipt
    with pytest.raises(ValueError, match="changed state"):
        owner.rollback_committed_consume(undo)

    discarded = owner.prepare_consume()
    owner.discard_prepared(discarded)
    assert owner.snapshot_encoded() == armed
    with pytest.raises(ValueError, match="changed custody"):
        owner.commit_prepared_consume(
            discarded,
            binding=binding,
        )


def test_world_receipt_alone_invalidates_without_time_or_replay_state():
    harness = _Harness(
        world_key=b"pending-stale-world-authority-key"
    )
    _mosaic, receipt = _attempt(harness)
    owner = _owner(harness)
    owner.commit_prepared_arm(owner.prepare_arm(receipt))
    armed = owner.snapshot_encoded()

    harness.companion_action(
        causal_intent_receipt_sha256=_intent(
            "unrelated-pending-world-edge"
        )
    )
    assert owner.status()["stale_world"] is True
    with pytest.raises(
        PendingArticulatoryAttemptStaleError,
        match="world receipt is stale",
    ):
        owner.prepare_consume()
    assert owner.snapshot_encoded() == armed

    assert owner.invalidate_stale_world_attempt() is True
    assert owner.pending_attempt is None
    assert owner.invalidate_stale_world_attempt() is False
    assert owner.status()["stale_world"] is False
    with pytest.raises(ValueError, match="unavailable"):
        owner.prepare_consume()


def test_crossed_owner_preparation_and_dependencies_are_rejected():
    first = _Harness(
        world_key=b"pending-crossed-first-world-key"
    )
    second = _Harness(
        world_key=b"pending-crossed-second-world-key"
    )
    _mosaic, receipt = _attempt(first)
    first_owner = _owner(first)
    second_owner = _owner(second)

    prepared = first_owner.prepare_arm(receipt)
    with pytest.raises(ValueError, match="changed custody"):
        second_owner.commit_prepared_arm(prepared)
    first_owner.discard_prepared(prepared)

    with pytest.raises(
        PendingArticulatoryAttemptStaleError,
        match="world receipt is stale",
    ):
        second_owner.prepare_arm(receipt)
    with pytest.raises(ValueError, match="world changed owners"):
        PendingArticulatoryCausalAttemptOwner(
            authority_key=KEY,
            profile=_profile(),
            fresh_custody_authority=first.fresh,
            thing_owner=first.things,
            world_authority=second.world,
            consequence_closure_owner=first.closure,
        )


def test_authenticated_cold_restore_is_byte_exact_and_tamper_evident():
    harness = _Harness(
        world_key=b"pending-cold-restore-world-key"
    )
    _mosaic, receipt = _attempt(harness)
    profile = _profile()
    owner = _owner(harness, profile=profile)
    owner.commit_prepared_arm(owner.prepare_arm(receipt))
    encoded = owner.snapshot_encoded()

    restored = PendingArticulatoryCausalAttemptOwner.restore_encoded(
        authority_key=KEY,
        profile=profile,
        encoded=encoded,
        fresh_custody_authority=harness.fresh,
        thing_owner=harness.things,
        world_authority=harness.world,
        consequence_closure_owner=harness.closure,
    )
    assert restored.snapshot_encoded() == encoded
    assert restored.pending_attempt == receipt
    assert (
        harness.fresh.receipt_from_record(receipt.record())
        == receipt
    )
    forged_receipt = receipt.record()
    forged_receipt["program_id"] = "0" * 64
    with pytest.raises(
        ValueError,
        match="receipt authority changed",
    ):
        harness.fresh.receipt_from_record(forged_receipt)

    damaged = json.loads(encoded)
    damaged["body"]["pending_attempt"]["program_id"] = "0" * 64
    damaged_bytes = json.dumps(
        damaged,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    with pytest.raises(ValueError, match="snapshot HMAC changed"):
        PendingArticulatoryCausalAttemptOwner.restore_encoded(
            authority_key=KEY,
            profile=profile,
            encoded=damaged_bytes,
            fresh_custody_authority=harness.fresh,
            thing_owner=harness.things,
            world_authority=harness.world,
            consequence_closure_owner=harness.closure,
        )

    unrelated = _Harness(
        world_key=b"pending-cold-crossed-world-key"
    )
    with pytest.raises(
        PendingArticulatoryAttemptStaleError,
        match="world receipt is stale",
    ):
        PendingArticulatoryCausalAttemptOwner.restore_encoded(
            authority_key=KEY,
            profile=profile,
            encoded=encoded,
            fresh_custody_authority=unrelated.fresh,
            thing_owner=unrelated.things,
            world_authority=unrelated.world,
            consequence_closure_owner=unrelated.closure,
        )


def test_state_byte_capacity_rejects_arm_without_mutation():
    harness = _Harness(
        world_key=b"pending-capacity-world-authority-key"
    )
    _mosaic, receipt = _attempt(harness)
    empty_profile = _profile(max_state_bytes=2 * 1024 * 1024)
    empty_owner = _owner(harness, profile=empty_profile)
    empty_size = len(empty_owner.snapshot_encoded())
    limited_profile = _profile(max_state_bytes=empty_size)
    limited = _owner(harness, profile=limited_profile)
    before = limited.snapshot_encoded()

    with pytest.raises(
        RuntimeError,
        match="state capacity exhausted",
    ):
        limited.prepare_arm(receipt)
    assert limited.snapshot_encoded() == before
    assert limited.pending_attempt is None
