from decimal import Decimal
from fractions import Fraction as Q

import pytest

from tools.tfe_exact_geometry import build_geometry


def geometry(rows, times=None, **kwargs):
    return build_geometry(coordinate_ids=tuple(f"x{i}" for i in range(len(rows[0]))),
                          coordinate_units=("u",) * len(rows[0]), time_unit="s",
                          times=times if times is not None else range(len(rows)),
                          observations=rows, **kwargs)


def test_common_rise_and_fall_is_not_constant_or_zero_motion():
    flat = geometry([(1, 2), (1, 2), (1, 2)])
    changing = geometry([(1, 2), (2, 4), (1, 2)])
    assert changing.edges[0].change == (1, 2)
    assert changing.edges[1].change == (-1, -2)
    assert changing.turns[0].time_coordinate == (-2, -4)
    assert changing.edges != flat.edges
    assert changing.turns != flat.turns


def test_original_sequence_reconstructs_exactly_from_first_point_and_edges():
    rows = [(Decimal('0.1'), Q(2, 7)), (Decimal('0.3'), Q(1, 3)), (Decimal('-0.9'), Q(-4, 11))]
    result = geometry(rows, times=[Q(1, 7), Q(2, 7), Q(9, 7)])
    reconstructed = [result.points[0].values]
    for edge in result.edges:
        reconstructed.append(tuple(a + delta for a, delta in zip(reconstructed[-1], edge.change)))
    assert tuple(reconstructed) == tuple(point.values for point in result.points)
    assert result.edges[0].change[0] == Q(1, 5)


def test_prefix_geometry_does_not_change_when_future_input_arrives():
    prefix = geometry([(1, 2), (3, 1), (2, 4)])
    extended = geometry([(1, 2), (3, 1), (2, 4), (-1000, 999)])
    assert extended.points[:3] == prefix.points
    assert extended.edges[:2] == prefix.edges
    assert extended.turns[:1] == prefix.turns


def test_actual_time_changes_turn_and_straight_motion_remains_visible():
    straight = geometry([(0,), (1,), (3,)], times=[0, 1, 3])
    bent = geometry([(0,), (1,), (3,)], times=[0, 1, 2])
    assert straight.turns[0].time_coordinate == (0,)
    assert tuple(e.change for e in straight.edges) == ((1,), (2,))
    assert bent.turns[0].time_coordinate == (1,)


def test_every_coordinate_pair_is_retained_with_orientation():
    result = geometry([(0, 0, 0), (1, 2, 3), (3, 1, 7)])
    assert [(p.left, p.right, p.oriented_area) for p in result.turns[0].coordinate_pairs] == [
        (0, 1, -5), (0, 2, -2), (1, 2, 11)]
    swapped = geometry([(0, 0), (2, 1), (1, 3)])
    assert swapped.turns[0].coordinate_pairs[0].oriented_area == 5


def test_missing_observation_is_not_zero_or_interpolated():
    result = geometry([(1, 1), (None, 2), (3, 4)])
    assert result.points[1].values == (None, 2)
    assert result.edges[0].change == (None, 1)
    assert result.turns[0].time_coordinate == (None, 1)
    assert result.turns[0].coordinate_pairs[0].oriented_area is None


@pytest.mark.parametrize('rows,times,error', [
    ([(1,), (2,)], [0, 0], ValueError),
    ([(1,), (2,)], [2, 1], ValueError),
    ([(1,), (2, 3)], [0, 1], ValueError),
    ([(1,), (0.1,)], [0, 1], TypeError),
    ([(1,), (True,)], [0, 1], TypeError),
    ([(1,), (Decimal('NaN'),)], [0, 1], ValueError),
])
def test_invalid_inputs_are_refused(rows, times, error):
    with pytest.raises(error):
        geometry(rows, times)


def test_resource_bound_refuses_instead_of_truncating():
    with pytest.raises(ValueError, match='resource budget'):
        geometry([(1, 2), (3, 4), (5, 6)], max_geometry_terms=12)


def test_initial_observation_does_not_invent_derivatives():
    result = geometry([(1, 2)])
    assert result.edges == ()
    assert result.turns == ()
