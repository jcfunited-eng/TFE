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
from dsf_ai_service.substrate.functional_body_renderer import BOX
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
