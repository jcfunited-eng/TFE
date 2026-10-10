"""C122: actual-runtime first-edge teaching, sound-only recall, and cold-next.

Test-only external tutor/observer. Never patches native state, disables the
unattended actor clock, imports the legacy shell, or sends production requests.
C121's already-executed observers are reused without changing settlement.
"""
import argparse
import base64
import hashlib
import importlib.util
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

OBSERVER_PATH = Path("/tmp/guala-c121-runtime-recall.py")
if hashlib.sha256(OBSERVER_PATH.read_bytes()).hexdigest() != (
    "b061c218ac5429619a1df469871478acd681fb450eb5a8ab209264a8ab2bab30"
):
    raise ValueError("preserved C121 observer source changed")
_spec = importlib.util.spec_from_file_location("c121_preserved_observer", OBSERVER_PATH)
_old = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_old)
emit = _old.emit
digest = _old.digest
class ObservedRuntime(_old.ObservedRuntime):
    def __getattr__(self, name):
        call = super().__getattr__(name)
        if not name.startswith("advance_") or not callable(call):
            return call

        def observed(*args, **kwargs):
            result = call(*args, **kwargs)
            emit("native_roster", source_ports=[s.port_count for s in args[0]],
                 actual_sense_counts=result.receptor_ingress_sense_counts)
            return result
        return observed

original_topology_census = _old.original_topology_census
ROOT = "474c4e4c494e4531000000000000268e"
MIN_MOTORS = {"474c4e4c494e453100000000000000" + suffix for suffix in ("b7", "d3", "ef")}
MIN_MOTORS.add("474c4e4c494e453100000000000004fb")
MAX_MOTORS = {"474c4e4c494e453100000000000000" + suffix for suffix in ("c5", "e1", "fd")}
MAX_MOTORS.add("474c4e4c494e45310000000000000509")
VOCAL_MOTORS = MIN_MOTORS | MAX_MOTORS


def quiet(interval):
    return (not interval["breath"] and interval["nonzero_pressure"] == 0
            and not any(m[0] in VOCAL_MOTORS for m in interval["motor"])
            and not any(w[0] in VOCAL_MOTORS for w in interval["work"]))


def motors_from(interval, ordering):
    found = set()
    for motor in interval["motor"]:
        carrier = any(route[0] == ordering for route in motor[3])
        work = any(route[0] == ordering
                   for preparation in interval["work"] if preparation[0] == motor[0]
                   for route in preparation[1])
        if carrier or work:
            found.add(motor[0])
    return found


def occurrence(pcm, guided=False):
    payload = {"source": "guided-vocal-microphone" if guided else "microphone",
               "pcm_s16le_base64": base64.b64encode(pcm).decode("ascii")}
    if guided:
        payload["guided_vocal_drives"] = [
            {"axis_ordinal": axis, "direction_ordinal": 1,
             "outward_elementary_carriers": 1500} for axis in (37, 38, 39, 44)
        ]
    return production._physical_occurrence(production.OccurrenceBody.model_validate(
        {"kind": "sensory", "payload": payload}
    ))


class ObservedPhysical:
    def __init__(self, physical, cue, guide, stage):
        self.physical, self.cue, self.guide = physical, cue, guide
        self.stage = stage
        self.expected_guide_predecessor = None
        self.cue_before = None
        self.records = []

    def __getattr__(self, name):
        return getattr(self.physical, name)

    def _call(self, method, runtime, world, event=None):
        before = runtime.live_organism_tick
        if event is self.cue:
            recent = runtime.intervals[-8:]
            clean = (len(recent) == 8 and all(quiet(i) for i in recent)
                     and runtime.in_flight_acoustic_pressure_s16le is None)
            emit("cue_entry", stage=self.stage, before=before, quiet_at_cue=clean)
            if not clean:
                raise ValueError("harness cue timing inconclusive; baseline changed before ingress")
            self.cue_before = before
        if self.guide is not None and event is self.guide:
            pending = world.pending_physical_return
            exact = (before == self.expected_guide_predecessor and pending is not None
                     and pending.producer_tick == before)
            emit("guide_entry", stage=self.stage, before=before,
                 expected=self.expected_guide_predecessor,
                 pending_tick=None if pending is None else pending.producer_tick,
                 pending_self=runtime.in_flight_acoustic_pressure_s16le is not None,
                 exact_next_interval=exact)
            if not exact:
                raise ValueError("harness missed measured next-return interval; guide NOT delivered")
        started = time.perf_counter()
        result = (self.physical.unattended(runtime, world) if method == "unattended"
                  else self.physical.settle(runtime, world, event))
        fields = ("external_heard_sample_count", "external_guided_vocal_axis_count",
                  "self_heard_sample_count", "self_hearing_source_tick",
                  "consumed_physical_return_tick", "pending_physical_return_tick",
                  "physical_return_source_count", "vestibular_return_consumed",
                  "world_revision")
        row = {name: result.observation.get(name) for name in fields}
        row.update(before=before, after=runtime.live_organism_tick,
                   intervals=result.native_interval_count,
                   milliseconds=(time.perf_counter()-started)*1000,
                   guided=self.guide is not None and event is self.guide,
                   cue=event is self.cue)
        self.records.append(row)
        emit("physical", stage=self.stage, **row)
        if result.native_interval_count != 1 or row["after"] != before + 1:
            raise RuntimeError("candidate violated one ordinary interval per call")
        if row["guided"] and row["consumed_physical_return_tick"] != before:
            raise RuntimeError("delivered guide did not consume exact predecessor return")
        return result

    def settle(self, runtime, world, event):
        return self._call("settle", runtime, world, event)

    def unattended(self, runtime, world):
        return self._call("unattended", runtime, world)


def equip(actor, cue, guide, stage):
    actor._runtime = ObservedRuntime(actor._runtime)
    actor._physical = ObservedPhysical(actor._physical, cue, guide, stage)
    return actor


def baseline(actor, ordinary):
    start = actor._runtime.live_organism_tick
    while actor._runtime.live_organism_tick - start < 64:
        actor.submit(ordinary)
        recent = actor._runtime.intervals[-8:]
        if (len(recent) == 8 and all(quiet(i) for i in recent)
                and actor._runtime.in_flight_acoustic_pressure_s16le is None):
            emit("quiet_baseline", stage=actor._physical.stage,
                 tick=actor._runtime.live_organism_tick, intervals_since_start=
                 actor._runtime.live_organism_tick-start)
            return
    raise ValueError("bounded pre-cue baseline unavailable; no cue delivered")


def finish_tail(actor, ordinary, before_cue):
    while actor._runtime.live_organism_tick - before_cue < 64:
        actor.submit(ordinary)
    recent = actor._runtime.intervals[-8:]
    clean = (len(recent) == 8 and all(quiet(i) for i in recent)
             and actor._runtime.in_flight_acoustic_pressure_s16le is None)
    emit("tail", stage=actor._physical.stage, after=actor._runtime.live_organism_tick,
         last_eight_vocally_quiet=clean, pending_physical=
         actor._world.pending_physical_return is not None)
    if not clean:
        raise ValueError("64-clock tail not vocally quiet; preserve result, do not extend blindly")


def anatomy(runtime):
    layers = {lineage: layer for lineage, layer, _ in
              runtime.observe_reached_neuron_lineage_layers()}
    contacts = runtime.observe_reached_contact_channel_states()
    root_edges = []
    for row in contacts:
        left, right = row[:2]
        if ROOT not in (left, right):
            continue
        other = right if left == ROOT else left
        if layers.get(other) == 11:
            motor_contacts = [c for c in contacts if other in c[:2]
                              and (c[1] if c[0] == other else c[0]) in MAX_MOTORS]
            root_edges.append({"ordering": other, "bond": row,
                               "motor_contacts": motor_contacts})
    return root_edges


def assert_cold(actor, pointer):
    r = actor._runtime.readiness()
    world_sha = digest(bytes(actor._world.encoded_snapshot()))
    if (r.state_sha256 != pointer.body_sha256
            or actor._runtime.live_organism_tick != pointer.organism_tick
            or world_sha != pointer.world_sha256):
        raise ValueError("cold body/world/tick differs from exact published pair")
    emit("cold_exact", tick=pointer.organism_tick, body=pointer.body_sha256,
         world=pointer.world_sha256)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--native-directory", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if root.parent != Path("/tmp") or not root.name.startswith("guala-c122-edge."):
        raise ValueError("only explicit disposable C122 directory is allowed")
    if any(root.iterdir()):
        raise ValueError("disposable root must be empty")
    if not Path(guala_core.__file__).resolve().is_relative_to(
            args.native_directory.resolve(strict=True)):
        raise ValueError("candidate native module not loaded")
    if not Path(production.__file__).resolve().is_relative_to(
            Path("/tmp/guala-speech-existing-organ")):
        raise ValueError("production Python module not loaded from reviewed worktree")
    if any(name.startswith("GUALA_") for name in os.environ):
        raise ValueError("unexpected inherited Guala environment; inspect rather than override")
    source_path = Path("/tmp/guala-c121-recall.5e8ILP/paired")
    if digest((source_path/"CURRENT").read_bytes()) != (
            "e32442eb3370924a65211484528bed3b44925ec0c3e008cc4f7c8149f765d018"):
        raise ValueError("preserved C121 CURRENT changed")
    paired = root/"paired"
    admission = derive_native_resident_resource_admission(paired)
    bounds = dict(max_body_bytes=admission.max_envelope_bytes, max_world_bytes=16777216)
    source_store = PairedCurrentStore(source_path, **bounds)
    source = source_store.restore()
    current = source.pointer.current
    if (current.organism_tick != 651548 or current.body_sha256 !=
            "b95580172c60c1a6eb7ad36041f07cfac99605a7fe80515fb4df32bdd0ab7667"
            or current.world_sha256 !=
            "3e1db47e1b5e72418876de0134772fbf216fbb1026af449988a16bb0051b8333"):
        raise ValueError("wrong preserved source pair")
    pcm = Path("/tmp/guala-candidate81-mama-four-intervals.pcm").read_bytes()
    if len(pcm) != 32000 or digest(pcm) != (
            "d6835e370273ebf3e1593a60233096a5831f94d1da75cbb412e2f8c980c22f28"):
        raise ValueError("wrong four-phase tutor")
    if digest(pcm[:8000]) != "85a505e8569b7e4407ded73eab2539565096fad17a71afa67a9e93acddb5c545":
        raise ValueError("wrong root cue")
    if digest(pcm[8000:16000]) != "43692e736aec0fd200a1199e18af49978b473fa9e619a0459bb126e2f12fe374":
        raise ValueError("wrong phase1 guide")
    cue, guide = occurrence(pcm[:8000]), occurrence(pcm[8000:16000], guided=True)
    ordinary = production._physical_occurrence(production.OccurrenceBody(kind="unattended"))
    store = PairedCurrentStore(paired, **bounds)
    store.publish(identity=current.identity, organism_tick=current.organism_tick,
                  body=source.body, world=source.world, expected_current_body_sha256=None)
    del source
    os.environ.update(GUALA_PAIRED_ROOT=str(paired), GUALA_MAX_WORLD_BYTES="16777216",
                      PYTHONUNBUFFERED="1", GUALA_SOLAR_UTC_OVERRIDE="0")
    emit("input", candidate="C122", module=guala_core.__file__, source_tick=651548,
         root=str(root), solar_utc_second=0,
         environment_scope="same declared copied-world clock as C121; NOT live override")
    actor = production._restore_production_actor()
    before_topology, _ = original_topology_census(actor._runtime)
    before_edges = anatomy(actor._runtime)
    emit("before", originals=sum(before_topology.values()), edges=before_edges,
         anatomy_environment="task1456 has no receptor-roster overrides",
         native_module=guala_core.__file__)
    equip(actor, cue, guide, "teach")
    try:
        actor.start()
        baseline(actor, ordinary)
        actor.submit(cue)
        cue_before = actor._physical.cue_before
        root_seen = set()
        while actor._runtime.live_organism_tick-cue_before < 64:
            for row in actor._runtime.intervals:
                if row["tick"] > cue_before:
                    root_seen.update(motors_from(row, ROOT))
            if MIN_MOTORS.issubset(root_seen):
                completion = max(row["tick"] for row in actor._runtime.intervals
                                 if row["tick"] > cue_before and motors_from(row, ROOT))
                actor._physical.expected_guide_predecessor = completion
                emit("root_completion", tick=completion, motors=sorted(root_seen))
                actor.submit(guide)
                break
            actor.submit(ordinary)
        else:
            raise ValueError("root completion not observed; successor guide NOT delivered")
        finish_tail(actor, ordinary, cue_before)
    finally:
        actor.close()
    after_topology, _ = original_topology_census(actor._runtime)
    edges = anatomy(actor._runtime)
    missing = sum((before_topology-after_topology).values())
    new_edges = [edge for edge in edges
                 if edge["ordering"] not in {e["ordering"] for e in before_edges}
                 and len({c[1] if c[0] == edge["ordering"] else c[0]
                          for c in edge["motor_contacts"]}) == 4]
    emit("taught", tick=store.read_pointer().current.organism_tick,
         missing_originals=missing, edges=edges, new_complete_edges=new_edges,
         self_heard_samples=sum(r["self_heard_sample_count"] or 0
                               for r in actor._physical.records))
    if missing:
        raise ValueError("original memory member/bond topology lost")
    if len(new_edges) != 1:
        raise ValueError("exactly one new complete root-to-maximum edge not observed")
    successor = new_edges[0]["ordering"]
    del actor
    actor = production._restore_production_actor()
    assert_cold(actor, store.read_pointer().current)
    equip(actor, cue, None, "recall")
    try:
        actor.start()
        baseline(actor, ordinary)
        actor.submit(cue)
        cue_before = actor._physical.cue_before
        finish_tail(actor, ordinary, cue_before)
    finally:
        actor.close()
    recalled = [r for r in actor._runtime.intervals if r["tick"] > cue_before]
    root_rows = [r for r in recalled if motors_from(r, ROOT)]
    next_rows = [r for r in recalled if motors_from(r, successor)]
    root_set = set().union(*(motors_from(r, ROOT) for r in root_rows))
    next_set = set().union(*(motors_from(r, successor) for r in next_rows))
    own_samples = sum(r["self_heard_sample_count"] or 0 for r in actor._physical.records
                      if r["after"] > cue_before)
    passed = (MIN_MOTORS.issubset(root_set) and MAX_MOTORS.issubset(next_set)
              and max(r["tick"] for r in root_rows) < min(r["tick"] for r in next_rows)
              and any(r["breath"] for r in root_rows)
              and any(r["breath"] for r in next_rows)
              and any(r["nonzero_pressure"] for r in root_rows)
              and any(r["nonzero_pressure"] for r in next_rows) and own_samples > 0)
    final_topology, _ = original_topology_census(actor._runtime)
    missing = sum((before_topology-final_topology).values())
    emit("recall_result", passed=passed, cue_tick=cue_before+1,
         root_rows=root_rows, next_rows=next_rows, self_heard_samples=own_samples,
         missing_originals=missing, scope="two postures, not whole word or live speech")
    if not passed or missing:
        raise ValueError("actual-runtime two-posture acceptance not established")
    current = store.read_pointer().current
    del actor
    cold = production._restore_production_actor()
    assert_cold(cold, current)
    try:
        cold.start()
        result = cold.submit(ordinary)
    finally:
        cold.close()
    emit("cold_next", scope="exact prior restore plus next execution; no warm-next comparison",
         intervals=result.native_interval_count,
         tick=store.read_pointer().current.organism_tick,
         body_sha256=store.read_pointer().current.body_sha256,
         world_sha256=store.read_pointer().current.world_sha256,
         peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if result.native_interval_count != 1:
        raise ValueError("cold-next did not settle exactly one interval")


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        emit("proof_refused", error=type(error).__name__+": "+str(error),
             peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        raise
