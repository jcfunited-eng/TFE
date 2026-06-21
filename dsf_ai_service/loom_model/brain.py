"""
brain.py — LoomBrain: 8-hemisphere seed substrate with cross-hemi couplings.

GL-CMD-113 V2.4, per GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-103 Part 3.

Construction: 8 hemispheres × 50 neurons = 400 seed neurons.
Cross-hemi wiring: projection neurons (5 per hemi) coupled to adjacent
hemispheres via Watts-Strogatz topology (committed constant).
"""

from typing import Any, Dict, List

import numpy as np

from .hemisphere import LoomHemisphere
from .cross_hemi import CrossHemiCouplings
from .topology import (
    HEMISPHERE_ADJACENCY, N_HEMISPHERES,
    K_INTERHEMI, PROJECTION_NEURONS_PER_HEMI,
    validate_adjacency,
)


class LoomBrain:
    """8-hemisphere seed substrate with small-world cross-hemi coupling.

    Construction:
      1. Create 8 hemispheres with deterministic seeds derived from brain_seed
      2. Wire cross-hemi couplings between projection neurons in adjacent hemispheres
      3. Validate topology at boot

    step() propagates input through all hemispheres and routes cross-hemi spikes.
    """

    def __init__(self, brain_seed: int = 42,
                 seed_size: int = 50, k_neighbors: int = 16):
        self.brain_seed = brain_seed
        self.topology = HEMISPHERE_ADJACENCY.copy()

        # Validate topology at boot
        self._topology_metrics = validate_adjacency(self.topology)

        # Create hemispheres with deterministic seeds
        self.hemispheres: List[LoomHemisphere] = []
        for i in range(N_HEMISPHERES):
            hemi_id = f"H{i}"
            hemi_seed = brain_seed * 1000 + i  # deterministic per-hemi seed
            hemi = LoomHemisphere(
                hemi_id=hemi_id,
                seed=hemi_seed,
                seed_size=seed_size,
                k_neighbors=k_neighbors,
            )
            self.hemispheres.append(hemi)

        # Build lookup
        self._hemi_map: Dict[str, LoomHemisphere] = {
            h.hemi_id: h for h in self.hemispheres
        }

        # Wire cross-hemi couplings
        self._wire_cross_hemi()

    def _wire_cross_hemi(self):
        """Wire projection neurons to targets in adjacent hemispheres.

        Each projection neuron gets K_INTERHEMI targets distributed across
        adjacent hemispheres. Projection neurons are spread across adjacents
        so that every adjacent hemisphere gets at least one incoming projection.
        """
        rng = np.random.default_rng(self.brain_seed)

        for i, hemi in enumerate(self.hemispheres):
            adjacent = [j for j in range(N_HEMISPHERES)
                        if self.topology[i, j] == 1]

            for p_idx, proj_nid in enumerate(hemi.projection_neuron_ids):
                target_assignments = []
                for k in range(K_INTERHEMI):
                    # Rotate through adjacents: each projection neuron starts
                    # at a different offset so all adjacents get coverage
                    adj_idx = (p_idx * K_INTERHEMI + k) % len(adjacent)
                    target_hemi_idx = adjacent[adj_idx]
                    target_hemi = self.hemispheres[target_hemi_idx]
                    target_neuron = rng.choice(target_hemi.cluster.neurons)
                    target_assignments.append(
                        (target_neuron.neuron_id, target_hemi.hemi_id)
                    )

                couplings = CrossHemiCouplings(targets=target_assignments)
                hemi.cross_hemi_couplings[proj_nid] = couplings

    def step(self, input_signal, tick: int) -> Dict[str, Dict[str, Dict]]:
        """Step all hemispheres and route cross-hemi spikes.

        Returns dict mapping hemi_id → {neuron_id → step_result}.
        """
        # Phase 1: step each hemisphere locally
        all_results: Dict[str, Dict[str, Dict]] = {}
        for hemi in self.hemispheres:
            all_results[hemi.hemi_id] = hemi.step(input_signal, tick)

        # Phase 2: collect cross-hemi spike packets from projection neurons
        all_packets = []
        for hemi in self.hemispheres:
            packets = hemi.get_spiking_projections(all_results[hemi.hemi_id])
            all_packets.extend(packets)

        # Phase 3: deliver packets to target hemispheres
        for packet in all_packets:
            target_hemi = self._hemi_map.get(packet["target_hemi_id"])
            if target_hemi is not None:
                target_hemi._incoming_spikes.append(packet)

        return all_results

    def total_neurons(self) -> int:
        """Total neuron count across all hemispheres."""
        return sum(len(h.cluster.neurons) for h in self.hemispheres)

    def get_neuron(self, neuron_id: str):
        """Find a neuron by global ID (searches all hemispheres)."""
        for hemi in self.hemispheres:
            n = hemi.cluster._neuron_map.get(neuron_id)
            if n is not None:
                return n
        return None

    def topology_metrics(self) -> Dict:
        """Return validated topology metrics computed at boot."""
        return self._topology_metrics
