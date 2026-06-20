"""
cluster.py — LoomCluster: population of coupled LoomNeurons (Stage 2).

GL-CMD-LOOM-CLUSTER-STAGE2-EVE-20260620-79
Reference spec: GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74

Stage 2 adds:
  - K=16 ring-topology coupling per neuron
  - Phase A/B/C step cycle (independent → coupling → refresh)
  - Population grandurun composition via _grandurun_select_vector
  - Sur's-ferrets differentiation (identical neurons, input differentiates)

NO production imports beyond Stage 1's existing reuses.
NO writes to production atlas. NO ECS/S3/deploy.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .neuron import (
    LoomNeuron,
    CouplingsJij,
    PSI_DIM,
    J_BASE,
    J_MAX,
)
from dsf_ai_service.v4.gualaloom_v5_engine import (
    _grandurun_select_vector,
    _SPIN_VECTOR_DIM,
)


class LoomCluster:
    """Population of N coupled LoomNeurons with ring-topology J_ij.

    step() executes three phases per tick:
      Phase A — independent: every neuron runs its own step()
      Phase B — coupling:    spiking neurons propagate to neighbors
      Phase C — refresh:     each neuron recomputes J_ij from DSF

    emit() runs greedy coherent-integration over the population's
    7D grandurun state vectors.
    """

    def __init__(self,
                 cluster_id: str,
                 n_neurons: int = 50,
                 k_neighbors: int = 16,
                 dna_blueprints: Optional[List[Any]] = None,
                 seed: Optional[int] = None):
        """
        Args:
            cluster_id:     unique identifier for this cluster
            n_neurons:      number of neurons in the population
            k_neighbors:    coupling fan-out per neuron (Stage 2: 16)
            dna_blueprints: optional list of N blueprints to distribute
            seed:           deterministic RNG seed (topology is ring-based
                            so seed is only used if future stages add
                            stochastic elements)
        """
        self.cluster_id = cluster_id
        self.n_neurons = n_neurons
        self.k_neighbors = min(k_neighbors, n_neurons - 1)
        self.seed = seed

        # --- Instantiate neurons ---
        self.neurons: List[LoomNeuron] = []
        for i in range(n_neurons):
            nid = f"{cluster_id}_n{i}"
            bp = None
            if dna_blueprints is not None and i < len(dna_blueprints):
                bp = dna_blueprints[i]
            self.neurons.append(LoomNeuron(nid, dna_blueprint=bp))

        # Fast lookup by neuron_id
        self._neuron_map: Dict[str, LoomNeuron] = {
            n.neuron_id: n for n in self.neurons
        }

        # --- Build ring-distance connectivity ---
        self._build_ring_topology()

    # ------------------------------------------------------------------
    # Topology
    # ------------------------------------------------------------------

    def _build_ring_topology(self) -> None:
        """Assign K nearest neighbors per neuron on a ring.

        Neuron i's neighbors = the K/2 neurons on each side of i,
        wrapping around. For odd K, the extra neighbor goes forward.
        No self-loops, no duplicates.

        After assigning neighbors, replace each neuron's CouplingsJij
        with a K-connected instance (initial J = J_BASE = 1.0).
        """
        N = self.n_neurons
        K = self.k_neighbors

        for i, neuron in enumerate(self.neurons):
            half_back = K // 2
            half_fwd = K - half_back
            neighbor_ids = []
            for d in range(-half_back, 0):
                neighbor_ids.append(self.neurons[(i + d) % N].neuron_id)
            for d in range(1, half_fwd + 1):
                neighbor_ids.append(self.neurons[(i + d) % N].neuron_id)
            # Replace Stage 1 empty couplings with populated K-connected one
            neuron.couplings = CouplingsJij(
                n_modes=PSI_DIM, neighbors=neighbor_ids,
            )

    # ------------------------------------------------------------------
    # step — three-phase substrate cycle
    # ------------------------------------------------------------------

    def step(self, input_signal, tick: int) -> Dict[str, Dict]:
        """Execute one cluster tick.

        Phase A — independent:  every neuron runs step(input_signal, tick)
        Phase B — coupling:     spiking neurons propagate through J_ij
        Phase C — J_ij refresh: each neuron recomputes couplings from DSF

        Returns dict mapping neuron_id → step result dict.
        """
        results: Dict[str, Dict] = {}

        # Phase A: independent processing
        for neuron in self.neurons:
            results[neuron.neuron_id] = neuron.step(input_signal, tick)

        # Phase B: coupling propagation
        for neuron in self.neurons:
            if not results[neuron.neuron_id]["committed"]:
                continue
            for neighbor_idx, neighbor_id in enumerate(neuron.couplings.neighbors):
                neighbor = self._neuron_map[neighbor_id]
                J_weight = float(np.mean(neuron.couplings.J[neighbor_idx]))
                neighbor.receive_coupling_spike(
                    neuron.neuron_id,
                    J_weight,
                    neuron._last_dsf,
                    tick,
                )

        # Phase C: coupling matrix refresh from updated DSF
        for neuron in self.neurons:
            if neuron._last_dsf is not None:
                neuron.couplings.update_from_dsf(neuron._last_dsf)

        return results

    # ------------------------------------------------------------------
    # population_grandurun_state
    # ------------------------------------------------------------------

    def population_grandurun_state(self,
                                    target_chi: int,
                                    target_source: str,
                                    needs_vector,
                                    current_tick: int,
                                    ) -> List[Tuple[np.ndarray, str]]:
        """Collect 7D grandurun state vector from every neuron.

        Returns list of (state_vec_7d, neuron_id) — paste-ready for
        _grandurun_select_vector.
        """
        candidates = []
        for neuron in self.neurons:
            vec = neuron.get_grandurun_state(
                target_chi, target_source, needs_vector, current_tick,
            )
            candidates.append((vec, neuron.neuron_id))
        return candidates

    # ------------------------------------------------------------------
    # emit — greedy coherent-integration over population
    # ------------------------------------------------------------------

    def emit(self,
             target_chi: int,
             target_source: str,
             needs_vector,
             current_tick: int,
             ) -> Tuple[List[str], float, Dict[str, float]]:
        """Run population grandurun composition.

        Uses _grandurun_select_vector from production engine. Target_state
        is zero-vector (composition sum evolves greedily from zero).

        Returns:
            selected_neuron_ids: list of neuron IDs composing coherently
            alignment:           total alignment score
            dim_contributions:   dict dim_name → contribution
        """
        candidates = self.population_grandurun_state(
            target_chi, target_source, needs_vector, current_tick,
        )
        target_state = np.zeros(_SPIN_VECTOR_DIM, dtype=np.complex128)
        selected_ids, alignment, dim_contributions = _grandurun_select_vector(
            candidates, target_state,
        )
        return selected_ids, alignment, dim_contributions

    # ------------------------------------------------------------------
    # winding_signature — Sur's-ferrets differentiation diagnostic
    # ------------------------------------------------------------------

    def winding_signature(self) -> Dict[str, int]:
        """Return each neuron's current krimelack winding state.

        Used for Sur's-ferrets differentiation tests: identical neurons
        fed different input classes should develop different winding
        signatures.
        """
        return {
            n.neuron_id: n.krimelack.winding
            for n in self.neurons
        }
