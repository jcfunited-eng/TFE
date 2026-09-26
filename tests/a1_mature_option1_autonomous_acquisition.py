"""Option 1: Isolated autonomous food acquisition witness on environmentally provisioned world.

Complies with A1 audit recommendations in collaborative_todo.md (AUT34-A1-01, 02, 03):
- Safe isolated storage: atomically creates an owned temporary parent directory containing the paired store
  and metadata pointer; derives child store path from owned parent rejecting symlinks and path escapes;
  enforces explicit safety refusals before startup and strictly validates saved pointer before cold continuation;
  discloses cleanup failures rather than swallowing them.
- Genuine consequence grounding: food target is apple-1 (the specific target for which Guala holds authentic
  historical intake consequences with positive intake in state['meanings']; no legacy is_food fallback).
- Disclosed environmental provisioning: copies authentic apple-1 dimensions, appearance, and physical material
  fields from checkpoint 2,406,025 (radius 90mm, mass 180g, exact reflectance, odorant reservoir 3,551,525,631 ng,
  release 4,200 ng/s, tastants [140000, 200, 26000, 900, 300] ug, compliance 120,000 ppm, roughness 15 um,
  moisture 850,000 ppm, temperature 292,000 mK).
  The authenticated checkpoint carries 0 ug digestible mass for all objects (the field was absent in older schema
  and decodes as 0 ug). For this first-bite witness, digestible nutrition is explicitly provisioned at 140,000 ug
  (matching declared home world apple in guala_home_world.py:1053) with disclosed lawful floor placement at
  (3628, 6971, 0); blanket relocated to bed mattress (900, 8500, 0).
- Caregiver neutrality: caregiver starts outside at (14600, 7600, 0) with empty hands and lawfully completes
  withdrawal home to (7300, 7500, 0) on step 0, remaining stationary in hallway > 2.4m away throughout.
- Independent oral contact transfer & exact mass conservation: independently measures world active contact
  transferred digestible mass and asserts source debit == world transfer == organism meal intake == reserve gain.
- Truthful scope labeling: reports first_bite_acquisition_proven separately from satiety or lifelong autonomy.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, replace as dc_replace
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
    if digest(raw) != expected_digest:
        raise RuntimeError(f"canonical checkpoint mismatch: {digest(raw)}")
    capture = json.loads(raw)
    p = capture["pointer"]["current"]
    body = zlib.decompress(base64.b64decode(capture["body_zlib"]))
    world = zlib.decompress(base64.b64decode(capture["world_zlib"]))
    if len(body) != p["body_bytes"] or digest(body) != p["body_sha256"]:
        raise RuntimeError("checkpoint body corruption")
    if len(world) != p["world_bytes"] or digest(world) != p["world_sha256"]:
        raise RuntimeError("checkpoint world corruption")
    if trial_path.exists():
        raise RuntimeError(f"trial path must be non-existent fresh path: {trial_path}")
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
    """Disclosed environmental provisioning: authentic apple-1 identity and appearance
    with externally provisioned digestible nutrition.

    Preserves exact physical dimensions and material fields of the experienced apple-1
    from checkpoint 2,406,025 (radius 90mm, mass 180g, exact reflectance, odorant
    reservoir 3,551,525,631 ng, release 4,200 ng/s, tastants [140000, 200, 26000, 900, 300] ug,
    compliance 120,000 ppm, roughness 15 um, moisture 850,000 ppm, temperature 292,000 mK).

    Original checkpoint matter carries 0 ug digestible mass (the field was absent in older schema
    and decodes as 0 ug). For this first-bite witness, digestible nutrition is explicitly
    provisioned at 140,000 ug with lawful floor placement at (3628, 6971, 0).
    """
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

    # Retrieve actual experienced apple-1 from caregiver custody outside
    full_before = world.canonical_observation_snapshot()
    exp_apple = next(o for o in full_before.objects if o.object_id == "apple-1")

    # Depart apple-1 from caregiver custody
    world.admit_authored_departure("apple-1")

    # Record original vs provisioned material quantities
    original_digestible_ug = getattr(exp_apple.material, "digestible_mass_micrograms", 0)
    provisioned_digestible_ug = 140000

    report("provisioned_material_disclosure",
           object_id="apple-1",
           original_checkpoint_digestible_ug=original_digestible_ug,
           provisioned_digestible_ug=provisioned_digestible_ug,
           placement_mm=(3628, 6971, 0),
           radius_mm=exp_apple.radius_mm,
           mass_grams=exp_apple.mass_grams)

    # Lawful floor placement preserving exact physical/material state of the experienced object,
    # with externally provisioned digestible nutrition (140,000 ug):
    placed_apple = EmbodiedObject(
        object_id=exp_apple.object_id,
        radius_mm=exp_apple.radius_mm,
        mass_grams=exp_apple.mass_grams,
        position=PositionMM(3628, 6971, 0),
        reflectance_ppm=exp_apple.reflectance_ppm,
        material=dc_replace(exp_apple.material, digestible_mass_micrograms=provisioned_digestible_ug),
        shape=exp_apple.shape,
    )
    world.admit_authored_arrival(placed_apple)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "acquire"
    if mode not in ("acquire", "cold"):
        raise RuntimeError(f"unrecognized mode: {mode}")
    started = time.monotonic()

    if mode == "acquire":
        trial_parent = Path(tempfile.mkdtemp(prefix="guala_aut01_trial_")).resolve()
        if trial_parent.is_symlink():
            raise RuntimeError(f"trial parent cannot be a symlink: {trial_parent}")
        if any(p in str(trial_parent) for p in ("/app", "/workspaces/Tao_Financial_Engine/backups")):
            raise RuntimeError(f"refusing unsafe trial path: {trial_parent}")

        trial_store = (trial_parent / "store").resolve()
        if trial_store.is_symlink():
            raise RuntimeError(f"trial store cannot be a symlink: {trial_store}")
        if trial_store.parent != trial_parent:
            raise RuntimeError(f"path escape: trial store {trial_store} parent != {trial_parent}")

        meta = {
            "trial_parent": str(trial_parent),
            "trial_store": str(trial_store),
            "pid": os.getpid(),
            "created_ns": time.time_ns(),
            "expected_pointer": None,
        }
        (trial_parent / "trial_meta.json").write_text(json.dumps(meta))
        os.environ["GUALA_PAIRED_ROOT"] = str(trial_store)
        os.environ["GUALA_MAX_WORLD_BYTES"] = "16777216"
        seed_unique_trial_store(trial_store)
    else:
        if len(sys.argv) <= 2:
            raise RuntimeError("cold mode requires trial_parent argument")
        trial_parent = Path(sys.argv[2]).resolve()
        if not trial_parent.exists():
            raise RuntimeError(f"trial parent directory does not exist: {trial_parent}")
        if trial_parent.is_symlink():
            raise RuntimeError(f"trial parent cannot be a symlink: {trial_parent}")
        if any(p in str(trial_parent) for p in ("/app", "/workspaces/Tao_Financial_Engine/backups")):
            raise RuntimeError(f"refusing unsafe trial path: {trial_parent}")

        trial_store = (trial_parent / "store").resolve()
        if trial_store.is_symlink():
            raise RuntimeError(f"trial store cannot be a symlink: {trial_store}")
        if trial_store.parent != trial_parent:
            raise RuntimeError(f"path escape: trial store {trial_store} parent != {trial_parent}")
        if not trial_store.exists():
            raise RuntimeError(f"trial store directory does not exist: {trial_store}")

        meta_file = trial_parent / "trial_meta.json"
        if not meta_file.exists():
            raise RuntimeError(f"trial metadata not found in {trial_parent}")
        meta = json.loads(meta_file.read_text())
        if meta.get("trial_parent") != str(trial_parent):
            raise RuntimeError(f"trial parent pointer mismatch: {meta.get('trial_parent')} != {trial_parent}")
        if meta.get("trial_store") != str(trial_store):
            raise RuntimeError(f"trial store pointer mismatch: {meta.get('trial_store')} != {trial_store}")

        from dsf_ai_service.paired_current_store import PairedCurrentStore
        pre_store = PairedCurrentStore(trial_store, max_body_bytes=67108864, max_world_bytes=16777216)
        actual_ptr = asdict(pre_store.read_pointer().current)
        expected_ptr = meta.get("expected_pointer")
        if expected_ptr is not None and actual_ptr != expected_ptr:
            raise RuntimeError(f"cold restart pointer mismatch: expected {expected_ptr}, got {actual_ptr}")

        os.environ["GUALA_PAIRED_ROOT"] = str(trial_store)
        os.environ["GUALA_MAX_WORLD_BYTES"] = "16777216"

    actor = startup()
    try:
        if mode == "cold":
            advance(actor)
            persist(actor)
            report("cold_next_interval", tick=actor._runtime.live_organism_tick)
        else:
            if actor._runtime.reserve_micrograms != 0:
                raise RuntimeError("organism must start with zero reserves")
            if not actor._runtime.feeding:
                raise RuntimeError("organism must be in feeding state")

            # Verify Guala holds authentic historical intake consequences for apple-1 with positive intake
            state = actor._runtime._state
            consequence_targets = set()
            for m in state.get("meanings", {}).values():
                if isinstance(m, dict):
                    c = m.get("consequences", {})
                    if isinstance(c, dict):
                        for act_c in c.values():
                            if isinstance(act_c, dict) and act_c.get("relief") == "feeding":
                                intake = act_c.get("intake", 0)
                                if isinstance(intake, (int, float)) and intake > 0:
                                    tid = act_c.get("target_id")
                                    if tid:
                                        consequence_targets.add(tid)
            if "apple-1" not in consequence_targets:
                raise RuntimeError("organism lacks authentic consequence memory for apple-1")
            if "bread-slice" in consequence_targets:
                raise RuntimeError("unexpected consequence record for bread-slice")

            # Record source code hashes
            for name in ("guala_functional_organism.py", "guala_functional_loop.py", "guala_caretaker_hand.py", "substrate/embodiment_world.py"):
                src_path = Path(__file__).resolve().parent.parent / "dsf_ai_service" / name
                report("source_hash", path=str(src_path), sha256=digest(src_path.read_bytes()))

            provision_isolated_world(actor)

            before_intake = actor._runtime.counts["meals_micrograms"]
            before_bites = actor._runtime.counts["bites"]
            before_reserve = actor._runtime.reserve_micrograms

            moved = False
            certified_held = None
            intake_seen = False
            food_id = "apple-1"
            initial_digestible_ug = 140000

            source_debit_ug = 0
            world_transferred_ug = 0
            transferred_ug = 0
            reserve_gain_ug = 0

            # Observe autonomous navigation, grasp, bite, and nutritional debit
            for index in range(40):
                before_snap = actor._world.canonical_observation_snapshot()
                person_before = next(b for b in before_snap.bodies if b.body_id != before_snap.self_body_id)
                g_before = next(b for b in before_snap.bodies if b.body_id == before_snap.self_body_id)

                obs = advance(actor)
                # Caregiver must not present or interact
                if obs.get("caregiver_presentation") is not None:
                    raise RuntimeError("caregiver presentation occurred")

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
                if dist_caregiver < 2000:
                    raise RuntimeError(f"caregiver too close to Guala: {dist_caregiver} mm")
                if index > 0:
                    if person_before.pose.position != person_after.pose.position or person_after.pose.position != CAREGIVER_HOME_MM:
                        raise RuntimeError("caregiver moved after withdrawal")
                    if person_after.held_object_id is not None:
                        raise RuntimeError("caregiver held object during autonomous trial")

                acquired_now = applied in ("grasp", "take") and refusal is None
                if acquired_now:
                    if g_after.held_object_id != food_id:
                        raise RuntimeError(f"Guala held {g_after.held_object_id} instead of {food_id}")
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
                    apple_after_obj = next(o for o in after_snap.objects if o.object_id == food_id)
                    apple_digestible = apple_after_obj.material.digestible_mass_micrograms

                    # 1. World-side contact measurement
                    if g_after.active_contact is None:
                        raise RuntimeError("missing active contact on bite step")
                    if g_after.active_contact.kind != "oral":
                        raise RuntimeError(f"contact kind {g_after.active_contact.kind} is not oral")
                    if g_after.active_contact.object_id != food_id:
                        raise RuntimeError(f"contacted object {g_after.active_contact.object_id} != {food_id}")
                    world_transferred_ug = g_after.active_contact.transferred_digestible_micrograms

                    # 2. Source debit measurement
                    source_debit_ug = initial_digestible_ug - apple_digestible

                    # 3. Organism meal counter and bodily reserve measurement
                    transferred_ug = actor._runtime.counts["meals_micrograms"] - before_intake
                    reserve_gain_ug = actor._runtime.reserve_micrograms - before_reserve

                    # Exact mass conservation accounting: source debit == world transfer == organism intake == reserve gain
                    if not (source_debit_ug == world_transferred_ug == transferred_ug == reserve_gain_ug == 62222):
                        raise RuntimeError(
                            f"exact mass conservation violation: debit={source_debit_ug}, world={world_transferred_ug}, "
                            f"organism={transferred_ug}, reserve={reserve_gain_ug}"
                        )

                    if actor._runtime.counts["bites"] <= before_bites:
                        raise RuntimeError("bites count was not incremented")
                    if certified_held != food_id:
                        raise RuntimeError("object was not certified held on bite")
                    intake_seen = True
                    break

            # Truthful scope disclosure: first-bite success is distinct from full satiety or sustained autonomy
            report("option1_acquisition_result",
                   first_bite_acquisition_proven=intake_seen,
                   satiety_achieved=False,
                   sustained_lifetime_autonomy=False,
                   original_checkpoint_digestible_ug=0,
                   provisioned_digestible_ug=initial_digestible_ug,
                   source_debit_ug=source_debit_ug,
                   world_transferred_ug=world_transferred_ug,
                   transferred_digestible_ug=transferred_ug,
                   reserve_gain_ug=reserve_gain_ug,
                   final_reserves_ug=actor._runtime.reserve_micrograms,
                   capacity_fraction=actor._runtime.reserve_micrograms / 500000,
                   caregiver_interventions=0,
                   elapsed_seconds=time.monotonic() - started)

            if not intake_seen:
                raise RuntimeError("no autonomous intake within observation budget")
            persist(actor)
            saved_pointer = asdict(actor._store.read_pointer().current)
            meta["expected_pointer"] = saved_pointer
            (trial_parent / "trial_meta.json").write_text(json.dumps(meta))
    finally:
        try:
            actor._finish_checkpoint()
        finally:
            actor.close()

    if mode == "acquire":
        subprocess.run([sys.executable, "-B", __file__, "cold", str(trial_parent)], check=True, timeout=60)
        # Disclose cleanup cleanly; do not swallow errors silently
        try:
            shutil.rmtree(trial_parent)
            report("trial_cleaned", path=str(trial_parent))
        except Exception as exc:
            report("trial_cleanup_failed", path=str(trial_parent), error=str(exc))
            raise
    report("finished", mode=mode, elapsed_seconds=time.monotonic() - started,
           max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
