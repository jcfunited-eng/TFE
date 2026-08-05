"""Proofs for the exact PCM-quantum auditory pressure input map."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from dsf_ai_service.substrate.auditory_pressure_kernel_input import (
    AUDITORY_PRESSURE_KERNEL_INPUT_PROFILE,
    MAX_DIMENSIONLESS_PRESSURE_FIELD,
    MIN_DIMENSIONLESS_PRESSURE_FIELD,
    PCM16_FULL_SCALE_PRESSURE_QUANTUM,
    auditory_pressure_dimensionless_field,
    pressure_full_scale_from_dimensionless_field,
)


def test_pressure_map_has_exact_sensor_endpoints_and_inverse() -> None:
    assert auditory_pressure_dimensionless_field(Fraction(0)) == (
        MIN_DIMENSIONLESS_PRESSURE_FIELD
    )
    assert auditory_pressure_dimensionless_field(Fraction(1)) == (
        MAX_DIMENSIONLESS_PRESSURE_FIELD
    )
    values = (
        Fraction(0),
        PCM16_FULL_SCALE_PRESSURE_QUANTUM,
        Fraction(1, 100),
        Fraction(1, 2),
        Fraction(1),
    )
    assert tuple(
        pressure_full_scale_from_dimensionless_field(
            auditory_pressure_dimensionless_field(value)
        )
        for value in values
    ) == values


def test_pressure_map_preserves_exact_order_and_ratios() -> None:
    values = tuple(
        PCM16_FULL_SCALE_PRESSURE_QUANTUM * value
        for value in (0, 1, 2, 4, 8, 16)
    )
    fields = tuple(
        auditory_pressure_dimensionless_field(value)
        for value in values
    )
    assert all(
        left < right for left, right in zip(fields, fields[1:])
    )
    assert fields == tuple(Fraction(1 + value) for value in (0, 1, 2, 4, 8, 16))


def test_pressure_profile_states_only_the_exact_physical_map() -> None:
    profile = json.loads(AUDITORY_PRESSURE_KERNEL_INPUT_PROFILE)
    assert profile == {
        "forward": "F=(pressure+q)/q",
        "inverse": "pressure=q*(F-1)",
        "pressure_range": "[0,1]",
        "q_full_scale": "1/32768",
        "result_range": "[1,32769]",
        "schema": "guala.auditory.pressure_kernel_input.v1",
        "sensor_quantization": "signed-pcm16-full-scale",
    }


@pytest.mark.parametrize(
    "value",
    (
        Fraction(-1, 32_768),
        Fraction(32_769, 32_768),
    ),
)
def test_pressure_map_rejects_values_outside_sensor_calibration(
    value: Fraction,
) -> None:
    with pytest.raises(ValueError):
        auditory_pressure_dimensionless_field(value)


def test_pressure_map_rejects_non_exact_inputs() -> None:
    with pytest.raises(TypeError):
        auditory_pressure_dimensionless_field(0.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        pressure_full_scale_from_dimensionless_field(1.0)  # type: ignore[arg-type]
