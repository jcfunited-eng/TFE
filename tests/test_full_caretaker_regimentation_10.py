import math
import uuid
import pytest

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    PoseMM,
    PositionMM,
    MoveCommand,
    encode_command,
    ActionExecutionReceipt,
)
from dsf_ai_service.guala_caretaker_hand import (
    present_food,
    touch_her,
    material_impact_pcm,
    diurnal_thermal_reference_millikelvin,
    deictic_orientation_millidegrees,
)
from guala_caretaker.caretaker import (
    circadian_epoch,
    birdsong_blocks,
    TOUCH_GESTURES,
    MEAL_DELIVERY_CYCLE,
    TACTILE_OBJECTS,
    maybe_tv,
    maybe_stroll,
    maybe_read,
    maybe_playpen_challenge,
    maybe_ladder_challenge,
    maybe_feed,
    maybe_tactile_curriculum,
    maybe_housekeeping,
)


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """Isolate caretaker production log and state files to tmp_path for all tests,
    preventing test ticks and mock events from contaminating production caretaker.log."""
    import guala_caretaker.caretaker as ct
    monkeypatch.setattr(ct, "LOG", str(tmp_path / "test_caretaker.log"))
    monkeypatch.setattr(ct, "STATE", str(tmp_path / "test_state.json"))


def test_routine_1_high_chair_meal_variety(monkeypatch) -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # 1. Place in high chair via physical world action
    res = present_food(world, "high-chair-meal")
    assert res["presented"] is True
    applied_steps = [s for s in (res.get("steps") or []) if s.get("reason") == "applied"]
    assert any(s.get("operation") == "place_in_high_chair" for s in applied_steps)
    snap = world.observation_snapshot()
    her = next(b for b in snap.bodies if b.body_id == snap.self_body_id)
    assert her.pose.position.x == 3500
    assert her.pose.position.y == 1500
    assert snap.room_id == "kitchen"

    # 2. Release from high chair back to kitchen floor (seated-to-released lifecycle)
    res_release = present_food(world, "high-chair-release")
    assert res_release["presented"] is True
    snap_after_rel = world.observation_snapshot()
    her_rel = next(b for b in snap_after_rel.bodies if b.body_id == snap_after_rel.self_body_id)
    assert her_rel.pose.position.x == 2700
    assert her_rel.pose.position.y == 1500

    # 2b. Negative Case: Child not in high chair -> release refused (REG-A1-02)
    res_release_unseated = present_food(world, "high-chair-release")
    assert res_release_unseated["presented"] is False
    assert any(s.get("reason") == "child_not_in_high_chair" for s in res_release_unseated.get("steps", []))

    # 3. Multi-diet rotation
    assert "apple-delivery" in MEAL_DELIVERY_CYCLE
    assert "bread-delivery" in MEAL_DELIVERY_CYCLE
    assert "milk-delivery" in MEAL_DELIVERY_CYCLE

    # 4. Deliver bread and milk with face reach
    res_bread = present_food(world, "bread-delivery")
    assert res_bread["delivered"] is not None

    # 5. Gating check: high-chair placement occurs only when hungry and meal interval has elapsed
    st = {"meal_tick": 0}
    placed_calls = []

    def mock_present_envelope(item):
        placed_calls.append(item)
        return {
            "native_interval_count": 50,
            "observation": {
                "live_tick": 20_000,
                "last_occurrence": {
                    "native_tick": 20_000,
                    "caregiver_presentation": {
                        "object_id": item,
                        "presented": True,
                        "steps": [{"operation": item, "reason": "applied"}],
                    }
                }
            }
        }

    monkeypatch.setattr("guala_caretaker.caretaker.present_food", mock_present_envelope)

    # Negative Case: Not hungry (deficit below threshold) -> high-chair placement NOT called
    obs_not_hungry = {
        "live_tick": 20_000,
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [0, 1],
            "embodiment": {"bodies": [{"body_id": "guala-body-1", "pose": {"position": {"x_mm": 1000, "y_mm": 1000}}}], "self_body_id": "guala-body-1"},
            "tastant_remaining_micrograms": {},
        }
    }
    maybe_feed(obs_not_hungry, st)
    assert "high-chair-meal" not in placed_calls
    assert "high-chair-release" not in placed_calls

    # Positive Case 1: Verified hungry in MORNING_FOCUS -> high-chair placement and food delivery
    placed_calls.clear()
    st["meal_tick"] = 0
    obs_hungry = {
        "live_tick": 20_000,
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [8, 10],  # 80% deficit > HUNGRY_DEFICIT
            "embodiment": {"bodies": [{"body_id": "guala-body-1", "pose": {"position": {"x_mm": 1000, "y_mm": 1000}}}], "self_body_id": "guala-body-1"},
            "tastant_remaining_micrograms": {},
        }
    }
    maybe_feed(obs_hungry, st)
    assert "high-chair-meal" in placed_calls
    assert st.get("seated_for_meal") is True

    # Positive Case 2: Observed meal complete while seated in high chair -> high-chair release called
    placed_calls.clear()
    obs_seated_done = {
        "live_tick": 20_100,
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [0, 10],  # deficit resolved / satisfied
            "embodiment": {"bodies": [{"body_id": "guala-body-1", "pose": {"position": {"x_mm": 3500, "y_mm": 1500}}}], "self_body_id": "guala-body-1"},
            "tastant_remaining_micrograms": {},
        }
    }
    maybe_feed(obs_seated_done, st)
    assert "high-chair-release" in placed_calls
    assert st.get("seated_for_meal") is False

    # Positive Case 2b (Counterexample): Still-hungry child in high chair whose food left reach (REG-A1-02)
    # Delivered-but-uneaten: food was delivered, but child is NOT at mouth and STILL hungry
    placed_calls.clear()
    st["seated_for_meal"] = True
    st["food_delivered_for_meal"] = True
    obs_seated_still_hungry = {
        "live_tick": 20_150,
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [8, 10],  # 80% deficit (STILL hungry)
            "embodiment": {"bodies": [{"body_id": "guala-body-1", "pose": {"position": {"x_mm": 3500, "y_mm": 1500}}}], "self_body_id": "guala-body-1"},
            "tastant_remaining_micrograms": {},
        }
    }
    maybe_feed(obs_seated_still_hungry, st)
    assert "high-chair-release" in placed_calls
    assert st.get("seated_for_meal") is False
    assert st.get("meal_retry") is True  # Interrupted meal flags retry

    # Case 2c: Child seated in high chair during NIGHT_CONSOLIDATION -> safety release triggered (REG-A1-02)
    placed_calls.clear()
    st["seated_for_meal"] = True
    obs_night_seated = {
        "live_tick": 105_000,  # NIGHT_CONSOLIDATION epoch
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [8, 10],
            "embodiment": {"bodies": [{"body_id": "guala-body-1", "pose": {"position": {"x_mm": 3500, "y_mm": 1500}}}], "self_body_id": "guala-body-1"},
            "tastant_remaining_micrograms": {},
        }
    }
    maybe_feed(obs_night_seated, st)
    assert "high-chair-release" in placed_calls
    assert st.get("seated_for_meal") is False


def test_routine_2_tv_time_remote_gaze_alignment(monkeypatch) -> None:
    # Test geometric visibility evidence gating with real nested presentation envelope
    st = {}
    remote_cycled = []
    words = []

    def mock_tv_present(item):
        remote_cycled.append(item)
        ch = 1 if item == "tv-remote-cycle" else 0
        return {
            "native_interval_count": 60,
            "observation": {
                "last_occurrence": {
                    "caregiver_presentation": {
                        "object_id": item,
                        "presented": True,
                        "channel": ch,
                        "steps": [{"operation": item, "reason": "applied"}],
                    }
                }
            }
        }

    monkeypatch.setattr("guala_caretaker.caretaker.present_food", mock_tv_present)
    monkeypatch.setattr("guala_caretaker.caretaker.say_word", lambda word: words.append(word) or True)

    # Case A: Missing visual evidence (seen is None) -> demonstration withheld
    obs_missing = {
        "live_tick": 60_000,
        "last_occurrence": {"seen": None}
    }
    maybe_tv(obs_missing, st)
    assert len(remote_cycled) == 0

    # Case B: Television not in line-of-sight -> attention called, no remote cycle
    st["tv_next_tick"] = 0
    obs_not_seen = {
        "live_tick": 60_001,
        "last_occurrence": {"seen": ["bed", "toy-bear"]}
    }
    maybe_tv(obs_not_seen, st)
    assert len(remote_cycled) == 0
    assert "television" in words

    # Case C: Television verified in geometric sight -> remote cycle demonstrated with extracted channel
    st["tv_next_tick"] = 0
    obs_seen = {
        "live_tick": 60_002,
        "last_occurrence": {"seen": ["television", "sofa"]}
    }
    maybe_tv(obs_seen, st)
    assert "tv-remote" in remote_cycled
    assert "tv-remote-cycle" in remote_cycled

    # Case D: Failed remote presentation receipt aborts without recording story moment (REG-A1-03)
    st["tv_next_tick"] = 0
    st["daily_moments_presented"] = 0
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: {
        "observation": {"last_occurrence": {"caregiver_presentation": {"presented": False}}}
    })
    maybe_tv(obs_seen, st)
    assert st.get("daily_moments_presented") == 0

    # Case E: Terminal refusal with intermediate applied movement step (REG-A1-03)
    st["tv_next_tick"] = 0
    st["daily_moments_presented"] = 0
    calls_e = []
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: calls_e.append(item) or {
        "observation": {
            "last_occurrence": {
                "caregiver_presentation": {
                    "object_id": item,
                    "presented": False,
                    "steps": [{"operation": "move", "reason": "applied"}],
                }
            }
        }
    })
    maybe_tv(obs_seen, st)
    assert len(calls_e) == 1
    assert "tv-remote" in calls_e
    assert "tv-remote-cycle" not in calls_e
    assert st.get("daily_moments_presented") == 0


def test_routine_3_curriculum_variety_tactile(monkeypatch) -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    assert len(TACTILE_OBJECTS) >= 4
    assert "cup" in TACTILE_OBJECTS
    assert "stacking-rings" in TACTILE_OBJECTS
    assert "play-ball" in TACTILE_OBJECTS
    assert "toy-bear" in TACTILE_OBJECTS

    # Test material synthesis
    wood_pcm = material_impact_pcm("wood", intensity=0.8)
    assert len(wood_pcm) == 8000
    ceramic_pcm = material_impact_pcm("ceramic", intensity=0.7)
    assert len(ceramic_pcm) == 8000
    metal_pcm = material_impact_pcm("metal", intensity=0.85)
    assert len(metal_pcm) == 8000

    # Test receipt-gated tactile curriculum (REG-A1-03):
    # Case A: Refused presentation must NOT record modalities (even with applied move step)
    st = {"tactile_next_tick": 0, "daily_moments_presented": 0, "circadian_epoch": "MORNING_FOCUS"}
    obs_focus = {"live_tick": 20_000, "her_sleep": {"asleep": False}}
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: {
        "observation": {"last_occurrence": {"caregiver_presentation": {"presented": False, "steps": [{"operation": "move", "reason": "applied"}]}}}
    })
    maybe_tactile_curriculum(obs_focus, st)
    assert st.get("daily_moments_presented") == 0

    # Case B: Accepted presentation without physical contact records only visual & auditory (no tactile / proprioceptive)
    st["tactile_next_tick"] = 0
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: {
        "observation": {"last_occurrence": {"caregiver_presentation": {"presented": True, "steps": [{"operation": "present", "reason": "applied"}]}}}
    })
    maybe_tactile_curriculum(obs_focus, st)
    assert st.get("daily_moments_presented") == 1
    assert st.get("active_modalities_stimulated", {}).get("visual", 0) > 0
    assert st.get("active_modalities_stimulated", {}).get("auditory", 0) > 0
    assert st.get("active_modalities_stimulated", {}).get("tactile", 0) == 0
    assert st.get("active_modalities_stimulated", {}).get("proprioceptive", 0) == 0

    # Case C: Accepted presentation WITH skin contact evidence records tactile modality
    st["tactile_next_tick"] = 0
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: {
        "observation": {"last_occurrence": {"caregiver_presentation": {
            "presented": True,
            "contacts": [{"site": "palm", "pressure": 0.5}],
            "steps": [{"operation": "present", "reason": "applied"}]
        }}}
    })
    maybe_tactile_curriculum(obs_focus, st)
    assert st.get("active_modalities_stimulated", {}).get("tactile", 0) == 1


def test_routine_4_stroller_walk_and_sensory_field(monkeypatch) -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # 1. Stroller carriage delivery & physical excursion with child
    res_stroller = present_food(world, "stroller-carriage")
    assert res_stroller["presented"] is True
    applied_ops = [s.get("operation") for s in res_stroller.get("steps", []) if s.get("reason") == "applied"]
    assert "stroller_placement" in applied_ops
    assert "stroller_excursion" in applied_ops

    # 2. Assert child and stroller displacement: both must have successor coordinates in backyard
    snap_after = world.observation_snapshot()
    stroller_after = next(o for o in snap_after.objects if o.object_id == "stroller-carriage")
    her_after = next(b for b in snap_after.bodies if b.body_id == snap_after.self_body_id)
    assert stroller_after.position is not None
    assert stroller_after.position.y >= 10000, f"Stroller must be in backyard, got y={stroller_after.position.y}"
    assert her_after.pose.position.y >= 10000, f"Child must be in backyard, got y={her_after.pose.position.y}"

    # 3. Route refusal verification: when portal to backyard is missing, stroller excursion reports refusal
    from dataclasses import replace
    world_blocked = home_world_authority(identity=str(uuid.uuid4()))
    cur_w = world_blocked._state.world
    no_backyard_portals = tuple(p for p in cur_w.portals if "backyard" not in p.region_ids)
    from dsf_ai_service.guala_home_world import _commit_world_successor, _world_thermal_transaction
    with _world_thermal_transaction(world_blocked):
        _commit_world_successor(world_blocked, replace(cur_w, revision=cur_w.revision + 1, portals=no_backyard_portals))

    res_blocked = present_food(world_blocked, "stroller-carriage")
    assert res_blocked["presented"] is False
    assert any("refused" in str(s.get("reason", "")) for s in res_blocked.get("steps", []))

    # 4. Hand holding contact
    res_hand = present_food(world, "touch-hold-hand")
    assert res_hand["touched"] == "hold_hand"

    # 5. Birdsong acoustic field
    blocks = birdsong_blocks()
    assert len(blocks) >= 4
    for b in blocks[:4]:
        assert len(b) == 8000

    # 6. Partial outcome retention on child transport exception (REG-A1-05)
    world_exc = home_world_authority(identity=str(uuid.uuid4()))
    def fail_transport(*args, **kwargs):
        raise RuntimeError("simulated child transport barrier")
    monkeypatch.setattr(world_exc, "admit_authored_body_transport", fail_transport)
    res_partial = present_food(world_exc, "stroller-carriage")
    assert res_partial["presented"] is False
    reloc_steps = [s for s in res_partial.get("steps", []) if s.get("operation") == "stroller_relocation"]
    assert len(reloc_steps) == 1
    assert reloc_steps[0]["reason"] == "applied"
    assert reloc_steps[0]["stroller_pos"] == [6700, 11500]
    final_step = (res_partial.get("steps") or [])[-1]
    assert final_step.get("to") == "partial_stroller_only"
    assert final_step.get("stroller_pos") == [6700, 11500]


def test_routine_5_ladder_tool_affordance_challenge() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # 1. Successful demonstration: caregiver moves to backyard, faces elevated fruit, records applied receipt
    res = present_food(world, "ladder-challenge")
    assert res["presented"] is True
    applied = [s for s in res.get("steps", []) if s.get("reason") == "applied"]
    assert any(s.get("operation") == "ladder_demonstration" for s in applied)
    assert any(s.get("target") == "garden-apple" for s in applied)

    # 2. Truthful refusal when ladder is missing
    from dataclasses import replace
    no_ladder_objects = tuple(o for o in world.observation_snapshot().objects if o.object_id != "garden-ladder")
    cur_world = world._state.world
    new_world = replace(cur_world, revision=cur_world.revision + 1, objects=no_ladder_objects)
    from dsf_ai_service.guala_home_world import _commit_world_successor, _world_thermal_transaction
    with _world_thermal_transaction(world):
        _commit_world_successor(world, new_world)

    res_no_ladder = present_food(world, "ladder-challenge")
    assert res_no_ladder["presented"] is False
    assert any(s.get("reason") == "ladder_not_found" for s in res_no_ladder.get("steps", []))


def test_routine_6_playpen_containment_impedance() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # 1. Place in playpen at (2050, 6700)
    res_contain = present_food(world, "playpen-containment")
    assert res_contain["presented"] is True
    snap = world.observation_snapshot()
    her = next(b for b in snap.bodies if b.body_id == snap.self_body_id)
    assert her.pose.position.x == 2050
    assert her.pose.position.y == 6700
    assert snap.room_id == "her-room"

    # 2. Movement INSIDE playpen is permitted (interior step within 450mm radius)
    valid_step = PoseMM(PositionMM(2060, 6700, 0), her.pose.heading_millidegrees)
    prep_valid = world.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(valid_step, 100_000)),
        causal_intent_receipt_sha256="0" * 64,
        expected_revision=snap.revision,
    )
    assert not isinstance(prep_valid, ActionExecutionReceipt)
    world.discard_prepared_action(prep_valid)

    # 3. Stepping OUT of playpen hits boundary perimeter impedance and is rejected
    blocked_step = PoseMM(PositionMM(2500, 6700, 0), her.pose.heading_millidegrees)
    prep_blocked = world.prepare_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(blocked_step, 100_000)),
        causal_intent_receipt_sha256="1" * 64,
        expected_revision=snap.revision,
    )
    assert isinstance(prep_blocked, ActionExecutionReceipt)
    assert prep_blocked.reason == "move_path_intersects_object"


def test_routine_7_joint_clean_up_routine() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    res = present_food(world, "joint-clean-up")
    assert res["presented"] is True
    assert res["object_id"] == "joint-clean-up"
    # Unconditionally verify deictic orientation pointing step was recorded and applied
    steps = res.get("steps") or []
    pointing_steps = [s for s in steps if s.get("operation") == "point_to_stray"]
    assert len(pointing_steps) > 0, "Deictic pointing step must be unconditionally executed"
    assert pointing_steps[0]["reason"] == "applied"
    assert "heading" in pointing_steps[0]


def test_routine_8_lap_reading_stabilized_seating(monkeypatch) -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    lap = present_food(world, "touch-lap")
    assert lap["touched"] == "lap_hold"
    contacts = lap.get("contacts") or []
    sites = {c["site"] for c in contacts}
    assert "front-torso" in sites
    assert "left-shoulder" in sites
    assert "right-shoulder" in sites

    # Verify strict evening gate: reading is refused outside EVENING_CULTURE
    st = {"read_title_index": 1, "read_chapter": 2, "read_next_tick": 0}
    books_presented = []
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: books_presented.append(item) or {"presented": True})

    # Tick 20_000 is MORNING_FOCUS: must refuse to read despite saved chapter progress
    obs_morning = {"live_tick": 20_000, "her_sleep": {"asleep": False}}
    maybe_read(obs_morning, st)
    assert len(books_presented) == 0, "Reading must not proceed outside EVENING_CULTURE despite saved chapter"


def test_routine_9_affection_and_stress_recovery_hug() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # Playpen release delivers contingent recovery hug with applied receipt
    res_release = present_food(world, "playpen-release")
    assert res_release["presented"] is True
    steps = res_release.get("steps") or []
    assert any(s.get("operation") == "release_from_playpen" and s.get("reason") == "applied" for s in steps)
    assert any(s.get("operation") == "touch" and s.get("reason") == "applied" for s in steps)
    snap = world.observation_snapshot()
    her = next(b for b in snap.bodies if b.body_id == snap.self_body_id)
    assert her.pose.position.x == 2600
    assert her.pose.position.y == 6700

    # Diurnal thermal conduction
    temp_dawn = diurnal_thermal_reference_millikelvin(0)
    temp_midday = diurnal_thermal_reference_millikelvin(45_000)
    assert temp_dawn < temp_midday


def test_routine_10_diurnal_circadian_pacing_exclusivity(monkeypatch) -> None:
    # 1. 6 canonical epochs
    e0, _ = circadian_epoch(5_000)
    assert e0 == "DAWN_AWAKENING"
    e1, _ = circadian_epoch(20_000)
    assert e1 == "MORNING_FOCUS"
    e2, _ = circadian_epoch(45_000)
    assert e2 == "MIDDAY_STROLL"
    e3, _ = circadian_epoch(65_000)
    assert e3 == "AFTERNOON_CHALLENGE"
    e4, _ = circadian_epoch(85_000)
    assert e4 == "EVENING_CULTURE"
    e5, _ = circadian_epoch(105_000)
    assert e5 == "NIGHT_CONSOLIDATION"

    # 2. Comprehensive routine refusal verification during NIGHT_CONSOLIDATION:
    # None of the awake routines may run during night consolidation
    dispatched = []
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: dispatched.append(item) or {"presented": True})
    night_obs = {
        "live_tick": 105_000,
        "her_sleep": {"asleep": False},
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [9, 10],
            "tastant_remaining_micrograms": {"apple": 100_000},
            "seen": ["television"],
        }
    }
    st = {}

    maybe_feed(night_obs, st)
    assert len(dispatched) == 0, "Feed must refuse during NIGHT_CONSOLIDATION"

    maybe_tv(night_obs, st)
    assert len(dispatched) == 0, "TV demonstration must refuse during NIGHT_CONSOLIDATION"

    maybe_stroll(night_obs, st)
    assert len(dispatched) == 0, "Stroll must refuse during NIGHT_CONSOLIDATION"

    maybe_playpen_challenge(night_obs, st)
    assert len(dispatched) == 0, "Playpen challenge must refuse during NIGHT_CONSOLIDATION"

    maybe_ladder_challenge(night_obs, st)
    assert len(dispatched) == 0, "Ladder challenge must refuse during NIGHT_CONSOLIDATION"


def test_caretaker_script_order_and_awake_dispatch(monkeypatch, tmp_path) -> None:
    """Verify REG-A1-01: script entry-point main() is placed strictly after all
    function and constant definitions, and wait_clear dispatches awake routines in
    isolation without NameError or unhandled exceptions."""
    import ast
    import os
    import guala_caretaker.caretaker as ct

    # 1. Structural AST proof: if __name__ == "__main__" is strictly the final top-level node
    caretaker_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "guala_caretaker",
        "caretaker.py",
    )
    with open(caretaker_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=caretaker_path)

    main_node_idx = None
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            main_node_idx = i

    assert main_node_idx is not None, "if __name__ == '__main__' not found"
    nodes_after_main = tree.body[main_node_idx + 1:]
    assert len(nodes_after_main) == 0, f"Expected 0 nodes after main, found {len(nodes_after_main)}"

    # 2. Functional isolated awake dispatch proof:
    simulated_obs = {
        "live_tick": 20_000,
        "persisted_tick": 19_995,
        "available": True,
        "checkpoint_error": None,
        "her_sleep": {"asleep": False},
        "world": {"bodies": []},
    }

    monkeypatch.setattr(ct, "obs", lambda: simulated_obs)
    monkeypatch.setattr(ct, "present_food", lambda toy: {
        "observation": {
            "last_occurrence": {
                "caregiver_presentation": {"operation": "present", "presented": True, "reason": "applied", "toy": toy}
            }
        }
    })
    monkeypatch.setattr(ct, "say_word", lambda word: True)
    monkeypatch.setattr(ct, "sing_block", lambda pcm: True)
    monkeypatch.setattr(ct, "material_impact_pcm", lambda mat, intensity=0.75: b"\x00" * 8000)

    st = {
        "tactile_index": 0,
        "tactile_next_tick": 0,
        "circadian_epoch": "MORNING_FOCUS",
        "circadian_day": 1,
        "daily_moments_presented": 0,
        "active_modalities_stimulated": {},
    }

    res = ct.wait_clear(min_tick=20_000, st=st)
    assert res is not None
    assert st.get("tactile_index") == 1
    assert st.get("tactile_next_tick") == 23_600


def test_routine_nocturnal_cleanup_books_and_tv() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()), expand_library=True)
    # 1. Displace a book to floor and set TV away from Channel 0
    from dataclasses import replace
    cur_world = world._state.world
    updated = []
    for obj in cur_world.objects:
        if obj.object_id == "book-peter-rabbit":
            updated.append(replace(obj, position=PositionMM(11_000, 7_000, 0), elevation_mm=0))
        elif obj.object_id == "television":
            updated.append(replace(obj, optical_surface=((50_000, 50_000, 50_000, 50_000, 50_000, 50_000),) * 6, emission_ppm=(50_000,) * 6))
        else:
            updated.append(obj)
    world._state = replace(world._state, world=replace(cur_world, revision=cur_world.revision + 1, objects=tuple(updated)))

    world.television_broadcast.channel = 1

    # 2. Execute clean-up routine
    res = present_food(world, "clean-up")
    assert res["presented"] is True
    ops = [s.get("operation") for s in res.get("steps", [])]
    assert "nocturnal_house_tidying" in ops

    # 3. Assert TV reset to Channel 0 (Boring static)
    assert world.television_broadcast.channel == 0
    tv_obj = next(o for o in world._state.world.objects if o.object_id == "television")
    assert tv_obj.emission_ppm == (150_000, 150_000, 150_000, 150_000, 150_000, 150_000)

    # 4. Assert book-peter-rabbit reshelved to shelf-a reachable position
    book = next(o for o in world._state.world.objects if o.object_id == "book-peter-rabbit")
    assert book.position.x == 9_800
    assert book.position.y == 8_900
    assert book.elevation_mm == 330
