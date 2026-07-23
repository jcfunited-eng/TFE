from __future__ import annotations

import io
import json
import math
import os
import struct
import wave
from dataclasses import replace

import pytest

import dsf_ai_service.substrate.auditory_reciprocity as auditory_reciprocity
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.substrate.auditory_reciprocity import (
    AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA,
    AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA,
    MAX_ENCODED_SNAPSHOT_BYTES,
    MAX_PATH_BRANCHES_PER_CLASS,
    AuditoryRecognitionState,
    AuditoryReciprocityKind,
    AuditoryReciprocityOwner,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAdmissionReceipt,
)
from dsf_ai_service.v4.gualaloom_v5_engine import Guala


SAMPLE_RATE = 16_000
ANCHOR_NS = 2_000_000_000_000


def _wav(
    *,
    duration_seconds: float = 1.0,
    frequency_hz: float = 440.0,
    amplitude: int = 8_000,
    second_half_amplitude: int | None = None,
) -> bytes:
    sample_count = int(SAMPLE_RATE * duration_seconds)
    values = []
    for index in range(sample_count):
        selected_amplitude = (
            second_half_amplitude
            if second_half_amplitude is not None and index >= sample_count // 2
            else amplitude
        )
        values.append(int(
            selected_amplitude
            * math.sin(2.0 * math.pi * frequency_hz * index / SAMPLE_RATE)
        ))
    payload = io.BytesIO()
    with wave.open(payload, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        stream.writeframes(struct.pack(f"<{len(values)}h", *values))
    return payload.getvalue()


@pytest.fixture
def engine() -> Guala:
    os.environ["EVENT_DRIVEN_SUBSTRATE"] = "0"
    os.environ["WAVE_ATLAS_ENABLED"] = "0"
    os.environ["WAVE_SUMMARY_ENQUEUE_ENABLED"] = "0"
    os.environ["SELF_HEARING_ENABLED"] = "0"
    value = Guala()
    try:
        yield value
    finally:
        value.shutdown()


def _hear(
    engine: Guala,
    *,
    duration_seconds: float = 1.0,
    frequency_hz: float = 440.0,
    amplitude: int = 8_000,
    second_half_amplitude: int | None = None,
    source: str = "untrusted-source-label",
):
    engine.process_sound_frame(
        _wav(
            duration_seconds=duration_seconds,
            frequency_hz=frequency_hz,
            amplitude=amplitude,
            second_half_amplitude=second_half_amplitude,
        ),
        source=source,
        source_anchor_ns=ANCHOR_NS,
        source_time_end_ns=(
            ANCHOR_NS + int(duration_seconds * 1_000_000_000)
        ),
        auditory_event_boundary="utterance",
    )
    experience = engine._latest_auditory_l5_experience
    assert experience is not None
    experience.verify()
    return experience


def _recognition(engine: Guala, kind: AuditoryReciprocityKind):
    return next(
        value for value in engine._latest_auditory_recognitions
        if value.kind is kind
    )


def _teach(engine: Guala, experience, label: str):
    learned = engine._auditory_reciprocity_owner.teach(
        experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label=label,
    )
    recognition = engine._auditory_reciprocity_owner.recognize(
        experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
    )
    return {
        "recognition_state": recognition.state.value,
        "reinforcement_count": learned.reinforcement_count,
    }


def test_spoken_path_reachability_accepts_rate_change_but_not_other_structure(
    engine: Guala,
) -> None:
    witness = _hear(engine, duration_seconds=1.0, frequency_hz=440.0)
    taught = _teach(engine, witness, "steady lower form")
    assert taught["recognition_state"] == "unique"

    for duration in (0.8, 1.2):
        _hear(engine, duration_seconds=duration, frequency_hz=440.0)
        result = _recognition(engine, AuditoryReciprocityKind.SPOKEN_FORM)
        assert result.state is AuditoryRecognitionState.UNIQUE
        assert result.tutor_label == "steady lower form"

    _hear(engine, duration_seconds=1.0, frequency_hz=640.0)
    result = _recognition(engine, AuditoryReciprocityKind.SPOKEN_FORM)
    assert result.state is AuditoryRecognitionState.UNKNOWN


def test_one_joint_interpolation_coordinate_rejects_cartesian_time_mixture(
    engine: Guala,
) -> None:
    quiet = _hear(engine, amplitude=4_000)
    _teach(engine, quiet, "one form")
    loud = _hear(engine, amplitude=12_000)
    reinforced = _teach(engine, loud, "one form")
    assert reinforced["reinforcement_count"] == 2

    _hear(engine, amplitude=8_000)
    result = _recognition(engine, AuditoryReciprocityKind.SPOKEN_FORM)
    assert result.state is AuditoryRecognitionState.UNIQUE

    # Every half is individually witnessed, but no single interpolation
    # coordinate produces quiet then loud.  Independent marginal envelopes
    # would accept this; the joint causal path must not.
    _hear(engine, amplitude=4_000, second_half_amplitude=12_000)
    result = _recognition(engine, AuditoryReciprocityKind.SPOKEN_FORM)
    assert result.state is AuditoryRecognitionState.UNKNOWN


def test_monaural_source_identity_fails_closed_and_source_strings_are_inert(
    engine: Guala,
) -> None:
    experience = _hear(engine, source="claims-to-be-joe")
    with pytest.raises(ValueError, match="no physical acoustic-source"):
        engine.teach_latest_auditory_experience(
            experience_id=experience.experience_id,
            kind="source_continuity",
            tutor_label="Joe",
        )

    repeated = _hear(engine, source="claims-to-be-someone-else")
    result = engine._auditory_reciprocity_owner.recognize(
        repeated, kind=AuditoryReciprocityKind.SOURCE_CONTINUITY
    )
    assert result.state is AuditoryRecognitionState.UNKNOWN
    assert result.candidate_labels == ()
    status = engine.auditory_l5_status()["reciprocity"]
    assert status["class_counts"]["source_continuity"] == 0
    assert status["source_continuity"].startswith("unknown_without")


def test_four_branch_and_class_caps_fail_before_mutation(engine: Guala) -> None:
    experiences = [
        _hear(engine, frequency_hz=frequency)
        for frequency in (300.0, 360.0, 420.0, 480.0, 540.0)
    ]
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        max_classes_per_kind=1,
    )
    for experience in experiences[:MAX_PATH_BRANCHES_PER_CLASS]:
        owner.teach(
            experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="bounded form",
        )
    before = owner.snapshot()
    with pytest.raises(RuntimeError, match="branch capacity is full"):
        owner.teach(
            experiences[-1],
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="bounded form",
        )
    assert owner.snapshot() == before
    with pytest.raises(RuntimeError, match="class capacity is full"):
        owner.teach(
            experiences[-1],
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="second class",
        )


def test_overlap_is_ambiguous_and_tampered_experience_is_rejected(
    engine: Guala,
) -> None:
    experience = _hear(engine)
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    for label in ("one", "two"):
        owner.teach(
            experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=label,
        )
    result = owner.recognize(
        experience, kind=AuditoryReciprocityKind.SPOKEN_FORM
    )
    assert result.state is AuditoryRecognitionState.AMBIGUOUS
    assert result.candidate_labels == ("one", "two")

    altered = replace(experience, structural_fingerprint="0" * 64)
    with pytest.raises(ReceiptError, match="altered"):
        owner.recognize(
            altered, kind=AuditoryReciprocityKind.SPOKEN_FORM
        )


def test_packed_snapshot_round_trip_integrity_and_admission_boundary(
    engine: Guala,
) -> None:
    experience = _hear(engine)
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    owner.teach(
        experience,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="persisted form",
    )
    snapshot = owner.snapshot()
    encoded = owner.encoded_snapshot()
    assert len(encoded["payload"].encode("ascii")) < MAX_ENCODED_SNAPSHOT_BYTES
    assert "raw_audio" not in snapshot
    assert "source_continuity" in snapshot

    restored = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    restored.restore_encoded(encoded)
    assert restored.snapshot() == snapshot
    result = restored.recognize(
        experience, kind=AuditoryReciprocityKind.SPOKEN_FORM
    )
    assert result.state is AuditoryRecognitionState.UNIQUE

    damaged = dict(encoded)
    damaged["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="integrity"):
        restored.restore_encoded(damaged)

    tiny = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None,
        max_encoded_snapshot_bytes=256,
    )
    before = tiny.snapshot()
    with pytest.raises(RuntimeError, match="snapshot capacity is full"):
        tiny.teach(
            experience,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label="cannot fit",
        )
    assert tiny.snapshot() == before


def test_work_boundary_is_indeterminate_not_unknown(
    engine: Guala, monkeypatch: pytest.MonkeyPatch
) -> None:
    witness = _hear(engine, frequency_hz=440.0)
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    owner.teach(
        witness,
        kind=AuditoryReciprocityKind.SPOKEN_FORM,
        tutor_label="bounded",
    )
    query = _hear(engine, frequency_hz=640.0)
    monkeypatch.setattr(
        auditory_reciprocity,
        "MAX_REACHABILITY_CELLS_PER_RECOGNITION",
        1,
    )
    result = owner.recognize(
        query, kind=AuditoryReciprocityKind.SPOKEN_FORM
    )
    assert result.state is AuditoryRecognitionState.INDETERMINATE
    assert owner.status()["resource_exhausted_recognitions"] == 1


def test_exact_fingerprint_fast_path_remains_authoritative_at_class_cap(
    engine: Guala, monkeypatch: pytest.MonkeyPatch
) -> None:
    witness = _hear(engine)
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    for index in range(64):
        owner.teach(
            witness,
            kind=AuditoryReciprocityKind.SPOKEN_FORM,
            tutor_label=f"exact-{index:02d}",
        )
    monkeypatch.setattr(
        auditory_reciprocity,
        "MAX_REACHABILITY_CELLS_PER_RECOGNITION",
        0,
    )
    result = owner.recognize(
        witness, kind=AuditoryReciprocityKind.SPOKEN_FORM
    )
    assert result.state is AuditoryRecognitionState.AMBIGUOUS
    assert len(result.candidate_labels) == 64
    assert owner.status()["resource_exhausted_recognitions"] == 0


def test_v5_witness_preserves_16_direct_paired_channels_and_both_l4_banks(
    engine: Guala,
) -> None:
    experience = _hear(engine)
    witness = auditory_reciprocity._pack_experience(experience)

    assert len(witness.topology) == 16
    assert len(witness.packed_samples) == 16
    assert len(witness.pressure_l4_field_tuples) == 16
    assert len(witness.carrier_phase_advance_l4_field_tuples) == 16
    for channel_index, channel in enumerate(experience.channels):
        pressure, phase_advance = struct.unpack_from(
            "<dd", witness.packed_samples[channel_index], 0
        )
        assert pressure == float(channel.pressure.samples[0].signal)
        assert phase_advance == float(
            channel.carrier_phase_advance.samples[0].phase_turns
        )
        assert tuple(
            value.authority_receipt_sha256
            for value in witness.pressure_l4_field_tuples[channel_index]
        ) == tuple(
            value.authority_receipt_sha256
            for value in channel.pressure.l4_field_tuples
        )
        assert tuple(
            value.authority_receipt_sha256
            for value in witness.carrier_phase_advance_l4_field_tuples[
                channel_index
            ]
        ) == tuple(
            value.authority_receipt_sha256
            for value in channel.carrier_phase_advance.l4_field_tuples
        )


def test_pressure_and_phase_l4_banks_share_one_exact_interpolation_coordinate(
    engine: Guala,
) -> None:
    base = auditory_reciprocity._pack_experience(_hear(engine))

    def move_first_field(witness, bank_name: str, amount: int):
        bank = [list(channel) for channel in getattr(witness, bank_name)]
        first = bank[0][0]
        fields = list(first.fields)
        fields[0] = (fields[0][0], fields[0][1] + amount)
        bank[0][0] = replace(first, fields=tuple(fields))
        return replace(
            witness,
            **{bank_name: tuple(tuple(channel) for channel in bank)},
        )

    right = move_first_field(base, "pressure_l4_field_tuples", 4)
    right = move_first_field(
        right, "carrier_phase_advance_l4_field_tuples", 4
    )
    one_coordinate = move_first_field(
        base, "pressure_l4_field_tuples", 1
    )
    one_coordinate = move_first_field(
        one_coordinate, "carrier_phase_advance_l4_field_tuples", 1
    )
    conflicting_coordinates = move_first_field(
        base, "pressure_l4_field_tuples", 1
    )
    conflicting_coordinates = move_first_field(
        conflicting_coordinates,
        "carrier_phase_advance_l4_field_tuples",
        3,
    )

    assert auditory_reciprocity._l4_lambda_interval(
        one_coordinate, base, right, (0.0, 1.0)
    ) == (0.25, 0.25)
    assert auditory_reciprocity._l4_lambda_interval(
        conflicting_coordinates, base, right, (0.0, 1.0)
    ) is None


def test_v3_admission_requires_exact_ordered_component_l4_receipts(
    engine: Guala,
) -> None:
    experience = _hear(engine)
    witness = auditory_reciprocity._pack_experience(experience)
    authority_payload = experience.receipt_registry.resolve(
        experience.authority_receipt_sha256,
        "test auditory L5 authority",
    )
    admission = AuditoryTutorAdmissionReceipt(
        experience_id=experience.experience_id,
        kind="spoken_form",
        tutor_label="heard form",
        event_boundary="utterance",
        gateway_authority_hmac_sha256="0" * 64,
        l5_authority_receipt_sha256=experience.authority_receipt_sha256,
        l5_authority_payload=authority_payload,
        admission_hmac_sha256="0" * 64,
    )
    auditory_reciprocity._verify_l5_admission_evidence(
        admission, (witness,)
    )

    altered = json.loads(authority_payload)
    altered["channels"][0]["pressure"][
        "l4_field_receipt_sha256s"
    ][0] = "f" * 64
    changed = replace(
        admission,
        l5_authority_payload=json.dumps(
            altered,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8"),
    )
    with pytest.raises(ValueError, match="does not match"):
        auditory_reciprocity._verify_l5_admission_evidence(
            changed, (witness,)
        )


def test_v5_persistence_rejects_legacy_v4_without_mutating_state() -> None:
    owner = AuditoryReciprocityOwner(
        log_event=lambda *_args, **_kwargs: None
    )
    before = owner.snapshot()
    assert before["schema"] == AUDITORY_RECIPROCITY_SNAPSHOT_SCHEMA
    assert owner.encoded_snapshot()["schema"] == (
        AUDITORY_RECIPROCITY_ENVELOPE_SCHEMA
    )

    with pytest.raises(ValueError, match="legacy.*v4"):
        owner.restore({"schema": "guala.auditory.causal_path.v4"})
    assert owner.snapshot() == before
    with pytest.raises(ValueError, match="legacy.*v4"):
        owner.restore_encoded({
            "schema": "guala.auditory.causal_path.gzip.v4"
        })
    assert owner.snapshot() == before


def test_direct_phase_advance_python_native_differential(engine: Guala) -> None:
    left = auditory_reciprocity._pack_experience(
        _hear(engine, duration_seconds=1.0)
    )
    query = auditory_reciprocity._pack_experience(
        _hear(engine, duration_seconds=0.8)
    )
    assert auditory_reciprocity._native_port_values(query)[0][1] == (
        struct.unpack_from("<dd", query.packed_samples[0], 0)[1]
    )
    expected = auditory_reciprocity._joint_cell_contains_python(
        query, left, left, max_work=1_000_000
    )
    if auditory_reciprocity._native_joint_path_contains is None:
        pytest.skip("native auditory joint-path kernel is unavailable")
    assert auditory_reciprocity._joint_cell_contains_native(
        query, left, left, max_work=1_000_000
    ) == expected
