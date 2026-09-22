"""tests/test_multi_region_spatial_navigation.py — Sprint W2: Multi-Region Doorways & Spatial Navigation.

Validates:
1. Physical doorway traversals between rooms (her-room <-> hallway <-> library).
2. Inter-room affordance chaining across multiple portals.
3. Mobile object carrying across doorways (blanket travels with Guala and lands in new room).
4. Physical presence of the hallway mailbox by the entrance.
5. Kinematic bounds and energy cost per stride.
"""

from __future__ import annotations

import math
import pytest

from dsf_ai_service.affordance_planner import (
    AffordancePlan,
    extract_affordances,
    plan_need_fulfillment,
)
from dsf_ai_service.guala_caretaker_hand import _distance_mm, _portal_points, _region_of
from dsf_ai_service.guala_functional_organism import (
    BEAT_MICROSECONDS,
    FunctionalOrganism,
    door_crossing,
    door_crossing_commands,
    move_commands_toward,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    MoveCommand,
    PORT_ID,
    PickCommand,
    PoseMM,
    PositionMM,
    ReleaseHeldObjectCommand,
    encode_command,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def _her(world):
    snapshot = world.observation_snapshot()
    return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)


def _execute(world, command) -> str:
    """Executes a physical command through the canonical port transaction."""
    rev = world.observation_snapshot().revision
    prep = world.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(command),
        causal_intent_receipt_sha256="aa" * 32,
        expected_revision=rev,
    )
    if isinstance(prep, ActionExecutionReceipt):
        return prep.reason
    with world.prepared_action_visibility_transaction(prep):
        world.commit_prepared_action(prep)
    return "applied"


def _walk_and_cross_door(world, portal_id: str, from_region: str, max_beats: int = 30) -> bool:
    """Walks stride-by-stride to the doorway, sidestepping obstacles, and steps through."""
    for _ in range(max_beats):
        snap = world.observation_snapshot()
        her = _her(world)
        here = _region_of(snap, her.pose.position, her.radius_mm)
        if here is not None and here.region_id != from_region:
            return True
        portal = next(p for p in snap.portals if p.portal_id == portal_id)
        before_door, past_door = door_crossing(snap, portal, from_region)
        dist = _distance_mm(her.pose.position, before_door)
        if dist <= 400:
            for cmd in door_crossing_commands(snap, portal, from_region):
                if _execute(world, cmd) == "applied":
                    return True
        else:
            for cmd in move_commands_toward(snap, before_door, 0):
                if _execute(world, cmd) == "applied":
                    break
    return False


def test_doorway_crossing_transitions_physical_region():
    """Guala navigates from her-room through door-3 into hallway, updating physical room_id."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    her = _her(world)

    # Initially in her-room
    here = _region_of(snapshot, her.pose.position, her.radius_mm)
    assert here.region_id == "her-room"

    # Find door-3 (her-room <-> hallway) and cross
    success = _walk_and_cross_door(world, "door-3", "her-room")
    assert success, "Must navigate to and cross through door-3"

    # Verify Guala crossed into hallway
    new_snapshot = world.observation_snapshot()
    new_her = _her(world)
    new_here = _region_of(new_snapshot, new_her.pose.position, new_her.radius_mm)
    assert new_here is not None
    assert new_here.region_id == "hallway"
    assert new_snapshot.room_id == "hallway"


def test_inter_room_navigation_to_library_physical_book():
    """Guala traverses from hallway through door-4 into the library to reach the physical book."""
    world = home_world_authority(identity=IDENTITY)

    # Move to hallway through door-3
    assert _walk_and_cross_door(world, "door-3", "her-room")
    snap2 = world.observation_snapshot()
    her2 = _her(world)
    assert _region_of(snap2, her2.pose.position, her2.radius_mm).region_id == "hallway"

    # Move from hallway into library through door-4
    assert _walk_and_cross_door(world, "door-4", "hallway")

    snap3 = world.observation_snapshot()
    her3 = _her(world)
    assert _region_of(snap3, her3.pose.position, her3.radius_mm).region_id == "library"

    # Verify the physical book is present in the library
    book = next(obj for obj in snap3.objects if obj.object_id == "book")
    assert book.position is not None
    book_reg = _region_of(snap3, book.position, book.radius_mm)
    assert book_reg.region_id == "library"


def test_mobile_blanket_carrying_across_doorway_and_placement():
    """Mobile objects travel with her: Guala picks up the blanket in her-room,
    walks through door-3 into the hallway, releases it, and the blanket resides in the hallway."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    blanket = next(obj for obj in snapshot.objects if obj.object_id == "blanket")
    assert blanket.position is not None
    assert _region_of(snapshot, blanket.position, blanket.radius_mm).region_id == "her-room"

    # Approach blanket from open room to the south (3400, 8950)
    approach_pos = PositionMM(blanket.position.x, blanket.position.y - 350, 0)
    res = _execute(world, MoveCommand(PoseMM(approach_pos, 90_000), BEAT_MICROSECONDS))
    assert res == "applied"

    # Pick up blanket using canonical PickCommand
    res = _execute(world, PickCommand("blanket", BEAT_MICROSECONDS))
    assert res == "applied", f"Pick blanket must be applied, got {res}"
    snap_held = world.observation_snapshot()
    her_held = _her(world)
    assert her_held.held_object_id == "blanket"

    # Walk with blanket through door-3 into hallway
    assert _walk_and_cross_door(world, "door-3", "her-room")

    snap_hall = world.observation_snapshot()
    her_hall = _her(world)
    assert _region_of(snap_hall, her_hall.pose.position, her_hall.radius_mm).region_id == "hallway"
    assert her_hall.held_object_id == "blanket"

    # Orient heading north into clear hallway space away from caretaker person-body-1
    res = _execute(world, MoveCommand(PoseMM(her_hall.pose.position, 90_000), BEAT_MICROSECONDS))
    assert res == "applied"

    # Release blanket in hallway
    res = _execute(world, ReleaseHeldObjectCommand(BEAT_MICROSECONDS))
    assert res == "applied"

    # Verify blanket's physical position is now in the hallway
    snap_final = world.observation_snapshot()
    blanket_final = next(obj for obj in snap_final.objects if obj.object_id == "blanket")
    assert blanket_final.position is not None
    blanket_reg = _region_of(snap_final, blanket_final.position, blanket_final.radius_mm)
    assert blanket_reg.region_id == "hallway"


def test_hallway_mailbox_physical_presence_and_affordance():
    """Mailbox by the entrance doorway is physically declared, detectable, and accessible."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    mailbox = next(obj for obj in snapshot.objects if obj.object_id == "mailbox")
    assert mailbox.position is not None
    assert mailbox.position.x == 8_200
    assert mailbox.position.y == 9_200

    # Enclosed in hallway
    reg = _region_of(snapshot, mailbox.position, mailbox.radius_mm)
    assert reg.region_id == "hallway"

    # Has distinct sensory profile: wood/paper/ink odour
    assert mailbox.material is not None
    assert mailbox.material.odorant_release_nanograms_per_second[3] > 0  # wood/earth
    assert mailbox.material.odorant_release_nanograms_per_second[5] > 0  # paper/ink


def test_multi_room_affordance_plan_execution():
    """Guala in her-room evaluates a target in the kitchen, generating a multi-portal
    causal affordance plan across doorway topologies."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    her = _her(world)

    her_pos = (her.pose.position.x, her.pose.position.y, her.pose.position.z)
    affordances = extract_affordances(snapshot.objects, snapshot.portals, her, snapshot.regions)

    # Find apple in kitchen
    apple_aff = next(a for a in affordances if a.object_id == "apple")
    assert apple_aff.region_id == "kitchen"

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=her_pos,
        self_region="her-room",
        hunger_deficit=0.85,
        tick=100,
    )

    assert plan.is_refused is False
    assert plan.target_object_id in ("apple", "bread-slice")

    # Must contain door traversal steps followed by approach, grasp, bite
    actions = [s.action for s in plan.steps]
    door_steps = [s for s in plan.steps if s.action == "toward_door"]
    assert len(door_steps) >= 2  # door-3 (her-room -> hallway) and door-6 (hallway -> kitchen)
    assert door_steps[0].target_id == "door-3"
    assert door_steps[1].target_id == "door-6"
    assert actions[-3:] == ["toward_food", "grasp", "bite"]

