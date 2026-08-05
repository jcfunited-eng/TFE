#!/usr/bin/env python3
"""
WaveAtlas offline validator
GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 Phase 0 (v2 corrections)

Pure Python, no live substrate. Run with: python tools/wave_atlas_validator.py
"""

import os
import sys
import numpy as np
import time
from collections import defaultdict
from typing import Optional, Dict

# ─── Shared modules (wave_constants + wave_spillover live in tools/) ──────────
_tools_dir = os.path.dirname(os.path.abspath(__file__))
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

from wave_constants import (
    SATURATION_THRESHOLD, CHI_BAND, SUBDIVISION_TRIGGER, N_CELLS as ARRAY_SIZE, PHASE_DIMS
)
from wave_spillover import Cell, spill_write  # noqa: F401 (Cell used in type hints)

# ─── Pass thresholds (per spec + Eve correction) ─────────────────────────────
# M1: corrected per Eve — chi now correlated with phase, threshold loosened to 100
COHESION_S1_PASS = 100      # stage 1: median within-cluster centroid dist < 100
COHESION_S2_PASS = 200      # stage 2 (saturating): centroid dist stays < 200
SPREAD_PASS_THRESHOLD_FACTOR = 5     # median > CHI_BAND × 5
PILE_PASS_THRESHOLD = 5.0            # max_occ / mean_occ < 5.0
SUBDIV_WRITE_LIMIT = 500             # must fire before write 500
WALL_MEDIAN_PASS_US = 1000           # < 1ms
WALL_P99_PASS_US = 5000              # < 5ms


# ─── Validator-local WaveAtlas (delegates to shared wave_spillover) ───────────

class WaveAtlas:
    """Thin harness used by the validator. Spillover logic lives in wave_spillover."""

    def __init__(
        self,
        sat_thresh: float = SATURATION_THRESHOLD,
        chi_band: int = CHI_BAND,
        subdiv_trigger: int = SUBDIVISION_TRIGGER,
    ):
        self.sat_thresh = sat_thresh
        self.chi_band = chi_band
        self.subdiv_trigger = subdiv_trigger
        self.cells: Dict[int, Cell] = {}
        self._subdivision_count: int = 0
        self.first_subdivision_at_write: Optional[int] = None
        self._write_counter: int = 0

    def write(
        self,
        chi_target: int,
        phase_vec_in: np.ndarray,
        binding: Optional[dict] = None,
    ) -> tuple:
        """Delegate to shared spill_write. Returns (final_chi, hops)."""
        self._write_counter += 1
        final_chi, hops = spill_write(
            self.cells, chi_target, phase_vec_in, binding,
            sat_thresh=self.sat_thresh,
            chi_band=self.chi_band,
            subdiv_trigger=self.subdiv_trigger,
            _on_subdivide=self._on_subdivide,
        )
        return final_chi, hops

    def _on_subdivide(self, chi_center: int) -> None:
        self._subdivision_count += 1
        if self.first_subdivision_at_write is None:
            self.first_subdivision_at_write = self._write_counter

    def occupancy(self) -> Dict[int, int]:
        return {idx: len(c.bindings) for idx, c in self.cells.items()}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def chi_dist(a: int, b: int) -> int:
    """Circular distance in [0, ARRAY_SIZE)."""
    d = abs(int(a) - int(b))
    return min(d, ARRAY_SIZE - d)


def make_orthogonal_bases(n: int, dims: int, rng: np.random.Generator) -> np.ndarray:
    """Generate n roughly-orthogonal unit vectors in dims-dim complex space."""
    raw = rng.standard_normal((n, dims)) + 1j * rng.standard_normal((n, dims))
    out = []
    for v in raw:
        for u in out:
            v = v - (np.vdot(u, v) / (np.dot(u.conj(), u) + 1e-12)) * u
        norm = np.linalg.norm(v)
        out.append(v / norm if norm > 1e-12 else v)
    return np.array(out)


# ─── Core validation run ──────────────────────────────────────────────────────

def run_validation(
    sat_thresh: float = SATURATION_THRESHOLD,
    chi_band: int = CHI_BAND,
    subdiv_trigger: int = SUBDIVISION_TRIGGER,
    rng_seed: int = 42,
) -> dict:
    rng = np.random.default_rng(rng_seed)
    N_CLUSTERS = 10
    N_PER_CLUSTER = 100
    CHI_SPREAD_STD = 30  # std of per-experience chi offset around cluster center

    # ── Cluster bases (phase) and chi centers ─────────────────────────────────
    # Eve correction 1: chi_target is correlated with cluster, not globally random.
    # Each cluster gets one center_chi; experiences land within ±~90 of it.
    bases = make_orthogonal_bases(N_CLUSTERS, PHASE_DIMS, rng)
    cluster_center_chis = [int(rng.integers(0, ARRAY_SIZE)) for _ in range(N_CLUSTERS)]

    # ── Stage 1: generate 1000 experiences (shuffled) ─────────────────────────
    experiences = []
    for cluster_id in range(N_CLUSTERS):
        base = bases[cluster_id]
        center_chi = cluster_center_chis[cluster_id]
        for _ in range(N_PER_CLUSTER):
            noise = (
                rng.standard_normal(PHASE_DIMS) * 0.1
                + 1j * rng.standard_normal(PHASE_DIMS) * 0.1
            )
            pv = base + noise
            norm = np.linalg.norm(pv)
            pv = pv / norm if norm > 1e-12 else pv
            offset = int(round(rng.standard_normal() * CHI_SPREAD_STD))
            chi_target = (center_chi + offset) % ARRAY_SIZE
            experiences.append((cluster_id, pv, chi_target))

    perm = rng.permutation(len(experiences))
    experiences = [experiences[i] for i in perm]

    # ── Write all 1000 stage-1 experiences ───────────────────────────────────
    atlas = WaveAtlas(sat_thresh=sat_thresh, chi_band=chi_band, subdiv_trigger=subdiv_trigger)
    results = []  # (cluster_id, orig_chi, final_chi, hops, wall_us)

    for cluster_id, pv, chi_target in experiences:
        t0 = time.perf_counter()
        final_chi, hops = atlas.write(chi_target, pv, binding={"cluster": cluster_id})
        wall_us = (time.perf_counter() - t0) * 1e6
        results.append((cluster_id, chi_target, final_chi, hops, wall_us))

    # ── Metric 1a: Within-cluster cohesion (stage 1) ──────────────────────────
    # Same-cluster writes should stay near their cluster_center_chi.
    # Threshold: median < 100 (Eve correction — chi now correlated with phase).
    cluster_chis_s1 = defaultdict(list)
    for cid, _, fchi, _, _ in results:
        cluster_chis_s1[cid].append(fchi)

    per_cluster_median_s1 = []
    per_cluster_centroid = {}
    for cid in range(N_CLUSTERS):
        chis = cluster_chis_s1[cid]
        centroid = int(np.round(np.mean(chis)))
        per_cluster_centroid[cid] = centroid
        dists = [chi_dist(c, centroid) for c in chis]
        per_cluster_median_s1.append(float(np.median(dists)))

    cohesion_s1 = float(np.median(per_cluster_median_s1))
    cohesion_s1_pass = cohesion_s1 < COHESION_S1_PASS

    # ── Metric 1b: Within-cluster cohesion under saturating load (stage 2) ────
    # Inject 500 more writes (50 per cluster) all at each cluster's center chi.
    # Verify centroid stays tight < 200 even under saturation pressure.
    s2_writes_per_cluster = 50
    for cluster_id in range(N_CLUSTERS):
        base = bases[cluster_id]
        center_chi = cluster_center_chis[cluster_id]
        for _ in range(s2_writes_per_cluster):
            noise = (
                rng.standard_normal(PHASE_DIMS) * 0.1
                + 1j * rng.standard_normal(PHASE_DIMS) * 0.1
            )
            pv = base + noise
            norm = np.linalg.norm(pv)
            pv = pv / norm if norm > 1e-12 else pv
            t0 = time.perf_counter()
            final_chi, hops = atlas.write(center_chi, pv, binding={"cluster": cluster_id})
            wall_us = (time.perf_counter() - t0) * 1e6
            results.append((cluster_id, center_chi, final_chi, hops, wall_us))

    # Recompute centroids over all writes (stage 1 + stage 2)
    cluster_chis_s2 = defaultdict(list)
    for cid, _, fchi, _, _ in results:
        cluster_chis_s2[cid].append(fchi)

    per_cluster_median_s2 = []
    for cid in range(N_CLUSTERS):
        chis = cluster_chis_s2[cid]
        centroid = per_cluster_centroid[cid]  # anchor to stage-1 centroid
        dists = [chi_dist(c, centroid) for c in chis]
        per_cluster_median_s2.append(float(np.median(dists)))

    cohesion_s2 = float(np.median(per_cluster_median_s2))
    cohesion_s2_pass = cohesion_s2 < COHESION_S2_PASS

    cohesion_pass = cohesion_s1_pass and cohesion_s2_pass

    # ── Metric 2: Cross-cluster spread ───────────────────────────────────────
    centroids = [per_cluster_centroid[cid] for cid in range(N_CLUSTERS)]
    pairwise = [
        chi_dist(centroids[i], centroids[j])
        for i in range(N_CLUSTERS)
        for j in range(i + 1, N_CLUSTERS)
    ]
    spread_median = float(np.median(pairwise))
    spread_threshold = chi_band * SPREAD_PASS_THRESHOLD_FACTOR
    spread_pass = spread_median > spread_threshold

    # ── Metric 3: No degenerate piling ───────────────────────────────────────
    occ = atlas.occupancy()
    if occ:
        occ_vals = list(occ.values())
        max_occ = max(occ_vals)
        mean_occ = float(np.mean(occ_vals))
        pile_ratio = max_occ / mean_occ if mean_occ > 0 else float("inf")
    else:
        max_occ, mean_occ, pile_ratio = 0, 0.0, float("inf")
    pile_pass = pile_ratio < PILE_PASS_THRESHOLD

    # ── Metric 4: Subdivision under sustained pressure ────────────────────────
    # Eve correction 2: 500 writes all targeting chi=131072, IDENTICAL phase.
    # PASS: subdivision fires before write 500.
    # On failure: report cell occupancy distribution + reason subdivision not reached.
    atlas2 = WaveAtlas(sat_thresh=sat_thresh, chi_band=chi_band, subdiv_trigger=subdiv_trigger)
    SUBDIV_CHI = 131072
    flood_pv = bases[0].copy()  # identical phase, no noise
    subdiv_write_count = None
    subdiv_max_hops = 0
    hops_per_write = []

    for i in range(500):
        _, hops = atlas2.write(SUBDIV_CHI, flood_pv, binding={"write_idx": i})
        hops_per_write.append(hops)
        subdiv_max_hops = max(subdiv_max_hops, hops)
        if atlas2._subdivision_count > 0 and subdiv_write_count is None:
            subdiv_write_count = i + 1  # 1-indexed

    subdiv_pass = subdiv_write_count is not None

    # Diagnostics around SUBDIV_CHI for failure analysis
    radius = chi_band * (subdiv_trigger + 2)  # inspect full expected chain region
    subdiv_region_occ = {}
    for d in range(-radius, radius + 1):
        idx = (SUBDIV_CHI + d) % ARRAY_SIZE
        c = atlas2.cells.get(idx)
        if c is not None:
            subdiv_region_occ[d] = (len(c.bindings), c.aggregate_strength, c.saturated)

    # What stopped subdivision (for failure report)?
    subdiv_blocker = None
    if subdiv_write_count is None:
        n_sat_in_region = sum(1 for v in subdiv_region_occ.values() if v[2])
        if subdiv_max_hops < subdiv_trigger:
            subdiv_blocker = (
                f"chain depth never reached {subdiv_trigger}: max_hops={subdiv_max_hops}. "
                f"{n_sat_in_region} saturated cells in ±{radius} of target."
            )
        else:
            subdiv_blocker = (
                f"chain reached depth {subdiv_max_hops} but _subdivide_hot_region "
                f"stub returned without incrementing _subdivision_count."
            )

    # ── Metric 5: Per-write wall time ─────────────────────────────────────────
    wall_times = [r[4] for r in results]
    wall_median_us = float(np.median(wall_times))
    wall_p99_us = float(np.percentile(wall_times, 99))
    wall_pass = wall_median_us < WALL_MEDIAN_PASS_US and wall_p99_us < WALL_P99_PASS_US

    # ── Summary diagnostics ───────────────────────────────────────────────────
    total_cells_used = len(occ)
    saturated_cells = sum(1 for c in atlas.cells.values() if c.saturated)
    spillover_count = sum(1 for r in results if r[3] > 0)
    max_hops_main = max(r[3] for r in results) if results else 0

    return {
        # Constants used
        "sat_thresh": sat_thresh,
        "chi_band": chi_band,
        "subdiv_trigger": subdiv_trigger,
        # Metric 1
        "cohesion_s1": cohesion_s1,
        "cohesion_s2": cohesion_s2,
        "cohesion_s1_pass": cohesion_s1_pass,
        "cohesion_s2_pass": cohesion_s2_pass,
        "cohesion_pass": cohesion_pass,
        # Metric 2
        "spread_median": spread_median,
        "spread_threshold": spread_threshold,
        "spread_pass": spread_pass,
        # Metric 3
        "pile_ratio": pile_ratio,
        "max_occ": max_occ,
        "mean_occ": mean_occ,
        "pile_pass": pile_pass,
        # Metric 4
        "subdiv_write_count": subdiv_write_count,
        "subdiv_pass": subdiv_pass,
        "subdiv_max_hops": subdiv_max_hops,
        "subdiv_blocker": subdiv_blocker,
        "subdiv_region_occ": subdiv_region_occ,
        "subdiv_count_atlas2": atlas2._subdivision_count,
        # Metric 5
        "wall_median_us": wall_median_us,
        "wall_p99_us": wall_p99_us,
        "wall_pass": wall_pass,
        # Diagnostics
        "total_cells_used": total_cells_used,
        "saturated_cells": saturated_cells,
        "spillover_count": spillover_count,
        "max_hops_main": max_hops_main,
    }


# ─── Main: single run, fixed constants ───────────────────────────────────────

def all_pass(r: dict) -> bool:
    return (
        r["cohesion_pass"] and r["spread_pass"] and r["pile_pass"]
        and r["subdiv_pass"] and r["wall_pass"]
    )


if __name__ == "__main__":
    print("=" * 70)
    print("WaveAtlas Phase 0 Validator (v2)")
    print("GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1")
    print(f"Constants: SAT={SATURATION_THRESHOLD} CHI_BAND={CHI_BAND} SUBDIV_TRIGGER={SUBDIVISION_TRIGGER}")
    print("=" * 70)

    r = run_validation()

    print(f"\nM1 cohesion stage1  = {r['cohesion_s1']:.1f}   (threshold < {COHESION_S1_PASS})  {'PASS' if r['cohesion_s1_pass'] else 'FAIL'}")
    print(f"M1 cohesion stage2  = {r['cohesion_s2']:.1f}   (threshold < {COHESION_S2_PASS})  {'PASS' if r['cohesion_s2_pass'] else 'FAIL'}")
    print(f"M2 spread_median    = {r['spread_median']:.1f}   (threshold > {r['spread_threshold']})  {'PASS' if r['spread_pass'] else 'FAIL'}")
    print(f"M3 pile_ratio       = {r['pile_ratio']:.3f}   (max={r['max_occ']} mean={r['mean_occ']:.3f})  (threshold < {PILE_PASS_THRESHOLD})  {'PASS' if r['pile_pass'] else 'FAIL'}")
    print(f"M4 subdiv_write     = {r['subdiv_write_count']}   (threshold < {SUBDIV_WRITE_LIMIT} writes)  {'PASS' if r['subdiv_pass'] else 'FAIL'}")
    if not r['subdiv_pass']:
        print(f"  M4 blocker: {r['subdiv_blocker']}")
        print(f"  M4 region occupancy (offset→(writes,strength,saturated)):")
        for offset, info in sorted(r['subdiv_region_occ'].items()):
            print(f"    d={offset:+4d}: writes={info[0]} strength={info[1]:.1f} sat={info[2]}")
    else:
        print(f"  M4 subdivision fired on write {r['subdiv_write_count']}, max_hops_in_M4_test={r['subdiv_max_hops']}, total_subdivisions={r['subdiv_count_atlas2']}")
    print(f"M5 wall             = {r['wall_median_us']:.2f}µs median / {r['wall_p99_us']:.2f}µs p99  (thresholds <{WALL_MEDIAN_PASS_US}/<{WALL_P99_PASS_US})  {'PASS' if r['wall_pass'] else 'FAIL'}")
    print(f"\nDiag (main atlas): cells={r['total_cells_used']} saturated={r['saturated_cells']} spillovers={r['spillover_count']} max_hops={r['max_hops_main']}")

    print("\n" + "=" * 70)
    overall = "ALL PASS" if all_pass(r) else "PARTIAL PASS / FAIL"
    print(f"Overall: {overall}")
    print("=" * 70)
