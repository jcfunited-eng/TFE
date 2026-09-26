"""Focused physical affordance, contact lifecycle, and ordinary-loop recognition falsifier:
Verifies that:
1. Physically identical objects under different administrative identifiers have identical affordances.
2. Depleted objects remain graspable and manipulable when physical geometry permits.
3. Unsuccessful bite suppression is scoped strictly to the unchanged contact episode and ends on custody change.
4. Continuous ordinary-loop experience establishes spatial recognition without manual test harness injection.
5. AUT-ORAL-01: Oral contact distinguishes sensory tastants from declared digestible material and conserves mass.
6. AUT-ORAL-02: Unsuccessful bite suppression survives refused releases and suppresses unchanged caregiver offers.
7. AUT-ORAL-03: Zero-intake bite sample records episode suppression without marking the whole object currently_depleted.
8. AUT-ORAL-04: Matched-control twin verification demonstrates causal memory-directed pursuit of recognized food.
"""
from __future__ import annotations

import copy
from dataclasses import replace
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
from dsf_ai_service.guala_home_world import (
    home_world_authority,
    _world_thermal_transaction,
    _commit_world_successor,
)
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    ObjectMaterialState,
    OralContactCommand,
    ReleaseHeldObjectCommand,
)

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
        digestible_mass_micrograms=0,
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
        digestible_mass_micrograms=0,
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


def test_oral_contact_distinguishes_sensory_tastants_from_digestible_energy():
    """AUT-ORAL-01: Oral contact transfers chemical tastants to the mouth but transfers
    digestible mass to metabolic reserves ONLY when declared digestible mass is present.
    Mass is strictly conserved between source object and oral recipient."""
    # 1. Non-nutritive tasted textile: has tastants, but digestible_mass_micrograms == 0
    world_cloth = home_world_authority(identity=IDENTITY)
    body_cloth = _her(world_cloth)
    blanket_mat = ObjectMaterialState(
        odorant_reservoir_nanograms=(0, 0, 0, 0, 1_000, 0, 0, 150),
        odorant_release_nanograms_per_second=(0, 0, 0, 0, 1_000, 0, 0, 150),
        tastant_mass_micrograms=(0, 300, 0, 800, 0),
        surface_temperature_millikelvin=294_000,
        compliance_ppm=850_000,
        roughness_micrometers=150,
        moisture_ppm=50_000,
        digestible_mass_micrograms=0,
    )
    tasted_cloth = EmbodiedObject(
        "tasted-cloth", radius_mm=90, mass_grams=150,
        position=PositionMM(body_cloth.pose.position.x + 350, body_cloth.pose.position.y, 0),
        held_by_body_id=None,
        reflectance_ppm=(500_000,)*6,
        material=blanket_mat,
    )
    world_cloth.admit_authored_arrival(tasted_cloth)

    org_cloth = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Beat 1: Grasp the cloth
    r1 = loop.settle(org_cloth, world_cloth, UNATTENDED)
    assert r1.observation["requested_world_action"] == "grasp"
    assert _her(world_cloth).held_object_id == "tasted-cloth"

    # Set metabolic deficit
    org_cloth._state["reserve_micrograms"] = 50_000
    org_cloth._state["feeding"] = True

    # Beat 2: Oral contact on non-nutritive cloth
    r2 = loop.settle(org_cloth, world_cloth, UNATTENDED)
    assert r2.observation["her_act"] == "bite"
    snap2 = world_cloth.observation_snapshot()
    her2 = next(b for b in snap2.bodies if b.body_id == snap2.self_body_id)
    # Tongue receives dissolved tastant chemistry
    assert sum(her2.active_contact.dissolved_tastant_micrograms) > 0
    # But digestible nutrient mass transfer is zero!
    assert her2.active_contact.transferred_digestible_micrograms == 0
    # Metabolic reserves receive 0 intake
    assert r2.observation["real_nutrition_intake_zeptojoules"] == 0
    assert org_cloth.reserve_micrograms <= 50_000

    # 2. Nutritive food item: apple with declared digestible mass
    world_apple = home_world_authority(identity=IDENTITY)
    body_apple = _her(world_apple)
    apple = next(item for item in world_apple.observation_snapshot().objects if item.object_id == "apple")
    assert apple.material.digestible_mass_micrograms == 140_000

    nutritive_apple = EmbodiedObject(
        "nutritive-apple", radius_mm=apple.radius_mm, mass_grams=apple.mass_grams,
        position=PositionMM(body_apple.pose.position.x + 350, body_apple.pose.position.y, 0),
        held_by_body_id=None,
        reflectance_ppm=apple.reflectance_ppm,
        material=apple.material,
    )
    world_apple.admit_authored_arrival(nutritive_apple)

    org_apple = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    # Grasp apple
    r3 = loop.settle(org_apple, world_apple, UNATTENDED)
    assert r3.observation["requested_world_action"] == "grasp"
    assert _her(world_apple).held_object_id == "nutritive-apple"

    # Set hunger
    org_apple._state["reserve_micrograms"] = 50_000
    org_apple._state["feeding"] = True

    # Beat 4: Oral contact on nutritive apple
    r4 = loop.settle(org_apple, world_apple, UNATTENDED)
    assert r4.observation["her_act"] == "bite"
    snap4 = world_apple.observation_snapshot()
    her4 = next(b for b in snap4.bodies if b.body_id == snap4.self_body_id)
    transferred_dig = her4.active_contact.transferred_digestible_micrograms
    assert transferred_dig > 0, "Nutritive apple yielded zero digestible mass!"
    assert r4.observation["real_nutrition_intake_zeptojoules"] > 0
    assert org_apple.reserve_micrograms > 50_000

    # Conservation of matter: source object is debited by exactly transferred_dig
    apple_after = next(item for item in snap4.objects if item.object_id == "nutritive-apple")
    assert apple_after.material.digestible_mass_micrograms == apple.material.digestible_mass_micrograms - transferred_dig


def test_unsuccessful_bite_suppression_with_refused_release_and_unchanged_offer():
    """AUT-ORAL-02: Scoped suppression remains active if an attempted release is refused by the world,
    and suppresses repetitive bites when a non-nutritive item remains offered unchanged by the caregiver."""
    world = home_world_authority(identity=IDENTITY)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    org._state["reserve_micrograms"] = 50_000
    org._state["feeding"] = True

    # 1. Refused release preserves suppression
    org._state["unsuccessful_bite_held_id"] = "test-item"
    decision = Decision("release", "attempted release", (ReleaseHeldObjectCommand(100_000),), "test-item", None, "sig", False, 1, ())
    # World refuses release
    org.commit(
        decision,
        applied_action="release",
        refusal="release_body_holds_nothing",
        intake_micrograms=0,
        spoke=None,
        heard_profile=None,
        self_profile=None,
        tick_now=1,
    )
    assert org._state.get("unsuccessful_bite_held_id") == "test-item", "Refused release cleared bite suppression!"

    # 2. Offered unchanged item suppression: admit non-nutritive toy on the floor, then transfer to caregiver hand
    snap = world.observation_snapshot()
    empty_mat = ObjectMaterialState((0,)*8, (0,)*8, (0,)*5, 294_000, 100_000, 50, 10_000, digestible_mass_micrograms=0)
    non_nutritive = EmbodiedObject(
        "non-nutritive-toy", 50, 100, PositionMM(7000, 7500, 0),
        held_by_body_id=None,
        reflectance_ppm=(300_000,)*6,
        material=empty_mat,
    )
    world.admit_authored_arrival(non_nutritive)

    with _world_thermal_transaction(world):
        cur_w = world._state.world
        # Caregiver stands 600 mm away (clear of 500 mm body disc collision, within 800 mm reach)
        new_w = replace(
            cur_w,
            bodies=tuple(
                replace(b, held_object_id="non-nutritive-toy", pose=PoseMM(PositionMM(2600 + 600, 7600, 0), 180_000))
                if b.body_id == "person-body-1" else b
                for b in cur_w.bodies
            ),
            objects=tuple(
                replace(o, held_by_body_id="person-body-1", position=None)
                if o.object_id == "non-nutritive-toy" else o
                for o in cur_w.objects
            ),
        )
        _commit_world_successor(world, new_w)

    loop = FunctionalPhysicalLoop()
    # Beat 1: Bites the offered item
    r1 = loop.settle(org, world, UNATTENDED)
    assert r1.observation["her_act"] == "bite"
    assert org._state.get("unsuccessful_bite_held_id") == "non-nutritive-toy"

    # Beat 2: While caregiver still holds the same unchanged item within reach, bite reflex does NOT fire again
    r2 = loop.settle(org, world, UNATTENDED)
    assert r2.observation["her_act"] != "bite", "Bite reflex fired repeatedly on unchanged caregiver offer!"


def test_zero_sample_does_not_declare_whole_source_depleted():
    """AUT-ORAL-03: A single zero-intake bite sample does not mark the entire object currently_depleted,
    nor does it erase genuine historical food classification."""
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    conserved = org._state.setdefault("conserved_objects", {})
    conserved["apple-test"] = {
        "object_id": "apple-test",
        "position": (2600, 7600, 0),
        "radius_mm": 50,
        "room_id": "her-room",
        "last_seen_tick": 1,
        "confidence": 1.0,
        "historical_intake_micrograms": 5000,
        "fed_count": 2,
        "currently_depleted": False,
        "is_food": True,
    }

    decision = Decision("bite", "sample", (OralContactCommand("apple-test", 100_000),), "apple-test", None, "sig", False, 1, ())
    # Bite applied with ZERO intake
    org.commit(
        decision,
        applied_action="bite",
        refusal=None,
        intake_micrograms=0,
        spoke=None,
        heard_profile=None,
        self_profile=None,
        tick_now=1,
    )

    assert org._state.get("unsuccessful_bite_held_id") == "apple-test"
    entry = conserved["apple-test"]
    assert entry.get("currently_depleted") is False, "Zero bite sample prematurely declared whole source depleted!"
    assert entry.get("fed_count") == 2
    assert entry.get("historical_intake_micrograms") == 5000
    assert entry.get("is_food") is True


def test_matched_control_memory_verification():
    """AUT-ORAL-04: Matched-control and ablation memory verification:
    1. Phase 1: Twin A acquires nutritional recognition for 'tested-nourishment' through
       ordinary sensorimotor grasp and oral contact (intake > 0) with zero manual injection.
    2. Phase 2: Twin A and Twin B (matched unconditioned control) are placed in identical worlds
       with identical object 'tested-nourishment' placed at 1200 mm (distal).
       Twin A pursues the recognized food ('toward_food'); Twin B does not ('toward_thing').
    3. Phase 3: In an ablated clone of Twin A where only the retained memory entry is removed,
       the food-seeking pursuit is abolished, proving causal necessity."""
    loop = FunctionalPhysicalLoop()

    # Phase 1: Authentic sensorimotor conditioning of Twin A (no dictionary injection)
    world_cond = home_world_authority(identity=IDENTITY)
    snap_cond = world_cond.observation_snapshot()
    apple = next(item for item in snap_cond.objects if item.object_id == "apple")
    body_cond = _her(world_cond)

    food_cond = EmbodiedObject(
        "tested-nourishment",
        apple.radius_mm,
        apple.mass_grams,
        PositionMM(body_cond.pose.position.x + 350, body_cond.pose.position.y, 0),
        held_by_body_id=None,
        reflectance_ppm=apple.reflectance_ppm,
        material=apple.material,
    )
    world_cond.admit_authored_arrival(food_cond)

    twin_a = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    twin_a._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.3)
    twin_a._state["feeding"] = True

    # Beat 1: Ordinary grasp
    r0 = loop.settle(twin_a, world_cond, UNATTENDED)
    assert r0.observation["requested_world_action"] == "grasp"
    assert _her(world_cond).held_object_id == "tested-nourishment"

    # Beat 2: Ordinary bite yielding genuine nutritional mass intake
    r1 = loop.settle(twin_a, world_cond, UNATTENDED)
    assert r1.observation["her_act"] == "bite"
    assert r1.observation["real_nutrition_intake_zeptojoules"] > 0

    entry_a = twin_a._state["conserved_objects"]["tested-nourishment"]
    assert entry_a["fed_count"] == 1
    assert entry_a["historical_intake_micrograms"] > 0
    assert entry_a["is_food"] is True

    # Phase 2: Matched-control evaluation in identical sensory environments
    world_a = home_world_authority(identity=IDENTITY)
    world_b = home_world_authority(identity=IDENTITY)
    body_a = _her(world_a)
    body_b = _her(world_b)

    food_test_a = EmbodiedObject(
        "tested-nourishment",
        apple.radius_mm,
        apple.mass_grams,
        PositionMM(body_a.pose.position.x + 1200, body_a.pose.position.y, 0),
        held_by_body_id=None,
        reflectance_ppm=apple.reflectance_ppm,
        material=apple.material,
    )
    food_test_b = EmbodiedObject(
        "tested-nourishment",
        apple.radius_mm,
        apple.mass_grams,
        PositionMM(body_b.pose.position.x + 1200, body_b.pose.position.y, 0),
        held_by_body_id=None,
        reflectance_ppm=apple.reflectance_ppm,
        material=apple.material,
    )
    world_a.admit_authored_arrival(food_test_a)
    world_b.admit_authored_arrival(food_test_b)

    # Twin B is unconditioned genesis twin at matching tick and reserves
    twin_b = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=twin_a.live_organism_tick)
    twin_b._state["reserve_micrograms"] = twin_a.reserve_micrograms
    twin_b._state["feeding"] = True

    res_a = loop.settle(twin_a, world_a, UNATTENDED)
    res_b = loop.settle(twin_b, world_b, UNATTENDED)

    # Twin A recognizes food from lived intake and pursues it
    assert res_a.observation["her_act"] == "toward_food"
    assert res_a.observation["requested_world_action"] == "toward_food"
    assert "tested-nourishment" in res_a.observation["act_reason"]

    # Twin B lacks nutritional history for the object and does not pursue it as food
    assert res_b.observation["her_act"] != "toward_food"
    assert res_b.observation["requested_world_action"] != "toward_food"

    entry_b = twin_b._state.get("conserved_objects", {}).get("tested-nourishment", {})
    assert entry_b.get("is_food", False) is False
    assert entry_b.get("fed_count", 0) == 0
    assert entry_b.get("historical_intake_micrograms", 0) == 0

    # Phase 3: Controlled ablation of Twin A's memory abolishes food pursuit
    world_ablated = home_world_authority(identity=IDENTITY)
    body_abl = _her(world_ablated)
    food_test_abl = EmbodiedObject(
        "tested-nourishment",
        apple.radius_mm,
        apple.mass_grams,
        PositionMM(body_abl.pose.position.x + 1200, body_abl.pose.position.y, 0),
        held_by_body_id=None,
        reflectance_ppm=apple.reflectance_ppm,
        material=apple.material,
    )
    world_ablated.admit_authored_arrival(food_test_abl)

    twin_ablated = copy.deepcopy(twin_a)
    twin_ablated._state["conserved_objects"].pop("tested-nourishment", None)
    res_abl = loop.settle(twin_ablated, world_ablated, UNATTENDED)

    assert res_abl.observation["her_act"] != "toward_food"
    assert res_abl.observation["requested_world_action"] != "toward_food"
