"""Instantaneous rigid-segment forces and energy; not a movement controller.

SI units throughout. RigidMotion origins MUST be centres of mass and their
local axes MUST be the declared principal inertia axes. Net loads are supplied
explicitly, including gravity, contact and joint reactions. No unknown load is
defaulted, and inverse dynamics never authorizes execution of a desired pose.

Exact for admitted rational instantaneous states, not a finite-time integrator,
muscle/metabolic law, constraint solver or production-mounted body. Reuses the
existing bounded contact arithmetic and mechanical frame representation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from dsf_ai_service.substrate.body_surface_contact import (
    ExactVector3,
    ZERO_VECTOR,
    _require_fraction,
    _validate_vector,
)
from dsf_ai_service.substrate.functional_body_kinematics import (
    RigidBasis,
    RigidMotion,
    _cross,
)


@dataclass(frozen=True, slots=True)
class MassProperties:
    """Positive mass and principal moments about the centre of mass.

    Triangle inequalities exclude tensors impossible for a nonnegative mass
    distribution. Equality admits a planar lamina; zero moments (singular
    point/line bodies) are not supported by this invertible segment law.
    """

    mass_kilograms: Fraction
    principal_inertia_kilogram_metres_squared: ExactVector3

    def __post_init__(self) -> None:
        _require_fraction(self.mass_kilograms, "segment mass", positive=True)
        inertia = self.principal_inertia_kilogram_metres_squared
        _validate_vector(inertia, "principal inertia")
        values = (inertia.x, inertia.y, inertia.z)
        if min(values) <= 0 or 2 * max(values) > sum(values):
            raise ValueError("principal inertia must be positive and physically realizable")

    def momentum(self, angular_velocity_local: ExactVector3) -> ExactVector3:
        """Local angular momentum in kg m^2/s, not a retained record."""
        _validate_vector(angular_velocity_local, "local angular velocity")
        inertia = self.principal_inertia_kilogram_metres_squared
        result = ExactVector3(
            inertia.x * angular_velocity_local.x,
            inertia.y * angular_velocity_local.y,
            inertia.z * angular_velocity_local.z,
        )
        _validate_vector(result, "angular momentum")
        return result


@dataclass(frozen=True, slots=True)
class Wrench:
    """Force and moment about ONE origin, expressed in ONE common frame.

    The caller supplies the geometrically correct origin/frame relationship.
    No names, frame registries, identity hashes or hidden transform lookup.
    """

    force_newtons: ExactVector3
    torque_newton_metres: ExactVector3

    def __post_init__(self) -> None:
        _validate_vector(self.force_newtons, "force")
        _validate_vector(self.torque_newton_metres, "torque")

    def __add__(self, other: Wrench) -> Wrench:
        """Combine loads only after expressing them about the same origin."""
        return Wrench(
            self.force_newtons + other.force_newtons,
            self.torque_newton_metres + other.torque_newton_metres,
        )

    def opposite(self) -> Wrench:
        return Wrench(
            self.force_newtons.scaled(Fraction(-1)),
            self.torque_newton_metres.scaled(Fraction(-1)),
        )

    def shifted(self, old_to_new_origin_metres: ExactVector3) -> Wrench:
        """Same physical load about a new origin; components keep their axes."""
        _validate_vector(old_to_new_origin_metres, "origin displacement")
        return Wrench(
            self.force_newtons,
            self.torque_newton_metres - _cross(old_to_new_origin_metres, self.force_newtons),
        )

    def to_parent(self, basis: RigidBasis) -> Wrench:
        """Rotate force and moment without changing their physical origin."""
        return Wrench(
            basis.to_parent(self.force_newtons),
            basis.to_parent(self.torque_newton_metres),
        )

    def power_watts(self, origin_velocity: ExactVector3, angular_velocity: ExactVector3) -> Fraction:
        """Instantaneous mechanical power, NOT metabolic consumption."""
        _validate_vector(origin_velocity, "load origin velocity")
        _validate_vector(angular_velocity, "load angular velocity")
        return _require_fraction(
            self.force_newtons.dot(origin_velocity)
            + self.torque_newton_metres.dot(angular_velocity),
            "mechanical power",
        )


def required_wrench(properties: MassProperties, motion: RigidMotion) -> Wrench:
    """Net load about COM required by the supplied actual acceleration.

    All motion derivatives are in an inertial parent frame. This calculation
    does not turn desired kinematics into an applied force or physical action.
    """
    omega = motion.basis.to_local(motion.angular_velocity_radians_per_second)
    alpha = motion.basis.to_local(motion.angular_acceleration_radians_per_second_squared)
    torque_local = properties.momentum(alpha) + _cross(omega, properties.momentum(omega))
    return Wrench(
        motion.origin.acceleration_metres_per_second_squared.scaled(properties.mass_kilograms),
        motion.basis.to_parent(torque_local),
    )


def accelerated_motion(
    properties: MassProperties, motion: RigidMotion, net_load_about_com: Wrench,
) -> RigidMotion:
    """Solve this instant's acceleration; do NOT advance time, pose or speed.

    Replaces only acceleration fields. The caller still owes joint/contact
    constraints and time integration before any successor can be published.
    In particular, this is NOT independent-limb forward dynamics of a chain.
    """
    omega = motion.basis.to_local(motion.angular_velocity_radians_per_second)
    torque = motion.basis.to_local(net_load_about_com.torque_newton_metres)
    effective = torque - _cross(omega, properties.momentum(omega))
    inertia = properties.principal_inertia_kilogram_metres_squared
    alpha = ExactVector3(effective.x / inertia.x, effective.y / inertia.y, effective.z / inertia.z)
    return replace(
        motion,
        origin=replace(
            motion.origin,
            acceleration_metres_per_second_squared=net_load_about_com.force_newtons.scaled(
                1 / properties.mass_kilograms
            ),
        ),
        angular_acceleration_radians_per_second_squared=motion.basis.to_parent(alpha),
    )


def kinetic_energy_joules(properties: MassProperties, motion: RigidMotion) -> Fraction:
    """COM translation plus complete principal-axis rotational energy."""
    velocity = motion.origin.velocity_metres_per_second
    omega = motion.basis.to_local(motion.angular_velocity_radians_per_second)
    return _require_fraction(
        (properties.mass_kilograms * velocity.dot(velocity)
         + omega.dot(properties.momentum(omega))) / 2,
        "kinetic energy", nonnegative=True,
    )


def joint_torque_pair(axis: ExactVector3, torque_newton_metres: Fraction) -> tuple[Wrench, Wrench]:
    """Equal/opposite pure torques in common axes, first on child then parent.

    Axis is an actual unit joint axis. Effort is already physical, not a motor
    request with invented strength/efficiency. Bearing reactions are separate
    constraint loads; a pure torque pair does not constrain the joint itself.
    """
    _validate_vector(axis, "joint axis")
    if axis.dot(axis) != 1:
        raise ValueError("joint axis must have exact unit length")
    _require_fraction(torque_newton_metres, "joint torque")
    child = Wrench(ZERO_VECTOR, axis.scaled(torque_newton_metres))
    return child, child.opposite()
