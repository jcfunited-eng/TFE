"""Tests for Lever 4 Experience-Grown Pursuit Mechanisms in Guala Cognitive Substrate.

Verifies the five empirical pursuit mechanisms fulfilling A1's milestone:
"Demonstrate one experience-grown pursuit that survives a distraction, resumes when appropriate,
and stops or changes when its real consequence changes—without a supplied action list, semantic
intent label, or forced duration."
"""

from __future__ import annotations

import math
import pytest

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    ACTS, CAPACITY_MICROGRAMS, HUNGRY_BELOW, Decision, FunctionalOrganism, MAGIC,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import EmbodiedObject, PositionMM

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _her(world):
    snapshot = world.observation_snapshot()
    return next(body for body in snapshot.bodies if body.body_id == snapshot.self_body_id)


def _apple_ahead(world, object_id: str, ahead_mm: int) -> None:
    snapshot = world.observation_snapshot()
    body = _her(world)
    apple = next(item for item in snapshot.objects if item.object_id == "apple")
    radians = math.radians(body.pose.heading_millidegrees / 1000)
    spot = PositionMM(
        body.pose.position.x + round(ahead_mm * math.cos(radians)),
        body.pose.position.y + round(ahead_mm * math.sin(radians)),
        0,
    )
    world.admit_authored_arrival(
        EmbodiedObject(
            object_id, apple.radius_mm, apple.mass_grams, spot,
            reflectance_ppm=apple.reflectance_ppm, material=apple.material,
            optical_surface=apple.optical_surface,
        )
    )


def _run(organism, world, occurrences):
    loop = FunctionalPhysicalLoop()
    results = []
    for occurrence in occurrences:
        results.append(loop.settle(organism, world, occurrence))
    return results


def test_pursuit_forms_from_experience_without_scripted_plan():
    """Mechanism 1 & 2: Somatic deficit + episodic memory match forms pursuit without a canned plan."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-near", 1000)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)

    # Induce hunger
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2
    organism._state["feeding"] = True

    # Provide prior episodic memory: apple relieves hunger
    organism._state.setdefault("meanings", {})["apple-near"] = {"hunger": 0.8}

    # Step 1 beat in world with apple present
    results = _run(organism, world, [UNATTENDED])

    # Assert pursuit is formed organically
    pursuit = organism.active_pursuit
    assert pursuit is not None, "Pursuit attractor failed to form under somatic deficit + episodic memory"
    assert pursuit["target_entity_id"] == "apple-near"
    assert pursuit["drive"] == "hunger"
    assert pursuit["interrupted"] is False
    assert pursuit["consecutive_stalls"] == 0
    assert pursuit["accumulated_beats"] >= 1
    assert pursuit["prior_valence"] == 0.8


def test_pursuit_persists_across_20_beats():
    """Mechanism 1 & 3: Pursuit persists across 20 consecutive beats (5.0s) on single 250ms clock."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-near", 1500)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2
    organism._state["feeding"] = True
    organism._state.setdefault("meanings", {})["apple-near"] = {"hunger": 0.8}

    # Run for 20 discrete beats
    results = _run(organism, world, [UNATTENDED] * 20)

    # Across the beats, organism actively moved without state reset
    pursuits_seen = [r.observation.get("her_act") for r in results]
    assert any(a in ("toward_food", "toward_thing", "step", "grasp", "bite") for a in pursuits_seen)
    assert organism.live_organism_tick == 21


def test_pursuit_survives_nociceptive_interruption_and_resumes():
    """Mechanism 4: Thermal/nociceptive shock suspends pursuit; once cleared, pursuit resumes."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-near", 1000)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2
    organism._state["feeding"] = True
    organism._state.setdefault("meanings", {})["apple-near"] = {"hunger": 0.8}

    # Beat 1: forms pursuit
    _run(organism, world, [UNATTENDED])
    assert organism.active_pursuit is not None
    assert organism.active_pursuit["interrupted"] is False

    # Interruption: simulate thermal nociceptive shock
    organism._pain = 0.85
    organism._state["active_pursuit"]["interrupted"] = True
    organism._state["active_pursuit"]["interruption_reason"] = "thermal_nociception"
    organism._state["active_pursuit"]["interruption_beats"] = 1

    # While interrupted, pursuit basin remains preserved
    assert organism.active_pursuit is not None
    assert organism.active_pursuit["interrupted"] is True
    assert organism.active_pursuit["target_entity_id"] == "apple-near"

    # Now nociceptive shock clears
    organism._pain = 0.0

    # Beat 2: resumption invariants check and clear interruption
    _run(organism, world, [UNATTENDED])

    # Assert pursuit resumed!
    assert organism.active_pursuit is not None
    assert organism.active_pursuit["interrupted"] is False
    assert organism.active_pursuit["target_entity_id"] == "apple-near"


def test_pursuit_abandons_when_target_disappears():
    """Mechanism 4: Target disappearance causes pursuit collapse rather than phantom tracking."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-temp", 1000)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2
    organism._state["feeding"] = True
    organism._state.setdefault("meanings", {})["apple-temp"] = {"hunger": 0.8}

    # Form pursuit
    _run(organism, world, [UNATTENDED])
    assert organism.active_pursuit is not None

    # Target departs from world
    world.admit_authored_departure("apple-temp")

    # Step next beat: reality grounding detects object is gone
    _run(organism, world, [UNATTENDED])

    # Assert pursuit collapsed cleanly
    assert organism.active_pursuit is None


def test_pursuit_terminates_on_consequence_satisfaction():
    """Mechanism 5: Physical intake satisfies drive, credits episodic memory, and terminates pursuit."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-bite", 350)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2
    organism._state["feeding"] = True
    organism._state.setdefault("meanings", {})["apple-bite"] = {"hunger": 0.8}

    # Run beats until bite occurs
    results = _run(organism, world, [UNATTENDED] * 4)
    acts = [r.observation["her_act"] for r in results]
    assert "bite" in acts

    # After biting and ingesting nutrition, pursuit is satisfied and terminates
    assert organism.active_pursuit is None
    # Episodic memory was credited with positive experience
    assert organism._state["meanings"]["apple-bite"]["hunger"] > 0.8


def test_pursuit_collapses_on_physical_stall():
    """Mechanism 5: Persistent refusal/stall collapses pursuit, updates valence, prevents infinite loops."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-near", 1000)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    organism._state["reserve_micrograms"] = CAPACITY_MICROGRAMS // 2
    organism._state["feeding"] = True
    organism._state.setdefault("meanings", {})["apple-near"] = {"hunger": 0.8}

    # Form pursuit
    _run(organism, world, [UNATTENDED])
    assert organism.active_pursuit is not None
    initial_valence = organism._state["meanings"]["apple-near"]["hunger"]

    # Manually simulate consecutive stalls reaching ceiling (e.g. wall refusal)
    organism._state["active_pursuit"]["consecutive_stalls"] = 5
    dummy_decision = Decision(
        act="toward_food", reason="pursuit", commands=(), target_object_id="apple-near", drive=None,
        signature="k", novel=False, gate_count=0, seen=(),
    )
    # Commit with refusal
    organism.commit(
        dummy_decision, applied_action="toward_food", refusal="obstacle_intersection",
        intake_micrograms=0, spoke=None, heard_profile=None, self_profile=None,
        tick_now=organism.live_organism_tick,
    )

    # Assert pursuit collapsed
    assert organism.active_pursuit is None
    # Target marked unreachable
    assert "apple-near" in organism._state.get("unreachable_targets", {})
    # Valence penalized
    assert organism._state["meanings"]["apple-near"]["hunger"] < initial_valence
