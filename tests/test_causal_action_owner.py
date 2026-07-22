from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
from fractions import Fraction

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
    AuditoryIncrementalTerminalEvent,
    _event_payload,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AUDITORY_L5_SCHEMA,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECOGNITION_OPERATOR,
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.causal_action import (
    CausalActionOwner,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _built(name: str, values: tuple[Fraction, ...]):
    sample_count = 320
    capture = transduce_auditory_full_field(
        np.asarray(
            [float(values[index % len(values)]) for index in range(sample_count)],
            dtype=np.float64,
        ),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    ports = auditory_kernel_component_inputs(
        capture,
        source_anchor=Fraction(0),
    )
    assert len(capture.channels) == 16
    assert len(ports) == AUDITORY_KERNEL_COMPONENT_COUNT
    return build_six_sense_full_field(
        assembly_id=f"causal-action-test-{name}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(sample_count, REQUIRED_SAMPLE_RATE_HZ),
        observed_substreams={PhysicalSense.SOUND: ports},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )


def _settlement(
    *,
    name: str,
    label: str,
    values: tuple[Fraction, ...],
    reciprocity: AuditoryReciprocityOwner,
    teach: bool,
):
    built = _built(name, values)
    auditory = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="utterance")
    assert auditory is not None
    if teach:
        reciprocity.teach(
            auditory,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=label,
        )
    recognition = reciprocity.recognize(
        auditory,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
    )
    assert recognition.state.value == "unique"
    stream_id = f"stream-{name}"
    event_id = _digest({
        "source_sample_end": 320,
        "source_sample_start": 0,
        "stream_id": stream_id,
        "structural_fingerprint": auditory.structural_fingerprint,
    })
    transport = (_digest({"transport": name}),)
    cochlear = (_digest({"cochlear": name}),)
    joint = (_digest({"joint": name}),)
    payload = _event_payload(
        event_id=event_id,
        stream_id=stream_id,
        source_sample_start=0,
        source_sample_end=320,
        tutor_label=label,
        structural_fingerprint=auditory.structural_fingerprint,
        l5_authority_receipt_sha256=auditory.authority_receipt_sha256,
        transport_receipt_sha256s=transport,
        cochlear_receipt_sha256s=cochlear,
        joint_settlement_receipt_sha256s=joint,
        recognition_occurrence=recognition.occurrence,
        schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
        l5_schema=AUDITORY_L5_SCHEMA,
        reciprocity_snapshot_schema=AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
    )
    terminal = AuditoryIncrementalTerminalEvent(
        event_id=event_id,
        stream_id=stream_id,
        source_sample_start=0,
        source_sample_end=320,
        tutor_label=label,
        structural_fingerprint=auditory.structural_fingerprint,
        l5_authority_receipt_sha256=auditory.authority_receipt_sha256,
        transport_receipt_sha256s=transport,
        cochlear_receipt_sha256s=cochlear,
        joint_settlement_receipt_sha256s=joint,
        schema=AUDITORY_INCREMENTAL_EVENT_SCHEMA_V3,
        authority_receipt_sha256=_digest(payload),
        recognition_occurrence=recognition.occurrence,
        l5_schema=AUDITORY_L5_SCHEMA,
        reciprocity_snapshot_schema=AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
        recognition_operator=AUDITORY_RECOGNITION_OPERATOR,
    )
    terminal.verify()
    settled = []
    owner = ExactCausalExperienceOwner(
        on_settlement=settled.append,
        log_event=lambda *_args, **_kwargs: None,
    )
    result = owner.settle(
        built,
        recognized_language_record=terminal.as_record(),
        routing_chis=(3, 1, 3),
        source_tags=("auditory:unresolved_source",),
    )
    assert settled == [result]
    result.verify()
    return result


@pytest.fixture
def learned_experiences():
    reciprocity = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    trigger = _settlement(
        name="trigger",
        label="hello guala",
        values=(Fraction(1, 8), Fraction(1, 4), Fraction(3, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    action = _settlement(
        name="action",
        label="hello daddy",
        values=(Fraction(5, 8), Fraction(3, 4), Fraction(7, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    return reciprocity, trigger, action


def test_two_full_experiences_form_one_exact_closed_action(
    learned_experiences,
) -> None:
    _reciprocity, trigger, action = learned_experiences
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="test-causal-action-key",
    )
    owner.offer_teaching_experience(trigger)
    owner.offer_teaching_experience(action)
    binding = owner.teach(
        trigger_experience_id=trigger.event_id,
        action_experience_id=action.event_id,
        source="joe",
    )

    formed = owner.form(trigger, tick=17)
    assert owner.verify_issued(formed)
    assert formed.content == "hello daddy"
    assert formed.unicode_scalars == tuple(ord(value) for value in formed.content)
    assert formed.committed_sections == ("causal_action",)
    assert formed.commit_provenance[0].binding_id == binding.binding_id
    assert formed.commit_provenance[0].current_settlement_receipt_sha256 == (
        trigger.authority_receipt_sha256
    )
    assert formed.exact_close_receipt_sha256
    assert formed.authority_receipt_sha256


def test_unknown_and_conflicting_actions_fail_closed(
    learned_experiences,
) -> None:
    reciprocity, trigger, first_action = learned_experiences
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="test-causal-action-key",
    )
    assert owner.form(trigger, tick=1).stop_reason == "causal_action_unknown"

    second_action = _settlement(
        name="second-action",
        label="good morning",
        values=(Fraction(1, 2), Fraction(9, 16), Fraction(5, 8)),
        reciprocity=reciprocity,
        teach=True,
    )
    for action in (first_action, second_action):
        owner.offer_teaching_experience(trigger)
        owner.offer_teaching_experience(action)
        owner.teach(
            trigger_experience_id=trigger.event_id,
            action_experience_id=action.event_id,
            source="joe",
        )
    ambiguous = owner.form(trigger, tick=2)
    assert ambiguous.status == "ambiguous"
    assert ambiguous.content == ""
    assert ambiguous.commit_provenance == ()


def test_snapshot_is_bounded_authenticated_and_repeat_stable(
    learned_experiences,
) -> None:
    _reciprocity, trigger, action = learned_experiences
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="test-causal-action-key",
    )
    owner.offer_teaching_experience(trigger)
    owner.offer_teaching_experience(action)
    first = owner.teach(
        trigger_experience_id=trigger.event_id,
        action_experience_id=action.event_id,
        source="joe",
    )
    before = owner.encoded_snapshot()
    for _ in range(1_000):
        repeated = owner.teach(
            trigger_experience_id=trigger.event_id,
            action_experience_id=action.event_id,
            source="joe",
        )
        assert repeated == first
    assert owner.encoded_snapshot() == before

    restored = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="test-causal-action-key",
    )
    restored.restore_encoded(before)
    assert restored.encoded_snapshot() == before
    assert restored.form(trigger, tick=3).content == "hello daddy"
    assert restored.status()["working_experiences"] == 0

    damaged = dict(before)
    payload = bytearray(base64.b64decode(damaged["payload_base64"]))
    payload[-2] ^= 1
    damaged["payload_base64"] = base64.b64encode(payload).decode("ascii")
    with pytest.raises(ValueError, match="HMAC changed"):
        restored.restore_encoded(damaged)


def test_capacity_rejects_without_mutating_existing_learning(
    learned_experiences,
) -> None:
    reciprocity, trigger, action = learned_experiences
    owner = CausalActionOwner(
        log_event=lambda *_args, **_kwargs: None,
        authority_key="test-causal-action-key",
        action_capacity=1,
        witness_capacity=2,
    )
    owner.offer_teaching_experience(trigger)
    owner.offer_teaching_experience(action)
    owner.teach(
        trigger_experience_id=trigger.event_id,
        action_experience_id=action.event_id,
        source="joe",
    )
    before = owner.encoded_snapshot()
    second_action = _settlement(
        name="capacity-action",
        label="different action",
        values=(Fraction(7, 16), Fraction(1, 2), Fraction(9, 16)),
        reciprocity=reciprocity,
        teach=True,
    )
    owner.offer_teaching_experience(second_action)
    with pytest.raises(RuntimeError, match="capacity is full"):
        owner.teach(
            trigger_experience_id=trigger.event_id,
            action_experience_id=second_action.event_id,
            source="joe",
        )
    assert owner.encoded_snapshot() == before
    assert owner.status()["actions"] == 1
    assert owner.status()["witnesses"] == 2
