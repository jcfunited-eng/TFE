from __future__ import annotations

from fractions import Fraction

import numpy as np

from dsf_ai_service.substrate.senses import auditory_full_field_provider as provider
from tools.probe_auditory_receptor_topology_census import (
    _absence_audit,
    _coefficients,
    _native_inputs,
    _state_cost,
    _transduce,
)


def _physical_signal() -> np.ndarray:
    index = np.arange(320, dtype=np.float64)
    return 0.25 * np.sin(
        2.0 * np.pi * 733.0 * index / provider.REQUIRED_SAMPLE_RATE_HZ
    )


def test_sixteen_channel_census_reproduces_canonical_recurrence_exactly() -> None:
    signal = _physical_signal()
    capture = _transduce(signal, 16)
    envelopes, phases, advances = provider._cochlear_state_python(signal)
    advances[0].fill(0.0)
    assert np.array_equal(capture.envelopes, envelopes)
    assert np.array_equal(capture.cumulative_phase_turns, phases)
    assert np.array_equal(capture.phase_advance_turns, advances)


def test_declared_topologies_preserve_erb_endpoints_and_full_ports() -> None:
    for channel_count in (16, 32, 64, 128):
        centres, widths, poles, injection = _coefficients(channel_count)
        assert len(centres) == len(widths) == len(poles) == len(injection)
        assert len(centres) == channel_count
        assert abs(
            centres[0] - provider.LOWEST_CENTRE_FREQUENCY_HZ
        ) < 1e-11
        assert abs(
            centres[-1] - provider.HIGHEST_CENTRE_FREQUENCY_HZ
        ) < 1e-11
        capture = _transduce(_physical_signal(), channel_count)
        mounted = _native_inputs(capture, source_anchor=Fraction(0))
        assert len(mounted) == channel_count * 2
        assert tuple(value.topology_index for value in mounted) == tuple(
            range(channel_count * 2)
        )


def test_resource_state_is_fixed_and_linear_in_channel_count() -> None:
    prior = _state_cost(16, 100)
    for channel_count in (32, 64, 128):
        current = _state_cost(channel_count, 100)
        ratio = channel_count // 16
        assert current["persistent_filter_state_bytes"] == (
            prior["persistent_filter_state_bytes"] * ratio
        )
        assert current["one_capture_output_binary64_bytes"] == (
            prior["one_capture_output_binary64_bytes"] * ratio
        )


def test_canonical_provider_has_neither_missing_physical_operator() -> None:
    audit = _absence_audit()
    assert not audit[
        "canonical_provider_has_deterministic_inner_hair_cell_adaptation"
    ]
    assert not audit[
        "canonical_provider_has_cross_band_formant_trajectory_operator"
    ]
    assert not any(audit["source_identifier_presence"].values())
