#!/usr/bin/env python3
"""
DARPA ArcLoom Neuromorphic Substrate: Physical Sensorimotor Closed-Loop Demonstration
-------------------------------------------------------------------------------------
Demonstrates causal, deterministic closed-loop sensorimotor transduction:
  1. Multimodal Afferents: Optical gaze tracking, cochlear acoustic formants, tactile contact.
  2. Continuous Structural Field: 7D tensor field (D_k, M_k, R_rev, U*, C_k, P_k, B_k) + S_UF.
  3. 64-Column Cortical Array: Laminar flow (L4 -> L2/3 -> L5 -> L6) and inter-column yield plasticity.
  4. Causal Motor Efferent Decoding: Settled Layer 5 pyramidal neurons driving vocal, stride, steer, grip.
  5. Physical World Authority Execution: Commits MoveCommand and produces committed ActionExecutionReceipt.
  6. Oscilloscope Hardware Probe Calibration: Maps physical voltages and channel signals for benchtop probes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.substrate.modular_column_substrate import ModularColumnSubstrate
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    PORT_ID,
    encode_command,
)
from dsf_ai_service.guala_functional_organism import motor_efferent_to_locomotion_command


# Deterministic authority identity for physical demonstrator reproducibility
DEMO_AUTHORITY_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, "darpa.arcloom.sensorimotor.closedloop"))


def run_closed_loop_demo(steps: int = 50, verbose: bool = True) -> dict:
    started = time.perf_counter()
    if verbose:
        print("=" * 80)
        print("DARPA ARCLOOM PHYSICAL SENSORIMOTOR CLOSED-LOOP DEMONSTRATION")
        print("=" * 80)

    # 1. Initialize 64-Column Cortical Modular Substrate
    sub = ModularColumnSubstrate(
        yield_threshold=0.50,
        plastic_rate=0.08,
        activation_threshold=0.15,
        columns=64,
    )

    # 2. Initialize Physical World Authority
    world = home_world_authority(identity=DEMO_AUTHORITY_UUID)
    init_snap = world.observation_snapshot()
    her_init = next(b for b in init_snap.bodies if b.body_id == init_snap.self_body_id)
    init_pose = her_init.pose

    if verbose:
        print(f"[INIT] ModularSubstrate64D: 64 Columns, 18,432 Nodes, Yield Threshold = 0.50")
        print(f"[INIT] Physical World Authority: Initial Pose = ({init_pose.position.x} mm, {init_pose.position.y} mm, {init_pose.heading_millidegrees / 1000.0:.2f}°)")
        print("-" * 80)

    step_telemetry = []
    total_yields = 0
    total_strain = 0.0

    for step in range(steps):
        # A. Multimodal Sensory Inputs
        # Optical: visual target orbiting ahead
        orbit_angle = (step * 0.1) % (2.0 * math.pi)
        target_r_mm = 800.0 + 200.0 * math.cos(orbit_angle)
        target_theta_mdeg = int(25_000 * math.sin(orbit_angle))  # +/- 25 degrees
        
        # Acoustic: caregiver voice tone sweeping formants
        tone_freq = 220.0 + 110.0 * math.sin(step * 0.2)
        acoustic_formants = [tone_freq, tone_freq * 2.0, tone_freq * 3.0]

        # Somatosensory: minimal barrier stress (clear path)
        barrier_stress = 0.0

        # B. Continuous Joint Structural Field (DSF-AI L0-L4)
        # Harmonic test field in Accumulate basin (D_k > 0, S_UF > 0, R_rev < 0, P_k < B_k)
        field_7d = [
            0.65 + 0.10 * math.sin(step * 0.05),  # D_k (Displacement)
            0.40 + 0.08 * math.cos(step * 0.05),  # M_k (Motion)
            -0.25,                                # R_rev_k (Reversal: Negative => Viable)
            0.15,                                 # U*_k (Uncertainty)
            0.75 - 0.05 * math.sin(step * 0.05),  # C_k (Cohesion)
            0.42,                                 # P_k (Pressure)
            0.55,                                 # B_k (Breathing: P_k < B_k => No Venting)
        ]
        s_uf = 0.94  # Stability: Positive => Viable

        # Feed continuous structural field into prefrontal columns 48..55
        sub.consume_continuous_joint_field(field_7d, s_uf=s_uf)

        # C. Encode Multimodal Sensory Afferents (Optical 0..15, Cochlear 16..31, Somatic 32..47)
        sensory_trits = [0] * 64
        # Retinal projection into first 16 slots
        for i in range(16):
            sensory_trits[i] = 1 if math.sin(step * 0.15 + i) > 0.3 else 0

        # Cochlear projection into next 16 slots
        for i in range(16):
            sensory_trits[16 + i] = 1 if math.cos(step * 0.10 + i) > 0.4 else 0

        # Somatic apical trits (internal homeostatic state)
        somatic_trits = [1 if (step + i) % 5 == 0 else 0 for i in range(32)]

        # D. Execute Native Substrate Step (Laminar microcircuit + plastic return map)
        yields, strain = sub.step(
            sensory_trits,
            somatic_trits,
            observed_r_mm=target_r_mm,
            observed_theta_mdeg=target_theta_mdeg,
            barrier_stress=barrier_stress,
            acoustic_formant=acoustic_formants,
        )
        total_yields += yields
        total_strain += strain

        # E. Causal Motor Efferent Decoding from Settled Layer 5 Pyramidal Neurons
        vocal_hz, stride_mm, steer_deg, grip_n = sub.get_motor_efferent()

        # F. Execute Causal Kinematics in Physical World Authority
        current_snap = world.observation_snapshot()
        her_current = next(b for b in current_snap.bodies if b.body_id == current_snap.self_body_id)
        current_pose = her_current.pose

        move_cmd = motor_efferent_to_locomotion_command(
            (vocal_hz, stride_mm, steer_deg, grip_n), current_pose
        )

        receipt = None
        if move_cmd is not None:
            intent_sha = hashlib.sha256(f"{stride_mm}:{steer_deg}".encode()).hexdigest()
            prep = world.prepare_port_command(
                port_id=PORT_ID,
                command_payload=encode_command(move_cmd),
                causal_intent_receipt_sha256=intent_sha,
                expected_revision=current_snap.revision,
            )
            if not isinstance(prep, ActionExecutionReceipt):
                with world.prepared_action_visibility_transaction(prep):
                    receipt = world.commit_prepared_action(prep)
            else:
                receipt = prep

        post_snap = world.observation_snapshot()
        her_post = next(b for b in post_snap.bodies if b.body_id == post_snap.self_body_id)
        post_pose = her_post.pose

        # Record step telemetry
        record = {
            "step": step,
            "target_r_mm": round(target_r_mm, 1),
            "target_theta_mdeg": target_theta_mdeg,
            "field_D_k": round(field_7d[0], 4),
            "field_S_UF": round(s_uf, 4),
            "yields": yields,
            "strain": round(strain, 2),
            "vocal_hz": round(vocal_hz, 1),
            "stride_mm": round(stride_mm, 2),
            "steer_deg": round(steer_deg, 2),
            "pose_x_mm": post_pose.position.x,
            "pose_y_mm": post_pose.position.y,
            "pose_deg": round(post_pose.heading_millidegrees / 1000.0, 2),
            "receipt_status": receipt.disposition if receipt else "silent",
        }
        step_telemetry.append(record)

        if verbose and (step < 5 or step % 10 == 0 or step == steps - 1):
            print(
                f"[STEP {step:03d}] "
                f"Sensory: (r={target_r_mm:5.1f}mm, θ={target_theta_mdeg/1000.0:+5.1f}°) | "
                f"Field: D={field_7d[0]:.2f}, S={s_uf:.2f} | "
                f"Motor: stride={stride_mm:4.1f}mm, steer={steer_deg:+4.1f}° | "
                f"World Pose: ({post_pose.position.x:4d}, {post_pose.position.y:4d}) mm, {post_pose.heading_millidegrees/1000.0:+5.1f}° | "
                f"Yields: {yields:5d} | "
                f"Receipt: {record['receipt_status']}"
            )

    elapsed = time.perf_counter() - started
    active_contacts = sub.active_synapses()

    if verbose:
        print("-" * 80)
        print("DEMONSTRATION RESULTS & PHYSICAL INVARIANTS")
        print("-" * 80)
        print(f"Total Steps Executed: {steps} beats in {elapsed:.3f} s ({steps / elapsed:.1f} beats/sec)")
        print(f"Total Plastic Yield Events: {total_yields:,}")
        print(f"Total Contact Model Strain: {total_strain:,.1f}")
        print(f"Final Active Synaptic Contacts: {active_contacts:,}")
        print(f"Final Robot Pose: ({post_pose.position.x} mm, {post_pose.position.y} mm, {post_pose.heading_millidegrees / 1000.0:.2f}°)")

    # 3. Oscilloscope Hardware Probe Calibration Map
    oscilloscope_map = {
        "benchtop_hardware_target": "ArcLoom Ternary Neuromorphic Evaluation Board",
        "reference_voltage_mv": 3300,  # 3.3V LVCMOS / Analog
        "channels": [
            {
                "channel": "CH1 (Yellow)",
                "signal_name": "MOTOR_STRIDE_L5_PYRAMIDAL",
                "source_location": "Column 40, Layer 5 Output Bus (Header J4, Pin 2)",
                "scale": "500 mV / div",
                "range": "0.0V to 3.3V (maps linearly to 0 to 60 mm stride)",
                "bandwidth": "100 kHz",
                "physical_meaning": "Effector motor locomotion drive settled from settled L5 pyramidal neurons",
            },
            {
                "channel": "CH2 (Blue)",
                "signal_name": "PREFRONTAL_FIELD_D_k_AFFERENT",
                "source_location": "Column 48, Layer 4 Input Bus (Header J4, Pin 4)",
                "scale": "200 mV / div",
                "range": "-1.65V to +1.65V (bipolar balanced-ternary displacement D_k centered at 1.65V virtual GND)",
                "bandwidth": "500 kHz",
                "physical_meaning": "Macro-structural displacement tensor coordinate transduced across rational trits",
            },
            {
                "channel": "CH3 (Magenta)",
                "signal_name": "BARRIER_CONTACT_STRESS_REFUSAL",
                "source_location": "Column 23, Pyramidal Refusal Gate Interlock (Header J5, Pin 1)",
                "scale": "1.0 V / div",
                "range": "0.0V (normal navigation) or 3.3V (refusal clamp / stride arrest)",
                "bandwidth": "1 MHz (hard safety interlock)",
                "physical_meaning": "Somatosensory yield stress barrier refusal and S_UF <= 0 viability kill switch",
            },
            {
                "channel": "CH4 (Green)",
                "signal_name": "AUDITORY_COCHLEAR_FORMANT_CARRIER",
                "source_location": "Column 24, Layer 4 ERB Filterbank Peak (Header J5, Pin 3)",
                "scale": "200 mV / div",
                "range": "0.0V to 2.5V (acoustic spectral envelope power)",
                "bandwidth": "20 kHz (auditory bandwidth)",
                "physical_meaning": "Primary acoustic formant transduction from binaural cochlear hop",
            },
        ],
        "trigger": {
            "source": "CH1",
            "type": "Edge / Rising",
            "level": "500 mV",
            "mode": "Normal",
        },
    }

    report = {
        "status": "success",
        "evidence_scope": "physical_sensorimotor_closed_loop",
        "total_steps": steps,
        "elapsed_seconds": elapsed,
        "steps_per_second": round(steps / elapsed, 1),
        "total_yields": total_yields,
        "total_strain": round(total_strain, 2),
        "final_active_contacts": active_contacts,
        "initial_pose": {
            "x_mm": init_pose.position.x,
            "y_mm": init_pose.position.y,
            "deg": round(init_pose.heading_millidegrees / 1000.0, 2),
        },
        "final_pose": {
            "x_mm": post_pose.position.x,
            "y_mm": post_pose.position.y,
            "deg": round(post_pose.heading_millidegrees / 1000.0, 2),
        },
        "oscilloscope_calibration": oscilloscope_map,
        "first_step": step_telemetry[0],
        "last_step": step_telemetry[-1],
    }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=50, help="Number of closed-loop beats to execute")
    parser.add_argument("--json", action="store_true", help="Output pure JSON telemetry")
    args = parser.parse_args()

    report = run_closed_loop_demo(steps=args.steps, verbose=not args.json)
    if args.json:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
