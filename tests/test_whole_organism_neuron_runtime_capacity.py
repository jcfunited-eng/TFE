"""Runtime neuron bounds must admit their own exact coupling law."""

from __future__ import annotations

from fractions import Fraction
import json
import time

import pytest

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
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
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    WholeOrganismNeuronPopulationOwner,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala
from dsf_ai_service.v4.guala_physical_runtime_core import (
    GualaBootStateIntegrityHalt,
    WHOLE_ORGANISM_NEURON_PROFILE_MIGRATION,
    _whole_organism_neuron_population_profile,
    whole_organism_neuron_anatomy_path_counts,
)
from tests.test_whole_organism_neuron_population import KEY, _manifest


def _substream(
    sense: PhysicalSense,
    *,
    sensor_id: str,
    topology_index: int,
) -> NativeSensorySubstreamInput:
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=sensor_id,
        substream_id=f"path-{topology_index:03d}",
        topology_index=topology_index,
        coordinates=(
            NativeAxisCoordinate(
                f"{sense.value}-axis",
                f"{sensor_id}-{topology_index:03d}",
            ),
        ),
        physical_quantity=f"{sense.value}-intensity",
        physical_unit="normalized-intensity",
        source_times=(Fraction(1, 3), Fraction(2, 3)),
        normalized_signal=(0.0, 1.0),
        phase_turns=(Fraction(0), Fraction(1, 2)),
    )


def _settlement(
    label: str,
    paths: dict[PhysicalSense, tuple[NativeSensorySubstreamInput, ...]],
):
    return ExactCausalExperienceOwner(
        on_settlement=lambda _value: None,
        log_event=lambda *_args, **_kwargs: None,
    ).settle(
        build_six_sense_full_field(
            assembly_id=label,
            source_time_start=Fraction(0),
            source_time_end=Fraction(1),
            observed_substreams=paths,
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense in paths
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        ),
        routing_chis=(),
        source_tags=(),
    )


def _owner_with_profile(profile):
    return WholeOrganismNeuronPopulationOwner(
        authority_key=KEY,
        manifest_authority_key=KEY,
        manifest=_manifest(),
        profile=profile,
    )


def _current_production_210_settlements():
    return (
        _settlement(
            "authenticated-current-production-base-198",
            {
                PhysicalSense.SIGHT: tuple(
                    _substream(
                        PhysicalSense.SIGHT,
                        sensor_id="w1_retina",
                        topology_index=index,
                    )
                    for index in range(162)
                ),
                PhysicalSense.SOUND: tuple(
                    _substream(
                        PhysicalSense.SOUND,
                        sensor_id="microphone_cochlear_field",
                        topology_index=index,
                    )
                    for index in range(32)
                ),
                PhysicalSense.BODY: tuple(
                    _substream(
                        PhysicalSense.BODY,
                        sensor_id="w1_body_displacement",
                        topology_index=index,
                    )
                    for index in range(4)
                ),
            },
        ),
        _settlement(
            "authenticated-current-production-fovea-12",
            {
                PhysicalSense.SIGHT: tuple(
                    _substream(
                        PhysicalSense.SIGHT,
                        sensor_id="w1_physical_fovea",
                        topology_index=index,
                    )
                    for index in range(12)
                ),
            },
        ),
    )


def test_runtime_edge_bound_covers_all_pairs_of_bounded_neurons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "whole-organism-neuron-capacity-test-key",
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    guala = Guala()
    try:
        profile = guala._whole_organism_neuron_population_owner._profile
        required = (
            profile.max_neurons * (profile.max_neurons - 1) // 2
        )
        assert profile.max_edges >= required, (
            "runtime neuron profile cannot retain every exact pair its "
            f"own all-pairs coupling law may produce: "
            f"{profile.max_edges} < {required}"
        )
    finally:
        guala.shutdown()


def test_runtime_capacity_is_exact_union_of_mounted_receptor_paths() -> None:
    counts = whole_organism_neuron_anatomy_path_counts()
    assert counts == {
        "browser_camera_retina": 64,
        "camera_saccade_fixations": 3,
        "microphone_cochlear_field": 32,
        "w1_binaural_cochlear_field": 64,
        "w1_body_displacement": 4,
        "w1_material_smell": 8,
        "w1_material_taste": 5,
        "w1_material_touch": 6,
        "w1_physical_fovea": 18,
        "w1_physical_touch": 3,
        "w1_retina": 162,
    }
    profile = _whole_organism_neuron_population_profile()
    assert profile.max_neurons == sum(counts.values()) == 369
    assert profile.max_neurons >= 185 + 64 + 32


def test_every_mounted_anatomy_path_fits_then_new_path_fails_closed() -> None:
    counts = whole_organism_neuron_anatomy_path_counts()
    senses = {
        "browser_camera_retina": PhysicalSense.SIGHT,
        "camera_saccade_fixations": PhysicalSense.SIGHT,
        "microphone_cochlear_field": PhysicalSense.SOUND,
        "w1_binaural_cochlear_field": PhysicalSense.SOUND,
        "w1_body_displacement": PhysicalSense.BODY,
        "w1_material_smell": PhysicalSense.SMELL,
        "w1_material_taste": PhysicalSense.TASTE,
        "w1_material_touch": PhysicalSense.TOUCH,
        "w1_physical_fovea": PhysicalSense.SIGHT,
        "w1_physical_touch": PhysicalSense.TOUCH,
        "w1_retina": PhysicalSense.SIGHT,
    }
    owner = _owner_with_profile(
        _whole_organism_neuron_population_profile()
    )
    for domain, count in counts.items():
        sense = senses[domain]
        settlement = _settlement(
            f"mounted-anatomy-{domain}",
            {
                sense: tuple(
                    _substream(
                        sense,
                        sensor_id=domain,
                        topology_index=index,
                    )
                    for index in range(count)
                )
            },
        )
        owner.commit(owner.prepare(settlement))

    status = owner.status()
    assert status["neurons"] == status["neuron_capacity"] == 369
    assert status["state_bytes"] <= status["state_capacity_bytes"]
    before = owner.snapshot_encoded()
    extra = _settlement(
        "unmounted-future-anatomy",
        {
            PhysicalSense.SIGHT: (
                _substream(
                    PhysicalSense.SIGHT,
                    sensor_id="future-unmounted-receptor",
                    topology_index=0,
                ),
            ),
        },
    )
    with pytest.raises(RuntimeError, match="neuron capacity exhausted"):
        owner.prepare(extra)
    assert owner.snapshot_encoded() == before


def test_authenticated_v1_population_migrates_without_learned_state_change(
) -> None:
    legacy_profile = _whole_organism_neuron_population_profile(legacy=True)
    current_profile = _whole_organism_neuron_population_profile()
    legacy = _owner_with_profile(legacy_profile)
    for settlement in _current_production_210_settlements():
        legacy.commit(legacy.prepare(settlement))
    before = legacy.snapshot_encoded()
    migrated = (
        WholeOrganismNeuronPopulationOwner
        .migrate_authenticated_runtime_profile_v1_to_v2_encoded(
            authority_key=KEY,
            manifest_authority_key=KEY,
            manifest=_manifest(),
            legacy_profile=legacy_profile,
            current_profile=current_profile,
            encoded=before,
        )
    )
    restored = WholeOrganismNeuronPopulationOwner.restore_encoded(
        authority_key=KEY,
        manifest_authority_key=KEY,
        manifest=_manifest(),
        profile=current_profile,
        encoded=migrated,
    )
    assert len(restored.neurons) == 210
    assert restored.status()["neurons_by_sense"] == {
        "body": 4,
        "sight": 174,
        "smell": 0,
        "sound": 32,
        "taste": 0,
        "touch": 0,
    }
    assert restored.neurons == legacy.neurons
    assert restored.edges == legacy.edges
    assert tuple(value.record() for value in restored.neurons) == tuple(
        value.record() for value in legacy.neurons
    )
    assert legacy.snapshot_encoded() == before
    assert len(migrated) <= current_profile.max_state_bytes

    damaged = bytearray(before)
    damaged[-2] ^= 1
    with pytest.raises(ValueError):
        (
            WholeOrganismNeuronPopulationOwner
            .migrate_authenticated_runtime_profile_v1_to_v2_encoded(
                authority_key=KEY,
                manifest_authority_key=KEY,
                manifest=_manifest(),
                legacy_profile=legacy_profile,
                current_profile=current_profile,
                encoded=bytes(damaged),
            )
        )
    assert legacy.snapshot_encoded() == before


def test_production_shaped_commit_promotes_one_validated_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = _owner_with_profile(
        _whole_organism_neuron_population_profile()
    )
    base, fovea = _current_production_210_settlements()
    owner.commit(owner.prepare(base))
    owner.commit(owner.prepare(fovea))
    before = owner.snapshot_encoded()
    sound = _settlement(
        "production-shaped-next-microphone-frame",
        {
            PhysicalSense.SOUND: tuple(
                _substream(
                    PhysicalSense.SOUND,
                    sensor_id="microphone_cochlear_field",
                    topology_index=index,
                )
                for index in range(32)
            ),
        },
    )
    original_build = owner._build_encoded_locked
    build_calls = 0

    def counted_build():
        nonlocal build_calls
        build_calls += 1
        return original_build()

    monkeypatch.setattr(owner, "_build_encoded_locked", counted_build)
    started = time.perf_counter()
    prepared = owner.prepare(sound)
    prepare_seconds = time.perf_counter() - started
    started = time.perf_counter()
    undo = owner.commit(prepared)
    commit_seconds = time.perf_counter() - started
    after = owner.snapshot_encoded()
    rebuilt_after = original_build()
    started = time.perf_counter()
    owner.rollback(undo)
    rollback_seconds = time.perf_counter() - started

    report = {
        "after_state_bytes": len(after),
        "before_state_bytes": len(before),
        "commit_seconds": round(commit_seconds, 6),
        "neuron_count": len(owner.neurons),
        "prepare_seconds": round(prepare_seconds, 6),
        "rollback_seconds": round(rollback_seconds, 6),
        "staged_full_encoding_builds": build_calls,
    }
    print("production-shaped neuron transaction " + json.dumps(
        report,
        sort_keys=True,
    ))
    assert report["neuron_count"] == 210
    assert build_calls == 1
    assert after == rebuilt_after
    assert owner.snapshot_encoded() == before
    assert commit_seconds < prepare_seconds
    assert rollback_seconds < prepare_seconds


def test_current_210_neuron_runtime_generation_restores_by_named_migration(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "current-production-210-neuron-runtime-restore-key-v1",
    )
    writer = Guala()
    reader = None
    refuser = None
    try:
        recovery = writer._whole_organism_recovery_owner
        chemical = writer._whole_organism_neurochemical_owner
        legacy = WholeOrganismNeuronPopulationOwner(
            authority_key=(
                writer._whole_organism_neuron_population_authority_key
            ),
            manifest_authority_key=(
                writer._whole_organism_episode_authority_key
            ),
            manifest=writer._whole_organism_episode_authority.manifest,
            profile=_whole_organism_neuron_population_profile(
                legacy=True
            ),
            local_receptor_verifier=chemical.local_receptor_verifier,
        )
        for settlement in _current_production_210_settlements():
            writer._synchronize_physical_internal_body_state(settlement)
            recovery.commit_prepared(
                recovery.prepare_observation(settlement)
            )
            chemical.advance(settlement)
            legacy.commit(legacy.prepare(
                settlement,
                local_receptor_activations=(
                    chemical.local_receptor_activations(settlement)
                ),
            ))
        writer._whole_organism_neuron_population_owner = legacy
        writer._whole_organism_thing_learning_owner.rebind_neuron_owner(
            legacy
        )
        writer._passive_whole_organism_thing_learning.rebind_neuron_owner(
            legacy
        )
        before_records = tuple(value.record() for value in legacy.neurons)
        writer.save_full_state(str(tmp_path))

        refuser = Guala()
        with pytest.raises(GualaBootStateIntegrityHalt):
            refuser.load_full_state(str(tmp_path))

        reader = Guala()
        reader.load_full_state(
            str(tmp_path),
            allow_authenticated_current_schema_migration=True,
        )
        restored = reader._whole_organism_neuron_population_owner
        assert restored.status()["neurons"] == 210
        assert restored.status()["neurons_by_sense"] == {
            "body": 4,
            "sight": 174,
            "smell": 0,
            "sound": 32,
            "taste": 0,
            "touch": 0,
        }
        assert tuple(value.record() for value in restored.neurons) == (
            before_records
        )
        assert reader._authenticated_current_schema_migrations == (
            WHOLE_ORGANISM_NEURON_PROFILE_MIGRATION,
        )
    finally:
        if reader is not None:
            reader.shutdown()
        if refuser is not None:
            refuser.shutdown()
        writer.shutdown()
