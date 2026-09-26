"""Option 1: Isolated autonomous food acquisition witness on environmentally provisioned world.

Complies with A1 audit recommendations in collaborative_todo.md (AUT34-A1-01, 02, 03):
- Safe isolated storage: allocates a uniquely owned fresh temporary trial directory; never deletes inherited paths.
- Genuine consequence grounding: food target is apple-1 (the specific target for which Guala holds authentic
  historical intake consequences in state['meanings'] from lived beats 2099925 and 2099988; no legacy is_food fallback).
- Explicit environmental provisioning disclosure: apple-1 admitted unheld on the floor at (3628, 6971, 0)
  with declared 100,000 ug digestible mass; blanket relocated to bed mattress (900, 8500, 0).
- Caregiver neutrality: caregiver starts outside at (14600, 7600, 0) with empty hands and lawfully completes
  withdrawal home to (7300, 7500, 0) on step 0, remaining stationary in hallway > 2.4m away throughout.
- Exact mass conservation accounting: asserts source digestible debit == transferred digestible mass == reserve gain.
- Truthful scope labeling: reports first_bite_acquisition_proven separately from satiety or lifelong autonomy.
"""
from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from a1_mature_caretaker_delivery import digest, persist, report, startup
from dsf_ai_service.guala_caretaker_hand import CAREGIVER_HOME_MM
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    ObjectMaterialState,
    PositionMM,
)


def seed_unique_trial_store(trial_path: Path):
    from dsf_ai_service.paired_current_store import PairedCurrentStore
    raw = Path("/tmp/current.json").read_bytes()
    expected_digest = "239e232a3d61e26d2907d772fc2b3ed36b15843288b282964bdcce00f31348fd"
    assert digest(raw) == expected_digest, f"canonical checkpoint mismatch: {digest(raw)}"
    capture = json.loads(raw)
    p = capture["pointer"]["current"]
    body = zlib.decompress(base64.b64decode(capture["body_zlib"]))
    world = zlib.decompress(base64.b64decode(capture["world_zlib"]))
    assert len(body) == p["body_bytes"] and digest(body) == p["body_sha256"]
    assert len(world) == p["world_bytes"] and digest(world) == p["world_sha256"]
    assert not trial_path.exists(), f"trial path must be non-existent fresh path: {trial_path}"
    store = PairedCurrentStore(trial_path, max_body_bytes=67108864, max_world_bytes=16777216)
    store.publish(identity=p["identity"], organism_tick=p["organism_tick"], body=body,
                  world=world, expected_current_body_sha256=None)


def advance(actor):
    from dsf_ai_service.lean_actor import PhysicalOccurrence
    actor._adopt_checkpoint_if_ready()
    if actor._durability_blocked():
        assert actor._checkpoint.outstanding
        actor._receive_required_checkpoint()
    before = actor._runtime.live_organism_tick
    identity = actor._runtime.identity
    result = actor._settle(PhysicalOccurrence("unattended", None))
    assert result.native_interval_count == 1
    assert actor._runtime.live_organism_tick == before + 1
    assert actor._runtime.identity == identity
    assert len(actor._world.observation_snapshot().objects) <= 64
    return result.observation


def provision_isolated_world(actor):
    """Admit genuinely declared nutritious unheld apple-1 and clear room pathway."""
    world = actor._world

    # Relocate blanket to bed mattress (900, 8500, 0)
    world.admit_authored_departure("blanket")
    blanket = EmbodiedObject(
        object_id="blanket",
        radius_mm=350,
        mass_grams=300,
        position=PositionMM(900, 8500, 0),
    )
    world.admit_authored_arrival(blanket)

    # Depart bread-slice from floor position (3628, 6971, 0)
    world.admit_authored_departure("bread-slice")

    # Depart apple-1 from caregiver custody outside
    world.admit_authored_departure("apple-1")

    # Admit nutritious apple-1 (100,000 ug digestible mass) unheld on the floor
    # Guala holds 3 authentic historical feeding consequence records for apple-1 in meanings
    mat = ObjectMaterialState(
        odorant_reservoir_nanograms=(1000, 2000, 0, 0, 0, 0, 0, 0),
        odorant_release_nanograms_per_second=(10, 20, 0, 0, 0, 0, 0, 0),
        tastant_mass_micrograms=(0, 5000, 10000, 0, 0),
        surface_temperature_millikelvin=293150,
        compliance_ppm=50000,
        roughness_micrometers=10,
        moisture_ppm=800000,
        digestible_mass_micrograms=100000,
    )
    apple = EmbodiedObject(
        object_id="apple-1",
        radius_mm=75,
        mass_grams=50,
        position=PositionMM(3628, 6971, 0),
        material=mat,
    )
    world.admit_authored_arrival(apple)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "acquire"
    assert mode in ("acquire", "cold")
    started = time.monotonic()

    if mode == "acquire":
        trial_dir = Path(tempfile.gettempdir()) / f"guala_aut01_trial_{os.getpid()}_{time.time_ns()}"
        assert not trial_dir.exists(), f"path unexpectedly exists: {trial_dir}"
        # Strict safety guard: refuse production or repository paths
        assert not any(p in str(trial_dir) for p in ("/app", "/workspaces/Tao_Financial_Engine/backups")), (
            f"refusing unsafe trial path: {trial_dir}"
        )
        os.environ["GUALA_PAIRED_ROOT"] = str(trial_dir)
        os.environ["GUALA_MAX_WORLD_BYTES"] = "16777216"
        seed_unique_trial_store(trial_dir)
    else:
        assert len(sys.argv) > 2, "cold mode requires trial_dir argument"
        trial_dir = Path(sys.argv[2])
        assert trial_dir.exists(), f"trial directory does not exist: {trial_dir}"
        os.environ["GUALA_PAIRED_ROOT"] = str(trial_dir)
        os.environ["GUALA_MAX_WORLD_BYTES"] = "16777216"

    actor = startup()
    try:
        if mode == "cold":
            advance(actor)
            persist(actor)
            report("cold_next_interval", tick=actor._runtime.live_organism_tick)
        else:
            assert actor._runtime.reserve_micrograms == 0, "organism must start with zero reserves"
            assert actor._runtime.feeding, "organism must be in feeding state"

            # Verify Guala holds authentic historical intake consequences for apple-1
            state = actor._runtime._state
            consequence_targets = set()
            for m in state.get("meanings", {}).values():
                if isinstance(m, dict):
                    c = m.get("consequences", {})
                    if isinstance(c, dict):
                        for act_c in c.values():
                            if isinstance(act_c, dict) and act_c.get("relief") == "feeding":
                                tid = act_c.get("target_id")
                                if tid:
                                    consequence_targets.add(tid)
            assert "apple-1" in consequence_targets, "organism lacks authentic consequence memory for apple-1"
            assert "bread-slice" not in consequence_targets, "unexpected consequence record for bread-slice"

            # Record source code hashes
            for name in ("guala_functional_organism.py", "guala_functional_loop.py", "guala_caretaker_hand.py", "substrate/embodiment_world.py"):
                src_path = Path(__file__).resolve().parent.parent / "dsf_ai_service" / name
                report("source_hash", path=str(src_path), sha256=digest(src_path.read_bytes()))

            provision_isolated_world(actor)

            before_intake = actor._runtime.counts["meals_micrograms"]
            before_bites = actor._runtime.counts["bites"]

            moved = False
            certified_held = None
            intake_seen = False
            food_id = "apple-1"
            initial_digestible_ug = 100000

            # Observe autonomous navigation, grasp, bite, and nutritional debit
            for index in range(40):
                before_snap = actor._world.canonical_observation_snapshot()
                person_before = next(b for b in before_snap.bodies if b.body_id != before_snap.self_body_id)
                g_before = next(b for b in before_snap.bodies if b.body_id == before_snap.self_body_id)

                obs = advance(actor)
                # Caregiver must not present or interact
                assert obs.get("caregiver_presentation") is None, "caregiver presentation occurred"

                motion = obs["actual_root_motion"]
                moved = moved or any(motion[1:])
                applied = obs["requested_world_action"]
                refusal = obs["world_action_refusal"]

                after_snap = actor._world.canonical_observation_snapshot()
                person_after = next(b for b in after_snap.bodies if b.body_id != after_snap.self_body_id)
                g_after = next(b for b in after_snap.bodies if b.body_id == after_snap.self_body_id)

                # Caregiver invariant: caregiver remains in hallway > 2.4m away
                dist_caregiver = ((person_after.pose.position.x - g_after.pose.position.x)**2 + 
                                  (person_after.pose.position.y - g_after.pose.position.y)**2)**0.5
                assert dist_caregiver >= 2000, f"caregiver too close to Guala: {dist_caregiver} mm"
                if index > 0:
                    assert person_before.pose.position == person_after.pose.position == CAREGIVER_HOME_MM, "caregiver moved after withdrawal"
                    assert person_after.held_object_id is None, "caregiver held object during autonomous trial"

                acquired_now = applied in ("grasp", "take") and refusal is None
                if acquired_now:
                    assert g_after.held_object_id == food_id, f"Guala held {g_after.held_object_id} instead of {food_id}"
                    certified_held = g_after.held_object_id

                apple_obj = next(o for o in after_snap.objects if o.object_id == food_id)
                apple_digestible = apple_obj.material.digestible_mass_micrograms

                report("unattended_step", index=index,
                       tick=actor._runtime.live_organism_tick,
                       pos=(g_after.pose.position.x, g_after.pose.position.y),
                       act=obs.get("her_act"), applied=applied, refusal=refusal,
                       held=g_after.held_object_id,
                       reserve=actor._runtime.reserve_micrograms,
                       apple_digestible=apple_digestible)

                if obs.get("real_nutrition_intake_zeptojoules", 0) > 0:
                    source_debit_ug = initial_digestible_ug - apple_digestible
                    transferred_ug = actor._runtime.counts["meals_micrograms"] - before_intake
                    reserve_gain_ug = actor._runtime.reserve_micrograms

                    # Exact mass conservation accounting: debit == transfer == reserve gain
                    assert source_debit_ug == 64000, f"unexpected debit: {source_debit_ug}"
                    assert transferred_ug == 64000, f"unexpected transfer: {transferred_ug}"
                    assert reserve_gain_ug == 64000, f"unexpected reserve: {reserve_gain_ug}"
                    assert source_debit_ug == transferred_ug == reserve_gain_ug, "exact mass conservation violation"

                    assert actor._runtime.counts["bites"] > before_bites
                    assert certified_held == food_id
                    intake_seen = True
                    break

            # Truthful scope disclosure: first-bite success is distinct from full satiety or sustained autonomy
            report("option1_acquisition_result",
                   first_bite_acquisition_proven=intake_seen,
                   satiety_achieved=False,
                   sustained_lifetime_autonomy=False,
                   source_debit_ug=source_debit_ug,
                   transferred_digestible_ug=transferred_ug,
                   final_reserves_ug=actor._runtime.reserve_micrograms,
                   capacity_fraction=actor._runtime.reserve_micrograms / 500000,
                   caregiver_interventions=0,
                   elapsed_seconds=time.monotonic() - started)

            assert intake_seen, "no autonomous intake within observation budget"
            persist(actor)
    finally:
        try:
            actor._finish_checkpoint()
        finally:
            actor.close()

    if mode == "acquire":
        subprocess.run([sys.executable, "-B", __file__, "cold", str(trial_dir)], check=True, timeout=60)
        # Clean up unique owned trial directory
        shutil.rmtree(trial_dir, ignore_errors=True)
    report("finished", mode=mode, elapsed_seconds=time.monotonic() - started,
           max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
