"""Focused offline admission proof for accuracy-controlled mechanical intervals.

Authenticated legacy raw integration coordinates are an explicit diagnostic
input, NOT a header migration. Cold continuation uses only new-law state bytes.
No world, live organism, network, or cognitive decision authority is instantiated.
"""
from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time
import zlib

import mujoco as mj
import numpy as np
import guala_body_interval as interval

from dsf_ai_service.substrate.functional_body_native import ENGINE_VERSION, NativeBody
from guala_body_contact_onset import archived_controls
from guala_body_joint_boundary import encode
from guala_body_load_release import engine_at
from guala_body_local_refinement import restore, state_copy

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ("FB-01aj-midpoint-first-divergence-refinement.json",
           "ad25ecfae7475907043f2f192f5769fc3dda75b5c6533e5f3b01e999bf808eb3")
JOINT = ("FB-01aj-midpoint-joint-events.json",
         "af2dda02925dd22e16717625326ead2fbd7cae5ce267dfb5c789de8ec415d71d")


def read(reference):
    name, sha = reference
    raw = (ROOT/"docs/evidence"/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha
    p = json.loads(raw)["raw_measurement"]
    body = zlib.decompress(base64.b64decode(p["payload_zlib_base64"], validate=True))
    assert len(body) == p["raw_bytes"] and hashlib.sha256(body).hexdigest() == p["raw_sha256"]
    return json.loads(body)


def main():
    assert mj.__version__ == mj.mj_versionString() == ENGINE_VERSION
    assert interval.INTERVAL_ABI == 3 and interval.INTERVAL_LAW == "midpoint-dyadic-accuracy-v1"
    # Arithmetic falsifier only: two contact-point vectors partly cancel.
    # This exercises the same point-to-pair reduction used by native contacts.
    pair_impulse = interval._pair_impulses((
        ((2, 7), np.array([1., 1., 0.]), np.array([0., 1., 1.])),
        ((2, 7), np.array([1., -1., 0.]), np.array([0., 1., -1.])),
        ((3, 8), np.array([1., 0., 0.]), np.zeros(3)),
        ((3, 8), np.array([-1., 0., 0.]), np.zeros(3)),
    ), .25)
    assert np.array_equal(pair_impulse[(2, 7)][0], [.5, 0., 0.])
    assert np.array_equal(pair_impulse[(2, 7)][1], [0., .5, 0.])
    assert pair_impulse[(2, 7)][2:] == (.5, .5)
    assert pair_impulse[(3, 8)][2:] == (0., 0.)
    joint, refinement = read(JOINT), read(ARCHIVE)
    old = next(c for c in joint["cases"] if c["width_us"] == .25)
    raw = base64.b64decode(old["endpoint_state_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == refinement["predecessor_sha256"]
    values = np.frombuffer(raw, dtype="<f8").copy()
    assert np.isfinite(values).all()
    control = archived_controls()[100]
    engine, xml, limits = engine_at(100)
    assert hashlib.sha256(xml.encode()).hexdigest() == control["model_sha256"]
    assert float(engine._model.opt.timestep) == .0001
    restore(engine, values)
    assert state_copy(engine).astype("<f8").tobytes() == raw
    initial = engine._capture()
    supply = old["remaining_supply_j"]
    original_step = mj.mj_step
    calls = 0
    runs = []
    failures = []
    last_native = None
    failure = None
    q_difference = v_difference = None
    cold_exact = False

    def counted(m, d):
        nonlocal calls, last_native
        if calls >= 480:
            raise RuntimeError("focused proof native-call ceiling exhausted")
        calls += 1
        last_native = dict(call=calls, time_s=float(d.time), dt_s=float(m.opt.timestep))
        original_step(m, d)
        last_native["completed_time_s"] = float(d.time)

    def advance(e, state, work_supply, label, updates=()):
        start_calls = calls
        started = time.perf_counter()
        value = e.advance(state, None, 100, work_supply, effort_updates=updates)
        assert e._capture() == value.state and e._model.opt.timestep == .0001
        runs.append(dict(label=label, native_calls=calls-start_calls,
            elapsed_s=time.perf_counter()-started,
            state_sha256=hashlib.sha256(value.state).hexdigest(),
            positive_work_j=value.positive_motor_work_j,
            signed_work_j=value.signed_motor_work_j,
            braking_work_j=value.motor_braking_work_j,
            bearing_work_j=value.bearing_dissipation_j))
        return value

    mj.mj_step = counted
    try:
        first = advance(engine, initial, supply, "same-predecessor accuracy")
        assert runs[-1]["native_calls"] > 3, "known coarse discrepancy was not refined"
        repeat = advance(engine, initial, supply, "exact repeat")
        assert repeat == first
        # Independent archived uniform25us endpoint: compare coordinates, rates,
        # and actual work, not only the candidate's own error indicator.
        reference = next(row["result"] for row in refinement["cases"] if row["result"]["h_us"] == 25.)
        reference_state = base64.b64decode(reference["state_base64"], validate=True)
        ref_engine = NativeBody(xml, limits, sensory_root=engine._sensory_root)
        restore(ref_engine, np.frombuffer(reference_state[32:], dtype="<f8").copy())
        q_difference = float(np.max(np.abs(engine._data.qpos-ref_engine._data.qpos), initial=0))
        v_difference = float(np.max(np.abs(engine._data.qvel-ref_engine._data.qvel), initial=0))
        assert q_difference <= .0001 and v_difference <= .001
        assert abs(first.positive_motor_work_j-reference["work"][0]) <= 1e-6
        assert abs(first.bearing_dissipation_j-reference["work"][4]) <= 1e-6

        restored = NativeBody(xml, limits, sensory_root=engine._sensory_root)
        restored._restore(first.state)
        assert restored._capture() == first.state
        remaining = supply-first.positive_motor_work_j
        later = advance(engine, first.state, remaining, "continued interval")
        cold_later = advance(restored, first.state, remaining, "cold continued interval")
        assert later == cold_later

        cold_exact = True
        # Same physical input, deliberately smaller declared computational budget.
        # No active organism or physical state is edited to obtain a pass.
        bounded = NativeBody(xml, replace(limits, max_substeps=1), sensory_root=engine._sensory_root)
        restore(bounded, values)
        bounded_initial = bounded._capture()
        for label, e, state, work_supply, updates, reason in (
            ("call budget", bounded, bounded_initial, supply, (), "native accuracy call allowance exhausted"),
            ("physical supply", engine, initial, 0., (), "mechanical energy supply exhausted"),
            ("updated effort rollback", engine, initial, 0.,
             ((engine.actuator_names.index(control["name"]), control["phases"][0]["effort_nm"]+1e-9),),
             "mechanical energy supply exhausted"),
        ):
            start_calls = calls
            try:
                advance(e, state, work_supply, label, updates)
            except ValueError as error:
                assert reason in str(error), str(error)
                assert e._capture() == state and e._model.opt.timestep == .0001
                failures.append(dict(label=label, reason=str(error), native_calls=calls-start_calls,
                                     predecessor_exact=True))
            else:
                raise AssertionError("expected bounded refusal did not occur: "+label)
    except Exception as error:
        failure = dict(type=type(error).__name__, message=str(error), last_native=last_native)

    finally:
        mj.mj_step = original_step
    result = dict(schema="guala.functional-body.accuracy-control-proof.v1",
        completed=failure is None, failure=failure, engine_version=ENGINE_VERSION,
        interval_abi=interval.INTERVAL_ABI, archive_sha256=ARCHIVE[1],
        raw_predecessor_sha256=hashlib.sha256(raw).hexdigest(),
        new_state_sha256=hashlib.sha256(initial).hexdigest(), runs=runs, failures=failures,
        calls=calls, call_ceiling=480, pair_resultant_arithmetic_passed=True,
        reference_q_max_difference=q_difference,
        reference_v_max_difference=v_difference, cold_continuation_exact=cold_exact,
        full_motion_qualified=False, continuum_error_enclosure=False,
        scope="Authenticated local discrepancy plus next interval, repeat and refusal/cold branches; no gravity/contact/full-world qualification.")
    print(json.dumps(encode(result)), flush=True)


if __name__ == "__main__":
    main()
