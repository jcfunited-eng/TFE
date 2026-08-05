"""Falsify balanced-ternary auditory Krimelack Negative Space.

This diagnostic differs from the current candidate only in one structural
fact: a physically settled lower cochlear pressure basin is a ``-1``
commitment, not uncertainty.  Only a frame whose two basins cannot be
physically separated becomes all-null.  The complete experiences are still
settled through exact L0--L4 before this L5 diagnostic is evaluated.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_event_boundary import (
    partition_auditory_energy_basins,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.auditory_reciprocity import (
    PCM_PRESSURE_QUANTUM,
)
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction,
)
from tools.probe_auditory_surrounded_event_recognition import _experience


def _balanced_path(experience) -> tuple[tuple[int, ...], ...]:
    frame_count = len(experience.channels[0].pressure.samples)
    rows = []
    for frame_index in range(frame_count):
        pressure = tuple(
            float(channel.pressure.samples[frame_index].signal)
            for channel in experience.channels
        )
        try:
            partition = partition_auditory_energy_basins(
                tuple((value,) for value in pressure),
                pressure_uncertainty_full_scale=float(
                    PCM_PRESSURE_QUANTUM
                ),
            )
        except ValueError:
            rows.append((0,) * len(pressure))
            continue
        lower = frozenset(partition.lower_indices)
        upper = frozenset(partition.upper_indices)
        if (
            lower & upper
            or lower | upper != frozenset(range(len(pressure)))
        ):
            raise RuntimeError(
                "auditory pressure basin partition lost one channel"
            )
        rows.append(tuple(
            1 if index in upper else -1
            for index in range(len(pressure))
        ))
    return tuple(rows)


def _matching_non_null(left, right) -> int:
    prior = [0] * (len(right) + 1)
    for left_frame in left:
        current = [0]
        for right_index, right_frame in enumerate(right, 1):
            local = sum(
                1
                for left_value, right_value in zip(
                    left_frame,
                    right_frame,
                    strict=True,
                )
                if (
                    left_value != 0
                    and right_value != 0
                    and left_value == right_value
                )
            )
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
    paths = tuple(_balanced_path(value) for value in experiences)
    dimensions = tuple(
        sum(value != 0 for frame in path for value in frame)
        for path in paths
    )

    results = []
    for source, query_index in zip(
        args.queries,
        range(1, len(paths)),
        strict=True,
    ):
        matching = _matching_non_null(paths[0], paths[query_index])
        left_l6 = canonical_l6_direction(
            dimensions=dimensions[0],
            matching_non_null=matching,
            matching_quiescent=0,
        )
        right_l6 = canonical_l6_direction(
            dimensions=dimensions[query_index],
            matching_non_null=matching,
            matching_quiescent=0,
        )
        results.append({
            "left_effective_dimensions": left_l6.effective_dimensions,
            "matching_non_null": matching,
            "query": str(source.resolve()),
            "query_dimensions": dimensions[query_index],
            "right_effective_dimensions": right_l6.effective_dimensions,
            "structurally_locked": left_l6.locked and right_l6.locked,
        })
    print(json.dumps({
        "reference": str(args.reference.resolve()),
        "reference_dimensions": dimensions[0],
        "results": results,
        "schema": "guala.audit.auditory_krimelack_negative_space.v1",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
