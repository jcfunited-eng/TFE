#!/usr/bin/env python3
"""tests/test_tdw_vr_bridge.py — ThreeDWorld (TDW) / VR Visual Streaming Bridge Verification.

Physics & Verification Invariants:
1. Coordinate Invariance: Integer millimeters (Z up) maps to Unity left-handed meters (Y up).
2. Spectral Invariance: 6-channel optical reflectance PPM maps to physical RGBA color floats.
3. Aperture Invariance: Real-time VR visual streaming strictly respects <= 64 object receptor ceiling.
4. Architectural Invariance: Open-sky exterior regions omit ceilings while interior rooms have ceilings.
5. Photometric Invariance: High-emission sources (>100,000 ppm) spawn point lights alongside directional sun.
6. Cryptographic Invariance: Every VR frame packet carries a valid SHA-256 authority receipt.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from dsf_ai_service.guala_home_world import (
    home_world_authority,
)
from dsf_ai_service.guala_tdw_bridge import (
    VRVisualFramePacket,
    build_tdw_architecture_commands,
    build_tdw_avatar_commands,
    build_tdw_lighting_commands,
    build_tdw_object_commands,
    export_tdw_scene_json,
    generate_tdw_scene_graph,
    mm_to_unity_meters,
    reflectance_ppm_to_rgba,
    stream_vr_visual_frame,
)

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_mm_to_unity_meters_coordinate_transformation() -> None:
    """Verify integer mm coordinates (Z up) map to Unity meters (Y up)."""
    # 1. Standard room coordinate
    u1 = mm_to_unity_meters(2500, 7500, 1100)
    assert u1 == {"x": 2.5, "y": 1.1, "z": 7.5}

    # 2. Origin
    u0 = mm_to_unity_meters(0, 0, 0)
    assert u0 == {"x": 0.0, "y": 0.0, "z": 0.0}

    # 3. Walkway coordinate
    u_walkway = mm_to_unity_meters(10_000, 19_000, 450)
    assert u_walkway == {"x": 10.0, "y": 0.45, "z": 19.0}


def test_optical_reflectance_ppm_to_rgba() -> None:
    """Verify 6-channel spectral reflectance PPM maps to physical RGBA color floats."""
    # 1. 6-channel spectrum: [700nm, 620nm, 550nm, 490nm, 440nm, 400nm]
    ppm = (800_000, 700_000, 400_000, 300_000, 200_000, 100_000)
    rgba = reflectance_ppm_to_rgba(ppm)
    assert rgba["r"] == 0.8
    assert rgba["g"] == 0.4
    assert rgba["b"] == 0.2
    assert rgba["a"] == 1.0

    # 2. Fallback empty sequence
    rgba_empty = reflectance_ppm_to_rgba(())
    assert rgba_empty == {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0}

    # 3. Clamping beyond 1.0
    rgba_clamp = reflectance_ppm_to_rgba((1_200_000, 0, 1_500_000, 0, 0, 0))
    assert rgba_clamp["r"] == 1.0
    assert rgba_clamp["g"] == 1.0
    assert rgba_clamp["b"] == 0.0


def test_tdw_architecture_commands() -> None:
    """Verify 10 regions produce floor slabs and outdoor regions omit ceiling slabs."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world
    commands = build_tdw_architecture_commands(cur_w.regions, cur_w.portals, base_id=100)

    # 1. First command is scene load
    assert commands[0]["$type"] == "load_scene"
    assert commands[0]["scene_name"] == "empty_scene"

    # 2. Check floor and ceiling creation
    primitives = [c for c in commands if c.get("$type") == "load_primitive_from_resources"]
    # 10 regions = 10 floors; 8 indoor regions have ceilings (backyard and walkway omit ceilings)
    # Total primitive slabs = 10 floors + 8 ceilings = 18 slabs
    assert len(primitives) == 18

    # Verify walkway floor slab exists
    walkway_floor = next(
        p for p in primitives
        if p["position"]["x"] == 10.0 and p["position"]["z"] == 19.0 and p["position"]["y"] == 0.0
    )
    assert walkway_floor["primitive_type"] == "Cube"
    assert walkway_floor["scale"]["x"] == 20.0  # 20_000 mm
    assert walkway_floor["scale"]["z"] == 6.0   # 6_000 mm


def test_tdw_lighting_commands() -> None:
    """Verify directional sun lighting and point lights for high-emission sources."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world
    commands = build_tdw_lighting_commands(cur_w.regions, cur_w.objects, base_id=500)

    # 1. Sun light
    sun = next(c for c in commands if c.get("$type") == "set_directional_light")
    assert sun["intensity"] == 1.2

    # 2. Point lights
    point_lights = [c for c in commands if c.get("$type") == "add_point_light"]
    assert len(point_lights) >= 3  # walkway-lantern, living-lamp, hallway-lamp

    # Verify walkway lantern point light at (8.5, 1.2, 17.0)
    lantern_light = next(
        pl for pl in point_lights
        if pl["position"]["x"] == 8.5 and pl["position"]["z"] == 17.0
    )
    assert lantern_light["position"]["y"] == 1.2  # 1_200 mm elevation
    assert lantern_light["range"] == 4.5


def test_tdw_object_commands() -> None:
    """Verify canonical TDW primitive commands for box, cylinder, and sphere objects."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world
    commands = build_tdw_object_commands(cur_w.objects, base_id=1000)

    prims = [c for c in commands if c.get("$type") == "load_primitive_from_resources"]
    assert len(prims) == len(cur_w.objects)

    # Check walkway bench (box -> Cube)
    bench_prim = next(p for p in prims if p["position"]["x"] == 10.0 and p["position"]["z"] == 19.0)
    assert bench_prim["primitive_type"] == "Cube"
    assert bench_prim["scale"]["x"] == 1.2   # 1200 mm
    assert bench_prim["scale"]["z"] == 0.45  # 450 mm
    assert bench_prim["scale"]["y"] == 0.45  # 450 mm height

    # Check garden butterfly (elevation 450mm -> Unity Y = 0.45m)
    butterfly_prim = next(p for p in prims if p["position"]["x"] == 16.5 and p["position"]["z"] == 11.0)
    assert butterfly_prim["primitive_type"] == "Sphere"
    assert butterfly_prim["position"]["y"] == 0.45


def test_tdw_avatar_camera_commands() -> None:
    """Verify TDW avatar camera is mounted at Guala's retinal receptor location."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world
    body = cur_w.bodies[0]

    avatar_cmds = build_tdw_avatar_commands(body, avatar_id="guala_retinal_avatar")
    cmd_types = [c["$type"] for c in avatar_cmds]
    assert "create_avatar" in cmd_types
    assert "teleport_avatar_to" in cmd_types
    assert "rotate_avatar_to_euler_angles" in cmd_types
    assert "set_aperture" in cmd_types
    assert "set_focal_length" in cmd_types

    teleport = next(c for c in avatar_cmds if c["$type"] == "teleport_avatar_to")
    # Body at (2800, 7600, 0) with standing eye offset z=1100 -> Unity (2.8, 1.1, 7.6)
    assert teleport["position"] == {"x": 2.8, "y": 1.1, "z": 7.6}


def test_realtime_vr_visual_frame_streaming_bounded_aperture() -> None:
    """Verify real-time VR frame streaming strictly bounds visible candidate objects to <= 64."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    cur_w = world._state.world
    assert len(cur_w.objects) == 69  # 64 base + 3 garden (bird, butterfly, flowers) + 2 walkway (bench, lantern)

    frame: VRVisualFramePacket = stream_vr_visual_frame(world, body_id="guala-body-1", tick=42)

    # 1. Structural bounding invariant
    assert frame.visible_object_count <= 64
    assert len(frame.visible_object_ids) <= 64
    assert frame.visible_object_count == len(frame.visible_object_ids)

    # 2. Retinal camera frame
    assert frame.camera_position == {"x": 2.8, "y": 1.1, "z": 7.6}
    assert frame.camera_rotation["y"] == 0.0

    # 3. Cryptographic receipt
    assert len(frame.authority_receipt_sha256) == 64
    int(frame.authority_receipt_sha256, 16)  # Valid hex

    # 4. TDW command stream
    assert len(frame.tdw_commands) > 0
    # Includes avatar commands
    avatar_create = next(c for c in frame.tdw_commands if c.get("$type") == "create_avatar")
    assert avatar_create["id"] == "guala_retinal_avatar"


def test_export_tdw_scene_json(tmp_path: Path) -> None:
    """Verify TDW scene graph JSON export serialization and file output."""
    world = home_world_authority(identity=IDENTITY, expand_garden=True, expand_walkway=True)
    json_path = tmp_path / "scene_tdw.json"

    dumped = export_tdw_scene_json(world, file_path=json_path)
    assert json_path.exists()

    parsed = json.loads(dumped)
    assert parsed["format"] == "threedworld_scene_v1"
    assert parsed["command_count"] == len(parsed["commands"])
    assert parsed["command_count"] > 100

    file_content = json.loads(json_path.read_text(encoding="utf-8"))
    assert file_content == parsed
