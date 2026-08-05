"""
cluster.py — LoomCluster: population of coupled LoomNeurons (Stage 2 + 3).

GL-CMD-LOOM-CLUSTER-STAGE2-EVE-20260620-79
GL-CMD-LOOM-STAGE3-FOLDING-CLAUDE-20260620-84
Reference spec: GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74

Stage 2: K=16 ring-topology coupling, Phase A/B/C step, population grandurun.
Stage 3: Folding Division — process_folds, attach, fold_diagnostics.

NO production imports beyond Stage 1's existing reuses.
NO writes to production atlas. NO ECS/S3/deploy.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .neuron import (
    LoomNeuron,
    CouplingsJij,
    PSI_DIM,
    J_BASE,
    J_MAX,
    FOLD_TRIGGER_RATIO,
)
from .substrate_dna import derive_daughter_parameters, K_TOTAL
from dsf_ai_service.loom_model.structural_integration import (
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
                 seed: Optional[int] = None,
                 primary_modality: str = "physical_signal",
                 observable: str = "event_count"):
        """
        Args:
            cluster_id:        unique identifier for this cluster
            n_neurons:         number of neurons in the population
            k_neighbors:       coupling fan-out per neuron (Stage 2: 16)
            dna_blueprints:    optional list of N blueprints to distribute
            seed:              deterministic RNG seed (topology is ring-based
                               so seed is only used if future stages add
                               stochastic elements)
            primary_modality:  krimelack modality for this cluster's neurons
                               (GL-CMD-139)
        """
        self.cluster_id = cluster_id
        self.n_neurons = n_neurons
        self.k_neighbors = min(k_neighbors, n_neurons - 1)
        self.seed = seed
        self.primary_modality = primary_modality
        self.observable = observable  # GL-CMD-146: propagated to daughters too

        # --- Instantiate neurons ---
        self.neurons: List[LoomNeuron] = []
        for i in range(n_neurons):
            nid = f"{cluster_id}_n{i}"
            bp = None
            if dna_blueprints is not None and i < len(dna_blueprints):
                bp = dna_blueprints[i]
            self.neurons.append(LoomNeuron(nid, dna_blueprint=bp,
                                           primary_modality=primary_modality,
                                           observable=observable))

        # Fast lookup by neuron_id
        self._neuron_map: Dict[str, LoomNeuron] = {
            n.neuron_id: n for n in self.neurons
        }

        # --- Build ring-distance connectivity ---
        self._build_ring_topology()

        # GL-CMD-98: positional phase offset on each neuron's krimelack.
        # Neuron i gets offset = threshold × i. Each neuron starts exactly one
        # winding-transition-width apart. threshold (π/3) is the krimelack's
        # own physics — the distance between consecutive winding transitions.
        # This means neuron i starts i transitions ahead of neuron 0, giving
        # each neuron a distinct phase position in the oscillator's cycle.
        for i, neuron in enumerate(self.neurons):
            threshold = getattr(neuron.krimelack, 'threshold',
                        getattr(getattr(neuron.krimelack, '_inner', None),
                                'threshold', math.pi / 3))
            neuron._positional_phase_offset = threshold * i
            neuron.ring_pos = i
            neuron.ring_N = self.n_neurons

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
            ring_dists = []
            for d in range(-half_back, 0):
                neighbor_ids.append(self.neurons[(i + d) % N].neuron_id)
                ring_dists.append(abs(d))
            for d in range(1, half_fwd + 1):
                neighbor_ids.append(self.neurons[(i + d) % N].neuron_id)
                ring_dists.append(abs(d))
            # Replace Stage 1 empty couplings with populated K-connected one
            # GL-CMD-98: ring_distances enable topology-driven J_ij differentiation
            neuron.couplings = CouplingsJij(
                n_modes=PSI_DIM, neighbors=neighbor_ids,
                ring_distances=ring_dists,
            )

    # ------------------------------------------------------------------
    # step — three-phase substrate cycle
    # ------------------------------------------------------------------

    def step(self, input_signal, tick: int, input_chi: Optional[int] = None) -> Dict[str, Dict]:
        """Execute one cluster tick.

        Phase A — every neuron receives the physical input.
        Phase B — spiking neurons propagate through J_ij.
        Phase C — every stepped neuron refreshes J_ij from its full DSF.

        ``input_chi`` is accepted only so an older engine shell cannot break
        during cutover. It has no routing, identity, or familiarity authority.

        Returns one physical step result for every neuron.
        """
        results: Dict[str, Dict] = {}

        # Phase A: independent physical processing across the population.
        stepping_neurons = self.neurons
        for neuron in stepping_neurons:
            results[neuron.neuron_id] = neuron.step(input_signal, tick)

        # Phase B: coupling propagation — unchanged, runs across all neurons.
        # GL-CMD-98: J_weight comes from the RECEIVING neuron's coupling matrix,
        # not the spiking neuron's. This means each neuron receives a different
        # total coupling signal based on its own ring-distance-scaled J_ij,
        # enabling topology-driven differentiation.
        # (.get() here, not direct indexing, since `results` now only has
        # entries for neurons that stepped this tick — a non-stepping neuron
        # correctly reads as "did not spike" rather than a KeyError.)
        spiking_neurons = [
            n for n in self.neurons if results.get(n.neuron_id, {}).get("committed")
        ]
        for neuron in self.neurons:
            for src_idx, src_id in enumerate(neuron.couplings.neighbors):
                src = self._neuron_map.get(src_id)
                if src is None or not results.get(src_id, {}).get("committed"):
                    continue
                J_weight = float(np.mean(neuron.couplings.J[src_idx]))
                neuron.receive_coupling_spike(
                    src_id,
                    J_weight,
                    src._last_dsf,
                    tick,
                )

        # Phase C: coupling matrix refresh from updated DSF — stepping neurons only
        for neuron in stepping_neurons:
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

    # ------------------------------------------------------------------
    # Stage 3: Folding Division
    # ------------------------------------------------------------------

    def next_id(self) -> str:
        """Generate the next unique neuron ID for daughter neurons."""
        idx = len(self.neurons)
        return f"{self.cluster_id}_n{idx}"

    def attach(self, daughter: LoomNeuron, inherit_from: LoomNeuron) -> None:
        """Wire a daughter neuron into the cluster.

        - Add daughter to neurons list + lookup map
        - Wire inherited_neighbors into daughter's couplings
        - Clear the parent's overflow modes so n_eff recovers
        """
        self.neurons.append(daughter)
        self._neuron_map[daughter.neuron_id] = daughter

        # Wire couplings: daughter gets K nearest neighbors from ring position
        # Half inherited from parent, half from ring position
        K = self.k_neighbors
        parent_idx = self.neurons.index(inherit_from)
        daughter_idx = len(self.neurons) - 1
        N = len(self.neurons)

        inherited = inherit_from.nearest_neighbors(K // 2)
        ring_neighbors = []
        half = (K - len(inherited)) // 2
        for d in range(-half, 0):
            nid = self.neurons[(daughter_idx + d) % N].neuron_id
            if nid != daughter.neuron_id and nid not in inherited:
                ring_neighbors.append(nid)
        for d in range(1, half + 2):
            if len(ring_neighbors) + len(inherited) >= K:
                break
            nid = self.neurons[(daughter_idx + d) % N].neuron_id
            if nid != daughter.neuron_id and nid not in inherited:
                ring_neighbors.append(nid)

        all_neighbors = inherited + ring_neighbors
        all_neighbors = all_neighbors[:K]

        daughter.couplings = CouplingsJij(n_modes=PSI_DIM, neighbors=all_neighbors)

        # Clear parent's overflow modes so n_eff recovers
        inherit_from.clear_overflow_modes()

    def process_folds(self, tick: int) -> List[str]:
        """Check all neurons for fold triggers and spawn daughters.

        Contact inhibition (GL-CMD-105): after fold_check passes, the
        overflow signal is scaled by inhibition_factor = (1 - n/K_TOTAL)².
        Spawn only proceeds if the effective overflow exceeds the fold
        threshold. At full neighbor saturation, inhibition_factor → 0
        and fold rate → 0.

        Returns list of newly spawned daughter neuron_ids.
        """
        new_ids = []
        # Iterate over a snapshot of current neurons (don't process daughters
        # spawned this tick)
        current_neurons = list(self.neurons)
        for neuron in current_neurons:
            if neuron.fold_check(tick):
                # Contact inhibition gate
                n_neighbors = len(neuron.couplings.neighbors)
                saturation_ratio = n_neighbors / K_TOTAL
                inhibition_factor = (1.0 - saturation_ratio) ** 2
                if inhibition_factor <= 0.0:
                    continue  # fully saturated — fold suppressed

                # Effective overflow magnitude check:
                # n_eff is already below threshold (fold_check passed).
                # Scale the overflow margin by inhibition_factor.
                n_eff = neuron.l6_tcl.n_eff(neuron._last_dsf)
                threshold = neuron.l6_tcl.n_start * FOLD_TRIGGER_RATIO
                overflow_raw = threshold - n_eff  # positive when fold_check passed
                overflow_eff = overflow_raw * inhibition_factor
                if overflow_eff <= 0.0:
                    continue  # inhibited below threshold

                overflow = neuron.compute_overflow_signal()
                params = derive_daughter_parameters(overflow, neuron)
                daughter_id = self.next_id()
                daughter = LoomNeuron(
                    neuron_id=daughter_id,
                    birth_params=params,
                    primary_modality=self.primary_modality,
                    observable=self.observable,
                )
                self.attach(daughter, inherit_from=neuron)
                neuron._fold_ticks.append(tick)
                new_ids.append(daughter_id)
        return new_ids

    def fold_diagnostics(self, window_ticks: int) -> Dict[str, Any]:
        """Instrumentation only. NOT regulation.

        Returns:
            n_folds_in_window:        total folds across cluster in window
            per_neuron_fold_counts:   dict neuron_id → fold count
            max_per_neuron_fold_rate: max folds/1000 ticks for any neuron
        """
        per_neuron = {}
        for neuron in self.neurons:
            per_neuron[neuron.neuron_id] = neuron._fold_count

        # Fold rate: folds within the window, scaled to per-1000-ticks
        max_rate = 0.0
        for neuron in self.neurons:
            recent = [t for t in neuron._fold_ticks
                      if t >= (neuron._fold_ticks[-1] - window_ticks)
                      ] if neuron._fold_ticks else []
            if window_ticks > 0:
                rate = len(recent) / window_ticks * 1000
            else:
                rate = 0.0
            max_rate = max(max_rate, rate)

        return {
            "n_folds_in_window": sum(per_neuron.values()),
            "per_neuron_fold_counts": per_neuron,
            "max_per_neuron_fold_rate": max_rate,
        }
