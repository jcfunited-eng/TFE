"""Read-only probe for a complete-field auditory Krimelack relation.

Every pressure and phase component contributes every ordered
D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k tuple.  A tuple becomes seven balanced
trits by its exact relation to zero; zero remains canonical quiescence.  Local
tuple, per-component path, and whole-cochlea decisions use reciprocal
canonical L6 only.  This diagnostic does not teach, label, transcribe, or
alter state.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction,
)
from tools.probe_auditory_surrounded_event_recognition import _experience


def _trit(value) -> int:
    return -1 if value < 0 else 1 if value > 0 else 0


def _components(experience):
    return tuple(
        _component(component)
        for channel in experience.channels
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        )
    )


def _component(component):
    result = []
    prior = None
    for field_tuple in component.l4_field_tuples:
        values = tuple(value for _name, value in field_tuple.fields)
        result.append(tuple(
            _trit(value) for value in values
        ) + tuple(
            0 if prior is None else _trit(value - prior_value)
            for value, prior_value in zip(
                values,
                prior if prior is not None else values,
                strict=True,
            )
        ))
        prior = values
    return tuple(result)


def _tuple_locks(left, right) -> bool:
    if len(left) != 2 * len(DSF_FIELD_ORDER) or len(right) != 2 * len(
        DSF_FIELD_ORDER
    ):
        raise RuntimeError("full DSF tuple width changed")
    non_null = sum(
        l == r and l != 0 for l, r in zip(left, right, strict=True)
    )
    quiescent = sum(
        l == r == 0 for l, r in zip(left, right, strict=True)
    )
    forward = canonical_l6_direction(
        dimensions=len(left),
        matching_non_null=non_null,
        matching_quiescent=quiescent,
    )
    reverse = canonical_l6_direction(
        dimensions=len(right),
        matching_non_null=non_null,
        matching_quiescent=quiescent,
    )
    return forward.locked and reverse.locked


def _matching(left, right) -> int:
    prior = [0] * (len(right) + 1)
    for left_tuple in left:
        current = [0]
        for right_index, right_tuple in enumerate(right, 1):
            current.append(max(
                prior[right_index],
                current[-1],
                prior[right_index - 1]
                + int(_tuple_locks(left_tuple, right_tuple)),
            ))
        prior = current
    return prior[-1]


def _component_locks(left, right) -> bool:
    if not left or not right:
        return False
    matching = _matching(left, right)
    return (
        canonical_l6_direction(
            dimensions=len(left),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
        and canonical_l6_direction(
            dimensions=len(right),
            matching_non_null=matching,
            matching_quiescent=0,
        ).locked
    )


def _relation(left, right):
    locked = tuple(
        _component_locks(l_component, r_component)
        for l_component, r_component in zip(left, right, strict=True)
    )
    matching = sum(locked)
    forward = canonical_l6_direction(
        dimensions=len(left),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    reverse = canonical_l6_direction(
        dimensions=len(right),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    pressure_matching = sum(locked[0::2])
    phase_matching = sum(locked[1::2])
    pressure = canonical_l6_direction(
        dimensions=len(left) // 2,
        matching_non_null=pressure_matching,
        matching_quiescent=0,
    )
    phase = canonical_l6_direction(
        dimensions=len(right) // 2,
        matching_non_null=phase_matching,
        matching_quiescent=0,
    )
    left_pressure_counts = tuple(
        len(value) for value in left[0::2]
    )
    right_pressure_counts = tuple(
        len(value) for value in right[0::2]
    )
    left_gradient = tuple(
        _trit(second - first)
        for first, second in zip(
            left_pressure_counts,
            left_pressure_counts[1:],
        )
    )
    right_gradient = tuple(
        _trit(second - first)
        for first, second in zip(
            right_pressure_counts,
            right_pressure_counts[1:],
        )
    )
    gradient_non_null = sum(
        left_value == right_value != 0
        for left_value, right_value in zip(
            left_gradient,
            right_gradient,
            strict=True,
        )
    )
    gradient_quiescent = sum(
        left_value == right_value == 0
        for left_value, right_value in zip(
            left_gradient,
            right_gradient,
            strict=True,
        )
    )
    gradient_locked = canonical_l6_direction(
        dimensions=len(left_gradient),
        matching_non_null=gradient_non_null,
        matching_quiescent=gradient_quiescent,
    ).locked
    return (
        matching,
        pressure_matching,
        phase_matching,
        gradient_non_null + gradient_quiescent,
        gradient_locked,
        forward.locked
        and reverse.locked
        and pressure.locked
        and phase.locked,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("recordings", nargs="+", type=Path)
    args = parser.parse_args()
    owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    start_exact_field_executor().assert_healthy()
    try:
        experiences = tuple(
            _experience(path.resolve(), index, owner)[0]
            for index, path in enumerate(args.recordings)
        )
    finally:
        stop_exact_field_executor()
    paths = tuple(_components(value) for value in experiences)
    for index, path in enumerate(paths):
        print(
            "path",
            index,
            "component_tuple_counts",
            tuple(len(value) for value in path),
        )
    for left in range(len(paths)):
        for right in range(left + 1, len(paths)):
            print(
                "pair",
                left,
                right,
                "locked_components",
                *_relation(paths[left], paths[right]),
            )


if __name__ == "__main__":
    main()
