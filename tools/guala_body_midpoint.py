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



def stalled_step():
    """Inspect ONE retained full-body refusal; no trajectory or runtime edits."""
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
    assert np.array_equal(state_copy(e), state)
    q0, v0, t0, a0 = d.qpos.copy(), d.qvel.copy(), float(d.time), d.qacc_warmstart.copy()
    counters = [int(t.number) for t in d.timer]
    try:
        mj.mj_step(m, d)
    except mj.FatalError as error:
        assert "midpoint residual did not converge" in str(error)
        assert np.array_equal(state_copy(e), state)
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
    baseline = dict(schema="guala.functional-body.midpoint-single-stall.v1",
        input_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
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



def main():
    assert mj.__version__ == mj.mj_versionString() == ENGINE_VERSION == VERSION
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motion-intervals", action="store_true")
    parser.add_argument("--stalled-step", action="store_true")
    args = parser.parse_args()
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
