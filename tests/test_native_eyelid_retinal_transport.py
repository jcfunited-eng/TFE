"""Focused proof that the native eyelids physically gate retinal light."""

from __future__ import annotations

from fractions import Fraction

import pytest

from dsf_ai_service import native_production_app as production


def _axes(left: int, right: int) -> tuple[tuple[object, ...], ...]:
    return (
        (
            8,
            "left_eyelid_aperture",
            "micrometre",
            left,
            0,
            10_000,
            12_000,
        ),
        (
            9,
            "right_eyelid_aperture",
            "micrometre",
            right,
            0,
            10_000,
            12_000,
        ),
    )


def test_native_eyelid_apertures_have_exact_bounded_transmission() -> None:
    assert production._eyelid_transmission_from_axes(_axes(0, 0)) == 0
    assert production._eyelid_transmission_from_axes(_axes(6_000, 6_000)) == Fraction(1, 2)
    assert production._eyelid_transmission_from_axes(_axes(12_000, 12_000)) == 1


def test_eyelid_motion_changes_the_same_retinal_occurrence(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(production, "settle_native_joint_source_episode", capture)
    times = (Fraction(0), Fraction(1, 4))
    production._whole_roster_hop_episode(
        "eyelid-retinal-transition",
        times,
        (0.8,) * production.CARD_SURFACE_PORT_COUNT,
        (0.0, 0.0),
        retinal_transmission=(Fraction(1), Fraction(0)),
        surface_trajectories=(
            (0.8, 0.8),
        ) * production.CARD_SURFACE_PORT_COUNT,
    )

    sight = captured["observed_substreams"][production.PhysicalSense.SIGHT]
    assert len(sight) == production.CARD_SURFACE_PORT_COUNT
    for stream in sight:
        assert stream.normalized_signal == pytest.approx((0.8, 0.0))
