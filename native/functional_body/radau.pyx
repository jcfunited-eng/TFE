"""Compiled, unmounted two-stage Radau body candidate.

Same instantaneous native forces and reviewed offline equations. Typed loops
remove repeated Python vector algebra, not force evaluations or acceptance
checks. No organism import, persistent solver state, controller or motor plan.
The fixed diagnostic trace is returned to its offline caller only.
"""
import base64
import math
import time

import mujoco as mj
import numpy as np
import guala_body_interval as interval
from libc.math cimport fabs, isfinite, pow, sqrt, tan

RADAU_LAW = "radau-iia2-krylov-candidate-v1"
MAX_NEWTON = 6
MAX_LINE = 16
MAX_KRYLOV = 32
EPS = np.finfo(float).eps
B = np.array((.75, .25))
cdef double MACHINE_EPS = 2.220446049250313e-16


def packed_numbers(value):
    if value is None:
        return None
    a = np.asarray(value, dtype='<f8')
    return dict(shape=list(a.shape), finite=bool(np.isfinite(a).all()),
                float64_le_base64=base64.b64encode(a.tobytes()).decode())


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


cdef class _Stages:
    cdef object e, m, d, owner, base, q_array, sigma_array
    cdef object x_array, r_array, h_array, target_array, last_value, last_residual
    cdef double dt, t0, tolerance
    cdef Py_ssize_t n, size, kmax
    cdef double[::1] q0, v0, q, v, acceleration, sigma_buffer
    cdef double[::1] x, residual, scale, plus, minus, rp, rm, w, update
    cdef double[::1] trial, trial_residual, target, weights
    cdef double[:,::1] acc, tangent, basis, hessenberg

    def __init__(self, e, base, double dt, owner):
        self.e, self.m, self.d, self.owner, self.base = e, e._model, e._data, owner, base
        self.dt, self.t0 = dt, float(self.d.time)
        self.tolerance = float(self.m.opt.tolerance)
        if not isfinite(self.tolerance) or self.tolerance <= 0:
            raise ValueError('invalid existing residual tolerance')
        self.n = self.m.nv
        self.size = 2*self.n+6
        self.kmax = min(self.size, MAX_KRYLOV)
        self.q0 = self.d.qpos.copy()
        self.v0 = self.d.qvel.copy()
        self.q_array = self.d.qpos
        self.q, self.v, self.acceleration = self.q_array, self.d.qvel, self.d.qacc
        self.sigma_array = np.empty(3)
        self.sigma_buffer = self.sigma_array
        self.x_array, self.r_array = np.empty(self.size), np.empty(self.size)
        self.x, self.residual = self.x_array, self.r_array
        self.scale = np.empty(self.size)
        self.plus, self.minus = np.empty(self.size), np.empty(self.size)
        self.rp, self.rm, self.w = np.empty(self.size), np.empty(self.size), np.empty(self.size)
        self.update = np.empty(self.size)
        self.trial, self.trial_residual = np.empty(self.size), np.empty(self.size)
        self.acc, self.tangent = np.empty((2, self.n)), np.empty((2, 3))
        # Krylov directions are rows: scalar sweeps touch contiguous storage.
        self.basis = np.empty((self.kmax+1, self.size))
        self.h_array = np.zeros((self.kmax+1, self.kmax))
        self.hessenberg = self.h_array
        self.target_array = np.zeros(self.kmax+1)
        self.target = self.target_array
        self.last_value = self.last_residual = None
        cdef Py_ssize_t i, j
        cdef double linear_scale = .001+.001*sqrt(
            self.v0[0]*self.v0[0]+self.v0[1]*self.v0[1]+self.v0[2]*self.v0[2])
        for i in range(2):
            for j in range(self.n):
                self.x[i*self.n+j] = self.v0[j]
                self.scale[i*self.n+j] = linear_scale if j < 3 else .01+.001*fabs(self.v0[j])
            for j in range(3):
                self.x[2*self.n+3*i+j] = dt*(1./3 if i == 0 else 1.)*self.v0[j+3]
                self.scale[2*self.n+3*i+j] = interval.ANGLE_RAD
        for j in range(self.size):
            if not isfinite(self.scale[j]) or self.scale[j] <= 0 or not isfinite(self.x[j]):
                raise ValueError('nonfinite or invalid coupled variable scale')

    cdef object evaluate(self, double[::1] values, double[::1] out, bint capture):
        cdef Py_ssize_t i, j, s, a, n = self.n
        cdef double sx, sy, sz, wx, wy, wz, cx, cy, cz, theta, square, coefficient
        cdef double first, second, stage_time
        self.last_value, self.last_residual = values, None
        for j in range(self.size):
            if not isfinite(values[j]):
                raise ValueError('nonfinite coupled trial')
        for i in range(2):
            s, a = 2*n+3*i, i*n+3
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
        for i in range(2):
            first, second = (5./12, -1./12) if i == 0 else (.75, .25)
            mj.mj_setState(self.m, self.d, self.base, interval.STATE_KIND)
            for j in range(self.q.shape[0]):
                self.q[j] = self.q0[j]
            for j in range(3):
                self.q[j] += self.dt*(first*values[j]+second*values[n+j])
                self.sigma_buffer[j] = values[2*n+3*i+j]
            for j in range(6, n):
                self.q[j+1] += self.dt*(first*values[j]+second*values[n+j])
            mj.mju_quatIntegrate(self.q_array[3:7], self.sigma_array, 1.)
            for j in range(n):
                self.v[j] = values[i*n+j]
            stage_time = self.t0+(1./3 if i == 0 else 1.)*self.dt
            self.d.time = stage_time
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
        for i in range(2):
            first, second = (5./12, -1./12) if i == 0 else (.75, .25)
            for j in range(n):
                s = i*n+j
                out[s] = (values[s]-self.v0[j]-self.dt*(first*self.acc[0,j]+second*self.acc[1,j]))/self.scale[s]
            for j in range(3):
                s = 2*n+3*i+j
                out[s] = (values[s]-self.dt*(first*self.tangent[0,j]+second*self.tangent[1,j]))/self.scale[s]
        self.last_residual = out
        norm_inf(out)
        return stages

    cdef void correction(self, object record) except *:
        cdef Py_ssize_t i, j, k, sweep
        cdef double beta, limit, radius, pnorm, epsilon, coefficient, length, predicted, value
        cdef bint different, plus_valid = False, minus_valid = False
        beta = norm2(self.residual)
        limit = max(self.tolerance, sqrt(MACHINE_EPS)*beta)
        record.update(completed=False,initial_norm=beta,predicted_tolerance=limit,
                      krylov_ceiling=self.kmax,directions=[])
        if beta == 0:
            for i in range(self.size): self.update[i] = 0
            record.update(completed=True,predicted_residual=0.)
            return
        for i in range(self.size): self.w[i] = self.x[i]/self.scale[i]
        radius = pow(MACHINE_EPS,1./3)*max(1.,norm2(self.w))
        for i in range(self.size): self.basis[0,i] = -self.residual[i]/beta
        self.h_array.fill(0.)
        self.target_array.fill(0.)
        self.target[0] = beta
        try:
            for k in range(self.kmax):
                plus_valid = minus_valid = False
                pnorm = norm2(self.basis[k])
                if pnorm == 0: raise ValueError('zero matrix-free direction')
                epsilon = radius/pnorm
                if not isfinite(epsilon) or epsilon <= 0:
                    raise ValueError('invalid matrix-free perturbation')
                different = False
                for i in range(self.size):
                    value = self.scale[i]*(epsilon*self.basis[k,i])
                    self.plus[i], self.minus[i] = self.x[i]+value,self.x[i]-value
                    if self.plus[i] != self.minus[i]: different = True
                if not different: raise ValueError('unrepresentable matrix-free perturbation')
                self.evaluate(self.plus,self.rp,False)
                plus_valid = True
                self.evaluate(self.minus,self.rm,False)
                minus_valid = True
                for i in range(self.size): self.w[i] = (self.rp[i]-self.rm[i])/(2*epsilon)
                norm2(self.w)
                for sweep in range(2):
                    for j in range(k+1):
                        coefficient = 0
                        for i in range(self.size): coefficient += self.basis[j,i]*self.w[i]
                        if not isfinite(coefficient): raise ValueError('nonfinite Krylov projection')
                        self.hessenberg[j,k] += coefficient
                        for i in range(self.size): self.w[i] -= coefficient*self.basis[j,i]
                length = norm2(self.w)
                self.hessenberg[k+1,k] = length
                weights,_,rank,_ = np.linalg.lstsq(self.h_array[:k+2,:k+1],self.target_array[:k+2],rcond=None)
                self.weights = weights
                norm2(self.weights)
                predicted = 0
                for j in range(k+2):
                    value = -self.target[j]
                    for i in range(k+1): value += self.hessenberg[j,i]*self.weights[i]
                    predicted += value*value
                if not isfinite(predicted): raise ValueError('nonfinite predicted residual')
                predicted = sqrt(predicted)
                record['directions'].append(dict(index=k,epsilon=epsilon,rank=int(rank),
                    predicted_residual=predicted,next_norm=length))
                if predicted <= limit:
                    for i in range(self.size):
                        value = 0
                        for j in range(k+1): value += self.basis[j,i]*self.weights[j]
                        self.update[i] = self.scale[i]*value
                    norm2(self.update)
                    record.update(completed=True,predicted_residual=predicted)
                    return
                if length == 0: raise ValueError('matrix-free Krylov breakdown without convergence')
                for i in range(self.size): self.basis[k+1,i] = self.w[i]/length
            raise ValueError('bounded matrix-free Krylov directions exhausted')
        except BaseException as error:
            record.update(failure=repr(error),last_direction=packed_numbers(self.basis[k]),
                          last_residual_plus=packed_numbers(self.rp) if plus_valid else None,
                          last_residual_minus=packed_numbers(self.rm) if minus_valid else None)
            raise

    cdef object solve(self, object receipt):
        cdef Py_ssize_t iteration, power, i
        cdef double norm, trial_norm, multiplier
        cdef bint accepted, differs
        self.evaluate(self.x,self.residual,False)
        norm = norm_inf(self.residual)
        for iteration in range(MAX_NEWTON):
            if norm <= self.tolerance: break
            record = {}
            receipt['linear_solves'].append(record)
            self.correction(record)
            accepted = False
            for power in range(MAX_LINE):
                multiplier = math.ldexp(1.,-power)
                differs = False
                for i in range(self.size):
                    self.trial[i] = self.x[i]+multiplier*self.update[i]
                    if self.trial[i] != self.x[i]: differs = True
                if not differs: break
                self.evaluate(self.trial,self.trial_residual,False)
                trial_norm = norm_inf(self.trial_residual)
                if trial_norm < norm or trial_norm <= self.tolerance:
                    receipt['iterations'].append(dict(before=norm,after=trial_norm,line_divisions=power))
                    for i in range(self.size):
                        self.x[i], self.residual[i] = self.trial[i],self.trial_residual[i]
                    norm,accepted = trial_norm,True
                    break
            if not accepted: raise ValueError('coupled Radau residual failed to decrease')
        if norm > self.tolerance: raise ValueError('bounded coupled Radau iterations exhausted')
        stages = self.evaluate(self.x,self.residual,True)
        norm = norm_inf(self.residual)
        if norm > self.tolerance: raise ValueError('captured coupled stage residual differs')
        receipt['final_residual'] = norm
        return stages


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
        receipt = dict(dt_s=dt,start_s=t0,iterations=[],linear_solves=[],converged=False,
                       calls_start=self.calls,failure=None)
        self.steps.append(receipt)
        try:
            solver = _Stages(e,base,dt,self)
            stages = solver.solve(receipt)
            work = interval._finite(dt*sum((B[i]*stages[i]['work'] for i in range(2)),start=np.zeros(6)))
            if work[0] > supply: raise ValueError('mechanical energy supply exhausted; no successor')
            if any(work[i] < 0 for i in (0,3,4,5)): raise ValueError('negative physical dissipative quadrature')
            d.qacc_warmstart[:] = stages[1]['qacc']
            self.forward(e)
            e._check()
            if float(d.time) != end: raise ValueError('Radau endpoint clock differs')
            endpoint = interval._snapshot(e)
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
            impulse = interval._impulse_add(stages[0]['impulse'],stages[1]['impulse'])
            receipt.update(converged=True,calls=self.calls-receipt['calls_start'],
                sampled_domain_unchanged=before['domain']==stages[0]['snapshot']['domain']==endpoint['domain'],
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
            receipt['rollback_exact'] = bool(np.array_equal(restored,base))
            if not receipt['rollback_exact']: raise AssertionError('diagnostic rollback differs') from error
            raise
