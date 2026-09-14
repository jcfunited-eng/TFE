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
    (3, "neck_pitch", "millidegree", 0, -35_000, 0, 45_000),
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


def _closure(axis: str, carriers: int) -> tuple:
    """One native body consequence: the axis discharged toward its minimum."""
    return ("00" * 16, axis, 0, 0, 0, -carriers, carriers, 0, 0, 0, 0)


def test_jaw_closing_on_a_held_apple_is_a_bite_with_real_intake() -> None:
    from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM

    world = home_world_authority(identity=IDENTITY)
    before = world.observation_snapshot()
    body = next(item for item in before.bodies if item.body_id == before.self_body_id)
    apple = next(item for item in before.objects if item.object_id == "apple")
    # A grocery arrival within reach (the world's own boundary for authored matter).
    world.admit_authored_arrival(EmbodiedObject(
        "apple-9", apple.radius_mm, apple.mass_grams,
        PositionMM(body.pose.position.x + 500, body.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=apple.material,
    ))

    grasp = prepare_motor_consequence(
        world=world,
        evidence=_with_consequences(_closure("right_grip_aperture", 40)),
        predecessor_state_sha256="04" * 32,
        predecessor_body_axes=BODY_AXES, successor_body_axes=BODY_AXES,
    )
    assert grasp.requested_action == "grasp"
    assert grasp.refusal_reason is None, grasp.refusal_reason
    assert grasp.nutrition_intake_zeptojoules == 0
    with world.prepared_action_visibility_transaction(grasp.prepared_world):
        world.commit_prepared_action(grasp.prepared_world)
    held = next(item for item in world.observation_snapshot().bodies if item.body_id == before.self_body_id)
    assert held.held_object_id == "apple-9"

    bite = prepare_motor_consequence(
        world=world,
        evidence=_with_consequences(_closure("jaw_opening", 40)),
        predecessor_state_sha256="05" * 32,
        predecessor_body_axes=BODY_AXES, successor_body_axes=BODY_AXES,
    )
    assert bite.requested_action == "bite"
    assert bite.refusal_reason is None, bite.refusal_reason
    after_body = next(
        item for item in bite.prepared_world.execution_receipt.after.bodies
        if item.body_id == before.self_body_id
    )
    assert after_body.active_contact is not None and after_body.active_contact.kind == "oral"
    mouthful = sum(after_body.active_contact.dissolved_tastant_micrograms)
    assert mouthful > 0
    assert bite.nutrition_intake_zeptojoules == mouthful * 17_000_000_000_000_000_000
    world.discard_prepared_action(bite.prepared_world)

    # No object in hand: a closing jaw is just the body, never a bite.
    empty = home_world_authority(identity=IDENTITY)
    plain = prepare_motor_consequence(
        world=empty,
        evidence=_with_consequences(_closure("jaw_opening", 40)),
        predecessor_state_sha256="04" * 32,
        predecessor_body_axes=BODY_AXES, successor_body_axes=BODY_AXES,
    )
    assert plain.requested_action == "body"
    assert plain.nutrition_intake_zeptojoules == 0
    empty.discard_prepared_action(plain.prepared_world)


def _with_consequences(*consequences: tuple) -> SimpleNamespace:
    evidence = _evidence()
    evidence.articulated_body_consequences = consequences
    return evidence
