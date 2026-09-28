"""Compiled, unmounted three-stage Radau IIA body candidate.

Same instantaneous forces, bounded coupled residual, and physical acceptance.
Fifth-order collocation is a numerical approximation, not a trajectory-wide
error guarantee. No persistent solver memory, controller, or motor plan.
"""
import base64
import hashlib
import math
import time

import mujoco as mj
import numpy as np
import guala_body_interval as interval
from libc.math cimport fabs, frexp, isfinite, ldexp, pow, sqrt, tan

RADAU_LAW = "radau-iia3-secant-solved-domain-v11-scaled-rotation"
MAX_LINE = 16
MAX_SECANT = 32
STAGE_COUNT = 3
# Integrals of the Lagrange basis at the right-Radau nodes. Positive final-row
# weights integrate polynomials through degree four; the final node is the end.
_root6 = math.sqrt(6.)
C = np.array(((4-_root6)/10, (4+_root6)/10, 1.))
A = np.array((
    ((88-7*_root6)/360, (296-169*_root6)/1800, (-2+3*_root6)/225),
    ((296+169*_root6)/1800, (88+7*_root6)/360, (-2-3*_root6)/225),
    ((16-_root6)/36, (16+_root6)/36, 1./9),
))
B = A[-1].copy()
# Positive quadratic quadrature through the start, second Radau node and end.
# These are integrated Lagrange weights, not fitted error tolerances.
_a = float(C[1])
E = np.array(((3*_a-1)/(6*_a), 1/(6*_a*(1-_a)), (2-3*_a)/(6*(1-_a))))
_middle_scale = float(E[1]/B[1])
for _coefficient in (A, B, C, E):
    _coefficient.flags.writeable = False
cdef double MACHINE_EPS = 2.220446049250313e-16

include "joint_event_law.pxi"

def packed_numbers(value):
    if value is None:
        return None
    a = np.asarray(value, dtype='<f8')
    return dict(shape=list(a.shape), finite=bool(np.isfinite(a).all()),
                float64_le_base64=base64.b64encode(a.tobytes()).decode())


def _record_domain(domain):
    return tuple(
        tuple(bool(x) for x in row) if index < 2 else
        tuple(int(x) for x in row) if index < 5 else
        tuple(tuple(int(x) for x in pair) for pair in row)
        for index,row in enumerate(domain))


def _record_impulses(impulses):
    return [dict(pair=pair,force=packed_numbers(values[0]),
                 couple=packed_numbers(values[1]),
                 force_path=float(values[2]),couple_path=float(values[3]))
            for pair,values in sorted(impulses.items())]


cdef double norm2(double[::1] a) except *:
    cdef Py_ssize_t i
    cdef double s = 0
    for i in range(a.shape[0]):
        if not isfinite(a[i]):
            raise ValueError('nonfinite matrix-free operand')
        s += a[i]*a[i]
    if not isfinite(s):
        raise ValueError('nonfinite matrix-free norm')
    return sqrt(s)


cdef double norm_inf(double[::1] a) except *:
    cdef Py_ssize_t i
    cdef double peak = 0
    for i in range(a.shape[0]):
        if not isfinite(a[i]):
            raise ValueError('nonfinite coupled residual')
        if fabs(a[i]) > peak:
            peak = fabs(a[i])
    return peak



def _integrate_local_rotation(quaternion, rotation_scratch):
    """Apply a local rotation vector without the native small-vector axis reset.

    The three-component rotation_scratch is caller-owned temporary storage:
    power-of-two rescaling overwrites it, never the retained chart variables.
    Its scaled maximum lies in [0.5, 1), keeping native normalization away
    from mjMINVAL and avoiding squared-norm underflow. Multiplication by the
    reciprocal power of two restores the angle; no physical threshold changes.
    """
    cdef double[::1] v = rotation_scratch
    cdef double peak = 0., scale = 1.
    cdef int exponent = 0
    cdef Py_ssize_t j
    if v.shape[0] != 3:
        raise ValueError("rotation scratch must have three components")
    for j in range(3):
        if not isfinite(v[j]):
            raise ValueError("nonfinite local rotation")
        if fabs(v[j]) > peak:
            peak = fabs(v[j])
    if math.hypot(v[0], v[1], v[2]) >= math.pi:
        raise ValueError("local rotation chart exceeded")
    if peak > 0.:
        frexp(peak, &exponent)
        scale = ldexp(1., exponent)
        for j in range(3):
            v[j] = ldexp(v[j], -exponent)
    mj.mju_quatIntegrate(quaternion, rotation_scratch, scale)


cdef class _Stages:
    cdef object e, m, d, owner, base, q_array, sigma_array
    cdef object boundary
    cdef object x_array, r_array, last_value, last_residual
    cdef double dt, t0, tolerance
    cdef Py_ssize_t n, size, kmax, rank
    cdef const double[:,::1] tableau
    cdef const double[::1] nodes
    cdef double[::1] q0, v0, q, v, acceleration, sigma_buffer
    cdef double[::1] x, residual, scale, update, delta_x, delta_r, image
    cdef double[::1] trial, trial_residual
    cdef double[:,::1] acc, tangent, inverse_left, inverse_right

    def __init__(self, e, base, double dt, owner, boundary=None):
        self.e, self.m, self.d, self.owner, self.base = e, e._model, e._data, owner, base
        self.boundary = boundary
        self.dt, self.t0 = dt, float(self.d.time)
        self.tolerance = float(self.m.opt.tolerance)
        if not isfinite(self.tolerance) or self.tolerance <= 0:
            raise ValueError('invalid existing residual tolerance')
        self.n = self.m.nv
        self.size = 3*self.n+9
        self.tableau, self.nodes = A, C
        self.kmax = min(self.size, MAX_SECANT)
        self.rank = 0
        self.q0 = self.d.qpos.copy()
        self.v0 = self.d.qvel.copy()
        self.q_array = self.d.qpos
        self.q, self.v, self.acceleration = self.q_array, self.d.qvel, self.d.qacc
        self.sigma_array = np.empty(3)
        self.sigma_buffer = self.sigma_array
        self.x_array, self.r_array = np.empty(self.size), np.empty(self.size)
        self.x, self.residual = self.x_array, self.r_array
        self.scale = np.empty(self.size)
        self.update = np.empty(self.size)
        self.delta_x, self.delta_r, self.image = np.empty(self.size), np.empty(self.size), np.empty(self.size)
        self.trial, self.trial_residual = np.empty(self.size), np.empty(self.size)
        self.acc, self.tangent = np.empty((3, self.n)), np.empty((3, 3))
        self.inverse_left = np.empty((self.kmax, self.size))
        self.inverse_right = np.empty((self.kmax, self.size))
        self.last_value = self.last_residual = None
        cdef Py_ssize_t i, j
        cdef double linear_scale = .001+.001*sqrt(
            self.v0[0]*self.v0[0]+self.v0[1]*self.v0[1]+self.v0[2]*self.v0[2])
        for i in range(3):
            for j in range(self.n):
                self.x[i*self.n+j] = self.v0[j]
                self.scale[i*self.n+j] = linear_scale if j < 3 else .01+.001*fabs(self.v0[j])
            for j in range(3):
                self.x[3*self.n+3*i+j] = dt*self.nodes[i]*self.v0[j+3]
                self.scale[3*self.n+3*i+j] = interval.ANGLE_RAD
        for j in range(self.size):
            if not isfinite(self.scale[j]) or self.scale[j] <= 0 or not isfinite(self.x[j]):
                raise ValueError('nonfinite or invalid coupled variable scale')

    cdef object evaluate(self, double[::1] values, double[::1] out, bint capture):
        cdef Py_ssize_t i, j, k, s, a, n = self.n
        cdef double sx, sy, sz, wx, wy, wz, cx, cy, cz, theta, square, coefficient
        cdef double total, stage_time, terminal_q = 0.
        self.last_value, self.last_residual = values, None
        for j in range(self.size):
            if not isfinite(values[j]):
                raise ValueError('nonfinite coupled trial')
        for i in range(3):
            s, a = 3*n+3*i, i*n+3
            sx, sy, sz = values[s], values[s+1], values[s+2]
            wx, wy, wz = values[a], values[a+1], values[a+2]
            square = sx*sx+sy*sy+sz*sz
            theta = sqrt(square)
            if not isfinite(theta) or theta >= math.pi:
                raise ValueError('local rotation chart exceeded; no pose clipping')
            if theta <= pow(MACHINE_EPS,1./6):
                coefficient = 1./12+square/720+square*square/30240
            else:
                coefficient = (1-(theta/2)/tan(theta/2))/square
            cx, cy, cz = sy*wz-sz*wy, sz*wx-sx*wz, sx*wy-sy*wx
            self.tangent[i,0] = wx+cx/2+coefficient*(sy*cz-sz*cy)
            self.tangent[i,1] = wy+cy/2+coefficient*(sz*cx-sx*cz)
            self.tangent[i,2] = wz+cz/2+coefficient*(sx*cy-sy*cx)
        stages = [] if capture else None
        for i in range(3):
            mj.mj_setState(self.m, self.d, self.base, interval.STATE_KIND)
            for j in range(self.q.shape[0]):
                self.q[j] = self.q0[j]
            for j in range(3):
                total = 0.
                for k in range(3):
                    total += self.tableau[i,k]*values[k*n+j]
                self.q[j] += self.dt*total
                self.sigma_buffer[j] = values[3*n+3*i+j]
            for j in range(6, n):
                total = 0.
                for k in range(3):
                    total += self.tableau[i,k]*values[k*n+j]
                self.q[j+1] += self.dt*total
            _integrate_local_rotation(self.q_array[3:7], self.sigma_array)
            for j in range(n):
                self.v[j] = values[i*n+j]
            stage_time = self.t0+self.nodes[i]*self.dt
            self.d.time = stage_time
            # Force scratch only: preserve the solved collocation coordinate.
            # The event-time transaction below is the sole caller of this mode.
            if i == 2 and self.boundary is not None:
                terminal_q = self.q[self.boundary['qadr']]
                self.q[self.boundary['qadr']] = self.boundary['incoming_q']
            self.owner.forward(self.e)
            for j in range(n):
                self.acc[i,j] = self.acceleration[j]
            if capture:
                self.e._check()
                power = self.d.ctrl*self.d.qvel[self.e._motor_dof]
                work = np.array((np.maximum(power,0).sum(),power.sum(),0.,
                    np.maximum(-power,0).sum(),np.dot(self.m.dof_damping,self.d.qvel**2),
                    np.dot(self.m.dof_damping[self.e._self_dofs],self.d.qvel[self.e._self_dofs]**2)))
                stages.append(dict(snapshot=interval._snapshot(self.e),
                    qpos=self.d.qpos.copy(),qvel=self.d.qvel.copy(),qacc=self.d.qacc.copy(),
                    work=interval._finite(work),
                    impulse=interval._midpoint_impulses(self.m,self.d,self.dt*B[i])))
            if i == 2 and self.boundary is not None:
                self.q[self.boundary['qadr']] = terminal_q
                if capture:
                    stages[-1]['qpos'][self.boundary['qadr']] = terminal_q
                    stages[-1]['one_sided_force_coordinate'] = self.boundary['incoming_q']
        for i in range(3):
            for j in range(n):
                total = 0.
                for k in range(3):
                    total += self.tableau[i,k]*self.acc[k,j]
                s = i*n+j
                out[s] = (values[s]-self.v0[j]-self.dt*total)/self.scale[s]
            for j in range(3):
                total = 0.
                for k in range(3):
                    total += self.tableau[i,k]*self.tangent[k,j]
                s = 3*n+3*i+j
                out[s] = (values[s]-self.dt*total)/self.scale[s]
        self.last_residual = out
        norm_inf(out)
        return stages

    cdef void inverse_product(self, double[::1] operand, double[::1] out) except *:
        cdef Py_ssize_t i, j
        cdef double coefficient
        for i in range(self.size): out[i] = operand[i]
        for j in range(self.rank):
            coefficient = 0
            for i in range(self.size): coefficient += self.inverse_right[j,i]*operand[i]
            if not isfinite(coefficient): raise ValueError('nonfinite inverse-secant projection')
            for i in range(self.size): out[i] += self.inverse_left[j,i]*coefficient
        norm_inf(out)

    cdef object solve(self, object receipt):
        cdef Py_ssize_t iteration, power, i
        cdef double norm, trial_norm, multiplier, length
        cdef bint accepted, differs
        # H_0=I is the zero-duration Jacobian limit in the existing scaled variables.
        self.evaluate(self.x,self.residual,False)
        norm = norm_inf(self.residual)
        for iteration in range(self.kmax):
            if norm <= self.tolerance: break
            self.inverse_product(self.residual,self.update)
            accepted = False
            for power in range(MAX_LINE):
                multiplier = math.ldexp(1.,-power)
                differs = False
                for i in range(self.size):
                    self.trial[i] = self.x[i]-multiplier*self.scale[i]*self.update[i]
                    if self.trial[i] != self.x[i]: differs = True
                if not differs: break
                self.evaluate(self.trial,self.trial_residual,False)
                trial_norm = norm_inf(self.trial_residual)
                if trial_norm < norm or trial_norm <= self.tolerance:
                    receipt['iterations'].append(dict(before=norm,after=trial_norm,line_divisions=power))
                    for i in range(self.size):
                        self.delta_x[i] = (self.trial[i]-self.x[i])/self.scale[i]
                        self.delta_r[i] = self.trial_residual[i]-self.residual[i]
                        self.x[i], self.residual[i] = self.trial[i],self.trial_residual[i]
                    norm,accepted = trial_norm,True
                    break
            if not accepted: raise ValueError('coupled Radau residual failed to decrease')
            if norm <= self.tolerance: break
            # H+=H+(s-Hy)y^T/(y^Ty), normalized to avoid squaring a small denominator.
            length = norm2(self.delta_r)
            if length == 0: raise ValueError('zero residual change in inverse-secant update')
            for i in range(self.size): self.delta_r[i] /= length
            self.inverse_product(self.delta_r,self.image)
            for i in range(self.size):
                self.inverse_left[self.rank,i] = self.delta_x[i]/length-self.image[i]
                self.inverse_right[self.rank,i] = self.delta_r[i]
                if not isfinite(self.inverse_left[self.rank,i]):
                    raise ValueError('nonfinite inverse-secant update')
            self.rank += 1
            receipt['secant_updates'].append(dict(rank=self.rank,residual_change_norm=length))
        if norm > self.tolerance: raise ValueError('bounded inverse-secant iterations exhausted')
        stages = self.evaluate(self.x,self.residual,True)
        norm = norm_inf(self.residual)
        if norm > self.tolerance: raise ValueError('captured coupled stage residual differs')
        receipt['final_residual'] = norm
        return stages


def sampled_event_path(before, values):
    """Observed numerical-path brackets; not an enclosure of unseen crossings."""
    sequence = [before['domain']]
    brackets = []
    resolved = True
    for piece_index, value in enumerate(values):
        samples = [before, *(stage['snapshot'] for stage in value[3]), value[0]]
        for index in range(1, len(samples)):
            left, right = samples[index-1], samples[index]
            lo, hi = left['time'], right['time']
            if not (math.isfinite(lo) and math.isfinite(hi)) or hi < lo:
                raise ValueError('invalid chronological event sample')
            if left['domain'] != right['domain']:
                # Contradictory observations at one time are unresolved, not
                # zero-width physical transitions.
                resolved = resolved and hi > lo
                brackets.append(dict(piece_index=piece_index, from_sample=index-1,
                    to_sample=index, start_s=lo, end_s=hi))
                sequence.append(right['domain'])
        before = value[0]
    return dict(sequence=tuple(sequence), brackets=brackets, resolved=resolved)


def sampled_event_comparison(before, coarse, left, right):
    coarse_events = sampled_event_path(before, (coarse,))
    fine_events = sampled_event_path(before, (left,right))
    same_sequence = coarse_events['sequence'] == fine_events['sequence']
    resolved = coarse_events['resolved'] and fine_events['resolved']
    narrow = all(event['end_s']-event['start_s'] <= interval.EVENT_S
                 for event in fine_events['brackets'])
    overlap = same_sequence and all(
        max(a['start_s'],b['start_s']) <= min(a['end_s'],b['end_s'])
        for a,b in zip(coarse_events['brackets'],fine_events['brackets']))
    return dict(passed=resolved and same_sequence and narrow and overlap,
        same_sequence=same_sequence, resolved=resolved, fine_brackets_within_limit=narrow,
        corresponding_brackets_overlap=overlap, coarse_brackets=coarse_events['brackets'],
        fine_brackets=fine_events['brackets'])


include "one_sided_joint_event.pxi"


class RadauProbe:
    """Offline call-bounded probe; never imported into organism/runtime custody."""
    def __init__(self, ceiling):
        if type(ceiling) is not int or ceiling <= 0:
            raise ValueError('positive force-evaluation ceiling required')
        self.ceiling, self.calls, self.native_seconds = ceiling,0,0.
        self.steps = []

    def forward(self, e):
        if self.calls >= self.ceiling:
            raise RuntimeError('bounded diagnostic force-evaluation allowance exhausted')
        self.calls += 1
        started = time.perf_counter()
        try: mj.mj_forward(e._model,e._data)
        finally: self.native_seconds += time.perf_counter()-started
        if e._data.warning.number.any(): raise ValueError('native warning in diagnostic force evaluation')
        interval._finite(e._data.qacc)

    def step(self, e, dt, supply):
        return _event_aligned_step(self,e,dt,supply)

    def _plain_step(self, e, dt, supply, boundary=None):
        cdef _Stages solver = None
        m,d = e._model,e._data
        if not math.isfinite(dt) or not 0 < dt <= e.limits.step_us/1e6:
            raise ValueError('diagnostic step must not enlarge declared timestep')
        if not math.isfinite(supply) or supply < 0: raise ValueError('invalid work supply')
        if (m.nq != m.nv+1 or m.nv < 6 or m.jnt_type[0] != mj.mjtJoint.mjJNT_FREE or
                not np.all(m.jnt_type[1:] == mj.mjtJoint.mjJNT_HINGE)):
            raise ValueError('probe covers the declared one-free-root hinge anatomy only')
        base = interval._state(e)
        original_dt = float(m.opt.timestep)
        before = interval._snapshot(e)
        t0 = float(d.time)
        end = t0+dt
        if not math.isfinite(end) or end <= t0: raise ValueError('unrepresentable interval')
        dt = end-t0
        m.opt.timestep = dt
        receipt = dict(dt_s=dt,start_s=t0,iterations=[],secant_updates=[],converged=False,
                       calls_start=self.calls,failure=None)
        self.steps.append(receipt)
        try:
            # Compare the actual Radau impulse with a positive start-inclusive
            # quadratic estimate. Neither estimator replaces force or dynamics.
            initial_impulse = interval._midpoint_impulses(m,d,dt*E[0])
            solver = _Stages(e,base,dt,self,boundary)
            stages = solver.solve(receipt)
            terminal_impulse = interval._midpoint_impulses(m,d,dt*E[2])
            work = interval._finite(dt*sum((B[i]*stages[i]['work'] for i in range(3)),start=np.zeros(6)))
            if work[0] > supply: raise ValueError('mechanical energy supply exhausted; no successor')
            if any(work[i] < 0 for i in (0,3,4,5)): raise ValueError('negative physical dissipative quadrature')
            d.qacc_warmstart[:] = stages[-1]['qacc']
            self.forward(e)
            e._check()
            if float(d.time) != end: raise ValueError('Radau endpoint clock differs')
            endpoint = interval._snapshot(e)
            if boundary is not None:
                # Native endpoint observation is NOT the one-sided force
                # approximation. Retain each separately and never persist the
                # force-evaluation coordinate as physical body state.
                stages[-1]['force_snapshot'] = stages[-1]['snapshot']
                stages[-1]['snapshot'] = endpoint
                stages[-1]['collocation_residual'] = receipt['final_residual']
            travel = []
            for stage in stages:
                snap = stage['snapshot']
                relative = interval._finite(np.einsum('nji,njk->nik',before['rotation'],snap['rotation']))
                skew = np.stack((relative[:,2,1]-relative[:,1,2],relative[:,0,2]-relative[:,2,0],
                                 relative[:,1,0]-relative[:,0,1]),axis=1)
                angle = interval._finite(np.arctan2(np.linalg.norm(skew,axis=1),np.trace(relative,axis1=1,axis2=2)-1))
                surface = interval._finite(np.linalg.norm(snap['position']-before['position'],axis=1)+m.geom_rbound*angle)
                travel.append(float(np.max(surface)))
            work[2] = max(travel)
            interval._finite(work)
            if work[2] > e.limits.max_surface_travel_m:
                raise ValueError('sampled surface travel exceeds existing limit')
            impulse = {}
            for stage in stages:
                impulse = interval._impulse_add(impulse,stage['impulse'])
            # Reweight the existing middle-stage impulse; no new force solve.
            middle = {pair:tuple(interval._finite(x*_middle_scale) for x in values)
                      for pair,values in stages[1]['impulse'].items()}
            embedded = interval._impulse_add(
                interval._impulse_add(initial_impulse,middle),terminal_impulse)
            receipt['contact_impulse_estimator_passed'] = interval._impulses_close(embedded,impulse,dt)
            if not receipt['contact_impulse_estimator_passed']:
                raise ValueError('contact impulse embedded quadrature unresolved')
            # The same sampled bin may hide several distinct joint releases.
            # Refine the actual dynamics instead of fabricating an intermediate
            # solver domain from Boolean flags or accepting the merged record.
            domains = tuple(s['snapshot']['domain'] for s in stages)
            operands = {}
            for kind in (0,1):
                for ordinal, active in enumerate(before['domain'][kind]):
                    if all(active == domain[kind][ordinal] for domain in domains):
                        continue
                    joint = int(e._limited[ordinal])
                    qa,va = int(m.jnt_qposadr[joint]),int(m.jnt_dofadr[joint])
                    operands[(kind,ordinal)] = (
                        float(solver.q0[qa]), *(float(s['qpos'][qa]) for s in stages),
                        *(float(s['qvel'][va]) for s in stages),
                        float(m.jnt_range[joint,kind]+(1 if kind == 0 else -1)*m.jnt_margin[joint]),dt)
            resolution = joint_sample_resolution(before['domain'],domains,operands)
            if resolution['groups']:
                receipt['joint_event_resolution'] = resolution
            if not resolution['resolved']:
                raise ValueError('multiple joint-limit events unresolved in sampled interval')
            receipt.update(converged=True,calls=self.calls-receipt['calls_start'],
                sampled_domain_unchanged=all(before['domain']==s['snapshot']['domain'] for s in stages)
                    and before['domain']==endpoint['domain'],
                work=work.tolist(),sampled_surface_travel_m=travel)
            m.opt.timestep = original_dt
            return endpoint,tuple(work),impulse,stages
        except BaseException as error:
            receipt.update(failure=repr(error),calls=self.calls-receipt['calls_start'],
                last_nonlinear_iterate=packed_numbers(None if solver is None else solver.last_value),
                last_normalized_residual=packed_numbers(None if solver is None else solver.last_residual),
                rollback_exact=False)
            interval._restore(e,base,original_dt)
            restored = interval._state(e)
            receipt['raw_rollback_state'] = packed_numbers(restored)
            receipt['rollback_exact'] = (restored.astype('<f8',copy=False).tobytes()
                                          == base.astype('<f8',copy=False).tobytes())
            if not receipt['rollback_exact']: raise AssertionError('diagnostic rollback differs') from error
            raise

    def admit(self, e, stop, supply, nominal_dt, max_trials):
        """Offline local-admission transaction; not production custody or global-error proof."""
        m, d = e._model, e._data
        start = float(d.time)
        if not (math.isfinite(stop) and stop > start and math.isfinite(nominal_dt)
                and 0 < nominal_dt <= e.limits.step_us/1e6):
            raise ValueError('invalid bounded Radau admission interval')
        if not math.isfinite(supply) or supply < 0:
            raise ValueError('invalid work supply')
        if type(max_trials) is not int or max_trials <= 0:
            raise ValueError('positive admission trial allowance required')
        initial, original_dt = interval._state(e), float(m.opt.timestep)
        total, impulses = (0.,)*6, {}
        report = dict(start_s=start, stop_s=stop, nominal_dt_s=nominal_dt,
            max_trials=max_trials, trials=0, reused=0, accepted=[], rejected=[],
            completed=False, rollback_exact=None, failure=None)
        self.last_admission = report
        maximum_depth = int(np.finfo(float).nmant)+1
        refinable = {
            'coupled Radau residual failed to decrease',
            'bounded inverse-secant iterations exhausted',
            'captured coupled stage residual differs',
            'contact impulse embedded quadrature unresolved',
            'multiple joint-limit events unresolved in sampled interval',
            'one-sided joint event requires subdivision',
        }

        def trial(end, remaining):
            if report['trials'] >= max_trials:
                raise RuntimeError('bounded Radau admission trial allowance exhausted')
            report['trials'] += 1
            predecessor = interval._state(e)
            begin = float(d.time)
            report['attempt'] = dict(start_s=begin, end_s=end, supply_j=remaining,
                predecessor=packed_numbers(predecessor))
            value = self.step(e,end-begin,remaining)
            return dict(begin=begin, end=end, supply=remaining,
                        predecessor=predecessor, value=value)

        try:
            before = interval._snapshot(e)
            while before['time'] < stop:
                begin = before['time']
                remaining_time = stop-begin
                if remaining_time <= nominal_dt:
                    target = stop
                elif remaining_time <= 2*nominal_dt:
                    target = begin+remaining_time/2
                else:
                    target = begin+nominal_dt
                if target-begin > nominal_dt:
                    target = math.nextafter(target,begin)
                pending = [(target,0,None)]
                while pending:
                    target, depth, reused = pending.pop()
                    begin, base = before['time'], before['state']
                    dt = target-begin
                    midpoint = begin+dt/2
                    if not (math.isfinite(dt) and begin < midpoint < target):
                        raise ValueError('no representable Radau admission subdivision')
                    remaining = supply-total[0]
                    coarse = left = right = None
                    numeric_refusal = None
                    event_test = None
                    try:
                        if reused is None:
                            coarse = trial(target,remaining)
                            interval._restore(e,base,original_dt)
                        else:
                            base_bytes = base.astype('<f8',copy=False).tobytes()
                            if (reused['begin'] != begin or reused['end'] != target
                                    or reused['supply'] != remaining
                                    or reused['predecessor'].astype('<f8',copy=False).tobytes() != base_bytes
                                    or interval._state(e).astype('<f8',copy=False).tobytes() != base_bytes):
                                raise AssertionError('Radau reused trial predecessor differs')
                            coarse = reused
                            report['reused'] += 1
                        left = trial(midpoint,remaining)
                        right = trial(target,remaining-left['value'][1][0])
                    except ValueError as error:
                        if str(error) not in refinable:
                            raise
                        numeric_refusal = str(error)
                    accepted = False
                    if numeric_refusal is None:
                        c, l, r = coarse['value'],left['value'],right['value']
                        work = interval._work_add(l[1],r[1])
                        impulse = interval._impulse_add(l[2],r[2])
                        event_test = sampled_event_comparison(before,c,l,r)
                        accepted = (event_test['passed']
                            and interval._close(e,c[0],r[0],c[1],work,c[2],impulse,dt))
                        if accepted:
                            total = interval._work_add(total,work)
                            impulses = interval._impulse_add(impulses,impulse)
                            if total[0] > supply:
                                raise ValueError('mechanical energy supply exhausted; no successor')
                            for piece_index, piece in enumerate((left,right)):
                                value = piece['value']
                                report['accepted'].append(dict(start_s=piece['begin'],end_s=piece['end'],
                                    predecessor_sha256=hashlib.sha256(piece['predecessor'].astype('<f8').tobytes()).hexdigest(),
                                    state=packed_numbers(value[0]['state']),work=value[1],
                                    available_work_j=piece['supply'],
                                    joint_boundaries=[stage['joint_boundary'] for stage in value[3]
                                                      if 'joint_boundary' in stage],
                                    event_sequence=tuple(_record_domain(domain) for domain in
                                        sampled_event_path(
                                            before if piece_index == 0 else left['value'][0],
                                            (value,))['sequence']),
                                    event_brackets=[event for event in event_test['fine_brackets']
                                                    if event['piece_index'] == piece_index]))
                            before = r[0]
                            continue
                    report['rejected'].append(dict(start_s=begin,end_s=target,
                        numerical_refusal=numeric_refusal,local_accuracy_rejected=numeric_refusal is None,
                        event_test=event_test))
                    interval._restore(e,base,original_dt)
                    if depth >= maximum_depth:
                        raise ValueError('bounded Radau admission subdivision exhausted')
                    pending.append((target,depth+1,None))
                    pending.append((midpoint,depth+1,left))
            if float(d.time) != stop:
                raise ValueError('Radau admission endpoint clock differs')
            m.opt.timestep = original_dt
            self.forward(e)
            e._check()
            successor = interval._snapshot(e)
            report.update(completed=True,work=total,remaining_supply_j=supply-total[0])
            return successor,total,impulses,report
        except BaseException as error:
            report['failure'] = repr(error)
            interval._restore(e,initial,original_dt)
            report['rollback_exact'] = (interval._state(e).astype('<f8',copy=False).tobytes()
                                        == initial.astype('<f8',copy=False).tobytes())
            if not report['rollback_exact']:
                raise AssertionError('Radau admission rollback differs') from error
            raise


    def admit_history_pair(self, e, lanes, stop, history_start, supply,
                           nominal_dts, max_trials):
        """Advance two OWN unpublished predecessors; refine timing locally.

        A returned pair has passed the unchanged physical comparison. Every
        exception restores the entry engine exactly. Supplied lane objects are
        never mutated. No trial work is debited into an accepted predecessor.
        """
        now, original_dt = float(e._data.time), float(e._model.opt.timestep)
        if (len(lanes) != 2 or len(nominal_dts) != 2
                or not math.isfinite(history_start) or history_start > now
                or not math.isfinite(stop) or not 0 < stop-now <= e.limits.step_us/1e6
                or any(lane['snapshot']['time'] != now for lane in lanes)
                or any(not math.isfinite(h) or not 0 < h <= e.limits.step_us/1e6
                       for h in nominal_dts)
                or not math.isfinite(supply) or supply < 0
                or type(max_trials) is not int or max_trials <= 0):
            raise ValueError('invalid independent history pair interval')
        entry_state = interval._state(e)
        report = dict(law='radau-iia3-local-paired-events-v1',start_s=now,
            stop_s=stop,history_start_s=history_start,nominal_dts=tuple(nominal_dts),
            max_trials=max_trials,trials=0,rounds=[],completed=False,
            failure=None,rollback_exact=None,active_attempt=None,disagreement=None)
        self.last_pair_admission = report
        try:
            for refinement in range(int(np.finfo(float).nmant)+1):
                steps = tuple(math.ldexp(h,-refinement) for h in nominal_dts)
                if any(now+h <= now for h in steps):
                    break
                attempt = dict(refinement=refinement,nominal_dts=steps,
                               lanes=[],agreement=None)
                report['rounds'].append(attempt)
                candidates = []
                for index,(before,h) in enumerate(zip(lanes,steps)):
                    remaining = supply-before['work'][0]
                    evidence = dict(lane='coarse' if index == 0 else 'fine',
                        start_s=now,target_s=stop,phase='lane_restore',
                        predecessor=packed_numbers(before['snapshot']['state']),
                        prior_work=before['work'],available_work_j=remaining,
                        local_report=None)
                    attempt['lanes'].append(evidence)
                    report['active_attempt'] = evidence
                    self.last_admission = None
                    allowance = max_trials-report['trials']
                    if allowance <= 0:
                        raise RuntimeError('trajectory trial allowance exhausted')
                    if not math.isfinite(remaining) or remaining < 0:
                        raise ValueError('trajectory work supply exhausted')
                    interval._restore(e,before['snapshot']['state'],original_dt)
                    if interval._state(e).tobytes() != before['snapshot']['state'].tobytes():
                        raise AssertionError('trajectory lane restore differs')
                    evidence['phase'] = 'local_admission'
                    try:
                        snap,work,impulses,local = self.admit(e,stop,remaining,h,allowance)
                    finally:
                        local = self.last_admission
                        evidence['local_report'] = local
                        if local is not None:
                            report['trials'] += local['trials']
                    sequence,brackets = [_record_domain(before['snapshot']['domain'])],[]
                    for piece in local['accepted']:
                        events = piece['event_sequence']
                        if (not events or events[0] != sequence[-1]
                                or len(events)-1 != len(piece['event_brackets'])):
                            raise AssertionError('accepted event chronology differs')
                        sequence.extend(events[1:]);brackets.extend(piece['event_brackets'])
                    candidate = dict(snapshot=snap,
                        work=interval._work_add(before['work'],work),
                        impulses=interval._impulse_add(before['impulses'],impulses),
                        sequence=tuple(sequence),brackets=brackets)
                    candidates.append(candidate)
                    if snap['time'] != stop or candidate['work'][0] > supply:
                        raise ValueError('trajectory lane custody differs')
                report['active_attempt']['phase'] = 'history_comparison'
                agreement = trajectory_agreement(e,*candidates,stop-history_start)
                attempt['agreement'] = agreement
                if agreement['passed']:
                    report.update(completed=True,active_attempt=None)
                    return candidates,report
                a,b = candidates
                report['disagreement'] = dict(time_s=stop,**agreement,
                    coarse_state=packed_numbers(a['snapshot']['state']),
                    fine_state=packed_numbers(b['snapshot']['state']),
                    coarse_work=a['work'],fine_work=b['work'],
                    coarse_sequence=a['sequence'],fine_sequence=b['sequence'],
                    coarse_brackets=a['brackets'],fine_brackets=b['brackets'],
                    coarse_impulses=_record_impulses(a['impulses']),
                    fine_impulses=_record_impulses(b['impulses']))
                # Only resolution of a matching event path can retry here.
                # Inherited state/path error returns to the existing outer
                # independent-history refinement, not a synchronized state.
                if not (agreement['state_work_impulse_passed'] and
                        agreement['same_event_sequence']):
                    break
            raise ValueError('paired history interval remains unresolved')
        except BaseException as error:
            report.update(completed=False,failure=repr(error))
            # Preserve the actual failed scratch state before rollback. Native
            # extraction deliberately precedes finite-state validation so a
            # refused nonfinite state cannot erase its diagnostic evidence.
            try:
                failed_state = np.empty_like(entry_state)
                mj.mj_getState(e._model,e._data,failed_state,interval.STATE_KIND)
                report['failure_state'] = packed_numbers(failed_state)
                report['failure_time_s'] = float(e._data.time)
            except BaseException as evidence_error:
                report['failure_state_error'] = repr(evidence_error)
            interval._restore(e,entry_state,original_dt)
            report['rollback_exact'] = (interval._state(e).tobytes() == entry_state.tobytes()
                                       and float(e._model.opt.timestep) == original_dt)
            if not report['rollback_exact']:
                raise AssertionError('history pair rollback differs') from error
            raise

    def admit_trajectory(self, e, stop, supply, nominal_dt, sample_dt,
                         max_trials, max_refinements):
        """Two independent meshes over one unpublished physical interval.

        Local admission still controls residuals, force/work quadrature and
        sampled events. This outer guard preserves BOTH numerical histories
        across common observations. Event resolution retries the current pair;
        inherited errors retry the original uncommitted predecessor. No history
        synchronization, double debit, changed forces or relaxed tolerances.
        Sample agreement is not a
        continuum enclosure or a production cost certificate.
        """
        m, d = e._model, e._data
        start, original_dt = float(d.time), float(m.opt.timestep)
        if not (math.isfinite(stop) and start < stop
                and stop-start <= e.limits.max_substeps*e.limits.step_us/1e6
                and math.isfinite(nominal_dt) and math.isfinite(sample_dt)
                and 0 < nominal_dt <= sample_dt <= e.limits.step_us/1e6):
            raise ValueError('invalid bounded trajectory interval')
        if not math.isfinite(supply) or supply < 0:
            raise ValueError('invalid trajectory work supply')
        if (type(max_trials) is not int or max_trials <= 0
                or type(max_refinements) is not int
                or not 0 <= max_refinements <= int(np.finfo(float).nmant)):
            raise ValueError('invalid trajectory numerical work allowance')
        initial = interval._snapshot(e)
        report = dict(law='radau-iia3-independent-history-v2-local-events',
            start_s=start, stop_s=stop, nominal_dt_s=nominal_dt,
            sample_dt_s=sample_dt, max_trials=max_trials,
            max_refinements=max_refinements, trials=0, rounds=[],
            completed=False, failure=None, rollback_exact=None)
        self.last_trajectory_admission = report

        try:
            for refinement in range(max_refinements+1):
                coarse_dt = math.ldexp(nominal_dt,-refinement)
                fine_dt = coarse_dt/2
                if not 0 < fine_dt < coarse_dt:
                    raise ValueError('unrepresentable trajectory refinement')
                interval._restore(e,initial['state'],original_dt)
                lanes = [dict(snapshot=initial,work=(0.,)*6,impulses={})
                         for _ in range(2)]
                entry = dict(refinement=refinement,coarse_dt_s=coarse_dt,
                    fine_dt_s=fine_dt,observations=0,accepted=False,
                    disagreement=None,local_event_refinements=[])
                report['rounds'].append(entry)
                now = start
                while now < stop:
                    duration = stop-now
                    target = stop if duration <= sample_dt else (
                        now+duration/2 if duration <= 2*sample_dt else now+sample_dt)
                    if target-now > sample_dt:
                        target = math.nextafter(target,now)
                    if not now < target <= stop:
                        raise ValueError('unrepresentable trajectory sample')
                    allowance = max_trials-report['trials']
                    if allowance <= 0:
                        raise RuntimeError('trajectory trial allowance exhausted')
                    self.last_pair_admission = None
                    try:
                        successors,pair = self.admit_history_pair(
                            e,lanes,target,start,supply,(coarse_dt,fine_dt),allowance)
                    except ValueError as error:
                        if str(error) != 'paired history interval remains unresolved':
                            raise
                        entry['disagreement'] = self.last_pair_admission['disagreement']
                        break
                    finally:
                        pair = self.last_pair_admission
                        if pair is not None:
                            report['trials'] += pair['trials']
                            report['active_attempt'] = pair['active_attempt']
                            if pair['active_attempt'] is not None:
                                report['active_attempt']['refinement'] = refinement
                            if len(pair['rounds']) > 1 or not pair['completed']:
                                entry['local_event_refinements'].append(pair)
                    lanes = successors
                    entry['observations'] += 1
                    now = target
                if now == stop:
                    fine = lanes[1]
                    report['active_attempt'] = dict(phase='successor_preparation',
                        refinement=refinement,lane='fine',target_s=stop,
                        expected_successor=packed_numbers(fine['snapshot']['state']),
                        work=fine['work'],remaining_supply_j=supply-fine['work'][0])
                    interval._restore(e,fine['snapshot']['state'],original_dt)
                    if interval._state(e).tobytes() != fine['snapshot']['state'].tobytes():
                        raise AssertionError('trajectory successor restore differs')
                    successor = interval._snapshot(e)
                    if successor['state'].tobytes() != fine['snapshot']['state'].tobytes():
                        raise AssertionError('prepared trajectory successor differs')
                    entry['accepted'] = True
                    report.update(completed=True,work=fine['work'],
                        remaining_supply_j=supply-fine['work'][0],active_attempt=None)
                    return successor,fine['work'],fine['impulses'],report
            raise ValueError('independent trajectory histories remain unresolved')
        except BaseException as error:
            report.update(completed=False,failure=repr(error))
            if report['rounds']:
                report['rounds'][-1]['accepted'] = False
            interval._restore(e,initial['state'],original_dt)
            report['rollback_exact'] = (
                interval._state(e).tobytes() == initial['state'].tobytes())
            if not report['rollback_exact']:
                raise AssertionError('trajectory rollback differs') from error
            raise


def trajectory_agreement(e, coarse, fine, elapsed):
    """Compare actual history returns, not two resets to a shared current state."""
    if not math.isfinite(elapsed) or elapsed <= 0:
        raise ValueError('positive physical history interval required')
    a,b = coarse['snapshot'],fine['snapshot']
    if a['time'] != b['time']:
        raise ValueError('trajectory observation clocks differ')
    state_passed = interval._close(e,a,b,coarse['work'],fine['work'],
                                  coarse['impulses'],fine['impulses'],elapsed)
    same_sequence = coarse['sequence'] == fine['sequence']
    ab,bb = coarse['brackets'],fine['brackets']
    if (len(coarse['sequence']) != len(ab)+1
            or len(fine['sequence']) != len(bb)+1):
        raise ValueError('trajectory event evidence incomplete')
    bounded = len(ab)==len(bb) and all(
        math.isfinite(v['start_s']) and math.isfinite(v['end_s'])
        and 0 < v['end_s']-v['start_s'] <= interval.EVENT_S
        for v in (*ab,*bb))
    paired = same_sequence and bounded and all(
        max(x['end_s'],y['end_s'])-min(x['start_s'],y['start_s']) <= interval.EVENT_S
        for x,y in zip(ab,bb))
    return dict(passed=state_passed and same_sequence and paired,
                state_work_impulse_passed=state_passed,
                same_event_sequence=same_sequence,
                paired_event_brackets_within_limit=paired)
