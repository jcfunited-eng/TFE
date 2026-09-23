"""Exact temporal geometry, independently implemented from retained observations.

This is geometry, not a replacement DSF law or a trading strategy. No legacy
kernel is imported. No field is averaged, normalized, thresholded, or ranked.
Unknown observations remain unknown. There is no interpolated trajectory.

For consecutive observed vectors x[i] at exact times t[i]:
    dt[i] = t[i+1] - t[i]
    dx[i] = x[i+1] - x[i]                         (componentwise)
    time_turn[i,j] = dt[i-1]*dx[i,j] - dt[i]*dx[i-1,j]
    pair_turn[i,j,k] = dx[i-1,j]*dx[i,k] - dx[i-1,k]*dx[i,j]

The turn values are the individual components of the exterior product of two
consecutive time-and-observation edges. They are not summed or replaced by a
norm. Their units are time*coordinate and coordinate*coordinate respectively.
Raw points and both edge operands remain available. In particular, a zero
turn does not mean zero motion: a straight rising path has nonzero edges.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Sequence


Scalar = Fraction | None


def exact(value: int | Decimal | Fraction) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal, Fraction)):
        raise TypeError("supply exact integers, Decimals or Fractions; floats are refused")
    if isinstance(value, Decimal) and not value.is_finite():
        raise ValueError("nonfinite observation")
    return Fraction(value)


def _identity(value: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError("coordinate identities and units must be nonempty explicit strings")
    return value


@dataclass(frozen=True)
class Point:
    time: Fraction
    values: tuple[Scalar, ...]


@dataclass(frozen=True)
class Edge:
    start: int
    end: int
    elapsed: Fraction
    change: tuple[Scalar, ...]


@dataclass(frozen=True)
class PairTurn:
    left: int
    right: int
    oriented_area: Scalar


@dataclass(frozen=True)
class Turn:
    incoming_edge: int
    outgoing_edge: int
    time_coordinate: tuple[Scalar, ...]
    coordinate_pairs: tuple[PairTurn, ...]


@dataclass(frozen=True)
class Geometry:
    coordinate_ids: tuple[str, ...]
    coordinate_units: tuple[str, ...]
    time_unit: str
    points: tuple[Point, ...]
    edges: tuple[Edge, ...]
    turns: tuple[Turn, ...]


def build_geometry(
    *,
    coordinate_ids: Sequence[str],
    coordinate_units: Sequence[str],
    time_unit: str,
    times: Sequence[int | Decimal | Fraction],
    observations: Sequence[Sequence[int | Decimal | Fraction | None]],
    max_geometry_terms: int = 1_000_000,
) -> Geometry:
    """Construct every component, or refuse before expansion exceeds its budget.

    max_geometry_terms bounds allocated derived scalar terms, not a physical
    threshold. No data are truncated when the bound is exceeded. Dates and
    coordinates are never sorted, deduplicated or silently re-aligned here.
    """
    ids = tuple(_identity(v) for v in coordinate_ids)
    units = tuple(_identity(v) for v in coordinate_units)
    time_unit = _identity(time_unit)
    width, count = len(ids), len(times)
    if not width or len(set(ids)) != width or len(units) != width:
        raise ValueError("coordinate identities must be unique and have explicit units")
    if not count or len(observations) != count:
        raise ValueError("nonempty, equally sized times and observations required")
    if isinstance(max_geometry_terms, bool) or not isinstance(max_geometry_terms, int) or max_geometry_terms < 0:
        raise ValueError("geometry resource budget must be a nonnegative integer")
    pair_count = width * (width - 1) // 2
    required = count * width + max(0, count - 1) * width + max(0, count - 2) * (width + pair_count)
    if required > max_geometry_terms:
        raise ValueError(f"geometry needs {required} terms; resource budget is {max_geometry_terms}")

    points = []
    for time, row in zip(times, observations, strict=True):
        if len(row) != width:
            raise ValueError("observation width differs from the declared joint field")
        point = Point(exact(time), tuple(None if value is None else exact(value) for value in row))
        if points and point.time <= points[-1].time:
            raise ValueError("times must be strictly increasing; no implicit reorder")
        points.append(point)

    edges = []
    for index in range(count - 1):
        first, second = points[index], points[index + 1]
        change = tuple(None if a is None or b is None else b - a
                       for a, b in zip(first.values, second.values, strict=True))
        edges.append(Edge(index, index + 1, second.time - first.time, change))

    turns = []
    for index in range(1, len(edges)):
        before, after = edges[index - 1], edges[index]
        time_coordinate = tuple(
            None if a is None or b is None else before.elapsed * b - after.elapsed * a
            for a, b in zip(before.change, after.change, strict=True)
        )
        pairs = []
        for left in range(width):
            for right in range(left + 1, width):
                a, b = before.change[left], before.change[right]
                c, d = after.change[left], after.change[right]
                area = None if any(v is None for v in (a, b, c, d)) else a * d - b * c
                pairs.append(PairTurn(left, right, area))
        turns.append(Turn(index - 1, index, time_coordinate, tuple(pairs)))

    return Geometry(ids, units, time_unit, tuple(points), tuple(edges), tuple(turns))
