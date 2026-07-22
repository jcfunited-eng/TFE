from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SOUND_SUBSTREAMS,
    MAX_NATIVE_SUBSTREAMS_PER_SENSE,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)


def _port(sense: PhysicalSense, index: int) -> NativeSensorySubstreamInput:
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"test-{sense.value}-sensor",
        substream_id=f"component-{index:02d}",
        topology_index=index,
        coordinates=(NativeAxisCoordinate("component", str(index)),),
        physical_quantity="bounded-test-component",
        physical_unit="normalized",
        source_times=(Fraction(1, 100), Fraction(2, 100), Fraction(3, 100)),
        normalized_signal=(0.0, 0.25, -0.25),
        phase_turns=(Fraction(0), Fraction(0), Fraction(0)),
    )


def _build(sense: PhysicalSense, count: int):
    return build_six_sense_full_field(
        assembly_id=f"capacity-{sense.value}-{count}",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        observed_substreams={
            sense: tuple(_port(sense, index) for index in range(count))
        },
        states={
            candidate: (
                SenseBoundaryState.OBSERVED
                if candidate is sense
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for candidate in SENSE_ORDER
        },
    )


def test_sound_admits_exactly_thirty_two_bounded_components() -> None:
    built = _build(PhysicalSense.SOUND, MAX_NATIVE_SOUND_SUBSTREAMS)

    built.boundary.verify(built.receipt_registry)
    sound = next(
        boundary
        for boundary in built.boundary.boundaries
        if boundary.sense is PhysicalSense.SOUND
    )
    assert len(sound.substreams) == 32


def test_sound_rejects_thirty_third_component_before_building() -> None:
    with pytest.raises(ValueError, match="topology exceeds"):
        _build(PhysicalSense.SOUND, MAX_NATIVE_SOUND_SUBSTREAMS + 1)


def test_non_sound_senses_keep_the_sixteen_component_boundary() -> None:
    with pytest.raises(ValueError, match="topology exceeds"):
        _build(PhysicalSense.SIGHT, MAX_NATIVE_SUBSTREAMS_PER_SENSE + 1)
