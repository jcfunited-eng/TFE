"""D12236: use the retained second-lesson pair; rest, sound-only recall, cold-next.

No new lesson, organism law, direct state mutation, hidden rest, or live call.
The real runtime consumes the saved pending body and sound on ordinary clocks.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import resource
import guala_core

H = Path("/tmp/guala-c122-runtime-edge.py")
assert hashlib.sha256(H.read_bytes()).hexdigest() == "393fe88247e5077f10762943a863cf1df77d3bdd8c14e4fdb69edcc6ab892e6a"
spec = importlib.util.spec_from_file_location("c122_verified", H)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
SUCCESSOR = "474c4e4c494e4531000000000000269c"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if root.parent != Path("/tmp") or not root.name.startswith("guala-c123-recall."):
        raise ValueError("wrong disposable root")
    if any(root.iterdir()):
        raise ValueError("disposable root is not empty")
    native_path = Path(guala_core.__file__).resolve().parent / "guala_core.cpython-311-x86_64-linux-gnu.so"
    assert native_path.parent == Path("/tmp/guala-c123-admission-wheel.Qcx88Y/installed/guala_core")
    assert h.digest(native_path.read_bytes()) == "d015e3b978b8690705c43358e84abfde289948b261442f512d4886cf5aaafb7b"
    assert Path(h.production.__file__).resolve().is_relative_to(Path("/tmp/guala-speech-existing-organ"))
    if any(k.startswith("GUALA_") for k in os.environ):
        raise ValueError("unexpected inherited Guala environment")
    source_root = Path("/tmp/guala-c123-repeat.T706D9/paired")
    head = (source_root / "CURRENT").read_bytes()
    assert h.digest(head) == "569f5b0d30098eb9c07d8ee23e29797606fefffe106410e5b036d903b44511f4"
    paired = root / "paired"
    admission = h.derive_native_resident_resource_admission(paired)
    bounds = dict(max_body_bytes=admission.max_envelope_bytes, max_world_bytes=16777216)
    source = h.PairedCurrentStore(source_root, **bounds).restore()
    current = source.pointer.current
    assert current.organism_tick == 651632
    assert current.body_sha256 == "885fb49d9836d0848caf6a28f514b6e1145fc0953737a4bcc8ed66cdde64226c"
    assert current.world_sha256 == "74da84ef674a7e92e2206e10d2d7218c75c04b8dbb472b79f410ee7323952a2f"
    pcm = Path("/tmp/guala-candidate81-mama-four-intervals.pcm").read_bytes()
    assert len(pcm) == 32000
    assert h.digest(pcm) == "d6835e370273ebf3e1593a60233096a5831f94d1da75cbb412e2f8c980c22f28"
    cue = h.occurrence(pcm[:8000])
    ordinary = h.production._physical_occurrence(h.production.OccurrenceBody(kind="unattended"))
    store = h.PairedCurrentStore(paired, **bounds)
    store.publish(identity=current.identity, organism_tick=current.organism_tick,
                  body=source.body, world=source.world, expected_current_body_sha256=None)
    del source
    os.environ.update(GUALA_PAIRED_ROOT=str(paired), GUALA_MAX_WORLD_BYTES="16777216",
                      PYTHONUNBUFFERED="1", GUALA_SOLAR_UTC_OVERRIDE="0")
    actor = h.production._restore_production_actor()
    h.assert_cold(actor, current)
    before_topology, _ = h.original_topology_census(actor._runtime)
    edges = h.anatomy(actor._runtime)
    assert len(edges) == 1 and edges[0]["ordering"] == SUCCESSOR
    pending = actor._world.pending_physical_return
    assert pending is not None and pending.producer_tick == 651632
    h.emit("recall_input", source_tick=651632, originals=sum(before_topology.values()),
           pending_tick=pending.producer_tick, edges=edges,
           scope="actual runtime two-posture recall, not full word or production")
    h.equip(actor, cue, None, "finish-existing-lesson")
    try:
        actor.start()
        h.finish_tail(actor, ordinary, 651628)
    finally:
        actor.close()
    rested = store.read_pointer().current
    h.emit("rested", tick=rested.organism_tick, body=rested.body_sha256, world=rested.world_sha256)
    del actor
    actor = h.production._restore_production_actor()
    h.assert_cold(actor, rested)
    h.equip(actor, cue, None, "recall")
    try:
        actor.start()
        h.baseline(actor, ordinary)
        actor.submit(cue)
        cue_before = actor._physical.cue_before
        h.finish_tail(actor, ordinary, cue_before)
    finally:
        actor.close()
    rows = [r for r in actor._runtime.intervals if r["tick"] > cue_before]
    roots = [r for r in rows if h.motors_from(r, h.ROOT)]
    successors = [r for r in rows if h.motors_from(r, SUCCESSOR)]
    root_set = set().union(*(h.motors_from(r, h.ROOT) for r in roots))
    successor_set = set().union(*(h.motors_from(r, SUCCESSOR) for r in successors))
    vocal_events = [(r["tick"], m[0]) for r in rows for m in r["motor"] if m[0] in h.VOCAL_MOTORS]
    expected_events = [(r["tick"], m) for r in roots for m in h.motors_from(r, h.ROOT)]
    expected_events += [(r["tick"], m) for r in successors for m in h.motors_from(r, SUCCESSOR)]
    own = sum(r["self_heard_sample_count"] or 0 for r in actor._physical.records if r["after"] > cue_before)
    passed = (root_set == h.MIN_MOTORS and successor_set == h.MAX_MOTORS
              and max(r["tick"] for r in roots) < min(r["tick"] for r in successors)
              and len(expected_events) == 8 and sorted(vocal_events) == sorted(expected_events)
              and any(r["breath"] for r in roots) and any(r["breath"] for r in successors)
              and any(r["nonzero_pressure"] for r in roots)
              and any(r["nonzero_pressure"] for r in successors) and own > 0)
    after_topology, _ = h.original_topology_census(actor._runtime)
    missing = sum((before_topology - after_topology).values())
    current = store.read_pointer().current
    h.emit("recall_result", passed=passed, cue_tick=cue_before+1, root_rows=roots,
           next_rows=successors, vocal_events=vocal_events, self_heard_samples=own,
           missing_originals=missing, tick=current.organism_tick,
           body=current.body_sha256, world=current.world_sha256,
           scope="two postures with quiet baseline and finite quiet, not full word")
    if not passed or missing:
        raise ValueError("two-posture runtime recall not established; retain anatomy success")
    del actor
    actor = h.production._restore_production_actor()
    h.assert_cold(actor, current)
    h.equip(actor, cue, None, "cold-next")
    try:
        actor.start()
        result = actor.submit(ordinary)
    finally:
        actor.close()
    assert result.native_interval_count == 1
    assert (source_root / "CURRENT").read_bytes() == head
    h.emit("cold_next", tick=store.read_pointer().current.organism_tick,
           body=store.read_pointer().current.body_sha256,
           world=store.read_pointer().current.world_sha256,
           scope="exact prior restore and next execution, not warm-next comparison",
           peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)

if __name__ == "__main__":
    main()
