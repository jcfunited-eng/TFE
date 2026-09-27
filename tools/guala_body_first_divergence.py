"""Three-call isolation of the saved 1800us body accuracy discrepancy.

Restores an authenticated, already-measured joint-event endpoint. No replay of
the prefix, no new mechanics, no world or organism authority, no adaptive retry.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path
import time
import zlib

import mujoco as mj
import numpy as np

from guala_body_contact_onset import archived_controls
from guala_body_joint_boundary import encode
from guala_body_local_refinement import add_receipts, restore
from guala_body_midpoint import VERSION
from guala_body_trajectory_accuracy import Errors, Trajectory, contact_support, primary

ROOT = Path(__file__).resolve().parents[1]
JOINT = ("FB-01aj-midpoint-joint-events.json",
         "af2dda02925dd22e16717625326ead2fbd7cae5ce267dfb5c789de8ec415d71d")
WHOLE = ("FB-01aj-midpoint-trajectory-accuracy.json",
         "c6ac46c2d01131f294f184847a3d9caa7a68d8eaa327af4c5dca6d91245cc01e")
LIBRARY_SHA = "de96a1766223905d26b1df0e68ce7bc97608cf2c6238acef8dcf8b344a3fd48f"


def read_receipt(reference):
    name, expected = reference
    raw = (ROOT / "docs/evidence" / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    receipt = json.loads(raw)
    assert receipt["library_sha256"] == LIBRARY_SHA
    packed = receipt["raw_measurement"]
    data = zlib.decompress(base64.b64decode(packed["payload_zlib_base64"], validate=True))
    assert len(data) == packed["raw_bytes"]
    assert hashlib.sha256(data).hexdigest() == packed["raw_sha256"]
    return json.loads(data)


def boundaries(case):
    m, d = case.m, case.d
    joints = []
    for i in range(m.njnt):
        if not m.jnt_limited[i]:
            continue
        assert m.jnt_type[i] == mj.mjtJoint.mjJNT_HINGE
        q = float(d.qpos[m.jnt_qposadr[i]])
        joints.append(dict(joint_id=i, name=case.e.joint_names[i],
            angle=q, rate=float(d.qvel[m.jnt_dofadr[i]]),
            gaps=[float(q-m.jnt_range[i, 0]-m.jnt_margin[i]),
                  float(m.jnt_range[i, 1]-q-m.jnt_margin[i])]))
    return dict(time_s=float(d.time), joints=joints,
        constraint_type=d.efc_type.tolist(), constraint_id=d.efc_id.tolist(),
        constraint_force=d.efc_force.tolist(), support=contact_support(case.e))


def main():
    assert mj.mj_versionString() == mj.__version__ == VERSION
    joint, whole = read_receipt(JOINT), read_receipt(WHOLE)
    assert joint["all_completed"] and whole["all_completed"]
    assert whole["first_failure"]["time_us"] == 1800
    selected = [r for r in joint["cases"] if r["width_us"] == .25]
    assert len(selected) == 1 and selected[0]["completed"] and selected[0]["fresh_repeat_exact"]
    selected = selected[0]
    raw = base64.b64decode(selected["endpoint_state_base64"], validate=True)
    physical = np.frombuffer(raw, dtype="<f8").copy()
    assert np.isfinite(physical).all()
    control = archived_controls()[100]
    cases = [Trajectory(h, control) for h in (100, 50)]

    # Read the original two different-history successors without advancing.
    # This recovers the actual first-error magnitudes omitted by worst-only
    # per-channel summaries; it does not regenerate either failed trajectory.
    original_boundaries = []
    for case, saved in zip(cases, whole["first_failure_states"]):
        assert case.h_us == saved["h_us"] and saved["time_s"] == .0018
        state = base64.b64decode(saved["state_base64"], validate=True)
        dt = saved["native_dt_s"]
        assert np.isfinite(dt) and dt > 0
        case.m.opt.timestep = dt
        case.e._restore(state)
        assert case.e._capture() == state
        case.work = tuple(saved["work"])
        original_boundaries.append(boundaries(case))
    original = Errors()
    original.compare(cases[0], cases[1], cases[0].snapshot(), cases[1].snapshot(), 1800)

    # Same raw native state under the same authenticated model/engine. This is
    # diagnostic restore, never a persistence-header substitution or migration.
    for case in cases:
        assert physical.nbytes == case.e._state_buffer.nbytes
        dt = 100 / 1_000_000
        assert np.isfinite(dt) and dt > 0
        case.m.opt.timestep = dt
        restore(case.e, physical)
        assert primary(case.e) == raw
        assert float(case.d.time) == selected["original_end_s"]
        case.work = (0.,) * 6
        case.initial_supply = case.supply = selected["remaining_supply_j"]
        case.support = contact_support(case.e)
        case.last_accepted = base64.b64encode(case.e._capture()).decode()
        case.initial = case.last_accepted
        case.ceiling = 100 // case.h_us
    assert cases[0].initial == cases[1].initial
    start = float(cases[0].d.time)
    finish = start + .0001
    common_boundary = boundaries(cases[0])
    steps, failure = [], None
    comparison = Errors()
    completed = False
    started = time.perf_counter()
    try:
        for case in cases:
            endpoints = (finish,) if case.h_us == 100 else (start + .00005, finish)
            for stop in endpoints:
                before = boundaries(case)
                case.m.opt.timestep = stop - float(case.d.time)
                assert case.m.opt.timestep > 0
                work = case.e._advance_interval(case.e, case.d.ctrl.copy(), 1, case.supply)
                case.work = add_receipts(case.work, work)
                case.supply = case.initial_supply - case.work[0]
                assert np.isfinite(case.work).all() and case.supply >= 0
                assert float(case.d.time) == stop
                steps.append(dict(h_us=case.h_us, before=before, after=boundaries(case),
                                  result=case.record()))
        comparison.compare(cases[0], cases[1], cases[0].snapshot(), cases[1].snapshot(), 1800)
        completed = True
    except Exception as error:
        failure = dict(type=type(error).__name__, message=str(error))
    print(json.dumps(encode(dict(schema="guala.functional-body.first-divergence.v1",
        version=VERSION, model_sha256=whole["model_sha256"],
        input_artifact_sha256=JOINT[1], original_accuracy_artifact_sha256=WHOLE[1],
        predecessor_sha256=hashlib.sha256(raw).hexdigest(),
        start_s=start, end_s=finish, prior_interval_construction_replayed=False,
        common_boundary=common_boundary, original_boundaries=original_boundaries,
        original_metrics=original.result(), original_first_error=original.first_failure,
        calls=sum(c.calls for c in cases), call_ceiling=3,
        all_completed=completed, failure=failure, steps=steps,
        cases=[c.record(include_events=True) for c in cases],
        metrics=comparison.result(), first_failure=comparison.first_failure,
        worst_failure=comparison.worst_failure,
        elapsed_seconds=time.perf_counter()-started,
        full_body_qualification=False,
        scope="Three native steps from one archived1700us predecessor; local mesh disagreement only, not full-trajectory or continuum proof."
    ))), flush=True)


def refinement():
    """One fixed local resolution matrix, reusing the archived 50us endpoint."""
    assert mj.mj_versionString() == mj.__version__ == VERSION
    isolation = read_receipt((
        "FB-01aj-midpoint-first-divergence.json",
        "df2887df851390b2d6a8db95d2d66411495bb2495546ef9f9ff95ebf7162c8d4"))
    joint = read_receipt(JOINT)
    assert isolation["all_completed"] and isolation["calls"] == 3
    selected = next(row for row in joint["cases"] if row["width_us"] == .25)
    raw = base64.b64decode(selected["endpoint_state_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == isolation["predecessor_sha256"]
    physical = np.frombuffer(raw, dtype="<f8").copy()
    assert np.isfinite(physical).all()
    control = archived_controls()[100]
    prior = Trajectory(50, control)
    saved = next(row for row in isolation["cases"] if row["h_us"] == 50)
    prior.m.opt.timestep = saved["native_dt_s"]
    assert np.isfinite(prior.m.opt.timestep) and prior.m.opt.timestep > 0
    state = base64.b64decode(saved["state_base64"], validate=True)
    prior.e._restore(state)
    assert prior.e._capture() == state and not saved["impulses"]
    prior.work = tuple(saved["work"])
    prior.supply = saved["remaining_supply_j"]
    prior_snapshot = prior.snapshot()
    start, finish = isolation["start_s"], isolation["end_s"]
    assert finish == start + .0001
    rows, comparisons = [], []
    failure = None
    cases = []
    common_boundary = None
    active_case = None
    changes, before, attempted_step = [], None, None

    def signature(record):
        return (tuple((j["joint_id"], *(g <= 0 for g in j["gaps"])) for j in record["joints"]),
                tuple(record["constraint_type"]), tuple(record["constraint_id"]), record["support"])

    try:
        for h_us in (25., 12.5, 6.25, 3.125):
            active_case = None
            changes, before, attempted_step = [], None, None
            case = Trajectory(h_us, control)
            active_case = case
            cases.append(case)
            steps = int(100 / h_us)
            assert steps * h_us == 100
            case.ceiling = steps
            case.m.opt.timestep = .0001
            restore(case.e, physical)
            assert primary(case.e) == raw and float(case.d.time) == start
            case.work = (0.,) * 6
            case.initial_supply = case.supply = selected["remaining_supply_j"]
            case.last_accepted = base64.b64encode(case.e._capture()).decode()
            case.initial = case.last_accepted
            case.support = contact_support(case.e)
            before = boundaries(case)
            if common_boundary is None:
                common_boundary = before
            else:
                assert before == common_boundary
            changes = []
            for index in range(1, steps + 1):
                stop = finish if index == steps else start + index * h_us / 1_000_000
                attempted_step = dict(index=index, target_s=stop)
                case.m.opt.timestep = stop - float(case.d.time)
                assert np.isfinite(case.m.opt.timestep) and case.m.opt.timestep > 0
                work = case.e._advance_interval(case.e, case.d.ctrl.copy(), 1, case.supply)
                case.work = add_receipts(case.work, work)
                case.supply = case.initial_supply - case.work[0]
                assert np.isfinite(case.work).all() and case.supply >= 0
                assert float(case.d.time) == stop
                after = boundaries(case)
                if signature(after) != signature(before):
                    changes.append(dict(before=before, after=after))
                before = after
            current_snapshot = case.snapshot()
            comparison = Errors()
            comparison.compare(prior, case, prior_snapshot, current_snapshot, 1800)
            comparisons.append(dict(coarse_us=prior.h_us, fine_us=h_us,
                metrics=comparison.result(), first_failure=comparison.first_failure,
                worst_disagreement=comparison.worst_failure))
            rows.append(dict(result=case.record(include_events=True),
                final_boundary=before, observed_boundary_changes=changes))
            prior, prior_snapshot = case, current_snapshot
            print(json.dumps(encode(dict(event="local_refinement_measured",
                case=rows[-1], comparison=comparisons[-1]))), flush=True)
    except Exception as error:
        failure = dict(type=type(error).__name__, message=str(error))
    print(json.dumps(encode(dict(
        schema="guala.functional-body.first-divergence-refinement.v1",
        version=VERSION, predecessor_sha256=isolation["predecessor_sha256"],
        start_s=start, end_s=finish, baseline_50us_replayed=False,
        new_native_calls=sum(c.calls for c in cases), native_call_ceiling=60,
        all_completed=len(rows) == 4 and failure is None, failure=failure,
        common_boundary=common_boundary, cases=rows, comparisons=comparisons,
        interrupted_case=(dict(result=active_case.record(include_events=True),
            observed_boundary_changes=changes, last_observed_boundary=before,
            attempted_substep=attempted_step) if failure and active_case is not None else None),
        continuum_error_enclosure=False, full_body_qualification=False,
        scope="Same1700us predecessor; fixed four-resolution local map only. Endpoint branch observations do not exclude hidden crossings; no fulltrajectory, continuum or live qualification."
    ))), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--refinement"]:
        refinement()
    elif not sys.argv[1:]:
        main()
    else:
        raise ValueError("expected no argument or --refinement")
