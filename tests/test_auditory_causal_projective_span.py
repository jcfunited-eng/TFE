from fractions import Fraction

from tools.probe_auditory_causal_projective_span import (
    PROOF_PRIMES,
    FullFieldCoordinate,
    _ModularRowBasis,
    _residue,
)


def _coordinate(index: int) -> FullFieldCoordinate:
    return FullFieldCoordinate(
        ear_id="left",
        cochlear_index=0,
        source_index=index,
        component_kind="pressure",
        field_name="D_k",
    )


def test_modular_rank_witness_proves_augmented_nonmembership() -> None:
    prime = PROOF_PRIMES[0]
    references = _ModularRowBasis(width=2, prime=prime)
    augmented = _ModularRowBasis(width=3, prime=prime)
    rows = (
        (Fraction(1), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1), Fraction(0)),
        (Fraction(1), Fraction(1), Fraction(1)),
    )
    for index, row in enumerate(rows):
        references.admit(
            tuple(_residue(value, prime) for value in row[:2]),
            _coordinate(index),
        )
        augmented.admit(
            tuple(_residue(value, prime) for value in row),
            _coordinate(index),
        )
    assert references.rank == 2
    assert augmented.rank == 3


def test_modular_rank_does_not_invent_difference_inside_span() -> None:
    prime = PROOF_PRIMES[1]
    references = _ModularRowBasis(width=2, prime=prime)
    augmented = _ModularRowBasis(width=3, prime=prime)
    rows = (
        (Fraction(1, 3), Fraction(0), Fraction(2, 3)),
        (Fraction(0), Fraction(1, 5), Fraction(1, 5)),
        (Fraction(2, 3), Fraction(3, 5), Fraction(29, 15)),
    )
    for index, row in enumerate(rows):
        references.admit(
            tuple(_residue(value, prime) for value in row[:2]),
            _coordinate(index),
        )
        augmented.admit(
            tuple(_residue(value, prime) for value in row),
            _coordinate(index),
        )
    assert references.rank == 2
    assert augmented.rank == 2


def test_fraction_residue_preserves_exact_field_arithmetic() -> None:
    prime = PROOF_PRIMES[0]
    left = Fraction(17, 31)
    right = Fraction(-5, 19)
    assert _residue(left + right, prime) == (
        _residue(left, prime) + _residue(right, prime)
    ) % prime
    assert _residue(left * right, prime) == (
        _residue(left, prime) * _residue(right, prime)
    ) % prime
