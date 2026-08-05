from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.approved_curriculum_physical_surfaces import (
    _APPROVED_ALPHABET_ASSET_NAMES,
    _APPROVED_NUMBER_ASSET_NAMES,
    approved_curriculum_physical_surfaces,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_OPTICAL_SURFACE_COLUMNS,
    MAX_OPTICAL_SURFACE_ROWS,
    PORT_ID,
    AdvancePhysicalTimeCommand,
    EmbodiedObject,
    EmbodimentWorldAuthority,
    ObjectOpticalSurface,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.w1_physical_foveal_observation import (
    FOVEAL_PHYSICAL_QUANTITY,
    MAX_FOVEAL_FIXATIONS_PER_SCAN,
    PhysicalFovealObservationAuthority,
    SurfaceFixation,
    complete_surface_fixation_sequence,
    successive_surface_patch_fixation_sequences,
)


KEY = b"physical-foveal-observation-test-authority-key"


def _surface(
    cell_palette_indices: tuple[int, ...] | None = None,
) -> ObjectOpticalSurface:
    indices = (
        (
            0, 0, 2, 2, 0, 0,
            0, 2, 2, 2, 2, 0,
            2, 2, 1, 1, 2, 2,
            2, 3, 1, 1, 3, 2,
            0, 3, 3, 3, 3, 0,
            0, 0, 3, 3, 0, 0,
        )
        if cell_palette_indices is None
        else cell_palette_indices
    )
    return ObjectOpticalSurface(
        columns=6,
        rows=6,
        palette_reflectance_ppm=(
            (900_000, 880_000, 850_000, 820_000, 790_000, 760_000),
            (20_000, 20_000, 20_000, 20_000, 20_000, 20_000),
            (780_000, 620_000, 360_000, 120_000, 60_000, 30_000),
            (30_000, 70_000, 220_000, 560_000, 760_000, 680_000),
        ),
        cell_palette_indices=indices,
    )


def _world(
    *,
    surface: ObjectOpticalSurface | None = None,
    object_id: str = "physical-optical-surface",
) -> EmbodimentWorldAuthority:
    physical_surface = _surface() if surface is None else surface
    return EmbodimentWorldAuthority(
        authority_key=KEY,
        initial_objects=(
            EmbodiedObject(
                object_id=object_id,
                radius_mm=120,
                mass_grams=18,
                position=PositionMM(5_400, 1_000, 0),
                reflectance_ppm=(
                    900_000,
                    880_000,
                    850_000,
                    820_000,
                    790_000,
                    760_000,
                ),
                optical_surface=physical_surface,
            ),
        ),
    )


def _first_surface(observation):
    return next(
        item for item in observation.objects
        if item.optical_surface is not None
    )


def _scan(world: EmbodimentWorldAuthority):
    observation = world.observation_snapshot()
    target = _first_surface(observation)
    assert target.optical_surface is not None
    authority = PhysicalFovealObservationAuthority(authority_key=KEY)
    plan = authority.authorize_scan(
        observation,
        target_object_id=target.object_id,
        fixations=complete_surface_fixation_sequence(
            target.optical_surface
        ),
    )
    return authority, observation, target, plan


def _expected_band_trajectory(
    surface: ObjectOpticalSurface,
    band: int,
) -> tuple[float, ...]:
    return tuple(
        float(
            Fraction(
                surface.reflectance_at_ppm(
                    row=index // surface.columns,
                    column=index % surface.columns,
                )[band],
                1_000_000,
            )
        )
        for index in range(len(surface.cell_palette_indices))
    )


def test_foveal_window_binding_retains_original_typed_trajectories_once():
    world = _world()
    authority, observation, _target, plan = _scan(world)
    result = authority.observe(observation, scan_plan=plan)
    records = list(result.native_records())

    bound = result._bind_to_window_entries(
        window_id="typed-foveal-window",
        context_id="typed-foveal-context",
        entry_indices=(0,),
        entry_records=({"full_field": records},),
    )

    mounted = bound.inputs_for_settlement(
        window_id="typed-foveal-window",
        context_id="typed-foveal-context",
    )
    assert tuple(value for _index, value in mounted) == (
        result.physical_substreams
    )
    assert {index for index, _value in mounted} == {0}
    with pytest.raises(RuntimeError, match="already bound"):
        result._bind_to_window_entries(
            window_id="typed-foveal-window",
            context_id="typed-foveal-context",
            entry_indices=(0,),
            entry_records=({"full_field": records},),
        )


def _built(result):
    states = {
        sense: (
            SenseBoundaryState.OBSERVED
            if sense is PhysicalSense.SIGHT
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in SENSE_ORDER
    }
    return build_transaction_owned_six_sense_full_field(
        assembly_id=(
            f"test-physical-foveal-"
            f"{result.scan_plan.authority_receipt_sha256}"
        ),
        source_time_start=result.scan_plan.source_time_start,
        source_time_end=result.scan_plan.source_time_end,
        observed_substreams={
            PhysicalSense.SIGHT: result.physical_substreams,
        },
        states=states,
        occurrences=result.joint_source_occurrences(),
    )


def _exact_dsf_fields(result) -> tuple[tuple[tuple[object, ...], ...], ...]:
    built = _built(result)
    sight = next(
        boundary
        for boundary in built.boundary.boundaries
        if boundary.sense is PhysicalSense.SIGHT
    )
    return tuple(
        tuple(
            tuple(
                getattr(field_tuple, field_name)
                for field_name in DSF_FIELD_ORDER
            )
            for field_tuple
            in substream.kernel_basin.exact_dsf_field_tuples
        )
        for substream in sight.substreams
    )


def test_one_visible_physical_cell_changes_native_and_full_l0_l4_field():
    original_world = _world()
    original_observation = original_world.observation_snapshot()
    original_target = _first_surface(original_observation)
    original_surface = original_target.optical_surface
    assert original_surface is not None

    changed_cells = list(original_surface.cell_palette_indices)
    changed_cells[0] = 1
    changed_surface = replace(
        original_surface,
        cell_palette_indices=tuple(changed_cells),
    )
    changed_world = EmbodimentWorldAuthority(
        authority_key=KEY,
        initial_objects=tuple(
            replace(item, optical_surface=changed_surface)
            if item.object_id == original_target.object_id
            else item
            for item in original_observation.objects
        ),
    )

    original_authority, observation, target, plan = _scan(
        original_world
    )
    changed_authority, changed_observation, _, changed_plan = _scan(
        changed_world
    )
    original = original_authority.observe(
        observation, scan_plan=plan
    )
    changed = changed_authority.observe(
        changed_observation, scan_plan=changed_plan
    )

    assert tuple(
        value.normalized_signal for value in original.physical_substreams
    ) != tuple(
        value.normalized_signal for value in changed.physical_substreams
    )
    assert (
        original.authority_receipt_sha256
        != changed.authority_receipt_sha256
    )
    original_built = _built(original)
    sight = next(
        boundary
        for boundary in original_built.boundary.boundaries
        if boundary.sense is PhysicalSense.SIGHT
    )
    assert sight.state is SenseBoundaryState.OBSERVED
    assert len(sight.substreams) == 6
    for substream in sight.substreams:
        assert substream.kernel_basin.exact_dsf_field_tuples
        assert all(
            tuple(
                getattr(field_tuple, field_name)
                for field_name in DSF_FIELD_ORDER
            ) == field_tuple.as_tuple()
            for field_tuple
            in substream.kernel_basin.exact_dsf_field_tuples
        )
        assert tuple(
            layer.layer_index for layer in substream.kernel_basin.layers
        ) == (0, 1, 2, 3, 4)
    assert target.object_id not in repr(original.physical_substreams)


def test_visually_distinct_rasters_differ_as_full_seven_field_l0_l4():
    first_surface = _surface()
    second_surface = _surface(
        (
            3, 3, 0, 0, 3, 3,
            3, 1, 0, 0, 1, 3,
            0, 1, 2, 2, 1, 0,
            0, 1, 2, 2, 1, 0,
            3, 1, 1, 1, 1, 3,
            3, 3, 0, 0, 3, 3,
        )
    )
    first_world = _world(surface=first_surface)
    second_world = _world(surface=second_surface)
    first_authority, first_observation, _, first_plan = _scan(
        first_world
    )
    second_authority, second_observation, _, second_plan = _scan(
        second_world
    )

    first = first_authority.observe(
        first_observation,
        scan_plan=first_plan,
    )
    second = second_authority.observe(
        second_observation,
        scan_plan=second_plan,
    )
    first_fields = _exact_dsf_fields(first)
    second_fields = _exact_dsf_fields(second)

    assert DSF_FIELD_ORDER == (
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    )
    assert first_fields != second_fields
    assert all(
        tuple(
            field_tuple[field_index]
            for substream in first_fields
            for field_tuple in substream
        )
        != tuple(
            field_tuple[field_index]
            for substream in second_fields
            for field_tuple in substream
        )
        for field_index in range(len(DSF_FIELD_ORDER))
    )
    assert all(
        len(field_tuple) == len(DSF_FIELD_ORDER)
        for substream in first_fields + second_fields
        for field_tuple in substream
    )
    assert tuple(
        layer.layer_index
        for substream in next(
            boundary
            for boundary
            in _built(first).boundary.boundaries
            if boundary.sense is PhysicalSense.SIGHT
        ).substreams
        for layer in substream.kernel_basin.layers
    ) == (0, 1, 2, 3, 4) * len(first.physical_substreams)


def test_hidden_object_identity_does_not_change_receptor_input():
    original_world = _world()
    original_observation = original_world.observation_snapshot()
    target = _first_surface(original_observation)
    hidden_name = "physically-renamed-surface"
    renamed_world = EmbodimentWorldAuthority(
        authority_key=KEY,
        initial_objects=tuple(
            replace(item, object_id=hidden_name)
            if item.object_id == target.object_id
            else item
            for item in original_observation.objects
        ),
    )
    original_authority, observation, _, plan = _scan(original_world)
    renamed_observation = renamed_world.observation_snapshot()
    renamed_target = next(
        item for item in renamed_observation.objects
        if item.object_id == hidden_name
    )
    assert renamed_target.optical_surface is not None
    renamed_authority = PhysicalFovealObservationAuthority(
        authority_key=KEY
    )
    renamed_plan = renamed_authority.authorize_scan(
        renamed_observation,
        target_object_id=hidden_name,
        fixations=complete_surface_fixation_sequence(
            renamed_target.optical_surface
        ),
    )

    assert plan == renamed_plan
    original = original_authority.observe(
        observation, scan_plan=plan
    )
    renamed = renamed_authority.observe(
        renamed_observation, scan_plan=renamed_plan
    )
    assert original.physical_substreams == renamed.physical_substreams
    receptor_text = repr(original.physical_substreams).lower()
    assert target.object_id.lower() not in receptor_text
    assert hidden_name not in receptor_text
    assert not any(
        forbidden in receptor_text
        for forbidden in (
            "asset-id",
            "card-index",
            "meaning",
            "ocr",
            "semantic-label",
            "text",
        )
    )


def test_exact_repeated_fixation_is_deterministic():
    world = _world()
    observation = world.observation_snapshot()
    target = _first_surface(observation)
    assert target.optical_surface is not None
    fixations = (
        SurfaceFixation(row=0, column=0),
        SurfaceFixation(row=0, column=0),
        SurfaceFixation(row=0, column=0),
    )
    authority = PhysicalFovealObservationAuthority(authority_key=KEY)
    first_plan = authority.authorize_scan(
        observation,
        target_object_id=target.object_id,
        fixations=fixations,
    )
    second_plan = authority.authorize_scan(
        observation,
        target_object_id=target.object_id,
        fixations=fixations,
    )
    first = authority.observe(observation, scan_plan=first_plan)
    second = authority.observe(observation, scan_plan=second_plan)

    assert first_plan == second_plan
    assert first.physical_substreams == second.physical_substreams
    assert (
        first.authority_receipt_sha256
        == second.authority_receipt_sha256
    )


def test_out_of_bounds_and_stale_focus_authority_fail_closed():
    world = _world()
    authority, observation, target, plan = _scan(world)
    assert target.optical_surface is not None
    with pytest.raises(ValueError, match="outside"):
        authority.authorize_scan(
            observation,
            target_object_id=target.object_id,
            fixations=(
                SurfaceFixation(row=0, column=0),
                SurfaceFixation(
                    row=target.optical_surface.rows,
                    column=0,
                ),
            ),
        )

    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(
            AdvancePhysicalTimeCommand(1_000_000)
        ),
        causal_intent_receipt_sha256="7" * 64,
        expected_revision=observation.revision,
    )
    assert execution.disposition == "applied"
    with pytest.raises(ValueError, match="stale"):
        authority.observe(
            world.observation_snapshot(),
            scan_plan=plan,
        )


def test_complete_scan_covers_every_surface_cell_without_flattening():
    world = _world()
    authority, observation, target, plan = _scan(world)
    surface = target.optical_surface
    assert surface is not None
    result = authority.observe(observation, scan_plan=plan)

    assert plan.fixations == tuple(
        SurfaceFixation(row=row, column=column)
        for row in range(surface.rows)
        for column in range(surface.columns)
    )
    assert len(plan.fixations) == surface.rows * surface.columns
    assert len(result.physical_substreams) == 6
    for band, substream in enumerate(result.physical_substreams):
        assert substream.physical_quantity == FOVEAL_PHYSICAL_QUANTITY
        assert len(substream.normalized_signal) == len(
            surface.cell_palette_indices
        )
        assert substream.normalized_signal == _expected_band_trajectory(
            surface, band
        )
        assert len(substream.source_times) == len(
            surface.cell_palette_indices
        )
        assert len(substream.phase_turns) == len(
            surface.cell_palette_indices
        )


def test_successive_gaze_patches_cover_raster_within_sample_bounds():
    world = _world()
    observation = world.observation_snapshot()
    target = _first_surface(observation)
    surface = target.optical_surface
    assert surface is not None
    patches = successive_surface_patch_fixation_sequences(
        surface,
        patch_rows=2,
        patch_columns=3,
    )
    authority = PhysicalFovealObservationAuthority(authority_key=KEY)
    seen = []
    prior_end = Fraction(0)
    for index, fixations in enumerate(patches):
        start = Fraction(index, len(patches))
        end = Fraction(index + 1, len(patches))
        assert start == prior_end
        plan = authority.authorize_scan(
            observation,
            target_object_id=target.object_id,
            fixations=fixations,
            source_time_start=start,
            source_time_end=end,
        )
        result = authority.observe(observation, scan_plan=plan)
        assert len(fixations) <= MAX_FOVEAL_FIXATIONS_PER_SCAN
        assert sum(
            len(substream.normalized_signal)
            for substream in result.physical_substreams
        ) == len(fixations) * 6
        assert all(
            substream.physical_quantity == FOVEAL_PHYSICAL_QUANTITY
            for substream in result.physical_substreams
        )
        seen.extend(fixations)
        prior_end = end

    assert len(seen) == surface.rows * surface.columns
    assert len(set(seen)) == len(seen)
    assert set(seen) == set(complete_surface_fixation_sequence(surface))


def test_maximum_illustrated_raster_is_finite_and_splits_into_gaze_patches():
    cell_count = (
        MAX_OPTICAL_SURFACE_COLUMNS * MAX_OPTICAL_SURFACE_ROWS
    )
    surface = ObjectOpticalSurface(
        columns=MAX_OPTICAL_SURFACE_COLUMNS,
        rows=MAX_OPTICAL_SURFACE_ROWS,
        palette_reflectance_ppm=(
            (900_000, 880_000, 850_000, 820_000, 790_000, 760_000),
            (20_000, 20_000, 20_000, 20_000, 20_000, 20_000),
        ),
        cell_palette_indices=(0,) * (cell_count - 1) + (1,),
    )
    patches = successive_surface_patch_fixation_sequences(
        surface,
        patch_rows=32,
        patch_columns=32,
    )

    assert surface.columns == 128
    assert surface.rows == 160
    assert len(patches) == 20
    assert sum(len(patch) for patch in patches) == cell_count
    assert all(
        2 <= len(patch) <= MAX_FOVEAL_FIXATIONS_PER_SCAN
        for patch in patches
    )
    world = _world(surface=surface)
    encoded = world.encoded_snapshot()
    assert len(encoded) <= 2 * 1024 * 1024
    restored = EmbodimentWorldAuthority(authority_key=KEY)
    restored.restore_encoded(encoded)
    assert restored.encoded_snapshot() == encoded

    observation = world.observation_snapshot()
    target = _first_surface(observation)
    authority = PhysicalFovealObservationAuthority(authority_key=KEY)
    for index, fixations in enumerate(patches):
        authority.authorize_scan(
            observation,
            target_object_id=target.object_id,
            fixations=fixations,
            source_time_start=Fraction(index, len(patches)),
            source_time_end=Fraction(index + 1, len(patches)),
        )
    with pytest.raises(ValueError, match="boundary"):
        authority.authorize_scan(
            observation,
            target_object_id=target.object_id,
            fixations=complete_surface_fixation_sequence(surface),
        )


def test_palette_surface_state_cold_restores_exactly_and_is_authenticated():
    world = _world()
    encoded = world.encoded_snapshot()
    restored = EmbodimentWorldAuthority(authority_key=KEY)
    restored.restore_encoded(encoded)

    assert restored.encoded_snapshot() == encoded
    assert restored.observation_snapshot() == world.observation_snapshot()
    restored_surface = _first_surface(
        restored.observation_snapshot()
    ).optical_surface
    assert restored_surface == _surface()

    envelope = json.loads(encoded)
    envelope["authority_hmac_sha256"] = (
        ("0" if envelope["authority_hmac_sha256"][0] != "0" else "1")
        + envelope["authority_hmac_sha256"][1:]
    )
    tampered = json.dumps(
        envelope,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    before = restored.encoded_snapshot()
    with pytest.raises(ValueError, match="HMAC"):
        restored.restore_encoded(tampered)
    assert restored.encoded_snapshot() == before


def test_default_world_contains_all_approved_curriculum_surfaces():
    world = EmbodimentWorldAuthority(authority_key=KEY)
    observation = world.observation_snapshot()
    assert len(observation.objects) == 42
    surfaces = tuple(
        item
        for item in observation.objects
        if item.optical_surface is not None
    )
    assert len(surfaces) == 36
    assert all(
        item.optical_surface.columns == 56
        and item.optical_surface.rows == 70
        for item in surfaces
    )
    approved = approved_curriculum_physical_surfaces()
    assert approved == surfaces
    assert len(_APPROVED_NUMBER_ASSET_NAMES) == 10
    assert len({item.optical_surface for item in approved}) == 36

    for card, asset_name in zip(
        approved,
        _APPROVED_ALPHABET_ASSET_NAMES
        + _APPROVED_NUMBER_ASSET_NAMES,
        strict=True,
    ):
        surface = card.optical_surface
        assert surface is not None
        physical_world = _world(
            surface=surface,
            object_id=card.object_id,
        )
        physical_observation = physical_world.observation_snapshot()
        authority = PhysicalFovealObservationAuthority(authority_key=KEY)
        plan = authority.authorize_scan(
            physical_observation,
            target_object_id=card.object_id,
            fixations=(
                SurfaceFixation(row=0, column=0),
                SurfaceFixation(row=0, column=1),
            ),
        )
        result = authority.observe(
            physical_observation,
            scan_plan=plan,
        )
        records = result.native_records()
        assert records
        assert all(record["sense"] == "sight" for record in records)
        receptor_text = json.dumps(records, sort_keys=True).lower()
        for forbidden in (
            card.object_id.lower(),
            asset_name.lower(),
            "is-for",
            ".png",
            "alphabet-",
            "number-",
        ):
            assert forbidden not in receptor_text

    encoded = world.encoded_snapshot()
    restored = EmbodimentWorldAuthority(authority_key=KEY)
    restored.restore_encoded(encoded)
    assert restored.encoded_snapshot() == encoded
