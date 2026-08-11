"""
uf_core.layer1 — Gate and Mosaic Architecture (UF-Spec v1.4.0)
================================================================

L1 responsibilities:
- Segment L0 SEV stream into gates via boundary operator D(t).
- Compute gate TVR descriptors: (T_k, V_k, R_k).
- Compute multi-lattice projections P_l(G_k).
- Compute mosaic divergence C_k.
- Compute gate drift delta_g(G_k).
- Compute negative-space gate flags N(G_k).

The approved domain override for boundary comparison (`>` instead of `>=`) is
preserved and controlled by `KERNEL_THRESHOLDS.gate_boundary_strict_gt`.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import List, Sequence, Tuple

import numpy as np

from .config import KERNEL_THRESHOLDS
from .layer0 import SEV


TVR = Tuple[float, float, float]
Projection = Tuple[int, int, int]


@dataclass(frozen=True)
class Gate:
    """Contiguous time segment [start_idx, end_idx] in the SEV stream."""

    start_idx: int
    end_idx: int


@dataclass(frozen=True)
class GateL1State:
    """Complete L1 output record for one gate."""

    gate: Gate
    tvr: TVR
    projections: Tuple[Projection, ...]
    C_k: int
    delta_g: float
    N_gate: int


def compute_deviation(
    sev_series: Sequence[SEV],
    alpha1: float | None = None,
    alpha2: float | None = None,
    alpha3: float | None = None,
) -> np.ndarray:
    """Compute D(t) = a1*||dF|| + a2*sigma + a3*kappa."""

    if alpha1 is None:
        alpha1 = float(KERNEL_THRESHOLDS.alpha1)
    if alpha2 is None:
        alpha2 = float(KERNEL_THRESHOLDS.alpha2)
    if alpha3 is None:
        alpha3 = float(KERNEL_THRESHOLDS.alpha3)

    D = np.zeros(len(sev_series), dtype=float)
    for i, sev in enumerate(sev_series):
        D[i] = (
            alpha1 * abs(float(sev.dF))
            + alpha2 * float(sev.sigma)
            + alpha3 * float(sev.kappa)
        )
    return D


def segment_gates(sev_series: Sequence[SEV]) -> List[Gate]:
    """
    Segment gates by threshold crossings of D(t).

    Canonical boundary form is D(t) >= tau_D.
    Approved domain override keeps strict D(t) > tau_D when configured.
    """

    if not sev_series:
        return []

    D = compute_deviation(sev_series)
    tau_D = float(KERNEL_THRESHOLDS.tau_D)
    strict_gt = bool(getattr(KERNEL_THRESHOLDS, "gate_boundary_strict_gt", True))

    gates: List[Gate] = []
    current_start = 0

    for i in range(1, len(sev_series)):
        if strict_gt:
            boundary = D[i] > tau_D
        else:
            boundary = D[i] >= tau_D

        if boundary:
            gates.append(Gate(start_idx=current_start, end_idx=i - 1))
            current_start = i

    gates.append(Gate(start_idx=current_start, end_idx=len(sev_series) - 1))
    return gates


def compute_gate_tvr(
    sev_series: Sequence[SEV],
    gates: Sequence[Gate],
    beta1: float | None = None,
    beta2: float | None = None,
    beta3: float | None = None,
) -> List[TVR]:
    """
    Compute TVR_k = (T_k, V_k, R_k).

    Discrete implementation with dt=1:
    - T_k = t_b - t_a
    - V_k = sum(beta1*|dF| + beta2*sigma + beta3*kappa)
    - R_k = sum(relevance)
    """

    if beta1 is None:
        beta1 = float(KERNEL_THRESHOLDS.beta1)
    if beta2 is None:
        beta2 = float(KERNEL_THRESHOLDS.beta2)
    if beta3 is None:
        beta3 = float(KERNEL_THRESHOLDS.beta3)

    if not sev_series or not gates:
        return []

    dF = np.array([float(sev.dF) for sev in sev_series], dtype=float)
    sigma = np.array([float(sev.sigma) for sev in sev_series], dtype=float)
    kappa = np.array([float(sev.kappa) for sev in sev_series], dtype=float)
    relevance = np.array([float(sev.relevance) for sev in sev_series], dtype=float)

    out: List[TVR] = []
    for gate in gates:
        s = gate.start_idx
        e = gate.end_idx

        T_k = float(max(0, e - s))

        seg_dF = dF[s : e + 1]
        seg_sigma = sigma[s : e + 1]
        seg_kappa = kappa[s : e + 1]
        seg_rel = relevance[s : e + 1]

        V_k = float(np.sum(beta1 * np.abs(seg_dF) + beta2 * seg_sigma + beta3 * seg_kappa))
        R_k = float(np.sum(seg_rel))
        out.append((T_k, V_k, R_k))

    return out


def compute_gate_means(sev_series: Sequence[SEV], gates: Sequence[Gate]) -> List[Tuple[float, float, float]]:
    """Compute mu_k = mean(dF, sigma, kappa) for each gate."""

    if not sev_series or not gates:
        return []

    dF = np.array([float(sev.dF) for sev in sev_series], dtype=float)
    sigma = np.array([float(sev.sigma) for sev in sev_series], dtype=float)
    kappa = np.array([float(sev.kappa) for sev in sev_series], dtype=float)

    means: List[Tuple[float, float, float]] = []
    for gate in gates:
        s = gate.start_idx
        e = gate.end_idx
        seg_dF = dF[s : e + 1]
        seg_sigma = sigma[s : e + 1]
        seg_kappa = kappa[s : e + 1]

        means.append(
            (
                float(np.mean(seg_dF)) if len(seg_dF) else 0.0,
                float(np.mean(seg_sigma)) if len(seg_sigma) else 0.0,
                float(np.mean(seg_kappa)) if len(seg_kappa) else 0.0,
            )
        )

    return means


def compute_gate_drift(means: Sequence[Tuple[float, float, float]]) -> List[float]:
    """Compute delta_g(G_k) = ||mu_k - mu_{k-1}||, with delta_0 = 0."""

    if not means:
        return []

    drifts: List[float] = [0.0]
    for i in range(1, len(means)):
        prev = np.array(means[i - 1], dtype=float)
        curr = np.array(means[i], dtype=float)
        drifts.append(float(np.linalg.norm(curr - prev)))
    return drifts


def _resolve_lattices(lattice_steps: Sequence[Tuple[float, float, float]] | None) -> Tuple[Tuple[float, float, float], ...]:
    if lattice_steps is None:
        lattice_steps = KERNEL_THRESHOLDS.mosaic_lattices

    out: List[Tuple[float, float, float]] = []
    for h1, h2, h3 in lattice_steps:
        if h1 <= 0 or h2 <= 0 or h3 <= 0:
            raise ValueError("All lattice steps must be positive.")
        out.append((float(h1), float(h2), float(h3)))

    if not out:
        raise ValueError("At least one lattice must be configured.")

    return tuple(out)


def compute_mosaic_projections(
    tvr_list: Sequence[TVR],
    lattice_steps: Sequence[Tuple[float, float, float]] | None = None,
) -> List[Tuple[Projection, ...]]:
    """Compute P_l(G_k) = (floor(T/h1), floor(V/h2), floor(R/h3)) for each lattice."""

    if not tvr_list:
        return []

    lattices = _resolve_lattices(lattice_steps)
    projections: List[Tuple[Projection, ...]] = []

    for T_k, V_k, R_k in tvr_list:
        gate_proj: List[Projection] = []
        for h1, h2, h3 in lattices:
            gate_proj.append(
                (
                    int(floor(T_k / h1)),
                    int(floor(V_k / h2)),
                    int(floor(R_k / h3)),
                )
            )
        projections.append(tuple(gate_proj))

    return projections


def compute_mosaic_divergence(projections: Sequence[Tuple[Projection, ...]]) -> List[int]:
    """Compute C_k = |{P_1(G_k), ..., P_L(G_k)}| for each gate."""

    if not projections:
        return []

    out: List[int] = []
    for gate_proj in projections:
        out.append(int(len(set(gate_proj))))
    return out


def compute_negative_space_gate_flags(
    sev_series: Sequence[SEV],
    gates: Sequence[Gate],
    tvr_list: Sequence[TVR],
    theta_V: float | None = None,
    theta_R: float | None = None,
) -> List[int]:
    """Compute N(G_k) gate flag from SEV N(t), V_k, and R_k thresholds."""

    if theta_V is None:
        theta_V = float(KERNEL_THRESHOLDS.theta_V)
    if theta_R is None:
        theta_R = float(KERNEL_THRESHOLDS.theta_R)

    if not sev_series or not gates or not tvr_list:
        return []

    N_values = np.array([int(sev.N) for sev in sev_series], dtype=int)
    flags: List[int] = []

    for gate, (_, V_k, R_k) in zip(gates, tvr_list):
        s = gate.start_idx
        e = gate.end_idx
        seg_N = N_values[s : e + 1]
        all_negative_space = bool(len(seg_N) > 0 and np.all(seg_N == 1))
        flags.append(1 if (all_negative_space and V_k < theta_V and R_k < theta_R) else 0)

    return flags


def build_gate_l1_state(sev_series: Sequence[SEV], gates: Sequence[Gate]) -> List[GateL1State]:
    """Build full L1 records for each gate."""

    if not sev_series or not gates:
        return []

    tvr_list = compute_gate_tvr(sev_series, gates)
    projections = compute_mosaic_projections(tvr_list)
    C_k_list = compute_mosaic_divergence(projections)
    means = compute_gate_means(sev_series, gates)
    delta_g_list = compute_gate_drift(means)
    N_gate_list = compute_negative_space_gate_flags(sev_series, gates, tvr_list)

    out: List[GateL1State] = []
    for gate, tvr, proj, C_k, delta_g, N_gate in zip(
        gates,
        tvr_list,
        projections,
        C_k_list,
        delta_g_list,
        N_gate_list,
    ):
        out.append(
            GateL1State(
                gate=gate,
                tvr=tvr,
                projections=proj,
                C_k=int(C_k),
                delta_g=float(delta_g),
                N_gate=int(N_gate),
            )
        )

    return out
