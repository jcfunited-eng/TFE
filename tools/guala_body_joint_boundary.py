"""Offline qualification of the versioned closed hinge/slide stop boundary.

No network, world/cognitive instance or live writes. Scalar comparison is a
constitutive proof, not whole-body accuracy. Body startup comparisons retain
the previous diagnostic precision questions without selecting new tolerances.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import resource
import zlib

import mujoco as mj
import numpy as np

STOCK = "3.3.7"
CLOSED = "3.3.7+guala.closed-limits.1"
KIND = mj.mjtState.mjSTATE_INTEGRATION


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def encode(value):
    raw = canonical(value)
    return dict(raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
                payload_zlib_base64=base64.b64encode(zlib.compress(raw, 9)).decode())


def decode(path):
    packed = json.loads(path.read_bytes())
    raw = zlib.decompress(base64.b64decode(packed["payload_zlib_base64"]))
    assert len(raw) == packed["raw_bytes"]
    assert hashlib.sha256(raw).hexdigest() == packed["raw_sha256"]
    return json.loads(raw)


def integration(model, data):
    result = np.empty(mj.mj_stateSize(model, KIND))
    mj.mj_getState(model, data, result, KIND)
    return result


def scalar_cases():
    rows = []
    for joint in ("hinge", "slide"):
        for jacobian in ("dense", "sparse"):
            xml = f'''<mujoco>
              <compiler angle="radian"/>
              <option timestep=".0001" gravity="0 0 0" integrator="implicitfast"
                solver="Newton" iterations="100" tolerance="1e-10" jacobian="{jacobian}"/>
              <size memory="2M"/>
              <worldbody><body><joint type="{joint}" axis="0 0 1" limited="true"
                range="0 1" margin="0" solreflimit=".0002 1"
                solimplimit=".999 .999 .001 .5 2"/>
                <geom type="sphere" size=".1" mass="1" contype="0" conaffinity="0"/>
              </body></worldbody></mujoco>'''
            m = mj.MjModel.from_xml_string(xml)
            d = mj.MjData(m)
            mass = float(m.dof_M0[0])
            for q in (-.000001, 0., .5, 1., 1.000001):
                for v in (-.01, 0., .01):
                    for force in (-1., 0., 1.):
                        mj.mj_resetData(m, d)
                        d.qpos[0], d.qvel[0], d.qfrc_applied[0] = q, v, force
                        mj.mj_forward(m, d)
                        at_boundary = q in (0., 1.)
                        expected_rows = int(q < 0 or q > 1 or
                                            (at_boundary and mj.__version__ == CLOSED))
                        assert d.nefc == expected_rows
                        assert np.all(d.warning.number == 0)
                        row = dict(joint=joint, jacobian=jacobian, q=q, v=v, force=force,
                                   rows=int(d.nefc), acceleration=float(d.qacc[0]),
                                   reaction=float(d.qfrc_constraint[0]))
                        if d.nefc:
                            sign = 1. if q <= 0 else -1.
                            expected_force = max(0., (float(d.efc_aref[0]) -
                                sign * float(d.qacc_smooth[0])) /
                                (1. / mass + float(d.efc_R[0])))
                            assert float(d.efc_force[0]) >= 0.
                            # Floating equation identity, not a trajectory tolerance.
                            assert math.isclose(float(d.efc_force[0]), expected_force,
                                                rel_tol=1e-12, abs_tol=1e-12)
                            if at_boundary and v == 0:
                                outward = force * sign < 0.
                                if not outward:
                                    assert d.efc_force[0] == 0.
                                else:
                                    assert math.isclose(float(d.qacc[0]),
                                        .001 * force / mass, rel_tol=1e-10, abs_tol=1e-12)
                        # Every branch continues from full native integration state.
                        before = integration(m, d)
                        mj.mj_step(m, d)
                        after = integration(m, d)
                        assert np.all(d.warning.number == 0)
                        assert np.isfinite(after).all()
                        fresh = mj.MjData(m)
                        mj.mj_setState(m, fresh, before, KIND)
                        mj.mj_forward(m, fresh)
                        mj.mj_step(m, fresh)
                        fresh_after = integration(m, fresh)
                        assert np.all(fresh.warning.number == 0)
                        assert np.isfinite(fresh_after).all()
                        assert np.array_equal(after, fresh_after)
                        row["successor_sha256"] = hashlib.sha256(after.tobytes()).hexdigest()
                        rows.append(row)
    return rows


def body_startup():
    from guala_body_contact_onset import archived_controls
    from guala_body_load_release import engine_at
    from guala_body_local_refinement import difference, restore, state_copy
    controls = archived_controls()
    rows = []
    for h in (100, 50, 25):
        e, xml, limits = engine_at(h)
        c = controls[h]
        assert hashlib.sha256(xml.encode()).hexdigest() == c["model_sha256"]
        initial = e.initial_state()
        # Authenticate identical initial PHYSICAL payload, not header transplant
        # into an executing engine. This old-law record is used only for refusal.
        old_header = hashlib.sha256((STOCK + repr(limits) +
                         repr(e._sensory_root) + xml).encode()).digest()
        old_record = old_header + initial[32:]
        assert hashlib.sha256(old_record).hexdigest() == c["initial_state_sha256"]
        try:
            e._restore(old_record)
        except ValueError as error:
            assert str(error) == "body state/model mismatch"
        else:
            raise AssertionError("old-law retained bytes were silently admitted")
        command = dict(efforts=None, elapsed_us=100,
            available_work_j=c["initial_supply_j"],
            effort_updates=((e.actuator_names.index(c["name"]),
                             c["phases"][0]["effort_nm"]),))
        result = e.advance(initial, **command)
        cold, _, _ = engine_at(h)
        assert cold.advance(initial, **command) == result
        rows.append(dict(h_us=h, qpos=list(result.observation.qpos),
                         qvel=list(result.observation.qvel),
                         successor_sha256=hashlib.sha256(result.state).hexdigest(),
                         state_bytes=len(result.state), old_law_refused=True,
                         full_cold_successor_exact=True))
    e, _, _ = engine_at(100)
    e.initial_state()
    c = controls[100]
    effort = e._data.ctrl.copy()
    effort[e.actuator_names.index(c["name"])] = c["phases"][0]["effort_nm"]
    e._data.ctrl[:] = effort
    mj.mj_forward(e._model, e._data)
    initial = state_copy(e)
    errors = []
    try:
        for level in range(6):
            h = 100. / 2**level
            samples = []
            for count in (1, 2):
                e._model.opt.timestep = h / count / 1_000_000
                restore(e, initial)
                receipt = e._advance_interval(e, effort, count, c["initial_supply_j"])
                samples.append(((e._data.qpos.copy(), e._data.qvel.copy()), receipt))
            errors.append(dict(coarse_step_us=h, fine_step_us=h/2,
                **difference(e._model, samples[0][0], samples[1][0],
                             samples[0][1], samples[1][1])))
    finally:
        e._model.opt.timestep = .0001
    return dict(prefixes=rows, initial_dyadic_errors=errors,
                scope="100us startup only; impact and global accuracy NOT qualified")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stock-control", type=Path)
    args = p.parse_args()
    expected = CLOSED if args.stock_control else STOCK
    assert mj.__version__ == expected and mj.mj_versionString() == expected
    rows = scalar_cases()
    result = dict(engine_version=mj.__version__, scalar_cases=rows)
    if args.stock_control:
        control = decode(args.stock_control)
        assert control["engine_version"] == STOCK
        assert len(rows) == len(control["scalar_cases"])
        unchanged = 0
        for old, new in zip(control["scalar_cases"], rows):
            for key in ("joint", "jacobian", "q", "v", "force"):
                assert old[key] == new[key]
            if new["q"] not in (0., 1.):
                assert old == new, (old, new)
                unchanged += 1
        result["nonboundary_cases_exact"] = unchanged
        result["body_startup"] = body_startup()
    result["maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(encode(result), sort_keys=True))


if __name__ == "__main__":
    main()
