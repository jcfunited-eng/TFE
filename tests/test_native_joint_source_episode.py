from __future__ import annotations

from dataclasses import fields
from fractions import Fraction
from types import SimpleNamespace

import pytest

import dsf_ai_service.glew_runtime.native_joint_source_episode as source_module
from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    NativeJointSourceOccurrenceInput,
    UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
    encode_native_joint_source_episode,
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)


TIMES = tuple(Fraction(index, 4) for index in range(4))
JOINT_PROFILE = b"guala.test.explicit_joint_relevance.v1"
INTERSAMPLE_PROFILE = UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR


def _input(sense: PhysicalSense, topology_index: int) -> NativeSensorySubstreamInput:
    values = (0.0, 0.5, -0.25, 1.0)
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"{sense.value}-organ",
        substream_id=f"{sense.value}-{topology_index}",
        topology_index=topology_index,
        coordinates=(
            NativeAxisCoordinate("receptor", str(topology_index)),
        ),
        physical_quantity="normalized_physical_excitation",
        physical_unit="normalized_binary64",
        source_times=TIMES,
        normalized_signal=values,
        phase_turns=(Fraction(0),) * 4,
    )


def _boundary():
    observed = {
        PhysicalSense.SIGHT: (
            _input(PhysicalSense.SIGHT, 0),
            _input(PhysicalSense.SIGHT, 1),
        ),
        PhysicalSense.SOUND: (_input(PhysicalSense.SOUND, 0),),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    return observed, states


def _occurrence(
    *,
    port_indices: tuple[int, ...] = (0, 1, 2),
    source_times: tuple[Fraction, ...] = TIMES,
    groups: tuple[tuple[int, ...], ...] = ((0, 1), (2,)),
    relevance: tuple[Fraction, ...] = (
        Fraction(1, 4),
        Fraction(1, 2),
        Fraction(3, 4),
        Fraction(1),
    ),
    profile: bytes = JOINT_PROFILE,
    intersample: bytes = INTERSAMPLE_PROFILE,
) -> NativeJointSourceOccurrenceInput:
    return NativeJointSourceOccurrenceInput(
        port_indices=port_indices,
        source_times=source_times,
        joint_intersample_profile_payload=intersample,
        groups=groups,
        joint_relevance_profile_payload=profile,
        joint_relevance=relevance,
    )


def _encode(
    occurrences: tuple[NativeJointSourceOccurrenceInput, ...],
    *,
    assembly_id: str = "joint-source-test",
):
    observed, states = _boundary()
    return encode_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed,
        states=states,
        occurrences=occurrences,
    )


def test_gljsrc02_encodes_only_explicit_joint_occurrence_authority() -> None:
    candidate, ports, samples, occurrence_count, occurrence_frames = _encode(
        (_occurrence(),)
    )

    assert candidate.startswith(b"GLJSRC02\x02\x00")
    assert b"GLJSRC01" not in candidate
    assert ports == 3
    assert samples == 12
    assert occurrence_count == 1
    assert occurrence_frames == 4
    assert tuple(field.name for field in fields(NativeJointSourceOccurrenceInput)) == (
        "port_indices",
        "source_times",
        "joint_intersample_profile_payload",
        "groups",
        "joint_relevance_profile_payload",
        "joint_relevance",
    )
    assert "contact" not in " ".join(
        field.name for field in fields(NativeJointSourceOccurrenceInput)
    )


def test_joint_relevance_and_profile_change_exact_source_body() -> None:
    baseline = _encode((_occurrence(),))[0]
    changed_relevance = _encode(
        (_occurrence(relevance=(Fraction(0),) * 4),)
    )[0]
    changed_profile = _encode(
        (_occurrence(profile=b"guala.test.other_joint_relevance.v1"),)
    )[0]

    assert baseline != changed_relevance
    assert baseline != changed_profile
    assert changed_relevance != changed_profile


def test_missing_occurrence_argument_has_no_default() -> None:
    observed, states = _boundary()
    with pytest.raises(TypeError, match="occurrences"):
        encode_native_joint_source_episode(
            assembly_id="missing-occurrence",
            observed_substreams=observed,
            states=states,
        )


@pytest.mark.parametrize(
    "occurrences, message",
    (
        ((), "do not cover"),
        (
            (
                _occurrence(
                    port_indices=(0, 1),
                    groups=((0, 1),),
                ),
            ),
            "do not partition",
        ),
        (
            (
                _occurrence(
                    port_indices=(1, 2),
                    groups=((0, 1),),
                ),
                _occurrence(
                    port_indices=(0,),
                    groups=((0,),),
                ),
            ),
            "canonically ordered",
        ),
    ),
)
def test_occurrences_must_canonically_partition_every_port(
    occurrences: tuple[NativeJointSourceOccurrenceInput, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _encode(occurrences)


def test_equal_clock_is_verified_but_never_used_to_infer_occurrence() -> None:
    changed_clock = (
        Fraction(0),
        Fraction(1, 4),
        Fraction(1, 2),
        Fraction(1),
    )
    with pytest.raises(ValueError, match="clock differs"):
        _encode(
            (
                _occurrence(
                    source_times=changed_clock,
                ),
            )
        )


@pytest.mark.parametrize(
    "kwargs, message",
    (
        ({"groups": ((0,), (2,))}, "do not partition"),
        ({"groups": ((2,), (0, 1))}, "canonically ordered"),
        ({"intersample": b""}, "intersample profile is empty"),
        ({"profile": b""}, "profile is empty"),
        ({"relevance": (Fraction(1),) * 3}, "not exact, aligned"),
        (
            {
                "relevance": (
                    Fraction(0),
                    Fraction(1, 2),
                    Fraction(3, 2),
                    Fraction(1),
                )
            },
            "not exact, aligned",
        ),
    ),
)
def test_occurrence_rejects_missing_or_invented_structure(
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _occurrence(**kwargs)


def test_settle_passes_all_caller_derived_extents_without_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed, states = _boundary()
    occurrence = _occurrence()
    expected = encode_native_joint_source_episode(
        assembly_id="joint-source-test",
        observed_substreams=observed,
        states=states,
        occurrences=(occurrence,),
    )
    candidate, ports, samples, occurrence_total, frame_total = expected

    class Result:
        schema = "guala.native.exact_joint_source_episode.v2"
        payload_sha256 = "00" * 32
        port_count = ports
        source_sample_count = samples
        occurrence_count = occurrence_total
        occurrence_frame_count = frame_total
        python_callback_count = 0

        def as_bytes(self) -> bytes:
            return candidate

    def native_settle(*args):
        assert args == expected
        return Result()

    monkeypatch.setattr(
        source_module,
        "_native_core",
        lambda: SimpleNamespace(
            settle_native_joint_source_episode=native_settle
        ),
    )
    settled = settle_native_joint_source_episode(
        assembly_id="joint-source-test",
        observed_substreams=observed,
        states=states,
        occurrences=(occurrence,),
    )
    assert settled.as_bytes() == candidate
