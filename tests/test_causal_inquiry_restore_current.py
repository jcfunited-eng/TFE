from __future__ import annotations

import pytest

from dsf_ai_service.substrate.embodiment_world import (
    MoveCommand,
    PoseMM,
    PositionMM,
)
from tests.test_articulatory_consequence_closure import _Harness
from tests.test_causal_inquiry import (
    _custody_for_action,
    _owner,
)


def _prepared_witness(owner, harness, suffix: str):
    execution = harness.self_action(
        MoveCommand(
            target_pose=PoseMM(
                PositionMM(1_010, 1_000, 0),
                0,
            ),
            duration_microseconds=100_000,
        ),
        suffix,
    )
    custody, capability = _custody_for_action(
        harness,
        execution,
    )
    return owner.prepare_witness(
        custody_authority=custody,
        custody_capability=capability,
    )


def test_in_place_restore_preserves_owner_identity_and_exact_bytes() -> None:
    harness = _Harness(
        world_key=b"causal-inquiry-in-place-restore-world-key"
    )
    owner = _owner(harness)
    identity = id(owner)
    before = owner.snapshot_encoded()
    undo = owner.commit_prepared(
        _prepared_witness(owner, harness, "in-place-restore-change")
    )
    owner.finalize_committed(undo)
    assert owner.snapshot_encoded() != before

    owner.restore_current_encoded(before)

    assert id(owner) == identity
    assert owner.snapshot_encoded() == before


def test_in_place_restore_rejects_tamper_without_mutation() -> None:
    harness = _Harness(
        world_key=b"causal-inquiry-in-place-tamper-world-key"
    )
    owner = _owner(harness)
    before = owner.snapshot_encoded()
    damaged = bytearray(before)
    damaged[-12] ^= 1

    with pytest.raises(ValueError):
        owner.restore_current_encoded(bytes(damaged))

    assert owner.snapshot_encoded() == before


def test_in_place_restore_refuses_prepared_and_committed_transactions() -> None:
    harness = _Harness(
        world_key=b"causal-inquiry-in-place-transaction-world-key"
    )
    owner = _owner(harness)
    before = owner.snapshot_encoded()
    prepared = _prepared_witness(
        owner,
        harness,
        "in-place-restore-prepared",
    )

    with pytest.raises(RuntimeError, match="active transaction"):
        owner.restore_current_encoded(before)
    owner.discard_prepared(prepared)

    committed = owner.commit_prepared(
        _prepared_witness(
            owner,
            harness,
            "in-place-restore-committed",
        )
    )
    with pytest.raises(RuntimeError, match="active transaction"):
        owner.restore_current_encoded(before)
    owner.rollback_committed(committed)
    assert owner.snapshot_encoded() == before
