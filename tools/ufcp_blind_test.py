#!/usr/bin/env python3
"""
UFCP BLIND TEST ENGINE
======================
Generate predictions for every cluster we can, THEN compare to experiment.
The predictions are written BEFORE looking at the experimental values.

Extends the 13-atom framework to:
  - All icosahedral magic numbers (13, 55, 147, 309, 561)
  - Non-magic sizes using interpolated geometry
  - Multiple properties: moment, IP, EA, gap
  - Multiple elements: all 3d, 4d, 5d transition metals

TRADE SECRET — DO NOT DISTRIBUTE
"""

import math
import csv
import json

k_B = 8.617e-5
GOLDEN = (1 + math.sqrt(5)) / 2

# ══════════════════════════════════════════════════════════════════
# GEOMETRY ENGINE
# ══════════════════════════════════════════════════════════════════
#
# Icosahedral magic numbers: 13, 55, 147, 309, 561
# At these sizes, the cluster is a perfect Mackay icosahedron.
# Between magic numbers, the cluster is an incomplete shell.
#
# The frustration angle θ = arctan(1/φ) is for a PERFECT icosahedron.
# For an incomplete shell, the effective symmetry is REDUCED.
# This means:
#   - At magic numbers: full Ih symmetry, θ = 31.72°
#   - Between magic numbers: reduced symmetry, effective θ varies
#   - At half-shell filling: maximum frustration (θ peaks)
#   - The curve is NOT smooth — specific "sub-magic" numbers exist

MAGIC_NUMBERS = {
    1: 13,    # 1-shell icosahedron
    2: 55,    # 2-shell
    3: 147,   # 3-shell
    4: 309,   # 4-shell
    5: 561,   # 5-shell
}

# Sub-shell magic numbers (completed geometric sub-shells within a Mackay shell)
# Between 13 and 55: vertices(19), edge-centers(23), face-centers(43), then 55
# Between 55 and 147: similar progression

THETA_ICO = math.atan(1.0 / GOLDEN)  # 31.72° — the universal angle

def effective_theta(N):
    """
    Effective frustration angle for cluster of N atoms.

    At magic numbers: θ = arctan(1/φ) (full icosahedral)
    Between magic numbers: θ varies based on shell completion

    The key insight: an incomplete shell has LOWER symmetry than Ih.
    Lower symmetry means LESS geometric frustration (fewer 5-fold axes active).
    So θ_eff < θ_ico between magic numbers.

    Approximation: θ_eff = θ_ico × f_shell
    where f_shell = fraction of current shell that is complete.
    At magic numbers f=1, between them f<1.
    """
    # Find which shell we're in
    if N <= 1:
        return 0  # single atom, no frustration

    prev_magic = 1  # atom count at previous complete shell
    prev_n = 0
    for n_shell in range(1, 6):
        magic = MAGIC_NUMBERS[n_shell]
        if N <= magic:
            # We're filling shell n_shell
            shell_atoms = magic - prev_magic  # total atoms in this shell
            filled = N - prev_magic  # how many we've placed
            f_shell = filled / shell_atoms

            # At f=0 (just completed previous shell): θ = θ_ico (previous shell complete)
            # At f=0.5: θ minimum (most disordered, least symmetric)
            # At f=1: θ = θ_ico (new shell complete)
            # Model as: θ_eff = θ_ico × (1 - 0.3 × sin(π × f_shell))
            # The 0.3 factor: incomplete shell reduces effective frustration by up to 30%
            theta_eff = THETA_ICO * (1 - 0.3 * math.sin(math.pi * f_shell))
            return theta_eff
        prev_magic = magic

    # Beyond 561: approaching bulk, frustration dies as 1/N^(1/3)
    return THETA_ICO * (561 / N) ** (1.0/3.0)


def n_shell_for_N(N):
    """Which shell is this cluster filling?"""
    for n in range(1, 6):
        if N <= MAGIC_NUMBERS[n]:
            return n
    return 5 + int((N - 561) ** (1.0/3.0))


# ══════════════════════════════════════════════════════════════════
# ELEMENT DATABASE
# ══════════════════════════════════════════════════════════════════

ELEMENTS = {
    # 3d metals
    'Sc': {'Z': 3,  'd': 1, 'Ef': 5.00, 'W': 3.50, 'r_at': 1.62, 'r_s': 1.71, 'lam': 0.010, 'I': 0.50, 'mu_bulk': 0.0,   'zeta': 0.02, 'rel': 0.99, 'row': 3},
    'Ti': {'Z': 4,  'd': 2, 'Ef': 5.15, 'W': 4.33, 'r_at': 1.47, 'r_s': 1.52, 'lam': 0.019, 'I': 0.56, 'mu_bulk': 0.0,   'zeta': 0.02, 'rel': 0.99, 'row': 3},
    'V':  {'Z': 5,  'd': 3, 'Ef': 5.25, 'W': 4.30, 'r_at': 1.34, 'r_s': 1.41, 'lam': 0.028, 'I': 0.62, 'mu_bulk': 0.0,   'zeta': 0.02, 'rel': 0.99, 'row': 3},
    'Cr': {'Z': 6,  'd': 5, 'Ef': 5.30, 'W': 4.50, 'r_at': 1.28, 'r_s': 1.35, 'lam': 0.037, 'I': 0.76, 'mu_bulk': 0.0,   'zeta': 0.03, 'rel': 0.99, 'row': 3},
    'Mn': {'Z': 7,  'd': 5, 'Ef': 5.35, 'W': 4.10, 'r_at': 1.27, 'r_s': 1.37, 'lam': 0.043, 'I': 0.82, 'mu_bulk': 0.0,   'zeta': 0.04, 'rel': 0.99, 'row': 3},
    'Fe': {'Z': 8,  'd': 6, 'Ef': 5.45, 'W': 4.50, 'r_at': 1.26, 'r_s': 1.36, 'lam': 0.057, 'I': 0.93, 'mu_bulk': 2.22,  'zeta': 0.05, 'rel': 0.99, 'row': 3},
    'Co': {'Z': 9,  'd': 7, 'Ef': 5.50, 'W': 5.00, 'r_at': 1.25, 'r_s': 1.32, 'lam': 0.073, 'I': 0.99, 'mu_bulk': 1.72,  'zeta': 0.06, 'rel': 0.99, 'row': 3},
    'Ni': {'Z': 10, 'd': 8, 'Ef': 5.55, 'W': 5.15, 'r_at': 1.24, 'r_s': 1.37, 'lam': 0.097, 'I': 1.01, 'mu_bulk': 0.60,  'zeta': 0.04, 'rel': 0.98, 'row': 3},
    'Cu': {'Z': 11, 'd': 10,'Ef': 7.00, 'W': 4.65, 'r_at': 1.28, 'r_s': 1.41, 'lam': 0.000, 'I': 0.00, 'mu_bulk': 0.0,   'zeta': 0.03, 'rel': 0.98, 'row': 3},

    # 4d metals
    'Nb': {'Z': 5,  'd': 4, 'Ef': 5.25, 'W': 4.30, 'r_at': 1.46, 'r_s': 1.56, 'lam': 0.035, 'I': 0.55, 'mu_bulk': 0.0,   'zeta': 0.08, 'rel': 0.95, 'row': 4},
    'Mo': {'Z': 6,  'd': 5, 'Ef': 5.30, 'W': 4.60, 'r_at': 1.39, 'r_s': 1.47, 'lam': 0.045, 'I': 0.60, 'mu_bulk': 0.0,   'zeta': 0.10, 'rel': 0.95, 'row': 4},
    'Rh': {'Z': 9,  'd': 8, 'Ef': 5.40, 'W': 4.98, 'r_at': 1.34, 'r_s': 1.41, 'lam': 0.090, 'I': 0.80, 'mu_bulk': 0.0,   'zeta': 0.15, 'rel': 0.94, 'row': 4},
    'Pd': {'Z': 10, 'd': 10,'Ef': 5.42, 'W': 5.12, 'r_at': 1.37, 'r_s': 1.52, 'lam': 0.000, 'I': 0.00, 'mu_bulk': 0.0,   'zeta': 0.12, 'rel': 0.93, 'row': 4},
    'Ag': {'Z': 11, 'd': 10,'Ef': 5.49, 'W': 4.26, 'r_at': 1.44, 'r_s': 1.60, 'lam': 0.000, 'I': 0.00, 'mu_bulk': 0.0,   'zeta': 0.10, 'rel': 0.93, 'row': 4},

    # 5d metals
    'Ta': {'Z': 5,  'd': 3, 'Ef': 5.30, 'W': 4.25, 'r_at': 1.46, 'r_s': 1.56, 'lam': 0.060, 'I': 0.50, 'mu_bulk': 0.0,   'zeta': 0.30, 'rel': 0.75, 'row': 5},
    'W':  {'Z': 6,  'd': 4, 'Ef': 5.40, 'W': 4.55, 'r_at': 1.39, 'r_s': 1.47, 'lam': 0.070, 'I': 0.55, 'mu_bulk': 0.0,   'zeta': 0.35, 'rel': 0.73, 'row': 5},
    'Ir': {'Z': 9,  'd': 7, 'Ef': 5.55, 'W': 5.27, 'r_at': 1.36, 'r_s': 1.42, 'lam': 0.110, 'I': 0.75, 'mu_bulk': 0.0,   'zeta': 0.45, 'rel': 0.71, 'row': 5},
    'Pt': {'Z': 10, 'd': 9, 'Ef': 5.64, 'W': 5.65, 'r_at': 1.39, 'r_s': 1.53, 'lam': 0.130, 'I': 0.80, 'mu_bulk': 0.0,   'zeta': 0.53, 'rel': 0.72, 'row': 5},
    'Au': {'Z': 11, 'd': 10,'Ef': 5.53, 'W': 5.10, 'r_at': 1.44, 'r_s': 1.59, 'lam': 0.000, 'I': 0.00, 'mu_bulk': 0.0,   'zeta': 0.58, 'rel': 0.70, 'row': 5},
}


# ══════════════════════════════════════════════════════════════════
# PREDICTION FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def predict_moment(elem_name, N):
    """
    Magnetic moment for any d-metal cluster of size N.

    μ = μ_sat × (d-1)/(d+2) × pair_correction × size_correction

    size_correction: for N >> 13, moment approaches bulk as geometry relaxes.
    At N=13 (perfect icosahedron): full geometric enhancement.
    At N→∞: bulk moment.

    The transition between cluster and bulk follows the shell structure:
    μ(N) = μ_bulk + (μ_cluster - μ_bulk) × g(N)
    where g(N) = surface_fraction × geometric_factor

    surface_fraction = (N^(2/3)) / N = N^(-1/3)  (surface atoms / total)
    geometric_factor = effective_theta(N) / theta_ico
    """
    e = ELEMENTS[elem_name]
    d = e['d']
    lam = e['lam']
    I = e['I']
    mu_bulk = e['mu_bulk']

    if I == 0:  # non-magnetic (d10 metals)
        return {'element': elem_name, 'N': N, 'mu': 0.0, 'type': 'non-magnetic'}

    # Saturation moment
    if d > 5:
        mu_sat = 10 - d
        n_holes = 10 - d
    else:
        mu_sat = d
        n_holes = 0  # for d ≤ 5, no hole pairing

    # Exchange fraction (combinatoric, size-independent)
    exchange_frac = (d - 1) / (d + 2)

    # Pair correction (only for n_holes = 2, i.e., Ni-like)
    theta = effective_theta(N)
    sin2 = math.sin(theta) ** 2
    if n_holes == 2 and sin2 > 0:
        pair_strength = (lam / I) / sin2
        pair_correction = max(0, 1 - pair_strength)
    else:
        pair_correction = 1.0

    # Cluster moment at this geometry
    mu_cluster = mu_sat * exchange_frac * pair_correction

    # Size scaling: interpolate between cluster limit and bulk
    # Surface fraction gives weight of geometric (cluster) behavior
    surface_frac = N ** (-1.0/3.0)  # fraction of atoms on surface
    # At N=13: surface_frac = 0.425 (12/13 are surface, but N^{-1/3} = 0.425)
    # Normalize so that N=13 gives full cluster behavior
    surface_frac_13 = 13 ** (-1.0/3.0)
    geo_weight = min(1.0, surface_frac / surface_frac_13)

    # Geometric factor: how icosahedral is this cluster?
    geo_factor = theta / THETA_ICO if THETA_ICO > 0 else 0

    # Combined
    cluster_weight = geo_weight * geo_factor
    mu = mu_bulk + (mu_cluster - mu_bulk) * cluster_weight

    return {
        'element': elem_name,
        'N': N,
        'mu': mu,
        'mu_cluster': mu_cluster,
        'mu_bulk': mu_bulk,
        'cluster_weight': cluster_weight,
        'theta_eff': math.degrees(theta),
        'type': 'magnetic',
    }


def predict_IP(elem_name, N):
    """
    Ionization potential for a cluster of N atoms.

    IP = W + (3/8)(e²/R_eff)×(1 + 1/(2N)) - kubo_correction

    (Opposite sign from EA: removing an electron costs MORE from a small cluster
    because the remaining positive charge is poorly screened)
    """
    e = ELEMENTS[elem_name]
    W = e['W']
    r_at = e['r_at']
    r_s = e['r_s']
    Z = e['Z']
    Ef = e['Ef']

    # Cluster radius scales as N^(1/3)
    R_cluster = 2 * r_at * (N / 13) ** (1.0/3.0)  # scale from 13-atom reference
    R_eff = R_cluster + 0.5 * r_s  # spillout

    E_charge = (3.0 / 8.0) * 14.4 / R_eff
    discrete = 1 + 1.0 / (2 * N)  # for IP: positive correction (costs more)

    delta_kubo = Ef / (Z * N)
    n_elec = Z * N
    kubo_sign = -0.5 if (n_elec % 2 == 1) else +0.5  # opposite from EA

    IP = W + E_charge * discrete + kubo_sign * delta_kubo

    return {
        'element': elem_name,
        'N': N,
        'IP_eV': IP,
        'W': W,
        'E_charge': E_charge,
        'R_eff': R_eff,
    }


def predict_EA(elem_name, N):
    """
    Electron affinity for cluster of N atoms.
    """
    e = ELEMENTS[elem_name]
    W = e['W']
    r_at = e['r_at']
    r_s = e['r_s']
    Z = e['Z']
    Ef = e['Ef']

    R_cluster = 2 * r_at * (N / 13) ** (1.0/3.0)
    R_eff = R_cluster + 0.5 * r_s

    E_charge = (3.0 / 8.0) * 14.4 / R_eff
    discrete = 1 - 1.0 / (2 * N)

    delta_kubo = Ef / (Z * N)
    n_elec = Z * N
    kubo_sign = +0.5 if (n_elec % 2 == 1) else -0.5

    EA = W - E_charge * discrete + kubo_sign * delta_kubo

    return {
        'element': elem_name,
        'N': N,
        'EA_eV': EA,
        'W': W,
        'E_charge': E_charge,
        'R_eff': R_eff,
    }


# ══════════════════════════════════════════════════════════════════
# GENERATE ALL PREDICTIONS
# ══════════════════════════════════════════════════════════════════

def main():
    # Sizes to predict for: all experimentally relevant sizes
    # Magnetic: typically measured at 12-300 atoms
    # IP/EA: typically measured at 2-100 atoms

    mag_sizes = list(range(10, 51)) + [55, 60, 70, 80, 100, 120, 150, 200, 250, 300, 400, 500, 600, 700]
    ip_ea_sizes = list(range(2, 41)) + [45, 50, 55, 60, 70, 80, 100]

    mag_elements = ['Fe', 'Co', 'Ni', 'Mn', 'Cr', 'V', 'Rh']
    ip_ea_elements = ['Au', 'Ag', 'Cu']

    all_predictions = []

    # Magnetic moments
    for elem in mag_elements:
        for N in mag_sizes:
            r = predict_moment(elem, N)
            all_predictions.append({
                'element': elem,
                'N': N,
                'property': 'magnetic_moment',
                'predicted_value': round(r['mu'], 3),
                'unit': 'μB/atom',
                'theta_eff_deg': round(r.get('theta_eff', 0), 2),
                'cluster_weight': round(r.get('cluster_weight', 0), 4),
            })

    # Ionization potentials
    for elem in ip_ea_elements:
        for N in ip_ea_sizes:
            r = predict_IP(elem, N)
            all_predictions.append({
                'element': elem,
                'N': N,
                'property': 'ionization_potential',
                'predicted_value': round(r['IP_eV'], 3),
                'unit': 'eV',
                'theta_eff_deg': round(math.degrees(effective_theta(N)), 2),
                'cluster_weight': 0,
            })

    # Electron affinities
    for elem in ip_ea_elements:
        for N in ip_ea_sizes:
            r = predict_EA(elem, N)
            all_predictions.append({
                'element': elem,
                'N': N,
                'property': 'electron_affinity',
                'predicted_value': round(r['EA_eV'], 3),
                'unit': 'eV',
                'theta_eff_deg': round(math.degrees(effective_theta(N)), 2),
                'cluster_weight': 0,
            })

    # Write CSV
    csv_path = '/workspaces/Tao_Financial_Engine/tools/ufcp_blind_predictions.csv'
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['element', 'N', 'property', 'predicted_value', 'unit', 'theta_eff_deg', 'cluster_weight'])
        writer.writeheader()
        writer.writerows(all_predictions)

    # Summary
    print("=" * 100)
    print("UFCP BLIND PREDICTIONS — GENERATED BEFORE LOOKING AT DATA")
    print("=" * 100)

    n_mag = sum(1 for p in all_predictions if p['property'] == 'magnetic_moment')
    n_ip = sum(1 for p in all_predictions if p['property'] == 'ionization_potential')
    n_ea = sum(1 for p in all_predictions if p['property'] == 'electron_affinity')

    print(f"\nMagnetic moment predictions: {n_mag}")
    print(f"  Elements: {', '.join(mag_elements)}")
    print(f"  Sizes: {min(mag_sizes)}-{max(mag_sizes)} atoms")

    print(f"\nIonization potential predictions: {n_ip}")
    print(f"  Elements: {', '.join(ip_ea_elements)}")
    print(f"  Sizes: {min(ip_ea_sizes)}-{max(ip_ea_sizes)} atoms")

    print(f"\nElectron affinity predictions: {n_ea}")
    print(f"  Elements: {', '.join(ip_ea_elements)}")
    print(f"  Sizes: {min(ip_ea_sizes)}-{max(ip_ea_sizes)} atoms")

    print(f"\nTOTAL PREDICTIONS: {len(all_predictions)}")
    print(f"Saved to: {csv_path}")

    # Print some key predictions for reference
    print("\n" + "─" * 100)
    print("KEY PREDICTIONS (selected)")
    print("─" * 100)

    print("\nMagnetic moments at icosahedral magic numbers:")
    for elem in ['Fe', 'Co', 'Ni']:
        print(f"\n  {elem}:")
        for N in [13, 55, 147]:
            r = predict_moment(elem, N)
            print(f"    N={N:>3}: μ = {r['mu']:.3f} μB/atom "
                  f"(weight={r.get('cluster_weight',0):.3f}, θ={r.get('theta_eff',0):.1f}°)")

    print("\nMagnetic moments for Mn and Cr (predicted ferromagnetic):")
    for elem in ['Mn', 'Cr']:
        print(f"\n  {elem}:")
        for N in [13, 20, 30, 55]:
            r = predict_moment(elem, N)
            print(f"    N={N:>3}: μ = {r['mu']:.3f} μB/atom")

    print("\nIonization potentials for Au (odd-even oscillation):")
    print("  Au_N:")
    for N in range(2, 21):
        r = predict_IP('Au', N)
        oddeven = "odd " if (11*N) % 2 == 1 else "even"
        print(f"    N={N:>3} ({oddeven}): IP = {r['IP_eV']:.3f} eV")

    print("\nElectron affinities for Au:")
    print("  Au_N:")
    for N in [3, 5, 7, 11, 13, 20, 30, 55]:
        r = predict_EA('Au', N)
        print(f"    N={N:>3}: EA = {r['EA_eV']:.3f} eV")

    print(f"\n{'='*100}")
    print("ALL PREDICTIONS GENERATED. NOW COMPARE TO EXPERIMENTAL DATA.")
    print(f"{'='*100}")


if __name__ == '__main__':
    main()
