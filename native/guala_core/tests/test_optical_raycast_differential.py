#!/usr/bin/env python3
"""Differential test: native Rust optical raycast kernel (cast_focal_rays_native)
vs pure-Python NumPy implementation from dsf_ai_service/substrate/w1_physical_receptors.py.

Asserts exact geometric parity (distance <= 1e-9, normal <= 1e-9, hit point <= 1e-9,
face and box indices bit-exact) across 19,200 focal rays.
"""

import math
import os
import sys
import time

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pytest

import guala_core as gc


def _pure_python_raycast(
    eye,
    heading_rad,
    pitch_rad,
    h_offsets,
    v_offsets,
    room_bounds,
    boxes,
):
    """Pure-Python reference raycast matching w1_physical_receptors.py."""
    min_x, max_x, min_y, max_y, min_z, max_z = room_bounds
    eye_x, eye_y, eye_z = eye
    origin = np.array([eye_x, eye_y, eye_z])
    count = len(h_offsets)

    h = heading_rad + h_offsets
    v = pitch_rad + v_offsets
    cos_v = np.cos(v)
    d = np.stack((cos_v * np.cos(h), cos_v * np.sin(h), np.sin(v)))

    planes = (
        (min_z, 2, (0.0, 0.0, 1.0)),
        (max_z, 2, (0.0, 0.0, -1.0)),
        (min_x, 0, (1.0, 0.0, 0.0)),
        (max_x, 0, (-1.0, 0.0, 0.0)),
        (min_y, 1, (0.0, 1.0, 0.0)),
        (max_y, 1, (0.0, -1.0, 0.0)),
    )

    best = np.full(count, np.inf)
    face = np.full(count, -1, dtype=np.int64)

    for index, (plane, axis, _normal) in enumerate(planes):
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(np.abs(d[axis]) < 1e-9, np.inf, (plane - origin[axis]) / d[axis])
        t = np.where(t > 1e-6, t, np.inf)
        closer = t < best
        best = np.where(closer, t, best)
        face = np.where(closer, index, face)

    hit = face >= 0
    normals_lut = np.array([p[2] for p in planes] + [(0.0, 0.0, 0.0)])
    normal = normals_lut[np.where(hit, face, len(planes))].T
    point = origin[:, None] + d * np.where(hit, best, 0.0)[None, :]

    box_depth = np.full(count, np.inf)
    box_indices = np.full(count, -1, dtype=np.int64)

    for (cx, cy, cz, sx, sy, sz, angle, box_idx) in boxes:
        hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
        centre = np.array([cx, cy, cz])
        ca, sa = math.cos(angle), math.sin(angle)
        o = origin - centre
        o_local = np.array([ca * o[0] + sa * o[1], -sa * o[0] + ca * o[1], o[2]])
        d_local = np.stack((ca * d[0] + sa * d[1], -sa * d[0] + ca * d[1], d[2]))

        near = np.full(count, -np.inf)
        far = np.full(count, np.inf)
        entry_axis = np.zeros(count, dtype=np.int64)

        for axis, half in enumerate((hx, hy, hz)):
            with np.errstate(divide="ignore", invalid="ignore"):
                t1 = (-half - o_local[axis]) / d_local[axis]
                t2 = (half - o_local[axis]) / d_local[axis]
            parallel = np.abs(d_local[axis]) < 1e-12
            inside = np.abs(o_local[axis]) <= half
            lo = np.where(parallel, np.where(inside, -np.inf, np.inf), np.minimum(t1, t2))
            hi = np.where(parallel, np.where(inside, np.inf, -np.inf), np.maximum(t1, t2))
            entry_axis = np.where(lo > near, axis, entry_axis)
            near = np.maximum(near, lo)
            far = np.minimum(far, hi)

        struck = (far >= near) & (near > 1e-6) & (near < best)
        if not struck.any():
            continue

        p_local = o_local[:, None] + d_local * near[None, :]
        sign = np.sign(np.take_along_axis(p_local, entry_axis[None, :], axis=0)[0])
        sign = np.where(sign == 0, 1.0, sign)
        n_local = np.zeros((3, count))
        np.put_along_axis(n_local, entry_axis[None, :], sign[None, :], axis=0)
        n_world = np.stack((ca * n_local[0] - sa * n_local[1], sa * n_local[0] + ca * n_local[1], n_local[2]))

        best = np.where(struck, near, best)
        normal = np.where(struck[None, :], n_world, normal)
        point = np.where(struck[None, :], origin[:, None] + d * near[None, :], point)
        box_depth = np.where(struck, near, box_depth)
        box_indices = np.where(struck, box_idx, box_indices)
        face = np.where(struck, 6, face)

    return best, box_depth, point, normal, face, box_indices


def test_optical_raycast_planes_differential():
    """Verify exact parity for 19,200 rays against 6 room boundary planes."""
    count = 19_200
    h_offsets = np.linspace(-math.radians(30), math.radians(30), count)
    v_offsets = np.linspace(-math.radians(20), math.radians(20), count)
    eye = (100.0, -200.0, 1100.0)
    heading_rad = 0.35
    pitch_rad = -0.15
    room_bounds = (-2500.0, 2500.0, -2500.0, 2500.0, 0.0, 2800.0)
    boxes = []

    # Pure Python
    py_best, py_bdepth, py_pt, py_norm, py_face, py_bidx = _pure_python_raycast(
        eye, heading_rad, pitch_rad, h_offsets, v_offsets, room_bounds, boxes
    )

    # Native Rust
    t0 = time.perf_counter()
    rs_best, rs_bdepth, px, py, pz, nx, ny, nz, rs_face, rs_bidx = gc.cast_focal_rays_native(
        eye,
        heading_rad,
        pitch_rad,
        h_offsets.tolist(),
        v_offsets.tolist(),
        room_bounds,
        boxes,
    )
    t1 = time.perf_counter()
    rs_time_ms = (t1 - t0) * 1000.0

    rs_best = np.asarray(rs_best)
    rs_pt = np.stack((px, py, pz))
    rs_norm = np.stack((nx, ny, nz))
    rs_face = np.asarray(rs_face)

    # Tolerances
    np.testing.assert_allclose(rs_best, py_best, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(rs_pt, py_pt, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(rs_norm, py_norm, rtol=1e-12, atol=1e-9)
    np.testing.assert_array_equal(rs_face, py_face)

    print(f"\n[PARITY PASS] 19,200 rays planes-only in {rs_time_ms:.2f} ms")


def test_optical_raycast_boxes_differential():
    """Verify exact parity for 19,200 rays with rotated boxes and room planes."""
    count = 19_200
    h_offsets = np.linspace(-math.radians(35), math.radians(35), count)
    v_offsets = np.linspace(-math.radians(25), math.radians(25), count)
    eye = (0.0, 0.0, 1000.0)
    heading_rad = 0.2
    pitch_rad = -0.05
    room_bounds = (-3000.0, 3000.0, -3000.0, 3000.0, 0.0, 3000.0)

    boxes = [
        # (cx, cy, cz, sx, sy, sz, angle_rad, box_id)
        (800.0, 200.0, 800.0, 400.0, 400.0, 600.0, 0.35, 101),
        (1200.0, 500.0, 900.0, 500.0, 300.0, 500.0, -0.78, 102),
        (-500.0, 800.0, 500.0, 350.0, 350.0, 400.0, 1.10, 103),
    ]

    # Pure Python
    py_best, py_bdepth, py_pt, py_norm, py_face, py_bidx = _pure_python_raycast(
        eye, heading_rad, pitch_rad, h_offsets, v_offsets, room_bounds, boxes
    )

    # Native Rust
    t0 = time.perf_counter()
    rs_best, rs_bdepth, px, py, pz, nx, ny, nz, rs_face, rs_bidx = gc.cast_focal_rays_native(
        eye,
        heading_rad,
        pitch_rad,
        h_offsets.tolist(),
        v_offsets.tolist(),
        room_bounds,
        boxes,
    )
    t1 = time.perf_counter()
    rs_time_ms = (t1 - t0) * 1000.0

    rs_best = np.asarray(rs_best)
    rs_bdepth = np.asarray(rs_bdepth)
    rs_pt = np.stack((px, py, pz))
    rs_norm = np.stack((nx, ny, nz))
    rs_face = np.asarray(rs_face)
    rs_bidx = np.asarray(rs_bidx)

    # Tolerances
    np.testing.assert_allclose(rs_best, py_best, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(rs_bdepth, py_bdepth, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(rs_pt, py_pt, rtol=1e-12, atol=1e-9)
    np.testing.assert_allclose(rs_norm, py_norm, rtol=1e-12, atol=1e-9)
    np.testing.assert_array_equal(rs_face, py_face)
    np.testing.assert_array_equal(rs_bidx, py_bidx)

    box_hits = int(np.sum(rs_face == 6))
    print(f"\n[PARITY PASS] 19,200 rays with 3 rotated boxes ({box_hits} box hits) in {rs_time_ms:.2f} ms")


if __name__ == "__main__":
    test_optical_raycast_planes_differential()
    test_optical_raycast_boxes_differential()
    print("\nAll optical raycast differential tests passed cleanly.")

