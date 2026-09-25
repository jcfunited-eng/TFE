"""Standalone aperture-geometry proofs; not a full renderer or live body test."""
import math
import time
import unittest

import numpy as np

from dsf_ai_service.substrate.functional_body_optics import aperture_solid_angles, surface_cone
from dsf_ai_service.substrate.functional_body_native import NativeBody
from tools.guala_body_optical_regime import (
    BANDS, CASES, LIMITS, ORIGIN, analytic_bounds, retinal_apertures, scene,
)


CELLS = 8 * 1024 * 1024 // 256  # explicit logical scratch budget, allocator peak measured separately


def visible_native_box_faces(engine, state):
    """Read exact native box/head transforms; only its disjoint front faces.

    This helper is for one convex emissive box. It must not be generalized to
    summing overlapping objects without actual visibility partitioning.
    """
    observation = engine.observe(state)
    head = next(f for f in observation.world_frames if f.name == "guala/head")
    eye_rotation = np.array(head.rotation_world).reshape(3, 3)
    eye = np.array(head.position_m) + eye_rotation @ ORIGIN
    geom = engine.geom_names.index("emissive-panel")
    m, d = engine._model, engine._data
    size = m.geom_size[geom]
    centre, rotation = d.geom_xpos[geom], d.geom_xmat[geom].reshape(3, 3)
    eye_local = rotation.T @ (eye - centre)
    faces = []
    for axis in range(3):
        others = [a for a in range(3) if a != axis]
        for sign in (-1, 1):
            if sign * eye_local[axis] <= size[axis]:
                continue
            vertices = np.zeros((4, 3))
            vertices[:, axis] = sign * size[axis]
            for j, pair in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
                vertices[j, others] = np.asarray(pair) * size[others]
            world = vertices @ rotation.T + centre
            faces.append(surface_cone((world - eye) @ eye_rotation))
    return faces


def box_light(engine, state, apertures):
    area = sum((aperture_solid_angles(n, apertures, max_cells=CELLS)
                for n in visible_native_box_faces(engine, state)), np.zeros(len(apertures)))
    total = (apertures[:, 1] - apertures[:, 0]) * (apertures[:, 3] - apertures[:, 2])
    return area[:, None] / total[:, None] * BANDS


class FunctionalBodyOpticsTests(unittest.TestCase):
    def test_full_empty_complements_and_chunk_equivalence(self):
        sites = retinal_apertures()
        omega = (sites[:, 1] - sites[:, 0]) * (sites[:, 3] - sites[:, 2])
        forward = np.array(((1., 0., 0.),))
        np.testing.assert_allclose(aperture_solid_angles(forward, sites, max_cells=CELLS), omega)
        np.testing.assert_array_equal(aperture_solid_angles(-forward, sites, max_cells=CELLS), 0.)
        for n in (np.array(((0., 1., 0.),)), np.array(((0., 0., 1.),)), np.array(((.3, -.7, .4),))):
            a = aperture_solid_angles(n, sites, max_cells=CELLS)
            b = aperture_solid_angles(-n, sites, max_cells=CELLS)
            np.testing.assert_allclose(a + b, omega, atol=1e-12, rtol=0)
            np.testing.assert_array_equal(a, aperture_solid_angles(n, sites, max_cells=128))

    def test_finite_native_edges_and_previously_missed_strip(self):
        sites = retinal_apertures()
        for kind, edge, upper in CASES:
            with self.subTest(kind=kind, edge=edge):
                xml, engine = scene(edge, upper)
                state = engine.initial_state()
                before = engine.observe(state)
                # Independent point-hit witness, not an aperture-area estimator.
                bright_h = math.radians((edge + upper) / 2 if upper is not None else edge + 1.)
                dark_h = math.radians(-1.)
                rays = np.array(((math.cos(bright_h), math.sin(bright_h), 0.),
                                 (math.cos(dark_h), math.sin(dark_h), 0.)))
                hits = engine.ray_geometry(state, "guala/head", ORIGIN, rays, max_rays=2)
                self.assertEqual(tuple(engine.geom_names[i] for i in hits.geom_indices),
                                 ("emissive-panel", "dark-panel"))
                low, high = analytic_bounds(sites, edge, upper)
                started = time.perf_counter()
                measured = box_light(engine, state, sites)
                elapsed = time.perf_counter() - started
                # One output grain even at the existing maximum16x pupil gain.
                outside = np.maximum(np.maximum(low - measured, measured - high), 0.)
                self.assertLessEqual(float(outside.max()), 1 / (255 * 16))
                self.assertTrue(np.any(measured > 0))
                if kind == "strip":
                    self.assertGreater(float(measured[135:].max()), .05)
                print(f"surface_aperture case={kind}:{edge} sites={len(sites)} "
                      f"seconds={elapsed:.9f} error_outside_reference={outside.max():.12g}", flush=True)
                self.assertEqual(engine.observe(state), before)
                fresh = NativeBody(xml, LIMITS, sensory_root="guala/pelvis")
                np.testing.assert_array_equal(measured, box_light(fresh, state, sites))

    def test_rotated_surface_area_and_winding(self):
        vertices = np.array(((2., -.2, -.1), (2., .2, -.1),
                             (2., .2, .1), (2., -.2, .1)))
        sites = retinal_apertures()
        expected = 0.
        unit = vertices / np.linalg.norm(vertices, axis=1)[:, None]
        for a, b, c in ((unit[0], unit[1], unit[2]), (unit[0], unit[2], unit[3])):
            expected += 2 * math.atan2(abs(np.dot(a, np.cross(b, c))), 1 + a @ b + b @ c + c @ a)
        for roll, pitch, yaw in ((0., 0., 0.), (.31, -.17, .12), (-.27, .14, -.09)):
            cx, sx, cy, sy, cz, sz = math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
            rotation = (np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)))
                        @ np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)))
                        @ np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx))))
            shifted = vertices @ rotation.T
            area = aperture_solid_angles(surface_cone(shifted), sites, max_cells=CELLS)
            for part in (area[:27], area[27:135], area[135:]):
                self.assertAlmostEqual(float(part.sum()), expected, places=10)
            reverse = aperture_solid_angles(surface_cone(shifted[::-1].copy()), sites, max_cells=CELLS)
            np.testing.assert_allclose(area, reverse, atol=1e-12, rtol=0)

    def test_actual_head_effort_changes_light_and_cold_continues(self):
        xml, engine = scene(.117, None)
        state = engine.initial_state()
        sites = retinal_apertures()
        before = box_light(engine, state, sites)
        updates = tuple(sorted((engine.actuator_names.index(name), value) for name, value in (
            ("guala/head/pitch/effort", .015), ("guala/head/roll/effort", .02),
            ("guala/head/yaw/effort", -.01))))
        moved = engine.advance(state, None, 50000, 1., effort_updates=updates)
        after = box_light(engine, moved.state, sites)
        self.assertGreater(float(np.max(np.abs(after - before))), 1 / 255)
        fresh = NativeBody(xml, LIMITS, sensory_root="guala/pelvis")
        np.testing.assert_array_equal(after, box_light(fresh, moved.state, sites))
        self.assertEqual(engine.advance(moved.state, None, 1000, 1.),
                         fresh.advance(moved.state, None, 1000, 1.))

    def test_invalid_domains_and_work_refusal(self):
        sites = retinal_apertures()[:1]
        normal = np.array(((1., 0., 0.),))
        for budget in (True, 0, 1):
            with self.assertRaises(ValueError):
                aperture_solid_angles(normal, sites, max_cells=budget)
        for bad in (np.zeros((1, 3)), np.full((1, 3), np.nan), np.ones((1, 2)), normal.astype(np.float32)):
            with self.assertRaises(ValueError):
                aperture_solid_angles(bad, sites, max_cells=CELLS)
        for bad in (np.array(((0., 0., -.1, .1),)), np.array(((-2., 0., -.1, .1),)),
                    np.array(((0., .1, -1., .1),)), np.full((1, 4), np.inf)):
            with self.assertRaises(ValueError):
                aperture_solid_angles(normal, bad, max_cells=CELLS)
        with self.assertRaises(ValueError):
            surface_cone(np.array(((1., 0., 0.), (2., 0., 0.), (3., 0., 0.))))
        # This concave face passes the former centroid-sided winding check.
        with self.assertRaises(ValueError):
            surface_cone(np.array(((2., -1., -1.), (2., 1., -1.),
                                   (2., -.1, 0.), (2., -1., 1.))))


if __name__ == "__main__":
    unittest.main()
