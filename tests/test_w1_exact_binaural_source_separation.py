from __future__ import annotations

import math
import struct
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralSeparationState,
    ExactBinauralTransferPath,
    mount_exact_separated_auditory_fields,
    separate_exact_binaural_sources,
)


SAMPLE_COUNT = 960


def _source(frequency_hz: int) -> tuple[int, ...]:
    return tuple(
        4 * int(
            1_500 * math.sin(
                2 * math.pi * frequency_hz * index / 16_000
            )
        )
        for index in range(SAMPLE_COUNT)
    )


def _pcm(values: tuple[int, ...]) -> bytes:
    return struct.pack(f"<{len(values)}h", *values)


def _render(
    sources: tuple[tuple[int, ...], tuple[int, ...]],
    paths: tuple[ExactBinauralTransferPath, ExactBinauralTransferPath],
) -> tuple[bytes, bytes]:
    maximum_delay = max(
        paths[0].left_delay_samples,
        paths[0].right_delay_samples,
        paths[1].left_delay_samples,
        paths[1].right_delay_samples,
    )
    capture_count = SAMPLE_COUNT + maximum_delay
    ears: list[bytes] = []
    for ear in ("left", "right"):
        values: list[int] = []
        for capture_index in range(capture_count):
            pressure = Fraction(0)
            for source, path in zip(sources, paths, strict=True):
                delay = (
                    path.left_delay_samples
                    if ear == "left" else path.right_delay_samples
                )
                attenuation = (
                    path.left_attenuation
                    if ear == "left" else path.right_attenuation
                )
                source_index = capture_index - delay
                if 0 <= source_index < SAMPLE_COUNT:
                    pressure += attenuation * source[source_index]
            assert pressure.denominator == 1
            values.append(pressure.numerator)
        ears.append(_pcm(tuple(values)))
    return ears[0], ears[1]


def test_two_overlapping_sources_separate_exactly_and_mount_full_dsf_fields():
    sources = (_source(440), _source(730))
    paths = (
        ExactBinauralTransferPath(
            left_delay_samples=0,
            right_delay_samples=0,
            left_attenuation=Fraction(1),
            right_attenuation=Fraction(1, 2),
        ),
        ExactBinauralTransferPath(
            left_delay_samples=0,
            right_delay_samples=0,
            left_attenuation=Fraction(1, 2),
            right_attenuation=Fraction(1),
        ),
    )
    left, right = _render(sources, paths)

    result = separate_exact_binaural_sources(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert result.state is ExactBinauralSeparationState.SEPARATED
    assert result.separated_pcm_s16le == tuple(
        _pcm(value) for value in sources
    )
    result.verify()

    fields = mount_exact_separated_auditory_fields(
        result,
        source_time_start=Fraction(11),
    )
    assert len(fields) == 2
    assert (
        fields[0].auditory_l5.structural_fingerprint
        != fields[1].auditory_l5.structural_fingerprint
    )
    for field in fields:
        field.verify()
        assert all(
            tuple(name for name, _value in field_tuple.fields)
            == DSF_FIELD_ORDER
            for channel in field.auditory_l5.channels
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            )
            for field_tuple in component.l4_field_tuples
        )


def test_opposing_interaural_delays_recover_concurrent_sources_with_closed_tail():
    sources = (_source(390), _source(910))
    paths = (
        ExactBinauralTransferPath(
            left_delay_samples=0,
            right_delay_samples=3,
            left_attenuation=Fraction(1),
            right_attenuation=Fraction(1),
        ),
        ExactBinauralTransferPath(
            left_delay_samples=3,
            right_delay_samples=0,
            left_attenuation=Fraction(1),
            right_attenuation=Fraction(1),
        ),
    )
    left, right = _render(sources, paths)

    result = separate_exact_binaural_sources(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert result.state is ExactBinauralSeparationState.SEPARATED
    assert result.separated_pcm_s16le == tuple(
        _pcm(value) for value in sources
    )
    result.verify()


def test_mono_capture_refuses_two_source_release_and_has_two_decompositions():
    first = _source(440)
    second = _source(660)
    mono = tuple(
        left + right for left, right in zip(first, second, strict=True)
    )
    paths = (
        ExactBinauralTransferPath(
            0, 0, Fraction(1), Fraction(1)
        ),
        ExactBinauralTransferPath(
            0, 0, Fraction(1), Fraction(1)
        ),
    )

    result = separate_exact_binaural_sources(
        left_pcm_s16le=_pcm(mono),
        right_pcm_s16le=None,
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert result.state is (
        ExactBinauralSeparationState
        .INDETERMINATE_INSUFFICIENT_SENSORS
    )
    assert result.separated_pcm_s16le == ()
    assert tuple(a + b for a, b in zip(first, second, strict=True)) == mono
    assert tuple(a + b for a, b in zip(mono, (0,) * SAMPLE_COUNT)) == mono
    with pytest.raises(
        ValueError,
        match="indeterminate binaural evidence",
    ):
        mount_exact_separated_auditory_fields(
            result,
            source_time_start=Fraction(0),
        )


def test_identical_two_ear_paths_are_nonunique_and_release_nothing():
    sources = (_source(440), _source(660))
    same_path = ExactBinauralTransferPath(
        0, 0, Fraction(1, 2), Fraction(1, 2)
    )
    paths = (same_path, same_path)
    left, right = _render(sources, paths)

    result = separate_exact_binaural_sources(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert result.state is (
        ExactBinauralSeparationState
        .INDETERMINATE_NONUNIQUE_TRANSFER
    )
    assert result.separated_pcm_s16le == ()
    result.verify()


def test_redundant_closed_tail_rejects_path_inconsistent_pressure():
    sources = (_source(390), _source(910))
    paths = (
        ExactBinauralTransferPath(
            0, 3, Fraction(1), Fraction(1)
        ),
        ExactBinauralTransferPath(
            3, 0, Fraction(1), Fraction(1)
        ),
    )
    left, right = _render(sources, paths)
    altered = list(struct.unpack(f"<{len(right) // 2}h", right))
    altered[-1] += 1

    result = separate_exact_binaural_sources(
        left_pcm_s16le=left,
        right_pcm_s16le=_pcm(tuple(altered)),
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert result.state is (
        ExactBinauralSeparationState
        .INDETERMINATE_INCONSISTENT_EVIDENCE
    )
    assert result.separated_pcm_s16le == ()
    result.verify()


def test_unique_nonintegral_inverse_is_not_released_as_pcm():
    paths = (
        ExactBinauralTransferPath(
            0, 0, Fraction(1), Fraction(1, 2)
        ),
        ExactBinauralTransferPath(
            0, 0, Fraction(1, 2), Fraction(1)
        ),
    )
    left = _pcm((1,) * SAMPLE_COUNT)
    right = _pcm((0,) * SAMPLE_COUNT)

    result = separate_exact_binaural_sources(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )

    assert result.state is (
        ExactBinauralSeparationState
        .INDETERMINATE_PCM_QUANTIZATION
    )
    assert result.separated_pcm_s16le == ()
    result.verify()


def test_separation_receipt_rejects_altered_recovered_pressure():
    sources = (_source(440), _source(730))
    paths = (
        ExactBinauralTransferPath(
            0, 0, Fraction(1), Fraction(1, 2)
        ),
        ExactBinauralTransferPath(
            0, 0, Fraction(1, 2), Fraction(1)
        ),
    )
    left, right = _render(sources, paths)
    result = separate_exact_binaural_sources(
        left_pcm_s16le=left,
        right_pcm_s16le=right,
        paths=paths,
        source_sample_count=SAMPLE_COUNT,
    )
    altered_samples = list(struct.unpack(
        f"<{SAMPLE_COUNT}h",
        result.separated_pcm_s16le[0],
    ))
    altered_samples[10] += 1
    changed = replace(
        result,
        separated_pcm_s16le=(
            _pcm(tuple(altered_samples)),
            result.separated_pcm_s16le[1],
        ),
    )

    with pytest.raises(
        ValueError,
        match="separation authority changed",
    ):
        changed.verify()
