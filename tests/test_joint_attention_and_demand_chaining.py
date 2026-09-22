"""Test Cognitive Asset 5: Social Joint Attention & Combinatorial Demand Phrasing.

Validates:
1. Caregiver gaze vector raycasting intersection with environmental entities.
2. Social joint attention: Guala aligns retinal gaze and head with caregiver's focus.
3. Combinatorial demand chaining: consecutive two-beat emission under hunger / joint attention.
4. Reinforcement credit on demand fulfillment.
"""

from __future__ import annotations

import math
import os
import time
import pytest

# Daylight override so world illumination is invariant
os.environ.setdefault("GUALA_SOLAR_UTC_OVERRIDE", str(int(time.time()) - int(time.time()) % 86_400 + 13 * 3_600))

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    project_caregiver_gaze_ray,
    SYLLABLE_DRIVES,
    CAPACITY_MICROGRAMS,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    SECOND_BODY_PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def _turn_caregiver(world, heading_mdeg: int) -> None:
    snapshot = world.observation_snapshot()
    cg = next(b for b in snapshot.bodies if b.body_id != snapshot.self_body_id)
    cmd = world.prepare_port_command(
        port_id=SECOND_BODY_PORT_ID,
        command_payload=encode_command(MoveCommand(PoseMM(cg.pose.position, heading_mdeg), 250_000)),
        causal_intent_receipt_sha256="cc" * 32,
        expected_revision=snapshot.revision,
    )
    with world.prepared_action_visibility_transaction(cmd):
        world.commit_prepared_action(cmd)


def test_caregiver_gaze_ray_projection() -> None:
    """The caregiver's 3D heading ray intersects objects lying in its forward gaze cone."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()
    cg = next(b for b in snapshot.bodies if b.body_id != snapshot.self_body_id)

    # 1. Heading 180 degrees (West, into room): Ray intersects the desk
    res_180 = project_caregiver_gaze_ray(PoseMM(cg.pose.position, 180_000), snapshot)
    assert res_180 is not None
    assert res_180[0] == "desk"

    # 2. Heading 135 degrees (North-West): Ray intersects toy-bear
    res_135 = project_caregiver_gaze_ray(PoseMM(cg.pose.position, 135_000), snapshot)
    assert res_135 is not None
    assert res_135[0] == "toy-bear"

    # 3. Heading 60 degrees (North-East, into hallway): Ray intersects mailbox
    res_60 = project_caregiver_gaze_ray(PoseMM(cg.pose.position, 60_000), snapshot)
    assert res_60 is not None
    assert res_60[0] == "mailbox"

    # 4. Heading 270 degrees (South, towards empty wall): No object in focal cone
    res_270 = project_caregiver_gaze_ray(PoseMM(cg.pose.position, 270_000), snapshot)
    assert res_270 is None


def test_joint_attention_orienting_saccade() -> None:
    """When the caregiver looks at an object, Guala locks joint attention onto it."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Default caregiver heading 180000 -> points at desk
    loop.settle(organism, world, UNATTENDED)
    assert organism.joint_attention_target == "desk"

    # Turn caregiver to 135000 -> points at toy-bear
    _turn_caregiver(world, 135_000)
    loop.settle(organism, world, UNATTENDED)
    assert organism.joint_attention_target == "toy-bear"


def test_combinatorial_demand_chaining_emission() -> None:
    """Under hunger or joint attention, Guala executes a consecutive 2-beat vocal demand chain."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=10)
    loop = FunctionalPhysicalLoop()

    # Step 1: Caregiver at 180000 looks at desk, establishing joint attention
    res1 = loop.settle(organism, world, UNATTENDED)
    assert organism.joint_attention_target == "desk"

    # Test immediate successor articulation when pending_chain is populated
    organism._state["pending_chain"] = ["dah0"]
    res2 = loop.settle(organism, world, UNATTENDED)

    # Must emit the chained syllable on the subsequent beat
    assert res2.observation["her_act"] == "say"
    chosen = organism._state.get("last_chosen", {})
    assert chosen.get("act") == "say"
    assert organism._state.get("last_said") == "dah0"


def test_syntactic_chain_credit_reinforcement() -> None:
    """When a demand chain is fulfilled by caregiver contact/intake, both syllables receive credit."""
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=50)
    
    # Register a demand chain that was just spoken
    organism._state["last_demand_chain"] = ["bah0", "dah0", 50, "desk"]
    
    # Simulate commit of a successful intake or contact
    from dsf_ai_service.guala_functional_organism import Decision
    dec = Decision("say", "combinatorial chain demand successor: dah0", (), None, SYLLABLE_DRIVES["dah0"], "s1 s2 s3 s4 s5", False, 1, ())
    
    organism.commit(
        dec,
        applied_action="bite",
        refusal=None,
        intake_micrograms=50_000,
        contact_fraction=0.8,
        spoke=None,
        heard_profile=None,
        self_profile=None,
        tick_now=organism.live_organism_tick,
    )
    
    # Verify that the demand chain transition bah0 -> dah0 received credit
    speech = organism._state.get("speech", {})
    matched_ctx = [k for k in speech if ":bah0" in k]
    assert len(matched_ctx) > 0, "Transition context from bah0 must exist"
    assert "dah0" in speech[matched_ctx[0]]["syllables"], "dah0 must receive credit under bah0 transition"
    assert speech[matched_ctx[0]]["syllables"]["dah0"][1] > 0.0, "Credit must be positive"
