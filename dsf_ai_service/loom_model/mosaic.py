"""
mosaic.py — LoomMosaic: multi-cluster population for recall + learning-from-exposure.

GL-CMD-LOOM-MOSAIC-STAGE4-EVE-20260620-91
Reference: GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74 Section 6 Stage 4

Composition: ordered set of LoomCluster instances.
Input routing: all clusters receive the same input (Sur's-ferrets, never pre-routing).
Recall: population-wide grandurun coherent integration.
Learning: co-occurrence binding via chi-band cofire, no supervised gradient.

NO lookup tables. NO classification. NO label matching.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .cluster import LoomCluster
from .neuron import LoomNeuron, PSI_DIM
from dsf_ai_service.v4.gualaloom_v5_engine import (
    _grandurun_select_vector,
    _SPIN_VECTOR_DIM,
    MIN_GAIN_THRESHOLD,
)


class LoomMosaic:
    """Multi-cluster population with recall and learning-from-exposure.

    All clusters receive the same input. Differentiation is Sur's-ferrets:
    each cluster starts from a different seed, so internal topology differs,
    and coupling-driven divergence accumulates through exposure.

    Recall: inject query → settle → gather 7D grandurun across ALL clusters
    → greedy coherent integration → return composition sum or None.

    Learning: expose(input_a, input_b) in same binding window.
    """

    def __init__(self,
                 name: str,
                 n_clusters: int = 3,
                 neurons_per_cluster: int = 50,
                 k_neighbors: int = 16,
                 seed: int = 0):
        self.name = name
        self.n_clusters = n_clusters
        self.neurons_per_cluster = neurons_per_cluster
        self.k_neighbors = k_neighbors
        self.seed = seed
        self._tick = 0

        self.clusters: List[LoomCluster] = []
        for i in range(n_clusters):
            cid = f"{name}_c{i}"
            c = LoomCluster(
                cluster_id=cid,
                n_neurons=neurons_per_cluster,
                k_neighbors=k_neighbors,
                seed=seed + i,
            )
            self.clusters.append(c)

    @property
    def total_neurons(self) -> int:
        return sum(len(c.neurons) for c in self.clusters)

    def all_neurons(self) -> List[LoomNeuron]:
        """Flat list of every neuron across all clusters."""
        neurons = []
        for c in self.clusters:
            neurons.extend(c.neurons)
        return neurons

    # ------------------------------------------------------------------
    # step — broadcast input to all clusters
    # ------------------------------------------------------------------

    def step(self, input_signal, tick: Optional[int] = None) -> Dict[str, Dict]:
        """Broadcast input to every cluster. Returns merged results dict."""
        if tick is None:
            tick = self._tick
        self._tick = tick + 1
        results = {}
        for cluster in self.clusters:
            r = cluster.step(input_signal, tick)
            results.update(r)
        return results

    # ------------------------------------------------------------------
    # recall — population-wide grandurun coherent integration
    # ------------------------------------------------------------------

    def recall(self, query_input, target_chi: int = 0,
               target_source: str = "corpus") -> Optional[np.ndarray]:
        """Inject query, settle, gather population grandurun, compose.

        Returns the coherent composition vector (Σψ over selected candidates),
        or None if no candidate clears MIN_GAIN_THRESHOLD.

        No dict.get(), no label matching, no classification.
        """
        tick = self._tick
        self.step(query_input, tick)

        needs_vec = np.ones(3, dtype=np.float64) / 3.0

        # Gather 7D grandurun from ALL neurons across ALL clusters
        candidates = []
        for cluster in self.clusters:
            for neuron in cluster.neurons:
                vec = neuron.get_grandurun_state(
                    target_chi, target_source, needs_vec, tick,
                )
                candidates.append((vec, neuron.neuron_id))

        if not candidates:
            return None

        target_state = np.zeros(_SPIN_VECTOR_DIM, dtype=np.complex128)
        selected_ids, alignment, dim_contributions = _grandurun_select_vector(
            candidates, target_state,
        )

        if not selected_ids or alignment < MIN_GAIN_THRESHOLD:
            return None

        # Composition vector: sum of selected candidates' state vectors
        composition = np.zeros(_SPIN_VECTOR_DIM, dtype=np.complex128)
        selected_set = set(selected_ids)
        for vec, nid in candidates:
            if nid in selected_set:
                composition += vec

        return composition

    # ------------------------------------------------------------------
    # expose — learning from co-occurrence (no supervised gradient)
    # ------------------------------------------------------------------

    def expose(self, input_a, input_b) -> None:
        """Inject input_a then input_b in the same binding window.

        The substrate's existing per-neuron chi-band binding + cofire
        spread through J_ij captures co-occurrence. No loss function,
        no expected-output labels. input_b is just a second input that
        co-occurs with input_a.
        """
        tick_a = self._tick
        self.step(input_a, tick_a)
        tick_b = self._tick
        self.step(input_b, tick_b)

    # ------------------------------------------------------------------
    # winding_signature — mosaic-wide diagnostics
    # ------------------------------------------------------------------

    def winding_signature(self) -> Dict[str, Dict[str, int]]:
        """Per-cluster winding signatures for Sur's-ferrets analysis."""
        return {
            c.cluster_id: c.winding_signature()
            for c in self.clusters
        }
