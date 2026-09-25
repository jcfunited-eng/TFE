"""Instantaneous massive revolute-tree mechanics in world coordinates.

The public exact wrapper preserves bounded rational geometry. The shared
private elimination also accepts finite binary64 operands for the explicitly
ratified numerical-body path. One Newton-Euler law; neither path is cognition,
a contact solver, an actuator controller or a production-mounted body.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction as F
from math import isfinite

from dsf_ai_service.substrate.body_surface_contact import (
    ExactVector3, ZERO_VECTOR, _require_fraction, _validate_vector,
)
from dsf_ai_service.substrate.functional_body_kinematics import (
    PointMotion, RigidBasis, RigidMotion, _cross,
)
from dsf_ai_service.substrate.functional_body_dynamics import MassProperties, Wrench, required_wrench


_ZERO = F(0)
_ONE = F(1)


def _bounded(value):
    if type(value) is float:
        if not isfinite(value):
            raise ValueError("non-finite numerical articulated mechanics")
        return value
    return _require_fraction(value, "articulated mechanics")


def _six(angular, linear):
    return (angular.x, angular.y, angular.z, linear.x, linear.y, linear.z)


def _parts(values):
    return ExactVector3(*values[:3]), ExactVector3(*values[3:])


def _add(a, b):
    return tuple(_bounded(x + y) for x, y in zip(a, b))


def _scale(a, k):
    return tuple(_bounded(x * k) for x in a)


def _dot(a, b):
    return _bounded(sum((x * y for x, y in zip(a, b) if x and y), _ZERO))


def _mv(matrix, vector):
    return tuple(_dot(row, vector) for row in matrix)


def _transpose(matrix):
    return tuple(zip(*matrix))


def _mm(a, b):
    columns = _transpose(b)
    return tuple(tuple(_dot(row, col) for col in columns) for row in a)


def _matrix_add(a, b):
    return tuple(_add(x, y) for x, y in zip(a, b))


def _translation_components(x, y, z):
    # [alpha; a] -> [alpha; a + alpha cross r], all in world axes.
    return (
        (_ONE, _ZERO, _ZERO, _ZERO, _ZERO, _ZERO),
        (_ZERO, _ONE, _ZERO, _ZERO, _ZERO, _ZERO),
        (_ZERO, _ZERO, _ONE, _ZERO, _ZERO, _ZERO),
        (_ZERO, z, -y, _ONE, _ZERO, _ZERO),
        (-z, _ZERO, x, _ZERO, _ONE, _ZERO),
        (y, -x, _ZERO, _ZERO, _ZERO, _ONE),
    )


def _inertia_components(mass, moments, axes):
    """Principal moments and rotation COLUMNS -> world COM spatial inertia."""
    rotation = tuple(tuple(_bounded(sum((moments[k] * axes[k][i] * axes[k][j]
                                       for k in range(3)), _ZERO))
                           for j in range(3)) for i in range(3))
    return tuple(tuple(rotation[i][j] if i < 3 and j < 3 else
                       mass if i == j and i >= 3 else _ZERO
                       for j in range(6)) for i in range(6))


def _inertia(properties, basis):
    axes = tuple((v.x, v.y, v.z) for v in (basis.x, basis.y, basis.z))
    principal = properties.principal_inertia_kilogram_metres_squared
    return _inertia_components(properties.mass_kilograms,
                               (principal.x, principal.y, principal.z), axes)


def _solve_root(matrix, rhs):
    """Six SPD equations only, fixed elimination order and no iteration."""
    rows = [list(row) + [b] for row, b in zip(matrix, rhs)]
    for k in range(6):
        pivot = rows[k][k]
        if pivot <= 0:
            raise ValueError("non-positive articulated root inertia")
        for i in range(k + 1, 6):
            factor = _bounded(rows[i][k] / pivot)
            rows[i][k] = _ZERO
            for j in range(k + 1, 7):
                rows[i][j] = _bounded(rows[i][j] - factor * rows[k][j])
    result = [_ZERO] * 6
    for i in range(5, -1, -1):
        result[i] = _bounded((rows[i][6] - sum(
            (rows[i][j] * result[j] for j in range(i + 1, 6)), _ZERO)) / rows[i][i])
    return tuple(result)


def _eliminate_tree(inertias, forces, transforms, subspaces, biases, parents,
                    joint_efforts, root_acceleration):
    """Shared exact/numerical ABA. Consumes temporary inertia/force lists.

    Inputs are dimensionally validated by their mechanical wrapper.
    Fixed 6x6 blocks, two linear passes; no joint-space dense matrix.
    No external state is mutated and no history is retained.
    """
    n = len(parents)
    eliminated = [None] * n
    for j in range(n - 1, -1, -1):
        i, parent = j + 1, parents[j]
        inertia, force, axis = inertias[i], forces[i], subspaces[j]
        u_column = _mv(inertia, axis)
        d = _dot(axis, u_column)
        if d <= 0:
            raise ValueError("non-positive hinge effective inertia")
        u = _bounded(joint_efforts[j] - _dot(axis, force))
        reduced = tuple(tuple(_bounded(inertia[a][b] - u_column[a] * u_column[b] / d)
                              for b in range(6)) for a in range(6))
        reduced_force = _add(_add(force, _mv(reduced, biases[j])), _scale(u_column, u / d))
        transform = transforms[j]
        transpose = _transpose(transform)
        inertias[parent] = _matrix_add(inertias[parent], _mm(_mm(transpose, reduced), transform))
        forces[parent] = _add(forces[parent], _mv(transpose, reduced_force))
        eliminated[j] = (u_column, d, u)
    acceleration = (_solve_root(inertias[0], _scale(forces[0], F(-1)))
                    if root_acceleration is None else root_acceleration)
    accelerations, joint_accelerations = [acceleration], []
    for j, parent in enumerate(parents):
        a = _add(_mv(transforms[j], accelerations[parent]), biases[j])
        u_column, d, u = eliminated[j]
        qdd = _bounded((u - _dot(u_column, a)) / d)
        accelerations.append(_add(a, _scale(subspaces[j], qdd)))
        joint_accelerations.append(qdd)
    return accelerations, joint_accelerations


@dataclass(frozen=True, slots=True)
class HingeSegment:
    """Child mass/hinge geometry and actual relative orientation.

    Parent indices are mechanical-tree positions, not object identities.
    Root is 0; each parent precedes its child. Origins are COMs and axes are
    principal inertia axes. Coincident anchors determine child COM position.
    """
    parent: int
    properties: MassProperties
    parent_anchor_metres: ExactVector3
    child_anchor_metres: ExactVector3
    parent_axis: ExactVector3
    child_axis: ExactVector3
    child_basis_in_parent: RigidBasis

    def __post_init__(self):
        if type(self.parent) is not int or self.parent < 0:
            raise ValueError("hinge parent must be a nonnegative tree index")
        if not isinstance(self.properties, MassProperties) or not isinstance(self.child_basis_in_parent, RigidBasis):
            raise TypeError("hinge needs declared mass and rigid basis")
        for vector in (self.parent_anchor_metres, self.child_anchor_metres, self.parent_axis, self.child_axis):
            _validate_vector(vector, "hinge geometry")
        if self.parent_axis.dot(self.parent_axis) != 1 or self.child_axis.dot(self.child_axis) != 1:
            raise ValueError("hinge axes must be unit vectors")
        if self.child_basis_in_parent.to_parent(self.child_axis) != self.parent_axis:
            raise ValueError("hinge axes do not align in current configuration")


@dataclass(frozen=True, slots=True)
class ArticulatedAcceleration:
    motions: tuple[RigidMotion, ...]
    joint_accelerations_radians_per_second_squared: tuple[F, ...]
    joint_wrenches_on_child_about_com: tuple[Wrench, ...]
    root_support_wrench_about_com: Wrench


def solve_hinge_tree(root_properties, root_motion, segments, joint_rates,
                     joint_efforts, external_loads, root_acceleration):
    """Exact instantaneous accelerations/reactions, no time advancement.

    Inputs are unchanged from FB-01c. Root motion gives time/pose/velocity;
    old accelerations are not loads. None root_acceleration means free base;
    otherwise explicit (angular, linear COM) acceleration returns the required
    support reaction. Loads are world-frame COM wrenches including gravity.
    """
    if not isinstance(root_properties, MassProperties) or not isinstance(root_motion, RigidMotion):
        raise TypeError("root needs declared mass and actual motion")
    if any(type(value) is not tuple for value in (segments, joint_rates, joint_efforts, external_loads)):
        raise TypeError("articulation inputs must be immutable tuples")
    n = len(segments)
    if len(joint_rates) != n or len(joint_efforts) != n or len(external_loads) != n + 1:
        raise ValueError("tree inputs have inconsistent lengths")
    if not all(isinstance(load, Wrench) for load in external_loads):
        raise TypeError("each link needs an explicit external wrench")
    if root_acceleration is not None:
        if type(root_acceleration) is not tuple or len(root_acceleration) != 2:
            raise TypeError("base acceleration is an angular/linear vector pair")
        for vector in root_acceleration:
            _validate_vector(vector, "base acceleration")
    for i, link in enumerate(segments, 1):
        if not isinstance(link, HingeSegment) or link.parent >= i:
            raise ValueError("tree parent must precede child")
        _require_fraction(joint_rates[i - 1], "hinge rate")
        _require_fraction(joint_efforts[i - 1], "hinge effort")
    zero_acceleration = replace(root_motion.origin, acceleration_metres_per_second_squared=ZERO_VECTOR)
    motions = [replace(root_motion, origin=zero_acceleration,
                       angular_acceleration_radians_per_second_squared=ZERO_VECTOR)]
    transforms, subspaces, biases, offsets = [], [], [], []
    for link, rate in zip(segments, joint_rates):
        parent = motions[link.parent]
        basis = RigidBasis(*(parent.basis.to_parent(axis) for axis in
                             (link.child_basis_in_parent.x, link.child_basis_in_parent.y, link.child_basis_in_parent.z)))
        lever = basis.to_parent(link.child_anchor_metres).scaled(F(-1))
        r = parent.basis.to_parent(link.parent_anchor_metres) + lever
        axis = basis.to_parent(link.child_axis)
        linear_axis = _cross(axis, lever)
        relative_omega, relative_v = axis.scaled(rate), linear_axis.scaled(rate)
        omega = parent.angular_velocity_radians_per_second
        bias_angular = _cross(omega, relative_omega)
        bias_linear = (_cross(omega, _cross(omega, r))
                       + _cross(omega, relative_v).scaled(F(2))
                       + _cross(axis, linear_axis).scaled(rate * rate))
        for vector in (r, bias_angular, bias_linear):
            _validate_vector(vector, "joint kinematics")
        motions.append(RigidMotion(PointMotion(
            root_motion.origin.time_microseconds,
            parent.origin.position_metres + r,
            parent.origin.velocity_metres_per_second + _cross(omega, r) + relative_v,
            ZERO_VECTOR), basis, omega + relative_omega, ZERO_VECTOR))
        transforms.append(_translation_components(r.x, r.y, r.z))
        subspaces.append(_six(axis, linear_axis))
        biases.append(_six(bias_angular, bias_linear))
        offsets.append(r)
    properties = (root_properties,) + tuple(link.properties for link in segments)
    inertias = [_inertia(prop, body.basis) for prop, body in zip(properties, motions)]
    forces = []
    for prop, body, load in zip(properties, motions, external_loads):
        omega_local = body.basis.to_local(body.angular_velocity_radians_per_second)
        momentum = body.basis.to_parent(prop.momentum(omega_local))
        gyro = _cross(body.angular_velocity_radians_per_second, momentum)
        forces.append(_six(gyro - load.torque_newton_metres, load.force_newtons.scaled(F(-1))))
    accelerations, joint_accelerations = _eliminate_tree(
        inertias, forces, transforms, subspaces, biases,
        tuple(link.parent for link in segments), joint_efforts,
        None if root_acceleration is None else _six(*root_acceleration))
    solved = []
    for body, a in zip(motions, accelerations):
        angular, linear = _parts(a)
        solved.append(replace(body, origin=replace(body.origin, acceleration_metres_per_second_squared=linear),
                              angular_acceleration_radians_per_second_squared=angular))
    reactions = [required_wrench(prop, body) + load.opposite()
                 for prop, body, load in zip(properties, solved, external_loads)]
    for j in range(n - 1, -1, -1):
        parent = segments[j].parent
        reactions[parent] = reactions[parent] + reactions[j + 1].shifted(offsets[j].scaled(F(-1)))
    return ArticulatedAcceleration(tuple(solved), tuple(joint_accelerations),
                                  tuple(reactions[1:]), reactions[0])
