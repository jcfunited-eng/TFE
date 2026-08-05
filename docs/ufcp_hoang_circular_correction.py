"""
UFCP Hoang Circular Correction Analysis
==========================================
Hoang corrects for LPD using standard m*.
But if m* has a UFCP anomaly, their λ_L is wrong.
The correction absorbs part of the anomaly.

How much gets absorbed? That depends on the sensitivity
of the extracted m* to the assumed λ_L.

From Hoang Eq (1): B depends on m*, λ_L, geometry.
But λ_L = sqrt(m* / (μ₀ n_s e²)) depends on m*.
So m* appears BOTH directly and through λ_L.
"""

import math
import numpy as np

alpha = 1/137.036
mu_0 = 4 * math.pi * 1e-7
e_charge = 1.602e-19
m_e = 9.109e-31

print("=" * 70)
print("CIRCULAR CORRECTION ANALYSIS")
print("=" * 70)

# Material data with superfluid density
materials = {
    "Nb": {"Z": 41, "m_hoang_ppm": 10, "err_ppm": 2.1, "lambda_ep": 1.26,
            "lambda_L_nm": 39.0, "n_s": 2.78e28},
    "Sn": {"Z": 50, "m_hoang_ppm": 30, "err_ppm": 2.2, "lambda_ep": 0.72,
            "lambda_L_nm": 34.0, "n_s": 1.48e29},
    "In": {"Z": 49, "m_hoang_ppm": 60, "err_ppm": 2.3, "lambda_ep": 0.81,
            "lambda_L_nm": 23.5, "n_s": 1.15e29},
    "Al": {"Z": 13, "m_hoang_ppm": 70, "err_ppm": 1.0, "lambda_ep": 0.43,
            "lambda_L_nm": 16.0, "n_s": 1.81e29},
    "Cd": {"Z": 48, "m_hoang_ppm": 80, "err_ppm": 3.1, "lambda_ep": 0.38,
            "lambda_L_nm": 110.0, "n_s": 4.63e28},
    "Pb": {"Z": 82, "m_hoang_ppm": 100, "err_ppm": 4.1, "lambda_ep": 1.55,
            "lambda_L_nm": 37.0, "n_s": 1.32e29},
}

# Hoang's geometry (from paper)
a_i = 0.02     # inner radius (quartz core), meters
delta_a = 0.002  # shell thickness, meters (2 mm estimated)
a_o = a_i + delta_a
r = 0.05       # sensor distance, meters

print(f"\nGeometry: a_i={a_i*100}cm, Δa={delta_a*1000}mm, a_o={a_o*100}cm, r={r*100}cm")

print(f"\n{'='*70}")
print("STEP 1: How sensitive is the extracted m* to the assumed λ_L?")
print(f"{'='*70}\n")

# From Eq (1), the correction term involves:
# tanh((a_o - a_i) / λ_L) and ratios a_o/λ_L, a_i/λ_L
#
# For each material, compute:
#   dm*/dλ_L × (δλ_L from UFCP anomaly)
#
# λ_L = sqrt(m* / (μ₀ n_s e²))
# If m* has anomaly δm*, then:
#   δλ_L/λ_L = (1/2) × δm*/m*
#
# The correction in Eq (1) modifies the MEASURED B field.
# The extracted m* depends on the correction applied.
# If the correction uses wrong λ_L, the extracted m* shifts.

for name, d in materials.items():
    lam_L = d["lambda_L_nm"] * 1e-9
    ufcp_anomaly_ppm = alpha**2 * d["lambda_ep"]**2 * 1e6

    # How much does λ_L change with the UFCP anomaly?
    delta_lam_L_frac = 0.5 * ufcp_anomaly_ppm * 1e-6
    delta_lam_L = lam_L * delta_lam_L_frac

    # Key ratios in Eq (1)
    ratio_shell = delta_a / lam_L  # Δa / λ_L
    ratio_outer = a_o / lam_L      # a_o / λ_L
    ratio_inner = a_i / lam_L      # a_i / λ_L

    # The hyperbolic correction factor in Eq (1):
    # F = 1 - (3λ_L/a_o) × [correction involving tanh]
    # For Δa >> λ_L (thick shell): tanh → 1, correction small
    # For Δa ~ λ_L (thin shell): correction significant

    tanh_val = math.tanh(delta_a / lam_L)

    # Sensitivity: how much does the geometry factor change
    # when λ_L changes by δλ_L?
    # Numerically: compute F(λ_L) and F(λ_L + δλ_L)

    def geometry_factor(lam):
        """Simplified geometry correction from Hoang Eq (1)."""
        if lam < 1e-12:
            return 1.0
        x = delta_a / lam
        ao_lam = a_o / lam
        ai_lam = a_i / lam

        # The key correction term
        # From Eq (1): involves ratio a_o³/r³ × [1 + 3/(a_o/λ_L)² - ...]
        # Simplified: the correction scales as (λ_L/a_o)² for thick shells
        corr = 1.0 - 3.0 * (lam / a_o)**2 * (1.0 - (2.0/x) * math.tanh(x/2))
        return corr

    F_standard = geometry_factor(lam_L)
    F_ufcp = geometry_factor(lam_L * (1 + delta_lam_L_frac))

    # The change in F causes a change in extracted m*
    # m*_extracted = m*_true × F_standard / F_ufcp
    # (because they divide by F_standard but should divide by F_ufcp)
    if F_ufcp > 0:
        m_correction_factor = F_standard / F_ufcp
        absorbed_ppm = (1 - m_correction_factor) * 1e6
    else:
        absorbed_ppm = 0

    # How much of the UFCP anomaly gets absorbed?
    if ufcp_anomaly_ppm > 0:
        absorption_fraction = absorbed_ppm / ufcp_anomaly_ppm
    else:
        absorption_fraction = 0

    # The TRUE anomaly visible after Hoang's correction:
    visible_ppm = ufcp_anomaly_ppm - absorbed_ppm

    print(f"{name:>3}: UFCP={ufcp_anomaly_ppm:>6.1f}ppm | "
          f"Δa/λ_L={ratio_shell:>5.1f} | "
          f"F_std={F_standard:.6f} | F_ufcp={F_ufcp:.6f} | "
          f"absorbed={absorbed_ppm:>6.1f}ppm ({absorption_fraction*100:>4.1f}%) | "
          f"visible={visible_ppm:>6.1f}ppm | "
          f"Hoang measured={d['m_hoang_ppm']}ppm")

print(f"\n{'='*70}")
print("STEP 2: Compare visible UFCP anomaly to Hoang measured")
print(f"{'='*70}\n")

print(f"{'Mat':>3} | {'UFCP total':>10} | {'Absorbed':>8} | {'Visible':>8} | {'Hoang':>6} | {'Δ':>6} | {'σ':>4}")
print(f"{'-'*3}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}-+-{'-'*4}")

for name, d in materials.items():
    lam_L = d["lambda_L_nm"] * 1e-9
    ufcp_total = alpha**2 * d["lambda_ep"]**2 * 1e6
    delta_lam_frac = 0.5 * ufcp_total * 1e-6

    F_std = geometry_factor(lam_L)
    F_ufcp = geometry_factor(lam_L * (1 + delta_lam_frac))

    if F_ufcp > 0:
        absorbed = (1 - F_std / F_ufcp) * 1e6
    else:
        absorbed = 0

    visible = ufcp_total - absorbed
    delta = visible - d["m_hoang_ppm"]
    sigma = abs(delta) / d["err_ppm"] if d["err_ppm"] > 0 else 999

    print(f"{name:>3} | {ufcp_total:>9.1f}  | {absorbed:>7.1f}  | {visible:>7.1f}  | {d['m_hoang_ppm']:>5}  | {delta:>+5.0f}  | {sigma:>4.1f}")

# ==============================================================
# STEP 3: What if the absorption is stronger?
# ==============================================================
print(f"\n{'='*70}")
print("STEP 3: The absorption depends on shell geometry")
print(f"{'='*70}\n")

print("""
The simplified geometry factor may not capture the full
sensitivity. The actual Eq (1) has additional terms with
(a_o/λ_L)² in the denominator that amplify the λ_L dependence.

Also: different materials may have been measured with different
shell thicknesses. The paper mentions 2 μm for the Fig 1
demonstration but the actual mass measurements could use
different thicknesses optimized per material.

If Δa/λ_L varies by material, the absorption fraction varies,
and the VISIBLE anomaly after Hoang's correction would be
material-dependent even if the UNDERLYING anomaly is purely
α²λ_ep².

The key ratio is Δa/λ_L:
  - Large Δa/λ_L (thick shell vs penetration): little absorption
  - Small Δa/λ_L (thin shell or large λ_L): more absorption
""")

# What Δa would make the visible anomaly match Hoang's data?
print("What shell thickness Δa makes UFCP match Hoang for each material?\n")

for name, d in materials.items():
    lam_L = d["lambda_L_nm"] * 1e-9
    ufcp_total = alpha**2 * d["lambda_ep"]**2 * 1e6
    target_visible = d["m_hoang_ppm"]

    # Need: ufcp_total - absorbed(Δa) = target_visible
    # absorbed(Δa) = ufcp_total - target_visible
    needed_absorbed = ufcp_total - target_visible

    # Search for Δa that gives the right absorption
    best_da = delta_a
    best_diff = 1e10

    for da_try in np.linspace(lam_L * 0.5, lam_L * 200, 10000):
        ao_try = a_i + da_try
        delta_frac = 0.5 * ufcp_total * 1e-6

        F1 = geometry_factor(lam_L)

        # Recalculate with adjusted a_o
        def gf(lam, da):
            ao = a_i + da
            x = da / lam
            corr = 1.0 - 3.0 * (lam / ao)**2 * (1.0 - (2.0/x) * math.tanh(x/2)) if x > 0.01 else 1.0
            return corr

        F1 = gf(lam_L, da_try)
        F2 = gf(lam_L * (1 + delta_frac), da_try)

        if F2 > 0:
            abs_ppm = (1 - F1/F2) * 1e6
            vis_ppm = ufcp_total - abs_ppm
            diff = abs(vis_ppm - target_visible)
            if diff < best_diff:
                best_diff = diff
                best_da = da_try

    ratio = best_da / lam_L
    print(f"  {name}: need Δa = {best_da*1e6:.0f} μm "
          f"(Δa/λ_L = {ratio:.1f}) to get {target_visible} ppm visible")

print(f"\n{'='*70}")
print("CONCLUSION")
print(f"{'='*70}\n")

print("""
The circular correction analysis shows:

1. The simplified geometry factor absorbs very LITTLE of the
   UFCP anomaly (<1%) because for typical shell thicknesses
   (mm scale) the λ_L correction terms are tiny (λ_L is nm).

2. For the absorption to be significant enough to explain the
   difference between α²λ_ep² and Hoang's measurements, the
   shell thickness would need to be comparable to λ_L (nm scale).
   That's unrealistically thin for a precision measurement.

3. The circularity effect is REAL but TOO SMALL to rescue the
   α²λ_ep² formula. The Hoang data genuinely contradicts the
   specific UFCP prediction.

HOWEVER: the anomalies (10-100 ppm) remain UNEXPLAINED by
standard BCS theory. Something beyond standard physics is
producing these material-dependent mass corrections. UFCP's
general framework (W kernel coupling, coherence field effects)
is not killed — just the specific formula α²λ_ep².

The right formula is still unknown.
""")
