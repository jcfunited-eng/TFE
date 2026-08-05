from __future__ import annotations

from fractions import Fraction

import numpy as np

from dsf_ai_service.substrate.senses import auditory_full_field_provider as provider
from tools.probe_auditory_cross_band_relation_walkup import (
    RELATION_NAMES,
    RELATION_PORT_COUNT,
    _relation_native_inputs,
    _relation_trajectory,
)
from tools.probe_auditory_ihc_adaptation_walkup import (
    IHC_FIELDS,
    IHC_PORT_COUNT,
    _ihc_native_inputs,
    _ihc_trajectory,
    _ihc_transduce,
)
from tools.probe_auditory_receptor_topology_census import _transduce


def _physical_signal() -> np.ndarray:
    index = np.arange(320, dtype=np.float64)
    return (
        0.20
        * np.sin(
            2.0
            * np.pi
            * 733.0
            * index
            / provider.REQUIRED_SAMPLE_RATE_HZ
        )
        + 0.10
        * np.sin(
            2.0
            * np.pi
            * 1_301.0
            * index
            / provider.REQUIRED_SAMPLE_RATE_HZ
        )
    )


def test_cross_band_field_retains_every_adjacent_pair_and_relation() -> None:
    capture = _transduce(_physical_signal(), provider.COCHLEAR_CHANNEL_COUNT)
    trajectory = _relation_trajectory(capture)
    assert len(trajectory) == RELATION_PORT_COUNT
    assert {lane[3] for lane in trajectory} == set(RELATION_NAMES)
    assert all(
        len(values) == capture.observation_count
        and all(Fraction(-1) <= value <= Fraction(1) for value in values)
        for values in trajectory.values()
    )
    mounted = _relation_native_inputs(
        capture,
        trajectory,
        source_anchor=Fraction(0),
    )
    assert len(mounted) == RELATION_PORT_COUNT
    assert tuple(value.topology_index for value in mounted) == tuple(
        range(RELATION_PORT_COUNT)
    )


def test_cross_band_projective_motion_has_exact_causal_genesis() -> None:
    capture = _transduce(_physical_signal(), provider.COCHLEAR_CHANNEL_COUNT)
    trajectory = _relation_trajectory(capture)
    assert all(
        values[0] == 0
        for lane, values in trajectory.items()
        if lane[3] in (
            "envelope_crossing",
            "projective_amplitude_motion",
        )
    )


def test_ihc_field_is_deterministic_complete_and_parameter_free() -> None:
    signal = _physical_signal()
    left = _ihc_transduce(signal)
    right = _ihc_transduce(signal.copy())
    for field_name in IHC_FIELDS:
        assert np.array_equal(
            getattr(left, field_name),
            getattr(right, field_name),
        )
    trajectory = _ihc_trajectory(left)
    assert len(trajectory) == IHC_PORT_COUNT
    assert {lane[3] for lane in trajectory} == set(IHC_FIELDS)
    mounted = _ihc_native_inputs(
        left,
        trajectory,
        source_anchor=Fraction(0),
    )
    assert len(mounted) == IHC_PORT_COUNT
    assert tuple(value.topology_index for value in mounted) == tuple(
        range(IHC_PORT_COUNT)
    )


def test_ihc_silence_has_exact_zero_potential_and_release() -> None:
    capture = _ihc_transduce(np.zeros(320, dtype=np.float64))
    for field_name in IHC_FIELDS:
        assert np.count_nonzero(getattr(capture, field_name)) == 0
