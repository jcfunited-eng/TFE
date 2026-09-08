"""Exact six-band retinal source for the lean Guala runtime."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from typing import Any

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.guala_physical_sensorium import RETINAL_PORTS
from dsf_ai_service.substrate.w1_physical_receptors import (
    OPTICAL_BANDS,
    RETINA_TOTAL_RECEPTOR_COUNT,
    physical_receptor_joint_units,
)


SPECTRAL_RETINAL_PORTS = RETINA_TOTAL_RECEPTOR_COUNT * OPTICAL_BANDS
SPECTRAL_RETINAL_TOPOLOGY_OFFSET = RETINAL_PORTS


def _exact_binary64(value: object, label: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float, Fraction)):
        raise TypeError(f"{label} is not numeric")
    return Fraction.from_float(float(value))


def _retime(
    stream: NativeSensorySubstreamInput,
    *,
    source_times: tuple[Fraction, ...],
    before_transmission: Fraction,
    after_transmission: Fraction,
    transition_time: Fraction | None,
) -> NativeSensorySubstreamInput:
    if len(stream.normalized_signal) != 2:
        raise RuntimeError("W1 spectral retinal endpoint count changed")
    before = _exact_binary64(
        stream.normalized_signal[0], "W1 spectral predecessor"
    ) * before_transmission
    after = _exact_binary64(
        stream.normalized_signal[1], "W1 spectral successor"
    ) * after_transmission
    if any(not Fraction(0) <= value <= Fraction(1) for value in (before, after)):
        raise RuntimeError("W1 spectral retinal value left physical bounds")
    if transition_time is None:
        if before != after:
            raise RuntimeError("passive spectral retina changed within one snapshot")
        values = (after,) * len(source_times)
    else:
        values = tuple(
            before if source_time < transition_time else after
            for source_time in source_times
        )
    count = len(values)
    return replace(
        stream,
        source_times=source_times,
        normalized_signal=tuple(float(value) for value in values),
        phase_turns=tuple(Fraction(index, count) for index in range(count)),
        source_relevance=None,
        source_relevance_rule="exact-unit-source-relevance.v1",
        source_relevance_origin_substream_id=None,
        exact_physical_signal=None,
    )


def settle_spectral_retina(
    *,
    assembly_id: str,
    streams: tuple[NativeSensorySubstreamInput, ...],
    source_times: tuple[Fraction, ...],
    before_transmission: Fraction,
    after_transmission: Fraction | None = None,
    transition_time: Fraction | None = None,
) -> Any:
    """Settle all six optical bands per site without a grayscale projection."""

    if (
        not source_times
        or any(not isinstance(value, Fraction) for value in source_times)
        or any(
            right <= left
            for left, right in zip(source_times, source_times[1:])
        )
    ):
        raise ValueError("spectral retina requires one exact increasing clock")
    successor_transmission = (
        before_transmission
        if after_transmission is None
        else after_transmission
    )
    if any(
        not isinstance(value, Fraction) or not Fraction(0) <= value <= Fraction(1)
        for value in (before_transmission, successor_transmission)
    ):
        raise ValueError("eyelid transmission left its physical range")
    if transition_time is not None and not isinstance(transition_time, Fraction):
        raise TypeError("spectral retinal transition time is not exact")
    if (
        len(streams) != SPECTRAL_RETINAL_PORTS
        or tuple(stream.sense for stream in streams)
        != (PhysicalSense.SIGHT,) * SPECTRAL_RETINAL_PORTS
        or tuple(stream.topology_index for stream in streams)
        != tuple(range(SPECTRAL_RETINAL_PORTS))
    ):
        raise RuntimeError("W1 spectral retinal topology changed")
    retimed = tuple(
        replace(
            _retime(
                stream,
                source_times=source_times,
                before_transmission=before_transmission,
                after_transmission=successor_transmission,
                transition_time=transition_time,
            ),
            topology_index=(
                SPECTRAL_RETINAL_TOPOLOGY_OFFSET + stream.topology_index
            ),
        )
        for stream in streams
    )
    observed = {PhysicalSense.SIGHT: retimed}
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    occurrences = declare_joint_source_occurrences(
        observed_substreams=observed,
        declared_units=physical_receptor_joint_units(observed),
    )
    if len(occurrences) != RETINA_TOTAL_RECEPTOR_COUNT:
        raise RuntimeError("six-band retinal sites lost joint occurrence custody")
    return settle_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed,
        states=states,
        occurrences=occurrences,
    )


def spectral_retina_admissions(
    maximum_causal_interval: Fraction,
) -> list[tuple[int, int]]:
    """Declare one identical exact causal bound per physical retinal site."""

    if (
        not isinstance(maximum_causal_interval, Fraction)
        or maximum_causal_interval <= 0
    ):
        raise ValueError("spectral retinal admission must be positive and exact")
    numerator = maximum_causal_interval.numerator
    denominator = maximum_causal_interval.denominator
    if not -(1 << 63) <= numerator < (1 << 63) or not 0 < denominator < (1 << 63):
        raise ValueError("spectral retinal admission exceeds native i64 custody")
    return [(numerator, denominator)] * RETINA_TOTAL_RECEPTOR_COUNT


def spectral_retina_u8_observation(
    *,
    streams: tuple[NativeSensorySubstreamInput, ...],
    transmission: Fraction,
) -> tuple[int, ...]:
    """Project the latest exact six-band field for bounded human observation."""

    if (
        len(streams) != SPECTRAL_RETINAL_PORTS
        or tuple(stream.topology_index for stream in streams)
        != tuple(range(SPECTRAL_RETINAL_PORTS))
        or not isinstance(transmission, Fraction)
        or not Fraction(0) <= transmission <= Fraction(1)
    ):
        raise ValueError("spectral retinal observation changed its exact extent")
    result = []
    for stream in streams:
        if stream.sense is not PhysicalSense.SIGHT or not stream.normalized_signal:
            raise ValueError("spectral retinal observation crossed anatomy")
        value = _exact_binary64(
            stream.normalized_signal[-1], "spectral retinal observation"
        ) * transmission
        if not Fraction(0) <= value <= Fraction(1):
            raise ValueError("spectral retinal observation left physical bounds")
        result.append(round(value * 255))
    return tuple(result)


__all__ = (
    "SPECTRAL_RETINAL_PORTS",
    "SPECTRAL_RETINAL_TOPOLOGY_OFFSET",
    "settle_spectral_retina",
    "spectral_retina_admissions",
    "spectral_retina_u8_observation",
)
