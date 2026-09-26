"""One-step, read-only diagnosis of constraint/implicit-bearing splitting.

No new solver, coefficient, motor selection or published state. The complete
observed successor must equal the authenticated existing closed-boundary step.
"""
from __future__ import annotations

import base64
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import resource
import zlib

import mujoco as mj
import numpy as np

from guala_body_contact_onset import archived_controls
from guala_body_joint_boundary import encode
from guala_body_load_release import engine_at

ARCHIVE = Path(__file__).resolve().parents[1] / "docs/evidence/FB-01aj-closed-joint-boundary.json"


def solve2(a, b):
    det = a[0][0]*a[1][1] - a[0][1]*a[1][0]
    assert det > 0
    return ((a[1][1]*b[0]-a[0][1]*b[1])/det,
            (-a[1][0]*b[0]+a[0][0]*b[1])/det)


def exact_counterexample():
    m = ((Q(2), Q(1)), (Q(1), Q(1)))
    h = ((Q(2), Q(1)), (Q(1), Q(2)))
    force, regularizer = (Q(-2), Q(-1)), Q(1,999)
    def reaction(metric):
        free = solve2(metric, force)
        inverse_j = solve2(metric, (Q(1), Q(0)))
        return max(Q(0), -free[0] / (inverse_j[0] + regularizer))
    old_lambda = reaction(m)
    solved = solve2(m, (force[0]+old_lambda,force[1]))
    split = solve2(h, (force[0]+old_lambda,force[1]))
    coupled_lambda = reaction(h)
    coupled = solve2(h, (force[0]+coupled_lambda,force[1]))
    split_residual = split[0]+regularizer*old_lambda
    coupled_residual = coupled[0]+regularizer*coupled_lambda
    assert old_lambda == Q(999,1000)
    assert solved == (Q(-1,1000),Q(-999,1000))
    assert split == (Q(-334,1000),Q(-333,1000))
    assert split_residual == Q(-333,1000)
    assert coupled_lambda == Q(999,667)
    assert coupled == (Q(-1,667),Q(-333,667))
    assert coupled_residual == 0
    return dict(old_lambda=str(old_lambda), solved=list(map(str,solved)),
        split=list(map(str,split)), split_residual=str(split_residual),
        coupled_lambda=str(coupled_lambda), coupled=list(map(str,coupled)),
        coupled_residual=str(coupled_residual))


def main():
    assert mj.__version__ == "3.3.7+guala.closed-limits.1"
    counterexample = exact_counterexample()
    archive = json.loads(ARCHIVE.read_bytes())["corrected"]
    raw = zlib.decompress(base64.b64decode(archive["payload_zlib_base64"]))
    assert len(raw) == archive["raw_bytes"]
    assert hashlib.sha256(raw).hexdigest() == archive["raw_sha256"]
    record = next(r for r in json.loads(raw)["body_startup"]["prefixes"] if r["h_us"] == 100)
    e, xml, _ = engine_at(100)
    c = archived_controls()[100]
    assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
    initial = e.initial_state()
    command = dict(efforts=None, elapsed_us=100, available_work_j=c["initial_supply_j"],
        effort_updates=((e.actuator_names.index(c["name"]),c["phases"][0]["effort_nm"]),))
    original = mj.mj_step
    evidence = {}
    calls = 0
    def observe(m,d):
        nonlocal calls
        assert m is e._model and d is e._data and calls == 0
        before_v = d.qvel.copy()
        original(m,d)
        calls += 1
        assert np.all(d.warning.number == 0)
        assert d.ncon == 0
        assert np.all(d.efc_type == mj.mjtConstraint.mjCNSTR_LIMIT_JOINT)
        expected_derivative = np.zeros(m.nD)
        expected_derivative[m.D_rowadr+m.D_diag] = -m.dof_damping
        assert np.array_equal(d.qDeriv,expected_derivative)
        assert np.array_equal(d.qfrc_passive,-m.dof_damping*before_v)
        delta_v = d.qvel-before_v
        integrated_a = delta_v/m.opt.timestep
        solved_rows, integrated_rows = np.empty(d.nefc),np.empty(d.nefc)
        mj.mj_mulJacVec(m,d,solved_rows,d.qacc)
        mj.mj_mulJacVec(m,d,integrated_rows,integrated_a)
        solved_residual = solved_rows+d.efc_R*d.efc_force-d.efc_aref
        integrated_residual = integrated_rows+d.efc_R*d.efc_force-d.efc_aref
        momentum = np.empty(m.nv)
        mj.mj_mulM(m,d,momentum,delta_v)
        impulse_residual = momentum+m.opt.timestep*m.dof_damping*delta_v - (
            m.opt.timestep*(d.qfrc_smooth+d.qfrc_constraint))
        assert all(np.isfinite(a).all() for a in (
            d.qpos,d.qvel,d.qacc,solved_residual,integrated_residual,impulse_residual))
        rows = []
        for i in range(d.nefc):
            j = int(d.efc_id[i])
            dof = int(m.jnt_dofadr[j])
            rows.append(dict(joint=m.joint(j).name, force=float(d.efc_force[i]),
                regularizer=float(d.efc_R[i]), reference_acceleration=float(d.efc_aref[i]),
                solved_residual=float(solved_residual[i]),
                integrated_residual=float(integrated_residual[i]),
                solved_joint_acceleration=float(d.qacc[dof]),
                integrated_joint_acceleration=float(integrated_a[dof])))
        active = d.efc_force > 0
        evidence.update(rows=rows, active_rows=int(active.sum()), row_count=d.nefc,
            max_active_solved_residual=float(np.max(np.abs(solved_residual[active]),initial=0)),
            max_active_integrated_residual=float(np.max(np.abs(integrated_residual[active]),initial=0)),
            max_physical_impulse_residual=float(np.max(np.abs(impulse_residual),initial=0)),
            max_integrated_vs_solved_acceleration=float(np.max(np.abs(integrated_a-d.qacc),initial=0)))
    try:
        mj.mj_step = observe
        result = e.advance(initial, **command)
    finally:
        mj.mj_step = original
    assert calls == 1
    assert hashlib.sha256(result.state).hexdigest() == record["successor_sha256"]
    assert list(result.observation.qpos) == record["qpos"]
    assert list(result.observation.qvel) == record["qvel"]
    evidence.update(exact_counterexample=counterexample,
        engine_version=mj.__version__, model_sha256=c["model_sha256"],
        complete_successor_exact=True, original_step_calls=calls,
        successor_sha256=record["successor_sha256"],
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope="one startup step; diagnostic only; no numerical or physical law changed")
    print(json.dumps(encode(evidence),sort_keys=True))


if __name__ == "__main__":
    main()
