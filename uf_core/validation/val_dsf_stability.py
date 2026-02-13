"""
UF-Spec v1.4.0 — Section 13 Validation
======================================

Module: val_dsf_stability.py

Purpose:
    Compute ONLY the DSF Stability Score (strict mode) for a given CSV and
    noise level.

This module performs:
    1. Dataset QA
    2. Baseline UF pipeline run
    3. Percentage-noise injection
    4. Noisy UF pipeline run
    5. DSF Stability Score computation
"""

import sys
import os

# Ensure project root is on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd

from uf_core.validation.qa_dataset import qa_csv_structure, qa_csv_content
from uf_core.validation.val_noise import (
    run_uf_pipeline,
    inject_percentage_noise,
)
from uf_core.validation.val_metrics import dsf_stability_score


def main():
    """
    Usage:
        python val_dsf_stability.py <csv_path> <sigma_pct>

    Example:
        python val_dsf_stability.py validation_sample.csv 0.005
    """

    if len(sys.argv) < 3:
        print("Usage: python val_dsf_stability.py <csv_path> <sigma_pct>")
        return

    csv_path = sys.argv[1]
    sigma_pct = float(sys.argv[2])

    # 1. QA
    df = qa_csv_structure(csv_path)
    qa_csv_content(df)

    # 2. Baseline DSF
    _, _, _, _, dsf_base = run_uf_pipeline(df)

    # 3. Noisy DSF
    noisy_df = inject_percentage_noise(df, sigma_pct=sigma_pct, seed=42)
    _, _, _, _, dsf_noisy = run_uf_pipeline(noisy_df)

    # 4. DSF Stability Score
    dssf = dsf_stability_score(dsf_base, dsf_noisy)

    print("\n=== DSF Stability Score (Strict Mode) ===")
    print(f"Sigma_pct: {sigma_pct}")
    print(f"DSF Stability Score: {dssf:.6f}")


if __name__ == "__main__":
    main()
