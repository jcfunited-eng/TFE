from __future__ import annotations

from fractions import Fraction
from types import SimpleNamespace

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_motor_world import prepare_motor_consequence
from dsf_ai_service.guala_world_sensorium import (
    prepare_passive_body_interval,
    prepare_passive_world_interval,
)


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
PASSIVE_TIMES = tuple(Fraction(index, 16_000) for index in range(0, 4_001, 160))
BODY_AXES = (
    (0, "neck_yaw", "millidegree", 0, -75_000, 0, 75_000),
    (1, "left_eyelid_aperture", "micrometre", 10_000, 0, 10_000, 12_000),
    (2, "right_eyelid_aperture", "micrometre", 10_000, 0, 10_000, 12_000),
)


def _evidence(*, yaw: int = 0, x: int = 0, y: int = 0) -> SimpleNamespace:
    root_yaw = (
        (("01" * 16, 4, abs(yaw), "positive" if yaw > 0 else "negative"),)
        if yaw
        else ()
    )
    translations = tuple(
        ("02" * 16, 5 + index, abs(value), axis, "positive" if value > 0 else "negative")
        for index, (axis, value) in enumerate((("x", x), ("y", y)))
        if value
    )
    return SimpleNamespace(
        articulated_body_consequences=(),
        body_proprioceptive_source_extents=(), body_proprioceptive_source_admissions=(),
        body_proprioceptive_sources=(),
        causal_transition_sha256="03" * 32,
        organism_tick=41,
        root_translation_unit_recruitments=translations,
        root_yaw_unit_recruitments=root_yaw,
    )


def test_applied_root_yaw_returns_actual_world_motion_and_exact_sources() -> None:
    world = home_world_authority(identity=IDENTITY)
    before = world.observation_snapshot()
    before_body = next(body for body in before.bodies if body.body_id == before.self_body_id)

    plan = prepare_motor_consequence(
        world=world,
        evidence=_evidence(yaw=7),
        predecessor_state_sha256="04" * 32,
        predecessor_body_axes=BODY_AXES,
        successor_body_axes=BODY_AXES,
    )
    after_body = next(
        body
        for body in plan.prepared_world.execution_receipt.after.bodies
        if body.body_id == before.self_body_id
    )

    assert plan.requested_action == "move"
    assert plan.refusal_reason is None
    assert plan.requested_root_motion == (7, 0, 0)
    assert plan.actual_root_motion == (7, 0, 0)
    assert after_body.pose.heading_millidegrees == (
        before_body.pose.heading_millidegrees + 7
    )
    assert len(plan.sources) == 1
    assert plan.sources[0].restore().port_count == 2
    assert len(plan.sensorium.retina) == 135
    assert all(len(port) == 3 for port in plan.sensorium.ordered_ports())
    assert not hasattr(plan, "spectral_retinal_u8")
    assert plan.vestibular == (before_body.pose.heading_millidegrees, 7)
    world.discard_prepared_action(plan.prepared_world)


def test_refused_root_translation_returns_truthful_zero_motion() -> None:
    world = home_world_authority(identity=IDENTITY)
    plan = prepare_motor_consequence(
        world=world,
        evidence=_evidence(x=2_000_000),
        predecessor_state_sha256="04" * 32,
        predecessor_body_axes=BODY_AXES,
        successor_body_axes=BODY_AXES,
    )

    assert plan.requested_action == "move"
    assert plan.refusal_reason is not None
    assert plan.requested_root_motion == (0, 2_000_000, 0)
    assert plan.actual_root_motion == (0, 0, 0)
    assert not plan.sources
    assert len(plan.sensorium.retina) == 135
    assert not hasattr(plan, "spectral_retinal_u8")
    assert plan.vestibular is None
    world.discard_prepared_action(plan.prepared_world)


def test_exact_world_snapshot_restores_across_two_committed_intervals() -> None:
    world = home_world_authority(identity=IDENTITY)
    predecessor = bytes(world.encoded_snapshot())

    primary = prepare_passive_world_interval(world)
    with world.prepared_action_visibility_transaction(primary):
        world.commit_prepared_action(primary)
    consequence = prepare_passive_body_interval(
        world,
        native_transition_sha256="05" * 32,
    )
    with world.prepared_action_visibility_transaction(consequence):
        world.commit_prepared_action(consequence)
    assert bytes(world.encoded_snapshot()) != predecessor

    world.restore_encoded(predecessor)
    assert bytes(world.encoded_snapshot()) == predecessor
