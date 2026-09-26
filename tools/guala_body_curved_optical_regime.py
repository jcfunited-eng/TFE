#!/usr/bin/env python3
"""Offline native optical proof. Rendering law lives only in substrate modules."""
from __future__ import annotations

import json
import math
import os
import resource
import subprocess
import time
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_native import NativeBody
from dsf_ai_service.substrate.functional_body_renderer import (
    SPHERE, CAPSULE, ELLIPSOID, CYLINDER, BOX, KINDS, directions,
    patch_geometry, entry_bounds, validate_geometry, integrate,
)
from dsf_ai_service.substrate.functional_body_sphere_cap import cap_solid_angles
from tools.guala_body_optical_regime import (
    LIMITS, ORIGIN, EYE_Z, BANDS, retinal_apertures, scene,
)

def witness(geometry, patches):
    """Sample only for falsification; a finite grid never proves an enclosure."""
    prepared = patch_geometry(patches)
    count = 0
    for kind, size, centre, rotation in zip(geometry.kinds, geometry.sizes_m,
                                          geometry.positions_eye_m, geometry.rotations_eye):
        lower, upper = entry_bounds(kind, size, centre, rotation, patches, prepared)
        for fi in (0., .25, .5, .75, 1.):
            for fj in (0., .25, .5, .75, 1.):
                rays = directions(patches[:,0]+fi*(patches[:,1]-patches[:,0]),
                                  patches[:,2]+fj*(patches[:,3]-patches[:,2]))
                for index, ray in enumerate(rays):
                    native = mj.mju_rayGeom(centre, rotation.ravel(), size, np.zeros(3), ray, int(kind))
                    if native >= 0:
                        assert lower[index] <= native+1e-10, (kind, 'lower', lower[index], native)
                        if np.isfinite(upper[index]):
                            assert native <= upper[index]+1e-10, (kind, 'upper', native, upper[index])
                    else:
                        assert not np.isfinite(upper[index]), (kind, 'false all-hit', upper[index])
                    count += 1
    return count


def one_geometry(kind, size, centre, angle):
    c, s = math.cos(angle), math.sin(angle)
    rotation = np.array(((c, 0., s), (0., 1., 0.), (-s, 0., c)))
    return SimpleNamespace(kinds=np.array((kind,)), sizes_m=np.array((size,)),
                           positions_eye_m=np.array((centre,)), rotations_eye=np.array((rotation,)))


def native_panel_bounds(geometry, index, apertures):
    """Independent initial-bench silhouette from actual compiled box extents.

    The huge finite panel loses picometres at centre-minus-halfsize. Using
    its ideal pre-compilation edge instead compares two different scenes.
    This reference uses corner angles, not the renderer's face-chart solver.
    Outside the conservative vertical support, coverage remains an interval.
    It is float64 geometry, not directed-rounding interval arithmetic.
    """
    assert geometry.kinds[index] == BOX
    np.testing.assert_array_equal(geometry.rotations_eye[index], np.eye(3))
    low = geometry.positions_eye_m[index] - geometry.sizes_m[index]
    high = geometry.positions_eye_m[index] + geometry.sizes_m[index]
    near, far = low[0], high[0]
    vertical = min(-low[2], high[2])
    assert 0 < near < far < vertical
    assert np.all(np.abs(apertures[:, 2:]) <= math.sqrt(.5))
    corners = [math.atan2(y, x) for x in (near, far) for y in (low[1], high[1])]
    lo, hi = min(corners), max(corners)
    hlo, hhi = apertures[:, 0], apertures[:, 1]
    coverage = np.maximum(0., np.minimum(hhi, hi) - np.maximum(hlo, lo)) / (hhi-hlo)
    safe_h = math.acos(far/vertical)
    certain = np.maximum(0., np.minimum(hhi, min(hi, safe_h))
                         - np.maximum(hlo, max(lo, -safe_h))) / (hhi-hlo)
    return certain[:, None]*BANDS, coverage[:, None]*BANDS


def main():
    started = time.perf_counter()
    print(json.dumps({'pid': os.getpid(), 'kind': 'offline float64 regime, not formal certified optics'}), flush=True)
    sites = retinal_apertures()
    size_by_kind = {SPHERE: (.07, 0., 0.), CAPSULE: (.025, .12, 0.),
                   ELLIPSOID: (.12, .03, .07), CYLINDER: (.04, .12, 0.), BOX: (.03, .07, .12)}
    witnessed = 0
    for kind in KINDS:
        for distance in (.16, .7, 3.):
            for angle in (0., .6, 1.4):
                geometry = one_geometry(kind, size_by_kind[kind], (distance, .031, .014), angle)
                validate_geometry(geometry)
                witnessed += witness(geometry, sites[135::613])
    print(json.dumps({'native_sampled_ray_witnesses': witnessed, 'enclosure_discrepancies': 0}), flush=True)
    # Analytic cap: axis-centred sphere subtends Omega=2*pi*(1-sqrt(1-r^2/d^2)).
    # Integrating one enclosing rectangle checks aperture bounds independently.
    cap = one_geometry(SPHERE, (.07, 0., 0.), (.7, 0., 0.), 0.)
    aperture = np.array(((-.2, .2, -.2, .2),))
    image, uncertainty, nodes, depth, _ = integrate(cap, aperture, np.ones((1,6)), 1/510)
    expected = 2*math.pi*(1-math.sqrt(1-.1**2)) / .16
    assert abs(image[0,0]-expected) <= uncertainty[0,0]+1e-12
    print(json.dumps({'analytic_sphere': expected, 'measured': image[0,0],
                      'absolute_bound': uncertainty[0,0], 'nodes': nodes, 'depth': depth}), flush=True)
    # Localized source-review boundaries: malformed roster/budget/zero area
    # must refuse instead of changing the apparent physical image.
    invalid = one_geometry(SPHERE, (.07, 0., 0.), (.7, 0., 0.), 0.)
    invalid.positions_eye_m = np.empty((0, 3))
    cases = ((invalid, aperture, {}),
             (cap, aperture, {'max_nodes': 1.5}),
             (cap, aperture, {'max_depth': -1}),
             (cap, np.array(((0., 1e-200, 0., 1e-200),)), {}),
             (one_geometry(SPHERE, (1e-20,0.,0.), (1.,0.,0.), 0.), aperture, {}),
             (one_geometry(SPHERE, (1.,0.,0.), (1e200,0.,0.), 0.), aperture, {}))
    for geom, bounds, limits in cases:
        try:
            integrate(geom, bounds, np.ones((1, 6)), 1/510, **limits)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid numerical/geometry request admitted')
    print(json.dumps({'admission_refusals': len(cases)}), flush=True)
    # Off-centre sub-aperture cap: translation in longitude preserves dOmega.
    tiny = one_geometry(SPHERE, (.0004, 0., 0.), (.7*math.cos(.041), .7*math.sin(.041), 0.), 0.)
    tiny_aperture = np.array(((.038, .044, -.003, .003),))
    tiny_image, tiny_error, tiny_nodes, _, _ = integrate(tiny, tiny_aperture, np.ones((1, 6)), 1/510)
    ratio = .0004/.7
    # Stable form of 1-sqrt(1-ratio^2).
    tiny_expected = 2*math.pi*ratio**2/(1+math.sqrt(1-ratio**2)) / (.006*.006)
    assert abs(tiny_image[0,0]-tiny_expected) <= tiny_error[0,0]+1e-12
    print(json.dumps({'off_centre_subaperture_cap': tiny_expected,
                      'measured': tiny_image[0,0], 'bound': tiny_error[0,0],
                      'nodes': tiny_nodes}), flush=True)
    # Independent whole/half-cap and partition laws; no image-derived answers.
    aperture = np.array(((-.3,.3,-.3,.3),))
    checks = 0
    for centre, radius in ((np.array((.7,0.,0.)),.07),
                           (np.array((.7,.05,.04)),.07),
                           (np.array((.7,.0287,0.)),.0004)):
        ratio = radius/np.linalg.norm(centre)
        expected = 2*math.pi*ratio**2/(1+math.sqrt(1-ratio**2))
        whole, whole_error = cap_solid_angles(centre, radius, aperture, np.empty((0,3)))
        assert abs(whole[0]-expected) <= whole_error[0]+1e-12
        plane = np.cross(centre, np.array((0.,0.,1.)))[None,:]
        half, half_error = cap_solid_angles(centre, radius, aperture, plane)
        assert abs(2*half[0]-expected) <= 2*half_error[0]+1e-12
        mid = math.atan2(centre[1],centre[0])
        split = np.array(((-.3,mid,-.3,.3),(mid,.3,-.3,.3)))
        pieces, pieces_error = cap_solid_angles(centre, radius, split, np.empty((0,3)))
        assert abs(float(pieces.sum())-expected) <= float(pieces_error.sum())+1e-12
        checks += 3
    print(json.dumps({'analytic_cap_laws':checks}), flush=True)
    # Real full finite roster, including all self surfaces; no plane removal.
    base_xml, _ = scene(.117, None)
    for scene_label in ('original', 'curved_foreground'):
        root = ET.fromstring(base_xml)
        if scene_label == 'curved_foreground':
            ET.SubElement(root.find('worldbody'), 'geom', name='curved-foreground', type='sphere',
                          pos=f'.8 .07 {EYE_Z}', size='.07')
            ET.SubElement(root.find('worldbody'), 'geom', name='small-foreground', type='sphere',
                          pos=f'.8 -.13 {EYE_Z+.07}', size='.0004')
        xml = ET.tostring(root, encoding='unicode')
        engine = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
        initial = engine.initial_state()
        effort = ((engine.actuator_names.index('guala/head/yaw/effort'), .01),)
        moved = engine.advance(initial, None, 50000, 1., effort_updates=effort).state
        for label, state in (('initial', initial), ('moved', moved)):
            geometry = engine.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
            validate_geometry(geometry)
            radiance = np.ones((len(geometry.kinds),6))
            radiance[engine.geom_names.index('dark-panel')] = 0.
            radiance[engine.geom_names.index('emissive-panel')] = BANDS
            if scene_label == 'curved_foreground':
                radiance[engine.geom_names.index('curved-foreground')] = (.1, .3, .5, .7, .9, 1.)
                radiance[engine.geom_names.index('small-foreground')] = (.9, .7, .5, .3, .1, 0.)
                for name in ('curved-foreground', 'small-foreground'):
                    # Authentic native point witness, not an aperture certificate.
                    index = engine.geom_names.index(name)
                    ray = geometry.positions_eye_m[index:index+1].copy()
                    observed = engine.ray_geometry(state, 'guala/head', ORIGIN, ray, max_rays=1)
                    assert observed.geom_indices[0] == index
            before = engine.observe(state)
            begin = time.perf_counter()
            try:
                image, uncertainty, nodes, depth, residual_area = integrate(geometry, sites, radiance, 1/510)
            except ValueError as exc:
                result = {'status': 'refused', 'reason': str(exc)}
            else:
                elapsed = time.perf_counter()-begin
                if scene_label == 'original' and label == 'initial':
                    lower, upper = native_panel_bounds(
                        geometry, engine.geom_names.index('emissive-panel'), sites)
                    assert np.all(image-uncertainty <= upper+1e-10)
                    assert np.all(image+uncertainty >= lower-1e-10)
                if scene_label == 'curved_foreground' and label == 'initial':
                    old_source = subprocess.check_output(
                        ['git','show','dc769bbcd:tools/guala_body_curved_optical_regime.py'], text=True)
                    old = {'__name__':'reviewed_predecessor'}
                    exec(compile(old_source,'<reviewed predecessor dc769bbcd>','exec'),old)
                    prior, prior_error, _, _ = old['integrate'](geometry, sites, radiance, 1/510)
                    nested = np.all((image-uncertainty >= prior-prior_error-1e-10)
                                    & (image+uncertainty <= prior+prior_error+1e-10),axis=1)
                    assert np.all(nested[residual_area == 0]), 'analytic result outside predecessor interval'
                    mixed = np.flatnonzero(~nested & (residual_area > 0))
                    if len(mixed):
                        # Independently stopped adaptive bounds need not nest.
                        # Resolve only the non-nested mixed roots against a
                        # 16x finer predecessor, with the SAME work ceilings.
                        reference, reference_error, _, _ = old['integrate'](
                            geometry, sites[mixed], radiance, (1/510)/16)
                        assert np.all(reference-reference_error >= image[mixed]-uncertainty[mixed]-1e-10), 'mixed reference inconclusive'
                        assert np.all(reference+reference_error <= image[mixed]+uncertainty[mixed]+1e-10), 'mixed reference inconclusive'
                    print(json.dumps({'analytic_predecessor_containment':'passed',
                                      'mixed_independent_reference_roots':len(mixed)}),flush=True)
                fresh = NativeBody(xml, LIMITS, sensory_root='guala/pelvis')
                cold = fresh.optical_geometry(state, 'guala/head', ORIGIN, max_geoms=256)
                second = integrate(cold, sites, radiance, 1/510)
                np.testing.assert_array_equal(image, second[0])
                np.testing.assert_array_equal(uncertainty, second[1])
                np.testing.assert_array_equal(residual_area, second[4])
                assert engine.advance(state, None, 1000, 1.) == fresh.advance(state, None, 1000, 1.)
                result = {'status': 'bounded', 'nodes': nodes, 'depth': depth,
                          'frame_seconds': elapsed, 'max_absolute_bound': float(uncertainty.max())}
            assert engine.observe(state) == before
            print(json.dumps({'scene': scene_label, 'pose': label, 'geoms': len(geometry.kinds),
                              'sites': len(sites),
                              'seconds_including_cold_and_reference': time.perf_counter()-begin,
                              **result}), flush=True)
    print(json.dumps({'seconds': time.perf_counter()-started,
                      'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}), flush=True)


if __name__ == '__main__':
    main()
