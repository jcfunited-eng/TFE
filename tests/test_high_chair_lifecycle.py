import uuid
from dataclasses import replace
from unittest.mock import patch

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_caretaker_hand import place_in_high_chair, release_from_high_chair, _negative_space_path_for_hand
from dsf_ai_service.substrate.embodiment_world import (
    BodyContactState,
    PositionMM,
    PoseMM,
    _derived_contact_patch_square_mm,
    _receptor_position,
)
from guala_caretaker import caretaker


def test_high_chair_release_with_active_contact():
    world = home_world_authority(identity=str(uuid.uuid4()))
    place_res = place_in_high_chair(world)
    assert place_res["presented"] is True

    # Simulate child establishing active contact with the high chair
    chair = next(o for o in world._state.world.objects if o.object_id == "high-chair")
    her = next(b for b in world._state.world.bodies if b.body_id == "guala-body-1")
    rec_pos = _receptor_position(her, her.receptor_geometry.touch_offset_mm)
    patch_sq_mm = _derived_contact_patch_square_mm(
        receptor_position=rec_pos,
        receptor_radius_mm=her.receptor_geometry.touch_radius_mm,
        object_position=chair.position,
        object_radius_mm=chair.radius_mm,
    )

    contact = BodyContactState(
        kind="touch",
        object_id="high-chair",
        contact_patch_square_mm=patch_sq_mm,
        duration_microseconds=250_000,
    )
    world._state = replace(
        world._state,
        world=replace(
            world._state.world,
            bodies=tuple(
                replace(b, active_contact=contact) if b.body_id == "guala-body-1" else b
                for b in world._state.world.bodies
            ),
        ),
    )

    # Release from high chair must succeed and cleanly clear active contact
    rel_res = release_from_high_chair(world)
    assert rel_res["presented"] is True, f"Release failed: {rel_res}"
    assert rel_res["steps"][-1]["operation"] == "release_from_high_chair"
    assert rel_res["steps"][-1]["reason"] == "applied"
    assert rel_res["steps"][-1]["to"] == [2700, 1500]

    her_after = next(b for b in world._state.world.bodies if b.body_id == "guala-body-1")
    assert her_after.pose.position.x == 2700
    assert her_after.pose.position.y == 1500
    assert her_after.active_contact is None


def test_caretaker_failed_release_non_blocking_for_hungry_child():
    st = {
        "seated_for_meal": True,
        "food_delivered_for_meal": True,
        "meal_retry": False,
        "meal_tick": 1000,
        "seated_meal_tick": 1000,
    }

    o = {
        "live_tick": 1500,
        "last_occurrence": {
            "metabolic_need_reserve_deficit": [1, 1],
            "embodiment": {
                "self_body_id": "guala-body-1",
                "bodies": [
                    {
                        "body_id": "guala-body-1",
                        "held_object_id": None,
                        "pose": {"position": {"x_mm": 3500, "y_mm": 1500, "z_mm": 0}},
                    },
                    {
                        "body_id": "person-body-1",
                        "held_object_id": None,
                        "pose": {"position": {"x_mm": 7300, "y_mm": 7500, "z_mm": 0}},
                    },
                ],
                "objects": [
                    {
                        "object_id": "high-chair",
                        "position": {"x_mm": 3500, "y_mm": 1500, "z_mm": 0},
                        "radius_mm": 250,
                        "tastant_remaining_micrograms": None,
                    },
                    {
                        "object_id": "apple-1",
                        "position": {"x_mm": 2000, "y_mm": 2000, "z_mm": 0},
                        "radius_mm": 50,
                        "tastant_remaining_micrograms": 50_000,
                    },
                ],
            },
        },
    }

    calls = []

    def mock_present_food(obj_id):
        calls.append(obj_id)
        if obj_id == "high-chair-release":
            return {
                "observation": {
                    "last_occurrence": {
                        "caregiver_presentation": {
                            "object_id": "high-chair-release",
                            "presented": False,
                            "steps": [
                                {
                                    "operation": "release_from_high_chair",
                                    "reason": "approach_refused",
                                    "to": None,
                                }
                            ],
                        }
                    }
                }
            }
        elif obj_id == "high-chair-meal":
            return {
                "observation": {
                    "last_occurrence": {
                        "caregiver_presentation": {
                            "object_id": "high-chair-meal",
                            "presented": True,
                            "steps": [
                                {"operation": "place_in_high_chair", "reason": "applied"}
                            ],
                        }
                    }
                }
            }
        else:
            return {
                "observation": {
                    "live_tick": 1501,
                    "last_occurrence": {
                        "native_tick": 1501,
                        "caregiver_presentation": {
                            "object_id": obj_id,
                            "presented": True,
                            "steps": [{"operation": "deliver", "reason": "applied"}],
                        },
                    },
                }
            }

    with patch("guala_caretaker.caretaker.present_food", side_effect=mock_present_food), \
         patch("guala_caretaker.caretaker.sing_block"), \
         patch("guala_caretaker.caretaker.say_word", return_value="apple"):
        caretaker.maybe_feed(o, st)

    assert "high-chair-release" in calls
    assert "apple-1" in calls
    assert st["food_delivered_for_meal"] is True
    assert st["meal_retry"] is False


def test_negative_space_path_approach_collision_exclusion():
    world = home_world_authority(identity=str(uuid.uuid4()))
    origin = PositionMM(4800, 5600, 0)
    goal = PositionMM(2630, 8349, 0)
    world._state = replace(
        world._state,
        world=replace(
            world._state.world,
            bodies=tuple(
                replace(b, pose=PoseMM(PositionMM(2058, 8530, 0), 0))
                if b.body_id == "guala-body-1"
                else replace(b, pose=PoseMM(origin, 0))
                for b in world._state.world.bodies
            ),
        ),
    )
    snap = world.observation_snapshot()
    person = next(b for b in snap.bodies if b.body_id != "guala-body-1")
    path = _negative_space_path_for_hand(snap, person, origin, goal)
    assert path is not None
    assert path[0] == origin
    assert path[-1] == goal
    assert len(path) > 2
