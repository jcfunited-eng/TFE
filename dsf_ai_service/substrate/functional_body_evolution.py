"""Bounded numerical FREE-body evolution, authorized by Joe 2026-09-25.

Binary64 rigid-body approximation, NOT DSF/neuron arithmetic. Uses the exact
reference's joint-tree elimination, not a second force law. No contacts, joint
limits, actuator strength, metabolism, controller, history or production mount.
External world-frame COM wrenches and joint efforts are constant over a step.

RK4 at N and 2N subdivisions gives an error INDICATOR, not a rigorous enclosure.
Mechanical energy/work and momentum/impulse residuals are checked separately.
No velocity rescaling, fake heat, silent retries or partially published state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from dsf_ai_service.substrate.functional_body_articulation import (
    HingeSegment, _eliminate_tree, _inertia_components, _translation_components,
)
from dsf_ai_service.substrate.functional_body_dynamics import MassProperties


def _finite(values):
    if any(type(x) is not float or not math.isfinite(x) for x in values):
        raise ValueError("mechanical numerical state requires finite binary64 values")


def _tuple(values, size):
    if type(values) is not tuple or len(values) != size:
        raise ValueError("mechanical tuple has wrong shape")
    _finite(values)


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _scale(a, k):
    return tuple(x * k for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    x, y, z = a
    u, v, w = b
    return (y*w-z*v, z*u-x*w, x*v-y*u)


def _norm(v):
    return math.hypot(*v)


def _difference(a, b):
    return _norm(tuple(x-y for x, y in zip(a, b)))


def _unit(q):
    length = _norm(q)
    if length == 0.0 or not math.isfinite(length):
        raise ValueError("orientation quaternion is zero or non-finite")
    return tuple(x / length for x in q)


def _qmul(q, r):
    w, x, y, z = q
    a, b, c, d = r
    return (w*a-x*b-y*c-z*d, w*b+x*a+y*d-z*c,
            w*c-x*d+y*a+z*b, w*d+x*c-y*b+z*a)


def _basis(q):
    w, x, y, z = _unit(q)
    # Rotation COLUMNS, body -> world.
    return ((1-2*(y*y+z*z), 2*(x*y+w*z), 2*(x*z-w*y)),
            (2*(x*y-w*z), 1-2*(x*x+z*z), 2*(y*z+w*x)),
            (2*(x*z+w*y), 2*(y*z-w*x), 1-2*(x*x+y*y)))


def _rotate(columns, v):
    return tuple(sum(columns[k][i]*v[k] for k in range(3)) for i in range(3))


def _compose(a, b):
    return tuple(_rotate(a, column) for column in b)


def _inertia_times(moments, basis, omega):
    return _rotate(basis, tuple(moments[k] * _dot(basis[k], omega) for k in range(3)))


def _fv(vector):
    return (float(vector.x), float(vector.y), float(vector.z))


@dataclass(frozen=True, slots=True)
class BodyState:
    """Only current generalized mechanics. Quaternion is homogeneous, not a pose score."""
    time_microseconds: int
    root_position_metres: tuple
    root_quaternion: tuple
    root_velocity_metres_per_second: tuple
    root_angular_velocity_radians_per_second: tuple
    joint_angles_radians: tuple
    joint_rates_radians_per_second: tuple

    def __post_init__(self):
        if type(self.time_microseconds) is not int or not 0 <= self.time_microseconds < 2**63:
            raise ValueError("body clock must fit nonnegative signed64 microseconds")
        for vector in (self.root_position_metres, self.root_velocity_metres_per_second,
                       self.root_angular_velocity_radians_per_second):
            _tuple(vector, 3)
        _tuple(self.root_quaternion, 4)
        _unit(self.root_quaternion)
        if type(self.joint_angles_radians) is not tuple:
            raise ValueError("joint angles must be immutable")
        _tuple(self.joint_angles_radians, len(self.joint_angles_radians))
        _tuple(self.joint_rates_radians_per_second, len(self.joint_angles_radians))

    def _values(self):
        return (self.root_position_metres + _unit(self.root_quaternion)
                + self.root_velocity_metres_per_second
                + self.root_angular_velocity_radians_per_second
                + self.joint_angles_radians + self.joint_rates_radians_per_second)


@dataclass(frozen=True, slots=True)
class EvolutionLimits:
    """Explicit mechanical accuracy and work budget, not a cognitive threshold.

    All tolerances are positive absolute SI quantities. They are supplied by
    the caller's actual geometry/load accuracy contract; no production defaults.
    max_substeps bounds the FINE pass; total dynamics calls are 6*max_substeps.
    """
    position_metres: float
    angle_radians: float
    velocity_metres_per_second: float
    angular_velocity_radians_per_second: float
    energy_joules: float
    linear_momentum_kg_metres_per_second: float
    angular_momentum_kg_metres_squared_per_second: float
    max_substeps: int

    def __post_init__(self):
        values = (self.position_metres, self.angle_radians,
                  self.velocity_metres_per_second, self.angular_velocity_radians_per_second,
                  self.energy_joules, self.linear_momentum_kg_metres_per_second,
                  self.angular_momentum_kg_metres_squared_per_second)
        _finite(values)
        if min(values) <= 0:
            raise ValueError("numerical tolerances must be positive")
        if type(self.max_substeps) is not int or self.max_substeps < 2:
            raise ValueError("numerical subdivision budget must permit two steps")


@dataclass(frozen=True, slots=True)
class EvolutionResult:
    state: BodyState
    position_refinement_metres: float
    angle_refinement_radians: float
    velocity_refinement_metres_per_second: float
    angular_velocity_refinement_radians_per_second: float
    energy_work_residual_joules: float
    linear_momentum_residual_kg_metres_per_second: tuple
    angular_momentum_residual_kg_metres_squared_per_second: tuple


@dataclass(frozen=True, slots=True, init=False)
class FreeHingeBody:
    """Compile declared exact anatomy once; do not retain a duplicate anatomy.

    Existing HingeSegment orientation becomes its zero-angle rest orientation.
    Parent anchors and axes remain fixed in their respective anatomical frames.
    Numeric state is never passed into the exact contact or DSF laws.
    """
    masses: tuple
    principal_inertias: tuple
    hinges: tuple

    def __init__(self, root: MassProperties, segments: tuple[HingeSegment, ...]):
        if not isinstance(root, MassProperties) or type(segments) is not tuple:
            raise TypeError("body requires declared exact anatomy")
        for i, link in enumerate(segments, 1):
            if not isinstance(link, HingeSegment) or link.parent >= i:
                raise ValueError("body parent must precede child")
        props = (root,) + tuple(link.properties for link in segments)
        object.__setattr__(self, "masses", tuple(float(p.mass_kilograms) for p in props))
        object.__setattr__(self, "principal_inertias",
                           tuple(_fv(p.principal_inertia_kilogram_metres_squared) for p in props))
        object.__setattr__(self, "hinges", tuple(
            (link.parent, _fv(link.parent_anchor_metres), _fv(link.child_anchor_metres),
             _fv(link.parent_axis), tuple(_fv(a) for a in
                 (link.child_basis_in_parent.x, link.child_basis_in_parent.y, link.child_basis_in_parent.z)))
            for link in segments))
        _finite(self.masses)
        for inertia in self.principal_inertias:
            _finite(inertia)

    def _kinematics(self, y, limits=None):
        n = len(self.hinges)
        if limits is not None:
            # Necessary representability guard, not an accumulated error proof.
            # One ULP in each coordinate must fit the declared physical norm
            # budget. This catches two equally frozen coarse/fine trajectories.
            checks = [(y[:3], limits.position_metres),
                      (y[7:10], limits.velocity_metres_per_second),
                      (y[10:13], limits.angular_velocity_radians_per_second),
                      (_unit(y[3:7]), limits.angle_radians/2)]
            checks.extend(((angle,), limits.angle_radians) for angle in y[13:13+n])
            checks.extend(((rate,), limits.angular_velocity_radians_per_second) for rate in y[13+n:13+2*n])
            for _, pa, ca, _, _ in self.hinges:
                checks.extend(((pa, limits.position_metres), (ca, limits.position_metres)))
            if any(math.hypot(*(math.ulp(x) for x in values)) > budget for values, budget in checks):
                raise ValueError("binary64 spacing exceeds declared physical resolution")
        positions, bases, velocities, omegas = [y[:3]], [_basis(y[3:7])], [y[7:10]], [y[10:13]]
        transforms, subspaces, biases = [], [], []
        for j, (parent, parent_anchor, child_anchor, axis_parent, rest) in enumerate(self.hinges):
            angle, rate = y[13+j], y[13+n+j]
            half = angle / 2
            rotation = _basis((math.cos(half),) + _scale(axis_parent, math.sin(half)))
            basis = _compose(bases[parent], _compose(rotation, rest))
            lever = _scale(_rotate(basis, child_anchor), -1.0)
            r = _add(_rotate(bases[parent], parent_anchor), lever)
            axis = _rotate(bases[parent], axis_parent)
            linear_axis = _cross(axis, lever)
            relative_omega, relative_v = _scale(axis, rate), _scale(linear_axis, rate)
            omega = omegas[parent]
            bias_angular = _cross(omega, relative_omega)
            bias_linear = _add(_add(_cross(omega, _cross(omega, r)),
                                   _scale(_cross(omega, relative_v), 2.0)),
                               _scale(_cross(axis, linear_axis), rate*rate))
            positions.append(_add(positions[parent], r))
            bases.append(basis)
            velocities.append(_add(_add(velocities[parent], _cross(omega, r)), relative_v))
            omegas.append(_add(omega, relative_omega))
            transforms.append(_translation_components(*r))
            subspaces.append(axis + linear_axis)
            biases.append(bias_angular + bias_linear)
        if limits is not None:
            for vectors, budget in ((positions, limits.position_metres),
                                    (velocities, limits.velocity_metres_per_second),
                                    (omegas, limits.angular_velocity_radians_per_second)):
                if any(math.hypot(*(math.ulp(x) for x in vector)) > budget for vector in vectors):
                    raise ValueError("binary64 derived geometry exceeds declared physical resolution")
        return positions, bases, velocities, omegas, transforms, subspaces, biases

    def _derivative(self, y, loads, efforts, limits=None):
        p, bases, v, w, transforms, subspaces, biases = self._kinematics(y, limits)
        inertias = [_inertia_components(m, inertia, basis) for m, inertia, basis in
                    zip(self.masses, self.principal_inertias, bases)]
        forces, power = [], 0.0
        impulse_rate, angular_impulse_rate = (0.0,)*3, (0.0,)*3
        for inertia, basis, pos, vel, omega, load in zip(
                self.principal_inertias, bases, p, v, w, loads):
            gyro = _cross(omega, _inertia_times(inertia, basis, omega))
            forces.append(tuple(gyro[k]-load[k] for k in range(3)) + _scale(load[3:], -1.0))
            power += _dot(load[:3], omega) + _dot(load[3:], vel)
            impulse_rate = _add(impulse_rate, load[3:])
            angular_impulse_rate = _add(angular_impulse_rate, _add(load[:3], _cross(pos, load[3:])))
        accelerations, qdd = _eliminate_tree(inertias, forces, transforms, subspaces, biases,
                                             tuple(link[0] for link in self.hinges), efforts, None)
        n = len(self.hinges)
        power += _dot(efforts, y[13+n:13+2*n])
        quaternion_rate = _scale(_qmul((0.0,) + y[10:13], y[3:7]), 0.5)
        result = (y[7:10] + quaternion_rate + tuple(accelerations[0][3:])
                  + tuple(accelerations[0][:3]) + y[13+n:13+2*n] + tuple(qdd)
                  + (power,) + impulse_rate + angular_impulse_rate)
        result = tuple(float(x) for x in result)
        _finite(result)
        return result

    def _integrate(self, initial, duration, steps, loads, efforts, limits):
        y = initial + (0.0,)*7  # Work and impulses are temporary interval integrals.
        h = duration / steps
        for _ in range(steps):
            k1 = self._derivative(y, loads, efforts, limits)
            k2 = self._derivative(_add(y, _scale(k1, h/2)), loads, efforts, limits)
            k3 = self._derivative(_add(y, _scale(k2, h/2)), loads, efforts, limits)
            k4 = self._derivative(_add(y, _scale(k3, h)), loads, efforts, limits)
            y = tuple(a+h*(b+2*c+2*d+e)/6 for a, b, c, d, e in zip(y, k1, k2, k3, k4))
            _finite(y)
            y = y[:3] + _unit(y[3:7]) + y[7:]
        return y

    def _measure(self, y, limits=None):
        p, bases, v, w, _, _, _ = self._kinematics(y, limits)
        energy, momentum, angular_momentum = 0.0, (0.0,)*3, (0.0,)*3
        for mass, inertia, basis, pos, vel, omega in zip(
                self.masses, self.principal_inertias, bases, p, v, w):
            linear = _scale(vel, mass)
            angular = _inertia_times(inertia, basis, omega)
            energy += (_dot(vel, linear) + _dot(omega, angular))/2
            momentum = _add(momentum, linear)
            angular_momentum = _add(angular_momentum, _add(angular, _cross(pos, linear)))
        _finite((energy,) + momentum + angular_momentum)
        return energy, momentum, angular_momentum, (p, bases, v, w)

    def advance(self, state, duration_microseconds, external_wrenches, joint_efforts,
                *, subdivisions, limits):
        """Return one fully checked successor or raise without changing input.

        external_wrenches are immutable (torque xyz, force xyz) binary64 tuples,
        one per link including root. No implicit gravity or fixed support.
        Subdivision choice is a numerical work/accuracy parameter, not behavior.
        No automatic retry, step truncation or clamping occurs.
        """
        if not isinstance(state, BodyState) or not isinstance(limits, EvolutionLimits):
            raise TypeError("advance requires body state and explicit numerical limits")
        n = len(self.hinges)
        if len(state.joint_angles_radians) != n:
            raise ValueError("state does not match body anatomy")
        if (type(duration_microseconds) is not int or duration_microseconds <= 0
                or state.time_microseconds + duration_microseconds >= 2**63):
            raise ValueError("invalid physical interval")
        if type(subdivisions) is not int or subdivisions < 1 or 2*subdivisions > limits.max_substeps:
            raise ValueError("numerical subdivision budget exceeded")
        if type(external_wrenches) is not tuple or len(external_wrenches) != n+1:
            raise ValueError("explicit external wrench required for every link")
        for load in external_wrenches:
            _tuple(load, 6)
        _tuple(joint_efforts, n)
        initial = state._values()
        seconds = duration_microseconds / 1_000_000
        coarse = self._integrate(initial, seconds, subdivisions, external_wrenches, joint_efforts, limits)
        fine = self._integrate(initial, seconds, subdivisions*2, external_wrenches, joint_efforts, limits)
        before = self._measure(initial, limits)
        after = self._measure(fine, limits)
        cpos, cbasis, cvel, comega, _, _, _ = self._kinematics(coarse, limits)
        fpos, fbasis, fvel, fomega = after[3]
        position_error = max(_difference(a, b) for a, b in zip(cpos, fpos))
        # ||R-S||_F = 2 sqrt(2) sin(theta/2); actual rotation separation,
        # not the smaller separation of one axis. asin clamp covers roundoff
        # at the mathematical pi boundary, not an acceptance tolerance.
        angle_error = max(2*math.asin(min(1.0, math.hypot(
            *(x-y for a, b in zip(a_basis, b_basis) for x, y in zip(a, b)))
            / math.sqrt(8.0))) for a_basis, b_basis in zip(cbasis, fbasis))
        angle_error = max(angle_error, max((abs(a-b) for a, b in
                          zip(coarse[13:13+n], fine[13:13+n])), default=0.0))
        velocity_error = max(_difference(a, b) for a, b in zip(cvel, fvel))
        angular_error = max(_difference(a, b) for a, b in zip(comega, fomega))
        energy_residual = after[0] - before[0] - fine[-7]
        momentum_residual = tuple(a-b-c for a, b, c in zip(after[1], before[1], fine[-6:-3]))
        angular_residual = tuple(a-b-c for a, b, c in zip(after[2], before[2], fine[-3:]))
        errors = (position_error, angle_error, velocity_error, angular_error,
                  abs(energy_residual), _norm(momentum_residual), _norm(angular_residual))
        thresholds = (limits.position_metres, limits.angle_radians,
                      limits.velocity_metres_per_second, limits.angular_velocity_radians_per_second,
                      limits.energy_joules, limits.linear_momentum_kg_metres_per_second,
                      limits.angular_momentum_kg_metres_squared_per_second)
        _finite(tuple(float(x) for x in errors))
        if any(error > tolerance for error, tolerance in zip(errors, thresholds)):
            raise ValueError("body evolution exceeds declared numerical accuracy/conservation limits")
        successor = BodyState(state.time_microseconds + duration_microseconds, fine[:3],
                              fine[3:7], fine[7:10], fine[10:13],
                              fine[13:13+n], fine[13+n:13+2*n])
        return EvolutionResult(successor, position_error, angle_error, velocity_error, angular_error,
                               energy_residual, momentum_residual, angular_residual)
