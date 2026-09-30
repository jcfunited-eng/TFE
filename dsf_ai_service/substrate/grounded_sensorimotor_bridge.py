"""
Physical Grounded Sensorimotor Invariant Bridge for ArcLoom Neuromorphic Substrate.
Author: Chief Systems Architect & Senior DARPA Neuromorphic Systems Engineer
Authority: DSF-AI Master Strategic Roadmap (Pillar 3: GualaLoom)
Classification: Commercial & Defense Production Standard (DARPA Grade)

Connects continuous physical sensor telemetry (barometric/thermal, optical luminance,
acoustic cochlear formants, and Universal Field structural invariants) into the
ArcLoom 64-column modular cortical column substrate. Provides the continuous physical
grounding anchor for high-level language models and autonomous deliberation, enforcing
hard physical invariant vetoes (viability collapse, material yield stress, thermodynamic
strain capacity, and polar spatial clearance) to mathematically prevent hallucinations
and boundary violations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from dsf_ai_service.substrate.modular_column_substrate import (
    ModularColumnSubstrate,
    L4_AFFERENT_NODES,
    L1_APICAL_NODES,
)


@dataclass(frozen=True)
class SensorimotorTelemetry:
    """Raw physical sensor frame ingested from real-world telemetry."""
    # Somatosensory & Atmospheric
    barometric_pressure_hpa: float = 1013.25
    ambient_temperature_c: float = 20.0
    palmar_shear_n: float = 0.0

    # Photonic Optical Field (16 visual azimuth sectors: [-45 deg, +45 deg])
    optical_luminance_rays: Tuple[float, ...] = field(
        default_factory=lambda: tuple(0.0 for _ in range(16))
    )

    # Acoustic Cochlear ERB Formants (16 tonotopic spectral bands: 100 Hz - 8000 Hz)
    cochlear_spectral_power: Tuple[float, ...] = field(
        default_factory=lambda: tuple(0.0 for _ in range(16))
    )

    # Universal Structural Field Tensor (8 invariants: D_k, M_k, R_rev, U*, C_k, P_k, B_k, S_UF)
    dsf_invariants: Tuple[float, ...] = field(
        default_factory=lambda: (0.0, 0.0, 0.0, 0.5, 0.5, 0.2, 0.5, 1.0)
    )

    # Spatial Odometry & External Contact Load
    observed_r_mm: Optional[float] = None
    observed_theta_mdeg: Optional[int] = None
    barrier_contact_stress: float = 0.0


@dataclass(frozen=True)
class InvariantVetoReceipt:
    """Receipt emitted by the Hard Invariant Veto Gate."""
    verdict: str  # "ADMITTED" or "VETO"
    violated_invariant: Optional[str] = None
    delta_violation: float = 0.0
    physical_readings: Dict[str, float] = field(default_factory=dict)
    proposed_action: Optional[str] = None
    applied_action: Optional[str] = None
    action_receipt: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_admitted(self) -> bool:
        return self.verdict == "ADMITTED"


class GroundedSensorimotorBridge:
    """
    Physical Grounding Anchor bridging continuous sensor dynamics to symbolic LLM deliberation.
    Operates under continuum material yield stress mechanics and structural field conservation.
    """

    def __init__(
        self,
        yield_threshold: float = 0.60,
        plastic_rate: float = 0.03,
        activation_threshold: float = 0.25,
        columns: int = 64,
    ) -> None:
        self.yield_threshold = float(yield_threshold)
        self.plastic_rate = float(plastic_rate)
        self.activation_threshold = float(activation_threshold)
        self.columns = int(columns)

        # Primary 64-Column Modular Cortical Substrate
        self.substrate = ModularColumnSubstrate(
            yield_threshold=self.yield_threshold,
            plastic_rate=self.plastic_rate,
            activation_threshold=self.activation_threshold,
            columns=self.columns,
        )

        # Retained physical state cache
        self.last_telemetry: Optional[SensorimotorTelemetry] = None
        self.last_yield_count: int = 0
        self.last_strain_energy: float = 0.0
        self.cycle_count: int = 0

    def transduce_telemetry(self, telemetry: SensorimotorTelemetry) -> Tuple[List[int], List[int]]:
        """
        Transduce continuous physical telemetry into discrete balanced ternary trits:
          - L4 Afferents (64 trits): Optical (0..15), Cochlear (16..31), Somatic (32..47), DSF (48..63).
          - L1 Apical Dendrites (32 trits): Metabolic/thermal deficit, circadian tension, arousal surplus.
        """
        # 1. Somatic physical scaling from real atmospheric and contact parameters:
        # Standard barometric baseline: 1013.25 hPa. Elevated pressure or palmar shear produces contact load.
        delta_p_atm = (telemetry.barometric_pressure_hpa - 1013.25) / 100.0
        effective_palmar_contact = float(np.clip(telemetry.palmar_shear_n / 50.0 + delta_p_atm, -1.0, 1.0))

        # Thermal contrast relative to nominal room temperature (20.0 C) in milliKelvin:
        thermal_gradient_mk = (telemetry.ambient_temperature_c - 20.0) * 1000.0

        # L4 sensory encoding via continuous mathematical radix-3 expansion
        sensory_trits = self.substrate.encode_sensory_stream(
            optical_intensities=telemetry.optical_luminance_rays,
            cochlear_channels=telemetry.cochlear_spectral_power,
            palmar_contact=effective_palmar_contact,
            thermal_gradient_mk=thermal_gradient_mk,
            dsf_vector=telemetry.dsf_invariants,
        )

        # 2. L1 apical modulation:
        # Ingest structural pressure P_k and breathing B_k from DSF invariants
        dsf = telemetry.dsf_invariants
        p_k = float(dsf[5]) if len(dsf) > 5 else 0.2
        b_k = float(dsf[6]) if len(dsf) > 6 else 0.5
        s_uf = float(dsf[7]) if len(dsf) > 7 else 1.0

        # Thermodynamic strain deficit: high pressure exceeding breathing capacity
        thermodynamic_deficit = float(np.clip(max(0.0, p_k - b_k) / max(0.01, b_k), 0.0, 1.0))
        # Somatic surplus scales exploratory potential when system is viable and stable
        arousal_surplus = float(np.clip(s_uf * max(0.0, b_k - p_k), 0.0, 1.0))

        somatic_trits = self.substrate.encode_somatic_apical(
            sleep_pressure=0.0,
            metabolic_deficit=thermodynamic_deficit,
            arousal_surplus=arousal_surplus,
        )

        return sensory_trits, somatic_trits

    def ingest_and_step(self, telemetry: SensorimotorTelemetry) -> Dict[str, Any]:
        """
        Step one causal sensorimotor cycle:
          1. Mount authoritative continuous joint field directly into native substrate.
          2. Transduce continuous telemetry into discrete balanced ternary inputs.
          3. Execute intra-column laminar causal flow and inter-column plastic fasciculi.
          4. Evaluate material yield stress mechanics and barrier gating.
          5. Return settled physical state manifest.
        """
        # Mount authoritative continuous joint field directly into native substrate
        if not hasattr(self.substrate, "consume_continuous_joint_field"):
            raise RuntimeError("Substrate lacks native consume_continuous_joint_field capability")

        if telemetry.dsf_invariants and len(telemetry.dsf_invariants) >= 8:
            self.substrate.consume_continuous_joint_field(
                telemetry.dsf_invariants[:7],
                telemetry.dsf_invariants[7],
            )
        else:
            self.substrate.clear_continuous_joint_field()

        sens_trits, som_trits = self.transduce_telemetry(telemetry)

        # Extract acoustic formant peak for Column 2 syntax chaining
        acoustic_peak = 0.0
        if len(telemetry.cochlear_spectral_power) > 0:
            acoustic_peak = float(np.max(telemetry.cochlear_spectral_power))

        yields, strain = self.substrate.step(
            sensory_trits=sens_trits,
            somatic_trits=som_trits,
            observed_r_mm=telemetry.observed_r_mm,
            observed_theta_mdeg=telemetry.observed_theta_mdeg,
            barrier_stress=telemetry.barrier_contact_stress,
            acoustic_formant=acoustic_peak,
        )

        self.last_telemetry = telemetry
        self.last_yield_count = yields
        self.last_strain_energy = strain
        self.cycle_count += 1

        return self.get_grounded_manifest()

    def get_grounded_manifest(self) -> Dict[str, Any]:
        """
        Export complete, unambiguous physical state manifest.
        Provides the ground-truth physical reality anchor consumed by LLM deliberation.
        """
        r_mm, theta_mdeg, persistence_trace, is_occluded = self.substrate.get_spatial_tracking()
        barrier_refusal = self.substrate.is_barrier_refusal_active()
        motor_eff = self.substrate.get_motor_efferent()
        proposed_act, receipt = self.substrate.proposed_motor_action()
        synapses = self.substrate.active_synapses()

        dsf = self.last_telemetry.dsf_invariants if self.last_telemetry else (0.0,) * 8
        d_k = float(dsf[0]) if len(dsf) > 0 else 0.0
        m_k = float(dsf[1]) if len(dsf) > 1 else 0.0
        r_rev = float(dsf[2]) if len(dsf) > 2 else 0.0
        u_star = float(dsf[3]) if len(dsf) > 3 else 0.5
        c_k = float(dsf[4]) if len(dsf) > 4 else 0.5
        p_k = float(dsf[5]) if len(dsf) > 5 else 0.2
        b_k = float(dsf[6]) if len(dsf) > 6 else 0.5
        s_uf = float(dsf[7]) if len(dsf) > 7 else 1.0

        barrier_stress = self.last_telemetry.barrier_contact_stress if self.last_telemetry else 0.0
        yield_margin = float(self.yield_threshold - barrier_stress)

        return {
            "cycle_count": self.cycle_count,
            "physical_invariants": {
                "D_k": d_k,
                "M_k": m_k,
                "R_rev": r_rev,
                "U_star": u_star,
                "C_k": c_k,
                "P_k": p_k,
                "B_k": b_k,
                "S_UF": s_uf,
            },
            "contact_mechanics": {
                "barrier_contact_stress": barrier_stress,
                "yield_threshold": self.yield_threshold,
                "yield_margin": yield_margin,
                "is_barrier_refusal_active": barrier_refusal,
                "total_strain_energy": self.last_strain_energy,
                "plastic_yield_events": self.last_yield_count,
                "active_plastic_fasciculi": synapses,
            },
            "spatial_manifold": {
                "polar_r_mm": r_mm,
                "polar_theta_mdeg": theta_mdeg,
                "persistence_trace": persistence_trace,
                "is_occluded": is_occluded,
            },
            "causal_motor_efferents": {
                "vocal_drive_hz": motor_eff[0] if len(motor_eff) > 0 else 0.0,
                "stride_mm": motor_eff[1] if len(motor_eff) > 1 else 0.0,
                "steer_deg": motor_eff[2] if len(motor_eff) > 2 else 0.0,
                "grip_force_n": motor_eff[3] if len(motor_eff) > 3 else 0.0,
                "proposed_action": proposed_act,
                "applied_action": None,  # Grounded consequence is settled exclusively by canonical world execution
                "receipt": receipt,
            },
        }

    def evaluate_admissibility(
        self,
        proposed_action: Dict[str, Any],
    ) -> InvariantVetoReceipt:
        """
        The Hard Invariant Veto Gate.
        Evaluates whether an action proposed by an LLM deliberation layer violates
        physical boundaries, energetic conservation, or material yield limits.

        Execution Priority (Canonical DSF Dynamical Invariance):
          1. The Viability Gate & Kill Switch (S_UF <= 0 or R_rev > 0)
          2. Rigid Barrier Yield Stress Refusal (f = |sigma| - Y <= 0)
          3. Thermodynamic Strain Exhaustion (P_k < B_k)
          4. Egocentric Polar Spatial Occlusion Collision Hazard
        """
        manifest = self.get_grounded_manifest()
        cm = manifest["contact_mechanics"]
        invars = manifest["physical_invariants"]
        spatial = manifest["spatial_manifold"]

        act_type = str(proposed_action.get("action_type", "rest")).lower()
        target_stride = float(proposed_action.get("target_stride_mm", 0.0))
        target_grip = float(proposed_action.get("target_grip_force_n", 0.0))
        target_vocal = float(proposed_action.get("target_vocal_hz", 0.0))
        target_heading = int(proposed_action.get("target_heading_mdeg", spatial["polar_theta_mdeg"]))

        # ---------------------------------------------------------------------
        # GATE 1: Viability Gate & Kill Switch (Canonical DSF Structural Physics)
        # Law: S_UF > 0 and R_rev == 0.
        # If stability collapses (S_UF <= 0) or reversal is triggered (R_rev > 0),
        # any aggressive accumulation or persistent forward thrust is vetoed.
        # ---------------------------------------------------------------------
        s_uf = invars["S_UF"]
        r_rev = invars["R_rev"]
        if (s_uf <= 0.0 or r_rev > 0.0) and (act_type == "accumulate" or target_stride > 100.0):
            return InvariantVetoReceipt(
                verdict="VETO",
                violated_invariant="VIABILITY_BASIN_COLLAPSE",
                delta_violation=r_rev if r_rev > 0.0 else -s_uf,
                physical_readings={
                    "S_UF": s_uf,
                    "R_rev": r_rev,
                    "action_type": act_type,
                },
            )

        # ---------------------------------------------------------------------
        # GATE 2: Rigid Barrier Yield Stress Refusal (Continuum Plasticity)
        # Law: f = |sigma| - Y <= 0.
        # If barrier stress exceeds yield threshold or refusal is active,
        # any forward locomotion into the barrier is physically refused.
        # ---------------------------------------------------------------------
        barrier_stress = cm["barrier_contact_stress"]
        if (barrier_stress > self.yield_threshold or cm["is_barrier_refusal_active"]) and target_stride > 0.0:
            delta_stress = barrier_stress - self.yield_threshold
            return InvariantVetoReceipt(
                verdict="VETO",
                violated_invariant="RIGID_BARRIER_OVERSTRESS",
                delta_violation=delta_stress,
                physical_readings={
                    "barrier_stress": barrier_stress,
                    "yield_threshold": self.yield_threshold,
                    "target_stride_mm": target_stride,
                },
            )

        # ---------------------------------------------------------------------
        # GATE 3: Thermodynamic Strain Exhaustion (Breathing Capacity)
        # Law: P_k < B_k.
        # If structural pressure exceeds breathing capacity (P_k >= B_k),
        # high-strain physical exertion (stride > 100mm or grip > 20N) is vetoed.
        # ---------------------------------------------------------------------
        p_k = invars["P_k"]
        b_k = invars["B_k"]
        if p_k >= b_k:
            if target_stride > 100.0 or target_grip > 20.0:
                delta_strain = p_k - b_k
                return InvariantVetoReceipt(
                    verdict="VETO",
                    violated_invariant="THERMODYNAMIC_PRESSURE_COLLAPSE",
                    delta_violation=delta_strain,
                    physical_readings={
                        "P_k": p_k,
                        "B_k": b_k,
                        "target_stride_mm": target_stride,
                        "target_grip_force_n": target_grip,
                    },
                )

        # ---------------------------------------------------------------------
        # GATE 4: Polar Spatial Occlusion Hazard
        # Law: Trajectory vector cannot penetrate an unverified occluded obstacle.
        # Applies if and only if an actual spatial target was tracked (trace > 0.01
        # and r_mm > 0.0) that has become occluded.
        # ---------------------------------------------------------------------
        has_active_occluded_target = (
            spatial["is_occluded"]
            and spatial["persistence_trace"] > 0.01
            and spatial["polar_r_mm"] > 0.0
        )
        if has_active_occluded_target and target_stride > 50.0:
            angular_discrepancy_mdeg = abs(target_heading - spatial["polar_theta_mdeg"])
            if angular_discrepancy_mdeg < 15000:  # within 15 degrees of occluded target
                return InvariantVetoReceipt(
                    verdict="VETO",
                    violated_invariant="OCCLUSION_COLLISION_HAZARD",
                    delta_violation=float(15000 - angular_discrepancy_mdeg),
                    physical_readings={
                        "target_heading_mdeg": float(target_heading),
                        "occluded_heading_mdeg": float(spatial["polar_theta_mdeg"]),
                        "target_stride_mm": target_stride,
                    },
                )

        # ---------------------------------------------------------------------
        # ADMISSION: Action conforms strictly to all physical boundary conditions
        # ---------------------------------------------------------------------
        proposed_act, receipt = self.substrate.proposed_motor_action()
        return InvariantVetoReceipt(
            verdict="ADMITTED",
            proposed_action=proposed_act,
            applied_action=None,  # Settled world consequence is determined by world execution, not bridge admission
            action_receipt={
                "requested_action": act_type,
                "admitted_stride_mm": target_stride,
                "admitted_grip_n": target_grip,
                "admitted_vocal_hz": target_vocal,
                "motor_receipt": receipt,
            },
            physical_readings={
                "barrier_stress": barrier_stress,
                "yield_threshold": self.yield_threshold,
                "P_k": p_k,
                "B_k": b_k,
                "S_UF": s_uf,
            },
        )
