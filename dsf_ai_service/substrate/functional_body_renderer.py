"""Bounded native-primitive aperture integration under numerical-optics approval.

One transient geometric operator; no world state or cognitive authority.
Float64 analytical evaluation is not directed-rounding certification.
This module is not yet mounted in the ordinary organism loop.
"""
from __future__ import annotations

import math

import mujoco as mj
import numpy as np

from .functional_body_optics import (
    _aperture_geometry, _dot_extrema, _plane_parameters, _validate_apertures,
    disjoint_surface_radiance,
)
from .functional_body_visibility import PlanarSurface, visible_planar_regions
from .functional_body_sphere_cap import cap_solid_angles, sphere_parameters
from .functional_body_materials import _prepare_material, _material_regions

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


def box_face_charts(size, centre, rotation):
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
            faces.append((axis, sign, PlanarSurface.from_chart(origin, axes, quad, max_corners=4)))
    return tuple(faces)


def box_faces(size, centre, rotation):
    return tuple(face for _, _, face in box_face_charts(size, centre, rotation))


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


def prepare_scene(geometry, apertures, radiance, face_materials):
    domain = np.array(((apertures[:,0].min(), apertures[:,1].max(),
                        apertures[:,2].min(), apertures[:,3].max()),))
    domain_geometry = patch_geometry(domain)
    boxes, curved, surfaces, prepared = {}, [], [], []
    input_halfspaces = 0
    for i, (kind, size, centre, rotation) in enumerate(zip(
            geometry.kinds, geometry.sizes_m, geometry.positions_eye_m, geometry.rotations_eye)):
        if kind == BOX:
            charts = box_face_charts(size, centre, rotation)
            boxes[i] = tuple(face for _, _, face in charts)
            for axis, sign, face in charts:
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
                prepared.append(face_materials.get((i, axis, sign), (None, radiance[i:i+1])))
        else:
            lower, _ = entry_bounds(kind, size, centre, rotation, domain, domain_geometry)
            if np.isfinite(lower[0]):
                curved.append(i)
    regions = visible_planar_regions(tuple(surfaces), domain, max_halfspaces=32768,
                                     max_work=1048576, max_cells=32768)
    planes, values = _material_regions(surfaces, prepared, regions, max_halfspaces=32768)
    return boxes, tuple(curved), planes, values


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
    half, radius = radii(kind, size)
    original_count = len(patches)
    rows = np.arange(original_count)
    with np.errstate(over='ignore', invalid='ignore'):
        enclosure_offset = float(centre @ centre-radius*radius)
    if math.isfinite(enclosure_offset) and enclosure_offset > 0:
        # A ray missing this enclosing sphere cannot hit the contained solid.
        # The maximum covers the ENTIRE aperture, not a sampled central ray.
        _, high = _dot_extrema(centre[None,:], patches,
                               _plane_parameters(centre[None,:]), angular)
        rows = np.flatnonzero(high[0] >= math.sqrt(enclosure_offset))
        if not len(rows):
            return np.full(original_count, np.inf), np.full(original_count, np.inf)
        patches, direction, epsilon = patches[rows], direction[rows], epsilon[rows]
        angular = tuple(a[rows] for a in angular)
    origin = -centre @ rotation
    velocity = direction @ rotation
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
    inner = np.flatnonzero(nonempty & possible)
    if len(inner):
        a, b = interval(kind, contracted[inner], origin, velocity[inner])
        entry = np.maximum(a, 0)
        upper[inner] = np.where((b >= entry) & (entry <= tmax[inner]), entry, np.inf)
    all_lower, all_upper = np.full(original_count, np.inf), np.full(original_count, np.inf)
    all_lower[rows], all_upper[rows] = lower, upper
    return all_lower, all_upper


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


def integrate(geometry, apertures, radiance, error, *, max_nodes=262144, max_depth=20,
              face_materials=(), max_material_cells=0):
    """Midpoint, total radius, work, depth, unresolved area fraction; or refusal."""
    validate_geometry(geometry)
    _validate_apertures(apertures)
    if type(max_nodes) is not int or not 0 < max_nodes <= 262144 or type(max_depth) is not int or not 0 <= max_depth <= 20:
        raise ValueError('positive integer node budget and bounded integer depth required')
    if not 0 < len(apertures) <= 19335 or error <= 0 or not math.isfinite(error):
        raise ValueError('bounded retinal/error request required')
    if radiance.shape != (len(geometry.kinds), 6) or not np.isfinite(radiance).all() or np.any(radiance < 0):
        raise ValueError('finite six-band diagnostic emitters required')
    if (type(face_materials) is not tuple or len(face_materials) > 6*len(geometry.kinds)
            or type(max_material_cells) is not int or max_material_cells < 0):
        raise ValueError('bounded explicit physical face materials required')
    prepared_materials, declared_cells = {}, 0
    for override in face_materials:
        if type(override) is not tuple or len(override) != 4:
            raise ValueError('native row, local axis, side and material required')
        index, axis, side, material = override
        if (any(type(n) is not int for n in (index, axis, side))
                or not 0 <= index < len(geometry.kinds) or geometry.kinds[index] != BOX
                or axis not in (0, 1, 2) or side not in (-1, 1)):
            raise ValueError('material chart must name an actual native box face')
        key = index, axis, side
        if key in prepared_materials:
            raise ValueError('duplicate native face material')
        pattern, values = _prepare_material(material)
        if pattern is not None:
            declared_cells += pattern.rows*pattern.columns
            if declared_cells > max_material_cells:
                raise ValueError('declared material cell bound exceeded')
        prepared_materials[key] = pattern, values
    maximum = radiance.max(axis=0)
    for _, values in prepared_materials.values():
        maximum = np.maximum(maximum, values.max(axis=0))
    total = (apertures[:, 1]-apertures[:, 0])*(apertures[:, 3]-apertures[:, 2])
    if not np.isfinite(total).all() or np.any(total <= 0):
        raise ValueError('positive representable aperture areas required')
    boxes, curved, regions, values = prepare_scene(geometry, apertures, radiance, prepared_materials)
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
        hit = resolved >= 0
        planar_only[hit] |= geometry.kinds[resolved[hit]] == BOX
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
            if not np.isfinite(mean).all() or not np.isfinite(bound).all():
                raise ValueError('cap material composition exceeds numerical domain')
            np.add.at(exact, owners[selected], area[selected,None]*mean)
            np.add.at(numerical, owners[selected], bound/total[owners[selected],None])
        if not np.isfinite(numerical).all() or np.any(numerical > error):
            raise ValueError('analytic event uncertainty exceeds optical budget')
        hit = (resolved >= 0) & ~planar_only
        np.add.at(exact, owners[hit], area[hit, None]*radiance[resolved[hit]])
        if not np.isfinite(exact).all():
            raise ValueError('accumulated optical radiance exceeds numerical domain')
        active = (resolved == -2) & ~planar_only & (foreground_cap < 0)
        unknown = np.bincount(owners[active], weights=area[active], minlength=len(apertures))
        done = np.all(numerical + unknown[:,None]*maximum/2 <= error, axis=1)
        completed = done & (unknown > 0)
        uncertainty[completed] = unknown[completed]
        keep = active & ~done[owners]
        if not keep.any():
            residual = uncertainty[:, None]*maximum/2
            image, radius = exact + residual, residual + numerical
            if not np.isfinite(image).all() or not np.isfinite(radius).all():
                raise ValueError('final optical result exceeds numerical domain')
            return image, radius, visited, depth, uncertainty
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


def integrate_materials(geometry, apertures, materials, error, *, face_materials=(),
                        max_material_cells, max_nodes=262144, max_depth=20):
    """Physical materials on all native shapes; explicit chart overrides only.

    Base materials are uniform; a curved pattern without its physical chart
    refuses. Uniform incident irradiance is declared, not estimated from gaze.
    Materials remain externally owned and must accompany cold-restored geometry.
    """
    if (type(materials) is not tuple or not 0 < len(materials) <= 256
            or len(materials) != len(geometry.kinds)):
        raise ValueError('one physical base material per native primitive required')
    values = []
    for material in materials:
        pattern, bands = _prepare_material(material)
        if pattern is not None:
            raise ValueError('pattern requires an explicitly declared box-face chart')
        values.append(bands[0])
    return integrate(geometry, apertures, np.asarray(values, dtype=np.float64), error,
                     max_nodes=max_nodes, max_depth=max_depth, face_materials=face_materials,
                     max_material_cells=max_material_cells)
