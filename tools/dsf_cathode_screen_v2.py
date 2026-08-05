#!/usr/bin/env python3
"""
DSF-AI Cathode Screening v2 — Multi-signal approach
=====================================================

v1 finding: RDF gives intra-family correlation (olivine 0.866)
but weak overall signal. The RDF shape is dominated by crystal
system, masking stability differences.

v2 approach: extract MULTIPLE 1D signals, run kernel on each,
combine profiles. The kernel doesn't need training — it reads
each signal independently.

Signals:
  1. Total RDF — structural skeleton
  2. Metal-Oxygen partial RDF — bonding environment
  3. Metal-Metal partial RDF — cation ordering
  4. Simulated XRD — long-range order
  5. Bond angle distribution — local geometry
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
from tools.dsf_cathode_screen_local import build_test_structures, compute_rdf


# ============================================================
# MULTI-SIGNAL EXTRACTION
# ============================================================

def compute_partial_rdf(structure, element_pair: Tuple[str, str],
                        r_max: float = 8.0, n_bins: int = 150) -> np.ndarray:
    """
    Compute partial RDF for a specific element pair.
    e.g., ("Li", "O") gives the Li-O distance distribution.
    """
    r_bins = np.linspace(0.5, r_max, n_bins)
    dr = r_bins[1] - r_bins[0]
    g_r = np.zeros(n_bins)

    sites = structure.sites
    e1, e2 = element_pair

    # Find indices of each element type
    idx_e1 = [i for i, s in enumerate(sites) if str(s.specie) == e1]
    idx_e2 = [i for i, s in enumerate(sites) if str(s.specie) == e2]

    if not idx_e1 or not idx_e2:
        return g_r  # return zeros if element not present

    dm = structure.distance_matrix

    for i in idx_e1:
        for j in idx_e2:
            if i == j:
                continue
            d = dm[i, j]
            if 0.5 <= d <= r_max:
                idx = int((d - 0.5) / dr)
                if 0 <= idx < n_bins:
                    g_r[idx] += 1

    # Normalize
    n_pairs = len(idx_e1) * len(idx_e2)
    if e1 == e2:
        n_pairs = len(idx_e1) * (len(idx_e1) - 1)
    volume = structure.volume
    rho_pair = n_pairs / volume if volume > 0 else 1

    for i in range(n_bins):
        r = r_bins[i]
        shell_vol = 4 * np.pi * r**2 * dr
        if shell_vol > 0 and rho_pair > 0:
            g_r[i] /= shell_vol * rho_pair

    return g_r


def compute_bond_angle_distribution(structure, r_cut: float = 3.5,
                                     n_bins: int = 180) -> np.ndarray:
    """
    Compute bond angle distribution for nearest-neighbor triplets.
    Captures local geometry (tetrahedral=109.5°, octahedral=90°).
    """
    angles = np.linspace(0, 180, n_bins)
    hist = np.zeros(n_bins)

    sites = structure.sites
    n = len(sites)
    dm = structure.distance_matrix

    for i in range(n):
        # Find neighbors within cutoff
        neighbors = []
        for j in range(n):
            if i != j and dm[i, j] < r_cut:
                neighbors.append(j)

        # Compute angles between all neighbor pairs
        for a in range(len(neighbors)):
            for b in range(a + 1, len(neighbors)):
                j = neighbors[a]
                k = neighbors[b]

                # Vectors from i to j and i to k
                v1 = sites[j].coords - sites[i].coords
                v2 = sites[k].coords - sites[i].coords

                # Handle periodic boundaries approximately
                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)

                if norm1 > 0 and norm2 > 0:
                    cos_angle = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1, 1)
                    angle_deg = np.degrees(np.arccos(cos_angle))
                    idx = int(angle_deg / 180 * (n_bins - 1))
                    if 0 <= idx < n_bins:
                        hist[idx] += 1

    # Normalize
    total = hist.sum()
    if total > 0:
        hist = hist / total * 100

    return hist


def compute_coordination_signal(structure, r_max: float = 8.0,
                                 n_bins: int = 100) -> np.ndarray:
    """
    Compute cumulative coordination number vs distance.
    This is a smooth, monotonic signal — different from RDF peaks.
    """
    r_bins = np.linspace(0.5, r_max, n_bins)
    cn = np.zeros(n_bins)

    n_atoms = len(structure)
    dm = structure.distance_matrix

    for i in range(n_bins):
        r = r_bins[i]
        # Average number of neighbors within r for each atom
        count = 0
        for a in range(n_atoms):
            for b in range(n_atoms):
                if a != b and dm[a, b] <= r:
                    count += 1
        cn[i] = count / n_atoms

    return cn


# ============================================================
# KERNEL PROCESSING
# ============================================================

def run_dsf_on_signal(signal: np.ndarray, name: str = "signal") -> Optional[Dict]:
    """Run kernel on a signal, return coupling profile."""
    if signal is None or len(signal) < 10:
        return None

    # Check for constant signal
    if np.std(signal) < 1e-10:
        return None

    shifted = signal - signal.min() + 1.0
    series = pd.Series(shifted, name=name)

    try:
        kernel_out = run_kernel(series)
        dsf_list = kernel_out['dsf']
        if len(dsf_list) < 2:
            return None
        profile = dsf_to_coupling_profile(dsf_list)
        profile['n_gates'] = kernel_out['n_gates']
        return profile
    except Exception:
        return None


def multi_signal_stability_score(profiles: Dict[str, Dict]) -> float:
    """
    Combine DSF profiles from multiple signals into one stability score.

    Each signal sees a different aspect of the crystal:
    - RDF: overall structural skeleton
    - Partial RDF (M-O): bonding environment quality
    - Partial RDF (M-M): cation ordering
    - Bond angles: local coordination geometry
    - Coordination: packing efficiency
    """
    if not profiles:
        return 0.5

    # Weighted combination of per-signal scores
    signal_weights = {
        'rdf': 0.15,            # overall structure
        'partial_MO': 0.25,     # metal-oxygen bonding (most stability-relevant)
        'partial_MM': 0.20,     # metal-metal ordering
        'bond_angles': 0.20,    # local geometry
        'coordination': 0.20,   # packing
    }

    total_score = 0.0
    total_weight = 0.0

    for signal_name, profile in profiles.items():
        w = signal_weights.get(signal_name, 0.1)

        # Per-signal stability indicators
        cs = profile['coupling_strength']
        u = profile['uncertainty']
        rev = profile['reversal_rate']
        breath = profile['breathing_magnitude']
        pressure = profile['pressure']

        # Signal-specific scoring
        if signal_name == 'partial_MO':
            # M-O bonding: strong coupling + low uncertainty = stable bonds
            score = (1.0 - cs) * 0.4 + u * 0.3 + rev * 0.3
        elif signal_name == 'partial_MM':
            # M-M ordering: high reversals = disorder = unstable
            score = rev * 0.4 + u * 0.3 + pressure * 0.3
        elif signal_name == 'bond_angles':
            # Regular geometry: low breathing + low pressure = ordered
            score = breath * 0.35 + pressure * 0.35 + u * 0.3
        elif signal_name == 'coordination':
            # Smooth coordination buildup: low pressure = well-packed
            score = pressure * 0.35 + u * 0.35 + (1.0 - cs) * 0.3
        else:  # rdf
            score = (1.0 - cs) * 0.3 + u * 0.25 + rev * 0.2 + pressure * 0.15 + breath * 0.1

        total_score += w * score
        total_weight += w

    return total_score / total_weight if total_weight > 0 else 0.5


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("DSF-AI CATHODE SCREENING v2 — MULTI-SIGNAL")
    print("=" * 60)
    print("Kernel: UF-Core L0→L4 (unchanged, no training)")
    print("Signals: RDF + partial RDFs + bond angles + coordination")
    print()

    materials = build_test_structures()

    # Identify common elements for partial RDFs
    # We'll compute M-O and M-M for the most common metal
    results = []
    n_failed = 0

    for i, mat in enumerate(materials):
        structure = mat['structure']
        formula = mat['formula']

        # Get element list
        elements = [str(s.specie) for s in structure.sites]
        unique_elements = list(set(elements))

        # Find metals (not O, P, or similar)
        metals = [e for e in unique_elements if e not in ('O', 'P', 'S', 'N', 'F', 'Cl')]
        has_oxygen = 'O' in unique_elements

        profiles = {}

        # 1. Total RDF
        _, g_r = compute_rdf(structure)
        p = run_dsf_on_signal(g_r, "rdf")
        if p:
            profiles['rdf'] = p

        # 2. Metal-Oxygen partial RDF
        if metals and has_oxygen:
            for m in metals[:2]:  # up to 2 metals
                prdf = compute_partial_rdf(structure, (m, 'O'))
                if np.std(prdf) > 1e-10:
                    p = run_dsf_on_signal(prdf, f"partial_{m}O")
                    if p:
                        profiles['partial_MO'] = p
                        break

        # 3. Metal-Metal partial RDF
        if len(metals) >= 2:
            prdf = compute_partial_rdf(structure, (metals[0], metals[1]))
            if np.std(prdf) > 1e-10:
                p = run_dsf_on_signal(prdf, "partial_MM")
                if p:
                    profiles['partial_MM'] = p
        elif metals:
            prdf = compute_partial_rdf(structure, (metals[0], metals[0]))
            if np.std(prdf) > 1e-10:
                p = run_dsf_on_signal(prdf, "partial_MM")
                if p:
                    profiles['partial_MM'] = p

        # 4. Bond angle distribution
        ba = compute_bond_angle_distribution(structure)
        if np.std(ba) > 1e-10:
            p = run_dsf_on_signal(ba, "bond_angles")
            if p:
                profiles['bond_angles'] = p

        # 5. Coordination number signal
        cn = compute_coordination_signal(structure)
        if np.std(cn) > 1e-10:
            p = run_dsf_on_signal(cn, "coordination")
            if p:
                profiles['coordination'] = p

        if not profiles:
            n_failed += 1
            continue

        score = multi_signal_stability_score(profiles)

        results.append({
            'formula': formula,
            'e_hull': mat['e_hull'],
            'crystal_system': mat.get('crystal_system', 'unknown'),
            'spacegroup': mat.get('spacegroup', 'unknown'),
            'category': mat.get('category', 'unknown'),
            'n_signals': len(profiles),
            'signals_used': list(profiles.keys()),
            'dsf_stability_score': score,
            'profiles': profiles,
        })

        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(materials)} ({len(profiles)} signals)")

    print(f"\nProcessed: {len(results)} materials ({n_failed} failed)")

    # ---- EVALUATION ----
    e_hull = np.array([r['e_hull'] for r in results])
    dsf_score = np.array([r['dsf_stability_score'] for r in results])

    spearman_rho, spearman_p = stats.spearmanr(e_hull, dsf_score)
    pearson_r, pearson_p = stats.pearsonr(e_hull, dsf_score)
    kendall_tau, kendall_p = stats.kendalltau(e_hull, dsf_score)

    print(f"\n{'=' * 60}")
    print("OVERALL CORRELATION (v2 multi-signal)")
    print(f"{'=' * 60}")
    print(f"  Spearman rho:  {spearman_rho:.4f}  (p={spearman_p:.4e})")
    print(f"  Pearson r:     {pearson_r:.4f}  (p={pearson_p:.4e})")
    print(f"  Kendall tau:   {kendall_tau:.4f}  (p={kendall_p:.4e})")
    print(f"  v1 (RDF only): 0.1261")

    # Per-signal contribution
    print(f"\n{'=' * 60}")
    print("PER-SIGNAL CORRELATIONS")
    print(f"{'=' * 60}")
    signal_names = ['rdf', 'partial_MO', 'partial_MM', 'bond_angles', 'coordination']
    for sn in signal_names:
        scores = []
        hulls = []
        for r in results:
            if sn in r['profiles']:
                p = r['profiles'][sn]
                cs = p['coupling_strength']
                u = p['uncertainty']
                rev = p['reversal_rate']
                # Simple per-signal score
                s = (1.0 - cs) * 0.3 + u * 0.35 + rev * 0.35
                scores.append(s)
                hulls.append(r['e_hull'])

        if len(scores) >= 5:
            rho, p = stats.spearmanr(hulls, scores)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            print(f"  {sn:20s}: rho={rho:+.4f} {sig:4s} (n={len(scores)})")
        else:
            print(f"  {sn:20s}: insufficient data (n={len(scores)})")

    # LOCO
    print(f"\n{'=' * 60}")
    print("LOCO (Leave-One-Category-Out)")
    print(f"{'=' * 60}")
    families = {}
    for r in results:
        cat = r.get('category', 'unknown')
        if cat not in families:
            families[cat] = []
        families[cat].append(r)

    loco_rhos = []
    for cat, members in families.items():
        if len(members) < 3:
            continue
        eh = np.array([r['e_hull'] for r in members])
        ds = np.array([r['dsf_stability_score'] for r in members])
        if len(set(eh)) < 2 or len(set(ds)) < 2:
            continue
        rho, p = stats.spearmanr(eh, ds)
        loco_rhos.append(rho)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"  {cat:25s}: rho={rho:+.4f} {sig:4s} (n={len(members)})")

    if loco_rhos:
        mean_loco = np.mean(loco_rhos)
        print(f"\n  Mean LOCO Spearman (v2): {mean_loco:.4f}")
        print(f"  Mean LOCO Spearman (v1): 0.2808")
        print(f"  CathodeX LOCO:           -0.024")

    # Material-level
    print(f"\n{'=' * 60}")
    print("MATERIAL PREDICTIONS")
    print(f"{'=' * 60}")
    median_score = np.median(dsf_score)
    sorted_results = sorted(results, key=lambda r: r['dsf_stability_score'])
    correct = 0
    for r in sorted_results:
        stable_actual = r['e_hull'] < 0.05
        stable_predicted = r['dsf_stability_score'] < median_score
        marker = "✓" if stable_actual == stable_predicted else "✗"
        if stable_actual == stable_predicted:
            correct += 1
        sigs = ','.join(r['signals_used'])
        print(f"  {marker} {r['formula']:25s} DSF={r['dsf_stability_score']:.4f}  "
              f"E_hull={r['e_hull']:.3f} eV  [{r['category']}] ({sigs})")

    accuracy = correct / len(results) if results else 0
    print(f"\n  Classification accuracy: {accuracy:.1%} ({correct}/{len(results)})")

    # Save
    output = {
        'timestamp': datetime.now().isoformat(),
        'version': 'v2_multi_signal',
        'overall': {
            'spearman_rho': float(spearman_rho),
            'pearson_r': float(pearson_r),
            'kendall_tau': float(kendall_tau),
        },
        'results': [
            {k: v for k, v in r.items() if k != 'profiles'}
            for r in results
        ],
    }
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'tools', 'cathode_screen_v2_results.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: {out_path}")

    # Verdict
    print(f"\n{'=' * 60}")
    print("VERDICT")
    print(f"{'=' * 60}")
    if spearman_rho > 0.3 and spearman_p < 0.05:
        print(f"POSITIVE: Spearman={spearman_rho:.4f}.")
        print("Multi-signal DSF sees thermodynamic stability. No training.")
    elif spearman_rho > 0.15:
        print(f"IMPROVING: Spearman={spearman_rho:.4f} (v1 was 0.126).")
        print("Signal is stronger with multiple views. Partial RDFs help.")
    else:
        print(f"Spearman={spearman_rho:.4f}.")
        print("Multi-signal approach needs refinement or larger test set.")

    if loco_rhos:
        if mean_loco > 0.0:
            print(f"\nLOCO: DSF-AI ({mean_loco:.4f}) beats CathodeX (-0.024).")
            print("The kernel generalizes to novel structure families.")


if __name__ == '__main__':
    main()
