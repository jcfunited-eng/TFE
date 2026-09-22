from __future__ import annotations

import hashlib
import math
import struct
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
from dsf_ai_service.dynamic_television_broadcast import (
    CHANNEL_NAMES,
    PALETTE_BORING,
    PALETTE_CARTOON,
    PALETTE_EDUCATIONAL,
    TVChannel,
    TelevisionBroadcast,
)
from dsf_ai_service.guala_home_world import (
    get_tv_broadcast,
    home_world_authority,
    switch_tv_channel,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


# ===========================================================================
# 1. Dynamic Television Broadcast Channels and Physical Spectra
# ===========================================================================

def test_tv_broadcast_channels_and_spectra() -> None:
    """Verify the 3 TV channels generate distinct physical fields (optical and acoustic)."""
    broadcast = TelevisionBroadcast()

    # Channel 0: Boring static noise & monotone 60 Hz hum
    broadcast.switch_channel(int(TVChannel.BORING))
    assert broadcast.channel == TVChannel.BORING
    boring_surface = broadcast.render_screen_surface()
    assert boring_surface.columns == 32 and boring_surface.rows == 32
    assert boring_surface.palette_reflectance_ppm == PALETTE_BORING
    boring_emission = broadcast.get_emission_ppm()
    assert boring_emission == (150_000, 150_000, 150_000, 150_000, 150_000, 150_000)

    boring_pcm = broadcast.generate_audio_pcm(samples=4000)
    assert len(boring_pcm) == 8000
    samples_boring = struct.unpack("<4000h", boring_pcm)
    max_boring = max(abs(s) for s in samples_boring)
    assert 500 <= max_boring <= 1200, f"Expected low monotone hum, got max {max_boring}"

    # Channel 1: Fun / Cartoon bouncing shapes & upbeat melodic chime
    broadcast.switch_channel(int(TVChannel.CARTOON))
    assert broadcast.channel == TVChannel.CARTOON
    cartoon_surface = broadcast.render_screen_surface()
    assert cartoon_surface.columns == 32 and cartoon_surface.rows == 32
    assert cartoon_surface.palette_reflectance_ppm == PALETTE_CARTOON
    cartoon_emission = broadcast.get_emission_ppm()
    assert cartoon_emission == (480_000, 420_000, 500_000, 480_000, 450_000, 400_000)

    cartoon_pcm = broadcast.generate_audio_pcm(samples=4000)
    assert len(cartoon_pcm) == 8000
    samples_cartoon = struct.unpack("<4000h", cartoon_pcm)
    max_cartoon = max(abs(s) for s in samples_cartoon)
    assert max_cartoon >= 3000, f"Expected loud musical chime, got {max_cartoon}"

    # Channel 2: Educational symbolic glyphs & spoken phonetic speech
    broadcast.switch_channel(int(TVChannel.EDUCATIONAL))
    assert broadcast.channel == TVChannel.EDUCATIONAL
    edu_surface = broadcast.render_screen_surface()
    assert edu_surface.columns == 32 and edu_surface.rows == 32
    assert edu_surface.palette_reflectance_ppm == PALETTE_EDUCATIONAL

    edu_pcm = broadcast.generate_audio_pcm(samples=4000)
    assert len(edu_pcm) == 8000
    samples_edu = struct.unpack("<4000h", edu_pcm)
    max_edu = max(abs(s) for s in samples_edu)
    assert max_edu > 1000, "Educational phonetics speech synthesis produced sound"


def test_caretaker_tv_channel_switching() -> None:
    """Verify Caretaker channel switching cycles through all channels deterministically."""
    broadcast = TelevisionBroadcast(channel=TVChannel.CARTOON)
    assert broadcast.channel == TVChannel.CARTOON

    # Cycle: Cartoon (1) -> Educational (2) -> Boring (0) -> Cartoon (1)
    ch = broadcast.switch_channel()
    assert ch == TVChannel.EDUCATIONAL
    ch = broadcast.switch_channel()
    assert ch == TVChannel.BORING
    ch = broadcast.switch_channel()
    assert ch == TVChannel.CARTOON

    # Direct target switching
    assert broadcast.switch_channel(0) == TVChannel.BORING
    assert broadcast.switch_channel(2) == TVChannel.EDUCATIONAL
    assert broadcast.switch_channel(1) == TVChannel.CARTOON

    # Power toggle
    broadcast.is_powered = False
    dark_surface = broadcast.render_screen_surface()
    assert dark_surface.columns == 32 and dark_surface.rows == 32
    silent_pcm = broadcast.generate_audio_pcm(4000)
    assert silent_pcm == b"\x00\x00" * 4000


# ===========================================================================
# 2. Backyard Apple Tree & Ladder Affordance Tool-Use Planning
# ===========================================================================

def test_backyard_orchard_ladder_affordance_chain() -> None:
    """Verify Guala uses the climbable garden ladder to reach elevated hanging fruit."""
    # Organism standing in backyard at (12000, 11000, 0)
    guala_pos = (12_000, 11_000, 0)

    # Hanging apple in tree at (14000, 14100, 850)
    # dz = 850 mm, which exceeds Reach_z of 350 mm
    apple_pos = (14_000, 14_100, 850)

    # Garden ladder standing at (14000, 11800, 0)
    ladder_pos = (14_000, 11_800, 0)

    affordances = [
        AffordanceField(
            object_id="garden-apple",
            movable=True,
            mass_grams=180,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=apple_pos,
            region_id="backyard",
        ),
        AffordanceField(
            object_id="garden-ladder",
            movable=True,
            mass_grams=4_000,
            support_surface=True,
            elevation_height_mm=550,   # 550 mm elevation + 350 mm reach = 900 mm >= 850 mm!
            is_portal=False,
            is_food=False,
            position=ladder_pos,
            region_id="backyard",
        ),
    ]

    # Evaluate reachability from ground
    reachable, horiz_dist, dz = evaluate_reachability(guala_pos, apple_pos)
    assert reachable is False
    assert dz == 850.0

    # Plan need fulfillment
    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=guala_pos,
        self_region="backyard",
        hunger_deficit=0.85,
        tick=1000,
    )

    assert plan.is_refused is False
    assert plan.target_object_id == "garden-apple"
    assert len(plan.steps) == 7

    actions = [s.action for s in plan.steps]
    assert actions == [
        "toward_thing",  # 0: Approach ladder
        "grasp",         # 1: Grasp ladder
        "toward_food",   # 2: Carry ladder toward tree
        "release",       # 3: Place ladder at tree base
        "mount_tool",    # 4: Step up onto ladder platform (elevation +550 mm)
        "grasp",         # 5: Grasp hanging apple
        "bite",          # 6: Eat apple
    ]

    # Verify targets
    assert plan.steps[0].target_id == "garden-ladder"
    assert plan.steps[1].target_id == "garden-ladder"
    assert plan.steps[2].target_id == "garden-apple"
    assert plan.steps[3].target_id == "garden-ladder"
    assert plan.steps[4].target_id == "garden-ladder"
    assert plan.steps[5].target_id == "garden-apple"
    assert plan.steps[6].target_id == "garden-apple"


def test_backyard_ladder_adjacent_tool_chain() -> None:
    """When ladder is already positioned under the apple tree, planner generates direct 4-step chain."""
    guala_pos = (14_000, 13_800, 0)
    apple_pos = (14_000, 14_100, 850)
    ladder_adjacent_pos = (14_000, 13_900, 0)  # within 200 mm of apple

    affordances = [
        AffordanceField(
            object_id="garden-apple",
            movable=True,
            mass_grams=180,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=apple_pos,
            region_id="backyard",
        ),
        AffordanceField(
            object_id="garden-ladder",
            movable=True,
            mass_grams=4_000,
            support_surface=True,
            elevation_height_mm=550,
            is_portal=False,
            is_food=False,
            position=ladder_adjacent_pos,
            region_id="backyard",
        ),
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=guala_pos,
        self_region="backyard",
        hunger_deficit=0.7,
        tick=1100,
    )

    assert plan.is_refused is False
    assert len(plan.steps) == 4
    actions = [s.action for s in plan.steps]
    assert actions == [
        "toward_thing",  # 0: Approach ladder
        "mount_tool",    # 1: Mount ladder
        "grasp",         # 2: Grasp apple
        "bite",          # 3: Eat apple
    ]


def test_backyard_unreachable_apple_fails_closed() -> None:
    """If fruit is hung too high for ladder (e.g. dz = 1200 mm > 550 + 350 mm), planner refuses."""
    guala_pos = (12_000, 11_000, 0)
    impossible_apple_pos = (14_000, 14_100, 1_200)

    affordances = [
        AffordanceField(
            object_id="garden-apple",
            movable=True,
            mass_grams=180,
            support_surface=False,
            elevation_height_mm=0,
            is_portal=False,
            is_food=True,
            position=impossible_apple_pos,
            region_id="backyard",
        ),
        AffordanceField(
            object_id="garden-ladder",
            movable=True,
            mass_grams=4_000,
            support_surface=True,
            elevation_height_mm=550,
            is_portal=False,
            is_food=False,
            position=(14_000, 11_800, 0),
            region_id="backyard",
        ),
    ]

    plan = plan_need_fulfillment(
        affordances=affordances,
        self_pos=guala_pos,
        self_region="backyard",
        hunger_deficit=0.8,
        tick=1200,
    )

    assert plan.is_refused is True
    assert "unreachable_elevation" in plan.refusal_reason


# ===========================================================================
# 3. Whole Home World Environmental Variety Integration
# ===========================================================================

def test_home_world_environmental_variety_manifest() -> None:
    """Verify the physical home world includes all environmental variety entities."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    # Headroom compliance: exactly 64 objects (<= 64 ceiling)
    assert len(snapshot.objects) == 64
    assert len(snapshot.objects) <= 64

    # Television entity exists in TV room
    tv = next(item for item in snapshot.objects if item.object_id == "television")
    assert tv.position.x == 17_000 and tv.position.y == 9_200
    assert tv.optical_surface is not None

    # Backyard entities exist
    tree = next(item for item in snapshot.objects if item.object_id == "tree-apple")
    assert tree.position.x == 14_000 and tree.position.y == 14_800
    assert tree.radius_mm == 500

    apple = next(item for item in snapshot.objects if item.object_id == "garden-apple")
    assert apple.position.x == 14_000 and apple.position.y == 14_100
    assert apple.elevation_mm == 850

    ladder = next(item for item in snapshot.objects if item.object_id == "garden-ladder")
    assert ladder.position.x == 14_000 and ladder.position.y == 11_800
    assert ladder.mass_grams == 4_000

    # TV Broadcast controls
    tv_broadcast = get_tv_broadcast(world)
    assert isinstance(tv_broadcast, TelevisionBroadcast)
    initial_channel = tv_broadcast.channel

    new_channel = switch_tv_channel(world)
    assert new_channel != initial_channel
    assert tv_broadcast.channel == new_channel

    # Affordance extraction from live world objects
    affordances = extract_affordances(snapshot.objects, snapshot.portals, regions=snapshot.regions)
    ladder_aff = next(a for a in affordances if a.object_id == "garden-ladder")
    assert ladder_aff.support_surface is True
    assert ladder_aff.movable is True
    assert ladder_aff.elevation_height_mm == 550

    apple_aff = next(a for a in affordances if a.object_id == "garden-apple")
    assert apple_aff.is_food is True
    assert apple_aff.position == (14_000, 14_100, 850)

    tree_aff = next(a for a in affordances if a.object_id == "tree-apple")
    assert tree_aff.is_food is False
