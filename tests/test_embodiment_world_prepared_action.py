from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    PreparedActionExecution,
    VocalizeCommand,
    encode_command,
)


def _intent(number: int) -> str:
    return f"{number:064x}"


def _vocal_command() -> VocalizeCommand:
    return VocalizeCommand(
        epoch_commitment_sha256="a" * 64,
        sequence=0,
        source_sample_start=0,
        pcm_sha256="b" * 64,
        sample_count=256,
    )


def _prepare(
    authority: EmbodimentWorldAuthority,
    *,
    intent_number: int = 1,
    expected_revision: int = 0,
) -> PreparedActionExecution | ActionExecutionReceipt:
    return authority.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(_vocal_command()),
        causal_intent_receipt_sha256=_intent(intent_number),
        expected_revision=expected_revision,
    )


def test_prepare_is_physically_pure_and_commit_applies_exactly_once() -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-purity-key"
    )
    before_encoded = authority.encoded_snapshot()
    before = authority.observation_snapshot()

    prepared = _prepare(authority)

    assert isinstance(prepared, PreparedActionExecution)
    receipt = prepared.execution_receipt
    assert receipt.disposition == "applied"
    assert receipt.before == before
    assert receipt.after.revision == before.revision + 1
    assert authority.encoded_snapshot() == before_encoded
    assert authority.observation_snapshot() == before
    assert authority.recent_applied_receipts() == ()
    assert authority.status()["prepared_action_execution"] == 1

    committed = authority.commit_prepared_action(prepared)

    assert committed is receipt
    assert authority.observation_snapshot() == receipt.after
    assert authority.recent_applied_receipts() == (receipt,)
    assert authority.status()["prepared_action_execution"] == 0
    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_action(prepared)


def test_discard_releases_capacity_without_any_world_mutation() -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-discard-key"
    )
    before = authority.encoded_snapshot()
    prepared = _prepare(authority)
    assert isinstance(prepared, PreparedActionExecution)

    authority.discard_prepared_action(prepared)

    assert authority.encoded_snapshot() == before
    assert authority.status()["prepared_action_execution"] == 0
    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_action(prepared)


def test_stale_prepare_returns_rejection_without_reserving_or_mutating() -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-stale-key"
    )
    before = authority.encoded_snapshot()

    rejected = _prepare(authority, expected_revision=1)

    assert isinstance(rejected, ActionExecutionReceipt)
    assert rejected.disposition == "rejected"
    assert rejected.reason == "stale_world_revision"
    assert rejected.before == rejected.after
    assert authority.encoded_snapshot() == before
    assert authority.status()["prepared_action_execution"] == 0


def test_capacity_one_refuses_crossed_prepare_and_live_execution() -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-capacity-key"
    )
    before = authority.encoded_snapshot()
    prepared = _prepare(authority)
    assert isinstance(prepared, PreparedActionExecution)

    with pytest.raises(RuntimeError, match="already has a prepared"):
        _prepare(authority, intent_number=2)
    with pytest.raises(RuntimeError, match="already has a prepared"):
        authority.execute_port_command(
            port_id=PORT_ID,
            command_payload=encode_command(
                MoveCommand(
                    PoseMM(PositionMM(1000, 1200, 0), 0),
                    200_000,
                )
            ),
            causal_intent_receipt_sha256=_intent(3),
            expected_revision=0,
        )

    assert authority.encoded_snapshot() == before
    assert authority.status()["prepared_action_execution"] == 1
    authority.discard_prepared_action(prepared)


def test_concurrent_prepare_grants_exactly_one_live_capability() -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-concurrency-key"
    )
    barrier = threading.Barrier(3)

    def attempt(number: int):
        barrier.wait()
        try:
            return _prepare(authority, intent_number=number)
        except RuntimeError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(attempt, 10),
            pool.submit(attempt, 11),
        )
        barrier.wait()
        results = tuple(future.result() for future in futures)

    prepared = tuple(
        value for value in results
        if isinstance(value, PreparedActionExecution)
    )
    refused = tuple(
        value for value in results if isinstance(value, RuntimeError)
    )
    assert len(prepared) == len(refused) == 1
    assert "already has a prepared" in str(refused[0])
    assert authority.observation_snapshot().revision == 0
    authority.commit_prepared_action(prepared[0])
    assert authority.observation_snapshot().revision == 1
    assert len(authority.recent_applied_receipts()) == 1


def test_prepare_failure_leaves_no_reservation_and_exact_prior_bytes(
    monkeypatch,
) -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-prepare-failure-key"
    )
    before = authority.encoded_snapshot()
    original_verify = authority._verify_state_capacity_for

    def fail_candidate(candidate) -> None:
        if candidate is not authority._state:
            raise RuntimeError("injected prepared candidate capacity failure")
        original_verify(candidate)

    monkeypatch.setattr(
        authority, "_verify_state_capacity_for", fail_candidate
    )
    with pytest.raises(RuntimeError, match="candidate capacity failure"):
        _prepare(authority)
    monkeypatch.setattr(
        authority, "_verify_state_capacity_for", original_verify
    )

    assert authority.encoded_snapshot() == before
    assert authority.status()["prepared_action_execution"] == 0


def test_commit_interruption_restores_exact_world_and_remains_discardable(
    monkeypatch,
) -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-commit-failure-key"
    )
    before = authority.encoded_snapshot()
    prepared = _prepare(authority)
    assert isinstance(prepared, PreparedActionExecution)
    original_commit = authority._commit_authority_state

    def interrupt_after_assignment(candidate):
        authority._state = candidate
        raise KeyboardInterrupt("injected prepared commit interruption")

    monkeypatch.setattr(
        authority,
        "_commit_authority_state",
        interrupt_after_assignment,
    )
    with pytest.raises(KeyboardInterrupt, match="commit interruption"):
        authority.commit_prepared_action(prepared)
    monkeypatch.setattr(
        authority,
        "_commit_authority_state",
        original_commit,
    )

    assert authority.encoded_snapshot() == before
    assert authority.status()["prepared_action_execution"] == 1
    authority.discard_prepared_action(prepared)
    assert authority.status()["prepared_action_execution"] == 0


def test_copied_capability_and_changed_world_identity_fail_closed() -> None:
    authority = EmbodimentWorldAuthority(
        authority_key="prepared-world-capability-key"
    )
    before = authority.encoded_snapshot()
    prepared = _prepare(authority)
    assert isinstance(prepared, PreparedActionExecution)

    copied = replace(prepared)
    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_action(copied)

    prior_identity = authority._state
    authority._state = replace(prior_identity)
    with pytest.raises(RuntimeError, match="world changed before commit"):
        authority.commit_prepared_action(prepared)
    assert authority.encoded_snapshot() == before

    authority._state = prior_identity
    authority.discard_prepared_action(prepared)


def test_prepared_state_is_not_persisted_and_cold_bytes_remain_equivalent() -> None:
    key = "prepared-world-cold-equivalence-key"
    authority = EmbodimentWorldAuthority(authority_key=key)
    before = authority.encoded_snapshot()
    prepared = _prepare(authority)
    assert isinstance(prepared, PreparedActionExecution)
    assert authority.encoded_snapshot() == before

    cold = EmbodimentWorldAuthority(authority_key=key)
    cold.restore_encoded(authority.encoded_snapshot())

    assert cold.encoded_snapshot() == before
    assert cold.observation_snapshot() == authority.observation_snapshot()
    assert cold.status()["prepared_action_execution"] == 0
    with pytest.raises(RuntimeError, match="prepared action execution"):
        authority.restore_encoded(before)
    assert authority.encoded_snapshot() == before
    assert authority.status()["prepared_action_execution"] == 1
    authority.discard_prepared_action(prepared)
