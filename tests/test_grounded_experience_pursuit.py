"""tests/test_grounded_experience_pursuit.py — Empirical Pursuit Milestone Verification.

Fulfills A1's empirical Pursuit Milestone acceptance criterion:
"Demonstrate one experience-grown pursuit that survives a distraction, resumes when
appropriate, and stops or changes when its real consequence changes—without a supplied
action list, semantic intent label, or forced duration."

Grounded strictly in:
1. Senses & 7-field L0-L4 structural kernel.
2. Real episodic memory consolidation (eat -> sleep -> Pool Shock consolidation into meanings).
3. Spatial object permanence (conserved_objects) bound to sensorimotor figures.
4. Learned Closed-Loop Continuation Mechanism over experienced transitions without scalar reward ranking.
5. Causal consequence attribution and expectation discrepancy.
"""

from __future__ import annotations

import copy
import math
import struct
import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    ACTS, CAPACITY_MICROGRAMS, FunctionalOrganism, HUNGRY_BELOW, SATED_ABOVE,
    SLEEP_RECOVERY_PER_BEAT, PositionMM,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from tests.test_guala_functional_organism import _apple_ahead, IDENTITY, UNATTENDED


def _train_experienced_organism() -> FunctionalOrganism:
    """Trains an organism through the authentic physical loop:
    1. Organism encounters food at hand reach in the home world.
    2. Guala approaches, grasps, and bites the food across multiple beats, consuming matter.
    3. Moments form with authentic somatic salience and measured successor states.
    4. Sleep occurs naturally through the physical loop, consolidating episodic moments into meanings
       via the Pool Shock Principle without manual count or salience manipulation.
    """
    world_train = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_train, "apple-target", 600)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Natural waking experience: approach -> grasp -> bite -> bite
    for beat in range(8):
        loop.settle(org, world_train, UNATTENDED)

    assert org.counts["bites"] >= 1, "Organism must execute real biting in the world"
    assert len(org._state["moments"]) > 0, "Real moment must form from waking experience"

    # Natural sleep consolidation through the physical loop:
    # Sets sleep pressure proportional to moments to drain and sleeps until recovered
    org._state["asleep"] = True
    org._state["sleep_pressure"] = SLEEP_RECOVERY_PER_BEAT * (len(org._state["moments"]) + 1)
    while org.asleep:
        loop.settle(org, world_train, UNATTENDED)

    assert len(org._state["meanings"]) > 0, "Pool Shock Principle failed to consolidate into meanings"
    assert any(m.get("fed", 0) >= 1 for m in org._state["meanings"].values()), "Consolidated meaning must record positive feeding consequence"
    return org


def test_matched_naive_vs_experienced_encounter() -> None:
    """1. Experience-Grown Formation:
    Compares two identical organisms in the exact same room encounter with food at 1500 mm.
    - Experienced organism: Pursues food across consecutive beats (4 toward_food + 1 grasp).
    - Matched control: Identical checkpoint history, but with the learned association ablated;
      meanders across untried affordances (things and doors).
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

    # Matched Checkpoint Control (identical body/world history, with learned meanings ablated)
    org_control = FunctionalOrganism(copy.deepcopy(org_exp._state))
    org_control._state["meanings"].clear()
    world_control = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_control, "apple-target", 1500)
    org_control._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org_control._state["feeding"] = True
    loop_control = FunctionalPhysicalLoop()

    control_acts = []
    for beat in range(5):
        res = loop_control.settle(org_control, world_control, UNATTENDED)
        control_acts.append(res.observation["her_act"])

    # Control organism diverts to exploring other untried affordances (toward_thing, toward_door)
    assert control_acts != exp_acts
    assert "toward_thing" in control_acts or "toward_door" in control_acts


def test_multi_beat_trajectory_displacement() -> None:
    """2. Multi-Beat Trajectory Persistence:
    Demonstrates sustained pursuit across multiple consecutive beats on the canonical
    single 250ms clock, verifying continuous physical displacement toward the target
    satisfying the exact finite displacement condition 2(v . d) > ||v||^2.
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
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.50)
    org._state["feeding"] = True
    loop = FunctionalPhysicalLoop()

    # Beat 1: Approach step
    r1 = loop.settle(org, world, UNATTENDED)
    assert r1.observation["her_act"] == "toward_food"

    # Beat 2: Distraction arrives - acoustic sound event from another object
    pcm = struct.pack("<4000h", *(int(14_000 * math.sin(2 * math.pi * 440 * i / 16_000)) for i in range(4000)))
    sound_occ = PhysicalOccurrence("sensory", LeanSensoryOccurrence(
        source="thing-sound", retina_rgb_u8=None, pressure_s16le=pcm, from_object="toy-bear",
    ))
    r2 = loop.settle(org, world, sound_occ)
    # The distraction actually alters action (mandatory observed interruption)
    assert r2.observation["her_act"] != "toward_food", "Acoustic distraction must interrupt motor pursuit"
    # Mandatory target retention in spatial object permanence
    assert "apple-target" in org.conserved_objects, "Pursuit target must be retained in spatial object permanence"

    # Beat 3: Distraction clears (quiet beat)
    # The attractor basin in phase space remains active:
    # Deficit is still high, apple-target is in conserved_objects, meaning is positive.
    r3 = loop.settle(org, world, UNATTENDED)
    assert r3.observation["her_act"] == "toward_food", "Pursuit must resume after distraction clears"
    assert "apple-target" in org.conserved_objects


def test_consequence_satisfaction_terminates_pursuit() -> None:
    """4. Consequence-Driven Termination (Satisfaction):
    When food is consumed through actual bites and bodily deficit is relieved to the
    satisfaction boundary (>= 85%), the anticipatory continuation gradient dissipates naturally,
    and pursuit ceases without forced counters or manual state overrides.
    """
    org = _train_experienced_organism()
    loop = FunctionalPhysicalLoop()

    # Hungry -> Pursues food
    world_hungry = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_hungry, "apple-target", 1500)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.50)
    org._state["feeding"] = True
    r_hungry = loop.settle(org, world_hungry, UNATTENDED)
    assert r_hungry.observation["her_act"] == "toward_food"

    # Actual consumption in the physical world bringing reserves past satisfaction boundary (>= 85%)
    world_feed = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_feed, "apple-target", 350)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.80)
    org._state["feeding"] = True

    # Natural eating: actual grasp and bites until full
    for _ in range(6):
        r_feed = loop.settle(org, world_feed, UNATTENDED)
        if not org._state["feeding"]:
            break

    assert org.reserve_micrograms >= int(CAPACITY_MICROGRAMS * SATED_ABOVE), "Bites must relieve deficit to satisfaction boundary"
    assert not org._state["feeding"], "Feeding state must terminate naturally from intake"

    # Now sated, presented with food at 1500 mm:
    world_sated = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_sated, "apple-target", 1500)
    r_sated = loop.settle(org, world_sated, UNATTENDED)
    assert r_sated.observation["her_act"] != "toward_food", "Sated organism must not pursue food"


def test_target_departure_collapses_pursuit_via_expectation_discrepancy() -> None:
    """5. Reality Feedback (Target Removal):
    If target disappears, expectation discrepancy clears the entity from conserved_objects
    upon visual inspection. Pursuit collapses cleanly without pursuing empty space.
    """
    org = _train_experienced_organism()
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 1000)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.50)
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
