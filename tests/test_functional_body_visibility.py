"""Standalone direct-constraint optics proofs, not full-body/live vision."""
import hashlib
import math
import time
import unittest
import xml.etree.ElementTree as ET

import numpy as np

from dsf_ai_service.substrate.functional_body_native import NativeBody
from dsf_ai_service.substrate.functional_body_optics import aperture_solid_angles
from dsf_ai_service.substrate.functional_body_visibility import PlanarSurface, visible_planar_regions
from tools.guala_body_optical_regime import BANDS, LIMITS, ORIGIN, retinal_apertures, scene


QUAD = np.array(((-1., -1.), (1., -1.), (1., 1.), (-1., 1.)))
BOUNDS = dict(max_halfspaces=32768, max_work=1048576, max_cells=32768)


def surface(origin, axes, uv=QUAD):
    return PlanarSurface.from_chart(np.array(origin, dtype=np.float64),
                                    np.array(axes, dtype=np.float64), uv, max_corners=16)


def panel(x, hy, hz):
    return surface((x, 0., 0.), ((0., hy, 0.), (0., 0., hz)))


def domain_of(sites):
    return np.array(((sites[:,0].min(), sites[:,1].max(), sites[:,2].min(), sites[:,3].max()),))


def radiance(surfaces, colors, sites):
    regions = visible_planar_regions(surfaces, domain_of(sites), **BOUNDS)
    image = np.zeros((len(sites), 6))
    for region in regions:
        area = aperture_solid_angles(region.halfspaces, sites, max_cells=BOUNDS['max_cells'])
        image += area[:, None] * colors[region.surface_index]
    omega = (sites[:,1]-sites[:,0])*(sites[:,3]-sites[:,2])
    return image / omega[:, None], regions


def native_surfaces(engine, state):
    """Original faces of this bench's three boxes, not a full-scene exporter.

    Native ray witnesses still include ALL geometry; no observer-body exclusion
    or alternate mechanical state. Material colors belong to the original face.
    """
    observation = engine.observe(state)
    head = next(f for f in observation.world_frames if f.name == 'guala/head')
    rotation = np.array(head.rotation_world).reshape(3, 3)
    eye = np.array(head.position_m) + rotation @ ORIGIN
    surfaces, ids, colors = [], [], []
    for name, color in (('dark-panel', np.zeros(6)), ('emissive-panel', BANDS),
                        ('occluder', BANDS[::-1].copy())):
        geom = engine.geom_names.index(name)
        size, centre = engine._model.geom_size[geom], engine._data.geom_xpos[geom]
        frame = engine._data.geom_xmat[geom].reshape(3, 3)
        eye_local = frame.T @ (eye-centre)
        for axis in range(3):
            others = [a for a in range(3) if a != axis]
            for sign in (-1, 1):
                if sign * eye_local[axis] <= size[axis]:
                    continue
                origin = (centre+frame[:,axis]*sign*size[axis]-eye) @ rotation
                axes = np.array([frame[:,a]*size[a] for a in others]) @ rotation
                surfaces.append(surface(origin, axes)); ids.append(geom); colors.append(color)
    return tuple(surfaces), ids, colors


class DirectVisibilityTests(unittest.TestCase):
    def test_area_partition_permutation_and_crossing_planes(self):
        sites = retinal_apertures()
        near, far = panel(1., .1, .1), panel(2., .8, .8)
        colors = (BANDS, BANDS[::-1].copy())
        image, _ = radiance((near, far), colors, sites)
        a = aperture_solid_angles(near.halfspaces, sites, max_cells=32768)
        b = aperture_solid_angles(far.halfspaces, sites, max_cells=32768)
        omega = (sites[:,1]-sites[:,0])*(sites[:,3]-sites[:,2])
        expected = (a[:,None]*colors[0]+(b-a)[:,None]*colors[1])/omega[:,None]
        np.testing.assert_allclose(image, expected, atol=1e-10, rtol=0)
        reverse, _ = radiance((far, near), colors[::-1], sites)
        np.testing.assert_allclose(image, reverse, atol=1e-10, rtol=0)
        # Global centre sorting cannot solve intersecting physical planes.
        left = surface((2., 0., 0.), ((.4, .8, 0.), (0., 0., .8)))
        right = surface((2., 0., 0.), ((-.4, .8, 0.), (0., 0., .8)))
        _, regions = radiance((left, right), colors, sites[135:])
        rays = np.array(((1., -.1, .03), (1., .1, .03)))
        chosen = np.full(2, -1)
        for region in regions:
            inside = np.all(rays @ region.halfspaces.T > 0, axis=1)
            self.assertTrue(np.all(chosen[inside] == -1))
            chosen[inside] = region.surface_index
        np.testing.assert_array_equal(chosen, (0, 1))

    def test_rejected_native_scene_head_motion_and_cold_successor(self):
        xml, _ = scene(.117, None)
        root = ET.fromstring(xml)
        ET.SubElement(root.find('worldbody'), 'geom', name='occluder', type='box',
                      pos='1.2 0 0.96', size='.02 .15 .15', euler='.13 -.11 .21')
        xml = ET.tostring(root, encoding='unicode')
        engine = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
        initial = engine.initial_state()
        updates = tuple(sorted((engine.actuator_names.index(name), value) for name, value in (
            ('guala/head/roll/effort', .02), ('guala/head/pitch/effort', .015),
            ('guala/head/yaw/effort', -.01))))
        moved = engine.advance(initial, None, 50000, 1., effort_updates=updates).state
        rays = np.array([(math.cos(v)*math.cos(h), math.cos(v)*math.sin(h), math.sin(v))
                         for v in np.radians(np.linspace(-10.33, 10.33, 8))
                         for h in np.radians(np.linspace(-12.37, 12.37, 10))])
        images = []
        expected_hashes = (
            "d53a40d0d3e6d26ce2785e87cc6ff7b65bfcb3c807d3b443fcbdec094dbd1373",
            "b446fa182e541c378feacf12c85deb8005498902ca09ab223e07f28da6b5a2e8",
        )
        for state, expected_hash in zip((initial, moved), expected_hashes):
            surfaces, ids, colors = native_surfaces(engine, state)
            before = engine.observe(state)
            started = time.perf_counter()
            image, regions = radiance(surfaces, colors, retinal_apertures())
            print(f'direct_visibility surfaces={len(surfaces)} regions={len(regions)} '
                  f'seconds={time.perf_counter()-started:.9f}', flush=True)
            self.assertTrue(np.isfinite(image).all())
            self.assertGreaterEqual(float(image.min()), -1e-10)
            self.assertLessEqual(float(image.max()), 1.+1e-10)
            # Exact pre-optimization numerical output, alongside independent
            # native physical witnesses below. No tolerance relaxation.
            self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(), expected_hash)
            images.append(image)
            hits = engine.ray_geometry(state, 'guala/head', ORIGIN, rays, max_rays=len(rays))
            chosen, coverage = np.full(len(rays), -1), np.zeros(len(rays), dtype=np.int64)
            for region in regions:
                inside = np.all(rays @ region.halfspaces.T > 0, axis=1)
                coverage += inside
                chosen[inside] = ids[region.surface_index]
            np.testing.assert_array_equal(coverage, 1)
            np.testing.assert_array_equal(chosen, hits.geom_indices)
            self.assertEqual(engine.observe(state), before)
            fresh = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
            cold, _, colors_cold = native_surfaces(fresh, state)
            cold_image, _ = radiance(cold, colors_cold, retinal_apertures())
            np.testing.assert_array_equal(image, cold_image)
            self.assertEqual(engine.advance(state, None, 1000, 1.), fresh.advance(state, None, 1000, 1.))
        self.assertGreater(float(np.max(np.abs(images[0]-images[1]))), 1/255)

    def test_attached_material_cells_are_not_occluders(self):
        origin, axes = np.array((2., 0., 0.)), np.array(((0., .4, 0.), (0., 0., .3)))
        base = surface(origin, axes)
        cells = (np.array(((-1.,-1.),(0.,-1.),(0.,1.),(-1.,1.))),
                 np.array(((0.,-1.),(1.,-1.),(1.,1.),(0.,1.))))
        sites = retinal_apertures()
        regions = visible_planar_regions((base, panel(1., .1, .1)), domain_of(sites), **BOUNDS)
        for region in regions:
            if region.surface_index != 0:
                continue
            all_area = aperture_solid_angles(region.halfspaces, sites, max_cells=32768)
            parts = [aperture_solid_angles(np.vstack((region.halfspaces,
                     base.material_halfspaces(c, max_corners=16))), sites, max_cells=32768) for c in cells]
            np.testing.assert_allclose(parts[0]+parts[1], all_area, atol=1e-12, rtol=0)
        # A physical marking at this exact chart coordinate remains the same
        # marking after rotating the surface. There is no view-facing remap.
        uv = np.array((.37, -.23)); point = origin + uv @ axes
        a = .23
        rotation = np.array(((math.cos(a),-math.sin(a),0.),(math.sin(a),math.cos(a),0.),(0.,0.,1.)))
        rotated = surface(origin @ rotation.T, axes @ rotation.T)
        for s, p in ((base, point), (rotated, point @ rotation.T)):
            reciprocal = s.inverse @ p
            np.testing.assert_allclose(reciprocal[1:]/reciprocal[0], uv, atol=1e-15, rtol=0)
            self.assertTrue(np.all(s.material_halfspaces(cells[1], max_corners=16) @ p >= 0))
            self.assertFalse(np.all(s.material_halfspaces(cells[0], max_corners=16) @ p >= 0))

    def test_empty_forward_crossing_coplanar_and_budget_refusal(self):
        sites = retinal_apertures(); domain = domain_of(sites)
        self.assertEqual(visible_planar_regions((panel(-2., .1, .1),), domain, **BOUNDS), ())
        crossing = surface((0.,1.,0.), ((1.,0.,0.),(0.,0.,1.)))
        self.assertTrue(visible_planar_regions((crossing,), domain, **BOUNDS))
        p = panel(2., .4, .4)
        with self.assertRaisesRegex(ValueError, 'coplanar'):
            visible_planar_regions((p,p), domain, **BOUNDS)
        for key, value in (('max_halfspaces',1),('max_work',1),('max_cells',1)):
            limits = {**BOUNDS, key:value}
            with self.assertRaises(ValueError): visible_planar_regions((p,), domain, **limits)
        with self.assertRaises(ValueError):
            surface((0.,0.,0.), ((1.,0.,0.),(0.,1.,0.)))
        with self.assertRaises(ValueError):
            surface((np.inf,0.,0.), ((1.,0.,0.),(0.,1.,0.)))
        with self.assertRaises(ValueError):
            PlanarSurface.from_chart(np.ones(3), np.ones((2,3)), QUAD, max_corners=3)
        redundant = np.array(((-1.,-1.),(0.,-1.),(1.,-1.),(1.,1.),(-1.,1.)))
        same = surface((2.,0.,0.), ((0.,.4,0.),(0.,0.,.4)), redundant)
        np.testing.assert_allclose(aperture_solid_angles(same.halfspaces, sites, max_cells=32768),
                                   aperture_solid_angles(p.halfspaces, sites, max_cells=32768), atol=1e-12, rtol=0)


if __name__ == '__main__':
    unittest.main()
