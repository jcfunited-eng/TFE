#!/usr/bin/env python3
"""
DSF-AI Cathode Material Screening Test
=======================================

Tests whether the DSF-AI kernel (L0-L4) can predict thermodynamic
stability (energy above hull) of crystal structures — the same task
CathodeX does with a 5-member ML ensemble.

Approach:
    1. Fetch lithium cathode materials from Materials Project
    2. Compute Radial Distribution Function (RDF) for each structure
    3. Run DSF-AI kernel on each RDF signal
    4. Extract L4 DSF coupling profile
    5. Map DSF fields to stability prediction
    6. Evaluate correlation with known E_hull values
    7. Run LOCO-style structural family splits

The kernel has never seen a crystal structure before.
If this works, it works because structure IS the signal.

Usage:
    # With Materials Project API key:
    MP_API_KEY=your_key python tools/dsf_cathode_screen.py

    # Or set it interactively:
    python tools/dsf_cathode_screen.py --api-key YOUR_KEY
"""

import sys
import os
import json
import argparse
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.derive_sppu_weights import build_field_series, run_kernel, dsf_to_coupling_profile


# ============================================================
# STAGE 1: DATA ACQUISITION
# ============================================================

def fetch_cathode_materials(api_key: str, max_materials: int = 500) -> List[Dict]:
    """
    Fetch lithium transition metal oxide cathode materials
    from Materials Project with known E_hull values.
    """
    from mp_api.client import MPRester

    print(f"Fetching up to {max_materials} Li cathode materials from Materials Project...")

    with MPRester(api_key) as mpr:
        # Query: lithium-containing oxides with transition metals
        # Same chemical space as CathodeX
        docs = mpr.materials.summary.search(
            elements=["Li", "O"],
            num_elements=(3, 5),  # ternary to quinary
            fields=[
                "material_id",
                "formula_pretty",
                "structure",
                "energy_above_hull",
                "formation_energy_per_atom",
                "band_gap",
                "density",
                "nsites",
                "symmetry",
            ],
            num_chunks=None,
        )

    # Filter to materials with valid E_hull
    materials = []
    for doc in docs:
        e_hull = doc.energy_above_hull
        if e_hull is not None and doc.structure is not None:
            materials.append({
                'material_id': str(doc.material_id),
                'formula': doc.formula_pretty,
                'structure': doc.structure,
                'e_hull': float(e_hull),
                'formation_energy': float(doc.formation_energy_per_atom) if doc.formation_energy_per_atom is not None else None,
                'band_gap': float(doc.band_gap) if doc.band_gap is not None else None,
                'density': float(doc.density) if doc.density is not None else None,
                'nsites': int(doc.nsites),
                'spacegroup': doc.symmetry.symbol if doc.symmetry else "unknown",
                'crystal_system': doc.symmetry.crystal_system if doc.symmetry else "unknown",
            })

        if len(materials) >= max_materials:
            break

    print(f"  Got {len(materials)} materials with valid E_hull")
    return materials


# ============================================================
# STAGE 2: RDF SIGNAL EXTRACTION
# ============================================================

def compute_rdf(structure, r_max: float = 10.0, n_bins: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the radial distribution function g(r) for a crystal structure.

    This is the 1D signal the kernel will read. It contains:
    - Peak positions: interatomic distances (structural skeleton)
    - Peak heights: coordination numbers (bonding intensity)
    - Peak widths: thermal/structural disorder
    - Gaps between peaks: structural voids (negative space)

    All the information the kernel needs is here.
    """
    from pymatgen.core.structure import Structure

    r_bins = np.linspace(0.1, r_max, n_bins)
    dr = r_bins[1] - r_bins[0]
    g_r = np.zeros(n_bins)

    # Get all pairwise distances
    all_distances = structure.distance_matrix.flatten()
    all_distances = all_distances[all_distances > 0.1]  # exclude self
    all_distances = all_distances[all_distances <= r_max]

    # Build histogram
    for d in all_distances:
        idx = int((d - 0.1) / dr)
        if 0 <= idx < n_bins:
            g_r[idx] += 1

    # Normalize by shell volume and number density
    n_atoms = len(structure)
    volume = structure.volume
    rho = n_atoms / volume  # number density

    for i in range(n_bins):
        r = r_bins[i]
        shell_vol = 4 * np.pi * r**2 * dr
        if shell_vol > 0 and rho > 0:
            g_r[i] /= (n_atoms * shell_vol * rho)

    return r_bins, g_r


def compute_xrd_signal(structure, two_theta_range: Tuple[float, float] = (10, 90),
                       n_points: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute simulated XRD pattern as a 1D signal.
    Backup signal if RDF doesn't give enough contrast.
    """
    from pymatgen.analysis.diffraction.xrd import XRDCalculator

    calc = XRDCalculator()
    pattern = calc.get_pattern(structure, two_theta_range=two_theta_range)

    # Resample to uniform grid
    two_theta = np.linspace(two_theta_range[0], two_theta_range[1], n_points)
    intensity = np.zeros(n_points)

    # Gaussian broadening of peaks
    sigma = 0.3  # degrees
    for peak_pos, peak_int in zip(pattern.x, pattern.y):
        intensity += peak_int * np.exp(-0.5 * ((two_theta - peak_pos) / sigma) ** 2)

    # Normalize
    if intensity.max() > 0:
        intensity = intensity / intensity.max() * 100.0

    return two_theta, intensity


# ============================================================
# STAGE 3: DSF-AI KERNEL PROCESSING
# ============================================================

def run_dsf_on_signal(signal_values: np.ndarray, signal_name: str = "rdf") -> Optional[Dict[str, float]]:
    """
    Run the full DSF-AI kernel on a 1D signal and extract coupling profile.

    The kernel doesn't know this is a crystal structure.
    It sees a 1D signal with peaks, valleys, slopes, curvature.
    It extracts structural field properties. That's all.
    """
    # Shift to positive range (kernel uses log internally)
    shifted = signal_values - signal_values.min() + 1.0

    # Need enough points for meaningful gate segmentation
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
        print(f"  Kernel error: {e}")
        return None


def compute_stability_score(profile: Dict[str, float]) -> float:
    """
    Map DSF coupling profile to predicted stability.

    Hypothesis: thermodynamically stable structures have:
    - HIGH coupling strength (strong, well-defined peaks in RDF)
    - LOW uncertainty (kernel is confident about the structure)
    - LOW reversal rate (structural signal is consistent)
    - MODERATE breathing (some structural freedom but not chaotic)
    - LOW pressure (transitions are smooth, not sharp)

    Unstable structures (high E_hull) have:
    - Diffuse RDF peaks → low coupling strength
    - High structural ambiguity → high uncertainty
    - Frequent direction changes → high reversal rate

    The score is LOWER for more stable materials (like E_hull).
    """
    cs = profile['coupling_strength']
    u = profile['uncertainty']
    rev = profile['reversal_rate']
    breath = profile['breathing_magnitude']
    pressure = profile['pressure']
    complexity = profile['complexity']

    # Stability score: higher = less stable (matches E_hull convention)
    # Strong coupling → stable → low score
    # High uncertainty → unstable → high score
    # High reversals → unstable → high score
    score = (
        (1.0 - cs) * 0.30          # weak coupling = unstable
        + u * 0.25                   # high uncertainty = unstable
        + rev * 0.20                 # frequent reversals = unstable
        + pressure * 0.15            # high pressure = sharp transitions = unstable
        + (1.0 - min(complexity, 3.0) / 3.0) * 0.10  # low complexity = featureless = unstable
    )

    return float(score)


# ============================================================
# STAGE 4: EVALUATION
# ============================================================

def evaluate_correlation(materials: List[Dict], results: List[Dict]) -> Dict[str, Any]:
    """
    Evaluate DSF stability predictions against known E_hull values.
    """
    e_hull = np.array([r['e_hull'] for r in results])
    dsf_score = np.array([r['dsf_stability_score'] for r in results])

    # Spearman rank correlation (same metric CathodeX reports)
    spearman_rho, spearman_p = stats.spearmanr(e_hull, dsf_score)

    # Pearson correlation
    pearson_r, pearson_p = stats.pearsonr(e_hull, dsf_score)

    # Kendall tau
    kendall_tau, kendall_p = stats.kendalltau(e_hull, dsf_score)

    # Classification accuracy: can we triage STABLE vs UNSTABLE?
    # CathodeX uses E_hull = 0 as stable, > 0 as unstable
    # More useful: E_hull < 0.05 eV = stable
    threshold = 0.05  # eV
    is_stable = e_hull < threshold

    # DSF triage: use median DSF score as threshold
    dsf_median = np.median(dsf_score)
    dsf_predicts_stable = dsf_score < dsf_median

    # Confusion matrix
    tp = np.sum(is_stable & dsf_predicts_stable)
    fp = np.sum(~is_stable & dsf_predicts_stable)
    fn = np.sum(is_stable & ~dsf_predicts_stable)
    tn = np.sum(~is_stable & ~dsf_predicts_stable)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    accuracy = (tp + tn) / len(e_hull) if len(e_hull) > 0 else 0

    # False kill rate (the critical metric — missing a stable material)
    false_kill_rate = fn / (tp + fn) if (tp + fn) > 0 else 0

    return {
        'n_materials': len(results),
        'spearman_rho': float(spearman_rho),
        'spearman_p': float(spearman_p),
        'pearson_r': float(pearson_r),
        'pearson_p': float(pearson_p),
        'kendall_tau': float(kendall_tau),
        'kendall_p': float(kendall_p),
        'triage_accuracy': float(accuracy),
        'triage_precision': float(precision),
        'triage_recall': float(recall),
        'false_kill_rate': float(false_kill_rate),
        'n_stable': int(np.sum(is_stable)),
        'n_unstable': int(np.sum(~is_stable)),
        'e_hull_range': [float(e_hull.min()), float(e_hull.max())],
        'dsf_score_range': [float(dsf_score.min()), float(dsf_score.max())],
    }


def evaluate_loco(results: List[Dict]) -> Dict[str, Any]:
    """
    Leave-One-Cluster-Out evaluation by crystal system.

    This is the test CathodeX FAILS (Spearman = -0.024).
    We split by crystal_system — each split holds out one
    structural family and tests on it.
    """
    # Group by crystal system
    families = {}
    for r in results:
        cs = r.get('crystal_system', 'unknown')
        if cs not in families:
            families[cs] = []
        families[cs].append(r)

    print(f"\n  Crystal system families: {len(families)}")
    for cs, members in sorted(families.items(), key=lambda x: -len(x[1])):
        print(f"    {cs}: {len(members)} materials")

    # LOCO: for each family, train on everything else, test on this family
    loco_results = []
    for held_out_cs, held_out in families.items():
        if len(held_out) < 5:
            continue

        # "Training" set: everything except held-out family
        train = [r for r in results if r.get('crystal_system') != held_out_cs]
        if len(train) < 10:
            continue

        # For DSF-AI: there IS no training. The kernel runs identically
        # on every material. But we evaluate only on the held-out set.
        e_hull = np.array([r['e_hull'] for r in held_out])
        dsf_score = np.array([r['dsf_stability_score'] for r in held_out])

        if len(set(e_hull)) < 3 or len(set(dsf_score)) < 3:
            continue

        rho, p = stats.spearmanr(e_hull, dsf_score)

        loco_results.append({
            'crystal_system': held_out_cs,
            'n_held_out': len(held_out),
            'n_train': len(train),
            'spearman_rho': float(rho),
            'spearman_p': float(p),
        })

        print(f"    LOCO {held_out_cs}: rho={rho:.4f} (p={p:.4f}), n={len(held_out)}")

    # Aggregate LOCO
    if loco_results:
        mean_rho = np.mean([r['spearman_rho'] for r in loco_results])
        weighted_rho = np.average(
            [r['spearman_rho'] for r in loco_results],
            weights=[r['n_held_out'] for r in loco_results]
        )
    else:
        mean_rho = 0.0
        weighted_rho = 0.0

    return {
        'n_families': len(families),
        'n_evaluated': len(loco_results),
        'per_family': loco_results,
        'mean_spearman': float(mean_rho),
        'weighted_spearman': float(weighted_rho),
    }


# ============================================================
# STAGE 5: INDIVIDUAL DSF FIELD CORRELATIONS
# ============================================================

def evaluate_field_correlations(results: List[Dict]) -> Dict[str, Dict]:
    """
    Check which DSF fields individually correlate with E_hull.
    This tells us WHAT the kernel sees in crystal structures.
    """
    e_hull = np.array([r['e_hull'] for r in results])
    fields = ['coupling_strength', 'momentum_weight', 'uncertainty',
              'breathing_magnitude', 'pressure', 'complexity', 'reversal_rate']

    correlations = {}
    for field in fields:
        values = np.array([r['dsf_profile'][field] for r in results])
        if len(set(values)) < 3:
            continue
        rho, p = stats.spearmanr(e_hull, values)
        correlations[field] = {
            'spearman_rho': float(rho),
            'spearman_p': float(p),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
        }

    return correlations


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="DSF-AI Cathode Material Screening Test")
    parser.add_argument('--api-key', type=str, default=None,
                        help='Materials Project API key')
    parser.add_argument('--max-materials', type=int, default=300,
                        help='Maximum materials to fetch')
    parser.add_argument('--signal', type=str, default='rdf',
                        choices=['rdf', 'xrd', 'both'],
                        help='Signal type to extract from structures')
    parser.add_argument('--output', type=str, default='tools/cathode_screen_results.json',
                        help='Output file for results')
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get('MP_API_KEY')
    if not api_key:
        print("ERROR: Materials Project API key required.")
        print("  Set MP_API_KEY environment variable or use --api-key")
        print("  Get a free key at https://materialsproject.org/api")
        sys.exit(1)

    print("=" * 60)
    print("DSF-AI CATHODE MATERIAL SCREENING TEST")
    print("=" * 60)
    print(f"Signal type: {args.signal}")
    print(f"Max materials: {args.max_materials}")
    print(f"Kernel: UF-Core L0→L1→L2→L3→L4 (unchanged)")
    print(f"Training: NONE")
    print()

    # 1. Fetch materials
    materials = fetch_cathode_materials(api_key, max_materials=args.max_materials)
    if not materials:
        print("ERROR: No materials fetched.")
        sys.exit(1)

    # 2. Process each material
    results = []
    n_failed = 0

    for i, mat in enumerate(materials):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"\nProcessing {i+1}/{len(materials)}: {mat['formula']} ({mat['material_id']})")

        structure = mat['structure']

        # Extract signal(s)
        profiles_for_mat = []

        if args.signal in ('rdf', 'both'):
            r_bins, g_r = compute_rdf(structure)
            profile = run_dsf_on_signal(g_r, "rdf")
            if profile:
                profiles_for_mat.append(('rdf', profile))

        if args.signal in ('xrd', 'both'):
            try:
                two_theta, intensity = compute_xrd_signal(structure)
                profile = run_dsf_on_signal(intensity, "xrd")
                if profile:
                    profiles_for_mat.append(('xrd', profile))
            except Exception:
                pass

        if not profiles_for_mat:
            n_failed += 1
            continue

        # Use primary signal profile (or average if both)
        if len(profiles_for_mat) == 1:
            signal_type, profile = profiles_for_mat[0]
        else:
            # Average profiles from both signals
            profile = {}
            for key in profiles_for_mat[0][1]:
                if key == 'n_gates':
                    profile[key] = sum(p[1][key] for p in profiles_for_mat)
                else:
                    profile[key] = np.mean([p[1][key] for p in profiles_for_mat])
            signal_type = 'both'

        stability_score = compute_stability_score(profile)

        results.append({
            'material_id': mat['material_id'],
            'formula': mat['formula'],
            'e_hull': mat['e_hull'],
            'formation_energy': mat['formation_energy'],
            'band_gap': mat['band_gap'],
            'density': mat['density'],
            'nsites': mat['nsites'],
            'spacegroup': mat['spacegroup'],
            'crystal_system': mat['crystal_system'],
            'signal_type': signal_type,
            'dsf_profile': profile,
            'dsf_stability_score': stability_score,
        })

    print(f"\n{'=' * 60}")
    print(f"RESULTS")
    print(f"{'=' * 60}")
    print(f"Materials processed: {len(results)}")
    print(f"Materials failed:    {n_failed}")

    if len(results) < 10:
        print("ERROR: Not enough materials processed for evaluation.")
        sys.exit(1)

    # 3. Overall correlation
    print(f"\n--- OVERALL CORRELATION ---")
    overall = evaluate_correlation(materials, results)
    print(f"  Spearman rho:      {overall['spearman_rho']:.4f}  (p={overall['spearman_p']:.2e})")
    print(f"  Pearson r:         {overall['pearson_r']:.4f}  (p={overall['pearson_p']:.2e})")
    print(f"  Kendall tau:       {overall['kendall_tau']:.4f}  (p={overall['kendall_p']:.2e})")
    print(f"  Triage accuracy:   {overall['triage_accuracy']:.4f}")
    print(f"  Triage precision:  {overall['triage_precision']:.4f}")
    print(f"  Triage recall:     {overall['triage_recall']:.4f}")
    print(f"  False kill rate:   {overall['false_kill_rate']:.4f}")
    print(f"  Stable: {overall['n_stable']}, Unstable: {overall['n_unstable']}")

    # CathodeX comparison
    print(f"\n--- vs CathodeX ---")
    print(f"  CathodeX overall Spearman:  0.663")
    print(f"  DSF-AI overall Spearman:    {overall['spearman_rho']:.4f}")
    print(f"  CathodeX LOCO Spearman:     -0.024  (FAILS on novel structures)")

    # 4. LOCO evaluation
    print(f"\n--- LOCO (Leave-One-Crystal-System-Out) ---")
    loco = evaluate_loco(results)
    print(f"  DSF-AI LOCO mean Spearman:      {loco['mean_spearman']:.4f}")
    print(f"  DSF-AI LOCO weighted Spearman:   {loco['weighted_spearman']:.4f}")
    print(f"  CathodeX LOCO Spearman:          -0.024")

    # 5. Per-field correlations
    print(f"\n--- DSF FIELD CORRELATIONS WITH E_HULL ---")
    field_corr = evaluate_field_correlations(results)
    for field, corr in sorted(field_corr.items(), key=lambda x: abs(x[1]['spearman_rho']), reverse=True):
        rho = corr['spearman_rho']
        direction = "↑ unstable" if rho > 0 else "↓ stable"
        sig = "***" if corr['spearman_p'] < 0.001 else "**" if corr['spearman_p'] < 0.01 else "*" if corr['spearman_p'] < 0.05 else "ns"
        print(f"  {field:25s}: rho={rho:+.4f} {sig:4s} ({direction})")

    # 6. Top predictions
    print(f"\n--- TOP 10 MOST STABLE (by DSF score) ---")
    sorted_results = sorted(results, key=lambda r: r['dsf_stability_score'])
    for r in sorted_results[:10]:
        marker = "✓" if r['e_hull'] < 0.05 else "✗"
        print(f"  {marker} {r['formula']:20s} DSF={r['dsf_stability_score']:.4f}  E_hull={r['e_hull']:.4f} eV  ({r['spacegroup']})")

    print(f"\n--- TOP 10 LEAST STABLE (by DSF score) ---")
    for r in sorted_results[-10:]:
        marker = "✓" if r['e_hull'] >= 0.05 else "✗"
        print(f"  {marker} {r['formula']:20s} DSF={r['dsf_stability_score']:.4f}  E_hull={r['e_hull']:.4f} eV  ({r['spacegroup']})")

    # 7. Save results
    output = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'signal_type': args.signal,
            'max_materials': args.max_materials,
            'kernel': 'UF-Core L0-L4 (unchanged, no training)',
        },
        'overall': overall,
        'loco': loco,
        'field_correlations': field_corr,
        'materials': [
            {k: v for k, v in r.items() if k != 'dsf_profile'}
            for r in results
        ],
        'dsf_profiles': {
            r['material_id']: r['dsf_profile'] for r in results
        },
    }

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        args.output
    )
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nResults saved to: {output_path}")

    # 8. Verdict
    print(f"\n{'=' * 60}")
    print("VERDICT")
    print(f"{'=' * 60}")
    if overall['spearman_rho'] > 0.3:
        print("STRONG: DSF-AI kernel sees thermodynamic stability in crystal RDFs.")
        print("The coupling profile correlates with E_hull. No training. No ML.")
    elif overall['spearman_rho'] > 0.15:
        print("MODERATE: DSF-AI kernel detects partial structural signal.")
        print("Correlation exists but may need signal refinement (XRD, combined).")
    elif overall['spearman_rho'] > 0.05:
        print("WEAK: Marginal correlation. The kernel sees something but not enough.")
        print("Try: XRD signal, combined signals, or element-aware RDF.")
    else:
        print("NO SIGNAL: DSF-AI kernel does not correlate with E_hull on this signal.")
        print("RDF alone may not carry enough thermodynamic information.")
        print("This is an honest result. Try element-specific partial RDFs next.")

    if loco['mean_spearman'] > 0.0:
        print(f"\nLOCO: DSF-AI ({loco['mean_spearman']:.4f}) beats CathodeX (-0.024) on novel structures.")
    else:
        print(f"\nLOCO: DSF-AI also struggles on novel structures ({loco['mean_spearman']:.4f}).")


if __name__ == '__main__':
    main()
