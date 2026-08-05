"""Low-level numeric sensory waveform compatibility.

This module deliberately contains no word-to-sense dictionaries and no
descriptor lookup authority.  A label, object name, sentence, atlas entry, or
hash is never accepted as sensory evidence.

The tactile and visual helpers remain only as numeric transducers for callers
that already possess measured physical receptor values.  Olfactory and
gustatory generation is retired here because receptor activation must now come
from authenticated material transport/contact physics.  Inventing chemical
receptor activity from a mapping supplied by language was the prohibited
legacy mechanism that made fabricated experience accumulate as learned state.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np


class RetiredSemanticSensoryGeneration(RuntimeError):
    """Raised when a caller attempts to synthesize a sense from parameters."""


_TACTILE_PHYSICAL_AXES = frozenset(
    {
        "temperature",
        "pressure",
        "texture_freq",
        "sharpness",
        "wetness",
    }
)
_VISUAL_PHYSICAL_AXES = frozenset(
    {
        "luminance",
        "edge_density",
        "form_complexity",
        "contrast",
        "shape_coherence",
    }
)


def _finite_unit_interval(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a measured numeric value")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0:
        raise ValueError(f"{field_name} must be finite and within [0, 1]")
    return numeric


def _validated_physical_mapping(
    values: object,
    *,
    allowed_axes: frozenset[str],
    modality: str,
) -> dict[str, float]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{modality} input must be a physical-axis mapping")
    unknown = set(values) - allowed_axes
    if unknown:
        raise ValueError(
            f"{modality} input contains non-physical or unknown axes: "
            f"{sorted(str(item) for item in unknown)}"
        )
    return {
        axis: _finite_unit_interval(value, field_name=f"{modality}.{axis}")
        for axis, value in values.items()
    }


def generate_touch_waveform(
    params: Mapping[str, float],
    n_samples: int = 200,
    sample_rate: int = 100,
) -> dict[str, np.ndarray]:
    """Transduce already-measured tactile axes into temporal receptor curves.

    This does not decide what an object should feel like.  Temperature,
    pressure, surface frequency, edge acuity, and moisture must already have
    been measured by a physical contact provider.  The function only models
    receptor onset/adaptation over the requested sample interval.
    """

    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 2:
        raise ValueError("n_samples must be an integer of at least 2")
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError("sample_rate must be a positive integer")
    measured = _validated_physical_mapping(
        params,
        allowed_axes=_TACTILE_PHYSICAL_AXES,
        modality="touch",
    )
    duration = (n_samples - 1) / sample_rate
    t = np.linspace(0.0, duration, n_samples)

    temperature = measured.get("temperature", 0.5)
    thermal_delta = temperature - 0.5
    thermal_rate = 1.0 + abs(thermal_delta)

    pressure = measured.get("pressure", 0.0)
    pressure_onset = 1.0 - np.exp(-t * sample_rate / n_samples)
    pressure_adaptation = np.exp(-t / (duration + (1.0 / sample_rate)))

    texture = measured.get("texture_freq", 0.0)
    texture_hz = texture * (sample_rate / 2.0)

    sharpness = measured.get("sharpness", 0.0)
    pulse_width = 1.0 / sample_rate

    wetness = measured.get("wetness", 0.0)

    return {
        "pressure": pressure * pressure_onset * pressure_adaptation,
        "sharpness": sharpness * np.exp(-((t - pulse_width) / pulse_width) ** 2),
        "temperature": 0.5
        + thermal_delta * (1.0 - np.exp(-thermal_rate * t)),
        "texture": texture * np.sin(2.0 * math.pi * texture_hz * t),
        "wetness": wetness * (1.0 - np.exp(-t / (duration + (1.0 / sample_rate)))),
    }


def generate_smell_waveform(*_args: object, **_kwargs: object) -> dict[str, np.ndarray]:
    """Refuse the retired descriptor/profile olfactory generator."""

    raise RetiredSemanticSensoryGeneration(
        "olfactory receptor activity requires authenticated material emission "
        "and environmental transport evidence"
    )


def generate_taste_waveform(*_args: object, **_kwargs: object) -> dict[str, np.ndarray]:
    """Refuse the retired descriptor/profile gustatory generator."""

    raise RetiredSemanticSensoryGeneration(
        "gustatory receptor activity requires authenticated oral contact, "
        "dissolution, and material evidence"
    )


def generate_sensory_signals(*_args: object, **_kwargs: object) -> dict[str, np.ndarray]:
    """Refuse every legacy descriptor-selection sensory request."""

    raise RetiredSemanticSensoryGeneration(
        "word and descriptor selections cannot create sensory evidence"
    )


def generate_visual_waveform(
    params: Mapping[str, float],
    n_samples: int = 200,
    sample_rate: int = 100,
) -> dict[str, np.ndarray]:
    """Transduce already-measured optical axes without label-derived noise."""

    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 2:
        raise ValueError("n_samples must be an integer of at least 2")
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate <= 0:
        raise ValueError("sample_rate must be a positive integer")
    measured = _validated_physical_mapping(
        params,
        allowed_axes=_VISUAL_PHYSICAL_AXES,
        modality="visual",
    )
    duration = (n_samples - 1) / sample_rate
    t = np.linspace(0.0, duration, n_samples)
    signals: dict[str, np.ndarray] = {}
    for channel, intensity in sorted(measured.items()):
        if intensity == 0.0:
            signals[channel] = np.zeros(n_samples)
            continue
        rise_rate = sample_rate / n_samples
        adaptation_rate = intensity / (duration + (1.0 / sample_rate))
        signals[channel] = (
            intensity
            * (1.0 - np.exp(-rise_rate * t))
            * np.exp(-adaptation_rate * t)
        )
    return signals


def transduce_sensory_signals(*_args: object, **_kwargs: object) -> dict[str, object]:
    """Refuse the retired winding-modulo-chi identity conversion."""

    raise RetiredSemanticSensoryGeneration(
        "sensory identity cannot be reduced to legacy winding modulo chi"
    )


__all__ = (
    "RetiredSemanticSensoryGeneration",
    "generate_sensory_signals",
    "generate_smell_waveform",
    "generate_taste_waveform",
    "generate_touch_waveform",
    "generate_visual_waveform",
    "transduce_sensory_signals",
)
