"""Release-only check: fresh live pair -> normal startup migration -> cold-next.

No lesson, private state surgery, live write, clock override, or speech claim.
The input archive is immutable; all publications use a new disposable root.
"""
import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import zipfile


def digest(value):
    return hashlib.sha256(value).hexdigest()


def emit(event, **fields):
    print(json.dumps({"event": event, **fields}, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--native-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if root.parent != Path("/tmp") or not root.name.startswith("guala-c123-release-migration."):
        raise ValueError("wrong disposable root")
    if any(root.iterdir()):
        raise ValueError("disposable root must be empty")
    paired = root / "paired"
    expected_env = {"GUALA_PAIRED_ROOT": str(paired), "GUALA_MAX_WORLD_BYTES": "16777216"}
    if {k: v for k, v in os.environ.items() if k.startswith("GUALA_")} != expected_env:
        raise ValueError("environment differs from live task except disposable root")
    if os.environ.get("PYTHONUNBUFFERED") != "1":
        raise ValueError("missing production stdout setting")
    import guala_core
    from dsf_ai_service import lean_production_app as production
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission
    native = Path(guala_core.__file__).resolve().parent / "guala_core.cpython-311-x86_64-linux-gnu.so"
    if native.parent != Path("/usr/local/lib/python3.11/site-packages/guala_core"):
        raise ValueError("not the isolated ordinary artifact")
    if digest(native.read_bytes()) != args.native_sha256:
        raise ValueError("native artifact changed")
    if hasattr(guala_core.NativeResidentOrganismRuntime, "observe_active_frontier_custody"):
        raise ValueError("diagnostic feature present in ordinary artifact")
    if not Path(production.__file__).resolve().is_relative_to(Path("/app")):
        raise ValueError("wrong Python release source")
    archive_path = Path("/tmp/guala-c123-cutover-backup.gE8MMZ/current.zip")
    archive_hash = digest(archive_path.read_bytes())
    if archive_hash != "e37f9a77bc31b5411dfe76bd2c96256702814b67bff8d6b89ba19a519482f98f":
        raise ValueError("captured archive changed")
    with zipfile.ZipFile(archive_path) as archive:
        if sorted(archive.namelist()) != ["body.glorun.gz", "pointer.json", "world.json"]:
            raise ValueError("unexpected archive members")
        pointer = json.loads(archive.read("pointer.json"))["current"]
        body = gzip.decompress(archive.read("body.glorun.gz"))
        world = archive.read("world.json")
    if pointer["identity"] != "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1" or pointer["organism_tick"] != 661388:
        raise ValueError("wrong captured predecessor")
    for name, value in (("body", body), ("world", world)):
        if digest(value) != pointer[name + "_sha256"] or len(value) != pointer[name + "_bytes"]:
            raise ValueError("captured pair mismatch: " + name)
    admission = derive_native_resident_resource_admission(paired)
    store = PairedCurrentStore(paired, max_body_bytes=admission.max_envelope_bytes,
                              max_world_bytes=16777216)
    store.publish(identity=pointer["identity"], organism_tick=pointer["organism_tick"],
                  body=body, world=world, expected_current_body_sha256=None)
    before_world = json.loads(base64.b64decode(json.loads(world)["payload_base64"]))
    del body, world
    emit("input", pointer=pointer, archive_sha256=archive_hash, native_sha256=args.native_sha256,
         native_path=str(native), solar_override=False, scope="migration and next execution, NOT speech")
    actor = production._restore_production_actor()
    try:
        migrated = store.read_pointer().current
        state = actor._runtime.readiness()
        migrated_world = bytes(actor._world.encoded_snapshot())
        after_world = json.loads(base64.b64decode(json.loads(migrated_world)["payload_base64"]))
        expected_world = dict(before_world, schema="guala.thermally_coupled_embodiment.state.v3",
                              pending_physical_return=None)
        if after_world != expected_world:
            raise ValueError("world migration changed more than schema and empty return")
        if (state.identity != pointer["identity"] or state.organism_tick != pointer["organism_tick"]
                or state.state_sha256 != migrated.body_sha256
                or digest(migrated_world) != migrated.world_sha256):
            raise ValueError("migration lost exact paired identity or tick")
        emit("migrated", tick=state.organism_tick, body=migrated.body_sha256,
             world=migrated.world_sha256, body_bytes=migrated.body_bytes,
             world_payload_preserved=True, pending_return=None)
    finally:
        actor.close()
    del actor
    ordinary = production._physical_occurrence(production.OccurrenceBody(kind="unattended"))
    for phase in ("first-cold-next", "second-cold-next"):
        expected = store.read_pointer().current
        actor = production._restore_production_actor()
        try:
            state = actor._runtime.readiness()
            if (state.state_sha256 != expected.body_sha256 or state.organism_tick != expected.organism_tick
                    or digest(bytes(actor._world.encoded_snapshot())) != expected.world_sha256):
                raise ValueError("cold restore changed exact published pair")
            actor.start()
            result = actor.submit(ordinary)
        finally:
            actor.close()
        current = store.read_pointer().current
        if result.native_interval_count != 1 or current.organism_tick <= expected.organism_tick:
            raise ValueError("ordinary next interval did not complete")
        emit(phase, before=expected.organism_tick, after=current.organism_tick,
             body=current.body_sha256, world=current.world_sha256,
             observation=actor.observation(), scope="exact restore plus execution, not warm/cold equivalence")
        del actor
    if digest(archive_path.read_bytes()) != archive_hash:
        raise ValueError("source archive changed")
    emit("completed", peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
