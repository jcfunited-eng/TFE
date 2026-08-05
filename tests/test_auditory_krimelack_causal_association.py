from __future__ import annotations

import json
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AuditoryKrimelackAssociationState,
    AuditoryKrimelackCausalAssociationOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    bind_auditory_krimelack_causal_occurrence,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AuditoryKrimelackStreamOwner,
    AuditoryKrimelackStreamState,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from tests.test_auditory_krimelack_causal_occurrence import (
    _causal,
    _heard_field,
    _recognition,
    _stream,
    causal_occurrence_evidence,
)


AUTHORITY_KEY = b"auditory-causal-association-test-key-v1"


def _owner(**values) -> AuditoryKrimelackCausalAssociationOwner:
    return AuditoryKrimelackCausalAssociationOwner(
        authority_key=AUTHORITY_KEY,
        log_event=lambda *_args, **_kwargs: None,
        **values,
    )


def _occurrence(
    auditory,
    causal,
    stream,
    recognition,
):
    return bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )


def _repeated_occurrences(causal_occurrence_evidence):
    built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    first = _occurrence(
        auditory,
        causal,
        stream,
        recognition,
    )
    repeated_causal = _causal(built, routing_chis=(11, 29))
    repeated_stream = _stream(auditory, repeated_causal)
    repeated_recognition = _recognition(
        auditory,
        repeated_stream,
    )
    second = _occurrence(
        auditory,
        repeated_causal,
        repeated_stream,
        repeated_recognition,
    )
    assert first.occurrence_id != second.occurrence_id
    assert first.association_id == second.association_id
    return first, second


def test_two_distinct_exact_experiences_are_required_for_admission(
    causal_occurrence_evidence,
) -> None:
    first, second = _repeated_occurrences(
        causal_occurrence_evidence
    )
    owner = _owner()

    initial = owner.admit(first)
    observed_once = owner.observe(first)
    replay = owner.observe(first)
    before_confirmation = owner.admit(first)
    confirmed = owner.observe(second)
    admitted = owner.admit(second)

    assert initial.state is AuditoryKrimelackAssociationState.UNKNOWN
    assert observed_once.state is (
        AuditoryKrimelackAssociationState.UNCONFIRMED
    )
    assert observed_once.distinct_occurrences == 1
    assert replay.repeated is True
    assert replay.distinct_occurrences == 1
    assert before_confirmation.state is (
        AuditoryKrimelackAssociationState.UNCONFIRMED
    )
    assert before_confirmation.admission is None
    assert confirmed.state is AuditoryKrimelackAssociationState.CONFIRMED
    assert confirmed.distinct_occurrences == 2
    assert admitted.state is AuditoryKrimelackAssociationState.ADMITTED
    assert admitted.admission is not None
    admitted.verify(AUTHORITY_KEY)
    admitted.admission.verify(AUTHORITY_KEY)
    assert admitted.admission.reinforcement_occurrence_ids == (
        first.occurrence_id,
        second.occurrence_id,
    )
    assert admitted.admission.world_witnesses == tuple(
        value.causal_witness for value in second.components
    )


def test_deliberation_admission_contains_no_label_transcript_or_action(
    causal_occurrence_evidence,
) -> None:
    first, second = _repeated_occurrences(
        causal_occurrence_evidence
    )
    owner = _owner()
    owner.observe(first)
    owner.observe(second)
    decision = owner.admit(second)
    assert decision.admission is not None
    encoded = json.dumps(
        decision.admission.as_record(AUTHORITY_KEY),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    assert "hello guala" not in encoded
    assert "tutor_label" not in encoded
    assert "unicode_scalars" not in encoded
    assert '"action"' not in encoded
    assert not hasattr(decision.admission, "action")


def test_unobserved_conflict_and_learned_ambiguity_fail_closed(
    causal_occurrence_evidence,
) -> None:
    _built, tutor, _causal_value, _stream_value, _recognition_value = (
        causal_occurrence_evidence
    )
    first, second = _repeated_occurrences(
        causal_occurrence_evidence
    )
    conflict_built, conflict_auditory = _heard_field(
        assembly_id="auditory-association-conflict",
        anchor=Fraction(14_000),
        touch_observed=True,
    )
    conflict_causal = _causal(conflict_built)
    conflict_stream = _stream(conflict_auditory, conflict_causal)
    hearing = AuditoryKrimelackStreamOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    learned = hearing.teach(tutor, tutor_label="hello guala")
    conflict_recognition = hearing.advance(
        conflict_auditory,
        conflict_stream,
    )
    assert conflict_recognition.state is (
        AuditoryKrimelackStreamState.UNIQUE
    )
    assert conflict_recognition.selected_kind_id == learned.kind_id
    conflict = _occurrence(
        conflict_auditory,
        conflict_causal,
        conflict_stream,
        conflict_recognition,
    )
    assert conflict.kind_id == first.kind_id
    assert conflict.association_id != first.association_id

    owner = _owner()
    owner.observe(first)
    owner.observe(second)
    rejected = owner.admit(conflict)
    ambiguous_observation = owner.observe(conflict)
    ambiguous = owner.admit(second)

    assert rejected.state is (
        AuditoryKrimelackAssociationState.CONFLICTING
    )
    assert rejected.admission is None
    assert ambiguous_observation.state is (
        AuditoryKrimelackAssociationState.AMBIGUOUS
    )
    assert ambiguous_observation.variant_count == 2
    assert ambiguous.state is (
        AuditoryKrimelackAssociationState.AMBIGUOUS
    )
    assert ambiguous.admission is None


def test_confirmed_association_cold_restores_with_exact_admission(
    causal_occurrence_evidence,
) -> None:
    first, second = _repeated_occurrences(
        causal_occurrence_evidence
    )
    owner = _owner()
    owner.observe(first)
    owner.observe(second)
    snapshot = owner.encoded_snapshot()

    restored = _owner()
    restored.restore_encoded(snapshot)
    decision = restored.admit(second)

    assert restored.encoded_snapshot() == snapshot
    assert decision.state is (
        AuditoryKrimelackAssociationState.ADMITTED
    )
    assert decision.admission is not None
    decision.admission.verify(AUTHORITY_KEY)
    assert restored.status()["states"]["confirmed"] == 1


def test_changed_persistence_hmac_is_rejected(
    causal_occurrence_evidence,
) -> None:
    first, _second = _repeated_occurrences(
        causal_occurrence_evidence
    )
    owner = _owner()
    owner.observe(first)
    snapshot = owner.encoded_snapshot()
    changed = dict(snapshot)
    changed["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="HMAC changed"):
        _owner().restore_encoded(changed)


def test_state_capacity_failure_does_not_partially_grow(
    causal_occurrence_evidence,
) -> None:
    first, second = _repeated_occurrences(
        causal_occurrence_evidence
    )
    first_size = len(json.dumps(first.as_record()))
    owner = _owner(
        encoded_state_capacity=first_size + 32_768,
    )
    owner.observe(first)
    before = owner.encoded_snapshot()

    with pytest.raises(RuntimeError, match="state capacity is full"):
        owner.observe(second)

    assert owner.encoded_snapshot() == before
    assert owner.admit(second).state is (
        AuditoryKrimelackAssociationState.UNCONFIRMED
    )
