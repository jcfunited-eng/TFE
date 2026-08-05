"""Retired semantic touch, smell, and taste boundary.

The former implementation accepted words such as a touch or smell
descriptor and minted a unit boundary flux.  That made language the causal
source of sensory evidence.  It is prohibited and is retired fail-closed.

Physical somatic and chemical observations now require a world-coupled
provider that authenticates material state, environmental transport, body
surface contact, and receptor values.  Until such evidence is supplied
through that provider, this compatibility boundary returns ``UNKNOWN`` and
never creates a ``StoryPhysicalBoundaryObservation``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from .story_chemistry import (
    StoryChemistryRuntime,
    StoryPhysicalBoundaryObservation,
)


SOMATIC_BOUNDARY_PROVENANCE_SCHEMA = "glew.somatic_boundary.retired.v2"

SOMATIC_LANE_TO_PORT_ID: dict[str, str] = {
    "smell": "story-smell.native-port-0",
    "taste": "story-taste.native-port-0",
    "touch": "story-touch.native-port-0",
}
PORT_ID_TO_SOMATIC_LANE: dict[str, str] = {
    port_id: lane for lane, port_id in SOMATIC_LANE_TO_PORT_ID.items()
}


class ChemistryPortBoundaryStatus(str, Enum):
    OBSERVED = "observed"
    UNKNOWN = "unknown"


class SomaticBoundaryEventKind(str, Enum):
    RETIRED_SEMANTIC_SOURCE = "retired_semantic_source"


@dataclass(frozen=True, slots=True)
class ChemistryPortBoundaryResult:
    status: ChemistryPortBoundaryStatus
    port_id: str
    active_descriptor: str | None
    lane_id: str | None
    event_kind: SomaticBoundaryEventKind | None
    observation: StoryPhysicalBoundaryObservation | None
    reason: str


def _retired_result(
    *,
    port_id: str,
    active_descriptor: str | None,
) -> ChemistryPortBoundaryResult:
    lane_id = PORT_ID_TO_SOMATIC_LANE.get(port_id)
    return ChemistryPortBoundaryResult(
        status=ChemistryPortBoundaryStatus.UNKNOWN,
        port_id=port_id,
        active_descriptor=active_descriptor,
        lane_id=lane_id,
        event_kind=SomaticBoundaryEventKind.RETIRED_SEMANTIC_SOURCE,
        observation=None,
        reason=(
            "semantic somatic boundary is retired; physical material, transport, "
            "contact, and receptor evidence is required"
        ),
    )


def observe_chemistry_port_boundary(
    runtime: StoryChemistryRuntime | None,
    port_id: str,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    """Refuse to convert a descriptor or its absence into sensory evidence."""

    del runtime, event_id, observation_id, source_time_start, source_time_end
    return _retired_result(
        port_id=port_id if isinstance(port_id, str) else "",
        active_descriptor=active_descriptor,
    )


def observe_touch_port_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    return observe_chemistry_port_boundary(
        runtime,
        SOMATIC_LANE_TO_PORT_ID["touch"],
        event_id=event_id,
        observation_id=observation_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        active_descriptor=active_descriptor,
    )


def observe_smell_port_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    return observe_chemistry_port_boundary(
        runtime,
        SOMATIC_LANE_TO_PORT_ID["smell"],
        event_id=event_id,
        observation_id=observation_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        active_descriptor=active_descriptor,
    )


def observe_taste_port_boundary(
    runtime: StoryChemistryRuntime | None,
    *,
    event_id: str,
    observation_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    active_descriptor: str | None = None,
) -> ChemistryPortBoundaryResult:
    return observe_chemistry_port_boundary(
        runtime,
        SOMATIC_LANE_TO_PORT_ID["taste"],
        event_id=event_id,
        observation_id=observation_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        active_descriptor=active_descriptor,
    )


__all__ = (
    "PORT_ID_TO_SOMATIC_LANE",
    "SOMATIC_BOUNDARY_PROVENANCE_SCHEMA",
    "SOMATIC_LANE_TO_PORT_ID",
    "ChemistryPortBoundaryResult",
    "ChemistryPortBoundaryStatus",
    "SomaticBoundaryEventKind",
    "observe_chemistry_port_boundary",
    "observe_smell_port_boundary",
    "observe_taste_port_boundary",
    "observe_touch_port_boundary",
)
