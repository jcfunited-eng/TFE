"""Test Cognitive Asset 4: Spatial Object Permanence & Occlusion Conservation (The Piaget Invariant).

Validates:
1. Mass and 3D coordinate conservation when objects leave retinal line-of-sight.
2. Targeted candidate generation toward occluded food and bed.
3. Expectation discrepancy (prediction error) detection when an unobserved object has been removed.
4. Bounded capacity enforcement and fixture preservation.
"""

from __future__ import annotations

import math
import os
import time
import pytest

# Daylight override so world illumination is invariant
os.environ.setdefault("GUALA_SOLAR_UTC_OVERRIDE", str(int(time.time()) - int(time.time()) % 86_400 + 13 * 3_600))

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    candidates,
    things_in_sight,
    OBJECT_PERMANENCE_CAPACITY,
    PERMANENCE_FIXTURES,
    BED_ID,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _her(world):
    snapshot = world.observation_snapshot()
    return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)


def _turn_her(world, new_heading_mdeg: int) -> None:
    her = _her(world)
    snapshot = world.observation_snapshot()
    cmd = world.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(PoseMM(her.pose.position, new_heading_mdeg), 250_000)),
        causal_intent_receipt_sha256="aa" * 32,
        expected_revision=snapshot.revision,
    )
    with world.prepared_action_visibility_transaction(cmd):
        world.commit_prepared_action(cmd)


def test_object_permanence_coordinate_conservation() -> None:
    """When an object leaves instantaneous retinal sight, its 3D coordinates
    and mass are conserved in the spatial conservation register."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Settle one beat: initial objects in sight are perceived
    result1 = loop.settle(organism, world, UNATTENDED)
    snapshot1 = world.observation_snapshot()
    seen1 = things_in_sight(snapshot1)
    assert len(seen1) > 0, "must perceive initial objects in sight"

    # Identify a visible object
    target = seen1[0]
    target_id = target.object_id
    assert target_id in organism.conserved_objects, f"{target_id} must be conserved upon sight"
    entry = organism.conserved_objects[target_id]
    assert entry["position"] == (int(target.position.x), int(target.position.y), int(target.position.z))
    assert entry["is_food"] == target.is_food

    # Now turn Guala 180 degrees away so target is behind her
    body = _her(world)
    new_heading = (body.pose.heading_millidegrees + 180_000) % 360_000
    _turn_her(world, new_heading)

    # Verify target is no longer in instantaneous retinal sight
    snapshot2 = world.observation_snapshot()
    seen2 = things_in_sight(snapshot2)
    assert not any(th.object_id == target_id for th in seen2), f"{target_id} must be out of sight behind her"

    # Crucial Piaget Invariant: target remains conserved in memory!
    assert target_id in organism.conserved_objects, f"{target_id} must persist in conserved_objects despite occlusion"
    entry2 = organism.conserved_objects[target_id]
    assert entry2["position"] == entry["position"], "conserved position must remain invariant"


def test_occluded_food_directed_navigation_under_hunger() -> None:
    """When hungry, Guala generates toward_food directed at conserved food
    even when the food is currently occluded / behind her."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=10)
    body = _her(world)

    # Turn Guala to face south (270 degrees) away from toys/food
    _turn_her(world, 270_000)
    snapshot_turned = world.observation_snapshot()
    body_turned = _her(world)
    seen_turned = things_in_sight(snapshot_turned)

    # Place an apple at (2000, 2000, 0) in memory as a conserved object
    apple_pos = (2000, 2000, 0)
    organism._state["conserved_objects"]["apple"] = {
        "object_id": "apple",
        "position": apple_pos,
        "radius_mm": 50,
        "room_id": "her-room",
        "is_food": True,
        "is_fixture": False,
        "last_seen_tick": 5,
        "confidence": 1.0,
    }

    # Ensure apple is NOT in instantaneous sight cone
    assert not any(th.object_id == "apple" for th in seen_turned)

    # Evaluate candidate actions
    options = candidates(
        snapshot_turned, body_turned, None, None, seen_turned, 10,
        conserved_objects=organism.conserved_objects,
    )

    # toward_food must be generated targeting the conserved apple
    food_candidates = [opt for opt in options if opt[0] == "toward_food" and opt[3] == "apple"]
    assert len(food_candidates) > 0, "toward_food must be generated for conserved occluded apple"
    act, detail, commands, target, _drive = food_candidates[0]
    assert target == "apple"
    assert "conserved" in detail
    assert len(commands) > 0, "must produce valid move commands toward conserved coordinates"


def test_occluded_bed_directed_navigation() -> None:
    """When bed is out of retinal line-of-sight, toward_bed is generated
    from the conserved bed fixture coordinates."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=20)

    # Turn Guala south-east (315 degrees) so bed (at north-west 139 deg) is out of field of view
    _turn_her(world, 315_000)
    snapshot = world.observation_snapshot()
    body_turned = _her(world)
    seen = things_in_sight(snapshot)

    # Confirm bed is not in instantaneous sight
    assert not any(th.object_id == BED_ID for th in seen)

    # Seed conserved bed
    organism._state["conserved_objects"][BED_ID] = {
        "object_id": BED_ID,
        "position": (1200, 8800, 0),
        "radius_mm": 900,
        "room_id": "her-room",
        "is_food": False,
        "is_fixture": True,
        "last_seen_tick": 1,
        "confidence": 1.0,
    }

    options = candidates(
        snapshot, body_turned, None, None, seen, 20,
        conserved_objects=organism.conserved_objects,
    )

    bed_candidates = [opt for opt in options if opt[0] == "toward_bed"]
    assert len(bed_candidates) > 0, "toward_bed must be generated from conserved bed register"
    assert bed_candidates[0][3] == BED_ID
    assert "conserved" in bed_candidates[0][1]


def test_expectation_discrepancy_on_moved_object() -> None:
    """When Guala arrives at the conserved location of an object and looks
    directly at where it was, but the object is absent, an expectation
    discrepancy (invariant violation) is detected and the object is evicted."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=30)
    loop = FunctionalPhysicalLoop()
    body = _her(world)

    # Seed a conserved toy at a location right ahead of Guala
    target_pos = (body.pose.position.x + 400, body.pose.position.y, 0)
    organism._state["conserved_objects"]["phantom_toy"] = {
        "object_id": "phantom_toy",
        "position": target_pos,
        "radius_mm": 50,
        "room_id": "her-room",
        "is_food": False,
        "is_fixture": False,
        "last_seen_tick": 10,
        "confidence": 1.0,
    }

    # Ensure Guala faces directly toward (heading 0 degrees)
    _turn_her(world, 0)

    # Settle loop step
    loop.settle(organism, world, UNATTENDED)

    # Invariant discrepancy check:
    # Guala was facing right at the coordinates within verification distance, but phantom_toy does not exist in world!
    assert "phantom_toy" not in organism.conserved_objects, "phantom_toy must be evicted on expectation discrepancy"
    assert organism._state.get("expectation_discrepancy") is not None
    assert organism._state["expectation_discrepancy"]["object_id"] == "phantom_toy"


def test_permanence_capacity_bounded() -> None:
    """Conserved objects table is strictly bounded by OBJECT_PERMANENCE_CAPACITY,
    and fixtures are protected from eviction."""
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
    conserved = organism._state.setdefault("conserved_objects", {})

    # Protect fixture
    conserved[BED_ID] = {
        "object_id": BED_ID,
        "position": (1200, 8800, 0),
        "radius_mm": 900,
        "room_id": "her-room",
        "is_food": False,
        "is_fixture": True,
        "last_seen_tick": 1,
        "confidence": 1.0,
    }

    # Add 75 mobile objects (exceeding capacity 64)
    for i in range(75):
        obj_id = f"item_{i}"
        conserved[obj_id] = {
            "object_id": obj_id,
            "position": (1000 + i * 10, 1000, 0),
            "radius_mm": 50,
            "room_id": "her-room",
            "is_food": False,
            "is_fixture": False,
            "last_seen_tick": 10 + i,
            "confidence": 1.0,
        }

    world = home_world_authority(identity=IDENTITY)
    loop = FunctionalPhysicalLoop()
    loop.settle(organism, world, UNATTENDED)

    # Capacity bound enforced!
    assert len(organism.conserved_objects) <= OBJECT_PERMANENCE_CAPACITY
    # Fixture preserved!
    assert BED_ID in organism.conserved_objects
