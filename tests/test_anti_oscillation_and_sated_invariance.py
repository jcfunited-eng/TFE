"""
DSF-AI Invariant Verification Suite: Anti-Oscillation & Sated Convergence
=========================================================================
Verifies that the autonomous organism substrate never enters 2-beat or 3-beat
limit-cycle attractor oscillations (e.g. infinite grasp -> release loops on non-food fixtures)
and guarantees closed-loop homeostatic evacuation of barren basins to achieve
sated reserve convergence (> 0% sated).

Author: Senior DARPA Neuromorphic Systems Architect
Invariants Enforced:
1. Anti-Oscillation Invariant: No repeating periodic limit cycles over action histories.
2. Material Affordance Invariant: Items with no edible material are never pursued as nourishment.
3. Barren Basin Invariant: A starving organism in a barren room evacuates toward negative space.
4. Closed-Loop Sated Convergence Invariant: A starving organism starting at 0% reserve autonomously
   navigates through portals, explores rooms, finds nourishment, bites, and restores reserve (> 0% sated).
"""

from collections import Counter
from typing import Any
import pytest

from dsf_ai_service.guala_functional_organism import (
    CAPACITY_MICROGRAMS, FunctionalOrganism,
)
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _detect_limit_cycle(actions: list[str], min_cycle_len: int = 2, max_cycle_len: int = 4, min_repetitions: int = 3) -> tuple[bool, list[str]]:
    """Detect if the action sequence ends in a repeating limit-cycle attractor across distinct actions."""
    if len(actions) < min_cycle_len * min_repetitions:
        return False, []

    for cycle_len in range(min_cycle_len, max_cycle_len + 1):
        window = cycle_len * min_repetitions
        tail = actions[-window:]
        pattern = tail[-cycle_len:]
        # An oscillation requires distinct alternating states, not monotonic locomotion repetition (e.g. repeated walking)
        if len(set(pattern)) <= 1:
            continue
        reconstructed = pattern * min_repetitions
        if tail == reconstructed:
            return True, pattern
    return False, []


def test_organism_never_oscillates_on_bedroom_night_light_when_starving():
    """Verify that when waking with 0% reserve next to night-light, Guala NEVER oscillates
    between grasp and release.
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    # Force 0% reserve (100% hunger deficit)
    organism._state["reserve_micrograms"] = 0
    organism._state["feeding"] = True
    organism._state["room_now"] = "her-room"

    loop = FunctionalPhysicalLoop()
    actions = []
    reasons = []

    for beat in range(40):
        result = loop.settle(organism, world, UNATTENDED)
        obs = result.observation
        act = obs.get("her_act")
        reason = obs.get("act_reason")
        actions.append(act)
        reasons.append(reason)

        # Invariant 1: Check for limit-cycle oscillation on every beat
        is_oscillating, cycle_pattern = _detect_limit_cycle(actions)
        assert not is_oscillating, (
            f"Oscillation limit-cycle detected at beat {beat}: pattern={cycle_pattern}! "
            f"Recent actions={actions[-8:]} reasons={reasons[-4:]}"
        )

    # Invariant 2: Night-light must NOT be grasped as candidate nourishment
    night_light_grasps = [
        (a, r) for a, r in zip(actions, reasons)
        if a == "grasp" and "night-light" in str(r)
    ]
    assert len(night_light_grasps) == 0, f"Night-light was grasped as nourishment: {night_light_grasps}"


def test_fixtures_without_material_never_considered_candidate_nourishment():
    """Verify that handleable objects with material=None are never generated as grasp feeding candidates."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = 0
    organism._state["feeding"] = True

    snapshot = world.observation_snapshot()
    her = next(b for b in snapshot.bodies if b.body_id == snapshot.self_body_id)

    from dsf_ai_service.guala_functional_organism import candidates, things_in_sight
    seen = things_in_sight(snapshot)
    cands = candidates(
        snapshot, her, None, None, seen, 1,
        feeding=True,
        conserved_objects=organism._state.get("conserved_objects"),
    )

    # Ensure no non-food fixture is a grasp candidate under feeding
    feeding_grasps = [c for c in cands if c[0] == "grasp"]
    for fg in feeding_grasps:
        target_obj = next((o for o in snapshot.objects if o.object_id == fg[3]), None)
        assert target_obj is not None
        assert target_obj.material is not None, f"Object {fg[3]} has material=None but was offered as grasp candidate under feeding!"
        assert sum(target_obj.material.tastant_mass_micrograms) >= 2_000, f"Object {fg[3]} has insufficient tastants but offered as grasp candidate!"


def test_starving_organism_evacuates_bedroom_toward_nourishment():
    """Verify that starting at 0% reserve in her bedroom, Guala evacuates her room to seek food."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    # Start at 0% reserve (deficit = 1.0) in her-room
    organism._state["reserve_micrograms"] = 0
    organism._state["feeding"] = True
    organism._state["room_now"] = "her-room"

    loop = FunctionalPhysicalLoop()
    actions = []
    reasons = []
    evacuated = False

    for beat in range(30):
        result = loop.settle(organism, world, UNATTENDED)
        act = result.observation.get("her_act")
        reason = result.observation.get("act_reason")
        actions.append(act)
        reasons.append(reason)

        if act == "toward_door" and ("barren basin" in str(reason) or "evacuat" in str(reason)):
            evacuated = True
            break

    assert evacuated, (
        f"Guala failed to evacuate barren bedroom within 30 beats! "
        f"Actions taken: {actions[:15]} Reasons: {reasons[:5]}"
    )


def test_starving_organism_achieves_closed_loop_sated_convergence():
    """Verify that an organism starting at 0% reserve in her bedroom autonomously evacuates,
    explores the environment, discovers nourishment, executes bite reflex, and achieves
    positive reserve convergence (> 0% sated).
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    organism._state["reserve_micrograms"] = 0
    organism._state["feeding"] = True
    organism._state["room_now"] = "her-room"

    loop = FunctionalPhysicalLoop()
    achieved_sated = False
    max_beats = 100

    for beat in range(max_beats):
        res = loop.settle(organism, world, UNATTENDED)
        obs = res.observation
        act = obs.get("her_act")
        res_ug = organism._state.get("reserve_micrograms", 0)
        intake = obs.get("real_nutrition_intake_zeptojoules", 0)

        if intake > 0 and res_ug > 0:
            achieved_sated = True
            break

    assert achieved_sated, (
        f"Guala failed to achieve closed-loop sated convergence within {max_beats} beats! "
        f"Final reserve: {organism._state.get('reserve_micrograms', 0)} ug, "
        f"Final room: {organism._state.get('room_now')}"
    )
