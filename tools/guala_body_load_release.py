"""Offline load/release/reverse qualification of the fixed soft-constraint trial.

This is a mechanical bench protocol, NOT an organism action script. No runtime
source, cognitive law, coefficient, safety limit or production state is changed.
The original numerical approximation permits explicit unassigned constraint
exchange; this probe does not invent a contact heat/storage law or certify one.
"""
from dataclasses import replace
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import resource
import time
import xml.etree.ElementTree as ET
import zlib

import numpy as np

from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.substrate.functional_body_native import NativeBody
from guala_body_constraint_work import advance_with_constraint_work
from test_functional_body_optical_sources import declaration


# Same declared response in ALL resolutions: no solref=2*h retuning.
RESPONSE_S, IMPEDANCE = .0002, .999
LOADS = (
    ("guala/torso/roll/effort", -1),
    ("guala/left/upper-arm/roll/effort", -1),
    ("guala/left/digit-0/distal/flexion/effort", -1),
)
PHASES = (("load", 1), ("release", 0), ("reverse", -1), ("release_again", 0))
INTERVAL_US = 250000
EVIDENCE = Path(__file__).resolve().parents[1] / "docs/evidence/FB-01aj-discrete-work.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def prior_records():
    records = {}
    for row in json.loads(EVIDENCE.read_text())["measurements"]:
        raw = zlib.decompress(base64.b64decode(row["payload_zlib_base64"]))
        if hashlib.sha256(raw).hexdigest() != row["raw_sha256"]:
            raise AssertionError("prior discrete evidence authentication failed")
        records[row["name"], row["h_us"], row["effort"]] = json.loads(raw)
    return records


def engine_at(step_us, *, integrator="implicitfast"):
    declared = declaration()
    root = ET.fromstring(declared.xml)
    if integrator not in ("implicitfast", "implicit"):
        raise ValueError("only the two declared native integration schemes are in scope")
    if integrator != "implicitfast":
        root.find("option").set("integrator", integrator)
    for tag, response_key, impedance_key in (
        ("joint", "solreflimit", "solimplimit"),
        ("geom", "solref", "solimp"),
    ):
        for element in root.findall(".//" + tag):
            element.set(response_key, f"{RESPONSE_S:.17g} 1")
            element.set(impedance_key, f"{IMPEDANCE:.17g} {IMPEDANCE:.17g} .001 .5 2")
    xml = ET.tostring(root, encoding="unicode")
    limits = replace(declared.limits, step_us=step_us,
                     max_substeps=INTERVAL_US // step_us)
    return NativeBody(xml, limits, sensory_root=declared.sensory_root), xml, limits


def run_case(name, sign, step_us, prior, *, integrator="implicitfast"):
    engine, xml, limits = engine_at(step_us, integrator=integrator)
    m, d = engine._model, engine._data
    index = engine.actuator_names.index(name)
    force = float(m.actuator_forcerange[index, 0 if sign < 0 else 1])
    state = engine.initial_state()
    supply = FunctionalOrganism.genesis(
        identity="offline-load-budget", organism_tick=100).available_motor_work_j
    row = dict(name=name, step_us=step_us, response_s=RESPONSE_S,
               impedance=IMPEDANCE, model_sha256=hashlib.sha256(xml.encode()).hexdigest(),
               initial_state_sha256=hashlib.sha256(state).hexdigest(),
               initial_supply_j=supply, phases=[],
               scope="zero-gravity bench; fixed prescribed test loads; no behavioral claim")
    if integrator == "implicit":
        reference, _, _ = engine_at(step_us)
        reference_state = reference.initial_state()
        # Compare, never transplant/rewrite, the complete initial physical
        # integration payload. Each engine keeps its own numerical-law header.
        if state[len(engine._header):] != reference_state[len(reference._header):]:
            raise AssertionError("integration method changed initial physical state")
        row.update(integrator=integrator, initial_physical_payload_exact=True,
            initial_physical_payload_sha256=hashlib.sha256(state[len(engine._header):]).hexdigest())
        del reference
    for label, multiplier in PHASES:
        effort = multiplier * force
        before = state
        started = time.perf_counter()
        try:
            result, report = advance_with_constraint_work(engine, before,
                INTERVAL_US, supply, effort_updates=((index, effort),))
        except ValueError as error:
            # Do not reset, reduce effort or retry a failed physical path.
            row["failure"] = dict(phase=label, error=str(error), native_time_s=float(d.time))
            break
        elapsed = time.perf_counter() - started
        if (label == "load" and integrator == "implicitfast"
                and report["discrete_update"] != prior[name, step_us, force]):
            raise AssertionError("first load diverged from accepted prior measurement")
        # Fresh model/data must continue the complete same native state,
        # including contacts/warm start. No pose/velocity rewriting.
        cold = NativeBody(xml, limits, sensory_root="guala/pelvis")
        started = time.perf_counter()
        cold_result = cold.advance(before, None, INTERVAL_US, supply,
                                   effort_updates=((index, effort),))
        cold_seconds = time.perf_counter() - started
        if cold_result != result:
            raise AssertionError("fresh native restart changed full mechanical successor")
        if len(result.state) != len(before):
            raise AssertionError("integration-state size grew across recurrence")
        if multiplier == 0 and (
                result.positive_motor_work_j != 0 or result.signed_motor_work_j != 0):
            raise AssertionError("zero effort produced nonzero actuator work")
        supply -= result.positive_motor_work_j
        if not math.isfinite(supply) or supply < 0:
            raise AssertionError("mechanical work was not supplied by retained bench budget")
        phase = dict(phase=label, effort_nm=effort, predecessor_sha256=hashlib.sha256(before).hexdigest(),
            successor_sha256=hashlib.sha256(result.state).hexdigest(), state_bytes=len(result.state),
            native_time_s=result.observation.time_s, remaining_supply_j=supply,
            qpos=list(result.observation.qpos), qvel=list(result.observation.qvel),
            kinetic_j=result.observation.kinetic_j, potential_j=result.observation.potential_j,
            terminal_constraint_rows=int(d.nefc),
            terminal_nonzero_constraint_force_rows=int(np.count_nonzero(d.efc_force)),
            terminal_contact_pairs=[list(c.geom_pair) for c in result.observation.contacts],
            terminal_contact_separations_m=[c.separation_m for c in result.observation.contacts],
            terminal_joint_overruns_rad=[max(0., float(m.jnt_range[j, 0]-d.qpos[m.jnt_qposadr[j]]),
                float(d.qpos[m.jnt_qposadr[j]]-m.jnt_range[j, 1])) for j in engine._limited],
            max_surface_travel_m=result.max_surface_travel_m,
            ordinary_and_observed_seconds=elapsed, cold_advance_seconds=cold_seconds,
            cold_successor_exact=True,
            first_load_prior_exact=(label == "load" and integrator == "implicitfast"),
            report=report)
        row["phases"].append(phase)
        state = result.state
    row["completed"] = len(row["phases"]) == len(PHASES)
    row["net_constraint_work_j"] = math.fsum(
        p["report"]["discrete_update"]["work_j"]["constraint"] for p in row["phases"])
    row["sum_absolute_equation_closure_j"] = math.fsum(
        p["report"]["discrete_update"]["sum_absolute_discrete_energy_closure_j"]
        for p in row["phases"])
    row["max_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    raw = canonical(row)
    return dict(name=name, step_us=step_us, integrator=integrator, completed=row["completed"],
        failure=row.get("failure"), phases=len(row["phases"]),
        net_constraint_work_j=row["net_constraint_work_j"],
        sum_absolute_equation_closure_j=row["sum_absolute_equation_closure_j"],
        raw_bytes=len(raw), raw_sha256=hashlib.sha256(raw).hexdigest(),
        payload_zlib_base64=base64.b64encode(zlib.compress(raw, 9)).decode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step-us", type=int, choices=(100, 50, 25), required=True)
    parser.add_argument("--load-index", type=int, choices=range(len(LOADS)), required=True)
    parser.add_argument("--integrator", choices=("implicitfast", "implicit"), default="implicitfast")
    args = parser.parse_args()
    name, sign = LOADS[args.load_index]
    print(json.dumps(run_case(name, sign, args.step_us, prior_records(),
        integrator=args.integrator), allow_nan=False), flush=True)
