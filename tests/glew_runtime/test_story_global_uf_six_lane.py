from __future__ import annotations

from dataclasses import replace

import pytest

from dsf_ai_service.glew_runtime.commit import AuthorityDisposition
from dsf_ai_service.glew_runtime.experience_origin import ExperienceOriginKind
from dsf_ai_service.glew_runtime.model import ReceiptError
from dsf_ai_service.glew_runtime.story_global_uf_basin import evaluate_story_global_uf
from tests.glew_runtime.test_story_global_uf_basin import (
    _mount_authorities,
    _mounted_six_lane_preparation,
)


def test_self_recall_preserves_senses_with_exact_zero_fresh_event_support():
    preparation, topology, pre_window, profile, boundary, typed, registry = (
        _mounted_six_lane_preparation()
    )
    mounted, registry = _mount_authorities(
        preparation=preparation,
        topology=topology,
        profile=profile,
        boundary=boundary,
        origin_kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        registry=registry,
    )
    result = evaluate_story_global_uf(
        authority_id="story-six-lane-recall-global-uf",
        preparation=preparation,
        mounted_authorities=mounted,
        topology=topology,
        pre_window_state=pre_window,
        receipt_registry=registry,
    )

    assert all(item.event_support_evaluation.exact_r_event == 0 for item in mounted)
    assert result.preparation.observation_window.typed_unicode_observations[0].text == (
        typed.event.normalized_text
    )
    expected_keys = {fiber.key for fiber in topology.ordered_port_fibers}
    assert all(
        {item.key for item in context.preparation.evidence} == expected_keys
        for context in preparation.contexts
    )
    assert result.validation.authority.disposition in (
        AuthorityDisposition.PASS,
        AuthorityDisposition.FAIL,
    )
    result.validation.verify()


def test_counterfactual_cannot_inherit_base_scoped_authorities():
    preparation, topology, pre_window, profile, boundary, _, registry = (
        _mounted_six_lane_preparation()
    )
    mounted, registry = _mount_authorities(
        preparation=preparation,
        topology=topology,
        profile=profile,
        boundary=boundary,
        origin_kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
        registry=registry,
    )
    crossed = list(mounted)
    crossed[1] = replace(
        crossed[1],
        origin=mounted[0].origin,
        safe_mode_evaluation=mounted[0].safe_mode_evaluation,
        event_support_evaluation=mounted[0].event_support_evaluation,
        l6_scope=mounted[0].l6_scope,
        pending_conjunction=mounted[0].pending_conjunction,
    )

    with pytest.raises(ReceiptError):
        evaluate_story_global_uf(
            authority_id="story-six-lane-cross-scope-global-uf",
            preparation=preparation,
            mounted_authorities=tuple(crossed),
            topology=topology,
            pre_window_state=pre_window,
            receipt_registry=registry,
        )

