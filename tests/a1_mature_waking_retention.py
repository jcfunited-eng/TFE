"""Bounded real-intake retention seam, NOT autonomous acquisition acceptance.

Uses a separate authenticated copied pair and one ordinary caregiver offer.
The eight intake-observation and 136 pressure intervals are proof bounds only;
no body state, memory, reserves, sleep pressure, decisions or routes are injected.
Run in the exact production image, network none, no live mounts. The accepted
CT-01 startup/physical delivery fixes must be identical in both conditions.
"""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import zlib

from a1_mature_caretaker_delivery import digest, persist, report, startup


def records(actor):
    state = actor._runtime._state
    assert len(state["moments"]) <= 128
    assert len(state["meanings"]) <= 4096
    return dict(state["meanings"], **state["moments"])


def step(actor, occurrence):
    # Same checkpoint adoption/backpressure ordering as the actor's run loop.
    actor._adopt_checkpoint_if_ready()
    if actor._durability_blocked():
        assert actor._checkpoint.outstanding
        actor._receive_required_checkpoint()
    assert actor._runtime._state["asleep"] is False
    before = actor._runtime.live_organism_tick
    identity = actor._runtime.identity
    result = actor._settle(occurrence)
    assert result.native_interval_count == 1
    assert actor._runtime.live_organism_tick == before + 1
    assert actor._runtime.identity == identity
    assert actor._runtime._state["asleep"] is False
    assert len(actor._world.observation_snapshot().objects) <= 64
    records(actor)
    return result


def seed_copied_pair():
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    raw = Path("/tmp/current.json").read_bytes()
    assert digest(raw) == "239e232a3d61e26d2907d772fc2b3ed36b15843288b282964bdcce00f31348fd"
    capture = json.loads(raw)
    p = capture["pointer"]["current"]
    body = zlib.decompress(base64.b64decode(capture["body_zlib"]))
    world = zlib.decompress(base64.b64decode(capture["world_zlib"]))
    assert len(body) == p["body_bytes"] and digest(body) == p["body_sha256"]
    assert len(world) == p["world_bytes"] and digest(world) == p["world_sha256"]
    root = Path(os.environ["GUALA_PAIRED_ROOT"])
    assert not root.exists(), "must use a fresh isolated store"
    store = PairedCurrentStore(root, max_body_bytes=67108864, max_world_bytes=16777216)
    store.publish(identity=p["identity"], organism_tick=p["organism_tick"], body=body,
                  world=world, expected_current_body_sha256=None)


def transition_hashes(actor, keys):
    saved = records(actor)
    return {key: digest(json.dumps(saved[key]["motor_transition"], sort_keys=True).encode())
            for key in keys if key in saved}


def main():
    mode = sys.argv[1]
    assert mode in ("baseline", "candidate", "cold")
    started = time.monotonic()
    from dsf_ai_service.lean_actor import PhysicalOccurrence
    from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
    unattended = PhysicalOccurrence("unattended", None)
    if mode != "cold":
        seed_copied_pair()
    actor = startup()
    saved_hashes = {}
    try:
        if mode == "cold":
            expected = json.loads(sys.argv[2])
            assert transition_hashes(actor, expected) == expected
            step(actor, unattended)
            assert transition_hashes(actor, expected) == expected
            persist(actor)
            report("cold_retention", roots=len(expected), next_interval=True)
        else:
            for name in ("episodic_binding_engine.py", "guala_functional_organism.py",
                         "guala_functional_loop.py", "guala_caretaker_hand.py",
                         "lean_production_app.py"):
                path = Path("/app/dsf_ai_service") / name
                report("source", path=str(path), sha256=digest(path.read_bytes()))
            first_tick = actor._runtime.live_organism_tick
            assert actor._runtime._state["asleep"] is False
            assert actor._runtime.reserve_micrograms == 0 and actor._runtime.feeding
            initial_intake = actor._runtime.counts["meals_micrograms"]
            full = actor._world.canonical_observation_snapshot()
            people = [b for b in full.bodies if b.body_id != full.self_body_id]
            assert len(people) == 1 and people[0].held_object_id is not None
            result = step(actor, PhysicalOccurrence("sensory", LeanSensoryOccurrence(
                "caretaker-food", None, None, present_food=people[0].held_object_id)))
            assert result.observation["caregiver_presentation"]["presented"] is True
            experienced = {}
            for _ in range(8):
                step(actor, unattended)
                for key, entry in records(actor).items():
                    trial = entry.get("motor_transition")
                    if (trial and trial["start_tick"] >= first_tick
                            and trial["intake"] > 0 and trial["refusal"] is None):
                        experienced.setdefault(key, copy.deepcopy(trial))
            assert actor._runtime.counts["meals_micrograms"] > initial_intake
            assert experienced, "no actual finalized intake trial observed"
            report("physical_intake", roots=len(experienced),
                   micrograms=actor._runtime.counts["meals_micrograms"] - initial_intake,
                   autonomous_acquisition=False, elapsed_seconds=time.monotonic() - started)
            assert set(experienced).issubset(actor._runtime._state["moments"])
            initial_keys = set(actor._runtime._state["moments"])
            encountered_keys = set(initial_keys)
            for i in range(136):
                assert actor._runtime._state["asleep"] is False
                step(actor, unattended)
                assert actor._runtime._state["asleep"] is False
                encountered_keys.update(actor._runtime._state["moments"])
                if (i + 1) % 32 == 0:
                    report("retention_progress", intervals=i + 1,
                           tick=actor._runtime.live_organism_tick,
                           elapsed_seconds=time.monotonic() - started)
            current = records(actor)
            retained = {key: trial for key, trial in experienced.items() if key in current}
            for key, trial in retained.items():
                assert current[key]["motor_transition"] == trial
            report("retention_result", mode=mode, original_intake_roots=len(experienced),
                   retained_intake_roots=len(retained), new_record_keys=len(encountered_keys - initial_keys),
                   moments=len(actor._runtime._state["moments"]),
                   meanings=len(actor._runtime._state["meanings"]),
                   asleep=actor._runtime._state["asleep"],
                   elapsed_seconds=time.monotonic() - started)
            # Actual new records, not time alone, must exercise the128-slot bound.
            assert len(encountered_keys - initial_keys) >= 128
            if mode == "baseline":
                assert not retained, "baseline did not reproduce measured eviction"
            else:
                assert retained, "all genuinely experienced intake roots were lost"
                saved_hashes = transition_hashes(actor, retained)
            persist(actor)
    finally:
        try:
            actor._finish_checkpoint()
        finally:
            actor.close()
    if mode == "candidate":
        subprocess.run([sys.executable, "-B", __file__, "cold", json.dumps(saved_hashes)],
                       check=True, timeout=60)
    report("finished", mode=mode, elapsed_seconds=time.monotonic() - started,
           max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
