"""Standalone mechanical bench; no organism, caretaker, network or pytest fixtures.

Dimensions, material coefficients and efforts below describe the test apparatus,
not Guala's anatomy or learned movement. A motor effort is an external bench load.
"""
from dataclasses import replace
import math
import unittest

from dsf_ai_service.substrate.functional_body_native import MechanicalLimits, NativeBody


LIMITS = MechanicalLimits(1000, 1000, 0.008, 0.03, 0.005, 0.01)


def apparatus(panel=True, timestep=1000, travel=LIMITS.max_surface_travel_m):
    panel_xml = '''<body name="panel" pos="0.30 0.12 1">
      <joint name="panel-hinge" type="hinge" axis="0 0 1" range="0 1.2" damping="0.02"/>
      <geom name="panel-face" type="box" pos="0.20 0 0" size="0.20 0.025 0.20" mass="0.5"/>
    </body>''' if panel else ""
    xml = f'''<mujoco model="mechanical-hand-panel-bench">
      <compiler angle="radian"/>
      <size memory="2M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
      <default>
        <joint limited="true" range="-1 1"/>
        <geom friction="0.6 0.002 0.0001" solref="0.01 1" solimp="0.95 0.99 0.001"/>
      </default>
      <worldbody>
        <body name="arm" pos="0 0 1">
          <joint name="shoulder" axis="0 0 1" range="-0.7 0.7"/>
          <geom type="capsule" fromto="0 0 0 0.32 0 0" size="0.025" mass="1"/>
          <body name="palm" pos="0.35 0 0">
            <joint name="wrist" axis="0 1 0" range="-0.6 0.6" damping="0.02"/>
            <geom type="box" size="0.035 0.035 0.015" mass="0.15"/>
            <site name="palm-inertial" size="0.005"/>
            <body name="finger-a" pos="0.035 -0.018 0">
              <joint name="finger-a-joint" axis="0 1 0" range="-0.3 1.4"/>
              <geom type="capsule" fromto="0 0 0 0.045 0 0" size="0.008" mass="0.025"/>
            </body>
            <body name="finger-b" pos="0.035 0.018 0">
              <joint name="finger-b-joint" axis="0 1 0" range="-0.3 1.4"/>
              <geom type="capsule" fromto="0 0 0 0.045 0 0" size="0.008" mass="0.025"/>
            </body>
          </body>
        </body>
        {panel_xml}
      </worldbody>
      <actuator><motor name="shoulder-effort" joint="shoulder" forcelimited="true" forcerange="-1 1"/></actuator>
      <sensor><accelerometer name="palm-specific-force" site="palm-inertial"/>
        <gyro name="palm-angular-rate" site="palm-inertial"/>
        <jointpos name="wrist-angle" joint="wrist"/>
        <jointvel name="wrist-rate" joint="wrist"/></sensor>
    </mujoco>'''
    return NativeBody(xml, replace(LIMITS, step_us=timestep, max_surface_travel_m=travel))


def falling_body(*, supported=False, step_us=1000, initial_height=None):
    plane = '<geom name="floor" type="plane" size="2 2 0.1"/>' if supported else ""
    height = (0.1 if supported else 1.0) if initial_height is None else initial_height
    return NativeBody(f'''<mujoco>
      <size memory="2M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 -9.81"/>
      <default><geom friction="0.6 0.002 0.0001" solref="0.01 1" solimp="0.95 0.99 0.001"/></default>
      <worldbody>{plane}<body name="mass" pos="0 0 {height}"><freejoint/>
        <geom type="sphere" size="0.1" mass="1"/><site name="sensor" size="0.005"/>
      </body></worldbody><sensor><accelerometer name="specific-force" site="sensor"/>
        <gyro name="angular-rate" site="sensor"/></sensor>
    </mujoco>''', replace(LIMITS, step_us=step_us))


def gripper(friction):
    # Two independently actuated jaws. The object is free, never welded/held.
    return NativeBody(f'''<mujoco>
      <compiler angle="radian"/><size memory="2M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 -9.81"/>
      <default><geom friction="{friction} 0 0" solref="0.01 1" solimp="0.95 0.99 0.001"/></default>
      <worldbody>
        <body pos="-0.033 0 0.5">
          <joint name="left" type="slide" axis="1 0 0" limited="true" range="-0.02 0.02"/>
          <geom type="box" size="0.01 0.04 0.06" mass="0.1"/>
        </body>
        <body pos="0.033 0 0.5">
          <joint name="right" type="slide" axis="-1 0 0" limited="true" range="-0.02 0.02"/>
          <geom type="box" size="0.01 0.04 0.06" mass="0.1"/>
        </body>
        <body pos="0 0 0.5"><freejoint name="object"/>
          <geom name="free-object" type="sphere" size="0.025" mass="0.05"/>
        </body>
      </worldbody>
      <actuator>
        <motor name="left-force" joint="left" forcelimited="true" forcerange="-2 2"/>
        <motor name="right-force" joint="right" forcelimited="true" forcerange="-2 2"/>
      </actuator>
    </mujoco>''', LIMITS)


def direct_model(joint_attributes="", body_attributes="", option_attributes=""):
    return f'''<mujoco><size memory="2M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" {option_attributes}/>
      <worldbody><body {body_attributes}><joint name="joint" type="hinge" {joint_attributes}/>
        <geom type="sphere" size="0.1" mass="1"/></body></worldbody>
      <actuator><motor joint="joint" forcelimited="true" forcerange="-1 1"/></actuator>
    </mujoco>'''


class NativeBodyTests(unittest.TestCase):
    def test_jointed_hand_physically_pushes_panel_and_contact_restart(self):
        engine = apparatus()
        state = engine.initial_state()
        panel_index = engine.qpos_addresses[engine.joint_names.index("panel-hinge")]
        initial = engine.observe(state)
        panel_geom = engine.geom_names.index("panel-face")
        contact_peak = 0.0
        contacted_state = None
        for _ in range(30):
            result = engine.advance(state, (0.3,), 20000, 1.0)
            state = result.state
            for c in result.observation.contacts:
                if panel_geom not in c.geom_pair:
                    continue
                contact_peak = max(contact_peak, abs(c.wrench[0]))
                if c.wrench[0] > 0:
                    contacted_state = state
        self.assertGreater(contact_peak, 0)
        self.assertGreater(result.observation.qpos[panel_index], initial.qpos[panel_index] + 0.01)
        self.assertIsNotNone(contacted_state)
        a = engine.advance(contacted_state, (0.3,), 10000, 1.0)
        fresh = apparatus()
        b = fresh.advance(bytes(contacted_state), (0.3,), 10000, 1.0)
        self.assertEqual(a, b)
        self.assertTrue(any(abs(v) > 0 for _, x in a.observation.sensors for v in x))

    def test_no_effort_does_not_move_panel(self):
        engine = apparatus()
        state = engine.initial_state()
        before = engine.observe(state)
        after = engine.advance(state, (0.0,), 500000, 0.0)
        self.assertEqual(before.qpos, after.observation.qpos)
        self.assertEqual(after.positive_motor_work_j, 0)

    def test_removing_panel_removes_contact_resistance(self):
        loaded, free = apparatus(), apparatus(panel=False)
        a, b = loaded.initial_state(), free.initial_state()
        for _ in range(25):
            ra = loaded.advance(a, (0.3,), 20000, 1.0)
            rb = free.advance(b, (0.3,), 20000, 1.0)
            a, b = ra.state, rb.state
        self.assertGreater(rb.observation.qpos[0], ra.observation.qpos[0])
        self.assertEqual(rb.observation.contacts, ())

    def test_gravity_inertial_return_and_energy_error_refinement(self):
        errors = []
        for step in (1000, 500):
            engine = falling_body(step_us=step)
            state = engine.initial_state()
            initial = engine.observe(state)
            result = engine.advance(state, (), 100000, 0)
            final = result.observation
            self.assertAlmostEqual(final.qvel[2], -0.981, places=12)
            self.assertLessEqual(abs(final.qpos[2] - (1 - 9.81 * 0.1**2 / 2)),
                                 9.81 * 0.1 * (step / 1e6) / 2 + 1e-12)
            for _, values in final.sensors:
                self.assertLess(max(abs(x) for x in values), 1e-10)
            error = abs(final.kinetic_j + final.potential_j - initial.potential_j)
            self.assertLessEqual(error, 0.5 * 9.81**2 * 0.1 * step / 1e6 + 1e-11)
            errors.append(error)
        self.assertLess(errors[1], errors[0] * 0.51)

    def test_normal_support_returns_weight_and_specific_force(self):
        engine = falling_body(supported=True)
        result = engine.advance(engine.initial_state(), (), 500000, 0)
        self.assertGreater(result.observation.qpos[2], 0.1 - LIMITS.max_penetration_m)
        readings = dict(result.observation.sensors)
        self.assertAlmostEqual(readings["specific-force"][2], 9.81, delta=0.02)
        self.assertAlmostEqual(sum(c.wrench[0] for c in result.observation.contacts), 9.81, delta=0.02)

    def test_capacity_energy_and_work_budget_refuse_without_committing(self):
        engine = apparatus(panel=False)
        state = engine.initial_state()
        baseline = engine.advance(state, (0.3,), 10000, 1)
        for efforts, dt, work in (((1.01,), 10000, 1), ((0.3,), 10000, 0),
                                  ((0.3,), 1000001, 1), ((math.nan,), 10000, 1)):
            with self.assertRaises(ValueError):
                engine.advance(state, efforts, dt, work)
            self.assertEqual(engine.advance(state, (0.3,), 10000, 1), baseline)
        self.assertGreater(baseline.positive_motor_work_j, 0)

    def test_state_is_current_only_and_anatomy_bound(self):
        engine = apparatus()
        state = engine.initial_state()
        size = len(state)
        for _ in range(100):
            state = engine.advance(state, (0,), 1000, 0).state
            self.assertEqual(len(state), size)
        with self.assertRaises(ValueError):
            apparatus(panel=False).observe(state)
        with self.assertRaises(ValueError):
            engine.observe(state[:-1])

    def test_joint_stop_limits_motion(self):
        engine = apparatus(panel=False)
        state = engine.initial_state()
        for _ in range(100):
            result = engine.advance(state, (0.3,), 10000, 1)
            state = result.state
        self.assertGreater(result.observation.qpos[0], 0.6)
        self.assertLessEqual(result.observation.qpos[0], 0.7 + LIMITS.max_hinge_overrun_rad)


    def test_frictional_grip_requires_both_squeeze_and_friction(self):
        heights = []
        for friction, force in ((0.8, 1.0), (0.0, 1.0), (0.8, 0.0)):
            engine = gripper(friction)
            result = engine.advance(engine.initial_state(), (force, force), 500000, 1.0)
            index = engine.qpos_addresses[engine.joint_names.index("object")]
            heights.append(result.observation.qpos[index + 2])
            if friction and force:
                object_geom = engine.geom_names.index("free-object")
                contacts = [c for c in result.observation.contacts if object_geom in c.geom_pair]
                self.assertGreaterEqual(len(contacts), 2)
                self.assertGreater(sum(abs(c.wrench[1]) + abs(c.wrench[2]) for c in contacts), 0)
        self.assertGreater(heights[0], 0.49)
        self.assertLess(heights[1], 0.30)
        self.assertLess(heights[2], 0.30)

    def test_resolution_breaches_are_refused(self):
        with self.assertRaisesRegex(ValueError, "penetration"):
            falling_body(supported=True, initial_height=0.08).initial_state()
        engine = apparatus(panel=False, travel=1e-12)
        state = engine.initial_state()
        with self.assertRaisesRegex(ValueError, "surface movement"):
            engine.advance(state, (0.3,), 1000, 1)
        self.assertEqual(engine.advance(state, (0,), 1000, 0).observation.qpos,
                         engine.observe(state).qpos)

    def test_additional_actuator_authorities_are_rejected(self):
        models = (
            direct_model(joint_attributes='actuatorfrclimited="true" actuatorfrcrange="-0.1 0.1"'),
            direct_model(body_attributes='gravcomp="1"'),
            direct_model(joint_attributes='actuatorgravcomp="true"'),
            direct_model(option_attributes='actuatorgroupdisable="0"'),
        )
        for xml in models:
            with self.assertRaisesRegex(ValueError, "additional motor"):
                NativeBody(xml, LIMITS)

    def test_active_native_callback_is_refused_not_cleared(self):
        import mujoco
        engine = apparatus()
        state = engine.initial_state()
        called = []
        callback = lambda m, d: called.append(True)
        mujoco.set_mjcb_control(callback)
        try:
            with self.assertRaisesRegex(ValueError, "callbacks"):
                engine.advance(state, (0,), 1000, 0)
            self.assertIs(mujoco.get_mjcb_control(), callback)
            self.assertEqual(called, [])
        finally:
            mujoco.set_mjcb_control(None)
        self.assertEqual(engine.advance(state, (0,), 1000, 0).observation.qpos,
                         engine.observe(state).qpos)


def sensory_bench(*, other_x=5.0, root="self"):
    # Engineering test apparatus: a rotated instrumented sphere on a floor,
    # plus a distant, unobserved hinged object. This is not an organism policy.
    return NativeBody(f'''<mujoco>
      <size memory="2M"/>
      <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 -9.81"/>
      <default><geom solref="0.01 1" solimp="0.95 0.99 0.001"/></default>
      <worldbody><geom name="floor" type="plane" size="2 2 .1"/>
        <body name="self" pos="0 0 .1" euler="90 0 0">
          <freejoint/><geom name="skin" type="sphere" size=".1" mass="1"/>
          <site name="inertial" size=".001"/>
        </body>
        <body name="outsider" pos="{other_x} 0 2">
          <joint name="external-hinge" axis="0 0 1"/>
          <geom name="external-surface" type="sphere" size=".1" mass="1"/>
        </body>
      </worldbody>
      <sensor>
        <accelerometer name="self-acceleration" site="inertial"/>
        <gyro name="self-angular-rate" site="inertial"/>
        <framepos name="forbidden-global-position" objtype="body" objname="self"/>
        <jointpos name="forbidden-external-angle" joint="external-hinge"/>
      </sensor>
    </mujoco>''', LIMITS, sensory_root=root)


class NativeInterfaceTests(unittest.TestCase):
    def test_incremental_commands_preserve_simultaneous_effort_and_cold_state(self):
        engine = gripper(.8)
        initial = engine.initial_state()
        first = engine.advance(initial, None, 1000, 1, effort_updates=((0, .5),))
        both = engine.advance(first.state, None, 1000, 1, effort_updates=((1, .5),))
        explicit = engine.advance(first.state, (.5, .5), 1000, 1)
        self.assertEqual(both, explicit)
        self.assertEqual(engine.advance(both.state, None, 1000, 1),
                         gripper(.8).advance(both.state, (.5, .5), 1000, 1))
        released = engine.advance(both.state, None, 1000, 1, effort_updates=((0, 0.),))
        self.assertEqual(released, engine.advance(both.state, (0., .5), 1000, 1))
        self.assertEqual(len(initial), len(released.state))

    def test_bad_partial_commands_refuse_without_changing_authoritative_bytes(self):
        engine = gripper(.8)
        state = engine.initial_state()
        expected = engine.advance(state, None, 1000, 1, effort_updates=((0, .5),))
        for updates in (((0, .1), (0, .2)), ((2, 0.),), ((True, .1),),
                        ((0, math.nan),), ((0, 3.),)):
            with self.assertRaises(ValueError):
                engine.advance(state, None, 1000, 1, effort_updates=updates)
            self.assertEqual(engine.advance(state, None, 1000, 1,
                                             effort_updates=((0, .5),)), expected)
        with self.assertRaises(ValueError):
            engine.advance(state, (0., 0.), 1000, 1, effort_updates=((0, .5),))

    def test_local_feedback_has_no_external_identity_or_global_position(self):
        a, b = sensory_bench(other_x=5), sensory_bench(other_x=7)
        ra = a.advance(a.initial_state(), (), 100000, 0)
        rb = b.advance(b.initial_state(), (), 100000, 0)
        self.assertEqual(ra.observation.self_feedback, rb.observation.self_feedback)
        self.assertEqual(set(dict(ra.observation.self_feedback.sensors)),
                         {"self-acceleration", "self-angular-rate"})
        self.assertIn("forbidden-global-position", dict(ra.observation.sensors))
        self.assertIn("forbidden-external-angle", dict(ra.observation.sensors))
        self.assertTrue(ra.observation.self_feedback.contacts)
        for contact in ra.observation.self_feedback.contacts:
            self.assertEqual(contact.surface, "skin")
            self.assertFalse(hasattr(contact, "geom_pair"))
            self.assertFalse(hasattr(contact, "world_position"))
        self.assertFalse(hasattr(ra.observation.self_feedback, "qpos"))
        self.assertIsNone(falling_body().observe(falling_body().initial_state()).self_feedback)
        with self.assertRaises(ValueError):
            sensory_bench(root="absent")

    def test_rotated_contact_returns_local_force_and_retains_restart_evidence(self):
        engine = sensory_bench()
        result = engine.advance(engine.initial_state(), (), 500000, 0)
        sensed = result.observation.self_feedback
        # The sphere's +local-y axis is world up after a 90deg x rotation.
        force = tuple(sum(c.force_n[i] for c in sensed.contacts) for i in range(3))
        self.assertAlmostEqual(force[0], 0, delta=.02)
        self.assertAlmostEqual(force[1], 9.81, delta=.02)
        self.assertAlmostEqual(force[2], 0, delta=.02)
        self.assertLess(sensed.contacts[0].position_m[1], -.09)
        self.assertEqual(sensed, sensory_bench().observe(result.state).self_feedback)
        self.assertEqual(engine.advance(result.state, None, 1000, 0),
                         sensory_bench().advance(result.state, None, 1000, 0))

    def test_bearing_heat_braking_and_energy_residual_are_separate(self):
        errors = []
        for step in (1000, 500):
            engine = NativeBody(direct_model(joint_attributes='damping="0.02"'),
                                replace(LIMITS, step_us=step))
            before = engine.observe(engine.initial_state())
            result = engine.advance(engine.initial_state(), (.3,), 100000, 1)
            self.assertGreater(result.bearing_dissipation_j, 0)
            self.assertEqual(result.motor_braking_work_j, 0)
            self.assertAlmostEqual(result.positive_motor_work_j,
                                   result.signed_motor_work_j, places=14)
            delta = (result.observation.kinetic_j + result.observation.potential_j
                     - before.kinetic_j - before.potential_j)
            self.assertAlmostEqual(result.signed_motor_work_j,
                delta + result.bearing_dissipation_j + result.unresolved_energy_exchange_j,
                places=14)
            # No contacts, other damping or springs: only quadrature/integration
            # error remains. Implicit Euler viscous evolution converges in dt.
            self.assertEqual(result.observation.contacts, ())
            errors.append(abs(result.unresolved_energy_exchange_j))
            braking = engine.advance(result.state, (-.3,), 1000, 0)
            self.assertEqual(braking.positive_motor_work_j, 0)
            self.assertLess(braking.signed_motor_work_j, 0)
            self.assertGreater(braking.motor_braking_work_j, 0)
            self.assertAlmostEqual(-braking.signed_motor_work_j,
                                   braking.motor_braking_work_j, places=14)
            self.assertGreater(braking.bearing_dissipation_j, 0)
        self.assertLess(errors[1], .55 * errors[0])

    def test_inactive_proximity_is_not_tactile_contact(self):
        xml = '''<mujoco><size memory="2M"/>
          <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
          <worldbody>
            <geom name="floor" type="plane" size="2 2 .1" margin=".01" gap=".008"/>
            <body name="self" pos="0 0 .105"><freejoint/>
              <geom name="skin" type="sphere" size=".1" mass="1"/>
            </body>
          </worldbody></mujoco>'''
        engine = NativeBody(xml, LIMITS, sensory_root="self")
        observation = engine.observe(engine.initial_state())
        self.assertTrue(observation.contacts)  # Within detection margin.
        self.assertTrue(all(c.separation_m > 0 for c in observation.contacts))
        self.assertTrue(all(c.efc_address < 0 for c in engine._data.contact))
        self.assertEqual(observation.self_feedback.contacts, ())

    def test_both_contact_sides_receive_opposite_local_forces(self):
        xml = '''<mujoco><size memory="2M"/>
          <option integrator="implicitfast" iterations="100" tolerance="1e-10" gravity="0 0 0"/>
          <worldbody><body name="self">
            <body name="left" pos="-.025 0 .5">
              <joint type="slide" axis="1 0 0"/>
              <geom name="left-skin" type="sphere" size=".026" mass=".1"/>
            </body>
            <body name="right" pos=".025 0 .5">
              <joint type="slide" axis="1 0 0"/>
              <geom name="right-skin" type="sphere" size=".026" mass=".1"/>
            </body>
          </body></worldbody></mujoco>'''
        engine = NativeBody(xml, LIMITS, sensory_root="self")
        observation = engine.observe(engine.initial_state())
        sensed = {c.surface: c for c in observation.self_feedback.contacts}
        self.assertEqual(set(sensed), {"left-skin", "right-skin"})
        self.assertLess(sensed["left-skin"].force_n[0], 0)
        self.assertGreater(sensed["right-skin"].force_n[0], 0)
        for i in range(3):
            self.assertAlmostEqual(sensed["left-skin"].force_n[i],
                                   -sensed["right-skin"].force_n[i], places=14)


if __name__ == "__main__":
    unittest.main()
