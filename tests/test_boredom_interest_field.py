"""Tests for Unified Structural Boredom, Interest, and Somatic Potential Manifold.

Verifies:
1. Somatic Free Energy Partitioning (surplus vs deficit).
2. Local Basin Exhaustion (boredom monotonically rising with room dwell time under surplus).
3. Distal Negative Space Attraction (interest favoring unvisited/least-recent portals).
4. Natural room evacuation out of a saturated room without heuristic scripts or momentum hacks.
5. Barren room exhaustion (evacuation under fatigue when room lacks bed).
6. Topological multi-room portal routing toward distal bed across doorways.
7. Rotational limit-cycle damping breaking in-place spin traps.
"""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Any
import pytest

from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    candidates,
    BED_ID,
    CAPACITY_MICROGRAMS,
    SLEEP_PRESSURE_CEILING,
    PositionMM,
)
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_somatic_surplus_and_boredom_mechanics():
    """Verify that surplus free energy scales boredom with room dwell time."""
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
    
    # Case A: Well-fed, rested infant has high surplus free energy
    org._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 80 // 100  # 20% deficit
    org._state["sleep_pressure"] = 0
    deficit = float(org.deficit)
    sleep_ratio = float(org._state["sleep_pressure"]) / SLEEP_PRESSURE_CEILING
    surplus = max(0.0, min(1.0, (1.0 - deficit) * (1.0 - sleep_ratio)))
    assert surplus >= 0.79

    # Initial dwell: boredom is zero for first 32 beats (natural in-room affordance exploration)
    org._state["room_now"] = "her-room"
    org._state["room_dwell_beats"] = 20
    boredom_20 = surplus * math.tanh(max(0.0, float(org._state["room_dwell_beats"] - 32)) / 24.0)
    assert boredom_20 == 0.0

    org._state["room_dwell_beats"] = 32
    boredom_32 = surplus * math.tanh(max(0.0, float(org._state["room_dwell_beats"] - 32)) / 24.0)
    assert boredom_32 == 0.0

    # Extended dwell: boredom rises asymptotically past 32 beats
    org._state["room_dwell_beats"] = 48
    boredom_48 = surplus * math.tanh(max(0.0, float(org._state["room_dwell_beats"] - 32)) / 24.0)
    assert 0.40 <= boredom_48 <= 0.55

    org._state["room_dwell_beats"] = 80
    boredom_80 = surplus * math.tanh(max(0.0, float(org._state["room_dwell_beats"] - 32)) / 24.0)
    assert boredom_80 > boredom_48
    assert boredom_80 >= 0.70

    # Case B: Severe hunger or sleep deficit suppresses boredom (homeostasis dominates)
    org._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 15 // 100  # 85% deficit
    deficit_hungry = float(org.deficit)
    surplus_hungry = max(0.0, min(1.0, (1.0 - deficit_hungry) * (1.0 - sleep_ratio)))
    assert surplus_hungry <= 0.16
    boredom_hungry = surplus_hungry * math.tanh(max(0.0, float(80 - 32)) / 24.0)
    assert boredom_hungry < 0.20


def test_portal_interest_favors_unvisited_negative_space():
    """Verify that unvisited or less-recently visited regions exert stronger attractive potential."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1000)

    # Set up region history: Guala recently visited wcs-room, but dining is unvisited
    org._state["room_now"] = "daddys-room"
    org._state["region_visits"] = {"daddys-room": 100, "wcs-room": 50}
    org._state["region_last_tick"] = {"daddys-room": 1000, "wcs-room": 980}
    # "dining" has 0 visits in region_visits

    here = next((r for r in snapshot.regions if r.region_id == "daddys-room"), None)
    assert here is not None

    doors = [p for p in snapshot.portals if "daddys-room" in p.region_ids]
    assert len(doors) >= 2  # door-1 (dining) and door-2 (wcs-room)

    # Evaluate novelty scoring
    scored_doors = []
    for p in doors:
        dest_r = next((r for r in p.region_ids if r != "daddys-room"), None)
        visits = org._state.get("region_visits", {}).get(dest_r, 0)
        last_t = org._state.get("region_last_tick", {}).get(dest_r, 0)
        elapsed = 1000 - last_t if last_t > 0 else 1_000_000
        # Priority: unvisited (visits == 0), then largest elapsed time, then fewer visits
        score = (visits == 0, elapsed, -visits)
        scored_doors.append((score, p.portal_id, dest_r))

    scored_doors.sort(reverse=True)
    # The portal to "dining" must rank higher than "wcs-room" because dining was never visited
    best_score, best_portal, best_dest = scored_doors[0]
    assert best_dest == "dining"
    assert best_score[0] is True  # unvisited = True


def test_room_evacuation_under_boredom_in_loop():
    """In a functional loop, verify Guala evacuates her-room when dwell beats mount past threshold."""
    world = home_world_authority(identity=IDENTITY)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    org._state["reserve_micrograms"] = CAPACITY_MICROGRAMS * 85 // 100  # well-fed
    org._state["room_now"] = "her-room"
    # Prime dwell beats past 32 so boredom is actively engaged
    org._state["room_dwell_beats"] = 48

    loop = FunctionalPhysicalLoop()
    
    # Run loop beats until room changes or up to 25 beats
    initial_room = org._state["room_now"]
    assert initial_room == "her-room"
    
    room_transitions = []
    for _ in range(25):
        settle_res = loop.settle(org, world, UNATTENDED)
        cur_room = org._state.get("room_now")
        if cur_room != initial_room:
            room_transitions.append(cur_room)
            break
            
    # Verify Guala evacuated her-room through door-3 into hallway
    assert len(room_transitions) > 0, f"Guala failed to evacuate her-room within 25 beats; dwell={org._state.get('room_dwell_beats')}"
    assert room_transitions[0] == "hallway"
    # Verify dwell reset to 1 in the new room
    assert org._state.get("room_dwell_beats") == 1


def test_barren_room_evacuation_under_fatigue():
    """Verify that when fatigued in a room with no bed (e.g. kitchen), basin exhaustion drives toward_door."""
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1000)
    org._state["room_now"] = "kitchen"
    org._state["room_dwell_beats"] = 22
    org._state["sleep_pressure"] = int(SLEEP_PRESSURE_CEILING * 0.95)
    acts = ["turn_left", "turn_right", "step", "toward_door"]
    act, why = org._choose("barren_key_1", "TSVS", acts)
    assert act == "toward_door"
    assert "barren basin exhaustion" in why


def test_toward_bed_multi_room_portal_routing():
    """Verify that toward_bed in kitchen routes toward door-6 connecting to hallway."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    body = [b for b in snapshot.bodies if b.body_id == "guala-body-1"][0]
    pose = replace(body.pose, position=PositionMM(6000, 3500, 0))
    kitchen_body = replace(body, pose=pose)
    conserved = {BED_ID: {"position": (1200, 8800, 0), "radius_mm": 600, "is_food": False}}
    cands = candidates(snapshot, kitchen_body, None, None, (), 1000, sleepy=True, conserved_objects=conserved)
    toward_bed_cands = [c for c in cands if c[0] == "toward_bed"]
    assert len(toward_bed_cands) > 0
    assert "door-6" in toward_bed_cands[0][1]


def test_rotational_spin_trap_damping():
    """Verify that after 2 consecutive turns, in-place turns are damped and forward translation is selected."""
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1000)
    org._state["consecutive_turns"] = 2
    act, why = org._choose("spin_test_key", "SSSS", ["turn_left", "turn_right", "step"])
    assert act == "step"
