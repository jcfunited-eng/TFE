from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from dsf_ai_service.glew_runtime.sensory_full_field_boundary import PhysicalSense
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    physical_receptor_substreams,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
    PoseMM,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
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
