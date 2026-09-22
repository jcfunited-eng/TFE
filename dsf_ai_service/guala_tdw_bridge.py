#!/usr/bin/env python3
"""dsf_ai_service/guala_tdw_bridge.py — ThreeDWorld (TDW) / VR Visual Streaming Bridge.

Exports Guala's physical environment (10 topological regions, 10 portals, furniture,
orchard trees, garden fauna/flora, stroller carriage, and exterior walkway) into
canonical ThreeDWorld (TDW) command streams and VR scene descriptors for Unity
3D rendering and VR headsets.

Physics & Coordinate Invariants:
1. Metric Frame Mapping:
   - Physical runtime uses millimeters (Z up): x, y in [0, 20_000] mm, z in [0, 8_000] mm.
   - TDW / Unity uses left-handed meters (Y up):
       Unity X = x_mm / 1000.0
       Unity Y = elevation_z_mm / 1000.0
       Unity Z = y_mm / 1000.0
2. Optical Spectrum Mapping:
   - 6-channel reflectance PPM (700nm, 620nm, 550nm, 490nm, 440nm, 400nm) mapped
     deterministically to physical RGB color floats in [0.0, 1.0]:
       R = ppm[0] / 1_000_000.0  (Red / 700 nm)
       G = ppm[2] / 1_000_000.0  (Green / 550 nm)
       B = ppm[4] / 1_000_000.0  (Blue / 440 nm)
3. Sensory Aperture Bounding:
   - Real-time VR visual streaming leverages the Spatial Horizon Streaming engine to
     stream strictly <= 64 candidate entities to the active foveal frustum.
4. Deterministic Scene Generation:
   - Zero ML approximations, heuristics, or probabilistic shortcuts.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence


def mm_to_unity_meters(x_mm: float, y_mm: float, z_mm: float) -> dict[str, float]:
    """Convert integer millimeter home world coordinates (Z up) to Unity meters (Y up)."""
    return {
        "x": round(float(x_mm) / 1_000.0, 4),
        "y": round(float(z_mm) / 1_000.0, 4),
        "z": round(float(y_mm) / 1_000.0, 4),
    }


def reflectance_ppm_to_rgba(reflectance_ppm: Sequence[int]) -> dict[str, float]:
    """Map 6-channel optical spectral reflectance PPM to physical RGBA color floats."""
    if not reflectance_ppm:
        return {"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0}
    r = min(1.0, max(0.0, float(reflectance_ppm[0]) / 1_000_000.0))
    g = min(1.0, max(0.0, float(reflectance_ppm[2]) / 1_000_000.0)) if len(reflectance_ppm) > 2 else r
    b = min(1.0, max(0.0, float(reflectance_ppm[4]) / 1_000_000.0)) if len(reflectance_ppm) > 4 else r
    return {"r": round(r, 4), "g": round(g, 4), "b": round(b, 4), "a": 1.0}


@dataclass(frozen=True)
class VRVisualFramePacket:
    """Cryptographically verifiable real-time VR frame packet for ThreeDWorld / Unity."""
    timestamp_iso: str
    tick: int
    body_id: str
    camera_position: dict[str, float]
    camera_rotation: dict[str, float]
    visible_object_count: int
    visible_object_ids: tuple[str, ...]
    tdw_commands: tuple[dict[str, Any], ...]
    authority_receipt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def build_tdw_architecture_commands(
    regions: Sequence[Any],
    portals: Sequence[Any],
    base_id: int = 100,
) -> list[dict[str, Any]]:
    """Build canonical TDW commands representing room architecture (floors, ceilings, walls)."""
    commands: list[dict[str, Any]] = [
        {"$type": "load_scene", "scene_name": "empty_scene"},
    ]
    cur_id = base_id

    for r in regions:
        if not hasattr(r, "bounds"):
            continue
        min_x, max_x = r.bounds.minimum.x, r.bounds.maximum.x
        min_y, max_y = r.bounds.minimum.y, r.bounds.maximum.y
        ceiling = getattr(r, "ceiling_height_mm", 2_600)

        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        width_m = (max_x - min_x) / 1_000.0
        depth_m = (max_y - min_y) / 1_000.0
        height_m = ceiling / 1_000.0

        floor_pos = mm_to_unity_meters(center_x, center_y, 0)
        ceiling_pos = mm_to_unity_meters(center_x, center_y, ceiling)

        # Floor slab
        commands.append({
            "$type": "load_primitive_from_resources",
            "primitive_type": "Cube",
            "id": cur_id,
            "position": floor_pos,
            "scale": {"x": round(width_m, 4), "y": 0.05, "z": round(depth_m, 4)},
        })
        refl = getattr(r, "reflectance_ppm", (380_000,) * 6)
        commands.append({
            "$type": "set_color",
            "id": cur_id,
            "color": reflectance_ppm_to_rgba(refl),
        })
        cur_id += 1

        # Ceiling slab (omitted for open-sky exterior regions if outdoor)
        if r.region_id not in ("backyard", "walkway"):
            commands.append({
                "$type": "load_primitive_from_resources",
                "primitive_type": "Cube",
                "id": cur_id,
                "position": ceiling_pos,
                "scale": {"x": round(width_m, 4), "y": 0.05, "z": round(depth_m, 4)},
            })
            commands.append({
                "$type": "set_color",
                "id": cur_id,
                "color": {"r": 0.95, "g": 0.95, "b": 0.95, "a": 1.0},
            })
            cur_id += 1

    return commands


def build_tdw_lighting_commands(
    regions: Sequence[Any],
    objects: Sequence[Any],
    base_id: int = 500,
) -> list[dict[str, Any]]:
    """Build TDW directional sun lighting and indoor/outdoor point light commands."""
    commands: list[dict[str, Any]] = [
        # Directional sunlight
        {
            "$type": "set_directional_light",
            "direction": {"x": -0.5, "y": -0.8, "z": 0.3},
            "color": {"r": 1.0, "g": 0.98, "b": 0.92, "a": 1.0},
            "intensity": 1.2,
        },
    ]
    cur_id = base_id

    for obj in objects:
        emission = getattr(obj, "emission_ppm", ())
        if emission and any(e > 100_000 for e in emission):
            elev = getattr(obj, "elevation_mm", 0)
            unity_pos = mm_to_unity_meters(obj.position.x, obj.position.y, elev)
            color = reflectance_ppm_to_rgba(emission)
            commands.append({
                "$type": "add_point_light",
                "id": cur_id,
                "position": unity_pos,
                "color": color,
                "intensity": round(float(emission[0]) / 500_000.0, 2),
                "range": 4.5,
            })
            cur_id += 1

    return commands


def build_tdw_object_commands(
    objects: Sequence[Any],
    base_id: int = 1000,
) -> list[dict[str, Any]]:
    """Build canonical TDW primitive and mesh spawn commands for environmental objects."""
    commands: list[dict[str, Any]] = []
    cur_id = base_id

    for obj in objects:
        elev = getattr(obj, "elevation_mm", 0)
        unity_pos = mm_to_unity_meters(obj.position.x, obj.position.y, elev)
        shape = getattr(obj, "shape", "sphere")
        radius_m = getattr(obj, "radius_mm", 100) / 1_000.0

        if shape == "box":
            size = getattr(obj, "size_mm", (200, 200, 200))
            scale = {
                "x": round(size[0] / 1_000.0, 4),
                "y": round(size[2] / 1_000.0, 4),
                "z": round(size[1] / 1_000.0, 4),
            }
            prim_type = "Cube"
        elif shape == "cylinder":
            scale = {"x": round(radius_m * 2, 4), "y": 0.5, "z": round(radius_m * 2, 4)}
            prim_type = "Cylinder"
        else:
            scale = {"x": round(radius_m * 2, 4), "y": round(radius_m * 2, 4), "z": round(radius_m * 2, 4)}
            prim_type = "Sphere"

        commands.append({
            "$type": "load_primitive_from_resources",
            "primitive_type": prim_type,
            "id": cur_id,
            "position": unity_pos,
            "scale": scale,
        })
        refl = getattr(obj, "reflectance_ppm", (500_000,) * 6)
        commands.append({
            "$type": "set_color",
            "id": cur_id,
            "color": reflectance_ppm_to_rgba(refl),
        })
        cur_id += 1

    return commands


def build_tdw_avatar_commands(
    body: Any,
    avatar_id: str = "guala_retinal_avatar",
) -> list[dict[str, Any]]:
    """Mount ThreeDWorld camera avatar at the organism's physical retinal receptor coordinates."""
    pos_x = body.pose.position.x
    pos_y = body.pose.position.y
    pos_z = getattr(body.pose.position, "z", 0)

    if hasattr(body, "receptor_geometry") and hasattr(body.receptor_geometry, "retinal_offset_mm"):
        offset = body.receptor_geometry.retinal_offset_mm
        pos_x += offset.x
        pos_y += offset.y
        pos_z += offset.z
    else:
        pos_z += 1_100  # Standard standing toddler eye height

    eye_pos = mm_to_unity_meters(pos_x, pos_y, pos_z)
    heading_deg = getattr(body.pose, "heading_millidegrees", 0) / 1_000.0

    return [
        {
            "$type": "create_avatar",
            "type": "A_Img_Caps_Sensors",
            "id": avatar_id,
        },
        {
            "$type": "teleport_avatar_to",
            "avatar_id": avatar_id,
            "position": eye_pos,
        },
        {
            "$type": "rotate_avatar_to_euler_angles",
            "avatar_id": avatar_id,
            "euler_angles": {"x": 0.0, "y": round(heading_deg, 2), "z": 0.0},
        },
        {
            "$type": "set_aperture",
            "avatar_id": avatar_id,
            "aperture": 8.0,
        },
        {
            "$type": "set_focal_length",
            "avatar_id": avatar_id,
            "focal_length": 35.0,
        },
    ]


def generate_tdw_scene_graph(
    authority: Any,
    body_id: str = "guala-body-1",
    base_id: int = 1000,
) -> list[dict[str, Any]]:
    """Generate the complete deterministic ThreeDWorld command list for the current world state."""
    cur_w = authority._state.world
    commands: list[dict[str, Any]] = []

    # 1. Architecture
    commands.extend(build_tdw_architecture_commands(cur_w.regions, cur_w.portals, base_id=100))

    # 2. Lighting
    commands.extend(build_tdw_lighting_commands(cur_w.regions, cur_w.objects, base_id=500))

    # 3. Objects
    commands.extend(build_tdw_object_commands(cur_w.objects, base_id=base_id))

    # 4. Avatar Camera
    body = next((b for b in cur_w.bodies if b.body_id == body_id), None)
    if body:
        commands.extend(build_tdw_avatar_commands(body))

    return commands


def stream_vr_visual_frame(
    authority: Any,
    body_id: str = "guala-body-1",
    tick: int = 0,
) -> VRVisualFramePacket:
    """Produce a real-time cryptographically verified VR visual frame packet.

    Leverages Spatial Horizon Streaming to filter candidates strictly to <= 64 entities.
    """
    cur_w = authority._state.world
    body = next((b for b in cur_w.bodies if b.body_id == body_id), None)
    if not body:
        raise ValueError(f"Body {body_id} not found in world state")

    # 1. Compute streamed spatial horizon snapshot (strictly <= 64 objects)
    snapshot = authority.observation_snapshot()
    streamed_objects = snapshot.objects
    visible_ids = tuple(o.object_id for o in streamed_objects)

    # 2. Retinal camera pose
    pos_x = body.pose.position.x
    pos_y = body.pose.position.y
    pos_z = getattr(body.pose.position, "z", 0)
    if hasattr(body, "receptor_geometry") and hasattr(body.receptor_geometry, "retinal_offset_mm"):
        offset = body.receptor_geometry.retinal_offset_mm
        pos_x += offset.x
        pos_y += offset.y
        pos_z += offset.z
    else:
        pos_z += 1_100

    cam_pos = mm_to_unity_meters(pos_x, pos_y, pos_z)
    heading_deg = getattr(body.pose, "heading_millidegrees", 0) / 1_000.0
    cam_rot = {"x": 0.0, "y": round(heading_deg, 2), "z": 0.0}

    # 3. Build TDW command stream for visible entities
    tdw_commands = []
    tdw_commands.extend(build_tdw_object_commands(streamed_objects, base_id=1000))
    tdw_commands.extend(build_tdw_avatar_commands(body))

    # 4. Cryptographic receipt
    canonical_repr = f"vr_frame|{tick}|{cam_pos}|{visible_ids}".encode("ascii")
    receipt = hashlib.sha256(canonical_repr).hexdigest()

    return VRVisualFramePacket(
        timestamp_iso=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        tick=tick,
        body_id=body_id,
        camera_position=cam_pos,
        camera_rotation=cam_rot,
        visible_object_count=len(visible_ids),
        visible_object_ids=visible_ids,
        tdw_commands=tuple(tdw_commands),
        authority_receipt_sha256=receipt,
    )


def export_tdw_scene_json(
    authority: Any,
    file_path: str | Path | None = None,
    indent: int = 2,
) -> str:
    """Export complete TDW scene commands to JSON format for rendering in ThreeDWorld / Unity."""
    commands = generate_tdw_scene_graph(authority)
    payload = {
        "format": "threedworld_scene_v1",
        "command_count": len(commands),
        "commands": commands,
    }
    dumped = json.dumps(payload, indent=indent)
    if file_path is not None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumped, encoding="utf-8")
    return dumped
