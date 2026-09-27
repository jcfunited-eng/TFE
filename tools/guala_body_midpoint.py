"""One bounded equation/caller witness for the body-only implicit midpoint law.

Analytical constant-inertia controls and one existing 100us body input only.
Not a contact-accuracy, continuum-error, mature-world or production certificate.
The prior coupled-step evidence and its diagnostic remain historical controls.
"""
from __future__ import annotations

from fractions import Fraction
from dataclasses import asdict
import argparse
import base64
import hashlib
import json
import resource
import time
import xml.etree.ElementTree as ET

import mujoco as mj
import numpy as np

from dsf_ai_service.substrate.functional_body_native import ENGINE_VERSION
from guala_body_contact_onset import archived_controls
from guala_body_coupled_step import model_xml
from guala_body_joint_boundary import encode, integration
from guala_body_load_release import engine_at

VERSION = "3.3.7+guala.midpoint-step.1"


def close(actual, expected, atol=1e-9):
    assert np.isfinite(actual).all() and np.isfinite(expected).all()
    np.testing.assert_allclose(actual, expected, rtol=0, atol=atol)


def control(jacobian, islands, force):
    root = ET.fromstring(model_xml(jacobian))
    option = root.find("option")
    option.set("timestep", ".00001")
    ET.SubElement(option, "flag", dict(refsafe="disable", autoreset="disable", energy="enable"))
    m = mj.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
    if not islands:
        m.opt.disableflags |= int(mj.mjtDisableBit.mjDSBL_ISLAND)
    d = mj.MjData(m)
    d.qfrc_applied[:] = [2*force, force, 1, force, force/2]
    d.qacc_warmstart[:] = [.2, -.4, .6, -.8, 1]
    mj.mj_forward(m, d)
    before = integration(m, d)
    h = m.opt.timestep
    # Exact inertia of two pairs of unit-mass co-linear slides, plus one free slide.
    mass = np.array([[2,1,0,0,0],[1,1,0,0,0],[0,0,1,0,0],
                     [0,0,0,2,1],[0,0,0,1,1]], dtype=float)
    physical = {k: getattr(d,k).copy() for k in ("M","qLD","qLDiagInv")}
    operator = mass + np.diag(h*m.dof_damping/2)
    # At either lower stop: qm=h²*a/4, vm=h*a/2.
    # J*a + R*lambda - aref = 0, aref=-b*J*vm-k*I*J*qm.
    # Native KBIP is independently checked against its declared material law;
    # no discrete numerical solution feeds the reference acceleration.
    assert d.nefc == 2
    assert np.array_equal(d.efc_type,
                          [mj.mjtConstraint.mjCNSTR_LIMIT_JOINT]*2)
    close(d.efc_R, np.full(2, 1/999), 1e-12)
    k, b, impedance = d.efc_KBIP[:,0].copy(), d.efc_KBIP[:,1].copy(), d.efc_KBIP[:,2].copy()
    close(impedance, np.full(2, .999), 1e-12)
    close(k, np.full(2, 1/(.999**2*.0002**2)), 1e-6)
    close(b, np.full(2, 2/(.999*.0002)), 1e-8)
    factor = 1 + h*b/2 + h*h*k*impedance/4
    if force < 0:
        for row, dof in enumerate((0,3)):
            operator[dof,dof] += factor[row]/d.efc_R[row]
    expected = np.linalg.solve(operator, d.qfrc_applied)
    timers_before = [(float(t.duration), int(t.number)) for t in d.timer]
    mj.mj_step(m, d)
    assert not np.any(d.warning.number)
    actual = d.qvel/h
    close(d.qacc, expected)
    close(actual, expected)
    close(d.qpos, h*h*expected/2)
    for name, values in physical.items():
        assert np.array_equal(getattr(d, name), values), name
    residual = mass @ d.qacc - d.qfrc_smooth - d.qfrc_constraint
    defect = float(np.linalg.norm(residual)/(m.stat.meaninertia*max(1,m.nv)))
    assert defect <= m.opt.tolerance
    if force < 0:
        close(d.efc_force, -factor*expected[[0,3]]/(1/999))
    else:
        assert d.nefc == 0
    vm = h*d.qacc/2
    work = h*float(vm @ d.qfrc_applied)
    bearing = h*float((vm*vm) @ m.dof_damping)
    contact_work = h*float(vm @ d.qfrc_constraint)
    kinetic = float(d.qvel @ mass @ d.qvel)/2
    close(np.array([work-bearing+contact_work]), np.array([kinetic]), 1e-12)
    after = integration(m, d)
    for two_phase in (False, True):
        fresh = mj.MjData(m)
        mj.mj_setState(m, fresh, before, mj.mjtState.mjSTATE_INTEGRATION)
        if two_phase:
            mj.mj_step1(m, fresh)
            mj.mj_step2(m, fresh)
        else:
            mj.mj_step(m, fresh)
        assert np.array_equal(integration(m,fresh), after)
    return dict(jacobian=jacobian, islands=islands, applied_force=force,
        acceleration=d.qacc.tolist(), reference=expected.tolist(),
        reaction=d.efc_force.tolist(), normalized_midpoint_defect=defect,
        work_j=work, bearing_loss_j=bearing, contact_work_j=contact_work,
        kinetic_j=kinetic, cold_exact=True, step2_exact=True,
        physical_inertia_unchanged=True,
        native_timer_call_deltas=[int(t.number)-old[1]
                                  for t,old in zip(d.timer,timers_before)])


def refusal():
    rows = []
    for invalid in ("iterations", "linesearch", "tolerance", "split"):
        m = mj.MjModel.from_xml_string(model_xml())
        m.opt.timestep = .00001
        d = mj.MjData(m)
        d.qfrc_applied[:] = [-2,-1,1,-1,-.5]
        if invalid == "iterations":
            m.opt.iterations = 1
        elif invalid == "linesearch":
            m.opt.ls_iterations = 0
        elif invalid == "tolerance":
            m.opt.tolerance = float("nan")
        before = integration(m,d)
        try:
            (mj.mj_implicit if invalid == "split" else mj.mj_step)(m,d)
        except mj.FatalError as error:
            expected = {"iterations": "residual did not converge",
                        "linesearch": "convergence bounds",
                        "tolerance": "convergence bounds",
                        "split": "requires mj_step"}[invalid]
            assert expected in str(error)
            assert np.array_equal(before,integration(m,d))
            rows.append(dict(case=invalid, error=str(error), no_successor=True))
        else:
            raise AssertionError("invalid midpoint operation accepted: "+invalid)
    return rows


def body():
    e,xml,limits = engine_at(100)
    c = archived_controls()[100]
    assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
    initial = e.initial_state()
    command = dict(efforts=None, elapsed_us=100, available_work_j=c["initial_supply_j"],
        effort_updates=((e.actuator_names.index(c["name"]),c["phases"][0]["effort_nm"]),))
    before_v = e._data.qvel.copy()
    result = e.advance(initial, **command)
    vm = (before_v+e._data.qvel)/2
    bearing = .0001*float(np.dot(e._model.dof_damping,vm**2))
    assert result.bearing_dissipation_j == bearing
    cold,_,_ = engine_at(100)
    assert cold.advance(initial, **command) == result
    # The old law may not enter through a substituted persistence identity.
    prior_header = hashlib.sha256(("3.3.7+guala.coupled-step.1"+repr(limits)
                                   +repr(e._sensory_root)+xml).encode()).digest()
    try:
        cold._restore(prior_header+initial[32:])
    except ValueError as error:
        assert str(error) == "body state/model mismatch"
    else:
        raise AssertionError("old numerical law restored")
    # Failed supply does not publish or poison the next same-predecessor operation.
    try:
        cold.advance(initial, **(command | dict(available_work_j=0)))
    except ValueError as error:
        assert "supply exhausted" in str(error)
    else:
        raise AssertionError("unfunded mechanical work accepted")
    assert cold.advance(initial, **command) == result
    return dict(model_sha256=c["model_sha256"], state_bytes=len(result.state),
        successor_sha256=hashlib.sha256(result.state).hexdigest(),
        fresh_cold_exact=True, old_law_refused=True, failed_supply_recovers=True,
        signed_motor_work_j=result.signed_motor_work_j,
        bearing_midpoint_loss_j=bearing,
        unresolved_exchange_j=result.unresolved_energy_exchange_j)


def heat_reversal():
    """Two real efforts, one sign reversal, actual world/thermal publication."""
    from dsf_ai_service.substrate.functional_body_native import MechanicalLimits
    from dsf_ai_service.substrate.embodiment_world import (
        AnatomicalEffortCommand, NativeWorldMount, PORT_ID, encode_command,
    )
    from test_functional_body_world import world, INTENT
    # A one-joint calorimetry bench, NOT a replacement organism morphology.
    xml = """<mujoco><size memory="2M"/>
      <option gravity="0 0 0" integrator="implicitfast" iterations="100" tolerance="1e-10"/>
      <worldbody>
        <body name="guala/pelvis" pos="1 1 0">
          <joint name="joint" type="hinge" damping=".02"/>
          <geom name="guala/pelvis/surface" type="sphere" size=".1" mass="1" pos="0 0 .1"/>
        </body>
        <body name="bench-other" pos="4.75 4.75 0" quat="0 0 0 1">
          <geom type="sphere" size=".25" mass="1" pos="0 0 .25"/>
        </body>
        <body name="bench-object" pos="1.5 1 0">
          <geom type="sphere" size=".1" mass=".5" pos="0 0 .1"/>
        </body>
      </worldbody><actuator>
        <motor name="motor" joint="joint" forcelimited="true" forcerange="-1 1"/>
      </actuator></mujoco>"""
    mount = NativeWorldMount(xml=xml, limits=MechanicalLimits(1000,1,.008,.03,.005,.015),
        sensory_root="guala/pelvis",
        body_frames=(("guala-body-1","guala/pelvis"),("w1-body-2","bench-other")),
        object_frames=(("bench-object","bench-object"),),
        actuator_owners=(("motor","guala-body-1"),))
    authority = world(thermal=True, measured_core=True)
    prepared = authority.prepare_native_mount(mount, expected_revision=0,
                                               causal_intent_receipt_sha256=INTENT)
    authority.commit_prepared_action(prepared)
    def prepare(auth, effort):
        return auth.prepare_port_command(port_id=PORT_ID,
            command_payload=encode_command(AnatomicalEffortCommand((("motor",effort),),1000)),
            causal_intent_receipt_sha256=INTENT,
            expected_revision=auth.observation_snapshot().revision,
            available_motor_work_j=1., basal_heat_nanojoules=0)
    authority.commit_prepared_action(prepare(authority,.3))
    before = authority.encoded_snapshot()
    engine = authority._native_engine_for(mount)
    v0 = float(engine._data.qvel[0])
    prepared = prepare(authority,-.6)
    v1 = float(engine._data.qvel[0])
    assert v0 > 0 > v1
    vm = (v0+v1)/2
    power = -.6*vm
    work = prepared.native_work
    assert work.signed_motor_work_j == .001*power
    assert work.positive_motor_work_j == .001*max(power,0)
    assert work.motor_braking_work_j == .001*max(-power,0)
    close(np.array([work.self_bearing_dissipation_j]),np.array([.001*.02*vm*vm]),1e-18)
    old_bound = .001/2*(max(.6*v0,0)+max(.6*v1,0))
    assert old_bound > work.motor_braking_work_j
    expected_heat = round((Fraction.from_float(work.self_bearing_dissipation_j)
                         +Fraction.from_float(work.motor_braking_work_j))*10**9)
    assert expected_heat != round((Fraction.from_float(work.self_bearing_dissipation_j)
                                  +Fraction.from_float(old_bound))*10**9)
    core_before = authority._thermal_state.nodes[4].energy_microjoules
    authority.commit_prepared_action(prepared)
    receipt = authority._latest_thermal_transition
    assert receipt.native_dissipation_heat_nanojoules == expected_heat
    assert receipt.native_basal_heat_nanojoules == 0
    assert authority._thermal_state.nodes[4].energy_microjoules-core_before == expected_heat//1000
    fresh = world(thermal=True, measured_core=True)
    fresh.restore_encoded(before)
    repeated = prepare(fresh,-.6)
    assert repeated.native_work == work
    fresh.commit_prepared_action(repeated)
    assert fresh.encoded_snapshot() == authority.encoded_snapshot()
    return dict(v0=v0,v1=v1,midpoint_power_w=power,
        positive_work_j=work.positive_motor_work_j,braking_work_j=work.motor_braking_work_j,
        rejected_endpoint_braking_bound_j=old_bound,
        actual_received_heat_nanojoules=receipt.native_dissipation_heat_nanojoules,
        expected_heat_nanojoules=expected_heat,fresh_cold_exact=True)



def motion_intervals():
    """Existing full-body load, three fixed rates, then release; no new anatomy.

    This is a zero-gravity mechanical bench and a bounded feasibility/cost
    measurement, not whole-history accuracy or production qualification.
    No failed interval is published. Other predeclared rates are independent
    cases, not retries of a live body.
    """
    from guala_body_local_refinement import state_copy
    controls = archived_controls()
    rows = []
    for h_us in (100, 50, 25):
        e, xml, limits = engine_at(h_us)
        c = controls[h_us]
        assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
        state = e.initial_state()
        # Authenticate genesis physical bytes against the original archive.
        # Do not submit this old numerical identity to the candidate decoder.
        header = hashlib.sha256(("3.3.7"+repr(limits)+repr(e._sensory_root)+xml).encode()).digest()
        assert hashlib.sha256(header+state[32:]).hexdigest() == c["initial_state_sha256"]
        supply = c["initial_supply_j"]
        motor = e.actuator_names.index(c["name"])
        row = dict(h_us=h_us, model_sha256=c["model_sha256"],
                   effort_name=c["name"], initial_supply_j=supply,
                   native_step_ceiling=4*250000//h_us, phases=[], failure=None)
        print(json.dumps(encode(dict(event="motion_case_started", h_us=h_us))),flush=True)
        for phase, multiplier in (("load", 1), ("release", 0)):
            effort = multiplier*c["phases"][0]["effort_nm"]
            command = dict(efforts=None, elapsed_us=250000, available_work_j=supply,
                           effort_updates=((motor, effort),))
            phase_started = time.perf_counter()
            result = repeated = cold = None
            stage = "ordinary"
            try:
                result = e.advance(state, **command)
                ordinary_seconds = time.perf_counter()-phase_started
                stage = "cold"
                cold, _, _ = engine_at(h_us)
                started = time.perf_counter()
                repeated = cold.advance(state, **command)
                cold_seconds = time.perf_counter()-started
                stage = "comparison"
                assert repeated == result, "fresh cold continuation changed the mechanical successor"
                assert len(result.state) == len(state)
                if multiplier == 0:
                    assert result.positive_motor_work_j == result.signed_motor_work_j == result.motor_braking_work_j == 0
                next_supply = supply-result.positive_motor_work_j
                assert np.isfinite(next_supply) and next_supply >= 0
            except Exception as error:
                active = cold if cold is not None and stage != "ordinary" else e
                scratch = state_copy(active).astype("<f8").tobytes()
                def result_evidence(value):
                    if value is None:
                        return None
                    data = asdict(value)
                    data["state_base64"] = base64.b64encode(data.pop("state")).decode()
                    return data
                row["failure"] = dict(phase=phase, stage=stage,
                    type=type(error).__name__, error=str(error),
                    attempted_seconds=time.perf_counter()-phase_started,
                    command=command, predecessor_sha256=hashlib.sha256(state).hexdigest(),
                    predecessor_base64=base64.b64encode(state).decode(),
                    native_time_repr=repr(float(active._data.time)),
                    ordinary_result=result_evidence(result), cold_result=result_evidence(repeated),
                    unpublished_scratch_sha256=hashlib.sha256(scratch).hexdigest(),
                    unpublished_scratch_base64=base64.b64encode(scratch).decode())
                break
            supply = next_supply
            measured = dict(phase=phase, effort_nm=effort, native_steps=250000//h_us,
                ordinary_seconds=ordinary_seconds, fresh_repeat_seconds=cold_seconds,
                successor_sha256=hashlib.sha256(result.state).hexdigest(), state_bytes=len(state),
                positive_motor_work_j=result.positive_motor_work_j,
                signed_motor_work_j=result.signed_motor_work_j,
                bearing_loss_j=result.bearing_dissipation_j,
                braking_work_j=result.motor_braking_work_j,
                unresolved_exchange_j=result.unresolved_energy_exchange_j,
                remaining_supply_j=supply, observation=asdict(result.observation),
                fresh_cold_exact=True)
            row["phases"].append(measured)
            state=result.state
            print(json.dumps(encode(dict(event="motion_phase_measured",h_us=h_us,phase=measured))),flush=True)
        row["completed"] = len(row["phases"]) == 2 and row["failure"] is None
        rows.append(row)
        print(json.dumps(encode(dict(event="motion_case_measured",case=row))),flush=True)
    return dict(schema="guala.functional-body.midpoint-motion-feasibility.v1",
        version=VERSION, cases=rows, all_intervals_completed=all(r["completed"] for r in rows),
        native_step_ceiling=sum(r["native_step_ceiling"] for r in rows),
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope="Existing zero-gravity full-torque250ms load then250ms release; NOT full-history accuracy, gravity or production acceptance.")



def saved_motion_refusal():
    """Authenticate and restore the saved numerical input, without advancing."""
    import pathlib
    import zlib
    from guala_body_local_refinement import restore, state_copy
    path = pathlib.Path("docs/evidence/FB-01aj-midpoint-full-interval.json")
    receipt_bytes = path.read_bytes()
    assert hashlib.sha256(receipt_bytes).hexdigest() == "27e6197df42bd9a60ddf9b6dc30f71559c4ff5a2f84f82b96614f9c66b9a939a"
    packed = json.loads(receipt_bytes)["raw_measurement"]
    raw = zlib.decompress(base64.b64decode(packed["payload_zlib_base64"], validate=True))
    assert len(raw) == packed["raw_bytes"]
    assert hashlib.sha256(raw).hexdigest() == packed["raw_sha256"]
    case = json.loads(raw)["cases"][0]
    assert case["h_us"] == 100 and case["failure"]["stage"] == "ordinary"
    fail = case["failure"]
    state_bytes = base64.b64decode(fail["unpublished_scratch_base64"], validate=True)
    assert hashlib.sha256(state_bytes).hexdigest() == fail["unpublished_scratch_sha256"]
    e, xml, _ = engine_at(100)
    assert hashlib.sha256(xml.encode()).hexdigest() == case["model_sha256"]
    m, d = e._model, e._data
    state = np.frombuffer(state_bytes, dtype="<f8").copy()
    assert state.size == mj.mj_stateSize(m, mj.mjtState.mjSTATE_INTEGRATION)
    restore(e, state)
    assert state_copy(e).astype("<f8").tobytes() == state_bytes
    return e, state, case, fail, hashlib.sha256(receipt_bytes).hexdigest()



def saved_event_refusal():
    """Restore the newly retained bracket-refinement refusal; no prefix replay."""
    import pathlib
    import zlib
    from guala_body_local_refinement import restore, state_copy
    path = pathlib.Path("docs/evidence/FB-01aj-midpoint-limit-event.json")
    receipt_bytes = path.read_bytes()
    receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
    assert receipt_sha == "f97ffdfb1d130387703beb3e92b701c8bd8de7f097bf8557751336f328332923"
    packed = json.loads(receipt_bytes)["raw_measurement"]
    raw = zlib.decompress(base64.b64decode(packed["payload_zlib_base64"],validate=True))
    assert len(raw) == packed["raw_bytes"] and hashlib.sha256(raw).hexdigest() == packed["raw_sha256"]
    result = json.loads(raw)
    assert result["schema"] == "guala.functional-body.midpoint-limit-event.v1"
    failed = result["cases"][0]
    assert failed["width_us"] == 1 and failed["stage"] == "onset_bracket" and not failed["completed"]
    attempt = failed["last_attempt"]
    assert attempt["primary_rollback_byte_exact"] is True
    assert "midpoint residual did not converge" in attempt["native_refusal"]
    state_bytes = base64.b64decode(attempt["predecessor_base64"],validate=True)
    e, state, case, fail, original_receipt_sha = saved_motion_refusal()
    assert original_receipt_sha == result["prefix"]["input_receipt_sha256"]
    assert state_bytes == state.astype("<f8").tobytes(), "event trial used a different predecessor"
    e._model.opt.timestep = attempt["dt"]
    restore(e,state)
    assert state_copy(e).astype("<f8").tobytes() == state_bytes
    assert float(e._data.time) == attempt["start_s"]
    assert float(e._data.time)+e._model.opt.timestep == attempt["end_s"]
    return e,state,case,fail,receipt_sha

def stalled_step(event_refusal=False):
    """Inspect ONE retained full-body refusal; no trajectory or runtime edits."""
    from guala_body_local_refinement import state_copy
    e, state, case, fail, receipt_sha = saved_event_refusal() if event_refusal else saved_motion_refusal()
    m, d = e._model, e._data
    q0, v0, t0, a0 = d.qpos.copy(), d.qvel.copy(), float(d.time), d.qacc_warmstart.copy()
    counters = [int(t.number) for t in d.timer]
    try:
        mj.mj_step(m, d)
    except mj.FatalError as error:
        assert "midpoint residual did not converge" in str(error)
        assert state_copy(e).astype("<f8").tobytes() == state.astype("<f8").tobytes()
        refusal = str(error)
    else:
        raise AssertionError("saved failed step no longer refuses")
    final_a = d.qacc.copy()
    timers = [int(t.number)-c for t,c in zip(d.timer,counters)]
    solver_niter = d.solver_niter.copy().tolist()
    native_r = np.empty(m.nv)
    mj.mj_mulM(m,d,native_r,final_a)
    native_r -= d.qfrc_smooth
    native_r -= d.qfrc_constraint
    native_nefc = d.nefc
    normalization = m.stat.meaninertia*max(1,m.nv)
    calls = 0
    def residual(a):
        nonlocal calls
        calls += 1
        d.qpos[:] = q0
        d.qvel[:] = v0+.5*m.opt.timestep*a
        mj.mj_integratePos(m,d.qpos,d.qvel,.5*m.opt.timestep)
        d.time = t0+.5*m.opt.timestep
        mj.mj_fwdPosition(m,d)
        mj.mj_fwdVelocity(m,d)
        mj.mj_fwdActuation(m,d)
        # Calls the SAME native smoothForce used by midpointResidual; its
        # extra unconstrained solve is diagnostic-only, not another body law.
        mj.mj_fwdAcceleration(m,d)
        d.qacc[:] = a
        if d.nefc:
            jar = np.empty(d.nefc)
            mj.mj_mulJacVec(m,d,jar,a)
            jar -= d.efc_aref
            mj.mj_constraintUpdate(m,d,jar,None,0)
        else:
            d.qfrc_constraint[:] = 0
        r = np.empty(m.nv)
        mj.mj_mulM(m,d,r,a)
        r -= d.qfrc_smooth
        r -= d.qfrc_constraint
        assert np.isfinite(r).all()
        return r
    r_final = residual(final_a)
    assert native_nefc == d.nefc
    assert np.array_equal(r_final,native_r), "observer did not reproduce native final residual"
    final_constraints = dict(types=d.efc_type.copy().tolist(), ids=d.efc_id.copy().tolist(),
        state=d.efc_state.copy().tolist(), force=d.efc_force.copy().tolist(),
        aref=d.efc_aref.copy().tolist(), position=d.efc_pos.copy().tolist())
    r_initial = residual(a0)
    baseline = dict(schema=("guala.functional-body.midpoint-event-stall.v1" if event_refusal else "guala.functional-body.midpoint-single-stall.v1"),
        input_receipt_sha256=receipt_sha,
        failed_input_sha256=fail["unpublished_scratch_sha256"], model_sha256=case["model_sha256"],
        time=t0, timestep=m.opt.timestep, dofs=m.nv, refusal=refusal,
        no_successor=True, native_timer_call_deltas=timers, solver_niter=solver_niter,
        tolerance=m.opt.tolerance, normalized_initial_residual=float(np.linalg.norm(r_initial)/normalization),
        normalized_final_residual=float(np.linalg.norm(r_final)/normalization),
        final_acceleration=final_a.tolist(), initial_acceleration=a0.tolist(),
        final_residual=r_final.tolist(), native_residual_reproduced_exactly=True,
        final_constraints=final_constraints,
        scope="One saved unpublished failed native step; sensitivity only, no modified physics or trajectory.")
    # Preserve the complete native replay even if offline sensitivity fails.
    print(json.dumps(encode(dict(event="stalled_step_baseline", baseline=baseline))),flush=True)
    # Offline sensitivity diagnostic only. Two predeclared roundoff-derived
    # central-difference resolutions; neither defines runtime acceptance.
    finite_difference = []
    for scale in (1., .5):
        row = dict(scale=scale, trials=[])
        location = dict(stage="jacobian", coordinate=None, alpha=None)
        try:
            delta = scale*np.cbrt(np.finfo(float).eps)*np.maximum(1.,np.abs(final_a))
            assert np.isfinite(delta).all() and (delta > 0).all()
            jac = np.empty((m.nv,m.nv))
            for i in range(m.nv):
                location["coordinate"] = i
                plus, minus = final_a.copy(), final_a.copy()
                plus[i] += delta[i]
                minus[i] -= delta[i]
                jac[:,i] = (residual(plus)-residual(minus))/(2*delta[i])
            assert np.isfinite(jac).all(), "nonfinite diagnostic Jacobian"
            row["jacobian_sha256"] = hashlib.sha256(jac.astype("<f8").tobytes()).hexdigest()
            location = dict(stage="conditioning", coordinate=None, alpha=None)
            condition = float(np.linalg.cond(jac))
            row["condition"] = condition if np.isfinite(condition) else None
            row["condition_status"] = "finite" if np.isfinite(condition) else repr(condition)
            location["stage"] = "linear_solve"
            direction = np.linalg.solve(jac,-r_final)
            assert np.isfinite(direction).all(), "nonfinite diagnostic direction"
            linear_error = float(np.linalg.norm(jac@direction+r_final)/normalization)
            assert np.isfinite(linear_error), "nonfinite diagnostic linear residual"
            row["newton_direction"] = direction.tolist()
            row["linear_solve_residual"] = linear_error
            location["stage"] = "direction_trial"
            for k in range(8):
                alpha = 2.**-k
                location["alpha"] = alpha
                trial = final_a+alpha*direction
                assert np.isfinite(trial).all(), "nonfinite diagnostic trial"
                norm = float(np.linalg.norm(residual(trial))/normalization)
                assert np.isfinite(norm), "nonfinite diagnostic trial residual"
                row["trials"].append(dict(alpha=alpha,normalized_residual=norm))
        except Exception as error:
            row["failure"] = dict(**location,type=type(error).__name__,error=str(error))
        finite_difference.append(row)
    return dict(**baseline, sensitivity=finite_difference, residual_evaluations=calls,
                residual_evaluation_ceiling=2+4*m.nv+16)





def joint_event_case(body_state, supply, width_us):
    """Partition one saved interval by measured joint-domain changes, offline."""
    from guala_body_local_refinement import restore, state_copy, add_receipts
    e, _, _ = engine_at(100)
    e._restore(body_state)
    m, d = e._model, e._data
    initial = state_copy(e)
    effort = d.ctrl.copy()
    start, end = float(d.time), float(d.time)+.0001
    joints = [i for i in range(m.njnt) if m.jnt_limited[i]]
    assert joints and all(m.jnt_type[i] == mj.mjtJoint.mjJNT_HINGE for i in joints)
    boundaries = [(i,side) for i in joints for side in (0,1)]
    def gaps():
        values=[]
        for i,side in boundaries:
            q=d.qpos[m.jnt_qposadr[i]]
            values.append(float((q-m.jnt_range[i,0] if side==0 else m.jnt_range[i,1]-q)-m.jnt_margin[i]))
        assert np.isfinite(values).all()
        return tuple(values)
    def domain(candidate):
        return tuple(x <= 0 for x in candidate["gaps"])
    def retained(candidate):
        if candidate is None:
            return None
        return dict(end_s=candidate["end"],gaps_rad=candidate["gaps"],
            work_receipt=candidate["work"],
            state_base64=base64.b64encode(candidate["state"].astype("<f8").tobytes()).decode())
    def snapshot(state):
        restore(e,state)
        assert state_copy(e).astype("<f8").tobytes() == state.astype("<f8").tobytes()
        assert all(t == mj.mjtConstraint.mjCNSTR_LIMIT_JOINT for t in d.efc_type), "non-joint constraint outside this witness"
        return dict(gaps_rad=gaps(),constraint_type=d.efc_type.copy().tolist(),
            constraint_id=d.efc_id.copy().tolist(),constraint_force=d.efc_force.copy().tolist(),
            observation=asdict(e._observation()))
    calls, last_attempt = 0, None
    refused, segments = [], []
    stage = "initial"
    current=dict(state=initial,end=start,gaps=gaps(),work=(0.,)*6)
    total_work=(0.,)*6
    remaining=supply
    lower=upper=low_evidence=high_evidence=accepted=None
    bracket=None
    def trial(before,stop,budget):
        nonlocal calls,last_attempt
        dt=stop-before["end"]
        assert np.isfinite(dt) and dt>0 and before["end"]+dt==stop
        assert calls<107, "bounded joint-event numerical work exhausted"
        m.opt.timestep=dt
        restore(e,before["state"])
        assert state_copy(e).astype("<f8").tobytes()==before["state"].astype("<f8").tobytes()
        assert float(d.time)==before["end"]
        assert all(t == mj.mjtConstraint.mjCNSTR_LIMIT_JOINT for t in d.efc_type), "non-joint constraint outside this witness"
        calls+=1
        last_attempt=dict(start_s=before["end"],end_s=stop,dt=dt,
            predecessor_base64=base64.b64encode(before["state"].astype("<f8").tobytes()).decode())
        try:
            work=e._advance_interval(e,effort,1,budget)
        except mj.FatalError as error:
            exact=state_copy(e).astype("<f8").tobytes()==before["state"].astype("<f8").tobytes()
            last_attempt.update(native_refusal=str(error),primary_rollback_byte_exact=exact)
            assert exact, "native refusal changed primary integration bytes"
            raise
        assert np.isfinite(work).all() and float(d.time)==stop
        assert all(t == mj.mjtConstraint.mjCNSTR_LIMIT_JOINT for t in d.efc_type), "non-joint constraint outside this witness"
        return dict(state=state_copy(e),end=stop,gaps=gaps(),work=work)
    try:
        while current["end"]<end:
            stage="whole_remainder"
            lower=dict(current,work=(0.,)*6)
            upper=low_evidence=high_evidence=accepted=None
            bracket=None
            signature=domain(current)
            candidate=None
            try:
                candidate=trial(current,end,remaining)
            except mj.FatalError as error:
                if "midpoint residual did not converge" not in str(error):
                    raise
                refused.append(dict(last_attempt))
            if candidate is not None and domain(candidate)==signature:
                accepted=candidate
            else:
                lo,hi=current["end"],end
                upper=candidate
                stage="first_changed_domain_bracket"
                for _ in range(53):
                    bracket=dict(low_s=lo,high_s=upper["end"] if upper else None,
                        numerical_search_hi_s=hi,low_gaps_rad=lower["gaps"],
                        high_gaps_rad=upper["gaps"] if upper else None)
                    if upper is not None and hi-lo<=width_us/1_000_000:
                        break
                    mid=lo+(hi-lo)/2
                    assert lo<mid<hi, "no representable bracket time"
                    try:
                        candidate=trial(current,mid,remaining)
                    except mj.FatalError as error:
                        if "midpoint residual did not converge" not in str(error):
                            raise
                        refused.append(dict(last_attempt))
                        if upper is not None:
                            raise  # no negative-gap evidence at this unresolved interior point
                        hi=mid
                        continue
                    if domain(candidate)==signature:
                        lo,lower=mid,candidate
                    else:
                        hi,upper=mid,candidate
                assert upper is not None and hi-lo<=width_us/1_000_000
                assert domain(lower)==signature and domain(upper)!=signature
                bracket=dict(low_s=lo,high_s=hi,width_s=hi-lo,
                    low_gaps_rad=lower["gaps"],high_gaps_rad=upper["gaps"],
                    changed_boundaries=[boundaries[i] for i,(a,b) in enumerate(zip(signature,domain(upper))) if a!=b])
                low_evidence=snapshot(lower["state"])
                high_evidence=snapshot(upper["state"])
                accepted=upper
            stage="accept_unpublished_segment"
            assert accepted["end"]>current["end"] and accepted["end"]<=end
            total_work=add_receipts(total_work,accepted["work"])
            remaining=supply-total_work[0]
            assert np.isfinite(total_work).all() and remaining>=0
            segments.append(dict(start_s=current["end"],end_s=accepted["end"],
                work_receipt=accepted["work"],bracket=bracket,
                low_side=low_evidence,high_side=high_evidence,
                endpoint_state_base64=base64.b64encode(accepted["state"].astype("<f8").tobytes()).decode()))
            current=accepted
        stage="final_observation"
        endpoint=snapshot(current["state"])
        assert float(d.time)==end
        return dict(completed=True,width_us=width_us,calls=calls,
            original_start_s=start,original_end_s=end,boundaries=boundaries,
            segments=segments,refused_trials=refused,endpoint=endpoint,
            work_receipt=total_work,remaining_supply_j=remaining,
            endpoint_state_base64=base64.b64encode(current["state"].astype("<f8").tobytes()).decode())
    except Exception as error:
        return dict(completed=False,width_us=width_us,calls=calls,stage=stage,
            boundaries=boundaries,segments=segments,refused_trials=refused,
            failure_type=type(error).__name__,failure=str(error),last_attempt=last_attempt,
            completed_unpublished=dict(published=False,current=retained(current),
                total_work_receipt=total_work,remaining_supply_j=remaining,
                lower=retained(lower),upper=retained(upper),accepted_candidate=retained(accepted),bracket=bracket,
                low_side=low_evidence,high_side=high_evidence),
            unpublished_scratch_base64=base64.b64encode(state_copy(e).astype("<f8").tobytes()).decode())


def joint_events():
    """Reuse authenticated prefix work; resolve all measured joint-domain changes."""
    import pathlib,zlib
    e,state,case,fail,input_sha=saved_motion_refusal()
    receipt_bytes=pathlib.Path("docs/evidence/FB-01aj-midpoint-limit-event.json").read_bytes()
    receipt_sha=hashlib.sha256(receipt_bytes).hexdigest()
    assert receipt_sha=="f97ffdfb1d130387703beb3e92b701c8bd8de7f097bf8557751336f328332923"
    packed=json.loads(receipt_bytes)["raw_measurement"]
    raw=zlib.decompress(base64.b64decode(packed["payload_zlib_base64"],validate=True))
    assert len(raw)==packed["raw_bytes"] and hashlib.sha256(raw).hexdigest()==packed["raw_sha256"]
    prefix=json.loads(raw)["prefix"]
    assert prefix["input_receipt_sha256"]==input_sha and prefix["saved_inner_state_reproduced_exactly"] is True
    body_state=e._capture()
    assert body_state[32:]==state.astype("<f8").tobytes()
    assert hashlib.sha256(body_state).hexdigest()==prefix["prefix_successor_sha256"]
    supply=prefix["remaining_supply_j"]
    assert np.isfinite(supply) and supply>=0
    assert fail["command"]["available_work_j"]-prefix["positive_work_j"]==supply
    rows=[]
    for width in (1.,.5,.25):
        row=joint_event_case(body_state,supply,width)
        if row["completed"]:
            repeated=joint_event_case(body_state,supply,width)
            row["fresh_repeat_exact"]=repeated==row
            row["fresh_repeat"]=None if row["fresh_repeat_exact"] else repeated
        else:
            row["fresh_repeat_exact"]=None
        rows.append(row)
        print(json.dumps(encode(dict(event="joint_event_case",case=row))),flush=True)
    return dict(schema="guala.functional-body.midpoint-joint-events.v1",
        prefix_receipt_sha256=receipt_sha,prefix=prefix,cases=rows,native_call_ceiling=642,
        all_completed=all(x["completed"] and x["fresh_repeat_exact"] for x in rows),
        full_body_qualification=False,
        scope="One saved100us interval; observed joint-domain partition, no earliest-continuum-event guarantee, full accuracy or runtime event policy.")




def subdivide_refused_step(e, stop, supply, initial_refusal, call_ceiling):
    """Chronological native time refinement; never alter any physical force."""
    from guala_body_local_refinement import state_copy, restore, add_receipts
    m, d = e._model, e._data
    initial = state_copy(e)
    start = float(d.time)
    assert initial_refusal["start_s"] == start and initial_refusal["end_s"] == stop
    assert initial_refusal["dt"] == stop-start
    assert base64.b64decode(initial_refusal["predecessor_base64"], validate=True) == initial.astype("<f8").tobytes()
    assert initial_refusal["primary_rollback_byte_exact"] is True
    assert "midpoint residual did not converge" in initial_refusal["native_refusal"]
    assert type(call_ceiling) is int and 0 <= call_ceiling <= 5642
    pending = [(stop, True, 0)]
    total, remaining = (0.,)*6, supply
    calls = accepted = refused = 0
    smallest = largest = None
    trace = hashlib.sha256()
    last_attempt = last_native_refusal = None
    try:
        while pending:
            target, known_refusal, depth = pending.pop()
            begin = float(d.time)
            dt = target-begin
            assert np.isfinite(dt) and dt > 0 and begin+dt == target
            before = state_copy(e)
            m.opt.timestep = dt
            last_attempt = dict(start_s=begin, end_s=target, dt=dt, depth=depth,
                predecessor_base64=base64.b64encode(before.astype("<f8").tobytes()).decode())
            numeric_refusal = known_refusal
            if known_refusal:
                last_attempt.update(native_refusal=initial_refusal["native_refusal"],
                    primary_rollback_byte_exact=True, reused_prior_refusal=True)
            else:
                assert calls < call_ceiling, "bounded native subdivision work exhausted"
                # Native refusal restores primary bytes, not derived stage geometry.
                # Rebuild the true predecessor before interval travel/work sampling.
                restore(e, before)
                assert state_copy(e).astype("<f8").tobytes() == before.astype("<f8").tobytes()
                calls += 1
                try:
                    work = e._advance_interval(e, d.ctrl.copy(), 1, remaining)
                except mj.FatalError as error:
                    exact = state_copy(e).astype("<f8").tobytes() == before.astype("<f8").tobytes()
                    last_attempt.update(native_refusal=str(error), primary_rollback_byte_exact=exact)
                    # Retain the most recent rejected geometry before any rebuild.
                    # This bounded scratch is diagnostic, never a physical successor.
                    last_native_refusal = dict(last_attempt,
                        rejected_geom_positions_m=d.geom_xpos.copy().tolist(),
                        rejected_geom_rotations=d.geom_xmat.copy().tolist())
                    assert exact, "subdivision refusal changed full primary state"
                    if "midpoint residual did not converge" not in str(error):
                        raise
                    numeric_refusal = True
            if numeric_refusal:
                refused += 1
                mid = begin+dt/2
                assert depth < 53 and begin < mid < target, "no bounded representable subdivision"
                # LIFO executes left then right; right receives actual left successor.
                pending.append((target, False, depth+1))
                pending.append((mid, False, depth+1))
                continue
            assert float(d.time) == target and np.isfinite(work).all()
            total = add_receipts(total, work)
            remaining = supply-total[0]
            assert np.isfinite(remaining) and remaining >= 0
            accepted += 1
            smallest = dt if smallest is None else min(smallest, dt)
            largest = dt if largest is None else max(largest, dt)
            trace.update(state_copy(e).astype("<f8").tobytes())
            trace.update(np.asarray(work, dtype="<f8").tobytes())
        assert float(d.time) == stop
        return dict(completed=True, calls=calls, accepted_steps=accepted,
            refused_trials=refused, work_receipt=total, remaining_supply_j=remaining,
            smallest_step_s=smallest, largest_step_s=largest,
            accepted_step_sha256=trace.hexdigest())
    except Exception as error:
        return dict(completed=False, calls=calls, accepted_steps=accepted,
            refused_trials=refused, failure_type=type(error).__name__, failure=str(error),
            unpublished_accepted_work_receipt=total, unpublished_remaining_supply_j=remaining,
            smallest_step_s=smallest, largest_step_s=largest, pending_times=pending,
            last_attempt=last_attempt, last_native_refusal=last_native_refusal,
            accepted_step_sha256=trace.hexdigest(),
            unpublished_scratch_base64=base64.b64encode(state_copy(e).astype("<f8").tobytes()).decode())


def continued_motion_case(body_state, supply, effort_name, saved_step_s,
                          initial_refusal=None):
    """Offline remaining load/release, reusing the accepted prefix exactly."""
    from guala_body_local_refinement import state_copy, restore, add_receipts
    e, _, _ = engine_at(100)
    m, d = e._model, e._data
    m.opt.timestep = saved_step_s
    e._restore(body_state)
    assert e._capture() == body_state
    motor = e.actuator_names.index(effort_name)
    initial_time = float(d.time)
    assert 0 < initial_time < .25
    calls, ordinary_steps = 0, 0
    total = (0.,)*6
    remaining = supply
    phases, events = [], []
    trace = hashlib.sha256()
    phase = stage = "start"
    last_attempt = partition = None
    try:
        for phase, finish in (("continued_load", .25), ("release", .5)):
            if phase == "release":
                # Mechanical bench input, not a programmed organism action.
                d.ctrl[motor] = 0.
                mj.mj_forward(m, d)
                e._check()
            effort = d.ctrl.copy()
            phase_work = (0.,)*6
            phase_start = float(d.time)
            while float(d.time) < finish:
                stage = "ordinary_step"
                assert calls < 5642, "bounded full-interval native work exhausted"
                start = float(d.time)
                stop = min(finish, start+.0001)
                dt = stop-start
                assert dt > 0 and start+dt == stop
                m.opt.timestep = dt
                before = state_copy(e)
                last_attempt = dict(start_s=start, end_s=stop, dt=dt,
                    predecessor_base64=base64.b64encode(before.astype("<f8").tobytes()).decode())
                partition = None
                numeric_refusal = None
                if initial_refusal is not None:
                    assert initial_refusal["start_s"] == start and initial_refusal["end_s"] == stop
                    assert initial_refusal["dt"] == dt
                    assert base64.b64decode(initial_refusal["predecessor_base64"], validate=True) == before.astype("<f8").tobytes()
                    numeric_refusal = initial_refusal
                    initial_refusal = None
                else:
                    calls += 1
                    try:
                        work = e._advance_interval(e, effort, 1, remaining)
                        ordinary_steps += 1
                    except mj.FatalError as error:
                        exact = state_copy(e).astype("<f8").tobytes() == before.astype("<f8").tobytes()
                        last_attempt.update(native_refusal=str(error), primary_rollback_byte_exact=exact)
                        assert exact, "refused step changed full primary state"
                        if "midpoint residual did not converge" not in str(error):
                            raise
                        numeric_refusal = dict(last_attempt)
                if numeric_refusal is not None:
                    last_attempt = numeric_refusal
                    stage = "numerical_time_subdivision"
                    partition = subdivide_refused_step(e, stop, remaining, numeric_refusal, 5642-calls)
                    calls += partition["calls"]
                    if not partition["completed"]:
                        raise RuntimeError("numerical subdivision failed: "+partition["failure"])
                    work = tuple(partition["work_receipt"])
                    events.append(dict(start_s=start, end_s=stop, **partition))
                assert float(d.time) == stop
                assert np.isfinite(work).all()
                total = add_receipts(total, work)
                phase_work = add_receipts(phase_work, work)
                remaining = supply-total[0]
                assert np.isfinite(remaining) and remaining >= 0
                # Digest has observation-only authority; it cannot alter motion.
                trace.update(state_copy(e).astype("<f8").tobytes())
                trace.update(np.asarray(work, dtype="<f8").tobytes())
            stage = "phase_endpoint"
            if phase == "release":
                assert phase_work[0] == phase_work[1] == phase_work[3] == 0.
            mj.mj_forward(m, d)
            e._check()
            state = e._capture()
            phases.append(dict(phase=phase, start_s=phase_start, end_s=float(d.time),
                work_receipt=phase_work, state_base64=base64.b64encode(state).decode(),
                state_sha256=hashlib.sha256(state).hexdigest(),
                remaining_supply_j=remaining, observation=asdict(e._observation())))
        return dict(completed=True, calls=calls, ordinary_steps=ordinary_steps,
            phases=phases, events=events, work_receipt=total,
            remaining_supply_j=remaining, accepted_step_sha256=trace.hexdigest())
    except Exception as error:
        return dict(completed=False, calls=calls, ordinary_steps=ordinary_steps,
            phase=phase, stage=stage, failure_type=type(error).__name__, failure=str(error),
            phases=phases, events=events, work_receipt=total, remaining_supply_j=remaining,
            last_attempt=last_attempt, failed_partition=partition,
            unpublished_scratch_base64=base64.b64encode(state_copy(e).astype("<f8").tobytes()).decode(),
            accepted_step_sha256=trace.hexdigest())


def continued_motion():
    """Authenticate saved21.5ms contact refusal; do not replay its good prefix."""
    import pathlib, zlib
    from guala_body_local_refinement import restore, state_copy
    path = pathlib.Path("docs/evidence/FB-01aj-midpoint-continued-motion.json")
    raw_receipt = path.read_bytes()
    receipt_sha = hashlib.sha256(raw_receipt).hexdigest()
    assert receipt_sha == "8d0ea545e1d1bd00a5698c7546f4f786c9fa9c27be42f79ecce3e53429a8b8f5"
    receipt = json.loads(raw_receipt)
    packed = receipt["raw_measurement"]
    raw = zlib.decompress(base64.b64decode(packed["payload_zlib_base64"], validate=True))
    assert len(raw) == packed["raw_bytes"] and hashlib.sha256(raw).hexdigest() == packed["raw_sha256"]
    prior = json.loads(raw)
    assert prior["input_receipt_sha256"] == "af2dda02925dd22e16717625326ead2fbd7cae5ce267dfb5c789de8ec415d71d"
    saved = prior["case"]
    assert saved["phase"] == "continued_load" and saved["stage"] == "joint_domain_partition"
    assert saved["calls"] == saved["ordinary_steps"]+1 == 199
    failed = saved["last_attempt"]
    assert failed["primary_rollback_byte_exact"] is True
    assert "midpoint residual did not converge" in failed["native_refusal"]
    e, _, original, _, _ = saved_motion_refusal()
    e._model.opt.timestep = failed["dt"]
    state_bytes = base64.b64decode(failed["predecessor_base64"], validate=True)
    assert base64.b64decode(saved["unpublished_scratch_base64"], validate=True) == state_bytes
    restore(e, np.frombuffer(state_bytes, dtype="<f8").copy())
    assert state_copy(e).astype("<f8").tobytes() == state_bytes
    assert float(e._data.time) == failed["start_s"]
    body_state = e._capture()
    supply = saved["remaining_supply_j"]
    assert np.isfinite(supply) and supply >= 0
    assert prior["input_supply_j"]-saved["work_receipt"][0] == supply
    args = (body_state, supply, original["effort_name"], failed["dt"], failed)
    measured = continued_motion_case(*args)
    print(json.dumps(encode(dict(event="subdivided_motion_measured", case=measured))), flush=True)
    if measured["completed"]:
        repeat = continued_motion_case(*args)
        exact = repeat == measured
    else:
        repeat, exact = None, None
    return dict(schema="guala.functional-body.midpoint-subdivided-motion.v1",
        input_receipt_sha256=receipt_sha, input_state_sha256=hashlib.sha256(body_state).hexdigest(),
        input_time_s=float(e._data.time), input_supply_j=supply, case=measured,
        fresh_repeat_exact=exact, fresh_repeat=repeat if exact is not True else None,
        all_completed=measured["completed"] and exact is True, native_call_ceiling=11284,
        full_body_qualification=False,
        scope="Saved21.5ms successor to250ms load and500ms release; numerical convergence/feasibility only, not event-time, full-history accuracy, gravity or mounted world qualification.")


def main():
    assert mj.__version__ == mj.mj_versionString() == ENGINE_VERSION == VERSION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-intervals", action="store_true")
    parser.add_argument("--stalled-step", action="store_true")
    parser.add_argument("--joint-events", action="store_true")
    parser.add_argument("--event-stall", action="store_true")
    parser.add_argument("--continued-motion", action="store_true")
    args = parser.parse_args()
    if args.continued_motion:
        print(json.dumps(encode(continued_motion()), sort_keys=True), flush=True)
        return
    if args.event_stall:
        print(json.dumps(encode(stalled_step(event_refusal=True)),sort_keys=True),flush=True)
        return
    if args.joint_events:
        print(json.dumps(encode(joint_events()), sort_keys=True), flush=True)
        return
    if args.stalled_step:
        print(json.dumps(encode(stalled_step()), sort_keys=True), flush=True)
        return
    if args.motion_intervals:
        print(json.dumps(encode(motion_intervals()), sort_keys=True), flush=True)
        return
    started = time.perf_counter()
    rows = [control(jacobian,islands,force)
            for jacobian in ("dense","sparse") for islands in (False,True)
            for force in (-1,1)]
    result = dict(schema="guala.functional-body.midpoint-equation-witness.v1",
        version=VERSION, controls=rows, refusals=refusal(), body=body(), heat_sign_reversal=heat_reversal(),
        seconds=time.perf_counter()-started,
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        stage_bound_per_step="1 + opt.iterations * opt.ls_iterations",
        proposal_bound_per_step=100, newton_bound_per_proposal_per_island=100,
        scope="Local equation, callers, energy accounting and restart only; contact accuracy and production remain unqualified.")
    print(json.dumps(encode(result), sort_keys=True))


if __name__ == "__main__":
    main()
