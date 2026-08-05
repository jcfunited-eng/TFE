from fractions import Fraction

from tools.probe_w1_causal_run_envelope_walkup import (
    LaneRunBasin,
    _runs,
)


def test_grounded_experience_expands_exact_run_envelope() -> None:
    basin = LaneRunBasin.create()
    first = _runs(
        (
            Fraction(0),
            Fraction(1),
            Fraction(2),
            Fraction(1),
        ),
        (Fraction(1, 10),) * 4,
    )
    second = _runs(
        (
            Fraction(0),
            Fraction(2),
            Fraction(3),
            Fraction(1),
        ),
        (Fraction(1, 5),) * 4,
    )
    between = _runs(
        (
            Fraction(0),
            Fraction(3, 2),
            Fraction(5, 2),
            Fraction(1),
        ),
        (Fraction(3, 20),) * 4,
    )

    basin.grow(first)
    assert basin.contains(first)
    assert not basin.contains(second)

    basin.grow(second)
    assert basin.contains(first)
    assert basin.contains(second)
    assert basin.contains(between)


def test_run_order_and_learned_tempo_are_required() -> None:
    basin = LaneRunBasin.create()
    learned = _runs(
        (
            Fraction(0),
            Fraction(1),
            Fraction(2),
            Fraction(1),
        ),
        (Fraction(1, 10),) * 4,
    )
    wrong_order = _runs(
        (
            Fraction(2),
            Fraction(1),
            Fraction(0),
            Fraction(1),
        ),
        (Fraction(1, 10),) * 4,
    )
    outside_tempo = _runs(
        (
            Fraction(0),
            Fraction(1),
            Fraction(2),
            Fraction(1),
        ),
        (Fraction(1),) * 4,
    )

    basin.grow(learned)

    assert not basin.contains(wrong_order)
    assert not basin.contains(outside_tempo)
