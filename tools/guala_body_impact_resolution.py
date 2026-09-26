"""Offline resolution map of the first self-impact from ONE common predecessor.

Internal integration arrays are diagnostic scratch, never published body state.
No coefficient, body authority, cognition, production tolerance or heat law changes.
Paired-step differences are indicators, not certified continuous-solution errors.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import resource
import time
import zlib

import mujoco as mj
import numpy as np

from guala_body_contact_onset import archived_controls
from guala_body_coupled_step import VERSION
from guala_body_joint_boundary import encode
from guala_body_load_release import engine_at
from guala_body_local_refinement import difference, restore, state_copy

START_US, WINDOW_US = 20000, 2000
BASE_US, LEVELS = 25, 5
ARCHIVE = Path(__file__).resolve().parents[1] / "docs/evidence/FB-01aj-coupled-motion.json"
RAW_SHA = "9d04fb192fd2a316a8e083645d36ee5b7957061759fb98c4cd7ee219456fcc67"


def finite(value):
    if not np.all(np.isfinite(value)):
        raise AssertionError("non-finite impact evidence")
    return value


def read_control():
    envelope = json.loads(ARCHIVE.read_text())["packed_result"]
    raw = zlib.decompress(base64.b64decode(envelope["payload_zlib_base64"]))
    assert len(raw) == envelope["raw_bytes"]
    assert hashlib.sha256(raw).hexdigest() == envelope["raw_sha256"] == RAW_SHA
    record = json.loads(raw)
    assert record["engine_version"] == VERSION
    prefix = next(p for p in record["motion"]["prefixes"] if p["h_us"] == BASE_US)
    sample = next(p for p in prefix["samples"] if p["elapsed_us"] == START_US)
    control = archived_controls()[BASE_US]
    engine, xml, _ = engine_at(BASE_US)
    assert hashlib.sha256(xml.encode()).hexdigest() == control["model_sha256"]
    result = engine.advance(engine.initial_state(), None, START_US, control["initial_supply_j"],
        effort_updates=((engine.actuator_names.index(control["name"]),
                         control["phases"][0]["effort_nm"]),))
    assert np.array_equal(engine._data.qpos, sample["qpos"])
    assert np.array_equal(engine._data.qvel, sample["qvel"])
    supply = control["initial_supply_j"] - result.positive_motor_work_j
    assert np.isfinite(supply) and supply >= 0
    return engine, state_copy(engine), supply, control["model_sha256"]


def endpoint(engine):
    m, d = engine._model, engine._data
    mj.mj_forward(m, d)
    engine._check()
    velocities = np.empty((m.ngeom, 6))
    for geom in range(m.ngeom):
        mj.mj_objectVelocity(m, d, mj.mjtObj.mjOBJ_GEOM, geom, velocities[geom], 0)
    return tuple(finite(a.copy()) for a in
        (d.qpos, d.qvel, d.geom_xpos, d.geom_xmat.reshape(-1, 3, 3), velocities))


def run_case(before, supply, level, capture_manifold=False):
    h_us = BASE_US / 2**level
    steps = WINDOW_US * 2**level // BASE_US
    engine, _, _ = engine_at(BASE_US)
    m, d = engine._model, engine._data
    m.opt.timestep = h_us / 1_000_000
    restore(engine, before)
    effort = d.ctrl.copy()
    original = mj.mj_step
    contacts, count = {}, 0
    manifold = []
    pair = ('guala/right/forearm/surface', 'guala/torso/surface')

    def observe(model, data):
        nonlocal count
        assert model is m and data is d
        original(model, data)
        assert not np.any(data.warning.number)
        points = []
        for index in range(data.ncon):
            contact = data.contact[index]
            wrench = np.empty(6)
            mj.mj_contactForce(model, data, index, wrench)
            finite(wrench)
            finite(contact.frame)
            finite(contact.dist)
            names = tuple(model.geom(int(g)).name for g in contact.geom)
            if capture_manifold and names == pair:
                # Same-solve geometry remains at the step's input pose here.
                # Store every point, including zero-force contacts. Do not infer
                # persistent point identity from native array indices.
                address = int(contact.efc_address)
                assert model.opt.cone == mj.mjtCone.mjCONE_PYRAMIDAL
                width = 1 if contact.dim == 1 else 2 * (int(contact.dim) - 1)
                assert address < 0 or address + width <= data.nefc
                box = int(contact.geom[1])
                local = data.geom_xmat[box].reshape(3, 3).T @ (
                    contact.pos - data.geom_xpos[box])
                points.append(dict(position_box_m=finite(local).tolist(),
                    separation_m=float(contact.dist),
                    frame_world=finite(contact.frame.copy()).tolist(),
                    wrench_contact=finite(wrench.copy()).tolist(),
                    friction=finite(contact.friction.copy()).tolist(),
                    dimension=int(contact.dim), excluded=int(contact.exclude),
                    efc_state=[] if address < 0 else
                        data.efc_state[address:address+width].tolist()))
            if not np.any(wrench):
                continue
            key = "|".join(names)
            row = contacts.setdefault(key, dict(first_us=START_US + count*h_us,
                last_us=START_US + count*h_us, impulse_world_ns=np.zeros(3),
                couple_impulse_world_nms=np.zeros(3), min_separation_m=0.))
            rotation = contact.frame.reshape(3, 3).T
            # Sum ALL points of the pair, expressed in world axes. Couple is
            # the intrinsic contact couple, NOT torque about a common origin.
            row["impulse_world_ns"] += finite(rotation @ wrench[:3]) * m.opt.timestep
            row["couple_impulse_world_nms"] += finite(rotation @ wrench[3:]) * m.opt.timestep
            finite(row["impulse_world_ns"])
            finite(row["couple_impulse_world_nms"])
            row["last_us"] = START_US + count*h_us
            row["min_separation_m"] = min(row["min_separation_m"], float(contact.dist))
        if capture_manifold:
            manifold.append([START_US + count*h_us, points])
        count += 1

    started = time.perf_counter()
    try:
        mj.mj_step = observe
        work = engine._advance_interval(engine, effort, steps, supply)
    finally:
        mj.mj_step = original
    sample = endpoint(engine)
    after = state_copy(engine)
    sensors = finite(d.sensordata.copy())
    assert count == steps
    assert np.isfinite(work).all() and work[0] <= supply

    # Fresh native model/data, same full predecessor and numerical schedule.
    # Never construct a serialized state with a substituted model header.
    cold, _, _ = engine_at(BASE_US)
    cold._model.opt.timestep = m.opt.timestep
    restore(cold, before)
    repeat = cold._advance_interval(cold, cold._data.ctrl.copy(), steps, supply)
    repeated_sample = endpoint(cold)
    assert repeat == work and np.array_equal(after, state_copy(cold))
    assert np.array_equal(sensors, cold._data.sensordata)
    assert all(np.array_equal(a, b) for a, b in zip(sample, repeated_sample))
    rows = {key: {k: v.tolist() if isinstance(v, np.ndarray) else v
                  for k, v in row.items()} for key, row in contacts.items()}
    result = dict(h_us=h_us, steps=steps, contacts=rows, work=list(work),
        internal_state_sha256=hashlib.sha256(after.astype("<f8").tobytes()).hexdigest(),
        internal_state_bytes=after.nbytes, fresh_schedule_repeat_exact=True,
        elapsed_seconds=time.perf_counter()-started)
    if capture_manifold:
        result["manifold_pair"] = list(pair)
        result["manifold_same_solve"] = manifold
    return sample, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifold', action='store_true')
    args = parser.parse_args()
    assert mj.__version__ == mj.mj_versionString() == VERSION
    engine, before, supply, model_sha = read_control()
    rows, comparisons = [], []
    previous = None
    for level in ((3, 4) if args.manifold else range(LEVELS)):
        sample, row = run_case(before, supply, level, args.manifold)
        if previous is not None:
            old_sample, old_row = previous
            delta = difference(engine._model, old_sample[:2], sample[:2],
                               old_row["work"], row["work"])
            center = finite(np.linalg.norm(sample[2]-old_sample[2], axis=1))
            speed = finite(np.linalg.norm(sample[4][:, 3:]-old_sample[4][:, 3:], axis=1))
            spin = finite(np.linalg.norm(sample[4][:, :3]-old_sample[4][:, :3], axis=1))
            # Compare rotations geometrically, not elementwise as angles.
            trace = finite(np.einsum("ijk,ijk->i", sample[3], old_sample[3]))
            angle = finite(np.arccos(np.clip((trace-1)/2, -1, 1)))
            metrics = {}
            for name, values in (("geom_center_m", center), ("geom_center_rate_m_s", speed),
                                 ("geom_angular_rate_rad_s", spin), ("geom_angle_rad", angle)):
                index = int(np.argmax(values))
                metrics[name] = dict(maximum=float(values[index]), geom=engine.geom_names[index])
            impulses = {}
            for key in old_row["contacts"].keys() | row["contacts"].keys():
                a = old_row["contacts"].get(key, {}).get("impulse_world_ns", [0., 0., 0.])
                b = row["contacts"].get(key, {}).get("impulse_world_ns", [0., 0., 0.])
                impulses[key] = float(finite(np.linalg.norm(np.asarray(b)-a)))
            comparisons.append(dict(coarse_us=old_row["h_us"], fine_us=row["h_us"],
                **delta, physical_geometry=metrics, contact_impulse_difference_ns=impulses))
        rows.append(row)
        previous = sample, row
    record = dict(schema="guala.functional-body.matched-impact-resolution.v1",
        mode="contact-manifold" if args.manifold else "resolution",
        engine_version=VERSION, model_sha256=model_sha, archived_20ms_pose_rate_exact=True,
        common_predecessor_sha256=hashlib.sha256(before.astype("<f8").tobytes()).hexdigest(),
        start_us=START_US, window_us=WINDOW_US, remaining_supply_j=supply,
        charged_native_steps=START_US//BASE_US + 2*sum(r["steps"] for r in rows),
        cases=rows, comparisons=comparisons, maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope="Common-predecessor local impact resolution only; NOT global accuracy, a production step policy, thermal accounting, or behavior.")
    print(json.dumps(encode(record), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
