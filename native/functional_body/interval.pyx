"""Same-law compiled interval control; MuJoCo owns every physical settlement.

Only IEEE-double scalar bookkeeping is compiled here. NumPy's existing vector
operations and MuJoCo's public error-safe bindings retain their arithmetic.
Caller validates/restores before entry and captures only after final guards.
No persistent state, raw native pointer, callback, solver, or behavior policy.
"""
from libc.math cimport isfinite

import mujoco as mj
import numpy as np

INTERVAL_ABI = 2


def advance_interval(engine, effort, steps, available_work_j):
    # Keep count and supply as Python objects: the predecessor accepts arbitrary
    # integer counts and numeric supplies; narrowing either changes boundaries.
    cdef double positive_work = 0.0
    cdef double signed_work = 0.0
    cdef double braking_work = 0.0
    cdef double bearing_heat = 0.0
    cdef double self_bearing_heat = 0.0
    cdef double travel_peak = 0.0
    cdef double sample_peak, dt
    cdef bint has_self = engine._sensory_root is not None

    m, d = engine._model, engine._data
    check = engine._check
    step, kinematics, collision = mj.mj_step, mj.mj_kinematics, mj.mj_collision
    qvel = d.qvel
    geometry_position = d.geom_xpos
    geometry_rotation = d.geom_xmat.reshape(-1, 3, 3)
    damping, rbound = m.dof_damping, m.geom_rbound
    motor_dofs = np.asarray(engine._motor_dof, dtype=np.intp)
    self_dofs = engine._self_dofs
    travel_limit = engine.limits.max_surface_travel_m
    dt = m.opt.timestep

    for _ in range(steps):
        position, rotation = geometry_position.copy(), geometry_rotation.copy()
        velocity_before = qvel.copy()
        step(m, d)
        kinematics(m, d)
        collision(m, d)
        check()
        velocity_midpoint = (velocity_before + qvel) * 0.5
        # Supply debit, signed work and braking heat share the motion law's
        # midpoint quadrature. Conservative endpoint bounds are NOT heat.
        midpoint_power = effort * velocity_midpoint[motor_dofs]
        signed_work += float(midpoint_power.sum()) * dt
        positive_work += float(np.maximum(midpoint_power, 0).sum()) * dt
        braking_work += float(np.maximum(-midpoint_power, 0).sum()) * dt
        # Endpoint bearing trapezoids would add h/4 * dv.T * B * dv.
        # Only the midpoint law's own dissipation is passed to thermal custody.
        bearing_heat += float(np.dot(damping, velocity_midpoint**2)) * dt
        if has_self:
            self_bearing_heat += float(np.dot(
                damping[self_dofs], velocity_midpoint[self_dofs]**2)) * dt
        if not (isfinite(positive_work) and isfinite(signed_work)
                and isfinite(braking_work) and isfinite(bearing_heat)
                and isfinite(self_bearing_heat)):
            raise ValueError("non-finite mechanical work")
        if positive_work > available_work_j:
            raise ValueError("mechanical energy supply exhausted; no successor")
        trace = np.einsum("ijk,ijk->i", rotation, geometry_rotation)
        angle = np.arccos(((trace - 1) / 2).clip(-1, 1))
        travel = np.linalg.norm(geometry_position - position, axis=1) + rbound * angle
        sample_peak = float(travel.max(initial=0))
        # Preserve max(previous, sample): a NaN sample does not replace previous.
        # The very next predicate rejects that non-finite surface observation.
        if sample_peak > travel_peak:
            travel_peak = sample_peak
        if not np.isfinite(travel).all():
            raise ValueError("non-finite surface motion")
        if travel_peak > travel_limit:
            raise ValueError("surface movement exceeds collision sampling resolution")
    return (positive_work, signed_work, travel_peak, braking_work,
            bearing_heat, self_bearing_heat)
