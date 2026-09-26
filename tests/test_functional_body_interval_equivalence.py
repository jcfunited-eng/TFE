"""Offline execution-equivalence proof, not an organism learning experiment.

Predecessor.advance below is the exact 9d8c778fe method, retained only as a
test oracle. No runtime import or fallback uses it. Bench efforts and temporary
NumPy call counters are measurement inputs, never fabricated lived experience.
Standalone unittest: no pytest/conftest, live transport, caretaker or subprocess.
"""
import json
import math
from pathlib import Path
import resource
import time
from types import MethodType
import unittest

import mujoco as mj
import numpy as np

from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.substrate.functional_body_native import NativeBody, MechanicalSuccessor
from guala_body_load_release import LOADS, PHASES, engine_at, prior_records
from guala_body_constraint_work import advance_with_constraint_work
from test_functional_body_native import apparatus, falling_body, gripper
from test_functional_body_optical_sources import declaration

class Predecessor:
    def advance(self, state: bytes, efforts: tuple[float, ...] | None, elapsed_us: int,
                available_work_j: float, *,
                effort_updates: tuple[tuple[int, float], ...] = ()) -> MechanicalSuccessor:
        """Advance one interval with full-vector or sparse anatomical input.

        Full vector replaces every command. None retains the previously applied
        vector; optional updates replace distinct addressed components. Constant
        effort is a declared zero-order-held mechanical input, NOT a posture
        servo, muscle metabolic model, chosen movement or learned coordination.
        Zero effort explicitly releases a motor. Sleep/depletion policy belongs
        to the existing caller, not this solver. No duplicate command store:
        ctrl is already part of the single native integration state.
        """
        lim, m, d = self.limits, self._model, self._data
        if (type(elapsed_us) is not int or elapsed_us <= 0
                or elapsed_us % lim.step_us or elapsed_us // lim.step_us > lim.max_substeps):
            raise ValueError("interval exceeds declared fixed-step budget")
        if not math.isfinite(available_work_j) or available_work_j < 0:
            raise ValueError("finite nonnegative mechanical supply required")
        if type(effort_updates) is not tuple or len(effort_updates) > m.nu:
            raise ValueError("bounded unique anatomical effort updates required")
        if efforts is not None and effort_updates:
            raise ValueError("full vector and incremental effort updates are exclusive")
        addressed = set()
        for item in effort_updates:
            if (type(item) is not tuple or len(item) != 2 or type(item[0]) is not int
                    or not 0 <= item[0] < m.nu or item[0] in addressed):
                raise ValueError("bounded unique anatomical effort updates required")
            addressed.add(item[0])
        self._restore(state)
        effort = d.ctrl.copy() if efforts is None else np.asarray(efforts, dtype=np.float64)
        for index, value in effort_updates:
            effort[index] = value
        if (effort.shape != (m.nu,) or not np.isfinite(effort).all()
                or np.any(effort < m.actuator_forcerange[:, 0])
                or np.any(effort > m.actuator_forcerange[:, 1])):
            raise ValueError("effort exceeds physical motor capacity")
        d.ctrl[:] = effort
        mj.mj_forward(m, d)
        initial_energy = float(sum(d.energy))
        initial_time = float(d.time)
        if math.ulp(initial_time) > m.opt.timestep:
            raise ValueError("mechanical time cannot represent this interval")
        positive_work = signed_work = braking_work = bearing_heat = travel_peak = 0.0
        self_bearing_heat = 0.0
        for _ in range(elapsed_us // lim.step_us):
            position, rotation = d.geom_xpos.copy(), d.geom_xmat.copy().reshape(-1, 3, 3)
            power_before = effort * d.qvel[self._motor_dof]
            bearing_before = float(np.dot(m.dof_damping, d.qvel**2))
            self_bearing_before = (0.0 if self._sensory_root is None else
                float(np.dot(m.dof_damping[self._self_dofs], d.qvel[self._self_dofs]**2)))
            mj.mj_step(m, d)
            mj.mj_kinematics(m, d)
            mj.mj_collision(m, d)
            self._check()
            power_after = effort * d.qvel[self._motor_dof]
            dt_half = m.opt.timestep / 2
            signed_work += float(np.sum(power_before + power_after)) * dt_half
            positive_work += float(np.sum(np.maximum(power_before, 0)
                                         + np.maximum(power_after, 0))) * dt_half
            braking_work += float(np.sum(np.maximum(-power_before, 0)
                                        + np.maximum(-power_after, 0))) * dt_half
            bearing_heat += (bearing_before + float(np.dot(m.dof_damping, d.qvel**2))) * dt_half
            if self._sensory_root is not None:
                self_bearing_after = float(np.dot(
                    m.dof_damping[self._self_dofs], d.qvel[self._self_dofs]**2))
                self_bearing_heat += (self_bearing_before + self_bearing_after) * dt_half
            if not all(math.isfinite(x) for x in (
                    positive_work, signed_work, braking_work, bearing_heat, self_bearing_heat)):
                raise ValueError("non-finite mechanical work")
            if positive_work > available_work_j:
                raise ValueError("mechanical energy supply exhausted; no successor")
            new_rotation = d.geom_xmat.reshape(-1, 3, 3)
            trace = np.einsum("ijk,ijk->i", rotation, new_rotation)
            angle = np.arccos(np.clip((trace - 1) / 2, -1, 1))
            travel = np.linalg.norm(d.geom_xpos - position, axis=1) + m.geom_rbound * angle
            travel_peak = max(travel_peak, float(np.max(travel, initial=0)))
            if not np.isfinite(travel).all():
                raise ValueError("non-finite surface motion")
            if travel_peak > lim.max_surface_travel_m:
                raise ValueError("surface movement exceeds collision sampling resolution")
        expected = initial_time + elapsed_us / 1_000_000
        if abs(d.time - expected) > (elapsed_us // lim.step_us + 1) * math.ulp(expected):
            raise ValueError("native mechanical time diverged")
        mj.mj_forward(m, d)
        self._check()
        observation = self._observation()
        residual = signed_work - (observation.kinetic_j + observation.potential_j - initial_energy) - bearing_heat
        if not math.isfinite(residual):
            raise ValueError("non-finite mechanical energy balance")
        return MechanicalSuccessor(self._capture(), observation, positive_work,
                                   signed_work, travel_peak, braking_work, bearing_heat, residual,
                                   None if self._sensory_root is None else self_bearing_heat)


def previous(engine):
    engine.advance = MethodType(Predecessor.advance, engine)
    return engine

def supply():
    return FunctionalOrganism.genesis(identity="offline-interval-budget", organism_tick=100).available_motor_work_j

def outcome(engine, state, **kwargs):
    try:
        result = engine.advance(state, **kwargs)
        error = None
    except ValueError as exception:
        result, error = None, str(exception)
    return result, error, engine._capture(), tuple(engine._data.warning.number)

class IntervalEquivalenceTests(unittest.TestCase):
    def test_recurrent_load_release_full_successors_cold_and_non_growth(self):
        rows = []
        for h in (100, 50, 25):
            for name, sign in LOADS:
                a, xml, limits = engine_at(h)
                b = previous(engine_at(h)[0])
                sa = a.initial_state()
                self.assertEqual(sa, b.initial_state())
                budget = supply()
                index = a.actuator_names.index(name)
                force = float(a._model.actuator_forcerange[index, 0 if sign < 0 else 1])
                costs = []
                for phase, multiplier in PHASES:
                    command = dict(efforts=None, elapsed_us=250000, available_work_j=budget,
                                   effort_updates=((index, force*multiplier),))
                    start=time.perf_counter(); ra=a.advance(sa, **command); ta=time.perf_counter()-start
                    start=time.perf_counter(); rb=b.advance(sa, **command); tb=time.perf_counter()-start
                    self.assertEqual(ra, rb, (h,name,phase))
                    fresh=NativeBody(xml,limits,sensory_root="guala/pelvis")
                    self.assertEqual(fresh.advance(sa, **command),ra)
                    self.assertEqual(len(ra.state),len(sa))
                    self.assertEqual(ra.state[:32],sa[:32])
                    if multiplier==0:
                        self.assertEqual(ra.positive_motor_work_j,0.)
                        self.assertEqual(ra.signed_motor_work_j,0.)
                    costs.append(dict(phase=phase,candidate_s=ta,predecessor_s=tb))
                    budget-=ra.positive_motor_work_j; self.assertGreaterEqual(budget,0.)
                    sa=ra.state
                rows.append(dict(step_us=h,name=name,phases=costs,state_bytes=len(sa)))
        print("RECURRENCE "+json.dumps(rows),flush=True)

    def test_all_128_original_endpoint_refusals_preserve_scratch_and_time(self):
        decl=declaration()
        a=NativeBody(decl.xml,decl.limits,sensory_root=decl.sensory_root)
        b=previous(NativeBody(decl.xml,decl.limits,sensory_root=decl.sensory_root))
        state=a.initial_state(); self.assertEqual(state,b.initial_state())
        prior=json.loads((Path(__file__).resolve().parents[1]/
            "docs/evidence/FB-01aj-endpoint-loads.json").read_text())
        self.assertEqual(len(prior["rows"]),128)
        for row in prior["rows"]:
            index=a.actuator_names.index(row["name"])
            command=dict(efforts=None,elapsed_us=250000,available_work_j=supply(),
                         effort_updates=((index,row["effort"]),))
            x,y=outcome(a,state,**command),outcome(b,state,**command)
            self.assertEqual(x,y,row["name"])
            self.assertIsNotNone(x[1])
            self.assertEqual(a._data.time,b._data.time)

    def test_gravity_contact_gripper_sparse_updates_and_energy_refusal(self):
        for factory,actions in (
            (falling_body,[((),(),10000,0.)]*5),
            (lambda:falling_body(supported=True),[((),(),10000,0.)]*5),
            (lambda:gripper(.6),[((.8,.8),(),20000,1.)]*5+
                [(None,((0,0.),),20000,1.),(None,(),20000,1.)]),
            (apparatus,[((.3,),(),20000,1.)]*30+
                [(None,((0,-.3),),20000,1.),((.3,),(),20000,0.)]),
        ):
            a,b=factory(),previous(factory())
            state=a.initial_state(); self.assertEqual(state,b.initial_state())
            for effort,updates,elapsed,budget in actions:
                x=outcome(a,state,efforts=effort,effort_updates=updates,
                          elapsed_us=elapsed,available_work_j=budget)
                y=outcome(b,state,efforts=effort,effort_updates=updates,
                          elapsed_us=elapsed,available_work_j=budget)
                self.assertEqual(x,y)
                if x[0] is not None: state=x[0].state

    def test_one_step_and_rejected_input_preserve_exact_outcome(self):
        a,b=apparatus(False),previous(apparatus(False))
        state=a.initial_state(); self.assertEqual(state,b.initial_state())
        cases=[
            dict(efforts=(.3,),elapsed_us=1000,available_work_j=1.),
            dict(efforts=(2.,),elapsed_us=1000,available_work_j=1.),
            dict(efforts=(.3,),elapsed_us=1000,available_work_j=0.),
            dict(efforts=(.3,),elapsed_us=999,available_work_j=1.),
            dict(efforts=(.3,),elapsed_us=1000,available_work_j=math.nan),
            dict(efforts=None,effort_updates=((0,.2),(0,.3)),elapsed_us=1000,available_work_j=1.),
        ]
        for command in cases:
            self.assertEqual(outcome(a,state,**command),outcome(b,state,**command))
        # Refused scratch must not poison the next lawful caller-owned state.
        self.assertEqual(a.advance(state,(.3,),10000,1.),b.advance(state,(.3,),10000,1.))

    def test_duplicate_dot_work_absent_without_retained_cache(self):
        for factory,with_self in ((lambda:apparatus(False),False),(lambda:engine_at(100)[0],True)):
            a,b=factory(),previous(factory()); state=a.initial_state()
            n=10; elapsed=n*a.limits.step_us
            effort=tuple(0. for _ in a.actuator_names)
            original=np.dot
            def measured(engine):
                count=0
                def dot(*args,**kwargs):
                    nonlocal count
                    count+=1
                    return original(*args,**kwargs)
                keys=set(vars(engine))
                try:
                    np.dot=dot
                    result=engine.advance(state,effort,elapsed,supply())
                finally: np.dot=original
                self.assertEqual(set(vars(engine)),keys)
                return result,count
            ra,ca=measured(a); rb,cb=measured(b)
            self.assertEqual(ra,rb)
            factor=2 if with_self else 1
            self.assertEqual(ca,factor*(n+1))
            self.assertEqual(cb,2*factor*n)

    def test_constraint_observer_and_full_implicit_stay_compatible(self):
        a,_,_=engine_at(100)
        index=a.actuator_names.index(LOADS[0][0])
        force=float(a._model.actuator_forcerange[index,0])
        result,report=advance_with_constraint_work(a,a.initial_state(),250000,supply(),
            effort_updates=((index,force),))
        self.assertEqual(report["discrete_update"],prior_records()[LOADS[0][0],100,force])
        a,_,_=engine_at(100,integrator="implicit")
        b=previous(engine_at(100,integrator="implicit")[0])
        state=a.initial_state(); self.assertEqual(state,b.initial_state())
        self.assertEqual(a.advance(state,None,250000,supply(),effort_updates=((index,force),)),
                         b.advance(state,None,250000,supply(),effort_updates=((index,force),)))

if __name__=="__main__":
    started=time.perf_counter()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IntervalEquivalenceTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print("SUMMARY "+json.dumps(dict(tests=result.testsRun,success=result.wasSuccessful(),
        elapsed_s=time.perf_counter()-started,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)),flush=True)
    raise SystemExit(0 if result.wasSuccessful() else 1)
