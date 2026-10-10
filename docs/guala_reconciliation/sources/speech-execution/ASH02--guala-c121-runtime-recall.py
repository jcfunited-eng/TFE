"""C121: actual runtime sound-only root recall on the preserved taught pair.

No production network calls, private native mutations, injected pressure,
cognitive fixture splicing, or semantic success assertion. JSONL is observer
evidence only. The production actor keeps its ordinary unattended clock.
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import time

import guala_core
from dsf_ai_service import lean_production_app as production
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import (
    derive_native_resident_resource_admission,
)


def emit(event, **values):
    print(json.dumps({"event": event, **values}, sort_keys=True), flush=True)


def digest(body):
    return hashlib.sha256(body).hexdigest()


class ObservedRuntime:
    """Observe existing calls; do not choose or modify their arguments/results."""
    def __init__(self, runtime):
        self.runtime = runtime
        self.intervals = []

    def __getattr__(self, name):
        value = getattr(self.runtime, name)
        if not name.startswith("advance_") or not callable(value):
            return value

        def call(*args, **kwargs):
            before = self.runtime.live_organism_tick
            started = time.perf_counter()
            try:
                result = value(*args, **kwargs)
            except BaseException as error:
                emit("native_refusal", method=name, tick=before,
                     error=type(error).__name__ + ": " + str(error))
                raise
            intervals = result.causal_interval_evidence
            self.intervals.extend({
                "tick": item.organism_tick,
                "motor": item.motor_unit_recruitments,
                "work": item.learned_motor_work_preparations,
                "breath": item.articulatory_unit_recruitments,
                "nonzero_pressure": sum(sample != 0 for sample in item.articulatory_pressure_pcm),
            } for item in intervals)
            emit("native", method=name, before=before,
                 after=self.runtime.live_organism_tick,
                 milliseconds=(time.perf_counter() - started) * 1000,
                 consumed_self=kwargs.get("consumed_sample_count", (
                     args[5] if name == "advance_in_flight_self_hearing_unsealed"
                     and len(args) > 5 else None)),
                 intervals=[{
                     "tick": item.organism_tick,
                     "motor": item.motor_unit_recruitments,
                     "work": item.learned_motor_work_preparations,
                     "breath": item.articulatory_unit_recruitments,
                     "nonzero_pressure": sum(sample != 0 for sample in item.articulatory_pressure_pcm),
                     "pressure_samples": len(item.articulatory_pressure_pcm),
                 } for item in intervals])
            return result
        return call



class ObservedPhysicalLoop:
    """Timestamp the actual cue on the actor thread; never alter settlement."""
    def __init__(self, physical, cue, quiet):
        self.physical = physical
        self.cue = cue
        self.quiet = quiet
        self.cue_before = None
        self.quiet_at_cue = None

    def __getattr__(self, name):
        return getattr(self.physical, name)

    def settle(self, runtime, world, occurrence):
        if occurrence is self.cue:
            self.cue_before = runtime.live_organism_tick
            recent = runtime.intervals[-8:]
            self.quiet_at_cue = (
                len(recent) == 8 and all(self.quiet(i) for i in recent)
                and runtime.in_flight_acoustic_pressure_s16le is None
            )
            emit("cue_entry", before=self.cue_before, quiet_at_cue=self.quiet_at_cue)
        return self.physical.settle(runtime, world, occurrence)


def original_topology_census(runtime):
    """Read exact original membership/contact topology; never infer semantics."""
    layers = {lineage: layer for lineage, layer, _ in
              runtime.observe_reached_neuron_lineage_layers()}
    targets = {
        "474c4e4c494e4531000000000000077a", "474c4e4c494e45310000000000000796",
        "474c4e4c494e453100000000000007b2", "474c4e4c494e453100000000000007ce",
    }
    keys = Counter()
    matched = []
    for receipt, members, bonds, recurrence, reinforcement in runtime.observe_retained_formation_structures():
        keys[json.dumps([members, bonds], separators=(",", ":"))] += 1
        endpoints = set(members)
        endpoints.update(lineage for left, right, _ in bonds for lineage in (left, right))
        participating = sorted(targets.intersection(endpoints))
        if participating:
            matched.append({
                "receipt": receipt, "targets": participating,
                "members": len(members), "original_bonds": len(bonds),
                "recurrence_bonds": len(recurrence), "reinforcement": reinforcement,
                "source_layers": sorted({layers[lineage] for lineage in endpoints
                                         if layers[lineage] <= 5}),
            })
    return keys, matched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--native-directory", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if root.parent != Path("/tmp") or not root.name.startswith("guala-c121-recall."):
        raise ValueError("only the explicitly allocated disposable directory is allowed")
    if any(root.iterdir()):
        raise ValueError("disposable proof root must be empty")
    if not Path(guala_core.__file__).resolve().is_relative_to(
        args.native_directory.resolve(strict=True)
    ):
        raise ValueError("loaded native module is not the isolated candidate")
    snapshot = Path("/tmp/guala-c120-runtime.IB3mlW/paired")
    body = (snapshot / "body-generations/d91e69c9cf17f74aa8edd7147d6d15fb9baf5424d2fa64a369e5606868194091.glorun").read_bytes()
    world = (snapshot / "world-generations/4a605818648fca6b8bfac82c77d1a9a13c76455c39fd868f843fe6aecc8ac3ae.glworld").read_bytes()
    cue = Path("/tmp/guala-candidate110-phase0.pcm").read_bytes()
    if digest(body) != "d91e69c9cf17f74aa8edd7147d6d15fb9baf5424d2fa64a369e5606868194091":
        raise ValueError("body differs from authenticated tick651474")
    if digest(world) != "4a605818648fca6b8bfac82c77d1a9a13c76455c39fd868f843fe6aecc8ac3ae":
        raise ValueError("world differs from authenticated paired world")
    if digest(cue) != "85a505e8569b7e4407ded73eab2539565096fad17a71afa67a9e93acddb5c545" or len(cue) != 8000:
        raise ValueError("tutor is not the retained exact4000-sample phase")
    paired = root / "paired"
    admission = derive_native_resident_resource_admission(paired)
    store = PairedCurrentStore(paired, max_body_bytes=admission.max_envelope_bytes,
                               max_world_bytes=16_777_216)
    store.publish(identity="1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1",
                  organism_tick=651474, body=body, world=world,
                  expected_current_body_sha256=None)
    del body, world
    os.environ["GUALA_PAIRED_ROOT"] = str(paired)
    os.environ["GUALA_MAX_WORLD_BYTES"] = "16777216"
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["GUALA_SOLAR_UTC_OVERRIDE"] = "0"
    emit("input", module=guala_core.__file__, source_tick=651474, root=str(root),
         solar_utc_second=0, candidate="C121")
    actor = production._restore_production_actor()
    baseline = actor._runtime.observe_reached_contact_count_by_layer_pair()
    before_originals, before_owners = original_topology_census(actor._runtime)
    emit("original_topology_before", count=sum(before_originals.values()), owners=before_owners)
    emit("before", contacts=baseline, tick=actor._runtime.live_organism_tick,
         pending_pressure=actor._runtime.in_flight_acoustic_pressure_s16le is not None)
    actor._runtime = ObservedRuntime(actor._runtime)
    cue_event = production._physical_occurrence(production.OccurrenceBody.model_validate({
        "kind": "sensory",
        "payload": {"source": "microphone",
                    "pcm_s16le_base64": base64.b64encode(cue).decode("ascii")},
    }))
    ordinary = production._physical_occurrence(production.OccurrenceBody(kind="unattended"))
    vocal_motors = {
        "474c4e4c494e453100000000000000b7", "474c4e4c494e453100000000000000c5",
        "474c4e4c494e453100000000000000d3", "474c4e4c494e453100000000000000e1",
        "474c4e4c494e453100000000000000ef", "474c4e4c494e453100000000000000fd",
        "474c4e4c494e453100000000000004fb", "474c4e4c494e45310000000000000509",
    }
    root_ordering = "474c4e4c494e4531000000000000268e"
    def quiet(interval):
        return (not interval["breath"] and interval["nonzero_pressure"] == 0
                and not any(motor[0] in vocal_motors for motor in interval["motor"])
                and not any(work[0] in vocal_motors for work in interval["work"]))
    observed_physical = ObservedPhysicalLoop(actor._physical, cue_event, quiet)
    actor._physical = observed_physical
    def root_motors(interval):
        result = []
        for motor in interval["motor"]:
            carrier_routes = [route for route in motor[3] if route[0] == root_ordering]
            work_routes = [
                route for preparation in interval["work"] if preparation[0] == motor[0]
                for route in preparation[1] if route[0] == root_ordering
            ]
            if carrier_routes or work_routes:
                result.append({"motor": motor, "carrier_routes": carrier_routes,
                               "work_routes": work_routes})
        return result
    try:
        actor.start()
        baseline_start = actor._runtime.live_organism_tick
        while actor._runtime.live_organism_tick - baseline_start < 64:
            actor.submit(ordinary)
            recent = actor._runtime.intervals[-8:]
            if (len(recent) == 8 and all(quiet(interval) for interval in recent)
                    and actor._runtime.in_flight_acoustic_pressure_s16le is None):
                break
        else:
            emit("baseline_refused", reason="eight quiet native intervals not observed in bounded completed occurrences",
                 native_intervals=actor._runtime.live_organism_tick-baseline_start,
                 target_intervals=64, maximum_occurrence_intervals=4,
                 last=actor._runtime.intervals[-8:])
            raise ValueError("no quiet pre-cue baseline; cue was not delivered")
        baseline_end = actor._runtime.live_organism_tick
        emit("quiet_baseline", tick=baseline_end, native_intervals=baseline_end-baseline_start,
             target_intervals=64, maximum_occurrence_intervals=4,
             last_eight=actor._runtime.intervals[-8:])
        result = actor.submit(cue_event)
        before_cue = observed_physical.cue_before
        if before_cue is None:
            raise ValueError("actual cue entry was not observed")
        if observed_physical.quiet_at_cue is not True:
            raise ValueError("actor-thread pre-cue baseline changed; recall is inconclusive")
        emit("sound_only_cue", before=before_cue, quiet_at_cue=observed_physical.quiet_at_cue, after=actor._runtime.live_organism_tick,
             intervals=result.native_interval_count, guided=False, samples=4000)
        while actor._runtime.live_organism_tick - before_cue < 64:
            actor.submit(ordinary)
        recalled = [interval for interval in actor._runtime.intervals
                    if interval["tick"] > before_cue]
        acts = []
        for interval in recalled:
            motors = root_motors(interval)
            if motors:
                acts.append({"tick": interval["tick"], "motors": motors,
                             "breath": interval["breath"]})
        emit("recall_result", cue_tick=before_cue+1, native_intervals=len(recalled),
             target_intervals=64, maximum_occurrence_intervals=4,
             quiet_at_cue=observed_physical.quiet_at_cue,
             root_acts=acts, nonzero_pressure=sum(i["nonzero_pressure"] for i in recalled),
             pending_pressure=actor._runtime.in_flight_acoustic_pressure_s16le is not None,
             last_eight_quiet=len(recalled) >= 8 and all(quiet(i) for i in recalled[-8:]))
    finally:
        actor.close()
    current = store.read_pointer().current
    after = actor._runtime.observe_reached_contact_count_by_layer_pair()
    after_originals, after_owners = original_topology_census(actor._runtime)
    missing_originals = before_originals - after_originals
    emit("original_topology_after", count=sum(after_originals.values()),
         missing_old_count=sum(missing_originals.values()), owners=after_owners,
         scope="original members and bonds only; not a complete neuronal-state comparison")
    if missing_originals:
        raise ValueError("an old recognized original topology was lost")
    emit("recalled", tick=current.organism_tick, body_sha256=current.body_sha256,
         world_sha256=current.world_sha256, contacts=after,
         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    del actor
    cold = production._restore_production_actor()
    if cold._runtime.readiness().state_sha256 != current.body_sha256:
        cold.close()
        raise ValueError("cold restore changed the published successor")
    try:
        cold._runtime = ObservedRuntime(cold._runtime)
        cold.start()
        result = cold.submit(ordinary)
    finally:
        cold.close()
    emit("cold_next", intervals=result.native_interval_count,
         tick=store.read_pointer().current.organism_tick,
         body_sha256=store.read_pointer().current.body_sha256,
         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
