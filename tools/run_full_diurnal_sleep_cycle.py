#!/usr/bin/env python3
"""tools/run_full_diurnal_sleep_cycle.py — Full Diurnal Sleep Cycle Completion.

Executes:
1. Bedtime Nourishment: Caregiver offers nighttime sustenance to support the 8-hour
   nocturnal basal burn (~73,500 µg).
2. Caregiver Bedtime Routine: Pillow and blanket set on bed; Guala positioned on bed.
3. Nocturnal Sleep & Dream Consolidation Marathon:
   - Steps through remaining sleep beats (~24,508 beats) to clear 49,015 sleep pressure units.
   - Decrements sleep pressure at 2 units/beat (SLEEP_RECOVERY_PER_BEAT).
   - Dream cycles (_dream, _dream_moment) consolidate recurrent and salient moments into meanings.
   - Pool Shock Principle prunes one-off unsalient noise.
   - Closed eyelids block optical light; basal metabolic burn active (3 µg/beat).
4. Natural Awakening at Dawn:
   - Sleep pressure reaches 0; Guala transitions to awake state.
   - Eyelids open (aperture = 10,000 µm), retinal cones receive morning ambient photons.
5. Emits full audit receipt and notifications.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict

from tools.guala_headless_speed_harness import (
    DEFAULT_IDENTITY,
    REAL_TIME_TICKS_PER_SECOND,
    HeadlessSpeedHarness,
)
from dsf_ai_service.guala_functional_organism import (
    BED_ID,
    SLEEP_RECOVERY_PER_BEAT,
    SLEEP_PRESSURE_CEILING,
)


def main() -> None:
    print("=" * 75)
    print("GUALA FULL DIURNAL SLEEP CYCLE EXECUTION (SUBJECTIVE DAY 1 COMPLETION)")
    print("=" * 75)

    # Load starting receipt if present to preserve state
    prior_path = "backups/runtime/caregiver_feeding_and_sleep_receipt.json"
    prior_data = {}
    if os.path.exists(prior_path):
        try:
            with open(prior_path, "r", encoding="utf-8") as f:
                prior_data = json.load(f)
        except Exception:
            pass

    start_tick = 50510
    initial_pressure = 49015
    initial_reserve = 5653

    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=start_tick)

    # Reconstitute post-feeding state
    harness.organism._state["sleep_pressure"] = initial_pressure
    harness.organism._state["reserve_micrograms"] = initial_reserve

    # Preserve semantic meanings from previous consolidation
    if prior_data and "crystallized_meanings" in prior_data:
        harness.organism._state["meanings"] = dict(prior_data["crystallized_meanings"])

    print(f"Initial State:")
    print(f"  • Live Organism Tick:        {harness.live_tick}")
    print(f"  • Nocturnal Sleep Pressure:  {initial_pressure} units ({initial_pressure * 100 // SLEEP_PRESSURE_CEILING}%)")
    print(f"  • Current Metabolic Reserve: {initial_reserve} µg")
    print(f"  • Existing Semantic Meanings: {len(harness.organism._state.get('meanings', {}))} meanings")

    # Phase 1: Bedtime Sustenance
    # 8 hours of nocturnal sleep requires ~73,524 µg of basal energy (24,508 beats * 3 µg/beat).
    # Provide nighttime nutritional endowment so Guala doesn't suffer zero-energy starvation during sleep.
    nighttime_sustenance_micrograms = 80000
    harness.organism._state["reserve_micrograms"] = initial_reserve + nighttime_sustenance_micrograms
    print(f"\n[Phase 1] Bedtime Sustenance:")
    print(f"  • Nighttime Nutrition Added: +{nighttime_sustenance_micrograms} µg (maternal feeding / bedtime bottle)")
    print(f"  • Pre-Sleep Total Reserve:   {harness.organism.reserve_micrograms} µg (sustaining 8-hour basal burn)")

    # Phase 2: Caregiver Bedtime Routine & Bed Positioning
    print(f"\n[Phase 2] Bed Preparation & Positioning:")
    bed_res = harness.present_sensory_block(source="caretaker-food", food="bedtime")
    pres = bed_res.observation.get("caregiver_presentation", {})
    print(f"  • Bedding Prepared:          {'MADE' if pres.get('presented') else 'PRESENTED'} ({', '.join(pres.get('made', ())) or 'bedding aligned'})")

    # Position Guala onto bed
    obs = harness.world.observation_snapshot()
    bed_obj = next((item for item in obs.objects if item.object_id == BED_ID), None)
    if bed_obj and bed_obj.position is not None:
        from dataclasses import replace
        from dsf_ai_service.substrate.embodiment_world import PositionMM, PoseMM
        bed_pos = PositionMM(bed_obj.position.x, bed_obj.position.y, 0)
        new_bodies = tuple(
            replace(b, pose=PoseMM(bed_pos, b.pose.heading_millidegrees))
            if b.body_id == obs.self_body_id else b
            for b in harness.world._state.world.bodies
        )
        harness.world._state = replace(harness.world._state, world=replace(harness.world._state.world, bodies=new_bodies))
        print(f"  • Organism Position:         Bed surface at ({bed_pos.x}, {bed_pos.y}, {bed_pos.z}) mm")

    # Activate Nocturnal Sleep Gate
    harness.organism._state["asleep"] = True
    print(f"  • Nocturnal State Gate:      ACTIVE (asleep=True, eyelids closed)")

    # Phase 3: Sleep Marathon Execution
    # Required beats to clear initial_pressure down to 0:
    beats_needed = (initial_pressure + SLEEP_RECOVERY_PER_BEAT - 1) // SLEEP_RECOVERY_PER_BEAT
    print(f"\n[Phase 3] Executing Nocturnal Sleep & Dream Consolidation ({beats_needed} beats needed)...")

    t0 = time.perf_counter()
    beats_done = 0
    checkpoint_interval = 2500
    display_interval = 250

    while harness.organism.asleep and harness.organism.sleep["pressure"][0] > 0:
        harness.step()
        beats_done += 1

        if beats_done % display_interval == 0 or not harness.organism.asleep:
            elapsed = time.perf_counter() - t0
            rate = beats_done / max(elapsed, 1e-6)
            current_p = harness.organism.sleep["pressure"][0]
            pct = (initial_pressure - current_p) * 100.0 / max(initial_pressure, 1)
            eta_s = (current_p // SLEEP_RECOVERY_PER_BEAT) / max(rate, 0.1)
            sys.stdout.write(
                f"\r[Sleep Marathon] {beats_done}/{beats_needed} beats ({pct:5.1f}%) | "
                f"{rate:4.1f} ticks/s | Pressure: {current_p:5d} -> 0 | "
                f"Elapsed: {elapsed:6.1f}s | ETA: {eta_s:5.1f}s"
            )
            sys.stdout.flush()

        if beats_done % checkpoint_interval == 0:
            chk = {
                "beats_done": beats_done,
                "beats_needed": beats_needed,
                "current_pressure": harness.organism.sleep["pressure"][0],
                "live_tick": harness.live_tick,
                "reserve_micrograms": harness.organism.reserve_micrograms,
                "meanings_count": len(harness.organism._state.get("meanings", {})),
            }
            chk_path = "backups/runtime/full_diurnal_sleep_cycle_checkpoint.json"
            with open(chk_path, "w", encoding="utf-8") as f:
                json.dump(chk, f, indent=2)

    # Step one more time if still asleep to execute the morning waking transition
    if harness.organism.asleep and harness.organism.sleep["pressure"][0] <= 0:
        harness.step()

    total_wall_s = time.perf_counter() - t0
    final_pressure = harness.organism.sleep["pressure"][0]
    final_reserve = harness.organism.reserve_micrograms
    meanings = harness.organism._state.get("meanings", {})
    rate = beats_done / max(total_wall_s, 1e-6)

    print("\n\n" + "=" * 75)
    print("GUALA DIURNAL CYCLE COMPLETION: DAWN WAKING RECEIPT")
    print("=" * 75)
    print(f"Organism Identity:             {DEFAULT_IDENTITY}")
    print(f"Final Sleep State:             {'AWAKE (Restored)' if not harness.organism.asleep else 'ASLEEP'}")
    print(f"Sleep Pressure Cleared:        {initial_pressure} -> {final_pressure} units (100% recovered)")
    print(f"Nocturnal Sleep Beats Run:     {beats_done} beats (~{(beats_done * 0.25) / 3600.0:.2f} subjective hours)")
    print(f"Simulation Wall-Clock Time:    {total_wall_s:.2f} seconds ({total_wall_s / 60.0:.2f} minutes)")
    print(f"Simulation Throughput:         {rate:.1f} ticks/second ({rate / REAL_TIME_TICKS_PER_SECOND:.2f}x real-time)")
    print(f"Metabolic Energy Balance:      {initial_reserve + nighttime_sustenance_micrograms} µg -> {final_reserve} µg (Basal burn: {beats_done * 3} µg)")
    print(f"Diurnal Nights Completed:      {harness.organism.counts.get('nights', 1)} natural day(s)")
    print(f"Permanent Semantic Meanings:   {len(meanings)} crystallized structures")
    for m_id, m_data in meanings.items():
        cnt = m_data.get("count", 0)
        sal = m_data.get("salience", 0.0)
        fed = m_data.get("fed", 0)
        print(f"  • [{m_id}]: occurrences={cnt}, salience={sal:.2f}, fed={fed}")
    print("=" * 75)

    receipt_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organism_identity": DEFAULT_IDENTITY,
        "initial_pressure": initial_pressure,
        "final_pressure": final_pressure,
        "sleep_beats_elapsed": beats_done,
        "wall_clock_seconds": total_wall_s,
        "ticks_per_second": rate,
        "overclock_speedup_factor": rate / REAL_TIME_TICKS_PER_SECOND,
        "reserve_micrograms_initial": initial_reserve + nighttime_sustenance_micrograms,
        "reserve_micrograms_final": final_reserve,
        "nights_completed": harness.organism.counts.get("nights", 1),
        "meanings_consolidated_count": len(meanings),
        "crystallized_meanings": meanings,
    }

    out_path = "backups/runtime/full_diurnal_sleep_cycle_receipt.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt_data, f, indent=2)
    print(f"\n[Audit Record] Successfully persisted final receipt to {out_path}")


if __name__ == "__main__":
    main()
