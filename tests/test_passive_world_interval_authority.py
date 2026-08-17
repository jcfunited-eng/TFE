from __future__ import annotations

from dsf_ai_service.substrate.embodiment_world import (
    ENVIRONMENT_PORT_ID,
    AdvancePhysicalTimeCommand,
    EmbodimentWorldAuthority,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)


def _odorant_total(observation) -> tuple[int, ...]:
    total = [0] * 8
    for region in observation.regions:
        if region.air is not None:
            for index, mass in enumerate(region.air.odorant_mass_nanograms):
                total[index] += mass
    for item in observation.objects:
        if item.material is not None:
            for index, mass in enumerate(
                item.material.odorant_reservoir_nanograms
            ):
                total[index] += mass
    return tuple(total)


def test_world_owned_interval_has_no_body_actor_or_retained_action_tail():
    world = EmbodimentWorldAuthority(authority_key=b"passive-world-test-key")
    before = world.observation_snapshot()
    retained_before = world.recent_applied_receipts()

    execution = world.execute_port_command(
        port_id=ENVIRONMENT_PORT_ID,
        command_payload=encode_command(
            AdvancePhysicalTimeCommand(duration_microseconds=1_000_000)
        ),
        causal_intent_receipt_sha256="4" * 64,
        expected_revision=before.revision,
    )

    assert execution.disposition == "applied"
    assert execution.actor_body_id is None
    assert execution.after.revision == before.revision + 1
    assert _odorant_total(execution.before) == _odorant_total(execution.after)
    assert world.recent_applied_receipts() == retained_before
    world.verify_execution_receipt(execution)
    assert world.execution_receipt_from_record(execution.as_record()) == execution


def test_environment_port_refuses_body_action():
    world = EmbodimentWorldAuthority(authority_key=b"passive-world-test-key")
    before = world.observation_snapshot()
    rejected = world.execute_port_command(
        port_id=ENVIRONMENT_PORT_ID,
        command_payload=encode_command(
            MoveCommand(
                target_pose=PoseMM(PositionMM(500, 500, 0), 0),
                duration_microseconds=1_000,
            )
        ),
        causal_intent_receipt_sha256="5" * 64,
        expected_revision=before.revision,
    )

    assert rejected.disposition == "rejected"
    assert rejected.reason == "environment_port_requires_physical_time"
    assert world.observation_snapshot() == before
