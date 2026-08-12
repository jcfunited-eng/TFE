from __future__ import annotations

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
    _default_objects,
)


def test_transient_motor_recruitment_prepares_one_exact_world_yaw(monkeypatch) -> None:
    world = EmbodimentWorldAuthority(
        authority_key="native-motor-yaw-test-key",
        initial_objects=_default_objects()[:1],
    )
    monkeypatch.setattr(production, "_world", lambda: world)
    before = world.observation_snapshot()
    before_body = next(body for body in before.bodies if body.body_id == before.self_body_id)

    prepared = production._prepare_motor_yaw_action(
        "00" * 32,
        (("11" * 16, 0, 7), ("22" * 16, 1, 2)),
    )
    assert prepared is not None
    authority, world_action, predecessor_heading, trajectory = prepared
    assert predecessor_heading == before_body.pose.heading_millidegrees
    assert trajectory == (5,)
    assert authority.observation_snapshot() == before

    with authority.prepared_action_visibility_transaction(world_action):
        execution = authority.commit_prepared_action(world_action)
    after_body = next(
        body
        for body in execution.after.bodies
        if body.body_id == execution.after.self_body_id
    )
    assert after_body.pose.heading_millidegrees == 5
    assert after_body.pose.position == before_body.pose.position
