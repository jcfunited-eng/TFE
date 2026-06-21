"""
hemisphere.py — LoomHemisphere: one brain region with local cluster + projection neurons.

GL-CMD-113 V2.2.

Each hemisphere contains one LoomCluster at seed. Projection neurons
(5 per hemisphere) carry cross-hemi couplings to adjacent hemispheres.
No pre-assigned cognitive specialization — names are H0..H7 placeholders.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from .cluster import LoomCluster
from .cross_hemi import CrossHemiCouplings
from .topology import PROJECTION_NEURONS_PER_HEMI, K_INTERHEMI


class LoomHemisphere:
    """One hemisphere of the LoomBrain.

    Contains a LoomCluster (the local neural population) and manages
    cross-hemi projection neurons that carry signals between hemispheres.
    """

    def __init__(self, hemi_id: str, seed: int = 0,
                 seed_size: int = 50, k_neighbors: int = 16):
        self.hemi_id = hemi_id
        self.seed = seed
        self.seed_size = seed_size

        # Local cluster
        self.cluster = LoomCluster(
            cluster_id=hemi_id,
            n_neurons=seed_size,
            k_neighbors=k_neighbors,
            seed=seed,
        )

        # Designate projection neurons (deterministic from seed)
        rng = np.random.default_rng(seed)
        indices = rng.choice(seed_size, size=PROJECTION_NEURONS_PER_HEMI, replace=False)
        self.projection_neuron_ids: List[str] = [
            self.cluster.neurons[i].neuron_id for i in sorted(indices)
        ]

        # Cross-hemi couplings: neuron_id → CrossHemiCouplings
        self.cross_hemi_couplings: Dict[str, CrossHemiCouplings] = {}

        # Incoming spike queue: filled by brain during cross-hemi routing
        self._incoming_spikes: List[Dict[str, Any]] = []

    def step(self, input_signal, tick: int) -> Dict[str, Dict]:
        """Step the local cluster, then process incoming cross-hemi spikes."""
        results = self.cluster.step(input_signal, tick)

        # Process incoming cross-hemi spikes from other hemispheres
        for spike in self._incoming_spikes:
            target_id = spike["target_neuron_id"]
            target = self.cluster._neuron_map.get(target_id)
            if target is not None:
                target.receive_coupling_spike(
                    spike["source_neuron_id"],
                    spike["J_weight"],
                    spike["source_dsf"],
                    tick,
                )
        self._incoming_spikes.clear()

        return results

    def get_spiking_projections(self, step_results: Dict[str, Dict]) -> List[Dict]:
        """Return list of cross-hemi spike packets from spiking projection neurons."""
        packets = []
        for nid in self.projection_neuron_ids:
            result = step_results.get(nid, {})
            if not result.get("committed"):
                continue
            neuron = self.cluster._neuron_map.get(nid)
            if neuron is None:
                continue
            couplings = self.cross_hemi_couplings.get(nid)
            if couplings is None:
                continue
            for idx, (target_nid, target_hemi_id) in enumerate(couplings.targets):
                packets.append({
                    "source_neuron_id": nid,
                    "source_hemi_id": self.hemi_id,
                    "target_neuron_id": target_nid,
                    "target_hemi_id": target_hemi_id,
                    "J_weight": couplings.get_weight(idx),
                    "source_dsf": neuron._last_dsf,
                })
        return packets
