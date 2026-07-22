from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from dsf_ai_service.substrate.auditory_event_boundary import (
    settle_auditory_event_boundary,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
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


def test_boundary_receipt_binds_the_complete_native_capture() -> None:
    _, boundary = _settle(_surrounded_tone())

    altered = dataclasses.replace(
        boundary,
        event_frame_end=boundary.event_frame_end - 1,
    )
    with pytest.raises(ValueError, match="receipt changed"):
        altered.verify()


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
