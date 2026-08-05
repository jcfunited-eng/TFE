"""Isolate which authority dimension rejects three Hello Guala recordings."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable

import dsf_ai_service.substrate.auditory_reciprocity as reciprocity
from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


RECORDINGS = (
    Path("/workspaces/Tao_Financial_Engine/harness/Hello Guala.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 1.mp3"),
    Path("/workspaces/Tao_Financial_Engine/harness/hello guala 2.mp3"),
)


def _local_interval(
    query,
    left,
    right,
    query_index: int,
    reference_index: int,
    ports: tuple[int, ...],
    *,
    include_phase: bool,
):
    reference_count = max(left.sample_count, right.sample_count)
    interval = (0.0, 1.0)
    pressure_uncertainty = 2.0 * float(reciprocity.PCM_PRESSURE_QUANTUM)
    for port in ports:
        query_pressure, query_phase = reciprocity._interpolated_sample(
            query, port, query_index, query.sample_count
        )
        left_pressure, left_phase = reciprocity._interpolated_sample(
            left, port, reference_index, reference_count
        )
        right_pressure, right_phase = reciprocity._interpolated_sample(
            right, port, reference_index, reference_count
        )
        interval = reciprocity._intersect_lambda(
            interval,
            query=query_pressure,
            left=left_pressure,
            right=right_pressure,
            uncertainty=pressure_uncertainty,
        )
        if interval is None:
            return None
        if not include_phase or query_index == 0 or reference_index == 0:
            continue
        phase_uncertainty = reciprocity._phase_uncertainty(
            query_pressure,
            reciprocity._interpolated_phase_prior_pressure(
                query, port, query_index, query.sample_count
            ),
            left_pressure,
            reciprocity._interpolated_phase_prior_pressure(
                left, port, reference_index, reference_count
            ),
            right_pressure,
            reciprocity._interpolated_phase_prior_pressure(
                right, port, reference_index, reference_count
            ),
        )
        if phase_uncertainty is not None:
            interval = reciprocity._intersect_lambda(
                interval,
                query=query_phase,
                left=left_phase,
                right=right_phase,
                uncertainty=phase_uncertainty,
            )
        if interval is None:
            return None
    return interval


def _monotone_path(
    query,
    left,
    right,
    feasible: Callable[[int, int], bool],
) -> tuple[bool, int]:
    reference_count = max(left.sample_count, right.sample_count)
    previous = [False] * reference_count
    feasible_cells = 0
    for query_index in range(query.sample_count):
        current = [False] * reference_count
        for reference_index in range(reference_count):
            local = feasible(query_index, reference_index)
            feasible_cells += int(local)
            if not local:
                continue
            if query_index == 0 and reference_index == 0:
                current[reference_index] = True
                continue
            current[reference_index] = (
                (query_index > 0 and previous[reference_index])
                or (reference_index > 0 and current[reference_index - 1])
                or (
                    query_index > 0
                    and reference_index > 0
                    and previous[reference_index - 1]
                )
            )
        previous = current
    return previous[-1], feasible_cells


def _local_path(query, left, right, ports, *, include_phase):
    return _monotone_path(
        query,
        left,
        right,
        lambda query_index, reference_index: _local_interval(
            query,
            left,
            right,
            query_index,
            reference_index,
            ports,
            include_phase=include_phase,
        )
        is not None,
    )


def main() -> None:
    exact_owner = start_exact_field_executor()
    exact_owner.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        experiences = tuple(
            _experience(path, index, l5_owner)[0]
            for index, path in enumerate(RECORDINGS)
        )
    finally:
        stop_exact_field_executor()

    query, left, right = tuple(
        reciprocity._pack_experience(value) for value in experiences
    )
    print({
        "sample_counts": (
            query.sample_count,
            left.sample_count,
            right.sample_count,
        ),
        "pressure_l4_counts": (
            len(query.pressure_l4_field_tuples[0]),
            len(left.pressure_l4_field_tuples[0]),
            len(right.pressure_l4_field_tuples[0]),
        ),
        "l4_relation": reciprocity._l4_lambda_interval(
            query, left, right, (0.0, 1.0)
        ),
        "original": reciprocity._joint_cell_contains_python(
            query, left, right, max_work=1_000_000
        ),
    })
    query_without_l4_difference = replace(
        query,
        pressure_l4_field_tuples=left.pressure_l4_field_tuples,
        carrier_phase_advance_l4_field_tuples=(
            left.carrier_phase_advance_l4_field_tuples
        ),
    )
    right_without_l4_difference = replace(
        right,
        pressure_l4_field_tuples=left.pressure_l4_field_tuples,
        carrier_phase_advance_l4_field_tuples=(
            left.carrier_phase_advance_l4_field_tuples
        ),
    )
    all_ports = tuple(range(len(query.topology)))
    print({
        "neutralized_l4": reciprocity._joint_cell_contains_python(
            query_without_l4_difference,
            left,
            right_without_l4_difference,
            max_work=1_000_000,
        ),
        "local_lambda_all_ports_pressure": _local_path(
            query, left, right, all_ports, include_phase=False
        ),
        "local_lambda_all_ports_pressure_phase": _local_path(
            query, left, right, all_ports, include_phase=True
        ),
        "local_lambda_per_port_pressure": tuple(
            _local_path(
                query, left, right, (port,), include_phase=False
            )
            for port in all_ports
        ),
        "local_lambda_per_port_pressure_phase": tuple(
            _local_path(
                query, left, right, (port,), include_phase=True
            )
            for port in all_ports
        ),
    })


if __name__ == "__main__":
    main()
