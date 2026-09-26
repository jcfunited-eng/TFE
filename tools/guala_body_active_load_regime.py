"""Offline active-load numerical map for the functional-body precursor.

No runtime law, controller, learner, checkpoint or production endpoint is changed.
All cases preserve geometry, mass, force capacity, bearing drag and error limits.
Response/impedance values below are diagnostic hypotheses, NOT calibrated tissue
or accepted production laws. Eight representatives precede the optional full
128-endpoint census. Every trial begins from the same declared pristine bench.
"""
from dataclasses import replace
import argparse
import collections
import hashlib
import json
from pathlib import Path
import resource
import time
import xml.etree.ElementTree as ET

from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.substrate.functional_body_native import NativeBody
from test_functional_body_optical_sources import declaration


# Default-response controls separate time resolution from constraint response.
# The trial response 2*h is MuJoCo's documented positive-solref lower bound,
# not a statement that this is the right physical material law.
CASES = (
    ("baseline", 1000, None, None),
    ("resolution_only", 250, None, None),
    ("resolved_default_impedance", 250, .0005, None),
    ("resolved_constant_impedance", 250, .0005, .999),
    ("finer_constant_impedance", 100, .0002, .999),
    ("finest_constant_impedance", 50, .0001, .999),
    ("fixed_response_half_step", 50, .0002, .999),
    ("fixed_response_quarter_step", 25, .0002, .999),
)
REPRESENTATIVES = (
    ("guala/torso/roll/effort", -1), ("guala/torso/roll/effort", 1),
    ("guala/left/thigh/roll/effort", 1),
    ("guala/left/upper-arm/roll/effort", -1),
    ("guala/left/digit-0/proximal/flexion/effort", -1),
    ("guala/left/digit-0/proximal/flexion/effort", 1),
    ("guala/left/digit-0/distal/flexion/effort", -1),
    ("guala/left/digit-0/distal/flexion/effort", 1),
)


def run(all_motors=False, configurations=None, stream=False, constraint_work=False):
    declared = declaration()
    supply = FunctionalOrganism.genesis(identity="offline-load-budget", organism_tick=100).available_motor_work_j
    previous = json.loads((Path(__file__).resolve().parents[1] /
        "docs/evidence/FB-01aj-endpoint-loads.json").read_text())
    prior = {(r["name"], r["effort"]): r for r in previous["rows"]}
    known = json.loads((Path(__file__).resolve().parents[1] /
        "docs/evidence/FB-01aj-active-load-map.json").read_text())
    controls = {(r["configuration"], r["name"], r["effort"]): r for r in known["cases"]}
    rows = []
    cases = CASES if configurations is None else tuple(c for c in CASES if c[0] in configurations)
    for label, step_us, response, impedance in cases:
        root = ET.fromstring(declared.xml)
        if response is not None:
            for joint in root.findall(".//joint"):
                joint.set("solreflimit", f"{response:.17g} 1")
                if impedance is not None:
                    joint.set("solimplimit", f"{impedance:.17g} {impedance:.17g} .001 .5 2")
            for geom in root.findall(".//geom"):
                geom.set("solref", f"{response:.17g} 1")
                if impedance is not None:
                    geom.set("solimp", f"{impedance:.17g} {impedance:.17g} .001 .5 2")
        xml = ET.tostring(root, encoding="unicode")
        limits = replace(declared.limits, step_us=step_us, max_substeps=250000//step_us)
        engine = NativeBody(xml, limits, sensory_root=declared.sensory_root)
        state = engine.initial_state()
        model, data = engine._model, engine._data
        trials = ([(name, sign) for name in engine.actuator_names for sign in (-1, 1)]
                  if all_motors else REPRESENTATIVES)
        for name, sign in trials:
            index = engine.actuator_names.index(name)
            force = float(model.actuator_forcerange[index, 0 if sign < 0 else 1])
            start = time.perf_counter()
            row = dict(configuration=label, step_us=step_us, response_s=response,
                       impedance=impedance, model_sha256=hashlib.sha256(xml.encode()).hexdigest(),
                       name=name, effort=force)
            try:
                if constraint_work:
                    from guala_body_constraint_work import advance_with_constraint_work
                    result, work_report = advance_with_constraint_work(
                        engine, state, 250000, supply, effort_updates=((index, force),))
                    row["constraint_work"] = work_report
                else:
                    result = engine.advance(state, None, 250000, supply,
                                            effort_updates=((index, force),))
                row.update(result="accepted", time_s=result.observation.time_s,
                           positive_work_j=result.positive_motor_work_j,
                           unresolved_energy_exchange_j=result.unresolved_energy_exchange_j,
                           terminal_qpos=list(result.observation.qpos),
                           terminal_qvel=list(result.observation.qvel))
            except ValueError as error:
                row.update(result=str(error), time_s=float(data.time))
            row["terminal_max_hinge_overrun_rad"] = max(
                (max(float(model.jnt_range[j, 0]-data.qpos[model.jnt_qposadr[j]]),
                     float(data.qpos[model.jnt_qposadr[j]]-model.jnt_range[j, 1]), 0.)
                 for j in engine._limited), default=0.)
            row["terminal_max_contact_penetration_m"] = max(
                (max(0., -float(c.dist)) for c in data.contact), default=0.)
            row["wall_seconds"] = time.perf_counter()-start
            if label == "baseline":
                expected = prior[name, force]
                if (row["result"], row["time_s"]) != (expected["result"], expected["time_s"]):
                    raise AssertionError("diagnostic does not reproduce frozen predecessor")
            control = controls.get((label, name, force))
            if control is not None:
                keys = tuple(k for k in control if k != "wall_seconds")
                if any(row[k] != control[k] for k in keys):
                    raise AssertionError("diagnostic diverged from recorded control trajectory")
            rows.append(row)
            if stream:
                print(json.dumps({"load": row}, allow_nan=False), flush=True)
        print(json.dumps({"completed": label,
            "counts": dict(collections.Counter(r["result"] for r in rows if r["configuration"] == label))}),
            flush=True)
    return dict(scope="diagnostic only; accepted is numerical admissibility, not production proof",
                all_motors=all_motors, supply_j=supply, cases=rows,
                joint_names=list(engine.joint_names), qpos_addresses=list(engine.qpos_addresses),
                dof_addresses=[int(x) for x in model.jnt_dofadr],
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all-motors", action="store_true")
    parser.add_argument("--configuration", action="append", choices=[c[0] for c in CASES],
                        help="Run only named diagnostic cases; repeat for a bounded stage.")
    parser.add_argument("--jsonl", action="store_true",
                        help="Emit each measured load as completed to preserve bounded output chunks.")
    parser.add_argument("--constraint-work", action="store_true",
                        help="Compare unchanged successor with non-perturbing signed-work observation.")
    args = parser.parse_args()
    result = run(args.all_motors, args.configuration, args.jsonl, args.constraint_work)
    if args.jsonl:
        del result["cases"]  # Raw cases have already been emitted, never summarized away.
        print(json.dumps({"summary": result}, allow_nan=False), flush=True)
    else:
        print(json.dumps(result, allow_nan=False), flush=True)
