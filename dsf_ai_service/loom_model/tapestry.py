"""Physical LoomTapestry population.

The tapestry preserves its mosaics and broadcasts numeric physical signals.
The former word-emission decoder and corpus-label exposure surface are absent;
learned meaning belongs to authenticated causal THING mosaics.
"""

from typing import Any, Dict, List, Optional, Tuple

from .mosaic import LoomMosaic


class LoomTapestry:
    """Ordered collection of physical LoomMosaic populations."""

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

    # ------------------------------------------------------------------
    # persistence — GL-CMD-BRAIN-FULL-DEPLOY-TODAY-175 P1: same convention
    # as Embryo.save_full_state/load_full_state (embryo.py, GL-CMD-169) --
    # closed structural graph, so every neuron's real spike/winding/
    # familiarity history round-trips while runtime handles are rebuilt.
    # ------------------------------------------------------------------

    def save_full_state(self, path, *, persistence_admission=None):
        """Persist the exact tapestry through the bounded graph boundary."""
        from dsf_ai_service.loom_model.structural_graph_state import (
            save_structural_graph,
            structural_graph_limits_from_environment,
        )
        return save_structural_graph(
            self,
            path,
            limits=structural_graph_limits_from_environment(),
            persistence_admission=persistence_admission,
        )

    @staticmethod
    def load_full_state(path):
        from dsf_ai_service.loom_model.structural_graph_state import (
            load_structural_graph,
            structural_graph_limits_from_environment,
        )
        return load_structural_graph(
            path,
            expected_root_type=LoomTapestry,
            limits=structural_graph_limits_from_environment(),
        )

    @staticmethod
    def load_legacy_pickle_state(path):
        """Read one authenticated pre-graph generation for migration only."""
        import gzip
        import pickle
        with gzip.open(path, "rb") as source:
            restored = pickle.load(source)
        if not isinstance(restored, LoomTapestry):
            raise TypeError("legacy tapestry state restored an unexpected type")
        return restored
