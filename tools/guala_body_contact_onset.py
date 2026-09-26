"""Read-only onset localization of the already-recorded torso-load discrepancy.

One 30ms prefix at each existing 100/50/25us resolution; no new load, coefficient,
solver, tolerance or force law. No organism/world instance, network or live state.
The unobserved successor and archived 10ms samples are exact controls. Observed
forces are solver evidence, not a new heat law or continuous-accuracy certificate.
"""
from __future__ import annotations

import base64
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import resource
import time
import zlib

import mujoco as mj
import numpy as np

from guala_body_load_release import engine_at

PREFIX_US = 30000
ARCHIVE = Path(__file__).resolve().parents[1] / "docs/evidence/FB-01aj-load-release.json"
ARCHIVE_SHA = "ee094938721e179aa40f497b2b31c8130257792e78a608b4068294b803203931"


def archived_controls():
    raw = ARCHIVE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ARCHIVE_SHA
    controls = {}
    for entry in json.loads(raw)["measurements"]:
        payload = zlib.decompress(base64.b64decode(entry["payload_zlib_base64"]))
        assert len(payload) == entry["raw_bytes"]
        assert hashlib.sha256(payload).hexdigest() == entry["raw_sha256"]
        row = json.loads(payload)
        if row["name"] == "guala/torso/roll/effort":
            controls[row["step_us"]] = row
    assert set(controls) == {25, 50, 100}
    return controls


def run_case(step_us, control):
    engine, xml, _ = engine_at(step_us)
    assert hashlib.sha256(xml.encode()).hexdigest() == control["model_sha256"]
    model, data = engine._model, engine._data
    state = engine.initial_state()
    assert hashlib.sha256(state).hexdigest() == control["initial_state_sha256"]
    index = engine.actuator_names.index(control["name"])
    command = dict(efforts=None, elapsed_us=PREFIX_US,
        available_work_j=control["initial_supply_j"],
        effort_updates=((index, control["phases"][0]["effort_nm"]),))
    ordinary = engine.advance(state, **command)
    target_samples = {r["elapsed_us"]: r for r in
        control["phases"][0]["report"]["trajectory_every_10ms"]
        if r["elapsed_us"] <= PREFIX_US}
    dofs = [model.joint(int(j)).name for j in model.dof_jntid]
    contacts = defaultdict(lambda: {"rows_seen": 0, "signed_power_integral_j": 0.,
        "absolute_power_integral_j": 0., "peak_abs_row_force": 0.})
    limits = defaultdict(lambda: {"rows_seen": 0, "signed_power_integral_j": 0.,
        "absolute_power_integral_j": 0., "peak_abs_row_force": 0.})
    samples, matched = [], []
    original = mj.mj_step
    steps = 0
    max_power_identity_error = 0.

    def observe(m, d):
        nonlocal steps, max_power_identity_error
        assert m is model and d is data
        t = steps * step_us
        position, velocity = d.qpos.copy(), d.qvel.copy()
        original(m, d)  # sole physical solve/integration, unchanged
        if t in target_samples:
            expected = target_samples[t]
            assert np.array_equal(position, expected["qpos"])
            assert np.array_equal(velocity, expected["qvel"])
            matched.append(t)
        row_powers = []
        active = set()
        for i in range(d.nefc):
            kind, ident = int(d.efc_type[i]), int(d.efc_id[i])
            force = float(d.efc_force[i])
            power = float(d.efc_vel[i]) * force
            row_powers.append(power)
            if kind == int(mj.mjtConstraint.mjCNSTR_LIMIT_JOINT):
                key = model.joint(ident).name
                table = limits
                witness = {"joint": key, "qpos": float(position[m.jnt_qposadr[ident]]),
                           "bounds_rad": m.jnt_range[ident].tolist()}
            elif kind in (int(mj.mjtConstraint.mjCNSTR_CONTACT_FRICTIONLESS),
                          int(mj.mjtConstraint.mjCNSTR_CONTACT_PYRAMIDAL),
                          int(mj.mjtConstraint.mjCNSTR_CONTACT_ELLIPTIC)):
                c = d.contact[ident]  # same-solve geometry, before refresh
                names = [model.geom(int(g)).name for g in c.geom]
                key = "|".join(names)
                table = contacts
                witness = {"geoms": names, "separation_m": float(c.dist),
                           "position_m": c.pos.tolist(), "frame": c.frame.tolist(),
                           "friction": c.friction.tolist(), "dimension": int(c.dim)}
            else:
                raise AssertionError("unmapped constraint class in pinned bench")
            if force == 0.:
                continue
            active.add(key)
            record = table[key]
            if record["rows_seen"] == 0:
                record.update(first_us=t, first_witness=witness)
            record["last_us"] = t
            record["rows_seen"] += 1
            record["signed_power_integral_j"] += power * m.opt.timestep
            record["absolute_power_integral_j"] += abs(power) * m.opt.timestep
            if abs(force) > record["peak_abs_row_force"]:
                record.update(peak_abs_row_force=abs(force), peak_us=t,
                              peak_witness=witness, peak_row_velocity=float(d.efc_vel[i]))
        error = abs(math.fsum(row_powers) - float(np.dot(velocity, d.qfrc_constraint)))
        max_power_identity_error = max(max_power_identity_error, error)
        # 100us observer grid only. Every physical substep/guard still executes.
        if t % 100 == 0:
            j = 6 + int(np.argmax(np.abs(velocity[6:])))
            samples.append(dict(time_us=t,
                max_abs_joint_rate_rad_s=float(abs(velocity[j])), fastest_joint=dofs[j],
                fastest_joint_rate_rad_s=float(velocity[j]),
                fastest_joint_constraint_force=float(d.qfrc_constraint[j]),
                active_groups=sorted(active)))
        steps += 1

    started = time.perf_counter()
    try:
        mj.mj_step = observe
        measured = engine.advance(state, **command)
    finally:
        mj.mj_step = original
    assert measured == ordinary, "read-only row observer changed physical successor"
    assert steps == PREFIX_US // step_us
    endpoint = target_samples[PREFIX_US]
    assert np.array_equal(data.qpos, endpoint["qpos"])
    assert np.array_equal(data.qvel, endpoint["qvel"])
    matched.append(PREFIX_US)
    assert matched == sorted(target_samples)
    return dict(step_us=step_us, same_successor=True, archived_samples_exact=matched,
        steps=steps, contacts=dict(contacts), limits=dict(limits), samples=samples,
        max_row_vs_dof_power_error_w=max_power_identity_error,
        observed_seconds=time.perf_counter()-started)


def main():
    controls = archived_controls()
    rows = [run_case(h, controls[h]) for h in (100, 50, 25)]
    record = dict(schema="guala.functional-body.contact-onset.v1",
        source_archive_sha256=ARCHIVE_SHA, prefix_us=PREFIX_US, measurements=rows,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        interpretation="Solver force/power localization only. Left-endpoint group power integrals are NOT heat or discrete impulse-work accounting.")
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    print(json.dumps(dict(raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
        payload_zlib_base64=base64.b64encode(zlib.compress(raw, 9)).decode())), flush=True)


if __name__ == "__main__":
    main()
