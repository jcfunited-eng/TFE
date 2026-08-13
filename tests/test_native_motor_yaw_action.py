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
        (
            (
                "11" * 16,
                0,
                7,
                (("11" * 16, 12, "33" * 16, 11, 0, 5),),
            ),
            (
                "22" * 16,
                1,
                2,
                (("44" * 16, 11, "22" * 16, 12, 0, 3),),
            ),
        ),
    )
    assert prepared is not None
    authority, world_action, predecessor_heading, trajectory = prepared
    assert predecessor_heading == before_body.pose.heading_millidegrees
    assert trajectory == (5,)
    assert authority.observation_snapshot() == before
    alternate_world = EmbodimentWorldAuthority(
        authority_key="native-motor-yaw-test-key",
        initial_objects=_default_objects()[:1],
    )
    monkeypatch.setattr(production, "_world", lambda: alternate_world)
    alternate = production._prepare_motor_yaw_action(
        "00" * 32,
        (
            (
                "11" * 16,
                0,
                7,
                (("11" * 16, 12, "33" * 16, 11, 0, 6),),
            ),
            (
                "22" * 16,
                1,
                2,
                (("44" * 16, 11, "22" * 16, 12, 0, 3),),
            ),
        ),
    )
    assert alternate is not None
    assert (
        alternate[1].execution_receipt.causal_intent_receipt_sha256
        != world_action.execution_receipt.causal_intent_receipt_sha256
    )
    assert alternate_world.observation_snapshot() == before
    monkeypatch.setattr(production, "_world", lambda: world)

    with authority.prepared_action_visibility_transaction(world_action):
        execution = authority.commit_prepared_action(world_action)
        committed_body = authority.encoded_committed_prepared_action(
            world_action
        )
    after_body = next(
        body
        for body in execution.after.bodies
        if body.body_id == execution.after.self_body_id
    )
    assert after_body.pose.heading_millidegrees == 5
    assert after_body.pose.position == before_body.pose.position
    assert committed_body == authority.encoded_snapshot()


def test_native_motor_action_is_truthfully_projected(monkeypatch) -> None:
    motor_action = {
        "moved": True,
        "signed_yaw_millidegrees": 5,
        "motor_unit_recruitment_count": 2,
        "world_revision": 1,
    }
    monkeypatch.setattr(
        production,
        "_last_unattended_evidence",
        {
            "category": "native_causal_action_observed",
            "declared_interval_milliseconds": 2_000,
            "hop_count": 8,
            "intake": "continuous-environment:test",
            "measured": {},
            "motor_action": motor_action,
            "organism_tick": 9,
            "receptor_ingress": {
                "changing_count": 0,
                "quiescent_count": 105 * 8,
                "sense_counts": {
                    "sight": 27 * 8,
                    "sound": 34 * 8,
                    "touch": 27 * 8,
                    "smell": 8 * 8,
                    "taste": 5 * 8,
                    "body": 4 * 8,
                },
                "source_hop_count": 8,
            },
            "state_sha256": "33" * 32,
            "world_revision": 1,
        },
    )

    observed = production._autonomy_record()

    assert observed["available"] is True
    assert observed["status"] == "native_causal_action_observed"
    assert observed["action_observed"] is True
    assert observed["action"]["observed_effect"] == "body yawed 5 millidegrees"
    assert observed["consequence"]["available"] is True
    assert observed["motor_action"] == motor_action
