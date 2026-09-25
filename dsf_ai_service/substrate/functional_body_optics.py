"""Float64 surface-aperture geometry under Joe's numerical-optics approval.

Integrates convex spherical halfspaces, not a recognition or visibility engine.
The caller supplies visible, disjoint surface regions and their physical material;
overlapping/occluded regions must not simply be summed. No scene/state is retained.
Directions and normals are in the actual eye frame: x forward, y left, z up.
"""
from __future__ import annotations

import math
import numpy as np


def _unit_rows(values, name):
    if (not isinstance(values, np.ndarray) or values.dtype != np.dtype(np.float64)
            or values.ndim != 2 or values.shape[1] != 3 or not len(values)
            or not np.isfinite(values).all()):
        raise ValueError(f"finite packed float64 {name} required")
    scale = np.max(np.abs(values), axis=1)
    if np.any(scale == 0):
        raise ValueError(f"zero {name}")
    result = values / scale[:, None]
    return result / np.linalg.norm(result, axis=1)[:, None]


def surface_cone(vertices):
    """Directed edge planes of one ordered convex face, relative to the eye.

    This is projected boundary geometry only, not an independent physical mesh.
    A degenerate/nonconvex face is refused rather than invented or masked.
    """
    unit = _unit_rows(vertices, "surface vertices")
    if len(unit) < 3:
        raise ValueError("surface needs at least three ordered vertices")
    normals = _unit_rows(np.cross(unit, np.roll(unit, -1, axis=0)), "surface edges")
    signs = normals @ unit.sum(axis=0)
    if np.all(signs < 0):
        normals = -normals
    elif not np.all(signs > 0):
        raise ValueError("surface is degenerate or not ordered convex")
    # Centroid-sided winding alone also admits some concave faces. Every
    # nonincident vertex must lie inside every directed edge hemisphere.
    # Skip its two endpoints: their mathematical dot is zero and float64
    # cross/dot cancellation need not reproduce that zero exactly.
    for i, normal in enumerate(normals):
        side = unit @ normal
        side[i] = side[(i + 1) % len(unit)] = 0.
        if np.any(side < 0):
            raise ValueError("surface is not ordered convex")
    return normals


def _wrap(h):
    return (h + math.pi) % (2 * math.pi) - math.pi


def _dot_extrema(n, apertures):
    """Extrema of n dot d over a rectangular (h,sin(v)) aperture."""
    a, b, lo, hi = apertures.T
    nx, ny, nz = n
    radius, phi = math.hypot(nx, ny), math.atan2(ny, nx)
    first, last = nx * np.cos(a) + ny * np.sin(a), nx * np.cos(b) + ny * np.sin(b)
    amin, amax = np.minimum(first, last), np.maximum(first, last)
    amax = np.where((a <= phi) & (phi <= b), radius, amax)
    opposite = _wrap(phi + math.pi)
    amin = np.where((a <= opposite) & (opposite <= b), -radius, amin)
    c_lo, c_hi = np.sqrt(1 - lo * lo), np.sqrt(1 - hi * hi)
    minimum = np.minimum(amin * c_lo + nz * lo, amin * c_hi + nz * hi)
    maximum = np.maximum(amax * c_lo + nz * lo, amax * c_hi + nz * hi)
    norm_min, norm_max = np.hypot(amin, nz), np.hypot(amax, nz)
    at_min = np.divide(-nz, norm_min, out=np.zeros_like(norm_min), where=norm_min != 0)
    at_max = np.divide(nz, norm_max, out=np.zeros_like(norm_max), where=norm_max != 0)
    minimum = np.where((amin < 0) & (lo <= at_min) & (at_min <= hi), -norm_min, minimum)
    maximum = np.where((amax > 0) & (lo <= at_max) & (at_max <= hi), norm_max, maximum)
    return minimum, maximum


def _boundary_integral(n, a, b):
    """Integral of the great-circle edge's mu(h); stable angle difference."""
    nx, ny, nz = n
    radius, phi = math.hypot(nx, ny), math.atan2(ny, nx)
    norm = math.hypot(radius, nz)
    sa, sb = radius * np.sin(a - phi) / norm, radius * np.sin(b - phi) / norm
    ca = np.hypot(nz, radius * np.cos(a - phi)) / norm
    cb = np.hypot(nz, radius * np.cos(b - phi)) / norm
    return -math.copysign(1., nz) * np.arctan2(sb * ca - sa * cb, cb * ca + sb * sa)


def aperture_solid_angles(normals, apertures, *, max_cells):
    """Integrate intersection of n dot d >= 0 with each receptor aperture.

    Apertures are float64 rows (h_lo,h_hi,mu_lo,mu_hi), radians and mu=sin(v).
    Forward horizontal hemisphere only, with vertical endpoints strictly inside
    the poles. max_cells bounds temporary event-matrix cells, not numerical
    accuracy or cognitive capacity. Errors/refusals cannot change physical state.
    Float64 evaluation is not formal exact-real interval arithmetic.
    """
    if type(max_cells) is not int or max_cells <= 0:
        raise ValueError("positive temporary event-cell budget required")
    if not isinstance(normals, np.ndarray) or normals.ndim != 2:
        raise ValueError("packed surface normals required")
    k = len(normals)
    # Pair intersections, vertical-plane events, two aperture boundaries,
    # and two roots for each crossing with each constant-mu aperture edge.
    event_count = k * (k - 1) + 6 * k + 2
    if event_count > max_cells:
        raise ValueError("surface events exceed temporary cell budget")
    planes = _unit_rows(normals, "surface normals")
    if (not isinstance(apertures, np.ndarray) or apertures.dtype != np.dtype(np.float64)
            or apertures.ndim != 2 or apertures.shape[1] != 4
            or not np.isfinite(apertures).all()):
        raise ValueError("finite packed float64 receptor apertures required")
    a, b, lo, hi = apertures.T
    if (np.any(a < -math.pi / 2) or np.any(b > math.pi / 2)
            or np.any(a >= b) or np.any(lo <= -1) or np.any(hi >= 1)
            or np.any(lo >= hi)):
        raise ValueError("invalid forward receptor aperture")
    total = (b - a) * (hi - lo)
    inside, outside = np.ones(len(a), dtype=bool), np.zeros(len(a), dtype=bool)
    for n in planes:
        lower, upper = _dot_extrema(n, apertures)
        inside &= lower >= 0
        outside |= upper <= 0
    result = np.where(inside & ~outside, total, 0.)
    active = np.flatnonzero(~inside & ~outside)
    if not len(active):
        return result

    fixed = []
    for i, n in enumerate(planes):
        phi = math.atan2(n[1], n[0])
        fixed.extend((_wrap(phi - math.pi / 2), _wrap(phi + math.pi / 2)))
        for other in planes[i + 1:]:
            p = np.cross(n, other)
            h = math.atan2(p[1], p[0])
            fixed.extend((h, _wrap(h + math.pi)))
    batch = max_cells // event_count
    for begin in range(0, len(active), batch):
        ids = active[begin:begin + batch]
        aa, bb, ll, hh = apertures[ids].T
        events = [aa, bb]
        events.extend(np.clip(h, aa, bb) for h in fixed)
        for n in planes:
            radius, phi = math.hypot(n[0], n[1]), math.atan2(n[1], n[0])
            for mu in (ll, hh):
                if radius == 0:
                    events.extend((aa, aa))
                    continue
                ratio = -n[2] * mu / (radius * np.sqrt(1 - mu * mu))
                exists = np.abs(ratio) <= 1
                delta = np.arccos(np.clip(ratio, -1, 1))
                for sign in (-1, 1):
                    events.append(np.where(exists, np.clip(_wrap(phi + sign * delta), aa, bb), aa))
        cuts = np.sort(np.stack(events, axis=1), axis=1)
        left, right = cuts[:, :-1], cuts[:, 1:]
        mid = (left + right) / 2
        cosine, sine = np.cos(mid), np.sin(mid)
        lower = np.broadcast_to(ll[:, None], mid.shape).copy()
        upper = np.broadcast_to(hh[:, None], mid.shape).copy()
        lower_id, upper_id = np.full(mid.shape, -1), np.full(mid.shape, -1)
        valid = right > left
        for i, n in enumerate(planes):
            horizontal = n[0] * cosine + n[1] * sine
            if n[2] == 0:
                valid &= horizontal >= 0
                continue
            boundary = -math.copysign(1., n[2]) * horizontal / np.hypot(horizontal, n[2])
            if n[2] > 0:
                update = boundary > lower
                lower, lower_id = np.where(update, boundary, lower), np.where(update, i, lower_id)
            else:
                update = boundary < upper
                upper, upper_id = np.where(update, boundary, upper), np.where(update, i, upper_id)
        valid &= upper > lower
        integral_lower = ll[:, None] * (right - left)
        integral_upper = hh[:, None] * (right - left)
        for i, n in enumerate(planes):
            if n[2] == 0:
                continue
            for indices, integral in ((lower_id, integral_lower), (upper_id, integral_upper)):
                selected = valid & (indices == i)
                if selected.any():
                    integral[selected] = _boundary_integral(n, left[selected], right[selected])
        integrated = np.sum(np.where(valid, integral_upper - integral_lower, 0.), axis=1)
        # Roundoff projection only; the exact geometric result lies in [0,Omega].
        # No salience threshold or minimum visible feature size is introduced.
        result[ids] = np.clip(integrated, 0., total[ids])
    return result
