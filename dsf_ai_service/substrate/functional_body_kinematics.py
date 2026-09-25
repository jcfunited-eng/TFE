"""Exact instantaneous rigid-link kinematics and passive inertial evidence.

This is mechanical infrastructure, not an action selector or a dynamics solver.
The caller supplies actual motion in metres, seconds and radians at one common
physical time. No endpoint interpolation, desired motion, default gravity,
body-age rule, semantic action or organ/neuron response is manufactured here.

Rational rigid bases preserve exact geometry admitted by the existing contact
arithmetic boundary. Arbitrary real rotations and their numerical evolution are
outside this module. No state, trajectory history or second organism is retained.
This foundation is not yet mounted in Guala's production motor/sensory loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.substrate.body_surface_contact import (
    ExactVector3,
    _require_fraction,
    _validate_vector,
)


def _cross(a: ExactVector3, b: ExactVector3) -> ExactVector3:
    return ExactVector3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x,
    )


@dataclass(frozen=True, slots=True)
class RigidBasis:
    """Local unit axes expressed in the parent frame (rotation columns)."""

    x: ExactVector3
    y: ExactVector3
    z: ExactVector3

    def __post_init__(self) -> None:
        for axis in (self.x, self.y, self.z):
            _validate_vector(axis, "basis axis")
            if axis.dot(axis) != 1:
                raise ValueError("basis axes must have exact unit length")
        if self.x.dot(self.y) != 0 or _cross(self.x, self.y) != self.z:
            raise ValueError("basis must be orthogonal and right-handed")

    def to_parent(self, vector: ExactVector3) -> ExactVector3:
        _validate_vector(vector, "local vector")
        result = (
            self.x.scaled(vector.x)
            + self.y.scaled(vector.y)
            + self.z.scaled(vector.z)
        )
        _validate_vector(result, "rotated vector")
        return result

    def to_local(self, vector: ExactVector3) -> ExactVector3:
        _validate_vector(vector, "parent vector")
        result = ExactVector3(self.x.dot(vector), self.y.dot(vector), self.z.dot(vector))
        _validate_vector(result, "inverse rotated vector")
        return result


@dataclass(frozen=True, slots=True)
class PointMotion:
    """Actual motion of a point, in its containing reference frame."""

    time_microseconds: Fraction
    position_metres: ExactVector3
    velocity_metres_per_second: ExactVector3
    acceleration_metres_per_second_squared: ExactVector3

    def __post_init__(self) -> None:
        _require_fraction(self.time_microseconds, "physical time", nonnegative=True)
        for vector in (
            self.position_metres,
            self.velocity_metres_per_second,
            self.acceleration_metres_per_second_squared,
        ):
            _validate_vector(vector, "point motion")


@dataclass(frozen=True, slots=True)
class RigidMotion:
    """Origin and angular motion in a parent frame at one physical instant.

    For a root the parent is the world. For a child this is motion relative
    to its parent, with derivatives taken in that rotating parent frame.
    Basis columns describe the link orientation relative to the same parent.
    """

    origin: PointMotion
    basis: RigidBasis
    angular_velocity_radians_per_second: ExactVector3
    angular_acceleration_radians_per_second_squared: ExactVector3

    def __post_init__(self) -> None:
        if not isinstance(self.origin, PointMotion) or not isinstance(self.basis, RigidBasis):
            raise TypeError("rigid motion requires a point motion and rigid basis")
        _validate_vector(self.angular_velocity_radians_per_second, "angular velocity")
        _validate_vector(self.angular_acceleration_radians_per_second_squared, "angular acceleration")

    def at_local_point(self, offset_metres: ExactVector3) -> PointMotion:
        """Kinematics of a site fixed on this link, not a desired movement."""
        r = self.basis.to_parent(offset_metres)
        omega = self.angular_velocity_radians_per_second
        alpha = self.angular_acceleration_radians_per_second_squared
        rotational_velocity = _cross(omega, r)
        return PointMotion(
            self.origin.time_microseconds,
            self.origin.position_metres + r,
            self.origin.velocity_metres_per_second + rotational_velocity,
            self.origin.acceleration_metres_per_second_squared
            + _cross(alpha, r)
            + _cross(omega, rotational_velocity),
        )


def compose_motion(parent: RigidMotion, child: RigidMotion) -> RigidMotion:
    """Express one child-relative motion in its parent's reference frame.

    Work is constant for this edge. Callers visit only affected anatomical
    chains; this function neither scans anatomy nor retains past results.
    Child and parent must describe the SAME instant, not adjacent snapshots.
    """
    if parent.origin.time_microseconds != child.origin.time_microseconds:
        raise ValueError("parent and child motion must share one physical time")
    r = parent.basis.to_parent(child.origin.position_metres)
    v_relative = parent.basis.to_parent(child.origin.velocity_metres_per_second)
    a_relative = parent.basis.to_parent(child.origin.acceleration_metres_per_second_squared)
    omega = parent.angular_velocity_radians_per_second
    alpha = parent.angular_acceleration_radians_per_second_squared
    child_omega = parent.basis.to_parent(child.angular_velocity_radians_per_second)
    child_alpha = parent.basis.to_parent(child.angular_acceleration_radians_per_second_squared)
    return RigidMotion(
        PointMotion(
            parent.origin.time_microseconds,
            parent.origin.position_metres + r,
            parent.origin.velocity_metres_per_second + _cross(omega, r) + v_relative,
            parent.origin.acceleration_metres_per_second_squared
            + _cross(alpha, r)
            + _cross(omega, _cross(omega, r))
            + _cross(omega, v_relative).scaled(Fraction(2))
            + a_relative,
        ),
        RigidBasis(
            parent.basis.to_parent(child.basis.x),
            parent.basis.to_parent(child.basis.y),
            parent.basis.to_parent(child.basis.z),
        ),
        omega + child_omega,
        alpha + child_alpha + _cross(omega, child_omega),
    )


@dataclass(frozen=True, slots=True)
class InertialEvidence:
    """Ideal inertial quantities in link axes; not inner-ear physiology.

    Specific force is acceleration MINUS gravity, not a balance score.
    Angular rate is gyro-like physical evidence, not a semicircular-canal model.
    """

    time_microseconds: Fraction
    specific_force_metres_per_second_squared: ExactVector3
    angular_velocity_radians_per_second: ExactVector3

    def __post_init__(self) -> None:
        _require_fraction(self.time_microseconds, "physical time", nonnegative=True)
        _validate_vector(self.specific_force_metres_per_second_squared, "specific force")
        _validate_vector(self.angular_velocity_radians_per_second, "angular rate")


def inertial_evidence(
    motion: RigidMotion,
    site_offset_metres: ExactVector3,
    gravity_metres_per_second_squared: ExactVector3,
) -> InertialEvidence:
    """Sample actual point acceleration and angular rate in the link frame.

    Gravity is supplied by the environment; no Earth constant is assumed.
    Evidence is computed on demand and is not a new persistent body state.
    """
    _validate_vector(gravity_metres_per_second_squared, "environment gravity")
    point = motion.at_local_point(site_offset_metres)
    return InertialEvidence(
        point.time_microseconds,
        motion.basis.to_local(
            point.acceleration_metres_per_second_squared
            - gravity_metres_per_second_squared
        ),
        motion.basis.to_local(motion.angular_velocity_radians_per_second),
    )
