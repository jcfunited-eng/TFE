"""Monotonic causal-THING union law for local auditory interval neurons."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from tools.probe_auditory_thing_local_interval_mosaic import (
    CellBasin,
    CellKey,
    Episode,
    _basins,
)


SCHEMA = "guala.audit.auditory_monotonic_union_law.v1"


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
    edges: frozenset[tuple[CellKey, CellKey]]
    witness_receipt_sha256s: tuple[str, ...]
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
            "edges": [
                [left.record(), right.record()]
                for left, right in sorted(self.edges)
            ],
            "episode_receipt_sha256s": list(
                self.episode_receipt_sha256s
            ),
            "schema": SCHEMA,
            "thing_id": self.thing_id,
            "witness_receipt_sha256s": list(
                self.witness_receipt_sha256s
            ),
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
    cells = tuple(sorted(_basins(episodes, keys).items()))
    edges = frozenset(
        edge for episode in episodes for edge in episode.edges
    )
    witnesses = tuple(sorted({
        receipt
        for episode in episodes
        for receipt in episode.witness_receipt_sha256s
    }))
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
        "edges": [
            [left.record(), right.record()]
            for left, right in sorted(edges)
        ],
        "episode_receipt_sha256s": [
            value.settlement_receipt_sha256 for value in episodes
        ],
        "schema": SCHEMA,
        "thing_id": thing_id,
        "witness_receipt_sha256s": list(witnesses),
    }
    return MonotonicThingUnion(
        thing_id=thing_id,
        episode_receipt_sha256s=tuple(
            value.settlement_receipt_sha256 for value in episodes
        ),
        cells=cells,
        edges=edges,
        witness_receipt_sha256s=witnesses,
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
    drive_memberships = []
    for drive in query.drives:
        drive_memberships.append(frozenset(
            thing_id
            for thing_id, cells in maps.items()
            if drive.key in cells and cells[drive.key].contains(drive)
        ))
    edge_memberships = []
    for edge in sorted(query.edges):
        edge_memberships.append(frozenset(
            memory.thing_id
            for memory in memories
            if edge in memory.edges
        ))
    dimensions = len(drive_memberships) + len(edge_memberships)
    relations = []
    locked = []
    for memory in sorted(memories, key=lambda value: value.thing_id):
        memberships = (*drive_memberships, *edge_memberships)
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
        relations.append({
            "dimensions": dimensions,
            "effective_dimensions": direction.effective_dimensions,
            "knee": direction.knee,
            "locked": is_locked,
            "matching_non_null": non_null,
            "matching_quiescent": quiescent,
            "thing_id": memory.thing_id,
        })
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
        "schema": "guala.audit.auditory_monotonic_union_settlement.v1",
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
