"""FB-01ag standalone current-world retinal composition; no pytest/network.

Bench anatomy, illumination and applied head commands are controlled physical
inputs, not cognitive fixtures. Native point rays independently falsify optical
intervals; runtime never samples those diagnostic points.
"""
from dataclasses import replace
import resource
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.substrate.embodiment_world import (
    AnatomicalEffortCommand, EmbodimentWorldAuthority, ObjectOpticalSurface,
    PositionMM, SurfaceLookMM, PORT_ID, encode_command,
)
from dsf_ai_service.substrate.functional_body_illumination import NativeIllumination
from dsf_ai_service.substrate.functional_body_materials import PlanarMaterial
from dsf_ai_service.substrate.functional_body_optical_sources import NativeOpticalBinding
from dsf_ai_service.substrate.functional_body_optics import aperture_solid_angles
from dsf_ai_service.substrate.functional_body_renderer import directions, integrate_materials
from dsf_ai_service.substrate.functional_body_retinal import native_retinal_radiance
from dsf_ai_service.substrate.functional_body_visibility import PlanarSurface
from test_functional_body_optical_sources import KEY, INTENT, advance, declaration, mount, query, world
from tools.guala_body_optical_regime import retinal_apertures


ERROR = 1/510
BANDS = (100000, 200000, 300000, 400000, 500000, 600000)
WHITE, BLACK = (1000000,)*6, (0,)*6
RED = (800000, 700000, 100000, 100000, 200000, 200000)
GREEN = (100000, 200000, 700000, 800000, 100000, 200000)
QUAD = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))


def bench(*, lamps=True, looks=False, card_pattern=True, dark=False, card_emission=None):
    base = world()._state.world
    objects = (replace(base.objects[0], optical_surface=base.objects[0].optical_surface if card_pattern else None,
                       reflectance_ppm=BLACK if card_emission is not None else base.objects[0].reflectance_ppm,
                       emission_ppm=base.objects[0].emission_ppm if card_emission is None else card_emission),
               replace(base.objects[1], position=PositionMM(500, 2500, 0), elevation_mm=750,
                       emission_ppm=BANDS if lamps else BLACK))
    regions = base.regions
    if dark:
        regions = tuple(replace(r, illumination_ppm=BLACK, reflectance_ppm=BLACK) for r in regions)
    if looks:
        patterns = (ObjectOpticalSurface(2, 1, (RED, GREEN), (0, 1)),
                    ObjectOpticalSurface(2, 1, (GREEN, RED), (0, 1)))
        regions = (replace(regions[0], looks=(
            SurfaceLookMM("x-max", 2700, 3200, 1700, 2200, patterns[0]),
            SurfaceLookMM("x-max", 3000, 3400, 1900, 2400, patterns[1]),
        )), *regions[1:])
    auth = EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=2,
        initial_objects=objects, regions=regions)
    declared = declaration()
    root = ET.fromstring(declared.xml)
    lamp = root.find("./worldbody/body[@name='lamp']")
    lamp.set("pos", ".5 2.5 0")
    for geom, x in zip(lamp.findall("geom"), (-.1, .1)):
        geom.set("pos", f"{x} 0 .85")
    bindings = list(declared.optical_bindings)
    if looks:
        ET.SubElement(root.find("worldbody"), "geom", name="wall-xmax", type="box",
                      pos="5.005 2.5 1.5", size=".005 2.5 1.5")
        bindings.append(NativeOpticalBinding("wall-xmax", "region", "W1-region-A",
                                             region_faces=((0, -1, "x-max"),)))
    mount(auth, replace(declared, xml=ET.tostring(root, encoding="unicode"),
        optical_bindings=tuple(sorted(bindings, key=lambda b: b.geom_name))))
    return auth, objects, regions


def sites_at(source, points, half=1e-4):
    rotation = np.asarray(source.geometry.rotation_world).reshape(3, 3)
    q = (np.asarray(points)-source.geometry.origin_world_m) @ rotation
    h = np.arctan2(q[:, 1], q[:, 0])
    mu = q[:, 2]/np.linalg.norm(q, axis=1)
    return np.column_stack((h-half, h+half, mu-half, mu+half))


def draw(source, sites, **options):
    defaults = dict(max_shadow_tests=20000000, max_nodes=262144)
    defaults.update(options)
    return native_retinal_radiance(source, sites, ERROR, **defaults)


def native_rays(auth, q):
    return auth.native_ray_geometry(expected_revision=auth._state.world.revision,
        frame_name="guala/head", origin_local_m=(.08, 0., .03),
        directions_local=np.asarray(q, dtype=float), max_rays=len(q))


def ambient_reference(source, sites):
    light = NativeIllumination(source)
    base, override = [], []
    for row, material in enumerate(source.materials):
        incident = tuple(float(v) for v in light.rooms[light.surface_regions[row]][3])
        base.append(PlanarMaterial(material.reflectance_ppm, material.emission_ppm, incident))
        if material.box_pattern is not None:
            painted = replace(base[-1], pattern=material.box_pattern)
            override.extend((row, a, side, painted) for a in range(3) for side in (-1, 1))
    return integrate_materials(source.geometry, sites, tuple(base), ERROR,
        face_materials=tuple(override), max_material_cells=24)


class NativeRetinalTests(unittest.TestCase):
    def test_complete_native_ambient_field_matches_accepted_uniform_integral(self):
        auth, _, _ = bench(lamps=False)
        source = query(auth)
        before = auth.encoded_snapshot()
        sites = retinal_apertures()
        expected = ambient_reference(source, sites)
        start = time.perf_counter()
        actual = draw(source, sites)
        seconds = time.perf_counter()-start
        self.assertEqual(actual[0].shape, (19335, 6))
        self.assertTrue(np.all(np.abs(actual[0]-expected[0]) <= actual[1]+expected[1]+3e-12))
        self.assertTrue(np.all(actual[1] <= ERROR))
        self.assertEqual(before, auth.encoded_snapshot())
        print(dict(native_source_retina_sites=len(sites), seconds=seconds,
                   nodes=actual[2], depth=actual[3], max_radius=float(actual[1].max())), flush=True)

    def test_ordered_room_paint_is_clipped_without_becoming_an_occluder(self):
        auth, _, _ = bench(lamps=False, looks=True)
        source = query(auth, max_material_cells=8)
        sites = sites_at(source, ((5., 2.9, 1.9), (5., 3.1, 2.1), (5., 3.3, 2.3)), half=.045)
        actual = draw(source, sites)
        rotation = np.asarray(source.geometry.rotation_world).reshape(3, 3)
        eye = np.asarray(source.geometry.origin_world_m)
        def rect(y0, y1, z0, z1):
            return PlanarSurface.from_chart((np.array((5., y0, z0))-eye) @ rotation,
                np.array(((0., y1-y0, 0.), (0., 0., z1-z0))) @ rotation, QUAD, max_corners=4)
        first = rect(2.7, 3.2, 1.7, 2.2)
        omega = (sites[:, 1]-sites[:, 0])*(sites[:, 3]-sites[:, 2])
        room = source.regions[0]
        base = np.asarray(room.reflectance_ppm)/1e6
        incident = np.asarray(room.illumination_ppm)/1e6
        expected = np.broadcast_to(base, (len(sites), 6)).copy()
        # Independent world-coordinate rectangles for each actual 2-column paint.
        # The first physical look covers the second in their common area.
        for cell, color, behind in (
                (rect(2.7, 2.95, 1.7, 2.2), RED, False),
                (rect(2.95, 3.2, 1.7, 2.2), GREEN, False),
                (rect(3., 3.2, 1.9, 2.4), GREEN, True),
                (rect(3.2, 3.4, 1.9, 2.4), RED, True)):
            area = aperture_solid_angles(cell.halfspaces, sites, max_cells=32768)
            if behind:
                area -= aperture_solid_angles(np.vstack((first.halfspaces, cell.halfspaces)),
                                             sites, max_cells=32768)
            expected += (area/omega)[:, None]*(np.asarray(color)/1e6-base)
        expected *= incident
        # Independently verify the declared pencil has no foreground obstruction.
        hs = np.concatenate((sites[:, 0], sites[:, 1], sites[:, :2].mean(axis=1)))
        mus = np.concatenate((sites[:, 2], sites[:, 3], sites[:, 2:].mean(axis=1)))
        rays = native_rays(auth, directions(hs, mus))
        wall = auth._native_scratch.geom_names.index("wall-xmax")
        self.assertTrue(np.all(rays.geom_indices == wall))
        self.assertTrue(np.all(np.abs(actual[0]-expected) <= actual[1]+3e-12))
        self.assertTrue(np.all(actual[1] <= ERROR))

    def test_variable_light_encloses_independent_native_card_witnesses(self):
        auth, _, _ = bench(card_pattern=False)
        source = query(auth)
        sites = sites_at(source, ((1.49, .96, .96), (1.49, 1.04, 1.04)), half=2e-5)
        actual = draw(source, sites)
        light = NativeIllumination(source)
        card = auth._native_scratch.geom_names.index("card/surface")
        for i, site in enumerate(sites):
            h = np.array((site[0], site[1], (site[0]+site[1])/2))
            mu = np.array((site[2], site[3], (site[2]+site[3])/2))
            q = directions(h, mu)
            rays = native_rays(auth, q)
            self.assertTrue(np.all(rays.geom_indices == card))
            # Exact native distance, not renderer depth or a synthetic sensation.
            point = (rays.directions_world @ light.rotation)*rays.distances_m[:, None]
            normal = np.broadcast_to(np.array((-1., 0., 0.)) @ light.rotation, point.shape)
            lo, hi = light.bounds(light.surface_regions[card], point, normal,
                position_radius_m=np.zeros(3), normal_radius=np.zeros(3),
                receiver_rows=np.full(3, card, dtype=int), max_points=3, max_shadow_tests=1000000)
            np.testing.assert_array_equal(lo, hi)
            witness = lo*np.asarray(source.materials[card].reflectance_ppm)/1e6
            self.assertTrue(np.all(witness >= actual[0][i]-actual[1][i]-3e-12))
            self.assertTrue(np.all(witness <= actual[0][i]+actual[1][i]+3e-12))
        dark_auth, _, _ = bench(lamps=False, card_pattern=False)
        dark_source = query(dark_auth)
        ambient = draw(dark_source, sites)[0]
        self.assertTrue(np.any(actual[0] > ambient+actual[1]))

    def test_real_head_action_cold_image_and_next_motor_are_identical(self):
        auth, objects, regions = bench()
        source = query(auth)
        sites = sites_at(source, ((1.49, .97, 1.03), (1.49, 1.03, .97)), half=.012)
        before = draw(source, sites)
        command = AnatomicalEffortCommand((("guala/head/yaw/effort", .015),), 50000)
        prepared = auth.prepare_port_command(port_id=PORT_ID, command_payload=encode_command(command),
            expected_revision=auth._state.world.revision, causal_intent_receipt_sha256=INTENT,
            available_motor_work_j=1.)
        auth.commit_prepared_action(prepared)
        encoded = auth.encoded_snapshot()
        moved = draw(query(auth), sites)
        self.assertFalse(np.array_equal(before[0], moved[0]))
        fresh = EmbodimentWorldAuthority(authority_key=KEY, receipt_capacity=2,
            initial_objects=objects, regions=regions)
        fresh.restore_encoded(encoded)
        for a, b in zip(moved, draw(query(fresh), sites)):
            np.testing.assert_array_equal(a, b)
        self.assertEqual(auth.encoded_snapshot(), encoded)
        self.assertEqual(fresh.encoded_snapshot(), encoded)
        a, b = advance(auth, motor=True), advance(fresh, motor=True)
        self.assertEqual(a.execution_receipt, b.execution_receipt)
        auth.commit_prepared_action(a)
        fresh.commit_prepared_action(b)
        self.assertEqual(auth.encoded_snapshot(), fresh.encoded_snapshot())


    def test_actual_emissive_target_needs_no_reflection_or_shadow_work(self):
        auth, _, _ = bench(lamps=False, dark=True, card_pattern=False, card_emission=BANDS)
        source = query(auth)
        sites = sites_at(source, ((1.49, .97, 1.03), (1.49, 1.03, .97)), half=.001)
        before = auth.encoded_snapshot()
        result = draw(source, sites, max_shadow_tests=0)
        np.testing.assert_allclose(result[0], np.broadcast_to(np.asarray(BANDS)/1e6, (2, 6)),
                                   rtol=0, atol=3e-12)
        self.assertTrue(np.all(result[1] <= ERROR))
        self.assertEqual(auth.encoded_snapshot(), before)

    def test_admission_precedes_array_scans_and_scene_access(self):
        # Diagnostic refusal sentinel only; no mock bodily/learning outcome.
        class NoScan(np.ndarray):
            def __array_ufunc__(self, *args, **kwargs):
                raise AssertionError("unadmitted aperture array was scanned")
        too_many = np.empty((19336, 4), dtype=float).view(NoScan)
        with self.assertRaisesRegex(ValueError, "bounded retinal"):
            native_retinal_radiance(None, too_many, ERROR, max_shadow_tests=0)
        within_cap = np.empty((2, 4), dtype=float).view(NoScan)
        with self.assertRaisesRegex(ValueError, "node budget"):
            native_retinal_radiance(None, within_cap, ERROR, max_shadow_tests=0, max_nodes=1)
        tiny = np.nextafter(0., 1.)
        with self.assertRaisesRegex(ValueError, "representable aperture"):
            native_retinal_radiance(None, np.array(((0., tiny, 0., tiny),)), ERROR,
                                    max_shadow_tests=0)

    def test_dark_field_and_resource_refusals_preserve_world(self):
        dark, _, _ = bench(lamps=False, dark=True)
        source = query(dark)
        sites = sites_at(source, ((1.49, .96, .96),), half=.001)
        np.testing.assert_array_equal(draw(source, sites)[0], np.zeros((1, 6)))
        auth, _, _ = bench(card_pattern=False)
        source = query(auth)
        before = auth.encoded_snapshot()
        sites = sites_at(source, ((1.49, .96, .96),), half=.02)
        with self.assertRaisesRegex(ValueError, "shadow work"):
            draw(source, sites, max_shadow_tests=0)
        with self.assertRaisesRegex(ValueError, "node budget"):
            draw(source, np.repeat(sites, 2, axis=0), max_nodes=1)
        with self.assertRaisesRegex(ValueError, "depth budget"):
            draw(source, sites, max_depth=0)
        self.assertEqual(auth.encoded_snapshot(), before)


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(NativeRetinalTests))
    print(dict(native_retinal_proof_s=time.perf_counter()-started,
               peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), flush=True)
    raise SystemExit(not result.wasSuccessful())
