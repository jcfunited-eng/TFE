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


def _dot_extrema(planes, apertures, parameters, geometry):
    """The same dot extrema for a bounded plane-by-aperture matrix."""
    a, b, lo, hi = apertures.T
    nx, ny, nz = (p[:, None] for p in planes.T)
    radius, phi, opposite = (p[:, None] for p in parameters)
    ca, sa, cb, sb, c_lo, c_hi = geometry
    first = nx * ca + ny * sa
    last = nx * cb + ny * sb
    amin, amax = np.minimum(first, last), np.maximum(first, last)
    amax = np.where((a <= phi) & (phi <= b), radius, amax)
    amin = np.where((a <= opposite) & (opposite <= b), -radius, amin)
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


def _prepare_planes(normals, max_cells):
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
    return planes


def _validate_apertures(apertures):
    if (not isinstance(apertures, np.ndarray) or apertures.dtype != np.dtype(np.float64)
            or apertures.ndim != 2 or apertures.shape[1] != 4
            or not np.isfinite(apertures).all()):
        raise ValueError("finite packed float64 receptor apertures required")
    a, b, lo, hi = apertures.T
    if (np.any(a < -math.pi / 2) or np.any(b > math.pi / 2)
            or np.any(a >= b) or np.any(lo <= -1) or np.any(hi >= 1)
            or np.any(lo >= hi)):
        raise ValueError("invalid forward receptor aperture")


def _plane_parameters(planes):
    # Scalar constants preserve the predecessor's math.hypot/atan2 rounding.
    radius = np.array([math.hypot(n[0], n[1]) for n in planes])
    phi = np.array([math.atan2(n[1], n[0]) for n in planes])
    opposite = np.array([_wrap(float(p) + math.pi) for p in phi])
    return radius, phi, opposite


def _aperture_geometry(apertures):
    a, b, lo, hi = apertures.T
    return (np.cos(a), np.sin(a), np.cos(b), np.sin(b),
            np.sqrt(1 - lo * lo), np.sqrt(1 - hi * hi))


def _classify_apertures(planes, apertures, parameters, geometry, max_cells):
    k, a = len(planes), apertures[:, 0]
    inside, outside = np.ones(len(a), dtype=bool), np.zeros(len(a), dtype=bool)
    remaining = np.arange(len(a))
    # One domain aperture: all planes in one array. Receptor arrays: stop
    # visiting a site after a boundary excludes it. Both use the same law.
    plane_batch = k if len(a) == 1 else 1
    for first in range(0, k, plane_batch):
        last = min(first + plane_batch, k)
        sample_batch = max_cells // (last - first)
        for begin in range(0, len(remaining), sample_batch):
            ids = remaining[begin:begin + sample_batch]
            lower, upper = _dot_extrema(
                planes[first:last], apertures[ids],
                tuple(p[first:last] for p in parameters),
                tuple(g[ids] for g in geometry))
            inside[ids] &= np.all(lower >= 0, axis=0)
            outside[ids] |= np.any(upper <= 0, axis=0)
        remaining = remaining[~outside[remaining]]
        if not len(remaining):
            break
    return inside, outside


def _integrate_apertures(planes, apertures, parameters, inside, outside, max_cells):
    a, b, lo, hi = apertures.T
    total = (b - a) * (hi - lo)
    radius, phi, opposite = parameters
    k = len(planes)
    event_count = k * (k - 1) + 6 * k + 2
    result = np.where(inside & ~outside, total, 0.)
    active = np.flatnonzero(~inside & ~outside)
    if not len(active):
        return result

    fixed = []
    for i, n in enumerate(planes):
        p = float(phi[i])
        fixed.extend((_wrap(p - math.pi / 2), _wrap(p + math.pi / 2)))
        nx, ny, nz = map(float, n)
        for other in planes[i + 1:]:
            # Only the intersection longitude is needed.
            ox, oy, oz = map(float, other)
            px, py = ny * oz - nz * oy, nz * ox - nx * oz
            h = math.atan2(py, px)
            fixed.extend((h, _wrap(h + math.pi)))
    fixed = np.asarray(fixed)
    positive, negative = np.flatnonzero(planes[:, 2] > 0), np.flatnonzero(planes[:, 2] < 0)
    vertical = planes[:, 2] == 0
    batch = max_cells // event_count
    for begin in range(0, len(active), batch):
        ids = active[begin:begin + batch]
        aa, bb, ll, hh = apertures[ids].T
        cuts = np.empty((len(ids), event_count))
        cuts[:, 0], cuts[:, 1] = aa, bb
        end = 2 + len(fixed)
        cuts[:, 2:end] = np.clip(fixed[None, :], aa[:, None], bb[:, None])
        # Same n / lower-upper latitude / negative-positive root order,
        # emitted directly into the event matrix instead of scalar arrays.
        mu = np.stack((ll, hh), axis=1)[:, None, :]
        denominator = radius[None, :, None] * np.sqrt(1 - mu * mu)
        ratio = np.divide(-planes[None, :, 2, None] * mu, denominator,
                          out=np.zeros((len(ids), k, 2)),
                          where=radius[None, :, None] != 0)
        exists = (radius[None, :, None] != 0) & (np.abs(ratio) <= 1)
        delta = np.arccos(np.clip(ratio, -1, 1))
        roots = cuts[:, end:].reshape(len(ids), k, 2, 2)
        for root_index, sign in enumerate((-1, 1)):
            roots[:, :, :, root_index] = np.where(
                exists, np.clip(_wrap(phi[None, :, None] + sign * delta),
                                aa[:, None, None], bb[:, None, None]), aa[:, None, None])
        cuts.sort(axis=1)
        left, right = cuts[:, :-1], cuts[:, 1:]
        mid = (left + right) / 2
        lower_id, upper_id = np.full(mid.shape, -1), np.full(mid.shape, -1)
        valid = right > left
        # Duplicate/clipped events have zero width and no integral. Evaluate
        # only actual intervals, with at most max_cells plane-interval pairs.
        intervals = np.flatnonzero(valid)
        slab = max_cells // k
        bottom = np.broadcast_to(ll[:, None], mid.shape).ravel()
        top = np.broadcast_to(hh[:, None], mid.shape).ravel()
        for offset in range(0, len(intervals), slab):
            selected = intervals[offset:offset + slab]
            h = mid.ravel()[selected]
            horizontal = (planes[:, 0, None] * np.cos(h)
                          + planes[:, 1, None] * np.sin(h))
            allowed = np.all(horizontal[vertical] >= 0, axis=0)
            lower, upper = bottom[selected].copy(), top[selected].copy()
            columns = np.arange(len(selected))
            if len(positive):
                boundaries = (-horizontal[positive]
                              / np.hypot(horizontal[positive], planes[positive, 2, None]))
                owner = np.argmax(boundaries, axis=0)
                value = boundaries[owner, columns]
                update = value > lower
                lower[update] = value[update]
                lower_id.ravel()[selected[update]] = positive[owner[update]]
            if len(negative):
                boundaries = (horizontal[negative]
                              / np.hypot(horizontal[negative], planes[negative, 2, None]))
                owner = np.argmin(boundaries, axis=0)
                value = boundaries[owner, columns]
                update = value < upper
                upper[update] = value[update]
                upper_id.ravel()[selected[update]] = negative[owner[update]]
            valid.ravel()[selected] = allowed & (upper > lower)
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


def aperture_solid_angles(normals, apertures, *, max_cells):
    """Convex halfspace areas; read-only numerical body optics, not cognition.

    max_cells bounds event/matrix scratch. Apertures are float64 rows
    (h_lo,h_hi,mu_lo,mu_hi), radians and mu=sin(v), in the forward hemisphere.
    The supplied planes must describe one convex region, not overlapping faces.
    """
    planes = _prepare_planes(normals, max_cells)
    _validate_apertures(apertures)
    parameters = _plane_parameters(planes)
    inside, outside = _classify_apertures(
        planes, apertures, parameters, _aperture_geometry(apertures), max_cells)
    return _integrate_apertures(planes, apertures, parameters, inside, outside, max_cells)


def disjoint_surface_radiance(regions, values, apertures, *, max_cells, max_halfspaces):
    """Six-band aperture means of caller-proved disjoint visible regions.

    Shared plane classification exists only in this call. Exact normalized
    plane bytes (including signed zero) identify duplicated geometry work, not
    an object, perceptual identity, memory or learned association. Original
    region row order and multiplicity remain intact in the area integrator.

    Input/index residency is O(max_halfspaces), output is 6*N float64 values.
    Packed classification tables plus two masks occupy <=8*max_cells bytes;
    every numeric/event matrix is also max_cells-bounded. No persistent cache.
    """
    if (type(max_cells) is not int or max_cells <= 0
            or type(max_halfspaces) is not int or max_halfspaces <= 0
            or not isinstance(regions, tuple)):
        raise ValueError("bounded region tuple required")
    _validate_apertures(apertures)
    if (not isinstance(values, np.ndarray) or values.dtype != np.dtype(np.float64)
            or values.shape != (len(regions), 6) or not np.isfinite(values).all()
            or np.any(values < 0)):
        raise ValueError("finite nonnegative six-band radiances required")
    total = ((apertures[:, 1] - apertures[:, 0])
             * (apertures[:, 3] - apertures[:, 2]))
    if np.any(total <= 0):
        raise ValueError("aperture area underflows numerical domain")
    addresses, unique, index, rows = [], [], {}, 0
    for normals in regions:
        if not isinstance(normals, np.ndarray) or normals.ndim != 2:
            raise ValueError("packed region planes required")
        rows += len(normals)
        if rows > max_halfspaces:
            raise ValueError("region halfspace residency exceeded")
        prepared = _prepare_planes(normals, max_cells)
        ids = []
        for n in prepared:
            key = n.tobytes()
            if key not in index:
                index[key] = len(unique)
                unique.append(n.copy())
            ids.append(index[key])
        addresses.append(np.array(ids, dtype=np.intp))
    result = np.zeros((len(apertures), 6))
    if not unique:
        return result
    planes = np.array(unique)
    del unique, index
    parameters = _plane_parameters(planes)
    width_budget = (8 * max_cells) // (2 * (len(planes) + 1))
    if not width_budget:
        raise ValueError("shared classification residency exceeded")
    batch = min(max_cells, 8 * width_budget)
    maximum_width = (min(batch, len(apertures)) + 7) // 8
    packed_inside = np.empty((len(planes), maximum_width), dtype=np.uint8)
    packed_outside = np.empty_like(packed_inside)
    all_inside_mask = np.empty(maximum_width, dtype=np.uint8)
    all_outside_mask = np.empty(maximum_width, dtype=np.uint8)
    for begin in range(0, len(apertures), batch):
        end = min(begin + batch, len(apertures))
        block = apertures[begin:end]
        geometry = _aperture_geometry(block)
        width = (len(block) + 7) // 8
        inside_bits, outside_bits = packed_inside[:, :width], packed_outside[:, :width]
        inside_mask, outside_mask = all_inside_mask[:width], all_outside_mask[:width]
        for i in range(len(planes)):
            lower, upper = _dot_extrema(
                planes[i:i + 1], block, tuple(p[i:i + 1] for p in parameters), geometry)
            inside_bits[i] = np.packbits(lower[0] >= 0)
            outside_bits[i] = np.packbits(upper[0] <= 0)
        for region_index, ids in enumerate(addresses):
            inside_mask.fill(255)
            outside_mask.fill(0)
            for i in ids:
                np.bitwise_and(inside_mask, inside_bits[i], out=inside_mask)
                np.bitwise_or(outside_mask, outside_bits[i], out=outside_mask)
            inside = np.unpackbits(inside_mask, count=len(block)).astype(bool)
            outside = np.unpackbits(outside_mask, count=len(block)).astype(bool)
            area = _integrate_apertures(
                planes[ids], block, tuple(p[ids] for p in parameters),
                inside, outside, max_cells)
            result[begin:end] += area[:, None] * values[region_index]
        result[begin:end] /= total[begin:end, None]
    if not np.isfinite(result).all():
        raise ValueError("radiance exceeds numerical domain")
    return result
