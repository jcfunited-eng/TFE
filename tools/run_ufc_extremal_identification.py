#!/usr/bin/env python3
from __future__ import annotations

import csv
import glob
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path("/workspaces/Tao_Financial_Engine").resolve()
BACKUPS = REPO_ROOT / "backups" / "runtime"
WEB_ROOT = REPO_ROOT / "web"
CURRENT_EXPERIMENTAL_RUNTIME = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision-unified-field.ts"
SELECTED_RUNTIME_SOURCE = WEB_ROOT / "src" / "lib" / "uf-dynamic-decision-unified-field-selected.ts"

BASELINE_SYNTHETIC_VALIDATION = BACKUPS / "dsf_primitive_production_synthetic_validation_20260321T044121Z.json"
BASELINE_FULL_DISTRIBUTION = BACKUPS / "dsf_primitive_production_distribution_fixed_snapshot_20260321T035659Z.json"
BASELINE_LATEST_SNAPSHOT_DECISION = BACKUPS / "dsf_primitive_production_latest_snapshot_decision_20260321T013943Z.json"
BASELINE_ONE_SIDED_CONTESTED = BACKUPS / "dsf_primitive_production_one_sided_contested_full_audit_fixed_snapshot_20260321T055330Z.json"

ANCHORS = [
    ("AGO", "Accumulate", "Accumulate anchor 1"),
    ("TXRH", "Accumulate", "Accumulate anchor 2"),
    ("DHI", "Accumulate", "Accumulate anchor 3"),
    ("AAT", "Hold", "Hold anchor 1"),
    ("ACGL", "Hold", "Hold anchor 2"),
    ("ADC", "Hold", "Hold anchor 3"),
    ("AA", "Avoid", "Avoid anchor 1"),
    ("AAPL", "Avoid", "Avoid anchor 2"),
    ("ACLS", "Avoid", "Avoid anchor 3"),
]

EIGEN_EPSILON = 1e-9


@dataclass(frozen=True)
class PrimitiveState:
    symbol: str
    barCount: int
    S_UF: float
    R_UF: float
    D_k: float
    M_k: float
    R_rev_k: float
    U_star_k: float
    C_k: float
    P_k: float
    B_k: float


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_stamp(dt: datetime | None = None) -> str:
    value = dt or utc_now()
    return value.strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def write_markdown(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def latest_file(prefix: str, suffix: str) -> Path:
    matches = sorted(glob.glob(str(BACKUPS / f"{prefix}*{suffix}")))
    if not matches:
        raise SystemExit(f"missing artifact for {prefix}*{suffix}")
    return Path(matches[-1])


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def positive_part(value: float) -> float:
    return max(value, 0.0)


def negative_part(value: float) -> float:
    return max(-value, 0.0)


def canonicalize_state(input_row: dict[str, Any]) -> PrimitiveState:
    return PrimitiveState(
        symbol=str(input_row.get("symbol", "")),
        barCount=int(float(input_row.get("barCount", 252))),
        S_UF=clip(float(input_row["S_UF"]), 0.0, 1.0),
        R_UF=clip(float(input_row["R_UF"]), 0.0, 1.0),
        D_k=clip(float(input_row["D_k"]), -1.0, 1.0),
        M_k=clip(float(input_row["M_k"]), -1.0, 1.0),
        R_rev_k=clip(float(input_row["R_rev_k"]), 0.0, 1.0),
        U_star_k=clip(float(input_row["U_star_k"]), 0.0, 1.0),
        C_k=max(0.0, float(input_row["C_k"])),
        P_k=max(0.0, float(input_row["P_k"])),
        B_k=clip(float(input_row["B_k"]), -1.0, 1.0),
    )


def dsf_relations(state: PrimitiveState) -> dict[str, float]:
    s = state.S_UF - state.U_star_k
    r = state.R_UF - state.U_star_k
    q_r = 1.0 - state.R_rev_k
    q_c = 1.0 / (1.0 + state.C_k)
    q_p = 1.0 / (1.0 + state.P_k)
    directional_positive = positive_part(state.D_k)
    directional_negative = negative_part(state.D_k)
    momentum_positive = positive_part(state.M_k)
    momentum_negative = negative_part(state.M_k)
    carry_positive = positive_part(state.B_k)
    carry_negative = negative_part(state.B_k)
    rupture = max(directional_negative, momentum_negative, carry_negative, 1.0 - q_r)
    forward = directional_positive * momentum_positive * carry_positive * q_r
    contest = directional_positive * q_r * positive_part(1.0 - rupture)
    return {
        "s": s,
        "r": r,
        "q_r": q_r,
        "q_c": q_c,
        "q_p": q_p,
        "weak_coverage": min(s, r),
        "secondary_coverage": max(s, r),
        "trajectory_forward": forward,
        "trajectory_contest": contest,
        "trajectory_rupture": rupture,
    }


def topology(rel: dict[str, float]) -> str:
    if rel["weak_coverage"] > 0:
        return "covered"
    if rel["secondary_coverage"] > 0:
        return "one_sided"
    return "double_sided"


def trajectory_family(rel: dict[str, float]) -> str:
    if rel["trajectory_forward"] == 0 and rel["trajectory_rupture"] == 0:
        return "still"
    if rel["trajectory_forward"] > rel["trajectory_contest"] and rel["trajectory_forward"] > rel["trajectory_rupture"]:
        return "constructive"
    if rel["trajectory_rupture"] > rel["trajectory_forward"] and rel["trajectory_rupture"] > rel["trajectory_contest"]:
        return "rupture_like"
    return "contested"


def tensor_components(state: PrimitiveState) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rel = dsf_relations(state)
    tensor = np.array(
        [
            [rel["s"], 0.0, state.D_k, state.M_k, state.B_k],
            [0.0, rel["r"], state.D_k, state.M_k, state.B_k],
            [state.D_k, state.D_k, rel["q_r"], 0.0, 0.0],
            [state.M_k, state.M_k, 0.0, rel["q_c"], 0.0],
            [state.B_k, state.B_k, 0.0, 0.0, rel["q_p"]],
        ],
        dtype=float,
    )
    return tensor, tensor[:2, :2], tensor[2:, 2:], tensor[:2, 2:]


def leading_principal_minors(matrix: np.ndarray) -> list[float]:
    return [float(np.linalg.det(matrix[:k, :k])) for k in range(1, matrix.shape[0] + 1)]


def stable_condition_number(matrix: np.ndarray) -> float | None:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    smallest = singular_values[-1]
    if abs(smallest) <= EIGEN_EPSILON:
        return None
    return float(singular_values[0] / smallest)


def invariant_bundle(tensor: np.ndarray, effective_reserve: np.ndarray | None = None, metric: np.ndarray | None = None) -> dict[str, Any]:
    eigvals, eigvecs = np.linalg.eigh(tensor)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    dominant = eigvecs[:, order[0]]
    off = tensor - np.diag(np.diag(tensor))
    positive_mass = float(np.maximum(eigvals, 0).sum())
    negative_mass = float(np.maximum(-eigvals, 0).sum())
    out = {
        "eigenvalues": [float(v) for v in eigvals],
        "inertia": {
            "n_pos": int(np.sum(eigvals > EIGEN_EPSILON)),
            "n_neg": int(np.sum(eigvals < -EIGEN_EPSILON)),
            "n_zero": int(np.sum(np.abs(eigvals) <= EIGEN_EPSILON)),
        },
        "trace": float(np.trace(tensor)),
        "determinant": float(np.linalg.det(tensor)),
        "principal_minors": leading_principal_minors(tensor),
        "positive_spectral_mass": positive_mass,
        "negative_spectral_mass": negative_mass,
        "indefiniteness_mass": float(min(positive_mass, negative_mass)),
        "dominant_mode_signed_coupling": float(dominant.T @ off @ dominant),
        "condition_number": stable_condition_number(tensor),
        "diagonal_norm": float(np.linalg.norm(np.diag(np.diag(tensor)), ord="fro")),
        "off_diagonal_norm": float(np.linalg.norm(off, ord="fro")),
    }
    if effective_reserve is not None:
        out["effective_reserve_eigenvalues"] = [float(v) for v in np.sort(np.linalg.eigvalsh(effective_reserve))[::-1]]
    if metric is not None:
        out["metric_condition_number"] = stable_condition_number(metric)
    return out


def family_1_raw_tensor_signature(state: PrimitiveState) -> dict[str, Any]:
    tensor, _, _, _ = tensor_components(state)
    inv = invariant_bundle(tensor)
    eigvals = np.array(inv["eigenvalues"], dtype=float)
    if bool(np.all(eigvals > EIGEN_EPSILON)):
        decision = "Accumulate"
    elif inv["inertia"]["n_neg"] >= inv["inertia"]["n_pos"] and inv["trace"] < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "invariants": inv}


def family_2_raw_tensor_spectral_orientation(state: PrimitiveState) -> dict[str, Any]:
    tensor, _, _, _ = tensor_components(state)
    inv = invariant_bundle(tensor)
    if inv["positive_spectral_mass"] > inv["negative_spectral_mass"] and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif inv["negative_spectral_mass"] > inv["positive_spectral_mass"] and inv["dominant_mode_signed_coupling"] < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "invariants": inv}


def family_3_reserve_reduced_schur(state: PrimitiveState) -> dict[str, Any]:
    tensor, reserve, admissibility, coupling = tensor_components(state)
    if abs(float(np.linalg.det(admissibility))) <= EIGEN_EPSILON:
        inv = invariant_bundle(tensor)
        inv["effective_reserve_eigenvalues"] = None
        inv["schur_defined"] = False
        return {"decision": "Hold", "invariants": inv}
    effective = reserve - coupling @ np.linalg.inv(admissibility) @ coupling.T
    inv = invariant_bundle(tensor, effective_reserve=effective)
    inv["schur_defined"] = True
    mu1, mu2 = inv["effective_reserve_eigenvalues"]
    if mu1 > 0 and mu2 > 0 and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif mu1 < 0 and mu2 < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "invariants": inv}


def family_4_bounded_resolvent_reserve(state: PrimitiveState) -> dict[str, Any]:
    tensor, reserve, admissibility, coupling = tensor_components(state)
    effective = reserve - coupling @ np.linalg.inv(np.eye(3) + admissibility) @ coupling.T
    inv = invariant_bundle(tensor, effective_reserve=effective)
    mu1, mu2 = inv["effective_reserve_eigenvalues"]
    if mu1 > 0 and mu2 > 0 and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif mu1 < 0 and mu2 < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    return {"decision": decision, "invariants": inv}


def family_5_primitive_congruence_preconditioned_tensor(state: PrimitiveState) -> dict[str, Any]:
    tensor, _, _, _ = tensor_components(state)
    rel = dsf_relations(state)
    metric_diag = np.array([1.0 + abs(rel["s"]), 1.0 + abs(rel["r"]), 1.0 + rel["q_r"], 1.0 + rel["q_c"], 1.0 + rel["q_p"]], dtype=float)
    root = np.diag(metric_diag ** -0.5)
    transformed = root @ tensor @ root
    inv = invariant_bundle(transformed, metric=np.diag(metric_diag))
    if inv["positive_spectral_mass"] > inv["negative_spectral_mass"] and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif inv["negative_spectral_mass"] > inv["positive_spectral_mass"] and inv["dominant_mode_signed_coupling"] < 0:
        decision = "Avoid"
    else:
        decision = "Hold"
    inv["preconditioner_metric_diagonal"] = [float(v) for v in metric_diag]
    return {"decision": decision, "invariants": inv}


def family_6_generalized_eigen_geometry(state: PrimitiveState) -> dict[str, Any]:
    tensor, _, _, _ = tensor_components(state)
    rel = dsf_relations(state)
    metric_diag = np.array(
        [
            1.0 + positive_part(rel["s"]) + positive_part(rel["r"]),
            1.0 + positive_part(rel["s"]) + positive_part(rel["r"]),
            rel["q_r"] + rel["q_c"],
            rel["q_c"] + rel["q_p"],
            rel["q_r"] + rel["q_p"],
        ],
        dtype=float,
    )
    root = np.diag(metric_diag ** -0.5)
    generalized = root @ tensor @ root
    inv = invariant_bundle(generalized, metric=np.diag(metric_diag))
    eigvals = np.array(inv["eigenvalues"], dtype=float)
    if bool(np.all(eigvals > EIGEN_EPSILON)) and inv["dominant_mode_signed_coupling"] > 0:
        decision = "Accumulate"
    elif inv["negative_spectral_mass"] > inv["positive_spectral_mass"]:
        decision = "Avoid"
    else:
        decision = "Hold"
    inv["generalized_metric_diagonal"] = [float(v) for v in metric_diag]
    return {"decision": decision, "invariants": inv}


CANDIDATE_FAMILIES = {
    "family_1_raw_tensor_signature": family_1_raw_tensor_signature,
    "family_2_raw_tensor_spectral_orientation": family_2_raw_tensor_spectral_orientation,
    "family_3_reserve_reduced_schur": family_3_reserve_reduced_schur,
    "family_4_bounded_resolvent_reserve": family_4_bounded_resolvent_reserve,
    "family_5_primitive_congruence_preconditioned_tensor": family_5_primitive_congruence_preconditioned_tensor,
    "family_6_generalized_eigen_geometry": family_6_generalized_eigen_geometry,
}


def state_from_reserves(label: str, idx: int, u: float, rl: float, rr: float, d: float, m: float, rev: float, c: float, p: float, b: float) -> PrimitiveState:
    return PrimitiveState(
        symbol=f"{label}_{idx}",
        barCount=252,
        S_UF=clip(u + rl, 0.0, 1.0),
        R_UF=clip(u + rr, 0.0, 1.0),
        D_k=clip(d, -1.0, 1.0),
        M_k=clip(m, -1.0, 1.0),
        R_rev_k=clip(rev, 0.0, 1.0),
        U_star_k=clip(u, 0.0, 1.0),
        C_k=max(0.0, c),
        P_k=max(0.0, p),
        B_k=clip(b, -1.0, 1.0),
    )


def generate_canonical_extreme_families() -> dict[str, list[PrimitiveState]]:
    out: dict[str, list[PrimitiveState]] = defaultdict(list)

    def add_family(name: str, configs: list[tuple[float, float, float, float, float, float, float, float, float]]):
        for idx, cfg in enumerate(configs):
            out[name].append(state_from_reserves(name, idx, *cfg))

    covered_reserves = [(0.08, 0.12), (0.12, 0.12), (0.12, 0.22)]
    one_sided_reserves = [(-0.05, 0.08), (-0.10, 0.14), (-0.18, 0.24)]
    collapse_reserves = [(-0.04, -0.02), (-0.10, -0.08), (-0.24, -0.20)]
    low_mid_loads = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    load_sweep = [(0.0, 0.0), (0.0, 2.0), (2.0, 2.0), (4.0, 1.0)]
    constructive_motion = [(0.0, 0.4), (0.4, 0.4), (1.0, 0.6)]
    contested_motion = [(0.2, -0.2), (0.6, -0.1), (1.0, 0.0)]
    rupture_motion = [(-0.6, -0.2), (0.2, -0.6), (0.0, -1.0)]

    add_family(
        "covered_constructive",
        [(u, rl, rr, d, m, 0.0, c, p, b) for u in (0.20, 0.45) for rl, rr in covered_reserves for d, m in constructive_motion for c, p in low_mid_loads for b in (-0.2, 0.0, 0.3)],
    )
    add_family(
        "covered_still",
        [(u, rl, rr, 0.0, 0.0, 0.0, c, p, b) for u in (0.20, 0.45) for rl, rr in covered_reserves for c, p in low_mid_loads for b in (-0.1, 0.0, 0.1)],
    )
    add_family(
        "one_sided_constructive_edge",
        [(u, rl, rr, d, m, 0.0, c, p, b) for u in (0.20, 0.45) for rl, rr in one_sided_reserves for d, m in ((0.0, 0.4), (1.0, 0.4)) for c, p in low_mid_loads for b in (-0.2, 0.0, 0.1)],
    )
    add_family(
        "one_sided_contested",
        [(u, rl, rr, d, m, 0.0, c, p, b) for u in (0.20, 0.45) for rl, rr in one_sided_reserves for d, m in contested_motion for c, p in load_sweep for b in (-0.4, 0.0, 0.2, 0.4)],
    )
    add_family(
        "covered_rupture_like",
        [(u, rl, rr, d, m, rev, c, p, b) for u in (0.20, 0.45) for rl, rr in covered_reserves for d, m in rupture_motion for rev in (0.0, 1.0) for c, p in load_sweep for b in (-1.0, -0.4, 0.0)],
    )
    add_family(
        "one_sided_rupture",
        [(u, rl, rr, d, m, rev, c, p, b) for u in (0.20, 0.45) for rl, rr in one_sided_reserves for d, m in rupture_motion for rev in (0.0, 1.0) for c, p in load_sweep for b in (-1.0, -0.4, 0.0)],
    )
    add_family(
        "double_sided_collapse",
        [(u, rl, rr, d, m, rev, c, p, b) for u in (0.20, 0.45) for rl, rr in collapse_reserves for d, m in rupture_motion + [(-1.0, -1.0)] for rev in (0.0, 1.0) for c, p in [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (4.0, 1.0), (1.0, 4.0)] for b in (-1.0, -0.5)],
    )
    add_family(
        "reversal_active_covered",
        [(u, rl, rr, d, m, rev, c, p, b) for u in (0.20, 0.45) for rl, rr in covered_reserves for d, m in constructive_motion + contested_motion for rev in (0.25, 1.0) for c, p in load_sweep for b in (-0.3, 0.3)],
    )
    return out


def serialize_points(families: dict[str, list[PrimitiveState]]) -> dict[str, Any]:
    return {
        "families": {
            name: {
                "count": len(points),
                "points": [
                    {
                        "symbol": p.symbol,
                        "barCount": p.barCount,
                        "S_UF": p.S_UF,
                        "R_UF": p.R_UF,
                        "D_k": p.D_k,
                        "M_k": p.M_k,
                        "R_rev_k": p.R_rev_k,
                        "U_star_k": p.U_star_k,
                        "C_k": p.C_k,
                        "P_k": p.P_k,
                        "B_k": p.B_k,
                        "topology": topology(dsf_relations(p)),
                        "trajectory_family": trajectory_family(dsf_relations(p)),
                    }
                    for p in points
                ],
            }
            for name, points in families.items()
        }
    }


def summarize_invariants(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for field in [
        "trace",
        "determinant",
        "positive_spectral_mass",
        "negative_spectral_mass",
        "indefiniteness_mass",
        "dominant_mode_signed_coupling",
        "diagonal_norm",
        "off_diagonal_norm",
    ]:
        values = [r["invariants"][field] for r in results if r["invariants"].get(field) is not None]
        summary[field] = {
            "min": float(min(values)),
            "max": float(max(values)),
            "mean": float(sum(values) / len(values)),
        }
    reserve = [r["invariants"].get("effective_reserve_eigenvalues") for r in results if r["invariants"].get("effective_reserve_eigenvalues") is not None]
    if reserve:
        mu1 = [pair[0] for pair in reserve]
        mu2 = [pair[1] for pair in reserve]
        summary["effective_reserve_eigenvalues"] = {
            "mu1": {"min": float(min(mu1)), "max": float(max(mu1)), "mean": float(sum(mu1) / len(mu1))},
            "mu2": {"min": float(min(mu2)), "max": float(max(mu2)), "mean": float(sum(mu2) / len(mu2))},
        }
    return summary


def dominant_decision(counts: Counter[str]) -> str | None:
    if not counts:
        return None
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    return ranked[0][0]


def stage_a_law_checks(family_decisions: dict[str, Counter[str]]) -> dict[str, Any]:
    checks = {
        "covered_still_primary_hold": dominant_decision(family_decisions["covered_still"]) == "Hold",
        "double_sided_collapse_primary_avoid": dominant_decision(family_decisions["double_sided_collapse"]) == "Avoid",
        "covered_constructive_admits_accumulate": family_decisions["covered_constructive"]["Accumulate"] > 0,
        "one_sided_constructive_edge_not_mainly_avoid": dominant_decision(family_decisions["one_sided_constructive_edge"]) != "Avoid",
        "covered_rupture_like_not_mainly_accumulate": dominant_decision(family_decisions["covered_rupture_like"]) != "Accumulate",
        "one_sided_contested_not_mainly_avoid": dominant_decision(family_decisions["one_sided_contested"]) != "Avoid",
    }
    return {"checks": checks, "passed_count": int(sum(1 for value in checks.values() if value)), "total_checks": len(checks)}


def read_latest_snapshot_rows(path: Path) -> list[PrimitiveState]:
    rows: list[PrimitiveState] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(canonicalize_state({**row, "barCount": row["bar_count"]}))
    return rows


def prefilter_full_rowtrace(path: Path) -> tuple[list[PrimitiveState], list[PrimitiveState]]:
    covered_rupture_rows: list[PrimitiveState] = []
    one_sided_contested_rows: list[PrimitiveState] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            state = canonicalize_state({**row, "barCount": row["bar_count"]})
            rel = dsf_relations(state)
            topo = topology(rel)
            traj = trajectory_family(rel)
            if topo == "covered" and traj == "rupture_like":
                covered_rupture_rows.append(state)
            if topo == "one_sided" and traj == "contested":
                one_sided_contested_rows.append(state)
    return covered_rupture_rows, one_sided_contested_rows


def evaluate_stage_b_candidate(
    evaluator,
    latest_rows: list[PrimitiveState],
    covered_rupture_rows: list[PrimitiveState],
    one_sided_contested_rows: list[PrimitiveState],
    synthetic_suite: dict[str, Any],
) -> dict[str, Any]:
    latest_by_symbol = {row.symbol.upper(): row for row in latest_rows}
    anchor_cases = []
    matched = 0
    for symbol, expected, note in ANCHORS:
        row = latest_by_symbol.get(symbol)
        decision = "Hold" if row is None else evaluator(row)["decision"]
        if decision == expected:
            matched += 1
        anchor_cases.append({"symbol": symbol, "expected_decision": expected, "decision": decision, "matched_expected": decision == expected, "note": note})

    seam_counts: Counter[str] = Counter()
    for sample in synthetic_suite["samples"]:
        if sample["stored_trajectory_family"] == "constructive" and sample["stored_sign_w2"] == "pos":
            seam_counts[evaluator(canonicalize_state(sample["reconstructed_input"]))["decision"]] += 1

    latest_counts: Counter[str] = Counter()
    latest_dtt: Counter[str] = Counter()
    for row in latest_rows:
        decision = evaluator(row)["decision"]
        latest_counts[decision] += 1
        rel = dsf_relations(row)
        latest_dtt[f"{decision}|{topology(rel)}|{trajectory_family(rel)}"] += 1

    covered_counts: Counter[str] = Counter()
    for row in covered_rupture_rows:
        covered_counts[evaluator(row)["decision"].lower() if evaluator(row)["decision"] != "Hold" else "hold_positive"] += 1

    contested_counts: Counter[str] = Counter()
    for row in one_sided_contested_rows:
        contested_counts[evaluator(row)["decision"]] += 1

    contested_total = sum(contested_counts.values())
    return {
        "anchors": {"matched_expected_count": matched, "total_cases": len(ANCHORS), "cases": anchor_cases},
        "seam_probe": {"count": int(sum(seam_counts.values())), "decision_counts": dict(seam_counts)},
        "covered_rupture_compare": {
            "counts": {
                "hold_positive": int(covered_counts.get("hold_positive", 0)),
                "accumulate": int(covered_counts.get("accumulate", 0)),
                "avoid": int(covered_counts.get("avoid", 0)),
                "hold_zero_basin_fallback": 0,
            },
            "zero_basin_fallback": 0,
        },
        "latest_snapshot_distribution": {"counts": dict(latest_counts), "decision_by_topology_trajectory": dict(latest_dtt)},
        "one_sided_contested_compare": {
            "total": contested_total,
            "decision_counts": dict(contested_counts),
            "avoid_share": (contested_counts["Avoid"] / contested_total) if contested_total else 0.0,
        },
    }


def baseline_stage_b_bundle() -> dict[str, Any]:
    baseline_synthetic = load_json(BASELINE_SYNTHETIC_VALIDATION)
    baseline_distribution = load_json(BASELINE_FULL_DISTRIBUTION)
    baseline_latest = load_json(BASELINE_LATEST_SNAPSHOT_DECISION)
    baseline_one_sided = load_json(BASELINE_ONE_SIDED_CONTESTED)
    return {
        "anchors": {"matched_expected_count": baseline_synthetic["anchor_pressure_test"]["summary"]["matchedExpectedCount"], "total_cases": baseline_synthetic["anchor_pressure_test"]["summary"]["totalCases"]},
        "seam_probe": baseline_synthetic["corrected_positive_w2_seam_probe"],
        "covered_rupture_compare": {
            "counts": baseline_distribution["covered_rupture_like_basin_ownership"],
            "zero_basin_fallback": baseline_distribution["covered_rupture_like_basin_ownership"].get("hold_zero_basin_fallback", 0),
        },
        "latest_snapshot_distribution": baseline_latest["latest_snapshot_decision_distribution"],
        "one_sided_contested_compare": {
            "total": baseline_one_sided["totals"]["all_one_sided_contested_rows"],
            "decision_counts": baseline_one_sided["decision_counts"],
            "avoid_share": baseline_one_sided["totals"]["avoid_share"],
        },
    }


def stage_b_catastrophic_failures(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, bool]:
    return {
        "anchors_below_baseline": candidate["anchors"]["matched_expected_count"] < baseline["anchors"]["matched_expected_count"],
        "seam_accumulate_eliminated": candidate["seam_probe"]["decision_counts"].get("Accumulate", 0) == 0,
        "covered_rupture_accumulate_exceeds_baseline": candidate["covered_rupture_compare"]["counts"].get("accumulate", 0) > baseline["covered_rupture_compare"]["counts"].get("accumulate", 0),
        "latest_accumulate_eliminated": candidate["latest_snapshot_distribution"]["counts"].get("Accumulate", 0) == 0,
        "latest_hold_eliminated": candidate["latest_snapshot_distribution"]["counts"].get("Hold", 0) == 0,
        "covered_still_hold_eliminated": candidate["latest_snapshot_distribution"]["decision_by_topology_trajectory"].get("Hold|covered|still", 0) == 0,
    }


def summarize_invariant_family(
    name: str,
    families: dict[str, list[PrimitiveState]],
    latest_rows: list[PrimitiveState],
    covered_rupture_rows: list[PrimitiveState],
    one_sided_contested_rows: list[PrimitiveState],
    synthetic_suite: dict[str, Any],
    baseline_stage_b: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    evaluator = CANDIDATE_FAMILIES[name]
    matrix: dict[str, Any] = {}
    family_decisions: dict[str, Counter[str]] = {}
    for family_name, points in families.items():
        results = [evaluator(point) for point in points]
        counts = Counter(result["decision"] for result in results)
        family_decisions[family_name] = counts
        matrix[family_name] = {
            "point_count": len(points),
            "decision_counts": dict(counts),
            "dominant_decision": dominant_decision(counts),
            "invariant_summary": summarize_invariants(results),
        }
    stage_a = stage_a_law_checks(family_decisions)
    stage_b = evaluate_stage_b_candidate(evaluator, latest_rows, covered_rupture_rows, one_sided_contested_rows, synthetic_suite)
    catastrophic = stage_b_catastrophic_failures(stage_b, baseline_stage_b)
    return matrix, {
        "candidate_name": name,
        "stage_a": stage_a,
        "stage_b": stage_b,
        "stage_b_catastrophic_failures": catastrophic,
        "catastrophic_failure_count": int(sum(1 for value in catastrophic.values() if value)),
    }


def rank_candidates(scorecards: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    return sorted(
        scorecards.items(),
        key=lambda item: (
            -item[1]["stage_a"]["passed_count"],
            item[1]["catastrophic_failure_count"],
            -item[1]["stage_b"]["anchors"]["matched_expected_count"],
            -item[1]["stage_b"]["seam_probe"]["decision_counts"].get("Accumulate", 0),
        ),
    )


def selected_candidate_name(scorecards: dict[str, dict[str, Any]]) -> str | None:
    ranked = rank_candidates(scorecards)
    best_name, best = ranked[0]
    if best["stage_a"]["passed_count"] == best["stage_a"]["total_checks"] and best["catastrophic_failure_count"] == 0:
        if len(ranked) == 1:
            return best_name
        second = ranked[1][1]
        if best["stage_a"]["passed_count"] > second["stage_a"]["passed_count"] or best["catastrophic_failure_count"] < second["catastrophic_failure_count"]:
            return best_name
    return None


def forced_conclusion(selected_name: str | None, scorecards: dict[str, dict[str, Any]]) -> str:
    if selected_name is not None:
        return "one invariant family clearly dominates baseline and prior tensor variants"
    best = rank_candidates(scorecards)[0][1]
    if best["stage_a"]["passed_count"] > 0:
        return "one invariant family is promising but not yet safer than baseline"
    return "no whole-field invariant family identified yet; do not continue tensor replacement"


def load_prior_tensor_variant_verdicts() -> dict[str, Any]:
    out = {}
    for label, path in {
        "v2": BACKUPS / "dsf_primitive_unified_field_tensor_v2_verdict_20260321T194043Z.json",
        "v3": BACKUPS / "dsf_primitive_unified_field_tensor_v3_verdict_20260321T201817Z.json",
        "v4": BACKUPS / "dsf_primitive_unified_field_tensor_v4_verdict_20260321T205633Z.json",
        "v5": BACKUPS / "dsf_primitive_unified_field_tensor_v5_verdict_20260321T212204Z.json",
    }.items():
        if path.exists():
            verdict = load_json(path)
            out[label] = {"explicit_statement": verdict.get("explicit statement"), "forced_conclusion": verdict.get("forced_conclusion")}
    return out


def selected_candidate_validation_artifact(selected_name: str | None, scorecards: dict[str, dict[str, Any]], prior: dict[str, Any]) -> dict[str, Any]:
    ranked = rank_candidates(scorecards)
    return {
        "selected_candidate": selected_name,
        "selected_runtime_path": str(SELECTED_RUNTIME_SOURCE) if selected_name else None,
        "selected_runtime_created": bool(selected_name),
        "best_available_candidate": ranked[0][0],
        "best_available_stage_a_passes": ranked[0][1]["stage_a"]["passed_count"],
        "best_available_catastrophic_failure_count": ranked[0][1]["catastrophic_failure_count"],
        "prior_tensor_variants": prior,
        "forced_conclusion": forced_conclusion(selected_name, scorecards),
    }


def write_selected_runtime(selected_name: str) -> None:
    SELECTED_RUNTIME_SOURCE.write_text(f"export const UFC_SELECTED_INVARIANT_FAMILY = {json.dumps(selected_name)} as const;\n", encoding="utf-8")


def send_slack_completion(event: dict[str, Any]) -> None:
    payload = json.dumps(event)
    subprocess.run(["bash", "-lc", f"printf '%s\\n' {json.dumps(payload)} | /workspaces/Tao_Financial_Engine/tools/codex_notify_slack.sh"], cwd=str(REPO_ROOT), check=True)


def main() -> int:
    started = utc_now()
    stamp = utc_stamp(started)

    latest_snapshot_csv = latest_file("canonical_real_snapshot_production_fixed_snapshot_latest_", ".csv")
    full_rowtrace_csv = latest_file("canonical_real_rowtrace_production_fixed_snapshot_", ".csv")
    synthetic_suite_path = latest_file("canonical_synthetic_suite_production_fixed_snapshot_", ".json")

    latest_rows = read_latest_snapshot_rows(latest_snapshot_csv)
    covered_rupture_rows, one_sided_contested_rows = prefilter_full_rowtrace(full_rowtrace_csv)
    synthetic_suite = load_json(synthetic_suite_path)
    baseline_stage_b = baseline_stage_b_bundle()

    canonical_families = generate_canonical_extreme_families()
    family_points_payload = {"generated_at_utc": utc_iso(), "source": "approved primitive tuple geometry only", "families": serialize_points(canonical_families)["families"]}

    family_matrix: dict[str, Any] = {}
    scorecards: dict[str, Any] = {}
    for name in CANDIDATE_FAMILIES:
        matrix, scorecard = summarize_invariant_family(name, canonical_families, latest_rows, covered_rupture_rows, one_sided_contested_rows, synthetic_suite, baseline_stage_b)
        family_matrix[name] = matrix
        scorecards[name] = scorecard

    selected_name = selected_candidate_name(scorecards)
    if selected_name is not None:
        write_selected_runtime(selected_name)

    final_conclusion = forced_conclusion(selected_name, scorecards)
    prior_variants = load_prior_tensor_variant_verdicts()
    selected_validation = selected_candidate_validation_artifact(selected_name, scorecards, prior_variants)
    ranked = rank_candidates(scorecards)

    study_json = {
        "generated_at_utc": utc_iso(),
        "requested_architecture": "UFC extremal identification study before any further runtime replacement attempt",
        "current_code_reality": "baseline plus tensor v1-v5 each improved some surfaces and broke others",
        "common_whole_tensor_object": str(CURRENT_EXPERIMENTAL_RUNTIME),
        "accepted_snapshot_sources": {
            "latest_snapshot_csv": str(latest_snapshot_csv),
            "full_rowtrace_csv": str(full_rowtrace_csv),
            "synthetic_suite_json": str(synthetic_suite_path),
        },
        "selection_rule_outcome": {"selected_candidate": selected_name, "forced_conclusion": final_conclusion},
    }

    scorecard_json = {
        "generated_at_utc": utc_iso(),
        "ranked_candidates": [
            {
                "candidate_name": name,
                "stage_a_passed_count": card["stage_a"]["passed_count"],
                "stage_a_total_checks": card["stage_a"]["total_checks"],
                "catastrophic_failure_count": card["catastrophic_failure_count"],
                "anchor_matches": card["stage_b"]["anchors"]["matched_expected_count"],
                "seam_accumulate": card["stage_b"]["seam_probe"]["decision_counts"].get("Accumulate", 0),
                "covered_rupture_accumulate": card["stage_b"]["covered_rupture_compare"]["counts"].get("accumulate", 0),
            }
            for name, card in ranked
        ],
        "scorecards": scorecards,
        "selected_candidate": selected_name,
        "forced_conclusion": final_conclusion,
    }

    study_md = "# DSF UFC Extremal Identification\n\n## Ranking\n" + "\n".join(
        f"- `{name}`: stage A `{card['stage_a']['passed_count']}/{card['stage_a']['total_checks']}`, catastrophic failures `{card['catastrophic_failure_count']}`"
        for name, card in ranked
    ) + f"\n\n## Selection\n- selected candidate: `{selected_name}`\n- forced conclusion: `{final_conclusion}`\n"

    selected_md = "# UFC Selected Candidate Validation\n\n" + f"## Selected Candidate\n- selected candidate: `{selected_name}`\n- selected runtime created: `{bool(selected_name)}`\n\n## Prior Tensor Variants\n" + "\n".join(
        f"- `{label}`: `{info['forced_conclusion']}`" for label, info in prior_variants.items()
    ) + f"\n\n## Forced Conclusion\n- `{final_conclusion}`\n"

    family_points_path = BACKUPS / f"canonical_extreme_family_points_{stamp}.json"
    study_json_path = BACKUPS / f"dsf_ufc_extremal_identification_{stamp}.json"
    study_md_path = BACKUPS / f"dsf_ufc_extremal_identification_{stamp}.md"
    family_matrix_path = BACKUPS / f"dsf_ufc_extremal_family_matrix_{stamp}.json"
    scorecard_path = BACKUPS / f"dsf_ufc_invariant_family_scorecard_{stamp}.json"
    selected_validation_path = BACKUPS / f"dsf_ufc_selected_candidate_validation_{stamp}.json"
    selected_validation_md_path = BACKUPS / f"dsf_ufc_selected_candidate_validation_{stamp}.md"

    write_json(family_points_path, family_points_payload)
    write_json(study_json_path, study_json)
    write_markdown(study_md_path, study_md)
    write_json(family_matrix_path, family_matrix)
    write_json(scorecard_path, scorecard_json)
    write_json(selected_validation_path, selected_validation)
    write_markdown(selected_validation_md_path, selected_md)

    send_slack_completion({"task": "ufc extremal identification complete", "forced_conclusion": final_conclusion, "study_artifact": str(study_json_path)})

    print(
        json.dumps(
            {
                "canonical_extreme_family_points": str(family_points_path),
                "study_json": str(study_json_path),
                "study_md": str(study_md_path),
                "family_matrix": str(family_matrix_path),
                "scorecard": str(scorecard_path),
                "selected_candidate_validation_json": str(selected_validation_path),
                "selected_candidate_validation_md": str(selected_validation_md_path),
                "selected_candidate": selected_name,
                "forced_conclusion": final_conclusion,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
