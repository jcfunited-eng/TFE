"""
UF-Spec v1.4.0 — Section 13 Composite Metrics
=============================================

Module: val_composite_metrics.py

Purpose:
    Compute composite UF metrics:
        - S(UF): Structural Stability Score
        - R(UF): Robustness Score

Using:
    - gate_stability_score
    - directional_stability_score
    - dsf_stability_score
    - sensitivity_curve
    - composite_validation_metrics
"""

import sys
import os

# Ensure project root is on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from uf_core.validation.qa_dataset import qa_csv_structure, qa_csv_content
from uf_core.validation.val_noise import (
    run_uf_pipeline,
    inject_percentage_noise,
)
from uf_core.validation.val_metrics import (
    gate_stability_score,
    directional_stability_score,
    dsf_stability_score,
    sensitivity_curve,
    composite_validation_metrics,
)


def run_stability_for_sigma(df, sigma_pct: float):
    """
    Compute stability metrics for a single sigma_pct.
    Returns:
        (sigma_pct, gate_stab, dir_stab, dsf_stab)
    """
    _, _, _, _, dsf_base = run_uf_pipeline(df)
    noisy_df = inject_percentage_noise(df, sigma_pct=sigma_pct, seed=42)
    _, _, _, _, dsf_noisy = run_uf_pipeline(noisy_df)

    gss  = gate_stability_score(dsf_base, dsf_noisy)
    dss  = directional_stability_score(dsf_base, dsf_noisy)
    dssf = dsf_stability_score(dsf_base, dsf_noisy)

    return sigma_pct, gss, dss, dssf


def main():
    """
    Usage:
        python val_composite_metrics.py <csv_path>

    Sigma grid (fixed here):
        [0.001, 0.002, 0.005, 0.010, 0.020]

    Reference sigma for S(UF):
        sigma_ref = 0.005
    """

    if len(sys.argv) < 2:
        print("Usage: python val_composite_metrics.py <csv_path>")
        return

    csv_path = sys.argv[1]

    # 1. QA dataset
    df = qa_csv_structure(csv_path)
    qa_csv_content(df)

    # 2. Define sigma grid
    sigma_grid = [0.001, 0.002, 0.005, 0.010, 0.020]
    sigma_ref = 0.005

    # 3. Collect results per sigma
    results_by_sigma = []
    for sigma in sigma_grid:
        res = run_stability_for_sigma(df, sigma)
        results_by_sigma.append(res)

    # 4. Build sensitivity curve
    curve = sensitivity_curve(results_by_sigma)

    # 5. Extract stability_scores at reference sigma
    #    (strict lookup)
    ref_entry = None
    for entry in curve:
        if abs(entry["sigma_pct"] - sigma_ref) < 1e-12:
            ref_entry = entry
            break

    if ref_entry is None:
        print(f"ERROR: reference sigma {sigma_ref} not found in sensitivity data.")
        return

    stability_scores = {
        "gate":        ref_entry["gate"],
        "directional": ref_entry["directional"],
        "dsf":         ref_entry["dsf"],
    }

    # 6. Compute composite metrics
    composite = composite_validation_metrics(stability_scores, curve)

    S_UF = composite["S_UF"]
    R_UF = composite["R_UF"]

    # 7. Print results
    print("\n=== UF Composite Metrics (Strict Mode) ===")
    print(f"Reference sigma_pct for S(UF): {sigma_ref}")
    print(f"S(UF) (structural stability): {S_UF:.6f}")
    print(f"R(UF) (robustness)          : {R_UF:.6f}\n")


if __name__ == "__main__":
    main()
