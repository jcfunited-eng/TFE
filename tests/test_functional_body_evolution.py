"""Standalone free-body integration proofs; never import the organism/world.

All dimensions/loads/tolerances below describe analytic TEST bodies, not Guala's
anatomy, production error budgets or learned motor behavior.
"""
from dataclasses import fields, replace
from fractions import Fraction as F
import json
import math
import unittest

from dsf_ai_service.substrate.body_surface_contact import ExactVector3, ZERO_VECTOR
from dsf_ai_service.substrate.functional_body_kinematics import RigidBasis, PointMotion, RigidMotion
from dsf_ai_service.substrate.functional_body_dynamics import MassProperties, Wrench
from dsf_ai_service.substrate.functional_body_articulation import HingeSegment, solve_hinge_tree
from dsf_ai_service.substrate.functional_body_evolution import (
    BodyState, EvolutionLimits, FreeHingeBody,
)

Z = (0.0, 0.0, 0.0)
Q = (1.0, 0.0, 0.0, 0.0)
LOAD = (0.0,)*6


def ev(x=0, y=0, z=0):
    return ExactVector3(F(x), F(y), F(z))


BASIS = RigidBasis(ev(1), ev(0, 1), ev(0, 0, 1))


def properties(mass=1, inertia=(1, 1, 1)):
    return MassProperties(F(mass), ev(*inertia))


def link(parent=0, parent_anchor=ev(1), child_anchor=ev(-1)):
    return HingeSegment(parent, properties(), parent_anchor, child_anchor,
                        ev(0, 0, 1), ev(0, 0, 1), BASIS)


def state(joints=0, **changes):
    base = BodyState(0, Z, Q, Z, Z, (0.0,)*joints, (0.0,)*joints)
    return replace(base, **changes)


def limits(tolerance=1e-7, steps=64):
    return EvolutionLimits(tolerance, tolerance, tolerance, tolerance,
                           tolerance, tolerance, tolerance, steps)


class EvolutionProof(unittest.TestCase):
    def assertVectorClose(self, a, b, tolerance=1e-11):
        self.assertLessEqual(math.hypot(*(x-y for x, y in zip(a, b))), tolerance)

    def test_analytic_free_fall_and_external_work(self):
        model = FreeHingeBody(properties(2), ())
        initial = state()
        result = model.advance(initial, 250000, ((0.0, 0.0, 0.0, 0.0, 0.0, -20.0),),
                               (), subdivisions=2, limits=limits(1e-12))
        self.assertVectorClose(result.state.root_position_metres, (0.0, 0.0, -0.3125))
        self.assertVectorClose(result.state.root_velocity_metres_per_second, (0.0, 0.0, -2.5))
        self.assertEqual(result.state.time_microseconds, 250000)
        self.assertLess(abs(result.energy_work_residual_joules), 1e-12)
        self.assertVectorClose(result.linear_momentum_residual_kg_metres_per_second, Z)
        self.assertEqual(initial, state())

    def test_rest_and_constant_translation(self):
        model = FreeHingeBody(properties(), ())
        for velocity in (Z, (1.0, 2.0, -3.0)):
            initial = state(root_velocity_metres_per_second=velocity)
            result = model.advance(initial, 1000000, (LOAD,), (), subdivisions=1, limits=limits(1e-12))
            self.assertVectorClose(result.state.root_position_metres, velocity)
            self.assertEqual(result.state.root_velocity_metres_per_second, velocity)
            self.assertEqual(result.state.root_quaternion, Q)

    def test_numeric_instant_matches_exact_moving_offset_hinge(self):
        anatomy = (link(),)
        model = FreeHingeBody(properties(), anatomy)
        initial = state(1, root_velocity_metres_per_second=(0.25, -0.5, 0.75),
                        root_angular_velocity_radians_per_second=(0.5, 0.25, 0.75),
                        joint_rates_radians_per_second=(0.5,))
        exact_root = RigidMotion(PointMotion(F(0), ZERO_VECTOR, ev(F(1,4), F(-1,2), F(3,4)),
                                            ZERO_VECTOR), BASIS, ev(F(1,2), F(1,4), F(3,4)), ZERO_VECTOR)
        exact = solve_hinge_tree(properties(), exact_root, anatomy, (F(1,2),), (F(1,3),),
                                 (Wrench(ZERO_VECTOR, ZERO_VECTOR), Wrench(ev(0, 1), ZERO_VECTOR)), None)
        derivative = model._derivative(initial._values(),
                                       (LOAD, (0.0, 0.0, 0.0, 0.0, 1.0, 0.0)), (1/3,))
        linear = exact.motions[0].origin.acceleration_metres_per_second_squared
        angular = exact.motions[0].angular_acceleration_radians_per_second_squared
        self.assertVectorClose(derivative[7:10], tuple(float(v) for v in (linear.x, linear.y, linear.z)))
        self.assertVectorClose(derivative[10:13], tuple(float(v) for v in (angular.x, angular.y, angular.z)))
        self.assertAlmostEqual(derivative[14], float(exact.joint_accelerations_radians_per_second_squared[0]), places=12)

    def test_internal_motor_torque_has_equal_opposite_response(self):
        model = FreeHingeBody(properties(), (link(parent_anchor=ev(), child_anchor=ev()),))
        result = model.advance(state(1), 250000, (LOAD, LOAD), (1.0,),
                               subdivisions=8, limits=limits(1e-9))
        self.assertVectorClose(result.state.root_angular_velocity_radians_per_second, (0.0, 0.0, -0.25))
        self.assertAlmostEqual(result.state.joint_rates_radians_per_second[0], 0.5, places=12)
        self.assertAlmostEqual(result.state.joint_angles_radians[0], 0.0625, places=12)
        self.assertLess(abs(result.energy_work_residual_joules), 1e-10)
        self.assertVectorClose(result.angular_momentum_residual_kg_metres_squared_per_second, Z)

    def test_link_anchors_stay_joined_during_finite_motion(self):
        model = FreeHingeBody(properties(), (link(), link(1)))
        current = state(2, root_angular_velocity_radians_per_second=(0.1, 0.2, 0.3),
                        joint_rates_radians_per_second=(0.4, -0.2))
        for _ in range(8):
            current = model.advance(current, 10000, (LOAD,)*3, (0.1, -0.1),
                                    subdivisions=2, limits=limits(1e-8)).state
            p, bases, velocities, omega, _, _, _ = model._kinematics(current._values())
            for j, (parent, pa, ca, axis, rest) in enumerate(model.hinges, 1):
                parent_arm = tuple(sum(bases[parent][k][i]*pa[k] for k in range(3)) for i in range(3))
                child_arm = tuple(sum(bases[j][k][i]*ca[k] for k in range(3)) for i in range(3))
                self.assertVectorClose(tuple(p[parent][i]+parent_arm[i] for i in range(3)),
                                       tuple(p[j][i]+child_arm[i] for i in range(3)), 1e-12)
                def site_velocity(v, w, r):
                    return (v[0]+w[1]*r[2]-w[2]*r[1],
                            v[1]+w[2]*r[0]-w[0]*r[2],
                            v[2]+w[0]*r[1]-w[1]*r[0])
                self.assertVectorClose(site_velocity(velocities[parent], omega[parent], parent_arm),
                                       site_velocity(velocities[j], omega[j], child_arm), 1e-12)

    def test_asymmetric_tumbling_refines_and_conserves(self):
        model = FreeHingeBody(properties(inertia=(2, 3, 4)), ())
        initial = state(root_angular_velocity_radians_per_second=(2.0, 3.0, 4.0))
        coarse = model.advance(initial, 100000, (LOAD,), (), subdivisions=1, limits=limits(1.0))
        fine = model.advance(initial, 100000, (LOAD,), (), subdivisions=4, limits=limits(1.0))
        self.assertLess(fine.angle_refinement_radians, coarse.angle_refinement_radians / 4)
        self.assertLess(abs(fine.energy_work_residual_joules), abs(coarse.energy_work_residual_joules) / 4)
        self.assertLess(fine.angular_velocity_refinement_radians_per_second,
                        coarse.angular_velocity_refinement_radians_per_second / 4)

    def test_declared_rate_and_interval_regimes(self):
        model = FreeHingeBody(properties(), ())
        for rate in (0.1, 1.0, 10.0):
            for duration in (1000, 10000, 250000):
                with self.subTest(rate=rate, microseconds=duration):
                    initial = state(root_angular_velocity_radians_per_second=(0.0, 0.0, rate))
                    result = model.advance(initial, duration, (LOAD,), (),
                                           subdivisions=16, limits=limits(1e-6))
                    angle = rate * duration / 1e6
                    expected = (math.cos(angle/2), 0.0, 0.0, math.sin(angle/2))
                    self.assertVectorClose(result.state.root_quaternion, expected, 1e-6)

    def test_long_recurrence_bounded_state_and_global_energy(self):
        model = FreeHingeBody(properties(), ())
        initial = state(root_angular_velocity_radians_per_second=(0.0, 0.0, 10.0))
        current = initial
        for _ in range(100):
            current = model.advance(current, 10000, (LOAD,), (), subdivisions=2, limits=limits(1e-7)).state
        self.assertEqual(current.time_microseconds, 1000000)
        self.assertEqual(len(current._values()), len(initial._values()))
        self.assertTrue(all(type(x) is float for x in current._values()))
        self.assertVectorClose(current.root_quaternion, (math.cos(5), 0.0, 0.0, math.sin(5)), 1e-7)
        self.assertAlmostEqual(model._measure(current._values())[0], model._measure(initial._values())[0], places=12)

    def test_identical_serialized_current_state_replays_exactly(self):
        model = FreeHingeBody(properties(), (link(),))
        saved = model.advance(state(1), 10000, (LOAD, LOAD), (0.1,),
                              subdivisions=2, limits=limits()).state
        # Representation round trip only, NOT production world-authority restore.
        record = {f.name: getattr(saved, f.name) for f in fields(saved)}
        decoded = json.loads(json.dumps(record, allow_nan=False))
        restored = BodyState(**{k: tuple(v) if isinstance(v, list) else v for k, v in decoded.items()})
        self.assertEqual(saved, restored)
        left = model.advance(saved, 10000, (LOAD, LOAD), (0.1,), subdivisions=2, limits=limits())
        right = model.advance(restored, 10000, (LOAD, LOAD), (0.1,), subdivisions=2, limits=limits())
        self.assertEqual(left, right)

    def test_accuracy_refusal_does_not_publish_or_modify(self):
        model = FreeHingeBody(properties(inertia=(2, 3, 4)), ())
        initial = state(root_angular_velocity_radians_per_second=(2.0, 3.0, 4.0))
        values = initial._values()
        # This test targets integration error, not initial representation:
        # omega's combined ULP spacing is already about 1.088e-15 rad/s.
        accuracy = replace(limits(1e-15), angular_velocity_radians_per_second=1e-12)
        with self.assertRaisesRegex(ValueError, "accuracy/conservation"):
            model.advance(initial, 250000, (LOAD,), (), subdivisions=1, limits=accuracy)
        self.assertEqual(initial._values(), values)

    def test_invalid_state_load_budget_and_clock_refuse(self):
        model = FreeHingeBody(properties(), ())
        for changes in ({"root_quaternion": (0.0,)*4},
                        {"root_position_metres": (float("nan"), 0.0, 0.0)}):
            with self.assertRaises(ValueError):
                state(**changes)
        with self.assertRaisesRegex(ValueError, "budget"):
            model.advance(state(), 10000, (LOAD,), (), subdivisions=2, limits=limits(steps=2))
        with self.assertRaises(ValueError):
            model.advance(state(), 10000, ((float("inf"),)*6,), (), subdivisions=1, limits=limits())
        with self.assertRaises(ValueError):
            model.advance(state(), 0, (LOAD,), (), subdivisions=1, limits=limits())
        with self.assertRaises(ValueError):
            model.advance(state(), 10000, (), (), subdivisions=1, limits=limits())

    def test_large_coordinates_and_joint_angles_cannot_silently_freeze(self):
        model = FreeHingeBody(properties(), ())
        translated = state(root_position_metres=(float(2**60), 0.0, 0.0),
                           root_velocity_metres_per_second=(1.0, 0.0, 0.0))
        self.assertEqual(math.ulp(translated.root_position_metres[0]), 256.0)
        with self.assertRaisesRegex(ValueError, "spacing"):
            model.advance(translated, 1000000, (LOAD,), (), subdivisions=1, limits=limits())
        hinged = FreeHingeBody(properties(), (link(parent_anchor=ev(), child_anchor=ev()),))
        turned = state(1, joint_angles_radians=(float(2**60),), joint_rates_radians_per_second=(1.0,))
        with self.assertRaisesRegex(ValueError, "spacing"):
            hinged.advance(turned, 1000000, (LOAD, LOAD), (0.0,), subdivisions=1, limits=limits())
        with self.assertRaisesRegex(ValueError, "spacing"):
            model.advance(state(), 10000, (LOAD,), (), subdivisions=1, limits=limits(1e-20))

    def test_nonparallel_rotated_hinges_match_exact_instant(self):
        rest = RigidBasis(ev(0, 1), ev(-1), ev(0, 0, 1))
        first = HingeSegment(0, properties(inertia=(2, 3, 4)), ev(1, 2), ev(0, -1),
                             ev(1), ev(0, -1), rest)
        second = HingeSegment(1, properties(), ev(0, 1), ev(0, 0, -1),
                              ev(0, 0, 1), ev(0, 0, 1), BASIS)
        anatomy = (first, second)
        root = properties(2, (2, 3, 4))
        model = FreeHingeBody(root, anatomy)
        initial = state(2, root_angular_velocity_radians_per_second=(0.5, 0.25, 0.75),
                        joint_rates_radians_per_second=(0.5, -0.25))
        exact_root = RigidMotion(PointMotion(F(0), ZERO_VECTOR, ZERO_VECTOR, ZERO_VECTOR),
                                 BASIS, ev(F(1,2), F(1,4), F(3,4)), ZERO_VECTOR)
        exact = solve_hinge_tree(root, exact_root, anatomy, (F(1,2), F(-1,4)), (F(1,3), F(-1,2)),
                                 (Wrench(ZERO_VECTOR, ZERO_VECTOR), Wrench(ZERO_VECTOR, ZERO_VECTOR),
                                  Wrench(ev(0, 1), ZERO_VECTOR)), None)
        derivative = model._derivative(initial._values(),
                                       (LOAD, LOAD, (0.0, 0.0, 0.0, 0.0, 1.0, 0.0)), (1/3, -0.5))
        linear = exact.motions[0].origin.acceleration_metres_per_second_squared
        angular = exact.motions[0].angular_acceleration_radians_per_second_squared
        self.assertVectorClose(derivative[7:10], tuple(float(v) for v in (linear.x, linear.y, linear.z)))
        self.assertVectorClose(derivative[10:13], tuple(float(v) for v in (angular.x, angular.y, angular.z)))
        self.assertVectorClose(derivative[15:17], tuple(float(v) for v in exact.joint_accelerations_radians_per_second_squared))


if __name__ == "__main__":
    unittest.main()
