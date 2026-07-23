from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dsf_ai_service.substrate.auditory_incremental_terminal as terminal_module
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryIncrementalTerminalEvent,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_pcm_stream import PCM_SAMPLE_RATE_HZ
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECOGNITION_OPERATOR,
    AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA,
    AuditoryRecognitionOccurrence,
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    AuditoryTokenSequenceAuthority,
    TokenClassificationState,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    transduce_auditory_full_field,
)


SECRET = b"auditory-token-sequence-test-secret" * 2
STREAM_ID = "auditory-token-sequence-test-stream"
EPOCH = Fraction(17, 5)
EVENT_SAMPLES = OBSERVATION_HOP_SAMPLES * 4


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _experience_and_terminal(
    *,
    sample_start: int,
    frequency_hz: int,
    physical_class_receipt: str,
    tutor_label: str = "a label containing several written words",
):
    time_axis = np.arange(EVENT_SAMPLES) / PCM_SAMPLE_RATE_HZ
    capture = transduce_auditory_full_field(
        0.3 * np.sin(2.0 * math.pi * frequency_hz * time_axis),
        sample_rate_hz=PCM_SAMPLE_RATE_HZ,
    )
    source_start = EPOCH + Fraction(sample_start, PCM_SAMPLE_RATE_HZ)
    source_end = source_start + Fraction(EVENT_SAMPLES, PCM_SAMPLE_RATE_HZ)
    built = build_six_sense_full_field(
        assembly_id=f"token-sequence-{sample_start}-{frequency_hz}",
        source_time_start=source_start,
        source_time_end=source_end,
        observed_substreams={
            PhysicalSense.SOUND: auditory_kernel_component_inputs(
                capture, source_anchor=source_start
            )
        },
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    auditory_l5 = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="utterance")
    assert auditory_l5 is not None

    occurrence_payload = {
        "candidate_class_authority_receipts": [physical_class_receipt],
        "experience_id": auditory_l5.experience_id,
        "kind": AuditoryReciprocityKind.SPOKEN_FORM.value,
        "l5_authority_receipt_sha256": auditory_l5.authority_receipt_sha256,
        "operator": AUDITORY_RECOGNITION_OPERATOR,
        "schema": AUDITORY_RECOGNITION_OCCURRENCE_SCHEMA,
        "selected_class_authority_receipt_sha256": physical_class_receipt,
        "state": AuditoryRecognitionState.UNIQUE.value,
        "structural_fingerprint": auditory_l5.structural_fingerprint,
    }
    occurrence = AuditoryRecognitionOccurrence(
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        state=AuditoryRecognitionState.UNIQUE,
        experience_id=auditory_l5.experience_id,
        structural_fingerprint=auditory_l5.structural_fingerprint,
        l5_authority_receipt_sha256=auditory_l5.authority_receipt_sha256,
        candidate_class_authority_receipts=(physical_class_receipt,),
        selected_class_authority_receipt_sha256=physical_class_receipt,
        operator=AUDITORY_RECOGNITION_OPERATOR,
        authority_receipt_sha256=_digest(occurrence_payload),
    )
    sample_end = sample_start + EVENT_SAMPLES
    event_id = _digest({
        "source_sample_end": sample_end,
        "source_sample_start": sample_start,
        "stream_id": STREAM_ID,
        "structural_fingerprint": auditory_l5.structural_fingerprint,
    })
    evidence = (
        _sha(f"transport-{sample_start}"),
        _sha(f"cochlear-{sample_start}"),
        _sha(f"joint-{sample_start}"),
    )
    event_payload = terminal_module._event_payload(
        event_id=event_id,
        stream_id=STREAM_ID,
        source_sample_start=sample_start,
        source_sample_end=sample_end,
        tutor_label=tutor_label,
        structural_fingerprint=auditory_l5.structural_fingerprint,
        l5_authority_receipt_sha256=auditory_l5.authority_receipt_sha256,
        transport_receipt_sha256s=(evidence[0],),
        cochlear_receipt_sha256s=(evidence[1],),
        joint_settlement_receipt_sha256s=(evidence[2],),
        recognition_occurrence=occurrence,
    )
    terminal = AuditoryIncrementalTerminalEvent(
        event_id=event_id,
        stream_id=STREAM_ID,
        source_sample_start=sample_start,
        source_sample_end=sample_end,
        tutor_label=tutor_label,
        structural_fingerprint=auditory_l5.structural_fingerprint,
        l5_authority_receipt_sha256=auditory_l5.authority_receipt_sha256,
        transport_receipt_sha256s=(evidence[0],),
        cochlear_receipt_sha256s=(evidence[1],),
        joint_settlement_receipt_sha256s=(evidence[2],),
        authority_receipt_sha256=_digest(event_payload),
        recognition_occurrence=occurrence,
    )
    terminal.verify()
    return auditory_l5, terminal


@pytest.fixture(scope="module")
def admitted_events():
    authority = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    first_l5, first_terminal = _experience_and_terminal(
        sample_start=0,
        frequency_hz=440,
        physical_class_receipt=_sha("physical-class-first"),
    )
    second_l5, second_terminal = _experience_and_terminal(
        sample_start=EVENT_SAMPLES + OBSERVATION_HOP_SAMPLES,
        frequency_hz=660,
        physical_class_receipt=_sha("physical-class-second"),
    )
    return (
        authority,
        authority.admit(first_terminal, first_l5),
        authority.admit(second_terminal, second_l5),
        first_l5,
        first_terminal,
    )


def test_admission_binds_complete_terminal_to_unchanged_full_l5(
    admitted_events,
) -> None:
    authority, first, _second, first_l5, first_terminal = admitted_events
    assert first.source_sample_start == first_terminal.source_sample_start
    assert first.source_sample_end == first_terminal.source_sample_end
    assert first.source_time_start == first_l5.source_time_start
    assert first.source_time_end == first_l5.source_time_end

    other_l5, _other_terminal = _experience_and_terminal(
        sample_start=0,
        frequency_hz=880,
        physical_class_receipt=_sha("physical-class-other"),
    )
    with pytest.raises(ValueError, match="terminal and full L5 field disagree"):
        authority.admit(first_terminal, other_l5)

    with pytest.raises(ValueError, match="admission changed"):
        authority.classify(replace(first, admission_hmac_sha256="0" * 64))


def test_entire_event_requires_explicit_designation_and_never_parses_label(
    admitted_events,
) -> None:
    _fixture_authority, first, _second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    assert authority.classify(first).state is TokenClassificationState.UNKNOWN

    token_id = _sha("explicit-whole-event-token")
    designation = authority.issue_teacher_designation(
        first,
        token_class_id=token_id,
        token_form="one indivisible form",
        nonce=_sha("whole-event-designation"),
    )
    authority.teach(first, designation)
    classified = authority.classify(first)
    assert classified.state is TokenClassificationState.UNIQUE
    assert len(classified.candidates) == 1
    assert classified.candidates[0].token_form == "one indivisible form"

    sequence = authority.settle_sequence((first,))
    assert len(sequence.occurrences) == 1
    assert sequence.occurrences[0].source_sample_start == first.source_sample_start
    assert sequence.occurrences[0].source_sample_end == first.source_sample_end


def test_conflicting_whole_event_designations_are_honestly_ambiguous(
    admitted_events,
) -> None:
    _fixture_authority, first, _second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    for index in range(2):
        designation = authority.issue_teacher_designation(
            first,
            token_class_id=_sha(f"conflicting-token-{index}"),
            token_form=f"form-{index}",
            nonce=_sha(f"conflicting-nonce-{index}"),
        )
        authority.teach(first, designation)
    result = authority.classify(first)
    assert result.state is TokenClassificationState.AMBIGUOUS
    assert tuple(item.token_form for item in result.candidates) == (
        "form-0",
        "form-1",
    )


def test_sequence_preserves_supplied_physical_order_and_gap(admitted_events) -> None:
    _fixture_authority, first, second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    for ordinal, event in enumerate((first, second)):
        authority.teach(
            event,
            authority.issue_teacher_designation(
                event,
                token_class_id=_sha(f"ordered-token-{ordinal}"),
                token_form=f"token-{ordinal}",
                nonce=_sha(f"ordered-nonce-{ordinal}"),
            ),
        )
    receipt = authority.settle_sequence((first, second))
    authority.verify_sequence(receipt)
    assert tuple(item.ordinal for item in receipt.occurrences) == (0, 1)
    assert receipt.occurrences[0].source_sample_end < (
        receipt.occurrences[1].source_sample_start
    )

    with pytest.raises(ValueError, match="out of order"):
        authority.settle_sequence((second, first))
    changed = replace(
        receipt,
        occurrences=(
            replace(
                receipt.occurrences[0],
                source_sample_end=receipt.occurrences[0].source_sample_end + 1,
            ),
            receipt.occurrences[1],
        ),
    )
    with pytest.raises(ValueError, match="identity changed"):
        authority.verify_sequence(changed)


def test_teacher_nonce_replay_and_capacity_fail_without_partial_mutation(
    admitted_events,
) -> None:
    _fixture_authority, first, _second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(
        authority_secret=SECRET,
        max_bindings=1,
    )
    first_receipt = authority.issue_teacher_designation(
        first,
        token_class_id=_sha("capacity-first"),
        token_form="first",
        nonce=_sha("capacity-nonce"),
    )
    authority.teach(first, first_receipt)
    before = authority.snapshot()

    replay = authority.issue_teacher_designation(
        first,
        token_class_id=_sha("capacity-replay"),
        token_form="replay",
        nonce=_sha("capacity-nonce"),
    )
    with pytest.raises(RuntimeError, match="nonce was already used"):
        authority.teach(first, replay)
    assert authority.snapshot() == before

    full = authority.issue_teacher_designation(
        first,
        token_class_id=_sha("capacity-full"),
        token_form="full",
        nonce=_sha("capacity-full-nonce"),
    )
    with pytest.raises(RuntimeError, match="capacity is full"):
        authority.teach(first, full)
    assert authority.snapshot() == before


def test_hmac_snapshot_restore_is_complete_and_atomic(admitted_events) -> None:
    _fixture_authority, first, _second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    authority.teach(
        first,
        authority.issue_teacher_designation(
            first,
            token_class_id=_sha("persisted-token"),
            token_form="persisted",
            nonce=_sha("persisted-nonce"),
        ),
    )
    snapshot = authority.snapshot()
    restored = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot
    assert restored.classify(first).state is TokenClassificationState.UNIQUE

    before = restored.snapshot()
    changed = copy.deepcopy(snapshot)
    changed["payload"]["bindings"][0]["token_form"] = "tampered"
    with pytest.raises(ValueError, match="snapshot authority changed"):
        restored.restore(changed)
    assert restored.snapshot() == before


def test_concurrent_distinct_designations_are_serial_and_bounded(
    admitted_events,
) -> None:
    _fixture_authority, first, _second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(
        authority_secret=SECRET,
        max_bindings=32,
    )

    def teach(index: int) -> None:
        receipt = authority.issue_teacher_designation(
            first,
            token_class_id=_sha(f"concurrent-token-{index}"),
            token_form=f"concurrent-{index}",
            nonce=_sha(f"concurrent-nonce-{index}"),
        )
        authority.teach(first, receipt)

    with ThreadPoolExecutor(max_workers=8) as pool:
        tuple(pool.map(teach, range(24)))
    assert authority.binding_count == 24
    result = authority.classify(first)
    assert result.state is TokenClassificationState.AMBIGUOUS
    assert len(result.candidates) == 24


def test_long_run_sequence_settlement_has_constant_persisted_state(
    admitted_events,
) -> None:
    _fixture_authority, first, second, _l5, _terminal = admitted_events
    authority = AuditoryTokenSequenceAuthority(authority_secret=SECRET)
    for ordinal, event in enumerate((first, second)):
        authority.teach(
            event,
            authority.issue_teacher_designation(
                event,
                token_class_id=_sha(f"long-run-token-{ordinal}"),
                token_form=f"long-{ordinal}",
                nonce=_sha(f"long-run-nonce-{ordinal}"),
            ),
        )
    before_snapshot = authority.snapshot()
    before_bytes = authority.snapshot_bytes
    last = None
    for _ in range(2_000):
        last = authority.settle_sequence((first, second))
    assert last is not None
    authority.verify_sequence(last)
    assert authority.snapshot() == before_snapshot
    assert authority.snapshot_bytes == before_bytes
