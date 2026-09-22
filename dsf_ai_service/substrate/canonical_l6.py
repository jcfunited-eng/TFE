"""Domain-neutral canonical L6 exhaustion law.

L6 decides whether a finite set of structural constraints has collapsed below
the canonical ``n_start / e`` effective-dimension boundary.  This module owns
only that integer decision.  It has no language, Unicode, transcript, chi,
lookup, or sensory-label dependency.
"""

from __future__ import annotations

from dataclasses import dataclass


def _require_nonnegative_integer(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ValueError(f"L6 {label} must be a nonnegative integer")
    return value


def _ceil_dimensions_over_e(dimensions: int) -> int:
    """Return ``ceil(dimensions / e)`` using exact integer arithmetic.

    The alternating factorial expansion of ``1/e`` brackets the value
    strictly:

    ``A_(m + 1) < 1/e < A_m`` for every even ``m``,

    where ``A_r = sum((-1)^j / j!, j=0..r)``.  The recurrence below retains
    each adjacent pair as integer numerators and factorial denominators.  Once
    both scaled bounds have the same floor, that floor is exactly
    ``floor(dimensions / e)``.  For positive integer dimensions, irrationality
    of ``e`` then makes the requested ceiling one greater.
    """
    dimensions = _require_nonnegative_integer(
        dimensions,
        "dimensions",
    )
    if dimensions == 0:
        return 0

    even_index = 0
    upper_numerator = 1
    upper_denominator = 1
    while True:
        odd_index = even_index + 1
        lower_denominator = upper_denominator * odd_index
        lower_numerator = upper_numerator * odd_index - 1

        lower_floor = (
            dimensions * lower_numerator // lower_denominator
        )
        upper_floor = (
            dimensions * upper_numerator // upper_denominator
        )
        if lower_floor == upper_floor:
            return lower_floor + 1

        even_index += 2
        upper_denominator = lower_denominator * even_index
        upper_numerator = lower_numerator * even_index + 1


@dataclass(frozen=True, slots=True)
class L6Direction:
    """One direction of canonical non-null/quiescent exhaustion."""

    dimensions: int
    matching_non_null: int
    matching_quiescent: int
    effective_dimensions: int
    knee: int
    locked: bool


def canonical_l6_direction(
    *,
    dimensions: int,
    matching_non_null: int,
    matching_quiescent: int,
) -> L6Direction:
    """Apply the approved integer form of ``n_eff < n_start / e``."""
    dimensions = _require_nonnegative_integer(dimensions, "dimensions")
    matching_non_null = _require_nonnegative_integer(
        matching_non_null,
        "matching non-null count",
    )
    matching_quiescent = _require_nonnegative_integer(
        matching_quiescent,
        "matching quiescent count",
    )
    collapsed = matching_non_null + matching_quiescent
    if collapsed > dimensions:
        raise ValueError("L6 matching constraints cannot exceed n_start")
    effective = dimensions - collapsed
    knee = _ceil_dimensions_over_e(dimensions)
    return L6Direction(
        dimensions=dimensions,
        matching_non_null=matching_non_null,
        matching_quiescent=matching_quiescent,
        effective_dimensions=effective,
        knee=knee,
        locked=effective < knee,
    )


__all__ = ["L6Direction", "canonical_l6_direction"]
