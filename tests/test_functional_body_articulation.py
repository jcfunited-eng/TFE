"""Standalone coupled mechanics; no organism/world/network or learning claim."""

from dataclasses import replace
from fractions import Fraction as F
import unittest

from dsf_ai_service.substrate.body_surface_contact import ExactVector3, ZERO_VECTOR as Z
from dsf_ai_service.substrate.functional_body_kinematics import PointMotion, RigidBasis, RigidMotion, _cross
from dsf_ai_service.substrate.functional_body_dynamics import MassProperties, Wrench, required_wrench, accelerated_motion
from dsf_ai_service.substrate.functional_body_articulation import HingeSegment, solve_hinge_tree


def v(x=0, y=0, z=0):
    return ExactVector3(F(x), F(y), F(z))


IDENTITY = RigidBasis(v(1), v(0, 1), v(0, 0, 1))
TURN = RigidBasis(v(F(3, 5), F(4, 5)), v(F(-4, 5), F(3, 5)), v(0, 0, 1))
TIP = RigidBasis(v(1), v(0, 0, -1), v(0, 1))
UNIT = MassProperties(F(1), v(1, 1, 1))
ZERO_LOAD = Wrench(Z, Z)


def root(omega=Z, velocity=Z, basis=IDENTITY):
    return RigidMotion(PointMotion(F(456), v(2, -1, 3), velocity, Z), basis, omega, Z)


def link(parent=0, basis=IDENTITY, properties=UNIT, parent_anchor=v(1), child_anchor=v(-1), child_axis=v(0, 0, 1)):
    return HingeSegment(parent, properties, parent_anchor, child_anchor,
                        basis.to_parent(child_axis), child_axis, basis)


class ArticulationTests(unittest.TestCase):
    def check_physics(self, props, tree, rates, efforts, external, result):
        """Independent Cartesian Newton-Euler, constraint and work-rate checks."""
        masses = (props,) + tuple(item.properties for item in tree)
        linear, angular, input_linear, input_angular = Z, Z, Z, Z
        energy_rate, external_power = F(0), F(0)
        for mass, body, load in zip(masses, result.motions, external):
            a = body.origin.acceleration_metres_per_second_squared
            velocity = body.origin.velocity_metres_per_second
            omega = body.angular_velocity_radians_per_second
            alpha = body.angular_acceleration_radians_per_second_squared
            momentum = body.basis.to_parent(mass.momentum(body.basis.to_local(omega)))
            angular_rate = body.basis.to_parent(mass.momentum(body.basis.to_local(alpha))) + _cross(omega, momentum)
            force = a.scaled(mass.mass_kilograms)
            position = body.origin.position_metres
            linear = linear + force
            angular = angular + angular_rate + _cross(position, force)
            input_linear = input_linear + load.force_newtons
            input_angular = input_angular + load.torque_newton_metres + _cross(position, load.force_newtons)
            energy_rate += force.dot(velocity) + omega.dot(angular_rate)
            external_power += load.power_watts(velocity, omega)
        base = result.motions[0]
        support = result.root_support_wrench_about_com
        self.assertEqual(linear, input_linear + support.force_newtons)
        self.assertEqual(angular, input_angular + support.torque_newton_metres
                         + _cross(base.origin.position_metres, support.force_newtons))
        self.assertEqual(energy_rate, external_power + sum((t * q for t, q in zip(efforts, rates)), F(0))
                         + support.power_watts(base.origin.velocity_metres_per_second,
                                               base.angular_velocity_radians_per_second))
        for i, item in enumerate(tree, 1):
            parent, child = result.motions[item.parent], result.motions[i]
            p = parent.at_local_point(item.parent_anchor_metres)
            c = child.at_local_point(item.child_anchor_metres)
            self.assertEqual(p, c, "joint anchors must share position, velocity and acceleration")
            axis = child.basis.to_parent(item.child_axis)
            self.assertEqual(child.angular_velocity_radians_per_second - parent.angular_velocity_radians_per_second,
                             axis.scaled(rates[i - 1]))
            at_joint = result.joint_wrenches_on_child_about_com[i - 1].shifted(
                child.basis.to_parent(item.child_anchor_metres))
            self.assertEqual(axis.dot(at_joint.torque_newton_metres), efforts[i - 1])

    def test_no_joint_reduces_to_existing_free_segment_law(self):
        properties = MassProperties(F(2), v(1, 2, 3))
        initial = root(v(1, 2, -3), v(2, 1, -1), TURN)
        load = Wrench(v(3, -2, 1), v(1, 4, -3))
        solved = solve_hinge_tree(properties, initial, (), (), (), (load,), None)
        self.assertEqual(solved.motions[0], accelerated_motion(properties, initial, load))
        self.assertEqual(solved.root_support_wrench_about_com, ZERO_LOAD)

    def test_tip_force_accelerates_whole_two_link_body(self):
        tree, external = (link(),), (ZERO_LOAD, Wrench(v(0, 1), Z))
        solved = solve_hinge_tree(UNIT, root(), tree, (F(0),), (F(0),), external, None)
        parent, child = solved.motions
        self.assertEqual(parent.origin.acceleration_metres_per_second_squared, v(0, F(1, 4)))
        self.assertEqual(child.origin.acceleration_metres_per_second_squared, v(0, F(3, 4)))
        self.assertEqual(parent.angular_acceleration_radians_per_second_squared, v(0, 0, F(1, 4)))
        self.assertEqual(child.angular_acceleration_radians_per_second_squared, v(0, 0, F(1, 4)))
        self.assertEqual(solved.joint_accelerations_radians_per_second_squared, (F(0),))
        self.assertEqual(solved.root_support_wrench_about_com, ZERO_LOAD)
        self.check_physics(UNIT, tree, (F(0),), (F(0),), external, solved)
        isolated = accelerated_motion(UNIT, root(), external[1])
        self.assertNotEqual(isolated.origin.acceleration_metres_per_second_squared,
                            child.origin.acceleration_metres_per_second_squared)

    def test_internal_coaxial_torque_reacts_on_parent(self):
        child_props = MassProperties(F(1), v(2, 2, 2))
        tree = (link(properties=child_props, parent_anchor=Z, child_anchor=Z),)
        solved = solve_hinge_tree(UNIT, root(), tree, (F(0),), (F(3),), (ZERO_LOAD, ZERO_LOAD), None)
        self.assertEqual(solved.motions[0].angular_acceleration_radians_per_second_squared, v(0, 0, -3))
        self.assertEqual(solved.motions[1].angular_acceleration_radians_per_second_squared, v(0, 0, F(3, 2)))
        self.assertEqual(solved.joint_accelerations_radians_per_second_squared, (F(9, 2),))
        self.check_physics(UNIT, tree, (F(0),), (F(3),), (ZERO_LOAD, ZERO_LOAD), solved)

    def test_explicit_support_reports_reaction_not_invisible_floor(self):
        tree, external = (link(),), (ZERO_LOAD, Wrench(v(0, 1), Z))
        solved = solve_hinge_tree(UNIT, root(), tree, (F(0),), (F(0),), external, (Z, Z))
        self.assertEqual(solved.joint_accelerations_radians_per_second_squared, (F(1, 2),))
        self.assertEqual(solved.root_support_wrench_about_com, Wrench(v(0, F(-1, 2)), v(0, 0, F(-1, 2))))
        self.check_physics(UNIT, tree, (F(0),), (F(0),), external, solved)

    def test_moving_asymmetric_branched_tree_conserves_momentum_and_power(self):
        props = MassProperties(F(3), v(4, 5, 6))
        tree = (link(basis=TURN, properties=MassProperties(F(2), v(2, 3, 4))),
                link(parent=1, basis=TIP, child_axis=v(0, 0, 1)),
                link(parent=0, basis=TIP, parent_anchor=v(0, -1), child_anchor=v(0, 0, -1)))
        external = (Wrench(v(0, 1, -5), v(1)), Wrench(v(2, -3), v(0, 1)),
                    ZERO_LOAD, Wrench(v(0, 0, -2), v(2, 3, -1)))
        for sign in (-1, 0, 1):
            rates = (F(sign), F(2 * sign), F(-3 * sign))
            efforts = (F(2), F(-1), F(3))
            solved = solve_hinge_tree(props, root(v(1, -2, 3), v(2, 1, -3), TURN), tree,
                                      rates, efforts, external, None)
            self.assertEqual(solved.root_support_wrench_about_com, ZERO_LOAD)
            self.check_physics(props, tree, rates, efforts, external, solved)

    def test_uniform_gravity_gives_free_fall_not_joint_motion(self):
        gravity = v(0, 0, F(-981, 100))
        tree = (link(basis=TURN), link(parent=1, basis=TIP))
        external = tuple(Wrench(gravity, Z) for _ in range(3))
        solved = solve_hinge_tree(UNIT, root(), tree, (F(0),) * 2, (F(0),) * 2, external, None)
        for body in solved.motions:
            self.assertEqual(body.origin.acceleration_metres_per_second_squared, gravity)
            self.assertEqual(body.angular_acceleration_radians_per_second_squared, Z)
        self.assertEqual(solved.joint_accelerations_radians_per_second_squared, (F(0), F(0)))

    def test_disconnected_load_does_not_accelerate_other_body(self):
        external = Wrench(v(0, 1), Z)
        unloaded = solve_hinge_tree(UNIT, root(), (), (), (), (ZERO_LOAD,), None)
        loaded = solve_hinge_tree(UNIT, root(), (), (), (), (external,), None)
        self.assertEqual(unloaded.motions[0].origin.acceleration_metres_per_second_squared, Z)
        self.assertEqual(loaded.motions[0].origin.acceleration_metres_per_second_squared, v(0, 1))

    def test_geometry_graph_and_scalar_admission(self):
        with self.assertRaises(ValueError):
            replace(link(), parent_axis=v(1))
        with self.assertRaises(ValueError):
            replace(link(), child_axis=v(0, 0, 2))
        with self.assertRaises(ValueError):
            solve_hinge_tree(UNIT, root(), (link(parent=1),), (F(0),), (F(0),), (ZERO_LOAD,) * 2, None)
        with self.assertRaises(ValueError):
            solve_hinge_tree(UNIT, root(), (link(),), (), (F(0),), (ZERO_LOAD,) * 2, None)
        with self.assertRaises(TypeError):
            solve_hinge_tree(UNIT, root(), [link()], (F(0),), (F(0),), (ZERO_LOAD,) * 2, None)
        with self.assertRaises(TypeError):
            solve_hinge_tree(UNIT, root(), (link(),), (0.0,), (F(0),), (ZERO_LOAD,) * 2, None)

    def test_overflow_refuses_with_unchanged_inputs(self):
        props = MassProperties(F(1, 2**200), v(1, 1, 1))
        initial = root()
        before = repr(initial)
        with self.assertRaises(ValueError):
            solve_hinge_tree(props, initial, (), (), (), (Wrench(v(2**100), Z),), None)
        self.assertEqual(repr(initial), before)

    def test_recurrent_pure_solve_retains_no_history_or_time_advance(self):
        tree, rates, efforts, external = (link(),), (F(1),), (F(2),), (ZERO_LOAD,) * 2
        initial = root()
        expected = solve_hinge_tree(UNIT, initial, tree, rates, efforts, external, None)
        for _ in range(5):
            self.assertEqual(solve_hinge_tree(UNIT, initial, tree, rates, efforts, external, None), expected)
        self.assertTrue(all(body.origin.time_microseconds == initial.origin.time_microseconds for body in expected.motions))
        self.assertEqual(initial, root())


if __name__ == "__main__":
    unittest.main()
