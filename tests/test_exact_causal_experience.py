from __future__ import annotations

import math
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    MAX_NATIVE_SAMPLES_PER_SUBSTREAM,
    NativeSensorySubstreamInput,
    build_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)


def _boundary(
    assembly_id: str,
    *,
    frequency: int = 8,
    coordinate: str = "center",
    physical_unit: str = "normalized-intensity",
):
    sample_count = 96
    signal = tuple(
        math.sin(2 * math.pi * frequency * index / 200)
        for index in range(sample_count)
    )
    sight = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="test-camera",
        substream_id="fixation-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("fixation", coordinate),),
        physical_quantity="light-intensity",
        physical_unit=physical_unit,
        source_times=tuple(Fraction(index, 200)
                           for index in range(sample_count)),
        normalized_signal=signal,
        phase_turns=tuple(Fraction(index // 12)
                          for index in range(sample_count)),
    )
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    return build_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=Fraction(0),
        source_time_end=Fraction(sample_count, 200),
        observed_substreams={PhysicalSense.SIGHT: (sight,)},
        states=states,
    )


def test_exact_identity_excludes_chi_source_and_event_bookkeeping() -> None:
    accepted = []
    owner = ExactCausalExperienceOwner(
        on_settlement=accepted.append,
        log_event=lambda *_args, **_kwargs: None,
    )

    first = owner.settle(
        _boundary("capture-one"),
        routing_chis=(3,),
        source_tags=("joe_voice",),
    )
    repeated = owner.settle(
        _boundary("capture-two"),
        routing_chis=(91,),
        source_tags=("ambient",),
    )

    assert first.structural_fingerprint == repeated.structural_fingerprint
    assert first.event_id != repeated.event_id
    assert first.routing_chis != repeated.routing_chis
    assert first.source_tags != repeated.source_tags
    assert repeated.interpretations[0].relation == "recurrence"
    first.verify()
    repeated.verify()
    assert len(first.receipt_registry.records) == 2
    assert owner.status()["settled"] == 2
    assert accepted == [first, repeated]


def test_one_exact_field_change_is_structural_change() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    owner.settle(
        _boundary("capture-one", frequency=8),
        routing_chis=(),
        source_tags=(),
    )
    changed = owner.settle(
        _boundary("capture-two", frequency=9),
        routing_chis=(),
        source_tags=(),
    )

    assert changed.interpretations[0].relation == "structural_change"


def test_physical_topology_is_structural_but_capture_source_is_not() -> None:
    owner = ExactCausalExperienceOwner(
        on_settlement=lambda _settlement: None,
        log_event=lambda *_args, **_kwargs: None,
    )
    first = owner.settle(
        _boundary("capture-one"),
        routing_chis=(7,),
        source_tags=("camera-a",),
    )
    moved = owner.settle(
        _boundary("capture-two", coordinate="upper-left"),
        routing_chis=(91,),
        source_tags=("camera-b",),
    )
    unit_changed = owner.settle(
        _boundary("capture-three", coordinate="upper-left", physical_unit="lux"),
        routing_chis=(3,),
        source_tags=("camera-c",),
    )

    assert first.structural_fingerprint != moved.structural_fingerprint
    assert moved.structural_fingerprint != unit_changed.structural_fingerprint
    assert moved.interpretations[0].relation == "structural_change"
    assert unit_changed.interpretations[0].relation == "structural_change"


def test_one_oversized_native_substream_is_rejected_before_receipt_growth() -> None:
    count = MAX_NATIVE_SAMPLES_PER_SUBSTREAM + 1
    with pytest.raises(ValueError, match="settlement sample boundary"):
        NativeSensorySubstreamInput(
            sense=PhysicalSense.SOUND,
            sensor_id="test-microphone",
            substream_id="band-0",
            topology_index=0,
            coordinates=(NativeAxisCoordinate("frequency", "440-hz"),),
            physical_quantity="sound-pressure",
            physical_unit="normalized-amplitude",
            source_times=tuple(Fraction(index, 200) for index in range(count)),
            normalized_signal=(0.0,) * count,
            phase_turns=(Fraction(0),) * count,
        )
