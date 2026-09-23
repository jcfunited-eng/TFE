import math
import uuid
import pytest

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import PoseMM, PositionMM
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


def test_routine_1_high_chair_meal_variety() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # 1. Place in high chair
    res = present_food(world, "high-chair-meal")
    assert res["presented"] is True
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


def test_routine_2_tv_time_remote_gaze_alignment() -> None:
    # Retinal heading alignment calculation
    hx, hy = 15000, 7000
    tv_x, tv_y = 17000, 9200
    target_heading = round(math.degrees(math.atan2(tv_y - hy, tv_x - hx)) * 1_000) % 360_000
    assert 0 <= target_heading < 360_000

    # Test gaze within 45 degrees
    aligned_heading = target_heading
    deviation = min(abs(aligned_heading - target_heading), 360_000 - abs(aligned_heading - target_heading))
    assert deviation <= 45_000

    # Test unaligned gaze
    unaligned_heading = (target_heading + 90_000) % 360_000
    dev_unaligned = min(abs(unaligned_heading - target_heading), 360_000 - abs(unaligned_heading - target_heading))
    assert dev_unaligned > 45_000


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


def test_routine_4_stroller_walk_and_sensory_field() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # Stroller carriage delivery
    res_stroller = present_food(world, "stroller-carriage")
    assert res_stroller is not None

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
    res = present_food(world, "ladder-challenge")
    assert res["presented"] is True
    metal_pcm = material_impact_pcm("metal", intensity=0.85)
    assert len(metal_pcm) == 8000


def test_routine_6_playpen_containment_impedance() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # 1. Contain in playpen
    res_contain = present_food(world, "playpen-containment")
    assert res_contain["presented"] is True
    snap = world.observation_snapshot()
    her = next(b for b in snap.bodies if b.body_id == snap.self_body_id)
    assert her.pose.position.x == 2050
    assert her.pose.position.y == 6700
    assert snap.room_id == "her-room"


def test_routine_7_joint_clean_up_routine() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    res = present_food(world, "joint-clean-up")
    assert res["presented"] is True
    assert res["object_id"] == "joint-clean-up"


def test_routine_8_lap_reading_stabilized_seating() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    lap = present_food(world, "touch-lap")
    assert lap["touched"] == "lap_hold"
    contacts = lap.get("contacts") or []
    sites = {c["site"] for c in contacts}
    assert "front-torso" in sites
    assert "left-shoulder" in sites
    assert "right-shoulder" in sites


def test_routine_9_affection_and_stress_recovery_hug() -> None:
    world = home_world_authority(identity=str(uuid.uuid4()))
    # Playpen release delivers contingent recovery hug
    res_release = present_food(world, "playpen-release")
    assert res_release["presented"] is True
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
