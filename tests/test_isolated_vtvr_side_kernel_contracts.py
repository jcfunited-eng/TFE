"""
Domain-free walk-up contracts for the NON-CANONICAL VTVR side kernel.

These mirror the four walk-up validations of the Guala "UF Side Kernel
VTVR v2" spec in the spec's own domain-agnostic terms: abstract vertices,
exact rational observations, causal delay between vertex subsets. No
domain vocabulary appears anywhere in this file. The market-flavored
fixtures live separately in test_isolated_vtvr_side_kernel_market_adapter
as adapter-level regressions.

Run: python -m pytest tests/test_isolated_vtvr_side_kernel_contracts.py -q
"""

from fractions import Fraction as F

import pytest

from tools.isolated_vtvr_side_kernel import (
    dimensionalize,
    form_event,
    run_experience,
)

VERTICES = ["v1", "v2", "v3", "v4"]
TIMES = [F(0), F(1), F(2), F(3), F(6), F(7)]  # one 3-unit causal gap
FIELD_A = [
    [F(10, 1), F(5, 1), F(2, 1), F(1, 1)],
    [F(101, 10), F(5, 1), F(19, 10), F(1, 1)],
    [F(103, 10), F(49, 10), F(19, 10), F(11, 10)],
    [F(102, 10), F(51, 10), F(2, 1), F(11, 10)],
    [F(105, 10), F(52, 10), F(21, 10), F(12, 10)],
    [F(104, 10), F(53, 10), F(22, 10), F(12, 10)],
]
FIELD_B = [
    [F(10, 1), F(5, 1), F(2, 1), F(1, 1)],
    [F(99, 10), F(51, 10), F(21, 10), F(9, 10)],
    [F(97, 10), F(53, 10), F(22, 10), F(9, 10)],
    [F(98, 10), F(52, 10), F(21, 10), F(8, 10)],
    [F(95, 10), F(54, 10), F(23, 10), F(8, 10)],
    [F(96, 10), F(55, 10), F(24, 10), F(7, 10)],
]


def test_1_joint_field_and_determinism():
    e1 = run_experience(VERTICES, TIMES, FIELD_A)
    e2 = run_experience(VERTICES, TIMES, FIELD_A)
    assert e1.h_layers == e2.h_layers
    assert e1.h_experience == e2.h_experience
    m, n = len(TIMES), len(VERTICES)
    assert all(len(row) == n for row in e1.l0.xhat) and len(e1.l0.xhat) == m
    assert all(len(row) == n * (n - 1) // 2 for row in e1.l0.relations)
    assert len(e1.l4.cohesion) == m
    assert e1.l4.availability[0][0] == "genesis"
    assert e1.l4.availability[1][0] == "observed"


def test_2_common_positive_gain_quotient():
    scaled = [[v * 7 for v in row] for row in FIELD_A]
    f1 = dimensionalize(VERTICES, TIMES, FIELD_A)
    f2 = dimensionalize(VERTICES, TIMES, scaled)
    assert f1.h_raw != f2.h_raw
    assert form_event(f1).h_vtvr == form_event(f2).h_vtvr


def test_3_causal_delay_between_vertex_subsets():
    delayed = []
    for k in range(len(TIMES)):
        row = list(FIELD_A[k])
        src = FIELD_A[max(0, k - 1)]
        row[2], row[3] = src[2], src[3]
        delayed.append(row)
    e_base = form_event(dimensionalize(VERTICES, TIMES, FIELD_A))
    e_del = form_event(dimensionalize(VERTICES, TIMES, delayed))
    assert e_base.h_vtvr != e_del.h_vtvr
    assert any(r.r_wedge != 0 for row in e_del.field.relations for r in row)


def test_4_different_waveform_differs_in_x_v_r():
    fa = dimensionalize(VERTICES, TIMES, FIELD_A)
    fb = dimensionalize(VERTICES, TIMES, FIELD_B)
    assert fa.xhat != fb.xhat
    assert fa.volume != fb.volume
    assert fa.relations != fb.relations


def test_exact_time_enters_the_laws():
    field = dimensionalize(VERTICES, TIMES, FIELD_A)
    assert field.dts[4] == F(3)
    for i in range(len(VERTICES)):
        assert field.volume[4][i] == abs(field.dxhat[4][i]) * F(3)


def test_bounds_are_errors_not_truncation():
    with pytest.raises(ValueError):
        dimensionalize(["only"], TIMES, [[r[0]] for r in FIELD_A])
    with pytest.raises(ValueError):
        dimensionalize(VERTICES, TIMES[:1], FIELD_A[:1])
    with pytest.raises(ValueError):
        bad = list(TIMES)
        bad[2] = bad[1]
        dimensionalize(VERTICES, bad, FIELD_A)
    with pytest.raises(ValueError):
        dimensionalize(VERTICES, TIMES, [r[:3] for r in FIELD_A])
    with pytest.raises(ValueError):
        dimensionalize(VERTICES, TIMES, FIELD_A, groups=[[0, 1], [1, 2, 3]])
