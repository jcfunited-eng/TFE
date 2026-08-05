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
    python_envelopes, python_phases, python_advances = (
        provider._cochlear_state_python(signal)
    )
    native_envelopes, native_phases, native_advances = (
        provider._cochlear_state_native(signal)
    )

    assert native_envelopes.shape == python_envelopes.shape
    assert native_phases.shape == python_phases.shape
    assert native_advances.shape == python_advances.shape
    np.testing.assert_allclose(
        native_envelopes,
        python_envelopes,
        rtol=0.0,
        atol=ENVELOPE_ABSOLUTE_TOLERANCE,
    )
    assert np.array_equal(native_phases, python_phases)
    assert np.signbit(native_phases).tolist() == np.signbit(python_phases).tolist()
    assert np.array_equal(native_advances, python_advances)
    assert np.signbit(native_advances).tolist() == np.signbit(
        python_advances
    ).tolist()


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


def test_native_stream_is_exactly_invariant_to_non_hop_chunk_partitions() -> None:
    signal = RNG.uniform(-0.9, 0.9, SAMPLE_RATE * 6 + 73)
    pole, injection = provider._cochlear_coefficients()
    state = provider._zero_continuation_state()
    state = (*state[:7], state[-1])
    cuts = (17_333, 61_777, len(signal))
    start = 0
    stream_envelopes = []
    stream_phases = []
    stream_advances = []
    for end in cuts:
        result = guala_core.auditory_gammatone_stream(
            signal[start:end].tolist(),
            pole.real.tolist(),
            pole.imag.tolist(),
            injection.tolist(),
            state[0].reshape(-1).tolist(),
            state[1].reshape(-1).tolist(),
            state[2].tolist(),
            state[3].tolist(),
            state[4].tolist(),
            state[5].tolist(),
            state[6].tolist(),
            state[7],
        )
        stream_envelopes.extend(result[0])
        stream_phases.extend(result[1])
        stream_advances.extend(result[2])
        state = (
            np.asarray(result[3]).reshape((4, 16)),
            np.asarray(result[4]).reshape((4, 16)),
            np.asarray(result[5]),
            np.asarray(result[6]),
            np.asarray(result[7]),
            np.asarray(result[8]),
            np.asarray(result[9]),
            result[10],
        )
        start = end

    unsplit_envelopes, unsplit_phases, unsplit_advances = (
        provider._cochlear_state_native(signal)
    )
    assert np.array_equal(np.asarray(stream_envelopes), unsplit_envelopes)
    assert np.array_equal(np.asarray(stream_phases), unsplit_phases)
    assert np.array_equal(np.asarray(stream_advances), unsplit_advances)


def test_native_stream_state_matches_python_reference_across_chunks() -> None:
    signal = RNG.uniform(-0.8, 0.8, SAMPLE_RATE * 2 + 91)
    initial = provider._zero_continuation_state()
    python_state = (*initial[:7], initial[-1])
    native_state = (*initial[:7], initial[-1])
    for start, end in ((0, 7_111), (7_111, 21_333), (21_333, len(signal))):
        python_result = provider._cochlear_stream_python(
            signal[start:end], *python_state
        )
        native_result = provider._cochlear_stream_native(
            signal[start:end], *native_state
        )
        np.testing.assert_allclose(
            native_result[0], python_result[0], rtol=0.0,
            atol=ENVELOPE_ABSOLUTE_TOLERANCE,
        )
        assert np.array_equal(native_result[1], python_result[1])
        assert np.array_equal(native_result[2], python_result[2])
        for native_values, python_values in zip(
            native_result[3:10], python_result[3:10], strict=True
        ):
            np.testing.assert_allclose(
                native_values, python_values, rtol=0.0,
                atol=ENVELOPE_ABSOLUTE_TOLERANCE,
            )
        assert native_result[10] == python_result[10]
        python_state = (*python_result[3:10], python_result[10])
        native_state = (*native_result[3:10], native_result[10])


def test_550_hz_decay_reaches_nyquist_exactly_without_crossing_it() -> None:
    signal = np.asarray(
        [0] * (20 * provider.OBSERVATION_HOP_SAMPLES)
        + [
            int(8_000 * math.sin(2.0 * math.pi * 550.0 * index / SAMPLE_RATE))
            for index in range(SAMPLE_RATE)
        ]
        + [0] * (30 * provider.OBSERVATION_HOP_SAMPLES),
        dtype=np.float64,
    ) / 32768.0

    _, _, python_advances = provider._cochlear_state_python(signal)
    _, _, native_advances = provider._cochlear_state_native(signal)

    assert np.array_equal(native_advances, python_advances)
    assert np.max(np.abs(native_advances)) == (
        provider.PHASE_ADVANCE_NYQUIST_TURNS_PER_HOP
    )
    assert native_advances[145, 15] == 80.0


def test_hop_motion_is_independent_of_unbounded_absolute_phase_coordinate() -> None:
    signal = RNG.uniform(-0.8, 0.8, SAMPLE_RATE + 73)
    initial = provider._zero_continuation_state()
    initial_state = (*initial[:7], initial[-1])
    prefix = provider._cochlear_stream_python(signal[:317], *initial_state)
    base_state = (*prefix[3:10], prefix[10])
    shifted_state = (
        *base_state[:4],
        base_state[4] + 2.0 ** 52,
        *base_state[5:],
    )

    base = provider._cochlear_stream_python(signal[317:], *base_state)
    shifted = provider._cochlear_stream_python(signal[317:], *shifted_state)

    assert np.array_equal(base[2], shifted[2])
    assert np.array_equal(base[9], shifted[9])
