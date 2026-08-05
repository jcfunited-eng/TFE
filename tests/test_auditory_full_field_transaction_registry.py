from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.substrate.auditory_full_field_transaction_registry import (
    AuditoryFullFieldTransactionRegistry,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
    _digest,
)
from tests.test_w1_companion_vocal_experience import (
    _authorities,
    _pcm,
)


def _physical_mount():
    _world, _causal, _physical, companion = _authorities(
        lambda _value: None
    )
    prepared = companion.prepare(pcm_s16le=_pcm())
    mount = prepared.physical_mount
    receptor = mount.binaural_receptor_settlement
    assert receptor is not None
    return mount, receptor.ears[0].event


def _joint(mount, event, *, stream_id="stream-1", sequence=0):
    causal = mount.causal_settlement
    provisional = AuditoryStreamSettlementReceipt(
        stream_id=stream_id,
        sequence=sequence,
        first_sample_index=sequence * 960,
        sample_count=960,
        source_time_start=causal.source_time_start,
        source_time_end=causal.source_time_end,
        assembly_id=causal.assembly_id,
        transport_receipt_sha256="1" * 64,
        prior_transport_receipt_sha256=None,
        cochlear_receipt_sha256="2" * 64,
        prior_cochlear_state_receipt_sha256=None,
        auditory_l5_authority_receipt_sha256=(
            event.auditory_l5_authority_receipt_sha256
        ),
        causal_settlement_authority_receipt_sha256=(
            causal.authority_receipt_sha256
        ),
        authority_receipt_sha256="0" * 64,
    )
    result = replace(
        provisional,
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result.verify()
    return result


def _registry(**changes):
    values = {
        "max_streams": 2,
        "max_pending_per_stream": 2,
        "max_claims": 1,
    }
    values.update(changes)
    return AuditoryFullFieldTransactionRegistry(**values)


def test_full_field_transaction_claim_commit_and_rollback_are_atomic():
    mount, event = _physical_mount()
    registry = _registry()
    transaction = registry.stage(
        full_field_event=event,
        stream_settlement=_joint(mount, event),
        prepared_causal_settlement=mount.causal_settlement,
    )
    claim = registry.claim(transaction)
    claim.verify()

    assert registry.full_field_from_claim(claim) is event
    assert (
        registry.prepared_settlement_from_claim(claim)
        is mount.causal_settlement
    )
    registry.rollback_claim(claim)
    assert registry.status()["active_claims"] == 0
    assert registry.status()["pending_transactions"] == 1

    claim = registry.claim(transaction)
    callbacks = []
    registry.complete_claim(
        claim,
        commit_settlement=lambda: callbacks.append(
            mount.causal_settlement.authority_receipt_sha256
        ),
    )

    assert callbacks == [
        mount.causal_settlement.authority_receipt_sha256
    ]
    assert registry.status()["committed"] == 1
    assert registry.status()["pending_transactions"] == 0
    assert registry.authority_counts() == {
        "in_flight_full_field_claims": 0,
        "pending_full_field_transactions": 0,
    }


def test_full_field_transaction_refuses_gaps_capacity_and_claim_tamper():
    mount, event = _physical_mount()
    registry = _registry(max_streams=1)
    missing_zero = replace(
        _joint(mount, event),
        stream_id="missing-zero",
        sequence=1,
        first_sample_index=960,
        prior_transport_receipt_sha256="3" * 64,
        prior_cochlear_state_receipt_sha256="4" * 64,
        authority_receipt_sha256="0" * 64,
    )
    missing_zero = replace(
        missing_zero,
        authority_receipt_sha256=_digest(missing_zero.payload()),
    )
    missing_zero.verify()
    with pytest.raises(ValueError, match="sequence zero"):
        registry.stage(
            full_field_event=event,
            stream_settlement=missing_zero,
            prepared_causal_settlement=mount.causal_settlement,
        )

    transaction = registry.stage(
        full_field_event=event,
        stream_settlement=_joint(mount, event),
        prepared_causal_settlement=mount.causal_settlement,
    )
    with pytest.raises(RuntimeError, match="stream capacity"):
        registry.stage(
            full_field_event=event,
            stream_settlement=_joint(
                mount,
                event,
                stream_id="stream-2",
            ),
            prepared_causal_settlement=mount.causal_settlement,
        )
    claim = registry.claim(transaction)
    forged = replace(claim, claim_id="f" * 64)
    with pytest.raises(ValueError, match="claim is not live"):
        registry.verify_claim(forged)
    with pytest.raises(ValueError, match="cannot be discarded"):
        registry.discard(transaction)
    registry.rollback_claim(claim)
    registry.discard(transaction)
    assert registry.status()["discarded"] == 1


def test_full_field_transaction_has_no_classifier_surface():
    registry = _registry()
    status = registry.status()

    assert status["semantic_authority"] is False
    assert status["transcript_authority"] is False
    for forbidden in (
        "label",
        "word",
        "fingerprint",
        "candidate",
        "recognition",
        "reciprocity",
        "cell",
    ):
        assert forbidden not in repr(status).lower()
        assert not hasattr(registry, forbidden)
