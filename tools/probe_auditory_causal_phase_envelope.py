"""Test exact full-field causal-phase envelopes on supplied recordings.

This diagnostic does not alter recognition.  Two tutor experiences define,
for each cochlear component and causally overlapping normalized event phase,
the exact closed interval witnessed for every D/M/R/U/C/P/B field.  A query
gate is supported only when every explicit field lies inside the witnessed
interval.  There is no distance, tolerance, score, label lookup, or chi.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


HELLO_TUTORS = (
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
)
QUERIES = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Daddy says Hello.mp3"),
    Path("/workspaces/Tao_Financial_Engine/docs/Your Name is Guala.mp3"),
)


def _phase(value, sample_count: int) -> tuple[Fraction, Fraction]:
    return (
        Fraction(value.source_index_start, sample_count),
        Fraction(value.source_index_end + 1, sample_count),
    )


def _overlaps(
    left: tuple[Fraction, Fraction],
    right: tuple[Fraction, Fraction],
) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _component_report(query, tutors) -> dict[str, object]:
    query_count = query.tuples[-1].source_index_end + 1
    tutor_counts = tuple(
        value.tuples[-1].source_index_end + 1 for value in tutors
    )
    supported = 0
    field_supported = 0
    field_total = 0
    for query_tuple in query.tuples:
        query_phase = _phase(query_tuple, query_count)
        candidates = tuple(
            tuple(
                value
                for value in tutor.tuples
                if _overlaps(
                    query_phase,
                    _phase(value, tutor_count),
                )
            )
            for tutor, tutor_count in zip(
                tutors, tutor_counts, strict=True
            )
        )
        query_fields = dict(query_tuple.fields)
        tuple_supported = all(candidates)
        for field_name, query_value in query_tuple.fields:
            witnessed = tuple(
                dict(value.fields)[field_name]
                for tutor_candidates in candidates
                for value in tutor_candidates
            )
            inside = (
                bool(witnessed)
                and min(witnessed) <= query_value <= max(witnessed)
            )
            field_supported += int(inside)
            field_total += 1
            tuple_supported = tuple_supported and inside
        supported += int(tuple_supported)
    return {
        "supported_tuples": supported,
        "total_tuples": len(query.tuples),
        "supported_fields": field_supported,
        "total_fields": field_total,
        "complete": supported == len(query.tuples),
    }


def main() -> None:
    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        tutor_experiences = tuple(
            _experience(path, index, l5_owner)[0]
            for index, path in enumerate(HELLO_TUTORS)
        )
        query_experiences = tuple(
            _experience(path, index + len(HELLO_TUTORS), l5_owner)[0]
            for index, path in enumerate(QUERIES)
        )
    finally:
        stop_exact_field_executor()
    tutor_supports = tuple(
        mount_auditory_l4_causal_support(value)
        for value in tutor_experiences
    )
    reports = []
    for path, experience in zip(QUERIES, query_experiences, strict=True):
        support = mount_auditory_l4_causal_support(experience)
        components = tuple(
            _component_report(
                component,
                tuple(
                    tutor.components[index] for tutor in tutor_supports
                ),
            )
            for index, component in enumerate(support.components)
        )
        reports.append({
            "path": str(path),
            "complete_components": sum(
                value["complete"] for value in components
            ),
            "component_count": len(components),
            "supported_tuples": sum(
                value["supported_tuples"] for value in components
            ),
            "total_tuples": sum(
                value["total_tuples"] for value in components
            ),
            "supported_fields": sum(
                value["supported_fields"] for value in components
            ),
            "total_fields": sum(
                value["total_fields"] for value in components
            ),
        })
    print(json.dumps({
        "schema": "guala.audit.auditory_causal_phase_envelope.v1",
        "tutors": [str(value) for value in HELLO_TUTORS],
        "queries": reports,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
