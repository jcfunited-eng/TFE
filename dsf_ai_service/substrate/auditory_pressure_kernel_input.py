"""Exact auditory-pressure transduction into the unchanged UF kernel.

The generic native-sensory adapter admits signed unit signals by mapping
``s`` to ``1 + s/2``.  A cochlear pressure envelope is not a signed unit
coordinate: it is a nonnegative physical magnitude measured by a PCM16
sensor.  Adding one sensor quantum and expressing the result as a ratio to
that same quantum gives the positive dimensionless field required by L0:

    F = (pressure + q) / q = 1 + pressure / q

where ``q = 1 / 32768`` full scale.  The map is exact, monotone, invertible,
and has a direct sensor-physics meaning.  Multiplying ``F`` by any constant
unit scale changes only the additive origin of L0's logarithm, not its
structural derivatives.

This module does not execute or modify L0--L4.  It owns only the auditory
domain transduction and its immutable receipt description.
"""

from __future__ import annotations

import json
from fractions import Fraction

from dsf_ai_service.glew_runtime.closed_experience import (
    KernelNativeInputMap,
)


AUDITORY_PRESSURE_KERNEL_INPUT_SCHEMA = (
    "guala.auditory.pressure_kernel_input.v1"
)
PCM16_FULL_SCALE_PRESSURE_QUANTUM = Fraction(1, 32_768)
MIN_DIMENSIONLESS_PRESSURE_FIELD = Fraction(1)
MAX_DIMENSIONLESS_PRESSURE_FIELD = Fraction(32_769)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


AUDITORY_PRESSURE_KERNEL_INPUT_PROFILE = _canonical_bytes({
    "forward": "F=(pressure+q)/q",
    "inverse": "pressure=q*(F-1)",
    "pressure_range": "[0,1]",
    "q_full_scale": _fraction_text(
        PCM16_FULL_SCALE_PRESSURE_QUANTUM
    ),
    "result_range": "[1,32769]",
    "schema": AUDITORY_PRESSURE_KERNEL_INPUT_SCHEMA,
    "sensor_quantization": "signed-pcm16-full-scale",
})

AUDITORY_PRESSURE_KERNEL_INPUT_MAP = KernelNativeInputMap(
    map_id="pcm16-pressure-quantum-ratio-v1",
    source_min=Fraction(0),
    source_max=Fraction(1),
    field_offset=Fraction(1),
    field_scale=Fraction(32_768),
    profile_payload=AUDITORY_PRESSURE_KERNEL_INPUT_PROFILE,
)


def auditory_pressure_dimensionless_field(
    pressure_full_scale: Fraction,
) -> Fraction:
    """Map one exact nonnegative pressure envelope to its PCM quantum ratio."""
    if not isinstance(pressure_full_scale, Fraction):
        raise TypeError("auditory pressure must be an exact Fraction")
    if not 0 <= pressure_full_scale <= 1:
        raise ValueError("auditory pressure left its full-scale calibration")
    field = AUDITORY_PRESSURE_KERNEL_INPUT_MAP.forward(
        pressure_full_scale
    )
    if not (
        MIN_DIMENSIONLESS_PRESSURE_FIELD
        <= field
        <= MAX_DIMENSIONLESS_PRESSURE_FIELD
    ):
        raise RuntimeError("auditory pressure ratio left its exact boundary")
    return field


def pressure_full_scale_from_dimensionless_field(
    dimensionless_field: Fraction,
) -> Fraction:
    """Invert the exact PCM-quantum pressure map."""
    if not isinstance(dimensionless_field, Fraction):
        raise TypeError("auditory pressure field must be an exact Fraction")
    if not (
        MIN_DIMENSIONLESS_PRESSURE_FIELD
        <= dimensionless_field
        <= MAX_DIMENSIONLESS_PRESSURE_FIELD
    ):
        raise ValueError("auditory pressure field left its calibrated range")
    pressure = AUDITORY_PRESSURE_KERNEL_INPUT_MAP.inverse(
        dimensionless_field
    )
    if not 0 <= pressure <= 1:
        raise RuntimeError("auditory pressure inverse left full scale")
    return pressure


__all__ = (
    "AUDITORY_PRESSURE_KERNEL_INPUT_MAP",
    "AUDITORY_PRESSURE_KERNEL_INPUT_PROFILE",
    "AUDITORY_PRESSURE_KERNEL_INPUT_SCHEMA",
    "MAX_DIMENSIONLESS_PRESSURE_FIELD",
    "MIN_DIMENSIONLESS_PRESSURE_FIELD",
    "PCM16_FULL_SCALE_PRESSURE_QUANTUM",
    "auditory_pressure_dimensionless_field",
    "pressure_full_scale_from_dimensionless_field",
)
