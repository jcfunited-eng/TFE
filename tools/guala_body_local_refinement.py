"""Bounded offline numerical refinement of the recorded 30ms body impact.

No production import, contact law change, body publication or motor controller.
Explicit precision requests are diagnostic probes, NOT production tolerances.
Step-doubling agreement is an error indicator, not a continuous error enclosure.
"""
from __future__ import annotations

import base64
from collections import Counter
import hashlib
import json
import math
import resource
import time
import zlib

import mujoco as mj
import numpy as np

from guala_body_contact_onset import PREFIX_US, archived_controls
from guala_body_load_release import engine_at

BASE_US = 100
MAX_DEPTH = 5
MAX_TRIAL_STEPS = 3 * (2 ** (MAX_DEPTH + 1) - 1) * (PREFIX_US // BASE_US)
STATE_KIND = mj.mjtState.mjSTATE_INTEGRATION
WORK_INDICES = (0, 1, 3, 4, 5)


def state_copy(engine):
    mj.mj_getState(engine._model, engine._data, engine._state_buffer, STATE_KIND)
    return engine._state_buffer.copy()


def restore(engine, state):
    # Internal numerical trials only. No state/header transplant into NativeBody
    # or world custody. Full integration state includes applied control/warmstart.
    mj.mj_resetData(engine._model, engine._data)
    mj.mj_setState(engine._model, engine._data, state, STATE_KIND)
    mj.mj_forward(engine._model, engine._data)
    engine._check()


def add_receipts(left, right):
    return tuple(max(a, b) if i == 2 else a + b
                 for i, (a, b) in enumerate(zip(left, right)))


def difference(model, coarse, fine, coarse_work, fine_work):
    # This bench has exactly one free root followed by hinge coordinates.
    # Never subtract quaternion coefficients as angles.
    dq = np.empty(model.nv)
    mj.mj_differentiatePos(model, dq, 1., coarse[0], fine[0])
    dv = fine[1] - coarse[1]
    return {
        "translation_m": float(np.max(np.abs(dq[:3]))),
        "angle_rad": float(np.max(np.abs(dq[3:]))),
        "linear_rate_m_s": float(np.max(np.abs(dv[:3]))),
        "angular_rate_rad_s": float(np.max(np.abs(dv[3:]))),
        "work_j": max(abs(coarse_work[i] - fine_work[i]) for i in WORK_INDICES),
    }


def run(precision, controls):
    engine, xml, _ = engine_at(BASE_US)
    model, data = engine._model, engine._data
    control = controls[BASE_US]
    assert hashlib.sha256(xml.encode()).hexdigest() == control["model_sha256"]
    assert model.jnt_type[0] == mj.mjtJoint.mjJNT_FREE
    assert np.all(model.jnt_type[1:] == mj.mjtJoint.mjJNT_HINGE)
    assert int(model.jnt_dofadr[0]) == 0 and model.nq == model.nv + 1
    initial = engine.initial_state()
    assert hashlib.sha256(initial).hexdigest() == control["initial_state_sha256"]
    effort = data.ctrl.copy()
    effort[engine.actuator_names.index(control["name"])] = control["phases"][0]["effort_nm"]
    assert np.all(effort >= model.actuator_forcerange[:, 0])
    assert np.all(effort <= model.actuator_forcerange[:, 1])
    data.ctrl[:] = effort
    mj.mj_forward(model, data)
    current = state_copy(engine)
    supply = control["initial_supply_j"]
    original_timestep = float(model.opt.timestep)
    total_work = (0.,) * 6
    trial_steps = 0
    rejected = 0
    accepted = Counter()
    error_names = ("translation_m", "angle_rad", "linear_rate_m_s",
                   "angular_rate_rad_s", "work_j")
    tolerance = dict.fromkeys(error_names, precision)
    maximum_accepted_disagreement = dict.fromkeys(error_names, 0.)
    maximum_tested_disagreement = dict.fromkeys(error_names, 0.)
    trace_digest = hashlib.sha256()
    samples = []
    failure = None

    def trial(state, h_us, count, remaining):
        nonlocal trial_steps
        if trial_steps + count > MAX_TRIAL_STEPS:
            raise ValueError("finite numerical trial work exhausted")
        if not 0 < h_us <= BASE_US:
            raise AssertionError("trial changed declared timestep range")
        model.opt.timestep = h_us / 1_000_000
        restore(engine, state)
        trial_steps += count
        receipt = engine._advance_interval(engine, effort, count, remaining)
        # An existing warning/geometry/work refusal propagates out of the entire
        # case; the numerical refinement branch never catches a physical error.
        return state_copy(engine), (data.qpos.copy(), data.qvel.copy()), receipt

    def subdivide(state, h_us, remaining, depth):
        nonlocal rejected
        coarse_state, coarse_pose, coarse_work = trial(state, h_us, 1, remaining)
        fine_state, fine_pose, fine_work = trial(state, h_us / 2, 2, remaining)
        errors = difference(model, coarse_pose, fine_pose, coarse_work, fine_work)
        if not all(math.isfinite(x) for x in errors.values()):
            raise ValueError("non-finite refinement comparison")
        for key, value in errors.items():
            maximum_tested_disagreement[key] = max(maximum_tested_disagreement[key], value)
        if all(errors[k] <= tolerance[k] for k in error_names):
            accepted[h_us / 2] += 2
            for key, value in errors.items():
                maximum_accepted_disagreement[key] = max(maximum_accepted_disagreement[key], value)
            # Diagnostic digest authenticates the accepted complete state and
            # dyadic sequence without retaining lifetime motion history.
            trace_digest.update(float(h_us).hex().encode())
            trace_digest.update(np.asarray(fine_work, dtype="<f8").tobytes())
            trace_digest.update(fine_state.astype("<f8", copy=False).tobytes())
            return fine_state, fine_work
        rejected += 1
        if depth == MAX_DEPTH:
            raise ValueError("declared finest-step precision not met")
        middle, left = subdivide(state, h_us / 2, remaining, depth + 1)
        final, right = subdivide(middle, h_us / 2, remaining - left[0], depth + 1)
        result = add_receipts(left, right)
        if result[0] > remaining:
            raise ValueError("accepted refined work exceeds physical supply")
        return final, result

    started = time.perf_counter()
    completed_us = 0
    accepted_before = None
    try:
        for i in range(PREFIX_US // BASE_US):
            accepted_before = (accepted.copy(), maximum_accepted_disagreement.copy(),
                               trace_digest.copy())
            successor, work = subdivide(current, BASE_US, supply, 0)
            current = successor
            supply -= work[0]
            total_work = add_receipts(total_work, work)
            completed_us = (i + 1) * BASE_US
            accepted_before = None
            if completed_us % 10000 == 0:
                restore(engine, current)
                samples.append(dict(elapsed_us=completed_us,
                    qpos=data.qpos.tolist(), qvel=data.qvel.tolist()))
        restore(engine, current)
        if not math.isfinite(supply) or supply < 0:
            raise ValueError("accepted trajectory exceeded initial supply")
    except ValueError as error:
        # Roll back accepted-only evidence to the same fully completed prefix
        # as current/supply/total_work. Attempt counters remain diagnostic.
        if accepted_before is not None:
            accepted, maximum_accepted_disagreement, trace_digest = accepted_before
        failure = str(error)
    finally:
        model.opt.timestep = original_timestep

    # Independent fixed-resolution trajectories are comparison evidence, not
    # exact continuum solutions or a global error certificate.
    reference = {r["elapsed_us"]: r for r in
        controls[25]["phases"][0]["report"]["trajectory_every_10ms"]}
    comparisons = []
    for sample in samples:
        ref = reference[sample["elapsed_us"]]
        metrics = difference(model, (np.asarray(ref["qpos"]), np.asarray(ref["qvel"])),
                             (np.asarray(sample["qpos"]), np.asarray(sample["qvel"])),
                             (0.,) * 6, (0.,) * 6)
        metrics.pop("work_j")
        comparisons.append(dict(elapsed_us=sample["elapsed_us"], **metrics))
    return {
        "precision_request": tolerance, "complete": failure is None,
        "failure": failure, "completed_prefix_us": completed_us,
        "charged_trial_steps": trial_steps, "max_trial_steps": MAX_TRIAL_STEPS,
        "accepted_steps_by_us": sorted(accepted.items()),
        "rejected_comparisons": rejected,
        "max_tested_disagreement": maximum_tested_disagreement,
        "max_accepted_local_disagreement": maximum_accepted_disagreement,
        "accepted_receipt": list(total_work), "remaining_supply_j": supply,
        "accepted_trace_sha256": trace_digest.hexdigest(),
        "internal_state_sha256": hashlib.sha256(current.astype("<f8", copy=False).tobytes()).hexdigest(),
        "archived_25us_comparisons": comparisons,
        "elapsed_seconds": time.perf_counter() - started,
    }


def main():
    controls = archived_controls()
    # The published archive is checked BEFORE trying new numerical behavior.
    e, _, _ = engine_at(BASE_US)
    state = e.initial_state()
    c = controls[BASE_US]
    result = e.advance(state, None, PREFIX_US, c["initial_supply_j"],
        effort_updates=((e.actuator_names.index(c["name"]), c["phases"][0]["effort_nm"]),))
    reference = next(r for r in c["phases"][0]["report"]["trajectory_every_10ms"]
                     if r["elapsed_us"] == PREFIX_US)
    assert np.array_equal(e._data.qpos, reference["qpos"])
    assert np.array_equal(e._data.qvel, reference["qvel"])
    del e, state, result
    cases = []
    for precision in (1e-4, 1e-5):
        measured = run(precision, controls)
        repeated = run(precision, controls)  # fresh engine, identical input
        for key in measured:
            if key != "elapsed_seconds":
                assert measured[key] == repeated[key], f"cold numerical trial changed {key}"
        measured["fresh_repeat_exact"] = True
        measured["repeat_seconds"] = repeated["elapsed_seconds"]
        cases.append(measured)
    record = dict(schema="guala.functional-body.local-refinement.v1",
        archived_100us_control_exact=True, cases=cases,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        meaning="Offline step-doubling precision requests, not production accuracy limits, global convergence, sensory correctness, or real-time qualification.")
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    print(json.dumps(dict(raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
        payload_zlib_base64=base64.b64encode(zlib.compress(raw, 9)).decode())), flush=True)


if __name__ == "__main__":
    main()
