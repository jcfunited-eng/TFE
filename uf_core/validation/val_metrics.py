"""
UF-Spec v1.4.0 — Section 13 Validation Metrics
===============================================

Module: val_metrics.py

Purpose:
    Provide the quantitative scoring functions required by UF Section 13,
    including:
    - Gate Stability Score
    - Directional Stability Score
    - DSF Stability Score
    - Sensitivity Curve Construction
    - Composite System Metrics S(UF) and R(UF)

STRICT MODE IMPLEMENTATIONS:
    - gate_stability_score
    - directional_stability_score
    - dsf_stability_score
    - sensitivity_curve
    - composite_validation_metrics
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Gate Stability Score (STRICT)
# ---------------------------------------------------------------------------

def gate_stability_score(baseline_dsf, noisy_dsf):
    if len(baseline_dsf) != len(noisy_dsf):
        return 0.0

    total = len(baseline_dsf)
    if total == 0:
        return 1.0

    mismatches = 0
    for b, n in zip(baseline_dsf, noisy_dsf):
        if (b.gate.start_idx != n.gate.start_idx) or (b.gate.end_idx != n.gate.end_idx):
            mismatches += 1

    return float(1.0 - mismatches / total)


# ---------------------------------------------------------------------------
# Directional Stability Score (STRICT)
# ---------------------------------------------------------------------------

def directional_stability_score(baseline_dsf, noisy_dsf):
    if len(baseline_dsf) != len(noisy_dsf):
        return 0.0

    total = len(baseline_dsf)
    if total == 0:
        return 1.0

    mismatches = 0
    for b, n in zip(baseline_dsf, noisy_dsf):
        if (b.D_k != n.D_k) or (b.M_k != n.M_k) or (b.R_rev_k != n.R_rev_k):
            mismatches += 1

    return float(1.0 - mismatches / total)


# ---------------------------------------------------------------------------
# DSF Stability Score (STRICT)
# ---------------------------------------------------------------------------

def dsf_stability_score(baseline_dsf, noisy_dsf):
    if len(baseline_dsf) != len(noisy_dsf):
        return 0.0

    total = len(baseline_dsf)
    if total == 0:
        return 1.0

    mismatches = 0
    for b, n in zip(baseline_dsf, noisy_dsf):
        if (
            (b.D_k != n.D_k)
            or (b.M_k != n.M_k)
            or (b.R_rev_k != n.R_rev_k)
            or (abs(b.U_star_k - n.U_star_k) > 1e-9)
            or (b.P_k != n.P_k)
            or (b.B_k != n.B_k)
        ):
            mismatches += 1

    return float(1.0 - mismatches / total)


# ---------------------------------------------------------------------------
# Sensitivity Curve Construction (STRICT)
# ---------------------------------------------------------------------------

def sensitivity_curve(results_by_sigma):
    """
    Construct a deterministic, sorted representation of stability results
    across different sigma_pct values.

    Input:
        results_by_sigma: list of tuples
            (sigma_pct, gate_stab, dir_stab, dsf_stab)

    Output:
        List[Dict]:
        [
            {
                "sigma_pct": ...,
                "gate": ...,
                "directional": ...,
                "dsf": ...
            },
            ...
        ]
    """
    sorted_results = sorted(results_by_sigma, key=lambda x: x[0])

    curve = []
    for sigma, g, d, dsf in sorted_results:
        curve.append({
            "sigma_pct": float(sigma),
            "gate": float(g),
            "directional": float(d),
            "dsf": float(dsf),
        })

    return curve


# ---------------------------------------------------------------------------
# Composite UF Metrics: S(UF) and R(UF)
# ---------------------------------------------------------------------------

def composite_validation_metrics(stability_scores, sensitivity_data):
    """
    Compute composite UF metrics:

        S(UF): Structural Stability Score
        R(UF): Robustness Score

    Inputs:
        stability_scores: dict-like with keys:
            {
                "gate": <GateStab at reference sigma>,
                "directional": <DirStab at reference sigma>,
                "dsf": <DSFStab at reference sigma>
            }

        sensitivity_data: list[dict] as returned by sensitivity_curve:
            [
                {
                    "sigma_pct": ...,
                    "gate": ...,
                    "directional": ...,
                    "dsf": ...
                },
                ...
            ]

    Definitions (STRICT):

        S(UF) = (gate_stab + directional_stab + dsf_stab) / 3

        R(UF) = AUC of DSF stability over normalized sigma_pct ∈ [0,1],
                computed via trapezoidal rule.

        - If all dsf stability = 1 across noise, R(UF) = 1.
        - If dsf stability collapses quickly, R(UF) is small.
    """

    # --- S(UF) ---
    gate_stab = float(stability_scores.get("gate", 0.0))
    dir_stab  = float(stability_scores.get("directional", 0.0))
    dsf_stab  = float(stability_scores.get("dsf", 0.0))

    S_UF = (gate_stab + dir_stab + dsf_stab) / 3.0

    # --- R(UF) ---
    if not sensitivity_data:
        R_UF = 0.0
    else:
        sigmas = np.array([entry["sigma_pct"] for entry in sensitivity_data], dtype=float)
        dsf_vals = np.array([entry["dsf"] for entry in sensitivity_data], dtype=float)

        sigma_max = np.max(sigmas) if sigmas.size > 0 else 1.0
        if sigma_max == 0:
            # All sigmas zero → treat robustness as average dsf
            R_UF = float(np.mean(dsf_vals)) if dsf_vals.size > 0 else 0.0
        else:
            t = sigmas / sigma_max  # normalize to [0,1]
            # Trapezoidal AUC on dsf vs t
            R_UF = float(np.trapz(dsf_vals, t)) if dsf_vals.size > 0 else 0.0

    return {
        "S_UF": float(S_UF),
        "R_UF": float(R_UF),
    }
