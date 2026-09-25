"""Standalone physical-chart/material proof; not a complete/live renderer."""
import math
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.substrate.embodiment_world import ObjectOpticalSurface
from dsf_ai_service.substrate.functional_body_materials import PlanarMaterial, planar_material_radiance
from dsf_ai_service.substrate.functional_body_native import NativeBody
from dsf_ai_service.substrate.functional_body_optics import aperture_solid_angles
from dsf_ai_service.substrate.functional_body_visibility import PlanarSurface, visible_planar_regions
from tools.guala_body_optical_regime import LIMITS, ORIGIN, retinal_apertures, scene


QUAD = np.array(((0., 0.), (1., 0.), (1., 1.), (0., 1.)))
BLACK = (0,) * 6
WHITE = (1_000_000,) * 6
PALETTE = (WHITE, BLACK, (200000, 300000, 400000, 500000, 600000, 700000),
           (700000, 600000, 500000, 400000, 300000, 200000))
PATTERN = ObjectOpticalSurface(2, 2, PALETTE, (0, 1, 2, 3))
BOUNDS = dict(max_sites=19335, max_material_cells=4096, max_halfspaces=32768,
              max_work=1048576, max_cells=32768)


def face(origin, axes):
    return PlanarSurface.from_chart(np.asarray(origin, dtype=np.float64),
                                    np.asarray(axes, dtype=np.float64), QUAD, max_corners=4)


def render(surfaces, materials, sites, **overrides):
    return planar_material_radiance(surfaces, materials, sites, **{**BOUNDS, **overrides})


def native_faces(engine, state):
    """This bench's native boxes only; complete curved-world optics is unproved."""
    geometry = engine.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
    surfaces, materials, ids = [], [], []
    for name, pattern, paint in (('dark-panel', None, BLACK),
                                 ('emissive-panel', PATTERN, WHITE),
                                 ('occluder', None, BLACK)):
        index = engine.geom_names.index(name)
        size = geometry.sizes_m[index]
        centre, rotation = geometry.positions_eye_m[index], geometry.rotations_eye[index]
        eye = rotation.T @ -centre
        for axis in range(3):
            others = [a for a in range(3) if a != axis]
            for sign in (-1, 1):
                if sign * eye[axis] <= size[axis]:
                    continue
                axes = np.array([rotation[:, a] * (2 * size[a]) for a in others])
                origin = centre + rotation[:, axis] * sign * size[axis] - axes.sum(axis=0) / 2
                surfaces.append(face(origin, axes))
                materials.append(PlanarMaterial(paint, BLACK, (1.,) * 6, pattern))
                ids.append(index)
    return tuple(surfaces), tuple(materials), ids


class PhysicalMaterialTests(unittest.TestCase):
    def test_actual_palette_partition_and_dark_emission(self):
        surface = face((2., -.5, -.5), ((0., 1., 0.), (0., 0., 1.)))
        sites = retinal_apertures()[135:]
        omega = (sites[:, 1] - sites[:, 0]) * (sites[:, 3] - sites[:, 2])
        expected = np.zeros((len(sites), 6))
        # Independent physical locations of the four 0.5m square markings.
        for origin, color in zip(((2., -.5, 0.), (2., 0., 0.),
                                   (2., -.5, -.5), (2., 0., -.5)), PALETTE):
            part = face(origin, ((0., .5, 0.), (0., 0., .5)))
            area = aperture_solid_angles(part.halfspaces, sites, max_cells=32768)
            expected += area[:, None] * np.asarray(color)[None, :] / 1_000_000
        expected /= omega[:, None]
        material = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        measured = render((surface,), (material,), sites)
        np.testing.assert_allclose(measured, expected, atol=1e-10, rtol=0)
        dark = PlanarMaterial(WHITE, BLACK, (0.,) * 6, PATTERN)
        np.testing.assert_array_equal(render((surface,), (dark,), sites), 0.)
        glowing = PlanarMaterial(WHITE, PALETTE[2], (0.,) * 6, PATTERN)
        coverage = aperture_solid_angles(surface.halfspaces, sites, max_cells=32768) / omega
        np.testing.assert_allclose(render((surface,), (glowing,), sites),
            coverage[:, None] * np.asarray(PALETTE[2])[None, :] / 1_000_000, atol=1e-10, rtol=0)

    def test_occluder_blocks_real_pattern_and_subdivision_is_not_resampling(self):
        source = face((2., -.5, -.5), ((0., 1., 0.), (0., 0., 1.)))
        cover = face((1., -.25, -.25), ((0., .5, 0.), (0., 0., .5)))
        sites = retinal_apertures()[135:]
        patterned = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        dark = PlanarMaterial(BLACK, BLACK, (1.,) * 6)
        np.testing.assert_allclose(render((source, cover), (patterned, dark), sites), 0., atol=1e-10)
        # Same physical paint boundary, represented by twice as many columns.
        refined = ObjectOpticalSurface(4, 2, PALETTE, (0, 0, 1, 1, 2, 2, 3, 3))
        repeated = PlanarMaterial(WHITE, BLACK, (1.,) * 6, refined)
        np.testing.assert_array_equal(render((source,), (patterned,), sites),
                                      render((source,), (repeated,), sites))

    def test_native_head_movement_material_coordinates_and_cold_successor(self):
        xml, _ = scene(.117, None)
        root = ET.fromstring(xml)
        ET.SubElement(root.find('worldbody'), 'geom', name='occluder', type='box',
                      pos='1.2 0 0.96', size='.02 .15 .15', euler='.13 -.11 .21')
        xml = ET.tostring(root, encoding='unicode')
        engine = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
        initial = engine.initial_state()
        updates = tuple(sorted((engine.actuator_names.index(name), effort) for name, effort in (
            ('guala/head/roll/effort', .02), ('guala/head/pitch/effort', .015),
            ('guala/head/yaw/effort', -.01))))
        moved = engine.advance(initial, None, 50000, 1., effort_updates=updates).state
        sites = retinal_apertures()[135:]
        rays = np.array([(math.cos(v) * math.cos(h), math.cos(v) * math.sin(h), math.sin(v))
                         for v in np.radians(np.linspace(-10.33, 10.33, 8))
                         for h in np.radians(np.linspace(-12.37, 12.37, 10))])
        images = []
        for state in (initial, moved):
            surfaces, materials, ids = native_faces(engine, state)
            before = engine.observe(state)
            started = time.perf_counter()
            image = render(surfaces, materials, sites)
            print(f'native_material_frame surfaces={len(surfaces)} sites={len(sites)} '
                  f'seconds={time.perf_counter()-started}', flush=True)
            images.append(image)
            hits = engine.ray_geometry(state, 'guala/head', ORIGIN, rays, max_rays=len(rays))
            domain = np.array(((sites[:,0].min(), sites[:,1].max(), sites[:,2].min(), sites[:,3].max()),))
            regions = visible_planar_regions(surfaces, domain, max_halfspaces=32768,
                                             max_work=1048576, max_cells=32768)
            selected = np.full(len(rays), -1)
            for region in regions:
                inside = np.all(rays @ region.halfspaces.T > 0, axis=1)
                self.assertTrue(np.all(selected[inside] == -1))
                selected[inside] = ids[region.surface_index]
            np.testing.assert_array_equal(selected, hits.geom_indices)
            self.assertEqual(engine.observe(state), before)
            fresh = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
            cold_surfaces, cold_materials, _ = native_faces(fresh, state)
            np.testing.assert_array_equal(render(cold_surfaces, cold_materials, sites), image)
            self.assertEqual(engine.advance(state, None, 1000, 1.), fresh.advance(state, None, 1000, 1.))
        self.assertGreater(np.max(np.abs(images[0] - images[1])), 1/255)

    def test_invalid_material_chart_and_explicit_resource_bounds(self):
        sites = retinal_apertures()[135:]
        source = face((2., -.5, -.5), ((0., 1., 0.), (0., 0., 1.)))
        material = PlanarMaterial(WHITE, BLACK, (1.,) * 6, PATTERN)
        for limits in ({'max_sites': 1}, {'max_material_cells': 3},
                       {'max_halfspaces': 1}, {'max_work': 1}, {'max_cells': 1}):
            with self.assertRaises(ValueError):
                render((source,), (material,), sites, **limits)
        invalid = PlanarMaterial(WHITE, BLACK, (math.nan,) * 6, PATTERN)
        with self.assertRaises(ValueError):
            render((source,), (invalid,), sites)
        triangle = PlanarSurface.from_chart(np.array((2., -.5, -.5)),
            np.array(((0.,1.,0.), (0.,0.,1.))), np.array(((0.,0.), (1.,0.), (0.,1.))), max_corners=3)
        with self.assertRaisesRegex(ValueError, 'unit rectangular chart'):
            render((triangle,), (material,), sites)


if __name__ == '__main__':
    unittest.main()
