from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

pytest.importorskip("guala_core")

from dsf_ai_service.glew_runtime.native_joint_source_episode import (
    settle_native_joint_source_episode,
)
from dsf_ai_service.glew_runtime.native_materialized_fabric import (
    migrate_native_materialized_fabric,
    transition_native_materialized_fabric,
)
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    NativeSensorySubstreamInput,
)
from dsf_ai_service.substrate.owner_free_materialized_fabric_boundary import (
    VerifiedMaterializedFabricTransition,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)


def _input(sense: PhysicalSense) -> NativeSensorySubstreamInput:
    values = (0.75, -0.5, 1.0, -0.25, 0.5, -1.0, 0.25, -0.75)
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=f"{sense.value}-organ",
        substream_id=f"{sense.value}-receptor-0",
        topology_index=0,
        coordinates=(NativeAxisCoordinate("receptor", "0"),),
        physical_quantity="normalized_physical_excitation",
        physical_unit="normalized_binary64",
        source_times=tuple(
            Fraction(index, 8) for index in range(len(values))
        ),
        normalized_signal=values,
        phase_turns=tuple(
            Fraction(index, 16) for index in range(len(values))
        ),
    )


def _source(assembly_id: str):
    observed = {
        PhysicalSense.SIGHT: (_input(PhysicalSense.SIGHT),),
        PhysicalSense.SOUND: (_input(PhysicalSense.SOUND),),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    return settle_native_joint_source_episode(
        assembly_id=assembly_id,
        observed_substreams=observed,
        states=states,
    )


def test_real_extension_cold_restores_bounded_joint_fractal_recurrence() -> None:
    first_source = _source("materialized-extension-episode-1")
    first = transition_native_materialized_fabric(
        prior_state=None,
        source=first_source,
    )
    assert first.outcome == "joint_neuronal_fractals_transitioned"
    assert first.mosaic_count == 0
    assert first.mosaic_sha256 is None
    assert first.materialized_neuron_count == 0
    assert first.materialized_body_count == 0
    assert first.python_callback_count == 0
    assert first.joint_field_count == 1
    assert first.joint_neuron_count == 2
    assert first.transitioned_fractal_count == 2
    assert first.recurrent_fractal_count == 0
    assert first.joint_transition_sha256 is not None

    first_bytes = bytes(first.as_bytes())
    second = transition_native_materialized_fabric(
        prior_state=first_bytes,
        source=_source("materialized-extension-episode-2"),
    )

    assert second.outcome == "joint_neuronal_fractals_transitioned"
    assert second.mosaic_sha256 is None
    assert second.mosaic_count == 0
    assert second.materialized_neuron_count == 0
    assert second.materialized_body_count == 0
    assert second.evidence_count == 2
    assert second.joint_field_count == 1
    assert second.joint_neuron_count == 2
    assert second.transitioned_fractal_count == 2
    assert second.recurrent_fractal_count == 2
    assert second.joint_transition_sha256 is not None
    assert len(bytes(second.as_bytes())) > len(first_bytes)
    assert second.python_callback_count == 0

    second_bytes = bytes(second.as_bytes())
    third = transition_native_materialized_fabric(
        prior_state=second_bytes,
        source=_source("materialized-extension-episode-3"),
    )
    assert third.recurrent_fractal_count == 2
    assert len(bytes(third.as_bytes())) == len(second_bytes)


def test_cold_migration_discards_prior_pseudo_mosaic_arenas_immediately() -> None:
    current = transition_native_materialized_fabric(
        prior_state=None,
        source=_source("materialized-migration-source"),
    )
    current_bytes = bytes(current.as_bytes())
    generation = current_bytes[10:18]
    joint_size = int.from_bytes(current_bytes[18:22], "little")
    joint_bytes = current_bytes[22:22 + joint_size]
    prior = b"".join((
        b"GLMFAB03",
        (3).to_bytes(2, "little"),
        generation,
        (0).to_bytes(4, "little"),
        (0).to_bytes(4, "little"),
        len(joint_bytes).to_bytes(4, "little"),
        joint_bytes,
    ))

    migrated = migrate_native_materialized_fabric(prior_state=prior)

    migrated_bytes = bytes(migrated.as_bytes())
    assert migrated_bytes.startswith(b"GLMFAB04")
    assert b"GLMFAB03" not in migrated_bytes
    assert migrated.outcome == "joint_neuronal_state_restored"
    assert migrated.joint_field_count == current.joint_field_count
    assert migrated.joint_neuron_count == current.joint_neuron_count
    assert migrated.mosaic_count == 0
    assert migrated.mosaic_sha256 is None


def test_joint_field_does_not_interpolate_unequal_physical_clocks() -> None:
    sight = _input(PhysicalSense.SIGHT)
    sound = _input(PhysicalSense.SOUND)
    sound = replace(
        sound,
        source_times=tuple(
            value + Fraction(1, 1_000) for value in sound.source_times
        ),
    )
    observed = {
        PhysicalSense.SIGHT: (sight,),
        PhysicalSense.SOUND: (sound,),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }
    source = settle_native_joint_source_episode(
        assembly_id="materialized-unequal-clocks",
        observed_substreams=observed,
        states=states,
    )
    result = transition_native_materialized_fabric(
        prior_state=None,
        source=source,
    )
    assert result.outcome == "joint_field_not_reached"
    assert result.joint_field_count == 0
    assert result.joint_neuron_count == 0
    assert result.transitioned_fractal_count == 0
    assert result.joint_transition_sha256 is None


def test_distinct_exact_clocks_retain_one_episode_relation_candidate() -> None:
    sight_0 = _input(PhysicalSense.SIGHT)
    sight_1 = replace(
        sight_0,
        sensor_id="sight-organ-1",
        substream_id="sight-receptor-1",
        topology_index=1,
    )
    sound_0 = replace(
        _input(PhysicalSense.SOUND),
        source_times=tuple(
            value + Fraction(1, 1_000) for value in sight_0.source_times
        ),
    )
    sound_1 = replace(
        sound_0,
        sensor_id="sound-organ-1",
        substream_id="sound-receptor-1",
        topology_index=1,
    )
    observed = {
        PhysicalSense.SIGHT: (sight_0, sight_1),
        PhysicalSense.SOUND: (sound_0, sound_1),
    }
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense in observed
            else SenseBoundaryState.QUIESCENT
        )
        for sense in SENSE_ORDER
    }

    first = transition_native_materialized_fabric(
        prior_state=None,
        source=settle_native_joint_source_episode(
            assembly_id="two-clock-episode-1",
            observed_substreams=observed,
            states=states,
        ),
    )

    assert first.joint_field_count == 2
    assert first.joint_neuron_count == 4
    assert first.transitioned_fractal_count == 4
    assert first.recurrent_fractal_count == 0
    assert first.episode_relation_candidate_sha256 is not None
    assert first.mosaic_count == 0
    assert first.mosaic_sha256 is None

    persisted = VerifiedMaterializedFabricTransition.from_native(
        first
    ).persistence_record()
    restored = VerifiedMaterializedFabricTransition.from_persistence_record(
        persisted
    )

    second = transition_native_materialized_fabric(
        prior_state=restored.state_bytes,
        source=settle_native_joint_source_episode(
            assembly_id="two-clock-episode-2",
            observed_substreams=observed,
            states=states,
        ),
    )

    assert second.joint_field_count == 2
    assert second.joint_neuron_count == 4
    assert second.transitioned_fractal_count == 4
    assert second.recurrent_fractal_count == 4
    assert second.episode_relation_candidate_sha256 is not None
    assert (
        second.episode_relation_candidate_sha256
        != first.episode_relation_candidate_sha256
    )
    assert second.mosaic_count == 0

    second_bytes = bytes(second.as_bytes())
    third = transition_native_materialized_fabric(
        prior_state=second_bytes,
        source=settle_native_joint_source_episode(
            assembly_id="two-clock-episode-3",
            observed_substreams=observed,
            states=states,
        ),
    )

    assert third.recurrent_fractal_count == 4
    assert third.episode_relation_candidate_sha256 is not None
    assert len(bytes(third.as_bytes())) == len(second_bytes)
    assert third.mosaic_count == 0
