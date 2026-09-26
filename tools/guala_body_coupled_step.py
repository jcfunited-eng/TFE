"""Bounded equation/caller proof for the body-only coupled Newton step.

No world/organism run, live writes or behavior claim. Small mechanical controls
are specified analytically; the body input is the already authenticated 100us
startup load. This does not qualify whole-body accuracy or real-time delivery.
"""
from __future__ import annotations

import argparse
import ctypes
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import time
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_native import NativeBody, MechanicalLimits
from guala_body_constraint_split import exact_counterexample, solve2
from guala_body_contact_onset import archived_controls
from guala_body_joint_boundary import encode, integration, KIND
from guala_body_load_release import engine_at

VERSION = "3.3.7+guala.coupled-step.1"


def model_xml(jacobian="dense", *, damping=1):
    # Two independent coupled pairs separated in global DOF order by a free
    # slide. This exercises island mapping, not just a single identity map.
    def pair(name, y):
        return f'''<body name="{name}" pos="0 {y} 0">
          <joint name="{name}-stop" type="slide" axis="1 0 0" limited="true"
            range="0 1" margin="0" solreflimit=".0002 1"
            solimplimit=".999 .999 .001 .5 2"/>
          <geom type="sphere" size=".05" mass="1" contype="0" conaffinity="0"/>
          <body pos="0 .2 0"><joint type="slide" axis="1 0 0" damping="{damping}"/>
            <geom type="sphere" size=".05" mass="1" contype="0" conaffinity="0"/>
          </body></body>'''
    return f'''<mujoco><compiler angle="radian"/>
      <option timestep="1" gravity="0 0 0" integrator="implicitfast"
        solver="Newton" iterations="100" tolerance="1e-10" jacobian="{jacobian}"/>
      <size memory="8M"/><worldbody>{pair("a",0)}
        <body pos="0 1 0"><joint type="slide" axis="1 0 0" damping="{damping}"/>
          <geom type="sphere" size=".05" mass="1" contype="0" conaffinity="0"/>
        </body>{pair("b",2)}</worldbody></mujoco>'''


def close(actual, expected, tolerance):
    assert np.all(np.isfinite(actual))
    np.testing.assert_allclose(actual, expected, rtol=0, atol=tolerance)


def measure_step(m, d, advance):
    before_v = d.qvel.copy()
    mj.mj_forward(m, d)
    physical = {name: getattr(d, name).copy() for name in ("M", "qLD", "qLDiagInv", "efc_R")}
    advance(m, d)
    assert np.all(d.warning.number == 0)
    for name, value in physical.items():
        assert np.array_equal(getattr(d, name), value), name
    delta_v = d.qvel-before_v
    actual_acc = delta_v/m.opt.timestep
    close(actual_acc, d.qacc, m.opt.tolerance)
    momentum = np.empty(m.nv)
    mj.mj_mulM(m, d, momentum, delta_v)
    residual = momentum + m.opt.timestep*m.dof_damping*delta_v - (
        m.opt.timestep*(d.qfrc_smooth+d.qfrc_constraint))
    close(residual, np.zeros(m.nv), m.opt.tolerance)
    ja = np.empty(d.nefc)
    mj.mj_mulJacVec(m, d, ja, actual_acc)
    rows = ja + d.efc_R*d.efc_force-d.efc_aref
    assert np.all(d.efc_type == mj.mjtConstraint.mjCNSTR_LIMIT_JOINT)
    active = d.efc_force > 0
    close(rows[active], np.zeros(int(active.sum())), m.opt.tolerance)
    assert np.all(d.efc_force >= 0)
    assert np.all(rows[~active] >= -m.opt.tolerance)
    return dict(acceleration=d.qacc.tolist(), reaction=d.efc_force.tolist(),
        max_constraint_residual=float(np.max(np.abs(rows[active]),initial=0)),
        max_impulse_residual=float(np.max(np.abs(residual),initial=0)),
        solved_equals_integrated=True, physical_inertia_and_regularizer_unchanged=True,
        islands=int(d.nisland), active_rows=int(active.sum()))


def expected_pair(force, damping):
    h = ((Q(2), Q(1)), (Q(1), Q(1+damping)))
    free = solve2(h, force)
    inverse_j = solve2(h, (Q(1),Q(0)))
    reaction = max(Q(0), -free[0]/(inverse_j[0]+Q(1,999)))
    return solve2(h,(force[0]+reaction,force[1])), reaction


def scalar_cases():
    rows = []
    for jacobian in ("dense","sparse"):
        for islands in (False,True):
            for damping, force, away in ((1,-1,False),(1,1,False),(0,-1,False),(1,-1,True)):
                m = mj.MjModel.from_xml_string(model_xml(jacobian,damping=damping))
                if not islands:
                    m.opt.disableflags |= int(mj.mjtDisableBit.mjDSBL_ISLAND)
                d = mj.MjData(m)
                d.qfrc_applied[:] = [2*force,force,1,force,force/2]
                if away:
                    d.qpos[[0,3]] = .5
                d.qacc_warmstart[:] = [.2,-.4,.6,-.8,1]
                mj.mj_forward(m,d)
                before = integration(m,d)
                instantaneous = d.qacc.copy()
                metrics = measure_step(m,d,mj.mj_step)
                expect, reactions = [], []
                for amplitude in (Q(force),Q(force,2)):
                    f = (2*amplitude,amplitude)
                    if away:
                        pair = solve2(((Q(2),Q(1)),(Q(1),Q(1+damping))),f)
                        reaction = Q(0)
                    else:
                        pair, reaction = expected_pair(f,damping)
                        reactions.append(float(reaction))
                    if expect:
                        expect.append(1/(1+damping))
                    expect.extend(map(float,pair))
                close(d.qacc,expect,m.opt.tolerance)
                close(d.efc_force,reactions,m.opt.tolerance)
                if not away:
                    close(d.efc_R,[1/999,1/999],m.opt.tolerance)
                if damping == 0:
                    close(d.qacc,instantaneous,m.opt.tolerance)
                after = integration(m,d)
                for two_phase in (False,True):
                    cold = mj.MjData(m)
                    mj.mj_setState(m,cold,before,KIND)
                    if two_phase:
                        mj.mj_step1(m,cold)
                        mj.mj_step2(m,cold)
                    else:
                        mj.mj_step(m,cold)
                    assert np.array_equal(after,integration(m,cold))
                rows.append(dict(jacobian=jacobian,islands_enabled=islands,damping=damping,
                    force=force,away_from_stop=away,cold_exact=True,step2_exact=True,**metrics))
    return rows


def threaded_case():
    # Direct binding of the public C API; the ordinary body wrapper owns no pool.
    lib = ctypes.CDLL("libmujoco.so.3.3.7")
    lib.mju_threadPoolCreate.argtypes = [ctypes.c_size_t]
    lib.mju_threadPoolCreate.restype = ctypes.c_void_p
    lib.mju_bindThreadPool.argtypes = [ctypes.c_void_p,ctypes.c_void_p]
    lib.mju_threadPoolDestroy.argtypes = [ctypes.c_void_p]
    lib.mju_bindThreadPool.restype = lib.mju_threadPoolDestroy.restype = None
    m = mj.MjModel.from_xml_string(model_xml("sparse"))
    d = mj.MjData(m)
    d.qfrc_applied[:] = [-2,-1,1,-1,-.5]
    before = integration(m,d)
    pool = lib.mju_threadPoolCreate(2)
    assert pool
    try:
        lib.mju_bindThreadPool(d._address,pool)
        result = measure_step(m,d,mj.mj_step)
        assert d.nisland == 2
        after = integration(m,d)
    finally:
        # No data access after pool destruction; model/data die at function exit.
        lib.mju_threadPoolDestroy(pool)
    serial = mj.MjData(m)
    mj.mj_setState(m,serial,before,KIND)
    mj.mj_step(m,serial)
    assert np.array_equal(after,integration(m,serial))
    return dict(threaded_equals_serial=True,**result)


def refusal_cases():
    limits = MechanicalLimits(100,1,.008,.03,.005,.015)
    cases = []
    for attr,value in (("integrator","implicit"),("solver","CG"),("solver","PGS"),
                       ("noslip_iterations","1"),("density","1"),("viscosity","1")):
        root = ET.fromstring(model_xml())
        root.find("option").set(attr,value)
        xml = ET.tostring(root,encoding="unicode")
        try:
            NativeBody(xml,limits)
        except ValueError as e:
            assert "coupled" in str(e)
            cases.append(dict(attribute=attr,value=value,error=str(e)))
        else:
            raise AssertionError("unsupported profile accepted")
    root = ET.fromstring(model_xml())
    ET.SubElement(root.find("option"),"flag",{"fwdinv":"enable"})
    xml = ET.tostring(root,encoding="unicode")
    try:
        NativeBody(xml,limits)
    except ValueError as e:
        assert "forward-inverse" in str(e)
        cases.append(dict(attribute="fwdinv",error=str(e)))
    else:
        raise AssertionError("forward-inverse accepted")
    root = ET.fromstring(model_xml())
    tendon = ET.SubElement(ET.SubElement(root,"tendon"),"fixed",{"damping":"1"})
    ET.SubElement(tendon,"joint",{"joint":"a-stop","coef":"1"})
    try:
        NativeBody(ET.tostring(root,encoding="unicode"),limits)
    except ValueError as e:
        assert "tendon" in str(e)
        cases.append(dict(attribute="tendon_damping",error=str(e)))
    else:
        raise AssertionError("tendon damping accepted")
    for attr,value in (("solver",mj.mjtSolver.mjSOL_CG),
                       ("noslip_iterations",1),("density",1),
                       ("disableflags",int(mj.mjtDisableBit.mjDSBL_DAMPER))):
        m = mj.MjModel.from_xml_string(model_xml())
        d = mj.MjData(m)
        setattr(m.opt,attr,value)
        before = integration(m,d)
        try:
            mj.mj_step(m,d)
        except mj.FatalError as e:
            assert "coupled body step" in str(e)
            assert np.array_equal(before,integration(m,d))
        else:
            raise AssertionError("native unsupported step accepted")
    m = mj.MjModel.from_xml_string(model_xml())
    d = mj.MjData(m)
    mj.mj_forward(m,d)
    before = integration(m,d)
    try:
        mj.mj_implicit(m,d)
    except mj.FatalError as e:
        assert "requires mj_step" in str(e)
        assert np.array_equal(before,integration(m,d))
    else:
        raise AssertionError("old split integrator reachable")
    return dict(wrapper=cases,native_refusals=5,no_integration_mutation=True)


def body_case():
    e,xml,limits = engine_at(100)
    c = archived_controls()[100]
    assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
    initial = e.initial_state()
    command = dict(efforts=None,elapsed_us=100,available_work_j=c["initial_supply_j"],
        effort_updates=((e.actuator_names.index(c["name"]),c["phases"][0]["effort_nm"]),))
    original = mj.mj_step
    evidence = {}
    calls = 0
    def observe(m,d):
        nonlocal calls
        assert m is e._model and d is e._data and calls == 0
        calls += 1
        evidence.update(measure_step(m,d,original))
        assert d.ncon == 0
    try:
        mj.mj_step = observe
        result = e.advance(initial,**command)
    finally:
        mj.mj_step = original
    assert calls == 1
    cold,_,_ = engine_at(100)
    assert cold.advance(initial,**command) == result
    prior_header = hashlib.sha256(("3.3.7+guala.closed-limits.1"+repr(limits)
                                  +repr(e._sensory_root)+xml).encode()).digest()
    try:
        e._restore(prior_header+initial[32:])
    except ValueError as error:
        assert str(error) == "body state/model mismatch"
    else:
        raise AssertionError("old law integration state accepted")
    evidence.update(full_cold_successor_exact=True,old_law_refused=True,state_bytes=len(result.state),
        successor_sha256=hashlib.sha256(result.state).hexdigest(),model_sha256=c["model_sha256"])
    return evidence



def motion_prefix():
    """Same authored body/load, new discrete law; no old-law successor assertions."""
    from guala_body_local_refinement import difference, restore, state_copy
    controls = archived_controls()
    e, xml, _ = engine_at(100)
    c = controls[100]
    assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
    e.initial_state()
    efforts = e._data.ctrl.copy()
    efforts[e.actuator_names.index(c["name"])] = c["phases"][0]["effort_nm"]
    e._data.ctrl[:] = efforts
    mj.mj_forward(e._model,e._data)
    initial = state_copy(e)
    startup = []
    try:
        for level in range(6):
            h = 100./2**level
            trials = []
            for count in (1,2):
                e._model.opt.timestep = h/count/1_000_000
                restore(e,initial)
                receipt = e._advance_interval(e,efforts,count,c["initial_supply_j"])
                trials.append(((e._data.qpos.copy(),e._data.qvel.copy()),receipt))
            startup.append(dict(coarse_step_us=h,**difference(e._model,
                trials[0][0],trials[1][0],trials[0][1],trials[1][1])))
    finally:
        e._model.opt.timestep = .0001
    records = []
    for h in (100,50,25):
        engine, xml, limits = engine_at(h)
        c = controls[h]
        assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
        state = engine.initial_state()
        # Only authenticate the unchanged initial physical payload against the
        # historic header. Never submit the old-law record to the executing engine.
        old_header = hashlib.sha256(("3.3.7"+repr(limits)+repr(engine._sensory_root)+xml).encode()).digest()
        assert hashlib.sha256(old_header+state[32:]).hexdigest() == c["initial_state_sha256"]
        command = dict(efforts=None,elapsed_us=30000,available_work_j=c["initial_supply_j"],
            effort_updates=((engine.actuator_names.index(c["name"]),c["phases"][0]["effort_nm"]),))
        original = mj.mj_step
        contacts = {}
        samples = []
        steps = 0
        started = time.perf_counter()
        def observe(m,d):
            nonlocal steps
            assert m is engine._model and d is engine._data
            before_us = steps*h
            original(m,d)
            assert np.all(d.warning.number == 0)
            for index in range(d.ncon):
                contact = d.contact[index]
                wrench = np.empty(6)
                mj.mj_contactForce(m,d,index,wrench)
                assert np.all(np.isfinite(wrench)) and np.isfinite(contact.dist)
                if not np.any(wrench):
                    continue
                force = float(np.linalg.norm(wrench[:3]))
                couple = float(np.linalg.norm(wrench[3:]))
                assert np.isfinite(force) and np.isfinite(couple)
                names = [m.geom(int(g)).name for g in contact.geom]
                key = "|".join(names)
                # Each maximum is one contact-point wrench, not a summed pair resultant.
                record = contacts.setdefault(key,dict(first_us=before_us,
                    peak_point_force_n=0.,peak_point_couple_nm=0.,most_negative_separation_m=0.))
                record["peak_point_force_n"] = max(record["peak_point_force_n"],force)
                record["peak_point_couple_nm"] = max(record["peak_point_couple_nm"],couple)
                record["most_negative_separation_m"] = min(record["most_negative_separation_m"],float(contact.dist))
            steps += 1
            if steps*h in (10000,20000,30000):
                samples.append(dict(elapsed_us=steps*h,qpos=d.qpos.tolist(),qvel=d.qvel.tolist()))
        try:
            mj.mj_step = observe
            result = engine.advance(state,**command)
        finally:
            mj.mj_step = original
        observed_seconds = time.perf_counter()-started
        assert steps == 30000//h and len(samples)==3
        cold = NativeBody(xml,limits,sensory_root=engine._sensory_root)
        started = time.perf_counter()
        repeated = cold.advance(state,**command)
        unobserved_seconds = time.perf_counter()-started
        assert repeated == result
        assert len(result.state)==len(state)
        records.append(dict(h_us=h,steps=steps,samples=samples,contacts=contacts,
            signed_motor_work_j=result.signed_motor_work_j,
            positive_motor_work_j=result.positive_motor_work_j,
            braking_work_j=result.motor_braking_work_j,bearing_quadrature_j=result.bearing_dissipation_j,
            unresolved_exchange_j=result.unresolved_energy_exchange_j,
            kinetic_j=result.observation.kinetic_j,potential_j=result.observation.potential_j,
            max_surface_travel_m=result.max_surface_travel_m,
            full_cold_successor_exact=True,unobserved_seconds=unobserved_seconds,
            observed_seconds=observed_seconds,state_bytes=len(result.state),
            successor_sha256=hashlib.sha256(result.state).hexdigest()))
    comparisons = []
    for coarse,fine in zip(records,records[1:]):
        for a,b in zip(coarse["samples"],fine["samples"]):
            metrics = difference(e._model,(np.asarray(a["qpos"]),np.asarray(a["qvel"])),
                (np.asarray(b["qpos"]),np.asarray(b["qvel"])),(0.,)*6,(0.,)*6)
            metrics.pop("work_j")
            comparisons.append(dict(coarse_us=coarse["h_us"],fine_us=fine["h_us"],
                elapsed_us=a["elapsed_us"],**metrics))
    return dict(startup_dyadic_errors=startup,prefixes=records,comparisons=comparisons,
        scope="30ms load/contact diagnostic; convergence indicators, not continuum error bounds or production qualification")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-prefix",action="store_true")
    args = parser.parse_args()
    assert mj.__version__ == VERSION and mj.mj_versionString() == VERSION
    if args.motion_prefix:
        result = dict(engine_version=VERSION,motion=motion_prefix())
    else:
        result = dict(engine_version=VERSION,exact_control=exact_counterexample(),
            controls=scalar_cases(),threaded=threaded_case(),refusals=refusal_cases(),body=body_case(),
            scope="step consistency only; whole-body trajectory accuracy/realtime NOT qualified")
    result["maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(encode(result),sort_keys=True))


if __name__ == "__main__":
    main()
