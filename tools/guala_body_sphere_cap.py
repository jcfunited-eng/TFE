"""Offline small-circle aperture integral; no body/world or cognition authority.

Float64 analytic event settlement, not directed-rounding interval arithmetic.
Uses the physical sphere silhouette and original planar halfspaces. A midpoint
only selects boundary ownership between exhaustive intersection events.
"""
from __future__ import annotations

import math
import numpy as np

from dsf_ai_service.substrate.functional_body_optics import (
    _aperture_geometry, _boundary_integral, _dot_extrema, _plane_parameters,
    _unit_rows, _validate_apertures, _wrap, aperture_solid_angles,
)


def _difference(x0, y0, x1, y1):
    return np.arctan2(y1*x0-x1*y0, x0*x1+y0*y1)


def sphere_parameters(centre, radius):
    """Refuse arithmetic domains that cannot distinguish the sphere tangent."""
    with np.errstate(over='ignore', invalid='ignore'):
        squared = float(centre @ centre)
        radius_squared = float(radius*radius)
    a = squared-radius_squared
    if (not all(map(math.isfinite, (squared, radius_squared, a)))
            or not 0 < radius_squared or not 0 < a < squared or radius <= 0):
        raise ValueError('finite representable exterior sphere required')
    distance = math.sqrt(squared)
    s = radius/distance
    if not 0 < s < 1:
        raise ValueError('sphere angular radius not representable')
    k = math.sqrt((1-s)*(1+s))
    if not 0 < k < 1:
        raise ValueError('sphere tangent not representable')
    return centre/distance, s, k, a


def _cap_integrals(n, s, k, left, right):
    radial, phi = math.hypot(n[0], n[1]), math.atan2(n[1], n[0])
    u0, u1 = left-phi, right-phi
    y0, y1 = radial*np.sin(u0), radial*np.sin(u1)
    # Event endpoints may round just outside a tangent. Projection to that
    # exact known endpoint affects the primitive only, never hit admission.
    y0, y1 = np.clip(y0, -s, s), np.clip(y1, -s, s)
    q0 = np.sqrt((s-np.abs(y0))*(s+np.abs(y0)))
    q1 = np.sqrt((s-np.abs(y1))*(s+np.abs(y1)))
    eta = s*s/(1+k)
    j0 = np.arctan2(eta*y0*q0, q0*q0+k*y0*y0)+eta*np.arctan2(k*y0, q0)
    j1 = np.arctan2(eta*y1*q1, q1*q1+k*y1*y1)+eta*np.arctan2(k*y1, q1)
    alpha = _difference(np.cos(u0), n[2]*np.sin(u0),
                        np.cos(u1), n[2]*np.sin(u1))
    return k*alpha, j1-j0


def cap_solid_angles(centre, radius, apertures, normals, *, max_cells=32768):
    """Integral of a sphere cap intersected with original planar halfspaces.

    Domain: exterior sphere, forward apertures, horizontal cap projection A>0
    throughout every partially intersected aperture. Unsupported domains refuse.
    Returns area midpoint and geometric uncertainty radius. An event slab with
    no representable interior contributes [0, its aperture area], never a
    guessed boundary owner. Ordinary floating-point roundoff is not enclosed.
    No quadrature pixels, polygon reconstruction, visible-surface assumption,
    persistent cache, or material/recognition labels.
    """
    _validate_apertures(apertures)
    centre = np.asarray(centre, dtype=np.float64)
    if centre.shape != (3,) or not np.isfinite(centre).all():
        raise ValueError('finite sphere centre required')
    n, s, k, _ = sphere_parameters(centre, radius)
    if type(max_cells) is not int or not 0 < max_cells <= 32768:
        raise ValueError('bounded event cells required')
    if (not isinstance(normals, np.ndarray) or normals.dtype != np.dtype(np.float64)
            or normals.ndim != 2 or normals.shape[1] != 3):
        raise ValueError('packed original halfspaces required')
    count = len(normals)
    event_bound = count*(count-1)+8*count+8
    if event_bound > max_cells:
        raise ValueError('cap boundary events exceed budget')
    planes = _unit_rows(normals, 'halfspaces') if count else normals
    radial, phi = math.hypot(n[0], n[1]), math.atan2(n[1], n[0])
    geometry = _aperture_geometry(apertures)
    low, high = _dot_extrema(n[None, :], apertures, _plane_parameters(n[None, :]), geometry)
    full, outside = low[0] >= k, high[0] < k
    areas = np.zeros(len(apertures))
    uncertainty = np.zeros(len(apertures))
    if full.any():
        rows = apertures[full]
        areas[full] = (aperture_solid_angles(planes, rows, max_cells=max_cells)
                       if count else (rows[:,1]-rows[:,0])*(rows[:,3]-rows[:,2]))
    active = np.flatnonzero(~full & ~outside)
    if not len(active):
        return areas, uncertainty
    horizontal = np.array(((n[0], n[1], 0.),))
    lower, _ = _dot_extrema(horizontal, apertures[active],
                            _plane_parameters(horizontal),
                            tuple(a[active] for a in geometry))
    if np.any(lower <= 0):
        raise ValueError('cap horizontal projection changes sign')
    # Events independent of a receptor's latitude boundaries, prepared once.
    fixed = []
    for i, plane in enumerate(planes):
        angle = math.atan2(plane[1], plane[0])
        fixed.extend((_wrap(angle-math.pi/2), _wrap(angle+math.pi/2)))
        for other in planes[i+1:]:
            point = np.cross(plane, other)
            if point[0] == 0 and point[1] == 0:
                # Parallel planes or a polar intersection have no longitude
                # event in the admitted strictly non-polar aperture.
                continue
            h = math.atan2(point[1], point[0])
            fixed.extend((h, _wrap(h+math.pi)))
        if plane[2] == 0:
            # Its cap intersections have the SAME longitude as the vertical
            # plane events above. Recomputing that longitude from a 3-D point
            # introduces artificial one-ulp event slivers.
            continue
        cross = np.cross(n, plane)
        squared = float(cross @ cross)
        if squared >= k*k and squared > 0:
            base = k*(n-float(n @ plane)*plane)/squared
            offset = math.sqrt(max(0., 1-k*k/squared))*cross/math.sqrt(squared)
            for point in (base-offset, base+offset):
                fixed.append(math.atan2(point[1], point[0]))
    if s < radial:
        half = math.asin(s/radial)
        fixed.extend((_wrap(phi-half), _wrap(phi+half)))
        support = phi-half, phi+half
    else:
        support = -math.pi/2, math.pi/2
    for index in active:
        a, b, lo, hi = apertures[index]
        # The cap is identically absent outside these tangent longitudes.
        # Exclude irrelevant planar events there, not tiny physical features.
        a, b = max(a, support[0]), min(b, support[1])
        if a >= b:
            continue
        events = [a, b, *[h for h in fixed if a < h < b]]
        for level in (lo, hi):
            cv = math.sqrt((1-level)*(1+level))
            for plane in planes:
                r = math.hypot(plane[0], plane[1])
                if r:
                    ratio = -plane[2]*level/(r*cv)
                    if abs(ratio) <= 1:
                        delta = math.acos(ratio)
                        p = math.atan2(plane[1], plane[0])
                        events.extend(_wrap(p+sign*delta) for sign in (-1,1)
                                      if a < _wrap(p+sign*delta) < b)
            ratio = (k-n[2]*level)/(radial*cv)
            if abs(ratio) <= 1:
                delta = math.acos(ratio)
                events.extend(_wrap(phi+sign*delta) for sign in (-1,1)
                              if a < _wrap(phi+sign*delta) < b)
        if len(events) > max_cells:
            raise ValueError('cap events exceed budget')
        cuts = np.unique(events)
        left, right = cuts[:-1], cuts[1:]
        mid = (left+right)/2
        unresolved = (mid == left) | (mid == right)
        unknown = 0.
        if unresolved.any():
            bounds = np.nextafter((right[unresolved]-left[unresolved])*(hi-lo), np.inf)
            unknown = math.nextafter(math.fsum(map(float, bounds)), math.inf)
            uncertainty[index] = unknown/2
            left, right, mid = left[~unresolved], right[~unresolved], mid[~unresolved]
        h = radial*np.cos(mid-phi)
        d = h*h+n[2]*n[2]
        valid = d >= k*k
        root = np.sqrt(np.maximum(d-k*k, 0.))
        cap_lower = np.full(len(mid), -1.) if n[2] <= -k else (k*n[2]-h*root)/d
        cap_upper = np.full(len(mid), 1.) if n[2] >= k else (k*n[2]+h*root)/d
        bottom, top = np.maximum(lo, cap_lower), np.minimum(hi, cap_upper)
        lower_id = np.where(cap_lower > lo, -2, -1)
        upper_id = np.where(cap_upper < hi, -2, -1)
        for i, plane in enumerate(planes):
            projection = plane[0]*np.cos(mid)+plane[1]*np.sin(mid)
            if plane[2] == 0:
                valid &= projection >= 0
            else:
                boundary = -math.copysign(1., plane[2])*projection/np.hypot(projection, plane[2])
                if plane[2] > 0:
                    update = boundary > bottom
                    bottom, lower_id = np.maximum(bottom, boundary), np.where(update, i, lower_id)
                else:
                    update = boundary < top
                    top, upper_id = np.minimum(top, boundary), np.where(update, i, upper_id)
        valid &= top > bottom
        left, right, lower_id, upper_id = left[valid], right[valid], lower_id[valid], upper_id[valid]
        common, spread = _cap_integrals(n, s, k, left, right)
        bottom_integral, top_integral = lo*(right-left), hi*(right-left)
        bottom_integral = np.where(lower_id == -2, common-spread, bottom_integral)
        top_integral = np.where(upper_id == -2, common+spread, top_integral)
        for i in np.unique(np.concatenate((lower_id, upper_id))):
            if i >= 0:
                integral = _boundary_integral(planes[i], left, right)
                bottom_integral = np.where(lower_id == i, integral, bottom_integral)
                top_integral = np.where(upper_id == i, integral, top_integral)
        spans = np.where((lower_id == -2) & (upper_id == -2), 2*spread,
                         top_integral-bottom_integral)
        area = math.fsum(map(float, spans))
        if not math.isfinite(area):
            raise ValueError('cap area exceeds numerical domain')
        # Same roundoff projection as the accepted planar integral. The
        # analytical intersection area lies in [0, support aperture area].
        # No geometric feature threshold or widened comparison tolerance.
        areas[index] = np.clip(area+unknown/2, 0., (b-a)*(hi-lo))
    return areas, uncertainty
