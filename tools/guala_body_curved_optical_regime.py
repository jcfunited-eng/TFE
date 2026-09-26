#!/usr/bin/env python3
"""Offline finite-primitive cone-bound diagnostic; NOT a production renderer.

Float64 analytic enclosures are not directed-rounding interval arithmetic.
Native rays are sampled witnesses, never empty-aperture certificates. Planes,
meshes, variable lighting and material charts are outside this diagnostic.
Nothing here is imported by the organism or changes body/world state.
"""
from __future__ import annotations

import json
import math
import os
import resource
import subprocess
import time
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_native import NativeBody
from dsf_ai_service.substrate.functional_body_optics import (
    _aperture_geometry, _dot_extrema, _plane_parameters, _validate_apertures,
    disjoint_surface_radiance,
)
from dsf_ai_service.substrate.functional_body_visibility import PlanarSurface, visible_planar_regions
from tools.guala_body_optical_regime import (
    LIMITS, ORIGIN, EYE_Z, BANDS, retinal_apertures, scene,
)
from tools.guala_body_sphere_cap import cap_solid_angles, sphere_parameters


SPHERE, CAPSULE, ELLIPSOID, CYLINDER, BOX = (int(x) for x in (
    mj.mjtGeom.mjGEOM_SPHERE, mj.mjtGeom.mjGEOM_CAPSULE,
    mj.mjtGeom.mjGEOM_ELLIPSOID, mj.mjtGeom.mjGEOM_CYLINDER, mj.mjtGeom.mjGEOM_BOX))
KINDS = (SPHERE, CAPSULE, ELLIPSOID, CYLINDER, BOX)


def directions(h, mu):
    cv = np.sqrt(1 - mu * mu)
    return np.stack((cv * np.cos(h), cv * np.sin(h), mu), axis=-1)


def quadratic(a, b, c):
    """Real interval where a*t^2+2*b*t+c<=0, for squared-norm a>=0."""
    a, b, c = np.broadcast_arrays(a, b, c)
    det = b*b - a*c
    root = np.sqrt(np.maximum(det, 0))
    q = -b - np.copysign(root, b)
    x = np.divide(q, a, out=np.zeros_like(q), where=a != 0)
    y = np.divide(c, q, out=x.copy(), where=q != 0)
    lo, hi = np.minimum(x, y), np.maximum(x, y)
    constant_inside = (a == 0) & (c <= 0)
    missing = (det < 0) | ((a == 0) & (c > 0))
    return (np.where(missing, np.inf, np.where(constant_inside, -np.inf, lo)),
            np.where(missing, -np.inf, np.where(constant_inside, np.inf, hi)))


def slab(origin, velocity, half):
    origin, velocity, half = np.broadcast_arrays(origin, velocity, half)
    a = np.divide(-half-origin, velocity, out=np.zeros_like(velocity), where=velocity != 0)
    b = np.divide(half-origin, velocity, out=np.zeros_like(velocity), where=velocity != 0)
    parallel = velocity == 0
    outside = parallel & (np.abs(origin) > half)
    return (np.where(outside, np.inf, np.where(parallel, -np.inf, np.minimum(a, b))),
            np.where(outside, -np.inf, np.where(parallel, np.inf, np.maximum(a, b))))


def sphere_interval(origin, velocity, radius):
    return quadratic(np.sum(velocity*velocity, axis=-1),
                     np.sum(origin*velocity, axis=-1), np.sum(origin*origin, axis=-1)-radius*radius)


def interval(kind, sizes, origin, velocity):
    """Line interval through the original analytic convex solid, in local axes."""
    if kind == SPHERE:
        return sphere_interval(origin, velocity, sizes[..., 0])
    if kind == ELLIPSOID:
        return sphere_interval(origin / sizes, velocity / sizes, 1.)
    if kind == BOX:
        lo, hi = slab(origin, velocity, sizes)
        return np.max(lo, axis=-1), np.min(hi, axis=-1)
    if kind in (CAPSULE, CYLINDER):
        lo, hi = sphere_interval(origin[..., :2], velocity[..., :2], sizes[..., 0])
        zlo, zhi = slab(origin[..., 2], velocity[..., 2], sizes[..., 1])
        lo, hi = np.maximum(lo, zlo), np.minimum(hi, zhi)
        valid = lo <= hi
        lo, hi = np.where(valid, lo, np.inf), np.where(valid, hi, -np.inf)
        if kind == CAPSULE:
            for sign in (-1, 1):
                shifted = np.broadcast_to(origin, velocity.shape).copy()
                shifted[..., 2] -= sign*sizes[..., 1]
                a, b = sphere_interval(shifted, velocity, sizes[..., 0])
                lo, hi = np.minimum(lo, a), np.maximum(hi, b)
        return lo, hi
    raise ValueError('finite primitive required; no silent geometry exclusion')


def radii(kind, size):
    if kind == SPHERE:
        return np.full(3, size[0]), size[0]
    if kind == CAPSULE:
        return np.array((size[0], size[0], size[0]+size[1])), size[0]+size[1]
    if kind == CYLINDER:
        return np.array((size[0], size[0], size[1])), math.hypot(size[0], size[1])
    if kind == ELLIPSOID:
        return size, max(size)
    if kind == BOX:
        return size, np.linalg.norm(size)
    raise ValueError('finite primitive required')


def validate_geometry(geometry):
    if not isinstance(geometry.kinds, np.ndarray) or geometry.kinds.ndim != 1:
        raise ValueError('complete primitive roster required')
    count = len(geometry.kinds)
    for values, shape in ((geometry.sizes_m, (count, 3)),
                          (geometry.positions_eye_m, (count, 3)),
                          (geometry.rotations_eye, (count, 3, 3))):
        if not isinstance(values, np.ndarray) or values.shape != shape or not np.isfinite(values).all():
            raise ValueError('complete finite geometry arrays required')
    if not count or count > 256:
        raise ValueError('diagnostic primitive budget exceeded')
    for kind, size, centre, rotation in zip(geometry.kinds, geometry.sizes_m,
                                          geometry.positions_eye_m, geometry.rotations_eye):
        if kind not in KINDS:
            raise ValueError('finite primitives only; a plane is not silently omitted')
        if not np.isfinite(size).all() or not np.isfinite(centre).all() or not np.isfinite(rotation).all():
            raise ValueError('nonfinite geometry')
        required = size[:1] if kind == SPHERE else size[:2] if kind in (CAPSULE, CYLINDER) else size
        if np.any(required <= 0):
            raise ValueError('positive primitive dimensions required')
        if kind == SPHERE:
            sphere_parameters(centre, float(size[0]))
        local_origin = -centre @ rotation
        lo, hi = interval(kind, size[None, :], local_origin[None, :], np.array(((1., 0., 0.),)))
        if lo[0] <= 0 <= hi[0]:
            raise ValueError('optical origin inside/on opaque solid; exterior-eye regime required')


def patch_geometry(patches):
    h = (patches[:, 0]+patches[:, 1])/2
    mu = (patches[:, 2]+patches[:, 3])/2
    centre = directions(h, mu)
    # Rotating all longitudes by -h leaves chord length unchanged and avoids
    # 1-cos cancellation. The farthest direction is one of these two corners.
    base = directions(np.zeros_like(h), mu)
    half = (patches[:, 1]-patches[:, 0])/2
    epsilon = np.maximum(np.linalg.norm(directions(half, patches[:, 2])-base, axis=1),
                         np.linalg.norm(directions(half, patches[:, 3])-base, axis=1))
    return centre, epsilon, _aperture_geometry(patches)


def box_faces(size, centre, rotation):
    """Original physical unit charts, not reconstructed clipping vertices."""
    eye = -centre @ rotation
    quad = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))
    faces = []
    for axis in range(3):
        others = [a for a in range(3) if a != axis]
        for sign in (-1, 1):
            if sign*eye[axis] <= size[axis]:
                continue
            axes = np.array([rotation[:, a]*(2*size[a]) for a in others])
            origin = centre + rotation[:, axis]*sign*size[axis] - axes.sum(axis=0)/2
            faces.append(PlanarSurface.from_chart(origin, axes, quad, max_corners=4))
    return tuple(faces)


def box_entry_bounds(faces, patches, angular):
    lower = np.full(len(patches), np.inf)
    upper = lower.copy()
    for face in faces:
        lo, hi = _dot_extrema(face.halfspaces, patches,
                              _plane_parameters(face.halfspaces), angular)
        possible = np.all(hi >= 0, axis=0)
        all_inside = np.all(lo >= 0, axis=0)
        inverse = face.inverse[0:1]
        near, far = _dot_extrema(inverse, patches, _plane_parameters(inverse), angular)
        first = np.divide(1., far[0], out=np.full(len(patches), np.inf),
                          where=possible & (far[0] > 0))
        last = np.divide(1., near[0], out=np.full(len(patches), np.inf),
                         where=all_inside & (near[0] > 0))
        lower = np.minimum(lower, first)
        upper = np.minimum(upper, last)
    return lower, upper


def prepare_scene(geometry, apertures, radiance):
    domain = np.array(((apertures[:,0].min(), apertures[:,1].max(),
                        apertures[:,2].min(), apertures[:,3].max()),))
    domain_geometry = patch_geometry(domain)
    boxes, curved, surfaces, native_indices = {}, [], [], []
    input_halfspaces = 0
    for i, (kind, size, centre, rotation) in enumerate(zip(
            geometry.kinds, geometry.sizes_m, geometry.positions_eye_m, geometry.rotations_eye)):
        if kind == BOX:
            faces = box_faces(size, centre, rotation)
            boxes[i] = faces
            for face in faces:
                input_halfspaces += len(face.halfspaces)
                if input_halfspaces > 32768:
                    raise ValueError('original input halfspace residency exceeded')
                _, high = _dot_extrema(face.halfspaces, domain,
                                       _plane_parameters(face.halfspaces), domain_geometry[2])
                if np.any(high < 0):
                    # Every admitted ray violates an original face boundary:
                    # it can neither illuminate nor occlude this domain.
                    continue
                surfaces.append(face)
                native_indices.append(i)
        else:
            lower, _ = entry_bounds(kind, size, centre, rotation, domain, domain_geometry)
            if np.isfinite(lower[0]):
                curved.append(i)
    regions = visible_planar_regions(tuple(surfaces), domain, max_halfspaces=32768,
                                     max_work=1048576, max_cells=32768)
    values = np.array([radiance[native_indices[r.surface_index]] for r in regions],
                      dtype=np.float64).reshape(-1, 6)
    return boxes, tuple(curved), tuple(r.halfspaces for r in regions), values


def entry_bounds(kind, size, centre, rotation, patches, prepared, faces=None):
    direction, epsilon, angular = prepared
    if kind == BOX:
        return box_entry_bounds(box_faces(size, centre, rotation) if faces is None else faces,
                                patches, angular)
    if kind == SPHERE:
        # For an exterior eye, t(q)=a/(q+sqrt(q*q-a)), q=c dot d,
        # a=|c|^2-r^2. Forward entry exists iff q>=sqrt(a), and t
        # decreases with q. Aperture-wide extrema avoid radius inflation.
        a = float(centre @ centre - size[0]*size[0])
        if a <= 0:
            raise ValueError('exterior-eye sphere required')
        vectors = centre[None, :]
        low, high = _dot_extrema(vectors, patches, _plane_parameters(vectors), angular)
        def entry(q):
            result = np.full(len(patches), np.inf)
            hit = q >= math.sqrt(a)
            result[hit] = a/(q[hit] + np.sqrt(np.maximum(q[hit]*q[hit]-a, 0.)))
            return result
        return entry(high[0]), entry(low[0])
    origin = -centre @ rotation
    velocity = direction @ rotation
    half, radius = radii(kind, size)
    tmax = np.full(len(patches), np.linalg.norm(centre)+radius)
    low, high = _dot_extrema(rotation.T, patches, _plane_parameters(rotation.T), angular)
    for axis in range(3):
        positive, negative = low[axis] > 0, high[axis] < 0
        bound = np.full(len(patches), np.inf)
        np.divide(half[axis]-origin[axis], low[axis], out=bound, where=positive)
        np.divide(-half[axis]-origin[axis], high[axis], out=bound, where=negative)
        tmax = np.minimum(tmax, bound)
    delta = np.maximum(tmax, 0)*epsilon
    expanded = np.broadcast_to(size, (len(patches), 3)).copy()
    contracted = expanded.copy()
    if kind == ELLIPSOID:
        scale = delta/min(size)
        expanded *= (1+scale[:, None])
        contracted *= (1-scale[:, None])
        nonempty = scale < 1
    else:
        changed = (0,) if kind == CAPSULE else (0, 1) if kind == CYLINDER else (0, 1, 2)
        expanded[:, changed] += delta[:, None]
        contracted[:, changed] -= delta[:, None]
        nonempty = np.all(contracted[:, changed] > 0, axis=1)
    lo, hi = interval(kind, expanded, origin, velocity)
    lower = np.maximum(lo, 0)
    possible = (hi >= lower) & (lower <= tmax)
    lower = np.where(possible, lower, np.inf)
    upper = np.full(len(patches), np.inf)
    rows = np.flatnonzero(nonempty & possible)
    if len(rows):
        a, b = interval(kind, contracted[rows], origin, velocity[rows])
        entry = np.maximum(a, 0)
        upper[rows] = np.where((b >= entry) & (entry <= tmax[rows]), entry, np.inf)
    return lower, upper


def classify(geometry, patches, boxes, curved):
    """-1 background, -2 unresolved, otherwise original primitive row."""
    prepared = patch_geometry(patches)
    first = np.full(len(patches), np.inf)
    second, upper = first.copy(), first.copy()
    first_id = np.full(len(patches), -1, dtype=np.int32)
    winner = first_id.copy()
    curve_count = np.zeros(len(patches), dtype=np.int32)
    curve_id = first_id.copy()
    def record(index, rows, lo, hi):
        replace = lo < first[rows]
        second[rows] = np.where(replace, first[rows], np.minimum(second[rows], lo))
        first[rows] = np.minimum(first[rows], lo)
        first_id[rows] = np.where(replace, index, first_id[rows])
        replace_upper = hi < upper[rows]
        upper[rows] = np.minimum(upper[rows], hi)
        winner[rows] = np.where(replace_upper, index, winner[rows])
    for index in curved:
        lo, hi = entry_bounds(geometry.kinds[index], geometry.sizes_m[index],
                              geometry.positions_eye_m[index], geometry.rotations_eye[index],
                              patches, prepared)
        possible = np.isfinite(lo)
        curve_count += possible
        curve_id = np.where(possible, index, curve_id)
        record(index, slice(None), lo, hi)
    rows = np.flatnonzero(curve_count)
    box_front = np.full(len(patches), np.inf)
    if len(rows):
        reached = patches[rows]
        angular = tuple(a[rows] for a in prepared[2])
        for index, faces in boxes.items():
            lo, hi = box_entry_bounds(faces, reached, angular)
            box_front[rows] = np.minimum(box_front[rows], lo)
            record(index, rows, lo, hi)
    competitors = np.where(winner == first_id, second, first)
    resolved = upper < competitors
    settled = np.where(np.isinf(first), -1, np.where(resolved, winner, -2))
    foreground_cap = np.full(len(patches), -1, dtype=np.int32)
    for index in curved:
        if geometry.kinds[index] != SPHERE:
            continue
        centre, radius = geometry.positions_eye_m[index], geometry.sizes_m[index,0]
        last_entry = math.sqrt(float(centre @ centre-radius*radius))
        selected = np.flatnonzero((settled == -2) & (curve_count == 1)
                                 & (curve_id == index) & (box_front > last_entry))
        if len(selected):
            horizontal = np.array(((centre[0], centre[1], 0.),))
            low, _ = _dot_extrema(horizontal, patches[selected], _plane_parameters(horizontal),
                                  tuple(a[selected] for a in prepared[2]))
            foreground_cap[selected[low[0] > 0]] = index
    return settled, curve_count == 0, foreground_cap


def integrate(geometry, apertures, radiance, error, *, max_nodes=262144, max_depth=20):
    """Midpoint, total radius, work, depth, unresolved area fraction; or refusal."""
    validate_geometry(geometry)
    _validate_apertures(apertures)
    if type(max_nodes) is not int or not 0 < max_nodes <= 262144 or type(max_depth) is not int or not 0 <= max_depth <= 20:
        raise ValueError('positive integer node budget and bounded integer depth required')
    if not 0 < len(apertures) <= 19335 or error <= 0 or not math.isfinite(error):
        raise ValueError('bounded retinal/error request required')
    if radiance.shape != (len(geometry.kinds), 6) or not np.isfinite(radiance).all() or np.any(radiance < 0):
        raise ValueError('finite six-band diagnostic emitters required')
    maximum = radiance.max(axis=0)
    total = (apertures[:, 1]-apertures[:, 0])*(apertures[:, 3]-apertures[:, 2])
    if not np.isfinite(total).all() or np.any(total <= 0):
        raise ValueError('positive representable aperture areas required')
    boxes, curved, regions, values = prepare_scene(geometry, apertures, radiance)
    exact = np.zeros((len(apertures), 6))
    numerical = np.zeros_like(exact)
    uncertainty = np.zeros(len(apertures))
    nodes, owners = apertures.copy(), np.arange(len(apertures))
    visited = 0
    for depth in range(max_depth+1):
        visited += len(nodes)
        if visited > max_nodes:
            raise ValueError(f'node budget exhausted: visited={visited}, depth={depth}')
        patch_area = (nodes[:, 1]-nodes[:, 0])*(nodes[:, 3]-nodes[:, 2])
        if not np.isfinite(patch_area).all() or np.any(patch_area <= 0):
            raise ValueError('positive representable patch areas required')
        resolved, planar_only, foreground_cap = classify(geometry, nodes, boxes, curved)
        area = patch_area / total[owners]
        if planar_only.any():
            mean = disjoint_surface_radiance(regions, values, nodes[planar_only],
                                            max_cells=32768, max_halfspaces=32768)
            np.add.at(exact, owners[planar_only], area[planar_only, None]*mean)
        cap_rows = np.flatnonzero(foreground_cap >= 0)
        for sphere in np.unique(foreground_cap[cap_rows]):
            selected = cap_rows[foreground_cap[cap_rows] == sphere]
            patches = nodes[selected]
            centre, radius = geometry.positions_eye_m[sphere], geometry.sizes_m[sphere,0]
            solid = patch_area[selected]
            cap_area, cap_error = cap_solid_angles(centre, radius, patches, np.empty((0,3)))
            bound = cap_error[:,None]*radiance[sphere]
            mean = disjoint_surface_radiance(regions, values, patches,
                                            max_cells=32768, max_halfspaces=32768)
            mean += cap_area[:,None]/solid[:,None]*radiance[sphere]
            for region, value in zip(regions, values):
                overlap, overlap_error = cap_solid_angles(centre, radius, patches, region)
                mean -= overlap[:,None]/solid[:,None]*value
                bound += overlap_error[:,None]*value
            np.add.at(exact, owners[selected], area[selected,None]*mean)
            np.add.at(numerical, owners[selected], bound/total[owners[selected],None])
        if not np.isfinite(numerical).all() or np.any(numerical > error):
            raise ValueError('analytic event uncertainty exceeds optical budget')
        hit = (resolved >= 0) & ~planar_only
        np.add.at(exact, owners[hit], area[hit, None]*radiance[resolved[hit]])
        active = (resolved == -2) & ~planar_only & (foreground_cap < 0)
        unknown = np.bincount(owners[active], weights=area[active], minlength=len(apertures))
        done = np.all(numerical + unknown[:,None]*maximum/2 <= error, axis=1)
        completed = done & (unknown > 0)
        uncertainty[completed] = unknown[completed]
        keep = active & ~done[owners]
        if not keep.any():
            residual = uncertainty[:, None]*maximum/2
            return exact + residual, residual + numerical, visited, depth, uncertainty
        parent, owners = nodes[keep], owners[keep]
        if visited+4*len(parent) > max_nodes:
            raise ValueError(f'node budget exhausted: visited={visited}, next={4*len(parent)}, depth={depth}')
        nodes = np.repeat(parent, 4, axis=0)
        mid_h, mid_mu = (parent[:,0]+parent[:,1])/2, (parent[:,2]+parent[:,3])/2
        if np.any(mid_h == parent[:,0]) or np.any(mid_h == parent[:,1]) or np.any(mid_mu == parent[:,2]) or np.any(mid_mu == parent[:,3]):
            raise ValueError('float64 subdivision resolution exhausted')
        nodes[0::4,1], nodes[0::4,3] = mid_h, mid_mu
        nodes[1::4,0], nodes[1::4,3] = mid_h, mid_mu
        nodes[2::4,1], nodes[2::4,2] = mid_h, mid_mu
        nodes[3::4,0], nodes[3::4,2] = mid_h, mid_mu
        owners = np.repeat(owners, 4)
    raise ValueError('depth budget exhausted')


def witness(geometry, patches):
    """Sample only for falsification; a finite grid never proves an enclosure."""
    prepared = patch_geometry(patches)
    count = 0
    for kind, size, centre, rotation in zip(geometry.kinds, geometry.sizes_m,
                                          geometry.positions_eye_m, geometry.rotations_eye):
        lower, upper = entry_bounds(kind, size, centre, rotation, patches, prepared)
        for fi in (0., .25, .5, .75, 1.):
            for fj in (0., .25, .5, .75, 1.):
                rays = directions(patches[:,0]+fi*(patches[:,1]-patches[:,0]),
                                  patches[:,2]+fj*(patches[:,3]-patches[:,2]))
                for index, ray in enumerate(rays):
                    native = mj.mju_rayGeom(centre, rotation.ravel(), size, np.zeros(3), ray, int(kind))
                    if native >= 0:
                        assert lower[index] <= native+1e-10, (kind, 'lower', lower[index], native)
                        if np.isfinite(upper[index]):
                            assert native <= upper[index]+1e-10, (kind, 'upper', native, upper[index])
                    else:
                        assert not np.isfinite(upper[index]), (kind, 'false all-hit', upper[index])
                    count += 1
    return count


def one_geometry(kind, size, centre, angle):
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array(((c, 0., s), (0., 1., 0.), (-s, 0., c)))
    return SimpleNamespace(kinds=np.array((kind,)), sizes_m=np.array((size,)),
                           positions_eye_m=np.array((centre,)), rotations_eye=np.array((rotation,)))


def native_panel_bounds(geometry, index, apertures):
    """Independent initial-bench silhouette from actual compiled box extents.

    The huge finite panel loses picometres at centre-minus-halfsize. Using
    its ideal pre-compilation edge instead compares two different scenes.
    This reference uses corner angles, not the renderer's face-chart solver.
    Outside the conservative vertical support, coverage remains an interval.
    It is float64 geometry, not directed-rounding interval arithmetic.
    """
    assert geometry.kinds[index] == BOX
    np.testing.assert_array_equal(geometry.rotations_eye[index], np.eye(3))
    low = geometry.positions_eye_m[index] - geometry.sizes_m[index]
    high = geometry.positions_eye_m[index] + geometry.sizes_m[index]
    near, far = low[0], high[0]
    vertical = min(-low[2], high[2])
    assert 0 < near < far < vertical
    assert np.all(np.abs(apertures[:, 2:]) <= math.sqrt(.5))
    corners = [math.atan2(y, x) for x in (near, far) for y in (low[1], high[1])]
    lo, hi = min(corners), max(corners)
    hlo, hhi = apertures[:, 0], apertures[:, 1]
    coverage = np.maximum(0., np.minimum(hhi, hi) - np.maximum(hlo, lo)) / (hhi-hlo)
    safe_h = math.acos(far/vertical)
    certain = np.maximum(0., np.minimum(hhi, min(hi, safe_h))
                         - np.maximum(hlo, max(lo, -safe_h))) / (hhi-hlo)
    return certain[:, None]*BANDS, coverage[:, None]*BANDS


def main():
    started = time.perf_counter()
    print(json.dumps({'pid': os.getpid(), 'kind': 'offline float64 regime, not formal certified optics'}), flush=True)
    sites = retinal_apertures()
    size_by_kind = {SPHERE: (.07, 0., 0.), CAPSULE: (.025, .12, 0.),
                   ELLIPSOID: (.12, .03, .07), CYLINDER: (.04, .12, 0.), BOX: (.03, .07, .12)}
    witnessed = 0
    for kind in KINDS:
        for distance in (.16, .7, 3.):
            for angle in (0., .6, 1.4):
                geometry = one_geometry(kind, size_by_kind[kind], (distance, .031, .014), angle)
                validate_geometry(geometry)
                witnessed += witness(geometry, sites[135::613])
    print(json.dumps({'native_sampled_ray_witnesses': witnessed, 'enclosure_discrepancies': 0}), flush=True)
    # Analytic cap: axis-centred sphere subtends Omega=2*pi*(1-sqrt(1-r^2/d^2)).
    # Integrating one enclosing rectangle checks aperture bounds independently.
    cap = one_geometry(SPHERE, (.07, 0., 0.), (.7, 0., 0.), 0.)
    aperture = np.array(((-.2, .2, -.2, .2),))
    image, uncertainty, nodes, depth, _ = integrate(cap, aperture, np.ones((1,6)), 1/510)
    expected = 2*math.pi*(1-math.sqrt(1-.1**2)) / .16
    assert abs(image[0,0]-expected) <= uncertainty[0,0]+1e-12
    print(json.dumps({'analytic_sphere': expected, 'measured': image[0,0],
                      'absolute_bound': uncertainty[0,0], 'nodes': nodes, 'depth': depth}), flush=True)
    # Localized source-review boundaries: malformed roster/budget/zero area
    # must refuse instead of changing the apparent physical image.
    invalid = one_geometry(SPHERE, (.07, 0., 0.), (.7, 0., 0.), 0.)
    invalid.positions_eye_m = np.empty((0, 3))
    cases = ((invalid, aperture, {}),
             (cap, aperture, {'max_nodes': 1.5}),
             (cap, aperture, {'max_depth': -1}),
             (cap, np.array(((0., 1e-200, 0., 1e-200),)), {}),
             (one_geometry(SPHERE, (1e-20,0.,0.), (1.,0.,0.), 0.), aperture, {}),
             (one_geometry(SPHERE, (1.,0.,0.), (1e200,0.,0.), 0.), aperture, {}))
    for geom, bounds, limits in cases:
        try:
            integrate(geom, bounds, np.ones((1, 6)), 1/510, **limits)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid numerical/geometry request admitted')
    print(json.dumps({'admission_refusals': len(cases)}), flush=True)
    # Off-centre sub-aperture cap: translation in longitude preserves dOmega.
    tiny = one_geometry(SPHERE, (.0004, 0., 0.), (.7*math.cos(.041), .7*math.sin(.041), 0.), 0.)
    tiny_aperture = np.array(((.038, .044, -.003, .003),))
    tiny_image, tiny_error, tiny_nodes, _, _ = integrate(tiny, tiny_aperture, np.ones((1, 6)), 1/510)
    ratio = .0004/.7
    # Stable form of 1-sqrt(1-ratio^2).
    tiny_expected = 2*math.pi*ratio**2/(1+math.sqrt(1-ratio**2)) / (.006*.006)
    assert abs(tiny_image[0,0]-tiny_expected) <= tiny_error[0,0]+1e-12
    print(json.dumps({'off_centre_subaperture_cap': tiny_expected,
                      'measured': tiny_image[0,0], 'bound': tiny_error[0,0],
                      'nodes': tiny_nodes}), flush=True)
    # Independent whole/half-cap and partition laws; no image-derived answers.
    aperture = np.array(((-.3,.3,-.3,.3),))
    checks = 0
    for centre, radius in ((np.array((.7,0.,0.)),.07),
                           (np.array((.7,.05,.04)),.07),
                           (np.array((.7,.0287,0.)),.0004)):
        ratio = radius/np.linalg.norm(centre)
        expected = 2*math.pi*ratio**2/(1+math.sqrt(1-ratio**2))
        whole, whole_error = cap_solid_angles(centre, radius, aperture, np.empty((0,3)))
        assert abs(whole[0]-expected) <= whole_error[0]+1e-12
        plane = np.cross(centre, np.array((0.,0.,1.)))[None,:]
        half, half_error = cap_solid_angles(centre, radius, aperture, plane)
        assert abs(2*half[0]-expected) <= 2*half_error[0]+1e-12
        mid = math.atan2(centre[1],centre[0])
        split = np.array(((-.3,mid,-.3,.3),(mid,.3,-.3,.3)))
        pieces, pieces_error = cap_solid_angles(centre, radius, split, np.empty((0,3)))
        assert abs(float(pieces.sum())-expected) <= float(pieces_error.sum())+1e-12
        checks += 3
    print(json.dumps({'analytic_cap_laws':checks}), flush=True)
    # Real full finite roster, including all self surfaces; no plane removal.
    base_xml, _ = scene(.117, None)
    for scene_label in ('original', 'curved_foreground'):
        root = ET.fromstring(base_xml)
        if scene_label == 'curved_foreground':
            ET.SubElement(root.find('worldbody'), 'geom', name='curved-foreground', type='sphere',
                          pos=f'.8 .07 {EYE_Z}', size='.07')
            ET.SubElement(root.find('worldbody'), 'geom', name='small-foreground', type='sphere',
                          pos=f'.8 -.13 {EYE_Z+.07}', size='.0004')
        xml = ET.tostring(root, encoding='unicode')
        engine = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
        initial = engine.initial_state()
        effort = ((engine.actuator_names.index('guala/head/yaw/effort'), .01),)
        moved = engine.advance(initial, None, 50000, 1., effort_updates=effort).state
        for label, state in (('initial', initial), ('moved', moved)):
            geometry = engine.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
            validate_geometry(geometry)
            radiance = np.ones((len(geometry.kinds),6))
            radiance[engine.geom_names.index('dark-panel')] = 0.
            radiance[engine.geom_names.index('emissive-panel')] = BANDS
            if scene_label == 'curved_foreground':
                radiance[engine.geom_names.index('curved-foreground')] = (.1, .3, .5, .7, .9, 1.)
                radiance[engine.geom_names.index('small-foreground')] = (.9, .7, .5, .3, .1, 0.)
                for name in ('curved-foreground', 'small-foreground'):
                    # Authentic native point witness, not an aperture certificate.
                    index = engine.geom_names.index(name)
                    ray = geometry.positions_eye_m[index:index+1].copy()
                    observed = engine.ray_geometry(state, 'guala/head', ORIGIN, ray, max_rays=1)
                    assert observed.geom_indices[0] == index
            before = engine.observe(state)
            begin = time.perf_counter()
            try:
                image, uncertainty, nodes, depth, residual_area = integrate(geometry, sites, radiance, 1/510)
            except ValueError as exc:
                result = {'status': 'refused', 'reason': str(exc)}
            else:
                elapsed = time.perf_counter()-begin
                if scene_label == 'original' and label == 'initial':
                    lower, upper = native_panel_bounds(
                        geometry, engine.geom_names.index('emissive-panel'), sites)
                    assert np.all(image-uncertainty <= upper+1e-10)
                    assert np.all(image+uncertainty >= lower-1e-10)
                if scene_label == 'curved_foreground' and label == 'initial':
                    old_source = subprocess.check_output(
                        ['git','show','dc769bbcd:tools/guala_body_curved_optical_regime.py'], text=True)
                    old = {'__name__':'reviewed_predecessor'}
                    exec(compile(old_source,'<reviewed predecessor dc769bbcd>','exec'),old)
                    prior, prior_error, _, _ = old['integrate'](geometry, sites, radiance, 1/510)
                    nested = np.all((image-uncertainty >= prior-prior_error-1e-10)
                                    & (image+uncertainty <= prior+prior_error+1e-10),axis=1)
                    assert np.all(nested[residual_area == 0]), 'analytic result outside predecessor interval'
                    mixed = np.flatnonzero(~nested & (residual_area > 0))
                    if len(mixed):
                        # Independently stopped adaptive bounds need not nest.
                        # Resolve only the non-nested mixed roots against a
                        # 16x finer predecessor, with the SAME work ceilings.
                        reference, reference_error, _, _ = old['integrate'](
                            geometry, sites[mixed], radiance, (1/510)/16)
                        assert np.all(reference-reference_error >= image[mixed]-uncertainty[mixed]-1e-10), 'mixed reference inconclusive'
                        assert np.all(reference+reference_error <= image[mixed]+uncertainty[mixed]+1e-10), 'mixed reference inconclusive'
                    print(json.dumps({'analytic_predecessor_containment':'passed',
                                      'mixed_independent_reference_roots':len(mixed)}),flush=True)
                fresh = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
                cold = fresh.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
                second = integrate(cold, sites, radiance, 1/510)
                np.testing.assert_array_equal(image, second[0])
                np.testing.assert_array_equal(uncertainty, second[1])
                np.testing.assert_array_equal(residual_area, second[4])
                assert engine.advance(state, None, 1000, 1.) == fresh.advance(state, None, 1000, 1.)
                result = {'status': 'bounded', 'nodes': nodes, 'depth': depth,
                          'frame_seconds': elapsed, 'max_absolute_bound': float(uncertainty.max())}
            assert engine.observe(state) == before
            print(json.dumps({'scene': scene_label, 'pose': label, 'geoms': len(geometry.kinds),
                              'sites': len(sites),
                              'seconds_including_cold_and_reference': time.perf_counter()-begin,
                              **result}), flush=True)
    print(json.dumps({'seconds': time.perf_counter()-started,
                      'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)


if __name__ == '__main__':
    main()
