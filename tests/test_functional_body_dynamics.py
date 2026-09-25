"""Standalone mechanical proofs: no world, network, caretaker or pytest fixtures.

All loads/motions below are controlled mechanical boundary conditions. These
tests do not demonstrate autonomous body action, motor learning or deployment.
"""

from dataclasses import replace
from fractions import Fraction as F
import unittest

from dsf_ai_service.substrate.body_surface_contact import ExactVector3, ZERO_VECTOR as Z
from dsf_ai_service.substrate.functional_body_kinematics import (
    PointMotion, RigidBasis, RigidMotion, _cross, inertial_evidence,
)
from dsf_ai_service.substrate.functional_body_dynamics import (
    MassProperties, Wrench, accelerated_motion, joint_torque_pair,
    kinetic_energy_joules, required_wrench,
)


def v(x=0, y=0, z=0):
    return ExactVector3(F(x), F(y), F(z))


IDENTITY = RigidBasis(v(1), v(0, 1), v(0, 0, 1))
ROTATED = RigidBasis(v(F(3, 5), F(4, 5)), v(F(-4, 5), F(3, 5)), v(0, 0, 1))


def motion(basis=IDENTITY, velocity=Z, omega=Z, acceleration=Z, alpha=Z):
    return RigidMotion(PointMotion(F(123), v(1, 2, 3), velocity, acceleration), basis, omega, alpha)


class FunctionalBodyDynamicsTests(unittest.TestCase):
    def test_newton_euler_round_trip_regimes(self):
        # Unequal inertias, non-principal spins, both directions and rest.
        for mass in (F(1, 10), F(2), F(100)):
            for inertia in (v(1, 1, 1), v(1, 2, 3), v(5, 6, 7)):
                props = MassProperties(mass, inertia)
                for basis in (IDENTITY, ROTATED):
                    for sign in (-1, 0, 1):
                        original = motion(basis, v(2, 3, 4), v(sign, 2, -3), v(-1, 2, 3), v(4, -2, 1))
                        solved = accelerated_motion(props, original, required_wrench(props, original))
                        self.assertEqual(solved, original)

    def test_torque_free_asymmetric_spin_keeps_gyroscopic_term(self):
        props = MassProperties(F(2), v(1, 2, 3))
        result = accelerated_motion(props, motion(omega=v(1, 2, 3)), Wrench(Z, Z))
        self.assertEqual(result.angular_acceleration_radians_per_second_squared, v(-6, 3, F(-2, 3)))
        omega = result.angular_velocity_radians_per_second
        alpha = result.angular_acceleration_radians_per_second_squared
        self.assertEqual(omega.dot(props.momentum(alpha)), 0)

    def test_applied_power_equals_kinetic_energy_derivative(self):
        props = MassProperties(F(7, 3), v(2, 3, 4))
        initial = motion(ROTATED, v(1, -2, 3), v(-3, 4, 1))
        load = Wrench(v(5, -2, 7), v(3, -8, 4))
        result = accelerated_motion(props, initial, load)
        omega = result.basis.to_local(result.angular_velocity_radians_per_second)
        alpha = result.basis.to_local(result.angular_acceleration_radians_per_second_squared)
        derivative = (props.mass_kilograms * result.origin.velocity_metres_per_second.dot(
            result.origin.acceleration_metres_per_second_squared) + omega.dot(props.momentum(alpha)))
        self.assertEqual(derivative, load.power_watts(initial.origin.velocity_metres_per_second,
                                                    initial.angular_velocity_radians_per_second))

    def test_force_at_hand_site_returns_torque_and_site_acceleration(self):
        props = MassProperties(F(2), v(1, 2, 3))
        offset = v(1)
        site_load = Wrench(v(0, 6), Z)
        com_load = site_load.shifted(offset.scaled(F(-1)))
        self.assertEqual(com_load.torque_newton_metres, v(0, 0, 6))
        body = accelerated_motion(props, motion(), com_load)
        self.assertEqual(body.origin.acceleration_metres_per_second_squared, v(0, 3))
        self.assertEqual(body.angular_acceleration_radians_per_second_squared, v(0, 0, 2))
        self.assertEqual(body.at_local_point(offset).acceleration_metres_per_second_squared, v(0, 5))
        self.assertEqual(inertial_evidence(body, offset, Z).specific_force_metres_per_second_squared, v(0, 5))

    def test_origin_shift_preserves_power(self):
        load = Wrench(v(2, -3, 4), v(5, 1, -2))
        delta, velocity, omega = v(-2, 3, 1), v(1, 4, -2), v(3, -1, 2)
        self.assertEqual(load.power_watts(velocity, omega),
                         load.shifted(delta).power_watts(velocity + _cross(omega, delta), omega))
        self.assertEqual(load.shifted(delta).shifted(delta.scaled(F(-1))), load)

    def test_coordinate_rotation_preserves_power_and_load_acceleration(self):
        props = MassProperties(F(2), v(1, 2, 3))
        original = motion(velocity=v(2, -1, 3), omega=v(1, 3, -2))
        load = Wrench(v(3, 2, -4), v(1, 5, 2))
        result = accelerated_motion(props, original, load)
        rotated = motion(ROTATED, ROTATED.to_parent(original.origin.velocity_metres_per_second),
                         ROTATED.to_parent(original.angular_velocity_radians_per_second))
        solved = accelerated_motion(props, rotated, load.to_parent(ROTATED))
        self.assertEqual(solved.origin.acceleration_metres_per_second_squared,
                         ROTATED.to_parent(result.origin.acceleration_metres_per_second_squared))
        self.assertEqual(solved.angular_acceleration_radians_per_second_squared,
                         ROTATED.to_parent(result.angular_acceleration_radians_per_second_squared))
        self.assertEqual(kinetic_energy_joules(props, original), kinetic_energy_joules(props, rotated))
        self.assertEqual(load.power_watts(original.origin.velocity_metres_per_second,
                                         original.angular_velocity_radians_per_second),
                         load.to_parent(ROTATED).power_watts(rotated.origin.velocity_metres_per_second,
                                                           rotated.angular_velocity_radians_per_second))

    def test_joint_pair_reciprocity_and_relative_power(self):
        axis, effort = v(F(3, 5), F(4, 5)), F(7, 2)
        child, parent = joint_torque_pair(axis, effort)
        wc, wp = v(1, 2, 3), v(3, -1, 2)
        self.assertEqual(child + parent, Wrench(Z, Z))
        self.assertEqual(child.power_watts(Z, wc) + parent.power_watts(Z, wp), effort * axis.dot(wc - wp))
        self.assertEqual(child.power_watts(Z, wc) + parent.power_watts(Z, wc), 0)

    def test_gravity_only_fall_and_supported_rest_sensory_return(self):
        props = MassProperties(F(3), v(2, 2, 2))
        gravity = v(0, 0, F(-981, 100))
        weight = Wrench(gravity.scaled(props.mass_kilograms), Z)
        falling = accelerated_motion(props, motion(), weight)
        supported = accelerated_motion(props, motion(), weight + weight.opposite())
        self.assertEqual(inertial_evidence(falling, Z, gravity).specific_force_metres_per_second_squared, Z)
        self.assertEqual(inertial_evidence(supported, Z, gravity).specific_force_metres_per_second_squared,
                         gravity.scaled(F(-1)))

    def test_energy_retains_translation_and_rotation(self):
        props = MassProperties(F(2), v(1, 2, 3))
        self.assertEqual(kinetic_energy_joules(props, motion(velocity=v(3), omega=v(0, 0, 2))), F(15))

    def test_nonphysical_or_inexact_inputs_refuse(self):
        for inertia in (v(0, 1, 1), v(-1, 1, 1), v(1, 1, 3)):
            with self.assertRaises(ValueError):
                MassProperties(F(1), inertia)
        with self.assertRaises(ValueError):
            MassProperties(F(0), v(1, 1, 1))
        with self.assertRaises(TypeError):
            MassProperties(1.0, v(1, 1, 1))
        with self.assertRaises(ValueError):
            joint_torque_pair(v(2), F(1))
        with self.assertRaises(TypeError):
            joint_torque_pair(v(1), 1.0)

    def test_output_overflow_refuses_without_mutating_input(self):
        props = MassProperties(F(1, 2**200), v(1, 1, 1))
        initial = motion()
        before = repr(initial)
        with self.assertRaises(ValueError):
            accelerated_motion(props, initial, Wrench(v(2**100), Z))
        self.assertEqual(repr(initial), before)
        with self.assertRaises(ValueError):
            kinetic_energy_joules(MassProperties(F(1), v(1, 1, 1)), motion(velocity=v(2**200)))

    def test_repeated_stateless_calls_do_not_advance_clock_or_pose(self):
        props, initial, load = MassProperties(F(2), v(1, 2, 3)), motion(), Wrench(v(2), v(0, 0, 3))
        expected = accelerated_motion(props, initial, load)
        for _ in range(100):
            self.assertEqual(accelerated_motion(props, initial, load), expected)
        self.assertEqual(expected.origin.time_microseconds, initial.origin.time_microseconds)
        self.assertEqual(expected.origin.position_metres, initial.origin.position_metres)
        self.assertEqual(expected.origin.velocity_metres_per_second, initial.origin.velocity_metres_per_second)
        self.assertEqual(initial, motion())


if __name__ == "__main__":
    unittest.main()
