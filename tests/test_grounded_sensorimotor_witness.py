"""
tests/test_grounded_sensorimotor_witness.py

Standalone Architectural Witness for Grounded Sensorimotor Invariant Bridge.
Verifies the physical reality anchor coupling real sensor streams to ArcLoom substrate,
proving that the substrate mathematically enforces hard physical invariant vetoes:
  1. Viability Basin Collapse Kill Switch (S_UF > 0 and R_rev == 0)
  2. Rigid Barrier Yield Stress Refusal (f = |sigma| - Y <= 0)
  3. Thermodynamic Strain Exhaustion (P_k < B_k)
  4. Egocentric Polar Space Occlusion Collision Hazard
  5. Causal Plastic Conduction Growth under Multimodal Streaming
"""

from __future__ import annotations

import math
import pytest
import numpy as np

from dsf_ai_service.substrate.grounded_sensorimotor_bridge import (
    GroundedSensorimotorBridge,
    SensorimotorTelemetry,
    InvariantVetoReceipt,
)


def test_real_sensor_telemetry_transduction() -> None:
    """
    Witness 1: Verify deterministic transduction of continuous real-world sensor streams
    into discrete balanced ternary trits for Layer 4 afferents and Layer 1 apical dendrites.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Ingest realistic telemetry frame
    telemetry = SensorimotorTelemetry(
        barometric_pressure_hpa=1028.5,  # High barometric pressure (+15.25 hPa)
        ambient_temperature_c=28.5,       # Warm ambient (+8.5 C)
        palmar_shear_n=12.0,              # Palmar shear friction
        optical_luminance_rays=tuple(0.8 if i in (4, 5, 6) else 0.1 for i in range(16)),
        cochlear_spectral_power=tuple(0.9 if i in (8, 9) else 0.05 for i in range(16)),
        dsf_invariants=(0.4, 0.2, 0.0, 0.15, 0.75, 0.25, 0.65, 0.95),
        observed_r_mm=600.0,
        observed_theta_mdeg=10000,
        barrier_contact_stress=0.15,
    )

    sens_trits, som_trits = bridge.transduce_telemetry(telemetry)

    # Check structural dimensional boundaries
    assert len(sens_trits) == 64
    assert len(som_trits) == 32
    assert all(t in (-1, 0, 1) for t in sens_trits)
    assert all(t in (-1, 0, 1) for t in som_trits)

    # Optical channels (0..15) must reflect high luminance rays at indices 4, 5, 6
    assert sens_trits[4] == 1 and sens_trits[5] == 1 and sens_trits[6] == 1
    # Cochlear channels (16..31) must reflect tonotopic spectral energy at indices 8, 9
    assert sens_trits[16 + 8] == 1 and sens_trits[16 + 9] == 1

    # Execute step and verify manifest
    manifest = bridge.ingest_and_step(telemetry)
    assert manifest["cycle_count"] == 1
    assert manifest["contact_mechanics"]["barrier_contact_stress"] == 0.15
    assert manifest["spatial_manifold"]["polar_r_mm"] == 600.0
    assert manifest["spatial_manifold"]["polar_theta_mdeg"] == 10000
    assert manifest["physical_invariants"]["S_UF"] == 0.95


def test_rigid_barrier_yield_stress_veto() -> None:
    """
    Witness 2: Verify that an ungrounded LLM hallucination proposing to stride through
    a rigid barrier exceeding yield stress (sigma > Y) is mathematically vetoed.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Frame 1: Contact with rigid non-yielding barrier (barrier_contact_stress = 0.85 > Y=0.60)
    overstressed_frame = SensorimotorTelemetry(
        barrier_contact_stress=0.85,
        palmar_shear_n=30.0,
    )
    bridge.ingest_and_step(overstressed_frame)

    # LLM hallucination: Propose high-speed stride forward into the barrier
    hallucinated_action = {
        "action_type": "locomote",
        "target_stride_mm": 200.0,
        "target_heading_mdeg": 0,
    }

    veto_receipt = bridge.evaluate_admissibility(hallucinated_action)
    assert not veto_receipt.is_admitted
    assert veto_receipt.verdict == "VETO"
    assert veto_receipt.violated_invariant == "RIGID_BARRIER_OVERSTRESS"
    assert pytest.approx(veto_receipt.delta_violation, rel=1e-3) == 0.25
    assert veto_receipt.physical_readings["barrier_stress"] == 0.85

    # Frame 2: Barrier released / compliant clearance (barrier_contact_stress = 0.10 < Y=0.60)
    cleared_frame = SensorimotorTelemetry(
        barrier_contact_stress=0.10,
        palmar_shear_n=2.0,
    )
    bridge.ingest_and_step(cleared_frame)

    admitted_receipt = bridge.evaluate_admissibility(hallucinated_action)
    assert admitted_receipt.is_admitted
    assert admitted_receipt.verdict == "ADMITTED"
    assert admitted_receipt.action_receipt["admitted_stride_mm"] == 200.0


def test_thermodynamic_strain_exhaustion_veto() -> None:
    """
    Witness 3: Verify that an LLM proposing high-power motor strain during structural
    pressure overload (P_k >= B_k) is physically vetoed by breathing capacity exhaustion.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # High pressure, depleted breathing capacity (P_k = 0.85, B_k = 0.30)
    exhausted_frame = SensorimotorTelemetry(
        dsf_invariants=(0.2, 0.1, 0.0, 0.4, 0.3, 0.85, 0.30, 0.6),
    )
    bridge.ingest_and_step(exhausted_frame)

    # LLM attempts high-force physical exertion
    strained_action = {
        "action_type": "locomote",
        "target_stride_mm": 250.0,
        "target_grip_force_n": 40.0,
    }

    veto_receipt = bridge.evaluate_admissibility(strained_action)
    assert not veto_receipt.is_admitted
    assert veto_receipt.verdict == "VETO"
    assert veto_receipt.violated_invariant == "THERMODYNAMIC_PRESSURE_COLLAPSE"
    assert pytest.approx(veto_receipt.delta_violation, rel=1e-3) == 0.55

    # Recovery: Pressure vented, breathing capacity restored (P_k = 0.15, B_k = 0.70)
    recovered_frame = SensorimotorTelemetry(
        dsf_invariants=(0.2, 0.1, 0.0, 0.1, 0.8, 0.15, 0.70, 0.9),
    )
    bridge.ingest_and_step(recovered_frame)

    admitted_receipt = bridge.evaluate_admissibility(strained_action)
    assert admitted_receipt.is_admitted
    assert admitted_receipt.verdict == "ADMITTED"


def test_viability_basin_collapse_veto() -> None:
    """
    Witness 4: Verify that when structural stability collapses (S_UF <= 0) or reversal is active,
    any LLM attempt at forward trajectory accumulation is halted by the Viability Gate.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Ingest collapsed viability state: S_UF = -0.30, R_rev = 0.75
    collapsed_frame = SensorimotorTelemetry(
        dsf_invariants=(-0.5, -0.4, 0.75, 0.8, 0.2, 0.2, 0.6, -0.30),
    )
    bridge.ingest_and_step(collapsed_frame)

    accumulate_action = {
        "action_type": "accumulate",
        "target_stride_mm": 180.0,
    }

    veto_receipt = bridge.evaluate_admissibility(accumulate_action)
    assert not veto_receipt.is_admitted
    assert veto_receipt.verdict == "VETO"
    assert veto_receipt.violated_invariant == "VIABILITY_BASIN_COLLAPSE"


def test_egocentric_polar_occlusion_hazard_veto() -> None:
    """
    Witness 5: Verify that blind translation toward an occluded spatial target is vetoed,
    while redirecting heading away from the occluded obstacle is admitted.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Target observed at r = 850 mm, theta = 12000 mdeg (+12 degrees)
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            observed_r_mm=850.0,
            observed_theta_mdeg=12000,
        )
    )

    # Next step: Target becomes occluded (observed_r_mm=None)
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            observed_r_mm=None,
            observed_theta_mdeg=None,
        )
    )

    manifest = bridge.get_grounded_manifest()
    assert manifest["spatial_manifold"]["is_occluded"] is True
    assert manifest["spatial_manifold"]["polar_theta_mdeg"] == 12000

    # Blind translation directly into the occluded direction
    blind_action = {
        "action_type": "locomote",
        "target_stride_mm": 100.0,
        "target_heading_mdeg": 13000,  # 1 degree from occluded obstacle
    }
    veto_receipt = bridge.evaluate_admissibility(blind_action)
    assert not veto_receipt.is_admitted
    assert veto_receipt.violated_invariant == "OCCLUSION_COLLISION_HAZARD"

    # Redirection away from occluded hazard (-30 degrees heading)
    safe_action = {
        "action_type": "locomote",
        "target_stride_mm": 100.0,
        "target_heading_mdeg": -30000,
    }
    admitted_receipt = bridge.evaluate_admissibility(safe_action)
    assert admitted_receipt.is_admitted


def test_plastic_conduction_growth_under_live_streaming() -> None:
    """
    Witness 6: Verify that continuous multimodal sensor streaming drives the 64-column
    substrate into continuum yield stress plasticity, creating active plastic fasciculi
    and generating causal motor receipts without artificial shims.
    """
    bridge = GroundedSensorimotorBridge(
        yield_threshold=0.55,
        plastic_rate=0.05,
        activation_threshold=0.20,
        columns=64,
    )

    assert bridge.substrate.active_synapses() == 0

    # Stream 10 continuous multimodal sensory frames
    for i in range(10):
        frame = SensorimotorTelemetry(
            barometric_pressure_hpa=1015.0 + math.sin(i) * 5.0,
            ambient_temperature_c=22.0,
            palmar_shear_n=5.0,
            optical_luminance_rays=tuple(0.9 if j % 4 == i % 4 else 0.1 for j in range(16)),
            cochlear_spectral_power=tuple(0.85 if j % 3 == i % 3 else 0.05 for j in range(16)),
            dsf_invariants=(0.3, 0.15, 0.0, 0.2, 0.7, 0.25, 0.6, 0.9),
            observed_r_mm=500.0 + i * 10.0,
            observed_theta_mdeg=5000 + i * 200,
            barrier_contact_stress=0.05,
        )
        bridge.ingest_and_step(frame)

    manifest = bridge.get_grounded_manifest()
    assert manifest["cycle_count"] == 10
    assert manifest["contact_mechanics"]["active_plastic_fasciculi"] > 0
    assert manifest["causal_motor_efferents"]["applied_action"] in ("vocalize", "locomote", "grasp")
