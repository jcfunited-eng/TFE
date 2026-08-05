"""Inventory cumulative exact recurrence in settled auditory L5 evidence.

Every exposure is independently transduced through the unchanged auditory
provider, L0--L4 kernel, and auditory L5.  Recurrence means literal equality
of every D/M/R/U/C/P/B Fraction.  Occurrences retain their complete component,
tuple, source-index, and causal-interval support.  This probe never averages,
ranks, thresholds, templates, or converts fields to trits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from tools.probe_auditory_surrounded_event_recognition import _experience


@dataclass(frozen=True, slots=True)
class Exposure:
    name: str
    category: str
    path: Path


@dataclass(frozen=True, slots=True)
class RowOccurrence:
    exposure_index: int
    exposure_name: str
    component_index: int
    component_id: str
    tuple_index: int
    source_index_start: int
    source_index_end: int
    causal_offset_start: Fraction
    causal_offset_end: Fraction
    causal_interval_start: Fraction
    causal_interval_end: Fraction
    fields: tuple[Fraction, ...]


@dataclass(frozen=True, slots=True)
class FullFieldOccurrence:
    exposure_index: int
    exposure_name: str
    source_index: int
    fields: tuple[Fraction, ...]
    supports: tuple[RowOccurrence, ...]


def _text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _row_key(
    occurrence: RowOccurrence,
) -> tuple[int, str, tuple[Fraction, ...]]:
    return (
        occurrence.component_index,
        occurrence.component_id,
        occurrence.fields,
    )


def _occurrence_record(value: RowOccurrence) -> dict[str, object]:
    return {
        "causal_interval_end": _text(value.causal_interval_end),
        "causal_interval_start": _text(value.causal_interval_start),
        "causal_offset_end": _text(value.causal_offset_end),
        "causal_offset_start": _text(value.causal_offset_start),
        "component_id": value.component_id,
        "component_index": value.component_index,
        "exposure_index": value.exposure_index,
        "exposure_name": value.exposure_name,
        "source_index_end_inclusive": value.source_index_end,
        "source_index_start_inclusive": value.source_index_start,
        "tuple_index": value.tuple_index,
    }


def _row_identity_record(
    key: tuple[int, str, tuple[Fraction, ...]],
) -> dict[str, object]:
    component_index, component_id, fields = key
    return {
        "component_id": component_id,
        "component_index": component_index,
        "fields": [
            [name, _text(value)]
            for name, value in zip(
                DSF_FIELD_ORDER,
                fields,
                strict=True,
            )
        ],
    }


def _support_names(
    occurrences: list[RowOccurrence] | list[FullFieldOccurrence],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        value.exposure_name
        for value in sorted(
            occurrences,
            key=lambda item: item.exposure_index,
        )
    ))


def _support_count(
    occurrences: list[RowOccurrence] | list[FullFieldOccurrence],
) -> int:
    return len(_support_names(occurrences))


def _threshold_counts(
    ledger: dict[object, list[object]],
    exposure_count: int,
) -> dict[str, int]:
    supports = [
        len({
            value.exposure_index
            for value in occurrences
        })
        for occurrences in ledger.values()
    ]
    return {
        str(threshold): sum(
            support >= threshold for support in supports
        )
        for threshold in range(2, exposure_count + 1)
    }


def _ledger_summary(
    ledger: dict[object, list[object]],
    exposure_count: int,
) -> dict[str, object]:
    supports = [
        len({
            value.exposure_index
            for value in occurrences
        })
        for occurrences in ledger.values()
    ]
    return {
        "identity_count": len(ledger),
        "unresolved_support_one": sum(value == 1 for value in supports),
        "recurring_support_at_least": _threshold_counts(
            ledger,
            exposure_count,
        ),
    }


def _prefix_ledger(
    ledger: dict[object, list[object]],
    maximum_exposure_index: int,
) -> dict[object, list[object]]:
    return {
        key: selected
        for key, values in ledger.items()
        if (
            selected := [
                value
                for value in values
                if value.exposure_index <= maximum_exposure_index
            ]
        )
    }


def _component_summary(
    row_ledger: dict[
        tuple[int, str, tuple[Fraction, ...]],
        list[RowOccurrence],
    ],
    exposure_count: int,
) -> list[dict[str, object]]:
    grouped: dict[
        tuple[int, str],
        dict[object, list[object]],
    ] = defaultdict(dict)
    for key, values in row_ledger.items():
        grouped[(key[0], key[1])][key] = values
    return [
        {
            "component_index": component_index,
            "component_id": component_id,
            **_ledger_summary(values, exposure_count),
        }
        for (component_index, component_id), values in sorted(
            grouped.items()
        )
    ]


def _settled_occurrences(
    exposure: Exposure,
    exposure_index: int,
    experience,
) -> tuple[
    tuple[RowOccurrence, ...],
    tuple[FullFieldOccurrence, ...],
]:
    support = mount_auditory_l4_causal_support(experience)
    support.verify(experience)
    rows = tuple(
        RowOccurrence(
            exposure_index=exposure_index,
            exposure_name=exposure.name,
            component_index=component.topology_index,
            component_id=component.substream_id,
            tuple_index=value.tuple_index,
            source_index_start=value.source_index_start,
            source_index_end=value.source_index_end,
            causal_offset_start=value.causal_offset_start,
            causal_offset_end=value.causal_offset_end,
            causal_interval_start=value.causal_interval_start,
            causal_interval_end=value.causal_interval_end,
            fields=tuple(
                field
                for _name, field in value.fields
            ),
        )
        for component in support.components
        for value in component.tuples
    )
    by_component = []
    for component_index in range(len(support.components)):
        component_rows = tuple(
            value
            for value in rows
            if value.component_index == component_index
        )
        by_component.append(component_rows)
    source_count = len(experience.channels[0].pressure.samples)
    full_fields = []
    for source_index in range(source_count):
        active = tuple(
            next(
                value
                for value in component_rows
                if (
                    value.source_index_start
                    <= source_index
                    <= value.source_index_end
                )
            )
            for component_rows in by_component
        )
        full_fields.append(FullFieldOccurrence(
            exposure_index=exposure_index,
            exposure_name=exposure.name,
            source_index=source_index,
            fields=tuple(
                field
                for value in active
                for field in value.fields
            ),
            supports=active,
        ))
    return rows, tuple(full_fields)


def _row_inventory(
    ledger: dict[
        tuple[int, str, tuple[Fraction, ...]],
        list[RowOccurrence],
    ],
) -> list[dict[str, object]]:
    result = []
    for key, values in sorted(
        ledger.items(),
        key=lambda item: (
            item[0][0],
            item[0][1],
            tuple(_text(value) for value in item[0][2]),
        ),
    ):
        identity = _row_identity_record(key)
        result.append({
            "identity_sha256": _digest(identity),
            **identity,
            "exposure_support": list(_support_names(values)),
            "exposure_support_count": _support_count(values),
            "occurrences": [
                _occurrence_record(value)
                for value in sorted(
                    values,
                    key=lambda item: (
                        item.exposure_index,
                        item.tuple_index,
                    ),
                )
            ],
        })
    return result


def _full_inventory(
    ledger: dict[tuple[Fraction, ...], list[FullFieldOccurrence]],
) -> list[dict[str, object]]:
    result = []
    for fields, values in sorted(
        ledger.items(),
        key=lambda item: tuple(_text(value) for value in item[0]),
    ):
        identity_payload = {
            "component_count": 32,
            "field_order": list(DSF_FIELD_ORDER),
            "topology_major_fields": [
                _text(value) for value in fields
            ],
        }
        result.append({
            "identity_sha256": _digest(identity_payload),
            **identity_payload,
            "exposure_support": list(_support_names(values)),
            "exposure_support_count": _support_count(values),
            "occurrences": [
                {
                    "exposure_index": value.exposure_index,
                    "exposure_name": value.exposure_name,
                    "source_index": value.source_index,
                    "component_support": [
                        _occurrence_record(support)
                        for support in value.supports
                    ],
                }
                for value in sorted(
                    values,
                    key=lambda item: (
                        item.exposure_index,
                        item.source_index,
                    ),
                )
            ],
        })
    return result


def _cross_group_support(
    ledger: dict[object, list[object]],
    *,
    related_names: set[str],
    unrelated_names: set[str],
    hello_names: set[str],
) -> dict[str, int]:
    supports = [
        set(_support_names(values))
        for values in ledger.values()
    ]
    recurring_related = [
        value
        for value in supports
        if len(value & related_names) >= 2
    ]
    return {
        "recurring_in_at_least_two_related": len(recurring_related),
        "recurring_related_also_in_unrelated": sum(
            bool(value & unrelated_names)
            for value in recurring_related
        ),
        "present_in_all_three_independent_hello": sum(
            hello_names <= value
            for value in supports
        ),
        "all_three_hello_also_in_unrelated": sum(
            hello_names <= value and bool(value & unrelated_names)
            for value in supports
        ),
        "recurring_only_with_unrelated_additions": sum(
            len(value) >= 2
            and len(value & related_names) < 2
            and bool(value & unrelated_names)
            for value in supports
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exposure",
        action="append",
        nargs=3,
        metavar=("NAME", "CATEGORY", "PATH"),
        required=True,
    )
    args = parser.parse_args()
    exposures = tuple(
        Exposure(name, category, Path(path))
        for name, category, path in args.exposure
    )
    if len({value.name for value in exposures}) != len(exposures):
        raise SystemExit("exposure names must be unique")
    for exposure in exposures:
        if not exposure.path.is_file():
            raise SystemExit(f"exposure is absent: {exposure.path}")

    executor = start_exact_field_executor()
    executor.assert_healthy()
    owner = AuditoryL5Owner(log_event=lambda *_args, **_kwargs: None)
    try:
        traced = tuple(
            (
                exposure,
                *_experience(exposure.path, index, owner),
            )
            for index, exposure in enumerate(exposures)
        )
    finally:
        stop_exact_field_executor()

    row_ledger: dict[
        tuple[int, str, tuple[Fraction, ...]],
        list[RowOccurrence],
    ] = defaultdict(list)
    full_ledger: dict[
        tuple[Fraction, ...],
        list[FullFieldOccurrence],
    ] = defaultdict(list)
    exposure_records = []
    for index, (exposure, experience, report) in enumerate(traced):
        rows, full_rows = _settled_occurrences(
            exposure,
            index,
            experience,
        )
        for value in rows:
            row_ledger[_row_key(value)].append(value)
        for value in full_rows:
            full_ledger[value.fields].append(value)
        exposure_records.append({
            "category": exposure.category,
            "component_row_occurrences": len(rows),
            "full_field_hop_occurrences": len(full_rows),
            "index": index,
            "name": exposure.name,
            "path": str(exposure.path.resolve()),
            "source_sha256": hashlib.sha256(
                exposure.path.read_bytes()
            ).hexdigest(),
            **report,
        })

    cumulative = []
    prior_row_recurring: set[object] = set()
    prior_full_recurring: set[object] = set()
    for index, exposure in enumerate(exposures):
        rows = _prefix_ledger(row_ledger, index)
        full = _prefix_ledger(full_ledger, index)
        row_recurring = {
            key
            for key, values in rows.items()
            if _support_count(values) >= 2
        }
        full_recurring = {
            key
            for key, values in full.items()
            if _support_count(values) >= 2
        }
        cumulative.append({
            "after_exposure_index": index,
            "after_exposure_name": exposure.name,
            "component_rows": _ledger_summary(rows, index + 1),
            "full_cochlea_rows": _ledger_summary(full, index + 1),
            "new_component_rows_reaching_support_two": len(
                row_recurring - prior_row_recurring
            ),
            "new_full_rows_reaching_support_two": len(
                full_recurring - prior_full_recurring
            ),
        })
        prior_row_recurring = row_recurring
        prior_full_recurring = full_recurring

    related_names = {
        value.name
        for value in exposures
        if value.category != "unrelated_phrase"
    }
    unrelated_names = {
        value.name
        for value in exposures
        if value.category == "unrelated_phrase"
    }
    hello_names = {
        value.name
        for value in exposures
        if value.category == "independent_hello"
    }
    print(json.dumps({
        "schema": "guala.audit.auditory_cumulative_exact_recurrence.v1",
        "method": {
            "component_row_identity": (
                "component topology plus all ordered exact "
                "D/M/R/U/C/P/B Fractions"
            ),
            "full_cochlea_row_identity": (
                "simultaneous topology-major 32x7 exact field row at one "
                "source hop"
            ),
            "occurrence_support": (
                "every original tuple, inclusive source interval, relative "
                "causal offset, and absolute causal interval is retained"
            ),
            "recurrence": (
                "identity appears in distinct exposures; repeated tuples "
                "inside one exposure do not increase exposure support"
            ),
            "forbidden_reductions": [
                "averages",
                "templates",
                "thresholds",
                "trits",
                "rank-order proxies",
                "scores",
            ],
        },
        "exposures": exposure_records,
        "cumulative": cumulative,
        "final_component_rows": {
            **_ledger_summary(row_ledger, len(exposures)),
            "per_component": _component_summary(
                row_ledger,
                len(exposures),
            ),
            "cross_group_support": _cross_group_support(
                row_ledger,
                related_names=related_names,
                unrelated_names=unrelated_names,
                hello_names=hello_names,
            ),
        },
        "final_full_cochlea_rows": {
            **_ledger_summary(full_ledger, len(exposures)),
            "cross_group_support": _cross_group_support(
                full_ledger,
                related_names=related_names,
                unrelated_names=unrelated_names,
                hello_names=hello_names,
            ),
        },
        "l6_n_effective": {
            "derivable": False,
            "reason": (
                "recurring DSF state rows are primal observations, not "
                "provider-native constraint covectors; the evidence supplies "
                "no receipted physical perturbation coordinates, seven-by-"
                "perturbation tangent, or exact left-nullspace annihilation "
                "proof required before a lawful fixed-42 rank and n_effective "
                "can be formed"
            ),
            "rank_computed_from_observed_rows": False,
        },
        "component_row_inventory": _row_inventory(row_ledger),
        "full_cochlea_row_inventory": _full_inventory(full_ledger),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
