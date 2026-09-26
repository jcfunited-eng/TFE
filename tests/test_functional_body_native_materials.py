"""Standalone FB-01y native material/visibility proof, not a production mount.

Complete native biped geometry remains in every render. Uniform per-surface
illumination is declared; state bytes alone do not retain external materials.
Analytic checks use float64 geometry, not formal directed-rounding intervals.
"""
import math
import resource
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.substrate.embodiment_world import ObjectOpticalSurface
from dsf_ai_service.substrate.functional_body_materials import PlanarMaterial
from dsf_ai_service.substrate.functional_body_native import NativeBody
from dsf_ai_service.substrate.functional_body_optics import aperture_solid_angles
from dsf_ai_service.substrate.functional_body_renderer import integrate, integrate_materials
from dsf_ai_service.substrate.functional_body_sphere_cap import cap_solid_angles
from dsf_ai_service.substrate.functional_body_visibility import PlanarSurface
from tools.guala_body_optical_regime import (
    EYE_Z, LIMITS, ORIGIN, certify_initial_body_clear, retinal_apertures, scene,
)


BLACK = (0,) * 6
WHITE = (1_000_000,) * 6
PALETTE = (WHITE, BLACK, (200000, 300000, 400000, 500000, 600000, 700000),
           (700000, 600000, 500000, 400000, 300000, 200000))
PATTERN = ObjectOpticalSurface(2, 2, PALETTE, (0, 1, 2, 3))
QUAD = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))
ERROR = 1 / 510


def native_scene(kind="sphere"):
    xml, _ = scene(.117, None)
    root = ET.fromstring(xml)
    world = root.find("worldbody")
    world.remove(next(g for g in world.findall("geom") if g.get("name") == "emissive-panel"))
    ET.SubElement(world, "geom", name="printed-card", type="box",
                  pos=f"2.005 0 {EYE_Z}", size=".005 .6 .5")
    ET.SubElement(world, "geom", name="occluder", type=kind,
                  pos=f"1.2 .12 {EYE_Z + (.04 if kind == 'sphere' else 0)}",
                  size=".085" if kind == "sphere" else ".085 .5")
    xml = ET.tostring(root, encoding="unicode")
    return xml, NativeBody(xml, LIMITS, sensory_root="guala/pelvis")


def base_materials(engine):
    return tuple(PlanarMaterial(BLACK, BLACK, (1.,) * 6) for _ in engine.geom_names)


def geometry(engine, state):
    return engine.optical_geometry(state, "guala/head", ORIGIN, max_geoms=256)


def draw(engine, state, sites, material, *, error=ERROR, **options):
    base = base_materials(engine)
    card = engine.geom_names.index("printed-card")
    return integrate_materials(geometry(engine, state), sites, base, error,
                               face_materials=((card, 0, -1, material),),
                               max_material_cells=4, **options)


def chart(origin, axes):
    return PlanarSurface.from_chart(np.asarray(origin, dtype=np.float64),
        np.asarray(axes, dtype=np.float64), QUAD, max_corners=4)


def independent_initial_pattern(engine, state, sites, material):
    """Four physical rectangles, not renderer UV or visibility reconstruction.

    Initial body clearance is proven separately. The black sphere lies wholly
    in front of the card. Black background and non-front card faces emit zero.
    """
    certify_initial_body_clear(engine, state)
    eye = np.asarray((ORIGIN[0], 0., EYE_Z))
    sphere_centre = np.asarray((1.2, .12, EYE_Z + .04)) - eye
    omega = (sites[:, 1] - sites[:, 0]) * (sites[:, 3] - sites[:, 2])
    expected = np.zeros((len(sites), 6))
    reference_error = np.zeros_like(expected)
    for origin, color in zip(((2., -.6, EYE_Z), (2., 0., EYE_Z),
                               (2., -.6, EYE_Z-.5), (2., 0., EYE_Z-.5)), PALETTE):
        surface = chart(np.asarray(origin)-eye, ((0., .6, 0.), (0., 0., .5)))
        whole = aperture_solid_angles(surface.halfspaces, sites, max_cells=32768)
        covered, cap_error = cap_solid_angles(sphere_centre, .085, sites, surface.halfspaces)
        bands = np.asarray(color)/1_000_000 * material.incident_irradiance
        bands += np.asarray(material.emission_ppm)/1_000_000
        expected += (whole-covered)[:, None] * bands
        reference_error += cap_error[:, None] * bands
    return expected/omega[:, None], reference_error/omega[:, None]


class NativeMaterialTests(unittest.TestCase):
    def test_uniform_physical_inputs_equal_existing_operator(self):
        _, engine = native_scene()
        state = engine.initial_state()
        geom = geometry(engine, state)
        materials = tuple(PlanarMaterial(PALETTE[i % 4], PALETTE[(i+1) % 4],
                                         (2., 1., .5, .25, .125, .0625))
                          for i in range(len(engine.geom_names)))
        bands = np.asarray([np.asarray(m.reflectance_ppm)/1_000_000*m.incident_irradiance
                            + np.asarray(m.emission_ppm)/1_000_000 for m in materials])
        sites = retinal_apertures()[135::173]
        prior = integrate(geom, sites, bands, ERROR)
        typed = integrate_materials(geom, sites, materials, ERROR, max_material_cells=0)
        for a, b in zip(prior, typed):
            np.testing.assert_array_equal(a, b)

    def test_native_pattern_sphere_occlusion_against_physical_rectangles(self):
        _, engine = native_scene()
        state = engine.initial_state()
        sites = retinal_apertures()
        material = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        started = time.perf_counter()
        measured = draw(engine, state, sites, material)
        print(f"native_pattern sites={len(sites)} geoms={len(engine.geom_names)} "
              f"seconds={time.perf_counter()-started:.6f} nodes={measured[2]} "
              f"depth={measured[3]}", flush=True)
        expected, ref_error = independent_initial_pattern(engine, state, sites, material)
        self.assertTrue(np.all(np.abs(measured[0]-expected) <= measured[1]+ref_error+1e-10))
        self.assertGreater(float(expected.max()), .99)
        # A ray through the sphere must hit its physical opaque geometry.
        centre = geometry(engine, state).positions_eye_m[engine.geom_names.index("occluder")]
        hit = engine.ray_geometry(state, "guala/head", ORIGIN, centre[None, :], max_rays=1)
        self.assertEqual(int(hit.geom_indices[0]), engine.geom_names.index("occluder"))

    def test_head_motion_cold_material_input_and_next_motor_successor(self):
        xml, engine = native_scene()
        initial = engine.initial_state()
        updates = tuple(sorted((engine.actuator_names.index(name), effort) for name, effort in (
            ("guala/head/roll/effort", .02), ("guala/head/pitch/effort", .015),
            ("guala/head/yaw/effort", -.01))))
        moved = engine.advance(initial, None, 50000, 1., effort_updates=updates).state
        sites = retinal_apertures()
        material = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        images = []
        for state in (initial, moved):
            before = engine.observe(state)
            result = draw(engine, state, sites, material)
            fresh = NativeBody(xml, LIMITS, sensory_root="guala/pelvis")
            cold = draw(fresh, state, sites, material)
            repeat = draw(engine, state, sites, material)
            for a, b, c in zip(result, cold, repeat):
                np.testing.assert_array_equal(a, b)
                np.testing.assert_array_equal(a, c)
            self.assertEqual(engine.observe(state), before)
            self.assertEqual(engine.advance(state, None, 1000, 1.),
                             fresh.advance(state, None, 1000, 1.))
            images.append(result[0])
        self.assertGreater(float(np.max(np.abs(images[0]-images[1]))), 1/255)

    def test_common_rigid_world_transform_preserves_material_chart(self):
        xml, engine = native_scene()
        root = ET.fromstring(xml)
        angle = .63
        c, s = math.cos(angle), math.sin(angle)
        rotation = np.array(((c, -s, 0.), (s, c, 0.), (0., 0., 1.)))
        translation = np.asarray((.37, -.28, .09))
        for node in root.find("worldbody"):
            self.assertIn(node.tag, ("geom", "body"))
            self.assertFalse(any(key in node.attrib for key in ("quat", "euler", "axisangle")))
            point = np.fromstring(node.get("pos", "0 0 0"), sep=" ")
            node.set("pos", " ".join(str(v) for v in rotation @ point + translation))
            node.set("quat", f"{math.cos(angle/2)} 0 0 {math.sin(angle/2)}")
        transformed = NativeBody(ET.tostring(root, encoding="unicode"), LIMITS,
                                 sensory_root="guala/pelvis")
        material = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        sites = retinal_apertures()[135:]
        a = draw(engine, engine.initial_state(), sites, material)
        b = draw(transformed, transformed.initial_state(), sites, material)
        np.testing.assert_allclose(a[0], b[0], atol=1e-9, rtol=0)
        self.assertLessEqual(float(a[1].max()), ERROR)
        self.assertLessEqual(float(b[1].max()), ERROR)

    def test_dark_reflection_emission_and_no_radiance_clipping(self):
        _, engine = native_scene()
        state = engine.initial_state()
        sites = retinal_apertures()[135::157]
        dark = PlanarMaterial(WHITE, BLACK, (0.,) * 6, PATTERN)
        np.testing.assert_array_equal(draw(engine, state, sites, dark)[0], 0.)
        glow = PlanarMaterial(WHITE, PALETTE[2], (0.,) * 6, PATTERN)
        measured = draw(engine, state, sites, glow)
        expected, ref_error = independent_initial_pattern(engine, state, sites, glow)
        self.assertTrue(np.all(np.abs(measured[0]-expected) <= measured[1]+ref_error+1e-10))
        bright = PlanarMaterial(WHITE, PALETTE[2], (4., 3., 2., 1., .5, .25), PATTERN)
        measured = draw(engine, state, sites, bright)
        expected, ref_error = independent_initial_pattern(engine, state, sites, bright)
        self.assertTrue(np.all(np.abs(measured[0]-expected) <= measured[1]+ref_error+1e-10))
        self.assertGreater(float(measured[0].max()), 4.)

    def test_override_peak_bounds_unresolved_cylinder_against_analytic_shadow(self):
        _, engine = native_scene("cylinder")
        state = engine.initial_state()
        certify_initial_body_clear(engine, state)
        sites = np.array(((-.28, .28, -.08, .08),))
        split_cells = ObjectOpticalSurface(2, 2, (WHITE, BLACK), (1, 0, 1, 0))
        material = PlanarMaterial(WHITE, PALETTE[2], (4., 3., 2., 1., .5, .25), split_cells)
        result = draw(engine, state, sites, material, error=.01)
        # Vertical cylinder spans every vertical ray in this aperture. Its
        # horizontal tangent interval has exact width 2*asin(r / axial distance).
        x, y, radius = 1.2-ORIGIN[0], .12, .085
        centre, half = math.atan2(y, x), math.asin(radius/math.hypot(x, y))
        self.assertTrue(-.28 < centre-half < centre+half < .28)
        self.assertLess(math.hypot(x, y)*.08/math.sqrt(1-.08**2), .5)
        # y>=0 is white, y<0 black; both declared palette entries occur.
        # The whole cylinder silhouette lies within the white half. Emission
        # remains on both halves, and is also blocked by the opaque cylinder.
        self.assertGreater(centre-half, 0.)
        shadow = 2*half/.56
        expected = (np.asarray(material.incident_irradiance)*(.5-shadow)
                    + np.asarray(material.emission_ppm)/1e6*(1-shadow))
        self.assertGreater(float(result[4][0]), 0.)
        self.assertGreater(float(result[1].max()), 0.)
        self.assertLessEqual(float(result[1].max()), .01)
        self.assertTrue(np.all(np.abs(result[0][0]-expected) <= result[1][0]+1e-10))

    def test_finite_input_cap_composition_overflow_refuses(self):
        _, engine = native_scene()
        state = engine.initial_state()
        geom = geometry(engine, state)
        centre = geom.positions_eye_m[engine.geom_names.index("occluder")]
        h = math.atan2(centre[1], centre[0])
        mu = centre[2]/np.linalg.norm(centre)
        sites = np.array(((h-.06, h+.06, mu-.06, mu+.06),))
        # True image is the finite uniform radiance. The evaluated cap sum
        # overflows before its background subtraction; it must refuse, not
        # certify an infinite image or clamp to a representable brightness.
        bright = PlanarMaterial(WHITE, BLACK, (1e308,) * 6)
        materials = tuple(bright for _ in engine.geom_names)
        with np.errstate(over="ignore", invalid="ignore"):
            with self.assertRaisesRegex(ValueError, "numerical domain"):
                integrate_materials(geom, sites, materials, 1e307,
                                    max_material_cells=0)

    def test_hidden_bad_addresses_and_material_budget_refuse(self):
        _, engine = native_scene()
        state = engine.initial_state()
        geom = geometry(engine, state)
        card = engine.geom_names.index("printed-card")
        sphere = engine.geom_names.index("occluder")
        sites = retinal_apertures()[135::173]
        material = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        base = base_materials(engine)
        cases = (
            ((card, 0, -1, material), (card, 0, -1, material)),
            ((sphere, 0, -1, material),),
            ((card, 3, -1, material),),
            ((card, 0, 0, material),),
            ((True, 0, -1, material),),
            ((len(engine.geom_names), 0, -1, material),),
        )
        for overrides in cases:
            with self.assertRaises(ValueError):
                integrate_materials(geom, sites, base, ERROR, face_materials=overrides,
                                    max_material_cells=4)
        # Back face is invisible, but its declared storage still counts.
        with self.assertRaisesRegex(ValueError, "material cell bound"):
            integrate_materials(geom, sites, base, ERROR,
                face_materials=((card, 0, 1, material),), max_material_cells=3)
        invalid = PlanarMaterial(WHITE, BLACK, (math.inf,) * 6)
        with self.assertRaises(ValueError):
            integrate_materials(geom, sites, base, ERROR,
                face_materials=((card, 0, 1, invalid),), max_material_cells=4)
        changed = list(base)
        changed[sphere] = material
        with self.assertRaisesRegex(ValueError, "box-face chart"):
            integrate_materials(geom, sites, tuple(changed), ERROR, max_material_cells=4)
        self.assertEqual(engine.observe(state), engine.observe(engine.initial_state()))


if __name__ == "__main__":
    started = time.perf_counter()
    program = unittest.main(exit=False, verbosity=2)
    print(f"native_material_proof seconds={time.perf_counter()-started:.6f} "
          f"peak_rss_kib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}", flush=True)
    raise SystemExit(not program.result.wasSuccessful())
