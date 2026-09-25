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
import time
from types import SimpleNamespace

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_native import NativeBody
from dsf_ai_service.substrate.functional_body_optics import (
    _aperture_geometry, _dot_extrema, _plane_parameters, _validate_apertures,
)
from tools.guala_body_optical_regime import LIMITS, ORIGIN, retinal_apertures, scene


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


def entry_bounds(kind, size, centre, rotation, patches, prepared):
    direction, epsilon, angular = prepared
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
        changed = (0,) if kind in (SPHERE, CAPSULE) else (0, 1) if kind == CYLINDER else (0, 1, 2)
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


def classify(geometry, patches):
    """-1 background, -2 unresolved, otherwise original primitive row."""
    prepared = patch_geometry(patches)
    first = np.full(len(patches), np.inf)
    second, upper = first.copy(), first.copy()
    first_id = np.full(len(patches), -1, dtype=np.int32)
    winner = first_id.copy()
    for index, (kind, size, centre, rotation) in enumerate(zip(
            geometry.kinds, geometry.sizes_m, geometry.positions_eye_m, geometry.rotations_eye)):
        lo, hi = entry_bounds(kind, size, centre, rotation, patches, prepared)
        replace = lo < first
        second = np.where(replace, first, np.minimum(second, lo))
        first = np.minimum(first, lo)
        first_id = np.where(replace, index, first_id)
        replace_upper = hi < upper
        upper = np.minimum(upper, hi)
        winner = np.where(replace_upper, index, winner)
    competitors = np.where(winner == first_id, second, first)
    resolved = upper < competitors
    return np.where(np.isinf(first), -1, np.where(resolved, winner, -2))


def integrate(geometry, apertures, radiance, error, *, max_nodes=262144, max_depth=20):
    """Six-band interval midpoint and explicit residual bound, or refusal."""
    validate_geometry(geometry)
    _validate_apertures(apertures)
    if type(max_nodes) is not int or not 0 < max_nodes <= 262144 or type(max_depth) is not int or not 0 <= max_depth <= 20:
        raise ValueError('positive integer node budget and bounded integer depth required')
    if len(apertures) > 19335 or error <= 0 or not math.isfinite(error):
        raise ValueError('bounded retinal/error request required')
    if radiance.shape != (len(geometry.kinds), 6) or not np.isfinite(radiance).all() or np.any(radiance < 0):
        raise ValueError('finite six-band diagnostic emitters required')
    maximum = radiance.max(axis=0)
    total = (apertures[:, 1]-apertures[:, 0])*(apertures[:, 3]-apertures[:, 2])
    if not np.isfinite(total).all() or np.any(total <= 0):
        raise ValueError('positive representable aperture areas required')
    exact = np.zeros((len(apertures), 6))
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
        resolved = classify(geometry, nodes)
        area = patch_area / total[owners]
        hit = resolved >= 0
        np.add.at(exact, owners[hit], area[hit, None]*radiance[resolved[hit]])
        active = resolved == -2
        unknown = np.bincount(owners[active], weights=area[active], minlength=len(apertures))
        done = unknown*maximum.max()/2 <= error
        completed = done & (unknown > 0)
        uncertainty[completed] = unknown[completed]
        keep = active & ~done[owners]
        if not keep.any():
            return exact + uncertainty[:, None]*maximum/2, uncertainty[:, None]*maximum/2, visited, depth
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
    image, uncertainty, nodes, depth = integrate(cap, aperture, np.ones((1,6)), 1/510)
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
             (cap, np.array(((0., 1e-200, 0., 1e-200),)), {}))
    for geom, bounds, limits in cases:
        try:
            integrate(geom, bounds, np.ones((1, 6)), 1/510, **limits)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid numerical/geometry request admitted')
    print(json.dumps({'admission_refusals': len(cases)}), flush=True)
    # Real full finite roster, including all self surfaces; no plane removal.
    xml, engine = scene(.117, None)
    initial = engine.initial_state()
    effort = ((engine.actuator_names.index('guala/head/yaw/effort'), .01),)
    moved = engine.advance(initial, None, 50000, 1., effort_updates=effort).state
    for label, state in (('initial', initial), ('moved', moved)):
        geometry = engine.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
        validate_geometry(geometry)
        radiance = np.ones((len(geometry.kinds),6))
        radiance[engine.geom_names.index('dark-panel')] = 0.
        before = engine.observe(state)
        begin = time.perf_counter()
        try:
            image, uncertainty, nodes, depth = integrate(geometry, sites, radiance, 1/510)
        except ValueError as exc:
            result = {'status': 'refused', 'reason': str(exc)}
        else:
            fresh = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
            cold = fresh.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
            second = integrate(cold, sites, radiance, 1/510)
            np.testing.assert_array_equal(image, second[0])
            assert engine.advance(state, None, 1000, 1.) == fresh.advance(state, None, 1000, 1.)
            result = {'status': 'bounded', 'nodes': nodes, 'depth': depth,
                      'max_absolute_bound': float(uncertainty.max())}
        assert engine.observe(state) == before
        print(json.dumps({'pose': label, 'geoms': len(geometry.kinds), 'sites': len(sites),
                          'seconds_including_cold_when_bounded': time.perf_counter()-begin, **result}), flush=True)
    print(json.dumps({'seconds': time.perf_counter()-started,
                      'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)


if __name__ == '__main__':
    main()
