"""Exact rigid rotation projected onto W1's one-millimetre body lattice.

The body retains heading in integer millidegrees while the world retains
positions in integer millimetres.  A body-fixed receptor therefore has one
continuous rigid-body position and one nearest lattice position.  This module
proves that lattice position with rational interval arithmetic; binary
floating point never has authority over the selected millimetre.
"""

from __future__ import annotations

from fractions import Fraction
from math import factorial


_FULL_TURN_MILLIDEGREES = 360_000
_QUARTER_TURN_MILLIDEGREES = 90_000
_HALF_TURN_MILLIDEGREES = 180_000

# Machin's identity converges geometrically.  The same finite proof depth
# encloses pi and bounds the sine/cosine remainder; it is numerical proof
# precision, not sensory anatomy, a tolerance, or a behavioral threshold.
_PROOF_TERMS = 80

_Interval = tuple[Fraction, Fraction]


def _arctangent_reciprocal_bounds(
    inverse: int,
) -> _Interval:
    total = Fraction(0)
    for index in range(_PROOF_TERMS):
        term = Fraction(1, (2 * index + 1) * inverse ** (2 * index + 1))
        total = total - term if index % 2 else total + term
    index = _PROOF_TERMS
    next_term = Fraction(
        1,
        (2 * index + 1) * inverse ** (2 * index + 1),
    )
    successor = total - next_term if index % 2 else total + next_term
    return min(total, successor), max(total, successor)


_ATAN_FIFTH = _arctangent_reciprocal_bounds(5)
_ATAN_239TH = _arctangent_reciprocal_bounds(239)
_PI_BOUNDS = (
    4 * (4 * _ATAN_FIFTH[0] - _ATAN_239TH[1]),
    4 * (4 * _ATAN_FIFTH[1] - _ATAN_239TH[0]),
)


def _negate(value: _Interval) -> _Interval:
    return -value[1], -value[0]


def _add(left: _Interval, right: _Interval) -> _Interval:
    return left[0] + right[0], left[1] + right[1]


def _integer_scale(value: _Interval, multiplier: int) -> _Interval:
    if multiplier >= 0:
        return value[0] * multiplier, value[1] * multiplier
    return value[1] * multiplier, value[0] * multiplier


def _nearest_integer(value: Fraction) -> int:
    if value < 0:
        return -_nearest_integer(-value)
    shifted = value + Fraction(1, 2)
    return shifted.numerator // shifted.denominator


def _sine_cosine_bounds(
    first_quadrant_millidegrees: int,
    term_count: int,
) -> tuple[_Interval, _Interval]:
    scale = Fraction(
        first_quadrant_millidegrees,
        _HALF_TURN_MILLIDEGREES,
    )
    angle = _PI_BOUNDS[0] * scale, _PI_BOUNDS[1] * scale
    sine_low = Fraction(0)
    sine_high = Fraction(0)
    cosine_low = Fraction(0)
    cosine_high = Fraction(0)
    for index in range(term_count):
        sine_power = 2 * index + 1
        sine_term = (
            angle[0] ** sine_power / factorial(sine_power),
            angle[1] ** sine_power / factorial(sine_power),
        )
        cosine_power = 2 * index
        cosine_term = (
            angle[0] ** cosine_power / factorial(cosine_power),
            angle[1] ** cosine_power / factorial(cosine_power),
        )
        if index % 2:
            sine_low -= sine_term[1]
            sine_high -= sine_term[0]
            cosine_low -= cosine_term[1]
            cosine_high -= cosine_term[0]
        else:
            sine_low += sine_term[0]
            sine_high += sine_term[1]
            cosine_low += cosine_term[0]
            cosine_high += cosine_term[1]
    sine_remainder_power = 2 * term_count
    sine_remainder = (
        angle[1] ** sine_remainder_power
        / factorial(sine_remainder_power)
    )
    cosine_remainder_power = 2 * term_count - 1
    cosine_remainder = (
        angle[1] ** cosine_remainder_power
        / factorial(cosine_remainder_power)
    )
    return (
        (sine_low - sine_remainder, sine_high + sine_remainder),
        (cosine_low - cosine_remainder, cosine_high + cosine_remainder),
    )


def _quadrant_bounds(
    heading_millidegrees: int,
    term_count: int,
) -> tuple[_Interval, _Interval]:
    quadrant, remainder = divmod(
        heading_millidegrees,
        _QUARTER_TURN_MILLIDEGREES,
    )
    sine, cosine = _sine_cosine_bounds(remainder, term_count)
    if quadrant == 0:
        return sine, cosine
    if quadrant == 1:
        return cosine, _negate(sine)
    if quadrant == 2:
        return _negate(sine), _negate(cosine)
    return _negate(cosine), sine


def rotate_lattice_offset(
    x_millimetres: int,
    y_millimetres: int,
    heading_millidegrees: int,
) -> tuple[int, int]:
    """Return the uniquely proved nearest 1-mm rigid-body position.

    Half-millimetre ties, if one were ever reached, settle away from zero.
    The rational enclosures must prove the same integer before it is returned;
    otherwise the bounded proof depth refuses rather than guessing.
    """

    for value, name in (
        (x_millimetres, "body-fixed x offset"),
        (y_millimetres, "body-fixed y offset"),
        (heading_millidegrees, "body heading"),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an exact integer")
    if not 0 <= heading_millidegrees < _FULL_TURN_MILLIDEGREES:
        raise ValueError("body heading left the millidegree circle")
    if heading_millidegrees % _QUARTER_TURN_MILLIDEGREES == 0:
        quarter_turns = heading_millidegrees // _QUARTER_TURN_MILLIDEGREES
        if quarter_turns == 0:
            return x_millimetres, y_millimetres
        if quarter_turns == 1:
            return -y_millimetres, x_millimetres
        if quarter_turns == 2:
            return -x_millimetres, -y_millimetres
        return y_millimetres, -x_millimetres

    for term_count in range(6, _PROOF_TERMS + 1):
        sine, cosine = _quadrant_bounds(
            heading_millidegrees,
            term_count,
        )
        rotated_x = _add(
            _integer_scale(cosine, x_millimetres),
            _integer_scale(sine, -y_millimetres),
        )
        rotated_y = _add(
            _integer_scale(sine, x_millimetres),
            _integer_scale(cosine, y_millimetres),
        )
        x_bounds = (
            _nearest_integer(rotated_x[0]),
            _nearest_integer(rotated_x[1]),
        )
        y_bounds = (
            _nearest_integer(rotated_y[0]),
            _nearest_integer(rotated_y[1]),
        )
        if x_bounds[0] == x_bounds[1] and y_bounds[0] == y_bounds[1]:
            return x_bounds[0], y_bounds[0]
    raise ValueError(
        "body-fixed receptor rotation did not prove one millimetre lattice position"
    )


__all__ = ["rotate_lattice_offset"]
