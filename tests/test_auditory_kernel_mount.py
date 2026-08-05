from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    AUDITORY_KERNEL_MOUNT_SCHEMA,
    auditory_kernel_component_inputs,
    auditory_kernel_component_records,
    auditory_kernel_mount,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    PAIRED_SOURCE_RELEVANCE_RULE,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)
from dsf_ai_service.substrate.window_manager import (
    WindowManager,
    physical_topology_fact,
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
        for value in capture.channels[0].carrier_phase_turns
    )
    expected_relevance = tuple(
        Fraction.from_float(value) ** 2
        for value in capture.channels[0].pressure_envelope_full_scale
    )
    assert pressure.source_relevance == phase.source_relevance
    assert pressure.source_relevance == expected_relevance
    assert pressure.source_relevance_rule == PAIRED_SOURCE_RELEVANCE_RULE
    assert phase.source_relevance_rule == PAIRED_SOURCE_RELEVANCE_RULE
    assert pressure.source_relevance_origin_substream_id == pressure.substream_id
    assert phase.source_relevance_origin_substream_id == pressure.substream_id
    assert ("kernel-component", "pressure-envelope") in tuple(
        (item.axis_id, item.coordinate_id) for item in pressure.coordinates
    )
    assert ("kernel-component", "carrier-phase-advance") in tuple(
        (item.axis_id, item.coordinate_id) for item in phase.coordinates
    )
    assert pressure.physical_quantity == "cochlear-pressure-envelope"
    assert phase.physical_quantity == "cochlear-carrier-phase-advance"


def test_serialized_records_are_exact_deterministic_v4_inputs() -> None:
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
    expected_relevance = [
        [
            (Fraction.from_float(value) ** 2).numerator,
            (Fraction.from_float(value) ** 2).denominator,
        ]
        for value in capture.channels[0].pressure_envelope_full_scale
    ]
    assert first[0]["source_relevance_fraction"] == expected_relevance
    assert first[1]["source_relevance_fraction"] == expected_relevance
    assert first[0]["source_relevance_rule"] == PAIRED_SOURCE_RELEVANCE_RULE
    assert first[1]["source_relevance_rule"] == PAIRED_SOURCE_RELEVANCE_RULE
    assert first[0]["source_relevance_origin_substream_id"] == (
        "erb_00_pressure"
    )
    assert first[1]["source_relevance_origin_substream_id"] == (
        "erb_00_pressure"
    )
    assert first[1]["phase_turns"] == list(
        capture.channels[0].carrier_phase_turns
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


def test_typed_mount_custody_is_byte_exact_and_cannot_cross_windows() -> None:
    capture = _capture()
    mount = auditory_kernel_mount(
        capture,
        source_anchor=Fraction(13, 7),
    )
    settled = []
    manager = WindowManager(
        log_event_fn=lambda *_args, **_kwargs: None,
        get_tick_fn=lambda: 0,
        settle_window_fn=lambda record: settled.append((
            record,
            manager._settlement_custodies_for_record(record),
        )),
    )
    manager.begin_context("request:one", "sound")
    indices = tuple(
        manager.add_entry(
            modality="sound",
            topology=physical_topology_fact(record),
            full_field=record,
            context_id="request:one",
        )
        for record in mount.records
    )
    manager.bind_settlement_custody(
        "request:one",
        indices,
        mount,
    )
    manager.end_context("request:one", "complete")

    public_native = tuple(
        entry["full_field"]
        for entry in settled[0][0]["entries"]
    )
    assert public_native == mount.records
    bound = settled[0][1][0]
    assert tuple(
        native for _index, native in bound.inputs_for_settlement(
            window_id=settled[0][0]["window_id"],
            context_id="request:one",
        )
    ) == mount.native_inputs
    with pytest.raises(RuntimeError, match="left its bound causal window"):
        bound.inputs_for_settlement(
            window_id="window:other-request",
            context_id="request:two",
        )

    manager.begin_context("request:two", "sound")
    replay_indices = tuple(
        manager.add_entry(
            modality="sound",
            topology=physical_topology_fact(record),
            full_field=record,
            context_id="request:two",
        )
        for record in mount.records
    )
    with pytest.raises(RuntimeError, match="already bound"):
        manager.bind_settlement_custody(
            "request:two",
            replay_indices,
            mount,
        )
