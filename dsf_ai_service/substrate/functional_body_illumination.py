"""Native surface-patch illumination under approved bounded numerical optics.

Existing six-band room ambient / single bounce / point-lamp / directional-sun
law; original native convex solids cast shadows. No retina sampling, cognitive
input, state mutation or second world owner. Bounds are float64 analytic
enclosures, not directed-rounding certificates. A caller must derive its patch
centre, position ball and outward-normal enclosure from ONE convex surface;
arbitrary points/normals are not a physical surface certificate.
"""
from __future__ import annotations

import numpy as np

from .embodiment_world import EmbodimentWorldAuthority
from .functional_body_renderer import (
    BOX, CAPSULE, CYLINDER, ELLIPSOID, SPHERE, interval, interval_pair,
    surface_patch_geometry, validate_geometry,
)
from .w1_physical_receptors import (
    LAMP_NEAR_GAIN, LAMP_REFERENCE_MM, _Light, _bounce_ppm,
)


def _dilate(kind, size, radius):
    """Outer Minkowski enclosure; negative radius gives an inner enclosure."""
    sizes = np.broadcast_to(size, (len(radius), 3)).copy()
    if kind in (SPHERE, CAPSULE):
        sizes[:, 0] += radius
        valid = sizes[:, 0] > 0
    elif kind == CYLINDER:
        sizes[:, :2] += radius[:, None]
        valid = np.all(sizes[:, :2] > 0, axis=1)
    elif kind == BOX:
        sizes += radius[:, None]
        valid = np.all(sizes > 0, axis=1)
    elif kind == ELLIPSOID:
        scale = 1 + radius / min(size)
        sizes *= scale[:, None]
        valid = scale > 0
    else:
        raise ValueError("unsupported native shadow primitive")
    # Empty contractions cannot certify a blocked ray. A harmless positive
    # placeholder prevents division by zero inside the vectorized solver.
    sizes[~valid] = size
    return sizes, valid


def _visibility_bounds(geometry, points, direction, delta, near, far, receiver):
    """Both original bounds, sharing identical ray terms without row copies.

    Convex outward receivers cannot shadow themselves. For positive patches,
    independently rounded expanded/contracted roots remain independent: no
    inference of float inclusion. No new tolerance, shadow law or scene cache.
    """
    certain = np.ones(len(points), dtype=bool)
    possible = certain.copy()
    point_patches = not np.any(delta)
    for row, (kind, size, centre, rotation) in enumerate(zip(
            geometry.kinds, geometry.sizes_m, geometry.positions_eye_m,
            geometry.rotations_eye)):
        own = receiver == row
        if np.all(own):
            continue
        if not np.any(certain | possible):
            break
        origin = (points-centre) @ rotation
        velocity = direction @ rotation
        expanded, _ = _dilate(kind, size, delta)
        if point_patches:
            lo, hi = interval(kind, expanded, origin, velocity)
            inner_lo, inner_hi, nonempty = lo, hi, True
        else:
            contracted, nonempty = _dilate(kind, size, -delta)
            (lo, inner_lo), (hi, inner_hi) = interval_pair(
                kind, expanded, contracted, origin, velocity)
        intersects = (lo <= hi) & (hi > 0) & (lo < far) & (far > 0)
        certain &= ~intersects | own
        blocks = (nonempty & (inner_lo <= inner_hi) & (inner_hi > 0) &
                  (inner_lo < near) & (near > 0) & ~own)
        possible &= ~blocks
    return certain, possible


class NativeIllumination:
    """Transient evaluation over ONE immutable source view; no retained cache."""

    def __init__(self, sources):
        if sources.solar_evidence == "unretained":
            raise ValueError("native illumination requires retained solar evidence")
        if sources.solar_evidence not in ("retained", "absent"):
            raise ValueError("unknown native solar evidence")
        sample = sources.solar_sample
        if (sample is not None) != (sources.solar_evidence == "retained"):
            raise ValueError("native solar source disagrees with retained sample")
        validate_geometry(sources.geometry)
        if len(sources.bindings) != len(sources.geometry.kinds):
            raise ValueError("native surface source roster mismatch")
        self.sources = sources
        self.rotation = np.asarray(sources.geometry.rotation_world).reshape(3, 3)
        self.origin = np.asarray(sources.geometry.origin_world_m)
        frames = {f.name: f for f in sources.world_frames}
        object_frames = dict(sources.native_state.mount.object_frames)
        region_lamps = {r.region_id: [] for r in sources.regions}
        owner_frames = {"object": object_frames, "body": dict(sources.native_state.mount.body_frames)}
        owner_regions = {}
        def region_for(kind, source_id):
            key = kind, source_id
            if key not in owner_regions:
                owner_regions[key] = (source_id if kind == "region" else
                    EmbodimentWorldAuthority._native_region(
                        sources.regions, frames[owner_frames[kind][source_id]]).region_id)
            return owner_regions[key]
        self.surface_regions = tuple(region_for(
            "object" if b.source_kind == "part" else b.source_kind, b.source_id)
            for b, _ in sources.bindings)
        for item in sources.emitters:
            frame = frames[object_frames[item.object_id]]
            region_id = region_for("object", item.object_id)
            height = item.elevation_mm + (
                item.size_mm[2] / 2 if item.shape == "box" else item.radius_mm)
            centre = (np.asarray(frame.position_m) +
                      np.asarray(frame.rotation_world).reshape(3, 3)[:, 2] * height/1000)
            light = _Light("lamp", *(centre*1000), item.radius_mm,
                           item.emission_ppm, item.object_id)
            centre_eye = (centre-self.origin) @ self.rotation
            region_lamps[region_id].append((light, centre_eye))
        self.rooms = {}
        for region in sources.regions:
            lights = [light for light, _ in region_lamps[region.region_id]]
            sun = None
            if (sample is not None and sample.direction_to_sun is not None
                    and sample.direction_to_sun[2] > 0 and region.windows):
                sun = np.asarray(sample.direction_to_sun)
                lights.append(_Light("sun", *sun, 0, (sample.sky_ppm,)*6, None))
            base = (np.asarray(region.illumination_ppm, dtype=float) +
                    np.asarray(_bounce_ppm(region, lights), dtype=float))/1e6
            self.rooms[region.region_id] = (
                region, tuple(region_lamps[region.region_id]), sun, base)

    def _admit_work(self, region_id, n, max_points, max_shadow_tests):
        if (type(max_points) is not int or max_points <= 0 or
                type(max_shadow_tests) is not int or max_shadow_tests < 0):
            raise ValueError("explicit positive point and nonnegative shadow bounds required")
        if not 0 < n <= max_points:
            raise ValueError("bounded aligned surface-patch arrays required")
        room = self.rooms[region_id]
        region, lamps, sun, _ = room
        sources = len(lamps) + int(sun is not None)
        work = n*(2*len(self.sources.geometry.kinds)*sources +
                  (len(region.windows) if sun is not None else 0))
        if work > max_shadow_tests:
            raise ValueError("native shadow work bound exceeded")
        return room

    def bounds(self, region_id, points_eye_m, normals_eye, *,
               position_radius_m, normal_radius, receiver_rows,
               max_points, max_shadow_tests):
        """Six-band incident-light bounds over declared native surface patches.

        Position radii enclose all surface points; normal radii bound Euclidean
        differences from the supplied normalized normals. These are geometric
        integration bounds, never recognition thresholds. Return (lower, upper).
        No mutation occurs on refusal, including exhaustion of a work budget.
        """
        arrays = (points_eye_m, normals_eye, position_radius_m, normal_radius, receiver_rows)
        if not all(isinstance(a, np.ndarray) for a in arrays):
            raise ValueError("packed surface-patch arrays required before admission")
        points, normals, delta, epsilon, receiver = arrays
        if points.ndim != 2:
            raise ValueError("bounded aligned surface-patch arrays required")
        n = len(points)
        if (points.shape != (n, 3) or normals.shape != (n, 3) or
                delta.shape != (n,) or epsilon.shape != (n,) or receiver.shape != (n,)):
            raise ValueError("bounded aligned surface-patch arrays required")
        room = self._admit_work(region_id, n, max_points, max_shadow_tests)
        if (not all(np.issubdtype(a.dtype, np.floating) or np.issubdtype(a.dtype, np.integer)
                    for a in (points, normals, delta, epsilon)) or
                not all(np.isfinite(a).all() for a in (points, normals, delta, epsilon)) or
                np.any(delta < 0) or np.any(epsilon < 0) or np.any(epsilon > 2) or
                not np.issubdtype(receiver.dtype, np.integer) or
                np.any(receiver < 0) or np.any(receiver >= len(self.sources.geometry.kinds))):
            raise ValueError("finite physical surface-patch bounds required")
        return self._evaluate(room, points.astype(float, copy=False),
            normals.astype(float, copy=False), delta.astype(float, copy=False),
            epsilon.astype(float, copy=False), receiver)

    def surface_bounds(self, receiver_row, direction, angular_radius, entry_lower, entry_upper,
                       *, max_points, max_shadow_tests):
        """Consume existing aperture/depth bounds for one actual native solid.

        The caller must supply enclosures from that solid's native aperture
        geometry. This does not assert foreground visibility, integrate a
        receptor or admit simulator identities to the organism.
        """
        geometry = self.sources.geometry
        if type(receiver_row) is not int or not 0 <= receiver_row < len(geometry.kinds):
            raise ValueError("actual native receiver row required")
        arrays = (direction, angular_radius, entry_lower, entry_upper)
        if not all(isinstance(a, np.ndarray) for a in arrays) or direction.ndim != 2:
            raise ValueError("packed aperture/depth arrays required")
        n = len(direction)
        if direction.shape != (n, 3) or any(a.shape != (n,) for a in arrays[1:]):
            raise ValueError("aligned aperture/depth arrays required")
        room = self._admit_work(self.surface_regions[receiver_row], n,
                                max_points, max_shadow_tests)
        if (not all(np.issubdtype(a.dtype, np.floating) or np.issubdtype(a.dtype, np.integer)
                    for a in arrays) or not all(np.isfinite(a).all() for a in arrays)):
            raise ValueError("finite surface entry enclosure required")
        direction, angular_radius, entry_lower, entry_upper = (
            a.astype(float, copy=False) for a in arrays)
        points, normals, delta, epsilon = surface_patch_geometry(
            geometry.kinds[receiver_row], geometry.sizes_m[receiver_row],
            geometry.positions_eye_m[receiver_row], geometry.rotations_eye[receiver_row],
            direction, angular_radius, entry_lower, entry_upper)
        return self._evaluate(room, points, normals, delta, epsilon,
                              np.full(n, receiver_row, dtype=int))

    def _evaluate(self, room, points, normals, delta, epsilon, receiver):
        region, lamps, sun, base = room
        n = len(points)
        norms = np.linalg.norm(normals, axis=1)
        if np.any(norms == 0) or not np.isfinite(norms).all():
            raise ValueError("nonzero finite surface normals required")
        normals = normals / norms[:, None]
        low = np.broadcast_to(base, (n, 6)).copy()
        high = low.copy()
        for light, centre in lamps:
            vector = centre-points
            distance = np.linalg.norm(vector, axis=1)
            dmin, dmax = np.maximum(0, distance-delta), distance+delta
            direction = np.divide(vector, distance[:, None], out=np.zeros_like(vector),
                                  where=distance[:, None] != 0)
            radius = light.radius_mm/1000
            direction_error = np.minimum(2., np.divide(
                2*delta, dmin, out=np.full(n, np.inf), where=dmin > 0))
            cosine = np.sum(normals*direction, axis=1)
            factor_low = np.clip(cosine-epsilon-direction_error, 0, 1)
            factor_high = np.clip(cosine+epsilon+direction_error, 0, 1)
            factor_low[dmin <= radius] = 0
            factor_high[dmax <= radius] = 0
            # Parametric endpoint 1-radius/d varies over the patch. The common
            # prefix certifies blockage, the longest segment certifies clear.
            near = distance*np.maximum(0, 1-np.divide(
                radius, dmin, out=np.full(n, np.inf), where=dmin > 0))
            far = distance*np.maximum(0, 1-np.divide(
                radius, dmax, out=np.full(n, np.inf), where=dmax > 0))
            clear, possible = _visibility_bounds(
                self.sources.geometry, points, direction, delta, near, far, receiver)
            reference = LAMP_REFERENCE_MM/1000
            fall_low = np.minimum(LAMP_NEAR_GAIN, np.divide(
                reference**2, dmax*dmax, out=np.full(n, np.inf), where=dmax > 0))
            fall_high = np.minimum(LAMP_NEAR_GAIN, np.divide(
                reference**2, dmin*dmin, out=np.full(n, np.inf), where=dmin > 0))
            emission = np.asarray(light.ppm)/1e6
            low += (factor_low*fall_low*clear)[:, None]*emission
            high += (factor_high*fall_high*possible)[:, None]*emission
        if sun is not None:
            direction = np.broadcast_to(sun @ self.rotation, (n, 3))
            cosine = np.sum(normals*direction, axis=1)
            factor_low = np.clip(cosine-epsilon, 0, 1)
            factor_high = np.clip(cosine+epsilon, 0, 1)
            world_points = points @ self.rotation.T + self.origin
            aperture_certain = np.zeros(n, dtype=bool)
            aperture_possible = aperture_certain.copy()
            for window in region.windows:
                axis = 0 if window.wall[0] == "x" else 1
                along_axis = 1-axis
                component = sun[axis]
                if component == 0:
                    continue
                bounds = region.bounds.minimum if window.wall.endswith("min") else region.bounds.maximum
                plane = (bounds.x if axis == 0 else bounds.y)/1000
                reach = (plane-world_points[:, axis])/component
                error_t = delta/abs(component)
                along = world_points[:, along_axis] + sun[along_axis]*reach
                height = world_points[:, 2] + sun[2]*reach
                error_along = delta*np.sqrt(1+(sun[along_axis]/component)**2)
                error_height = delta*np.sqrt(1+(sun[2]/component)**2)
                certain = ((reach-error_t > 0) &
                    (along-error_along >= window.from_mm/1000) &
                    (along+error_along <= window.to_mm/1000) &
                    (height-error_height >= window.sill_mm/1000) &
                    (height+error_height <= window.top_mm/1000))
                possible = ((reach+error_t > 0) &
                    (along+error_along >= window.from_mm/1000) &
                    (along-error_along <= window.to_mm/1000) &
                    (height+error_height >= window.sill_mm/1000) &
                    (height-error_height <= window.top_mm/1000))
                aperture_certain |= certain
                aperture_possible |= possible
            # The window admits the ray, not permission to omit opaque native
            # walls or an exterior blocker. Test the whole directional ray.
            infinity = np.full(n, np.inf)
            clear, possible = _visibility_bounds(
                self.sources.geometry, points, direction, delta, infinity, infinity, receiver)
            sky = self.sources.solar_sample.sky_ppm/1e6
            low += (sky*factor_low*aperture_certain*clear)[:, None]
            high += (sky*factor_high*aperture_possible*possible)[:, None]
        if not np.isfinite(low).all() or not np.isfinite(high).all():
            raise ValueError("nonfinite illumination enclosure")
        return low, high
