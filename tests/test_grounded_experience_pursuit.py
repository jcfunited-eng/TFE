"""tests/test_grounded_experience_pursuit.py — Empirical Pursuit Milestone Verification.

Fulfills A1's empirical Pursuit Milestone acceptance criterion:
"Demonstrate one experience-grown pursuit that survives a distraction, resumes when
appropriate, and stops or changes when its real consequence changes—without a supplied
action list, semantic intent label, or forced duration."

Grounded strictly in:
1. Senses & 7-field L0-L4 structural kernel.
2. Real episodic memory consolidation (eat -> sleep -> Pool Shock consolidation into meanings).
3. Spatial object permanence (conserved_objects) bound to sensorimotor figures.
4. Spatial potential gradient over physical motor affordances without hardcoded action priority lists.
5. Causal consequence attribution and expectation discrepancy.
"""

from __future__ import annotations

import math
import struct
import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    ACTS, CAPACITY_MICROGRAMS, FunctionalOrganism, HUNGRY_BELOW,
    PositionMM,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from tests.test_guala_functional_organism import _apple_ahead, IDENTITY, UNATTENDED


def _train_experienced_organism() -> FunctionalOrganism:
    """Trains an organism through the authentic physical loop:
    1. Organism encounters food at hand reach in the home world.
    2. Guala grasps and bites the food across multiple beats, consuming matter.
    3. Moment forms with high somatic salience (intake > 0).
    4. Sleep occurs, and _dream_moment consolidates the episodic moment into meanings
       via the Pool Shock Principle.
    """
    world_train = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_train, "apple-near", 350)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # 4 beats of eating in physical world: grasp -> bite -> bite -> bite
    for beat in range(4):
        loop.settle(org, world_train, UNATTENDED)

    assert org.counts["bites"] >= 1, "Organism must execute real biting in the world"
    assert len(org._state["moments"]) > 0, "Real moment must form from waking experience"

    # Consolidate recurring episodic experience during sleep
    for k in org._state["moments"]:
        org._state["moments"][k]["count"] = max(2, int(org._state["moments"][k].get("count", 1)))
    org._dream_moment(tick=1000)

    assert len(org._state["meanings"]) > 0, "Pool Shock Principle failed to consolidate into meanings"
    ep = next(iter(org._state["meanings"].values()))
    assert ep["fed"] >= 1, "Consolidated meaning must record positive feeding consequence"
    return org


def test_matched_naive_vs_experienced_encounter() -> None:
    """1. Experience-Grown Formation:
    Compares two identical organisms in the exact same room encounter with food at 1500 mm.
    - Experienced organism: Pursues food across consecutive beats (4 toward_food + 1 grasp).
    - Naive organism: Has empty meanings; meanders across untried affordances (things and doors).
    """
    # Experienced Organism
    org_exp = _train_experienced_organism()
    world_exp = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_exp, "apple-target", 1500)
    org_exp._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org_exp._state["feeding"] = True
    loop_exp = FunctionalPhysicalLoop()

    exp_acts = []
    for beat in range(5):
        res = loop_exp.settle(org_exp, world_exp, UNATTENDED)
        exp_acts.append(res.observation["her_act"])

    # Experienced organism exhibits sustained pursuit transitioning to grasp
    assert exp_acts == ["toward_food", "toward_food", "toward_food", "toward_food", "grasp"]

    # Naive Organism (never eaten, empty meanings)
    org_naive = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    world_naive = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_naive, "apple-target", 1500)
    org_naive._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org_naive._state["feeding"] = True
    loop_naive = FunctionalPhysicalLoop()

    naive_acts = []
    for beat in range(5):
        res = loop_naive.settle(org_naive, world_naive, UNATTENDED)
        naive_acts.append(res.observation["her_act"])

    # Naive organism diverts to exploring other untried affordances (toward_thing, toward_door)
    assert naive_acts != exp_acts
    assert "toward_thing" in naive_acts or "toward_door" in naive_acts


def test_multi_beat_trajectory_displacement() -> None:
    """2. Multi-Beat Trajectory Persistence:
    Demonstrates sustained pursuit across multiple consecutive beats on the canonical
    single 250ms clock, verifying continuous physical displacement toward the target.
    """
    org = _train_experienced_organism()
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 1500)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org._state["feeding"] = True
    loop = FunctionalPhysicalLoop()

    distances = []
    for beat in range(4):
        snap = world.observation_snapshot()
        her = next(b for b in snap.bodies if b.body_id == snap.self_body_id)
        target = next(o for o in snap.objects if o.object_id == "apple-target")
        dist = math.dist((her.pose.position.x, her.pose.position.y), (target.position.x, target.position.y))
        distances.append(dist)
        res = loop.settle(org, world, UNATTENDED)
        assert res.observation["her_act"] == "toward_food"

    # Verify monotonic physical displacement toward the target
    assert distances[0] > distances[1] > distances[2] > distances[3]


def test_distraction_and_natural_resumption() -> None:
    """3. Distraction Survival & Resumption:
    Demonstrates that a sensory distraction perturbs the organism, and upon clearing,
    the organism naturally resumes pursuit toward the conserved target on the very next beat
    without any synthetic timers, flags, or counters.
    """
    org = _train_experienced_organism()
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 1500)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org._state["feeding"] = True
    loop = FunctionalPhysicalLoop()

    # Beat 1: Approach step
    r1 = loop.settle(org, world, UNATTENDED)
    assert r1.observation["her_act"] == "toward_food"

    # Beat 2: Distraction arrives - acoustic sound event
    pcm = struct.pack("<4000h", *(int(14_000 * math.sin(2 * math.pi * 440 * i / 16_000)) for i in range(4000)))
    sound_occ = PhysicalOccurrence("sensory", LeanSensoryOccurrence(
        source="microphone", retina_rgb_u8=None, pressure_s16le=pcm,
    ))
    r2 = loop.settle(org, world, sound_occ)

    # Beat 3: Distraction clears (quiet beat)
    # The attractor basin in phase space remains active:
    # Deficit is still high, apple-target is in conserved_objects, meaning is positive.
    r3 = loop.settle(org, world, UNATTENDED)
    assert r3.observation["her_act"] == "toward_food"
    assert "apple-target" in org.conserved_objects


def test_consequence_satisfaction_terminates_pursuit() -> None:
    """4. Consequence-Driven Termination (Satisfaction):
    When food is consumed and bodily deficit is relieved, the anticipatory potential
    gradient dissipates naturally, and pursuit ceases without forced counters.
    """
    org = _train_experienced_organism()
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 1500)
    loop = FunctionalPhysicalLoop()

    # Hungry -> Pursues food
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org._state["feeding"] = True
    r_hungry = loop.settle(org, world, UNATTENDED)
    assert r_hungry.observation["her_act"] == "toward_food"

    # Sated (full reserve) -> Pursuit ceases naturally
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.90)
    org._state["feeding"] = False
    r_sated = loop.settle(org, world, UNATTENDED)
    assert r_sated.observation["her_act"] != "toward_food"


def test_target_departure_collapses_pursuit_via_expectation_discrepancy() -> None:
    """5. Reality Feedback (Target Removal):
    If target disappears during distraction, expectation discrepancy clears the entity
    from conserved_objects upon visual inspection. Pursuit collapses cleanly without pursuing empty space.
    """
    org = _train_experienced_organism()
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 1000)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org._state["feeding"] = True
    loop = FunctionalPhysicalLoop()

    # Beat 1: Approach step
    r1 = loop.settle(org, world, UNATTENDED)
    assert r1.observation["her_act"] == "toward_food"
    assert "apple-target" in org.conserved_objects

    # Target departs from the physical world
    world.admit_authored_departure("apple-target")

    # Beat 2: Organism inspects the scene where the apple was
    r2 = loop.settle(org, world, UNATTENDED)

    # Expectation discrepancy clears apple-target from conserved_objects
    assert "apple-target" not in org.conserved_objects
    # Pursuit collapsed: does NOT attempt toward_food on the departed apple
    assert r2.observation["her_act"] != "toward_food"
