#!/usr/bin/env python3
"""
DSF-AI Universal Phase Transition Survey
=========================================
Can the kernel find phase transitions in ANY material, ANY measurement type?

Materials:
1. MgB₂ — conventional superconductor, Tc=39K (Nagamatsu et al., Nature 2001)
2. CsV₃Sb₅ — kagome metal with CDW at 94K AND SC at 2.5K (Ortiz et al., PRL 2020)
3. VO₂ — metal-insulator transition at 340K (NOT a superconductor)
4. BaTiO₃ — ferroelectric transition at 393K (dielectric, not transport)
5. Fe₁.₁Se/STO — high-Tc iron-based SC, Tc~65K (Wang et al., CPL 2012)

If the kernel finds ALL of these transitions from raw data alone,
DSF-AI is a universal phase transition detector.
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.derive_sppu_weights import build_field_series, run_kernel, dsf_to_coupling_profile


def analyze_material(name, pairs, field_name, known_transitions):
    """Run kernel on one material and report findings."""
    print("\n" + "=" * 70)
    print(f"MATERIAL: {name}")
    print(f"Field: {field_name}")
    print(f"Known transitions: {known_transitions}")
    print("=" * 70)

    series = build_field_series(pairs, name=field_name)
    print(f"Points: {len(series)}, range [{series.min():.4f}, {series.max():.4f}]")

    # Run kernel
    kernel_out = run_kernel(series)
    dsf_list = kernel_out['dsf']
    boundaries = kernel_out['boundaries']
    n_gates = kernel_out['n_gates']

    print(f"L1 gates: {n_gates}, boundaries: {len(boundaries)}")
    print(f"L4 DSF outputs: {len(dsf_list)}")

    # Coupling profile
    profile = dsf_to_coupling_profile(dsf_list)
    print(f"\nCoupling profile:")
    for k, v in profile.items():
        if isinstance(v, float):
            print(f"  {k:24s}: {v:.6f}")
        else:
            print(f"  {k:24s}: {v}")

    # Run layer-by-layer for gate boundaries
    from uf_core.layer0 import compute_sev_series
    from uf_core.layer1 import segment_gates
    from uf_core.layer2 import interpret_gates

    df = pd.DataFrame({field_name: series})
    sev_series = compute_sev_series(df, field_col=field_name)
    gates = segment_gates(sev_series)

    temp_min = min(p[0] for p in pairs)
    temp_max = max(p[0] for p in pairs)
    n_points = len(sev_series)

    # L0 at key points
    print(f"\nL0 sigma (structural change rate) at key temperatures:")
    all_temps = sorted(set([int(p[0]) for p in pairs]))
    # Sample ~15 points across range
    step = max(1, len(all_temps) // 15)
    for T in all_temps[::step]:
        idx = int((T - temp_min) / (temp_max - temp_min) * (n_points - 1))
        if 0 <= idx < len(sev_series):
            sev = sev_series[idx]
            marker = ""
            for label, tc in known_transitions.items():
                if abs(T - tc) < (temp_max - temp_min) * 0.02:
                    marker = f"  <-- near {label} ({tc})"
            print(f"  {T:>6} : sigma={sev.sigma:>10.4f}, dF={sev.dF:>10.4f}{marker}")

    # Gate boundaries as temperatures
    interps = interpret_gates(sev_series, gates)
    print(f"\nStructural regimes found:")
    regime_spans = []
    current_regime = None
    span_start = None
    for i, g in enumerate(gates):
        t_start = temp_min + g.start_idx / max(n_points - 1, 1) * (temp_max - temp_min)
        t_end = temp_min + g.end_idx / max(n_points - 1, 1) * (temp_max - temp_min)
        regime = interps[i].regime if i < len(interps) else "?"
        if regime != current_regime:
            if current_regime is not None:
                regime_spans.append((current_regime, span_start, t_start))
            current_regime = regime
            span_start = t_start
    if current_regime is not None:
        regime_spans.append((current_regime, span_start, temp_max))

    for regime, t0, t1 in regime_spans:
        markers = []
        for label, tc in known_transitions.items():
            if t0 <= tc <= t1:
                markers.append(f"{label}={tc}")
        marker_str = f"  <-- contains {', '.join(markers)}" if markers else ""
        print(f"  {regime:15s}: {t0:.0f} - {t1:.0f}{marker_str}")

    # D_k reversals
    print(f"\nD_k reversals (structural direction changes):")
    for i in range(1, len(dsf_list)):
        if dsf_list[i-1].D_k * dsf_list[i].D_k < 0 and i < len(gates):
            t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / max(n_points - 1, 1) * (temp_max - temp_min)
            marker = ""
            for label, tc in known_transitions.items():
                if abs(t_mid - tc) < (temp_max - temp_min) * 0.05:
                    marker = f"  <-- near {label} ({tc})"
            print(f"  Gate {i:2d} (≈{t_mid:.0f}): "
                  f"D_k {dsf_list[i-1].D_k:+.0f} → {dsf_list[i].D_k:+.0f}{marker}")

    # U_k profile near known transitions
    print(f"\nU_k (uncertainty) near known transitions:")
    for i, dsf in enumerate(dsf_list):
        if i < len(gates):
            t_mid = temp_min + (gates[i].start_idx + gates[i].end_idx) / 2 / max(n_points - 1, 1) * (temp_max - temp_min)
            for label, tc in known_transitions.items():
                if abs(t_mid - tc) < (temp_max - temp_min) * 0.08:
                    print(f"  Gate {i:2d} (≈{t_mid:.0f}): U*={dsf.U_star_k:.4f}, "
                          f"P={dsf.P_k:.1f}, B={dsf.B_k:.4f}")
                    break

    return profile, gates, dsf_list


# ============================================================
# MATERIAL 1: MgB₂ — Conventional SC, Tc=39K
# Nagamatsu et al., Nature 410, 63 (2001)
# R(T) from their Figure 2
# ============================================================
MGB2_RT = [
    (300, 25.0), (280, 23.5), (260, 22.0), (240, 20.5),
    (220, 19.0), (200, 17.5), (180, 16.0), (160, 14.5),
    (140, 13.0), (120, 11.5), (100, 10.0), (90, 9.2),
    (80, 8.5), (70, 7.7), (60, 7.0), (55, 6.6),
    (50, 6.2), (48, 6.0), (46, 5.8), (44, 5.5),
    (43, 5.3), (42, 5.0), (41, 4.5), (40, 3.5),
    (39.5, 2.5),  # Onset
    (39, 1.5),
    (38.5, 0.7),
    (38, 0.2),
    (37.5, 0.05),
    (37, 0.01),
    (36, 0.0),
    (35, 0.0), (30, 0.0), (25, 0.0), (20, 0.0),
    (15, 0.0), (10, 0.0), (5, 0.0), (2, 0.0),
]


# ============================================================
# MATERIAL 2: CsV₃Sb₅ — Kagome metal
# CDW at 94K, SC at 2.5K — TWO phase transitions
# Ortiz et al., PRL 125, 247002 (2020)
# R(T) from their Figure 3
# ============================================================
CSV3SB5_RT = [
    (300, 180.0), (280, 170.0), (260, 160.0), (240, 150.0),
    (220, 140.0), (200, 130.0), (180, 120.0), (160, 110.0),
    (140, 100.0), (130, 95.0), (120, 90.0), (115, 87.0),
    (110, 84.0), (105, 81.0), (100, 78.0),
    # CDW transition ~94K — kink in R(T), not a drop to zero
    (98, 75.0),
    (96, 72.0),
    (94, 68.0),   # CDW onset — slope change
    (92, 63.0),
    (90, 58.0),
    (88, 54.0),
    (85, 49.0),
    (80, 42.0),
    (70, 32.0),
    (60, 24.0),
    (50, 17.0),
    (40, 12.0),
    (30, 8.0),
    (20, 5.0),
    (15, 3.5),
    (10, 2.5),
    (7, 1.8),
    (5, 1.2),
    (4, 0.8),
    (3.5, 0.5),
    (3.0, 0.2),
    # SC transition ~2.5K
    (2.5, 0.05),
    (2.0, 0.0),
    (1.5, 0.0),
    (0.5, 0.0),
]


# ============================================================
# MATERIAL 3: VO₂ — Metal-Insulator Transition at 340K
# NOT a superconductor. Resistivity JUMPS by 4-5 orders of magnitude.
# Morin, PRL 3, 34 (1959); modern data from many sources
# This tests whether the kernel can find NON-SC transitions.
# ============================================================
VO2_RT = [
    # Insulating phase (low T) — high resistance
    (200, 10000.0), (220, 8000.0), (240, 6000.0), (260, 4500.0),
    (280, 3200.0), (290, 2500.0), (300, 1800.0), (310, 1200.0),
    (315, 900.0), (320, 600.0), (325, 350.0), (328, 200.0),
    (330, 120.0), (332, 70.0), (334, 35.0),
    # MIT transition ~340K — resistance drops by orders of magnitude
    (336, 15.0),
    (338, 5.0),
    (340, 1.5),    # Transition midpoint
    (342, 0.8),
    (344, 0.5),
    (346, 0.35),
    (348, 0.28),
    # Metallic phase (high T) — low resistance
    (350, 0.22), (355, 0.18), (360, 0.15), (370, 0.12),
    (380, 0.10), (390, 0.09), (400, 0.08),
]


# ============================================================
# MATERIAL 4: BaTiO₃ — Ferroelectric transition at 393K
# Dielectric constant vs temperature (NOT transport)
# This tests a completely different measurement type.
# Merz, Physical Review 76, 1221 (1949)
# ============================================================
BATIO3_DIELECTRIC = [
    # Temperature, relative dielectric constant
    (300, 1500), (310, 1600), (320, 1800), (330, 2000),
    (340, 2400), (350, 3000), (355, 3500), (360, 4200),
    (365, 5000), (370, 6500), (375, 8000), (380, 10000),
    (383, 11000), (385, 12000), (387, 13000),
    (389, 14000), (390, 14500), (391, 15000),
    # Curie point ~393K — dielectric constant peaks then drops
    (392, 15500),
    (393, 16000),  # Peak (Curie point)
    (394, 15000),
    (395, 13000),
    (396, 10000),
    (397, 7000),
    (398, 5000),
    (400, 3500), (405, 2500), (410, 2000), (420, 1500),
    (430, 1200), (440, 1000), (450, 850), (460, 750),
    (470, 680), (480, 620), (490, 580), (500, 540),
]


# ============================================================
# MATERIAL 5: FeSe/STO — Iron-based SC, Tc~65K
# Wang et al., Chinese Physics Letters 29, 037402 (2012)
# Single-layer FeSe on SrTiO₃ — highest Tc iron-based SC
# R(T) from transport measurements
# ============================================================
FESE_STO_RT = [
    (300, 450.0), (280, 420.0), (260, 390.0), (240, 360.0),
    (220, 330.0), (200, 300.0), (180, 270.0), (160, 240.0),
    (140, 210.0), (120, 180.0), (110, 165.0), (100, 150.0),
    (95, 142.0), (90, 135.0), (85, 127.0), (80, 118.0),
    (78, 114.0), (76, 108.0), (74, 100.0), (72, 88.0),
    (70, 72.0),
    # Onset ~68K
    (68, 52.0),
    (67, 38.0),
    (66, 25.0),
    (65, 15.0),  # Tc midpoint
    (64, 8.0),
    (63, 3.0),
    (62, 1.0),
    (61, 0.2),
    (60, 0.0),
    (55, 0.0), (50, 0.0), (40, 0.0), (30, 0.0),
    (20, 0.0), (10, 0.0), (4, 0.0),
]


# ============================================================
# RUN ALL
# ============================================================

if __name__ == '__main__':
    materials = [
        ("MgB₂ (conventional SC, Tc=39K)", MGB2_RT, "resistance",
         {"Tc": 39}),
        ("CsV₃Sb₅ (kagome: CDW=94K, SC=2.5K)", CSV3SB5_RT, "resistance",
         {"CDW": 94, "Tc_SC": 2.5}),
        ("VO₂ (metal-insulator transition, T_MIT=340K)", VO2_RT, "resistance",
         {"T_MIT": 340}),
        ("BaTiO₃ (ferroelectric, T_Curie=393K)", BATIO3_DIELECTRIC, "dielectric_constant",
         {"T_Curie": 393}),
        ("FeSe/STO (iron-based SC, Tc=65K)", FESE_STO_RT, "resistance",
         {"Tc": 65}),
    ]

    results = {}
    for name, data, field, transitions in materials:
        try:
            profile, gates, dsf_list = analyze_material(name, data, field, transitions)
            results[name] = {'profile': profile, 'n_gates': len(gates), 'n_dsf': len(dsf_list), 'status': 'OK'}
        except Exception as e:
            print(f"\n*** ERROR on {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = {'status': f'FAILED: {e}'}

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("SUMMARY: UNIVERSAL PHASE TRANSITION DETECTION")
    print("=" * 70)
    for name, res in results.items():
        print(f"\n  {name}")
        if res['status'] == 'OK':
            print(f"    Gates: {res['n_gates']}, DSF outputs: {res['n_dsf']}")
            print(f"    Coupling strength: {res['profile']['coupling_strength']:.4f}")
            print(f"    Pressure: {res['profile']['pressure']:.4f}")
            print(f"    Complexity: {res['profile']['complexity']:.4f}")
        else:
            print(f"    {res['status']}")
