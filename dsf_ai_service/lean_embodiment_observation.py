"""Bounded read-only projection of the exact persistent embodied world."""

from __future__ import annotations

from typing import Any


SCHEMA = "guala.lean_embodiment_observation.v1"
MAX_REGIONS = 16
MAX_PORTALS = 24
MAX_OBJECTS = 64
MAX_BODIES = 4
MAX_BODY_AXES = 64


def _position(value: Any) -> dict[str, int]:
    return {"x_mm": int(value.x), "y_mm": int(value.y), "z_mm": int(value.z)}


def _pose(value: Any) -> dict[str, object]:
    return {
        "heading_millidegrees": int(value.heading_millidegrees),
        "position": _position(value.position),
    }


def lean_embodiment_observation(
    snapshot: Any,
    body_axes: tuple[Any, ...],
) -> dict[str, object]:
    """Project geometry only; never infer actions, meaning, or cognition."""

    regions = tuple(snapshot.regions)
    portals = tuple(snapshot.portals)
    objects = tuple(snapshot.objects)
    bodies = tuple(snapshot.bodies)
    if (
        not 1 <= len(regions) <= MAX_REGIONS
        or len(portals) > MAX_PORTALS
        or len(objects) > MAX_OBJECTS
        or not 1 <= len(bodies) <= MAX_BODIES
        or len(body_axes) > MAX_BODY_AXES
    ):
        raise RuntimeError("embodiment observation exceeded its fixed boundary")
    if len({item.region_id for item in regions}) != len(regions):
        raise RuntimeError("embodiment observation has duplicate regions")
    if len({item.portal_id for item in portals}) != len(portals):
        raise RuntimeError("embodiment observation has duplicate portals")
    if len({item.object_id for item in objects}) != len(objects):
        raise RuntimeError("embodiment observation has duplicate objects")
    if len({item.body_id for item in bodies}) != len(bodies):
        raise RuntimeError("embodiment observation has duplicate bodies")
    if snapshot.self_body_id not in {item.body_id for item in bodies}:
        raise RuntimeError("embodiment observation lost the self body")

    axes = []
    for axis in body_axes:
        if not isinstance(axis, tuple) or len(axis) != 7:
            raise RuntimeError("native body axis changed representation")
        index, name, unit, position, minimum, neutral, maximum = axis
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not isinstance(name, str)
            or not isinstance(unit, str)
            or any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (position, minimum, neutral, maximum)
            )
            or not minimum <= position <= maximum
            or not minimum <= neutral <= maximum
        ):
            raise RuntimeError("native body axis left its exact boundary")
        axes.append({
            "index": index,
            "maximum": maximum,
            "minimum": minimum,
            "name": name,
            "neutral": neutral,
            "position": position,
            "unit": unit,
        })

    return {
        "authority_receipt_sha256": snapshot.authority_receipt_sha256,
        "bodies": [
            {
                "body_id": item.body_id,
                "held_object_id": item.held_object_id,
                "pose": _pose(item.pose),
                "radius_mm": item.radius_mm,
                "reach_mm": item.reach_mm,
            }
            for item in bodies
        ],
        "native_body_axes": axes,
        "objects": [
            {
                "emission_ppm": list(getattr(item, "emission_ppm", ()) or (0,) * 6),
                "held_by_body_id": item.held_by_body_id,
                "object_id": item.object_id,
                "optical_surface": (
                    None
                    if item.optical_surface is None
                    else {
                        "columns": item.optical_surface.columns,
                        "rows": item.optical_surface.rows,
                    }
                ),
                "position": None if item.position is None else _position(item.position),
                "radius_mm": item.radius_mm,
                "reflectance_ppm": list(item.reflectance_ppm),
            }
            for item in objects
        ],
        "portals": [
            {
                "aperture_max_mm": item.aperture_max_mm,
                "aperture_min_mm": item.aperture_min_mm,
                "axis": item.axis,
                "height_mm": item.height_mm,
                "plane_mm": item.plane_mm,
                "portal_id": item.portal_id,
                "region_ids": list(item.region_ids),
            }
            for item in portals
        ],
        "regions": [
            {
                "bounds": {
                    "maximum": _position(item.bounds.maximum),
                    "minimum": _position(item.bounds.minimum),
                },
                "ceiling_height_mm": item.ceiling_height_mm,
                "illumination_ppm": list(item.illumination_ppm),
                "reflectance_ppm": list(item.reflectance_ppm),
                "region_id": item.region_id,
            }
            for item in regions
        ],
        "revision": snapshot.revision,
        "room_id": snapshot.room_id,
        "schema": SCHEMA,
        "self_body_id": snapshot.self_body_id,
        "state_sha256": snapshot.state_sha256,
    }


__all__ = ("SCHEMA", "lean_embodiment_observation")
