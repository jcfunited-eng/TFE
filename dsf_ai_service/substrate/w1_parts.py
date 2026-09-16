"""Ray casting over a thing's parts, all focal rays at once.

A thing of parts (a bear: body, head, ears, limbs; a chair: seat, back, legs) is met
by the eye part by part: for every ray, the nearest entry into any part, with that
face's normal and the part's paint. Boxes by the slab test in the thing's frame,
spheres by the quadratic, vertical cylinders by the circle in plan and the caps.
Geometry only; nothing is stored. Shared by the drawing pass and the shadow tests.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np


def _frame(item: Any) -> tuple[np.ndarray, float, float]:
    """The thing's floor point (with its elevation) and its rotation about the vertical."""
    origin = np.array([float(item.position.x), float(item.position.y), float(item.position.z + item.elevation_mm)])
    angle = math.radians(item.heading_millidegrees / 1000.0)
    return origin, math.cos(angle), math.sin(angle)


def _to_local(vectors: np.ndarray, ca: float, sa: float) -> np.ndarray:
    """World directions or offsets into the thing's frame (rotate by minus its heading)."""
    return np.stack((ca * vectors[0] + sa * vectors[1], -sa * vectors[0] + ca * vectors[1], vectors[2]))


def _to_world(vectors: np.ndarray, ca: float, sa: float) -> np.ndarray:
    return np.stack((ca * vectors[0] - sa * vectors[1], sa * vectors[0] + ca * vectors[1], vectors[2]))


def _box_hits(o: np.ndarray, d: np.ndarray, half: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Entry distance, exit distance and entering normal (local frame) of rays against a box
    centred at the local origin; entry is +inf where the ray misses."""
    near = np.full(d.shape[1], -np.inf)
    far = np.full(d.shape[1], np.inf)
    entry_axis = np.zeros(d.shape[1], dtype=np.int64)
    for axis, h in enumerate(half):
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (-h - o[axis]) / d[axis]
            t2 = (h - o[axis]) / d[axis]
        parallel = np.abs(d[axis]) < 1e-12
        inside = np.abs(o[axis]) <= h
        lo = np.where(parallel, np.where(inside, -np.inf, np.inf), np.minimum(t1, t2))
        hi = np.where(parallel, np.where(inside, np.inf, -np.inf), np.maximum(t1, t2))
        entry_axis = np.where(lo > near, axis, entry_axis)
        near = np.maximum(near, lo)
        far = np.minimum(far, hi)
    struck = (far >= near) & (near > 1e-6)
    entry = np.where(struck, near, np.inf)
    point = o + d * np.where(struck, near, 0.0)[None, :]
    sign = np.sign(np.take_along_axis(point, entry_axis[None, :], axis=0)[0])
    sign = np.where(sign == 0, 1.0, sign)
    normal = np.zeros((3, d.shape[1]))
    np.put_along_axis(normal, entry_axis[None, :], sign[None, :], axis=0)
    return entry, far, normal


def _sphere_hits(o: np.ndarray, d: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Entry, exit and entering normal against a sphere at the local origin (rays are unit)."""
    b = np.sum(o * d, axis=0)
    c = np.sum(o * o, axis=0) - radius * radius
    disc = b * b - c
    root = np.sqrt(np.where(disc >= 0.0, disc, 0.0))
    t_in = -b - root
    t_out = -b + root
    struck = (disc >= 0.0) & (t_in > 1e-6)
    entry = np.where(struck, t_in, np.inf)
    point = o + d * np.where(struck, t_in, 0.0)[None, :]
    normal = point / max(radius, 1e-9)
    return entry, np.where(struck, t_out, -np.inf), normal


def _cylinder_hits(o: np.ndarray, d: np.ndarray, radius: float, half_height: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Entry, exit and entering normal against a vertical cylinder at the local origin:
    the side (a circle in plan) clipped by the two caps."""
    a = d[0] * d[0] + d[1] * d[1]
    b = o[0] * d[0] + o[1] * d[1]
    c = o[0] * o[0] + o[1] * o[1] - radius * radius
    disc = b * b - a * c
    with np.errstate(divide="ignore", invalid="ignore"):
        root = np.sqrt(np.where(disc >= 0.0, disc, 0.0))
        side_in = np.where(a > 1e-12, (-b - root) / a, np.where(c <= 0.0, -np.inf, np.inf))
        side_out = np.where(a > 1e-12, (-b + root) / a, np.where(c <= 0.0, np.inf, -np.inf))
        side_in = np.where((a > 1e-12) & (disc < 0.0), np.inf, side_in)
        side_out = np.where((a > 1e-12) & (disc < 0.0), -np.inf, side_out)
        cap_lo = (-half_height - o[2]) / d[2]
        cap_hi = (half_height - o[2]) / d[2]
    vertical_parallel = np.abs(d[2]) < 1e-12
    inside_z = np.abs(o[2]) <= half_height
    cap_in = np.where(vertical_parallel, np.where(inside_z, -np.inf, np.inf), np.minimum(cap_lo, cap_hi))
    cap_out = np.where(vertical_parallel, np.where(inside_z, np.inf, -np.inf), np.maximum(cap_lo, cap_hi))
    near = np.maximum(side_in, cap_in)
    far = np.minimum(side_out, cap_out)
    struck = (far >= near) & (near > 1e-6)
    entry = np.where(struck, near, np.inf)
    point = o + d * np.where(struck, near, 0.0)[None, :]
    on_cap = cap_in >= side_in
    radial = np.stack((point[0], point[1], np.zeros_like(point[2])))
    radial = radial / np.maximum(np.sqrt(np.sum(radial * radial, axis=0)), 1e-9)[None, :]
    cap_normal = np.stack((np.zeros_like(point[2]), np.zeros_like(point[2]), np.sign(point[2] + 0.0)))
    cap_normal[2] = np.where(cap_normal[2] == 0, 1.0, cap_normal[2])
    normal = np.where(on_cap[None, :], cap_normal, radial)
    return entry, np.where(struck, far, -np.inf), normal


def part_hits(item: Any, origin: np.ndarray, d: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """For every ray from `origin` along `d` (3 x N, unit): the distance to the nearest part
    of the thing (+inf where none), the entering normal in the world frame (3 x N), the paint
    of the part struck (bands x N; the thing's own where the part declares none), and the index
    of the part struck (-1 where none). Only the rays that enter the thing's bounding sphere are
    cast against its parts."""
    base, ca, sa = _frame(item)
    count = d.shape[1]
    best = np.full(count, np.inf)
    normal = np.zeros((3, count))
    paint = np.array(item.reflectance_ppm, dtype=np.float64)[:, None].repeat(count, axis=1)
    which = np.full(count, -1, dtype=np.int64)
    # The quick reject: a sphere around the thing's floor point that holds every part.
    reach = bounding_radius(item)
    centre = base.copy(); centre[2] += _centre_height(item)
    rel = (origin - centre)[:, None]
    b = np.sum(rel * d, axis=0)
    c = float(np.sum(rel * rel)) - reach * reach
    disc = b * b - c
    near_enough = (disc >= 0.0) & ((-b + np.sqrt(np.where(disc >= 0.0, disc, 0.0))) > 1e-6)
    subset = np.nonzero(near_enough)[0]
    if subset.size == 0:
        return best, normal, paint, which
    d_sub = d[:, subset]
    o_local = _to_local((origin - base)[:, None], ca, sa)
    d_local = _to_local(d_sub, ca, sa)
    best_sub = np.full(subset.size, np.inf)
    normal_sub = np.zeros((3, subset.size))
    paint_sub = paint[:, subset].copy()
    which_sub = np.full(subset.size, -1, dtype=np.int64)
    for index, part in enumerate(item.parts):
        part_centre = np.array([float(v) for v in part.offset_mm])[:, None]
        o = o_local - part_centre
        if part.kind == "box":
            entry, _far, n_local = _box_hits(o, d_local, tuple(v / 2.0 for v in part.size_mm))
        elif part.kind == "sphere":
            entry, _far, n_local = _sphere_hits(o, d_local, part.size_mm[0] / 2.0)
        else:
            entry, _far, n_local = _cylinder_hits(o, d_local, part.size_mm[0] / 2.0, part.size_mm[2] / 2.0)
        closer = entry < best_sub
        if not closer.any():
            continue
        best_sub = np.where(closer, entry, best_sub)
        normal_sub = np.where(closer[None, :], _to_world(n_local, ca, sa), normal_sub)
        if part.reflectance_ppm:
            own = np.array(part.reflectance_ppm, dtype=np.float64)[:, None]
            paint_sub = np.where(closer[None, :], own, paint_sub)
        which_sub = np.where(closer, index, which_sub)
    best[subset] = best_sub
    normal[:, subset] = normal_sub
    paint[:, subset] = paint_sub
    which[subset] = which_sub
    return best, normal, paint, which


def part_blocks(item: Any, points: np.ndarray, toward: np.ndarray, reach: np.ndarray, skip_part: np.ndarray | None = None) -> np.ndarray:
    """Whether the segment from each point toward the light (unit direction `toward`, length
    `reach`) enters any part of the thing; a ray's own part (skip_part index) never blocks it.
    Only the segments that pass the thing's bounding sphere are tested part by part."""
    base, ca, sa = _frame(item)
    count = points.shape[1]
    blocked = np.zeros(count, dtype=bool)
    radius = bounding_radius(item)
    centre = base.copy(); centre[2] += _centre_height(item)
    rel = centre[:, None] - points
    u = np.sum(rel * toward, axis=0)
    perp = rel - toward * u[None, :]
    candidate = (u > 0.0) & (u < reach + radius) & (np.sum(perp * perp, axis=0) <= radius * radius)
    subset = np.nonzero(candidate)[0]
    if subset.size == 0:
        return blocked
    o_local = _to_local(points[:, subset] - base[:, None], ca, sa)
    d_local = _to_local(toward[:, subset], ca, sa)
    reach_sub = reach[subset] if np.ndim(reach) else np.full(subset.size, float(reach))
    skip_sub = skip_part[subset] if skip_part is not None else None
    hit_any = np.zeros(subset.size, dtype=bool)
    for index, part in enumerate(item.parts):
        part_centre = np.array([float(v) for v in part.offset_mm])[:, None]
        o = o_local - part_centre
        if part.kind == "box":
            entry, _far, _n = _box_hits(o, d_local, tuple(v / 2.0 for v in part.size_mm))
        elif part.kind == "sphere":
            entry, _far, _n = _sphere_hits(o, d_local, part.size_mm[0] / 2.0)
        else:
            entry, _far, _n = _cylinder_hits(o, d_local, part.size_mm[0] / 2.0, part.size_mm[2] / 2.0)
        hit = np.isfinite(entry) & (entry < reach_sub)
        if skip_sub is not None:
            hit &= skip_sub != index
        hit_any |= hit
    blocked[subset] = hit_any
    return blocked


def _centre_height(item: Any) -> float:
    """The height above the thing's floor point of the middle of its parts."""
    if not item.parts:
        return 0.0
    tops = [part.offset_mm[2] + (part.size_mm[2] / 2.0 if part.kind != "sphere" else part.size_mm[0] / 2.0) for part in item.parts]
    bottoms = [part.offset_mm[2] - (part.size_mm[2] / 2.0 if part.kind != "sphere" else part.size_mm[0] / 2.0) for part in item.parts]
    return (max(tops) + min(bottoms)) / 2.0


def bounding_radius(item: Any) -> float:
    """A sphere around the middle of the thing's parts that contains every part (for a quick reject)."""
    middle = _centre_height(item)
    reach = 0.0
    for part in item.parts:
        if part.kind == "box":
            extent = math.sqrt(sum(v * v for v in part.size_mm)) / 2.0
        else:
            extent = math.hypot(part.size_mm[0] / 2.0, part.size_mm[2] / 2.0)
        reach = max(reach, math.sqrt(part.offset_mm[0] ** 2 + part.offset_mm[1] ** 2 + (part.offset_mm[2] - middle) ** 2) + extent)
    return reach
