"""
uf_core.layer1 — Gate Segmentation (UF-Spec v1.4.0)
===================================================

Implements the L1 gate segmentation portion of the UF v1.4.0 kernel.

This step focuses on:
- The deviation operator D(t) based on ΔF(t), σ(t), κ(t)
- A fixed global threshold τ_D for gate boundaries
- Producing gate segments as index ranges
- Computing structural TVR_k per gate (Hybrid: structural, extensible)

Mosaic embedding (MLMA) will be added in a subsequent step, NOT here.

UF v1.4.0 L1 requirements addressed in this module:
- D(t) = α1 * |ΔF(t)| + α2 * σ(t) + α3 * κ(t)
- Gate opening based solely on D(t) > τ_D
- Negative-space N(t) is NOT a gate opener
- TVR_k defined as structural summaries per gate
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .layer0 import SEV
from .config import KERNEL_THRESHOLDS


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Gate:
    """
    A gate represents a contiguous segment of the time axis [start_idx, end_idx]
    where the structural field is considered internally coherent at L1.
    """
    start_idx: int
    end_idx: int


# ---------------------------------------------------------------------------
# Deviation operator D(t) — UF-Spec v1.4.0
# ---------------------------------------------------------------------------

def compute_deviation(sev_series: List[SEV],
                      alpha1: float = 1.0,
                      alpha2: float = 1.0,
                      alpha3: float = 1.0) -> np.ndarray:
    """
    Compute D(t) for each SEV in the series, using:

        D(t) = α1 * |ΔF(t)| + α2 * σ(t) + α3 * κ(t)

    This corresponds to UF-Spec v1.4.0 L1 deviation definition.
    """

    n = len(sev_series)
    D = np.zeros(n, dtype=float)

    for i, sev in enumerate(sev_series):
        D[i] = (
            alpha1 * abs(sev.dF) +
            alpha2 * sev.sigma +
            alpha3 * sev.kappa
        )

    return D


# ---------------------------------------------------------------------------
# Gate segmentation using fixed τ_D
# ---------------------------------------------------------------------------

def segment_gates(sev_series: List[SEV]) -> List[Gate]:
    """
    Segment the SEV series into gates based on D(t) and a fixed threshold τ_D.

    Gate opening rule:

        - Start with index 0 as the beginning of the first gate.
        - For t > 0, if D(t) > τ_D, then close the previous gate at t-1 and
          start a new gate at t.
        - At the end, close the final gate at the last index.

    Negative-space N(t) is NOT used as a gate opener in v1.4.0.

    Returns:
        List[Gate] with (start_idx, end_idx) pairs.
    """

    if not sev_series:
        return []

    D = compute_deviation(sev_series)
    tau_D = KERNEL_THRESHOLDS.tau_D

    gates: List[Gate] = []
    current_start = 0

    for i in range(1, len(sev_series)):
        if D[i] > tau_D:
            gates.append(Gate(start_idx=current_start, end_idx=i-1))
            current_start = i

    gates.append(Gate(start_idx=current_start, end_idx=len(sev_series) - 1))

    return gates


# ---------------------------------------------------------------------------
# TVR_k extraction per gate (Hybrid structural definition)
# ---------------------------------------------------------------------------

def compute_gate_tvr(sev_series: List[SEV],
                     gates: List[Gate]) -> List[Tuple[float, float, float, float]]:
    """
    Compute a structural Time-Volume-Relevance-like vector for each gate:

        TVR_k = (ΔT_k, ΔF_k, σ̄_k, κ̄_k)

    Where:
    - ΔT_k  = gate length (number of steps)
    - ΔF_k  = mean absolute ΔF(t) over the gate
    - σ̄_k  = mean σ(t) over the gate
    - κ̄_k  = mean κ(t) over the gate

    This is the HYBRID structural TVR definition. Domain-specific extensions
    (e.g., volume, fundamentals) will be added at the adapter level, not here.
    """

    if not sev_series or not gates:
        return []

    tvr_list: List[Tuple[float, float, float, float]] = []

    # Extract simple series for convenience
    dF_series = np.array([sev.dF for sev in sev_series], dtype=float)
    sigma_series = np.array([sev.sigma for sev in sev_series], dtype=float)
    kappa_series = np.array([sev.kappa for sev in sev_series], dtype=float)

    for gate in gates:
        s = gate.start_idx
        e = gate.end_idx

        length = max(1, e - s + 1)  # ΔT_k as count

        seg_dF = dF_series[s:e+1]
        seg_sigma = sigma_series[s:e+1]
        seg_kappa = kappa_series[s:e+1]

        mean_abs_dF = float(np.mean(np.abs(seg_dF))) if len(seg_dF) > 0 else 0.0
        mean_sigma = float(np.mean(seg_sigma)) if len(seg_sigma) > 0 else 0.0
        mean_kappa = float(np.mean(seg_kappa)) if len(seg_kappa) > 0 else 0.0

        tvr_list.append((length, mean_abs_dF, mean_sigma, mean_kappa))

    return tvr_list
