from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from math import isqrt

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    physical_receptor_substreams,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    EmbodimentWorldAuthority,
    ObjectOpticalSurface,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    RETINA_COLUMNS,
    RETINAL_SITE_GEOMETRY,
    UPGRADED_RETINAL_SITE_GEOMETRY,
    RETINAL_REFERENCE_IRRADIANCE_UNIT,
    _atan2_millidegrees,
    _body_fixed_receptor_position,
    _retinal_projection,
)


def test_virtual_retina_exports_unit_bearing_energy_source_without_meaning() -> None:
    world = EmbodimentWorldAuthority(
        authority_key=b"retinal-physical-work-source-test-key"
    )
    observation = world.observation_snapshot()
    sources = physical_receptor_substreams(
        observation,
        observation,
        causal_transition=False,
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
    )[PhysicalSense.SIGHT]

    assert sources
    assert all(
        source.physical_quantity == "retinal-spectral-irradiance"
        and source.physical_unit == RETINAL_REFERENCE_IRRADIANCE_UNIT
        and all(0.0 <= sample <= 1.0 for sample in source.normalized_signal)
        for source in sources
    )
    rendered = repr(sources).lower()
    assert "alphabet" not in rendered
    assert "number-" not in rendered
    assert "apple" not in rendered


def test_persisted_neck_turn_changes_the_physical_retinal_field() -> None:
    world = EmbodimentWorldAuthority(
        authority_key=b"retinal-neck-bearing-test-key"
    )
    observation = world.observation_snapshot()
    self_body = next(
        body for body in observation.bodies
        if body.body_id == observation.self_body_id
    )
    turned_body = replace(
        self_body,
        pose=PoseMM(
            self_body.pose.position,
            (self_body.pose.heading_millidegrees + 90_000) % 360_000,
        ),
    )
    turned_observation = replace(
        observation,
        bodies=tuple(
            turned_body if body.body_id == self_body.body_id else body
            for body in observation.bodies
        ),
    )

    neck_turn = _retinal_projection(
        observation,
        retinal_heading_offset_millidegrees=90_000,
    )
    root_turn = _retinal_projection(turned_observation)

    assert neck_turn == root_turn
    assert neck_turn != _retinal_projection(observation)


def test_surface_radiance_stays_visible_while_angular_coverage_carries_distance() -> None:
    reflectance = (180_000, 260_000, 340_000, 520_000, 700_000, 880_000)
    near = EmbodiedObject(
        "radiance-target",
        1_000,
        1_000,
        PositionMM(3_000, 1_000, 0),
        reflectance_ppm=reflectance,
    )
    world = EmbodimentWorldAuthority(
        authority_key=b"retinal-surface-radiance-test-key",
        initial_objects=(near,),
    )
    observation = world.observation_snapshot()
    far = replace(near, position=PositionMM(3_800, 1_000, 0))
    farther_observation = replace(observation, objects=(far,))
    center = RETINA_COLUMNS + RETINA_COLUMNS // 2
    region = next(
        item for item in observation.regions
        if item.region_id == observation.room_id
    )
    expected = tuple(
        Fraction(value * illumination, 1_000_000_000_000)
        for value, illumination in zip(
            reflectance, region.illumination_ppm, strict=True
        )
    )

    assert _retinal_projection(observation)[center] == expected
    assert _retinal_projection(farther_observation)[center] == expected


def test_authored_doorway_exposes_only_adjacent_room_radiance() -> None:
    anchor = EmbodiedObject(
        "out-of-view-anchor",
        100,
        100,
        PositionMM(500, 1_000, 0),
    )
    world = EmbodimentWorldAuthority(
        authority_key=b"retinal-doorway-aperture-test-key",
        initial_objects=(anchor,),
    )
    observation = world.observation_snapshot()
    self_body = next(
        body for body in observation.bodies
        if body.body_id == observation.self_body_id
    )
    other_body = next(
        body for body in observation.bodies
        if body.body_id != observation.self_body_id
    )
    observation = replace(
        observation,
        bodies=(
            self_body,
            replace(
                other_body,
                pose=PoseMM(PositionMM(250, 250, 0), 180_000),
            ),
        ),
    )
    regions = {item.region_id: item for item in observation.regions}

    def radiance(region_id: str) -> tuple[Fraction, ...]:
        region = regions[region_id]
        return tuple(
            Fraction(value * illumination, 1_000_000_000_000)
            for value, illumination in zip(
                region.reflectance_ppm,
                region.illumination_ppm,
                strict=True,
            )
        )

    current = radiance("W1-region-A")
    adjacent = radiance("W1-region-B")
    changed = tuple(
        pixel for pixel in _retinal_projection(observation)
        if pixel != current
    )

    assert changed
    assert all(
        min(before, after) <= value <= max(before, after)
        for pixel in changed
        for value, before, after in zip(
            pixel, current, adjacent, strict=True
        )
    )


def test_pitch_uses_the_same_origin_for_portals_and_objects() -> None:
    world = EmbodimentWorldAuthority(
        authority_key=b"retinal-pitch-source-test-key",
        initial_objects=(
            EmbodiedObject("pitch-target", 50, 100, PositionMM(2_500, 1_000, 0)),
        ),
    )
    observation = world.observation_snapshot()
    body = next(item for item in observation.bodies if item.body_id == observation.self_body_id)
    # Each optical branch must independently witness pitch. The object crosses
    # the narrow center at minus eight degrees; the portal moves without any object.
    cases = (
        (replace(observation, portals=(), bodies=(body,)), -8_000),
        (replace(observation, objects=(), bodies=(body,)), 1_000),
    )
    for shown, pitch in cases:
        raised_apertures = tuple(
            (index, x, y + pitch, hx, hy)
            for index, x, y, hx, hy in UPGRADED_RETINAL_SITE_GEOMETRY
        )
        actual = _retinal_projection(
            shown, retinal_pitch_offset_millidegrees=pitch,
            site_geometry=UPGRADED_RETINAL_SITE_GEOMETRY,
        )
        assert actual == _retinal_projection(shown, site_geometry=raised_apertures)
        assert actual != _retinal_projection(
            shown, site_geometry=UPGRADED_RETINAL_SITE_GEOMETRY,
        )


def test_fovea_receives_one_arcminute_contrast_detail_not_a_larger_preview() -> None:
    # A floor-mounted 2 mm-wide 5x5 reflectance target at 1.5 m horizontal
    # distance. Its source is an authenticated world snapshot, not fake pixels.
    upright = (
        1, 1, 1, 1, 1,
        1, 0, 0, 0, 0,
        1, 1, 1, 1, 0,
        1, 0, 0, 0, 0,
        1, 1, 1, 1, 1,
    )
    rotated = tuple(upright[(4 - column) * 5 + row] for row in range(5) for column in range(5))
    fields = []
    for cells in (upright, rotated):
        target = EmbodiedObject(
            "contrast-target", 1, 1, PositionMM(2_500, 1_000, 0),
            optical_surface=ObjectOpticalSurface(
                columns=5, rows=5,
                palette_reflectance_ppm=((1_000_000,) * 6, (0,) * 6),
                cell_palette_indices=cells,
            ),
        )
        world = EmbodimentWorldAuthority(
            authority_key=b"retinal-fine-target-test-key", initial_objects=(target,),
        )
        shown = world.observation_snapshot()
        body = next(item for item in shown.bodies if item.body_id == shown.self_body_id)
        eye = _body_fixed_receptor_position(body, body.receptor_geometry.retinal_offset_mm)
        dx = target.position.x - eye.x
        dy = target.position.y - eye.y
        dz = target.position.z + target.radius_mm - eye.z
        planar_distance = isqrt(dx * dx + dy * dy)
        distance = isqrt(dx * dx + dy * dy + dz * dz)
        angular_radius = abs(_atan2_millidegrees(target.radius_mm, distance))
        critical_detail = Fraction(2 * angular_radius, 5)
        assert Fraction(25, 3) < critical_detail <= Fraction(1_000, 60)
        # This is a source acquisition check at the physically declared aim,
        # not a demonstration that the organism chose to aim at the target.
        pitch = _atan2_millidegrees(dz, planar_distance)
        field = _retinal_projection(
            shown, retinal_pitch_offset_millidegrees=pitch,
            site_geometry=UPGRADED_RETINAL_SITE_GEOMETRY,
        )
        assert field[:135] == _retinal_projection(
            shown, retinal_pitch_offset_millidegrees=pitch,
            site_geometry=RETINAL_SITE_GEOMETRY,
        )
        region = next(item for item in shown.regions if item.region_id == shown.room_id)
        white = tuple(Fraction(value, 1_000_000) for value in region.illumination_ppm)
        assert (Fraction(0),) * 6 in field[135:]
        assert white in field[135:]
        fields.append(field[135:])
    assert fields[0] != fields[1]
    # Optical differentiation is not recognition, native/live acuity or latency.
