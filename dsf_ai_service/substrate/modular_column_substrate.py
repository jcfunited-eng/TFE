"""dsf_ai_service/substrate/modular_column_substrate.py

ArcLoom Neuromorphic Substrate: 4-Column 3D Modular Neuromorphic Substrate.

Directly bridges authentic physical sensory streams (optical raycast, cochlear audio,
somatosensory pressure/temperature, and DSF L0-L4 invariants) to the compiled native Rust
ModularSubstrate4D core (guala_core.ModularSubstrate4D) without software dictionaries or ML.

Physical Architecture (4 Functional Columns with 6-Layer Vertical Laminar Microcircuits):
  1. Column 0: Multimodal Sensory Transduction
     - Encodes optical intensity, cochlear spectral envelope, palmar contact pressure,
       and DSF L0-L4 invariants into Layer 4 granular afferents (64 trits).
  2. Column 1: Spatial & Topological Invariance
     - Maintains egocentric polar tracking (r_mm, theta_mdeg) and object permanence
       under sensory occlusion.
  3. Column 2: Causal Sequential Syntax & Combinatorial Chaining
     - Governed by asymmetric directional plastic delay fasciculi across functional columns.
  4. Column 3: Material Affordance & Barrier Gating
     - Enforces contact stress yield threshold (sigma vs Y) to prevent physical barrier collisions.

Plasticity:
  Local continuum von Mises yield stress mechanics:
    f(sigma_ij) = |sigma_ij| - Y <= 0
    delta_g_ij = eta * (|sigma_ij| - Y) * sgn(sigma_ij)
    g_ij in [-1.0, 1.0] signed contact conductance bridges.

Sleep Consolidation (Synaptic Homeostasis Hypothesis):
  Offline synaptic downscaling and competitive noise pruning.
"""

from __future__ import annotations

import math
from typing import List, Tuple, Optional, Dict, Any, Sequence
import numpy as np

import guala_core
from guala_core import ModularSubstrate4D

L4_AFFERENT_NODES = 64
L1_APICAL_NODES = 32


class ModularColumnSubstrate:
    """
    Physical 4-Column 3D Modular Neuromorphic Substrate for Guala.
    Operates under strict material yield stress plasticity and vertical laminar causal flow.
    """

    def __init__(
        self,
        yield_threshold: float = 0.60,
        plastic_rate: float = 0.03,
        activation_threshold: float = 0.25,
    ) -> None:
        self.yield_threshold = float(yield_threshold)
        self.plastic_rate = float(plastic_rate)
        self.activation_threshold = float(activation_threshold)

        # Compiled native Rust 4-Column 3D Modular Substrate
        self.substrate = ModularSubstrate4D(
            yield_threshold=self.yield_threshold,
            plastic_rate=self.plastic_rate,
            activation_threshold=self.activation_threshold,
        )

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

        # 4. DSF kernel invariants (Nodes 48..63)
        if dsf_vector is not None and len(dsf_vector) >= 8:
            for inv_idx, val in enumerate(dsf_vector[:8]):
                start_n = 48 + inv_idx * 2
                if inv_idx in (0, 1):  # D_k, M_k signed [-1, +1]
                    if val > 0.20:
                        trits[start_n] = 1
                    elif val < -0.20:
                        trits[start_n] = -1
                else:  # R_rev, U*, C_k, P_k, B_k, S_UF in [0, 1]
                    if val > 0.50:
                        trits[start_n] = 1
                    elif val < 0.20:
                        trits[start_n] = -1

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
    ) -> Tuple[int, float]:
        """
        Step one full causal cycle across all 4 cortical columns:
          1. Step intra-column vertical laminar causal flow (L4 -> L2/3 -> L5 -> L6 -> L4).
          2. Propagate inter-column directional plastic fasciculi.
          3. Update specialized Column dynamics (spatial permanence, syntax chaining, barrier gating).
          4. Execute local continuum von Mises plasticity.

        Returns: (yield_synapses_count, total_strain_energy).
        """
        return self.substrate.step(
            sensory_trits,
            somatic_trits,
            observed_r_mm,
            observed_theta_mdeg,
            float(barrier_stress),
        )

    def get_spatial_tracking(self) -> Tuple[float, int, float, bool]:
        """
        Query Column 1 (Spatial Invariance & Topological Permanent Attractor):
        Returns: (r_mm, theta_mdeg, persistence_trace, is_occluded).
        """
        return self.substrate.get_spatial_tracking()

    def is_barrier_refusal_active(self) -> bool:
        """
        Query Column 3 (Material Affordance & Barrier Gating):
        Returns whether physical barrier refusal is active under contact overstress.
        """
        return self.substrate.is_barrier_refusal_active()

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
            "yield_threshold": self.yield_threshold,
            "plastic_rate": self.plastic_rate,
            "activation_threshold": self.activation_threshold,
            "sparse_hex": raw_bytes.hex(),
            "active_synapses": self.active_synapses(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ModularColumnSubstrate:
        """Reconstitute substrate from serialized body dictionary."""
        sub = cls(
            yield_threshold=float(data.get("yield_threshold", 0.60)),
            plastic_rate=float(data.get("plastic_rate", 0.03)),
            activation_threshold=float(data.get("activation_threshold", 0.25)),
        )
        return sub
