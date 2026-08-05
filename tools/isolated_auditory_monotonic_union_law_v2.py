"""Monotonic auditory union over witnessed physical receptor-route time."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from tools.isolated_auditory_physical_episode import (
    CellBasin,
    CellKey,
    Episode,
    TemporalEdge,
    basins,
)


SCHEMA = "guala.audit.auditory_monotonic_union_law.v2"


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


def _fraction_text(value) -> str:
    return f"{value.numerator}/{value.denominator}"


@dataclass(frozen=True, slots=True)
class MonotonicThingUnion:
    thing_id: str
    episode_receipt_sha256s: tuple[str, ...]
    cells: tuple[tuple[CellKey, CellBasin], ...]
    temporal_edges: frozenset[TemporalEdge]
    field_witness_receipt_sha256s: tuple[str, ...]
    temporal_witness_receipt_sha256s: tuple[str, ...]
    authority_receipt_sha256: str

    def cell_map(self) -> dict[CellKey, CellBasin]:
        return dict(self.cells)

    def payload(self) -> dict[str, object]:
        return {
            "cells": [
                {
                    "key": key.record(),
                    "lower": [
                        _fraction_text(value) for value in basin.lower
                    ],
                    "upper": [
                        _fraction_text(value) for value in basin.upper
                    ],
                }
                for key, basin in self.cells
            ],
            "episode_receipt_sha256s": list(
                self.episode_receipt_sha256s
            ),
            "field_witness_receipt_sha256s": list(
                self.field_witness_receipt_sha256s
            ),
            "schema": SCHEMA,
            "temporal_edges": [
                edge.record() for edge in sorted(self.temporal_edges)
            ],
            "temporal_witness_receipt_sha256s": list(
                self.temporal_witness_receipt_sha256s
            ),
            "thing_id": self.thing_id,
        }

    def encoded(self) -> bytes:
        return _canonical(
            self.payload()
            | {
                "authority_receipt_sha256": (
                    self.authority_receipt_sha256
                )
            }
        )


def build_union(
    *,
    thing_id: str,
    episodes: tuple[Episode, ...],
) -> MonotonicThingUnion:
    if not episodes:
        raise ValueError("monotonic union requires lived episodes")
    keys = frozenset(
        key for episode in episodes for key in episode.cells
    )
    cells = tuple(sorted(basins(episodes, keys).items()))
    temporal_edges = frozenset(
        edge
        for episode in episodes
        for edge in episode.temporal_edges
    )
    field_witnesses = tuple(
        sorted(
            {
                receipt
                for episode in episodes
                for receipt in episode.field_witness_receipt_sha256s
            }
        )
    )
    temporal_witnesses = tuple(
        sorted(
            {
                receipt
                for episode in episodes
                for receipt in episode.temporal_witness_receipt_sha256s
            }
        )
    )
    provisional = {
        "cells": [
            {
                "key": key.record(),
                "lower": [
                    _fraction_text(value) for value in basin.lower
                ],
                "upper": [
                    _fraction_text(value) for value in basin.upper
                ],
            }
            for key, basin in cells
        ],
        "episode_receipt_sha256s": [
            value.settlement_receipt_sha256 for value in episodes
        ],
        "field_witness_receipt_sha256s": list(field_witnesses),
        "schema": SCHEMA,
        "temporal_edges": [
            edge.record() for edge in sorted(temporal_edges)
        ],
        "temporal_witness_receipt_sha256s": list(temporal_witnesses),
        "thing_id": thing_id,
    }
    return MonotonicThingUnion(
        thing_id=thing_id,
        episode_receipt_sha256s=tuple(
            value.settlement_receipt_sha256 for value in episodes
        ),
        cells=cells,
        temporal_edges=temporal_edges,
        field_witness_receipt_sha256s=field_witnesses,
        temporal_witness_receipt_sha256s=temporal_witnesses,
        authority_receipt_sha256=_digest(provisional),
    )


def settle_union_query(
    *,
    query: Episode,
    memories: tuple[MonotonicThingUnion, ...],
) -> dict[str, object]:
    if not memories:
        raise ValueError("monotonic union query lacks causal THINGs")
    maps = {
        memory.thing_id: memory.cell_map() for memory in memories
    }
    drive_memberships = tuple(
        frozenset(
            thing_id
            for thing_id, cells in maps.items()
            if drive.key in cells and cells[drive.key].contains(drive)
        )
        for drive in query.drives
    )
    edge_memberships = tuple(
        frozenset(
            memory.thing_id
            for memory in memories
            if edge in memory.temporal_edges
        )
        for edge in sorted(query.temporal_edges)
    )
    memberships = (*drive_memberships, *edge_memberships)
    dimensions = len(memberships)
    relations = []
    locked = []
    for memory in sorted(memories, key=lambda value: value.thing_id):
        non_null = sum(
            memory.thing_id in owners and len(owners) == 1
            for owners in memberships
        )
        quiescent = sum(
            memory.thing_id in owners and len(owners) > 1
            for owners in memberships
        )
        direction = canonical_l6_direction(
            dimensions=dimensions,
            matching_non_null=non_null,
            matching_quiescent=quiescent,
        )
        is_locked = bool(dimensions and direction.locked)
        relations.append(
            {
                "dimensions": dimensions,
                "effective_dimensions": direction.effective_dimensions,
                "knee": direction.knee,
                "locked": is_locked,
                "matching_non_null": non_null,
                "matching_quiescent": quiescent,
                "thing_id": memory.thing_id,
            }
        )
        if is_locked:
            locked.append(memory.thing_id)
    state = (
        "resolved"
        if len(locked) == 1
        else "ambiguous"
        if locked
        else "unknown"
    )
    payload = {
        "locked_thing_ids": locked,
        "query_settlement_receipt_sha256": (
            query.settlement_receipt_sha256
        ),
        "relations": relations,
        "schema": "guala.audit.auditory_monotonic_union_settlement.v2",
        "state": state,
    }
    return payload | {
        "authority_receipt_sha256": _digest(payload),
    }


__all__ = [
    "MonotonicThingUnion",
    "build_union",
    "settle_union_query",
]
