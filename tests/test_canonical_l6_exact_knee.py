from fractions import Fraction
from math import factorial

import pytest

from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from dsf_ai_service.substrate.language_fact_strand import (
    canonical_l6_direction as language_canonical_l6_direction,
)


@pytest.mark.parametrize(
    ("dimensions", "expected_knee"),
    (
        (0, 0),
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 2),
        (5, 2),
        (6, 3),
        (8, 3),
        (9, 4),
    ),
)
def test_exact_knee_small_values(
    dimensions: int,
    expected_knee: int,
) -> None:
    direction = canonical_l6_direction(
        dimensions=dimensions,
        matching_non_null=0,
        matching_quiescent=0,
    )

    assert direction.knee == expected_knee


def test_exact_knee_rejects_negative_dimensions() -> None:
    with pytest.raises(ValueError, match="nonnegative integer"):
        canonical_l6_direction(
            dimensions=-1,
            matching_non_null=0,
            matching_quiescent=0,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("dimensions", True),
        ("dimensions", 1.0),
        ("matching_non_null", False),
        ("matching_non_null", 1.0),
        ("matching_quiescent", True),
        ("matching_quiescent", 1.0),
    ),
)
def test_exact_l6_rejects_noninteger_counts(
    field: str,
    value: object,
) -> None:
    arguments = {
        "dimensions": 1,
        "matching_non_null": 0,
        "matching_quiescent": 0,
    }
    arguments[field] = value

    with pytest.raises(ValueError, match="nonnegative integer"):
        canonical_l6_direction(**arguments)


def test_language_strand_delegates_to_canonical_l6() -> None:
    assert language_canonical_l6_direction is canonical_l6_direction


def test_exact_knee_64_bit_regression_has_independent_certificate() -> None:
    dimensions = 2**63 - 1
    expected_knee = 3_393_088_950_634_442_637
    direction = canonical_l6_direction(
        dimensions=dimensions,
        matching_non_null=0,
        matching_quiescent=0,
    )

    assert direction.knee == expected_knee

    terms = 64
    lower_e = sum(
        (Fraction(1, factorial(index)) for index in range(terms + 1)),
        start=Fraction(0),
    )
    upper_e = lower_e + Fraction(1, terms * factorial(terms))

    assert Fraction(expected_knee - 1) * upper_e < dimensions
    assert Fraction(expected_knee) * lower_e > dimensions


def test_exact_knee_preserves_strict_lock_inequality() -> None:
    dimensions = 2**63 - 1
    knee = 3_393_088_950_634_442_637

    at_knee = canonical_l6_direction(
        dimensions=dimensions,
        matching_non_null=dimensions - knee,
        matching_quiescent=0,
    )
    below_knee = canonical_l6_direction(
        dimensions=dimensions,
        matching_non_null=dimensions - knee + 1,
        matching_quiescent=0,
    )

    assert at_knee.effective_dimensions == knee
    assert at_knee.locked is False
    assert below_knee.effective_dimensions == knee - 1
    assert below_knee.locked is True
