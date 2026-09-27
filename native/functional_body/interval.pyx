"""Bounded numerical admission for the unchanged native midpoint body law.

Coarse/fine trials are unpublished scratch. Only accepted fine motion and its
actual work survive; no behavioral controller, new force law or second anatomy.
Local mesh disagreement is an error indicator, not a continuum error enclosure.
"""
import math
import sys

import mujoco as mj
import numpy as np

INTERVAL_ABI = 3
INTERVAL_LAW = "midpoint-dyadic-accuracy-v1"
ANGLE_RAD = math.radians(.01)
POSITION_M = .0001
EVENT_S = .000001
STATE_KIND = mj.mjtState.mjSTATE_INTEGRATION


def _finite(value):
    if not np.isfinite(value).all():
        raise ValueError("non-finite numerical comparison")
    return value


def _state(e):
    mj.mj_getState(e._model, e._data, e._state_buffer, STATE_KIND)
    return _finite(e._state_buffer).copy()


def _restore(e, state, dt):
    e._model.opt.timestep = dt
    mj.mj_resetData(e._model, e._data)
    mj.mj_setState(e._model, e._data, state, STATE_KIND)
    mj.mj_forward(e._model, e._data)
    e._check()


def _work_add(a, b):
    value = tuple(max(a[i], b[i]) if i == 2 else a[i]+b[i] for i in range(6))
    _finite(value)
    return value


def _impulse_add(a, b):
    # Each key is an internal native contact pair, never an organism identity.
    value = dict(a)
    for pair, row in b.items():
        old = value.get(pair)
        value[pair] = row if old is None else tuple(_finite(x+y) for x, y in zip(old, row))
    return value


def _midpoint_wrenches(m, d):
    for i, contact in enumerate(d.contact):
        if contact.efc_address < 0:
            continue
        wrench = np.empty(6)
        mj.mj_contactForce(m, d, i, wrench)
        _finite(wrench)
        if not np.any(wrench):
            continue
        rotation = _finite(contact.frame).reshape(3, 3).T
        force, couple = rotation @ wrench[:3], rotation @ wrench[3:]
        pair = tuple(int(g) for g in contact.geom)
        if pair[0] > pair[1]:
            pair = pair[::-1]
            force, couple = -force, -couple
        yield pair, force, couple


def _pair_impulses(wrenches, dt):
    result = {}
    for pair, force, couple in wrenches:
        previous = result.get(pair)
        result[pair] = (_finite(force), _finite(couple)) if previous is None else (
            _finite(previous[0]+force), _finite(previous[1]+couple))
    for pair, (force, couple) in result.items():
        result[pair] = tuple(_finite(x) for x in (
            dt*force, dt*couple, dt*float(np.linalg.norm(force)),
            dt*float(np.linalg.norm(couple))))
    return result


def _midpoint_impulses(m, d, dt):
    # Relative allowances use each pair's resultant, not pointwise magnitudes.
    return _pair_impulses(_midpoint_wrenches(m, d), dt)

def _snapshot(e):
    m, d = e._model, e._data
    velocity = np.empty((m.ngeom, 6))
    for i in range(m.ngeom):
        mj.mj_objectVelocity(m, d, mj.mjtObj.mjOBJ_GEOM, i, velocity[i], 0)
    _finite(velocity)
    contacts = []
    geometric = []
    for i, contact in enumerate(d.contact):
        if contact.efc_address < 0:
            continue
        pair = tuple(int(g) for g in contact.geom)
        geometric.append(pair)
        wrench = np.empty(6)
        mj.mj_contactForce(m, d, i, wrench)
        _finite(wrench)
        if not np.any(wrench):
            continue
        _finite(contact.pos)
        frame = _finite(contact.frame).reshape(3, 3).T
        for side, geom in enumerate(pair):
            link = int(m.geom_bodyid[geom])
            rotation = _finite(d.xmat[link]).reshape(3, 3)
            sign = -1 if side == 0 else 1
            transform = rotation.T @ frame
            contacts.append((pair+(side,),
                _finite(rotation.T @ (contact.pos-d.xpos[link])),
                _finite(sign * transform @ wrench[:3]),
                _finite(sign * transform @ wrench[3:])))
    q = d.qpos[e._limit_qpos]
    joints = np.asarray(e._limited, dtype=np.intp)
    domain = (tuple(q <= m.jnt_range[joints, 0]+m.jnt_margin[joints]),
              tuple(q >= m.jnt_range[joints, 1]-m.jnt_margin[joints]),
              tuple(d.efc_type), tuple(d.efc_id), tuple(d.efc_state),
              tuple(sorted(geometric)))
    return dict(state=_state(e), time=float(d.time), dt=float(m.opt.timestep),
        position=_finite(d.geom_xpos).copy(), rotation=_finite(d.geom_xmat).reshape(-1, 3, 3).copy(),
        velocity=velocity, sensory=_finite(d.sensordata).copy(),
        contacts=contacts, domain=domain)


def _vectors_close(a, b, absolute, relative):
    error = _finite(np.linalg.norm(_finite(a-b), axis=-1))
    allowed = _finite(absolute + relative*np.linalg.norm(_finite(b), axis=-1))
    return bool(np.all(error <= allowed))


def _contacts_close(a, b):
    if len(a) != len(b):
        return False
    used = set()
    for key, position, force, couple in a:
        matches = [i for i, (other_key, other_position, _, _) in enumerate(b)
                   if key == other_key and
                   float(_finite(np.linalg.norm(position-other_position))) <= POSITION_M]
        if len(matches) != 1 or matches[0] in used:
            return False
        index = matches[0]
        used.add(index)
        if not _vectors_close(force, b[index][2], .01, .001):
            return False
        if not _vectors_close(couple, b[index][3], .00001, .001):
            return False
    return True


def _close(e, coarse, fine, coarse_work, fine_work, coarse_impulse, fine_impulse, dt):
    trace = np.einsum("ijk,ijk->i", coarse["rotation"], fine["rotation"])
    angle = _finite(np.arccos(np.clip((trace-1)/2, -1, 1)))
    surface = _finite(np.linalg.norm(coarse["position"]-fine["position"], axis=1)
                      + 2*e._model.geom_rbound*np.sin(angle/2))
    if np.any(surface > POSITION_M) or np.any(angle > ANGLE_RAD):
        return False
    if not _vectors_close(coarse["velocity"][:, :3], fine["velocity"][:, :3], .01, .001):
        return False
    if not _vectors_close(coarse["velocity"][:, 3:], fine["velocity"][:, 3:], .001, .001):
        return False
    for addresses, dim, absolute, relative in e._accuracy_sensor_groups:
        a = coarse["sensory"][addresses].reshape(-1, dim)
        b = fine["sensory"][addresses].reshape(-1, dim)
        if not _vectors_close(a, b, absolute, relative):
            return False
    for i in (0, 1, 3, 4, 5):
        gross = float(_finite(fine_work[0]+fine_work[3] if i == 1 else abs(fine_work[i])))
        if abs(coarse_work[i]-fine_work[i]) > 1e-6+.001*gross:
            return False
    zero = (np.zeros(3), np.zeros(3), 0., 0.)
    for pair in coarse_impulse.keys() | fine_impulse.keys():
        a, b = coarse_impulse.get(pair, zero), fine_impulse.get(pair, zero)
        if float(_finite(np.linalg.norm(_finite(a[0]-b[0])))) > 1e-6+.001*b[2]:
            return False
        # Integrate the already-ratified instantaneous couple tolerance:
        # (1e-5 Nm)*dt + .001*integral|couple|dt, units Nm*s.
        if float(_finite(np.linalg.norm(_finite(a[1]-b[1])))) > .00001*dt+.001*b[3]:
            return False
    return _contacts_close(coarse["contacts"], fine["contacts"])


def _one_step(e, effort, remaining, stop):
    m, d = e._model, e._data
    begin = float(d.time)
    dt = stop-begin
    if not math.isfinite(dt) or not dt > 0 or begin+dt != stop:
        raise ValueError("unrepresentable mechanical substep")
    m.opt.timestep = dt
    position, rotation = d.geom_xpos.copy(), d.geom_xmat.reshape(-1, 3, 3).copy()
    velocity_before = d.qvel.copy()
    mj.mj_step(m, d)
    # The native solver retains converged midpoint contacts before kinematics.
    impulse = _midpoint_impulses(m, d, dt)
    mj.mj_kinematics(m, d)
    mj.mj_collision(m, d)
    e._check()
    velocity_midpoint = (velocity_before+d.qvel)*.5
    power = effort*velocity_midpoint[e._motor_dof]
    work = (float(np.maximum(power, 0).sum())*dt,
            float(power.sum())*dt, 0.,
            float(np.maximum(-power, 0).sum())*dt,
            float(np.dot(m.dof_damping, velocity_midpoint**2))*dt,
            float(np.dot(m.dof_damping[e._self_dofs],
                         velocity_midpoint[e._self_dofs]**2))*dt)
    _finite(work)
    if work[0] > remaining:
        raise ValueError("mechanical energy supply exhausted; no successor")
    trace = np.einsum("ijk,ijk->i", rotation, d.geom_xmat.reshape(-1, 3, 3))
    angle = _finite(np.arccos(np.clip((trace-1)/2, -1, 1)))
    travel = _finite(np.linalg.norm(d.geom_xpos-position, axis=1)+m.geom_rbound*angle)
    peak = float(travel.max(initial=0.))
    if peak > e.limits.max_surface_travel_m:
        raise ValueError("surface movement exceeds collision sampling resolution")
    work = (work[0], work[1], peak, work[3], work[4], work[5])
    if float(d.time) != stop:
        raise ValueError("mechanical substep clock differs")
    mj.mj_forward(m, d)
    e._check()
    return (_snapshot(e), work, impulse)


def advance_interval(engine, effort, steps, available_work_j):
    """One bounded transaction; accuracy retries cannot publish or debit twice."""
    m, d = engine._model, engine._data
    if type(steps) is not int or not 0 < steps <= engine.limits.max_substeps:
        raise ValueError("bounded positive numerical interval required")
    if not math.isfinite(available_work_j) or available_work_j < 0:
        raise ValueError("finite mechanical supply required")
    original_dt = float(m.opt.timestep)
    initial = _state(engine)
    start = float(d.time)
    nominal = engine.limits.step_us/1_000_000
    total = (0.,)*6
    calls = 0
    ceiling = 3*engine.limits.max_substeps
    before = None

    def trial(stop, supply):
        nonlocal calls
        if calls >= ceiling:
            raise ValueError("native accuracy call allowance exhausted")
        calls += 1
        return _one_step(engine, effort, supply, stop)

    try:
        before = _snapshot(engine)
        for index in range(1, steps+1):
            stop = start + index*nominal
            # A retained first-half result can be the left child's exact
            # coarse trial. The right child must use its new accepted predecessor.
            pending = [(stop, 0, None)]
            while pending:
                target, depth, reused_coarse = pending.pop()
                begin = before["time"]
                dt = target-begin
                midpoint = begin+dt/2
                if not (math.isfinite(dt) and begin < midpoint < target):
                    raise ValueError("no representable accuracy subdivision")
                remaining = available_work_j-total[0]
                coarse = left = right = None
                numeric_refusal = False
                try:
                    if reused_coarse is None:
                        coarse = trial(target, remaining)
                    else:
                        coarse = reused_coarse
                        if coarse[0]["time"] != target:
                            raise ValueError("reused numerical stage clock differs")
                    _restore(engine, before["state"], before["dt"])
                    left = trial(midpoint, remaining)
                    right = trial(target, remaining-left[1][0])
                except mj.FatalError as error:
                    if "midpoint residual did not converge" not in str(error):
                        raise
                    numeric_refusal = True
                if not numeric_refusal:
                    fine_work = _work_add(left[1], right[1])
                    fine_impulse = _impulse_add(left[2], right[2])
                    boundary_change = not (before["domain"] == left[0]["domain"] == right[0]["domain"])
                    accepted = ((not boundary_change or dt/2 <= EVENT_S) and
                                _close(engine, coarse[0], right[0], coarse[1], fine_work,
                                       coarse[2], fine_impulse, dt))
                    if accepted:
                        total = _work_add(total, fine_work)
                        if total[0] > available_work_j:
                            raise ValueError("mechanical energy supply exhausted; no successor")
                        before = right[0]
                        continue
                _restore(engine, before["state"], before["dt"])
                if depth >= sys.float_info.mant_dig:
                    raise ValueError("bounded accuracy subdivision exhausted")
                pending.append((target, depth+1, None))
                pending.append((midpoint, depth+1, left))
        if float(d.time) != start+steps*nominal:
            raise ValueError("accuracy interval clock differs")
        m.opt.timestep = original_dt
        mj.mj_forward(m, d)
        engine._check()
        return total
    except BaseException:
        _restore(engine, initial, original_dt)
        raise
