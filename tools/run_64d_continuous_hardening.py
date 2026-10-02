#!/usr/bin/env python3
"""tools/run_64d_continuous_hardening.py

ArcLoom 64-Column Cortical Array: Continuous Physical Plastic Deformation Daemon
Governing Law: Continuum von Mises Material Yield Stress (f = |sigma| - Y <= 0)

Delivers continuous multimodal experience across the expanded action-object verb curriculum:
Actions: come, follow, get, find, pickup, drop, stop, hide-and-seek.
Objects: bear, bottle, remote, ball, apple, caregiver.

Structures experience into two-phase temporal syntax sequences:
  Phase 1: Action Verb Formants (Cols 8..10) coupled with motor efferent depolarization (Cols 40..42).
  Phase 2: Object Noun Formants (Cols 11..13) coupled with polar spatial well tracking (Cols 0..7).
  Phase 3: Inter-trial auditory relaxation and membrane potential settling.

Periodically executes nocturnal sleep consolidation (Synaptic Homeostasis Hypothesis)
and persists crystallized synaptic conductances to backups/runtime/guala_64d_hardened_state.bin
under the canonical ARCLOOM4 state specification.
"""

from __future__ import annotations

import sys
import os
import time
import math
import signal
import logging
from typing import List, Tuple, Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import guala_core
from guala_core import ModularSubstrate64D

LOG_PATH = "backups/runtime/guala_64d_hardening.log"
STATE_PATH = "backups/runtime/guala_64d_hardened_state.bin"

# 1. Action Verb Formant Profiles (F1, F2, F3 in Hz) and Physical Motor Affordances
ACTION_VERBS: Dict[str, Dict[str, Any]] = {
    "come": {
        "formants": [380.0, 1100.0, 2400.0],
        "stride_mm": 35.0,
        "steer_bias_deg": 0.0,
        "grip_n": 0.0,
        "occluded": False,
    },
    "follow": {
        "formants": [420.0, 1050.0, 2300.0],
        "stride_mm": 40.0,
        "steer_bias_deg": 15.0,
        "grip_n": 0.0,
        "occluded": False,
    },
    "get": {
        "formants": [530.0, 1850.0, 2500.0],
        "stride_mm": 30.0,
        "steer_bias_deg": 0.0,
        "grip_n": 8.5,
        "occluded": False,
    },
    "find": {
        "formants": [680.0, 1250.0, 2600.0],
        "stride_mm": 25.0,
        "steer_bias_deg": 25.0,
        "grip_n": 0.0,
        "occluded": False,
    },
    "pickup": {
        "formants": [360.0, 950.0, 2200.0],
        "stride_mm": 10.0,
        "steer_bias_deg": 0.0,
        "grip_n": 12.0,
        "occluded": False,
    },
    "drop": {
        "formants": [550.0, 1100.0, 2450.0],
        "stride_mm": 0.0,
        "steer_bias_deg": 0.0,
        "grip_n": 0.0,
        "occluded": False,
    },
    "stop": {
        "formants": [500.0, 1000.0, 2350.0],
        "stride_mm": 0.0,
        "steer_bias_deg": 0.0,
        "grip_n": 0.0,
        "occluded": False,
    },
    "hide-and-seek": {
        "formants": [450.0, 1700.0, 2600.0],
        "stride_mm": 20.0,
        "steer_bias_deg": -20.0,
        "grip_n": 0.0,
        "occluded": True,
    },
}

# 2. Target Object Formant Profiles (F1, F2, F3 in Hz) and Spatial Attractor Wells
TARGET_OBJECTS: Dict[str, Dict[str, Any]] = {
    "bear": {
        "formants": [320.0, 950.0, 2150.0],
        "target_r_mm": 450.0,
        "target_theta_mdeg": 25000,
    },
    "bottle": {
        "formants": [390.0, 1150.0, 2380.0],
        "target_r_mm": 600.0,
        "target_theta_mdeg": -15000,
    },
    "remote": {
        "formants": [480.0, 1420.0, 2650.0],
        "target_r_mm": 800.0,
        "target_theta_mdeg": 40000,
    },
    "ball": {
        "formants": [520.0, 1280.0, 2500.0],
        "target_r_mm": 350.0,
        "target_theta_mdeg": -30000,
    },
    "caregiver": {
        "formants": [280.0, 850.0, 2200.0],
        "target_r_mm": 700.0,
        "target_theta_mdeg": 0,
    },
}

# Permutation sequence for systematic combinatorial action-object curriculum
COMBINATORIAL_CURRICULUM: List[Tuple[str, str]] = [
    (verb, obj) for verb in ACTION_VERBS for obj in TARGET_OBJECTS
]

RUNNING = True


def signal_handler(signum, frame):
    global RUNNING
    logging.info(f"Signal {signum} received. Initiating graceful shutdown...")
    RUNNING = False


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("guala_64d_hardening")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ"
    )

    fh = logging.FileHandler(LOG_PATH, mode="a")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def run_continuous_hardening(target_hz: float = 20.0) -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger = setup_logger()
    logger.info("=" * 72)
    logger.info("   ARCLOOM 64-COLUMN CORTICAL ARRAY: CONTINUOUS VERB-OBJECT HARDENING")
    logger.info("   Governing Law: Continuum von Mises Yield Stress  f = |σ| - Y ≤ 0  ")
    logger.info("   Verbs: come, follow, get, find, pickup, drop, stop, hide-and-seek ")
    logger.info("=" * 72)

    # Initialize 64D substrate
    sub64 = ModularSubstrate64D(
        yield_threshold=0.55,
        plastic_rate=0.03,
        activation_threshold=0.22,
    )

    # Restore existing hardened state if present
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "rb") as f:
                data = f.read()
            if len(data) > 0:
                sub64.import_sparse_v4(data)
                logger.info(f"Restored existing hardened state from {STATE_PATH}: {len(data):,} bytes, {sub64.active_synapses():,} active synapses.")
        except Exception as e:
            logger.warning(f"Could not restore existing state from {STATE_PATH} (starting clean V4): {e}")

    dt_target = 1.0 / target_hz
    tick = 0
    t_start = time.time()
    last_report_time = t_start

    trial_idx = 0
    trial_tick = 0
    TRIAL_TICKS = 60  # 3.0 seconds per complete two-phase syntax trial

    while RUNNING:
        tick += 1
        trial_tick += 1
        t_tick_start = time.perf_counter()

        if trial_tick >= TRIAL_TICKS:
            trial_tick = 0
            trial_idx = (trial_idx + 1) % len(COMBINATORIAL_CURRICULUM)

        verb_name, obj_name = COMBINATORIAL_CURRICULUM[trial_idx]
        verb_info = ACTION_VERBS[verb_name]
        obj_info = TARGET_OBJECTS[obj_name]

        # Two-Phase Temporal Syntax Chaining:
        # Ticks 0..24  (1.25s): Phase 1 - Action Verb Formants sounded in Cols 8..10
        # Ticks 25..49 (1.25s): Phase 2 - Object Noun Formants sounded in Cols 11..13
        # Ticks 50..59 (0.50s): Phase 3 - Inter-trial quiet relaxation
        time_sec = tick * dt_target
        active_formants = [0.0] * 8

        if trial_tick < 25:
            # Phase 1: Action Verb
            active_formants[0:3] = verb_info["formants"]
            is_occluded = verb_info["occluded"]
            current_r = max(180.0, min(1400.0, obj_info["target_r_mm"] + 50.0 * math.sin(time_sec * 0.2)))
            current_theta = int(obj_info["target_theta_mdeg"] + verb_info["steer_bias_deg"] * 1000.0)
            target_grip = verb_info["grip_n"]
        elif trial_tick < 50:
            # Phase 2: Object Noun
            active_formants[3:6] = obj_info["formants"]
            is_occluded = False
            current_r = max(180.0, min(1400.0, obj_info["target_r_mm"]))
            current_theta = int(obj_info["target_theta_mdeg"])
            target_grip = verb_info["grip_n"]
        else:
            # Phase 3: Inter-trial quiet settling
            is_occluded = False
            current_r = max(180.0, min(1400.0, obj_info["target_r_mm"]))
            current_theta = int(obj_info["target_theta_mdeg"])
            target_grip = 0.0

        obs_r = None if is_occluded else current_r
        obs_th = None if is_occluded else current_theta

        # Somatosensory & Barrier Stress Dynamics
        # Periodic obstacle contact every 400 ticks
        cycle_400 = tick % 400
        if 280 <= cycle_400 < 300:
            barrier_stress = 0.88  # Over-yield collision: triggers Col 23 refusal clamp
        elif 300 <= cycle_400 < 320:
            barrier_stress = 0.20  # Sub-yield gentle contact
        else:
            barrier_stress = 0.02  # Free air motion

        # Multimodal Sensory & Somatic Trits
        sensory = [1 if not is_occluded else 0] * 64
        somatic = [0] * 32
        surplus = 0.40 + 0.30 * math.cos(time_sec * 0.05)
        if surplus > 0.20:
            n_surplus = min(12, int(surplus * 12))
            for i in range(n_surplus):
                somatic[20 + i] = 1

        # Causal Step (Native 64D SIMD Rust Core)
        yields, strain = sub64.step(
            sensory,
            somatic,
            observed_r_mm=obs_r,
            observed_theta_mdeg=obs_th,
            barrier_stress=barrier_stress,
            acoustic_formants=active_formants,
        )

        # Periodic Nocturnal Sleep Consolidation (Every 5,000 ticks ~ 4.2 minutes)
        if tick % 5000 == 0:
            pre_active = sub64.active_synapses()
            decayed, pruned = sub64.sleep_consolidation(decay=0.02, prune_thresh=0.005)
            post_active = sub64.active_synapses()
            logger.info(
                f"[SLEEP CONSOLIDATION] Tick {tick:,} | Downscaled: {decayed:,} | Pruned Noise: {pruned:,} | "
                f"Active Synapses: {pre_active:,} -> {post_active:,}"
            )

        # Periodic Canonical ARCLOOM4 Checkpoint (Every 2,500 ticks ~ 2.1 minutes)
        if tick % 2500 == 0:
            try:
                v4_bytes = sub64.export_sparse_v4()
                with open(STATE_PATH, "wb") as f:
                    f.write(bytes(v4_bytes))
                logger.info(
                    f"[CHECKPOINT PERSISTED] Tick {tick:,} | Exported ARCLOOM4 {len(v4_bytes):,} bytes | "
                    f"Active Synapses: {sub64.active_synapses():,} to {STATE_PATH}"
                )
            except Exception as e:
                logger.error(f"Failed to persist state checkpoint: {e}")

        # Periodic Log Heartbeat (Every 10 seconds)
        now = time.time()
        if now - last_report_time >= 10.0:
            elapsed = now - t_start
            active_syn = sub64.active_synapses()
            r_val, th_val, trace_val, occ_val = sub64.get_spatial_tracking()
            refusal_val = sub64.is_barrier_refusal_active()
            vocal_m, stride_m, steer_m, grip_m = sub64.get_motor_efferent()
            hz_actual = tick / max(1.0, elapsed)

            logger.info(
                f"Tick {tick:,} | Rate: {hz_actual:0.1f} Hz | Active Synapses: {active_syn:,} | "
                f"Curriculum: [{verb_name} {obj_name}] (phase {1 if trial_tick < 25 else (2 if trial_tick < 50 else 3)}) | "
                f"Motor: Stride={stride_m:0.1f}mm, Steer={steer_m:0.1f}deg, Grip={grip_m:0.1f}N | "
                f"Target: r={r_val:0.1f}mm, th={th_val}mdeg, occ={occ_val}"
            )
            last_report_time = now

        # Pacing: regulate loop to target_hz
        t_calc = time.perf_counter() - t_tick_start
        t_sleep = dt_target - t_calc
        if t_sleep > 0.0:
            time.sleep(t_sleep)

    # Clean final persistence on exit
    logger.info(f"Saving final hardened state at tick {tick:,}...")
    try:
        final_bytes = sub64.export_sparse_v4()
        with open(STATE_PATH, "wb") as f:
            f.write(bytes(final_bytes))
        logger.info(f"Final state saved: {len(final_bytes):,} bytes, {sub64.active_synapses():,} synapses.")
    except Exception as e:
        logger.error(f"Failed to save final state: {e}")
    logger.info("Continuous physical hardening completed cleanly.")


if __name__ == "__main__":
    run_continuous_hardening(target_hz=20.0)
