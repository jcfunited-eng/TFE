#!/usr/bin/env python3
"""
YBCO R(T) through DSF-AI Kernel
================================
Data: Wu et al., PRL 58, 908 (1987), Figure 3
The first high-Tc superconductor R(T) measurement.

Digitized from Figure 3 (4-probe resistance vs temperature).
The figure shows R(T) from ~4K to ~300K with:
  - Linear metallic behavior above ~100K
  - Onset of superconducting transition at ~93K
  - Midpoint at ~89K
  - Zero resistance below ~77K

Question: Can the L0-L4 kernel find:
  1. The 93K transition (sanity check)
  2. Structural precursors ABOVE Tc
  3. Where the structural state changes character
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.derive_sppu_weights import build_field_series, run_kernel, dsf_to_coupling_profile
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


# ============================================================
# DIGITIZED DATA: Wu et al., PRL 58, 908 (1987), Figure 3
# ============================================================
# R(T) normalized to R(300K). Digitized from published figure.
# Temperature in Kelvin, Resistance in mΩ (approximate scale).
# The paper shows R dropping from ~2.0 mΩ at 300K to 0 below 77K.

YBCO_RT_DATA = [
    # (Temperature_K, Resistance_mOhm)
    # High temperature: linear metallic regime
    (300, 2.00),
    (290, 1.94),
    (280, 1.88),
    (270, 1.82),
    (260, 1.76),
    (250, 1.70),
    (240, 1.64),
    (230, 1.58),
    (220, 1.52),
    (210, 1.46),
    (200, 1.40),
    (190, 1.34),
    (180, 1.28),
    (170, 1.22),
    (160, 1.16),
    (150, 1.10),
    (140, 1.04),
    (130, 0.98),
    (120, 0.92),
    (115, 0.89),
    (110, 0.86),
    # Approach to transition - slight deviation from linearity
    (105, 0.82),
    (100, 0.78),
    (98,  0.76),
    (96,  0.73),
    (95,  0.71),
    # Onset region (~93K)
    (94,  0.68),
    (93,  0.62),  # Onset Tc
    (92,  0.52),
    (91,  0.40),
    (90,  0.30),
    (89,  0.22),  # Midpoint
    (88,  0.15),
    (87,  0.10),
    (86,  0.06),
    (85,  0.03),
    (84,  0.015),
    (83,  0.008),
    (82,  0.003),
    (81,  0.001),
    (80,  0.0005),
    (79,  0.0001),
    (78,  0.0),
    (77,  0.0),
    # Zero resistance
    (70,  0.0),
    (60,  0.0),
    (50,  0.0),
    (40,  0.0),
    (30,  0.0),
    (20,  0.0),
    (10,  0.0),
    (4,   0.0),
]


def run_full_analysis():
    """Run the YBCO R(T) data through the full DSF-AI kernel."""

    print("=" * 70)
    print("DSF-AI KERNEL ANALYSIS: YBCO R(T)")
    print("Data: Wu et al., PRL 58, 908 (1987), Figure 3")
    print("=" * 70)

    # Build field series from digitized data
    # NOTE: build_field_series expects (stimulus, response) pairs
    # Here stimulus = temperature, response = resistance
    pairs = [(float(t), float(r)) for t, r in YBCO_RT_DATA]
    series = build_field_series(pairs, name='resistance')

    print(f"\nField series: {len(series)} points")
    print(f"Temperature range: {int(min(t for t, _ in YBCO_RT_DATA))}K - "
          f"{int(max(t for t, _ in YBCO_RT_DATA))}K")
    print(f"Resistance range: [{series.min():.4f}, {series.max():.4f}] mΩ")

    # ============================================================
    # RUN KERNEL
    # ============================================================
    print("\n" + "-" * 70)
    print("RUNNING L0 → L1 → L2 → L3 → L4 KERNEL")
    print("-" * 70)

    kernel_out = run_kernel(series)
    dsf_list = kernel_out['dsf']
    boundaries = kernel_out['boundaries']
    n_gates = kernel_out['n_gates']

    print(f"\nKernel output:")
    print(f"  L1 gates:      {n_gates}")
    print(f"  L1 boundaries: {len(boundaries)}")
    print(f"  L4 DSF outputs: {len(dsf_list)}")

    # ============================================================
    # COUPLING PROFILE
    # ============================================================
    print("\n" + "-" * 70)
    print("L4 DSF → COUPLING PROFILE")
    print("-" * 70)

    profile = dsf_to_coupling_profile(dsf_list)
    for key, val in profile.items():
        print(f"  {key:24s}: {val:.6f}" if isinstance(val, float) else f"  {key:24s}: {val}")

    # ============================================================
    # DETAILED LAYER-BY-LAYER ANALYSIS
    # ============================================================
    print("\n" + "-" * 70)
    print("LAYER-BY-LAYER STRUCTURAL ANALYSIS")
    print("-" * 70)

    # Run each layer individually to inspect intermediate state
    df = pd.DataFrame({'resistance': series})
    sev_series = compute_sev_series(df, field_col='resistance')
    print(f"\nL0: {len(sev_series)} SEV points computed")

    # Print L0 structural features at key temperatures
    # The series index maps to temperature (ascending from min to max)
    temp_min = int(min(t for t, _ in YBCO_RT_DATA))
    temp_max = int(max(t for t, _ in YBCO_RT_DATA))
    n_points = len(sev_series)

    print("\nL0 Structural Event Values at key temperatures:")
    print(f"  {'T(K)':>6} | {'F_norm':>10} | {'dF':>10} | {'sigma':>10} | {'kappa':>10}")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

    # Map temperature to index
    for T_target in [300, 200, 150, 120, 105, 100, 97, 95, 93, 91, 89, 87, 85, 80, 70, 50]:
        idx = int((T_target - temp_min) / (temp_max - temp_min) * (n_points - 1))
        if 0 <= idx < len(sev_series):
            sev = sev_series[idx]
            print(f"  {T_target:>6} | {sev.F_norm:>10.4f} | {sev.dF:>10.4f} | "
                  f"{sev.sigma:>10.4f} | {sev.kappa:>10.4f}")

    # L1: Gate segmentation
    gates = segment_gates(sev_series)
    print(f"\nL1: {len(gates)} gates segmented")
    print("\nGate boundaries (structural transitions):")
    for i, g in enumerate(gates):
        # Convert gate indices back to approximate temperatures
        t_start = temp_min + g.start_idx / (n_points - 1) * (temp_max - temp_min)
        t_end = temp_min + g.end_idx / (n_points - 1) * (temp_max - temp_min)
        print(f"  Gate {i}: idx [{g.start_idx:4d} - {g.end_idx:4d}] "
              f"≈ T [{t_start:.0f}K - {t_end:.0f}K]")

    # L2: Gate interpretation
    interps = interpret_gates(sev_series, gates)
    print(f"\nL2: {len(interps)} gate interpretations")
    for i, interp in enumerate(interps):
        t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / (n_points - 1) * (temp_max - temp_min)
        print(f"  Gate {i} (≈{t_mid:.0f}K): "
              f"regime={interp.regime}, S_k={interp.S_k:.3f}, "
              f"U_k={interp.U_k:.3f}, chi={interp.chi_k:.3f}, psi={interp.psi_k:.3f}")

    # L3: Resonance
    resonance = compute_resonance(interps)
    print(f"\nL3: {len(resonance)} resonance outputs")
    for i, res in enumerate(resonance):
        t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / (n_points - 1) * (temp_max - temp_min)
        print(f"  Gate {i} (≈{t_mid:.0f}K): "
              f"URF={res.URF_k:.4f}, g_k={res.g_k}, "
              f"Hyst={res.Hyst_k}, U_k={res.U_k:.3f}")

    # L4: DSF 7-tuple
    print(f"\nL4: DSF 7-tuples")
    print(f"  {'Gate':>4} | {'T(K)':>5} | {'D_k':>8} | {'M_k':>8} | {'U*_k':>8} | "
          f"{'B_k':>8} | {'P_k':>8} | {'C_k':>8} | {'R_rev':>8}")
    print(f"  {'-'*4}-+-{'-'*5}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-"
          f"{'-'*8}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")
    for i, dsf in enumerate(dsf_list):
        if i < len(gates):
            t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / (n_points - 1) * (temp_max - temp_min)
        else:
            t_mid = 0
        print(f"  {i:>4} | {t_mid:>5.0f} | {dsf.D_k:>8.4f} | {dsf.M_k:>8.4f} | "
              f"{dsf.U_star_k:>8.4f} | {dsf.B_k:>8.4f} | {dsf.P_k:>8.4f} | "
              f"{dsf.C_k:>8.4f} | {dsf.R_rev_k:>8.4f}")

    # ============================================================
    # KEY QUESTIONS
    # ============================================================
    print("\n" + "=" * 70)
    print("ANALYSIS: WHAT DOES THE KERNEL SEE?")
    print("=" * 70)

    # Does the kernel find the 93K transition?
    print("\n1. TRANSITION DETECTION:")
    print("   Looking for gate boundaries near 93K (onset) and 77-80K (zero R)...")
    for i, g in enumerate(gates):
        t_start = temp_min + g.start_idx / (n_points - 1) * (temp_max - temp_min)
        t_end = temp_min + g.end_idx / (n_points - 1) * (temp_max - temp_min)
        if 75 <= t_start <= 100 or 75 <= t_end <= 100:
            print(f"   *** Gate {i} spans [{t_start:.0f}K - {t_end:.0f}K] — "
                  f"TRANSITION REGION ***")

    # Structural precursors above Tc?
    print("\n2. PRECURSORS ABOVE Tc:")
    print("   Looking for structural changes above 93K...")
    for i, g in enumerate(gates):
        t_start = temp_min + g.start_idx / (n_points - 1) * (temp_max - temp_min)
        t_end = temp_min + g.end_idx / (n_points - 1) * (temp_max - temp_min)
        if t_start > 93 or t_end > 93:
            if i < len(interps):
                print(f"   Gate {i} [{t_start:.0f}K - {t_end:.0f}K]: "
                      f"regime={interps[i].regime}, U_k={interps[i].U_k:.3f}")

    # Where does DSF character change?
    print("\n3. DSF CHARACTER CHANGE:")
    print("   Looking for D_k sign changes, U* jumps, P_k spikes...")
    if len(dsf_list) >= 2:
        for i in range(1, len(dsf_list)):
            d_prev = dsf_list[i-1]
            d_curr = dsf_list[i]
            # Direction reversal
            if d_prev.D_k * d_curr.D_k < 0:
                if i < len(gates):
                    t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / (n_points - 1) * (temp_max - temp_min)
                    print(f"   D_k reversal at gate {i} (≈{t_mid:.0f}K): "
                          f"{d_prev.D_k:.4f} → {d_curr.D_k:.4f}")
            # Pressure spike
            if abs(d_curr.P_k) > abs(d_prev.P_k) * 2:
                if i < len(gates):
                    t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / (n_points - 1) * (temp_max - temp_min)
                    print(f"   P_k spike at gate {i} (≈{t_mid:.0f}K): "
                          f"{d_prev.P_k:.4f} → {d_curr.P_k:.4f}")
            # U* jump
            if abs(d_curr.U_star_k - d_prev.U_star_k) > 0.1:
                if i < len(gates):
                    t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / (n_points - 1) * (temp_max - temp_min)
                    print(f"   U* jump at gate {i} (≈{t_mid:.0f}K): "
                          f"{d_prev.U_star_k:.4f} → {d_curr.U_star_k:.4f}")

    print("\n" + "=" * 70)
    print("END OF ANALYSIS")
    print("=" * 70)


if __name__ == '__main__':
    run_full_analysis()
