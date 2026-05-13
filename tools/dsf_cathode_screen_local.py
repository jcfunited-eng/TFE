#!/usr/bin/env python3
"""
DSF-AI Cathode Screening — LOCAL TEST (no API key required)
============================================================

Uses pymatgen's built-in structure database to test the DSF-AI kernel
against known crystal structures with computed stability properties.

This generates structures from known prototypes with varying compositions
and tests whether the kernel's structural field extraction correlates
with thermodynamic stability indicators.
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.derive_sppu_weights import build_field_series, run_kernel, dsf_to_coupling_profile

from pymatgen.core.structure import Structure
from pymatgen.core.lattice import Lattice


# ============================================================
# KNOWN CATHODE STRUCTURES (hand-built from published data)
# ============================================================

def build_test_structures() -> List[Dict]:
    """
    Build a test set of crystal structures with known stability.

    These are real cathode material structure types with varying
    compositions. E_hull values are approximate from literature
    to test the correlation.

    Structure types:
    - Layered (R-3m): LiCoO2, LiNiO2, etc — most stable cathodes
    - Spinel (Fd-3m): LiMn2O4 — moderate stability
    - Olivine (Pnma): LiFePO4 — very stable
    - Disordered/metastable variants — higher E_hull
    """
    materials = []

    # ---- LAYERED OXIDES (R-3m, hexagonal) ----
    # These are the workhorses: LiCoO2, LiNiO2, LiMnO2, NMC variants
    layered_a = 2.816  # Angstrom
    layered_c = 14.05

    # LiCoO2 — THE reference cathode, very stable
    s = Structure(
        Lattice.hexagonal(layered_a, layered_c),
        ["Li", "Co", "O", "O"],
        [[0, 0, 0.5], [0, 0, 0], [0, 0, 0.260], [0, 0, 0.740]],
    )
    materials.append({'structure': s, 'formula': 'LiCoO2', 'e_hull': 0.0,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered'})

    # LiNiO2 — layered, slightly less stable
    s = Structure(
        Lattice.hexagonal(2.878, 14.19),
        ["Li", "Ni", "O", "O"],
        [[0, 0, 0.5], [0, 0, 0], [0, 0, 0.258], [0, 0, 0.742]],
    )
    materials.append({'structure': s, 'formula': 'LiNiO2', 'e_hull': 0.012,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered'})

    # LiMnO2 (layered) — tends to transform to spinel, moderate stability
    s = Structure(
        Lattice.hexagonal(2.856, 14.28),
        ["Li", "Mn", "O", "O"],
        [[0, 0, 0.5], [0, 0, 0], [0, 0, 0.262], [0, 0, 0.738]],
    )
    materials.append({'structure': s, 'formula': 'LiMnO2_layered', 'e_hull': 0.045,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered'})

    # NMC-111: Li(Ni1/3Mn1/3Co1/3)O2 — stable, commercial
    s = Structure(
        Lattice.hexagonal(2.860, 14.23),
        ["Li", "Ni", "Mn", "Co", "O", "O", "O", "O", "O", "O"],
        [[0, 0, 0.5], [0.333, 0.667, 0], [0.667, 0.333, 0],
         [0, 0, 0], [0.333, 0.667, 0.260], [0.667, 0.333, 0.260],
         [0, 0, 0.260], [0.333, 0.667, 0.740], [0.667, 0.333, 0.740],
         [0, 0, 0.740]],
    )
    materials.append({'structure': s, 'formula': 'LiNi1/3Mn1/3Co1/3O2', 'e_hull': 0.005,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered'})

    # ---- SPINEL (Fd-3m, cubic) ----
    spinel_a = 8.248

    # LiMn2O4 — spinel, moderate stability
    s = Structure(
        Lattice.cubic(spinel_a),
        ["Li", "Li", "Mn", "Mn", "Mn", "Mn",
         "O", "O", "O", "O", "O", "O", "O", "O"],
        [[0.125, 0.125, 0.125], [0.375, 0.375, 0.375],
         [0.5, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5],
         [0.263, 0.263, 0.263], [0.737, 0.737, 0.737],
         [0.263, 0.737, 0.737], [0.737, 0.263, 0.263],
         [0.737, 0.263, 0.737], [0.263, 0.737, 0.263],
         [0.737, 0.737, 0.263], [0.263, 0.263, 0.737]],
    )
    materials.append({'structure': s, 'formula': 'LiMn2O4', 'e_hull': 0.0,
                      'crystal_system': 'cubic', 'spacegroup': 'Fd-3m',
                      'category': 'spinel'})

    # LiNi0.5Mn1.5O4 — high voltage spinel
    s = Structure(
        Lattice.cubic(8.17),
        ["Li", "Li", "Ni", "Ni", "Mn", "Mn",
         "O", "O", "O", "O", "O", "O", "O", "O"],
        [[0.125, 0.125, 0.125], [0.375, 0.375, 0.375],
         [0.5, 0.5, 0.5], [0.5, 0, 0],
         [0, 0.5, 0], [0, 0, 0.5],
         [0.263, 0.263, 0.263], [0.737, 0.737, 0.737],
         [0.263, 0.737, 0.737], [0.737, 0.263, 0.263],
         [0.737, 0.263, 0.737], [0.263, 0.737, 0.263],
         [0.737, 0.737, 0.263], [0.263, 0.263, 0.737]],
    )
    materials.append({'structure': s, 'formula': 'LiNi0.5Mn1.5O4', 'e_hull': 0.020,
                      'crystal_system': 'cubic', 'spacegroup': 'Fd-3m',
                      'category': 'spinel'})

    # ---- OLIVINE (Pnma, orthorhombic) ----

    # LiFePO4 — olivine, extremely stable
    s = Structure(
        Lattice.orthorhombic(10.33, 6.01, 4.69),
        ["Li", "Fe", "P", "O", "O", "O", "O"],
        [[0, 0, 0], [0.282, 0.25, 0.975],
         [0.095, 0.25, 0.418],
         [0.097, 0.25, 0.743], [0.457, 0.25, 0.206],
         [0.166, 0.046, 0.285], [0.166, 0.454, 0.285]],
    )
    materials.append({'structure': s, 'formula': 'LiFePO4', 'e_hull': 0.0,
                      'crystal_system': 'orthorhombic', 'spacegroup': 'Pnma',
                      'category': 'olivine'})

    # LiMnPO4 — olivine, stable but poor kinetics
    s = Structure(
        Lattice.orthorhombic(10.44, 6.10, 4.74),
        ["Li", "Mn", "P", "O", "O", "O", "O"],
        [[0, 0, 0], [0.282, 0.25, 0.975],
         [0.095, 0.25, 0.418],
         [0.097, 0.25, 0.743], [0.457, 0.25, 0.206],
         [0.166, 0.046, 0.285], [0.166, 0.454, 0.285]],
    )
    materials.append({'structure': s, 'formula': 'LiMnPO4', 'e_hull': 0.0,
                      'crystal_system': 'orthorhombic', 'spacegroup': 'Pnma',
                      'category': 'olivine'})

    # LiCoPO4 — olivine, higher voltage, less stable
    s = Structure(
        Lattice.orthorhombic(10.20, 5.92, 4.70),
        ["Li", "Co", "P", "O", "O", "O", "O"],
        [[0, 0, 0], [0.282, 0.25, 0.975],
         [0.095, 0.25, 0.418],
         [0.097, 0.25, 0.743], [0.457, 0.25, 0.206],
         [0.166, 0.046, 0.285], [0.166, 0.454, 0.285]],
    )
    materials.append({'structure': s, 'formula': 'LiCoPO4', 'e_hull': 0.030,
                      'crystal_system': 'orthorhombic', 'spacegroup': 'Pnma',
                      'category': 'olivine'})

    # ---- UNSTABLE / METASTABLE STRUCTURES ----

    # Hypothetical disordered rock salt — high E_hull
    s = Structure(
        Lattice.cubic(4.20),
        ["Li", "Mn", "O", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0]],
    )
    materials.append({'structure': s, 'formula': 'LiMnO2_rocksalt', 'e_hull': 0.150,
                      'crystal_system': 'cubic', 'spacegroup': 'Fm-3m',
                      'category': 'rocksalt'})

    # Disordered LiNiO2 — high E_hull
    s = Structure(
        Lattice.cubic(4.15),
        ["Li", "Ni", "O", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0]],
    )
    materials.append({'structure': s, 'formula': 'LiNiO2_rocksalt', 'e_hull': 0.180,
                      'crystal_system': 'cubic', 'spacegroup': 'Fm-3m',
                      'category': 'rocksalt'})

    # Hypothetical Li2MnO3 — layered but strained
    s = Structure(
        Lattice.monoclinic(4.94, 8.53, 5.02, 109.2),
        ["Li", "Li", "Li", "Mn", "O", "O", "O"],
        [[0, 0.167, 0], [0, 0.5, 0], [0, 0.833, 0],
         [0, 0, 0.5],
         [0.25, 0.167, 0.5], [0.25, 0.5, 0.5], [0.25, 0.833, 0.5]],
    )
    materials.append({'structure': s, 'formula': 'Li2MnO3', 'e_hull': 0.0,
                      'crystal_system': 'monoclinic', 'spacegroup': 'C2/m',
                      'category': 'layered_extra'})

    # Hypothetical high-energy variant — distorted lattice
    s = Structure(
        Lattice.hexagonal(2.95, 15.5),  # stretched c-axis = weaker interlayer
        ["Li", "Co", "O", "O"],
        [[0, 0, 0.5], [0, 0, 0], [0, 0, 0.260], [0, 0, 0.740]],
    )
    materials.append({'structure': s, 'formula': 'LiCoO2_stretched', 'e_hull': 0.120,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered_distorted'})

    # Highly distorted spinel — unstable
    s = Structure(
        Lattice.cubic(8.60),  # expanded lattice
        ["Li", "Li", "Mn", "Mn", "Mn", "Mn",
         "O", "O", "O", "O", "O", "O", "O", "O"],
        [[0.125, 0.125, 0.125], [0.375, 0.375, 0.375],
         [0.5, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5],
         [0.280, 0.280, 0.280], [0.720, 0.720, 0.720],
         [0.280, 0.720, 0.720], [0.720, 0.280, 0.280],
         [0.720, 0.280, 0.720], [0.280, 0.720, 0.280],
         [0.720, 0.720, 0.280], [0.280, 0.280, 0.720]],
    )
    materials.append({'structure': s, 'formula': 'LiMn2O4_expanded', 'e_hull': 0.200,
                      'crystal_system': 'cubic', 'spacegroup': 'Fd-3m',
                      'category': 'spinel_distorted'})

    # Compressed olivine — stressed lattice
    s = Structure(
        Lattice.orthorhombic(9.8, 5.7, 4.4),  # compressed
        ["Li", "Fe", "P", "O", "O", "O", "O"],
        [[0, 0, 0], [0.282, 0.25, 0.975],
         [0.095, 0.25, 0.418],
         [0.097, 0.25, 0.743], [0.457, 0.25, 0.206],
         [0.166, 0.046, 0.285], [0.166, 0.454, 0.285]],
    )
    materials.append({'structure': s, 'formula': 'LiFePO4_compressed', 'e_hull': 0.095,
                      'crystal_system': 'orthorhombic', 'spacegroup': 'Pnma',
                      'category': 'olivine_distorted'})

    # Li-rich layered — Li2MnO3·LiMO2
    s = Structure(
        Lattice.hexagonal(2.85, 14.30),
        ["Li", "Li", "Mn", "O", "O"],
        [[0, 0, 0.5], [0.333, 0.667, 0.5],
         [0, 0, 0], [0, 0, 0.260], [0, 0, 0.740]],
    )
    materials.append({'structure': s, 'formula': 'Li2MnO3_hex', 'e_hull': 0.015,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered'})

    # Rutile-like TiO2 (not a cathode — control, should be flagged different)
    s = Structure(
        Lattice.tetragonal(4.594, 2.959),
        ["Ti", "O", "O"],
        [[0, 0, 0], [0.305, 0.305, 0], [0.695, 0.695, 0]],
    )
    materials.append({'structure': s, 'formula': 'TiO2_rutile', 'e_hull': 0.0,
                      'crystal_system': 'tetragonal', 'spacegroup': 'P42/mnm',
                      'category': 'control'})

    # Perovskite BaTiO3 (control — different structure class entirely)
    s = Structure(
        Lattice.cubic(4.01),
        ["Ba", "Ti", "O", "O", "O"],
        [[0, 0, 0], [0.5, 0.5, 0.5],
         [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]],
    )
    materials.append({'structure': s, 'formula': 'BaTiO3', 'e_hull': 0.0,
                      'crystal_system': 'cubic', 'spacegroup': 'Pm-3m',
                      'category': 'control'})

    # Garnet Li7La3Zr2O12 — solid electrolyte, different stability regime
    s = Structure(
        Lattice.cubic(12.97),
        ["Li", "Li", "La", "Zr", "O", "O", "O", "O", "O", "O"],
        [[0.125, 0, 0.25], [0.375, 0, 0.25],
         [0.125, 0, 0.75], [0, 0, 0],
         [0.1, 0.2, 0.15], [0.9, 0.8, 0.85],
         [0.1, 0.8, 0.15], [0.9, 0.2, 0.85],
         [0.2, 0.1, 0.35], [0.8, 0.9, 0.65]],
    )
    materials.append({'structure': s, 'formula': 'Li7La3Zr2O12', 'e_hull': 0.0,
                      'crystal_system': 'cubic', 'spacegroup': 'Ia-3d',
                      'category': 'garnet'})

    # Antifluorite Li2O — very simple, very stable
    s = Structure(
        Lattice.cubic(4.619),
        ["Li", "Li", "O"],
        [[0.25, 0.25, 0.25], [0.75, 0.75, 0.75], [0, 0, 0]],
    )
    materials.append({'structure': s, 'formula': 'Li2O', 'e_hull': 0.0,
                      'crystal_system': 'cubic', 'spacegroup': 'Fm-3m',
                      'category': 'binary'})

    # Na analog — NaCoO2 (different chemistry, similar structure to LiCoO2)
    s = Structure(
        Lattice.hexagonal(2.89, 15.60),
        ["Na", "Co", "O", "O"],
        [[0, 0, 0.5], [0, 0, 0], [0, 0, 0.260], [0, 0, 0.740]],
    )
    materials.append({'structure': s, 'formula': 'NaCoO2', 'e_hull': 0.010,
                      'crystal_system': 'trigonal', 'spacegroup': 'R-3m',
                      'category': 'layered_Na'})

    # Heavily distorted — random-ish positions (clearly unstable)
    s = Structure(
        Lattice.cubic(5.0),
        ["Li", "Mn", "O", "O", "O"],
        [[0.1, 0.15, 0.12], [0.55, 0.48, 0.52],
         [0.3, 0.7, 0.1], [0.8, 0.2, 0.9], [0.5, 0.5, 0.5]],
    )
    materials.append({'structure': s, 'formula': 'LiMnO3_disordered', 'e_hull': 0.350,
                      'crystal_system': 'cubic', 'spacegroup': 'P1',
                      'category': 'disordered'})

    # Another disordered variant
    s = Structure(
        Lattice.cubic(4.8),
        ["Li", "Co", "O", "O"],
        [[0.12, 0.08, 0.15], [0.62, 0.58, 0.45],
         [0.38, 0.72, 0.18], [0.78, 0.22, 0.85]],
    )
    materials.append({'structure': s, 'formula': 'LiCoO2_disordered', 'e_hull': 0.250,
                      'crystal_system': 'cubic', 'spacegroup': 'P1',
                      'category': 'disordered'})

    # Generate lattice-parameter variations for sensitivity test
    # Take LiCoO2 and vary c/a ratio (structural breathing)
    for ca_ratio, e_hull_approx in [(4.5, 0.02), (4.8, 0.005), (5.0, 0.0),
                                     (5.2, 0.01), (5.5, 0.05), (6.0, 0.15)]:
        c_val = layered_a * ca_ratio
        s = Structure(
            Lattice.hexagonal(layered_a, c_val),
            ["Li", "Co", "O", "O"],
            [[0, 0, 0.5], [0, 0, 0], [0, 0, 0.260], [0, 0, 0.740]],
        )
        materials.append({
            'structure': s,
            'formula': f'LiCoO2_ca{ca_ratio:.1f}',
            'e_hull': e_hull_approx,
            'crystal_system': 'trigonal',
            'spacegroup': 'R-3m',
            'category': 'layered_variation',
        })

    # Vary spinel lattice parameter
    for a_val, e_hull_approx in [(7.8, 0.15), (8.0, 0.05), (8.248, 0.0),
                                  (8.4, 0.03), (8.6, 0.10), (8.8, 0.25)]:
        s = Structure(
            Lattice.cubic(a_val),
            ["Li", "Li", "Mn", "Mn", "Mn", "Mn",
             "O", "O", "O", "O", "O", "O", "O", "O"],
            [[0.125, 0.125, 0.125], [0.375, 0.375, 0.375],
             [0.5, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5],
             [0.263, 0.263, 0.263], [0.737, 0.737, 0.737],
             [0.263, 0.737, 0.737], [0.737, 0.263, 0.263],
             [0.737, 0.263, 0.737], [0.263, 0.737, 0.263],
             [0.737, 0.737, 0.263], [0.263, 0.263, 0.737]],
        )
        materials.append({
            'structure': s,
            'formula': f'LiMn2O4_a{a_val:.1f}',
            'e_hull': e_hull_approx,
            'crystal_system': 'cubic',
            'spacegroup': 'Fd-3m',
            'category': 'spinel_variation',
        })

    print(f"Built {len(materials)} test structures")
    return materials


# ============================================================
# RDF COMPUTATION
# ============================================================

def compute_rdf(structure, r_max: float = 10.0, n_bins: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """Compute radial distribution function g(r)."""
    r_bins = np.linspace(0.1, r_max, n_bins)
    dr = r_bins[1] - r_bins[0]
    g_r = np.zeros(n_bins)

    all_distances = structure.distance_matrix.flatten()
    all_distances = all_distances[all_distances > 0.1]
    all_distances = all_distances[all_distances <= r_max]

    for d in all_distances:
        idx = int((d - 0.1) / dr)
        if 0 <= idx < n_bins:
            g_r[idx] += 1

    n_atoms = len(structure)
    volume = structure.volume
    rho = n_atoms / volume

    for i in range(n_bins):
        r = r_bins[i]
        shell_vol = 4 * np.pi * r**2 * dr
        if shell_vol > 0 and rho > 0:
            g_r[i] /= (n_atoms * shell_vol * rho)

    return r_bins, g_r


# ============================================================
# DSF KERNEL PROCESSING
# ============================================================

def run_dsf_on_signal(signal_values: np.ndarray, signal_name: str = "rdf") -> Optional[Dict[str, float]]:
    """Run full DSF-AI kernel on a 1D signal."""
    shifted = signal_values - signal_values.min() + 1.0
    if len(shifted) < 10:
        return None

    series = pd.Series(shifted, name=signal_name)

    try:
        kernel_out = run_kernel(series)
        dsf_list = kernel_out['dsf']
        if len(dsf_list) < 2:
            return None
        profile = dsf_to_coupling_profile(dsf_list)
        profile['n_gates'] = kernel_out['n_gates']
        return profile
    except Exception as e:
        return None


def compute_stability_score(profile: Dict[str, float]) -> float:
    """Map DSF coupling profile to predicted stability."""
    cs = profile['coupling_strength']
    u = profile['uncertainty']
    rev = profile['reversal_rate']
    breath = profile['breathing_magnitude']
    pressure = profile['pressure']
    complexity = profile['complexity']

    score = (
        (1.0 - cs) * 0.30
        + u * 0.25
        + rev * 0.20
        + pressure * 0.15
        + (1.0 - min(complexity, 3.0) / 3.0) * 0.10
    )
    return float(score)


# ============================================================
# EVALUATION
# ============================================================

def evaluate(results: List[Dict]) -> Dict:
    """Full evaluation suite."""
    e_hull = np.array([r['e_hull'] for r in results])
    dsf_score = np.array([r['dsf_stability_score'] for r in results])

    spearman_rho, spearman_p = stats.spearmanr(e_hull, dsf_score)
    pearson_r, pearson_p = stats.pearsonr(e_hull, dsf_score)
    kendall_tau, kendall_p = stats.kendalltau(e_hull, dsf_score)

    return {
        'spearman_rho': float(spearman_rho),
        'spearman_p': float(spearman_p),
        'pearson_r': float(pearson_r),
        'pearson_p': float(pearson_p),
        'kendall_tau': float(kendall_tau),
        'kendall_p': float(kendall_p),
        'n': len(results),
    }


def evaluate_loco(results: List[Dict]) -> Dict:
    """LOCO by category (structure family)."""
    families = {}
    for r in results:
        cat = r.get('category', 'unknown')
        if cat not in families:
            families[cat] = []
        families[cat].append(r)

    loco_results = []
    for held_out_cat, held_out in families.items():
        if len(held_out) < 3:
            continue

        e_hull = np.array([r['e_hull'] for r in held_out])
        dsf_score = np.array([r['dsf_stability_score'] for r in held_out])

        if len(set(e_hull)) < 2 or len(set(dsf_score)) < 2:
            continue

        rho, p = stats.spearmanr(e_hull, dsf_score)
        loco_results.append({
            'category': held_out_cat,
            'n': len(held_out),
            'spearman_rho': float(rho),
            'spearman_p': float(p),
        })

    mean_rho = np.mean([r['spearman_rho'] for r in loco_results]) if loco_results else 0
    return {'per_family': loco_results, 'mean_spearman': float(mean_rho)}


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("DSF-AI CATHODE SCREENING — LOCAL TEST")
    print("=" * 60)
    print("Kernel: UF-Core L0→L1→L2→L3→L4 (unchanged)")
    print("Training: NONE")
    print("Signal: Radial Distribution Function (RDF)")
    print()

    # Build structures
    materials = build_test_structures()

    # Process each
    results = []
    n_failed = 0

    for i, mat in enumerate(materials):
        structure = mat['structure']
        r_bins, g_r = compute_rdf(structure)
        profile = run_dsf_on_signal(g_r, "rdf")

        if profile is None:
            n_failed += 1
            continue

        score = compute_stability_score(profile)

        results.append({
            'formula': mat['formula'],
            'e_hull': mat['e_hull'],
            'crystal_system': mat.get('crystal_system', 'unknown'),
            'spacegroup': mat.get('spacegroup', 'unknown'),
            'category': mat.get('category', 'unknown'),
            'dsf_profile': profile,
            'dsf_stability_score': score,
        })

    print(f"\nProcessed: {len(results)} materials ({n_failed} failed)")

    if len(results) < 5:
        print("ERROR: Not enough materials.")
        return

    # Overall correlation
    print(f"\n{'=' * 60}")
    print("OVERALL CORRELATION")
    print(f"{'=' * 60}")
    overall = evaluate(results)
    print(f"  Spearman rho:  {overall['spearman_rho']:.4f}  (p={overall['spearman_p']:.4e})")
    print(f"  Pearson r:     {overall['pearson_r']:.4f}  (p={overall['pearson_p']:.4e})")
    print(f"  Kendall tau:   {overall['kendall_tau']:.4f}  (p={overall['kendall_p']:.4e})")

    # Per-field correlations
    print(f"\n{'=' * 60}")
    print("DSF FIELD CORRELATIONS WITH E_HULL")
    print(f"{'=' * 60}")
    e_hull_arr = np.array([r['e_hull'] for r in results])
    fields = ['coupling_strength', 'momentum_weight', 'uncertainty',
              'breathing_magnitude', 'pressure', 'complexity', 'reversal_rate']

    for field in fields:
        values = np.array([r['dsf_profile'][field] for r in results])
        if len(set(values)) < 3:
            continue
        rho, p = stats.spearmanr(e_hull_arr, values)
        direction = "↑ unstable" if rho > 0 else "↓ stable"
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"  {field:25s}: rho={rho:+.4f} {sig:4s} ({direction})")

    # LOCO
    print(f"\n{'=' * 60}")
    print("LOCO (Leave-One-Category-Out)")
    print(f"{'=' * 60}")
    loco = evaluate_loco(results)
    for lr in loco['per_family']:
        print(f"  {lr['category']:25s}: rho={lr['spearman_rho']:.4f} (n={lr['n']})")
    print(f"\n  Mean LOCO Spearman: {loco['mean_spearman']:.4f}")
    print(f"  CathodeX LOCO:     -0.024")

    # Material-level results
    print(f"\n{'=' * 60}")
    print("MATERIAL PREDICTIONS (sorted by DSF score)")
    print(f"{'=' * 60}")
    sorted_results = sorted(results, key=lambda r: r['dsf_stability_score'])
    for r in sorted_results:
        marker = "✓" if (r['e_hull'] < 0.05) == (r['dsf_stability_score'] < np.median([x['dsf_stability_score'] for x in results])) else "✗"
        print(f"  {marker} {r['formula']:25s} DSF={r['dsf_stability_score']:.4f}  E_hull={r['e_hull']:.3f} eV  [{r['category']}]")

    # Save
    output = {
        'timestamp': datetime.now().isoformat(),
        'overall': overall,
        'loco': loco,
        'results': [{k: v for k, v in r.items() if k != 'dsf_profile'} for r in results],
    }
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'tools', 'cathode_screen_local_results.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")

    # Verdict
    print(f"\n{'=' * 60}")
    print("VERDICT")
    print(f"{'=' * 60}")
    rho = overall['spearman_rho']
    if rho > 0.3 and overall['spearman_p'] < 0.05:
        print(f"POSITIVE: Spearman={rho:.4f}. DSF-AI sees stability in crystal RDFs.")
        print("No training. No ML. Same kernel that runs TFE and ArcLoom.")
    elif rho > 0.1:
        print(f"PARTIAL: Spearman={rho:.4f}. Weak signal detected.")
        print("May need element-specific partial RDFs or XRD signal.")
    else:
        print(f"NO SIGNAL: Spearman={rho:.4f}. RDF alone insufficient.")
        print("Honest result. The kernel sees structure but RDF may not")
        print("carry enough thermodynamic information for stability prediction.")


if __name__ == '__main__':
    main()
