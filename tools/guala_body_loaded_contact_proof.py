"""Saved-event proof for loaded/unloaded contact-boundary refinement.

Legacy raw integration coordinates are explicit authenticated diagnostic input,
not a runtime header migration. No prefix replay, world authority or network.
"""
from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import json
import traceback

import mujoco as mj
import numpy as np
import guala_body_interval as interval

from guala_body_accuracy_control_proof import read
from guala_body_contact_onset import archived_controls
from guala_body_joint_boundary import encode
from guala_body_local_refinement import restore
from guala_body_trajectory_accuracy import (
    Trajectory, VERSION, contact_support, observer_control, packed_state)

ARCHIVE = ("FB-01aj-midpoint-accepted-trajectory.json",
           "07e1bb88682a25cc8e04d81a7301d156d606e012e31ef4f83b5325d7184206e2")
CALL_CEILING = 505  # Measured: 8 control + 251 (100 us) + 246 (50 us).


def comparison_operand(value):
    # Only retained on an actual mismatch; preserve every compared field.
    row = asdict(value)
    row["state"] = base64.b64encode(value.state).decode()
    row["state_encoding"] = "base64"
    return row


def main():
    assert mj.__version__ == mj.mj_versionString() == VERSION
    assert interval.INTERVAL_ABI == 3 and interval.INTERVAL_LAW == "midpoint-dyadic-accuracy-v2"
    prior, controls = read(ARCHIVE), archived_controls()
    rows = []
    calls = 0
    active = None
    failure = control = None

    def advance(case):
        nonlocal calls, active
        active = case
        case.ceiling = case.calls+CALL_CEILING-calls
        before = case.calls
        try:
            return case.advance_to((float(case.d.time)+.0001)*1e6)
        finally:
            calls += case.calls-before

    def seed(case, state, supply):
        nonlocal active
        active = case
        case.e._restore(state)
        case.initial_supply = case.supply = supply
        case.last_accepted = case.initial = packed_state(case.e)
        case.support = contact_support(case.e)

    try:
        active = Trajectory(100, controls[100])
        active.ceiling = CALL_CEILING
        try:
            control = observer_control(active)
        finally:
            calls += active.calls
        for prior_case in prior["cases"]:
            h = prior_case["h_us"]
            event, = [e for e in prior_case["events"] if not e["bracket_within_1us"]]
            assert event["before_domain"] == event["after_domain"]
            assert event["before_support"] != event["after_support"]
            raw = base64.b64decode(event["predecessor_base64"], validate=True)
            row = dict(h_us=h, predecessor_raw_sha256=hashlib.sha256(raw).hexdigest(),
                       predecessor_wide_s=event["width_s"], completed=False)
            rows.append(row)
            case = Trajectory(h, controls[h])
            active = case
            before_legacy_refusal = case.e._capture()
            try:
                case.e._restore(case.v1_header+raw)
            except ValueError as error:
                assert str(error) == "body state/model mismatch"
                assert case.e._capture() == before_legacy_refusal
                row["old_header_refused"] = True
            else:
                raise AssertionError("old numerical-law header was accepted")
            # Explicitly restore authenticated diagnostic coordinates only.
            restore(case.e, np.frombuffer(raw, dtype="<f8").copy())
            initial = case.e._capture()
            row["initial_v2_state_base64"] = base64.b64encode(initial).decode()
            assert initial[32:] == raw and float(case.d.time) == event["start_s"]
            seed(case, initial, event["available_work_j"])
            first = advance(case)
            first_record = case.record(include_events=True)
            row["first"] = first_record
            support_events = [e for e in case.events if e["before_support"] != e["after_support"]]
            assert support_events, "physical contact unloading was not observed"
            assert all(e["bracket_within_1us"] for e in case.events)
            before_loaded = {tuple(pair) for pair, _ in event["before_support"][1]}
            after_loaded = {tuple(pair) for pair, _ in case.support[1]}
            lost = before_loaded-after_loaded
            expected_lost = before_loaded-{tuple(pair) for pair, _ in event["after_support"][1]}
            assert expected_lost and expected_lost <= lost
            row.update(lost_loaded_pairs=sorted(lost),
                observed_event_width_max_s=max(e["width_s"] for e in first_record["events"]))

            repeated = Trajectory(h, controls[h])
            seed(repeated, initial, event["available_work_j"])
            repeated_result = advance(repeated)
            if repeated_result != first:
                row["repeat_mismatch"] = dict(expected=comparison_operand(first),
                    actual=comparison_operand(repeated_result))
                raise AssertionError("repeat successor differs")
            row.update(exact_repeat=True, repeat_calls=repeated.calls,
                       repeat_state_sha256=hashlib.sha256(repeated_result.state).hexdigest())
            del repeated

            cold = Trajectory(h, controls[h])
            seed(cold, first.state, case.supply)
            assert cold.e._capture() == first.state
            later = advance(case)
            row["warm_continuation"] = comparison_operand(later)
            cold_later = advance(cold)
            del row["warm_continuation"]
            if later != cold_later:
                row["cold_mismatch"] = dict(expected=comparison_operand(later),
                    actual=comparison_operand(cold_later))
                raise AssertionError("cold successor differs")
            row.update(cold_continuation_exact=True, cold_calls=cold.calls,
                       continued_state_sha256=hashlib.sha256(later.state).hexdigest())
            del cold

            refused = Trajectory(h, controls[h])
            seed(refused, initial, 0.)
            try:
                unexpected = advance(refused)
                row["unexpected_zero_energy_successor"] = comparison_operand(unexpected)
            except ValueError as error:
                assert "mechanical energy supply exhausted" in str(error)
                assert refused.e._capture() == initial
                assert refused.work == (0.,)*6 and not refused.events and not refused.impulses
                assert float(refused.m.opt.timestep) == h/1e6
                row["energy_refusal"] = dict(reason=str(error), calls=refused.calls, predecessor_exact=True)
            else:
                raise AssertionError("zero-energy interval was accepted")
            del refused
            row["completed"] = True
    except Exception as error:
        failure = dict(type=type(error).__name__, error=str(error),
                       traceback=traceback.format_exc(limit=8),
                       last_case=active.record(include_events=True) if active is not None else None)
    result = dict(schema="guala.functional-body.loaded-contact-boundary-proof.v1",
        interval_law=interval.INTERVAL_LAW, archive_sha256=ARCHIVE[1],
        completed=failure is None and len(rows) == 2 and all(r["completed"] for r in rows), failure=failure,
        observer_control=control, cases=rows, calls=calls, call_ceiling=CALL_CEILING,
        full_motion_qualified=False, continuum_error_enclosure=False,
        scope="Two authenticated saved unloading events, repeat/cold/refusal branches only; no prefix replay or live world.")
    print(json.dumps(encode(result)), flush=True)


if __name__ == "__main__":
    main()
