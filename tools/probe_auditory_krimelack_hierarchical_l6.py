"""Test two-level canonical L6 over auditory Krimelack motifs and paths.

Each settled 10 ms cochlear motif first earns a local canonical L6 lock from
its sixteen balanced trits.  A maximum monotone one-to-one path then counts
only those locked motif relations.  The resulting ordered constraints are
submitted to canonical L6 in both whole-path directions.  No fitted score,
distance, penalty, transcript, label, source, or chi participates.
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
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction,
)
from tools.probe_auditory_surrounded_event_recognition import _experience


def _motif_locks(left, right) -> bool:
    left_dimensions = sum(value != 0 for value in left)
    right_dimensions = sum(value != 0 for value in right)
    if left_dimensions == 0 or right_dimensions == 0:
        return False
    matching = sum(
        left_value != 0
        and right_value != 0
        and left_value == right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
    return (
        canonical_l6_direction(
            dimensions=left_dimensions,
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
        and canonical_l6_direction(
            dimensions=right_dimensions,
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
    )


def _ordered_locked_motifs(left, right) -> int:
    prior = [0] * (len(right) + 1)
    for left_motif in left:
        current = [0]
        for right_index, right_motif in enumerate(right, 1):
            local = int(_motif_locks(left_motif, right_motif))
            current.append(max(
                prior[right_index],
                current[-1],
                prior[right_index - 1] + local,
            ))
        prior = current
    return prior[-1]


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
    finally:
        stop_exact_field_executor()
    paths = tuple(
        mount_auditory_krimelack_path(value)
        for value in experiences
    )
    settled_frames = tuple(
        len(path.frames) - len(path.unsettled_frame_indices)
        for path in paths
    )

    results = []
    for source, query_index in zip(
        args.queries,
        range(1, len(paths)),
        strict=True,
    ):
        matching = _ordered_locked_motifs(
            paths[0].frames,
            paths[query_index].frames,
        )
        left_l6 = canonical_l6_direction(
            dimensions=settled_frames[0],
            matching_non_null=matching,
            matching_quiescent=0,
        )
        right_l6 = canonical_l6_direction(
            dimensions=settled_frames[query_index],
            matching_non_null=matching,
            matching_quiescent=0,
        )
        results.append({
            "left_effective_dimensions": left_l6.effective_dimensions,
            "locked_motif_relations": matching,
            "query": str(source.resolve()),
            "query_settled_frames": settled_frames[query_index],
            "right_effective_dimensions": right_l6.effective_dimensions,
            "structurally_locked": left_l6.locked and right_l6.locked,
        })
    print(json.dumps({
        "reference": str(args.reference.resolve()),
        "reference_settled_frames": settled_frames[0],
        "results": results,
        "schema": "guala.audit.auditory_krimelack_hierarchical_l6.v1",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
