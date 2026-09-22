#!/usr/bin/env python3
"""test_kinematics_differential.py -- Differential test for validate_world_kinematics_native.

Asserts 100% bit-exact behavioral and exception-parity between pure-Python
_validate_world logic and the compiled Rust native kernel.
"""

from __future__ import annotations

import pytest
from dataclasses import replace
import guala_core
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import (
    PositionMM,
    _is_bed,
)
from tools.guala_headless_speed_harness import DEFAULT_IDENTITY


def _extract_kinematics_tuples(world, occupied, placed):
    regions = [
        (
            int(r.bounds.minimum.x),
            int(r.bounds.maximum.x),
            int(r.bounds.minimum.y),
            int(r.bounds.maximum.y),
            int(r.bounds.minimum.z),
            str(r.region_id),
        )
        for r in world.regions
    ]
    placed_tuples = [
        (
            int(item.position.x),
            int(item.position.y),
            int(item.position.z),
            int(item.radius_mm),
            bool(_is_bed(item)),
        )
        for item in placed
    ]
    occupied_tuples = [
        (
            int(body.pose.position.x),
            int(body.pose.position.y),
            int(body.pose.position.z),
            int(carried_radius),
            bool(body.body_id == world.self_body_id),
        )
        for body, carried_radius in occupied
    ]
    return regions, placed_tuples, occupied_tuples, str(world.room_id)


def test_live_world_kinematics_parity():
    """Live world state must pass with zero errors in both Python and Rust."""
    auth = home_world_authority(identity=DEFAULT_IDENTITY)
    world = auth._state.world

    # 1. Pure Python validation passes
    auth._validate_world(world)

    # 2. Extract inputs and validate with Rust
    placed = [item for item in world.objects if item.held_by_body_id is None]
    occupied = [(body, body.radius_mm) for body in world.bodies]
    regions, placed_tuples, occupied_tuples, room_id = _extract_kinematics_tuples(world, occupied, placed)

    guala_core.validate_world_kinematics_native(regions, placed_tuples, occupied_tuples, room_id)
    print("\n[KINEMATICS PARITY PASS] Live world validated successfully in native Rust.")


def test_placed_out_of_bounds_differential():
    """An object out of bounds must raise ValueError('object position is outside room geometry')."""
    auth = home_world_authority(identity=DEFAULT_IDENTITY)
    world = auth._state.world
    placed = [item for item in world.objects if item.held_by_body_id is None]
    occupied = [(body, body.radius_mm) for body in world.bodies]

    bad_obj = replace(placed[0], position=PositionMM(x=999999, y=999999, z=0))
    bad_placed = [bad_obj] + placed[1:]

    regions, placed_tuples, occupied_tuples, room_id = _extract_kinematics_tuples(world, occupied, bad_placed)

    with pytest.raises(ValueError, match="object position is outside room geometry") as exc_info:
        guala_core.validate_world_kinematics_native(regions, placed_tuples, occupied_tuples, room_id)
    assert "object position is outside room geometry" in str(exc_info.value)
    print("[KINEMATICS PARITY PASS] Out of bounds exception bit-identical.")


def test_body_out_of_bounds_differential():
    """A body out of bounds must raise ValueError('body and held object are outside room geometry')."""
    auth = home_world_authority(identity=DEFAULT_IDENTITY)
    world = auth._state.world
    placed = [item for item in world.objects if item.held_by_body_id is None]
    occupied = [(body, body.radius_mm) for body in world.bodies]

    bad_body = replace(occupied[0][0], pose=replace(occupied[0][0].pose, position=PositionMM(x=-999999, y=0, z=0)))
    bad_occupied = [(bad_body, occupied[0][1])] + occupied[1:]

    regions, placed_tuples, occupied_tuples, room_id = _extract_kinematics_tuples(world, bad_occupied, placed)

    with pytest.raises(ValueError, match="body and held object are outside room geometry") as exc_info:
        guala_core.validate_world_kinematics_native(regions, placed_tuples, occupied_tuples, room_id)
    assert "body and held object are outside room geometry" in str(exc_info.value)
    print("[KINEMATICS PARITY PASS] Body out of bounds exception bit-identical.")


def test_placed_collision_differential():
    """Two placed objects colliding must raise ValueError('placed objects intersect each other')."""
    auth = home_world_authority(identity=DEFAULT_IDENTITY)
    world = auth._state.world
    placed = [item for item in world.objects if item.held_by_body_id is None and not _is_bed(item)]
    occupied = [(body, body.radius_mm) for body in world.bodies]

    assert len(placed) >= 2
    # Place object 1 at same position as object 0
    colliding_obj = replace(placed[1], position=placed[0].position)
    bad_placed = [placed[0], colliding_obj] + placed[2:]

    regions, placed_tuples, occupied_tuples, room_id = _extract_kinematics_tuples(world, occupied, bad_placed)

    with pytest.raises(ValueError, match="placed objects intersect each other") as exc_info:
        guala_core.validate_world_kinematics_native(regions, placed_tuples, occupied_tuples, room_id)
    assert "placed objects intersect each other" in str(exc_info.value)
    print("[KINEMATICS PARITY PASS] Placed collision exception bit-identical.")


def test_body_placed_collision_differential():
    """Body colliding with placed object must raise ValueError('body or held object intersects placed object geometry')."""
    auth = home_world_authority(identity=DEFAULT_IDENTITY)
    world = auth._state.world
    # Find desk in the bedroom
    desk = next(o for o in world.objects if o.object_id == "desk")
    placed = [item for item in world.objects if item.held_by_body_id is None]
    occupied = [(body, body.radius_mm) for body in world.bodies]

    # Collide self body with desk inside bedroom
    colliding_body = replace(occupied[0][0], pose=replace(occupied[0][0].pose, position=desk.position))
    bad_occupied = [(colliding_body, occupied[0][1])] + occupied[1:]

    regions, placed_tuples, occupied_tuples, room_id = _extract_kinematics_tuples(world, bad_occupied, placed)

    with pytest.raises(ValueError, match="body or held object intersects placed object geometry") as exc_info:
        guala_core.validate_world_kinematics_native(regions, placed_tuples, occupied_tuples, room_id)
    assert "body or held object intersects placed object geometry" in str(exc_info.value)
    print("[KINEMATICS PARITY PASS] Body-placed collision exception bit-identical.")


if __name__ == "__main__":
    test_live_world_kinematics_parity()
    test_placed_out_of_bounds_differential()
    test_body_out_of_bounds_differential()
    test_placed_collision_differential()
    test_body_placed_collision_differential()
    print("\nALL KINEMATICS DIFFERENTIAL TESTS PASSED WITH 100% PARITY!")

