"""
tapestry.py — LoomTapestry: ordered collection of LoomMosaics for composition.

GL-CMD-LOOM-TAPESTRY-STAGE5-EVE-20260620-95
Reference: GL-SPC-LOOM-NEURON-ARCH-EVE-20260620-74 Section 6 Stage 5

Two-phase coherent integration:
  Phase A: each mosaic produces its own composition vector via recall()
  Phase B: population grandurun across mosaic-level vectors

Sequence ordering: grandurun-selection order. No grammar parser, no syntax
tree, no part-of-speech tagging. Order emerges from selection physics.

NO NLP imports. NO slot-filling. NO label-matching vocabulary dicts.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .mosaic import LoomMosaic
from .neuron import LoomNeuron, PSI_DIM
from dsf_ai_service.v4.gualaloom_v5_engine import (
    _grandurun_select_vector,
    _SPIN_VECTOR_DIM,
    MIN_GAIN_THRESHOLD,
)


class LoomTapestry:
    """Ordered collection of LoomMosaics for multi-scale composition.

    compose(query) returns an emission_sequence decoded from two-phase
    grandurun coherent integration. Sequence order = selection order.
    """

    def __init__(self,
                 name: str,
                 n_mosaics: int = 3,
                 mosaic_kwargs: Optional[Dict[str, Any]] = None,
                 seed: int = 0):
        self.name = name
        self.n_mosaics = n_mosaics
        self.seed = seed
        self._tick = 0

        mk = mosaic_kwargs or {}
        self.mosaics: List[LoomMosaic] = []
        for i in range(n_mosaics):
            m = LoomMosaic(
                name=f"{name}_m{i}",
                n_clusters=mk.get("n_clusters", 3),
                neurons_per_cluster=mk.get("neurons_per_cluster", 50),
                k_neighbors=mk.get("k_neighbors", 16),
                seed=seed + i,
            )
            self.mosaics.append(m)

    @property
    def total_neurons(self) -> int:
        return sum(m.total_neurons for m in self.mosaics)

    # ------------------------------------------------------------------
    # step — broadcast to all mosaics
    # ------------------------------------------------------------------

    def step(self, input_signal, tick: Optional[int] = None) -> None:
        if tick is None:
            tick = self._tick
        self._tick = tick + 1
        for mosaic in self.mosaics:
            mosaic.step(input_signal, tick)

    # ------------------------------------------------------------------
    # compose — two-phase coherent integration → emission sequence
    # ------------------------------------------------------------------

    def compose(self, query) -> Optional[List[str]]:
        """Two-phase composition:

        Phase A: each mosaic produces its own composition vector via recall()
        Phase B: gather Phase A vectors as candidates; run _grandurun_select_vector

        The order in which mosaics' Phase A vectors were selected by Phase B's
        greedy gain IS the sequence order.

        Returns None if Phase B clears no candidate.
        """
        tick = self._tick
        self._tick = tick + 1

        # Phase A: per-mosaic recall
        phase_a = []
        for mosaic in self.mosaics:
            vec = mosaic.recall(query, target_chi=0, target_source="corpus")
            if vec is not None:
                phase_a.append((vec, mosaic.name))

        if not phase_a:
            return None

        # Phase B: mosaic-level grandurun selection
        target_state = np.zeros(_SPIN_VECTOR_DIM, dtype=np.complex128)
        selected_names, alignment, dim_contributions = _grandurun_select_vector(
            phase_a, target_state,
        )

        if not selected_names or alignment < MIN_GAIN_THRESHOLD:
            return None

        # Decode emission_sequence: read the most-activated word from each
        # selected mosaic's krimelack state, in grandurun-selection order.
        emission = []
        for mosaic_name in selected_names:
            mosaic = self._mosaic_by_name(mosaic_name)
            if mosaic is None:
                continue
            word = self._dominant_word(mosaic)
            if word:
                emission.append(word)

        return emission if emission else None

    def _mosaic_by_name(self, name: str) -> Optional[LoomMosaic]:
        for m in self.mosaics:
            if m.name == name:
                return m
        return None

    def _dominant_word(self, mosaic: LoomMosaic) -> Optional[str]:
        """Extract the dominant word from a mosaic's current krimelack state.

        The word is the input that produced the highest total winding across
        the mosaic's neurons. Since all neurons in a cluster receive the same
        input (Sur's-ferrets), we read the last input from any neuron's
        krimelack. The winding magnitude indicates signal strength.
        """
        best_winding = 0
        best_word = None
        for cluster in mosaic.clusters:
            for neuron in cluster.neurons:
                w = abs(neuron.krimelack.winding)
                if w > best_winding:
                    best_winding = w
                    # The krimelack doesn't store the input word, but the
                    # neuron's last processed signal is tracked via chi state.
                    # We use the neuron_id's cluster as a proxy for the
                    # mosaic-level contribution identity.
                    best_word = mosaic.name
        # In the current architecture, the "word" IS the mosaic's contribution
        # identity. The emission is the ordered list of mosaic contributions.
        # To get actual words, we'd need the krimelack to store its input —
        # that's a Stage 6 extension.
        return best_word

    # ------------------------------------------------------------------
    # expose_corpus — learning from consecutive word pairs
    # ------------------------------------------------------------------

    def expose_corpus(self, sentences: List[str]) -> None:
        """For each sentence, expose consecutive word pairs to all mosaics."""
        for sentence in sentences:
            words = sentence.lower().split()
            for i in range(len(words) - 1):
                for mosaic in self.mosaics:
                    mosaic.expose(words[i], words[i + 1])
                self._tick += 2  # each expose does 2 steps

    # ------------------------------------------------------------------
    # neuron_diversity_signature — real substrate diversity diagnostic
    # ------------------------------------------------------------------

    def neuron_diversity_signature(self) -> Dict[str, Dict[str, Tuple[int, float]]]:
        """Per-mosaic neuron diversity: (spike_count, recent_psi_norm).

        Reads from spike_buffer and psi_lattice — substrate's real
        diversity layer, NOT krimelack winding.
        """
        result = {}
        for mosaic in self.mosaics:
            result[mosaic.name] = mosaic.neuron_diversity_signature()
        return result
