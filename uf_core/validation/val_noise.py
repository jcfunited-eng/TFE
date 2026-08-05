"""
UF-Spec v1.4.0 — Section 13.1 Noise Robustness Validation
========================================================

This module runs the UF L0 → L4 pipeline on:
- baseline (clean) price data
- noisy price data (Gaussian multiplicative noise as percentage)

Noise model:
    noisy_price[t] = price[t] * (1 + eps[t])
    eps ~ N(0, sigma_pct^2)

Where:
    sigma_pct is a DECIMAL percentage (e.g., 0.005 = 0.5%)

This module currently:
- Runs both pipelines
- Prints structural DSF differences
- DOES NOT compute validation metrics yet
"""

import sys
import os
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Fix import path so uf_core loads correctly when running this script directly
# ---------------------------------------------------------------------------

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ---------------------------------------------------------------------------
# UF pipeline imports
# ---------------------------------------------------------------------------

from uf_core.validation.qa_dataset import qa_csv_structure, qa_csv_content
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf

from uf_core.validation.noise_model import gaussian_noise


# ---------------------------------------------------------------------------
# UF pipeline wrapper
# ---------------------------------------------------------------------------

def run_uf_pipeline(df: pd.DataFrame, price_col: str = "Close"):
    sev_list = compute_sev_series(df, price_col=price_col)
    gates = segment_gates(sev_list)
    interpretations = interpret_gates(sev_list, gates)
    resonance_results = compute_resonance(interpretations)
    decision_states = compute_directional_signal(resonance_results)
    dsf_list = compute_dsf(decision_states)
    return gates, interpretations, resonance_results, decision_states, dsf_list


# ---------------------------------------------------------------------------
# Noise injection (percentage-based)
# ---------------------------------------------------------------------------

def inject_percentage_noise(df: pd.DataFrame,
                            sigma_pct: float,
                            price_col: str = "Close",
                            seed: int = None) -> pd.DataFrame:
    """
    Apply Gaussian MULTIPLICATIVE noise where:

        noisy_price[t] = price[t] * (1 + eps[t])
        eps ~ N(0, sigma_pct^2)

    sigma_pct is a DECIMAL percent (e.g., 0.005 = 0.5%).
    """
    noisy_df = df.copy()
    clean = df[price_col].astype(float).values

    # Generate eps[t] ~ N(0, sigma_pct^2)
    eps = gaussian_noise(len(clean), sigma_pct, seed=seed)

    # Apply multiplicative noise
    noisy_df[price_col] = clean * (1.0 + eps)
    return noisy_df


# ---------------------------------------------------------------------------
# DSF difference function
# ---------------------------------------------------------------------------

def diff_dsf(baseline, noisy):
    """
    Compare two DSF sequences gate-by-gate.
    Returns dictionary of mismatches.
    """
    mismatches = {
        "D": 0,
        "M": 0,
        "R_rev": 0,
        "U_star": 0,
        "P": 0,
        "B": 0,
        "length_difference": False
    }

    if len(baseline) != len(noisy):
        mismatches["length_difference"] = True
        return mismatches

    for b, n in zip(baseline, noisy):
        if b.D_k != n.D_k:
            mismatches["D"] += 1
        if b.M_k != n.M_k:
            mismatches["M"] += 1
        if b.R_rev_k != n.R_rev_k:
            mismatches["R_rev"] += 1
        if abs(b.U_star_k - n.U_star_k) > 1e-9:
            mismatches["U_star"] += 1
        if b.P_k != n.P_k:
            mismatches["P"] += 1
        if b.B_k != n.B_k:
            mismatches["B"] += 1

    return mismatches


# ---------------------------------------------------------------------------
# Main Execution
# ---------------------------------------------------------------------------

def main():
    """
    RUN:
        python val_noise.py <path_to_csv> <sigma_pct>

    Example:
        python val_noise.py validation_sample.csv 0.005
    (applies 0.5% noise)
    """
    if len(sys.argv) < 3:
        print("Usage: python val_noise.py <csv> <sigma_pct>")
        return

    csv_path = sys.argv[1]
    sigma_pct = float(sys.argv[2])  # Already DECIMAL percent

    print(f"\n=== UF Noise Robustness Test (sigma_pct = {sigma_pct}) ===")

    # Load + QA CSV
    df = qa_csv_structure(csv_path)
    qa_csv_content(df)

    # Baseline run
    print("Running baseline UF pipeline...")
    _, _, _, _, dsf_base = run_uf_pipeline(df)

    # Inject noise (multiplicative, Section 13.1 compliant)
    print("Injecting percentage-based noise...")
    noisy_df = inject_percentage_noise(df, sigma_pct=sigma_pct, seed=42)

    # Noisy run
    print("Running noisy UF pipeline...")
    _, _, _, _, dsf_noisy = run_uf_pipeline(noisy_df)

    # Compare DSF sequences
    print("\n--- Structural Differences (Baseline vs Noisy) ---")
    diffs = diff_dsf(dsf_base, dsf_noisy)

    if diffs["length_difference"]:
        print("Gate count differs between baseline and noisy.")
    else:
        print("Gate count identical.")

    print(f"D_k mismatches      : {diffs['D']}")
    print(f"M_k mismatches      : {diffs['M']}")
    print(f"R_rev_k mismatches  : {diffs['R_rev']}")
    print(f"U*_k mismatches     : {diffs['U_star']}")
    print(f"P_k mismatches      : {diffs['P']}")
    print(f"B_k mismatches      : {diffs['B']}")

    print("\n(Note: Metrics and pass/fail logic will be added in later steps.)")


if __name__ == "__main__":
    main()
