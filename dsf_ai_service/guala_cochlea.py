"""Bounded physical cochlear transduction for one lean-runtime hop."""

from __future__ import annotations

from fractions import Fraction
import math
import struct
from typing import NamedTuple

from guala_core import auditory_gammatone_field


SAMPLE_RATE_HZ = 16_000
HOP_SAMPLES = 4_000
OBSERVATION_SAMPLES = 160
CHANNELS_PER_EAR = 16
EAR_COUNT = 2
LOWEST_CENTRE_HZ = 80.0
HIGHEST_CENTRE_HZ = 7_500.0
PRESSURE_LATTICE = 1 << 24


class CochlearChannel(NamedTuple):
    centre_hz: float
    erb_width_hz: float


def _erb_width_hz(frequency_hz: float) -> float:
    return 24.7 * (1.0 + 4.37e-3 * frequency_hz)


def _erb_rate(frequency_hz: float) -> float:
    return 21.4 * math.log10(1.0 + 4.37e-3 * frequency_hz)


def _frequency_from_erb_rate(rate: float) -> float:
    return (10.0 ** (rate / 21.4) - 1.0) / 4.37e-3


def _channels() -> tuple[CochlearChannel, ...]:
    lower = _erb_rate(LOWEST_CENTRE_HZ)
    upper = _erb_rate(HIGHEST_CENTRE_HZ)
    return tuple(
        CochlearChannel(
            centre := _frequency_from_erb_rate(
                lower + (upper - lower) * index / (CHANNELS_PER_EAR - 1)
            ),
            _erb_width_hz(centre),
        )
        for index in range(CHANNELS_PER_EAR)
    )


def _coefficients() -> tuple[list[float], list[float], list[float]]:
    pole_real: list[float] = []
    pole_imaginary: list[float] = []
    injection: list[float] = []
    for channel in _channels():
        radius = math.exp(
            -2.0 * math.pi * 1.019 * channel.erb_width_hz / SAMPLE_RATE_HZ
        )
        angle = 2.0 * math.pi * channel.centre_hz / SAMPLE_RATE_HZ
        pole_real.append(radius * math.cos(angle))
        pole_imaginary.append(radius * math.sin(angle))
        injection.append(1.0 - radius)
    return pole_real, pole_imaginary, injection


def one_self_hearing_hop(
    pressure_s16le: bytes,
) -> tuple[
    tuple[Fraction, ...],
    tuple[float, ...],
    tuple[tuple[float, ...], ...],
    int,
]:
    """Transduce at most one 250 ms slice; return exact consumed samples."""

    if not isinstance(pressure_s16le, bytes) or not pressure_s16le:
        raise ValueError("self-hearing pressure is empty")
    if len(pressure_s16le) % 2:
        raise ValueError("self-hearing pressure changed signed-16 width")
    sample_count = len(pressure_s16le) // 2
    raw = struct.unpack(f"<{sample_count}h", pressure_s16le)
    consumed = min(sample_count, HOP_SAMPLES)
    samples = list(raw[:consumed])
    samples.extend([0] * (HOP_SAMPLES - len(samples)))
    indices = tuple(range(0, HOP_SAMPLES + 1, OBSERVATION_SAMPLES))
    times = tuple(Fraction(index, SAMPLE_RATE_HZ) for index in indices)
    legacy = tuple(
        (samples[index] if index < HOP_SAMPLES else 0) / 32768.0
        for index in indices
    )
    signal = [value / 32768.0 for value in samples]
    pole_real, pole_imaginary, injection = _coefficients()
    envelopes, _phases, _advances = auditory_gammatone_field(
        signal + [0.0] * OBSERVATION_SAMPLES,
        pole_real,
        pole_imaginary,
        injection,
    )
    lattice = float(PRESSURE_LATTICE)
    quantized: list[tuple[float, ...]] = []
    for frame in envelopes:
        row = []
        for value in frame:
            level = round(value * lattice)
            if level < 0 or level > PRESSURE_LATTICE:
                raise ValueError(
                    "cochlear envelope left its declared pressure lattice"
                )
            row.append(level / lattice)
        quantized.append(tuple(row))
    if len(quantized) <= HOP_SAMPLES // OBSERVATION_SAMPLES:
        raise RuntimeError("cochlear transduction ended before the hop boundary")
    one_ear = tuple(
        tuple(quantized[index][channel] for index in range(len(indices)))
        for channel in range(CHANNELS_PER_EAR)
    )
    return times, legacy, one_ear * EAR_COUNT, consumed
