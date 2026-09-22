#!/usr/bin/env python3
"""Differential test for _native_lit_surfaces_focal vs pure-Python _lit_surfaces_focal
on a live physical observation snapshot from home_world_authority.
"""

import copy
import math
import os
import sys
from fractions import Fraction

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pytest

import guala_core as gc
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate import w1_physical_receptors as w1pr

_FOCAL_LIST_CACHE = {}


def _native_lit_surfaces_focal(
    observation,
    *,
    eye,
    body_heading_millidegrees: int,
    retinal_pitch_offset_millidegrees: int,
    current_region,
    illumination_ppm: tuple[int, ...],
    pixels: list,
    site_geometry,
    lights: list,
    occluders: list,
):
    if len(site_geometry) <= w1pr.RETINA_TOTAL_RECEPTOR_COUNT:
        return None
    boxes = [
        item
        for item in observation.objects
        if getattr(item, "shape", "sphere") == "box"
        and item.position is not None
        and current_region.bounds.contains_floor_disc(item.position, 0)
    ]
    assembled = [
        item
        for item in observation.objects
        if getattr(item, "shape", "sphere") == "parts"
        and item.position is not None
        and current_region.bounds.contains_floor_disc(item.position, 0)
    ]
    for other in observation.bodies:
        if other.body_id != observation.self_body_id and other.body_id in w1pr.BODY_PARTS:
            if other.pose.position is not None and current_region.bounds.contains_floor_disc(
                other.pose.position, 0
            ):
                assembled.append(w1pr._BodyAssembledItem(other, w1pr.BODY_PARTS[other.body_id]))
    if not lights and not current_region.looks and not boxes and not assembled:
        return None

    indices, h_offsets, v_offsets = w1pr._focal_rays(site_geometry)
    count = len(indices)
    bounds = current_region.bounds
    bands = len(current_region.reflectance_ppm)
    room_bounds = (
        float(bounds.minimum.x),
        float(bounds.maximum.x),
        float(bounds.minimum.y),
        float(bounds.maximum.y),
        float(bounds.minimum.z),
        float(bounds.maximum.z),
    )
    eye_coords = (float(eye.x), float(eye.y), float(eye.z))
    heading_rad = math.radians(body_heading_millidegrees / 1000.0)
    pitch_rad = math.radians(retinal_pitch_offset_millidegrees / 1000.0)

    boxes_native = []
    for k, item in enumerate(boxes):
        sx, sy, sz = item.size_mm
        hz = sz / 2.0
        centre = (
            float(item.position.x),
            float(item.position.y),
            float(item.position.z + item.elevation_mm) + hz,
        )
        angle = math.radians(item.heading_millidegrees / 1000.0)
        boxes_native.append((centre[0], centre[1], centre[2], float(sx), float(sy), float(sz), angle, k))

    # Fast cached conversion of offsets
    geom_key = id(site_geometry)
    cached_lists = _FOCAL_LIST_CACHE.get(geom_key)
    if cached_lists is None:
        cached_lists = (h_offsets.tolist(), v_offsets.tolist())
        _FOCAL_LIST_CACHE[geom_key] = cached_lists
    h_list, v_list = cached_lists

    best_l, box_depth_l, px, py, pz, nx, ny, nz, face_l, box_idx_l = gc.cast_focal_rays_native(
        eye_coords, heading_rad, pitch_rad, h_list, v_list, room_bounds, boxes_native
    )
    best = np.asarray(best_l, dtype=np.float64)
    box_depth = np.asarray(box_depth_l, dtype=np.float64)
    point = np.stack((px, py, pz))
    normal = np.stack((nx, ny, nz))
    face = np.asarray(face_l, dtype=np.int64)
    box_indices = np.asarray(box_idx_l, dtype=np.int64)
    hit = face >= 0
    face_names = ["floor", "ceiling", "x-min", "x-max", "y-min", "y-max"]

    paint = np.array(current_region.reflectance_ppm, dtype=np.float64)[:, None].repeat(count, axis=1)
    emission = np.zeros((bands, count))
    source = np.full(count, -1, dtype=np.int64)
    has_look = np.zeros(count, dtype=bool)

    for look in current_region.looks:
        face_index = face_names.index(look.face)
        if look.face in ("floor", "ceiling"):
            along, up = point[0], point[1]
        elif look.face.startswith("x"):
            along, up = point[1], point[2]
        else:
            along, up = point[0], point[2]
        inside = (
            hit
            & (face == face_index)
            & ~has_look
            & (along >= look.from_mm)
            & (along <= look.to_mm)
            & (up >= look.low_mm)
            & (up <= look.high_mm)
        )
        if not inside.any():
            continue
        surface = look.surface
        column = np.clip(
            ((along - look.from_mm) * surface.columns / (look.to_mm - look.from_mm)).astype(np.int64),
            0,
            surface.columns - 1,
        )
        row = np.clip(
            ((look.high_mm - up) * surface.rows / (look.high_mm - look.low_mm)).astype(np.int64),
            0,
            surface.rows - 1,
        )
        cells = np.array(surface.cell_palette_indices, dtype=np.int64).reshape(surface.rows, surface.columns)
        palette = np.array(surface.palette_reflectance_ppm, dtype=np.float64)
        paint = np.where(inside[None, :], palette[cells[row, column]].T, paint)
        has_look |= inside

    occluder_index = {entry[4]: k for k, entry in enumerate(occluders) if entry[4] is not None}
    origin = np.array([float(eye.x), float(eye.y), float(eye.z)])
    cos_v = np.cos(pitch_rad + v_offsets)
    d = np.stack((cos_v * np.cos(heading_rad + h_offsets), cos_v * np.sin(heading_rad + h_offsets), np.sin(pitch_rad + v_offsets)))

    for k, item in enumerate(boxes):
        struck = box_indices == k
        if not struck.any():
            continue
        source = np.where(struck, occluder_index.get(item.object_id, -1), source)
        has_look = np.where(struck, False, has_look)
        pattern = item.optical_surface
        if pattern is not None:
            sx, sy, sz = item.size_mm
            hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
            centre = np.array([float(item.position.x), float(item.position.y), float(item.position.z + item.elevation_mm) + hz])
            angle = math.radians(item.heading_millidegrees / 1000.0)
            ca, sa = math.cos(angle), math.sin(angle)
            o = origin - centre
            o_local = np.array([ca * o[0] + sa * o[1], -sa * o[0] + ca * o[1], o[2]])
            d_local = np.stack((ca * d[0] + sa * d[1], -sa * d[0] + ca * d[1], d[2]))
            p_local = o_local[:, None] + d_local * best[None, :]
            n_local = np.stack((ca * normal[0] + sa * normal[1], -sa * normal[0] + ca * normal[1], normal[2]))
            entry_axis = np.argmax(np.abs(n_local), axis=0)
            u = np.where(entry_axis == 0, (p_local[1] + hy) / sy, (p_local[0] + hx) / sx)
            vv = np.where(entry_axis == 2, (p_local[1] + hy) / sy, (p_local[2] + hz) / sz)
            column = np.clip((u * pattern.columns).astype(np.int64), 0, pattern.columns - 1)
            row = np.clip(((1.0 - vv) * pattern.rows).astype(np.int64), 0, pattern.rows - 1)
            cells = np.array(pattern.cell_palette_indices, dtype=np.int64).reshape(pattern.rows, pattern.columns)
            palette = np.array(pattern.palette_reflectance_ppm, dtype=np.float64)
            own = palette[cells[row, column]].T
        else:
            own = np.array(item.reflectance_ppm, dtype=np.float64)[:, None].repeat(count, axis=1)
        paint = np.where(struck[None, :], own, paint)
        glow = getattr(item, "emission_ppm", ()) or ()
        if len(glow) == bands and any(glow):
            emission = np.where(struck[None, :], np.array(glow, dtype=np.float64)[:, None], emission)

    source_part = np.full(count, -1, dtype=np.int64)
    for item in assembled:
        entry, n_world, own, which = w1pr.part_hits(item, origin, d)
        struck = entry < best
        if not struck.any():
            continue
        best = np.where(struck, entry, best)
        normal = np.where(struck[None, :], n_world, normal)
        point = np.where(struck[None, :], origin[:, None] + d * np.where(struck, entry, 0.0)[None, :], point)
        hit |= struck
        box_depth = np.where(struck, entry, box_depth)
        source = np.where(struck, occluder_index.get(item.object_id, -1), source)
        source_part = np.where(struck, which, source_part)
        has_look = np.where(struck, False, has_look)
        paint = np.where(struck[None, :], own, paint)
        glow = getattr(item, "emission_ppm", ()) or ()
        if len(glow) == bands and any(glow):
            emission = np.where(struck[None, :], np.array(glow, dtype=np.float64)[:, None], emission)

    direct = np.zeros((bands, count))
    for light in lights:
        if light.kind == "sun":
            lx = np.full(count, light.x)
            ly = np.full(count, light.y)
            lz = np.full(count, light.z)
            reach = np.full(count, np.inf)
            through = np.zeros(count, dtype=bool)
            for window in current_region.windows:
                axis = 0 if window.wall.startswith("x") else 1
                plane = {
                    "x-min": bounds.minimum.x,
                    "x-max": bounds.maximum.x,
                    "y-min": bounds.minimum.y,
                    "y-max": bounds.maximum.y,
                }[window.wall]
                s_axis = light.x if axis == 0 else light.y
                if abs(s_axis) < 1e-9:
                    continue
                u = (plane - point[axis]) / s_axis
                along = point[1] + light.y * u if axis == 0 else point[0] + light.x * u
                height = point[2] + light.z * u
                passes = (
                    (u > 1e-6)
                    & (along >= window.from_mm)
                    & (along <= window.to_mm)
                    & (height >= window.sill_mm)
                    & (height <= window.top_mm)
                    & ~through
                )
                reach = np.where(passes, u, reach)
                through |= passes
            lit = hit & through
            falloff = np.ones(count)
            skip = None
        else:
            vx, vy, vz = light.x - point[0], light.y - point[1], light.z - point[2]
            dist = np.sqrt(vx * vx + vy * vy + vz * vz)
            lit = hit & (dist > light.radius_mm)
            safe = np.where(dist > 0, dist, 1.0)
            lx, ly, lz = vx / safe, vy / safe, vz / safe
            reach = dist - light.radius_mm
            falloff = np.minimum(w1pr.LAMP_NEAR_GAIN, (w1pr.LAMP_REFERENCE_MM / safe) ** 2)
            skip = light.source_id
        factor = normal[0] * lx + normal[1] * ly + normal[2] * lz
        lit &= factor > 0.0
        if not lit.any():
            continue
        for k, (ox, oy, oz, r, oid, box) in enumerate(occluders):
            if oid is not None and oid == skip:
                continue
            vx, vy, vz = ox - point[0], oy - point[1], oz - point[2]
            u = vx * lx + vy * ly + vz * lz
            cx, cy, cz = vx - u * lx, vy - u * ly, vz - u * lz
            if box is not None and box[0] == "parts":
                candidate = (u > 0.0) & (u < reach + r) & (cx * cx + cy * cy + cz * cz <= r * r)
                if not candidate.any():
                    continue
                skip_part = np.where(source == k, source_part, -1)
                shadow = candidate & w1pr.part_blocks(box[1], point, np.stack((lx, ly, lz)), reach, skip_part)
                lit &= ~shadow
                if not lit.any():
                    break
                continue
            candidate = (u > 0.0) & (u < reach + r) & (cx * cx + cy * cy + cz * cz <= r * r) & (source != k)
            if box is None:
                shadow = candidate & (u < reach)
            else:
                hx, hy, hz, ca, sa = box
                rx, ry, rz = -vx, -vy, -vz
                near, far = w1pr._box_entry(
                    ca * rx + sa * ry,
                    -sa * rx + ca * ry,
                    rz,
                    (hx, hy, hz),
                    ca * lx + sa * ly,
                    -sa * lx + ca * ly,
                    lz,
                )
                shadow = candidate & (far >= near) & (near > 1e-6) & (near < reach)
            lit &= ~shadow
            if not lit.any():
                break
        if not lit.any():
            continue
        gain = np.where(lit, falloff * factor, 0.0)
        for band in range(bands):
            direct[band] += light.ppm[band] * gain

    changed = hit & (has_look | (source >= 0) | (direct > 0.0).any(axis=0))
    if changed.any():
        illumination = np.array(illumination_ppm, dtype=np.float64)[:, None]
        values = np.clip(paint * (illumination + direct) / 1e12 + emission / 1e6, 0.0, 1.0)
        eight_bit = np.rint(values * 255).astype(np.int64)
        for column in np.nonzero(changed)[0]:
            pixels[indices[column]] = tuple(w1pr._EIGHT_BIT[eight_bit[band, column]] for band in range(bands))
    if not boxes and not assembled:
        return None
    depth_by_site = np.full(len(site_geometry), np.inf)
    depth_by_site[np.array(indices)] = box_depth
    return depth_by_site


def test_live_world_lit_surfaces_parity():
    """Verify exact parity between pure-Python and native on live world state."""
    world = home_world_authority(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1")
    obs = world.observation_snapshot()
    body = next(b for b in obs.bodies if b.body_id == obs.self_body_id)
    current_region = next(
        region for region in obs.regions
        if region.region_id == obs.room_id
    )

    lights, occluders = w1pr._room_lights(obs, current_region, None)
    bounce = w1pr._bounce_ppm(current_region, lights)
    lit_illumination = tuple(
        i + b for i, b in zip(current_region.illumination_ppm, bounce, strict=True)
    )

    # Prepare identical inputs
    site_geometry = w1pr.RETINAL_SITE_GEOMETRY + w1pr.FOCAL_RETINAL_SITE_GEOMETRY
    eye = body.pose.position
    heading = body.pose.heading_millidegrees
    pitch = 0

    background = tuple(Fraction(0, 255) for _ in range(6))
    pixels_py = [background for _ in site_geometry]
    pixels_native = [background for _ in site_geometry]

    # Run Python
    depth_py = w1pr._lit_surfaces_focal(
        obs,
        eye=eye,
        body_heading_millidegrees=heading,
        retinal_pitch_offset_millidegrees=pitch,
        current_region=current_region,
        illumination_ppm=lit_illumination,
        pixels=pixels_py,
        site_geometry=site_geometry,
        lights=lights,
        occluders=occluders,
    )

    # Run Native
    depth_native = _native_lit_surfaces_focal(
        obs,
        eye=eye,
        body_heading_millidegrees=heading,
        retinal_pitch_offset_millidegrees=pitch,
        current_region=current_region,
        illumination_ppm=lit_illumination,
        pixels=pixels_native,
        site_geometry=site_geometry,
        lights=lights,
        occluders=occluders,
    )

    # Assert depth_by_site parity
    if depth_py is None:
        assert depth_native is None
    else:
        np.testing.assert_allclose(depth_native, depth_py, rtol=1e-12, atol=1e-9)

    # Assert pixels bit-equality
    assert len(pixels_native) == len(pixels_py)
    for i, (p_nat, p_py) in enumerate(zip(pixels_native, pixels_py)):
        assert p_nat == p_py, f"Pixel mismatch at site {i}: {p_nat} != {p_py}"

    print(f"\n[LIVE WORLD PARITY PASS] All {len(pixels_py)} retinal pixel tuples bit-equal!")


if __name__ == "__main__":
    test_live_world_lit_surfaces_parity()

