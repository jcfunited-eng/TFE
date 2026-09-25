"""Standalone reference morphology proofs; no cognitive or live-world imports."""
import math
import unittest
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_anatomy import (
    ACTUATOR_STRESS_PA, DENSITY_KG_M3, BEARING_VISCOSITY_PA_S,
    append_reference_biped, bearing_drag,
)
from dsf_ai_service.substrate.functional_body_native import MechanicalLimits, NativeBody


LIMITS = MechanicalLimits(1000, 250, .008, .03, .005, .015)


def model_xml(*, floor=False, gravity=True):
    root = ET.fromstring('''<mujoco model="functional-reference-body">
      <compiler angle="radian" inertiafromgeom="true"/>
      <size memory="8M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10"/>
      <default><geom friction="0.6 0.002 0.0001" solref="0.01 1"
        solimp="0.95 0.99 0.001"/></default>
      <worldbody/><actuator/><sensor/>
    </mujoco>''')
    root.find("option").set("gravity", "0 0 -9.81" if gravity else "0 0 0")
    world = root.find("worldbody")
    if floor:
        ET.SubElement(world, "geom", name="bench-floor", type="plane", size="2 2 .1")
    append_reference_biped(world, root.find("actuator"), root.find("sensor"),
                           root_position_m=(0, 0, .54))
    return ET.tostring(root, encoding="unicode")


class ReferenceBodyTests(unittest.TestCase):
    def test_one_free_body_independent_digits_and_measured_channels(self):
        engine = NativeBody(model_xml(), LIMITS)
        m = engine._model
        self.assertEqual((m.njnt, m.nu, m.nq, m.nv), (65, 64, 71, 70))
        self.assertEqual(sum(m.jnt_type == mj.mjtJoint.mjJNT_FREE), 1)
        self.assertEqual((m.neq, m.nmocap, m.nkey, m.na, m.nplugin), (0, 0, 0, 0, 0))
        self.assertEqual(m.nsensor, 204)
        self.assertTrue(all(name.startswith("guala/") for name in engine.actuator_names))
        for side in ("left", "right"):
            for digit in range(5):
                for part in ("proximal", "distal"):
                    self.assertIn(f"guala/{side}/digit-{digit}/{part}/flexion", engine.joint_names)
                self.assertIn(f"guala/{side}/toe-{digit}/flexion", engine.joint_names)
        self.assertTrue(np.all(m.body_mass[1:] > 0))
        self.assertTrue(np.all(m.body_inertia[1:] > 0))
        # No age multiplier or arbitrary inertia normalization: compiled mass is
        # the sum of declared homogeneous geom volume times declared density.
        total = 0.0
        for i, kind in enumerate(m.geom_type):
            a, b, c = m.geom_size[i]
            if kind == mj.mjtGeom.mjGEOM_BOX:
                volume = 8 * a * b * c
            elif kind == mj.mjtGeom.mjGEOM_SPHERE:
                volume = 4 / 3 * math.pi * a**3
            else:
                self.assertEqual(kind, mj.mjtGeom.mjGEOM_CAPSULE)
                volume = math.pi * a**2 * (2 * b) + 4 / 3 * math.pi * a**3
            total += volume * DENSITY_KG_M3
        self.assertAlmostEqual(sum(m.body_mass), total, places=10)
        i = engine.actuator_names.index("guala/left/thigh/pitch/effort")
        self.assertAlmostEqual(m.actuator_forcerange[i, 1],
                               ACTUATOR_STRESS_PA * math.pi * .032**2 * .016)

    def test_unpowered_body_falls_with_zero_specific_force_not_hidden_balance(self):
        engine = NativeBody(model_xml(), LIMITS)
        initial = engine.initial_state()
        before = engine.observe(initial)
        self.assertEqual(before.contacts, ())
        result = engine.advance(initial, (0,) * 64, 50000, 0)
        self.assertAlmostEqual(result.observation.qvel[2], -.4905, places=10)
        self.assertLess(result.observation.qpos[2], before.qpos[2])
        self.assertLess(max(abs(x) for x in result.observation.qvel[3:]), 1e-9)
        for name, values in result.observation.sensors:
            if name.endswith("/specific-force"):
                self.assertLess(max(abs(x) for x in values), 1e-8)
        self.assertEqual(result.positive_motor_work_j, 0)

    def test_digit_effort_has_physical_joint_return_and_cold_continuation(self):
        xml = model_xml(gravity=False)
        engine = NativeBody(xml, LIMITS)
        state = engine.initial_state()
        name = "guala/left/digit-1/distal/flexion"
        i = engine.actuator_names.index(name + "/effort")
        effort = [0.0] * 64
        effort[i] = engine._model.actuator_forcerange[i, 1] / 100
        result = engine.advance(state, tuple(effort), 10000, 1)
        readings = dict(result.observation.sensors)
        self.assertGreater(readings[name + "/angle"][0], 0)
        self.assertGreater(readings[name + "/rate"][0], 0)
        self.assertAlmostEqual(readings[name + "/effort-return"][0], effort[i])
        self.assertGreater(result.positive_motor_work_j, 0)
        zero = engine.advance(state, (0,) * 64, 10000, 0)
        self.assertEqual(dict(zero.observation.sensors)[name + "/angle"], (0,))
        fresh = NativeBody(xml, LIMITS)
        self.assertEqual(engine.advance(result.state, tuple(effort), 1000, 1),
                         fresh.advance(result.state, tuple(effort), 1000, 1))
        self.assertEqual(len(state), len(result.state))

    def test_floor_support_is_contact_not_a_seated_or_held_flag(self):
        engine = NativeBody(model_xml(floor=True), LIMITS)
        state = engine.initial_state()
        floor = engine.geom_names.index("bench-floor")
        result = engine.advance(state, (0,) * 64, 100000, 0)
        support = [c for c in result.observation.contacts if floor in c.geom_pair]
        self.assertTrue(support)
        self.assertGreater(sum(c.wrench[0] for c in support), 0)
        self.assertGreater(result.observation.qpos[2], .50)
        self.assertEqual(result.positive_motor_work_j, 0)


    def test_three_axis_workspace_excludes_interior_kinematic_singularities(self):
        root = ET.fromstring(model_xml())
        checked = 0
        for body in root.findall(".//body"):
            joints = body.findall("joint")
            if len(joints) != 3:
                continue
            lower, upper = map(float, joints[1].get("range").split())
            lower -= LIMITS.max_hinge_overrun_rad
            upper += LIMITS.max_hinge_overrun_rad
            self.assertGreater(lower, -math.pi / 2)
            self.assertLess(upper, math.pi / 2)
            # XYZ instantaneous axis columns at first angle zero. Rotating all
            # columns by the first angle preserves rank; third does not enter.
            for pitch in (lower, 0, upper):
                axes = np.array([[1, 0, math.sin(pitch)],
                                 [0, 1, 0],
                                 [0, 0, math.cos(pitch)]])
                self.assertEqual(np.linalg.matrix_rank(axes), 3)
                self.assertGreater(abs(np.linalg.det(axes)), .14)
            checked += 1
        self.assertEqual(checked, 6)


    def test_bearing_drag_is_material_derived_passive_and_native(self):
        r = .004
        ri, ro, length = r / 2, .55 * r, r
        expected = 4 * math.pi * BEARING_VISCOSITY_PA_S * length * ri**2 * ro**2 / (ro**2 - ri**2)
        self.assertAlmostEqual(bearing_drag(r), expected, places=15)
        self.assertAlmostEqual(bearing_drag(2*r), 8*bearing_drag(r), places=15)
        engine = NativeBody(model_xml(gravity=False), LIMITS)
        i = engine.actuator_names.index("guala/left/digit-1/distal/flexion/effort")
        effort = [0.] * 64
        effort[i] = engine._model.actuator_forcerange[i, 1] / 100
        engine.advance(engine.initial_state(), tuple(effort), 10000, 1)
        m, d = engine._model, engine._data
        self.assertLess(float(np.dot(d.qfrc_passive, d.qvel)), 0)
        self.assertTrue(np.allclose(d.qfrc_passive, -m.dof_damping * d.qvel,
                                    atol=1e-12, rtol=1e-12))
        self.assertEqual(tuple(m.dof_damping[:6]), (0,)*6)
        for value in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                bearing_drag(value)

    def test_duplicate_anatomy_refused_without_changing_model(self):
        root = ET.fromstring(model_xml())
        before = ET.tostring(root)
        with self.assertRaises(ValueError):
            append_reference_biped(root.find("worldbody"), root.find("actuator"),
                                   root.find("sensor"), root_position_m=(0, 0, .54))
        self.assertEqual(before, ET.tostring(root))


if __name__ == "__main__":
    unittest.main()
