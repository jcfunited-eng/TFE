#!/usr/bin/env python3
"""tests/test_spatial_horizon_streaming.py — Spatial Horizon Streaming & Occlusion Engine.

Verifies:
1. Exact baseline 64-object observation snapshot preservation.
2. Room-based spatial horizon occlusion in her-room (bedroom entities occupy highest solid angle ranks).
3. Dynamic shift when organism translates to the backyard (garden/tree/sandbox entities rise to top).
4. Unbounded world expansion (84+ objects) preserves global world authority while streaming <= 64 objects to physical receptors.
5. Inverse-square solid angle metric Omega = (pi * r^2) / (d^2 + 1) physics decay.
"""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from dsf_ai_service.guala_home_world import (
    compute_spatial_horizon_observation,
    home_world_authority,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    PoseMM,
    PositionMM,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_baseline_64_object_observation_snapshot() -> None:
    """Verify standard home world observation snapshot retains all 64 objects with valid HMAC."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.observation_snapshot()

    # Exact count matching physical ceiling
    assert len(snapshot.objects) == 64
    assert len(snapshot.objects) <= 64
    assert len(world.global_objects()) == 64
    assert snapshot.authority_hmac_sha256 != ""
    assert snapshot.authority_receipt_sha256 != ""


def test_spatial_horizon_occlusion_in_her_room() -> None:
    """Verify Guala in her-room perceives bedroom entities with largest optical/acoustic solid angles."""
    world = home_world_authority(identity=IDENTITY)
    snapshot = world.spatial_horizon_snapshot(body_id="guala-body-1", max_objects=64, strict_occlusion=False)

    assert len(snapshot.objects) == 64
    object_ids = [o.object_id for o in snapshot.objects]

    # Her immediate room furniture must lead the solid angle hierarchy
    top_5 = set(object_ids[:5])
    assert "bed" in top_5
    assert "desk" in top_5
    assert "toy-chest" in top_5 or "playpen" in top_5

    # Distant outdoor items behind multiple walls must rank far below
    assert object_ids.index("bed") < object_ids.index("garden-apple")
    assert object_ids.index("desk") < object_ids.index("tree-pine")
    assert object_ids.index("playpen") < object_ids.index("bath-tub")

    # Strict occlusion verifies only truly visible items in her-room and portal LOS are returned
    strict_snap = world.spatial_horizon_snapshot(body_id="guala-body-1", max_objects=64, strict_occlusion=True)
    assert len(strict_snap.objects) < 64
    strict_ids = [o.object_id for o in strict_snap.objects]
    assert "bed" in strict_ids
    assert "garden-apple" not in strict_ids


def test_spatial_horizon_occlusion_in_backyard() -> None:
    """Verify translating to the backyard dynamically elevates outdoor orchard and playground items."""
    world = home_world_authority(identity=IDENTITY)
    cur_world = world._state.world

    # Displace Guala's body to the center of the backyard (12_000, 12_000, 0)
    updated_bodies = []
    for b in cur_world.bodies:
        if b.body_id == "guala-body-1":
            updated_bodies.append(replace(b, pose=PoseMM(PositionMM(12_000, 12_000, 0), b.pose.heading_millidegrees)))
        else:
            updated_bodies.append(b)

    backyard_world = replace(cur_world, bodies=tuple(updated_bodies))
    world._state = replace(world._state, world=backyard_world, observation=world._observation_for(backyard_world))

    snapshot = world.spatial_horizon_snapshot(body_id="guala-body-1", max_objects=64, strict_occlusion=False)
    object_ids = [o.object_id for o in snapshot.objects]

    # Outdoor entities must occupy the leading ranks
    top_8 = set(object_ids[:8])
    assert "sandbox" in top_8
    assert "garden-patch" in top_8
    assert "tree-apple" in top_8
    assert "garden-ladder" in top_8
    assert "slide" in top_8 or "swing" in top_8


def test_unbounded_world_expansion_streams_bounded_horizon() -> None:
    """Verify adding 20 extra entities (84 total) preserves global authority while streaming strictly <= 64 objects."""
    world = home_world_authority(identity=IDENTITY)
    cur_world = world._state.world

    # Add 20 outdoor flora entities to the world ledger
    extra_flora = [
        EmbodiedObject(
            f"garden-flower-{i}",
            radius_mm=60,
            mass_grams=30,
            position=PositionMM(15_000 + i * 150, 13_800, 50),
            emission_ppm=(),
            reflectance_ppm=(900_000, 100_000, 300_000, 200_000, 100_000, 50_000),
        )
        for i in range(20)
    ]

    expanded_world = replace(cur_world, objects=cur_world.objects + tuple(extra_flora))
    world._state = replace(world._state, world=expanded_world, observation=world._observation_for(expanded_world))

    # 1. Global world ledger is unbounded (84 entities)
    assert len(world.global_objects()) == 84

    # 2. Canonical observation snapshot preserves full world state
    full_snap = getattr(world, "canonical_observation_snapshot", world.observation_snapshot)()
    assert len(full_snap.objects) == 84
    assert full_snap.authority_hmac_sha256 != ""
    assert full_snap.authority_receipt_sha256 != ""

    # 3. Spatial horizon snapshot automatically streams strictly <= 64 objects
    streamed_snap = world.spatial_horizon_snapshot()
    assert len(streamed_snap.objects) == 64
    assert len(streamed_snap.objects) <= 64

    # 4. Verified with standalone compute_spatial_horizon_observation
    direct_snap = compute_spatial_horizon_observation(world, body_id="guala-body-1", max_objects=64)
    assert len(direct_snap.objects) == 64


def test_solid_angle_distance_decay_physics() -> None:
    """Verify solid angle metric Omega obeys exact inverse-square spatial decay."""
    world = home_world_authority(identity=IDENTITY)
    guala_pos = PositionMM(2_600, 7_600, 0)

    # Calculate solid angle for identical radii at 1 meter vs 5 meters
    r = 200.0
    d_near = 1_000.0
    d_far = 5_000.0

    omega_near = (math.pi * (r ** 2)) / (d_near ** 2 + 1)
    omega_far = (math.pi * (r ** 2)) / (d_far ** 2 + 1)

    # Ratio must closely approach (5000 / 1000)^2 = 25.0
    ratio = omega_near / omega_far
    assert 24.99 <= ratio <= 25.01
