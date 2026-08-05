"""Shared test fixture support: declare joint-source occurrences for a boundary.

The native GLJSRC02 carrier requires every built six-sense full field to
declare its source occurrences explicitly.  Tests that construct their own
observed substreams use this helper to declare the matching occurrences
through the canonical production declarer: ports that settle jointly
(identical source clocks) form one declared unit over the test's own
source_times, with the canonical piecewise-linear payload and unit
relevance.
"""

from __future__ import annotations

from typing import Mapping

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER


def joint_occurrences_for(observed_substreams: Mapping[object, tuple]):
    """Declare one occurrence per jointly-settling receptor clock group."""

    by_clock: dict[tuple, list[tuple[object, int]]] = {}
    for sense in SENSE_ORDER:
        for port in observed_substreams.get(sense, ()):
            by_clock.setdefault(tuple(port.source_times), []).append(
                (sense, port.topology_index)
            )
    return declare_joint_source_occurrences(
        observed_substreams=observed_substreams,
        declared_units=tuple(
            tuple(unit) for unit in by_clock.values()
        ),
    )
