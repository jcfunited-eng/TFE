from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest

from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AuditoryKrimelackAssociationState,
    AuditoryKrimelackCausalAssociationOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    bind_auditory_krimelack_causal_occurrence,
)
from dsf_ai_service.substrate.auditory_krimelack_deliberation_adapter import (
    AuditoryKrimelackDeliberationAdapterOwner,
    AuditoryKrimelackDeliberationIntake,
)
from dsf_ai_service.substrate.causal_deliberation import (
    CausalDeliberation,
)
from tests.test_auditory_krimelack_causal_association import (
    AUTHORITY_KEY,
)
from tests.test_auditory_krimelack_causal_occurrence import (
    _causal,
    _recognition,
    _stream,
    causal_occurrence_evidence,
)


DELIBERATION_KEY = b"existing-causal-deliberation-test-key-v1"


def _association_owner():
    return AuditoryKrimelackCausalAssociationOwner(
        authority_key=AUTHORITY_KEY,
        log_event=lambda *_args, **_kwargs: None,
    )


def _adapter(deliberation=None):
    return AuditoryKrimelackDeliberationAdapterOwner(
        authority_key=AUTHORITY_KEY,
        deliberation=(
            deliberation
            if deliberation is not None
            else CausalDeliberation(
                authority_key=DELIBERATION_KEY,
            )
        ),
        log_event=lambda *_args, **_kwargs: None,
    )


def _confirmed_admission(causal_occurrence_evidence):
    built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    first = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )
    repeated_causal = _causal(built, routing_chis=(11, 29))
    repeated_stream = _stream(auditory, repeated_causal)
    repeated_recognition = _recognition(
        auditory,
        repeated_stream,
    )
    second = bind_auditory_krimelack_causal_occurrence(
        recognition=repeated_recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(repeated_stream,),
        causal_settlements=(repeated_causal,),
    )
    association = _association_owner()
    association.observe(first)
    association.observe(second)
    decision = association.admit(second)
    assert decision.state is AuditoryKrimelackAssociationState.ADMITTED
    assert decision.admission is not None
    return decision.admission, repeated_causal, first


def test_confirmed_admission_enters_existing_deliberation_full_field(
    causal_occurrence_evidence,
) -> None:
    admission, current_causal, _first = _confirmed_admission(
        causal_occurrence_evidence
    )
    deliberation = CausalDeliberation(
        authority_key=DELIBERATION_KEY,
    )
    adapter = _adapter(deliberation)

    result = adapter.start(
        admission=admission,
        causal_settlements=(current_causal,),
        admitted_evidence=(),
    )

    result.intake.verify(AUTHORITY_KEY)
    assert result.turn.status == "stopped"
    assert result.turn.stop_reason == "action_unknown"
    assert result.turn.action is None
    assert result.intake.action_receipt_sha256 is None
    assert result.intake.world_witness_receipts == (
        current_causal.authority_receipt_sha256,
    )
    assert result.intake.current_world_receipt_sha256 == (
        current_causal.authority_receipt_sha256
    )
    assert deliberation.status()["terminal_reason"] == "action_unknown"


def test_unconfirmed_or_bare_occurrence_cannot_enter_deliberation(
    causal_occurrence_evidence,
) -> None:
    admission, current_causal, first = _confirmed_admission(
        causal_occurrence_evidence
    )
    owner = _association_owner()
    owner.observe(first)
    unconfirmed = owner.admit(first)
    assert unconfirmed.state is (
        AuditoryKrimelackAssociationState.UNCONFIRMED
    )
    assert unconfirmed.admission is None
    adapter = _adapter()

    with pytest.raises(
        TypeError,
        match="requires confirmed admission",
    ):
        adapter.start(
            admission=unconfirmed.admission,
            causal_settlements=(current_causal,),
            admitted_evidence=(),
        )
    with pytest.raises(
        TypeError,
        match="requires confirmed admission",
    ):
        adapter.start(
            admission=first,
            causal_settlements=(current_causal,),
            admitted_evidence=(),
        )
    assert admission.current_occurrence.kind_id == first.kind_id


def test_forged_admission_stops_before_deliberation_mutates(
    causal_occurrence_evidence,
) -> None:
    admission, current_causal, _first = _confirmed_admission(
        causal_occurrence_evidence
    )
    forged = replace(
        admission,
        authority_hmac_sha256="0" * 64,
    )
    deliberation = CausalDeliberation(
        authority_key=DELIBERATION_KEY,
    )
    adapter = _adapter(deliberation)

    with pytest.raises(ValueError, match="admission HMAC changed"):
        adapter.start(
            admission=forged,
            causal_settlements=(current_causal,),
            admitted_evidence=(),
        )

    assert adapter.latest_intake() is None
    assert deliberation.status()["terminal_reason"] is None


def test_mismatched_live_full_field_stops_before_deliberation(
    causal_occurrence_evidence,
) -> None:
    _built, _auditory, original_causal, _stream_value, _recognition_value = (
        causal_occurrence_evidence
    )
    admission, current_causal, _first = _confirmed_admission(
        causal_occurrence_evidence
    )
    assert original_causal.authority_receipt_sha256 != (
        current_causal.authority_receipt_sha256
    )
    deliberation = CausalDeliberation(
        authority_key=DELIBERATION_KEY,
    )
    adapter = _adapter(deliberation)

    with pytest.raises(
        ValueError,
        match="left its live full field",
    ):
        adapter.start(
            admission=admission,
            causal_settlements=(original_causal,),
            admitted_evidence=(),
        )

    assert adapter.latest_intake() is None
    assert deliberation.status()["terminal_reason"] is None


def test_adapter_cold_restores_complete_admission_provenance(
    causal_occurrence_evidence,
) -> None:
    admission, current_causal, _first = _confirmed_admission(
        causal_occurrence_evidence
    )
    adapter = _adapter()
    result = adapter.start(
        admission=admission,
        causal_settlements=(current_causal,),
        admitted_evidence=(),
    )
    snapshot = adapter.encoded_snapshot()

    restored = _adapter()
    restored.restore_encoded(snapshot)
    with patch.object(
        AuditoryKrimelackDeliberationIntake,
        "verify",
        side_effect=AssertionError(
            "verified immutable intake must not be reverified on read"
        ),
    ):
        latest = restored.latest_intake()

    assert latest == result.intake
    assert restored.encoded_snapshot() == snapshot
    assert latest is not None
    latest.verify(AUTHORITY_KEY)
    assert latest.admission.world_witnesses == (
        result.intake.admission.world_witnesses
    )


def test_changed_adapter_persistence_is_rejected(
    causal_occurrence_evidence,
) -> None:
    admission, current_causal, _first = _confirmed_admission(
        causal_occurrence_evidence
    )
    adapter = _adapter()
    adapter.start(
        admission=admission,
        causal_settlements=(current_causal,),
        admitted_evidence=(),
    )
    snapshot = adapter.encoded_snapshot()
    retained = adapter.latest_intake()
    changed = dict(snapshot)
    changed["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="state HMAC changed"):
        adapter.restore_encoded(changed)
    assert adapter.latest_intake() is retained
