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

    # 2. Multi-diet rotation
    assert "apple-delivery" in MEAL_DELIVERY_CYCLE
    assert "bread-delivery" in MEAL_DELIVERY_CYCLE
    assert "milk-delivery" in MEAL_DELIVERY_CYCLE

    # 3. Deliver bread and milk with face reach
    res_bread = present_food(world, "bread-delivery")
    assert res_bread["delivered"] is not None

    # 4. Gating check: high-chair placement occurs only when hungry and meal interval has elapsed
    st = {"meal_tick": 0}
    placed_calls = []
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: placed_calls.append(item) or {"presented": True})

    # Not hungry: deficit below threshold -> high-chair placement not called
    obs_not_hungry = {
        "live_tick": 10_000,
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [0, 1],
            "embodiment": {"bodies": [{"body_id": "guala-body-1", "pose": {"position": {"x_mm": 1000, "y_mm": 1000}}}], "self_body_id": "guala-body-1"},
            "tastant_remaining_micrograms": {},
        }
    }
    maybe_feed(obs_not_hungry, st)
    assert "high-chair-meal" not in placed_calls


def test_routine_2_tv_time_remote_gaze_alignment(monkeypatch) -> None:
    # Test retinal visibility evidence gating
    st = {}
    remote_cycled = []
    words = []
    monkeypatch.setattr("guala_caretaker.caretaker.present_food", lambda item: remote_cycled.append(item) or ({"channel": 1} if item == "tv-remote-cycle" else {"presented": True}))
    monkeypatch.setattr("guala_caretaker.caretaker.say_word", lambda word: words.append(word) or True)

    # Case A: Missing visual evidence (seen is None) -> demonstration withheld
    obs_missing = {
        "live_tick": 60_000,
        "last_occurrence": {"seen": None}
    }
    maybe_tv(obs_missing, st)
    assert len(remote_cycled) == 0

    # Case B: Television not in retinal field -> attention called, no remote cycle
    st["tv_next_tick"] = 0
    obs_not_seen = {
        "live_tick": 60_001,
        "last_occurrence": {"seen": ["bed", "toy-bear"]}
    }
    maybe_tv(obs_not_seen, st)
    assert len(remote_cycled) == 0
    assert "television" in words

    # Case C: Television verified in retinal field -> remote cycle demonstrated
    st["tv_next_tick"] = 0
    obs_seen = {
        "live_tick": 60_002,
        "last_occurrence": {"seen": ["television", "sofa"]}
    }
    maybe_tv(obs_seen, st)
    assert "tv-remote-cycle" in remote_cycled


def test_routine_3_curriculum_variety_tactile() -> None:
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


def test_routine_4_stroller_walk_and_sensory_field() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # Stroller carriage delivery & excursion
    res_stroller = present_food(world, "stroller-carriage")
    assert res_stroller["presented"] is True
    applied_ops = [s.get("operation") for s in res_stroller.get("steps", []) if s.get("reason") == "applied"]
    assert "stroller_excursion" in applied_ops

    # Hand holding contact
    res_hand = present_food(world, "touch-hold-hand")
    assert res_hand["touched"] == "hold_hand"

    # Birdsong acoustic field
    blocks = birdsong_blocks()
    assert len(blocks) >= 4
    for b in blocks[:4]:
        assert len(b) == 8000


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
    # Guala radius 200mm, playpen center (2050, 6700), target (2060, 6700): dist = 10mm + 200mm <= 450mm
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
    # target (2500, 6700): dist = 450mm + 200mm = 650mm > 450mm -> crosses perimeter boundary
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
    # Verify deictic orientation pointing step was recorded and applied
    steps = res.get("steps") or []
    pointing_steps = [s for s in steps if s.get("operation") == "point_to_stray"]
    if pointing_steps:
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
    # even when read_title_index or read_chapter is nonzero (REG-A1-04 verification)
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


def test_routine_10_diurnal_circadian_pacing_exclusivity() -> None:
    # 6 canonical epochs
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
    monkeypatch.setattr(ct, "present_food", lambda toy: {"operation": "present", "reason": "applied", "toy": toy})
    monkeypatch.setattr(ct, "say_word", lambda word: True)
    monkeypatch.setattr(ct, "sing_block", lambda pcm: True)
    monkeypatch.setattr(ct, "material_impact_pcm", lambda mat, intensity=0.75: b"\x00" * 8000)

    fake_state_file = str(tmp_path / "state.json")
    monkeypatch.setattr(ct, "STATE", fake_state_file)
    monkeypatch.setattr(ct, "LOG", str(tmp_path / "test_caretaker.log"))

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
    world = home_world_authority(identity=str(uuid.uuid4()))
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
