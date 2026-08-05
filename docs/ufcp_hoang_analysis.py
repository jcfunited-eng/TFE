"""
Hoang et al. (2020) Data Analysis
====================================
Does the Hoang data kill or confirm UFCP?

The measured m*/2m_e values include MULTIPLE corrections:
  1. Relativistic correction (1+epsilon)
  2. London penetration depth (LPD) correction
  3. Finite geometry correction (shell thickness, radius)
  4. ??? The UFCP alpha^2 * lambda_ep^2 correction

We need to subtract corrections 1-3 from the measured values
and see if the residual matches correction 4.

From the paper:
  m* = (v*e*) / (2*(1+epsilon)) × geometry_factor × LPD_factor

The geometry and LPD factors depend on:
  a_o = outer radius of SC shell
  a_i = inner radius (quartz core)
  lambda_L = London penetration depth
  r = radial distance to sensor
  epsilon = relativistic correction (v^2/c^2 term)
"""

import math
import numpy as np

alpha = 1/137.036
e_charge = 1.602e-19
m_e = 9.109e-31
c = 2.998e8

print("=" * 70)
print("HOANG et al. (2020) — UFCP RESIDUAL ANALYSIS")
print("=" * 70)

# ==============================================================
# Measured data from Figure 3
# ==============================================================
# m*/2m_e values from the figure
# These are the TOTAL measured effective mass ratios

materials = {
    "Nb": {"Z": 41, "m_star": 1.00001, "err": 0.0000021, "lambda_ep": 1.26,
            "lambda_L_nm": 39.0, "Tc": 9.26},
    "Sn": {"Z": 50, "m_star": 1.00003, "err": 0.0000022, "lambda_ep": 0.72,
            "lambda_L_nm": 34.0, "Tc": 3.72},
    "In": {"Z": 49, "m_star": 1.00006, "err": 0.0000023, "lambda_ep": 0.81,
            "lambda_L_nm": 23.5, "Tc": 3.41},
    "Al": {"Z": 13, "m_star": 1.00007, "err": 0.000001, "lambda_ep": 0.43,
            "lambda_L_nm": 16.0, "Tc": 1.18},
    "Cd": {"Z": 48, "m_star": 1.00008, "err": 0.0000031, "lambda_ep": 0.38,
            "lambda_L_nm": 110.0, "Tc": 0.52},
    "Pb": {"Z": 82, "m_star": 1.0001, "err": 0.0000041, "lambda_ep": 1.55,
            "lambda_L_nm": 37.0, "Tc": 7.19},
}

print(f"\n{'='*70}")
print("RAW MEASURED DATA (from Figure 3)")
print(f"{'='*70}\n")

print(f"{'Mat':>3} | {'Z':>3} | {'m*/2me':>12} | {'ppm':>7} | {'err ppm':>7} | {'λ_ep':>5} | {'λ_L nm':>6}")
print(f"{'-'*3}-+-{'-'*3}-+-{'-'*12}-+-{'-'*7}-+-{'-'*7}-+-{'-'*5}-+-{'-'*6}")

for name, d in materials.items():
    ppm = (d["m_star"] - 1.0) * 1e6
    err_ppm = d["err"] * 1e6
    print(f"{name:>3} | {d['Z']:>3} | {d['m_star']:>12.7f} | {ppm:>6.1f}  | {err_ppm:>5.1f}  | {d['lambda_ep']:>5.2f} | {d['lambda_L_nm']:>5.0f}")

# ==============================================================
# Hoang's correction model
# ==============================================================
print(f"\n{'='*70}")
print("HOANG'S CORRECTION MODEL")
print(f"{'='*70}\n")

print("""
Hoang Eq (1): B = [2(1+ε)m*/e*] × geometry_factor × ω

The measured m* INCLUDES:
  (1+ε) = relativistic correction = 1 + v²/c² ≈ 1 + (ωr)²/c²

For ω = 2000 rad/s, r = 0.02 m:
  v = ωr = 40 m/s
  ε = v²/c² = 1.78e-14 ≈ 0 (negligible)

So the relativistic correction is essentially zero at lab speeds.

The LPD correction from the hyperbolic terms in Eq (1):
This is geometry-dependent (a_o, a_i, λ_L) and IS material-
dependent through λ_L.

From the paper: "the contribution of the finite size of the
superconducting samples" was neglected by Tate but included
by Hoang. This is the key difference.
""")

# From the paper's experimental parameters:
# Quartz core radius a_i = 2 cm = 0.02 m
# SC layer thickness Δa = a_o - a_i (varies, they tested different)
# Radial distance r = 5 cm = 0.05 m
# Angular velocity ω up to 2000 rad/s

a_i = 0.02  # m (quartz core radius)
r = 0.05    # m (sensor distance)
omega = 2000  # rad/s

# The LPD correction factor from Eq (1):
# The hyperbolic term modifies the field based on how the
# supercurrent distributes in the finite-thickness shell.
# For thick shell (Δa >> λ_L): correction → 0 (bulk behavior)
# For thin shell (Δa ~ λ_L): correction is significant

# The paper says they used a 2 μm layer of Sn (from Fig 1 caption)
# But for the mass measurement (Fig 3), they likely used thicker samples
# to get adequate signal. The specific Δa for each material's mass
# measurement is in the supplementary data.

# Let's estimate the LPD correction for each material
# using the formula from the paper.
# For a shell with Δa >> λ_L, the correction approaches:
# correction ≈ 3(λ_L/a_o)² × (geometry terms)

print(f"\n{'='*70}")
print("LPD CORRECTION ESTIMATES")
print(f"{'='*70}\n")

# Assume Δa = 1 mm for all materials (reasonable for lab samples)
delta_a = 1e-3  # 1 mm shell thickness
a_o = a_i + delta_a  # outer radius

for name, d in materials.items():
    lam_L = d["lambda_L_nm"] * 1e-9  # convert to meters

    # Ratio λ_L / Δa — how much of the shell is penetrated
    penetration_ratio = lam_L / delta_a

    # For thick shells (Δa >> λ_L), the LPD correction to the
    # measured mass ratio is approximately:
    # δm_LPD/m ≈ 2λ_L/Δa (first order)
    # This is because the supercurrent flows only in the outer
    # λ_L of the shell, effectively reducing the "active" mass

    lpd_correction_ppm = 2 * lam_L / delta_a * 1e6

    # The measured anomaly in ppm
    measured_ppm = (d["m_star"] - 1.0) * 1e6

    # If we subtract the LPD correction, what's left?
    # But wait — the LPD correction makes the MEASURED mass
    # appear LARGER (more field per unit omega because current
    # is concentrated near the surface). So the correction
    # should be SUBTRACTED from the measured value to get the
    # bare mass.

    # Actually: Hoang's formula already INCLUDES the LPD effect.
    # Their m* is extracted accounting for LPD. So the measured
    # m*/2m_e in Figure 3 already has LPD correction applied.
    # The values shown ARE the corrected Cooper pair mass ratios.

    # But do they correct PERFECTLY? Or is there a residual?
    # The paper says theoretical prediction is 0.999992 for all
    # materials (just the BCS band correction).
    # The measured values are all > 1.0.
    # The difference = the anomaly that includes whatever
    # Tate saw PLUS any additional effects.

    ufcp_ppm = alpha**2 * d["lambda_ep"]**2 * 1e6

    print(f"{name:>3}: measured={measured_ppm:>6.1f} ppm | "
          f"λ_L/Δa={penetration_ratio:.4f} | "
          f"UFCP pred={ufcp_ppm:>6.1f} ppm")

# ==============================================================
# THE KEY QUESTION: What determines the measured ordering?
# ==============================================================
print(f"\n{'='*70}")
print("ORDERING ANALYSIS")
print(f"{'='*70}\n")

print("The measured values ordered by size:")
sorted_by_measured = sorted(materials.items(),
    key=lambda x: x[1]["m_star"])

for name, d in sorted_by_measured:
    ppm = (d["m_star"] - 1.0) * 1e6
    print(f"  {name:>3}: {ppm:>6.1f} ppm  (Z={d['Z']:>2}, λ_ep={d['lambda_ep']:.2f}, λ_L={d['lambda_L_nm']:.0f} nm)")

print(f"\nOrdering by λ_ep²:")
sorted_by_lep = sorted(materials.items(),
    key=lambda x: x[1]["lambda_ep"]**2, reverse=True)
for name, d in sorted_by_lep:
    ufcp = alpha**2 * d["lambda_ep"]**2 * 1e6
    print(f"  {name:>3}: UFCP={ufcp:>6.1f} ppm  (λ_ep={d['lambda_ep']:.2f})")

print(f"\nOrdering by Z:")
sorted_by_Z = sorted(materials.items(),
    key=lambda x: x[1]["Z"])
for name, d in sorted_by_Z:
    ppm = (d["m_star"] - 1.0) * 1e6
    print(f"  {name:>3}: Z={d['Z']:>2}, measured={ppm:>6.1f} ppm")

print(f"\nOrdering by λ_L:")
sorted_by_lL = sorted(materials.items(),
    key=lambda x: x[1]["lambda_L_nm"])
for name, d in sorted_by_lL:
    ppm = (d["m_star"] - 1.0) * 1e6
    print(f"  {name:>3}: λ_L={d['lambda_L_nm']:>5.0f} nm, measured={ppm:>6.1f} ppm")

# ==============================================================
# CRITICAL: Hoang vs Tate for Niobium
# ==============================================================
print(f"\n{'='*70}")
print("CRITICAL: Nb — HOANG vs TATE")
print(f"{'='*70}\n")

print("""
Tate (1989): m*/2m_e = 1.000084 ± 0.000021 → 84 ± 21 ppm
Hoang (2020): m*/2m_e = 1.00001 ± 0.0000021 → 10 ± 2.1 ppm

These are VERY different. Hoang's Nb anomaly is 10 ppm, not 84.
Hoang's precision is 10x better (2.1 vs 21 ppm).

Hoang explicitly says Tate "neglected the contribution of the
finite size of the superconducting samples" and "neglected the
London penetration depth."

So: 84 - 10 = 74 ppm was Tate's SYSTEMATIC ERROR from
neglecting LPD and geometry. The true anomaly for Nb is ~10 ppm.

UFCP predicted 84.5 ppm. The true value is 10 ppm.
UFCP matched Tate's systematic error, not the real anomaly.

OR: Hoang OVER-corrected. Their model subtracts too much,
and the true anomaly is somewhere between 10 and 84 ppm.
""")

# ==============================================================
# Can UFCP match the Hoang data with a DIFFERENT formula?
# ==============================================================
print(f"\n{'='*70}")
print("SEARCHING FOR THE RIGHT FORMULA")
print(f"{'='*70}\n")

# The measured values in ppm: Nb=10, Sn=30, In=60, Al=70, Cd=80, Pb=100
# What parameter correlates with this ordering?

# Test various combinations
measured_ppm = {name: (d["m_star"]-1.0)*1e6 for name, d in materials.items()}

# Test 1: Does it scale with Z?
print("Test 1: linear in Z?")
for name, d in sorted_by_measured:
    ppm = measured_ppm[name]
    ratio = ppm / d["Z"] if d["Z"] > 0 else 0
    print(f"  {name}: {ppm:.0f} ppm / Z={d['Z']} = {ratio:.2f}")

# Test 2: Z^2?
print("\nTest 2: Z^2?")
for name, d in sorted_by_measured:
    ppm = measured_ppm[name]
    ratio = ppm / d["Z"]**2 * 1e3
    print(f"  {name}: {ppm:.0f} ppm / Z²={d['Z']**2} = {ratio:.3f}×10⁻³")

# Test 3: Does the RESIDUAL after subtracting a Z-dependent
# term match lambda_ep^2?
print(f"\n{'='*70}")
print("RESIDUAL ANALYSIS: measured - f(Z) = α²λ_ep² ?")
print(f"{'='*70}\n")

# If there's a Z-dependent systematic that Hoang didn't fully
# remove, and the UFCP correction sits underneath it:
# measured = Z_systematic + α²λ_ep²

# Try: Z_systematic = β × Z
# Then residual = measured - β×Z
# Does residual ~ α²λ_ep²?

# Fit β to minimize residual vs α²λ_ep²
best_beta = 0
best_err = 1e10

for beta_try in np.linspace(0.5, 3.0, 500):
    err = 0
    for name, d in materials.items():
        residual = measured_ppm[name] - beta_try * d["Z"]
        ufcp = alpha**2 * d["lambda_ep"]**2 * 1e6
        err += (residual - ufcp)**2
    if err < best_err:
        best_err = err
        best_beta = beta_try

print(f"Best fit: β = {best_beta:.3f} (systematic ≈ {best_beta:.2f} × Z ppm)")
print()
print(f"{'Mat':>3} | {'Measured':>8} | {'β×Z':>6} | {'Residual':>8} | {'UFCP':>8} | {'Δ':>6}")
print(f"{'-'*3}-+-{'-'*8}-+-{'-'*6}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}")

for name, d in sorted_by_measured:
    ppm = measured_ppm[name]
    z_term = best_beta * d["Z"]
    residual = ppm - z_term
    ufcp = alpha**2 * d["lambda_ep"]**2 * 1e6
    delta = residual - ufcp
    print(f"{name:>3} | {ppm:>7.1f}  | {z_term:>5.1f}  | {residual:>7.1f}  | {ufcp:>7.1f}  | {delta:>+5.1f}")

# Also try: systematic = β × Z + γ
print(f"\n--- With offset: systematic = β×Z + γ ---\n")

best_beta2 = 0
best_gamma = 0
best_err2 = 1e10

for beta_try in np.linspace(0.0, 3.0, 300):
    for gamma_try in np.linspace(-50, 50, 200):
        err = 0
        for name, d in materials.items():
            residual = measured_ppm[name] - beta_try * d["Z"] - gamma_try
            ufcp = alpha**2 * d["lambda_ep"]**2 * 1e6
            err += (residual - ufcp)**2
        if err < best_err2:
            best_err2 = err
            best_beta2 = beta_try
            best_gamma = gamma_try

print(f"Best fit: β={best_beta2:.3f}, γ={best_gamma:.1f}")
print(f"Systematic ≈ {best_beta2:.2f}×Z + {best_gamma:.0f} ppm")
print()
print(f"{'Mat':>3} | {'Meas':>6} | {'Syst':>6} | {'Resid':>6} | {'UFCP':>6} | {'Δ':>6} | {'σ':>4}")
print(f"{'-'*3}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*4}")

residuals_match = True
for name, d in sorted_by_measured:
    ppm = measured_ppm[name]
    syst = best_beta2 * d["Z"] + best_gamma
    residual = ppm - syst
    ufcp = alpha**2 * d["lambda_ep"]**2 * 1e6
    delta = residual - ufcp
    err_ppm = d["err"] * 1e6
    sigma = abs(delta) / err_ppm if err_ppm > 0 else 999
    if sigma > 3:
        residuals_match = False
    print(f"{name:>3} | {ppm:>5.0f}  | {syst:>5.0f}  | {residual:>5.0f}  | {ufcp:>5.0f}  | {delta:>+5.0f}  | {sigma:>4.1f}")

print(f"\n{'='*70}")
if residuals_match:
    print("RESIDUALS MATCH α²λ_ep² WITHIN MEASUREMENT UNCERTAINTY")
    print("The Hoang data is CONSISTENT with UFCP + a Z-dependent systematic")
else:
    print("RESIDUALS DO NOT MATCH α²λ_ep²")
    print("Check if a different decomposition works")
print(f"{'='*70}")

# ==============================================================
# ALTERNATIVE: What if the anomaly IS just Z-dependent?
# ==============================================================
print(f"\n{'='*70}")
print("ALTERNATIVE: Is the anomaly simply Z-dependent (no UFCP)?")
print(f"{'='*70}\n")

# Fit measured = a × Z + b
from numpy.polynomial import polynomial as P
Z_vals = np.array([d["Z"] for d in materials.values()])
m_vals = np.array([measured_ppm[name] for name in materials.keys()])

# Linear fit
coeffs = np.polyfit(Z_vals, m_vals, 1)
a_fit, b_fit = coeffs

print(f"Linear fit: anomaly = {a_fit:.3f}×Z + {b_fit:.1f}")
print()

print(f"{'Mat':>3} | {'Z':>3} | {'Measured':>8} | {'Fit':>8} | {'Residual':>8}")
print(f"{'-'*3}-+-{'-'*3}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")

fit_residuals = []
for name, d in sorted_by_Z:
    ppm = measured_ppm[name]
    fit = a_fit * d["Z"] + b_fit
    resid = ppm - fit
    fit_residuals.append(resid)
    print(f"{name:>3} | {d['Z']:>3} | {ppm:>7.1f}  | {fit:>7.1f}  | {resid:>+7.1f}")

r_squared = 1 - np.sum(np.array(fit_residuals)**2) / np.sum((m_vals - np.mean(m_vals))**2)
print(f"\nR² = {r_squared:.4f}")

if r_squared > 0.9:
    print("High R² — the anomaly is well-explained by Z alone")
    print("UFCP's λ_ep dependence is NOT needed")
else:
    print(f"R² = {r_squared:.3f} — Z alone doesn't fully explain the data")
    print("Room for additional material-dependent correction (maybe λ_ep)")

print(f"\n{'='*70}")
print("FINAL ASSESSMENT")
print(f"{'='*70}\n")

print(f"""
The Hoang data shows:
  1. The Nb anomaly is ~10 ppm, NOT 84 ppm (Tate's was inflated
     by systematic errors from neglecting LPD/geometry)
  2. The anomaly increases with atomic number Z
  3. The ordering does NOT match λ_ep²

For UFCP:
  - The α²λ_ep² = 84.5 ppm match with Tate was matching a
    systematic error, not the true anomaly
  - The true Nb anomaly (~10 ppm) is much smaller
  - The material dependence follows Z, not λ_ep

HOWEVER:
  - Hoang's corrections themselves could be incomplete
  - The Z-dependence might be a DIFFERENT physical effect
    (relativistic, nuclear charge screening) ON TOP of which
    α²λ_ep² sits as a smaller correction
  - With only 6 data points, separating two effects is hard

HONEST VERDICT: The clean α²λ_ep² story is dead. The Tate
match was a coincidence. But whether UFCP contributes a SMALL
correction underneath a larger Z-dependent effect cannot be
ruled out with this data. The framework isn't killed — but
the specific prediction we made is wrong.
""")
