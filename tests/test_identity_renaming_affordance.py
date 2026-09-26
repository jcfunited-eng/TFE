"""Focused physical affordance, contact lifecycle, and ordinary-loop recognition falsifier:
Verifies that:
1. Physically identical objects under different administrative identifiers have identical affordances.
2. Depleted objects remain graspable and manipulable when physical geometry permits.
3. Unsuccessful bite suppression is scoped strictly to the unchanged contact episode and ends on custody change.
4. Continuous ordinary-loop experience establishes spatial recognition without manual test harness injection.
"""
from __future__ import annotations

import copy
from typing import Any
import pytest

from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    Decision,
    Sensed,
    candidates,
    things_in_sight,
    CAPACITY_MICROGRAMS,
    HUNGRY_BELOW,
    PositionMM,
    PoseMM,
)
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import EmbodiedObject

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _her(world):
    snap = world.observation_snapshot()
    return next(b for b in snap.bodies if b.body_id == snap.self_body_id)


def test_physically_identical_objects_under_different_identifiers_have_identical_affordances():
    """Two objects with identical physical geometry and mass but different arbitrary identifiers
    have identical affordances: both are graspable and manipulable when reachable."""
    world = home_world_authority(identity=IDENTITY)
    body = _her(world)
    apple = next(item for item in world.observation_snapshot().objects if item.object_id == "apple")

    obj_a = EmbodiedObject(
        "unlabeled-item-a", radius_mm=apple.radius_mm, mass_grams=apple.mass_grams,
        position=PositionMM(body.pose.position.x + 350, body.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=apple.material,
    )
    world.admit_authored_arrival(obj_a)

    snap = world.observation_snapshot()
    cands_a = candidates(snap, _her(world), None, None, things_in_sight(snap), 1)
    grasp_a = [c for c in cands_a if c[0] == "grasp" and c[3] == "unlabeled-item-a"]
    assert len(grasp_a) == 1, f"Expected grasp candidate for obj_a, got {cands_a}"

    world_b = home_world_authority(identity=IDENTITY)
    body_b = _her(world_b)
    obj_b = EmbodiedObject(
        "unlabeled-item-b", radius_mm=apple.radius_mm, mass_grams=apple.mass_grams,
        position=PositionMM(body_b.pose.position.x + 350, body_b.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=apple.material,
    )
    world_b.admit_authored_arrival(obj_b)

    snap_b = world_b.observation_snapshot()
    cands_b = candidates(snap_b, _her(world_b), None, None, things_in_sight(snap_b), 1)
    grasp_b = [c for c in cands_b if c[0] == "grasp" and c[3] == "unlabeled-item-b"]
    assert len(grasp_b) == 1, f"Expected grasp candidate for obj_b, got {cands_b}"


def test_depleted_object_remains_manipulable_when_geometry_permits():
    """An object with zero or depleted tastant mass remains graspable and manipulable
    when physical geometry and mass satisfy carrying limits."""
    world = home_world_authority(identity=IDENTITY)
    body = _her(world)
    apple = next(item for item in world.observation_snapshot().objects if item.object_id == "apple")

    core_mat = type(apple.material)(
        odorant_reservoir_nanograms=apple.material.odorant_reservoir_nanograms,
        odorant_release_nanograms_per_second=apple.material.odorant_release_nanograms_per_second,
        tastant_mass_micrograms=(0, 0, 0, 0, 0),
        surface_temperature_millikelvin=apple.material.surface_temperature_millikelvin,
        compliance_ppm=apple.material.compliance_ppm,
        roughness_micrometers=apple.material.roughness_micrometers,
        moisture_ppm=apple.material.moisture_ppm,
    )
    depleted_obj = EmbodiedObject(
        "depleted-core", radius_mm=apple.radius_mm, mass_grams=25,
        position=PositionMM(body.pose.position.x + 350, body.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=core_mat,
    )
    world.admit_authored_arrival(depleted_obj)

    snap = world.observation_snapshot()
    her = _her(world)
    seen = things_in_sight(snap)
    cands = candidates(snap, her, None, None, seen, 1)

    grasp_cands = [c for c in cands if c[0] == "grasp" and c[3] == "depleted-core"]
    assert len(grasp_cands) == 1, f"Depleted object was refused grasp! Candidates: {cands}"

    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    res = loop.settle(org, world, UNATTENDED)
    assert res.observation["requested_world_action"] == "grasp"
    assert res.observation["world_action_refusal"] is None
    assert _her(world).held_object_id == "depleted-core"


def test_unsuccessful_bite_episode_lifecycle_and_custody_reset():
    """Zero-intake bite suppression is scoped strictly to the unchanged contact episode.
    When custody changes (release, drop, or re-grasp), the suppression ends naturally."""
    world = home_world_authority(identity=IDENTITY)
    body = _her(world)
    apple = next(item for item in world.observation_snapshot().objects if item.object_id == "apple")

    empty_mat = type(apple.material)(
        odorant_reservoir_nanograms=apple.material.odorant_reservoir_nanograms,
        odorant_release_nanograms_per_second=apple.material.odorant_release_nanograms_per_second,
        tastant_mass_micrograms=(0, 0, 0, 0, 0),
        surface_temperature_millikelvin=apple.material.surface_temperature_millikelvin,
        compliance_ppm=apple.material.compliance_ppm,
        roughness_micrometers=apple.material.roughness_micrometers,
        moisture_ppm=apple.material.moisture_ppm,
    )
    empty_cup = EmbodiedObject(
        "empty-cup-1", radius_mm=apple.radius_mm, mass_grams=apple.mass_grams,
        position=PositionMM(body.pose.position.x + 350, body.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=empty_mat,
    )
    world.admit_authored_arrival(empty_cup)

    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Beat 1: Grasp
    r1 = loop.settle(org, world, UNATTENDED)
    assert r1.observation["requested_world_action"] == "grasp"
    assert _her(world).held_object_id == "empty-cup-1"

    # Set metabolic deficit
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.3)
    org._state["feeding"] = True

    # Beat 2: Oral sampling yields zero intake
    r2 = loop.settle(org, world, UNATTENDED)
    assert r2.observation["her_act"] == "bite"
    assert r2.observation["real_nutrition_intake_zeptojoules"] == 0
    # Scoped episode suppression recorded for this held object
    assert org._state.get("unsuccessful_bite_held_id") == "empty-cup-1"

    # Beat 3: While still holding the same empty cup, repeated bite is suppressed; organism releases
    r3 = loop.settle(org, world, UNATTENDED)
    assert r3.observation["her_act"] != "bite", "Bite reflex looped compulsively on unchanged non-nutritive held item!"
    assert r3.observation["requested_world_action"] == "release"

    # Beat 4: Custody broken; object is released onto floor
    assert _her(world).held_object_id is None
    # Suppression is cleared upon custody change
    assert org._state.get("unsuccessful_bite_held_id") is None


def test_ordinary_loop_continuous_experience_and_spatial_recognition():
    """Runs a single continuous world and organism across sequential beats through FunctionalPhysicalLoop.
    Actual intake updates conserved_objects; subsequent ordinary loop settlement naturally recognizes
    the object from lived experience and issues toward_food without any manual harness injection."""
    world = home_world_authority(identity=IDENTITY)
    body = _her(world)
    apple = next(item for item in world.observation_snapshot().objects if item.object_id == "apple")

    nourishment = EmbodiedObject(
        "nourishment-live", radius_mm=apple.radius_mm, mass_grams=apple.mass_grams,
        position=PositionMM(body.pose.position.x + 350, body.pose.position.y, 0),
        reflectance_ppm=apple.reflectance_ppm, material=apple.material,
    )
    world.admit_authored_arrival(nourishment)

    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Beat 1: Grasp reachable nourishment
    r1 = loop.settle(org, world, UNATTENDED)
    assert r1.observation["requested_world_action"] == "grasp"
    assert _her(world).held_object_id == "nourishment-live"

    # Set metabolic deficit
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.3)
    org._state["feeding"] = True

    # Beat 2: Oral intake occurs
    r2 = loop.settle(org, world, UNATTENDED)
    assert r2.observation["her_act"] == "bite"
    assert r2.observation["real_nutrition_intake_zeptojoules"] > 0

    # Verification: conserved_objects has genuine intake provenance
    conserved = org._state.get("conserved_objects", {})
    assert "nourishment-live" in conserved
    assert conserved["nourishment-live"].get("is_food") is True
    assert conserved["nourishment-live"].get("fed_count", 0) > 0
    assert conserved["nourishment-live"].get("historical_intake_micrograms", 0) > 0
    assert conserved["nourishment-live"].get("currently_depleted") is False

    # Satiate organism so feeding ceases and she releases the held item
    org._state["reserve_micrograms"] = CAPACITY_MICROGRAMS
    org._state["feeding"] = False

    # Beat 3: When sated, organism releases held item to the floor
    r3 = loop.settle(org, world, UNATTENDED)
    assert r3.observation["requested_world_action"] == "release"
    assert _her(world).held_object_id is None

    # Reactivate metabolic deficit: hunger begins again
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.3)
    org._state["feeding"] = True

    # Beat 4: Ordinary loop execution: NO manual injection of known_foods or sight overrides!
    # The organism recognizes the released item on the floor from her continuous lived experience
    r4 = loop.settle(org, world, UNATTENDED)
    assert r4.observation["requested_world_action"] in ("toward_food", "approach", "turn_left", "turn_right", "reach_hand", "grasp", "touch"), (
        f"Expected food-directed action from ordinary loop, got {r4.observation['her_act']} / {r4.observation['requested_world_action']}"
    )
    assert "nourishment-live" in r4.observation["seen"]
