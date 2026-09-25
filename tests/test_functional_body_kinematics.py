"""Mechanical falsifiers only: no organism, world, caretaker or network boot.

Run directly with Python's unittest runner, avoiding the repository's autouse
caretaker fixture. These proofs do NOT establish a mounted sense or learning.
"""

from dataclasses import replace
from fractions import Fraction as F
import unittest

from dsf_ai_service.substrate.body_surface_contact import ExactVector3, MAX_CONTACT_RATIONAL_BITS
from dsf_ai_service.substrate.functional_body_kinematics import (
    PointMotion, RigidBasis, RigidMotion, compose_motion, inertial_evidence,
)


def vector(x=0, y=0, z=0):
    return ExactVector3(F(x), F(y), F(z))


ZERO = vector()
IDENTITY = RigidBasis(vector(1, 0, 0), vector(0, 1, 0), vector(0, 0, 1))
YAW_90 = RigidBasis(vector(0, 1, 0), vector(-1, 0, 0), vector(0, 0, 1))


def motion(position=ZERO, velocity=ZERO, acceleration=ZERO, omega=ZERO,
           alpha=ZERO, basis=IDENTITY, time=F(250_000)):
    return RigidMotion(PointMotion(time, position, velocity, acceleration), basis, omega, alpha)


class FunctionalBodyKinematicsTests(unittest.TestCase):
    def test_rational_rotation_preserves_length_and_inverse_exactly(self):
        rotation = RigidBasis(vector(F(3, 5), F(4, 5), 0),
                              vector(F(-4, 5), F(3, 5), 0), vector(0, 0, 1))
        local = vector(F(2, 7), F(-4, 9), 3)
        transformed = rotation.to_parent(local)
        self.assertEqual(transformed.dot(transformed), local.dot(local))
        self.assertEqual(rotation.to_local(transformed), local)

    def test_rejects_scaled_reflected_or_nonorthogonal_frames(self):
        for axes in (
            (vector(2, 0, 0), vector(0, 1, 0), vector(0, 0, 1)),
            (vector(1, 0, 0), vector(0, 1, 0), vector(0, 0, -1)),
            (vector(1, 0, 0), vector(1, 0, 0), vector(0, 0, 1)),
        ):
            with self.subTest(axes=axes), self.assertRaises(ValueError):
                RigidBasis(*axes)

    def test_child_translation_uses_parent_orientation(self):
        parent = motion(position=vector(3, 2, 1), basis=YAW_90)
        child = motion(position=vector(2, 0, 0), basis=YAW_90)
        combined = compose_motion(parent, child)
        self.assertEqual(combined.origin.position_metres, vector(3, 4, 1))
        self.assertEqual(combined.at_local_point(vector(1, 0, 0)).position_metres, vector(2, 4, 1))
        self.assertEqual(parent.origin.position_metres, vector(3, 2, 1))

    def test_rotating_site_has_tangential_and_centripetal_acceleration(self):
        point = motion(velocity=vector(5, 0, 0), omega=vector(0, 0, 2),
                       alpha=vector(0, 0, 3)).at_local_point(vector(1, 0, 0))
        self.assertEqual(point.velocity_metres_per_second, vector(5, 2, 0))
        self.assertEqual(point.acceleration_metres_per_second_squared, vector(-4, 3, 0))

    def test_moving_child_includes_coriolis_and_angular_transport(self):
        parent = motion(omega=vector(0, 0, 2), alpha=vector(0, 0, 5))
        child = motion(position=vector(1, 0, 0), velocity=vector(3, 0, 0),
                       omega=vector(0, 7, 0))
        combined = compose_motion(parent, child)
        self.assertEqual(combined.origin.velocity_metres_per_second, vector(3, 2, 0))
        self.assertEqual(combined.origin.acceleration_metres_per_second_squared, vector(-4, 17, 0))
        self.assertEqual(combined.angular_velocity_radians_per_second, vector(0, 7, 2))
        self.assertEqual(combined.angular_acceleration_radians_per_second_squared, vector(-14, 0, 5))

    def test_frame_chain_composition_is_associative(self):
        a = motion(position=vector(1, 2, 3), omega=vector(1, 2, 0), basis=YAW_90)
        b = motion(position=vector(2, 1, 0), velocity=vector(1, 0, 2), omega=vector(0, 1, 2))
        c = motion(position=vector(1, 3, 2), acceleration=vector(1, 1, 0), basis=YAW_90)
        self.assertEqual(compose_motion(compose_motion(a, b), c), compose_motion(a, compose_motion(b, c)))

    def test_standing_and_free_fall_are_distinct(self):
        gravity = vector(0, 0, F(-981, 100))  # declared test environment, not a production default
        standing = inertial_evidence(motion(), ZERO, gravity)
        falling = inertial_evidence(motion(acceleration=gravity), ZERO, gravity)
        self.assertEqual(standing.specific_force_metres_per_second_squared, vector(0, 0, F(981, 100)))
        self.assertEqual(falling.specific_force_metres_per_second_squared, ZERO)

    def test_sensor_axes_and_rotation_offset_are_preserved(self):
        tipped = RigidBasis(vector(0, 0, -1), vector(0, 1, 0), vector(1, 0, 0))
        reading = inertial_evidence(motion(basis=tipped, omega=vector(0, 0, 2)),
                                    vector(0, 0, 1), vector(0, 0, -10))
        self.assertEqual(reading.specific_force_metres_per_second_squared, vector(-10, 0, -4))
        self.assertEqual(reading.angular_velocity_radians_per_second, vector(-2, 0, 0))

    def test_mixed_physical_times_refuse(self):
        with self.assertRaises(ValueError):
            compose_motion(motion(time=F(1)), motion(time=F(2)))
        with self.assertRaises(ValueError):
            motion(time=F(-1))

    def test_inexact_and_oversized_inputs_refuse(self):
        with self.assertRaises(TypeError):
            motion(position=ExactVector3(0.1, F(0), F(0)))
        with self.assertRaises(ValueError):
            motion(position=vector(1 << MAX_CONTACT_RATIONAL_BITS, 0, 0))

    def test_oversized_output_refuses_without_mutating_input(self):
        large = motion(position=vector(1 << (MAX_CONTACT_RATIONAL_BITS - 1), 0, 0))
        before = large
        with self.assertRaises(ValueError):
            compose_motion(large, large)
        self.assertEqual(before, large)

    def test_repeated_sampling_retains_no_history_and_changes_no_motion(self):
        body = motion(omega=vector(0, 0, 2))
        unchanged = replace(body)
        expected = inertial_evidence(body, vector(1, 0, 0), vector(0, 0, -10))
        for _ in range(100):
            self.assertEqual(inertial_evidence(body, vector(1, 0, 0), vector(0, 0, -10)), expected)
        self.assertEqual(body, unchanged)
        self.assertFalse(hasattr(body, "__dict__"))


if __name__ == "__main__":
    unittest.main()
