"""Offline event-aligned resolution of the retained two-contact impact.

Numerical trials are unpublished scratch, not new body/world authority. The
engine still owns every force and settlement. No anatomical/coefficient change.
The bracket locates a crossing in the native one-step trial map; it is NOT a
certified continuous trajectory or general collision-detection algorithm.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
import zlib

import mujoco as mj
import guala_body_interval as interval
import numpy as np

from guala_body_coupled_step import VERSION
from guala_body_impact_resolution import BASE_US, START_US, WINDOW_US, endpoint, finite, read_control
from guala_body_joint_boundary import encode
from guala_body_load_release import engine_at
from guala_body_local_refinement import add_receipts, difference, restore, state_copy

PAIRS = (
    ("guala/right/forearm/surface", "guala/torso/surface"),
    ("guala/left/thigh/surface", "guala/left/palm/surface"),
)
BITS = sys.float_info.mant_dig
OLD = Path(__file__).resolve().parents[1] / "docs/evidence/FB-01aj-matched-impact.json"
OLD_SHA = "987c2776b6fd4fc097e140e066d44c2f80c50a0482e1710a6a580479f656c745"


def archived():
    p = json.loads(OLD.read_text())["packed_result"]
    raw = zlib.decompress(base64.b64decode(p["payload_zlib_base64"]))
    assert len(raw) == p["raw_bytes"]
    assert hashlib.sha256(raw).hexdigest() == p["raw_sha256"] == OLD_SHA
    return json.loads(raw)


class Trial:
    def __init__(self, before, h_us):
        self.engine, _, _ = engine_at(BASE_US)
        self.m, self.d = self.engine._model, self.engine._data
        self.m.opt.timestep = h_us / 1_000_000
        restore(self.engine, before)
        assert np.array_equal(state_copy(self.engine), before)
        self.effort = self.d.ctrl.copy()
        self.pairs = tuple(tuple(self.m.geom(n).id for n in pair) for pair in PAIRS)
        self.steps = int(WINDOW_US / h_us)
        self.calls = 0
        self.max_calls = self.steps + len(PAIRS) * (BITS + 3)
        self.original = mj.mj_step
        self.latest_contacts = []
        self.last_bracket = None

    def restore(self, state):
        restore(self.engine, state)
        assert np.array_equal(state_copy(self.engine), state)

    def gaps(self):
        # Capsule/box uses the very same native primitive as collision contact.
        # Cutoff is a proximity-query bound, not a contact margin or force law.
        result = []
        for a, b in self.pairs:
            kinds = {int(self.m.geom_type[a]), int(self.m.geom_type[b])}
            assert kinds == {int(mj.mjtGeom.mjGEOM_CAPSULE), int(mj.mjtGeom.mjGEOM_BOX)}
            cutoff = float(np.linalg.norm(self.d.geom_xpos[a]-self.d.geom_xpos[b])
                           + self.m.geom_rbound[a] + self.m.geom_rbound[b])
            value = mj.mj_geomDistance(self.m, self.d, a, b, cutoff, None)
            assert math.isfinite(value) and value < cutoff
            result.append(float(value))
        return result

    def observe(self, model, data):
        assert model is self.m and data is self.d
        self.original(model, data)
        rows = []
        for index in range(data.ncon):
            contact = data.contact[index]
            wrench = np.empty(6)
            mj.mj_contactForce(model, data, index, wrench)
            finite(wrench)
            if not np.any(wrench):
                continue
            key = "|".join(model.geom(int(g)).name for g in contact.geom)
            rotation = finite(contact.frame.reshape(3, 3).T)
            # Preserve native point order and predecessor addition grouping.
            rows.append((key, dict(
                impulse_world_ns=finite(rotation @ wrench[:3]) * model.opt.timestep,
                couple_impulse_world_nms=finite(rotation @ wrench[3:]) * model.opt.timestep,
                min_separation_m=min(0., float(finite(contact.dist))))))
        self.latest_contacts = rows

    def advance(self, dt, supply):
        assert math.isfinite(dt) and dt > 0 and self.d.time + dt > self.d.time
        self.calls += 1
        assert self.calls <= self.max_calls, "bounded numerical trial calls exhausted"
        self.m.opt.timestep = dt
        work = self.engine._advance_interval(self.engine, self.effort, 1, supply)
        assert np.isfinite(work).all()
        return dict(state=state_copy(self.engine), work=work,
                    contacts=self.latest_contacts, gaps=self.gaps(), dt=dt,
                    end=float(self.d.time))

    def bracket(self, before, start, end, pair, gap_start, supply):
        # Absolute native clock coordinates define the finite binary64 lattice.
        assert math.frexp(start)[1] == math.frexp(end)[1]
        lo, hi, low_gap = start, end, gap_start
        self.restore(before)
        upper = self.advance(hi-start, supply)
        assert low_gap >= 0 and upper["gaps"][pair] < 0
        count = 0
        self.last_bracket = dict(pair=list(PAIRS[pair]), start_s=start, lo_s=lo, hi_s=hi,
                                 low_gap_m=low_gap, high_gap_m=upper["gaps"][pair], count=count)
        while math.nextafter(lo, math.inf) < hi:
            count += 1
            assert count <= BITS, "onset did not reach adjacent representable times"
            mid = lo + (hi-lo)/2
            assert lo < mid < hi
            self.restore(before)
            trial = self.advance(mid-start, supply)
            assert trial["end"] == mid
            if trial["gaps"][pair] < 0:
                hi, upper = mid, trial
            else:
                lo, low_gap = mid, trial["gaps"][pair]
            self.last_bracket.update(lo_s=lo, hi_s=hi, low_gap_m=low_gap,
                                     high_gap_m=upper["gaps"][pair], count=count)
        return upper, dict(pair=list(PAIRS[pair]), separated_time_s=lo,
            contact_time_s=hi, separated_gap_m=low_gap, contact_gap_m=upper["gaps"][pair],
            time_width_s=hi-lo, bisections=count)


def merge_contacts(total, update):
    for key, row in update:
        target = total.setdefault(key, dict(impulse_world_ns=np.zeros(3),
            couple_impulse_world_nms=np.zeros(3), min_separation_m=0.))
        for field in ("impulse_world_ns", "couple_impulse_world_nms"):
            target[field] += finite(row[field])
            finite(target[field])
        target["min_separation_m"] = min(target["min_separation_m"], row["min_separation_m"])
        for field in ("force_path_ns", "couple_path_nms"):
            if field in row:
                target[field] = float(finite(target.get(field, 0.) + row[field]))


def run(before, supply, h_us, aligned, *, trial_class=Trial):
    trial = trial_class(before, h_us)
    d = trial.d
    contacts, events = {}, []
    work = (0.,)*6
    accepted = 0
    before_piece, gap_start = before, None
    original = mj.mj_step
    started = time.perf_counter()
    try:
        mj.mj_step = trial.observe
        for _ in range(trial.steps):
            dt = h_us / 1_000_000
            target = float(d.time + dt)
            while True:
                before_piece = state_copy(trial.engine)
                start, gap_start = float(d.time), trial.gaps()
                proposal = trial.advance(dt, supply-work[0])
                crossings = [i for i,(a,b) in enumerate(zip(gap_start,proposal["gaps"]))
                             if a >= 0 and b < 0]
                selected = proposal
                if aligned and crossings:
                    assert len(crossings) == 1, "simultaneous onsets outside this witness"
                    assert len(events) < len(PAIRS), "unexpected repeated onset"
                    i = crossings[0]
                    selected, event = trial.bracket(before_piece,start,proposal["end"],i,
                                                   gap_start[i],supply-work[0])
                    events.append(event)
                    trial.restore(selected["state"])
                accepted += 1
                assert accepted <= trial.steps+len(PAIRS)
                work = add_receipts(work,selected["work"])
                assert work[0] <= supply
                merge_contacts(contacts,selected["contacts"])
                if d.time == target:
                    break
                assert start < d.time < target
                dt = target-float(d.time)
        if aligned:
            assert len(events) == len(PAIRS)
            assert {tuple(e["pair"]) for e in events} == set(PAIRS)
    except Exception as error:
        # Diagnostic-only evidence. This is NOT an admitted body successor.
        print(json.dumps(encode(dict(event="failed_trial", h_us=h_us, aligned=aligned,
            error_type=type(error).__name__, error=str(error),
            native_time_repr=repr(float(d.time)), calls=trial.calls, accepted_steps=accepted,
            accepted_work=list(work), accepted_events=events, last_start_gaps=gap_start,
            bracket_scratch=trial.last_bracket,
            before_piece_sha256=hashlib.sha256(before_piece.astype("<f8").tobytes()).hexdigest(),
            before_piece_base64=base64.b64encode(before_piece.astype("<f8").tobytes()).decode()
        )), sort_keys=True), flush=True)
        raise
    finally:
        mj.mj_step = original
    sample = endpoint(trial.engine)
    state = state_copy(trial.engine)
    sensors = finite(trial.d.sensordata.copy())
    rows = {key:{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in row.items()}
            for key,row in contacts.items()}
    return (sample,state,sensors),dict(h_us=h_us,aligned=aligned,work=list(work),
        contacts=rows,events=events,native_calls=trial.calls,accepted_steps=accepted,
        internal_state_sha256=hashlib.sha256(state.astype("<f8").tobytes()).hexdigest(),
        internal_state_bytes=state.nbytes,elapsed_s=time.perf_counter()-started)



class AccuracyTrial(Trial):
    """Observation only: selected substeps carry their own gross impulse path."""
    def observe(self, model, data):
        super().observe(model, data)
        totals = {}
        for key, row in self.latest_contacts:
            values = totals.setdefault(key, [np.zeros(3), np.zeros(3)])
            values[0] += row["impulse_world_ns"]
            values[1] += row["couple_impulse_world_nms"]
        # One path increment for the pair resultant, not one duplicated copy
        # per contact point. Pointwise tactile comparisons remain separate.
        for key, row in self.latest_contacts:
            values = totals.pop(key, None)
            if values is not None:
                row["force_path_ns"] = float(finite(np.linalg.norm(values[0])))
                row["couple_path_nms"] = float(finite(np.linalg.norm(values[1])))


def measure_limit(errors, limits, labels, references=None):
    errors, limits = finite(np.asarray(errors)), finite(np.asarray(limits))
    assert errors.shape == limits.shape == (len(labels),) and len(labels)
    assert np.all(errors >= 0) and np.all(limits > 0)
    if references is not None:
        references = finite(np.asarray(references))
        assert references.shape == errors.shape and np.all(references >= 0)
    ratios = finite(errors / limits)
    i = int(np.argmax(ratios))
    channels = []
    for j, label in enumerate(labels):
        channel = dict(label=label, disagreement=float(errors[j]),
                       allowed=float(limits[j]), ratio=float(ratios[j]),
                       passed=bool(errors[j] <= limits[j]))
        if references is not None:
            channel["reference_magnitude"] = float(references[j])
        channels.append(channel)
    return dict(passed=bool(np.all(errors <= limits)), count=len(labels),
                maximum_disagreement=float(np.max(errors)),
                worst_label=labels[i], disagreement=float(errors[i]),
                allowed=float(limits[i]), ratio=float(ratios[i]),
                channels=channels)


def vector_limit(a, b, absolute, relative, labels):
    a, b = finite(np.asarray(a)), finite(np.asarray(b))
    assert a.shape == b.shape and a.ndim == 2 and a.shape[0] == len(labels)
    reference = np.linalg.norm(b, axis=1)
    return measure_limit(np.linalg.norm(a-b, axis=1),
                         absolute + relative*reference, labels, reference)


def tactile_limits(a, b):
    # Compare the same physical point loads, independent of exact-coincident
    # solver-row splitting. Distinct nearby points are never merged.
    groups = {}
    for side, contacts in enumerate((a, b)):
        rows = ((p.surface, p.position_m, p.force_n, p.couple_nm) for p in contacts)
        for surface, position, force, couple in interval._contact_resultants(rows):
            groups.setdefault(surface, [[], []])[side].append((position, force, couple))
    paired, unresolved = [], []
    for surface, (left, right) in sorted(groups.items()):
        if not left or len(left) != len(right):
            unresolved.append(dict(surface=surface, reason="point count changed",
                                   counts=[len(left), len(right)]))
            continue
        distance = np.linalg.norm(
            np.asarray([p[0] for p in left])[:, None, :]
            - np.asarray([p[0] for p in right])[None, :, :], axis=2)
        matches = finite(distance) <= .0001
        if not (np.all(matches.sum(axis=0) == 1) and np.all(matches.sum(axis=1) == 1)):
            unresolved.append(dict(surface=surface, reason="no unique position-bounded correspondence"))
            continue
        for i, point in enumerate(left):
            paired.append((surface, point, right[int(np.flatnonzero(matches[i])[0])]))
    if not paired:
        return dict(complete=False, unresolved=unresolved, matched_points=0)
    names = [p[0] for p in paired]
    forces = vector_limit([p[1][1] for p in paired],
                          [p[2][1] for p in paired], .01, .001, names)
    couples = vector_limit([p[1][2] for p in paired],
                           [p[2][2] for p in paired], .00001, .001, names)
    return dict(complete=not unresolved, unresolved=unresolved,
                matched_points=len(paired), force_n=forces, couple_nm=couples)


def accuracy_snapshot(engine, sample, h_us):
    # Same full integration bytes, same numerical schedule; no semantic state,
    # pose, warm-start or diagnostic successor substituted into world custody.
    engine._model.opt.timestep = h_us / 1_000_000
    restore(engine, sample[1])
    assert np.array_equal(state_copy(engine), sample[1])
    observed = engine._observation()
    assert observed.self_feedback is not None
    return observed.self_feedback


def accuracy_comparison(engine, left, right):
    coarse, a, feedback_a = left
    fine, b, feedback_b = right
    m = engine._model
    geom = np.asarray(sorted(engine._self_geoms), dtype=int)
    assert len(geom) and np.isfinite(m.geom_rbound[geom]).all()
    ca, cb = coarse[0], fine[0]
    centres = np.linalg.norm(ca[2][geom]-cb[2][geom], axis=1)
    trace = np.einsum("ijk,ijk->i", ca[3][geom], cb[3][geom])
    angle = finite(np.arccos(np.clip((trace-1)/2, -1, 1)))
    surfaces = finite(centres + 2*m.geom_rbound[geom]*np.sin(angle/2))
    names = [engine.geom_names[i] for i in geom]
    metrics = dict(
        surface_position_m=measure_limit(surfaces, np.full(len(geom), .0001), names),
        orientation_rad=measure_limit(angle, np.full(len(geom), math.radians(.01)), names),
        linear_rate_m_s=vector_limit(ca[4][geom, 3:], cb[4][geom, 3:], .001, .001, names),
        angular_rate_rad_s=vector_limit(ca[4][geom, :3], cb[4][geom, :3], .01, .001, names))
    # This already-authenticated bench is one free root followed by hinges.
    assert m.jnt_type[0] == mj.mjtJoint.mjJNT_FREE
    assert np.all(m.jnt_type[1:] == mj.mjtJoint.mjJNT_HINGE)
    dofs = list(engine._self_dofs)
    angular_dofs = [i for i in dofs if i >= 3]
    metrics["joint_and_root_angular_rate_rad_s"] = vector_limit(
        ca[1][angular_dofs, None], cb[1][angular_dofs, None], .01, .001,
        [str(i) for i in angular_dofs])
    a_sensors, b_sensors = dict(feedback_a.sensors), dict(feedback_b.sensors)
    for label, kind, absolute in (
        ("specific_force_m_s2", mj.mjtSensor.mjSENS_ACCELEROMETER, .01),
        ("gyro_rad_s", mj.mjtSensor.mjSENS_GYRO, .01)):
        indices = [i for i in engine._self_sensors if m.sensor_type[i] == kind]
        labels = [engine._sensor_names[i] for i in indices]
        metrics[label] = vector_limit([a_sensors[n] for n in labels],
                                      [b_sensors[n] for n in labels], absolute, .001, labels)
    work_names = {0:"positive_motor_work_j", 1:"signed_motor_work_j",
                  3:"braking_work_j", 4:"bearing_loss_j", 5:"self_bearing_loss_j"}
    for i, label in work_names.items():
        gross = abs(b["work"][i]) if i != 1 else b["work"][0]+b["work"][3]
        metrics[label] = measure_limit([abs(a["work"][i]-b["work"][i])],
                                      [.000001+.001*gross], [label], [gross])
    for field, path_field, label in (
        ("impulse_world_ns", "force_path_ns", "contact_impulse_ns"),
        ("couple_impulse_world_nms", "couple_path_nms", "contact_couple_impulse_nms")):
        keys = sorted(a["contacts"].keys() | b["contacts"].keys())
        errors, limits, references = [], [], []
        for key in keys:
            av = np.asarray(a["contacts"].get(key, {}).get(field, [0., 0., 0.]))
            bv = np.asarray(b["contacts"].get(key, {}).get(field, [0., 0., 0.]))
            errors.append(float(np.linalg.norm(av-bv)))
            # No approved couple-impulse ceiling: report it, do not invent one.
            if field == "impulse_world_ns":
                reference = b["contacts"].get(key, {}).get(path_field, 0.)
                references.append(reference)
                limits.append(.000001 + .001*reference)
        if field == "impulse_world_ns":
            metrics[label] = measure_limit(errors, limits, keys, references)
        else:
            metrics[label] = dict(qualified=False, reason="no separate couple-impulse requirement",
                                  differences=dict(zip(keys, errors)))
    events_a = {tuple(e["pair"]):e for e in a["events"]}
    events_b = {tuple(e["pair"]):e for e in b["events"]}
    assert events_a.keys() == events_b.keys() == set(PAIRS)
    metrics["onset_time_disagreement_s"] = measure_limit(
        [abs(events_a[k]["contact_time_s"]-events_b[k]["contact_time_s"]) for k in PAIRS],
        [1e-6]*len(PAIRS), ["|".join(k) for k in PAIRS])
    metrics["local_tactile_endpoints"] = tactile_limits(feedback_a.contacts, feedback_b.contacts)
    return dict(coarse_us=a["h_us"], fine_us=b["h_us"], metrics=metrics,
                scope="2ms common-predecessor resolution comparison; not continuum error, full250ms accuracy, full tactile history or production qualification")


def midpoint_control():
    """Authenticated old-law physical input only; NOT a runtime migration.

    A separate pinned predecessor process supplies the raw integration array.
    Its full hash and supply already exist in the immutable matched-impact
    archive. The candidate never regenerates that input under its new law and
    never rewrites a persisted NativeBody header.
    """
    from dsf_ai_service.substrate.functional_body_native import ENGINE_VERSION
    assert mj.__version__ == mj.mj_versionString() == ENGINE_VERSION == "3.3.7+guala.midpoint-step.1"
    reference = archived()
    text = sys.stdin.read(65537)
    assert len(text) <= 65536, "bounded predecessor transport exceeded"
    supplied = json.loads(text)
    assert supplied["schema"] == "guala.functional-body.raw-impact-predecessor.v1"
    raw = base64.b64decode(supplied["integration_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == reference["common_predecessor_sha256"]
    assert supplied["model_sha256"] == reference["model_sha256"]
    assert supplied["remaining_supply_j"] == reference["remaining_supply_j"]
    engine, xml, _ = engine_at(BASE_US)
    assert hashlib.sha256(xml.encode()).hexdigest() == reference["model_sha256"]
    assert len(raw) == engine._state_buffer.nbytes
    before = finite(np.frombuffer(raw, dtype="<f8").copy())
    restore(engine, before)
    assert np.array_equal(state_copy(engine), before)
    return engine, before, reference["remaining_supply_j"], reference["model_sha256"]


def accuracy_main(*, midpoint=False):
    if midpoint:
        engine, before, supply, model_sha = midpoint_control()
    else:
        assert mj.__version__ == mj.mj_versionString() == VERSION
        engine, before, supply, model_sha = read_control()
    archive = json.loads((OLD.parent/"FB-01aj-event-resolution.json").read_text())["raw_measurement"]
    raw = zlib.decompress(base64.b64decode(archive["payload_zlib_base64"]))
    assert len(raw) == archive["raw_bytes"]
    assert hashlib.sha256(raw).hexdigest() == archive["raw_sha256"] == "a498db53e982ddc8d27a281284e69426be407eeb93b1584982c862f3cf6ede30"
    old = json.loads(raw)["cases"][-1]
    rows, comparisons, prior = [], [], None
    predecessor_calls = 0 if midpoint else START_US//BASE_US
    calls = predecessor_calls
    for h_us in (1.5625, .78125, .390625, .1953125):
        sample, row = run(before, supply, h_us, True, trial_class=AccuracyTrial)
        feedback = accuracy_snapshot(engine, sample, h_us)
        endpoint_feedback = dict(sensors=[[n, list(v)] for n,v in feedback.sensors],
            contacts=[dict(surface=p.surface, position_m=list(p.position_m),
                           force_n=list(p.force_n), couple_nm=list(p.couple_nm))
                      for p in feedback.contacts])
        calls += row["native_calls"]
        if prior is None and not midpoint:
            assert row["h_us"] == old["h_us"]
            for key in old:
                if key not in ("elapsed_s", "fresh_schedule_repeat_exact", "contacts"):
                    assert row[key] == old[key], key
            assert row["contacts"].keys() == old["contacts"].keys()
            for key, fields in old["contacts"].items():
                for name, value in fields.items():
                    assert row["contacts"][key][name] == value
        row["endpoint_self_feedback"] = endpoint_feedback
        current = sample, row, feedback
        if prior is not None:
            comparisons.append(accuracy_comparison(engine, prior, current))
        rows.append(row)
        prior = current
        print(json.dumps(encode(dict(event="accuracy_case_measured", case=row,
              comparison=comparisons[-1] if comparisons else None)),sort_keys=True),flush=True)
    repeated, repeat = run(before, supply, rows[-1]["h_us"], True, trial_class=AccuracyTrial)
    repeated_feedback = accuracy_snapshot(engine, repeated, rows[-1]["h_us"])
    calls += repeat["native_calls"]
    assert all(np.array_equal(a,b) for a,b in zip(prior[0][0],repeated[0]))
    assert np.array_equal(prior[0][1],repeated[1]) and np.array_equal(prior[0][2],repeated[2])
    assert {k:v for k,v in repeat.items() if k != "elapsed_s"} == {
        k:v for k,v in rows[-1].items() if k not in ("elapsed_s", "endpoint_self_feedback")}
    assert repeated_feedback == prior[2]
    steps = [int(WINDOW_US/h) for h in (1.5625, .78125, .390625, .1953125, .1953125)]
    bound = predecessor_calls + sum(n+len(PAIRS)*(BITS+3) for n in steps)
    assert calls <= bound
    print(json.dumps(encode(dict(schema="guala.functional-body.ratified-accuracy-diagnostic.v1",
        engine_version=mj.mj_versionString(), model_sha256=model_sha,
        archived_finest_control_exact=None if midpoint else True,
        comparison_mode="midpoint-from-authenticated-old-input" if midpoint else "archived-law",
        common_predecessor_sha256=hashlib.sha256(before.astype("<f8").tobytes()).hexdigest(),
        finest_fresh_repeat_exact=True, cases=rows, comparisons=comparisons,
        charged_native_calls=calls, native_call_bound=bound,
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        full_contract_passed=False,
        scope="Ratified limits applied to local numerical resolution; full250ms/gravity/load and production qualification remain open."
    )),sort_keys=True),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--accuracy-contract", action="store_true")
    modes.add_argument("--midpoint-accuracy", action="store_true")
    args = parser.parse_args()
    if args.accuracy_contract or args.midpoint_accuracy:
        accuracy_main(midpoint=args.midpoint_accuracy)
        return
    assert mj.__version__ == mj.mj_versionString() == VERSION
    engine,before,supply,model_sha = read_control()
    old = archived()
    control,row = run(before,supply,BASE_US,False)
    previous = old["cases"][0]
    assert row["internal_state_sha256"] == previous["internal_state_sha256"]
    assert row["work"] == previous["work"]
    for pair,fields in row["contacts"].items():
        for key,value in fields.items():
            assert value == previous["contacts"][pair][key]
    assert row["contacts"].keys() == previous["contacts"].keys()
    print(json.dumps(encode(dict(event="ordinary_control_passed", case=row)),sort_keys=True),flush=True)
    rows,comparisons = [],[]
    previous_sample = None
    calls = START_US//BASE_US + row["native_calls"]
    for level in range(5):
        sample,row = run(before,supply,BASE_US/2**level,True)
        repeat,repeated = run(before,supply,BASE_US/2**level,True)
        assert all(np.array_equal(a,b) for a,b in zip(sample[0],repeat[0]))
        assert np.array_equal(sample[1],repeat[1]) and np.array_equal(sample[2],repeat[2])
        assert {k:v for k,v in row.items() if k != "elapsed_s"} == {
            k:v for k,v in repeated.items() if k != "elapsed_s"}
        row["fresh_schedule_repeat_exact"] = True
        calls += row["native_calls"]+repeated["native_calls"]
        if previous_sample is not None:
            prior_sample,prior = previous_sample
            delta = difference(engine._model,prior_sample[0][:2],sample[0][:2],
                               prior["work"],row["work"])
            delta["geom_center_m"] = float(finite(np.max(np.linalg.norm(
                sample[0][2]-prior_sample[0][2],axis=1))))
            delta["impulse_difference_ns"] = {}
            for key in row["contacts"].keys() | prior["contacts"].keys():
                a = row["contacts"].get(key, {}).get("impulse_world_ns", [0.,0.,0.])
                b = prior["contacts"].get(key, {}).get("impulse_world_ns", [0.,0.,0.])
                delta["impulse_difference_ns"][key] = float(finite(np.linalg.norm(np.asarray(a)-b)))
            comparisons.append(dict(coarse_us=prior["h_us"],fine_us=row["h_us"],**delta))
        rows.append(row)
        previous_sample = sample,row
        print(json.dumps(encode(dict(event="aligned_case_passed", case=row,
            comparison=comparisons[-1] if comparisons else None)),sort_keys=True),flush=True)
    bound = START_US//BASE_US + WINDOW_US//BASE_US + 2*sum(
        WINDOW_US*2**i//BASE_US + len(PAIRS)*(BITS+3) for i in range(5))
    assert calls <= bound
    print(json.dumps(encode(dict(schema="guala.functional-body.contact-event-resolution.v1",
        engine_version=VERSION,model_sha256=model_sha,
        common_predecessor_sha256=hashlib.sha256(before.astype("<f8").tobytes()).hexdigest(),
        ordinary_single_step_control_exact=True,cases=rows,comparisons=comparisons,
        charged_native_calls=calls,native_call_bound=bound,
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope="Two known onset pairs in retained 2ms window only. Brackets are for native trial flow, not continuous exact events, full-body accuracy, general CCD, production or thermal closure."
    )),sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
