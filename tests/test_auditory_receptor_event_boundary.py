from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import numpy as np

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    UNIT_SOURCE_RELEVANCE_RULE,
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.auditory_kernel_mount import (
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_receptor_event_boundary import (
    AuditoryReceptorEventState,
    AuditoryWindingState,
    auditory_pressure_energy_relevance,
    settle_auditory_receptor_event,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


def _capture():
    sample_count = OBSERVATION_HOP_SAMPLES * 8
    time = np.arange(sample_count, dtype=np.float64) / REQUIRED_SAMPLE_RATE_HZ
    return transduce_auditory_full_field(
        0.4 * np.sin(2.0 * np.pi * 440.0 * time),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )


def _experience(capture, *, old_unit_relevance: bool = False):
    anchor = Fraction(37)
    components = auditory_kernel_component_inputs(
        capture,
        source_anchor=anchor,
    )
    if old_unit_relevance:
        components = tuple(
            replace(
                value,
                source_relevance=None,
                source_relevance_rule=UNIT_SOURCE_RELEVANCE_RULE,
                source_relevance_origin_substream_id=None,
            )
            for value in components
        )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id="auditory-receptor-event-test",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            capture.input_sample_count,
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={PhysicalSense.SOUND: components},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    experience = AuditoryL5Owner(
        log_event=lambda *_args, **_kwargs: None
    ).settle(built, event_boundary="ambient")
    assert experience is not None
    return experience


def test_pressure_energy_relevance_is_exact_binary64_square() -> None:
    pressure = 0.125

    relevance = auditory_pressure_energy_relevance(pressure)

    assert relevance == Fraction.from_float(pressure) ** 2
    assert relevance == Fraction(1, 64)
    assert relevance != Fraction.from_float(pressure)


def test_complete_paired_relevance_and_full_fields_publish_event() -> None:
    capture = _capture()
    experience = _experience(capture)

    result = settle_auditory_receptor_event(
        capture=capture,
        auditory_l5=experience,
    )

    assert result.state is AuditoryReceptorEventState.OBSERVED
    assert result.event is not None
    result.event.verify()
    assert len(result.event.channels) == 16
    assert all(
        len(channel.frames) == capture.frame_count
        and channel.pressure_fields
        and channel.phase_fields
        for channel in result.event.channels
    )
    assert all(
        tuple(name for name, _ in field.fields)
        == (
            "D_k",
            "M_k",
            "R_rev_k",
            "U_star_k",
            "C_k",
            "P_k",
            "B_k",
        )
        for channel in result.event.channels
        for field in (*channel.pressure_fields, *channel.phase_fields)
    )
    assert all(
        channel.frames[0].winding_state
        is AuditoryWindingState.PRIOR_PHASE_UNRESOLVED
        and channel.frames[0].winding_delta is None
        and all(
            frame.winding_state is AuditoryWindingState.SETTLED
            and frame.winding_delta is not None
            for frame in channel.frames[1:]
        )
        for channel in result.event.channels
    )


def test_missing_physical_or_full_field_input_is_typed_null() -> None:
    capture = _capture()
    experience = _experience(capture)

    no_capture = settle_auditory_receptor_event(
        capture=None,
        auditory_l5=experience,
    )
    no_field = settle_auditory_receptor_event(
        capture=capture,
        auditory_l5=None,
    )

    assert no_capture.state is AuditoryReceptorEventState.UNRESOLVED
    assert no_capture.event is None
    assert no_capture.reason == (
        "typed auditory full-field capture is unavailable"
    )
    assert no_field.state is AuditoryReceptorEventState.UNRESOLVED
    assert no_field.event is None
    assert no_field.reason == (
        "typed complete auditory L5 experience is unavailable"
    )


def test_old_unit_relevance_cannot_publish_receptor_event() -> None:
    capture = _capture()
    old_experience = _experience(
        capture,
        old_unit_relevance=True,
    )

    result = settle_auditory_receptor_event(
        capture=capture,
        auditory_l5=old_experience,
    )

    assert result.state is AuditoryReceptorEventState.UNRESOLVED
    assert result.event is None
    assert "relevance differs from squared pressure amplitude" in result.reason


def test_capture_mismatch_cannot_publish_partial_receptor_event() -> None:
    capture = _capture()
    experience = _experience(capture)
    changed = transduce_auditory_full_field(
        np.zeros(capture.input_sample_count, dtype=np.float64),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )

    result = settle_auditory_receptor_event(
        capture=changed,
        auditory_l5=experience,
    )

    assert result.state is AuditoryReceptorEventState.UNRESOLVED
    assert result.event is None
