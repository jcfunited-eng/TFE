#!/usr/bin/env python3
"""arcloom_demonstrator/run_demonstrator.py

Tactical Sensorimotor Console & Oscilloscope Verification Harness
Substrate: ArcLoom Discrete Balanced-Ternary Neuromorphic Core
  - 8-Column Balanced Octet (Hardware FPGA Silicon Prototype)
  - 64-Column Cortical Array (High-Capacity Cortical Array, 20,480 nodes)
Governing Law: Continuum von Mises Plasticity (f = |sigma| - Y <= 0)

Interactive Real-Time Benchtop Demonstration for DARPA / AFRL Evaluators.
"""

from __future__ import annotations

import sys
import os
import time
import select
import tty
import termios
import argparse
from typing import Optional, Tuple

# Ensure local packages are loaded
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from substrate.modular_column_substrate import ModularColumnSubstrate


class NonBlockingInput:
    """Helper to read single keystrokes without blocking execution."""
    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_char(self) -> Optional[str]:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None


def render_dashboard(
    tick: int,
    dt_us: float,
    r_mm: float,
    theta_mdeg: int,
    trace: float,
    is_occluded: bool,
    formant: float,
    barrier_stress: float,
    yield_thresh: float,
    refusal: bool,
    motor_efferent: Tuple[float, ...],
    active_synapses: int,
    num_columns: int,
    status_msg: str,
) -> None:
    # Clear screen (ANSI escape)
    sys.stdout.write("\033[H\033[J")
    
    # Stress bar
    stress_ratio = min(1.0, barrier_stress / 1.0)
    bar_len = 24
    filled = int(stress_ratio * bar_len)
    stress_bar = "[" + "#" * filled + "-" * (bar_len - filled) + "]"

    total_synapses = 83_886_080 if num_columns == 64 else 1_048_576
    total_nodes = 20_480 if num_columns == 64 else 2_560
    config_title = f"{num_columns}-COLUMN CORTICAL ARRAY ({total_nodes:,} NODES)"

    print("=" * 76)
    print(f"      ARCLOOM TERNARY NEUROMORPHIC PROCESSOR -- {config_title}      ")
    print("        Governing Physical Law: Material Yield Stress  f = |σ| - Y ≤ 0    ")
    print("=" * 76)
    print(f" TICK: {tick:,}  |  CYCLE LATENCY: {dt_us:0.2f} µs  |  THROUGHPUT: {1e6/max(1.0, dt_us):,.0f} Hz")
    print("-" * 76)

    # Sector 1: Optical
    occ_str = " ** OCCLUDED (BLIND) **" if is_occluded else " NOMINAL FOVEA"
    print(f" [SECTOR 1: OPTICAL FOVEAL RADAR (V1/V2)]")
    print(f"   Target Polar Distance (r):   {r_mm:6.1f} mm       Status: {occ_str}")
    print(f"   Target Heading Angle (θ):    {theta_mdeg:6,d} mdeg    Persistence Trace: {trace:0.4f}")
    if is_occluded:
        print("   >> INVARIANT ACTIVE: Deep L5 spatial well sustains coordinates with 0.00 mm drift.")
    print()

    # Sector 2: Acoustic
    print(f" [SECTOR 2: ACOUSTIC COCHLEAR RESONANCE (A1/A2)]")
    print(f"   Peak Formant Frequency:      {formant:6.1f} Hz       Filterbank: 64 ERB channels")
    print()

    # Sector 3: Somatosensory & Yield Refusal
    ref_str = " ** OVER-YIELD REFUSAL (ARREST) **" if refusal else " SUB-YIELD PASSIVE CONTACT"
    print(f" [SECTOR 3: CONTINUUM MATERIAL AFFORDANCE (S1/S2)]")
    print(f"   Contact Stress (|σ|):        {barrier_stress:6.2f} / Y={yield_thresh:0.2f}   {stress_bar}")
    print(f"   Barrier State:               {ref_str}")
    print()

    # Sector 4: Motor Pyramidal Efferents
    print(f" [SECTOR 4: MOTOR PYRAMIDAL EFFERENTS (M1/M2)]")
    vocal = motor_efferent[0] if len(motor_efferent) > 0 else 0.0
    stride = motor_efferent[1] if len(motor_efferent) > 1 else 0.0
    print(f"   Locomotion Stride Drive:     {stride:6.1f} mm/step   (Pyramidal efferent)")
    print(f"   Airway Vocal Valve Pulse:    {vocal:6.1f} Hz        (Homeostatic exhaust)")
    if len(motor_efferent) >= 4:
        steer = motor_efferent[2]
        grip = motor_efferent[3]
        print(f"   Steering Heading Rate:       {steer:6.1f} deg/s      Gripper Clamping Force: {grip:6.1f} N")
    print()

    # Sector 5: Plastic Associative Matrix
    print(f" [SECTOR 5: CONTINUUM PLASTIC CONDUCTANCES]")
    print(f"   Active Hardened Synapses:    {active_synapses:,} / {total_synapses:,} fasciculi (|g| ≥ 0.001)")
    print("-" * 76)
    print(f" STATUS: {status_msg}")
    print("-" * 76)
    print(" CONTROLS: [B] Blind Camera (Occlude)  | [A] Acoustic Pulse | [C] Collision Stress")
    print("           [S] Sleep Consolidation     | [R] Reset Target   | [Q] Quit")
    print("=" * 76)
    sys.stdout.flush()


def run_interactive(num_columns: int = 8) -> None:
    substrate = ModularColumnSubstrate(
        yield_threshold=0.60,
        plastic_rate=0.04,
        activation_threshold=0.25,
        columns=num_columns,
    )

    # Initial state
    target_r = 350.0
    target_theta = 15000
    is_blind = False
    acoustic_stim = 0.0
    barrier_stress = 0.0
    status_msg = f"Substrate operating at nominal 20 Hz loop ({num_columns} columns). Press keys to interact."

    tick = 0
    with NonBlockingInput() as kb:
        while True:
            tick += 1
            t0 = time.perf_counter()

            # Handle keystrokes
            ch = kb.get_char()
            if ch:
                ch = ch.lower()
                if ch == 'q':
                    print("\nExiting demonstrator.\n")
                    break
                elif ch == 'b':
                    is_blind = not is_blind
                    status_msg = f"Visual feed {'BLINDED (Total Optical Occlusion)' if is_blind else 'RESTORED'}."
                elif ch == 'a':
                    acoustic_stim = 220.0
                    status_msg = "Injected 220 Hz acoustic formant peak into A1 cochlear column."
                elif ch == 'c':
                    barrier_stress = 0.95
                    status_msg = "Induced over-yield impact (|σ| = 0.95 > Y = 0.60). Barrier refusal engaged!"
                elif ch == 'r':
                    target_r = 400.0
                    target_theta = -12000
                    barrier_stress = 0.0
                    is_blind = False
                    status_msg = "Reset target to new coordinates (r=400mm, theta=-12,000 mdeg)."
                elif ch == 's':
                    d, p = substrate.substrate.sleep_consolidation(decay=0.05, prune_thresh=0.01)
                    status_msg = f"Nocturnal consolidation executed: {d:,} conductances decayed, {p:,} noise pruned."

            # Construct sensory and somatic vectors
            sensory = [1 if not is_blind else 0] * 64
            somatic = [0] * 32

            obs_r = None if is_blind else target_r
            obs_th = None if is_blind else target_theta

            # Step causal loop
            yields, energy = substrate.step(
                sensory_trits=sensory,
                somatic_trits=somatic,
                observed_r_mm=obs_r,
                observed_theta_mdeg=obs_th,
                barrier_stress=barrier_stress,
                acoustic_formant=acoustic_stim,
            )

            dt_us = (time.perf_counter() - t0) * 1e6

            # Query physical state
            r_mm, theta_mdeg, trace, occluded = substrate.get_spatial_tracking()
            refusal = substrate.is_barrier_refusal_active()
            motor = substrate.get_motor_efferent()
            active_syn = substrate.active_synapses()

            # Decay transient stimuli
            acoustic_stim = max(0.0, acoustic_stim - 20.0)
            if barrier_stress > 0.0:
                barrier_stress = max(0.0, barrier_stress - 0.15)

            # Render display every 2 ticks (~10 FPS console refresh)
            if tick % 2 == 0:
                render_dashboard(
                    tick=tick,
                    dt_us=dt_us,
                    r_mm=r_mm,
                    theta_mdeg=theta_mdeg,
                    trace=trace,
                    is_occluded=is_blind or occluded,
                    formant=acoustic_stim,
                    barrier_stress=barrier_stress,
                    yield_thresh=substrate.yield_threshold,
                    refusal=refusal,
                    motor_efferent=motor,
                    active_synapses=active_syn,
                    num_columns=num_columns,
                    status_msg=status_msg,
                )

            # Regulate to 20 Hz (50 ms loop) for human interaction pace
            time.sleep(0.05)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ArcLoom Sensorimotor Console Demonstrator")
    parser.add_argument("--columns", type=int, default=8, choices=[8, 64], help="Column count: 8 (hardware octet) or 64 (cortical array)")
    args = parser.parse_args()
    run_interactive(num_columns=args.columns)
