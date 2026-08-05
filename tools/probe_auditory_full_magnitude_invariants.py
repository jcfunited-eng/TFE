"""Falsify exact full-magnitude auditory invariants on settled L5 evidence.

This read-only probe independently settles every supplied recording through
the unchanged auditory provider, L0--L4 kernel, and auditory L5.  It does not
teach, transcribe, score, threshold, or mutate a production owner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


@dataclass(frozen=True, slots=True)
class Asset:
    name: str
    category: str
    path: Path


@dataclass(frozen=True, slots=True)
class Pair:
    category: str
    left: str
    right: str


def _text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _component_fields(experience) -> tuple[
    tuple[str, tuple[tuple[Fraction, ...], ...]],
    ...,
]:
    components = []
    for channel in experience.channels:
        for component in (
            channel.pressure,
            channel.carrier_phase_advance,
        ):
            fields = tuple(
                tuple(dict(item.fields)[name] for item in component.l4_field_tuples)
                for name in DSF_FIELD_ORDER
            )
            components.append((component.substream_id, fields))
    return tuple(components)


def _comparison(left: Fraction, right: Fraction) -> int:
    return int(left > right) - int(left < right)


def _positive_projective(
    left: tuple[Fraction, ...],
    right: tuple[Fraction, ...],
) -> tuple[bool, dict[str, object] | None]:
    if len(left) != len(right):
        return False, {
            "reason": "shape",
            "left_values": len(left),
            "right_values": len(right),
        }
    anchor = next(
        (
            index
            for index, (left_value, right_value) in enumerate(
                zip(left, right, strict=True)
            )
            if left_value != 0 or right_value != 0
        ),
        None,
    )
    if anchor is None:
        return True, None
    left_anchor = left[anchor]
    right_anchor = right[anchor]
    if (
        left_anchor == 0
        or right_anchor == 0
        or left_anchor * right_anchor <= 0
    ):
        return False, {
            "reason": "non_positive_or_zero_anchor",
            "index": anchor,
            "left": _text(left_anchor),
            "right": _text(right_anchor),
        }
    for index, (left_value, right_value) in enumerate(
        zip(left, right, strict=True)
    ):
        left_cross = left_value * right_anchor
        right_cross = right_value * left_anchor
        if left_cross != right_cross:
            return False, {
                "reason": "cross_product",
                "anchor_index": anchor,
                "index": index,
                "left": _text(left_value),
                "right": _text(right_value),
                "left_anchor": _text(left_anchor),
                "right_anchor": _text(right_anchor),
                "left_cross": _text(left_cross),
                "right_cross": _text(right_cross),
            }
    return True, None


def _order_type(values: tuple[Fraction, ...]) -> tuple[int, ...]:
    ranks = {
        value: rank
        for rank, value in enumerate(sorted(set(values)))
    }
    return tuple(ranks[value] for value in values)


def _order_type_equal(
    left: tuple[Fraction, ...],
    right: tuple[Fraction, ...],
) -> tuple[bool, dict[str, object] | None]:
    if len(left) != len(right):
        return False, {
            "reason": "shape",
            "left_values": len(left),
            "right_values": len(right),
        }
    if _order_type(left) == _order_type(right):
        return True, None
    for left_index in range(len(left)):
        for right_index in range(left_index + 1, len(left)):
            left_relation = _comparison(
                left[left_index],
                left[right_index],
            )
            right_relation = _comparison(
                right[left_index],
                right[right_index],
            )
            if left_relation != right_relation:
                return False, {
                    "reason": "ordered_pair",
                    "indices": [left_index, right_index],
                    "left_values": [
                        _text(left[left_index]),
                        _text(left[right_index]),
                    ],
                    "right_values": [
                        _text(right[left_index]),
                        _text(right[right_index]),
                    ],
                    "left_relation": left_relation,
                    "right_relation": right_relation,
                }
    raise RuntimeError("unequal order types had no unequal ordered pair")


def _collapse_runs(
    values: tuple[Fraction, ...],
) -> tuple[tuple[Fraction, int, int], ...]:
    if not values:
        return ()
    runs: list[tuple[Fraction, int, int]] = []
    start = 0
    current = values[0]
    for index, value in enumerate(values[1:], 1):
        if value == current:
            continue
        runs.append((current, start, index - 1))
        current = value
        start = index
    runs.append((current, start, len(values) - 1))
    return tuple(runs)


def _run_order_type_equal(
    left: tuple[Fraction, ...],
    right: tuple[Fraction, ...],
) -> tuple[bool, dict[str, object] | None]:
    left_runs = _collapse_runs(left)
    right_runs = _collapse_runs(right)
    equal, failure = _order_type_equal(
        tuple(value for value, _start, _end in left_runs),
        tuple(value for value, _start, _end in right_runs),
    )
    if equal:
        return True, None
    return False, {
        "left_runs": len(left_runs),
        "right_runs": len(right_runs),
        "order_failure": failure,
    }


def _extrema_signature(
    values: tuple[Fraction, ...],
) -> tuple[tuple[int, int, int, Fraction, Fraction, Fraction], ...]:
    runs = _collapse_runs(values)
    if not runs:
        return ()
    extrema = [0]
    for index in range(1, len(runs) - 1):
        prior_direction = _comparison(
            runs[index][0],
            runs[index - 1][0],
        )
        next_direction = _comparison(
            runs[index + 1][0],
            runs[index][0],
        )
        if prior_direction != next_direction:
            extrema.append(index)
    if len(runs) > 1:
        extrema.append(len(runs) - 1)
    if len(extrema) == 1:
        value, start, end = runs[extrema[0]]
        return ((0, start, end, value, value, Fraction(0)),)
    signature = []
    for left_index, right_index in zip(
        extrema,
        extrema[1:],
    ):
        left_value, left_start, _left_end = runs[left_index]
        right_value, _right_start, right_end = runs[right_index]
        signature.append((
            _comparison(right_value, left_value),
            left_start,
            right_end,
            left_value,
            right_value,
            right_value - left_value,
        ))
    return tuple(signature)


def _signature_failure(
    left: tuple[Fraction, ...],
    right: tuple[Fraction, ...],
) -> tuple[bool, dict[str, object] | None]:
    left_signature = _extrema_signature(left)
    right_signature = _extrema_signature(right)
    if left_signature == right_signature:
        return True, None
    mismatch = next(
        (
            index
            for index, (left_value, right_value) in enumerate(
                zip(left_signature, right_signature)
            )
            if left_value != right_value
        ),
        None,
    )

    def record(value):
        if value is None:
            return None
        direction, start, end, first, last, delta = value
        return {
            "direction": direction,
            "start_index": start,
            "end_index": end,
            "start_value": _text(first),
            "end_value": _text(last),
            "delta": _text(delta),
        }

    return False, {
        "left_segments": len(left_signature),
        "right_segments": len(right_signature),
        "first_mismatch": mismatch,
        "left": record(
            left_signature[mismatch]
            if mismatch is not None
            else None
        ),
        "right": record(
            right_signature[mismatch]
            if mismatch is not None
            else None
        ),
    }


def _flatten(
    components: tuple[
        tuple[str, tuple[tuple[Fraction, ...], ...]],
        ...,
    ],
) -> tuple[Fraction, ...]:
    return tuple(
        value
        for _component_id, fields in components
        for field_values in fields
        for value in field_values
    )


def _field_flatten(
    components: tuple[
        tuple[str, tuple[tuple[Fraction, ...], ...]],
        ...,
    ],
    field_index: int,
) -> tuple[Fraction, ...]:
    return tuple(
        value
        for _component_id, fields in components
        for value in fields[field_index]
    )


def _first_failure(
    failures: Iterable[dict[str, object] | None],
) -> dict[str, object] | None:
    return next((value for value in failures if value is not None), None)


def _compare_pair(
    pair: Pair,
    assets: dict[str, Asset],
    fields: dict[
        str,
        tuple[
            tuple[str, tuple[tuple[Fraction, ...], ...]],
            ...,
        ],
    ],
) -> dict[str, object]:
    left = fields[pair.left]
    right = fields[pair.right]
    if tuple(value[0] for value in left) != tuple(
        value[0] for value in right
    ):
        raise RuntimeError("auditory component topology changed")

    component_projective = []
    rank_results = []
    run_results = []
    signature_results = []
    for (component_id, left_fields), (_, right_fields) in zip(
        left,
        right,
        strict=True,
    ):
        projective, projective_failure = _positive_projective(
            tuple(value for field in left_fields for value in field),
            tuple(value for field in right_fields for value in field),
        )
        component_projective.append((
            projective,
            {
                "component": component_id,
                **(projective_failure or {}),
            } if not projective else None,
            component_id,
        ))
        for field_index, field_name in enumerate(DSF_FIELD_ORDER):
            for target, function in (
                (rank_results, _order_type_equal),
                (run_results, _run_order_type_equal),
                (signature_results, _signature_failure),
            ):
                equal, failure = function(
                    left_fields[field_index],
                    right_fields[field_index],
                )
                target.append((
                    equal,
                    {
                        "component": component_id,
                        "field": field_name,
                        **(failure or {}),
                    } if not equal else None,
                    f"{component_id}:{field_name}",
                ))

    full_projective, full_projective_failure = _positive_projective(
        _flatten(left),
        _flatten(right),
    )
    full_rank = []
    full_run = []
    full_signature = []
    for field_index, field_name in enumerate(DSF_FIELD_ORDER):
        for target, function in (
            (full_rank, _order_type_equal),
            (full_run, _run_order_type_equal),
            (full_signature, _signature_failure),
        ):
            equal, failure = function(
                _field_flatten(left, field_index),
                _field_flatten(right, field_index),
            )
            target.append((
                equal,
                {
                    "field": field_name,
                    **(failure or {}),
                } if not equal else None,
                field_name,
            ))

    def summary(values):
        return {
            "equal": sum(
                equal for equal, _failure, _label in values
            ),
            "total": len(values),
            "all_equal": all(
                equal for equal, _failure, _label in values
            ),
            "equal_members": [
                label
                for equal, _failure, label in values
                if equal
            ],
            "first_failure": _first_failure(
                failure
                for _equal, failure, _label in values
            ),
        }

    return {
        "category": pair.category,
        "left": {
            "name": pair.left,
            "path": str(assets[pair.left].path.resolve()),
        },
        "right": {
            "name": pair.right,
            "path": str(assets[pair.right].path.resolve()),
        },
        "component_positive_projective": summary(component_projective),
        "component_field_temporal_order_type": summary(rank_results),
        "component_field_run_collapsed_order_type": summary(run_results),
        "component_field_extrema_signature": summary(signature_results),
        "full_cochlea_positive_projective": {
            "equal": full_projective,
            "first_failure": (
                full_projective_failure
                if not full_projective
                else None
            ),
        },
        "full_cochlea_field_temporal_order_type": summary(full_rank),
        "full_cochlea_field_run_collapsed_order_type": summary(full_run),
        "full_cochlea_field_extrema_signature": summary(full_signature),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--asset",
        action="append",
        nargs=3,
        metavar=("NAME", "CATEGORY", "PATH"),
        required=True,
    )
    parser.add_argument(
        "--pair",
        action="append",
        nargs=3,
        metavar=("CATEGORY", "LEFT_NAME", "RIGHT_NAME"),
        required=True,
    )
    args = parser.parse_args()
    assets = {
        name: Asset(name=name, category=category, path=Path(path))
        for name, category, path in args.asset
    }
    if len(assets) != len(args.asset):
        raise SystemExit("asset names must be unique")
    pairs = tuple(Pair(*values) for values in args.pair)
    for asset in assets.values():
        if not asset.path.is_file():
            raise SystemExit(f"asset is absent: {asset.path}")
    for pair in pairs:
        if pair.left not in assets or pair.right not in assets:
            raise SystemExit(f"pair names an unknown asset: {pair}")

    executor = start_exact_field_executor()
    executor.assert_healthy()
    l5_owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        traced = {
            asset.name: _experience(asset.path, index, l5_owner)
            for index, asset in enumerate(assets.values())
        }
    finally:
        stop_exact_field_executor()
    fields = {
        name: _component_fields(experience)
        for name, (experience, _report) in traced.items()
    }
    asset_records = []
    for name, asset in assets.items():
        _experience_value, report = traced[name]
        asset_records.append({
            "name": name,
            "category": asset.category,
            **report,
            "source_sha256": hashlib.sha256(
                asset.path.read_bytes()
            ).hexdigest(),
            "component_count": len(fields[name]),
            "field_order": list(DSF_FIELD_ORDER),
            "component_tuple_counts": {
                component_id: len(component_fields[0])
                for component_id, component_fields in fields[name]
            },
        })
    results = [
        _compare_pair(pair, assets, fields)
        for pair in pairs
    ]
    print(json.dumps({
        "schema": (
            "guala.audit.auditory_full_magnitude_invariants.v1"
        ),
        "method": {
            "positive_projective": (
                "same ordered shape and one positive exact Fraction scale; "
                "every value checked by cross-product"
            ),
            "temporal_order_type": (
                "same exact weak ordering of every temporal value, ties "
                "included"
            ),
            "run_collapsed_order_type": (
                "collapse only consecutive exact-equal values, then compare "
                "exact weak ordering with ties"
            ),
            "extrema_signature": (
                "ordered local-extrema segments with exact start/end "
                "indices, endpoint magnitudes, direction, and delta"
            ),
            "full_cochlea_order": (
                "topology-major component order, field order "
                "D/M/R/U/C/P/B, then temporal tuple order"
            ),
        },
        "assets": asset_records,
        "pairs": results,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
