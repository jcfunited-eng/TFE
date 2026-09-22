"""Three-channel browser light delivered to Guala's six-band retina."""

from __future__ import annotations

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
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.guala_spectral_retina import (
    SPECTRAL_RETINAL_PORTS,
    SPECTRAL_RETINAL_TOPOLOGY_OFFSET,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    OPTICAL_BANDS,
    RETINAL_REFERENCE_IRRADIANCE_UNIT,
    RETINA_COLUMNS,
    RETINA_FINE_COLUMNS,
    RETINA_RECEPTOR_COUNT,
    RETINA_TOTAL_RECEPTOR_COUNT,
)


RGB_CHANNELS = ("red", "green", "blue")
EXTERNAL_RGB_VALUE_COUNT = RETINA_TOTAL_RECEPTOR_COUNT * len(RGB_CHANNELS)
EXTERNAL_RGB_RETINAL_PORTS = SPECTRAL_RETINAL_PORTS


def _validate_rgb(values: tuple[int, ...]) -> None:
    if (
        not isinstance(values, tuple)
        or len(values) != EXTERNAL_RGB_VALUE_COUNT
        or any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 255
            for value in values
        )
    ):
        raise ValueError("external retinal RGB changed its 135-site triplet field")


def rgb_retina_luminance_u8(values: tuple[int, ...]) -> tuple[int, ...]:
    """Retain the established 135-site achromatic receptors from RGB codes."""

    _validate_rgb(values)
    return tuple(
        (
            values[index] * 299
            + values[index + 1] * 587
            + values[index + 2] * 114
            + 500
        )
        // 1_000
        for index in range(0, len(values), 3)
    )


def transmitted_rgb_retina_u8(
    values: tuple[int, ...], transmission: Fraction
) -> tuple[int, ...]:
    """Return the bounded browser RGB field visible past the eyelids."""

    _validate_rgb(values)
    if not isinstance(transmission, Fraction) or not 0 <= transmission <= 1:
        raise ValueError("external retinal transmission left physical bounds")
    return tuple(round(Fraction(value) * transmission) for value in values)


def _site_identity(
    site_index: int,
) -> tuple[str, tuple[NativeAxisCoordinate, ...]]:
    if site_index < RETINA_RECEPTOR_COUNT:
        row = site_index // RETINA_COLUMNS
        column = site_index % RETINA_COLUMNS
        name = f"retinal-cell-{row}-{column}"
        row_coordinate = str(row)
        column_coordinate = str(column)
    else:
        fine_index = site_index - RETINA_RECEPTOR_COUNT
        row = fine_index // RETINA_FINE_COLUMNS
        column = fine_index % RETINA_FINE_COLUMNS
        name = f"retinal-fine-{row}-{column}"
        row_coordinate = f"fine-{row}"
        column_coordinate = f"fine-{column}"
    return name, (
        NativeAxisCoordinate("retinal-row", row_coordinate),
        NativeAxisCoordinate("retinal-column", column_coordinate),
    )


def settle_external_rgb_retina(
    *,
    assembly_id: str,
    rgb_u8: tuple[int, ...],
    source_times: tuple[Fraction, ...],
    transmission: Fraction,
) -> Any:
    """Project ideal RGB display primaries onto the one six-band retina.

    This is an authored display spectrum: blue reaches bands 0/1, green
    reaches 2/3, and red reaches 4/5. It does not reconstruct the unknown
    spectrum of the camera's real-world subject.
    """

    _validate_rgb(rgb_u8)
    if (
        not source_times
        or any(not isinstance(value, Fraction) for value in source_times)
        or any(right <= left for left, right in zip(source_times, source_times[1:]))
    ):
        raise ValueError("external RGB retina requires one exact increasing clock")
    if not isinstance(transmission, Fraction) or not 0 <= transmission <= 1:
        raise ValueError("external RGB retinal transmission left physical bounds")
    phase_turns = tuple(
        Fraction(index, len(source_times)) for index in range(len(source_times))
    )
    streams = []
    for site_index in range(RETINA_TOTAL_RECEPTOR_COUNT):
        name, site_coordinates = _site_identity(site_index)
        red, green, blue = rgb_u8[site_index * 3:site_index * 3 + 3]
        band_values = (blue, blue, green, green, red, red)
        for band, channel_value in enumerate(band_values):
            local_index = site_index * OPTICAL_BANDS + band
            value = Fraction(channel_value, 255) * transmission
            streams.append(
                NativeSensorySubstreamInput(
                    sense=PhysicalSense.SIGHT,
                    sensor_id="W1-retina",
                    substream_id=f"{name}-band-{band}",
                    topology_index=(
                        SPECTRAL_RETINAL_TOPOLOGY_OFFSET + local_index
                    ),
                    coordinates=(
                        *site_coordinates,
                        NativeAxisCoordinate("optical-band", str(band)),
                    ),
                    physical_quantity="retinal-spectral-irradiance",
                    physical_unit=RETINAL_REFERENCE_IRRADIANCE_UNIT,
                    source_times=source_times,
                    normalized_signal=(float(value),) * len(source_times),
                    phase_turns=phase_turns,
                )
            )
    observed = {PhysicalSense.SIGHT: tuple(streams)}
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    units = tuple(
        tuple(
            (
                PhysicalSense.SIGHT,
                SPECTRAL_RETINAL_TOPOLOGY_OFFSET
                + site_index * OPTICAL_BANDS
                + band,
            )
            for band in range(OPTICAL_BANDS)
        )
        for site_index in range(RETINA_TOTAL_RECEPTOR_COUNT)
    )
    occurrences = declare_joint_source_occurrences(
        observed_substreams=observed,
        declared_units=units,
    )
    return settle_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed,
        states=states,
        occurrences=occurrences,
    )


def external_rgb_retina_admissions(
    maximum_causal_interval: Fraction,
) -> list[tuple[int, int]]:
    """Declare one identical causal bound for each spatial light occurrence."""

    if (
        not isinstance(maximum_causal_interval, Fraction)
        or maximum_causal_interval <= 0
    ):
        raise ValueError("external RGB retinal admission must be positive and exact")
    numerator = maximum_causal_interval.numerator
    denominator = maximum_causal_interval.denominator
    if not -(1 << 63) <= numerator < (1 << 63) or not 0 < denominator < (1 << 63):
        raise ValueError("external RGB retinal admission exceeds native i64 custody")
    return [(numerator, denominator)] * RETINA_TOTAL_RECEPTOR_COUNT


__all__ = (
    "EXTERNAL_RGB_RETINAL_PORTS",
    "EXTERNAL_RGB_VALUE_COUNT",
    "RGB_CHANNELS",
    "external_rgb_retina_admissions",
    "rgb_retina_luminance_u8",
    "settle_external_rgb_retina",
    "transmitted_rgb_retina_u8",
)
