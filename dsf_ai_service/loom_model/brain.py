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
    SEED_SIZE_PER_HEMISPHERE,
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
                 seed_size: int = SEED_SIZE_PER_HEMISPHERE,
                 k_neighbors: int = 16):
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
        """Step all hemispheres, process folds, and route cross-hemi spikes.

        Folding is ON by default during step — substrate-true: real cells
        divide while they live. Contact inhibition (-105) bounds growth.

        Returns dict mapping hemi_id → {neuron_id → step_result}.
        """
        # Phase 1: step each hemisphere locally
        all_results: Dict[str, Dict[str, Dict]] = {}
        for hemi in self.hemispheres:
            all_results[hemi.hemi_id] = hemi.step(input_signal, tick)

        # Phase 2: cross-hemi coupling refresh from DSF (per -98 mechanism)
        for hemi in self.hemispheres:
            for nid, couplings in hemi.cross_hemi_couplings.items():
                neuron = hemi.cluster._neuron_map.get(nid)
                if neuron is not None and neuron._last_dsf is not None:
                    couplings.update_from_dsf(neuron._last_dsf)

        # Phase 3: Folding Division
        self._last_fold_ids: Dict[str, List[str]] = {}
        for hemi in self.hemispheres:
            new_ids = hemi.cluster.process_folds(tick)
            if new_ids:
                self._last_fold_ids[hemi.hemi_id] = new_ids

        # Phase 4: collect cross-hemi spike packets from projection neurons
        all_packets = []
        for hemi in self.hemispheres:
            packets = hemi.get_spiking_projections(all_results[hemi.hemi_id])
            all_packets.extend(packets)

        # Phase 5: deliver packets to target hemispheres
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

    def recall(self, query_signals: Dict[str, Any]) -> "Counter":
        """Population-vote recall across all neurons.

        For each neuron: feed query signals through krimelack bank in a
        non-binding pass, build target state vector, find best match in
        BindingAtlas. Aggregate votes. Phase state restored after query.
        """
        from collections import Counter
        from .grandurun import grandurun_state, MODALITIES

        votes = Counter()
        for hemi in self.hemispheres:
            for neuron in hemi.cluster.neurons:
                # Snapshot pre-query (phase + winding)
                snap = {}
                for m in MODALITIES:
                    krim = neuron.krimelack_bank.get(m)
                    if krim is not None:
                        snap[m] = (
                            float(krim.phase) if hasattr(krim, 'phase') else 0.0,
                            int(krim.winding) if hasattr(krim, 'winding') else 0,
                        )

                # Symmetric attenuated query (GL-CMD-133 Δ-cosine)
                query_deltas = neuron._unwrapped_deltas(query_signals)
                target_vec = grandurun_state(query_deltas)
                best_concept, _ = neuron.binding_atlas.recall_best(target_vec)
                if best_concept is not None:
                    votes[best_concept] += 1

                # Restore phase + winding — recall must not pollute training
                for m, (p, w) in snap.items():
                    krim = neuron.krimelack_bank.get(m)
                    if krim is not None:
                        if hasattr(krim, 'phase'):
                            krim.phase = p
                        krim.winding = w

        return votes
