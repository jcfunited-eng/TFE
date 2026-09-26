"""One bounded equation/caller witness for the body-only implicit midpoint law.

Analytical constant-inertia controls and one existing 100us body input only.
Not a contact-accuracy, continuum-error, mature-world or production certificate.
The prior coupled-step evidence and its diagnostic remain historical controls.
"""
from __future__ import annotations

from fractions import Fraction
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


def main():
    assert mj.__version__ == mj.mj_versionString() == ENGINE_VERSION == VERSION
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
