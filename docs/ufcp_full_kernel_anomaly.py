"""
UF Full Kernel (L0-L4): Nuclear Anomaly Analysis
==================================================
Complete L0→L1→L2→L3→L4 pipeline on anomaly data.
Same kernel that trades stocks — now looking at nuclear physics.
"""

import sys
import math
import numpy as np
import pandas as pd

sys.path.insert(0, "/workspaces/Tao_Financial_Engine")
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates, build_gate_l1_state, compute_deviation
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal

def run_full_kernel(data, label, x_axis_label="index", x_values=None):
    """Run L0-L4 on a data series and report everything."""
    data_clean = np.maximum(np.array(data, dtype=float), 1e-10)
    n = len(data_clean)

    df = pd.DataFrame({"Close": data_clean}, index=range(n))

    print(f"\n  --- {label} ---")
    print(f"  Points: {n}")

    # L0
    sev_series = compute_sev_series(df, "Close")
    n_negative = sum(1 for s in sev_series if s.N == 1)

    # L1
    gates = segment_gates(sev_series)
    D_t = compute_deviation(sev_series)

    # L2
    interps = interpret_gates(sev_series, gates)

    # L3
    resonance = compute_resonance(interps)

    # L4
    dsf = compute_directional_signal(resonance)

    n_gates = len(gates)
    print(f"  L0: {n_negative}/{n} negative-space points ({n_negative/n*100:.1f}%)")
    print(f"  L1: {n_gates} gates")

    if not interps or not resonance or not dsf:
        print(f"  Insufficient gates for L2-L4 analysis.")
        return None

    # L2 regime summary
    regimes = [ip.regime for ip in interps]
    regime_counts = {}
    for r in regimes:
        regime_counts[r] = regime_counts.get(r, 0) + 1

    print(f"  L2 Regimes: {regime_counts}")

    # L2 detail per gate
    print(f"\n  L2 Gate Detail:")
    print(f"  {'Gate':>4} | {'Range':>12} | {'Regime':<14} | {'S_k':>5} | {'U_k':>5} | {'chi':>5} | {'psi':>5} | {'C_k':>3} | {'IAS':>3}")
    print(f"  {'-'*4}-+-{'-'*12}-+-{'-'*14}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*5}-+-{'-'*3}-+-{'-'*3}")

    for i, ip in enumerate(interps[:20]):
        s_idx = ip.gate.start_idx
        e_idx = ip.gate.end_idx
        if x_values is not None and s_idx < len(x_values) and e_idx < len(x_values):
            rng = f"{x_values[s_idx]:.1f}-{x_values[e_idx]:.1f}"
        else:
            rng = f"{s_idx}-{e_idx}"
        print(f"  {i:>4} | {rng:>12} | {ip.regime:<14} | {ip.S_k:5.3f} | {ip.U_k:5.3f} | {ip.chi_k:5.3f} | {ip.psi_k:5.3f} | {ip.C_k:>3} | {ip.IAS_k:>3}")

    if len(interps) > 20:
        print(f"  ... ({len(interps) - 20} more gates)")

    # L3 resonance summary
    R_values = [r.R_k for r in resonance]
    URF_values = [r.URF_k for r in resonance]
    g_values = [r.g_k for r in resonance]
    hyst_values = [r.Hyst_k for r in resonance]

    gated_open = sum(g_values)
    hyst_count = sum(hyst_values)

    print(f"\n  L3 Resonance:")
    print(f"    R_k range: [{min(R_values):.4f}, {max(R_values):.4f}]")
    print(f"    URF_k range: [{min(URF_values):.4f}, {max(URF_values):.4f}]")
    print(f"    Gates open: {gated_open}/{n_gates} ({gated_open/n_gates*100:.0f}%)")
    print(f"    Hysteresis events: {hyst_count}")

    # L4 decision dynamics
    D_k_values = [d.D_k for d in dsf]
    M_k_values = [d.M_k for d in dsf]
    B_k_values = [d.B_k for d in dsf]
    P_k_values = [d.P_k for d in dsf]
    R_rev_values = [d.R_rev_k for d in dsf]

    # Direction changes
    n_positive = sum(1 for d in D_k_values if d > 0)
    n_negative_d = sum(1 for d in D_k_values if d < 0)
    n_neutral = sum(1 for d in D_k_values if d == 0)
    n_reversals = sum(1 for r in R_rev_values if r > 0)

    print(f"\n  L4 Decision Dynamics:")
    print(f"    D_k: +1={n_positive} | 0={n_neutral} | -1={n_negative_d}")
    print(f"    Reversals: {n_reversals}")
    print(f"    M_k range: [{min(M_k_values):.6f}, {max(M_k_values):.6f}]")
    print(f"    B_k range: [{min(B_k_values):.4f}, {max(B_k_values):.4f}]")
    print(f"    B_k final: {B_k_values[-1]:.4f}")
    print(f"    P_k max: {max(P_k_values):.6f}")

    # L4 detail
    print(f"\n  L4 Gate Detail:")
    print(f"  {'Gate':>4} | {'D_k':>5} | {'M_k':>8} | {'R_rev':>5} | {'U*_k':>5} | {'P_k':>8} | {'B_k':>6} | {'URF':>6} | {'Regime':<12}")
    print(f"  {'-'*4}-+-{'-'*5}-+-{'-'*8}-+-{'-'*5}-+-{'-'*5}-+-{'-'*8}-+-{'-'*6}-+-{'-'*6}-+-{'-'*12}")

    for i in range(min(len(dsf), 20)):
        d = dsf[i]
        r = resonance[i]
        ip = interps[i]
        D_str = f"{d.D_k:+.0f}" if d.D_k != 0 else " 0"
        print(f"  {i:>4} | {D_str:>5} | {d.M_k:+8.5f} | {d.R_rev_k:5.0f} | {d.U_star_k:5.3f} | {d.P_k:8.5f} | {d.B_k:+6.3f} | {r.URF_k:6.4f} | {ip.regime:<12}")

    return {
        "n_gates": n_gates,
        "regimes": regime_counts,
        "R_range": (min(R_values), max(R_values)),
        "gates_open_pct": gated_open / n_gates * 100,
        "n_reversals": n_reversals,
        "D_k_positive": n_positive,
        "D_k_negative": n_negative_d,
        "B_k_final": B_k_values[-1],
        "hyst_count": hyst_count,
    }


print("=" * 70)
print("UF FULL KERNEL (L0-L4): NUCLEAR ANOMALY ANALYSIS")
print("=" * 70)

# ==============================================================
# DATASET 1: GSI decay with 7-second oscillation
# ==============================================================
print(f"\n{'='*70}")
print("GSI DECAY: WITH 7-SECOND OSCILLATION")
print(f"{'='*70}")

t_gsi = np.linspace(0, 120, 2000)
dt = t_gsi[1] - t_gsi[0]
half_life = 203.4
lambda_d = math.log(2) / half_life
N0 = 1000
base = N0 * np.exp(-lambda_d * t_gsi)

T_osc = 7.06
amplitude = 0.18
oscillation = amplitude * np.sin(2 * np.pi * t_gsi / T_osc)
np.random.seed(42)
noise = np.random.normal(0, 0.05, len(t_gsi))

signal_osc = base * (1 + oscillation + noise)
r1 = run_full_kernel(signal_osc, "GSI with 7s oscillation", "time(s)", t_gsi)

# ==============================================================
# DATASET 2: GSI decay WITHOUT oscillation (control)
# ==============================================================
print(f"\n{'='*70}")
print("GSI DECAY: CONTROL (no oscillation)")
print(f"{'='*70}")

signal_ctrl = base * (1 + noise)
r2 = run_full_kernel(signal_ctrl, "GSI control (noise only)", "time(s)", t_gsi)

# ==============================================================
# DATASET 3: Pd screening anomaly vs beam energy
# ==============================================================
print(f"\n{'='*70}")
print("PALLADIUM SCREENING ANOMALY vs BEAM ENERGY")
print(f"{'='*70}")

E_beam = np.linspace(2, 50, 500)

def S_factor(E, U_screen_keV):
    S_bare = 50
    E_G = 31.28
    if E < 0.1:
        return S_bare
    eta = math.sqrt(E_G / (4 * E))
    enhance = math.exp(min(math.pi * eta * U_screen_keV / E, 50))
    return S_bare * enhance

anomaly = np.array([S_factor(E, 0.800)/S_factor(E, 0.050) for E in E_beam])
anomaly = np.minimum(anomaly, 100)

r3 = run_full_kernel(anomaly, "Pd screening anomaly ratio", "E(keV)", E_beam)

# ==============================================================
# COMPARISON
# ==============================================================
print(f"\n{'='*70}")
print("KERNEL COMPARISON: OSCILLATION vs CONTROL")
print(f"{'='*70}\n")

if r1 and r2:
    print(f"  {'Metric':<25} | {'With Oscillation':>18} | {'Control (noise)':>18} | {'Different?':>10}")
    print(f"  {'-'*25}-+-{'-'*18}-+-{'-'*18}-+-{'-'*10}")

    metrics = [
        ("Gates", r1["n_gates"], r2["n_gates"]),
        ("Gates open %", f"{r1['gates_open_pct']:.0f}%", f"{r2['gates_open_pct']:.0f}%"),
        ("Reversals", r1["n_reversals"], r2["n_reversals"]),
        ("D_k positive", r1["D_k_positive"], r2["D_k_positive"]),
        ("D_k negative", r1["D_k_negative"], r2["D_k_negative"]),
        ("B_k final", f"{r1['B_k_final']:.4f}", f"{r2['B_k_final']:.4f}"),
        ("Hysteresis events", r1["hyst_count"], r2["hyst_count"]),
        ("R_k range", f"{r1['R_range'][0]:.3f}-{r1['R_range'][1]:.3f}", f"{r2['R_range'][0]:.3f}-{r2['R_range'][1]:.3f}"),
    ]

    for name, v1, v2 in metrics:
        diff = "YES" if str(v1) != str(v2) else "no"
        print(f"  {name:<25} | {str(v1):>18} | {str(v2):>18} | {diff:>10}")

    print(f"\n  Regime comparison:")
    all_regimes = set(list(r1["regimes"].keys()) + list(r2["regimes"].keys()))
    for reg in sorted(all_regimes):
        c1 = r1["regimes"].get(reg, 0)
        c2 = r2["regimes"].get(reg, 0)
        diff = "YES" if c1 != c2 else "no"
        print(f"    {reg:<15}: {c1:>5} vs {c2:>5} | {diff}")

    print(f"""
  THE KERNEL'S VERDICT:

  If the oscillation produces different structural signatures than
  noise alone, the kernel will show it in:
    - Different gate counts (oscillation creates periodic boundaries)
    - Different regime distribution (oscillation creates TRANSITIONAL regimes)
    - Different reversal count (oscillation creates periodic D_k flips)
    - Different B_k trajectory (breathing dynamics respond to oscillation)
    - Different hysteresis count (oscillation creates R_k jumps)

  The kernel doesn't know about nuclear physics. It doesn't know
  about 7-second periods. It finds STRUCTURAL SIGNATURES in data.
  If the oscillation is real (not statistical noise), the kernel
  sees it as structure. If it's noise, the kernel treats it as noise.
""")
