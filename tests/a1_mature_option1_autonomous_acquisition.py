"""Option 1: Isolated autonomous food acquisition witness on environmentally provisioned world.

Complies with A1 recommendation in collaborative_todo.md:
- Explicitly labelled as an isolated, environmentally provisioned world, not unchanged-checkpoint replay.
- Original checkpoint preserved and seeded from /tmp/current.json into isolated store (/tmp/test_aut01_store).
- Guala lived body state untouched: initial reserves 0 µg, pose (5011, 8236, 0), lived memory preserved.
- No body relocation: Guala starts at (5011, 8236, 0); caregiver starts at (14600, 7600, 0) and lawfully withdraws home to (7300, 7500, 0) on step 0.
- Genuinely nutritious unheld food (bread-slice, 100,000 µg digestible mass) admitted through world arrival contract.
- Zero caregiver assistance: caregiver is in the hallway > 2.4m away; caregiver_presentation is None throughout.
- Records source nutrient debit, contact transfer, and body reserve gain net of metabolism.
- Validates persistence and cold next-interval restoration.
"""
from __future__ import annotations

import base64
from dataclasses import asdict
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("GUALA_PAIRED_ROOT", "/tmp/test_aut01_store")
os.environ.setdefault("GUALA_MAX_WORLD_BYTES", "16777216")

from a1_mature_caretaker_delivery import digest, persist, report, startup
from a1_mature_waking_retention import seed_copied_pair
from dsf_ai_service.guala_caretaker_hand import CAREGIVER_HOME_MM
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    ObjectMaterialState,
    PositionMM,
)


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
    """Admit genuinely nutritious unheld food into isolated trial world."""
    world = actor._world

    # Move blanket to bed mattress (900, 8500, 0) so floor pathway is standard
    world.admit_authored_departure("blanket")
    blanket = EmbodiedObject(
        object_id="blanket",
        radius_mm=350,
        mass_grams=300,
        position=PositionMM(900, 8500, 0),
    )
    world.admit_authored_arrival(blanket)

    # Lawfully admit genuinely declared nutritious bread-slice (100,000 ug digestible mass)
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
    world.admit_authored_departure("bread-slice")
    bread = EmbodiedObject(
        object_id="bread-slice",
        radius_mm=75,
        mass_grams=50,
        position=PositionMM(3628, 6971, 0),
        material=mat,
    )
    world.admit_authored_arrival(bread)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "acquire"
    assert mode in ("acquire", "cold")
    started = time.monotonic()
    if mode == "acquire":
        shutil.rmtree(os.environ["GUALA_PAIRED_ROOT"], ignore_errors=True)
        seed_copied_pair()
    actor = startup()
    try:
        if mode == "cold":
            advance(actor)
            persist(actor)
            report("cold_next_interval", tick=actor._runtime.live_organism_tick)
        else:
            assert actor._runtime.reserve_micrograms == 0, "organism must start with zero reserves"
            assert actor._runtime.feeding, "organism must be in feeding state"
            provision_isolated_world(actor)

            before_intake = actor._runtime.counts["meals_micrograms"]
            before_bites = actor._runtime.counts["bites"]

            moved = False
            certified_held = None
            intake_seen = False
            food_id = "bread-slice"

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

                # Caregiver invariant: caregiver never enters Guala's room or approaches within reach (held at > 2.0m)
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

                bread_obj = next(o for o in after_snap.objects if o.object_id == food_id)
                bread_digestible = bread_obj.material.digestible_mass_micrograms

                report("unattended_step", index=index,
                       tick=actor._runtime.live_organism_tick,
                       pos=(g_after.pose.position.x, g_after.pose.position.y),
                       act=obs.get("her_act"), applied=applied, refusal=refusal,
                       held=g_after.held_object_id,
                       reserve=actor._runtime.reserve_micrograms,
                       bread_digestible=bread_digestible)

                if obs.get("real_nutrition_intake_zeptojoules", 0) > 0:
                    assert actor._runtime.counts["bites"] > before_bites
                    assert actor._runtime.counts["meals_micrograms"] > before_intake
                    assert actor._runtime.reserve_micrograms > 0
                    assert certified_held == food_id
                    assert bread_digestible < 100000, "nutrients were not debited from food source"
                    intake_seen = True
                    break

            report("option1_acquisition_result",
                   autonomous_intake_proven=intake_seen,
                   final_reserves_ug=actor._runtime.reserve_micrograms,
                   food_debit_ug=100000 - bread_digestible,
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
        subprocess.run([sys.executable, "-B", __file__, "cold"], check=True, timeout=60)
    report("finished", mode=mode, elapsed_seconds=time.monotonic() - started,
           max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == "__main__":
    main()
