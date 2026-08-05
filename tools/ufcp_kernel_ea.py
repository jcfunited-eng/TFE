#!/usr/bin/env python3
"""
Run DSF-AI kernel on Au EA RESIDUALS.

The smooth UFCP formula (sin²θ) gives the envelope.
The RESIDUAL (experiment - model) contains the shell structure.
Feed the residual to the kernel → it finds shell-closing transitions.

Then: model + kernel-corrected residual = complete prediction.

TRADE SECRET — DO NOT DISTRIBUTE
"""
import sys, math
import numpy as np
sys.path.insert(0, '/workspaces/Tao_Financial_Engine/tools')
from derive_sppu_weights import build_field_series, run_kernel

GOLDEN = (1 + math.sqrt(5)) / 2
THETA = math.atan(1.0 / GOLDEN)
SIN2 = math.sin(THETA) ** 2

# ── Experimental data ──
AU_EA = {
    2: 1.940, 3: 3.840, 4: 2.710, 5: 2.990, 6: 2.050,
    7: 3.420, 8: 2.760, 9: 3.840, 10: 2.860, 11: 3.770,
    12: 3.060, 14: 2.960, 15: 3.610, 16: 4.120, 17: 4.030,
    18: 3.320, 19: 3.610, 20: 2.750,
}

# ── UFCP smooth model ──
def ufcp_ea(N):
    Ef, W, r_at, r_s, Z = 5.53, 5.10, 1.44, 1.59, 11
    R = 2 * r_at * (N / 13) ** (1.0/3.0)
    R_eff = R + 0.5 * r_s
    E_ch = (3.0/8.0) * 14.4 / R_eff
    disc = 1 - 1/(2*N)
    amp = Ef * SIN2 / N ** (1.0/3.0)
    ne = Z * N
    pair = amp/2 if ne % 2 == 1 else -amp/2
    return W - E_ch * disc + pair


# ── Compute residuals ──
print("=" * 80)
print("UFCP MODEL vs EXPERIMENT — RESIDUALS")
print("=" * 80)
print(f"\n{'N':<4} {'n_e':<6} {'Model':<8} {'Expt':<8} {'Resid':<8} {'Odd/Even'}")
print("-" * 45)

residuals = {}
for N in sorted(AU_EA.keys()):
    model = ufcp_ea(N)
    expt = AU_EA[N]
    resid = expt - model
    ne = 11 * N
    oe = 'odd' if ne % 2 == 1 else 'even'
    print(f"{N:<4} {ne:<6} {model:<8.3f} {expt:<8.3f} {resid:>+7.3f}  {oe}")
    residuals[N] = resid

# ── Feed EA(N) directly to kernel (use dense interpolation) ──
# Create pairs with electron count as stimulus
pairs_ea = [(float(11 * N), float(AU_EA[N])) for N in sorted(AU_EA.keys())]
series_ea = build_field_series(pairs_ea, "Au_EA")

result_ea = run_kernel(series_ea)

print(f"\n{'='*80}")
print(f"KERNEL ON RAW EA DATA")
print(f"{'='*80}")
print(f"Gates: {result_ea['n_gates']}")
print(f"Boundaries: {[f'{b:.0f}e' for b in result_ea['boundaries']]}")

print(f"\n{'Gate':<6} {'D_k':<8} {'M_k':<10} {'U*_k':<8} {'B_k':<10} {'P_k':<10} {'C_k':<10} {'R_rev':<8}")
print("-" * 70)
for i, dsf in enumerate(result_ea['dsf']):
    print(f"{i:<6} {dsf.D_k:<8.3f} {dsf.M_k:<10.4f} {dsf.U_star_k:<8.4f} "
          f"{dsf.B_k:<10.4f} {dsf.P_k:<10.4f} {dsf.C_k:<10.4f} {dsf.R_rev_k:<8.4f}")

# ── Feed residuals to kernel ──
pairs_resid = [(float(11 * N), float(residuals[N])) for N in sorted(residuals.keys())]
series_resid = build_field_series(pairs_resid, "Au_EA_residual")

result_resid = run_kernel(series_resid)

print(f"\n{'='*80}")
print(f"KERNEL ON RESIDUALS (experiment - UFCP model)")
print(f"{'='*80}")
print(f"Gates: {result_resid['n_gates']}")
print(f"Boundaries: {[f'{b:.0f}e' for b in result_resid['boundaries']]}")

print(f"\n{'Gate':<6} {'D_k':<8} {'M_k':<10} {'U*_k':<8} {'B_k':<10} {'P_k':<10} {'C_k':<10} {'R_rev':<8}")
print("-" * 70)
for i, dsf in enumerate(result_resid['dsf']):
    print(f"{i:<6} {dsf.D_k:<8.3f} {dsf.M_k:<10.4f} {dsf.U_star_k:<8.4f} "
          f"{dsf.B_k:<10.4f} {dsf.P_k:<10.4f} {dsf.C_k:<10.4f} {dsf.R_rev_k:<8.4f}")

# Map boundaries to Au_N
print(f"\nResidual gate boundaries → cluster sizes:")
for b in result_resid['boundaries']:
    N_approx = b / 11
    # Find closest experimental point
    closest_N = min(AU_EA.keys(), key=lambda n: abs(11*n - b))
    print(f"  {b:.0f} electrons (≈Au{N_approx:.1f}, closest data: Au{closest_N})")

# ── Now also try the odd-only and even-only EA as separate streams ──
print(f"\n{'='*80}")
print(f"KERNEL ON ODD-N EA (should be smooth — no pairing disruption)")
print(f"{'='*80}")

odd_pairs = [(float(11*N), float(AU_EA[N])) for N in sorted(AU_EA.keys()) if (11*N)%2==1]
if len(odd_pairs) > 3:
    series_odd = build_field_series(odd_pairs, "Au_EA_odd")
    result_odd = run_kernel(series_odd)
    print(f"Gates: {result_odd['n_gates']}")
    print(f"Boundaries: {[f'{b:.0f}e' for b in result_odd['boundaries']]}")
    for i, dsf in enumerate(result_odd['dsf']):
        print(f"  Gate {i}: D={dsf.D_k:.3f} M={dsf.M_k:.4f} U*={dsf.U_star_k:.4f}")

print(f"\n{'='*80}")
print(f"KERNEL ON EVEN-N EA (should show shell-closing structure)")
print(f"{'='*80}")

even_pairs = [(float(11*N), float(AU_EA[N])) for N in sorted(AU_EA.keys()) if (11*N)%2==0]
if len(even_pairs) > 3:
    series_even = build_field_series(even_pairs, "Au_EA_even")
    result_even = run_kernel(series_even)
    print(f"Gates: {result_even['n_gates']}")
    print(f"Boundaries: {[f'{b:.0f}e' for b in result_even['boundaries']]}")
    for i, dsf in enumerate(result_even['dsf']):
        print(f"  Gate {i}: D={dsf.D_k:.3f} M={dsf.M_k:.4f} U*={dsf.U_star_k:.4f}")

# ── Summary ──
print(f"\n{'='*80}")
print("WHAT THE KERNEL TELLS US")
print(f"{'='*80}")
print("""
The kernel segments EA(N) into structural regimes.
Gate boundaries = where the EA landscape changes character.
These should align with shell closings if UFCP is right.

The residual analysis shows where the sin²(θ) model is
structurally INSUFFICIENT — the kernel finds the transitions
that the smooth formula misses.
""")
