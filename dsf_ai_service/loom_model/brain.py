"""Physical Loom brain: hemispheres, neurons, and cross-hemisphere coupling.

Per-neuron ChiAtlas/BindingAtlas recall and label injection are intentionally
absent. Meaning is owned by authenticated causal experience and THING mosaics;
this class advances the neuron population without assigning semantic identity.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import numpy as np

from .cross_hemi import CrossHemiCouplings
from .hemisphere import LoomHemisphere
from .topology import (
    HEMISPHERE_ADJACENCY,
    K_INTERHEMI,
    N_HEMISPHERES,
    SEED_SIZE_PER_HEMISPHERE,
    validate_adjacency,
)


class LoomBrain:
    """Eight deterministic hemispheres joined by physical couplings."""

    def __init__(
        self,
        brain_seed: int = 42,
        seed_size: int = SEED_SIZE_PER_HEMISPHERE,
        k_neighbors: int = 16,
        hemisphere_primary_modality: Optional[Dict[str, str]] = None,
        observable: Optional[str] = None,
    ):
        self.brain_seed = brain_seed
        self.topology = HEMISPHERE_ADJACENCY.copy()
        self.observable = (
            observable
            or os.environ.get("COGNITION_OBSERVABLE")
            or "resonant_spectral"
        )
        self._topology_metrics = validate_adjacency(self.topology)
        primary_map = (
            hemisphere_primary_modality
            if hemisphere_primary_modality is not None
            else {}
        )

        self.hemispheres: List[LoomHemisphere] = []
        for index in range(N_HEMISPHERES):
            hemi_id = f"H{index}"
            self.hemispheres.append(
                LoomHemisphere(
                    hemi_id=hemi_id,
                    seed=brain_seed * 1000 + index,
                    seed_size=seed_size,
                    k_neighbors=k_neighbors,
                    primary_modality=primary_map.get(
                        hemi_id,
                        "physical_signal",
                    ),
                    observable=self.observable,
                )
            )
        self._hemi_map: Dict[str, LoomHemisphere] = {
            hemisphere.hemi_id: hemisphere
            for hemisphere in self.hemispheres
        }
        self._last_fold_ids: Dict[str, List[str]] = {}
        self._injection_floor_skips = 0
        self._spike_bus = None
        self._guala_ref = None
        self._wire_cross_hemi()

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_spike_bus", None)
        state.pop("_guala_ref", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def set_spike_bus(self, spike_bus) -> None:
        """Retain physical spike-bus wiring without semantic entry routing."""
        self._spike_bus = spike_bus

    def wire_mood_broadcast(self, mood_source) -> None:
        """Attach the read-only somatic modulation source to every neuron."""
        for hemisphere in self.hemispheres:
            for neuron in hemisphere.cluster.neurons:
                neuron.set_mood_source(mood_source)

    def _wire_cross_hemi(self) -> None:
        """Wire projection neurons to adjacent hemispheres deterministically."""
        rng = np.random.default_rng(self.brain_seed)
        for source_index, hemisphere in enumerate(self.hemispheres):
            adjacent = [
                target_index
                for target_index in range(N_HEMISPHERES)
                if self.topology[source_index, target_index] == 1
            ]
            for projection_index, neuron_id in enumerate(
                hemisphere.projection_neuron_ids
            ):
                targets = []
                for offset in range(K_INTERHEMI):
                    adjacent_index = (
                        projection_index * K_INTERHEMI + offset
                    ) % len(adjacent)
                    target_hemisphere = self.hemispheres[
                        adjacent[adjacent_index]
                    ]
                    target_neuron = rng.choice(
                        target_hemisphere.cluster.neurons)
                    targets.append(
                        (target_neuron.neuron_id, target_hemisphere.hemi_id)
                    )
                hemisphere.cross_hemi_couplings[neuron_id] = (
                    CrossHemiCouplings(targets=targets)
                )

    def step(
        self,
        input_signal,
        tick: int,
        input_chi: Optional[int] = None,
        modality: Optional[str] = None,
    ) -> Dict[str, Dict[str, Dict]]:
        """Advance every neuron and propagate physical cross-hemi spikes.

        ``input_chi`` and ``modality`` remain signature-compatible with the
        retiring engine shell but have no routing or identity authority.
        """
        del input_chi, modality
        all_results: Dict[str, Dict[str, Dict]] = {}
        for hemisphere in self.hemispheres:
            all_results[hemisphere.hemi_id] = hemisphere.step(
                input_signal,
                tick,
            )

        for hemisphere in self.hemispheres:
            for neuron_id, couplings in (
                hemisphere.cross_hemi_couplings.items()
            ):
                neuron = hemisphere.cluster._neuron_map.get(neuron_id)
                if neuron is not None and neuron._last_dsf is not None:
                    couplings.update_from_dsf(neuron._last_dsf)

        self._last_fold_ids = {}
        for hemisphere in self.hemispheres:
            new_ids = hemisphere.cluster.process_folds(tick)
            if new_ids:
                self._last_fold_ids[hemisphere.hemi_id] = new_ids

        packets = []
        for hemisphere in self.hemispheres:
            packets.extend(
                hemisphere.get_spiking_projections(
                    all_results[hemisphere.hemi_id]
                )
            )
        for packet in packets:
            target = self._hemi_map.get(packet["target_hemi_id"])
            if target is not None:
                target._incoming_spikes.append(packet)
        return all_results

    def total_neurons(self) -> int:
        return sum(
            len(hemisphere.cluster.neurons)
            for hemisphere in self.hemispheres
        )

    def get_neuron(self, neuron_id: str):
        for hemisphere in self.hemispheres:
            neuron = hemisphere.cluster._neuron_map.get(neuron_id)
            if neuron is not None:
                return neuron
        return None

    def topology_metrics(self) -> Dict:
        return self._topology_metrics
