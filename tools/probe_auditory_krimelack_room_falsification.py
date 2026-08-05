"""Read-only full-DSF Krimelack falsification over room transforms.

Every input is independently transduced and settled through the unchanged
L0--L4 kernel and auditory L5.  This probe invokes the same complete
component-path relation as live Krimelack memory.  It does not teach, label,
transcribe, tune, or mutate a persistent owner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    mount_auditory_krimelack_path,
    relate_auditory_krimelack_paths,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


def _l6_record(value) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("queries", nargs="+", type=Path)
    args = parser.parse_args()
    sources = (args.reference, *args.queries)
    for source in sources:
        if not source.is_file():
            raise SystemExit(f"recording does not exist: {source}")

    executor = start_exact_field_executor()
    executor.assert_healthy()
    owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        experiences = tuple(
            _experience(source, ordinal, owner)[0]
            for ordinal, source in enumerate(sources)
        )
        paths = tuple(
            mount_auditory_krimelack_path(experience)
            for experience in experiences
        )
    finally:
        stop_exact_field_executor()

    results = []
    for source, query in zip(args.queries, paths[1:], strict=True):
        relation = relate_auditory_krimelack_paths(paths[0], query)
        relation.verify(paths[0], query)
        results.append({
            "committed_trits": query.committed_trits,
            "component_tuple_counts": [
                len(component) for component in query.component_paths
            ],
            "matching_locked_components": relation.matching_non_null,
            "phase_matching_locked_components": (
                relation.phase_matching_non_null
            ),
            "pressure_matching_locked_components": (
                relation.pressure_matching_non_null
            ),
            "pressure_neighborhoods_locked": (
                relation.pressure_neighborhoods_locked
            ),
            "query": str(source.resolve()),
            "reciprocal_l6": {
                "left": _l6_record(relation.left_l6),
                "right": _l6_record(relation.right_l6),
            },
            "structurally_locked": relation.structurally_locked,
            "work_cells": relation.work_cells,
        })
    print(json.dumps({
        "field_authority": (
            "all ordered D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k "
            "states and exact causal changes"
        ),
        "reference": str(args.reference.resolve()),
        "reference_committed_trits": paths[0].committed_trits,
        "reference_component_tuple_counts": [
            len(component)
            for component in paths[0].component_paths
        ],
        "results": results,
        "schema": (
            "guala.audit.auditory_krimelack_room_falsification.v2"
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
