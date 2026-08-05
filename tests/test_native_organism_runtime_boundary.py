from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

from dsf_ai_service.glew_runtime import native_organism_runtime as boundary


def _source_episode():
    """One real settled native joint-source episode (no Python stubs)."""

    from fractions import Fraction

    from dsf_ai_service.glew_runtime.native_joint_source_episode import (
        NativeJointSourceOccurrenceInput,
        UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR,
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

    times = tuple(Fraction(index, 4) for index in range(4))
    port = NativeSensorySubstreamInput(
        sense=PhysicalSense.SIGHT,
        sensor_id="sight-organ",
        substream_id="sight-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("receptor", "0"),),
        physical_quantity="normalized_physical_excitation",
        physical_unit="normalized_binary64",
        source_times=times,
        normalized_signal=(0.0, 0.5, -0.25, 1.0),
        phase_turns=(Fraction(0),) * 4,
    )
    observed = {PhysicalSense.SIGHT: (port,)}
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    occurrence = NativeJointSourceOccurrenceInput(
        port_indices=(0,),
        source_times=times,
        joint_intersample_profile_payload=(
            UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
        ),
        groups=((0,),),
        joint_relevance_profile_payload=(
            UF_V1_4_SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR
        ),
        joint_relevance=(Fraction(1),) * len(times),
    )
    return settle_native_joint_source_episode(
        assembly_id="native-organism-boundary-test",
        observed_substreams=observed,
        states=states,
        occurrences=(occurrence,),
    )


@dataclass
class _Result:
    payload: bytes
    scope: str
    source: object | None = None
    predecessor: bytes | None = None
    physical_transition_claimed: bool = False
    cognitive_formation_claimed: bool = False
    cognitive_ordinal: int = 0
    cognitive_trace_count: int = 0
    cognitive_mosaic_count: int = 0
    formation_activation_count: int = 0
    partial_cue_reassembly_count: int = 0

    schema: str = boundary.OBSERVATION_SCHEMA
    identity: str = "12345678-9abc-4def-8123-456789abcdef"
    predecessor_organism_tick: int | None = None
    organism_tick: int = 92
    predecessor_fabric_generation: int | None = None
    fabric_generation: int = 18
    predecessor_mounted_generation: int | None = None
    mounted_generation: int = 4
    fabric_bytes: int = 100
    fabric_sha256: str = "a" * 64
    joint_field_count: int = 1
    joint_neuron_count: int = 3
    transitioned_fractal_count: int = 3
    recurrent_fractal_count: int = 3
    source_cohort_l0_l4_evaluation_count: int = 0
    successor_l0_l4_replay_count: int = 0
    joint_transition_sha256: str | None = "b" * 64
    episode_relation_candidate_sha256: str | None = None
    mounted_step_completed: bool = False
    python_callback_count: int = 0
    derived_budget: tuple[int, int, int, int, int] = (
        1_974,
        6_000,
        2_048,
        2_048,
        10_096,
    )

    @classmethod
    def transitioned(
        cls,
        predecessor: bytes,
        source,
    ) -> "_Result":
        return cls(
            payload=b"GLORUN01-successor",
            scope=boundary.MOUNTED_STEP_SCOPE,
            source=source,
            predecessor=predecessor,
            predecessor_organism_tick=91,
            predecessor_fabric_generation=17,
            predecessor_mounted_generation=3,
            source_cohort_l0_l4_evaluation_count=1,
            mounted_step_completed=True,
        )

    @property
    def predecessor_state_sha256(self) -> str | None:
        if self.predecessor is None:
            return None
        return hashlib.sha256(self.predecessor).hexdigest()

    @property
    def state_bytes(self) -> int:
        return len(self.payload)

    @property
    def state_sha256(self) -> str:
        return hashlib.sha256(self.payload).hexdigest()

    @property
    def source_sha256(self) -> str | None:
        return None if self.source is None else self.source.payload_sha256

    def as_bytes(self) -> bytes:
        return self.payload


class _Native:
    def __init__(self, result: _Result) -> None:
        self.result = result
        self.transition_calls: list[tuple[object, ...]] = []
        self.restore_calls: list[tuple[object, ...]] = []

    def transition_native_organism_runtime(self, *values):
        self.transition_calls.append(values)
        return self.result

    def restore_native_organism_runtime(self, *values):
        self.restore_calls.append(values)
        return self.result


def test_boundary_invokes_one_native_organism_step_without_d2_fallback(
    monkeypatch,
) -> None:
    predecessor = b"GLORUN01-predecessor"
    source = _source_episode()
    result = _Result.transitioned(predecessor, source)
    native = _Native(result)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    observed = boundary.transition_native_organism(
        prior_envelope=predecessor,
        source=source,
        max_envelope_bytes=2_048,
        max_fabric_bytes=2_000,
        max_logical_peak_bytes=10_096,
    )

    assert observed is result
    assert native.transition_calls == [
        (predecessor, source, 2_048, 2_000, 10_096)
    ]
    assert native.restore_calls == []
    assert observed.as_bytes().startswith(b"GLORUN01")
    assert observed.source_cohort_l0_l4_evaluation_count == 1
    assert observed.successor_l0_l4_replay_count == 0
    assert observed.python_callback_count == 0
    assert not observed.physical_transition_claimed
    assert not observed.cognitive_formation_claimed


def test_boundary_restores_exact_current_envelope_without_transition(
    monkeypatch,
) -> None:
    current = b"GLORUN01-current"
    result = _Result(payload=current, scope=boundary.RESTORED_SCOPE)
    native = _Native(result)
    monkeypatch.setattr(boundary, "_native_core", lambda: native)

    observed = boundary.restore_native_organism(
        current_envelope=current,
        max_envelope_bytes=2_048,
        max_fabric_bytes=2_000,
        max_logical_peak_bytes=10_096,
    )

    assert observed is result
    assert native.restore_calls == [(current, 2_048, 2_000, 10_096)]
    assert native.transition_calls == []
    assert observed.predecessor_state_sha256 is None
    assert not observed.mounted_step_completed
    assert observed.source_cohort_l0_l4_evaluation_count == 0
    assert observed.successor_l0_l4_replay_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("physical_transition_claimed", True),
        ("mounted_step_completed", False),
        ("python_callback_count", 1),
        ("successor_l0_l4_replay_count", 1),
    ),
)
def test_boundary_refuses_false_or_replayed_transition_claims(
    monkeypatch,
    field: str,
    value: object,
) -> None:
    predecessor = b"GLORUN01-predecessor"
    source = _source_episode()
    result = _Result.transitioned(predecessor, source)
    setattr(result, field, value)
    monkeypatch.setattr(boundary, "_native_core", lambda: _Native(result))

    with pytest.raises(
        RuntimeError,
        match="native organism (operation|transition) changed its causal contract",
    ):
        boundary.transition_native_organism(
            prior_envelope=predecessor,
            source=source,
            max_envelope_bytes=2_048,
            max_fabric_bytes=2_000,
            max_logical_peak_bytes=10_096,
        )


def test_boundary_carries_native_cognitive_formation_observation(monkeypatch) -> None:
    predecessor = b"GLORUN01-predecessor"
    source = _source_episode()
    result = _Result.transitioned(predecessor, source)
    result.cognitive_formation_claimed = True
    result.cognitive_ordinal = 1
    result.cognitive_trace_count = 1
    monkeypatch.setattr(boundary, "_native_core", lambda: _Native(result))

    observed = boundary.transition_native_organism(
        prior_envelope=predecessor,
        source=source,
        max_envelope_bytes=2_048,
        max_fabric_bytes=2_000,
        max_logical_peak_bytes=10_096,
    )

    assert observed.cognitive_formation_claimed
    assert observed.cognitive_ordinal == 1
    assert observed.cognitive_trace_count == 1
