from __future__ import annotations

from copy import deepcopy

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_krimelack_grounded_composition import (
    AuditoryKrimelackGroundedCompositionOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_grounded_referent import (
    AuditoryKrimelackGroundedReferentOwner,
)
from tests.test_auditory_krimelack_causal_association import (
    AUTHORITY_KEY,
)
from tests.test_auditory_krimelack_grounded_referent import (
    _confirmed_admission,
)


def _owner(**values):
    return AuditoryKrimelackGroundedCompositionOwner(
        authority_key=AUTHORITY_KEY,
        log_event=lambda *_args, **_kwargs: None,
        **values,
    )


def _grounding(left, right):
    owner = AuditoryKrimelackGroundedReferentOwner(
        authority_key=AUTHORITY_KEY,
        log_event=lambda *_args, **_kwargs: None,
    )
    assert owner.observe(left) is True
    assert owner.observe(right) is True
    learned = owner.learn()
    assert learned.state == "grounded"
    assert learned.construction is not None
    return learned.construction


@pytest.fixture(scope="module")
def ordered_grounded_pairs():
    left_first, left_second = _confirmed_admission(
        name="composition-left",
        anchor=30_000,
        waveform_variant=0,
        touch_values=(-0.5, -0.5),
        return_admission_pair=True,
    )
    right_first, right_second = _confirmed_admission(
        name="composition-right",
        anchor=31_000,
        waveform_variant=1,
        touch_values=(0.75, 0.25),
        return_admission_pair=True,
    )
    assert left_first.kind_id == left_second.kind_id
    assert right_first.kind_id == right_second.kind_id
    assert left_first.kind_id != right_first.kind_id
    grounding = _grounding(left_second, right_second)
    return (
        grounding,
        left_first,
        left_second,
        right_first,
        right_second,
    )


def _confirmed_owner(ordered_grounded_pairs):
    (
        grounding,
        left_first,
        left_second,
        right_first,
        right_second,
    ) = ordered_grounded_pairs
    owner = _owner()
    owner.observe(
        grounding=grounding,
        left=left_first,
        right=right_first,
    )
    owner.observe(
        grounding=grounding,
        left=left_second,
        right=right_second,
    )
    return owner


def test_two_distinct_lived_orders_are_required_and_replay_is_inert(
    ordered_grounded_pairs,
) -> None:
    (
        grounding,
        left_first,
        left_second,
        right_first,
        right_second,
    ) = ordered_grounded_pairs
    owner = _owner()

    first = owner.observe(
        grounding=grounding,
        left=left_first,
        right=right_first,
    )
    before_replay = owner.encoded_snapshot()
    replay = owner.observe(
        grounding=grounding,
        left=left_first,
        right=right_first,
    )
    after_replay = owner.encoded_snapshot()
    unresolved = owner.resolve(
        grounding_construction_id=grounding.construction_id,
        left_kind_id=left_first.kind_id,
        right_kind_id=right_first.kind_id,
    )
    second = owner.observe(
        grounding=grounding,
        left=left_second,
        right=right_second,
    )
    resolved = owner.resolve(
        grounding_construction_id=grounding.construction_id,
        left_kind_id=left_first.kind_id,
        right_kind_id=right_first.kind_id,
    )

    assert first.state == "unconfirmed"
    assert first.distinct_episodes == 1
    assert replay.repeated is True
    assert replay.distinct_episodes == 1
    assert after_replay == before_replay
    assert owner.encoded_snapshot() != before_replay
    assert unresolved.state == "unconfirmed"
    assert unresolved.composition is None
    assert second.state == "confirmed"
    assert second.distinct_episodes == 2
    assert resolved.state == "confirmed"
    assert resolved.composition is not None
    resolved.composition.verify(AUTHORITY_KEY)


def test_confirmed_composition_retains_full_grounded_dsf_field(
    ordered_grounded_pairs,
) -> None:
    grounding, left, _left_second, right, _right_second = (
        ordered_grounded_pairs
    )
    owner = _confirmed_owner(ordered_grounded_pairs)
    resolution = owner.resolve(
        grounding_construction_id=grounding.construction_id,
        left_kind_id=left.kind_id,
        right_kind_id=right.kind_id,
    )

    assert resolution.composition is not None
    alternatives = resolution.composition.grounding.alternatives
    assert len(alternatives) == 2
    for alternative in alternatives:
        assert alternative.referent_value
        for field_tuple in alternative.referent_value["field_tuples"]:
            assert tuple(
                name for name, _value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER


def test_reversed_order_is_a_distinct_unknown_identity(
    ordered_grounded_pairs,
) -> None:
    grounding, left, _left_second, right, _right_second = (
        ordered_grounded_pairs
    )
    owner = _confirmed_owner(ordered_grounded_pairs)

    reverse = owner.resolve(
        grounding_construction_id=grounding.construction_id,
        left_kind_id=right.kind_id,
        right_kind_id=left.kind_id,
    )

    assert reverse.state == "unknown"
    assert reverse.reason == "ordered_grounded_composition_absent"
    assert reverse.composition is None


def test_overlapping_occurrences_have_no_exact_causal_order() -> None:
    left, _left_second = _confirmed_admission(
        name="composition-overlap-left",
        anchor=32_000,
        waveform_variant=0,
        touch_values=(-0.5, -0.5),
        return_admission_pair=True,
    )
    right, right_second = _confirmed_admission(
        name="composition-overlap-right",
        anchor=32_000,
        waveform_variant=1,
        touch_values=(0.75, 0.25),
        return_admission_pair=True,
    )
    grounding = _grounding(left, right_second)

    with pytest.raises(
        ValueError,
        match="no exact causal order",
    ):
        _owner().observe(
            grounding=grounding,
            left=left,
            right=right,
        )


def test_ungrounded_kind_cannot_enter_composition(
    ordered_grounded_pairs,
) -> None:
    grounding, left, _left_second, _right, _right_second = (
        ordered_grounded_pairs
    )
    outside, _outside_second = _confirmed_admission(
        name="composition-outside",
        anchor=33_000,
        waveform_variant=2,
        touch_values=(0.5, -0.5),
        return_admission_pair=True,
    )
    assert all(
        outside.kind_id != value.kind_id
        for value in grounding.alternatives
    )

    with pytest.raises(ValueError, match="kind is not grounded"):
        _owner().observe(
            grounding=grounding,
            left=left,
            right=outside,
        )


def test_composition_persistence_is_exact_authenticated_and_label_free(
    ordered_grounded_pairs,
) -> None:
    grounding, left, _left_second, right, _right_second = (
        ordered_grounded_pairs
    )
    owner = _confirmed_owner(ordered_grounded_pairs)
    snapshot = owner.encoded_snapshot()
    encoded = str(snapshot)
    restored = _owner()
    restored.restore_encoded(snapshot)

    assert restored.encoded_snapshot() == snapshot
    assert restored.resolve(
        grounding_construction_id=grounding.construction_id,
        left_kind_id=left.kind_id,
        right_kind_id=right.kind_id,
    ) == owner.resolve(
        grounding_construction_id=grounding.construction_id,
        left_kind_id=left.kind_id,
        right_kind_id=right.kind_id,
    )
    assert "tutor_label" not in encoded
    assert "hello" not in encoded
    assert "reply" not in encoded
    assert "action" not in encoded

    changed = deepcopy(snapshot)
    changed["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="state HMAC changed"):
        _owner().restore_encoded(changed)
