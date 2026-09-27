"""Offline common-genesis load/release accuracy measurement, never body authority.

Two nominal meshes use the SAME native physical law and refusal subdivision.
Sample disagreement is not a continuum enclosure. Contact brackets are retained
for later localization; no hidden-event, real-gravity or production claim.
"""
from __future__ import annotations

import base64
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
import resource
import time

import mujoco as mj
import numpy as np

from guala_body_contact_onset import archived_controls
from guala_body_event_resolution import tactile_limits
from guala_body_joint_boundary import encode
from guala_body_load_release import engine_at
from guala_body_local_refinement import add_receipts, state_copy
from guala_body_midpoint import VERSION, subdivide_refused_step

SCHEMA = "guala.functional-body.trajectory-accuracy.v1"
ANGLE = math.radians(.01)


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
    # Native geometric constraints and physically loaded contact are distinct.
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


class Trajectory:
    def __init__(self, h_us, control):
        self.e, xml, limits = engine_at(100)
        self.m, self.d = self.e._model, self.e._data
        state = self.e.initial_state()
        old_header = hashlib.sha256(
            ("3.3.7" + repr(limits) + repr(self.e._sensory_root) + xml).encode()
        ).digest()
        assert hashlib.sha256(xml.encode()).hexdigest() == control["model_sha256"]
        assert hashlib.sha256(old_header + state[32:]).hexdigest() == control["initial_state_sha256"]
        assert np.all(self.m.opt.gravity == 0)
        self.h_us = h_us
        self.ceiling = 500000 // h_us + 642
        self.motor = self.e.actuator_names.index(control["name"])
        self.d.ctrl[self.motor] = control["phases"][0]["effort_nm"]
        mj.mj_forward(self.m, self.d)
        self.e._check()
        self.initial_supply = self.supply = control["initial_supply_j"]
        self.work = (0.,) * 6
        self.calls = self.accepted = self.refused = 0
        self.native_seconds = self.interval_seconds = self.observer_seconds = 0.
        self.impulses, self.events, self.endpoints = {}, [], []
        self.support = contact_support(self.e)
        self.last_attempt = self.failed_partition = None
        self.last_accepted = packed_state(self.e)
        self.initial = self.last_accepted
        self.original_interval = self.e._advance_interval
        self.e._advance_interval = self.call
        self.geom = np.asarray(sorted(self.e._self_geoms), dtype=int)
        assert len(self.geom)
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
            assert ids, "required feedback channel absent: " + label
            self.sensor_groups[label] = (
                [self.e._sensor_names[i] for i in ids],
                [slice(int(self.m.sensor_adr[i]), int(self.m.sensor_adr[i] + self.m.sensor_dim[i])) for i in ids],
            )

    def call(self, engine, effort, steps, budget):
        assert engine is self.e and steps == 1
        if self.calls >= self.ceiling:
            raise RuntimeError("bounded trajectory native-call allowance exhausted")
        self.calls += 1
        begin, dt = float(self.d.time), float(self.m.opt.timestep)
        before = primary(self.e)
        self.last_attempt = dict(start_s=begin, end_s=begin + dt, dt=dt,
            predecessor_base64=base64.b64encode(before).decode(), available_work_j=budget)
        step = mj.mj_step
        pending = None

        def observed_step(m, d):
            nonlocal pending
            t = time.perf_counter()
            try:
                step(m, d)
            finally:
                self.native_seconds += time.perf_counter() - t
            self.last_attempt["native_step_completed"] = True
            t = time.perf_counter()
            saved = primary(self.e)
            # Geometry/contact rows still describe the converged midpoint here;
            # the enclosing interval has not run endpoint kinematics/collision.
            totals = {}
            for i, c in enumerate(d.contact):
                if c.efc_address < 0:
                    continue
                force = np.empty(6)
                mj.mj_contactForce(m, d, i, force)
                force = finite(force)
                pair = tuple(int(x) for x in c.geom)
                rotation = finite(c.frame).reshape(3, 3).T
                world_force = finite(rotation @ force[:3])
                world_couple = finite(rotation @ force[3:])
                if pair[0] > pair[1]:
                    pair = pair[::-1]
                    world_force, world_couple = -world_force, -world_couple
                value = totals.setdefault(pair, [np.zeros(3), np.zeros(3)])
                value[0] = finite(value[0] + world_force)
                value[1] = finite(value[1] + world_couple)
            assert primary(self.e) == saved, "midpoint observer changed integration state"
            pending = totals
            self.observer_seconds += time.perf_counter() - t

        mj.mj_step = observed_step
        native_before, observer_before = self.native_seconds, self.observer_seconds
        started = time.perf_counter()
        try:
            work = self.original_interval(engine, effort, steps, budget)
        except mj.FatalError as error:
            self.refused += 1
            self.last_attempt.update(native_refusal=str(error),
                primary_rollback_byte_exact=primary(self.e) == before)
            assert self.last_attempt["primary_rollback_byte_exact"]
            raise
        finally:
            mj.mj_step = step
            elapsed = time.perf_counter() - started
            self.interval_seconds += elapsed - (self.native_seconds-native_before) - (self.observer_seconds-observer_before)
        assert pending is not None and float(self.d.time) == begin + dt
        assert np.isfinite(work).all()
        # Stage the whole observer receipt. A derived-observation failure must
        # not leave impulse history ahead of accepted work or primary state.
        self.last_attempt["interval_work_returned"] = list(work)
        started = time.perf_counter()
        try:
            staged = {}
            for pair, (force, couple) in pending.items():
                value = self.impulses.get(pair, [np.zeros(3), np.zeros(3), 0., 0.])
                staged[pair] = [
                    finite(value[0] + dt * force),
                    finite(value[1] + dt * couple),
                    float(finite(value[2] + dt * np.linalg.norm(force))),
                    float(finite(value[3] + dt * np.linalg.norm(couple))),
                ]
            saved = primary(self.e)
            mj.mj_forward(self.m, self.d)
            assert primary(self.e) == saved, "endpoint observation changed integration state"
            self.e._check()
            support = contact_support(self.e)
            event = None
            if support != self.support:
                event = dict(start_s=begin, end_s=float(self.d.time),
                    width_s=dt, bracket_within_1us=dt <= 1e-6,
                    before_support=self.support, after_support=support,
                    predecessor_base64=base64.b64encode(before).decode(),
                    successor_base64=base64.b64encode(saved).decode(),
                    available_work_j=budget, accepted_work=work)
            accepted_state = packed_state(self.e)
        finally:
            self.observer_seconds += time.perf_counter() - started
        self.impulses.update(staged)
        if event is not None:
            self.events.append(event)
        self.support = support
        self.last_accepted = accepted_state
        self.accepted += 1
        self.last_attempt["observer_receipt_committed"] = True
        return work

    def advance_to(self, stop_us):
        # Integer-derived endpoints avoid accumulating a different clock drift
        # for each mesh. This is a test schedule, not a body/cognition timer.
        for us in range(stop_us - 100 + self.h_us, stop_us + 1, self.h_us):
            stop = us / 1_000_000
            begin = float(self.d.time)
            self.m.opt.timestep = stop - begin
            assert begin < stop and begin + self.m.opt.timestep == stop
            self.failed_partition = None
            try:
                work = self.e._advance_interval(self.e, self.d.ctrl.copy(), 1, self.supply)
            except mj.FatalError as error:
                if "midpoint residual did not converge" not in str(error):
                    raise
                partition = subdivide_refused_step(self.e, stop, self.supply,
                    dict(self.last_attempt), min(5642, self.ceiling-self.calls))
                if not partition["completed"]:
                    self.failed_partition = partition
                    self.work = add_receipts(self.work, partition["unpublished_accepted_work_receipt"])
                    self.supply = partition["unpublished_remaining_supply_j"]
                    raise RuntimeError("trajectory subdivision: " + partition["failure"])
                work = tuple(partition["work_receipt"])
            self.work = add_receipts(self.work, work)
            self.supply = self.initial_supply - self.work[0]
            assert np.isfinite(self.supply) and self.supply >= 0
        assert self.d.time == stop_us / 1_000_000

    def snapshot(self):
        started = time.perf_counter()
        saved = primary(self.e)
        for row, geom in enumerate(self.geom):
            mj.mj_objectVelocity(self.m, self.d, mj.mjtObj.mjOBJ_GEOM,
                                 int(geom), self.velocity[row], 0)
        sensory = {
            label: finite([self.d.sensordata[s] for s in addresses]).copy()
            for label, (_, addresses) in self.sensor_groups.items()
        }
        feedback = self.e._observation().self_feedback
        assert feedback is not None
        result = dict(position=self.d.geom_xpos[self.geom].copy(),
            rotation=self.d.geom_xmat[self.geom].reshape(-1, 3, 3).copy(),
            velocity=self.velocity.copy(), sensors=sensory, contacts=feedback.contacts)
        assert primary(self.e) == saved, "sample observer changed integration state"
        self.observer_seconds += time.perf_counter() - started
        return result

    def record(self, include_events=False):
        # A refusal can leave nonfinite unpublished scratch. Preserve its raw
        # bytes rather than calling _capture() and losing the original failure.
        raw = primary(self.e)
        valid = bool(np.isfinite(np.frombuffer(raw, dtype="<f8")).all())
        clock = float(self.d.time)
        value = dict(h_us=self.h_us, native_call_ceiling=self.ceiling,
            time_s=clock if math.isfinite(clock) else None,
            native_dt_s=float(self.m.opt.timestep),
            unpublished_clock_repr=repr(clock),
            integration_values_finite=valid,
            unpublished_integration_base64=base64.b64encode(raw).decode() if not valid else None,
            state_base64=base64.b64encode(self.e._header+raw).decode() if valid else None,
            last_accepted_state_base64=self.last_accepted, calls=self.calls,
            accepted=self.accepted, refused=self.refused, work=self.work,
            remaining_supply_j=self.supply, support=self.support,
            impulses=[dict(pair=k, impulse_ns=v[0].tolist(),
                intrinsic_couple_impulse_nms=v[1].tolist(),
                force_path_ns=v[2], intrinsic_couple_path_nms=v[3])
                for k, v in sorted(self.impulses.items())],
            native_step_seconds=self.native_seconds,
            interval_wrapper_seconds=self.interval_seconds,
            observation_seconds=self.observer_seconds,
            event_count=len(self.events))
        if include_events:
            value.update(events=self.events, endpoints=self.endpoints,
                         last_attempt=self.last_attempt, failed_partition=self.failed_partition)
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


def main():
    assert mj.mj_versionString() == mj.__version__ == VERSION
    control = archived_controls()[100]
    cases = [Trajectory(h, control) for h in (100, 50)]
    assert cases[0].initial == cases[1].initial
    errors = Errors()
    first_failure_states = worst_failure_states = failure = None
    completed_us = 0
    emitted_events = [0, 0]
    started = time.perf_counter()
    try:
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
            sa, sb = (case.snapshot() for case in cases)
            old_ratio = errors.worst_ratio
            errors.compare(cases[0], cases[1], sa, sb, us)
            if errors.first_failure is not None and first_failure_states is None:
                first_failure_states = [case.record() for case in cases]
            if errors.worst_ratio > old_ratio:
                worst_failure_states = [case.record() for case in cases]
            completed_us = us
            if us in (250000, 500000):
                for case in cases:
                    case.endpoints.append(case.record())
            if us % 10000 == 0:
                print(json.dumps(encode(dict(event="trajectory_progress", time_us=us,
                    cases=[case.record() for case in cases],
                    event_deltas=[case.events[emitted_events[i]:] for i, case in enumerate(cases)],
                    metrics=errors.result(),
                    first_failure=errors.first_failure, worst_failure=errors.worst_failure,
                    first_failure_states=first_failure_states,
                    worst_failure_states=worst_failure_states))), flush=True)
                emitted_events = [len(case.events) for case in cases]
    except Exception as error:
        failure = dict(type=type(error).__name__, error=str(error),
                       last_completed_sample_us=completed_us)
    result = dict(schema=SCHEMA, version=VERSION, model_sha256=control["model_sha256"],
        common_initial_state_sha256=hashlib.sha256(base64.b64decode(cases[0].initial)).hexdigest(),
        completed_us=completed_us, all_completed=completed_us == 500000 and failure is None,
        calls=sum(c.calls for c in cases), call_ceiling=16284,
        cases=[c.record(include_events=True) for c in cases], metrics=errors.result(),
        first_failure=errors.first_failure, worst_failure=errors.worst_failure,
        first_failure_states=first_failure_states, worst_failure_states=worst_failure_states,
        failure=failure, wall_seconds=time.perf_counter()-started,
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        event_time_qualification="UNQUALIFIED: endpoint support brackets only; hidden crossings not excluded",
        continuum_error_enclosure=False, full_body_qualification=False,
        scope="Common-genesis zero-gravity load/release; sampled mesh disagreement, not continuum accuracy, gravity, cold mounted world or production.")
    print(json.dumps(encode(result)), flush=True)


if __name__ == "__main__":
    main()
