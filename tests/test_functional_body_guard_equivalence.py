"""Exact guard-execution equivalence; standalone, no pytest/world/network writes.

The scalar checker is the accepted c2c7f219a implementation, retained ONLY as a
test oracle. Numerical response variants are the already recorded diagnostic
loads, not admitted tissue laws. Injected scratch values test refusal boundaries;
they never count as sensory experience or successful organism behavior.
"""
from dataclasses import replace
import json
import math
from pathlib import Path
import resource
import time
from types import MethodType
import unittest
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_native import NativeBody
from test_functional_body_native import apparatus, falling_body, gripper
from test_functional_body_optical_sources import declaration
from guala_body_active_load_regime import REPRESENTATIVES


def _check(self):
    m, d, lim = self._model, self._data, self.limits
    if any(w.number for w in d.warning):
        raise ValueError("native mechanics warning; no successor admitted")
    if not all(np.isfinite(x).all() for x in (d.qpos, d.qvel, d.qacc)):
        raise ValueError("non-finite mechanical state")
    if not math.isfinite(d.time):
        raise ValueError("non-finite mechanical time")
    if np.any(np.spacing(np.abs(d.geom_xpos)) > lim.max_surface_travel_m):
        raise ValueError("body coordinates exceed declared numerical resolution")
    if any(c.dist < -lim.max_penetration_m for c in d.contact):
        raise ValueError("contact penetration exceeds declared resolution")
    for i in self._limited:
        q = d.qpos[m.jnt_qposadr[i]]
        tolerance = (lim.max_hinge_overrun_rad if m.jnt_type[i] == mj.mjtJoint.mjJNT_HINGE
                     else lim.max_slide_overrun_m)
        if not m.jnt_range[i, 0] - tolerance <= q <= m.jnt_range[i, 1] + tolerance:
            raise ValueError("joint limit overrun exceeds declared resolution")


def scalar(engine):
    engine._check = MethodType(_check, engine)
    return engine


def outcome(engine):
    try:
        engine._check()
        return None
    except ValueError as error:
        return str(error)


def pair(factory):
    return factory(), scalar(factory())


class NativeGuardEquivalenceTests(unittest.TestCase):
    def test_every_guard_boundary_and_precedence(self):
        for factory in (lambda: apparatus(False), lambda: gripper(.6), falling_body):
            a, b = pair(factory)
            initial = a.initial_state()
            self.assertEqual(initial, b.initial_state())

            def same(edit):
                for engine in (a, b):
                    engine._restore(initial)
                    edit(engine)
                self.assertEqual(outcome(a), outcome(b))

            # Empty contact/limited arrays and ordinary finite states included.
            same(lambda e: None)
            for index in range(len(a._data.warning)):
                same(lambda e, i=index: setattr(e._data.warning[i], "number", 1))
            for name in ("qpos", "qvel", "qacc"):
                for value in (math.nan, math.inf, -math.inf):
                    same(lambda e, n=name, v=value: getattr(e._data, n).__setitem__(0, v))
            same(lambda e: setattr(e._data, "time", math.nan))
            same(lambda e: e._data.geom_xpos.__setitem__((0, 0), 1e20))
            if len(a._data.contact):
                for value in (-a.limits.max_penetration_m,
                              np.nextafter(-a.limits.max_penetration_m, -math.inf)):
                    same(lambda e, v=value: setattr(e._data.contact[0], "dist", v))
            for joint in a._limited:
                tol = (a.limits.max_hinge_overrun_rad
                       if a._model.jnt_type[joint] == mj.mjtJoint.mjJNT_HINGE
                       else a.limits.max_slide_overrun_m)
                lower, upper = a._model.jnt_range[joint] + np.array((-tol, tol))
                addr = a._model.jnt_qposadr[joint]
                for value in (lower, upper, np.nextafter(lower, -math.inf),
                              np.nextafter(upper, math.inf)):
                    same(lambda e, v=value, i=addr: e._data.qpos.__setitem__(i, v))

            def multiple(e):
                e._data.warning[0].number = 1
                e._data.qpos[0] = math.nan
                e._data.time = math.nan
            same(multiple)
            self.assertEqual(outcome(a), "native mechanics warning; no successor admitted")
            for array in (a._limit_qpos, a._limit_lower, a._limit_upper):
                self.assertFalse(array.flags.writeable)

    def test_unordered_limit_bounds_preserve_fail_closed_refusal(self):
        # Guard fault injection only: never advance these artificial models.
        for side, attr in ((0, "_limit_lower"), (1, "_limit_upper")):
            a, b = pair(lambda: apparatus(False))
            initial = a.initial_state()
            for engine in (a, b):
                engine._restore(initial)
            joint = a._limited[0]
            bounds = getattr(a, attr).copy()
            bounds[0] = math.nan
            bounds.setflags(write=False)
            setattr(a, attr, bounds)
            b._model.jnt_range[joint, side] = math.nan
            self.assertEqual(outcome(a), outcome(b))
            self.assertEqual(outcome(a), "joint limit overrun exceeds declared resolution")

    def test_contact_successors_and_cold_continuation_are_identical(self):
        a, b = pair(apparatus)
        sa, sb = a.initial_state(), b.initial_state()
        contact_seen = False
        for _ in range(30):
            ra = a.advance(sa, (.3,), 20000, 1)
            rb = b.advance(sb, (.3,), 20000, 1)
            self.assertEqual(ra, rb)
            contact_seen |= bool(ra.observation.contacts)
            sa, sb = ra.state, rb.state
        self.assertTrue(contact_seen)
        fresh = apparatus()
        self.assertEqual(fresh.advance(bytes(sa), None, 10000, 1),
                         b.advance(sb, None, 10000, 1))

    def test_all_128_unchanged_endpoint_refusals_and_scratch_match(self):
        decl = declaration()
        a, b = pair(lambda: NativeBody(decl.xml, decl.limits, sensory_root=decl.sensory_root))
        state = a.initial_state()
        self.assertEqual(state, b.initial_state())
        prior = json.loads((Path(__file__).resolve().parents[1] /
            "docs/evidence/FB-01aj-endpoint-loads.json").read_text())
        supply = json.loads((Path(__file__).resolve().parents[1] /
            "docs/evidence/FB-01aj-active-load-map.json").read_text())["supply_j"]
        for row in prior["rows"]:
            index = a.actuator_names.index(row["name"])
            outputs = []
            for engine in (a, b):
                with self.assertRaisesRegex(ValueError, row["result"]):
                    engine.advance(state, None, 250000, supply,
                                   effort_updates=((index, row["effort"]),))
                outputs.append((engine._data.time, engine._capture()))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0][0], row["time_s"])

    def test_resolved_diagnostic_loads_exact_successors_and_measured_cost(self):
        decl = declaration()
        root = ET.fromstring(decl.xml)
        for element in root.findall(".//joint"):
            element.set("solreflimit", ".0002 1")
            element.set("solimplimit", ".999 .999 .001 .5 2")
        for element in root.findall(".//geom"):
            element.set("solref", ".0002 1")
            element.set("solimp", ".999 .999 .001 .5 2")
        xml = ET.tostring(root, encoding="unicode")
        limits = replace(decl.limits, step_us=100, max_substeps=2500)
        factory = lambda: NativeBody(xml, limits, sensory_root=decl.sensory_root)
        a, b = pair(factory)
        initial = a.initial_state()
        self.assertEqual(initial, b.initial_state())
        prior = json.loads((Path(__file__).resolve().parents[1] /
            "docs/evidence/FB-01aj-active-load-map.json").read_text())
        timing = {"array_seconds": 0., "scalar_seconds": 0.}
        for name, sign in REPRESENTATIVES:
            index = a.actuator_names.index(name)
            force = float(a._model.actuator_forcerange[index, 0 if sign < 0 else 1])
            results = []
            for label, engine in (("array_seconds", a), ("scalar_seconds", b)):
                start = time.perf_counter()
                result = engine.advance(initial, None, 250000, prior["supply_j"],
                                        effort_updates=((index, force),))
                timing[label] += time.perf_counter() - start
                results.append(result)
            self.assertEqual(results[0], results[1])
            old = next(r for r in prior["cases"] if r["configuration"] == "finer_constant_impedance"
                       and r["name"] == name and r["effort"] == force)
            self.assertEqual(results[0].positive_motor_work_j, old["positive_work_j"])
            self.assertEqual(results[0].unresolved_energy_exchange_j, old["unresolved_energy_exchange_j"])
            fresh = factory()
            self.assertEqual(fresh.observe(bytes(results[0].state)), results[1].observation)
        timing.update(loads=len(REPRESENTATIVES),
                      peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        print(json.dumps(timing), flush=True)


if __name__ == "__main__":
    unittest.main()
