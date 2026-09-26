"""CT-01 isolated mature-pair proof; never connects to production.

Run only in the exact production image with --network none and no live mounts.
The sole test intervention is an ordinary external caregiver presentation of
the object already in that caregiver's custody. No organism state is edited.
This proves caregiver delivery, NOT autonomous acquisition. Eight subsequent
intervals are a test observation bound, not a cognitive duration or retry law.
"""
from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import zlib


def report(event, **values):
    print(json.dumps({"event": event, **values}, sort_keys=True), flush=True)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def startup():
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    from dsf_ai_service.lean_production_app import _restore_production_actor
    store = PairedCurrentStore(Path(os.environ["GUALA_PAIRED_ROOT"]),
                               max_body_bytes=67108864, max_world_bytes=16777216)
    before = store.restore()
    actor = _restore_production_actor()
    try:
        assert actor._runtime.encoded() == before.body, "startup changed lived body"
        assert bytes(actor._world.encoded_snapshot()) == before.world, "startup changed lived world"
        assert actor._pointer == before.pointer == store.read_pointer()
        from dsf_ai_service.substrate import native_core
        import guala_core
        assert native_core.is_installed(), "exact production acceleration not installed"
        report("restored", tick=actor._runtime.live_organism_tick,
               native_module=guala_core.__file__, native_sha256=digest(Path(guala_core.__file__).read_bytes()),
               current=asdict(before.pointer.current))
        return actor
    except BaseException:
        actor.close()
        raise


def persist(actor):
    # Exercise the actual actor -> checkpoint worker -> paired store ordering.
    actor._finish_checkpoint()
    saved = actor._store.restore()
    assert saved.pointer == actor._pointer == actor._store.read_pointer()
    assert saved.body == actor._runtime.encoded()
    assert saved.world == bytes(actor._world.encoded_snapshot())
    assert actor._pending_intervals == 0
    assert actor._checkpoint_error is None and actor._cleanup_error is None
    report("persisted", current=asdict(saved.pointer.current))


def interval(actor, occurrence):
    tick = actor._runtime.live_organism_tick
    identity = actor._runtime.identity
    result = actor._settle(occurrence)
    assert result.native_interval_count == 1
    assert actor._runtime.live_organism_tick == tick + 1
    assert actor._runtime.identity == identity
    assert len(actor._world.observation_snapshot().objects) <= 64
    o = result.observation
    report("interval", tick=tick + 1, act=o["her_act"], applied=o["requested_world_action"],
           refusal=o["world_action_refusal"], reserve=o["reserve_micrograms"],
           intake_zeptojoules=o["real_nutrition_intake_zeptojoules"],
           presentation=o["caregiver_presentation"], withdrawal=o["caregiver_withdrawal"])
    return result


def main():
    mode = sys.argv[1]
    assert mode in ("baseline", "candidate", "cold")
    started = time.monotonic()
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    from dsf_ai_service.lean_actor import PhysicalOccurrence
    from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
    if mode != "cold":
        raw = Path("/tmp/current.json").read_bytes()
        assert digest(raw) == "239e232a3d61e26d2907d772fc2b3ed36b15843288b282964bdcce00f31348fd"
        capture = json.loads(raw)
        p = capture["pointer"]["current"]
        body = zlib.decompress(base64.b64decode(capture["body_zlib"]))
        world = zlib.decompress(base64.b64decode(capture["world_zlib"]))
        assert len(body) == p["body_bytes"] and digest(body) == p["body_sha256"]
        assert len(world) == p["world_bytes"] and digest(world) == p["world_sha256"]
        root = Path(os.environ["GUALA_PAIRED_ROOT"])
        assert not root.exists(), "probe must start from an empty isolated store"
        store = PairedCurrentStore(root, max_body_bytes=67108864, max_world_bytes=16777216)
        # Import the authenticated pair without changing its encoded contents.
        store.publish(identity=p["identity"], organism_tick=p["organism_tick"],
                      body=body, world=world, expected_current_body_sha256=None)
    actor = startup()
    try:
        for name in ("guala_caretaker_hand.py", "guala_functional_loop.py", "guala_functional_organism.py"):
            path = Path("/app/dsf_ai_service") / name
            report("source", path=str(path), sha256=digest(path.read_bytes()))
        if mode == "cold":
            interval(actor, PhysicalOccurrence("unattended", None))
            persist(actor)
        else:
            full = actor._world.canonical_observation_snapshot()
            people = [b for b in full.bodies if b.body_id != full.self_body_id]
            assert len(people) == 1 and people[0].held_object_id is not None
            held = people[0].held_object_id
            assert held not in {o.object_id for o in actor._world.observation_snapshot().objects}
            assert actor._runtime.reserve_micrograms == 0 and actor._runtime.feeding
            before_intake = actor._runtime.counts["meals_micrograms"]
            before_bites = actor._runtime.counts["bites"]
            report("custody_input", object_id=held, hidden_from_organism=True, reserve=0)
            result = interval(actor, PhysicalOccurrence("sensory", LeanSensoryOccurrence(
                "caretaker-food", None, None, present_food=held)))
            presentation = result.observation["caregiver_presentation"]
            if mode == "baseline":
                assert presentation["presented"] is False
                assert any(s.get("operation") == "resolve" and s.get("reason") == "unknown_object"
                           for s in presentation["steps"])
                report("predecessor_defect_reproduced")
            else:
                assert presentation["presented"] is True, "mature caregiver delivery refused"
                for _ in range(8):
                    if actor._runtime.counts["meals_micrograms"] > before_intake:
                        break
                    result = interval(actor, PhysicalOccurrence("unattended", None))
                assert actor._runtime.counts["meals_micrograms"] > before_intake, "no real intake"
                assert actor._runtime.counts["bites"] > before_bites, "no ordinary oral bite"
                assert result.observation["real_nutrition_intake_zeptojoules"] > 0
                report("caregiver_delivery_intake", micrograms=actor._runtime.counts["meals_micrograms"] - before_intake,
                       autonomous_acquisition=False)
                persist(actor)
    finally:
        # If an assertion failed after settlement, finish only this discarded
        # local checkpoint before joining its worker. No new interval is run.
        try:
            actor._finish_checkpoint()
        finally:
            actor.close()
    if mode == "candidate":
        subprocess.run([sys.executable, "-B", __file__, "cold"], check=True, timeout=90)
    report("finished", mode=mode, elapsed_seconds=time.monotonic() - started,
           max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
