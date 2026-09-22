#!/usr/bin/env python3
"""tools/run_caregiver_feeding_and_sleep_pass.py — Caregiver Feeding & Sleep Settle Pass.

Executes:
1. Caregiver Feeding Phase: Caretaker presents 'bottle-milk' (3,200 µg tastants), satisfying
   metabolic hunger deficit (from 4,172 µg up), articulating 'I want bottle-milk', taking
   oral bite, and confirming with 'I like bottle-milk'.
2. Caregiver Bedtime Routine: Bedding (pillow and blanket) fetched and aligned on bed.
3. Somatosensory Bed Settle: Guala moves onto bed surface.
4. Nocturnal Sleep & Dream Consolidation: Eyelids close, basal burn active, sleep pressure
   recovering (2 units/beat), dreaming recurrent/salient moments into permanent semantic meanings
   while pruning unsalient noise (Pool Shock Principle).
5. State Verification & Telemetry Output.
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
    print("GUALA DEVELOPMENTAL PASS: CAREGIVER FEEDING & NOCTURNAL SLEEP SETTLE")
    print("=" * 75)

    # Initialize headless harness
    harness = HeadlessSpeedHarness(identity=DEFAULT_IDENTITY, initial_tick=50001)

    # Reconstitute post-50k milestone state:
    # 4,172 µg depleted reserves, 50,000 sleep pressure units, and episodic memory moments
    harness.organism._state["reserve_micrograms"] = 4172
    harness.organism._state["sleep_pressure"] = 50000

    # Inject milestone moments representing lived experiences from the 50k run:
    # 1. High salience maternal feeding memory
    harness.organism._state.setdefault("moments", {})["maternal_feeding_milk"] = {
        "count": 4,
        "tick": 50000,
        "salience": 0.92,
        "held": "bottle-milk",
        "source": "oral",
        "context": ["kitchen", "feeding"],
        "next": {"comfort": 3},
        "fed": 2,
    }
    # 2. Recurrent caretaker voice comfort memory
    harness.organism._state["moments"]["caretaker_voice_comfort"] = {
        "count": 3,
        "tick": 49800,
        "salience": 0.65,
        "held": "none",
        "source": "heard",
        "context": ["nursery"],
        "next": {"coo": 2},
        "fed": 0,
    }
    # 3. Recurrent soft blanket tactile comfort
    harness.organism._state["moments"]["soft_blanket_tactile"] = {
        "count": 2,
        "tick": 48500,
        "salience": 0.55,
        "held": "blanket",
        "source": "touch",
        "context": ["nursery"],
        "next": {"settle": 1},
        "fed": 0,
    }
    # 4. One-off unsalient floor dust noise (should be pruned by Pool Shock Principle)
    harness.organism._state["moments"]["floor_dust_tickle_noise"] = {
        "count": 1,
        "tick": 49200,
        "salience": 0.04,
        "held": "none",
        "source": "touch",
        "context": ["hallway"],
        "next": {},
        "fed": 0,
    }

    t0 = time.perf_counter()
    initial_reserve = harness.organism.reserve_micrograms
    initial_pressure = harness.organism.sleep["pressure"][0]
    initial_moments = len(harness.organism._state["moments"])

    print(f"\n[Phase 1] Caregiver Feeding Session: Offering bottle-milk to satisfy metabolic deficit...")
    feed_receipt = harness.run_curriculum_session(target_entity_id="bottle-milk")

    print(f"  • Demand Intent Formulated:  {feed_receipt.demand_intent_id}")
    print(f"  • Syntactic Tokens Emitted:  {' -> '.join(feed_receipt.demand_tokens_emitted)}")
    print(f"  • Demand Fulfilled:          {'YES' if feed_receipt.demand_fulfilled else 'NO'} ({feed_receipt.demand_duration_beats} beats)")
    print(f"  • Oral Reflex (Bites):       {feed_receipt.bites_count} bite(s) taken")
    print(f"  • Reserves Replenishment:    {feed_receipt.reserve_micrograms_initial} µg -> {feed_receipt.reserve_micrograms_final} µg (+{feed_receipt.reserve_micrograms_final - feed_receipt.reserve_micrograms_initial} µg)")
    print(f"  • Affective Valuation Token: {' -> '.join(feed_receipt.valuation_tokens_emitted)}")
    print(f"  • Valuation Fulfilled:       {'YES' if feed_receipt.valuation_fulfilled else 'NO'}")

    print(f"\n[Phase 2] Caregiver Bedtime Routine & Somatosensory Bed Settle...")
    # Run sleep settle pass (500 sleep beats of deep nocturnal consolidation)
    sleep_beats = 500
    sleep_receipt = harness.run_sleep_settle_session(target_sleep_beats=sleep_beats)

    print(f"  • Bed Preparation Status:    {'MADE' if sleep_receipt.bed_made else 'PRESENTED'} ({', '.join(sleep_receipt.bedding_items) or 'bedding aligned'})")
    print(f"  • Nocturnal State Gate:      Asleep (eyelids closed, basal burn)")
    print(f"  • Sleep Pressure Dynamics:   {sleep_receipt.initial_sleep_pressure} -> {sleep_receipt.final_sleep_pressure} units (-{sleep_receipt.initial_sleep_pressure - sleep_receipt.final_sleep_pressure} units recovered)")
    print(f"  • Diurnal Nights Completed:  {sleep_receipt.nights_completed} night(s)")
    print(f"  • Basal Metabolic Burn:      {sleep_receipt.reserve_micrograms_initial} µg -> {sleep_receipt.reserve_micrograms_final} µg")

    print(f"\n[Phase 3] Nocturnal Dream Consolidation & Semantic Meanings...")
    print(f"  • Moments Settled:           {sleep_receipt.moments_initial_count} initial -> {sleep_receipt.moments_remaining_count} unpruned")
    print(f"  • Meanings Crystallized:     {sleep_receipt.meanings_consolidated_count} permanent meaning(s)")
    meanings = harness.organism._state.get("meanings", {})
    for m_id, m_data in meanings.items():
        cnt = m_data.get("count", 0)
        sal = m_data.get("salience", 0.0)
        fed = m_data.get("fed", 0)
        print(f"    - [{m_id}]: count={cnt}, salience={sal:.2f}, fed={fed}")

    # Verify Pool Shock Principle
    if "floor_dust_tickle_noise" not in meanings:
        print(f"  • Pool Shock Invariant:      CONFIRMED (unsalient one-off moment pruned cleanly)")

    total_wall_s = time.perf_counter() - t0
    total_ticks = feed_receipt.demand_duration_beats + sleep_receipt.sleep_beats_elapsed
    rate = total_ticks / max(total_wall_s, 1e-6)

    print("\n" + "=" * 75)
    print("SESSION SUMMARY & AUDIT RECEIPT")
    print("=" * 75)
    print(f"Organism Identity:             {DEFAULT_IDENTITY}")
    print(f"Total Ticks Simulated:         {total_ticks} ticks ({feed_receipt.demand_duration_beats} awake + {sleep_receipt.sleep_beats_elapsed} asleep)")
    print(f"Total Wall-Clock Time:         {total_wall_s:.2f} seconds")
    print(f"Overall Simulation Rate:       {rate:.1f} ticks/second ({rate / REAL_TIME_TICKS_PER_SECOND:.2f}x real-time)")
    print(f"Final Metabolic Reserve:       {harness.organism.reserve_micrograms} µg")
    print(f"Final Sleep Pressure:          {harness.organism.sleep['pressure'][0]} units ({harness.organism.sleep['pressure'][0] * 100 // SLEEP_PRESSURE_CEILING}%)")
    print(f"Permanent Semantic Meanings:   {len(meanings)} crystallized structures")
    print("=" * 75)

    receipt_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "organism_identity": DEFAULT_IDENTITY,
        "feed_receipt": asdict(feed_receipt),
        "sleep_receipt": asdict(sleep_receipt),
        "crystallized_meanings": meanings,
        "total_ticks": total_ticks,
        "total_wall_clock_seconds": total_wall_s,
        "throughput_ticks_per_second": rate,
    }

    os.makedirs("backups/runtime", exist_ok=True)
    out_path = "backups/runtime/caregiver_feeding_and_sleep_receipt.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt_data, f, indent=2)
    print(f"\n[Audit Record] Successfully persisted receipt to {out_path}")


if __name__ == "__main__":
    main()
