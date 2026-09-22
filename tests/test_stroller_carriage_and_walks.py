#!/usr/bin/env python3
"""tests/test_stroller_carriage_and_walks.py — Stroller Carriage Vehicle Tool & Outdoor Walks.

Verifies:
1. Physical entity definition, chassis mass, rolling compliance, and optical reflectance.
2. Pairwise floor disc clearances in the hallway and compliance with the 64-object ceiling.
3. Affordance extraction marking stroller as transport vehicle and rideable support surface.
4. Deterministic multi-step vehicle journey planning for outdoor walks (hallway -> backyard).
5. Inter-room journey chaining from her-room through hallway to backyard.
6. Caretaker nocturnal house tidying resetting stroller to parking perch in hallway.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from dsf_ai_service.affordance_planner import (
    AffordanceField,
    AffordancePlan,
    extract_affordances,
    plan_vehicle_journey,
)
from dsf_ai_service.guala_home_world import (
    HOME_SHAPES,
    home_world_authority,
    nocturnal_house_tidying,
)
from dsf_ai_service.substrate.embodiment_world import PositionMM

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_stroller_carriage_physical_entity() -> None:
    """Verify stroller carriage exists with authentic chassis mass, compliance, and optical properties."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    stroller = next((item for item in snapshot.objects if item.object_id == "stroller-carriage"), None)
    assert stroller is not None, "stroller-carriage missing from home world snapshot"
    assert stroller.position.x == 6_500
    assert stroller.position.y == 6_000
    assert stroller.position.z == 0
    assert stroller.mass_grams == 8_500
    assert stroller.radius_mm > 0

    # Material verification
    assert stroller.material is not None
    assert stroller.material.compliance_ppm == 150_000
    assert stroller.material.surface_temperature_millikelvin == 294_000
    assert stroller.material.roughness_micrometers == 25
    assert stroller.reflectance_ppm == (140_000, 180_000, 320_000, 260_000, 180_000, 140_000)

    # Declared shape in HOME_SHAPES
    assert "stroller-carriage" in HOME_SHAPES
    dims, heading, z_bottom = HOME_SHAPES["stroller-carriage"]
    assert dims == (850, 550, 750)
    assert z_bottom == 0


def test_hallway_clearance_and_strict_64_ceiling() -> None:
    """Verify hallway disc clearances and strict compliance with the 64-object ceiling."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    # Exact count: 64 objects (63 declared furniture/tools + 1 nightlight)
    assert len(snapshot.objects) == 64
    assert len(snapshot.objects) <= 64

    # Pairwise clearance check across all rooms
    for region in snapshot.regions:
        room_objects = [
            obj for obj in snapshot.objects
            if region.bounds.contains_floor_disc(obj.position, obj.radius_mm)
        ]
        for i in range(len(room_objects)):
            for j in range(i + 1, len(room_objects)):
                o1 = room_objects[i]
                o2 = room_objects[j]
                d = math.hypot(o1.position.x - o2.position.x, o1.position.y - o2.position.y)
                min_clearance = o1.radius_mm + o2.radius_mm
                assert d >= min_clearance, (
                    f"Floor disc overlap in {region.region_id} between {o1.object_id} (r={o1.radius_mm}) "
                    f"and {o2.object_id} (r={o2.radius_mm}): dist={d:.1f} < min={min_clearance}"
                )


def test_affordance_extraction_for_vehicle() -> None:
    """Verify affordance extraction tags stroller as vehicle, transport, support surface, and movable."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    affordances = extract_affordances(snapshot.objects, snapshot.portals, regions=snapshot.regions)

    stroller_aff = next(a for a in affordances if a.object_id == "stroller-carriage")
    assert stroller_aff.is_vehicle is True
    assert stroller_aff.can_transport is True
    assert stroller_aff.support_surface is True
    assert stroller_aff.movable is True
    assert stroller_aff.elevation_height_mm == 300
    assert stroller_aff.region_id == "hallway"


def test_plan_vehicle_journey_outdoor_walk() -> None:
    """Verify deterministic multi-step vehicle journey from hallway to backyard."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    affordances = extract_affordances(snapshot.objects, snapshot.portals, regions=snapshot.regions)

    # Guala starts in hallway near stroller
    guala_pos = (6_800, 6_200, 0)
    journey_plan = plan_vehicle_journey(
        affordances=affordances,
        self_pos=guala_pos,
        self_region="hallway",
        destination_region="backyard",
        target_vehicle_id="stroller-carriage",
        tick=1_000,
    )

    assert journey_plan.is_refused is False
    assert journey_plan.goal == "travel_to_backyard"
    assert journey_plan.target_object_id == "stroller-carriage"
    assert journey_plan.terminal_valence >= 0.90

    # Steps: approach -> mount -> traverse portal door-8 -> dismount
    actions = [s.action for s in journey_plan.steps]
    assert "mount_vehicle" in actions
    assert "traverse_portal_in_vehicle" in actions
    assert "dismount_vehicle" in actions
    assert journey_plan.steps[-1].expected_postcondition == "arrived_at_backyard"


def test_plan_vehicle_journey_inter_room_her_room_to_backyard() -> None:
    """Verify combinatorial multi-room chaining: her-room -> hallway -> mount vehicle -> backyard."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    affordances = extract_affordances(snapshot.objects, snapshot.portals, regions=snapshot.regions)

    # Guala starts in her room
    guala_bed_pos = (2_000, 7_000, 0)
    journey_plan = plan_vehicle_journey(
        affordances=affordances,
        self_pos=guala_bed_pos,
        self_region="her-room",
        destination_region="backyard",
        target_vehicle_id="stroller-carriage",
        tick=2_000,
    )

    assert journey_plan.is_refused is False
    assert journey_plan.goal == "travel_to_backyard"
    actions = [s.action for s in journey_plan.steps]

    # Must first navigate to doorway connecting her-room to hallway
    assert actions[0] == "toward_door"
    assert journey_plan.steps[0].precondition == "in_region_her-room"
    assert journey_plan.steps[0].expected_postcondition == "in_region_hallway"

    # Then approach and mount stroller
    assert "toward_vehicle" in actions
    assert "mount_vehicle" in actions

    # Then traverse into backyard and dismount
    assert "traverse_portal_in_vehicle" in actions
    assert "dismount_vehicle" in actions


def test_nocturnal_tidying_resets_stroller_position() -> None:
    """Verify caretaker nocturnal house tidying resets displaced stroller back to hallway perch."""
    world = home_world_authority(identity=IDENTITY)

    # Displace stroller to backyard
    cur_world = world._state.world
    updated = []
    for obj in cur_world.objects:
        if obj.object_id == "stroller-carriage":
            updated.append(replace(obj, position=PositionMM(5_000, 12_000, 0)))
        else:
            updated.append(obj)
    new_world = replace(cur_world, objects=tuple(updated))
    new_obs = world._observation_for(new_world)
    world._state = replace(world._state, world=new_world, observation=new_obs)

    # Verify displaced state
    displaced = next(o for o in world.observation_snapshot().objects if o.object_id == "stroller-carriage")
    assert displaced.position.x == 5_000 and displaced.position.y == 12_000

    # Run Caretaker Nocturnal Tidying
    nocturnal_house_tidying(world)

    # Verify stroller returned to hallway parking perch (6_500, 6_000, 0)
    reset_stroller = next(o for o in world.observation_snapshot().objects if o.object_id == "stroller-carriage")
    assert reset_stroller.position.x == 6_500 and reset_stroller.position.y == 6_000

