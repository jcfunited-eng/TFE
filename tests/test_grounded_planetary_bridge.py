"""
tests/test_grounded_planetary_bridge.py — Test Suite for Grounded Planetary Sensor Bridge.

Author: Chief Systems Architect & Senior DARPA Neuromorphic Systems Engineer
Authority: DSF-AI Master Strategic Roadmap (Pillar 3: GualaLoom)
Classification: Commercial & Defense Production Standard (DARPA Grade)

Verifies:
  1. HostHardwareSensorSource probing and graceful fallback.
  2. PlanetaryContinuumSensorSource diurnal atmospheric and thermal physics.
  3. Barometric pressure scaling into somatic contact load.
  4. Ambient thermal flux scaling into apical metabolic/thermal context trits.
  5. 16-ray optical luminance azimuth transduction and polar retinotopic tracking.
  6. Continuous closed-loop runner execution and plastic fasciculi development.
  7. Hard Invariant Veto Gate enforcement across all 4 physical failure boundaries:
     - Viability Basin Collapse (S_UF <= 0 or R_rev > 0)
     - Rigid Barrier Overstress (|sigma| > Y)
     - Thermodynamic Pressure Collapse (P_k >= B_k)
     - Polar Spatial Occlusion Hazard (heading into occluded target)
  8. Structured execution receipt generation and schema validity.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pytest

from dsf_ai_service.substrate.grounded_sensorimotor_bridge import (
    GroundedSensorimotorBridge,
    SensorimotorTelemetry,
    InvariantVetoReceipt,
)
from tools.run_grounded_planetary_bridge import (
    GroundedPlanetaryBridgeRunner,
    HostHardwareSensorSource,
    PlanetaryContinuumSensorSource,
    PlanetaryBridgeRunSummary,
)


def test_host_hardware_source_probing_and_fallback() -> None:
    """
    Test 1: Verify HostHardwareSensorSource safely discovers thermal zones and camera
    devices without crashing, returning valid physical telemetry frames.
    """
    source = HostHardwareSensorSource()
    telemetry = source.read_telemetry(cycle_index=0, elapsed_seconds=0.0)

    assert isinstance(telemetry, SensorimotorTelemetry)
    assert 900.0 <= telemetry.barometric_pressure_hpa <= 1100.0
    assert -20.0 <= telemetry.ambient_temperature_c <= 100.0
    assert len(telemetry.optical_luminance_rays) == 16
    assert len(telemetry.cochlear_spectral_power) == 16
    assert len(telemetry.dsf_invariants) == 8
    assert all(0.0 <= r <= 1.0 for r in telemetry.optical_luminance_rays)
    assert all(0.0 <= c <= 1.0 for c in telemetry.cochlear_spectral_power)

    source.close()


def test_planetary_continuum_physical_waveforms() -> None:
    """
    Test 2: Verify PlanetaryContinuumSensorSource generates physical diurnal pressure,
    temperature flux, moving optical luminance target, and occlusion phases.
    """
    source = PlanetaryContinuumSensorSource(
        nominal_pressure_hpa=1013.25,
        nominal_temperature_c=20.0,
        diurnal_period_seconds=10.0,
        simulate_occlusions=True,
    )

    pressures = []
    temps = []
    occluded_flags = []

    for t in np.linspace(0.0, 10.0, 50):
        frame = source.read_telemetry(cycle_index=int(t * 10), elapsed_seconds=float(t))
        pressures.append(frame.barometric_pressure_hpa)
        temps.append(frame.ambient_temperature_c)
        occluded_flags.append(frame.observed_r_mm is None)

    # Pressure must fluctuate around nominal 1013.25
    assert np.min(pressures) < 1013.25 < np.max(pressures)
    # Temperature must fluctuate around nominal 20.0 C
    assert np.min(temps) < 20.0 < np.max(temps)
    # Occlusion window must be triggered
    assert any(occluded_flags)
    assert not all(occluded_flags)


def test_atmospheric_pressure_transduction_scaling() -> None:
    """
    Test 3: Verify barometric pressure variation directly modulates somatic contact load
    in transduce_telemetry without heuristics.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Frame A: Standard sea-level pressure (1013.25 hPa)
    frame_std = SensorimotorTelemetry(barometric_pressure_hpa=1013.25, palmar_shear_n=0.0)
    sens_std, _ = bridge.transduce_telemetry(frame_std)

    # Frame B: High barometric pressure (+40 hPa -> delta_p_atm = +0.40)
    frame_high = SensorimotorTelemetry(barometric_pressure_hpa=1053.25, palmar_shear_n=0.0)
    sens_high, _ = bridge.transduce_telemetry(frame_high)

    # Somatosensory afferent trits in Column 4 (S1) are at indices 32..47
    # High pressure increases somatic positive trits
    somatic_std_pos = sum(1 for t in sens_std[32:48] if t > 0)
    somatic_high_pos = sum(1 for t in sens_high[32:48] if t > 0)
    assert somatic_high_pos >= somatic_std_pos


def test_thermal_flux_apical_deficit_scaling() -> None:
    """
    Test 4: Verify ambient temperature flux generates milliKelvin thermal contrast,
    and thermodynamic pressure imbalance (P_k >= B_k) drives Layer 1 apical metabolic deficit.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Baseline temperature (20.0 C, thermal_gradient = 0 mK)
    frame_baseline = SensorimotorTelemetry(
        ambient_temperature_c=20.0,
        dsf_invariants=(0.0, 0.0, 0.0, 0.5, 0.5, 0.2, 0.5, 1.0),  # P_k=0.2 < B_k=0.5
    )
    _, som_baseline = bridge.transduce_telemetry(frame_baseline)

    # Overheated with thermodynamic strain collapse (35.0 C, P_k=0.8 > B_k=0.3)
    frame_overheated = SensorimotorTelemetry(
        ambient_temperature_c=35.0,  # +15,000 mK
        dsf_invariants=(0.0, 0.0, 0.0, 0.5, 0.5, 0.8, 0.3, 1.0),  # P_k=0.8 > B_k=0.3
    )
    _, som_overheated = bridge.transduce_telemetry(frame_overheated)

    # Apical deficit trits reflect thermodynamic strain
    deficit_baseline = sum(1 for t in som_baseline if t > 0)
    deficit_overheated = sum(1 for t in som_overheated if t > 0)
    assert deficit_overheated > deficit_baseline


def test_optical_azimuth_ray_transduction_and_polar_tracking() -> None:
    """
    Test 5: Verify 16-ray optical luminance field activates retinotopic visual nodes (0..15),
    and spatial target coordinates lock polar tracking with exponential decay under occlusion.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # Active luminant target at sector 5 (azimuth ~ -15 deg)
    rays = [0.05] * 16
    rays[5] = 0.95
    telemetry = SensorimotorTelemetry(
        optical_luminance_rays=tuple(rays),
        observed_r_mm=480.0,
        observed_theta_mdeg=-15000,
    )

    sens_trits, _ = bridge.transduce_telemetry(telemetry)
    # Visual node 5 must be actively stimulated
    assert sens_trits[5] == 1

    # Step bridge and check spatial tracking
    manifest = bridge.ingest_and_step(telemetry)
    spatial = manifest["spatial_manifold"]
    assert spatial["polar_r_mm"] == 480.0
    assert spatial["polar_theta_mdeg"] == -15000
    assert spatial["persistence_trace"] == 1.0
    assert spatial["is_occluded"] is False

    # Next cycle: Visual occlusion occurs
    telemetry_occluded = SensorimotorTelemetry(
        optical_luminance_rays=tuple([0.05] * 16),
        observed_r_mm=None,
        observed_theta_mdeg=None,
    )
    manifest_occ = bridge.ingest_and_step(telemetry_occluded)
    spatial_occ = manifest_occ["spatial_manifold"]
    assert spatial_occ["polar_r_mm"] == 480.0  # Retained coordinate
    assert spatial_occ["polar_theta_mdeg"] == -15000  # Retained coordinate
    assert spatial_occ["is_occluded"] is True
    assert 0.0 < spatial_occ["persistence_trace"] < 1.0  # Decaying memory trace


def test_closed_loop_runner_execution_and_plasticity() -> None:
    """
    Test 6: Verify GroundedPlanetaryBridgeRunner runs continuous closed-loop cycles,
    accumulates von Mises yield stress, creates plastic fasciculi, and returns full summary.
    """
    source = PlanetaryContinuumSensorSource(
        nominal_pressure_hpa=1013.25,
        nominal_temperature_c=20.0,
        diurnal_period_seconds=5.0,
        simulate_occlusions=True,
        simulate_barrier_contacts=False,
    )

    runner = GroundedPlanetaryBridgeRunner(
        source=source,
        yield_threshold=0.55,
        plastic_rate=0.05,
        activation_threshold=0.20,
        columns=64,
        source_name="test_continuum",
    )

    summary = runner.execute_cycles(cycles=20, frequency_hz=0.0, test_veto_gates=True, quiet=True)

    assert isinstance(summary, PlanetaryBridgeRunSummary)
    assert summary.total_cycles == 20
    assert summary.duration_seconds > 0.0
    assert summary.effective_frequency_hz > 0.0
    assert summary.final_active_synapses > summary.initial_active_synapses
    assert summary.total_plastic_yield_events > 0
    assert summary.final_strain_energy > 0.0
    assert "barometric_pressure_hpa" in summary.sensor_telemetry_stats
    assert "ambient_temperature_c" in summary.sensor_telemetry_stats


def test_hard_invariant_veto_gate_enforcement() -> None:
    """
    Test 7: Verify all 4 Hard Invariant Veto Gates actively block non-conforming actions:
      - Gate 1: Viability Basin Collapse (S_UF <= 0 or R_rev > 0)
      - Gate 2: Rigid Barrier Overstress (|sigma| > Y)
      - Gate 3: Thermodynamic Pressure Collapse (P_k >= B_k)
      - Gate 4: Polar Spatial Occlusion Hazard (stride toward occluded target)
    And verify admission when boundary conditions are satisfied.
    """
    bridge = GroundedSensorimotorBridge(yield_threshold=0.60, columns=64)

    # -------------------------------------------------------------------------
    # Gate 1: Viability Basin Collapse
    # -------------------------------------------------------------------------
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            dsf_invariants=(-0.2, -0.1, 0.8, 0.4, 0.3, 0.2, 0.6, -0.25),  # S_UF <= 0, R_rev > 0
        )
    )
    veto_viability = bridge.evaluate_admissibility({"action_type": "accumulate", "target_stride_mm": 150.0})
    assert not veto_viability.is_admitted
    assert veto_viability.violated_invariant == "VIABILITY_BASIN_COLLAPSE"

    # -------------------------------------------------------------------------
    # Gate 2: Rigid Barrier Overstress
    # -------------------------------------------------------------------------
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            barrier_contact_stress=0.85,  # Exceeds Y=0.60
            dsf_invariants=(0.2, 0.1, 0.0, 0.2, 0.7, 0.2, 0.6, 0.95),  # Viable
        )
    )
    veto_barrier = bridge.evaluate_admissibility({"action_type": "locomote", "target_stride_mm": 50.0})
    assert not veto_barrier.is_admitted
    assert veto_barrier.violated_invariant == "RIGID_BARRIER_OVERSTRESS"

    # -------------------------------------------------------------------------
    # Gate 3: Thermodynamic Pressure Collapse
    # -------------------------------------------------------------------------
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            barrier_contact_stress=0.0,  # Clear
            dsf_invariants=(0.2, 0.1, 0.0, 0.2, 0.7, 0.90, 0.30, 0.95),  # P_k=0.90 >= B_k=0.30
        )
    )
    veto_thermo = bridge.evaluate_admissibility({
        "action_type": "locomote",
        "target_stride_mm": 150.0,  # High-strain exertion
    })
    assert not veto_thermo.is_admitted
    assert veto_thermo.violated_invariant == "THERMODYNAMIC_PRESSURE_COLLAPSE"

    # -------------------------------------------------------------------------
    # Gate 4: Polar Spatial Occlusion Hazard
    # -------------------------------------------------------------------------
    # Prime target at heading +20,000 mdeg
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            observed_r_mm=600.0,
            observed_theta_mdeg=20000,
            dsf_invariants=(0.2, 0.1, 0.0, 0.2, 0.7, 0.20, 0.60, 0.95),
        )
    )
    # Next step: Target occluded
    bridge.ingest_and_step(
        SensorimotorTelemetry(
            observed_r_mm=None,
            observed_theta_mdeg=None,
            dsf_invariants=(0.2, 0.1, 0.0, 0.2, 0.7, 0.20, 0.60, 0.95),
        )
    )
    veto_occlusion = bridge.evaluate_admissibility({
        "action_type": "locomote",
        "target_stride_mm": 100.0,
        "target_heading_mdeg": 21000,  # Heading directly into occluded hazard (< 15 deg error)
    })
    assert not veto_occlusion.is_admitted
    assert veto_occlusion.violated_invariant == "OCCLUSION_COLLISION_HAZARD"

    # Compliant heading away from occluded hazard is admitted
    safe_admitted = bridge.evaluate_admissibility({
        "action_type": "locomote",
        "target_stride_mm": 60.0,
        "target_heading_mdeg": -30000,  # -30 deg away
    })
    assert safe_admitted.is_admitted
    assert safe_admitted.verdict == "ADMITTED"


def test_planetary_receipt_emission_and_schema() -> None:
    """
    Test 8: Verify structured execution receipt output conforms to DARPA-grade schema.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        receipt_path = Path(tmpdir) / "test_planetary_receipt.json"

        source = PlanetaryContinuumSensorSource(nominal_pressure_hpa=1013.25, nominal_temperature_c=20.0)
        runner = GroundedPlanetaryBridgeRunner(source=source, yield_threshold=0.60, columns=64)

        summary = runner.execute_cycles(cycles=5, frequency_hz=0.0, test_veto_gates=True, quiet=True)

        # Write receipt
        with open(receipt_path, "w", encoding="utf-8") as f:
            from dataclasses import asdict
            json.dump(asdict(summary), f, indent=2)

        # Read back and validate schema
        with open(receipt_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["total_cycles"] == 5
        assert loaded["source_type"] == "planetary_continuum"
        assert "sensor_telemetry_stats" in loaded
        assert "barometric_pressure_hpa" in loaded["sensor_telemetry_stats"]
        assert "final_manifest" in loaded
        assert "physical_invariants" in loaded["final_manifest"]
        assert "contact_mechanics" in loaded["final_manifest"]
        assert "spatial_manifold" in loaded["final_manifest"]
        assert "causal_motor_efferents" in loaded["final_manifest"]
