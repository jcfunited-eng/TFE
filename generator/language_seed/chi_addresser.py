"""chi_addresser.py -- deterministic chi address assignment.

Each word gets exactly one chi address in 0..262143 (config.N_CELLS,
matching the wave atlas). Words sharing a semantic cluster (WordNet
lexicographer file, e.g. "noun.animal") land in the same contiguous chi
band, so chi-neighborhood proximity mirrors semantic proximity -- the
substrate's own ChiAtlas/WaveAtlas bind commits that land within a small
chi band, so this clustering is what makes that binding mechanism pick up
real semantic structure instead of noise.

Uses hashlib (NOT Python's built-in hash()) for the intra-band placement
hash -- built-in hash() is salted per-process, which would make chi
assignment non-reproducible across runs (the exact failure mode noted in
prior session work: [[gualaloom-capacity-probe-reproducibility]]).
"""

from __future__ import annotations

import hashlib
from typing import Dict, Iterable, Set, Tuple

from generator.language_seed import config


class ChiSpaceExhausted(Exception):
    pass


def stable_hash(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big")


def compute_cluster_bands(cluster_counts: Dict[str, int],
                           n_cells: int = config.N_CELLS,
                           headroom: float = 1.8) -> Dict[str, Tuple[int, int]]:
    """Allocate a contiguous [start, start+size) chi band per cluster,
    proportional to that cluster's actual word count with a headroom
    multiplier (so intra-band linear probing rarely has to spill into a
    full global probe). Deterministic: clusters sorted by name so the same
    input always produces the same band layout."""
    cluster_names = sorted(cluster_counts.keys())
    total_weighted = sum(max(cluster_counts[c], 1) * headroom for c in cluster_names)
    if total_weighted <= 0:
        return {}

    bands: Dict[str, Tuple[int, int]] = {}
    cursor = 0
    remaining_cells = n_cells
    for i, name in enumerate(cluster_names):
        weight = max(cluster_counts[name], 1) * headroom
        if i == len(cluster_names) - 1:
            size = n_cells - cursor
        else:
            size = max(1, int(n_cells * (weight / total_weighted)))
            size = min(size, remaining_cells - (len(cluster_names) - i - 1))
        size = max(size, 1)
        bands[name] = (cursor, size)
        cursor += size
        remaining_cells -= size
    return bands


class ChiAddresser:
    def __init__(self, cluster_counts: Dict[str, int]):
        self.bands = compute_cluster_bands(cluster_counts)
        self.used: Set[int] = set()
        self.word_to_chi: Dict[str, int] = {}

    def assign(self, word: str, cluster_key: str) -> int:
        if word in self.word_to_chi:
            return self.word_to_chi[word]

        band = self.bands.get(cluster_key)
        if band is None:
            band = self.bands.get("_unclustered")
        if band is None:
            raise ChiSpaceExhausted(f"no band for cluster {cluster_key!r} and no _unclustered fallback")
        start, size = band

        h = stable_hash(word) % size
        for probe in range(size):
            candidate = start + (h + probe) % size
            if candidate not in self.used:
                self.used.add(candidate)
                self.word_to_chi[word] = candidate
                return candidate

        # band exhausted -- fall back to a global probe across the whole space
        h2 = stable_hash(word + "::overflow")
        for probe in range(config.N_CELLS):
            candidate = (h2 + probe) % config.N_CELLS
            if candidate not in self.used:
                self.used.add(candidate)
                self.word_to_chi[word] = candidate
                return candidate

        raise ChiSpaceExhausted(f"chi address space fully saturated assigning {word!r}")
