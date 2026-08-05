"""Inspect complete-field relation evidence for continuous auditory units."""

from __future__ import annotations

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    _component_paths_relation,
    _matching_locked_motifs,
    mount_auditory_krimelack_path,
)
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tests.test_auditory_krimelack_stream import (
    HELLO,
    HELLO_QUERY,
    TRANSPORT_SAMPLES,
    UNRELATED,
    _ambient_experience,
    _event_pcm,
)
from tools.probe_auditory_surrounded_event_recognition import _experience
from fractions import Fraction


def _report(name, evidence, left, right) -> None:
    matches = tuple(
        _matching_locked_motifs(left_path, right_path)
        for left_path, right_path in zip(left, right, strict=True)
    )
    pressure_left = sum(len(value) for value in left[0::2])
    pressure_right = sum(len(value) for value in right[0::2])
    pressure_matches = sum(matches[0::2])
    phase_left = sum(len(value) for value in left[1::2])
    phase_right = sum(len(value) for value in right[1::2])
    phase_matches = sum(matches[1::2])
    print(
        name,
        "matching",
        evidence.matching,
        "pressure",
        evidence.pressure_matching,
        "phase",
        evidence.phase_matching,
        "whole_l6",
        evidence.left_l6.locked,
        evidence.right_l6.locked,
        "pressure_l6",
        evidence.left_pressure_l6.locked,
        evidence.right_pressure_l6.locked,
        "phase_l6",
        evidence.left_phase_l6.locked,
        evidence.right_phase_l6.locked,
        "locked",
        evidence.locked,
        "pressure_indices",
        tuple(
            index
            for index, locked in enumerate(
                evidence.component_locks[0::2]
            )
            if locked
        ),
        "phase_indices",
        tuple(
            index
            for index, locked in enumerate(
                evidence.component_locks[1::2]
            )
            if locked
        ),
        "aggregate_pressure",
        pressure_matches,
        pressure_left,
        pressure_right,
        canonical_l6_direction(
            dimensions=pressure_left,
            matching_non_null=pressure_matches,
            matching_quiescent=0,
        ).locked,
        canonical_l6_direction(
            dimensions=pressure_right,
            matching_non_null=pressure_matches,
            matching_quiescent=0,
        ).locked,
        "aggregate_phase",
        phase_matches,
        phase_left,
        phase_right,
        canonical_l6_direction(
            dimensions=phase_left,
            matching_non_null=phase_matches,
            matching_quiescent=0,
        ).locked,
        canonical_l6_direction(
            dimensions=phase_right,
            matching_non_null=phase_matches,
            matching_quiescent=0,
        ).locked,
    )


def main() -> None:
    start_exact_field_executor().assert_healthy()
    owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        tutor = _experience(HELLO, 0, owner)[0]
        query = _event_pcm(HELLO_QUERY)
        midpoint = len(query) // 4 * 2
        first = _ambient_experience(
            owner,
            query[:midpoint],
            offset=TRANSPORT_SAMPLES - midpoint // 2,
            anchor=Fraction(5_000),
            assembly_id="probe-stream-first",
        )
        second = _ambient_experience(
            owner,
            query[midpoint:],
            offset=0,
            anchor=Fraction(5_002),
            assembly_id="probe-stream-second",
        )
        unrelated = _ambient_experience(
            owner,
            _event_pcm(UNRELATED),
            offset=0,
            anchor=Fraction(6_000),
            assembly_id="probe-stream-unrelated",
        )
    finally:
        stop_exact_field_executor()
    tutor_path = mount_auditory_krimelack_path(tutor)
    first_path = mount_auditory_krimelack_path(first)
    second_path = mount_auditory_krimelack_path(second)
    unrelated_path = mount_auditory_krimelack_path(unrelated)
    composite = tuple(
        (*left, *right)
        for left, right in zip(
            first_path.component_paths,
            second_path.component_paths,
            strict=True,
        )
    )
    _report(
        "first",
        _component_paths_relation(
            tutor_path.component_paths,
            first_path.component_paths,
        ),
        tutor_path.component_paths,
        first_path.component_paths,
    )
    _report(
        "second",
        _component_paths_relation(
            tutor_path.component_paths,
            second_path.component_paths,
        ),
        tutor_path.component_paths,
        second_path.component_paths,
    )
    _report(
        "composite",
        _component_paths_relation(
            tutor_path.component_paths,
            composite,
        ),
        tutor_path.component_paths,
        composite,
    )
    _report(
        "unrelated",
        _component_paths_relation(
            tutor_path.component_paths,
            unrelated_path.component_paths,
        ),
        tutor_path.component_paths,
        unrelated_path.component_paths,
    )


if __name__ == "__main__":
    main()
