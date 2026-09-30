"""
Physical Modular Cortical Column Substrate for ArcLoom Neuromorphic Processor.
Pure continuous dynamical systems physics, discrete balanced ternary mechanics,
and deterministic material yield stress plasticity. Zero heuristics, zero ML.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple, Union
import numpy as np

import guala_core
from guala_core import ModularSubstrate4D, ModularSubstrate8D, ModularSubstrate64D

L4_AFFERENT_NODES = 64
L1_APICAL_NODES = 32


def _quantize_radix3_signed(x: float, num_trits: int = 2) -> Tuple[int, int]:
    """
    Finite continuous balanced ternary radix-3 positional projection:
        x ~ sum_{k=1}^K t_k * 3^(-k), where t_k in {-1, 0, +1}.
    Provides a deterministic 2-trit discrete projection (3^2 = 9 discrete quantized
    Voronoi intervals on [-1.0, 1.0]) for discrete balanced-ternary neuromorphic afferents.
    Note: as with any finite discrete representation, continuous values within the same
    interval map to identical trit pairs; this is a finite projection, not an unrestricted
    lossless continuous encoder.
    """
    val = min(max(float(x), -1.0), 1.0)
    trits = []
    rem = val
    power = 1.0 / 3.0
    for _ in range(num_trits):
        threshold = power / 2.0
        if rem > threshold:
            t = 1
            rem -= power
        elif rem < -threshold:
            t = -1
            rem += power
        else:
            t = 0
        trits.append(t)
        power /= 3.0
    return (trits[0], trits[1])


class ModularColumnSubstrate:
    """
    Physical Modular Neuromorphic Substrate for Guala (Defaults to 64-Column Cortical Array).
    Operates under strict material yield stress plasticity and vertical laminar causal flow.
    """

    def __init__(
        self,
        yield_threshold: float = 0.60,
        plastic_rate: float = 0.03,
        activation_threshold: float = 0.25,
        columns: int = 64,
    ) -> None:
        self._yield_threshold = float(yield_threshold)
        self._plastic_rate = float(plastic_rate)
        self._activation_threshold = float(activation_threshold)
        self.num_columns = int(columns)

        # Compiled native Rust Modular Substrate (64D, 8D, or 4D)
        if self.num_columns == 64:
            self.substrate = ModularSubstrate64D(
                yield_threshold=self._yield_threshold,
                plastic_rate=self._plastic_rate,
                activation_threshold=self._activation_threshold,
            )
        elif self.num_columns == 8:
            self.substrate = ModularSubstrate8D(
                yield_threshold=self._yield_threshold,
                plastic_rate=self._plastic_rate,
                activation_threshold=self._activation_threshold,
            )
        elif self.num_columns == 4:
            self.substrate = ModularSubstrate4D(
                yield_threshold=self._yield_threshold,
                plastic_rate=self._plastic_rate,
                activation_threshold=self._activation_threshold,
            )
        else:
            raise ValueError(f"Unsupported substrate column dimension: {self.num_columns} (must be 4, 8, or 64)")

    @property
    def yield_threshold(self) -> float:
        if hasattr(self.substrate, "yield_threshold"):
            return round(float(self.substrate.yield_threshold), 6)
        return self._yield_threshold

    @yield_threshold.setter
    def yield_threshold(self, val: float) -> None:
        self._yield_threshold = float(val)

    @property
    def plastic_rate(self) -> float:
        if hasattr(self.substrate, "plastic_rate"):
            return round(float(self.substrate.plastic_rate), 6)
        return self._plastic_rate

    @plastic_rate.setter
    def plastic_rate(self, val: float) -> None:
        self._plastic_rate = float(val)

    @property
    def activation_threshold(self) -> float:
        if hasattr(self.substrate, "activation_threshold"):
            return round(float(self.substrate.activation_threshold), 6)
        return self._activation_threshold

    @activation_threshold.setter
    def activation_threshold(self, val: float) -> None:
        self._activation_threshold = float(val)

    def zero_plastic_weights(self) -> None:
        """Zero all plastic inter-column and intra-column conductances for unconfounded plasticity ablation."""
        if hasattr(self.substrate, "zero_plastic_weights"):
            self.substrate.zero_plastic_weights()

    def encode_sensory_stream(
        self,
        optical_intensities: Optional[np.ndarray | Sequence[float]] = None,
        cochlear_channels: Optional[Sequence[Sequence[float]] | Sequence[float]] = None,
        palmar_contact: float = 0.0,
        thermal_gradient_mk: float = 0.0,
        dsf_vector: Optional[Tuple[float, ...] | Sequence[float]] = None,
    ) -> List[int]:
        """
        Encode multimodal inputs into 64 discrete ternary trits for Column 0 Layer 4 afferents:
          - Nodes 0..15: Visual luminance & spatial optical intensity (16 trits)
          - Nodes 16..31: Auditory cochlear tonotopic spectral energy (16 trits)
          - Nodes 32..47: Palmar skin contact pressure & thermal contrast (16 trits)
          - Nodes 48..63: DSF kernel invariants (D_k, M_k, R_rev, U*, C_k, P_k, B_k, S_UF) (16 trits)
        """
        trits = [0] * L4_AFFERENT_NODES

        # 1. Optical luminance field (Nodes 0..15)
        if optical_intensities is not None:
            arr = np.asarray(optical_intensities, dtype=np.float64).flatten()
            if len(arr) > 0:
                if len(arr) != 16:
                    indices = np.linspace(0, len(arr) - 1, 16)
                    arr = np.interp(indices, np.arange(len(arr)), arr)
                max_v = float(np.max(arr)) if len(arr) > 0 else 1.0
                if max_v > 0.01:
                    norm_arr = arr / max_v
                    for i in range(16):
                        if norm_arr[i] > 0.40:
                            trits[i] = 1

        # 2. Auditory cochlear tonotopic energy (Nodes 16..31)
        if cochlear_channels is not None:
            c_arr = np.asarray(cochlear_channels, dtype=np.float64).flatten()
            if len(c_arr) > 0:
                if len(c_arr) != 16:
                    indices = np.linspace(0, len(c_arr) - 1, 16)
                    c_arr = np.interp(indices, np.arange(len(c_arr)), c_arr)
                max_c = float(np.max(c_arr)) if len(c_arr) > 0 else 1.0
                if max_c > 0.001:
                    norm_c = c_arr / max_c
                    for i in range(16):
                        if norm_c[i] > 0.50:
                            trits[16 + i] = 1

        # 3. Somatosensory contact pressure & thermal gradient (Nodes 32..47)
        if abs(palmar_contact) > 0.01:
            val = 1 if palmar_contact > 0 else -1
            for i in range(8):
                trits[32 + i] = val

        if abs(thermal_gradient_mk) > 500.0:
            val = 1 if thermal_gradient_mk > 0 else -1
            for i in range(8):
                trits[40 + i] = val

        # 4. DSF kernel invariants (Nodes 48..63) via finite continuous balanced ternary radix-3 projection
        if dsf_vector is not None and len(dsf_vector) >= 8:
            for inv_idx, val in enumerate(dsf_vector[:8]):
                start_n = 48 + inv_idx * 2
                v = float(val)
                if inv_idx in (0, 1):  # D_k, M_k signed in [-1.0, 1.0]
                    t1, t2 = _quantize_radix3_signed(v)
                else:  # R_rev, U*, C_k, P_k, B_k, S_UF unsigned in [0.0, 1.0]
                    # Direct affine mapping of [0, 1] onto [-1, 1] for balanced ternary representation
                    t1, t2 = _quantize_radix3_signed(2.0 * min(max(v, 0.0), 1.0) - 1.0)
                trits[start_n] = t1
                trits[start_n + 1] = t2

        return trits

    def encode_somatic_apical(
        self,
        sleep_pressure: float = 0.0,
        metabolic_deficit: float = 0.0,
        arousal_surplus: float = 0.0,
    ) -> List[int]:
        """
        Encode global bodily arousal into 32 discrete ternary trits for Layer 1 apical modulation:
          - Nodes 0..9: Metabolic hunger deficit (10 trits)
          - Nodes 10..19: Circadian sleep pressure (10 trits)
          - Nodes 20..31: Somatic free energy surplus & exploratory arousal (12 trits)
        """
        trits = [0] * L1_APICAL_NODES

        # Metabolic deficit
        if metabolic_deficit > 0.20:
            active_k = min(10, int(metabolic_deficit * 10))
            for i in range(active_k):
                trits[i] = 1

        # Sleep pressure
        if sleep_pressure > 0.20:
            active_s = min(10, int(sleep_pressure * 10))
            for i in range(active_s):
                trits[10 + i] = 1

        # Arousal / surplus
        if arousal_surplus > 0.15:
            active_a = min(12, int(arousal_surplus * 12))
            for i in range(active_a):
                trits[20 + i] = 1

        return trits

    def step(
        self,
        sensory_trits: List[int],
        somatic_trits: List[int],
        observed_r_mm: Optional[float] = None,
        observed_theta_mdeg: Optional[int] = None,
        barrier_stress: float = 0.0,
        acoustic_formant: Union[float, Sequence[float]] = 0.0,
    ) -> Tuple[int, float]:
        """
        Step one full causal cycle across all cortical columns:
          1. Step intra-column vertical laminar causal flow.
          2. Propagate inter-column directional plastic fasciculi.
          3. Update specialized Column dynamics (spatial permanence, syntax chaining, barrier gating).
          4. Execute local continuum von Mises plasticity.

        Returns: (yield_synapses_count, total_strain_energy).
        """
        if self.num_columns == 64:
            if isinstance(acoustic_formant, (int, float)):
                formants = [float(acoustic_formant)] if acoustic_formant > 0 else []
            elif isinstance(acoustic_formant, (list, tuple)):
                formants = [float(f) for f in acoustic_formant]
            else:
                formants = []
            return self.substrate.step(
                sensory_trits,
                somatic_trits,
                observed_r_mm,
                observed_theta_mdeg,
                float(barrier_stress),
                formants,
            )
        elif self.num_columns == 8:
            single_formant = float(acoustic_formant[0]) if isinstance(acoustic_formant, (list, tuple)) and len(acoustic_formant) > 0 else float(acoustic_formant) if isinstance(acoustic_formant, (int, float)) else 0.0
            return self.substrate.step(
                sensory_trits,
                somatic_trits,
                observed_r_mm,
                observed_theta_mdeg,
                float(barrier_stress),
                single_formant,
            )
        else:
            return self.substrate.step(
                sensory_trits,
                somatic_trits,
                observed_r_mm,
                observed_theta_mdeg,
                float(barrier_stress),
            )

    def get_spatial_tracking(self) -> Tuple[float, int, float, bool]:
        """
        Query Spatial Invariance & Polar Coordinates:
        Returns: (r_mm, theta_mdeg, persistence_trace, is_occluded).
        Note: Stored polar odometry; recurrent grid decoding claim is formally withdrawn until implemented.
        """
        return self.substrate.get_spatial_tracking()

    def is_barrier_refusal_active(self) -> bool:
        """
        Query Material Affordance & Barrier Gating:
        Returns whether physical barrier refusal is active under contact overstress.
        """
        return self.substrate.is_barrier_refusal_active()

    def get_motor_efferent(self) -> Tuple[float, float, float, float]:
        """
        Query Causal Motor Efferents from Layer 5 motor pyramidal columns:
        Returns: (vocal_drive_hz, locomotion_stride_mm, steer_angle_deg, grip_force_n).
        Silent motor populations produce strictly (0.0, 0.0, 0.0, 0.0).
        """
        if hasattr(self.substrate, "get_motor_efferent"):
            eff = self.substrate.get_motor_efferent()
            if len(eff) >= 4:
                return (float(eff[0]), float(eff[1]), float(eff[2]), float(eff[3]))
            elif len(eff) >= 2:
                return (float(eff[0]), float(eff[1]), 0.0, 0.0)
            elif len(eff) == 1:
                return (float(eff[0]), 0.0, 0.0, 0.0)
        return (0.0, 0.0, 0.0, 0.0)

    def sever_tract(self, c_from: int, c_to: int) -> None:
        """Sever physical inter-column fascicular contact bridge."""
        if hasattr(self.substrate, "sever_tract"):
            self.substrate.sever_tract(c_from, c_to)

    def reconnect_tract(self, c_from: int, c_to: int) -> None:
        """Reconnect physical inter-column fascicular contact bridge."""
        if hasattr(self.substrate, "reconnect_tract"):
            self.substrate.reconnect_tract(c_from, c_to)

    def is_tract_severed(self, c_from: int, c_to: int) -> bool:
        """Query whether physical inter-column fascicular tract is severed."""
        if hasattr(self.substrate, "is_tract_severed"):
            return bool(self.substrate.is_tract_severed(c_from, c_to))
        return False

    def proposed_kinematic_action(self, dt_s: float = 0.05) -> Tuple[dict[str, Any], dict[str, Any]]:
        """
        Query read-only proposed kinematic consequence and intention receipt (A4-01).
        Efferents operate along distinct physical axes without cross-dimensional scalar ranking.
        Does NOT execute or settle real actions; unavailable physical load/work quantities
        (acoustic pressure, normal force, mechanical work) report strictly as None because
        they can only be determined upon canonical world settlement.

        Returns:
            (proposed_consequence, proposed_receipt)
        """
        vocal, stride, steer, grip = self.get_motor_efferent()
        is_silent = (vocal == 0.0 and stride == 0.0 and steer == 0.0 and grip == 0.0)

        # 2D Euclidean rigid body kinematics proposal
        th_rad = float(np.radians(steer))
        delta_x_mm = float(stride * np.cos(th_rad))
        delta_y_mm = float(stride * np.sin(th_rad))
        delta_theta_deg = float(steer * (stride / 60.0))

        proposed_consequence = {
            "delta_x_mm": delta_x_mm,
            "delta_y_mm": delta_y_mm,
            "delta_theta_deg": delta_theta_deg,
            "acoustic_pressure_pa": None,
            "normal_force_n": None,
            "mechanical_work_uj": None,
        }

        proposed_receipt = {
            "is_silent": is_silent,
            "motion_vector": (delta_x_mm, delta_y_mm, delta_theta_deg),
            "vocal_frequency_hz": vocal,
            "normal_force_n": None,
            "applied_stride_mm": stride,
            "applied_steer_deg": steer,
            "cycle_dt_s": dt_s,
        }

        return (proposed_consequence, proposed_receipt)

    def applied_kinematic_action(self, dt_s: float = 0.05) -> Tuple[dict[str, Any], dict[str, Any]]:
        """Deprecated ungrounded kinematic estimate; delegates to proposed_kinematic_action."""
        return self.proposed_kinematic_action(dt_s=dt_s)

    def applied_motor_action(self) -> Tuple[str, dict[str, Any]]:
        """
        Multi-axis kinematic summary without cross-dimensional scalar ranking:
        Returns ('rest', {}) if silent, or ('active', receipt) with independent channels.
        """
        consequence, receipt = self.proposed_kinematic_action()
        if receipt["is_silent"]:
            return ("rest", {})
        return ("active", receipt)

    def active_synapses(self) -> int:
        """
        Return the total number of active plastic conductances (|g| > 0.001)
        across intra-column laminar microcircuits and inter-column fasciculi.
        """
        return self.substrate.active_synapses()

    def sleep_consolidation(
        self,
        decay: float = 0.02,
        prune_thresh: float = 0.005,
    ) -> Tuple[int, int]:
        """
        Offline nocturnal sleep consolidation and synaptic downscaling (Synaptic Homeostasis Hypothesis).
        Returns: (decayed_count, pruned_count).
        """
        return self.substrate.sleep_consolidation(float(decay), float(prune_thresh))

    def export_sparse_bytes(self) -> bytes:
        """Export sparse active conductances as raw byte stream."""
        return bytes(self.substrate.export_sparse())

    def to_dict(self) -> dict:
        """Serialize substrate configuration and sparse conductances for persistent body storage."""
        raw_bytes = self.export_sparse_bytes()
        return {
            "format": "ARCLOOM3",
            "num_columns": self.num_columns,
            "yield_threshold": self.yield_threshold,
            "plastic_rate": self.plastic_rate,
            "activation_threshold": self.activation_threshold,
            "sparse_hex": raw_bytes.hex(),
            "active_synapses": self.active_synapses(),
        }

    @classmethod
    def from_dict(cls, data: dict, force_columns: Optional[int] = None) -> ModularColumnSubstrate:
        """
        Reconstitute substrate from serialized body dictionary with fail-closed binary verification.
        Preserves column dimension unless explicitly instructed.
        """
        sparse_hex = data.get("sparse_hex")
        if not sparse_hex or not isinstance(sparse_hex, str) or len(sparse_hex.strip()) == 0:
            raise ValueError("missing or empty sparse_hex payload: cannot restore without valid state payload")

        num_cols = force_columns if force_columns is not None else int(data.get("num_columns", 64))
        sub = cls(
            yield_threshold=float(data.get("yield_threshold", 0.60)),
            plastic_rate=float(data.get("plastic_rate", 0.03)),
            activation_threshold=float(data.get("activation_threshold", 0.25)),
            columns=num_cols,
        )
        raw = bytes.fromhex(sparse_hex.strip())
        sub.substrate.import_sparse(raw)
        return sub
