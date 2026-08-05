from __future__ import annotations

import json

import pytest

from dsf_ai_service.substrate.pending_body_owned_vocal_consequence import (
    PendingBodyOwnedVocalClientCapability,
    PendingBodyOwnedVocalConsequenceCapacityError,
    PendingBodyOwnedVocalConsequenceOwner,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from tests.physical_inquiry_test_support import (
    RUNTIME_KEY,
    _seed_held_thing_and_inquiry,
)


OWNER_KEY = (
    "pending-body-owned-vocal-consequence-test-authority-key-"
    "12345678901234567890"
)
PROFILE_ID = "test:pending-body-owned-vocal-consequence"
STATE_CAPACITY = 64 * 1024


def _runtime(monkeypatch: pytest.MonkeyPatch) -> Guala:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv("GUALA_CAUSAL_ACTION_KEY", RUNTIME_KEY)
    return Guala()


def _owner(guala: Guala) -> PendingBodyOwnedVocalConsequenceOwner:
    return PendingBodyOwnedVocalConsequenceOwner(
        authority_key=OWNER_KEY,
        profile_id=PROFILE_ID,
        max_state_bytes=STATE_CAPACITY,
        inquiry_owner=guala._causal_inquiry_owner,
        vocal_body_owner=guala._embodied_vocal_body,
    )


def _candidate_custody(guala: Guala):
    need = guala._causal_inquiry_owner.active_need
    assert need is not None
    witness = next(
        value
        for value in guala._causal_inquiry_owner.witnesses
        if value.authority_receipt_sha256
        == need.witness_receipt_sha256
    )
    efferent = guala._embodied_vocal_body.capture_inquiry_efferent(
        need=need,
        witness=witness,
    )
    candidate, delivery = (
        guala._embodied_vocal_body.attempt_with_transient_delivery(
            efferent,
            w1_authority=guala._body_owned_w1_self_acoustic,
        )
    )
    custody = guala._embodied_vocal_body.open_motor_fragment_custody(
        candidate
    )
    return need, witness, candidate, custody, delivery


def _physical_snapshots(guala: Guala) -> dict[str, bytes]:
    return {
        "body": guala._embodied_vocal_body.snapshot_encoded(),
        "causal": (
            guala._embodiment_outcome_causal_owner.sequence_snapshot()
        ),
        "l5": (
            guala._w1_binaural_auditory_l5_owner.encoded_snapshot()
        ),
        "motif": (
            guala._auditory_w1_binaural_motif_owner.snapshot_encoded()
        ),
        "world": guala._embodiment_world.encoded_snapshot(),
    }


def test_request_one_failure_discards_before_publication_and_rolls_back_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guala = _runtime(monkeypatch)
    try:
        _seed_held_thing_and_inquiry(guala)
        owner = _owner(guala)
        empty_state = owner.snapshot_encoded()
        physical_before = _physical_snapshots(guala)
        need, witness, candidate, custody, delivery = (
            _candidate_custody(guala)
        )

        prepared = owner.prepare(
            need=need,
            witness=witness,
            candidate=candidate,
            motor_custody=custody,
        )
        assert prepared.record.program == custody.program
        assert prepared.record.command_graph_sha256 == (
            custody.command_graph_sha256
        )
        assert prepared.record.witness_source_time_start == (
            witness.source_time_start
        )
        assert prepared.record.witness_source_time_end == (
            witness.source_time_end
        )
        assert prepared.record.witness_authority_receipt_sha256 == (
            witness.authority_receipt_sha256
        )
        assert prepared.record.witness_settlement_receipt_sha256 == (
            witness.settlement_receipt_sha256
        )
        assert prepared.record.candidate_w1_mount_receipt_sha256 == (
            candidate.w1_mount_receipt_sha256
        )
        assert prepared.record.candidate_recurrent_q_receipt_sha256 == (
            candidate.recurrent_q_receipt_sha256
        )
        assert prepared.record.world_before_receipt_sha256 == (
            custody.world_before_receipt_sha256
        )
        assert prepared.record.world_after_receipt_sha256 == (
            custody.world_after_receipt_sha256
        )
        assert owner.status()["pending_count"] == 0
        with pytest.raises(RuntimeError, match="cannot snapshot"):
            owner.snapshot_encoded()

        owner.discard(prepared)
        assert owner.snapshot_encoded() == empty_state
        assert owner.status()["retained_raw_media_bytes"] == 0
        assert delivery not in owner.snapshot_encoded()

        prepared = owner.prepare(
            need=need,
            witness=witness,
            candidate=candidate,
            motor_custody=custody,
        )
        commit_undo = owner.commit(prepared)
        assert owner.pending == commit_undo.record
        owner.rollback_commit(commit_undo)
        assert owner.snapshot_encoded() == empty_state

        guala._embodied_vocal_body.rollback_candidate(
            candidate,
            w1_authority=guala._body_owned_w1_self_acoustic,
        )
        assert _physical_snapshots(guala) == physical_before
    finally:
        guala.shutdown()


def test_committed_custody_survives_body_finalize_and_cold_restore_then_consumes_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guala = _runtime(monkeypatch)
    try:
        _seed_held_thing_and_inquiry(guala)
        owner = _owner(guala)
        need, witness, candidate, custody, delivery = (
            _candidate_custody(guala)
        )
        prepared = owner.prepare(
            need=need,
            witness=witness,
            candidate=candidate,
            motor_custody=custody,
        )
        capability = prepared.client_capability
        commit_undo = owner.commit(prepared)
        with pytest.raises(RuntimeError, match="cannot snapshot"):
            owner.snapshot_encoded()
        owner.finalize_commit(commit_undo)

        guala._embodied_vocal_body.finalize_candidate(candidate)
        assert guala._embodied_vocal_body.status()["live_candidate"] == 0
        encoded = owner.snapshot_encoded()
        assert delivery not in encoded
        assert len(encoded) <= STATE_CAPACITY

        restored = _owner(guala)
        restored.restore_encoded(encoded)
        assert restored.snapshot_encoded() == encoded
        typed = restored.open_pending_custody(capability)
        restored.verify_restored_custody(typed)
        assert typed.program == custody.program
        assert typed.command_graph_sha256 == custody.command_graph_sha256
        assert typed.pending_authority_receipt_sha256 == (
            prepared.record.authority_receipt_sha256
        )
        assert typed.witness_source_time_start == witness.source_time_start
        assert typed.witness_source_time_end == witness.source_time_end

        consume = restored.prepare_consume(capability)
        consume_undo = restored.commit_consume(consume)
        with pytest.raises(ValueError, match="not available"):
            restored.open_pending_custody(capability)
        restored.rollback_consume(consume_undo)
        restored.verify_restored_custody(
            restored.open_pending_custody(capability)
        )

        consume = restored.prepare_consume(capability)
        consume_undo = restored.commit_consume(consume)
        restored.finalize_consume(consume_undo)
        with pytest.raises(ValueError, match="not available"):
            restored.open_pending_custody(capability)
        with pytest.raises(
            ValueError,
            match="cannot be consumed",
        ):
            restored.prepare_consume(capability)

        empty_state = restored.snapshot_encoded()
        empty_restored = _owner(guala)
        empty_restored.restore_encoded(empty_state)
        assert empty_restored.pending is None
        assert empty_restored.snapshot_encoded() == empty_state
    finally:
        guala.shutdown()


def test_capacity_capability_and_state_hmac_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guala = _runtime(monkeypatch)
    candidate = None
    try:
        _seed_held_thing_and_inquiry(guala)
        owner = _owner(guala)
        need, witness, candidate, custody, _delivery = (
            _candidate_custody(guala)
        )
        prepared = owner.prepare(
            need=need,
            witness=witness,
            candidate=candidate,
            motor_custody=custody,
        )
        capability = prepared.client_capability
        undo = owner.commit(prepared)
        owner.finalize_commit(undo)
        guala._embodied_vocal_body.finalize_candidate(candidate)
        candidate = None

        with pytest.raises(
            PendingBodyOwnedVocalConsequenceCapacityError,
            match="capacity one",
        ):
            owner.prepare(
                need=need,
                witness=witness,
                candidate=prepared.record,  # type: ignore[arg-type]
                motor_custody=custody,
            )

        forged = PendingBodyOwnedVocalClientCapability(
            opaque_token="0" * 64,
            authority_hmac_sha256=capability.authority_hmac_sha256,
            authority_receipt_sha256=(
                capability.authority_receipt_sha256
            ),
        )
        with pytest.raises(ValueError, match="capability changed"):
            owner.open_pending_custody(forged)

        raw = json.loads(owner.snapshot_encoded().decode("utf-8"))
        raw["body"]["pending"]["candidate_sample_count"] += 1
        tampered = json.dumps(
            raw,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        with pytest.raises(ValueError, match="state HMAC changed"):
            _owner(guala).restore_encoded(tampered)
    finally:
        if candidate is not None:
            guala._embodied_vocal_body.rollback_candidate(
                candidate,
                w1_authority=guala._body_owned_w1_self_acoustic,
            )
        guala.shutdown()
