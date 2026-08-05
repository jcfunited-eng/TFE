"""Persistence absence contract for retired text-derived action state."""

from dsf_ai_service.substrate.owner_scoped_persistence import (
    OWNER_STATE_GROUPS,
    TEACHING_MONOLITH_OWNERS,
)


def test_retired_action_owner_has_no_persistence_authority() -> None:
    owner_ids = {group.owner_id for group in OWNER_STATE_GROUPS}
    assert "causal_action" not in owner_ids
    assert "causal_speech_release" not in owner_ids
    assert "causal_action" not in TEACHING_MONOLITH_OWNERS
    assert "causal_speech_release" not in TEACHING_MONOLITH_OWNERS
