from __future__ import annotations

import math

import numpy as np
import pytest

from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


def _tone(
    frequency_hz: float,
    amplitude: float,
    *,
    phase: float = 0.0,
    duration_seconds: float = 1.0,
) -> np.ndarray:
    sample_count = int(REQUIRED_SAMPLE_RATE_HZ * duration_seconds)
    time_axis = np.arange(sample_count, dtype=np.float64) / REQUIRED_SAMPLE_RATE_HZ
    return amplitude * np.sin(2.0 * math.pi * frequency_hz * time_axis + phase)


def _mean_pressures(capture) -> np.ndarray:
    return np.asarray([
        np.mean(channel.pressure_envelope_full_scale[20:])
        for channel in capture.channels
    ])


def _nearest_channel(frequency_hz: float) -> int:
    return min(
        range(len(AUDITORY_CHANNELS)),
        key=lambda index: abs(AUDITORY_CHANNELS[index].centre_hz - frequency_hz),
    )


def test_distinct_physical_frequencies_do_not_alias_to_one_channel() -> None:
    lower = transduce_auditory_full_field(
        _tone(440.0, 0.5), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    upper = transduce_auditory_full_field(
        _tone(1_800.0, 0.5), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )

    assert int(np.argmax(_mean_pressures(lower))) == _nearest_channel(440.0)
    assert int(np.argmax(_mean_pressures(upper))) == _nearest_channel(1_800.0)
    assert tuple(
        item.pressure_envelope_full_scale for item in lower.channels
    ) != tuple(item.pressure_envelope_full_scale for item in upper.channels)


def test_one_shared_calibration_preserves_relative_amplitude() -> None:
    quiet = transduce_auditory_full_field(
        _tone(440.0, 0.2), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    loud = transduce_auditory_full_field(
        _tone(440.0, 0.6), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    channel_index = _nearest_channel(440.0)
    quiet_values = np.asarray(
        quiet.channels[channel_index].pressure_envelope_full_scale
    )
    loud_values = np.asarray(
        loud.channels[channel_index].pressure_envelope_full_scale
    )
    assert np.allclose(loud_values, quiet_values * 3.0, rtol=1e-11, atol=1e-13)


def test_native_rate_phase_winding_retains_carrier_frequency() -> None:
    frequency_hz = 1_000.0
    capture = transduce_auditory_full_field(
        _tone(frequency_hz, 0.5, duration_seconds=2.0),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    channel = capture.channels[_nearest_channel(frequency_hz)]
    phase = np.asarray(channel.carrier_phase_turns)
    elapsed_seconds = (
        channel.causal_offsets_ns[-1] - channel.causal_offsets_ns[50]
    ) / 1_000_000_000
    measured_hz = (phase[-1] - phase[50]) / elapsed_seconds
    assert measured_hz == pytest.approx(frequency_hz, abs=0.5)


def test_phase_is_independent_from_pressure_envelope() -> None:
    first = transduce_auditory_full_field(
        _tone(440.0, 0.5, phase=0.0), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    shifted = transduce_auditory_full_field(
        _tone(440.0, 0.5, phase=math.pi / 2),
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    channel_index = _nearest_channel(440.0)
    assert np.allclose(
        first.channels[channel_index].pressure_envelope_full_scale[20:],
        shifted.channels[channel_index].pressure_envelope_full_scale[20:],
        rtol=5e-4,
        atol=1e-9,
    )
    assert first.channels[channel_index].carrier_phase_turns != (
        shifted.channels[channel_index].carrier_phase_turns
    )


def test_all_channels_share_one_bounded_causal_grid() -> None:
    eight_seconds = np.zeros(REQUIRED_SAMPLE_RATE_HZ * 8, dtype=np.float64)
    capture = transduce_auditory_full_field(
        eight_seconds, sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    expected_frames = len(eight_seconds) // OBSERVATION_HOP_SAMPLES
    assert capture.frame_count == expected_frames == 800
    assert len(capture.channels) == COCHLEAR_CHANNEL_COUNT == 16
    assert len(capture.channels) * expected_frames == 12_800
    assert all(
        channel.causal_offsets_ns == capture.channels[0].causal_offsets_ns
        for channel in capture.channels
    )
    assert all(
        not any(channel.pressure_envelope_full_scale)
        for channel in capture.channels
    )


def test_provider_is_deterministic_and_fails_closed_outside_contract() -> None:
    signal = _tone(1_250.0, 0.4)
    left = transduce_auditory_full_field(
        signal, sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    right = transduce_auditory_full_field(
        signal.copy(), sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )
    assert left == right

    with pytest.raises(ValueError, match="16 kHz"):
        transduce_auditory_full_field(signal, sample_rate_hz=48_000)
    with pytest.raises(ValueError, match="mono"):
        transduce_auditory_full_field(
            np.zeros((OBSERVATION_HOP_SAMPLES, 2)),
            sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        )
    with pytest.raises(ValueError, match="eight-second"):
        transduce_auditory_full_field(
            np.zeros(REQUIRED_SAMPLE_RATE_HZ * 8 + 1),
            sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
        )
