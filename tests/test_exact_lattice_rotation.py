from __future__ import annotations

from dsf_ai_service.substrate.exact_lattice_rotation import (
    _quadrant_bounds,
    rotate_lattice_offset,
)


def test_cardinal_body_geometry_remains_byte_exact() -> None:
    assert rotate_lattice_offset(200, 35, 0) == (200, 35)
    assert rotate_lattice_offset(200, 35, 90_000) == (-35, 200)
    assert rotate_lattice_offset(200, 35, 180_000) == (-200, -35)
    assert rotate_lattice_offset(200, 35, 270_000) == (35, -200)


def test_live_noncardinal_yaw_has_one_proved_receptor_position() -> None:
    assert rotate_lattice_offset(200, 0, 10_888) == (196, 38)
    assert rotate_lattice_offset(0, 180, 10_888) == (-34, 177)


def test_opposite_headings_preserve_rigid_body_symmetry() -> None:
    for heading in (1, 1_000, 10_888, 45_000, 89_999, 179_999):
        rotated = rotate_lattice_offset(200, 35, heading)
        opposite = rotate_lattice_offset(
            200,
            35,
            (heading + 180_000) % 360_000,
        )
        assert opposite == (-rotated[0], -rotated[1])


def test_one_heading_reuses_one_bounded_exact_proof_schedule() -> None:
    _quadrant_bounds.cache_clear()
    first = rotate_lattice_offset(200, 0, 10_888)
    before = _quadrant_bounds.cache_info()
    second = rotate_lattice_offset(0, 180, 10_888)
    after = _quadrant_bounds.cache_info()

    assert first == (196, 38)
    assert second == (-34, 177)
    assert after.hits > before.hits
    assert after.currsize <= after.maxsize == 5
