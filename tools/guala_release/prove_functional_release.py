"""Release proof for the functional organism on the copied live CURRENT pair.

Warm: the production restore path converts the native CURRENT body (the
retained predecessor) into a functional body at the same identity and tick;
hundreds of beats with the caretaker presenting food, a microphone sound and
a camera frame; state size per beat; checkpoint; fresh-interpreter cold
restore byte-exact; more beats. Networkless; nothing scripted in her.
"""
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import struct
import sys
import time
import zipfile

from dsf_ai_service import lean_production_app as production
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import FunctionalOrganism
from dsf_ai_service.paired_current_store import PairedCurrentStore
from dsf_ai_service.substrate.native_resident_resource_admission import derive_native_resident_resource_admission

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
OUT = Path("/proof")
FOOD = os.environ.get("PROOF_FOOD", "apple-5")
WARM_BEATS = int(os.environ.get("PROOF_WARM_BEATS", "400"))
COLD_BEATS = 40
ACTOR_OCCURRENCES = int(os.environ.get("PROOF_ACTOR_OCCURRENCES", "120"))
PRESENT_AT = (3, 200)
HEAR_AT = 60
SEE_AT = 90


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def emit(value):
    print(json.dumps(value, sort_keys=True, default=str), flush=True)


def restore():
    actor = production._restore_production_actor()
    try:
        actor._verify_restored_authorities()
        runtime, world, pointer = actor._runtime, actor._world, actor._pointer
    finally:
        actor.close()
    return runtime, world, pointer


def checkpoint(runtime, world, store):
    value = runtime.snapshot_lived_state().prepare_checkpoint()
    body, world_bytes = bytes(value.encoded_generation()), bytes(world.encoded_snapshot())
    assert value.organism_tick == runtime.live_organism_tick and sha(body) == value.state_sha256
    runtime.validate_lived_checkpoint(value)
    previous = store.read_pointer()
    store.publish(identity=IDENTITY, organism_tick=value.organism_tick, body=body, world=world_bytes,
                  expected_current_body_sha256=previous.current.body_sha256)
    saved = store.restore()
    assert saved.body == body and saved.world == world_bytes
    return {"tick": runtime.live_organism_tick, "body_sha": sha(body), "body_bytes": len(body), "world_sha": sha(world_bytes), "world_bytes": len(world_bytes)}


def world_food(world):
    snap = world.observation_snapshot()
    return {
        "bodies": [(b.body_id, b.held_object_id, (b.pose.position.x, b.pose.position.y, b.pose.heading_millidegrees)) for b in snap.bodies],
        "apples": [(o.object_id, o.held_by_body_id, None if o.material is None else sum(o.material.tastant_mass_micrograms))
                   for o in snap.objects if o.object_id.startswith("apple")],
        "room": snap.room_id,
    }


def tone(frequency_hz, samples=4000):
    return struct.pack(f"<{samples}h", *(int(9000 * math.sin(2 * math.pi * frequency_hz * i / 16000)) for i in range(samples)))


def occurrences():
    ordinary = production._physical_occurrence(production.OccurrenceBody(kind="unattended"))
    present = production._physical_occurrence(production.OccurrenceBody(
        kind="sensory", payload=production.SensoryBody(source="caretaker-food", present_food=FOOD)))
    import base64
    hear = production._physical_occurrence(production.OccurrenceBody(
        kind="sensory", payload=production.SensoryBody(source="microphone", pcm_s16le_base64=base64.b64encode(tone(370)).decode("ascii"))))
    frame = tuple((index * 7) % 256 for index in range(14805))
    see = production._physical_occurrence(production.OccurrenceBody(
        kind="sensory", payload=production.SensoryBody(source="camera", retina_rgb_u8=frame)))
    return ordinary, present, hear, see


def step(runtime, world, occurrence, label):
    before = runtime.live_organism_tick
    feeding = bool(runtime.feeding)  # her own law at this beat, hysteresis included
    started = time.perf_counter()
    result = FunctionalPhysicalLoop().settle(runtime, world, occurrence)
    elapsed = time.perf_counter() - started
    assert result.native_interval_count == 1 and runtime.live_organism_tick == before + 1
    o = result.observation
    d = o["metabolic_need_reserve_deficit"]
    row = {"label": label, "tick": runtime.live_organism_tick, "seconds": round(elapsed, 3), "act": o["her_act"], "reason": o["act_reason"], "feeding": feeding,
           "room": o["embodiment"]["room_id"], "said_text": o.get("said"), "withdrawal": None if o.get("caregiver_withdrawal") is None else (o["caregiver_withdrawal"]["set_down"], o["caregiver_withdrawal"]["home"]),
           "applied": o["requested_world_action"], "refusal": o["world_action_refusal"], "deficit": d[0] / d[1],
           "intake_ug": o["real_nutrition_intake_zeptojoules"] // 17_000_000_000_000_000_000, "seen": o["seen"][:4],
           "novel": o["kernel_novel"], "gates": o["dsf_delivery_count"], "motion": o["actual_root_motion"],
           "said": o["said_drive"], "heard": o["external_heard_sample_count"], "camera_sites": o["external_retinal_site_count"],
           "presentation": None if o["caregiver_presentation"] is None else o["caregiver_presentation"]["presented"],
           "body_bytes": len(runtime.encoded()), "world_bytes": len(world.encoded_snapshot()), "spoke": result.pressure is not None,
           "ear": (o.get("her_ear") or {}).get("closed", []), "events": (o.get("her_counts") or {}).get("events"),
           "own": (o.get("her_ear") or {}).get("own_closed", []), "moments": (o.get("her_counts") or {}).get("moments")}
    return row


def main():
    mode, expected_revision = sys.argv[1:]
    assert os.environ["GIT_SHA"] == expected_revision
    assert {k: v for k, v in os.environ.items() if k.startswith("GUALA_")} == {
        "GUALA_PAIRED_ROOT": "/proof/paired", "GUALA_MAX_WORLD_BYTES": "16777216"}
    limit = derive_native_resident_resource_admission(OUT)
    store = PairedCurrentStore(OUT / "paired", max_body_bytes=limit.max_envelope_bytes, max_world_bytes=16777216)
    ordinary, present, hear, see = occurrences()
    if mode == "warm":
        assert not (OUT / "paired").exists()
        with zipfile.ZipFile("/current.zip") as archive:
            assert sorted(archive.namelist()) == ["body.glorun.gz", "pointer.json", "world.json"]
            initial = json.loads(archive.read("pointer.json"))["current"]
            assert initial["identity"] == IDENTITY
            body = gzip.decompress(archive.read("body.glorun.gz"))
            world_bytes = archive.read("world.json")
        for kind, raw in (("body", body), ("world", world_bytes)):
            assert len(raw) == initial[kind + "_bytes"] and sha(raw) == initial[kind + "_sha256"]
        store.publish(identity=IDENTITY, organism_tick=initial["organism_tick"], body=body, world=world_bytes, expected_current_body_sha256=None)
        captured_body_sha = sha(body)
        captured_functional = body.startswith(b"GLFUNC01")
        del body, world_bytes
        # The actor itself, as production runs it (2026-09-14: the outage lived
        # only in the actor's own path): restore, its own unattended beats, the
        # caretaker presenting food every sixth occurrence while she handles
        # things, then a clean close with its final checkpoint.
        actor = production._restore_production_actor()
        actor._verify_restored_authorities()
        actor.start()
        actor_start = actor.observation()["live_tick"]
        assert actor_start == initial["organism_tick"]
        for index in range(ACTOR_OCCURRENCES):
            actor.offer(present if index % 6 == 0 else ordinary).result(timeout=120)
            state = actor.observation()
            assert state["available"], "the actor died in its own path: " + repr(getattr(actor, "_fatal", None))
            time.sleep(0.02)
        actor_end = actor.observation()["live_tick"]
        actor_fatal = getattr(actor, "_fatal", None)
        actor.close()
        assert actor_fatal is None and actor_end >= actor_start + ACTOR_OCCURRENCES, (actor_start, actor_end, actor_fatal)
        emit({"actor_stage": {"start_tick": actor_start, "end_tick": actor_end, "offered": ACTOR_OCCURRENCES, "presentations": (ACTOR_OCCURRENCES + 5) // 6}})
        started = time.perf_counter()
        runtime, world, pointer = restore()
        restore_seconds = time.perf_counter() - started
        assert isinstance(runtime, FunctionalOrganism) and runtime.live_organism_tick == actor_end == pointer.current.organism_tick
        # A native body was converted (or an older functional body migrated) on
        # the actor's restore; the actor's own checkpoints have since moved the
        # pair on, so the captured body is no longer CURRENT.
        assert pointer.current.body_sha256 != captured_body_sha
        assert runtime._state["voice_version"] >= 2  # the actor stage has spoken already; the old airway's sounds are gone either way (3: syllables valued by worth)
        emit({"captured_functional": captured_functional, "restore_seconds": round(restore_seconds, 3), "tick": runtime.live_organism_tick,
              "functional_body_bytes": pointer.current.body_bytes, "captured_body_bytes": initial["body_bytes"], "world_before": world_food(world)})
        feeding_at_start = bool(runtime.feeding)  # her own law, hysteresis included
        rows = []
        for index in range(WARM_BEATS):
            occurrence = present if index in PRESENT_AT else hear if index == HEAR_AT else see if index == SEE_AT else ordinary
            rows.append(step(runtime, world, occurrence, f"beat-{index}"))
            if index < 12 or index % 25 == 0 or rows[-1]["intake_ug"] or rows[-1]["presentation"] is not None or rows[-1]["refusal"]:
                emit(rows[-1])
        emit({"world_after": world_food(world)})
        fed = [r for r in rows if r["intake_ug"] > 0]
        assert any(r["presentation"] is not None for r in rows), "the caregiver never came to present"  # presented or refused; the actor stage may have fed her first
        acts = {}
        for r in rows:
            acts[r["act"]] = acts.get(r["act"], 0) + 1
        hungry_at_start = feeding_at_start
        # Her feeding law, beat by beat: every bite happened while she was
        # feeding; a presentation made while she was feeding was eaten from
        # within the next beats; a presentation made while sated was not.
        assert all(r["feeding"] for r in rows if r["intake_ug"] > 0), "a sated organism bit the food"
        presented_while_feeding = [r for r in rows if r["presentation"] and r["feeding"]]
        if presented_while_feeding:
            assert fed, "no real intake reached her after the caregiver held out the food while she was feeding"
        else:
            assert not fed, "she ate although no food was offered while she was feeding"
        assert sum(acts.get(name, 0) for name in ("step", "toward_food", "toward_thing", "toward_door")) >= 1, "she never moved"
        assert any(r["spoke"] for r in rows), "she never spoke"
        # Her acts come from her record: every chosen act names the structure it
        # was chosen under, and the record grows over the run.
        chosen = [r for r in rows if r["act"] != "bite"]
        assert chosen and all((r["reason"] or "").startswith("structure ") for r in chosen), "an act was not chosen from her record"
        assert runtime.counts["structures"] >= 5, runtime.counts
        assert any(r["heard"] for r in rows), "the heard call never reached her"
        if any(r["presentation"] for r in rows):  # a meal was presented in this stage: the caregiver goes home after it
            assert any(r["withdrawal"] is not None and r["withdrawal"][1] for r in rows), "the caregiver never withdrew home after the meal"
        assert any(r["camera_sites"] == 4935 for r in rows)
        saved = checkpoint(runtime, world, store)
        receipt = {"initial": initial, "saved": saved, "revision": expected_revision, "rows": rows, "acts": acts, "hungry_at_start": hungry_at_start,
                   "first_fed_tick": fed[0]["tick"] if fed else None, "fed_beats": len(fed), "total_intake_ug": sum(r["intake_ug"] for r in rows),
                   "deficit_first": rows[0]["deficit"], "deficit_min": min(r["deficit"] for r in rows), "deficit_last": rows[-1]["deficit"],
                   "worst_seconds": max(r["seconds"] for r in rows), "mean_seconds": round(sum(r["seconds"] for r in rows) / len(rows), 4),
                   "body_bytes_max": max(r["body_bytes"] for r in rows), "world_bytes_max": max(r["world_bytes"] for r in rows),
                   "novel_structures": sum(1 for r in rows if r["novel"]), "gates_total": sum(r["gates"] for r in rows),
                   "rooms": sorted({r["room"] for r in rows}), "syllables": sum(1 for r in rows if r["spoke"]),
                   "events_closed": sum(len(r["ear"]) for r in rows), "events_store": rows[-1]["events"],
                   "own_events_closed": sum(len(r["own"]) for r in rows), "moments_store": rows[-1]["moments"],
                   "withdrawals": [r["withdrawal"] for r in rows if r["withdrawal"] is not None],
                   "restore_seconds": round(restore_seconds, 3), "world_after": world_food(world), "captured_functional": captured_functional,
                   "warm_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        (OUT / "functional-warm.json").write_text(json.dumps(receipt, sort_keys=True, default=str))
        emit({"functional_warm_complete": True, **saved, "acts": acts})
        os.execv(sys.executable, [sys.executable, __file__, "cold", expected_revision])
    assert mode == "cold"
    receipt = json.loads((OUT / "functional-warm.json").read_text())
    saved = receipt["saved"]
    started = time.perf_counter()
    runtime, world, pointer = restore()
    cold_restore_seconds = time.perf_counter() - started
    assert isinstance(runtime, FunctionalOrganism) and runtime.live_organism_tick == saved["tick"]
    assert sha(runtime.encoded()) == saved["body_sha"] and sha(bytes(world.encoded_snapshot())) == saved["world_sha"]
    rows = [step(runtime, world, ordinary, f"post-cold-{index}") for index in range(COLD_BEATS)]
    for row in rows[:3]:
        emit(row)
    successor = checkpoint(runtime, world, store)
    receipt.update(cold_restart_exact=True, cold_restore_seconds=round(cold_restore_seconds, 3), post_cold=rows, successor=successor,
                   world_post_cold=world_food(world), cold_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (OUT / "functional-result.json").write_text(json.dumps(receipt, sort_keys=True, default=str))
    emit({"functional_path_pass": True, **successor})


if __name__ == "__main__":
    main()
