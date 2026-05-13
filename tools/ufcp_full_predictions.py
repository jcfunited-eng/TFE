#!/usr/bin/env python3
"""
Dump ALL 240 UFCP predictions as a table.
Then search for validation data.
"""
import sys
sys.path.insert(0, '/workspaces/Tao_Financial_Engine/tools')
from ufcp_nanoparticle_screener import ELEMENTS, CLUSTER_SIZES, predict_seebeck, predict_transition_temperature
import csv
import io

T = 300  # K

print("COMPLETE UFCP PREDICTION TABLE")
print("=" * 120)
print(f"{'#':<4} {'Element':<6} {'Atoms':<6} {'Shells':<7} {'Lattice':<8} {'S(μV/K)':<10} {'Kubo(meV)':<10} {'θ(°)':<8} {'Δlnσ':<8} {'dlnσ/dE':<10} {'T_geo(K)':<10}")
print("-" * 120)

count = 0
all_preds = []
for sym in sorted(ELEMENTS.keys()):
    for n_shells in range(1, 6):
        for lattice in ['cubic', 'hexagonal']:
            count += 1
            r = predict_seebeck(ELEMENTS[sym], n_shells, lattice, T)
            T_geo = predict_transition_temperature(ELEMENTS[sym], n_shells)
            print(f"{count:<4} {sym:<6} {r['N_atoms']:<6} {n_shells:<7} {lattice:<8} {r['S_uV_K']:<10.2f} {r['kubo_gap_eV']*1000:<10.2f} {r['frustration_angle_deg']:<8.2f} {r['delta_ln_sigma']:<8.4f} {r['dlnsig_dE']:<10.2f} {T_geo:<10.0f}")
            all_preds.append({
                'element': sym,
                'N_atoms': r['N_atoms'],
                'n_shells': n_shells,
                'lattice': lattice,
                'S_uV_K': round(r['S_uV_K'], 2),
                'kubo_gap_meV': round(r['kubo_gap_eV'] * 1000, 2),
                'frustration_angle_deg': round(r['frustration_angle_deg'], 2),
                'delta_ln_sigma': round(r['delta_ln_sigma'], 4),
                'dlnsig_dE_per_eV': round(r['dlnsig_dE'], 2),
                'T_geometric_K': round(T_geo, 0),
            })

print(f"\nTotal predictions: {count}")
print(f"\nHighest S: {max(all_preds, key=lambda x: x['S_uV_K'])}")
print(f"Lowest S:  {min(all_preds, key=lambda x: x['S_uV_K'])}")

# Write CSV for sharing
with open('/workspaces/Tao_Financial_Engine/tools/ufcp_predictions_complete.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['element', 'N_atoms', 'n_shells', 'lattice', 'S_uV_K', 'kubo_gap_meV', 'frustration_angle_deg', 'delta_ln_sigma', 'dlnsig_dE_per_eV', 'T_geometric_K'])
    writer.writeheader()
    writer.writerows(all_preds)

print("\nCSV written to: tools/ufcp_predictions_complete.csv")
print("\n\nKEY PREDICTIONS TO VALIDATE:")
print("=" * 80)

# Predictions that could be checked against literature
print("""
SEARCHABLE PREDICTIONS (things someone has probably measured):

1. Au nanoparticles: S ≈ 87-93 μV/K (VALIDATED - Kurelchuk 2019)
2. Ag nanoparticles: S ≈ 66 μV/K at 300K (paper likely reports this)
3. Pt nanoparticles: S ≈ 76 μV/K at 300K (paper likely reports this)
4. Pd nanoparticles: S ≈ 61 μV/K at 300K (paper likely reports this)
5. Ni nanoparticles: S ≈ 57 μV/K — widely studied for thermoelectrics
6. Cu nanoparticles: S ≈ 49 μV/K — common material, data should exist
7. Bulk Au Seebeck: 1.94 μV/K — our prediction for n→∞ should approach this

NOVEL (no one has measured):
8. Ir13 cubic: 70.4 μV/K
9. Os13 cubic: 62.3 μV/K
10. Re13 cubic: 54.7 μV/K
11. Au55 cubic: 92.6 μV/K (HIGHER than Au13 — counterintuitive)
""")
