import pytest
from dsf_ai_service.affordance_planner import (
    AffordanceField,
    AffordancePlan,
    PlanStep,
    evaluate_reachability,
    extract_affordances,
    plan_need_fulfillment,
    REACH_HORIZONTAL_MM,
    REACH_VERTICAL_MM,
)


def test_direct_one_step_reach_plan():
    """When food is within immediate limb reach, plans direct grasp -> bite."""
    self_pos = (1000, 1000, 0)
    food_pos = (1100, 1000, 0)  # 100 mm away

    affordances = [
        AffordanceField(
            object_id="apple-1",
            movable=True,
            mass_grams=150,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=food_pos,
            region_id="kitchen",
        )
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=self_pos,
        self_region="kitchen",
        hunger_deficit=0.6,
        tick=100,
    )

    assert plan.is_refused is False
    assert plan.target_object_id == "apple-1"
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "grasp"
    assert plan.steps[1].action == "bite"
    assert plan.terminal_valence == 0.80


def test_refrigerator_problem_elevated_food_requires_tool_chain():
    """The Refrigerator Problem:
    Food is on top of refrigerator (dz = 600 mm > 350 mm reach).
    A step stool is across the room.
    Planner must generate 7-step affordance chain:
    approach stool -> grasp stool -> carry stool to fridge -> set down stool -> mount stool -> grasp food -> bite.
    """
    self_pos = (1000, 1000, 0)
    target_pos = (1000, 1000, 600)  # dz = 600 mm (exceeds Reach_z of 350 mm)
    stool_pos = (3000, 3000, 0)      # stool is across the room

    affordances = [
        AffordanceField(
            object_id="apple-on-fridge",
            movable=True,
            mass_grams=150,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=target_pos,
            region_id="kitchen",
        ),
        AffordanceField(
            object_id="wooden-stool",
            movable=True,
            mass_grams=3000,
            support_surface=True,
            elevation_height_mm=300,  # 300 mm + 350 mm reach = 650 mm >= 600 mm!
            is_portal=False,
            is_food=False,
            position=stool_pos,
            region_id="kitchen",
        ),
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=self_pos,
        self_region="kitchen",
        hunger_deficit=0.8,
        tick=500,
    )

    assert plan.is_refused is False
    assert plan.target_object_id == "apple-on-fridge"
    assert len(plan.steps) == 7

    # Verify action sequence
    actions = [s.action for s in plan.steps]
    assert actions == [
        "toward_thing",  # approach tool
        "grasp",         # pick up stool
        "toward_food",   # carry stool to fridge
        "release",       # place stool
        "mount_tool",    # step onto stool
        "grasp",         # reach apple from elevated stance
        "bite",          # consume food
    ]
    assert plan.steps[4].action == "mount_tool"
    assert plan.steps[5].target_id == "apple-on-fridge"


def test_refrigerator_problem_tool_already_adjacent():
    """When the chair/stool is already placed beneath the elevated food,
    planner skips transport steps and executes:
    approach support -> mount tool -> grasp food -> bite.
    """
    self_pos = (0, 0, 0)
    target_pos = (1000, 1000, 600)
    stool_pos = (1000, 1000, 0)  # already under the food!

    affordances = [
        AffordanceField(
            object_id="apple-high",
            movable=True,
            mass_grams=150,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=target_pos,
            region_id="kitchen",
        ),
        AffordanceField(
            object_id="kitchen-chair",
            movable=True,
            mass_grams=4500,
            support_surface=True,
            elevation_height_mm=450,
            is_portal=False,
            is_food=False,
            position=stool_pos,
            region_id="kitchen",
        ),
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=self_pos,
        self_region="kitchen",
        hunger_deficit=0.7,
        tick=600,
    )

    assert plan.is_refused is False
    assert len(plan.steps) == 4
    actions = [s.action for s in plan.steps]
    assert actions == ["toward_thing", "mount_tool", "grasp", "bite"]


def test_unreachable_elevation_physical_refusal():
    """If food elevation exceeds reach even with the highest available tool,
    planner emits a physical refusal rather than falling into random wandering.
    """
    self_pos = (1000, 1000, 0)
    target_pos = (1000, 1000, 1200)  # 1200 mm high

    affordances = [
        AffordanceField(
            object_id="apple-ceiling",
            movable=True,
            mass_grams=150,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=target_pos,
            region_id="kitchen",
        ),
        AffordanceField(
            object_id="low-stool",
            movable=True,
            mass_grams=2000,
            support_surface=True,
            elevation_height_mm=200,  # 200 + 350 = 550 << 1200 mm
            is_portal=False,
            is_food=False,
            position=(1000, 1000, 0),
            region_id="kitchen",
        ),
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=self_pos,
        self_region="kitchen",
        hunger_deficit=0.9,
        tick=700,
    )

    assert plan.is_refused is True
    assert "unreachable_elevation" in plan.refusal_reason
    assert len(plan.steps) == 0


def test_multi_room_portal_traversal_plan():
    """When food is in an adjacent room, plans doorway navigation followed by ingestion."""
    self_pos = (500, 500, 0)
    target_pos = (4000, 4000, 0)

    affordances = [
        AffordanceField(
            object_id="apple-pantry",
            movable=True,
            mass_grams=150,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=target_pos,
            region_id="pantry",
        ),
        AffordanceField(
            object_id="door-kitchen-pantry",
            movable=False,
            mass_grams=999_999,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=True,
            is_food=False,
            position=(2000, 2000, 0),
            region_id="kitchen",
            connects_regions=("kitchen", "pantry"),
        ),
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=self_pos,
        self_region="kitchen",
        hunger_deficit=0.7,
        tick=800,
    )

    assert plan.is_refused is False
    actions = [s.action for s in plan.steps]
    assert "toward_door" in actions
    assert "toward_food" in actions
    assert actions[-2:] == ["grasp", "bite"]


def test_plan_step_advancement_and_serialization():
    """Tests step state tracking and JSON serialization roundtrip."""
    steps = (
        PlanStep(0, "toward_food", "apple-1", "start", "near_food"),
        PlanStep(1, "grasp", "apple-1", "near_food", "held"),
        PlanStep(2, "bite", "apple-1", "held", "fed", somatic_delta_projected=0.80),
    )
    plan = AffordancePlan(
        plan_id="plan_test_01",
        goal="quench_hunger",
        target_object_id="apple-1",
        steps=steps,
        created_tick=1000,
        terminal_valence=0.80,
    )

    assert plan.current_step_index == 0
    assert plan.next_step().action == "toward_food"
    assert plan.is_complete is False

    plan.advance_step()
    assert plan.current_step_index == 1
    assert plan.next_step().action == "grasp"

    plan.advance_step()
    assert plan.current_step_index == 2
    assert plan.next_step().action == "bite"

    plan.advance_step()
    assert plan.current_step_index == 3
    assert plan.is_complete is True
    assert plan.next_step() is None

    # Serialization roundtrip
    d = plan.to_dict()
    restored = AffordancePlan.from_dict(d)
    assert restored.plan_id == plan.plan_id
    assert restored.status == "completed"
    assert len(restored.steps) == 3

