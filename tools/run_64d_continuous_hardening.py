#!/usr/bin/env python3
"""tools/run_64d_continuous_hardening.py

ArcLoom 64-Column Cortical Array: Continuous Physical Plastic Deformation Daemon
Governing Law: Continuum von Mises Material Yield Stress (f = |sigma| - Y <= 0)

Delivers continuous multimodal experience across the caretaker curriculum over multi-day
operational cycles (accumulating millions of causal ticks) while awaiting hardware delivery.
Periodically executes nocturnal sleep consolidation (Synaptic Homeostasis Hypothesis)
and persists crystallized synaptic conductances to backups/runtime/guala_64d_hardened_state.bin.
"""

from __future__ import annotations

import sys
import os
import time
import math
import signal
import logging
from typing import List, Tuple, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import guala_core
from guala_core import ModularSubstrate64D

LOG_PATH = "backups/runtime/guala_64d_hardening.log"
STATE_PATH = "backups/runtime/guala_64d_hardened_state.bin"

# Speech instruction formant profiles (F1, F2, F3 in Hz)
SPOKEN_CURRICULUM = [
    # 0. "pick up bear"
    [320.0, 950.0, 2150.0],
    # 1. "find tv remote"
    [480.0, 1420.0, 2650.0],
    # 2. "get your bottle"
    [390.0, 1150.0, 2380.0],
    # 3. "touch red ball"
    [520.0, 1280.0, 2500.0],
    # 4. "caregiver name"
    [280.0, 850.0, 2200.0],
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
    logger.info("   ARCLOOM 64-COLUMN CORTICAL ARRAY: CONTINUOUS PHYSICAL HARDENING   ")
    logger.info("   Governing Law: Continuum von Mises Yield Stress  f = |σ| - Y ≤ 0  ")
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
                sub64.import_sparse(data)
                logger.info(f"Restored existing hardened state from {STATE_PATH}: {len(data):,} bytes, {sub64.active_synapses():,} active synapses.")
        except Exception as e:
            logger.warning(f"Could not restore existing state from {STATE_PATH}: {e}")

    dt_target = 1.0 / target_hz
    tick = 0
    t_start = time.time()
    last_report_time = t_start

    # State variables for continuous multimodal physical trajectory
    target_r_base = 450.0
    target_theta_base = 0
    phrase_idx = 0
    phrase_hold = 0

    while RUNNING:
        tick += 1
        t_tick_start = time.perf_counter()

        # 1. Optical Target Dynamics (Continuous harmonic polar sweep)
        time_sec = tick * dt_target
        r_osc = 180.0 * math.sin(time_sec * 0.15)
        current_r = max(180.0, min(1400.0, target_r_base + r_osc))
        current_theta = int(25000.0 * math.sin(time_sec * 0.08))

        # Periodic optical occlusion (15 ticks blind every 200 ticks)
        cycle_200 = tick % 200
        is_occluded = (120 <= cycle_200 < 135)
        obs_r = None if is_occluded else current_r
        obs_th = None if is_occluded else current_theta

        # 2. Caretaker Spoken Instruction Formants (Continuous curriculum)
        phrase_hold -= 1
        if phrase_hold <= 0:
            phrase_idx = (phrase_idx + 1) % len(SPOKEN_CURRICULUM)
            phrase_hold = 40  # Hold phrase across 40 ticks (2.0 seconds)

        active_formants = SPOKEN_CURRICULUM[phrase_idx]

        # 3. Somatosensory & Barrier Stress Dynamics
        # Periodic obstacle contact every 300 ticks
        cycle_300 = tick % 300
        if 200 <= cycle_300 < 220:
            barrier_stress = 0.88  # Over-yield collision: triggers Col 23 refusal & vocal exhaust
        elif 220 <= cycle_300 < 240:
            barrier_stress = 0.25  # Sub-yield gentle contact
        else:
            barrier_stress = 0.02  # Free air motion

        # 4. Multimodal Sensory & Somatic Trits
        sensory = [1 if not is_occluded else 0] * 64
        somatic = [0] * 32
        # Somatic surplus modulation
        surplus = 0.40 + 0.30 * math.cos(time_sec * 0.05)
        if surplus > 0.20:
            n_surplus = min(12, int(surplus * 12))
            for i in range(n_surplus):
                somatic[20 + i] = 1

        # 5. Causal Step (Native 64D SIMD Rust Core)
        yields, strain = sub64.step(
            sensory,
            somatic,
            observed_r_mm=obs_r,
            observed_theta_mdeg=obs_th,
            barrier_stress=barrier_stress,
            acoustic_formants=active_formants,
        )

        # 6. Periodic Nocturnal Sleep Consolidation (Every 5,000 ticks ~ 4.2 minutes)
        if tick % 5000 == 0:
            pre_active = sub64.active_synapses()
            decayed, pruned = sub64.sleep_consolidation(decay=0.02, prune_thresh=0.005)
            post_active = sub64.active_synapses()
            logger.info(
                f"[SLEEP CONSOLIDATION] Tick {tick:,} | Downscaled: {decayed:,} | Pruned Noise: {pruned:,} | "
                f"Active Synapses: {pre_active:,} -> {post_active:,}"
            )

        # 7. Periodic State Checkpoint (Every 2,500 ticks ~ 2 minutes)
        if tick % 2500 == 0:
            try:
                sparse_bytes = sub64.export_sparse()
                with open(STATE_PATH, "wb") as f:
                    f.write(bytes(sparse_bytes))
                logger.info(
                    f"[CHECKPOINT PERSISTED] Tick {tick:,} | Exported {len(sparse_bytes):,} bytes | "
                    f"Active Synapses: {sub64.active_synapses():,} to {STATE_PATH}"
                )
            except Exception as e:
                logger.error(f"Failed to persist state checkpoint: {e}")

        # 8. Periodic Log Heartbeat (Every 10 seconds)
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
                f"Target: r={r_val:0.1f}mm, th={th_val}mdeg, occ={occ_val} | "
                f"Barrier Refusal: {refusal_val} | Vocal: {vocal_m:0.1f}Hz, Stride: {stride_m:0.1f}mm"
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
        final_bytes = sub64.export_sparse()
        with open(STATE_PATH, "wb") as f:
            f.write(bytes(final_bytes))
        logger.info(f"Final state saved: {len(final_bytes):,} bytes, {sub64.active_synapses():,} synapses.")
    except Exception as e:
        logger.error(f"Failed to save final state: {e}")
    logger.info("Continuous physical hardening completed cleanly.")


if __name__ == "__main__":
    run_continuous_hardening(target_hz=20.0)
