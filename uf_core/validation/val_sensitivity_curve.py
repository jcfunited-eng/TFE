"""
UF-Spec v1.4.0 — Section 13 Sensitivity Curve
=============================================

Module: val_sensitivity_curve.py

Purpose:
    Use the existing stability computation across a sigma grid and transform
    it into a structured sensitivity curve via val_metrics.sensitivity_curve.
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
)


def run_stability_for_sigma(df, sigma_pct: float):
    """
    Compute stability metrics for a single sigma_pct.
    Returns:
        (sigma_pct, gate_stab, dir_stab, dsf_stab)
    """
    # Baseline DSF
    _, _, _, _, dsf_base = run_uf_pipeline(df)

    # Noisy DSF
    noisy_df = inject_percentage_noise(df, sigma_pct=sigma_pct, seed=42)
    _, _, _, _, dsf_noisy = run_uf_pipeline(noisy_df)

    # Metrics
    gss  = gate_stability_score(dsf_base, dsf_noisy)
    dss  = directional_stability_score(dsf_base, dsf_noisy)
    dssf = dsf_stability_score(dsf_base, dsf_noisy)

    return sigma_pct, gss, dss, dssf


def main():
    """
    Usage:
        python val_sensitivity_curve.py <csv_path>

    Sigma grid (fixed in this runner):
        [0.001, 0.002, 0.005, 0.010, 0.020]
    """

    if len(sys.argv) < 2:
        print("Usage: python val_sensitivity_curve.py <csv_path>")
        return

    csv_path = sys.argv[1]

    # 1. QA dataset
    df = qa_csv_structure(csv_path)
    qa_csv_content(df)

    # 2. Sigma grid
    sigma_grid = [0.001, 0.002, 0.005, 0.010, 0.020]

    # 3. Collect raw results
    results_by_sigma = []
    for sigma in sigma_grid:
        res = run_stability_for_sigma(df, sigma)
        results_by_sigma.append(res)

    # 4. Transform via sensitivity_curve
    curve = sensitivity_curve(results_by_sigma)

    # 5. Print curve
    print("=== UF Sensitivity Curve (Strict Mode) ===")
    print("sigma_pct  gate      directional  dsf")
    for entry in curve:
        print(f"{entry['sigma_pct']:8.3f}  "
              f"{entry['gate']:8.6f}  "
              f"{entry['directional']:12.6f}  "
              f"{entry['dsf']:8.6f}")


if __name__ == "__main__":
    main()
