from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import replace
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pytest

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_krimelack_causal_occurrence import (
    AuditoryKrimelackCausalOccurrence,
    bind_auditory_krimelack_causal_occurrence,
)
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    prepare_auditory_krimelack_exemplar,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AuditoryKrimelackStreamOwner,
    AuditoryKrimelackStreamState,
)
from dsf_ai_service.substrate.auditory_l5 import (
    AuditoryL5Experience,
    AuditoryL5Owner,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from tests.native_joint_occurrence_support import joint_occurrences_for


SAMPLE_COUNT = 320


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _heard_field(
    *,
    assembly_id: str,
    anchor: Fraction,
    gain: float = 1.0,
    touch_observed: bool = False,
    touch_values: tuple[float, float] = (-0.25, 0.75),
    waveform_variant: int = 0,
):
    signal = np.asarray(
        [
            gain
            * (
                (
                    ((index * 37) % 101) / 101.0
                    if index % 2 == 0
                    else -((index * 53) % 97) / 97.0
                )
                if waveform_variant == 0
                else (
                    ((index * 17 + 23) % 89) / 89.0
                    if index % 3 == 0
                    else -((index * 71 + 11) % 103) / 103.0
                )
            )
            for index in range(SAMPLE_COUNT)
        ],
        dtype=np.float64,
    )
    capture = transduce_auditory_full_field(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    source_end = anchor + Fraction(
        SAMPLE_COUNT,
        REQUIRED_SAMPLE_RATE_HZ,
    )
    observed = {
        PhysicalSense.SOUND: auditory_kernel_component_inputs(
            capture,
            source_anchor=anchor,
        ),
    }
    if touch_observed:
        observed[PhysicalSense.TOUCH] = (
            NativeSensorySubstreamInput(
                sense=PhysicalSense.TOUCH,
                sensor_id="auditory-causal-test-touch",
                substream_id="contact-pressure",
                topology_index=0,
                coordinates=(
                    NativeAxisCoordinate(
                        "reference-frame",
                        "body-surface",
                    ),
                ),
                physical_quantity="normalized-contact-state",
                physical_unit="dimensionless",
                source_times=(anchor, source_end),
                normalized_signal=touch_values,
                phase_turns=(Fraction(0), Fraction(0)),
            ),
        )
    built = build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=anchor,
        source_time_end=source_end,
        observed_substreams=observed, occurrences=joint_occurrences_for(observed),
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense in observed
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    auditory = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(
        built,
        event_boundary="utterance",
    )
    assert auditory is not None
    return built, auditory


def _causal(built, *, routing_chis: tuple[int, ...] = ()):
    settled = []
    result = ExactCausalExperienceOwner(
        on_settlement=settled.append,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        built,
        routing_chis=routing_chis,
        source_tags=("auditory:unresolved_source",),
    )
    assert settled == [result]
    assert result.language_events == ()
    result.verify()
    return result


def _stream(auditory, causal):
    provisional = AuditoryStreamSettlementReceipt(
        stream_id="causal-occurrence-room",
        sequence=0,
        first_sample_index=0,
        sample_count=SAMPLE_COUNT,
        source_time_start=auditory.source_time_start,
        source_time_end=auditory.source_time_end,
        assembly_id=auditory.assembly_id,
        transport_receipt_sha256=hashlib.sha256(
            b"causal-occurrence-transport"
        ).hexdigest(),
        prior_transport_receipt_sha256=None,
        cochlear_receipt_sha256=hashlib.sha256(
            b"causal-occurrence-cochlear"
        ).hexdigest(),
        prior_cochlear_state_receipt_sha256=None,
        auditory_l5_authority_receipt_sha256=(
            auditory.authority_receipt_sha256
        ),
        causal_settlement_authority_receipt_sha256=(
            causal.authority_receipt_sha256
        ),
        authority_receipt_sha256="0" * 64,
    )
    result = replace(
        provisional,
        authority_receipt_sha256=hashlib.sha256(
            _canonical(provisional.payload())
        ).hexdigest(),
    )
    result.verify()
    return result


def _recognition(auditory, stream, *, taught: bool = True):
    owner = AuditoryKrimelackStreamOwner(
        log_event=lambda *_args, **_kwargs: None,
        tutor_authority=AuditoryTutorAuthority.unrequired(),
    )
    if taught:
        owner.teach(auditory, tutor_label="hello guala")
    return owner.advance(auditory, stream)


@pytest.fixture(scope="module")
def causal_occurrence_evidence():
    executor = start_exact_field_executor()
    executor.assert_healthy()
    try:
        built, auditory = _heard_field(
            assembly_id="auditory-causal-occurrence",
            anchor=Fraction(12_000),
        )
        causal = _causal(built)
        stream = _stream(auditory, causal)
        recognition = _recognition(auditory, stream)
        assert recognition.state is AuditoryKrimelackStreamState.UNIQUE
        return built, auditory, causal, stream, recognition
    finally:
        stop_exact_field_executor()


def test_unique_heard_kind_closes_over_complete_full_field(
    causal_occurrence_evidence,
) -> None:
    _built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )

    occurrence = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )

    occurrence.verify()
    component = occurrence.components[0]
    assert occurrence.kind_id == recognition.selected_kind_id
    assert component.causal_witness.structural_fingerprint == (
        causal.structural_fingerprint
    )
    assert component.full_dsf_authority.source_field_authority_receipt_sha256 == (
        auditory.authority_receipt_sha256
    )
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for field_component in component.full_dsf_authority.components
        for field_tuple in field_component.tuples
    )


def test_prepared_exemplar_avoids_rewalking_verified_l5(
    causal_occurrence_evidence,
) -> None:
    _built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    prepared = prepare_auditory_krimelack_exemplar(auditory)
    expected = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )

    with patch.object(
        AuditoryL5Experience,
        "verify",
        side_effect=AssertionError("deep L5 verification repeated"),
    ):
        accelerated = bind_auditory_krimelack_causal_occurrence(
            recognition=recognition,
            auditory_experiences=(auditory,),
            stream_settlements=(stream,),
            causal_settlements=(causal,),
            prepared_exemplars=(prepared,),
        )

    assert accelerated == expected
    assert all(
        tuple(name for name, _value in field_tuple.fields)
        == DSF_FIELD_ORDER
        for component in accelerated.components
        for field_component in component.full_dsf_authority.components
        for field_tuple in field_component.tuples
    )


def test_occurrence_is_label_free_and_cold_verifiable(
    causal_occurrence_evidence,
) -> None:
    _built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    occurrence = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )
    record = occurrence.as_record()
    encoded = _canonical(record)

    assert b"hello guala" not in encoded
    assert b"tutor_label" not in encoded
    assert b"unicode_scalars" not in encoded
    restored = AuditoryKrimelackCausalOccurrence.from_record(
        json.loads(encoded)
    )
    assert restored == occurrence


def test_unknown_sound_cannot_enter_causal_association(
    causal_occurrence_evidence,
) -> None:
    _built, auditory, causal, stream, _unique_recognition = (
        causal_occurrence_evidence
    )
    unknown = _recognition(auditory, stream, taught=False)
    assert unknown.state is AuditoryKrimelackStreamState.UNKNOWN

    with pytest.raises(
        ValueError,
        match="requires unique recognition",
    ):
        bind_auditory_krimelack_causal_occurrence(
            recognition=unknown,
            auditory_experiences=(auditory,),
            stream_settlements=(stream,),
            causal_settlements=(causal,),
        )


def test_causal_receipt_mismatch_fails_closed(
    causal_occurrence_evidence,
) -> None:
    _built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    other_built, _other_auditory = _heard_field(
        assembly_id="auditory-causal-other",
        anchor=Fraction(13_000),
    )
    other_causal = _causal(other_built)
    assert other_causal.authority_receipt_sha256 != (
        causal.authority_receipt_sha256
    )

    with pytest.raises(
        ValueError,
        match="left its live causal settlement",
    ):
        bind_auditory_krimelack_causal_occurrence(
            recognition=recognition,
            auditory_experiences=(auditory,),
            stream_settlements=(stream,),
            causal_settlements=(other_causal,),
        )


def test_routing_chi_does_not_become_association_identity(
    causal_occurrence_evidence,
) -> None:
    built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    first = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )
    routed_causal = _causal(built, routing_chis=(7, 19))
    routed_stream = _stream(auditory, routed_causal)
    routed_recognition = _recognition(auditory, routed_stream)
    second = bind_auditory_krimelack_causal_occurrence(
        recognition=routed_recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(routed_stream,),
        causal_settlements=(routed_causal,),
    )

    assert routed_causal.authority_receipt_sha256 != (
        causal.authority_receipt_sha256
    )
    assert routed_causal.structural_fingerprint == (
        causal.structural_fingerprint
    )
    assert first.association_id == second.association_id


def test_changed_full_dsf_authority_is_rejected(
    causal_occurrence_evidence,
) -> None:
    _built, auditory, causal, stream, recognition = (
        causal_occurrence_evidence
    )
    occurrence = bind_auditory_krimelack_causal_occurrence(
        recognition=recognition,
        auditory_experiences=(auditory,),
        stream_settlements=(stream,),
        causal_settlements=(causal,),
    )
    record = json.loads(_canonical(occurrence.as_record()))
    text = record["components"][0]["full_dsf_authority_base64"]
    damaged = bytearray(base64.b64decode(text))
    damaged[-1] ^= 1
    record["components"][0]["full_dsf_authority_base64"] = (
        base64.b64encode(damaged).decode("ascii")
    )

    with pytest.raises(Exception):
        AuditoryKrimelackCausalOccurrence.from_record(record)
