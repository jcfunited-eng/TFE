"""Retirement boundary for the reversed action-before-vocal direction path."""

from __future__ import annotations

import inspect

from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_provenance import (
    W1AnonymousSpatialVocalProvenanceAuthority,
)
from dsf_ai_service.substrate.w1_anonymous_spatial_vocal_relation import (
    W1AnonymousSpatialVocalRelationOwner,
)
from dsf_ai_service.substrate.w1_vocal_spatial_action_lesson import (
    W1VocalSpatialActionLessonAuthority,
)


def test_direction_authority_cannot_receive_reversed_action_vocal_lessons():
    relation_constructor = inspect.signature(
        W1AnonymousSpatialVocalRelationOwner
    ).parameters
    relation_composition = inspect.signature(
        W1AnonymousSpatialVocalRelationOwner.compose_lesson
    ).parameters
    provenance_constructor = inspect.signature(
        W1AnonymousSpatialVocalProvenanceAuthority
    ).parameters
    provenance_binding = inspect.signature(
        W1AnonymousSpatialVocalProvenanceAuthority.bind
    ).parameters

    assert relation_constructor["lesson_authority"].annotation in {
        W1VocalSpatialActionLessonAuthority,
        "W1VocalSpatialActionLessonAuthority",
    }
    assert "action_lesson_authority" not in relation_constructor
    assert "vocal_spatial_action_lesson" in relation_composition
    assert "action_vocal_lesson" not in relation_composition
    assert "lesson_authority" in provenance_constructor
    assert "vocal_spatial_action_lesson" in provenance_binding
    assert "action_vocal_lesson" not in provenance_binding
