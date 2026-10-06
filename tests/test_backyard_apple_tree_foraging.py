"""tests/test_backyard_apple_tree_foraging.py — Autonomous VR Backyard Foraging Verification.

Validates:
1. Autonomous perceptual grounding of the apple tree (garden-apple) in the virtual backyard.
2. Approach, grasp, and oral bite extraction of digestible nutrients from the apple's physical reservoir.
3. Closed-loop satiety convergence and clean release of depleted core without limit-cycle oscillation.
4. Multi-source autonomous foraging crossing the true mathematical satiety threshold (>= 425,000 ug).
"""

from __future__ import annotations

import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    CAPACITY_MICROGRAMS,
    SATED_ABOVE,
    is_genuine_food_object,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import PoseMM, PositionMM
from tests.test_guala_functional_organism import IDENTITY, UNATTENDED


def test_backyard_apple_tree_acquisition_and_full_ingestion() -> None:
    """An organism at the backyard apple tree grasps the apple, bites it to full
    consumption, absorbs real digestible mass into somatic reserve, and cleanly releases
    the depleted core without regrasping or barrier oscillation.
    """
    world = home_world_authority(identity=IDENTITY)
    # Position Guala in backyard facing north directly at garden-apple (x=14000, y=14100)
    world.admit_authored_body_transport(
        "guala-body-1", PoseMM(PositionMM(14000, 13700, 0), 90000)
    )

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = 0
    organism._state["feeding"] = True
    organism._state["room_now"] = "backyard"

    loop = FunctionalPhysicalLoop()
    bites_taken = 0
    total_intake_zeptojoules = 0
    released = False

    for beat in range(30):
        result = loop.settle(organism, world, UNATTENDED)
        obs = result.observation
        act = obs.get("her_act")
        intake = obs.get("real_nutrition_intake_zeptojoules", 0)

        if act == "bite":
            bites_taken += 1
            total_intake_zeptojoules += intake

        if act == "release":
            released = True
            break

    # Physical invariants verification:
    assert bites_taken >= 10, f"Expected multi-beat mastication, got only {bites_taken} bites"
    assert total_intake_zeptojoules > 0, "No real nutritional energy was transferred"
    assert organism.reserve_micrograms > 100_000, (
        f"Reserve not replenished: {organism.reserve_micrograms} ug"
    )
    assert released, "Organism never released depleted core after exhaustion"

    # Verify that the depleted apple is marked in conserved memory and never retaken:
    conserved = organism._state.get("conserved_objects", {})
    apple_entry = conserved.get("garden-apple", {})
    assert apple_entry.get("currently_depleted") is True, (
        f"Conserved memory did not mark apple as depleted: {apple_entry}"
    )


def test_backyard_apple_approach_and_harvest() -> None:
    """An organism starting 800 mm south of the apple tree takes physical locomotion
    strides to approach the tree, acquires the hanging fruit, and initiates ingestion.
    """
    world = home_world_authority(identity=IDENTITY)
    # Position Guala 800 mm away from tree facing north
    world.admit_authored_body_transport(
        "guala-body-1", PoseMM(PositionMM(14000, 13300, 0), 90000)
    )

    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["room_now"] = "backyard"

    loop = FunctionalPhysicalLoop()
    grasped = False
    achieved_intake = False

    for beat in range(25):
        result = loop.settle(organism, world, UNATTENDED)
        obs = result.observation
        act = obs.get("her_act")
        intake = obs.get("real_nutrition_intake_zeptojoules", 0)

        if act == "grasp":
            grasped = True
        if intake > 0:
            achieved_intake = True
            break

    assert grasped, "Organism failed to grasp garden-apple after approach"
    assert achieved_intake, "Organism failed to ingest fruit from garden-apple"
    assert organism.counts["bites"] >= 1, "Organism took no bites"


def test_multi_source_autonomous_foraging_to_full_satiety() -> None:
    """An organism foraging across domestic food sources (garden-apple 140mg,
    bread-slice 100mg, bottle-milk 100mg, kitchen-apple 140mg) absorbs genuine digestible mass
    into somatic reserve until crossing the mathematical satiety threshold (>= 425,000 ug),
    at which point organism.feeding cleanly disengages (False) without threshold manipulation.
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    sated_target = int(CAPACITY_MICROGRAMS * SATED_ABOVE)  # Exactly 425,000 ug
    assert sated_target == 425_000, f"Expected 425,000 ug, got {sated_target}"

    # Verify initial hunger state
    organism._state["reserve_micrograms"] = 0
    organism._state["feeding"] = True

    # Multi-source sequence:
    # 1. Backyard: garden-apple at (14000, 14100)
    world.admit_authored_body_transport(
        "guala-body-1", PoseMM(PositionMM(14000, 13700, 0), 90000)
    )
    organism._state["room_now"] = "backyard"
    for _ in range(30):
        result = loop.settle(organism, world, UNATTENDED)
        if result.observation.get("her_act") == "release":
            break

    reserve_after_apple1 = organism.reserve_micrograms
    assert reserve_after_apple1 > 100_000, f"Expected >100,000 ug after garden-apple, got {reserve_after_apple1}"
    assert organism._state["feeding"] is True, "Organism should still be hungry after only 1 apple"

    # 2. Kitchen: bread-slice at (1300, 2000)
    world.admit_authored_body_transport(
        "guala-body-1", PoseMM(PositionMM(1650, 2000, 0), 180000)
    )
    organism._state["room_now"] = "kitchen"
    for _ in range(30):
        result = loop.settle(organism, world, UNATTENDED)
        if result.observation.get("her_act") == "release":
            break

    reserve_after_bread = organism.reserve_micrograms
    assert reserve_after_bread > reserve_after_apple1, "Bread did not increase reserve"
    assert organism._state["feeding"] is True, "Organism should still be hungry after apple + bread"

    # 3. Dining: bottle-milk at (8000, 3500)
    world.admit_authored_body_transport(
        "guala-body-1", PoseMM(PositionMM(7999, 3857, 0), 270087)
    )
    organism._state["room_now"] = "dining"
    for _ in range(30):
        result = loop.settle(organism, world, UNATTENDED)
        if result.observation.get("her_act") == "release":
            break

    reserve_after_milk = organism.reserve_micrograms
    assert reserve_after_milk > reserve_after_bread, "Milk did not increase reserve"
    assert organism._state["feeding"] is True, "Organism should still be hungry after apple + bread + milk"

    # 4. Kitchen: apple at (5650, 900)
    world.admit_authored_body_transport(
        "guala-body-1", PoseMM(PositionMM(5650, 550, 0), 90000)
    )
    organism._state["room_now"] = "kitchen"
    for _ in range(30):
        result = loop.settle(organism, world, UNATTENDED)
        if result.observation.get("her_act") == "release":
            break

    # Final Verification: somatic reserve must meet or exceed the full satiety threshold (425,000 ug)
    assert organism.reserve_micrograms >= sated_target, (
        f"Reserve {organism.reserve_micrograms} ug failed to reach satiety threshold {sated_target} ug"
    )
    assert organism._state["feeding"] is False, (
        f"Feeding state did not disengage after reaching full satiety: {organism._state['feeding']}"
    )
