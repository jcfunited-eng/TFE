# Provenance: copied VERBATIM from codex/persistent-etl-update-20260326
# at commit 31b9e8c (GL-CMD-112 Phase C, per GL-SPC-SENSORY-CATALOG-
# EVE-20260621-111 §6.5), which never merged to guala-live. Brought over
# 2026-07-04 alongside sensory_catalog.py, same provenance note applies.
"""
catalog_atlas_reader.py — CatalogAtlasReader for SensoryTransducer.

GL-CMD-112 Phase C, per GL-SPC-SENSORY-CATALOG-EVE-20260621-111 §6.5.

Implements the AtlasReader protocol by reading from the SensoryCatalog.
Plugs into F1 SensoryTransducer so catalog-populated words get their
distributions sampled, while unknown words fall through to _generate_initial.
"""

from typing import Dict, List, Optional, Tuple

from .sensory_catalog import SensoryCatalog


class CatalogAtlasReader:
    """AtlasReader backed by the sensory catalog SQLite store.

    Implements:
      - has_bindings(label, modality) → bool
      - get_binding_params(label, modality) → List[Dict]  (legacy path)
      - get_distribution(label, modality) → Optional[(mean, std)]  (direct path)
    """

    def __init__(self, catalog: SensoryCatalog):
        self.catalog = catalog

    def has_bindings(self, label: str, modality: str) -> bool:
        """True if catalog has applicable distribution for this (label, modality)."""
        return self.catalog.is_applicable(label, modality)

    def get_binding_params(self, label: str, modality: str) -> List[Dict[str, float]]:
        """Legacy path: generate N synthetic prior samples from stored distribution.

        Used if SensoryTransducer doesn't check get_distribution directly.
        """
        dist = self.catalog.get_distribution(label, modality)
        if dist is None:
            return []

        import numpy as np
        mean, std = dist
        # Generate 20 synthetic samples (enough for _compute_distribution to recover)
        rng = np.random.default_rng(hash((label, modality)) & 0xFFFFFFFF)
        samples = []
        for _ in range(20):
            sample = {}
            for ch, m in mean.items():
                s = std.get(ch, 0.1)
                val = float(rng.normal(m, s))
                sample[ch] = max(0.0, min(1.0, val))
            samples.append(sample)
        return samples

    def get_distribution(self, label: str, modality: str) -> Optional[Tuple[Dict[str, float], Dict[str, float]]]:
        """Direct path: return stored (mean, std) without synthetic sample generation."""
        return self.catalog.get_distribution(label, modality)
