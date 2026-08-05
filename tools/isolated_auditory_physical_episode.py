"""Physical full-field auditory episodes with witnessed per-route time edges."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
)


SCHEMA = "guala.audit.auditory_physical_episode.v1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _direction(value: Fraction) -> int:
    return (value > 0) - (value < 0)


@dataclass(frozen=True, order=True, slots=True)
class CellKey:
    ear_id: str
    cochlear_index: int
    component_kind: str
    field_directions: tuple[int, ...]

    def record(self) -> list[object]:
        return [
            self.ear_id,
            self.cochlear_index,
            self.component_kind,
            list(self.field_directions),
        ]


@dataclass(frozen=True, slots=True)
class LocalDrive:
    key: CellKey
    source_index_start: int
    source_index_end: int
    source_time_start: Fraction
    source_time_end: Fraction
    start_occurrence_receipt_sha256: str
    end_occurrence_receipt_sha256: str
    values: tuple[Fraction, ...]


@dataclass(frozen=True, order=True, slots=True)
class TemporalEdge:
    left: CellKey
    right: CellKey

    def __post_init__(self) -> None:
        if (
            self.left.ear_id != self.right.ear_id
            or self.left.cochlear_index != self.right.cochlear_index
            or self.left.component_kind != self.right.component_kind
        ):
            raise ValueError("temporal edge crossed a physical receptor route")

    def record(self) -> list[object]:
        return [self.left.record(), self.right.record()]


@dataclass(frozen=True, slots=True)
class Episode:
    settlement_receipt_sha256: str
    drives: tuple[LocalDrive, ...]
    cells: frozenset[CellKey]
    temporal_edges: frozenset[TemporalEdge]
    field_witness_receipt_sha256s: tuple[str, ...]
    temporal_witness_receipt_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CellBasin:
    key: CellKey
    lower: tuple[Fraction, ...]
    upper: tuple[Fraction, ...]

    def contains(self, drive: LocalDrive) -> bool:
        return (
            drive.key == self.key
            and all(
                low <= value <= high
                for low, value, high in zip(
                    self.lower,
                    drive.values,
                    self.upper,
                    strict=True,
                )
            )
        )


def _field_values(occurrence, kind: str) -> tuple[Fraction, ...]:
    fields = (
        occurrence.pressure_fields
        if kind == "pressure"
        else occurrence.phase_fields
    )
    if tuple(name for name, _value in fields) != DSF_FIELD_ORDER:
        raise ValueError("auditory episode flattened or reordered DSF")
    return tuple(value for _name, value in fields)


def _drive(*, ear_id: str, channel: int, kind: str, prior, current) -> LocalDrive:
    if current.source_index <= prior.source_index:
        raise ValueError("auditory route did not advance in physical time")
    duration = current.source_time - prior.source_time
    if duration <= 0:
        raise ValueError("auditory route did not advance in source time")
    left = _field_values(prior, kind)
    right = _field_values(current, kind)
    delta = tuple(
        after - before
        for before, after in zip(left, right, strict=True)
    )
    return LocalDrive(
        key=CellKey(
            ear_id=ear_id,
            cochlear_index=channel,
            component_kind=kind,
            field_directions=tuple(_direction(value) for value in delta),
        ),
        source_index_start=prior.source_index,
        source_index_end=current.source_index,
        source_time_start=prior.source_time,
        source_time_end=current.source_time,
        start_occurrence_receipt_sha256=prior.authority_receipt_sha256,
        end_occurrence_receipt_sha256=current.authority_receipt_sha256,
        values=(*left, *right, duration),
    )


def _temporal_witness(left: LocalDrive, right: LocalDrive) -> str:
    if (
        left.key.ear_id != right.key.ear_id
        or left.key.cochlear_index != right.key.cochlear_index
        or left.key.component_kind != right.key.component_kind
        or left.source_index_end != right.source_index_start
        or left.source_time_end != right.source_time_start
        or left.end_occurrence_receipt_sha256
        != right.start_occurrence_receipt_sha256
    ):
        raise ValueError("auditory edge lacks a shared physical occurrence")
    return _digest(
        {
            "component_kind": left.key.component_kind,
            "ear_id": left.key.ear_id,
            "left": left.key.record(),
            "right": right.key.record(),
            "schema": "guala.audit.auditory_temporal_witness.v1",
            "shared_occurrence_receipt_sha256": (
                left.end_occurrence_receipt_sha256
            ),
            "shared_source_index": left.source_index_end,
            "shared_source_time": (
                f"{left.source_time_end.numerator}/"
                f"{left.source_time_end.denominator}"
            ),
        }
    )


def episode_from_settlement(
    settlement: W1BinauralReceptorSettlement,
) -> Episode:
    settlement.verify()
    drives: list[LocalDrive] = []
    edges: set[TemporalEdge] = set()
    field_witnesses: set[str] = set()
    temporal_witnesses: set[str] = set()
    for ear in settlement.ears:
        for channel in range(16):
            occurrences = tuple(
                value
                for value in ear.experience.occurrences
                if value.receptor.cochlear_index == channel
            )
            if any(
                right.source_index <= left.source_index
                for left, right in zip(occurrences, occurrences[1:])
            ):
                raise ValueError("auditory channel occurrence order changed")
            for occurrence in occurrences:
                field_witnesses.update(
                    (
                        occurrence.pressure_field_receipt_sha256,
                        occurrence.phase_field_receipt_sha256,
                    )
                )
            for kind in ("pressure", "phase"):
                route = tuple(
                    _drive(
                        ear_id=ear.ear_id,
                        channel=channel,
                        kind=kind,
                        prior=prior,
                        current=current,
                    )
                    for prior, current in zip(
                        occurrences,
                        occurrences[1:],
                    )
                )
                drives.extend(route)
                for left, right in zip(route, route[1:]):
                    edges.add(TemporalEdge(left.key, right.key))
                    temporal_witnesses.add(_temporal_witness(left, right))
    ordered_drives = tuple(
        sorted(
            drives,
            key=lambda value: (
                value.key.ear_id,
                value.key.cochlear_index,
                value.key.component_kind,
                value.source_index_start,
                value.source_index_end,
                value.key.field_directions,
            ),
        )
    )
    return Episode(
        settlement_receipt_sha256=settlement.authority_receipt_sha256,
        drives=ordered_drives,
        cells=frozenset(value.key for value in ordered_drives),
        temporal_edges=frozenset(edges),
        field_witness_receipt_sha256s=tuple(sorted(field_witnesses)),
        temporal_witness_receipt_sha256s=tuple(sorted(temporal_witnesses)),
    )


def basins(
    episodes: tuple[Episode, ...],
    cells: frozenset[CellKey],
) -> dict[CellKey, CellBasin]:
    result = {}
    for key in cells:
        values = tuple(
            drive.values
            for episode in episodes
            for drive in episode.drives
            if drive.key == key
        )
        if not values:
            raise ValueError("auditory cell lacks physical drives")
        result[key] = CellBasin(
            key=key,
            lower=tuple(min(column) for column in zip(*values, strict=True)),
            upper=tuple(max(column) for column in zip(*values, strict=True)),
        )
    return result


__all__ = [
    "CellBasin",
    "CellKey",
    "Episode",
    "LocalDrive",
    "TemporalEdge",
    "basins",
    "episode_from_settlement",
]
