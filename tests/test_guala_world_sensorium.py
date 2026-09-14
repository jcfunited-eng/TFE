from __future__ import annotations

from fractions import Fraction

from dsf_ai_service.guala_physical_sensorium import (
    PORT_COUNT,
    compact_signal_body,
)
from dsf_ai_service.guala_world_sensorium import (
    passive_sensorium,
    prepare_passive_world_interval,
)
from dsf_ai_service.substrate.bounded_home_thermal_physics import (
    ConductiveThermalEdge,
    ThermalBathEdge,
    ThermalPowerSource,
)
from dsf_ai_service.substrate.thermally_coupled_embodiment_world import (
    CoupledThermalAnatomy,
    ThermallyCoupledEmbodimentWorldAuthority,
)


def _world() -> ThermallyCoupledEmbodimentWorldAuthority:
    regions = ("W1-region-A", "W1-region-B", "W1-region-C")
    anatomy = CoupledThermalAnatomy(
        node_ids=(
            "air:W1-region-A",
            "air:W1-region-B",
            "air:W1-region-C",
            "body:cutaneous-shell",
            "body:core",
        ),
        initial_temperatures_millikelvin=(
            296_150,
            296_150,
            296_150,
            303_150,
            309_950,
        ),
        capacities_microjoules_per_millikelvin=(
            50_000_000,
            100_000_000,
            50_000_000,
            4_700_000,
            42_000_000,
        ),
        fixed_conductive_edges=(ConductiveThermalEdge(4, 3, 6_102_941),),
        room_air_node_by_region_id=tuple(
            (region_id, index) for index, region_id in enumerate(regions)
        ),
        skin_node_index=3,
        core_node_index=4,
        skin_air_conductance_microwatts_per_kelvin=5_928_571,
        bath_edges=tuple(
            ThermalBathEdge(index, 296_150, 250_000_000)
            for index in range(3)
        ),
        power_sources=(ThermalPowerSource(4, 41_500_000),),
        parameter_provenance=("exact test thermal anatomy",),
    )
    return ThermallyCoupledEmbodimentWorldAuthority(
        authority_key="lean-world-sensorium-test-key-0001",
        thermal_anatomy=anatomy,
    )


BODY_AXES = (
    (0, "neck_yaw", "millidegree", 0, -180_000, 0, 180_000),
    (1, "left_eyelid_aperture", "micrometre", 160, 0, 0, 320),
    (2, "right_eyelid_aperture", "micrometre", 320, 0, 0, 320),
    (3, "neck_pitch", "millidegree", 0, -35_000, 0, 45_000),
)


def _commit(world: ThermallyCoupledEmbodimentWorldAuthority):
    prepared = prepare_passive_world_interval(world)
    with world.prepared_action_visibility_transaction(prepared):
        execution = world.commit_prepared_action(prepared)
    return prepared, execution


def test_real_world_passive_interval_builds_complete_truthful_sensorium() -> None:
    world = _world()
    before = world.observation_snapshot()
    _prepared, execution = _commit(world)
    sensorium = passive_sensorium(
        world=world,
        snapshot=execution.after,
        body_axes=BODY_AXES,
        frame_count=26,
    )
    after = world.observation_snapshot()

    assert after.revision == before.revision + 1
    assert len(sensorium.ordered_ports()) == PORT_COUNT
    assert len(compact_signal_body(sensorium, frame_count=26)) == (
        PORT_COUNT * 26 * 8
    )
    assert all(len(trajectory) == 26 for trajectory in sensorium.ordered_ports())
    assert sensorium.legacy_ears == ((Fraction(0),) * 26,) * 2
    assert sensorium.cochleae == ((Fraction(0),) * 26,) * 32
    assert sensorium.articulation == ((Fraction(0),) * 26,) * 4
    assert sensorium.retina[0][0] == sensorium.retina[0][-1]
    assert sensorium.thermal[0][0] != sensorium.thermal[1][0]


def test_committed_world_interval_can_roll_back_after_native_refusal() -> None:
    world = _world()
    before = bytes(world.encoded_snapshot())
    prepared, _execution = _commit(world)
    with world.committed_prepared_action_rollback_transaction(
        prepared
    ) as rollback:
        rollback()
    assert bytes(world.encoded_snapshot()) == before


def test_compact_retinal_capture_matches_spectral_values_without_signal_objects(monkeypatch) -> None:
    from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
    from dsf_ai_service.guala_world_sensorium import (
        _retinal_luminance, body_consequence_receptor_capture, passive_receptor_capture,
    )
    from dsf_ai_service.substrate import w1_physical_receptors as optics

    world = _world()
    _prepared, execution = _commit(world)
    # The existing spectral interface is the reference, not a second optical law.
    heading = 12_000
    changed_axes = ((0, "neck_yaw", "millidegree", heading, -180_000, 0, 180_000), *BODY_AXES[1:])
    spectral = optics.physical_receptor_substreams(
        execution.before, execution.after, causal_transition=True,
        before_retinal_heading_offset_millidegrees=0,
        after_retinal_heading_offset_millidegrees=heading,
        source_time_start=Fraction(0), source_time_end=Fraction(1, 1000),
    )
    expected = tuple(
        tuple(
            sum((
                Fraction(stream.normalized_signal[endpoint]).limit_denominator(1_000_000)
                for stream in spectral[PhysicalSense.SIGHT][site * 6:(site + 1) * 6]
            ), Fraction(0)) / 6
            for site in range(135)
        )
        for endpoint in range(2)
    )
    original_projection = optics._retinal_projection
    original_signal = optics._native_signal
    calls = []

    def counted_projection(*args, **kwargs):
        calls.append((args[0], kwargs["retinal_heading_offset_millidegrees"]))
        return original_projection(*args, **kwargs)

    def nonoptical_signal(**kwargs):
        assert kwargs["sense"] is not PhysicalSense.SIGHT
        return original_signal(**kwargs)

    monkeypatch.setattr(optics, "_retinal_projection", counted_projection)
    monkeypatch.setattr(optics, "_native_signal", nonoptical_signal)
    before, after, contacts, before_transmission, after_transmission = body_consequence_receptor_capture(
        execution=execution, predecessor_body_axes=BODY_AXES,
        successor_body_axes=changed_axes,
    )
    assert len(before) == len(after) == 4935
    assert (_retinal_luminance(before)[:135], _retinal_luminance(after)[:135]) == expected
    assert contacts == {sense: streams for sense, streams in spectral.items() if sense is not PhysicalSense.SIGHT}
    assert before_transmission == after_transmission == Fraction(3, 4)
    assert len(calls) == 2
    calls.clear()
    pixels, _contacts, transmission = passive_receptor_capture(
        snapshot=execution.after, body_axes=changed_axes,
    )
    assert len(pixels) == 4935
    assert _retinal_luminance(pixels)[:135] == expected[1]
    assert transmission == Fraction(3, 4)
    assert len(calls) == 1

    def original_luminance(field):
        return tuple(
            sum(
                (Fraction(float(band)).limit_denominator(1_000_000) for band in pixel),
                Fraction(0),
            ) / 6
            for pixel in field
        )

    # Compare the new focal sites too, not only the old spectral prefix.
    for field in (before, after, pixels):
        assert _retinal_luminance(field) == original_luminance(field)

    # Zero is a cached value, and two exact inputs can already round to one
    # float under the established conversion. Reuse must change neither.
    edge = Fraction(1, 2)
    collision = edge + Fraction(1, 2**60)
    assert edge != collision and float(edge) == float(collision)
    repeated = ((Fraction(0), edge, collision, -edge, edge, Fraction(0)),) * 4935
    assert _retinal_luminance(repeated) == original_luminance(repeated)


def test_focal_optics_preserve_old_apertures_and_tile_the_sixty_degree_center() -> None:
    # The focal field is 60 x 45 degrees across 32 x 24 sites (1875 millidegrees
    # per site) since 2026-09-14, the whole camera frame; the earlier half-arc-minute
    # pitch saw a 9 mm patch of wall, the 20-degree cone only wall above the floor.
    # The 135 old apertures are unchanged.
    from dsf_ai_service.substrate.w1_physical_receptors import (
        FOCAL_RETINAL_SITE_GEOMETRY, RETINAL_SITE_GEOMETRY, UPGRADED_RETINAL_SITE_GEOMETRY,
    )

    assert UPGRADED_RETINAL_SITE_GEOMETRY[:135] == RETINAL_SITE_GEOMETRY
    assert len(FOCAL_RETINAL_SITE_GEOMETRY) == 4800
    assert tuple(site[0] for site in FOCAL_RETINAL_SITE_GEOMETRY) == tuple(range(135, 4935))
    assert all(site[3:] == (Fraction(375), Fraction(375)) for site in FOCAL_RETINAL_SITE_GEOMETRY)
    first_row = FOCAL_RETINAL_SITE_GEOMETRY[:80]
    assert first_row[0][1] - first_row[0][3] == -30_000
    assert first_row[-1][1] + first_row[-1][3] == 30_000
    assert all(left[1] + left[3] == right[1] - right[3] for left, right in zip(first_row, first_row[1:]))
    first_column = FOCAL_RETINAL_SITE_GEOMETRY[::80]
    assert first_column[0][2] + first_column[0][4] == 22_500
    assert first_column[-1][2] - first_column[-1][4] == -22_500
    assert all(upper[2] - upper[4] == lower[2] + lower[4] for upper, lower in zip(first_column, first_column[1:]))


def test_external_sampled_sight_omits_discarded_rays_not_world_consequences(monkeypatch) -> None:
    from dataclasses import replace
    from dsf_ai_service import guala_world_sensorium as sampling

    world = _world()
    _prepared, execution = _commit(world)
    args = dict(world=world, snapshot=execution.after, body_axes=BODY_AXES, frame_count=26)
    reference = passive_sensorium(**args)
    before = bytes(world.encoded_snapshot())

    def forbidden_render(*_args, **_kwargs):
        raise AssertionError("discarded world sight was rendered")

    monkeypatch.setattr(sampling, "retinal_irradiance_field", forbidden_render)
    actual = passive_sensorium(**args, include_world_sight=False)
    assert actual.retina == actual.retina_focal == ()
    assert actual == replace(reference, retina=(), retina_focal=())
    assert bytes(world.encoded_snapshot()) == before


def test_actual_pitch_reaches_passive_and_both_body_return_fields() -> None:
    from dsf_ai_service.guala_world_sensorium import (
        body_consequence_receptor_capture, passive_receptor_capture,
    )
    from dsf_ai_service.substrate.w1_physical_receptors import retinal_irradiance_field

    world = _world()
    _prepared, execution = _commit(world)
    raised = tuple(
        (*axis[:3], 30_000, *axis[4:]) if axis[1] == "neck_pitch" else axis
        for axis in BODY_AXES
    )
    before, after, _contacts, _before_lid, _after_lid = body_consequence_receptor_capture(
        execution=execution, predecessor_body_axes=BODY_AXES,
        successor_body_axes=raised,
    )
    assert before == retinal_irradiance_field(execution.before, include_focal=True)
    assert after == retinal_irradiance_field(
        execution.after, retinal_pitch_offset_millidegrees=30_000, include_focal=True,
    )
    passive, _contacts, _lid = passive_receptor_capture(
        snapshot=execution.after, body_axes=raised,
    )
    assert passive == after
    assert after != before


def test_retinal_carriage_refuses_missing_or_untyped_pitch() -> None:
    import pytest
    from dsf_ai_service.guala_world_sensorium import retinal_carriage

    with pytest.raises(RuntimeError, match="neck_pitch"):
        retinal_carriage(tuple(axis for axis in BODY_AXES if axis[1] != "neck_pitch"))
    for position in (True, 45_001):
        invalid = tuple(
            (*axis[:3], position, *axis[4:]) if axis[1] == "neck_pitch" else axis
            for axis in BODY_AXES
        )
        with pytest.raises(RuntimeError, match="neck_pitch"):
            retinal_carriage(invalid)
