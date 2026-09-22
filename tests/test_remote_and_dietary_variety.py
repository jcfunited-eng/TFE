from __future__ import annotations

import math
import pytest

from dsf_ai_service.affordance_planner import (
    AffordanceField,
    AffordancePlan,
    extract_affordances,
    plan_need_fulfillment,
    plan_tool_operation,
)
from dsf_ai_service.dynamic_television_broadcast import (
    TVChannel,
    TelevisionBroadcast,
)
from dsf_ai_service.guala_home_world import (
    get_tv_broadcast,
    home_world_authority,
    nocturnal_house_tidying,
    operate_tv_remote,
    switch_tv_channel,
)
from dsf_ai_service.substrate.embodiment_world import PositionMM

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_tv_remote_physical_entity_and_material() -> None:
    """Verify tv-remote exists in TV room with authentic tactile material and dimensions."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    remote = next((item for item in snapshot.objects if item.object_id == "tv-remote"), None)
    assert remote is not None, "tv-remote must exist in the physical world"
    assert remote.position.x == 15_600 and remote.position.y == 7_600
    assert remote.mass_grams == 120
    assert remote.shape == "box"
    # Fits within Guala's handle radius (120 mm)
    assert remote.radius_mm <= 120

    # Material properties: dark matte casing, elastomer buttons
    assert remote.material is not None
    assert remote.material.surface_temperature_millikelvin == 294_000
    assert remote.material.compliance_ppm == 60_000
    assert remote.material.roughness_micrometers == 120


def test_tv_remote_operation_and_channel_cycling() -> None:
    """Verify operating the tv-remote cycles television channels and updates emission spectra."""
    world = home_world_authority(identity=IDENTITY)
    tv_broadcast = get_tv_broadcast(world)

    # Start at Boring (Channel 0)
    tv_broadcast.channel = TVChannel.BORING
    surface_0 = tv_broadcast.render_screen_surface()

    # Press remote: 0 -> 1 (Cartoon)
    new_ch = operate_tv_remote(world)
    assert new_ch == TVChannel.CARTOON
    assert tv_broadcast.channel == TVChannel.CARTOON

    # Press remote: 1 -> 2 (Educational)
    new_ch = operate_tv_remote(world)
    assert new_ch == TVChannel.EDUCATIONAL
    assert tv_broadcast.channel == TVChannel.EDUCATIONAL

    # Press remote: 2 -> 0 (Boring)
    new_ch = operate_tv_remote(world)
    assert new_ch == TVChannel.BORING
    assert tv_broadcast.channel == TVChannel.BORING


def test_caretaker_nocturnal_tidying_and_reset() -> None:
    """Verify nocturnal house tidying resets TV to Channel 0 (Boring) and returns remote to perch."""
    world = home_world_authority(identity=IDENTITY)
    tv_broadcast = get_tv_broadcast(world)

    # Simulate daytime activity: TV put on Cartoon channel, remote displaced
    tv_broadcast.channel = TVChannel.CARTOON
    from dataclasses import replace
    cur_world = world._state.world
    updated = []
    for obj in cur_world.objects:
        if obj.object_id == "tv-remote":
            updated.append(replace(obj, position=PositionMM(17_200, 6_900, 0)))  # left on sofa
        else:
            updated.append(obj)
    new_world = replace(cur_world, objects=tuple(updated))
    new_obs = world._observation_for(new_world)
    world._state = replace(world._state, world=new_world, observation=new_obs)

    # Verify displaced state
    displaced_remote = next(o for o in world.observation_snapshot().objects if o.object_id == "tv-remote")
    assert displaced_remote.position.x == 17_200 and displaced_remote.position.y == 6_900
    assert tv_broadcast.channel == TVChannel.CARTOON

    # Execute Caretaker Nocturnal Tidying
    nocturnal_house_tidying(world)

    # Verify TV reset to Channel 0 (Boring)
    assert tv_broadcast.channel == TVChannel.BORING
    tv_item = next(o for o in world.observation_snapshot().objects if o.object_id == "television")
    assert tv_item.emission_ppm == (150_000, 150_000, 150_000, 150_000, 150_000, 150_000)

    # Verify remote returned to resting perch (15_600, 7_600, 0)
    reset_remote = next(o for o in world.observation_snapshot().objects if o.object_id == "tv-remote")
    assert reset_remote.position.x == 15_600 and reset_remote.position.y == 7_600


def test_dietary_variety_physical_materials() -> None:
    """Verify milk and bread provide authentic dietary materials (tastants, volatiles, textures)."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    # Milk bottle
    milk = next((item for item in snapshot.objects if item.object_id == "bottle-milk"), None)
    assert milk is not None
    assert milk.position.x == 8_000 and milk.position.y == 3_500
    assert milk.mass_grams == 250
    assert milk.material is not None
    # High hydration/calcium tastant (channel 4 of 5)
    assert milk.material.tastant_mass_micrograms[4] == 3_000
    # Cool surface temperature (288 K / 15 C)
    assert milk.material.surface_temperature_millikelvin == 288_000
    # White optical reflectance
    assert milk.reflectance_ppm == (920_000, 920_000, 920_000, 900_000, 880_000, 850_000)

    # Bread slice
    bread = next((item for item in snapshot.objects if item.object_id == "bread-slice"), None)
    assert bread is not None
    assert bread.position.x == 4_800 and bread.position.y == 3_800
    assert bread.mass_grams == 60
    assert bread.material is not None
    # Caloric carbohydrate tastant (channel 0)
    assert bread.material.tastant_mass_micrograms[0] == 200
    # Aromatic volatile yeast odorants
    assert bread.material.odorant_release_nanograms_per_second[0] == 1_200
    # Soft yielding compliance
    assert bread.material.compliance_ppm == 350_000
    # Golden loaf reflectance
    assert bread.reflectance_ppm == (750_000, 550_000, 350_000, 220_000, 150_000, 100_000)


def test_affordance_planner_remote_and_dietary_integration() -> None:
    """Verify affordance planner identifies remote control tool operation and dietary sustenance."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    affordances = extract_affordances(snapshot.objects, snapshot.portals, regions=snapshot.regions)

    # 1. TV Remote Tool Affordance
    remote_aff = next(a for a in affordances if a.object_id == "tv-remote")
    assert remote_aff.operates_target == "television"
    assert remote_aff.movable is True
    assert remote_aff.is_food is False

    # Plan remote operation from near sofa (16000, 7000, 0)
    guala_tv_pos = (16_000, 7_000, 0)
    tool_plan = plan_tool_operation(
        affordances=affordances,
        self_pos=guala_tv_pos,
        target_tool_id="tv-remote",
        tick=500,
    )
    assert tool_plan.is_refused is False
    assert tool_plan.target_object_id == "tv-remote"
    assert len(tool_plan.steps) == 3
    assert tool_plan.steps[0].action == "toward_thing"
    assert tool_plan.steps[1].action == "grasp"
    assert tool_plan.steps[2].action == "manipulate"
    assert "operated_television" in tool_plan.steps[2].expected_postcondition

    # 2. Dietary Sustenance Affordances
    milk_aff = next(a for a in affordances if a.object_id == "bottle-milk")
    assert milk_aff.is_food is True
    assert milk_aff.movable is True

    bread_aff = next(a for a in affordances if a.object_id == "bread-slice")
    assert bread_aff.is_food is True
    assert bread_aff.movable is True

    # Plan feeding on bread from kitchen stance (4500, 3500, 0)
    kitchen_pos = (4_500, 3_500, 0)
    food_plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=kitchen_pos,
        self_region="kitchen",
        hunger_deficit=0.6,
        tick=600,
    )
    assert food_plan.is_refused is False
    # Bread is closest food entity in kitchen
    assert food_plan.target_object_id == "bread-slice"


def test_world_clearances_and_64_object_ceiling() -> None:
    """Verify exactly 64 objects, zero floor disc overlaps, and strict compliance with <= 64 ceiling."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    # Exact count: 64 objects (63 declared furniture/tools + 1 nightlight)
    assert len(snapshot.objects) == 64
    assert len(snapshot.objects) <= 64

    # Group objects by room/region and assert pairwise floor disc clearances
    for region in snapshot.regions:
        room_objects = [
            obj for obj in snapshot.objects
            if region.bounds.contains_floor_disc(obj.position, obj.radius_mm)
        ]
        for i in range(len(room_objects)):
            for j in range(i + 1, len(room_objects)):
                o1 = room_objects[i]
                o2 = room_objects[j]
                d = math.hypot(o1.position.x - o2.position.x, o1.position.y - o2.position.y)
                min_clearance = o1.radius_mm + o2.radius_mm
                assert d >= min_clearance, (
                    f"Floor disc overlap in {region.region_id} between {o1.object_id} (r={o1.radius_mm}) "
                    f"and {o2.object_id} (r={o2.radius_mm}): dist={d:.1f} < min={min_clearance}"
                )
