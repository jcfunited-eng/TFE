from __future__ import annotations

import base64
import json
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_krimelack_causal_association import (
    AuditoryKrimelackAssociationState,
)
from dsf_ai_service.substrate.auditory_krimelack_cognition import (
    AUDITORY_KRIMELACK_COGNITION_ENVELOPE_SCHEMA,
    AuditoryKrimelackCognitionOwner,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AuditoryKrimelackStreamOwner,
    AuditoryKrimelackStreamState,
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


DELIBERATION_KEY = b"auditory-cognition-deliberation-key-v1"


def _owner(*, log_event=None, **values):
    return AuditoryKrimelackCognitionOwner(
        authority_key=AUTHORITY_KEY,
        deliberation_authority_key=DELIBERATION_KEY,
        log_event=(
            log_event
            if log_event is not None
            else lambda *_args, **_kwargs: None
        ),
        **values,
    )


def _recognized_pair(
    *,
    name: str,
    anchor: int,
    waveform_variant: int,
    touch_values: tuple[float, float],
):
    built, auditory = _heard_field(
        assembly_id=f"cognition-{name}",
        anchor=Fraction(anchor),
        waveform_variant=waveform_variant,
        touch_observed=True,
        touch_values=touch_values,
    )
    first_causal = _causal(built)
    first_stream = _stream(auditory, first_causal)
    hearing = AuditoryKrimelackStreamOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    # This creates the typed recognition test fixture.  The resulting
    # recognition and every cognition record are label-free.
    hearing.teach(auditory, tutor_label=f"fixture-{name}")
    first_recognition = hearing.advance(auditory, first_stream)
    second_causal = _causal(
        built,
        routing_chis=(anchor % 37 + 1,),
    )
    second_stream = _stream(auditory, second_causal)
    hearing.close_stream(first_stream.stream_id)
    second_recognition = hearing.advance(
        auditory,
        second_stream,
    )
    assert first_recognition.state is (
        AuditoryKrimelackStreamState.UNIQUE
    )
    assert second_recognition.state is (
        AuditoryKrimelackStreamState.UNIQUE
    )
    assert first_recognition.selected_kind_id == (
        second_recognition.selected_kind_id
    )
    return (
        (
            first_recognition,
            (auditory,),
            (first_stream,),
            (first_causal,),
        ),
        (
            second_recognition,
            (auditory,),
            (second_stream,),
            (second_causal,),
        ),
    )


def _advance(owner, evidence):
    recognition, auditory, streams, causal = evidence
    return owner.advance(
        recognition=recognition,
        auditory_experiences=auditory,
        stream_settlements=streams,
        causal_settlements=causal,
    )


@pytest.fixture(scope="module")
def exact_ordered_evidence():
    executor = start_exact_field_executor()
    executor.assert_healthy()
    try:
        left = _recognized_pair(
            name="left",
            anchor=40_000,
            waveform_variant=0,
            touch_values=(-0.5, -0.5),
        )
        right = _recognized_pair(
            name="right",
            anchor=41_000,
            waveform_variant=1,
            touch_values=(0.75, 0.25),
        )
        assert (
            left[0][0].selected_kind_id
            != right[0][0].selected_kind_id
        )
        yield left, right
    finally:
        stop_exact_field_executor()


def _run_grounded(owner, exact_ordered_evidence):
    left, right = exact_ordered_evidence
    left_first = _advance(owner, left[0])
    left_second = _advance(owner, left[1])
    left_replayed = _advance(owner, left[0])
    right_first = _advance(owner, right[0])
    right_second = _advance(owner, right[1])
    right_replayed = _advance(owner, right[0])
    assert left_first.decision.admission is None
    assert right_first.decision.admission is None
    for result in (
        left_second,
        left_replayed,
        right_second,
        right_replayed,
    ):
        assert result.decision.state is (
            AuditoryKrimelackAssociationState.ADMITTED
        )
        assert result.decision.admission is not None
        assert result.deliberation is not None
        assert result.deliberation.turn.status == "stopped"
        assert result.deliberation.turn.stop_reason == "action_unknown"
        assert result.deliberation.turn.action is None
    grounded = owner.current_grounding()
    assert grounded.state == "grounded"
    assert grounded.construction is not None
    return (
        grounded.construction,
        left_replayed.decision.admission,
        left_second.decision.admission,
        right_replayed.decision.admission,
        right_second.decision.admission,
    )


def test_advance_requires_recurrence_before_deliberation_and_grounding(
    exact_ordered_evidence,
) -> None:
    left, _right = exact_ordered_evidence
    owner = _owner()

    first = _advance(owner, left[0])
    second = _advance(owner, left[1])

    assert first.association.state is (
        AuditoryKrimelackAssociationState.UNCONFIRMED
    )
    assert first.decision.admission is None
    assert first.deliberation is None
    assert second.association.state is (
        AuditoryKrimelackAssociationState.CONFIRMED
    )
    assert second.decision.state is (
        AuditoryKrimelackAssociationState.ADMITTED
    )
    assert second.decision.admission is not None
    assert second.deliberation is not None
    assert second.grounding.state == "unknown"


def test_exact_chain_reaches_full_dsf_grounded_ordered_composition(
    exact_ordered_evidence,
) -> None:
    owner = _owner()
    (
        grounding,
        left_first,
        left_second,
        right_first,
        right_second,
    ) = _run_grounded(owner, exact_ordered_evidence)

    first = owner.compose(
        grounding=grounding,
        left=left_first,
        right=right_first,
    )
    second = owner.compose(
        grounding=grounding,
        left=left_second,
        right=right_second,
    )

    assert first.observation.state == "unconfirmed"
    assert first.resolution.state == "unconfirmed"
    assert second.observation.state == "confirmed"
    assert second.resolution.state == "confirmed"
    assert second.resolution.composition is not None
    for alternative in (
        second.resolution.composition.grounding.alternatives
    ):
        for field_tuple in alternative.referent_value["field_tuples"]:
            assert tuple(
                name for name, _value in field_tuple["fields"]
            ) == DSF_FIELD_ORDER


def test_advance_rolls_back_every_child_when_commit_event_fails(
    exact_ordered_evidence,
) -> None:
    left, _right = exact_ordered_evidence

    def fail_event(_event, **_fields):
        raise RuntimeError("event commit failed")

    owner = _owner(log_event=fail_event)
    before = owner.encoded_snapshot()

    with pytest.raises(RuntimeError, match="event commit failed"):
        _advance(owner, left[0])

    assert owner.encoded_snapshot() == before
    assert owner.status()["association"]["association_count"] == 0
    assert owner.status()["latest_deliberation_intake"] is False


def test_single_hmac_surface_cold_restores_exactly_and_rejects_change(
    exact_ordered_evidence,
) -> None:
    owner = _owner()
    (
        grounding,
        left_first,
        left_second,
        right_first,
        right_second,
    ) = _run_grounded(owner, exact_ordered_evidence)
    owner.compose(
        grounding=grounding,
        left=left_first,
        right=right_first,
    )
    owner.compose(
        grounding=grounding,
        left=left_second,
        right=right_second,
    )
    snapshot = owner.encoded_snapshot()
    assert set(snapshot) == {
        "authority_hmac_sha256",
        "payload_base64",
        "schema",
        "sha256",
    }
    assert snapshot["schema"] == (
        AUDITORY_KRIMELACK_COGNITION_ENVELOPE_SCHEMA
    )

    restored = _owner()
    restored.restore_encoded(snapshot)
    assert restored.encoded_snapshot() == snapshot
    assert restored.status() == owner.status()

    before = restored.encoded_snapshot()
    changed = dict(snapshot)
    changed["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="state HMAC changed"):
        restored.restore_encoded(changed)
    assert restored.encoded_snapshot() == before


def test_persisted_cognition_contains_no_text_meaning_or_reply_surface(
    exact_ordered_evidence,
) -> None:
    owner = _owner()
    _run_grounded(owner, exact_ordered_evidence)
    snapshot = owner.encoded_snapshot()
    root = json.loads(base64.b64decode(snapshot["payload_base64"]))
    records = [json.dumps(root, sort_keys=True)]
    records.extend(
        base64.b64decode(value["payload_base64"]).decode("utf-8")
        for key, value in root.items()
        if key not in {"encoded_state_capacity", "schema"}
    )
    encoded = "\n".join(records)

    assert "tutor_label" not in encoded
    assert "unicode_scalars" not in encoded
    assert "transcript" not in encoded
    assert '"reply"' not in encoded
    assert "fixture-left" not in encoded
    assert "fixture-right" not in encoded
