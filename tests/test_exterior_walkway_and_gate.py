#!/usr/bin/env python3
"""tests/test_exterior_walkway_and_gate.py — Exterior Stroller Walkways & Garden Gate Physics.

Verifies:
1. Exterior walkway region expansion and perimeter garden gate portal topology.
2. Extended multi-step vehicle stroller journey from indoor Hallway out to Walkway.
3. Spatial horizon streaming on the walkway strictly maintaining <= 64 objects aperture.
4. Walkway lantern optical emission and bench support affordance.
5. Footprint disc coverage and zero pairwise floor collisions on walkway.
"""

from __future__ import annotations

import math
from dataclasses import replace
import pytest

from dsf_ai_service.affordance_planner import (
    extract_affordances,
    plan_vehicle_journey,
)
from dsf_ai_service.guala_home_world import (
    expand_exterior_walkway,
    home_world_authority,
)
from dsf_ai_service.substrate.embodiment_world import (
    PoseMM,
    PositionMM,
    _floor_discs_overlap,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_walkway_expansion_and_gate_portal_topology() -> None:
    """Verify exterior walkway region and garden perimeter gate portal are created with exact geometry."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world

    # 1. Ten physical regions
    assert len(cur_w.regions) == 10
    region_ids = {r.region_id for r in cur_w.regions}
    assert "walkway" in region_ids
    assert "backyard" in region_ids
    assert "hallway" in region_ids

    walkway = next(r for r in cur_w.regions if r.region_id == "walkway")
    assert walkway.bounds.minimum.y == 16_000
    assert walkway.bounds.maximum.y == 22_000
    assert walkway.ceiling_height_mm == 8_000

    # 2. Ten physical portals including perimeter garden gate
    assert len(cur_w.portals) == 10
    gate = next(p for p in cur_w.portals if p.portal_id == "door-gate")
    assert gate.region_ids == ("backyard", "walkway")
    assert gate.axis == "y"
    assert gate.plane_mm == 16_000
    assert gate.aperture_min_mm == 9_000
    assert gate.aperture_max_mm == 11_000
    assert gate.height_mm == 2_050

    # 3. Cryptographically valid observation snapshot
    snap = world.observation_snapshot()
    assert len(snap.regions) == 10
    assert len(snap.portals) == 10
    assert len(snap.objects) == 64
    assert snap.authority_hmac_sha256 != ""


def test_multi_step_vehicle_journey_from_hallway_to_exterior_walkway() -> None:
    """Verify stroller carriage can be planned on an extended journey through the backyard and garden gate."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world

    affordances = extract_affordances(world.global_objects(), regions=cur_w.regions)
    # Register portal connections in affordance manifold
    for p in cur_w.portals:
        portal_aff = replace(
            affordances[0],
            object_id=p.portal_id,
            is_portal=True,
            connects_regions=p.region_ids,
            position=(int(p.plane_mm), 0, 0),
        )
        affordances.append(portal_aff)

    # Guala at stroller resting perch in Hallway (6_500, 6_000, 0)
    plan = plan_vehicle_journey(
        affordances=affordances,
        self_pos=(6_500, 6_000, 0),
        self_region="hallway",
        destination_region="walkway",
        target_vehicle_id="stroller-carriage",
        tick=0,
    )

    assert plan.status == "active"
    assert not plan.is_refused
    assert len(plan.steps) == 4

    # Step 0: Mount stroller in hallway
    assert plan.steps[0].action == "mount_vehicle"
    assert plan.steps[0].target_id == "stroller-carriage"

    # Step 1: Transit into backyard through door-8
    assert plan.steps[1].action == "traverse_portal_in_vehicle"
    assert plan.steps[1].target_id == "door-8"

    # Step 2: Roll through garden gate door-gate into walkway
    assert plan.steps[2].action == "traverse_portal_in_vehicle"
    assert plan.steps[2].target_id == "door-gate"

    # Step 3: Dismount at walkway destination
    assert plan.steps[3].action == "dismount_vehicle"
    assert plan.steps[3].target_id == "stroller-carriage"
    assert plan.terminal_valence == 0.90


def test_spatial_horizon_streaming_on_walkway() -> None:
    """Verify Guala on exterior walkway perceives local outdoor structures while strictly streaming <= 64 objects."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world

    # Displace Guala into walkway (10_000, 18_000, 0)
    updated_bodies = [
        replace(b, pose=PoseMM(PositionMM(10_000, 18_000, 0), b.pose.heading_millidegrees))
        if b.body_id == "guala-body-1" else b
        for b in cur_w.bodies
    ]
    world._state = replace(world._state, world=replace(cur_w, bodies=tuple(updated_bodies)))

    snap = world.observation_snapshot()
    object_ids = [o.object_id for o in snap.objects]

    # Receptor ceiling strictly preserved
    assert len(snap.objects) == 64
    assert len(snap.objects) <= 64

    # Walkway and backyard entities dominate the local perceptual horizon
    top_10 = set(object_ids[:10])
    assert "walkway-bench" in top_10
    assert "walkway-lantern" in top_10
    assert "tree-apple" in top_10 or "garden-patch" in top_10


def test_walkway_lantern_emission_and_bench_support() -> None:
    """Verify physical properties: lantern illumination emission and bench support affordance."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    objects = {o.object_id: o for o in world.global_objects()}

    # Walkway Lantern
    lantern = objects["walkway-lantern"]
    assert len(lantern.emission_ppm) == 6
    assert lantern.emission_ppm[0] == 800_000  # High optical emission
    assert lantern.elevation_mm == 1_200

    # Walkway Bench
    bench = objects["walkway-bench"]
    assert bench.shape == "box"
    assert bench.size_mm == (1_200, 450, 450)
    assert bench.mass_grams == 35_000

    affordances = extract_affordances(world.global_objects(), regions=world._state.world.regions)
    aff_map = {a.object_id: a for a in affordances}
    assert aff_map["walkway-bench"].support_surface is True
    assert aff_map["walkway-bench"].movable is False  # Heavy park bench


def test_walkway_clearances_and_box_plan_coverage() -> None:
    """Verify geometric validity: box coverage inequality 4*r^2 >= sx^2 + sy^2 and zero floor collisions."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    bench = next(o for o in world.global_objects() if o.object_id == "walkway-bench")
    lantern = next(o for o in world.global_objects() if o.object_id == "walkway-lantern")

    # Footprint disc coverage over box plan
    sx, sy, sz = bench.size_mm
    assert 4 * (bench.radius_mm ** 2) >= (sx ** 2) + (sy ** 2)

    # Pairwise clearance between bench and lantern
    assert not _floor_discs_overlap(bench.position, bench.radius_mm, lantern.position, lantern.radius_mm)
    dist = math.hypot(bench.position.x - lantern.position.x, bench.position.y - lantern.position.y)
    assert dist > bench.radius_mm + lantern.radius_mm
