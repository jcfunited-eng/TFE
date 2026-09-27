"""Focused mechanical proof for exact-coincident contact-load comparison.

Uses authenticated failed body bytes; no world, cognition, network or steering.
Actual sensory contact records remain unmodified native contributions.
"""
from __future__ import annotations

import base64
import hashlib
import json
import traceback

import mujoco as mj
import numpy as np
import guala_body_interval as interval

from dsf_ai_service.substrate.functional_body_native import LocalContact
from guala_body_accuracy_control_proof import read
from guala_body_contact_onset import archived_controls
from guala_body_event_resolution import tactile_limits
from guala_body_joint_boundary import encode
from guala_body_loaded_contact_proof import comparison_operand
from guala_body_trajectory_accuracy import Trajectory, VERSION, contact_support, packed_state

ARCHIVE = ("FB-01aj-midpoint-contact-comparison-diagnostic.json",
           "bbd0e5ee803b7e24bd33d9ac4d9698478d290f243b281bfd70e3f9fd81f35e7c")


def main():
    assert mj.__version__ == mj.mj_versionString() == VERSION
    assert interval.INTERVAL_ABI == 3 and interval.INTERVAL_LAW == "midpoint-dyadic-accuracy-v3"
    prior = read(ARCHIVE)
    assert prior["rollback_exact"] and prior["failure"]["error"] == "no representable accuracy subdivision"
    old = prior["last_case"]
    predecessor = base64.b64decode(old["failed_interval"]["predecessor_base64"], validate=True)
    control = archived_controls()[100]
    result = dict(schema="guala.functional-body.coincident-contact-proof.v1",
                  completed=False, calls=0, call_ceiling=5*prior["call_ceiling"], failure=None)
    active = None

    def seed(state, supply):
        nonlocal active
        active = Trajectory(100, control)
        active.e._restore(state)
        active.initial_supply = active.supply = supply
        active.last_accepted = active.initial = packed_state(active.e)
        active.support = contact_support(active.e)
        return active

    def advance(case):
        nonlocal active
        active = case
        case.ceiling = case.calls+result["call_ceiling"]-result["calls"]
        before = case.calls
        try:
            return case.advance_to((float(case.d.time)+.0001)*1e6)
        finally:
            result["calls"] += case.calls-before

    try:
        # Exact point-load algebra, with deliberately distinct nearby points.
        p = np.array([1., 2., 3.])
        f1, f2 = np.array([2., 3., 5.]), np.array([-1., 7., 4.])
        c1, c2 = np.array([1., 0., 2.]), np.array([3., 2., -1.])
        rows = [(("surface", 0), p, f1, c1), (("surface", 0), p.copy(), f2, c2)]
        grouped, = interval._contact_resultants(rows)
        assert np.array_equal(grouped[2], f1+f2) and np.array_equal(grouped[3], c1+c2)
        assert np.array_equal(np.cross(p, grouped[2])+grouped[3],
                              np.cross(p, f1)+c1+np.cross(p, f2)+c2)
        v, w = np.array([2., 1., 4.]), np.array([1., 3., 2.])
        assert grouped[2] @ v+grouped[3] @ w == f1 @ v+c1 @ w+f2 @ v+c2 @ w
        shifted = p.copy(); shifted[0] = np.nextafter(p[0], np.inf)
        assert len(interval._contact_resultants(rows[:1]+[(rows[0][0], shifted, f2, c2)])) == 2
        assert len(interval._contact_resultants(rows[:1]+[(("other", 0), p, f2, c2)])) == 2
        assert np.array_equal(rows[0][2], f1) and np.array_equal(rows[1][2], f2)
        result["point_load_algebra"] = dict(force=True, moment=True, power=True,
                                             distinct_points=True, distinct_keys=True)

        def points(name):
            return [(tuple(r["key"]), np.asarray(r["position"]), np.asarray(r["force"]),
                     np.asarray(r["couple"])) for r in prior["last_failed_close"][name]]
        a, b = points("coarse_contacts"), points("fine_contacts")
        assert interval._contacts_close(a, b)
        changed = [(k, p, f+np.array([1., 0., 0.]), c) for k, p, f, c in b]
        assert not interval._contacts_close(a, changed)
        shifted = [(k, p+np.array([.001, 0., 0.]), f, c) for k, p, f, c in b]
        assert not interval._contacts_close(a, shifted)
        def tactile(rows):
            return tuple(LocalContact(str(k), tuple(p), tuple(f), tuple(c)) for k,p,f,c in rows)
        local = tactile_limits(tactile(a), tactile(b))
        assert local["complete"] and local["force_n"]["passed"] and local["couple_nm"]["passed"]
        result["saved_comparison"] = dict(raw_counts=[len(a),len(b)], actual_local_limits=local,
                                           excessive_force_refused=True, separated_point_refused=True)

        active = Trajectory(100, control)
        initial_before = active.e._capture()
        try:
            active.e._restore(predecessor)
        except ValueError as error:
            assert str(error) == "body state/model mismatch" and active.e._capture() == initial_before
            result["old_header_refused"] = True
        else:
            raise AssertionError("old numerical law accepted")
        # Authenticated raw diagnostic input, explicitly not a runtime migration.
        initial = active.e._header+predecessor[32:]
        case = seed(initial, old["remaining_supply_j"])
        result["initial_state_base64"] = base64.b64encode(initial).decode()
        first = advance(case)
        result["first"] = case.record(include_events=True)
        assert all(e["bracket_within_1us"] for e in case.events)
        # _observation remains the raw producer; compare repeatable full outputs.
        repeated = seed(initial, old["remaining_supply_j"])
        repeated_result = advance(repeated)
        if first != repeated_result:
            result["repeat_mismatch"] = dict(expected=comparison_operand(first),
                                              actual=comparison_operand(repeated_result))
            raise AssertionError("repeat successor differs")
        result["exact_repeat"] = True
        cold = seed(first.state, case.supply)
        later = advance(case)
        result["warm_continuation"] = comparison_operand(later)
        cold_later = advance(cold)
        if cold_later != later:
            result["cold_mismatch"] = dict(expected=comparison_operand(later),
                                            actual=comparison_operand(cold_later))
            raise AssertionError("cold successor differs")
        del result["warm_continuation"]
        result["cold_continuation_exact"] = True
        result["continued_state_sha256"] = hashlib.sha256(later.state).hexdigest()
        refused = seed(initial, 0.)
        try:
            advance(refused)
        except ValueError as error:
            assert "mechanical energy supply exhausted" in str(error)
            assert refused.e._capture() == initial
            assert refused.work == (0.,)*6 and not refused.events and not refused.impulses
            result["energy_refusal"] = dict(reason=str(error), calls=refused.calls, predecessor_exact=True)
        else:
            raise AssertionError("zero energy accepted")
        result["completed"] = True
    except Exception as error:
        result["failure"] = dict(type=type(error).__name__, error=str(error),
            traceback=traceback.format_exc(limit=8),
            last_case=active.record(include_events=True) if active is not None else None)
    result["full_body_qualification"] = False
    result["continuum_error_enclosure"] = False
    print(json.dumps(encode(result)), flush=True)


if __name__ == "__main__":
    main()
