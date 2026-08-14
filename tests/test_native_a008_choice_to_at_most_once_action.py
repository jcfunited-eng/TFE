from __future__ import annotations

import pytest

from dsf_ai_service import native_production_app as production
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
    _default_objects,
)


def test_one_layer_12_intent_commits_one_world_successor_at_most_once(
    monkeypatch,
) -> None:
    world = EmbodimentWorldAuthority(
        authority_key="a008-at-most-once-world",
        initial_objects=_default_objects()[:1],
    )
    monkeypatch.setattr(production, "_world", lambda: world)
    before = world.observation_snapshot()

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
    authority, capability, predecessor_heading, trajectory = prepared
    receipt = capability.execution_receipt
    assert predecessor_heading == 0
    assert trajectory == (5,)
    assert receipt.expected_revision == before.revision
    assert receipt.after.revision == before.revision + 1
    assert authority.observation_snapshot() == before

    with authority.prepared_action_visibility_transaction(capability):
        committed = authority.commit_prepared_action(capability)
        persisted = authority.encoded_committed_prepared_action(capability)

    assert committed is receipt
    assert committed.disposition == "applied"
    assert committed.lifecycle[-1] == "applied"
    assert committed.before.state_sha256 != committed.after.state_sha256
    assert authority.observation_snapshot().revision == before.revision + 1
    assert authority.encoded_snapshot() == persisted
    assert authority.status()["prepared_action_execution"] == 0

    with pytest.raises(ValueError, match="changed custody"):
        authority.commit_prepared_action(capability)
    assert authority.observation_snapshot().revision == before.revision + 1

