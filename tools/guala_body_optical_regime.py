#!/usr/bin/env python3
"""Offline aperture-error measurement, NOT Guala's production renderer.

Actual native opaque geometry with fixed six-band emissive surfaces. The
analytic edge/strip integral is independent of the numerical ray quadrature.
No inferred recognition, material IDs in cognition, live world, or network.
Print bounded JSON rows to stdout; retain no frame/history files.
"""
from __future__ import annotations

import ast
import json
import math
import os
from pathlib import Path
import resource
import time
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_anatomy import append_reference_biped
from dsf_ai_service.substrate.functional_body_native import MechanicalLimits, NativeBody


LIMITS = MechanicalLimits(1000, 250, .008, .03, .005, .015)
# Diagnostic optical point only: 1mm outside the reference head's .07m sphere
# at its centre height .03m. Not a production anatomical mounting decision.
ORIGIN = (.071, 0., .03)
EYE_Z = .54 + .09 + .30 + ORIGIN[2]
PLANE_X = 2.
EXTENT_M = 100_000.
BANDS = np.array((1., .8, .6, .4, .2, .1), dtype=np.float64)
LOGICAL_BATCH_BYTES = 8 * 1024 * 1024
LOGICAL_BYTES_PER_RAY = 256
MAX_BATCH_RAYS = LOGICAL_BATCH_BYTES // LOGICAL_BYTES_PER_RAY
COUNTS = (1, 2, 4, 8, 16, 32, 64, 128)
CASES = (("edge", .117, None), ("edge", .499, None),
         ("edge", 4.999, None), ("strip", .02, .04))


def retinal_apertures():
    """Read-only check of declared grid, without importing its world closure.

    This bench intentionally has no authority to update receptor anatomy.
    Fail if the inspected upstream declarations differ from this measurement.
    """
    path = Path(__file__).resolve().parents[1] / "dsf_ai_service/substrate/w1_physical_receptors.py"
    nodes = {n.targets[0].id: n.value for n in ast.parse(path.read_text()).body
             if isinstance(n, ast.Assign) and len(n.targets) == 1
             and isinstance(n.targets[0], ast.Name)}
    expected = {
        "RETINA_ROWS": "3", "RETINA_COLUMNS": "9",
        "RETINA_FINE_ROWS": "6", "RETINA_FINE_COLUMNS": "18",
        "RETINA_HORIZONTAL_FOV_MILLIDEGREES": "180000",
        "RETINA_VERTICAL_FOV_MILLIDEGREES": "90000",
        "RETINA_FOCAL_ROWS": "120", "RETINA_FOCAL_COLUMNS": "160",
        "RETINA_FOCAL_PITCH_MILLIDEGREES": "Fraction(375)",
    }
    for name, expression in expected.items():
        if name not in nodes or ast.dump(nodes[name]) != ast.dump(ast.parse(expression, mode="eval").body):
            raise ValueError(f"retinal declaration changed: {name}")
    apertures = []
    for rows, columns, hfov, vfov in ((3, 9, 180., 90.), (6, 18, 180., 90.),
                                     (120, 160, 60., 45.)):
        for row in range(rows):
            vlo, vhi = vfov / 2 - (row + 1) * vfov / rows, vfov / 2 - row * vfov / rows
            for column in range(columns):
                hlo = -hfov / 2 + column * hfov / columns
                hhi = -hfov / 2 + (column + 1) * hfov / columns
                apertures.append((math.radians(hlo), math.radians(hhi),
                                  math.sin(math.radians(vlo)), math.sin(math.radians(vhi))))
    return np.array(apertures, dtype=np.float64)


def scene(edge_degrees, upper_degrees):
    root = ET.fromstring('''<mujoco model="optical-aperture-regime">
      <compiler angle="radian" inertiafromgeom="true"/>
      <size memory="8M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
      <default><geom friction="0.6 0.002 0.0001" solref="0.01 1"
        solimp="0.95 0.99 0.001"/></default>
      <worldbody/><actuator/><sensor/>
    </mujoco>''')
    world = root.find("worldbody")
    ET.SubElement(world, "geom", name="dark-panel", type="box",
                  pos=f"{PLANE_X + .03} 0 {EYE_Z}", size=f".01 {EXTENT_M} {EXTENT_M}")
    distance = PLANE_X - ORIGIN[0]
    lo = distance * math.tan(math.radians(edge_degrees))
    hi = EXTENT_M if upper_degrees is None else distance * math.tan(math.radians(upper_degrees))
    ET.SubElement(world, "geom", name="emissive-panel", type="box",
                  pos=f"{PLANE_X + .005} {(lo + hi) / 2} {EYE_Z}",
                  size=f".005 {(hi - lo) / 2} {EXTENT_M}")
    append_reference_biped(world, root.find("actuator"), root.find("sensor"),
                           root_position_m=(0., 0., .54))
    xml = ET.tostring(root, encoding="unicode")
    return xml, NativeBody(xml, LIMITS, sensory_root="guala/pelvis")


def sample(engine, state, apertures, counts):
    """Solid-angle midpoint quadrature in bounded chunks on actual native hits.

    h and mu=sin(v) give dOmega=dh*dmu; all samples of one site have equal
    measure. Chunking changes neither locations nor sum order within a site.
    Material is fixed to a surface, not a viewer-facing image/chart.
    """
    if len(counts) != len(apertures) or any(type(n) is not int or n not in COUNTS for n in counts):
        raise ValueError("finite declared sample schedule required")
    count_array = np.array(counts, dtype=np.int64)
    squared = count_array ** 2
    ends = np.cumsum(squared)
    starts = ends - squared
    energy = np.zeros(len(apertures), dtype=np.int64)
    bright = engine.geom_names.index("emissive-panel")
    dark = engine.geom_names.index("dark-panel")
    calls = 0
    unexpected = 0
    started = time.perf_counter()
    for begin in range(0, int(ends[-1]), MAX_BATCH_RAYS):
        serial = np.arange(begin, min(begin + MAX_BATCH_RAYS, int(ends[-1])))
        sites = np.searchsorted(ends, serial, side="right")
        n = count_array[sites]
        within = serial - starts[sites]
        bounds = apertures[sites]
        h = bounds[:, 0] + ((within % n + .5) / n) * (bounds[:, 1] - bounds[:, 0])
        mu = bounds[:, 2] + ((within // n + .5) / n) * (bounds[:, 3] - bounds[:, 2])
        cv = np.sqrt(1 - mu * mu)
        directions = np.stack((cv * np.cos(h), cv * np.sin(h), mu), axis=1)
        rays = engine.ray_geometry(state, "guala/head", ORIGIN, directions,
                                   max_rays=MAX_BATCH_RAYS)
        np.add.at(energy, sites, (rays.geom_indices == bright).astype(np.int64))
        unexpected += int(np.count_nonzero((rays.geom_indices != bright) & (rays.geom_indices != dark)))
        calls += 1
    return energy[:, None] / squared[:, None] * BANDS, {
        "seconds": time.perf_counter() - started, "rays": int(ends[-1]),
        "native_calls": calls, "non_panel_hits": unexpected,
    }


def analytic_bounds(apertures, edge, upper):
    """Finite box silhouette; separate the bounded far-z aperture sliver.

    All front/back corners contribute to horizontal angular support. Outside
    |h| <= acos(d_far / EXTENT_M), a ray with |v|<=45deg may leave the finite
    vertical face. That small interval is reported as uncertain, not silently
    integrated as an infinite panel. Bounds use float64 analytic evaluation,
    not formal directed-rounding interval arithmetic.
    """
    near = PLANE_X - ORIGIN[0]
    far = near + .01
    ylo = near * math.tan(math.radians(edge))
    yhi = EXTENT_M if upper is None else near * math.tan(math.radians(upper))
    corners = [math.atan2(y, x) for x in (near, far) for y in (ylo, yhi)]
    lo, hi = min(corners), max(corners)
    hlo, hhi = apertures[:, 0], apertures[:, 1]
    coverage = np.maximum(0., np.minimum(hhi, hi) - np.maximum(hlo, lo)) / (hhi - hlo)
    safe_h = math.acos(far / EXTENT_M)
    certain = np.maximum(0., np.minimum(hhi, min(hi, safe_h))
                         - np.maximum(hlo, max(lo, -safe_h))) / (hhi - hlo)
    return certain[:, None] * BANDS, coverage[:, None] * BANDS


def certify_initial_body_clear(engine, state):
    """Conservative AABB separation for this diagnostic's forward +/-45deg FOV.

    Read native admitted geometry; do not remove any self surface from rays.
    This proof is for the unrotated initial bench only, not a production culler.
    """
    observed = engine.observe(state)
    head = next(f for f in observed.world_frames if f.name == "guala/head")
    eye = np.array(head.position_m) + np.array(head.rotation_world).reshape(3, 3) @ ORIGIN
    np.testing.assert_allclose(eye, (ORIGIN[0], 0., EYE_Z), atol=1e-15, rtol=0)
    m, d = engine._model, engine._data
    for i in engine._self_geoms:
        kind, size = m.geom_type[i], m.geom_size[i]
        rotation = d.geom_xmat[i].reshape(3, 3)
        if kind == mj.mjtGeom.mjGEOM_BOX:
            half = np.abs(rotation) @ size
        elif kind == mj.mjtGeom.mjGEOM_SPHERE:
            half = np.full(3, size[0])
        elif kind == mj.mjtGeom.mjGEOM_CAPSULE:
            half = np.abs(rotation[:, 2]) * size[1] + size[0]
        else:
            raise ValueError("analytic bench body-clearance shape unsupported")
        low, high = d.geom_xpos[i] - half - eye, d.geom_xpos[i] + half - eye
        if high[0] <= 0:
            continue
        horizontal = math.hypot(max(abs(low[0]), abs(high[0])),
                                max(abs(low[1]), abs(high[1])))
        if high[2] > -horizontal:
            raise AssertionError("body clearance cannot certify analytic optical bench")
    return observed


def byte_error(observed, truth, gain):
    return int(np.max(np.abs(np.rint(255 * np.minimum(1., observed * gain))
                             - np.rint(255 * np.minimum(1., truth * gain)))))


def run():
    print(json.dumps({"pid": os.getpid(), "kind": "offline_optical_regime",
                      "logical_batch_bytes": LOGICAL_BATCH_BYTES,
                      "no_production_renderer_claim": True}), flush=True)
    started = time.perf_counter()
    apertures = retinal_apertures()
    assert len(apertures) == 19335
    for kind, edge, upper in CASES:
        xml, engine = scene(edge, upper)
        state = engine.initial_state()
        before = certify_initial_body_clear(engine, state)
        lower, upper_bound = analytic_bounds(apertures, edge, upper)
        previous = None
        for n in COUNTS:
            # High-count sweep is coarse-only: focal counts are separately
            # measured at1,2,4. Never silently claim128x128 focal verification.
            selected = apertures if n <= 4 else apertures[:135]
            low, high = lower[:len(selected)], upper_bound[:len(selected)]
            measured, stats = sample(engine, state, selected, [n] * len(selected))
            if stats["non_panel_hits"]:
                raise AssertionError("analytic bench occluded or escaped its finite panels")
            error = np.maximum(np.abs(measured - low), np.abs(measured - high))
            change = None if previous is None else float(np.max(np.abs(measured[:135] - previous[:135])))
            print(json.dumps({"case": kind, "edge_degrees": edge, "upper_degrees": upper,
                              "samples_per_axis": n, "sites": len(selected), **stats,
                              "max_error_bound": float(error.max()), "mean_error_bound": float(error.mean()),
                              "analytic_interval_width": float(np.max(high - low)),
                              "coarse_level_change": change,
                              "max_byte_error_bound_gain1": max(byte_error(measured, low, 1.), byte_error(measured, high, 1.)),
                              "max_byte_error_bound_gain16": max(byte_error(measured, low, 16.), byte_error(measured, high, 16.))}), flush=True)
            previous = measured
        # Exact typed current state -> fresh authority -> same light and next
        # motor successor. No ray query may advance the body or retain commands.
        fresh = NativeBody(xml, LIMITS, sensory_root="guala/pelvis")
        a, _ = sample(engine, state, apertures[:135], [4] * 135)
        b, _ = sample(fresh, state, apertures[:135], [4] * 135)
        np.testing.assert_array_equal(a, b)
        assert engine.observe(state) == before
        motor = engine.actuator_names.index("guala/head/roll/effort")
        assert engine.advance(state, None, 10000, 1., effort_updates=((motor, .02),)) == fresh.advance(
            state, None, 10000, 1., effort_updates=((motor, .02),))
    usage = resource.getrusage(resource.RUSAGE_SELF)
    print(json.dumps({"kind": "completed", "wall_s": time.perf_counter() - started,
                      "user_s": usage.ru_utime, "system_s": usage.ru_stime,
                      "peak_rss_kib": usage.ru_maxrss,
                      "sampling_law_accepted": False}), flush=True)


if __name__ == "__main__":
    run()
