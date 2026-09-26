"""FB-01ab standalone numerical-light proof; no pytest, network or live state.

All scenes are explicitly authored isolated benches. Point samples falsify
analytic patch enclosures; they are never runtime retinal quadrature. These
proofs do not establish ordinary-loop sight or a complete production body.
"""
from dataclasses import replace
import math
import os
import resource
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority, PositionMM, WindowMM,
)
from dsf_ai_service.substrate.functional_body_illumination import NativeIllumination, _visibility_bounds
from dsf_ai_service.substrate.functional_body_native import OpticalGeometry
from dsf_ai_service.substrate.functional_body_renderer import (
    BOX, CAPSULE, CYLINDER, ELLIPSOID, SPHERE, interval, interval_pair,
    slab, sphere_interval,
)
from dsf_ai_service.substrate import functional_body_renderer as renderer
from dsf_ai_service.substrate.functional_body_illumination import _dilate
from test_functional_body_optical_sources import (
    KEY, advance, declaration, mount, query, world,
)


BANDS = (100000, 200000, 300000, 400000, 500000, 600000)


def bench(*, solar=False, closed_window=False, tilted=False, card_y=1., lamp_y=1., window_from=0):
    base = world(solar=solar)
    current = base._state.world
    objects = (replace(current.objects[0], position=PositionMM(1500, int(card_y*1000), 0)),
               replace(current.objects[1], position=PositionMM(3000, int(lamp_y*1000), 0),
                       elevation_mm=750, emission_ppm=(0,)*6 if solar else BANDS))
    regions = current.regions
    if solar:
        regions = (replace(regions[0], windows=(WindowMM("x-max", window_from, 5000, 0, 3000),)),
                   *regions[1:])
    auth = EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=2,
        initial_objects=objects, regions=regions, solar_coupling=base._solar_coupling)
    declared = declaration()
    root = ET.fromstring(declared.xml)
    lamp = root.find("./worldbody/body[@name='lamp']")
    lamp.set("pos", f"3 {lamp_y} 0")
    if tilted:
        lamp.set("quat", f"{math.sqrt(.5)} 0 {math.sqrt(.5)} 0")
    for geom, x in zip(lamp.findall("geom"), (-.1, .1)):
        geom.set("pos", f"{x} 0 .85")
    root.find("./worldbody/body[@name='card']").set("pos", f"1.5 {card_y} 0")
    if closed_window:
        root.find("./worldbody/geom[@name='wall']").set("pos", "5.005 2.5 1.5")
    mount(auth, replace(declared, xml=ET.tostring(root, encoding="unicode")))
    return auth


def bounds(field, points, normals, *, receiver="wall", delta=0., epsilon=0., **limits):
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    normals = np.broadcast_to(np.asarray(normals, dtype=float), points.shape)
    row = next(i for i, (binding, _) in enumerate(field.sources.bindings)
               if binding.geom_name == receiver)
    p = (points-field.origin) @ field.rotation
    n = normals @ field.rotation
    kwargs = dict(max_points=len(points), max_shadow_tests=1000000)
    kwargs.update(limits)
    return field.bounds("W1-region-A", p, n,
        position_radius_m=np.full(len(points), delta),
        normal_radius=np.full(len(points), epsilon),
        receiver_rows=np.full(len(points), row, dtype=int), **kwargs)


# Accepted145876ae7 interval/visibility bodies, with test-local callee names.
# The unchanged sphere/slab primitives remain shared; no runtime fallback.
def _predecessor_interval(kind, sizes, origin, velocity):
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


def _predecessor_visibility(geometry, points, direction, delta, near, far, receiver):
    certain = np.ones(len(points), dtype=bool)
    possible = certain.copy()
    for row, (kind, size, centre, rotation) in enumerate(zip(
            geometry.kinds, geometry.sizes_m, geometry.positions_eye_m,
            geometry.rotations_eye)):
        origin = (points-centre) @ rotation
        velocity = direction @ rotation
        expanded, _ = _dilate(kind, size, delta)
        lo, hi = _predecessor_interval(kind, expanded, origin, velocity)
        intersects = (lo <= hi) & (hi > 0) & (lo < far) & (far > 0)
        certain &= ~intersects | (receiver == row)
        contracted, nonempty = _dilate(kind, size, -delta)
        lo, hi = _predecessor_interval(kind, contracted, origin, velocity)
        blocks = (nonempty & (lo <= hi) & (hi > 0) & (lo < near) &
                  (near > 0) & (receiver != row))
        possible &= ~blocks
    return certain, possible


class IlluminationTests(unittest.TestCase):
    def setUp(self):
        self.old_clock = os.environ.get("GUALA_SOLAR_UTC_OVERRIDE")

    def tearDown(self):
        if self.old_clock is None:
            os.environ.pop("GUALA_SOLAR_UTC_OVERRIDE", None)
        else:
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = self.old_clock

    def test_actual_frame_inverse_square_six_bands_and_no_world_mutation(self):
        authority = bench()
        before = authority.encoded_snapshot()
        view = query(authority)
        self.assertIs(view.world_frames, authority.observation_snapshot().native.world_frames)
        self.assertIs(view.bindings, authority._native_scratch.optical_source_bindings)
        field = NativeIllumination(view)
        p = np.array((0., 3., 1.))
        lo, hi = bounds(field, p, (1., 0., 0.))
        # Independent analytic lamp law: distance sqrt(13), incidence 3/sqrt(13).
        region = view.regions[0]
        dimensions = np.array((5., 5., 3.))
        area = 2*(dimensions[0]*dimensions[1] + dimensions[0]*dimensions[2] +
                  dimensions[1]*dimensions[2])
        bounce = np.floor(np.array(BANDS)*4*math.pi*np.array(region.reflectance_ppm)/1e6/area)
        expected = (np.array(region.illumination_ppm)+bounce)/1e6 + np.array(BANDS)/1e6*3/(13**1.5)
        np.testing.assert_allclose(lo[0], expected, rtol=0, atol=2e-15)
        np.testing.assert_array_equal(lo, hi)
        back, _ = bounds(field, p, (-1., 0., 0.))
        np.testing.assert_allclose(back[0], (np.array(region.illumination_ppm)+bounce)/1e6,
                                   rtol=0, atol=2e-15)
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_native_box_shadow_and_receiver_outward_surface(self):
        authority = bench()
        field = NativeIllumination(query(authority))
        # Wall -> card -> lamp; biped is away from the y=1,z=1 optical segment
        # only the box shadow is claimed; the clear control moves the card.
        low, high = bounds(field, (0., 1., 1.), (1., 0., 0.))
        np.testing.assert_allclose(low[0], field.rooms["W1-region-A"][3], atol=2e-15)
        np.testing.assert_array_equal(low, high)
        # The card's right face must not shadow its own outgoing light.
        low, high = bounds(field, (1.51, 1., 1.), (1., 0., 0.), receiver="card/surface")
        self.assertTrue(np.all(low[0] > field.rooms["W1-region-A"][3]))
        np.testing.assert_array_equal(low, high)

    def test_positive_patch_enclosure_covers_spatial_and_normal_variation(self):
        field = NativeIllumination(query(bench()))
        centre = np.array((0., 3., 1.))
        low, high = bounds(field, centre, (1., 0., 0.), delta=.05, epsilon=.02)
        for y in (-.03, 0, .03):
            for z in (-.03, 0, .03):
                point = centre + (0., y, z)
                a, b = bounds(field, point, (1., 0., 0.))
                self.assertTrue(np.all(a >= low-2e-15))
                self.assertTrue(np.all(b <= high+2e-15))
        self.assertTrue(np.all(high > low))


    def test_curved_normal_shadow_and_window_boundary_enclosures(self):
        authority = bench(solar=True)
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "23400"
        authority.commit_prepared_action(advance(authority))
        field = NativeIllumination(query(authority))
        # Actual declared other-body sphere, not arbitrary normal perturbations.
        theta = math.pi/4
        angles = theta+np.array((-.04, -.02, 0., .02, .04))
        normals = np.column_stack((np.cos(angles), np.zeros(5), np.sin(angles)))
        central_normal = np.array((math.cos(theta), 0., math.sin(theta)))
        epsilon = np.linalg.norm(normals-central_normal, axis=1).max()
        centre = np.array((4.75, 4.75, .25))
        p0 = centre + .25*central_normal
        lo, hi = bounds(field, p0, central_normal, receiver="other/surface",
                        delta=.25*epsilon, epsilon=epsilon)
        values = []
        for normal in normals:
            a, b = bounds(field, centre+.25*normal, normal, receiver="other/surface")
            self.assertTrue(np.all(a >= lo-2e-15))
            self.assertTrue(np.all(b <= hi+2e-15))
            values.append(a[0, 0])
        self.assertGreater(max(values)-min(values), 0)

        field = NativeIllumination(query(bench(card_y=3., lamp_y=3.)))
        lo, hi = bounds(field, (0., 3.2, 1.), (1., 0., 0.), delta=.04)
        direct = []
        for y in (3.17, 3.18, 3.2, 3.22, 3.23):
            a, b = bounds(field, (0., y, 1.), (1., 0., 0.))
            self.assertTrue(np.all(a >= lo-2e-15))
            self.assertTrue(np.all(b <= hi+2e-15))
            direct.append(a[0, 0]-field.rooms["W1-region-A"][3][0])
        self.assertEqual(min(direct), 0)
        self.assertGreater(max(direct), 0)

        authority = bench(solar=True, window_from=1394)
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "23400"
        authority.commit_prepared_action(advance(authority))
        field = NativeIllumination(query(authority))
        lo, hi = bounds(field, (1.51, 1., 1.), (1., 0., 0.),
                        receiver="card/surface", delta=.03)
        direct = []
        for y in (.98, 1., 1.02):
            a, b = bounds(field, (1.51, y, 1.), (1., 0., 0.), receiver="card/surface")
            self.assertTrue(np.all(a >= lo-2e-15))
            self.assertTrue(np.all(b <= hi+2e-15))
            direct.append(a[0, 0]-field.rooms["W1-region-A"][3][0])
        self.assertEqual(min(direct), 0)
        self.assertGreater(max(direct), 0)

    def test_analytic_lamp_segment_endpoint_controls(self):
        # Independent two-solid optical bench for the pure geometric operator.
        # No source view, live state, actuator result or sensory record is forged.
        def geometry(x):
            return OpticalGeometry((0., 0., 0.), tuple(np.eye(3).ravel()),
                np.array((BOX, BOX)), np.array(((.005, 1., 1.), (.01, .1, .1))),
                np.array(((-.005, 0., 0.), (x, 0., 0.))),
                np.broadcast_to(np.eye(3), (2, 3, 3)).copy())
        point = np.zeros((1, 3))
        direction = np.array(((1., 0., 0.),))
        receiver = np.array((0,))
        for x, expected in ((2.7, False), (2.8, True)):
            certain, possible = _visibility_bounds(geometry(x), point, direction,
                np.zeros(1), np.array((2.75,)), np.array((2.75,)), receiver)
            self.assertEqual(bool(certain[0]), expected)
            self.assertEqual(bool(possible[0]), expected)
        delta = .3
        near, far = 3*(1-.25/(3-delta)), 3*(1-.25/(3+delta))
        certain, possible = _visibility_bounds(geometry(2.761), point, direction,
            np.array((delta,)), np.array((near,)), np.array((far,)), receiver)
        self.assertFalse(certain[0])
        self.assertTrue(possible[0])
        clear = []
        for y in (-.3, -.15, 0., .15, .3):
            p = np.array(((0., y, 0.),))
            vector = np.array(((3., 0., 0.),))-p
            d = np.linalg.norm(vector, axis=1)
            a, b = _visibility_bounds(geometry(2.761), p, vector/d[:, None],
                np.zeros(1), d-.25, d-.25, receiver)
            np.testing.assert_array_equal(a, b)
            self.assertTrue(np.all(a >= certain))
            self.assertTrue(np.all(b <= possible))
            clear.append(bool(a[0]))
        self.assertIn(True, clear)
        self.assertIn(False, clear)

    def test_tilted_light_uses_full_owner_frame_and_cold_restore_is_identical(self):
        authority = bench(tilted=True)
        view = query(authority)
        field = NativeIllumination(view)
        light, _ = field.rooms["W1-region-A"][1][0]
        np.testing.assert_allclose((light.x, light.y, light.z), (4000., 1000., 0.),
                                  atol=2e-12, rtol=0)
        before = authority.encoded_snapshot()
        fresh = bench(tilted=True)
        fresh.restore_encoded(before)
        restored = NativeIllumination(query(fresh))
        for a, b in zip(bounds(field, (0., 3., 1.), (1., 0., 0.)),
                        bounds(restored, (0., 3., 1.), (1., 0., 0.))):
            np.testing.assert_array_equal(a, b)
        os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "23400"
        a, b = advance(authority, motor=True), advance(fresh, motor=True)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        authority.commit_prepared_action(a)
        fresh.commit_prepared_action(b)
        self.assertEqual(authority.encoded_snapshot(), fresh.encoded_snapshot())

    def test_retained_sun_window_and_opaque_wall_not_bypassed(self):
        fields = []
        for closed in (False, True):
            authority = bench(solar=True, closed_window=closed)
            with self.assertRaisesRegex(ValueError, "retained solar"):
                NativeIllumination(query(authority))
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "23400"
            authority.commit_prepared_action(advance(authority))
            encoded = authority.encoded_snapshot()
            os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "invalid-clock"
            field = NativeIllumination(query(authority))
            # Physical x-positive face of the declared card.
            low, high = bounds(field, (1.51, 1., 1.), (1., 0., 0.),
                               receiver="card/surface")
            np.testing.assert_array_equal(low, high)
            self.assertEqual(authority.encoded_snapshot(), encoded)
            fields.append((field, low))
        clear_field, clear = fields[0]
        _, blocked = fields[1]
        self.assertTrue(np.all(clear > blocked))
        sun = clear_field.sources.solar_sample
        np.testing.assert_allclose(clear[0]-blocked[0],
            (sun.sky_ppm/1e6*sun.direction_to_sun[0],)*6, atol=2e-15, rtol=0)


    def test_shadow_frontier_is_byte_equal_to_predecessor_across_primitives(self):
        sizes = {SPHERE: (.25, 0., 0.), CAPSULE: (.15, .3, 0.),
                 CYLINDER: (.2, .3, 0.), ELLIPSOID: (.25, .15, .35),
                 BOX: (.25, .15, .35)}
        grid = np.linspace(-.6, .6, 9)
        grid_points = np.array([(0., y, z) for y in grid for z in grid])
        c, s = math.cos(.37), math.sin(.37)
        rotations = (np.eye(3), np.array(((c, -s, 0.), (s, c, 0.), (0., 0., 1.))),
                     np.array(((c, 0., s), (0., 1., 0.), (-s, 0., c))))
        for kind, size in sizes.items():
            # Genuine side/end silhouettes in each primitive's local axes,
            # including adjacent IEEE values. No authored numerical tolerance.
            side = size[0] if kind in (SPHERE, CAPSULE, CYLINDER) else size[1]
            top = (size[0] if kind == SPHERE else
                   size[0]+size[1] if kind == CAPSULE else
                   size[1] if kind == CYLINDER else size[2])
            local = []
            for axis, edge in ((1, side), (2, top)):
                for signed in (-edge, edge):
                    for value in (np.nextafter(signed, -np.inf), signed,
                                  np.nextafter(signed, np.inf)):
                        point = [-1.5, 0., 0.]
                        point[axis] = value
                        local.append(point)
            if kind == CAPSULE:
                for z in (-size[1], size[1]):
                    for y in (np.nextafter(side, -np.inf), side,
                              np.nextafter(side, np.inf)):
                        local.append((-1.5, y, z))
            for rotation in rotations:
                tangent = np.asarray(local) @ rotation.T + (1.5, 0., 0.)
                points = np.concatenate((grid_points, tangent))
                directions = np.array((3., 0., 0.))-points
                directions /= np.linalg.norm(directions, axis=1)[:, None]
                straight = np.concatenate((
                    np.broadcast_to(np.array((1., 0., 0.)), grid_points.shape),
                    np.broadcast_to(rotation[:, 0], tangent.shape)))
                n = len(points)
                geometry = OpticalGeometry((0., 0., 0.), tuple(np.eye(3).ravel()),
                    np.array((BOX, kind, BOX)), np.array(((.005, 2., 2.), size, (.01, .1, .1))),
                    np.array(((-.005, 0., 0.), (1.5, 0., 0.), (2.3, 0., 0.))),
                    np.array((np.eye(3), rotation, np.eye(3))))
                for direction in (directions, straight):
                    for radius in (0., 1e-16, .02, .4):
                        delta = np.full(n, radius)
                        outer, _ = _dilate(kind, np.asarray(size), delta)
                        inner, _ = _dilate(kind, np.asarray(size), -delta)
                        origins = (points-np.array((1.5, 0., 0.))) @ rotation
                        velocities = direction @ rotation
                        # Both existing origin layouts: per-ray and one shared
                        # origin as used by the aperture integration caller.
                        for origin in (origins, origins[0]):
                            pair = interval_pair(kind, outer, inner, origin, velocities)
                            for which, dimensions in enumerate((outer, inner)):
                                expected = _predecessor_interval(kind, dimensions, origin, velocities)
                                single = interval(kind, dimensions, origin, velocities)
                                for i in (0, 1):
                                    np.testing.assert_array_equal(pair[i][which], expected[i])
                                    np.testing.assert_array_equal(single[i], expected[i])
                        for near, far in ((0., 0.), (0., 3.), (1.5, 2.75),
                                          (2.75, 2.75), (np.inf, np.inf)):
                            args = (geometry, points, direction, np.full(n, radius),
                                    np.full(n, near), np.full(n, far), np.zeros(n, dtype=int))
                            prior = _predecessor_visibility(*args)
                            current = _visibility_bounds(*args)
                            for a, b in zip(prior, current):
                                np.testing.assert_array_equal(a, b,
                                    err_msg=f"kind={kind} radius={radius} interval={near, far}")

    def test_shared_ray_coefficients_are_computed_once_not_cached(self):
        authority = bench()
        view = query(authority)
        field = NativeIllumination(view)
        before = authority.encoded_snapshot()
        count = 512
        points_world = np.column_stack((np.zeros(count), np.linspace(2.5, 4., count),
                                       np.linspace(.2, 2.8, count)))
        points = (points_world-field.origin) @ field.rotation
        centre = field.rooms["W1-region-A"][1][0][1]
        vector = centre-points
        distance = np.linalg.norm(vector, axis=1)
        direction = vector/distance[:, None]
        receiver = np.full(count, next(i for i, (b, _) in enumerate(view.bindings)
                                     if b.geom_name == "wall"), dtype=int)
        original = renderer.sphere_interval
        examined = []
        def measured(origin, velocity, radius):
            # Each row computes the same three original ray dot products.
            examined.append(int(np.prod(np.broadcast_shapes(
                origin.shape[:-1], velocity.shape[:-1]))))
            return original(origin, velocity, radius)
        try:
            renderer.sphere_interval = measured
            globals()["sphere_interval"] = measured
            for radius in (0., .02):
                delta = np.full(count, radius)
                near = distance*(1-.25/(distance-delta))
                far = distance*(1-.25/(distance+delta))
                args = (view.geometry, points, direction, delta, near, far, receiver)
                examined.clear()
                expected = _predecessor_visibility(*args)
                prior_rows = sum(examined)
                examined.clear()
                actual = _visibility_bounds(*args)
                current_rows = sum(examined)
                for a, b in zip(expected, actual):
                    np.testing.assert_array_equal(a, b)
                self.assertLess(current_rows, prior_rows)
                print(dict(shadow_patch_radius=radius, predecessor_dot_rows=prior_rows,
                           candidate_dot_rows=current_rows), flush=True)
        finally:
            renderer.sphere_interval = original
            globals()["sphere_interval"] = original
        self.assertEqual(authority.encoded_snapshot(), before)

    def test_paired_capsule_rejects_different_segment_lengths(self):
        outer = np.array(((.4, .3, 0.),))
        inner = np.array(((.2, .2, 0.),))
        with self.assertRaisesRegex(ValueError, "equal half-lengths"):
            interval_pair(CAPSULE, outer, inner, np.array(((-2., 0., 0.),)),
                          np.array(((1., 0., 0.),)))

    def test_budget_refusal_and_bounded_repeated_read(self):
        authority = bench()
        before = authority.encoded_snapshot()
        field = NativeIllumination(query(authority))
        with self.assertRaisesRegex(ValueError, "work bound"):
            bounds(field, (0., 3., 1.), (1., 0., 0.), max_shadow_tests=0)
        with self.assertRaisesRegex(ValueError, "patch arrays"):
            bounds(field, [(0., 3., 1.)]*2, (1., 0., 0.), max_points=1)
        with self.assertRaisesRegex(ValueError, "finite physical"):
            bounds(field, (0., 3., 1.), (1., 0., 0.), delta=-1)

        class MustNotPack:
            def __array__(self, *args, **kwargs):
                raise AssertionError("rejected non-array input must not be packed")
        with self.assertRaisesRegex(ValueError, "packed surface-patch"):
            field.bounds("W1-region-A", MustNotPack(), np.ones((1, 3)),
                position_radius_m=np.zeros(1), normal_radius=np.zeros(1),
                receiver_rows=np.zeros(1, dtype=int), max_points=1, max_shadow_tests=0)
        class MustNotScan(np.ndarray):
            def __array_ufunc__(self, *args, **kwargs):
                raise AssertionError("over-bound input must not be scanned")
        with self.assertRaisesRegex(ValueError, "patch arrays"):
            field.bounds("W1-region-A", np.zeros((2, 3)).view(MustNotScan), np.ones((2, 3)),
                position_radius_m=np.zeros(2), normal_radius=np.zeros(2),
                receiver_rows=np.zeros(2, dtype=int), max_points=1, max_shadow_tests=0)
        expected = bounds(field, (0., 3., 1.), (1., 0., 0.))
        started = time.perf_counter()
        for _ in range(25):
            actual = bounds(field, (0., 3., 1.), (1., 0., 0.))
            for a, b in zip(expected, actual):
                np.testing.assert_array_equal(a, b)
        print(f"illumination repeated25_s={time.perf_counter()-started:.6f} "
              f"geoms={len(field.sources.geometry.kinds)}", flush=True)
        self.assertEqual(authority.encoded_snapshot(), before)


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(IlluminationTests))
    print(f"illumination_proof elapsed_s={time.perf_counter()-started:.6f} "
          f"peak_rss_kib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}", flush=True)
    raise SystemExit(not result.wasSuccessful())
