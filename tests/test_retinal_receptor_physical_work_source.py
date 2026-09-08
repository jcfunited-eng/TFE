from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    physical_receptor_substreams,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    EmbodimentWorldAuthority,
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    RETINA_COLUMNS,
    RETINAL_REFERENCE_IRRADIANCE_UNIT,
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
