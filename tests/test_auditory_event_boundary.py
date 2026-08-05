from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from dsf_ai_service.substrate.auditory_event_boundary import (
    AUDITORY_EVENT_BOUNDARY_SCHEMA,
    settle_auditory_event_boundary,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_FULL_FIELD_PROVIDER_SCHEMA,
    OBSERVATION_HOP_SAMPLES,
    PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


PRESSURE_UNCERTAINTY_FULL_SCALE = 2.0 / 32_768.0


def _surrounded_tone() -> np.ndarray:
    leading = np.zeros(20 * OBSERVATION_HOP_SAMPLES, dtype=np.float64)
    time_axis = np.arange(REQUIRED_SAMPLE_RATE_HZ) / REQUIRED_SAMPLE_RATE_HZ
    event = 0.25 * np.sin(2.0 * math.pi * 440.0 * time_axis)
    trailing = np.zeros(30 * OBSERVATION_HOP_SAMPLES, dtype=np.float64)
    return np.concatenate((leading, event, trailing))


def _settle(signal: np.ndarray):
    capture = transduce_auditory_full_field(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    return capture, settle_auditory_event_boundary(
        capture,
        pressure_uncertainty_full_scale=PRESSURE_UNCERTAINTY_FULL_SCALE,
    )


def test_two_physical_basins_settle_one_surrounded_full_field_event() -> None:
    capture, boundary = _settle(_surrounded_tone())

    boundary.verify()
    assert boundary.event_frame_start == 20
    assert boundary.event_frame_end == 122
    assert boundary.source_sample_start == 20 * OBSERVATION_HOP_SAMPLES
    assert boundary.source_sample_end == 122 * OBSERVATION_HOP_SAMPLES
    assert boundary.lower_basin_frames + boundary.upper_basin_frames == (
        capture.frame_count
    )
    assert boundary.upper_energy_lower_bound > boundary.lower_energy_upper_bound
    assert boundary.provider_schema == AUDITORY_FULL_FIELD_PROVIDER_SCHEMA
    assert boundary.payload()["schema"] == AUDITORY_EVENT_BOUNDARY_SCHEMA
    assert AUDITORY_EVENT_BOUNDARY_SCHEMA == "guala.auditory_event_boundary.v3"


def test_boundary_receipt_binds_the_complete_native_capture() -> None:
    _, boundary = _settle(_surrounded_tone())

    altered = dataclasses.replace(
        boundary,
        event_frame_end=boundary.event_frame_end - 1,
    )
    with pytest.raises(ValueError, match="receipt changed"):
        altered.verify()


def test_capture_identity_binds_phase_advance_and_normalized_motion() -> None:
    capture, original = _settle(_surrounded_tone())
    channel_index = 7
    channel = capture.channels[channel_index]
    phase_step_turns = 1e-6
    changed_phases = tuple(
        value + frame_index * phase_step_turns
        for frame_index, value in enumerate(channel.carrier_phase_turns)
    )
    changed_advances = (
        0.0,
        *(
            value + phase_step_turns
            for value in channel.carrier_phase_advance_turns[1:]
        ),
    )
    changed_normalized = tuple(
        value / PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
        for value in changed_advances
    )
    changed_channel = dataclasses.replace(
        channel,
        carrier_phase_turns=changed_phases,
        carrier_phase_advance_turns=changed_advances,
        carrier_phase_advance_nyquist_fraction=changed_normalized,
    )
    changed_capture = dataclasses.replace(
        capture,
        channels=(
            *capture.channels[:channel_index],
            changed_channel,
            *capture.channels[channel_index + 1:],
        ),
    )

    changed = settle_auditory_event_boundary(
        changed_capture,
        pressure_uncertainty_full_scale=PRESSURE_UNCERTAINTY_FULL_SCALE,
    )
    assert changed.event_frame_start == original.event_frame_start
    assert changed.event_frame_end == original.event_frame_end
    assert changed.capture_sha256 != original.capture_sha256
    assert changed.authority_receipt_sha256 != original.authority_receipt_sha256


def test_incomplete_provider_v3_evidence_fails_closed() -> None:
    capture = transduce_auditory_full_field(
        _surrounded_tone(), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    channel = capture.channels[7]
    normalized = list(channel.carrier_phase_advance_nyquist_fraction)
    normalized[20] += 1e-9
    object.__setattr__(
        channel,
        "carrier_phase_advance_nyquist_fraction",
        tuple(normalized),
    )

    with pytest.raises(ValueError, match="phase normalization changed"):
        settle_auditory_event_boundary(
            capture,
            pressure_uncertainty_full_scale=PRESSURE_UNCERTAINTY_FULL_SCALE,
        )


def test_old_provider_or_event_authority_fails_closed() -> None:
    capture, boundary = _settle(_surrounded_tone())
    object.__setattr__(capture, "provider_schema", "v1")
    with pytest.raises(ValueError, match="provider schema changed"):
        settle_auditory_event_boundary(
            capture,
            pressure_uncertainty_full_scale=PRESSURE_UNCERTAINTY_FULL_SCALE,
        )

    old_boundary = dataclasses.replace(boundary, provider_schema="v1")
    with pytest.raises(ValueError, match="provider schema changed"):
        old_boundary.verify()


def test_event_without_measured_ambient_on_both_sides_fails_closed() -> None:
    time_axis = np.arange(REQUIRED_SAMPLE_RATE_HZ) / REQUIRED_SAMPLE_RATE_HZ
    event = 0.25 * np.sin(2.0 * math.pi * 440.0 * time_axis)
    trailing = np.zeros(20 * OBSERVATION_HOP_SAMPLES, dtype=np.float64)

    with pytest.raises(ValueError, match="not surrounded"):
        _settle(np.concatenate((event, trailing)))


def test_one_unvarying_physical_basin_fails_closed() -> None:
    signal = np.zeros(REQUIRED_SAMPLE_RATE_HZ, dtype=np.float64)

    with pytest.raises(ValueError, match="only one physical basin"):
        _settle(signal)
