from __future__ import annotations

from dsf_ai_service.substrate.experience_grounded_conversation_acceptance import (
    _goal_rungs,
)
from tests.test_w1_grounded_lived_sequence import _proof_fixture


def test_one_ordered_sequence_proves_answering_but_not_daily_or_continuity():
    (
        owner,
        demonstration_owner,
        demonstration,
        first,
        second,
    ) = _proof_fixture()
    owner.admit(
        demonstration=demonstration,
        lived_settlements=(first, second),
    )

    rungs = {
        value.capability: value
        for value in _goal_rungs(
            demonstration_owner=demonstration_owner,
            lived_sequence_owner=owner,
        )
    }

    assert rungs[
        "attend_to_short_story_and_answer_about_it"
    ].state == "achieved_authenticated_lived_proof"
    assert rungs[
        "describe_one_lived_daily_event"
    ].state == "not_evaluable_missing_authority"
    assert "routine" in rungs[
        "describe_one_lived_daily_event"
    ].missing_authority
    assert rungs[
        "keep_simple_story_on_topic"
    ].state == "not_evaluable_missing_authority"
    assert "two source-disjoint" in rungs[
        "keep_simple_story_on_topic"
    ].missing_authority
    assert all(
        "age" not in value.capability
        and "age" not in value.missing_authority
        for value in rungs.values()
    )
