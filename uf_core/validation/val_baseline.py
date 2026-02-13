"""
UF-Spec v1.4.0 — Section 13 Validation
======================================

Module: val_baseline.py

Purpose:
    Run the UF L0 → L4 pipeline on a validated dataset (no noise)
    and print minimal baseline structural outputs.

This file includes a sys.path correction so that UF imports work
when executed directly via:
    python uf_core/validation/val_baseline.py <csv>
"""

import sys
import os
import pandas as pd

# ---------------------------------------------------------------------------
# Ensure project root is on PYTHONPATH
# ---------------------------------------------------------------------------

# Directory containing this file: .../uf_core/validation/
current_dir = os.path.dirname(os.path.abspath(__file__))

# Project root = parent of uf_core/
project_root = os.path.dirname(os.path.dirname(current_dir))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ---------------------------------------------------------------------------
# Now imports work deterministically
# ---------------------------------------------------------------------------

from uf_core.validation.qa_dataset import qa_csv_structure, qa_csv_content
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates
from uf_core.layer3 import compute_resonance
from uf_core.layer4 import compute_directional_signal, compute_dsf


def run_baseline(csv_path: str):
    """
    Perform:
    - QA checks
    - UF pipeline L0 → L4
    - DSF extraction
    - Minimal summary printouts
    """

    # 1) Load and QA dataset
    df = qa_csv_structure(csv_path)
    qa_csv_content(df)

    # 2) Run baseline UF pipeline
    sev_list = compute_sev_series(df)
    gates = segment_gates(sev_list)
    interpretations = interpret_gates(sev_list, gates)
    resonance_results = compute_resonance(interpretations)
    decision_states = compute_directional_signal(resonance_results)
    dsf_list = compute_dsf(decision_states)

    # 3) Print minimal structural results
    print("=== Baseline UF Run Summary ===")
    print(f"  Number of rows         : {len(df)}")
    print(f"  Number of gates        : {len(gates)}")
    print(f"  Number of DSF entries  : {len(dsf_list)}\n")

    print("=== First 5 DSF entries (if available) ===")
    for idx, dsf in enumerate(dsf_list[:5], start=1):
        gate = dsf.gate
        print(f"DSF {idx}: Gate[{gate.start_idx},{gate.end_idx}] "
              f"D={dsf.D_k}, M={dsf.M_k}, R_rev={dsf.R_rev_k}, "
              f"U*={dsf.U_star_k:.6f}, P={dsf.P_k}, B={dsf.B_k}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python val_baseline.py <path_to_csv>")
        return

    csv_path = sys.argv[1]
    run_baseline(csv_path)


if __name__ == "__main__":
    main()
