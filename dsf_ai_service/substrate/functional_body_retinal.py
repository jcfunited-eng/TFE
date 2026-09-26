"""Finite-aperture retinal light from one current native world source view.

Approved bounded float64 optics, not directed-rounding certification. Original
native geometry owns visibility; paint never becomes an occluder. No cognition,
world mutation, second scene owner, persistence, or live-loop fallback.
"""
from __future__ import annotations

import math
import numpy as np

from .functional_body_illumination import NativeIllumination
from .functional_body_materials import _material_regions
from .functional_body_optical_sources import region_face_charts
from .functional_body_optics import (
    _dot_extrema, _plane_parameters, _validate_apertures,
    aperture_solid_angles, disjoint_region_areas,
)
from .functional_body_renderer import BOX, classify, scene_geometry
from .functional_body_sphere_cap import cap_solid_angles
from .functional_body_visibility import VisibleRegion, subtract_convex
from .w1_physical_receptors import LAMP_NEAR_GAIN


def _painted_regions(sources, surfaces, addresses, visible, domain):
    """Visible native panels intersected with original, ordered physical paint."""
    planes, coefficients, owners = [], [], []
    retained, work = 0, 0

    def area(normals):
        nonlocal work
        k = len(normals)
        work += k*(k-1)+6*k+2
        if k > 32768 or work > 1048576:
            raise ValueError("room paint partition work exhausted")
        return float(aperture_solid_angles(normals, domain, max_cells=32768)[0])

    def append(surface, pattern, values, regions, face_index):
        nonlocal retained
        fragments, colors = _material_regions((surface,), ((pattern, values),),
            tuple(VisibleRegion(0, p) for p in regions), max_halfspaces=32768-retained)
        emission = sources.materials[addresses[face_index][0]].emission_ppm
        for fragment, color in zip(fragments, colors):
            # Absorbers already occluded their background in visible geometry.
            if not np.any(color) and not any(emission):
                continue
            retained += len(fragment)
            if retained > 32768:
                raise ValueError("retinal material halfspace residency exceeded")
            planes.append(fragment)
            coefficients.append(color)
            owners.append(face_index)

    for face_index, (surface, (row, axis, side)) in enumerate(zip(surfaces, addresses)):
        material = sources.materials[row]
        regions = tuple(r.halfspaces for r in visible if r.surface_index == face_index)
        if not regions:
            continue
        base = np.asarray(material.reflectance_ppm, dtype=float)[None, :]/1e6
        if material.box_pattern is not None:
            pattern = material.box_pattern
            append(surface, pattern, np.asarray(pattern.palette_reflectance_ppm)/1e6,
                   regions, face_index)
        elif material.region_looks:
            remaining = regions
            for chart, pattern in region_face_charts(sources, row, axis, side,
                                                      max_charts=len(material.region_looks)):
                covered, successor = [], []
                resident = sum(len(p) for p in remaining)
                for region in remaining:
                    inside, outside = subtract_convex(region, chart.halfspaces, area,
                                                       max_halfspaces=32768-retained)
                    if inside is not None:
                        covered.append(inside)
                    successor.extend(outside)
                    resident += sum(len(p) for p in outside)-len(region)
                    if resident + sum(len(p) for p in covered) + retained > 32768:
                        raise ValueError("ordered paint partition residency exceeded")
                if covered:
                    append(chart, pattern, np.asarray(pattern.palette_reflectance_ppm)/1e6,
                           covered, face_index)
                remaining = tuple(successor)
                if not remaining:
                    break
            append(surface, None, base, remaining, face_index)
        else:
            append(surface, None, base, regions, face_index)
    return tuple(planes), np.asarray(coefficients).reshape(-1, 6), tuple(owners)


def _planar_patch(sources, face, address, patches, prepared):
    """Position ball for all reached points, even if central ray misses panel."""
    row, axis, side = address
    geometry = sources.geometry
    rotation, size = geometry.rotations_eye[row], geometry.sizes_m[row]
    normal = side*rotation[:, axis]
    centre = geometry.positions_eye_m[row] + normal*size[axis]
    tangent = [a for a in range(3) if a != axis]
    whole_radius = float(np.linalg.norm(size[tangent]))
    radial_max = np.linalg.norm(centre)+whole_radius
    direction, angular_radius, angular = prepared
    inverse = face.inverse[0:1]
    near, far = _dot_extrema(inverse, patches, _plane_parameters(inverse), angular)
    low = np.divide(1., far[0], out=np.zeros(len(patches)), where=far[0] > 0)
    high = np.divide(1., near[0], out=np.full(len(patches), radial_max), where=near[0] > 0)
    high = np.minimum(high, radial_max)
    central = direction @ face.inverse[0]
    distance = np.divide(1., central, out=np.zeros(len(patches)), where=central > 0)
    delta = (np.maximum(np.abs(low-distance), np.abs(high-distance))
             * np.linalg.norm(direction, axis=1) + high*angular_radius)
    use_ray = (central > 0) & (delta < whole_radius) & (low <= high)
    points = np.where(use_ray[:, None], distance[:, None]*direction, centre)
    delta = np.where(use_ray, delta, whole_radius)
    return points, np.broadcast_to(normal, points.shape), delta


class _CurrentLightIntegral:
    """Transient physical integral operands; no stored scene or organism state."""

    def __init__(self, sources, apertures, max_shadow_tests):
        self.sources = sources
        self.light = NativeIllumination(sources)
        self.boxes, self.curved, self.faces, self.addresses, visible = scene_geometry(
            sources.geometry, apertures)
        domain = np.array(((apertures[:, 0].min(), apertures[:, 1].max(),
                            apertures[:, 2].min(), apertures[:, 3].max()),))
        self.planes, self.reflectance, self.face_ids = _painted_regions(
            sources, self.faces, self.addresses, visible, domain)
        self.shadow_work = 0
        self.max_shadow_tests = max_shadow_tests
        self.room_cost, self.room_lower, self.room_upper = {}, {}, {}
        for key, (region, lamps, sun, base) in self.light.rooms.items():
            self.room_cost[key] = (2*len(sources.geometry.kinds)*(len(lamps)+int(sun is not None))
                                   + (len(region.windows) if sun is not None else 0))
            self.room_lower[key] = base
            ceiling = base.copy()
            for lamp, _ in lamps:
                ceiling += LAMP_NEAR_GAIN*np.asarray(lamp.ppm)/1e6
            if sun is not None:
                ceiling += sources.solar_sample.sky_ppm/1e6
            self.room_upper[key] = ceiling
        self.base_reflectance = np.asarray([m.reflectance_ppm for m in sources.materials])/1e6
        self.emission = np.asarray([m.emission_ppm for m in sources.materials])/1e6
        maximum = np.zeros(6)
        for row, material in enumerate(sources.materials):
            peak = self.base_reflectance[row]
            patterns = (() if material.box_pattern is None else (material.box_pattern,))
            patterns += tuple(look.surface for look in material.region_looks)
            for pattern in patterns:
                peak = np.maximum(peak, np.asarray(pattern.palette_reflectance_ppm).max(axis=0)/1e6)
            maximum = np.maximum(maximum, self.emission[row]+peak*self.room_upper[self.light.surface_regions[row]])
        if not np.isfinite(maximum).all():
            raise ValueError("physical radiance ceiling exceeds numerical domain")
        self.maximum = maximum

    def charge(self, row, count):
        work = self.room_cost[self.light.surface_regions[row]]*count
        self.shadow_work += work
        if self.shadow_work > self.max_shadow_tests:
            raise ValueError("cumulative retinal shadow work exhausted")
        return work

    def planar(self, patches, cap, prepared):
        """Integrate visible paint once, then bound spatial light on each face."""
        lower, upper = np.zeros((len(patches), 6)), np.zeros((len(patches), 6))
        solid = (patches[:, 1]-patches[:, 0])*(patches[:, 3]-patches[:, 2])
        current = None
        weighted_low = weighted_high = area_low = area_high = None

        def finish(key):
            begin, end, face_index = key
            row = self.addresses[face_index][0]
            active = np.flatnonzero(area_high > 0)
            if not len(active):
                return
            indices = begin+active
            lo, hi = np.zeros((len(active), 6)), np.zeros((len(active), 6))
            reflected = np.flatnonzero(np.any(weighted_high[active] > 0, axis=1))
            if len(reflected):
                selected = indices[reflected]
                prep = (prepared[0][selected], prepared[1][selected],
                        tuple(a[selected] for a in prepared[2]))
                points, normals, delta = _planar_patch(self.sources, self.faces[face_index],
                    self.addresses[face_index], patches[selected], prep)
                cost = self.charge(row, len(selected))
                light_low, light_high = self.light.bounds(self.light.surface_regions[row],
                    points, normals, position_radius_m=delta, normal_radius=np.zeros(len(selected)),
                    receiver_rows=np.full(len(selected), row, dtype=int),
                    max_points=len(selected), max_shadow_tests=cost)
                lo[reflected], hi[reflected] = light_low, light_high
            lower[indices] += (weighted_low[active]*lo
                + area_low[active, None]*self.emission[row])/solid[indices, None]
            upper[indices] += (weighted_high[active]*hi
                + area_high[active, None]*self.emission[row])/solid[indices, None]

        areas = disjoint_region_areas(self.planes, patches, max_cells=32768, max_halfspaces=32768)
        for begin, end, index, area in areas:
            key = begin, end, self.face_ids[index]
            if key != current:
                if current is not None:
                    finish(current)
                current = key
                weighted_low, weighted_high = np.zeros((end-begin, 6)), np.zeros((end-begin, 6))
                area_low, area_high = np.zeros(end-begin), np.zeros(end-begin)
            lo, hi = area.copy(), area.copy()
            for row in np.unique(cap[begin:end]):
                if row < 0:
                    continue
                selected = np.flatnonzero((cap[begin:end] == row) & (area > 0))
                if not len(selected):
                    continue
                covered, error = cap_solid_angles(
                    self.sources.geometry.positions_eye_m[row],
                    self.sources.geometry.sizes_m[row, 0], patches[begin+selected], self.planes[index])
                lo[selected] = np.maximum(0., area[selected]-covered-error)
                hi[selected] = np.minimum(area[selected], np.maximum(0., area[selected]-covered+error))
            weighted_low += lo[:, None]*self.reflectance[index]
            weighted_high += hi[:, None]*self.reflectance[index]
            area_low += lo
            area_high += hi
        if current is not None:
            finish(current)
        return lower, upper

    def bounds(self, patches):
        geometry = self.sources.geometry
        resolved, planar_only, cap, prepared, first, last = classify(
            geometry, patches, self.boxes, self.curved)
        hit = resolved >= 0
        planar_only[hit] |= geometry.kinds[resolved[hit]] == BOX
        lower, upper = np.zeros((len(patches), 6)), np.zeros((len(patches), 6))
        selected = np.flatnonzero(planar_only | (cap >= 0))
        if len(selected):
            prep = (prepared[0][selected], prepared[1][selected],
                    tuple(a[selected] for a in prepared[2]))
            lower[selected], upper[selected] = self.planar(patches[selected], cap[selected], prep)
        for row in np.unique(cap[cap >= 0]):
            selected = np.flatnonzero(cap == row)
            region = self.light.surface_regions[row]
            area, error = cap_solid_angles(geometry.positions_eye_m[row],
                geometry.sizes_m[row, 0], patches[selected], np.empty((0, 3)))
            solid = ((patches[selected, 1]-patches[selected, 0])
                     *(patches[selected, 3]-patches[selected, 2]))
            lo = np.maximum(0., area-error)/solid
            hi = np.minimum(solid, area+error)/solid
            lower[selected] += lo[:, None]*(self.base_reflectance[row]*self.room_lower[region]+self.emission[row])
            upper[selected] += hi[:, None]*(self.base_reflectance[row]*self.room_upper[region]+self.emission[row])
        for row in np.unique(resolved[hit & ~planar_only]):
            selected = np.flatnonzero((resolved == row) & ~planar_only)
            lo = hi = np.zeros((len(selected), 6))
            if np.any(self.base_reflectance[row]):
                cost = self.charge(int(row), len(selected))
                lo, hi = self.light.surface_bounds(int(row), prepared[0][selected],
                    prepared[1][selected], first[selected], last[selected],
                    max_points=len(selected), max_shadow_tests=cost)
            lower[selected] = self.base_reflectance[row]*lo+self.emission[row]
            upper[selected] = self.base_reflectance[row]*hi+self.emission[row]
        unknown = (resolved == -2) & ~planar_only & (cap < 0)
        upper[unknown] = self.maximum
        if (not np.isfinite(lower).all() or not np.isfinite(upper).all()
                or np.any(lower < 0) or np.any(upper < lower)):
            raise ValueError("invalid physical retinal interval")
        return lower, upper, unknown


def native_retinal_radiance(sources, apertures, error, *,
                            max_shadow_tests, max_nodes=262144, max_depth=20):
    """Six-band midpoint/radius, visited nodes, depth, unresolved area fraction.

    The world source query already admitted material custody and source cells.
    This consumer admits geometric/event/refinement/shadow work. No production
    fallback on resource or physical refusal; all partial operands are discarded.
    """
    if (not isinstance(apertures, np.ndarray) or apertures.ndim != 2
            or apertures.shape[1] != 4 or apertures.dtype != np.dtype(np.float64)
            or not 0 < len(apertures) <= 19335 or type(error) not in (float, int)
            or not math.isfinite(error) or error <= 0
            or type(max_nodes) is not int or not 0 < max_nodes <= 262144
            or type(max_depth) is not int or not 0 <= max_depth <= 20
            or type(max_shadow_tests) is not int or max_shadow_tests < 0):
        raise ValueError("bounded retinal integration request required")
    if len(apertures) > max_nodes:
        raise ValueError("node budget exhausted before scene work")
    _validate_apertures(apertures)
    total = (apertures[:, 1]-apertures[:, 0])*(apertures[:, 3]-apertures[:, 2])
    if not np.isfinite(total).all() or np.any(total <= 0):
        raise ValueError("positive representable aperture areas required")
    scene = _CurrentLightIntegral(sources, apertures, max_shadow_tests)
    exact = np.zeros((len(apertures), 6))
    result, radius = exact.copy(), exact.copy()
    uncertainty = np.zeros(len(apertures))
    nodes, owners = apertures.copy(), np.arange(len(apertures))
    visited = 0
    for depth in range(max_depth+1):
        visited += len(nodes)
        if visited > max_nodes:
            raise ValueError("node budget exhausted")
        weights = ((nodes[:, 1]-nodes[:, 0])*(nodes[:, 3]-nodes[:, 2]))/total[owners]
        if np.any(weights <= 0) or not np.isfinite(weights).all():
            raise ValueError("positive representable patch areas required")
        lo, hi, unknown = scene.bounds(nodes)
        low, high = exact.copy(), exact.copy()
        np.add.at(low, owners, weights[:, None]*lo)
        np.add.at(high, owners, weights[:, None]*hi)
        if not np.isfinite(low).all() or not np.isfinite(high).all():
            raise ValueError("integrated retinal light exceeds numerical domain")
        width = (high-low)/2
        done = np.all(width <= error, axis=1)
        active_owners = np.unique(owners)
        completed = active_owners[done[active_owners]]
        result[completed] = low[completed]+width[completed]
        radius[completed] = width[completed]
        unknown_area = np.bincount(owners[unknown], weights=weights[unknown], minlength=len(apertures))
        uncertainty[completed] = unknown_area[completed]
        exact_patch = np.all(lo == hi, axis=1)
        accepted = exact_patch & ~done[owners]
        np.add.at(exact, owners[accepted], weights[accepted, None]*lo[accepted])
        keep = ~exact_patch & ~done[owners]
        if not keep.any():
            return result, radius, visited, depth, uncertainty
        if depth == max_depth:
            break
        parent, owners = nodes[keep], owners[keep]
        if visited+4*len(parent) > max_nodes:
            raise ValueError("node budget exhausted before subdivision")
        mid_h, mid_mu = (parent[:, 0]+parent[:, 1])/2, (parent[:, 2]+parent[:, 3])/2
        if (np.any(mid_h == parent[:, 0]) or np.any(mid_h == parent[:, 1])
                or np.any(mid_mu == parent[:, 2]) or np.any(mid_mu == parent[:, 3])):
            raise ValueError("float64 subdivision resolution exhausted")
        nodes = np.repeat(parent, 4, axis=0)
        nodes[0::4, 1], nodes[0::4, 3] = mid_h, mid_mu
        nodes[1::4, 0], nodes[1::4, 3] = mid_h, mid_mu
        nodes[2::4, 1], nodes[2::4, 2] = mid_h, mid_mu
        nodes[3::4, 0], nodes[3::4, 2] = mid_h, mid_mu
        owners = np.repeat(owners, 4)
    raise ValueError("depth budget exhausted")
