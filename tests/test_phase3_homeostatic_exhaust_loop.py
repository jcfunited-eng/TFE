"""tests/test_phase3_homeostatic_exhaust_loop.py — Phase 3 Verification.

Verification Suite for WHOLE_BRAIN_SPECIFICATION.md Phase 3:
Physical Homeostatic Exhaust Cycle (The Vocal & Motor Valves).

1. Strained State Entry: Internal metabolic deficit or motor frustration causes P_k > B_k (S_UF <= 0).
2. Barrier Inhibition: R_rev_k > 0 and refusal feedback inhibits repeating failing motor actions
   (releases non-nutritive barriers/obstacles).
3. Structured Exhaust: Frustrated energy discharges through lowest-resistance plastic channels
   of the 1,024-node ternary matrix, exciting the airway vocal efferent actuators ('say').
4. Equilibrium Restoration: Actuation relieves somatic tension, returning P_k < B_k (S_UF > 0).

Zero Software Dictionaries | Pure Physical Potential & Yield Plasticity Dynamics
"""

import uuid
from dataclasses import replace
import pytest

from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    CAPACITY_MICROGRAMS,
    HUNGRY_BELOW,
    SYLLABLE_DRIVES,
    ONSETS,
    VOWELS,
    PITCHES_DECIHERTZ,
)
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_home_world import (
    home_world_authority,
    _world_thermal_transaction,
    _commit_world_successor,
)
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import (
    PoseMM,
    PositionMM,
)
from dsf_ai_service.substrate.ternary_multimodal_substrate import (
    TOTAL_NODES,
    SOMATIC_START,
    EFFERENT_START,
    EFFERENT_END,
)

IDENTITY_TEST = "4cc5e81b-a1b2-48d6-b222-e5b6cd926dd4"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_barrier_inhibition_releases_non_nutritive_held_obstacle():
    """Verifies that when Guala is hungry and holds a non-nutritive object
    (e.g., toy-blocks or an item whose bite previously failed), Barrier Inhibition
    immediately selects 'release' instead of deadlocking on repetitive bites."""
    world = home_world_authority(identity=IDENTITY_TEST)
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Induce metabolic hunger and record previous unsuccessful bite attempt
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.3)
    org._state["feeding"] = True
    org._state["unsuccessful_bite_held_id"] = "toy-blocks"

    # Authoritative reciprocal holding of non-nutritive toy
    w = world._state.world
    toy = next(o for o in w.objects if o.object_id == "toy-blocks")
    toy_held = replace(toy, position=None, held_by_body_id="guala-body-1")
    her = next(b for b in w.bodies if b.body_id == "guala-body-1")
    her_holding = replace(her, held_object_id="toy-blocks")
    new_w = replace(
        w,
        bodies=tuple(her_holding if b.body_id == "guala-body-1" else b for b in w.bodies),
        objects=tuple(toy_held if o.object_id == "toy-blocks" else o for o in w.objects),
    )
    with _world_thermal_transaction(world):
        _commit_world_successor(world, new_w)

    res = loop.settle(org, world, UNATTENDED)

    # Barrier Inhibition invariant: must release the non-nutritive held barrier
    assert res.observation["her_act"] == "release", f"Expected 'release' under barrier inhibition, got: {res.observation['her_act']}"
    assert "barrier inhibition" in str(res.observation.get("act_reason", ""))


def test_homeostatic_exhaust_cycle_triggers_under_strained_deficit():
    """Verifies that when metabolic deficit causes internal Pressure to exceed Breathing
    capacity (P_k > B_k -> S_UF <= 0) and motor affordances are blocked, the organism
    vents frustrated energy through the vocal valve ('say') and restores equilibrium."""
    world = home_world_authority(identity=IDENTITY_TEST)
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=20)
    loop = FunctionalPhysicalLoop()

    # Induce severe metabolic hunger
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org._state["feeding"] = True

    # Set up kernel state with high pressure P_k exceeding breathing B_k
    org._last_dsf_states = {
        "hunger": {
            "D_k": 0.85,
            "M_k": 0.05,
            "R_rev_k": 1.0,
            "U_star_k": 0.70,
            "C_k": 0.10,
            "P_k": 0.95,
            "B_k": 0.40,
            "S_UF": -0.55,  # Strained non-viable state
            "regime": "Expansion",
        }
    }

    res = loop.settle(org, world, UNATTENDED)

    # Invariant: Homeostatic exhaust cycle fires vocal valve ('say')
    assert res.observation["her_act"] == "say", f"Expected vocal exhaust 'say', got: {res.observation['her_act']} ({res.observation['act_reason']})"
    assert "homeostatic exhaust" in str(res.observation.get("act_reason", ""))
    assert res.observation.get("said_drive") is not None, "Vocal exhaust must carry acoustic airway drive parameters"


def test_plastic_conduction_shapes_exhaust_syllable():
    """Verifies that when specific plastic conductances have yielded in the 1,024-node
    ternary matrix between somatic distress and airway articulators (e.g. 'deh3'),
    the Homeostatic Exhaust Cycle discharges through those exact yielded channels."""
    world = home_world_authority(identity=IDENTITY_TEST)
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=50)
    loop = FunctionalPhysicalLoop()

    # Pre-condition: Carve a plastic conductance channel for 'deh3'
    # deh3: Onset 'd'=3, Vowel 'eh'=1, Pitch 3=3900 dHz (PITCHES_DECIHERTZ[3] = 3900)
    # Drive encoding is (pitch, vowel_idx, onset_idx)
    cue = [0] * TOTAL_NODES
    cue[SOMATIC_START:SOMATIC_START + 16] = [1] * 16
    eff = org._ternary_substrate.encode_dsf_and_efferents(
        dsf_vector=(0.9, 0.0, 1.0, 0.5, 0.0, 0.9, 0.4, -0.5),
        onset_idx=3,
        vowel_idx=1,
        pitch_idx=3,
    )
    cue[EFFERENT_START:EFFERENT_END] = eff

    # Yield plastic deformation into the matrix
    org._ternary_substrate.present_experience(cue)
    org._sync_ternary_substrate()

    # Induce strained state
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.25)
    org._state["feeding"] = True

    res = loop.settle(org, world, UNATTENDED)

    assert res.observation["her_act"] == "say"
    # Verify the resonant articulators match the learned plastic channel ('deh3')
    assert tuple(res.observation.get("said_drive", ())) == (PITCHES_DECIHERTZ[3], 1, 3), f"Expected 'deh3' drive, got: {res.observation.get('said_drive')}"


def test_live_playpen_confinement_exhaust_breaks_deadlock():
    """Verifies that inside the live physical world loop, when Guala is placed in
    the playpen while hungry, she does NOT get stuck in an infinite loop of biting
    the playpen rail. She drops the rail and discharges vocal exhaust."""
    world = home_world_authority(identity=IDENTITY_TEST)
    org = FunctionalOrganism.genesis(identity=IDENTITY_TEST, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Place Guala inside the playpen at (4200, 8800)
    w = world._state.world
    her = next(b for b in w.bodies if b.body_id == "guala-body-1")
    her_in_pen = replace(her, pose=PoseMM(PositionMM(4200, 8800, 0), 0))
    new_w = replace(w, bodies=tuple(her_in_pen if b.body_id == "guala-body-1" else b for b in w.bodies))
    with _world_thermal_transaction(world):
        _commit_world_successor(world, new_w)

    # Drain metabolic reserve to induce hunger
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.35)
    org._state["feeding"] = True

    acts_executed = []
    reasons = []

    # Step through 8 beats of live physics
    for beat in range(8):
        res = loop.settle(org, world, UNATTENDED)
        her_act = res.observation.get("her_act")
        act_reason = res.observation.get("act_reason")
        acts_executed.append(her_act)
        reasons.append(act_reason)

    # Invariant: Guala must not be deadlocked repeating 'bite' on the playpen
    bite_count = sum(1 for a in acts_executed if a == "bite")
    assert bite_count <= 1, f"Guala deadlocked biting playpen {bite_count} times: {acts_executed}"

    # Invariant: Homeostatic exhaust cycle must have fired vocal valve ('say')
    say_count = sum(1 for a in acts_executed if a == "say")
    assert say_count > 0, f"Expected vocal exhaust 'say' during confinement, got acts: {acts_executed}"
