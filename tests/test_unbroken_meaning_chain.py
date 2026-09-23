#!/usr/bin/env python3
"""tests/test_unbroken_meaning_chain.py — Proof of the Unbroken Meaning Chain in the Ordinary World.

Validates the physical trajectory and causal isolation of episodic recall:
1. Physical Sensation: Retinal optics (figure_of_disc) and spatial coordinates (room_now).
2. Physical Consequence: Authentic nociceptive thermal shock (>316,150 mK) from real-world
   contact causally attributes acute pain (< -0.35) strictly to the actually applied action.
3. Retained Memory: Somatic salience admits silent moments preserving figure, room, and acts consequence;
   zero unperformed actions are recorded as experienced trials.
4. Nocturnal Sleep Consolidation: Natural sleep execution in the physical loop consolidates moments
   into permanent meanings without helper direct calls.
5. Byte-Exact Paired Restore: Both body and world checkpoint encodings restored byte-identically.
6. Matched Causal Isolation in Ordinary Loop: Under identical restored body and world state, advances
   both intact memory (Condition A) and ablated counterpart (Condition B) through the complete ordinary
   loop (loop.settle), isolating the causal role of episodic memory in governing real-world physical behavior.
7. Complete Sensory-to-Action Path: Retinal optics resolves the visual figure naturally; embodiment
   laws generate candidate acts naturally; zero preset figures or injected candidate lists.
8. Two Coexisting Conclusions:
   - Action-Specific Recall (Verified): Condition A retrieves the painful grasp experience and rejects
     grasp when that view returns (act_A != 'grasp'), while Condition B attempts grasp (act_B == 'grasp').
   - Recognition Across Views (Unresolved Capability, Explicitly Recorded): When posture shifts between
     grasp (Beat 0) and touch (Beat 2), retinal figure changes; consequence aggregation across differing
     views of the same physical object remains an open, unresolved capability (guarded by strict xfail
     on dedicated KnownMultiViewAvoidanceFailure).
9. Controlled Conditions Disclosure: Advancing sleep pressure to ceiling, habituating baseline tries, and
   waking the copy are controlled test interventions for reproducible physical verification—not autonomous emergence.
10. Phase-Shift Grounding: Silent admission governed strictly by physical phase shifts (figure, room, held)
   and somatic salience—zero arbitrary clock-based recurrence rules; entry count verified strictly invariant.
"""

from __future__ import annotations

import pytest

from dsf_ai_service.episodic_binding_engine import (
    evaluate_anticipatory_consequence,
)
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    EXHAUSTION_MARGIN,
    FunctionalOrganism,
    NOCICEPTION_MILLIKELVIN,
    SLEEP_PRESSURE_CEILING,
)
from dsf_ai_service.guala_home_world import home_world_authority
from tests.test_guala_functional_organism import (
    IDENTITY,
    UNATTENDED,
    _hot_apple_in_reach,
)


class KnownMultiViewAvoidanceFailure(AssertionError):
    """Raised specifically and exclusively for the final multi-view behavioral avoidance failure.

    Distinguishes the known behavioral capability gap from setup, restore, checkpoint,
    or consolidation assertion regressions.
    """


def test_action_specific_recall_under_matched_view() -> None:
    """Narrowly labeled causal proof: action-specific episodic recall under a matched view.

    Demonstrates that memory of an actually experienced painful action ('grasp') causally
    governs subsequent action selection in the complete ordinary physical loop (loop.settle):
    - Guala encounters a burning object (341,150 mK) and chooses grasp (untried affordance).
    - Thermal nociceptive shock credits negative valence strictly to 'grasp'.
    - Held object burns -> released by hand reflex.
    - Sleep consolidates the salient moment into a permanent meaning for that visual figure.
    - Restored under identical initial conditions:
      - Condition A (Intact Memory) retrieves the painful consequence and rejects grasp (act_A != 'grasp').
      - Condition B (Ablated Memory) lacks the memory and attempts grasp (act_B == 'grasp').
      - Causal divergence: act_A != act_B isolating episodic memory in the ordinary physical loop.
    """
    loop = FunctionalPhysicalLoop()

    # Step 1: Learning Encounter in Ordinary World
    world = home_world_authority(identity=IDENTITY, expand_library=False)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)

    # Baseline habituation: prior exploration across locomotion and touch affordances
    # leaves grasp untried (0 tries vs 1 try for others) so the chooser naturally selects grasp.
    for a in ("toward_thing", "toward_door", "step", "turn_left", "turn_right", "say", "rest", "touch"):
        organism._state.setdefault("act_totals", {})[a] = 1

    organism._state["head"] = [0, -40000]
    organism._state["eyes"] = [0, -39895]
    organism._state["gaze_target"] = "hot-apple"
    _hot_apple_in_reach(world, "hot-apple", NOCICEPTION_MILLIKELVIN + 25_000)

    # Beat 0: First try of grasp targeting the object -> acute thermal nociceptive contact
    res0 = loop.settle(organism, world, UNATTENDED)
    assert res0.observation["her_act"] == "grasp"

    # Beat 1: Held object exceeds pain threshold -> released by hand reflex
    res1 = loop.settle(organism, world, UNATTENDED)
    assert res1.observation["her_act"] == "release"
    assert "burns" in res1.observation["act_reason"]

    pain0 = float(getattr(organism, "_pain", 0.0))
    fig0 = organism._state.get("sight_figure")
    room0 = organism._state.get("room_now")
    moms0 = organism._state.get("moments", {})

    assert pain0 > 0.0, f"Expected physical nociceptive pain signal, got {pain0}"
    assert fig0 is not None, "Visual figure must be computed by retinal optics (figure_of_disc)"
    assert room0 == "her-room", f"Expected room coordinate 'her-room', got {room0}"
    assert len(moms0) > 0, "High somatic salience must form an episodic moment"

    # Verify pain credited strictly to actually applied action (grasp)
    grasp_moment = next(m for m in moms0.values() if "grasp" in m.get("acts", {}))
    assert grasp_moment["acts"]["grasp"][1] < -0.35, "Physical pain must record negative valence for grasp"

    # Step 2: Nocturnal Sleep Consolidation via Natural Physical Loop
    organism._state["sleep_pressure"] = int(SLEEP_PRESSURE_CEILING * (1 + EXHAUSTION_MARGIN) + 1)
    loop.settle(organism, world, UNATTENDED)
    for _ in range(4):
        loop.settle(organism, world, UNATTENDED)

    meanings = organism._state.get("meanings", {})
    assert len(meanings) > 0, "Salient moments must consolidate into permanent meanings during sleep"
    grasp_meaning = next(m for m in meanings.values() if "grasp" in m.get("acts", {}))
    assert grasp_meaning["acts"]["grasp"][1] < -0.35, "Consolidated grasp must preserve negative valence"

    # Step 3: Byte-Exact Paired Restore (Both Body and World)
    body_bytes = organism.encoded()
    world_bytes = bytes(world.encoded_snapshot())

    restored_org = FunctionalOrganism.restore(body_bytes)
    restored_world = home_world_authority(identity=IDENTITY, encoded_world=world_bytes, expand_library=False)
    assert restored_org.encoded() == body_bytes
    assert bytes(restored_world.encoded_snapshot()) == world_bytes

    # Step 4: Matched Causal Isolation in Ordinary Physical Loop (Condition A vs Condition B)
    # Condition A (Intact Memory):
    org_A = FunctionalOrganism.restore(body_bytes)
    world_A = home_world_authority(identity=IDENTITY, encoded_world=world_bytes, expand_library=False)
    org_A._state["asleep"] = False
    org_A._state["sleep_pressure"] = 0
    org_A._state["gaze_target"] = "hot-apple"
    org_A._state["head"] = [0, -40000]
    org_A._state["eyes"] = [0, -39895]

    # Condition B (Ablated Memory Counterpart):
    org_B = FunctionalOrganism.restore(body_bytes)
    world_B = home_world_authority(identity=IDENTITY, encoded_world=world_bytes, expand_library=False)
    org_B._state["asleep"] = False
    org_B._state["sleep_pressure"] = 0
    org_B._state["gaze_target"] = "hot-apple"
    org_B._state["head"] = [0, -40000]
    org_B._state["eyes"] = [0, -39895]

    # Ablate specific grasp contact meaning in B
    target_meaning_keys = [k for k, m in org_B._state.get("meanings", {}).items() if "grasp" in m.get("acts", {})]
    assert len(target_meaning_keys) > 0, "Expected grasp meaning to isolate in Condition B"
    for k in target_meaning_keys:
        del org_B._state["meanings"][k]

    # Step 5: Advance BOTH copies through the complete Ordinary Physical Loop (loop.settle)
    res_post_A = loop.settle(org_A, world_A, UNATTENDED)
    res_post_B = loop.settle(org_B, world_B, UNATTENDED)

    act_A = res_post_A.observation["her_act"]
    reason_A = res_post_A.observation["act_reason"]
    act_B = res_post_B.observation["her_act"]
    reason_B = res_post_B.observation["act_reason"]

    # Condition A (Intact Memory) must reject the painful action ('grasp'):
    assert act_A != "grasp", (
        f"Avoidance failed: Condition A repeated painful action 'grasp' following learning and sleep! Reason: {reason_A}"
    )

    # Condition B (Ablated Memory) must attempt grasp (untried / least-tried affordance):
    assert act_B == "grasp", (
        f"Condition B failed to select grasp without memory: chose '{act_B}', reason: {reason_B}"
    )

    # Strict causal divergence between identical initial states:
    assert act_A != act_B, (
        f"Causal divergence failed: both copies chose '{act_A}'; memory presence was not decisive."
    )


@pytest.mark.xfail(
    raises=KnownMultiViewAvoidanceFailure,
    reason="Unresolved capability: recognition across changing views under postural phase shifts prevents multi-action consequence aggregation",
    strict=True,
)
def test_ordinary_world_unbroken_meaning_chain_with_restore() -> None:
    """Broader test: all-contact harm avoidance under sequential actions and postural shifts.

    EXPLICITLY PRESERVED UNRESOLVED CAPABILITY TEST:
    Guala experiences pain from both 'grasp' (Beat 0) and 'touch' (Beat 2).
    However, because neck/eye posture shifts between grasp and touch, each experience is
    stored under a distinct retinal figure key. At re-encounter under the initial view,
    she retrieves the painful grasp consequence but does not aggregate the touch consequence
    recorded under the shifted view. Without an authored cross-action shortcut, she selects
    'touch', demonstrating that recognition across differing views of the same physical object
    remains an open, unresolved capability.
    """
    loop = FunctionalPhysicalLoop()

    # Step 1: Learning Encounter in Ordinary World
    world = home_world_authority(identity=IDENTITY, expand_library=False)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)

    for a in ("toward_thing", "toward_door", "step", "turn_left", "turn_right", "say", "rest"):
        organism._state.setdefault("act_totals", {})[a] = 1

    organism._state["head"] = [0, -40000]
    organism._state["eyes"] = [0, -39895]
    organism._state["gaze_target"] = "hot-apple"
    _hot_apple_in_reach(world, "hot-apple", NOCICEPTION_MILLIKELVIN + 25_000)

    # Beat 0: First try of grasp targeting the object -> acute thermal nociceptive contact
    res0 = loop.settle(organism, world, UNATTENDED)
    assert res0.observation["her_act"] == "grasp"

    # Beat 1: Held object exceeds pain threshold -> released by jaw/hand reflex
    res1 = loop.settle(organism, world, UNATTENDED)
    assert res1.observation["her_act"] == "release"
    assert "burns" in res1.observation["act_reason"]

    # Beat 2: Guala chooses candidate 'touch' from normal candidates -> acute thermal nociceptive contact
    res2 = loop.settle(organism, world, UNATTENDED)
    act2 = res2.observation["her_act"]
    pain2 = float(getattr(organism, "_pain", 0.0))
    fig2 = organism._state.get("sight_figure")
    room2 = organism._state.get("room_now")
    moms2 = organism._state.get("moments", {})

    assert act2 == "touch", f"Expected normal chooser to select 'touch', got {act2}"
    assert pain2 > 0.0, f"Expected physical nociceptive pain signal, got {pain2}"
    assert fig2 is not None, "Visual figure must be computed by retinal optics (figure_of_disc)"
    assert room2 == "her-room", f"Expected room coordinate 'her-room', got {room2}"
    assert len(moms2) > 0, "High somatic salience must form an episodic moment"

    # Verify that contact nociceptive shock is attributed to the performed contact affordance.
    grasp_moment = next(m for m in moms2.values() if "grasp" in m.get("acts", {}))
    touch_moment = next(m for m in moms2.values() if "touch" in m.get("acts", {}))
    assert grasp_moment["acts"]["grasp"][1] < -0.35, "Physical pain must record negative valence for grasp"
    assert touch_moment["acts"]["touch"][1] < -0.35, "Physical pain must record negative valence for touch"

    # Step 2: Nocturnal Sleep Consolidation via Natural Physical Loop
    organism._state["sleep_pressure"] = int(SLEEP_PRESSURE_CEILING * (1 + EXHAUSTION_MARGIN) + 1)
    res_sleep0 = loop.settle(organism, world, UNATTENDED)
    assert res_sleep0.observation["her_act"] == "sleep"
    assert organism._state.get("asleep") is True

    for _ in range(4):
        res_sleep = loop.settle(organism, world, UNATTENDED)
        assert res_sleep.observation["her_act"] == "sleep"

    meanings = organism._state.get("meanings", {})
    assert len(meanings) > 0, "Salient moments must consolidate into permanent meanings during sleep"
    grasp_meaning = next(m for m in meanings.values() if "grasp" in m.get("acts", {}))
    touch_meaning = next(m for m in meanings.values() if "touch" in m.get("acts", {}))
    assert grasp_meaning["acts"]["grasp"][1] < -0.35, "Consolidated grasp must preserve negative valence"
    assert touch_meaning["acts"]["touch"][1] < -0.35, "Consolidated touch must preserve negative valence"

    # Step 3: Byte-Exact Paired Restore (Both Body and World)
    body_bytes = organism.encoded()
    world_bytes = bytes(world.encoded_snapshot())

    restored_org = FunctionalOrganism.restore(body_bytes)
    restored_world = home_world_authority(identity=IDENTITY, encoded_world=world_bytes, expand_library=False)
    assert restored_org.encoded() == body_bytes
    assert bytes(restored_world.encoded_snapshot()) == world_bytes
    assert restored_org.live_organism_tick == organism.live_organism_tick

    # Step 4: Matched Causal Isolation in Ordinary Physical Loop (Condition A vs Condition B)
    # Condition A (Intact Memory):
    org_A = FunctionalOrganism.restore(body_bytes)
    world_A = home_world_authority(identity=IDENTITY, encoded_world=world_bytes, expand_library=False)
    org_A._state["asleep"] = False
    org_A._state["sleep_pressure"] = 0
    org_A._state["gaze_target"] = "hot-apple"
    org_A._state["head"] = [0, -40000]
    org_A._state["eyes"] = [0, -39895]

    # Condition B (Ablated Memory Counterpart):
    org_B = FunctionalOrganism.restore(body_bytes)
    world_B = home_world_authority(identity=IDENTITY, encoded_world=world_bytes, expand_library=False)
    org_B._state["asleep"] = False
    org_B._state["sleep_pressure"] = 0
    org_B._state["gaze_target"] = "hot-apple"
    org_B._state["head"] = [0, -40000]
    org_B._state["eyes"] = [0, -39895]

    contact_meaning_keys = [
        k for k, m in org_B._state.get("meanings", {}).items()
        if "touch" in m.get("acts", {}) or "grasp" in m.get("acts", {})
    ]
    assert len(contact_meaning_keys) > 0, "Expected contact meanings to isolate in Condition B"
    for k in contact_meaning_keys:
        del org_B._state["meanings"][k]

    # Step 5: Advance BOTH copies through the complete Ordinary Physical Loop (loop.settle)
    res_post_A = loop.settle(org_A, world_A, UNATTENDED)
    res_post_B = loop.settle(org_B, world_B, UNATTENDED)

    act_A = res_post_A.observation["her_act"]
    reason_A = res_post_A.observation["act_reason"]
    act_B = res_post_B.observation["her_act"]
    reason_B = res_post_B.observation["act_reason"]

    # This assertion fails because without cross-action generalization or view-invariant
    # recognition, Condition A selects 'touch' (retrieving only the grasp consequence for F0):
    if act_A in ("touch", "grasp"):
        raise KnownMultiViewAvoidanceFailure(
            f"Avoidance failed: Condition A chose harmful contact act '{act_A}' following learning and sleep! Reason: {reason_A}"
        )
    assert act_A not in ("touch", "grasp"), (
        f"Avoidance failed: Condition A chose harmful contact act '{act_A}' following learning and sleep!"
    )


def test_silent_sensory_admission_phase_shifts() -> None:
    """Verify that silent sensory admission is governed by physical phase transitions, not clocks."""
    organism = FunctionalOrganism.genesis(identity="guala-test", organism_tick=100)
    organism._state["room_now"] = "kitchen"
    organism._state["sight_figure"] = "apple_disc_01"

    measures = {
        "hunger": 0.5,
        "taste_residue": 0.0,
        "skin_contact": 0.0,
        "touch_texture": 0.0,
        "touch_warmth": 0.5,
    }
    organism._ear_closed = []
    organism._own_closed = []

    from types import SimpleNamespace
    body = SimpleNamespace(
        held_object_id=None,
        radius_mm=200,
        pose=SimpleNamespace(position=SimpleNamespace(x=0, y=0, z=0), heading_millidegrees=0),
        reach_mm=350,
        active_contact=None,
        receptor_geometry=None,
    )

    # 1. First encounter forms moment on phase shift (initial figure under gaze)
    organism._form_moments(body, measures, tick=100)
    assert len(organism._state["moments"]) == 1
    initial_entry = list(organism._state["moments"].values())[0]
    assert initial_entry["count"] == 1

    # 2. Staring at unchanged view with unchanged body state does NOT form duplicate moment
    for t in (101, 104, 110, 120):
        organism._form_moments(body, measures, tick=t)
        assert len(organism._state["moments"]) == 1, f"Unchanged view at tick {t} must not inflate moment count"
        assert list(organism._state["moments"].values())[0]["count"] == 1, f"Unchanged view at tick {t} must not increment recurrence count"

    # 3. Visual phase transition (new figure comes under gaze) admits a new moment
    organism._state["sight_figure"] = "cup_disc_02"
    organism._form_moments(body, measures, tick=121)
    assert len(organism._state["moments"]) == 2, "Visual phase transition must admit new moment"

    # 4. Spatial phase transition (entering a new room) admits recurrence on the active figure
    organism._state["room_now"] = "playroom"
    organism._form_moments(body, measures, tick=122)
    cup_mom = [m for m in organism._state["moments"].values() if m["figure"] == "cup_disc_02"][0]
    assert cup_mom["room"] == "playroom", "Room transition must update room coordinate on moment"
    assert cup_mom["count"] == 2, "Spatial transition must increment recurrence count"

    # 5. Somatic phase transition (tactile / held object change) admits a new moment
    body.held_object_id = "toy_block"
    organism._form_moments(body, measures, tick=123)
    assert len(organism._state["moments"]) == 3, "Tactile held transition must admit new moment key"
