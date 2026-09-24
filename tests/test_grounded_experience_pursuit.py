"""tests/test_grounded_experience_pursuit.py — Empirical Pursuit Milestone Verification.

Acceptance falsifiers for A1's empirical Pursuit Milestone (not a certification):
"Demonstrate one experience-grown pursuit that survives a distraction, resumes when
appropriate, and stops or changes when its real consequence changes—without a supplied
action list, semantic intent label, or forced duration."

Grounded strictly in:
1. The ordinary sensorimotor loop (not a proof of full joint-field cognition).
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
    4. Sleep is deliberately induced in this fixture; consolidation and wake then
       execute through the ordinary physical loop. No moment counts or salience
       are altered. This does NOT establish autonomous circadian sleep onset.
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

    # Controlled sleep induction (explicit test intervention, not natural onset).
    # The ordinary loop performs consolidation and recovery until she wakes.
    org._state["asleep"] = True
    org._state["sleep_pressure"] = SLEEP_RECOVERY_PER_BEAT * (len(org._state["moments"]) + 1)
    while org.asleep:
        loop.settle(org, world_train, UNATTENDED)

    assert all("body" not in entry.get("transitions", {}) for entry in org._state["meanings"].values()), (
        "Passive sleep/rest intervals were counted as physical motor trials"
    )
    assert len(org._state["meanings"]) > 0, "Pool Shock Principle failed to consolidate into meanings"
    assert any(m.get("fed", 0) >= 1 for m in org._state["meanings"].values()), "Consolidated meaning must record positive feeding consequence"
    return org


def test_matched_naive_vs_experienced_encounter() -> None:
    """Learned continuation must cause pursuit, not baseline food exploration.

    Both branches start at the SAME body/world checkpoint BEFORE either acts.
    Only the new continuation relations are ablated in the control. Existing
    meanings, scores, action history, senses, and bodily need stay identical.
    """
    org_exp = _train_experienced_organism()
    world_exp = home_world_authority(identity=IDENTITY)
    _apple_ahead(world_exp, "apple-target", 1500)
    # Declared initial condition, identical in both branches (not a learned result).
    org_exp._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.20)
    org_exp._state["feeding"] = True
    body_bytes = org_exp.encoded()
    org_exp = FunctionalOrganism.restore(body_bytes)
    world_bytes = bytes(world_exp.encoded_snapshot())
    org_control = FunctionalOrganism.restore(body_bytes)
    world_control = home_world_authority(identity=IDENTITY, encoded_world=world_bytes)
    assert org_control.encoded() == body_bytes
    assert bytes(world_control.encoded_snapshot()) == world_bytes

    # Remove only the relations whose causal effect this test claims to prove.
    for entry in org_control._state["meanings"].values():
        entry.pop("transitions", None)
        entry.pop("consequences", None)
        entry.pop("motor_transition", None)
        entry.pop("episode_tail", None)
    expected_control = copy.deepcopy(org_exp._state)
    for entry in expected_control["meanings"].values():
        entry.pop("transitions", None)
        entry.pop("consequences", None)
        entry.pop("motor_transition", None)
        entry.pop("episode_tail", None)
    assert org_control._state == expected_control

    exp_acts, control_acts, exp_reasons = [], [], []
    for _ in range(5):
        result_a = FunctionalPhysicalLoop().settle(org_exp, world_exp, UNATTENDED)
        result_b = FunctionalPhysicalLoop().settle(org_control, world_control, UNATTENDED)
        exp_acts.append(result_a.observation["her_act"])
        control_acts.append(result_b.observation["her_act"])
        exp_reasons.append(result_a.observation["act_reason"])
        # Every lived successor must survive a real cold JSON checkpoint.
        org_exp = FunctionalOrganism.restore(org_exp.encoded())
        org_control = FunctionalOrganism.restore(org_control.encoded())

    assert any(reason.startswith("learned continuation") for reason in exp_reasons), (
        "No learned continuation executed; baseline exploration is not pursuit proof. "
        f"experienced={exp_acts}, control={control_acts}, reasons={exp_reasons}"
    )
    assert exp_acts != control_acts, (
        f"Removing continuation relations did not change behavior: {exp_acts}"
    )

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
    # The retained experience is still available. This checks observed resumption,
    # not the existence of a continuous physical attractor basin.
    r3 = loop.settle(org, world, UNATTENDED)
    assert r3.observation["her_act"] == "toward_food", "Pursuit must resume after distraction clears"
    assert "apple-target" in org.conserved_objects


def test_consequence_satisfaction_terminates_pursuit() -> None:
    """Actual bites, in one continuing world, must cross the satiety boundary.

    Initial reserves and the initial feeding phase are controlled setup. Neither
    reserves nor the world is replaced after the first observed action.
    """
    org = _train_experienced_organism()
    loop = FunctionalPhysicalLoop()
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 1500)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * 0.80)
    org._state["feeding"] = True
    starting_reserves = org.reserve_micrograms
    starting_bites = org.counts["bites"]
    first = loop.settle(org, world, UNATTENDED)
    assert first.observation["her_act"] == "toward_food"
    # Finite TEST budget, never an organism stopping rule.
    for _ in range(12):
        result = loop.settle(org, world, UNATTENDED)
        org = FunctionalOrganism.restore(org.encoded())
        if not org._state["feeding"]:
            break

    assert org.counts["bites"] > starting_bites
    assert org.reserve_micrograms > starting_reserves
    assert org.reserve_micrograms >= int(CAPACITY_MICROGRAMS * SATED_ABOVE)
    assert not org._state["feeding"], "Real intake did not end feeding"
    after = loop.settle(org, world, UNATTENDED)
    assert not after.observation["act_reason"].startswith("learned continuation")
    assert after.observation["her_act"] != "toward_food"
    assert not org._state["feeding"]

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


def test_moving_successor_cold_checkpoint_and_next_interval() -> None:
    """A real motor command must not leak a Python object into durable state."""
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "opaque-target", 600)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    result = FunctionalPhysicalLoop().settle(org, world, UNATTENDED)
    assert any(result.observation["actual_root_motion"][1:]), "A physical move must execute"
    before_tick = org.live_organism_tick
    encoded = org.encoded()
    restored = FunctionalOrganism.restore(encoded)
    restored_world = home_world_authority(identity=IDENTITY, encoded_world=bytes(world.encoded_snapshot()))
    assert restored.encoded() == encoded
    FunctionalPhysicalLoop().settle(restored, restored_world, UNATTENDED)
    assert restored.live_organism_tick == before_tick + 1
    assert FunctionalOrganism.restore(restored.encoded()).encoded() == restored.encoded()


def test_sleep_retains_actual_predecessors_without_extra_trials() -> None:
    """Real world training, ordinary consolidation, unchanged trial evidence.

    Sleep onset is controlled setup. Neither its memory inputs nor consequences
    are injected. This proves retention, not view-invariant recognition.
    """
    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 600)
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()
    for _ in range(8):
        loop.settle(org, world, UNATTENDED)
    before = copy.deepcopy({
        key: entry for key, entry in org._state["moments"].items()
        if "motor_transition" in entry
    })
    approach = [
        key for key, entry in before.items()
        if entry["motor_transition"]["action"] == "toward_food"
    ]
    assert approach
    assert all(before[key]["count"] == 1 and before[key]["salience"] == 0.0 for key in approach)
    org._state["asleep"] = True
    org._state["sleep_pressure"] = SLEEP_RECOVERY_PER_BEAT * (len(org._state["moments"]) + 1)
    while org.asleep:
        loop.settle(org, world, UNATTENDED)
    meanings = org._state["meanings"]
    assert all(key in meanings for key in approach), "Experienced approach was discarded during sleep"
    for key, entry in before.items():
        if key in meanings:
            assert meanings[key] == entry, "Sleep changed the actual trial or its evidence"
    assert all(entry.get("motor_transition", {}).get("action") != "body" for entry in meanings.values())
    restored = FunctionalOrganism.restore(org.encoded())
    assert restored.encoded() == org.encoded()


def test_retention_requires_actual_contiguous_links_and_preserves_distinctions() -> None:
    """Isolated law falsifier, not an organism behavior or learning proof."""
    from dsf_ai_service.episodic_binding_engine import retained_episode_keys
    def trial(key, tick, before, after, previous=None, target="physical-custody"):
        return {"count": 1, "tick": tick + 1, "salience": 0.0, "motor_transition": {
            "key": key, "start_tick": tick, "end_tick": tick + 1,
            "pre": before, "post": after, "previous": previous,
            "target": target, "action": "step", "refusal": None, "intake": 0,
        }}
    moments = {
        "a": trial("a", 1, "view-A", "view-B"),
        "b": trial("b", 2, "view-B", "view-C", "a"),
        "unrelated": trial("unrelated", 9, "view-A", "view-C"),
        "outcome": {"count": 2, "tick": 4, "salience": 0.3, "episode_tail": "b"},
    }
    untouched = copy.deepcopy(moments)
    assert retained_episode_keys(moments, "outcome") == ("outcome", "b", "a")
    assert moments == untouched
    for field, wrong in (("pre", "different-view"), ("start_tick", 8), ("target", "other-custody")):
        altered = copy.deepcopy(moments)
        altered["b"]["motor_transition"][field] = wrong
        assert retained_episode_keys(altered, "outcome") == ("outcome", "b")
    del moments["a"]
    assert retained_episode_keys(moments, "outcome") == ("outcome", "b")
    moments["outcome"]["count"] = 1
    assert retained_episode_keys(moments, "outcome") == ()


def test_retention_admits_whole_episode_at_mature_capacity_and_refuses_oversize() -> None:
    """Storage boundary falsifier; counts cannot exclude new real one-trial links."""
    from dsf_ai_service.episodic_binding_engine import bound_retained_episode
    old = {f"old-{i}": {"count": 20, "tick": i} for i in range(4)}
    new = {
        "outcome": {"count": 2, "tick": 10, "episode_tail": "motor"},
        "motor": {"count": 1, "tick": 9, "salience": 0.0,
                  "motor_transition": {"previous": None}},
    }
    before = copy.deepcopy(old)
    combined = {**old, **new}
    successor = bound_retained_episode(combined, set(new), 4)
    assert successor is not None and len(successor) == 4
    assert all(successor[k] == v for k, v in new.items())
    assert old == before
    assert bound_retained_episode(combined, set(new), 1) is None
    assert old == before and combined == {**before, **new}


def test_observed_subject_is_not_replaced_by_acted_target() -> None:
    """A looked-at A / acted-on B record cannot become an A-directed act."""
    from dsf_ai_service.episodic_binding_engine import find_supported_continuation
    record = {"key": "motor", "start_tick": 1, "end_tick": 2,
              "pre": "actual-cue", "post": "successor", "action": "touch",
              "target": "B", "observed_subject": "A", "previous": None,
              "refusal": None, "intake": 12}
    candidates = (("touch", "A", (), "A", None),)
    kwargs = dict(current_target_id="A", current_figure="measured-shape")
    assert find_supported_continuation("actual-cue", "feeding",
        {"motor": {"motor_transition": record}}, candidates, **kwargs) is None
    witnessed = {**record, "observed_subject": "B"}
    # Exact cue recurrence may support an experienced act only after the
    # original trial actually observed its acted target; IDs are not cue keys.
    assert find_supported_continuation("actual-cue", "feeding",
        {"motor": {"motor_transition": witnessed}}, candidates, **kwargs) == candidates[0]


def test_visible_encounter_retention_changes_matched_action() -> None:
    """Same-view causal proof, not gaze acquisition or a mature-body release proof.

    Initial head posture, test-world re-presentation, 80% recall reserves, and
    sleep onset are explicit controlled conditions. No perception, memory,
    action history, or chosen action is supplied by the fixture.
    """
    from dsf_ai_service.guala_functional_organism import (
        HEAD_PITCH_BOUND_MILLIDEGREES, HEAD_YAW_BOUND_MILLIDEGREES,
        _aim, _self_body, _target_point,
    )

    def aimed_posture(org, world):
        snap = world.observation_snapshot()
        body = _self_body(snap)
        point = _target_point(snap, body, "apple-target")
        assert point is not None
        yaw, pitch = _aim(body, point)
        assert abs(yaw) <= HEAD_YAW_BOUND_MILLIDEGREES
        assert abs(pitch) <= HEAD_PITCH_BOUND_MILLIDEGREES
        # Starting physical pose only; the real retina computes the evidence.
        org._state["head"] = [yaw, pitch]
        org._state["eyes"] = [0, 0]

    world = home_world_authority(identity=IDENTITY)
    _apple_ahead(world, "apple-target", 600)
    initial_world = bytes(world.encoded_snapshot())
    org = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    aimed_posture(org, world)
    loop = FunctionalPhysicalLoop()
    first = loop.settle(org, world, UNATTENDED)
    teaching_cue = org._state["pending_transition"]["pre_key"]
    assert org._state["sight_figure"] is not None, "Aimed encounter still has no visual figure"
    assert first.observation["her_act"] == "toward_food"
    for _ in range(7):
        loop.settle(org, world, UNATTENDED)
    assert org.counts["bites"] > 0

    org._state["asleep"] = True
    sleep_beats = len(org._state["moments"]) + 1
    org._state["sleep_pressure"] = SLEEP_RECOVERY_PER_BEAT * sleep_beats
    for _ in range(sleep_beats + 2):
        loop.settle(org, world, UNATTENDED)
        if not org.asleep:
            break
    assert not org.asleep
    approach = org._state["meanings"]["motor:1"]
    assert approach["count"] == 1 and approach["salience"] == 0
    assert approach["motor_transition"]["pre"] == teaching_cue

    # A controlled identical visual re-presentation, not a claim of autonomous
    # navigation back to this spot. Both branches have the same body/world.
    world_a = home_world_authority(identity=IDENTITY, encoded_world=initial_world)
    org._state["reserve_micrograms"] = int(CAPACITY_MICROGRAMS * .80)
    org._state["feeding"] = True
    aimed_posture(org, world_a)
    body_bytes = org.encoded()
    org_a = FunctionalOrganism.restore(body_bytes)
    org_b = FunctionalOrganism.restore(body_bytes)
    world_b = home_world_authority(identity=IDENTITY, encoded_world=initial_world)
    assert bytes(world_a.encoded_snapshot()) == bytes(world_b.encoded_snapshot())
    expected_b = copy.deepcopy(org_a._state)
    for state in (org_b._state, expected_b):
        for entry in state["meanings"].values():
            entry.pop("motor_transition", None)
            entry.pop("episode_tail", None)
    assert org_b._state == expected_b

    result_a = FunctionalPhysicalLoop().settle(org_a, world_a, UNATTENDED)
    result_b = FunctionalPhysicalLoop().settle(org_b, world_b, UNATTENDED)
    print("visible encounter", {
        "teaching_cue": teaching_cue,
        "recall_cue": org_a._state["pending_transition"]["pre_key"],
        "retained_act": result_a.observation["her_act"],
        "control_act": result_b.observation["her_act"],
        "retained_reason": result_a.observation["act_reason"],
        "control_reason": result_b.observation["act_reason"],
    })
    assert org_a._state["pending_transition"]["pre_key"] == teaching_cue
    assert result_a.observation["act_reason"].startswith("learned continuation")
    assert result_a.observation["her_act"] != result_b.observation["her_act"]
    assert any(result_a.observation["actual_root_motion"][1:])
    assert FunctionalOrganism.restore(org_a.encoded()).encoded() == org_a.encoded()


def test_continuation_preserves_only_progressing_motor_alternatives() -> None:
    """Isolated geometry contract: not an independent learning proof."""
    from dsf_ai_service.episodic_binding_engine import find_supported_continuation
    from dsf_ai_service.substrate.embodiment_world import MoveCommand, PoseMM

    trial = {"key": "a", "start_tick": 1, "end_tick": 2,
             "pre": "visible-cue", "post": "near", "action": "step",
             "target": "T", "observed_subject": "T", "previous": None,
             "refusal": None, "intake": 0}
    outcome = {**trial, "key": "b", "start_tick": 2, "end_tick": 3,
               "pre": "near", "post": "fed", "action": "bite",
               "previous": "a", "intake": 12}
    meanings = {"a": {"motor_transition": trial}, "b": {"motor_transition": outcome}}
    forward = MoveCommand(PoseMM(PositionMM(300, 0, 0), 0), 250_000)
    sideways = MoveCommand(PoseMM(PositionMM(0, 300, 0), 0), 250_000)
    backward = MoveCommand(PoseMM(PositionMM(-300, 0, 0), 0), 250_000)
    original = ("step", "original", (forward, sideways, backward), "T", None)
    kwargs = dict(current_target_id="T", current_figure="actual-figure",
                  body_position=(0, 0, 0), target_positions={"T": (1000, 0, 0)})
    selected = find_supported_continuation("visible-cue", "feeding", meanings, (original,), **kwargs)
    assert selected == ("step", "original", (forward,), "T", None)
    assert selected[2][0] is forward
    assert original[2] == (forward, sideways, backward)
    away = ("step", "original", (sideways, backward), "T", None)
    assert find_supported_continuation("visible-cue", "feeding", meanings, (away,), **kwargs) is None
    assert find_supported_continuation("visible-cue", "feeding", meanings, (original,),
        **{**kwargs, "target_positions": {}}) is None
