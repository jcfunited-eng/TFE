"""Offline event-aligned resolution of the retained two-contact impact.

Numerical trials are unpublished scratch, not new body/world authority. The
engine still owns every force and settlement. No anatomical/coefficient change.
The bracket locates a crossing in the native one-step trial map; it is NOT a
certified continuous trajectory or general collision-detection algorithm.
"""
from __future__ import annotations

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


def run(before, supply, h_us, aligned):
    trial = Trial(before, h_us)
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


def main():
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
