from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    AUDITORY_KERNEL_MOUNT_SCHEMA,
    auditory_kernel_component_inputs,
    auditory_kernel_component_records,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


def _capture():
    sample_count = OBSERVATION_HOP_SAMPLES * 3
    time = np.arange(sample_count, dtype=np.float64) / REQUIRED_SAMPLE_RATE_HZ
    signal = 0.4 * np.sin(2.0 * np.pi * 440.0 * time)
    return transduce_auditory_full_field(
        signal, sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ
    )


def test_mount_is_interleaved_complete_and_keeps_components_separate() -> None:
    capture = _capture()
    anchor = Fraction(7, 3)

    mounted = auditory_kernel_component_inputs(capture, source_anchor=anchor)

    assert len(mounted) == AUDITORY_KERNEL_COMPONENT_COUNT == 32
    assert tuple(item.topology_index for item in mounted) == tuple(range(32))
    assert tuple(item.substream_id for item in mounted[:4]) == (
        "erb_00_pressure",
        "erb_00_phase_advance",
        "erb_01_pressure",
        "erb_01_phase_advance",
    )
    pressure, phase = mounted[:2]
    source_times = tuple(
        anchor + Fraction(value, 1_000_000_000)
        for value in capture.channels[0].causal_offsets_ns
    )
    assert pressure.source_times == phase.source_times == source_times
    assert pressure.normalized_signal == (
        capture.channels[0].pressure_envelope_full_scale
    )
    assert phase.normalized_signal == (
        capture.channels[0].carrier_phase_advance_nyquist_fraction
    )
    assert pressure.phase_turns == (Fraction(0),) * capture.frame_count
    assert phase.phase_turns == tuple(
        Fraction.from_float(value)
        for value in capture.channels[0].carrier_phase_advance_turns
    )
    assert ("kernel-component", "pressure-envelope") in tuple(
        (item.axis_id, item.coordinate_id) for item in pressure.coordinates
    )
    assert ("kernel-component", "carrier-phase-advance") in tuple(
        (item.axis_id, item.coordinate_id) for item in phase.coordinates
    )
    assert pressure.physical_quantity == "cochlear-pressure-envelope"
    assert phase.physical_quantity == "cochlear-carrier-phase-advance"


def test_serialized_records_are_exact_deterministic_v2_inputs() -> None:
    capture = _capture()
    anchor = Fraction(1_234_567_891, 1_000_000_000)

    first = auditory_kernel_component_records(capture, source_anchor=anchor)
    second = auditory_kernel_component_records(capture, source_anchor=anchor)

    assert first == second
    assert all(value["schema"] == AUDITORY_KERNEL_MOUNT_SCHEMA for value in first)
    assert first[0]["source_anchor_fraction"] == [
        anchor.numerator,
        anchor.denominator,
    ]
    assert first[0]["causal_offsets_fraction"] == [
        [Fraction(value, 1_000_000_000).numerator,
         Fraction(value, 1_000_000_000).denominator]
        for value in capture.channels[0].causal_offsets_ns
    ]
    assert first[0]["normalized_signal"] == list(
        capture.channels[0].pressure_envelope_full_scale
    )
    assert first[1]["normalized_signal"] == list(
        capture.channels[0].carrier_phase_advance_nyquist_fraction
    )
    assert "chi" not in first[0]
    first[0]["normalized_signal"][0] = -1.0
    assert auditory_kernel_component_records(
        capture, source_anchor=anchor
    ) == second


def test_mount_fails_closed_on_nonexact_time_and_tampered_phase_normalization() -> None:
    capture = _capture()
    with pytest.raises(TypeError, match="exact Fraction"):
        auditory_kernel_component_inputs(capture, source_anchor=1.0)  # type: ignore[arg-type]

    channel = capture.channels[0]
    changed = list(channel.carrier_phase_advance_nyquist_fraction)
    changed[-1] = 1.0 if changed[-1] != 1.0 else -1.0
    object.__setattr__(
        channel,
        "carrier_phase_advance_nyquist_fraction",
        tuple(changed),
    )
    with pytest.raises(ValueError, match="normalization changed"):
        auditory_kernel_component_records(
            capture, source_anchor=Fraction(0)
        )
