from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AuditoryKrimelackAssociationState,
    AuditoryKrimelackCausalAssociationOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    bind_auditory_krimelack_causal_occurrence,
)
from dsf_ai_service.substrate.auditory_krimelack_grounded_referent import (
    AuditoryKrimelackGroundedReferentOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AuditoryKrimelackStreamOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from tests.test_auditory_krimelack_causal_association import (
    AUTHORITY_KEY,
)
from tests.test_auditory_krimelack_causal_occurrence import (
    _causal,
    _heard_field,
    _stream,
)


def _owner(**values):
    return AuditoryKrimelackGroundedReferentOwner(
        authority_key=AUTHORITY_KEY,
        log_event=lambda *_args, **_kwargs: None,
        **values,
    )


def _confirmed_admission(
    *,
    name: str,
    anchor: int,
    waveform_variant: int,
    touch_values: tuple[float, float],
    hearing_owner=None,
    teach_hearing: bool = False,
    return_admission_pair: bool = False,
):
    built, auditory = _heard_field(
        assembly_id=f"grounded-{name}",
        anchor=Fraction(anchor),
        touch_observed=True,
        touch_values=touch_values,
        waveform_variant=waveform_variant,
    )
    causal = _causal(built)
    stream = _stream(auditory, causal)
    hearing = (
        hearing_owner
        if hearing_owner is not None
        else AuditoryKrimelackStreamOwner(
            log_event=lambda *_args, **_kwargs: None,
            tutor_authority=AuditoryTutorAuthority.unrequired(),
        )
    )
    if hearing_owner is None or teach_hearing:
        hearing.teach(auditory, tutor_label=f"form-{name}")
    recognition = hearing.advance(auditory, stream)
    first = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )
    repeated_causal = _causal(
        built,
        routing_chis=(anchor % 31 + 1,),
    )
    repeated_stream = _stream(auditory, repeated_causal)
    hearing.close_stream(stream.stream_id)
    repeated_recognition = hearing.advance(auditory, repeated_stream)
    second = bind_auditory_krimelack_causal_occurrence(
        recognition=repeated_recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(repeated_stream,),
        causal_settlements=(repeated_causal,),
    )
    association = AuditoryKrimelackCausalAssociationOwner(
        authority_key=AUTHORITY_KEY,
        log_event=lambda *_args, **_kwargs: None,
    )
    association.observe(first)
    association.observe(second)
    first_decision = association.admit(first)
    decision = association.admit(second)
    assert first_decision.state is (
        AuditoryKrimelackAssociationState.ADMITTED
    )
    assert decision.state is AuditoryKrimelackAssociationState.ADMITTED
    assert first_decision.admission is not None
    assert decision.admission is not None
    if return_admission_pair:
        return first_decision.admission, decision.admission
    return decision.admission


@pytest.fixture(scope="module")
def grounded_contrast():
    first = _confirmed_admission(
        name="first",
        anchor=15_000,
        waveform_variant=0,
        touch_values=(-0.5, -0.5),
    )
    second = _confirmed_admission(
        name="second",
        anchor=16_000,
        waveform_variant=1,
        touch_values=(0.75, 0.25),
    )
    assert first.kind_id != second.kind_id
    return first, second


def test_unique_non_auditory_controlled_contrast_grounds_two_kinds(
    grounded_contrast,
) -> None:
    first, second = grounded_contrast
    owner = _owner()

    assert owner.observe(first) is True
    assert owner.observe(second) is True
    learned = owner.learn()
    first_resolution = owner.resolve(first.kind_id)
    second_resolution = owner.resolve(second.kind_id)

    assert learned.state == "grounded"
    assert learned.construction is not None
    assert learned.construction.referent_root.startswith(
        "sense:touch:substream:"
    )
    assert first_resolution.state == "grounded"
    assert second_resolution.state == "grounded"
    assert first_resolution.referent_value != (
        second_resolution.referent_value
    )
    assert first_resolution.construction_id == (
        second_resolution.construction_id
    )
    for resolution in (first_resolution, second_resolution):
        assert resolution.referent_value is not None
        for field_tuple in resolution.referent_value["field_tuples"]:
            assert tuple(
                name for name, _value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER


def test_sound_cannot_ground_itself_without_non_auditory_contrast() -> None:
    first = _confirmed_admission(
        name="sound-only-first",
        anchor=17_000,
        waveform_variant=0,
        touch_values=(-0.25, 0.5),
    )
    second = _confirmed_admission(
        name="sound-only-second",
        anchor=18_000,
        waveform_variant=1,
        touch_values=(-0.25, 0.5),
    )
    owner = _owner()
    owner.observe(first)
    owner.observe(second)

    learned = owner.learn()

    assert learned.state == "unknown"
    assert learned.reason == "non_auditory_contrast_absent"
    assert learned.construction is None


def test_within_kind_changed_referent_is_conflicting() -> None:
    shared_hearing = AuditoryKrimelackStreamOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    first = _confirmed_admission(
        name="ambiguous-first",
        anchor=19_000,
        waveform_variant=0,
        touch_values=(-0.5, -0.5),
        hearing_owner=shared_hearing,
        teach_hearing=True,
    )
    second = _confirmed_admission(
        name="ambiguous-second",
        anchor=20_000,
        waveform_variant=1,
        touch_values=(0.75, 0.25),
    )
    second_record = second.current_occurrence.as_record()
    assert second_record
    owner = _owner()
    owner.observe(first)
    owner.observe(second)
    learned = owner.learn()
    assert learned.state == "grounded"

    third = _confirmed_admission(
        name="ambiguous-third",
        anchor=21_000,
        waveform_variant=0,
        touch_values=(0.5, -0.5),
        hearing_owner=shared_hearing,
    )
    assert third.kind_id == first.kind_id
    owner.observe(third)

    conflicted = owner.learn()
    assert conflicted.state == "conflicting"
    assert conflicted.construction is None


def test_replayed_admission_does_not_grow_curriculum(
    grounded_contrast,
) -> None:
    first, _second = grounded_contrast
    owner = _owner()

    assert owner.observe(first) is True
    before = owner.encoded_snapshot()
    assert owner.observe(first) is False

    assert owner.encoded_snapshot() == before
    assert owner.status()["episode_count"] == 1


def test_grounding_state_is_label_free_and_cold_exact(
    grounded_contrast,
) -> None:
    first, second = grounded_contrast
    owner = _owner()
    owner.observe(first)
    owner.observe(second)
    snapshot = owner.encoded_snapshot()
    encoded = str(snapshot)

    assert "hello guala" not in encoded
    assert "tutor_label" not in encoded
    restored = _owner()
    restored.restore_encoded(snapshot)

    assert restored.encoded_snapshot() == snapshot
    assert restored.resolve(first.kind_id) == owner.resolve(first.kind_id)
    assert restored.resolve(second.kind_id) == owner.resolve(
        second.kind_id
    )


def test_changed_grounding_persistence_is_rejected(
    grounded_contrast,
) -> None:
    first, _second = grounded_contrast
    owner = _owner()
    owner.observe(first)
    snapshot = owner.encoded_snapshot()
    changed = dict(snapshot)
    changed["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="state HMAC changed"):
        _owner().restore_encoded(changed)
