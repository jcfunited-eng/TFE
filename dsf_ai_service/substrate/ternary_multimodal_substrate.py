"""dsf_ai_service/substrate/ternary_multimodal_substrate.py

ArcLoom Neuromorphic Substrate: 1,024-Node Multi-Modal Ternary Contact Matrix.

Directly bridges authentic physical sensory streams (cochlear audio, optical raycast,
somatosensory pressure, and DSF L0-L4 invariants) to the compiled native Rust
TernaryLattice core (guala_core.TernaryLattice) without software dictionaries or ML.

Physical Topology (N = 1,024 nodes):
  1. Optical / Visual Retinotopic Field: Nodes 0..255 (256 nodes)
     - Encodes optical intensity and spatial luminance gradients.
     - Natural receptive fields: localized illumination (+1) against resting dark background (0).
  2. Cochlear / Auditory Tonotopic Sheet: Nodes 256..511 (256 nodes)
     - 16 ERB cochlear frequency channels x 16 time frames (2D tonotopic sheet).
     - Independent outer-hair-cell automatic gain control (AGC) per frequency band.
  3. Somatosensory, Thermal & Kinematic Field: Nodes 512..767 (256 nodes)
     - Encodes palmar contact pressure, thermal gradient, and egocentric displacement.
  4. DSF Kernel Invariants & Motor Efferents: Nodes 768..1023 (256 nodes)
     - Nodes 768..895: DSF L0-L4 basin physics (D_k, M_k, R_rev, U*, C_k, P_k, B_k, S_UF).
     - Nodes 896..1023: Airway vocal articulators (11 Onsets, 5 Vowels, 4 Pitches) & motor drives.

Plasticity:
  Local continuum von Mises yield stress mechanics:
    f(σ_ij) = |σ_ij| - Y <= 0
    Δg_ij = η * (|σ_ij| - Y) * sgn(σ_ij)
    g_ij ∈ [-1.0, 1.0] (signed contact bridges: in-phase vs anti-phase coupling).

Offline Dream Replay & Sleep Consolidation (Phase 4):
  - High-salience waking Krimelacks replayed during quiescence (M_k ≈ 0).
  - Synaptic downscaling and noise pruning (Synaptic Homeostasis Hypothesis).
"""

from __future__ import annotations

import math
from typing import List, Tuple, Optional, Dict, Any, Sequence
import numpy as np

import guala_core
from guala_core import TernaryLattice

# Substrate Receptive Field Partitioning
VISUAL_START = 0
VISUAL_END = 256

AUDITORY_START = 256
AUDITORY_END = 512

SOMATIC_START = 512
SOMATIC_END = 768

EFFERENT_START = 768
EFFERENT_END = 1024

TOTAL_NODES = 1024


class TernaryMultiModalSubstrate:
    """
    Physical 1,024-Node Discrete Ternary Neuromorphic Substrate for Guala.
    Operates under strict material yield stress plasticity and Content-Addressable Memory (CAM) dynamics.
    """

    def __init__(
        self,
        yield_threshold: float = 0.35,
        plastic_rate: float = 0.30,
        activation_threshold: float = 0.35,
    ) -> None:
        self.yield_threshold = float(yield_threshold)
        self.plastic_rate = float(plastic_rate)
        self.activation_threshold = float(activation_threshold)

        # Native Rust compiled 1,024-node lattice with 1,048,576 symmetric synaptic contacts
        self.lattice = TernaryLattice(
            yield_threshold=self.yield_threshold,
            plastic_rate=self.plastic_rate,
            activation_threshold=self.activation_threshold,
        )

    def encode_visual_field(self, optical_intensities: np.ndarray, target_active: int = 12) -> List[int]:
        """
        Encode continuous optical intensities (from raycast or retinal pixels) into 256 trits.
        Illumination above threshold produces +1 trits; dark resting background stays at 0 trits.
        """
        trits = [0] * (VISUAL_END - VISUAL_START)
        arr = np.asarray(optical_intensities, dtype=np.float64).flatten()
        if len(arr) == 0:
            return trits

        if len(arr) != len(trits):
            indices = np.linspace(0, len(arr) - 1, len(trits))
            arr = np.interp(indices, np.arange(len(arr)), arr)

        max_v = float(np.max(arr)) if len(arr) > 0 else 1.0
        if max_v > 0.01:
            norm_arr = arr / max_v
            top_pos = np.argsort(norm_arr)[-target_active:]
            for idx in top_pos:
                if norm_arr[idx] > 0.40:
                    trits[idx] = 1

        return trits

    def encode_cochlear_field_2d(
        self,
        cochlear_channels_32: Tuple[Tuple[float, ...], ...] | Sequence[Sequence[float]],
        target_active: int = 14,
    ) -> List[int]:
        """
        Encode 16-channel cochlear envelope frames into a 2D tonotopic sheet (16 channels x 16 frames = 256 nodes).
        Applies per-channel automatic gain control (AGC) to prevent low-frequency masking.
        """
        trits = [0] * (AUDITORY_END - AUDITORY_START)
        cochlea_2d = np.zeros((16, 16), dtype=np.float64)

        for ch in range(16):
            if ch < len(cochlear_channels_32):
                env = np.array(cochlear_channels_32[ch][:16])
                max_v = np.max(env) if len(env) > 0 else 0.0
                if max_v > 0.001:
                    cochlea_2d[ch, :len(env)] = env / max_v

        # Select most salient tonotopic-temporal cells
        flat_indices = np.argsort(cochlea_2d.flatten())[-target_active:]
        for idx_flat in flat_indices:
            if cochlea_2d.flatten()[idx_flat] > 0.70:
                trits[idx_flat] = 1

        return trits

    def encode_somatic_field(
        self,
        contact_load: float,
        thermal_gradient: float,
        displacement: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        target_active: int = 8,
    ) -> List[int]:
        """
        Encode tactile load, temperature, and kinematic displacement into 256 trits.
        """
        trits = [0] * (SOMATIC_END - SOMATIC_START)
        k = max(1, target_active // 3)

        if abs(contact_load) > 0.01:
            val = 1 if contact_load > 0 else -1
            for i in range(k):
                trits[i * 7] = val

        if abs(thermal_gradient) > 0.01:
            val = 1 if thermal_gradient > 0 else -1
            for i in range(k):
                trits[86 + i * 7] = val

        dx, dy, dz = displacement
        mag = math.sqrt(dx * dx + dy * dy + dz * dz)
        if mag > 0.01:
            val = 1 if dx + dy + dz >= 0 else -1
            for i in range(k):
                trits[171 + i * 7] = val

        return trits

    def encode_dsf_and_efferents(
        self,
        dsf_vector: Optional[Tuple[float, ...]] = None,
        onset_idx: Optional[int] = None,
        vowel_idx: Optional[int] = None,
        pitch_idx: Optional[int] = None,
    ) -> List[int]:
        """
        Encode 8-dim DSF kernel invariants and airway vocal articulators into 256 trits.
        - Nodes 0..127: DSF invariants (D_k, M_k, R_rev, U*, C_k, P_k, B_k, S_UF)
        - Nodes 128..255: Efferent vocal articulators (11 Onsets, 5 Vowels, 4 Pitches)
        """
        trits = [0] * (EFFERENT_END - EFFERENT_START)

        # 1. Encode 8-dim DSF invariants into 128 nodes
        if dsf_vector is not None and len(dsf_vector) >= 8:
            for inv_idx, val in enumerate(dsf_vector[:8]):
                start_n = inv_idx * 16
                if inv_idx in (0, 1):  # D_k, M_k signed [-1, +1]
                    if val > 0.2:
                        trits[start_n] = 1
                        trits[start_n + 1] = 1
                    elif val < -0.2:
                        trits[start_n] = -1
                        trits[start_n + 1] = -1
                else:  # R_rev, U*, C_k, P_k, B_k, S_UF [0, 1]
                    if val > 0.5:
                        trits[start_n] = 1
                        trits[start_n + 1] = 1
                    elif val < 0.2:
                        trits[start_n] = -1
                        trits[start_n + 1] = -1

        # 2. Encode vocal articulators into nodes 128..255
        # Onset: 11 categories -> 44 nodes (4 nodes per onset)
        if onset_idx is not None and 0 <= onset_idx < 11:
            base = 128 + onset_idx * 4
            trits[base] = 1
            trits[base + 1] = 1

        # Vowel: 5 categories -> 40 nodes (8 nodes per vowel)
        if vowel_idx is not None and 0 <= vowel_idx < 5:
            base = 128 + 44 + vowel_idx * 8
            trits[base] = 1
            trits[base + 1] = 1

        # Pitch: 4 categories -> 32 nodes (8 nodes per pitch)
        if pitch_idx is not None and 0 <= pitch_idx < 4:
            base = 128 + 44 + 40 + pitch_idx * 8
            trits[base] = 1
            trits[base + 1] = 1

        return trits

    def assemble_multimodal_vector(
        self,
        visual_trits: List[int],
        auditory_trits: List[int],
        somatic_trits: List[int],
        efferent_trits: List[int],
    ) -> List[int]:
        """
        Assemble the complete 1,024-node ternary state vector.
        """
        assert len(visual_trits) == 256
        assert len(auditory_trits) == 256
        assert len(somatic_trits) == 256
        assert len(efferent_trits) == 256

        return visual_trits + auditory_trits + somatic_trits + efferent_trits

    def present_experience(self, pattern_1024: List[int]) -> Tuple[int, float]:
        """
        Present a live multi-modal experience and execute local material yield plasticity.
        Returns: (yielding_synapses_count, plastic_strain_energy).
        """
        return self.lattice.present_and_yield(pattern_1024)

    def replay_krimelack(self, pattern_1024: List[int], factor: float = 1.0) -> Tuple[int, float]:
        """
        Replay an experiential Krimelack pattern through the matrix during offline sleep.
        Applies local yield plasticity with an optional plastic boost factor.
        Returns: (yielding_synapses_count, plastic_strain_energy).
        """
        return self.lattice.replay_pattern(pattern_1024, factor)

    def sleep_decay_and_prune(self, decay_factor: float = 0.05, min_conductance: float = 0.02) -> Tuple[int, int]:
        """
        Sleep synaptic downscaling and noise pruning (Synaptic Homeostasis Hypothesis).
        Scales conductances by (1.0 - decay_factor) and zeroes out those with |g_ij| < min_conductance.
        Returns: (decayed_count, pruned_count).
        """
        return self.lattice.decay_and_prune(decay_factor, min_conductance)

    def project_and_readout(self, cue_1024: List[int]) -> Tuple[Dict[str, Optional[int]], List[int]]:
        """
        Execute feedforward resonant projection and decode motor efferents and completed state.
        Uses continuous physical excitation energy integrated across articulatory columnar channels.
        """
        exc = self.lattice.compute_node_excitations(cue_1024)
        recalled_state = [1 if x > self.activation_threshold else (-1 if x < -self.activation_threshold else 0) for x in exc]

        vocal_exc = exc[EFFERENT_START + 128 : EFFERENT_END]

        onset_scores = [sum(vocal_exc[i * 4 : (i + 1) * 4]) for i in range(11)]
        vowel_scores = [sum(vocal_exc[44 + i * 8 : 44 + (i + 1) * 8]) for i in range(5)]
        pitch_scores = [sum(vocal_exc[44 + 40 + i * 8 : 44 + 40 + (i + 1) * 8]) for i in range(4)]

        rec_onset = int(np.argmax(onset_scores)) if max(onset_scores) > self.activation_threshold else None
        rec_vowel = int(np.argmax(vowel_scores)) if max(vowel_scores) > self.activation_threshold else None
        rec_pitch = int(np.argmax(pitch_scores)) if max(pitch_scores) > self.activation_threshold else None

        decoded = {
            "onset_idx": rec_onset,
            "vowel_idx": rec_vowel,
            "pitch_idx": rec_pitch,
        }

        return decoded, recalled_state

    def export_sparse(self) -> List[Tuple[int, int, float]]:
        """Export all non-zero synaptic conductances as (i, j, g_ij) tuples."""
        return self.lattice.export_sparse_conductances()

    def import_sparse(self, entries: List[Tuple[int, int, float]]) -> None:
        """Import sparse synaptic conductances into the 1,024-node matrix."""
        self.lattice.import_sparse_conductances(entries)

    def matrix_statistics(self) -> Tuple[float, float, int]:
        """Return (mean_active_conductance, max_conductance, active_synapse_count)."""
        return self.lattice.matrix_statistics()

    def to_dict(self) -> dict:
        """Serialize substrate configuration and sparse conductances for persistent body storage."""
        sparse = self.export_sparse()
        filtered = [e for e in sparse if abs(e[2]) >= 0.005]
        filtered.sort(key=lambda x: abs(x[2]), reverse=True)
        bounded = filtered[:1024]
        return {
            "yield_threshold": self.yield_threshold,
            "plastic_rate": self.plastic_rate,
            "activation_threshold": self.activation_threshold,
            "sparse_conductances": [[int(i), int(j), round(float(g), 5)] for i, j, g in bounded],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TernaryMultiModalSubstrate":
        """Reconstitute substrate from serialized body dictionary."""
        sub = cls(
            yield_threshold=float(data.get("yield_threshold", 0.35)),
            plastic_rate=float(data.get("plastic_rate", 0.30)),
            activation_threshold=float(data.get("activation_threshold", 0.35)),
        )
        sparse = data.get("sparse_conductances", [])
        if sparse:
            sub.import_sparse([(int(e[0]), int(e[1]), float(e[2])) for e in sparse])
        return sub

    def clear(self) -> None:
        """Reset lattice conductances to virgin state."""
        self.lattice.clear()
