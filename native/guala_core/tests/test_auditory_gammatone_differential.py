"""Strict differential contract for the native causal gammatone provider.

The Python implementation is the operation-order oracle and the production
fallback. Carrier phase must remain bit-identical, including signed-zero
behavior after an impulse decays into the subnormal range. Block RMS permits
only the final scalar-hypot rounding difference documented below.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import guala_core
from dsf_ai_service.substrate.senses import auditory_full_field_provider as provider


RNG = np.random.default_rng(20260721)
SAMPLE_RATE = provider.REQUIRED_SAMPLE_RATE_HZ
ENVELOPE_ABSOLUTE_TOLERANCE = 2.0e-16


def _differential(signal: np.ndarray) -> None:
    python_envelopes, python_phases = provider._cochlear_state_python(signal)
    native_envelopes, native_phases = provider._cochlear_state_native(signal)

    assert native_envelopes.shape == python_envelopes.shape
    assert native_phases.shape == python_phases.shape
    np.testing.assert_allclose(
        native_envelopes,
        python_envelopes,
        rtol=0.0,
        atol=ENVELOPE_ABSOLUTE_TOLERANCE,
    )
    assert np.array_equal(native_phases, python_phases)
    assert np.signbit(native_phases).tolist() == np.signbit(python_phases).tolist()


def test_silence_and_subnormal_impulse_phase_are_exact() -> None:
    _differential(np.zeros(SAMPLE_RATE, dtype=np.float64))
    impulse = np.zeros(SAMPLE_RATE, dtype=np.float64)
    impulse[0] = 1.0
    _differential(impulse)


def test_tone_noise_and_incomplete_hop_match_the_python_oracle() -> None:
    time_axis = np.arange(SAMPLE_RATE, dtype=np.float64) / SAMPLE_RATE
    tone = 0.73 * np.sin(
        2.0 * math.pi * 1_234.0 * time_axis + 0.37
    )
    _differential(tone)
    _differential(RNG.uniform(-1.0, 1.0, SAMPLE_RATE * 5))
    _differential(RNG.uniform(-1.0, 1.0, SAMPLE_RATE + 73))


def test_maximum_capture_matches_without_field_loss() -> None:
    maximum = RNG.uniform(
        -1.0,
        1.0,
        SAMPLE_RATE * provider.MAX_CAPTURE_SECONDS,
    )
    _differential(maximum)


def test_fallback_is_selected_only_when_native_symbol_is_absent(monkeypatch) -> None:
    signal = RNG.uniform(-1.0, 1.0, SAMPLE_RATE // 10)
    expected = provider._cochlear_state_python(signal)
    monkeypatch.setattr(provider, "_native_gammatone_field", None)
    actual = provider._cochlear_state(signal)
    assert np.array_equal(actual[0], expected[0])
    assert np.array_equal(actual[1], expected[1])


def test_native_runtime_error_is_not_hidden_by_fallback(monkeypatch) -> None:
    signal = np.zeros(provider.OBSERVATION_HOP_SAMPLES, dtype=np.float64)

    def fail_native(*_args):
        raise RuntimeError("native auditory failure")

    def forbidden_fallback(_values):
        raise AssertionError("runtime native failure selected fallback")

    monkeypatch.setattr(provider, "_native_gammatone_field", fail_native)
    monkeypatch.setattr(provider, "_cochlear_state_python", forbidden_fallback)
    with pytest.raises(RuntimeError, match="native auditory failure"):
        provider._cochlear_state(signal)


def test_native_boundary_rejects_changed_channel_topology() -> None:
    with pytest.raises(ValueError, match="sixteen"):
        guala_core.auditory_gammatone_field(
            [0.0] * provider.OBSERVATION_HOP_SAMPLES,
            [0.0] * 15,
            [0.0] * 15,
            [0.0] * 15,
        )
