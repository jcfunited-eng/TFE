"""
Hoang Relativistic Cross-Term Analysis
=========================================
The relativistic correction ε involves electron velocity.
In a rotating superconductor, the relevant velocity is
v_F (Fermi velocity) + ωr (rotation), not just ωr alone.

The cross term 2·v_F·ωr carries material dependence through
v_F, which is renormalized by λ_ep.

Does this hide the UFCP correction?
"""

import math
import numpy as np

alpha_em = 1/137.036
c = 2.998e8
m_e = 9.109e-31
hbar = 1.055e-34
e_charge = 1.602e-19

print("=" * 70)
print("RELATIVISTIC CROSS-TERM ANALYSIS")
print("=" * 70)

# Fermi velocities and electron-phonon coupling
# v_F values from published band structure calculations
materials = {
    "Nb": {"Z": 41, "m_hoang_ppm": 10, "err_ppm": 2.1, "lambda_ep": 1.26,
            "v_F": 1.37e6, "E_F_eV": 5.32, "m_band": 1.0},
    "Sn": {"Z": 50, "m_hoang_ppm": 30, "err_ppm": 2.2, "lambda_ep": 0.72,
            "v_F": 1.90e6, "E_F_eV": 10.2, "m_band": 1.0},
    "In": {"Z": 49, "m_hoang_ppm": 60, "err_ppm": 2.3, "lambda_ep": 0.81,
            "v_F": 1.74e6, "E_F_eV": 8.63, "m_band": 1.0},
    "Al": {"Z": 13, "m_hoang_ppm": 70, "err_ppm": 1.0, "lambda_ep": 0.43,
            "v_F": 2.03e6, "E_F_eV": 11.7, "m_band": 1.0},
    "Cd": {"Z": 48, "m_hoang_ppm": 80, "err_ppm": 3.1, "lambda_ep": 0.38,
            "v_F": 1.62e6, "E_F_eV": 7.47, "m_band": 1.0},
    "Pb": {"Z": 82, "m_hoang_ppm": 100, "err_ppm": 4.1, "lambda_ep": 1.55,
            "v_F": 1.83e6, "E_F_eV": 9.47, "m_band": 1.0},
}

omega = 2000  # rad/s (from paper)
r = 0.02  # radius in meters (quartz core)
v_rot = omega * r  # rotation velocity

print(f"\nRotation: ω={omega} rad/s, r={r*100} cm, v_rot={v_rot} m/s")
print(f"v_rot/c = {v_rot/c:.2e}")

print(f"\n{'='*70}")
print("RELATIVISTIC CORRECTIONS: BARE vs RENORMALIZED v_F")
print(f"{'='*70}\n")

# The relativistic correction to the London moment:
# ε = v²/c² where v is the relevant electron velocity
#
# Standard (what Hoang probably used):
# ε = (ωr)²/c² ← just rotation velocity
# This gives ε ~ 10⁻¹⁴ (negligible for all materials)
# But Table 1 shows 65 ppm for Al — that's NOT from (ωr)²/c²
#
# So Hoang must be using a DIFFERENT relativistic correction.
# From refs [9-11]: the CPM deviation from 2m_e is due to
# "large velocity and kinetic energy" (from the paper intro)
#
# The relativistic CPM correction from special relativity:
# m* = 2m_e × (1 + v_F²/c²/2 + ...) for electrons at v_F
# Or more precisely from the band structure: m* includes
# relativistic mass enhancement from the electron's velocity

# Bare relativistic correction (no e-ph renormalization):
# ε_bare = E_F / (m_e c²) = v_F² / (2c²)
# This is the kinetic energy fraction of rest mass energy

print(f"{'Mat':>3} | {'v_F (m/s)':>10} | {'v_F/c':>8} | {'ε_bare ppm':>10} | {'ε_renorm ppm':>12} | {'Δε ppm':>8} | {'Hoang ppm':>9}")
print(f"{'-'*3}-+-{'-'*10}-+-{'-'*8}-+-{'-'*10}-+-{'-'*12}-+-{'-'*8}-+-{'-'*9}")

results = {}
for name, d in materials.items():
    v_F = d["v_F"]
    lep = d["lambda_ep"]

    # Bare relativistic correction
    eps_bare = (v_F / c)**2 / 2  # v_F²/(2c²)
    eps_bare_ppm = eps_bare * 1e6

    # Renormalized Fermi velocity: v_F* = v_F / (1 + λ_ep)
    v_F_renorm = v_F / (1 + lep)
    eps_renorm = (v_F_renorm / c)**2 / 2
    eps_renorm_ppm = eps_renorm * 1e6

    # The DIFFERENCE is what gets mis-corrected if Hoang uses
    # bare v_F instead of renormalized v_F
    delta_eps = eps_bare_ppm - eps_renorm_ppm

    # Cross term with rotation:
    # (v_F + ωr)² ≈ v_F² + 2·v_F·ωr
    # The cross term: 2·v_F·ωr / c²
    cross_term = 2 * v_F * v_rot / c**2 * 1e6

    results[name] = {
        "eps_bare_ppm": eps_bare_ppm,
        "eps_renorm_ppm": eps_renorm_ppm,
        "delta_eps_ppm": delta_eps,
        "cross_term_ppm": cross_term,
    }

    print(f"{name:>3} | {v_F:>10.2e} | {v_F/c:>8.5f} | {eps_bare_ppm:>9.1f}  | {eps_renorm_ppm:>11.1f}  | {delta_eps:>7.1f}  | {d['m_hoang_ppm']:>8}")

print(f"\n{'='*70}")
print("KEY INSIGHT: Δε = ε_bare - ε_renorm")
print(f"{'='*70}\n")

print("""
If Hoang applied the BARE relativistic correction (using v_F
without electron-phonon renormalization), they OVER-corrected
by Δε. The measured anomaly INCLUDES Δε as a systematic.

The TRUE anomaly = Hoang measured + Δε (since they subtracted
too much).

OR: if Hoang applied the RENORMALIZED correction, their
measured values are the true anomalies.

The 65 ppm for Al in Table 1 — let's check:
""")

al = materials["Al"]
print(f"Al bare relativistic correction: {results['Al']['eps_bare_ppm']:.1f} ppm")
print(f"Al renormalized correction:      {results['Al']['eps_renorm_ppm']:.1f} ppm")
print(f"Table 1 says:                     65 ppm")
print()

# Check which one matches 65 ppm
if abs(results["Al"]["eps_bare_ppm"] - 65) < 10:
    print("*** The 65 ppm matches the BARE correction! ***")
    print("This means Hoang used BARE v_F (no e-ph renormalization)")
    correction_type = "bare"
elif abs(results["Al"]["eps_renorm_ppm"] - 65) < 10:
    print("*** The 65 ppm matches the RENORMALIZED correction! ***")
    correction_type = "renormalized"
else:
    print(f"Neither matches 65 ppm. The correction may come from a")
    print(f"different formula than v_F²/(2c²).")
    correction_type = "unknown"

    # Try E_F / (2 m_e c²) directly
    E_F_J = al["E_F_eV"] * e_charge
    eps_EF = E_F_J / (2 * m_e * c**2) * 1e6
    print(f"\nTrying E_F/(2·m_e·c²): {eps_EF:.1f} ppm")
    if abs(eps_EF - 65) < 10:
        print("*** MATCHES! The relativistic correction is E_F/(2·m_e·c²) ***")
        correction_type = "E_F"

# ==============================================================
# Recompute for all materials with the correct formula
# ==============================================================
print(f"\n{'='*70}")
print("RELATIVISTIC CORRECTION FOR ALL MATERIALS")
print(f"{'='*70}\n")

if correction_type == "E_F":
    print("Using ε = E_F / (2·m_e·c²):")
else:
    print(f"Using correction type: {correction_type}")

print(f"\n{'Mat':>3} | {'E_F eV':>6} | {'ε_std ppm':>9} | {'ε_renorm ppm':>12} | {'Δε':>5} | {'Hoang':>5} | {'Hoang+Δε':>8} | {'UFCP':>6}")
print(f"{'-'*3}-+-{'-'*6}-+-{'-'*9}-+-{'-'*12}-+-{'-'*5}-+-{'-'*5}-+-{'-'*8}-+-{'-'*6}")

for name, d in materials.items():
    E_F_eV = d["E_F_eV"]
    E_F_J = E_F_eV * e_charge
    lep = d["lambda_ep"]

    # Standard (bare) relativistic correction
    eps_std = E_F_J / (2 * m_e * c**2) * 1e6

    # Renormalized: E_F* = E_F / (1+λ_ep)²
    # because E_F = m_e v_F² / 2, and v_F* = v_F/(1+λ_ep)
    E_F_renorm = E_F_eV / (1 + lep)**2
    eps_renorm = E_F_renorm * e_charge / (2 * m_e * c**2) * 1e6

    delta_eps = eps_std - eps_renorm

    # If Hoang subtracted eps_std but should have subtracted eps_renorm:
    # true_anomaly = hoang_measured + delta_eps
    hoang_corrected = d["m_hoang_ppm"] + delta_eps

    ufcp = alpha_em**2 * lep**2 * 1e6

    print(f"{name:>3} | {E_F_eV:>5.1f}  | {eps_std:>8.1f}  | {eps_renorm:>11.1f}  | {delta_eps:>4.0f}  | {d['m_hoang_ppm']:>4}  | {hoang_corrected:>7.1f}  | {ufcp:>5.1f}")

# ==============================================================
# DOES THE CORRECTED DATA MATCH UFCP?
# ==============================================================
print(f"\n{'='*70}")
print("CORRECTED HOANG DATA vs UFCP PREDICTION")
print(f"{'='*70}\n")

print(f"{'Mat':>3} | {'Hoang+Δε':>8} | {'UFCP':>6} | {'Δ':>6} | {'σ':>5}")
print(f"{'-'*3}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}-+-{'-'*5}")

all_within_3sigma = True
for name, d in materials.items():
    E_F_eV = d["E_F_eV"]
    lep = d["lambda_ep"]

    eps_std = E_F_eV * e_charge / (2 * m_e * c**2) * 1e6
    eps_renorm = (E_F_eV / (1+lep)**2) * e_charge / (2 * m_e * c**2) * 1e6
    delta_eps = eps_std - eps_renorm

    corrected = d["m_hoang_ppm"] + delta_eps
    ufcp = alpha_em**2 * lep**2 * 1e6
    diff = corrected - ufcp
    sigma = abs(diff) / d["err_ppm"]

    if sigma > 3:
        all_within_3sigma = False

    match = "✓" if sigma < 3 else "✗"
    print(f"{name:>3} | {corrected:>7.1f}  | {ufcp:>5.1f}  | {diff:>+5.0f}  | {sigma:>4.1f} {match}")

print(f"\n{'='*70}")
if all_within_3sigma:
    print("*** ALL MATERIALS WITHIN 3σ ***")
    print("The Hoang data is CONSISTENT with UFCP after correcting")
    print("for the e-ph renormalization of the relativistic term.")
    print("UFCP SURVIVES.")
else:
    print("Some materials outside 3σ. Check the correction model.")
print(f"{'='*70}")
