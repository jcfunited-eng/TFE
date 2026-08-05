"""The retired semantic somatic boundary must fail closed."""

from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.somatic_boundary import (
    ChemistryPortBoundaryStatus,
    SOMATIC_LANE_TO_PORT_ID,
    observe_chemistry_port_boundary,
    observe_smell_port_boundary,
    observe_taste_port_boundary,
    observe_touch_port_boundary,
)


@pytest.mark.parametrize(
    ("observe", "descriptor"),
    (
        (observe_touch_port_boundary, "warm"),
        (observe_smell_port_boundary, "floral"),
        (observe_taste_port_boundary, "sweet"),
        (observe_touch_port_boundary, None),
        (observe_smell_port_boundary, None),
        (observe_taste_port_boundary, None),
    ),
)
def test_semantic_and_empty_requests_cannot_mint_sensory_evidence(
    observe,
    descriptor,
):
    result = observe(
        None,
        event_id="event-1",
        observation_id="observation-1",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor=descriptor,
    )

    assert result.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert result.observation is None
    assert "physical material" in result.reason


def test_arbitrary_port_cannot_bypass_retirement():
    result = observe_chemistry_port_boundary(
        None,
        "invented-port",
        event_id="event-2",
        observation_id="observation-2",
        source_time_start=Fraction(0),
        source_time_end=Fraction(1),
        active_descriptor="anything",
    )

    assert result.status is ChemistryPortBoundaryStatus.UNKNOWN
    assert result.observation is None
    assert result.lane_id is None


def test_compatibility_port_ids_remain_stable_without_authority():
    assert SOMATIC_LANE_TO_PORT_ID == {
        "smell": "story-smell.native-port-0",
        "taste": "story-taste.native-port-0",
        "touch": "story-touch.native-port-0",
    }
