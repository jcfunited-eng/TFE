"""Offline accepted-trajectory accuracy evidence for the frozen ABI3 body law.

The native interval alone chooses its numerical mesh. This observer stages only
accepted fine motion and commits it only after the ordinary body call succeeds.
Sample agreement is not a continuum enclosure or whole-body qualification.
"""
from __future__ import annotations

import base64
from collections import Counter, deque
from dataclasses import asdict
import hashlib
import json
import math
import resource
import time
import traceback

import mujoco as mj
import numpy as np
import guala_body_interval as interval

from guala_body_contact_onset import archived_controls
from guala_body_event_resolution import tactile_limits
from guala_body_joint_boundary import encode
from guala_body_load_release import engine_at
from guala_body_local_refinement import add_receipts, state_copy
from guala_body_accuracy_control_proof import JOINT, read

SCHEMA = "guala.functional-body.accepted-trajectory-accuracy.v1"
VERSION = "3.3.7+guala.midpoint-step.1"
ANGLE = math.radians(.01)
PROOF = ("FB-01aj-midpoint-accuracy-control-proof.json",
         "bb7ae1f244540448208dd0ff4dd638651c47deb4d8e1f22ea915773014db2d63")


def packed_state(e):
    return base64.b64encode(e._capture()).decode()


def primary(e):
    return state_copy(e).astype("<f8").tobytes()


def finite(value):
    a = np.asarray(value, dtype=float)
    if not np.isfinite(a).all():
        raise ValueError("non-finite accuracy observation")
    return a


def contact_support(e):
    geometric, loaded = Counter(), Counter()
    for i, c in enumerate(e._data.contact):
        pair = tuple(sorted(int(x) for x in c.geom))
        if c.efc_address >= 0:
            geometric[pair] += 1
            force = np.empty(6)
            mj.mj_contactForce(e._model, e._data, i, force)
            if np.any(finite(force)):
                loaded[pair] += 1
    return tuple(sorted(geometric.items())), tuple(sorted(loaded.items()))


def plain_domain(value):
    return tuple(tuple(bool(x) for x in row) if i < 2 else
                 tuple(tuple(int(x) for x in pair) for pair in row) if i >= 5 else
                 tuple(int(x) for x in row) for i, row in enumerate(value))


def current_domain(e, support):
    m, d = e._model, e._data
    q = d.qpos[e._limit_qpos]
    joints = np.asarray(e._limited, dtype=np.intp)
    return plain_domain((
        q <= m.jnt_range[joints, 0]+m.jnt_margin[joints],
        q >= m.jnt_range[joints, 1]-m.jnt_margin[joints],
        d.efc_type, d.efc_id, d.efc_state,
        sorted(tuple(int(g) for g in c.geom) for c in d.contact if c.efc_address >= 0),
        tuple(pair for pair, count in support[1] for _ in range(count))))


class Trajectory:
    def __init__(self, h_us, control):
        self.e, xml, limits = engine_at(h_us)
        self.m, self.d = self.e._model, self.e._data
        state = self.e.initial_state()
        old_header = hashlib.sha256(
            ("3.3.7"+repr(limits)+repr(self.e._sensory_root)+xml).encode()).digest()
        assert hashlib.sha256(xml.encode()).hexdigest() == control["model_sha256"]
        assert hashlib.sha256(old_header+state[32:]).hexdigest() == control["initial_state_sha256"]
        assert np.all(self.m.opt.gravity == 0)
        # Historical digest comparison only; never a restore/migration prefix.
        self.v1_header = hashlib.sha256(
            (VERSION+"midpoint-dyadic-accuracy-v1"+repr(limits)
             +repr(self.e._sensory_root)+xml).encode()).digest()
        self.h_us = h_us
        self.ceiling = 3*(500000//h_us+642)
        self.motor = self.e.actuator_names.index(control["name"])
        self.d.ctrl[self.motor] = control["phases"][0]["effort_nm"]
        mj.mj_forward(self.m, self.d)
        self.e._check()
        self.initial_supply = self.supply = control["initial_supply_j"]
        self.work = (0.,)*6
        self.calls = self.accepted = self.refused = 0
        self.native_seconds = self.interval_seconds = self.observer_seconds = 0.
        self.impulses, self.events, self.endpoints = {}, [], []
        self.support = contact_support(self.e)
        self.last_attempt = self.failed_interval = None
        self.last_accepted = self.initial = packed_state(self.e)
        self.geom = np.asarray(sorted(self.e._self_geoms), dtype=int)
        self.geom_labels = [self.e.geom_names[i] for i in self.geom]
        self.velocity = np.empty((len(self.geom), 6))
        self.sensor_groups = {}
        for label, kind in (
            ("specific_force_m_s2", mj.mjtSensor.mjSENS_ACCELEROMETER),
            ("gyro_rad_s", mj.mjtSensor.mjSENS_GYRO),
            ("proprioceptive_angle_rad", mj.mjtSensor.mjSENS_JOINTPOS),
            ("proprioceptive_rate_rad_s", mj.mjtSensor.mjSENS_JOINTVEL),
        ):
            ids = [i for i in self.e._self_sensors if self.m.sensor_type[i] == kind]
            assert ids, "required feedback channel absent: "+label
            self.sensor_groups[label] = (
                [self.e._sensor_names[i] for i in ids],
                [slice(int(self.m.sensor_adr[i]), int(self.m.sensor_adr[i]+self.m.sensor_dim[i])) for i in ids])

    def advance_to(self, nominal_us):
        before = self.e._capture()
        begin = float(self.d.time)
        staged = dict(work=(0.,)*6, impulses={}, events=[], pieces=0,
                      end=begin, state=primary(self.e))
        recent = deque(maxlen=2)
        one_step, close, native_step = interval._one_step, interval._close, mj.mj_step
        native_before, observer_before = self.native_seconds, self.observer_seconds
        started = time.perf_counter()

        def observed_native(m, d):
            if self.calls >= self.ceiling:
                raise RuntimeError("bounded trajectory native-call allowance exhausted")
            self.calls += 1
            t = time.perf_counter()
            try:
                return native_step(m, d)
            finally:
                self.native_seconds += time.perf_counter()-t

        def observed_step(e, effort, supply, stop):
            assert e is self.e
            t = time.perf_counter()
            raw = primary(e)
            support = contact_support(e)
            row = dict(start=float(self.d.time), stop=stop, before=raw,
                       domain=current_domain(e, support), support=support, supply=supply)
            self.last_attempt = dict(start_s=row["start"], end_s=stop,
                predecessor_base64=base64.b64encode(raw).decode(), available_work_j=supply)
            self.observer_seconds += time.perf_counter()-t
            try:
                result = one_step(e, effort, supply, stop)
            except mj.FatalError:
                self.refused += 1
                raise
            t = time.perf_counter()
            row.update(result=result, after_support=contact_support(e))
            assert primary(e) == result[0]["state"].astype("<f8").tobytes()
            recent.append(row)
            self.last_attempt["native_step_completed"] = True
            self.observer_seconds += time.perf_counter()-t
            return result

        def observed_close(e, coarse, fine, coarse_work, fine_work,
                           coarse_impulse, fine_impulse, dt):
            accepted = close(e, coarse, fine, coarse_work, fine_work,
                             coarse_impulse, fine_impulse, dt)
            if not accepted:
                return accepted
            t = time.perf_counter()
            assert e is self.e and len(recent) == 2
            left, right = recent
            assert right["result"][0] is fine
            assert left["stop"] == right["start"] and right["stop"] == fine["time"]
            assert left["start"] == staged["end"]
            assert left["before"] == staged["state"]
            assert left["result"][0]["state"].astype("<f8").tobytes() == right["before"]
            assert right["stop"]-left["start"] == dt
            # Runtime invokes _close only after its boundary-width gate passes.
            # Stage without changing that return value; caller may still refuse.
            staged["work"] = add_receipts(staged["work"], fine_work)
            staged["impulses"] = interval._impulse_add(staged["impulses"], fine_impulse)
            for row in (left, right):
                after = row["result"][0]
                after_domain = plain_domain(after["domain"])
                if row["support"] != row["after_support"] or row["domain"] != after_domain:
                    width = row["stop"]-row["start"]
                    staged["events"].append(dict(start_s=row["start"], end_s=row["stop"],
                        width_s=width, bracket_within_1us=width <= 1e-6,
                        before_support=row["support"], after_support=row["after_support"],
                        before_domain=row["domain"], after_domain=after_domain,
                        predecessor_base64=base64.b64encode(row["before"]).decode(),
                        successor_base64=base64.b64encode(after["state"].astype("<f8").tobytes()).decode(),
                        available_work_j=row["supply"], accepted_work=row["result"][1]))
            staged["pieces"] += 2
            staged["end"] = fine["time"]
            staged["state"] = fine["state"].astype("<f8").tobytes()
            self.observer_seconds += time.perf_counter()-t
            return accepted

        interval._one_step, interval._close, mj.mj_step = observed_step, observed_close, observed_native
        try:
            successor = self.e.advance(before, None, 100, self.supply)
            returned = (successor.positive_motor_work_j, successor.signed_motor_work_j,
                        successor.max_surface_travel_m, successor.motor_braking_work_j,
                        successor.bearing_dissipation_j, successor.self_bearing_dissipation_j)
            assert tuple(staged["work"]) == returned
            assert staged["end"] == float(self.d.time) == begin+.0001
            assert staged["state"] == successor.state[32:] == primary(self.e)
            assert abs(float(self.d.time)-nominal_us/1e6) <= (nominal_us//100+1)*math.ulp(.5)
            accumulated_impulses = interval._impulse_add(self.impulses, staged["impulses"])
            accumulated_work = add_receipts(self.work, returned)
            supply = self.initial_supply-accumulated_work[0]
            assert math.isfinite(supply) and supply >= 0
            support = contact_support(self.e)
            last_accepted = packed_state(self.e)
        except Exception as error:
            # Runtime rollback proof is separate; retain exact status on any
            # physical or diagnostic refusal, without rewriting the body here.
            self.failed_interval = dict(type=type(error).__name__, error=str(error),
                traceback=traceback.format_exc(limit=8),
                predecessor_base64=base64.b64encode(before).decode(),
                primary_rollback_exact=self.e._capture() == before,
                uncommitted_fine_pieces=staged["pieces"])
            raise
        finally:
            interval._one_step, interval._close, mj.mj_step = one_step, close, native_step
            self.interval_seconds += (time.perf_counter()-started
                -(self.native_seconds-native_before)-(self.observer_seconds-observer_before))
        self.impulses, self.work, self.supply = accumulated_impulses, accumulated_work, supply
        self.events.extend(staged["events"])
        self.support, self.last_accepted = support, last_accepted
        self.accepted += staged["pieces"]
        return successor

    def snapshot(self):
        started = time.perf_counter()
        saved = primary(self.e)
        for row, geom in enumerate(self.geom):
            mj.mj_objectVelocity(self.m, self.d, mj.mjtObj.mjOBJ_GEOM,
                                 int(geom), self.velocity[row], 0)
        sensory = {label: finite([self.d.sensordata[s] for s in addresses]).copy()
                   for label, (_, addresses) in self.sensor_groups.items()}
        feedback = self.e._observation().self_feedback
        assert feedback is not None
        result = dict(position=self.d.geom_xpos[self.geom].copy(),
            rotation=self.d.geom_xmat[self.geom].reshape(-1, 3, 3).copy(),
            velocity=self.velocity.copy(), sensors=sensory, contacts=feedback.contacts)
        assert primary(self.e) == saved, "sample observer changed integration state"
        self.observer_seconds += time.perf_counter()-started
        return result

    def record(self, include_events=False):
        raw = primary(self.e)
        valid = bool(np.isfinite(np.frombuffer(raw, dtype="<f8")).all())
        clock = float(self.d.time)
        value = dict(h_us=self.h_us, native_call_ceiling=self.ceiling,
            time_s=clock if math.isfinite(clock) else None, native_dt_s=float(self.m.opt.timestep),
            unpublished_clock_repr=repr(clock), integration_values_finite=valid,
            unpublished_integration_base64=base64.b64encode(raw).decode() if not valid else None,
            state_base64=base64.b64encode(self.e._header+raw).decode() if valid else None,
            last_accepted_state_base64=self.last_accepted, calls=self.calls,
            accepted_fine_pieces=self.accepted, numerical_refusals=self.refused,
            work=self.work, remaining_supply_j=self.supply, support=self.support,
            impulses=[dict(pair=k, impulse_ns=v[0].tolist(),
                intrinsic_couple_impulse_nms=v[1].tolist(),
                force_path_ns=v[2], intrinsic_couple_path_nms=v[3])
                for k, v in sorted(self.impulses.items())],
            native_step_seconds=self.native_seconds, interval_wrapper_seconds=self.interval_seconds,
            observation_seconds=self.observer_seconds, event_count=len(self.events))
        if include_events:
            value.update(events=self.events, endpoints=self.endpoints,
                         last_attempt=self.last_attempt, failed_interval=self.failed_interval)
        return value


class Errors:
    """Bounded channelwise measurement summary, with no action authority."""
    def __init__(self):
        self.groups = {}
        self.first_failure = self.worst_failure = None
        self.worst_ratio = 0.
        self.unresolved_touch = dict(samples=0, first=None, last=None)
        self.matched_touch_points = self.empty_touch_samples = 0
        self.couple_impulse = {}

    def add(self, label, names, errors, limits, references, us):
        errors, limits, references = finite(errors), finite(limits), finite(references)
        assert errors.shape == limits.shape == references.shape == (len(names),)
        assert len(names) and np.all(limits > 0) and np.all(errors >= 0)
        ratios = finite(errors / limits)
        group = self.groups.setdefault(label, {})
        for name, error, allowed, reference, measured_ratio in zip(names, errors, limits, references, ratios):
            ratio = float(measured_ratio)
            old = group.get(name)
            if old is None or ratio > old["ratio"]:
                group[name] = dict(time_us=us, error=float(error), allowed=float(allowed),
                    reference=float(reference), ratio=ratio)
            if ratio > 1 and self.first_failure is None:
                self.first_failure = dict(metric=label, channel=name, time_us=us)
            if ratio > self.worst_ratio:
                self.worst_ratio = ratio
                self.worst_failure = dict(metric=label, channel=name, time_us=us, ratio=ratio)

    def vector(self, label, names, a, b, absolute, relative, us):
        a, b = finite(a), finite(b)
        ref = np.linalg.norm(b, axis=1)
        self.add(label, names, np.linalg.norm(a-b, axis=1),
                 absolute+relative*ref, ref, us)

    def compare(self, a, b, sa, sb, us):
        names = a.geom_labels
        assert names == b.geom_labels
        trace = np.einsum("ijk,ijk->i", sa["rotation"], sb["rotation"])
        angles = finite(np.arccos(np.clip((trace-1)/2, -1, 1)))
        surface = np.linalg.norm(sa["position"]-sb["position"], axis=1)
        surface += 2*a.m.geom_rbound[a.geom]*np.sin(angles/2)
        self.add("surface_position_m", names, surface, np.full(len(names), .0001),
                 np.zeros(len(names)), us)
        self.add("orientation_rad", names, angles, np.full(len(names), ANGLE),
                 np.zeros(len(names)), us)
        self.vector("linear_rate_m_s", names, sa["velocity"][:, 3:], sb["velocity"][:, 3:], .001, .001, us)
        self.vector("angular_rate_rad_s", names, sa["velocity"][:, :3], sb["velocity"][:, :3], .01, .001, us)
        for label, (labels, _) in a.sensor_groups.items():
            absolute = ANGLE if label == "proprioceptive_angle_rad" else .01
            relative = 0 if label == "proprioceptive_angle_rad" else .001
            self.vector(label, labels, sa["sensors"][label], sb["sensors"][label], absolute, relative, us)
        for i, label in ((0,"positive_motor_work_j"), (1,"signed_motor_work_j"),
                         (3,"braking_work_j"), (4,"bearing_work_j"), (5,"self_bearing_work_j")):
            gross = b.work[0]+b.work[3] if i == 1 else abs(b.work[i])
            self.add(label, [label], [abs(a.work[i]-b.work[i])], [1e-6+.001*gross], [gross], us)
        for pair in sorted(a.impulses.keys() | b.impulses.keys()):
            av = a.impulses.get(pair, [np.zeros(3), np.zeros(3), 0., 0.])
            bv = b.impulses.get(pair, [np.zeros(3), np.zeros(3), 0., 0.])
            key = "|".join(a.e.geom_names[i] for i in pair)
            self.add("contact_impulse_ns", [key], [np.linalg.norm(av[0]-bv[0])],
                     [1e-6+.001*bv[2]], [bv[2]], us)
            error = float(finite(np.linalg.norm(av[1]-bv[1])))
            prior = self.couple_impulse.get(key)
            if prior is None or error > prior["error_nms"]:
                self.couple_impulse[key] = dict(error_nms=error, time_us=us,
                    qualified=False, reason="no ratified separate intrinsic-couple impulse ceiling")
        if not sa["contacts"] and not sb["contacts"]:
            self.empty_touch_samples += 1
            return
        touch = tactile_limits(sa["contacts"], sb["contacts"])
        self.matched_touch_points += touch["matched_points"]
        for source, metric in (("force_n", "local_contact_force_n"), ("couple_nm", "local_contact_couple_nm")):
            for row in touch.get(source, {}).get("channels", []):
                self.add(metric, [row["label"]], [row["disagreement"]], [row["allowed"]],
                         [row["reference_magnitude"]], us)
        if not touch["complete"]:
            self.unresolved_touch["samples"] += 1
            record = dict(time_us=us, reasons=touch["unresolved"],
                left=[asdict(c) for c in sa["contacts"]],
                right=[asdict(c) for c in sb["contacts"]])
            if self.unresolved_touch["first"] is None:
                self.unresolved_touch["first"] = record
            self.unresolved_touch["last"] = record

    def result(self):
        groups = {label:dict(status="PASS" if all(r["ratio"] <= 1 for r in rows.values()) else "FAIL",
                             channels=rows) for label, rows in self.groups.items()}
        groups["local_tactile_correspondence"] = dict(
            status="UNRESOLVED" if self.unresolved_touch["samples"] else "PASS",
            **self.unresolved_touch, matched_points=self.matched_touch_points,
            both_empty_samples=self.empty_touch_samples)
        groups["intrinsic_couple_impulse"] = dict(status="UNQUALIFIED", pairs=self.couple_impulse)
        return groups


def observer_control(case):
    proof = read(PROOF)
    joint = read(JOINT)
    old = next(c for c in joint["cases"] if c["width_us"] == .25)
    raw = base64.b64decode(old["endpoint_state_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == proof["raw_predecessor_sha256"]
    case.e._restore(case.e._header+raw)
    case.initial_supply = case.supply = old["remaining_supply_j"]
    case.last_accepted = case.initial = packed_state(case.e)
    case.support = contact_support(case.e)
    result = case.advance_to(1800)
    expected = proof["runs"][0]
    assert hashlib.sha256(case.v1_header+result.state[32:]).hexdigest() == expected["state_sha256"]
    assert result.positive_motor_work_j == expected["positive_work_j"]
    assert result.signed_motor_work_j == expected["signed_work_j"]
    assert result.motor_braking_work_j == expected["braking_work_j"]
    assert result.bearing_dissipation_j == expected["bearing_work_j"]
    assert case.calls == expected["native_calls"] == 8 and case.accepted == 4
    return dict(archived_physical_successor_exact=True, accepted_pieces=case.accepted,
                calls=case.calls, archived_v1_state_sha256=expected["state_sha256"],
                current_state_sha256=hashlib.sha256(result.state).hexdigest())


def main():
    assert mj.mj_versionString() == mj.__version__ == VERSION
    assert interval.INTERVAL_ABI == 3 and interval.INTERVAL_LAW == "midpoint-dyadic-accuracy-v2"
    controls = archived_controls()
    cases, errors = [], Errors()
    control_result = control_failure_state = failure = first_failure_states = None
    control_calls = 0
    completed_us = 0
    emitted_events = [0, 0]
    started = time.perf_counter()
    try:
        control_case = Trajectory(100, controls[100])
        try:
            control_result = observer_control(control_case)
        except Exception:
            control_failure_state = control_case.record(include_events=True)
            raise
        finally:
            control_calls = control_case.calls
            del control_case
        cases = [Trajectory(h, controls[h]) for h in (100, 50)]
        assert base64.b64decode(cases[0].initial)[32:] == base64.b64decode(cases[1].initial)[32:]
        for us in range(100, 500001, 100):
            if us == 250100:
                for case in cases:
                    case.d.ctrl[case.motor] = 0.
                    saved = primary(case.e)
                    mj.mj_forward(case.m, case.d)
                    assert primary(case.e) == saved
                    case.e._check()
            for case in cases:
                case.advance_to(us)
            assert cases[0].d.time == cases[1].d.time
            errors.compare(cases[0], cases[1], cases[0].snapshot(), cases[1].snapshot(), us)
            completed_us = us
            wide = any(not event["bracket_within_1us"]
                       for i, case in enumerate(cases) for event in case.events[emitted_events[i]:])
            if errors.first_failure is not None or errors.unresolved_touch["samples"] or wide:
                first_failure_states = [case.record(include_events=True) for case in cases]
                failure = dict(type="AccuracyGateFailure", error="first sampled qualification failure",
                    metric=errors.first_failure, unresolved_touch=bool(errors.unresolved_touch["samples"]),
                    wide_observed_event=wide, time_us=us)
                break
            if us in (250000, 500000):
                for case in cases:
                    case.endpoints.append(case.record())
            if us % 10000 == 0:
                print(json.dumps(encode(dict(event="accepted_trajectory_progress", time_us=us,
                    cases=[case.record() for case in cases],
                    event_deltas=[case.events[emitted_events[i]:] for i, case in enumerate(cases)],
                    metrics=errors.result()))), flush=True)
                emitted_events = [len(case.events) for case in cases]
    except Exception as error:
        failure = dict(type=type(error).__name__, error=str(error),
                       traceback=traceback.format_exc(limit=8),
                       last_completed_sample_us=completed_us)
    result = dict(schema=SCHEMA, version=VERSION, interval_abi=interval.INTERVAL_ABI,
        observer_control=control_result, control_failure_state=control_failure_state,
        model_sha256=controls[100]["model_sha256"],
        completed_us=completed_us, all_completed=completed_us == 500000 and failure is None,
        calls=sum(c.calls for c in cases)+control_calls,
        call_ceiling=48860, cases=[c.record(include_events=True) for c in cases],
        metrics=errors.result(), first_failure=errors.first_failure,
        first_failure_states=first_failure_states, failure=failure,
        wall_seconds=time.perf_counter()-started, maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        event_time_qualification="Observed accepted-piece brackets only; hidden crossings not excluded",
        continuum_error_enclosure=False, full_body_qualification=False,
        scope="Common-genesis zero-gravity accepted load/release trajectory; first failure stops the run. No gravity, mounted world or production qualification.")
    print(json.dumps(encode(result)), flush=True)


if __name__ == "__main__":
    main()
