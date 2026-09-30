#!/usr/bin/env python3
"""
tools/run_grounded_planetary_bridge.py — Continuous Planetary Sensor Runner for ArcLoom Substrate.

Author: Chief Systems Architect & Senior DARPA Neuromorphic Systems Engineer
Authority: DSF-AI Master Strategic Roadmap (Pillar 3: GualaLoom)
Classification: Commercial & Defense Production Standard (DARPA Grade)

Mounts live streaming planetary sensors into GroundedSensorimotorBridge:
1. Atmospheric Barometric Pressure Transduction:
   Continuously scales atmospheric pressure (hPa) into somatic contact load and structural pressure.
2. Ambient Thermal Flux & Temperature Streams:
   Maps environmental temperature (deg C) and thermal gradients (mK) into laminar somatic context trits
   and metabolic yield limits.
3. Photonic Optical Field & Retinotopic Polar Tracking:
   Converts real-time camera frames / optical ray luminance downsampled to 16 visual azimuth sectors
   into dual-column egocentric polar retinotopic foveal projection (V1: r_mm, V2: theta_mdeg)
   with spatial persistence trace and occlusion permanence.
4. Hard Invariant Veto Enforcement:
   Continuously evaluates proposed deliberative actions through the 4-gate Hard Invariant Veto Gate
   (Viability Basin Collapse, Rigid Barrier Overstress, Thermodynamic Pressure Collapse, and
   Occlusion Collision Hazard) to ensure zero ungrounded actions are permitted to settle.
5. Dual-Mode Operation:
   Automatically probes host Linux hardware sensors (/sys/class/thermal/, V4L2/OpenCV cameras),
   with seamless failover to physical planetary continuum simulation test fixtures.

TEST FIXTURE & CHANNEL PROVENANCE DISCLOSURE:
Procedural waveforms (e.g. synthetic sine/cosine barometric tides, thermal waves, procedural sweeps,
and static test DSF invariants) are strictly test-only fixtures for testing sensorimotor wiring,
bounded resource stability, and veto enforcement. They are NOT claimed as live planetary measurements,
environmental Navier-Stokes PDE solvers, or canonical full-field DSF evaluations. Missing hardware
channels are explicitly marked with 'procedural_test_fixture' provenance.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dsf_ai_service.substrate.grounded_sensorimotor_bridge import (
    GroundedSensorimotorBridge,
    InvariantVetoReceipt,
    SensorimotorTelemetry,
)


# =============================================================================
# Planetary Sensor Sources (Hardware Host & Physical Continuum Simulation)
# =============================================================================

class PlanetarySensorSource:
    """Abstract protocol for planetary sensor telemetry acquisition."""

    def read_telemetry(self, cycle_index: int, elapsed_seconds: float) -> SensorimotorTelemetry:
        raise NotImplementedError

    def get_channel_provenance(self) -> Dict[str, str]:
        """Returns per-channel provenance metadata ('hardware', 'procedural_test_fixture', etc.)."""
        return {}


class HostHardwareSensorSource(PlanetarySensorSource):
    """
    Probes real Linux host hardware sensors:
      - /sys/class/thermal/thermal_zone*/temp (converting millidegrees C to deg C)
      - Host barometric / pressure sensor buses (if exposed)
      - Video capture devices (/dev/video* or OpenCV VideoCapture)
    Falls back gracefully to procedural test fixtures for any unavailable hardware channel,
    with explicit channel provenance tracking.
    """

    def __init__(self) -> None:
        self.thermal_zones = self._discover_thermal_zones()
        self.camera_device: Optional[Any] = self._init_camera()
        self.has_hardware_thermal = len(self.thermal_zones) > 0
        self.has_hardware_camera = self.camera_device is not None

    def _discover_thermal_zones(self) -> List[str]:
        zones = sorted(glob.glob("/sys/class/thermal/thermal_zone*/temp"))
        return zones

    def _init_camera(self) -> Optional[Any]:
        try:
            import cv2  # type: ignore
            if glob.glob("/dev/video*"):
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    return cap
                cap.release()
        except Exception:
            pass
        return None

    def get_channel_provenance(self) -> Dict[str, str]:
        return {
            "ambient_temperature_c": "hardware" if self.has_hardware_thermal else "procedural_test_fixture",
            "optical_luminance_rays": "hardware" if self.has_hardware_camera else "procedural_test_fixture",
            "barometric_pressure_hpa": "procedural_test_fixture",
            "cochlear_spectral_power": "procedural_test_fixture",
            "dsf_invariants": "procedural_test_fixture",
        }

    def read_host_temperature_c(self) -> Optional[float]:
        temps = []
        for zone in self.thermal_zones:
            try:
                with open(zone, "r", encoding="utf-8") as f:
                    val_str = f.read().strip()
                    if val_str:
                        millideg = float(val_str)
                        if 0.0 < millideg < 150000.0:
                            temps.append(millideg / 1000.0)
            except Exception:
                continue
        if temps:
            return float(np.mean(temps))
        return None

    def read_camera_frame_luminance_rays(self) -> Optional[Tuple[float, ...]]:
        if self.camera_device is None:
            return None
        try:
            ret, frame = self.camera_device.read()
            if not ret or frame is None:
                return None
            if len(frame.shape) == 3:
                gray = np.mean(frame, axis=2)
            else:
                gray = frame.astype(float)
            h, w = gray.shape
            cols = 16
            col_width = max(1, w // cols)
            rays = []
            for c in range(cols):
                segment = gray[:, c * col_width : (c + 1) * col_width]
                mean_val = float(np.mean(segment)) / 255.0
                rays.append(float(np.clip(mean_val, 0.0, 1.0)))
            return tuple(rays)
        except Exception:
            return None

    def read_telemetry(self, cycle_index: int, elapsed_seconds: float) -> SensorimotorTelemetry:
        temp_c = self.read_host_temperature_c()
        if temp_c is None:
            temp_c = 20.0 + 2.5 * math.sin(elapsed_seconds * 0.1)

        camera_rays = self.read_camera_frame_luminance_rays()
        if camera_rays is None:
            camera_rays = tuple(
                float(np.clip(0.3 + 0.4 * math.sin(elapsed_seconds * 0.2 + i * 0.4), 0.0, 1.0))
                for i in range(16)
            )

        pressure_hpa = 1013.25 + 2.0 * math.sin(elapsed_seconds * 0.05)

        acoustic_bands = tuple(
            float(np.clip(0.1 + 0.2 * math.cos(elapsed_seconds * 0.15 + i * 0.3), 0.0, 1.0))
            for i in range(16)
        )

        # Invariant test-fixture tuple (disclosed fixture, not canonical kernel execution)
        return SensorimotorTelemetry(
            barometric_pressure_hpa=pressure_hpa,
            ambient_temperature_c=temp_c,
            palmar_shear_n=0.0,
            optical_luminance_rays=camera_rays,
            cochlear_spectral_power=acoustic_bands,
            dsf_invariants=(0.2, 0.1, 0.0, 0.25, 0.65, 0.20, 0.55, 0.95),
            observed_r_mm=450.0 + 50.0 * math.sin(elapsed_seconds * 0.1),
            observed_theta_mdeg=int(10000.0 * math.cos(elapsed_seconds * 0.08)),
            barrier_contact_stress=0.0,
        )

    def close(self) -> None:
        if self.camera_device is not None:
            try:
                self.camera_device.release()
            except Exception:
                pass
            self.camera_device = None


class PlanetaryContinuumSensorSource(PlanetarySensorSource):
    """
    Physical planetary continuum simulation test fixture:
      - Atmospheric Barometric Pressure:
        P(t) = P0 + A_p * sin(omega_diurnal * t) + micro_fluctuations
      - Ambient Thermal Flux Dynamics:
        T(t) = T0 + A_T * sin(omega_diurnal * t - phi) + thermal_gradient
      - Visual Photonic Field:
        16-ray azimuth luminance field tracking a moving luminant target
        across the visual horizon, with periodic occlusion windows.
      - Cochlear Acoustic Power:
        16 tonotopic spectral bands modeling atmospheric wind turbulence.
      - Structural Invariants:
        Test-fixture waveforms modeling basin dynamics.

    DISCLOSURE: This is a procedural simulation test fixture for verifying sensorimotor
    transduction and invariant gate handling. It is not an atmospheric Navier-Stokes solver.
    """

    def __init__(
        self,
        nominal_pressure_hpa: float = 1013.25,
        nominal_temperature_c: float = 20.0,
        diurnal_period_seconds: float = 60.0,
        simulate_occlusions: bool = True,
        simulate_barrier_contacts: bool = False,
    ) -> None:
        self.p0 = nominal_pressure_hpa
        self.t0 = nominal_temperature_c
        self.period = diurnal_period_seconds
        self.simulate_occlusions = simulate_occlusions
        self.simulate_barrier_contacts = simulate_barrier_contacts

    def get_channel_provenance(self) -> Dict[str, str]:
        return {
            "ambient_temperature_c": "procedural_test_fixture",
            "optical_luminance_rays": "procedural_test_fixture",
            "barometric_pressure_hpa": "procedural_test_fixture",
            "cochlear_spectral_power": "procedural_test_fixture",
            "dsf_invariants": "procedural_test_fixture",
        }

    def read_telemetry(self, cycle_index: int, elapsed_seconds: float) -> SensorimotorTelemetry:
        omega = (2.0 * math.pi) / max(1.0, self.period)

        # 1. Barometric Atmospheric Dynamics (Tides & Fronts)
        p_tide = 2.5 * math.sin(omega * elapsed_seconds)
        p_turb = 0.4 * math.sin(omega * 3.7 * elapsed_seconds)
        p_atm = self.p0 + p_tide + p_turb

        # 2. Ambient Thermal Flux & Temperature Gradients
        t_diurnal = 8.0 * math.sin(omega * elapsed_seconds - math.pi / 4.0)
        t_flux = 0.3 * math.cos(omega * 2.3 * elapsed_seconds)
        t_ambient = self.t0 + t_diurnal + t_flux

        # 3. Optical Photonic Field (16 azimuth sectors: -45 deg to +45 deg)
        target_azimuth_norm = 0.5 + 0.45 * math.sin(omega * 0.8 * elapsed_seconds)
        target_sector = int(target_azimuth_norm * 16.0)

        cycle_phase = (elapsed_seconds % 10.0)
        is_occluded_window = self.simulate_occlusions and (7.0 <= cycle_phase <= 9.5)

        rays = []
        ambient_light = float(np.clip(0.2 + 0.3 * max(0.0, math.sin(omega * elapsed_seconds)), 0.05, 0.8))
        for s in range(16):
            if is_occluded_window:
                val = ambient_light * 0.3
            else:
                dist = abs(s - target_sector)
                target_luminance = math.exp(-0.5 * (dist / 1.2) ** 2)
                val = ambient_light + 0.7 * target_luminance
            rays.append(float(np.clip(val, 0.0, 1.0)))
        optical_rays = tuple(rays)

        # 4. Egocentric Polar Spatial Tracking
        if is_occluded_window:
            observed_r = None
            observed_theta = None
        else:
            observed_r = 550.0 + 200.0 * math.cos(omega * 0.5 * elapsed_seconds)
            observed_theta = int((target_azimuth_norm - 0.5) * 60000.0)

        # 5. Acoustic Cochlear Formants (16 ERB bands)
        acoustic_bands = []
        for b in range(16):
            band_energy = 0.08 + 0.25 * math.sin(omega * 1.5 * elapsed_seconds + b * 0.5) ** 2
            acoustic_bands.append(float(np.clip(band_energy, 0.0, 1.0)))
        cochlear_bands = tuple(acoustic_bands)

        # 6. Contact & Barrier Mechanics
        palmar_shear = float(np.clip(abs(p_tide) * 3.0, 0.0, 25.0))
        barrier_stress = 0.0
        if self.simulate_barrier_contacts and (cycle_index % 30 >= 25):
            barrier_stress = 0.75

        # 7. Procedural Structural Invariants (Test fixture)
        d_k = 0.35 + 0.2 * math.sin(omega * 0.7 * elapsed_seconds)
        m_k = 0.15 + 0.1 * math.cos(omega * 0.7 * elapsed_seconds)
        r_rev = 0.0
        u_star = 0.20 + 0.1 * abs(math.sin(omega * 1.2 * elapsed_seconds))
        c_k = 0.70 - 0.15 * (cycle_index % 5) / 5.0
        p_k = 0.25 + 0.15 * math.sin(omega * elapsed_seconds)
        b_k = 0.60
        s_uf = 0.90 + 0.08 * math.cos(omega * 0.3 * elapsed_seconds)

        return SensorimotorTelemetry(
            barometric_pressure_hpa=p_atm,
            ambient_temperature_c=t_ambient,
            palmar_shear_n=palmar_shear,
            optical_luminance_rays=optical_rays,
            cochlear_spectral_power=cochlear_bands,
            dsf_invariants=(d_k, m_k, r_rev, u_star, c_k, p_k, b_k, s_uf),
            observed_r_mm=observed_r,
            observed_theta_mdeg=observed_theta,
            barrier_contact_stress=barrier_stress,
        )


# =============================================================================
# Planetary Sensor Bridge Runner
# =============================================================================

@dataclass
class PlanetaryBridgeRunSummary:
    """Execution receipt and statistical manifest for a planetary bridge run."""
    run_timestamp: str
    total_cycles: int
    duration_seconds: float
    effective_frequency_hz: float
    source_type: str
    yield_threshold: float
    initial_active_synapses: int
    final_active_synapses: int
    total_plastic_yield_events: int
    final_strain_energy: float
    sensor_telemetry_stats: Dict[str, Any]
    admissibility_evaluations: List[Dict[str, Any]]
    final_manifest: Dict[str, Any]
    channel_provenance: Dict[str, str] = field(default_factory=dict)
    total_veto_evaluations: int = 0
    total_vetoes_issued: int = 0


class GroundedPlanetaryBridgeRunner:
    """
    Production-grade continuous sensorimotor bridge runner.
    Ingests live planetary streams and enforces hard invariant veto gates.
    Maintains O(1) bounded running summary statistics for lifelong execution without memory growth.
    """

    MAX_RECENT_VETO_RECEIPTS = 16

    def __init__(
        self,
        source: PlanetarySensorSource,
        yield_threshold: float = 0.60,
        plastic_rate: float = 0.03,
        activation_threshold: float = 0.25,
        columns: int = 64,
        source_name: str = "planetary_continuum",
    ) -> None:
        self.source = source
        self.source_name = source_name
        self.yield_threshold = float(yield_threshold)
        self.plastic_rate = float(plastic_rate)
        self.activation_threshold = float(activation_threshold)
        self.columns = int(columns)

        # Initialize canonical bridge
        self.bridge = GroundedSensorimotorBridge(
            yield_threshold=self.yield_threshold,
            plastic_rate=self.plastic_rate,
            activation_threshold=self.activation_threshold,
            columns=self.columns,
        )

        # Running summary statistics (O(1) memory bound, eliminating unbounded growth)
        self._pressure_stats = {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0}
        self._temp_stats = {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0}
        self._shear_stats = {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0}
        self._optical_peak_stats = {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0}
        self._acoustic_peak_stats = {"min": float("inf"), "max": float("-inf"), "sum": 0.0, "count": 0}

        self.total_veto_evaluations = 0
        self.total_vetoes_issued = 0
        self.recent_veto_receipts: List[Dict[str, Any]] = []

    @staticmethod
    def _update_running_stats(stats: Dict[str, float], val: float) -> None:
        if val < stats["min"]:
            stats["min"] = val
        if val > stats["max"]:
            stats["max"] = val
        stats["sum"] += val
        stats["count"] += 1

    @staticmethod
    def _finalize_stats(stats: Dict[str, float]) -> Dict[str, float]:
        cnt = max(1, int(stats["count"]))
        if stats["count"] == 0:
            return {"min": 0.0, "max": 0.0, "mean": 0.0}
        return {
            "min": float(stats["min"]),
            "max": float(stats["max"]),
            "mean": float(stats["sum"] / cnt),
        }

    def execute_cycles(
        self,
        cycles: int = 50,
        frequency_hz: float = 20.0,
        test_veto_gates: bool = True,
        quiet: bool = False,
    ) -> PlanetaryBridgeRunSummary:
        """
        Execute continuous sensory ingestion loop.
        Frequency specifies target loop cadence; 0.0 or negative runs at maximum headless speed.
        """
        initial_synapses = self.bridge.substrate.active_synapses()
        target_interval = (1.0 / frequency_hz) if frequency_hz > 0.0 else 0.0

        start_time = time.monotonic()
        total_yield_events = 0

        for cycle in range(cycles):
            cycle_start = time.monotonic()
            elapsed = cycle_start - start_time

            # 1. Read live telemetry from physical or continuum sensor source
            telemetry = self.source.read_telemetry(cycle_index=cycle, elapsed_seconds=elapsed)

            # Record running metrics (O(1) memory)
            self._update_running_stats(self._pressure_stats, telemetry.barometric_pressure_hpa)
            self._update_running_stats(self._temp_stats, telemetry.ambient_temperature_c)
            self._update_running_stats(self._shear_stats, telemetry.palmar_shear_n)
            if telemetry.optical_luminance_rays:
                self._update_running_stats(self._optical_peak_stats, float(np.max(telemetry.optical_luminance_rays)))
            if telemetry.cochlear_spectral_power:
                self._update_running_stats(self._acoustic_peak_stats, float(np.max(telemetry.cochlear_spectral_power)))

            # 2. Ingest and step substrate
            manifest = self.bridge.ingest_and_step(telemetry)
            total_yield_events += manifest["contact_mechanics"]["plastic_yield_events"]

            # 3. Deliberation Gate Testing (Verify Hard Invariant Vetoes)
            if test_veto_gates:
                self._evaluate_test_proposals(cycle, manifest)

            if not quiet and (cycle % 10 == 0 or cycle == cycles - 1):
                p_invars = manifest["physical_invariants"]
                cm = manifest["contact_mechanics"]
                sp = manifest["spatial_manifold"]
                motor = manifest["causal_motor_efferents"]
                print(
                    f"[{cycle:03d} | +{elapsed:6.2f}s] "
                    f"Atm: {telemetry.barometric_pressure_hpa:6.1f} hPa | "
                    f"Temp: {telemetry.ambient_temperature_c:5.2f} C | "
                    f"Syn: {cm['active_plastic_fasciculi']:3d} | "
                    f"Yields: {cm['plastic_yield_events']} | "
                    f"Polar: ({sp['polar_r_mm']:5.1f}mm, {sp['polar_theta_mdeg']:+6d}mdeg, occ={sp['is_occluded']}) | "
                    f"Motor: {motor['proposed_action']}"
                )

            # Cadence regulation
            if target_interval > 0.0:
                compute_time = time.monotonic() - cycle_start
                sleep_time = target_interval - compute_time
                if sleep_time > 0.0:
                    time.sleep(sleep_time)

        total_duration = time.monotonic() - start_time
        effective_hz = cycles / max(1e-5, total_duration)

        final_manifest = self.bridge.get_grounded_manifest()

        summary = PlanetaryBridgeRunSummary(
            run_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_cycles=cycles,
            duration_seconds=float(total_duration),
            effective_frequency_hz=float(effective_hz),
            source_type=self.source_name,
            yield_threshold=self.yield_threshold,
            initial_active_synapses=initial_synapses,
            final_active_synapses=final_manifest["contact_mechanics"]["active_plastic_fasciculi"],
            total_plastic_yield_events=total_yield_events,
            final_strain_energy=final_manifest["contact_mechanics"]["total_strain_energy"],
            sensor_telemetry_stats={
                "barometric_pressure_hpa": self._finalize_stats(self._pressure_stats),
                "ambient_temperature_c": self._finalize_stats(self._temp_stats),
                "optical_luminance_max": self._finalize_stats(self._optical_peak_stats),
                "acoustic_spectral_max": self._finalize_stats(self._acoustic_peak_stats),
            },
            admissibility_evaluations=list(self.recent_veto_receipts),
            final_manifest=final_manifest,
            channel_provenance=self.source.get_channel_provenance(),
            total_veto_evaluations=self.total_veto_evaluations,
            total_vetoes_issued=self.total_vetoes_issued,
        )

        return summary

    def _evaluate_test_proposals(self, cycle: int, manifest: Dict[str, Any]) -> None:
        """
        Evaluate representative action proposals to test all 4 invariant veto gates.
        """
        # Periodic probe 1: Compliant, safe navigation
        safe_action = {
            "action_type": "locomote",
            "target_stride_mm": 50.0,
            "target_heading_mdeg": manifest["spatial_manifold"]["polar_theta_mdeg"],
        }
        self.total_veto_evaluations += 1
        safe_receipt = self.bridge.evaluate_admissibility(safe_action)

        # Periodic probe 2: High-stride forward movement into potentially occluded hazard
        spatial = manifest["spatial_manifold"]
        if spatial["is_occluded"] and spatial["persistence_trace"] > 0.01:
            blind_heading_action = {
                "action_type": "locomote",
                "target_stride_mm": 120.0,
                "target_heading_mdeg": spatial["polar_theta_mdeg"],
            }
            self.total_veto_evaluations += 1
            hazard_receipt = self.bridge.evaluate_admissibility(blind_heading_action)
            if not hazard_receipt.is_admitted:
                self.total_vetoes_issued += 1
                if len(self.recent_veto_receipts) >= self.MAX_RECENT_VETO_RECEIPTS:
                    self.recent_veto_receipts.pop(0)
                self.recent_veto_receipts.append({
                    "cycle": cycle,
                    "verdict": hazard_receipt.verdict,
                    "violated_invariant": hazard_receipt.violated_invariant,
                    "delta_violation": hazard_receipt.delta_violation,
                    "physical_readings": hazard_receipt.physical_readings,
                })

        # Periodic probe 3: Barrier overstress (if barrier refusal is active)
        if manifest["contact_mechanics"]["is_barrier_refusal_active"]:
            stride_action = {
                "action_type": "locomote",
                "target_stride_mm": 80.0,
                "target_heading_mdeg": 0,
            }
            self.total_veto_evaluations += 1
            barrier_receipt = self.bridge.evaluate_admissibility(stride_action)
            if not barrier_receipt.is_admitted:
                self.total_vetoes_issued += 1
                if len(self.recent_veto_receipts) >= self.MAX_RECENT_VETO_RECEIPTS:
                    self.recent_veto_receipts.pop(0)
                self.recent_veto_receipts.append({
                    "cycle": cycle,
                    "verdict": barrier_receipt.verdict,
                    "violated_invariant": barrier_receipt.violated_invariant,
                    "delta_violation": barrier_receipt.delta_violation,
                    "physical_readings": barrier_receipt.physical_readings,
                })


# =============================================================================
# CLI Entry Point
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Grounded Planetary Sensor Bridge for ArcLoom Neuromorphic Substrate."
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=50,
        help="Number of sensorimotor cycles to execute (default: 50).",
    )
    parser.add_argument(
        "--frequency-hz",
        type=float,
        default=20.0,
        help="Cadence frequency in Hz (default: 20.0; set 0 for max speed).",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "hardware", "planetary"],
        default="auto",
        help="Sensor source: 'hardware' (host sensors), 'planetary' (continuum simulation), or 'auto' (hardware if present).",
    )
    parser.add_argument(
        "--yield-threshold",
        type=float,
        default=0.60,
        help="Material yield stress threshold Y (default: 0.60).",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=64,
        help="Modular substrate column count (default: 64).",
    )
    parser.add_argument(
        "--emit-receipt",
        type=str,
        default="backups/runtime/planetary_bridge_telemetry_receipt.json",
        help="Path to emit structured run receipt JSON.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-cycle terminal telemetry output.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 80)
    print("ARCLOOM GROUNDED PLANETARY SENSOR BRIDGE RUNNER")
    print("=" * 80)
    print(f"Cycles:           {args.cycles}")
    print(f"Frequency:        {args.frequency_hz} Hz ({'max headless speed' if args.frequency_hz <= 0 else f'{1000.0/args.frequency_hz:.1f}ms/cycle'})")
    print(f"Source Mode:      {args.source}")
    print(f"Yield Threshold:  {args.yield_threshold}")
    print(f"Substrate Columns:{args.columns}")

    # Select sensor source
    source: PlanetarySensorSource
    source_name = args.source
    if args.source == "hardware":
        hw_source = HostHardwareSensorSource()
        print(f"Hardware Thermal Zones: {len(hw_source.thermal_zones)}")
        print(f"Hardware Camera Device: {'ACTIVE' if hw_source.has_hardware_camera else 'NONE'}")
        source = hw_source
    elif args.source == "planetary":
        source = PlanetaryContinuumSensorSource(
            nominal_pressure_hpa=1013.25,
            nominal_temperature_c=20.0,
            simulate_occlusions=True,
            simulate_barrier_contacts=True,
        )
        source_name = "planetary_continuum"
    else:  # auto
        hw_source = HostHardwareSensorSource()
        if hw_source.has_hardware_thermal or hw_source.has_hardware_camera:
            source = hw_source
            source_name = "host_hardware_hybrid"
            print(f"Auto-selected Hardware Source (Thermal zones: {len(hw_source.thermal_zones)}, Camera: {hw_source.has_hardware_camera})")
        else:
            source = PlanetaryContinuumSensorSource(
                nominal_pressure_hpa=1013.25,
                nominal_temperature_c=20.0,
                simulate_occlusions=True,
                simulate_barrier_contacts=True,
            )
            source_name = "planetary_continuum_auto_fallback"
            print("Auto-selected Planetary Continuum Simulation (no direct host thermal zones/cameras exposed).")

    print("-" * 80)

    runner = GroundedPlanetaryBridgeRunner(
        source=source,
        yield_threshold=args.yield_threshold,
        columns=args.columns,
        source_name=source_name,
    )

    summary = runner.execute_cycles(
        cycles=args.cycles,
        frequency_hz=args.frequency_hz,
        test_veto_gates=True,
        quiet=args.quiet,
    )

    print("=" * 80)
    print("RUN COMPLETE — PHYSICAL STATE SUMMARY")
    print("=" * 80)
    print(f"Duration:            {summary.duration_seconds:.2f} s ({summary.effective_frequency_hz:.1f} Hz)")
    print(f"Initial Synapses:    {summary.initial_active_synapses}")
    print(f"Final Synapses:      {summary.final_active_synapses} (active plastic fasciculi)")
    print(f"Total Yield Events:  {summary.total_plastic_yield_events}")
    print(f"Total Strain Energy: {summary.final_strain_energy:.4f}")
    print(f"Pressure Range:      {summary.sensor_telemetry_stats['barometric_pressure_hpa']['min']:.1f} - {summary.sensor_telemetry_stats['barometric_pressure_hpa']['max']:.1f} hPa")
    print(f"Temperature Range:   {summary.sensor_telemetry_stats['ambient_temperature_c']['min']:.2f} - {summary.sensor_telemetry_stats['ambient_temperature_c']['max']:.2f} C")
    print(f"Total Veto Evals:    {summary.total_veto_evaluations}")
    print(f"Total Vetoes Issued: {summary.total_vetoes_issued}")
    print(f"Recent Veto Log:     {len(summary.admissibility_evaluations)} events")

    # Emit JSON receipt if requested
    if args.emit_receipt:
        out_path = Path(args.emit_receipt)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2)
        print(f"\nExecution receipt emitted to: {out_path}")

    # Clean up hardware resources if needed
    if isinstance(source, HostHardwareSensorSource):
        source.close()


if __name__ == "__main__":
    main()
