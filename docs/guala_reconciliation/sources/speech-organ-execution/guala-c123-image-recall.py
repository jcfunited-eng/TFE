"""Normal-artifact two-posture delivery proof from retained fresh taught body.

Reuse S12238's rest/recall/cold-next. No lessons or native edits. Distinguish
known L8 reflex provenance from learned L11 actions (H12251), never by volume.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import resource


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--native-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if root.parent != Path("/tmp") or not root.name.startswith("guala-c123-audio-recall."):
        raise ValueError("wrong disposable root")
    if any(root.iterdir()):
        raise ValueError("empty root required; log outside")
    paired = root / "paired"
    expected = {"GUALA_PAIRED_ROOT": str(paired), "GUALA_MAX_WORLD_BYTES": "16777216"}
    if {k: v for k, v in os.environ.items() if k.startswith("GUALA_")} != expected:
        raise ValueError("wrong task environment")
    for key, value in {"PYTHONUNBUFFERED": "1", "OPENBLAS_NUM_THREADS": "1",
                       "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                       "NUMEXPR_NUM_THREADS": "1", "RAYON_NUM_THREADS": "4"}.items():
        if os.environ.get(key) != value:
            raise ValueError("wrong image environment: " + key)
    import guala_core
    native = Path(guala_core.__file__).resolve().parent / "guala_core.cpython-311-x86_64-linux-gnu.so"
    if (native.parent != Path("/usr/local/lib/python3.11/site-packages/guala_core")
            or hashlib.sha256(native.read_bytes()).hexdigest() !=
            args.native_sha256):
        raise ValueError("wrong normal artifact")
    if hasattr(guala_core.NativeResidentOrganismRuntime, "observe_active_frontier_custody"):
        raise ValueError("diagnostic feature present in release image")
    if os.environ.get("GIT_SHA") != "5e327afbdfa85c45ceed16f45c8f1264d4d1c153":
        raise ValueError("wrong release revision")
    helper = Path("/tmp/guala-c122-runtime-edge.py")
    if hashlib.sha256(helper.read_bytes()).hexdigest() != "393fe88247e5077f10762943a863cf1df77d3bdd8c14e4fdb69edcc6ab892e6a":
        raise ValueError("helper changed")
    spec = importlib.util.spec_from_file_location("verified_edge", helper)
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    if not Path(h.production.__file__).resolve().is_relative_to(Path("/app")):
        raise ValueError("wrong Python source")
    source_root = Path("/tmp/guala-c123-release-recall.hsgWCI/paired")
    head = (source_root / "CURRENT").read_bytes()
    if h.digest(head) != "2c39ef1d457dbdcf776da1545bfe7640468288d396116f77df82c83e01a3b27c":
        raise ValueError("second lesson successor changed")
    admission = h.derive_native_resident_resource_admission(paired)
    bounds = dict(max_body_bytes=admission.max_envelope_bytes, max_world_bytes=16777216)
    saved = h.PairedCurrentStore(source_root, **bounds).restore()
    current = saved.pointer.current
    if (current.organism_tick != 659890 or current.body_sha256 !=
            "55609c3bfbd1421e055bfbc6376220f9f8b04fefdfe4913f0cae15fcede847bd"
            or current.world_sha256 !=
            "9b1b52557f10d54dc4e876391d3db1ee4ebaa25a00bec0b589c453da3b16cf67"):
        raise ValueError("wrong taught pair")
    pcm = Path("/tmp/guala-candidate81-mama-four-intervals.pcm").read_bytes()
    if len(pcm) != 32000 or h.digest(pcm) != "d6835e370273ebf3e1593a60233096a5831f94d1da75cbb412e2f8c980c22f28":
        raise ValueError("wrong cue source")
    cue = h.occurrence(pcm[:8000])
    ordinary = h.production._physical_occurrence(h.production.OccurrenceBody(kind="unattended"))
    store = h.PairedCurrentStore(paired, **bounds)
    store.publish(identity=current.identity, organism_tick=current.organism_tick,
                  body=saved.body, world=saved.world, expected_current_body_sha256=None)
    del saved
    actor = h.production._restore_production_actor()
    h.assert_cold(actor, current)
    before_topology, _ = h.original_topology_census(actor._runtime)
    successor = "474c4e4c494e4531000000000000269c"
    edges = h.anatomy(actor._runtime)
    if len(edges) != 1 or edges[0]["ordering"] != successor:
        raise ValueError("observed taught edge missing before recall")
    h.emit("recall_input", source_tick=current.organism_tick, edges=edges,
           originals=sum(before_topology.values()), module=str(native),
           scope="retained taught body; no lessons; physical producer to HTTP audio")
    h.equip(actor, cue, None, "recall")
    import base64
    from fastapi.testclient import TestClient
    application = h.production.create_lean_production_app(lambda: actor)
    # Existing proof owns start/close; HTTP receives the SAME actor.
    application.state.guala_actor = actor
    client = TestClient(application)
    feed_head = client.get(h.production.PRESSURE_FEED_ROUTE).json()
    cursor = {"stream": feed_head["stream"], "after": feed_head["cursor"]}
    emitted, delivered = {}, {}
    physical_call = actor._physical._call

    def observe_physical(method, runtime, world, event=None):
        result = physical_call(method, runtime, world, event)
        if result.pressure is not None:
            emitted[runtime.live_organism_tick] = result.pressure
        return result

    actor._physical._call = observe_physical

    def drain_audio():
        for _ in range(4):
            response = client.get(h.production.PRESSURE_FEED_ROUTE, params=cursor)
            if response.status_code != 200:
                raise ValueError("HTTP pressure feed refused")
            record = response.json()
            if record["gap"] is not None or record["stream"] != cursor["stream"]:
                raise ValueError("unexpected pressure stream gap")
            for item in record["events"]:
                pcm = base64.b64decode(item["pcm_s16le_base64"], validate=True)
                if item["tick"] in delivered or h.digest(pcm) != item["sha256"]:
                    raise ValueError("duplicate/corrupt delivered emission")
                delivered[item["tick"]] = item["sha256"], pcm
            cursor["after"] = record["cursor"]
            if record["cursor"] == record["latest"]:
                return
        raise ValueError("four bounded audio batches did not reach observed head")

    original_submit = actor.submit

    def observed_submit(event, **kwargs):
        result = original_submit(event, **kwargs)
        drain_audio()
        return result

    actor.submit = observed_submit
    try:
        actor.start()
        h.baseline(actor, ordinary)
        actor.submit(cue)
        before = actor._physical.cue_before
        h.finish_tail(actor, ordinary, before)
    finally:
        actor.close()
    drain_audio()
    client.close()
    if not emitted or delivered != emitted or list(delivered) != list(emitted):
        raise ValueError("physical emitted audio differs from HTTP delivery")
    h.emit("audio_delivery", blocks=len(emitted),
           pcm_bytes=sum(len(item[1]) for item in emitted.values()),
           ticks=list(emitted), exact_all_bytes=True, duplicate_events=0,
           live_network=False, scope="actual copied-body PCM through production HTTP feed")
    rows = [r for r in actor._runtime.intervals if r["tick"] > before]
    learned, reflex, unexplained = [], [], []
    for row in rows:
        for motor in row["motor"]:
            if motor[0] not in h.VOCAL_MOTORS:
                continue
            intended = h.ROOT if motor[0] in h.MIN_MOTORS else successor
            paths = motor[3]
            work_routes = [p for w in row["work"] if w[0] == motor[0] for p in w[1]]
            valid_paths = bool(paths) and all(
                p[1] in (8, 11) and p[2] == motor[0] and p[3] == 12 and p[5] > 0
                for p in paths)
            ordered = [p for p in paths if p[1] == 11]
            if (valid_paths and ordered and all(p[0] == intended for p in ordered)
                    and all(p[0] == intended for p in work_routes)):
                learned.append((row["tick"], motor[0]))
            elif valid_paths and not ordered and not work_routes:
                reflex.append({"tick": row["tick"], "motor": motor})
            else:
                unexplained.append({"tick": row["tick"], "motor": motor,
                                    "work_routes": work_routes})
    roots = [r for r in rows if any((r["tick"], m) in learned for m in h.MIN_MOTORS)]
    successors = [r for r in rows if any((r["tick"], m) in learned for m in h.MAX_MOTORS)]
    root_set = {m for _, m in learned if m in h.MIN_MOTORS}
    next_set = {m for _, m in learned if m in h.MAX_MOTORS}

    def joined_breath(row, ordering, motors):
        # Native completion may return a branch from the preceding interval.
        measured = {tuple(p) for prior in rows
                    if row["tick"] - 1 <= prior["tick"] <= row["tick"]
                    for m in prior["motor"] if (prior["tick"], m[0]) in learned
                    for p in m[3] if p[0] == ordering and p[1] == 11}
        if not row["breath"]:
            return False
        return all(
            breath[2] > 0 and bool(breath[3])
            and {p[2] for p in breath[3]} == motors
            and all(p[0] == ordering and p[1] == 11 and p[3] == 12 and p[5] > 0
                    and tuple(p) in measured for p in breath[3])
            for breath in row["breath"])

    root_breath = [r for r in roots if joined_breath(r, h.ROOT, h.MIN_MOTORS)]
    next_breath = [r for r in successors if joined_breath(r, successor, h.MAX_MOTORS)]
    joined_ticks = {r["tick"] for r in root_breath + next_breath}
    extra_breath = [r["tick"] for r in rows if r["breath"] and r["tick"] not in joined_ticks]
    own = sum(r["self_heard_sample_count"] or 0 for r in actor._physical.records if r["after"] > before)
    passed = (root_set == h.MIN_MOTORS and next_set == h.MAX_MOTORS
              and max(r["tick"] for r in roots) < min(r["tick"] for r in successors)
              and len(learned) == 8 and not unexplained and not extra_breath
              and bool(root_breath) and bool(next_breath)
              and any(r["nonzero_pressure"] for r in root_breath)
              and any(r["nonzero_pressure"] for r in next_breath) and own > 0)
    after_topology, _ = h.original_topology_census(actor._runtime)
    missing = sum((before_topology - after_topology).values())
    current = store.read_pointer().current
    h.emit("recall_result", passed=passed, cue_tick=before+1, root_rows=roots,
           next_rows=successors, learned_events=learned, reflex_events=reflex,
           unexplained_events=unexplained, extra_breath=extra_breath,
           self_heard_samples=own, missing_originals=missing,
           tick=current.organism_tick, body=current.body_sha256, world=current.world_sha256,
           scope="sound-only two postures and quiet; not full word or live speech")
    if (source_root / "CURRENT").read_bytes() != head:
        raise ValueError("source pair changed")
    if not passed or missing:
        raise ValueError("recall not established; retain taught anatomy and exact result")
    del actor
    actor = h.production._restore_production_actor()
    h.assert_cold(actor, current)
    try:
        actor.start()
        result = actor.submit(ordinary)
    finally:
        actor.close()
    if result.native_interval_count != 1:
        raise ValueError("cold-next did not complete")
    current = store.read_pointer().current
    h.emit("cold_next", tick=current.organism_tick, body=current.body_sha256,
           world=current.world_sha256, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
           scope="exact cold restore plus next ordinary; not warm-next comparison")


if __name__ == "__main__":
    main()
