"""
Walk-up contracts for the NON-CANONICAL TFE joint-field side kernel.

Mirrors the four walk-up validations of the Guala "UF Side Kernel VTVR v2"
reconstruction (27 July 2026), adapted to the market domain, plus boundary
contracts. These tests grant the side kernel no canonical authority.

Run: python -m pytest tests/test_isolated_vtvr_side_kernel.py -q
"""

from fractions import Fraction as F

import pytest

from tools.isolated_vtvr_side_kernel import (
    dimensionalize,
    form_event,
    run_experience,
)


def _fixture_a():
    """Four stocks, six causal times with UNEQUAL exact gaps (a weekend)."""
    names = ["AAA", "BBB", "CCC", "DDD"]
    times = [F(0), F(1), F(2), F(3), F(6), F(7)]  # 3→6 is a weekend gap
    observations = [
        [F(100), F(50), F(20), F(10)],
        [F(101), F(50), F(19), F(10)],
        [F(103), F(49), F(19), F(11)],
        [F(102), F(51), F(20), F(11)],
        [F(105), F(52), F(21), F(12)],
        [F(104), F(53), F(22), F(12)],
    ]
    return names, times, observations


def _fixture_b():
    """Structurally different waveform on the same vertices and times."""
    names, times, _ = _fixture_a()
    observations = [
        [F(100), F(50), F(20), F(10)],
        [F(99),  F(51), F(21), F(9)],
        [F(97),  F(53), F(22), F(9)],
        [F(98),  F(52), F(21), F(8)],
        [F(95),  F(54), F(23), F(8)],
        [F(96),  F(55), F(24), F(7)],
    ]
    return names, times, observations


# ── 1. Joint field and determinism ──────────────────────────────────────

def test_joint_field_and_determinism():
    names, times, obs = _fixture_a()
    e1 = run_experience(names, times, obs)
    e2 = run_experience(names, times, obs)

    # Byte-identical layer and experience receipts
    assert e1.h_layers == e2.h_layers
    assert e1.h_experience == e2.h_experience

    m, n = len(times), len(names)
    # Four vector components at every time
    assert all(len(row) == n for row in e1.l0.xhat) and len(e1.l0.xhat) == m
    # Six retained pair relations at every time
    assert all(len(row) == n * (n - 1) // 2 for row in e1.l0.relations)
    # Separate typed structures survive through L4
    assert len(e1.l4.displacement) == m
    assert len(e1.l4.cohesion) == m
    assert len(e1.l4.breathing) == m
    assert e1.l4.availability[0][0] == "genesis"
    assert e1.l4.availability[1][0] == "observed"


def test_exact_time_enters_the_laws():
    """The weekend gap must scale swept volume — time is not an index."""
    names, times, obs = _fixture_a()
    field = dimensionalize(names, times, obs)
    # dt at index 4 is 3 (weekend), others are 1
    assert field.dts[4] == F(3)
    # A displacement across the gap sweeps 3x the volume of the same
    # displacement across a unit gap.
    k = 4
    for i in range(len(names)):
        assert field.volume[k][i] == abs(field.dxhat[k][i]) * F(3)


# ── 2. Common positive gain (currency redenomination) ───────────────────

def test_common_positive_gain_quotient():
    names, times, obs = _fixture_a()
    scaled = [[v * 7 for v in row] for row in obs]

    f1 = dimensionalize(names, times, obs)
    f2 = dimensionalize(names, times, scaled)

    # Raw custody changes
    assert f1.h_raw != f2.h_raw
    # Joint structural receipt is invariant
    assert form_event(f1).h_vtvr == form_event(f2).h_vtvr


# ── 3. Lead–lag delay (the market analog of interaural delay) ───────────

def test_lead_lag_delay_is_retained():
    names, times, obs = _fixture_a()
    # Delay two of the four stocks by one causal step
    delayed = []
    for k in range(len(times)):
        row = list(obs[k])
        src = obs[max(0, k - 1)]
        row[2], row[3] = src[2], src[3]
        delayed.append(row)

    e_base = form_event(dimensionalize(names, times, obs))
    e_del = form_event(dimensionalize(names, times, delayed))

    # The delay is structurally visible
    assert e_base.h_vtvr != e_del.h_vtvr
    # At least one nonzero oriented-area (wedge) relation survives
    wedges = [
        r.r_wedge
        for row in e_del.field.relations
        for r in row
    ]
    assert any(w != 0 for w in wedges)


# ── 4. Different waveform ───────────────────────────────────────────────

def test_different_waveform_differs_in_x_v_r():
    names, times, obs_a = _fixture_a()
    _, _, obs_b = _fixture_b()

    fa = dimensionalize(names, times, obs_a)
    fb = dimensionalize(names, times, obs_b)

    def h_x(f):
        return [list(r) for r in f.xhat]

    def h_v(f):
        return [list(r) for r in f.volume]

    def h_r(f):
        return [[(e.r_minus, e.r_plus, e.r_delta, e.r_wedge) for e in row]
                for row in f.relations]

    assert h_x(fa) != h_x(fb)
    assert h_v(fa) != h_v(fb)
    assert h_r(fa) != h_r(fb)


# ── Boundary contracts ──────────────────────────────────────────────────

def test_bounds_are_errors_not_truncation():
    names, times, obs = _fixture_a()

    with pytest.raises(ValueError):
        dimensionalize(["ONLY"], times, [[r[0]] for r in obs])  # N=1

    with pytest.raises(ValueError):
        dimensionalize(names, times[:1], obs[:1])  # M=1

    with pytest.raises(ValueError):
        bad_times = list(times)
        bad_times[2] = bad_times[1]  # not strictly increasing
        dimensionalize(names, bad_times, obs)

    with pytest.raises(ValueError):
        ragged = [row[:3] for row in obs]  # not a complete joint vector
        dimensionalize(names, times, ragged)

    with pytest.raises(ValueError):
        dimensionalize(names, times, obs, groups=[[0, 1], [1, 2, 3]])  # overlap
